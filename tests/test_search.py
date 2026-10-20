"""Bounded search references, fixed nested membership and immutable trial resume."""

import copy
import threading
from contextlib import closing
from dataclasses import replace

import numpy as np
import polars as pl
import pytest
from test_model_families import fixture

from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.families import FamilyPreparation
from veri_ufku.modeling.search import calculate
from veri_ufku.modeling.search_contracts import SearchSpec
from veri_ufku.modeling.validation import ValidationSpec, development_folds
from veri_ufku.storage.project_model import ProjectError


def run_fixture(tmp_path, purpose="regression", method="grid", **kwargs):
    store, r, work, protocol = fixture(tmp_path, purpose)
    r.update(search_id="search:test49", prior_test_use_ids=[])
    return store, r, work, protocol, SearchSpec(method=method, curves=False, **kwargs)


@pytest.mark.parametrize("method", ["grid", "random"])
@pytest.mark.parametrize("purpose", ["regression", "classification"])
def test_bounded_search_completes_no_test_fit_and_winner_inner_only(
    tmp_path, monkeypatch, method, purpose
):
    store, r, work, p, s = run_fixture(tmp_path, purpose, method)
    fits = []
    original = FamilyPreparation.fit

    def spy(self, X, y=None):
        fits.append(set(X["__vu_row_id"]))
        return original(self, X, y)

    monkeypatch.setattr(FamilyPreparation, "fit", spy)
    with closing(store):
        before = pl.read_parquet(r["path"])
        out = calculate(r, p.data(), s.data(), work)
        assert out["status"] == "completed", out.get("reason")
        assert len(out["trials"]) == 6 and len(out["outer_evaluations"]) == 2
        final = set(out["plan"]["membership"]["test"])
        assert all(not a & final for a in fits)
        for scope in out["scope_plans"]:
            for trial in [t for t in out["trials"] if t["scope"] == scope["name"]]:
                assert trial["status"] == "completed"
                assert [
                    dict(train=f["fit_row_ids"], validation=f["evaluation_row_ids"])
                    for f in trial["folds"]
                ] == scope["inner_plan"]["folds"]
        for outer in out["outer_evaluations"]:
            t = next(t for t in out["trials"] if t["id"] == outer["winner_trial"])
            assert t["loss"] == min(
                t["loss"]
                for t in out["trials"]
                if t["scope"] == outer["scope"] and t["feasible"]
            )
        assert pl.read_parquet(r["path"]).equals(before)


def test_cancel_resume_preserves_completed_attempts_and_compatibility(tmp_path):
    store, r, work, p, s = run_fixture(tmp_path)
    with closing(store):
        original = calculate(r, p.data(), s.data(), work)
        snapshots = []
        cancel = threading.Event()

        def stop(value):
            snapshots.append(copy.deepcopy(value))
            if any(t["status"] == "completed" for t in value["trials"]):
                cancel.set()

        canceled = calculate(
            r, p.data(), s.data(), work, Control(cancel=cancel), checkpoint=stop
        )
        assert canceled["status"] == "canceled"
        saved = copy.deepcopy(canceled)
        completed = [t for t in saved["trials"] if t["status"] == "completed"]
        assert completed
        resumed = calculate(r, p.data(), s.data(), work, resume=saved)
        assert resumed["status"] == "completed"
        assert resumed["recommended"] == original["recommended"]
        assert all(t in resumed["trials"] for t in completed)
        assert canceled == saved
        with pytest.raises(ProjectError, match="Resume uyumsuz"):
            calculate(r, p.data(), replace(s, seed=50).data(), work, resume=saved)
        with pytest.raises(ProjectError, match="Resume uyumsuz"):
            calculate(r, replace(p, seed=7).data(), s.data(), work, resume=saved)


def test_pruning_and_failed_trials_not_success(tmp_path):
    store, r, work, p, s = run_fixture(
        tmp_path, prune_after_folds=1, prune_loss_above=-1
    )
    with closing(store):
        out = calculate(r, p.data(), s.data(), work)
        assert out["status"] == "failed" and out["recommended"] is None
        assert all(
            t["status"] == "pruned" and len(t["folds"]) == 1 for t in out["trials"]
        )


