"""Independent references, scope leakage, frozen inference and uncertainty support."""

import copy
from contextlib import closing
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import brier_score_loss, log_loss
from test_model_families import fixture

from veri_ufku.modeling.baseline import calculate, validate_saved
from veri_ufku.modeling.lifecycle import load_package, predict, save_package
from veri_ufku.modeling.uncertainty import (
    UncertaintySpec,
    conformal_quantile,
    probability_report,
    threshold_choice,
)
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.validation_store import (
    choice,
    complete,
    prior_uses,
    reserve_test,
)

CASES = [
    ("classification", "logistic", "sigmoid", "sets"),
    ("classification", "forest", "isotonic", "sets"),
    ("classification", "forest", "none", "sets"),
    ("regression", "ridge", "none", "interval"),
    ("regression", "forest", "none", "interval"),
    ("regression", "quantile", "none", "quantile"),
    ("regression", "quantile", "none", "cqr"),
]


def request(tmp_path, purpose, model, calibration, prediction):
    store, r, work, protocol = fixture(tmp_path, purpose)
    spec = UncertaintySpec(
        model=model,
        calibration=calibration,
        prediction=prediction,
        threshold="cost" if purpose == "classification" else "default",
        positive_class="risk" if purpose == "classification" else "",
    )
    config = dict(
        candidates=["baseline", "ridge" if model == "quantile" else model],
        uncertainty=spec.data(),
    )
    if purpose == "classification":
        config["positive_class"] = "risk"
    r[purpose] = config
    return store, r, work, protocol


@pytest.mark.parametrize("purpose,model,calibration,prediction", CASES)
def test_native_template_safe_package_inference_and_empirical_coverage(
    tmp_path, purpose, model, calibration, prediction
):
    store, r, work, protocol = request(
        tmp_path, purpose, model, calibration, prediction
    )
    with closing(store):
        original = pl.read_parquet(r["path"])
        result = calculate(r, protocol.data(), work)
        model, card = load_package(result["model_package"]["path"])
        validate_saved(
            dict(
                baseline=result,
                seed=protocol.seed,
                capability_id="model." + purpose,
                dataset_version_ids=[r["version_id"]],
            ),
            {d["version_id"]: d for d in store.state["datasets"]},
        )
        ids = result["uncertainty"]["membership"]
        assert not set(ids["fit"]) & set(
            ids["probability_calibration"]
            + ids["conformal_calibration"]
            + ids["validation"]
            + ids["test"]
        )
        assert (
            card["fit_row_ids"] == ids["fit"]
            or sorted(card["fit_row_ids"]) == ids["fit"]
        )
        out, report = predict(model, card, original, r["columns"], batch_size=17)
        assert out["__vu_row_id"].to_list() == original["__vu_row_id"].to_list()
        assert report["fit_calls"] == 0
        assert (
            report["uncertainty"]["partition_id"]
            == result["uncertainty"]["partition_id"]
        )
        metrics = result["evaluations"][0]["uncertainty_report"]
        assert 0 <= metrics["empirical_coverage"] <= 1
        if purpose == "classification":
            assert "vu_prediction_set" in out.columns
            rows = result["evaluations"][0]["prediction_records"]
            assert metrics["empirical_coverage"] == np.mean(
                [v["actual"] in v["prediction_set"] for v in rows]
            )
        else:
            assert "vu_predictive_lower" in out.columns
            assert (out["vu_predictive_lower"] <= out["vu_predictive_upper"]).all()
        assert pl.read_parquet(r["path"]).equals(original)


@pytest.mark.parametrize("calibration", ["sigmoid", "isotonic"])
def test_calibration_exact_sklearn_frozen_reference_and_fit_spy(
    tmp_path, monkeypatch, calibration
):
    store, r, work, protocol = request(
        tmp_path, "classification", "logistic", calibration, "sets"
    )
    from veri_ufku.modeling.baseline import FoldPreparation

    seen = []
    fit = FoldPreparation.fit

    def spy(self, X, y=None):
        seen.append(X["__vu_row_id"].to_list())
        return fit(self, X, y)

    monkeypatch.setattr(FoldPreparation, "fit", spy)
    with closing(store):
        result = calculate(r, protocol.data(), work)
        model, card = load_package(result["model_package"]["path"])
        pools = result["uncertainty"]["membership"]
        assert len(seen) == 1 and sorted(seen[0]) == pools["fit"]
        frame = pl.read_parquet(r["path"])
        cal = frame.filter(
            pl.col("__vu_row_id").is_in(pools["probability_calibration"])
        )
        x = model.named_steps["prepare"].transform(cal)
        reference = CalibratedClassifierCV(
            FrozenEstimator(model.named_steps["baseline"].base), method=calibration
        ).fit(x, cal["y"].to_numpy())
        np.testing.assert_allclose(
            model.predict_proba(frame),
            reference.predict_proba(model.named_steps["prepare"].transform(frame)),
            rtol=1e-12,
            atol=1e-12,
        )
        assert card["label_order"] == ["normal", "risk"]


