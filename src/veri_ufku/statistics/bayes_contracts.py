"""Bounded declarative templates; never executable probabilistic programs."""

import math

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.storage.project_model import ProjectError

BAYES_LABELS = {
    "bayes_beta_binomial": "Beta-binomial · bağımsız 0/1 sonuç",
    "bayes_normal_mean": "Normal ortalama · bilinen gözlem SD",
    "bayes_linear": "Gaussian doğrusal regresyon",
    "bayes_hierarchical": "Gaussian grup random-intercept regresyon",
}
BAYES_METHODS = tuple(BAYES_LABELS)
FIELDS = {
    "alpha",
    "beta",
    "location",
    "scale",
    "noise_scale",
    "group_scale",
    "chains",
    "draws",
    "warmup",
    "target_accept",
    "sensitivity_factor",
}


def validate(spec, columns, run=False):
    def reject(text):
        raise ProjectError(text)

    p = spec.bayes_plan
    if spec.method not in BAYES_METHODS or not isinstance(p, dict) or set(p) != FIELDS:
        reject(
            "Bayes şablonu ve tam declarative prior/sampling tarifi gerekli; kod kabul edilmez."
        )
    for name in ("question", "unit", "observation_unit"):
        v = getattr(spec, name)
        if not isinstance(v, str) or not v.strip() or len(v) > 1000:
            reject("Soru, ölçüm birimi ve gözlem birimini yazın.")
    for name in ("alpha", "beta", "scale", "noise_scale", "group_scale"):
        if (
            type(p[name]) not in (float, int)
            or not math.isfinite(p[name])
            or not 1e-6 <= p[name] <= 1e6
        ):
            reject("Prior şekil/SD ölçekleri sonlu ve pozitif olmalı (1e-6–1e6).")
    if (
        type(p["location"]) not in (float, int)
        or not math.isfinite(p["location"])
        or abs(p["location"]) > 1e6
    ):
        reject("Prior merkezi sonlu ve sınırlı olmalı.")
    for name, lo, hi in (("chains", 2, 4), ("draws", 100, 2000), ("warmup", 100, 2000)):
        if type(p[name]) is not int or not lo <= p[name] <= hi:
            reject(
                "Sampling: chains2–4, draws/warmup100–2000; tek chain tanısı kabul edilmez."
            )
    for name, lo, hi in (("target_accept", 0.8, 0.99), ("sensitivity_factor", 1.1, 4)):
        if (
            type(p[name]) not in (float, int)
            or not math.isfinite(p[name])
            or not lo <= p[name] <= hi
        ):
            reject(
                "Target accept0.8–0.99 ve alternatif prior ölçek çarpanı1.1–4 olmalı."
            )
    if (
        type(spec.seed) is not int
        or not 0 <= spec.seed < 2**32
        or type(spec.confidence) not in (float, int)
        or not 0.8 <= spec.confidence <= 0.99
    ):
        reject("Seed ve credible interval düzeyi geçersiz.")
    ids = {c["id"] for c in columns}
    if (
        not isinstance(spec.features, list)
        or len(spec.features) > 5
        or any(not isinstance(c, str) for c in spec.features)
    ):
        reject("En fazla5 sayısal predictor seçin.")
    if (
        not isinstance(spec.bayes_feature_units, dict)
        or set(spec.bayes_feature_units) != set(spec.features)
        or any(
            not isinstance(v, str) or not v.strip() or len(v) > 100
            for v in spec.bayes_feature_units.values()
        )
    ):
        reject(
            "Her predictor için ölçüm birimi açık olmalı; dimensionless ise 1 yazın."
        )
    regression = spec.method in ("bayes_linear", "bayes_hierarchical")
    required = (
        [spec.x]
        + spec.features
        + ([spec.group] if spec.method == "bayes_hierarchical" else [])
    )
    if not set(required) <= ids or len(set(required)) != len(required):
        reject("Mevcut ve farklı outcome/predictor/grup sütunları seçin.")
    if (
        regression != bool(spec.features)
        or spec.group
        and spec.method != "bayes_hierarchical"
    ):
        reject(
            "Regresyon predictor ister; random-intercept şablonu dışında grup desteklenmez."
        )
    if (
        spec.weight_type != "none"
        or any(
            (
                spec.weight,
                spec.y,
                spec.key,
                spec.cluster,
                spec.strata,
                spec.psu,
                spec.offset,
                spec.exposure,
                spec.interactions,
                spec.random_slopes,
            )
        )
        or spec.precision != "reject"
        or spec.missing_policy != "reject"
    ):
        reject(
            "Weight/offset/etkileşim/random slope veya sessiz missing/precision dönüşümü desteklenmez."
        )
    if spec.scope not in ("full", "view"):
        reject("Kapsam full veya view olmalı.")
    ViewSpec.from_dict(spec.view).validate(columns)
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
            "Ölçüm/birim ve bağımsız birim (hierarchical: gruplar arası); önkontrol varsayımlarını onaylayın."
        )
