"""Append-only safe JSON model/checkpoint artifacts through the single ProjectStore."""

import copy
import json

from veri_ufku.modeling.neural import MAX_BYTES
from veri_ufku.modeling.neural_contracts import NeuralSpec
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.project_store import file_hash
from veri_ufku.storage.validation_store import prior_uses, transaction


def validate(data):
    if data.get("schema") == "WorkflowRun/v1":
        from veri_ufku.operations.workflow import validate as validate_workflow_run

        return validate_workflow_run(data)

    if data.get("schema") == "CodeRun/v1":
        from veri_ufku.modeling.code_workspace import validate as validate_code

        return validate_code(data)

    if data.get("schema") == "SpecialTargetRun/v1":
        from veri_ufku.modeling.special_runs import validate as validate_special

        return validate_special(data)

    if data.get("schema") == "StreamRun/v1":
        from veri_ufku.modeling.streams import validate as validate_stream

        return validate_stream(data)

    if data.get("schema") == "GraphRun/v1":
        from veri_ufku.modeling.graphs import validate as validate_graph

        return validate_graph(data)
    if data.get("schema") == "PatternRun/v1":
        from veri_ufku.modeling.patterns import validate as validate_pattern

        return validate_pattern(data)
    if data.get("schema") == "RecommendationRun/v1":
        from veri_ufku.modeling.recommendation import (
            validate as validate_recommendation,
        )

        return validate_recommendation(data)
    if data.get("schema") == "AudioRun/v1":
        from veri_ufku.modeling.audio import validate as validate_audio

        return validate_audio(data)
    if data.get("schema") == "VisionRun/v1":
        from veri_ufku.modeling.vision import validate as validate_vision

        return validate_vision(data)
    if data.get("schema") != "NeuralRun/v1" or data.get("status") not in (
        "running",
        "completed",
        "paused",
        "canceled",
        "budget_exhausted",
        "failed",
    ):
        raise ProjectError("Neural kayıt schema/status geçersiz.")
    spec = NeuralSpec.from_dict(data["spec"], require_backend=False)
    if (
        type(data["epoch"]) is not int
        or not 0 <= data["epoch"] <= spec.epochs
        or len(data["curves"]) != data["epoch"]
    ):
        raise ProjectError("Checkpoint epoch/curve uyuşmuyor.")
    membership = data["plan"]["membership"]
    if (
        set(membership["train"]) & set(membership["validation"])
        or set(membership["development"]) & set(membership["test"])
        or set(data["tensor_schema"]["fit_row_ids"]) != set(membership["train"])
    ):
        raise ProjectError("Neural fit/validation/final üyelik sızıntısı.")
    if (
        data["status"] == "completed"
        and not data.get("model_weights")
        and not data.get("details_uri")
    ):
        raise ProjectError("Completed neural model weights eksik.")
    if len(json.dumps(data, allow_nan=False).encode()) > MAX_BYTES:
        raise ProjectError("Neural safe JSON boyut sınırı.")


def validate_journal(state, versions):
    seen = []
    latest = {}
    for record in state["results"]:
        if "test_use" in record or "time_series_test_use" in record:
            seen.append(record["id"])
        if "neural" not in record:
            continue
        data = record["neural"]
        validate(data)
        if data.get("schema") == "WorkflowRun/v1":
            from veri_ufku.storage.workflow_store import validate_journal as dag_journal

            dag_journal(data, versions)
        if (
            data["dataset_version"] not in versions
            or data["origin_version"] not in versions
            or set(record["dataset_version_ids"])
            != (
                {r["version_id"] for r in data["source_references"]}
                | {data["dataset_version"], data["origin_version"]}
                if data.get("schema") == "WorkflowRun/v1"
                else {data["dataset_version"], data["origin_version"]}
            )
            or data["prior_test_use_ids"] != seen
        ):
            raise ProjectError("Neural source/test journal bağı geçersiz.")
        if (
            data["source_snapshot_id"]
            != versions[data["dataset_version"]]["import_metadata"][
                "source_snapshot_id"
            ]
        ):
            raise ProjectError("Neural snapshot bağı geçersiz.")
        if data.get("schema") == "GraphRun/v1" and data.get("node_source"):
            ns = data["node_source"]
            nd = versions.get(ns["version_id"])
            if (
                not nd
                or ns["version_id"] != data["origin_version"]
                or nd["snapshot_uri"] != ns["snapshot_uri"]
                or nd["import_metadata"]["source_snapshot_id"]
                != ns["source_snapshot_id"]
            ):
                raise ProjectError("Graph node-source journal bağı geçersiz.")
        if data.get("schema") == "StreamRun/v1":
            before = (
                latest.get(data.get("resume_from"))
                if data.get("resume_from")
                else latest.get(data["training_id"])
            )
            if data.get("resume_from") and not before:
                raise ProjectError("Stream resume parent journal içinde yok.")
            if before and (
                before["compat_id"] != data["compat_id"]
                or before["cursor"] > data["cursor"]
            ):
                raise ProjectError("Stream resume/cursor geçmişi değişti.")
        previous = latest.get(data["training_id"])
        if previous and (
            previous["compat_id"] != data["compat_id"]
            or previous["epoch"] > data["epoch"]
            or previous["elapsed_seconds"] > data["elapsed_seconds"]
            or previous["curves"] != data["curves"][: previous["epoch"]]
        ):
            raise ProjectError("Neural immutable checkpoint geçmişi değişti.")
        latest[data["training_id"]] = data


