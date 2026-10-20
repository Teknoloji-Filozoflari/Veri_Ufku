"""Verified statsmodels adapters, explicit design matrices and safe JSON prediction."""

import hashlib
import itertools
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
import statsmodels
import statsmodels.api as sm
from statsmodels.stats.anova import AnovaRM
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.sm_exceptions import (
    ConvergenceWarning,
    IterationLimitWarning,
    PerfectSeparationWarning,
)

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import checked, filtered
from veri_ufku.importers.delimited import hash_artifact
from veri_ufku.statistics.model_contracts import MODEL_LABELS
from veri_ufku.storage.project_model import ProjectError, uid

CAUTION = "p-değeri nedensellik kanıtı değildir. Çıkarım varsayımlara bağlıdır; tahmin başarısı ayrı held-out doğrulama gerektirir. Bu fit bir prediction benchmark değildir."


def finite(value):
    value = float(value)
    return value if math.isfinite(value) else None


def prepare(request, spec, control):
    checked(request, control)
    view = ViewSpec.from_dict(spec.view) if spec.scope == "view" else ViewSpec()
    query, schema, names = filtered(request, view)
    chosen = list(
        dict.fromkeys(
            [spec.x]
            + spec.features
            + spec.within
            + [
                v
                for v in (
                    spec.weight,
                    spec.offset,
                    spec.exposure,
                    spec.group,
                    spec.cluster,
                )
                if v
            ]
        )
    )
    count = query.select(pl.len()).collect(engine="streaming").item()
    if (
        not count
        or count > 10000
        or count * (512 + 1024 * max(1, len(spec.features)))
        > control.budget.ram_bytes // 3
    ):
        raise ProjectError(
            "Model kapsamı boş veya bütçe dışında; en fazla10000 satır. Açık filtre kullanın; sessiz örnekleme yok."
        )
    for ident in chosen:
        dtype = schema[names[ident]]
        if (
            dtype.is_nested()
            or dtype.is_temporal()
            or dtype == pl.Binary
            or isinstance(dtype, pl.Decimal)
        ):
            raise ProjectError(
                "Model alanı skaler sayı/kategori olmalı; tarih/nested/binary/decimal sessiz dönüştürülmez."
            )
    numeric = (
        [spec.x]
        + [c for c in spec.features if c not in spec.references]
        + [c for c in (spec.weight, spec.offset, spec.exposure) if c]
    )
    for ident in numeric:
        if not schema[names[ident]].is_numeric():
            raise ProjectError(
                "Sayısal response/predictor/ağırlık rolü gerekli; kategorik predictor için referans seçin."
            )
    data = query.select(
        "__vu_row_id", *[pl.col(names[c]).alias(c) for c in chosen]
    ).collect(engine="streaming")
    # Integer >2**53 is rejected, not silently rounded into the design matrix.
    for ident in numeric:
        if (
            schema[names[ident]].is_integer()
            and data[ident].drop_nulls().abs().max() is not None
            and data[ident].drop_nulls().abs().max() > 2**53
        ):
            raise ProjectError(
                "Float64 için kayıpsız olmayan büyük tamsayı; açık dönüşüm/ölçek seçin."
            )
    valid = pl.all_horizontal(
        [pl.col(c).is_not_null() for c in chosen]
        + [pl.col(c).is_finite() for c in chosen if schema[names[c]].is_float()]
    )
    clean = data.filter(valid)
    excluded = data.height - clean.height
    if excluded and spec.missing_policy == "reject":
        raise ProjectError(
            "Eksik/sonlu olmayan model alanı var; açık complete-case politikasını seçin veya veriyi düzeltin."
        )
    if clean.height < 4:
        raise ProjectError("En az4 geçerli model gözlemi gerekli.")
    values = {c: clean[c].to_list() for c in chosen}
    y = np.asarray(values[spec.x], dtype=float)
    if spec.method == "glm_binomial" and (
        not np.isin(y, [0, 1]).all() or len(np.unique(y)) != 2
    ):
        raise ProjectError(
            "Binomial response iki sınıflı 0/1 olmalı; successes/trials veya otomatik event seçimi yok."
        )
    if spec.method in ("glm_poisson", "glm_negative_binomial") and (
        (y < 0).any() or not np.equal(y, np.floor(y)).all() or y.sum() == 0
    ):
        raise ProjectError(
            "Count response sıfır dahil negatif olmayan tamsayı ve pozitif toplam olmalı."
        )
    for c in (spec.weight, spec.exposure):
        if c and (np.asarray(values[c], dtype=float) <= 0).any():
            raise ProjectError(
                "WLS ters-varyans ağırlığı/exposure kesin pozitif olmalı."
            )
    design = [dict(label="Intercept", factors=[])]
    blocks, levels = {}, {}
    for c in spec.features:
        if c in spec.references:
            labels = [str(v) for v in values[c]]
            # String conversion must not collapse distinct original categories.
            if len(set(labels)) != len(
                set((type(v).__name__, str(v)) for v in values[c])
            ):
                raise ProjectError("Kategorik etiket dönüşümü çakışıyor.")
            categories = sorted(set(labels))
            if not 2 <= len(categories) <= 20 or spec.references[c] not in categories:
                raise ProjectError(
                    "Kategorik baseline mevcut olmalı;2–20 gözlenen kategori gerekir."
                )
            levels[c] = dict(
                reference=spec.references[c], levels=categories, name=names[c]
            )
            blocks[c] = [
                dict(
                    label=names[c] + "[" + k + "] vs " + spec.references[c],
                    factors=[dict(column=c, level=k)],
                )
                for k in categories
                if k != spec.references[c]
            ]
        else:
            blocks[c] = [dict(label=names[c], factors=[dict(column=c)])]
        design.extend(blocks[c])
    for a, b in spec.interactions:
        for da, db in itertools.product(blocks[a], blocks[b]):
            design.append(
                dict(
                    label=da["label"] + " × " + db["label"],
                    factors=da["factors"] + db["factors"],
                )
            )
    if len(design) > 60 or clean.height <= len(design) + 1:
        raise ProjectError("En fazla60 design terimi ve pozitif residual df gerekli.")
    X = matrix(values, design)
    if np.linalg.matrix_rank(X) != X.shape[1] or np.linalg.cond(X) > 1e12:
        raise ProjectError(
            "Singular / tam rank değil veya kötü koşullu design. Redundant predictor/interaction ve ölçeği düzeltin."
        )
    if spec.method == "wls":
        weighted_design = (
            X * np.sqrt(np.asarray(values[spec.weight], dtype=float))[:, None]
        )
        if (
            np.linalg.matrix_rank(weighted_design) != X.shape[1]
            or np.linalg.cond(weighted_design) > 1e12
        ):
            raise ProjectError(
                "WLS ağırlıklı design singular / kötü koşullu; ağırlık ölçeğini ve predictorları inceleyin."
            )
    notes = [CAUTION]
    clusters = None
    if spec.cluster:
        clusters = np.asarray([str(v) for v in values[spec.cluster]])
        nclusters = len(set(clusters))
        if nclusters < 5:
            raise ProjectError(
                "Cluster SE için en az5 bağımsız küme (uygulama alt sınırı) gerekli; az kümede asimptotik çıkarım güvenilmez."
            )
        notes.append(
            f"Cluster sayısı={nclusters}.5 alt sınır güvenilirlik garantisi değildir;50 altı küçük-küme yanlılığına dikkat. Small-sample correction kullanılır; CR2/wild bootstrap değildir."
        )
    vif = [
        dict(term=d["label"], value=finite(variance_inflation_factor(X, i)))
        for i, d in enumerate(design)
        if i
    ]
    if any(v["value"] is None or v["value"] > 10 for v in vif):
        notes.append(
            "Yüksek VIF: katsayı çıkarımı kararsız olabilir;10 eşiği otomatik değişken silme kuralı değildir."
        )
    if spec.method == "wls":
        notes.append(
            "WLS ağırlığı ters hata varyansıdır; survey/frekans ağırlığı değildir. Tanılama whitened residual üzerinde yapılır."
        )
    if spec.method == "glm_negative_binomial":
        notes.append(
            f"NB2 Var(Y)=mu+alpha*mu²; alpha={spec.nb_alpha} kullanıcı tarafından sabitlenir, tahmin edilmez. AIC/BIC bağlamında alpha korunur."
        )
    if spec.method == "mixed":
        if (
            len(set(map(str, values[spec.group]))) < 5
            or min(pd.Series(values[spec.group]).value_counts())
            < len(spec.random_slopes) + 2
        ):
            raise ProjectError(
                "Mixed için en az5 grup ve her grupta random design boyutundan fazla gözlem gerekli."
            )
        notes.append(
            "Gaussian random intercept"
            + (" + slope" if spec.random_slopes else "")
            + "; bağımsız birim gruptur. Prediction marginal fixed-effect; yeni grubun random etkisi tahmin edilmez."
        )
    info = dict(
        method=spec.method,
        n=[clean.height],
        used_rows=clean.height,
        total_rows=count,
        excluded_rows=excluded,
        warnings=notes,
        design=design,
        categorical_baselines=levels,
        vif=vif,
        condition_number=float(np.linalg.cond(X)),
        formula=names[spec.x] + " ~ " + " + ".join(d["label"] for d in design),
        link="logit"
        if spec.method == "glm_binomial"
        else "log"
        if spec.method.startswith("glm_")
        else "identity",
        observation_unit=spec.observation_unit,
    )
    return info, y, X, values, clean["__vu_row_id"].to_list(), clusters


