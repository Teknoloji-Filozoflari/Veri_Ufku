"""Beginner journey: real routes/help, explicit expert tools, no data mutation."""

import copy

from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown
from test_learning_gui import visual_item
from test_ui_renewal import evaluate, screenshot


def test_beginner_journey_project_last_shared_learning_and_modes(tmp_path, monkeypatch):
    app, window, _, projects, _ = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    preferences = engine.rootContext().contextProperty("preferences")
    before = copy.deepcopy(projects.draft)

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        assert preferences.view == "beginner"
        assert not window.property("advanced")
        road, project = item("scienceRoadmap"), item("projectPanel")
        app.processEvents()
        assert project.property("y") >= road.property("y") + road.property("height")
        screenshot(window, "beginner-home")
        item("newProjectButton").forceActiveFocus()
        screenshot(window, "project-at-journey-end")
        item("roadmapOpen_0").clicked.emit()
        assert window.property("selectedSection") == 1
        assert item("journeyGuide").property("visible")
        assert item("journeyLearn").property("visible")
        screenshot(window, "beginner-data")
        item("journeyLearn").clicked.emit()
        spin(app, lambda: window.property("readingOpen"))
        assert window.property("selectedSection") == 7
        assert engine._learning_resources.article["id"] == "data"
        QTest.keyClick(window, Qt.Key_Escape)
        spin(app, lambda: not window.property("readingOpen"))
        learn = item("learningRoadmap")
        assert learn.property("visible")
        assert evaluate(road, "stageModel.map(s => s.id).join(',')") == evaluate(
            learn, "stageModel.map(s => s.id).join(',')"
        )
        screenshot(window, "learn-map")
        for section in range(1, 7):
            window.setProperty("selectedSection", section)
            app.processEvents()
            assert item("journeyGuide").property("visible")
            article = evaluate(item("journeyGuide"), "step.article")
            engine._learning_resources.openArticle(article)
            assert engine._learning_resources.article["id"] == article
        window.setProperty("selectedSection", 6)
        assert item("environmentExpanded") is None
        item("expertToolsEntry").clicked.emit()
        spin(app, lambda: window.property("advanced"))
        assert not item("journeyGuide").property("visible")
        assert item("deferredEnvironmentPanel").property("visible")
        assert item("environmentExpanded") is not None
        item("environmentExpanded").setProperty("checked", True)
        screenshot(window, "advanced-report")
        item("beginnerButton").clicked.emit()
        assert not item("deferredEnvironmentPanel").property("visible")
        item("advancedButton").clicked.emit()
        assert item("environmentExpanded").property("checked")
        window.setProperty("selectedSection", 0)
        app.processEvents()
        assert not road.property("visible")
        assert project.property("visible")
        screenshot(window, "advanced-home")
        item("beginnerButton").clicked.emit()
        assert road.property("visible")
        for width, scale in ((720, 1.0), (720, 2.0), (1366, 1.0)):
            preferences.setTextScale(scale)
            window.setWidth(width)
            app.processEvents()
            assert item("roadmapCard_0").property("width") > 200
            screenshot(window, f"home-{width}-{scale}")
        assert projects.draft == before
    finally:
        teardown(app, window)
