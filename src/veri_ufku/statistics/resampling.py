"""Bounded nonparametric unit resampling, exact null tests and declared families."""

import hashlib
import itertools
import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import polars as pl
import scipy
from scipy import stats
from scipy.special import ndtr, ndtri

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import checked, filtered
from veri_ufku.importers.delimited import hash_artifact
from veri_ufku.statistics.engine import adjusted
from veri_ufku.statistics.resampling_contracts import RESAMPLING_LABELS
from veri_ufku.storage.project_model import ProjectError, uid

CAUTION = "Resampling tasarım varsayımını ispatlamaz. p-değeri nedensellik kanıtı değildir. Filtre/yöntem/aileyi p gördükten sonra seçmek p-hacking yaratır; bütün önceden belirlenmiş duyarlılık sonuçlarını birlikte raporlayın."
MAX_ROWS = 2000
MAX_WORK = 2_000_000
DETAIL_SCHEMA = {
    "kind": pl.String,
    "replicate": pl.Int64,
    "position": pl.Int64,
    "unit_id": pl.String,
    "value": pl.Float64,
}


def statistic(values, name, trim):
    if not len(values) or not np.isfinite(values).all():
        return None
    out = (
        np.mean(values)
        if name == "mean"
        else np.median(values)
        if name == "median"
        else stats.trim_mean(values, trim)
    )
    return float(out) if math.isfinite(float(out)) else None


def load(request, spec, control):
    view = ViewSpec.from_dict(spec.view) if spec.scope == "view" else ViewSpec()
    query, schema, names = filtered(request, view)
    columns = list(
        dict.fromkeys(
            [spec.x]
            + [
                c
                for c in (spec.y, spec.group, spec.key, spec.cluster, spec.time_column)
                if c
            ]
        )
    )
    n = query.select(pl.len()).collect(engine="streaming").item()
    if (
        not n
        or n > MAX_ROWS
        or n * max(1, spec.resamples) > MAX_WORK
        or n * max(1, spec.resamples) * 128 > control.budget.ram_bytes // 2
    ):
        raise ProjectError(
            "Resampling bütçesi: en fazla2000 satır,2000000 satır×tekrar; açık filtre/tekrar seçin, sessiz sample yok."
        )
    for c in columns:
        dtype = schema[names[c]]
        if (
            dtype.is_nested()
            or dtype == pl.Binary
            or isinstance(dtype, pl.Decimal)
            or dtype.is_temporal()
            and c != spec.time_column
        ):
            raise ProjectError(
                "Resampling scalar sayı/kimlik gerektirir; decimal/nested/binary veya ölçümde tarih sessiz dönüştürülmez."
            )
    for c in [spec.x] + ([spec.y] if spec.y else []):
        if not schema[names[c]].is_numeric():
            raise ProjectError("Ölçüm/p-değeri/paired response sayısal olmalı.")
    frame = query.select(
        "__vu_row_id", *[pl.col(names[c]).alias(c) for c in columns]
    ).collect(engine="streaming")
    for c in columns:
        if (
            schema[names[c]].is_integer()
            and frame[c].drop_nulls().len()
            and frame[c].drop_nulls().abs().max() > 2**53
        ):
            raise ProjectError(
                "Float64 ölçüm/kimlik için kayıpsız olmayan büyük integer reddedilir."
            )
    structural = [
        c for c in (spec.group, spec.key, spec.cluster, spec.time_column) if c
    ]
    if (
        structural
        and frame.filter(
            ~pl.all_horizontal(
                [pl.col(c).is_not_null() for c in structural]
                + [
                    pl.col(c).is_finite()
                    for c in structural
                    if schema[names[c]].is_float()
                ]
            )
        ).height
    ):
        raise ProjectError(
            "Label/pair/cluster/time kimliği eksik veya sonlu değil; birim bütünlüğü için sessiz düşürülmez."
        )
    if spec.time_column:
        dtype = schema[names[spec.time_column]]
        if (
            not (dtype.is_numeric() or dtype.is_temporal())
            or frame[spec.time_column].n_unique() != frame.height
        ):
            raise ProjectError(
                "Time block açık numeric/temporal, benzersiz sıralama sütunu ister; duplicate zamanın tie sırası tahmin edilmez."
            )
        frame = frame.sort(spec.time_column)
    return frame, names


