"""Declared fixed-horizon, independently randomized two-arm experiments."""

import math

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.storage.project_model import ProjectError

EXPERIMENT_LABELS = {
    "power_mean": "42.1 · Ortalama için güç / örneklem planı",
    "power_proportion": "42.1 · Oran için güç / örneklem planı",
    "random_assignment": "42.2 · Yerel taslak randomizasyon listesi",
    "experiment_mean": "42.3 · İki randomize grup · ortalama",
    "experiment_proportion": "42.3 · İki randomize grup · oran",
}
EXPERIMENT_METHODS = tuple(EXPERIMENT_LABELS)
PLAN_FIELDS = {
    "design",
    "randomization_unit",
    "analysis_unit",
    "primary_metric",
    "measurement_window",
    "eligibility",
    "stop_rule",
    "monitoring",
    "alpha",
    "power",
    "mde",
    "baseline_value",
    "sd",
    "allocation",
    "expected_attrition",
    "design_effect",
    "planned_total",
    "randomized_confirmed",
    "randomization_evidence",
    "horizon_complete",
    "analysis_population",
    "protocol_column",
    "baseline_columns",
    "guardrails",
}


def validate(spec, columns, run=False):
    def reject(s):
        raise ProjectError(s)

    ids = {c["id"] for c in columns}
    if spec.method not in EXPERIMENT_METHODS or not isinstance(
        spec.experiment_plan, dict
    ):
        reject("Faz42 yöntem ve ölçüm planı seçin.")
    p = spec.experiment_plan
    if set(p) != PLAN_FIELDS:
        reject("Ölçüm planı alanları eksik veya bilinmeyen alan içeriyor.")
    for name in ("question", "hypothesis", "unit", "observation_unit"):
        v = getattr(spec, name)
        if not isinstance(v, str) or not v.strip() or len(v) > 1000:
            reject("Soru, H0, ölçüm ve gözlem birimini yazın.")
    for name in (
        "randomization_unit",
        "analysis_unit",
        "primary_metric",
        "measurement_window",
        "eligibility",
        "stop_rule",
    ):
        if not isinstance(p[name], str) or not p[name].strip() or len(p[name]) > 1000:
            reject(
                "Randomizasyon/analiz birimi, birincil metrik, uygunluk, ölçüm penceresi ve durdurma planı gerekli."
            )
    if p["design"] != "two_group_independent" or p["monitoring"] != "fixed_horizon":
        reject(
            "Paired/cluster/factorial ve sequential ayrı, henüz kapalı alt işlerdir; sabit ufuk sequential değildir."
        )
    if p["randomization_unit"] != p["analysis_unit"] or p["design_effect"] != 1:
        reject(
            "Bu bağımsız iki-grup yolu aynı randomizasyon/analiz birimi ve design effect=1 ister; cluster tasarımı uygulanmadı."
        )
    for name, low, high in (
        ("alpha", 0.01, 0.2),
        ("power", 0.8, 0.99),
        ("allocation", 0.1, 0.9),
        ("expected_attrition", 0, 0.8),
        ("sd", 1e-12, 1e12),
        ("baseline_value", -1e12, 1e12),
        ("mde", -1e12, 1e12),
    ):
        v = p[name]
        if type(v) not in (int, float) or not math.isfinite(v) or not low <= v <= high:
            reject("Alpha/power/allocation/MDE/baseline/SD/kayıp varsayımı geçersiz.")
    if p["mde"] == 0 or (
        "proportion" in spec.method and not 0 < p["baseline_value"] < 1
    ):
        reject("MDE sıfır olamaz; planlanan baseline oran0–1 açık aralığında olmalı.")
    if "proportion" in spec.method and not 0 < p["baseline_value"] + p["mde"] < 1:
        reject("Baseline+mutlak MDE planlanan oran0–1 açık aralığında olmalı.")
    if type(p["planned_total"]) is not int or not 4 <= p["planned_total"] <= 100000:
        reject("Sabit ufuk planlanan toplam4–100000 bağımsız birim olmalı.")
    for name in ("randomized_confirmed", "horizon_complete"):
        if type(p[name]) is not bool:
            reject("Randomizasyon ve ufuk onayı boolean olmalı.")
    if (
        not isinstance(p["randomization_evidence"], str)
        or len(p["randomization_evidence"]) > 1000
    ):
        reject("Randomizasyon kanıtı/plan kimliği metin olmalı.")
    if spec.method.startswith("experiment_") and (
        not p["randomized_confirmed"] or not p["randomization_evidence"].strip()
    ):
        reject(
            "Gözlemsel veri randomize diye etiketlenmez; gerçek randomizasyon tasarımını ve plan/kanıt kimliğini açıkça onaylayın."
        )
    if spec.method.startswith("experiment_") and run and not p["horizon_complete"]:
        reject(
            "Sabit ufuk tamamlanmadan çıkarım yok; tekrar bakmak güvenli sequential değildir."
        )
    if (
        p["analysis_population"] not in ("ITT", "PP")
        or p["protocol_column"]
        and p["protocol_column"] not in ids
    ):
        reject("ITT/PP ve protokol sütunu geçersiz.")
    if p["analysis_population"] == "PP" and not p["protocol_column"]:
        reject(
            "PP açık0/1 protokole uygunluk sütunu ister; randomizasyonun ITT etkisi değildir."
        )
    if p["analysis_population"] == "ITT" and p["protocol_column"]:
        reject("ITT protokole göre satır seçmez.")
    if (
        not isinstance(p["baseline_columns"], list)
        or len(p["baseline_columns"]) > 5
        or len(set(p["baseline_columns"])) != len(p["baseline_columns"])
        or any(c not in ids for c in p["baseline_columns"])
    ):
        reject("En fazla5 farklı mevcut baseline sütunu seçin.")
    if not isinstance(p["guardrails"], list) or len(p["guardrails"]) > 5:
        reject("En fazla5 önceden belirlenen guardrail seçin.")
    for g in p["guardrails"]:
        if (
            not isinstance(g, dict)
            or set(g) != {"column_id", "name", "metric", "limit", "direction"}
            or g["column_id"] not in ids
            or g["metric"] not in ("mean", "proportion")
            or g["direction"] not in ("increase", "decrease")
            or not isinstance(g["name"], str)
            or not g["name"].strip()
            or len(g["name"]) > 200
            or type(g["limit"]) not in (int, float)
            or not math.isfinite(g["limit"])
            or g["limit"] < 0
        ):
            reject(
                "Guardrail: sütun/ad/mean-proportion/mutlak zarar sınırı/yön açık olmalı."
            )
    if p["baseline_columns"] and any(
        c in (spec.x, spec.key, spec.group, p["protocol_column"])
        for c in p["baseline_columns"]
    ):
        reject(
            "Baseline pretreatment ölçüm primary outcome/arm/key/protocol ile aynı olamaz."
        )
    if len({g["column_id"] for g in p["guardrails"]}) != len(p["guardrails"]) or any(
        g["column_id"] in (spec.x, spec.key, spec.group, p["protocol_column"])
        for g in p["guardrails"]
    ):
        reject(
            "Guardrail farklı ikincil ölçüm olmalı; duplicate veya primary/kimlik sütunu seçilmez."
        )
    if spec.method == "random_assignment" and (
        spec.x
        or spec.group
        or p["analysis_population"] != "ITT"
        or p["baseline_columns"]
        or p["guardrails"]
    ):
        reject(
            "Yerel assignment taslağı yalnız birim rosterı kullanır; outcome/PP seçimi uygulanmaz."
        )
    if spec.scope != "full" or ViewSpec.from_dict(spec.view).filters:
        reject(
            "Randomizasyon rosterı tam kapsam olmalı; sonuç/PP sonrası filtre SRM ve paydaları bozabilir."
        )
    if (
        spec.alternative != "two-sided"
        or abs(spec.confidence - (1 - p["alpha"])) > 1e-12
    ):
        reject("Bu yol iki yönlü H0 fark0 ve CI=1−alpha ister.")
    if spec.before == spec.after or not spec.before or not spec.after:
        reject("İki farklı kontrol/tedavi etiketi yazın.")
    if type(spec.seed) is not int or not 0 <= spec.seed < 2**32:
        reject("Seed0–2³²−1 olmalı.")
    if (
        any(
            type(getattr(spec, f)) is not bool
            for f in ("measurement_confirmed", "independent", "assumptions_confirmed")
        )
        or not spec.independent
        or not spec.measurement_confirmed
        or run
        and not spec.assumptions_confirmed
    ):
        reject(
            "Bağımsız birim ve ölçümü; çalıştırırken önkontrol varsayımlarını onaylayın."
        )
    if spec.method.startswith("power_"):
        if (
            spec.x
            or spec.key
            or spec.group
            or p["baseline_columns"]
            or p["guardrails"]
            or p["protocol_column"]
        ):
            reject(
                "Güç planı veriden observed power üretmez; yalnız önceden seçilen varsayımlar kullanılmalı."
            )
    else:
        if (
            spec.key not in ids
            or spec.method.startswith("experiment_")
            and (spec.x not in ids or spec.group not in ids)
        ):
            reject(
                "Benzersiz randomizasyon birimi; analiz için outcome ve özgün assigned arm sütunu seçin."
            )
        roles = [v for v in (spec.x, spec.key, spec.group, p["protocol_column"]) if v]
        if len(set(roles)) != len(roles):
            reject("Outcome/arm/birim/protokol farklı sütunlar olmalı.")
    if (
        spec.y
        or spec.dependence != "independent"
        or spec.resampling_unit != "observation"
        or spec.covariance != "nonrobust"
        or spec.null_value != 0
        or spec.cluster
        or spec.weight
        or spec.weight_type != "none"
        or spec.strata
        or spec.psu
        or spec.offset
        or spec.exposure
        or spec.features
        or spec.interactions
        or spec.scenarios
        or spec.posthoc != "none"
    ):
        reject(
            "Weight/cluster/model/resampling kombinasyonu bu deney yolunda desteklenmiyor."
        )
