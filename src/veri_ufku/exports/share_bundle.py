"""Local review/share containers, strict safe opening and semantic diff; no code loading."""

import copy
import io
import json
import math
import stat
import zipfile
from pathlib import Path

from veri_ufku.exports.share_privacy import LIMITATIONS, sanitize, scan, terms
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import (
    SCHEMA_VERSION,
    ProjectError,
    decode,
    encode,
    relative,
    uid,
    validate_manifest,
)
from veri_ufku.storage.project_store import file_hash

MAX_TOTAL = 64 * 1024**2
MAX_MEMBERS = 128
KINDS = ("metadata-only", "redacted-sample", "full-copy")
CATEGORIES = ("schema", "operations", "params", "runs_metrics", "learning_notes")


def spec(raw):
    if not isinstance(raw, dict) or set(raw) != {
        "mode",
        "version",
        "rows",
        "keep_numeric",
        "sensitive_terms",
    }:
        raise ProjectError(
            "ShareSpec/v1 kapalı mode/version/rows/keep_numeric/sensitive_terms alanları gerekli."
        )
    if (
        raw["mode"] not in KINDS
        or type(raw["rows"]) is not int
        or not 1 <= raw["rows"] <= 1000
    ):
        raise ProjectError("Share mode veya ilk1..1000satır sınırı geçersiz.")
    if (
        not isinstance(raw["version"], str)
        or not isinstance(raw["keep_numeric"], list)
        or len(raw["keep_numeric"]) > 64
        or len(set(raw["keep_numeric"])) != len(raw["keep_numeric"])
    ):
        raise ProjectError("Sample sürümü ve açık numeric ColumnId listesi gerekli.")
    terms(raw["sensitive_terms"])
    return copy.deepcopy(raw)


def entity_binding(value, artifacts):
    refs = {}

    def visit(v):
        if isinstance(v, str) and v in artifacts:
            meta = artifacts[v].get("metadata", artifacts[v])
            refs[v] = {k: meta[k] for k in ("size", "sha256")}
        elif isinstance(v, dict):
            for x in v.values():
                visit(x)
        elif isinstance(v, list):
            for x in v:
                visit(x)

    visit(value)
    return dict(entity_hash=digest(dict(value=value, artifacts=refs)), artifacts=refs)


def projection(state, origin, sensitive=(), artifacts=None):
    artifacts = artifacts or {}
    raw = {k: {} for k in CATEGORIES}
    for d in state["datasets"]:
        raw["schema"][d["version_id"]] = dict(
            dataset_id=d["dataset_id"],
            source_id=d["source_id"],
            columns=d.get("import_metadata", {}).get("columns", []),
            semantics=d.get("semantic_metadata", {}),
            rules=d.get("schema_contract", {}),
            recorded_hash=digest(d),
            snapshot_uri=d["snapshot_uri"],
            snapshot_fingerprint=entity_binding(d, artifacts)["artifacts"].get(
                d["snapshot_uri"]
            ),
        )
    for o in state["operations"]:
        raw["operations"][o["id"]] = dict(value=o, recorded_hash=digest(o))
        raw["params"][o["id"]] = dict(
            value=o.get("spec", o.get("parameters", {})),
            recorded_hash=digest(o.get("spec", o.get("parameters", {}))),
        )
    for r in state["results"]:
        key = next(
            (
                k
                for k in (
                    "profile",
                    "quality",
                    "monitoring",
                    "scenario",
                    "unsupervised",
                    "baseline",
                    "analysis",
                    "search",
                    "chart",
                    "time_series",
                    "neural",
                    "scientific_report",
                    "learning_lab",
                    "review_event",
                )
                if k in r
            ),
            None,
        )
        v = r.get(key, {}) if key else {}
        raw["runs_metrics"][r["id"]] = dict(
            kind=key,
            capability=r.get("capability_id"),
            dataset_versions=r["dataset_version_ids"],
            record_hash=digest(r),
            **{
                k: v[k]
                for k in (
                    "run_id",
                    "status",
                    "metrics",
                    "cv_summary",
                    "summary",
                    "statistics",
                    "numeric",
                    "value",
                )
                if k in v
            },
        )
        if key != "review_event":
            raw["params"][r["id"]] = dict(
                value=v.get("spec", v.get("params", {})),
                recorded_hash=digest(v.get("spec", v.get("params", {}))),
            )
        if key == "review_event":
            raw["learning_notes"][r["id"]] = v
    raw["learning_notes"]["project-learning-preferences"] = state["help_preferences"]
    entities = {}
    for kind, key in (
        ("dataset", "datasets"),
        ("operation", "operations"),
        ("run", "results"),
    ):
        for v in state[key]:
            ident = v.get("version_id", v.get("id"))
            entities[kind + ":" + ident] = dict(
                kind=kind, id=ident, **entity_binding(v, artifacts)
            )
    entities["project:" + origin["project_id"]] = dict(
        kind="project", id=origin["project_id"], **entity_binding(state, artifacts)
    )
    findings = []
    safe = sanitize(raw, sensitive, findings)
    return dict(origin=origin, categories=safe, entities=entities), findings


