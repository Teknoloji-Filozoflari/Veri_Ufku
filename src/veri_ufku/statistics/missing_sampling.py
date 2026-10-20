"""Bounded missingness, sampling, typed weights and separate MI inference.

Survey: stratified ultimate-cluster Taylor linearization, with-replacement,
no FPC/calibration/lonely-PSU adjustment. MI: Gaussian conditional posterior
numeric imputations; normal-theory mean and full-rank OLS only, Rubin/Barnard-
Rubin scalar marginal intervals, never pool predictions or p-values.
"""

import hashlib
import json
import math
from decimal import Decimal
from pathlib import Path

import numpy as np
import polars as pl
from scipy import stats
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import checked, filtered
from veri_ufku.importers.delimited import hash_artifact
from veri_ufku.statistics.contracts import LABELS
from veri_ufku.storage.project_model import ProjectError, uid


def rubin_pool(estimates, covariances, complete_df, confidence=0.95):
    """Rubin total covariance and Barnard–Rubin finite-sample marginal df."""
    q, u = np.asarray(estimates, float), np.asarray(covariances, float)
    if (
        q.ndim != 2
        or len(q) < 2
        or u.shape != (len(q), q.shape[1], q.shape[1])
        or not np.isfinite(q).all()
        or not np.isfinite(u).all()
        or complete_df <= 0
    ):
        raise ProjectError("MI havuzlama şekli/sonluluğu/serbestlik derecesi geçersiz.")
    if any(not np.allclose(a, a.T) or np.linalg.eigvalsh(a).min() < -1e-10 for a in u):
        raise ProjectError(
            "MI kovaryans matrisi simetrik ve pozitif yarı tanımlı olmalı."
        )
    mean, within = q.mean(axis=0), u.mean(axis=0)
    between = np.atleast_2d(np.cov(q, rowvar=False, ddof=1))
    total = within + (1 + 1 / len(q)) * between
    variance = np.diag(total)
    if (variance <= 0).any():
        raise ProjectError("MI toplam varyansı sıfır/geçersiz; çıkarım sunulamaz.")
    fraction = (1 + 1 / len(q)) * np.diag(between) / variance
    old_df = np.divide(
        len(q) - 1, fraction**2, out=np.full_like(fraction, np.inf), where=fraction > 0
    )
    observed_df = (complete_df + 1) / (complete_df + 3) * complete_df * (1 - fraction)
    if (observed_df <= 0).any():
        raise ProjectError("MI gözlenen serbestlik derecesi yetersiz.")
    df = 1 / (1 / old_df + 1 / observed_df)
    se = np.sqrt(variance)
    margin = stats.t.ppf((1 + confidence) / 2, df) * se
    return dict(
        estimates=mean.tolist(),
        within_covariance=within.tolist(),
        between_covariance=between.tolist(),
        total_covariance=total.tolist(),
        standard_errors=se.tolist(),
        df=df.tolist(),
        missing_variance_fraction=fraction.tolist(),
        fraction_missing_information=(
            fraction + (1 - fraction) * 2 / (df + 3)
        ).tolist(),
        confidence_intervals=np.column_stack([mean - margin, mean + margin]).tolist(),
        p_values=(2 * stats.t.sf(abs(mean / se), df)).tolist(),
        rule="Rubin covariance; Barnard–Rubin finite-sample df; marginal t intervals",
    )