def matrix(values, design):
    n = len(next(iter(values.values())))
    columns = []
    for term in design:
        a = np.ones(n)
        for factor in term["factors"]:
            vals = values[factor["column"]]
            a *= (
                np.asarray([float(str(v) == factor["level"]) for v in vals])
                if "level" in factor
                else np.asarray(vals, dtype=float)
            )
        columns.append(a)
    result = np.column_stack(columns)
    if not np.isfinite(result).all():
        raise ProjectError("Design/interaction sonlu olmayan değer üretti.")
    return result


def repeated(spec, y, values):
    frame = pd.DataFrame(
        dict(
            response=y,
            subject=[str(v) for v in values[spec.group]],
            **{f"w{i}": [str(v) for v in values[c]] for i, c in enumerate(spec.within)},
        )
    )
    if len(y) > 300 or frame.subject.nunique() > 100:
        raise ProjectError(
            "AnovaRM saturated design bütçesi: en fazla300 hücre /100 kişi; açık daha küçük kapsam seçin."
        )
    factors = [f"w{i}" for i in range(len(spec.within))]
    if (
        any(not 2 <= frame[c].nunique() <= 10 for c in factors)
        or frame.subject.nunique() < 3
    ):
        raise ProjectError(
            "Repeated: en az3 kişi ve within faktör başına2–10 düzey gerekli."
        )
    if frame.duplicated(["subject"] + factors).any():
        raise ProjectError("Tekrarlı kişi×within hücresi; otomatik agregasyon yok.")
    expected = math.prod(frame[c].nunique() for c in factors)
    if not (frame.groupby("subject").size() == expected).all():
        raise ProjectError(
            "Repeated-measures dengeli tam kişi×within grid ister; eksik hücre reddedilir."
        )
    fit = AnovaRM(frame, "response", "subject", within=factors).fit()
    return [
        dict(
            term=k,
            f=finite(r["F Value"]),
            numerator_df=finite(r["Num DF"]),
            denominator_df=finite(r["Den DF"]),
            p=finite(r["Pr > F"]),
        )
        for k, r in fit.anova_table.iterrows()
    ], (
        y
        - frame.groupby("subject").response.transform("mean").to_numpy()
        - frame.groupby(factors).response.transform("mean").to_numpy()
        + float(np.mean(y))
    )


