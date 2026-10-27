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

from veri_ufku.config import SUPPORTED_LOCALES
from veri_ufku.ui.controller import tr

_HISTORICAL_SCALES = {1.0, 1.25, 1.5, 2.0}


class PresentationPreferences(QObject):
    changed = Signal()
    errorChanged = Signal()

    def __init__(self, config_path: Path, parent=None, locale="tr"):
        super().__init__(parent)
        self.path = config_path / "ui-preferences.json"
        self._view = "beginner"
        self._theme = "dark"
        self._text_scale = 1.0
        self._locale = locale
        self._error = ""
        self._writable = True
        normalize_scale = False
        try:
            if self.path.exists():
                if self.path.stat().st_size > 4096:
                    raise ValueError("Preferences too large")
                data = json.loads(self.path.read_text())
                if not isinstance(data, dict):
                    raise ValueError("Unsupported preferences")
                version = data.get("schema_version")
                fields = {"schema_version", "view"}
                if version in {1, 2}:
                    fields.add("theme")
                    if data.get("theme") not in {"light", "dark", "system"}:
                        raise ValueError("Invalid legacy preferences")
                if type(version) is not int or version not in {1, 2, 3, 4}:
                    raise ValueError("Unsupported preferences")
                if version == 1:
                    fields.add("text_scale")
                    if type(data.get("text_scale")) not in {int, float} or data[
                        "text_scale"
                    ] not in {1.0, 1.25, 1.5, 2.0}:
                        raise ValueError("Invalid preferences")
                if version == 4:
                    fields.update({"theme", "text_scale", "locale"})
                    if (
                        data.get("theme") not in {"dark", "light"}
                        or data.get("locale") not in SUPPORTED_LOCALES
                    ):
                        raise ValueError("Invalid display preference")
                    if (
                        type(data.get("text_scale")) not in {int, float}
                        or data["text_scale"] not in _HISTORICAL_SCALES
                    ):
                        raise ValueError("Invalid text size")
                if set(data) != fields or data["view"] not in {"beginner", "advanced"}:
                    raise ValueError("Invalid preferences")
                # Read legacy theme/size without applying them. Explicit level changes
                # publish schema 3; merely opening preserves the old file.
                self._view = data["view"]
                if version == 4:
                    self._theme = data["theme"]
                    # Text size is no longer a user option. Historical values stay valid
                    # on disk until the next save, and the running scale is always 1.
                    self._text_scale = 1.0
                    self._locale = data["locale"]
                    normalize_scale = data["text_scale"] != 1.0
        except (OSError, ValueError, TypeError):
            self._writable = False
            self._error = tr(
                "Display preferences could not be read. The existing file was preserved."
            )
        else:
            if normalize_scale:
                self._save(text_scale=1.0)

    @Property(str, notify=changed)
    def view(self):
        return self._view

    @Property(str, notify=errorChanged)
    def errorText(self):
        return self._error

    theme = Property(str, lambda self: self._theme, notify=changed)
    textScale = Property(float, lambda self: self._text_scale, notify=changed)
    locale = Property(str, lambda self: self._locale, notify=changed)

    def _save(self, view=None, theme=None, text_scale=None, locale=None):
        if not self._writable:
            return
        state = dict(
            schema_version=4,
            view=view or self._view,
            theme=theme or self._theme,
            text_scale=text_scale if text_scale is not None else self._text_scale,
            locale=locale or self._locale,
        )
        data = json.dumps(state).encode()
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
        self._view = state["view"]
        self._theme = state["theme"]
        self._text_scale = state["text_scale"]
        self._locale = state["locale"]
        self._error = ""
        self.changed.emit()
        self.errorChanged.emit()

    def _save_failed(self):
        self._error = tr(
            "Display preferences could not be saved. Check configuration folder permissions."
        )
        self.errorChanged.emit()

    @Slot(str)
    def setView(self, value):
        if value in {"beginner", "advanced"}:
            self._save(value)

    @Slot(str)
    def setTheme(self, value):
        if value in {"dark", "light"}:
            self._save(theme=value)

    @Slot(float)
    def setTextScale(self, value):
        # Larger sizes are ignored so a stored or called scale cannot grow the UI.
        if value in _HISTORICAL_SCALES and self._text_scale != 1.0:
            self._save(text_scale=1.0)

    @Slot(str)
    def setLocale(self, value):
        if value in SUPPORTED_LOCALES:
            self._save(locale=value)
