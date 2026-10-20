"""Expert presentation over the existing registry, immutable runs and project state.

No computation, shell execution, model loading or second capability registry.
"""

import copy
import hashlib
import json
from dataclasses import asdict

from PySide6.QtCore import (
    Property,
    QFileDevice,
    QIODevice,
    QObject,
    QSaveFile,
    QUrl,
    Signal,
    Slot,
)

from veri_ufku.domain.capabilities import (
    availability,
    discover,
    get_capability,
    result_compatibility,
)
from veri_ufku.domain.contracts import ResultArtifact
from veri_ufku.learning.catalog import fold
from veri_ufku.statistics.bayes_contracts import BAYES_LABELS, BAYES_METHODS
from veri_ufku.statistics.causal_contracts import CAUSAL_LABELS, CAUSAL_METHODS
from veri_ufku.statistics.contracts import LABELS, METHODS
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
from veri_ufku.storage.project_store import file_hash


def display(value):
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)[:20000]


def describe_result(ident, capability_id, value):
    """Adapt existing result metadata; absent historical fields stay unknown."""
    spec = value.get("spec", {})
    provenance = value.get("provenance", {})
    status, reason = result_compatibility(
        capability_id, value.get("method_version", 1), value.get("parameter_version", 1)
    )
    artifacts = [
        ResultArtifact(
            ident + ":text",
            "text",
            "Sonuç",
            display(
                value.get("primary", value.get("summary", value.get("metrics", {})))
            ),
        )
    ]
    artifacts.append(
        ResultArtifact(ident + ":parameters", "table", "Parametreler", display(spec))
    )
    artifacts.append(
        ResultArtifact(
            ident + ":warnings",
            "log",
            "Uyarılar ve tanılama",
            display(value.get("warnings", value.get("diagnostics", []))),
        )
    )
    if "model" in capability_id or "pipeline" in value:
        artifacts.append(
            ResultArtifact(
                ident + ":model",
                "model",
                "Model kaydı",
                display(
                    {
                        k: value[k]
                        for k in (
                            "pipeline",
                            "model",
                            "model_card",
                            "selection",
                            "plan",
                            "card",
                        )
                        if k in value
                    }
                ),
            )
        )
    return dict(
        id=ident,
        capability=capability_id,
        label=spec.get("question", spec.get("title", capability_id)),
        readonly=status == "readonly",
        compatibility=reason,
        dataset=value.get(
            "dataset_version", value.get("dataset_version_ids", "Eski kayıtta yok")
        ),
        method_version=value.get("method_version", 1),
        parameter_version=value.get("parameter_version", 1),
        filters=(
            "Filtre yok"
            if spec.get("view", {}).get("filters") == []
            else display(
                spec.get("view", {}).get(
                    "filters", value.get("filters", "Eski kayıtta yok")
                )
            )
        ),
        scope=" · ".join(
            str(v)
            for v in (
                value.get("scope", spec.get("scope", "Eski kayıtta yok")),
                "Evren: "
                + str(
                    value.get(
                        "population_n", value.get("population_rows", "Eski kayıtta yok")
                    )
                ),
                "Kullanılan: "
                + str(value.get("used_rows", value.get("used_n", "Eski kayıtta yok"))),
            )
        ),
        seed=display(provenance.get("seed", value.get("seed", "Eski kayıtta yok"))),
        environment=display(provenance),
        parameters=display(spec),
        warnings=display(value.get("warnings", [])),
        artifacts=[
            dict(
                asdict(a),
                rows=[dict(name=k, value=display(v)) for k, v in spec.items()]
                if a.kind == "table"
                else [],
            )
            for a in artifacts
        ],
    )


