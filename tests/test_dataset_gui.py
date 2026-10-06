"""Actual installed QML/controller/spawn workflow, persistent metadata and cancellation."""

import copy
from pathlib import Path

from PySide6.QtCore import QObject, Qt
from test_import_gui import setup, spin, teardown


def load(tmp_path, monkeypatch, rows=450):
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "sample.csv"
    source.write_text(
        "id,amount,category\n" + "".join(f"{i:05},{i},A\n" for i in range(rows))
    )
    imports.choose(str(source))
    spin(app, lambda: not imports.busy)
    imports.setType(1, "int64")
    imports.refreshPreview()
    spin(app, lambda: not imports.busy)
    imports.importData()
    spin(app, lambda: not imports.busy)
    assert imports.errorText == ""
    engine = app._veri_ufku_resources[0]
    data = engine._dataset_resources
    return app, window, projects, data, source


def test_qml_page_worker_filter_profile_role_save_reopen(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch)
    original = source.read_bytes()
    try:
        window.setProperty("selectedSection", 1)
        tabs = window.findChild(QObject, "datasetTabs")
        tabs.setProperty("currentIndex", 0)
        window.findChild(QObject, "loadDatasetButton").clicked.emit()
        spin(app, lambda: not data.busy)
        assert (
            data.errorText == ""
            and data.model.rowCount() == 200
            and data.totalRows == 450
        )
        assert window.findChild(QObject, "datasetTable").property("visible")
        assert not data.model.flags(data.model.index(0, 0)) & Qt.ItemIsEditable
        row_id = data.model.data(data.model.index(0, 0), data.model.RowIdRole)
        data.selectRow(0)
        assert row_id in data.selectionText and "Görüntü sırası 1" in data.selectionText
        data.searchColumns("amount")
        assert len(data.columns) == 1
        data.searchColumns("")
        cols = data.dataset()["import_metadata"]["columns"]
        data.hideColumn(cols[2]["id"], True)
        spin(app, lambda: not data.busy)
        assert data.model.columnCount() == 2 and "Gizli sütun: 1" in data.viewSummary
        amount = cols[1]["id"]
        data.selectColumn(amount)
        window.findChild(QObject, "datasetSortDesc").clicked.emit()
        spin(app, lambda: not data.busy)
        assert data.model.data(data.model.index(0, 1)) == "449"
        assert data.model.data(data.model.index(0, 0), data.model.RowIdRole) != row_id
        data.addFilter(amount, "ge", "440")
        spin(app, lambda: not data.busy)
        assert data.totalRows == 10 and "amount ge 440" in data.viewSummary
        data.computeProfile(False, "view", 1)
        spin(app, lambda: not data.busy)
        assert data.errorText == "" and data.profileResult["used_n"] == 10
        assert float(data.profileResult["numeric"]["mean"]) == 444.5
        data.saveProfile()
        old = data.dataset()["version_id"]
        data.applyRole("identifier", "", "", "satış")
        assert data.dataset()["version_id"] != old and projects.dirty
        assert (
            data.columnDetails["role"] == "identifier" and "sıfırlandı" in data.message
        )
        assert not projects._result_statuses()[-1]["current"]
        projects.request("save")
        spin(app, lambda: not projects.busy)
        assert not projects.dirty
        assert projects.closeProject() and projects.open(str(tmp_path / "project"))
        assert data.dataset()["semantic_metadata"][amount]["role"] == "identifier"
        assert data.dataset()["analysis_unit"] == "satış"
        data.selectColumn(amount)
        data.computeProfile(False, "dataset", 1)
        spin(app, lambda: not data.busy)
        assert data.errorText == "" and data.profileResult["numeric"]["mean"] is None
        assert source.read_bytes() == original
        assert not list(Path(data.cache).glob("view-*"))
    finally:
        teardown(app, window)


def test_cancel_and_stale_binding_do_not_publish(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 10000)
    before = copy.deepcopy(projects.draft)
    original = source.read_bytes()
    try:
        data.computeProfile(False, "dataset", 1)
        assert projects.busy
        data.cancel()
        spin(app, lambda: not data.busy)
        assert (
            data.profileResult == {}
            and projects.draft == before
            and source.read_bytes() == original
        )
        data.computeProfile(False, "dataset", 1)
        data.selectColumn(data.dataset()["import_metadata"]["columns"][1]["id"])
        spin(app, lambda: not data.busy)
        assert data.profileResult == {} and "Eski veri" in data.message
        assert projects.draft == before
    finally:
        teardown(app, window)
