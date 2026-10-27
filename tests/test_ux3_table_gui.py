"""UX3: table-centered data pane, page scope, column selection persistence."""

from PySide6.QtCore import QObject, Qt
from test_dataset_gui import load
from test_import_gui import setup, spin, teardown
from test_learning_gui import visual_item


def test_ux3_stage_opens_table_and_keeps_column_selection(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 250)
    before = source.read_bytes()
    version_before = data.dataset()["version_id"]

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        stage = item("moduleVeri")
        stage.clicked.emit()
        spin(app, lambda: window.property("dataPane") == "rows")
        assert window.property("selectedSection") == 1
        assert window.property("dataPane") == "rows"
        assert item("toolDock").property("visible")
        assert item("dataWorkspacePanel").property("visible")
        assert item("datasetPageScope").property("visible")
        assert not item("datasetToolsToggle").property("checked")
        spin(app, lambda: not data.busy and data.model.rowCount() > 0)
        assert data.model.rowCount() <= 200
        assert data.dataset()["version_id"] == version_before
        header = data.model.headerData(0, Qt.Orientation.Horizontal)
        assert " · " in str(header)
        item("moduleIncele").clicked.emit()
        spin(app, lambda: window.property("inceleOpen"))
        assert window.property("selectedSection") == 1
        assert window.property("inceleOpen")
        assert item("datasetTable").property("visible")
        assert item("toolDock").property("visible")
        assert item("toolDock").property("width") >= 280
        panel = item("inspectWorkspacePanel")
        assert panel is not None and panel.property("visible")
        assert item("inspectScanStrip") is not None
        scope = item("inspectScopeLabel").property("text")
        assert "tarama" in scope.lower() or "kapsam" in scope.lower()
        assert data.dataset()["version_id"] == version_before
        item("moduleVeri").clicked.emit()
        spin(app, lambda: window.property("dataPane") == "rows")

        first = data.columns[0]["id"]
        data.selectColumn(first)
        selected = data.selectedColumn
        window.setProperty("selectedSection", 3)
        app.processEvents()
        window.setProperty("selectedSection", 1)
        window.setProperty("dataPane", "rows")
        app.processEvents()
        assert data.selectedColumn == selected

        data.addFilter(selected, "not_null", "")
        assert data.dataset()["version_id"] == version_before
        assert source.read_bytes() == before
    finally:
        teardown(app, window)


def test_ux3_data_heading_stays_available(tmp_path, monkeypatch):
    app, window, *_ = setup(tmp_path, monkeypatch)
    try:
        heading = visual_item(window.contentItem(), "dataHeading_rows")
        assert heading is not None
        assert heading.property("text") == "Veri tablosu"
    finally:
        teardown(app, window)