def read_artifact(path, control, sensitive=()):
    path = Path(path)
    control.check()
    if path.stat().st_size > 32 * 1024**2:
        raise ProjectError("Artifact32MiB sınırı; full copy unavailable.")
    data = path.read_bytes()
    if data[:4] == b"PAR1" and data[-4:] == b"PAR1":
        import pyarrow.parquet as pq

        pf = pq.ParquetFile(io.BytesIO(data))
        if pf.metadata.num_rows > 10000 or len(pf.schema_arrow) > 80:
            raise ProjectError("Parquet tarama10000row/80column sınırı.")

        def metadata_text(meta):
            return {
                k.decode("utf-8", errors="replace"): v.decode("utf-8", errors="replace")
                for k, v in (meta or {}).items()
                if k != b"ARROW:schema"
            }

        values = scan(metadata_text(pf.metadata.metadata), sensitive)
        values += scan(metadata_text(pf.schema_arrow.metadata), sensitive)
        for field in pf.schema_arrow:
            values += scan(metadata_text(field.metadata), sensitive)
        for batch in pf.iter_batches(batch_size=256):
            control.check()
            # Scan all cells, including source keys. Never materialize full table.
            values.extend(
                scan(json.loads(json.dumps(batch.to_pylist(), default=str)), sensitive)
            )
            if len(values) > 1000:
                raise ProjectError("Artifact tarama1000bulgu sınırı.")
        return data, values, "parquet"
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        return data, [dict(field="artifact", reason="unscannable-binary")], "opaque"
    if "\x00" in text:
        return data, [dict(field="artifact", reason="unscannable-binary")], "opaque"
    if text.lstrip().startswith(("{", "[")):
        try:
            obj = decode(data)
        except ProjectError:
            obj = text
    else:
        obj = text
    found = scan(obj, sensitive)
    from veri_ufku.exports.repro import SECRET_KEY

    if (
        isinstance(obj, str)
        and obj.splitlines()
        and SECRET_KEY.search(obj.splitlines()[0])
    ):
        found.append(dict(field="header", reason="secret-key"))
    return data, found, "text"


