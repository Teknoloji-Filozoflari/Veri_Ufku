"""Bounded descriptive distributions; immutable members and explicit inferential intervals."""

import bisect
import math
from collections import defaultdict

import numpy as np
from scipy import stats

from veri_ufku.storage.project_model import ProjectError


def enabled(spec):
    from veri_ufku.charts.contracts import DISTRIBUTION_KINDS

    return (
        spec.kind in DISTRIBUTION_KINDS
        or spec.kind in ("histogram", "box")
        and (
            spec.group
            or spec.facet
            or spec.weight
            or spec.normalization != "count"
            or spec.category_order
        )
    )


def labels(vals, default=""):
    occupied, identities, result = set(), {}, []
    for value in vals:
        identity = (type(value).__name__, str(value))
        if identity not in identities:
            label = "Eksik kategori (null)" if value is None else str(value)
            original, suffix = label, 1
            while label in occupied:
                suffix += 1
                label = f"{original} [{suffix}]"
            identities[identity] = label
            occupied.add(label)
        result.append(identities[identity])
    return result or [default]


def calculate(spec, values, numbers, add, used, details, warnings, control):
    groups = labels(values[spec.group]) if spec.group else [""] * used
    facets = labels(values[spec.facet]) if spec.facet else [""] * used
    facet_order = list(dict.fromkeys(facets))
    order = list(dict.fromkeys(groups))
    if spec.category_order:
        if set(spec.category_order) != set(order):
            raise ProjectError(
                "Kategorik sıra kullanılan grup etiketlerinin tümünü içermeli."
            )
        order = list(spec.category_order)
    if len(facet_order) > 4 or len(order) > spec.top_n:
        raise ProjectError(
            "Facet en fazla4, grup açık top-N sınırında olmalı; sessiz birleştirme yok."
        )
    w = numbers(spec.weight) if spec.weight else [1.0] * used
    if any(v is None or v < 0 or not math.isfinite(v) for v in w):
        raise ProjectError(
            "Ağırlık eksik, negatif veya sonlu değil; kayıtlar sessizce atılmaz."
        )
    if spec.weight_type == "frequency" and any(v != int(v) or v > 1e9 for v in w):
        raise ProjectError("Frekans ağırlığı en fazla1e9 olan tam sayı olmalı.")
    x = (
        numbers(spec.x)
        if spec.kind != "missing-pattern" and spec.kind != "error-bar"
        else None
    )
    y = numbers(spec.y) if spec.kind in ("error-bar", "ci-band") else None
    buckets = defaultdict(list)
    for i in range(used):
        if spec.kind == "missing-pattern":
            pattern = tuple(values[c][i] is None for c in spec.columns)
            buckets[(facets[i], groups[i], pattern)].append(i)
        elif spec.kind in ("error-bar", "ci-band"):
            xv = values[spec.x][i]
            if (
                xv is not None
                and y[i] is not None
                and (not isinstance(xv, float) or math.isfinite(xv))
            ):
                buckets[(facets[i], groups[i], xv)].append(i)
        elif x[i] is not None and w[i] > 0:
            buckets[(facets[i], groups[i], None)].append(i)
    included = {i for m in buckets.values() for i in m}
    if not included:
        raise ProjectError("Sonlu pozitif ağırlıklı dağılım örneği yok.")
    if spec.kind == "swarm" and len(included) > min(500, spec.point_limit):
        raise ProjectError(
            "Swarm en fazla500 gözlem; açık filtre/örneklem veya strip seçin."
        )
    if (
        spec.kind in ("strip", "rug", "qq", "pp", "ecdf")
        and len(included) > spec.point_limit
    ):
        raise ProjectError("Grafik nokta sınırı aşıldı; açık filtre/örneklem seçin.")
    if spec.kind in ("kde", "violin") and (
        len(included) > 5000 or len(included) * 128 * 96 > control.budget.ram_bytes // 2
    ):
        raise ProjectError(
            "Yoğunluk en fazla5000 örnek ve bütçe içinde; açık örneklem seçin."
        )
    if len(buckets) > spec.point_limit:
        raise ProjectError("Grup/desen sayısı nokta sınırını aşıyor.")
    details.update(
        distribution_version=1,
        group_order=order,
        facets=facet_order,
        normalization=spec.normalization
        if spec.kind == "histogram"
        else "density"
        if spec.kind in ("kde", "violin")
        else "cumulative probability"
        if spec.kind == "ecdf"
        else "none",
        weight_type=spec.weight_type,
        weight_column=spec.weight,
        excluded_rows=used - len(included),
        zero_weight_rows=sum(v == 0 for v in w),
        included_n=len(included),
        aggregation="mean" if y is not None else "distribution",
        samples=[],
        bin_rule="left closed/right open; final right closed",
        uncertainty=spec.uncertainty if y is not None else "none",
    )
    if spec.kind == "violin":
        details["violin_width_normalization"] = (
            "each facet/group peak density scaled to half-width 0.35; not sample count"
        )
    # Common bins across every group/facet make panel heights comparable.
    if spec.kind == "histogram":
        lo, hi = min(x[i] for i in included), max(x[i] for i in included)
        if lo == hi:
            lo, hi = lo - 0.5, hi + 0.5
        boundaries = np.linspace(lo, hi, spec.bins + 1).tolist()
        width = (hi - lo) / spec.bins
        if not math.isfinite(width) or width <= 0:
            raise ProjectError("Histogram aralığı çizim hassasiyetine sığmıyor.")
        details.update(
            bin_edges=boundaries, normalization_scope="within each facet/group"
        )
    category_x = {}
    for (facet, group, key), members in sorted(
        buckets.items(),
        key=lambda pair: (
            facet_order.index(pair[0][0]),
            order.index(pair[0][1]),
            str(pair[0][2]),
        ),
    ):
        control.check()
        vals = [x[i] for i in members] if x is not None else []
        weights = [w[i] for i in members]
        total = math.fsum(weights)
        if not math.isfinite(total) or total <= 0:
            raise ProjectError("Ağırlık toplamı sonlu ve pozitif olmalı.")
        effective = (
            total
            if spec.weight_type == "frequency"
            else total**2 / math.fsum(v * v for v in weights)
        )
        sample = dict(
            facet=facet,
            group=group,
            key=str(key),
            n=len(members),
            weight_sum=total,
            effective_n=effective,
        )
        details["samples"].append(sample)
        extras = dict(facet=facet, group=group, weight_sum=total)
        pos = order.index(group)
        if spec.kind == "histogram":
            bins = [[] for _ in range(spec.bins)]
            for i in members:
                bins[
                    min(
                        spec.bins - 1, max(0, bisect.bisect_right(boundaries, x[i]) - 1)
                    )
                ].append(i)
            for j, m in enumerate(bins):
                mass = math.fsum(w[i] for i in m)
                height = (
                    mass
                    if spec.normalization == "count"
                    else mass / total / width
                    if spec.normalization == "density"
                    else mass / total * (100 if spec.normalization == "percent" else 1)
                )
                add(
                    (boundaries[j] + boundaries[j + 1]) / 2,
                    height,
                    m,
                    left=boundaries[j],
                    right=boundaries[j + 1],
                    **extras,
                )
        elif spec.kind == "box":
            ordered = sorted(members, key=lambda i: x[i])
            cumulative = np.cumsum([w[i] for i in ordered]).tolist()

            def q(prob):
                if spec.weight_type in ("none", "frequency"):
                    h = (total - 1) * prob
                    a, b = math.floor(h), math.ceil(h)
                    va, vb = (
                        x[
                            ordered[
                                min(
                                    len(ordered) - 1,
                                    bisect.bisect_right(cumulative, rank),
                                )
                            ]
                        ]
                        for rank in (a, b)
                    )
                    return va + (vb - va) * (h - a)
                return x[
                    ordered[
                        min(
                            len(ordered) - 1,
                            bisect.bisect_left(cumulative, prob * total),
                        )
                    ]
                ]

            q1, med, q3 = (q(p) for p in (0.25, 0.5, 0.75))
            inliers = [
                v for v in vals if q1 - 1.5 * (q3 - q1) <= v <= q3 + 1.5 * (q3 - q1)
            ]
            fliers = [v for v in vals if v not in inliers]
            add(
                pos,
                med,
                members,
                group or "Dağılım",
                q1=q1,
                q3=q3,
                whislo=min(inliers),
                whishi=max(inliers),
                fliers=fliers[:1000],
                fliers_total=len(fliers),
                **extras,
            )
            sample["quantile_method"] = (
                "replicated frequency linear h=(W-1)*q"
                if spec.weight_type != "analytic"
                else "weighted inverse CDF"
            )
            if len(fliers) > 1000:
                warnings.append(
                    "İlk1000 aykırı işaret çizildi; tam sayı metadata içinde."
                )
        elif spec.kind in ("kde", "violin"):
            mean = math.fsum(v * a / total for v, a in zip(vals, weights))
            denom = (
                total - 1
                if spec.weight_type == "frequency"
                else total - math.fsum(a * a for a in weights) / total
            )
            if len(vals) < 3 or denom <= 0 or min(vals) == max(vals):
                raise ProjectError(
                    "KDE/violin en az3 sonlu ve değişken gözlem ister; sabit örneğe yoğunluk uydurulmaz."
                )
            variance = (
                math.fsum(a * (v - mean) ** 2 for v, a in zip(vals, weights)) / denom
            )
            factor = (
                effective ** (-1 / 5)
                * ((4 / 3) ** (1 / 5) if spec.bandwidth == "silverman" else 1)
                * spec.bandwidth_factor
            )
            bandwidth = math.sqrt(variance) * factor
            if not math.isfinite(bandwidth) or bandwidth <= 0:
                raise ProjectError("KDE bandwidth sonlu pozitif aralıkta değil.")
            grid = np.linspace(
                min(vals) - 3 * bandwidth, max(vals) + 3 * bandwidth, 128
            )
            sample.update(
                bandwidth=bandwidth,
                bandwidth_rule=spec.bandwidth,
                bandwidth_factor=factor,
                kernel="Gaussian",
                grid_points=128,
                tail_cut="observed range ±3 bandwidth; no renormalization",
            )
            for value in grid:
                control.check()
                density = float(
                    np.dot(
                        np.asarray(weights) / total,
                        stats.norm.pdf((value - np.asarray(vals)) / bandwidth),
                    )
                    / bandwidth
                )
                add(
                    value if spec.kind == "kde" else pos,
                    density if spec.kind == "kde" else value,
                    members,
                    density=density,
                    **extras,
                )
        elif spec.kind == "ecdf":
            tied = defaultdict(list)
            for i in members:
                tied[x[i]].append(i)
            cumulative = 0
            for value, m in sorted(tied.items()):
                cumulative += math.fsum(w[i] for i in m)
                add(value, cumulative / total, m, **extras)
            sample["tie_policy"] = (
                "right-continuous; equal values combined; membership is jump contributors"
            )
        elif spec.kind in ("qq", "pp"):
            if len(vals) < 2 or min(vals) == max(vals):
                raise ProjectError(
                    "QQ/PP en az2 değişken gözlem ister; sabit dağılım tanımsız."
                )
            mean, sd = float(np.mean(vals)), float(np.std(vals, ddof=1))
            sample.update(
                reference="normal fitted sample mean/SD(ddof=1)",
                mean=mean,
                sd=sd,
                plotting_position="(i+0.5)/n; no normality test",
            )
            for rank, i in enumerate(sorted(members, key=lambda i: x[i])):
                prob = (rank + 0.5) / len(members)
                add(
                    float(stats.norm.ppf(prob))
                    if spec.kind == "qq"
                    else float(stats.norm.cdf((x[i] - mean) / sd)),
                    x[i] if spec.kind == "qq" else prob,
                    [i],
                    **extras,
                )
        elif spec.kind in ("strip", "swarm", "rug"):
            if spec.kind == "swarm":
                # Bounded lane placement in measurement space; positions saved, never recomputed by renderer.
                span = max(vals) - min(vals) or 1
                placed = []
            for rank, i in enumerate(sorted(members, key=lambda i: x[i])):
                offset = ((rank * 0.61803398875) % 1 - 0.5) * 0.5
                if spec.kind == "swarm":
                    candidates = [0] + [
                        sign * lane * 0.035 for lane in range(1, 11) for sign in (1, -1)
                    ]
                    valid = [
                        d
                        for d in candidates
                        if all(
                            abs(x[i] - v) > span * 0.025 or abs(d - o) >= 0.034
                            for v, o in placed
                        )
                    ]
                    if not valid:
                        raise ProjectError(
                            "Swarm çakışma bütçesi doldu; strip veya açık örneklem seçin."
                        )
                    offset = valid[0]
                    placed.append((x[i], offset))
                add(
                    x[i] if spec.kind == "rug" else pos + offset,
                    pos if spec.kind == "rug" else x[i],
                    [i],
                    original_value=x[i],
                    **extras,
                )
            sample["placement"] = (
                "bounded measurement-space lanes"
                if spec.kind == "swarm"
                else "deterministic golden-ratio strip jitter"
                if spec.kind == "strip"
                else "observed values; no jitter"
            )
        elif spec.kind in ("error-bar", "ci-band"):
            data = [y[i] for i in members]
            n = len(data)
            if n < 2:
                raise ProjectError(
                    "SD/SE/CI için her hücrede en az2 sonlu gözlem gerekli."
                )
            mean, sd = float(np.mean(data)), float(np.std(data, ddof=1))
            se = sd / math.sqrt(n)
            critical = (
                float(stats.t.ppf((1 + spec.confidence) / 2, n - 1))
                if spec.uncertainty == "ci"
                else 1.0
            )
            radius = sd if spec.uncertainty == "sd" else se * critical
            if spec.kind == "ci-band":
                coordinate = float(key)
            else:
                if str(key) not in category_x:
                    category_x[str(key)] = len(category_x)
                coordinate = category_x[str(key)]
            sample.update(
                estimate=mean,
                sd=sd,
                se=se,
                df=n - 1,
                critical=critical,
                confidence=spec.confidence if spec.uncertainty == "ci" else None,
                method="sample SD(ddof=1)"
                if spec.uncertainty == "sd"
                else "iid mean SE=s/sqrt(n)"
                if spec.uncertainty == "se"
                else "iid Student-t mean CI",
                assumption="independent observations; mean CI requires suitable sampling/distribution; not survey or simultaneous band",
            )
            add(
                coordinate,
                mean,
                members,
                str(key),
                lower=mean - radius,
                upper=mean + radius,
                uncertainty=spec.uncertainty,
                **extras,
            )
        else:
            add(
                len(details["samples"]) - 1,
                len(members),
                members,
                "".join("1" if v else "0" for v in key),
                pattern=list(key),
                **extras,
            )
    if spec.kind in ("error-bar", "ci-band"):
        warnings.append(
            "Belirsizlik: "
            + spec.uncertainty
            + "; bağımsız gözlem varsayımı. CI band noktasal aralıktır; eşzamanlı/survey aralığı değildir."
        )
    if spec.kind == "missing-pattern":
        details["pattern_columns"] = list(spec.columns)
        warnings.append(
            "Desen: 1=null,0=gözlenen; NaN/sonsuz null değildir. Mekanizma bu grafikten belirlenmez."
        )
    if spec.weight:
        warnings.append(
            "Ağırlık: "
            + spec.weight_type
            + "; betimsel dağılım, survey çıkarımı değildir. Sıfır ağırlıklı kayıtlar açıkça dışlanır."
        )