def publish(store, state, data):
    validate(data)
    d = next(v for v in state["datasets"] if v["version_id"] == data["dataset_version"])
    if file_hash(store.path(d["snapshot_uri"])) != data["snapshot_fingerprint"]:
        raise ProjectError("Neural source fingerprint değişti.")

    if data.get("schema") == "GraphRun/v1" and data.get("node_source"):
        source = data["node_source"]
        if (
            source["version_id"] != data["origin_version"]
            or file_hash(store.path(source["snapshot_uri"])) != source["fingerprint"]
        ):
            raise ProjectError("Graph node table source fingerprint değişti.")

    def add(draft):
        nonlocal data
        if data["prior_test_use_ids"] != prior_uses(draft):
            raise ProjectError("Neural test geçmişi silinemez/değişti.")
        if data.get("schema") == "WorkflowRun/v1":
            from veri_ufku.storage.workflow_store import attach

            data = attach(store, draft, data)
        staging = store.path("staging") / uid()
        staging.mkdir(mode=0o700)
        path = staging / "neural.bin"
        raw = json.dumps(
            data, ensure_ascii=False, sort_keys=True, allow_nan=False
        ).encode()
        path.write_bytes(raw)
        fp = file_hash(path)
        uri = "sources/" + uid() + ".bin"
        store.pending[uri] = (path, dict(**fp, kind="source", rows=None, schema=None))
        summary = {
            k: copy.deepcopy(v)
            for k, v in data.items()
            if k not in ("runtime", "model_weights", "validation_predictions")
            and not (
                data.get("schema") == "RecommendationRun/v1"
                and k in ("rows", "queries", "plan", "tensor_schema")
            )
        }
        if data.get("schema") == "WorkflowRun/v1":
            summary["nodes_hash"] = digest(data["nodes"])
            summary["nodes"] = [
                {
                    k: v
                    for k, v in n.items()
                    if k
                    in (
                        "case",
                        "node",
                        "kind",
                        "status",
                        "attempts",
                        "cache_key",
                        "cache_invalidated",
                        "verified_at",
                        "operation_spec",
                        "root_versions",
                    )
                }
                for n in data["nodes"]
            ]
        if data.get("schema") == "StreamRun/v1":
            summary.pop("state", None)
            summary.update(
                state_hash=digest(data["state"]), cursor=data["state"]["cursor"]
            )
        if data.get("schema") == "RecommendationRun/v1":
            summary.update(
                split_id=data["plan"]["split_id"],
                fit_row_count=len(data["tensor_schema"]["fit_row_ids"]),
                query_count=len(data["queries"]),
                lineage_hash=digest(dict(rows=data["rows"], plan=data["plan"])),
            )
        if data.get("schema") == "PatternRun/v1":
            for key in ("rows", "analysis", "plan", "tensor_schema"):
                summary.pop(key, None)
            summary.update(
                split_id=data["plan"]["split_id"],
                lineage_hash=digest(data["rows"]),
                analysis_hash=digest(data["analysis"]),
            )
        if data.get("schema") == "GraphRun/v1":
            for key in ("nodes", "edges", "analysis", "view", "plan", "tensor_schema"):
                summary.pop(key, None)
            summary.update(
                split_id=data["plan"]["split_id"],
                lineage_hash=digest(dict(nodes=data["nodes"], edges=data["edges"])),
                analysis_hash=digest(
                    dict(analysis=data["analysis"], view=data["view"])
                ),
            )
        summary.update(details_uri=uri, details_fingerprint=fp)
        if data["status"] == "completed" and (
            data.get("schema")
            not in (
                "VisionRun/v1",
                "AudioRun/v1",
                "RecommendationRun/v1",
                "PatternRun/v1",
                "GraphRun/v1",
                "StreamRun/v1",
                "SpecialTargetRun/v1",
                "CodeRun/v1",
                "WorkflowRun/v1",
            )
            or data.get("model_weights")
        ):
            summary.update(
                model_package_uri=uri,
                model_package_fingerprint=fp,
                model_card=dict(
                    schema="NeuralModelCard/v1",
                    template=data.get("recommendation_spec", {}).get("task")
                    or data.get("audio_spec", {}).get("task")
                    or data.get("vision_spec", {}).get("task")
                    or data["spec"]["template"],
                    tensor_schema={
                        k: v
                        for k, v in data["tensor_schema"].items()
                        if k != "fit_row_ids"
                    }
                    if data.get("schema") == "RecommendationRun/v1"
                    else data["tensor_schema"],
                    training_id=data["training_id"],
                    safe_format="closed JSON tensor data; no object import",
                    limitations=data["warnings"],
                ),
            )
        draft["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=list(
                    dict.fromkeys(
                        [data["dataset_version"], data["origin_version"]]
                        + (
                            [r["version_id"] for r in data["source_references"]]
                            if data.get("schema") == "WorkflowRun/v1"
                            else []
                        )
                    )
                ),
                seed=data["seed"],
                capability_id=(
                    "workflow.source"
                    if data.get("schema") == "WorkflowRun/v1"
                    else "code.workspace"
                    if data.get("schema") == "CodeRun/v1"
                    else "model.special." + data["target_recipe"]["task"]
                    if data.get("schema") == "SpecialTargetRun/v1"
                    else "model.stream.replay"
                    if data.get("schema") == "StreamRun/v1"
                    else "model.graph." + data["graph_spec"]["task"]
                    if data.get("schema") == "GraphRun/v1"
                    else "model.pattern."
                    + data["pattern_spec"]["task"].replace("_", "-")
                    if data.get("schema") == "PatternRun/v1"
                    else "model.recommendation." + data["recommendation_spec"]["task"]
                    if data.get("schema") == "RecommendationRun/v1"
                    else "model.audio." + data["audio_spec"]["task"]
                    if data.get("schema") == "AudioRun/v1"
                    else "model.vision." + data["vision_spec"]["task"]
                    if data.get("schema") == "VisionRun/v1"
                    else "model.neural." + data["spec"]["template"]
                ),
                neural=summary,
            )
        )

    return transaction(store, state, add)


