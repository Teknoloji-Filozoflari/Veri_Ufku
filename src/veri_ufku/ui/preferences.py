"""Presentation preferences, stored independently of dataset and job settings."""

import json
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QFileDevice,
    QIODevice,
    QObject,
    QSaveFile,
    Signal,
    Slot,
)

from veri_ufku.ui.controller import tr


class PresentationPreferences(QObject):
    changed = Signal()
    errorChanged = Signal()

    def __init__(self, config_path: Path, parent=None):
        super().__init__(parent)
        self.path = config_path / "ui-preferences.json"
        self._theme = "system"
        self._view = "beginner"
        self._scale = 1.0
        self._error = ""
        self._writable = True
        try:
            if self.path.exists():
                if self.path.stat().st_size > 4096:
                    raise ValueError("Preferences too large")
                data = json.loads(self.path.read_text())
                if not isinstance(data, dict) or set(data) != {
                    "schema_version",
                    "theme",
                    "view",
                    "text_scale",
                }:
                    raise ValueError("Unsupported preferences")
                if (
                    type(data["schema_version"]) is not int
                    or data["schema_version"] != 1
                    or data["theme"] not in {"light", "dark", "system"}
                    or data["view"] not in {"beginner", "advanced"}
                    or type(data["text_scale"]) not in {int, float}
                    or data["text_scale"] not in {1.0, 1.25, 1.5, 2.0}
                ):
                    raise ValueError("Invalid preferences")
                self._theme, self._view, self._scale = (
                    data["theme"],
                    data["view"],
                    data["text_scale"],
                )
        except (OSError, ValueError, TypeError):
            self._writable = False
            self._error = tr(
                "Display preferences could not be read. The existing file was preserved."
            )

    @Property(str, notify=changed)
    def theme(self):
        return self._theme

    @Property(str, notify=changed)
    def view(self):
        return self._view

    @Property(float, notify=changed)
    def textScale(self):
        return self._scale

    @Property(str, notify=errorChanged)
    def errorText(self):
        return self._error

    def _save(self, theme, view, scale):
        if not self._writable:
            return
        data = json.dumps(
            {"schema_version": 1, "theme": theme, "view": view, "text_scale": scale}
        ).encode()
        file = QSaveFile(str(self.path))
        file.setDirectWriteFallback(False)
        if not file.open(QIODevice.OpenModeFlag.WriteOnly):
            self._save_failed()
            return
        if not file.setPermissions(
            QFileDevice.Permission.ReadOwner | QFileDevice.Permission.WriteOwner
        ):
            file.cancelWriting()
            self._save_failed()
            return
        # QSaveFile publishes by atomic rename; failure preserves the prior file.
        if file.write(data) != len(data):
            file.cancelWriting()
            self._save_failed()
            return
        if not file.commit():
            self._save_failed()
            return
        self._theme, self._view, self._scale = theme, view, scale
        self._error = ""
        self.changed.emit()
        self.errorChanged.emit()

    def _save_failed(self):
        self._error = tr(
            "Display preferences could not be saved. Check configuration folder permissions."
        )
        self.errorChanged.emit()

    @Slot(str)
    def setTheme(self, value):
        if value in {"light", "dark", "system"}:
            self._save(value, self._view, self._scale)

    @Slot(str)
    def setView(self, value):
        if value in {"beginner", "advanced"}:
            self._save(self._theme, value, self._scale)

    @Slot(float)
    def setTextScale(self, value):
        if value in {1.0, 1.25, 1.5, 2.0}:
            self._save(self._theme, self._view, value)
