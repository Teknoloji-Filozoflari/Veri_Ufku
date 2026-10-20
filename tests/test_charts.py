"""Hand-computed graph tables, identity membership, precision and publication boundaries."""

import copy
from contextlib import closing
from datetime import date
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.charts.contracts import ChartSpec
from veri_ufku.charts.engine import calculate, select, suggest
from veri_ufku.charts.export import export
from veri_ufku.charts.plot import render
from veri_ufku.storage.chart_store import publish
from veri_ufku.storage.project_model import ProjectError, validate_manifest
from veri_ufku.storage.project_store import ProjectStore


def run(r, work, kind, **kwargs):
    return calculate(r, ChartSpec(kind, **kwargs), work)


def test_hand_histogram_box_missing_and_exact_summary(tmp_path):
    frame = pl.DataFrame(
        {
            "x": [1.0, 2.0, 3.0, 4.0, None, float("nan"), float("inf")],
            "label": ["", None, "A", "B", "C", "D", "E"],
        }
    )
    store, r, work = prepare(tmp_path, frame)
    with closing(store):
        x = column(r, "x")
        result = run(r, work, "histogram", x=x, bins=2)
        assert [p["n"] for p in result["points"]] == [2, 2]
        assert result["details"]["bin_edges"] == [1.0, 2.5, 4.0]
        assert result["details"]["excluded_rows"] == 3
        assert Decimal(result["summary"][0]["numeric"]["mean"]) == Decimal("2.5")
        assert Decimal(result["summary"][0]["numeric"]["median"]) == Decimal("2.5")
        original = pl.read_parquet(r["path"])["__vu_row_id"].to_list()
        picked = select(result, [0])
        assert set(picked["row_ids"]) == set(original[:2]) and picked["count"] == 2
        box = run(r, work, "box", x=x)["points"][0]
        assert (box["q1"], box["y"], box["q3"], box["whislo"], box["whishi"]) == (
            1.75,
            2.5,
            3.25,
            1.0,
            4.0,
        )
        missing = run(r, work, "missing", columns=(x, column(r, "label")))
        assert [p["null_count"] for p in missing["points"]] == [1, 1]
        assert (
            missing["points"][0]["nan"] == 1
            and missing["points"][0]["positive_infinity"] == 1
        )
        assert missing["points"][0]["y"] == 1 / 7
        assert missing["points"][1]["y"] == 1 / 7  # Empty string is not missing.


def test_bar_other_and_date_line_duplicate_policy(tmp_path):
    frame = pl.DataFrame(
        {
            "cat": ["A", "A", "B", "C", "D", "D"],
            "x": [1, 2, 3, 4, 5, 6],
            "y": [2, 4, 6, 8, 10, 12],
            "day": [
                date(2024, 1, 2),
                date(2024, 1, 1),
                date(2024, 1, 1),
                date(2024, 1, 3),
                date(2024, 1, 3),
                date(2024, 1, 3),
            ],
        }
    )
    store, r, work = prepare(tmp_path, frame)
    with closing(store):
        bar = run(r, work, "bar", x=column(r, "cat"), top_n=1)
        assert [(p["label"], p["y"], p["n"]) for p in bar["points"]] == [
            ("A", 2.0, 2),
            ("Diğer (birleşik)", 4.0, 4),
        ]
        assert (
            bar["details"]["other_rows"] == 4
            and bar["details"]["other_categories"] == 3
        )
        assert select(bar, [1])["count"] == 4
        p = dict(x=column(r, "day"), y=column(r, "y"), aggregation="sum")
        line = run(r, work, "line", **p)
        assert [p["y"] for p in line["points"]] == [10.0, 2.0, 30.0]
        assert [p["n"] for p in line["points"]] == [2, 1, 3]
        assert line["details"]["duplicate_x_rows"] == 3
        assert [p["label"] for p in line["points"]] == [
            "2024-01-01",
            "2024-01-02",
            "2024-01-03",
        ]
        with pytest.raises(ProjectError, match="Agregasyon|agregasyon|toplulaştır"):
            run(r, work, "line", **dict(p, aggregation="reject"))
        nullbar = run(
            r, work, "bar", x=column(r, "cat"), y=column(r, "y"), aggregation="mean"
        )
        assert [p["y"] for p in nullbar["points"]] == [3.0, 6.0, 8.0, 11.0]


