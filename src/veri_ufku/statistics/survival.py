"""Right-censored survival templates and safe numerical models; no pickle/user code."""

import json
import math
import warnings
from pathlib import Path

import numpy as np
import polars as pl
import scipy
import statsmodels
from scipy import optimize, special, stats
from statsmodels.duration.hazard_regression import PHReg
from statsmodels.duration.survfunc import CumIncidenceRight, SurvfuncRight, survdiff

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import checked, filtered
from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.statistics.survival_contracts import (
    MODELS,
    SURVIVAL_LABELS,
    finite_number,
)
from veri_ufku.storage.project_model import ProjectError, uid

CAUTION = "Censored kayıt kayıp/null veri değildir: bilinen son takip süresi risk set'e katkı verir. Independent censoring/truncation kullanıcı gerekçesidir; gözlenen veriden kanıtlanmaz. Hazard ratio event olasılığı değildir. KM complement competing cause incidence değildir. Model tanıları geçse bile güvenilirlik veya nedensellik kanıtı yok."


def load(request, spec, control):
    q, schema, names = filtered(request, ViewSpec())
    n = q.select(pl.len()).collect(engine="streaming").item()
    limit = 2000 if spec.method in MODELS else 10000
    if not 2 <= n <= limit or n * 8192 > control.budget.ram_bytes // 2:
        raise ProjectError("Sağkalım2–10000; model<=2000 kayıt/RAM bütçesi aşıldı.")
    p = spec.survival_plan
    for cid in (spec.x, p["entry"]):
        unit = request.get("semantic_metadata", {}).get(cid, {}).get("unit", "")
        if unit and unit != spec.unit:
            raise ProjectError(
                "Sözlükteki duration/entry birimi seçili zaman birimiyle farklı; açık birim dönüşümü veya metadata onayı gerekli."
            )
    fields = (
        [spec.x, spec.y, spec.key]
        + [v for v in (p["entry"], spec.group) if v]
        + spec.features
    )
    numeric = [spec.x, spec.y] + ([p["entry"]] if p["entry"] else []) + spec.features
    for c in fields:
        dtype = schema[names[c]]
        if (
            dtype.is_nested()
            or dtype == pl.Binary
            or isinstance(dtype, pl.Decimal)
            or dtype.is_temporal()
        ):
            raise ProjectError(
                "Duration/event/kimlik alanları skaler; zaman Date değil aynı birimde duration olmalı."
            )
        if c in numeric and not dtype.is_numeric():
            raise ProjectError("Duration/event/entry/covariate fiziksel sayı olmalı.")
        if c in numeric and dtype.is_integer():
            maximum = (
                q.select(pl.col(names[c]).cast(pl.Float64).abs().max()).collect().item()
            )
            if maximum is not None and maximum > 2**53:
                raise ProjectError("Float64 kayıpsız integer sınırı aşıldı.")
    source = [
        c
        for c in (
            "__vu_source_record_id",
            "__vu_source_locator",
            "__vu_expansion_index",
        )
        if c in schema
    ]
    frame = (
        q.select("__vu_row_id", *source, *[pl.col(names[c]).alias(c) for c in fields])
        .collect(engine="streaming")
        .sort("__vu_row_id")
    )
    for c in fields:
        vals = frame[c].to_list()
        if any(
            v is None
            or not str(v).strip()
            or isinstance(v, float)
            and not math.isfinite(v)
            for v in vals
        ):
            raise ProjectError(
                "Sağkalım alanı null/sonsuz; censored0 durumuyla missing alanı karıştırmayın."
            )
        if c in numeric and any(abs(float(v)) > 1e12 for v in vals):
            raise ProjectError("Sağkalım sayısal kararlılık sınırı aşıldı.")
    if frame[spec.key].n_unique() != n:
        raise ProjectError(
            "Statik sağkalım şeması bir unit/bir satır; time-dependent interval ayrı şema."
        )
    t = frame[spec.x].to_numpy().astype(float)
    e = frame[spec.y].to_numpy().astype(float)
    if np.any(t < 0) or spec.method in MODELS and np.any(t <= 0):
        raise ProjectError("Negatif duration reddi; Cox/AFT için duration>0 gerekli.")
    allowed = (
        set(range(len(p["cause_labels"]) + 1))
        if spec.method == "survival_cif"
        else {0, 1}
    )
    if not set(e) <= allowed:
        raise ProjectError("Event0censored/1event veya açık competing1..K kodu olmalı.")
    if spec.method == "survival_cif" and set(e[e > 0]) != allowed - {0}:
        raise ProjectError(
            "Her beyan edilen competing cause en az1 gözlenen event ister."
        )
    if p["entry"]:
        entry = frame[p["entry"]].to_numpy().astype(float)
        if np.any(entry < 0) or np.any(entry >= t):
            raise ProjectError(
                "Invalid entry:0<=entry<duration gerekli; left censoring değildir."
            )
    if spec.group:
        groups = frame[spec.group].unique().to_list()
        if (
            not 2 <= len(groups) <= 8
            or any(len(str(v)) > 200 for v in groups)
            or len({str(v) for v in groups}) != len(groups)
        ):
            raise ProjectError("Group/strata2–8 farklı skaler etiket ister.")
        if spec.method == "survival_cox" and p["prediction_group"] not in set(
            map(str, groups)
        ):
            raise ProjectError("Prediction strata mevcut group etiketi olmalı.")
    if any(v > float(t.max()) for v in p["risk_times"]):
        raise ProjectError("Risk table zamanı gözlenen takip desteği dışına çıkamaz.")
    control.check()
    return frame


