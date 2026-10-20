"""Explicit typed workflow editor; parent alone publishes through ProjectStore."""

import copy
import json
import multiprocessing as mp
import shutil
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from veri_ufku.exports.files import publish as publish_file
from veri_ufku.jobs.admission import start_controller
from veri_ufku.operations.workflow_contracts import DAGSpec
from veri_ufku.operations.workflow_service import request_for, worker
from veri_ufku.storage.neural_store import load, publish
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.ui.projects import project_error_text


class WorkflowController(QObject):
    changed = Signal()

    def __init__(self, data, projects, cache, budget, parent=None):
        super().__init__(parent)
        self.data, self.projects, self.cache, self.budget = (
            data,
            projects,
            Path(cache),
            budget,
        )
        self.process = self.future = self.connection = self.cancel_event = None
        self.workspace = None
        self.spec = None
        self.active = None
        self._error = ""
        self._message = "DAG yalnız Dry-run veya Çalıştır eyleminde işler. Schedule mevcut değil; uygulama kapalıyken otomatik iş çalışmaz."
        self.stale = True
        self._root = None
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        projects.changed.connect(self.project_changed)
        data.changed.connect(self.changed)

    @Slot()
    def project_changed(self):
        root = str(self.projects.store.root) if self.projects.store else None
        if root != self._root and not self.busy:
            self._root = root
            self.spec = self.active = None
            self.stale = True
        self.changed.emit()

    busy = Property(
        bool, lambda s: s.process is not None or s.future is not None, notify=changed
    )
    canAct = Property(
        bool,
        lambda s: bool(
            s.projects.store
            and s.data.dataset()
            and not s.projects.readOnly
            and not s.projects.busy
            and not s.data.busy
            and not s.busy
        ),
        notify=changed,
    )
    errorText = Property(str, lambda s: s._error, notify=changed)
    message = Property(str, lambda s: s._message, notify=changed)
    graph = Property("QVariantMap", lambda s: s.spec or {}, notify=changed)
    nodes = Property(
        "QVariantList", lambda s: (s.spec or {}).get("nodes", []), notify=changed
    )
    report = Property("QVariantMap", lambda s: s.active or {}, notify=changed)
    staleResult = Property(bool, lambda s: s.stale, notify=changed)
    graphText = Property(
        str,
        lambda s: json.dumps(s.spec or {}, indent=2, ensure_ascii=False),
        notify=changed,
    )
    savedRuns = Property(
        "QVariantList",
        lambda s: [
            dict(
                id=r["id"],
                label=r["neural"]["status"] + " · " + r["neural"]["run_id"][-8:],
            )
            for r in s.projects.draft["results"]
            if r.get("neural", {}).get("schema") == "WorkflowRun/v1"
        ],
        notify=changed,
    )

    def fail(self, e):
        self._error = project_error_text(e)
        self.changed.emit()

    def update(self, spec):
        self.spec = DAGSpec.from_dict(spec).data()
        self.stale = True
        self._error = ""
        self.changed.emit()

    @Slot(str)
    def setGraph(self, text):
        if self.busy:
            return
        try:
            if len(text.encode()) > 65536:
                raise ProjectError("DAG64KiB sınırı.")
            self.update(json.loads(text))
        except (ValueError, TypeError, KeyError) as e:
            # Invalid edited content cannot silently run the previous recipe.
            self.spec = None
            self.stale = True
            self.fail(e)

    @Slot()
    def reset(self):
        if not self.canAct:
            return
        d = self.data.dataset()
        self.update(
            DAGSpec(
                [
                    dict(
                        id="source",
                        kind="source",
                        inputs={},
                        after=[],
                        params=dict(version_id=d["version_id"]),
                        method_version=1,
                    )
                ]
            ).data()
        )

    @Slot(str, str, str, str, str, str, str, bool)
    def addNode(self, kind, ident, upstream, model, column, target, value, confirmed):
        if self.busy or not self.spec:
            return
        try:
            inputs = (
                {} if kind == "source" else dict(data=dict(node=upstream, port="data"))
            )
            if kind == "predict":
                inputs["model"] = dict(node=model, port="model")
            params = {
                "source": dict(version_id=value),
                "quality": dict(column=column, fail_on_null=confirmed),
                "analysis": dict(column=column, ddof=1),
                "train": dict(feature=column, target=target, confirmed=confirmed),
                "predict": dict(prediction_column="col:" + uid()),
                "export": dict(format="parquet"),
                "transform": dict(
                    kind="rename", columns=[column], parameters=dict(name=value)
                ),
            }[kind]
            spec = copy.deepcopy(self.spec)
            spec["nodes"].append(
                dict(
                    id=ident,
                    kind=kind,
                    inputs=inputs,
                    after=[],
                    params=params,
                    method_version=1,
                )
            )
            self.update(spec)
        except (ValueError, KeyError, TypeError) as e:
            self.fail(e)

    @Slot(str, str, str, str)
    def connectPorts(self, target, input_port, source, output_port):
        if self.busy or not self.spec:
            return
        try:
            spec = copy.deepcopy(self.spec)
            node = next(n for n in spec["nodes"] if n["id"] == target)
            node["inputs"][input_port] = dict(node=source, port=output_port)
            self.update(spec)
        except (ValueError, KeyError, TypeError, StopIteration) as e:
            self.fail(e)

    @Slot(str, str)
    def setAfter(self, target, parents):
        if self.busy or not self.spec:
            return
        try:
            spec = copy.deepcopy(self.spec)
            node = next(n for n in spec["nodes"] if n["id"] == target)
            node["after"] = [p.strip() for p in parents.split(",") if p.strip()]
            self.update(spec)
        except (ValueError, KeyError, TypeError, StopIteration) as e:
            self.fail(e)

    @Slot(str)
    def removeNode(self, ident):
        if self.busy or not self.spec:
            return
        try:
            spec = copy.deepcopy(self.spec)
            spec["nodes"] = [n for n in spec["nodes"] if n["id"] != ident]
            self.update(spec)
        except (ValueError, KeyError, TypeError) as e:
            self.fail(e)

    @Slot()
    def fromChain(self):
        if not self.canAct:
            return
        try:
            state = self.projects.draft
            d = self.data.dataset()
            chain = []
            while d.get("parent_version_ids"):
                operation = next(
                    (
                        o["spec"]
                        for o in state["operations"]
                        if o.get("output_version_id") == d["version_id"] and "spec" in o
                    ),
                    None,
                )
                if not operation or operation["kind"] not in (
                    "rename",
                    "drop",
                    "filter",
                ):
                    raise ProjectError(
                        "DAG zincir köprüsü yalnız rename/drop/filter destekler; diğer adımlar için ayrı source snapshot seçin."
                    )
                chain.append(operation)
                d = next(
                    v
                    for v in state["datasets"]
                    if v["version_id"] == d["parent_version_ids"][0]
                )
            nodes = [
                dict(
                    id="source",
                    kind="source",
                    inputs={},
                    after=[],
                    params=dict(version_id=d["version_id"]),
                    method_version=1,
                )
            ]
            for i, op in enumerate(reversed(chain)):
                nodes.append(
                    dict(
                        id="step-" + str(i),
                        kind="transform",
                        inputs=dict(data=dict(node=nodes[-1]["id"], port="data")),
                        after=[],
                        params=dict(
                            kind=op["kind"],
                            columns=op["column_ids"],
                            parameters=op["parameters"],
                        ),
                        method_version=1,
                    )
                )
            self.update(DAGSpec(nodes).data())
        except (ValueError, KeyError, TypeError, StopIteration) as e:
            self.fail(e)

    @Slot(str)
    def saveGraph(self, destination):
        if self.busy or not self.spec or not self.projects.store:
            return
        try:
            with tempfile.TemporaryDirectory() as work:
                p = Path(work) / "dag.json"
                p.write_text(json.dumps(self.spec, ensure_ascii=False, indent=2))
                publish_file(p, Path(destination), self.projects.store.root)
            self._message = "Declarative DAG kaydedildi; veri/model/secret gömülmedi. Mevcut dosya ezilmez."
            self.changed.emit()
        except (ValueError, OSError) as e:
            self.fail(e)

    @Slot(bool, bool, str, str)
    def start(self, dry_run, allow_export, output_dir, token):
        if not self.canAct:
            return
        try:
            if not self.spec:
                raise ProjectError(
                    "Geçerli DAG gerekir; eski tarif sessiz çalıştırılmaz."
                )
            self.cache.mkdir(parents=True, exist_ok=True)
            request = request_for(
                self.projects.store,
                self.projects.draft,
                self.spec,
                self.cache,
                output_dir,
                allow_export,
                dry_run,
                token,
            )
            self._error = ""
            self.workspace = tempfile.mkdtemp(prefix="dag-work-", dir=self.cache)
            ctx = mp.get_context("spawn")
            self.cancel_event = ctx.Event()
            self.connection, child = ctx.Pipe()
            self.process = ctx.Process(
                target=worker,
                args=(
                    request,
                    copy.deepcopy(self.spec),
                    self.workspace,
                    self.cancel_event,
                    child,
                    self.budget,
                ),
            )
            self.started = time.monotonic()
            self.cancel_at = None
            self.projects.dataset_active = True
            if not start_controller(self, child):
                return
            child.close()
            self._message = "DAG çalışıyor; her node kaynak/config/yöntem/ortam ve ComputeBudget ile doğrulanır."
            self.changed.emit()
        except (ValueError, KeyError, TypeError, OSError) as e:
            self.cleanup()
            self.projects.dataset_active = False
            self.fail(e)

    @Slot(str)
    def openRecord(self, ident):
        if self.busy or self.projects.busy:
            return
        try:
            record = next(
                r
                for r in self.projects.draft["results"]
                if r["id"] == ident
                and r.get("neural", {}).get("schema") == "WorkflowRun/v1"
            )
            self.active = load(self.projects.store, record)
            self.spec = copy.deepcopy(self.active["workflow_spec"])
            self.stale = True
            self._message = "Geçmiş sonuç: açmak çalıştırmaz. Güncellik için yeniden dry-run/çalıştır; verified_at geçmiş erişim zamanıdır."
            self.changed.emit()
        except (ValueError, OSError, KeyError, StopIteration) as e:
            self.fail(e)

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

    def poll(self):
        if self.future:
            if not self.future.done():
                return
            future, self.future = self.future, None
            try:
                state = future.result()
                self.projects.draft = state
                self.projects.saved = copy.deepcopy(state)
                self.active = load(self.projects.store, state["results"][-1])
                self.stale = False
                self._message = (
                    "DAG "
                    + self.active["status"]
                    + " · doğrulama zamanı kaydedildi. Ana dataset head değişmedi."
                )
            except (ValueError, OSError, KeyError, TypeError) as e:
                self.fail(e)
            self.projects.dataset_active = False
            self.projects.changed.emit()
            self.changed.emit()
            return
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
                raise ProjectError(
                    "DAG iptal/timeout; önceki yayınlar korundu, başarı sayılmadı."
                )
            if self.connection.poll():
                kind, value = self.connection.recv()
                self.cleanup()
                if kind != "result":
                    raise ProjectError(
                        value if kind == "error" else "DAG canceled; başarı sayılmadı."
                    )
                self.future = self.projects.executor.submit(
                    publish,
                    self.projects.store,
                    copy.deepcopy(self.projects.draft),
                    value,
                )
                self.changed.emit()
            elif not self.process.is_alive():
                raise ProjectError("DAG worker sonuçsuz kapandı; başarı sayılmadı.")
        except (ValueError, OSError, EOFError, TypeError) as e:
            self.cleanup()
            self.projects.dataset_active = False
            self.fail(e)

    def shutdown(self):
        if self.future:
            try:
                self.future.result(timeout=20)
            except (ValueError, OSError, TimeoutError):
                pass
        self.cleanup()