def clean_frame(frame, spec):
    cols = [spec.x] + ([spec.y] if spec.y else [])
    valid = pl.all_horizontal(
        [pl.col(c).is_not_null() & pl.col(c).is_finite() for c in cols]
    )
    missing = frame.filter(~valid)
    if missing.height and spec.missing_policy == "reject":
        raise ProjectError(
            "Eksik/NaN/inf ölçüm var; açık complete-case seçin. Eksik mekanizması veriden kanıtlanamaz."
        )
    clean = frame.filter(valid)
    if clean.height < (1 if spec.method.startswith("adjust_") else 3):
        raise ProjectError("En az3 geçerli gözlem/pair/test gerekli.")
    if spec.resampling_unit == "time_block" and missing.height:
        raise ProjectError(
            "Zaman serisinde missing satırı düşürmek sahte bitişiklik üretir; blok resampling tam seri ister."
        )
    if spec.resampling_unit == "cluster" and missing.height:
        raise ProjectError(
            "Grup resampling eksik ölçümlü grubu parçalayamaz; eksiksiz grup kapsamını açık filtreyle seçin."
        )
    return clean, missing.height


def units_for(frame, spec):
    row_ids = frame["__vu_row_id"].to_list()
    if spec.resampling_unit == "cluster":
        labels = [str(v) for v in frame[spec.cluster].to_list()]
        keys = sorted(set(labels))
        if len(keys) < 3:
            raise ProjectError(
                "En az3 bağımsız cluster gerekli; küçük cluster sayısı CI doğruluğunu garanti etmez."
            )
        units = {k: np.flatnonzero(np.asarray(labels) == k) for k in keys}
    elif spec.resampling_unit == "time_block":
        n = frame.height
        L = spec.block_length
        if n < 2 * L:
            raise ProjectError(
                "Moving block için en az2 block uzunluğu gözlem gerekli."
            )
        units = {f"block:{i}": np.arange(i, i + L) for i in range(n - L + 1)}
    else:
        units = {rid: np.array([i]) for i, rid in enumerate(row_ids)}
    return units, {k: [row_ids[i] for i in indexes] for k, indexes in units.items()}


