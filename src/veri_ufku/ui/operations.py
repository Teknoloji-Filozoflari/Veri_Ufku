"""Explicit preview/apply and persisted history, with compute off the GUI thread."""

import copy
import multiprocessing as mp
import os
import shutil
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from veri_ufku.operations.contracts import activate, build, move
from veri_ufku.operations.worker import process_entry
from veri_ufku.storage.project_model import ProjectError, decode
from veri_ufku.ui.dataset import DatasetTableModel
from veri_ufku.ui.projects import project_error_text


def publish(store, state, result=None):
    previous = store.state
    store.state = state
    try:
        if result:
            store.publish_operation(result)
        else:
            store.save()
        return copy.deepcopy(store.state)
    except BaseException:
        # publish_operation reconciles a post-ACTIVE durability failure itself.
        if not result:
            pointer = decode(store._read("ACTIVE", 4096))
            if pointer["commit_id"] != store.commit_id:
                store._load("ACTIVE")
            else:
                store.state = previous
        raise


class OperationsController(QObject):
    changed = Signal()

    def __init__(self, data, projects, cache, budget, parent=None):
        super().__init__(parent)
        self.data, self.projects = data, projects
        self.cache, self.budget = Path(cache), budget
        self.before = DatasetTableModel(self)
        self.after = DatasetTableModel(self)
        self.process = self.connection = self.cancel_event = self.future = None
        self.workspace = None
        self.preview = None
        self.binding = None
        self.signature = None
        self._message = "Kaynak korunur. Önizleme tüm veriyi hesaplar; tablolar ilk200 kaydı gösterir."
        self._error = ""
        self._state = "idle"
        self.cancel_time = None
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        projects.changed.connect(self.project_changed)
        data.changed.connect(self.changed)

    busy = Property(
        bool,
        lambda self: self.process is not None or self.future is not None,
        notify=changed,
    )
    message = Property(str, lambda self: self._message, notify=changed)
    errorText = Property(str, lambda self: self._error, notify=changed)
    state = Property(str, lambda self: self._state, notify=changed)
    beforeModel = Property(QObject, lambda self: self.before, constant=True)
    afterModel = Property(QObject, lambda self: self.after, constant=True)
    canApply = Property(
        bool,
        lambda self: bool(
            self.preview
            and not self.busy
            and not self.projects.busy
            and not self.projects.readOnly
            and self.binding == self.current_binding()
        ),
        notify=changed,
    )
    previewResult = Property(
        "QVariantMap",
        lambda self: {
            k: v
            for k, v in (self.preview or {}).items()
            if k not in ("before", "after", "path")
        },
        notify=changed,
    )
    history = Property("QVariantList", lambda self: self.history_rows(), notify=changed)
    resultStatuses = Property(
        "QVariantList",
        lambda self: [
            dict(
                id=r["id"],
                label=r.get("capability_id", "Sonuç"),
                current=r["current"],
                versions=", ".join(r["dataset_version_ids"]),
            )
            for r in self.projects._result_statuses()
        ],
        notify=changed,
    )

    def current_binding(self):
        d = self.data.dataset()
        return (
            str(self.projects.store.root) if self.projects.store else "",
            d["version_id"] if d else "",
            self.data.revision,
        )

    def project_changed(self):
        binding = self.current_binding()
        if self.signature != binding:
            self.signature = binding
            if self.process:
                self.cancel()
            if not self.future:
                self.clear_preview()
        self.changed.emit()

    @Slot()
    def discardPreview(self):
        if not self.busy:
            self.clear_preview()
            self.changed.emit()

    def clear_preview(self):
        self.preview = None
        self.before.replace()
        self.after.replace()
        if self.workspace and not self.process:
            shutil.rmtree(self.workspace, ignore_errors=True)
            self.workspace = None

    def history_rows(self):
        d = self.data.dataset()
        if not d:
            return []
        versions = {v["version_id"]: v for v in self.projects.draft["datasets"]}
        chain, cursor = set(), d
        while cursor:
            chain.add(cursor["version_id"])
            cursor = versions.get(next(iter(cursor.get("parent_version_ids", [])), ""))
        return [
            dict(
                id=v["version_id"],
                label=f"{i + 1}. {next((o.get('spec', {}).get('kind', o.get('capability_id', 'metadata')) for o in self.projects.draft['operations'] if o.get('output_version_id') == v['version_id']), 'Kaynak / metadata')} · {v['version_id'][-8:]}",
                current=v["version_id"] == d["version_id"],
                onBranch=v["version_id"] in chain,
                parent=next(iter(v.get("parent_version_ids", [])), ""),
            )
            for i, v in enumerate(self.projects.draft["datasets"])
            if v["dataset_id"] == d["dataset_id"]
        ]

    def fail(self, error):
        self._error = project_error_text(error)
        self._state = "failed"
        self.changed.emit()

    @Slot(str, str, str)
    def previewOperation(self, kind, column_id="", name=""):
        if self.busy or self.projects.busy or self.projects.readOnly:
            return self.fail(
                ProjectError("Devam eden işi bekleyin; proje yazılabilir olmalı.")
            )
        try:
            d = self.data.dataset()
            if not d:
                raise ProjectError("Önce dataset içe aktarın.")
            self.clear_preview()
            artifact = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]
            request = dict(
                path=str(self.projects.store.path(d["snapshot_uri"])).replace(
                    "/proc/self/", f"/proc/{os.getpid()}/", 1
                ),
                fingerprint={k: artifact[k] for k in ("sha256", "size")},
                columns=copy.deepcopy(d["import_metadata"]["columns"]),
                row_count=d["import_metadata"]["row_count"],
                version_id=d["version_id"],
                source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
                config_revision=self.data.revision,
            )
            if kind == "filter":
                cols = {c["id"]: c for c in request["columns"]}
                filters = [
                    dict(
                        column_id=f["column_id"],
                        operator=f["operator"],
                        literal={
                            "dtype": cols[f["column_id"]]["type"],
                            "text": f["value"],
                        },
                    )
                    for f in self.data.view.filters
                ]
                spec = build(
                    request,
                    kind,
                    list(dict.fromkeys(f["column_id"] for f in filters)),
                    {"filters": filters},
                )
            else:
                spec = build(
                    request,
                    kind,
                    [column_id],
                    {"name": name} if kind == "rename" else {},
                )
            self.binding = self.current_binding()
            self.cache.mkdir(parents=True, exist_ok=True)
            self.workspace = tempfile.mkdtemp(prefix="operation-", dir=self.cache)
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
            self.process.start()
            sender.close()
            self.started = time.monotonic()
            self.cancel_time = None
            self.projects.dataset_active = True
            self._error = ""
            self._state = "running"
            self._message = "Önizleme hesaplanıyor… Eski dataset korunuyor."
            self.projects.changed.emit()
            self.changed.emit()
        except (ValueError, OSError, KeyError, TypeError) as error:
            self.release()
            self.clear_preview()
            self.fail(error)

    @Slot()
    def cancel(self):
        if self.process:
            self.cancel_event.set()
            self.cancel_time = self.cancel_time or time.monotonic()
            self._state = "cancel_requested"
            self.changed.emit()

    def release(self):
        if self.process:
            self.process.join(timeout=0.1)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=0.2)
            if self.process.is_alive():
                self.process.kill()
                self.process.join()
            self.process.close()
            self.process = None
        if self.connection:
            self.connection.close()
            self.connection = None
        self.projects.dataset_active = False

    @Slot()
    def apply(self):
        if not self.canApply:
            return self.fail(ProjectError("Geçerli önizleme yok; yeniden önizleyin."))
        self.submit(copy.deepcopy(self.projects.draft), self.preview)

    def submit(self, state, result=None):
        self.publication_commit = self.projects.store.commit_id
        self.future = self.projects.executor.submit(
            publish, self.projects.store, state, result
        )
        self.projects.dataset_active = True
        self._state = "publishing"
        self._message = (
            "İşlem ve geçmiş atomik kaydediliyor… Bu eylem proje taslağını da kaydeder."
        )
        self.projects.changed.emit()
        self.changed.emit()

    @Slot(str)
    def historyAction(self, direction):
        if self.busy or self.projects.busy or self.projects.readOnly:
            return
        try:
            state = copy.deepcopy(self.projects.draft)
            move(state, self.data.dataset_id, direction)
            self.submit(state)
        except (ValueError, TypeError) as error:
            self.fail(error)

    @Slot(str)
    def checkout(self, version):
        if self.busy or self.projects.busy or self.projects.readOnly:
            return
        state = copy.deepcopy(self.projects.draft)
        d = next(
            (
                v
                for v in state["datasets"]
                if v["dataset_id"] == self.data.dataset_id
                and v["version_id"] == version
            ),
            None,
        )
        if d:
            activate(state, d)
            self.submit(state)

    def poll(self):
        if self.future:
            if not self.future.done():
                return
            future, self.future = self.future, None
            try:
                state = future.result()
                self.projects.draft = state
                self.projects.saved = copy.deepcopy(state)
                self.projects.store.state = state
                self._state = "succeeded"
                self._message = (
                    "İşlem/geçmiş kaydedildi. Eski sonuçların sürüm bağları korunur."
                )
            except Exception as error:
                if self.projects.store.commit_id != self.publication_commit:
                    self.projects.draft = copy.deepcopy(self.projects.store.state)
                    self.projects.saved = copy.deepcopy(self.projects.store.state)
                self.fail(error)
            self.projects.dataset_active = False
            self.clear_preview()
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
            self.clear_preview()
            self._state = "canceled"
            self._message = "İptal edildi; eski dataset korundu."
            self.projects.changed.emit()
            self.changed.emit()
            return
        while self.connection.poll():
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
            if kind == "result" and valid and not canceled:
                self.preview = value
                self.before.replace(value["before"])
                self.after.replace(value["after"])
                self._state = "previewed"
                self._message = "Tam veri etki sayımı hazır. Karşılaştırma tabloları ilk200 kaydı gösterir. Uygula proje taslağını da kaydeder."
            else:
                self.clear_preview()
                if kind == "error":
                    self.fail(ProjectError(value))
                else:
                    self._state = "canceled"
                    self._message = (
                        "İptal/eski sürüm: sonuç uygulanmadı; dataset korundu."
                    )
            self.projects.changed.emit()
            self.changed.emit()
            return
        if not self.process.is_alive() and not self.connection.poll():
            self.release()
            self.clear_preview()
            self.fail(ProjectError("İşlem süreci durdu; eski dataset korundu."))
            self.projects.changed.emit()

    def shutdown(self):
        self.timer.stop()
        if self.future:
            self.future.result()
            self.poll()
        self.release()
        self.clear_preview()
