"""Separate chronological path; bounded UI and durable final-test reveal."""

import copy
import json
import multiprocessing as mp
import os
import tempfile
import time

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.jobs.admission import start_controller
from veri_ufku.modeling.time_series_contracts import TimeSeriesSpec
from veri_ufku.modeling.worker import time_series_entry
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.time_series_store import check_history, finish, load, reserve
from veri_ufku.ui.preparation import PreparationController


class TimeSeriesController(PreparationController):
    timeSeriesChanged = Signal()
    restoreRequested = Signal(str)
    selectTemporal = Signal(str)
    selectSignal = Signal(str)

    def __init__(self, *args):
        super().__init__(*args)
        self.changed.connect(self.timeSeriesChanged)
        self.record_id = ""
        self.action = None
        self.test_use_id = None
        self.final_development = None
        self.pending_spec = None
        self.pending_result = None
        self._message = (
            "Zaman serisi: tarih sırası, ayrı gruplar ve gelecekte saklı final test."
        )

    savedRuns = Property(
        "QVariantList",
        lambda self: [
            dict(
                id=r["id"],
                label=r["time_series"]["mode"]
                + " · "
                + r["time_series"]["dataset_version"][-8:],
            )
            for r in self.projects.draft["results"]
            if "time_series" in r
        ],
        notify=timeSeriesChanged,
    )

    def display_report(self):
        if not self.result:
            return {}
        value = {k: v for k, v in self.result.items() if k != "groups"}
        value["groups"] = [
            {
                k: v
                for k, v in g.items()
                if k not in ("train_row_ids", "test_row_ids", "folds")
            }
            for g in self.result["groups"]
        ]
        return value

    @Slot(result="QVariantList")
    def temporalMethods(self):
        from veri_ufku.domain.capabilities import CAPABILITIES

        return [
            dict(id=c.capability_id.removeprefix("model.temporal."), label=c.method)
            for c in CAPABILITIES.values()
            if c.capability_id.startswith("model.temporal.")
        ]

    @Slot(result="QVariantList")
    def signalMethods(self):
        from veri_ufku.domain.capabilities import CAPABILITIES

        return [
            dict(id=c.capability_id.removeprefix("model.signal."), label=c.method)
            for c in CAPABILITIES.values()
            if c.capability_id.startswith("model.signal.")
        ]

    report = Property("QVariantMap", display_report, notify=timeSeriesChanged)

    def selected_source(self):
        return self.data.dataset()

    def current_binding(self):
        return (
            str(self.projects.store.root) if self.projects.store else "",
            (self.data.dataset() or {}).get("version_id"),
            self.revision,
        )

    @Slot(str)
    def create(self, value):
        if self.busy or self.projects.busy:
            return self.fail(ProjectError("Devam eden işi bekleyin veya iptal edin."))
        if not self.final_development:
            self.invalidate()
        try:
            d = self.data.dataset()
            if not d:
                raise ProjectError("Önce veri içe aktarın.")
            check_history(self.projects.draft, d["version_id"])
            spec = TimeSeriesSpec.from_dict(json.loads(value))
            spec.validate(d["import_metadata"]["columns"])
            fp = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]
            request = dict(
                path=str(self.projects.store.path(d["snapshot_uri"])).replace(
                    "/proc/self/", f"/proc/{os.getpid()}/", 1
                ),
                fingerprint={k: fp[k] for k in ("size", "sha256")},
                columns=copy.deepcopy(d["import_metadata"]["columns"]),
                semantic_metadata=copy.deepcopy(d.get("semantic_metadata", {})),
                row_count=d["import_metadata"]["row_count"],
                version_id=d["version_id"],
                snapshot_uri=d["snapshot_uri"],
                source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
                config_revision=self.revision,
            )
            request["mode"] = "final" if self.final_development else "development"
            request["development"] = copy.deepcopy(self.final_development)
            self.cache.mkdir(parents=True, exist_ok=True)
            self.workspace = tempfile.mkdtemp(prefix="time-series-", dir=self.cache)
            ctx = mp.get_context("spawn")
            self.cancel_event = ctx.Event()
            self.connection, sender = ctx.Pipe(duplex=False)
            self.process = ctx.Process(
                target=time_series_entry,
                args=(
                    request,
                    spec.data(),
                    self.workspace,
                    self.cancel_event,
                    sender,
                    self.budget,
                ),
            )
            self.binding = self.current_binding()
            self.started = time.monotonic()
            self.cancel_time = None
            if not start_controller(self, sender):
                return
            sender.close()
            self.projects.dataset_active = True
            self._error = ""
            self._message = (
                "Geçmişten geleceğe doğrulama ayrı süreçte çalışıyor; gruplar ayrıdır."
            )
            self.projects.changed.emit()
            self.changed.emit()
        except (ValueError, TypeError, KeyError, OSError) as error:
            if self.process is not None and self.process.pid is None:
                self.release()
            self.finish_aborted("failed")
            self.fail(error)

    @Slot(str)
    def openSaved(self, ident):
        if self.busy or self.projects.busy:
            return
        try:
            record = next(
                r
                for r in self.projects.draft["results"]
                if r["id"] == ident and "time_series" in r
            )
            # Artifact I/O stays off the GUI thread.
            self.action = "open"
            self.loading_id = ident
            self.future = self.projects.executor.submit(
                load, self.projects.store, copy.deepcopy(record)
            )
            self.projects.dataset_active = True
            self._error = ""
            self.projects.changed.emit()
            self.changed.emit()
        except (ValueError, KeyError, StopIteration) as error:
            self.fail(error)

    def poll(self):
        if self.future:
            if not self.future.done():
                return
            future, self.future = self.future, None
            try:
                if self.action == "reserve":
                    state, self.test_use_id = future.result()
                    self.projects.draft = state
                    self.projects.saved = copy.deepcopy(state)
                    self.projects.dataset_active = False
                    self.create(self.pending_spec)
                    return
                if self.action == "open":
                    value = future.result()
                    self.result = value
                    self.revision = value.get("config_revision", self.revision)
                    self.record_id = self.loading_id
                    self.restoreRequested.emit(json.dumps(value["spec"]))
                    self.result_binding = (
                        str(self.projects.store.root),
                        value["dataset_version"],
                        self.revision,
                    )
                    self._message = "Kayıtlı sonuç açıldı; veri sürümünü ve fit kapsamını inceleyin."
                else:
                    state, item = future.result()
                    self.projects.draft = state
                    self.projects.saved = copy.deepcopy(state)
                    if self.action == "publish":
                        self.result = dict(
                            item["time_series"],
                            groups=self.pending_result["groups"],
                            worker_pid=self.pending_result["worker_pid"],
                            **(
                                {
                                    "advanced": copy.deepcopy(
                                        self.pending_result["advanced"]
                                    )
                                }
                                if self.pending_result.get("advanced")
                                else {}
                            ),
                        )
                        self.result_binding = self.binding
                        self.record_id = item["id"]
                        self._message = "Zaman serisi hesabı ve geçmiş/final RowId ayrımı projeye kaydedildi."
                    else:
                        self._message = "Final test denemesi kaydedildi; tamamlanmamış sonuç başarılı sayılmaz."
            except (ValueError, OSError, StopIteration, KeyError) as error:
                self.fail(error)
            self.pending_result = None
            self.test_use_id = None
            self.final_development = None
            self.release()
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
            self._message = "İptal edildi; önceki sonuç/veri korundu."
            self.finish_aborted("canceled")
            self.projects.changed.emit()
            self.changed.emit()
            return
        for _ in range(30):
            if not self.connection.poll():
                break
            try:
                kind, value = self.connection.recv()
            except EOFError:
                break
            if kind == "progress":
                self._message = value.phase
                self.changed.emit()
                continue
            valid = self.binding == self.current_binding()
            canceled = self.cancel_event.is_set()
            if canceled or kind == "canceled":
                self._message = "İptal edildi; önceki sonuç/veri korundu."
            elif not valid:
                self._message = "Eski veri/ayar sonucu güncel ekrana bağlanmadı."
            elif kind == "error":
                self._error = value
            elif kind == "result":
                workspace, self.workspace = self.workspace, None
                self.release()
                self.workspace = workspace
                self.action = "publish"
                self.pending_result = value
                self.future = self.projects.executor.submit(
                    finish,
                    self.projects.store,
                    copy.deepcopy(self.projects.draft),
                    value,
                    self.test_use_id,
                )
                self.projects.dataset_active = True
                self._message = "Sonuç ve RowId üyelikleri atomik kaydediliyor…"
                self.projects.changed.emit()
                self.changed.emit()
                return
            self.release()
            self.finish_aborted(
                "canceled"
                if canceled or kind == "canceled"
                else "stale"
                if not valid
                else "failed"
            )
            self.projects.changed.emit()
            self.changed.emit()
            return
        if self.process and not self.process.is_alive() and not self.connection.poll():
            self.release()
            self.finish_aborted("failed")
            self._error = "Worker beklenmedik kapandı; tamamlanmış sonuç kaydedilmedi."
            self.projects.changed.emit()
            self.changed.emit()

    @Slot()
    def finalTest(self):
        if (
            self.busy
            or self.projects.busy
            or not self.current
            or self.result["mode"] != "development"
            or self.result.get("advanced", {}).get("spec", {}).get("task", "forecast")
            != "forecast"
        ):
            return self.fail(
                ProjectError("Önce güncel geliştirme koşusunu hesaplayın.")
            )
        self.final_development = copy.deepcopy(self.result)
        self.pending_spec = json.dumps(self.result["spec"])
        self.action = "reserve"
        self.future = self.projects.executor.submit(
            reserve,
            self.projects.store,
            copy.deepcopy(self.projects.draft),
            self.final_development,
        )
        self.projects.dataset_active = True
        self._message = "Final test açılmadan kullanım kalıcı kaydediliyor…"
        self.projects.changed.emit()
        self.changed.emit()

    def finish_aborted(self, status):
        if self.test_use_id:
            self.action = "finish"
            self.future = self.projects.executor.submit(
                finish,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                None,
                self.test_use_id,
                status,
            )
            self.projects.dataset_active = True
        else:
            self.final_development = None

    def shutdown(self):
        self.timer.stop()
        if self.future:
            try:
                self.future.result()
            except (ValueError, OSError):
                pass
            self.future = None
        self.release()
