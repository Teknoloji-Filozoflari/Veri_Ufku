"""Validated additive composition, hierarchy and flow; no implicit data repair."""

import math
from collections import defaultdict
from datetime import date, datetime, timedelta

import numpy as np

from veri_ufku.charts.contracts import COMPOSITION_SCHEMAS
from veri_ufku.charts.distributions import labels
from veri_ufku.storage.project_model import ProjectError


def total(values):
    try:
        result = math.fsum(values)
    except OverflowError:
        raise ProjectError(
            "Toplam sonlu Float64 değil; precision/ölçek seçimini inceleyin."
        ) from None
    if not math.isfinite(result):
        raise ProjectError("Toplam sonlu değil; veri sessizce düzeltilmedi.")
    return result


def ordered(spec, categories, required=False):
    unique = list(dict.fromkeys(categories))
    if spec.category_order:
        if set(spec.category_order) != set(unique):
            raise ProjectError(
                "Sıra tüm farklı kategori/aşama etiketlerini tam içermeli."
            )
        return list(spec.category_order)
    if required:
        raise ProjectError("Başlangıç/aşama sırasını açıkça seçin.")
    return unique


def calculate(spec, values, numbers, add, used, details, warnings, control):
    details.update(
        composition_version=1,
        input_schema=COMPOSITION_SCHEMAS[spec.kind],
        aggregation=spec.aggregation,
        normalization="none",
        missing_category=spec.missing_category,
        missing_measure_policy="excluded, not in denominator; no imputation",
        denominator_scope="selected version + explicit view/sample; included additive values",
        structural_rows=0,
    )
    included = set()
    if spec.kind in ("treemap", "sunburst"):
        hierarchy(spec, values, numbers, add, used, details, control)
        included.update(details.pop("included_indices"))
    elif spec.kind in ("sankey", "alluvial"):
        flow(spec, values, numbers, add, used, details, control)
        included.update(details.pop("included_indices"))
    elif spec.kind == "radar":
        arrays = {c: numbers(c) for c in spec.columns}
        eligible = [
            i
            for i in range(used)
            if all(arrays[c][i] is not None for c in spec.columns)
        ]
        if not eligible:
            raise ProjectError("Radar sonlu complete-case ölçüm ister.")
        groups = labels(values[spec.group]) if spec.group else ["All"] * used
        order = ordered(spec, [groups[i] for i in eligible])
        if len(order) > 6:
            raise ProjectError("Radar en fazla6 grup; dot/parallel seçin.")
        scales = {}
        for c in spec.columns:
            data = [arrays[c][i] for i in eligible]
            scales[c] = [min(data), max(data)]
        for g in order:
            indices = [i for i in eligible if groups[i] == g]
            for k, c in enumerate(spec.columns):
                lo, hi = scales[c]
                normalized = [
                    (arrays[c][i] - lo) / (hi - lo) if hi != lo else 0.5
                    for i in indices
                ]
                add(
                    2 * math.pi * k / len(spec.columns),
                    total(normalized) / len(indices),
                    indices,
                    label=g,
                    group=g,
                    column=c,
                )
        included.update(eligible)
        details.update(
            aggregation="group mean of complete-case per-column minmax",
            radar=dict(
                scales=scales,
                constant=0.5,
                columns=list(spec.columns),
                group_order=order,
                advanced=True,
                alternative="dot / parallel coordinates",
            ),
        )
        warnings.append(
            "Radar alanı eksen sırasına bağlıdır; farklı birimler per-column minmax ile normalize edilir. Dot/parallel daha açık alternatif."
        )
    elif spec.kind == "funnel":
        if any(v is None or not isinstance(v, str) or not v for v in values[spec.x]):
            raise ProjectError(
                "Funnel aşaması boş olmayan string olmalı; eksik aşama sessiz dışlanmaz."
            )
        stages = labels(values[spec.x])
        order = ordered(spec, stages, required=True)
        if len(order) > 12:
            raise ProjectError("Funnel en fazla12 aşama.")
        entities = values[spec.entity] if spec.funnel_unit == "people" else None
        previous = None
        duplicates = 0
        first = None
        for k, stage in enumerate(order):
            indices = [i for i in range(used) if stages[i] == stage]
            if entities is not None:
                if any(
                    entities[i] is None
                    or isinstance(entities[i], float)
                    and not math.isfinite(entities[i])
                    for i in indices
                ):
                    raise ProjectError("Funnel kişi kimliği eksik/nonfinite olamaz.")
                identities = {
                    (type(entities[i]).__name__, str(entities[i])) for i in indices
                }
                if previous is not None and not identities <= previous:
                    raise ProjectError(
                        "Funnel kişi cohort'u iç içe değil; önceki aşamaya katılmayan kişi var."
                    )
                duplicates += len(indices) - len(identities)
                amount = len(identities)
                previous = identities
            else:
                amount = len(indices)
                if previous is not None and amount > previous:
                    raise ProjectError(
                        "Funnel olay sayısı aşama sırasında artıyor; bağımsız olayları dönüşüm diye sunmayın."
                    )
                previous = amount
            first = amount if first is None else first
            add(
                k,
                amount,
                indices,
                label=stage,
                percent=100 * amount / first if first else 0,
            )
        included.update(range(used))
        details.update(
            aggregation="distinct entity per stage"
            if entities is not None
            else "event row count; repeats included",
            funnel=dict(
                unit=spec.funnel_unit,
                stage_order=order,
                duplicate_person_stage_events=duplicates,
                denominator=first,
                cohort="nested source identities"
                if entities is not None
                else "event counts; not individual conversion",
            ),
            denominator=first,
        )
    else:
        raw = values[spec.x]
        categories = labels(raw)
        measure = numbers(spec.y)
        groups = labels(values[spec.group]) if spec.group else [""] * used
        eligible = []
        for i in range(used):
            if (
                raw[i] is None
                and spec.missing_category == "exclude"
                or spec.group
                and values[spec.group][i] is None
                and spec.missing_category == "exclude"
            ):
                continue
            if measure[i] is None:
                if spec.aggregation == "count":
                    eligible.append(i)
                continue
            eligible.append(i)
        if spec.kind in (
            "pie",
            "donut",
            "pareto",
            "stacked-bar",
            "percent-bar",
            "stacked-area",
            "percent-area",
        ) and any(measure[i] is not None and measure[i] < 0 for i in eligible):
            raise ProjectError(
                "Pay/stacked grafik negatif katkı kabul etmez; waterfall/dot seçin."
            )
        if not eligible:
            raise ProjectError("Seçili kapsamda uygun katkı yok.")
        included.update(eligible)
        buckets = defaultdict(list)
        for i in eligible:
            buckets[categories[i], groups[i]].append(i)
        if len(buckets) > min(spec.point_limit, 500):
            raise ProjectError(
                "Kategori×seri önkontrolü500 hücre/nokta limiti; açık filtre seçin."
            )

        def aggregate(indices):
            if spec.aggregation == "count":
                return len(indices)
            a = [measure[i] for i in indices]
            if spec.aggregation == "sum":
                return total(a)
            if spec.aggregation == "mean":
                return total(a) / len(a)
            result = float(getattr(np, spec.aggregation)(a))
            if not math.isfinite(result):
                raise ProjectError("Agregasyon sonucu sonlu değil.")
            return result

        if spec.kind == "waterfall":
            if any(v is None for v in measure):
                raise ProjectError("Waterfall eksiksiz sonlu adım ölçümü ister.")
            order = ordered(spec, [categories[i] for i in eligible], required=True)
            if len(order) != len(eligible) or len(eligible) != used:
                raise ProjectError(
                    "Waterfall her adımda tek, eksiksiz kaynak satırı ister; toplama/sessiz dışlama yok."
                )
            roles = values[spec.waterfall_role]
            by = {categories[i]: i for i in eligible}
            if (
                len(order) < 2
                or roles[by[order[0]]] != "start"
                or roles[by[order[-1]]] != "end"
                or any(roles[by[k]] != "change" for k in order[1:-1])
            ):
                raise ProjectError("Waterfall sırası start → change… → end olmalı.")
            start = measure[by[order[0]]]
            current = start
            for k, label in enumerate(order):
                i = by[label]
                value = measure[i]
                role = roles[i]
                before = 0 if role in ("start", "end") else current
                if role == "change":
                    current = total([current, value])
                if role == "end" and not math.isclose(
                    current, value, rel_tol=1e-9, abs_tol=1e-12
                ):
                    raise ProjectError(
                        "Waterfall bitiş değeri başlangıç + ara değişimler ile uyuşmuyor."
                    )
                after = value if role in ("start", "end") else current
                add(
                    k,
                    after,
                    [i],
                    label=label,
                    bottom=min(before, after),
                    top=max(before, after),
                    delta=value,
                    role=role,
                )
            details.update(
                waterfall=dict(
                    start=start,
                    end=current,
                    order=order,
                    tolerance="rtol1e-9;atol1e-12",
                ),
                aggregation="verified start/change/end; no total double counting",
            )
        elif spec.kind == "calendar":
            if any(not isinstance(raw[i], (date, datetime)) for i in eligible):
                raise ProjectError(
                    "Takvim X Date/Datetime fiziksel tür ister; string tarih sessiz parse edilmez."
                )
            days = defaultdict(list)
            for i in eligible:
                d = raw[i].date() if isinstance(raw[i], datetime) else raw[i]
                days[d].append(i)
            first, last = min(days), max(days)
            if (last - first).days > 366 or len({d.year for d in days}) > 1:
                raise ProjectError(
                    "Takvim tek seçili yıl / en fazla366 gün; açık yıl filtresi seçin."
                )
            origin = date(first.year, 1, 1)
            origin -= timedelta(days=origin.weekday())
            for day, indices in sorted(days.items()):
                add(
                    (day - origin).days // 7,
                    day.weekday(),
                    indices,
                    label=day.isoformat(),
                    z=aggregate(indices),
                )
            details["calendar"] = dict(
                year=first.year,
                week_start="Monday",
                origin=origin.isoformat(),
                missing_days="blank: unknown, not zero",
                timezone="Datetime local calendar date; no implicit UTC conversion",
            )
        else:
            order = ordered(spec, [categories[i] for i in eligible])
            series = list(dict.fromkeys(groups[i] for i in eligible))
            if len(order) > 100 or len(series) > min(spec.top_n, 12):
                raise ProjectError("En fazla100 kategori/12 seri; açık filtre seçin.")
            if spec.kind in ("stacked-area", "percent-area"):
                if any(
                    raw[i] is None
                    or not isinstance(raw[i], (int, float, date, datetime))
                    or isinstance(raw[i], bool)
                    for i in eligible
                ):
                    raise ProjectError(
                        "Area yalnız sıralı numeric/date X ister; kategorilere sürekli anlam verilmez."
                    )
                coordinate = {categories[i]: raw[i] for i in eligible}
                if spec.category_order:
                    if any(
                        coordinate[a] >= coordinate[b] for a, b in zip(order, order[1:])
                    ):
                        raise ProjectError("Area X sırası artan olmalı.")
                else:
                    order.sort(key=coordinate.get)
                if any((c, g) not in buckets for c in order for g in series):
                    raise ProjectError(
                        "Area ortak X×seri grid eksik; sıfır katkı uydurulmadı."
                    )
            amounts = {
                (c, g): aggregate(indices) for (c, g), indices in buckets.items()
            }
            grand = total(amounts.values())
            if spec.kind in ("pie", "donut", "pareto"):
                if spec.group:
                    raise ProjectError(
                        "Bu toplam grafiği tek kategori alanı ister; grup/seri seçmeyin."
                    )
                if grand <= 0 or spec.kind in ("pie", "donut") and len(order) > 6:
                    raise ProjectError(
                        "Pie/donut en fazla6 kategori ve pozitif doğru toplam; Pareto pozitif toplam ister."
                    )
                if spec.kind == "pareto":
                    order.sort(key=lambda c: -amounts[c, ""])
                cumulative = 0
                for k, c in enumerate(order):
                    amount = amounts[c, ""]
                    cumulative = total([cumulative, amount])
                    add(
                        k,
                        amount,
                        buckets[c, ""],
                        label=c,
                        percent=100 * amount / grand,
                        cumulative_percent=100 * cumulative / grand,
                    )
                details.update(
                    denominator=grand,
                    category_order=order,
                    parts_policy="mutually exclusive X categories; each source row once",
                )
            elif spec.kind in ("dot", "lollipop"):
                if spec.group:
                    raise ProjectError(
                        "Dot/lollipop tek kategori; grup karşılaştırması için facet seçin."
                    )
                for k, c in enumerate(order):
                    add(k, amounts[c, ""], buckets[c, ""], label=c)
                details["category_order"] = order
            else:
                denominators = {
                    c: total(amounts.get((c, g), 0) for g in series) for c in order
                }
                if any(v <= 0 for v in denominators.values()):
                    raise ProjectError("Stacked için her X paydası pozitif olmalı.")
                for k, c in enumerate(order):
                    bottom = 0
                    for g in series:
                        amount = amounts.get((c, g), 0)
                        display = (
                            100 * amount / denominators[c]
                            if spec.kind.startswith("percent")
                            else amount
                        )
                        indices = buckets.get((c, g), [])
                        x = k
                        if "area" in spec.kind:
                            v = coordinate[c]
                            x = (
                                v.toordinal()
                                + (
                                    v.hour / 24
                                    + v.minute / 1440
                                    + v.second / 86400
                                    + v.microsecond / 86400000000
                                    if isinstance(v, datetime)
                                    else 0
                                )
                                if isinstance(v, date)
                                else float(v)
                            )
                        add(
                            x,
                            bottom + display,
                            indices,
                            label=c,
                            group=g,
                            bottom=bottom,
                            top=bottom + display,
                            value=amount,
                            percent=100 * amount / denominators[c],
                        )
                        bottom += display
                details.update(
                    denominators=denominators,
                    grand_total=grand,
                    category_order=order,
                    series_order=series,
                    normalization="100 percent per X"
                    if spec.kind.startswith("percent")
                    else "additive; baseline zero",
                    area_interpolation="linear between observed ordered coordinates; not integrated total"
                    if "area" in spec.kind
                    else "none",
                )
        details["missing_measure_n"] = sum(v is None for v in measure)
        details["missing_category_n"] = sum(v is None for v in raw)
        details["count_policy"] = (
            "count includes rows with missing Y"
            if spec.aggregation == "count"
            else "missing Y excluded from aggregate and denominator"
        )
    details.update(included_n=len(included), excluded_rows=used - len(included))
    control.check()


