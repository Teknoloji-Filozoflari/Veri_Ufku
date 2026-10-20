"""Phase40 independent matrix / likelihood / LP / balanced-design references."""

import json
from contextlib import closing
from dataclasses import replace

import numpy as np
import polars as pl
import pytest
import statsmodels.api as sm
from scipy.optimize import linprog
from scipy.stats import f as fdist
from test_dataset import column, prepare

from veri_ufku.statistics.contracts import AnalysisSpec
from veri_ufku.statistics.engine import calculate
from veri_ufku.statistics.models import compare_information, predict
from veri_ufku.storage.analysis_store import publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def recipe(r, method="ols", **changes):
    return AnalysisSpec(
        path="models",
        method=method,
        x=column(r, "y"),
        question="Yanıt ile seçili predictors ilişkisi nedir?",
        hypothesis="Katsayı0",
        unit="puan",
        observation_unit="kişi / bağımsız grup",
        measurement_confirmed=True,
        independent=True,
        assumptions_confirmed=True,
        **changes,
    )


def linear():
    x = np.arange(20, dtype=float)
    return pl.DataFrame(
        dict(
            y=3 + 2 * x + np.sin(x) * 2,
            x=x,
            weight=1 + (x % 4),
            z=np.cos(x),
            g=["A", "B"] * 10,
            cluster=[str(i // 2) for i in range(20)],
        )
    )


def mixed_frame():
    rng = np.random.default_rng(400)
    groups = np.repeat(np.arange(12), 10)
    x = np.tile(np.linspace(-1, 1, 10), 12)
    intercept = np.repeat(rng.normal(0, 3, 12), 10)
    return pl.DataFrame(
        dict(
            y=2 + 1.5 * x + intercept + rng.normal(0, 0.4, 120),
            x=x,
            person=groups.astype(str),
        )
    )


def repeated_frame():
    rng = np.random.default_rng(402)
    person = np.repeat(np.arange(10), 3)
    phase = np.tile(["A", "B", "C"], 10)
    return pl.DataFrame(
        dict(
            y=np.repeat(rng.normal(0, 3, 10), 3)
            + np.tile([0.0, 1.0, 3.0], 10)
            + rng.normal(0, 0.3, 30),
            person=person.astype(str),
            phase=phase,
        )
    )


@pytest.mark.parametrize(
    "method,covariance",
    [
        ("ols", "nonrobust"),
        ("ols", "HC3"),
        ("ols", "cluster"),
        ("wls", "nonrobust"),
        ("wls", "HC3"),
        ("wls", "cluster"),
    ],
)
def test_linear_closed_matrix_and_sandwich_reference(tmp_path, method, covariance):
    store, r, work = prepare(tmp_path, linear())
    with closing(store):
        s = recipe(
            r,
            method,
            features=[column(r, "x")],
            covariance=covariance,
            weight=column(r, "weight") if method == "wls" else "",
            cluster=column(r, "cluster") if covariance == "cluster" else "",
        )
        result = calculate(r, s, work)
        frame = linear()
        X = np.column_stack([np.ones(20), frame["x"].to_numpy()])
        y = frame["y"].to_numpy()
        w = frame["weight"].to_numpy() if method == "wls" else np.ones(20)
        WX = X * np.sqrt(w[:, None])
        wy = y * np.sqrt(w)
        bread = np.linalg.inv(WX.T @ WX)
        beta = bread @ WX.T @ wy
        res = wy - WX @ beta
        if covariance == "nonrobust":
            cov = bread * (res @ res / 18)
        elif covariance == "HC3":
            hat = np.einsum("ij,jk,ik->i", WX, bread, WX)
            scores = WX * (res / (1 - hat))[:, None]
            cov = bread @ scores.T @ scores @ bread
        else:
            scores = np.stack(
                [
                    np.sum(WX[i : i + 2] * res[i : i + 2, None], axis=0)
                    for i in range(0, 20, 2)
                ]
            )
            cov = bread @ scores.T @ scores @ bread * (10 / 9) * (19 / 18)
        assert [c["estimate"] for c in result["coefficients"]] == pytest.approx(
            beta, rel=1e-10
        )
        assert [c["se"] for c in result["coefficients"]] == pytest.approx(
            np.sqrt(np.diag(cov)), rel=1e-10
        )
        assert result["diagnostics"]["heteroskedasticity"]["p"] >= 0
        assert len(result["diagnostics"]["influence"]["points"]) == 20
        assert result["provenance"]["backend"] == "statsmodels"
        assert predict(result, {column(r, "x"): 5})["value"] == pytest.approx(
            beta @ [1, 5]
        )
        state = publish(store, store.state, result)
        root = store.root
        store.close()
        reopened = ProjectStore.open(root)
        with closing(reopened):
            assert (
                reopened.state["results"][-1]["analysis"]["coefficients"]
                == state["results"][-1]["analysis"]["coefficients"]
            )


@pytest.mark.parametrize(
    "method,values,alpha",
    [
        ("glm_binomial", [0, 1, 1, 0, 1, 1, 1, 0], 1.0),
        ("glm_poisson", [0, 1, 2, 3, 1, 4, 5, 2], 1.0),
        ("glm_negative_binomial", [0, 1, 2, 3, 1, 4, 5, 2], 0.5),
    ],
)
def test_glm_intercept_closed_likelihood_information(tmp_path, method, values, alpha):
    store, r, work = prepare(tmp_path, pl.DataFrame({"y": values}))
    with closing(store):
        result = calculate(r, recipe(r, method, nb_alpha=alpha), work)
        mean = np.mean(values)
        expected = (
            np.log(mean / (1 - mean)) if method == "glm_binomial" else np.log(mean)
        )
        variance = (
            1 / (len(values) * mean * (1 - mean))
            if method == "glm_binomial"
            else (1 + alpha * mean) / (len(values) * mean)
            if method == "glm_negative_binomial"
            else 1 / (len(values) * mean)
        )
        c = result["coefficients"][0]
        assert c["effect_label"] == (
            "baseline odds"
            if method == "glm_binomial"
            else "baseline rate / expected count"
        )
        assert c["estimate"] == pytest.approx(expected, abs=1e-9)
        assert c["se"] == pytest.approx(np.sqrt(variance), rel=1e-5)
        from scipy.special import gammaln

        y = np.asarray(values)
        ll = (
            np.sum(y * np.log(mean) + (1 - y) * np.log(1 - mean))
            if method == "glm_binomial"
            else np.sum(y * np.log(mean) - mean - gammaln(y + 1))
            if method == "glm_poisson"
            else np.sum(
                gammaln(y + 1 / alpha)
                - gammaln(1 / alpha)
                - gammaln(y + 1)
                + (1 / alpha) * np.log(1 / (1 + alpha * mean))
                + y * np.log(alpha * mean / (1 + alpha * mean))
            )
        )
        assert result["fit"]["aic"] == pytest.approx(-2 * ll + 2, rel=1e-8)
        assert result["fit"]["bic"] == pytest.approx(-2 * ll + np.log(len(y)), rel=1e-8)
        assert predict(result, {})["value"] == pytest.approx(mean, rel=1e-8)
        assert (
            "odds" in c["effect_label"]
            if method == "glm_binomial"
            else "rate" in c["effect_label"]
        )


@pytest.mark.parametrize("covariance", ["nonrobust", "HC0", "cluster"])
def test_glm_offset_exposure_and_se_backend(tmp_path, covariance):
    rng = np.random.default_rng(410)
    x = np.linspace(-1, 1, 100)
    exposure = np.tile([1.0, 2.0, 3.0, 4.0], 25)
    y = rng.poisson(exposure * np.exp(0.4 + 0.5 * x))
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            dict(
                y=y,
                x=x,
                exposure=exposure,
                offset=np.log(exposure),
                cluster=np.repeat(np.arange(20), 5),
            )
        ),
    )
    with closing(store):
        base = recipe(
            r,
            "glm_poisson",
            features=[column(r, "x")],
            covariance=covariance,
            cluster=column(r, "cluster") if covariance == "cluster" else "",
        )
        result = calculate(r, replace(base, exposure=column(r, "exposure")), work)
        other = calculate(r, replace(base, offset=column(r, "offset")), work)
        assert result["coefficients"] == pytest.approx(other["coefficients"])
        args = dict(cov_type=covariance)
        if covariance == "cluster":
            args.update(
                cov_kwds=dict(groups=np.repeat(np.arange(20), 5), use_correction=True),
                use_t=True,
            )
        direct = sm.GLM(
            y, sm.add_constant(x), family=sm.families.Poisson(), exposure=exposure
        ).fit(**args)
        assert [c["se"] for c in result["coefficients"]] == pytest.approx(
            direct.bse, rel=1e-9
        )
        p = predict(result, {column(r, "x"): 0.2}, exposure=2)["value"]
        assert p == pytest.approx(2 * np.exp(direct.params @ [1, 0.2]))
        with pytest.raises(ProjectError, match="bağlam"):
            compare_information(result, other)


