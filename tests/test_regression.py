"""Independent regression references and adversarial training-boundary checks."""

import copy
from contextlib import closing
from dataclasses import replace

import numpy as np
import polars as pl
import pytest
from test_dataset import column, prepare
from test_preparation import request, specification

from veri_ufku.modeling.baseline import FoldPreparation, calculate, regression_scores
from veri_ufku.modeling.preparation import calculate as preparation
from veri_ufku.modeling.regression import settings
from veri_ufku.modeling.validation import ValidationSpec
from veri_ufku.storage.project_model import ProjectError, validate_state
from veri_ufku.storage.validation_store import (
    choice,
    complete,
    load_run,
    prior_uses,
    reserve_test,
)


def synthetic(tmp_path, target=None, n=120):
    x = np.linspace(-10, 10, n)
    frame = pl.DataFrame(dict(x=x, y=3 * x + 7 if target is None else target))
    store, _, work = prepare(tmp_path, frame)
    r = request(store)
    p = replace(
        specification(r, family="linear", scaling="standard"),
        features=(column(r, "x"),),
    )
    report = preparation(r, p, work)
    s = ValidationSpec(
        prediction_moment="Ölçüm öncesi",
        availability={p.features[0]: dict(offset_seconds=0, note="Önceden bilinir")},
    )
    return (
        store,
        dict(r, preparation=report, regression=settings(dict(unit="TL"))),
        work,
        s,
    )


def test_true_predictions_cv_baseline_reference_and_test_fit_spy(tmp_path, monkeypatch):
    store, r, work, s = synthetic(tmp_path)
    with closing(store):
        first = calculate(r, s.data(), work)
        test_ids = set(first["plan"]["membership"]["test"])
        original = FoldPreparation.fit
        calls = []

        def spy(self, X, y=None):
            assert not test_ids & set(X["__vu_row_id"])
            assert self.spec.target not in self.spec.features
            calls.append(set(X["__vu_row_id"]))
            return original(self, X, y)

        monkeypatch.setattr(FoldPreparation, "fit", spy)
        out = calculate(r, s.data(), work)
        assert out["plan"] == first["plan"]
        candidates = {c["model"]: c for c in out["comparison"]}
        assert len(calls) == 16
        assert candidates["linear"]["cv_mae"] < 1e-10
        assert candidates["baseline"]["cv_mae"] > 10
        assert candidates["forest"]["cv_mae"] < candidates["baseline"]["cv_mae"] / 10
        assert candidates["ridge"]["cv_mae"] < 1
        assert out["selected_model"] == "linear"
        for point in out["evaluations"][0]["predictions"]:
            assert point["predicted"] == pytest.approx(point["actual"], abs=1e-10)
            assert point["residual"] == pytest.approx(0, abs=1e-10)
        frame = pl.read_parquet(r["path"])
        members = out["plan"]["membership"]
        train = frame.filter(pl.col("__vu_row_id").is_in(members["train"]))[
            "y"
        ].to_numpy()
        val = frame.filter(pl.col("__vu_row_id").is_in(members["validation"]))[
            "y"
        ].to_numpy()
        assert candidates["baseline"]["evaluations"][0]["metrics"][0][
            "value"
        ] == pytest.approx(np.mean(abs(val - train.mean())))
        final = calculate(
            dict(
                r,
                mode="final",
                selected_model=out["selected_model"],
                expected_split_id=out["plan"]["split_id"],
                expected_protocol_id=out["plan"]["protocol_id"],
            ),
            s.data(),
            work,
        )
        assert not final["comparison"] and len(final["evaluations"]) == 1
        assert calls[-1] == set(members["development"])
        assert final["evaluations"][0]["metrics"][0]["value"] < 1e-10