def arrays(frame, spec):
    t = frame[spec.x].to_numpy().astype(float)
    event = frame[spec.y].to_numpy().astype(int)
    entry = (
        frame[spec.survival_plan["entry"]].to_numpy().astype(float)
        if spec.survival_plan["entry"]
        else None
    )
    groups = (
        np.array(list(map(str, frame[spec.group].to_list())))
        if spec.group
        else np.repeat("all", len(t))
    )
    x = (
        frame.select(spec.features).to_numpy().astype(float)
        if spec.features
        else np.empty((len(t), 0))
    )
    return t, event, entry, groups, x


def risk_table(t, event, entry, times, cox=False):
    result = []
    for time in times:
        eligible = (
            np.ones(len(t), bool)
            if entry is None
            else entry <= time
            if cox
            else entry < time
        )
        risk = eligible & (t >= time)
        result.append(
            dict(
                time=float(time),
                at_risk=int(risk.sum()),
                events_at_time=int(np.sum(risk & (t == time) & (event > 0))),
                censored_at_time=int(np.sum(risk & (t == time) & (event == 0))),
                not_yet_entered=int(np.sum(~eligible)),
                risk_convention="entry<=t<=duration"
                if cox and entry is not None
                else "entry<t<=duration"
                if entry is not None
                else "t<=duration; event before tied censoring",
            )
        )
    return result


def km(t, event, entry, label, times, confidence):
    backend = SurvfuncRight(t, event, entry=entry)
    curve = []
    z = float(stats.norm.ppf((1 + confidence) / 2))
    for time, s, se, risk, events in zip(
        backend.surv_times,
        backend.surv_prob,
        backend.surv_prob_se,
        backend.n_risk,
        backend.n_events,
    ):
        interval = None
        if 0 < s < 1 and math.isfinite(se):
            error = float(se / (s * abs(math.log(s))))
            center = math.log(-math.log(s))
            interval = [
                math.exp(-math.exp(center + z * error)),
                math.exp(-math.exp(center - z * error)),
            ]
        curve.append(
            dict(
                time=float(time),
                survival=float(s),
                se=float(se) if math.isfinite(se) else None,
                interval=interval,
                risk=int(risk),
                events=int(events),
            )
        )
    return dict(
        group=label,
        curve=curve,
        risk_table=risk_table(t, event, entry, times),
        events=int(event.sum()),
        censored=int(np.sum(event == 0)),
        initial_survival=1.0,
        ci="Greenwood log-log pointwise CI; boundary0/1 undefined",
        median=next((v["time"] for v in curve if v["survival"] <= 0.5), None),
        time_support=[float(t.min()), float(t.max())],
    )


def concordance(t, event, risk, control):
    """Harrell comparable-pair estimator, no IPCW or held-out-performance claim."""
    comparable = concordant = discordant = tied = 0
    for i in range(len(t)):
        control.check()
        if not event[i]:
            continue
        later = (t > t[i]) | ((t == t[i]) & (event == 0))
        diff = risk[i] - risk[later]
        comparable += len(diff)
        tied += int(np.sum(np.abs(diff) <= 1e-8))
        concordant += int(np.sum(diff > 1e-8))
        discordant += int(np.sum(diff < -1e-8))
    return dict(
        value=(concordant + 0.5 * tied) / comparable if comparable else None,
        comparable=comparable,
        concordant=concordant,
        discordant=discordant,
        tied_risk=tied,
        tied_tol=1e-8,
        method="Harrell right-censored comparable pairs; event/censor same-time comparable, two tied events excluded",
        scope="Apparent training discrimination, not held-out validation; censoring-distribution sensitive, not IPCW; no CI",
    )


def aft_objective(theta, design, time, event, control):
    control.check()
    beta = theta[:-1]
    sigma = math.exp(theta[-1])
    z = (np.log(time) - design @ beta) / sigma
    logsf = special.log_ndtr(-z)
    mills = np.exp(-0.5 * z * z - 0.5 * math.log(2 * math.pi) - logsf)
    observed = event.astype(bool)
    ll = np.where(
        observed,
        -np.log(time) - math.log(sigma) - 0.5 * z * z - 0.5 * math.log(2 * math.pi),
        logsf,
    )
    gmu = np.where(observed, z / sigma, mills / sigma)
    gs = np.where(observed, z * z - 1, mills * z)
    return -float(ll.sum()), -np.r_[design.T @ gmu, gs.sum()]


