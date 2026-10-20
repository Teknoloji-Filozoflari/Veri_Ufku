"""Full/filtered calculations with independent point membership; never modify a dataset."""

import bisect
import json
import math
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path

import polars as pl

from veri_ufku.analytics.contracts import ProfileSpec, ViewSpec
from veri_ufku.analytics.dataset import checked, filtered, profile, suggest_role
from veri_ufku.charts.contracts import COMPOSITION_KINDS, MULTIVARIATE_KINDS, ChartSpec
from veri_ufku.charts.distributions import enabled as distribution_enabled
from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.storage.project_model import ProjectError, uid


def finite(v):
    return v is not None and (not isinstance(v, (float, Decimal)) or math.isfinite(v))


def numeric(v, precision, losses):
    if not finite(v):
        return None
    f = float(v)
    if not math.isfinite(f):
        raise ProjectError("Değer sonlu Float64 çizim koordinatına sığmıyor.")
    loss = isinstance(v, (int, Decimal)) and Decimal.from_float(f) != Decimal(v)
    if loss and precision == "reject":
        raise ProjectError(
            "Integer/Decimal çiziminde Float64 hassasiyet kaybı var. Yaklaşık çizime açık izin verin; istatistik özeti kesin kalır."
        )
    losses[0] += int(loss)
    return f


def ranks(values):
    order = sorted(range(len(values)), key=values.__getitem__)
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        for k in range(i, j):
            result[order[k]] = (i + 1 + j) / 2
        i = j
    return result


def correlation(x, y, method):
    if len(x) < 2:
        return None, "En az iki sonlu ortak gözlem gerekli."
    if method == "spearman":
        x, y = ranks(x), ranks(y)

    # Exact Float64 offsets, normalized in Decimal before returning to bounded float.
    # Neither a large common offset nor opposite1e308 values can overflow the moments.
    def centered(values):
        with localcontext() as ctx:
            ctx.prec = 80
            origin = Decimal.from_float(values[0])
            delta = [Decimal.from_float(v) - origin for v in values]
            scale = max(map(abs, delta))
            return [float(v / scale) for v in delta] if scale else [0.0] * len(values)

    x, y = centered(x), centered(y)
    mx, my = math.fsum(x) / len(x), math.fsum(y) / len(y)
    a, b = [v - mx for v in x], [v - my for v in y]
    sx, sy = max(map(abs, a)), max(map(abs, b))
    if not sx or not sy:
        return (
            None,
            "Sabit sütun: varyans sıfır; korelasyon tanımsız (NaN sayı gibi çizilmedi).",
        )
    a, b = [v / sx for v in a], [v / sy for v in b]
    r = math.fsum(u * v for u, v in zip(a, b)) / math.sqrt(
        math.fsum(v * v for v in a) * math.fsum(v * v for v in b)
    )
    return max(-1.0, min(1.0, r)), ""


def quantile(values, q):
    h = (len(values) - 1) * q
    lo = int(h)
    return values[lo] + (values[min(lo + 1, len(values) - 1)] - values[lo]) * (h - lo)


def suggest(columns, schema, semantics, purpose="distribution"):
    result = []
    for c in columns:
        dt = schema[c["name"]]
        role = (
            semantics.get(c["id"], {}).get("role") or suggest_role(c["name"], dt, [])[0]
        )
        if role in ("identifier", "ignored", "text"):
            continue
        kind = (
            "missing"
            if purpose == "quality"
            else "line"
            if dt.is_temporal()
            else "bar"
            if role in ("category", "ordinal")
            else "scatter"
            if purpose == "relationship"
            else "box"
            if purpose == "compare"
            else "histogram"
        )
        result.append(
            dict(
                column_id=c["id"],
                name=c["name"],
                role=role,
                kind=kind,
                reason=f"{c['name']}: {role} rolü / {dt} türü / {purpose} amacı; kullanıcı seçimi gerekir.",
            )
        )
    return result


