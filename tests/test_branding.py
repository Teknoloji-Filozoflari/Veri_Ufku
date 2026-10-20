"""Verify packaged branding reaches Qt windows and the Linux launcher."""

import hashlib
import json

from PySide6.QtCore import QObject
from PySide6.QtGui import QImage
from test_import_gui import setup, spin, teardown

from veri_ufku.desktop import APP_ID, ASSETS, install


def test_selected_logo_and_linux_launcher(tmp_path):
    manifest = json.loads((ASSETS / "source.json").read_text())
    assert (
        hashlib.sha256((ASSETS / "logo.png").read_bytes()).hexdigest()
        == (manifest["sha256"])
    )
    paths = install(tmp_path)
    assert len(paths) == 9
    launcher = paths[-1].read_text()
    assert f"Icon={APP_ID}" in launcher
    assert 'Exec="' in launcher and '/veri-ufku"' in launcher
    for path, size in zip(paths[:-1], (16, 24, 32, 48, 64, 128, 256, 512)):
        image = QImage(str(path))
        assert not image.isNull() and image.hasAlphaChannel()
        assert image.width() == image.height() == size


def test_logo_loads_in_both_qml_windows(tmp_path, monkeypatch):
    app, window, _, _, _ = setup(tmp_path, monkeypatch)
    try:
        assert app.desktopFileName() == APP_ID
        assert not app.windowIcon().isNull() and not window.icon().isNull()
        logo = window.findChild(QObject, "applicationLogo")
        spin(app, lambda: logo.property("ready"))
        assert logo.property("width") == 36
        engine = app._veri_ufku_resources[0]
        example = engine.rootObjects()[0].findChild(QObject, "learningExampleWindow")
        assert example is not None
        assert not example.icon().isNull()
        mark = example.findChild(QObject, "exampleLogo")
        spin(app, lambda: mark.property("ready"))
    finally:
        teardown(app, window)
