"""Durable finding notebook stored inside the existing ProjectStore transaction.

A finding carries the schema's five fields — question, method, result,
interpretation, decision — and stays bound to a dataset version, a scope and the
parameters that produced it. Nothing is written by hand: the result summary is
computed from the recorded run of the stage that created the finding.
"""

import copy
from datetime import UTC, datetime

from veri_ufku.storage.project_model import ProjectError, entity_id, uid

STAGES = (
    "veri",
    "incele",
    "gorsellestir",
    "hazirla",
    "istatistik",
    "model",
    "raporla",
)
STAGE_LABELS = {
    "veri": "Veri",
    "incele": "İncele",
    "gorsellestir": "Görselleştir",
    "hazirla": "Hazırla",
    "istatistik": "İstatistik",
    "model": "Model",
    "raporla": "Raporla",
}
SCOPES = ("full", "filtered", "sample")
MAX_FINDINGS = 500
MAX_TEXT = 2000
MAX_SHORT = 500
NOT_RECORDED = "Bağlı kayıt yok; sonuç uydurulmaz."


def _text(value, maximum, required=False, label="Metin"):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ProjectError(f"{label} metin olmalı.")
    value = value.strip()
    if required and not value:
        raise ProjectError(f"{label} boş olamaz.")
    if len(value) > maximum:
        raise ProjectError(f"{label} {maximum} karakter sınırını aşıyor.")
    return value


def _integer(value, label):
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ProjectError(f"{label} geçersiz.")
    return value


def current_version(state):
    """The dataset version the workspace currently shows, if any."""
    from veri_ufku.operations.contracts import active_datasets

    active = active_datasets(state)
    if not active:
        return None
    return active[-1]["version_id"]


def heads(state):
    """dataset_id → current version_id map used by the staleness rule."""
    from veri_ufku.operations.contracts import heads as workflow_heads

    return workflow_heads(state)


def _record_summary(state, stage, version=None):
    """Computed summary of the stage's latest recorded run.

    The text is produced from stored numbers. When the stage has no recorded
    run the status is ``not_recorded`` and no number is invented.
    """
    results = state.get("results") or []
    records = list(reversed(results))
    if version:
        matching = [
            r for r in records if version in (r.get("dataset_version_ids") or [])
        ]
        if matching:
            records = matching
    if stage in ("veri", "incele"):
        for record in records:
            value = record.get("quality") or record.get("profile")
            if not value:
                continue
            columns = value.get("columns") or []
            rows = value.get("row_count") or value.get("rows") or 0
            missing = value.get("missing_total")
            text = f"{rows} satır · {len(columns)} sütun"
            if isinstance(missing, int):
                text += f" · eksik hücre {missing}"
            return dict(
                text=text,
                record_id=record["id"],
                capability_id=record.get("capability_id", ""),
                status="recorded",
            )
        return dict(
            text=NOT_RECORDED, record_id=None, capability_id="", status="not_recorded"
        )
    if stage == "gorsellestir":
        for record in records:
            value = record.get("chart")
            if not value:
                continue
            spec = value.get("spec") or {}
            used = value.get("used_n")
            total = value.get("population_n")
            scope = value.get("scope") or "full"
            text = (
                f"{spec.get('kind') or spec.get('title') or 'grafik'} · kapsam {scope}"
            )
            if isinstance(used, int) and isinstance(total, int):
                text += f" · n={used}/{total}"
            return dict(
                text=text,
                record_id=record["id"],
                capability_id=record.get("capability_id", ""),
                status="recorded",
            )
        return dict(
            text=NOT_RECORDED, record_id=None, capability_id="", status="not_recorded"
        )
    if stage == "hazirla":
        for record in records:
            value = record.get("operation") or record.get("preparation")
            if not value:
                continue
            changed = value.get("changed_rows")
            text = value.get("label") or value.get("kind") or "hazırlama işlemi"
            if isinstance(changed, int):
                text += f" · etkilenen satır {changed}"
            return dict(
                text=text,
                record_id=record["id"],
                capability_id=record.get("capability_id", ""),
                status="recorded",
            )
        for operation in reversed(state.get("operations") or []):
            spec = operation.get("spec") or {}
            text = spec.get("kind") or "hazırlama işlemi"
            return dict(
                text=text,
                record_id=operation.get("id"),
                capability_id=operation.get("capability_id", ""),
                status="recorded",
            )
        return dict(
            text=NOT_RECORDED, record_id=None, capability_id="", status="not_recorded"
        )
    if stage == "istatistik":
        for record in records:
            value = record.get("analysis")
            if not value:
                continue
            spec = value.get("spec") or {}
            primary = value.get("primary") or {}
            text = spec.get("method") or spec.get("path") or "analiz"
            sample = primary.get("n") or value.get("used_rows")
            if isinstance(sample, int):
                text += f" · n={sample}"
            p = primary.get("p_value")
            if isinstance(p, (int, float)):
                text += f" · p={p:.4g}"
            effect = primary.get("effect")
            if isinstance(effect, (int, float)):
                text += f" · etki={effect:.4g}"
            return dict(
                text=text,
                record_id=record["id"],
                capability_id=record.get("capability_id", ""),
                status="recorded",
            )
        return dict(
            text=NOT_RECORDED, record_id=None, capability_id="", status="not_recorded"
        )
    if stage == "model":
        for record in records:
            value = record.get("baseline") or record.get("model")
            if not value:
                continue
            metric = value.get("metric") or {}
            text = value.get("family") or value.get("model_id") or "model"
            score = metric.get("score") if isinstance(metric, dict) else None
            if isinstance(score, (int, float)):
                text += f" · {metric.get('name', 'skor')}={score:.4g}"
            return dict(
                text=text,
                record_id=record["id"],
                capability_id=record.get("capability_id", ""),
                status="recorded",
            )
        return dict(
            text=NOT_RECORDED, record_id=None, capability_id="", status="not_recorded"
        )
    # raporla
    for record in records:
        value = record.get("scientific_report")
        if not value:
            continue
        blocks = value.get("blocks") or []
        text = f"{len(blocks)} rapor bloğu"
        if value.get("stale"):
            text += " · güncel değil"
        return dict(
            text=text,
            record_id=record["id"],
            capability_id=record.get("capability_id", ""),
            status="recorded",
        )
    return dict(
        text=NOT_RECORDED, record_id=None, capability_id="", status="not_recorded"
    )


