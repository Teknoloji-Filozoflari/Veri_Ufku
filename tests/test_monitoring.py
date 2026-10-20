"""Phase67 reference drift, delayed identity matching, shadow and real rollback."""

import copy
import json
from contextlib import closing
from dataclasses import replace

import numpy as np
import polars as pl
import pytest
from test_dataset import column, prepare
from test_regression import synthetic
from test_relational import add_source

from veri_ufku.modeling.baseline import calculate as train
from veri_ufku.modeling.monitor_contracts import MonitorSpec
from veri_ufku.modeling.monitoring import (
    calculate,
    distribution,
    evaluate,
    public_report,
)
from veri_ufku.storage import monitor_store as storage
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.validation_store import choice, complete


def spec(r, w, **kwargs):
    return MonitorSpec(
        reference=r["version_id"],
        window=w["version_id"],
        features=[
            dict(
                reference=column(r, "x"),
                window=column(w, "x"),
                kind="numeric",
                continuous=True,
            )
        ],
        window_start="2026-01-01T00:00:00Z",
        window_end="2026-02-01T00:00:00Z",
        as_of="2026-02-02T00:00:00Z",
        min_n=2,
        **kwargs,
    )


def fixture(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame({"x": np.linspace(0, 1, 30), "category": ["A", "B"] * 15}),
    )
    w = add_source(
        store,
        work,
        pl.DataFrame({"x": np.linspace(10, 11, 30), "category": ["C"] * 30}),
    )
    return store, r, w, work, spec(r, w)


def trained_fixture(tmp_path):
    store, r, work, protocol = synthetic(tmp_path)
    rid = "run:" + uid()
    r["run_id"] = rid
    choice(
        store,
        store.state,
        r["version_id"],
        protocol.data(),
        r["preparation"]["plan"]["version_id"],
        rid,
    )
    out = train(r, protocol.data(), work)
    complete(store, store.state, result=out, run_id=rid)
    model = next(
        k for k, v in storage.models(store.state).items() if v["run_id"] == rid
    )
    w = add_source(
        store,
        work,
        pl.DataFrame(
            {
                "x": np.linspace(20, 30, 30),
                "business_id": [f"w{i}" for i in range(30)],
                "when": ["2026-01-15T00:00:00Z"] * 30,
            }
        ),
    )
    reference = add_source(store, work, pl.DataFrame({"x": np.linspace(-4.9, 4.9, 30)}))
    return (
        store,
        r,
        w,
        work,
        spec(
            reference,
            w,
            champion=model,
            window_key=column(w, "business_id"),
            event_time=column(w, "when"),
        ),
    )


def test_drift_fixture_no_labels_snapshot_identity_and_reopen(tmp_path):
    store, r, w, work, s = fixture(tmp_path)
    root = store.root
    with closing(store):
        request = storage.request_for(store, store.state, s.data())
        before = {
            k: open(v["path"], "rb").read() for k, v in request["sources"].items()
        }
        out = calculate(request, s.data(), work)
        assert out["features"][0]["distribution"]["alarm"]
        assert out["features"][0]["distribution"]["wasserstein"] == pytest.approx(10)
        assert out["models"] == [] and out["shadow"]["status"] == "not_configured"
        assert out["fit_calls"] == 0 and out["window"]["n"] == 30
        assert out["membership"]["window_source_record_ids"]
        state = storage.publish(store, store.state, out)
        record = state["results"][-1]
        assert storage.load(store, record) == out
        assert "membership" not in public_report(out)
        assert all(
            open(v["path"], "rb").read() == before[k]
            for k, v in request["sources"].items()
        )
    with closing(ProjectStore.open(root)) as opened:
        assert storage.load(opened, opened.state["results"][-1]) == out
        path = opened.path(record["monitoring"]["details_uri"])
        path.write_bytes(path.read_bytes() + b"bad")
        with pytest.raises(ProjectError, match="hash"):
            storage.load(opened, record)


def test_psi_manual_js_support_constant_missing_and_ks(tmp_path):
    store, r, w, work, s = fixture(tmp_path)
    with closing(store):
        s = replace(s, bins=2, independent=True)
        d = distribution([0.0, 1.0, 2.0, 3.0], [0.0, 1.0, 2.0, 3.0], "numeric", s, True)
        assert d["psi"] == 0 and d["wasserstein"] == 0 and d["ks_p"] == 1
        d = distribution(
            [0.0, 1.0, 2.0, 3.0], [8.0, 9.0, 10.0, 11.0], "numeric", s, True
        )
        p = np.array([2.5, 2.5]) / 5
        q = np.array([0.5, 4.5]) / 5
        assert d["psi"] == pytest.approx(float(np.sum((q - p) * np.log(q / p))))
        assert d["window_counts"] == [0, 4]
        assert distribution([1.0] * 20, [1.0] * 20, "numeric", s, True)["ks_p"] is None
        assert distribution([None], [2.0], "numeric", s)["status"] == "insufficient_n"
        c = distribution(["A"] * 10, ["B"] * 10, "categorical", s)
        assert c["js_distance"] == 1 and c["unseen_count"] == 10
        assert "A" not in c["category_hashes"]


