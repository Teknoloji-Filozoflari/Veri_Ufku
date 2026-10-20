"""Independent references for Phase36 geometry, cell memberships and safe filters."""

import copy
import re
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from scipy.cluster.hierarchy import leaves_list, linkage
from test_dataset import column, prepare

from veri_ufku.charts.contracts import MULTIVARIATE_KINDS, ChartSpec
from veri_ufku.charts.engine import calculate, select
from veri_ufku.charts.multivariate import preflight
from veri_ufku.charts.plot import render
from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Control
from veri_ufku.operations.contracts import build
from veri_ufku.operations.engine import calculate as operation
from veri_ufku.storage.chart_store import publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def fixture(tmp_path):
    return prepare(
        tmp_path,
        pl.DataFrame(
            dict(
                x=[1.0, 2.0, 3.0, 4.0, 10.0, 20.0, 30.0, 40.0],
                y=[2.0, 4.0, 6.0, 8.0, 3.0, 5.0, 7.0, 9.0],
                size=[1.0, 2.0, 4.0, 8.0, 1.0, 2.0, 4.0, 8.0],
                g=["A"] * 4 + ["B"] * 4,
            )
        ),
    )


def specification(r, kind):
    return ChartSpec(
        kind,
        x=column(r, "x"),
        y=column(r, "y"),
        columns=(column(r, "x"), column(r, "y")),
        size=column(r, "size") if kind == "bubble" else "",
        group=column(r, "g") if kind not in ("hexbin", "density-2d") else "",
        facet=column(r, "g") if kind == "facets" else "",
        aggregation="mean",
        bins=2,
        grid_bins=4,
    )


@pytest.mark.parametrize("kind", MULTIVARIATE_KINDS)
def test_render_memberships_save_reopen_source(tmp_path, kind):
    store, r, work = fixture(tmp_path)
    root = store.root
    original = Path(r["path"]).read_bytes()
    with closing(store):
        spec = specification(r, kind)
        result = render(calculate(r, spec, work), work)
        assert result["details"]["included_n"] == 8
        members = pl.read_parquet(result["paths"]["members"])
        source_ids = pl.read_parquet(r["path"])["__vu_row_id"].to_list()
        assert set(members["row_id"]) == set(source_ids)
        for p in result["points"]:
            selection = select(result, [p["point_id"]])
            expected = members.filter(pl.col("point_id") == p["point_id"])[
                "row_id"
            ].to_list()
            assert set(selection["row_ids"]) == set(expected)
            assert selection["count"] == p["n"]
        assert len(result["render"]["panel_axes"]) == len(result["details"]["panels"])
        for fmt in ("png", "svg", "pdf"):
            assert Path(result["paths"][fmt]).stat().st_size > 1000
        publish(store, copy.deepcopy(store.state), result)
        assert Path(r["path"]).read_bytes() == original
    with closing(ProjectStore.open(root)) as reopened:
        assert reopened.state["results"][-1]["chart"]["details"] == result["details"]


@pytest.mark.parametrize("encoding", ["area", "radius"])
def test_bubble_actual_marker_area_formula(tmp_path, encoding):
    store, r, work = fixture(tmp_path)
    with closing(store):
        result = calculate(
            r, replace(specification(r, "bubble"), bubble_encoding=encoding), work
        )
        points = result["points"]
        ratio = points[2]["marker_area"] / points[0]["marker_area"]
        assert ratio == (4 if encoding == "area" else 16)
        assert result["details"]["bubble"]["legend_values"] == [2.0, 4.0, 8.0]


def test_density_integral_and_numpy_cell_counts(tmp_path):
    store, r, work = fixture(tmp_path)
    with closing(store):
        result = calculate(r, specification(r, "density-2d"), work)
        d = result["details"]["density_2d"]
        assert sum(p["z"] * d["cell_area"] for p in result["points"]) == pytest.approx(
            1
        )
        source = pl.read_parquet(r["path"])
        expected, _, _ = np.histogram2d(
            source["x"], source["y"], bins=[d["x_edges"], d["y_edges"]]
        )
        actual = sorted(p["n"] for p in result["points"])
        assert actual == sorted(expected[expected > 0].astype(int).tolist())


def test_heatmap_means_scaling_linkage_and_cell_sources(tmp_path):
    store, r, work = fixture(tmp_path)
    with closing(store):
        result = calculate(
            r,
            replace(
                specification(r, "clustered-heatmap"),
                heatmap_scale="column-zscore",
                cluster_method="ward",
            ),
            work,
        )
        h = result["details"]["heatmap"]
        raw = np.array([[2.5, 5.0], [25.0, 6.0]])
        expected = (raw - raw.mean(0)) / raw.std(0)
        tree = linkage(expected, method="ward", metric="euclidean")
        assert np.asarray(h["linkage"]["rows"]) == pytest.approx(tree)
        assert h["row_order"] == leaves_list(tree).tolist()
        assert h["center"] == [13.75, 5.5]
        assert sorted(p["z"] for p in result["points"]) == [-1.0, -1.0, 1.0, 1.0]
        source = pl.read_parquet(r["path"])
        for p in result["points"]:
            assert set(select(result, [p["point_id"]])["row_ids"]) == set(
                source.filter(pl.col("g") == p["label"])["__vu_row_id"]
            )


