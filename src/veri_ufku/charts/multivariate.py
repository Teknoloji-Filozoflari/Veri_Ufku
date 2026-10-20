"""Bounded CPU relationships. Every glyph retains immutable source membership."""

import math
from collections import defaultdict

import numpy as np
from scipy.cluster.hierarchy import leaves_list, linkage
from scipy.spatial import cKDTree

from veri_ufku.charts.contracts import MULTIVARIATE_KINDS
from veri_ufku.charts.distributions import labels
from veri_ufku.storage.project_model import ProjectError


def preflight(spec, used, control):
    if spec.kind not in MULTIVARIATE_KINDS:
        return
    panels = len(spec.columns) ** 2 if spec.kind == "pair" else 1
    edges = used * (
        panels
        if spec.kind == "pair"
        else len(spec.columns)
        if spec.kind in ("parallel", "grouped-heatmap", "clustered-heatmap")
        else 1
    )
    if edges * 160 > control.budget.ram_bytes // 2:
        raise ProjectError(
            f"Panel önkontrolü: {panels} panel / {edges} üyelik; RAM bütçesi aşılıyor. Daha az sütun veya açık ilk-N örnek seçin."
        )
    if (
        spec.kind in ("pair", "parallel", "bubble", "facets", "conditional")
        and used > spec.point_limit
    ):
        raise ProjectError(
            f"Panel önkontrolü: {panels} panel / {used} satır; nokta limiti {spec.point_limit}. Açık ilk-N örnek seçin veya hexbin/2D density kullanın."
        )


