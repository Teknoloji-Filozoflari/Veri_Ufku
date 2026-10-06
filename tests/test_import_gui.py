"""Real QML/model workflow, isolated process cancellation and Qt drop events."""

import hashlib
import time

import polars as pl
from PySide6.QtCore import QMimeData, QPointF, Qt, QTimer, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from veri_ufku.app import create_application
from veri_ufku.storage.project_store import ProjectStore


def spin(app, predicate, timeout=20000):
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError("Import GUI condition timed out")


def setup(tmp_path, monkeypatch):
    for key in ("CONFIG", "STATE", "CACHE"):
        monkeypatch.setenv("XDG_" + key + "_HOME", str(tmp_path / key.lower()))
    app, window, bridge = create_application()
    engine = app._veri_ufku_resources[0]
    projects, imports = engine._projects_resources, engine._imports_resources
    assert projects.create(str(tmp_path / "project"))
    return app, window, bridge, projects, imports


def teardown(app, window):
    app._veri_ufku_resources[-1]()
    window.deleteLater()
    app.processEvents()


def test_qml_preview_setting_types_immutable_source_import_and_reopen(
    tmp_path, monkeypatch
):
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "sample.csv"
    source.write_text("id;ad;tutar\n001;Çağrı;1,25\n002;Işıl;2,50\n", encoding="utf8")
    try:
        window.setProperty("selectedSection", 1)
        imports.choose(QUrl.fromLocalFile(str(source)).toString())
        spin(app, lambda: not imports.busy)
        assert imports.ready, imports.errorText
        assert imports.model.rowCount() == 2
        assert imports.model.data(imports.model.index(0, 0)) == "001"
        assert "Değişmez kopya" in imports.message and "200" in imports.message
        imports.setType(2, "decimal")
        assert not imports.ready
        imports.refreshPreview()
        spin(app, lambda: not imports.busy)
        assert imports.ready, imports.errorText
        source.write_text("id;ad;tutar\n999;Yeni;5,00\n", encoding="utf8")
        button = window.findChild(QQuickItem, "importCsvButton")
        assert button.isEnabled()
        button.clicked.emit()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        assert len(projects.draft["datasets"]) == 1 and not projects.dirty
        dataset = projects.draft["datasets"][0]
        frame = pl.read_parquet(projects.store.path(dataset["snapshot_uri"]))
        assert frame["id"].to_list() == ["001", "002"]
        assert frame["tutar"].to_list() == [1.25, 2.5]
        assert projects._statuses[dataset["source_id"]] == "changed"
        assert dataset["version_id"] in imports.datasetSummary
        state = projects.draft.copy()
        assert projects.closeProject()
        assert projects.open(str(tmp_path / "project"))
        assert projects.draft == state
        assert imports.model.rowCount() <= 200
    finally:
        teardown(app, window)


