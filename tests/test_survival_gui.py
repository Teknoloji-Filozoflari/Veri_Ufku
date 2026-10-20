"""Real QML/backend gates, curves/risk table, offline help, model reuse and publication."""

import json
import os

import polars as pl
import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown
from test_survival import fixture, recipe
from test_unsupervised_gui import visual_find

from veri_ufku.statistics.survival_contracts import SURVIVAL_METHODS

CASES = [(m, "normal") for m in SURVIVAL_METHODS] + [
    ("survival_km", "noevents"),
    ("survival_km", "entry"),
    ("survival_cox", "few_events"),
]


@pytest.mark.parametrize("method,mode", CASES)
def test_survival_desktop_path(tmp_path, monkeypatch, method, mode, capture=None):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "survival-source.parquet"
    frame = fixture(method)
    if mode == "noevents":
        frame = frame.with_columns(pl.lit(0).alias("event"))
    if mode == "few_events":
        frame = frame.with_columns(pl.Series("event", [1] * 5 + [0] * 195))
    frame.write_parquet(source)
    original = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText
        engine = app._veri_ufku_resources[0]
        c = engine._statistics_resources
        engine._workspace_resources.activate("statistics." + method.replace("_", "-"))
        app.processEvents()

        def get(name):
            item = window.findChild(QObject, "survival" + name) or visual_find(
                window.contentItem(), "survival" + name
            )
            assert item is not None, name
            return item

        def field(name, prop, value):
            assert get(name).setProperty(prop, value)
            app.processEvents()

        r = dict(columns=projects.draft["datasets"][-1]["import_metadata"]["columns"])
        s = recipe(r, method, entry=mode == "entry")
        engine._workspace_resources.restorePreset.emit(json.dumps(s.data()))
        app.processEvents()
        assert get("Expanded").property("checked")
        # Actual unsupported selector must not admit a fake interval fit.
        field("Censoring", "currentIndex", 3)
        get("Preflight").clicked.emit()
        assert "desteklemiyor" in c.errorText and not c.busy
        engine._workspace_resources.restorePreset.emit(json.dumps(s.data()))
        app.processEvents()
        get("Preflight").clicked.emit()
        spin(app, lambda: not c.busy, timeout=30000)
        assert not c.errorText, c.errorText
        assert c.preflightCurrent
        field("Assumptions", "checked", True)
        get("Run").clicked.emit()
        spin(app, lambda: not c.busy, timeout=30000)
        assert not c.errorText, c.errorText
        assert c.current and c.result["worker_pid"] != os.getpid()
        assert "censored" in get("Result").property("text")
        assert get("Curve").property("source").toString()
        assert get("RiskTable")
        if mode == "few_events":
            assert "TANI BAŞARISIZ" in get("Result").property("text")
        if mode == "noevents":
            assert c.result["survival_analysis"]["events"] == 0
        get("Help").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert engine._learning_resources.article["id"] == method.replace("_", "-")
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        get("Measurement").forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_F1)
        spin(app, lambda: window.property("infoOpen"))
        assert engine._learning_resources.article["id"] == "survival"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        export = tmp_path / "survival-export"
        field("ExportPath", "text", str(export))
        get("Export").clicked.emit()
        assert not c.errorText, c.errorText
        exported = json.loads((export / "result.json").read_text())
        assert (export / "diagnostic_png.png").exists()
        assert (export / "details.parquet").exists()
        get("Save").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        saved = next(
            v
            for v in projects.draft["results"]
            if v.get("analysis", {}).get("survival")
        )
        c.result = None
        c.openSaved(saved["id"])
        assert not c.errorText, c.errorText
        assert c.result["survival_analysis"] == exported["survival_analysis"]
        spin(app, lambda: not projects.busy and c.current)
        if c.result["survival_analysis"]["model"]:
            get("Predict").clicked.emit()
            assert not c.errorText, c.errorText
            assert c.survivalPrediction["curve"][0]["survival"] == 1
            field("ReuseTimes", "text", "[10000000]")
            get("Predict").clicked.emit()
            assert c.errorText and not c.survivalPrediction
        if capture:
            capture(app, window, c, method, mode, export)
        assert source.read_bytes() == original
        get("Preflight").clicked.emit()
        assert c.busy
        get("Cancel").clicked.emit()
        spin(app, lambda: not c.busy, timeout=15000)
        assert "İptal" in c.message
        c.invalidate()
        app.processEvents()
        assert not c.current and not get("Save").property("enabled")
        assert "ESKİ VERİ/TARİF" in get("Result").property("text")
        c.predictSurvival("[0]", "[1]", "")
        assert c.errorText and not c.survivalPrediction
    finally:
        teardown(app, window)
