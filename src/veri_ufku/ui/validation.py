"""Separate development and final-test actions, with durable journal before exposure."""

import copy
import json
import multiprocessing as mp
import os
import tempfile
import time

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.jobs.admission import start_controller
from veri_ufku.modeling.validation import ValidationSpec
from veri_ufku.modeling.worker import validation_entry
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.validation_store import (
    choice,
    complete,
    load_run,
    prior_uses,
    reserve_test,
)
from veri_ufku.ui.preparation import PreparationController


class ValidationController(PreparationController):
    validationChanged = Signal()
    selectFamily = Signal(str, str)
    selectUncertainty = Signal(str)

    def __init__(self, data, projects, preparation, cache, budget, parent=None):
        super().__init__(data, projects, cache, budget, parent)
        self.changed.connect(self.validationChanged)
        self.preparation = preparation
        preparation.changed.connect(self.changed)
        self.stage = None
        self.test_use_id = None
        self.pending_result = None
        self._invalid = []
        self._message = "Hazırlama planını oluşturun; kayıt yapısını ve tahmin bağlamını seçin. Final test ayrı değerlendirilir."

    summaryReport = Property(
        "QVariantMap", lambda self: self.ui_report(), notify=validationChanged
    )

    def ui_report(self):
        if not self.result:
            return {}
        value = {
            k: v
            for k, v in self.result.items()
            if k
            in (
                "uncertainty",
                "mode",
                "baseline",
                "default_reason",
                "estimated_cost",
                "cv_summary",
                "run_id",
                "regression",
                "classification",
                "classes",
                "decision",
                "decision_validation",
                "external_test_use_known",
                "selected_model",
                "interpretation",
                "selection_rule",
            )
        }
        if self.result.get("regression"):
            value["comparison"] = [
                dict(
                    model=c["model"],
                    cv_mae=c["cv_mae"],
                    validation_metrics=c["evaluations"][0]["metrics"],
                )
                for c in self.result["comparison"]
            ]
        if self.result.get("classification"):
            value["decision"] = {
                k: v
                for k, v in self.result["decision"].items()
                if k != "validation_row_ids"
            }
            value["decision_validation"] = {
                k: v
                for k, v in (self.result.get("decision_validation") or {}).items()
                if k not in ("fit_row_ids", "fitted_parameters")
            }
            value["comparison"] = [
                dict(
                    model=c["model"],
                    cv_f1=c["cv_f1"],
                    validation_metrics=c["evaluations"][0]["metrics"],
                )
                for c in self.result["comparison"]
            ]
        value["plan"] = {
            k: v for k, v in self.result["plan"].items() if k != "membership"
        }
        value["evaluations"] = [
            {
                k: v
                for k, v in e.items()
                if k not in ("fit_row_ids", "fitted_parameters")
                and not (
                    e["scope"].startswith("cv:")
                    and k
                    in (
                        "predictions",
                        "prediction_coverage",
                        "curves",
                        "per_class",
                        "confusion_matrix",
                    )
                )
            }
            for e in self.result["evaluations"]
        ]
        return value

    invalidFolds = Property(
        "QVariantList", lambda self: self._invalid, notify=validationChanged
    )
    savedRuns = Property(
        "QVariantList",
        lambda self: [
            dict(
                id=r["id"],
                label=r["baseline"]["mode"] + " · " + r["baseline"]["run_id"][-8:],
            )
            for r in self.projects.draft["results"]
            if "baseline" in r
        ],
        notify=validationChanged,
    )
    testHistory = Property(
        "QVariantList",
        lambda self: [
            dict(
                r["test_use"],
                id=r["id"],
                subsequent_choices=[
                    c["model_choice"]["run_id"]
                    for c in self.projects.draft["results"]
                    if "model_choice" in c
                    and r["id"] in c["model_choice"]["prior_test_use_ids"]
                ],
            )
            for r in self.projects.draft["results"]
            if "test_use" in r
        ],
        notify=validationChanged,
    )
    choiceHistory = Property(
        "QVariantList",
        lambda self: [
            dict(
                r["model_choice"],
                id=r["id"],
                decision=next(
                    (
                        b["baseline"].get("decision", {})
                        for b in self.projects.draft["results"]
                        if b.get("baseline", {}).get("run_id")
                        == r["model_choice"]["run_id"]
                    ),
                    {},
                ),
            )
            for r in self.projects.draft["results"]
            if r.get("model_choice", {}).get("classification")
        ],
        notify=validationChanged,
    )

    cancelable = Property(
        bool,
        lambda self: bool(
            self.process or self.future and self.stage in ("choice", "reserve")
        ),
        notify=validationChanged,
    )
    canRun = Property(
        bool,
        lambda self: bool(
            self.preparation.current
            and self.preparation.result
            and not self.preparation.result["blockers"]
            and self.preparation.result["spec"]["purpose"]
            in ("regression", "classification")
            and not self.busy
            and not self.projects.busy
            and not self.projects.readOnly
        ),
        notify=validationChanged,
    )
    canTest = Property(
        bool,
        lambda self: bool(
            self.current
            and self.result["mode"] == "development"
            and not self.busy
            and not self.projects.busy
            and not self.projects.readOnly
        ),
        notify=validationChanged,
    )

    def selected_source(self):
        return (
            self.preparation.selected_source() if hasattr(self, "preparation") else None
        )

    def current_binding(self):
        b = super().current_binding()
        return (*b, (self.preparation.result or {}).get("plan", {}).get("version_id"))

    def family_diagnostics(self):
        if not self.result or not (
            self.result.get("regression") or self.result.get("classification") or {}
        ).get("family_options"):
            return {}
        metadata = self.result["evaluations"][0]["fitted_parameters"]
        value = {
            k: v
            for k, v in metadata.items()
            if k
            not in (
                "fit_row_ids",
                "preprocessing",
                "child_preprocessing",
                "oof",
                "meta_training_row_ids",
            )
        }
        value["fit_n"] = len(metadata.get("fit_row_ids", []))
        value["preprocessing"] = {
            ident: {
                k: (v[:5] if k == "categories" else v)
                for k, v in state.items()
                if k != "fit_row_ids"
            }
            for ident, state in metadata.get("preprocessing", {}).items()
        }
        value["oof"] = [
            dict(
                fold=r["fold"],
                fit_n=len(r["fit_row_ids"]),
                prediction_n=len(r["prediction_row_ids"]),
            )
            for r in metadata.get("oof", [])
        ]
        return value

    familyDiagnostics = Property(
        "QVariantMap", lambda self: self.family_diagnostics(), notify=validationChanged
    )

    @Slot(str, result="QVariantList")
    def familyMethods(self, purpose):
        from veri_ufku.domain.capabilities import CAPABILITIES, availability
        from veri_ufku.modeling.family_contracts import support

        prefix = "model.family." + purpose + "."
        return [
            dict(
                id=ident.removeprefix(prefix).replace("-", "_"),
                label=ident.removeprefix(prefix).replace("-", " "),
                enabled=availability(capability)[0],
                reason=availability(capability)[1],
                support=support(ident.removeprefix(prefix).replace("-", "_"), purpose),
            )
            for ident, capability in CAPABILITIES.items()
            if ident.startswith(prefix)
        ]

    @Slot(str, str)
    def createFamily(self, protocol, config):
        try:
            value = json.loads(config)
            method = value.pop("method")
            purpose = (self.preparation.result or {}).get("spec", {}).get("purpose")
            value.update(candidates=["baseline", method], explicit_model=method)
            if purpose == "classification":
                self.createClassification(protocol, json.dumps(value))
            elif purpose == "regression":
                self.createRegression(protocol, json.dumps(value))
            else:
                raise ProjectError("Önce supervised hazırlık oluşturun.")
        except (ProjectError, ValueError, TypeError, KeyError) as error:
            self.fail(error)

    @Slot(str)
    def create(self, value):
        if not self.canRun:
            return self.fail(
                ProjectError(
                    "Güncel, engelsiz regresyon/sınıflandırma hazırlığı ve yazılabilir proje gerekir; bu protokol engelli."
                )
            )
        try:
            parameters = ValidationSpec.from_dict(json.loads(value))
            parameters.resolved(self.preparation.result)
            self.start_request(
                parameters.data(), copy.deepcopy(self.preparation.result), "development"
            )
        except (ValueError, TypeError, KeyError, OSError) as error:
            self.fail(error)

    @Slot(str, str)
    def createRegression(self, protocol, config):
        try:
            from veri_ufku.modeling.regression import settings

            if (
                not self.canRun
                or self.preparation.result["spec"]["purpose"] != "regression"
            ):
                raise ProjectError(
                    "Önce engelsiz sayısal hedef hazırlama planı oluşturun."
                )
            parameters = ValidationSpec.from_dict(json.loads(protocol))
            parameters.resolved(self.preparation.result)
            regression = settings(json.loads(config))
            self.start_request(
                parameters.data(),
                copy.deepcopy(self.preparation.result),
                "development",
                regression=regression,
            )
        except (ValueError, TypeError, KeyError, OSError) as error:
            self.fail(error)

    @Slot(str, str)
    def createClassification(self, protocol, config):
        try:
            from veri_ufku.modeling.classification import settings

            if (
                not self.canRun
                or self.preparation.result["spec"]["purpose"] != "classification"
            ):
                raise ProjectError(
                    "Önce engelsiz kategori hedef hazırlama planı oluşturun."
                )
            parameters = ValidationSpec.from_dict(json.loads(protocol))
            parameters.resolved(self.preparation.result)
            category = settings(json.loads(config))
            self.start_request(
                parameters.data(),
                copy.deepcopy(self.preparation.result),
                "development",
                classification=category,
            )
        except (ValueError, TypeError, KeyError, OSError) as error:
            self.fail(error)

    @Slot(str, result="QVariantList")
    def uncertaintyMethods(self, purpose):
        from veri_ufku.domain.capabilities import CAPABILITIES, availability

        return [
            dict(
                id=c.capability_id.removeprefix("model.uncertainty."),
                label=c.method,
                enabled=availability(c)[0],
            )
            for c in CAPABILITIES.values()
            if c.capability_id.startswith("model.uncertainty.")
            and c.input_schema.startswith(purpose + ";")
        ]

    @Slot(str, str)
    def createUncertainty(self, protocol, value):
        try:
            from veri_ufku.modeling.uncertainty import UncertaintySpec

            if not self.canRun:
                raise ProjectError("Önce engelsiz supervised hazırlık gerekir.")
            purpose = self.preparation.result["spec"]["purpose"]
            spec = UncertaintySpec.from_dict(json.loads(value), purpose)
            if purpose == "classification":
                self.createClassification(
                    protocol,
                    json.dumps(
                        dict(
                            candidates=["baseline", spec.model],
                            positive_class=spec.positive_class,
                            uncertainty=spec.data(),
                        )
                    ),
                )
            else:
                # quantile is a dedicated uncertainty template, not a point-only family promise.
                self.createRegression(
                    protocol,
                    json.dumps(
                        dict(
                            candidates=[
                                "baseline",
                                "ridge" if spec.model == "quantile" else spec.model,
                            ],
                            uncertainty=spec.data(),
                        )
                    ),
                )
        except (ValueError, TypeError, KeyError, OSError) as error:
            self.fail(error)

    @Slot()
    def evaluateTest(self):
        if not self.canTest:
            return self.fail(
                ProjectError(
                    "Güncel kayıtlı geliştirme koşusu seçin; desteklenmeyen/eski protokol engelli."
                )
            )
        try:
            old = self.result
            p = dict(spec=old["preparation_spec"], plan=old["pipeline"])
            self.start_request(
                old["spec"],
                p,
                "final",
                old,
                old.get("regression"),
                old.get("classification"),
            )
        except (ValueError, TypeError, KeyError, OSError) as error:
            self.fail(error)

    def start_request(
        self, parameters, p, mode, baseline=None, regression=None, classification=None
    ):
        d = self.selected_source()
        if d["version_id"] != p["spec"]["source_version"]:
            raise ProjectError(
                "Hazırlama kaynağını kayıtlı koşunun kaynak sürümüne getirin."
            )
        fp = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]
        self.revision += 1
        run_id = "run:" + uid()
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
            snapshot_uri=d["snapshot_uri"],
            source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
            history_state=copy.deepcopy(self.projects.draft),
            config_revision=self.revision,
            preparation=p,
            mode=mode,
            run_id=run_id,
            prior_test_use_ids=prior_uses(self.projects.draft),
        )
        if regression:
            self.request["regression"] = regression
            if baseline:
                self.request["selected_model"] = baseline["selected_model"]
        if classification:
            self.request["classification"] = classification
            if baseline:
                self.request["selected_model"] = baseline["selected_model"]
                self.request["decision"] = copy.deepcopy(baseline["decision"])
        self.parameters = parameters
        self.binding = self.current_binding()
        self.pending_result = None
        self.test_use_id = None
        self._invalid = []
        self._error = ""
        self.projects.dataset_active = True
        if mode == "final":
            self.request.update(
                expected_split_id=baseline["plan"]["split_id"],
                expected_protocol_id=baseline["plan"]["protocol_id"],
            )
            if baseline.get("uncertainty"):
                stored = next(
                    r["baseline"]
                    for r in self.projects.draft["results"]
                    if r.get("baseline", {}).get("run_id") == baseline["run_id"]
                )
                self.request["frozen_uncertainty_package"] = dict(
                    path=str(
                        self.projects.store.path(stored["model_package_uri"])
                    ).replace("/proc/self/", f"/proc/{os.getpid()}/", 1),
                    fingerprint=stored["model_package_fingerprint"],
                )
            self.stage = "reserve"
            self.future = self.projects.executor.submit(
                reserve_test,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                copy.deepcopy(baseline),
                run_id,
            )
        else:
            self.stage = "choice"
            self.future = self.projects.executor.submit(
                choice,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                d["version_id"],
                parameters,
                p["plan"]["version_id"],
                run_id,
                regression,
                classification,
            )
        self._message = "Değerlendirme protokolü/seçim geçmişi projeye kaydediliyor…"
        self.projects.changed.emit()
        self.changed.emit()

    def launch(self):
        self.request["history_state"] = copy.deepcopy(self.projects.draft)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.workspace = tempfile.mkdtemp(prefix="baseline-", dir=self.cache)
        ctx = mp.get_context("spawn")
        self.cancel_event = ctx.Event()
        self.connection, sender = ctx.Pipe(duplex=False)
        self.process = ctx.Process(
            target=validation_entry,
            args=(
                self.request,
                self.parameters,
                self.workspace,
                self.cancel_event,
                sender,
                self.budget,
            ),
        )
        self.started = time.monotonic()
        self.cancel_time = None
        if not start_controller(self, sender):
            return
        sender.close()
        self._message = (
            "Yalnız train/fold fit ediliyor; final test geliştirme CV'sine katılmıyor."
        )

    @Slot()
    def cancel(self):
        if self.future and self.stage in ("choice", "reserve"):
            self.abort_pending = True
            self._message = "İptal isteniyor…"
            self.changed.emit()
        else:
            super().cancel()

    def finish(self, status, result=None, invalid=None):
        workspace, self.workspace = self.workspace, None
        self.release()
        self.workspace = workspace
        self.pending_result = result
        self._invalid = invalid or []
        self.finished_status = status
        self._message = (
            "Sonuç ve defter atomik kaydediliyor; bu kısa kayıt adımı iptal edilemez."
        )
        self.projects.dataset_active = True
        self.stage = "complete"
        self.future = self.projects.executor.submit(
            complete,
            self.projects.store,
            copy.deepcopy(self.projects.draft),
            result,
            self.test_use_id,
            status,
            self._invalid,
            run_id=self.request["run_id"],
        )
        self.changed.emit()

    def poll(self):
        if self.future:
            if not self.future.done():
                return
            future, self.future = self.future, None
            try:
                value = future.result()
                if self.stage == "open":
                    self.show_run(value)
                    self.stage = None
                    self.projects.dataset_active = False
                    self.projects.changed.emit()
                    return
                if self.stage == "reserve":
                    value, self.test_use_id = value
                self.projects.draft = value
                self.projects.saved = copy.deepcopy(value)
                if self.stage in ("reserve", "choice"):
                    if (
                        getattr(self, "abort_pending", False)
                        or self.binding != self.current_binding()
                    ):
                        self.abort_pending = False
                        self.finish("canceled")
                    else:
                        self.launch()
                else:
                    if self.pending_result and self.binding == self.current_binding():
                        self.result = dict(
                            self.pending_result, project_root=self.binding[0]
                        )
                        self.result_binding = self.binding
                        self._message = (
                            "Final test kaydedildi. Önceki test kullanımından sonraki seçim/değerlendirme keşifseldir; bağımsız değerlendirme gerekir."
                            if self.result["mode"] == "final"
                            else "Validation/CV sonucu kaydedildi. Aday seçimi yalnız geliştirme CV; kategori eşiği ayrı validation kararıdır. Final test ayrı kalır."
                        )
                    elif self.finished_status == "canceled":
                        self._message = "İptal edildi; koşu başarılı sayılmadı. Test rezervasyonu varsa defterde korunur."
                    elif self.finished_status == "stale":
                        self._message = (
                            "Eski veri/ayar sonucu güncel koşuya bağlanmadı."
                        )
                    self.release()
                    self.stage = None
            except (ValueError, OSError, TypeError, KeyError) as error:
                self.release()
                self.pending_result = None
                self._message = "Koşu/kayıt başarısız; final sonuç gösterilmedi. Varsa pending test kaydı korunur."
                self.fail(error)
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
            self.finish("canceled")
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
            if self.cancel_event.is_set() or kind == "canceled":
                self.finish("canceled")
            elif self.binding != self.current_binding():
                self.finish("stale")
            elif kind == "error":
                self._error = value["message"]
                self.finish("failed", invalid=value["invalid_folds"])
            else:
                self.finish("completed", result=value)
            return
        if self.process and not self.process.is_alive() and not self.connection.poll():
            self._error = "Baseline süreci durdu; yarım sonuç kabul edilmedi."
            self.finish("failed")

    @Slot(str)
    def openRun(self, ident):
        if self.busy or self.projects.busy:
            return
        try:
            record = copy.deepcopy(
                next(
                    r
                    for r in self.projects.draft["results"]
                    if r["id"] == ident and "baseline" in r
                )
            )
            if record["baseline"].get("details_uri"):
                self.stage = "open"
                self.future = self.projects.executor.submit(
                    load_run, self.projects.store, record
                )
                self.projects.dataset_active = True
                self.projects.changed.emit()
                self.changed.emit()
            else:
                self.show_run(record["baseline"])
        except (StopIteration, ValueError, KeyError) as error:
            self.fail(error)

    def show_run(self, value):
        self.result = dict(value, project_root=str(self.projects.store.root))
        self.result_binding = (
            self.current_binding()
            if value["dataset_version"] == self.sourceVersion
            and value["origin_version"] == (self.data.dataset() or {}).get("version_id")
            else None
        )
        self._error = ""
        self._message = "Kayıtlı koşu açıldı; test geçmişi proje boyunca korunur."
        self.changed.emit()

    def shutdown(self):
        # Complete any in-flight metadata transaction before project lock release.
        self.timer.stop()
        if self.process:
            self.cancel_event.set()
            self.finish("canceled")
        if self.future:
            try:
                value = self.future.result()
                if self.stage == "reserve":
                    value, self.test_use_id = value
                    value = complete(
                        self.projects.store,
                        value,
                        test_use_id=self.test_use_id,
                        status="canceled",
                    )
                if self.stage != "open":
                    self.projects.draft = value
                    self.projects.saved = copy.deepcopy(value)
            except (ValueError, OSError):
                pass
            self.future = None
        self.release()