def test_model_no_labels_and_window_selection(tmp_path):
    store, r, w, work, s = trained_fixture(tmp_path)
    with closing(store):
        out = calculate(
            storage.request_for(store, store.state, s.data()), s.data(), work
        )
        assert out["models"][0]["window_evaluation"] == dict(
            status="labels_unavailable", n=0, metrics=None, calibration=None
        )
        assert out["prediction_drift"][0]["distribution"]["wasserstein"] > 0
        assert out["models"][0]["performance_changes"] == []
        assert len(out["prediction_records"]["champion"]) == 30
        assert [p["source_key"] for p in out["prediction_records"]["champion"]] == [
            f"w{i}" for i in range(30)
        ]
        storage.publish(store, store.state, out)


def test_delayed_labels_shuffled_unique_keys_and_reference_metrics(tmp_path):
    store, r, w, work, s = trained_fixture(tmp_path)
    with closing(store):
        y = 3 * np.linspace(20, 30, 30) + 7
        labels = pl.DataFrame(
            {
                "id": [f"w{i}" for i in reversed(range(30))],
                "target": y[::-1],
                "arrived": ["2026-02-01T00:00:00Z"] * 29 + ["2026-03-01T00:00:00Z"],
            }
        )
        label_source = add_source(store, work, labels)
        s = replace(
            s,
            labels=label_source["version_id"],
            label_key=column(label_source, "id"),
            label_value=column(label_source, "target"),
            label_arrived=column(label_source, "arrived"),
            key_namespace="orders-v1",
        )
        out = calculate(
            storage.request_for(store, store.state, s.data()), s.data(), work
        )
        e = out["models"][0]["window_evaluation"]
        assert e["n"] == 29 and e["metrics"]["mae"] < 1e-10
        assert e["label_delay"]["pending"] == 1 and e["label_delay"]["overdue"] == 1
        assert e["label_delay"]["observed_mean_seconds"] == 17 * 86400
        assert out["models"][0]["calibration_change"] is None
        storage.publish(store, store.state, out)


def test_evaluation_probability_label_order_reference_and_unseen(tmp_path):
    store, r, w, work, s = fixture(tmp_path)
    with closing(store):
        label_source = add_source(
            store,
            work,
            pl.DataFrame(
                {
                    "id": ["b", "a"],
                    "y": ["yes", "no"],
                    "arrived": ["2026-01-20T00:00:00Z"] * 2,
                }
            ),
        )
        s = replace(
            s,
            labels=label_source["version_id"],
            champion="record:model",
            window_key="key",
            label_key=column(label_source, "id"),
            label_value=column(label_source, "y"),
            label_arrived=column(label_source, "arrived"),
            key_namespace="orders",
        )
        records = [
            dict(source_key="a", prediction="no", probabilities=[0.8, 0.2]),
            dict(source_key="b", prediction="yes", probabilities=[0.3, 0.7]),
        ]
        card = dict(purpose="classification", label_order=["no", "yes"])
        frame = pl.read_parquet(label_source["path"])
        e = evaluate(
            records, frame, s, label_source, "source_key", card, 1770000000, {}
        )
        assert e["metrics"]["accuracy"] == 1
        assert e["metrics"]["brier_multiclass_sum"] == pytest.approx(0.13)
        assert e["metrics"]["log_loss"] == pytest.approx(-np.log(0.8 * 0.7) / 2)
        assert e["calibration"]["label_order"] == ["no", "yes"]
        assert [
            sum(b["n"] for b in v["bins"]) for v in e["calibration"]["reliability"]
        ] == [2, 2]
        with pytest.raises(ProjectError, match="unique"):
            evaluate(
                records,
                pl.concat([frame, frame]),
                s,
                label_source,
                "source_key",
                card,
                1770000000,
                {},
            )
        with pytest.raises(ProjectError, match="Unseen"):
            evaluate(
                records,
                frame.with_columns(pl.lit("unknown").alias("y")),
                s,
                label_source,
                "source_key",
                card,
                1770000000,
                {},
            )