@pytest.mark.parametrize("structure", ["group", "time", "group_time"])
def test_inner_joint_protocol_no_group_or_future_leakage(structure):
    n = 240
    ids = [f"r{i}" for i in range(n)]
    y = np.arange(n, dtype=float)
    groups = np.asarray([str(i // 4) for i in range(n)], dtype=object)
    times = np.arange(n, dtype=float) * 10
    spec = ValidationSpec(structure=structure, folds=3, horizon_seconds=2)
    plan, folds = development_folds(ids, y, groups, times, spec, structure, False)
    assert len(folds) == 3
    for a, b in folds:
        if structure != "time":
            assert not set(groups[a]) & set(groups[b])
        if structure != "group":
            assert max(times[a] + 2) < min(times[b])
    assert plan["method"] == structure
    if structure == "group_time":
        with pytest.raises(ProjectError, match="yetersiz"):
            development_folds(ids, y, groups, np.zeros(n), spec, structure, False)


def test_conditional_space_and_optional_absence():
    s = SearchSpec(
        space={
            "methods": ["decision_tree", "svm"],
            "parameters": [
                {"name": "C", "values": [1, 2], "when": {"method": ["svm"]}},
                {
                    "name": "depth",
                    "values": [2, 4],
                    "when": {"method": ["decision_tree"]},
                },
            ],
        }
    )
    assert len(s.candidates("regression")) == 4
    with pytest.raises(ProjectError, match="when"):
        SearchSpec(
            space={
                "methods": ["decision_tree"],
                "parameters": [{"name": "C", "values": [1]}],
            }
        ).candidates("regression")
    with pytest.raises(ProjectError, match="Optuna"):
        SearchSpec(method="bayesian").validate()
    with pytest.raises(ProjectError, match="concurrency"):
        SearchSpec(concurrency=2).validate()


@pytest.mark.parametrize("structure", ["group", "time", "group_time"])
def test_actual_joint_nested_search_prune_cancel_resume_same_plan(tmp_path, structure):
    from test_validation import setup_run

    store, r, work, p = setup_run(tmp_path, structure, folds=2)
    r.update(search_id="search:joint49", prior_test_use_ids=[])
    search = SearchSpec(
        curves=True,
        trials=1,
        space={
            "methods": ["decision_tree"],
            "parameters": [{"name": "depth", "values": [2]}],
        },
    )
    with closing(store):
        cancel = threading.Event()

        def checkpoint(value):
            if any(t["status"] == "completed" for t in value["trials"]):
                cancel.set()

        stopped = calculate(
            r,
            p.data(),
            search.data(),
            work,
            Control(cancel=cancel),
            checkpoint=checkpoint,
        )
        assert stopped["status"] == "canceled"
        out = calculate(r, p.data(), search.data(), work, resume=stopped)
        assert out["status"] == "completed", out.get("reason")
        assert (
            out["plan"] == stopped["plan"]
            and out["scope_plans"] == stopped["scope_plans"]
        )
        frame = pl.read_parquet(r["path"])
        rows = {v: i for i, v in enumerate(frame["__vu_row_id"])}
        for trial in out["trials"]:
            for f in trial["folds"]:
                a = [rows[x] for x in f["fit_row_ids"]]
                b = [rows[x] for x in f["evaluation_row_ids"]]
                if structure != "time":
                    assert not set(frame["group"][a]) & set(frame["group"][b])
                if structure != "group":
                    assert max(frame["when"][a]) < min(frame["when"][b])
        pruned = calculate(
            dict(r, search_id="search:pruned49"),
            p.data(),
            replace(
                search, curves=False, prune_after_folds=1, prune_loss_above=-1
            ).data(),
            work,
        )
        assert pruned["status"] == "failed" and all(
            t["status"] == "pruned" for t in pruned["trials"]
        )
        assert pruned["plan"] == out["plan"]


def test_external_early_stopping_validation_is_disjoint_from_scoring_outer_test(
    tmp_path,
):
    store, r, work, p, _ = run_fixture(tmp_path)
    search = SearchSpec(
        trials=1,
        curves=False,
        early_stopping=True,
        space={
            "methods": ["gradient_boosting"],
            "parameters": [{"name": "trees", "values": [20]}],
        },
    )
    with closing(store):
        out = calculate(r, p.data(), search.data(), work)
        assert out["status"] == "completed", out.get("reason")
        final = set(out["plan"]["membership"]["test"])
        for trial in out["trials"]:
            for fold in trial["folds"]:
                fit = set(fold["fit_row_ids"])
                evaluation = set(fold["evaluation_row_ids"])
                assert fold["selected_trees"] in (10, 20)
                for stage in fold["early_stopping"]:
                    stop = set(stage["validation_row_ids"])
                    assert not stop & fit and not stop & evaluation and not stop & final


def test_failed_trial_can_be_followed_by_success_and_secondary_constraints(tmp_path):
    from veri_ufku.modeling.family_contracts import FamilyOptions

    store, r, work, p, _ = run_fixture(tmp_path)
    search = SearchSpec(
        curves=False,
        trials=2,
        options=replace(FamilyOptions(), neighbors=30).data(),
        space={"methods": ["knn", "decision_tree"], "parameters": []},
    )
    with closing(store):
        out = calculate(r, p.data(), search.data(), work)
        assert out["status"] == "completed"
        assert any(t["status"] == "failed" for t in out["trials"])
        assert out["recommended"]["method"] == "decision_tree"
        constrained = calculate(
            r, p.data(), replace(search, constraints={"max_rmse": 0}).data(), work
        )
        assert constrained["status"] == "failed" and constrained["recommended"] is None
        assert any(
            t["status"] == "completed" and not t["feasible"]
            for t in constrained["trials"]
        )


def test_search_curves_control_one_parameter_and_no_final_fit(tmp_path, monkeypatch):
    store, r, work, p, _ = run_fixture(tmp_path)
    search = SearchSpec(method="grid", curves=True)
    with closing(store):
        out = calculate(r, p.data(), search.data(), work)
        assert out["status"] == "completed"
        assert len(out["curves"]) == 4
        final = set(out["plan"]["membership"]["test"])
        selected = out["recommended"]
        for curve in out["curves"]:
            if curve["kind"] == "validation":
                assert {
                    k: v
                    for k, v in curve["fixed_parameters"]["options"].items()
                    if k != "depth"
                } == {k: v for k, v in selected["options"].items() if k != "depth"}
            for f in curve["folds"]:
                assert (
                    not set(f["fit_row_ids"]) & final
                    and not set(f["evaluation_row_ids"]) & final
                )


def test_environment_and_space_resume_mismatch_and_prior_history_preserved(
    tmp_path, monkeypatch
):
    import veri_ufku.modeling.search as engine

    store, r, work, p, s = run_fixture(tmp_path)
    with closing(store):
        cancel = threading.Event()

        def checkpoint(value):
            if value["trials"]:
                cancel.set()

        partial = calculate(
            r, p.data(), s.data(), work, Control(cancel=cancel), checkpoint=checkpoint
        )
        env = engine.environment()
        monkeypatch.setattr(
            engine, "environment", lambda: dict(env, engine_sha256="changed")
        )
        with pytest.raises(ProjectError, match="Resume uyumsuz"):
            calculate(r, p.data(), s.data(), work, resume=partial)
        monkeypatch.undo()
        with pytest.raises(ProjectError, match="Resume uyumsuz"):
            calculate(
                r,
                p.data(),
                replace(
                    s,
                    space={
                        "methods": ["decision_tree"],
                        "parameters": [{"name": "depth", "values": [3, 4]}],
                    },
                ).data(),
                work,
                resume=partial,
            )
        r["prior_test_use_ids"] = ["result:previous-final"]
        resumed = calculate(r, p.data(), s.data(), work, resume=partial)
        assert resumed["status"] == "completed"
        assert resumed["prior_test_use_ids"] == r["prior_test_use_ids"]
        assert resumed["test_usage_epochs"][-1]["ids"] == r["prior_test_use_ids"]
        assert all(
            t["prior_test_use_ids"] == r["prior_test_use_ids"]
            for t in resumed["trials"]
            if t["status"] == "completed"
        )


def test_final_target_poison_cannot_change_trial_scores_or_suggestion(
    tmp_path, monkeypatch
):
    store, r, work, p, s = run_fixture(tmp_path)
    with closing(store):
        original = calculate(r, p.data(), s.data(), work)
        final = set(original["plan"]["membership"]["test"])
        read = pl.read_parquet

        def poisoned(path, *args, **kwargs):
            frame = read(path, *args, **kwargs)
            if str(path) == r["path"] and {"y", "__vu_row_id"} <= set(frame.columns):
                return frame.with_columns(
                    pl.when(pl.col("__vu_row_id").is_in(list(final)))
                    .then(pl.lit(10000000.0))
                    .otherwise(pl.col("y"))
                    .alias("y")
                )
            return frame

        monkeypatch.setattr(pl, "read_parquet", poisoned)
        changed = calculate(r, p.data(), s.data(), work)
        assert changed["recommended"] == original["recommended"]
        assert [(t["parameters"], t["loss"]) for t in changed["trials"]] == [
            (t["parameters"], t["loss"]) for t in original["trials"]
        ]
        assert [e["metrics"] for e in changed["outer_evaluations"]] == [
            e["metrics"] for e in original["outer_evaluations"]
        ]


def test_small_grid_fold_metric_matches_independent_sklearn_reference(tmp_path):
    from sklearn.metrics import mean_absolute_error
    from sklearn.preprocessing import OneHotEncoder
    from sklearn.tree import DecisionTreeRegressor

    store, r, work, p, s = run_fixture(tmp_path)
    with closing(store):
        out = calculate(r, p.data(), s.data(), work)
        fold = out["trials"][0]["folds"][0]
        raw = pl.read_parquet(r["path"])
        a = raw.filter(pl.col("__vu_row_id").is_in(fold["fit_row_ids"]))
        b = raw.filter(pl.col("__vu_row_id").is_in(fold["evaluation_row_ids"]))
        encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore").fit(
            np.asarray(a["category"]).reshape(-1, 1)
        )
        x = np.column_stack(
            [
                np.asarray(a["x"]),
                encoder.transform(np.asarray(a["category"]).reshape(-1, 1)),
            ]
        )
        z = np.column_stack(
            [
                np.asarray(b["x"]),
                encoder.transform(np.asarray(b["category"]).reshape(-1, 1)),
            ]
        )
        model = DecisionTreeRegressor(
            max_depth=2, min_samples_leaf=2, random_state=p.seed
        ).fit(x, a["y"])
        assert fold["metrics"]["mae"] == pytest.approx(
            mean_absolute_error(b["y"], model.predict(z))
        )


def test_wall_budget_and_resume_do_not_reset_elapsed(tmp_path, monkeypatch):
    import time

    import veri_ufku.modeling.search as engine

    store, r, work, p, s = run_fixture(tmp_path)
    original = engine.train_model

    def slow(*args, **kwargs):
        time.sleep(1.05)
        return original(*args, **kwargs)

    monkeypatch.setattr(engine, "train_model", slow)
    with closing(store):
        s = replace(s, wall_seconds=1)
        out = calculate(r, p.data(), s.data(), work)
        assert out["status"] == "budget_exhausted"
        assert out["elapsed_seconds"] >= 1
        assert out["trials"][0]["status"] == "canceled"
        resumed = calculate(r, p.data(), s.data(), work, resume=out)
        assert resumed["status"] == "budget_exhausted"
        assert len(resumed["trials"]) == len(out["trials"])
        assert resumed["elapsed_seconds"] >= out["elapsed_seconds"]


def test_selection_and_bootstrap_are_inside_trial_fold(tmp_path, monkeypatch):
    from sklearn.feature_selection import VarianceThreshold
    from test_validation import setup_run

    store, r, work, p = setup_run(tmp_path, folds=2)
    r.update(search_id="search:selection49", prior_test_use_ids=[])
    original = VarianceThreshold.fit
    calls = []

    def spy(self, X, y=None):
        calls.append(len(X))
        return original(self, X, y)

    monkeypatch.setattr(VarianceThreshold, "fit", spy)
    with closing(store):
        s = SearchSpec(
            trials=1, curves=False, space={"methods": ["bagging"], "parameters": []}
        )
        out = calculate(r, p.data(), s.data(), work)
        assert out["status"] == "completed"
        final = set(out["plan"]["membership"]["test"])
        assert calls and max(calls) < len(out["plan"]["membership"]["development"]) + 1
        for trial in out["trials"]:
            for f in trial["folds"]:
                assert len(f["child_fit_scopes"]) == 10
                assert all(
                    set(ids) <= set(f["fit_row_ids"])
                    and not set(ids) & set(f["evaluation_row_ids"])
                    and not set(ids) & final
                    for ids in f["child_fit_scopes"]
                )


def test_stacking_search_extra_oof_cost_and_scopes_are_visible(tmp_path):
    store, r, work, p, _ = run_fixture(tmp_path)
    with closing(store):
        s = SearchSpec(
            trials=1, curves=False, space={"methods": ["stacking"], "parameters": []}
        )
        out = calculate(r, p.data(), s.data(), work)
        assert out["status"] == "completed"
        assert (
            out["estimated_cost"]["native_fit_upper"]
            > out["estimated_cost"]["fit_upper"]
        )
        for t in out["trials"]:
            for f in t["folds"]:
                assert f["stacking_oof"]
                for fold in f["stacking_oof"]:
                    assert not set(fold["fit_row_ids"]) & set(
                        fold["prediction_row_ids"]
                    )
                    assert set(fold["fit_row_ids"]) | set(
                        fold["prediction_row_ids"]
                    ) == set(f["fit_row_ids"])


def test_attempt_budget_is_cumulative_across_resume(tmp_path):
    store, r, work, p, s = run_fixture(tmp_path)
    with closing(store):
        s = replace(s, attempts=1)
        out = calculate(r, p.data(), s.data(), work)
        assert out["status"] == "budget_exhausted" and len(out["trials"]) == 1
        reserved = out["native_fit_reservations"]
        resumed = calculate(r, p.data(), s.data(), work, resume=out)
        assert resumed["status"] == "budget_exhausted" and len(resumed["trials"]) == 1
        assert resumed["native_fit_reservations"] >= reserved
