"""Bounded report references reuse the existing immutable ProjectStore transaction."""

import base64
import copy
import os
from pathlib import Path

from veri_ufku.exports.report_contracts import LIMITATIONS, RECORD_KINDS, recipe, redact
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError, encode, uid
from veri_ufku.storage.project_model import digest as byte_digest
from veri_ufku.storage.project_store import file_hash
from veri_ufku.storage.validation_store import prior_uses, transaction


def file_hash_bytes(raw):
    import hashlib

    return dict(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())


MAX_TOTAL = 32 * 1024**2


def result_value(record):
    return next(((k, record[k]) for k in ("chart", *RECORD_KINDS) if k in record), None)


def freshness(state, spec):
    from veri_ufku.operations.contracts import active_datasets

    datasets = {d["version_id"]: d for d in state["datasets"]}
    heads = {d["dataset_id"]: d["version_id"] for d in active_datasets(state)}
    records = {r["id"]: r for r in state["results"]}
    issues = []

    def check_version(v):
        d = datasets[v]
        if heads.get(d["dataset_id"]) != v:
            issues.append(
                dict(kind="dataset_stale", id=v, current=heads.get(d["dataset_id"]))
            )

    for b in spec["blocks"]:
        if "version" in b:
            check_version(b["version"])
        if "record" not in b:
            continue
        r = records[b["record"]]
        index = state["results"].index(r)
        for version in r["dataset_version_ids"]:
            check_version(version)
        later = [
            x["id"]
            for x in state["results"][index + 1 :]
            if x.get("capability_id") == r.get("capability_id")
            and x.get("dataset_version_ids") == r["dataset_version_ids"]
            and result_value(x)
            and result_value(x)[0] == result_value(r)[0]
        ]
        if later:
            issues.append(
                dict(kind="newer_same_capability_run", id=r["id"], current=later[-1])
            )
    return issues


def request_for(store, state, parameters):
    from veri_ufku.operations.workflow import references
    from veri_ufku.storage.experiment_store import capture

    spec = recipe(parameters)
    datasets = {d["version_id"]: d for d in state["datasets"]}
    all_refs = references(store, state)
    records = {r["id"]: r for r in state["results"]}
    selected = {}
    sources = {}
    artifacts = {}
    for b in spec["blocks"]:
        if "version" in b:
            v = b["version"]
            if v not in all_refs or not set(b["columns"]) <= {
                c["id"] for c in all_refs[v]["columns"]
            }:
                raise ProjectError("Rapor dataset/ColumnId bağı projede yok.")
            sources[v] = copy.deepcopy(all_refs[v])
            sources[v]["dataset"] = copy.deepcopy(datasets[v])
        if "record" not in b:
            continue
        ident = b["record"]
        if ident not in records or not result_value(records[ident]):
            raise ProjectError("Rapor destekli kayıtlı sonuç referansı gerekli.")
        r = records[ident]
        kind, value = result_value(r)
        if (
            kind == "chart"
            and b["kind"] != "chart"
            or b["kind"] == "chart"
            and kind != "chart"
        ):
            raise ProjectError("Grafik bloğu gerçek chart kaydı ister.")
        if b["kind"] == "model-card" and not value.get("model_card"):
            raise ProjectError("Model kartı kaydedilmemiş; uydurulmaz.")
        selected[ident] = copy.deepcopy(r)
        for v in r["dataset_version_ids"]:
            if v in all_refs:
                sources[v] = copy.deepcopy(all_refs[v])
                sources[v]["dataset"] = copy.deepcopy(datasets[v])
        if kind == "chart":
            if not spec["allow_graphics"]:
                raise ProjectError(
                    "Grafik görsel içerik redaction için explicit allow_graphics incelemesi ister."
                )
            if set(spec["masked_columns"]) & set(
                encode(value["spec"]).decode().split('"')
            ):
                raise ProjectError(
                    "Maskeli kolon kullanan grafik redakte edilmeden eklenemez; temiz grafik kaydı oluşturun."
                )
            for fmt in ("png", "svg", "pdf"):
                uri = value.get("artifact_uris", {}).get(fmt)
                if not uri:
                    raise ProjectError("Grafik PNG/SVG/PDF artifact seti eksik.")
                artifacts[ident + ":" + fmt] = artifact(store, uri)
        # Verify all recorded native artifact references, not only rendered values.
        for key, uri in value.get("artifact_uris", {}).items():
            artifacts.setdefault(ident + ":native:" + key, artifact(store, uri))
        if value.get("details_uri"):
            artifacts[ident + ":details"] = artifact(store, value["details_uri"])
        if value.get("model_package_uri"):
            artifacts[ident + ":model"] = artifact(store, value["model_package_uri"])
    masked_names = [
        c["name"]
        for d in state["datasets"]
        for c in d.get("import_metadata", {}).get("columns", [])
        if c["id"] in spec["masked_columns"]
    ]
    if any(r["fingerprint"]["size"] > 64 * 1024**2 for r in sources.values()):
        raise ProjectError("Rapor snapshot64MiB sınırı; daha dar dataset seçin.")
    safe_spec, redactions = redact(spec, masked_names)
    # Only text/caption changes are expected. Structural ids/units are validated again.
    recipe(safe_spec)
    if safe_spec != spec:
        raise ProjectError(
            "Tarifte secret/path/sensitive alan var. Önce Önizleme maskesi ile temizlenmiş tarifi kullanın."
        )
    return dict(
        spec=spec,
        sources=sources,
        records=selected,
        artifacts=artifacts,
        masked_names=masked_names,
        stale=freshness(state, spec),
        test_uses=[
            dict(
                id=r["id"],
                kind=kind,
                **{
                    k: r[kind][k]
                    for k in (
                        "run_id",
                        "status",
                        "requested_at",
                        "evaluated_at",
                        "prior_test_use_ids",
                        "split_id",
                        "protocol_id",
                        "development_run_id",
                        "result_id",
                    )
                    if k in r[kind]
                },
            )
            for r in state["results"]
            for kind in ("test_use", "time_series_test_use")
            if kind in r
        ],
        prior_test_use_ids=prior_uses(state),
        record_refs={k: digest(v) for k, v in selected.items()},
        source_refs={
            k: dict(
                fingerprint=v["fingerprint"], source_snapshot_id=v["source_snapshot_id"]
            )
            for k, v in sources.items()
        },
        experiment_capture=capture(spec),
    )