def load(store, record):
    summary = record["neural"]
    path = store.path(summary["details_uri"])
    if (
        file_hash(path) != summary["details_fingerprint"]
        or path.stat().st_size > MAX_BYTES
    ):
        raise ProjectError("Neural checkpoint hash/boyut bozuk.")
    try:
        data = json.loads(path.read_text())
    except (UnicodeError, ValueError):
        raise ProjectError(
            "Safe JSON checkpoint okunamadı; .pt/.pkl import desteklenmez."
        ) from None
    validate(data)
    if data.get("schema") == "StreamRun/v1" and (
        summary.get("state_hash") != digest(data["state"])
        or summary.get("cursor") != data["state"]["cursor"]
    ):
        raise ProjectError("Stream immutable state hash/cursor uyuşmuyor.")
    if data.get("schema") == "RecommendationRun/v1" and (
        summary.get("lineage_hash")
        != digest(dict(rows=data["rows"], plan=data["plan"]))
        or summary.get("split_id") != data["plan"]["split_id"]
        or summary.get("fit_row_count") != len(data["tensor_schema"]["fit_row_ids"])
        or summary.get("query_count") != len(data["queries"])
    ):
        raise ProjectError("Recommendation summary/lineage hash uyuşmuyor.")
    if data.get("schema") == "PatternRun/v1" and (
        summary.get("lineage_hash") != digest(data["rows"])
        or summary.get("analysis_hash") != digest(data["analysis"])
        or summary.get("split_id") != data["plan"]["split_id"]
    ):
        raise ProjectError("Pattern artifact summary hash uyuşmuyor.")
    if data.get("schema") == "GraphRun/v1" and (
        summary.get("lineage_hash")
        != digest(dict(nodes=data["nodes"], edges=data["edges"]))
        or summary.get("analysis_hash")
        != digest(dict(analysis=data["analysis"], view=data["view"]))
    ):
        raise ProjectError("Graph immutable summary/lineage hash uyuşmuyor.")
    if data.get("schema") == "WorkflowRun/v1" and summary.get("nodes_hash") != digest(
        data["nodes"]
    ):
        raise ProjectError("Workflow immutable node summary hash uyuşmuyor.")
    if any(
        digest(data[k]) != digest(v)
        for k, v in summary.items()
        if k in data and not (data.get("schema") == "WorkflowRun/v1" and k == "nodes")
    ):
        raise ProjectError("Neural checkpoint/immutable summary uyuşmuyor.")
    return data
