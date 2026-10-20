"""Three-stage recipe mapping/dry-run/atomic apply desktop controller."""

import copy
import multiprocessing as mp
import os
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.domain.json import raw_json
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.admission import start_controller
from veri_ufku.modeling.lifecycle_worker import publish_file
from veri_ufku.operations.recipe_worker import process_entry
from veri_ufku.operations.recipes import export, publish, read
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.ui.lifecycle import local
from veri_ufku.ui.preparation import PreparationController


class RecipeController(PreparationController):
    recipeChanged = Signal()

    def __init__(self, *args):
        super().__init__(*args)
        self.changed.connect(self.recipeChanged)
        self.recipe = None
        self.sources = {}
        self.mappings = {}
        self.action = None
        self._message = "1. Kayıtlı zinciri seç veya tarif aç. 2. Yeni kaynak/kolonları eşle. 3. Dry-run etkisini incele ve uygula."

    recipeSeed = Property(
        int, lambda self: (self.recipe or {}).get("seed", 42), notify=recipeChanged
    )

    @Slot(int)
    def setSeed(self, seed):
        if self.recipe and not self.busy and 0 <= seed < 2**31:
            self.recipe["seed"] = seed
            self.invalidate()

    versions = Property(
        "QVariantList",
        lambda self: [
            dict(
                id=d["version_id"],
                name=f"{d['version_id'][-8:]} · {d['import_metadata']['row_count']} kayıt",
                columns=d["import_metadata"]["columns"],
            )
            for d in self.projects.draft["datasets"]
        ],
        notify=recipeChanged,
    )
    recipeSources = Property(
        "QVariantList",
        lambda self: [
            dict(
                id=k,
                columns=v["columns"],
                selected=self.sources.get(k, ""),
                mapping=self.mappings.get(k, {}),
            )
            for k, v in (self.recipe or {}).get("sources", {}).items()
        ],
        notify=recipeChanged,
    )
    steps = Property(
        "QVariantList",
        lambda self: (self.result or {}).get("steps", []) if self.current else [],
        notify=recipeChanged,
    )
    changeReport = Property(
        "QVariantMap",
        lambda self: (
            self.result
            if self.current
            and (self.result or {}).get("schema")
            in ("DatasetChange/v1", "DelayedPerformance/v1")
            else {}
        ),
        notify=recipeChanged,
    )
    canApply = Property(
        bool,
        lambda self: (
            self.current
            and bool((self.result or {}).get("valid"))
            and not self.busy
            and not self.projects.busy
            and not self.projects.readOnly
        ),
        notify=recipeChanged,
    )

    def current_binding(self):
        return (
            str(self.projects.store.root) if self.projects.store else "",
            self.projects.store.commit_id if self.projects.store else "",
            self.revision,
            (self.data.dataset() or {}).get("version_id"),
        )

    @Slot(str)
    def selectRecipe(self, version):
        if self.busy or self.projects.busy:
            return
        try:
            self.recipe = export(
                self.projects.draft, version, self.projects.store.manifest["artifacts"]
            )
            self.sources, self.mappings = {}, {}
            self.result = None
            self.invalidate()
            self._error = ""
        except (ValueError, KeyError, TypeError) as error:
            self.fail(error)

    @Slot(str)
    def openRecipe(self, url):
        if self.busy or self.projects.busy:
            return
        try:
            self.recipe = read(local(url))
            self.sources, self.mappings = {}, {}
            self.result = None
            self.invalidate()
            self._error = ""
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.fail(error)

    @Slot(str)
    def saveRecipe(self, url):
        if self.busy or not self.recipe:
            return
        try:
            with tempfile.TemporaryDirectory(dir=self.cache.parent) as work:
                path = Path(work) / "recipe.json"
                path.write_bytes(raw_json(self.recipe))
                publish_file(path, local(url), Control())
            self._message = (
                "AnalysisRecipe/v1 JSON kaydedildi; kod ve öğrenilmiş model içermez."
            )
            self.changed.emit()
        except (OSError, ValueError) as error:
            self.fail(error)

    @Slot(str, str)
    def mapSource(self, source, version):
        if self.busy or source not in (self.recipe or {}).get("sources", {}):
            return
        d = next(
            (d for d in self.projects.draft["datasets"] if d["version_id"] == version),
            None,
        )
        if not d:
            return
        self.sources[source] = version
        self.mappings[source] = {
            c["id"]: a["id"]
            for c in self.recipe["sources"][source]["columns"]
            for a in d["import_metadata"]["columns"]
            if a["name"] == c["name"]
        }
        self.invalidate()

    @Slot(str, str, str)
    def mapColumn(self, source, column, target):
        if self.busy:
            return
        self.mappings.setdefault(source, {})[column] = target
        self.invalidate()

    def request(self, version):
        d = next(
            d for d in self.projects.draft["datasets"] if d["version_id"] == version
        )
        fp = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]
        return dict(
            path=str(self.projects.store.path(d["snapshot_uri"])).replace(
                "/proc/self/", f"/proc/{os.getpid()}/", 1
            ),
            fingerprint={k: fp[k] for k in ("size", "sha256")},
            columns=copy.deepcopy(d["import_metadata"]["columns"]),
            semantic_metadata=copy.deepcopy(d.get("semantic_metadata", {})),
            settings=copy.deepcopy(d["import_metadata"]["settings"]),
            row_count=d["import_metadata"]["row_count"],
            version_id=version,
            source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
            config_revision=self.revision,
        )

    @Slot()
    def dryRun(self):
        if not self.recipe:
            return self.fail(ProjectError("Önce tarif seçin."))
        self.start(
            "dry",
            dict(
                recipe=self.recipe,
                sources={k: self.request(v) for k, v in self.sources.items()},
                mappings=self.mappings,
            ),
        )

    @Slot(str, str)
    def compareData(self, old, new):
        try:
            a, b = self.request(old), self.request(new)
            mapping = {
                c["id"]: d["id"]
                for c in a["columns"]
                for d in b["columns"]
                if c["name"] == d["name"]
            }
            # Reuse explicit recipe mapping when those same versions are selected.
            for source, target in self.sources.items():
                if source == old and target == new:
                    mapping = self.mappings[source]
            self.start("compare", dict(old=a, new=b, mapping=mapping))
        except (ValueError, KeyError, StopIteration) as error:
            self.fail(error)

    @Slot(str, str, str, str, str)
    def evaluateTargets(
        self, version, prediction_key, target_key, prediction_column, target_column
    ):
        try:
            lifecycle = self.parent()._lifecycle_resources
            result = lifecycle.result or {}
            if not result.get("output_fingerprint") or not result.get(
                "dataset_version"
            ):
                raise ProjectError("Önce Modeli uygula ile tahmin dosyası oluşturun.")
            self.start(
                "evaluate",
                dict(
                    prediction=copy.deepcopy(result),
                    target=self.request(version),
                    prediction_key=prediction_key,
                    target_key=target_key,
                    prediction_column=prediction_column,
                    target_column=target_column,
                ),
            )
        except (ValueError, KeyError, StopIteration) as error:
            self.fail(error)

    @Slot(str)
    def saveReport(self, url):
        if not self.current or self.busy:
            return
        try:
            value = {
                k: v
                for k, v in self.result.items()
                if k not in ("results", "worker_pid")
            }
            with tempfile.TemporaryDirectory(dir=self.cache.parent) as work:
                path = Path(work) / "report.json"
                path.write_bytes(raw_json(value))
                publish_file(path, local(url), Control())
            self._message = (
                "Veri/model referanslı rapor yeni JSON dosyasına kaydedildi."
            )
            self.changed.emit()
        except (OSError, ValueError) as error:
            self.fail(error)

    def start(self, action, request):
        if self.busy or self.projects.busy:
            return
        try:
            self.release()
            self.invalidate()
            self.cache.mkdir(parents=True, exist_ok=True)
            self.workspace = tempfile.mkdtemp(prefix="recipe-", dir=self.cache)
            ctx = mp.get_context("spawn")
            self.cancel_event = ctx.Event()
            self.connection, sender = ctx.Pipe(duplex=False)
            self.process = ctx.Process(
                target=process_entry,
                args=(
                    copy.deepcopy(request),
                    action,
                    self.workspace,
                    self.cancel_event,
                    sender,
                    self.budget,
                ),
            )
            self.binding = self.current_binding()
            self.started, self.cancel_time = time.monotonic(), None
            self.action = action
            if not start_controller(self, sender):
                return
            sender.close()
            self.projects.dataset_active = True
            self._error = ""
            self._message = "Geçici alanda hesaplanıyor; proje henüz değişmedi."
            self.changed.emit()
            self.projects.changed.emit()
        except (ValueError, KeyError, TypeError, OSError) as error:
            self.release()
            self.fail(error)

    @Slot()
    def applyRecipe(self):
        if not self.canApply:
            return self.fail(ProjectError("Güncel başarılı dry-run gerekli."))
        self.future = self.projects.executor.submit(
            publish,
            self.projects.store,
            copy.deepcopy(self.projects.draft),
            copy.deepcopy(self.result),
        )
        self.projects.dataset_active = True
        self.changed.emit()
        self.projects.changed.emit()

    def poll(self):
        if self.future:
            if not self.future.done():
                return
            future, self.future = self.future, None
            try:
                self.projects.draft = future.result()
                self.projects.saved = copy.deepcopy(self.projects.draft)
                self._message = "Tüm adımlar tek atomik proje yayınıyla uygulandı."
                self.result_binding = None
            except (ValueError, OSError, KeyError) as error:
                self.fail(error)
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
            self._message = "İptal edildi; proje korundu."
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
                self._message = value.phase
                self.changed.emit()
                continue
            valid = self.binding == self.current_binding()
            if kind == "result" and valid and not self.cancel_event.is_set():
                # Preserve completed temporary artifacts until apply or the next dry-run.
                self.process.join(0.2)
                if self.process.is_alive():
                    self.process.terminate()
                    self.process.join(0.2)
                self.process.close()
                self.process = None
                self.connection.close()
                self.connection = None
                self.projects.dataset_active = False
                self.result, self.result_binding = value, self.binding
                self._message = (
                    "Dry-run hazır; her adımın etkisini inceleyin."
                    if self.action == "dry"
                    else "Yeni veri raporu hazır; yöntem ve kapsam aşağıda."
                )
            else:
                self.release()
                self.result_binding = None
                self._error = (
                    value if kind == "error" else "İptal/eski sonuç; proje korundu."
                )
            self.changed.emit()
            self.projects.changed.emit()
            return
        if self.process and not self.process.is_alive() and not self.connection.poll():
            self.release()
            self._error = "Süreç durdu; eksik çıktı yayımlanmadı."
            self.changed.emit()
            self.projects.changed.emit()
