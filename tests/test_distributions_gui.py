"""Every Phase35 graphic through real QML/spawn/help/export/save/reopen."""

import copy
import json
import os
from pathlib import Path

import polars as pl
import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown

from veri_ufku.charts.contracts import DISTRIBUTION_KINDS

CASES = DISTRIBUTION_KINDS + ("histogram", "box")


@pytest.mark.parametrize("kind", CASES)
def test_qml_distribution_help_worker_exports_and_reopen(
    tmp_path, monkeypatch, kind, render=None
):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "distribution.parquet"
    pl.DataFrame(
        {
            "x": [1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 4.0],
            "y": [2.0, 4.0, 4.0, 6.0, 6.0, 8.0, 8.0, 10.0],
            "g": ["A"] * 4 + ["B"] * 4,
            "f": ["F"] * 4 + ["G"] * 4,
            "w": [1, 2, 1, 2, 1, 2, 1, 2],
        }
    ).write_parquet(source)
    original = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        resources = app._veri_ufku_resources[0]
        charts = resources._charts_resources
        data = resources._dataset_resources
        learning = resources._learning_resources
        window.setProperty("selectedSection", 3)

        def field(name, prop, value):
            obj = window.findChild(QObject, name)
            assert obj is not None, name
            obj.setProperty(prop, value)
            return obj

        panel = window.findChild(QObject, "chartPanel")
        kinds = list(panel.property("kindValues").toVariant())
        field("chartKind", "currentIndex", kinds.index(kind))
        field("chartX", "currentIndex", 0)
        field("chartY", "currentIndex", 1)
        field("chartBins", "value", 2)
        field("chartAnnotation", "text", "Kaynak korunur · gerçek GUI")
        cols = {c["name"]: c["id"] for c in data.datasetColumns}
        field("chartPanel", "selected", [cols["x"], cols["y"]])
        if kind in ("histogram", "box"):
            field("chartGroup", "currentIndex", 3)
            field("chartFacet", "currentIndex", 4)
            field("chartWeight", "currentIndex", 5)
            field("chartWeightType", "currentIndex", 1)
            field("chartNormalization", "currentIndex", 2)
            field("chartCategoryOrder", "text", "B|A")
        if kind == "ci-band":
            field("chartUncertainty", "currentIndex", 2)
        if kind == "ecdf":
            field("chartXScale", "currentIndex", 2)
            field("chartDPI", "value", 180)
            field("chartFont", "currentIndex", 1)
        before = projects.store.commit_id
        control = window.findChild(QObject, "chartKind")
        control.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_F1)
        spin(app, lambda: window.property("infoOpen"))
        assert learning.article["id"] == "chart-" + kind
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        assert control.hasActiveFocus()
        assert projects.store.commit_id == before
        if kind == "error-bar":
            field("chartYScale", "currentIndex", 1)
            window.findChild(QObject, "chartCreate").clicked.emit()
            spin(app, lambda: not charts.busy)
            assert "Log" in charts.errorText
            field("chartYScale", "currentIndex", 2)
        window.findChild(QObject, "chartCreate").clicked.emit()
        spin(app, lambda: not charts.busy)
        assert not charts.errorText, (kind, charts.errorText)
        assert charts.result["worker_pid"] != os.getpid() and charts.current
        assert not charts.provider.image.isNull()
        assert charts.result["details"]["included_n"] == 8
        assert "Normalizasyon" in window.findChild(
            QObject, "chartMethodDetails"
        ).property("text")
        if render:
            render(app, window, kind, "chartImage", charts.result)
        for fmt in ("png", "svg", "pdf"):
            target = tmp_path / f"{kind}.{fmt}"
            charts.export(str(target), fmt)
            spin(app, lambda: not charts.busy)
            assert not charts.errorText, charts.errorText
            assert target.stat().st_size > 1000
        charts.save()
        spin(app, lambda: not charts.busy)
        assert not charts.errorText, charts.errorText
        saved = copy.deepcopy(charts.result["details"])
        record = projects.draft["results"][-1]["id"]
        points = copy.deepcopy(charts.result["points"])
        charts.openSaved(record)
        assert charts.result["details"] == saved and charts.result["points"] == points
        assert Path(charts.result["paths"]["pdf"]).read_bytes().startswith(b"%PDF")
        assert source.read_bytes() == original
        assert charts.result["provenance"]["dataset_versions"] == [
            data.dataset()["version_id"]
        ]
        if kind == "ecdf":
            field("chartSettings", "checked", True)
            field("chartTitle", "text", "Sadece başlık değişti")
            field("chartX", "currentIndex", 0)
            field("chartXScale", "currentIndex", 2)
            window.findChild(QObject, "chartCreate").clicked.emit()
            spin(app, lambda: not charts.busy)
            assert not charts.errorText and charts.result["points"] == points
            charts.create(json.dumps(charts.result["spec"]))
            charts.cancel()
            spin(app, lambda: not charts.busy)
            assert source.read_bytes() == original
    finally:
        teardown(app, window)
