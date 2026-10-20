"""Persist an unfitted plan in the existing atomic project metadata transaction."""

import copy

from veri_ufku.modeling.contracts import validate_saved
from veri_ufku.modeling.history import audit
from veri_ufku.operations.contracts import active_datasets
from veri_ufku.storage.project_model import ProjectError, decode, uid
from veri_ufku.storage.project_store import file_hash


def publish(store, state, result, checkpoint=lambda point: None):
    store._guard()
    previous, pending, commit = store.state, dict(store.pending), store.commit_id
    try:
        value = {
            k: v for k, v in result.items() if k not in ("worker_pid", "project_root")
        }
        versions = {d["version_id"]: d for d in state["datasets"]}
        record = dict(
            id="result:" + uid(),
            dataset_version_ids=list(
                dict.fromkeys([value["origin_version"], value["dataset_version"]])
            ),
            seed=None,
            capability_id="model.prepare",
            preparation=copy.deepcopy(value),
        )
        validate_saved(record, versions)
        if value["origin_version"] not in {
            d["version_id"] for d in active_datasets(state)
        }:
            raise ProjectError("Model hazırlığı eski aktif veriye ait; yeniden tara.")
        expected = audit(
            state,
            value["origin_version"],
            value["dataset_version"],
            value["spec"]["history_action"],
        )
        if value["history"] != expected:
            raise ProjectError(
                "Model hazırlığı geçmişi değişmiş; risk incelemesini yenileyin."
            )
        dataset = versions[value["dataset_version"]]
        fp = {
            k: store.manifest["artifacts"][dataset["snapshot_uri"]][k]
            for k in ("size", "sha256")
        }
        if (
            value["provenance"]["snapshot_fingerprint"] != fp
            or file_hash(store.path(dataset["snapshot_uri"])) != fp
        ):
            raise ProjectError("Model hazırlığı snapshot bağı değişmiş.")
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