def fit_model(spec, y, X, values, clusters):
    kw = dict(cov_type=spec.covariance)
    if clusters is not None:
        kw.update(cov_kwds=dict(groups=clusters, use_correction=True), use_t=True)
    if spec.method == "ols":
        return sm.OLS(y, X).fit(**kw)
    if spec.method == "wls":
        return sm.WLS(y, X, weights=np.asarray(values[spec.weight], dtype=float)).fit(
            **kw
        )
    if spec.method.startswith("glm_"):
        family = (
            sm.families.Binomial()
            if spec.method == "glm_binomial"
            else sm.families.Poisson()
            if spec.method == "glm_poisson"
            else sm.families.NegativeBinomial(alpha=spec.nb_alpha)
        )
        return sm.GLM(
            y,
            X,
            family=family,
            offset=np.asarray(values[spec.offset], dtype=float)
            if spec.offset
            else None,
            exposure=np.asarray(values[spec.exposure], dtype=float)
            if spec.exposure
            else None,
        ).fit(maxiter=spec.max_iterations, **kw)
    if spec.method == "quantile":
        return sm.QuantReg(y, X).fit(
            q=spec.quantile, vcov=spec.covariance, max_iter=spec.max_iterations
        )
    if spec.method == "mixed":
        Z = np.column_stack(
            [np.ones(len(y))]
            + [np.asarray(values[c], dtype=float) for c in spec.random_slopes]
        )
        for g in set(map(str, values[spec.group])):
            local = Z[np.asarray([str(v) == g for v in values[spec.group]])]
            if np.linalg.matrix_rank(local) != Z.shape[1]:
                raise ProjectError("Grup içi random slope design singular.")
        return sm.MixedLM(
            y, X, groups=np.asarray([str(v) for v in values[spec.group]]), exog_re=Z
        ).fit(reml=spec.reml, method="lbfgs", maxiter=spec.max_iterations, disp=False)
    raise ProjectError("Model adaptörü desteklenmiyor.")


