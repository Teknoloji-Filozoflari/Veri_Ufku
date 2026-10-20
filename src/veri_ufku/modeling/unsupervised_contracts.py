"""Data-only, Qt-free settings and saved exploratory result invariants."""

import json
import math
from dataclasses import asdict, dataclass

from veri_ufku.storage.project_model import ProjectError

CLUSTER_METHODS = ("kmeans", "dbscan", "agglomerative", "gmm", "optics", "hdbscan")
METHODS = CLUSTER_METHODS + (
    "isolation_forest",
    "iqr",
    "lof",
    "one_class_svm",
    "robust_covariance",
)
LIMITS = dict.fromkeys(METHODS, 3000)
LIMITS.update(kmeans=100000, isolation_forest=100000, iqr=100000)


@dataclass(frozen=True)
class UnsupervisedSpec:
    method: str
    features: tuple[str, ...]
    scaling: str = "standard"
    seed: int = 42
    clusters: int = 3
    eps: float = 0.5
    min_samples: int = 5
    contamination: float = 0.05
    iqr_multiplier: float = 1.5
    threshold_mode: str = "fraction"
    score_threshold: float = 0.6

    metric: str = "euclidean"
    linkage: str = "ward"
    covariance_type: str = "full"
    xi: float = 0.05
    min_cluster_size: int = 5
    stability_runs: int = 0
    compare_methods: tuple[str, ...] = ()
    anomaly_mode: str = "outlier"
    training_fraction: float = 0.7
    nu: float = 0.05
    gamma: str = "scale"
    label_column: str = ""
    false_positive_cost: float = 1.0
    false_negative_cost: float = 1.0

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or set(value) - set(cls.__dataclass_fields__):
            raise ProjectError("Etiketsiz analiz ayarları geçersiz.")
        try:
            return cls(
                **dict(
                    value,
                    features=tuple(value["features"]),
                    compare_methods=tuple(value.get("compare_methods", ())),
                )
            )
        except (TypeError, KeyError) as error:
            raise ProjectError("Yöntem ve ölçümler seçilmeli.") from error

    def data(self):
        return dict(asdict(self), features=list(self.features))

    def validate(self, columns):
        if self.method not in METHODS or self.scaling not in ("standard", "none"):
            raise ProjectError("Yöntem/ölçekleme desteklenmiyor.")
        if (
            not 1 <= len(self.features) <= 20
            or len(set(self.features)) != len(self.features)
            or not set(self.features) <= {c["id"] for c in columns}
        ):
            raise ProjectError("1–20 farklı ölçüm seçin.")
        for name, low, high in (
            ("seed", 0, 2**32 - 1),
            ("clusters", 1, 20),
            ("min_samples", 2, 100),
        ):
            v = getattr(self, name)
            if type(v) is not int or not low <= v <= high:
                raise ProjectError(f"{name} ayarı {low}–{high} aralığında olmalı.")
        for name, low, high in (
            ("eps", 0, 1000000),
            ("contamination", 0, 0.5),
            ("iqr_multiplier", 0, 10),
            ("score_threshold", 0, 1),
        ):
            v = getattr(self, name)
            if (
                type(v) not in (int, float)
                or not math.isfinite(v)
                or not low < v <= high
            ):
                raise ProjectError(
                    f"{name} sonlu ve ({low}, {high}] aralığında olmalı."
                )
        if self.threshold_mode not in ("fraction", "score"):
            raise ProjectError("Eşik modu desteklenmiyor.")
        if self.metric not in ("euclidean", "manhattan") or self.linkage not in (
            "ward",
            "complete",
            "average",
            "single",
        ):
            raise ProjectError("Mesafe/linkage desteklenmiyor.")
        methods = (self.method,) + self.compare_methods
        if (
            len(set(self.compare_methods)) != len(self.compare_methods)
            or any(m not in CLUSTER_METHODS for m in self.compare_methods)
            or (self.compare_methods and self.method not in CLUSTER_METHODS)
        ):
            raise ProjectError("Karşılaştırma yalnız kümeleme yöntemleri içindir.")
        if self.metric != "euclidean" and (
            any(
                m in ("kmeans", "gmm", "one_class_svm", "robust_covariance")
                for m in methods
            )
            or ("agglomerative" in methods and self.linkage == "ward")
        ):
            raise ProjectError(
                "KMeans/GMM/Ward/SVM/covariance Euclidean numeric temsil gerektirir."
            )
        if self.covariance_type not in (
            "full",
            "tied",
            "diag",
            "spherical",
        ) or self.gamma not in ("scale", "auto"):
            raise ProjectError("Covariance/gamma desteklenmiyor.")
        for name, low, high in (
            ("stability_runs", 0, 10),
            ("min_cluster_size", 2, 100),
        ):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ProjectError(f"{name} aralığı {low}–{high}.")
        for name, low, high in (
            ("xi", 0, 1),
            ("training_fraction", 0.2, 0.9),
            ("nu", 0, 1),
            ("false_positive_cost", 0, 1e9),
            ("false_negative_cost", 0, 1e9),
        ):
            value = getattr(self, name)
            if (
                type(value) not in (int, float)
                or not math.isfinite(value)
                or not low < value <= high
            ):
                raise ProjectError(f"{name} geçersiz.")
        if self.anomaly_mode not in ("outlier", "novelty") or (
            self.anomaly_mode == "novelty"
            and self.method not in ("lof", "one_class_svm", "robust_covariance")
        ):
            raise ProjectError(
                "Novelty yalnız LOF/OneClassSVM/robust covariance yolunda."
            )
        if self.label_column and (
            self.label_column not in {c["id"] for c in columns}
            or self.label_column in self.features
            or self.method in CLUSTER_METHODS
        ):
            raise ProjectError("Anomali etiketi ayrı bir sütun olmalı.")
        if self.method == "iqr" and len(self.features) != 1:
            raise ProjectError("Basit IQR yöntemi tek sayısal sütun içindir.")


