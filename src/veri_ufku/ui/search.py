"""Qt parent owns durable search checkpoints; worker is Qt-free and cannot publish ACTIVE."""

import copy
import json
import multiprocessing as mp
import os
import tempfile
import time
from dataclasses import replace

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.jobs.admission import start_controller
from veri_ufku.modeling.search_contracts import SearchSpec
from veri_ufku.modeling.validation import ValidationSpec
from veri_ufku.modeling.worker import search_entry
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.search_store import export_history, load_search, publish
from veri_ufku.storage.validation_store import choice, complete, prior_uses
from veri_ufku.ui.preparation import PreparationController


class SearchController(PreparationController):
    selectMethod = Signal(str)
    searchChanged = Signal()

    def __init__(
        self, data, projects, preparation, validation, cache, budget, parent=None
    ):
        super().__init__(data, projects, cache, budget, parent)
        self.changed.connect(self.searchChanged)
        self.preparation = preparation
        self.validation = validation
        self.active = None
        self.stage = None
        self._resume = None
        self._incoming = None
        self._pending_final = None
        self._finish_status = None
        self.last_received = 0
        self._message = "Önce hazırlık ve validation protokolünü seçin. Final test aramaya katılmaz."
        preparation.changed.connect(self.changed)

    def selected_source(self):
        return (
            self.preparation.selected_source() if hasattr(self, "preparation") else None
        )

    def current_binding(self):
        return (
            (
                *super().current_binding(),
                (self.preparation.result or {}).get("plan", {}).get("version_id"),
            )
            if hasattr(self, "preparation")
            else super().current_binding()
        )

    def summary(self, value):
        if not value:
            return {}
        return dict(
            status=value["status"],
            reason=value.get("reason", ""),
            search_id=value["search_id"],
            trial_counts={
                k: sum(t["status"] == k for t in value["trials"])
                for k in ("running", "completed", "failed", "pruned", "canceled")
            },
            trials=[
                dict(
                    id=t["id"],
                    scope=t["scope"],
                    method=t["parameters"]["method"],
                    parameters={
                        k: t["parameters"]["options"][k]
                        for k in {
                            p["name"]
                            for p in value["search_spec"]["space"]["parameters"]
                        }
                    },
                    status=t["status"],
                    metrics=t.get("metrics", {}),
                    feasible=t.get("feasible"),
                    reason=t.get("reason", ""),
                    folds_done=len(t["folds"]),
                )
                for t in value["trials"]
            ],
            outer=[
                dict(
                    scope=e["scope"],
                    metrics=e["metrics"],
                    fit_n=len(e["fit_row_ids"]),
                    evaluation_n=len(e["evaluation_row_ids"]),
                )
                for e in value["outer_evaluations"]
            ],
            curves=[
                dict(
                    kind=p["kind"],
                    x=p["x"],
                    parameter=p["parameter"],
                    value=p["value"],
                    metric=p["metric"],
                    scope=p["scope"],
                    training_n=[
                        len(f["fit_row_ids"]) if "fit_row_ids" in f else 0
                        for f in p["folds"]
                    ],
                )
                for p in value["curves"]
            ],
            recommended=value.get("recommended"),
            cost=value["estimated_cost"],
            prior_test_count=len(value["prior_test_use_ids"]),
            interpretation=value["interpretation"],
            elapsed_seconds=value["elapsed_seconds"],
            native_fit_reservations=value["native_fit_reservations"],
        )

    report = Property(
        "QVariantMap",
        lambda self: self.summary(self.result),
        notify=searchChanged,
    )
    historyReport = Property(
        "QVariantMap",
        lambda self: self.summary(self.active),
        notify=searchChanged,
    )
    canRun = Property(
        bool,
        lambda self: bool(
            self.projects.store
            and not self.busy
            and not self.projects.busy
            and self.preparation.current
            and self.preparation.result
            and self.preparation.result["spec"]["purpose"]
            in ("regression", "classification")
            and not self.preparation.result["blockers"]
        ),
        notify=searchChanged,
    )

    def registry_methods(self):
        from veri_ufku.domain.capabilities import CAPABILITIES, availability

        labels = {
            "grid": "Grid — tüm bounded kombinasyonlar",
            "random": "Random — unique seeded örnek",
            "bayesian": "Bayesian — optional Optuna TPE",
        }
        return [
            dict(
                id=ident.removeprefix("model.search."),
                label=labels[ident.removeprefix("model.search.")],
                enabled=availability(capability)[0],
            )
            for ident, capability in CAPABILITIES.items()
            if ident.startswith("model.search.")
        ]

    methods = Property(
        "QVariantList", lambda self: self.registry_methods(), constant=True
    )

    def saved(self):
        latest = {}
        for r in self.projects.draft["results"]:
            if "search" in r:
                latest[r["search"]["search_id"]] = r
        return [
            dict(
                id=r["id"],
                label=r["search"]["search_spec"]["method"]
                + " · "
                + r["search"]["status"]
                + " · "
                + r["search"]["search_id"][-8:],
            )
            for r in latest.values()
        ]

    savedSearches = Property(
        "QVariantList", lambda self: self.saved(), notify=searchChanged
    )

    @Slot(str)
    def openSearch(self, ident):
        if self.busy:
            return
        record = next(
            (
                r
                for r in self.projects.draft["results"]
                if r["id"] == ident and "search" in r
            ),
            None,
        )
        if record:
            self.active = load_search(self.projects.store, record)
            if self.active["status"] == "completed":
                self.result = copy.deepcopy(self.active)
                self.result_binding = self.current_binding()
            self.changed.emit()

    @Slot(str, str, str)
    def start(self, protocol_json, search_json, resume_id=""):
        if not self.canRun:
            return self.fail(
                ProjectError("Geçerli hazırlık seçin; devam eden işi bekleyin.")
            )
        try:
            protocol = ValidationSpec.from_dict(json.loads(protocol_json))
            p = copy.deepcopy(self.preparation.result)
            protocol.resolved(p)
            spec = SearchSpec.from_dict(json.loads(search_json))
            pool = spec.candidates(p["spec"]["purpose"])
            d = self.selected_source()
            fp = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]
            resume = None
            if resume_id:
                record = next(
                    (
                        r
                        for r in self.projects.draft["results"]
                        if r["id"] == resume_id and "search" in r
                    ),
                    None,
                )
                if record is None or resume_id not in {r["id"] for r in self.saved()}:
                    raise ProjectError(
                        "Resume yalnız en yeni kalıcı checkpointten yapılır."
                    )
                resume = load_search(self.projects.store, record)
            if (
                spec.ram_bytes > self.budget.ram_bytes
                or spec.wall_seconds > self.budget.max_wall_seconds
            ):
                raise ProjectError(
                    "Arama bütçesi birleşik ComputeBudget sınırını aşıyor."
                )
            self.revision += 1
            self.binding = self.current_binding()
            self._resume = resume
            self.request = dict(
                path=str(self.projects.store.path(d["snapshot_uri"])).replace(
                    "/proc/self/", f"/proc/{os.getpid()}/", 1
                ),
                fingerprint={k: fp[k] for k in ("size", "sha256")},
                columns=copy.deepcopy(d["import_metadata"]["columns"]),
                semantic_metadata=copy.deepcopy(d.get("semantic_metadata", {})),
                row_count=d["import_metadata"]["row_count"],
                version_id=d["version_id"],
                origin_version=self.data.dataset()["version_id"],
                source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
                snapshot_uri=d["snapshot_uri"],
                config_revision=self.revision,
                history_state=copy.deepcopy(self.projects.draft),
                preparation=p,
                prior_test_use_ids=prior_uses(self.projects.draft),
                search_id=resume["search_id"] if resume else "search:" + uid(),
                run_id="run:" + uid(),
            )
            self.protocol = protocol.data()
            self.parameters = spec.data()
            self.active = resume
            self._error = ""
            self._pending_final = None
            self._finish_status = None
            self.cancel_time = None
            self._timed_out = False
            first = pool[0]
            config = dict(
                candidates=["baseline", first["method"]],
                explicit_model=first["method"],
                family_options=first["options"],
            )
            classification = p["spec"]["purpose"] == "classification"
            if classification:
                config["positive_class"] = p["target"]["class_distribution"][0]["label"]
            self.projects.dataset_active = True
            self.stage = "choice"
            self.future = self.projects.executor.submit(
                choice,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                d["version_id"],
                self.protocol,
                p["plan"]["version_id"],
                self.request["run_id"],
                None if classification else config,
                config if classification else None,
                self.request["search_id"],
            )
            self._message = (
                "Arama seçim kaydı kalıcı final kullanım defterine bağlanıyor…"
            )
            self.changed.emit()
        except (ValueError, TypeError, KeyError) as error:
            self.fail(error)

    def launch(self):
        self.request["history_state"] = copy.deepcopy(self.projects.draft)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.workspace = tempfile.mkdtemp(prefix="search-", dir=self.cache)
        ctx = mp.get_context("spawn")
        self.cancel_event = ctx.Event()
        self.connection, sender = ctx.Pipe(duplex=False)
        budget = replace(
            self.budget,
            ram_bytes=min(self.budget.ram_bytes, self.parameters["ram_bytes"]),
            max_wall_seconds=min(
                self.budget.max_wall_seconds, self.parameters["wall_seconds"]
            ),
        )
        self.process = ctx.Process(
            target=search_entry,
            args=(
                self.request,
                self.protocol,
                self.parameters,
                self.workspace,
                self.cancel_event,
                sender,
                budget,
                self._resume,
            ),
        )
        self.started = time.monotonic()
        self.last_received = self.started
        if not start_controller(self, sender):
            return
        sender.close()
        self.stage = "running"
        self._message = "İç CV tuning; dış CV evaluation. Final test kapalı."
        self.changed.emit()

    @Slot()
    def cancel(self):
        if self.future and self.stage == "choice":
            self.cancel_time = time.monotonic()
            self._message = "Başlangıç iptali bekleniyor…"
            self.changed.emit()
        elif self.process:
            self.cancel_event.set()
            self.cancel_time = self.cancel_time or time.monotonic()
            self._message = "İptal isteniyor; kalıcı checkpointler korunur."
            self.changed.emit()

    def final(self, data=None, status=None):
        if data is not None:
            self._pending_final = copy.deepcopy(data)
            self.stage = "final_publish"
            self._incoming = self._pending_final
            self.future = self.projects.executor.submit(
                publish,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                self._pending_final,
            )
        else:
            self._finish_status = status or "failed"
            self.stage = "complete"
            self.release()
            self.projects.dataset_active = True
            self.future = self.projects.executor.submit(
                complete,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                status=self._finish_status,
                run_id=self.request["run_id"],
            )
        self.changed.emit()

    def forced(self, status):
        if self.active is None:
            return self.final(status=status)
        data = copy.deepcopy(self.active)
        data["status"] = status
        data["elapsed_seconds"] += max(0, time.monotonic() - self.last_received)
        for trial in data["trials"]:
            if trial["status"] == "running":
                trial.update(
                    status="canceled"
                    if status in ("canceled", "budget_exhausted")
                    else "failed",
                    reason="worker forced stop; retry requires new attempt",
                )
        self.release()
        self.final(data)

    def poll(self):
        if self.future:
            if not self.future.done():
                return
            future, self.future = self.future, None
            try:
                state = future.result()
                if self.stage == "export":
                    self.stage = None
                    self.projects.dataset_active = False
                    self._message = (
                        "Trial geçmişi yeni safe JSON dosyasına export edildi."
                    )
                    self.changed.emit()
                    return
                self.projects.draft = state
                self.projects.saved = copy.deepcopy(state)
                if self.stage == "choice":
                    if self.cancel_time:
                        self.final(status="canceled")
                    else:
                        self.launch()
                elif self.stage in ("checkpoint", "final_publish"):
                    self.active = copy.deepcopy(self._incoming)
                    if self.stage == "final_publish":
                        status = (
                            "completed"
                            if self.active["status"] == "completed"
                            else "canceled"
                            if self.active["status"] in ("canceled", "budget_exhausted")
                            else "failed"
                        )
                        self.final(status=status)
                    else:
                        self.stage = "running"
                elif self.stage == "complete":
                    if (
                        self._finish_status == "completed"
                        and self._pending_final is not None
                    ):
                        self.result = copy.deepcopy(self._pending_final)
                        self.result_binding = self.binding
                    self.projects.dataset_active = False
                    self.stage = None
                    self._message = (
                        "Arama tamamlandı; öneri optimum garantisi değildir. Final test ayrı eylemdir."
                        if self._finish_status == "completed"
                        else "Arama durdu; trial geçmişi ve önceki sonuç/model korundu."
                    )
            except (ValueError, OSError, TypeError, KeyError) as error:
                self._error = str(error)
                self.release()
                self.projects.dataset_active = False
                self.stage = None
            self.projects.changed.emit()
            self.changed.emit()
            return
        if not self.process:
            return
        if time.monotonic() - self.started > self.parameters["wall_seconds"]:
            self._timed_out = True
            self.cancel()
        if (
            self.cancel_time
            and time.monotonic() - self.cancel_time > self.budget.cancel_grace_ms / 1000
        ):
            self.forced("budget_exhausted" if self._timed_out else "canceled")
            return
        if self.connection.poll():
            try:
                kind, value = self.connection.recv()
            except EOFError:
                kind, value = "error", "Search worker bağlantısı kapandı."
            if kind == "checkpoint":
                self.last_received = time.monotonic()
                self._incoming = value
                self.stage = "checkpoint"
                self.future = self.projects.executor.submit(
                    publish,
                    self.projects.store,
                    copy.deepcopy(self.projects.draft),
                    value,
                )
            elif kind == "result":
                if self.cancel_time and value["status"] == "completed":
                    value = dict(value, status="canceled")
                if self._timed_out and value["status"] == "canceled":
                    value = dict(value, status="budget_exhausted")
                self.final(value)
            elif kind == "canceled":
                self.forced("budget_exhausted" if self._timed_out else "canceled")
            else:
                self._error = value
                self.forced("failed")
            self.changed.emit()
            return
        if not self.process.is_alive():
            self._error = "Search worker beklenmeden durdu."
            self.forced("failed")

    @Slot(str, str)
    def applyRecommendation(self, protocol_json, positive):
        if self.busy or not self.result or self.result["status"] != "completed":
            return
        try:
            protocol = json.loads(protocol_json)
            if (
                protocol != self.result["protocol"]
                or (self.preparation.result or {}).get("spec")
                != self.result["preparation"]["spec"]
            ):
                raise ProjectError(
                    "Öneri için aynı hazırlık ve validation planı gerekir; final test dışında kalır."
                )
            selected = self.result["recommended"]
            config = dict(method=selected["method"], family_options=selected["options"])
            if self.result["preparation"]["spec"]["purpose"] == "classification":
                config["positive_class"] = positive
            if not self.validation.canRun:
                raise ProjectError(
                    "Model aktarımı için hazırlığın ve proje işlemlerinin hazır olmasını bekleyin."
                )
            self.validation.createFamily(protocol_json, json.dumps(config))
        except (ValueError, KeyError) as error:
            self.fail(error)

    @Slot(str)
    def exportHistory(self, target):
        if self.busy or self.projects.busy or self.active is None:
            return self.fail(ProjectError("Önce kayıtlı arama geçmişini açın."))
        self._error = ""
        self.stage = "export"
        self.projects.dataset_active = True
        self.future = self.projects.executor.submit(
            export_history, copy.deepcopy(self.active), target
        )
        self.changed.emit()
