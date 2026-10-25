"""Question-driven model preparation; no model evaluation or complete-data fit."""

import copy
import json
import multiprocessing as mp
import os
import shutil
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from veri_ufku.jobs.admission import start_controller
from veri_ufku.modeling.contracts import PreparationSpec, identifier
from veri_ufku.modeling.history import ancestors, clean_sources
from veri_ufku.modeling.worker import process_entry
from veri_ufku.storage.preparation_store import publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.ui.projects import project_error_text


class PreparationController(QObject):
    changed = Signal()

    def __init__(self, data, projects, cache, budget, parent=None):
        super().__init__(parent)
        self.data, self.projects, self.cache, self.budget = (
            data,
            projects,
            Path(cache),
            budget,
        )
        self.process = self.connection = self.future = None
        self.workspace = self.result = None
        self.binding = self.result_binding = None
        self.revision = 0
        self.source_version = ""
        self._message = "Önce amaç/hedef ve özellikleri seçin. Hazırlık raporu veri değiştirmez veya model fit etmez."
        self._error = ""
        self.cancel_time = None
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        data.changed.connect(self.changed)
        projects.changed.connect(self.changed)

    busy = Property(
        bool,
        lambda self: self.process is not None or self.future is not None,
        notify=changed,
    )
    message = Property(str, lambda self: self._message, notify=changed)
    errorText = Property(str, lambda self: self._error, notify=changed)
    report = Property(
        "QVariantMap",
        lambda self: {
            k: v for k, v in (self.result or {}).items() if k not in ("project_root",)
        },
        notify=changed,
    )
    current = Property(
        bool,
        lambda self: bool(
            self.result and self.result_binding == self.current_binding()
        ),
        notify=changed,
    )
    columns = Property("QVariantList", lambda self: self.column_rows(), notify=changed)
    sourceVersion = Property(
        str,
        lambda self: (self.selected_source() or {}).get("version_id", ""),
        notify=changed,
    )
    sourceChoices = Property(
        "QVariantList", lambda self: self.source_choices(), notify=changed
    )
    savedPlans = Property(
        "QVariantList",
        lambda self: [
            dict(
                id=r["id"],
                label=r["preparation"]["spec"]["purpose"]
                + " · "
                + r["preparation"]["plan"]["version_id"][-8:],
            )
            for r in self.projects.draft["results"]
            if "preparation" in r
        ],
        notify=changed,
    )
    modelCandidates = Property(
        "QVariantMap", lambda self: self.candidate_bundle(), notify=changed
    )

    def candidate_bundle(self):
        from veri_ufku.modeling.candidates import suggest_candidates

        spec = (self.result or {}).get("spec") or {}
        return suggest_candidates(
            spec.get("purpose", ""),
            has_group=bool(spec.get("group")),
            has_time=bool(spec.get("time")),
        )

    @Slot(str, bool, bool, result="QVariantMap")
    def previewCandidates(self, purpose, has_group, has_time):
        from veri_ufku.modeling.candidates import suggest_candidates

        return suggest_candidates(purpose, has_group=has_group, has_time=has_time)

    def selected_source(self):
        origin = self.data.dataset()
        if not origin:
            return None
        if self.source_version:
            ids = ancestors(self.projects.draft, origin["version_id"])
            found = next(
                (
                    d
                    for d in self.projects.draft["datasets"]
                    if d["version_id"] == self.source_version and d["version_id"] in ids
                ),
                None,
            )
            if found:
                return found
        return origin

    def column_rows(self):
        d = self.selected_source()
        if not d or not self.projects.store:
            return []
        schema = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]["schema"]
        return [
            dict(
                c,
                physical_type=schema[c["name"]],
                role=d.get("semantic_metadata", {}).get(c["id"], {}).get("role", ""),
                identifier_candidate=identifier(c, d.get("semantic_metadata", {})),
            )
            for c in d["import_metadata"]["columns"]
        ]

    def source_choices(self):
        origin = self.data.dataset()
        if not origin:
            return []
        choices = [
            dict(
                id=origin["version_id"],
                label="Aktif temizlik sürümü · " + origin["version_id"][-8:],
            )
        ]
        choices.extend(
            dict(
                id=d["version_id"],
                label="Önceki kaynak · "
                + d["version_id"][-8:]
                + " · "
                + str(d["import_metadata"]["row_count"])
                + " kayıt",
            )
            for d in clean_sources(self.projects.draft, origin["version_id"])
            if d["version_id"] != origin["version_id"]
        )
        return choices

    def current_binding(self):
        return (
            str(self.projects.store.root) if self.projects.store else "",
            (self.data.dataset() or {}).get("version_id"),
            (self.selected_source() or {}).get("version_id"),
            self.revision,
        )

    @Slot()
    def invalidate(self):
        self.revision += 1
        self.changed.emit()

    @Slot()
    def beginRetraining(self):
        if self.busy or self.projects.busy:
            return
        self.source_version = ""
        self.result_binding = None
        self.invalidate()
        self._message = "Yeni veri için hazırlık ve split seçin; eğitim ayrıca başlatılmalıdır. Önceki model korunur."
        self.changed.emit()

    @Slot(str)
    def selectSource(self, version):
        if self.busy:
            return
        if version not in {c["id"] for c in self.source_choices()}:
            return self.fail(
                ProjectError("Kaynak sürümü aktif veri geçmişinde bulunamadı.")
            )
        self.source_version = version
        self.invalidate()

    def fail(self, error):
        self._error = project_error_text(error)
        self.changed.emit()

    @Slot(str)
    def create(self, value):
        if self.busy or self.projects.busy:
            return self.fail(ProjectError("Devam eden işi bekleyin veya iptal edin."))
        try:
            d = self.selected_source()
            origin = self.data.dataset()
            if not d or not origin:
                raise ProjectError("Önce veri içe aktarın.")
            spec = PreparationSpec.from_dict(
                dict(json.loads(value), source_version=d["version_id"])
            )
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
                origin_version=origin["version_id"],
                snapshot_uri=d["snapshot_uri"],
                source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
                history_state=copy.deepcopy(self.projects.draft),
                config_revision=self.revision,
            )
            self.cache.mkdir(parents=True, exist_ok=True)
            self.workspace = tempfile.mkdtemp(prefix="prepare-", dir=self.cache)
            ctx = mp.get_context("spawn")
            self.cancel_event = ctx.Event()
            self.connection, sender = ctx.Pipe(duplex=False)
            self.process = ctx.Process(
                target=process_entry,
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
            self._message = "Uygunluk/geçmiş taraması ayrı süreçte; hiçbir transformer fit edilmiyor."
            self.projects.changed.emit()
            self.changed.emit()
        except (ValueError, TypeError, KeyError, OSError) as error:
            if self.process is not None and self.process.pid is None:
                self.release()
            self.fail(error)

    @Slot()
    def cancel(self):
        if self.process:
            self.cancel_event.set()
            self.cancel_time = self.cancel_time or time.monotonic()
            self._message = "İptal isteniyor…"
            self.changed.emit()

    def release(self):
        if self.process:
            if self.process.pid is not None:
                self.process.join(0.1)
                if self.process.is_alive():
                    self.process.terminate()
                    self.process.join(0.2)
                if self.process.is_alive():
                    self.process.kill()
                    self.process.join()
                self.process.close()
            self.process = None
        if self.connection:
            self.connection.close()
            self.connection = None
        if self.workspace:
            shutil.rmtree(self.workspace, ignore_errors=True)
            self.workspace = None
        self.projects.dataset_active = False

    def poll(self):
        if self.future:
            if not self.future.done():
                return
            future, self.future = self.future, None
            try:
                self.projects.draft = future.result()
                self.projects.saved = copy.deepcopy(self.projects.draft)
                self._message = "Fit edilmemiş pipeline planı, uygunluk ve geçmiş riskleri projeye kaydedildi."
            except (ValueError, OSError) as error:
                self.fail(error)
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
            self._message = "İptal edildi; veri ve önceki plan korundu."
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
            self.release()
            if canceled or kind == "canceled":
                self._message = "İptal edildi; veri ve önceki plan korundu."
            elif not valid:
                self._message = "Eski veri/ayar sonucu güncel plana bağlanmadı."
            elif kind == "error":
                self._error = value
            else:
                self.result = dict(value, project_root=self.binding[0])
                self.result_binding = self.binding
                self._message = "Rapor ve plan hazır. Fit yapılmadı; riskler ve sonraki ayırma protokolü incelenmeli."
            self.projects.changed.emit()
            self.changed.emit()
            return
        if self.process and not self.process.is_alive() and not self.connection.poll():
            self.release()
            self._error = "Hazırlama süreci durdu; eksik plan kabul edilmedi."
            self.projects.changed.emit()
            self.changed.emit()

    @Slot()
    def save(self):
        if (
            not self.current
            or self.busy
            or self.projects.busy
            or self.projects.readOnly
        ):
            return self.fail(ProjectError("Güncel rapor ve yazılabilir proje gerekir."))
        self.future = self.projects.executor.submit(
            publish,
            self.projects.store,
            copy.deepcopy(self.projects.draft),
            copy.deepcopy(self.result),
        )
        self.projects.dataset_active = True
        self.projects.changed.emit()
        self.changed.emit()

    @Slot(str)
    def openSaved(self, ident):
        if self.busy or self.projects.busy:
            return
        try:
            value = copy.deepcopy(
                next(
                    r["preparation"]
                    for r in self.projects.draft["results"]
                    if r["id"] == ident and "preparation" in r
                )
            )
            self.result = dict(value, project_root=str(self.projects.store.root))
            self.source_version = value["dataset_version"]
            self.revision = value["config_revision"]
            self.binding = (
                str(self.projects.store.root),
                value["origin_version"],
                value["dataset_version"],
                value["config_revision"],
            )
            self.result_binding = self.binding
            self._error = ""
            self._message = "Kayıtlı plan açıldı; kaynak sürümü ve geçmiş riskleriyle birlikte incelenmeli."
            self.changed.emit()
        except (ValueError, KeyError, StopIteration) as error:
            self.fail(error)

    def shutdown(self):
        self.timer.stop()
        self.release()
        if self.future:
            try:
                self.future.result()
            except (ValueError, OSError):
                pass
            self.future = None
