"""Independent references for plots, weighted semantics and immutable memberships."""

import copy
import math
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from scipy import stats
from test_dataset import column, prepare

from veri_ufku.charts.contracts import DISTRIBUTION_KINDS, ChartSpec
from veri_ufku.charts.engine import calculate, select
from veri_ufku.charts.export import export
from veri_ufku.charts.plot import render
from veri_ufku.domain.capabilities import CAPABILITIES
from veri_ufku.storage.chart_store import publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


@pytest.mark.parametrize("kind", DISTRIBUTION_KINDS + ("histogram", "box"))
def test_every_distribution_render_export_membership_and_reopen(tmp_path, kind):
    frame = pl.DataFrame(
        {
            "x": [1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 4.0],
            "y": [2.0, 4.0, 4.0, 6.0, 6.0, 8.0, 8.0, 10.0],
            "group": ["A"] * 4 + ["B"] * 4,
            "facet": ["F"] * 4 + ["G"] * 4,
        }
    )
    store, r, work = prepare(tmp_path, frame)
    root = store.root
    original = Path(r["path"]).read_bytes()
    with closing(store):
        x, y = column(r, "x"), column(r, "y")
        spec = ChartSpec(
            kind,
            aggregation="mean" if kind in ("error-bar", "ci-band") else "count",
            x=x,
            y=y,
            columns=(x, y),
            group=column(r, "group")
            if kind not in ("qq", "pp", "kde", "violin")
            else "",
            facet=column(r, "facet")
            if kind in ("histogram", "box", "strip", "rug")
            else "",
            title="Türkçe yoğunluk",
            annotation="Açık kapsam",
            bins=2,
        )
        result = render(calculate(r, spec, work), work)
        assert result["details"]["included_n"] == 8
        if kind == "violin":
            assert "peak" in result["details"]["violin_width_normalization"]
        assert result["points"] and all(
            p["n"] >= 1 or kind == "histogram" for p in result["points"]
        )
        for fmt in ("png", "svg", "pdf"):
            dest = tmp_path / f"plot.{fmt}"
            export(result, str(dest), fmt, root)
            assert dest.stat().st_size > 1000
            assert dest.read_bytes() == Path(result["paths"][fmt]).read_bytes()
            with pytest.raises(ProjectError):
                export(result, str(dest), fmt, root)
        assert "<svg" in Path(result["paths"]["svg"]).read_text()
        assert Path(result["paths"]["pdf"]).read_bytes().startswith(b"%PDF")
        point = result["points"][0]
        assert select(result, [point["point_id"]])["count"] == point["n"]
        publish(store, copy.deepcopy(store.state), result)
        saved = copy.deepcopy(store.state["results"][-1]["chart"])
        assert saved["details"] == result["details"]
        assert Path(r["path"]).read_bytes() == original
    with closing(ProjectStore.open(root)) as reopened:
        assert reopened.state["results"][-1]["chart"] == saved
        assert (
            reopened.path(saved["artifact_uris"]["pdf"])
            .read_bytes()
            .startswith(b"%PDF")
        )


def test_kde_matches_scipy_weighted_reference_and_frequency_replication(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 4.0, 7.0], "w": [1.0, 2.0, 3.0, 1.0]})
    )
    with closing(store):
        for weight_type in ("none", "analytic", "frequency"):
            spec = ChartSpec(
                "kde",
                x=column(r, "x"),
                weight=column(r, "w") if weight_type != "none" else "",
                weight_type=weight_type,
            )
            result = calculate(r, spec, work)
            values = np.array([1.0, 2.0, 4.0, 7.0])
            weights = np.array([1, 2, 3, 1])
            ref = stats.gaussian_kde(
                np.repeat(values, weights) if weight_type == "frequency" else values,
                weights=weights if weight_type == "analytic" else None,
            )
            assert [p["y"] for p in result["points"]] == pytest.approx(
                ref([p["x"] for p in result["points"]]), rel=1e-10
            )
            assert result["details"]["samples"][0]["bandwidth"] == pytest.approx(
                math.sqrt(ref.covariance[0, 0])
            )