def test_final_ledger_retuning_artifact_reopen(tmp_path):
    store, r, work, s = synthetic(tmp_path, n=1200)
    root = store.root
    with closing(store):
        out = calculate(r, s.data(), work)
        state = choice(
            store,
            store.state,
            r["version_id"],
            s.data(),
            out["pipeline_id"],
            out["run_id"],
            r["regression"],
        )
        state = complete(store, state, out, run_id=out["run_id"])
        for i in range(2):
            state, ident = reserve_test(store, state, out, f"run:final{i}")
            final = calculate(
                dict(
                    r,
                    mode="final",
                    run_id=f"run:final{i}",
                    selected_model=out["selected_model"],
                    prior_test_use_ids=prior_uses(state)[:-1],
                    expected_split_id=out["plan"]["split_id"],
                    expected_protocol_id=out["plan"]["protocol_id"],
                ),
                s.data(),
                work,
            )
            state = complete(store, state, final, ident)
            assert final["interpretation"] == (
                "exploratory" if i else "project_test_not_previously_used"
            )
        retuned = dict(
            r,
            regression=settings(dict(unit="TL", alpha=10)),
            prior_test_use_ids=prior_uses(state),
        )
        new = calculate(retuned, s.data(), work)
        state = choice(
            store,
            state,
            r["version_id"],
            s.data(),
            new["pipeline_id"],
            new["run_id"],
            retuned["regression"],
        )
        state = complete(store, state, new, run_id=new["run_id"])
        assert new["interpretation"] == "exploratory"
        assert state["results"][-2]["model_choice"]["prior_test_use_ids"] == prior_uses(
            state
        )
        validate_state(state)
        assert any(x.get("baseline", {}).get("details_uri") for x in state["results"])
    with closing(type(store).open(root)) as opened:
        records = [x for x in opened.state["results"] if "baseline" in x]
        assert load_run(opened, records[0])["comparison"] == out["comparison"]
        assert len(prior_uses(opened.state)) == 2


def test_constant_negative_r2_and_missing_target(tmp_path):
    assert (
        regression_scores(np.array([1, 2, 3]), np.array([10, 10, 10]), "validation")[0][
            "value"
        ]
        < 0
    )
    metric = regression_scores(np.ones(3), np.zeros(3), "validation")[0]
    assert metric["value"] is None and metric["status"] == "undefined_constant_target"
    target = (3 * np.linspace(-10, 10, 120) + 7).tolist()
    target[0] = None
    store, r, work, s = synthetic(tmp_path, target)
    with closing(store):
        out = calculate(r, s.data(), work)
        assert len(out["excluded_target_row_ids"]) == 1
        assert all(e["metrics"][2]["status"] == "valid" for e in out["evaluations"])
        state = complete(store, store.state, out)
        validate_state(state)


@pytest.mark.parametrize(
    "change",
    [
        dict(alpha=0),
        dict(trees=10000),
        dict(depth=None),
        dict(candidates=["ridge"]),
        dict(unit=""),
    ],
)
def test_narrow_parameters_rejected(change):
    with pytest.raises(ProjectError):
        settings(change)


def test_target_leakage_and_wrong_type_errors(tmp_path):
    store, r, work, s = synthetic(tmp_path, ["category"] * 120)
    with closing(store):
        assert r["preparation"]["blockers"]
        with pytest.raises(ProjectError, match="Hazırlık engellerini"):
            calculate(r, s.data(), work)
        p = copy.deepcopy(r["preparation"]["spec"])
        p["features"].append(p["target"])
        with pytest.raises(ProjectError, match="Hedef"):
            preparation(r, p, work)


def test_group_time_regression_candidates_and_constant_fold(tmp_path):
    from test_validation import setup_run

    store, r, work, s = setup_run(tmp_path, "group_time")
    with closing(store):
        out = calculate(dict(r, regression=settings(dict(unit="kg"))), s.data(), work)
        assert len(out["comparison"]) == 4
        assert out["plan"]["method"] == "group_time"
        test = set(out["plan"]["membership"]["test"])
        for c in out["comparison"]:
            assert all(not test & set(e["fit_row_ids"]) for e in c["evaluations"])


def test_constant_validation_target_preserved_as_undefined(tmp_path):
    from sklearn.model_selection import train_test_split

    development, test = train_test_split(np.arange(120), test_size=0.2, random_state=42)
    train, val = train_test_split(development, test_size=0.2 / 0.8, random_state=42)
    y = np.arange(120, dtype=float)
    y[val] = 5
    store, r, work, s = synthetic(tmp_path, y)
    with closing(store):
        out = calculate(r, s.data(), work)
        assert (
            out["evaluations"][0]["metrics"][2]["status"] == "undefined_constant_target"
        )
        assert out["evaluations"][0]["metrics"][2]["value"] is None
        complete(store, store.state, out)


def test_forest_cost_limit_rejects_without_training(tmp_path, monkeypatch):
    store, r, work, s = synthetic(tmp_path, n=20001)
    with closing(store):

        def forbidden(*args, **kwargs):
            pytest.fail("Maliyet sınırını aşan kayıtlar fit'e gönderilemez")

        monkeypatch.setattr(FoldPreparation, "fit", forbidden)
        with pytest.raises(ProjectError, match="20.000"):
            calculate(r, s.data(), work)
