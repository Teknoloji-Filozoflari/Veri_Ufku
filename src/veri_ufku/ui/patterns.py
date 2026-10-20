"""Recommendation tasks extend the existing CPU controller/checkpoint/journal lifecycle."""

import copy
import json
import multiprocessing as mp
import tempfile
import time

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.jobs.admission import start_controller
from veri_ufku.modeling.pattern_contracts import PatternSpec
from veri_ufku.modeling.worker import pattern_entry
from veri_ufku.storage.experiment_store import capture
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.validation_store import choice, prior_uses
from veri_ufku.ui.neural import NeuralController


class PatternController(NeuralController):
    selectPattern = Signal(str)
    patternChanged = Signal()

    def __init__(self, data, projects, preparation, cache, budget, parent=None):
        super().__init__(data, projects, preparation, cache, budget, parent)
        self.changed.connect(self.patternChanged)
        self._message = (
            "Yerel sepet ve olay keşfi; model eğitimi veya final test hesabı yok."
        )

    def summary(self, data):
        # QML does not need thousands of lineage objects for a status caption.
        # Full immutable rows remain in active Python data and the hashed artifact.
        value = super().summary(data)
        value["row_count"] = len(value.pop("rows", []))
        value.pop("plan", None)
        value.pop("tensor_schema", None)
        return value

    def poll(self):
        super().poll()
        if not self.busy and self.active:
            status = self.active["status"]
            messages = {
                "completed": "Kalıcı keşif sonucu hazır; payda ve gözlem kapsamını inceleyin.",
                "canceled": "Keşif iptal edildi; kalıcı kaynak ve önceki sonuçlar korundu.",
                "failed": "Keşif tamamlanmadı; bütçe veya şema nedenini inceleyin.",
            }
            message = messages.get(status, self._message)
            reason = self.active["warnings"][-1] if status == "failed" else self._error
            if self._message != message or self._error != reason:
                self._message, self._error = message, reason
                self.changed.emit()

    def record_schema(self):
        return "PatternRun/v1"

    def selected_source(self):
        return self.data.dataset()

    canPatternRun = Property(
        bool,
        lambda self: bool(
            self.data.dataset()
            and self.projects.store
            and not self.projects.readOnly
            and not self.busy
            and not self.projects.busy
        ),
        notify=patternChanged,
    )

    def saved(self):
        return [
            dict(
                id=r["id"],
                label=r["neural"]["pattern_spec"]["task"]
                + " · "
                + r["neural"]["status"]
                + " · "
                + r["neural"].get("mode", ""),
            )
            for r in self.projects.draft["results"]
            if r.get("neural", {}).get("schema") == "PatternRun/v1"
        ]

    @Slot(str)
    def startPattern(self, parameters):
        if not self.canPatternRun:
            return self.fail(
                ProjectError(
                    "Önce etkileşim tablosunu import edin; yazılabilir proje gerekli."
                )
            )
        try:
            spec = PatternSpec.from_dict(json.loads(parameters))

            self.revision += 1
            self.binding = self.current_binding()
            d = self.selected_source()
            self.request = self.request_for(d)
            self.request.update(
                run_id="run:" + uid(),
                prior_test_use_ids=prior_uses(self.projects.draft),
                experiment_capture=capture(dict(pattern_spec=spec.data())),
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
        self.workspace = tempfile.mkdtemp(prefix="pattern-", dir=self.cache)
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
            target=pattern_entry,
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