def test_scatter_sampling_grid_membership_and_filters(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": list(range(10)), "y": [i * 2 for i in range(10)]})
    )
    with closing(store):
        x, y = column(r, "x"), column(r, "y")
        sample = run(r, work, "scatter", x=x, y=y, point_limit=3)
        assert [p["x"] for p in sample["points"]] == [0.0, 3.0, 6.0]
        assert sample["details"]["omitted_rows"] == 7
        original = pl.read_parquet(r["path"])["__vu_row_id"].to_list()
        assert select(sample, [], [original[1]])["point_ids"] == []
        assert select(sample, [], [original[3]])["point_ids"] == [1]
        grid = run(r, work, "scatter", x=x, y=y, scatter_mode="grid", grid_bins=2)
        assert [(p["x"], p["y"], p["n"]) for p in grid["points"]] == [
            (2.0, 4.0, 5),
            (7.0, 14.0, 5),
        ]
        selected = select(grid, [1], page_row_ids=original[7:])
        assert selected["count"] == 5 and set(selected["page_row_ids"]) == set(
            original[7:]
        )
        with pytest.raises(ProjectError, match="sınır"):
            run(r, work, "scatter", x=x, y=y, scatter_mode="full", point_limit=3)
        view = ViewSpec(
            filters=({"column_id": x, "operator": "ge", "value": "7"},)
        ).data()
        filtered = run(r, work, "scatter", x=x, y=y, view=view)
        assert (
            filtered["scope"] == "filtered"
            and filtered["used_n"] == filtered["population_n"] == 3
        )
        assert [p["x"] for p in filtered["points"]] == [7.0, 8.0, 9.0]
        sample = run(
            r, work, "scatter", x=x, y=y, scope="sample", sample_rows=2, view=view
        )
        assert (sample["used_n"], sample["population_n"], sample["scope"]) == (
            2,
            3,
            "sample",
        )
        assert sample["summary"][0]["used_n"] == 2
        assert Decimal(sample["summary"][0]["numeric"]["mean"]) == Decimal("7.5")


@pytest.mark.parametrize("method", ["pearson", "spearman"])
def test_pairwise_correlation_n_ties_constant_and_nonfinite(tmp_path, method):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "x": [1.0, 2.0, 3.0, None, float("inf")],
                "y": [6.0, 4.0, 2.0, 8.0, 10.0],
                "constant": [7.0] * 5,
            }
        ),
    )
    with closing(store):
        result = run(
            r,
            work,
            "correlation",
            columns=tuple(column(r, n) for n in ("x", "y", "constant")),
            correlation=method,
        )
        pair = result["points"][1]
        assert pair["coefficient"] == pytest.approx(-1.0) and pair["n"] == 3
        constant = result["points"][2]
        assert constant["coefficient"] is None and "Sabit" in constant["error"]
        assert constant["n"] == 3
        assert result["points"][4]["n"] == 5
        assert len(select(result, [1])["row_ids"]) == 3
    # Average ranks ties are independent hand values: [1.5,1.5,3] vs [1,2.5,2.5] => r=.5.
    other = tmp_path / "tie"
    other.mkdir()
    store, r, work = prepare(
        other, pl.DataFrame({"x": [1.0, 1.0, 2.0], "y": [1.0, 2.0, 2.0]})
    )
    with closing(store):
        result = run(
            r,
            work,
            "correlation",
            columns=(column(r, "x"), column(r, "y")),
            correlation="spearman",
        )
        assert result["points"][1]["coefficient"] == pytest.approx(0.5)


def test_decimal_precision_role_recommendation_and_readonly_admission(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            {"amount": [Decimal("0.1"), Decimal("0.2")], "customer_id": [1, 2]}
        ),
    )
    with closing(store):
        c = column(r, "amount")
        with pytest.raises(ProjectError, match="hassasiyet"):
            run(r, work, "histogram", x=c)
        result = run(r, work, "histogram", x=c, precision="approximate")
        assert result["details"]["precision_loss_values"] == 2
        assert Decimal(result["summary"][0]["numeric"]["mean"]) == Decimal(".15")
        schema = pl.read_parquet_schema(r["path"])
        choices = suggest(r["columns"], schema, {}, "distribution")
        assert [v["column_id"] for v in choices] == [c]
        semantics = {c: dict(role="identifier")}
        assert not suggest(r["columns"], schema, semantics)
        assert store.state["results"] == []


