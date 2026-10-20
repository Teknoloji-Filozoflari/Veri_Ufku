"""Hand KM/risk sets, censoring contracts, model likelihoods and immutable lineage."""

import json
import threading
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from scipy import optimize, stats
from test_dataset import column, prepare

from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.statistics.contracts import AnalysisSpec
from veri_ufku.statistics.survival import aft_objective, calculate, concordance, predict
from veri_ufku.statistics.survival_contracts import (
    SURVIVAL_METHODS,
    validate_time_dependent,
)
from veri_ufku.storage.analysis_store import publish
from veri_ufku.storage.project_model import ProjectError


def fixture(method="survival_km", n=200):
    if method in ("survival_km", "survival_logrank", "survival_cif"):
        return pl.DataFrame(
            dict(
                person=list(range(10)),
                duration=[1.0, 2.0, 2.0, 3.0, 4.0] * 2,
                event=[1, 0, 1, 2 if method == "survival_cif" else 1, 0] * 2,
                entry=[0.0, 1.0, 0.0, 1.0, 2.0] * 2,
                group=["A"] * 5 + ["B"] * 5,
                predictor=[float(i % 3) for i in range(10)],
            )
        )
    rng = np.random.default_rng(321)
    x = rng.normal(size=n)
    if method == "survival_cox":
        latent = rng.exponential(scale=5 * np.exp(-0.4 * x))
    else:
        latent = np.exp(1 + 0.4 * x + 0.6 * rng.normal(size=n))
    censor = np.full(n, 12.0)
    return pl.DataFrame(
        dict(
            person=np.arange(n),
            duration=np.minimum(latent, censor),
            event=(latent <= censor).astype(int),
            entry=np.zeros(n),
            group=np.where(np.arange(n) % 2, "A", "B"),
            predictor=x,
        )
    )


def recipe(r, method="survival_km", entry=False, group=False):
    plan = dict(
        censoring="competing_right"
        if method == "survival_cif"
        else "left_truncated_right"
        if entry
        else "right",
        entry=column(r, "entry") if entry else "",
        ties="breslow",
        event_definition="Single failure;0last followup/right censor; CIF1failure/2othercause",
        origin="Common protocol origin, durations measured after enrolment origin",
        censoring_assumption="Independent administrative followup; fixture mechanism, not observed-data proof",
        unit_confirmation=True,
        cause_labels={"1": "failure", "2": "other cause"}
        if method == "survival_cif"
        else {},
        risk_times=[0.0, 1.0, 2.0, 3.0, 4.0]
        if method not in ("survival_cox", "survival_aft")
        else [0.0, 1.0, 2.0],
        prediction_times=[0.0, 1.0, 2.0, 3.0],
        prediction_profile=[0.0] if method in ("survival_cox", "survival_aft") else [],
        prediction_group="A" if group and method == "survival_cox" else "",
    )
    return AnalysisSpec(
        path="survival",
        method=method,
        x=column(r, "duration"),
        y=column(r, "event"),
        key=column(r, "person"),
        group=column(r, "group") if group or method == "survival_logrank" else "",
        features=[column(r, "predictor")]
        if method in ("survival_cox", "survival_aft")
        else [],
        unit="day",
        observation_unit="person",
        question="Survival under declared censoring?",
        scope="full",
        max_iterations=100,
        independent=True,
        measurement_confirmed=True,
        assumptions_confirmed=True,
        survival_plan=plan,
    )


