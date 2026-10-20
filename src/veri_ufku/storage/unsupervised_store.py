"""Verified RowId assignments, atomic result storage and explicit new-dataset marking."""

import copy
from pathlib import Path

import polars as pl

from veri_ufku.modeling.unsupervised_contracts import CLUSTER_METHODS, validate_summary
from veri_ufku.operations.contracts import active_datasets
from veri_ufku.storage.project_model import ProjectError, decode, uid
from veri_ufku.storage.project_store import file_hash


def check_members(value, members, source):
    cluster = value["spec"]["method"] in CLUSTER_METHODS
    expected = {
        "__vu_row_id": pl.String,
        **(
            {"cluster": pl.Int64}
            if cluster
            else {"anomaly_score": pl.Float64, "anomaly_candidate": pl.Boolean}
        ),
    }
    if (
        members.schema != expected
        or members.height != source.height
        or members["__vu_row_id"].n_unique() != members.height
        or members["__vu_row_id"].null_count()
        or members["__vu_row_id"].to_list() != source["__vu_row_id"].to_list()
    ):
        raise ProjectError("Analiz tüm gerçek RowId'leri aynı sırada korumalı.")
    if cluster:
        counts = members.group_by("cluster").len()
        actual = {label: n for label, n in counts.iter_rows()}
        expected_counts = {p["label"]: p["count"] for p in value["profiles"]}
        if (
            actual != expected_counts
            or sum(n for label, n in actual.items() if label == -1)
            != value["noise_count"]
        ):
            raise ProjectError("Küme üyelik sayımları/profilleri uyuşmuyor.")
    else:
        score, flag = members["anomaly_score"], members["anomaly_candidate"]
        scored = score.is_not_null()
        if (
            score.is_null().to_list() != flag.is_null().to_list()
            or not score.drop_nulls().is_finite().all()
            or (score.drop_nulls() > value["threshold"]).to_list()
            != flag.drop_nulls().to_list()
            or int(flag.sum()) != value["flagged_count"]
        ):
            raise ProjectError("Anomali skor/eşik/aday bağı uyuşmuyor.")
        counts = {0: int(scored.sum()) - int(flag.sum()), 1: int(flag.sum())}
        if not scored.all():
            if value["spec"]["anomaly_mode"] != "novelty":
                raise ProjectError("Outlier skorları eksik olamaz.")
            counts[2] = members.height - int(scored.sum())
            indices = value["method_state"]["training_indices"]
            if [i for i, v in enumerate(score.is_null()) if v] != indices:
                raise ProjectError("Novelty eğitim kayıtları skorlanamaz.")
        if {p["label"]: p["count"] for p in value["profiles"]} != counts:
            raise ProjectError("Anomali profil sayımları uyuşmuyor.")


def validate_record(record, versions):
    value = record["unsupervised"]
    dataset = versions.get(value["dataset_version"])
    if (
        not dataset
        or record["dataset_version_ids"] != [dataset["version_id"]]
        or record["seed"] != value["spec"]["seed"]
    ):
        raise ProjectError("Etiketsiz sonuç sürüm/seed bağı geçersiz.")
    validate_summary(value, dataset)
    if not isinstance(value.get("assignments_uri"), str) or not value[
        "assignments_uri"
    ].startswith("snapshots/"):
        raise ProjectError("Analiz üyelik artifact bağı eksik.")


def load(store, record):
    value = copy.deepcopy(record["unsupervised"])
    dataset = next(
        d
        for d in store.state["datasets"]
        if d["version_id"] == value["dataset_version"]
    )
    validate_summary(value, dataset)
    info = store.manifest["artifacts"][dataset["snapshot_uri"]]
    if value["provenance"]["snapshot_fingerprint"] != {
        k: info[k] for k in ("size", "sha256")
    }:
        raise ProjectError("Kayıtlı analiz snapshot bağı değişmiş.")
    source = pl.read_parquet(store.path(dataset["snapshot_uri"]))
    members = pl.read_parquet(store.path(value["assignments_uri"]))
    check_members(value, members, source)
    from veri_ufku.modeling.exploration import verify_source

    verify_source(value, members, source, dataset)
    return value, members, source, dataset