def test_baseline_interaction_injection_rank_missing_and_comparison(tmp_path):
    store, r, work = prepare(tmp_path, linear())
    with closing(store):
        s = recipe(
            r,
            features=[column(r, "x"), column(r, "g")],
            references={column(r, "g"): "A"},
            interactions=[[column(r, "x"), column(r, "g")]],
        )
        result = calculate(r, s, work)
        X = np.column_stack(
            [
                np.ones(20),
                np.arange(20),
                np.array([0, 1] * 10),
                np.arange(20) * np.array([0, 1] * 10),
            ]
        )
        assert [c["estimate"] for c in result["coefficients"]] == pytest.approx(
            np.linalg.lstsq(X, linear()["y"].to_numpy(), rcond=None)[0]
        )
        assert result["categorical_baselines"][column(r, "g")]["reference"] == "A"
        with pytest.raises(ProjectError, match="kategori"):
            predict(result, {column(r, "x"): 1, column(r, "g"): "NEW"})
        simpler = calculate(r, recipe(r, features=[column(r, "x")]), work)
        assert compare_information(result, simpler)["delta_aic"] == pytest.approx(
            result["fit"]["aic"] - simpler["fit"]["aic"]
        )
        for change in (
            dict(features=['__import__("os").system("touch /tmp/unsafe")']),
            dict(references={column(r, "g"): "absent"}),
            dict(interactions=[[column(r, "x"), column(r, "x")]]),
        ):
            with pytest.raises(ProjectError):
                calculate(r, replace(s, **change), work)


