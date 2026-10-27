"""UX6 GUI: missing impact preview leaves version and source unchanged."""

from PySide6.QtCore import QObject
from test_dataset_gui import load
from test_import_gui import spin, teardown
from test_learning_gui import visual_item


def test_ux6_missing_impact_preview_does_not_apply(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 80)
    before = source.read_bytes()
    version = data.dataset()["version_id"]
    columns = data.dataset()["import_metadata"]["columns"]
    amount = next(c for c in columns if c["name"] == "amount")

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        window.setProperty("selectedSection", 1)
        window.findChild(QObject, "datasetTabs").setProperty("currentIndex", 2)
        app.processEvents()
        assert window.property("dataPane") == "quality"
        data.previewMissingDrop(amount["id"], "")
        spin(app, lambda: bool(data.missingImpact.get("dataset_version")))
        assert data.missingImpact["applied"] is False
        assert data.missingImpact["missing_n"] >= 0
        assert data.dataset()["version_id"] == version
        assert source.read_bytes() == before
        result = item("missingImpactResult")
        assert result is not None
        assert "kaybolur" in str(result.property("text"))
    finally:
        teardown(app, window)