def interval(distribution, observed, spec, jackknife):
    a = (1 - spec.confidence) / 2
    valid = np.asarray([v for v in distribution if v is not None], dtype=float)
    info = dict(
        valid_replicates=len(valid),
        invalid_replicates=len(distribution) - len(valid),
        status="available",
        method="BCa" if spec.method == "bootstrap_bca" else "percentile",
        confidence=spec.confidence,
    )
    if (
        len(valid) != len(distribution)
        or len(np.unique(valid)) < 2
        or np.std(valid) == 0
    ):
        return dict(
            info,
            status="unavailable: missing/nonfinite/constant bootstrap distribution",
            low=None,
            high=None,
            monte_carlo=None,
        )
    probabilities = np.array([a, 1 - a])
    if spec.method == "bootstrap_bca":
        j = np.asarray(jackknife, dtype=float)
        centered = np.mean(j) - j
        den = 6 * np.sum(centered**2) ** 1.5
        # Midrank bias correction makes bootstrap ties explicit.
        bias = (np.sum(valid < observed) + 0.5 * np.sum(valid == observed)) / len(valid)
        if den <= 0 or not np.isfinite(j).all() or not 0 < bias < 1:
            return dict(
                info,
                status="unavailable: degenerate jackknife / bias correction",
                low=None,
                high=None,
                monte_carlo=None,
            )
        acceleration = float(np.sum(centered**3) / den)
        z0 = float(ndtri(bias))
        zs = ndtri(probabilities)
        denom = 1 - acceleration * (z0 + zs)
        if np.any(denom <= 0):
            return dict(
                info,
                status="unavailable: invalid BCa acceleration",
                low=None,
                high=None,
                monte_carlo=None,
            )
        probabilities = ndtr(z0 + (z0 + zs) / denom)
        info.update(
            acceleration=acceleration,
            bias_correction=z0,
            jackknife_units=len(j),
            tie_policy="midrank",
            adjusted_quantiles=probabilities.tolist(),
        )
        if (
            probabilities[0] <= 0
            or probabilities[1] >= 1
            or probabilities[0] >= probabilities[1]
            or probabilities[0] * len(valid) < 5
            or (1 - probabilities[1]) * len(valid) < 5
        ):
            return dict(
                info,
                status="unavailable: BCa tail has fewer than5 resamples",
                low=None,
                high=None,
                monte_carlo=None,
            )
    endpoints = np.quantile(valid, probabilities, method="linear")
    # Order-statistic bands quantify finite Monte Carlo uncertainty in CI endpoints.
    ordered = np.sort(valid)
    bands = []
    for p in probabilities:
        counts = stats.binom.ppf([0.025, 0.975], len(valid), p)
        indexes = np.clip(counts.astype(int), 0, len(valid) - 1)
        bands.append(
            dict(
                probability=float(p),
                low=float(ordered[indexes[0]]),
                high=float(ordered[indexes[1]]),
            )
        )
    return dict(
        info,
        low=float(endpoints[0]),
        high=float(endpoints[1]),
        monte_carlo=dict(
            kind="95% binomial order-statistic endpoint bands; simulation error only, not another data CI",
            endpoint_bands=bands,
        ),
        quantile_method="linear",
    )


def bootstrap(frame, spec, rng, control):
    units, membership = units_for(frame, spec)
    keys = list(units)
    n = frame.height
    y = frame[spec.x].to_numpy()
    observed = statistic(y, spec.statistic, spec.trim_fraction)
    distribution = []
    details = []
    draws = (
        math.ceil(n / spec.block_length)
        if spec.resampling_unit == "time_block"
        else len(keys)
    )
    for b in range(spec.resamples):
        control.check()
        selected = rng.integers(0, len(keys), draws)
        indexes = np.concatenate([units[keys[i]] for i in selected])
        if spec.resampling_unit == "time_block":
            indexes = indexes[:n]
        value = statistic(y[indexes], spec.statistic, spec.trim_fraction)
        distribution.append(value)
        details.append(
            dict(kind="distribution", replicate=b, position=-1, unit_id="", value=value)
        )
        details.extend(
            dict(kind="draw", replicate=b, position=j, unit_id=keys[i], value=None)
            for j, i in enumerate(selected)
        )
        if b % 100 == 0:
            control.progress("Bootstrap", b, spec.resamples)
    jack = []
    if spec.method == "bootstrap_bca":
        for key in keys:
            control.check()
            mask = np.ones(n, dtype=bool)
            mask[units[key]] = False
            jack.append(statistic(y[mask], spec.statistic, spec.trim_fraction))
    ci = interval(distribution, observed, spec, jack)
    return (
        dict(
            estimate=observed,
            confidence_interval=ci,
            unit_members=membership,
            draws_per_replicate=draws,
            unit_count=len(keys),
            resampling="moving overlapping blocks; last concatenated block truncated to original n"
            if spec.resampling_unit == "time_block"
            else "sample independent units with replacement; cluster rows stay intact",
            estimand="pooled observation " + spec.statistic,
            bootstrap_sd=float(np.std(distribution, ddof=1))
            if all(v is not None for v in distribution)
            else None,
        ),
        details,
        None,
    )


def extreme(value, observed, tail):
    # Conservative tie comparison at floating arithmetic resolution.
    tol = 100 * np.finfo(float).eps * max(1.0, abs(observed))
    return (
        abs(value) >= abs(observed) - tol
        if tail == "two-sided"
        else value >= observed - tol
        if tail == "greater"
        else value <= observed + tol
    )


