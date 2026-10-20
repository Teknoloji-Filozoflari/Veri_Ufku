"""CPU composition rendering; device coordinates follow each actual glyph."""

import math

from matplotlib.patches import PathPatch, Rectangle, Wedge
from matplotlib.path import Path


def draw(result, spec, fig, palette):
    ax = fig.add_subplot(111, projection="polar" if spec.kind == "radar" else None)
    points = result["points"]
    d = result["details"]
    k = spec.kind
    labels = result["column_labels"]
    if k in ("stacked-bar", "percent-bar"):
        for j, g in enumerate(d["series_order"]):
            pp = [p for p in points if p["group"] == g]
            ax.bar(
                [p["x"] for p in pp],
                [p["top"] - p["bottom"] for p in pp],
                bottom=[p["bottom"] for p in pp],
                label=g,
                color=palette[j % len(palette)],
                hatch=("/", "\\", ".")[j % 3],
                alpha=0.8,
            )
        ax.set_xticks(
            range(len(d["category_order"])),
            d["category_order"],
            rotation=30,
            ha="right",
        )
        ax.legend(fontsize=8)
    elif k in ("stacked-area", "percent-area"):
        for j, g in enumerate(d["series_order"]):
            pp = [p for p in points if p["group"] == g]
            ax.fill_between(
                [p["x"] for p in pp],
                [p["bottom"] for p in pp],
                [p["top"] for p in pp],
                label=g,
                color=palette[j % len(palette)],
                alpha=0.8,
            )
            ax.plot(
                [p["x"] for p in pp],
                [p["top"] for p in pp],
                linewidth=0.6,
                color="black",
            )
        coordinates = list(dict.fromkeys(p["x"] for p in points))
        ax.set_xticks(coordinates, d["category_order"], rotation=30, ha="right")
        ax.legend(fontsize=8)
    elif k in ("dot", "lollipop"):
        if k == "lollipop":
            ax.vlines(
                [p["x"] for p in points], 0, [p["y"] for p in points], color=palette[0]
            )
        ax.scatter([p["x"] for p in points], [p["y"] for p in points], color=palette[0])
        ax.set_xticks(
            [p["x"] for p in points],
            [p["label"] for p in points],
            rotation=30,
            ha="right",
        )
    elif k == "waterfall":
        for p in points:
            ax.bar(
                p["x"],
                p["top"] - p["bottom"],
                bottom=p["bottom"],
                color=palette[0]
                if p["role"] in ("start", "end")
                else palette[2]
                if p["delta"] >= 0
                else palette[1],
                edgecolor="black",
            )
            ax.text(
                p["x"],
                p["top"],
                f"{p['delta']:g}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
        ax.set_xticks([p["x"] for p in points], [p["label"] for p in points])
    elif k == "pareto":
        ax.bar(
            [p["x"] for p in points],
            [p["y"] for p in points],
            color=palette[0],
            label="Sol eksen · değer",
        )
        ax.set_xticks(
            [p["x"] for p in points],
            [p["label"] for p in points],
            rotation=30,
            ha="right",
        )
        right = ax.twinx()
        right.plot(
            [p["x"] for p in points],
            [p["cumulative_percent"] for p in points],
            color=palette[1],
            marker="o",
            label="Sağ eksen · birikimli yüzde",
        )
        right.legend(loc="upper right")
        ax.legend(loc="upper left")
        right.set_ylim(0, 105)
        right.set_ylabel("Birikimli yüzde · dahil edilen toplam")
    elif k in ("pie", "donut"):
        start = 0
        for j, p in enumerate(points):
            end = start + 360 * p["percent"] / 100
            ax.add_patch(
                Wedge(
                    (0, 0),
                    1,
                    start,
                    end,
                    width=0.4 if k == "donut" else None,
                    facecolor=palette[j % len(palette)],
                    edgecolor="white",
                )
            )
            angle = math.radians((start + end) / 2)
            p["glyph_x"] = 0.8 * math.cos(angle)
            p["glyph_y"] = 0.8 * math.sin(angle)
            ax.text(
                1.15 * math.cos(angle),
                1.15 * math.sin(angle),
                f"{p['label']} {p['percent']:.1f}%",
                ha="center",
                fontsize=9,
            )
            start = end
        ax.set_aspect("equal")
        ax.set_xlim(-1.6, 1.6)
        ax.set_ylim(-1.4, 1.4)
        ax.axis("off")
        if k == "donut":
            ax.text(0, 0, f"Toplam\n{d['denominator']:g}", ha="center", va="center")
    elif k == "treemap":
        for j, p in enumerate(points):
            x, y, w, h = p["rect"]
            ax.add_patch(
                Rectangle(
                    (x, y), w, h, facecolor=palette[j % len(palette)], edgecolor="white"
                )
            )
            ax.text(
                p["x"],
                p["y"],
                f"{p['label']}\n{p['value']:g} ({p['percent']:.1f}%)",
                ha="center",
                va="center",
                fontsize=8,
                clip_on=True,
            )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect("equal")
        ax.axis("off")
    elif k == "sunburst":
        for j, p in enumerate(points):
            a, b = p["theta"]
            r = p["depth"] + 1
            ax.add_patch(
                Wedge(
                    (0, 0),
                    r,
                    a,
                    b,
                    width=1,
                    facecolor=palette[j % len(palette)],
                    edgecolor="white",
                )
            )
            ax.text(
                p["x"],
                p["y"],
                f"{p['label']}\n{p['value']:g}",
                ha="center",
                va="center",
                fontsize=7,
                clip_on=True,
            )
        radius = max(p["depth"] for p in points) + 1
        ax.set_xlim(-radius, radius)
        ax.set_ylim(-radius, radius)
        ax.set_aspect("equal")
        ax.axis("off")
    elif k in ("sankey", "alluvial"):
        for j, p in enumerate(points):
            x0, x1 = p["source_x"], p["target_x"]
            y0, y1 = p["source_bottom"], p["target_bottom"]
            h = p["flow_width"]
            mid = (x0 + x1) / 2
            vertices = [
                (x0, y0),
                (mid, y0),
                (mid, y1),
                (x1, y1),
                (x1, y1 + h),
                (mid, y1 + h),
                (mid, y0 + h),
                (x0, y0 + h),
                (x0, y0),
            ]
            codes = [
                Path.MOVETO,
                Path.CURVE4,
                Path.CURVE4,
                Path.CURVE4,
                Path.LINETO,
                Path.CURVE4,
                Path.CURVE4,
                Path.CURVE4,
                Path.CLOSEPOLY,
            ]
            ax.add_patch(
                PathPatch(
                    Path(vertices, codes),
                    facecolor=palette[j % len(palette)],
                    alpha=0.65,
                    edgecolor="none",
                )
            )
            ax.text(
                p["x"], p["y"], f"{p['value']:g}", ha="center", va="center", fontsize=8
            )
        for n, (x, y, h) in d["flow"]["nodes"].items():
            ax.add_patch(Rectangle((x - 0.06, y), 0.12, h, color="#333333"))
            ax.text(x, y + h + 0.02, n, ha="center", va="bottom", fontsize=8)
        ax.set_xlim(-0.3, max(d["flow"]["levels"].values()) + 0.3)
        ax.set_ylim(-0.08, max(y + h for x, y, h in d["flow"]["nodes"].values()) + 0.2)
        ax.axis("off")
    elif k == "funnel":
        largest = d["denominator"]
        for p in points:
            left = (largest - p["y"]) / 2
            ax.add_patch(
                Rectangle(
                    (left, p["x"] - 0.4),
                    p["y"],
                    0.8,
                    facecolor=palette[int(p["x"]) % len(palette)],
                )
            )
            ax.text(
                largest / 2,
                p["x"],
                f"{p['label']} · {p['y']:g} · {p['percent']:.1f}%",
                ha="center",
                va="center",
                fontsize=9,
                color="black",
            )
            p["glyph_x"], p["glyph_y"] = largest / 2, p["x"]
        ax.set_xlim(0, largest)
        ax.set_ylim(len(points) - 0.5, -0.5)
        ax.axis("off")
    elif k == "calendar":
        from matplotlib import colormaps
        from matplotlib.cm import ScalarMappable
        from matplotlib.colors import Normalize

        norm = Normalize(min(p["z"] for p in points), max(p["z"] for p in points))
        cmap = colormaps["viridis"]
        for p in points:
            ax.add_patch(
                Rectangle(
                    (p["x"] - 0.5, p["y"] - 0.5),
                    1,
                    1,
                    facecolor=cmap(norm(p["z"])),
                    edgecolor="white",
                )
            )
        ax.set_xlim(-0.5, 53.5)
        ax.set_ylim(6.5, -0.5)
        ax.set_yticks(range(7), ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"])
        fig.colorbar(
            ScalarMappable(norm=norm, cmap=cmap), ax=ax, label=spec.aggregation
        )
        ax.set_title(str(d["calendar"]["year"]) + " · boş gün bilinmiyor")
    elif k == "radar":
        angles = [2 * math.pi * i / len(spec.columns) for i in range(len(spec.columns))]
        for j, g in enumerate(d["radar"]["group_order"]):
            pp = [p for p in points if p["group"] == g]
            vals = [p["y"] for p in pp]
            ax.plot(
                angles + [angles[0]],
                vals + [vals[0]],
                label=g,
                color=palette[j % len(palette)],
                marker="o",
            )
            ax.fill(
                angles + [angles[0]],
                vals + [vals[0]],
                alpha=0.1,
                color=palette[j % len(palette)],
            )
        ax.set_xticks(angles, [labels[c] for c in spec.columns])
        ax.set_ylim(0, 1)
        ax.legend(loc="upper right", fontsize=8)
    return [ax], {p["point_id"]: ax for p in points}


def finish(result, spec, axes, fig):
    ax = axes[0]
    ax.set_title(
        ""
        if spec.kind != "calendar"
        else str(result["details"]["calendar"]["year"]) + " · boş gün bilinmiyor"
    )
    if spec.kind not in (
        "radar",
        "pie",
        "donut",
        "treemap",
        "sunburst",
        "sankey",
        "alluvial",
        "funnel",
    ):
        ax.set_xlabel(spec.xlabel or result["column_labels"].get(spec.x, "Kategori"))
        ax.set_ylabel(
            spec.ylabel
            or (
                "Yüzde · her X içindeki toplam"
                if spec.kind.startswith("percent")
                else "Gün"
                if spec.kind == "calendar"
                else spec.aggregation
            )
        )
    if spec.kind == "radar":
        ax.set_xlabel("")
        ax.set_ylabel("Per-column minmax [0,1]")
    fig.suptitle(
        spec.title or spec.kind, fontfamily=spec.font, fontsize=spec.font_size + 2
    )