def test_hand_km_risk_counts_and_safe_roundtrip(tmp_path):
    store, r, w = prepare(tmp_path, fixture())
    with closing(store):
        s = recipe(r)
        out = calculate(r, s, w, Control())
        a = out["survival_analysis"]
        curve = a["curves"][0]["curve"]
        assert [v["time"] for v in curve] == [1, 2, 3]
        assert [v["survival"] for v in curve] == pytest.approx([0.8, 0.6, 0.3])
        assert [v["risk"] for v in curve] == [10, 8, 4]
        assert [v["events"] for v in curve] == [2, 2, 2]
        assert [v["at_risk"] for v in a["risk_tables"][0]["risk_table"]] == [
            10,
            10,
            8,
            4,
            2,
        ]
        assert a["curves"][0]["median"] == 3
        state = publish(store, store.state, out)
        saved = state["results"][-1]["analysis"]
        assert saved["plan"] == s.survival_plan
        assert set(saved["artifact_uris"]) == {
            "result",
            "members",
            "details",
            "diagnostic_png",
        }
        assert (
            "__vu_source_record_id" in pl.read_parquet(out["paths"]["details"]).columns
        )
        assert json.loads(open(out["paths"]["result"]).read())["survival_analysis"] == a


@pytest.mark.parametrize("method", ["survival_km", "survival_logrank", "survival_cox"])
def test_delayed_entry_backend_supported_risk_convention(tmp_path, method):
    f = fixture(method)
    if method == "survival_cox":
        f = f.with_columns((pl.col("duration") * 0.1).alias("entry"))
    store, r, w = prepare(tmp_path, f)
    with closing(store):
        out = calculate(r, recipe(r, method, entry=True), w, Control())[
            "survival_analysis"
        ]
        if method == "survival_cox":
            assert out["model"], out
            assert out["prediction"] is None and not out["model"]["prediction_allowed"]
        else:
            # At1, entries exactly1 excluded (statsmodels KM/logrank); two events,6risk.
            curve = out["curves"][0]["curve"]
            assert curve[0]["risk"] == (2 if method == "survival_logrank" else 4)
            assert curve[0]["survival"] == pytest.approx(0.5)
            assert out["risk_tables"][0]["risk_table"][0]["at_risk"] == 0


@pytest.mark.parametrize("method", SURVIVAL_METHODS)
def test_method_paths_and_publish(tmp_path, method):
    store, r, w = prepare(tmp_path, fixture(method))
    with closing(store):
        s = recipe(r, method)
        out = calculate(r, s, w, Control())
        a = out["survival_analysis"]
        if method in ("survival_cox", "survival_aft"):
            assert a["model"], a
            assert a["model"]["beta"][-1] == pytest.approx(0.4, abs=0.2)
            assert a["prediction"] and a["metrics"]["c_index"]["comparable"] > 0
            assert a["prediction"]["curve"][0]["survival"] == 1
            assert "probability" in a["coefficients"][-1]["ratio_meaning"]
            assert not a["metrics"]["time_dependent_brier"]["available"]
        if method == "survival_logrank":
            assert a["logrank"]["p_value"] == pytest.approx(1)
        if method == "survival_cif":
            first, second = a["curves"]
            assert [v["incidence"] for v in first["curve"]] == pytest.approx(
                [0.2, 0.4, 0.4, 0.4]
            )
            assert [v["incidence"] for v in second["curve"]] == pytest.approx(
                [0, 0, 0.3, 0.3]
            )
            assert all(
                a["incidence"] + b["incidence"] <= 1
                for a, b in zip(first["curve"], second["curve"])
            )
        publish(store, store.state, out)


def test_negative_invalid_entry_and_unsupported_censoring(tmp_path):
    store, r, w = prepare(
        tmp_path, fixture().with_columns(pl.lit(-1.0).alias("duration"))
    )
    with closing(store):
        with pytest.raises(ProjectError, match="Negatif"):
            calculate(r, recipe(r), w, Control())
        s = recipe(r)
        s.survival_plan["censoring"] = "interval"
        with pytest.raises(ProjectError, match="desteklemiyor"):
            s.validate(r["columns"])
    p = tmp_path / "invalid"
    p.mkdir()
    store, r, w = prepare(p, fixture().with_columns(pl.col("duration").alias("entry")))
    with closing(store):
        with pytest.raises(ProjectError, match="Invalid entry"):
            calculate(r, recipe(r, entry=True), w, Control())
        for method in ("survival_aft", "survival_cif"):
            with pytest.raises(ProjectError):
                recipe(r, method, entry=True).validate(r["columns"])


