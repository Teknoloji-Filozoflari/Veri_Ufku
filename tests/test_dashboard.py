"""Independent references for full snapshot filtering, linkage and publication."""

import copy
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.analytics.contracts import metadata_version
from veri_ufku.charts.contracts import ChartSpec
from veri_ufku.charts.dashboard import (
    DashboardFilter,
    DashboardSpec,
    DashboardWidget,
    FigureSpec,
    filter_row_ids,
    freshness,
    kpi_value,
    map_selection,
    open_dashboard,
    save_dashboard,
    validate_axis_policy,
)
from veri_ufku.charts.dashboard_engine import evaluate
from veri_ufku.charts.engine import calculate
from veri_ufku.charts.figure import build, compose, interactive_export
from veri_ufku.charts.plot import render
from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Control
from veri_ufku.storage.chart_store import publish
from veri_ufku.storage.project_model import ProjectError, validate_state
from veri_ufku.storage.project_store import ProjectStore


def request(spec, pairs, charts=None, active=None):
    datasets = {
        r["version_id"]: {
            **s.state["datasets"][-1],
            "request": r,
            "source_current": True,
        }
        for s, r in pairs
    }
    return {
        "spec": spec.data(),
        "datasets": datasets,
        "charts": charts or {},
        "active_versions": active if active is not None else list(datasets),
        "revision": 0,
    }


def test_dashboard_versions_grid_and_explicit_source_mapping():
    widget = DashboardWidget(
        "kpi",
        "v1",
        column_id="amount",
        aggregation="sum",
        denominator="included rows",
        previous_period="month",
        previous_filters=(
            {
                "column_id": "period",
                "operator": "eq",
                "value": "month",
                "scope": "local",
            },
        ),
    )
    spec = DashboardSpec(
        "Sales",
        (widget,),
        (DashboardFilter("region", "eq", "TR"),),
        {"v1:region": {"target_version": "v2", "target_column": "area"}},
    )
    spec.validate({"v1", "v2"})
    assert spec.data()["widgets"][0]["dataset_version"] == "v1"
    assert freshness("v1", "v2") == "stale"
    with pytest.raises(ProjectError):
        spec.validate({"v2"})


def test_filter_and_brush_preserve_row_identity_across_datasets():
    a = {
        "a:1": {"region": "TR", "customer": "c1"},
        "a:2": {"region": "US", "customer": "c2"},
    }
    b = {"b:8": {"client": "c1"}, "b:9": {"client": "c2"}, "b:10": {"client": "c1"}}
    assert filter_row_ids(a, [DashboardFilter("region", "eq", "TR")], {"region"}) == {
        "a:1"
    }
    assert map_selection(a, b, {"a:1"}, "customer", "client") == {"b:8", "b:10"}
    with pytest.raises(ProjectError):
        map_selection(a, b, {"a:1"}, "", "client")


def test_kpi_definition_and_axis_safety_are_explicit():
    value = kpi_value(
        {"r1": {"x": 3}, "r2": {"x": 5}}, "x", "mean", "non-null x", "previous 30 days"
    )
    assert (
        value["value"] == 4
        and value["included_n"] == 2
        and value["previous_period"] == "previous 30 days"
    )
    assert validate_axis_policy(
        {"dual_axis": True, "axis_warning": "Separate scales", "legend": True}
    )
    with pytest.raises(ProjectError):
        validate_axis_policy({"dual_axis": True, "legend": True})
    with pytest.raises(ProjectError):
        validate_axis_policy({"automatic_axis_truncation": True})
    with pytest.raises(ProjectError):
        FigureSpec(("r1", "r2"), rows=1, columns=1).validate()


