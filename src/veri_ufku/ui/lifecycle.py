"""Model card and explicit preview-before-predict desktop flow."""

import copy
import json
import multiprocessing as mp
import os
import tempfile
import threading
import time
from pathlib import Path

from PySide6.QtCore import Property, QUrl, Signal, Slot

from veri_ufku.jobs.admission import start_controller
from veri_ufku.modeling.lifecycle_worker import process_entry
from veri_ufku.storage import experiment_store as registry
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.validation_store import prior_uses
from veri_ufku.ui.preparation import PreparationController


def local(value):
    url = QUrl(value)
    if not url.isLocalFile() or url.host():
        if not url.scheme() and Path(value).is_absolute():
            return str(Path(value))
        raise ProjectError("Yerel dosya seçin.")
    return url.toLocalFile()


class LifecycleController(PreparationController):
    lifecycleChanged = Signal()
    selectExplanation = Signal(str)

    @Property("QVariantList", notify=lifecycleChanged)
    def experimentRuns(self):
        if not self.projects.store:
            return []
        return registry.rows(self.projects.store, self.projects.draft)

    @Property("QVariantMap", notify=lifecycleChanged)
    def experimentReport(self):
        if not self.projects.store or getattr(
            self, "_experiment_store_root", None
        ) != str(self.projects.store.root):
            return {}
        return getattr(self, "_experiment_report", {})

    @Slot(str, str, str, result="QVariantList")
    def findExperiments(self, query, status, tag):
        return (
            registry.rows(self.projects.store, self.projects.draft, query, status, tag)
            if self.projects.store
            else []
        )

    def registry_ready(self, writable=False):
        if (
            not self.projects.store
            or self.busy
            or self.projects.busy
            or (writable and self.projects.readOnly)
        ):
            raise ProjectError("Açık, uygun erişimli ve boşta proje gerekir.")

    def registry_submit(self, kind, function, *args):
        self.registry_kind = kind
        self._experiment_store_root = str(self.projects.store.root)
        self.registry_future = self.projects.executor.submit(function, *args)
        self.future = self.registry_future
        self.projects.dataset_active = True
        self._error = ""
        self.projects.changed.emit()
        self.changed.emit()

    @Slot(str, str, str)
    def reviseExperiment(self, run_id, kind, value):
        from veri_ufku.importers.delimited import Control

        try:
            self.registry_ready(True)
            self.registry_submit(
                "revision",
                registry.event,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                run_id or None,
                kind,
                json.loads(value),
                Control(budget=self.budget),
            )
        except (ValueError, OSError, TypeError, KeyError) as error:
            self.fail(error)

    @Slot(str, str)
    def compareExperiments(self, ids, metric):
        from veri_ufku.importers.delimited import Control

        try:
            self.registry_ready()
            self.registry_cancel = threading.Event()
            control = Control(cancel=self.registry_cancel, budget=self.budget)
            self.registry_submit(
                "compare",
                registry.compare,
                self.projects.store,
                json.loads(ids),
                metric,
                control,
            )
        except (ValueError, OSError, TypeError, KeyError) as error:
            self.fail(error)

    @Slot(str, str, str)
    def exportExperiments(self, ids, metric, path):
        from veri_ufku.importers.delimited import Control

        try:
            self.registry_ready()
            self.registry_cancel = threading.Event()
            control = Control(cancel=self.registry_cancel, budget=self.budget)
            self.registry_submit(
                "export",
                registry.export,
                self.projects.store,
                json.loads(ids),
                local(path),
                metric,
                control,
            )
        except (ValueError, OSError, TypeError, KeyError) as error:
            self.fail(error)

    @Slot()
    def cancel(self):
        if self.registry_future is not None:
            if self.registry_cancel is not None:
                self.registry_cancel.set()
            return
        super().cancel()

    def __init__(self, *args):
        super().__init__(*args)
        self.changed.connect(self.lifecycleChanged)
        self.package = ""
        self.package_fingerprint = None
        self.expected_card = None
        self.mapping = {}
        self.action = None
        self.explanation = None
        self.pending_explanation = None
        self.explanation_future = None
        self.registry_future = None
        self.registry_cancel = None
        self._message = "Kayıtlı güvenli model veya .vumodel paketi seçin. Yeni dosyayı Veri ekranında içe aktarın; kolon önizlemesinden sonra tahmin edin."

    models = Property(
        "QVariantList",
        lambda self: [
            dict(
                id=r["id"],
                label=(r.get("baseline") or r.get("unsupervised"))["run_id"],
                supported=bool(
                    (r.get("baseline") or r.get("unsupervised")).get(
                        "model_package_uri"
                    )
                ),
            )
            for r in self.projects.draft["results"]
            if "baseline" in r or "unsupervised" in r
        ],
        notify=lifecycleChanged,
    )
    card = Property(
        "QVariantMap",
        lambda self: self.ui_card(),
        notify=lifecycleChanged,
    )
    previewReport = Property(
        "QVariantMap",
        lambda self: (self.result or {}).get("preview", {}) if self.current else {},
        notify=lifecycleChanged,
    )
    outputReport = Property(
        "QVariantMap",
        lambda self: dict(
            output=(self.result or {}).get("output", ""),
            details=(self.result or {}).get("details", {}),
        ),
        notify=lifecycleChanged,
    )
    featureMapping = Property(
        "QVariantMap", lambda self: self.mapping, notify=lifecycleChanged
    )

    explanationHasModel = Property(
        bool,
        lambda self: bool(self.package and self.expected_card),
        notify=lifecycleChanged,
    )
    explanationRows = Property(
        "QStringList",
        lambda self: (
            ((self.expected_card or {}).get("split") or {})
            .get("membership", {})
            .get("validation", [])
        ),
        notify=lifecycleChanged,
    )
    explanationReport = Property(
        "QVariantMap", lambda self: self.explanation or {}, notify=lifecycleChanged
    )
    savedExplanations = Property(
        "QVariantList",
        lambda self: [
            dict(
                id=r["id"],
                label=r["explanation"]["spec"]["method"]
                + " · "
                + r["explanation"]["created_at"],
            )
            for r in self.projects.draft["results"]
            if "explanation" in r
        ],
        notify=lifecycleChanged,
    )

    @Slot(result="QVariantList")
    def explanationMethods(self):
        from veri_ufku.domain.capabilities import CAPABILITIES, availability

        return [
            dict(
                id=c.capability_id.removeprefix("model.explain."),
                label=c.method,
                enabled=availability(c)[0],
                reason=availability(c)[1],
            )
            for c in CAPABILITIES.values()
            if c.capability_id.startswith("model.explain.")
        ]

    @Slot(str, str)
    def explain(self, value, background_version):
        try:
            from veri_ufku.modeling.explanation import ExplainSpec

            if self.projects.readOnly or not self.expected_card:
                raise ProjectError("Yazılabilir projede kayıtlı model seçin.")
            if not any(
                r.get("baseline", {}).get("model_card") == self.expected_card
                and r.get("baseline", {}).get("model_package_fingerprint")
                == self.package_fingerprint
                for r in self.projects.draft["results"]
            ):
                raise ProjectError(
                    "Bu explanation yalnız projede kayıtlı model paketiyle çalışır."
                )
            self.invalidate()
            self.start(
                "explain",
                explain_spec=ExplainSpec.from_dict(json.loads(value)).data(),
                background_version=background_version,
            )
        except (ValueError, TypeError, KeyError) as error:
            self.fail(error)

    @Slot(str)
    def exportExplanation(self, destination):
        try:
            if not self.explanation:
                raise ProjectError("Önce kayıtlı açıklama sonucu gerekir.")
            self.start(
                "explain-export",
                destination=local(destination),
                explanation=copy.deepcopy(self.explanation),
            )
        except ValueError as error:
            self.fail(error)

    @Slot(str)
    def openExplanation(self, ident):
        try:
            if self.busy or self.projects.busy:
                return
            from veri_ufku.storage.explanation_store import load

            record = next(
                r
                for r in self.projects.draft["results"]
                if r["id"] == ident and "explanation" in r
            )
            self.explanation = load(self.projects.store, record)
            self._error = ""
            self._message = "Kayıtlı açıklama açıldı; ağ veya fit yok. Kaynak/model değiştiyse tarihsel sonuçtur."
            self.changed.emit()
        except (ValueError, TypeError, KeyError, StopIteration) as error:
            self.fail(error)

    def ui_card(self):
        original = (self.result or {}).get("card", {})
        value = {k: v for k, v in original.items() if k not in ("fit_row_ids", "split")}
        if original:
            value["fit_row_count"] = len(original["fit_row_ids"])
            split = original.get("split")
            value["split"] = (
                {k: v for k, v in split.items() if k != "membership"} if split else None
            )
            if split:
                value["split"]["membership_counts"] = {
                    k: len(v) for k, v in split["membership"].items()
                }
        return value

    def selected_source(self):
        return self.data.dataset()

    def current_binding(self):
        return (
            str(self.projects.store.root) if self.projects.store else "",
            (self.data.dataset() or {}).get("version_id"),
            self.revision,
            self.package if hasattr(self, "package") else "",
        )

    @Slot(str)
    def selectModel(self, ident):
        if self.busy or self.projects.busy:
            return
        try:
            r = next(r for r in self.projects.draft["results"] if r["id"] == ident)
            run = r.get("baseline") or r.get("unsupervised")
            if not run.get("model_package_uri"):
                raise ProjectError(
                    "Bu koşuda güvenli fitted model yok. DBSCAN doğal predict desteklemez; eski koşular için açık yeni eğitim gerekir."
                )
            self.package = str(
                self.projects.store.path(run["model_package_uri"])
            ).replace("/proc/self/", f"/proc/{os.getpid()}/", 1)
            self.package_fingerprint = run["model_package_fingerprint"]
            self.expected_card = run["model_card"]
            self.mapping = {}
            self.invalidate()
            self.start("open")
        except (ValueError, KeyError, StopIteration) as error:
            self.fail(error)

    @Slot(str)
    def openPackage(self, value):
        if self.busy or self.projects.busy:
            return
        try:
            self.package = local(value)
            self.expected_card = self.package_fingerprint = None
            self.mapping = {}
            self.invalidate()
            self.start("open")
        except ValueError as error:
            self.fail(error)

    @Slot(str, str)
    def mapFeature(self, feature, column):
        if self.busy:
            return
        self.mapping = dict(self.mapping)
        if column:
            self.mapping[feature] = column
        else:
            self.mapping.pop(feature, None)
        self.invalidate()

    @Slot()
    def resetMapping(self):
        self.mapping = {}
        self.invalidate()

    @Slot(str, int)
    def previewData(self, invalid, batch):
        self.invalidate()
        self.start("preview", invalid=invalid, batch_size=batch)

    @Slot(str, str, int)
    def predictData(self, destination, invalid, batch):
        if not self.current or not (self.result or {}).get("token"):
            return self.fail(
                ProjectError("Önce güncel kolon/kayıt önizlemesini inceleyin.")
            )
        try:
            self.start(
                "predict",
                destination=local(destination),
                invalid=invalid,
                batch_size=batch,
                preview_token=self.result["token"],
            )
        except ValueError as error:
            self.fail(error)

    @Slot(str)
    def savePackage(self, destination):
        try:
            self.start("save", destination=local(destination))
        except ValueError as error:
            self.fail(error)

    def start(self, action, **options):
        if self.busy or self.projects.busy or self.explanation_future is not None:
            return
        try:
            if not self.package and action != "explain-export":
                raise ProjectError("Güvenli model paketi seçin.")
            request = dict(
                package=self.package,
                package_fingerprint=self.package_fingerprint,
                expected_card=self.expected_card,
                mapping=copy.deepcopy(self.mapping),
                **options,
            )
            if action in ("preview", "predict", "explain"):
                d = self.data.dataset()
                if not d:
                    raise ProjectError(
                        "Yeni dosyayı önce Veri ekranında içe aktarın ve seçin."
                    )
                fp = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]
                request["source"] = dict(
                    path=str(self.projects.store.path(d["snapshot_uri"])).replace(
                        "/proc/self/", f"/proc/{os.getpid()}/", 1
                    ),
                    fingerprint={k: fp[k] for k in ("size", "sha256")},
                    columns=copy.deepcopy(d["import_metadata"]["columns"]),
                    semantic_metadata=copy.deepcopy(d.get("semantic_metadata", {})),
                    row_count=d["import_metadata"]["row_count"],
                    version_id=d["version_id"],
                    source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
                    prior_test_use_ids=prior_uses(self.projects.draft),
                )
            if action == "explain":
                background = next(
                    d
                    for d in self.projects.draft["datasets"]
                    if d["version_id"] == options["background_version"]
                )
                fp = self.projects.store.manifest["artifacts"][
                    background["snapshot_uri"]
                ]
                request["background"] = dict(
                    path=str(
                        self.projects.store.path(background["snapshot_uri"])
                    ).replace("/proc/self/", f"/proc/{os.getpid()}/", 1),
                    fingerprint={k: fp[k] for k in ("size", "sha256")},
                    version_id=background["version_id"],
                    row_count=background["import_metadata"]["row_count"],
                    columns=copy.deepcopy(background["import_metadata"]["columns"]),
                )
            self.cache.mkdir(parents=True, exist_ok=True)
            self.workspace = tempfile.mkdtemp(prefix="lifecycle-", dir=self.cache)
            ctx = mp.get_context("spawn")
            self.cancel_event = ctx.Event()
            self.connection, sender = ctx.Pipe(duplex=False)
            self.process = ctx.Process(
                target=process_entry,
                args=(
                    request,
                    action,
                    self.workspace,
                    self.cancel_event,
                    sender,
                    self.budget,
                ),
            )
            self.binding = self.current_binding()
            self.action = action
            self.started = time.monotonic()
            self.cancel_time = None
            if not start_controller(self, sender):
                return
            sender.close()
            self.projects.dataset_active = True
            self._error = ""
            self._message = "Güvenli paket/şema kontrolü ayrı süreçte çalışıyor; yeni veride yalnız transform/predict."
            self.changed.emit()
            self.projects.changed.emit()
        except (ValueError, KeyError, TypeError, OSError, StopIteration) as error:
            self.release()
            self.fail(error)

    def shutdown(self):
        if self.registry_future is not None:
            from veri_ufku.jobs.workers import Canceled

            if self.registry_cancel is not None:
                self.registry_cancel.set()
            try:
                self.registry_future.result()
            except (Canceled, ValueError, OSError, TypeError, KeyError):
                pass
            self.registry_future = self.future = None
        super().shutdown()

    def poll(self):
        if self.registry_future is not None:
            if not self.registry_future.done():
                return
            from veri_ufku.jobs.workers import Canceled

            future, self.registry_future = self.registry_future, None
            self.future = None
            try:
                result = future.result()
                if self.registry_kind == "revision":
                    self.projects.draft = result
                    self.projects.saved = copy.deepcopy(result)
                elif self.registry_kind == "compare":
                    self._experiment_report = result
                self._message = "Registry işlemi tamamlandı; yerel durum dış deploy başlatmaz. Eşik/kalibrasyon değişikliği yeni eğitim koşusu gerektirir."
            except Canceled:
                self._message = (
                    "Registry okuması/export iptal edildi; önceki sonuç korundu."
                )
            except (ValueError, OSError, TypeError, KeyError) as error:
                self._experiment_report = {}
                self.fail(error)
            self.registry_cancel = None
            self.projects.dataset_active = False
            self.projects.changed.emit()
            self.changed.emit()
            return
        if self.explanation_future is not None:
            if not self.explanation_future.done():
                return
            future, self.explanation_future = self.explanation_future, None
            self.future = None
            try:
                self.projects.draft = future.result()
                self.projects.saved = copy.deepcopy(self.projects.draft)
                self.explanation = self.pending_explanation
                self._message = "Açıklama kaynak/model/kimlik kontrolüyle atomik kaydedildi; nedensellik veya adil model iddiası yok."
            except (ValueError, OSError, TypeError, KeyError) as error:
                self.fail(error)
            self.pending_explanation = None
            self.projects.dataset_active = False
            self.changed.emit()
            self.projects.changed.emit()
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
            self._message = "İptal edildi; kaynak korundu."
            self.changed.emit()
            self.projects.changed.emit()
            return
        for _ in range(30):
            if not self.connection.poll():
                break
            try:
                kind, value = self.connection.recv()
            except EOFError:
                break
            if kind == "progress":
                if self._message != value.phase:
                    self._message = value.phase
                    self.changed.emit()
                continue
            valid = self.binding == self.current_binding()
            canceled = self.cancel_event.is_set()
            self.release()
            if canceled or kind == "canceled":
                self._message = "İptal edildi; kaynak korundu."
            elif not valid:
                self._message = (
                    "Veri/model/eşleme değişmiş; eski sonuç güncel sayılmadı."
                )
            elif kind == "error":
                self._error = value
                self.result_binding = None
            else:
                if self.action == "explain":
                    from veri_ufku.storage.explanation_store import publish

                    self.pending_explanation = value["explanation"]
                    self.projects.dataset_active = True
                    self.explanation_future = self.projects.executor.submit(
                        publish,
                        self.projects.store,
                        copy.deepcopy(self.projects.draft),
                        self.pending_explanation,
                    )
                    self.future = self.explanation_future
                    self._message = "Açıklama kaynak/kimlik kontrolüyle kaydediliyor…"
                self.result = value
                self.result_binding = self.binding
                self.package_fingerprint = value.get(
                    "package_fingerprint", self.package_fingerprint
                )
                self.expected_card = value["card"]
                self._message = (
                    "Paket ve sürüm doğrulandı."
                    if self.action == "open"
                    else "Önizleme hazır; eksikleri, bilinmeyen kategorileri ve eşlemeyi inceleyin."
                    if self.action == "preview"
                    else "Yeni dosya kaydedildi; tüm kaynak satırları/RowId korundu."
                )
            self.changed.emit()
            self.projects.changed.emit()
            return
        if self.process and not self.process.is_alive() and not self.connection.poll():
            self.release()
            self._error = "Model/tahmin süreci durdu; eksik sonuç kabul edilmedi."
            self.changed.emit()
            self.projects.changed.emit()
