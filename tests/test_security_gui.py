"""Actual QML recovery preview and unchanged manual commit."""

import pytest
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown


@pytest.mark.parametrize("scale", [1, 2])
def test_recovery_dialog_describes_exact_autosave_before_explicit_load(
    tmp_path, monkeypatch, scale
):
    app, window, _, projects, _ = setup(tmp_path, monkeypatch)
    try:
        if scale == 2:
            window.setWidth(720)
            window.setHeight(560)
            app._veri_ufku_resources[-2].setTextScale(2)
        projects.setName("Sentetik kurtarma")
        projects.autosave()
        active = (projects.store.root / "ACTIVE").read_bytes()
        window.setProperty("selectedSection", 0)
        button = window.findChild(QObject, "restoreAutosaveButton")
        button.clicked.emit()
        spin(app, lambda: not projects.busy)
        dialog = window.findChild(QObject, "recoveryDialog")
        spin(app, lambda: dialog.property("visible"))
        assert dialog.property("height") <= window.height()
        text = window.findChild(QObject, "recoveryPreviewText").property("text")
        assert "Sentetik kurtarma" in text and "Manuel kayıt korunur" in text
        assert projects.recoveryPreview["commit_id"]
        assert (projects.store.root / "ACTIVE").read_bytes() == active
        dialog.reject()
        app.processEvents()
        assert projects.dirty and projects.name == "Sentetik kurtarma"
        assert (projects.store.root / "ACTIVE").read_bytes() == active
        button.clicked.emit()
        spin(app, lambda: not projects.busy)
        spin(app, lambda: dialog.property("visible"))
        dialog.accept()
        spin(app, lambda: not projects.busy)
        assert not projects.errorText and projects.name == "Sentetik kurtarma"
        assert (
            projects.dirty and (projects.store.root / "ACTIVE").read_bytes() == active
        )
        projects.request("save")
        spin(app, lambda: not projects.busy)
        assert not projects.errorText and not projects.dirty
        assert (projects.store.root / "ACTIVE").read_bytes() != active
    finally:
        teardown(app, window)
