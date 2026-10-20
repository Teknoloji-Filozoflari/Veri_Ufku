"""Independent totals, geometry, invalid graph audits and immutable publications."""

import copy
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import polars as pl
import pytest
from phase37_fixtures import frame, options
from test_dataset import column, prepare

from veri_ufku.charts.contracts import COMPOSITION_KINDS, COMPOSITION_SCHEMAS, ChartSpec
from veri_ufku.charts.engine import calculate, select
from veri_ufku.charts.plot import render
from veri_ufku.domain.capabilities import CAPABILITIES
from veri_ufku.storage.chart_store import publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


@pytest.mark.parametrize("kind", COMPOSITION_KINDS)
def test_every_composition_schema_render_membership_publish_reopen(tmp_path, kind):
    store, r, work = prepare(tmp_path, frame(kind))
    root = store.root
    original = Path(r["path"]).read_bytes()
    with closing(store):
        spec = ChartSpec.from_dict(options(kind, r["columns"]))
        result = render(calculate(r, spec, work), work)
        assert result["details"]["input_schema"] == COMPOSITION_SCHEMAS[kind]
        assert CAPABILITIES["chart." + kind].input_schema == COMPOSITION_SCHEMAS[kind]
        assert result["details"]["excluded_rows"] == 0
        source_ids = set(pl.read_parquet(r["path"])["__vu_row_id"])
        memberships = pl.read_parquet(result["paths"]["members"])
        assert set(memberships["row_id"]) == source_ids
        for p in result["points"]:
            selected = select(result, [p["point_id"]])
            expected = memberships.filter(pl.col("point_id") == p["point_id"])["row_id"]
            assert set(selected["row_ids"]) == set(expected)
        for fmt in ("png", "svg", "pdf"):
            assert Path(result["paths"][fmt]).stat().st_size > 1000
        publish(store, copy.deepcopy(store.state), result)
        assert Path(r["path"]).read_bytes() == original
    with closing(ProjectStore.open(root)) as reopened:
        assert reopened.state["results"][-1]["chart"]["details"] == result["details"]


@pytest.mark.parametrize("kind", ["percent-bar", "percent-area"])
def test_stacked_reference_per_x_denominator_and_percent(tmp_path, kind):
    store, r, work = prepare(tmp_path, frame(kind))
    with closing(store):
        result = calculate(r, ChartSpec.from_dict(options(kind, r["columns"])), work)
        for x in {p["x"] for p in result["points"]}:
            points = [p for p in result["points"] if p["x"] == x]
            assert sum(p["percent"] for p in points) == pytest.approx(100)
            assert points[-1]["top"] == pytest.approx(100)
        assert result["details"]["grand_total"] == (15 if "area" in kind else 10)


def test_pareto_pie_leaf_area_and_ring_reference_totals(tmp_path):
    for kind in ("pareto", "pie", "donut", "treemap", "sunburst"):
        d = tmp_path / kind
        d.mkdir()
        store, r, work = prepare(d, frame(kind))
        with closing(store):
            result = calculate(
                r, ChartSpec.from_dict(options(kind, r["columns"])), work
            )
            assert result["details"]["denominator"] == 10
            if kind == "pareto":
                assert [p["y"] for p in result["points"]] == [8.0, 2.0]
                assert [p["cumulative_percent"] for p in result["points"]] == [
                    80.0,
                    100.0,
                ]
            if kind == "treemap":
                assert sum(
                    p["rect"][2] * p["rect"][3] for p in result["points"]
                ) == pytest.approx(1)
                for p in result["points"]:
                    assert p["rect"][2] * p["rect"][3] == pytest.approx(p["value"] / 10)
            if kind == "sunburst":
                for depth in (0, 1, 2):
                    points = [p for p in result["points"] if p["depth"] == depth]
                    # Ring2 represents only descendants of internal A (40%); terminal B does not invent descendants.
                    assert sum(
                        p["theta"][1] - p["theta"][0] for p in points
                    ) == pytest.approx(360 if depth < 2 else 144)


@pytest.mark.parametrize("problem", ["cycle", "internal-value", "duplicate", "orphan"])
def test_hierarchy_no_cycle_or_double_counting(tmp_path, problem):
    f = frame("treemap").to_dict(as_series=False)
    if problem == "cycle":
        f["parent"] = ["A", "root", "root", "A", "A"]
    if problem == "internal-value":
        f["y"][0] = 10.0
    if problem == "duplicate":
        f["x"][-1] = "a1"
    if problem == "orphan":
        f["parent"][-1] = "missing"
    store, r, work = prepare(tmp_path, pl.DataFrame(f))
    with closing(store), pytest.raises(ProjectError):
        calculate(r, ChartSpec.from_dict(options("treemap", r["columns"])), work)


