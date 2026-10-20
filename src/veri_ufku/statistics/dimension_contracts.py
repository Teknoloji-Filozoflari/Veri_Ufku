"""Explicit representation purpose and fold-local numeric selection contracts."""

import math

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.storage.project_model import ProjectError

DIMENSION_LABELS = {
    "dimension_pca": "46 · PCA · merkezlenmiş doğrusal boyut",
    "dimension_incremental_pca": "46 · Incremental PCA · batch fit",
    "dimension_svd": "46 · Truncated SVD · sparse / merkezlemesiz",
    "dimension_nmf": "46 · NMF · non-negative parçalar",
    "dimension_ica": "46 · ICA · bağımsız bileşen varsayımı",
    "dimension_tsne": "46 · t-SNE · yalnız görsel keşif",
    "dimension_umap": "46 · UMAP · optional görsel keşif",
    "dimension_variance": "46 · Variance filter · ham varyans eşiği",
    "dimension_model": "46 · Model-based selection · top-k coefficient",
    "dimension_univariate": "46 · Univariate selection · F score",
    "dimension_rfe": "46 · RFE · sabit k",
    "dimension_sequential": "46 · Sequential forward selection · inner CV",
}
DIMENSION_METHODS = tuple(DIMENSION_LABELS)
VISUAL = ("dimension_tsne", "dimension_umap")
SELECTORS = DIMENSION_METHODS[7:]
SUPERVISED = SELECTORS[1:]
REDUCERS = DIMENSION_METHODS[:5]
PLAN_FIELDS = {
    "purpose",
    "fit_scope",
    "target_kind",
    "scaling",
    "missing",
    "storage",
    "components",
    "variance_threshold",
    "folds",
    "inner_folds",
    "batch_size",
    "perplexity",
    "neighbors",
    "profile",
}