def hierarchy(spec, values, numbers, add, used, details, control):
    nodes = values[spec.x]
    parents = values[spec.parent]
    measure = numbers(spec.y)
    if (
        used > 200
        or any(not isinstance(n, str) or not n for n in nodes)
        or len(set(nodes)) != used
    ):
        raise ProjectError(
            "Hiyerarşi en fazla200 benzersiz, boş olmayan string node ID ister; double counting/aynı düğüm tekrarı ret."
        )
    indices = {n: i for i, n in enumerate(nodes)}
    children = defaultdict(list)
    roots = []
    if any(v is None or v < 0 for v in measure):
        raise ProjectError("Hiyerarşi değerleri eksik/nonfinite/negatif olamaz.")
    for n, p in zip(nodes, parents):
        if p is None:
            roots.append(n)
        elif p not in indices:
            raise ProjectError(
                "Hiyerarşi parent mevcut node ID olmalı veya root için null."
            )
        else:
            children[p].append(n)
    colors = {}
    depth = {}
    desc = {}
    sums = {}

    def visit(n, d):
        if colors.get(n) == 1:
            raise ProjectError("Hiyerarşide cycle var.")
        if colors.get(n) == 2:
            return
        if d > 8:
            raise ProjectError("Hiyerarşi derinliği8 sınırını aşıyor.")
        colors[n] = 1
        depth[n] = d
        members = [indices[n]]
        for c in children[n]:
            visit(c, d + 1)
            members.extend(desc[c])
        if children[n] and measure[indices[n]] != 0:
            raise ProjectError(
                "Double counting: iç düğüm değeri0 olmalı; yalnız yapraklar toplama katılır."
            )
        sums[n] = (
            total(sums[c] for c in children[n]) if children[n] else measure[indices[n]]
        )
        desc[n] = members
        colors[n] = 2

    # Audit every component, including a disconnected cycle.
    for n in roots:
        visit(n, 0)
    for n in nodes:
        if colors.get(n) != 2:
            visit(n, 0)
    if len(roots) != 1 or sums[roots[0]] <= 0:
        raise ProjectError("Hiyerarşi bir root ve pozitif yaprak toplamı ister.")
    root = roots[0]
    rects = {}
    angles = {}

    def layout(n, x, y, w, h, a, b):
        rects[n] = [float(v) for v in (x, y, w, h)]
        angles[n] = [float(a), float(b)]
        cursor = x if depth[n] % 2 == 0 else y
        angle = a
        for c in children[n]:
            fraction = sums[c] / sums[n] if sums[n] else 0
            if depth[n] % 2 == 0:
                layout(c, cursor, y, w * fraction, h, angle, angle + (b - a) * fraction)
                cursor += w * fraction
            else:
                layout(c, x, cursor, w, h * fraction, angle, angle + (b - a) * fraction)
                cursor += h * fraction
            angle += (b - a) * fraction

    layout(root, 0, 0, 1, 1, 0, 360)
    represented = set()
    for n in nodes:
        control.check()
        if sums[n] <= 0:
            continue
        if spec.kind == "treemap" and children[n]:
            continue
        x, y, w, h = rects[n]
        a, b = angles[n]
        r = depth[n] + 0.5
        members = (
            desc[n]
            if spec.kind == "sunburst"
            else [indices[n]]
            + [indices[p] for p in ancestor_chain(n, indices, parents)]
        )
        represented.update(members)
        px, py = (
            (x + w / 2, y + h / 2)
            if spec.kind == "treemap"
            else (
                r * math.cos(math.radians((a + b) / 2)),
                r * math.sin(math.radians((a + b) / 2)),
            )
        )
        add(
            px,
            py,
            members,
            label=n,
            value=sums[n],
            rect=rects[n],
            theta=[a, b],
            depth=depth[n],
            percent=100 * sums[n] / sums[root],
        )
    details.update(
        denominator=sums[root],
        included_indices=list(represented),
        structural_rows=sum(bool(children[n]) for n in nodes),
        hierarchy=dict(
            root=root,
            zero_nodes=[n for n in nodes if sums[n] == 0],
            leaf_total=sums[root],
            node_totals=sums,
            depth=depth,
            parent=dict(zip(nodes, parents)),
            layout="slice-and-dice alternating depth"
            if spec.kind == "treemap"
            else "angular fraction of parent; radial depth rings",
            double_counting="internal source values must be0; descendant sums are display totals, never re-summed",
        ),
    )


