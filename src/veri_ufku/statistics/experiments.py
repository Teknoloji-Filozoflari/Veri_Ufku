"""Bounded, declared randomization plans; no contact or real-world assignment."""

import json
import math
from pathlib import Path

import numpy as np
import polars as pl
import scipy
import statsmodels
from scipy import stats
from statsmodels.stats.power import NormalIndPower, TTestIndPower
from statsmodels.stats.proportion import proportion_effectsize

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import checked, filtered
from veri_ufku.importers.delimited import hash_artifact
from veri_ufku.statistics.experiment_contracts import EXPERIMENT_LABELS
from veri_ufku.storage.project_model import ProjectError, uid

CAUTION = "Randomize tasarım kullanıcı beyanıdır, uygulama kanıtı doğrulamaz. Sabit ufuk testi tekrar bakmayla sequential olmaz. Eksik ölçüm, SRM veya PP randomizasyonun nedensel ITT yorumunu bozabilir; p-değeri nedensellik kanıtı değildir."


def power_plan(p):
    ratio = p["allocation"] / (1 - p["allocation"])
    binary = p["metric"] == "proportion"
    effect = (
        abs(
            float(
                proportion_effectsize(
                    p["baseline_value"] + p["mde"], p["baseline_value"]
                )
            )
        )
        if binary
        else abs(p["mde"]) / p["sd"]
    )
    backend = NormalIndPower() if binary else TTestIndPower()
    raw = float(
        backend.solve_power(
            effect_size=effect,
            alpha=p["alpha"],
            power=p["power"],
            ratio=ratio,
            alternative="two-sided",
        )
    )
    if not math.isfinite(raw) or raw < 2 or raw > 1e8:
        raise ProjectError(
            "Örneklem çözümü sonlu veya uygulama plan bütçesi içinde değil."
        )
    na, nb = math.ceil(raw), math.ceil(raw * ratio)
    if min(na, nb) < 2:
        raise ProjectError("Her kol en az2 planlanan birim ister.")
    achieved = float(
        backend.power(
            effect_size=effect,
            nobs1=na,
            alpha=p["alpha"],
            ratio=nb / na,
            alternative="two-sided",
        )
    )
    if not math.isfinite(achieved) or achieved < p["power"] - 1e-6:
        raise ProjectError("Yuvarlanan örneklem güç çözümü doğrulanamadı.")
    return dict(
        assumptions=p,
        standardized_effect=effect,
        effect_scale="Cohen h: arcsine proportions"
        if binary
        else "Cohen d: common planning SD",
        continuous_n_control=raw,
        analyzable_control=na,
        analyzable_treatment=nb,
        recruit_control=math.ceil(na / (1 - p["expected_attrition"])),
        recruit_treatment=math.ceil(nb / (1 - p["expected_attrition"])),
        rounded_design_power=achieved,
        design_effect=1,
        method="NormalIndPower arcsine normal approximation"
        if binary
        else "TTestIndPower pooled common-SD noncentral t",
        limitations="A priori design power, not observed power. Missing recruitment inflation does not correct attrition bias. Independent units; paired/cluster/factorial not supported.",
    )