def create(
    state,
    stage,
    question,
    method,
    interpretation="",
    decision="",
    scope="full",
    parameters=None,
    version=None,
):
    """Build a validated finding bound to the current dataset version."""
    if stage not in STAGES:
        raise ProjectError("Bulgu aşaması geçersiz.")
    if scope not in SCOPES:
        raise ProjectError("Bulgu kapsamı geçersiz.")
    version = version or current_version(state)
    summary = _record_summary(state, stage, version)
    finding = dict(
        id="finding:" + uid(),
        stage=stage,
        question=_text(question, MAX_SHORT, required=True, label="Soru"),
        method=_text(method, MAX_SHORT, required=True, label="Yöntem"),
        result=summary["text"],
        result_status=summary["status"],
        result_source=summary["record_id"],
        result_capability=summary["capability_id"],
        interpretation=_text(interpretation, MAX_TEXT, label="Yorum"),
        decision=_text(decision, MAX_TEXT, label="Seçim gerekçesi"),
        dataset_version_ids=[version] if version else [],
        context=dict(scope=scope),
        parameters=copy.deepcopy(parameters) if parameters else {},
        created_at=datetime.now(UTC).isoformat(),
    )
    validate(finding, {d["version_id"] for d in state["datasets"]})
    return finding


def validate(finding, versions):
    """Closed field contract for a stored finding."""
    if not isinstance(finding, dict) or set(finding) != {
        "id",
        "stage",
        "question",
        "method",
        "result",
        "result_status",
        "result_source",
        "result_capability",
        "interpretation",
        "decision",
        "dataset_version_ids",
        "context",
        "parameters",
        "created_at",
    }:
        raise ProjectError("Bulgu alanları geçersiz.")
    entity_id(finding["id"], "finding")
    if finding["stage"] not in STAGES:
        raise ProjectError("Bulgu aşaması geçersiz.")
    for key, label in (
        ("question", "Soru"),
        ("method", "Yöntem"),
        ("result", "Sonuç"),
        ("interpretation", "Yorum"),
        ("decision", "Seçim gerekçesi"),
    ):
        _text(finding[key], MAX_TEXT, label=label)
    if finding["result_status"] not in ("recorded", "not_recorded"):
        raise ProjectError("Bulgu sonuç durumu geçersiz.")
    if finding["result_source"] is not None:
        entity_id(finding["result_source"], "result")
    if (
        not isinstance(finding["result_capability"], str)
        or len(finding["result_capability"]) > 120
    ):
        raise ProjectError("Bulgu yetenek bağı geçersiz.")
    if (
        not isinstance(finding["dataset_version_ids"], list)
        or len(finding["dataset_version_ids"]) > 8
        or len(set(finding["dataset_version_ids"]))
        != len(finding["dataset_version_ids"])
    ):
        raise ProjectError("Bulgu veri sürümü bağı geçersiz.")
    for version in finding["dataset_version_ids"]:
        entity_id(version, "dv")
        if version not in versions:
            raise ProjectError("Bulgu bağlı veri sürümü projede yok.")
    context = finding["context"]
    if (
        not isinstance(context, dict)
        or not {"scope"} <= set(context)
        or set(context) - {"scope", "used_n", "population_n", "filters"}
    ):
        raise ProjectError("Bulgu bağlam alanları geçersiz.")
    if context["scope"] not in SCOPES:
        raise ProjectError("Bulgu kapsamı geçersiz.")
    for key in ("used_n", "population_n"):
        _integer(context.get(key), "Bulgu bağlam sayacı")
    if not isinstance(context.get("filters", {}), dict):
        raise ProjectError("Bulgu filtre bağı geçersiz.")
    if not isinstance(finding["parameters"], dict) or len(finding["parameters"]) > 64:
        raise ProjectError("Bulgu parametre alanları geçersiz.")
    if (
        not isinstance(finding["created_at"], str)
        or len(finding["created_at"]) > 64
        or not finding["created_at"]
    ):
        raise ProjectError("Bulgu zaman damgası geçersiz.")
    return finding


