"""Workspace shell: module rail, data table, tool dock."""

from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_learning_gui import visual_item


def test_workspace_shell_modules_dock_and_narrow_center(tmp_path, monkeypatch):
    app, window, _, projects, _ = setup(tmp_path, monkeypatch)
    draft_before = projects.draft

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        rail = item("moduleRail")
        assert rail is not None and rail.property("visible")
        assert item("stageStrip") is None or not item("stageStrip").property("visible")
        veri = item("moduleVeri")
        veri.clicked.emit()
        spin(app, lambda: window.property("selectedSection") == 1)
        assert window.property("veriEmpty")
        assert item("dataEmptyCard") is not None
        assert not item("toolDock").property("visible")
        assert item("moduleOgren") is None
        for name in (
            "moduleIncele",
            "moduleGrafik",
            "moduleHazirla",
            "moduleIstatistik",
            "moduleModel",
            "moduleRapor",
        ):
            assert item(name) is not None
        item("moduleIncele").clicked.emit()
        spin(app, lambda: window.property("selectedSection") == 1)
        assert window.property("selectedSection") == 1
        assert window.property("veriEmpty")
        item("moduleIstatistik").clicked.emit()
        spin(app, lambda: window.property("selectedSection") == 4)
        assumption = item("statisticsAssumption").property("text")
        assert "Welch" in assumption and "Mann-Whitney" in assumption
        advice = item("statisticsAdviceQuestion").property("text")
        assert "uydurulmaz" in advice
        item("moduleGrafik").clicked.emit()
        spin(
            app,
            lambda: (
                item("chartExplainSee") is not None
                and "üretilmez" in item("chartExplainSee").property("text")
            ),
        )

        for section, probe in (
            (2, "operationPreview"),
            (3, "chartCreate"),
            (5, "preparationScan"),
            (6, "deferredReportBuilderPanel"),
        ):
            window.setProperty("selectedSection", section)
            spin(
                app,
                lambda p=probe: item(p) is not None and item(p).property("visible"),
            )
            assert item("toolDock").property("visible")

        window.setProperty("selectedSection", 2)
        spin(app, lambda: item("operationPreviewContract") is not None)
        contract = item("operationPreviewContract").property("text")
        assert (
            "Önizleme" in contract
            and "Uygula" in contract
            and "kaynak dosya" in contract
        )
        assert item("moduleModel").property("visible")
        window.setProperty("selectedSection", 5)
        spin(app, lambda: item("modelLeakageNotice") is not None)
        assert not item("modelLeakageNotice").property("visible")
        window.setProperty("selectedSection", 6)
        spin(app, lambda: item("reportWithoutModel") is not None)
        assert not item("reportWithoutModel").property("visible")
        spin(app, lambda: item("reportStatisticsFindings") is not None)
        assert "uydurulmaz" in item("reportStatisticsFindings").property("text")
        assert "uydurulmaz" in item("reportOperationPython").property("text")
        assert "Python:" in item("reportEnvironment").property("text")
        assert "veri-ufku==" in item("reportEnvironment").property("text")
        assert "uydurulmaz" in item("reportSeed").property("text")
        assert "uydurulmaz" in item("reportSourceLicense").property("text")
        assert item("reportLicenseNote") is not None
        assert item("reportPackage") is not None
        assert item("reportShareMode").property("currentIndex") == 0
        item("reportPrivacyPreview").clicked.emit()
        spin(app, lambda: "uydurulmaz" in item("reportPrivacyText").property("text"))

        window.setWidth(720)
        app.processEvents()
        workspace = item("workspace")
        dock = item("toolDock")
        assert workspace is not None and dock is not None
        assert not window.property("showTable")
        assert dock.property("visible")
        assert dock.property("width") >= 280
        window.setWidth(1366)
        app.processEvents()
        assert projects.draft == draft_before
        assert item("uxStageStatus") is None
    finally:
        teardown(app, window)
