"""Folder-only project workflow, encoded paths and saved recent names in real QML."""

import json

from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_learning_gui import visual_item


def test_folder_picker_create_search_hidden_navigation_open_recent_names(
    tmp_path, monkeypatch
):
    app, window, _, projects, _ = setup(tmp_path, monkeypatch)
    parent = tmp_path / "Klasör #1"
    parent.mkdir()
    child = parent / "İş Projesi"
    child.mkdir()
    (parent / "Diğer").mkdir()
    (parent / ".gizli").mkdir()
    try:
        assert window.findChild(QObject, "helpButton").property("visible")
        assert window.findChild(QObject, "projectHelpButton") is None
        assert (
            window.findChild(QObject, "roadmapHeading").property("text")
            == "Veri Bilimi Yol Haritası"
        )
        close = window.findChild(QObject, "closeButton")
        advanced = window.findChild(QObject, "advancedButton")
        assert close.property("symbol") == "close"
        assert close.x() > advanced.x() and close.y() == advanced.y()
        assert all(place["name"] != "Dosya sistemi" for place in projects.folderPlaces)
        assert projects.closeProject(True)
        window.findChild(QObject, "newProjectButton").clicked.emit()
        app.processEvents()
        assert window.findChild(QObject, "projectPathField") is None
        submit = window.findChild(QObject, "confirmProjectPathButton")
        assert not submit.property("enabled")
        window.findChild(QObject, "chooseProjectLocationButton").clicked.emit()
        picker = window.findChild(QObject, "projectLocationPicker")
        picker.setProperty("currentFolder", parent.as_uri())
        listing = window.findChild(QObject, "projectLocationPickerList")
        spin(app, lambda: listing.property("count") == 2)
        search = window.findChild(QObject, "projectLocationPickerSearch")
        search.setProperty("text", "Projesi")
        app.processEvents()
        row = visual_item(window.contentItem(), "folderEntry_İş Projesi")
        assert row is not None and row.property("visible")
        row.doubleClicked.emit()
        spin(app, lambda: picker.property("currentFolder").toLocalFile() == str(child))
        window.findChild(QObject, "projectLocationPickerUp").clicked.emit()
        spin(app, lambda: picker.property("currentFolder").toLocalFile() == str(parent))
        window.findChild(QObject, "projectLocationPickerHidden").setProperty(
            "checked", True
        )
        spin(app, lambda: listing.property("count") == 3)
        name = window.findChild(QObject, "projectLocationPickerNewFolderName")
        name.setProperty("text", "Yeni # klasör")
        window.findChild(QObject, "projectLocationPickerCreateFolder").clicked.emit()
        spin(
            app,
            lambda: (
                picker.property("currentFolder").toLocalFile()
                == str(parent / "Yeni # klasör")
                and not app._veri_ufku_resources[0]._folders_resources.busy
            ),
        )
        assert (parent / "Yeni # klasör").is_dir()
        window.findChild(QObject, "projectLocationPickerUp").clicked.emit()
        spin(app, lambda: listing.property("count") == 4)
        folders = app._veri_ufku_resources[0]._folders_resources
        folders.createFolder(parent.as_uri(), "Yeni # klasör")
        spin(app, lambda: not folders.busy)
        assert "zaten var" in folders.errorText
        assert (parent / "Yeni # klasör").is_dir()
        folders.createFolder(parent.as_uri(), "../dışarı")
        assert folders.errorText and not (tmp_path / "dışarı").exists()
        folders.load(parent.as_uri())
        spin(app, lambda: not folders.busy)
        window.findChild(QObject, "projectLocationPickerChoose").clicked.emit()
        app.processEvents()
        assert submit.property("enabled")
        submit.clicked.emit()
        spin(app, lambda: not projects.busy)
        assert projects.opened and not projects.errorText
        assert projects.store.root == parent / "Yeni_Proje"
        projects.setName("Çalışma projem")
        projects.request("save")
        spin(app, lambda: not projects.busy)
        assert projects.recentProjects[0]["name"] == "Çalışma projem"
        app.processEvents()
        recent = [
            visual_item(window.contentItem(), "recentProject_" + r["name"])
            for r in projects.recentProjects
        ]
        assert all(recent) and len(recent) == 2
        spin(
            app,
            lambda: recent[0].y() == recent[1].y() and recent[0].x() != recent[1].x(),
        )
        record = json.loads((projects.config / "recent-projects.json").read_text())
        assert record[0] == dict(path=str(parent / "Yeni_Proje"), name="Çalışma projem")
        assert projects.newProjectPath(parent.as_uri()) == str(parent / "Yeni_Proje_2")
        assert projects.closeProject(True)
        window.findChild(QObject, "openProjectButton").clicked.emit()
        open_picker = window.findChild(QObject, "openProjectFolderPicker")
        open_picker.setProperty("currentFolder", (parent / "Yeni_Proje").as_uri())
        open_picker.setProperty("selectedFolder", (parent / "Yeni_Proje").as_uri())
        spin(
            app,
            lambda: (
                window.findChild(QObject, "openProjectFolderPickerList").property(
                    "count"
                )
                > 0
            ),
        )
        window.findChild(QObject, "openProjectFolderPickerChoose").clicked.emit()
        spin(app, lambda: not projects.busy)
        assert projects.opened and projects.name == "Çalışma projem"
        assert not projects.errorText
    finally:
        teardown(app, window)