def permutation(frame, spec, rng, control):
    units, membership = units_for(frame, spec)
    keys = list(units)
    y = frame[spec.x].to_numpy()
    if spec.method == "paired_sign_flip":
        if frame[spec.key].n_unique() != frame.height:
            raise ProjectError(
                "Paired wide veri: kişi key benzersiz olmalı; positional/eşleşmemiş çift yok."
            )
        values = frame[spec.y].to_numpy() - y - spec.null_value
        estimates = (
            np.array([np.mean(values[units[k]]) for k in keys])
            if spec.resampling_unit == "cluster"
            else values
        )
        observed = statistic(estimates, spec.statistic, spec.trim_fraction)
        space = 2 ** len(estimates)
        iterator = (
            itertools.product((-1, 1), repeat=len(estimates))
            if space <= 10000
            else (
                rng.choice([-1, 1], size=len(estimates)) for _ in range(spec.resamples)
            )
        )

        def function(sign):
            return statistic(
                estimates * np.asarray(sign), spec.statistic, spec.trim_fraction
            )

        mapping = "independent pair differences / cluster-mean pair differences; one whole-unit sign"
    else:
        labels = np.asarray([str(v) for v in frame[spec.group].to_list()])
        if set(labels) != {spec.before, spec.after}:
            raise ProjectError(
                "Permutation tam iki seçili label ister; diğer label sessiz dışlanmaz."
            )
        unit_labels = []
        estimates = []
        for k in keys:
            local = set(labels[units[k]])
            if len(local) != 1:
                raise ProjectError(
                    "Cluster permutation grup label cluster içinde sabit olmalı; bağımlı satır label shuffle yok."
                )
            unit_labels.append(next(iter(local)))
            estimates.append(np.mean(y[units[k]]))
        estimates = np.asarray(estimates)
        mask = np.asarray(unit_labels) == spec.after
        n1 = int(mask.sum())
        n0 = len(mask) - n1
        if min(n0, n1) < 2:
            raise ProjectError("Her label için en az2 bağımsız birim gerekli.")
        observed = statistic(
            estimates[mask], spec.statistic, spec.trim_fraction
        ) - statistic(estimates[~mask], spec.statistic, spec.trim_fraction)
        space = math.comb(len(estimates), n1)
        iterator = (
            itertools.combinations(range(len(estimates)), n1)
            if space <= 10000
            else (
                tuple(sorted(rng.choice(len(estimates), n1, replace=False)))
                for _ in range(spec.resamples)
            )
        )

        def function(indexes):
            mask = np.zeros(len(estimates), dtype=bool)
            mask[list(indexes)] = True
            return statistic(
                estimates[mask], spec.statistic, spec.trim_fraction
            ) - statistic(estimates[~mask], spec.statistic, spec.trim_fraction)

        mapping = "after−before, exchangeable unit labels with fixed group sizes; cluster means weighted equally"
    if len(estimates) < 3 or (
        np.all(estimates == 0)
        if spec.method == "paired_sign_flip"
        else np.std(estimates) == 0
    ):
        raise ProjectError(
            "Null dağılımını tanımlayacak değişken bağımsız birimler gerekli; sabit ölçüm kabul edilmedi."
        )
    details = []
    hits = 0
    for i, allocation in enumerate(iterator):
        control.check()
        value = function(allocation)
        if value is None:
            raise ProjectError("Eksik/nonfinite null replicate; p üretilmedi.")
        hits += extreme(value, observed, spec.alternative)
        details.append(
            dict(
                kind="null_distribution",
                replicate=i,
                position=-1,
                unit_id=json.dumps([int(v) for v in allocation], separators=(",", ":")),
                value=value,
            )
        )
    m = len(details)
    exact = space <= 10000
    p = hits / m if exact else (hits + 1) / (m + 1)
    mc = None
    if not exact:
        lo = 0.0 if hits == 0 else float(stats.beta.ppf(0.025, hits, m - hits + 1))
        hi = 1.0 if hits == m else float(stats.beta.ppf(0.975, hits + 1, m - hits))
        mc = dict(
            method="Clopper–Pearson95% for uncorrected exceedance probability",
            low=lo,
            high=hi,
            standard_error=math.sqrt((hits / m) * (1 - hits / m) / m),
            p_resolution=1 / (m + 1),
            interval_is_not_effect_ci=True,
        )
    return (
        dict(
            estimate=observed,
            p_value=p,
            null_value=spec.null_value,
            null_hypothesis=spec.hypothesis,
            tail=spec.alternative,
            exact=exact,
            permutation_space=space,
            performed=m,
            extreme_count=int(hits),
            p_algorithm="exhaustive inclusive ties"
            if exact
            else "(extreme+1)/(B+1); independent draws with replacement",
            monte_carlo=mc,
            unit_members=membership,
            unit_count=len(estimates),
            estimand=mapping,
            exchangeability="explicit user design assertion; not verified from p-values",
        ),
        details,
        p,
    )