class WorkspaceController(QObject):
    changed = Signal()
    navigate = Signal(int, str)
    restorePreset = Signal(str)
    selectMethod = Signal(str, str)

    def __init__(self, projects, statistics, charts, controllers=(), parent=None):
        super().__init__(parent)
        self.projects, self.statistics, self.charts = projects, statistics, charts
        self.controllers = (statistics, charts, *controllers)
        self._query = self._selected = self._error = ""
        self._compare = []
        self._live = {}
        self._root = None
        self._workspace_state = None
        self._workspace_path = None
        projects.changed.connect(self.refresh)
        for controller in self.controllers:
            controller.changed.connect(self.refresh)
        self.refresh()

    def state(self):
        state = self._workspace_state
        if state is None:
            return dict(schema_version=1, tabs=[], favorites=[], presets=[])
        valid = (
            isinstance(state, dict)
            and type(state.get("schema_version")) is int
            and state.get("schema_version") == 1
            and set(state) <= {"schema_version", "tabs", "favorites", "presets"}
            and all(
                isinstance(state.get(k, []), list)
                for k in ("tabs", "favorites", "presets")
            )
            and all(
                isinstance(i, str)
                for k in ("tabs", "favorites")
                for i in state.get(k, [])
            )
            and all(
                isinstance(p, dict)
                and {
                    "name",
                    "capability_id",
                    "method_version",
                    "parameter_version",
                    "parameters",
                }
                <= set(p)
                and isinstance(p["parameters"], dict)
                for p in state.get("presets", [])
            )
        )
        if not valid:
            self._error = "Çalışma alanı sürümü/biçimi desteklenmiyor; eski kayıt korunur, sonuçlar salt okunur gösterilir."
            return dict(schema_version=0, tabs=[], favorites=[], presets=[])
        return state

    def refresh(self):
        root = str(self.projects.store.root) if self.projects.store else None
        if root != self._root:
            self._live, self._compare, self._selected = {}, [], ""
            self._root = root
            self._workspace_state = None
            self._workspace_path = None
            if root:
                # Machine-local presentation preferences. No new project schema,
                # user data store, or copy of analytical results is introduced.
                key = self.projects.store.manifest["project_id"]
                digest = hashlib.sha256(key.encode()).hexdigest()
                self._workspace_path = self.projects.config / (
                    "expert-workspace-" + digest + ".json"
                )
                if self._workspace_path.exists():
                    try:
                        if self._workspace_path.stat().st_size > 18000:
                            raise ValueError("Workspace too large")
                        self._workspace_state = json.loads(
                            self._workspace_path.read_text()
                        )
                    except (OSError, ValueError):
                        self._workspace_state = {"schema_version": 0}
        if root:
            for controller in self.controllers:
                value = getattr(controller, "result", None)
                if not isinstance(value, dict) or not value.get(
                    "result_version", value.get("run_id")
                ):
                    continue
                dataset = value.get("dataset_version")
                if dataset and dataset not in {
                    d["version_id"] for d in self.projects.draft["datasets"]
                }:
                    continue
                ident = value.get("result_version", value.get("run_id"))
                if ident not in self._live:
                    method = value.get("method", value.get("spec", {}).get("kind", ""))
                    capability = (
                        ("statistics." + method.replace("_", "-"))
                        if controller is self.statistics
                        else (
                            "chart." + method
                            if controller is self.charts
                            else {
                                "PreparationController": "model.prepare",
                                "ValidationController": "model.baseline",
                                "UnsupervisedController": "model.unsupervised",
                                "TextController": "text.inspect",
                                "TimeSeriesController": "model.time-series",
                                "LifecycleController": "model.lifecycle",
                            }.get(type(controller).__name__, "unknown")
                        )
                    )
                    self._live[ident] = (capability, copy.deepcopy(value))
                    if len(self._live) > 64:
                        del self._live[next(iter(self._live))]
                    self._selected = ident
        self.changed.emit()

    def results(self):
        rows = {}
        records = self.projects.draft["results"]
        pinned = set(self.state().get("tabs", [])) | {self._selected}
        for index, record in enumerate(records):
            value = next(
                (
                    record[k]
                    for k in (
                        "analysis",
                        "chart",
                        "baseline",
                        "preparation",
                        "monitoring",
                        "scenario",
                        "scientific_report",
                        "review_event",
                        "privacy_event",
                        "plugin_result",
                        "unsupervised",
                        "time_series",
                        "text",
                    )
                    if isinstance(record.get(k), dict)
                ),
                record,
            )
            ident = value.get(
                "result_version",
                record.get("result_version", value.get("run_id", record["id"])),
            )
            if index < len(records) - 64 and ident not in pinned:
                continue
            rows[ident] = describe_result(
                ident, record.get("capability_id", "unknown"), value
            )
            uris = value.get("artifact_uris", {})
            if ident == self._selected and "png" in uris and self.projects.store:
                uri = uris["png"]
                fp = self.projects.store.manifest["artifacts"].get(uri)
                if fp and fp["size"] <= 16 * 1024**2:
                    path = self.projects.store.path(uri)
                    if file_hash(path) == {k: fp[k] for k in ("size", "sha256")}:
                        rows[ident]["artifacts"].append(
                            asdict(
                                ResultArtifact(
                                    ident + ":chart",
                                    "chart",
                                    "Grafik",
                                    uri=QUrl.fromLocalFile(str(path)).toString(),
                                )
                            )
                        )
        for ident, (capability, value) in self._live.items():
            if ident not in rows:
                rows[ident] = describe_result(ident, capability, value)
        return rows

    def write(self, **changes):
        if not self.projects.store or self.projects.readOnly or self.projects.busy:
            self._error = (
                "Çalışma alanını kaydetmek için yazılabilir ve boşta bir proje açın."
            )
            self.changed.emit()
            return False
        if self.state()["schema_version"] != 1:
            self.changed.emit()
            return False
        state = dict(self.state(), schema_version=1, **changes)
        if len(json.dumps(state, ensure_ascii=False).encode()) > 18000:
            self._error = "Çalışma alanı sınırına ulaşıldı; kullanılmayan sekme veya presetleri kaldırın."
            self.changed.emit()
            return False
        raw = json.dumps(state, ensure_ascii=False, allow_nan=False).encode()
        file = QSaveFile(str(self._workspace_path))
        file.setDirectWriteFallback(False)
        if (
            not file.open(QIODevice.WriteOnly)
            or not file.setPermissions(QFileDevice.ReadOwner | QFileDevice.WriteOwner)
            or file.write(raw) != len(raw)
            or not file.commit()
        ):
            file.cancelWriting()
            self._error = "Çalışma alanı tercihleri kaydedilemedi; eski dosya korundu."
            self.changed.emit()
            return False
        self._workspace_state = copy.deepcopy(state)
        self._error = ""
        self.changed.emit()
        return True

    @Property("QVariantList", notify=changed)
    def modules(self):
        favorites = self.state().get("favorites", [])
        rows = []
        for c in discover():
            label = (
                LABELS
                | MODEL_LABELS
                | RESAMPLING_LABELS
                | EXPERIMENT_LABELS
                | BAYES_LABELS
                | CAUSAL_LABELS
                | SURVIVAL_LABELS
                | DIMENSION_LABELS
            ).get(
                c.capability_id.removeprefix("statistics.").replace("-", "_"),
                c.capability_id,
            )
            if fold(self._query) not in fold(
                label + " " + c.capability_id + " " + c.method
            ):
                continue
            enabled, reason = availability(c)
            rows.append(
                dict(
                    id=c.capability_id,
                    label=label,
                    maturity=c.maturity,
                    enabled=enabled,
                    reason=reason,
                    favorite=c.capability_id in favorites,
                )
            )
        return sorted(rows, key=lambda r: (not r["favorite"], r["label"]))

    query = Property(str, lambda self: self._query, notify=changed)

    resultRows = Property(
        "QVariantList", lambda self: list(self.results().values()), notify=changed
    )
    selected = Property(
        "QVariantMap",
        lambda self: self.results().get(self._selected, {}),
        notify=changed,
    )
    tabs = Property(
        "QVariantList",
        lambda self: [
            self.results()[i]
            for i in self.state().get("tabs", [])
            if i in self.results()
        ],
        notify=changed,
    )
    presets = Property(
        "QVariantList", lambda self: self.state().get("presets", []), notify=changed
    )
    comparison = Property(
        "QVariantList",
        lambda self: [self.results()[i] for i in self._compare if i in self.results()],
        notify=changed,
    )
    errorText = Property(str, lambda self: self._error, notify=changed)

    @Slot(str)
    def search(self, query):
        self._query = query[:200]
        self.changed.emit()

    @Slot(str, result="QVariantMap")
    def details(self, ident):
        return asdict(get_capability(ident))

    @Slot(str)
    def activate(self, ident):
        c = get_capability(ident)
        enabled, reason = availability(c)
        if not enabled:
            self._error = reason
            self.changed.emit()
            return
        if ident.startswith("code."):
            self.navigate.emit(6, ident)
            for controller in self.controllers:
                if hasattr(controller, "selectCode"):
                    controller.selectCode.emit()
        elif ident.startswith(("model.stream.", "model.special.")):
            self.navigate.emit(5, ident)
            for controller in self.controllers:
                if hasattr(controller, "selectStream"):
                    controller.selectStream.emit(ident)
        elif ident.startswith("model.graph."):
            self.navigate.emit(5, ident)
            for controller in self.controllers:
                if hasattr(controller, "selectGraph"):
                    controller.selectGraph.emit(ident.removeprefix("model.graph."))
        elif ident.startswith("model.pattern."):
            self.navigate.emit(5, ident)
            for controller in self.controllers:
                if hasattr(controller, "selectPattern"):
                    controller.selectPattern.emit(
                        ident.removeprefix("model.pattern.").replace("-", "_")
                    )
        elif ident.startswith("model.recommendation."):
            self.navigate.emit(5, ident)
            for controller in self.controllers:
                if hasattr(controller, "selectRecommendation"):
                    controller.selectRecommendation.emit(
                        ident.removeprefix("model.recommendation.")
                    )
        elif ident.startswith("model.audio."):
            self.navigate.emit(5, ident)
            for controller in self.controllers:
                if hasattr(controller, "selectAudio"):
                    controller.selectAudio.emit(ident.removeprefix("model.audio."))
        elif ident.startswith("model.vision."):
            self.navigate.emit(5, ident)
            for controller in self.controllers:
                if hasattr(controller, "selectVision"):
                    controller.selectVision.emit(ident.removeprefix("model.vision."))
        elif ident.startswith("model.neural."):
            self.navigate.emit(5, ident)
            for controller in self.controllers:
                if hasattr(controller, "selectNeural"):
                    controller.selectNeural.emit(ident.removeprefix("model.neural."))
        elif ident.startswith("text.nlp."):
            self.navigate.emit(5, ident)
            for controller in self.controllers:
                if hasattr(controller, "selectNLP"):
                    controller.selectNLP.emit(ident.removeprefix("text.nlp."))
        elif ident.startswith("model.signal."):
            self.navigate.emit(5, ident)
            for controller in self.controllers:
                if hasattr(controller, "selectSignal"):
                    controller.selectSignal.emit(ident.removeprefix("model.signal."))
        elif ident.startswith("model.temporal."):
            self.navigate.emit(5, ident)
            for controller in self.controllers:
                if hasattr(controller, "selectTemporal"):
                    controller.selectTemporal.emit(
                        ident.removeprefix("model.temporal.")
                    )
        elif ident.startswith("learn.lab."):
            self.navigate.emit(7, ident)
        elif ident.startswith("environment."):
            self.navigate.emit(6, ident)
        elif ident.startswith("plugin."):
            self.navigate.emit(6, ident)
        elif ident.startswith("privacy."):
            self.navigate.emit(6, ident)
        elif ident.startswith("share."):
            self.navigate.emit(6, ident)
        elif ident.startswith("report."):
            self.navigate.emit(6, ident)
        elif ident.startswith("scenario."):
            self.navigate.emit(5, ident)
        elif ident.startswith("model.monitor."):
            self.navigate.emit(5, ident)
        elif ident == "model.experiment-registry":
            self.navigate.emit(5, ident)
        elif ident.startswith("model.explain."):
            self.navigate.emit(5, ident)
            for controller in self.controllers:
                if hasattr(controller, "selectExplanation"):
                    controller.selectExplanation.emit(
                        ident.removeprefix("model.explain.")
                    )
        elif ident.startswith("model.uncertainty."):
            for controller in self.controllers:
                if hasattr(controller, "selectUncertainty"):
                    controller.selectUncertainty.emit(
                        ident.removeprefix("model.uncertainty.")
                    )
            self.navigate.emit(5, ident)
        elif ident.startswith("model.search."):
            self.navigate.emit(5, ident)
            for controller in self.controllers:
                if type(controller).__name__ == "SearchController":
                    controller.selectMethod.emit(ident.removeprefix("model.search."))
                    break
        elif ident.startswith("model.family."):
            purpose, method = ident.removeprefix("model.family.").split(".")
            self.navigate.emit(5, ident)
            for controller in self.controllers:
                if type(controller).__name__ == "ValidationController":
                    controller.selectFamily.emit(purpose, method.replace("-", "_"))
                    break
        elif c.method.startswith("immutable_contract_"):
            self.navigate.emit(1, ident)
        elif ident.startswith("statistics."):
            method = ident.removeprefix("statistics.").replace("-", "_")
            path = (
                "dimensions"
                if method in DIMENSION_METHODS
                else "survival"
                if method in SURVIVAL_METHODS
                else "causal"
                if method in CAUSAL_METHODS
                else "bayes"
                if method in BAYES_METHODS
                else "experiments"
                if method in EXPERIMENT_METHODS
                else "resampling"
                if method in RESAMPLING_METHODS
                else "models"
                if method in MODEL_METHODS
                else next((p for p, ms in METHODS.items() if method in ms), "advanced")
            )
            self.navigate.emit(4, ident)
            self.selectMethod.emit(path, method)
        else:
            prefix = ident.split(".")[0]
            self.navigate.emit(
                {
                    "import": 1,
                    "dataset": 1,
                    "operation": 2,
                    "transform": 2,
                    "clean": 2,
                    "chart": 3,
                    "dashboard": 3,
                    "figure": 3,
                    "statistics": 4,
                    "model": 5,
                    "text": 5,
                    "workflow": 2,
                    "export": 6,
                }.get(prefix, 1),
                ident,
            )

    @Slot(str)
    def favorite(self, ident):
        get_capability(ident)
        values = list(self.state().get("favorites", []))
        values.remove(ident) if ident in values else values.append(ident)
        self.write(favorites=values[:76])

    @Slot(str)
    def selectResult(self, ident):
        if ident in self.results():
            self._selected = ident
            self.changed.emit()

    @Slot(str)
    def pin(self, ident):
        # Only published results can be persistent tabs; run metadata is not copied.
        saved = {
            r.get("result_version", r["id"]) for r in self.projects.draft["results"]
        }
        if ident not in saved:
            self._error = (
                "Önce sonucu kendi ekranındaki kaydet eylemiyle projeye kaydedin."
            )
            self.changed.emit()
            return
        values = list(self.state().get("tabs", []))
        values.remove(ident) if ident in values else values.append(ident)
        self.write(tabs=values[-24:])

    @Slot(str)
    def compare(self, ident):
        if ident in self.results():
            self._compare.remove(
                ident
            ) if ident in self._compare else self._compare.append(ident)
            self._compare = self._compare[-2:]
            self.changed.emit()

    @Slot(str, str)
    def savePreset(self, name, spec_json):
        from veri_ufku.statistics.contracts import AnalysisSpec

        try:
            spec = AnalysisSpec.from_dict(json.loads(spec_json))
            capability = get_capability("statistics." + spec.method.replace("_", "-"))
            # Validate the existing spec; never persist the old assumption approval.
            spec.validate(
                (self.statistics.data.dataset() or {})["import_metadata"]["columns"]
            )
            data = spec.data()
            data["assumptions_confirmed"] = False
            data["view"] = {}
            presets = [
                p for p in self.state().get("presets", []) if p["name"] != name[:80]
            ]
            presets.append(
                dict(
                    name=name[:80] or "Preset",
                    capability_id=capability.capability_id,
                    method_version=capability.semantic_version,
                    parameter_version=capability.version,
                    parameters=data,
                )
            )
            self.write(presets=presets[-20:])
        except (ValueError, KeyError, TypeError) as error:
            self._error = str(error)
            self.changed.emit()

    @Slot(int)
    def applyPreset(self, index):
        values = self.state().get("presets", [])
        if not 0 <= index < len(values):
            return
        preset = values[index]
        status, reason = result_compatibility(
            preset["capability_id"],
            preset["method_version"],
            preset["parameter_version"],
        )
        if status != "compatible":
            self._error = reason
            self.changed.emit()
            return
        from veri_ufku.statistics.contracts import AnalysisSpec

        try:
            spec = AnalysisSpec.from_dict(preset["parameters"])
            if preset["capability_id"] != "statistics." + spec.method.replace("_", "-"):
                raise ValueError("Preset yöntemi ve parametre tarifi uyuşmuyor.")
            spec.validate(
                (self.statistics.data.dataset() or {})["import_metadata"]["columns"]
            )
        except (ValueError, KeyError, TypeError) as error:
            self._error = str(error)
            self.changed.emit()
            return
        self.activate(preset["capability_id"])
        self.statistics.invalidate()
        self.restorePreset.emit(json.dumps(preset["parameters"]))