def ancestor_chain(n, indices, parents):
    chain = []
    p = parents[indices[n]]
    while p is not None:
        chain.append(p)
        p = parents[indices[p]]
    return chain


def flow(spec, values, numbers, add, used, details, control):
    sources, targets, amounts = values[spec.x], values[spec.target], numbers(spec.y)
    if any(not isinstance(v, str) or not v for v in sources + targets) or any(
        v is None or v < 0 for v in amounts
    ):
        raise ProjectError(
            "Akış source/target boş olmayan string; value sonlu ve nonnegative olmalı."
        )
    edges = defaultdict(list)
    for i, (s, t, v) in enumerate(zip(sources, targets, amounts)):
        if s == t:
            raise ProjectError("Akış cycle/self-loop desteklenmez.")
        if v > 0:
            edges[s, t].append(i)
    nodes = list(dict.fromkeys(sources + targets))
    if len(nodes) > 50 or len(edges) > 100 or not edges:
        raise ProjectError("Akış en fazla50 node/100edge ve pozitif akış ister.")
    weights = {
        edge: total(amounts[i] for i in indices) for edge, indices in edges.items()
    }
    incoming = defaultdict(list)
    outgoing = defaultdict(list)
    for (s, t), v in weights.items():
        outgoing[s].append(t)
        incoming[t].append(s)
    indegree = {n: len(incoming[n]) for n in nodes}
    queue = [n for n in nodes if not indegree[n]]
    levels = {n: 0 for n in queue}
    visited = []
    while queue:
        n = queue.pop(0)
        visited.append(n)
        for t in outgoing[n]:
            levels[t] = max(levels.get(t, 0), levels[n] + 1)
            indegree[t] -= 1
            if not indegree[t]:
                queue.append(t)
    if len(visited) != len(nodes):
        raise ProjectError("Akış graph cycle içeriyor; DAG gerekli.")
    ins = {n: total(weights[s, n] for s in incoming[n]) for n in nodes}
    outs = {n: total(weights[n, t] for t in outgoing[n]) for n in nodes}
    for n in nodes:
        if (
            incoming[n]
            and outgoing[n]
            and not math.isclose(ins[n], outs[n], rel_tol=1e-9, abs_tol=1e-12)
        ):
            raise ProjectError("Dengesiz akış: iç node giriş/çıkış uyuşmuyor: " + n)
    if spec.kind == "alluvial" and any(levels[t] != levels[s] + 1 for s, t in edges):
        raise ProjectError(
            "Alluvial yalnız bitişik aşamalar; uzun atlayan edge için Sankey seçin."
        )
    boundary = total(outs[n] for n in nodes if not incoming[n])
    sink = total(ins[n] for n in nodes if not outgoing[n])
    if not math.isclose(boundary, sink, rel_tol=1e-9, abs_tol=1e-12):
        raise ProjectError("Toplam kaynak/sink akışı uyuşmuyor.")
    boxes = {}
    for level in sorted(set(levels.values())):
        cursor = 0
        for n in nodes:
            if levels[n] != level:
                continue
            height = max(ins[n], outs[n]) / boundary
            boxes[n] = [level, cursor, height]
            cursor += height + 0.08
    in_cursor = {n: boxes[n][1] for n in nodes}
    out_cursor = dict(in_cursor)
    for (s, t), v in weights.items():
        control.check()
        width = v / boundary
        start = out_cursor[s]
        end = in_cursor[t]
        out_cursor[s] += width
        in_cursor[t] += width
        add(
            (levels[s] + levels[t]) / 2,
            (start + end + width) / 2,
            edges[s, t],
            label=s + " → " + t,
            value=v,
            source=s,
            target=t,
            flow_width=width,
            source_bottom=start,
            target_bottom=end,
            source_x=levels[s] + 0.06,
            target_x=levels[t] - 0.06,
        )
    details.update(
        denominator=boundary,
        included_indices=[i for indices in edges.values() for i in indices],
        flow=dict(
            incoming=ins,
            outgoing=outs,
            levels=levels,
            nodes=boxes,
            source_total=boundary,
            sink_total=sink,
            edge_total=total(weights.values()),
            zero_excluded=sum(v == 0 for v in amounts),
            balance_tolerance="rtol1e-9;atol1e-12",
            semantics="aggregated edge quantities; repeated transit counted once per edge, boundary total is denominator; no inferred individual paths",
        ),
    )


def preflight(spec, used, control):
    """Reject exact node/step explosions before materializing selected data."""
    if spec.kind in ("treemap", "sunburst") and used > 200:
        raise ProjectError(
            "Hiyerarşi önkontrolü: en fazla200 kaynak node; açık filtre seçin."
        )
    if spec.kind == "waterfall" and used > 100:
        raise ProjectError("Waterfall önkontrolü: en fazla100 benzersiz adım.")
    if (
        spec.kind == "radar"
        and used * len(spec.columns) * 160 > control.budget.ram_bytes // 2
    ):
        raise ProjectError(
            "Radar ölçüm matrisi RAM önkontrolünü aşıyor; açık örnek seçin."
        )