def test_probability_reference_label_order_bins_and_unseen():
    y = np.array(["z", "a", "z", "a"])
    p = np.array([[0.8, 0.2], [0.3, 0.7], [0.6, 0.4], [0.1, 0.9]])
    report = probability_report(y, p, ["z", "a"], 4)
    assert report["brier"] == pytest.approx(brier_score_loss(y == "z", p[:, 0]))
    assert report["log_loss"] == pytest.approx(
        log_loss(y, p[:, [1, 0]], labels=["a", "z"])
    )
    fraction, mean = calibration_curve(y == "z", p[:, 0], n_bins=4)
    np.testing.assert_allclose(
        [v["mean_probability"] for v in report["reliability"][0]["points"]], mean
    )
    np.testing.assert_allclose(
        [v["fraction_positive"] for v in report["reliability"][0]["points"]], fraction
    )
    with pytest.raises(ProjectError, match="unseen"):
        probability_report(["new"], [[0.5, 0.5]], ["z", "a"], 4)


def test_hand_threshold_cost_constraint_and_quantile():
    spec = UncertaintySpec(positive_class="yes", false_negative_cost=4, min_recall=1)
    result = threshold_choice(
        np.array(["no", "no", "yes", "yes"]),
        np.array([[0.9, 0.1], [0.6, 0.4], [0.7, 0.3], [0.2, 0.8]]),
        ["no", "yes"],
        spec,
    )
    assert result["winner"]["threshold"] == 0.3
    assert result["winner"]["cost_per_record"] == 0.25
    q, rank = conformal_quantile([1, 2, 3, 4, 5, 6, 7, 8, 9], 0.2)
    assert (q, rank) == (8.0, 8)
    with pytest.raises(ProjectError, match="yetersiz"):
        conformal_quantile([1, 2], 0.05)
    with pytest.raises(ProjectError, match="desteklenmiyor"):
        UncertaintySpec.from_dict(dict(model="svm"), "classification")
    with pytest.raises(ProjectError, match="yalnız quantile"):
        UncertaintySpec.from_dict(
            dict(
                model="ridge",
                calibration="none",
                threshold="default",
                prediction="quantile",
            ),
            "regression",
        )


def test_frozen_final_zero_fit_journal_repeat_and_tamper(tmp_path, monkeypatch):
    store, r, work, protocol = request(
        tmp_path, "regression", "ridge", "none", "interval"
    )
    with closing(store):
        r["run_id"] = "run:development50"
        store.state = choice(
            store,
            store.state,
            r["version_id"],
            protocol.data(),
            r["preparation"]["plan"]["version_id"],
            r["run_id"],
            regression=r["regression"],
        )
        r["history_state"] = store.state
        dev = calculate(r, protocol.data(), work)
        store.state = complete(store, store.state, dev, run_id=r["run_id"])
        stored = next(x["baseline"] for x in store.state["results"] if "baseline" in x)
        state, test_id = reserve_test(store, store.state, stored, "run:final50")
        store.state = state
        from veri_ufku.modeling.baseline import FoldPreparation

        monkeypatch.setattr(
            FoldPreparation, "fit", lambda *a, **k: pytest.fail("final refit leakage")
        )
        f = dict(
            r,
            run_id="run:final50",
            mode="final",
            history_state=state,
            prior_test_use_ids=[],
            expected_split_id=dev["plan"]["split_id"],
            expected_protocol_id=dev["plan"]["protocol_id"],
            frozen_uncertainty_package=dict(
                path=str(store.path(stored["model_package_uri"])),
                fingerprint=stored["model_package_fingerprint"],
            ),
        )
        result = calculate(f, protocol.data(), work)
        assert result["fit_count"] == 0
        store.state = complete(store, store.state, result, test_id, run_id=f["run_id"])
        uses = prior_uses(store.state)
        store.state = choice(
            store,
            store.state,
            r["version_id"],
            protocol.data(),
            r["preparation"]["plan"]["version_id"],
            "run:new50",
            regression=r["regression"],
        )
        assert prior_uses(store.state) == uses
        altered = copy.deepcopy(result)
        altered["evaluations"][0]["uncertainty_report"]["empirical_coverage"] = 123
        with pytest.raises(ProjectError, match="coverage"):
            validate_saved(
                dict(
                    baseline=altered,
                    seed=protocol.seed,
                    capability_id="model.regression",
                    dataset_version_ids=[r["version_id"]],
                ),
                {d["version_id"]: d for d in store.state["datasets"]},
            )
        model, card = load_package(dev["model_package"]["path"])
        model.named_steps["baseline"].q = 999
        with pytest.raises(ProjectError, match="q uyuşmuyor"):
            save_package(work / "tampered.vumodel", model, card)


