"""Explicit independent sampling units and exchangeability contracts."""

import math

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.storage.project_model import ProjectError

RESAMPLING_LABELS = {
    "bootstrap_percentile": "41.1 · Bootstrap percentile",
    "bootstrap_bca": "41.1 · Bootstrap BCa",
    "permutation": "41.2 · Exchangeable group-label permutation",
    "paired_sign_flip": "41.2 · Paired sign flip",
    "robust_summary": "41.3 · Trimmed / robust summary",
    "adjust_holm": "41.4 · Holm · FWER",
    "adjust_bonferroni": "41.4 · Bonferroni · FWER",
    "adjust_bh": "41.4 · BH · FDR",
    "sensitivity": "41.5 · Duyarlılık karşılaştırması",
}
RESAMPLING_METHODS = tuple(RESAMPLING_LABELS)
STATISTICS = ("mean", "median", "trimmed_mean")


def validate(spec, columns, run=False):
    def reject(message):
        raise ProjectError(message)

    ids = {c["id"] for c in columns}
    if spec.method not in RESAMPLING_METHODS or spec.x not in ids:
        reject("Mevcut ölçüm sütunu ve Faz41 yöntemi seçin.")
    for name in ("y", "group", "key", "cluster", "time_column"):
        v = getattr(spec, name)
        if not isinstance(v, str) or v and (v not in ids or v == spec.x):
            reject("Resampling rolleri mevcut ve ölçümden farklı ColumnId olmalı.")
    if spec.resampling_unit not in (
        "observation",
        "cluster",
        "time_block",
    ) or spec.dependence not in ("independent", "grouped", "temporal"):
        reject("Gözlem / grup / zaman blok birimi ve bağımlılık tasarımı seçin.")
    if (
        spec.resampling_unit
        != {
            "independent": "observation",
            "grouped": "cluster",
            "temporal": "time_block",
        }[spec.dependence]
    ):
        reject(
            "Bağımlı ölçümler tek satır örneklenemez: tasarım ve resampling birimi uyuşmuyor."
        )
    if bool(spec.cluster) != (spec.resampling_unit == "cluster") or bool(
        spec.time_column
    ) != (spec.resampling_unit == "time_block"):
        reject("Grup birimi cluster, zaman blok birimi açık sıralama sütunu ister.")
    if (
        spec.cluster
        and spec.cluster in (spec.group, spec.y, spec.key)
        or spec.time_column
        and spec.time_column in (spec.group, spec.y, spec.key)
    ):
        reject("Cluster/zaman sütunu test label/pair anahtarından farklı olmalı.")
    if (
        type(spec.seed) is not int
        or not 0 <= spec.seed < 2**32
        or type(spec.resamples) is not int
        or not 100 <= spec.resamples <= 10000
    ):
        reject("Seed0–2³²−1 ve tekrar100–10000 olmalı.")
    if type(spec.block_length) is not int or not 2 <= spec.block_length <= 500:
        reject("Zaman block uzunluğu2–500 olmalı.")
    if (
        spec.statistic not in STATISTICS
        or spec.alternative not in ("two-sided", "less", "greater")
        or spec.scope not in ("view", "full")
    ):
        reject("İstatistik/tail/kapsam seçimi geçersiz.")
    for name, lo, hi in (
        ("confidence", 0.8, 0.99),
        ("trim_fraction", 0.0, 0.4),
        ("null_value", -1e100, 1e100),
    ):
        v = getattr(spec, name)
        if type(v) not in (int, float) or not math.isfinite(v) or not lo <= v <= hi:
            reject("CI / trim oranı / null değeri geçersiz.")
    for name in (
        "measurement_confirmed",
        "independent",
        "assumptions_confirmed",
        "exchangeability_confirmed",
        "symmetry_confirmed",
    ):
        if type(getattr(spec, name)) is not bool:
            reject("Tasarım/varsayım onayı boolean olmalı.")
    if (
        not spec.measurement_confirmed
        or not spec.independent
        or run
        and not spec.assumptions_confirmed
    ):
        reject("Ölçüm ve bağımsız birimleri, çalıştırmadan önce önkontrolü onaylayın.")
    if spec.method in ("permutation", "paired_sign_flip"):
        if not spec.exchangeability_confirmed or spec.resampling_unit == "time_block":
            reject(
                "Exchangeability açık onay ister; zaman blok label/sign permütasyonu bu adapterda yok."
            )
    if spec.method == "permutation":
        if (
            not spec.group
            or spec.before == spec.after
            or not spec.before
            or not spec.after
            or spec.y
            or spec.key
            or spec.null_value != 0
        ):
            reject(
                "Permutation iki açık label ve H0 exchangeable distribution / fark0 ister; key/y/nonzero null desteklenmez."
            )
    elif spec.method == "paired_sign_flip":
        if (
            not spec.y
            or not spec.key
            or spec.group
            or spec.y == spec.key
            or not spec.symmetry_confirmed
        ):
            reject(
                "Paired wide before=x / after=y, benzersiz kişi key ve null etrafında simetrik fark / random sign tasarımı onayı gerekli."
            )
    elif spec.group or spec.y:
        reject(
            "Group label veya paired y yalnız ilgili permütasyon yönteminde seçilebilir."
        )
    if spec.method == "bootstrap_bca" and (
        spec.resampling_unit == "time_block" or spec.statistic != "mean"
    ):
        reject(
            "BCa bu adapterda yalnız iid/cluster mean ve delete-one independent-unit jackknife; median/trim/block desteklenmiyor."
        )
    if (
        spec.missing_policy not in ("reject", "complete")
        or spec.missing_assumption not in ("MCAR", "MAR", "MNAR")
        or spec.outlier_policy not in ("keep", "mad_exclude", "winsorize")
    ):
        reject("Eksik varsayımı ve açık outlier politikası seçin.")
    if (
        spec.method not in ("robust_summary", "sensitivity")
        and spec.outlier_policy != "keep"
    ):
        reject(
            "Çıkarımda outlier filtreleme otomatik uygulanmaz; duyarlılık yolu kullanın."
        )
    if spec.family_dependence not in ("arbitrary", "independent", "positive"):
        reject("Test ailesi bağımlılık varsayımı geçersiz.")
    if spec.method.startswith("adjust_"):
        if (
            spec.resampling_unit != "observation"
            or not spec.key
            or not spec.family_name.strip()
            or not isinstance(spec.family_ids, list)
            or not 1 <= len(spec.family_ids) <= 200
            or len(set(spec.family_ids)) != len(spec.family_ids)
            or any(
                not isinstance(v, str) or not v or len(v) > 256 for v in spec.family_ids
            )
        ):
            reject(
                "Düzeltme: p sütunu, benzersiz testID sütunu, açık aile adı ve1–200 seçili test kimliği gerekli."
            )
        if spec.method == "adjust_bh" and spec.family_dependence not in (
            "independent",
            "positive",
        ):
            reject(
                "BH bağımsız veya PRDS/pozitif bağımlılık varsayımı ister; keyfi bağımlılıkta Holm/Bonferroni seçin."
            )
    elif (
        spec.family_ids
        or spec.family_name
        or spec.key
        and spec.method != "paired_sign_flip"
    ):
        reject("Test ailesi alanları yalnız multiple-testing yolunda kullanılabilir.")
    if (
        not isinstance(spec.scenarios, list)
        or len(spec.scenarios) > 8
        or spec.scenarios
        and spec.method != "sensitivity"
    ):
        reject("En fazla8 senaryo yalnız duyarlılık yolundadır.")
    if spec.method == "sensitivity" and not spec.scenarios:
        reject("En az1 önceden belirlenmiş duyarlılık senaryosu ekleyin.")
    scenario_names = set()
    for scenario in spec.scenarios:
        if not isinstance(scenario, dict) or set(scenario) != {
            "name",
            "view",
            "statistic",
            "outlier_policy",
            "missing_policy",
            "missing_assumption",
            "missing_delta",
        }:
            reject("Duyarlılık senaryosu alanları geçersiz.")
        if (
            not isinstance(scenario["name"], str)
            or not scenario["name"].strip()
            or scenario["name"] == "baseline"
            or len(scenario["name"]) > 100
            or scenario["name"] in scenario_names
        ):
            reject("Senaryo adı benzersiz/açık olmalı.")
        scenario_names.add(scenario["name"])
        if (
            scenario["statistic"] not in STATISTICS
            or scenario["outlier_policy"] not in ("keep", "mad_exclude", "winsorize")
            or scenario["missing_policy"] not in ("reject", "complete", "delta")
            or scenario["missing_assumption"] not in ("MCAR", "MAR", "MNAR")
            or type(scenario["missing_delta"]) not in (int, float)
            or not math.isfinite(scenario["missing_delta"])
        ):
            reject("Senaryo yöntem/outlier/missing/delta seçimi geçersiz.")
        ViewSpec.from_dict(scenario["view"]).validate(columns)
    for name in ("question", "hypothesis", "unit", "observation_unit"):
        v = getattr(spec, name)
        if not isinstance(v, str) or not v.strip() or len(v) > 1000:
            reject("Soru, null hypothesis, ölçüm ve bağımsız birim açıklaması gerekli.")
    if (
        spec.features
        or spec.references
        or spec.interactions
        or spec.within
        or spec.random_slopes
        or any((spec.weight, spec.offset, spec.exposure, spec.strata, spec.psu))
        or spec.weight_type != "none"
        or spec.posthoc != "none"
    ):
        reject(
            "Faz41 resampling yolu model/ağırlık/offset/posthoc kombinasyonunu desteklemez."
        )
    ViewSpec.from_dict(spec.view).validate(columns)
