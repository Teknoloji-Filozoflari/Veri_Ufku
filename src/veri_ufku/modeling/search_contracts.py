"""Declarative bounded conditional search; no user callbacks or executable distributions."""

import hashlib
import itertools
import math
import platform
import sys
from dataclasses import asdict, dataclass, field
from importlib.metadata import PackageNotFoundError, version
from importlib.util import find_spec
from pathlib import Path

from veri_ufku.modeling.family_contracts import (
    FAMILY_METHODS,
    OPTIONAL_FAMILIES,
    REGRESSION_FAMILIES,
    FamilyOptions,
)
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError

SEARCH_METHODS = ("grid", "random", "bayesian")
TUNABLE = {
    "depth": (
        "decision_tree",
        "extra_trees",
        "gradient_boosting",
        "hist_gradient",
        "bagging",
        "voting",
        "stacking",
    ),
    "trees": ("extra_trees", "gradient_boosting", "hist_gradient"),
    "alpha": ("elasticnet", "lasso", "sgd", "multinomial_nb", "voting", "stacking"),
    "l1_ratio": ("elasticnet", "sgd", "voting", "stacking"),
    "C": ("elasticnet", "lasso", "svm", "voting", "stacking"),
    "neighbors": ("knn",),
    "kernel": ("svm",),
    "learning_rate": ("gradient_boosting", "hist_gradient"),
    "scaling": FAMILY_METHODS,
    "max_iter": ("elasticnet", "lasso", "sgd", "svm", "voting", "stacking"),
}


def environment():
    root = Path(__file__).parent
    engine = hashlib.sha256()
    for name in (
        "search.py",
        "search_contracts.py",
        "validation.py",
        "families.py",
        "preparation.py",
        "baseline.py",
        "contracts.py",
    ):
        engine.update(name.encode())
        engine.update((root / name).read_bytes())
    out = {
        "search_engine": "SearchRun/v1",
        "engine_sha256": engine.hexdigest(),
        "python": sys.version,
        "architecture": platform.machine(),
    }
    for name in ("scikit-learn", "numpy", "polars", "scipy", "optuna"):
        try:
            out[name] = version(name)
        except PackageNotFoundError:
            out[name] = "absent"
    return out


def backend_available(method):
    return method != "bayesian" or find_spec("optuna") is not None


