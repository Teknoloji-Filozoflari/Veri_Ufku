"""UX4 GUI: Verilerim copy survives deletion of library entry for an open project."""

from pathlib import Path

from PySide6.QtCore import QObject
from test_dataset_gui import load
from test_import_gui import spin, teardown
from test_learning_gui import visual_item

from veri_ufku.storage import user_library as library


def test_ux4_library_add_import_delete_keeps_project_dataset(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 40)
    engine = app._veri_ufku_resources[0]
    data_library = engine.rootContext().contextProperty("dataLibrary")
    version_before = data.dataset()["version_id"]
    source_bytes = source.read_bytes()

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        window.setProperty("selectedSection", 1)
        window.setProperty("dataPane", "import")
        app.processEvents()
        item("importLibraryToggle").setProperty("checked", True)
        app.processEvents()
        assert item("dataLibraryPanel") is not None
        assert len(data_library.samples) >= 2

        data_home = Path(engine.rootContext().contextProperty("dataLibrary").paths.data)
        entry = library.add_file_entry(
            data_home, source, name="Kaynak kopya", description="ux4"
        )
        data_library.changed.emit()
        app.processEvents()
        data_library.useLibraryEntry(entry["id"])
        spin(app, lambda: not engine.rootContext().contextProperty("imports").busy)
        # Project already has a dataset; library choose only previews — dataset version unchanged
        assert data.dataset()["version_id"] == version_before
        assert source.read_bytes() == source_bytes

        data_library.requestDelete(entry["id"])
        data_library.confirmDelete()
        assert library.find_entry(data_home, entry["id"]) is None
        assert data.dataset()["version_id"] == version_before
        assert projects.draft["datasets"]
    finally:
        teardown(app, window)