def robust(values, spec):
    median = float(np.median(values))
    mad = float(stats.median_abs_deviation(values, scale=1.0))
    lo, hi = np.quantile(
        values, [spec.trim_fraction, 1 - spec.trim_fraction], method="linear"
    )
    if spec.outlier_policy == "mad_exclude":
        if mad == 0:
            raise ProjectError(
                "MAD0: outlier sınırı tanımlanamaz; keep veya açık winsor seçin."
            )
        mask = np.abs(values - median) <= 3 * 1.4826 * mad
        used = values[mask]
    elif spec.outlier_policy == "winsorize":
        mask = np.ones(len(values), bool)
        used = np.clip(values, lo, hi)
    else:
        mask = np.ones(len(values), bool)
        used = values
    if len(used) < 3:
        raise ProjectError("Outlier politikası sonrası en az3 değer gerekli.")
    return dict(
        estimate=statistic(used, spec.statistic, spec.trim_fraction),
        mean=float(np.mean(used)),
        median=float(np.median(used)),
        trimmed_mean=float(stats.trim_mean(used, spec.trim_fraction)),
        mad=float(stats.median_abs_deviation(used, scale=1.0)),
        mad_definition="raw median absolute deviation; not SD",
        trim_fraction=spec.trim_fraction,
        outlier_policy=spec.outlier_policy,
        outlier_removed=int((~mask).sum()),
        winsor_bounds=[float(lo), float(hi)]
        if spec.outlier_policy == "winsorize"
        else None,
        original_n=len(values),
        used_n=len(used),
        inference=False,
    ), mask


def family(frame, spec):
    ids = [str(v) for v in frame[spec.key].to_list()]
    if len(set(ids)) != len(ids):
        raise ProjectError(
            "TestID benzersiz olmalı; duplicate hipotez/aile reddedildi."
        )
    lookup = {k: float(v) for k, v in zip(ids, frame[spec.x].to_list())}
    if not set(spec.family_ids) <= set(lookup):
        raise ProjectError("Seçili ailede eksik testID var; aile sessiz küçültülmez.")
    ps = [lookup[k] for k in spec.family_ids]
    if any(not 0 <= p <= 1 for p in ps):
        raise ProjectError("Ailede her p-değeri0–1 aralığında olmalı.")
    method = spec.method.removeprefix("adjust_")
    corrected = adjusted(ps, method)
    return dict(
        name=spec.family_name,
        ids=spec.family_ids,
        size=len(ps),
        method=method,
        dependence=spec.family_dependence,
        error_control="FDR: expected proportion of false discoveries among rejections; independence/PRDS required"
        if method == "bh"
        else "FWER: probability of at least one false rejection in the declared family; arbitrary dependence",
        alpha=1 - spec.confidence,
        tests=[
            dict(test_id=k, p_raw=p, p_adjusted=q, reject=q <= 1 - spec.confidence)
            for k, p, q in zip(spec.family_ids, ps, corrected)
        ],
        outside_family=sorted(set(ids) - set(spec.family_ids)),
        selection="explicit user-selected IDs; valid original p-values/tails assumed; no automatic search across projects",
    )


