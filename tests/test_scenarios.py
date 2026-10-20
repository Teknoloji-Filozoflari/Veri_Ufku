"""Analytic distribution/LP, bounded solver states and immutable project lineage."""

import copy
import multiprocessing as mp
from contextlib import closing
from dataclasses import replace

import pytest

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.scenario_contracts import ScenarioSpec, example
from veri_ufku.modeling.scenarios import Units, calculate, simulate, solve
from veri_ufku.storage import scenario_store as storage
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.validation_store import transaction


def q(value, unit="dimensionless"):
    return dict(value=value, unit=unit)


def lp(method="linear"):
    return dict(
        method=method,
        variables=[
            dict(
                name="x",
                unit="dimensionless",
                lower=0,
                upper=None,
                integer=method == "mixed-integer",
            ),
            dict(name="y", unit="dimensionless", lower=0, upper=None),
        ],
        objective=dict(unit="dimensionless", linear=[q(-3), q(-2)]),
        constraints=[
            dict(linear=[q(1), q(1)], sense="le", rhs=4, unit="dimensionless"),
            dict(linear=[q(1), q(0)], sense="le", rhs=2, unit="dimensionless"),
        ],
        assumptions="Explicit nonnegative production; shared capacity4; x cap2.",
    )


def canonical(s):
    return ScenarioSpec.from_dict(s).data()


def test_normal_analytic_quantiles_mcse_repeatability():
    s = example("monte-carlo")
    s.update(draws=100000)
    out = simulate(canonical(s), Control())
    assert abs(out["mean"] - 10) < 4 * out["mean_mcse"]
    assert out["sd"] == pytest.approx(2, abs=0.025)
    assert out["quantiles"][0]["value"] == pytest.approx(6.080072, abs=0.06)
    assert (
        out["analytic_reference"]["mean"] == 10
        and out["analytic_reference"]["variance"] == 4
    )
    assert out["sensitivity"][0]["spearman"] == pytest.approx(1)
    assert out == simulate(canonical(s), Control())
    s["seed"] = 43
    assert out["mean"] != simulate(canonical(s), Control())["mean"]


def test_correlated_normal_variance_and_psd_reject():
    s = example("monte-carlo")
    s["draws"] = 100000
    s["variables"] = [
        dict(
            name=n,
            unit="dimensionless",
            uncertainty=t,
            distribution=dict(kind="normal", mean=0, sd=1),
        )
        for n, t in [("x", "parameter"), ("y", "measurement")]
    ]
    s.update(dependence="normal-correlation", correlation=[[1, 0.8], [0.8, 1]])
    s["objective"] = dict(unit="dimensionless", linear=[q(1), q(1)])
    out = simulate(canonical(s), Control())
    assert out["analytic_reference"]["variance"] == pytest.approx(3.6)
    assert out["sd"] ** 2 == pytest.approx(3.6, rel=0.02)
    assert out["input_correlation"][0][1] == pytest.approx(0.8, abs=0.01)
    s["correlation"] = [[1, 2], [2, 1]]
    with pytest.raises(ProjectError, match="PSD"):
        simulate(canonical(s), Control())


@pytest.mark.parametrize(
    "kind,params,mean",
    [
        ("uniform", dict(low=0, high=2), 1),
        ("triangular", dict(low=0, mode=1, high=5), 2),
    ],
)
def test_other_distributions(kind, params, mean):
    s = example("monte-carlo")
    s["variables"][0]["distribution"] = dict(kind=kind, **params)
    out = simulate(canonical(s), Control())
    assert out["mean"] == pytest.approx(mean, abs=0.04)
    assert out["analytic_reference"] is None


def test_constant_output_and_uncertainty_record():
    s = example("monte-carlo")
    s["objective"]["linear"] = [q(0)]
    out = simulate(canonical(s), Control())
    assert out["mean_mcse"] == 0 and out["sensitivity"][0]["spearman"] is None
    assert all(v["mcse_approx"] == 0 for v in out["quantiles"])
    assert out["uncertainty_types"] == {"x": "measurement"}


