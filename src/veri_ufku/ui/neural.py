"""Tensor GUI uses the shared CPU worker, budget and atomic ProjectStore journals."""

import copy
import json
import multiprocessing as mp
import os
import tempfile
import time

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.jobs.admission import start_controller
from veri_ufku.modeling.neural_contracts import NeuralSpec
from veri_ufku.modeling.validation import ValidationSpec
from veri_ufku.modeling.worker import neural_entry, neural_predict_entry
from veri_ufku.storage.experiment_store import capture
from veri_ufku.storage.neural_store import load, publish
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.validation_store import choice, complete, prior_uses
from veri_ufku.ui.preparation import PreparationController


class NeuralController(PreparationController):
    selectNeural = Signal(str)
    neuralChanged = Signal()

    def __init__(self, data, projects, preparation, cache, budget, parent=None):
        super().__init__(data, projects, cache, budget, parent)
        self.changed.connect(self.neuralChanged)
        self.preparation = preparation
        self.active = None
        self.prediction = {}
        self.stage = None
        self.resume = None
        self._message = "CPU MLP/CNN; optional backend. Final test bu panelde kapalı; validation keşifseldir."
        preparation.changed.connect(self.changed)

    def selected_source(self):
        return (
            self.preparation.selected_source()
            if hasattr(self, "preparation")
            else super().selected_source()
        )

    ramMiB = Property(int, lambda self: self.budget.ram_bytes // 1024**2, constant=True)
    available = Property(bool, lambda self: self.backend_available(), constant=True)
    canRun = Property(
        bool,
        lambda self: bool(
            self.backend_available()
            and self.preparation.current
            and not self.preparation.result["blockers"]
            and self.projects.store
            and not self.projects.readOnly
            and not self.busy
            and not self.projects.busy
        ),
        notify=neuralChanged,
    )
    historyReport = Property(
        "QVariantMap",
        lambda self: self.summary(self.active),
        notify=neuralChanged,
    )
    predictionReport = Property(
        "QVariantMap",
        lambda self: self.prediction,
        notify=neuralChanged,
    )
    savedRuns = Property(
        "QVariantList", lambda self: self.saved(), notify=neuralChanged
    )

    def backend_available(self):
        import importlib.metadata

        try:
            return importlib.metadata.version("torch") == "2.13.0+cpu"
        except importlib.metadata.PackageNotFoundError:
            return False

    def summary(self, data):
        return {
            k: v
            for k, v in (data or {}).items()
            if k
            not in (
                "runtime",
                "model_weights",
                "preprocessing",
                "validation_predictions",
            )
        }

    def record_schema(self):
        return "NeuralRun/v1"

    def saved(self):
        latest = {}
        for r in self.projects.draft["results"]:
            if r.get("neural", {}).get("schema") == self.record_schema():
                latest[r["neural"]["training_id"]] = r
        return [
            dict(
                id=r["id"],
                label=r["neural"]["spec"]["template"]
                + " · "
                + r["neural"]["status"]
                + " · epoch "
                + str(r["neural"]["epoch"]),
            )
            for r in latest.values()
        ]

    def request_for(self, d):
        fp = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]
        return dict(
            path=str(self.projects.store.path(d["snapshot_uri"])).replace(
                "/proc/self/", f"/proc/{os.getpid()}/", 1
            ),
            fingerprint={k: fp[k] for k in ("size", "sha256")},
            columns=copy.deepcopy(d["import_metadata"]["columns"]),
            semantic_metadata=copy.deepcopy(d.get("semantic_metadata", {})),
            row_count=d["import_metadata"]["row_count"],
            version_id=d["version_id"],
            origin_version=self.data.dataset()["version_id"],
            source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
            snapshot_uri=d["snapshot_uri"],
            config_revision=self.revision,
            history_state=copy.deepcopy(self.projects.draft),
        )

    @Slot(str, str, bool)
    def start(self, protocol_json, parameters_json, resume=False):
        if not self.canRun:
            return self.fail(
                ProjectError(
                    "Engelsiz hazırlık, optional CPU backend ve yazılabilir proje gerekir."
                )
            )
        try:
            spec = NeuralSpec.from_dict(json.loads(parameters_json))
            protocol = ValidationSpec.from_dict(json.loads(protocol_json))
            protocol.resolved(self.preparation.result)
            if spec.wall_seconds > self.budget.max_wall_seconds:
                raise ProjectError("Tensor süre bütçesi ComputeBudget sınırını aşamaz.")
            self.resume = copy.deepcopy(self.active) if resume else None
            if resume and self.resume is None:
                raise ProjectError("Önce kalıcı paused/canceled checkpoint açın.")
            self.revision += 1
            self.binding = self.current_binding()
            d = self.selected_source()
            self.request = self.request_for(d)
            self.request.update(
                preparation=copy.deepcopy(self.preparation.result),
                prior_test_use_ids=prior_uses(self.projects.draft),
                run_id="run:" + uid(),
                training_id=self.resume["training_id"]
                if self.resume
                else "run:" + uid(),
                experiment_capture=capture(
                    dict(neural_spec=spec.data(), protocol=protocol.data())
                ),
            )
            self.protocol, self.parameters = protocol.data(), spec.data()
            self._error = ""
            self.cancel_time = None
            self._timed_out = False
            self.projects.dataset_active = True
            self.stage = "choice"
            self.future = self.projects.executor.submit(
                choice,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                d["version_id"],
                self.protocol,
                self.preparation.result["plan"]["version_id"],
                self.request["run_id"],
            )
            self.changed.emit()
        except (ValueError, TypeError, KeyError, OSError) as error:
            self.fail(error)

    def launch(self, prediction=False):
        self.cache.mkdir(parents=True, exist_ok=True)
        self.workspace = tempfile.mkdtemp(prefix="tensor-", dir=self.cache)
        ctx = mp.get_context("spawn")
        self.cancel_event, self.pause_event = ctx.Event(), ctx.Event()
        self.connection, sender = ctx.Pipe(duplex=True)
        target = neural_predict_entry if prediction else neural_entry
        args = (
            (
                self.request,
                self.active,
                self.workspace,
                self.cancel_event,
                sender,
                self.budget,
            )
            if prediction
            else (
                self.request,
                self.protocol,
                self.parameters,
                self.workspace,
                self.cancel_event,
                sender,
                self.budget,
                self.resume,
                self.pause_event,
            )
        )
        self.process = ctx.Process(target=target, args=args)
        self.started = time.monotonic()
        if not start_controller(self, sender):
            return
        sender.close()
        self.stage = "prediction" if prediction else "running"
        self.projects.dataset_active = True
        self.changed.emit()

    @Slot()
    def pause(self):
        if self.process and self.stage != "prediction":
            self.pause_event.set()
            self._message = (
                "Epoch sınırında pause: optimizer/scheduler/RNG birlikte korunacak."
            )
            self.changed.emit()

    @Slot()
    def cancel(self):
        if self.process:
            super().cancel()
        elif self.future:
            self.cancel_time = self.cancel_time or time.monotonic()

    def finish(self, status):
        self.release()
        self.projects.dataset_active = True
        self.stage = "complete"
        self.future = self.projects.executor.submit(
            complete,
            self.projects.store,
            copy.deepcopy(self.projects.draft),
            status="completed"
            if status == "completed"
            else "canceled"
            if status in ("paused", "canceled", "budget_exhausted")
            else "failed",
            run_id=self.request["run_id"],
        )

    def terminal(self, status):
        if (
            self.active
            and self.active["training_id"] == self.request.get("training_id")
            and self.active["status"] != "completed"
        ):
            value = copy.deepcopy(self.active)
            value.update(status=status, run_id=self.request["run_id"])
            base = (self.resume or {}).get("elapsed_seconds", 0)
            value["elapsed_seconds"] = max(
                value["elapsed_seconds"], base + time.monotonic() - self.started
            )
            self.release()
            self.projects.dataset_active = True
            self._incoming = value
            self.stage = "terminal_publish"
            self.future = self.projects.executor.submit(
                publish, self.projects.store, copy.deepcopy(self.projects.draft), value
            )
        else:
            self.finish(status)

    def poll(self):
        if self.future:
            if not self.future.done():
                return
            future, self.future = self.future, None
            try:
                state = future.result()
                self.projects.draft = state
                self.projects.saved = copy.deepcopy(state)
                if self.stage == "choice":
                    if self.cancel_time:
                        self.finish("canceled")
                    else:
                        self.launch()
                elif self.stage == "terminal_publish":
                    self.active = self._incoming
                    self.finish(self.active["status"])
                elif self.stage == "checkpoint":
                    self.active = self._incoming
                    self.stage = "running"
                    self.connection.send("published")
                else:
                    if (
                        self.active
                        and self.active["status"] == "completed"
                        and self.active["run_id"] == self.request["run_id"]
                    ):
                        self.result = self.summary(self.active)
                        self.result_binding = self.binding
                    self.stage = None
                    self.projects.dataset_active = False
                    self._message = "Kalıcı tensor kaydı hazır; validation/test kapsamını ve framework sınırlarını inceleyin."
            except (ValueError, TypeError, KeyError, OSError) as error:
                self.fail(error)
                self.release()
                self.stage = None
            self.projects.changed.emit()
            self.changed.emit()
            return
        if not self.process:
            return
        if time.monotonic() - self.started > (
            self.budget.max_wall_seconds
            if self.stage == "prediction"
            else min(self.budget.max_wall_seconds, self.parameters["wall_seconds"])
        ):
            self._timed_out = True
            self.cancel()
        if (
            self.cancel_time
            and time.monotonic() - self.cancel_time > self.budget.cancel_grace_ms / 1000
        ):
            prediction = self.stage == "prediction"
            self.release()
            if not prediction:
                self.terminal("budget_exhausted" if self._timed_out else "canceled")
            self._message = "Zorunlu iptal: son atomik epoch checkpoint korundu; kısmi epoch resume sayılmaz."
            self.changed.emit()
            return
        if self.connection.poll():
            try:
                kind, value = self.connection.recv()
            except EOFError:
                kind, value = "error", "Tensor worker bağlantısı kapandı."
            if kind == "progress":
                self._message = value.phase
            elif kind == "checkpoint":
                self._incoming = value
                self.stage = "checkpoint"
                self.future = self.projects.executor.submit(
                    publish,
                    self.projects.store,
                    copy.deepcopy(self.projects.draft),
                    value,
                )
            elif kind == "result":
                if self.stage == "prediction":
                    self.prediction = value
                    self.release()
                    self.stage = None
                    self._message = (
                        "Yeni immutable veri prediction hazır; fit yapılmadı."
                    )
                else:
                    self.active = value
                    self.finish(value["status"])
            else:
                self._error = value or "İptal edildi; önceki kalıcı checkpoint korundu."
                if self.stage == "prediction":
                    self.release()
                    self.stage = None
                else:
                    if kind == "canceled":
                        self.terminal(
                            "budget_exhausted" if self._timed_out else "canceled"
                        )
                    else:
                        self.finish("failed")
            self.projects.changed.emit()
            self.changed.emit()
        elif not self.process.is_alive():
            self._error = "Tensor worker beklenmeden durdu; başarılı sayılmadı."
            self.finish("failed")

    @Slot(str)
    def openRun(self, ident):
        if self.busy or self.projects.busy:
            return
        try:
            record = next(
                r
                for r in self.projects.draft["results"]
                if r["id"] == ident
                and r.get("neural", {}).get("schema") == self.record_schema()
            )
            self.active = load(self.projects.store, record)
            self.result = (
                self.summary(self.active)
                if self.active["status"] == "completed"
                else None
            )
            self.result_binding = self.current_binding()
            self._error = ""
            self._message = "Kalıcı safe JSON checkpoint/model açıldı; ağ isteği ve object import yok."
            self.changed.emit()
        except (ValueError, KeyError, OSError, StopIteration) as error:
            self.fail(error)

    @Slot()
    def predictData(self):
        if (
            self.busy
            or self.projects.busy
            or not self.active
            or self.active["status"] != "completed"
        ):
            return self.fail(ProjectError("Önce completed safe tensor modeli açın."))
        d = self.data.dataset()
        if not d:
            return self.fail(ProjectError("Prediction için yeni veriyi içe aktarın."))
        self.request = self.request_for(d)
        self.request["model_training_id"] = self.active["training_id"]
        self._error = ""
        self.cancel_time = None
        self.launch(prediction=True)
