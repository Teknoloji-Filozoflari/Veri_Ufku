"""Analytic posterior references, real CPU sampler and numeric artifact contracts."""

import copy
import threading
from contextlib import closing
from dataclasses import replace

import h5py
import numpy as np
import polars as pl
import pytest
from scipy import stats
from test_dataset import column, prepare

from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.statistics.bayes import (
    backend,
    compare_results,
    conjugate,
    diagnostic_summary,
    fit,
    information_criteria,
)
from veri_ufku.statistics.contracts import AnalysisSpec
from veri_ufku.statistics.engine import calculate
from veri_ufku.storage.analysis_store import publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def plan(**kwargs):
    return (
        dict(
            alpha=1,
            beta=1,
            location=0,
            scale=2,
            noise_scale=1,
            group_scale=1,
            chains=2,
            draws=100,
            warmup=100,
            target_accept=0.9,
            sensitivity_factor=2,
        )
        | kwargs
    )


def frame(method):
    rng = np.random.default_rng(71)
    x = np.linspace(-1, 1, 40)
    return pl.DataFrame(
        dict(
            y=([1] * 8 + [0] * 2) * 4
            if method == "bayes_beta_binomial"
            else 1 + 2 * x + rng.normal(0, 0.5, 40),
            x=x,
            group=["a", "b", "c", "d"] * 10,
        )
    )


def recipe(r, method="bayes_beta_binomial", **changes):
    features = (
        [column(r, "x")] if method in ("bayes_linear", "bayes_hierarchical") else []
    )
    return AnalysisSpec(
        **(
            dict(
                path="bayes",
                method=method,
                x=column(r, "y"),
                features=features,
                bayes_feature_units={c: "metre" for c in features},
                group=column(r, "group") if method == "bayes_hierarchical" else "",
                question="Posterior ölçüm",
                unit="puan",
                observation_unit="kişi",
                measurement_confirmed=True,
                independent=True,
                assumptions_confirmed=True,
                scope="full",
                bayes_plan=plan(),
            )
            | changes
        )
    )


@pytest.fixture(autouse=True)
def isolated_backend_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "mpl"))


@pytest.mark.parametrize(
    "method",
    ["bayes_beta_binomial", "bayes_normal_mean", "bayes_linear", "bayes_hierarchical"],
)
def test_real_sampler_safe_publish_reopen_source(tmp_path, method):
    store, r, w = prepare(tmp_path, frame(method))
    before = __import__("pathlib").Path(r["path"]).read_bytes()
    with closing(store):
        spec = recipe(r, method)
        preview = calculate(r, spec, w, preflight=True)
        assert preview["prior_predictive"]["draws"] == 200 and "paths" not in preview
        result = calculate(r, spec, w)
        assert result["primary"]["p_value"] is None
        assert result["diagnostics"]["status"] == "diagnostic_fail"
        assert not result["diagnostics"]["reliable_badge"]
        assert not result["criteria"]["available"]
        assert result["prior_sensitivity"]["diagnostics"]["summary"]
        assert len(result["posterior_predictive"]["checks"]) == 3
        with h5py.File(result["paths"]["chains"], "r") as h:
            key = "theta" if method == "bayes_beta_binomial" else "intercept"
            assert h["posterior"][key].shape == (2, 100)
            assert h["posterior"][key].compression == "gzip"
            assert h["posterior"][key].chunks[1] <= 128
            assert h["log_likelihood/outcome"].shape == (2, 100, 40)
            assert h["posterior_predictive/outcome"].shape == (2, 100, 40)
        if result["conjugate_reference"]:
            estimate = result["diagnostics"]["summary"][0]["mean"]
            assert estimate == pytest.approx(
                result["conjugate_reference"]["mean"], abs=0.13
            )
        state = publish(store, store.state, result)
        assert (
            state["results"][-1]["analysis"]["observation_ids"]
            == result["observation_ids"]
        )
        if method == "bayes_beta_binomial":
            from pathlib import Path

            from veri_ufku.storage.project_store import file_hash

            active = store.commit_id
            with h5py.File(result["paths"]["chains"], "r+") as h:
                h["posterior/theta"][0, 0] = 0.001
            result["fingerprints"]["chains"] = file_hash(
                Path(result["paths"]["chains"])
            )
            with pytest.raises(ProjectError, match="summary/chain"):
                publish(store, store.state, result)
            assert store.commit_id == active
        path = store.root
        assert __import__("pathlib").Path(r["path"]).read_bytes() == before
    with closing(ProjectStore.open(path)) as reopened:
        assert (
            reopened.state["results"][-1]["analysis"]["diagnostics"]
            == result["diagnostics"]
        )


