"""Bounded text summaries in a disposable process; ephemeral explicit raw preview."""

import copy
import json
import multiprocessing as mp
import os
import tempfile
import time

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.analytics.text_contracts import TextSpec
from veri_ufku.importers.delimited import Canceled as ExceptionCanceled
from veri_ufku.jobs.admission import start_controller
from veri_ufku.modeling.worker import text_entry
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.text_store import load, publish
from veri_ufku.ui.preparation import PreparationController


class TextController(PreparationController):
    textChanged = Signal()
    restoreRequested = Signal(str)
    selectNLP = Signal(str)
    modelSelected = Signal(str)

    def __init__(self, *args):
        super().__init__(*args)
        self.changed.connect(self.textChanged)
        self.record_id = ""
        self.action = None
        self.pending_result = None
        self._message = (
            "Yerel metin incelemesi; ham önizleme varsayılan kapalı. İçerik loglanmaz."
        )

    savedRuns = Property(
        "QVariantList",
        lambda self: [
            dict(
                id=r["id"],
                label="Metin" + " · " + r["text_analysis"]["dataset_version"][-8:],
            )
            for r in self.projects.draft["results"]
            if "text_analysis" in r
        ],
        notify=textChanged,
    )

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
        self.invalidate()
        try:
            d = self.data.dataset()
            if not d:
                raise ProjectError("Önce veri içe aktarın.")
            spec = TextSpec.from_dict(json.loads(value))
            spec.validate()
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
            request["protected_test_row_ids"] = sorted(
                {
                    i
                    for r in self.projects.draft["results"]
                    if r.get("text_analysis", {}).get("dataset_version")
                    == d["version_id"]
                    for i in r["text_analysis"]
                    .get("advanced", {})
                    .get("protected_test_row_ids", [])
                }
            )
            self.cache.mkdir(parents=True, exist_ok=True)
            self.workspace = tempfile.mkdtemp(prefix="text-", dir=self.cache)
            ctx = mp.get_context("spawn")
            self.cancel_event = ctx.Event()
            self.connection, sender = ctx.Pipe(duplex=False)
            self.process = ctx.Process(
                target=text_entry,
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
            self._message = "Token ve vocab bütçesi ayrı yerel süreçte inceleniyor."
            self.projects.changed.emit()
            self.changed.emit()
        except (ValueError, TypeError, KeyError, OSError) as error:
            if self.process is not None and self.process.pid is None:
                self.release()
            self.fail(error)

    @Slot(str)
    def openSaved(self, ident):
        if self.busy or self.projects.busy:
            return
        try:
            record = next(
                r
                for r in self.projects.draft["results"]
                if r["id"] == ident and "text_analysis" in r
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
                if self.action in ("model-inspect", "model-download", "nlp-export"):
                    answer = future.result()
                    if self.action == "model-inspect":
                        self._model_info = answer[1]
                    elif self.action == "model-download":
                        from veri_ufku.analytics.nlp_models import inspect

                        self._model_info = inspect(answer)[1]
                        self.modelSelected.emit(answer)
                    self._message = "Model/cache veya annotation export tamamlandı; metadata/hash ve kapsamı inceleyin."
                elif self.action == "open":
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
                    self._message = (
                        "Kayıtlı betimsel metin özeti açıldı; ham önizleme saklanmaz."
                    )
                else:
                    state, item = future.result()
                    self.projects.draft = state
                    self.projects.saved = copy.deepcopy(state)
                    if self.action in ("publish", "review"):
                        report_source = item.get("full_nlp", self.pending_result)
                        self.result = dict(
                            item["text_analysis"],
                            worker_pid=report_source.get("worker_pid", 0),
                            previews=report_source["previews"],
                            **(
                                {"advanced": copy.deepcopy(report_source["advanced"])}
                                if report_source.get("advanced")
                                else {}
                            ),
                        )
                        if self.action == "review":
                            self.restoreRequested.emit(
                                json.dumps(report_source["spec"])
                            )
                            self.binding = self.current_binding()
                        self.result_binding = self.binding
                        self.record_id = item["id"]
                        self._message = "Betimsel metin özeti kaydedildi. Ham önizleme kayıt dışında tutuldu."
                    else:
                        self._message = "İşaretli yeni dataset oluşturuldu; tüm kayıtlar ve kaynak kolonlar korundu. Veri ekranından seçebilirsiniz."
            except (
                ValueError,
                OSError,
                StopIteration,
                KeyError,
                ExceptionCanceled,
            ) as error:
                self.fail(error)
            self.pending_result = None
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
                    publish,
                    self.projects.store,
                    copy.deepcopy(self.projects.draft),
                    value,
                )
                self.projects.dataset_active = True
                self._message = "Sonuç ve RowId üyelikleri atomik kaydediliyor…"
                self.projects.changed.emit()
                self.changed.emit()
                return
            self.release()
            self.projects.changed.emit()
            self.changed.emit()
            return
        if self.process and not self.process.is_alive() and not self.connection.poll():
            self.release()
            self._error = "Worker beklenmedik kapandı; tamamlanmış sonuç kaydedilmedi."
            self.projects.changed.emit()
            self.changed.emit()

    def shutdown(self):
        self.timer.stop()
        if self.future:
            try:
                self.future.result()
            except (ValueError, OSError):
                pass
            self.future = None
        self.release()

    @Slot(result="QVariantList")
    def nlpMethods(self):
        from veri_ufku.domain.capabilities import CAPABILITIES

        return [
            dict(id=c.capability_id.removeprefix("text.nlp."), label=c.method)
            for c in CAPABILITIES.values()
            if c.capability_id.startswith("text.nlp.")
        ]

    modelInfo = Property(
        "QVariantMap", lambda self: getattr(self, "_model_info", {}), notify=textChanged
    )

    @Slot(str)
    def inspectModel(self, folder):
        if self.busy or self.projects.busy:
            return
        from veri_ufku.analytics.nlp_models import inspect

        self._error = ""
        self.action = "model-inspect"
        self.future = self.projects.executor.submit(inspect, folder)
        self.changed.emit()

    @Slot(str, str, int)
    def downloadModel(self, url, sha, size):
        if self.busy or self.projects.busy:
            return
        from threading import Event

        from veri_ufku.analytics.nlp_models import download
        from veri_ufku.importers.delimited import Control

        self._error = ""
        self.download_cancel = Event()
        self.action = "model-download"
        self.future = self.projects.executor.submit(
            download,
            url,
            sha,
            size,
            self.cache,
            Control(self.download_cancel, budget=self.budget),
        )
        self.changed.emit()

    @Slot()
    def cancel(self):
        if self.future and self.action == "model-download":
            self.download_cancel.set()
            return
        super().cancel()

    @Slot(str, str, str)
    def reviewNLP(self, patch, reviewer, revision):
        if self.busy or self.projects.busy or not self.current:
            return
        try:
            self._error = ""
            self.action = "review"
            self.binding = self.current_binding()
            self.pending_result = copy.deepcopy(self.result)
            self.future = self.projects.executor.submit(
                review_task,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                self.record_id,
                json.loads(patch),
                reviewer,
                revision,
            )
            self.projects.dataset_active = True
            self.changed.emit()
        except (ValueError, TypeError) as error:
            self.fail(error)

    @Slot(str, bool)
    def exportNLP(self, path, include_raw):
        if self.busy or self.projects.busy or not self.current:
            return
        from veri_ufku.storage.text_store import export_annotations

        record = next(
            r for r in self.projects.draft["results"] if r["id"] == self.record_id
        )
        self._error = ""
        self.action = "nlp-export"
        self.future = self.projects.executor.submit(
            export_annotations,
            self.projects.store,
            copy.deepcopy(record),
            path,
            include_raw,
        )
        self.changed.emit()


def review_task(store, state, record_id, patch, reviewer, revision):
    from veri_ufku.storage.text_store import revise

    state, item = revise(store, state, record_id, patch, reviewer, revision)
    return state, dict(item, full_nlp=load(store, item))