def prepare(request, raw_spec, workspace, control=None):
    control = control or Control()
    s = spec(raw_spec)
    state = copy.deepcopy(request["state"])
    origin = request["origin"]
    p, redactions = projection(
        state, origin, s["sensitive_terms"], request["artifacts"]
    )
    findings = []
    members = {}
    inclusion = []
    sample_preview = []
    # External locations are disarmed explicitly, not relinked at open time.
    for source in state["sources"]:
        source["path"] = "/unresolved-source/" + source["id"].split(":")[-1]
    if s["mode"] == "full-copy":
        findings.extend(scan(state, s["sensitive_terms"]))
        if len(request["artifacts"]) + 3 > MAX_MEMBERS:
            raise ProjectError("Tam kopya artifact128member sınırı.")
        for uri, ref in request["artifacts"].items():
            control.check()
            if file_hash(Path(ref["path"])) != {
                k: ref["metadata"][k] for k in ("size", "sha256")
            }:
                raise ProjectError("Paylaşım artifact hash değişmiş.")
            data, found, kind = read_artifact(
                ref["path"], control, s["sensitive_terms"]
            )
            # Explicit terms are also applied to known textual/batch formats.
            if s["sensitive_terms"] and kind == "text":
                found += scan(data.decode(), s["sensitive_terms"])
            findings.extend(dict(field=uri, reason=f["reason"]) for f in found)
            members["artifacts/" + uri] = data
            inclusion.append(dict(member="artifacts/" + uri, size=len(data), kind=kind))
        members["project.json"] = encode(
            dict(
                state=state,
                artifacts={k: r["metadata"] for k, r in request["artifacts"].items()},
            )
        )
    elif s["mode"] == "redacted-sample":
        import pyarrow as pa
        import pyarrow.parquet as pq

        d = next(
            (d for d in state["datasets"] if d["version_id"] == s["version"]), None
        )
        if not d:
            raise ProjectError("Sample için projedeki dataset sürümünü seçin.")
        cols = d.get("import_metadata", {}).get("columns", [])
        if len(cols) > 64 or not set(s["keep_numeric"]) <= {c["id"] for c in cols}:
            raise ProjectError("Sample kolon sınırı/ColumnId geçersiz.")
        ref = request["artifacts"][d["snapshot_uri"]]
        if ref["metadata"]["size"] > MAX_TOTAL:
            raise ProjectError("Sample snapshot64MiB sınırı; metadata-only seçin.")
        if file_hash(Path(ref["path"])) != {
            k: ref["metadata"][k] for k in ("size", "sha256")
        }:
            raise ProjectError("Sample snapshot değişmiş.")
        pf = pq.ParquetFile(ref["path"])
        internal = [
            n
            for n in ("__vu_row_id", "__vu_source_record_id")
            if n in pf.schema_arrow.names
        ]
        if len(internal) != 2:
            raise ProjectError("Sample kaynak kimliği eksik; uydurulmaz.")
        names = internal + [c["name"] for c in cols]
        batch = next(pf.iter_batches(batch_size=s["rows"], columns=names), None)
        rows = batch.to_pylist() if batch else []
        schema = [pa.field(n, pa.string()) for n in internal]
        for i, c in enumerate(cols):
            field = pf.schema_arrow.field(c["name"])
            keep = c["id"] in s["keep_numeric"]
            if keep and not (
                pa.types.is_integer(field.type)
                or pa.types.is_floating(field.type)
                or pa.types.is_boolean(field.type)
            ):
                raise ProjectError(
                    "Yalnız açık numeric/bool kolon paylaşılabilir; kategori/metin tamamı maskeli."
                )
            alias = "column-" + str(i + 1)
            for row in rows:
                val = row.pop(c["name"])
                row[alias] = val if keep else "[redacted]"
            schema.append(pa.field(alias, field.type if keep else pa.string()))
        # Source identities are preserved verbatim; a sensitive identity blocks sharing.
        for row in rows:
            findings.extend(scan({n: row[n] for n in internal}, s["sensitive_terms"]))
        sample_preview = [
            {
                k: (str(v) if isinstance(v, float) and not math.isfinite(v) else v)
                for k, v in row.items()
            }
            for row in rows[:10]
        ]
        table = pa.Table.from_pylist(rows, schema=pa.schema(schema))
        out = io.BytesIO()
        pq.write_table(table, out)
        members["sample.parquet"] = out.getvalue()
        sample = dict(
            version_id=d["version_id"],
            source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
            source_fingerprint={k: ref["metadata"][k] for k in ("size", "sha256")},
            columns=[
                dict(
                    id=c["id"],
                    alias="column-" + str(i + 1),
                    masked=c["id"] not in s["keep_numeric"],
                )
                for i, c in enumerate(cols)
            ],
            rows=len(rows),
            population=d["import_metadata"]["row_count"],
            selection="first-N; no random or complete-data claim",
        )
        if file_hash(Path(ref["path"])) != {
            k: ref["metadata"][k] for k in ("size", "sha256")
        }:
            raise ProjectError("Sample snapshot okuma sırasında değişti.")
        members["sample-reference.json"] = encode(sample)
        inclusion.append(
            dict(
                member="sample.parquet",
                size=len(members["sample.parquet"]),
                rows=len(rows),
                columns=sample["columns"],
            )
        )
    members["projection.json"] = encode(p)
    if len(members["projection.json"]) > 4 * 1024**2:
        raise ProjectError("Share projection4MiB sınırı; daha dar proje gerekli.")
    if (
        any(len(v) > MAX_TOTAL for v in members.values())
        or sum(map(len, members.values())) > MAX_TOTAL
    ):
        raise ProjectError("Share64MiB toplam bütçe sınırı.")
    blocked = any(
        f["reason"]
        in (
            "secret-key",
            "secret-pattern",
            "unscannable-binary",
            "external-location",
            "sensitive-key",
            "explicit-sensitive-term",
        )
        for f in findings
    )
    blocked = blocked or (s["mode"] != "full-copy" and bool(findings))
    preview = dict(
        schema="SharePreview/v1",
        origin=origin,
        mode=s["mode"],
        projection=p,
        inclusion=inclusion,
        findings=findings,
        redactions=redactions,
        blocked=blocked,
        sample_preview=sample_preview,
        pii_found=any(f["reason"] == "pii-pattern" for f in findings),
        limitations=LIMITATIONS,
        member_hashes={
            n: dict(size=len(v), sha256=__import__("hashlib").sha256(v).hexdigest())
            for n, v in members.items()
        },
    )
    if len(encode(preview)) > 4 * 1024**2:
        raise ProjectError("Share preview4MiB sınırı.")
    preview["preview_hash"] = digest(preview)
    return preview, members