def artifact(store, uri):
    meta = store.manifest["artifacts"].get(uri)
    if not meta:
        raise ProjectError("Rapor artifact manifest bağı eksik.")
    if meta["size"] > 16 * 1024**2:
        raise ProjectError("Rapor artifact16MiB sınırı; daha dar sonuç seçin.")
    return dict(
        uri=uri,
        path=str(store.path(uri)).replace("/proc/self/", f"/proc/{os.getpid()}/", 1),
        fingerprint={k: meta[k] for k in ("size", "sha256")},
    )


def validate_value(v, versions):
    from veri_ufku.domain.contracts import ComputeBudget

    ComputeBudget(**v["compute_budget"])
    s = recipe(v["spec"])
    c = v["experiment_capture"]
    if (
        v["schema"] != "ScientificReport/v1"
        or v["status"] != "completed"
        or v["limitations"] != LIMITATIONS
        or v["provenance"]["parameters_hash"] != digest(s)
        or v["provenance"]["capability_id"] != "report.builder"
        or set(v["provenance"]["source_snapshot_ids"])
        != {r["source_snapshot_id"] for r in v["source_refs"].values()}
        or v["provenance"]["method_version"] != 1
        or set(v["source_refs"]) != set(v["provenance"]["dataset_versions"])
        or not set(v["source_refs"]) <= set(versions)
    ):
        raise ProjectError("Rapor contract/provenance bağı geçersiz.")
    if (
        c["schema"] != "RunCapture/v1"
        or c["config_hash"] != byte_digest(encode(s))
        or c["code_hash"] != byte_digest(encode(c["code_files"]))
        or c["environment_hash"] != byte_digest(encode(c["environment"]))
    ):
        raise ProjectError("Rapor code/config/environment hash bozuk.")
    if v["review_hash"] != digest(
        {
            k: x
            for k, x in v.items()
            if k not in ("review_hash", "files", "file_refs", "bundle_ref")
        }
    ):
        raise ProjectError("Rapor önizleme hash bozuk.")


