"""Per-family real evaluation/prediction, support gates, source identity and OOF leakage."""

from contextlib import closing

import numpy as np
import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.modeling.baseline import calculate
from veri_ufku.modeling.contracts import PreparationSpec
from veri_ufku.modeling.family_contracts import (
    FAMILY_METHODS,
    OPTIONAL_FAMILIES,
    REGRESSION_FAMILIES,
    FamilyOptions,
)
from veri_ufku.modeling.lifecycle import load_package
from veri_ufku.modeling.preparation import calculate as preparation
from veri_ufku.modeling.validation import ValidationSpec

METHODS = tuple(m for m in FAMILY_METHODS if m not in OPTIONAL_FAMILIES)
CASES = [
    (m, "regression") for m in REGRESSION_FAMILIES if m not in OPTIONAL_FAMILIES
] + [(m, "classification") for m in METHODS]


def fixture(
    tmp_path, purpose="regression", method="decision_tree", options=None, weights=None
):
    rng = np.random.default_rng(48)
    x = rng.uniform(0.1, 2.0, 90)
    y = (
        3 * x + rng.normal(0, 0.05, 90)
        if purpose == "regression"
        else np.where(x > 1.0, "risk", "normal")
    )
    frame = pl.DataFrame(
        dict(
            x=x,
            y=y,
            category=["A" if i % 2 else "B" for i in range(90)],
            weight=(x + 0.2) if weights is None else weights,
        )
    )
    store, r, work = prepare(tmp_path, frame)
    spec = PreparationSpec(
        purpose,
        (column(r, "x"), column(r, "category")),
        target=column(r, "y"),
        source_version=r["version_id"],
        family="tree",
        prediction_context="Before outcome",
    )
    r = dict(r, history_state=store.state, origin_version=r["version_id"])
    prep = preparation(r, spec, work)
    assert not prep["blockers"]
    protocol = ValidationSpec(
        folds=2,
        prediction_moment="Before outcome",
        availability={
            c: dict(offset_seconds=0, note="available") for c in spec.features
        },
    )
    config = dict(
        candidates=["baseline", method],
        family_options=(options or FamilyOptions()).data(),
        explicit_model=method,
    )
    if purpose == "classification":
        config["positive_class"] = "risk"
    return store, dict(r, preparation=prep, **{purpose: config}), work, protocol


@pytest.mark.parametrize("method,purpose", CASES)
def test_every_supported_family_actual_evaluate_safe_model_predict(
    tmp_path, method, purpose
):
    store, r, work, protocol = fixture(tmp_path, purpose, method)
    with closing(store):
        original = pl.read_parquet(r["path"])
        out = calculate(r, protocol.data(), work)
        assert out["selected_model"] == method
        assert "explicit" in out["selection_rule"]
        assert [c["model"] for c in out["comparison"]] == ["baseline", method]
        assert all(
            set(c["evaluations"][0]["fit_row_ids"])
            == set(out["plan"]["membership"]["train"])
            for c in out["comparison"]
        )
        learner = out["evaluations"][0]["fitted_parameters"]
        assert learner["method"] == method
        test_rows = set(out["plan"]["membership"]["test"])
        for evaluation in out["evaluations"]:
            assert not test_rows & set(evaluation["fit_row_ids"])
        if method == "stacking":
            for fold in learner["oof"]:
                assert not set(fold["fit_row_ids"]) & set(fold["prediction_row_ids"])
                assert set(fold["fit_row_ids"] + fold["prediction_row_ids"]) <= set(
                    out["plan"]["membership"]["train"]
                )
        model, card = load_package(out["model_package"]["path"])
        predicted = model.predict(original)
        assert predicted.shape == (90,)
        if purpose == "classification":
            assert set(predicted) <= set(card["label_order"])
            assert card["probability_supported"] == (method != "svm")
        assert pl.read_parquet(r["path"]).equals(original)