def validate_summary(value, dataset):
    spec = UnsupervisedSpec.from_dict(value["spec"])
    spec.validate(dataset["import_metadata"]["columns"])
    if (
        value["schema"] != "UnsupervisedRun/v1"
        or value["dataset_version"] != dataset["version_id"]
        or value["rows"] != dataset["import_metadata"]["row_count"]
        or value["provenance"]["seed"] != spec.seed
        or value["projection"] is not None
    ):
        raise ProjectError("Etiketsiz analiz kapsam/sürüm/seed bağı geçersiz.")
    if (
        sum(p["count"] for p in value["profiles"]) != value["rows"]
        or (
            not spec.label_column
            and (
                value["evaluation"]["precision"] is not None
                or value["evaluation"]["recall"] is not None
            )
        )
        or value["new_data"]["available"]
        and (spec.method == "dbscan" or not value.get("model_card"))
        or value["new_data"]["native_support"]
        != (
            spec.method
            in (
                "kmeans",
                "isolation_forest",
                "iqr",
                "gmm",
                "one_class_svm",
                "robust_covariance",
            )
            or (spec.method == "lof" and spec.anomaly_mode == "novelty")
        )
    ):
        raise ProjectError(
            "Etiketsiz analiz profil/değerlendirme/yeni veri bağı geçersiz."
        )
    separation = value["silhouette"]
    if separation and separation["status"] == "valid":
        counts = [p["count"] for p in value["profiles"] if p["label"] != -1]
        if (
            len(counts) < 2
            or min(counts) < 3
            or sum(counts) > 3000
            or not isinstance(separation["value"], (int, float))
            or not -1 <= separation["value"] <= 1
        ):
            raise ProjectError("Geçersiz silhouette başarılı olarak kaydedilemez.")
    json.dumps(value, allow_nan=False)