def survey_mean(values, weights, strata, psu, confidence):
    mean = float(np.dot(values, weights) / weights.sum())
    clusters = {}
    for v, w, h, j in zip(values, weights, strata, psu):
        key = (h, j)  # PSU ids are explicitly nested in strata.
        clusters[key] = clusters.get(key, 0.0) + w * (v - mean) / weights.sum()
    buckets = {}
    for (h, _), v in clusters.items():
        buckets.setdefault(h, []).append(v)
    if any(len(v) < 2 for v in buckets.values()):
        raise ProjectError(
            "Her stratada en az2 PSU gerekli; lonely-PSU sessizce düzeltilmez."
        )
    variance = sum(
        len(v) / (len(v) - 1) * sum((z - np.mean(v)) ** 2 for z in v)
        for v in buckets.values()
    )
    df = sum(len(v) - 1 for v in buckets.values())
    se = math.sqrt(variance)
    margin = float(stats.t.ppf((1 + confidence) / 2, df)) * se
    reference = float(np.var(values, ddof=1) / len(values))
    return dict(
        estimate=mean,
        variance=float(variance),
        standard_error=se,
        df=df,
        confidence_interval=[mean - margin, mean + margin],
        design_effect=float(variance / reference) if reference > 0 else None,
        design_effect_reference="observed unweighted iid SRS s²/n; descriptive reference, not calibrated survey deff",
        strata=len(buckets),
        psus=len(clusters),
        method="stratified ultimate-cluster Taylor; WR; no FPC; PSU nested within strata",
        zero_variance=bool(variance == 0),
    )


def numeric(frame, name, precision, missing=False):
    if not frame.schema[name].is_numeric():
        raise ProjectError("Ölçüm/özellik/ağırlık fiziksel sayısal olmalı.")
    out = []
    for v in frame[name]:
        if v is None:
            if not missing:
                raise ProjectError("Ölçüm/ağırlık eksik; sessiz satır düşürme yok.")
            out.append(np.nan)
            continue
        z = float(v)
        if not math.isfinite(z) or abs(z) > 1e100:
            raise ProjectError(
                "Sonlu olmayan/güvenli aralık dışı sayılar reddedildi; otomatik eksik sayılmaz."
            )
        if (
            precision == "reject"
            and isinstance(v, (int, Decimal))
            and Decimal.from_float(z) != Decimal(v)
        ):
            raise ProjectError(
                "Float64 hassasiyet kaybı; açık yaklaşık hesap izni gerekir."
            )
        out.append(z)
    return np.asarray(out)


def fit_ols(values, features, weights=None, inference=True):
    design = np.column_stack([np.ones(len(values)), features])
    w = np.ones(len(values)) if weights is None else weights
    weighted = design * np.sqrt(w[:, None])
    if (
        len(values) <= design.shape[1]
        or np.linalg.matrix_rank(weighted) < design.shape[1]
    ):
        raise ProjectError(
            "OLS/WLS için tam rank ve pozitif artık serbestliği gerekli."
        )
    beta = np.linalg.lstsq(weighted, values * np.sqrt(w), rcond=None)[0]
    residual = values - design @ beta
    df = len(values) - design.shape[1]
    cov = (
        np.linalg.inv(weighted.T @ weighted) * np.dot(w, residual**2) / df
        if inference
        else None
    )
    return beta, cov, df