def load(request, spec, control):
    q, schema, names = filtered(request, ViewSpec())
    n = q.select(pl.len()).collect(engine="streaming").item()
    if not n or n > 100000 or n * 2048 > control.budget.ram_bytes // 2:
        raise ProjectError("Deney tam rosterı boş veya100000 kayıt/RAM bütçesi aşıldı.")
    p = spec.experiment_plan
    columns = list(
        dict.fromkeys(
            [
                c
                for c in [
                    spec.key,
                    spec.x,
                    spec.group,
                    p["protocol_column"],
                    *p["baseline_columns"],
                    *[g["column_id"] for g in p["guardrails"]],
                ]
                if c
            ]
        )
    )
    for c in columns:
        d = schema[names[c]]
        if (
            d.is_nested()
            or d.is_temporal()
            or d == pl.Binary
            or isinstance(d, pl.Decimal)
        ):
            raise ProjectError(
                "Deney alanları skaler sayı/kimlik olmalı; decimal/nested/tarih/binary sessiz dönüştürülmez."
            )
        if (
            d.is_integer()
            and q.select(pl.col(names[c]).abs().max()).collect().item() > 2**53
        ):
            raise ProjectError(
                "Float64 için kayıpsız olmayan büyük integer reddedildi."
            )
    frame = q.select(
        "__vu_row_id", *[pl.col(names[c]).alias(c) for c in columns]
    ).collect(engine="streaming")
    for c in (spec.key, spec.group):
        if not c:
            continue
        vals = frame[c].to_list()
        if any(
            v is None
            or isinstance(v, float)
            and not math.isfinite(v)
            or not str(v).strip()
            for v in vals
        ):
            raise ProjectError(
                "Randomizasyon birimi/assigned arm eksik veya sonlu değil."
            )
    ids = list(map(str, frame[spec.key].to_list()))
    if len(set(ids)) != n:
        raise ProjectError(
            "Bir randomizasyon/analiz birimi bir satır olmalı; tekrar/cluster satırlarını bağımsız saymayın."
        )
    if any(len(i) > 500 for i in ids):
        raise ProjectError("Birim kimliği500 karakter sınırını aşıyor.")
    for c in [
        v
        for v in [
            spec.x,
            p["protocol_column"],
            *p["baseline_columns"],
            *[g["column_id"] for g in p["guardrails"]],
        ]
        if v
    ]:
        binary_roles = (
            ([spec.x] if spec.method == "experiment_proportion" else [])
            + [g["column_id"] for g in p["guardrails"] if g["metric"] == "proportion"]
            + [p["protocol_column"]]
        )
        if not schema[names[c]].is_numeric() and not (
            c in binary_roles and schema[names[c]] == pl.Boolean
        ):
            raise ProjectError(
                "Outcome, baseline, guardrail ve protocol fiziksel sayı olmalı."
            )
        vals = frame[c].to_list()
        if any(
            v is not None and (not math.isfinite(float(v)) or abs(float(v)) > 1e50)
            for v in vals
        ):
            raise ProjectError(
                "NaN/sonsuz veya1e50 üzeri ölçüm ret; eksik yalnız null ile açık raporlanır."
            )
    if spec.group and set(map(str, frame[spec.group].to_list())) != {
        spec.before,
        spec.after,
    }:
        raise ProjectError(
            "Tam iki assigned arm etiketi gerekli; alınan tedaviyle assigned kolu değiştirmeyin."
        )
    if p["protocol_column"] and any(
        v not in (0, 1) for v in frame[p["protocol_column"]].to_list()
    ):
        raise ProjectError("Protokol uygunluğu eksiksiz0/1 olmalı.")
    binary = [spec.x] if spec.method == "experiment_proportion" else []
    binary += [g["column_id"] for g in p["guardrails"] if g["metric"] == "proportion"]
    for c in binary:
        if any(v is not None and v not in (0, 1) for v in frame[c].to_list()):
            raise ProjectError(
                "Oran metriği kişi başına0/1 event ister; agregat yüzde veya denominator sütunu otomatik tahmin edilmez."
            )
    control.check()
    return frame


