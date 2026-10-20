"""Actual support combinations; rejected boundaries never advertised as computed."""

import json
from contextlib import closing
from dataclasses import replace

import numpy as np
import polars as pl
import pytest
from scipy import sparse
from sklearn.preprocessing import StandardScaler
from test_model_families import CASES, fixture

from veri_ufku.modeling.baseline import calculate
from veri_ufku.modeling.families import (
    FamilyClassifier,
    FamilyPreparation,
    FamilyRegressor,
)
from veri_ufku.modeling.family_contracts import (
    OPTIONAL_FAMILIES,
    FamilyOptions,
    RankingSpec,
    support,
    validate_family,
)
from veri_ufku.modeling.lifecycle import load_package, preview
from veri_ufku.modeling.optional_families import ranking_schema
from veri_ufku.storage.project_model import ProjectError

SPARSE_CASES = [
    (m, p)
    for m, p in CASES
    if support(m, p)["sparse"] and m not in ("bagging", "voting", "stacking")
]
WEIGHT_CASES = [(m, p) for m, p in CASES if support(m, p)["weights"] != "unsupported"]


@pytest.mark.parametrize("method,purpose", SPARSE_CASES)
def test_actual_csr_no_densification_train_transform_predict(tmp_path, method, purpose):
    store, r, work, protocol = fixture(
        tmp_path, purpose, method, FamilyOptions(matrix="sparse")
    )
    with closing(store):
        out = calculate(r, protocol.data(), work)
        model, card = load_package(out["model_package"]["path"])
        learner = model.named_steps["baseline"]
        values = learner.preparation_.transform(pl.read_parquet(r["path"]))
        assert sparse.isspmatrix_csr(values)
        assert learner.metadata_["matrix"] == "sparse"
        assert model.predict(pl.read_parquet(r["path"])).shape == (90,)
        for value in learner.preparation_.summary_.values():
            if value["kind"] == "numeric":
                assert not value["center"]


@pytest.mark.parametrize("method,purpose", WEIGHT_CASES)
def test_training_weights_supported_and_baseline_same_loss_weights(
    tmp_path, method, purpose
):
    store, r, work, protocol = fixture(tmp_path, purpose, method)
    with closing(store):
        ident = next(c["id"] for c in r["columns"] if c["name"] == "weight")
        r[purpose]["family_options"]["weight_column"] = ident
        if purpose == "classification":
            r[purpose]["family_options"]["class_balance"] = "balanced"
        out = calculate(r, protocol.data(), work)
        assert "fit only" in out["evaluations"][0]["fitted_parameters"]["weights"]
        if purpose == "regression":
            ids = out["plan"]["membership"]["train"]
            frame = pl.read_parquet(r["path"]).filter(pl.col("__vu_row_id").is_in(ids))
            assert out["comparison"][0]["evaluations"][0][
                "baseline_center"
            ] == pytest.approx(np.average(frame["y"], weights=frame["weight"]))


@pytest.mark.parametrize("method,purpose", CASES)
def test_each_adapter_rejects_multioutput_and_gpu_without_success(
    tmp_path, method, purpose
):
    store, r, work, protocol = fixture(tmp_path, purpose, method)
    with closing(store):
        spec = r["preparation"]["spec"]
        from veri_ufku.modeling.contracts import PreparationSpec

        child = (FamilyClassifier if purpose == "classification" else FamilyRegressor)(
            method,
            FamilyOptions().data(),
            PreparationSpec.from_dict(spec),
            r["columns"],
            r["preparation"]["plan"],
        )
        with pytest.raises(ProjectError, match="multioutput"):
            child.fit(pl.read_parquet(r["path"]), np.zeros((90, 2)))
        with pytest.raises(ProjectError, match="device"):
            FamilyOptions.from_dict(dict(device="gpu"))


