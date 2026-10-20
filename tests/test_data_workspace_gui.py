from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_dataset_gui import load
from test_import_gui import setup, spin, teardown
from test_learning_gui import visual_item


def test_data_starts_with_headings_and_no_separate_guide(tmp_path, monkeypatch):
    app, window, *_ = setup(tmp_path, monkeypatch)
    try:
        assert window.findChild(QObject, "reopenGuide") is None
        visual_item(window.contentItem(), "roadmapOpen_0").clicked.emit()
        assert (
            window.property("selectedSection") == 1
            and window.property("dataPane") == ""
        )
        assert not window.findChild(QObject, "datasetPanel").property("visible")
        assert not window.findChild(QObject, "csvDropArea").property("visible")
        header = visual_item(window.contentItem(), "dataHeading_profile")
        header.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Space)
        assert window.property("dataPane") == "profile"
        header.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Space)
        assert window.property("dataPane") == ""
        window.setProperty("selectedSection", 7)
        visual_item(window.contentItem(), "learningStage-data").clicked.emit()
        app.processEvents()
        QTest.qWait(250)
        visual_item(window.contentItem(), "learningGroup-inventory").clicked.emit()
        app.processEvents()
        QTest.qWait(250)
        visual_item(
            window.contentItem(), "learningArticle-inspection-inventory"
        ).clicked.emit()
        assert window.property("readingOpen")
        assert (
            app._veri_ufku_resources[0]._learning_resources.article["id"]
            == "inspection-inventory"
        )
    finally:
        teardown(app, window)


def test_real_inventory_values_describe_and_persistent_notes(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 405)
    original = source.read_bytes()
    try:
        window.setProperty("selectedSection", 1)
        visual_item(window.contentItem(), "dataHeading_profile").clicked.emit()
        window.findChild(QObject, "computeInventory").clicked.emit()
        spin(app, lambda: not data.busy)
        assert not data.errorText and data.info_model.rowCount() == 3
        assert data.inventoryResult["columns"][1]["non_null"] == 405
        data.selectInspectionCell(1, 0, False)
        visual_item(window.contentItem(), "dataHeading_values").clicked.emit()
        window.findChild(QObject, "computeValues").clicked.emit()
        spin(app, lambda: not data.busy)
        assert (
            data.profileResult["unique"] == 405
            and len(data.profileResult["unique_values"]) == 200
        )
        window.findChild(QObject, "nextUniquePage").clicked.emit()
        spin(app, lambda: not data.busy)
        assert data.profileResult["unique_offset"] == 200
        visual_item(window.contentItem(), "dataHeading_describe").clicked.emit()
        window.findChild(QObject, "computeDescribe").clicked.emit()
        spin(app, lambda: not data.busy)
        assert (
            data.describe_model.rowCount() == 8
            and data.describeResult["scope"] == "full"
        )
        visual_item(window.contentItem(), "dataHeading_rows").clicked.emit()
        window.findChild(QObject, "columnDescription").setProperty(
            "text", "Sentetik sipariş tutarı; TL."
        )
        window.findChild(QObject, "columnRole").setProperty("currentIndex", 2)
        window.findChild(QObject, "columnUnit").setProperty("text", "TL")
        window.findChild(QObject, "applyColumnRole").clicked.emit()
        assert (
            projects.dirty
            and data.columnDetails["description"] == "Sentetik sipariş tutarı; TL."
        )
        root = str(projects.store.root)
        assert projects.save() and projects.closeProject(False) and projects.open(root)
        data.selectColumn(data.datasetColumns[1]["id"])
        assert data.columnDetails["unit"] == "TL"
        assert data.columnDetails["description"] == "Sentetik sipariş tutarı; TL."
        assert source.read_bytes() == original
        assert data.inventoryResult == {} and data.describeResult == {}
    finally:
        teardown(app, window)