def test_shadow_and_real_route_rollback_preserves_artifacts_lineage(tmp_path):
    store, r, w, work, s = trained_fixture(tmp_path)
    root = store.root
    with closing(store):
        champion = s.champion
        # A second real train/run/package, not a renamed duplicate model record.
        rid = "run:" + uid()
        r["run_id"] = rid
        second = work / "second"
        second.mkdir()
        protocol = (
            store.state["results"][0]["model_choice"]["spec"]
            if "model_choice" in store.state["results"][0]
            else None
        )
        from veri_ufku.modeling.validation import ValidationSpec

        protocol = ValidationSpec(
            prediction_moment="shadow second explicit train",
            availability={
                f: dict(offset_seconds=0, note="known")
                for f in r["preparation"]["spec"]["features"]
            },
        )
        choice(
            store,
            store.state,
            r["version_id"],
            protocol.data(),
            r["preparation"]["plan"]["version_id"],
            rid,
        )
        complete(
            store, store.state, result=train(r, protocol.data(), second), run_id=rid
        )
        challenger = next(k for k in storage.models(store.state) if k != champion)
        s = replace(s, challenger=challenger)
        out = calculate(
            storage.request_for(store, store.state, s.data()), s.data(), work
        )
        assert (
            out["shadow"]["status"] == "same_batch_no_deploy"
            and not out["shadow"]["performance_available"]
        )
        assert storage.route(store.state) is None
        storage.publish(store, store.state, out)
        before = {k: dict(v) for k, v in storage.models(store.state).items()}
        storage.activate(store, store.state, champion, "manual_selection")
        storage.activate(store, store.state, challenger, "shadow_review")
        storage.activate(store, store.state, champion, "rollback", True)
        assert storage.route(store.state)["value"]["record_id"] == champion
        assert storage.models(store.state) == before
        routed = replace(s, champion="", challenger="", use_champion_route=True)
        after = calculate(
            storage.request_for(store, store.state, routed.data()), routed.data(), work
        )
        assert after["models"][0]["record_id"] == champion
        assert after["models"][0]["fingerprint"] == before[champion]["fingerprint"]
        from veri_ufku.storage.lineage import graph

        g = graph(store.state, store.manifest)
        assert any(e["relation"] == "rollback_reference" for e in g["edges"])
        commit = store.commit_id
        with pytest.raises(ProjectError):
            storage.activate(store, store.state, champion, "rollback", True)
        assert store.commit_id == commit
    with closing(ProjectStore.open(root)) as reopened:
        assert storage.route(reopened.state)["value"]["record_id"] == champion
        assert storage.models(reopened.state) == before


@pytest.mark.parametrize(
    "changes",
    [
        dict(alpha=0),
        dict(bins=0),
        dict(psi_threshold=float("nan")),
        dict(independent=1),
        dict(window_end="2027-01-01T00:00:00Z"),
        dict(as_of="2026-02-02"),
        dict(challenger="model-only"),
        dict(token="secret"),
    ],
)
def test_closed_recipe_rejects_invalid(changes):
    s = dict(
        reference="dv:a",
        window="dv:b",
        features=[
            dict(reference="col:a", window="col:b", kind="numeric", continuous=True)
        ],
        window_start="2026-01-01T00:00:00Z",
        window_end="2026-02-01T00:00:00Z",
        as_of="2026-02-02T00:00:00Z",
    )
    with pytest.raises(ProjectError):
        MonitorSpec.from_dict(dict(s, **changes))