def fit_aft(t, event, x, spec, control):
    design = np.column_stack((np.ones(len(t)), x))
    if np.linalg.matrix_rank(design) < design.shape[1]:
        raise ProjectError("AFT predictor tasarımı rank deficient.")
    initial = np.linalg.lstsq(design, np.log(t), rcond=None)[0]
    sigma = max(float(np.std(np.log(t) - design @ initial)), 0.1)
    start = np.r_[initial, math.log(sigma)]
    solution = optimize.minimize(
        aft_objective,
        start,
        args=(design, t, event, control),
        jac=True,
        method="L-BFGS-B",
        bounds=[(None, None)] * len(initial) + [(-8, 8)],
        options=dict(maxiter=spec.max_iterations, ftol=1e-12, gtol=1e-7),
    )
    if (
        not solution.success
        or np.max(np.abs(solution.jac)) > 1e-3
        or abs(solution.x[-1]) > 7.99
    ):
        raise ProjectError(
            "AFT convergence/boundary/separation sorunu; model/prediction kapalı."
        )
    # Central differences of analytic score, observed information, not L-BFGS inverse approximation.
    hessian = np.column_stack(
        [
            (
                aft_objective(
                    solution.x + np.eye(len(start))[j] * 1e-4, design, t, event, control
                )[1]
                - aft_objective(
                    solution.x - np.eye(len(start))[j] * 1e-4, design, t, event, control
                )[1]
            )
            / (2e-4)
            for j in range(len(start))
        ]
    )
    hessian = (hessian + hessian.T) / 2
    if (
        not np.isfinite(hessian).all()
        or np.linalg.eigvalsh(hessian).min() <= 1e-8
        or np.linalg.cond(hessian) > 1e10
    ):
        raise ProjectError(
            "AFT observed information singular; separation/CI doğrulanamadı."
        )
    covariance = np.linalg.inv(hessian)
    if np.max(np.abs(solution.x[:-1])) > 30 or not np.isfinite(covariance).all():
        raise ProjectError(
            "AFT extreme katsayı/nonfinite covariance; separation kontrolü başarısız."
        )
    return dict(
        kind="lognormal_aft",
        beta=solution.x[:-1].tolist(),
        sigma=math.exp(solution.x[-1]),
        covariance=covariance.tolist(),
        log_likelihood=-float(solution.fun),
        iterations=int(solution.nit),
        score_max=float(np.max(np.abs(solution.jac))),
        inference="Observed information Wald CI; conditional log-normal duration model, not PH/HR",
    ), -design @ solution.x[:-1]


def fit_cox(t, event, entry, groups, x, spec, control):
    if np.linalg.matrix_rank(x) < x.shape[1] or any(
        np.std(x[:, j]) < 1e-12 for j in range(x.shape[1])
    ):
        raise ProjectError(
            "Cox predictors full rank ve değişken olmalı; intercept/constant eklemeyin."
        )
    for group in np.unique(groups):
        if np.sum(event[groups == group]) < max(5, 2 * x.shape[1]):
            raise ProjectError(
                "Cox strata event azlığı; her stratada en az5/2×predictor event gerekli."
            )
    model = PHReg(
        t,
        x,
        status=event,
        entry=entry,
        strata=groups if spec.group else None,
        ties=spec.survival_plan["ties"],
        missing="raise",
    )
    with warnings.catch_warnings(record=True) as messages:
        warnings.simplefilter("always")
        fitted = model.fit(
            disp=False,
            maxiter=spec.max_iterations,
            callback=lambda theta: control.check(),
        )
    control.check()
    beta = np.asarray(fitted.params)
    cov = np.asarray(fitted.cov_params())
    info = -model.hessian(beta)
    score = float(np.max(np.abs(model.score(beta))))
    if (
        messages
        or not np.isfinite(beta).all()
        or not np.isfinite(cov).all()
        or score > 1e-3
        or np.linalg.eigvalsh(info).min() <= 1e-8
        or np.linalg.cond(info) > 1e10
        or np.max(np.abs(beta)) > 20
    ):
        raise ProjectError(
            "Cox separation/nonconvergence/ill-conditioned bilgi; inference/prediction kapalı."
        )
    lp = x @ beta
    baselines = []
    residuals = []
    for group in np.unique(groups):
        mask = groups == group
        tg = t[mask]
        eg = event[mask]
        xg = x[mask]
        lpg = lp[mask]
        en = entry[mask] if entry is not None else None
        event_times = np.unique(tg[eg == 1])
        cumulative = 0.0
        curve = []
        for time in event_times:
            control.check()
            risk = (tg >= time) & (en <= time if en is not None else True)
            failures = (tg == time) & (eg == 1)
            d = int(failures.sum())
            w = np.exp(lpg[risk])
            denominator = float(w.sum())
            cumulative += d / denominator
            curve.append(
                dict(
                    time=float(time),
                    cumulative_hazard=cumulative,
                    risk=int(risk.sum()),
                    events=d,
                )
            )
            # Breslow-weighted residuals are descriptive under Efron tied fit; never a formal PH p-test.
            mean = np.sum(xg[risk] * w[:, None], axis=0) / denominator
            for index in np.flatnonzero(failures):
                residuals.append(
                    dict(
                        time=float(time),
                        group=str(group),
                        values=(xg[index] - mean).tolist(),
                    )
                )
        baselines.append(dict(group=str(group), curve=curve))
    trend = []
    times = np.array([r["time"] for r in residuals])
    values = np.array([r["values"] for r in residuals])
    for j in range(x.shape[1]):
        rho = None
        if len(np.unique(times)) >= 3 and np.std(values[:, j]) > 1e-12:
            rho = float(stats.spearmanr(np.log(times), values[:, j]).statistic)
        trend.append(
            dict(
                column_id=spec.features[j],
                spearman_logtime=rho,
                large_trend_flag=rho is not None and abs(rho) > 0.3,
            )
        )
    diagnostic = dict(
        method="Descriptive Schoenfeld residual trend; Breslow risk-weighted means, Efron ties approximation explicitly labelled",
        trend=trend,
        residuals=residuals,
        formal_ph_test=False,
        interpretation="Trend plot/flag is screening, no calibrated PH p-test. No trend does not establish PH; crossing/non-PH requires another model.",
        status="ph_screen_warning"
        if any(v["large_trend_flag"] for v in trend)
        else "ph_not_established",
    )
    return dict(
        kind="cox",
        beta=beta.tolist(),
        covariance=cov.tolist(),
        log_likelihood=float(model.loglike(beta)),
        score_max=score,
        baselines=baselines,
        baseline_method="Breslow cumulative increments including current event; coefficients ties="
        + spec.survival_plan["ties"],
        ph_diagnostics=diagnostic,
        inference="Partial likelihood Wald HR CI, not event probability",
    ), lp