def test_aft_uncensored_against_log_ols_mle_and_analytic_gradient(tmp_path):
    f = fixture("survival_aft").with_columns(pl.lit(1).alias("event"))
    # Use actual uncensored lognormal values, no cap at12.
    rng = np.random.default_rng(32)
    x = rng.normal(size=200)
    time = np.exp(1 + 0.4 * x + 0.6 * rng.normal(size=200))
    f = f.with_columns(pl.Series("predictor", x), pl.Series("duration", time))
    store, r, w = prepare(tmp_path, f)
    with closing(store):
        model = calculate(r, recipe(r, "survival_aft"), w, Control())[
            "survival_analysis"
        ]["model"]
        design = np.c_[np.ones(200), x]
        beta = np.linalg.lstsq(design, np.log(time), rcond=None)[0]
        sigma = np.sqrt(np.mean((np.log(time) - design @ beta) ** 2))
        assert model["beta"] == pytest.approx(beta, abs=1e-6)
        assert model["sigma"] == pytest.approx(sigma, abs=1e-6)
        theta = np.array([0.5, 0.2, -0.3])
        event = np.array([0, 1] * 100)
        value, gradient = aft_objective(theta, design, time, event, Control())
        numeric = optimize.approx_fprime(
            theta, lambda p: aft_objective(p, design, time, event, Control())[0], 1e-7
        )
        assert gradient == pytest.approx(numeric, abs=1e-4)
        direct = -np.sum(
            np.where(
                event,
                stats.lognorm.logpdf(
                    time, s=np.exp(theta[-1]), scale=np.exp(design @ theta[:-1])
                ),
                stats.lognorm.logsf(
                    time, s=np.exp(theta[-1]), scale=np.exp(design @ theta[:-1])
                ),
            )
        )
        assert value == pytest.approx(direct)


def test_harrell_censoring_pair_counts():
    a = concordance(
        np.array([1, 2, 2, 3]),
        np.array([1, 1, 0, 0]),
        np.array([4.0, 3.0, 2.0, 1.0]),
        Control(),
    )
    assert a["comparable"] == 5 and a["concordant"] == 5 and a["value"] == 1
    b = concordance(
        np.array([1, 2, 2, 3]), np.array([1, 1, 0, 0]), np.ones(4), Control()
    )
    assert b["tied_risk"] == 5 and b["value"] == 0.5


def test_event_scarcity_cancel_safe_prediction_and_tamper(tmp_path):
    f = fixture("survival_cox").with_columns(pl.Series("event", [1] * 5 + [0] * 195))
    store, r, w = prepare(tmp_path, f)
    with closing(store):
        s = recipe(r, "survival_cox")
        out = calculate(r, s, w, Control())
        a = out["survival_analysis"]
        assert a["status"] == "model_diagnostic_fail" and a["model"] is None
        assert "azlığı" in a["diagnostics"]["failure"]
        cancel = threading.Event()
        cancel.set()
        with pytest.raises(Canceled):
            calculate(r, s, w, Control(cancel))
        out["survival_analysis"]["events"] += 1
        with pytest.raises(ProjectError):
            publish(store, store.state, out)
        bad = replace(s, unit="metres")
        with pytest.raises(ProjectError):
            bad.validate(r["columns"])


def test_time_dependent_schema_is_separate_and_execution_closed():
    f = pl.DataFrame(
        dict(
            id=["A", "A", "B"],
            start=[0, 2, 0],
            stop=[2, 4, 3],
            event=[0, 1, 0],
            x=[1, 2, 3],
        )
    )
    schema = dict(
        schema="SurvivalCountingProcess/v1",
        id="id",
        start="start",
        stop="stop",
        event="event",
        features=["x"],
        unit="day",
    )
    a = validate_time_dependent(f, schema)
    assert a["subjects"] == 2 and not a["execution_supported"]
    for bad in (
        f.with_columns(pl.Series("start", [0, 1, 0])),
        f.with_columns(pl.Series("event", [1, 1, 0])),
    ):
        with pytest.raises(ProjectError):
            validate_time_dependent(bad, schema)


