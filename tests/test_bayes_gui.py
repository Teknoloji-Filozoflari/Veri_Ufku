"""Actual QML/spawn/help/predictive preview/export/save and reopened posterior."""

import json
import os

import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_bayes import frame
from test_import_gui import setup, spin, teardown
from test_unsupervised_gui import visual_find

from veri_ufku.statistics.bayes_contracts import BAYES_METHODS


@pytest.mark.parametrize("method", BAYES_METHODS)
def test_bayes_gui_offline_templates(tmp_path, monkeypatch, method, capture=None):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "bayes-source.parquet"
    frame(method).write_parquet(source)
    original = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText
        engine = app._veri_ufku_resources[0]
        c = engine._statistics_resources
        window.setProperty("selectedSection", 4)

        def get(name):
            obj = window.findChild(QObject, "bayes" + name) or visual_find(
                window.contentItem(), "bayes" + name
            )
            assert obj is not None, name
            return obj

        def field(name, prop, value):
            assert get(name).setProperty(prop, value)
            app.processEvents()

        field("Expanded", "checked", True)
        field("Method", "currentIndex", BAYES_METHODS.index(method))
        columns = {v["name"]: i + 1 for i, v in enumerate(c.columns)}
        field("Outcome", "currentIndex", columns["y"])
        if method in ("bayes_linear", "bayes_hierarchical"):
            field("Predictor", "currentIndex", columns["x"])
            get("AddPredictor").clicked.emit()
        if method == "bayes_hierarchical":
            field("Group", "currentIndex", columns["group"])
        for name in ("Chains", "Draws", "Warmup"):
            field(name, "value", 2 if name == "Chains" else 100)
        field("Measurement", "checked", True)
        field("Independent", "checked", True)
        get("Preflight").clicked.emit()
        spin(app, lambda: not c.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.preflightCurrent and c.preflight_result["prior_predictive"]
        field("Assumptions", "checked", True)
        get("Run").clicked.emit()
        spin(app, lambda: not c.busy, timeout=120000)
        assert not c.errorText, c.errorText
        assert c.current and c.result["worker_pid"] != os.getpid()
        assert "diagnostic_fail" in get("Status").property("text")
        assert "p-değeri değildir" in get("Result").property("text")
        get("Help").clicked.emit()
        assert window.property("infoOpen")
        assert engine._learning_resources.article[
            "id"
        ] == "bayes-" + method.removeprefix("bayes_").replace("_", "-")
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        get("Measurement").forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_F1)
        spin(app, lambda: window.property("infoOpen"))
        assert engine._learning_resources.article["id"] == "bayes"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        export = tmp_path / "bayes-export"
        field("ExportPath", "text", str(export))
        get("Export").clicked.emit()
        assert not c.errorText, c.errorText
        assert (export / "chains.nc").exists() and (
            export / "diagnostic_png.png"
        ).exists()
        result = json.loads((export / "result.json").read_text())
        assert result["diagnostics"]["status"] == "diagnostic_fail"
        get("Save").clicked.emit()
        projects._source_changed(str(source.parent))
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        saved = next(
            r for r in projects.draft["results"] if r.get("analysis", {}).get("bayes")
        )
        c.result = None
        c.openSaved(saved["id"])
        assert not c.errorText, c.errorText
        assert c.result["diagnostics"] == result["diagnostics"]
        app.processEvents()
        spin(app, lambda: not projects.busy and c.current)
        if capture:
            capture(app, window, c, method, export)
        get("Compare").clicked.emit()
        assert "diagnostic" in c.errorText.lower()
        assert source.read_bytes() == original
    finally:
        teardown(app, window)


def test_bayes_gui_sampler_cancel(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "source.parquet"
    frame("bayes_normal_mean").write_parquet(source)
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        c = app._veri_ufku_resources[0]._statistics_resources
        from test_bayes import recipe

        r = {"columns": projects.draft["datasets"][-1]["import_metadata"]["columns"]}
        spec = recipe(r, "bayes_normal_mean").data()
        c.create(json.dumps(spec), True)
        spin(app, lambda: not c.busy, timeout=60000)
        assert not c.errorText, c.errorText
        c.create(json.dumps(spec), False)
        assert c.busy
        c.cancel()
        spin(app, lambda: not c.busy, timeout=15000)
        assert "İptal" in c.message and c.result is None
        assert not any(
            r.get("analysis", {}).get("bayes") for r in projects.draft["results"]
        )
    finally:
        teardown(app, window)
