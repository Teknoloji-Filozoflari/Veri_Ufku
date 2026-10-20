"""Recommendation tasks extend the existing CPU controller/checkpoint/journal lifecycle."""

import copy
import json
import multiprocessing as mp
import tempfile
import time

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.jobs.admission import start_controller
from veri_ufku.modeling.recommendation_contracts import RecommendationSpec
from veri_ufku.modeling.worker import recommendation_entry
from veri_ufku.storage.experiment_store import capture
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.recommendation_store import export_list
from veri_ufku.storage.validation_store import choice, prior_uses
from veri_ufku.ui.neural import NeuralController


class RecommendationController(NeuralController):
    selectRecommendation = Signal(str)
    recommendationChanged = Signal()

    def __init__(self, data, projects, preparation, cache, budget, parent=None):
        super().__init__(data, projects, preparation, cache, budget, parent)
        self.changed.connect(self.recommendationChanged)

    def record_schema(self):
        return "RecommendationRun/v1"

    def selected_source(self):
        return self.data.dataset()

    canRecommendationRun = Property(
        bool,
        lambda self: bool(
            self.data.dataset()
            and self.projects.store
            and not self.projects.readOnly
            and not self.busy
            and not self.projects.busy
        ),
        notify=recommendationChanged,
    )

    def saved(self):
        return [
            dict(
                id=r["id"],
                label=r["neural"]["recommendation_spec"]["task"]
                + " · "
                + r["neural"]["status"]
                + " · "
                + r["neural"].get("mode", ""),
            )
            for r in self.projects.draft["results"]
            if r.get("neural", {}).get("schema") == "RecommendationRun/v1"
        ]

    @Slot(str)
    def startRecommendation(self, parameters):
        if not self.canRecommendationRun:
            return self.fail(
                ProjectError(
                    "Önce etkileşim tablosunu import edin; yazılabilir proje gerekli."
                )
            )
        try:
            spec = RecommendationSpec.from_dict(json.loads(parameters))

            self.revision += 1
            self.binding = self.current_binding()
            d = self.selected_source()
            self.request = self.request_for(d)
            self.request.update(
                run_id="run:" + uid(),
                prior_test_use_ids=prior_uses(self.projects.draft),
                experiment_capture=capture(dict(recommendation_spec=spec.data())),
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
        self.workspace = tempfile.mkdtemp(prefix="recommendation-", dir=self.cache)
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
            target=recommendation_entry,
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

    @Slot(str)
    def requestList(self, raw):
        if (
            self.busy
            or self.projects.busy
            or not self.active
            or self.active["status"] != "completed"
        ):
            return self.fail(ProjectError("Önce completed recommendation modeli açın."))
        try:
            if len(raw.encode()) > 65536:
                raise ProjectError("Öneri istek64KiB sınırı.")
            self.request = dict(recommendation_request=json.loads(raw))
            self._error = ""
            self.cancel_time = None
            self._timed_out = False
            self.launch(prediction=True)
        except (ValueError, TypeError, KeyError, OSError) as e:
            self.fail(e)

    @Slot(str, bool)
    def exportList(self, destination, include_ids=False):
        if self.busy or not self.prediction:
            return self.fail(ProjectError("Önce açık bir yerel öneri listesi üretin."))
        try:
            export_list(self.prediction, destination, include_ids)
            self._message = (
                "Yeni JSON öneri listesi yazıldı; dış kullanıcıya gönderilmedi."
            )
            self._error = ""
            self.changed.emit()
        except (ValueError, TypeError, KeyError, OSError) as e:
            self.fail(e)
