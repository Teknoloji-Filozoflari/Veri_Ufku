import os
import subprocess
import sys
import time

from PySide6.QtCore import QObject, QTimer
from PySide6.QtTest import QTest

from veri_ufku.app import create_application


def spin(app, predicate, timeout=8000):
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError("GUI condition timed out")


def test_real_qml_buttons_responsiveness_error_cancel_and_stale(tmp_path, monkeypatch):
    for variable, folder in [
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_STATE_HOME", "state"),
        ("XDG_CACHE_HOME", "cache"),
    ]:
        monkeypatch.setenv(variable, str(tmp_path / folder))
    app, window, bridge = create_application()
    manager = bridge.session.manager
    try:
        cpu = window.findChild(QObject, "cpuButton")
        assert cpu.property("text") == "CPU denemesini başlat"
        ticks = []
        timer = QTimer()
        timer.setInterval(10)
        timer.timeout.connect(lambda: ticks.append(time.monotonic()))
        timer.start()
        cpu.clicked.emit()
        spin(app, lambda: bridge.active)
        spin(app, lambda: len(ticks) >= 20)
        assert manager.snapshot(bridge.job_id).state.value == "running"
        assert window.findChild(QObject, "taskNotice").property("kind") == "loading"
        cancel = window.findChild(QObject, "cancelButton")
        cancel.clicked.emit()
        spin(app, lambda: not bridge.active)
        assert bridge.stateText == "İptal edildi"
        assert manager.snapshot(bridge.job_id).result is None
        assert window.findChild(QObject, "taskNotice").property("kind") == "canceled"
        window.findChild(QObject, "failureButton").clicked.emit()
        spin(app, lambda: not bridge.active)
        assert "Hata kaydı:" in bridge.errorText
        assert window.findChild(QObject, "taskNotice").property("kind") == "error"
        assert "Sensitive sample value" not in bridge.errorText
        assert (
            "RuntimeError" in (tmp_path / "state/veri_ufku/application.log").read_text()
        )
        # Real I/O widget path plus a config change while executing.
        window.findChild(QObject, "ioButton").clicked.emit()
        spin(app, lambda: bridge.active)
        window.findChild(QObject, "contextButton").clicked.emit()
        spin(app, lambda: not bridge.active)
        assert "eski bir yapılandırmaya" in bridge.resultText
        assert "Deneme sonucu:" not in bridge.resultText
        timer.stop()
        # Close with a process running: QML rejects the first close until cleanup.
        cpu.clicked.emit()
        spin(app, lambda: bridge.active)
        window.close()
        spin(app, lambda: manager.closed and not window.isVisible())
    finally:
        manager.shutdown()
        app._veri_ufku_resources[-1]()
        window.deleteLater()
        app.processEvents()