def sensitivity(request, spec, control, baseline):
    rows = []
    union = set()
    details = []
    definitions = [
        dict(
            name="baseline",
            view=spec.view,
            statistic=spec.statistic,
            outlier_policy=spec.outlier_policy,
            missing_policy=spec.missing_policy,
            missing_assumption=spec.missing_assumption,
            missing_delta=0.0,
        )
    ] + spec.scenarios
    for index, s in enumerate(definitions):
        control.check()
        local = replace(
            spec,
            scope="view" if index else spec.scope,
            view=s["view"],
            statistic=s["statistic"],
            outlier_policy=s["outlier_policy"],
            missing_policy="complete"
            if s["missing_policy"] == "delta"
            else s["missing_policy"],
            scenarios=[],
        )
        frame, _ = load(request, local, control)
        valid = pl.col(spec.x).is_not_null() & pl.col(spec.x).is_finite()
        missing = frame.filter(~valid).height
        if missing and s["missing_policy"] == "reject":
            rows.append(
                dict(
                    name=s["name"],
                    config=s,
                    status="unavailable: missing policy rejects scope",
                    estimate=None,
                    change=None,
                    n=0,
                    missing=missing,
                    imputed=0,
                )
            )
            continue
        if s["missing_policy"] == "delta" and missing:
            observed = frame.filter(valid)[spec.x].to_numpy()
            if len(observed) < 3:
                raise ProjectError(
                    "Delta missing scenario en az3 observed değer ister."
                )
            replacement = float(np.mean(observed) + s["missing_delta"])
            frame = frame.with_columns(
                pl.when(valid)
                .then(pl.col(spec.x))
                .otherwise(pl.lit(replacement))
                .alias(spec.x)
            )
        else:
            frame = frame.filter(valid)
        if frame.height < 3:
            rows.append(
                dict(
                    name=s["name"],
                    config=s,
                    status="unavailable: fewer than3 observations",
                    estimate=None,
                    change=None,
                    n=frame.height,
                    missing=missing,
                    imputed=0,
                )
            )
            continue
        summary, mask = robust(frame[spec.x].to_numpy(), local)
        ids = np.asarray(frame["__vu_row_id"].to_list())[mask].tolist()
        union.update(ids)
        rows.append(
            dict(
                name=s["name"],
                config=s,
                status="descriptive sensitivity only; no hypothesis selection",
                estimate=summary["estimate"],
                change=summary["estimate"] - baseline,
                n=len(ids),
                missing=missing,
                imputed=missing if s["missing_policy"] == "delta" else 0,
                outlier_removed=summary["outlier_removed"],
                row_ids=ids,
            )
        )
        details.extend(
            dict(
                kind="scenario_member",
                replicate=index,
                position=j,
                unit_id=ident,
                value=None,
            )
            for j, ident in enumerate(ids)
        )
    return rows, sorted(union), details