def test_real_store_dashboard_reopen_preserves_layout_filters_and_stale(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"n": [1, 2, 3], "region": ["TR", "US", "TR"]})
    )
    version = r["version_id"]
    n = column(r, "n")
    region = column(r, "region")
    spec = DashboardSpec(
        "saved question",
        (
            DashboardWidget("kpi", version, column_id=n, grid=(2, 4, 3, 6)),
            DashboardWidget("note", version, text="Source matters", grid=(0, 0, 2, 12)),
        ),
        (DashboardFilter(region, "eq", "TR", dataset_version=version),),
    )
    root = store.root
    ident = save_dashboard(store.state, spec)
    validate_state(store.state)
    store.save()
    store.close()
    with closing(ProjectStore.open(root)) as reopened:
        opened = open_dashboard(reopened.state, ident, {version: version})
        assert opened["spec"] == spec.data()
        assert opened["widgets"][0]["grid"] == [2, 4, 3, 6]
        assert opened["widgets"][0]["freshness"] == "current"
        d = reopened.state["datasets"][-1]
        new = metadata_version(d, n, "measurement", "", [], "row")
        reopened.state["datasets"].append(new)
        reopened.save()
        old = open_dashboard(
            reopened.state, ident, {d["dataset_id"]: new["version_id"]}
        )
        assert old["widgets"][0]["freshness"] == "stale"
        assert (
            reopened.state["results"][-1]["dashboard"]["widgets"][0]["dataset_version"]
            == version
        )


def test_global_local_filter_kpi_previous_and_null_denominator_reference(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "amount": [2.0, 4.0, 8.0, 16.0, None, float("nan")],
                "period": ["now", "now", "previous", "previous", "now", "now"],
                "region": ["TR", "TR", "TR", "US", "TR", "TR"],
            }
        ),
    )
    with closing(store):
        amount, period, region = (column(r, n) for n in ("amount", "period", "region"))
        w = DashboardWidget(
            "kpi",
            r["version_id"],
            column_id=amount,
            aggregation="sum",
            denominator_mode="non-null",
            denominator="finite measurements",
            previous_period="previous records",
            filters=(
                {
                    "column_id": period,
                    "operator": "eq",
                    "value": "now",
                    "scope": "local",
                },
            ),
            previous_filters=(
                {
                    "column_id": period,
                    "operator": "eq",
                    "value": "previous",
                    "scope": "local",
                },
            ),
        )
        spec = DashboardSpec(
            "period comparison",
            (w,),
            (DashboardFilter(region, "eq", "TR", dataset_version=r["version_id"]),),
        )
        result = evaluate(request(spec, [(store, r)]), work)
        k = result["widgets"][0]["kpi"]
        assert (
            k["value"] == "3.0"
            and k["numerator"] == "6.0"
            and k["denominator_value"] == "2"
        )
        assert k["previous"]["value"] == "8.0" and k["difference"] == "-5.0"
        assert k["excluded_n"] == 2
        empty = replace(
            w,
            filters=(
                {
                    "column_id": period,
                    "operator": "eq",
                    "value": "missing",
                    "scope": "local",
                },
            ),
        )
        e = evaluate(request(DashboardSpec("empty", (empty,)), [(store, r)]), work)[
            "widgets"
        ][0]["kpi"]
        assert e["value"] is None and "tanımsız" in e["warning"]


