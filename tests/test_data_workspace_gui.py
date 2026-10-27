"""Veri empty card and loaded workspace panel."""

from PySide6.QtCore import QObject
from test_dataset_gui import load
from test_import_gui import setup, spin, teardown, visible_item
from test_learning_gui import visual_item


def test_empty_veri_shows_card_without_dock(tmp_path, monkeypatch):
    app, window, _, projects, _ = setup(tmp_path, monkeypatch)

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        item("moduleVeri").clicked.emit()
        spin(app, lambda: window.property("selectedSection") == 1)
        assert window.property("veriEmpty")
        assert item("dataEmptyCard") is not None
        assert item("chooseCsvButton") is not None
        assert item("dataEmptyProjectName") is not None
        assert (
            item("dataEmptyBrowseProject") is not None
            or item("importProjectButton") is not None
        )
        assert item("dataEmptyFooter") is not None
        assert not item("dataEmptyFooter").property("visible")
        browse = item("dataEmptyBrowseSource")
        assert browse is not None and not browse.property("visible")
        hint = item("dataEmptyHint")
        assert hint is not None and not hint.property("visible")
        assert item("dataEmptyLibrary").property("text") == "Verilerim"
        assert item("dataEmptySample").property("text") == "Örnek"
        assert item("headerBack") is not None
        assert item("headerSaveProject") is not None
        assert not item("commandSearchButton").property("visible")
        assert not item("closeButton").property("visible")
        drop = item("csvDropArea")
        assert drop is None or not drop.property("visible")
        reason = item("importBlockReason")
        assert reason is not None and not reason.property("visible")
        assert not item("toolDock").property("visible")
        assert item("dataWorkspacePanel") is None or not item(
            "dataWorkspacePanel"
        ).property("visible")
        assert projects.draft == projects.draft
    finally:
        teardown(app, window)


def test_loaded_veri_shows_table_and_ten_chips(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 40)
    before = data.dataset()["version_id"]

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        item("moduleVeri").clicked.emit()
        spin(app, lambda: window.property("showTable"))
        assert item("datasetTable").property("visible")
        assert item("toolDock").property("visible")
        panel = item("dataWorkspacePanel")
        assert panel is not None and panel.property("visible")
        assert item("dataWorkspaceTitle") is not None
        assert item("dataWorkspaceTitle").property("text") == "Veri"
        assert item("dataHealthSummary") is not None
        assert item("dataNextBlock") is not None
        assert item("dataNextBlock").property("visible")
        assert not item("dockClose").property("visible")
        for index in range(1, 11):
            chip = item(f"dataBlockChip_{index}")
            assert chip is not None
        item("dataBlockChip_2").clicked.emit()
        app.processEvents()
        assert panel.property("selectedBlock") == 2
        assert item("dataBlockChooseFile") is not None
        assert item("dataBlockPreviewTable") is not None
        item("dataBlockChip_3").clicked.emit()
        app.processEvents()
        assert panel.property("selectedBlock") == 3
        summary = item("dataBlockReadingSummary")
        assert summary is not None
        primary = item("dataPrimaryAction")
        assert primary is not None
        assert "satır" in (window.property("veriScopeLine") or "")
        assert item("headerBack") is not None
        assert item("headerSaveProject") is not None
        assert item("datasetHeader") is not None
        assert data.dataset()["version_id"] == before
        assert source.is_file()
    finally:
        teardown(app, window)


def test_import_from_empty_project_saves_dataset(tmp_path, monkeypatch):
    import veri_ufku.ui.projects as projects_mod

    docs = tmp_path / "docs"
    docs.mkdir()
    monkeypatch.setattr(
        projects_mod.QStandardPaths, "writableLocation", lambda kind: str(docs)
    )
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "sales.csv"
    source.write_text("id,ad\n1,Ada\n2,Ece\n", encoding="utf8")
    try:
        assert projects.closeProject()
        window.setProperty("selectedSection", 1)
        imports.choose(str(source))
        spin(app, lambda: not imports.busy and len(imports.columns) > 0)
        assert not projects.opened
        assert not projects.dirty
        button = visible_item(window.contentItem(), "importCsvButton")
        assert button is not None and button.isEnabled()
        button.clicked.emit()
        spin(
            app,
            lambda: (
                projects.opened
                and len(projects.draft["datasets"]) == 1
                and not projects.busy
                and not imports.busy
            ),
        )
        assert projects.draft == projects.saved
        assert not projects.dirty
        status = visible_item(window.contentItem(), "workspaceStatus")
        assert status is not None
        assert "Kaydedilmemiş" not in status.property("text")
        assert "Proje açık" in status.property("text")
    finally:
        teardown(app, window)
