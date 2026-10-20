"""Actual QML selection, worker, cost rejection, cancel, plot/export/save/reopen."""

import hashlib
import json

import polars as pl
import pytest
from phase34_fixtures import fixture
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown

from veri_ufku.importers.arrays import ARRAY_FORMATS


@pytest.mark.parametrize("adapter", ARRAY_FORMATS)
def test_qml_array_slice_cost_cancel_import_plot_reopen(
    tmp_path, monkeypatch, adapter, render=None
):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source, values = fixture(tmp_path, adapter)
    original = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (list(source.rglob("*")) if source.is_dir() else [source])
        if p.is_file()
    }
    try:
        window.setProperty("selectedSection", 1)
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        if adapter == "hdf5_array":
            imports.setFormat(adapter)
            imports.refreshPreview()
            spin(app, lambda: not imports.busy)
        assert imports.formatId == adapter and not imports.ready
        window.findChild(QObject, "importAdvancedButton").clicked.emit()
        app.processEvents()
        variable = "/temperature" if adapter == "hdf5_array" else "temperature"
        choice = window.findChild(QObject, "arrayVariable")
        assert choice.property("visible")
        choice.setProperty(
            "currentIndex", imports.choices["array_variables"].index(variable) + 1
        )
        choice.activated.emit(choice.property("currentIndex"))
        slice_field = window.findChild(QObject, "arraySlice")
        slice_field.setProperty(
            "text", '{"time":1,"latitude":[1,3,1],"longitude":[0,4,2]}'
        )
        slice_field.editingFinished.emit()
        decode = window.findChild(QObject, "arrayDecode")
        decode.setProperty("checked", True)
        decode.toggled.emit()
        unit = window.findChild(QObject, "arrayUnit")
        unit.setProperty("text", "kelvin")
        unit.editingFinished.emit()
        imports.setOption("max_rows", 1)
        imports.refreshPreview()
        spin(app, lambda: not imports.busy)
        assert not imports.ready and not imports.errorText, imports.errorText
        assert "4 satır" in imports.previewWarnings
        assert not imports.result["rows"]
        if render:
            render(app, window, adapter + "-cost", "importStatus")
        imports.setOption("max_rows", 100)
        imports.refreshPreview()
        spin(app, lambda: not imports.busy)
        assert imports.ready, imports.errorText
        before = projects.store.commit_id
        learning = app._veri_ufku_resources[0]._learning_resources
        for name, topic in (
            ("arrayVariable", "array-dimensions"),
            ("arraySlice", "array-chunks"),
            ("arrayUnit", "array-units"),
        ):
            current = json.dumps(imports.result, sort_keys=True)
            control = window.findChild(QObject, name)
            control.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_F1)
            spin(app, lambda: window.property("infoOpen"))
            assert learning.article["id"] == topic
            QTest.keyClick(window, Qt.Key.Key_Escape)
            spin(app, lambda: not window.property("infoOpen"))
            assert control.hasActiveFocus()
            assert json.dumps(imports.result, sort_keys=True) == current
        imports.importData()
        imports.cancel()
        spin(app, lambda: not imports.busy)
        assert projects.store.commit_id == before and not projects.draft["datasets"]
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        if adapter == "hdf5_array":
            imports.setFormat(adapter)
        imports.setOption("array_variable", variable)
        imports.setOption(
            "array_slice", '{"time":1,"latitude":[1,3,1],"longitude":[0,4,2]}'
        )
        imports.setOption("array_decode", True)
        imports.setOption("array_unit", "kelvin")
        imports.refreshPreview()
        spin(app, lambda: not imports.busy)
        assert imports.ready, imports.errorText
        window.findChild(QObject, "importCsvButton").clicked.emit()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        dataset = projects.draft["datasets"][-1]
        metadata = dataset["import_metadata"]["settings"]["format_metadata"]
        frame = pl.read_parquet(projects.store.path(dataset["snapshot_uri"]))
        assert frame["value"].to_list() == pytest.approx(
            (values[1, 1:3, ::2].reshape(-1) * 0.5 + 10 + 273.15).tolist()
        )
        data = app._veri_ufku_resources[0]._dataset_resources
        charts = app._veri_ufku_resources[0]._charts_resources
        window.setProperty("selectedSection", 3)
        columns = {c["name"]: c["id"] for c in data.datasetColumns}
        panel = window.findChild(QObject, "chartPanel")
        kind = window.findChild(QObject, "chartKind")
        kind.setProperty("currentIndex", 7)
        kind.activated.emit(7)
        kind.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_F1)
        spin(app, lambda: window.property("infoOpen"))
        assert learning.article["id"] == "array-raster"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        panel.setProperty(
            "selected", [columns["longitude"], columns["latitude"], columns["value"]]
        )
        window.findChild(QObject, "chartCreate").clicked.emit()
        spin(app, lambda: not charts.busy)
        assert not charts.errorText, charts.errorText
        assert charts.result["spec"]["kind"] == "array-heatmap"
        assert (
            charts.result["details"]["array_source"]
            == metadata["parts"][0]["multidimensional"]
        )
        assert not charts.provider.image.isNull()
        assert len(charts.result["points"]) == 4
        if render:
            render(app, window, adapter + "-heatmap", "chartCanvas")
        charts.export(str(tmp_path / "heatmap.png"), "png")
        spin(app, lambda: not charts.busy)
        assert (tmp_path / "heatmap.png").stat().st_size > 1000
        charts.save()
        spin(app, lambda: not charts.busy)
        assert not charts.errorText, charts.errorText
        kind.setProperty("currentIndex", 8)
        window.findChild(QObject, "chartX").setProperty(
            "currentIndex", list(columns).index("longitude")
        )
        window.findChild(QObject, "chartY").setProperty(
            "currentIndex", list(columns).index("value")
        )
        window.findChild(QObject, "chartAggregation").setProperty("currentIndex", 2)
        window.findChild(QObject, "chartCreate").clicked.emit()
        spin(app, lambda: not charts.busy)
        assert not charts.errorText, charts.errorText
        assert len(charts.result["points"]) == 2
        assert [p["y"] for p in charts.result["points"]] == pytest.approx(
            [292.15, 293.15]
        )
        assert charts.result["details"]["aggregation"] == "mean"
        if render:
            render(app, window, adapter + "-profile", "chartCanvas")
        charts.save()
        spin(app, lambda: not charts.busy)
        assert not charts.errorText, charts.errorText
        assert projects.closeProject() and projects.open(str(tmp_path / "project"))
        assert (
            projects.draft["datasets"][-1]["import_metadata"]["settings"][
                "format_metadata"
            ]
            == metadata
        )
        records = [r for r in projects.draft["results"] if "chart" in r]
        assert len(records) == 2
        assert all(
            r["chart"]["provenance"]["array_source"] == metadata for r in records
        )
        charts.openSaved(records[-1]["id"])
        assert charts.result["spec"]["kind"] == "array-profile"
        assert not charts.provider.image.isNull()
        for path, digest in original.items():
            from pathlib import Path

            assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    finally:
        teardown(app, window)
