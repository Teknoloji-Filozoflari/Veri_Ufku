"""Audio tasks extend the existing CPU controller/checkpoint/journal lifecycle."""

import copy
import json
import multiprocessing as mp
import os
import tempfile
import time

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.jobs.admission import start_controller
from veri_ufku.modeling.audio_contracts import AudioSpec
from veri_ufku.modeling.worker import audio_entry
from veri_ufku.storage.experiment_store import capture
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.validation_store import choice, prior_uses
from veri_ufku.ui.neural import NeuralController


class AudioController(NeuralController):
    selectAudio = Signal(str)
    audioChanged = Signal()

    def __init__(self, data, projects, preparation, cache, budget, parent=None):
        super().__init__(data, projects, preparation, cache, budget, parent)
        self.changed.connect(self.audioChanged)

    def record_schema(self):
        return "AudioRun/v1"

    def selected_source(self):
        return self.data.dataset()

    canAudioRun = Property(
        bool,
        lambda self: bool(
            self.data.dataset()
            and self.data.dataset()
            .get("import_metadata", {})
            .get("settings", {})
            .get("adapter_id")
            == "audio_dataset"
            and self.projects.store
            and not self.projects.readOnly
            and not self.busy
            and not self.projects.busy
        ),
        notify=audioChanged,
    )

    def saved(self):
        return [
            dict(
                id=r["id"],
                label=r["neural"]["audio_spec"]["task"]
                + " · "
                + r["neural"]["status"]
                + " · "
                + r["neural"].get("mode", ""),
            )
            for r in self.projects.draft["results"]
            if r.get("neural", {}).get("schema") == "AudioRun/v1"
        ]

    def request_for(self, d):
        request = super().request_for(d)
        source = next(
            s for s in self.projects.draft["sources"] if s["id"] == d["source_id"]
        )
        if not source["copy_uri"]:
            raise ProjectError("Ses immutable kopyası gerekli; yeniden import edin.")
        fp = self.projects.store.manifest["artifacts"][source["copy_uri"]]
        request.update(
            audio_bundle=str(self.projects.store.path(source["copy_uri"])).replace(
                "/proc/self/", f"/proc/{os.getpid()}/", 1
            ),
            audio_fingerprint={k: fp[k] for k in ("size", "sha256")},
            audio_catalog=d["import_metadata"]["settings"]["format_metadata"],
            audio_column=next(
                c["id"]
                for c in d["import_metadata"]["columns"]
                if c["name"] == "member"
            ),
        )
        return request

    @Slot(str)
    def startAudio(self, parameters):
        if not self.canAudioRun:
            return self.fail(
                ProjectError("Önce yerel WAV/FLAC veya audio.json import edin.")
            )
        try:
            spec = AudioSpec.from_dict(json.loads(parameters))

            self.revision += 1
            self.binding = self.current_binding()
            d = self.selected_source()
            self.request = self.request_for(d)
            self.request.update(
                run_id="run:" + uid(),
                prior_test_use_ids=prior_uses(self.projects.draft),
                experiment_capture=capture(dict(audio_spec=spec.data())),
            )
            if (
                self.active
                and self.active["schema"] == "AudioRun/v1"
                and self.active["dataset_version"] == d["version_id"]
                and self.active["audio_spec"]["task"] == "classification"
                and spec.task == "classification"
            ):
                self.request["frozen_plan"] = self.active["plan"]
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
        self.workspace = tempfile.mkdtemp(prefix="audio-", dir=self.cache)
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
            target=audio_entry,
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

    @Slot()
    def predictData(self):
        if (
            not self.data.dataset()
            or self.data.dataset()
            .get("import_metadata", {})
            .get("settings", {})
            .get("adapter_id")
            != "audio_dataset"
        ):
            return self.fail(ProjectError("Yeni audio snapshot seçin; fit yapılmaz."))
        try:
            super().predictData()
        except (ValueError, KeyError, TypeError, OSError) as e:
            self.fail(e)