def superseded(state, version):
    """True when a newer version was derived from the given version."""
    children = {}
    for dataset in state["datasets"]:
        for parent in dataset.get("parent_version_ids") or []:
            children.setdefault(parent, []).append(dataset["version_id"])
    seen, stack = set(), [version]
    while stack:
        current = stack.pop()
        for child in children.get(current, []):
            if child not in seen:
                seen.add(child)
                stack.append(child)
    return bool(seen)


def stale(state, finding):
    """A finding is out of date when its bound version is no longer current."""
    from veri_ufku.operations.contracts import active_datasets

    versions = finding.get("dataset_version_ids") or []
    if not versions:
        return True, "Bulgu veri sürümüne bağlı değil."
    known = {d["version_id"] for d in state["datasets"]}
    active = {d["version_id"] for d in active_datasets(state)}
    for version in versions:
        if version not in known:
            return True, "Bağlı veri sürümü projede yok."
        if superseded(state, version):
            return (
                True,
                "Bağlı veri sürümünden yeni bir sürüm türetildi; bulgu güncel değil.",
            )
        if version not in active:
            return True, "Bağlı veri sürümü güncel değil."
    return False, ""


def rows(state):
    """Findings with their computed freshness, newest first."""
    out = []
    for finding in state.get("findings") or []:
        is_stale, reason = stale(state, finding)
        out.append(
            dict(
                id=finding["id"],
                stage=finding["stage"],
                stage_label=STAGE_LABELS[finding["stage"]],
                question=finding["question"],
                method=finding["method"],
                result=finding["result"],
                result_status=finding["result_status"],
                interpretation=finding["interpretation"],
                decision=finding["decision"],
                dataset_version_ids=list(finding["dataset_version_ids"]),
                scope=finding["context"]["scope"],
                parameters=copy.deepcopy(finding["parameters"]),
                created_at=finding["created_at"],
                stale=is_stale,
                stale_reason=reason,
            )
        )
    return out


def append(state, finding):
    """Add a validated finding to a project state.

    The caller persists the state through the existing ProjectStore transaction;
    this module never writes a file of its own.
    """
    validate(finding, {d["version_id"] for d in state["datasets"]})
    findings = state.setdefault("findings", [])
    if len(findings) >= MAX_FINDINGS:
        raise ProjectError("Bulgu defteri en fazla 500 kayıt tutar.")
    findings.append(copy.deepcopy(finding))
    return finding


def remove(state, ident):
    """Remove a finding after an explicit user decision."""
    findings = state.get("findings") or []
    if not any(f["id"] == ident for f in findings):
        raise ProjectError("Bulgu kaydı bulunamadı.")
    state["findings"] = [f for f in findings if f["id"] != ident]
    return ident
