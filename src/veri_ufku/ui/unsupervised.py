"""Two exploratory paths, disposable spawned computation and durable safe marking."""

import base64
import copy
import json
import multiprocessing as mp
import os
import tempfile
import time

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.jobs.admission import start_controller
from veri_ufku.modeling.unsupervised_contracts import UnsupervisedSpec
from veri_ufku.modeling.worker import unsupervised_entry
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.unsupervised_store import load, publish, transfer
from veri_ufku.ui.preparation import PreparationController


class UnsupervisedController(PreparationController):
    unsupervisedChanged = Signal()
    restoreRequested = Signal(str)

    def __init__(self, *args):
        super().__init__(*args)
        self.changed.connect(self.unsupervisedChanged)
        self.record_id = ""
        self.cost_preview = {}
        self.action = None
        self.pending_result = None
        self._message = "Kümeleme veya anomali yolunu seçin. Fit seçilen veri sürümünün tamamında yapılır; hiçbir kayıt silinmez."

    savedRuns = Property(
        "QVariantList",
        lambda self: [
            dict(
                id=r["id"],
                label=r["unsupervised"]["spec"]["method"]
                + " · "
                + r["unsupervised"]["dataset_version"][-8:],
            )
            for r in self.projects.draft["results"]
            if "unsupervised" in r
        ],
        notify=unsupervisedChanged,
    )

    costPreview = Property(
        "QVariantMap", lambda self: self.cost_preview, notify=unsupervisedChanged
    )
    treeImage = Property(
        str,
        lambda self: (
            "data:image/svg+xml;base64,"
            + base64.b64encode(
                self.result.get("method_state", {}).get("dendrogram_svg", "").encode()
            ).decode()
            if self.result and self.result.get("method_state", {}).get("dendrogram_svg")
            else ""
        ),
        notify=unsupervisedChanged,
    )

    @Slot(str)
    def preflight(self, value):
        from veri_ufku.modeling.exploration import preflight

        try:
            d = self.data.dataset()
            if not d:
                raise ProjectError("Önce veri aktarın.")
            spec = UnsupervisedSpec.from_dict(json.loads(value))
            spec.validate(d["import_metadata"]["columns"])
            self.cost_preview = preflight(
                spec, d["import_metadata"]["row_count"], self.budget
            )
            self._error = ""
            self.changed.emit()
        except (ProjectError, ValueError, TypeError) as error:
            self.cost_preview = {}
            self.fail(error)

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
            spec = UnsupervisedSpec.from_dict(json.loads(value))
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
            self.cache.mkdir(parents=True, exist_ok=True)
            self.workspace = tempfile.mkdtemp(prefix="unsupervised-", dir=self.cache)
            ctx = mp.get_context("spawn")
            self.cancel_event = ctx.Event()
            self.connection, sender = ctx.Pipe(duplex=False)
            self.process = ctx.Process(
                target=unsupervised_entry,
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
                "Seçilen veri sürümünün tamamında etiketsiz fit ayrı süreçte çalışıyor."
            )
            self.projects.changed.emit()
            self.changed.emit()
        except (ValueError, TypeError, KeyError, OSError) as error:
            if self.process is not None and self.process.pid is None:
                self.release()
            self.fail(error)

    @Slot()
    def transfer(self):
        if self.busy or self.projects.busy or not self.current or not self.record_id:
            return self.fail(
                ProjectError("Güncel, kayıtlı sonuç gerekli; devam eden işi bekleyin.")
            )
        self.action = "transfer"
        self.future = self.projects.executor.submit(
            transfer,
            self.projects.store,
            copy.deepcopy(self.projects.draft),
            self.record_id,
        )
        self.projects.dataset_active = True
        self._error = ""
        self._message = "Tüm satırları koruyan işaretli yeni dataset hazırlanıyor…"
        self.projects.changed.emit()
        self.changed.emit()

    @Slot(str)
    def openSaved(self, ident):
        if self.busy or self.projects.busy:
            return
        try:
            record = next(
                r
                for r in self.projects.draft["results"]
                if r["id"] == ident and "unsupervised" in r
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
                if self.action == "open":
                    value, _, _, _ = future.result()
                    self.result = value
                    self.revision = value["config_revision"]
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
                            item["unsupervised"],
                            worker_pid=self.pending_result["worker_pid"],
                        )
                        self.result_binding = self.binding
                        self.record_id = item["id"]
                        self._message = "Gerçek hesap ve tüm RowId üyelikleri projeye kaydedildi. Kaynak veri değişmedi."
                    else:
                        self._message = "İşaretli yeni dataset oluşturuldu; tüm kayıtlar ve kaynak kolonlar korundu. Veri ekranından seçebilirsiniz."
            except (ValueError, OSError, StopIteration, KeyError) as error:
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