def test_native_categorical_nan_and_unknown_preserved_roundtrip(tmp_path):
    store, r, work, protocol = fixture(tmp_path, "regression", "hist_gradient")
    with closing(store):
        out = calculate(r, protocol.data(), work)
        model, card = load_package(out["model_package"]["path"])
        learner = model.named_steps["baseline"]
        raw = pl.read_parquet(r["path"])
        future = raw.head(3).with_columns(
            pl.Series("category", ["new", None, "A"]),
            pl.Series("x", [None, 1.0, 2.0], dtype=pl.Float64),
        )
        prepared = learner.preparation_.transform(future)
        assert (
            prepared.shape == (3, 2)
            and np.isnan(prepared[0, 0])
            and np.isnan(prepared[0, 1])
            and np.isnan(prepared[1, 1])
        )
        assert learner.preparation_.categorical_mask_ == [False, True]
        assert np.isfinite(model.predict(future)).all()
        checked = preview(model, card, future, r["columns"])
        assert (
            checked["invalid_rows"] == 0
            and checked["features"][1]["unknown_categories"] == 1
        )
        assert (
            learner.preparation_.summary_[r["preparation"]["spec"]["features"][1]][
                "kind"
            ]
            == "native_categorical"
        )


def test_stacking_inner_preprocessing_isolation_and_oof_values_reference(
    tmp_path, monkeypatch
):
    store, r, work, protocol = fixture(tmp_path, "regression", "stacking")
    original = FamilyPreparation.fit
    calls = []

    def spy(self, X, y=None):
        calls.append(set(X["__vu_row_id"]))
        return original(self, X, y)

    monkeypatch.setattr(FamilyPreparation, "fit", spy)
    with closing(store):
        out = calculate(r, protocol.data(), work)
        model, card = load_package(out["model_package"]["path"])
        learner = model.named_steps["baseline"]
        training = set(card["fit_row_ids"])
        test = set(out["plan"]["membership"]["test"])
        assert all(not c & test for c in calls)
        for fold in learner.oof_:
            a = set(fold["fit_row_ids"])
            b = set(fold["prediction_row_ids"])
            assert not a & b and a | b == training and a in calls
        assert learner.meta_training_values_.shape == (len(training), 2)
        assert set(learner.meta_training_row_ids_) == training
        # Refit a child on exactly the first inner training membership; scaler reference uses only that fold.
        raw = pl.read_parquet(r["path"])
        first = learner.oof_[0]
        train = raw.filter(pl.col("__vu_row_id").is_in(first["fit_row_ids"]))
        child = learner._child("elasticnet", 43).fit(train, train["y"].to_numpy())
        numeric = child.preparation_.summary_[r["preparation"]["spec"]["features"][0]]
        assert numeric["mean"] == pytest.approx(
            StandardScaler().fit(train["x"].to_numpy().reshape(-1, 1)).mean_.tolist()
        )
        source = raw.filter(pl.col("__vu_row_id").is_in(first["prediction_row_ids"]))
        rows = list(learner.meta_training_row_ids_)
        expected = child.predict(source)
        actual = learner.meta_training_values_[
            [rows.index(v) for v in source["__vu_row_id"]], 0
        ]
        assert actual == pytest.approx(expected)


@pytest.mark.parametrize("method", OPTIONAL_FAMILIES)
def test_optional_absence_not_computed_and_ranking_not_classification(tmp_path, method):
    from veri_ufku.modeling.family_contracts import available

    assert not available(method)[0]
    store, r, work, protocol = fixture(tmp_path, "classification", method)
    with closing(store), pytest.raises(ProjectError, match="backend ortamı yok"):
        calculate(r, protocol.data(), work)
    with pytest.raises(ProjectError, match="ranking"):
        FamilyOptions.from_dict(dict(objective="ranking"))


def test_weight_boundaries_negative_missing_unsupported_and_ranking_groups(tmp_path):
    store, r, work, protocol = fixture(tmp_path, "classification", "knn")
    with closing(store):
        opts = replace(FamilyOptions(), class_balance="balanced")
        with pytest.raises(ProjectError, match="weight/imbalance"):
            validate_family(
                "knn", "classification", opts, r["preparation"]["spec"], protocol
            )
        with pytest.raises(ProjectError, match="weight_kind"):
            FamilyOptions.from_dict(dict(weight_kind="survey"))
        columns = [
            dict(id="x", name="x"),
            dict(id="y", name="y"),
            dict(id="q", name="q"),
        ]
        spec = RankingSpec(("x",), "y", "q")
        frame = pl.DataFrame(
            dict(
                __vu_row_id=["r1", "r2", "r3", "r4"],
                x=[1, 2, 3, 4],
                y=[0, 1, 2, 0],
                q=["a", "a", "b", "b"],
            )
        )
        assert (
            ranking_schema(spec, frame, columns, ["a"], ["b"])["schema"]
            == "RankingSpec/v1"
        )
        with pytest.raises(ProjectError, match="ayrık"):
            ranking_schema(spec, frame, columns, ["a"], ["a"])


