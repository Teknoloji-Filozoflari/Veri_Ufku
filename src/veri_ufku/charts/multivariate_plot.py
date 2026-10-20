"""Static plots and exact per-panel device geometry for brushing."""

import math
from collections import defaultdict

import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D


def draw(result, spec, fig, palette):
    panels = result["details"]["panels"]
    points = result["points"]
    count = len(panels)
    columns = len(spec.columns) if spec.kind == "pair" else min(2, count)
    rows = math.ceil(count / columns)
    axes, point_axes = [], {}
    labels = result["column_labels"]
    for panel in panels:
        ax = fig.add_subplot(rows, columns, panel["index"] + 1)
        axes.append(ax)
        pp = [p for p in points if p["panel"] == panel["index"]]
        for p in pp:
            point_axes[p["point_id"]] = ax
        if spec.kind == "pair" and panel["row"] == panel["col"]:
            ax.bar(
                [p["x"] for p in pp],
                [p["y"] for p in pp],
                width=[p["right"] - p["left"] for p in pp],
                color=palette[0],
                alpha=0.7,
            )
        elif spec.kind in ("hexbin", "density-2d"):
            polygons = []
            for p in pp:
                if spec.kind == "hexbin":
                    # Voronoi hexagon of staggered lattice in x²+3y² metric.
                    vertices = [
                        (-0.5, -1 / 6),
                        (0, -1 / 3),
                        (0.5, -1 / 6),
                        (0.5, 1 / 6),
                        (0, 1 / 3),
                        (-0.5, 1 / 6),
                    ]
                    polygons.append(
                        [
                            (p["x"] + x * p["dx"], p["y"] + y * p["dy"])
                            for x, y in vertices
                        ]
                    )
                else:
                    polygons.append(
                        [
                            (p["left"], p["bottom"]),
                            (p["right"], p["bottom"]),
                            (p["right"], p["top"]),
                            (p["left"], p["top"]),
                        ]
                    )
            collection = PolyCollection(
                polygons,
                array=np.array([p["z"] for p in pp]),
                cmap="viridis",
                edgecolors="none",
            )
            ax.add_collection(collection)
            ax.autoscale_view()
            fig.colorbar(
                collection,
                ax=ax,
                label="Count" if spec.kind == "hexbin" else "Density / unit area",
            )
        elif spec.kind in ("grouped-heatmap", "clustered-heatmap"):
            h = result["details"]["heatmap"]
            matrix = np.full((len(h["row_labels"]), len(h["column_ids"])), np.nan)
            for p in pp:
                matrix[int(p["y"]), int(p["x"])] = p["z"]
            im = ax.imshow(matrix, aspect="auto", origin="lower", cmap="viridis")
            ax.set_xticks(
                range(matrix.shape[1]),
                [labels[c] for c in h["column_ids"]],
                rotation=35,
                ha="right",
            )
            ax.set_yticks(range(matrix.shape[0]), h["row_labels"])
            fig.colorbar(im, ax=ax, label=h["scale"] + " / " + spec.aggregation)
        elif spec.kind == "parallel":
            lines = defaultdict(list)
            for p in pp:
                lines[p["line"]].append(p)
            groups = result["details"]["group_order"]
            for line in lines.values():
                ax.plot(
                    [p["x"] for p in line],
                    [p["y"] for p in line],
                    alpha=0.4,
                    color=palette[groups.index(line[0]["group"]) % len(palette)],
                    marker=".",
                )
            ax.set_xticks(
                range(len(spec.columns)),
                [labels[c] for c in spec.columns],
                rotation=30,
                ha="right",
            )
            ax.set_ylim(-0.05, 1.05)
        else:
            for j, g in enumerate(result["details"]["group_order"]):
                bucket = [p for p in pp if p.get("group", "") == g]
                ax.scatter(
                    [p["x"] for p in bucket],
                    [p["y"] for p in bucket],
                    s=[p.get("marker_area", 12) for p in bucket],
                    alpha=0.6,
                    color=palette[j % len(palette)],
                    label=g or None,
                    marker=("o", "s", "^", "D")[j % 4],
                )
            if spec.legend and spec.group:
                ax.legend(fontsize=7)
            if spec.kind == "bubble":
                b = result["details"]["bubble"]
                handles = [
                    Line2D(
                        [],
                        [],
                        linestyle="",
                        marker="o",
                        color=palette[0],
                        markersize=math.sqrt(
                            400
                            * (
                                v / b["maximum"]
                                if b["encoding"] == "area"
                                else (v / b["maximum"]) ** 2
                            )
                        ),
                        label=f"{v:g}",
                    )
                    for v in b["legend_values"]
                ]
                ax.add_artist(
                    ax.legend(
                        handles=handles,
                        title=labels[spec.size] + " / " + b["encoding"],
                        loc="upper left",
                        fontsize=7,
                    )
                )
        title = panel["title"]
        if spec.kind == "conditional":
            title += f" · n={panel['n']} · r={panel['pearson'] if panel['pearson'] is not None else 'undefined'}"
        ax.set_title(title, fontsize=8)
    if spec.facet_scale == "shared" and spec.kind in ("facets", "conditional"):
        limits = [a.get_xlim() + a.get_ylim() for a in axes]
        xlim = (min(v[0] for v in limits), max(v[1] for v in limits))
        ylim = (min(v[2] for v in limits), max(v[3] for v in limits))
        for ax in axes:
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
    if spec.kind == "pair" and spec.facet_scale == "shared":
        for c in range(columns):
            selected = [a for i, a in enumerate(axes) if i % columns == c]
            limits = [a.get_xlim() for a in selected]
            for a in selected:
                a.set_xlim(min(v[0] for v in limits), max(v[1] for v in limits))
        for r in range(rows):
            selected = [
                a for i, a in enumerate(axes) if i // columns == r and i % columns != r
            ]
            if selected:
                limits = [a.get_ylim() for a in selected]
                for a in selected:
                    a.set_ylim(min(v[0] for v in limits), max(v[1] for v in limits))
    fig.subplots_adjust(wspace=0.5, hspace=0.7)
    return axes, point_axes


def finish(result, spec, axes, fig):
    labels = result["column_labels"]
    for panel, ax in zip(result["details"]["panels"], axes):
        ax.set_xlabel(spec.xlabel or labels.get(panel["xcol"], "Selected columns"))
        ax.set_ylabel(
            spec.ylabel
            or (
                "Count"
                if spec.kind == "pair" and panel["row"] == panel["col"]
                else labels.get(panel["ycol"], "Group / normalized measurement")
            )
        )
        ax.tick_params(labelsize=7)
    fig.suptitle(
        spec.title or spec.kind, fontfamily=spec.font, fontsize=spec.font_size + 2
    )
