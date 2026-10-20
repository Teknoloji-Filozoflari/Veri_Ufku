"""Separate ephemeral example ProjectController; no main project reference."""

import copy
import json
import tempfile
from pathlib import Path

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.learning.lab_worker import worker
from veri_ufku.storage import learning_lab_store as storage
from veri_ufku.ui.monitoring import MonitoringController
from veri_ufku.ui.projects import ProjectController


class LearningLabController(MonitoringController):
    opened = Signal()
    labChanged = Signal()
    storage = storage
    worker = staticmethod(worker)
    result_kind = "learning_lab"
    public_report = staticmethod(storage.public_report)

    def __init__(self, learning, cache, budget, parent=None):
        self.learning = learning
        self._example_directory = None
        self._base = Path(cache)
        self._pending_start = None
        # Config stays in the disposable workspace, never in the user's recents.
        host = ProjectController(
            self._base / "unused-config", learning.exampleLibrary, parent
        )
        super().__init__(host, self._base / "jobs", budget, parent)
        self.changed.connect(self.labChanged.emit)
        self.timer.timeout.connect(self.check_start)

    saved = Property(
        "QVariantList",
        lambda s: [
            dict(
                id=r["id"],
                label=r["learning_lab"]["spec"]["lesson"]
                + " · "
                + r["learning_lab"]["run_id"],
            )
            for r in s.projects.draft["results"]
            if "learning_lab" in r
        ],
        notify=labChanged,
    )
    models = Property("QVariantList", lambda s: [], notify=labChanged)
    currentRoute = Property("QVariantMap", lambda s: {}, notify=labChanged)
    errorText = Property(
        str,
        lambda s: s._error.replace("Monitoring", "Laboratuvar"),
        notify=labChanged,
    )
    workspaceId = Property(
        str,
        lambda s: s.projects.store.manifest["project_id"] if s.projects.store else "",
        notify=labChanged,
    )
    starting = Property(
        bool,
        lambda s: s._pending_start is not None,
        notify=labChanged,
    )

    @Slot(str)
    def startLesson(self, ident):
        if ident not in self.learning.curriculum.lessons or self.busy or self.starting:
            return
        self.learning.openLesson(ident)
        if self.projects.store:
            self.opened.emit()
            return
        self._base.mkdir(parents=True, exist_ok=True)
        self._example_directory = tempfile.TemporaryDirectory(
            prefix="workspace-", dir=self._base
        )
        root = Path(self._example_directory.name)
        self.projects.config = root / "config"
        self.projects.config.mkdir()
        self.projects.draft["name"] = "Veri_Ufku · Geçici öğrenme laboratuvarı"
        self.projects.saved = copy.deepcopy(self.projects.draft)
        self._pending_start = ident
        self.projects.request("create", str(root / "project"))
        self.changed.emit()

    @Slot()
    def check_start(self):
        if self._pending_start and not self.projects.busy:
            self._pending_start = None
            if self.projects.store:
                self.opened.emit()
            else:
                self._error = self.projects.errorText
            self.changed.emit()

    @Slot(int, int)
    def calculateLesson(self, value, seed):
        if self.projects.store:
            self.run(
                json.dumps(
                    dict(lesson=self.learning.lesson["id"], value=value, seed=seed)
                )
            )

    @Slot()
    def closeView(self):
        self.cancel()

    def shutdown(self):
        super().shutdown()
        self.projects.shutdown()
        if self._example_directory:
            self._example_directory.cleanup()
            self._example_directory = None