def test_cross_source_mapping_is_explicit_and_preserves_all_duplicate_keys(tmp_path):
    aroot = tmp_path / "a"
    broot = tmp_path / "b"
    aroot.mkdir()
    broot.mkdir()
    a, ra, wa = prepare(
        aroot, pl.DataFrame({"key": ["a", "b", None], "value": [1, 2, 3]})
    )
    b, rb, wb = prepare(
        broot,
        pl.DataFrame({"client": ["b", "a", "a", None], "value": [10, 20, 30, 40]}),
    )
    try:
        av, bv = ra["version_id"], rb["version_id"]
        ak, bk = column(ra, "key"), column(rb, "client")
        aid = pl.read_parquet(ra["path"])["__vu_row_id"].to_list()
        bid = pl.read_parquet(rb["path"])["__vu_row_id"].to_list()
        widgets = (
            DashboardWidget("table", av, columns=(ak,)),
            DashboardWidget("table", bv, columns=(bk,)),
        )
        spec = DashboardSpec(
            "cross-source",
            widgets,
            (DashboardFilter(ak, "eq", "a", dataset_version=av),),
            selection={"dataset_version": av, "row_ids": [aid[0]]},
        )
        result = evaluate(request(spec, [(a, ra), (b, rb)]), wa)
        assert result["widgets"][0]["row_ids"] == [aid[0]]
        assert (
            result["widgets"][1]["n"] == 4 and result["widgets"][1]["linked_count"] == 0
        )
        assert result["widgets"][1]["filter_contract"]["unmapped"] == [ak]
        mapped = replace(
            spec,
            filter_mappings={
                "explicit": {
                    "source_version": av,
                    "source_column": ak,
                    "target_version": bv,
                    "target_column": bk,
                }
            },
            drill_down=True,
        )
        result = evaluate(request(mapped, [(a, ra), (b, rb)]), wa)
        assert set(result["widgets"][1]["row_ids"]) == set(bid[1:3])
        assert result["widgets"][1]["linked_count"] == 2
        assert result["mapping_keys"][av][ak][aid[2]] is None
    finally:
        a.close()
        b.close()


def chart_fixture(tmp_path, kind="scatter", group=False, facet=False):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "x": [1, 2, 3, 4],
                "y": [3, 5, 4, 8],
                "group": ["A", "B", "A", "B"],
                "facet": ["F1", "F1", "F2", "F2"],
            }
        ),
    )
    spec = ChartSpec(
        kind,
        x=column(r, "x"),
        y=column(r, "y"),
        group=column(r, "group") if group else "",
        facet=column(r, "facet") if facet else "",
        scope="full",
        aggregation="mean",
    )
    result = render(calculate(r, spec, work), work)
    store.state = publish(store, copy.deepcopy(store.state), result)
    record = store.state["results"][-1]
    result["id"] = record["id"]
    return store, r, work, result, record


@pytest.mark.parametrize("fmt", ["svg", "png", "pdf"])
def test_actual_vector_composer_font_legend_context_export(tmp_path, fmt):
    store, r, work, result, record = chart_fixture(tmp_path, group=True)
    with closing(store):
        spec = FigureSpec(
            (record["id"], record["id"]),
            rows=1,
            columns=2,
            width=14,
            height=9,
            font="DejaVu Serif",
            palette="colorblind",
            caption="Publication caption",
            unit="kg",
            source="Immutable fixture",
        )
        target = tmp_path / ("figure." + fmt)
        figure, context = build(spec, [result, result])
        figure.canvas.draw()
        caption = next(t for t in figure.texts if "Publication caption" in t.get_text())
        caption_box = caption.get_window_extent(figure.canvas.get_renderer())
        for subfigure in figure.subfigs:
            footer = next(t for t in subfigure.texts if r["version_id"] in t.get_text())
            assert not caption_box.overlaps(
                footer.get_window_extent(figure.canvas.get_renderer())
            )
        exported = compose(spec, [result, result], target, fmt, store.root, work)
        assert exported["vector_content"] and not exported["interactive"]
        assert set(exported["legend"]) == {"A", "B"}
        assert exported["font"] == "DejaVu Serif"
        if fmt == "svg":
            svg = target.read_text()
            assert (
                "<image" not in svg
                and "Publication caption" in svg
                and "Immutable fixture" in svg
                and r["version_id"] in svg
            )
        if fmt == "pdf":
            assert target.read_bytes().startswith(b"%PDF")
        if fmt == "png":
            assert target.read_bytes().startswith(b"\x89PNG")
        before = target.read_bytes()
        with pytest.raises(ProjectError):
            compose(spec, [result, result], target, fmt, store.root, work)
        assert target.read_bytes() == before


