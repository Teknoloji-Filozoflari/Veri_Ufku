"""Real QML/offline/spawn and preview-before-apply spatial paths."""

import json

import pytest
from phase38_fixtures import fixture
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown

MAPS = ("map-point", "map-choropleth", "map-density", "map-raster")
FORMATS = ("geojson", "geopackage", "shapefile", "geoparquet", "geotiff")
OPS = (
    "geo_coordinates",
    "geo_assign",
    "geo_reproject",
    "geo_repair",
    "geo_buffer",
    "geo_area",
    "geo_distance",
    "geo_clip",
    "geo_join",
    "geo_block",
    "geo_moran",
)


def import_source(app, imports, path):
    imports.choose(str(path))
    spin(app, lambda: not imports.busy)
    assert not imports.errorText, imports.errorText
    imports.importData()
    spin(app, lambda: not imports.busy)
    assert not imports.errorText, imports.errorText


def field(window, name, prop, value):
    obj = window.findChild(QObject, name)
    assert obj is not None, name
    obj.setProperty(prop, value)
    return obj


def index_of(picker, ident):
    model = picker.property("model")
    model = model.toVariant() if hasattr(model, "toVariant") else model
    return next(i for i, c in enumerate(model) if c.get("id") == ident)


@pytest.mark.parametrize("kind", FORMATS)
def test_qml_geo_source_preview_and_reopen(tmp_path, monkeypatch, kind, render=None):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = fixture(tmp_path, kind)
    original = source.read_bytes()
    try:
        window.setProperty("selectedSection", 1)
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        panel = window.findChild(QObject, "geoSourceMetadata")
        assert panel is not None
        assert "crs" in panel.property("text") and "invalid_count" in panel.property(
            "text"
        )
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        if render:
            render(app, window, kind)
        root = projects.store.root
        projects.save()
        spin(app, lambda: not projects.busy)
        projects.open(str(root))
        spin(app, lambda: not projects.busy)
        assert not projects.errorText, projects.errorText
        assert source.read_bytes() == original
    finally:
        teardown(app, window)


@pytest.mark.parametrize("kind", MAPS)
def test_qml_offline_map_help_export_save_open(
    tmp_path, monkeypatch, kind, render=None
):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = fixture(
        tmp_path,
        "geotiff" if kind == "map-raster" else "geoparquet",
        points=kind != "map-choropleth",
    )
    original = source.read_bytes()
    try:
        import_source(app, imports, source)
        resources = app._veri_ufku_resources[0]
        data = resources._dataset_resources
        charts = resources._charts_resources
        columns = {c["name"]: c["id"] for c in data.datasetColumns}
        window.setProperty("selectedSection", 3)
        panel = window.findChild(QObject, "chartPanel")
        kinds = panel.property("kindValues").toVariant()
        field(window, "chartKind", "currentIndex", kinds.index(kind))
        if kind == "map-raster":
            for obj, name in [
                ("chartX", "x"),
                ("chartY", "y"),
                ("geoChartMeasure", "value"),
            ]:
                picker = window.findChild(QObject, obj)
                picker.setProperty("currentIndex", index_of(picker, columns[name]))
        else:
            picker = window.findChild(QObject, "geoChartGeometry")
            picker.setProperty("currentIndex", index_of(picker, columns["geometry"]))
            if kind == "map-choropleth":
                picker = window.findChild(QObject, "geoChartMeasure")
                picker.setProperty("currentIndex", index_of(picker, columns["count"]))
                field(window, "geoChartMode", "currentIndex", 1)
                picker = window.findChild(QObject, "geoChartDenominator")
                picker.setProperty(
                    "currentIndex", index_of(picker, columns["population"])
                )
                field(window, "geoClassification", "currentIndex", 2)
                field(window, "geoThresholds", "text", ".15")
        field(window, "chartAnnotation", "text", "Offline · CRS ve kaynak korunur")
        panel.create()
        spin(app, lambda: not charts.busy)
        assert not charts.errorText, charts.errorText
        assert charts.result and charts.imageUrl
        assert "geospatial" in charts.result["details"]
        assert "CRS" in charts.methodSummary
        button = window.findChild(QObject, "chartCreate")
        button.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_F1)
        app.processEvents()
        QTest.keyClick(window, Qt.Key_Escape)
        app.processEvents()
        if render:
            render(app, window, kind)
        for ext in ("png", "svg", "pdf"):
            charts.export(str(tmp_path / ("map." + ext)), ext)
            spin(app, lambda: not charts.busy)
            assert not charts.errorText, charts.errorText
            assert (tmp_path / ("map." + ext)).is_file()
        charts.save()
        spin(app, lambda: not charts.busy)
        assert not charts.errorText, charts.errorText
        charts.openSaved(charts.savedCharts[0]["id"])
        spin(app, lambda: not charts.busy)
        assert not charts.errorText, charts.errorText
        assert source.read_bytes() == original
    finally:
        teardown(app, window)