def publish(store, state, result, checkpoint=lambda point: None):
    store._guard()
    previous, pending, commit = store.state, dict(store.pending), store.commit_id
    try:
        dataset = next(
            (
                d
                for d in active_datasets(state)
                if d["version_id"] == result["dataset_version"]
            ),
            None,
        )
        if not dataset:
            raise ProjectError("Analiz eski veri sürümüne bağlı; yeniden çalıştırın.")
        value = {
            k: copy.deepcopy(v)
            for k, v in result.items()
            if k
            not in (
                "assignment_path",
                "assignment_fingerprint",
                "worker_pid",
                "model_package",
            )
        }
        from veri_ufku.storage.model_store import adopt

        if result.get("model_package"):
            adopt(store, value, result["model_package"])
        validate_summary(value, dataset)
        info = store.manifest["artifacts"][dataset["snapshot_uri"]]
        fp = {k: info[k] for k in ("size", "sha256")}
        if (
            value["provenance"]["snapshot_fingerprint"] != fp
            or file_hash(store.path(dataset["snapshot_uri"])) != fp
        ):
            raise ProjectError("Analiz snapshot hash'i değişmiş.")
        path = Path(result["assignment_path"])
        if path.is_symlink() or file_hash(path) != result["assignment_fingerprint"]:
            raise ProjectError("Analiz üyelik çıktısı değişmiş/symlink.")
        members = pl.read_parquet(path)
        check_members(
            value, members, pl.read_parquet(store.path(dataset["snapshot_uri"]))
        )
        from veri_ufku.modeling.exploration import verify_source

        verify_source(
            value,
            members,
            pl.read_parquet(store.path(dataset["snapshot_uri"])),
            dataset,
        )
        value["assignments_uri"] = store.stage_parquet(members, checkpoint=checkpoint)
        record = dict(
            id="result:" + uid(),
            dataset_version_ids=[dataset["version_id"]],
            seed=value["spec"]["seed"],
            capability_id="model." + value["spec"]["method"].replace("_", "-"),
            unsupervised=value,
        )
        store.state = copy.deepcopy(state)
        store.state["results"].append(record)
        store.save(checkpoint=checkpoint)
        return copy.deepcopy(store.state), record
    except BaseException:
        if decode(store._read("ACTIVE", 4096))["commit_id"] != commit:
            store._load("ACTIVE")
            store.pending.clear()
        else:
            store.state, store.pending = previous, pending
        raise


def transfer(store, state, record_id, checkpoint=lambda point: None):
    """A new dataset with all rows; original source/head/columns never overwritten."""
    store._guard()
    previous, pending, commit = store.state, dict(store.pending), store.commit_id
    try:
        record = next(
            r for r in state["results"] if r["id"] == record_id and "unsupervised" in r
        )
        value, members, source, dataset = load(store, record)
        if dataset["version_id"] not in {
            d["version_id"] for d in active_datasets(state)
        }:
            raise ProjectError(
                "Eski sonuç aktif veriye aktarılamaz; kaynak sürümünü seçin veya yeniden hesaplayın."
            )
        columns = copy.deepcopy(dataset["import_metadata"]["columns"])
        if len(columns) + len(members.columns) - 1 > 256:
            raise ProjectError("İşaretli dataset 256 sütun sınırını aşamaz.")
        semantics = copy.deepcopy(dataset.get("semantic_metadata", {}))
        for name in members.columns[1:]:
            base = {
                "cluster": "kesif_kumesi",
                "anomaly_score": "anomali_skoru",
                "anomaly_candidate": "anomali_adayi",
            }[name]
            used = {c["name"] for c in columns}
            target = base
            suffix = 1
            while target in used:
                target = base + "_" + str(suffix)
                suffix += 1
            col = dict(
                id="col:" + uid(),
                name=target,
                original_name=target,
                type=str(members[name].dtype),
            )
            columns.append(col)
            source = source.with_columns(members[name].alias(target))
            semantics[col["id"]] = dict(
                role="category"
                if name in ("cluster", "anomaly_candidate")
                else "measurement",
                unit="",
                description=value["warning"],
                ordinal_order=[],
                confirmed=True,
            )
        new = copy.deepcopy(dataset)
        for key in (
            "parent_version_ids",
            "input_version_ids",
            "operation_id",
            "output_schema",
            "forked_from_version_id",
            "derived_analysis",
        ):
            new.pop(key, None)
        new.update(
            dataset_id="dataset:" + uid(),
            version_id="dv:" + uid(),
            snapshot_uri=store.stage_parquet(source, checkpoint=checkpoint),
            semantic_metadata=semantics,
            derived_analysis=dict(
                result_id=record_id,
                source_version=dataset["version_id"],
                row_policy="preserve_all_RowId_SourceRecordId",
            ),
        )
        if "schema_contract" in new:
            new["schema_contract"]["dataset_version"] = new["version_id"]
            new["schema_contract"]["status"] = "requires_validation"
        new["import_metadata"]["columns"] = columns
        store.state = copy.deepcopy(state)
        store.state["datasets"].append(new)
        store.state["import_settings"][new["dataset_id"]] = copy.deepcopy(
            new["import_metadata"]["settings"]
        )
        store.save(checkpoint=checkpoint)
        return copy.deepcopy(store.state), new["version_id"]
    except BaseException:
        if decode(store._read("ACTIVE", 4096))["commit_id"] != commit:
            store._load("ACTIVE")
            store.pending.clear()
        else:
            store.state, store.pending = previous, pending
        raise


def validate_derived(dataset, versions, results):
    relation = dataset["derived_analysis"]
    source = versions.get(relation["source_version"])
    record = next(
        (
            r
            for r in results
            if r["id"] == relation["result_id"] and "unsupervised" in r
        ),
        None,
    )
    if (
        not source
        or not record
        or record["unsupervised"]["dataset_version"] != source["version_id"]
        or dataset["dataset_id"] == source["dataset_id"]
        or relation["row_policy"] != "preserve_all_RowId_SourceRecordId"
        or dataset["source_id"] != source["source_id"]
        or dataset["import_metadata"]["row_count"]
        != source["import_metadata"]["row_count"]
        or dataset["import_metadata"]["columns"][
            : len(source["import_metadata"]["columns"])
        ]
        != source["import_metadata"]["columns"]
    ):
        raise ProjectError("İşaretli dataset kaynak/sonuç/satır koruma bağı geçersiz.")