def build(
    request,
    parameters,
    workspace,
    destination,
    preview_hash,
    allow_pii=False,
    control=None,
):
    from veri_ufku.exports.files import publish

    control = control or Control()
    p, members = prepare(request, parameters, workspace, control)
    if p["preview_hash"] != preview_hash or p["blocked"]:
        raise ProjectError(
            "Önizleme değişti veya secret/taranamayan içerik var; paylaşım reddedildi."
        )
    if p["pii_found"] and not allow_pii:
        raise ProjectError(
            "Tam kopyada PII bulgusu; explicit inclusion onayı gerekli veya redacted/metadata seçin."
        )
    manifest = dict(
        schema="ReviewShare/v1",
        project_schema=SCHEMA_VERSION,
        bundle_id="bundle:" + uid(),
        mode=p["mode"],
        origin=p["origin"],
        preview_hash=preview_hash,
        members=p["member_hashes"],
        limitations=LIMITATIONS,
        pii_included=p["pii_found"],
        inclusion=p["inclusion"],
    )
    target = Path(workspace) / "review-share.vushare"
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", encode(manifest))
        for n, data in members.items():
            control.check()
            z.writestr(n, data)
    control.disk(workspace, force=True)
    opened = open_bundle(target, control)
    control.check()
    receipt = publish(target, destination, request["project_root"], control)
    return dict(
        action="bundle",
        status="exported",
        receipt=receipt,
        manifest=opened["manifest"],
        limitations=LIMITATIONS,
    )