def test_actual_qt_drop_routes_one_local_tsv_and_rejects_multiple(
    tmp_path, monkeypatch
):
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "sample.tsv"
    source.write_text("id\tad\n001\tŞule\n")
    try:
        window.setProperty("selectedSection", 1)
        spin(app, lambda: window.findChild(QQuickItem, "csvDropArea").isVisible())
        QTest.qWait(80)
        area = window.findChild(QQuickItem, "csvDropArea")
        position = area.mapToScene(QPointF(20, 20))
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(source))])
        enter = QDragEnterEvent(
            position.toPoint(), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
        )
        app.sendEvent(window, enter)
        drop = QDropEvent(position, Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        app.sendEvent(window, drop)
        spin(app, lambda: imports.snapshot is not None and not imports.busy)
        assert imports.ready and imports.model.rowCount() == 1, imports.errorText
        assert imports.settings["delimiter"] == "\t"
        imports.dropFiles([str(source), str(source)])
        assert "Tek bir" in imports.errorText
    finally:
        teardown(app, window)


def test_real_worker_cancel_ui_ticks_source_active_unchanged(tmp_path, monkeypatch):
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "large.csv"
    with source.open("w") as stream:
        stream.write("id,ad\n")
        for _ in range(180000):
            stream.write("001,Çağrı\n")
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        assert imports.ready, imports.errorText
        active = projects.store.path("ACTIVE").read_bytes()
        ticks = []
        timer = QTimer()
        timer.setInterval(10)
        timer.timeout.connect(lambda: ticks.append(time.monotonic()))
        timer.start()
        imports.importData()
        assert not projects.closeProject(True)
        projects.request("saveAs", str(tmp_path / "second"))
        assert not (tmp_path / "second").exists()
        spin(app, lambda: len(ticks) >= 15)
        assert imports.busy
        started = time.monotonic()
        window.findChild(QQuickItem, "cancelImportButton").clicked.emit()
        spin(app, lambda: not imports.busy)
        assert time.monotonic() - started < 3
        timer.stop()
        assert not projects.draft["datasets"]
        assert projects.store.path("ACTIVE").read_bytes() == active
        assert hashlib.sha256(source.read_bytes()).hexdigest() == original
        assert "İptal edildi" in imports.message
    finally:
        teardown(app, window)


def test_readonly_cannot_import_and_invalid_option_invalidates_preview(
    tmp_path, monkeypatch
):
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "data.csv"
    source.write_text("id\n001\n")
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.setOption("timezone", "Unknown/Time")
        assert not imports.ready and imports.errorText
        owner = projects.store
        reader = ProjectStore.open(owner.root)
        projects.store = reader
        imports.choose(str(source))
        assert "yazılabilir" in imports.errorText
        projects.store = owner
        reader.close()
    finally:
        teardown(app, window)


def test_initial_bad_csv_can_switch_to_quarantine_and_repreview(tmp_path, monkeypatch):
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "broken.csv"
    source.write_text("id,v\n001,1\nbad,2,extra\n002,3\n")
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        assert imports.snapshot is not None
        assert "Bozuk kayıt" in imports.errorText
        imports.setOption("bad_rows", "quarantine")
        imports.refreshPreview()
        spin(app, lambda: not imports.busy)
        assert imports.ready, imports.errorText
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        assert projects.draft["datasets"][0]["import_metadata"]["bad_count"] == 1
        assert "1 bozuk kayıt" in imports.message
    finally:
        teardown(app, window)


def test_qml_file_dialog_accepted_local_path_reaches_importer(tmp_path, monkeypatch):
    from PySide6.QtCore import QObject

    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "chosen.csv"
    source.write_text("id,ad\n0001,Çağrı\n")
    try:
        window.setProperty("selectedSection", 1)
        dialog = window.findChild(QObject, "csvFileDialog")
        assert dialog.setProperty("selectedFile", QUrl.fromLocalFile(str(source)))
        dialog.accepted.emit()
        spin(app, lambda: not imports.busy)
        assert imports.ready, imports.errorText
        assert imports.model.data(imports.model.index(0, 0)) == "0001"
    finally:
        teardown(app, window)


def test_phase06_four_formats_real_worker_qml_controls_and_reopen(
    tmp_path, monkeypatch
):
    from decimal import Decimal
    from pathlib import Path

    from PySide6.QtCore import QObject

    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    fixtures = Path(__file__).parent / "fixtures/structured"
    parquet = tmp_path / "native.parquet"
    pl.DataFrame(
        {"id": ["001", "001"], "n": pl.Series([1, None], dtype=pl.Int16)}
    ).write_parquet(parquet)
    try:
        window.setProperty("selectedSection", 1)
        imports.choose(str(fixtures / "nested.json"))
        spin(app, lambda: not imports.busy)
        assert imports.formatId == "json" and not imports.ready
        assert "/payload/records" in imports.choices["record_paths"]
        path = window.findChild(QObject, "jsonRecordPath")
        assert path.isVisible()
        path.setProperty("text", "/payload/records")
        path.editingFinished.emit()
        expand = window.findChild(QObject, "jsonExpandLists")
        expand.setProperty("text", "/items|/tags")
        expand.editingFinished.emit()
        window.findChild(QObject, "jsonFlatten").setProperty("checked", True)
        window.findChild(QObject, "jsonFlatten").clicked.emit()
        imports.refreshPreview()
        spin(app, lambda: not imports.busy)
        assert imports.ready and imports.model.rowCount() == 7, imports.errorText
        assert "kartesyen" in imports.message
        imports.importData(True)
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        assert projects.draft["datasets"][-1]["import_metadata"]["row_count"] == 7
        for filename, adapter, expected in (
            (fixtures / "records.ndjson", "jsonl", 3),
            (fixtures / "workbook.xlsx", "xlsx", 1),
            (parquet, "parquet", 2),
        ):
            imports.choose(str(filename))
            spin(app, lambda: not imports.busy)
            assert imports.formatId == adapter
            if adapter == "jsonl":
                imports.setOption("bad_rows", "quarantine")
            elif adapter == "xlsx":
                sheet = window.findChild(QObject, "excelSheet")
                assert sheet.isVisible()
                sheet.setProperty("currentIndex", 1)
                sheet.activated.emit(1)
                assert imports.settings["sheet"] == "Diğer"
            imports.refreshPreview()
            spin(app, lambda: not imports.busy)
            assert imports.ready, imports.errorText
            imports.importData()
            spin(app, lambda: not imports.busy)
            assert not imports.errorText, imports.errorText
            assert (
                projects.draft["datasets"][-1]["import_metadata"]["row_count"]
                == expected
            )
        before = projects.draft.copy()
        assert projects.closeProject() and projects.open(str(tmp_path / "project"))
        assert projects.draft == before and len(before["datasets"]) == 4
        first = pl.read_parquet(
            projects.store.path(before["datasets"][0]["snapshot_uri"])
        )
        assert first["/money"][0] == Decimal("12345678901234567890.1200")
    finally:
        teardown(app, window)


def test_jsonl_worker_cancel_keeps_previous_project_and_original(tmp_path, monkeypatch):
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "large.ndjson"
    source.write_text('{"id":"001","nested":{"n":1}}\n' * 120000)
    before = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        assert imports.ready, imports.errorText
        active = projects.store.path("ACTIVE").read_bytes()
        imports.importData()
        spin(app, lambda: imports.process is not None and imports.process.is_alive())
        QTest.qWait(100)
        imports.cancel()
        spin(app, lambda: not imports.busy)
        assert not projects.draft["datasets"] and source.read_bytes() == before
        assert projects.store.path("ACTIVE").read_bytes() == active
        assert "İptal edildi" in imports.message
    finally:
        teardown(app, window)
