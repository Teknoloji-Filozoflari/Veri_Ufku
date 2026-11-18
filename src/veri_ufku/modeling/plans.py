"""Mod 2 plan tarifi: dönüşüm yalnız eğitim katında öğrenilir; veri sürümü üretmez."""

import copy
from datetime import UTC, datetime

from veri_ufku.storage.project_model import ProjectError, entity_id

PLAN_SCHEMA = "Mod2Plan/v1"
LEARN_SCOPE = "training_fold"
PLANNED = "planned"
STATUSES = (PLANNED, "applied", "cancelled")
FILL_METHODS = ("mean", "median", "mode")
STRATEGY = {"mean": "mean", "median": "median", "mode": "most_frequent"}
PLAN_FIELDS = {
    "schema",
    "dataset_version",
    "origin_version",
    "learn_scope",
    "status",
    "operations",
    "columns",
    "reason",
    "created_at",
}
MAX_REASON = 1000
MAX_OPERATIONS = 100
MAX_COLUMNS = 256


def strategy_of(method):
    """Doldurma yöntemi -> model hazırlığı imputasyon stratejisi."""
    return STRATEGY.get(method, method)


def create_plan(*, dataset_version, origin_version, operations, columns, reason):
    """Mod 2 plan yükü üretir; kayıt zarfı değildir, gizli değer taşımaz."""
    plan = dict(
        schema=PLAN_SCHEMA,
        dataset_version=dataset_version,
        origin_version=origin_version,
        learn_scope=LEARN_SCOPE,
        status=PLANNED,
        operations=copy.deepcopy(list(operations)),
        columns=copy.deepcopy(list(columns)),
        reason=str(reason),
        created_at=datetime.now(UTC).isoformat(),
    )
    validate_plan(plan)
    return plan


def validate_plan(plan, by_version=None):
    """Plan yükünün alan kümesi, sürüm bağı ve işlem biçimini denetler."""
    if not isinstance(plan, dict) or set(plan) != PLAN_FIELDS:
        raise ProjectError("Mod 2 planı alanları eksik veya bilinmiyor.")
    if plan["schema"] != PLAN_SCHEMA:
        raise ProjectError("Mod 2 planı şema sürümü desteklenmiyor.")
    if plan["learn_scope"] != LEARN_SCOPE:
        raise ProjectError("Mod 2 planı yalnız eğitim katında öğrenilebilir.")
    if plan["status"] not in STATUSES:
        raise ProjectError("Mod 2 planı durumu geçersiz.")
    for name in ("dataset_version", "origin_version"):
        entity_id(plan[name], "dv")
        if by_version is not None and plan[name] not in by_version:
            raise ProjectError("Mod 2 planı bilinmeyen veri sürümüne bağlı.")
    if not isinstance(plan["reason"], str) or len(plan["reason"]) > MAX_REASON:
        raise ProjectError("Mod 2 planı açıklaması en fazla1000 karakter olmalı.")
    if not isinstance(plan["created_at"], str) or not plan["created_at"]:
        raise ProjectError("Mod 2 planı oluşturulma zamanı geçersiz.")
    operations = plan["operations"]
    if not isinstance(operations, list) or not 1 <= len(operations) <= MAX_OPERATIONS:
        raise ProjectError("Mod 2 planı işlem sayısı geçersiz.")
    for operation in operations:
        validate_operation(operation)
    columns = plan["columns"]
    if not isinstance(columns, list) or not 1 <= len(columns) <= MAX_COLUMNS:
        raise ProjectError("Mod 2 planı kolon sayısı geçersiz.")
    for column in columns:
        if (
            not isinstance(column, dict)
            or set(column) != {"id", "name", "type"}
            or not isinstance(column["name"], str)
            or not isinstance(column["type"], str)
        ):
            raise ProjectError("Mod 2 planı kolon alanları geçersiz.")
        entity_id(column["id"], "col")


def validate_operation(operation):
    """Plan işlemi yalnız öğrenilen doldurma olabilir."""
    if (
        not isinstance(operation, dict)
        or set(operation) != {"kind", "method", "column_ids", "parameters"}
        or operation["kind"] != "fill"
        or operation["method"] not in FILL_METHODS
        or not isinstance(operation["parameters"], dict)
    ):
        raise ProjectError("Mod 2 planı işlemi yalnız öğrenilen doldurma olabilir.")
    columns = operation["column_ids"]
    if not isinstance(columns, list) or not columns:
        raise ProjectError("Mod 2 planı işlemi kolon seçimi geçersiz.")
    for ident in columns:
        entity_id(ident, "col")


def validate_record(record, by_version):
    """Proje sonucu içindeki Mod 2 plan kaydını doğrular."""
    plan = record.get("mod2_plan")
    if not isinstance(plan, dict):
        raise ProjectError("Mod 2 plan kaydı biçimi geçersiz.")
    validate_plan(plan, by_version)
    if record.get("capability_id") != "model.prepare":
        raise ProjectError("Mod 2 planı yetenek kaydı model.prepare olmalı.")
    if record.get("seed") is not None:
        raise ProjectError("Mod 2 planı seed taşımaz.")
    versions = list(record.get("dataset_version_ids") or [])
    if (
        plan["dataset_version"] not in versions
        or plan["origin_version"] not in versions
    ):
        raise ProjectError("Mod 2 planının veri sürümü bağı kayıtla uyuşmuyor.")
    if any(v not in by_version for v in versions):
        raise ProjectError("Mod 2 planı bilinmeyen veri sürümüne bağlı.")


def plan_steps(record):
    """Normalize edilmiş adım listesi; UI ve plan üretimi aynı görünümü kullanır."""
    plan = record.get("mod2_plan") if isinstance(record, dict) else record
    if not isinstance(plan, dict):
        raise ProjectError("Mod 2 planı bulunamadı.")
    steps = []
    for operation in plan.get("operations", []):
        validate_operation(operation)
        steps.append(
            dict(
                kind=operation["kind"],
                method=operation["method"],
                strategy=strategy_of(operation["method"]),
                column_ids=list(operation["column_ids"]),
                parameters=dict(operation["parameters"]),
            )
        )
    return steps


def plan_key(operation):
    """Aynı dönüşümü iki modda da kullanmayı engelleyen kararlı anahtar."""
    kind = str(operation.get("kind", ""))
    method = str(operation.get("method", ""))
    columns = operation.get("column_ids", [])
    return kind + "|" + method + "|" + ",".join(sorted(str(c) for c in columns))


def pending_plans(state, version_id):
    """Verilen sürüme uygulanabilir, hâlâ planlanmış Mod 2 kayıtları."""
    from veri_ufku.modeling.history import ancestors

    history = ancestors(state, version_id)
    plans = []
    for record in state.get("results", []):
        plan = record.get("mod2_plan")
        if not isinstance(plan, dict) or plan.get("status") != PLANNED:
            continue
        if plan.get("dataset_version") not in history:
            continue
        plans.append(
            dict(
                id=record["id"],
                status=plan["status"],
                learn_scope=plan["learn_scope"],
                dataset_version=plan["dataset_version"],
                origin_version=plan["origin_version"],
                columns=list(plan.get("columns", [])),
                operations=list(plan.get("operations", [])),
                plan=plan,
            )
        )
    return plans
