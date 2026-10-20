"""Small explicit composition schemas and reference totals; synthetic data only."""

from datetime import date

import polars as pl


def frame(kind):
    if kind in ("treemap", "sunburst"):
        return pl.DataFrame(
            dict(
                x=["root", "A", "B", "a1", "a2"],
                y=[0.0, 0.0, 6.0, 2.0, 2.0],
                parent=[None, "root", "root", "A", "A"],
            )
        )
    if kind in ("sankey", "alluvial"):
        return pl.DataFrame(
            dict(
                x=["S", "S", "M", "M"],
                y=[4.0, 6.0, 5.0, 5.0],
                target=["M", "M", "T1", "T2"],
            )
        )
    if kind == "waterfall":
        return pl.DataFrame(
            dict(
                x=["Start", "Gain", "Loss", "End"],
                y=[10.0, 4.0, -2.0, 12.0],
                role=["start", "change", "change", "end"],
            )
        )
    if kind == "funnel":
        return pl.DataFrame(
            dict(
                x=["Visit", "Visit", "Visit", "Visit", "Buy", "Buy", "Buy"],
                entity=["p1", "p2", "p3", "p1", "p1", "p2", "p1"],
            )
        )
    if kind == "calendar":
        return pl.DataFrame(
            dict(
                x=[
                    date(2024, 2, 28),
                    date(2024, 2, 29),
                    date(2024, 2, 29),
                    date(2024, 3, 1),
                ],
                y=[1.0, 2.0, 3.0, 4.0],
            )
        )
    if kind == "radar":
        return pl.DataFrame(
            dict(
                a=[0.0, 10.0, 20.0, 30.0],
                b=[100.0, 200.0, 300.0, 400.0],
                c=[-4.0, -2.0, 0.0, 2.0],
                g=["A", "A", "B", "B"],
            )
        )
    if kind in ("stacked-area", "percent-area"):
        return pl.DataFrame(
            dict(x=[1.0, 1.0, 2.0, 2.0], y=[2.0, 3.0, 4.0, 6.0], g=["A", "B", "A", "B"])
        )
    return pl.DataFrame(
        dict(
            x=["Small", "Large", "Small", "Large"],
            y=[1.0, 4.0, 1.0, 4.0],
            g=["A", "A", "B", "B"],
        )
    )


def options(kind, columns):
    ids = {c["name"]: c["id"] for c in columns}
    s = dict(kind=kind, x=ids.get("x", ""), y=ids.get("y", ""), aggregation="sum")
    if kind in ("stacked-bar", "percent-bar", "stacked-area", "percent-area"):
        s["group"] = ids["g"]
    if kind in ("treemap", "sunburst"):
        s["parent"] = ids["parent"]
    if kind in ("sankey", "alluvial"):
        s["target"] = ids["target"]
    if kind == "waterfall":
        s.update(
            waterfall_role=ids["role"], category_order=["Start", "Gain", "Loss", "End"]
        )
    if kind == "funnel":
        s.update(
            entity=ids["entity"], category_order=["Visit", "Buy"], aggregation="count"
        )
    if kind == "radar":
        s.update(
            aggregation="mean",
            columns=[ids[k] for k in ("a", "b", "c")],
            group=ids["g"],
            advanced=True,
        )
    return s