def test_dashboard_chart_brush_membership_and_offline_html(tmp_path):
    store, r, work, result, record = chart_fixture(tmp_path, group=True)
    with closing(store):
        version = r["version_id"]
        ids = pl.read_parquet(r["path"])["__vu_row_id"].to_list()
        spec = DashboardSpec(
            "Linked <safe> question",
            (
                DashboardWidget("chart", version, chart_result_id=record["id"]),
                DashboardWidget("table", version, columns=(column(r, "x"),)),
            ),
            selection={"dataset_version": version, "row_ids": [ids[0]]},
        )
        job = work / "dashboard"
        job.mkdir()
        value = evaluate(
            request(spec, [(store, r)], {record["id"]: record["chart"]}), job
        )
        c = value["widgets"][0]
        assert c["linked_count"] == 1 and c["chart"]["render"]["highlight"]
        members = {rid for rows in c["memberships"].values() for rid in rows}
        assert members == set(ids)
        assert value["widgets"][1]["rows"][0]["selected"]
        out = interactive_export(value, tmp_path / "dashboard.html", store.root, job)
        document = (tmp_path / "dashboard.html").read_text()
        assert out["adapter"] == "local-svg/v1" and not out["network"]
        assert "Linked &lt;safe&gt; question" in document and "connect-src" in document
        assert (
            'src="http' not in document
            and "fetch(" not in document
            and "<script src" not in document
        )
        assert "data:image/svg+xml;base64" in document and ids[0] in document
        with pytest.raises(ProjectError):
            interactive_export(value, tmp_path / "dashboard.html", store.root, job)


def test_snapshot_tampering_invalid_row_and_row_budget_are_rejected(tmp_path):
    store, r, work = prepare(tmp_path, pl.DataFrame({"x": [1, 2, 3]}))
    with closing(store):
        spec = DashboardSpec(
            "safe",
            (DashboardWidget("table", r["version_id"]),),
            selection={"dataset_version": r["version_id"], "row_ids": ["unrelated"]},
        )
        with pytest.raises(ProjectError, match="RowId"):
            evaluate(request(spec, [(store, r)]), work)
        req = request(replace(spec, selection={}), [(store, r)])
        req["datasets"][r["version_id"]]["request"]["row_count"] = 10001
        with pytest.raises(ProjectError, match="10000"):
            evaluate(req, work)
        req = request(replace(spec, selection={}), [(store, r)])
        req["datasets"][r["version_id"]]["request"]["fingerprint"]["sha256"] = "0" * 64
        with pytest.raises(ProjectError, match="snapshot"):
            evaluate(req, work)
        with pytest.raises(ProjectError):
            compose(
                FigureSpec(("x",), width=40, height=40),
                [],
                tmp_path / "f.svg",
                "svg",
                control=Control(budget=ComputeBudget(ram_bytes=1024)),
            )


@pytest.mark.parametrize(
    "kind",
    __import__(
        "veri_ufku.charts.contracts", fromlist=["COMPOSITION_KINDS"]
    ).COMPOSITION_KINDS,
)
def test_composer_preserves_composition_geometry_and_explicit_dual_axis(tmp_path, kind):
    from phase37_fixtures import frame, options

    store, r, work = prepare(tmp_path, frame(kind))
    with closing(store):
        data = calculate(r, ChartSpec.from_dict(options(kind, r["columns"])), work)
        data["id"] = "figure-test"
        destination = tmp_path / "composition.svg"
        result = compose(
            FigureSpec(("figure-test",), caption="Panel context"),
            [data],
            destination,
            "svg",
        )
        assert result["vector_content"] and destination.stat().st_size > 1000
        if kind == "pareto":
            assert any("Çift eksen" in n for n in result["notices"])
            assert {"Sol eksen · değer", "Sağ eksen · birikimli yüzde"} <= set(
                result["legend"]
            )