@pytest.mark.parametrize("ties", ["breslow", "efron"])
@pytest.mark.parametrize("delayed", [False, True])
def test_cox_against_independent_partial_likelihood_and_baseline(
    tmp_path, ties, delayed
):
    f = fixture("survival_cox").with_columns(
        (pl.col("duration") * 3).round(0).truediv(3).clip(0.01).alias("duration")
    )
    if delayed:
        f = f.with_columns((pl.col("duration") * 0.2).alias("entry"))
    store, r, w = prepare(tmp_path, f)
    with closing(store):
        s = recipe(r, "survival_cox", entry=delayed)
        s.survival_plan["ties"] = ties
        a = calculate(r, s, w, Control())["survival_analysis"]
        model = a["model"]
        assert model, a
        t = f["duration"].to_numpy()
        e = f["event"].to_numpy()
        x = f["predictor"].to_numpy()
        entry = f["entry"].to_numpy() if delayed else np.zeros(len(t))

        def likelihood(beta):
            ll = 0.0
            for tm in np.unique(t[e == 1]):
                fail = (t == tm) & (e == 1)
                risk = (entry <= tm) & (t >= tm)
                d = int(fail.sum())
                weights = np.exp(beta * x)
                ll += beta * x[fail].sum()
                if ties == "breslow":
                    ll -= d * np.log(weights[risk].sum())
                else:
                    for j in range(d):
                        ll -= np.log(weights[risk].sum() - j / d * weights[fail].sum())
            return ll

        ref = optimize.minimize_scalar(
            lambda b: -likelihood(b),
            bounds=(-3, 3),
            method="bounded",
            options={"xatol": 1e-10},
        )
        assert model["beta"][0] == pytest.approx(ref.x, abs=1e-6)
        assert model["log_likelihood"] == pytest.approx(likelihood(ref.x), abs=1e-8)
        cumulative = 0.0
        for v in model["baselines"][0]["curve"]:
            tm = v["time"]
            risk = (entry <= tm) & (t >= tm)
            assert v["risk"] == int(risk.sum())
            cumulative += (
                np.sum((t == tm) & (e == 1)) / np.exp(model["beta"][0] * x[risk]).sum()
            )
            assert v["cumulative_hazard"] == pytest.approx(cumulative)


def test_model_predict_after_numeric_roundtrip_reject_extrapolation_and_code(tmp_path):
    store, r, w = prepare(tmp_path, fixture("survival_aft"))
    with closing(store):
        out = calculate(r, recipe(r, "survival_aft"), w, Control())
        model = json.loads(Path(out["paths"]["result"]).read_text())[
            "survival_analysis"
        ]["model"]
        a = predict(model, [0.0], [0.0, 1.0, 2.0, 3.0])
        assert a["curve"][0]["survival"] == 1
        assert all(
            x["survival"] >= y["survival"] for x, y in zip(a["curve"], a["curve"][1:])
        )
        for profile, times in (
            ([1e9], [1.0]),
            ([0.0], [1e9]),
            ([0.0, 1.0], [1.0]),
            ([0.0], [-1.0]),
        ):
            with pytest.raises(ProjectError):
                predict(model, profile, times)
        model["code"] = "import secrets"
        with pytest.raises(ProjectError):
            predict(model, [0.0], [1.0])


def test_unit_metadata_mismatch_and_published_unit_provenance(tmp_path):
    store, r, w = prepare(tmp_path, fixture())
    with closing(store):
        s = recipe(r)
        r["semantic_metadata"] = {s.x: {"unit": "hour"}}
        with pytest.raises(ProjectError, match="birimi"):
            calculate(r, s, w, Control())
        r["semantic_metadata"] = {s.x: {"unit": "day"}}
        a = calculate(r, s, w, Control())
        assert a["provenance"]["semantic_units"] == {s.x: "day"}
        # Dataset metadata mutation requires its normal versioned protocol; forged request is not accepted.
        with pytest.raises(ProjectError, match="metadata"):
            publish(store, store.state, a)


