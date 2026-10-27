"""Read-only Python text for a chart spec. This module does not execute it."""

import json

CORE_KINDS = frozenset({"histogram", "box", "bar", "line", "scatter", "missing"})
RELATION_KINDS = frozenset({"scatter", "correlation", "line"})
BAR_METHODS = frozenset({"sum", "mean", "median", "min", "max", "size"})


def chart_python_snippet(spec, columns):
    """Return a pandas/matplotlib sketch that uses the same column names as the chart."""
    spec = spec or {}
    kind = str(spec.get("kind") or "")
    if not kind:
        return "# Grafik henüz yok. Kod, oluşturulan belirtimle birlikte yazılır.\n"
    if kind not in CORE_KINDS and kind != "correlation":
        return (
            f"# {kind} çekirdek Python görünümünün dışında.\n"
            "# Bu şema için sahte grafik ve sahte kod üretilmez.\n"
        )
    names = {
        item.get("id"): item.get("name")
        for item in columns or []
        if item.get("id") and item.get("name")
    }
    x = names.get(spec.get("x") or "", "")
    y = names.get(spec.get("y") or "", "")
    group = names.get(spec.get("group") or "", "")
    chosen = [names[item] for item in spec.get("columns") or [] if item in names]
    lines = [
        "import matplotlib.pyplot as plt",
        "import pandas as pd",
        "",
        "# Veri_Ufku belirtimi. Bu metin burada çalıştırılmaz.",
        f"# kind={kind}",
    ]
    if x:
        lines.append(f"# x={x}")
    if y:
        lines.append(f"# y={y}")
    if spec.get("used_n") is not None:
        lines.append(f"# n={spec['used_n']}")
    if spec.get("scope"):
        lines.append(f"# kapsam={spec['scope']}")
    if kind in RELATION_KINDS or spec.get("purpose") == "relationship":
        lines.append("# Bu bir ilişki özetidir. Nedensel etki değildir.")
    lines.extend(["", "fig, ax = plt.subplots()"])
    lines.extend(_plot(kind, spec, x, y, group, chosen))
    lines.append("")
    return "\n".join(lines)


def _plot(kind, spec, x, y, group, chosen):
    if kind == "histogram" and x:
        raw = spec.get("bins") or 10
        bins = raw if isinstance(raw, int) and raw > 0 else 10
        return [f"frame[{_lit(x)}].plot.hist(bins={bins}, ax=ax)"]
    if kind == "box" and x:
        if group:
            return [f"frame.boxplot(column={_lit(x)}, by={_lit(group)}, ax=ax)"]
        return [f"frame.boxplot(column={_lit(x)}, ax=ax)"]
    if kind == "bar" and x:
        return _bar(spec, x, y)
    if kind == "line" and x and y:
        return [f"frame.plot.line(x={_lit(x)}, y={_lit(y)}, ax=ax)"]
    if kind == "scatter" and x and y:
        return [f"frame.plot.scatter(x={_lit(x)}, y={_lit(y)}, ax=ax)"]
    if kind == "missing" and chosen:
        return [
            f"frame[{_list(chosen)}].isna().mean().plot.bar(ax=ax)",
            'ax.set_ylabel("missing_rate")',
        ]
    if kind == "correlation" and chosen:
        method = spec.get("correlation") or "pearson"
        if method not in {"pearson", "spearman"}:
            method = "pearson"
        listed = _list(chosen)
        return [
            f"matrix = frame[{listed}].corr(method={_lit(method)})",
            "ax.imshow(matrix.to_numpy())",
        ]
    return ["# Atanan sütun bu tür için eksik; grafik üretilmez."]


def _bar(spec, x, y):
    how = spec.get("aggregation") or "mean"
    if how == "count":
        how = "size"
    if y and how in BAR_METHODS:
        return [f"frame.groupby({_lit(x)})[{_lit(y)}].{how}().plot.bar(ax=ax)"]
    if not y:
        return [f"frame[{_lit(x)}].value_counts().plot.bar(ax=ax)"]
    return ["# Bu agregasyon çekirdek Python görünümünde yok."]


def _lit(value):
    return json.dumps(str(value), ensure_ascii=False)


def _list(values):
    return "[" + ", ".join(_lit(value) for value in values) + "]"
