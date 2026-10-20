"""Matplotlib Agg adapter: render/export and device coordinate map; no Qt dependency."""

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from veri_ufku.charts.contracts import COMPOSITION_KINDS, MULTIVARIATE_KINDS, ChartSpec
from veri_ufku.charts.distribution_plot import TITLES, draw, style, validate_scales
from veri_ufku.charts.distributions import enabled
from veri_ufku.importers.delimited import Control, hash_artifact

PALETTE = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9")
HATCHES = ("/", "\\", "x", ".", "-", "+")


def render(
    result,
    workspace,
    bounds=(),
    highlight=(),
    control=None,
    figure=None,
    palette_override=None,
):
    control = control or Control()
    spec = ChartSpec.from_dict(result["spec"])
    bounds = bounds or spec.bounds
    validate_scales(result, spec, bounds)
    control.check()
    points = result["points"]
    selection_context = {}
    if highlight:
        from veri_ufku.charts.engine import select

        selection_context = select(result, highlight)

    from veri_ufku.storage.project_model import ProjectError

    if (
        spec.width * spec.height * (spec.dpi / 120) ** 2 * 12
        > control.budget.ram_bytes // 2
    ):
        raise ProjectError("DPI/piksel genişlemesi grafik RAM bütçesini aşıyor.")
    fig = figure or Figure(
        figsize=(spec.width / 120, spec.height / 120),
        dpi=spec.dpi,
        facecolor="white",
    )
    canvas = FigureCanvasAgg(fig) if figure is None else None
    palette = (
        PALETTE
        if spec.palette == "accessible"
        else ("#222222", "#666666", "#999999", "#bbbbbb")
        if spec.palette == "grayscale"
        else ("#440154", "#31688e", "#35b779", "#fde725")
    )
    if palette_override:
        palette = tuple(palette_override)
    ax = fig.add_subplot(111)
    axes, point_axes = [ax], {}
    fig.subplots_adjust(left=0.13, right=0.95, bottom=0.24, top=0.85)
    xs, ys = [p["x"] for p in points], [p["y"] for p in points]
    groups = list(dict.fromkeys(p.get("group", "") for p in points))
    if spec.kind.startswith("map-"):
        from veri_ufku.geo.charts import draw as geo_draw

        fig.delaxes(ax)
        axes, point_axes = geo_draw(result, spec, fig, palette)
        ax = axes[0]
    elif spec.kind in COMPOSITION_KINDS:
        from veri_ufku.charts.composition_plot import draw as composition_draw

        fig.delaxes(ax)
        axes, point_axes = composition_draw(result, spec, fig, palette)
        ax = axes[0]
    elif spec.kind in MULTIVARIATE_KINDS:
        from veri_ufku.charts.multivariate_plot import draw as multi_draw

        fig.delaxes(ax)
        axes, point_axes = multi_draw(result, spec, fig, palette)
        ax = axes[0]
    elif enabled(spec):
        fig.delaxes(ax)
        axes, point_axes = draw(result, spec, fig, palette)
        ax = axes[0]
    elif spec.kind == "array-heatmap":
        import numpy as np

        xcoords, ycoords = sorted(set(xs)), sorted(set(ys))
        if len(xcoords) * len(ycoords) > spec.point_limit:
            from veri_ufku.storage.project_model import ProjectError

            raise ProjectError("Isı haritası grid genişlemesi nokta sınırını aşıyor.")
        grid = np.full((len(ycoords), len(xcoords)), np.nan)
        xi, yi = (
            {v: i for i, v in enumerate(xcoords)},
            {v: i for i, v in enumerate(ycoords)},
        )
        for point in points:
            if point["z"] is not None:
                grid[yi[point["y"]], xi[point["x"]]] = point["z"]
        mesh = ax.pcolormesh(xcoords, ycoords, grid, shading="nearest", cmap="viridis")
        fig.colorbar(
            mesh, ax=ax, label=result["details"]["array_source"]["output_unit"]
        )
    elif spec.kind == "histogram":
        ax.bar(
            xs,
            ys,
            width=[p["right"] - p["left"] for p in points],
            align="center",
            color=palette[0],
            edgecolor="white",
        )
    elif spec.kind == "box":
        ax.bxp(
            [
                dict(
                    label=p["label"],
                    med=p["y"],
                    q1=p["q1"],
                    q3=p["q3"],
                    whislo=p["whislo"],
                    whishi=p["whishi"],
                    fliers=p["fliers"],
                )
                for p in points
            ],
            positions=xs,
            patch_artist=True,
            boxprops=dict(facecolor=palette[0], alpha=0.65),
            medianprops=dict(color="black"),
            showfliers=True,
        )
    elif spec.kind in ("bar", "line", "scatter", "array-profile"):
        for gidx, g in enumerate(groups):
            subset = [p for p in points if p.get("group", "") == g]
            x, y = (
                [p["x"] for p in subset],
                [math.nan if p["y"] is None else p["y"] for p in subset],
            )
            label = g or (
                "Kayıt sayısı"
                if spec.aggregation == "count" and spec.kind == "bar"
                else "Ölçüm"
            )
            color = palette[gidx % len(palette)]
            if spec.kind == "bar":
                ax.bar(
                    [v + (gidx - (len(groups) - 1) / 2) * 0.8 / len(groups) for v in x],
                    y,
                    width=0.8 / len(groups),
                    label=label,
                    color=color,
                    hatch=HATCHES[gidx % len(HATCHES)],
                    edgecolor="#202020",
                )
            elif spec.kind in ("line", "array-profile"):
                ax.plot(
                    x,
                    y,
                    marker=("o", "s", "^", "D", "v", "P")[gidx % 6],
                    markersize=4,
                    label=label,
                    color=color,
                    linestyle=("-", "--", ":", "-.")[gidx % 4],
                )
            else:
                ax.scatter(
                    x,
                    y,
                    s=[max(9, min(120, p["n"] ** 0.5 * 8)) for p in subset],
                    label=label,
                    color=color,
                    alpha=0.7,
                    marker=("o", "s", "^", "D", "v", "P")[gidx % 6],
                )
        if spec.kind == "bar":
            labels = {p["x"]: p["label"] for p in points}
            ax.set_xticks(list(labels), list(labels.values()), rotation=35, ha="right")
        elif spec.kind in ("line", "array-profile") and result["details"].get(
            "timezone", ""
        ).startswith(("Date", "Datetime")):
            labels = {p["x"]: p["label"] for p in points}
            # Bounded tick labels carry original timezone/instant strings; no implicit timezone conversion.
            selected = list(labels)[:: max(1, len(labels) // 6)]
            ax.set_xticks(
                selected, [labels[x] for x in selected], rotation=25, ha="right"
            )
        if spec.legend:
            ax.legend(loc="best", fontsize=9)
    elif spec.kind == "missing":
        ax.bar(xs, ys, color=palette[0])
        ax.set_xticks(xs, [p["label"] for p in points], rotation=35, ha="right")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{100 * x:g}%"))
        ax.set_ylim(0, 1)
    else:
        labels = result["details"]["labels"]
        n = len(labels)
        matrix = [[float("nan")] * n for _ in range(n)]
        for p in points:
            matrix[int(p["y"])][int(p["x"])] = (
                float("nan") if p["coefficient"] is None else p["coefficient"]
            )
        im = ax.imshow(
            matrix, vmin=-1, vmax=1, cmap="BrBG", origin="upper", aspect="auto"
        )
        fig.colorbar(im, ax=ax, label=result["details"]["method"])
        ax.set_xticks(range(n), labels, rotation=35, ha="right")
        ax.set_yticks(range(n), labels)
        if n <= 10:
            for p in points:
                value = (
                    "tanımsız"
                    if p["coefficient"] is None
                    else f"{p['coefficient']:.3f}"
                )
                ax.text(
                    p["x"],
                    p["y"],
                    f"{value}\nn={p['n']}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.8),
                )
    ax.set_title(
        ax.get_title()
        if enabled(spec)
        else spec.title
        or {
            "histogram": "Histogram",
            "box": "Kutu grafiği",
            "bar": "Sütun grafiği",
            "line": "Çizgi grafiği",
            "scatter": "Dağılım grafiği",
            "correlation": "Korelasyon ısı haritası",
            "missing": "Eksik oranı",
            "array-heatmap": "Seçili array kesiti · 2D ısı haritası",
            "array-profile": "Seçili array kesiti · profil",
        }.get(spec.kind, TITLES.get(spec.kind, spec.kind)),
        fontsize=14,
    )
    ax.set_xlabel(
        (
            spec.xlabel
            or (
                result.get("column_labels", {}).get(spec.group, "Gruplar")
                if spec.kind == "box"
                else result.get("column_labels", {}).get(
                    spec.columns[0] if spec.kind == "array-heatmap" else spec.x, "Sütun"
                )
            )
        )
        + (f" ({spec.xunit})" if spec.xunit else "")
    )
    ax.set_ylabel(
        (
            spec.ylabel
            or (
                "Kayıt sayısı"
                if spec.kind == "histogram"
                or (spec.kind == "bar" and spec.aggregation == "count")
                else "Null oranı"
                if spec.kind == "missing"
                else "Sütun"
                if spec.kind == "correlation"
                else result.get("column_labels", {}).get(
                    spec.columns[1]
                    if spec.kind == "array-heatmap"
                    else spec.y or spec.x,
                    "Ölçüm",
                )
            )
        )
        + (f" ({spec.yunit})" if spec.yunit else "")
    )
    if enabled(spec):
        ylabel = (
            "Yoğunluk (tam dağılım alanı=1)"
            if spec.kind == "kde"
            or spec.kind == "histogram"
            and spec.normalization == "density"
            else "Birikimli olasılık"
            if spec.kind in ("ecdf", "pp")
            else "Yüzde"
            if spec.kind == "histogram" and spec.normalization == "percent"
            else "Olasılık"
            if spec.kind == "histogram" and spec.normalization == "probability"
            else "Kayıt / ağırlık toplamı"
            if spec.kind in ("histogram", "missing-pattern")
            else result.get("column_labels", {}).get(spec.y or spec.x, "Ölçüm")
        )
        xlabel = (
            "Standart normal quantile"
            if spec.kind == "qq"
            else "Fit normal CDF"
            if spec.kind == "pp"
            else "Null deseni (seçili sütun sırası)"
            if spec.kind == "missing-pattern"
            else result.get("column_labels", {}).get(spec.group, "Gruplar")
            if spec.kind in ("box", "violin", "strip", "swarm")
            else ax.get_xlabel()
        )
        if spec.kind == "rug":
            ylabel = "Grup"
        for other in axes:
            other.set_xlabel(spec.xlabel or xlabel)
            other.set_ylabel(spec.ylabel or ylabel)
        fig.suptitle(
            spec.title or TITLES.get(spec.kind, spec.kind),
            fontsize=spec.font_size + 2,
            fontfamily=spec.font,
        )
    style(axes, spec, bounds)
    if spec.kind in MULTIVARIATE_KINDS:
        from veri_ufku.charts.multivariate_plot import finish

        finish(result, spec, axes, fig)
    if spec.kind.startswith("map-"):
        geo = result["details"]["geospatial"]
        from veri_ufku.geo.core import crs

        ax.set_xlabel(
            spec.xlabel
            or ("Longitude / x" if crs(geo["crs"]).is_geographic else "Easting / x")
        )
        ax.set_ylabel(
            spec.ylabel
            or ("Latitude / y" if crs(geo["crs"]).is_geographic else "Northing / y")
        )
    elif spec.kind in COMPOSITION_KINDS:
        from veri_ufku.charts.composition_plot import finish as composition_finish

        composition_finish(result, spec, axes, fig)
    ax.tick_params(labelsize=spec.font_size)
    if spec.kind != "correlation":
        ax.grid(axis="y", alpha=0.2)
    if bounds:
        ax.set_xlim(bounds[:2])
        ax.set_ylim(bounds[2:])
    selected = [p for p in points if p["point_id"] in highlight and p["y"] is not None]
    if selected:
        for current_ax in axes:
            marked = [
                p for p in selected if point_axes.get(p["point_id"], ax) is current_ax
            ]
            current_ax.scatter(
                [p.get("glyph_x", p["x"]) for p in marked],
                [p.get("glyph_y", p["y"]) for p in marked],
                s=100,
                facecolors="none",
                edgecolors="#991B1B",
                linewidths=2,
                zorder=10,
            )
    # Version/scope travels into PNG and SVG, including every viewport export.
    footer = f"{result['dataset_version']} | {result['scope']} {result['used_n']}/{result['population_n']} | filters={len(result['filters'])} | null/NaN/inf excluded separately"
    if spec.kind == "scatter":
        footer += f" | {result['details'].get('sampling_method')} {result['details'].get('represented_rows')}/{result['details'].get('valid_pairs')}"
    footer += f" | finite_n={result['details'].get('included_n', result['used_n'])}"
    footer += f" | normalization={result['details'].get('normalization')} | excluded={result['details'].get('excluded_rows', 0)} | {spec.xscale}/{spec.yscale} | clipped={bool(bounds)} | DPI={spec.dpi}"
    from textwrap import wrap

    from matplotlib.text import Text

    footer += f" | aggregation={result['details'].get('aggregation')} | weight={spec.weight_type}"
    if spec.kind == "histogram":
        footer += f" | bins={spec.bins}"
    if spec.kind in ("kde", "violin"):
        footer += " | Gaussian bandwidth: " + ", ".join(
            f"{v['facet']}/{v['group']}={v['bandwidth']:.4g}"
            for v in result["details"]["samples"]
        )
        footer += f" ({spec.bandwidth}, multiplier={spec.bandwidth_factor}); range=observed±3bw, unrenormalized"
        if spec.kind == "violin":
            footer += " | width=per-group peak; half-width=0.35"
    if spec.kind in ("error-bar", "ci-band"):
        footer += f" | interval={spec.uncertainty} | confidence={spec.confidence if spec.uncertainty == 'ci' else 'n/a'} | iid mean; pointwise only"
    if spec.kind in MULTIVARIATE_KINDS:
        footer += f" | panels={len(result['details']['panels'])} | facet_scale={spec.facet_scale} | explicit first-N sample={spec.scope == 'sample'} | selection=view only | highlighted glyphs={len(highlight)}"
        if spec.kind == "bubble":
            footer += f" | bubble={spec.bubble_encoding}; {result['details']['bubble']['formula']}"
        if spec.kind in ("grouped-heatmap", "clustered-heatmap"):
            footer += f" | heatmap={spec.heatmap_scale}; order={spec.heatmap_order}; cluster={result['details']['heatmap']['method']}/euclidean"
    if spec.kind.startswith("map-"):
        geo = result["details"]["geospatial"]
        footer += f" | OFFLINE local map; CRS={geo.get('authority')}; xy axis; mode={geo['mode']}; semantics={geo.get('value_semantics', 'value')}; thresholds={geo.get('thresholds', [])}; nodata={geo.get('nodata_count', geo.get('nodata'))}; no tiles/network"
        if geo.get("attribution"):
            footer += f" | attribution={geo['attribution']}"
    elif spec.kind in COMPOSITION_KINDS:
        footer += f" | denominator={result['details'].get('denominator', result['details'].get('denominators', 'not share'))}; missing_category={spec.missing_category}; missing_Y={result['details'].get('count_policy', 'strict schema')}; structural={result['details']['structural_rows']}"
        if spec.kind == "radar":
            footer += " | ADVANCED per-column minmax; area depends on axis order; alternative=dot/parallel"
        if spec.kind == "funnel":
            footer += f" | unit={spec.funnel_unit}; duplicates={result['details']['funnel']['duplicate_person_stage_events']}"
        if spec.kind in ("sankey", "alluvial"):
            footer += f" | balanced DAG; boundary={result['details']['flow']['source_total']}; edge sum={result['details']['flow']['edge_total']} is not boundary total"
    if selection_context:
        footer += f" | selected RowId n={selection_context['count']}; glyph IDs={list(highlight)[:10]}{' (first10)' if len(highlight) > 10 else ''}; RowId first5={selection_context['row_ids'][:5]}"
    fig.text(0.02, 0.02, "\n".join(wrap(footer, 140)), fontsize=7, fontfamily=spec.font)
    for text in fig.findobj(match=Text):
        text.set_fontfamily(spec.font)
    if figure is not None:
        return axes
    canvas.draw()
    control.check()
    render_width, render_height = canvas.get_width_height()
    pixels, hit_regions = [], []
    for p in points:
        display_x = p.get("glyph_x", p["x"])
        if spec.kind == "bar":
            display_x += (
                (groups.index(p.get("group", "")) - (len(groups) - 1) / 2)
                * 0.8
                / len(groups)
            )
        point_ax = point_axes.get(p["point_id"], ax)
        x, y = point_ax.transData.transform(
            (display_x, p.get("glyph_y", 0 if p["y"] is None else p["y"]))
        )
        rectangle = None
        if spec.kind in ("histogram", "bar", "missing") and p["y"] is not None:
            half = (
                (p["right"] - p["left"]) / 2
                if spec.kind == "histogram"
                else 0.4 / len(groups)
                if spec.kind == "bar"
                else 0.4
            )
            rectangle = (display_x - half, display_x + half, 0, p["y"])
        elif spec.kind == "box":
            rectangle = (display_x - 0.2, display_x + 0.2, p["q1"], p["q3"])
        elif spec.kind == "correlation":
            rectangle = (display_x - 0.5, display_x + 0.5, p["y"] - 0.5, p["y"] + 0.5)
        if spec.kind in ("grouped-heatmap", "clustered-heatmap"):
            rectangle = (p["x"] - 0.5, p["x"] + 0.5, p["y"] - 0.5, p["y"] + 0.5)
        elif spec.kind == "density-2d":
            rectangle = (p["left"], p["right"], p["bottom"], p["top"])
        if spec.kind in ("stacked-bar", "percent-bar", "waterfall"):
            rectangle = (p["x"] - 0.4, p["x"] + 0.4, p["bottom"], p["top"])
        elif spec.kind == "treemap":
            xx, yy, ww, hh = p["rect"]
            rectangle = (xx, xx + ww, yy, yy + hh)
        elif spec.kind == "calendar":
            rectangle = (p["x"] - 0.5, p["x"] + 0.5, p["y"] - 0.5, p["y"] + 0.5)
        if rectangle:
            left, right, low, high = rectangle
            a, b = (
                point_ax.transData.transform((left, low)),
                point_ax.transData.transform((right, high)),
            )
            hit_regions.append(
                dict(
                    point_id=p["point_id"],
                    left=min(a[0], b[0]),
                    right=max(a[0], b[0]),
                    top=render_height - max(a[1], b[1]),
                    bottom=render_height - min(a[1], b[1]),
                )
            )
        pixels.append(
            dict(point_id=p["point_id"], x=float(x), y=float(render_height - y))
        )
    bbox = ax.get_window_extent()
    metadata = dict(
        width=render_width,
        height=render_height,
        pixels=pixels,
        hit_regions=hit_regions,
        axes_rect=[
            float(bbox.x0),
            float(render_height - bbox.y1),
            float(bbox.x1),
            float(render_height - bbox.y0),
        ],
        bounds=[float(v) for v in (*ax.get_xlim(), *ax.get_ylim())],
        view_bounds=list(bounds),
        facets=len(axes),
        panel_axes=[
            dict(index=i, bounds=[float(v) for v in (*a.get_xlim(), *a.get_ylim())])
            for i, a in enumerate(axes)
        ],
        display=result["details"].get("display", {}),
        highlight=list(highlight),
        selection_context=selection_context,
        accessibility=dict(
            palette={
                "accessible": "Okabe-Ito subset",
                "viridis": "Viridis subset",
                "grayscale": "grayscale",
            }[spec.palette],
            group_encoding="bar hatch / line dash+marker / scatter marker",
            numeric_alternative="points and membership table",
            correlation_encoding="BrBG diverging + numeric values when <=10 columns",
        ),
    )
    root = Path(workspace)
    fig.savefig(root / "chart.png", dpi=spec.dpi)
    fig.savefig(root / "chart.svg", format="svg")
    fig.savefig(root / "chart.pdf", format="pdf")
    result["paths"]["pdf"] = str(root / "chart.pdf")
    result["paths"].update(png=str(root / "chart.png"), svg=str(root / "chart.svg"))
    result["render"] = metadata
    result["paths"]["result"] = str(root / "chart-result.json")
    (root / "chart-result.json").write_text(
        json.dumps(
            {k: v for k, v in result.items() if k != "fingerprints"},
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )
    result["fingerprints"] = {
        k: hash_artifact(v, control) for k, v in result["paths"].items()
    }
    control.disk(root)
    fig.clear()
    return result