def calculate(request, spec, workspace, control, preflight=False):
    checked(request, control)
    query, schema, names = filtered(
        request, ViewSpec.from_dict(spec.view) if spec.scope == "view" else ViewSpec()
    )
    count = query.select(pl.len()).collect().item()
    limit = 5000 if spec.method.startswith("mi_") else 10000
    if (
        not 0 < count <= limit
        or count
        * (256 + 80 * len(request["columns"]))
        * max(1, spec.imputations if spec.method.startswith("mi_") else 1)
        > control.budget.ram_bytes // 2
    ):
        raise ProjectError(
            "İleri hesap kapsamı boş/bütçe dışı: MI5000, diğerleri10000 satır. Sessiz örnekleme yok."
        )
    frame = query.collect()
    for ident in [spec.x, *spec.features]:
        if spec.method.startswith(("mi_", "weighted_", "survey_")) and request.get(
            "semantic_metadata", {}
        ).get(ident, {}).get("role") in ("identifier", "category", "time", "ignored"):
            raise ProjectError("Kimlik/kategori/zaman ölçüm olarak kullanılamaz.")
    warnings = [
        "MCAR/MAR/MNAR gözlenen veriden kesin tespit edilmez; seçilen mekanizma bir varsayımdır."
    ]
    if spec.weight_type == "survey":
        warnings.append(
            "Strata/PSU tasarımı: bağımsız PSU, WR Taylor; FPC, kalibrasyon, replicate weights, domain ve çok aşamalı alt-küme düzeltmesi desteklenmiyor. Filtreli kapsam domain survey inference değildir."
        )
        if spec.scope == "view" and ViewSpec.from_dict(spec.view).filters:
            raise ProjectError(
                "Filtreli survey domain çıkarımı desteklenmiyor; tam dataset kullanın."
            )
    info = dict(
        source_columns=request["columns"],
        method=spec.method,
        method_label=LABELS[spec.method],
        scope=spec.scope,
        population_n=count,
        used_rows=count,
        excluded_rows=0,
        n=[count],
        group_labels=[],
        summaries=[],
        warnings=warnings,
        spec=spec.data(),
        dataset_version=request["version_id"],
        config_revision=request.get("config_revision", 0),
    )
    fields = [spec.x, *spec.features]
    x = None
    if spec.method.startswith(("mi_", "weighted_", "survey_")):
        matrix = np.column_stack(
            [
                numeric(
                    frame,
                    names[i],
                    spec.precision,
                    missing=spec.method.startswith("mi_"),
                )
                for i in fields
            ]
        )
        if np.isnan(matrix).all(axis=0).any():
            raise ProjectError(
                "Tamamen eksik sayısal alan için MI dağılımı öğrenilemez."
            )
        x = matrix[:, 0]
    weights = None
    if spec.weight:
        weights = numeric(frame, names[spec.weight], spec.precision)
        if (weights < 0).any() or weights.sum() <= 0:
            raise ProjectError("Negatif veya toplamı sıfır ağırlık reddedildi.")
        if spec.weight_type in ("analytic", "survey") and (weights <= 0).any():
            raise ProjectError("Analitik/survey ağırlık kesin pozitif olmalı.")
        if spec.weight_type == "frequency" and (
            (weights != np.floor(weights)).any() or weights.sum() > 1e9
        ):
            raise ProjectError(
                "Frekans ağırlığı tamsayı tekrar sayısı; toplam en fazla1e9."
            )
        info["weight_summary"] = dict(
            type=spec.weight_type,
            sum=float(weights.sum()),
            zero_rows=int((weights == 0).sum()),
            applied_automatically=False,
        )
    for ident in [i for i in (spec.group, spec.strata, spec.psu) if i]:
        col = frame[names[ident]]
        if (
            schema[names[ident]].is_nested()
            or col.null_count()
            or col.dtype.is_float()
            and not col.is_finite().all()
        ):
            raise ProjectError("Grup/strata/PSU skaler ve eksiksiz/sonlu olmalı.")
    if spec.method == "survey_mean":
        survey_mean(
            x,
            weights,
            frame[names[spec.strata]].to_list(),
            frame[names[spec.psu]].to_list(),
            spec.confidence,
        )
    if preflight:
        info["warnings"].append(
            "Hesap kaynak veriyi değiştirmez. MI ayrı realizasyonlar ve katsayı kovaryansları saklar; tek doldurma ve model CV'siyle karıştırılmaz."
        )
        return info
    rng = np.random.default_rng(spec.seed)
    rowids = frame["__vu_row_id"].to_list()
    sourcecol = "__vu_source_record_id"
    if sourcecol not in frame.columns:
        raise ProjectError("Kaynak kayıt kimliği snapshot'ta yok.")
    identity = frame.select(
        pl.col("__vu_row_id").alias("row_id"),
        pl.col(sourcecol).alias("source_record_id"),
    )
    details = identity
    data = {}
    primary = dict(
        method=spec.method,
        statistic=None,
        p_value=None,
        effect=dict(name=LABELS[spec.method], value=None, confidence_interval=None),
    )
    if spec.method in ("missing_patterns", "missing_indicators"):
        mask = frame.select([pl.col(names[i]).is_null().alias(i) for i in fields])
        if any(
            frame.schema[names[i]].is_float()
            and (~frame[names[i]].is_finite().fill_null(True)).any()
            for i in fields
        ):
            warnings.append(
                "NaN/inf eksik sayılmaz; null desenlerinden ayrı, veri kalitesinde incelenmelidir."
            )
        patterns = (
            mask.group_by(fields)
            .len()
            .sort(["len", *fields], descending=[True] + [False] * len(fields))
        )
        if patterns.height > 1024:
            raise ProjectError("Eksiklik deseni1024 sınırını aştı; sütunları daraltın.")
        data = dict(
            patterns=patterns.to_dicts(),
            column_missing={i: mask[i].sum() for i in fields},
            mechanism_detected=None,
        )
        details = identity.hstack(
            mask.rename({i: "missing_" + str(j) for j, i in enumerate(fields)})
        )
    elif spec.method.startswith("sample_"):
        indices = []
        groups = []
        if {"row_id", "source_record_id"} & set(frame.columns):
            raise ProjectError(
                "Örnek çıktı için row_id/source_record_id adları ayrılmış; kullanıcı sütunlarını açık rename ile değiştirin."
            )
        if spec.method == "sample_random":
            if spec.sample_size > count:
                raise ProjectError(
                    "Örnek sayısı kapsamı aşıyor; yerine koymadan örnekleme."
                )
            indices = rng.choice(count, spec.sample_size, replace=False).tolist()
            groups = [
                dict(
                    population_n=count,
                    selected_n=spec.sample_size,
                    inclusion_probability=spec.sample_size / count,
                )
            ]
        else:
            labels = frame[names[spec.group]].to_list()
            buckets = {}
            for i, label in enumerate(labels):
                buckets.setdefault(label, []).append(i)
            ordered = sorted(buckets, key=lambda v: (type(v).__name__, str(v)))
            if spec.method == "sample_stratified":
                for label in ordered:
                    control.check()
                    b = buckets[label]
                    if spec.sample_size > len(b):
                        raise ProjectError(
                            "Strata örnek sayısı en küçük stratayı aşıyor; sessiz daraltma yok."
                        )
                    indices += rng.choice(b, spec.sample_size, replace=False).tolist()
                    groups.append(
                        dict(
                            label=str(label),
                            population_n=len(b),
                            selected_n=spec.sample_size,
                            inclusion_probability=spec.sample_size / len(b),
                        )
                    )
            else:
                if spec.sample_size > len(ordered):
                    raise ProjectError("Seçilecek küme sayısı mevcut kümeleri aşıyor.")
                selected = rng.choice(len(ordered), spec.sample_size, replace=False)
                for j in selected:
                    indices += buckets[ordered[j]]
                    groups.append(
                        dict(
                            label=str(ordered[j]),
                            selected_n=len(buckets[ordered[j]]),
                            inclusion_probability=spec.sample_size / len(ordered),
                        )
                    )
        indices = sorted(indices)
        details = frame[indices].rename(
            {"__vu_row_id": "row_id", sourcecol: "source_record_id"}
        )
        rowids = [rowids[i] for i in indices]
        info.update(
            used_rows=len(indices), excluded_rows=count - len(indices), n=[len(indices)]
        )
        data = dict(
            seed=spec.seed,
            replace=False,
            selected_row_ids=rowids,
            groups=groups,
            representation_guaranteed=False,
        )
    elif spec.method.startswith("mi_"):
        missing = np.isnan(matrix)
        if not missing[:, 0].any():
            warnings.append(
                "Ölçüm alanı tam gözlendi; yalnız yardımcı özellikler doldurulur. Seçilen delta ölçümü değiştirmez."
            )
        if not missing.any():
            raise ProjectError(
                "MI için en az bir null alan gerekli; tek tam veri analizi kullanın."
            )
        if any((~missing[:, j]).sum() < 3 for j in range(matrix.shape[1])):
            raise ProjectError("Her MI sayısal alanı en az3 gözlenen değer ister.")
        if spec.method == "mi_mean" and matrix.shape[1] < 2:
            raise ProjectError(
                "Posterior MI için ölçüme ek en az bir yardımcı sayısal özellik seçin."
            )
        draws = []
        estimates = {str(delta): [] for delta in spec.deltas}
        covariances = {str(delta): [] for delta in spec.deltas}
        seeds = rng.choice(2**32 - 1, spec.imputations, replace=False).tolist()
        for k, seed in enumerate(seeds):
            control.check()
            control.progress("Çoklu imputasyon realizasyonu", k, spec.imputations)
            filled = IterativeImputer(
                random_state=seed, sample_posterior=True, max_iter=spec.iterations
            ).fit_transform(matrix)
            if not np.isfinite(filled).all() or not np.array_equal(
                filled[~missing], matrix[~missing]
            ):
                raise ProjectError("MI gözlenen hücre/sonluluk doğrulaması başarısız.")
            draws.append(
                identity.with_columns(
                    pl.lit(k + 1).alias("imputation"),
                    *[
                        pl.Series("value_" + str(j), filled[:, j])
                        for j in range(matrix.shape[1])
                    ],
                    *[
                        pl.Series("missing_" + str(j), missing[:, j])
                        for j in range(matrix.shape[1])
                    ],
                )
            )
            for delta in spec.deltas:
                # Delta is in x's original unit; only originally missing x cells move.
                shifted = filled.copy()
                shifted[missing[:, 0], 0] += delta
                if spec.method == "mi_mean":
                    q = np.array([shifted[:, 0].mean()])
                    u = np.array([[shifted[:, 0].var(ddof=1) / count]])
                    df = count - 1
                else:
                    q, u, df = fit_ols(shifted[:, 0], shifted[:, 1:])
                estimates[str(delta)].append(q.tolist())
                covariances[str(delta)].append(u.tolist())
        scenarios = []
        for delta in spec.deltas:
            pooled = rubin_pool(
                estimates[str(delta)], covariances[str(delta)], df, spec.confidence
            )
            scenarios.append(dict(delta=delta, **pooled))
        baseline = next(s for s in scenarios if s["delta"] == 0)
        details = pl.concat(draws)
        data = dict(
            imputation_kind="multiple",
            imputations=spec.imputations,
            realization_seeds=seeds,
            assumption=spec.missing_assumption,
            mechanism_detected=None,
            model="mean" if spec.method == "mi_mean" else "OLS",
            parameter_names=[spec.x]
            if spec.method == "mi_mean"
            else ["intercept", *spec.features],
            per_imputation_estimates=estimates["0.0"]
            if "0.0" in estimates
            else estimates["0"],
            per_imputation_covariances=covariances["0.0"]
            if "0.0" in covariances
            else covariances["0"],
            scenarios=scenarios,
            delta_target=spec.x,
            delta_unit=spec.unit,
            delta_policy="originally missing x cells only; fixed posterior draws across sensitivity scenarios",
            fit_scope="inferential selected sample, not predictive CV",
            pooling_supported_models=["normal-theory mean", "full-rank OLS"],
            predictive_validation=False,
        )
        primary.update(
            statistic=baseline["estimates"][0],
            p_value=baseline["p_values"][0],
            effect=dict(
                name="MI havuzlanmış " + data["parameter_names"][0],
                value=baseline["estimates"][0],
                confidence_interval=dict(
                    low=baseline["confidence_intervals"][0][0],
                    high=baseline["confidence_intervals"][0][1],
                    confidence=spec.confidence,
                ),
            ),
        )
        warnings.append(
            "Gaussian conditional posterior varsayımı; dağılım ve imputasyon yakınsaması insan tarafından incelenmeli. MI p-değerlerini/prediction'ları ortalamaz; kategorik, bounded/discrete, survey/weighted MI ve diğer modeller desteklenmez."
        )
    elif spec.method == "survey_mean":
        data = survey_mean(
            x,
            weights,
            frame[names[spec.strata]].to_list(),
            frame[names[spec.psu]].to_list(),
            spec.confidence,
        )
    elif spec.method == "weighted_mean":
        mean = float(np.dot(x, weights) / weights.sum())
        if spec.weight_type == "frequency":
            n = float(weights.sum())
            if n <= 1:
                raise ProjectError("Frekans çıkarımı toplam tekrar sayısı>1 ister.")
            variance = float(np.dot(weights, (x - mean) ** 2) / (n - 1) / n)
            df = n - 1
        else:
            # WLS intercept: weights are relative inverse variances.
            _, cov, df = fit_ols(x, np.empty((count, 0)), weights)
            variance = float(cov[0, 0])
        margin = float(stats.t.ppf((1 + spec.confidence) / 2, df)) * math.sqrt(variance)
        data = dict(
            estimate=mean,
            variance=variance,
            standard_error=math.sqrt(variance),
            df=df,
            confidence_interval=[mean - margin, mean + margin],
            weight_type=spec.weight_type,
            interpretation="independent replicated observations"
            if spec.weight_type == "frequency"
            else "relative inverse-variance normal WLS intercept; residual scale estimated",
            design_corrected=False,
        )
    else:
        beta, cov, df = fit_ols(
            x, matrix[:, 1:], weights, inference=spec.method != "weighted_fit"
        )
        data = dict(
            estimates=beta.tolist(),
            parameter_names=["intercept", *spec.features],
            weight_type=spec.weight_type,
            df=df if spec.method != "weighted_fit" else None,
            inference=spec.method != "weighted_fit",
            covariance=None if cov is None else cov.tolist(),
        )
        if cov is not None:
            se = np.sqrt(np.diag(cov))
            margin = stats.t.ppf((1 + spec.confidence) / 2, df) * se
            data.update(
                standard_errors=se.tolist(),
                confidence_intervals=np.column_stack(
                    [beta - margin, beta + margin]
                ).tolist(),
            )
        else:
            warnings.append(
                "sample_weight yalnız kayıp fonksiyonundaki katkıdır; bu fit survey çıkarımı/SE/CI/CV değerlendirmesi değildir."
            )
    if "estimate" in data:
        ci = data.get("confidence_interval")
        primary["effect"] = dict(
            name=LABELS[spec.method],
            value=data["estimate"],
            confidence_interval=dict(low=ci[0], high=ci[1], confidence=spec.confidence)
            if ci
            else None,
        )
        primary["statistic"] = data["estimate"]
    checked(request, control)
    from veri_ufku.domain.capabilities import get_capability

    cap = get_capability("statistics." + spec.method.replace("_", "-"))
    result = dict(
        info,
        primary=primary,
        advanced=data,
        comparisons=[],
        result_version="analysis:" + uid(),
        method_version=cap.semantic_version,
        parameter_version=cap.version,
        correction=dict(
            method="none",
            family="single analysis; marginal MI coefficients",
            family_size=1,
            scope="this run only",
            ci_adjusted=False,
        ),
        provenance=dict(
            array_source=request.get("format_metadata", {}),
            snapshot_fingerprint=request["fingerprint"],
            snapshot_uri=request["snapshot_uri"],
            source_snapshot_id=request["source_snapshot_id"],
            schema="AnalysisResult/v1",
            backend="numpy/scipy/sklearn",
            numpy_version=np.__version__,
            help_content_version=49,
            seed=spec.seed,
            source_record_ids_preserved=True,
            fit_scope="inferential selected sample"
            if spec.method.startswith("mi_")
            else None,
        ),
    )
    directory = Path(workspace)
    membership = directory / "analysis-members.parquet"
    pl.DataFrame({"row_id": rowids}, schema={"row_id": pl.String}).write_parquet(
        membership
    )
    artifact = directory / "analysis-details.parquet"
    details.write_parquet(artifact)
    destination = directory / "analysis-result.json"
    destination.write_text(
        json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )
    result["paths"] = dict(
        result=str(destination), members=str(membership), details=str(artifact)
    )
    result["fingerprints"] = {
        k: hash_artifact(Path(v), control) for k, v in result["paths"].items()
    }
    result["member_digest"] = hashlib.sha256("\n".join(rowids).encode()).hexdigest()
    control.disk(directory)
    control.check()
    return result


