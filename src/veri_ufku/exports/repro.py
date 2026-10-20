"""Data-only, bounded reproducibility bundles. ZIP reopening never executes code."""

import hashlib
import importlib.metadata as md
import json
import os
import platform
import re
import stat
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from veri_ufku.exports.code_bridge import environment as code_environment
from veri_ufku.exports.files import publish
from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.experiment_store import quota, usage
from veri_ufku.storage.lineage import graph
from veri_ufku.storage.project_model import (
    SCHEMA_VERSION,
    ProjectError,
    entity_id,
    fingerprint,
    relative,
    uid,
)

MAX_TOTAL = 128 * 1024**2
MAX_METADATA = 8 * 1024**2
SECRET_KEY = re.compile(
    r"password|passwd|secret|token|credential|authorization|cookie|private.?key|api.?key",
    re.I,
)
SENSITIVE = re.compile(
    r"(?:bearer\s+|password\s*[:=]|token\s*[:=]|secret\s*[:=]|-----BEGIN .*PRIVATE KEY|(?:AKIA|ASIA)[A-Z0-9]{16})",
    re.I,
)
LOCATION = re.compile(
    r"(?:^/|^[A-Za-z]:[\\/]|https?://|s3://|file://|/home/|/tmp/|/proc/)"
)


def raw(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
        separators=(",", ":"),
    ).encode()


def sanitize(value):
    """Fail-closed names/notes/free text; preview stores locations/reasons, never secrets."""
    changes = []

    def visit(v, path="root"):
        if isinstance(v, dict):
            result = {}
            for k, item in sorted(v.items(), key=lambda pair: str(pair[0])):
                # Unknown secret-looking keys themselves may contain user material.
                label = (
                    "field-" + str(len(result))
                    if SECRET_KEY.search(str(k)) or LOCATION.search(str(k))
                    else str(k)
                )
                where = path + "." + label
                if SECRET_KEY.search(str(k)) or str(k) in (
                    "source_location",
                    "path",
                    "destination",
                    "output_dir",
                    "cache",
                    "original_name",
                    "description",
                    "note",
                    "title",
                    "purpose",
                    "name",
                ):
                    changes.append(
                        dict(field=where, reason="secret/location/free-text field")
                    )
                    result[label] = "[redacted]"
                else:
                    result[label] = visit(item, where)
            return result
        if isinstance(v, (list, tuple)):
            # Provenance.environment historically stores key/value pairs rather
            # than mappings. A plain secret value must be masked there as well.
            if (
                len(v) == 2
                and isinstance(v[0], str)
                and (
                    SECRET_KEY.search(v[0])
                    or v[0] in ("path", "file_path", "location", "url")
                )
            ):
                changes.append(
                    dict(field=path, reason="secret/location provenance pair")
                )
                return ["[redacted-field]", "[redacted]"]
            return [visit(x, path + "." + str(i)) for i, x in enumerate(v)]
        if isinstance(v, str) and (LOCATION.search(v) or SENSITIVE.search(v)):
            changes.append(
                dict(field=path, reason="external location or secret pattern")
            )
            return "[redacted]"
        return v

    cleaned = visit(value)
    return cleaned, sorted(changes, key=lambda row: (row["field"], row["reason"]))


def environment():
    from veri_ufku.analytics import contracts, dataset
    from veri_ufku.exports import code_bridge, repro_worker
    from veri_ufku.modeling import repro_verify
    from veri_ufku.operations.workflow_fingerprint import signature
    from veri_ufku.storage import lineage

    env = code_environment()
    files = [
        Path(__file__),
        Path(dataset.__file__),
        Path(contracts.__file__),
        Path(code_bridge.__file__),
        Path(repro_verify.__file__),
        Path(repro_worker.__file__),
        Path(lineage.__file__),
        *[
            Path(__file__).parents[1] / p
            for p in ("jobs/resources.py", "jobs/limits.py", "importers/delimited.py")
        ],
    ]
    env.update(
        system=platform.system(),
        project_schema=SCHEMA_VERSION,
        bundle_schema="ReproBundle/v1",
        workflow=signature(),
        repro_code_hash=digest(
            {
                str(p.relative_to(Path(__file__).parents[1])): hashlib.sha256(
                    p.read_bytes()
                ).hexdigest()
                for p in files
            }
        ),
    )
    return env