def diagnostic_plot(path, fitted, residual, leverage, info):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    fig = Figure(figsize=(10, 7), layout="constrained")
    FigureCanvasAgg(fig)
    axes = fig.subplots(2, 2)
    n = min(1000, len(residual))
    positions = np.linspace(0, len(residual) - 1, n, dtype=int)
    axes[0, 0].scatter(np.asarray(fitted)[positions], residual[positions], s=8)
    axes[0, 0].axhline(0, color="black", lw=0.7)
    axes[0, 0].set(
        xlabel="Fitted (in-sample)", ylabel="Residual", title="Residual vs fitted"
    )
    sm.qqplot(residual[positions], line="s", ax=axes[0, 1])
    axes[0, 1].set_title("QQ: residual distribution; not a normality proof")
    axes[1, 0].hist(residual[positions], bins=min(25, n))
    axes[1, 0].set(xlabel="Residual", ylabel="Count")
    axes[1, 1].scatter(
        np.arange(n),
        np.asarray(leverage)[positions]
        if leverage is not None
        else residual[positions],
        s=8,
    )
    axes[1, 1].set(
        xlabel="Sample position (not time)",
        ylabel="Leverage" if leverage is not None else "Residual",
    )
    fig.suptitle(
        MODEL_LABELS[info["method"]]
        + f" · n={info['used_rows']} · plot ≤1000; statistics use all rows",
        fontsize=10,
    )
    with __import__("matplotlib").rc_context(
        {"svg.fonttype": "path", "font.family": "DejaVu Sans"}
    ):
        fig.savefig(
            path,
            format="svg",
            metadata={
                "Description": info["formula"]
                + "; dataset-bound; inference is not prediction; p is not causality"
            },
        )

    fig.savefig(path.with_suffix(".png"), dpi=120)


