"""Model aşaması yol panosu: Mod 2 tarifleri, kayıt durumu, opsiyonel modül erişimi."""

import copy

from PySide6.QtCore import Property, QObject, Signal, Slot

from veri_ufku.storage.project_model import ProjectError
from veri_ufku.ui.projects import project_error_text

# Şema Model aşamasındaki on alt başlığı; her biri için sonuç kaydı anahtarı.
ENTRY_RESULT_KEYS = {
    1: ("preparation",),
    2: ("mod2_plan",),
    3: ("baseline",),
    4: ("baseline",),
    5: ("unsupervised",),
    6: ("analysis",),
    7: ("baseline", "search", "experiment_event"),
    8: ("explanation",),
    9: (
        "time_series",
        "text_analysis",
        "graph",
        "stream",
        "audio",
        "vision",
    ),
    10: (
        "neural",
        "monitoring",
        "scenario",
        "pattern",
        "recommendation",
    ),
}

# B-06 kararı (2026-11-13): çekirdek kurulum = temel + keşif; yorum ve ileri
# yollar isteğe bağlı modüldür ve ortamda yoksa açıkça bildirilir.
OPTIONAL_MODULES = (
    ("model.explain.shap", "Yorum · SHAP", (8,)),
    ("model.neural.mlp", "İleri yollar · sinir ağı (MLP)", (10,)),
)


class ModelPathsController(QObject):
    """Model kataloğunun veri kaynağı: tarif listesi, durum, opsiyonel modüller."""

    changed = Signal()
    recipeOpened = Signal(str)

    def __init__(self, projects, preparation, data, parent=None):
        super().__init__(parent)
        self.projects = projects
        self.preparation = preparation
        self.data = data
        self._error = ""
        projects.changed.connect(self.changed)

    errorText = Property(str, lambda self: self._error, notify=changed)

    def records(self):
        try:
            return self.projects.draft.get("results", [])
        except (AttributeError, TypeError):
            return []

    def recipes(self):
        """Saklanan tarifler: Mod 2 planları ve fit edilmemiş hazırlık planları."""
        values = []
        for record in self.records():
            plan = record.get("mod2_plan")
            if plan:
                values.append(
                    dict(
                        id=record["id"],
                        kind="mod2_plan",
                        label=("Mod 2 · Model için planla")
                        + " · "
                        + (plan.get("dataset_version") or "")[-8:],
                        status=plan.get("status", "planned"),
                        learn_scope=plan.get("learn_scope", "training_fold"),
                        dataset_version=plan.get("dataset_version", ""),
                        created_at=plan.get("created_at", ""),
                        reason=plan.get("reason", ""),
                        operations=[
                            dict(
                                kind=item.get("kind", ""),
                                method=item.get("method", ""),
                                column_ids=list(item.get("column_ids", [])),
                                parameters=copy.deepcopy(item.get("parameters") or {}),
                            )
                            for item in plan.get("operations", [])
                        ],
                    )
                )
                continue
            preparation = record.get("preparation")
            if not preparation:
                continue
            plan = preparation.get("plan") or {}
            values.append(
                dict(
                    id=record["id"],
                    kind="preparation",
                    label=("Hazırlık planı")
                    + " · "
                    + str(plan.get("version_id", ""))[-8:],
                    status=plan.get("fit_state", "not_fitted"),
                    learn_scope="training_fold",
                    dataset_version=preparation.get("dataset_version", ""),
                    created_at=str(
                        preparation.get("provenance", {}).get("created_at", "")
                    ),
                    reason=(
                        "Fit edilmemiş pipeline planı; öğrenilen adımlar "
                        "eğitim katında uygulanır."
                    ),
                    operations=[
                        dict(
                            kind=step.get("kind", ""),
                            method=step.get("kind", ""),
                            column_ids=list(step.get("input_column_ids", [])),
                            parameters=copy.deepcopy(step.get("parameters") or {}),
                            reason=step.get("reason", ""),
                            learned_scope=step.get("learned_scope", ""),
                        )
                        for step in plan.get("steps", [])
                    ],
                )
            )
        return values

    recipeList = Property("QVariantList", lambda self: self.recipes(), notify=changed)
    planCount = Property(int, lambda self: len(self.recipes()), notify=changed)

    def status_for(self, index):
        """Bir alt başlığın durumu yalnız gerçek kayıtlardan türetilir."""
        records = self.records()
        if index == 3:
            hit = any(r.get("baseline", {}).get("regression") for r in records)
        elif index == 4:
            hit = any(r.get("baseline", {}).get("classification") for r in records)
        else:
            keys = ENTRY_RESULT_KEYS.get(index, ())
            hit = any(any(key in record for key in keys) for record in records)
        return "done" if hit else "untouched"

    def statuses(self):
        return {str(index): self.status_for(index) for index in ENTRY_RESULT_KEYS}

    statusMap = Property("QVariantMap", lambda self: self.statuses(), notify=changed)

    def optional_modules(self):
        from veri_ufku.domain.capabilities import CAPABILITIES, availability

        values = []
        for ident, label, entries in OPTIONAL_MODULES:
            capability = CAPABILITIES.get(ident)
            if capability is None:
                values.append(
                    dict(
                        id=ident,
                        label=label,
                        available=False,
                        reason=("Bu yetenek kayıtta yok; yol kapalı."),
                        entries=list(entries),
                    )
                )
                continue
            installed, reason = availability(capability)
            values.append(
                dict(
                    id=ident,
                    label=label,
                    available=bool(installed),
                    reason=reason or "",
                    entries=list(entries),
                )
            )
        return values

    optionalModules = Property(
        "QVariantList", lambda self: self.optional_modules(), notify=changed
    )

    def leakage_text(self):
        """Model açılışındaki sızıntı uyarısı: tüm veriye uygulanmış öğrenilen dönüşüm."""
        from veri_ufku.ui.model_leakage import model_leakage_notice

        try:
            version = (self.data.dataset() or {}).get("version_id", "")
            return model_leakage_notice(self.projects.draft, version).get("text", "")
        except (AttributeError, KeyError, ProjectError):
            return "Sürüm geçmişi okunamadı. Sızıntı uyarısı uydurulmaz."

    leakageText = Property(str, lambda self: self.leakage_text(), notify=changed)

    @Slot(str)
    def openRecipe(self, ident):
        """Tarif kaydını aç: hazırlık planı model formuna, Mod 2 planı ise uyarıyla."""
        self._error = ""
        try:
            record = next((r for r in self.records() if r.get("id") == ident), None)
            if record is None:
                raise ProjectError("Tarif kaydı bulunamadı.")
            if "mod2_plan" in record:
                raise ProjectError(
                    "Mod 2 planı Hazırla aşamasında düzenlenir; "
                    "tarif Model aşamasında yalnız okunur ve uygulanır."
                )
            if "preparation" not in record:
                raise ProjectError("Bu kayıt açılabilir bir hazırlık planı değil.")
            self.preparation.openSaved(ident)
            self.recipeOpened.emit(ident)
            self.changed.emit()
        except (ProjectError, KeyError, StopIteration, ValueError) as error:
            self._error = project_error_text(error)
            self.changed.emit()