@pytest.mark.parametrize("structure", ["independent", "group", "time", "group_time"])
def test_shared_joint_partition_group_time_horizon(structure):
    from veri_ufku.modeling.uncertainty import partitions
    from veri_ufku.modeling.validation import ValidationSpec, split_plan

    n = 400
    ids = [f"row:{i}" for i in range(n)]
    y = np.arange(n, dtype=float)
    groups = (
        np.array([f"group:{i // 4}" for i in range(n)])
        if structure in ("group", "group_time")
        else None
    )
    times = (
        np.arange(n, dtype=float) * 172800
        if structure in ("time", "group_time")
        else None
    )
    spec = ValidationSpec(
        structure=structure, folds=2, horizon_seconds=86400 if times is not None else 0
    )
    method = {
        "independent": "random",
        "group": "group",
        "time": "time",
        "group_time": "group_time",
    }[structure]
    plan, outer = split_plan(
        ids, y, groups, times, spec, method, False, "dv:test", {"sha256": "test"}
    )
    pools, inner = partitions(
        ids, y, groups, times, spec, method, False, outer, "dv:test", {"sha256": "test"}
    )
    names = (
        "fit",
        "probability_calibration",
        "conformal_calibration",
        "validation",
        "test",
    )
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            assert not set(pools[a]) & set(pools[b])
            if groups is not None:
                assert not set(groups[pools[a]]) & set(groups[pools[b]])
            if times is not None:
                assert max(times[pools[a]]) + spec.horizon_seconds < min(
                    times[pools[b]]
                )
    assert [ids[i] for i in sorted(pools["test"], key=lambda i: ids[i])] == plan[
        "membership"
    ]["test"]
    assert inner["method"] == method


def test_development_ignores_final_targets_and_features(tmp_path):
    store, r, work, protocol = request(
        tmp_path, "regression", "ridge", "none", "interval"
    )
    with closing(store):
        dev = calculate(r, protocol.data(), work)
        ids = dev["uncertainty"]["membership"]["test"]
        frame = pl.read_parquet(r["path"])
        poisoned = frame.with_columns(
            pl.when(pl.col("__vu_row_id").is_in(ids))
            .then(1e9)
            .otherwise(pl.col("y"))
            .alias("y"),
            pl.when(pl.col("__vu_row_id").is_in(ids))
            .then(-1e9)
            .otherwise(pl.col("x"))
            .alias("x"),
        )
        dest = work / "poison.parquet"
        poisoned.write_parquet(dest)
        from veri_ufku.storage.project_store import file_hash

        changed = dict(r, path=str(dest), fingerprint=file_hash(dest))
        # Source binding differs, but no proper-train/calibration/validation statistic changes.
        new = calculate(changed, protocol.data(), work)
        assert new["evaluations"] == dev["evaluations"]
        assert new["uncertainty"]["conformal_q"] == dev["uncertainty"]["conformal_q"]


def test_multiclass_order_calibration_normalization_and_no_binary_threshold(tmp_path):
    from test_validation import setup_run

    store, r, work, protocol = setup_run(tmp_path, classification=True)
    with closing(store):
        r["classification"] = dict(
            candidates=["baseline", "logistic"],
            uncertainty=UncertaintySpec(threshold="default").data(),
        )
        result = calculate(r, protocol.data(), work)
        model, card = load_package(result["model_package"]["path"])
        frame = pl.read_parquet(r["path"])
        p = model.predict_proba(frame)
        np.testing.assert_allclose(p.sum(axis=1), 1)
        assert card["label_order"] == sorted(
            str(v) for v in frame["y"].unique().to_list()
        )
        assert result["decision"]["threshold"] is None
        assert (
            result["evaluations"][0]["uncertainty_report"]["probability"]["brier_scale"]
            == "multiclass sum [0,2]"
        )
        spec = UncertaintySpec(positive_class=card["label_order"][0], threshold="cost")
        with pytest.raises(ProjectError, match="Çok sınıflı"):
            threshold_choice(
                np.array(card["label_order"]),
                np.eye(len(card["label_order"])),
                card["label_order"],
                spec,
            )


