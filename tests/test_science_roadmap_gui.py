"""Actual accordion navigation, planned paths and responsive timeline geometry."""

from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown
from test_learning_gui import visual_item


def test_science_roadmap_expand_keyboard_navigation_planned_and_resize(
    tmp_path, monkeypatch
):
    app, window, _, projects, _ = setup(tmp_path, monkeypatch)
    try:
        assert (
            window.findChild(QObject, "roadmapHeading").property("text")
            == "Veri Bilimi Yol Haritası"
        )

        def item(name):
            return visual_item(window.contentItem(), name)

        item("roadmapOpen_0").clicked.emit()
        assert window.property("selectedSection") == 1
        assert window.property("dataPane") == ""
        assert not window.property("infoOpen")
        window.setProperty("selectedSection", 0)
        item("roadmapOpen_2").clicked.emit()
        assert window.property("selectedSection") == 2
        assert not window.property("infoOpen")
        spin(
            app,
            lambda: (
                window.findChild(QObject, "operationKind").property("currentIndex") == 3
            ),
        )
        window.setProperty("selectedSection", 0)
        app.processEvents()
        item("roadmapToggle_2").clicked.emit()
        spin(app, lambda: item("roadmapStep_2_1").isVisible())
        item("roadmapStep_2_1").clicked.emit()
        spin(
            app,
            lambda: (
                window.findChild(QObject, "transformMethod").property("currentIndex")
                == 8
            ),
        )
        assert window.findChild(QObject, "operationKind").property("currentIndex") == 4
        assert not window.property("infoOpen")
        window.setProperty("selectedSection", 0)
        app.processEvents()
        first = item("roadmapStage_0")
        analysis = item("roadmapStage_1")
        assert first is not None and analysis is not None
        toggle = item("roadmapToggle_1")
        assert not analysis.property("expanded")
        toggle.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        spin(app, lambda: analysis.property("expanded"))
        spin(app, lambda: item("roadmapStep_1_0").isVisible())
        assert item("roadmapStep_1_3").isEnabled()
        old = projects.draft.copy()
        item("roadmapStep_1_3").clicked.emit()
        spin(app, lambda: window.property("advanced"))
        spin(
            app,
            lambda: window.findChild(QObject, "scenarioExpanded").property("checked"),
        )
        assert window.property("selectedSection") == 5 and projects.draft == old
        window.findChild(QObject, "beginnerButton").clicked.emit()
        window.setProperty("selectedSection", 0)
        app.processEvents()
        # Opening the explicit advanced route navigates, without starting a solver.
        item("roadmapStep_1_0").clicked.emit()
        assert window.property("selectedSection") == 1
        assert item("nav1").hasActiveFocus()
        assert window.findChild(QObject, "datasetTabs").property("currentIndex") == 0
        window.setProperty("selectedSection", 0)
        app.processEvents()
        toggle.clicked.emit()
        spin(app, lambda: not analysis.property("expanded"))
        window.setWidth(1366)
        app.processEvents()
        QTest.qWait(300)
        assert item("roadmapCard_0").x() == item("roadmapCard_1").x() == 64
        window.setWidth(720)
        app.processEvents()
        QTest.qWait(300)
        assert item("roadmapCard_0").x() == item("roadmapCard_1").x() == 64
        assert item("roadmapCard_0").width() > 250
        learning = app._veri_ufku_resources[0]._learning_resources
        learning.openContext("home.roadmap")
        assert learning.article["id"] == "home"
        assert projects.draft == old
    finally:
        teardown(app, window)
