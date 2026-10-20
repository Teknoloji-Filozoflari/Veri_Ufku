"""Recommendation tasks extend the existing CPU controller/checkpoint/journal lifecycle."""

import copy
import json
import multiprocessing as mp
import tempfile
import time

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.jobs.admission import start_controller
from veri_ufku.modeling.stream_contracts import StreamSpec
from veri_ufku.modeling.worker import stream_entry
from veri_ufku.storage.experiment_store import capture
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.validation_store import choice, prior_uses
from veri_ufku.ui.neural import NeuralController


class StreamController(NeuralController):
    selectStream = Signal(str)
    streamChanged = Signal()

    def __init__(self, data, projects, preparation, cache, budget, parent=None):
        super().__init__(data, projects, preparation, cache, budget, parent)
        self.changed.connect(self.streamChanged)
        self._message = (
            "Yerel append simülatörü; binary prequential, bounded feedback ve pencere."
        )

    def summary(self, data):
        # QML does not need thousands of lineage objects for a status caption.
        # Full immutable rows remain in active Python data and the hashed artifact.
        value = super().summary(data)
        return value

    def poll(self):
        super().poll()
        if not self.busy and self.active:
            status = self.active["status"]
            messages = {
                "completed": "Replay tamamlandı; pending/missing/late ve yalnız etiketli prequential metriği inceleyin.",
                "canceled": "Keşif iptal edildi; kalıcı kaynak ve önceki sonuçlar korundu.",
                "failed": "Keşif tamamlanmadı; bütçe veya şema nedenini inceleyin.",
            }
            message = messages.get(status, self._message)
            reason = self.active["warnings"][-1] if status == "failed" else self._error
            if self._message != message or self._error != reason:
                self._message, self._error = message, reason
                self.changed.emit()

    def record_schema(self):
        return getattr(self, "_schema", "StreamRun/v1")

    def selected_source(self):
        return self.data.dataset()

    canStreamRun = Property(
        bool,
        lambda self: bool(
            self.data.dataset()
            and self.projects.store
            and not self.projects.readOnly
            and not self.busy
            and not self.projects.busy
        ),
        notify=streamChanged,
    )

    def saved(self):
        return [
            dict(
                id=r["id"], label=r["neural"]["schema"] + " · " + r["neural"]["status"]
            )
            for r in self.projects.draft["results"]
            if r.get("neural", {}).get("schema")
            in ("StreamRun/v1", "SpecialTargetRun/v1")
        ]

    @Slot(str)
    def openRun(self, ident):
        record = next(
            (r for r in self.projects.draft["results"] if r["id"] == ident), None
        )
        if record and record.get("neural", {}).get("schema") in (
            "StreamRun/v1",
            "SpecialTargetRun/v1",
        ):
            self._schema = record["neural"]["schema"]
            super().openRun(ident)

    @Slot(str)
    def startSpecial(self, parameters):
        self._special_requested = True
        try:
            self.startStream(parameters)
        finally:
            self._special_requested = False

    @Slot(str)
    def resumeStream(self, parameters):
        if (
            not self.active
            or self.active.get("schema") != "StreamRun/v1"
            or self.active["status"] not in ("running", "canceled", "budget_exhausted")
        ):
            return self.fail(
                ProjectError("Önce running/canceled/budget_exhausted checkpoint açın.")
            )
        self._resume_requested = True
        try:
            self.startStream(parameters)
        finally:
            self._resume_requested = False

    @Slot(str)
    def startStream(self, parameters):
        if not self.canStreamRun:
            return self.fail(
                ProjectError(
                    "Önce etkileşim tablosunu import edin; yazılabilir proje gerekli."
                )
            )
        try:
            if getattr(self, "_special_requested", False):
                from veri_ufku.modeling.special_runs import TargetRecipe

                spec = TargetRecipe.from_dict(json.loads(parameters))
                self._schema = "SpecialTargetRun/v1"
            else:
                spec = StreamSpec.from_dict(json.loads(parameters))
                self._schema = "StreamRun/v1"

            self.revision += 1
            self.binding = self.current_binding()
            d = self.selected_source()
            self.request = self.request_for(d)
            if (
                getattr(self, "_resume_requested", False)
                and self.active
                and self.active.get("schema") == "StreamRun/v1"
                and self.active["status"] in ("running", "canceled", "budget_exhausted")
            ):
                self.request["stream_resume"] = copy.deepcopy(self.active)
            self.request.update(
                run_id="run:" + uid(),
                prior_test_use_ids=prior_uses(self.projects.draft),
                experiment_capture=capture(
                    {
                        "target_recipe"
                        if getattr(self, "_special_requested", False)
                        else "stream_spec": spec.data()
                    }
                ),
            )
            self.request["training_id"] = self.request["run_id"]
            self.parameters = spec.data()
            self.parameters["wall_seconds"] = self.budget.max_wall_seconds
            self.protocol = dict(seed=spec.seed, structure="time")
            self.resume = None
            self.cancel_time = None
            self._timed_out = False
            self._error = ""
            self.stage = "choice"
            self.projects.dataset_active = True
            self.future = self.projects.executor.submit(
                choice,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                d["version_id"],
                self.protocol,
                "pipeline:" + uid(),
                self.request["run_id"],
            )
            self.changed.emit()
        except (ValueError, KeyError, TypeError, OSError) as e:
            self.fail(e)

    def launch(self, prediction=False):
        self.cache.mkdir(parents=True, exist_ok=True)
        self.workspace = tempfile.mkdtemp(prefix="stream-", dir=self.cache)
        ctx = mp.get_context("spawn")
        self.cancel_event = ctx.Event()
        self.pause_event = ctx.Event()
        self.connection, sender = ctx.Pipe(duplex=True)
        parameters = (
            {k: v for k, v in self.parameters.items() if k != "wall_seconds"}
            if not prediction
            else {}
        )
        self.process = ctx.Process(
            target=stream_entry,
            args=(
                self.request,
                parameters,
                self.workspace,
                self.cancel_event,
                sender,
                self.budget,
                "predict" if prediction else "train",
                self.active if prediction else None,
            ),
        )
        self.started = time.monotonic()
        if not start_controller(self, sender):
            return
        sender.close()
        self.stage = "prediction" if prediction else "running"
        self.projects.dataset_active = True
        self.changed.emit()
