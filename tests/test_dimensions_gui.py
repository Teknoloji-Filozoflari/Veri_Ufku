"""Actual desktop purposes, nested worker, honest embedding view and safe representation reuse."""

import importlib.util
import json
import os

import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_dimensions import fixture, recipe
from test_import_gui import setup, spin, teardown
from test_unsupervised_gui import visual_find

from veri_ufku.statistics.dimension_contracts import (
    DIMENSION_METHODS,
    SELECTORS,
    VISUAL,
)

CASES = [(m, "default") for m in DIMENSION_METHODS if m != "dimension_umap"] + [
    ("dimension_pca", "model_input")
]


@pytest.mark.parametrize("method,mode", CASES)
def test_dimension_desktop_purpose_transform_cv(
    tmp_path, monkeypatch, method, mode, capture=None
):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "dimension-source.parquet"
    fixture(method).write_parquet(source)
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
            item = window.findChild(QObject, "dimension" + name) or visual_find(
                window.contentItem(), "dimension" + name
            )
            assert item is not None, name
            return item

        def field(name, prop, value):
            assert get(name).setProperty(prop, value)
            app.processEvents()

        r = dict(columns=projects.draft["datasets"][-1]["import_metadata"]["columns"])
        s = recipe(r, method, purpose="model_input" if mode == "model_input" else None)
        engine._workspace_resources.restorePreset.emit(json.dumps(s.data()))
        app.processEvents()
        assert get("Expanded").property("checked")
        if method == "dimension_nmf":
            field("Scaling", "currentIndex", 1)
            get("Preflight").clicked.emit()
            assert "centering" in c.errorText and not c.busy
            engine._workspace_resources.restorePreset.emit(json.dumps(s.data()))
            app.processEvents()
        get("Preflight").clicked.emit()
        spin(app, lambda: not c.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.preflightCurrent
        field("Assumptions", "checked", True)
        get("Run").clicked.emit()
        spin(app, lambda: not c.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.current and c.result["worker_pid"] != os.getpid()
        a = c.result["dimension_analysis"]
        assert not a["display"]["class_labels"]
        assert "gerçek sınıf" in get("Result").property("text")
        assert get("Plot").property("source").toString()
        if method in SELECTORS or mode == "model_input":
            assert a["cv"] and not a["cv"]["final_test"]["evaluated"]
        if method in VISUAL:
            assert a["explained_variance"] is None
            assert not get("Transform").property("enabled") and not get(
                "Inverse"
            ).property("enabled")
        get("Help").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert engine._learning_resources.article["id"] == method.replace("_", "-")
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        get("Measurement").forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_F1)
        spin(app, lambda: window.property("infoOpen"))
        assert engine._learning_resources.article["id"] == "dimensions"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        export = tmp_path / "dimension-export"
        field("ExportPath", "text", str(export))
        get("Export").clicked.emit()
        assert not c.errorText, c.errorText
        saved_result = json.loads((export / "result.json").read_text())
        assert (export / "details.parquet").exists() and (
            export / "diagnostic_png.png"
        ).exists()
        get("Save").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        saved = next(
            v
            for v in projects.draft["results"]
            if v.get("analysis", {}).get("dimensions")
        )
        c.result = None
        c.openSaved(saved["id"])
        assert not c.errorText, c.errorText
        assert c.result["dimension_analysis"] == saved_result["dimension_analysis"]
        spin(app, lambda: not projects.busy and c.current)
        field("Matrix", "text", json.dumps([[0.5] * 4]))
        if method not in VISUAL:
            get("Transform").clicked.emit()
            assert not c.errorText, c.errorText
            assert c.dimensionTransform["values"]
            if method not in SELECTORS:
                field("Matrix", "text", json.dumps(c.dimensionTransform["values"]))
                get("Inverse").clicked.emit()
                assert not c.errorText and len(c.dimensionTransform["values"][0]) == 4
            else:
                assert not get("Inverse").property("enabled")
        if capture:
            capture(app, window, c, method, mode, export)
        get("Preflight").clicked.emit()
        assert c.busy
        get("Cancel").clicked.emit()
        spin(app, lambda: not c.busy, timeout=15000)
        assert "İptal" in c.message
        c.invalidate()
        app.processEvents()
        assert not c.current
        assert "ESKİ VERİ/TARİF" in get("Result").property("text") and not get(
            "Save"
        ).property("enabled")
        c.transformDimension("[[0,0,0,0]]", False)
        assert c.errorText and not c.dimensionTransform
        assert source.read_bytes() == original
    finally:
        teardown(app, window)


def test_optional_umap_registry_unavailable_ui_honest(tmp_path, monkeypatch):
    if importlib.util.find_spec("umap"):
        pytest.skip("UMAP installed; unavailable environment test not applicable")
    app, window, _, _, _ = setup(tmp_path, monkeypatch)
    try:
        window.setProperty("selectedSection", 4)
        app.processEvents()
        panel = window.findChild(QObject, "dimensionExpanded")
        assert panel is not None
        panel.setProperty("checked", True)
        choice = window.findChild(QObject, "dimensionMethod")
        choice.setProperty("currentIndex", DIMENSION_METHODS.index("dimension_umap"))
        app.processEvents()
        assert "KAPALI" in window.findChild(QObject, "dimensionAvailability").property(
            "text"
        )
        assert not window.findChild(QObject, "dimensionPreflight").property("enabled")
    finally:
        teardown(app, window)
