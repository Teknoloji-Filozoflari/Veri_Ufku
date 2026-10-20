"""Image tasks extend the existing CPU controller/checkpoint/journal lifecycle."""

import copy
import json
import multiprocessing as mp
import os
import tempfile
import threading
import time

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.analytics.nlp_models import download
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.admission import start_controller
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.vision import parse_weights
from veri_ufku.modeling.vision_contracts import VisionSpec
from veri_ufku.modeling.worker import vision_entry
from veri_ufku.storage.experiment_store import capture
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.validation_store import choice, prior_uses
from veri_ufku.storage.vision_store import export_annotations, export_weights, review
from veri_ufku.ui.neural import NeuralController


class VisionController(NeuralController):
    selectVision = Signal(str)
    visionChanged = Signal()

    def __init__(self, data, projects, preparation, cache, budget, parent=None):
        super().__init__(data, projects, preparation, cache, budget, parent)
        self.changed.connect(self.visionChanged)

    def record_schema(self):
        return "VisionRun/v1"

    def selected_source(self):
        return self.data.dataset()

    canVisionRun = Property(
        bool,
        lambda self: bool(
            self.data.dataset()
            and self.data.dataset()
            .get("import_metadata", {})
            .get("settings", {})
            .get("adapter_id")
            == "image_dataset"
            and self.projects.store
            and not self.projects.readOnly
            and not self.busy
            and not self.projects.busy
        ),
        notify=visionChanged,
    )
    visionRows = Property(
        "QVariantList",
        lambda self: [
            dict(
                row_id=r["row_id"],
                label=r["image_id"] + " · " + r["annotation"]["status"],
            )
            for r in (self.active or {}).get("images", [])
        ],
        notify=visionChanged,
    )

    def saved(self):
        return [
            dict(
                id=r["id"],
                label=r["neural"]["vision_spec"]["task"]
                + " · "
                + r["neural"]["status"]
                + " · "
                + r["neural"].get("mode", ""),
            )
            for r in self.projects.draft["results"]
            if r.get("neural", {}).get("schema") == "VisionRun/v1"
        ]

    def request_for(self, d):
        request = super().request_for(d)
        source = next(
            s for s in self.projects.draft["sources"] if s["id"] == d["source_id"]
        )
        if not source["copy_uri"]:
            raise ProjectError(
                "Görüntü bundle immutable kopyası gerekli; yeniden import edin."
            )
        fp = self.projects.store.manifest["artifacts"][source["copy_uri"]]
        request.update(
            image_bundle=str(self.projects.store.path(source["copy_uri"])).replace(
                "/proc/self/", f"/proc/{os.getpid()}/", 1
            ),
            image_fingerprint={k: fp[k] for k in ("size", "sha256")},
            image_catalog=d["import_metadata"]["settings"]["format_metadata"],
            image_column=next(
                c["id"]
                for c in d["import_metadata"]["columns"]
                if c["name"] == "member"
            ),
        )
        return request

    @Slot(str)
    def startVision(self, parameters):
        if not self.canVisionRun:
            return self.fail(
                ProjectError("Önce yerel görüntü klasörü/images.json import edin.")
            )
        try:
            spec = VisionSpec.from_dict(json.loads(parameters))
            if (
                spec.task in ("classification", "transfer")
                and not self.backend_available()
            ):
                raise ProjectError("Optional CPU PyTorch yok; model indirilmez.")
            self.revision += 1
            self.binding = self.current_binding()
            d = self.selected_source()
            self.request = self.request_for(d)
            self.request.update(
                run_id="run:" + uid(),
                prior_test_use_ids=prior_uses(self.projects.draft),
                experiment_capture=capture(dict(vision_spec=spec.data())),
            )
            if (
                self.active
                and self.active["schema"] == "VisionRun/v1"
                and self.active["dataset_version"] == d["version_id"]
            ):
                self.request.update(
                    annotations=copy.deepcopy(self.active["annotations"]),
                    frozen_plan=self.active["plan"],
                )
            self.request["training_id"] = self.request["run_id"]
            self.parameters = spec.data()
            self.parameters["wall_seconds"] = self.budget.max_wall_seconds
            self.protocol = dict(seed=spec.seed, structure="group")
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
        self.workspace = tempfile.mkdtemp(prefix="vision-", dir=self.cache)
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
            target=vision_entry,
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

    def poll(self):
        if self.future and self.stage in (
            "vision_review",
            "vision_export",
            "vision_download",
        ):
            if not self.future.done():
                return
            future, self.future = self.future, None
            try:
                value = future.result()
                if self.stage == "vision_review":
                    state, self.active = value
                    self.projects.draft = state
                    self.projects.saved = copy.deepcopy(state)
                elif self.stage == "vision_download":
                    self._message = "Safe model cache hazır: " + str(value)
                else:
                    self._message = "Yeni dosyaya export tamamlandı; reviewer masked, insan/model statüsü korunur."
            except Canceled:
                self._message = (
                    "Model indirme iptal edildi; cache tamamlanmış gibi sunulmadı."
                )
            except (ValueError, KeyError, TypeError, OSError) as e:
                self.fail(e)
            self.stage = None
            self.projects.dataset_active = False
            self.projects.changed.emit()
            self.changed.emit()
            return
        super().poll()

    @Slot(str, str, str)
    def reviewAnnotation(self, row, value, reviewer):
        if self.busy or self.projects.busy or not self.active:
            return
        try:
            self.stage = "vision_review"
            self.future = self.projects.executor.submit(
                review,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                copy.deepcopy(self.active),
                row,
                json.loads(value),
                reviewer,
            )
            self.projects.dataset_active = True
            self._error = ""
            self.changed.emit()
        except (ValueError, TypeError) as e:
            self.stage = None
            self.fail(e)

    @Slot()
    def predictData(self):
        if (
            not self.data.dataset()
            or self.data.dataset()
            .get("import_metadata", {})
            .get("settings", {})
            .get("adapter_id")
            != "image_dataset"
        ):
            return self.fail(ProjectError("Prediction için yeni image snapshot seçin."))
        try:
            super().predictData()
        except (ValueError, KeyError, OSError) as error:
            self.fail(error)

    @Slot()
    def cancel(self):
        if self.stage == "vision_download" and self.future:
            self._download_cancel.set()
            self._message = "Optional model download iptal isteniyor."
            self.changed.emit()
        else:
            super().cancel()

    @Slot(str)
    def exportAnnotations(self, target):
        if self.busy or not self.active:
            return
        self.stage = "vision_export"
        self.future = self.projects.executor.submit(
            export_annotations, copy.deepcopy(self.active), target
        )
        self.projects.dataset_active = True
        self.changed.emit()

    @Slot(str, str, str)
    def exportWeights(self, target, license_text, dataset):
        if self.busy or not self.active:
            return
        self.stage = "vision_export"
        self.future = self.projects.executor.submit(
            export_weights, copy.deepcopy(self.active), target, license_text, dataset
        )
        self.projects.dataset_active = True
        self.changed.emit()

    @Slot(str, str, int, bool)
    def downloadModel(self, url, sha, bytes_count, consent):
        if self.busy or not consent or not self.backend_available():
            return self.fail(
                ProjectError(
                    "Açık HTTPS download onayı ve CPU backend gerekli; auth desteklenmez."
                )
            )
        self._download_cancel = threading.Event()
        self.stage = "vision_download"
        self.future = self.projects.executor.submit(
            download,
            url,
            sha,
            bytes_count,
            self.cache,
            Control(cancel=self._download_cancel, budget=self.budget),
            validator=parse_weights,
            namespace="vision-models",
        )
        self.projects.dataset_active = True
        self.changed.emit()