@pytest.mark.parametrize("method", ["linear", "mixed-integer"])
def test_known_lp_and_milp(method):
    out = solve(canonical(lp(method)), Control())
    assert out["optimal"] and out["feasibility"]["feasible"]
    assert out["point"] == pytest.approx([2, 2]) and out["objective"] == pytest.approx(
        -10
    )
    assert out["status"] == "optimal_within_tolerance"
    assert (
        out["mip_relative_gap"] == 0
        if method == "mixed-integer"
        else out["mip_relative_gap"] is None
    )


def test_fractional_relaxation_and_integer_answer():
    s = lp("mixed-integer")
    s["constraints"][1]["rhs"] = 1.5
    out = solve(canonical(s), Control())
    assert out["point"] == pytest.approx([1, 3]) and out["objective"] == pytest.approx(
        -9
    )


@pytest.mark.parametrize("method", ["linear", "mixed-integer"])
def test_infeasible_unbounded_distinct(method):
    s = lp(method)
    s["constraints"].append(
        dict(linear=[q(1), q(0)], sense="ge", rhs=3, unit="dimensionless")
    )
    infeasible = solve(canonical(s), Control())
    assert (
        infeasible["status"] == "infeasible"
        and not infeasible["optimal"]
        and infeasible["point"] is None
    )
    s["constraints"] = []
    unbounded = solve(canonical(s), Control())
    assert unbounded["status"] == "unbounded" and not unbounded["optimal"]
    # LP must identify the truly unbounded ray, rather than conflate with infeasible.
    if method == "linear":
        assert unbounded["status"] == "unbounded"


def test_bounded_nonlinear_local_and_iteration_limit():
    s = canonical(example("nonlinear"))
    out = solve(s, Control())
    assert out["point"] == pytest.approx([3]) and out["objective"] == pytest.approx(
        0, abs=1e-9
    )
    assert (
        out["status"] == "local_candidate"
        and not out["optimal"]
        and not out["global_optimum_claim"]
    )
    s["maxiter"] = 1
    out = solve(s, Control())
    assert out["status"] == "iteration_limit" and not out["optimal"]


def test_real_solver_timeout_no_optimal_claim():
    # Real HiGHS MILP with a very small explicit time limit, no mocked solver.
    s = lp("mixed-integer")
    s["seconds"] = 1e-6
    out = solve(canonical(s), Control())
    assert out["status"] in ("timeout", "limit_reached") and not out["optimal"]
    # SLSQP checks wall time in actual objective calls as well as the supervisor.
    s = canonical(example("nonlinear"))
    s["seconds"] = 1e-6
    out = solve(s, Control())
    assert out["status"] == "timeout" and not out["optimal"]


def test_units_reference_mismatch_and_offset():
    s = example("linear")
    s["variables"][0]["unit"] = "centimeter"
    out = solve(canonical(s), Control())
    s["direction"] = "max"
    out = solve(canonical(s), Control())
    assert out["objective"] == pytest.approx(0.1)
    s["objective"]["unit"] = "second"
    with pytest.raises(ProjectError, match="uyumsuz"):
        solve(canonical(s), Control())
    with pytest.raises(ProjectError, match="offset"):
        Units([dict(unit="degC")])


@pytest.mark.parametrize(
    "mutation",
    [
        lambda s: s.update(code="print(1)"),
        lambda s: s.update(dependence="guessed"),
        lambda s: s.update(draws=100001),
        lambda s: s["variables"][0].update(uncertainty="unknown"),
        lambda s: s["variables"][0]["distribution"].update(sd=-1),
        lambda s: s.update(seed=True),
        lambda s: s.update(correlation=[[1]]),
        lambda s: s["variables"][0]["distribution"].update(mean=float("nan")),
    ],
)
def test_closed_bounded_recipe(mutation):
    s = example("monte-carlo")
    mutation(s)
    with pytest.raises((ProjectError, ValueError)):
        canonical(s)