def hardware():
    return dict(
        system=platform.system(),
        machine=platform.machine(),
        visible_cpu_count=len(os.sched_getaffinity(0)),
        physical_memory_bytes=os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"),
        device="cpu",
        gpu="not_probed",
        scope="captured now; not attributed to historical runs",
        backend_versions={
            n: md.version(n) for n in ("numpy", "scipy", "polars", "statsmodels")
        },
    )


def storage_policy(store):
    return dict(
        artifact_usage_bytes=usage(store),
        quota_bytes=quota(store.state),
        snapshot="immutable native copy retained by project; bundle data inclusion is a separate choice",
        reference="version/URI/hash/schema only; access to original local project required without included data",
        retention="retain historical snapshots/artifacts; no automatic deletion/GC; archive does not reclaim disk",
        deletion="Deleting project/bundle may permanently lose snapshots and reproducibility; no delete operation here",
    )


def references(store, versions):
    result = []
    for d in store.state["datasets"]:
        if d["version_id"] not in versions or not d.get("import_metadata"):
            continue
        fp = store.manifest["artifacts"][d["snapshot_uri"]]
        cols = [
            dict(id=c["id"], type=c["type"]) for c in d["import_metadata"]["columns"]
        ]
        result.append(
            dict(
                version_id=d["version_id"],
                source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
                uri=d["snapshot_uri"],
                fingerprint={k: fp[k] for k in ("size", "sha256")},
                rows=d["import_metadata"]["row_count"],
                columns=cols,
                semantic_hash=digest(d.get("semantic_metadata", {})),
                column_schema_hash=digest(d["import_metadata"]["columns"]),
                access="local project snapshot or explicit included native data; no credential or network resolver",
            )
        )
    return result


def profile_recipe(store, record_id):
    r = next((r for r in store.state["results"] if r["id"] == record_id), None)
    if not r or "profile" not in r:
        return None
    p = r["profile"]
    if (
        p.get("target") != "dataset"
        or p.get("filters")
        or p.get("role") != "measurement"
        or p.get("numeric", {}).get("suppressed")
    ):
        return None
    if p["used_n"] > 10000 and p["scope"] == "sample":
        return None
    return dict(
        kind="profile",
        version=p["dataset_version"],
        recipe=dict(
            column_id=p["column_id"],
            sample=p["scope"] == "sample",
            ddof=p["numeric"]["ddof"],
            sample_limit=p["used_n"] if p["scope"] == "sample" else 10000,
        ),
        reference={
            k: p[k]
            for k in (
                "counts",
                "numeric",
                "used_n",
                "population_n",
                "scope",
                "sampling_method",
                "representative_sample",
            )
        },
    )


def workflow_recipe(store, record_id):
    r = next((r for r in store.state["results"] if r["id"] == record_id), None)
    if not r or r.get("neural", {}).get("schema") != "WorkflowRun/v1":
        return None
    from veri_ufku.modeling.repro_verify import workflow_projection
    from veri_ufku.storage.neural_store import load

    full = load(store, r)
    if full["status"] != "completed":
        return None
    return dict(
        kind="workflow",
        spec=full["workflow_spec"],
        reference=workflow_projection(full, lambda uri: store.path(uri)),
        recorded_signature=full["environment"],
    )


