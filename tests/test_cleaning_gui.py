"""Actual cleaning form/spawn/publication, errors, cancellation and reopening."""

import copy
import json

import polars as pl
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown

from veri_ufku.operations.cleaning_contracts import defaults


def test_cleaning_qml_methods_copy_leakage_and_atomic_errors(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "clean.parquet"
    pl.DataFrame(
        {
            "v": [1, None, 3, 5],
            "text": [" A ", "A", "B", "B"],
            "time": [1, 2, 3, 4],
            "group": ["x", "x", "y", "y"],
            "missing": pl.Series([None] * 4, dtype=pl.Int64),
            "date": ["2026-01-01", "bad", "2026-01-03", None],
        }
    ).write_parquet(source)
    original = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText
        engine = app._veri_ufku_resources[0]
        data, ops = engine._dataset_resources, engine._operations_resources
        window.setProperty("selectedSection", 2)
        window.findChild(QObject, "operationKind").setProperty("currentIndex", 3)

        def field(name, prop, value):
            obj = window.findChild(QObject, name)
            assert obj is not None, name
            obj.setProperty(prop, value)

        def snapshot():
            return pl.read_parquet(projects.store.path(data.dataset()["snapshot_uri"]))

        initial = snapshot()
        cols = {
            c["name"]: c["id"] for c in data.dataset()["import_metadata"]["columns"]
        }
        for index in range(9):
            field("cleaningMethod", "currentIndex", index)
            field(
                "cleaningColumn",
                "currentIndex",
                1 if index in (3, 4, 5) else 4 if index == 2 else 0,
            )
            field("cleaningValue", "text", "2")
            field("cleaningOrder", "currentIndex", 2)
            if index == 5:
                field("cleaningFrom", "text", "B")
                field("cleaningTo", "text", "C")
                window.findChild(QObject, "cleaningAddMapping").clicked.emit()
            if index == 7:
                field("cleaningOptions", "groups", [cols["group"]])
            window.findChild(QObject, "operationPreview").clicked.emit()
            spin(app, lambda: not ops.busy)
            assert not ops.errorText and ops.canApply, (index, ops.errorText)
            assert ops.previewResult["impact"]["scope"] == "full"
            window.findChild(QObject, "operationApply").clicked.emit()
            spin(app, lambda: not ops.busy)
            assert not ops.errorText, ops.errorText
            applied = snapshot()
            ops.historyAction("undo")
            spin(app, lambda: not ops.busy)
            assert snapshot().equals(initial)
            ops.historyAction("redo")
            spin(app, lambda: not ops.busy)
            assert snapshot().equals(applied)
            assert projects.closeProject() and projects.open(str(tmp_path / "project"))
            assert snapshot().equals(applied)
            ops.historyAction("undo")
            spin(app, lambda: not ops.busy)
        # Exercise selectable fill submethods, full-key dedup, backward fill and explicit IQR filtering through the form.
        for method in (1, 2, 3):
            field("cleaningMethod", "currentIndex", 0)
            field("cleaningColumn", "currentIndex", 0)
            field("cleaningFillMethod", "currentIndex", method)
            assert (
                window.findChild(QObject, "cleaningOptions").property("helpContext")
                == [
                    "clean.fill.constant",
                    "clean.fill.mean",
                    "clean.fill.median",
                    "clean.fill.mode",
                ][method]
            )
            field("cleaningModeTie", "currentIndex", 1)
            field("cleaningValue", "text", "3")
            window.findChild(QObject, "operationPreview").clicked.emit()
            spin(app, lambda: not ops.busy)
            assert ops.canApply, ops.errorText
            ops.apply()
            spin(app, lambda: not ops.busy)
            assert snapshot()["v"].to_list() == [1, 3, 3, 5]
            ops.historyAction("undo")
            spin(app, lambda: not ops.busy)
            assert snapshot().equals(initial)
        for method in (3, 7, 8):
            field("cleaningOrder", "currentIndex", 2)
            field("cleaningAllColumns", "checked", False)
            field("cleaningMethod", "currentIndex", method)
            field("cleaningColumn", "currentIndex", 0)
            if method == 3:
                field("cleaningAllColumns", "checked", True)
            if method == 7:
                field("cleaningDirection", "currentIndex", 1)
                field("cleaningOptions", "groups", [cols["group"]])
            if method == 8:
                field("cleaningOutlierAction", "currentIndex", 1)
            window.findChild(QObject, "operationPreview").clicked.emit()
            spin(app, lambda: not ops.busy)
            assert ops.canApply, ops.errorText
            ops.apply()
            spin(app, lambda: not ops.busy)
            assert not ops.errorText
            ops.historyAction("undo")
            spin(app, lambda: not ops.busy)
            assert snapshot().equals(initial)
        field("cleaningMethod", "currentIndex", 6)
        field("cleaningColumn", "currentIndex", 5)
        field("cleaningTarget", "currentIndex", 6)
        window.findChild(QObject, "operationPreview").clicked.emit()
        spin(app, lambda: not ops.busy)
        assert ops.errorText and not ops.canApply and snapshot().equals(initial)
        field("cleaningOnError", "currentIndex", 1)
        window.findChild(QObject, "operationPreview").clicked.emit()
        spin(app, lambda: not ops.busy)
        assert ops.previewResult["impact"]["parse_errors"] == 1
        assert ops.previewResult["impact"]["new_nulls"] == 1
        assert (
            ops.previewResult["diagnostics"]["examples"][0]["row_id"]
            == initial["__vu_row_id"][1]
        )
        ops.discardPreview()
        before = copy.deepcopy(projects.draft)
        p = defaults("fill")
        p.update(method="mean")
        ops.previewCleaning("fill", json.dumps([cols["v"]]), json.dumps(p), "copy")
        ops.cancel()
        spin(app, lambda: not ops.busy)
        assert projects.draft == before and not ops.previewResult
        # Median is learned on the whole dataset, separately from future ML fold fitting.
        p["method"] = "median"
        ops.previewCleaning("fill", json.dumps([cols["v"]]), json.dumps(p), "copy")
        spin(app, lambda: not ops.busy)
        assert ops.canApply, ops.errorText
        ops.apply()
        spin(app, lambda: not ops.busy)
        assert not ops.errorText and ops.leakageHistory
        version = data.dataset()["version_id"]
        assert projects.closeProject() and projects.open(str(tmp_path / "project"))
        assert data.dataset()["version_id"] == version and ops.leakageHistory
        assert source.read_bytes() == original
    finally:
        teardown(app, window)
