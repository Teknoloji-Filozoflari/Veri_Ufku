"""Independent power, SRM, denominators, assignment and source integrity references."""

import json
import math
from contextlib import closing
from dataclasses import replace

import numpy as np
import polars as pl
import pytest
from scipy import stats
from scipy.optimize import brentq
from test_dataset import column, prepare

from veri_ufku.statistics.contracts import AnalysisSpec
from veri_ufku.statistics.engine import calculate
from veri_ufku.statistics.experiments import power_plan
from veri_ufku.storage.analysis_store import publish
from veri_ufku.storage.project_model import ProjectError


def plan(**changes):
    return (
        dict(
            design="two_group_independent",
            randomization_unit="kişi",
            analysis_unit="kişi",
            primary_metric="önceden belirlenen ölçüm",
            measurement_window="7 gün",
            eligibility="kayıt öncesi uygun tüm kişiler",
            stop_rule="planlanan sabit ufuk ve ölçüm penceresi",
            monitoring="fixed_horizon",
            alpha=0.05,
            power=0.8,
            mde=0.2,
            baseline_value=0.3,
            sd=1.0,
            allocation=0.5,
            expected_attrition=0.1,
            design_effect=1,
            planned_total=20,
            randomized_confirmed=True,
            randomization_evidence="bağımsız Bernoulli randomizasyon planı R1",
            horizon_complete=True,
            analysis_population="ITT",
            protocol_column="",
            baseline_columns=[],
            guardrails=[],
        )
        | changes
    )


def recipe(r, method="experiment_mean", **changes):
    fields = dict(
        path="experiments",
        method=method,
        x=column(r, "outcome") if method.startswith("experiment_") else "",
        key=column(r, "person") if not method.startswith("power_") else "",
        group=column(r, "arm") if method.startswith("experiment_") else "",
        before="A",
        after="B",
        question="Önceden belirlenen deney",
        hypothesis="H0: B−A=0",
        unit="puan",
        observation_unit="kişi",
        independent=True,
        measurement_confirmed=True,
        assumptions_confirmed=True,
        scope="full",
        experiment_plan=plan(),
    )
    fields.update(changes)
    return AnalysisSpec(**fields)


def frame(binary=False):
    return pl.DataFrame(
        dict(
            person=[f"p{i:03}" for i in range(40)],
            arm=["A"] * 20 + ["B"] * 20,
            outcome=([0, 1] * 10 + [0, 1, 1, 1] * 5)
            if binary
            else [float(i % 7) for i in range(40)],
            baseline=[float(i % 5) for i in range(40)],
            protocol=[1] * 15 + [0] * 5 + [1] * 18 + [0] * 2,
            guard=[0, 0, 0, 1] * 10,
        )
    )


@pytest.mark.parametrize("metric", ["mean", "proportion"])
@pytest.mark.parametrize("allocation", [0.5, 0.3, 0.7])
def test_power_against_noncentral_t_and_normal_analytic_root(metric, allocation):
    p = dict(plan(allocation=allocation), metric=metric)
    out = power_plan(p)
    r = allocation / (1 - allocation)
    if metric == "mean":
        d = abs(p["mde"]) / p["sd"]

        def power(n):
            df = n * (1 + r) - 2
            crit = stats.t.ppf(1 - p["alpha"] / 2, df)
            nc = d * math.sqrt(n * r / (1 + r))
            return stats.nct.sf(crit, df, nc) + stats.nct.cdf(-crit, df, nc)
    else:
        h = abs(
            2 * math.asin(math.sqrt(p["baseline_value"] + p["mde"]))
            - 2 * math.asin(math.sqrt(p["baseline_value"]))
        )

        def power(n):
            z = stats.norm.ppf(1 - p["alpha"] / 2)
            nc = h * math.sqrt(n * r / (1 + r))
            return stats.norm.sf(z - nc) + stats.norm.cdf(-z - nc)

    expected = brentq(lambda n: power(n) - p["power"], 2, 2000)
    assert out["continuous_n_control"] == pytest.approx(expected, rel=1e-7)
    assert out["analyzable_control"] == math.ceil(expected)
    assert out["recruit_control"] == math.ceil(math.ceil(expected) / 0.9)
    assert out["rounded_design_power"] >= p["power"]


