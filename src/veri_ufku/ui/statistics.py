"""Qt presentation for statistical preflight, spawn computation and durable results."""

import copy
import json
import multiprocessing as mp
import os
import shutil
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from veri_ufku.domain.capabilities import CAPABILITIES, availability, get_capability
from veri_ufku.jobs.admission import start_controller
from veri_ufku.statistics.bayes_contracts import BAYES_LABELS, BAYES_METHODS
from veri_ufku.statistics.causal_contracts import CAUSAL_LABELS, CAUSAL_METHODS
from veri_ufku.statistics.contracts import (
    ADVANCED_METHODS,
    LABELS,
    METHODS,
    AnalysisSpec,
)
from veri_ufku.statistics.dimension_contracts import DIMENSION_LABELS, DIMENSION_METHODS
from veri_ufku.statistics.experiment_contracts import (
    EXPERIMENT_LABELS,
    EXPERIMENT_METHODS,
)
from veri_ufku.statistics.model_contracts import MODEL_LABELS, MODEL_METHODS
from veri_ufku.statistics.resampling_contracts import (
    RESAMPLING_LABELS,
    RESAMPLING_METHODS,
)
from veri_ufku.statistics.survival_contracts import SURVIVAL_LABELS, SURVIVAL_METHODS
from veri_ufku.statistics.worker import process_entry
from veri_ufku.storage.analysis_store import publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import file_hash
from veri_ufku.ui.projects import project_error_text