def validate_model(model):
    """Safe numbers only, bounded schema; never import/execute serialized models."""
    if (
        not isinstance(model, dict)
        or model.get("schema") != "SurvivalModel/v1"
        or model.get("kind") not in ("cox", "lognormal_aft")
    ):
        raise ProjectError("Safe sağkalım model şeması desteklenmiyor.")
    from veri_ufku.statistics.survival_contracts import TIME_UNITS

    required = {
        "schema",
        "kind",
        "beta",
        "covariance",
        "log_likelihood",
        "score_max",
        "inference",
        "features",
        "unit",
        "censoring",
        "training_support",
        "predictor_ranges",
        "prediction_allowed",
        "prediction_limit",
    }
    required |= (
        {"sigma", "iterations"}
        if model["kind"] == "lognormal_aft"
        else {"baselines", "baseline_method", "ph_diagnostics"}
    )
    if (
        set(model) != required
        or model.get("unit") not in TIME_UNITS
        or model.get("censoring") not in ("right", "left_truncated_right")
    ):
        raise ProjectError("Safe model tam alan/timeunit/censoring şeması geçersiz.")
    allowed = {
        "schema",
        "kind",
        "beta",
        "sigma",
        "covariance",
        "log_likelihood",
        "iterations",
        "score_max",
        "inference",
        "baselines",
        "baseline_method",
        "ph_diagnostics",
        "features",
        "unit",
        "censoring",
        "training_support",
        "predictor_ranges",
        "prediction_allowed",
        "prediction_limit",
    }
    if (
        not set(model) <= allowed
        or not isinstance(model.get("features"), list)
        or not 1 <= len(model["features"]) <= 5
        or any(not isinstance(c, str) for c in model["features"])
    ):
        raise ProjectError("Model alanları/predictor şeması geçersiz.")
    beta = model.get("beta")
    expected = len(model["features"]) + (model["kind"] == "lognormal_aft")
    if (
        not isinstance(beta, list)
        or len(beta) != expected
        or any(not finite_number(v) or abs(v) > 30 for v in beta)
    ):
        raise ProjectError("Safe model katsayıları geçersiz.")

    def numbers(v):
        if isinstance(v, dict):
            return all(numbers(x) for x in v.values())
        if isinstance(v, list):
            return all(numbers(x) for x in v)
        return (
            v is None
            or type(v) in (str, bool, int, float)
            and (not isinstance(v, float) or math.isfinite(v))
        )

    if not numbers(model) or type(model.get("prediction_allowed")) is not bool:
        raise ProjectError("Safe model sonlu JSON değerleri gerekli.")
    dimension = len(beta) + (model["kind"] == "lognormal_aft")
    covariance = model.get("covariance")
    if (
        not isinstance(covariance, list)
        or len(covariance) != dimension
        or any(
            not isinstance(row, list)
            or len(row) != dimension
            or any(not finite_number(v) for v in row)
            for row in covariance
        )
    ):
        raise ProjectError("Safe model covariance şeması geçersiz.")
    if (
        not finite_number(model["log_likelihood"])
        or not finite_number(model["score_max"])
        or not isinstance(model["inference"], str)
        or not isinstance(model["prediction_limit"], str)
    ):
        raise ProjectError("Safe model likelihood/score/metadata geçersiz.")
    support = model.get("training_support")
    if (
        not isinstance(support, list)
        or len(support) != 2
        or not all(finite_number(v) for v in support)
        or not 0 < support[0] <= support[1]
    ):
        raise ProjectError("Model prediction destek aralığı geçersiz.")
    if model["kind"] == "lognormal_aft":
        if not finite_number(model.get("sigma")) or not 0 < model["sigma"] <= math.exp(
            8
        ):
            raise ProjectError("AFT scale geçersiz.")
    else:
        baselines = model.get("baselines")
        if not isinstance(baselines, list) or not 1 <= len(baselines) <= 8:
            raise ProjectError("Cox baseline şeması geçersiz.")
        if len({b.get("group") for b in baselines if isinstance(b, dict)}) != len(
            baselines
        ):
            raise ProjectError("Cox baseline grup kimliği yineleniyor/geçersiz.")
        for b in baselines:
            if (
                not isinstance(b, dict)
                or set(b) != {"group", "curve"}
                or not isinstance(b["group"], str)
                or not isinstance(b["curve"], list)
                or not 1 <= len(b["curve"]) <= 2000
            ):
                raise ProjectError("Cox baseline grup/eğri geçersiz.")
            previous = 0.0
            hazard = 0.0
            for c in b["curve"]:
                if (
                    not isinstance(c, dict)
                    or set(c) != {"time", "cumulative_hazard", "risk", "events"}
                    or not finite_number(c["time"])
                    or not previous < c["time"] <= support[1]
                    or not finite_number(c["cumulative_hazard"])
                    or c["cumulative_hazard"] < hazard
                ):
                    raise ProjectError("Cox baseline zaman/hazard artışı geçersiz.")
                previous = c["time"]
                hazard = c["cumulative_hazard"]


