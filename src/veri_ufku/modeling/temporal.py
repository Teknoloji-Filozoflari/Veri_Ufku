"""Bounded temporal diagnostics/backtests; no random row split, fit after origin or Qt."""

import importlib.metadata
import json
import math
import time
import warnings
from dataclasses import asdict
from datetime import UTC, datetime
from itertools import chain

import numpy as np
import pandas as pd
import polars as pl
from scipy.stats import norm

from veri_ufku.analytics.dataset import checked
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.temporal_contracts import TemporalSpec
from veri_ufku.storage.project_model import ProjectError, digest, encode, uid


def token(group):
    return json.dumps([group["group_type"], group["group"]], ensure_ascii=False)


def origins(n, base, extra, mode):
    dev = n - base.test_periods
    gap = extra.gap + extra.embargo
    if mode == "final":
        return [(dev - gap, dev, base.test_periods)]
    first = dev - base.folds * base.horizon
    if first - gap < max(base.minimum_history, 3 * extra.lags + 4):
        raise ProjectError(
            "İlk origin için yeterli train geçmişi yok; fold/horizon/gap azaltın."
        )
    return [
        (start - gap, start, base.horizon) for start in range(first, dev, base.horizon)
    ]


def scores(actual, pred, history, period=1, distribution=None, alpha=0.2):
    y = np.asarray(actual, float)
    p = np.asarray(pred, float)
    train = np.asarray(history, float)
    if y.shape != p.shape or not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ProjectError("Forecast actual/prediction finite shape geçersiz.")
    scale = (
        float(np.mean(np.abs(train[period:] - train[:-period])))
        if len(train) > period
        else 0.0
    )
    error = y - p
    result = dict(
        mae=float(np.mean(abs(error))),
        rmse=float(np.sqrt(np.mean(error**2))),
        n=len(y),
        mase=float(np.mean(abs(error)) / scale) if scale > 0 else None,
        mase_denominator=scale,
        mase_period=period,
        mase_status="valid" if scale > 0 else "undefined_constant_training_scale",
        mape=None,
        mape_reason="MAPE zero/near-zero unstable; not reported",
    )
    if distribution:
        sd = np.asarray(distribution["sd"])
        z = (y - p) / sd
        lower = p + norm.ppf(alpha / 2) * sd
        upper = p + norm.ppf(1 - alpha / 2) * sd
        result["probabilistic"] = dict(
            assumption="Gaussian model forecast; conditional on supplied future exog, not covariate uncertainty",
            alpha=alpha,
            coverage=float(np.mean((y >= lower) & (y <= upper))),
            mean_width=float(np.mean(upper - lower)),
            interval_score=float(
                np.mean(
                    (upper - lower)
                    + 2 / alpha * np.maximum(lower - y, 0)
                    + 2 / alpha * np.maximum(y - upper, 0)
                )
            ),
            crps=float(
                np.mean(
                    sd
                    * (
                        z * (2 * norm.cdf(z) - 1)
                        + 2 * norm.pdf(z)
                        - 1 / math.sqrt(math.pi)
                    )
                )
            ),
            pinball=[
                dict(
                    q=q,
                    value=float(
                        np.mean(
                            np.maximum(
                                q * (y - (p + norm.ppf(q) * sd)),
                                (q - 1) * (y - (p + norm.ppf(q) * sd)),
                            )
                        )
                    ),
                )
                for q in (0.1, 0.5, 0.9)
            ],
        )
    else:
        result["probabilistic"] = None
    return result