def calculate(request, spec, workspace, control=None):
    control = control or Control()
    spec = spec if isinstance(spec, ChartSpec) else ChartSpec.from_dict(spec)
    spec.validate(request["columns"])
    from veri_ufku.domain.capabilities import CAPABILITIES

    capability = CAPABILITIES["chart." + spec.kind]
    if spec.weight and not dict(capability.supports).get(
        "weight_" + spec.weight_type, False
    ):
        raise ProjectError("Registry bu grafik/ağırlık türünü desteklemiyor.")
    checked(request, control)
    array_source = None
    if spec.kind.startswith("array-"):
        parts = request.get("format_metadata", {}).get("parts", [])
        array_source = parts[0].get("multidimensional") if len(parts) == 1 else None
        if not array_source or array_source.get("origin") != "verified-array-adapter":
            raise ProjectError(
                "Bu grafik doğrulanmış çok boyutlu kaynak kesiti ister; tablodan tensor çıkarılmaz."
            )
        chosen_names = {c["id"]: c["name"] for c in request["columns"]}
        axes = spec.columns[:2] if spec.kind == "array-heatmap" else (spec.x,)
        axis_dims = []
        for column in axes:
            name = chosen_names[column]
            dimension = (
                name[6:]
                if name.startswith("index_")
                else (
                    array_source["coordinates"]
                    .get(name, {})
                    .get("dimensions", [None])[0]
                )
            )
            if dimension not in array_source["dimensions"] or (
                not name.startswith("index_")
                and array_source["coordinates"][name]["dimensions"] != [dimension]
            ):
                raise ProjectError(
                    "Grafik ekseni tek boyutlu kaynak koordinatı/indeksi olmalı."
                )
            axis_dims.append(dimension)
        measure = spec.columns[2] if spec.kind == "array-heatmap" else spec.y
        if chosen_names[measure] != "value" or len(set(axis_dims)) != len(axis_dims):
            raise ProjectError("Farklı boyut eksenleri ve array ölçümünü seçin.")
        active = {d for d, s in array_source["selection"].items() if len(range(*s)) > 1}
        if active - set(axis_dims) and spec.aggregation == "reject":
            raise ProjectError(
                "Ek boyutlar için açık toplulaştırma seçin veya kesiti daraltın."
            )
        if spec.aggregation not in ("reject", "mean", "sum", "min", "max", "median"):
            raise ProjectError(
                "Array ölçümü için açık toplulaştırma veya yinelenenlerde dur seçin."
            )
        if not array_source["decoded"]:
            raise ProjectError(
                "Array grafiği için fill/scale çözülmüş kesit içe aktarın."
            )
    view = ViewSpec.from_dict(spec.view) if spec.scope != "full" else ViewSpec()
    query, schema, names = filtered(request, view)
    chosen = list(
        dict.fromkeys(
            [
                v
                for v in (
                    spec.x,
                    spec.y,
                    spec.group,
                    spec.facet,
                    spec.weight,
                    spec.size,
                    spec.parent,
                    spec.target,
                    spec.entity,
                    spec.waterfall_role,
                    spec.geometry,
                    spec.geo_measure,
                    spec.geo_denominator,
                    *spec.columns,
                )
                if v
            ]
        )
    )
    for c in chosen:
        if schema[names[c]].is_nested() or schema[names[c]] in (
            pl.Binary,
            pl.Duration,
            pl.Time,
        ):
            raise ProjectError(
                "Bu grafik yalnız skaler sayı, kategori, Date/Datetime destekler; nested/Binary/Duration/Time seçmeyin."
            )
    population = query.select(pl.len()).collect().item()
    if spec.scope == "sample":
        query = query.head(spec.sample_rows)
    used = min(population, spec.sample_rows) if spec.scope == "sample" else population
    # Explicit admission, then process RSS/time/disk enforcement by caller.
    if used * (160 + 40 * len(chosen)) > control.budget.ram_bytes // 2:
        raise ProjectError(
            "Grafik seçili alanları RAM bütçesine sığmıyor. Açık ilk-N kapsamını veya daha az alan seçin."
        )
    if spec.kind.startswith("map-") and used > (
        65536 if spec.kind == "map-raster" else 10000
    ):
        raise ProjectError("Harita feature/cell admission sınırı; collect yapılmadı.")
    if not used:
        raise ProjectError(
            "Seçili veri/filtre kapsamı boş; oran veya grafik uydurulmadı."
        )
    from veri_ufku.charts.multivariate import preflight

    preflight(spec, used, control)
    if spec.kind in COMPOSITION_KINDS:
        from veri_ufku.charts.composition import preflight as composition_preflight

        composition_preflight(spec, used, control)
    control.progress("Grafik verisi", 0, used)
    frame = query.select("__vu_row_id", *[names[c] for c in chosen]).collect(
        engine="streaming"
    )
    control.check()
    values = {c: frame[names[c]].to_list() for c in chosen}
    # Identity and display are distinct: null never merges with a literal label.
    group_labels = {}
    if spec.group:
        native = frame[names[spec.group]]
        keys = (
            native.cast(pl.Int64).to_list()
            if native.dtype.is_temporal()
            else values[spec.group]
        )
        occupied = set()
        for key, value in zip(keys, values[spec.group]):
            identity = (type(key).__name__, str(key))
            if identity not in group_labels:
                label = "Eksik grup (null)" if value is None else str(value)
                original, suffix = label, 1
                while label in occupied:
                    suffix += 1
                    label = f"{original} [{suffix}]"
                group_labels[identity] = label
                occupied.add(label)
        group_values = [group_labels[(type(key).__name__, str(key))] for key in keys]
    else:
        group_values = [""] * used
    if len(group_labels) > spec.top_n:
        raise ProjectError(
            "Legend/grup sayısı açık top-N sınırını aşıyor; grubu filtreleyin. Gruplar sessizce atılmaz."
        )
    if (
        spec.kind == "correlation"
        and used * len(spec.columns) ** 2 * 64 > control.budget.ram_bytes // 2
    ):
        raise ProjectError(
            "Korelasyon çift üyelikleri RAM bütçesini aşıyor; daha az sütun veya açık örneklem seçin."
        )
    ids = frame["__vu_row_id"].to_list()
    losses = [0]
    warnings = []
    for c in chosen:
        role = (
            request.get("semantic_metadata", {}).get(c, {}).get("role")
            or suggest_role(names[c], schema[names[c]], [])[0]
        )
        if role == "identifier":
            warnings.append(
                f"{names[c]} kimlik rolünde; kullanıcı elle seçti. Grafik değeri ölçüm anlamına geldiğini kanıtlamaz."
            )
    points, edges = [], []
    counts = {
        c: dict(
            null=sum(v is None for v in values[c]),
            nan=sum(isinstance(v, float) and math.isnan(v) for v in values[c]),
            positive_infinity=sum(
                isinstance(v, float) and v == math.inf for v in values[c]
            ),
            negative_infinity=sum(
                isinstance(v, float) and v == -math.inf for v in values[c]
            ),
        )
        for c in chosen
    }

    def add(x, y, members, label="", **extras):
        pid = len(points)
        points.append(
            dict(
                point_id=pid,
                x=float(x),
                y=None if y is None else float(y),
                label=label,
                n=len(members),
                **extras,
            )
        )
        edges.extend((pid, ids[i]) for i in members)
        return pid

    def numbers(c):
        if not schema[names[c]].is_numeric():
            raise ProjectError(
                f"{names[c]} sayısal fiziksel türde değil. Önce açık tür dönüşümü uygulayın."
            )
        return [numeric(v, spec.precision, losses) for v in values[c]]

    def aggregate(indices, vals, method):
        valid = [vals[i] for i in indices if vals[i] is not None]
        exact = spec.y and (
            schema[names[spec.y]].is_integer()
            or isinstance(schema[names[spec.y]], pl.Decimal)
        )
        if exact:
            valid = [Decimal(values[spec.y][i]) for i in indices if vals[i] is not None]
        if method == "count":
            return len(indices)
        if not valid:
            return None
        with localcontext() as ctx:
            ctx.prec = 80
            if method == "sum":
                result = sum(valid, Decimal(0)) if exact else math.fsum(valid)
            elif method == "mean":
                result = (
                    sum(valid, Decimal(0)) / len(valid)
                    if exact
                    else math.fsum(v / len(valid) for v in valid)
                )
            elif method == "median":
                ordered = sorted(valid)
                middle = len(ordered) // 2
                result = (
                    ordered[middle]
                    if len(ordered) % 2
                    else (ordered[middle - 1] + ordered[middle]) / 2
                )
            elif method == "min":
                result = min(valid)
            elif method == "max":
                result = max(valid)
            else:
                if len(valid) > 1:
                    raise ProjectError(
                        "Aynı tarih/grup için çok kayıt var; sum/mean/median/min/max toplulaştırmasını açıkça seçin."
                    )
                result = valid[0]
            return numeric(result, spec.precision, losses)

    details = dict(
        exclusions=counts,
        precision_loss_values=0,
        other_categories=0,
        other_rows=0,
        excluded_rows=0,
    )
    if spec.kind in ("map-point", "map-choropleth", "map-density", "map-raster"):
        from veri_ufku.geo.charts import calculate as geo_calculate

        geo_calculate(request, spec, values, numbers, add, used, details, control)
    elif spec.kind == "array-heatmap":
        ax, ay, measure = spec.columns
        xv, yv, zv = numbers(ax), numbers(ay), numbers(measure)
        cells = defaultdict(list)
        for i in range(used):
            if xv[i] is not None and yv[i] is not None:
                cells[(xv[i], yv[i])].append(i)
        if len(cells) > spec.point_limit:
            raise ProjectError(
                "Isı haritası nokta sınırı aşıldı; daha küçük kesit seçin."
            )
        for (cx, cy), indices in sorted(cells.items()):
            valid = [zv[i] for i in indices if zv[i] is not None]
            if spec.aggregation == "reject" and len(indices) > 1:
                raise ProjectError("Yinelenen hücre; açık toplulaştırma seçin.")
            z = (
                None
                if not valid
                else (
                    valid[0]
                    if spec.aggregation == "reject"
                    else math.fsum(v / len(valid) for v in valid)
                    if spec.aggregation == "mean"
                    else math.fsum(valid)
                    if spec.aggregation == "sum"
                    else min(valid)
                    if spec.aggregation == "min"
                    else max(valid)
                    if spec.aggregation == "max"
                    else quantile(sorted(valid), 0.5)
                )
            )
            point = len(points)
            points.append(
                dict(point_id=point, x=cx, y=cy, z=z, n=len(indices), label="")
            )
            edges.extend((point, ids[i]) for i in indices)
        details.update(
            array_source=array_source,
            aggregation=spec.aggregation,
            geometry="coordinate grid; missing cells blank; no interpolation",
        )
    elif spec.kind in COMPOSITION_KINDS:
        from veri_ufku.charts.composition import calculate as composition_calculate

        composition_calculate(
            spec, values, numbers, add, used, details, warnings, control
        )
    elif spec.kind in MULTIVARIATE_KINDS:
        from veri_ufku.charts.multivariate import calculate as multi_calculate

        multi_calculate(spec, values, numbers, add, used, details, warnings, control)
    elif distribution_enabled(spec):
        from veri_ufku.charts.distributions import calculate as distribution_calculate

        distribution_calculate(
            spec, values, numbers, add, used, details, warnings, control
        )
    elif spec.kind == "histogram":
        x = numbers(spec.x)
        valid = [v for v in x if v is not None]
        if not valid:
            raise ProjectError("Histogram için sonlu ölçüm yok.")
        low, high = min(valid), max(valid)
        if low == high:
            low, high = low - 0.5, high + 0.5
        width = (high - low) / spec.bins
        if not math.isfinite(width) or not width:
            raise ProjectError("Histogram aralığı çizim hassasiyetine sığmıyor.")
        boundaries = [low + i * width for i in range(spec.bins + 1)]
        boundaries[-1] = high
        buckets = [[] for _ in range(spec.bins)]
        for i, v in enumerate(x):
            if v is not None:
                buckets[
                    min(spec.bins - 1, max(0, bisect.bisect_right(boundaries, v) - 1))
                ].append(i)
        for i, m in enumerate(buckets):
            add(
                (boundaries[i] + boundaries[i + 1]) / 2,
                len(m),
                m,
                f"[{boundaries[i]:g}, {boundaries[i + 1]:g}{']' if i == spec.bins - 1 else ')'}",
                left=boundaries[i],
                right=boundaries[i + 1],
            )
        details.update(
            bin_edges=boundaries,
            excluded_rows=used - len(valid),
            bin_rule="left closed/right open; final right closed",
        )
    elif spec.kind == "box":
        x = numbers(spec.x)
        groups = defaultdict(list)
        for i, v in enumerate(x):
            if v is not None:
                groups[group_values[i] if spec.group else names[spec.x]].append(i)
        if not groups:
            raise ProjectError("Kutu grafiği için sonlu ölçüm yok.")
        if len(groups) > spec.top_n:
            raise ProjectError(
                "Kutu grup sayısı top-N sınırını aşıyor; grubu filtreleyin. Dağılımlar sessizce birleşmez."
            )
        for label, m in groups.items():
            ordered = sorted(x[i] for i in m)
            q1, med, q3 = (quantile(ordered, q) for q in (0.25, 0.5, 0.75))
            lo, hi = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
            inliers = [v for v in ordered if lo <= v <= hi]
            fliers = [v for v in ordered if v < lo or v > hi]
            add(
                len(points),
                med,
                m,
                label,
                q1=q1,
                q3=q3,
                whislo=min(inliers),
                whishi=max(inliers),
                fliers=fliers[:1000],
                fliers_total=len(fliers),
            )
        details.update(
            quantile_method="linear h=(n-1)*q",
            whisker_rule="most extreme observed within1.5IQR",
            excluded_rows=sum(v is None for v in x),
        )
        if any(p["fliers_total"] > 1000 for p in points):
            warnings.append(
                "Kutu grafiğinde ilk1000 aykırı işaret çizildi; tam aykırı sayısı veri tablosunda. Grup seçimi tüm sonlu üyeleri kapsar."
            )
    elif spec.kind in ("bar", "line", "array-profile"):
        y = numbers(spec.y) if spec.y else [None] * used
        grouped = defaultdict(list)
        temporal = schema[names[spec.x]].is_temporal()
        if spec.kind in ("line", "array-profile") and not (
            temporal or schema[names[spec.x]].is_numeric()
        ):
            raise ProjectError("Çizgi X ekseni sayı veya Date/Datetime olmalı.")
        temporal_keys = (
            frame[names[spec.x]].cast(pl.Int64).to_list() if temporal else None
        )
        for i, v in enumerate(values[spec.x]):
            if spec.kind in ("line", "array-profile") and (
                not finite(v) or y[i] is None
            ):
                continue
            g = group_values[i]
            if isinstance(v, float) and not math.isfinite(v):
                continue
            # Native integer temporal keys preserve ns and timezone equality before rendering.
            key = temporal_keys[i] if temporal else v
            grouped[(g, key)].append(i)
        if len(grouped) > 100000:
            raise ProjectError(
                "Kategori/tarih grup sayısı100.000 sınırını aştı; açık filtre/örneklem seçin."
            )
        ordered = list(grouped.items())
        if spec.kind in ("line", "array-profile"):
            ordered.sort(key=lambda pair: (pair[0][0], pair[0][1]))
            if len(ordered) > spec.point_limit:
                raise ProjectError(
                    "Çizgi nokta sınırı aşıldı; açık filtre/grup veya örneklem seçin."
                )
            warnings.append(
                "Çizgi X değerine göre artan sıralı; aynı tarih/gruptaki ölçümler açık agregasyonla birleşir. Naive zaman UTC sayılmaz; grafik tarih koordinatları yaklaşık, kaynak timezone/ns korunur."
            )
            duplicates = sum(len(m) - 1 for _, m in ordered)
            details.update(
                duplicate_x_rows=duplicates,
                ordering="group then native X ascending",
                aggregation=spec.aggregation,
                timezone=str(schema[names[spec.x]]),
            )
        else:
            other_key = object()
            # Stable count order; top-N considers whole categories, including group branches.
            categories = defaultdict(int)
            for (_, k), m in ordered:
                categories[k] += len(m)
            top = sorted(categories, key=lambda k: -categories[k])[: spec.top_n]
            outside = [pair for pair in ordered if pair[0][1] not in top]
            ordered = [pair for pair in ordered if pair[0][1] in top]
            if outside:
                rest = defaultdict(list)
                for (g, k), m in outside:
                    rest[g].extend(m)
                ordered.extend(((g, other_key), m) for g, m in rest.items())
                details.update(
                    other_categories=len(categories) - len(top),
                    other_rows=sum(len(m) for _, m in outside),
                )
                warnings.append(
                    f"Diğer: {details['other_categories']} kategori / {details['other_rows']} kayıt; hiçbir kayıt sessizce dışlanmadı."
                )
        labels, category_coordinates = [], {}
        for (g, key), m in ordered:
            value = aggregate(m, y, spec.aggregation)
            if spec.kind in ("line", "array-profile") and temporal:
                original = values[spec.x][m[0]]
                # Date/datetime plotted as native ordinal or seconds; formatter carries original label.
                coordinate = float(key) / (
                    86400000000000
                    if isinstance(schema[names[spec.x]], pl.Datetime)
                    and schema[names[spec.x]].time_unit == "ns"
                    else 86400000000
                    if isinstance(schema[names[spec.x]], pl.Datetime)
                    and schema[names[spec.x]].time_unit == "us"
                    else 86400000
                    if isinstance(schema[names[spec.x]], pl.Datetime)
                    else 1
                )
                label = str(original)
            elif spec.kind in ("line", "array-profile"):
                coordinate = numeric(key, spec.precision, losses)
                label = str(key)
            else:
                label = (
                    "Diğer (birleşik)"
                    if key is other_key
                    else "Eksik kategori (null)"
                    if key is None
                    else str(key)
                )
                if key not in category_coordinates:
                    original, suffix = label, 1
                    while label in labels:
                        suffix += 1
                        label = f"{original} [{suffix}]"
                    category_coordinates[key] = len(labels)
                    labels.append(label)
                coordinate = category_coordinates[key]
                label = labels[coordinate]
            add(coordinate, value, m, label, group=g)
        details["excluded_rows"] = used - sum(len(m) for m in grouped.values())
    elif spec.kind == "scatter":
        x, y = numbers(spec.x), numbers(spec.y)
        valid = [i for i in range(used) if x[i] is not None and y[i] is not None]
        if not valid:
            raise ProjectError("Dağılım grafiği için ortak sonlu gözlem yok.")
        details.update(
            valid_pairs=len(valid),
            excluded_rows=used - len(valid),
            sampling_method=spec.scatter_mode,
        )
        if spec.scatter_mode == "grid":
            lowx, highx = min(x[i] for i in valid), max(x[i] for i in valid)
            lowy, highy = min(y[i] for i in valid), max(y[i] for i in valid)
            groups = defaultdict(list)
            for i in valid:
                gx = (
                    min(
                        spec.grid_bins - 1,
                        int((x[i] - lowx) / (highx - lowx) * spec.grid_bins),
                    )
                    if highx > lowx
                    else 0
                )
                gy = (
                    min(
                        spec.grid_bins - 1,
                        int((y[i] - lowy) / (highy - lowy) * spec.grid_bins),
                    )
                    if highy > lowy
                    else 0
                )
                groups[(group_values[i], gx, gy)].append(i)
            if len(groups) > spec.point_limit:
                raise ProjectError(
                    "Grup/ızgara nokta sınırı aşıldı; hücre sayısını azaltın veya açık filtre seçin."
                )
            for m in groups.values():
                add(
                    math.fsum(x[i] / len(m) for i in m),
                    math.fsum(y[i] / len(m) for i in m),
                    m,
                    "Izgara hücresi",
                    group=group_values[m[0]],
                )
            details.update(
                grid_bins=spec.grid_bins, represented_rows=len(valid), omitted_rows=0
            )
            warnings.append(
                "Izgara: her nokta hücredeki tüm sonlu kayıtların ortalama koordinatı; seçim hücrenin tüm üyelerini kapsar."
            )
        else:
            if spec.scatter_mode == "full" and len(valid) > spec.point_limit:
                raise ProjectError(
                    "Tam scatter nokta sınırını aşıyor; örnekleme/ızgara seçin."
                )
            take = min(spec.point_limit, len(valid))
            selected = [valid[i * len(valid) // take] for i in range(take)]
            for i in selected:
                add(
                    x[i],
                    y[i],
                    [i],
                    group=group_values[i],
                )
            details.update(
                represented_rows=take,
                omitted_rows=len(valid) - take,
                selection_expression="finite input positions floor(j*N/K), j=0..K-1",
                seed=None,
            )
            warnings.append(
                f"Scatter {take}/{len(valid)} sonlu kayıt; dışarıda {len(valid) - take}. Sistematik seçim temsil garantisi değildir; seçilen nokta yalnız o RowId'dir."
            )
    elif spec.kind == "correlation":
        nums = {c: numbers(c) for c in spec.columns}
        for a, c in enumerate(spec.columns):
            for b, d in enumerate(spec.columns):
                members = [
                    i
                    for i in range(used)
                    if nums[c][i] is not None and nums[d][i] is not None
                ]
                value, error = correlation(
                    [nums[c][i] for i in members],
                    [nums[d][i] for i in members],
                    spec.correlation,
                )
                add(
                    b,
                    a,
                    members,
                    names[c] + " / " + names[d],
                    coefficient=value,
                    error=error,
                )
        details.update(
            method=spec.correlation,
            labels=[names[c] for c in spec.columns],
            pairwise_finite=True,
        )
        warnings.append(
            "Her hücre kendi ortak sonlu gözlem n'sini kullanır. Korelasyon nedensellik değildir; sabit/n<2 hücre tanımsızdır."
        )
    else:
        for c in spec.columns:
            m = [i for i, v in enumerate(values[c]) if v is None]
            add(
                len(points),
                len(m) / used if used else 0,
                m,
                names[c],
                null_count=len(m),
                population_n=used,
                **counts[c],
            )
        warnings.append(
            "Eksik oranı yalnız null / kullanılan kayıt sayısıdır; NaN ve ±sonsuz ayrı sütun sayımlarıdır. Boş metin null değildir."
        )
    if not points:
        raise ProjectError("Seçili kapsamta çizilebilir kayıt yok.")
    if any(p["y"] is not None and not math.isfinite(p["y"]) for p in points):
        raise ProjectError(
            "Toplulaştırılmış çizim değeri sonlu Float64 aralığını aştı."
        )
    if array_source:
        details.update(array_source=array_source, aggregation=spec.aggregation)
    details.setdefault("normalization", "count" if spec.kind == "histogram" else "none")
    details.setdefault("aggregation", spec.aggregation)
    details.setdefault("included_n", used - details.get("excluded_rows", 0))
    details.update(
        display=dict(
            xscale=spec.xscale,
            yscale=spec.yscale,
            linthresh=spec.linthresh,
            clipped=bool(spec.bounds),
            bounds=list(spec.bounds),
            palette=spec.palette,
            font=spec.font,
            font_size=spec.font_size,
            annotation=spec.annotation,
            export_dpi=spec.dpi,
        )
    )
    details["precision_loss_values"] = losses[0]
    if losses[0]:
        warnings.append(
            f"Açık yaklaşık çizim: {losses[0]} Integer/Decimal değer Float64 koordinatında tam temsil edilmedi. Kaynak ve kesin istatistik özeti değişmez."
        )
    if spec.scope == "sample":
        warnings.append(
            f"İlk-N örneklem: {used}/{population}; kaynak sırası seçildi, temsili örneklem iddiası yok."
        )
    summary = []
    from dataclasses import replace

    for c in list(dict.fromkeys([spec.x, spec.y, *spec.columns])):
        if c and schema[names[c]].is_numeric():
            p = profile(
                request,
                ProfileSpec(
                    c,
                    sample=spec.scope == "sample",
                    target="dataset" if spec.scope == "full" else "view",
                    view=view,
                ),
                workspace,
                Control(
                    control.cancel,
                    control.progress,
                    replace(control.budget, sample_limit_rows=spec.sample_rows)
                    if spec.scope == "sample"
                    else control.budget,
                ),
            )
            summary.append(p)
    root = Path(workspace)
    data = root / "chart-data.parquet"
    members = root / "chart-members.parquet"
    pl.DataFrame(
        {
            "point_id": [p["point_id"] for p in points],
            "x": [p["x"] for p in points],
            "y": [p["y"] for p in points],
            "n": [p["n"] for p in points],
            "label": [p["label"] for p in points],
        }
    ).write_parquet(data)
    pl.DataFrame(
        edges, schema={"point_id": pl.Int64, "row_id": pl.String}, orient="row"
    ).write_parquet(members)
    control.disk(root)
    result = dict(
        schema_version=1,
        result_id="result:" + uid(),
        dataset_version=request["version_id"],
        config_revision=request.get("config_revision", 0),
        spec=spec.data(),
        points=points,
        summary=summary,
        details=details,
        column_labels={c: names[c] for c in chosen},
        warnings=warnings,
        dataset_n=request["row_count"],
        population_n=population,
        used_n=used,
        scope="sample"
        if spec.scope == "sample"
        else "filtered"
        if view.filters
        else "full",
        filters=list(view.filters),
        selection_scope="point membership in immutable chart-members; viewport does not change statistics",
        provenance=dict(
            array_source=request.get("format_metadata", {}),
            method="charts/v1",
            backend="polars/python/Matplotlib Agg",
            dataset_versions=[request["version_id"]],
            snapshot_fingerprint=request["fingerprint"],
            sampling_method="firstN" if spec.scope == "sample" else "none",
            seed=None,
            source_snapshot_ids=[request["source_snapshot_id"]],
        ),
        paths=dict(data=str(data), members=str(members)),
    )
    checked(request, control)
    (root / "chart-result.json").write_text(
        json.dumps(result, ensure_ascii=False, allow_nan=False) + "\n"
    )
    result["paths"]["result"] = str(root / "chart-result.json")
    result["fingerprints"] = {
        k: hash_artifact(v, control) for k, v in result["paths"].items()
    }
    control.progress("Grafik verisi", used, used)
    return result


def select(result, point_ids, row_ids=(), limit=200, page_row_ids=()):
    membership = pl.scan_parquet(result["paths"]["members"])
    if row_ids:
        matches = membership.filter(pl.col("row_id").is_in(list(row_ids)))
        points = matches.select("point_id").unique().collect()["point_id"].to_list()
        return dict(
            point_ids=points,
            row_ids=list(row_ids),
            count=len(row_ids),
            scope="Tablodaki seçili kayıt; kaydı içeren noktalar vurgulanır, grup üyeleri ayrıca seçilmez",
        )
    matches = (
        membership.filter(pl.col("point_id").is_in(point_ids))
        .select("row_id")
        .unique(maintain_order=True)
    )
    count = matches.select(pl.len()).collect().item()
    return dict(
        point_ids=list(point_ids),
        row_ids=matches.head(limit).collect()["row_id"].to_list(),
        page_row_ids=matches.filter(pl.col("row_id").is_in(list(page_row_ids)))
        .collect()["row_id"]
        .to_list(),
        count=count,
        dataset_row_ids=matches.collect()["row_id"].to_list() if count <= 10000 else [],
        chart_result_id=result["result_id"],
        dataset_version=result["dataset_version"],
        shown_limit=limit,
        membership_ref=result["paths"]["members"],
        scope="Seçilen nokta/grupların tüm kayıtları; kimlik listesi ilk200, tablo eşleşmesi görünen sayfada",
    )