def contrast(a, b, metric, alpha):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    na = len(a)
    nb = len(b)
    if min(na, nb) < 2:
        return dict(status="unavailable: her kolda en az2 gözlenen birim", p_value=None)
    ma = float(a.mean())
    mb = float(b.mean())
    delta = mb - ma
    relative = delta / ma if ma != 0 else None
    if relative is not None and not math.isfinite(relative):
        relative = None
    rel_ci = None
    if metric == "proportion":
        ka = int(a.sum())
        kb = int(b.sum())
        ia = stats.binomtest(ka, na).proportion_ci(1 - alpha / 2, method="exact")
        ib = stats.binomtest(kb, nb).proportion_ci(1 - alpha / 2, method="exact")
        ci = [float(ib.low - ia.high), float(ib.high - ia.low)]
        rel_ci = (
            [float(ib.low / ia.high - 1), float(ib.high / ia.low - 1)]
            if ia.low > 0
            else None
        )
        pv = float(stats.fisher_exact([[kb, nb - kb], [ka, na - ka]]).pvalue)
        method = "Fisher two-sided; simultaneous Clopper–Pearson Bonferroni absolute/relative CI (conservative)"
    else:
        va = float(a.var(ddof=1) / na)
        vb = float(b.var(ddof=1) / nb)
        se = math.sqrt(va + vb)
        if not se > 0 or not math.isfinite(se):
            return dict(
                status="unavailable: constant/overflow variance",
                control=ma,
                treatment=mb,
                absolute_effect=delta,
                relative_effect=relative,
                p_value=None,
            )
        df = (va + vb) ** 2 / (va**2 / (na - 1) + vb**2 / (nb - 1))
        ci = [
            delta - float(stats.t.ppf(1 - alpha / 2, df)) * se,
            delta + float(stats.t.ppf(1 - alpha / 2, df)) * se,
        ]
        pv = float(stats.ttest_ind(b, a, equal_var=False).pvalue)
        method = "Welch t; two-sided absolute mean-difference CI"
    if any(not math.isfinite(float(v)) for v in [ma, mb, delta, pv, *ci]):
        raise ProjectError("Etki/CI numeric overflow; sahte sonuç üretilmedi.")
    return dict(
        status="available",
        control=ma,
        treatment=mb,
        control_n=na,
        treatment_n=nb,
        control_events=int(a.sum()) if metric == "proportion" else None,
        treatment_events=int(b.sum()) if metric == "proportion" else None,
        absolute_effect=delta,
        absolute_ci=ci,
        relative_effect=relative,
        relative_ci=rel_ci,
        relative_ci_status="available"
        if rel_ci
        else "unavailable: zero baseline/unbounded ratio or mean ratio CI not supported",
        p_value=pv,
        confidence=1 - alpha,
        method=method,
    )