def test_quantile_lp_and_backend_ci(tmp_path):
    store, r, work = prepare(tmp_path, linear())
    with closing(store):
        s = recipe(
            r, "quantile", features=[column(r, "x")], covariance="robust", quantile=0.4
        )
        result = calculate(r, s, work)
        X = sm.add_constant(linear()["x"].to_numpy())
        y = linear()["y"].to_numpy()
        n = len(y)
        opt = linprog(
            np.r_[np.zeros(2), np.full(n, 0.4), np.full(n, 0.6)],
            A_eq=np.column_stack([X, np.eye(n), -np.eye(n)]),
            b_eq=y,
            bounds=[(None, None)] * 2 + [(0, None)] * (2 * n),
            method="highs",
        )
        assert opt.success
        beta = np.array([c["estimate"] for c in result["coefficients"]])
        res = y - X @ beta
        loss = np.sum(np.where(res >= 0, 0.4 * res, -0.6 * res))
        assert loss == pytest.approx(opt.fun, abs=1e-4)
        direct = sm.QuantReg(y, X).fit(q=0.4)
        assert [c["low"] for c in result["coefficients"]] == pytest.approx(
            direct.conf_int()[:, 0]
        )
        assert result["fit"]["aic"] is None
        with pytest.raises(ProjectError):
            compare_information(result, result)


def test_mixed_balanced_reml_variance_reference(tmp_path):
    frame = mixed_frame()
    store, r, work = prepare(tmp_path, frame)
    with closing(store):
        result = calculate(r, recipe(r, "mixed", group=column(r, "person")), work)
        y = frame["y"].to_numpy().reshape(12, 10)
        means = y.mean(axis=1)
        within = np.sum((y - means[:, None]) ** 2) / (12 * 9)
        between = np.var(means, ddof=1) - within / 10
        assert result["coefficients"][0]["estimate"] == pytest.approx(
            np.mean(y), abs=1e-8
        )
        assert result["fit"]["random_covariance"][0][0] == pytest.approx(
            between, rel=2e-4
        )
        assert result["fit"]["residual_variance"] == pytest.approx(within, rel=2e-4)
        assert result["fit"]["aic"] is None
        assert predict(result, {})["kind"] == "marginal fixed effect"