@pytest.mark.parametrize("problem", ["negative", "imbalance", "cycle", "nonfinite"])
def test_flow_invalid_and_boundary_not_edge_double_count(tmp_path, problem):
    f = frame("sankey").to_dict(as_series=False)
    if problem == "negative":
        f["y"][0] = -1.0
    if problem == "imbalance":
        f["y"][-1] = 4.0
    if problem == "cycle":
        f["target"][-1] = "S"
    if problem == "nonfinite":
        f["y"][0] = float("nan")
    store, r, work = prepare(tmp_path, pl.DataFrame(f))
    with closing(store), pytest.raises(ProjectError):
        calculate(r, ChartSpec.from_dict(options("sankey", r["columns"])), work)


def test_flow_reference_width_balance_and_waterfall_endpoint(tmp_path):
    for kind in ("sankey", "waterfall"):
        d = tmp_path / kind
        d.mkdir()
        store, r, work = prepare(d, frame(kind))
        with closing(store):
            result = calculate(
                r, ChartSpec.from_dict(options(kind, r["columns"])), work
            )
            if kind == "sankey":
                assert result["details"]["flow"]["source_total"] == 10
                assert result["details"]["flow"]["edge_total"] == 20
                assert sorted(p["flow_width"] for p in result["points"]) == [
                    0.5,
                    0.5,
                    1.0,
                ]
            else:
                assert [p["y"] for p in result["points"]] == [10.0, 14.0, 12.0, 12.0]
                assert result["details"]["waterfall"]["end"] == 12
    f = frame("waterfall").with_columns(
        pl.when(pl.col("x") == "End").then(13.0).otherwise(pl.col("y")).alias("y")
    )
    d = tmp_path / "bad"
    d.mkdir()
    store, r, work = prepare(d, f)
    with closing(store), pytest.raises(ProjectError, match="bitiş"):
        calculate(r, ChartSpec.from_dict(options("waterfall", r["columns"])), work)


def test_funnel_people_repeats_events_and_wrong_cohort(tmp_path):
    store, r, work = prepare(tmp_path, frame("funnel"))
    with closing(store):
        spec = ChartSpec.from_dict(options("funnel", r["columns"]))
        people = calculate(r, spec, work)
        events = calculate(r, replace(spec, funnel_unit="events", entity=""), work)
        assert [p["y"] for p in people["points"]] == [3.0, 2.0]
        assert [p["y"] for p in events["points"]] == [4.0, 3.0]
        assert people["details"]["funnel"]["duplicate_person_stage_events"] == 2
        assert people["points"][-1]["percent"] == pytest.approx(200 / 3)
    d = tmp_path / "bad"
    d.mkdir()
    f = frame("funnel").with_columns(
        pl.when(pl.col("x") == "Buy")
        .then(pl.lit("new_person"))
        .otherwise(pl.col("entity"))
        .alias("entity")
    )
    store, r, work = prepare(d, f)
    with closing(store), pytest.raises(ProjectError, match="cohort"):
        calculate(r, ChartSpec.from_dict(options("funnel", r["columns"])), work)


@pytest.mark.parametrize("policy,total", [("include", 12.0), ("exclude", 8.0)])
def test_missing_denominator_policy_is_visible(tmp_path, policy, total):
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=["A", None, "A", "B"], y=[2.0, 4.0, None, 6.0]))
    )
    with closing(store):
        spec = ChartSpec(
            "pie",
            x=column(r, "x"),
            y=column(r, "y"),
            aggregation="sum",
            missing_category=policy,
        )
        result = calculate(r, spec, work)
        assert result["details"]["denominator"] == total
        assert result["details"]["missing_measure_n"] == 1
        assert result["details"]["missing_category"] == policy
        count = calculate(r, replace(spec, aggregation="count"), work)
        assert count["details"]["denominator"] == (4 if policy == "include" else 3)


def test_calendar_leap_day_and_radar_normalized_units(tmp_path):
    for kind in ("calendar", "radar"):
        d = tmp_path / kind
        d.mkdir()
        store, r, work = prepare(d, frame(kind))
        with closing(store):
            spec = ChartSpec.from_dict(options(kind, r["columns"]))
            result = calculate(r, spec, work)
            if kind == "calendar":
                leap = next(p for p in result["points"] if p["label"] == "2024-02-29")
                assert leap["y"] == 3 and leap["z"] == 5 and leap["n"] == 2
                assert result["details"]["calendar"]["missing_days"].startswith("blank")
            else:
                assert [p["y"] for p in result["points"][:3]] == pytest.approx(
                    [1 / 6] * 3
                )
                assert result["details"]["radar"]["scales"][column(r, "b")] == [
                    100.0,
                    400.0,
                ]
                with pytest.raises(ProjectError, match="advanced"):
                    calculate(r, replace(spec, advanced=False), work)


