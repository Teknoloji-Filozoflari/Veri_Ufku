"""Presentation contracts: deferred forms, real navigation, bounded table identity."""

import hashlib
import json
import os
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import polars as pl
from PySide6.QtCore import QObject, Qt
from PySide6.QtQml import QQmlEngine, QQmlExpression
from PySide6.QtTest import QTest
from test_dataset import prepare
from test_import_gui import setup, spin, teardown

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import page
from veri_ufku.importers.delimited import Control
from veri_ufku.ui.dataset import DatasetTableModel


def evaluate(obj, expression):
    script = QQmlExpression(QQmlEngine.contextForObject(obj), obj, expression)
    result = script.evaluate()[0]
    assert not script.hasError(), script.error().toString()
    return result


def screenshot(window, name):
    folder = os.environ.get("VERI_UFKU_UI_EVIDENCE")
    if folder:
        path = Path(folder)
        path.mkdir(parents=True, exist_ok=True)
        QTest.qWait(120)  # Let Canvas icons finish painting before grabbing the frame.
        assert window.grabWindow().save(str(path / f"{name}.png"))


def test_null_identity_and_invalid_model_indices(tmp_path):
    store, request, _ = prepare(
        tmp_path, pl.DataFrame(dict(value=[None, "∅", "null", "=SUM(A1:A2)"]))
    )
    with closing(store):
        result = page(request, ViewSpec(), 0, Control())
        assert result["null_cells"] == [[0, 0]]
        model = DatasetTableModel()
        model.replace(result)
        assert model.data(model.index(0, 0)) == model.data(model.index(1, 0)) == "∅"
        assert model.data(model.index(0, 0), model.MissingRole) is True
        assert model.data(model.index(1, 0), model.MissingRole) is False
        assert model.data(model.createIndex(999, 0)) is None
        assert model.headerData(-1, Qt.Horizontal) is None
        assert model.headerData(999, Qt.Vertical) is None
        model.replace()
        assert model.rowCount() == 0 and not model._null_cells


def test_navigation_deferred_panels_state_and_responsive_shell(tmp_path, monkeypatch):
    app, window, _, _, _ = setup(tmp_path, monkeypatch)
    try:
        assert window.findChild(QObject, "chartCreate") is None
        assert window.findChild(QObject, "operationPreview") is None
        window.setWidth(1366)
        window.setHeight(900)
        app.processEvents()
        assert not window.property("compactNavigation")
        toggle = window.findChild(QObject, "navigationToggle")
        toggle.clicked.emit()
        app.processEvents()
        assert window.property("compactNavigation")
        assert window.findChild(QObject, "navigationRail").property("width") == 68
        toggle.clicked.emit()
        window.setProperty("navigationMode", -1)
        for section in range(8):
            QTest.keyClick(window, Qt.Key.Key_1 + section, Qt.ControlModifier)
            spin(app, lambda: window.property("selectedSection") == section)
        window.setProperty("selectedSection", 3)
        app.processEvents()
        bins = window.findChild(QObject, "chartBins")
        assert bins and bins.setProperty("value", 17)
        window.setProperty("selectedSection", 0)
        window.setProperty("selectedSection", 3)
        assert window.findChild(QObject, "chartBins") is bins
        assert bins.property("value") == 17
        assert not evaluate(
            window.findChild(QObject, "chartMouse"), "insideImage(0, 0)"
        )
        for width, scale in ((1366, 1.0), (720, 1.0), (720, 2.0)):
            preferences = (
                app._veri_ufku_resources[0].rootContext().contextProperty("preferences")
            )
            preferences.setTextScale(scale)
            window.setWidth(width)
            app.processEvents()
            assert window.findChild(QObject, "workspace").property("width") >= 320
            assert window.property("compactNavigation") == (width < 1000 * scale)
        preferences.setTextScale(1.0)
        window.setProperty("selectedSection", 0)
        window.findChild(QObject, "commandSearchButton").clicked.emit()
        spin(
            app, lambda: window.findChild(QObject, "commandPalette").property("visible")
        )
        QTest.keyClick(window, Qt.Key_Escape)
        window.findChild(QObject, "displayButton").clicked.emit()
        spin(app, lambda: window.findChild(QObject, "displayTheme").property("visible"))
        screenshot(window, "settings")
    finally:
        teardown(app, window)


def test_hidden_discovery_does_not_probe_optional_backends(tmp_path, monkeypatch):
    app, window, _, _, _ = setup(tmp_path, monkeypatch)
    import veri_ufku.ui.workspace as workspace

    try:
        calls = []
        original = workspace.availability

        def observed(capability):
            calls.append(capability.capability_id)
            return original(capability)

        monkeypatch.setattr(workspace, "availability", observed)
        registry = app._veri_ufku_resources[0]._workspace_resources
        for _ in range(3):
            registry.changed.emit()
            app.processEvents()
        assert calls == []
        window.findChild(QObject, "commandSearchButton").clicked.emit()
        app.processEvents()
        assert calls  # Discovery still checks support when the user opens it.
        assert (
            len(
                [
                    item
                    for item in window.findChildren(QObject)
                    if item.objectName().startswith("module-")
                ]
            )
            < 50
        )
    finally:
        teardown(app, window)


