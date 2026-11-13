"""Durable finding notebook surface for every stage.

The notebook is a permanent panel on the bottom drawer. Findings are written
into the open project's draft and persisted through the existing ProjectStore
transaction; this controller never writes a file of its own and never changes
the dataset.
"""

from PySide6.QtCore import Property, QObject, Signal, Slot

from veri_ufku.storage import finding_store as storage
from veri_ufku.storage.project_model import ProjectError


class FindingsController(QObject):
    changed = Signal()
    drawerRequested = Signal(str)

    def __init__(self, projects, data, parent=None):
        super().__init__(parent)
        self.projects = projects
        self.data = data
        self._error = ""
        self._stage = storage.STAGES[0]
        projects.changed.connect(self.changed)

    def _current_version(self):
        """The dataset version the workspace is currently showing."""
        try:
            dataset = self.data.dataset()
        except (AttributeError, KeyError, TypeError):
            dataset = None
        return (dataset or {}).get("version_id")

    # --- read surface -----------------------------------------------------
    def _rows(self):
        rows = storage.rows(self.projects.draft)
        current = self._current_version()
        for row in rows:
            versions = row["dataset_version_ids"]
            if current and versions and current not in versions:
                row["stale"] = True
                row["stale_reason"] = "Çalışma alanındaki veri sürümü değişti."
        return rows

    findings = Property("QVariantList", lambda s: s._rows(), notify=changed)
    count = Property(int, lambda s: len(s._rows()), notify=changed)
    staleCount = Property(
        int, lambda s: sum(1 for row in s._rows() if row["stale"]), notify=changed
    )
    stages = Property(
        "QVariantList",
        lambda s: [
            dict(id=stage, label=storage.STAGE_LABELS[stage])
            for stage in storage.STAGES
        ],
        constant=True,
    )
    currentStage = Property(str, lambda s: s._stage, notify=changed)
    errorText = Property(str, lambda s: s._error, notify=changed)
    summaryText = Property(
        str,
        lambda s: (
            f"{len(s._rows())} bulgu"
            + (
                f" · {sum(1 for row in s._rows() if row['stale'])} güncel değil"
                if any(row["stale"] for row in s._rows())
                else ""
            )
        ),
        notify=changed,
    )
    available = Property(bool, lambda s: s.projects.opened, notify=changed)

    @Slot(str, result=str)
    def preview(self, stage):
        """Computed result preview for a stage; never invented by hand."""
        if stage not in storage.STAGES:
            return storage.NOT_RECORDED
        summary = storage._record_summary(
            self.projects.draft, stage, self._current_version()
        )
        return summary["text"]

    @Slot(str, result=str)
    def stageLabel(self, stage):
        return storage.STAGE_LABELS.get(stage, stage)

    # --- write surface ----------------------------------------------------
    def _require_project(self):
        if not self.projects.opened:
            raise ProjectError("Bulgu eklemek için önce bir proje açın.")
        if self.projects.readOnly:
            raise ProjectError("Bu proje salt okunur; bulgu eklenemez.")

    @Slot(str, str, str, str, str, result=bool)
    def add(self, stage, question, method, interpretation="", decision=""):
        """Create a finding from the stage's current recorded run."""
        try:
            self._require_project()
            draft = self.projects.draft
            finding = storage.create(
                draft,
                stage,
                question,
                method,
                interpretation=interpretation,
                decision=decision,
                version=self._current_version(),
            )
            storage.append(draft, finding)
            self._error = ""
            self.projects.changed.emit()
            self.projects.save()
            self.changed.emit()
            return True
        except (ProjectError, ValueError, TypeError, KeyError) as error:
            self._error = str(error)
            self.changed.emit()
            return False

    @Slot(str, result=bool)
    def remove(self, ident):
        """Remove a finding after the user's explicit decision."""
        try:
            self._require_project()
            draft = self.projects.draft
            storage.remove(draft, ident)
            self._error = ""
            self.projects.changed.emit()
            self.projects.save()
            self.changed.emit()
            return True
        except (ProjectError, ValueError, TypeError, KeyError) as error:
            self._error = str(error)
            self.changed.emit()
            return False

    @Slot(str)
    def openFor(self, stage):
        """Open the notebook for a stage and ask the drawer to come forward."""
        if stage in storage.STAGES:
            self._stage = stage
        self.changed.emit()
        self.drawerRequested.emit(self._stage)