def open_bundle(path, control=None):
    control = control or Control()
    try:
        path = Path(path)
        if path.is_symlink() or path.stat().st_size > MAX_TOTAL:
            raise ProjectError("Share dosyası64MiB/symlink sınırı.")
        before = file_hash(path)
        with zipfile.ZipFile(path) as z:
            infos = z.infolist()
            if (
                len(infos) > MAX_MEMBERS
                or len({i.filename for i in infos}) != len(infos)
                or sum(i.file_size for i in infos) > MAX_TOTAL
            ):
                raise ProjectError("Share duplicate/member/expanded size sınırı.")
            for i in infos:
                if (
                    i.is_dir()
                    or i.flag_bits & 1
                    or stat.S_ISLNK(i.external_attr >> 16)
                    or i.filename.startswith("/")
                    or ".." in Path(i.filename).parts
                    or "\\" in i.filename
                ):
                    raise ProjectError("Share güvensiz member/path reddi.")
            m = decode(z.read("manifest.json"))
            if (
                set(m)
                != {
                    "schema",
                    "project_schema",
                    "bundle_id",
                    "mode",
                    "origin",
                    "preview_hash",
                    "members",
                    "limitations",
                    "pii_included",
                    "inclusion",
                }
                or type(m.get("pii_included")) is not bool
            ):
                raise ProjectError("Share manifest kapalı alanları geçersiz.")
            from veri_ufku.storage.project_model import (
                entity_id,
                fingerprint,
                identifier,
            )

            identifier(m["bundle_id"])
            if (
                set(m["origin"]) != {"project_id", "commit_id", "schema_version"}
                or m["origin"]["schema_version"] != SCHEMA_VERSION
            ):
                raise ProjectError("Share kaynak proje şeması geçersiz.")
            identifier(m["origin"]["project_id"])
            identifier(m["origin"]["commit_id"])
            for fp in m["members"].values():
                fingerprint(fp)
            if (
                m.get("schema") != "ReviewShare/v1"
                or m.get("project_schema") != SCHEMA_VERSION
                or m.get("mode") not in KINDS
                or m.get("limitations") != LIMITATIONS
            ):
                raise ProjectError("Share şema/yöntem/migration desteklenmiyor.")
            expected = {"projection.json"}
            if m["mode"] == "redacted-sample":
                expected |= {"sample.parquet", "sample-reference.json"}
            if m["mode"] == "full-copy":
                expected.add("project.json")
                for n in m["members"]:
                    if n.startswith("artifacts/"):
                        relative(n.removeprefix("artifacts/"))
                        expected.add(n)
            if set(m["members"]) != expected or set(z.namelist()) != expected | {
                "manifest.json"
            }:
                raise ProjectError("Share closed member set uyuşmuyor.")
            payload = {}
            for name in expected:
                control.check()
                data = z.read(name)
                if (
                    dict(
                        size=len(data),
                        sha256=__import__("hashlib").sha256(data).hexdigest(),
                    )
                    != m["members"][name]
                ):
                    raise ProjectError("Share artifact hash bozuk.")
                payload[name] = data
            p = decode(payload["projection.json"])
            if p["origin"] != m["origin"] or set(p["categories"]) != set(CATEGORIES):
                raise ProjectError("Share köken/projection uyuşmuyor.")
            if m["mode"] == "redacted-sample":
                import pyarrow as pa
                import pyarrow.parquet as pq

                ref = decode(payload["sample-reference.json"])
                entity_id(ref["version_id"], "dv")
                entity_id(ref["source_snapshot_id"], "snapshot")
                fingerprint(ref["source_fingerprint"])
                cols = ref["columns"]
                if not 1 <= len(cols) <= 64 or len({c["id"] for c in cols}) != len(
                    cols
                ):
                    raise ProjectError("Sample ColumnId listesi geçersiz.")
                for i, c in enumerate(cols):
                    entity_id(c["id"], "col")
                    if (
                        set(c) != {"id", "alias", "masked"}
                        or c["alias"] != "column-" + str(i + 1)
                        or type(c["masked"]) is not bool
                    ):
                        raise ProjectError("Sample alias/mask sözleşmesi geçersiz.")
                pf = pq.ParquetFile(io.BytesIO(payload["sample.parquet"]))
                if (
                    pf.metadata.num_rows != ref["rows"]
                    or not 0 <= ref["rows"] <= 1000
                    or ref["population"] < ref["rows"]
                    or pf.schema_arrow.names
                    != ["__vu_row_id", "__vu_source_record_id"]
                    + [c["alias"] for c in cols]
                ):
                    raise ProjectError("Sample satır/şema uyuşmuyor.")
                table = pf.read()
                rows = table.to_pylist()
                for row in rows:
                    entity_id(row["__vu_row_id"], "row")
                    if not isinstance(row["__vu_source_record_id"], str) or scan(
                        {"identity": row["__vu_source_record_id"]}
                    ):
                        raise ProjectError("Sample source identity geçersiz/hassas.")
                if len({r["__vu_row_id"] for r in rows}) != len(rows):
                    raise ProjectError("Sample RowId duplicate reddi.")
                for c in cols:
                    field = pf.schema_arrow.field(c["alias"])
                    if c["masked"]:
                        if not pa.types.is_string(field.type) or any(
                            r[c["alias"]] != "[redacted]" for r in rows
                        ):
                            raise ProjectError("Sample maske doğrulanamadı.")
                    elif not (
                        pa.types.is_integer(field.type)
                        or pa.types.is_floating(field.type)
                        or pa.types.is_boolean(field.type)
                    ):
                        raise ProjectError("Sample numeric yetenek uyuşmuyor.")
            if m["mode"] == "full-copy":
                project = decode(payload["project.json"])
                if set(project) != {"state", "artifacts"}:
                    raise ProjectError("Full native container kapalı alan hatası.")
                # Validate the logical native project without constructing/opening any runtime.
                from datetime import UTC, datetime

                validate_manifest(
                    dict(
                        format_version=SCHEMA_VERSION,
                        project_id=m["origin"]["project_id"],
                        commit_id=m["origin"]["commit_id"],
                        parent_commit=None,
                        state=project["state"],
                        artifacts=project["artifacts"],
                        created_at=datetime.now(UTC).isoformat(),
                        environment={},
                        migration=[],
                    )
                )
                if {"artifacts/" + u for u in project["artifacts"]} != expected - {
                    "projection.json",
                    "project.json",
                }:
                    raise ProjectError("Full artifact manifest uyuşmuyor.")
                for uri, meta in project["artifacts"].items():
                    if {k: meta[k] for k in ("size", "sha256")} != m["members"][
                        "artifacts/" + uri
                    ]:
                        raise ProjectError("Native manifest hash bozuk.")
                artifact_findings = []
                import tempfile

                with tempfile.TemporaryDirectory(prefix="share-verify-") as scratch:
                    for uri in project["artifacts"]:
                        control.check()
                        path_copy = Path(scratch) / "artifact"
                        path_copy.write_bytes(payload["artifacts/" + uri])
                        _, detected, _ = read_artifact(path_copy, control)
                        artifact_findings.extend(detected)
                        control.disk(scratch)
                found = scan(project["state"]) + artifact_findings
                if any(f["reason"] != "pii-pattern" for f in found) or (
                    found and not m["pii_included"]
                ):
                    raise ProjectError("Full share secret/inclusion taraması reddi.")
            if file_hash(path) != before:
                raise ProjectError("Share açılırken değişti.")
            return dict(
                manifest=m,
                projection=p,
                payload=payload,
                fingerprint=before,
                status="integrity_verified; no execution",
            )
    except (
        KeyError,
        TypeError,
        OSError,
        zipfile.BadZipFile,
        RuntimeError,
        UnicodeError,
    ):
        raise ProjectError(
            "Share safe container okunamadı; veri çalıştırılmadı/değişmedi."
        ) from None