class StatisticsController(QObject):
    changed = Signal()

    def __init__(self, data, projects, charts, cache, budget, parent=None):
        super().__init__(parent)
        self.data, self.projects, self.charts = data, projects, charts
        self.cache, self.budget = Path(cache), budget
        self.process = self.connection = self.cancel_event = self.future = None
        self.workspace = self.result_workspace = None
        self.result = self.preflight_result = None
        self.binding = self.preflight_binding = None
        self.revision = 0
        self.cancel_time = None
        self._error = ""
        self._message = (
            "Soru, ölçüm, grup, birim ve hipotezi belirtin; önce önkontrolü inceleyin."
        )
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
    columns = Property(
        "QVariantList", lambda self: self.charts.column_rows(), notify=changed
    )
    analysisResult = Property(
        "QVariantMap",
        lambda self: {
            k: v
            for k, v in (self.result or {}).items()
            if k not in ("paths", "fingerprints")
        },
        notify=changed,
    )
    viewSpec = Property(
        "QVariantMap", lambda self: self.data.view.data(), notify=changed
    )
    preflightResult = Property(
        "QVariantMap", lambda self: self.preflight_result or {}, notify=changed
    )
    preflightCurrent = Property(
        bool,
        lambda self: (
            self.preflight_binding == self.current_binding()
            and self.preflight_result is not None
        ),
        notify=changed,
    )
    advice = Property("QVariantMap", lambda self: self.advice_card(), notify=changed)
    current = Property(
        bool,
        lambda self: bool(
            self.result
            and self.result["dataset_version"]
            == (self.data.dataset() or {}).get("version_id")
            and self.result["config_revision"] == self.revision
            and (
                self.result["spec"]["scope"] == "full"
                or self.result["spec"]["view"] == self.data.view.data()
            )
            and (
                self.result["spec"]["path"]
                not in (
                    "models",
                    "resampling",
                    "experiments",
                    "bayes",
                    "causal",
                    "survival",
                    "dimensions",
                )
                or self.projects._statuses.get(
                    (self.data.dataset() or {}).get("source_id")
                )
                in ("unchanged", "captured")
            )
            and self.result.get("project_root")
            == (str(self.projects.store.root) if self.projects.store else "")
        ),
        notify=changed,
    )
    savedAnalyses = Property(
        "QVariantList",
        lambda self: [
            dict(
                id=r["id"],
                label=r["analysis"]["spec"]["question"],
                version=r["analysis"]["dataset_version"],
                path=r["analysis"]["spec"]["path"],
            )
            for r in self.projects.draft["results"]
            if "analysis" in r
        ],
        notify=changed,
    )

    @Slot(str, result="QVariantList")
    def methods(self, path):
        return [
            dict(
                id=m,
                enabled=availability(CAPABILITIES["statistics." + m.replace("_", "-")])[
                    0
                ],
                reason=availability(CAPABILITIES["statistics." + m.replace("_", "-")])[
                    1
                ],
                label=(
                    DIMENSION_LABELS
                    if path == "dimensions"
                    else SURVIVAL_LABELS
                    if path == "survival"
                    else CAUSAL_LABELS
                    if path == "causal"
                    else BAYES_LABELS
                    if path == "bayes"
                    else EXPERIMENT_LABELS
                    if path == "experiments"
                    else RESAMPLING_LABELS
                    if path == "resampling"
                    else MODEL_LABELS
                    if path == "models"
                    else LABELS
                )[m],
            )
            for m in (
                DIMENSION_METHODS
                if path == "dimensions"
                else SURVIVAL_METHODS
                if path == "survival"
                else CAUSAL_METHODS
                if path == "causal"
                else BAYES_METHODS
                if path == "bayes"
                else EXPERIMENT_METHODS
                if path == "experiments"
                else RESAMPLING_METHODS
                if path == "resampling"
                else MODEL_METHODS
                if path == "models"
                else ADVANCED_METHODS
                if path == "advanced"
                else METHODS.get(path, ())
            )
            if "statistics." + m.replace("_", "-") in CAPABILITIES
        ]

    def current_binding(self):
        return (
            str(self.projects.store.root) if self.projects.store else "",
            (self.data.dataset() or {}).get("version_id"),
            self.revision,
            json.dumps(self.data.view.data(), sort_keys=True),
        )

    @Slot()
    def invalidate(self):
        self._dimension_transform = {}
        self._survival_prediction = {}
        self._model_prediction = {}
        self.revision += 1
        self.changed.emit()

    def advice_card(self):
        from veri_ufku.ui.statistics_advice import statistics_advice

        result = self.result or {}
        if result.get("spec") and result.get("used_rows") is not None:
            return statistics_advice(result)
        return statistics_advice(self.preflight_result)

    def fail(self, error):
        self._error = project_error_text(error)
        self.changed.emit()

    @Slot(str, bool)
    def create(self, spec_json, preflight):
        if self.busy or self.projects.busy:
            return self.fail(ProjectError("Devam eden işi bekleyin veya iptal edin."))
        try:
            if not preflight and not self.preflightCurrent:
                raise ProjectError("Güncel önkontrolü çalıştırıp inceleyin.")
            dataset = self.data.dataset()
            if not dataset:
                raise ProjectError("Önce veri içe aktarın.")
            spec = AnalysisSpec.from_dict(json.loads(spec_json))
            spec = AnalysisSpec.from_dict(dict(spec.data(), view=self.data.view.data()))
            capability = get_capability("statistics." + spec.method.replace("_", "-"))
            enabled, reason = availability(capability)
            if not enabled:
                raise ProjectError(reason)
            spec.validate(dataset["import_metadata"]["columns"], run=not preflight)
            if not preflight:
                before = dict(
                    self.preflight_result["spec"],
                    assumptions_confirmed=spec.assumptions_confirmed,
                )
                if before != spec.data():
                    raise ProjectError(
                        "Tarif önkontrolden sonra değişti; yeniden önkontrol çalıştırın."
                    )
            fp = self.projects.store.manifest["artifacts"][dataset["snapshot_uri"]]
            request = dict(
                path=str(self.projects.store.path(dataset["snapshot_uri"])).replace(
                    "/proc/self/", f"/proc/{os.getpid()}/", 1
                ),
                fingerprint={k: fp[k] for k in ("size", "sha256")},
                columns=copy.deepcopy(dataset["import_metadata"]["columns"]),
                semantic_metadata=copy.deepcopy(dataset.get("semantic_metadata", {})),
                row_count=dataset["import_metadata"]["row_count"],
                version_id=dataset["version_id"],
                source_snapshot_id=dataset["import_metadata"]["source_snapshot_id"],
                snapshot_uri=dataset["snapshot_uri"],
                format_metadata=copy.deepcopy(
                    dataset["import_metadata"]["settings"].get("format_metadata", {})
                ),
                config_revision=self.revision,
            )
            self.cache.mkdir(parents=True, exist_ok=True)
            self.workspace = tempfile.mkdtemp(prefix="statistics-", dir=self.cache)
            ctx = mp.get_context("spawn")
            self.cancel_event = ctx.Event()
            self.connection, sender = ctx.Pipe(duplex=False)
            self.action = "preflight" if preflight else "calculate"
            self.process = ctx.Process(
                target=process_entry,
                args=(
                    self.action,
                    request,
                    spec.data(),
                    self.workspace,
                    self.cancel_event,
                    sender,
                    self.budget,
                ),
            )
            self.binding = self.current_binding()
            self.started, self.cancel_time = time.monotonic(), None
            if not start_controller(self, sender):
                return
            sender.close()
            self.projects.dataset_active = True
            self._error = ""
            self._message = (
                "Önkontrol ayrı süreçte…" if preflight else "İstatistik ayrı süreçte…"
            )
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

    def release(self, keep=False):
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
        if self.workspace and not keep:
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
                self._message = "Analiz tarifi, sonuç ve RowId kökeni atomik proje kaydında saklandı."
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
            self._message = "İptal edildi; veri ve önceki analiz korundu."
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
            workspace = self.workspace
            keep = (
                kind == "result"
                and valid
                and not canceled
                and self.action == "calculate"
            )
            self.release(keep)
            if canceled or kind == "canceled":
                self._message = "İptal edildi; veri ve önceki analiz korundu."
            elif not valid:
                self._message = (
                    "Eski veri/yapılandırma sonucu güncel analize bağlanmadı."
                )
            elif kind == "error":
                self._error = value
                self.preflight_binding = None
            elif self.action == "preflight":
                self.preflight_result = value
                self.preflight_binding = self.binding
                self._message = "Önkontrol hazır. Varsayımları ve dağılımı inceleyip açıkça onaylayın."
            elif keep:
                if self.result_workspace:
                    shutil.rmtree(self.result_workspace, ignore_errors=True)
                self.result_workspace = workspace
                self.result = dict(value, project_root=self.binding[0])
                self._message = (
                    "Boyut/selection sonucu hazır; fit kapsamı, nested CV, loadings ve operasyon sınırlarını inceleyin."
                    if value.get("dimensions")
                    else "Sağkalım raporu hazır; censoring, risk set, model tanıları ve prediction kapsamını inceleyin."
                    if value.get("survival")
                    else "Nedensel rapor hazır; identification, varsayımlar ve alternatif açıklamaları inceleyin."
                    if value.get("causal")
                    else "Bayes sonucu hazır; posterior/prior, credible interval ve sampling tanılarını birlikte inceleyin."
                    if value.get("bayes")
                    else "Analiz hazır; p, etki ve güven aralığı birlikte yorumlanmalı."
                )
            self.projects.changed.emit()
            self.changed.emit()
            return
        if self.process and not self.process.is_alive() and not self.connection.poll():
            self.release()
            self._error = "İstatistik süreci durdu; eksik sonuç kabul edilmedi."
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
            return self.fail(
                ProjectError("Güncel analiz ve yazılabilir proje gerekli.")
            )
        value = {k: v for k, v in self.result.items() if k != "project_root"}
        self.future = self.projects.executor.submit(
            publish,
            self.projects.store,
            copy.deepcopy(self.projects.draft),
            copy.deepcopy(value),
        )
        self.projects.dataset_active = True
        self.projects.changed.emit()
        self.changed.emit()

    @Slot(str)
    def exportAdvanced(self, destination):
        """Explicit, atomic, new-directory export of a verified local result."""
        if (
            self.busy
            or self.projects.busy
            or not self.current
            or not (
                self.result.get("advanced")
                or self.result.get("resampling")
                or self.result.get("experiment")
                or self.result.get("bayes")
                or self.result.get("causal")
                or self.result.get("survival")
                or self.result.get("dimensions")
            )
        ):
            return self.fail(ProjectError("Güncel ileri hesap sonucu gerekli."))
        temporary = None
        try:
            target = Path(destination)
            if (
                not target.is_absolute()
                or target.exists()
                or target.is_symlink()
                or not target.parent.is_dir()
            ):
                raise ProjectError(
                    "Var olmayan yeni bir mutlak çıktı klasörü seçin; mevcut dosya üzerine yazılmaz."
                )
            root = self.projects.store.root.resolve()
            if target.resolve().is_relative_to(root):
                raise ProjectError("Proje iç dosyalarına export yapılamaz.")
            temporary = Path(
                tempfile.mkdtemp(prefix=".veri-ufku-export-", dir=target.parent)
            )
            for key, source in self.result["paths"].items():
                if file_hash(Path(source)) != self.result["fingerprints"][key]:
                    raise ProjectError("Çıktı hash'i değişti; export reddedildi.")
                output = temporary / (
                    key
                    + (
                        ".json"
                        if key == "result"
                        else ".nc"
                        if key == "chains"
                        else ".png"
                        if key == "diagnostic_png"
                        else ".parquet"
                    )
                )
                shutil.copyfile(source, output)
                output.chmod(0o600)
            recipe = temporary / "recipe.json"
            recipe.write_text(
                json.dumps(
                    dict(
                        dataset_version=self.result["dataset_version"],
                        spec=self.result["spec"],
                    ),
                    ensure_ascii=False,
                    allow_nan=False,
                )
            )
            recipe.chmod(0o600)
            temporary.rename(target)
            temporary = None
            self._message = "Tarif ve kimlikli yerel çıktı yeni klasöre aktarıldı."
            self._error = ""
            self.changed.emit()
        except (ValueError, OSError, KeyError) as error:
            self.fail(error)
        finally:
            if temporary:
                shutil.rmtree(temporary, ignore_errors=True)

    modelPrediction = Property(
        "QVariantMap",
        lambda self: getattr(self, "_model_prediction", {}),
        notify=changed,
    )
    modelDiagnostic = Property(
        str,
        lambda self: (
            Path(self.result["paths"]["diagnostic_png"]).as_uri()
            if self.result and "diagnostic_png" in self.result.get("paths", {})
            else ""
        ),
        notify=changed,
    )

    @Slot(str)
    def compareBayes(self, ident):
        try:
            if not self.current or self.busy or self.projects.busy:
                raise ProjectError("Güncel ve boşta Bayes sonucu gerekli.")
            from veri_ufku.statistics.bayes import compare_results

            other = next(
                r["analysis"]
                for r in self.projects.draft["results"]
                if r["id"] == ident and r.get("analysis", {}).get("bayes")
            )
            for uri in other["artifact_uris"].values():
                fp = self.projects.store.manifest["artifacts"][uri]
                if file_hash(self.projects.store.path(uri)) != {
                    k: fp[k] for k in ("size", "sha256")
                }:
                    raise ProjectError(
                        "Kayıtlı Bayes artifact hash değişmiş; karşılaştırma reddedildi."
                    )
            saved = json.loads(
                self.projects.store.path(other["artifact_uris"]["result"]).read_text()
            )
            if saved != {k: v for k, v in other.items() if k != "artifact_uris"}:
                raise ProjectError("Kayıtlı Bayes sonucu JSON/manifest uyuşmuyor.")
            self._bayes_comparison = compare_results(self.result, other)
            self._error = ""
            self.changed.emit()
        except (ValueError, KeyError, TypeError, StopIteration, OSError) as error:
            self._bayes_comparison = {}
            self.fail(ProjectError(str(error) or "Kayıtlı Bayes sonucu gerekli."))

    bayesComparison = Property(
        "QVariantMap",
        lambda self: getattr(self, "_bayes_comparison", {}),
        notify=changed,
    )

    dimensionTransform = Property(
        "QVariantMap",
        lambda self: (
            getattr(self, "_dimension_transform", {})
            if self.current and self.result.get("dimensions")
            else {}
        ),
        notify=changed,
    )

    @Slot(str, bool)
    def transformDimension(self, matrix, inverse):
        try:
            if (
                not self.current
                or self.busy
                or self.projects.busy
                or not self.result.get("dimensions")
            ):
                raise ProjectError(
                    "Güncel ve boşta representation modeli gerekli; eski fit scope/config reddi."
                )
            for key, path in self.result["paths"].items():
                if file_hash(Path(path)) != self.result["fingerprints"][key]:
                    raise ProjectError(
                        "Representation artifact hash değişmiş; transform reddi."
                    )
            saved = json.loads(Path(self.result["paths"]["result"]).read_text())
            if (
                saved["dimension_analysis"] != self.result["dimension_analysis"]
                or saved["spec"] != self.result["spec"]
            ):
                raise ProjectError("Safe representation JSON/current model uyuşmuyor.")
            from veri_ufku.statistics.dimensions import transform

            self._dimension_transform = transform(
                saved["dimension_analysis"]["model"], json.loads(matrix), inverse
            )
            self._error = ""
            self.changed.emit()
        except (ValueError, TypeError, KeyError) as error:
            self._dimension_transform = {}
            self.fail(error)

    survivalPrediction = Property(
        "QVariantMap",
        lambda self: (
            getattr(self, "_survival_prediction", {})
            if self.current and self.result.get("survival")
            else {}
        ),
        notify=changed,
    )

    @Slot(str, str, str)
    def predictSurvival(self, profile, times, group):
        try:
            if (
                not self.current
                or self.busy
                or self.projects.busy
                or not self.result.get("survival")
            ):
                raise ProjectError("Güncel ve boşta safe sağkalım modeli gerekli.")
            from veri_ufku.statistics.survival import predict

            for key, path in self.result["paths"].items():
                if file_hash(Path(path)) != self.result["fingerprints"][key]:
                    raise ProjectError(
                        "Sağkalım artifact hash değişmiş; prediction reddi."
                    )
            saved = json.loads(Path(self.result["paths"]["result"]).read_text())
            if (
                saved["survival_analysis"] != self.result["survival_analysis"]
                or saved["spec"] != self.result["spec"]
            ):
                raise ProjectError("Safe model JSON/current sonuç uyuşmuyor.")
            self._survival_prediction = predict(
                saved["survival_analysis"]["model"],
                json.loads(profile),
                json.loads(times),
                group,
            )
            self._error = ""
            self.changed.emit()
        except (ValueError, KeyError, TypeError) as error:
            self._survival_prediction = {}
            self.fail(error)

    @Slot(str, float, float)
    def predictModel(self, values, offset, exposure):
        try:
            if not self.current or self.busy or self.result["spec"]["path"] != "models":
                raise ProjectError(
                    "Güncel kaydedilmiş/hesaplanmış model gerekli; eski veriyle prediction reddedilir."
                )
            from veri_ufku.statistics.models import predict

            self._model_prediction = predict(
                self.result, json.loads(values), offset, exposure
            )
            self._error = ""
            self.changed.emit()
        except (ValueError, KeyError, TypeError) as error:
            self._model_prediction = {}
            self.fail(error)

    @Slot(str, result="QVariantMap")
    def compareModel(self, ident):
        try:
            if not self.current or self.busy:
                raise ProjectError("Güncel model gerekli.")
            from veri_ufku.statistics.models import compare_information

            other = next(
                r["analysis"]
                for r in self.projects.draft["results"]
                if r["id"] == ident
            )
            return compare_information(self.result, other)
        except (ValueError, KeyError, StopIteration) as error:
            self.fail(error)
            return {}

    @Slot(str)
    def openSaved(self, ident):
        self._dimension_transform = {}
        self._survival_prediction = {}
        if self.busy or self.projects.busy:
            return
        try:
            record = next(
                r
                for r in self.projects.draft["results"]
                if r["id"] == ident and "analysis" in r
            )
            analysis = copy.deepcopy(record["analysis"])
            for uri in analysis["artifact_uris"].values():
                fp = self.projects.store.manifest["artifacts"][uri]
                if file_hash(self.projects.store.path(uri)) != {
                    k: fp[k] for k in ("size", "sha256")
                }:
                    raise ProjectError("Kayıtlı istatistik artifact değişmiş.")
            value = json.loads(
                self.projects.store.path(
                    analysis["artifact_uris"]["result"]
                ).read_text()
            )
            if value != {k: v for k, v in analysis.items() if k != "artifact_uris"}:
                raise ProjectError("Kayıtlı istatistik JSON/manifest uyuşmuyor.")
            value["project_root"] = str(self.projects.store.root)
            value["paths"] = {
                k: str(self.projects.store.path(uri))
                for k, uri in analysis["artifact_uris"].items()
            }
            value["fingerprints"] = {
                k: {
                    f: self.projects.store.manifest["artifacts"][uri][f]
                    for f in ("size", "sha256")
                }
                for k, uri in analysis["artifact_uris"].items()
            }
            self.result = value
            self.revision = value["config_revision"]
            self.preflight_binding = None
            self._error = ""
            self._message = "Kayıtlı analiz açıldı; veri/filtre sürümünü kontrol edin."
            self.changed.emit()
        except (ValueError, KeyError, OSError, StopIteration) as error:
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
        if self.result_workspace:
            shutil.rmtree(self.result_workspace, ignore_errors=True)
            self.result_workspace = None
