"""Phase48 data-only model-family choices and bounded adapter support contracts."""

import math
from dataclasses import asdict, dataclass
from importlib.util import find_spec

from veri_ufku.storage.project_model import ProjectError

FAMILY_METHODS = (
    "elasticnet",
    "lasso",
    "sgd",
    "decision_tree",
    "extra_trees",
    "gradient_boosting",
    "hist_gradient",
    "svm",
    "knn",
    "gaussian_nb",
    "multinomial_nb",
    "bagging",
    "voting",
    "stacking",
    "xgboost",
    "lightgbm",
    "catboost",
)
REGRESSION_FAMILIES = tuple(
    m for m in FAMILY_METHODS if m not in ("gaussian_nb", "multinomial_nb")
)
OPTIONAL_FAMILIES = ("xgboost", "lightgbm", "catboost")
SCALED_FAMILIES = ("elasticnet", "lasso", "sgd", "svm", "knn")


def available(method):
    if method in OPTIONAL_FAMILIES and find_spec(method) is None:
        return (
            False,
            f"Optional {method} backend ortamı yok; train/evaluate/predict doğrulanmadı.",
        )
    return True, ""


@dataclass(frozen=True)
class FamilyOptions:
    matrix: str = "dense"
    scaling: str = "auto"
    alpha: float = 0.1
    l1_ratio: float = 0.5
    C: float = 1.0
    trees: int = 25
    depth: int = 4
    learning_rate: float = 0.1
    neighbors: int = 5
    max_iter: int = 5000
    kernel: str = "rbf"
    gamma: str = "scale"
    class_balance: str = "none"
    weight_column: str = ""
    weight_kind: str = "sample_weight"
    inner_folds: int = 3
    objective: str = "supervised"
    device: str = "cpu"

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or set(value) - set(cls.__dataclass_fields__):
            raise ProjectError("Model aile parametreleri geçersiz.")
        try:
            result = cls(**value)
        except TypeError as error:
            raise ProjectError("Model aile parametreleri geçersiz.") from error
        result.validate()
        return result

    def data(self):
        return asdict(self)

    def validate(self):
        choices = dict(
            matrix=("dense", "sparse"),
            scaling=("auto", "none", "standard"),
            kernel=("linear", "rbf"),
            gamma=("scale", "auto"),
            class_balance=("none", "balanced"),
            weight_kind=("sample_weight",),
            objective=("supervised",),
            device=("cpu",),
        )
        for name, values in choices.items():
            if getattr(self, name) not in values:
                raise ProjectError(
                    f"{name} desteklenmiyor; ranking ayrı RankingSpec grup şemasıdır; GPU bu adapterde kapalı."
                )
        for name, low, high in (
            ("alpha", 0, 1000),
            ("l1_ratio", 0, 1),
            ("C", 0, 1000),
            ("learning_rate", 0, 1),
        ):
            v = getattr(self, name)
            if (
                type(v) not in (float, int)
                or not math.isfinite(v)
                or not low < v <= high
            ):
                raise ProjectError(f"{name} sınırı geçersiz.")
        for name, low, high in (
            ("trees", 10, 100),
            ("depth", 2, 12),
            ("neighbors", 1, 30),
            ("max_iter", 100, 10000),
            ("inner_folds", 2, 5),
        ):
            v = getattr(self, name)
            if type(v) is not int or not low <= v <= high:
                raise ProjectError(f"{name} sınırı {low}–{high}.")
        if not isinstance(self.weight_column, str):
            raise ProjectError("Weight ColumnId olmalı.")


def support(method, purpose):
    optional = method in OPTIONAL_FAMILIES
    native_cat = method in ("hist_gradient", *OPTIONAL_FAMILIES)
    return dict(
        method=method,
        purpose=purpose,
        dense=True,
        sparse=method
        not in (
            "hist_gradient",
            "gaussian_nb",
            "bagging",
            "voting",
            "stacking",
            *OPTIONAL_FAMILIES,
        ),
        scaling="training-only standard recommended"
        if method in SCALED_FAMILIES
        else "none recommended",
        categorical="native training vocabulary; unknown→missing"
        if native_cat
        else "training-only one-hot; ordinal only declared order",
        nan="native" if native_cat else "train-only declared imputation or reject",
        imbalance="training-only balanced sample weights"
        if method not in ("knn", "bagging", "voting", "stacking")
        else "no resampling/class weights; inspect per-class metrics",
        weights="fit sample_weight only; preprocessing and evaluation unweighted"
        if method not in ("knn", "bagging", "voting", "stacking")
        else "unsupported",
        multioutput="application schema single target; native multioutput not exposed",
        predict_proba=purpose == "classification" and method != "svm",
        gpu="unsupported CPU-only adapter",
        safe_persistence="unsupported optional backend"
        if optional
        else "closed reviewed skops package; no pickle/joblib",
        ranking="separate RankingSpec/v1, no ordinary class target",
        row_limit=1000
        if method in ("bagging", "voting", "stacking")
        else 2000
        if method in ("svm", "knn")
        else 5000,
        backend_available=available(method)[0],
        backend_reason=available(method)[1],
    )


def validate_family(method, purpose, options, preparation, protocol):
    if method not in FAMILY_METHODS or (
        purpose == "regression" and method not in REGRESSION_FAMILIES
    ):
        raise ProjectError("Bu model ailesi/hedef türü desteklenmiyor.")
    options.validate()
    ready, reason = available(method)
    if not ready:
        raise ProjectError(reason)
    table = support(method, purpose)
    if options.matrix == "sparse" and not table["sparse"]:
        raise ProjectError("Seçili model sparse desteklemiyor; açık dense seçin.")
    if (
        method in ("hist_gradient", *OPTIONAL_FAMILIES)
        and options.scaling == "standard"
    ):
        raise ProjectError(
            "Native categorical adapter standard scaling desteklemiyor; auto/none seçin."
        )
    if method == "multinomial_nb" and options.scaling == "standard":
        raise ProjectError(
            "MultinomialNB non-negative ölçü ister; centering desteklenmiyor."
        )
    if (
        options.weight_column
        and table["weights"] == "unsupported"
        or options.class_balance == "balanced"
        and (purpose != "classification" or table["weights"] == "unsupported")
    ):
        raise ProjectError("Model seçili weight/imbalance ayarını desteklemiyor.")
    if preparation.get("text"):
        raise ProjectError("Faz48 structured adapter; TF-IDF eski yolunda kalır.")
    if method == "stacking" and protocol.structure not in ("independent", "group"):
        raise ProjectError(
            "Stacking iç OOF şu anda independent/group destekler; time/group_time için random fallback yok."
        )
    if method in ("bagging", "voting", "stacking") and options.matrix != "dense":
        raise ProjectError("Bu ensemble wrapper structured dense yolunda doğrulandı.")


@dataclass(frozen=True)
class RankingSpec:
    """Explicit query-group relevance schema; cannot enter classifier routing."""

    features: tuple[str, ...]
    relevance: str
    query_group: str
    method: str = "xgboost"
    objective: str = "ndcg"

    def validate(self, columns):
        ids = {c["id"] for c in columns}
        if (
            self.method not in OPTIONAL_FAMILIES
            or self.objective != "ndcg"
            or not self.features
            or not set(self.features) <= ids
            or self.relevance not in ids
            or self.query_group not in ids
            or self.relevance == self.query_group
            or {self.relevance, self.query_group} & set(self.features)
        ):
            raise ProjectError(
                "Ranking query-group/relevance/features ayrı ve mevcut olmalı."
            )