def test_actual_cli_scoring_explicit_opt_in(tmp_path):
    import os
    import subprocess
    import sys

    store, r, w, work, s = fixture(tmp_path)
    project = str(store.root)
    before = store.commit_id
    store.close()
    recipe = tmp_path / "recipe.json"
    recipe.write_text(json.dumps(s.data()))
    command = [
        sys.executable,
        "-m",
        "veri_ufku.modeling.monitor_cli",
        "--project",
        project,
        "--cache",
        str(tmp_path / "cache"),
        "--spec",
        str(recipe),
    ]
    env = dict(os.environ)
    denied = subprocess.run(
        command, capture_output=True, text=True, env=env, timeout=30
    )
    assert denied.returncode == 2 and "opt-in" in denied.stdout
    with closing(ProjectStore.open(project)) as reopened:
        assert reopened.commit_id == before
    result = subprocess.run(
        command + ["--allow-batch-scoring"],
        capture_output=True,
        text=True,
        env=env,
        timeout=40,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["labels"].startswith("unavailable")
    with closing(ProjectStore.open(project)) as reopened:
        assert reopened.commit_id != before
        assert reopened.state["results"][-1]["monitoring"]["fit_calls"] == 0


def test_schema_missing_column_and_quality_contract(tmp_path):
    store, r, w, work, s = fixture(tmp_path)
    with closing(store):
        request = storage.request_for(store, store.state, s.data())
        # Real source-bound quality request inherited from a dataset contract.
        request["sources"][s.window]["schema_contract"] = dict(
            definition_version=s.window,
            status="checked",
            definition=dict(
                schema_version=1,
                rules=[
                    dict(
                        id="range",
                        kind="range",
                        column_id=column(w, "x"),
                        severity="error",
                        parameters=dict(minimum="0", maximum="5"),
                    )
                ],
            ),
        )
        out = calculate(request, s.data(), work)
        assert out["data_quality"]["window"]["error_violations"] == 30
        assert out["data_quality"]["window"]["silent_corrections"] == 0
        missing = replace(
            s,
            features=[
                dict(
                    reference=column(r, "x"),
                    window="col:missing",
                    kind="numeric",
                    continuous=True,
                )
            ],
        )
        out = calculate(
            storage.request_for(store, store.state, missing.data()),
            missing.data(),
            work,
        )
        assert out["schema_drift"][0]["status"] == "missing_mapped_column"
        assert out["features"][0]["distribution"]["alarm"]


def test_reference_current_label_key_overlap_rejected_and_route_scoring(tmp_path):
    store, r, w, work, s = trained_fixture(tmp_path)
    with closing(store):
        storage.activate(store, store.state, s.champion, "manual_selection")
        routed = replace(s, champion="", use_champion_route=True)
        request = storage.request_for(store, store.state, routed.data())
        out = calculate(request, routed.data(), work)
        assert out["models"][0]["record_id"] == s.champion
        assert out["route_event_id"] == storage.route(store.state)["id"]
        storage.publish(store, store.state, out)
        original = copy.deepcopy(store.state)
        stale = copy.deepcopy(original)
        stale["results"] = [r for r in stale["results"] if "monitoring" not in r]
        from veri_ufku.storage.experiment_store import event

        with pytest.raises(ProjectError, match="defteri"):
            event(store, stale, None, "quota", 32 * 1024**2)
        assert store.state == original


def test_model_final_test_bypass_and_tampered_worker_result_rejected(tmp_path):
    store, r, w, work, s = trained_fixture(tmp_path)
    with closing(store):
        bad = replace(
            s,
            reference=r["version_id"],
            features=[
                dict(
                    reference=column(r, "x"),
                    window=column(w, "x"),
                    kind="numeric",
                    continuous=True,
                )
            ],
        )
        with pytest.raises(ProjectError, match="final-test"):
            calculate(
                storage.request_for(store, store.state, bad.data()), bad.data(), work
            )
        out = calculate(
            storage.request_for(store, store.state, s.data()), s.data(), work
        )
        out["fit_calls"] = 1
        before = store.commit_id
        with pytest.raises(ProjectError):
            storage.publish(store, store.state, out)
        assert store.commit_id == before


def test_real_classification_calibration_and_performance_change(tmp_path):
    from test_classification import synthetic as classification

    store, r, work, protocol = classification(tmp_path, n=90)
    with closing(store):
        rid = "run:" + uid()
        r["run_id"] = rid
        choice(
            store,
            store.state,
            r["version_id"],
            protocol.data(),
            r["preparation"]["plan"]["version_id"],
            rid,
        )
        complete(store, store.state, result=train(r, protocol.data(), work), run_id=rid)
        model = next(iter(storage.models(store.state)))
        values = np.linspace(-2.9, 2.9, 30)
        reference = add_source(
            store, work, pl.DataFrame({"x": values, "id": [f"r{i}" for i in range(30)]})
        )
        window = add_source(
            store, work, pl.DataFrame({"x": values, "id": [f"w{i}" for i in range(30)]})
        )
        normal = np.where(values > 1.5, "risk", "normal").tolist()
        inverted = ["normal" if v == "risk" else "risk" for v in normal]
        labels = add_source(
            store,
            work,
            pl.DataFrame(
                {
                    "id": [f"r{i}" for i in range(30)] + [f"w{i}" for i in range(30)],
                    "target": normal + inverted,
                    "arrival": ["2026-02-01T00:00:00Z"] * 60,
                }
            ),
        )
        s = spec(
            reference,
            window,
            champion=model,
            reference_key=column(reference, "id"),
            window_key=column(window, "id"),
            labels=labels["version_id"],
            label_key=column(labels, "id"),
            label_value=column(labels, "target"),
            label_arrived=column(labels, "arrival"),
            key_namespace="classification-events",
        )
        out = calculate(
            storage.request_for(store, store.state, s.data()), s.data(), work
        )
        result = out["models"][0]
        assert result["window_evaluation"]["calibration"]["n"] == 30
        assert result["calibration_change"]["alarm"]
        assert any(
            v["metric"] == "accuracy" and v["alarm"]
            for v in result["performance_changes"]
        )
        assert out["prediction_drift"][0]["distribution"]["psi"] == 0
        # No input/prediction drift is needed for measured performance to change.
        storage.publish(store, store.state, out)