def predict(model, profile, times, group=""):
    validate_model(model)
    if not model["prediction_allowed"]:
        raise ProjectError(model["prediction_limit"])
    if (
        not isinstance(profile, list)
        or len(profile) != len(model["features"])
        or any(not finite_number(v) or abs(v) > 1e12 for v in profile)
    ):
        raise ProjectError("Prediction profili model predictor sırasıyla uyuşmuyor.")
    if (
        not isinstance(times, list)
        or not 1 <= len(times) <= 12
        or any(
            not finite_number(t) or t < 0 or t > model["training_support"][1]
            for t in times
        )
        or sorted(set(times)) != times
    ):
        raise ProjectError(
            "Prediction1–12artan zaman ve takip desteği içinde olmalı; extrapolation kapalı."
        )
    ranges = model.get("predictor_ranges")
    if (
        not isinstance(ranges, list)
        or len(ranges) != len(profile)
        or any(
            not isinstance(r, list)
            or len(r) != 2
            or not all(finite_number(v) for v in r)
            or r[0] > r[1]
            for r in ranges
        )
    ):
        raise ProjectError("Safe model predictor aralığı geçersiz.")
    if any(not a <= v <= b for v, (a, b) in zip(profile, ranges)):
        raise ProjectError(
            "Prediction profili eğitim predictor desteği dışında; extrapolation kapalı."
        )
    answer = []
    if model["kind"] == "cox":
        curves = model["baselines"]
        selected = next((c for c in curves if c["group"] == (group or "all")), None)
        if selected is None:
            raise ProjectError("Prediction strata mevcut model grubuyla aynı olmalı.")
        lp = float(np.dot(profile, model["beta"]))
        if abs(lp) > 50:
            raise ProjectError("Prediction extreme log-hazard extrapolation reddi.")
        for time in times:
            h = next(
                (
                    c["cumulative_hazard"]
                    for c in reversed(selected["curve"])
                    if c["time"] <= time
                ),
                0.0,
            )
            answer.append(dict(time=time, survival=math.exp(-h * math.exp(lp))))
    else:
        mu = float(np.dot([1, *profile], model["beta"]))
        for time in times:
            answer.append(
                dict(
                    time=time,
                    survival=1.0
                    if time == 0
                    else float(special.ndtr(-(math.log(time) - mu) / model["sigma"])),
                )
            )
    return dict(
        profile=profile,
        feature_order=model["features"],
        unit=model["unit"],
        group=group,
        curve=answer,
        interpretation="Conditional fitted survival S(t|baseline profile); not HR, causal effect or validated individual prognosis; no prediction CI",
        training_support=model["training_support"],
    )


