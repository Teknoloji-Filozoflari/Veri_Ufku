import socket
import time
import urllib.request

from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from veri_ufku.app import create_application


def spin(app, predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError("Offline help GUI timed out")


def visual_item(item, name):
    if item.objectName() == name:
        return item
    for child in item.childItems():
        found = visual_item(child, name)
        if found:
            return found
    return None


def test_offline_qml_search_context_depth_critical_close_and_example_isolation(
    tmp_path, monkeypatch
):
    def network_forbidden(*args, **kwargs):
        raise AssertionError("Help attempted network access")

    monkeypatch.setattr(socket, "create_connection", network_forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", network_forbidden)
    for name in ("CONFIG", "STATE", "CACHE"):
        monkeypatch.setenv(f"XDG_{name}_HOME", str(tmp_path / name.lower()))
    app, window, bridge = create_application()
    learning = app._veri_ufku_resources[-3]
    preferences = app._veri_ufku_resources[-2]
    try:
        spin(app, lambda: not window.grabWindow().isNull())
        # Real nav + text input and article activation from search results.
        nav = visual_item(window.contentItem(), "nav7")
        nav.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        spin(app, lambda: window.property("selectedSection") == 7)
        search = visual_item(window.contentItem(), "learningSearch")
        search.forceActiveFocus()
        for letter in "medyan":
            QTest.keyClick(window, getattr(Qt.Key, "Key_" + letter.upper()))
        spin(app, lambda: learning.query == "medyan")
        assert "mean-median" in [a["id"] for a in learning.results]
        result_button = visual_item(window.contentItem(), "learningArticle-mean-median")
        result_button.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        spin(app, lambda: window.property("infoOpen"))
        assert learning.article["id"] == "mean-median"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        assert visual_item(
            window.contentItem(), "learningArticle-mean-median"
        ).hasActiveFocus()
        # Model screen opens prediction, and related concept opens leakage.
        window.setProperty("selectedSection", 5)
        QTest.keyClick(window, Qt.Key.Key_F1)
        spin(app, lambda: window.property("infoOpen"))
        assert learning.article["id"] == "prediction"
        related = visual_item(window.contentItem(), "related-leakage")
        related.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        assert learning.article["id"] == "leakage"
        depth = visual_item(window.contentItem(), "articleDepthPicker")
        depth.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        QTest.keyClick(window, Qt.Key.Key_End)
        QTest.keyClick(window, Qt.Key.Key_Return)
        spin(app, lambda: learning.depth == 2)
        preferences.setView("advanced")
        app.processEvents()
        assert "Test verisiyle" in learning.article["critical"]
        warning = visual_item(window.contentItem(), "criticalWarning")
        assert warning.isVisible()
        # Jobs are not stopped or rebound by reading/closing either help layout.
        bridge.start("demo.io")
        job = bridge.job_id
        binding = bridge.session.binding
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        assert bridge.job_id == job and bridge.session.binding == binding
        assert bridge.active
        window.setWidth(720)
        window.setHeight(560)
        window.setProperty("selectedSection", 0)
        window.setProperty("showDemo", True)
        app.processEvents()
        cpu = window.findChild(QQuickItem, "taskHelpButton")
        cpu.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_F1)
        spin(app, lambda: window.property("infoOpen"))
        assert learning.article["id"] == "tasks"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        assert cpu.hasActiveFocus()
        assert bridge.job_id == job
        # Try opens actual isolated sample learning project, never analytic work.
        window.setWidth(1366)
        window.setHeight(900)
        window.setProperty("selectedSection", 7)
        window.findChild(QQuickItem, "helpButton").clicked.emit()
        try_button = visual_item(window.contentItem(), "tryLearningButton")
        try_button.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        example = window.findChild(QObject, "learningExampleWindow")
        spin(app, lambda: example.isVisible())
        assert bridge.session.binding == binding and bridge.job_id == job
        sandbox = learning.exampleLibrary
        sandbox.setQuery("korelasyon")
        assert learning.query == "medyan"
        example.close()
        window.requestActivate()
        QTest.qWait(100)
        assert bridge.job_id == job
        spin(app, lambda: not bridge.active)
        assert bridge.session.manager.snapshot(job).result_for(binding) is not None
        result = bridge.resultText
        window.setProperty("selectedSection", 7)
        window.findChild(QQuickItem, "helpButton").clicked.emit()
        QTest.qWait(250)
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        assert bridge.resultText == result
    finally:
        bridge.session.manager.shutdown()
        app._veri_ufku_resources[-1]()
        window.deleteLater()
        app.processEvents()


def test_article_markup_is_rendered_as_plain_text(tmp_path, monkeypatch):
    for name in ("CONFIG", "STATE", "CACHE"):
        monkeypatch.setenv(f"XDG_{name}_HOME", str(tmp_path / name.lower()))
    app, window, bridge = create_application()
    learning = app._veri_ufku_resources[-3]
    try:
        payload = '<img src="https://invalid.example/private"><script>alert(1)</script>'
        learning.catalog.articles["home"]["summary"] = payload
        window.findChild(QQuickItem, "helpButton").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        label = visual_item(window.contentItem(), "articleSummary")
        assert label.property("text") == payload
        from PySide6.QtQml import QQmlExpression, qmlContext

        assert QQmlExpression(
            qmlContext(label), label, "textFormat === Text.PlainText"
        ).evaluate()[0]
        # A picker below the fold becomes visible when focused at 200% in the drawer.
        window.setWidth(720)
        window.setHeight(560)
        app._veri_ufku_resources[-2].setTextScale(2.0)
        QTest.qWait(300)
        drawer = window.findChild(QObject, "informationDrawer")
        picker = visual_item(drawer.property("contentItem"), "articleDepthPicker")
        picker.forceActiveFocus()
        spin(
            app,
            lambda: (
                0 <= picker.mapToScene(QPointF(0, 0)).y()
                and picker.mapToScene(QPointF(0, picker.height())).y()
                <= window.height()
            ),
        )

    finally:
        bridge.session.manager.shutdown()
        app._veri_ufku_resources[-1]()
        window.deleteLater()
        app.processEvents()
