"""Data-only preparation intent; model fitting belongs to later authorized phases."""

import re
from dataclasses import asdict, dataclass

from veri_ufku.storage.project_model import ProjectError, entity_id

PURPOSES = {
    "regression": "Sayısal hedef tahmini",
    "classification": "Kategori hedef tahmini",
    "clustering": "Benzer kayıtları gruplama",
    "anomaly": "Sıra dışı kayıtları bulma",
}
FAMILIES = {
    "linear": "Düzenlileştirilmiş doğrusal model",
    "distance": "Uzaklığa dayalı model",
    "tree": "Ağaç tabanlı model",
}


def identifier(column, semantics):
    return semantics.get(column["id"], {}).get("role") == "identifier" or bool(
        re.search(
            r"(^|[_\s])(id|uuid|kimlik|record_id|person_id)($|[_\s])",
            column["name"],
            re.I,
        )
    )


@dataclass(frozen=True)
class PreparationSpec:
    purpose: str
    features: tuple
    target: str = ""
    family: str = "tree"
    source_version: str = ""
    history_action: str = "review"
    numeric_imputation: str = "median"
    categorical_imputation: str = "most_frequent"
    encoding: str = "onehot"
    scaling: str = "auto"
    date_features: bool = True
    selection: str = "none"
    group: str = ""
    time: str = ""
    allow_identifiers: bool = False
    prediction_context: str = ""
    history_note: str = ""
    invalid_numeric: str = "reject"
    precision: str = "reject"
    text: dict | None = None
    missing_indicator: bool = False
    imputation_neighbors: int = 5
    imputation_iterations: int = 10
    imputation_seed: int = 42

    @classmethod
    def from_dict(cls, value):
        try:
            result = cls(**value)
            if not isinstance(result.features, (list, tuple)) or any(
                not isinstance(v, str) for v in result.features
            ):
                raise TypeError()
            return cls(**dict(asdict(result), features=tuple(result.features)))
        except (TypeError, ValueError):
            raise ProjectError("Model hazırlama planı alanları geçersiz.") from None

    def data(self):
        value = dict(asdict(self), features=list(self.features))
        if self.text is None:
            value.pop("text")
        for name, default in (
            ("missing_indicator", False),
            ("imputation_neighbors", 5),
            ("imputation_iterations", 10),
            ("imputation_seed", 42),
        ):
            if value[name] == default:
                value.pop(name)
        return value

    def validate(self, columns):
        for name in (
            "purpose",
            "target",
            "family",
            "source_version",
            "history_action",
            "numeric_imputation",
            "categorical_imputation",
            "encoding",
            "scaling",
            "selection",
            "group",
            "time",
            "prediction_context",
            "history_note",
            "invalid_numeric",
            "precision",
        ):
            if not isinstance(getattr(self, name), str):
                raise ProjectError("Plan seçimi ve sütun kimliği metin olmalı.")
        if self.purpose not in PURPOSES or self.family not in FAMILIES:
            raise ProjectError("Amaç/model ailesi geçersiz.")
        if (
            self.purpose == "clustering"
            and self.family != "distance"
            or self.purpose == "anomaly"
            and self.family == "linear"
        ):
            raise ProjectError(
                "Bu amaçta seçili model ailesi hazırlama planında desteklenmiyor."
            )
        for name in ("date_features", "allow_identifiers", "missing_indicator"):
            if type(getattr(self, name)) is not bool:
                raise ProjectError("Plan onayı geçersiz.")
        allowed = {
            "history_action": ("review", "raw", "relocate"),
            "numeric_imputation": ("median", "mean", "none", "knn", "iterative"),
            "categorical_imputation": ("most_frequent", "none"),
            "encoding": ("onehot", "ordinal"),
            "scaling": ("auto", "none", "standard"),
            "selection": ("none", "variance"),
            "invalid_numeric": ("reject", "as_missing"),
            "precision": ("reject", "approximate"),
        }
        if any(getattr(self, k) not in values for k, values in allowed.items()):
            raise ProjectError("Encoding/scaling/imputasyon/geçmiş seçimi geçersiz.")
        for name, low, high in (
            ("imputation_neighbors", 1, 20),
            ("imputation_iterations", 1, 30),
            ("imputation_seed", 0, 2**32 - 1),
        ):
            if (
                type(getattr(self, name)) is not int
                or not low <= getattr(self, name) <= high
            ):
                raise ProjectError("İmputasyon komşu/iterasyon/seed sınırı geçersiz.")
        if max(len(self.prediction_context), len(self.history_note)) > 1000:
            raise ProjectError("Plan açıklaması en fazla1000 karakter olmalı.")
        if self.text is not None:
            from veri_ufku.analytics.text_contracts import TextSpec

            config = TextSpec.from_dict(self.text)
            if (
                self.purpose != "classification"
                or list(self.features) != [config.column]
                or self.selection != "none"
            ):
                raise ProjectError(
                    "Metin sınıflandırması tek metin özelliği ve mevcut kategori hedefi ister; variance seçimi desteklenmez."
                )
        ids = {c["id"] for c in columns}
        if (
            not self.features
            or len(self.features) > 100
            or len(set(self.features)) != len(self.features)
            or not set(self.features) <= ids
        ):
            raise ProjectError("En az bir, en fazla100 farklı mevcut özellik seçin.")
        supervised = self.purpose in ("regression", "classification")
        if supervised and self.target not in ids or not supervised and self.target:
            raise ProjectError(
                "Tahmin için mevcut hedef seçin; hedef gerektirmeyen amaçta hedef boş olmalı."
            )
        if self.target in self.features or self.group in self.features:
            raise ProjectError("Hedef ve grup anahtarı özelliklere dahil edilemez.")
        if (
            any(v and v not in ids for v in (self.group, self.time))
            or self.target
            and self.target in (self.group, self.time)
            or self.group
            and self.group == self.time
        ):
            raise ProjectError(
                "Hedef/grup/zaman alanlarını farklı ve mevcut sütunlardan seçin."
            )
        if self.source_version:
            entity_id(self.source_version, "dv")


