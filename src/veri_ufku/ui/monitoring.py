"""Explicit local monitoring actions. Opening a project never scores or serves API."""

import copy
import multiprocessing as mp
import shutil
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from veri_ufku.domain.json import parse
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.admission import start_controller
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.monitor_service import worker
from veri_ufku.storage import monitor_store as storage
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.ui.projects import project_error_text


class MonitoringController(QObject):
    changed = Signal()
    storage = storage
    worker = staticmethod(worker)
    result_kind = "monitoring"

    @staticmethod
    def public_report(value):
        from veri_ufku.modeling.monitoring import public_report

        return public_report(value)

    def __init__(self, projects, cache, budget, parent=None):
        super().__init__(parent)
        self.projects, self.cache, self.budget = projects, Path(cache), budget
        self.process = self.connection = self.future = self.workspace = None
        self.result = {}
        self._error = ""
        self.cancel_time = None
        self._pending_report = None
        self._root = None
        self._commit = None
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        projects.changed.connect(self.project_changed)

    busy = Property(
        bool, lambda s: s.process is not None or s.future is not None, notify=changed
    )
    errorText = Property(str, lambda s: s._error, notify=changed)
    report = Property("QVariantMap", lambda s: s.result, notify=changed)
    datasets = Property(
        "QVariantList",
        lambda s: [
            dict(
                id=d["version_id"],
                label=d["version_id"],
                columns=d.get("import_metadata", {}).get("columns", []),
            )
            for d in s.projects.draft["datasets"]
        ],
        notify=changed,
    )
    models = Property(
        "QVariantList",
        lambda s: [
            dict(id=k, label=v["run_id"])
            for k, v in s.storage.models(s.projects.draft).items()
        ],
        notify=changed,
    )
    currentRoute = Property(
        "QVariantMap", lambda s: s.storage.route(s.projects.draft) or {}, notify=changed
    )
    saved = Property(
        "QVariantList",
        lambda s: [
            dict(id=r["id"], label=r["monitoring"]["run_id"])
            for r in s.projects.draft["results"]
            if "monitoring" in r
        ],
        notify=changed,
    )

    @Slot()
    def project_changed(self):
        root = str(self.projects.store.root) if self.projects.store else None
        if root != self._root and not self.busy:
            self.result = {}
            self._root = root
        self.changed.emit()

    def ready(self):
        if (
            not self.projects.store
            or self.projects.readOnly
            or self.projects.busy
            or self.busy
            or self.projects.draft != self.projects.store.state
        ):
            raise ProjectError(
                "Kaydedilmiş, yazılabilir ve boşta proje gerekli; önce Projeyi kaydet."
            )

    @Slot(str)
    def run(self, text):
        try:
            self.ready()
            if len(text.encode()) > 65536:
                raise ProjectError("Recipe64KiB sınırı.")
            spec = parse(text)
            request = self.storage.request_for(
                self.projects.store, self.projects.draft, spec
            )
            self._root = str(self.projects.store.root)
            self._commit = self.projects.store.commit_id
            self.cache.mkdir(parents=True, exist_ok=True)
            self.workspace = tempfile.mkdtemp(prefix="monitor-", dir=self.cache)
            ctx = mp.get_context("spawn")
            self.cancel_event = ctx.Event()
            self.connection, sender = ctx.Pipe(False)
            self.process = ctx.Process(
                target=self.worker,
                args=(
                    request,
                    spec,
                    self.workspace,
                    self.cancel_event,
                    sender,
                    self.budget,
                ),
            )
            self.cancel_time = None
            self.started = time.monotonic()
            self._error = ""
            if not start_controller(self, sender):
                return
            sender.close()
            self.projects.dataset_active = True
            self.changed.emit()
            self.projects.changed.emit()
        except (ValueError, TypeError, KeyError, OSError) as e:
            self.fail(e)

    def fail(self, e):
        self._error = project_error_text(e)
        self.changed.emit()

    @Slot()
    def cancel(self):
        if self.process or self.future is not None and self._pending_report is not None:
            self.cancel_event.set()
            self.cancel_time = self.cancel_time or time.monotonic()
            self.changed.emit()

    @Slot(str, bool)
    def selectChampion(self, record_id, rollback):
        try:
            self.ready()
            self._error = ""
            self.future = self.projects.executor.submit(
                self.storage.activate,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                record_id,
                "rollback" if rollback else "manual_selection",
                rollback,
            )
            self.projects.dataset_active = True
            self.projects.changed.emit()
            self.changed.emit()
        except (ValueError, TypeError, KeyError, OSError) as e:
            self.fail(e)

    @Slot(str)
    def openReport(self, ident):
        try:
            self.ready()
            record = next(
                r
                for r in self.projects.draft["results"]
                if r["id"] == ident and self.result_kind in r
            )
            self.result = self.public_report(
                self.storage.load(self.projects.store, record)
            )
            self._error = ""
            self.changed.emit()
        except (ValueError, TypeError, KeyError, OSError, StopIteration) as e:
            self.fail(e)

    def release(self):
        if self.process:
            self.process.join(0.1)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(2)
            self.process.close()
        if self.connection:
            self.connection.close()
        self.process = self.connection = None
        if self.workspace:
            shutil.rmtree(self.workspace, ignore_errors=True)
        self.workspace = None

    def poll(self):
        if self.future:
            if not self.future.done():
                return
            future, self.future = self.future, None
            try:
                self.projects.draft = future.result()
                self.projects.saved = copy.deepcopy(self.projects.draft)
                if self._pending_report is not None:
                    self.result = self._pending_report
            except Canceled:
                self._error = (
                    "Monitoring yayın öncesi iptal edildi; önceki kayıt korundu."
                )
            except (ValueError, TypeError, KeyError, OSError) as e:
                self.fail(e)
            self._pending_report = None
            self.projects.dataset_active = False
            self.projects.changed.emit()
            self.changed.emit()
            return
        if not self.process:
            return
        if time.monotonic() - self.started > self.budget.max_wall_seconds:
            self.cancel()
        if (
            self.cancel_time
            and time.monotonic() - self.cancel_time > self.budget.cancel_grace_ms / 1000
        ):
            self.release()
            self._error = "Monitoring iptal edildi; önceki sonuç korundu."
        elif self.connection.poll():
            try:
                kind, value = self.connection.recv()
            except EOFError:
                kind, value = "error", "Monitoring worker eksik sonuçla kapandı."
            canceled = self.cancel_event.is_set()
            self.release()
            if canceled or kind == "canceled":
                self._error = "Monitoring iptal edildi; önceki sonuç korundu."
            elif kind == "error":
                self._error = value
            elif (
                not self.projects.store or self.projects.store.commit_id != self._commit
            ):
                self._error = "Proje değişti; eski sonuç yayınlanmadı."
            else:
                self._pending_report = self.public_report(value)
                self.future = self.projects.executor.submit(
                    self.storage.publish,
                    self.projects.store,
                    copy.deepcopy(self.projects.draft),
                    value,
                    Control(cancel=self.cancel_event, budget=self.budget),
                )
                return
        elif not self.process.is_alive():
            self.release()
            self._error = "Monitoring worker durdu; eksik sonuç başarılı sayılmaz."
        else:
            return
        self.projects.dataset_active = False
        self.projects.changed.emit()
        self.changed.emit()

    def shutdown(self):
        self.timer.stop()
        self.cancel()
        self.release()
        if self.future:
            try:
                self.future.result()
            except (Canceled, ValueError, TypeError, KeyError, OSError):
                pass
            self.future = None