@pytest.mark.parametrize("kind", OPS)
def test_qml_geo_operation_preview_apply_undo(tmp_path, monkeypatch, kind, render=None):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = fixture(
        tmp_path,
        "geoparquet",
        points=kind not in ("geo_repair", "geo_moran"),
        invalid=kind == "geo_repair",
    )
    original = source.read_bytes()
    try:
        import_source(app, imports, source)
        resources = app._veri_ufku_resources[0]
        data = resources._dataset_resources
        ops = resources._operations_resources
        columns = {c["name"]: c["id"] for c in data.datasetColumns}
        before = data.dataset()["version_id"]
        window.setProperty("selectedSection", 2)
        field(window, "operationKind", "currentIndex", 5)
        field(window, "geoOperationKind", "currentIndex", OPS.index(kind))
        picker = window.findChild(QObject, "geoOperationGeometry")
        picker.setProperty(
            "currentIndex",
            index_of(
                picker,
                columns["count"] if kind == "geo_coordinates" else columns["geometry"],
            ),
        )
        if kind in ("geo_coordinates", "geo_moran"):
            picker = window.findChild(QObject, "geoOperationAuxiliary")
            picker.setProperty(
                "currentIndex",
                index_of(
                    picker,
                    columns["population"]
                    if kind == "geo_coordinates"
                    else columns["count"],
                ),
            )
        p = {"crs": "EPSG:32635"}
        if kind in (
            "geo_coordinates",
            "geo_area",
            "geo_distance",
            "geo_join",
            "geo_block",
        ):
            p.update(output_id=ops.newColumnId(), output_name="geo_result")
        if kind == "geo_reproject":
            p["target_crs"] = "EPSG:4326"
        if kind == "geo_buffer":
            p["distance"] = 10
        if kind == "geo_distance":
            p["reference_wkt"] = "POINT (500000 4500000)"
        if kind == "geo_clip":
            p["mask_wkt"] = (
                "POLYGON ((499999 4499999,500010 4499999,500010 4500010,499999 4500010,499999 4499999))"
            )
        if kind == "geo_join":
            p["predicate"] = "intersects"
            picker = window.findChild(QObject, "geoJoinGeometry")
            picker.setProperty("currentIndex", index_of(picker, columns["geometry"]))
        if kind == "geo_block":
            p.update(block_size=10.0, folds=2, seed=42)
        if kind == "geo_moran":
            p.update(
                neighbors="rook",
                threshold=10,
                standardization="row",
                permutations=99,
                seed=42,
            )
        field(window, "geoOperationParameters", "text", json.dumps(p))
        button = window.findChild(QObject, "operationPreview")
        button.clicked.emit()
        spin(app, lambda: not ops.busy)
        assert not ops.errorText, ops.errorText
        assert ops.canApply and data.dataset()["version_id"] == before
        assert "geospatial" in ops.preview["diagnostics"]
        assert source.read_bytes() == original
        if render:
            render(app, window, kind)
        ops.apply()
        spin(app, lambda: not ops.busy)
        assert not ops.errorText, ops.errorText
        assert data.dataset()["version_id"] != before
        ops.historyAction("undo")
        spin(app, lambda: not ops.busy)
        assert not ops.errorText, ops.errorText
        assert data.dataset()["version_id"] == before
        assert source.read_bytes() == original
    finally:
        teardown(app, window)
