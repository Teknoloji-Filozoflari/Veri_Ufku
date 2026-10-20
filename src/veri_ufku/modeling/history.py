"""Traverse all immutable ancestors, including fork/join inputs; no history erased."""

from veri_ufku.storage.project_model import ProjectError


def ancestors(state, version):
    versions = {d["version_id"]: d for d in state["datasets"]}
    seen = set()
    todo = [version]
    while todo:
        ident = todo.pop()
        if ident in seen:
            continue
        if ident not in versions:
            raise ProjectError("Hazırlık geçmişinde bilinmeyen veri sürümü var.")
        seen.add(ident)
        d = versions[ident]
        todo.extend(d.get("parent_version_ids", []))
        todo.extend(d.get("input_version_ids", []))
        if d.get("forked_from_version_id"):
            todo.append(d["forked_from_version_id"])
    return seen


def audit(state, origin, source, action):
    origin_ids = ancestors(state, origin)
    if source not in origin_ids:
        raise ProjectError("Model kaynağı seçili verinin geçmişinden olmalı.")
    source_ids = ancestors(state, source)
    operations = {o["id"]: o for o in state["operations"]}
    findings = []
    for d in state["datasets"]:
        if d["version_id"] not in origin_ids or not d.get("operation_id"):
            continue
        op = operations[d["operation_id"]]
        s = op["spec"]
        kind = s["kind"]
        params = s["parameters"]
        if s.get("learned_scope", "none") == "dataset":
            reason = "İşlem tüm giriş verisinden öğrenildi; gelecekteki validation/test bilgisi karara katılmış olabilir."
            risk = "dataset_learned"
        elif kind in (
            "drop",
            "filter",
            "computed",
            "aggregate",
            "pivot",
            "ordered_fill",
            "map_categories",
        ):
            reason = "Seçim/özellik/özet kararı kayıtlı; hedef veya tüm veri incelendikten sonra alınmış olup olmadığı yalnız geçmişten kesin bilinemez."
            risk = "decision_review"
        else:
            continue
        can_move = (
            kind == "fill"
            and params.get("method") in ("mean", "median", "mode")
            or kind == "outlier"
            and params.get("action") == "mark"
        )
        removed = d["version_id"] not in source_ids
        findings.append(
            dict(
                operation_id=op["id"],
                dataset_version=d["version_id"],
                kind=kind,
                method=params.get("method", ""),
                policy_parameters=dict(params),
                column_ids=list(s["column_ids"]),
                input_version=s["input_version_id"],
                learned_scope=s.get("learned_scope", "none"),
                risk=risk,
                reason=reason,
                removed_from_source=removed,
                relocatable=bool(can_move),
                resolution="pending_fold_step"
                if removed and action == "relocate" and can_move
                else "bypassed_by_source"
                if removed
                else "unresolved",
            )
        )
    return dict(
        origin_version=origin,
        source_version=source,
        action=action,
        findings=findings,
        unresolved_source_operations=[
            f["operation_id"] for f in findings if not f["removed_from_source"]
        ],
        relocation_unavailable=[
            f["operation_id"]
            for f in findings
            if action == "relocate"
            and f["removed_from_source"]
            and not f["relocatable"]
        ],
        external_history="Proje dışındaki geçmiş ve kullanıcı seçimlerinin bütününü tespit edemeyiz; yeni plan tek başına eski riski gidermez.",
        leakage_certified=False,
    )


def clean_sources(state, origin):
    ids = ancestors(state, origin)
    return [
        d
        for d in state["datasets"]
        if d["version_id"] in ids
        and not audit(state, origin, d["version_id"], "raw")[
            "unresolved_source_operations"
        ]
    ]
