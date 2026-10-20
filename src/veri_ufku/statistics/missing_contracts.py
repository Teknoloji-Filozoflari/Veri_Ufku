"""Closed Phase33 recipes and registry-declared weight semantics."""

import math

from veri_ufku.statistics.contracts import ADVANCED_METHODS
from veri_ufku.storage.project_model import ProjectError


def validate(spec, columns, run):
    for name in (
        "weight_type",
        "weight",
        "strata",
        "psu",
        "missing_assumption",
        "group",
        "y",
        "key",
    ):
        if not isinstance(getattr(spec, name), str):
            raise ProjectError("Ağırlık/tasarım/alan seçimleri metin olmalı.")
    if spec.method not in ADVANCED_METHODS:
        raise ProjectError("İleri eksik veri/örnekleme yöntemi desteklenmiyor.")
    for name in ("question", "hypothesis", "unit", "observation_unit"):
        text = getattr(spec, name)
        if not isinstance(text, str) or not text.strip() or len(text) > 1000:
            raise ProjectError("Soru, varsayım, ölçüm ve gözlem birimini belirtin.")
    if (
        any(
            type(getattr(spec, name)) is not bool
            for name in (
                "independent",
                "measurement_confirmed",
                "assumptions_confirmed",
            )
        )
        or not spec.independent
        or not spec.measurement_confirmed
        or run
        and not spec.assumptions_confirmed
    ):
        raise ProjectError("Ölçüm/tasarım ve varsayım onayları gerekli.")
    if (
        spec.scope not in ("view", "full")
        or spec.precision not in ("reject", "approximate")
        or type(spec.confidence) not in (int, float)
        or not 0.8 <= spec.confidence <= 0.99
    ):
        raise ProjectError("Kapsam/hassasiyet/güven düzeyi geçersiz.")
    if spec.posthoc != "none" or spec.alternative != "two-sided":
        raise ProjectError("Bu yolda post-hoc/yönlü test sunulmuyor.")
    for name, lo, hi in (
        ("seed", 0, 2**32 - 1),
        ("sample_size", 1, 10000),
        ("imputations", 2, 20),
        ("iterations", 1, 30),
    ):
        if type(getattr(spec, name)) is not int or not lo <= getattr(spec, name) <= hi:
            raise ProjectError("Seed/örneklem/MI sayısı/iterasyon sınırı geçersiz.")
    if spec.missing_assumption not in ("MCAR", "MAR", "MNAR"):
        raise ProjectError(
            "Eksiklik varsayımını açıkça seçin; mekanizma tespit edilmez."
        )
    if (
        not isinstance(spec.deltas, list)
        or not 1 <= len(spec.deltas) <= 7
        or any(
            type(d) not in (float, int) or not math.isfinite(d) or abs(d) > 1e6
            for d in spec.deltas
        )
        or 0 not in spec.deltas
        or len(set(spec.deltas)) != len(spec.deltas)
    ):
        raise ProjectError(
            "Duyarlılık deltaları sonlu, benzersiz ve0 dahil en fazla7 senaryo olmalı."
        )
    if (
        not isinstance(spec.features, list)
        or len(spec.features) > 19
        or any(not isinstance(i, str) for i in spec.features)
        or len(set(spec.features)) != len(spec.features)
    ):
        raise ProjectError("Ölçüm dahil en fazla20 farklı alan seçin.")
    from veri_ufku.domain.capabilities import get_capability

    supports = dict(
        get_capability("statistics." + spec.method.replace("_", "-")).supports
    )
    if (
        spec.weight_type
        not in ("none", "frequency", "analytic", "survey", "sample_weight")
        or spec.weight_type != "none"
        and not supports.get("weight_" + spec.weight_type, False)
    ):
        raise ProjectError("Seçilen yöntem bu ağırlık türünü desteklemiyor.")
    weighted = spec.method in (
        "weighted_mean",
        "weighted_ols",
        "weighted_fit",
        "survey_mean",
    )
    if weighted != (spec.weight_type != "none") or bool(spec.weight) != weighted:
        raise ProjectError("Ağırlıklı yöntemde tür ve ağırlık sütununu açıkça seçin.")
    survey = spec.method == "survey_mean"
    if (
        survey != bool(spec.strata and spec.psu)
        or not survey
        and (spec.strata or spec.psu)
    ):
        raise ProjectError(
            "Survey strata ve PSU ister; diğer yöntemler survey tasarımını kabul etmez."
        )
    selected = [spec.x]
    if spec.method in ("mi_ols", "weighted_ols", "weighted_fit"):
        if not spec.features:
            raise ProjectError(
                "Doğrusal model için en az bir ayrı sayısal özellik seçin."
            )
        selected += spec.features
    elif spec.method in ("mi_mean", "missing_patterns", "missing_indicators"):
        selected += spec.features
    elif spec.features:
        raise ProjectError("Bu yöntem ek özellikleri kullanmaz; seçimi temizleyin.")
    selected += [v for v in (spec.weight, spec.strata, spec.psu) if v]
    if spec.method in ("sample_stratified", "sample_cluster"):
        selected += [spec.group]
    elif spec.group:
        raise ProjectError("Bu yöntemde grup alanı desteklenmiyor.")
    if spec.y or spec.key:
        raise ProjectError("Bu ileri yolda y/key alanı kullanılmaz.")
    ids = {c["id"] for c in columns}
    if not set(selected) <= ids or len(selected) != len(set(selected)):
        raise ProjectError(
            "Ölçüm, özellik, ağırlık ve tasarım alanları farklı ve mevcut olmalı."
        )
    from veri_ufku.analytics.contracts import ViewSpec

    ViewSpec.from_dict(spec.view).validate(columns)