def test_budget_cancel_and_no_publish(tmp_path):
    ctx = mp.get_context("spawn")
    cancel = ctx.Event()
    cancel.set()
    with pytest.raises(Canceled):
        simulate(canonical(example("monte-carlo")), Control(cancel))
    with pytest.raises(ProjectError, match="RAM"):
        simulate(
            canonical(example("monte-carlo")),
            Control(budget=replace(ComputeBudget(), ram_bytes=1024)),
        )
    with closing(ProjectStore.create(tmp_path / "project")) as store:
        s = example("linear")
        req = storage.request_for(store, store.state, s)
        out = calculate(req, s, tmp_path)
        previous = store.commit_id
        with pytest.raises(Canceled):
            storage.publish(store, store.state, out, Control(cancel))
        assert store.commit_id == previous and not store.state["results"]


def test_project_atomic_reopen_integrity_registry_lineage(tmp_path):
    from veri_ufku.storage.experiment_store import rows
    from veri_ufku.storage.lineage import graph

    store = ProjectStore.create(tmp_path / "project")
    s = example("monte-carlo")
    req = storage.request_for(store, store.state, s)
    out = calculate(req, s, tmp_path)
    state = storage.publish(store, store.state, out)
    record = state["results"][-1]
    assert (
        record["dataset_version_ids"] == []
        and state["datasets"] == []
        and state["sources"] == []
    )
    assert rows(store)[0]["run_id"] == out["run_id"]
    lineage = graph(state, store.manifest)
    assert any(n["id"] == record["id"] for n in lineage["nodes"])
    root = store.root
    store.close()
    with closing(ProjectStore.open(root)) as opened:
        assert storage.load(opened, record) == out
        stale = copy.deepcopy(opened.state)
        stale["results"] = []
        with pytest.raises(ProjectError):
            transaction(opened, stale, lambda draft: None)
        path = opened.path(record["scenario"]["details_uri"])
        path.write_bytes(b"broken")
        with pytest.raises(ProjectError, match="hash"):
            storage.load(opened, record)


def test_forged_timeout_optimal_rejected(tmp_path):
    from veri_ufku.modeling.validation import digest

    with closing(ProjectStore.create(tmp_path / "project")) as store:
        s = example("linear")
        out = calculate(storage.request_for(store, store.state, s), s, tmp_path)
        out["output"]["status"] = "timeout"
        out["identity"] = digest({k: v for k, v in out.items() if k != "identity"})
        with pytest.raises(ProjectError, match="optimum"):
            storage.publish(store, store.state, out)


def test_frozen_model_domain_whatif_and_optimization(tmp_path):
    from test_monitoring import trained_fixture

    from veri_ufku.modeling.scenarios import public_report

    store, r, w, work, monitor = trained_fixture(tmp_path)
    try:
        model = storage.models(store.state)[monitor.champion]
        card = model["card"]
        variables = [
            dict(
                name=f["id"],
                unit=f["unit"] or "dimensionless",
                lower=-1,
                upper=1,
                initial=0,
            )
            for f in card["features"]
        ]
        s = dict(
            method="what-if",
            variables=variables,
            objective=dict(unit=card["target"].get("unit") or "dimensionless"),
            model=dict(record_id=model["record_id"]),
            point=[0.0] * len(variables),
            assumptions="Training marginal range only; not causal.",
        )
        before = copy.deepcopy(store.state)
        req = storage.request_for(store, store.state, s)
        out = calculate(req, s, work)
        assert (
            out["output"]["status"] == "scenario_prediction" and out["fit_calls"] == 0
        )
        assert not out["output"]["outside_model_domain"]
        assert out["output"]["model_domain"]["fit_rows"] == len(card["fit_row_ids"])
        assert "fit_row_ids" not in public_report(out)["output"]["model_domain"]
        s["point"] = [1e6] * len(variables)
        outside = calculate(storage.request_for(store, store.state, s), s, work)
        assert outside["output"]["outside_model_domain"]
        s.pop("point")
        s["method"] = "model-optimize"
        optimized = calculate(storage.request_for(store, store.state, s), s, work)
        assert (
            optimized["output"]["feasibility"]["feasible"]
            and not optimized["output"]["optimal"]
        )
        assert store.state == before
        storage.publish(store, store.state, optimized)
        assert storage.load(store, store.state["results"][-1]) == optimized
        s["variables"][0]["upper"] = 1e6
        with pytest.raises(ProjectError, match="geçerlilik"):
            calculate(storage.request_for(store, store.state, s), s, work)
    finally:
        store.close()