@pytest.mark.parametrize("scale", ["shared", "independent"])
def test_facet_scale_actual_limits_and_sample_static_context(tmp_path, scale):
    store, r, work = fixture(tmp_path)
    with closing(store):
        spec = replace(
            specification(r, "facets"), facet_scale=scale, scope="sample", sample_rows=6
        )
        result = render(calculate(r, spec, work), work, highlight=[0])
        bounds = [p["bounds"] for p in result["render"]["panel_axes"]]
        assert (bounds[0] == bounds[1]) == (scale == "shared")
        assert result["used_n"] == 6 and result["population_n"] == 8
        svg = " ".join(
            re.findall(r"<!--(.*?)-->", Path(result["paths"]["svg"]).read_text(), re.S)
        )
        assert "sample=True" in svg and f"facet_scale={scale}" in svg
        assert "highlighted glyphs=1" in svg


def test_pair_diagonal_and_parallel_original_values(tmp_path):
    store, r, work = fixture(tmp_path)
    with closing(store):
        pair = calculate(r, specification(r, "pair"), work)
        assert len(pair["details"]["panels"]) == 4
        assert sum(p["y"] for p in pair["points"] if p["panel"] == 0) == 8
        assert len([p for p in pair["points"] if p["panel"] == 1]) == 8
        parallel = calculate(r, specification(r, "parallel"), work)
        assert parallel["points"][0]["y"] == 0 and parallel["points"][-2]["y"] == 1
        assert parallel["points"][-2]["original_value"] == 40
        with pytest.raises(ProjectError, match="Parallel"):
            calculate(
                r,
                replace(
                    specification(r, "parallel"),
                    columns=(column(r, "x"), column(r, "g")),
                ),
                work,
            )


def test_preflight_no_silent_sample_and_budget(tmp_path):
    store, r, work = fixture(tmp_path)
    with closing(store):
        with pytest.raises(ProjectError, match="önkontrol"):
            calculate(r, replace(specification(r, "pair"), point_limit=4), work)
        with pytest.raises(ProjectError, match="RAM"):
            preflight(
                specification(r, "pair"),
                1000,
                Control(budget=replace(ComputeBudget(), ram_bytes=2000)),
            )
        result = calculate(
            r,
            replace(
                specification(r, "pair"), scope="sample", sample_rows=4, point_limit=4
            ),
            work,
        )
        assert result["used_n"] == 4 and result["scope"] == "sample"
        with pytest.raises(ProjectError, match="2–6"):
            replace(specification(r, "pair"), columns=(column(r, "x"),)).validate(
                r["columns"]
            )


def test_simpson_pooled_and_within_are_separate(tmp_path):
    store, r, work = fixture(tmp_path)
    with closing(store):
        result = calculate(r, specification(r, "conditional"), work)
        panels = result["details"]["panels"]
        assert [p["n"] for p in panels] == [8, 4, 4]
        assert panels[0]["pearson"] < panels[1]["pearson"]
        assert panels[1]["pearson"] == pytest.approx(1)
        assert "Simpson" in result["warnings"][0]


def test_selection_filter_preview_preserves_source_ids_and_rejects_unknown(tmp_path):
    store, r, work = fixture(tmp_path)
    with closing(store):
        chart = calculate(r, specification(r, "density-2d"), work)
        selection = select(chart, [chart["points"][0]["point_id"]])
        chosen = selection["dataset_row_ids"]
        spec = build(
            r,
            "filter",
            [],
            dict(row_ids=chosen, chart_result_id=chart["result_id"]),
            destination="copy",
        )
        result = operation(r, spec, work)
        output = pl.read_parquet(result["path"])
        original = pl.read_parquet(r["path"])
        assert output.equals(original.filter(pl.col("__vu_row_id").is_in(chosen)))
        assert result["spec"]["parameters"]["chart_result_id"] == chart["result_id"]
        bad = build(
            r,
            "filter",
            [],
            dict(
                row_ids=["row:00000000-0000-4000-8000-000000000000"],
                chart_result_id=chart["result_id"],
            ),
        )
        with pytest.raises(ProjectError, match="olmayan RowId"):
            operation(r, bad, work)


@pytest.mark.parametrize("bad", [-1.0, None, float("nan"), float("inf")])
def test_bubble_invalid_size_never_dropped(tmp_path, bad):
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=[1.0, 2.0], y=[3.0, 4.0], size=[1.0, bad]))
    )
    with closing(store), pytest.raises(ProjectError, match="Bubble"):
        calculate(
            r,
            ChartSpec(
                "bubble", x=column(r, "x"), y=column(r, "y"), size=column(r, "size")
            ),
            work,
        )


def test_cpu_hexbin_large_n_source_memberships(tmp_path):
    n = 10001
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            dict(x=np.arange(n, dtype=float) % 101, y=np.arange(n, dtype=float) % 37)
        ),
    )
    with closing(store):
        result = calculate(
            r,
            ChartSpec("hexbin", x=column(r, "x"), y=column(r, "y"), grid_bins=12),
            work,
        )
        assert (
            len(result["points"]) < 300 and sum(p["n"] for p in result["points"]) == n
        )
        ids = pl.read_parquet(r["path"])["__vu_row_id"]
        members = pl.read_parquet(result["paths"]["members"])
        assert len(members) == n and set(members["row_id"]) == set(ids)
        assert result["used_n"] == n and result["scope"] == "full"