def calculate(spec, values, numbers, add, used, details, warnings, control):
    group = labels(values[spec.group]) if spec.group else [""] * used
    facets = labels(values[spec.facet]) if spec.facet else [""] * used
    group_order, facet_order = list(dict.fromkeys(group)), list(dict.fromkeys(facets))
    if len(group_order) > min(spec.top_n, 100) or len(facet_order) > 4:
        raise ProjectError("Önkontrol: en fazla100 grup /4 facet; açık filtre seçin.")
    if spec.category_order:
        if set(spec.category_order) != set(group_order):
            raise ProjectError("Kategori sırası tüm farklı grup etiketlerini içermeli.")
        group_order = list(spec.category_order)
    details.update(
        multivariate_version=1,
        facet_scale=spec.facet_scale,
        group_order=group_order,
        facets=facet_order,
        panels=[],
        preflight=dict(
            columns=len(spec.columns),
            input_rows=used,
            estimated_memberships=used
            * (
                len(spec.columns) ** 2
                if spec.kind == "pair"
                else max(1, len(spec.columns))
            ),
        ),
        selection_action="view only; explicit filtered dataset action required",
        aggregation="none",
        normalization="none",
    )
    included = set()

    def panel(title, xcol="", ycol="", **extra):
        index = len(details["panels"])
        details["panels"].append(
            dict(index=index, title=title, xcol=xcol, ycol=ycol, **extra)
        )
        return index

    if spec.kind == "pair":
        arrays = {c: numbers(c) for c in spec.columns}
        for row, yc in enumerate(spec.columns):
            for col, xc in enumerate(spec.columns):
                control.check()
                pid = panel("", xc, yc, row=row, col=col)
                eligible = [
                    i
                    for i in range(used)
                    if arrays[xc][i] is not None and arrays[yc][i] is not None
                ]
                included.update(eligible)
                if row == col:
                    data = [arrays[xc][i] for i in eligible]
                    if not data:
                        continue
                    counts, bins = np.histogram(data, bins=spec.bins)
                    for k, count in enumerate(counts):
                        members = [
                            i
                            for i in eligible
                            if bins[k] <= arrays[xc][i] <= bins[k + 1]
                            and (k == len(counts) - 1 or arrays[xc][i] < bins[k + 1])
                        ]
                        add(
                            (bins[k] + bins[k + 1]) / 2,
                            int(count),
                            members,
                            panel=pid,
                            left=float(bins[k]),
                            right=float(bins[k + 1]),
                            diagonal=True,
                        )
                else:
                    for i in eligible:
                        add(
                            arrays[xc][i], arrays[yc][i], [i], panel=pid, group=group[i]
                        )
        details["pair_policy"] = (
            "pairwise complete cases; diagonal count histogram; off-diagonal source observations"
        )
    elif spec.kind in ("grouped-heatmap", "clustered-heatmap"):
        arrays = {c: numbers(c) for c in spec.columns}
        rows = (
            sorted(group_order) if spec.heatmap_order == "alphabetical" else group_order
        )
        matrix = np.empty((len(rows), len(spec.columns)))
        members = {}
        if len(rows) * len(spec.columns) > spec.point_limit:
            raise ProjectError("Heatmap hücre genişlemesi nokta limitini aşıyor.")
        for j, label in enumerate(rows):
            for k, c in enumerate(spec.columns):
                indices = [
                    i
                    for i in range(used)
                    if group[i] == label and arrays[c][i] is not None
                ]
                if not indices:
                    raise ProjectError(
                        "Heatmap boş hücre içeriyor; imputasyon veya sıfır uydurulmadı."
                    )
                included.update(indices)
                members[j, k] = indices
                a = np.asarray([arrays[c][i] for i in indices])
                if spec.aggregation not in (
                    "mean",
                    "sum",
                    "median",
                    "min",
                    "max",
                    "count",
                ):
                    raise ProjectError("Heatmap için açık agregasyon seçin.")
                matrix[j, k] = (
                    len(a)
                    if spec.aggregation == "count"
                    else getattr(np, spec.aggregation)(a)
                )
        if not np.isfinite(matrix).all():
            raise ProjectError(
                "Heatmap agregasyon sonucu sonlu değil; ölçek/precision seçimini inceleyin."
            )
        center, scale = np.zeros(len(spec.columns)), np.ones(len(spec.columns))
        if spec.heatmap_scale == "column-zscore":
            center, scale = matrix.mean(axis=0), matrix.std(axis=0, ddof=0)
            if not np.isfinite(center).all() or not np.isfinite(scale).all():
                raise ProjectError(
                    "Heatmap ölçek hesabı sonlu değil; daha küçük ölçüm ölçeği seçin."
                )
            scale[scale == 0] = 1
            matrix = (matrix - center) / scale
        ro, co = list(range(len(rows))), list(range(len(spec.columns)))
        trees = {}
        if spec.kind == "clustered-heatmap":
            for key, a in (("rows", matrix), ("columns", matrix.T)):
                control.check()
                if len(a) > 1:
                    tree = linkage(
                        a,
                        method=spec.cluster_method,
                        metric="euclidean",
                        optimal_ordering=False,
                    )
                    trees[key] = tree.tolist()
                    order = leaves_list(tree).astype(int).tolist()
                    if key == "rows":
                        ro = order
                    else:
                        co = order
        pid = panel("Grouped values")
        for y, j in enumerate(ro):
            for x, k in enumerate(co):
                add(
                    x,
                    y,
                    members[j, k],
                    label=rows[j],
                    panel=pid,
                    z=float(matrix[j, k]),
                    column=spec.columns[k],
                )
        details.update(
            aggregation=spec.aggregation,
            heatmap=dict(
                scale=spec.heatmap_scale,
                ordering=spec.heatmap_order,
                row_labels=[rows[j] for j in ro],
                column_ids=[spec.columns[k] for k in co],
                row_order=ro,
                column_order=co,
                center=center.tolist(),
                divisor=scale.tolist(),
                method=spec.cluster_method if trees else "none",
                metric="euclidean" if trees else "none",
                linkage=trees,
                color_limits=[float(matrix.min()), float(matrix.max())],
            ),
        )
    elif spec.kind == "parallel":
        arrays, scales = {}, {}
        for c in spec.columns:
            try:
                arrays[c] = numbers(c)
            except ProjectError:
                # Never assign ordinal distances to category labels.
                raise ProjectError(
                    "Parallel coordinates sayısal ölçümler ister; kategoriler için grouped heatmap/facet seçin."
                ) from None
            finite = [v for v in arrays[c] if v is not None]
            if not finite:
                raise ProjectError("Parallel coordinates boş ölçüm içeriyor.")
            scales[c] = [min(finite), max(finite)]
        pid = panel("Numeric axes: independent min/max scaling")
        for i in range(used):
            if any(arrays[c][i] is None for c in spec.columns):
                continue
            included.add(i)
            for k, c in enumerate(spec.columns):
                lo, hi = scales[c]
                add(
                    k,
                    (arrays[c][i] - lo) / (hi - lo) if hi != lo else 0.5,
                    [i],
                    panel=pid,
                    line=i,
                    group=group[i],
                    original_value=arrays[c][i],
                )
        details["parallel"] = dict(
            scales=scales,
            normalization="per-column minmax; constant=0.5",
            category_policy="reject; no continuous category interpolation",
        )
    else:
        xs, ys = numbers(spec.x), numbers(spec.y)
        sizes = numbers(spec.size) if spec.kind == "bubble" else None
        if sizes is not None and any(v is None or v < 0 for v in sizes):
            raise ProjectError(
                "Bubble boyutu eksik/nonfinite/negatif olamaz; sıfır açıkça dışlanır."
            )
        eligible = [
            i
            for i in range(used)
            if xs[i] is not None
            and ys[i] is not None
            and (sizes is None or sizes[i] > 0)
        ]
        if not eligible:
            raise ProjectError("Sonlu ilişki çifti yok.")
        included.update(eligible)
        if spec.kind in ("hexbin", "density-2d"):
            pid = panel("CPU aggregation", spec.x, spec.y)
            xa, ya = (
                np.array([xs[i] for i in eligible]),
                np.array([ys[i] for i in eligible]),
            )
            xmin, xmax, ymin, ymax = (
                float(xa.min()),
                float(xa.max()),
                float(ya.min()),
                float(ya.max()),
            )
            if xmin == xmax:
                xmin, xmax = xmin - 0.5, xmax + 0.5
            if ymin == ymax:
                ymin, ymax = ymin - 0.5, ymax + 0.5
            if spec.kind == "hexbin":
                # Two staggered lattices; nearest center in hex metric x²+3y².
                nx, ny = spec.grid_bins, max(1, int(spec.grid_bins / math.sqrt(3)))
                dx, dy = (xmax - xmin) / nx, (ymax - ymin) / ny
                centers = [
                    (xmin + j * dx, ymin + k * dy)
                    for j in range(nx + 1)
                    for k in range(ny + 1)
                ] + [
                    (xmin + (j + 0.5) * dx, ymin + (k + 0.5) * dy)
                    for j in range(nx)
                    for k in range(ny)
                ]
                normalized = [
                    ((x - xmin) / dx, math.sqrt(3) * (y - ymin) / dy)
                    for x, y in centers
                ]
                _, nearest = cKDTree(normalized).query(
                    np.column_stack(((xa - xmin) / dx, math.sqrt(3) * (ya - ymin) / dy))
                )
                buckets = defaultdict(list)
                for i, k in zip(eligible, nearest):
                    buckets[int(k)].append(i)
                for k, indices in buckets.items():
                    x, y = centers[k]
                    add(x, y, indices, panel=pid, z=len(indices), dx=dx, dy=dy)
                details.update(
                    aggregation="hexagonal count",
                    hexbin=dict(
                        gridsize=[nx, ny],
                        extent=[xmin, xmax, ymin, ymax],
                        metric="normalized x²+3y²; nearest staggered lattice",
                        tie_policy="cKDTree deterministic input order",
                    ),
                )
            else:
                xe, ye = (
                    np.linspace(xmin, xmax, spec.grid_bins + 1),
                    np.linspace(ymin, ymax, spec.grid_bins + 1),
                )
                buckets = defaultdict(list)
                for i in eligible:
                    k = min(
                        spec.grid_bins - 1,
                        int(np.searchsorted(xe, xs[i], side="right") - 1),
                    )
                    j = min(
                        spec.grid_bins - 1,
                        int(np.searchsorted(ye, ys[i], side="right") - 1),
                    )
                    buckets[k, j].append(i)
                area = float((xe[1] - xe[0]) * (ye[1] - ye[0]))
                for (k, j), indices in buckets.items():
                    add(
                        (xe[k] + xe[k + 1]) / 2,
                        (ye[j] + ye[j + 1]) / 2,
                        indices,
                        panel=pid,
                        z=len(indices) / (len(eligible) * area),
                        left=float(xe[k]),
                        right=float(xe[k + 1]),
                        bottom=float(ye[j]),
                        top=float(ye[j + 1]),
                    )
                details.update(
                    aggregation="rectangular histogram",
                    normalization="density: sum(cell_density * cell_area)=1",
                    density_2d=dict(
                        x_edges=xe.tolist(), y_edges=ye.tolist(), cell_area=area
                    ),
                )
        else:
            if spec.kind == "conditional":
                partitions = [("Pooled", eligible)] + [
                    (g, [i for i in eligible if group[i] == g]) for g in group_order
                ]
                if len(partitions) > 5:
                    raise ProjectError(
                        "Koşullu ilişki en fazla4 grup + pooled panel destekler."
                    )
            elif spec.kind == "facets":
                partitions = [
                    (f, [i for i in eligible if facets[i] == f]) for f in facet_order
                ]
            else:
                partitions = [("", eligible)]
            for name, indices in partitions:
                pid = panel(name, spec.x, spec.y)
                for i in indices:
                    extras = dict(panel=pid, group=group[i])
                    if sizes is not None:
                        ratio = sizes[i] / max(sizes)
                        extras.update(
                            size_value=sizes[i],
                            marker_area=400
                            * (ratio if spec.bubble_encoding == "area" else ratio**2),
                        )
                    add(xs[i], ys[i], [i], **extras)
                if spec.kind == "conditional":
                    a, b = (
                        np.array([xs[i] for i in indices]),
                        np.array([ys[i] for i in indices]),
                    )
                    correlation = (
                        float(np.corrcoef(a, b)[0, 1])
                        if len(a) > 1 and a.std() > 0 and b.std() > 0
                        else None
                    )
                    details["panels"][-1].update(n=len(indices), pearson=correlation)
            if sizes is not None:
                details["bubble"] = dict(
                    encoding=spec.bubble_encoding,
                    maximum=max(sizes),
                    maximum_marker_area=400,
                    formula="s=400*v/max"
                    if spec.bubble_encoding == "area"
                    else "s=400*(v/max)^2",
                    zero_excluded=sum(v == 0 for v in sizes),
                    legend_values=[max(sizes) / 4, max(sizes) / 2, max(sizes)],
                )
            if spec.kind == "conditional":
                warnings.append(
                    "Pooled ve grup içi ilişki farklı olabilir (Simpson); koşullama nedensellik kanıtı değildir."
                )
    details.update(included_n=len(included), excluded_rows=used - len(included))
    if len(details["panels"]) > 1:
        warnings.append(
            f"Facet/panel eksenleri: {spec.facet_scale}; pair eksenleri seçili değişkene göre; diagonal count ayrı ölçek."
        )
    control.check()
