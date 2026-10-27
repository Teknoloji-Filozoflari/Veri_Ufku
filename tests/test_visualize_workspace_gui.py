"""Görselleştir keşif ekranı: sekmeler, amaç kartları, canlı hesap, Python kapalı."""

import copy

from PySide6.QtCore import QObject
from test_dataset_gui import load
from test_import_gui import spin, teardown
from test_learning_gui import visual_item


def test_visualize_purpose_tabs_live_create_python_closed(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 40)
    before = copy.deepcopy(projects.draft)
    version_before = data.dataset()["version_id"]
    charts = app._veri_ufku_resources[0]._charts_resources

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        window.setProperty("selectedSection", 3)
        window.setProperty("chartTool", 0)
        spin(app, lambda: window.property("gorsellestirOpen"))
        assert window.property("centerOpen")
        assert item("visualizeWorkspace") is not None
        assert item("visualizeWorkspace").property("visible")
        assert item("chartPanel") is not None
        item("chartPanel").setProperty("liveEnabled", False)
        item("chartPanel").setProperty("liveArmed", False)
        spin(app, lambda: not data.busy and not projects.busy and not charts.busy)
        assert item("chartVariablesBox") is not None
        assert item("chartFacetSlot") is not None
        assert item("chartCreate") is None
        assert item("chartPythonToggle") is not None
        for index in range(1, 7):
            assert item(f"visualizePurposeCard_{index}") is not None
        assert item("visualizeTab_0") is not None
        assert item("visualizeTab_1") is not None
        assert item("visualizeTab_2") is not None
        # Kabuk doğrulaması create gerektirmez; sürüm/kapsam için isteğe bağlı sonuç.
        assert data.dataset()["version_id"] == version_before
        assert projects.draft["datasets"] == before["datasets"]
        scope = item("visualizeScopeBadge")
        assert scope is not None
        assert item("chartPythonPanel") is None or not item(
            "chartPythonPanel"
        ).property("visible")
        item("visualizeTab_1").clicked.emit()
        app.processEvents()
        assert item("chartExplainSee") is not None
        item("visualizeTab_2").clicked.emit()
        app.processEvents()
        assert source.is_file()
    finally:
        teardown(app, window)


def test_visualize_slot_passive_and_recalc(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 40)
    version_before = data.dataset()["version_id"]

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        window.setProperty("selectedSection", 3)
        spin(app, lambda: window.property("gorsellestirOpen"))
        item("chartPanel").setProperty("liveEnabled", False)
        item("chartKind").setProperty("currentIndex", 0)
        app.processEvents()
        y = item("chartY")
        assert y is not None
        assert not y.property("enabled")
        assert "istemiyor" in (y.property("displayText") or "")
        assert item("chartRecalc") is not None
        assert data.dataset()["version_id"] == version_before
        assert source.is_file()
    finally:
        teardown(app, window)