@pytest.mark.parametrize(
    "kind", ["histogram", "box", "bar", "line", "scatter", "correlation", "missing"]
)
def test_real_matplotlib_png_svg_persist_reopen_and_protected_export(tmp_path, kind):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            {"x": [1, 2, 3, 4], "y": [2, 4, 6, 8], "cat": ["A", "A", "B", "B"]}
        ),
    )
    root = store.root
    with closing(store):
        x, y = column(r, "x"), column(r, "y")
        spec = ChartSpec(
            kind,
            x=column(r, "cat") if kind == "bar" else x,
            y=y,
            columns=(x, y),
            bins=2,
            aggregation="sum",
            title="Türkçe ölçüm",
            xlabel="X ekseni",
            ylabel="Y ekseni",
            xunit="gün",
            yunit="kg",
        )
        result = render(calculate(r, spec, work), work)
        png = Path(result["paths"]["png"]).read_bytes()
        assert png.startswith(b"\x89PNG\r\n\x1a\n")
        svg = Path(result["paths"]["svg"]).read_text()
        assert "<svg" in svg and "Türkçe ölçüm" in svg and r["version_id"] in svg
        source = Path(r["path"]).read_bytes()
        path = tmp_path / "plot.png"
        export(result, str(path), "png", root)
        assert path.read_bytes() == png
        with pytest.raises(ProjectError):
            export(result, str(path), "png", root)
        with pytest.raises(ProjectError):
            export(result, str(root / "evil.svg"), "svg", root)
        publish(store, copy.deepcopy(store.state), result)
        assert Path(r["path"]).read_bytes() == source
        saved = copy.deepcopy(store.state["results"][-1]["chart"])
        assert (
            saved["spec"]["title"] == "Türkçe ölçüm" and saved["spec"]["yunit"] == "kg"
        )
        assert len(saved["artifact_uris"]) == 6
        damaged = copy.deepcopy(store.manifest)
        damaged["state"]["results"][-1]["chart"]["artifact_uris"]["png"] = (
            "sources/missing.bin"
        )
        with pytest.raises(ProjectError):
            validate_manifest(damaged)
    with closing(ProjectStore.open(root)) as reopened:
        assert reopened.state["results"][-1]["chart"] == saved
        assert reopened.path(saved["artifact_uris"]["png"]).read_bytes() == png


def test_chart_save_fault_tamper_and_invalid_specs_preserve_active(tmp_path):
    store, r, work = prepare(tmp_path, pl.DataFrame({"x": [1, 2, 3, 4]}))
    with closing(store):
        result = render(run(r, work, "histogram", x=column(r, "x")), work)
        before = copy.deepcopy(store.state)
        commit = store.commit_id

        def fault(point):
            if point == "pointer_written":
                raise OSError("fault")

        with pytest.raises(OSError):
            publish(store, copy.deepcopy(store.state), result, fault)
        assert store.state == before and store.commit_id == commit
        Path(result["paths"]["svg"]).write_text("tampered")
        with pytest.raises(ProjectError, match="değişmiş"):
            publish(store, copy.deepcopy(store.state), result)
        assert store.state == before
        for kwargs in (
            {"bins": 0},
            {"columns": ("missing",)},
            {"bounds": (1, 0, 0, 1)},
            {"null_policy": "null=0"},
        ):
            with pytest.raises(ProjectError):
                run(r, work, "histogram", x=column(r, "x"), **kwargs)


def test_correlation_large_float_offsets_do_not_overflow():
    from veri_ufku.charts.engine import correlation

    for x, y in [
        ([1e308, 0.0, -1e308], [-1e308, 0.0, 1e308]),
        ([1e16, 1e16 + 2, 1e16 + 4], [3.0, 2.0, 1.0]),
    ]:
        value, error = correlation(x, y, "pearson")
        assert not error and value == pytest.approx(-1.0)


def test_null_group_and_reserved_category_labels_do_not_merge(tmp_path):
    frame = pl.DataFrame(
        {
            "x": [1, 2, 3, 4],
            "cat": ["__vu_other__", "__vu_other__", "Diğer (birleşik)", "B"],
            "g": [None, "Eksik grup (null)", "None", None],
        }
    )
    store, r, work = prepare(tmp_path, frame)
    with closing(store):
        box = run(r, work, "box", x=column(r, "x"), group=column(r, "g"))
        assert sorted(p["n"] for p in box["points"]) == [1, 1, 2]
        assert len(set(p["label"] for p in box["points"])) == 3
        bar = run(r, work, "bar", x=column(r, "cat"), top_n=2)
        assert [p["n"] for p in bar["points"]] == [2, 1, 1]
        assert len(set(p["x"] for p in bar["points"])) == 3
        assert len(set(p["label"] for p in bar["points"])) == 3
        assert bar["points"][0]["label"] == "__vu_other__"


