"""Scenario results use the existing project transaction, registry and provenance."""

import copy
import json
from pathlib import Path

from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.scenario_contracts import LIMITATIONS, ScenarioSpec
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.monitor_store import models
from veri_ufku.storage.project_model import ProjectError, encode, uid
from veri_ufku.storage.project_model import digest as byte_digest
from veri_ufku.storage.project_store import file_hash
from veri_ufku.storage.validation_store import prior_uses, transaction

MAX_BYTES = 2 * 1024**2


def request_for(store, state, parameters):
    import os

    from veri_ufku.operations.workflow import references
    from veri_ufku.storage.experiment_store import capture

    s = ScenarioSpec.from_dict(parameters).data()
    selected = None
    sources = {}
    if "model" in s:
        available = models(state)
        ident = s["model"]["record_id"]
        if (
            ident not in available
            or available[ident]["card"]["purpose"] != "regression"
        ):
            raise ProjectError("Tamamlanmış safe regression modeli seçin.")
        selected = copy.deepcopy(available[ident])
        selected["path"] = str(store.path(selected["uri"])).replace(
            "/proc/self/", f"/proc/{os.getpid()}/", 1
        )
        if file_hash(Path(selected["path"])) != selected["fingerprint"]:
            raise ProjectError("Model hash değişmiş.")
        refs = references(store, state)
        version = selected["card"]["dataset_version"]
        if (
            version not in refs
            or refs[version]["fingerprint"] != selected["card"]["snapshot_fingerprint"]
        ):
            raise ProjectError("Model training snapshot reference/hash eksik.")
        sources[version] = refs[version]
    return dict(
        sources=sources,
        model=selected,
        experiment_capture=capture(s),
        prior_test_use_ids=prior_uses(state),
        commit_id=store.commit_id,
    )


def validate_value(v, versions, full=True):
    s = ScenarioSpec.from_dict(v["spec"]).data()
    c = v["experiment_capture"]
    p = v["provenance"]
    out = v["output"]
    if (
        v["schema"] != "ScenarioRun/v1"
        or v["status"] != "completed"
        or v["fit_calls"] != 0
        or v["limitations"] != LIMITATIONS
        or c["schema"] != "RunCapture/v1"
        or c["code_hash"] != byte_digest(encode(c["code_files"]))
        or c["environment_hash"] != byte_digest(encode(c["environment"]))
        or c["config_hash"] != byte_digest(encode(s))
        or p["parameters_hash"] != digest(s)
        or p["capability_id"] != "scenario." + s["method"]
        or set(p["dataset_versions"]) != set(v["source_refs"])
        or not set(v["source_refs"]) <= set(versions)
    ):
        raise ProjectError("Scenario schema/config/provenance/capture bağı bozuk.")
    if full and v["identity"] != digest(
        {k: x for k, x in v.items() if k != "identity"}
    ):
        raise ProjectError("Scenario artifact identity bozuk.")
    if s["method"] == "monte-carlo":
        if (
            out["status"] != "completed"
            or out["draws"] != s["draws"]
            or out["mean_mcse"] < 0
            or len(out["quantiles"]) != 5
        ):
            raise ProjectError("Monte Carlo draw/özet şeması bozuk.")
    else:
        if out.get("optimal") and (
            out["status"] != "optimal_within_tolerance"
            or not out["feasibility"]["feasible"]
            or s["method"] not in ("linear", "mixed-integer")
        ):
            raise ProjectError("Limit/infeasible/local sonuç optimum sayılamaz.")
    if ("model" in s) != bool(v["model_refs"]) or len(v["model_refs"]) > 1:
        raise ProjectError("Scenario model lineage eksik.")
    if "model" in s and set(v["model_refs"]) != {s["model"]["record_id"]}:
        raise ProjectError("Scenario frozen model bağı bozuk.")
    if len(encode(v)) > MAX_BYTES:
        raise ProjectError("Scenario2MiB artifact sınırı.")


def publish(store, state, value, control=None):
    control = control or Control()
    v = copy.deepcopy(value)
    validate_value(v, {d["version_id"] for d in state["datasets"]})
    req = request_for(store, state, v["spec"])
    expected_sources = {
        k: dict(
            fingerprint=x["fingerprint"], source_snapshot_id=x["source_snapshot_id"]
        )
        for k, x in req["sources"].items()
    }
    expected_models = (
        {
            req["model"]["record_id"]: {
                k: req["model"][k] for k in ("fingerprint", "record_id", "run_id")
            }
        }
        if req["model"]
        else {}
    )
    if (
        v["source_refs"] != expected_sources
        or v["model_refs"] != expected_models
        or v["prior_test_use_ids"] != prior_uses(state)
    ):
        raise ProjectError("Scenario source/model/test geçmişi değişmiş.")
    for source in req["sources"].values():
        if file_hash(Path(source["path"])) != source["fingerprint"]:
            raise ProjectError("Scenario source hash değişmiş.")
    if req["model"]:
        import polars as pl

        source = next(iter(req["sources"].values()))
        f = pl.read_parquet(
            source["path"], columns=["__vu_row_id", "__vu_source_record_id"]
        )
        domain = v["output"]["model_domain"]
        lookup = dict(zip(f["__vu_row_id"], f["__vu_source_record_id"], strict=True))
        ids = domain["fit_row_ids"]
        if (
            set(ids) != set(req["model"]["card"]["fit_row_ids"])
            or not set(ids) <= set(lookup)
            or [lookup[i] for i in ids] != domain["fit_source_record_ids"]
        ):
            raise ProjectError("Scenario fit RowId/SourceRecordId kökeni bozuk.")
    raw = encode(v)
    control.check()

    def add(draft):
        control.check()
        stage = store.path("staging") / uid()
        stage.mkdir(mode=0o700)
        path = stage / "scenario.bin"
        path.write_bytes(raw)
        fp = file_hash(path)
        uri = "sources/" + uid() + ".bin"
        store.pending[uri] = (path, dict(**fp, kind="source", rows=None, schema=None))
        from veri_ufku.modeling.scenario_contracts import public_report

        summary = public_report(v)
        summary.update(details_uri=uri, details_fingerprint=fp)
        draft["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=list(v["source_refs"]),
                seed=v["spec"].get("seed"),
                capability_id=v["provenance"]["capability_id"],
                scenario=summary,
            )
        )
        control.check()

    return transaction(store, state, add)


def validate_records(state, versions):
    available = models(state)
    for record in state["results"]:
        if "scenario" not in record:
            continue
        v = record["scenario"]
        validate_value(v, versions, False)
        if (
            set(record["dataset_version_ids"]) != set(v["source_refs"])
            or v["details_fingerprint"]["size"] > MAX_BYTES
        ):
            raise ProjectError("Scenario summary kaynak/size bağı bozuk.")
        if any(
            k not in available or available[k]["fingerprint"] != r["fingerprint"]
            for k, r in v["model_refs"].items()
        ):
            raise ProjectError("Scenario frozen model lineage kayıp.")


def load(store, record):
    summary = record["scenario"]
    p = store.path(summary["details_uri"])
    if file_hash(p) != summary["details_fingerprint"]:
        raise ProjectError("Scenario artifact hash değişmiş.")
    value = json.loads(p.read_bytes())
    validate_value(value, {d["version_id"] for d in store.state["datasets"]})
    from veri_ufku.modeling.scenario_contracts import public_report

    if public_report(value) != {
        k: v
        for k, v in summary.items()
        if k not in ("details_uri", "details_fingerprint")
    }:
        raise ProjectError("Scenario summary/artifact farklı.")
    return value