def analyze(frame, spec, control):
    t, event, entry, groups, x = arrays(frame, spec)
    p = spec.survival_plan
    curves = []
    risk = []
    warnings_list = [CAUTION]
    for label in sorted(np.unique(groups)):
        m = groups == label
        risk.append(
            dict(
                group=str(label),
                rows=int(m.sum()),
                risk_table=risk_table(
                    t[m],
                    event[m],
                    entry[m] if entry is not None else None,
                    p["risk_times"],
                    spec.method == "survival_cox",
                ),
            )
        )
        if spec.method in ("survival_km", "survival_logrank"):
            curves.append(
                km(
                    t[m],
                    event[m],
                    entry[m] if entry is not None else None,
                    str(label),
                    p["risk_times"],
                    spec.confidence,
                )
            )
    result = dict(
        curves=curves,
        risk_tables=risk,
        logrank=None,
        model=None,
        prediction=None,
        coefficients=[],
        diagnostics={},
        metrics=dict(
            c_index=None,
            time_dependent_brier=dict(
                available=False,
                reason="Validated IPCW train/evaluation censoring distribution and supported follow-up protocol not implemented; ordinary MSE is not survival Brier.",
            ),
            time_dependent_auc=dict(
                available=False,
                reason="Validated censoring-aware evaluation backend not implemented.",
            ),
        ),
        events=int(np.sum(event > 0)),
        censored=int(np.sum(event == 0)),
        warnings=warnings_list,
        status="descriptive",
    )
    if not result["events"]:
        warnings_list.append(
            "Event yok: KM1, median/CI tanımlanamaz; takip sonrası survival bilinmez."
        )
    if spec.method == "survival_logrank":
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                chi, pv = survdiff(t, event, groups, entry=entry)
            except (ValueError, np.linalg.LinAlgError):
                chi = pv = None
        if chi is None or not math.isfinite(chi) or not math.isfinite(pv):
            result["status"] = "inference_unavailable"
            warnings_list.append(
                "Log-rank event/risk-set variance yetersiz; test sunulmuyor."
            )
        else:
            result["logrank"] = dict(
                statistic=float(chi),
                p_value=float(pv),
                df=len(np.unique(groups)) - 1,
                method="Unweighted log-rank, independent right-censoring; asymptotic chi-square",
                limitations="Survival-distribution comparison, not effect/HR; crossing curves can lose power.",
            )
        if (
            result["events"] < 20
            or any(np.sum(event[groups == g]) < 5 for g in np.unique(groups))
            or caught
        ):
            warnings_list.append(
                "Log-rank az event/grup dengesizliği: asimptotik p yorumunu sınırlayın; uyarılar görünür."
            )
    elif spec.method == "survival_cif":
        for label in sorted(np.unique(groups)):
            m = groups == label
            if set(event[m][event[m] > 0]) != set(range(1, len(p["cause_labels"]) + 1)):
                raise ProjectError(
                    "CIF her grupta tüm seçili cause kodlarının en az1event örneğini ister."
                )
            backend = CumIncidenceRight(t[m], event[m])
            for cause, values in enumerate(backend.cinc, 1):
                curves.append(
                    dict(
                        group=str(label),
                        cause=cause,
                        cause_label=p["cause_labels"][str(cause)],
                        curve=[
                            dict(time=float(a), incidence=float(b))
                            for a, b in zip(backend.times, values)
                        ],
                        inference="Nonparametric cause-specific cumulative incidence; CI not implemented",
                        time_support=[float(t[m].min()), float(t[m].max())],
                    )
                )
        result["interpretation"] = (
            "CIF P(T<=t,J=cause); competing events remain risk exits, not relabelled censoring. Sum CIF<=1;1-KM is not cause incidence."
        )
    elif spec.method in MODELS:
        required = max(20, 10 * (x.shape[1] + (spec.method == "survival_aft")))
        result["diagnostics"].update(
            minimum_events=required,
            observed_events=result["events"],
            ties=p["ties"]
            if spec.method == "survival_cox"
            else "Exact duration density/right-censored likelihood",
            tied_event_times=int(result["events"] - len(np.unique(t[event == 1]))),
        )
        try:
            if result["events"] < required:
                raise ProjectError(
                    "Event azlığı: model için en az20/10×parametre observed event gerekli."
                )
            model, score = (
                fit_cox(t, event, entry, groups, x, spec, control)
                if spec.method == "survival_cox"
                else fit_aft(t, event, x, spec, control)
            )
        except (ProjectError, np.linalg.LinAlgError) as exc:
            result["status"] = "model_diagnostic_fail"
            result["diagnostics"]["failure"] = (
                str(exc)
                if isinstance(exc, ProjectError)
                else "Singular model information"
            )
            warnings_list.append(
                "Model tanısı başarısız; katsayı/CI/prediction/persisted model sunulmuyor."
            )
        else:
            model.update(
                schema="SurvivalModel/v1",
                features=spec.features,
                unit=spec.unit,
                censoring=p["censoring"],
                predictor_ranges=[
                    [float(x[:, j].min()), float(x[:, j].max())]
                    for j in range(x.shape[1])
                ],
                training_support=[float(t.min()), float(t.max())],
                prediction_allowed=entry is None,
                prediction_limit="Delayed-entry model origin survival prediction not validated; conditional-on-entry prediction backend required.",
            )
            if spec.method == "survival_cox":
                result["diagnostics"]["ph"] = model["ph_diagnostics"]
                if any(v["large_trend_flag"] for v in model["ph_diagnostics"]["trend"]):
                    model["prediction_allowed"] = False
                    model["prediction_limit"] = (
                        "PH residual trend screening warning; constant-HR survival prediction kapalı. PH tanısı formal test veya doğruluk kanıtı değil."
                    )
                    warnings_list.append(model["prediction_limit"])
                else:
                    warnings_list.append(
                        "PH not established: descriptive residual screening only, no calibrated PH p-test."
                    )
            result["model"] = model
            result["status"] = "fitted_conditional"
            z = float(stats.norm.ppf((1 + spec.confidence) / 2))
            for j, b in enumerate(model["beta"]):
                se = math.sqrt(model["covariance"][j][j])
                interval = [b - z * se, b + z * se]
                result["coefficients"].append(
                    dict(
                        parameter="intercept"
                        if spec.method == "survival_aft" and j == 0
                        else spec.features[j - (spec.method == "survival_aft")],
                        beta=b,
                        se=se,
                        interval=interval,
                        ratio=math.exp(b),
                        ratio_interval=[
                            math.exp(v) if abs(v) < 700 else None for v in interval
                        ],
                        ratio_meaning="hazard ratio, not event probability"
                        if spec.method == "survival_cox"
                        else "time ratio conditional quantiles, not HR/event probability",
                        confidence=spec.confidence,
                    )
                )
            if entry is None and not spec.group:
                result["metrics"]["c_index"] = concordance(t, event, score, control)
            else:
                result["metrics"]["c_index"] = dict(
                    value=None,
                    reason="Delayed entry/strata pooled comparability metric not validated; disabled.",
                )
            try:
                result["prediction"] = predict(
                    model,
                    p["prediction_profile"],
                    p["prediction_times"],
                    p["prediction_group"],
                )
            except ProjectError as exc:
                warnings_list.append("Prediction kapalı: " + str(exc))
    control.check()
    return result