def test_startup_does_not_import_model_serializers(tmp_path):
    env = dict(os.environ)
    for key in ("CONFIG", "STATE", "CACHE"):
        env[f"XDG_{key}_HOME"] = str(tmp_path / key.lower())
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from veri_ufku.app import create_application; import sys; a,w,b=create_application(); a.processEvents(); assert 'skops.io' not in sys.modules; assert 'torch' not in sys.modules; a._veri_ufku_resources[-1]()",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_report_form_edits_preserve_bindings_and_reject_invalid_recipe(
    tmp_path, monkeypatch
):
    from test_report_builder import fixture

    build = tmp_path / "report-fixture"
    build.mkdir()
    store, spec, _ = fixture(build)
    store.close()
    app, window, _, projects, _ = setup(tmp_path, monkeypatch)
    try:
        window.setProperty("selectedSection", 6)
        expanded = window.findChild(QObject, "reportBuilderExpanded")
        expanded.setProperty("checked", True)
        controller = app._veri_ufku_resources[0]._report_builder_resources
        editor = window.findChild(QObject, "reportBuilderRecipe")
        editor.setProperty("text", json.dumps(spec))
        app.processEvents()
        commit = projects.store.commit_id
        window.findChild(QObject, "reportTitleEditor").setProperty(
            "text", "Ölçüm raporu"
        )
        window.findChild(QObject, "reportTitleApply").clicked.emit()
        updated = json.loads(editor.property("text"))
        assert updated == dict(spec, title="Ölçüm raporu")
        choice = window.findChild(QObject, "reportBlockChoice")
        choice.setProperty("currentIndex", 0)
        choice.activated.emit(0)
        window.findChild(QObject, "reportBlockTitle").setProperty("text", "Amaç")
        window.findChild(QObject, "reportBlockText").setProperty(
            "text", "Bu bir kullanıcı notudur."
        )
        window.findChild(QObject, "reportBlockApply").clicked.emit()
        updated = json.loads(editor.property("text"))
        assert updated["blocks"][0]["text"] == "Bu bir kullanıcı notudur."
        assert updated["blocks"][1:] == spec["blocks"][1:]
        assert updated["masked_columns"] == spec["masked_columns"]
        assert projects.store.commit_id == commit and not controller.busy
        assert not editor.property("visible")
        window.findChild(QObject, "reportAdvancedRecipe").setProperty("checked", True)
        assert editor.property("visible")
        original = editor.property("text")
        assert controller.editText(original, 999, "Geçersiz", "") == original
        assert controller.errorText
        assert controller.editText("{invalid", 0, "Başlık", "Metin") == "{invalid"
        assert projects.store.commit_id == commit
        screenshot(window, "report-editor")
    finally:
        teardown(app, window)


def test_real_table_null_clipboard_resize_keyboard_and_source_integrity(
    tmp_path, monkeypatch
):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    data = app._veri_ufku_resources[0]._dataset_resources
    source = tmp_path / "observations.parquet"
    pl.DataFrame(
        dict(
            person=[f"Kişi {i}" for i in range(250)],
            measurement=[None, 1.5] + list(range(248)),
        )
    ).write_parquet(source)
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy and not projects.busy)
        assert not imports.errorText
        window.setProperty("selectedSection", 1)
        window.findChild(QObject, "datasetTabs").setProperty("currentIndex", 0)
        window.setProperty("dataPane", "rows")
        data.refresh()
        spin(app, lambda: not data.busy)
        assert not data.errorText and data.model.rowCount() == 200
        assert data.model.data(data.model.index(0, 1), data.model.MissingRole)
        table = window.findChild(QObject, "datasetTable")
        table.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Space)
        QTest.keyClick(window, Qt.Key_C, Qt.ControlModifier)
        copied = json.loads(app.clipboard().text())
        assert copied["rows"][0]["row_id"] == data.model.result["row_ids"][0]
        assert copied["rows"][0]["displayed_values"] == ["Kişi 0", "∅"]
        assert len(copied["rows"]) == 1
        QTest.keyClick(window, Qt.Key_Down)
        assert data.selectedRowIds == [data.model.result["row_ids"][1]]
        evaluate(table, "setColumnWidth(0, 270); forceLayout()")
        assert evaluate(table, "columnWidth(0)") == 270
        window.setWidth(1366)
        window.setHeight(900)
        app.processEvents()
        QTest.qWait(100)
        screenshot(window, "data-table")
        window.findChild(QObject, "datasetNextPage").clicked.emit()
        spin(app, lambda: not data.busy)
        assert data.model.rowCount() == 50 and table.property("keyboardRow") == 0
        assert evaluate(table, "columnWidth(0)") == 270
        assert (
            not data.copyVisibleSelection()
        )  # A selected prior-page RowId is not row 0 here.
        assert hashlib.sha256(source.read_bytes()).hexdigest() == original
    finally:
        teardown(app, window)