def diagnostics(y, base, extra, control):
    from statsmodels.tsa.seasonal import STL, seasonal_decompose
    from statsmodels.tsa.stattools import acf, adfuller, kpss, pacf

    y = np.asarray(y, float)
    output = {}
    for method in extra.diagnostics:
        control.check()
        if method in ("acf", "pacf", "stationarity") and np.ptp(y) <= 1e-12:
            output[method] = dict(
                status="unavailable",
                reason="Constant series; statistic undefined, no stationarity badge",
            )
            continue
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            if method in ("decomposition", "stl"):
                if len(y) < 2 * base.seasonal_period:
                    raise ProjectError(
                        "Decomposition/STL requires two complete cycles."
                    )
                fit = (
                    STL(y, period=base.seasonal_period, robust=True).fit()
                    if method == "stl"
                    else seasonal_decompose(
                        y, period=base.seasonal_period, model="additive", two_sided=True
                    )
                )
                output[method] = dict(
                    status="available",
                    scope="descriptive within development only; centered trend is not a causal forecasting feature",
                    period=base.seasonal_period,
                    trend=[float(v) if np.isfinite(v) else None for v in fit.trend],
                    seasonal=fit.seasonal.tolist(),
                    residual=[float(v) if np.isfinite(v) else None for v in fit.resid],
                )
            elif method in ("acf", "pacf"):
                lag = min(extra.lags, len(y) // 2 - 1)
                values = (
                    acf(y, nlags=lag, fft=True)
                    if method == "acf"
                    else pacf(y, nlags=lag, method="ywm")
                )
                output[method] = dict(
                    status="available",
                    lags=list(range(len(values))),
                    values=values.tolist(),
                    estimator="FFT biased autocorrelation"
                    if method == "acf"
                    else "Yule-Walker MLE; no adjusted denominator",
                )
            elif method == "stationarity":
                lag = min(extra.lags, len(y) // 2 - 3)
                a = adfuller(y, maxlag=lag, regression="c", autolag=None)
                k = kpss(y, regression="c", nlags=lag)
                output[method] = dict(
                    status="available",
                    adf=dict(
                        statistic=float(a[0]),
                        p=float(a[1]),
                        lag=a[2],
                        n=a[3],
                        null="unit root",
                    ),
                    kpss=dict(
                        statistic=float(k[0]),
                        p=float(k[1]),
                        lag=k[2],
                        null="level stationarity",
                    ),
                    warning="Tests depend on lag/trend, sample size and regime. Failure to reject is not proof. KPSS tabulated p-values may be bounds.",
                )
            else:
                # Explicit finite single-break penalized Gaussian mean-shift scan.
                minimum = max(4, extra.lags)
                rss0 = float(np.sum((y - y.mean()) ** 2))
                options = []
                for point in range(minimum, len(y) - minimum + 1):
                    control.check()
                    rss = float(
                        np.sum((y[:point] - y[:point].mean()) ** 2)
                        + np.sum((y[point:] - y[point:].mean()) ** 2)
                    )
                    gain = len(y) * math.log(
                        max(rss0, 1e-12) / max(rss, 1e-12)
                    ) - extra.change_penalty * math.log(len(y))
                    options.append((gain, point))
                gain, point = max(options)
                output[method] = dict(
                    status="available",
                    algorithm="single mean-shift penalized RSS scan",
                    penalty=extra.change_penalty,
                    min_segment=minimum,
                    candidate_index=point,
                    gain=float(gain),
                    detected=bool(gain > 0),
                    warning="Retrospective descriptive candidate, not online detection performance or forecast success; serial dependence and repeated search can create false alerts.",
                )
        output[method]["warnings"] = [str(w.message) for w in caught]
    return output


def croston(y, alpha):
    y = np.asarray(y, float)
    if np.any(y < 0):
        raise ProjectError("Croston requires nonnegative demand.")
    nz = np.flatnonzero(y > 0)
    if not len(nz):
        return 0.0
    first = int(nz[0])
    size = float(y[first])
    interval = float(first + 1)
    elapsed = 1
    for value in y[first + 1 :]:
        if value > 0:
            size = alpha * value + (1 - alpha) * size
            interval = alpha * elapsed + (1 - alpha) * interval
            elapsed = 1
        else:
            elapsed += 1
    return size / interval


def covariates(frame, group, base, extra, origin, steps, columns):
    names = {c["id"]: c["name"] for c in columns}
    rows = {rid: i for i, rid in enumerate(frame["__vu_row_id"].to_list())}
    pos = [rows[m[0]] for m in group["members"]]
    train = []
    future = []
    read_ids = []
    for cid in extra.known_future + extra.past_covariates:
        raw = frame[names[cid]][pos].cast(pl.Float64).to_numpy()
        if cid in extra.known_future:
            a = raw[extra.lags if extra.past_covariates else 0 : origin]
            b = raw[origin : origin + steps]
            read_ids.extend(chain.from_iterable(group["members"][: origin + steps]))
        else:
            # Fixed lag known for the complete multi-step horizon. No realized future x.
            a = raw[: origin - extra.lags]
            b = raw[origin - extra.lags : origin + steps - extra.lags]
            read_ids.extend(chain.from_iterable(group["members"][:origin]))
        if len(b) != steps or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ProjectError(
                "Covariate values missing/nonfinite within explicitly used scope; no implicit fill."
            )
        train.append(a)
        future.append(b)
    return (
        np.column_stack(train),
        np.column_stack(future),
        list(dict.fromkeys(read_ids)),
    )


def predict(method, history, steps, base, extra, control, exog=None, var=None):
    control.check()
    y = np.asarray(history, float)
    distribution = None
    metadata = dict(method=method, fit_n=len(y), warnings=[])
    if method in ("naive", "seasonal-naive"):
        from veri_ufku.modeling.time_series import forecast

        p = np.asarray(forecast(y, steps, method, base.seasonal_period, control))
    elif method == "croston":
        p = np.repeat(croston(y, extra.croston_alpha), steps)
        metadata["warning"] = (
            "Croston point forecast; positive demand intervals, biased estimator; no predictive distribution fabricated."
        )
    elif method == "var":
        from statsmodels.tsa.api import VAR

        matrix = np.asarray(var, float)
        transformed = np.diff(matrix, axis=0) if extra.difference else matrix
        if (
            transformed.shape[0] <= 3 * extra.lags + 5
            or np.linalg.matrix_rank(np.c_[np.ones(len(transformed)), transformed])
            != transformed.shape[1] + 1
        ):
            raise ProjectError("VAR history/rank insufficient; no arbitrary fit.")
        fit = VAR(transformed).fit(extra.lags, trend="c")
        metadata["fit_n"] = int(fit.nobs)
        if not fit.is_stable():
            raise ProjectError("VAR is unstable; stationary VAR forecast not accepted.")
        all_p = fit.forecast(transformed[-extra.lags :], steps)
        if extra.difference:
            all_p = matrix[-1] + np.cumsum(all_p, axis=0)
        p = all_p[:, 0]
        metadata.update(
            var_forecast=all_p.tolist(),
            variable_ids=[base.measurement] + extra.var_columns,
            stable=True,
            difference=extra.difference,
            assumption=extra.var_assumption,
        )
        # Integrated VAR interval covariance requires cumulative cross-step terms, not simple summation.
        if not extra.difference:
            sd = np.sqrt(fit.forecast_cov(steps)[:, 0, 0])
            distribution = dict(sd=sd.tolist())
    else:
        if exog and extra.past_covariates:
            y = y[extra.lags :]
            metadata.update(fit_n=len(y), target_warmup_excluded=extra.lags)
        from statsmodels.tsa.arima.model import ARIMA
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        seasonal = (
            tuple(extra.seasonal_order) + (base.seasonal_period,)
            if method in ("sarima", "sarimax")
            else (0, 0, 0, 0)
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            if method == "arima":
                fit = ARIMA(y, order=tuple(extra.order), trend="n").fit(
                    method_kwargs=dict(maxiter=100)
                )
            else:
                fit = SARIMAX(
                    y,
                    exog=exog[0] if exog else None,
                    order=tuple(extra.order),
                    seasonal_order=seasonal,
                    trend="n",
                    enforce_stationarity=True,
                    enforce_invertibility=True,
                ).fit(disp=False, maxiter=100)
            if not fit.mle_retvals.get("converged", True):
                raise ProjectError(
                    "ARIMA/SARIMAX convergence failed; no reliable-model badge."
                )
            result = fit.get_forecast(steps=steps, exog=exog[1] if exog else None)
            p = np.asarray(result.predicted_mean)
            sd = np.sqrt(np.asarray(result.var_pred_mean))
            distribution = dict(sd=sd.tolist())
            burn = max(int(fit.loglikelihood_burn), extra.lags)
            residual = np.asarray(fit.resid)[burn:]
            from statsmodels.stats.diagnostic import acorr_ljungbox

            lag = min(extra.lags, len(residual) // 3)
            lb = (
                acorr_ljungbox(
                    residual,
                    lags=[lag],
                    model_df=sum(extra.order[::2])
                    + sum(extra.seasonal_order[::2]) * (method != "arima"),
                    return_df=True,
                )
                if lag
                else None
            )
            metadata.update(
                aic=float(fit.aic),
                bic=float(fit.bic),
                converged=True,
                residual_n=len(residual),
                ljung_box_p=float(lb["lb_pvalue"].iloc[0])
                if lb is not None and np.isfinite(lb["lb_pvalue"].iloc[0])
                else None,
                residual_warning="Ljung-Box adequate lag/df and model assumptions required; white residuals do not prove forecast success.",
            )
        metadata["warnings"] = [str(w.message) for w in caught]
    if not np.isfinite(p).all() or (
        distribution
        and (not np.isfinite(distribution["sd"]).all() or min(distribution["sd"]) <= 0)
    ):
        raise ProjectError(
            "Nonfinite forecast/invalid distribution; intervals not fabricated."
        )
    control.check()
    return p, distribution, metadata


def global_predict(groups, origin, steps, extra, control):
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    x = []
    y = []
    gcount = len(groups)
    for gi, g in enumerate(groups):
        values = g["series"].iloc[:origin].to_numpy()
        for t in range(extra.lags, origin):
            x.append(np.r_[values[t - extra.lags : t], np.eye(gcount)[gi]])
            y.append(values[t])
    model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    model.fit(np.asarray(x), np.asarray(y))
    predictions = []
    for gi, g in enumerate(groups):
        history = g["series"].iloc[:origin].to_list()
        out = []
        for _ in range(steps):
            control.check()
            v = float(
                model.predict(
                    np.array([np.r_[history[-extra.lags :], np.eye(gcount)[gi]]])
                )[0]
            )
            out.append(v)
            history.append(v)
        predictions.append(np.asarray(out))
    return predictions, dict(
        method="global-ridge",
        lag=extra.lags,
        fit_n=len(y),
        fit_groups=[token(g) for g in groups],
        fit_row_ids=list(
            chain.from_iterable(
                chain.from_iterable(g["members"][:origin]) for g in groups
            )
        ),
        scaling="fit on pooled past training lag windows only; entity onehot; Ridge alpha1; recursive forecast",
    )


def hierarchy_leaves(edges, tokens):
    children = {}
    parents = {}
    for parent, child in edges:
        if parent == child or child in parents:
            raise ProjectError("Hierarchy cycle/double counting/multiple parent.")
        parents[child] = parent
        children.setdefault(parent, []).append(child)
    if set(children) & set(tokens):
        raise ProjectError(
            "Observed group cannot be both aggregate parent and leaf; double counting."
        )

    def visit(node, path):
        if node in path:
            raise ProjectError("Hierarchy cycle.")
        if node not in children:
            if node not in tokens:
                raise ProjectError("Hierarchy leaf group token unknown.")
            return [node]
        return list(
            chain.from_iterable(visit(c, path + [node]) for c in children[node])
        )

    out = {p: visit(p, []) for p in children}
    if set(chain.from_iterable(out.values())) != set(tokens):
        raise ProjectError("Hierarchy must cover all observed leaf groups.")
    return out


def series_task(groups, frame, columns, base, extra):
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.neighbors import NearestCentroid
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    tokens = [token(g) for g in groups]
    cutoffs = [len(g["series"]) - base.test_periods for g in groups]
    values = [g["series"].iloc[:n].to_numpy() for g, n in zip(groups, cutoffs)]
    if extra.task == "clustering":
        if not extra.clusters < len(groups) or len(set(cutoffs)) != 1:
            raise ProjectError(
                "Series clustering requires equal length aligned≥k+1 groups."
            )
        x = np.array([(v - v.mean()) / (v.std() or 1.0) for v in values])
        labels = KMeans(
            n_clusters=extra.clusters, n_init=10, random_state=extra.seed
        ).fit_predict(x)
        return dict(
            task="clustering",
            method="whole-series standardized Euclidean KMeans",
            scope="development prefix only; each entire series is one sample; no forecast accuracy claim",
            members=[
                dict(
                    series_id=t,
                    cluster=int(v),
                    row_ids=list(chain.from_iterable(g["members"][:n])),
                )
                for t, v, g, n in zip(tokens, labels, groups, cutoffs)
            ],
            silhouette=float(silhouette_score(x, labels))
            if 1 < len(set(labels)) < len(labels)
            else None,
            warning="Alignment and scaling define distance. Clusters are exploratory, not real classes or predictive success.",
        )
    train = [tokens.index(t) for t in extra.training_series if t in tokens]
    val = [tokens.index(t) for t in extra.validation_series if t in tokens]
    if len(train) != len(extra.training_series) or len(val) != len(
        extra.validation_series
    ):
        raise ProjectError("Unknown whole-series identity; no approximate matching.")
    names = {c["id"]: c["name"] for c in columns}
    rows = {r: i for i, r in enumerate(frame["__vu_row_id"])}
    labels = {}
    for i in train + val:
        g = groups[i]
        ids = list(chain.from_iterable(g["members"][: cutoffs[i]]))
        a = frame[names[extra.label]][[rows[r] for r in ids]].to_list()
        if (
            any(v is None for v in a)
            or len({(type(v).__name__, str(v)) for v in a}) != 1
        ):
            raise ProjectError(
                "One constant nonmissing categorical label per used series required."
            )
        labels[i] = str(a[0])
    if len({labels[i] for i in train}) < 2 or not {labels[i] for i in val} <= {
        labels[i] for i in train
    }:
        raise ProjectError(
            "Training needs≥2 classes; unseen validation class rejected."
        )
    features = np.array(
        [
            [v.mean(), v.std(), float(np.polyfit(np.arange(len(v)), v, 1)[0]), v[-1]]
            for v in values
        ]
    )
    model = make_pipeline(StandardScaler(), NearestCentroid())
    model.fit(features[train], [labels[i] for i in train])
    pred = model.predict(features[val])
    majority = max(
        sorted({labels[i] for i in train}),
        key=lambda c: sum(labels[i] == c for i in train),
    )
    return dict(
        task="classification",
        method="whole-series train-scaled mean/std/slope/last nearest centroid",
        training_series=extra.training_series,
        validation_series=extra.validation_series,
        fit_row_ids=list(
            chain.from_iterable(
                chain.from_iterable(groups[i]["members"][: cutoffs[i]]) for i in train
            )
        ),
        predictions=[
            dict(series_id=t, actual=labels[i], predicted=str(p))
            for t, i, p in zip(extra.validation_series, val, pred)
        ],
        accuracy=float(np.mean([labels[i] == p for i, p in zip(val, pred)])),
        baseline_accuracy=float(np.mean([labels[i] == majority for i in val])),
        n=len(val),
        warning="Whole entity series split; not random segments. Tiny entity validation is uncertain, labels are user supplied; no forecasting or causal claim. New-data model persistence unsupported.",
    )


def aggregate_folds(folds, method, horizon):
    selected = [f for f in folds if f["method"] == method]
    summary = []
    for h in range(horizon):
        records = [f["points"][h] for f in selected]
        if not records:
            continue
        errors = np.array([r["actual"] - r["predicted"] for r in records])
        scaled = [
            abs(r["actual"] - r["predicted"]) / f["metrics"]["mase_denominator"]
            for r, f in zip(records, selected)
            if f["metrics"]["mase_denominator"] > 0
        ]
        probabilistic = [r["probabilistic"] for r in records if r["probabilistic"]]
        summary.append(
            dict(
                horizon=h + 1,
                lead=selected[0]["gap"] + h + 1,
                mae=float(abs(errors).mean()),
                rmse=float(np.sqrt(np.mean(errors**2))),
                mase=float(np.mean(scaled)) if len(scaled) == len(records) else None,
                n=len(records),
                probabilistic={
                    k: float(np.mean([r[k] for r in probabilistic]))
                    for k in ("coverage", "mean_width", "crps", "interval_score")
                }
                if len(probabilistic) == len(records) and records
                else None,
            )
        )
    for h, entry in enumerate(summary):
        ps = [f["points"][h]["probabilistic"] for f in selected]
        if entry["probabilistic"] is not None:
            entry["probabilistic"]["pinball"] = [
                dict(q=q, value=float(np.mean([p["pinball"][i]["value"] for p in ps])))
                for i, q in enumerate((0.1, 0.5, 0.9))
            ]
    return summary


def calculate(request, base, workspace, control=None):
    from veri_ufku.modeling.time_series import normalize
    from veri_ufku.storage.experiment_store import capture

    control = control or Control()
    started = time.monotonic()
    extra = TemporalSpec.from_dict(base.advanced, base, request["columns"])
    mode = request.get("mode", "development")
    if request["row_count"] > 4000:
        raise ProjectError(
            "Advanced temporal budget:4000 rows/8 groups/1000 periods/group; no hidden sample."
        )
    checked(request, control)
    access = datetime.now(UTC).isoformat()
    ids = {
        base.date,
        base.measurement,
        base.group,
        *extra.known_future,
        *extra.past_covariates,
        *extra.var_columns,
        extra.label,
    }
    columns = request["columns"]
    names = {c["id"]: c["name"] for c in columns}
    selected = [names[c] for c in ids if c]
    frame = pl.read_parquet(request["path"], columns=["__vu_row_id"] + selected)
    if (
        frame.height != request["row_count"]
        or frame["__vu_row_id"].n_unique() != frame.height
    ):
        raise ProjectError("Temporal source RowId/count mismatch.")
    for cid in extra.known_future + extra.past_covariates + extra.var_columns:
        from veri_ufku.modeling.contracts import identifier

        c = next(c for c in columns if c["id"] == cid)
        if not frame[names[cid]].dtype.is_numeric() or identifier(
            c, request.get("semantic_metadata", {})
        ):
            raise ProjectError(
                "Covariate/VAR requires numeric nonidentifier column; no category code distance."
            )
    groups = normalize(frame, columns, base, request.get("semantic_metadata"))
    if len(groups) > 8 or any(len(g["series"]) > 1000 for g in groups):
        raise ProjectError("Advanced temporal group/period budget exceeded.")
    descendants = (
        hierarchy_leaves(extra.hierarchy, [token(g) for g in groups])
        if extra.hierarchy
        else {}
    )
    shared = (
        extra.method == "global-ridge" or extra.hierarchy or extra.task == "clustering"
    )
    if shared and any(
        not g["series"].index.equals(groups[0]["series"].index) for g in groups[1:]
    ):
        raise ProjectError(
            "Global/hierarchy/clustering requires exact shared calendar; asynchronous future history must not leak."
        )
    previous = request.get("development")
    if mode == "final" and (
        extra.task != "forecast"
        or not previous
        or previous["mode"] != "development"
        or previous["spec"] != base.data()
        or previous["snapshot_fingerprint"] != request["fingerprint"]
    ):
        raise ProjectError(
            "Final requires frozen same-source forecast development, not diagnostic/classification."
        )
    if mode not in ("development", "final"):
        raise ProjectError("Temporal mode invalid.")
    methods = list(
        dict.fromkeys(
            ["naive"]
            + (["seasonal-naive"] if base.seasonal_period else [])
            + ([extra.method] if extra.task == "forecast" else [])
        )
    )
    estimated_fits = (
        len(groups) * len(methods) * (base.folds if mode == "development" else 1)
    )
    if estimated_fits > 200:
        raise ProjectError("Temporal fit budget200 exceeded.")
    out = []
    global_cache = {}
    series_output = None
    if extra.task in ("classification", "clustering"):
        if mode != "development":
            raise ProjectError("Whole-series task final reveal unsupported.")
        series_output = series_task(groups, frame, columns, base, extra)
    for gi, g in enumerate(groups):
        control.check()
        s = g["series"]
        n = len(s)
        cutoff = n - base.test_periods
        y = s.to_numpy()
        schedule = origins(n, base, extra, mode)
        folds = []
        failed = []
        training_diagnostics = (
            diagnostics(y[:cutoff], base, extra, control)
            if mode == "development"
            else next(p for p in previous["groups"] if token(p) == token(g))[
                "diagnostics"
            ]
        )
        rows = {r: i for i, r in enumerate(frame["__vu_row_id"])}
        positions = [rows[m[0]] for m in g["members"]]
        variables = np.column_stack(
            [y]
            + [
                frame[names[c]][positions].cast(pl.Float64).to_numpy()
                for c in extra.var_columns
            ]
        )
        used_methods = methods if extra.task == "forecast" else []
        if mode == "final":
            saved = next(p for p in previous["groups"] if token(p) == token(g))
            used_methods = list(
                dict.fromkeys(
                    methods[: 1 + bool(base.seasonal_period)] + [saved["chosen"]]
                )
            )
        for method in used_methods:
            try:
                model_folds = []
                for origin, start, h in schedule:
                    control.check()
                    gap = start - origin
                    steps = gap + h
                    exog = None
                    cov_ids = []
                    if method == "global-ridge":
                        if origin not in global_cache:
                            global_cache[origin] = global_predict(
                                groups, origin, steps, extra, control
                            )
                        p = global_cache[origin][0][gi]
                        dist = None
                        meta = global_cache[origin][1]
                    else:
                        if method == "sarimax":
                            a, b, cov_ids = covariates(
                                frame, g, base, extra, origin, steps, columns
                            )
                            exog = (a, b)
                        if (
                            method == "var"
                            and not np.isfinite(variables[:origin]).all()
                        ):
                            raise ProjectError(
                                "VAR history has missing/nonfinite values."
                            )
                        p, dist, meta = predict(
                            method,
                            y[:origin],
                            steps,
                            base,
                            extra,
                            control,
                            exog,
                            variables[:origin],
                        )
                    p = p[gap:]
                    dist = dict(sd=dist["sd"][gap:]) if dist else None
                    actual = y[start : start + h]
                    m = scores(
                        actual,
                        p,
                        y[:origin],
                        base.seasonal_period or 1,
                        dist,
                        extra.alpha,
                    )
                    points = []
                    for j in range(h):
                        sd = dist["sd"][j] if dist else None
                        pm = scores(
                            actual[j : j + 1],
                            p[j : j + 1],
                            y[:origin],
                            base.seasonal_period or 1,
                            dict(sd=[sd]) if sd else None,
                            extra.alpha,
                        )["probabilistic"]
                        points.append(
                            dict(
                                date=s.index[start + j].isoformat(),
                                horizon=j + 1,
                                lead=gap + j + 1,
                                predicted=float(p[j]),
                                actual=float(actual[j]),
                                sd=sd,
                                lower=float(p[j] + norm.ppf(extra.alpha / 2) * sd)
                                if sd
                                else None,
                                upper=float(p[j] + norm.ppf(1 - extra.alpha / 2) * sd)
                                if sd
                                else None,
                                probabilistic=pm,
                            )
                        )
                    model_folds.append(
                        dict(
                            method=method,
                            origin=origin,
                            start=start,
                            gap=gap,
                            train_end=s.index[origin - 1].isoformat(),
                            validation_start=s.index[start].isoformat(),
                            validation_end=s.index[start + h - 1].isoformat(),
                            train_row_ids=list(
                                chain.from_iterable(g["members"][:origin])
                            ),
                            validation_row_ids=list(
                                chain.from_iterable(g["members"][start : start + h])
                            ),
                            covariate_read_row_ids=cov_ids,
                            metrics=m,
                            points=points,
                            backend=meta,
                        )
                    )
                folds.extend(model_folds)
            except ProjectError as error:
                control.check()
                if method in ("naive", "seasonal-naive"):
                    raise
                failed.append(dict(method=method, reason=str(error), status="invalid"))
        comparisons = []
        for method in used_methods:
            fs = [f for f in folds if f["method"] == method]
            if fs:
                es = np.array(
                    [p["actual"] - p["predicted"] for f in fs for p in f["points"]]
                )
                comparison = dict(
                    method=method,
                    mae=float(abs(es).mean()),
                    rmse=float(np.sqrt(np.mean(es**2))),
                    n=len(es),
                    mape=None,
                    mape_reason="not reported",
                    per_horizon=aggregate_folds(
                        fs,
                        method,
                        base.test_periods if mode == "final" else base.horizon,
                    ),
                )
                comparisons.append(comparison)
        chosen = (
            (
                next(p for p in previous["groups"] if token(p) == token(g))["chosen"]
                if mode == "final"
                else min(comparisons, key=lambda m: m["mae"])["method"]
            )
            if comparisons
            else "diagnostic-only"
        )
        if mode == "final" and chosen not in {f["method"] for f in folds}:
            raise ProjectError(
                "Frozen selected model failed final; no silent baseline replacement."
            )
        forecast_points = []
        if mode == "final":
            forecast_points = [
                dict(date=p["date"], predicted=p["predicted"], actual=p["actual"])
                for f in folds
                if f["method"] == chosen
                for p in f["points"]
            ]
        out.append(
            dict(
                group=g["group"],
                group_type=g["group_type"],
                series_id=token(g),
                timezone=g["timezone"],
                periods=n,
                duplicate_dates=g["duplicates"],
                missing_periods=0,
                train_end=s.index[cutoff - 1].isoformat(),
                test_start=s.index[cutoff].isoformat(),
                test_end=s.index[-1].isoformat(),
                train_row_ids=list(chain.from_iterable(g["members"][:cutoff])),
                test_row_ids=list(chain.from_iterable(g["members"][cutoff:])),
                chosen=chosen,
                comparisons=comparisons
                if mode == "development"
                else next(p for p in previous["groups"] if token(p) == token(g))[
                    "comparisons"
                ],
                invalid_models=failed,
                folds=folds,
                diagnostics=training_diagnostics,
                history=[
                    dict(date=s.index[i].isoformat(), actual=float(y[i]))
                    for i in range(max(0, cutoff - 120), cutoff)
                ],
                forecast=forecast_points,
                future_forecast=[],
                final_metrics=comparisons if mode == "final" else [],
                trend_per_period=float(np.polyfit(np.arange(cutoff), y[:cutoff], 1)[0]),
                seasonal_profile=[],
            )
        )
    reconciled = []
    if extra.hierarchy:
        lookup = {token(g): i for i, g in enumerate(groups)}
        for parent, leaves in descendants.items():
            common = set.intersection(
                *[{f["method"] for f in out[lookup[t]]["folds"]} for t in leaves]
            )
            for method in sorted(common):
                for fi in range(len(schedule)):
                    leaf_folds = [
                        [f for f in out[lookup[t]]["folds"] if f["method"] == method][
                            fi
                        ]
                        for t in leaves
                    ]
                    a = np.sum(
                        [[p["actual"] for p in f["points"]] for f in leaf_folds], axis=0
                    )
                    p = np.sum(
                        [[p["predicted"] for p in f["points"]] for f in leaf_folds],
                        axis=0,
                    )
                    origin = leaf_folds[0]["origin"]
                    history = np.sum(
                        [
                            groups[lookup[t]]["series"].iloc[:origin].to_numpy()
                            for t in leaves
                        ],
                        axis=0,
                    )
                    reconciled.append(
                        dict(
                            parent=parent,
                            leaf_ids=leaves,
                            method=method,
                            origin=origin,
                            predicted=p.tolist(),
                            actual=a.tolist(),
                            metrics=scores(a, p, history, base.seasonal_period or 1),
                            interval=None,
                            warning="Bottom-up sums of leaves only; no double counting, no aggregate CI without covariance model. Not MinT.",
                        )
                    )
    ident = "ts:" + uid()
    created = datetime.now(UTC).isoformat()
    capture_data = capture(dict(spec=base.data()))
    for package in ("statsmodels", "pandas"):
        capture_data["environment"][package] = importlib.metadata.version(package)
    capture_data["environment_hash"] = digest(encode(capture_data["environment"]))
    capture_data["config_scope"] = (
        "full TimeSeriesSpec including temporal protocol, availability, method and parameters"
    )
    from veri_ufku.domain.capabilities import CAPABILITIES

    method_id = (
        extra.method
        if extra.task == "forecast"
        else (
            extra.diagnostics[0]
            if extra.task == "diagnostics" and extra.diagnostics
            else extra.task
        )
    )
    capability_id = "model.temporal." + method_id
    if capability_id not in CAPABILITIES:
        capability_id = "model.time-series"
    prov = asdict(
        Provenance(
            provenance_id="provenance:" + uid(),
            dataset_versions=(request["version_id"],),
            config_revision=0,
            capability_id=capability_id,
            parameters_hash=digest(encode(base.data())),
            environment=(("statsmodels", importlib.metadata.version("statsmodels")),),
            created_at=created,
            scope="chronological origin fit; development diagnostics only; no final target choice",
            seed=extra.seed,
            seed_reason="seeded whole-series KMeans; deterministic numerical forecasting otherwise",
            source_snapshot_ids=(request["source_snapshot_id"],),
        )
    )
    result = dict(
        schema="TimeSeriesRun/v1",
        run_id=ident,
        status="completed",
        dataset_version=request["version_id"],
        snapshot_fingerprint=request["fingerprint"],
        source_snapshot_id=request["source_snapshot_id"],
        created_at=created,
        data_access_at=access,
        elapsed_seconds=time.monotonic() - started,
        seed=extra.seed,
        spec=base.data(),
        mode=mode,
        development_run_id=previous["run_id"] if previous and mode == "final" else None,
        groups=out,
        interval=None,
        feature_policy="chronological pooled or local fit; known_future explicitly declared, past x fixed lag; no whole-data fit",
        scope="Aligned regular panel; rolling-origin gap+embargo excluded from fit; held final targets not used during development",
        warning="Diagnostic tests do not prove stationarity or predictive success. Coverage not guaranteed after regime/parameter/covariate change.",
        advanced=dict(
            schema="TemporalRun/v1",
            spec=extra.data(),
            provenance=json.loads(encode(prov)),
            estimated_fit_count=estimated_fits,
            compute_budget=asdict(control.budget),
            series_task=series_output,
            reconciliation=reconciled,
        ),
        experiment_capture=capture_data,
        plan=dict(
            split_id="split:"
            + digest(
                encode(
                    [
                        (g["series_id"], g["train_row_ids"], g["test_row_ids"])
                        for g in out
                    ]
                )
            ),
            protocol_id="protocol:"
            + digest(
                encode(
                    dict(
                        date=base.date,
                        target=base.measurement,
                        frequency=base.frequency,
                        seasonal_period=base.seasonal_period,
                        horizon=base.horizon,
                        folds=base.folds,
                        test_periods=base.test_periods,
                        gap=extra.gap,
                        embargo=extra.embargo,
                        known_future=extra.known_future,
                        past_covariates=extra.past_covariates,
                        availability=extra.availability,
                        task=extra.task,
                    )
                )
            ),
        ),
    )
    checked(request, control)
    return result


def validate(value, dataset):
    """Safe finite archived contract validation, no fit or executable model import."""
    from veri_ufku.modeling.time_series_contracts import TimeSeriesSpec

    base = TimeSeriesSpec.from_dict(value["spec"])
    extra = TemporalSpec.from_dict(
        base.advanced, base, dataset["import_metadata"]["columns"]
    )
    if (
        value["schema"] != "TimeSeriesRun/v1"
        or value["dataset_version"] != dataset["version_id"]
        or value["advanced"]["spec"] != extra.data()
        or value["mode"] not in ("development", "final")
    ):
        raise ProjectError("Temporal archived schema/source/spec mismatch.")
    from veri_ufku.domain.capabilities import CAPABILITIES

    provenance = value["advanced"]["provenance"]
    if (
        provenance["capability_id"] not in CAPABILITIES
        or provenance["seed"] != extra.seed
        or provenance["dataset_versions"] != [value["dataset_version"]]
        or provenance["source_snapshot_ids"] != [value["source_snapshot_id"]]
    ):
        raise ProjectError("Temporal common provenance binding mismatch.")
    if value["advanced"]["provenance"]["parameters_hash"] != digest(
        encode(base.data())
    ):
        raise ProjectError("Temporal provenance config mismatch.")
    ids = []
    for g in value["groups"]:
        train, test = g["train_row_ids"], g["test_row_ids"]
        ids += train + test
        if (
            set(train) & set(test)
            or len(train + test) != len(set(train + test))
            or pd.Timestamp(g["train_end"]) >= pd.Timestamp(g["test_start"])
        ):
            raise ProjectError("Temporal archive train/test overlap.")
        if value["mode"] == "development" and g["final_metrics"]:
            raise ProjectError("Temporal development reveals final metric.")
        for f in g["folds"]:
            permitted = set(train + test) if value["mode"] == "final" else set(train)
            if (
                set(f["train_row_ids"]) & set(f["validation_row_ids"])
                or not set(f["train_row_ids"] + f["validation_row_ids"]) <= permitted
                or pd.Timestamp(f["train_end"]) >= pd.Timestamp(f["validation_start"])
            ):
                raise ProjectError("Temporal origin/identity leakage.")
            if (
                len(f["points"])
                != (base.test_periods if value["mode"] == "final" else base.horizon)
                or f["gap"] != extra.gap + extra.embargo
            ):
                raise ProjectError("Temporal horizon/gap mismatch.")
            a = np.array([p["actual"] for p in f["points"]])
            p = np.array([p["predicted"] for p in f["points"]])
            error = a - p
            m = f["metrics"]
            if (
                not np.isfinite(error).all()
                or not math.isclose(m["mae"], float(abs(error).mean()), abs_tol=1e-10)
                or not math.isclose(
                    m["rmse"], float(np.sqrt(np.mean(error**2))), abs_tol=1e-10
                )
            ):
                raise ProjectError("Temporal stored forecast metrics mismatch.")
            if value["mode"] == "development" and set(f["validation_row_ids"]) & set(
                test
            ):
                raise ProjectError("Temporal final targets exposed during development.")
        for c in g["comparisons"] + g["final_metrics"]:
            for h in c["per_horizon"]:
                if not all(math.isfinite(h[k]) and h[k] >= 0 for k in ("mae", "rmse")):
                    raise ProjectError("Temporal nonfinite metric.")
    if len(ids) != len(set(ids)):
        raise ProjectError("Panel source identity duplicated.")
    if extra.hierarchy:
        hierarchy_leaves(extra.hierarchy, [token(g) for g in value["groups"]])


def validate_source(value, frame, columns):
    """Recompute origin membership/denominator/actual targets on open; no refitting."""
    from veri_ufku.modeling.time_series import normalize
    from veri_ufku.modeling.time_series_contracts import TimeSeriesSpec

    base = TimeSeriesSpec.from_dict(value["spec"])
    extra = TemporalSpec.from_dict(base.advanced, base, columns)
    normalized = normalize(frame, columns, base)
    for g, saved in zip(normalized, value["groups"], strict=True):
        if token(g) != token(saved):
            raise ProjectError("Temporal group identity changed.")
        y = g["series"].to_numpy()
        expected = origins(len(y), base, extra, value["mode"])
        period = base.seasonal_period or 1
        for f in saved["folds"]:
            if (f["origin"], f["start"], len(f["points"])) not in expected:
                raise ProjectError(
                    "Stored temporal origin differs from frozen protocol."
                )
            origin, start, h = f["origin"], f["start"], len(f["points"])
            if f["train_row_ids"] != list(
                chain.from_iterable(g["members"][:origin])
            ) or f["validation_row_ids"] != list(
                chain.from_iterable(g["members"][start : start + h])
            ):
                raise ProjectError("Stored temporal origin RowId membership mismatch.")
            actual = [p["actual"] for p in f["points"]]
            p = [p["predicted"] for p in f["points"]]
            if actual != y[start : start + h].tolist():
                raise ProjectError("Temporal actual target/source mismatch.")
            sd = [p["sd"] for p in f["points"]]
            dist = dict(sd=sd) if sd and all(v is not None for v in sd) else None
            m = scores(actual, p, y[:origin], period, dist, extra.alpha)
            if encode(m) != encode(f["metrics"]):
                raise ProjectError(
                    "Training-only MASE/probabilistic metrics source mismatch."
                )
            if f["method"] == "sarimax":
                _, _, cov_ids = covariates(
                    frame, g, base, extra, origin, start - origin + h, columns
                )
                if cov_ids != f["covariate_read_row_ids"]:
                    raise ProjectError("Covariate access audit/source mismatch.")
        if value["mode"] == "development" and extra.task == "forecast":
            for c in saved["comparisons"]:
                if c["per_horizon"] != aggregate_folds(
                    saved["folds"], c["method"], base.horizon
                ):
                    raise ProjectError("Stored per-horizon backtest mismatch.")
    for reconciled in value["advanced"]["reconciliation"]:
        leaves = reconciled["leaf_ids"]
        fs = [
            next(
                f
                for f in g["folds"]
                if f["method"] == reconciled["method"]
                and f["origin"] == reconciled["origin"]
            )
            for g in value["groups"]
            if token(g) in leaves
        ]
        if len(fs) != len(leaves) or not np.allclose(
            reconciled["predicted"],
            np.sum([[p["predicted"] for p in f["points"]] for f in fs], axis=0),
            rtol=0,
            atol=1e-10,
        ):
            raise ProjectError("Bottom-up leaf total mismatch.")
