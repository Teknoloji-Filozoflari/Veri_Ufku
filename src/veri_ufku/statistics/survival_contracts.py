"""Backend-specific censoring and survival model contracts, safe declarative only."""

import math

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.storage.project_model import ProjectError

SURVIVAL_LABELS = {
    "survival_km": "45 · Kaplan–Meier / risk table",
    "survival_logrank": "45 · Log-rank · grup survival karşılaştırması",
    "survival_cox": "45 · Cox PH · hazard ratio",
    "survival_aft": "45 · Log-normal AFT · zaman oranı",
    "survival_cif": "45 · Competing risks · cumulative incidence",
}
SURVIVAL_METHODS = tuple(SURVIVAL_LABELS)
MODELS = ("survival_cox", "survival_aft")
CENSORING = {
    "survival_km": ("right", "left_truncated_right"),
    "survival_logrank": ("right", "left_truncated_right"),
    "survival_cox": ("right", "left_truncated_right"),
    "survival_aft": ("right",),
    "survival_cif": ("competing_right",),
}
TIME_UNITS = ("second", "minute", "hour", "day", "week", "year")
PLAN_FIELDS = {
    "censoring",
    "entry",
    "ties",
    "event_definition",
    "origin",
    "censoring_assumption",
    "unit_confirmation",
    "cause_labels",
    "risk_times",
    "prediction_times",
    "prediction_profile",
    "prediction_group",
}


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate(spec, columns, run=False):
    p = spec.survival_plan
    if (
        spec.method not in SURVIVAL_METHODS
        or not isinstance(p, dict)
        or set(p) != PLAN_FIELDS
    ):
        raise ProjectError("Sağkalım şablonu ve tam declarative plan gerekli.")
    if p["censoring"] not in CENSORING[spec.method]:
        raise ProjectError(
            "Bu backend/yöntem seçili censoring türünü desteklemiyor; interval/left censoring kapalı."
        )
    if not isinstance(p["entry"], str) or bool(p["entry"]) != (
        p["censoring"] == "left_truncated_right"
    ):
        raise ProjectError(
            "Entry yalnız desteklenen left truncation/right censoring yolunda seçilmeli."
        )
    if spec.unit not in TIME_UNITS or p["unit_confirmation"] is not True:
        raise ProjectError(
            "Duration/entry/prediction aynı açık zaman biriminde olmalı; dönüşüm otomatik değil."
        )
    for k in ("event_definition", "origin", "censoring_assumption"):
        if not isinstance(p[k], str) or not p[k].strip() or len(p[k]) > 2000:
            raise ProjectError(
                "Event tanımı, ortak zaman başlangıcı ve independent censoring gerekçesi gerekli."
            )
    if any(
        not isinstance(v, str) or not v.strip() or len(v) > 1000
        for v in (spec.question, spec.observation_unit)
    ):
        raise ProjectError("Soru ve bağımsız analiz birimi açıklaması gerekli.")
    if (
        not isinstance(spec.features, list)
        or len(spec.features) > 5
        or any(not isinstance(v, str) for v in spec.features)
    ):
        raise ProjectError(
            "En fazla5 baseline sayısal covariate seçin; time-dependent format ayrı."
        )
    if bool(spec.features) != (spec.method in MODELS):
        raise ProjectError(
            "Cox/AFT en az1 baseline predictor ister; KM/log-rank/CIF predictor kullanmaz."
        )
    if spec.method == "survival_aft" and spec.group:
        raise ProjectError(
            "Bu AFT şablonunda strata/group desteklenmiyor; sessiz yok sayılmaz."
        )
    if spec.method == "survival_logrank" and not spec.group:
        raise ProjectError("Log-rank grup sütunu gerekli.")
    fields = (
        [spec.x, spec.y, spec.key]
        + [v for v in (spec.group, p["entry"]) if v]
        + spec.features
    )
    ids = {c["id"] for c in columns}
    if not set(fields) <= ids or len(set(fields)) != len(fields):
        raise ProjectError(
            "Farklı mevcut duration/event/unit/entry/group/predictor ColumnId seçin."
        )
    if (
        p["ties"] not in ("breslow", "efron")
        or spec.method != "survival_cox"
        and p["ties"] != "breslow"
    ):
        raise ProjectError(
            "Efron yalnız Cox'ta; diğer şablonlarda default ties seçimi korunmalı."
        )
    labels = p["cause_labels"]
    if (
        not isinstance(labels, dict)
        or len(labels) > 5
        or any(
            k not in ("1", "2", "3", "4", "5")
            or not isinstance(v, str)
            or not v.strip()
            or len(v) > 200
            for k, v in labels.items()
        )
    ):
        raise ProjectError("Competing event1–5 kodlarının açık etiketleri gerekli.")
    if spec.method == "survival_cif":
        if (
            len(labels) < 2
            or set(labels) != {str(i) for i in range(1, len(labels) + 1)}
            or len(set(labels.values())) != len(labels)
        ):
            raise ProjectError(
                "En az2 farklı cause, ardışık1..K kod ve0censored gerekir."
            )
    elif labels:
        raise ProjectError(
            "İkili event şablonu competing cause kodlarını sessiz sansürleyemez."
        )
    for k in ("risk_times", "prediction_times"):
        v = p[k]
        if (
            not isinstance(v, list)
            or not 1 <= len(v) <= 12
            or any(not finite_number(t) or not 0 <= t <= 1e12 for t in v)
            or sorted(set(v)) != v
        ):
            raise ProjectError(
                "Risk/prediction zamanları1–12artan benzersiz sonlu pozitif/sıfır değer olmalı."
            )
    profile = p["prediction_profile"]
    if (
        not isinstance(profile, list)
        or len(profile) != len(spec.features)
        or any(not finite_number(v) or abs(v) > 1e12 for v in profile)
    ):
        raise ProjectError(
            "Model prediction profili seçili baseline predictor sırasına göre sonlu değerler ister."
        )
    if (
        not isinstance(p["prediction_group"], str)
        or len(p["prediction_group"]) > 200
        or spec.method != "survival_cox"
        and p["prediction_group"]
    ):
        raise ProjectError(
            "Prediction strata yalnız Cox group şablonunda açık seçilir."
        )
    if spec.method == "survival_cox" and bool(spec.group) != bool(
        p["prediction_group"]
    ):
        raise ProjectError(
            "Stratified Cox prediction için mevcut grup etiketi açık gerekli."
        )
    if (
        type(spec.confidence) not in (int, float)
        or not 0.8 <= spec.confidence <= 0.99
        or type(spec.max_iterations) is not int
        or not 20 <= spec.max_iterations <= 300
    ):
        raise ProjectError("Confidence0.8–0.99 ve iterations20–300 gerekli.")
    if (
        spec.scope != "full"
        or ViewSpec.from_dict(spec.view).filters
        or spec.precision != "reject"
        or spec.missing_policy != "reject"
    ):
        raise ProjectError(
            "Bu şablon tam sürüm/eksiksiz alan ister; sessiz drop/precision dönüşümü yok."
        )
    if spec.weight_type != "none" or any(
        (
            spec.weight,
            spec.strata,
            spec.psu,
            spec.offset,
            spec.exposure,
            spec.cluster,
            spec.interactions,
            spec.random_slopes,
            spec.within,
            spec.time_column,
            spec.causal_plan,
            spec.bayes_plan,
            spec.experiment_plan,
        )
    ):
        raise ProjectError(
            "Weight/cluster/time-dependent veya başka model planı bu şablonda desteklenmez."
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
        raise ProjectError("Bağımsız birim, zaman/ölçüm ve önkontrol onayı gerekli.")


def validate_time_dependent(frame, schema):
    """Validate SurvivalCountingProcess/v1 without pretending PHReg is an interval backend."""
    if (
        not isinstance(schema, dict)
        or set(schema) != {"schema", "id", "start", "stop", "event", "features", "unit"}
        or schema["schema"] != "SurvivalCountingProcess/v1"
        or schema["unit"] not in TIME_UNITS
    ):
        raise ProjectError(
            "Time-dependent covariate ayrı SurvivalCountingProcess/v1 şeması ister."
        )
    keys = [schema[k] for k in ("id", "start", "stop", "event")]
    features = schema["features"]
    if (
        not isinstance(features, list)
        or not 1 <= len(features) <= 5
        or any(not isinstance(k, str) for k in keys + features)
        or len(set(keys + features)) != len(keys + features)
        or not set(keys + features) <= set(frame.columns)
    ):
        raise ProjectError(
            "Counting-process farklı id/start/stop/event/covariate sütunları gerekli."
        )
    if not 1 <= frame.height <= 10000:
        raise ProjectError("Counting-process1–10000intervals sınırı gerekli.")
    grouped = {}
    for row in frame.select(keys + features).iter_rows(named=True):
        person = row[keys[0]]
        start, stop, event = [row[k] for k in keys[1:]]
        if (
            person is None
            or not str(person).strip()
            or not finite_number(start)
            or not finite_number(stop)
            or not 0 <= start < stop
            or event not in (0, 1)
            or any(not finite_number(row[k]) for k in features)
        ):
            raise ProjectError(
                "Counting-process eksik/negatif süre veya invalid event/predictor."
            )
        grouped.setdefault(str(person), []).append((start, stop, event))
    for records in grouped.values():
        records.sort()
        if (
            any(a[1] != b[0] or a[2] for a, b in zip(records, records[1:]))
            or sum(r[2] for r in records) > 1
        ):
            raise ProjectError(
                "Counting-process interval çakışması/gap veya event sonrası kayıt; her subject tek terminal event."
            )
    return dict(
        schema="SurvivalCountingProcess/v1",
        subjects=len(grouped),
        intervals=frame.height,
        execution_supported=False,
        reason="Mevcut PHReg statik baseline covariate modeli; counting-process fit/prediction backend doğrulanmadı.",
    )