def verify_details(path, spec, result, details, members):
    """Parent checks immutable source identities, sampled values and MI pooling."""
    source = pl.read_parquet(path)
    ids = source.select(
        pl.col("__vu_row_id").alias("row_id"),
        pl.col("__vu_source_record_id").alias("source_record_id"),
    )
    if (
        not {"row_id", "source_record_id"} <= set(details.columns)
        or details.select("row_id", "source_record_id")
        .join(ids, on=["row_id", "source_record_id"], how="anti")
        .height
    ):
        raise ProjectError("İleri çıktı kaynak kayıt kimliği uyuşmuyor.")
    if set(details["row_id"]) != set(members["row_id"]):
        raise ProjectError("İleri çıktı ve RowId üyeliği farklı.")
    if spec.method.startswith("mi_"):
        if details.height != len(members) * spec.imputations or sorted(
            details["imputation"].unique()
        ) != list(range(1, spec.imputations + 1)):
            raise ProjectError("MI realizasyon üyeliği/sayısı geçersiz.")
        names = {c["id"]: c["name"] for c in result["source_columns"]}
        originals = source.filter(
            pl.col("__vu_row_id").is_in(members["row_id"].implode())
        )
        expected = originals.select(
            "__vu_row_id", *[names[i] for i in [spec.x, *spec.features]]
        )
        qs, us = [], []
        for k in range(1, spec.imputations + 1):
            draw = details.filter(pl.col("imputation") == k)
            if draw["row_id"].n_unique() != len(members):
                raise ProjectError("MI realizasyonunda yinelenen/eksik RowId.")
            aligned = draw.join(
                expected, left_on="row_id", right_on="__vu_row_id", how="left"
            )
            matrix = np.column_stack(
                [
                    aligned["value_" + str(j)].to_numpy()
                    for j in range(len(spec.features) + 1)
                ]
            )
            for j, ident in enumerate([spec.x, *spec.features]):
                mask = aligned[names[ident]].is_null().to_numpy()
                if not np.array_equal(
                    mask, aligned["missing_" + str(j)].to_numpy()
                ) or not np.array_equal(
                    matrix[~mask, j], aligned[names[ident]].to_numpy()[~mask]
                ):
                    raise ProjectError(
                        "MI özgün gözlenen hücre/eksiklik maskesi değişti."
                    )
            if not np.isfinite(matrix).all():
                raise ProjectError("MI realizasyon değeri sonlu değil.")
            if spec.method == "mi_mean":
                q = np.array([matrix[:, 0].mean()])
                u = np.array([[matrix[:, 0].var(ddof=1) / len(matrix)]])
                df = len(matrix) - 1
            else:
                q, u, df = fit_ols(matrix[:, 0], matrix[:, 1:])
            qs.append(q.tolist())
            us.append(u.tolist())
        data = result["advanced"]
        if not np.allclose(
            qs, data["per_imputation_estimates"], rtol=1e-10, atol=1e-12
        ) or not np.allclose(
            us, data["per_imputation_covariances"], rtol=1e-10, atol=1e-12
        ):
            raise ProjectError("MI realizasyon/katsayı/kovaryans bağı uyuşmuyor.")
        baseline = next(s for s in data["scenarios"] if s["delta"] == 0)
        pooled = rubin_pool(qs, us, df, spec.confidence)
        for key in (
            "estimates",
            "total_covariance",
            "standard_errors",
            "df",
            "confidence_intervals",
        ):
            if not np.allclose(pooled[key], baseline[key], rtol=1e-10, atol=1e-12):
                raise ProjectError("MI Rubin havuzlama çıktısı uyuşmuyor.")
    elif details.height != len(members) or details["row_id"].n_unique() != len(members):
        raise ProjectError("İleri çıktı RowId sayımı geçersiz.")
    if spec.method.startswith("sample_"):
        expected = source.filter(
            pl.col("__vu_row_id").is_in(members["row_id"].implode())
        ).rename({"__vu_row_id": "row_id", "__vu_source_record_id": "source_record_id"})
        if (
            not details.sort("row_id").equals(expected.sort("row_id"))
            or result["advanced"]["selected_row_ids"] != members["row_id"].to_list()
        ):
            raise ProjectError("Örneklem çıktısı kaynak satırlarını değiştirdi.")