def plot(payload, spec, path):
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    fig, (ax, detail) = plt.subplots(
        2,
        1,
        figsize=(10, 9),
        layout="constrained",
        gridspec_kw={"height_ratios": [3, 2]},
    )
    if payload["curves"]:
        for c in payload["curves"]:
            key = "incidence" if spec.method == "survival_cif" else "survival"
            times = [0.0] + [v["time"] for v in c["curve"]]
            values = [0.0 if key == "incidence" else 1.0] + [v[key] for v in c["curve"]]
            # Empirical step remains constant through observed follow-up only;
            # all-censored cohorts still have a visible [0,max followup] curve.
            if c["time_support"][1] > times[-1]:
                times.append(c["time_support"][1])
                values.append(values[-1])
            ax.step(
                times,
                values,
                where="post",
                label=c["group"]
                + (" · " + c["cause_label"] if key == "incidence" else ""),
            )
        ax.legend()
    elif payload["prediction"]:
        curve = payload["prediction"]["curve"]
        model = payload["model"]
        horizon = max(v["time"] for v in curve)
        if model["kind"] == "cox":
            group = payload["prediction"]["group"] or "all"
            baseline = next(b for b in model["baselines"] if b["group"] == group)
            points = [c for c in baseline["curve"] if c["time"] <= horizon]
            rate = math.exp(
                float(np.dot(payload["prediction"]["profile"], model["beta"]))
            )
            times = [0.0] + [v["time"] for v in points]
            values = [1.0] + [math.exp(-v["cumulative_hazard"] * rate) for v in points]
            if times[-1] < horizon:
                times.append(horizon)
                values.append(values[-1])
            ax.step(
                times,
                values,
                where="post",
                label="Cox baseline steps · selected profile/horizon · no prediction CI",
            )
        else:
            times = np.linspace(0, horizon, 250)
            mu = float(np.dot([1, *payload["prediction"]["profile"]], model["beta"]))
            values = np.ones(len(times))
            positive = times > 0
            values[positive] = special.ndtr(
                -(np.log(times[positive]) - mu) / model["sigma"]
            )
            ax.plot(
                times,
                values,
                label="Log-normal AFT · selected profile/horizon · no prediction CI",
            )
        ax.scatter(
            [v["time"] for v in curve],
            [v["survival"] for v in curve],
            s=24,
            label="explicit prediction query times",
        )
        ax.legend()
    else:
        ax.text(
            0.5,
            0.5,
            "Model/prediction unavailable\nSee saved diagnostics",
            ha="center",
            transform=ax.transAxes,
        )
    ax.set(
        xlabel="Duration (" + spec.unit + ")",
        ylabel="Cumulative incidence"
        if spec.method == "survival_cif"
        else "Survival probability",
        ylim=(-0.02, 1.02),
        title=spec.method
        + " · n="
        + str(payload["events"] + payload["censored"])
        + " · events="
        + str(payload["events"]),
    )
    ax.text(
        0,
        -0.22,
        "Right censoring · independent censoring assumed · HR ≠ event probability\nRisk table, time origin, exclusions and diagnostic limitations in companion JSON/Parquet.",
        transform=ax.transAxes,
        fontsize=9,
    )
    if payload["diagnostics"].get("ph"):
        ph = payload["diagnostics"]["ph"]
        for j, c in enumerate(spec.features):
            detail.scatter(
                [r["time"] for r in ph["residuals"]],
                [r["values"][j] for r in ph["residuals"]],
                s=8,
                alpha=0.5,
                label="baseline predictor" + str(j + 1),
            )
        detail.axhline(0, color="grey", lw=1)
        detail.set_xscale("log")
        detail.set(
            xlabel="Event duration (log scale)",
            ylabel="Schoenfeld residual (Breslow means)",
            title="Descriptive PH screening; Efron ties approximate; no calibrated PH p-test",
        )
        detail.legend()
    else:
        detail.axis("off")
        rows = []
        for block in payload["risk_tables"]:
            for row in block["risk_table"]:
                rows.append(
                    [
                        block["group"],
                        row["time"],
                        row["at_risk"],
                        row["events_at_time"],
                        row["censored_at_time"],
                    ]
                )
        # Limit visual density; all values remain in JSON and QML risk table.
        table = detail.table(
            cellText=rows[:24],
            colLabels=["group", "time", "at risk", "event at t", "censor at t"],
            loc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.25)
        detail.set_title(
            "Risk table (first24rows); full table in companion JSON"
            if len(rows) > 24
            else "Risk table; censoring at tied event follows event"
        )
    fig.savefig(path, dpi=150)
    plt.close(fig)


