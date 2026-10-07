"""Real QML buttons, spawn preview, atomic application, undo/redo and cancellation."""

import copy

import polars as pl
from PySide6.QtCore import QObject
from test_dataset_gui import load
from test_import_gui import spin, teardown


def test_qml_apply_undo_redo_reopen_stale_history(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch)
    ops = app._veri_ufku_resources[0]._operations_resources
    original = source.read_bytes()
    try:
        data.computeProfile(False, "dataset", 1)
        spin(app, lambda: not data.busy)
        data.saveProfile()
        window.setProperty("selectedSection", 2)
        window.findChild(QObject, "operationName").setProperty("text", "renamed")
        window.findChild(QObject, "operationPreview").clicked.emit()
        spin(app, lambda: not ops.busy)
        assert not ops.errorText and ops.canApply
        assert ops.before.rowCount() == ops.after.rowCount() == 200
        assert ops.previewResult["impact"]["population_n"] == 450
        assert len(projects.draft["datasets"]) == 1
        window.findChild(QObject, "operationApply").clicked.emit()
        spin(app, lambda: not ops.busy)
        assert not ops.errorText, ops.errorText
        d = data.dataset()
        renamed = pl.read_parquet(projects.store.path(d["snapshot_uri"]))
        assert renamed.columns[0] == "renamed"
        assert not projects._result_statuses()[0]["current"]
        window.findChild(QObject, "operationUndo").clicked.emit()
        spin(app, lambda: not ops.busy)
        assert data.dataset()["version_id"] != d["version_id"]
        assert projects._result_statuses()[0]["current"]
        window.findChild(QObject, "operationRedo").clicked.emit()
        spin(app, lambda: not ops.busy)
        assert data.dataset()["version_id"] == d["version_id"]
        assert pl.read_parquet(
            projects.store.path(data.dataset()["snapshot_uri"])
        ).equals(renamed)
        assert projects.closeProject() and projects.open(str(tmp_path / "project"))
        assert data.dataset()["version_id"] == d["version_id"]
        assert pl.read_parquet(projects.store.path(d["snapshot_uri"])).equals(renamed)
        assert source.read_bytes() == original
        assert ops.resultStatuses[0]["current"] is False
        amount = data.dataset()["import_metadata"]["columns"][1]["id"]
        data.selectColumn(amount)
        data.sort(amount, True)
        spin(app, lambda: not data.busy)
        data.addFilter(amount, "ge", "440")
        spin(app, lambda: not data.busy)
        shown_ids = set(data.model.result["row_ids"])
        window.findChild(QObject, "operationKind").setProperty("currentIndex", 2)
        window.findChild(QObject, "operationPreview").clicked.emit()
        spin(app, lambda: not ops.busy)
        assert ops.previewResult["impact"]["removed_rows"] == 440
        window.findChild(QObject, "operationApply").clicked.emit()
        spin(app, lambda: not ops.busy)
        assert not ops.errorText, ops.errorText
        filtered = pl.read_parquet(projects.store.path(data.dataset()["snapshot_uri"]))
        assert filtered["amount"].to_list() == list(range(440, 450))
        assert set(filtered["__vu_row_id"].to_list()) == shown_ids
        window.findChild(QObject, "operationKind").setProperty("currentIndex", 1)
        window.findChild(QObject, "operationColumn").setProperty("currentIndex", 2)
        window.findChild(QObject, "operationPreview").clicked.emit()
        spin(app, lambda: not ops.busy)
        window.findChild(QObject, "operationApply").clicked.emit()
        spin(app, lambda: not ops.busy)
        assert not ops.errorText, ops.errorText
        assert len(data.dataset()["import_metadata"]["columns"]) == 2
        assert (
            pl.read_parquet(projects.store.path(data.dataset()["snapshot_uri"]))[
                "__vu_row_id"
            ].to_list()
            == filtered["__vu_row_id"].to_list()
        )
        ops.historyAction("undo")
        spin(app, lambda: not ops.busy)
        assert projects.closeProject() and projects.open(str(tmp_path / "project"))
        ops.historyAction("redo")
        spin(app, lambda: not ops.busy)
        assert len(data.dataset()["import_metadata"]["columns"]) == 2
        assert source.read_bytes() == original

    finally:
        teardown(app, window)


def test_real_process_cancel_and_invalid_do_not_mutate(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 10000)
    ops = app._veri_ufku_resources[0]._operations_resources
    before = copy.deepcopy(projects.draft)
    try:
        col = data.dataset()["import_metadata"]["columns"][0]["id"]
        ops.previewOperation("rename", col, "amount")
        assert ops.errorText and projects.draft == before
        ops.previewOperation("rename", col, "renamed")
        ops.cancel()
        spin(app, lambda: not ops.busy)
        assert ops.previewResult == {} and projects.draft == before
        assert not list(ops.cache.glob("operation-*"))
    finally:
        teardown(app, window)
