"""UX2 workspace shell: stage strip, context panel, existing screens, narrow width."""

from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_learning_gui import visual_item


def test_ux2_stage_strip_context_panel_and_narrow_center(tmp_path, monkeypatch):
    app, window, _, projects, _ = setup(tmp_path, monkeypatch)
    draft_before = projects.draft

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        assert not window.property("advanced")
        strip = item("stageStrip")
        assert strip is not None and strip.property("visible")
        stage2 = item("uxStage2")
        assert stage2 is not None
        stage2.clicked.emit()
        spin(app, lambda: window.property("uxStage") == 2)
        assert window.property("selectedSection") == 1
        assert window.property("dataPane") == "rows"
        assert item("nav1") is not None

        toggle = item("contextPanelToggle")
        toggle.clicked.emit()
        spin(app, lambda: window.property("contextPanelOpen"))
        panel = item("contextSidePanelHost")
        assert panel is not None and panel.property("visible")
        tabs = item("contextPanelTabs")
        tabs.setProperty("currentIndex", 1)
        app.processEvents()
        learn = item("contextLearnButton")
        assert learn is not None and learn.property("visible")
        item("contextPanelClose").clicked.emit()
        spin(app, lambda: not window.property("contextPanelOpen"))
        assert window.property("selectedSection") == 1
        assert window.property("dataPane") == "rows"

        for section, probe in (
            (2, "operationPreview"),
            (3, "chartCreate"),
            (5, "preparationScan"),
            (6, "deferredReportBuilderPanel"),
            (7, "learningSearch"),
        ):
            window.setProperty("selectedSection", section)
            spin(
                app,
                lambda p=probe: item(p) is not None and item(p).property("visible"),
            )

        window.setWidth(720)
        app.processEvents()
        workspace = item("workspace")
        assert workspace is not None
        assert workspace.width() >= 400
        assert item("nav0") is not None
        window.setWidth(1366)
        app.processEvents()
        assert projects.draft == draft_before
        assert item("uxStageStatus") is not None
    finally:
        teardown(app, window)
