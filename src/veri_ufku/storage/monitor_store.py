"""Monitoring artifacts reuse ProjectStore publication and existing experiment audit."""

import copy
import json
import os
from pathlib import Path

from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.monitor_contracts import LIMITATIONS, MonitorSpec
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError, encode, uid
from veri_ufku.storage.project_model import digest as byte_digest
from veri_ufku.storage.project_store import file_hash
from veri_ufku.storage.validation_store import prior_uses, transaction

MAX_BYTES = 16 * 1024**2


def models(state):
    return {
        r["id"]: dict(
            record_id=r["id"],
            run_id=r["baseline"]["run_id"],
            card=r["baseline"]["model_card"],
            fingerprint=r["baseline"]["model_package_fingerprint"],
            uri=r["baseline"]["model_package_uri"],
        )
        for r in state["results"]
        if r.get("baseline", {}).get("status") == "completed"
        and r["baseline"].get("model_package_uri")
        and r["baseline"]["model_card"]["purpose"] in ("regression", "classification")
    }


def request_for(store, state, parameters):
    from veri_ufku.operations.workflow import references

    s = MonitorSpec.from_dict(parameters)
    refs = references(store, state)
    versions = list(
        dict.fromkeys([s.reference, s.window] + ([s.labels] if s.labels else []))
    )
    if any(v not in refs for v in versions):
        raise ProjectError("Monitoring dataset sürümü projede yok.")
    from veri_ufku.storage.experiment_store import capture

    available = models(state)
    selected = {}
    selected_route = route(state) if s.use_champion_route else None
    if s.use_champion_route and not selected_route:
        raise ProjectError("Kayıtlı local champion route yok.")
    champion = selected_route["value"]["record_id"] if selected_route else s.champion
    if champion and champion == s.challenger:
        raise ProjectError("Shadow champion/challenger aynı kayıt olamaz.")
    for ident in (champion, s.challenger):
        if not ident:
            continue
        if ident not in available:
            raise ProjectError("Kayıtlı completed güvenli model seçin.")
        item = copy.deepcopy(available[ident])
        item["path"] = str(store.path(item["uri"])).replace(
            "/proc/self/", f"/proc/{os.getpid()}/", 1
        )
        if file_hash(Path(item["path"])) != item["fingerprint"]:
            raise ProjectError("Model artifact hash değişmiş.")
        selected[ident] = item
    return dict(
        sources={
            v: dict(
                refs[v],
                schema_contract=next(
                    d.get("schema_contract")
                    for d in state["datasets"]
                    if d["version_id"] == v
                ),
            )
            for v in versions
        },
        models=selected,
        resolved_champion=champion,
        route_event_id=selected_route["id"] if selected_route else None,
        prior_test_use_ids=prior_uses(state),
        commit_id=store.commit_id,
        experiment_capture=capture(s.data()),
    )


def validate_capture(value):
    c = value["experiment_capture"]
    if (
        c.get("schema") != "RunCapture/v1"
        or c.get("code_hash") != byte_digest(encode(c["code_files"]))
        or c.get("environment_hash") != byte_digest(encode(c["environment"]))
        or c.get("config_hash") != byte_digest(encode(value["spec"]))
    ):
        raise ProjectError("Monitoring code/config/environment capture hash bozuk.")


def validate_value(value, versions):
    s = MonitorSpec.from_dict(value["spec"])
    if (
        value["schema"] != "MonitoringRun/v1"
        or value["status"] != "completed"
        or value["fit_calls"] != 0
        or value["limitations"] != LIMITATIONS
        or value["identity"]
        != digest({k: v for k, v in value.items() if k != "identity"})
    ):
        raise ProjectError("Monitoring result identity/schema/status geçersiz.")
    validate_capture(value)
    p = value["provenance"]
    if (
        set(p["dataset_versions"])
        != set([s.reference, s.window] + ([s.labels] if s.labels else []))
        or not set(p["dataset_versions"]) <= set(versions)
        or p["parameters_hash"] != digest(s.data())
        or p["capability_id"] != "model.monitor.batch"
    ):
        raise ProjectError("Monitoring provenance dataset/config bağı bozuk.")
    for side in ("reference", "window"):
        if value[side]["version"] != getattr(s, side):
            raise ProjectError("Monitoring reference/window bağı bozuk.")
    m = value["membership"]
    for k in ("reference_row_ids", "window_row_ids"):
        if len(m[k]) != len(set(m[k])):
            raise ProjectError("Monitoring RowId üyeliği yinelenmiş.")
    if (
        len(m["window_row_ids"]) != value["window"]["n"]
        or len(m["reference_row_ids"]) != value["reference"]["n"]
        or len(m["window_source_record_ids"]) != value["window"]["n"]
    ):
        raise ProjectError("Monitoring üyelik sayısı bozuk.")
    for record in value["models"]:
        e = record["window_evaluation"]
        if not s.labels and (
            e["metrics"] is not None or e["status"] != "labels_unavailable"
        ):
            raise ProjectError("Labels yokken başarı metriği üretilemez.")
    if len(json.dumps(value, allow_nan=False).encode()) > MAX_BYTES:
        raise ProjectError("Monitoring16MiB sınırı.")