def test_readme_entry_point_smoke(tmp_path):
    env = dict(
        os.environ,
        XDG_CONFIG_HOME=str(tmp_path / "config"),
        XDG_STATE_HOME=str(tmp_path / "state"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        QT_QPA_PLATFORM="offscreen",
    )
    result = subprocess.run(
        [sys.executable, "-m", "veri_ufku", "--smoke-test"],
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "GUI_SMOKE PASS" in result.stdout


def test_english_startup_uses_same_qml_with_local_configuration(tmp_path):
    config = tmp_path / "config/veri_ufku"
    config.mkdir(parents=True)
    (config / "settings.json").write_text('{"locale": "en"}')
    env = dict(
        os.environ,
        XDG_CONFIG_HOME=str(tmp_path / "config"),
        XDG_STATE_HOME=str(tmp_path / "state"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
    )
    source = (
        "from veri_ufku.app import create_application; "
        "from PySide6.QtCore import QObject; "
        "app, window, bridge = create_application(); "
        'print(window.findChild(QObject,"cpuButton").property("text")); '
        "bridge.session.manager.shutdown(); app._veri_ufku_resources[-1]()"
    )
    completed = subprocess.run(
        [sys.executable, "-c", source],
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "Run CPU test"


def test_bad_configuration_is_visible_and_never_logged_verbatim(tmp_path):
    config = tmp_path / "config/veri_ufku"
    config.mkdir(parents=True)
    (config / "settings.json").write_text('{"credential": "private-fixture-value"}')
    env = dict(
        os.environ,
        XDG_CONFIG_HOME=str(tmp_path / "config"),
        XDG_STATE_HOME=str(tmp_path / "state"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
    )
    source = (
        "from veri_ufku.app import create_application; "
        "from PySide6.QtCore import QObject; "
        "app, window, bridge = create_application(); "
        "assert bridge is None; "
        'print(window.findChild(QObject,"errorLabel").property("text")); '
        "app._veri_ufku_resources[-1]()"
    )
    completed = subprocess.run(
        [sys.executable, "-c", source],
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Yapılandırma geçersiz" in completed.stdout
    log = (tmp_path / "state/veri_ufku/application.log").read_text()
    assert "startup_failed" in log
    assert "private-fixture-value" not in log + completed.stdout + completed.stderr


def test_phase02_keyboard_preferences_and_view_preserve_session(tmp_path, monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtQuick import QQuickItem

    for name in ("CONFIG", "STATE", "CACHE"):
        monkeypatch.setenv(f"XDG_{name}_HOME", str(tmp_path / name.lower()))
    app, window, bridge = create_application()
    preferences = app._veri_ufku_resources[-2]
    try:
        spin(app, lambda: not window.grabWindow().isNull())
        binding = bridge.session.binding
        bridge.start("demo.io")
        job_id = bridge.job_id
        theme = window.findChild(QQuickItem, "themePicker")
        theme.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        QTest.keyClick(window, Qt.Key.Key_End)
        QTest.keyClick(window, Qt.Key.Key_Return)
        spin(app, lambda: preferences.theme == "dark")
        view = window.findChild(QQuickItem, "viewPicker")
        view.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        QTest.keyClick(window, Qt.Key.Key_End)
        QTest.keyClick(window, Qt.Key.Key_Return)
        spin(app, lambda: preferences.view == "advanced")
        assert window.property("advanced")
        assert window.findChild(QQuickItem, "technicalSettings").isVisible()
        assert bridge.session.binding == binding
        assert bridge.job_id == job_id
        spin(app, lambda: not bridge.active)
        result = bridge.resultText
        preferences.setView("beginner")
        app.processEvents()
        assert not window.findChild(QQuickItem, "technicalSettings").isVisible()
        assert bridge.resultText == result
        assert window.findChild(QQuickItem, "resultLabel").isVisible()
        assert not window.findChild(QQuickItem, "openFileButton").isEnabled()
        assert not window.findChild(QQuickItem, "sampleButton").isEnabled()
        # Preferences survive a new process and select the same QML presentation.
        source = (
            "from veri_ufku.app import create_application; "
            "app,w,b=create_application(); "
            "assert w.property('darkTheme'); assert not w.property('advanced'); "
            "b.session.manager.shutdown();app._veri_ufku_resources[-1]()"
        )
        completed = subprocess.run(
            [sys.executable, "-c", source],
            env=os.environ.copy(),
            text=True,
            capture_output=True,
            timeout=15,
        )
        assert completed.returncode == 0, completed.stderr
    finally:
        bridge.session.manager.shutdown()
        app._veri_ufku_resources[-1]()
        window.deleteLater()
        app.processEvents()


def visual_item(item, name):
    if item.objectName() == name:
        return item
    for child in item.childItems():
        found = visual_item(child, name)
        if found:
            return found
    return None


def test_phase02_resize_help_navigation_and_system_theme(tmp_path, monkeypatch):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtQuick import QQuickItem

    for name in ("CONFIG", "STATE", "CACHE"):
        monkeypatch.setenv(f"XDG_{name}_HOME", str(tmp_path / name.lower()))
    app, window, bridge = create_application()
    preferences = app._veri_ufku_resources[-2]
    from PySide6.QtGui import QColor, QPalette

    original_palette = app.palette()
    try:
        spin(app, lambda: not window.grabWindow().isNull())
        for width, height, scale in [
            (720, 560, 1.0),
            (1366, 900, 1.0),
            (720, 560, 2.0),
        ]:
            window.setWidth(width)
            window.setHeight(height)
            preferences.setTextScale(scale)
            app.processEvents()
            QTest.qWait(60)
            workspace = window.findChild(QQuickItem, "workspace")
            assert workspace.width() >= 320
            assert workspace.height() >= 200
            help_button = window.findChild(QQuickItem, "helpButton")
            point = help_button.mapToScene(
                QPointF(help_button.width() / 2, help_button.height() / 2)
            )
            assert 0 <= point.x() <= window.width()
            assert 0 <= point.y() <= window.height()
            QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=point.toPoint())
            spin(app, lambda: window.property("infoOpen"))
            QTest.keyClick(window, Qt.Key.Key_Escape)
            spin(app, lambda: not window.property("infoOpen"))
            assert help_button.hasActiveFocus()
        preferences.setTextScale(1.0)
        preferences.setTheme("system")
        # Offscreen has no OS color scheme; exercise the real palette fallback.
        assert app.styleHints().colorScheme() == Qt.ColorScheme.Unknown
        palette = QPalette(original_palette)
        palette.setColor(QPalette.ColorRole.Window, QColor("#111827"))
        app.setPalette(palette)
        spin(app, lambda: window.property("darkTheme"))
        palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
        app.setPalette(palette)
        spin(app, lambda: not window.property("darkTheme"))
        first = visual_item(window.contentItem(), "nav0")
        first.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Tab)
        assert visual_item(window.contentItem(), "nav1").hasActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Tab, Qt.KeyboardModifier.ShiftModifier)
        assert first.hasActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Down)
        QTest.keyClick(window, Qt.Key.Key_Space)
        spin(app, lambda: window.property("selectedSection") == 1)
        notice = window.findChild(QQuickItem, "availabilityNotice")
        assert notice.isVisible()
        assert notice.property("heading") == "Henüz mevcut değil"
        QTest.keyClick(window, Qt.Key.Key_1, Qt.KeyboardModifier.ControlModifier)
        spin(app, lambda: window.property("selectedSection") == 0)
        # A keyboard-focused control below the fold is brought into view.
        close = window.findChild(QQuickItem, "closeButton")
        close.forceActiveFocus()
        spin(
            app,
            lambda: (
                0 <= close.mapToScene(QPointF(0, 0)).y()
                and close.mapToScene(QPointF(0, close.height())).y() <= window.height()
            ),
        )
    finally:
        app.setPalette(original_palette)
        bridge.session.manager.shutdown()
        app._veri_ufku_resources[-1]()
        window.deleteLater()
        app.processEvents()
