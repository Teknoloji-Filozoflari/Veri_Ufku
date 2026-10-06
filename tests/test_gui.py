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
        cancel = window.findChild(QObject, "cancelButton")
        cancel.clicked.emit()
        spin(app, lambda: not bridge.active)
        assert bridge.stateText == "İptal edildi"
        assert manager.snapshot(bridge.job_id).result is None
        window.findChild(QObject, "failureButton").clicked.emit()
        spin(app, lambda: not bridge.active)
        assert "Hata kaydı:" in bridge.errorText
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