def test_repeated_independent_balanced_f_and_limits(tmp_path):
    frame = repeated_frame()
    store, r, work = prepare(tmp_path, frame)
    with closing(store):
        s = recipe(
            r, "repeated", group=column(r, "person"), within=[column(r, "phase")]
        )
        result = calculate(r, s, work)
        y = frame["y"].to_numpy().reshape(10, 3)
        grand = y.mean()
        ssphase = 10 * np.sum((y.mean(axis=0) - grand) ** 2)
        error = y - y.mean(axis=0)[None, :] - y.mean(axis=1)[:, None] + grand
        sserror = np.sum(error**2)
        F = (ssphase / 2) / (sserror / 18)
        assert result["model_tests"][0]["f"] == pytest.approx(F, rel=1e-10)
        assert result["model_tests"][0]["p"] == pytest.approx(fdist.sf(F, 2, 18))
        assert (
            not result["model_support"]["prediction"]
            and not result["model_support"]["model_save"]
        )
        with pytest.raises(ProjectError, match="prediction"):
            predict(result, {})
        state = publish(store, store.state, result)
        assert state["results"][-1]["analysis"]["model_tests"] == result["model_tests"]


@pytest.mark.parametrize(
    "method,change",
    [
        ("ols", dict(covariance="HC0")),
        ("glm_binomial", dict(covariance="HC3")),
        ("quantile", dict(covariance="cluster")),
        ("mixed", dict(covariance="HC3")),
        ("repeated", dict(covariance="cluster")),
        ("ols", dict(offset="x")),
        ("glm_poisson", dict(offset="x", exposure="weight")),
        ("ols", dict(random_slopes=["x"])),
        ("wls", dict(weight="weight", weight_type="frequency")),
    ],
)
def test_unsupported_combinations_are_rejected(tmp_path, method, change):
    store, r, work = prepare(tmp_path, linear())
    with closing(store):
        fields = {c["name"]: c["id"] for c in r["columns"]}
        change = {
            k: fields.get(v, v) if isinstance(v, str) else [fields.get(x, x) for x in v]
            for k, v in change.items()
        }
        with pytest.raises(ProjectError):
            calculate(r, recipe(r, method, **change), work)


@pytest.mark.parametrize(
    "kind",
    [
        "singular",
        "missing",
        "negative_weight",
        "small_cluster",
        "invalid_count",
        "unbalanced",
        "duplicates",
        "iteration",
        "separation",
    ],
)
def test_controlled_rank_data_convergence_errors(tmp_path, kind):
    if kind in ("unbalanced", "duplicates"):
        frame = (
            repeated_frame().head(29)
            if kind == "unbalanced"
            else pl.concat([repeated_frame(), repeated_frame().head(1)])
        )
    elif kind == "separation":
        frame = pl.DataFrame(dict(y=[0] * 10 + [1] * 10, x=list(range(20))))
    else:
        frame = linear()
        if kind == "singular":
            frame = frame.with_columns((pl.col("x") * 2).alias("z"))
        if kind == "missing":
            frame = frame.with_columns(
                pl.when(pl.col("x") == 1).then(None).otherwise(pl.col("y")).alias("y")
            )
        if kind == "negative_weight":
            frame = frame.with_columns(pl.lit(-1).alias("weight"))
    store, r, work = prepare(tmp_path, frame)
    with closing(store):
        changes = dict(features=[column(r, "x")]) if "x" in frame.columns else {}
        method = "ols"
        if kind == "singular":
            changes["features"].append(column(r, "z"))
        if kind == "negative_weight":
            method = "wls"
            changes["weight"] = column(r, "weight")
        if kind == "small_cluster":
            changes.update(covariance="cluster", cluster=column(r, "g"))
        if kind == "invalid_count":
            method = "glm_poisson"
        if kind in ("unbalanced", "duplicates"):
            method = "repeated"
            changes = dict(group=column(r, "person"), within=[column(r, "phase")])
        if kind == "iteration":
            method = "quantile"
            changes.update(covariance="robust", max_iterations=1)
        if kind == "separation":
            method = "glm_binomial"
        with pytest.raises(ProjectError):
            calculate(r, recipe(r, method, **changes), work)


