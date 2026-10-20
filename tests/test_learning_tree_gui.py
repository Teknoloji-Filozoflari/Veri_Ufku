from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtTest import QTest
from test_learning_gui import spin, visual_item

from veri_ufku.app import create_application


def test_learning_hierarchy_and_readable_modal(tmp_path, monkeypatch):
    for name in ("CONFIG", "STATE", "CACHE"):
        monkeypatch.setenv(f"XDG_{name}_HOME", str(tmp_path / name.lower()))
    app, window, _ = create_application()
    try:
        window.setProperty("selectedSection", 7)
        assert window.findChild(QObject, "helpButton").property("visible")
        assert window.findChild(QObject, "glossaryButton") is None
        assert window.findChild(QObject, "readingMarksButton") is None
        assert not window.findChild(QObject, "guidePanel").property("visible")
        stage = visual_item(window.contentItem(), "learningStage-data")
        stage.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        group = visual_item(window.contentItem(), "learningGroup-definition")
        spin(app, lambda: group.isVisible())
        QTest.qWait(280)
        group.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        topic = visual_item(window.contentItem(), "learningArticle-data")
        spin(app, lambda: topic.isVisible())
        QTest.qWait(250)
        topic.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        reader = window.findChild(QObject, "learningReader")
        spin(app, lambda: reader.property("visible"))
        assert window.property("readingOpen") and window.property("infoOpen")
        content = reader.property("contentItem")
        assert visual_item(content, "articleTitle").property("text") == "Veri nedir?"
        assert not visual_item(content, "articleDepthPicker").isVisible()
        learning = app._veri_ufku_resources[-3]
        assert visual_item(content, "articleSource-0") is None
        source_toggle = visual_item(content, "articleSourcesToggle")
        source_toggle.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        spin(app, lambda: visual_item(content, "articleSource-0") is not None)
        assert "reference" not in visual_item(content, "articleSource-0").property(
            "text"
        )
        learning.openArticle("analysis-prescriptive")
        app.processEvents()
        assert visual_item(content, "articleSource-0") is None
        assert "otomatik karar aracı çalıştırılmaz" in learning.article["critical"]
        source_toggle.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        spin(app, lambda: visual_item(content, "articleSource-0") is not None)
        learning.openArticle("analysis-prescriptive")
        app.processEvents()
        assert visual_item(content, "articleSource-0") is None
        learning.openArticle("data")
        assert reader.property("width") <= window.width()
        window.setWidth(720)
        window.setHeight(560)
        app.processEvents()
        assert reader.property("width") <= 720
        assert reader.property("height") <= 560
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        assert topic.hasActiveFocus()
        window.setWidth(1366)
        app.processEvents()
        QTest.qWait(300)
        learning_card = visual_item(window.contentItem(), "learningCard-data")
        window.setProperty("selectedSection", 0)
        app.processEvents()
        roadmap = window.findChild(QObject, "scienceRoadmap")
        project = window.findChild(QObject, "projectPanel")
        home_card = visual_item(window.contentItem(), "roadmapCard_0")
        assert home_card.width() == learning_card.width()
        assert home_card.x() == learning_card.x()
        window.setWidth(720)
        app.processEvents()
        assert home_card.x() == 64
        window.setProperty("selectedSection", 7)
        app.processEvents()
        QTest.qWait(300)
        assert learning_card.x() == 64
        window.setProperty("selectedSection", 0)
        app.processEvents()
        assert (
            project.mapToScene(QPointF(0, 0)).y()
            >= roadmap.mapToScene(QPointF(0, roadmap.height())).y()
        )

    finally:
        app._veri_ufku_resources[-1]()
        window.deleteLater()
        app.processEvents()
