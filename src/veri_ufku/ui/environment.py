"""Explicit environment inventory and comparison; never install or import user code."""

import json
import multiprocessing as mp
import shutil
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from veri_ufku.jobs.admission import start_controller
from veri_ufku.packaging.environment import lock_profile
from veri_ufku.packaging.environment_worker import worker


class EnvironmentController(QObject):
    changed = Signal()

    def __init__(self, projects, cache, budget, parent=None):
        super().__init__(parent)
        self.projects, self.cache, self.budget = projects, Path(cache), budget
        self.process = self.connection = self.workspace = None
        self.result = {}
        self.inventory = {}
        self._error = ""
        self.cancel_time = None
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    busy = Property(bool, lambda s: s.process is not None, notify=changed)
    reportText = Property(
        str,
        lambda s: json.dumps(s.inventory, ensure_ascii=False, indent=2),
        notify=changed,
    )
    outputText = Property(
        str,
        lambda s: json.dumps(s.result, ensure_ascii=False, indent=2),
        notify=changed,
    )
    errorText = Property(str, lambda s: s._error, notify=changed)

    def run(self, request):
        if self.busy or self.projects.busy:
            self._error = "Ortam işlemi için uygulamanın boşta olması gerekli."
            self.changed.emit()
            return
        self.cache.mkdir(parents=True, exist_ok=True)
        self.workspace = tempfile.mkdtemp(prefix="environment-", dir=self.cache)
        ctx = mp.get_context("spawn")
        self.cancel_event = ctx.Event()
        self.connection, sender = ctx.Pipe(False)
        self.process = ctx.Process(
            target=worker,
            args=(request, self.workspace, self.cancel_event, sender, self.budget),
        )
        self.started = time.monotonic()
        self.cancel_time = None
        self._error = ""
        if not start_controller(self, sender):
            return
        sender.close()
        self.changed.emit()

    @Slot()
    def refresh(self):
        allowed = {n for p in lock_profile()["groups"].values() for n in p} | {
            "python",
            "sklearn",
            "numpy",
            "torch",
            "statsmodels",
        }
        artifacts = []
        for r in self.projects.draft["results"][-500:]:
            value = next(
                (
                    r[k]
                    for k in (
                        "baseline",
                        "neural",
                        "time_series",
                        "plugin_result",
                        "analysis",
                    )
                    if isinstance(r.get(k), dict)
                ),
                {},
            )
            env = value.get("environment", {})
            artifacts.append(
                dict(
                    id=r["id"],
                    versions={
                        k: v
                        for k, v in env.items()
                        if k in allowed and isinstance(v, str)
                    }
                    if isinstance(env, dict)
                    else {},
                )
            )
        self.run(dict(action="scan", artifacts=artifacts))

    @Slot(str, bool)
    def exportProfile(self, path, approved):
        if approved is not True or not self.inventory:
            self._error = "Önce yerel raporu oluşturup export kapsamını onaylayın."
            self.changed.emit()
            return
        self.run(
            dict(
                action="export",
                report=self.inventory,
                destination=path,
                project_root=str(self.projects.store.root)
                if self.projects.store
                else str(self.cache),
            )
        )

    @Slot(str, bool)
    def importProfile(self, path, approved):
        self.run(dict(action="import", path=path, approved=approved))

    @Slot(str, str, str, bool)
    def prepareUpdate(self, path, expected, current, approved):
        self.run(
            dict(
                action="update-plan",
                path=path,
                expected_sha256=expected,
                current_commit=current,
                approved=approved,
            )
        )

    @Slot(str, bool)
    def inspectCache(self, path, approved):
        self.run(dict(action="cache", path=path, approved=approved))

    @Slot()
    def cancel(self):
        if self.process:
            self.cancel_event.set()
            self.cancel_time = self.cancel_time or time.monotonic()
            self.changed.emit()

    def release(self):
        if self.process:
            self.process.join(0.1)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(2)
            self.process.close()
        if self.connection:
            self.connection.close()
        if self.workspace:
            shutil.rmtree(self.workspace, ignore_errors=True)
        self.process = self.connection = self.workspace = None

    def poll(self):
        if not self.process:
            return
        if time.monotonic() - self.started > self.budget.max_wall_seconds:
            self.cancel()
        if (
            self.cancel_time
            and time.monotonic() - self.cancel_time > self.budget.cancel_grace_ms / 1000
        ):
            self.release()
            self._error = "Environment işlemi iptal edildi; önceki rapor korundu."
        elif self.connection.poll():
            try:
                kind, value = self.connection.recv()
            except EOFError:
                kind, value = (
                    "error",
                    "Environment worker eksik çıktı; başarılı sayılmadı.",
                )
            canceled = self.cancel_event.is_set()
            self.release()
            if canceled or kind == "canceled":
                self._error = "Environment işlemi iptal edildi; önceki rapor korundu."
            elif kind == "error":
                self._error = value
            else:
                self.result = value
                if value.get("action") == "scan":
                    self.inventory = value["report"]
        elif not self.process.is_alive():
            self.release()
            self._error = "Environment worker çöktü; kurulum/proje değişmedi."
        else:
            return
        self.changed.emit()

    def shutdown(self):
        self.timer.stop()
        self.cancel()
        self.release()
