"""Bounded matrix recipes; identifiers are never executable formula text."""

import math

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.storage.project_model import ProjectError

MODEL_LABELS = {
    "ols": "40.1 · OLS",
    "wls": "40.1 · WLS (ters varyans)",
    "glm_binomial": "40.2 · GLM binomial / logit",
    "glm_poisson": "40.2 · GLM Poisson / log",
    "glm_negative_binomial": "40.2 · GLM NB2 / log (sabit alpha)",
    "quantile": "40.3 · Quantile regression",
    "mixed": "40.4 · Mixed-effects (Gaussian)",
    "repeated": "40.5 · Repeated-measures ANOVA (dengeli)",
}
MODEL_METHODS = tuple(MODEL_LABELS)
COVARIANCE = {
    "ols": ("nonrobust", "HC3", "cluster"),
    "wls": ("nonrobust", "HC3", "cluster"),
    "glm_binomial": ("nonrobust", "HC0", "cluster"),
    "glm_poisson": ("nonrobust", "HC0", "cluster"),
    "glm_negative_binomial": ("nonrobust", "HC0", "cluster"),
    "quantile": ("robust", "iid"),
    "mixed": ("nonrobust",),
    "repeated": ("nonrobust",),
}


def validate(spec, columns, run=False):
    def reject(message):
        raise ProjectError(message)

    if (
        spec.method not in MODEL_METHODS
        or spec.covariance not in COVARIANCE[spec.method]
    ):
        reject("Bu model / SE kombinasyonu desteklenmiyor.")
    ids = {c["id"] for c in columns}
    if (
        not isinstance(spec.features, list)
        or not 0 <= len(spec.features) <= 12
        or len(set(spec.features)) != len(spec.features)
        or not set(spec.features) <= ids
    ):
        reject("En fazla12 farklı predictor ColumnId seçin.")
    if spec.x not in ids or spec.x in spec.features:
        reject("Response ve predictors farklı mevcut sütunlar olmalı.")
    if (
        not isinstance(spec.references, dict)
        or not set(spec.references) <= set(spec.features)
        or any(not isinstance(v, str) or len(v) > 256 for v in spec.references.values())
    ):
        reject("Kategorik predictor için açık referans kategori seçin.")
    if (
        not isinstance(spec.interactions, list)
        or len(spec.interactions) > 12
        or any(
            not isinstance(p, list)
            or len(p) != 2
            or p[0] == p[1]
            or not set(p) <= set(spec.features)
            for p in spec.interactions
        )
    ):
        reject("Interaction yalnız iki seçili predictor kimliği ile oluşturulur.")
    if len({tuple(sorted(p)) for p in spec.interactions}) != len(spec.interactions):
        reject("Tekrarlanan interaction seçilemez.")
    if (
        not isinstance(spec.random_slopes, list)
        or len(spec.random_slopes) > 3
        or len(set(spec.random_slopes)) != len(spec.random_slopes)
        or not set(spec.random_slopes) <= set(spec.features)
        or set(spec.random_slopes) & set(spec.references)
    ):
        reject("Random slope en fazla3 seçili sayısal predictor olabilir.")
    if (
        not isinstance(spec.within, list)
        or len(spec.within) > 2
        or len(set(spec.within)) != len(spec.within)
        or not set(spec.within) <= ids
    ):
        reject("Within faktörleri en fazla2 farklı sütun olabilir.")
    for name in ("weight", "offset", "exposure", "cluster", "group"):
        value = getattr(spec, name)
        if (
            not isinstance(value, str)
            or value
            and (value not in ids or value == spec.x or value in spec.features)
        ):
            reject("Ağırlık/offset/exposure/group/cluster rolü ayrı ColumnId olmalı.")
    if bool(spec.weight) != (spec.method == "wls") or spec.weight_type != "none":
        reject(
            "Yalnız WLS ayrı pozitif ters-varyans ağırlığı destekler; frekans/survey ağırlığı değildir."
        )
    count = spec.method in ("glm_poisson", "glm_negative_binomial")
    if (spec.offset or spec.exposure) and not count or spec.offset and spec.exposure:
        reject(
            "Offset veya exposure yalnız log-count GLM için; ikisini birlikte seçmeyin."
        )
    if bool(spec.cluster) != (spec.covariance == "cluster"):
        reject(
            "Cluster SE için açık küme sütunu gerekli; diğer SE için cluster seçilemez."
        )
    if (
        bool(spec.group) != (spec.method in ("mixed", "repeated"))
        or spec.random_slopes
        and spec.method != "mixed"
    ):
        reject("Group/random etkiler yalnız mixed/repeated yoluna uygundur.")
    if spec.method == "repeated":
        if not spec.within or spec.features or spec.interactions or spec.references:
            reject(
                "Repeated: kişi + within faktörleri seçin; between/predictor/interaction yolu desteklenmiyor."
            )
        if spec.x in spec.within or spec.group in spec.within:
            reject("Response, kişi ve within faktörleri farklı olmalı.")
    elif spec.within:
        reject("Within yalnız repeated-measures yolundadır.")
    for name, low, high in (
        ("confidence", 0.8, 0.99),
        ("quantile", 0.05, 0.95),
        ("nb_alpha", 0.000001, 100),
    ):
        value = getattr(spec, name)
        if (
            type(value) not in (float, int)
            or not math.isfinite(value)
            or not low <= value <= high
        ):
            reject("CI / quantile / NB alpha aralığı geçersiz.")
    if (
        type(spec.max_iterations) is not int
        or not 1 <= spec.max_iterations <= 2000
        or type(spec.reml) is not bool
    ):
        reject("Iteration / REML seçimi geçersiz.")
    if (
        spec.missing_policy not in ("reject", "complete")
        or spec.scope not in ("view", "full")
        or spec.posthoc != "none"
        or spec.alternative != "two-sided"
    ):
        reject(
            "Model kapsamı/eksik veri veya yönlü/posthoc kombinasyonu desteklenmiyor."
        )
    for name in ("question", "hypothesis", "unit", "observation_unit"):
        v = getattr(spec, name)
        if not isinstance(v, str) or not v.strip() or len(v) > 1000:
            reject("Soru, hipotez, birim ve gözlem birimini açıkça yazın.")
    if (
        any(
            type(getattr(spec, n)) is not bool
            for n in ("measurement_confirmed", "independent", "assumptions_confirmed")
        )
        or not spec.measurement_confirmed
        or not spec.independent
        or run
        and not spec.assumptions_confirmed
    ):
        reject(
            "Ölçüm ve bağımsız gözlem/küme birimini; çalıştırmadan önce önkontrolü onaylayın."
        )
    ViewSpec.from_dict(spec.view).validate(columns)
