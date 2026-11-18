"""Atomik Mod 2 plan kaydı; ikinci proje deposu veya ayrı provenance günlüğü yok."""

import copy

from veri_ufku.modeling.plans import validate_record
from veri_ufku.storage.project_model import ProjectError, decode, uid


def publish(store, state, plan, checkpoint=lambda point: None):
    """Planı mevcut proje durumuna atomik olarak ekler; veri sürümü üretmez."""
    store._guard()
    previous, pending, commit = store.state, dict(store.pending), store.commit_id
    try:
        record = dict(
            id="result:" + uid(),
            dataset_version_ids=list(
                dict.fromkeys([plan["origin_version"], plan["dataset_version"]])
            ),
            seed=None,
            capability_id="model.prepare",
            mod2_plan=copy.deepcopy(plan),
        )
        versions = {d["version_id"]: d for d in state["datasets"]}
        validate_record(record, versions)
        store.state = copy.deepcopy(state)
        store.state["results"].append(record)
        store.save(checkpoint=checkpoint)
        return copy.deepcopy(store.state)
    except BaseException:
        if decode(store._read("ACTIVE", 4096))["commit_id"] != commit:
            store._load("ACTIVE")
            store.pending.clear()
        else:
            store.state, store.pending = previous, pending
        raise


def remove(store, state, result_id):
    """Mod 2 plan kaydını proje durumundan çıkarır; dönüşüm geçmişi korunur."""
    store._guard()
    previous, pending, commit = store.state, dict(store.pending), store.commit_id
    try:
        target = next((r for r in state["results"] if r["id"] == result_id), None)
        if not target or "mod2_plan" not in target:
            raise ProjectError("Mod 2 plan kaydı bulunamadı.")
        store.state = copy.deepcopy(state)
        store.state["results"] = [
            r for r in store.state["results"] if r["id"] != result_id
        ]
        store.save()
        return copy.deepcopy(store.state)
    except BaseException:
        if decode(store._read("ACTIVE", 4096))["commit_id"] != commit:
            store._load("ACTIVE")
            store.pending.clear()
        else:
            store.state, store.pending = previous, pending
        raise