def experiment(frame, spec):
    p = spec.experiment_plan
    labels = list(map(str, frame[spec.group].to_list()))
    idxa = np.array([v == spec.before for v in labels])
    idxb = ~idxa
    na = int(idxa.sum())
    nb = int(idxb.sum())
    srm_p = float(stats.binomtest(nb, na + nb, p["allocation"]).pvalue)
    srm = dict(
        control=na,
        treatment=nb,
        denominator=na + nb,
        expected_treatment_fraction=p["allocation"],
        p_value=srm_p,
        threshold=0.001,
        flag=srm_p < 0.001,
        method="exact binomial two-sided on full assigned roster; independent Bernoulli allocation only",
    )
    selected = (
        np.ones(frame.height, bool)
        if p["analysis_population"] == "ITT"
        else frame[p["protocol_column"]].to_numpy() == 1
    )
    metric = "proportion" if spec.method == "experiment_proportion" else "mean"
    values = np.array(
        [np.nan if v is None else float(v) for v in frame[spec.x].to_list()]
    )
    valid = np.isfinite(values)
    arms = []
    for name, mask in [(spec.before, idxa), (spec.after, idxb)]:
        pop = mask & selected
        obs = pop & valid
        arms.append(
            dict(
                arm=name,
                assigned=int(mask.sum()),
                population=int(pop.sum()),
                protocol_excluded=int((mask & ~selected).sum()),
                observed=int(obs.sum()),
                missing=int((pop & ~valid).sum()),
                attrition_rate=float((mask & ~valid).sum() / mask.sum()),
                events=int(values[obs].sum()) if metric == "proportion" else None,
            )
        )
    reasons = []
    if srm["flag"]:
        reasons.append(
            "SRM flag: allocation/logging/randomization investigation required"
        )
    if not p["horizon_complete"] or frame.height < p["planned_total"]:
        reasons.append("fixed horizon incomplete")
    if any(a["missing"] for a in arms):
        reasons.append(
            "missing outcomes: observed-case inference is not complete ITT/PP"
        )
    if reasons:
        effect = dict(status="unavailable: " + "; ".join(reasons), p_value=None)
    else:
        effect = contrast(
            values[idxa & selected & valid],
            values[idxb & selected & valid],
            metric,
            p["alpha"],
        )
    missing_bounds = None
    if (
        metric == "proportion"
        and p["analysis_population"] == "ITT"
        and all(a["assigned"] > 0 for a in arms)
    ):
        a, b = arms
        missing_bounds = [
            b["events"] / b["assigned"] - (a["events"] + a["missing"]) / a["assigned"],
            (b["events"] + b["missing"]) / b["assigned"] - a["events"] / a["assigned"],
        ]
    baseline = []
    for c in p["baseline_columns"]:
        v = np.array([np.nan if x is None else float(x) for x in frame[c].to_list()])
        a = v[idxa & np.isfinite(v)]
        b = v[idxb & np.isfinite(v)]
        den = (
            math.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
            if min(len(a), len(b)) > 1
            else 0
        )
        baseline.append(
            dict(
                column_id=c,
                control_n=len(a),
                treatment_n=len(b),
                control_mean=float(a.mean()) if len(a) else None,
                treatment_mean=float(b.mean()) if len(b) else None,
                smd=float((b.mean() - a.mean()) / den) if den > 0 else None,
                interpretation="descriptive pre-treatment balance; no significance-based covariate selection",
            )
        )
    guards = []
    for g in p["guardrails"]:
        v = np.array(
            [np.nan if x is None else float(x) for x in frame[g["column_id"]].to_list()]
        )
        a = v[idxa & selected & np.isfinite(v)]
        b = v[idxb & selected & np.isfinite(v)]
        delta = float(b.mean() - a.mean()) if len(a) and len(b) else None
        harm = (
            delta
            if g["direction"] == "increase"
            else -delta
            if delta is not None
            else None
        )
        guards.append(
            dict(
                plan=g,
                control_n=len(a),
                treatment_n=len(b),
                missing=int((selected & ~np.isfinite(v)).sum()),
                absolute_change=delta,
                descriptive_limit_crossed=harm > g["limit"]
                if harm is not None
                else None,
                interpretation="predeclared descriptive guardrail; no adjusted hypothesis test or automatic experiment success",
            )
        )
    return dict(
        design_label="user-declared randomized two-arm independent experiment",
        randomization_verified=False,
        analysis_population=p["analysis_population"],
        population_interpretation="assignment-based ITT; all outcomes required for inference"
        if p["analysis_population"] == "ITT"
        else "PP selected on protocol; association, not randomized causal ITT effect",
        srm=srm,
        arms=arms,
        attrition_rate_difference=arms[1]["attrition_rate"] - arms[0]["attrition_rate"],
        effect=effect,
        missing_binary_worst_case_effect_bounds=missing_bounds,
        baseline=baseline,
        guardrails=guards,
        sequential_enabled=False,
    )