def identity_sets(opened):
    columns = {
        c["id"]
        for d in opened["projection"]["categories"]["schema"].values()
        for c in d.get("columns", [])
        if isinstance(c, dict) and "id" in c
    }
    rows = set()
    payload = opened.get("payload", {})
    names = ["sample.parquet"] if "sample.parquet" in payload else []
    if "project.json" in payload:
        native = decode(payload["project.json"])
        names += ["artifacts/" + d["snapshot_uri"] for d in native["state"]["datasets"]]
    if names:
        import pyarrow.parquet as pq

        for name in set(names):
            pf = pq.ParquetFile(io.BytesIO(payload[name]))
            if "__vu_row_id" in pf.schema_arrow.names:
                for b in pf.iter_batches(batch_size=256, columns=["__vu_row_id"]):
                    rows.update(b.column(0).to_pylist())
    return columns, rows


def compare(left, right):
    a, b = left["projection"], right["projection"]
    same = a["origin"]["project_id"] == b["origin"]["project_id"]
    left_columns, left_rows = identity_sets(left)
    right_columns, right_rows = identity_sets(right)
    duplicate_columns = sorted(left_columns & right_columns) if not same else []
    duplicate_rows = sorted(left_rows & right_rows) if not same else []
    collisions = dict(
        column_ids=duplicate_columns[:1000],
        row_ids=duplicate_rows[:1000],
        column_count=len(duplicate_columns),
        row_count=len(duplicate_rows),
        detail_limit=1000,
        row_scope="included sample/full snapshot only; metadata-only row collisions not observable; detail first1000, full count retained",
    )
    result = {}
    for category in CATEGORIES:
        x, y = a["categories"][category], b["categories"][category]
        result[category] = [
            dict(
                id=k,
                change="added"
                if k not in x
                else "removed"
                if k not in y
                else "changed",
                identity_collision=not same and k in x and k in y,
                left=x.get(k),
                right=y.get(k),
            )
            for k in sorted(set(x) | set(y))
            if x.get(k) != y.get(k) or (not same and k in x and k in y)
        ]
    return dict(
        action="diff",
        same_origin=same,
        identity_collisions=collisions,
        left_origin=a["origin"],
        right_origin=b["origin"],
        left_fingerprint=left["fingerprint"],
        right_fingerprint=right["fingerprint"],
        categories=result,
        policy="review-only; keep-local / incoming-as-separate-fork / defer; no automatic apply or last-write-wins",
        limitations=LIMITATIONS,
    )