def test_complete_case_and_json_bound_row_members(tmp_path):
    frame = linear().with_columns(
        pl.when(pl.col("x") == 2).then(None).otherwise(pl.col("y")).alias("y")
    )
    store, r, work = prepare(tmp_path, frame)
    with closing(store):
        result = calculate(
            r, recipe(r, features=[column(r, "x")], missing_policy="complete"), work
        )
        assert result["excluded_rows"] == 1 and result["used_rows"] == 19
        assert pl.read_parquet(result["paths"]["members"]).height == 19
        saved = json.loads(open(result["paths"]["result"]).read())
        assert saved["prediction_schema"] == result["prediction_schema"]


@pytest.mark.parametrize(
    "method,covariance",
    [
        ("glm_binomial", "HC0"),
        ("glm_binomial", "cluster"),
        ("glm_negative_binomial", "HC0"),
        ("glm_negative_binomial", "cluster"),
    ],
)
def test_full_glm_design_baseline_and_backend_reference(tmp_path, method, covariance):
    rng = np.random.default_rng(411)
    x = rng.normal(size=120)
    g = np.array(["B", "A"] * 60)
    cluster = np.repeat(np.arange(24), 5)
    X = np.column_stack([np.ones(120), x, g == "B", x * (g == "B")])
    eta = X @ np.array([-0.4, 0.7, 0.2, -0.15])
    p = 1 / (1 + np.exp(-eta))
    alpha = 0.7
    y = (
        rng.binomial(1, p)
        if method == "glm_binomial"
        else rng.negative_binomial(1 / alpha, 1 / (1 + alpha * np.exp(eta)))
    )
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(y=y, x=x, g=g, cluster=cluster))
    )
    with closing(store):
        s = recipe(
            r,
            method,
            features=[column(r, "x"), column(r, "g")],
            references={column(r, "g"): "A"},
            interactions=[[column(r, "x"), column(r, "g")]],
            covariance=covariance,
            nb_alpha=alpha,
            cluster=column(r, "cluster") if covariance == "cluster" else "",
        )
        result = calculate(r, s, work)
        family = (
            sm.families.Binomial()
            if method == "glm_binomial"
            else sm.families.NegativeBinomial(alpha=alpha)
        )
        kw = dict(cov_type=covariance)
        if covariance == "cluster":
            kw.update(cov_kwds=dict(groups=cluster, use_correction=True), use_t=True)
        direct = sm.GLM(y, X, family=family).fit(**kw)
        for key, reference in [
            ("estimate", direct.params),
            ("se", direct.bse),
            ("p", direct.pvalues),
            ("low", direct.conf_int()[:, 0]),
            ("effect", np.exp(direct.params)),
        ]:
            assert [c[key] for c in result["coefficients"]] == pytest.approx(
                reference, rel=1e-8
            )
        assert result["diagnostics"]["influence"]["method"] == "backend Cook/leverage"
        assert result["coefficients"][3]["effect_label"].startswith("interaction")
        assert result["coefficients"][1]["effect_label"] == (
            "odds ratio" if method == "glm_binomial" else "rate ratio"
        )


@pytest.mark.parametrize(
    "random_slope,reml", [(False, False), (True, False), (True, True)]
)
def test_mixed_random_design_backend_reference(tmp_path, random_slope, reml):
    rng = np.random.default_rng(420)
    frame = mixed_frame()
    x = frame["x"].to_numpy()
    y = frame["y"].to_numpy() + np.repeat(rng.normal(0, 0.8, 12), 10) * x
    frame = frame.with_columns(pl.Series("y", y))
    store, r, work = prepare(tmp_path, frame)
    with closing(store):
        s = recipe(
            r,
            "mixed",
            features=[column(r, "x")],
            group=column(r, "person"),
            random_slopes=[column(r, "x")] if random_slope else [],
            reml=reml,
        )
        result = calculate(r, s, work)
        X = sm.add_constant(x)
        Z = X if random_slope else np.ones((120, 1))
        direct = sm.MixedLM(y, X, groups=frame["person"].to_numpy(), exog_re=Z).fit(
            reml=reml, method="lbfgs", disp=False
        )
        assert direct.converged
        assert [c["estimate"] for c in result["coefficients"]] == pytest.approx(
            direct.fe_params, rel=1e-8
        )
        assert result["fit"]["random_covariance"] == pytest.approx(
            np.asarray(direct.cov_re)
        )
        if not reml:
            assert result["fit"]["aic"] == pytest.approx(direct.aic)
        assert predict(result, {column(r, "x"): 1})["value"] == pytest.approx(
            direct.fe_params @ [1, 1]
        )