def test_inventory_cancel_and_changed_column_never_publish(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 700)
    original = source.read_bytes()
    try:
        data.inspectColumns(False, False)
        assert data.busy
        data.cancel()
        spin(app, lambda: not data.busy)
        assert data.inventoryResult == {} and data.info_model.rowCount() == 0
        data.inspectColumns(False, True)
        data.selectColumn(data.datasetColumns[1]["id"])
        spin(app, lambda: not data.busy)
        assert data.describeResult == {} and "Eski veri" in data.message
        assert source.read_bytes() == original
    finally:
        teardown(app, window)


def test_inspection_tables_keyboard_open_column_and_allow_tab_exit(
    tmp_path, monkeypatch
):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 25)
    original = source.read_bytes()
    try:
        window.setProperty("selectedSection", 1)
        window.setProperty("dataPane", "profile")
        data.inspectColumns(False, False)
        spin(app, lambda: not data.busy)
        table = visual_item(window.contentItem(), "inventoryTable")
        spin(app, lambda: table.property("rows") == data.info_model.rowCount())
        table.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Down)
        assert table.property("chosenRow") == 1
        QTest.keyClick(window, Qt.Key_Return)
        assert window.property("dataPane") == "values"
        assert data.selectedColumn == data.datasetColumns[1]["id"]

        window.setProperty("dataPane", "describe")
        data.inspectColumns(False, True)
        spin(app, lambda: not data.busy)
        table = visual_item(window.contentItem(), "describeTable")
        spin(
            app,
            lambda: (
                table.property("columns") == data.describe_model.columnCount()
                and table.property("rows") == data.describe_model.rowCount()
            ),
        )
        table.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Right)
        assert table.property("chosenColumn") == 1
        QTest.keyClick(window, Qt.Key_Space)
        assert window.property("dataPane") == "values"
        assert data.selectedColumn == data.datasetColumns[1]["id"]

        window.setProperty("dataPane", "describe")
        table.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Tab)
        assert not table.hasActiveFocus()
        assert source.read_bytes() == original and not projects.busy

        assert projects.closeProject(False)
        window.setProperty("dataPane", "profile")
        table = visual_item(window.contentItem(), "inventoryTable")
        app.processEvents()
        table.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Down)
        QTest.keyClick(window, Qt.Key_Return)
        assert table.property("chosenRow") == 0
        assert window.property("dataPane") == "profile"
        QTest.keyClick(window, Qt.Key_Tab)
        assert not table.hasActiveFocus()
    finally:
        teardown(app, window)


def test_inventory_automatically_reads_full_dataset_and_only_shows_schema_summary(
    tmp_path, monkeypatch
):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 10005)
    original = source.read_bytes()
    try:
        window.setProperty("selectedSection", 1)
        visual_item(window.contentItem(), "dataHeading_profile").clicked.emit()
        spin(app, lambda: data.inventoryResult.get("used_n") == 10005 and not data.busy)
        assert data.inventoryResult["scope"] == "full"
        assert data.inventoryResult["columns"][1]["non_null"] == 10005
        assert data.info_model.columnCount() == 5
        assert window.findChild(QObject, "inventoryScope") is None
        assert not window.findChild(QObject, "computeInventory").property("visible")
        assert window.findChild(QObject, "inventoryColumnCount").property("text") == "3"
        summary = window.findChild(QObject, "inventoryTypes").property("text")
        assert "Int64: 1 — amount" in summary
        assert "String: 2 — id, category" in summary
        assert "\n" in summary
        assert window.findChild(QObject, "inventoryDiskSize").property("text")
        assert source.read_bytes() == original
    finally:
        teardown(app, window)


def test_profile_of_legacy_text_shows_actual_stored_type(tmp_path, monkeypatch):
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "legacy.csv"
    source.write_text("PassengerId,Pclass\n1,3\n2,1\n")
    original = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.setType(0, "text")
        imports.setType(1, "text")
        imports.refreshPreview()
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText
        data = app._veri_ufku_resources[0]._dataset_resources
        snapshot = projects.store.path(data.dataset()["snapshot_uri"])
        before = snapshot.read_bytes()
        window.setProperty("selectedSection", 1)
        visual_item(window.contentItem(), "dataHeading_profile").clicked.emit()
        spin(app, lambda: data.inventoryResult.get("used_n") == 2 and not data.busy)
        assert data.info_model.columnCount() == 5
        assert data.info_model.data(data.info_model.index(0, 1)) == "String"
        assert data.info_model.data(data.info_model.index(0, 2)) == "2"
        assert data.info_model.data(data.info_model.index(0, 3)) == "0"
        assert "String: 2 — PassengerId, Pclass" in window.findChild(
            QObject, "inventoryTypes"
        ).property("text")
        assert snapshot.read_bytes() == before and source.read_bytes() == original
    finally:
        teardown(app, window)