def test_pie_category_and_area_string_limits(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=list("ABCDEFG"), y=[1.0] * 7, g=["S"] * 7))
    )
    with closing(store):
        with pytest.raises(ProjectError, match="6 kategori"):
            calculate(
                r,
                ChartSpec("pie", x=column(r, "x"), y=column(r, "y"), aggregation="sum"),
                work,
            )
        with pytest.raises(ProjectError, match="Area yalnız"):
            calculate(
                r,
                ChartSpec(
                    "stacked-area",
                    x=column(r, "x"),
                    y=column(r, "y"),
                    group=column(r, "g"),
                    aggregation="sum",
                ),
                work,
            )


@pytest.mark.parametrize(
    "kind", ["treemap", "sunburst", "sankey", "alluvial", "waterfall"]
)
def test_value_schema_rejects_count_instead_of_summing(tmp_path, kind):
    store, r, work = prepare(tmp_path, frame(kind))
    with closing(store), pytest.raises(ProjectError, match="agregasyon"):
        calculate(
            r,
            replace(
                ChartSpec.from_dict(options(kind, r["columns"])), aggregation="count"
            ),
            work,
        )


def test_alluvial_skip_stage_controlled_sankey_valid(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            dict(x=["S", "S", "A"], target=["A", "T", "T"], y=[4.0, 6.0, 4.0])
        ),
    )
    with closing(store):
        sankey = calculate(
            r, ChartSpec.from_dict(options("sankey", r["columns"])), work
        )
        assert sankey["details"]["denominator"] == 10
        with pytest.raises(ProjectError, match="bitişik"):
            calculate(r, ChartSpec.from_dict(options("alluvial", r["columns"])), work)


@pytest.mark.parametrize("problem", ["missing", "roles", "repeated"])
def test_waterfall_incomplete_roles_and_repeated_steps(tmp_path, problem):
    f = frame("waterfall").to_dict(as_series=False)
    if problem == "missing":
        f["y"][1] = None
    if problem == "roles":
        f["role"][1] = "end"
    if problem == "repeated":
        f["x"][1] = "Start"
    store, r, work = prepare(tmp_path, pl.DataFrame(f))
    with closing(store), pytest.raises(ProjectError):
        calculate(r, ChartSpec.from_dict(options("waterfall", r["columns"])), work)


@pytest.mark.parametrize("kind", ["pie", "percent-bar"])
def test_nonpositive_denominator_and_negative_part_rejected(tmp_path, kind):
    f = frame("stacked-bar").with_columns(pl.lit(0.0).alias("y"))
    store, r, work = prepare(tmp_path, f)
    with closing(store), pytest.raises(ProjectError, match="pozitif"):
        calculate(r, ChartSpec.from_dict(options(kind, r["columns"])), work)


def test_count_missing_y_and_excluded_group_explicit(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(dict(x=["X", "X", "X"], y=[1.0, None, 3.0], g=["A", None, "B"])),
    )
    with closing(store):
        spec = ChartSpec.from_dict(options("percent-bar", r["columns"]))
        result = calculate(
            r, replace(spec, aggregation="count", missing_category="exclude"), work
        )
        assert result["details"]["denominators"] == {"X": 2.0}
        assert result["details"]["excluded_rows"] == 1
        assert result["details"]["count_policy"].startswith("count includes")


def test_calendar_string_and_cross_year_rejected(tmp_path):
    store, r, work = prepare(tmp_path, pl.DataFrame(dict(x=["2024-01-01"], y=[2.0])))
    with closing(store), pytest.raises(ProjectError, match="fiziksel tür"):
        calculate(r, ChartSpec.from_dict(options("calendar", r["columns"])), work)
    from datetime import date

    d = tmp_path / "year"
    d.mkdir()
    store, r, work = prepare(
        d, pl.DataFrame(dict(x=[date(2023, 12, 31), date(2024, 1, 1)], y=[2.0, 3.0]))
    )
    with closing(store), pytest.raises(ProjectError, match="tek seçili yıl"):
        calculate(r, ChartSpec.from_dict(options("calendar", r["columns"])), work)


def test_zero_leaf_accounted_without_fabricated_area(tmp_path):
    f = frame("treemap").with_columns(
        pl.when(pl.col("x") == "a2").then(0.0).otherwise(pl.col("y")).alias("y")
    )
    store, r, work = prepare(tmp_path, f)
    with closing(store):
        result = calculate(
            r, ChartSpec.from_dict(options("treemap", r["columns"])), work
        )
        assert result["details"]["hierarchy"]["zero_nodes"] == ["a2"]
        assert result["details"]["excluded_rows"] == 1
        assert sum(p["value"] for p in result["points"]) == 8


def test_hierarchy_source_preflight_rejects_before_calculation(tmp_path):
    n = 201
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            dict(
                x=[str(i) for i in range(n)],
                parent=[None] + ["0"] * (n - 1),
                y=[0.0] + [1.0] * (n - 1),
            )
        ),
    )
    with closing(store), pytest.raises(ProjectError, match="önkontrol"):
        calculate(r, ChartSpec.from_dict(options("treemap", r["columns"])), work)