def calculate(request, spec, workspace, control, preflight=False):
    checked(request, control)
    frame, names = load(request, spec, control)
    # Correction families must not silently drop a selected missing p-value.
    if spec.method.startswith("adjust_"):
        ids = [str(v) for v in frame[spec.key].to_list()]
        selected = frame.filter(pl.col(spec.key).cast(pl.String).is_in(spec.family_ids))
        if len(set(ids)) != len(ids):
            raise ProjectError("TestID benzersiz olmalı.")
        if not set(spec.family_ids) <= set(ids):
            raise ProjectError("Seçili test ailesi kapsamda eksik.")
        frame, excluded = clean_frame(selected, replace(spec, missing_policy="reject"))
    else:
        frame, excluded = clean_frame(frame, spec)
    members = frame["__vu_row_id"].to_list()
    units, mapping = units_for(frame, spec)
    info = dict(
        method=spec.method,
        method_label=RESAMPLING_LABELS[spec.method],
        n=[frame.height],
        used_rows=frame.height,
        excluded_rows=excluded,
        warnings=[
            CAUTION,
            f"Eksik varsayımı: {spec.missing_assumption}; complete-case tarafsızlığı otomatik garanti değildir.",
        ],
        resampling=True,
        unit_count=len(units),
        resampling_unit=spec.resampling_unit,
        dependence=spec.dependence,
        unit_members=mapping,
        scope_view=spec.view,
        statistic=spec.statistic,
        null_hypothesis=spec.hypothesis,
        tail=spec.alternative,
        seed=spec.seed,
        requested_replicates=spec.resamples,
    )
    if spec.resampling_unit == "time_block":
        info["warnings"].append(
            "Moving blocks: seri seçili sıralamaya göre durağan/yerel bağımlı kabul edilir; trend/seasonality otomatik giderilmez. Block uzunluğu bilimsel tasarım kararıdır; uç bloklar farklı inclusion probability taşır."
        )
    if spec.method == "paired_sign_flip" and frame[spec.key].n_unique() != frame.height:
        raise ProjectError("Kişi key benzersiz olmalı.")
    if spec.method == "permutation":
        labels = set(map(str, frame[spec.group].to_list()))
        if labels != {spec.before, spec.after}:
            raise ProjectError("Tam iki seçili exchangeable label gerekli.")
        for indexes in units.values():
            if len(set(str(frame[spec.group][int(i)]) for i in indexes)) != 1:
                raise ProjectError("Cluster içinde label sabit olmalı.")
    if preflight:
        return dict(
            info,
            spec=spec.data(),
            dataset_version=request["version_id"],
            config_revision=request.get("config_revision", 0),
        )
    rng = np.random.default_rng(spec.seed)
    details = []
    p = None
    if spec.method.startswith("bootstrap_"):
        info["bootstrap"], details, p = bootstrap(frame, spec, rng, control)
    elif spec.method in ("permutation", "paired_sign_flip"):
        info["permutation"], details, p = permutation(frame, spec, rng, control)
    elif spec.method.startswith("adjust_"):
        info["family"] = family(frame, spec)
        info["family"]["outside_family"] = sorted(set(ids) - set(spec.family_ids))
        details = [
            dict(
                kind="family_p_adjusted",
                replicate=0,
                position=i,
                unit_id=t["test_id"],
                value=t["p_adjusted"],
            )
            for i, t in enumerate(info["family"]["tests"])
        ]
    else:
        summary, mask = robust(frame[spec.x].to_numpy(), spec)
        info["summary"] = summary
        members = np.asarray(members)[mask].tolist()
        details = [
            dict(kind="summary_member", replicate=0, position=i, unit_id=k, value=None)
            for i, k in enumerate(members)
        ]
        if spec.method == "sensitivity":
            info["sensitivity"], members, details = sensitivity(
                request, spec, control, summary["estimate"]
            )
    info["used_rows"] = len(members)
    checked(request, control)
    control.check()
    result = dict(
        info,
        primary=dict(method=spec.method, p_value=p, statistic=None, effect=None),
        spec=spec.data(),
        comparisons=[],
        correction=dict(
            method=spec.method.removeprefix("adjust_")
            if spec.method.startswith("adjust_")
            else "none",
            family=spec.family_name or "single declared analysis",
            family_size=len(spec.family_ids) or 1,
            ci_adjusted=False,
            scope="explicit selected family / this recipe",
        ),
        dataset_version=request["version_id"],
        config_revision=request.get("config_revision", 0),
        result_version="analysis:" + uid(),
        method_version=1,
        parameter_version=1,
        provenance=dict(
            schema="AnalysisResult/v1",
            backend="numpy/scipy explicit-unit adapter",
            numpy_version=np.__version__,
            scipy_version=scipy.__version__,
            snapshot_fingerprint=request["fingerprint"],
            snapshot_uri=request["snapshot_uri"],
            source_snapshot_id=request["source_snapshot_id"],
            seed=spec.seed,
            rng="NumPy Generator PCG64",
            resampling_unit=spec.resampling_unit,
            unit_members_digest=hashlib.sha256(
                json.dumps(mapping, sort_keys=True).encode()
            ).hexdigest(),
            help_content_version=57,
        ),
    )
    directory = Path(workspace)
    membership = directory / "resampling-members.parquet"
    pl.DataFrame({"row_id": members}, schema={"row_id": pl.String}).write_parquet(
        membership
    )
    detailpath = directory / "resampling-details.parquet"
    pl.DataFrame(details, schema=DETAIL_SCHEMA).write_parquet(detailpath)
    verify_details(result, pl.read_parquet(detailpath), pl.read_parquet(membership))
    destination = directory / "resampling-result.json"
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