def test_mean_welch_reference_baseline_guardrail_and_atomic_reopen(tmp_path):
    store, r, work = prepare(tmp_path, frame())
    with closing(store):
        p = plan(
            baseline_columns=[column(r, "baseline")],
            guardrails=[
                dict(
                    column_id=column(r, "guard"),
                    name="zarar oranı",
                    metric="proportion",
                    limit=0.05,
                    direction="increase",
                )
            ],
        )
        s = recipe(r, experiment_plan=p)
        out = calculate(r, s, work)
        a = out["experiment_analysis"]
        y = frame()["outcome"].to_list()
        x = np.array(y[:20])
        z = np.array(y[20:])
        se = math.sqrt(x.var(ddof=1) / 20 + z.var(ddof=1) / 20)
        df = (x.var(ddof=1) + z.var(ddof=1)) ** 2 / (
            (x.var(ddof=1) ** 2 + z.var(ddof=1) ** 2) / 19
        )
        assert a["effect"]["p_value"] == pytest.approx(
            stats.ttest_ind(z, x, equal_var=False).pvalue
        )
        assert a["effect"]["absolute_ci"] == pytest.approx(
            [
                z.mean() - x.mean() - stats.t.ppf(0.975, df) * se,
                z.mean() - x.mean() + stats.t.ppf(0.975, df) * se,
            ]
        )
        assert a["baseline"][0]["smd"] == 0
        assert a["guardrails"][0]["absolute_change"] == 0
        assert a["randomization_verified"] is False
        assert (
            publish(store, store.state, out)["results"][-1]["analysis"][
                "experiment_analysis"
            ]
            == a
        )
    from veri_ufku.storage.project_store import ProjectStore

    with closing(ProjectStore.open(tmp_path / "project")) as restored:
        assert restored.state["results"][-1]["analysis"]["spec"]["experiment_plan"] == p


def test_binary_denominators_and_conservative_ci(tmp_path):
    store, r, work = prepare(tmp_path, frame(True))
    with closing(store):
        out = calculate(r, recipe(r, "experiment_proportion"), work)
        a = out["experiment_analysis"]
        e = a["effect"]
        assert [(v["assigned"], v["observed"], v["events"]) for v in a["arms"]] == [
            (20, 20, 10),
            (20, 20, 15),
        ]
        assert e["absolute_effect"] == 0.25 and e["relative_effect"] == 0.5
        assert e["p_value"] == pytest.approx(
            stats.fisher_exact([[15, 5], [10, 10]]).pvalue
        )
        ia = stats.beta.ppf([0.0125, 0.9875], [10, 11], [11, 10])
        ib = stats.beta.ppf([0.0125, 0.9875], [15, 16], [6, 5])
        assert e["absolute_ci"] == pytest.approx([ib[0] - ia[1], ib[1] - ia[0]])
        assert e["relative_ci"] == pytest.approx([ib[0] / ia[1] - 1, ib[1] / ia[0] - 1])


def test_missing_itt_not_complete_case_fake_inference(tmp_path):
    f = frame(True).with_columns(
        pl.Series("outcome", [None] + frame(True)["outcome"].to_list()[1:])
    )
    store, r, work = prepare(tmp_path, f)
    with closing(store):
        out = calculate(r, recipe(r, "experiment_proportion"), work)
        a = out["experiment_analysis"]
        assert (
            a["arms"][0]["assigned"] == 20
            and a["arms"][0]["observed"] == 19
            and a["arms"][0]["missing"] == 1
        )
        assert a["effect"]["p_value"] is None and "missing" in a["effect"]["status"]
        assert a["srm"]["denominator"] == 40
        assert a["missing_binary_worst_case_effect_bounds"] == pytest.approx(
            [0.2, 0.25]
        )
        assert out["used_rows"] == 40


def test_pp_and_srm_keep_full_roster(tmp_path):
    store, r, work = prepare(tmp_path, frame(True))
    with closing(store):
        a = calculate(
            r,
            recipe(
                r,
                "experiment_proportion",
                experiment_plan=plan(
                    analysis_population="PP", protocol_column=column(r, "protocol")
                ),
            ),
            work,
        )["experiment_analysis"]
        assert a["srm"]["denominator"] == 40
        assert [v["population"] for v in a["arms"]] == [15, 18]
        assert "association" in a["population_interpretation"]


def test_srm_exact_fixture_suppresses_primary_inference(tmp_path):
    f = frame().with_columns(pl.Series("arm", ["A"] * 5 + ["B"] * 35))
    store, r, work = prepare(tmp_path, f)
    with closing(store):
        a = calculate(r, recipe(r), work)["experiment_analysis"]
        assert a["srm"]["p_value"] == pytest.approx(
            2 * sum(math.comb(40, k) for k in range(6)) / 2**40
        )
        assert a["srm"]["flag"]
        assert a["effect"]["p_value"] is None


def test_assignment_seed_unit_identity_and_source_reorder(tmp_path):
    store, r, work = prepare(tmp_path, frame())
    with closing(store):
        s = recipe(r, "random_assignment")
        a = calculate(r, s, work)
        d = pl.read_parquet(a["paths"]["details"])
        b = calculate(r, s, work)
        assert d.equals(pl.read_parquet(b["paths"]["details"]))
        c = calculate(r, replace(s, seed=43), work)
        assert not d.equals(pl.read_parquet(c["paths"]["details"]))
        assert "draft" in a["assignment"]["status"]
        assert set(d["unit_id"]) == set(frame()["person"])
        publish(store, store.state, c)