def test_weighted_bins_ecdf_box_hand_reference_and_category_facet(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "x": [1.0, 2.0, 4.0, 7.0],
                "w": [1, 2, 3, 1],
                "g": ["B", "B", "A", "A"],
                "f": ["F"] * 4,
            }
        ),
    )
    with closing(store):
        spec = ChartSpec(
            "histogram",
            x=column(r, "x"),
            weight=column(r, "w"),
            weight_type="frequency",
            bins=2,
        )
        for mode, reference in [
            ("count", [3, 4]),
            ("probability", [3 / 7, 4 / 7]),
            ("density", [1 / 7, 4 / 21]),
            ("percent", [300 / 7, 400 / 7]),
        ]:
            result = calculate(r, replace(spec, normalization=mode), work)
            assert [p["y"] for p in result["points"]] == pytest.approx(reference)
        box = calculate(r, replace(spec, kind="box"), work)["points"][0]
        assert [box["q1"], box["y"], box["q3"]] == pytest.approx(
            np.quantile([1, 2, 2, 4, 4, 4, 7], [0.25, 0.5, 0.75])
        )
        ecdf = calculate(r, replace(spec, kind="ecdf"), work)
        assert [p["y"] for p in ecdf["points"]] == pytest.approx(
            [1 / 7, 3 / 7, 6 / 7, 1]
        )
        assert [p["n"] for p in ecdf["points"]] == [1, 1, 1, 1]
        group = calculate(
            r,
            replace(
                spec,
                group=column(r, "g"),
                facet=column(r, "f"),
                category_order=("A", "B"),
            ),
            work,
        )
        assert group["details"]["group_order"] == ["A", "B"]
        assert [s["n"] for s in group["details"]["samples"]] == [2, 2]
        assert (
            next(
                d
                for d in CAPABILITIES["chart.histogram"].support_details
                if d.name == "weights"
            ).status
            == "conditional"
        )


@pytest.mark.parametrize("meaning", ["sd", "se", "ci"])
def test_interval_hand_reference_and_metadata(tmp_path, meaning):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [1, 1, 2, 2], "y": [2.0, 4.0, 6.0, 10.0]})
    )
    with closing(store):
        spec = ChartSpec(
            "error-bar",
            x=column(r, "x"),
            y=column(r, "y"),
            uncertainty=meaning,
            aggregation="mean",
        )
        with pytest.raises(ProjectError, match="agregasyon"):
            calculate(r, replace(spec, aggregation="sum"), work)
        result = calculate(r, spec, work)
        p = result["points"][0]
        radius = (
            math.sqrt(2)
            if meaning == "sd"
            else 1
            if meaning == "se"
            else 12.706204736432095
        )
        assert [p["y"], p["lower"], p["upper"]] == pytest.approx(
            [3, 3 - radius, 3 + radius]
        )
        meta = result["details"]["samples"][0]
        assert meta["df"] == 1 and meta["se"] == pytest.approx(1) and meta["n"] == 2
        assert "survey" in meta["assumption"]
        band = calculate(r, replace(spec, kind="ci-band"), work)
        assert band["points"][0]["y"] == p["y"]


def test_qq_pp_ecdf_missing_patterns_reference(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            {"x": [1.0, 2.0, 2.0, 4.0, None], "y": [None, 2.0, 3.0, 4.0, None]}
        ),
    )
    with closing(store):
        spec = ChartSpec("qq", x=column(r, "x"))
        qq = calculate(r, spec, work)
        assert [p["x"] for p in qq["points"]] == pytest.approx(
            stats.norm.ppf([0.125, 0.375, 0.625, 0.875])
        )
        assert [p["y"] for p in qq["points"]] == [1, 2, 2, 4]
        pp = calculate(r, replace(spec, kind="pp"), work)
        assert [p["x"] for p in pp["points"]] == pytest.approx(
            stats.norm.cdf(
                (np.array([1, 2, 2, 4]) - 2.25) / np.std([1, 2, 2, 4], ddof=1)
            )
        )
        assert [p["y"] for p in pp["points"]] == [0.125, 0.375, 0.625, 0.875]
        ecdf = calculate(r, replace(spec, kind="ecdf"), work)
        assert [p["y"] for p in ecdf["points"]] == [0.25, 0.75, 1]
        assert [p["n"] for p in ecdf["points"]] == [1, 2, 1]
        patterns = calculate(
            r,
            ChartSpec("missing-pattern", columns=(column(r, "x"), column(r, "y"))),
            work,
        )
        assert {p["label"]: p["n"] for p in patterns["points"]} == {
            "00": 3,
            "01": 1,
            "11": 1,
        }


@pytest.mark.parametrize("kind", ["kde", "violin", "qq", "pp"])
def test_small_constant_and_empty_are_controlled(tmp_path, kind):
    store, r, work = prepare(tmp_path, pl.DataFrame({"x": [1.0, 1.0, None]}))
    with closing(store):
        with pytest.raises(ProjectError, match="sabit|Sabit|değişken"):
            calculate(r, ChartSpec(kind, x=column(r, "x")), work)
        with pytest.raises(ProjectError, match="örneği|Sonlu"):
            calculate(
                r,
                ChartSpec(
                    kind,
                    x=column(r, "x"),
                    view={
                        "filters": [
                            {
                                "column_id": column(r, "x"),
                                "operator": "is_null",
                                "value": "",
                            }
                        ]
                    },
                ),
                work,
            )
        for good in ("histogram", "box", "ecdf", "strip", "rug", "swarm"):
            assert calculate(r, ChartSpec(good, x=column(r, "x")), work)["points"]