def test_exact_integer_aggregation_checks_final_coordinate(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"cat": ["A", "A"], "y": [2**53, 1]})
    )
    with closing(store):
        args = dict(x=column(r, "cat"), y=column(r, "y"), aggregation="sum")
        with pytest.raises(ProjectError, match="hassasiyet"):
            run(r, work, "bar", **args)
        result = run(r, work, "bar", precision="approximate", **args)
        assert result["details"]["precision_loss_values"] == 1


def test_grid_preserves_legend_groups_and_limits_points(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame({"x": [1, 2, 1, 2], "y": [1, 2, 1, 2], "g": ["A", "A", "B", "B"]}),
    )
    with closing(store):
        args = dict(
            x=column(r, "x"),
            y=column(r, "y"),
            group=column(r, "g"),
            scatter_mode="grid",
            grid_bins=2,
        )
        result = run(r, work, "scatter", **args)
        assert len(result["points"]) == 4
        assert [p["group"] for p in result["points"]] == ["A", "A", "B", "B"]
        with pytest.raises(ProjectError, match="nokta sınırı"):
            run(r, work, "scatter", point_limit=3, **args)


@pytest.mark.parametrize("point", ["chart_copy_chunk", "pointer_replaced"])
def test_chart_real_sigkill_keeps_complete_active_commit(tmp_path, point):
    import json
    import signal
    import subprocess
    import sys

    store, r, work = prepare(tmp_path, pl.DataFrame({"x": [1, 2, 3]}))
    result = render(run(r, work, "histogram", x=column(r, "x"), bins=2), work)
    recipe = tmp_path / "recipe.json"
    recipe.write_text(json.dumps(result))
    root, before = store.root, copy.deepcopy(store.state)
    store.close()
    code = """import json,os,signal,sys
from pathlib import Path
from veri_ufku.storage.chart_store import publish
from veri_ufku.storage.project_store import ProjectStore
store=ProjectStore.open(sys.argv[1])
def checkpoint(p):
    if p==sys.argv[3]:os.kill(os.getpid(),signal.SIGKILL)
publish(store,store.state,json.loads(Path(sys.argv[2]).read_text()),checkpoint)
"""
    child = subprocess.run(
        [sys.executable, "-c", code, str(root), str(recipe), point],
        capture_output=True,
        timeout=20,
    )
    assert child.returncode == -signal.SIGKILL, child.stderr
    with closing(ProjectStore.open(root, recover_lock=True)) as reopened:
        if point == "chart_copy_chunk":
            assert reopened.state == before
        else:
            assert len(reopened.state["results"]) == 1
            uris = reopened.state["results"][0]["chart"]["artifact_uris"]
            assert pl.read_parquet(reopened.path(uris["members"])).height == 3
            assert all(reopened.path(uri).is_file() for uri in uris.values())
        assert not list(reopened.path("staging").iterdir())


def test_chart_second_real_process_cannot_publish(tmp_path):
    import json
    import subprocess
    import sys

    store, r, work = prepare(tmp_path, pl.DataFrame({"x": [1, 2]}))
    with closing(store):
        result = render(run(r, work, "histogram", x=column(r, "x")), work)
        recipe = tmp_path / "recipe.json"
        recipe.write_text(json.dumps(result))
        before = copy.deepcopy(store.state)
        code = """import json,sys
from pathlib import Path
from veri_ufku.storage.chart_store import publish
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.project_model import ProjectError
store=ProjectStore.open(sys.argv[1],recover_lock=True)
assert store.read_only
try:publish(store,store.state,json.loads(Path(sys.argv[2]).read_text()))
except ProjectError:print('READONLY_CHART_REJECTED')
else:raise AssertionError('second writer admitted')
store.close()
"""
        child = subprocess.run(
            [sys.executable, "-c", code, str(store.root), str(recipe)],
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert child.returncode == 0 and "READONLY_CHART_REJECTED" in child.stdout, (
            child.stderr
        )
        assert store.state == before