def validate_saved(record, versions):
    result = record["preparation"]
    if (
        result["schema"] != "PreparationReport/v1"
        or result["fitted"] is not False
        or result["plan"]["fit_state"] != "not_fitted"
        or result["plan"]["fitted_parameters"] != {}
        or result["leakage_certified"] is not False
        or result["history"]["leakage_certified"] is not False
        or result["provenance"]["fit_scope"] is not None
    ):
        raise ProjectError("Model hazırlığı henüz fit edilmemiş plan olmalı.")
    if record["capability_id"] != "model.prepare" or record[
        "dataset_version_ids"
    ] != list(dict.fromkeys([result["origin_version"], result["dataset_version"]])):
        raise ProjectError("Model planının veri sürümü bağı uyuşmuyor.")
    dataset = versions[result["dataset_version"]]
    spec = PreparationSpec.from_dict(result["spec"])
    spec.validate(dataset["import_metadata"]["columns"])
    if spec.source_version != result["dataset_version"]:
        raise ProjectError("Hazırlama kaynağı tarifle uyuşmuyor.")
    if (
        result["dataset_n"] != dataset["import_metadata"]["row_count"]
        or not 0 <= result["eligible_n"] <= result["dataset_n"]
        or result["excluded_target_n"] != result["dataset_n"] - result["eligible_n"]
        or result["status"] != ("blocked" if result["blockers"] else "review_required")
    ):
        raise ProjectError("Hazırlık sayımları veya risk durumu tutarsız.")
    from veri_ufku.modeling.plan import blueprint

    expected = blueprint(
        spec,
        dataset["import_metadata"]["columns"],
        dataset.get("semantic_metadata", {}),
        result["history"],
    )
    if {k: v for k, v in result["plan"].items() if k != "version_id"} != expected:
        raise ProjectError("Plan adımları veya kolon eşlemesi tarifle uyuşmuyor.")
    entity_id(result["plan"]["version_id"], "ml-pipeline")