def calculate(request, spec, workspace, control, preflight=False):
    info, y, X, values, members, clusters = prepare(request, spec, control)
    if preflight:
        # Validate repeated grid before asking user to approve assumptions.
        if spec.method == "repeated":
            repeated(spec, y, values)
        return dict(
            info,
            spec=spec.data(),
            dataset_version=request["version_id"],
            config_revision=request.get("config_revision", 0),
        )
    control.progress("İstatistiksel model fit", 0, None)
    coefficients, fitstats, diag, tests = [], {}, {}, []
    leverage = None
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            if spec.method == "repeated":
                tests, residual = repeated(spec, y, values)
                within_names = {
                    f"w{i}": next(
                        c["name"] for c in request["columns"] if c["id"] == ident
                    )
                    for i, ident in enumerate(spec.within)
                }
                for test in tests:
                    test["term"] = " × ".join(
                        within_names[part] for part in test["term"].split(":")
                    )
                fitted = y - residual
                if any(t["f"] is None or t["p"] is None for t in tests):
                    raise ProjectError(
                        "Repeated test tanımsız; sıfır residual varyansını inceleyin."
                    )
                info["warnings"].append(
                    "AnovaRM balanced within-subject ANOVA: sphericity varsayımı; GG/HF correction ve between-subject etkisi desteklenmiyor. QQ kişi ve within hücre etkileri çıkarılmış residual gösterir; omnibus F için katsayı CI yok."
                )
            else:
                fitted_model = fit_model(spec, y, X, values, clusters)
                if not getattr(fitted_model, "converged", True) or any(
                    issubclass(
                        w.category,
                        (
                            ConvergenceWarning,
                            IterationLimitWarning,
                            PerfectSeparationWarning,
                        ),
                    )
                    for w in caught
                ):
                    raise ProjectError(
                        "Model convergence / separation kontrolü başarısız; sonuç kabul edilmedi. İterasyon, ölçek ve designı inceleyin."
                    )
                params = np.asarray(
                    fitted_model.fe_params
                    if spec.method == "mixed"
                    else fitted_model.params
                )
                ci = np.asarray(fitted_model.conf_int(alpha=1 - spec.confidence))[
                    : len(params)
                ]
                bse = np.asarray(fitted_model.bse)[: len(params)]
                ps = np.asarray(fitted_model.pvalues)[: len(params)]
                if not all(np.isfinite(a).all() for a in (params, ci, bse, ps)):
                    raise ProjectError(
                        "Model katsayı/CI/SE tanımsız; singular veya boundary fit kabul edilmedi."
                    )
                for i, term in enumerate(info["design"]):
                    transformed = spec.method.startswith("glm_")
                    if spec.method == "glm_binomial":
                        effect_label = (
                            "baseline odds"
                            if i == 0
                            else "interaction odds-ratio multiplier"
                            if len(term["factors"]) > 1
                            else "odds ratio"
                        )
                    elif transformed:
                        effect_label = (
                            "baseline rate / expected count"
                            if i == 0
                            else "interaction rate-ratio multiplier"
                            if len(term["factors"]) > 1
                            else "rate ratio"
                        )
                    else:
                        effect_label = "coefficient"
                    coefficients.append(
                        dict(
                            term=term["label"],
                            estimate=float(params[i]),
                            se=float(bse[i]),
                            p=float(ps[i]),
                            low=float(ci[i, 0]),
                            high=float(ci[i, 1]),
                            confidence=spec.confidence,
                            effect=finite(np.exp(params[i]))
                            if transformed
                            else float(params[i]),
                            effect_low=finite(np.exp(ci[i, 0]))
                            if transformed
                            else float(ci[i, 0]),
                            effect_high=finite(np.exp(ci[i, 1]))
                            if transformed
                            else float(ci[i, 1]),
                            effect_label=effect_label,
                        )
                    )
                fitted = np.asarray(fitted_model.fittedvalues)
                residual = np.asarray(
                    fitted_model.resid_response
                    if spec.method.startswith("glm_")
                    else fitted_model.resid
                )
                if not np.isfinite(fitted).all() or not np.isfinite(residual).all():
                    raise ProjectError("Model fitted/residual sonlu değil.")
                if spec.method in ("ols", "wls"):
                    bp = (
                        het_breuschpagan(fitted_model.wresid, X)
                        if X.shape[1] > 1
                        else None
                    )
                    diag["heteroskedasticity"] = (
                        dict(
                            method="Koenker BP on whitened residual, original variance predictors",
                            lm=finite(bp[0]),
                            p=finite(bp[1]),
                        )
                        if bp
                        else dict(status="unsupported: intercept-only")
                    )
                    fitstats.update(
                        r_squared=finite(fitted_model.rsquared),
                        adjusted_r_squared=finite(fitted_model.rsquared_adj),
                    )
                    # WLS influence uses explicitly whitened OLS, preserving weights.
                    influence = (
                        sm.OLS(fitted_model.model.wendog, fitted_model.model.wexog)
                        .fit()
                        .get_influence()
                    )
                    leverage = influence.hat_matrix_diag
                    cooks = influence.cooks_distance[0]
                elif spec.method.startswith("glm_"):
                    dispersion = float(
                        np.sum(np.asarray(fitted_model.resid_pearson) ** 2)
                        / fitted_model.df_resid
                    )
                    diag["overdispersion"] = dict(
                        pearson_ratio=dispersion,
                        warning=dispersion > 1.5,
                        threshold="1.5 heuristic; not a formal test",
                        family=spec.method,
                    )
                    fitstats.update(
                        deviance=finite(fitted_model.deviance),
                        pearson_chi2=finite(fitted_model.pearson_chi2),
                    )
                    influence = fitted_model.get_influence()
                    leverage, cooks = (
                        influence.hat_matrix_diag,
                        influence.cooks_distance[0],
                    )
                else:
                    cooks = None
                    diag["influence"] = dict(
                        status="unsupported for quantile/mixed; residual extremes are not Cook distance"
                    )
                    diag["heteroskedasticity"] = dict(
                        status="unsupported; OLS BP is not reused"
                    )
                    if spec.method == "quantile":
                        fitstats.update(pseudo_r_squared=finite(fitted_model.prsquared))
                    else:
                        covariance = np.asarray(fitted_model.cov_re)
                        if np.min(np.linalg.eigvalsh(covariance)) <= 1e-10:
                            raise ProjectError(
                                "Random covariance singular/boundary; mixed fit kabul edilmedi."
                            )
                        fitstats.update(
                            random_covariance=covariance.tolist(),
                            residual_variance=finite(fitted_model.scale),
                            reml=spec.reml,
                        )
                if leverage is not None:
                    diag["influence"] = dict(
                        method="whitened Cook/leverage"
                        if spec.method == "wls"
                        else "backend Cook/leverage",
                        cutoff=4 / len(y),
                        points=[
                            dict(
                                row_id=members[i],
                                cook=finite(cooks[i]),
                                leverage=finite(leverage[i]),
                            )
                            for i in np.argsort(cooks)[-20:][::-1]
                        ],
                        influential_count=int(np.sum(cooks > 4 / len(y))),
                    )
                likelihood = spec.method != "quantile" and not (
                    spec.method == "mixed" and spec.reml
                )
                fitstats.update(
                    log_likelihood=finite(fitted_model.llf) if likelihood else None,
                    aic=finite(fitted_model.aic) if likelihood else None,
                    bic=finite(
                        fitted_model.bic_llf
                        if spec.method.startswith("glm_")
                        else fitted_model.bic
                    )
                    if likelihood
                    else None,
                    information_criteria_status="ML likelihood; compare only equal context"
                    if likelihood
                    else "unsupported: quantile pseudo likelihood / mixed REML",
                )
            info["warnings"].extend("Backend: " + str(w.message)[:350] for w in caught)
    except ProjectError:
        raise
    except (
        ValueError,
        np.linalg.LinAlgError,
        ZeroDivisionError,
        FloatingPointError,
    ) as error:
        raise ProjectError(
            "Model singular/design/convergence hatası; desteklenmeyen veya tanımsız fit: "
            + type(error).__name__
        ) from error
    control.check()
    checked(request, control)
    directory = Path(workspace)
    plot = directory / "model-diagnostic.svg"
    diagnostic_plot(plot, fitted, residual, leverage, info)
    # Context deliberately excludes predictors, but includes data/response/likelihood/
    # covariance and auxiliary roles; REML cannot compare changed fixed effects.
    context = dict(
        dataset_version=request["version_id"],
        rows=members,
        response=spec.x,
        family="gaussian" if spec.method in ("ols", "wls") else spec.method,
        link=info["link"],
        weight=spec.weight,
        offset=spec.offset,
        exposure=spec.exposure,
        alpha=spec.nb_alpha if spec.method == "glm_negative_binomial" else None,
        group=spec.group,
        random_slopes=spec.random_slopes,
        covariance=spec.covariance,
        cluster=spec.cluster,
        reml=spec.reml if spec.method == "mixed" else None,
    )
    info.update(
        coefficients=coefficients,
        model_tests=tests,
        fit=fitstats,
        diagnostics=diag,
        residual_summary=dict(
            mean=finite(np.mean(residual)),
            sd=finite(np.std(residual, ddof=1)),
            definition="response residual"
            if spec.method != "repeated"
            else "response minus subject/within cell means plus grand mean",
        ),
        comparison_context=hashlib.sha256(
            json.dumps(context, sort_keys=True).encode()
        ).hexdigest(),
        model_support=dict(
            prediction=spec.method != "repeated",
            prediction_kind="marginal fixed effect"
            if spec.method == "mixed"
            else "conditional quantile"
            if spec.method == "quantile"
            else "mean response/probability"
            if spec.method.startswith("glm_")
            else "mean response",
            result_save=True,
            model_save=spec.method != "repeated",
            prediction_interval=False,
            reason="safe JSON coefficients/design; no executable pickle; repeated ANOVA is inference only; no held-out score",
        ),
    )
    info["prediction_schema"] = dict(
        features=spec.features,
        columns={
            c: next(v["name"] for v in request["columns"] if v["id"] == c)
            for c in spec.features
        },
        baselines=info["categorical_baselines"],
        design=info["design"],
        coefficients=[c["estimate"] for c in coefficients],
        link=info["link"],
        offset=spec.offset,
        exposure=spec.exposure,
    )
    result = dict(
        info,
        spec=spec.data(),
        primary=dict(method=spec.method, p_value=None, statistic=None, effect=None),
        comparisons=[],
        correction=dict(
            method="none",
            family="individual coefficient CI; not simultaneous",
            family_size=len(coefficients),
            ci_adjusted=False,
            scope="this run",
        ),
        dataset_version=request["version_id"],
        config_revision=request.get("config_revision", 0),
        result_version="analysis:" + uid(),
        method_version=1,
        parameter_version=1,
        provenance=dict(
            schema="AnalysisResult/v1",
            backend="statsmodels",
            statsmodels_version=statsmodels.__version__,
            numpy_version=np.__version__,
            snapshot_fingerprint=request["fingerprint"],
            snapshot_uri=request["snapshot_uri"],
            source_snapshot_id=request["source_snapshot_id"],
            seed=None,
            help_content_version=56,
        ),
    )
    membership = directory / "model-members.parquet"
    pl.DataFrame({"row_id": members}, schema={"row_id": pl.String}).write_parquet(
        membership
    )
    destination = directory / "model-result.json"
    destination.write_text(
        json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )
    result["paths"] = dict(
        result=str(destination),
        members=str(membership),
        diagnostic=str(plot),
        diagnostic_png=str(plot.with_suffix(".png")),
    )
    result["fingerprints"] = {
        k: hash_artifact(Path(v), control) for k, v in result["paths"].items()
    }
    control.disk(directory)
    control.check()
    return result


