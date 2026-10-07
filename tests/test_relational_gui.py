"""Actual QML form, spawned computation and publication for every Phase11 method."""

from datetime import date

import polars as pl
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown


def test_all_transform_forms_publish_undo_redo_reopen(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "transforms.parquet"
    pl.DataFrame(
        {
            "key": [1, 1, 2],
            "text": ["a-b", "c-d", "e-f"],
            "value": [2, 4, 8],
            "date": [date(2024, 1, 1), date(2024, 1, 2), date(2024, 3, 1)],
            "header": ["x", "y", "x"],
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
        data = engine._dataset_resources
        ops = engine._operations_resources
        window.setProperty("selectedSection", 2)

        def field(name, prop, value):
            obj = window.findChild(QObject, name)
            assert obj is not None, name
            obj.setProperty(prop, value)

        def click(name):
            window.findChild(QObject, name).clicked.emit()

        def snapshot():
            return pl.read_parquet(projects.store.path(data.dataset()["snapshot_uri"]))

        initial = snapshot()
        cols = {
            c["name"]: c["id"] for c in data.dataset()["import_metadata"]["columns"]
        }
        field("operationKind", "currentIndex", 4)
        for method in range(9):
            field("transformMethod", "currentIndex", method)
            field(
                "transformColumn",
                "currentIndex",
                1 if method in (1, 2) else 3 if method == 3 else 2,
            )
            field("transformOutputName", "text", "new_" + str(method))
            field("transformSecondName", "text", "second_" + str(method))
            field("transformationOptions", "groups", [cols["key"]])
            field(
                "transformationOptions",
                "selected",
                [cols["text"]] if method == 2 else [cols["value"]],
            )
            if method == 0:
                field("formulaExpression", "text", f'col("{cols["value"]}") * 2')
            if method == 4:
                field("transformMetric", "currentIndex", 2)
                click("transformAddMetric")
            if method == 5:
                field("pivotHeader", "currentIndex", 4)
            if method == 7:
                click("appendPrepareMapping")
                field("appendApproveMapping", "checked", True)
            if method == 8:
                field("joinLeftKey", "currentIndex", 0)
                field("joinRightKey", "currentIndex", 0)
                click("joinAddKey")
                click("joinNextStep")
                click("joinNextStep")
            click("operationPreview")
            spin(app, lambda: not ops.busy)
            assert ops.canApply, (method, ops.errorText)
            assert ops.previewResult["impact"]["scope"] == "full"
            click("operationApply")
            spin(app, lambda: not ops.busy)
            assert not ops.errorText, (method, ops.errorText)
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
        assert source.read_bytes() == original
    finally:
        teardown(app, window)


def test_new_formats_real_import_gui_table_choices_and_reopen(tmp_path, monkeypatch):
    import sqlite3
    from contextlib import closing

    from test_phase11_formats import ods_fixture

    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    try:
        sources = []
        ods = tmp_path / "sample.ods"
        ods_fixture(ods)
        sources.append((ods, "ods", 2))
        sql = tmp_path / "sample.sqlite"
        with closing(sqlite3.connect(sql)) as db:
            db.execute("CREATE TABLE first(a INTEGER)")
            db.execute("INSERT INTO first VALUES(1)")
            db.execute("CREATE TABLE second(a INTEGER)")
            db.executemany("INSERT INTO second VALUES(?)", [(2,), (3,)])
            db.commit()
        sources.append((sql, "sqlite", 2))
        frame = pl.DataFrame({"a": [1, 2]})
        ipc = tmp_path / "sample.feather"
        frame.write_ipc(ipc)
        sources.append((ipc, "ipc", 2))
        stream = tmp_path / "sample.arrows"
        frame.write_ipc_stream(stream)
        sources.append((stream, "ipc_stream", 2))
        for path, adapter, count in sources:
            original = path.read_bytes()
            imports.choose(str(path))
            spin(app, lambda: not imports.busy)
            assert imports.formatId == adapter and not imports.errorText, (
                adapter,
                imports.errorText,
            )
            if adapter == "sqlite":
                assert imports.choices["sheets"] == ["first", "second"]
                imports.setOption("sheet", "second")
                imports.refreshPreview()
                spin(app, lambda: not imports.busy)
            imports.importData()
            spin(app, lambda: not imports.busy)
            assert not imports.errorText, (adapter, imports.errorText)
            data = app._veri_ufku_resources[0]._dataset_resources
            data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
            spin(app, lambda: not data.busy)
            assert data.dataset()["import_metadata"]["row_count"] == count
            if adapter == "sqlite":
                assert (
                    data.dataset()["import_metadata"]["settings"]["sheet"] == "second"
                )
            assert path.read_bytes() == original
            assert projects.closeProject() and projects.open(str(tmp_path / "project"))
            assert data.dataset()["import_metadata"]["row_count"] == count
    finally:
        teardown(app, window)