def test_cancellation_before_fit_preserves_source(tmp_path):
    import threading

    from veri_ufku.importers.delimited import Control
    from veri_ufku.jobs.workers import Canceled

    store, r, work, protocol = request(
        tmp_path, "regression", "ridge", "none", "interval"
    )
    with closing(store):
        original = Path(r["path"]).read_bytes()
        event = threading.Event()
        event.set()
        with pytest.raises(Canceled):
            calculate(r, protocol.data(), work, Control(event))
        assert Path(r["path"]).read_bytes() == original


def test_bounded_large_artifact_publication_and_reopen(tmp_path, monkeypatch):
    import test_validation as helpers

    from veri_ufku.modeling.regression import settings
    from veri_ufku.storage.project_store import ProjectStore
    from veri_ufku.storage.validation_store import load_run

    fixture = helpers.fixture
    monkeypatch.setattr(helpers, "fixture", lambda: fixture(1000))
    store, r, work, protocol = helpers.setup_run(tmp_path)
    r["regression"] = settings(
        dict(
            candidates=["baseline", "ridge"],
            uncertainty=UncertaintySpec(
                model="ridge",
                calibration="none",
                prediction="interval",
                threshold="default",
            ).data(),
        )
    )
    with closing(store):
        r["run_id"] = "run:large50"
        store.state = choice(
            store,
            store.state,
            r["version_id"],
            protocol.data(),
            r["preparation"]["plan"]["version_id"],
            r["run_id"],
            regression=r["regression"],
        )
        r["history_state"] = store.state
        out = calculate(r, protocol.data(), work)
        store.state = complete(store, store.state, out, run_id=r["run_id"])
        record = next(x for x in store.state["results"] if "baseline" in x)
        assert record["baseline"]["details_uri"]
        loaded = load_run(store, record)
        assert loaded["evaluations"] == out["evaluations"]
        root = store.root
    with closing(ProjectStore.open(root)) as reopened:
        saved = next(x for x in reopened.state["results"] if "baseline" in x)
        assert load_run(reopened, saved)["uncertainty"] == out["uncertainty"]


def test_infeasible_threshold_and_missing_final_class_control():
    spec = UncertaintySpec(positive_class="yes", min_precision=1, min_recall=1)
    with pytest.raises(ProjectError, match="karşılanamıyor"):
        threshold_choice(
            np.array(["no", "yes"]), np.full((2, 2), 0.5), ["no", "yes"], spec
        )
    # Absent known final class is valid for proper probability scores, distinct from unseen.
    assert probability_report(["yes"], [[0.2, 0.8]], ["no", "yes"], 4)["n"] == 1


@pytest.mark.parametrize(
    "purpose,model,calibration",
    [("classification", "logistic", "sigmoid"), ("regression", "ridge", "none")],
)
def test_probability_only_or_point_only_does_not_invent_coverage_or_interval(
    tmp_path, purpose, model, calibration
):
    store, r, work, protocol = request(tmp_path, purpose, model, calibration, "none")
    with closing(store):
        result = calculate(r, protocol.data(), work)
        model, card = load_package(result["model_package"]["path"])
        frame = pl.read_parquet(r["path"])
        out, report = predict(model, card, frame, r["columns"])
        assert (
            "vu_prediction_set" not in out.columns
            and "vu_predictive_lower" not in out.columns
        )
        assert (
            result["evaluations"][0]["uncertainty_report"]["empirical_coverage"] is None
        )
        assert (
            result["evaluations"][0]["uncertainty_report"]["nominal_coverage"] is None
        )
        assert result["uncertainty"]["conformal_calibration_used_n"] == 0
        if purpose == "regression":
            with pytest.raises(ProjectError, match="desteklemiyor"):
                model.named_steps["baseline"].intervals(
                    model.named_steps["prepare"].transform(frame)
                )