def plan(store, focus, include_data=False):
    if type(include_data) is not bool:
        raise ProjectError("Data inclusion açık boolean seçimi gerekir.")
    g = graph(store.state, store.manifest, focus)
    versions = {n["id"] for n in g["nodes"] if n["kind"] == "dataset"}
    replay = profile_recipe(store, focus) or workflow_recipe(store, focus)
    # A report can replay exactly one explicitly recorded supported analysis/run.
    if replay is None:
        r = next((r for r in store.state["results"] if r["id"] == focus), {})
        candidates = [
            profile_recipe(store, i) or workflow_recipe(store, i)
            for i in r.get("export", {}).get("lineage_record_ids", [])
        ]
        candidates = [c for c in candidates if c]
        if len(candidates) == 1:
            replay = candidates[0]
    cleaned, changes = sanitize(dict(lineage=g, replay=replay))
    # Altered replay config/reference is not silently executed under different semantics.
    runnable = replay is not None and cleaned["replay"] == replay
    refs = references(store, versions)
    if replay and replay["kind"] == "workflow":
        for n in replay["spec"]["nodes"]:
            if n["kind"] == "source":
                versions.add(n["params"]["version_id"])
        for c in replay["spec"]["cases"]:
            versions.update(c["sources"].values())
        refs = references(store, versions)
    unavailable_versions = sorted(versions - {r["version_id"] for r in refs})
    if include_data and unavailable_versions:
        raise ProjectError(
            "Legacy dataset snapshot schema/RowId metadata kaydedilmemiş; data inclusion desteklenmiyor. Reference-only lineage kullanın."
        )
    if len(refs) > 32:
        raise ProjectError("Repro32 dataset bütçesi; daha dar focus seçin.")
    estimated = sum(r["fingerprint"]["size"] for r in refs) if include_data else 0
    if estimated > MAX_TOTAL:
        raise ProjectError("Repro data128MiB önkontrolü aşıldı.")
    return dict(
        schema="ReproPlan/v1",
        focus=focus,
        project_id=store.manifest["project_id"],
        commit_id=store.commit_id,
        lineage=cleaned["lineage"],
        references=refs,
        unavailable_reference_versions=unavailable_versions,
        replay=cleaned["replay"] if runnable else None,
        rerun_supported=runnable,
        rerun_reason="profile Decimal80 / bounded workflow numeric projection; compare defined fields only"
        if runnable
        else "No supported recorded recipe or redaction changed configuration/reference; lineage/integrity only",
        include_data=include_data,
        estimated_data_bytes=estimated,
        redactions=changes,
        storage=storage_policy(store),
        sensitive_content="Aggregates/config may be sensitive. Data inclusion can contain personal/raw values and native row identifiers; user review required. Pattern scan is not a universal secret detector.",
        retention="No automatic expiration or deletion. Reference-only bundle does not preserve source bytes.",
        captured_hardware=hardware(),
        preview_hash="",
    )


def preview(store, focus, include_data=False):
    p = plan(store, focus, include_data)
    p["preview_hash"] = digest(
        {k: v for k, v in p.items() if k not in ("preview_hash", "captured_hardware")}
    )
    return p


def scan_data(path, control):
    import polars as pl

    schema = pl.read_parquet_schema(path)
    if any(SECRET_KEY.search(n) for n in schema):
        raise ProjectError(
            "Secret adlı veri kolonu: raw snapshot bundle dışında bırakılmalı."
        )
    for name, dt in schema.items():
        if (
            dt.is_nested()
            and not (name == "__vu_missing_fields" and dt == pl.List(pl.String))
        ) or dt in (pl.Binary, pl.Object):
            raise ProjectError(
                "Repro data inclusion nested/binary taraması desteklenmiyor; reference-only kullanın."
            )
    rows = 0
    for batch in pl.scan_parquet(path).collect_batches(chunk_size=512):
        control.check()
        rows += batch.height
        if rows > 10000:
            raise ProjectError("Repro inclusion10000row sınırı.")
        for n, dt in schema.items():
            if dt == pl.String and any(
                v and (SENSITIVE.search(v) or LOCATION.search(v))
                for v in batch[n].to_list()
            ):
                raise ProjectError(
                    "Secret örüntüsü içeren snapshot bundle dışında bırakılmalı; veri düzeltilmedi."
                )


