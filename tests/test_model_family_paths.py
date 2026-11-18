"""Her aday ailesi için en az bir çalışan yol ve kayıtlı yetenek (şema M-03/M-04/M-05)."""

from veri_ufku.domain.capabilities import CAPABILITIES, availability
from veri_ufku.modeling.candidates import suggest_candidates
from veri_ufku.modeling.classification import estimator as classification_estimator
from veri_ufku.modeling.family_contracts import (
    FAMILY_METHODS,
    OPTIONAL_FAMILIES,
    REGRESSION_FAMILIES,
)
from veri_ufku.modeling.regression import estimator as regression_estimator
from veri_ufku.modeling.unsupervised_contracts import CLUSTER_METHODS, METHODS


def test_regression_candidates_have_estimator_path():
    bundle = suggest_candidates("regression")
    ids = [c["id"] for c in bundle["candidates"]]
    assert ids == ["baseline", "linear", "ridge", "forest"]
    for candidate in bundle["candidates"]:
        model = regression_estimator(
            candidate["id"], {"alpha": 1.0, "trees": 5, "depth": 2}, "mean", 42
        )
        assert model is not None, candidate["id"]


def test_classification_candidates_have_estimator_path():
    bundle = suggest_candidates("classification")
    ids = [c["id"] for c in bundle["candidates"]]
    assert ids == ["baseline", "logistic", "forest"]
    for candidate in bundle["candidates"]:
        model = classification_estimator(
            candidate["id"], {"C": 1.0, "trees": 5, "depth": 2}, "prior", 42
        )
        assert model is not None, candidate["id"]


def test_schema_regression_and_classification_families_are_registered():
    # Şema M-03: Doğrusal · Ridge · Lasso · karar ağacı · Random Forest · SVR.
    # Şema M-04: Lojistik · Naive Bayes · K-NN · karar ağacı · RF · SVM.
    required = {
        "regression": ("lasso", "decision_tree", "svm", "hist_gradient", "knn"),
        "classification": ("gaussian_nb", "multinomial_nb", "knn", "svm"),
    }
    for purpose, families in required.items():
        for family in families:
            ident = f"model.family.{purpose}.{family.replace('_', '-')}"
            assert ident in CAPABILITIES, ident
            installed, reason = availability(CAPABILITIES[ident])
            if family in OPTIONAL_FAMILIES:
                assert reason, ident
            else:
                assert installed, (ident, reason)


def test_core_family_methods_are_available_and_optional_ones_are_marked():
    for purpose, families in (
        ("regression", REGRESSION_FAMILIES),
        (
            "classification",
            tuple(m for m in FAMILY_METHODS if m not in REGRESSION_FAMILIES),
        ),
    ):
        for family in families:
            ident = f"model.family.{purpose}.{family.replace('_', '-')}"
            assert ident in CAPABILITIES, ident
            installed, reason = availability(CAPABILITIES[ident])
            if family in OPTIONAL_FAMILIES:
                # Optional backend yoksa yol kapalı; gerekçe uydurulmaz.
                assert reason, ident
            else:
                assert installed, (ident, reason)


def test_clustering_and_anomaly_families_have_working_paths():
    # Şema M-05: K-Means · hiyerarşik · DBSCAN · Gaussian karışım · anomali tespiti.
    for method in ("kmeans", "dbscan", "agglomerative", "gmm"):
        assert method in CLUSTER_METHODS
    for method in ("isolation_forest", "iqr", "lof", "one_class_svm"):
        assert method in METHODS
    bundle = suggest_candidates("clustering")
    assert bundle["candidates"][0]["id"] == "clustering"
    bundle = suggest_candidates("anomaly")
    assert bundle["candidates"][0]["id"] == "anomaly"