@dataclass(frozen=True)
class SearchSpec:
    method: str = "random"
    space: dict = field(
        default_factory=lambda: {
            "methods": ["decision_tree"],
            "parameters": [{"name": "depth", "values": [2, 4]}],
        }
    )
    options: dict = field(default_factory=lambda: FamilyOptions().data())
    trials: int = 2
    attempts: int = 60
    inner_folds: int = 2
    seed: int = 49
    metric: str = "auto"
    constraints: dict = field(default_factory=dict)
    wall_seconds: float = 120
    ram_bytes: int = 2 * 1024**3
    concurrency: int = 1
    prune_after_folds: int = 0
    prune_loss_above: float = 1000000
    early_stopping: bool = False
    patience: int = 1
    curves: bool = True
    calibration: bool = False

    @classmethod
    def from_dict(cls, value, require_backend=True):
        if not isinstance(value, dict):
            raise ProjectError("Arama tarifi bir nesne olmalı.")
        try:
            result = cls(**value)
        except TypeError:
            raise ProjectError("Arama tarifi bilinmeyen alan içeriyor.") from None
        result.validate(require_backend)
        return result

    def data(self):
        return asdict(self)

    def validate(self, require_backend=True):
        if self.method not in SEARCH_METHODS:
            raise ProjectError("Grid/random/optional Bayesian yöntemini seçin.")
        if require_backend and not backend_available(self.method):
            raise ProjectError(
                "Optional Optuna ortamı yok; Bayesian compute doğrulanmadı."
            )
        for name, low, high in (
            ("trials", 1, 12),
            ("attempts", 1, 200),
            ("inner_folds", 2, 4),
            ("seed", 0, 2**32 - 1),
            ("prune_after_folds", 0, 3),
            ("patience", 1, 3),
        ):
            v = getattr(self, name)
            if type(v) is not int or not low <= v <= high:
                raise ProjectError(f"{name} sınırı {low}–{high}.")
        if self.concurrency != 1 or type(self.concurrency) is not int:
            raise ProjectError("Bu CPU adapter concurrency=1; paralel trial kapalı.")
        if (
            type(self.ram_bytes) is not int
            or not 64 * 1024**2 <= self.ram_bytes <= 8 * 1024**3
        ):
            raise ProjectError("Arama RAM bütçesi 64MiB–8GiB olmalı.")
        if (
            type(self.wall_seconds) not in (int, float)
            or not math.isfinite(self.wall_seconds)
            or not 1 <= self.wall_seconds <= 600
        ):
            raise ProjectError("Arama süre bütçesi 1–600 saniye.")
        if type(self.prune_loss_above) not in (int, float) or not math.isfinite(
            self.prune_loss_above
        ):
            raise ProjectError("Pruning loss eşiği sonlu olmalı.")
        if self.prune_after_folds >= self.inner_folds:
            raise ProjectError(
                "Pruning tamamlanmış CV yerine geçmez; fold sayısından önce olmalı."
            )
        if (
            any(
                type(v) is not bool
                for v in (self.early_stopping, self.curves, self.calibration)
            )
            or self.calibration
        ):
            raise ProjectError(
                "Calibration search bu adapterde kapalı; yeni calibration bölmesi gerektirir."
            )
        FamilyOptions.from_dict(self.options)
        if not isinstance(self.constraints, dict) or set(self.constraints) - {
            "max_rmse",
            "min_accuracy",
        }:
            raise ProjectError("Secondary constraints yalnız max_rmse/min_accuracy.")
        for name, value in self.constraints.items():
            if (
                type(value) not in (int, float)
                or not math.isfinite(value)
                or value < 0
                or name == "min_accuracy"
                and value > 1
            ):
                raise ProjectError("Secondary constraint sınırı geçersiz.")

    def candidates(self, purpose, require_backend=True):
        self.validate(require_backend)
        metrics = (
            ("mae", "rmse") if purpose == "regression" else ("accuracy", "f1_macro")
        )
        if self.metric != "auto" and self.metric not in metrics:
            raise ProjectError(
                "Metric hedef türüyle uyumsuz; final test metric arama girdisi değildir."
            )
        if (
            purpose == "regression"
            and "min_accuracy" in self.constraints
            or purpose == "classification"
            and "max_rmse" in self.constraints
        ):
            raise ProjectError("Secondary constraint hedef türüyle uyumsuz.")
        if not isinstance(self.space, dict) or set(self.space) != {
            "methods",
            "parameters",
        }:
            raise ProjectError(
                "Arama uzayı methods/parameters declarative alanları ister."
            )
        methods = self.space["methods"]
        allowed = REGRESSION_FAMILIES if purpose == "regression" else FAMILY_METHODS
        if (
            not isinstance(methods, list)
            or not 1 <= len(methods) <= 4
            or len(set(methods)) != len(methods)
            or any(m not in allowed or m in OPTIONAL_FAMILIES for m in methods)
        ):
            raise ProjectError(
                "Arama 1–4 native family ister; optional family tuning doğrulanmadı."
            )
        parameters = self.space["parameters"]
        if not isinstance(parameters, list) or len(parameters) > 5:
            raise ProjectError(
                "En fazla beş discrete parameter; executable distribution yok."
            )
        seen = set()
        for p in parameters:
            if (
                not isinstance(p, dict)
                or set(p) - {"name", "values", "when"}
                or not {"name", "values"} <= set(p)
                or p["name"] not in TUNABLE
                or p["name"] in seen
            ):
                raise ProjectError("Arama parametresi bilinmiyor veya tekrarlandı.")
            seen.add(p["name"])
            when = p.get("when", {})
            if (
                not isinstance(when, dict)
                or set(when) - {"method", "purpose"}
                or any(not isinstance(v, list) or not v for v in when.values())
            ):
                raise ProjectError("Önkoşul yalnız method/purpose listeleri.")
            if (
                "method" in when
                and not set(when["method"]) <= set(methods)
                or "purpose" in when
                and not set(when["purpose"]) <= {"regression", "classification"}
            ):
                raise ProjectError("Önkoşul bilinmeyen method/purpose içeriyor.")
            values = p["values"]
            if (
                not isinstance(values, list)
                or not 1 <= len(values) <= 10
                or len({digest(v) for v in values}) != len(values)
                or any(type(v) not in (int, float, str) for v in values)
            ):
                raise ProjectError("Parametre değerleri 1–10 unique scalar olmalı.")
        pool = []
        for method in methods:
            active = [
                p
                for p in parameters
                if method in p.get("when", {}).get("method", methods)
                and purpose in p.get("when", {}).get("purpose", [purpose])
            ]
            if any(method not in TUNABLE[p["name"]] for p in active):
                raise ProjectError(
                    "Parametre bu modele uygulanmıyor; açık when önkoşulu gerekli."
                )
            if self.early_stopping and method != "gradient_boosting":
                raise ProjectError(
                    "External-validation early stopping yalnız gradient_boosting."
                )
            for p in active:
                if (
                    p["name"] == "C"
                    and purpose == "regression"
                    and method != "svm"
                    or p["name"] == "alpha"
                    and purpose == "classification"
                    and method in ("elasticnet", "lasso", "voting", "stacking")
                ):
                    raise ProjectError(
                        "Parametre bu hedef türünde etkisiz; when.purpose önkoşulu gerekli."
                    )
            for values in itertools.product(*(p["values"] for p in active)):
                options = dict(
                    FamilyOptions.from_dict(self.options).data(),
                    **dict(zip([p["name"] for p in active], values)),
                )
                FamilyOptions.from_dict(options)
                if self.early_stopping and options["trees"] % 10:
                    raise ProjectError("Early stopping tree bütçesi 10'un katı olmalı.")
                pool.append(dict(method=method, options=options))
                if len(pool) > 2000:
                    raise ProjectError(
                        "Discrete space 2000 kombinasyon sınırını aşıyor."
                    )
        if not pool:
            raise ProjectError("Arama uzayı boş.")
        return pool

    def selected_metric(self, purpose):
        return (
            ("mae" if purpose == "regression" else "f1_macro")
            if self.metric == "auto"
            else self.metric
        )