@pytest.mark.parametrize("method", ["survival_cox", "survival_aft"])
def test_rank_separation_fail_reports_are_visible_and_no_model(tmp_path, method):
    f = fixture(method).with_columns(pl.lit(1.0).alias("predictor"))
    store, r, w = prepare(tmp_path, f)
    with closing(store):
        a = calculate(r, recipe(r, method), w, Control())["survival_analysis"]
        assert (
            a["status"] == "model_diagnostic_fail"
            and a["model"] is None
            and a["prediction"] is None
        )
        assert "rank" in a["diagnostics"]["failure"]


def test_nonidentified_event_and_null_are_not_silently_recoded(tmp_path):
    for index, changes in enumerate(
        (pl.lit(2).alias("event"), pl.lit(None, dtype=pl.Int64).alias("event"))
    ):
        folder = tmp_path / str(index)
        folder.mkdir()
        store, r, w = prepare(folder, fixture().with_columns(changes))
        with closing(store):
            with pytest.raises(ProjectError):
                calculate(r, recipe(r), w, Control())


def test_logrank_against_hand_hypergeometric_risk_set_variance(tmp_path):
    f = pl.DataFrame(
        dict(
            person=list(range(8)),
            duration=[1.0, 2.0, 3.0, 4.0, 2.0, 4.0, 5.0, 6.0],
            event=[1, 1, 1, 0, 1, 1, 0, 0],
            entry=[0.0] * 8,
            group=["A"] * 4 + ["B"] * 4,
            predictor=[0.0] * 8,
        )
    )
    store, r, w = prepare(tmp_path, f)
    with closing(store):
        a = calculate(r, recipe(r, "survival_logrank"), w, Control())[
            "survival_analysis"
        ]["logrank"]
        t = f["duration"].to_numpy()
        e = f["event"].to_numpy()
        g = f["group"].to_numpy()
        oe = variance = 0.0
        for time in np.unique(t[e == 1]):
            risk = t >= time
            n = risk.sum()
            na = np.sum(risk & (g == "A"))
            d = np.sum((t == time) & (e == 1))
            da = np.sum((t == time) & (e == 1) & (g == "A"))
            oe += da - d * na / n
            variance += d * na * (n - na) * (n - d) / (n * n * (n - 1)) if n > 1 else 0
        reference = oe * oe / variance
        assert a["statistic"] == pytest.approx(reference)
        assert a["p_value"] == pytest.approx(stats.chi2.sf(reference, 1))


def test_separation_boundary_diagnostics_not_falsely_converged(tmp_path):
    for method in ("survival_cox", "survival_aft"):
        folder = tmp_path / method
        folder.mkdir()
        n = 60
        x = np.linspace(-2, 2, n)
        time = (
            np.arange(1.0, n + 1) if method == "survival_cox" else np.exp(1 + 0.4 * x)
        )
        f = pl.DataFrame(
            dict(
                person=np.arange(n),
                duration=time,
                event=np.ones(n, dtype=int),
                entry=np.zeros(n),
                group=np.where(np.arange(n) % 2, "A", "B"),
                predictor=x,
            )
        )
        store, r, w = prepare(folder, f)
        with closing(store):
            a = calculate(r, recipe(r, method), w, Control())["survival_analysis"]
            assert a["status"] == "model_diagnostic_fail", a
            assert a["model"] is None and a["prediction"] is None


def test_stratified_cox_baselines_and_prediction_same_group(tmp_path):
    store, r, w = prepare(tmp_path, fixture("survival_cox"))
    with closing(store):
        a = calculate(r, recipe(r, "survival_cox", group=True), w, Control())[
            "survival_analysis"
        ]
        assert a["model"], a
        assert {b["group"] for b in a["model"]["baselines"]} == {"A", "B"}
        assert a["metrics"]["c_index"]["value"] is None
        assert predict(a["model"], [0.0], [0.0, 1.0], "A")["group"] == "A"
        with pytest.raises(ProjectError):
            predict(a["model"], [0.0], [0.0, 1.0], "wrong")
