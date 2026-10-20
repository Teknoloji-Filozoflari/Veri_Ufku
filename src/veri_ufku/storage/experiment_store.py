"""Local views and append-only revisions over existing ProjectStore run identities.

No model deserialization, network, second depot, or inferred historical hashes.
"""

import copy
import hashlib
import importlib.metadata
import math
import os
import platform
import re
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from veri_ufku.storage.project_model import ProjectError, digest, encode, uid


def capture(config):
    root = Path(__file__).parents[1]
    files = sorted(
        p
        for folder in ("modeling", "operations", "analytics", "domain", "jobs")
        for p in (root / folder).glob("*.py")
    ) + [
        root / "storage/validation_store.py",
        root / "storage/experiment_store.py",
        root / "storage/monitor_store.py",
        root / "storage/scenario_store.py",
        root / "storage/learning_lab_store.py",
        root / "storage/report_builder_store.py",
        root / "exports/report_builder.py",
        root / "exports/report_contracts.py",
        root / "exports/report_worker.py",
        root / "exports/share_bundle.py",
        root / "exports/share_privacy.py",
        root / "exports/share_worker.py",
        root / "storage/review_store.py",
        root / "exports/reports.py",
        root / "exports/files.py",
        root / "exports/code_bridge.py",
        root / "assets/fonts/DejaVuSans.ttf",
        root / "learning/lab_engine.py",
        root / "learning/lab_worker.py",
        root / "learning/curriculum.py",
        root / "learning/content/lessons.tr.json",
    ]
    code = {str(p.relative_to(root)): digest(p.read_bytes()) for p in files}
    env = {
        "python": platform.python_version(),
        "machine": platform.machine(),
        "system": platform.system(),
    }
    for name in (
        "numpy",
        "scipy",
        "scikit-learn",
        "polars",
        "skops",
        "veri-ufku",
        "PySide6",
        "pyarrow",
    ):
        try:
            env[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            env[name] = "unavailable"
    return dict(
        schema="RunCapture/v1",
        captured_at=datetime.now(UTC).isoformat(),
        code_hash=digest(encode(code)),
        environment_hash=digest(encode(env)),
        config_hash=digest(encode(config)),
        config_scope="validation/model options + immutable PipelineId preprocessing reference",
        environment=env,
        hardware=dict(
            system=platform.system(),
            machine=platform.machine(),
            visible_cpu_count=len(os.sched_getaffinity(0)),
            physical_memory_bytes=os.sysconf("SC_PAGE_SIZE")
            * os.sysconf("SC_PHYS_PAGES"),
            device="not_recorded; inspect method spec",
            captured_at="same capture boundary",
        ),
        code_files=code,
        data_access_time="captured before scheduling; run.data_access_at records first immutable snapshot read boundary",
    )


def _events(state):
    return [r["experiment_event"] for r in state["results"] if "experiment_event" in r]


def rows(store, state=None, query="", status="", tag=""):
    state = store.state if state is None else state
    choices = {
        r["model_choice"]["run_id"]: r["model_choice"]
        for r in state["results"]
        if "model_choice" in r
    }
    uses = [
        dict(id=r["id"], **r.get("test_use", r.get("time_series_test_use", {})))
        for r in state["results"]
        if "test_use" in r or "time_series_test_use" in r
    ]
    for use in uses:
        # Older temporal reveal entries bind development/result IDs, not a new run ID.
        if not use.get("run_id") and use.get("result_id"):
            final = next(
                (
                    r.get("time_series", {})
                    for r in state["results"]
                    if r["id"] == use["result_id"]
                ),
                {},
            )
            use["run_id"] = final.get("run_id")
        if use.get("run_id") and use["run_id"] not in choices:
            choices[use["run_id"]] = use
    events = _events(state)
    output = []
    seen = set()
    # Search checkpoints share an identity; show only the latest persisted checkpoint.
    records = {}
    for record in state["results"]:
        for kind in (
            "baseline",
            "search",
            "neural",
            "unsupervised",
            "time_series",
            "monitoring",
            "scenario",
            "learning_lab",
            "scientific_report",
            "explanation",
            "analysis",
            "chart",
            "text",
            "text_analysis",
        ):
            run = record.get(kind)
            if run:
                identity = (
                    run.get("run_id")
                    or run.get("training_id")
                    or run.get("search_id")
                    or run.get("result_version")
                    or record.get("result_version")
                    or record["id"]
                )
                records[identity] = (record, kind, run)
    for run_id, (record, kind, run) in records.items():
        choice = choices.get(run_id, {})
        test_capture = next(
            (u.get("experiment_capture") for u in uses if u.get("run_id") == run_id),
            None,
        )
        plan = run.get("plan") or {}
        card = run.get("model_card", {})
        metadata = (
            (run.get("experiment_capture") if kind == "neural" else None)
            or choice.get("experiment_capture")
            or test_capture
            or run.get("experiment_capture")
            or {}
        )
        params = {
            k: run.get(k)
            for k in (
                "spec",
                "preparation_spec",
                "regression",
                "classification",
                "search_spec",
                "vision_spec",
                "audio_spec",
                "recommendation_spec",
                "pattern_spec",
                "graph_spec",
                "stream_spec",
                "target_recipe",
                "code_recipe",
                "workflow_spec",
            )
            if k in run
        }
        own_events = [e for e in events if e.get("run_id") == run_id]
        tags = next(
            (e["value"] for e in reversed(own_events) if e["kind"] == "tags"), []
        )
        model_status = next(
            (e["value"] for e in reversed(own_events) if e["kind"] == "model_status"),
            "candidate",
        )
        revisions = [e for e in own_events if e["kind"] == "metric_revision"]
        evaluations = run.get("evaluations", [])
        # Summary archives omit individual fold details; load only on explicit comparison.
        item = dict(
            run_id=run_id,
            record_id=record["id"],
            kind=kind,
            status=run.get("status", "unknown"),
            dataset_version_ids=record["dataset_version_ids"],
            source_snapshot_id=run.get("source_snapshot_id"),
            snapshot_fingerprint=run.get("snapshot_fingerprint"),
            lineage=run.get("history", {}),
            split_id=plan.get("split_id") or run.get("split_id"),
            protocol_id=plan.get("protocol_id"),
            evaluation_scope=run.get("mode", kind),
            params=params,
            config_hash=metadata.get("config_hash"),
            code_hash=metadata.get("code_hash")
            or run.get("environment", {}).get("engine_sha256"),
            recorded_environment=run.get("environment", run.get("packages", {})),
            compatibility_hash=run.get("compat_id"),
            environment_hash=metadata.get("environment_hash"),
            capture=metadata,
            seed=run.get("seed", record["seed"]),
            data_access_at=run.get("data_access_at"),
            evaluated_at=run.get("evaluated_at", run.get("created_at")),
            duration_seconds=run.get(
                "elapsed_seconds", sum(e.get("elapsed_seconds", 0) for e in evaluations)
            ),
            duration_scope="reported run elapsed"
            if "elapsed_seconds" in run
            else "selected model evaluation sum; not full job wall time",
            metrics=run.get("cv_summary", []),
            evaluations=evaluations,
            artifact_uri=run.get("model_package_uri"),
            artifact_fingerprint=run.get("model_package_fingerprint"),
            model_card=card,
            model_version=run_id if run.get("model_package_uri") else None,
            model_status=model_status,
            warnings=run.get("warnings", [])
            + (
                ["Legacy code/environment/config hashes unavailable"]
                if not metadata
                else []
            ),
            tags=tags,
            revisions=revisions,
            prior_test_use_ids=run.get(
                "prior_test_use_ids", choice.get("prior_test_use_ids", [])
            ),
            test_uses=[
                u
                for u in uses
                if u.get("run_id") == run_id or u.get("development_run_id") == run_id
            ],
            test_seen_before=bool(
                run.get("prior_test_use_ids", choice.get("prior_test_use_ids", []))
            ),
            historical_access_unknown=not bool(run.get("data_access_at")),
        )
        output.append(item)
        seen.add(run_id)
    for run_id, choice in choices.items():
        if run_id not in seen:
            output.append(
                dict(
                    run_id=run_id,
                    record_id=None,
                    kind="model_choice",
                    status=choice["status"],
                    tags=[],
                    warnings=["No completed result artifact"],
                    model_version=None,
                    prior_test_use_ids=choice["prior_test_use_ids"],
                    test_seen_before=bool(choice["prior_test_use_ids"]),
                    capture=choice.get("experiment_capture", {}),
                )
            )
    return [
        r
        for r in output
        if (
            not query
            or query.casefold()
            in (r["run_id"] + " " + r["kind"] + " " + " ".join(r["tags"])).casefold()
        )
        and (not status or r["status"] == status)
        and (not tag or tag in r["tags"])
    ]


def event(store, state, run_id, kind, value, control=None):
    from veri_ufku.storage.validation_store import transaction

    def add(draft):
        available = {r["run_id"]: r for r in rows(store, draft)}
        if kind != "quota" and run_id not in available:
            raise ProjectError("Kayıtlı run seçin.")
        if kind == "model_status" and not available[run_id].get("model_version"):
            raise ProjectError("Güvenli artifact olmayan koşu model sürümü değildir.")
        if kind == "metric_revision":
            metrics = compare(store, [run_id], value, control)["rows"][0].get(
                "evaluation_metrics", []
            )
            if not metrics:
                raise ProjectError("Bu run için gerçek fold metriği yok.")
        if kind == "model_route":
            from veri_ufku.storage.monitor_store import models

            candidates = models(draft)
            if (
                value.get("record_id") not in candidates
                or candidates[value["record_id"]]["run_id"] != run_id
            ):
                raise ProjectError("Model route/run bağı geçersiz.")
            verify(store, available[run_id], control)
        if kind == "model_status" and value == "selected":
            verify(store, available[run_id], control)
        e = dict(
            schema="ExperimentEvent/v1",
            id="revision:" + uid(),
            run_id=run_id,
            kind=kind,
            value=value,
            created_at=datetime.now(UTC).isoformat(),
            previous_hash=digest(encode(_events(draft))),
        )
        from veri_ufku.domain.contracts import Provenance

        item = available.get(run_id, {})
        e["provenance"] = asdict(
            Provenance(
                provenance_id="provenance:" + uid(),
                dataset_versions=tuple(item.get("dataset_version_ids", [])),
                config_revision=len(_events(draft)),
                capability_id="model.experiment-registry",
                parameters_hash=digest(encode(dict(kind=kind, value=value))),
                environment=(("storage", "ProjectStore"),),
                created_at=e["created_at"],
                scope="local registry revision; no fit or deploy",
                seed=item.get("seed"),
                source_snapshot_ids=tuple(
                    [item["source_snapshot_id"]]
                    if item.get("source_snapshot_id")
                    else []
                ),
            )
        )
        # Normalize tuples to the safe ProjectStore JSON representation.
        import json

        e = json.loads(encode(e))
        e["hash"] = digest(encode(e))
        record = dict(
            id="result:" + uid(),
            dataset_version_ids=available.get(run_id, {}).get(
                "dataset_version_ids", []
            ),
            seed=None,
            capability_id="model.experiment-registry",
            experiment_event=e,
        )
        draft["results"].append(record)
        validate(draft)

    return transaction(store, state, add)


def validate(state):
    for record in state["results"]:
        for kind in ("model_choice", "test_use"):
            c = record.get(kind, {}).get("experiment_capture")
            if c:
                if (
                    c.get("schema") != "RunCapture/v1"
                    or c.get("code_hash") != digest(encode(c["code_files"]))
                    or c.get("environment_hash") != digest(encode(c["environment"]))
                ):
                    raise ProjectError("Run capture code/environment hash bağı bozuk.")
                for field in ("config_hash", "code_hash", "environment_hash"):
                    if not isinstance(c.get(field), str) or not re.fullmatch(
                        "[0-9a-f]{64}", c[field]
                    ):
                        raise ProjectError("Run capture hash geçersiz.")
    previous = []
    known = {
        r.get(k, {}).get("run_id", r.get(k, {}).get("search_id"))
        for r in state["results"]
        for k in (
            "baseline",
            "model_choice",
            "search",
            "neural",
            "unsupervised",
            "time_series",
            "monitoring",
            "scenario",
            "learning_lab",
            "scientific_report",
            "explanation",
            "text_analysis",
        )
    }
    known.update(r["id"] for r in state["results"] if "experiment_event" not in r)
    known.update(
        r.get("result_version") for r in state["results"] if "experiment_event" not in r
    )
    known.update(
        r.get(k, {}).get("result_version")
        for r in state["results"]
        for k in ("analysis", "chart", "text")
    )
    for e in _events(state):
        expected = {
            "schema",
            "provenance",
            "id",
            "run_id",
            "kind",
            "value",
            "created_at",
            "previous_hash",
            "hash",
        }
        if (
            set(e) != expected
            or e["schema"] != "ExperimentEvent/v1"
            or e["previous_hash"] != digest(encode(previous))
            or e["hash"] != digest(encode({k: v for k, v in e.items() if k != "hash"}))
        ):
            raise ProjectError("Experiment immutable revision/hash zinciri bozuk.")
        kind, v = e["kind"], e["value"]
        p = e["provenance"]
        if (
            p["capability_id"] != "model.experiment-registry"
            or p["parameters_hash"] != digest(encode(dict(kind=kind, value=v)))
            or p["created_at"] != e["created_at"]
            or p["config_revision"] != len(previous)
        ):
            raise ProjectError("Registry Provenance bağı bozuk.")
        if kind != "quota" and e["run_id"] not in known:
            raise ProjectError("Experiment run bağı bulunamadı.")
        if kind == "model_status":
            valid = v in ("candidate", "selected", "archived")
        elif kind == "tags":
            valid = (
                isinstance(v, list)
                and len(v) <= 16
                and all(
                    isinstance(t, str)
                    and re.fullmatch(r"[a-zA-Z0-9_-]{1,32}", t)
                    and not re.search(r"secret|token|password|credential|key", t, re.I)
                    for t in v
                )
            )
        elif kind == "metric_revision":
            valid = v in (
                "mae",
                "rmse",
                "mase",
                "r2",
                "accuracy",
                "f1",
                "log_loss",
                "brier",
                "precision",
                "recall",
                "ndcg",
                "ap",
            )
        elif kind == "model_route":
            from veri_ufku.storage.monitor_store import models

            candidates = models(state)
            earlier = next(
                (x for x in reversed(previous) if x["kind"] == "model_route"), None
            )
            expected_keys = {
                "record_id",
                "model_fingerprint",
                "previous_record_id",
                "previous_event_id",
                "reason",
                "rollback",
                "scope",
            }
            valid = (
                isinstance(v, dict)
                and set(v) == expected_keys
                and v["record_id"] in candidates
                and e["run_id"] == candidates[v["record_id"]]["run_id"]
                and v["model_fingerprint"] == candidates[v["record_id"]]["fingerprint"]
                and v["previous_record_id"]
                == (earlier["value"]["record_id"] if earlier else None)
                and v["previous_event_id"] == (earlier["id"] if earlier else None)
                and v["reason"] in ("manual_selection", "shadow_review", "rollback")
                and type(v["rollback"]) is bool
                and v["rollback"] == (v["reason"] == "rollback")
                and (
                    not v["rollback"]
                    or earlier is not None
                    and earlier["value"]["previous_record_id"] == v["record_id"]
                )
                and v["scope"]
                == "local explicit scoring reference; no external deployment"
            )
        elif kind == "quota":
            valid = (
                e["run_id"] is None and type(v) is int and 16 * 1024**2 <= v <= 1024**4
            )
        else:
            valid = False
        if not valid:
            raise ProjectError("Experiment durum/tag/metric/quota tarifi geçersiz.")
        previous.append(e)


def quota(state):
    return next(
        (e["value"] for e in reversed(_events(state)) if e["kind"] == "quota"),
        4 * 1024**3,
    )


def usage(store):
    # All immutable artifact files, including historical unreferenced versions, count.
    total = 0
    for folder in ("sources", "snapshots"):
        for path in store.path(folder).iterdir():
            if path.is_symlink():
                raise ProjectError("Quota dizininde symlink var.")
            if path.is_file():
                total += path.stat().st_size
    return total


def verify(store, item, control=None):
    from veri_ufku.importers.delimited import Control

    control = control or Control()
    checked = []
    record = next(
        (r for r in store.state["results"] if r["id"] == item.get("record_id")), {}
    )
    run = record.get(item["kind"], {})
    artifacts = []
    if item["kind"] == "text_analysis" and run.get("advanced", {}).get("details_uri"):
        info = run["advanced"]
        artifacts.append((info["details_uri"], info["details_fingerprint"]))
    for uri_field, fp_field in (
        ("model_package_uri", "model_package_fingerprint"),
        ("details_uri", "details_fingerprint"),
    ):
        if run.get(uri_field):
            artifacts.append((run[uri_field], run[fp_field]))
    for uri in run.get("artifact_uris", {}).values():
        fp = store.manifest["artifacts"][uri]
        artifacts.append((uri, {k: fp[k] for k in ("size", "sha256")}))
    for dataset in store.state["datasets"]:
        if dataset["version_id"] in item.get("dataset_version_ids", []):
            uri = dataset["snapshot_uri"]
            fp = store.manifest["artifacts"][uri]
            artifacts.append((uri, {k: fp[k] for k in ("size", "sha256")}))
    for uri, fp in artifacts:
        path = store.path(uri)
        h = hashlib.sha256()
        control.check()
        if path.is_symlink():
            raise ProjectError("Artifact symlink reddedildi.")
        with path.open("rb") as stream:
            while chunk := stream.read(1024**2):
                control.check()
                h.update(chunk)
        actual = dict(size=path.stat().st_size, sha256=h.hexdigest())
        if actual != fp:
            raise ProjectError("Eski artifact bütünlüğü bozuk; run: " + item["run_id"])
        checked.append(dict(uri=uri, **fp))
    return checked


def compare(store, run_ids, metric="mae", control=None):
    if (
        metric
        not in (
            "mae",
            "rmse",
            "mase",
            "r2",
            "accuracy",
            "f1",
            "log_loss",
            "brier",
            "precision",
            "recall",
            "ndcg",
            "ap",
        )
        or not 1 <= len(run_ids) <= 32
        or len(set(run_ids)) != len(run_ids)
    ):
        raise ProjectError("1–32 benzersiz run ve destekli metric seçin.")
    available = {r["run_id"]: r for r in rows(store)}
    result = []
    for run_id in run_ids:
        if run_id not in available:
            raise ProjectError("Run bulunamadı.")
        item = copy.deepcopy(available[run_id])
        item["verified_artifacts"] = verify(store, item, control)
        if item["kind"] == "baseline":
            from veri_ufku.storage.validation_store import load_run

            record = next(
                r for r in store.state["results"] if r["id"] == item["record_id"]
            )
            run = load_run(store, record)
            item["evaluation_metrics"] = [
                dict(
                    scope=e["scope"],
                    value=m["value"],
                    direction=m["direction"],
                    n=e["evaluation_n"],
                )
                for e in run["evaluations"]
                for m in e.get("metrics", [])
                if m["metric"] == metric and m["value"] is not None
            ]
            item["folds"] = [
                dict(
                    scope=e["scope"],
                    value=m["value"],
                    direction=m["direction"],
                    n=e["evaluation_n"],
                )
                for e in run["evaluations"]
                for m in e.get("metrics", [])
                if m["metric"] == metric
                and e["scope"].startswith("cv:")
                and m["value"] is not None
            ]
            item["protocol_key"] = digest(
                encode(
                    dict(
                        dataset=run["dataset_version"],
                        snapshot=run["snapshot_fingerprint"],
                        split=run["plan"]["split_id"],
                        protocol=run["plan"]["protocol_id"],
                        mode=run["mode"],
                        target=run["preparation_spec"].get("target"),
                        metric=metric,
                        metric_definitions=sorted(
                            {
                                encode(
                                    {
                                        k: m.get(k)
                                        for k in ("direction", "averaging", "coverage")
                                    }
                                ).decode()
                                for e in run["evaluations"]
                                for m in e.get("metrics", [])
                                if m["metric"] == metric
                            }
                        ),
                        decision=run.get("decision"),
                        uncertainty=run.get("uncertainty"),
                    )
                )
            )
        elif item["kind"] == "neural" and item["params"].get("recommendation_spec"):
            from veri_ufku.storage.neural_store import load as load_recommendation

            record = next(
                r for r in store.state["results"] if r["id"] == item["record_id"]
            )
            run = load_recommendation(store, record)
            item["folds"] = [
                dict(
                    scope=q["query"],
                    value=q["metrics"][metric],
                    direction="maximize",
                    n=len(q["relevant_ids"]),
                )
                for q in run["queries"]
                if metric in q["metrics"] and q["metrics"][metric] is not None
            ]
            item["evaluation_metrics"] = item["folds"]
            item["protocol_key"] = (
                digest(
                    encode(
                        dict(
                            dataset=run["dataset_version"],
                            snapshot=run["snapshot_fingerprint"],
                            ranking=run["metrics"].get("comparability_key"),
                            metric=metric,
                        )
                    )
                )
                if run["status"] == "completed" and item["folds"]
                else None
            )
        elif item["kind"] == "time_series":
            from veri_ufku.storage.time_series_store import load as load_series

            record = next(
                r for r in store.state["results"] if r["id"] == item["record_id"]
            )
            run = load_series(store, record)
            item["folds"] = []
            if (
                run.get("advanced", {}).get("schema") == "TemporalRun/v1"
                and run["advanced"]["spec"]["task"] == "forecast"
                and metric in ("mae", "rmse", "mase")
            ):
                for group in run["groups"]:
                    for f in group["folds"]:
                        if (
                            f["method"] == group["chosen"]
                            and f["metrics"].get(metric) is not None
                        ):
                            item["folds"].append(
                                dict(
                                    scope="cv:series-"
                                    + digest(encode(group["series_id"]))[:16]
                                    + ":"
                                    + str(f["origin"])
                                    if run["mode"] == "development"
                                    else "final_test",
                                    value=f["metrics"][metric],
                                    direction="minimize",
                                    n=f["metrics"]["n"],
                                )
                            )
                item["evaluation_metrics"] = item["folds"]
                item["protocol_key"] = digest(
                    encode(
                        dict(
                            dataset=run["dataset_version"],
                            fingerprint=run["snapshot_fingerprint"],
                            plan=run["plan"],
                            mode=run["mode"],
                            metric=metric,
                        )
                    )
                )
            else:
                item["protocol_key"] = None
        else:
            item["folds"] = []
            item["protocol_key"] = None
        chosen = item["folds"] or [
            v
            for v in item.get("evaluation_metrics", [])
            if v["scope"] in ("final_test", "validation", "validation_threshold")
        ]
        item["score_scope"] = (
            (
                "development_cv"
                if any(f["scope"].startswith("cv:") for f in item["folds"])
                else item["folds"][0]["scope"]
            )
            if item["folds"]
            else (chosen[0]["scope"] if chosen else "unavailable")
        )
        values = [v["value"] for v in chosen]
        item["score"] = sum(values) / len(values) if values else None
        result.append(item)
    comparable = (
        all(r.get("protocol_key") for r in result)
        and len({r["protocol_key"] for r in result}) == 1
    )
    warning = (
        []
        if comparable
        else [
            "Evaluation protocol/dataset/split/decision differs or is unknown; no common ranking or Pareto frontier."
        ]
    )
    cost_comparable = len({r.get("duration_scope") for r in result}) == 1
    if not cost_comparable:
        warning.append(
            "Duration scopes differ: full job wall time versus selected evaluation sum; no common cost Pareto frontier."
        )
    points = [
        r
        for r in result
        if r["status"] == "completed"
        and r["score"] is not None
        and r["duration_seconds"] > 0
        and math.isfinite(r["score"])
    ]
    maximize = metric in ("accuracy", "f1", "r2")
    for r in points:

        def better(other):
            score_better = (
                other["score"] >= r["score"]
                if maximize
                else other["score"] <= r["score"]
            )
            strict_score = (
                other["score"] > r["score"] if maximize else other["score"] < r["score"]
            )
            return (
                score_better
                and other["duration_seconds"] <= r["duration_seconds"]
                and (strict_score or other["duration_seconds"] < r["duration_seconds"])
            )

        r["pareto"] = (
            comparable
            and cost_comparable
            and not any(better(o) for o in points if o is not r)
        )
    return dict(
        schema="ExperimentComparison/v1",
        metric=metric,
        comparable=comparable,
        cost_comparable=cost_comparable,
        warnings=warning,
        rows=result,
        points=[
            dict(
                run_id=r["run_id"],
                x=r["duration_seconds"],
                y=r["score"],
                pareto=r["pareto"],
            )
            for r in points
        ],
        note="Metric mean over actual recorded folds or explicit evaluation scope; duration scope shown per run. Same protocol does not establish independent test evidence. Project-external test access is unknown.",
    )


def export(store, run_ids, path, metric="mae", control=None):
    from veri_ufku.importers.delimited import Control

    control = control or Control()
    import tempfile

    from veri_ufku.modeling.lifecycle_worker import publish_file

    report = compare(store, run_ids, metric, control)
    # No free-form params, tags, labels, warnings, paths, model cards or environment values.
    allowed = (
        "run_id",
        "kind",
        "status",
        "dataset_version_ids",
        "split_id",
        "protocol_id",
        "code_hash",
        "config_hash",
        "environment_hash",
        "seed",
        "data_access_at",
        "historical_access_unknown",
        "test_seen_before",
        "prior_test_use_ids",
        "duration_seconds",
        "duration_scope",
        "score",
        "folds",
        "score_scope",
        "model_status",
        "model_version",
    )
    safe = dict(
        schema="ExperimentExport/v1",
        metric=metric,
        comparable=report["comparable"],
        warnings=report["warnings"],
        rows=[{k: r.get(k) for k in allowed} for r in report["rows"]],
        limitation="Hashes and IDs retained; raw configuration/card/tags/labels omitted. Not an anonymity guarantee.",
    )
    with tempfile.TemporaryDirectory() as td:
        source = Path(td) / "export.json"
        source.write_bytes(encode(safe))
        publish_file(source, Path(path), control)
    return safe