def calculate(request, spec, workspace, control, preflight=False):
    spec.validate(request["columns"], run=not preflight)
    checked(request, control)
    p = spec.experiment_plan
    frame = None
    payload = {}
    details = pl.DataFrame(
        schema={"row_id": pl.String, "unit_id": pl.String, "arm": pl.String}
    )
    if spec.method.startswith("power_"):
        payload["power_plan"] = power_plan(
            dict(
                p, metric="proportion" if spec.method == "power_proportion" else "mean"
            )
        )
        members = []
    else:
        frame = load(request, spec, control)
        members = frame["__vu_row_id"].to_list()
        if spec.method == "random_assignment":
            ordered = sorted(zip(map(str, frame[spec.key].to_list()), members))
            rng = np.random.default_rng(spec.seed)
            arms = np.where(
                rng.random(len(ordered)) < p["allocation"], spec.after, spec.before
            ).tolist()
            details = pl.DataFrame(
                dict(
                    row_id=[v[1] for v in ordered],
                    unit_id=[v[0] for v in ordered],
                    arm=arms,
                )
            )
            payload["assignment"] = dict(
                status="local draft only; no real participant assigned/contacted",
                scheme="independent Bernoulli",
                seed=spec.seed,
                rng="NumPy Generator PCG64",
                ordering="lexicographic unit ID",
                allocation=p["allocation"],
                control=arms.count(spec.before),
                treatment=arms.count(spec.after),
                units=len(arms),
            )
        else:
            payload["experiment_analysis"] = experiment(frame, spec)
            details = frame.rename({"__vu_row_id": "row_id"})
    common = dict(
        experiment=True,
        method=spec.method,
        method_label=EXPERIMENT_LABELS[spec.method],
        n=dict(population=len(members)),
        used_rows=len(members),
        excluded_rows={},
        warnings=[CAUTION],
        plan=p,
        **payload,
    )
    if preflight:
        return dict(
            common,
            spec=spec.data(),
            dataset_version=request["version_id"],
            config_revision=request.get("config_revision", 0),
        )
    primary_p = payload.get("experiment_analysis", {}).get("effect", {}).get("p_value")
    result = dict(
        common,
        primary=dict(
            method=spec.method, p_value=primary_p, statistic=None, effect=None
        ),
        spec=spec.data(),
        comparisons=[],
        correction=dict(
            method="none",
            family="one predeclared primary metric; guardrails descriptive",
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
            backend="statsmodels power/scipy fixed-horizon adapter",
            numpy_version=np.__version__,
            scipy_version=scipy.__version__,
            statsmodels_version=statsmodels.__version__,
            snapshot_fingerprint=request["fingerprint"],
            snapshot_uri=request["snapshot_uri"],
            source_snapshot_id=request["source_snapshot_id"],
            help_content_version=58,
            seed=spec.seed,
        ),
    )
    checked(request, control)
    directory = Path(workspace)
    membership = directory / "experiment-members.parquet"
    detailpath = directory / "experiment-details.parquet"
    destination = directory / "experiment-result.json"
    pl.DataFrame({"row_id": members}, schema={"row_id": pl.String}).write_parquet(
        membership
    )
    details.write_parquet(detailpath)
    destination.write_text(
        json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )
    result["paths"] = dict(
        result=str(destination), members=str(membership), details=str(detailpath)
    )
    result["fingerprints"] = {
        k: hash_artifact(Path(v), control) for k, v in result["paths"].items()
    }
    control.disk(directory)
    control.check()
    return result


def verify_source(path, columns, result, details, members):
    """Check immutable roster, original roles and reproducible local draft before publication."""
    from veri_ufku.importers.delimited import Control
    from veri_ufku.statistics.contracts import AnalysisSpec

    spec = AnalysisSpec.from_dict(result["spec"])
    spec.validate(columns, run=True)
    if spec.method.startswith("power_"):
        expected = power_plan(
            dict(
                spec.experiment_plan,
                metric="proportion" if spec.method == "power_proportion" else "mean",
            )
        )
        if members.height or details.height or expected != result["power_plan"]:
            raise ProjectError("Power plan/source artifact uyuşmuyor.")
        return
    frame = load(dict(path=str(path), columns=columns), spec, Control())
    if set(members["row_id"].to_list()) != set(frame["__vu_row_id"].to_list()):
        raise ProjectError("Deney roster RowId source bağı uyuşmuyor.")
    if spec.method == "random_assignment":
        ordered = sorted(
            zip(map(str, frame[spec.key].to_list()), frame["__vu_row_id"].to_list())
        )
        rng = np.random.default_rng(spec.seed)
        arms = np.where(
            rng.random(len(ordered)) < spec.experiment_plan["allocation"],
            spec.after,
            spec.before,
        ).tolist()
        expected = pl.DataFrame(
            dict(
                row_id=[v[1] for v in ordered],
                unit_id=[v[0] for v in ordered],
                arm=arms,
            )
        )
    else:
        expected = frame.rename({"__vu_row_id": "row_id"})
        if experiment(frame, spec) != result["experiment_analysis"]:
            raise ProjectError("Deney hesap/original source bağı uyuşmuyor.")
    if not expected.equals(details):
        raise ProjectError("Deney/assignment details source veya seed ile uyuşmuyor.")