def test_simple_column_notes_under_profile_persist_and_preserve_semantics(
    tmp_path, monkeypatch
):
    import copy

    app, window, projects, data, source = load(tmp_path, monkeypatch, 12)
    original = source.read_bytes()
    try:
        amount = data.dataset()["import_metadata"]["columns"][1]["id"]
        category = data.dataset()["import_metadata"]["columns"][2]["id"]
        data.selectColumn(amount)
        data.applyRole("measurement", "TL", "", "satış")
        semantics = copy.deepcopy(data.dataset()["semantic_metadata"][amount])
        snapshot = data.dataset()["snapshot_uri"]
        snapshot_bytes = projects.store.path(snapshot).read_bytes()
        window.setProperty("selectedSection", 1)
        visual_item(window.contentItem(), "dataHeading_profile").clicked.emit()
        spin(app, lambda: data.inventoryResult.get("used_n") == 12 and not data.busy)
        assert window.findChild(QObject, "dataHeading_notes") is None
        notes = visual_item(window.contentItem(), "columnNotesPanel")
        assert notes.property("visible")
        field = window.findChild(QObject, "columnNoteDescription")
        field.setProperty("text", "Satış tutarı. Eksik değer bilinmiyor demektir.")
        data.selectColumn(category)
        field.setProperty("text", "Ürün grubu.")
        data.selectColumn(amount)
        assert (
            field.property("text") == "Satış tutarı. Eksik değer bilinmiyor demektir."
        )
        window.findChild(QObject, "saveColumnNote").clicked.emit()
        spin(app, lambda: not projects.busy and not projects.dirty and not data.busy)
        saved = data.dataset()["semantic_metadata"][amount]
        assert {k: v for k, v in saved.items() if k != "description"} == semantics
        assert saved["description"] == field.property("text")
        assert data.dataset()["snapshot_uri"] == snapshot
        assert projects.store.path(snapshot).read_bytes() == snapshot_bytes
        data.selectColumn(category)
        assert field.property("text") == "Ürün grubu."
        window.findChild(QObject, "saveColumnNote").clicked.emit()
        spin(app, lambda: not projects.busy and not projects.dirty and not data.busy)
        assert not data.dataset()["semantic_metadata"][category]["confirmed"]
        assert projects.closeProject() and projects.open(str(tmp_path / "project"))
        data.selectColumn(amount)
        assert (
            data.columnDetails["description"]
            == "Satış tutarı. Eksik değer bilinmiyor demektir."
        )
        data.selectColumn(category)
        assert data.columnDetails["description"] == "Ürün grubu."
        spin(
            app,
            lambda: (
                window.findChild(QObject, "savedColumnNotesList").property("count") == 2
            ),
        )
        spin(
            app,
            lambda: (
                visual_item(window.contentItem(), "savedColumnNote_" + amount)
                is not None
            ),
        )
        assert window.findChild(QObject, "savedColumnNotesPanel").property("visible")
        assert (
            visual_item(window.contentItem(), "savedColumnNote_" + amount).property(
                "text"
            )
            == "Satış tutarı. Eksik değer bilinmiyor demektir."
        )
        assert (
            visual_item(window.contentItem(), "savedColumnNote_" + category).property(
                "text"
            )
            == "Ürün grubu."
        )
        assert window.findChild(QObject, "valuesScope") is None
        assert window.findChild(QObject, "describeScope") is None
        assert window.findChild(QObject, "profileMethod") is None
        assert source.read_bytes() == original
    finally:
        teardown(app, window)