def test_quantile_iid_and_two_within_factors(tmp_path):
    first = tmp_path / "quantile"
    first.mkdir()
    store, r, work = prepare(first, linear())
    with closing(store):
        result = calculate(
            r,
            recipe(
                r, "quantile", features=[column(r, "x")], covariance="iid", quantile=0.7
            ),
            work,
        )
        direct = sm.QuantReg(
            linear()["y"].to_numpy(), sm.add_constant(linear()["x"].to_numpy())
        ).fit(q=0.7, vcov="iid")
        assert [c["se"] for c in result["coefficients"]] == pytest.approx(direct.bse)
    second = tmp_path / "repeated"
    second.mkdir()
    rng = np.random.default_rng(421)
    people = np.repeat(np.arange(8), 4)
    a = np.tile(["A", "A", "B", "B"], 8)
    b = np.tile(["X", "Y", "X", "Y"], 8)
    frame = pl.DataFrame(
        dict(
            y=np.repeat(rng.normal(0, 2, 8), 4)
            + (a == "B")
            + (b == "Y")
            + rng.normal(0, 0.4, 32),
            person=people.astype(str),
            a=a,
            b=b,
        )
    )
    store, r, work = prepare(second, frame)
    with closing(store):
        result = calculate(
            r,
            recipe(
                r,
                "repeated",
                group=column(r, "person"),
                within=[column(r, "a"), column(r, "b")],
            ),
            work,
        )
        assert len(result["model_tests"]) == 3
        assert result["residual_summary"]["mean"] == pytest.approx(0, abs=1e-12)


def test_model_snapshot_hash_and_cancellation(tmp_path):
    from threading import Event

    from veri_ufku.importers.delimited import Control
    from veri_ufku.jobs.workers import Canceled

    store, r, work = prepare(tmp_path, linear())
    with closing(store):
        event = Event()
        event.set()
        with pytest.raises(Canceled):
            calculate(r, recipe(r), work, Control(event))
        r = dict(r, fingerprint=dict(r["fingerprint"], sha256="0" * 64))
        with pytest.raises(ProjectError, match="snapshot"):
            calculate(r, recipe(r), work)


def test_mixed_singular_slope_and_repeated_budget(tmp_path):
    first = tmp_path / "mixed"
    first.mkdir()
    frame = mixed_frame().with_columns(pl.lit(1.0).alias("x"))
    store, r, work = prepare(first, frame)
    with closing(store):
        with pytest.raises(ProjectError, match="Singular"):
            calculate(
                r,
                recipe(
                    r,
                    "mixed",
                    features=[column(r, "x")],
                    group=column(r, "person"),
                    random_slopes=[column(r, "x")],
                ),
                work,
            )
    second = tmp_path / "repeated"
    second.mkdir()
    frame = pl.DataFrame(
        dict(
            y=list(range(400)),
            person=[str(i // 4) for i in range(400)],
            phase=[str(i % 4) for i in range(400)],
        )
    )
    store, r, work = prepare(second, frame)
    with closing(store):
        with pytest.raises(ProjectError, match="300"):
            calculate(
                r,
                recipe(
                    r,
                    "repeated",
                    group=column(r, "person"),
                    within=[column(r, "phase")],
                ),
                work,
            )


def test_wls_weighted_design_rank_is_not_silently_pseudoinverted(tmp_path):
    frame = linear().with_columns(pl.Series("weight", [1e300] + [1e-300] * 19))
    store, r, work = prepare(tmp_path, frame)
    with closing(store):
        with pytest.raises(ProjectError, match="WLS ağırlıklı design singular"):
            calculate(
                r,
                recipe(r, "wls", features=[column(r, "x")], weight=column(r, "weight")),
                work,
            )