def test_conjugate_hand_calculations():
    spec = AnalysisSpec(path="bayes", method="bayes_beta_binomial", x="")
    p = plan()
    a = conjugate(np.array([1] * 8 + [0] * 2), spec, p)
    assert (a["alpha"], a["beta"], a["mean"]) == (9, 3, 0.75)
    assert a["credible_interval"] == pytest.approx(stats.beta.ppf([0.025, 0.975], 9, 3))
    spec = replace(spec, method="bayes_normal_mean")
    p = plan(scale=1, noise_scale=2)
    a = conjugate(np.array([2, 2, 2, 2]), spec, p)
    assert a["mean"] == 1 and a["sd"] == pytest.approx(np.sqrt(0.5))
    assert a["probability_above_zero"] == pytest.approx(stats.norm.cdf(np.sqrt(2)))


@pytest.mark.parametrize(
    "change",
    [
        {"alpha": 0},
        {"scale": -1},
        {"chains": 1},
        {"draws": 99},
        {"warmup": 0},
        {"target_accept": 1},
        {"location": float("nan")},
        {"script": "import os"},
    ],
)
def test_declarative_validation_rejects_invalid(tmp_path, change):
    store, r, w = prepare(tmp_path, frame("bayes_beta_binomial"))
    with closing(store), pytest.raises(ProjectError):
        calculate(r, recipe(r, bayes_plan=plan() | change), w)


@pytest.mark.parametrize(
    "values", [[1, None, 0, 1], [1, float("nan"), 0, 1], [1, 2, 0, 1]]
)
def test_missing_nonfinite_binary_retains_source(tmp_path, values):
    store, r, w = prepare(tmp_path, pl.DataFrame({"y": values}, strict=False))
    with closing(store), pytest.raises(ProjectError):
        calculate(r, recipe(r), w, preflight=True)


def test_prior_preview_seed_no_data_fit(tmp_path):
    store, r, w = prepare(tmp_path, frame("bayes_normal_mean"))
    with closing(store):
        a = calculate(r, recipe(r, "bayes_normal_mean"), w, preflight=True)
        b = calculate(r, recipe(r, "bayes_normal_mean"), w, preflight=True)
        assert a["prior_predictive"] == b["prior_predictive"]
        assert not list(w.glob("bayes-chains*"))


def test_sampler_cancellation_inside_actual_callback(tmp_path):
    event = threading.Event()
    callbacks = []

    def progress(*args):
        callbacks.append(args)
        event.set()

    spec = AnalysisSpec(
        path="bayes", method="bayes_normal_mean", x="", bayes_plan=plan(), unit="puan"
    )
    with pytest.raises(Canceled):
        fit(
            np.array([1.0, 2.0, 3.0, 4.0]),
            np.empty((4, 0)),
            None,
            [],
            spec,
            spec.bayes_plan,
            Control(event, progress),
            "test",
        )
    assert callbacks and event.is_set()


def test_rhat_ess_divergence_and_loo_waic_references():
    _, az = backend()
    rng = np.random.default_rng(4)
    samples = rng.normal(0, 1, (4, 1200))
    observed = np.linspace(-0.5, 0.5, 12)
    ll = stats.norm.logpdf(observed[None, None, :], samples[:, :, None], 2)
    idata = az.from_dict(
        posterior={"intercept": samples},
        sample_stats={
            "diverging": np.zeros_like(samples, dtype=bool),
            "reached_max_treedepth": np.zeros_like(samples, dtype=bool),
            "energy": rng.normal(size=samples.shape),
        },
        log_likelihood={"outcome": ll},
    )
    idata.log_likelihood = idata.log_likelihood.rename({"outcome_dim_0": "observation"})
    spec = AnalysisSpec(
        path="bayes",
        method="bayes_normal_mean",
        x="",
        bayes_plan=plan(chains=4, draws=1200),
    )
    d = diagnostic_summary(idata, spec)
    assert d["status"] == "diagnostics_passed" and not d["reliable_badge"]
    criteria = information_criteria(idata, d)
    assert criteria["available"] and criteria["ranking_allowed"]
    assert criteria["loo"]["elpd"] == pytest.approx(float(az.loo(idata).elpd_loo))
    assert criteria["waic"]["elpd"] == pytest.approx(float(az.waic(idata).elpd_waic))
    result = dict(
        dataset_version="v",
        observation_ids=list(range(12)),
        spec={"x": "y", "unit": "m"},
        method="bayes_normal_mean",
        criteria=criteria,
    )
    assert compare_results(result, result)["loo"]["elpd_difference"] == 0
    other = copy.deepcopy(result)
    other["observation_ids"].reverse()
    with pytest.raises(ProjectError):
        compare_results(result, other)
    idata.posterior["intercept"].values[0] += 10
    idata.sample_stats["diverging"].values[0, 0] = True
    fail = diagnostic_summary(idata, spec)
    assert fail["status"] == "diagnostic_fail" and fail["divergences"] == 1
    assert not information_criteria(idata, fail)["available"]
    idata.log_likelihood["outcome"].values[0, 0, 0] = np.inf
    assert not information_criteria(idata, d)["available"]


