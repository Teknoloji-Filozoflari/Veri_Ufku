"""UX V2 stage texts + first-run tour flag (separate from learning catalog schema)."""

from __future__ import annotations

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


def stages_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "learning"
        / "content"
        / "ux_v2_stages.json"
    )


def load_ux_content() -> dict:
    return json.loads(stages_path().read_text(encoding="utf-8"))


class UxContentController(QObject):
    changed = Signal()

    def __init__(self, config_path: Path, parent=None):
        super().__init__(parent)
        self._path = Path(config_path) / "ux-v2-tour.json"
        self._content = load_ux_content()
        self._tour_seen = False
        self._tour_open = False
        try:
            if self._path.is_file() and self._path.stat().st_size <= 1024:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                if (
                    isinstance(data, dict)
                    and data.get("schema_version") == 1
                    and isinstance(data.get("tour_seen"), bool)
                ):
                    self._tour_seen = data["tour_seen"]
                    self._tour_open = not self._tour_seen
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self._tour_seen = False
            self._tour_open = True

    @Property(str, notify=changed)
    def draftStatus(self):
        return self._content.get("status", "taslak")

    @Property("QVariantList", notify=changed)
    def glossary(self):
        return list(self._content.get("glossary", []))

    @Property("QVariantList", notify=changed)
    def stages(self):
        return list(self._content.get("stages", []))

    @Slot(int, result="QVariant")
    def stageAt(self, index: int):
        stages = self._content.get("stages", [])
        if 0 <= index < len(stages):
            return stages[index]
        return {}

    @Property(bool, notify=changed)
    def tourSeen(self):
        return self._tour_seen

    @Property(bool, notify=changed)
    def tourOpen(self):
        return self._tour_open

    def _save_tour(self, seen: bool):
        payload = json.dumps(
            {"schema_version": 1, "tour_seen": seen}, ensure_ascii=False
        ).encode()
        self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        file = QSaveFile(str(self._path))
        file.setDirectWriteFallback(False)
        if not file.open(QIODevice.OpenModeFlag.WriteOnly):
            return
        file.setPermissions(
            QFileDevice.Permission.ReadOwner | QFileDevice.Permission.WriteOwner
        )
        if file.write(payload) != len(payload):
            file.cancelWriting()
            return
        file.commit()

    @Slot()
    def dismissTour(self):
        self._tour_seen = True
        self._tour_open = False
        self._save_tour(True)
        self.changed.emit()

    @Slot()
    def reopenTour(self):
        self._tour_open = True
        self.changed.emit()

    @Slot()
    def closeTourKeepUnseen(self):
        """Skip for this session without writing; next launch may show again."""
        self._tour_open = False
        self.changed.emit()