@pytest.mark.parametrize(
    "weights,type_",
    [
        ([-1, 1, 1], "analytic"),
        ([None, 1, 1], "analytic"),
        ([float("nan"), 1, 1], "analytic"),
        ([0.5, 1, 1], "frequency"),
        ([0, 0, 0], "analytic"),
    ],
)
def test_bad_weights_are_rejected(tmp_path, weights, type_):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "w": weights}, strict=False)
    )
    with closing(store), pytest.raises(ProjectError):
        calculate(
            r,
            ChartSpec(
                "histogram", x=column(r, "x"), weight=column(r, "w"), weight_type=type_
            ),
            work,
        )


def test_display_changes_do_not_change_statistics_and_log_never_drops(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [-1.0, 0.0, 2.0, 3.0], "w": [1, 1, 1, 1]})
    )
    with closing(store):
        base = ChartSpec("ecdf", x=column(r, "x"))
        a = calculate(r, base, work)
        b = calculate(
            r,
            replace(
                base,
                title="Başlık",
                xlabel="Değer",
                palette="grayscale",
                font="DejaVu Serif",
                annotation="Not",
                dpi=180,
                xscale="symlog",
            ),
            work,
        )
        assert a["points"] == b["points"]
        assert a["summary"][0]["numeric"] == b["summary"][0]["numeric"]
        result = render(b, work)
        assert result["render"]["width"] == 1500 and result["render"]["height"] == 975
        with pytest.raises(ProjectError, match="Log"):
            render(calculate(r, replace(base, xscale="log"), work), work)
        with pytest.raises(ProjectError, match="desteklemiyor"):
            calculate(
                r,
                ChartSpec(
                    "qq",
                    x=column(r, "x"),
                    weight=column(r, "w"),
                    weight_type="analytic",
                ),
                work,
            )
        with pytest.raises(ProjectError):
            calculate(
                r,
                ChartSpec(
                    "histogram",
                    x=column(r, "x"),
                    weight=column(r, "w"),
                    weight_type="survey",
                ),
                work,
            )


def test_swarm_and_kde_limits(tmp_path):
    store, r, work = prepare(tmp_path, pl.DataFrame({"x": list(range(501))}))
    with closing(store):
        with pytest.raises(ProjectError, match="500"):
            calculate(r, ChartSpec("swarm", x=column(r, "x")), work)
        assert (
            len(
                calculate(
                    r,
                    ChartSpec(
                        "swarm", x=column(r, "x"), scope="sample", sample_rows=20
                    ),
                    work,
                )["points"]
            )
            == 20
        )


def test_scale_geometry_matches_matplotlib_and_is_invertible():
    from matplotlib.scale import SymmetricalLogTransform

    from veri_ufku.charts.contracts import axis_coordinate

    for threshold in (0.1, 1, 5):
        values = np.array([-100.0, -5.0, -1.0, 0.0, 0.1, 1.0, 5.0, 100.0])
        reference = SymmetricalLogTransform(10, threshold, 1).transform(values)
        coordinates = [axis_coordinate(v, "symlog", threshold) for v in values]
        assert coordinates == pytest.approx(reference)
        assert [
            axis_coordinate(v, "symlog", threshold, True) for v in coordinates
        ] == pytest.approx(values)
    assert axis_coordinate(100, "log") == 2
    assert axis_coordinate(2, "log", inverse=True) == 100


def test_render_preserves_category_ticks_and_exports_interval_meaning(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "x": [1.0, 2.0, 3.0, 4.0],
                "y": [2.0, 4.0, 6.0, 8.0],
                "g": ["Düşük", "Düşük", "Yüksek", "Yüksek"],
            }
        ),
    )
    with closing(store):
        result = render(
            calculate(
                r,
                ChartSpec(
                    "strip",
                    x=column(r, "x"),
                    group=column(r, "g"),
                    category_order=("Yüksek", "Düşük"),
                ),
                work,
            ),
            work,
        )
        svg = Path(result["paths"]["svg"]).read_text()
        assert "Yüksek" in svg and "Düşük" in svg
        interval = render(
            calculate(
                r,
                ChartSpec(
                    "error-bar",
                    x=column(r, "g"),
                    y=column(r, "y"),
                    uncertainty="se",
                    aggregation="mean",
                ),
                work,
            ),
            work,
        )
        svg = Path(interval["paths"]["svg"]).read_text()
        assert "interval=se" in svg and "aggregation=mean" in svg
        assert "Düşük" in svg and "Yüksek" in svg