def validate(spec, columns, run=False):
    p = spec.dimension_plan
    if (
        spec.method not in DIMENSION_METHODS
        or not isinstance(p, dict)
        or set(p) != PLAN_FIELDS
    ):
        raise ProjectError("Boyut indirgeme / selection tam declarative plan gerekli.")
    if p["purpose"] not in ("model_input", "compression", "visual") or p[
        "fit_scope"
    ] != ("development" if p["purpose"] == "model_input" else "full"):
        raise ProjectError(
            "Model girdisi yalnız development; kompresyon/görsel keşif açık full-fit kapsamı ister."
        )
    if (
        spec.method in VISUAL
        and p["purpose"] != "visual"
        or spec.method in SUPERVISED
        and p["purpose"] != "model_input"
    ):
        raise ProjectError(
            "t-SNE/UMAP yalnız görsel; hedef kullanan selection yalnız nested CV model girdisi."
        )
    if (
        not isinstance(spec.features, list)
        or not 2 <= len(spec.features) <= 20
        or any(not isinstance(v, str) for v in spec.features)
    ):
        raise ProjectError(
            "2–20 sayısal ölçüm ColumnId seçin; encoded/text/tensor şemaları bu yolda yok."
        )
    fields = spec.features + ([spec.y] if spec.y else [])
    ids = {c["id"] for c in columns}
    if (
        len(set(fields)) != len(fields)
        or not set(fields) <= ids
        or spec.x != spec.features[0]
    ):
        raise ProjectError("Feature sırası/ColumnId/target ayrı mevcut alanlar olmalı.")
    if bool(spec.y) != (p["purpose"] == "model_input") or p["target_kind"] not in (
        "regression",
        "binary",
    ):
        raise ProjectError(
            "Model girdisi açık regression/binary target ister; keşif target kullanmaz ve test etiketleri gösterilmez."
        )
    if (
        p["scaling"] not in ("none", "standard", "standard_no_center")
        or p["missing"] not in ("reject", "mean")
        or p["storage"] not in ("dense", "csr")
    ):
        raise ProjectError(
            "Scaling/missing/storage seçimi geçersiz; imputasyon yalnız fit satırlarında."
        )
    if p["storage"] == "csr" and (
        spec.method not in ("dimension_svd", "dimension_nmf")
        or p["scaling"] == "standard"
    ):
        raise ProjectError(
            "CSR yalnız SVD/NMF ve merkezlemesiz scaling; sessiz densification yok."
        )
    if spec.method == "dimension_nmf" and p["scaling"] == "standard":
        raise ProjectError(
            "NMF non-negative ister; centering negatif yaratabilir, otomatik shift/clip yok."
        )
    if (
        type(p["components"]) is not int
        or not (1 if spec.method in SELECTORS else 2)
        <= p["components"]
        <= len(spec.features)
        or spec.method in VISUAL
        and p["components"] != 2
    ):
        raise ProjectError(
            "Bileşen/selected-k feature sayısına uygun; görsel embedding tam2boyut."
        )
    if spec.method in SELECTORS and (
        len(spec.features) > 10 or p["storage"] != "dense"
    ):
        raise ProjectError(
            "Selection bu yolda<=10dense sayısal feature; explicit bounded search."
        )
    if (
        type(p["variance_threshold"]) not in (float, int)
        or not math.isfinite(p["variance_threshold"])
        or not 0 <= p["variance_threshold"] <= 1e6
    ):
        raise ProjectError(
            "Variance threshold ham feature birimlerinin karesi, sonlu0–1e6 olmalı."
        )
    for key, lo, hi in (
        ("folds", 2, 5),
        ("inner_folds", 2, 3),
        ("batch_size", 10, 1000),
    ):
        if type(p[key]) is not int or not lo <= p[key] <= hi:
            raise ProjectError("Fold/batch sınırı geçersiz.")
    if (
        type(spec.seed) is not int
        or not 0 <= spec.seed < 2**32
        or type(spec.max_iterations) is not int
        or not 300 <= spec.max_iterations <= 1000
    ):
        raise ProjectError("Seed0–2³²−1/iterations300–1000 gerekli.")
    if (
        type(p["perplexity"]) not in (float, int)
        or not math.isfinite(p["perplexity"])
        or not 2 <= p["perplexity"] <= 50
        or type(p["neighbors"]) is not int
        or not 3 <= p["neighbors"] <= 50
    ):
        raise ProjectError("Perplexity2–50/neighbors3–50 gerekli.")
    profile = p["profile"]
    if (
        not isinstance(profile, list)
        or len(profile) != len(spec.features)
        or any(
            type(v) not in (float, int) or not math.isfinite(v) or abs(v) > 1e12
            for v in profile
        )
    ):
        raise ProjectError("Yeni veri profili feature sırasıyla sonlu değerler ister.")
    for key in ("question", "observation_unit"):
        v = getattr(spec, key)
        if not isinstance(v, str) or not v.strip() or len(v) > 1000:
            raise ProjectError("Soru ve analiz birimi gerekli.")
    if (
        spec.scope != "full"
        or ViewSpec.from_dict(spec.view).filters
        or spec.precision != "reject"
        or spec.missing_policy != "reject"
    ):
        raise ProjectError(
            "Tam immutable sürüm ve precision-reject; eksiklik politikası ayrı plan alanında açık."
        )
    if spec.weight_type != "none" or any(
        (
            spec.group,
            spec.key,
            spec.weight,
            spec.strata,
            spec.psu,
            spec.offset,
            spec.cluster,
            spec.exposure,
            spec.interactions,
            spec.random_slopes,
            spec.within,
            spec.time_column,
            spec.survival_plan,
            spec.causal_plan,
            spec.bayes_plan,
            spec.experiment_plan,
        )
    ):
        raise ProjectError(
            "Bu ilk numeric independent yolda group/time/weights/başka model planı yok; uygun validation backend olmadan random fallback yapılmaz."
        )
    if (
        any(
            type(getattr(spec, k)) is not bool
            for k in ("independent", "measurement_confirmed", "assumptions_confirmed")
        )
        or not spec.independent
        or not spec.measurement_confirmed
        or run
        and not spec.assumptions_confirmed
    ):
        raise ProjectError(
            "Bağımsız birim, baseline ölçümler ve önkontrol onayı gerekli."
        )