def publish(store, state, value, control=None):
    control = control or Control()
    v = copy.deepcopy(value)
    validate_value(v, {d["version_id"] for d in state["datasets"]})
    req = request_for(store, state, v["spec"])
    if any(
        v[k] != req[k]
        for k in ("source_refs", "record_refs", "prior_test_use_ids", "stale")
    ):
        raise ProjectError(
            "Rapor kaynak/run/test/freshness değişti; açık önizlemeyi yenileyin."
        )
    for a in req["artifacts"].values():
        if file_hash(Path(a["path"])) != a["fingerprint"]:
            raise ProjectError("Rapor kaynak artifact hash değişmiş.")
    for a in req["sources"].values():
        if file_hash(Path(a["path"])) != a["fingerprint"]:
            raise ProjectError("Rapor dataset hash değişmiş.")
    files = v.pop("files")
    total = 0
    if (
        not {
            "report.md",
            "report.html",
            "report.pdf",
            "manifest.json",
            "report-package.zip",
        }
        <= set(files)
        or len(files) > 80
        or set(files) != set(v["file_hashes"])
    ):
        raise ProjectError("Rapor format seti eksik/aşırı.")
    decoded = {}
    for name, data in files.items():
        if Path(name).name != name or name.startswith(".") or len(name) > 120:
            raise ProjectError("Rapor dosya adı güvenli değil.")
        decoded[name] = base64.b64decode(data, validate=True)
        total += len(decoded[name])
        if file_hash_bytes(decoded[name]) != v["file_hashes"].get(name):
            raise ProjectError("Rapor dosya hash/preview eşlemesi bozuk.")
    if total > MAX_TOTAL:
        raise ProjectError("Rapor toplam32MiB sınırı.")
    control.check()

    stage = store.path("staging") / uid()
    stage.mkdir(mode=0o700)

    def add(draft):
        refs = {}
        for name, raw in decoded.items():
            control.check()
            p = stage / name
            control.disk(stage)
            p.write_bytes(raw)
            fp = file_hash(p)
            uri = "sources/" + uid() + ".bin"
            refs[name] = dict(uri=uri, fingerprint=fp)
            store.pending[uri] = (p, dict(**fp, kind="source", rows=None, schema=None))
        summary = dict(v, file_refs=refs)
        draft["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=list(v["source_refs"]),
                seed=None,
                capability_id="report.builder",
                scientific_report=summary,
            )
        )

    try:
        return transaction(store, state, add)
    finally:
        import shutil

        shutil.rmtree(stage, ignore_errors=True)


def validate_records(state, versions):
    records = {r["id"]: r for r in state["results"]}
    for r in state["results"]:
        if "scientific_report" not in r:
            continue
        v = r["scientific_report"]
        validate_value(v, versions)
        if set(r["dataset_version_ids"]) != set(v["source_refs"]) or any(
            k not in records or digest(records[k]) != fp
            for k, fp in v["record_refs"].items()
        ):
            raise ProjectError("Rapor kayıtlı run bağı kayıp/değişmiş.")


def load(store, record):
    v = copy.deepcopy(record["scientific_report"])
    validate_value(v, {d["version_id"] for d in store.state["datasets"]})
    if {k: a["fingerprint"] for k, a in v["file_refs"].items()} != v["file_hashes"]:
        raise ProjectError("Rapor dosya/preview eşlemesi değişmiş.")
    for a in v["file_refs"].values():
        if file_hash(store.path(a["uri"])) != a["fingerprint"]:
            raise ProjectError("Rapor artifact hash bozuk.")
    return v


def export_file(store, state, ident, name, destination, review_hash, control=None):
    from veri_ufku.exports.files import publish as publish_file

    control = control or Control()
    r = next(
        r for r in state["results"] if r["id"] == ident and "scientific_report" in r
    )
    value = load(store, r)
    if review_hash != value["review_hash"]:
        raise ProjectError("Export için görülen redaction önizlemesi gerekli.")
    current = request_for(store, state, value["spec"])
    if (
        value["stale"] != current["stale"]
        or value["prior_test_use_ids"] != current["prior_test_use_ids"]
    ):
        raise ProjectError(
            "Önizlemeden sonra güncellik/test geçmişi değişti; yeni rapor oluşturun."
        )
    for source in current["sources"].values():
        if file_hash(Path(source["path"])) != source["fingerprint"]:
            raise ProjectError("Rapor kaynağı değişmiş.")
    for a in current["artifacts"].values():
        if file_hash(Path(a["path"])) != a["fingerprint"]:
            raise ProjectError("Rapor referans artifact değişmiş.")
    if name not in value["file_refs"] or name not in (
        "report.md",
        "report.html",
        "report.pdf",
        "report-package.zip",
    ):
        raise ProjectError("Rapor formatı desteklenmiyor.")
    if Path(destination).suffix.lower() != Path(name).suffix:
        raise ProjectError("Çıktı uzantısı seçilen formatla aynı olmalı.")
    return publish_file(
        store.path(value["file_refs"][name]["uri"]), destination, store.root, control
    )