def build(
    store, focus, include_data, expected_preview, workspace, destination, control=None
):
    control = control or Control()
    p = preview(store, focus, include_data)
    if p["preview_hash"] != expected_preview:
        raise ProjectError(
            "Repro önizleme/proje değişti; yeniden redaction önizlemesi açın."
        )
    env = environment()
    from veri_ufku.learning.catalog import Catalog

    catalog = Catalog()
    files = {
        "lineage.json": raw(p["lineage"]),
        "config.json": raw(dict(replay=p["replay"], focus=focus)),
        "reference-report.json": raw(
            p["replay"]["reference"]
            if p["replay"]
            else dict(status="not_rerunnable; no reference invented")
        ),
        "environment.lock.json": raw(env),
        "hardware.json": raw(p["captured_hardware"]),
        "redaction-preview.json": raw(
            dict(
                redactions=p["redactions"],
                raw_data_included=include_data,
                warning=p["sensitive_content"],
            )
        ),
        "storage-policy.json": raw(p["storage"]),
        "requirements.lock": (
            "\n".join(k + "==" + v for k, v in env["packages"].items()) + "\n"
        ).encode(),
    }
    files["README.txt"] = (
        b"Veri_Ufku safe data bundle. Open verifies hashes only; explicit re-run action is separate. No executable model or Python object is imported. Same trusted build/environment required; lock is not an offline installer. Seed alone is insufficient. Integrity hashes detect corruption, not malicious re-signing. Raw data inclusion is explicit and can expose values. Paths and credentials are not access grants. Retention is manual; no automatic deletion. Unsupported schemas/backends/platforms fail closed. Tolerances compare only documented numeric projections; no blanket scientific equivalence claim."
    )
    binary = {}
    for r in p["references"]:
        path = store.path(r["uri"])
        if hash_artifact(path, control) != r["fingerprint"]:
            raise ProjectError("Dataset bytes değişti; bundle güncel sayılmadı.")
        if include_data:
            scan_data(path, control)
            d = next(
                d for d in store.state["datasets"] if d["version_id"] == r["version_id"]
            )
            original = d.get("semantic_metadata", {})
            cleaned, _ = sanitize(original)
            if cleaned != original:
                raise ProjectError(
                    "Snapshot metadata redaction re-run anlamını değiştirir; reference-only seçin."
                )
            r["included_semantics"] = cleaned
            name = "data/" + r["version_id"].removeprefix("dv:") + ".parquet"
            binary[name] = path
            r["included_member"] = name
    manifest = dict(
        schema="ReproBundle/v1",
        project_schema=SCHEMA_VERSION,
        bundle_id="bundle:" + uid(),
        created_at=datetime.now(UTC).isoformat(),
        project_id=p["project_id"],
        commit_id=p["commit_id"],
        focus=focus,
        references=p["references"],
        include_data=include_data,
        rerun_supported=p["rerun_supported"],
        rerun_reason=p["rerun_reason"],
        methods=dict(profile=1, workflow=1),
        help=dict(
            content_version=catalog.data["content_version"],
            articles={
                k: catalog.articles[k]["content_version"]
                for k in (
                    "repro-lineage",
                    "repro-snapshot",
                    "repro-environment",
                    "repro-tolerance",
                    "repro-record",
                )
            },
        ),
        safe_artifacts="closed config/reference aggregate JSON and opt-in native snapshots only; arbitrary model object or executable never included",
        members={},
    )
    for n, value in files.items():
        manifest["members"][n] = dict(
            size=len(value), sha256=hashlib.sha256(value).hexdigest()
        )
    for n, path in binary.items():
        manifest["members"][n] = hash_artifact(path, control)
    metadata = raw(manifest)
    if len(metadata) > MAX_METADATA or sum(
        fp["size"] for fp in manifest["members"].values()
    ) > min(MAX_TOTAL, control.budget.temp_disk_bytes // 2):
        raise ProjectError("Bundle metadata/storage budget aşıldı.")
    path = Path(workspace) / "repro.vurepro"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", metadata)
        for n, value in files.items():
            control.check()
            z.writestr(n, value)
        for n, source in binary.items():
            with source.open("rb") as inp, z.open(n, "w") as out:
                while chunk := inp.read(1024**2):
                    control.check()
                    out.write(chunk)
    opened = open_bundle(path, control)
    control.disk(workspace, force=True)
    receipt = publish(path, destination, store.root, control)
    return dict(
        schema="ReproReceipt/v1",
        **receipt,
        bundle_id=manifest["bundle_id"],
        focus=focus,
        include_data=include_data,
        member_count=len(opened["manifest"]["members"]),
        preview_hash=expected_preview,
        reference_hash=digest(p["replay"]["reference"]) if p["replay"] else None,
    )


def parse(data):
    def pairs(items):
        obj = {}
        for k, v in items:
            if k in obj:
                raise ProjectError("Duplicate JSON key reddi.")
            obj[k] = v
        return obj

    try:
        return json.loads(
            data,
            object_pairs_hook=pairs,
            parse_constant=lambda x: (_ for _ in ()).throw(ValueError()),
        )
    except (ValueError, UnicodeError, RecursionError):
        raise ProjectError("Safe JSON okunamadı.") from None


def open_bundle(path, control=None):
    control = control or Control()
    try:
        if Path(path).is_symlink() or Path(path).stat().st_size > MAX_TOTAL:
            raise ProjectError("Bundle normal dosya/128MiB sınırı.")
        with zipfile.ZipFile(path) as z:
            infos = z.infolist()
            if (
                len(infos) > 256
                or len({i.filename for i in infos}) != len(infos)
                or sum(i.file_size for i in infos) > MAX_TOTAL
            ):
                raise ProjectError("Bundle duplicate/member/size bütçesi.")
            for i in infos:
                if (
                    i.flag_bits & 1
                    or stat.S_ISLNK(i.external_attr >> 16)
                    or i.filename.startswith("/")
                    or ".." in Path(i.filename).parts
                    or "\\" in i.filename
                    or i.is_dir()
                ):
                    raise ProjectError("Bundle path/encrypted/symlink reddi.")
            if z.getinfo("manifest.json").file_size > MAX_METADATA:
                raise ProjectError("Manifest size bütçesi.")
            m = parse(z.read("manifest.json"))
            if (
                m.get("schema") != "ReproBundle/v1"
                or m.get("project_schema") != SCHEMA_VERSION
            ):
                raise ProjectError(
                    "Bundle migration/schema desteklenmiyor; orijinal dosya korundu."
                )
            required = {
                "lineage.json",
                "config.json",
                "reference-report.json",
                "environment.lock.json",
                "hardware.json",
                "redaction-preview.json",
                "storage-policy.json",
                "requirements.lock",
                "README.txt",
            }
            if (
                m.get("methods") != dict(profile=1, workflow=1)
                or type(m.get("include_data")) is not bool
                or type(m.get("rerun_supported")) is not bool
                or not isinstance(m.get("references"), list)
                or len(m["references"]) > 32
            ):
                raise ProjectError(
                    "Bundle method/version/reference kapalı şema desteklenmiyor."
                )
            expected_names = set(required)
            seen = set()
            for ref in m["references"]:
                entity_id(ref["version_id"], "dv")
                entity_id(ref["source_snapshot_id"], "snapshot")
                relative(ref["uri"])
                fingerprint(ref["fingerprint"])
                if (
                    ref["version_id"] in seen
                    or type(ref["rows"]) is not int
                    or not 0 <= ref["rows"] <= 1000000
                ):
                    raise ProjectError("Bundle duplicate/reference rows geçersiz.")
                seen.add(ref["version_id"])
                for col in ref["columns"]:
                    entity_id(col["id"], "col")
                    if set(col) != {"id", "type"} or not isinstance(col["type"], str):
                        raise ProjectError("Reference column schema geçersiz.")
                if m["include_data"]:
                    name = "data/" + ref["version_id"].removeprefix("dv:") + ".parquet"
                    if ref.get("included_member") != name:
                        raise ProjectError("Included member reference geçersiz.")
                    expected_names.add(name)
                elif "included_member" in ref:
                    raise ProjectError("Data inclusion consent uyuşmuyor.")
            if set(m["members"]) != expected_names:
                raise ProjectError("Bundle closed members alanı geçersiz.")
            for fp in m["members"].values():
                fingerprint(fp)
            if set(m["members"]) | {"manifest.json"} != {i.filename for i in infos}:
                raise ProjectError("Bundle member manifest uyuşmuyor.")
            payload = {}
            for i in infos:
                if i.filename == "manifest.json":
                    continue
                if not re.fullmatch(
                    r"(?:[A-Za-z][A-Za-z0-9.-]*|data/[0-9a-f-]{36}\.parquet)",
                    i.filename,
                ):
                    raise ProjectError("Bundle closed member names reddi.")
                fp = m["members"][i.filename]
                if i.file_size != fp["size"]:
                    raise ProjectError("Artifact size değişti.")
                if not i.filename.startswith("data/") and i.file_size > MAX_METADATA:
                    raise ProjectError("Metadata8MiB sınırı.")
                sha = hashlib.sha256()
                buffer = bytearray()
                with z.open(i) as inp:
                    while chunk := inp.read(1024**2):
                        control.check()
                        sha.update(chunk)
                        if not i.filename.startswith("data/"):
                            buffer.extend(chunk)
                if sha.hexdigest() != fp["sha256"]:
                    raise ProjectError("Bundle artifact hash bozuk/değişti.")
                if i.filename.endswith(".json") and not i.filename.startswith("data/"):
                    payload[i.filename] = parse(buffer)
            # Configuration is data only. Reopening never loads modules from the archive.
            from veri_ufku.modeling.repro_verify import validate_replay

            validate_replay(payload["config.json"]["replay"])
            return dict(
                manifest=m,
                payload=payload,
                bundle_fingerprint=hash_artifact(path, control),
                status="integrity_verified; no execution",
            )
    except (KeyError, TypeError, zipfile.BadZipFile, RuntimeError, OSError):
        raise ProjectError(
            "Bundle safe format/member okunamadı; çalışma başlatılmadı."
        ) from None