@pytest.mark.parametrize(
    "kind",
    __import__(
        "veri_ufku.charts.contracts", fromlist=["MULTIVARIATE_KINDS"]
    ).MULTIVARIATE_KINDS,
)
def test_composer_preserves_multivariate_and_facet_context(tmp_path, kind):
    from test_multivariate import fixture, specification

    store, r, work = fixture(tmp_path)
    with closing(store):
        data = calculate(r, specification(r, kind), work)
        data["id"] = "multi-test"
        result = compose(
            FigureSpec(("multi-test",), font="DejaVu Serif", caption="Facet context"),
            [data],
            tmp_path / "multivariate.svg",
            "svg",
        )
        assert result["font"] == "DejaVu Serif" and "Facet context" in result["context"]


def test_local_adapter_real_javascript_row_mapping_and_keyboard():
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QJSEngine

    app = QGuiApplication.instance() or QGuiApplication([])
    engine = QJSEngine(app)
    harness = r"""
    let callbacks={};
    function row(id){return {dataset:{row:id},classList:{toggle:(k,v)=>{callbacks[id+'selected']=v}},addEventListener:(k,f)=>{callbacks[id+k]=f}}}
    let a=row('a1'),b=row('b1'),c=row('b2'),d=row('b3');
    function panel(id,rows){let selection={textContent:''};return {dataset:{widget:id},querySelector:s=>s==='.selection'?selection:null,querySelectorAll:s=>rows}}
    let pa=panel('a',[a]),pb=panel('b',[b,c,d]);
    const document={getElementById:id=>id==='clear'?{addEventListener:(k,f)=>{callbacks.clear=f}}:{textContent:JSON.stringify({widgets:[{id:'a',dataset_version:'va',row_ids:['a1']},{id:'b',dataset_version:'vb',row_ids:['b1','b2','b3']}],mappings:{key:{source_version:'va',source_column:'k',target_version:'vb',target_column:'v'}},keys:{va:{k:{a1:'String:x'}},vb:{v:{b1:'String:x',b2:'String:x',b3:null}}}})},querySelectorAll:s=>[pa,pb]};
    """
    from veri_ufku.charts import figure

    adapter = Path(figure.__file__).with_name("local_svg_adapter.js").read_text()
    loaded = engine.evaluate(
        harness.replace("let ", "var ").replace("const ", "var ") + "\n" + adapter
    )
    assert not loaded.isError(), loaded.toString()
    result = engine.evaluate(
        "callbacks.a1keydown({key:'Enter',preventDefault:()=>{}});callbacks.b1selected && callbacks.b2selected && !callbacks.b3selected"
    )
    assert not result.isError() and result.toBool()
    assert engine.evaluate(
        "callbacks.clear();!callbacks.a1selected && !callbacks.b1selected && !callbacks.b2selected"
    ).toBool()


@pytest.mark.parametrize("invalid_key", [float("nan"), float("inf")])
def test_offline_mapping_cannot_match_nonfinite_keys_before_any_selection(
    tmp_path, invalid_key
):
    aroot = tmp_path / "a"
    broot = tmp_path / "b"
    aroot.mkdir()
    broot.mkdir()
    a, ra, wa = prepare(aroot, pl.DataFrame({"key": [1.0, invalid_key]}))
    b, rb, wb = prepare(broot, pl.DataFrame({"client": [1.0, invalid_key]}))
    try:
        av, bv = ra["version_id"], rb["version_id"]
        mapping = {
            "key": {
                "source_version": av,
                "source_column": column(ra, "key"),
                "target_version": bv,
                "target_column": column(rb, "client"),
            }
        }
        spec = DashboardSpec(
            "finite keys",
            (DashboardWidget("note", av), DashboardWidget("note", bv)),
            filter_mappings=mapping,
        )
        with pytest.raises(ProjectError, match="sonlu"):
            evaluate(request(spec, [(a, ra), (b, rb)]), wa)
    finally:
        a.close()
        b.close()
