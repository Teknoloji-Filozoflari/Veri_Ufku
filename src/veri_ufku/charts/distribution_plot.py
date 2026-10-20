"""Render stored distribution coordinates without repeating analytical calculations."""

import math

import numpy as np
from matplotlib.ticker import FixedLocator, PercentFormatter

from veri_ufku.storage.project_model import ProjectError

TITLES = {
    "histogram": "Histogram",
    "box": "Kutu grafiği",
    "violin": "Violin · yoğunluk",
    "kde": "KDE · yoğunluk",
    "ecdf": "ECDF · birikimli olasılık",
    "rug": "Rug · gözlenen değerler",
    "strip": "Strip · gözlenen değerler",
    "swarm": "Swarm · gözlenen değerler",
    "qq": "QQ · normal referans",
    "pp": "PP · normal referans",
    "error-bar": "Ortalama ve hata çubuğu",
    "ci-band": "Ortalama ve noktasal belirsizlik bandı",
    "missing-pattern": "Eksiklik desenleri",
}


def draw(result, spec, fig, palette):
    points = result["points"]
    facets = result["details"].get("facets", [""])
    axes, point_axes = [], {}
    groups = result["details"].get("group_order", [""])
    for fi, facet in enumerate(facets):
        ax = fig.add_subplot(1 if len(facets) < 3 else 2, min(2, len(facets)), fi + 1)
        axes.append(ax)
        subset = [p for p in points if p.get("facet", "") == facet]
        ax.set_title(facet if len(facets) > 1 else "", fontsize=spec.font_size)
        for gi, group in enumerate(groups):
            ps = [p for p in subset if p.get("group", "") == group]
            if not ps:
                continue
            for p in ps:
                point_axes[p["point_id"]] = ax
            xs, ys = [p["x"] for p in ps], [p["y"] for p in ps]
            color = palette[gi % len(palette)]
            if spec.kind == "histogram":
                ax.bar(
                    xs,
                    ys,
                    width=[p["right"] - p["left"] for p in ps],
                    alpha=0.55,
                    color=color,
                    label=group,
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
                        for p in ps
                    ],
                    positions=xs,
                    patch_artist=True,
                    boxprops=dict(facecolor=color, alpha=0.65),
                )
            elif spec.kind == "violin":
                densities = np.array([p["density"] for p in ps])
                width = densities / max(densities) * 0.35
                ax.fill_betweenx(
                    ys,
                    np.array(xs) - width,
                    np.array(xs) + width,
                    color=color,
                    alpha=0.65,
                    label=group,
                )
            elif spec.kind == "kde":
                ax.plot(xs, ys, color=color, label=group)
            elif spec.kind == "ecdf":
                ax.step(xs, ys, where="post", color=color, label=group)
            elif spec.kind == "rug":
                ax.scatter(xs, ys, marker="|", s=100, color=color, label=group)
            elif spec.kind in ("strip", "swarm", "qq", "pp"):
                ax.scatter(xs, ys, s=18, color=color, label=group, alpha=0.75)
                if spec.kind == "qq":
                    sample = next(
                        s
                        for s in result["details"]["samples"]
                        if s["facet"] == facet and s["group"] == group
                    )
                    ax.plot(
                        xs,
                        [sample["mean"] + sample["sd"] * v for v in xs],
                        linestyle="--",
                        color=color,
                    )
                elif spec.kind == "pp":
                    ax.plot([0, 1], [0, 1], linestyle="--", color=color)
            elif spec.kind in ("error-bar", "ci-band"):
                ps = sorted(ps, key=lambda p: p["x"])
                xs, ys = [p["x"] for p in ps], [p["y"] for p in ps]
                lo, hi = [p["lower"] for p in ps], [p["upper"] for p in ps]
                if spec.kind == "error-bar":
                    ax.errorbar(
                        xs,
                        ys,
                        yerr=[
                            [v - lower for v, lower in zip(ys, lo)],
                            [h - v for h, v in zip(hi, ys)],
                        ],
                        fmt="o",
                        capsize=4,
                        color=color,
                        label=group,
                    )
                    ax.set_xticks(xs, [p["label"] for p in ps], rotation=25)
                else:
                    ax.plot(xs, ys, marker="o", color=color, label=group)
                    ax.fill_between(xs, lo, hi, color=color, alpha=0.2)
            else:
                ax.bar(xs, ys, color=color)
                ax.set_xticks(xs, [p["label"] for p in ps], rotation=25)
        if spec.kind in ("box", "violin", "strip", "swarm"):
            ax.set_xticks(
                range(len(groups)), [g or "Dağılım" for g in groups], rotation=25
            )
        if spec.kind == "rug":
            ax.set_yticks(range(len(groups)), [g or "Dağılım" for g in groups])
        if spec.kind == "histogram" and spec.normalization == "percent":
            ax.yaxis.set_major_formatter(PercentFormatter(100))
        if (
            spec.legend
            and any(groups)
            and spec.kind not in ("box", "strip", "swarm", "missing-pattern")
        ):
            ax.legend(fontsize=8)
    fig.subplots_adjust(wspace=0.45, hspace=0.65)
    return axes, point_axes


