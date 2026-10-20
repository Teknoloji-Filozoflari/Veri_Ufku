"""Actual QML methods, editable DAG, worker, offline help and safe publication."""

import json
import os

import polars as pl
import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_causal import fixture, recipe
from test_import_gui import setup, spin, teardown
from test_unsupervised_gui import visual_find

from veri_ufku.statistics.causal_contracts import CAUSAL_METHODS


@pytest.mark.parametrize("method", CAUSAL_METHODS)
def test_causal_qml_template(
    tmp_path, monkeypatch, method, capture=None, positivity_failure=False
):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "causal-source.parquet"
    frame = fixture(method)
    if positivity_failure:
        frame = frame.with_columns(
            (pl.col("covariate") > 0).cast(pl.Int64).alias("treatment")
        )
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
            item = window.findChild(QObject, "causal" + name) or visual_find(
                window.contentItem(), "causal" + name
            )
            assert item is not None, name
            return item

        def field(name, prop, value):
            assert get(name).setProperty(prop, value)
            app.processEvents()

        r = dict(columns=projects.draft["datasets"][-1]["import_metadata"]["columns"])
        s = recipe(r, method)
        engine._workspace_resources.restorePreset.emit(json.dumps(s.data()))
        app.processEvents()
        assert get("Expanded").property("checked")
        # Exercise actual editor mutation, with a justified isolated latent node.
        field("DagLatent", "text", "Unobserved reviewer hypothesis")
        field("DagRole", "currentIndex", 5)
        field("DagReason", "text", "Alternative hypothesis, no proposed edges")
        get("DagAddNode").clicked.emit()
        app.processEvents()
        get("Preflight").clicked.emit()
        spin(app, lambda: not c.busy, timeout=30000)
        assert not c.errorText, c.errorText
        assert c.preflightCurrent
        assert (
            bool(c.preflight_result["causal_analysis"]["effect"]) != positivity_failure
        )
        field("Assumptions", "checked", True)
        get("Run").clicked.emit()
        spin(app, lambda: not c.busy, timeout=30000)
        assert not c.errorText, c.errorText
        assert c.current and c.result["worker_pid"] != os.getpid()
        if positivity_failure:
            assert "Bu veri/varsayımla belirlenemiyor" in get("Result").property("text")
            assert c.result["causal_analysis"]["effect"] is None
        else:
            assert "nedensellik kanıtı değil" in get("Result").property("text")
        get("Help").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert engine._learning_resources.article["id"] == method.replace("_", "-")
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        get("Measurement").forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_F1)
        spin(app, lambda: window.property("infoOpen"))
        assert engine._learning_resources.article["id"] == "causal"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        export = tmp_path / "causal-export"
        field("ExportPath", "text", str(export))
        get("Export").clicked.emit()
        assert not c.errorText, c.errorText
        exported = json.loads((export / "result.json").read_text())
        assert exported["plan"]["alternatives"]
        assert (export / "details.parquet").exists()
        get("Save").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        saved = next(
            v for v in projects.draft["results"] if v.get("analysis", {}).get("causal")
        )
        c.result = None
        c.openSaved(saved["id"])
        assert not c.errorText, c.errorText
        assert c.result["causal_analysis"] == exported["causal_analysis"]
        spin(app, lambda: not projects.busy and c.current)
        if capture:
            capture(app, window, c, method, export)
        assert source.read_bytes() == original
        get("Preflight").clicked.emit()
        assert c.busy
        get("Cancel").clicked.emit()
        spin(app, lambda: not c.busy, timeout=15000)
        assert "İptal" in c.message
    finally:
        teardown(app, window)


def test_causal_positivity_failure_visible_qml_and_saved_report(tmp_path, monkeypatch):
    test_causal_qml_template(
        tmp_path, monkeypatch, "causal_aipw", positivity_failure=True
    )