def calculate(request, spec, workspace, control, preflight=False):
    spec.validate(request["columns"], run=not preflight)
    checked(request, control)
    frame = load(request, spec, control)
    payload = analyze(frame, spec, control)
    common = dict(
        survival=True,
        method=spec.method,
        method_label=SURVIVAL_LABELS[spec.method],
        n=dict(population=frame.height, units=frame[spec.key].n_unique()),
        used_rows=frame.height,
        excluded_rows={},
        warnings=payload["warnings"],
        plan=spec.survival_plan,
        survival_analysis=payload,
        budget=dict(
            rows=frame.height,
            predictors=len(spec.features),
            estimated_working_bytes=frame.height * 8192,
            ram_limit=control.budget.ram_bytes,
            model_rows_limit=2000,
            descriptive_rows_limit=10000,
        ),
    )
    if preflight:
        return dict(
            common,
            spec=spec.data(),
            dataset_version=request["version_id"],
            config_revision=request.get("config_revision", 0),
        )
    result = dict(
        common,
        primary=dict(
            method=spec.method,
            p_value=payload["logrank"]["p_value"] if payload["logrank"] else None,
            statistic=payload["logrank"]["statistic"] if payload["logrank"] else None,
            effect=None,
        ),
        spec=spec.data(),
        comparisons=[],
        correction=dict(
            method="none",
            family="one declared survival question; PH screening descriptive",
            family_size=1,
            ci_adjusted=False,
        ),
        dataset_version=request["version_id"],
        config_revision=request.get("config_revision", 0),
        result_version="analysis:" + uid(),
        method_version=1,
        parameter_version=1,
        provenance=dict(
            schema="AnalysisResult/v1",
            backend="statsmodels KM/logrank/Cox/CIF; scipy censored lognormal AFT analytic-score MLE",
            numpy_version=np.__version__,
            scipy_version=scipy.__version__,
            statsmodels_version=statsmodels.__version__,
            semantic_units={
                c: request.get("semantic_metadata", {}).get(c, {}).get("unit", "")
                for c in [spec.x, spec.survival_plan["entry"]]
                if c
            },
            snapshot_fingerprint=request["fingerprint"],
            snapshot_uri=request["snapshot_uri"],
            source_snapshot_id=request["source_snapshot_id"],
            help_content_version=61,
            seed=spec.seed,
        ),
    )
    checked(request, control)
    directory = Path(workspace)
    paths = dict(
        result=str(directory / "survival-result.json"),
        members=str(directory / "survival-members.parquet"),
        details=str(directory / "survival-details.parquet"),
        diagnostic_png=str(directory / "survival.png"),
    )
    frame.select(pl.col("__vu_row_id").alias("row_id")).write_parquet(paths["members"])
    frame.rename({"__vu_row_id": "row_id"}).write_parquet(paths["details"])
    plot(payload, spec, paths["diagnostic_png"])
    control.check()
    Path(paths["result"]).write_text(
        json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )
    result["paths"] = paths
    result["fingerprints"] = {
        k: hash_artifact(Path(v), control) for k, v in paths.items()
    }
    control.disk(directory)
    control.check()
    return result


def verify_source(path, columns, result, details, members, semantic_metadata=None):
    from veri_ufku.statistics.contracts import AnalysisSpec

    spec = AnalysisSpec.from_dict(result["spec"])
    spec.validate(columns, run=True)
    control = Control()
    metadata = semantic_metadata or {}
    expected_units = {
        c: metadata.get(c, {}).get("unit", "")
        for c in [spec.x, spec.survival_plan["entry"]]
        if c
    }
    if expected_units != result["provenance"]["semantic_units"]:
        raise ProjectError(
            "Sağkalım metadata zaman birimi source/version bağı değişmiş."
        )
    frame = load(
        dict(path=str(path), columns=columns, semantic_metadata=metadata), spec, control
    )
    if not frame.rename({"__vu_row_id": "row_id"}).equals(details) or not frame.select(
        pl.col("__vu_row_id").alias("row_id")
    ).equals(members):
        raise ProjectError("Sağkalım source/RowId/SourceRecordId detay bağı değişmiş.")
    expected = analyze(frame, spec, control)
    if expected != result["survival_analysis"]:
        raise ProjectError(
            "Sağkalım risk/curve/model/censoring hesabı immutable source ile uyuşmuyor."
        )