def publish(store, state, value, control=None):
    control = control or Control()
    value = copy.deepcopy(value)
    validate_value(value, {d["version_id"]: d for d in state["datasets"]})
    request = request_for(store, state, value["spec"])
    if value["route_event_id"] != request["route_event_id"]:
        raise ProjectError("Monitoring route revision değişmiş.")
    if value["prior_test_use_ids"] != prior_uses(state) or value["model_refs"] != {
        k: {n: v[n] for n in ("fingerprint", "record_id", "run_id")}
        for k, v in request["models"].items()
    }:
        raise ProjectError("Monitoring model/test geçmişi değişmiş.")
    if value["source_refs"] != {
        k: dict(
            fingerprint=v["fingerprint"], source_snapshot_id=v["source_snapshot_id"]
        )
        for k, v in request["sources"].items()
    }:
        raise ProjectError("Monitoring labels/source reference değişmiş.")
    for r in request["sources"].values():
        if file_hash(Path(r["path"])) != r["fingerprint"]:
            raise ProjectError("Monitoring snapshot hash değişmiş.")
    for side in ("reference", "window"):
        r = request["sources"][value[side]["version"]]
        if file_hash(Path(r["path"])) != value[side]["fingerprint"]:
            raise ProjectError("Monitoring kaynak hash değişmiş.")
    # Bind reported membership to immutable source identities before accepting worker output.
    import polars as pl

    for side in ("reference", "window"):
        r = request["sources"][value[side]["version"]]
        f = pl.read_parquet(r["path"], columns=["__vu_row_id", "__vu_source_record_id"])
        ids = value["membership"][side + "_row_ids"]
        lookup = dict(zip(f["__vu_row_id"], f["__vu_source_record_id"], strict=True))
        if (
            not set(ids) <= set(lookup)
            or side == "window"
            and [lookup[i] for i in ids]
            != value["membership"]["window_source_record_ids"]
        ):
            raise ProjectError("Monitoring source RowId/SourceRecordId bozuk.")
    raw = json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True
    ).encode()
    control.check()

    def add(draft):
        control.check()
        stage = store.path("staging") / uid()
        stage.mkdir(mode=0o700)
        path = stage / "monitoring.bin"
        path.write_bytes(raw)
        fp = file_hash(path)
        uri = "sources/" + uid() + ".bin"
        store.pending[uri] = (path, dict(**fp, kind="source", rows=None, schema=None))
        from veri_ufku.modeling.monitoring import public_report

        summary = public_report(value)
        summary.update(details_uri=uri, details_fingerprint=fp)
        control.check()
        draft["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=list(value["provenance"]["dataset_versions"]),
                seed=None,
                capability_id="model.monitor.batch",
                monitoring=summary,
            )
        )

    return transaction(store, state, add)


def validate_records(state, versions):
    for r in state["results"]:
        if "monitoring" not in r:
            continue
        v = r["monitoring"]
        validate_capture(v)
        s = MonitorSpec.from_dict(v["spec"])
        if (
            v["schema"] != "MonitoringRun/v1"
            or v["status"] != "completed"
            or set(r["dataset_version_ids"]) != set(v["provenance"]["dataset_versions"])
            or not set(r["dataset_version_ids"]) <= set(versions)
            or v["provenance"]["parameters_hash"] != digest(s.data())
            or v["details_fingerprint"]["size"] > MAX_BYTES
        ):
            raise ProjectError("Monitoring summary/provenance geçersiz.")
        known = models(state)
        if any(
            k not in known or known[k]["fingerprint"] != m["fingerprint"]
            for k, m in v["model_refs"].items()
        ):
            raise ProjectError("Monitoring frozen model lineage kayıp.")


def load(store, record):
    v = record["monitoring"]
    path = store.path(v["details_uri"])
    if file_hash(path) != v["details_fingerprint"]:
        raise ProjectError("Monitoring artifact hash bozuk.")
    value = json.loads(path.read_bytes())
    validate_value(value, {d["version_id"]: d for d in store.state["datasets"]})
    return value


def route(state):
    return next(
        (
            r["experiment_event"]
            for r in reversed(state["results"])
            if r.get("experiment_event", {}).get("kind") == "model_route"
        ),
        None,
    )


def activate(store, state, record_id, reason, rollback=False):
    from veri_ufku.storage.experiment_store import event

    available = models(state)
    if (
        record_id not in available
        or reason not in ("manual_selection", "shadow_review", "rollback")
        or rollback != (reason == "rollback")
    ):
        raise ProjectError("Model route açık selection/review veya rollback gerekli.")
    previous = route(state)
    if rollback:
        if not previous or previous["value"]["previous_record_id"] != record_id:
            raise ProjectError(
                "Rollback yalnız son route'un gerçek önceki modeline döner."
            )
    if previous and previous["value"]["record_id"] == record_id:
        raise ProjectError("Model zaten yerel champion.")
    item = available[record_id]
    value = dict(
        record_id=record_id,
        model_fingerprint=item["fingerprint"],
        previous_record_id=previous["value"]["record_id"] if previous else None,
        previous_event_id=previous["id"] if previous else None,
        reason=reason,
        rollback=rollback,
        scope="local explicit scoring reference; no external deployment",
    )
    return event(store, state, item["run_id"], "model_route", value)