def test_budget_and_unsupported_weight(tmp_path):
    store, r, w = prepare(tmp_path, pl.DataFrame({"y": [0, 1] * 501}))
    with closing(store), pytest.raises(ProjectError, match="bütçe"):
        calculate(r, recipe(r), w, preflight=True)
    with pytest.raises(ProjectError, match="Weight"):
        replace(recipe(r), weight_type="frequency").validate(r["columns"])


def test_optional_backend_absence_controlled(monkeypatch):
    import builtins

    orig = builtins.__import__

    def unavailable(name, *args, **kwargs):
        if name == "pymc":
            raise ImportError()
        return orig(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", unavailable)
    with pytest.raises(ProjectError, match="İsteğe bağlı"):
        backend()


def test_real_normal_conjugate_sampler_converges_and_loo(tmp_path, monkeypatch):
    import socket

    def no_network(*a, **k):
        raise AssertionError("Bayes offline CPU must not make network calls")

    monkeypatch.setattr(socket, "create_connection", no_network)
    y = np.linspace(-1, 1, 24)
    spec = AnalysisSpec(
        path="bayes",
        method="bayes_normal_mean",
        x="",
        unit="m",
        bayes_plan=plan(chains=4, draws=1000, warmup=500),
    )
    idata, _, _, _ = fit(
        y,
        np.empty((len(y), 0)),
        None,
        [],
        spec,
        spec.bayes_plan,
        Control(),
        "reference",
    )
    d = diagnostic_summary(idata, spec)
    assert d["status"] == "diagnostics_passed", d
    ref = conjugate(y, spec, spec.bayes_plan)
    assert d["summary"][0]["mean"] == pytest.approx(ref["mean"], abs=0.025)
    assert d["summary"][0]["sd"] == pytest.approx(ref["sd"], rel=0.08)
    assert d["summary"][0]["credible_interval"] == pytest.approx(
        ref["credible_interval"], abs=0.03
    )
    criteria = information_criteria(idata, d)
    assert criteria["ranking_allowed"], criteria


def test_invalid_groups_rank_units_and_source_mutation(tmp_path):
    store, r, w = prepare(
        tmp_path, frame("bayes_hierarchical").with_columns(pl.lit("one").alias("group"))
    )
    with closing(store):
        with pytest.raises(ProjectError, match="grup"):
            calculate(r, recipe(r, "bayes_hierarchical"), w, preflight=True)
        with pytest.raises(ProjectError, match="birimi"):
            replace(recipe(r, "bayes_linear"), bayes_feature_units={}).validate(
                r["columns"]
            )
        from pathlib import Path

        Path(r["path"]).write_bytes(b"tampered")
        with pytest.raises(ProjectError, match="snapshot"):
            calculate(r, recipe(r), w, preflight=True)


def test_loo_waic_warnings_not_hidden():
    _, az = backend()
    rng = np.random.default_rng(9)
    theta = rng.normal(size=(4, 1000))
    ll = stats.norm.logpdf(
        np.array([0.0, 0.0, 50.0])[None, None, :], theta[:, :, None], 0.5
    )
    idata = az.from_dict(posterior={"intercept": theta}, log_likelihood={"outcome": ll})
    idata.log_likelihood = idata.log_likelihood.rename({"outcome_dim_0": "observation"})
    result = information_criteria(idata, {"status": "diagnostics_passed"})
    assert result["available"] and not result["ranking_allowed"]
    assert result["warnings"] and result["loo"]["warning"] and result["waic"]["warning"]
