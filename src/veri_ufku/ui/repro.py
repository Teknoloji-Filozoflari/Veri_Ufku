"""Lineage and safe reproduction UI. Every compute/archive action is explicit."""

import copy
import multiprocessing as mp
import os
import shutil
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from veri_ufku.exports.repro_worker import worker
from veri_ufku.jobs.admission import start_controller
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.ui.projects import project_error_text


class ReproController(QObject):
    changed = Signal()

    def __init__(self, projects, cache, budget, parent=None):
        super().__init__(parent)
        self.projects, self.cache, self.budget = projects, Path(cache), budget
        self.process = self.connection = self.cancel_event = None
        self.workspace = None
        self.action = ""
        self.result = {}
        self.preview_result = {}
        self.opened = {}
        self.graph_result = {}
        self.archive = ""
        self.selected = ""
        self._error = ""
        self._message = "Kaydedilmiş rapor/dataset/run seçin. Köken veya bundle açmak analiz çalıştırmaz; re-run ayrı açık eylemdir."
        self._root = None
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        projects.changed.connect(self.project_changed)

    @Slot()
    def project_changed(self):
        root = str(self.projects.store.root) if self.projects.store else None
        if root != self._root and not self.busy:
            self._root = root
            self.result = {}
            self.preview_result = {}
            self.opened = {}
            self.graph_result = {}
            self.archive = ""
            self.selected = ""
        self.changed.emit()

    busy = Property(bool, lambda s: s.process is not None, notify=changed)
    canAct = Property(
        bool,
        lambda s: bool(s.projects.store and not s.projects.busy and not s.busy),
        notify=changed,
    )
    targets = Property(
        "QVariantList",
        lambda s: (
            [
                dict(id=d["version_id"], label="dataset · " + d["version_id"][-8:])
                for d in s.projects.draft["datasets"]
            ]
            + [
                dict(
                    id=r["id"],
                    label=(
                        "report"
                        if "export" in r
                        else "workflow"
                        if r.get("neural", {}).get("schema") == "WorkflowRun/v1"
                        else "profile"
                        if "profile" in r
                        else "record"
                    )
                    + " · "
                    + r["id"][-8:],
                )
                for r in s.projects.draft["results"]
            ]
        ),
        notify=changed,
    )
    graph = Property("QVariantMap", lambda s: s.graph_result, notify=changed)
    preview = Property("QVariantMap", lambda s: s.preview_result, notify=changed)
    openedBundle = Property("QVariantMap", lambda s: s.opened, notify=changed)
    report = Property("QVariantMap", lambda s: s.result, notify=changed)
    errorText = Property(str, lambda s: s._error, notify=changed)
    message = Property(str, lambda s: s._message, notify=changed)

    def fail(self, e):
        self._error = project_error_text(e)
        self.changed.emit()

    def start(self, action, request):
        if not self.canAct:
            return
        try:
            if (
                action in ("preview", "bundle")
                and self.projects.draft != self.projects.store.state
            ):
                raise ProjectError(
                    "Önce projeyi kaydedin; lineage yalnız durable commit kayıtlarını okur."
                )
            self.cache.mkdir(parents=True, exist_ok=True)
            request.update(
                project=str(self.projects.store.root),
                commit_id=self.projects.store.commit_id,
            )
            store = self.projects.store
            request["project_view"] = dict(
                state=copy.deepcopy(store.state),
                manifest=copy.deepcopy(store.manifest),
                commit_id=store.commit_id,
                root=str(store.root),
                paths={
                    uri: str(store.path(uri)).replace(
                        "/proc/self/", f"/proc/{os.getpid()}/", 1
                    )
                    for uri in list(store.manifest["artifacts"])
                    + ["sources", "snapshots"]
                },
            )
            self.workspace = tempfile.mkdtemp(prefix="repro-", dir=self.cache)
            ctx = mp.get_context("spawn")
            self.cancel_event = ctx.Event()
            self.connection, child = ctx.Pipe()
            self.action = action
            self.result = {}
            self._error = ""
            self.started = time.monotonic()
            self.cancel_at = None
            self.process = ctx.Process(
                target=worker,
                args=(
                    action,
                    request,
                    self.workspace,
                    self.cancel_event,
                    child,
                    self.budget,
                ),
            )
            self.projects.dataset_active = True
            if not start_controller(self, child):
                return
            child.close()
            self.changed.emit()
        except (ValueError, OSError, TypeError, KeyError) as e:
            self.cleanup()
            self.fail(e)

    @Slot(str, bool)
    def inspect(self, focus, include_data):
        self.selected = focus
        self.preview_result = {}
        self.start("preview", dict(focus=focus, include_data=include_data))

    @Slot(str)
    def exportBundle(self, destination):
        if not self.preview_result:
            self.fail(ProjectError("Önce redaction/data inclusion önizlemesi gerekir."))
            return
        p = self.preview_result
        self.start(
            "bundle",
            dict(
                focus=p["focus"],
                include_data=p["include_data"],
                preview_hash=p["preview_hash"],
                destination=destination,
            ),
        )

    @Slot(str)
    def openBundle(self, path):
        self.archive = path
        self.opened = {}
        self.start("open", dict(archive=path))

    @Slot(bool, str, str)
    def rerun(self, use_project, mode, destination):
        if not self.opened:
            self.fail(ProjectError("Önce bundle açıp hash doğrulayın."))
            return
        if use_project is not True and not self.opened["manifest"]["include_data"]:
            self.fail(
                ProjectError(
                    "Reference-only bundle için açık yerel proje erişimi gerekir."
                )
            )
            return
        self.start(
            "rerun",
            dict(
                archive=self.archive,
                fingerprint=self.opened["fingerprint"],
                data_project=str(self.projects.store.root) if use_project else "",
                mode=mode,
                destination=destination,
            ),
        )

    @Slot(str)
    def selectNode(self, ident):
        try:
            node = next(
                n for n in self.graph_result.get("nodes", []) if n["id"] == ident
            )
            self.result = dict(selected_node=node)
            self.changed.emit()
        except StopIteration:
            self.fail(ProjectError("Graph düğümü bulunamadı."))

    @Slot()
    def cancel(self):
        if self.cancel_event:
            self.cancel_event.set()
            self.cancel_at = self.cancel_at or time.monotonic()
        self.changed.emit()

    def cleanup(self):
        if self.process:
            if self.process.is_alive():
                self.process.kill()
            self.process.join(timeout=2)
        if self.connection:
            self.connection.close()
        self.process = self.connection = self.cancel_event = None
        if self.workspace:
            shutil.rmtree(self.workspace, ignore_errors=True)
        self.workspace = None
        self.projects.dataset_active = False

    def poll(self):
        if not self.process:
            return
        try:
            if time.monotonic() - self.started > self.budget.max_wall_seconds:
                self.cancel()
            if (
                self.cancel_at
                and time.monotonic() - self.cancel_at
                > self.budget.cancel_grace_ms / 1000
            ):
                raise ProjectError("Repro iptal/timeout; önceki kayıtlar korundu.")
            if self.connection.poll():
                kind, value = self.connection.recv()
                self.cleanup()
                if kind != "result":
                    raise ProjectError(
                        value
                        if kind == "error"
                        else self._error or "Repro iptal; başarı sayılmadı."
                    )
                self.result = value
                if self.action == "preview":
                    self.preview_result = value
                    self.graph_result = value["lineage"]
                    self._message = "Kayıtlı lineage ve redaction önizlemesi hazır; hesap/re-run yapılmadı."
                elif self.action == "open":
                    self.opened = value
                    self.graph_result = value["lineage"]
                    self._message = "Bundle hashleri doğrulandı. Açmak re-run değildir; ortam uyumu re-run başında ayrıca doğrulanır."
                else:
                    self._message = (
                        "Repro "
                        + self.action
                        + " tamamlandı; sonuç kapsamını ve karşılaştırma farklarını inceleyin."
                    )
                    if not self.projects.readOnly:
                        refs = (
                            self.preview_result.get("references", [])
                            if self.action == "bundle"
                            else self.opened.get("manifest", {}).get("references", [])
                        )
                        versions = {
                            d["version_id"] for d in self.projects.draft["datasets"]
                        }
                        self.projects.draft["results"].append(
                            dict(
                                id="result:" + uid(),
                                dataset_version_ids=[
                                    r["version_id"]
                                    for r in refs
                                    if r["version_id"] in versions
                                ],
                                seed=None,
                                capability_id="repro.bundle"
                                if self.action == "bundle"
                                else "repro.verify",
                                export=copy.deepcopy(value),
                            )
                        )
                        self._message += (
                            " Receipt için projeyi kaydedin; kaynak değişmedi."
                        )
                self.projects.changed.emit()
                self.changed.emit()
            elif not self.process.is_alive():
                raise ProjectError("Repro worker sonuçsuz kapandı; başarılı sayılmadı.")
        except (ValueError, OSError, TypeError, KeyError, EOFError) as e:
            self.cleanup()
            self.fail(e)

    def shutdown(self):
        self.timer.stop()
        self.cleanup()