def validate_scales(result, spec, bounds):
    # Reject before Matplotlib can silently clip nonpositive measurements/endpoints.
    points = result["points"]
    for axis, scale in (("x", spec.xscale), ("y", spec.yscale)):
        if scale != "log":
            continue
        vals = [p[axis] for p in points if p[axis] is not None]
        if axis == "x" and spec.kind == "histogram":
            vals.extend(p["left"] for p in points)
        if axis == "y" and spec.kind in ("box", "error-bar", "ci-band"):
            vals.extend(p.get("lower", p.get("whislo")) for p in points)
            vals.extend(v for p in points for v in p.get("fliers", []))
        bad = sum(v is None or not math.isfinite(v) or v <= 0 for v in vals)
        if bad:
            raise ProjectError(
                f"Log {axis}: {bad} sıfır/negatif veya tanımsız çizim değeri. Linear/symlog seçin; sessiz kırpma yok."
            )
        if bounds and bounds[0 if axis == "x" else 2] <= 0:
            raise ProjectError("Log eksen sınırı pozitif olmalı.")


def style(axes, spec, bounds):
    for ax in axes:
        for axis, scale in (("x", spec.xscale), ("y", spec.yscale)):
            setter = ax.set_xscale if axis == "x" else ax.set_yscale
            axis_object = ax.xaxis if axis == "x" else ax.yaxis
            fixed = isinstance(axis_object.get_major_locator(), FixedLocator)
            ticks = (
                (ax.get_xticks() if axis == "x" else ax.get_yticks()) if fixed else []
            )
            labels = (
                [
                    t.get_text()
                    for t in (
                        ax.get_xticklabels() if axis == "x" else ax.get_yticklabels()
                    )
                ]
                if fixed
                else []
            )
            if scale != "linear":
                setter(
                    scale,
                    **({"linthresh": spec.linthresh} if scale == "symlog" else {}),
                )
                if fixed:
                    (ax.set_xticks if axis == "x" else ax.set_yticks)(ticks, labels)
        for text in [
            ax.title,
            ax.xaxis.label,
            ax.yaxis.label,
            *ax.get_xticklabels(),
            *ax.get_yticklabels(),
        ]:
            text.set_fontfamily(spec.font)
            text.set_fontsize(spec.font_size)
        if spec.annotation:
            ax.text(
                0.02,
                0.98,
                spec.annotation,
                transform=ax.transAxes,
                va="top",
                fontsize=spec.font_size,
                fontfamily=spec.font,
                bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"},
            )
        if bounds:
            ax.set_xlim(bounds[:2])
            ax.set_ylim(bounds[2:])