@pytest.mark.parametrize("weights", [[-1.0] * 90, [None] * 90, [0.0] * 90])
def test_negative_missing_zero_loss_weights_rejected_without_source_write(
    tmp_path, weights
):
    store, r, work, protocol = fixture(
        tmp_path, "regression", "decision_tree", weights=weights
    )
    with closing(store):
        before = pl.read_parquet(r["path"])
        ident = next(c["id"] for c in r["columns"] if c["name"] == "weight")
        r["regression"]["family_options"]["weight_column"] = ident
        with pytest.raises(ProjectError, match="weights|Weight"):
            calculate(r, protocol.data(), work)
        assert pl.read_parquet(r["path"]).equals(before)


def test_group_stacking_whole_groups_and_time_rejection(tmp_path):
    store, r, work, protocol = fixture(tmp_path, "regression", "stacking")
    with closing(store):
        from veri_ufku.modeling.contracts import PreparationSpec

        raw = pl.read_parquet(r["path"]).with_columns(
            pl.Series("unit_group", [str(i // 6) for i in range(90)])
        )
        columns = r["columns"] + [
            dict(id="group-column", name="unit_group", type="String")
        ]
        source = PreparationSpec.from_dict(r["preparation"]["spec"])
        learner = FamilyRegressor(
            "stacking",
            FamilyOptions().data(),
            source,
            columns,
            r["preparation"]["plan"],
            42,
            4000000,
            "unit_group",
            "group",
        ).fit(raw, raw["y"].to_numpy())
        groups = dict(zip(raw["__vu_row_id"], raw["unit_group"]))
        for fold in learner.oof_:
            assert not {groups[x] for x in fold["fit_row_ids"]} & {
                groups[x] for x in fold["prediction_row_ids"]
            }
        with pytest.raises(ProjectError, match="random fallback"):
            validate_family(
                "stacking",
                "regression",
                FamilyOptions(),
                source.data(),
                replace(protocol, structure="time"),
            )


def test_unknown_ordinal_explicit_order_and_no_implicit_recoding(tmp_path):
    from veri_ufku.modeling.contracts import PreparationSpec

    store, r, work, protocol = fixture(tmp_path, "regression", "decision_tree")
    with closing(store):
        source = PreparationSpec.from_dict(r["preparation"]["spec"])
        plan = json.loads(json.dumps(r["preparation"]["plan"]))
        category = source.features[1]
        step = next(s for s in plan["steps"] if s["kind"] == "encode_onehot")
        step.update(
            kind="encode_ordinal", parameters=dict(order=["B", "A"], unknown="error")
        )
        raw = pl.read_parquet(r["path"])
        preparation = FamilyPreparation(
            "decision_tree", FamilyOptions().data(), source, r["columns"], plan
        ).fit(raw)
        values = preparation.transform(raw)
        assert values.shape == (90, 2)
        assert values[:, 1].tolist() == [
            1.0 if v == "A" else 0.0 for v in raw["category"]
        ]
        assert preparation.summary_[category]["kind"] == "ordinal"
        with pytest.raises(ValueError):
            preparation.transform(
                raw.head(1).with_columns(pl.lit("unknown").alias("category"))
            )


def test_safe_parameter_tamper_and_svm_proba_boundary(tmp_path):
    from veri_ufku.modeling.lifecycle import validate_pipeline

    store, r, work, protocol = fixture(tmp_path, "classification", "svm")
    with closing(store):
        out = calculate(r, protocol.data(), work)
        model, card = load_package(out["model_package"]["path"])
        assert not card["probability_supported"] and not hasattr(model, "predict_proba")
        model.named_steps["baseline"].estimator_.C = 99999.0
        with pytest.raises(ProjectError, match="parametre"):
            validate_pipeline(model, card)


@pytest.mark.parametrize("method", ["voting", "stacking"])
def test_closed_ensemble_package_rejects_member_and_oof_tamper(tmp_path, method):
    from veri_ufku.modeling.lifecycle import validate_pipeline

    store, r, work, protocol = fixture(tmp_path, "regression", method)
    with closing(store):
        out = calculate(r, protocol.data(), work)
        model, card = load_package(out["model_package"]["path"])
        learner = model.named_steps["baseline"]
        if method == "voting":
            learner.children_.pop()
            match = "üyelik"
        else:
            learner.oof_[0]["prediction_row_ids"] = learner.oof_[0]["fit_row_ids"]
            match = "OOF|FamilyScope"
        with pytest.raises(ProjectError, match=match):
            validate_pipeline(model, card)


@pytest.mark.parametrize(
    "method,purpose", [("decision_tree", "regression"), ("stacking", "classification")]
)
def test_explicit_family_final_test_keeps_same_model_and_outer_split(
    tmp_path, method, purpose
):
    store, r, work, protocol = fixture(tmp_path, purpose, method)
    with closing(store):
        developed = calculate(r, protocol.data(), work)
        final = calculate(
            dict(
                r,
                mode="final",
                selected_model=developed["selected_model"],
                decision=developed.get("decision"),
                expected_split_id=developed["plan"]["split_id"],
                expected_protocol_id=developed["plan"]["protocol_id"],
            ),
            protocol.data(),
            work,
        )
        assert final["mode"] == "final" and not final["comparison"]
        assert final["selected_model"] == method
        assert final["plan"]["membership"] == developed["plan"]["membership"]
        assert not set(final["evaluations"][0]["fit_row_ids"]) & set(
            final["plan"]["membership"]["test"]
        )


@pytest.mark.parametrize("method,purpose", CASES)
def test_each_family_declared_missing_train_only_and_future_transform(
    tmp_path, method, purpose
):
    from veri_ufku.modeling.contracts import PreparationSpec

    store, r, work, protocol = fixture(tmp_path, purpose, method)
    with closing(store):
        spec = replace(
            PreparationSpec.from_dict(r["preparation"]["spec"]),
            numeric_imputation="median",
            categorical_imputation="mode",
        )
        raw = pl.read_parquet(r["path"])
        training = raw.head(70).with_columns(
            pl.when(pl.int_range(pl.len()) % 11 == 0)
            .then(None)
            .otherwise(pl.col("x"))
            .alias("x"),
            pl.when(pl.int_range(pl.len()) % 13 == 0)
            .then(None)
            .otherwise(pl.col("category"))
            .alias("category"),
        )
        learner = (
            FamilyClassifier if purpose == "classification" else FamilyRegressor
        )(
            method,
            FamilyOptions().data(),
            spec,
            r["columns"],
            r["preparation"]["plan"],
        ).fit(training, training["y"].to_numpy())
        future = raw.tail(3).with_columns(
            pl.Series("x", [None, 1.0, 2.0], dtype=pl.Float64),
            pl.Series("category", [None, "new", "A"]),
        )
        assert learner.predict(future).shape == (3,)
        assert set(learner.fit_row_ids_) == set(training["__vu_row_id"])
        children = learner.children_ or [learner]
        for child in children:
            assert not set(child.fit_row_ids_) & set(future["__vu_row_id"])
            for state in child.preparation_.summary_.values():
                assert state["fit_n"] == 70
        assert pl.read_parquet(r["path"]).equals(raw)


def test_convergence_failure_is_visible_without_model_artifact(tmp_path):
    store, r, work, protocol = fixture(
        tmp_path, "classification", "elasticnet", FamilyOptions(max_iter=100, C=1000)
    )
    with closing(store):
        with pytest.raises(ProjectError, match="convergence"):
            calculate(r, protocol.data(), work)
        assert not list(work.glob("*.vumodel"))


@pytest.mark.parametrize("method", ["svm", "knn"])
def test_quadratic_budget_rejected_before_any_family_fit(tmp_path, monkeypatch, method):
    from veri_ufku.domain.contracts import ComputeBudget
    from veri_ufku.importers.delimited import Control

    store, r, work, protocol = fixture(tmp_path, "regression", method)

    def unexpected(*args, **kwargs):
        raise AssertionError("Budget violation reached estimator fit")

    monkeypatch.setattr(FamilyRegressor, "fit", unexpected)
    # Isolate the estimator admission check from this pytest process's existing RSS.
    monkeypatch.setattr("veri_ufku.jobs.resources.rss_bytes", lambda pid: 0)
    with closing(store), pytest.raises(ProjectError, match="ComputeBudget"):
        calculate(
            r,
            protocol.data(),
            work,
            Control(budget=ComputeBudget(ram_bytes=128 * 1024)),
        )