@pytest.mark.parametrize(
    "changes",
    [
        {"monitoring": "sequential"},
        {"design": "cluster"},
        {"design": "paired"},
        {"design": "factorial"},
        {"randomization_unit": "klinik"},
        {"design_effect": 2},
        {"randomized_confirmed": False},
        {"randomization_evidence": ""},
        {"horizon_complete": False},
        {"analysis_population": "PP"},
        {"mde": 0},
        {"allocation": 1},
        {"alpha": 0},
        {"power": 0.4},
    ],
)
def test_unsupported_design_observational_and_peeking_rejected(tmp_path, changes):
    store, r, work = prepare(tmp_path, frame())
    with closing(store), pytest.raises(ProjectError):
        calculate(r, recipe(r, experiment_plan=plan(**changes)), work)


@pytest.mark.parametrize(
    "mutation",
    ["duplicate", "missing_key", "nan", "invalid_binary", "short_horizon", "filtered"],
)
def test_invalid_roster_or_measurement_and_horizon(tmp_path, mutation):
    f = frame(True)
    if mutation == "duplicate":
        f = f.with_columns(pl.lit("same").alias("person"))
    if mutation == "missing_key":
        f = f.with_columns(pl.Series("person", [None] + f["person"].to_list()[1:]))
    if mutation == "nan":
        f = f.with_columns(
            pl.Series(
                "outcome", [float("nan")] + f["outcome"].cast(pl.Float64).to_list()[1:]
            )
        )
    if mutation == "invalid_binary":
        f = f.with_columns(pl.lit(2).alias("outcome"))
    store, r, work = prepare(tmp_path, f)
    with closing(store):
        s = recipe(
            r,
            "experiment_proportion",
            experiment_plan=plan(planned_total=50)
            if mutation == "short_horizon"
            else plan(),
        )
        if mutation == "short_horizon":
            assert calculate(r, s, work)["primary"]["p_value"] is None
        else:
            if mutation == "filtered":
                s = replace(s, scope="view")
            with pytest.raises(ProjectError):
                calculate(r, s, work)


@pytest.mark.parametrize("method", ["power_mean", "power_proportion"])
def test_plan_save_no_observed_power(tmp_path, method):
    store, r, work = prepare(tmp_path, frame())
    with closing(store):
        out = calculate(r, recipe(r, method), work)
        assert out["used_rows"] == 0 and out["primary"]["p_value"] is None
        assert (
            json.loads(open(out["paths"]["result"]).read())["plan"]["design_effect"]
            == 1
        )
        publish(store, store.state, out)


def test_binary_zero_events_boolean_outcome_and_constant_mean(tmp_path):
    f = frame(True).with_columns(pl.lit(False).alias("outcome"))
    store, r, work = prepare(tmp_path, f)
    with closing(store):
        a = calculate(r, recipe(r, "experiment_proportion"), work)[
            "experiment_analysis"
        ]["effect"]
        assert a["p_value"] == 1
        assert a["absolute_ci"][0] < 0 < a["absolute_ci"][1]
        assert a["relative_effect"] is None and a["relative_ci"] is None
        f2 = tmp_path / "constant"
        f2.mkdir()
        other, q, w = prepare(f2, frame().with_columns(pl.lit(1.0).alias("outcome")))
        with closing(other):
            assert (
                "constant"
                in calculate(q, recipe(q), w)["experiment_analysis"]["effect"]["status"]
            )


def test_assignment_row_reordering_preserves_unit_arm(tmp_path):
    store, r, work = prepare(tmp_path, frame())
    folder = tmp_path / "reversed"
    folder.mkdir()
    other, q, w = prepare(folder, frame().reverse())
    with closing(store), closing(other):
        a = calculate(r, recipe(r, "random_assignment"), work)
        b = calculate(q, recipe(q, "random_assignment"), w)
        d1 = pl.read_parquet(a["paths"]["details"])
        d2 = pl.read_parquet(b["paths"]["details"])
        assert d1.select("unit_id", "arm").equals(d2.select("unit_id", "arm"))


def test_cancellation_and_details_source_tamper_atomic_rollback(tmp_path):
    from pathlib import Path
    from threading import Event

    from veri_ufku.importers.delimited import Control, hash_artifact
    from veri_ufku.jobs.workers import Canceled

    store, r, work = prepare(tmp_path, frame())
    with closing(store):
        event = Event()
        event.set()
        with pytest.raises(Canceled):
            calculate(r, recipe(r, "random_assignment"), work, Control(cancel=event))
        out = calculate(r, recipe(r, "random_assignment"), work)
        path = Path(out["paths"]["details"])
        detail = pl.read_parquet(path).with_columns(pl.lit("forged").alias("unit_id"))
        detail.write_parquet(path)
        out["fingerprints"]["details"] = hash_artifact(path, Control())
        commit = store.commit_id
        with pytest.raises(ProjectError, match="source|seed"):
            publish(store, store.state, out)
        assert store.commit_id == commit and not store.state["results"]