def verify_details(result, details, members):
    if (
        details.schema != DETAIL_SCHEMA
        or members.columns != ["row_id"]
        or members.height != result["used_rows"]
        or members["row_id"].n_unique() != members.height
    ):
        raise ProjectError("Resampling details / RowId üyeliği uyuşmuyor.")
    spec = result["spec"]
    ids = set(members["row_id"].to_list())
    mapping = result["unit_members"]
    if spec["method"].startswith("bootstrap_"):
        draws = details.filter(pl.col("kind") == "draw")
        distribution = details.filter(pl.col("kind") == "distribution")
        if (
            distribution.height != spec["resamples"]
            or distribution["replicate"].n_unique() != spec["resamples"]
            or not set(draws["unit_id"].to_list()) <= set(mapping)
        ):
            raise ProjectError("Bootstrap seed/tekrar/unit artifact bağı geçersiz.")
        counts = draws.group_by("replicate").len()
        if (
            counts.height != spec["resamples"]
            or set(counts["len"].to_list())
            != {result["bootstrap"]["draws_per_replicate"]}
            or any(not set(v) <= ids for v in mapping.values())
        ):
            raise ProjectError("Bootstrap cluster/block draw üyeliği geçersiz.")
    if spec["method"].startswith("adjust_"):
        if (
            result["family"]["ids"] != spec["family_ids"]
            or result["family"]["name"] != spec["family_name"]
            or details["unit_id"].to_list() != spec["family_ids"]
            or details["value"].to_list()
            != [t["p_adjusted"] for t in result["family"]["tests"]]
        ):
            raise ProjectError("Export/kayıt test ailesi kimliği uyuşmuyor.")


def verify_source(path, columns, result):
    """Bind unit membership and original family p-values to immutable source rows."""
    from veri_ufku.statistics.contracts import AnalysisSpec

    spec = AnalysisSpec.from_dict(result["spec"])
    request = dict(path=str(path), columns=columns)
    view = ViewSpec.from_dict(spec.view) if spec.scope == "view" else ViewSpec()
    query, _, names = filtered(request, view)
    chosen = list(
        dict.fromkeys(
            [spec.x]
            + [
                c
                for c in (spec.y, spec.group, spec.key, spec.cluster, spec.time_column)
                if c
            ]
        )
    )
    frame = query.select(
        "__vu_row_id", *[pl.col(names[c]).alias(c) for c in chosen]
    ).collect(engine="streaming")
    if spec.method.startswith("adjust_"):
        outside = sorted(
            set(str(v) for v in frame[spec.key].to_list()) - set(spec.family_ids)
        )
        frame = frame.filter(pl.col(spec.key).cast(pl.String).is_in(spec.family_ids))
        expected = family(frame, spec)
        expected["outside_family"] = outside
        if expected != result["family"]:
            raise ProjectError(
                "Kaydedilen test ailesi/original p/source bağı uyuşmuyor."
            )
    else:
        frame, _ = clean_frame(frame, spec)
    if spec.time_column:
        frame = frame.sort(spec.time_column)
    _, expected = units_for(frame, spec)
    if expected != result["unit_members"]:
        raise ProjectError(
            "Cluster/block/gözlem kimlik mapping kaynak RowId ile uyuşmuyor."
        )
    digest = hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest()
    if digest != result["provenance"]["unit_members_digest"]:
        raise ProjectError("Resampling birim kimliği hash uyuşmuyor.")