def predict(result, inputs, offset=0.0, exposure=1.0):
    if not result["model_support"]["prediction"]:
        raise ProjectError(
            "Repeated-measures ANOVA yeni gözlem prediction desteklemez."
        )
    schema = result["prediction_schema"]
    if not isinstance(inputs, dict) or set(inputs) != set(schema["features"]):
        raise ProjectError("Prediction bütün seçili predictor kimliklerini gerektirir.")
    values = {}
    for c, value in inputs.items():
        if c in schema["baselines"]:
            if str(value) not in schema["baselines"][c]["levels"]:
                raise ProjectError("Yeni kategori eğitim baseline sözleşmesinde yok.")
        elif (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or type(value) is int
            and abs(value) > 2**53
        ):
            raise ProjectError("Prediction sayısal değeri sonlu/kayıpsız olmalı.")
        values[c] = [value]
    if not values:
        values = {"_intercept": [0]}
    for value in (offset, exposure):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ProjectError("Prediction offset/exposure sonlu olmalı.")
    if (
        exposure <= 0
        or not schema["exposure"]
        and exposure != 1
        or not schema["offset"]
        and offset != 0
    ):
        raise ProjectError("Prediction offset/exposure eğitim sözleşmesiyle uyuşmuyor.")
    eta = (
        float(matrix(values, schema["design"])[0] @ np.asarray(schema["coefficients"]))
        + (offset if schema["offset"] else 0)
        + (math.log(exposure) if schema["exposure"] else 0)
    )
    from scipy.special import expit

    with np.errstate(over="ignore"):
        output = (
            float(expit(eta))
            if schema["link"] == "logit"
            else float(np.exp(eta))
            if schema["link"] == "log"
            else eta
        )
    if not math.isfinite(output):
        raise ProjectError("Prediction link dönüşümünde taşma; sonuç kabul edilmedi.")
    return dict(
        value=output,
        kind=result["model_support"]["prediction_kind"],
        interval=None,
        dataset_version=result["dataset_version"],
        warning="In-sample fit / p-değeri held-out prediction başarısı değildir; nedensel etki değildir.",
    )


def compare_information(a, b):
    if a["comparison_context"] != b["comparison_context"] or any(
        r["fit"].get("aic") is None or r["fit"].get("bic") is None for r in (a, b)
    ):
        raise ProjectError(
            "AIC/BIC için aynı response, satırlar, likelihood/link, ağırlık/offset ve ML bağlamı gerekli; REML/quantile desteklenmiyor."
        )
    return dict(
        delta_aic=a["fit"]["aic"] - b["fit"]["aic"],
        delta_bic=a["fit"]["bic"] - b["fit"]["bic"],
        warning="Relative likelihood fit; prediction veya nedensellik kanıtı değildir.",
    )
