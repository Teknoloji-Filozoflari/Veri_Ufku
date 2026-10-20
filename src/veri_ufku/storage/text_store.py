"""Atomic local text summaries; raw previews are never persisted or logged."""

import copy

from veri_ufku.operations.contracts import active_datasets
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import file_hash
from veri_ufku.storage.validation_store import transaction


def validate_record(record, versions):
    from veri_ufku.analytics.text import validate_run

    value = record["text_analysis"]
    dataset = versions.get(value["dataset_version"])
    if (
        not dataset
        or record["dataset_version_ids"] != [dataset["version_id"]]
        or value["previews"]
    ):
        raise ProjectError("Metin kayıt bağı geçersiz; ham önizleme saklanamaz.")
    validate_run(value, dataset)


def load(store, record):
    validate_record(record, {d["version_id"]: d for d in store.state["datasets"]})
    value = record["text_analysis"]
    if value.get("advanced"):
        return load_nlp(store, value)
    dataset = next(
        d
        for d in store.state["datasets"]
        if d["version_id"] == value["dataset_version"]
    )
    info = store.manifest["artifacts"][dataset["snapshot_uri"]]
    expected = {k: info[k] for k in ("sha256", "size")}
    if (
        value["snapshot_fingerprint"] != expected
        or file_hash(store.path(dataset["snapshot_uri"])) != expected
    ):
        raise ProjectError("Kayıtlı metin sonucu snapshot fingerprint ile uyuşmuyor.")
    if value["similarities"]:
        import polars as pl

        members = set(
            pl.read_parquet(
                store.path(dataset["snapshot_uri"]), columns=["__vu_row_id"]
            )["__vu_row_id"].to_list()
        )
        if any(
            p["left"] not in members or p["right"] not in members
            for p in value["similarities"]
        ):
            raise ProjectError(
                "Benzerlik çiftleri gerçek kaynak RowId'lerine bağlı olmalı."
            )
    return copy.deepcopy(value)


def publish(store, state, result):
    from veri_ufku.storage.project_model import uid

    item = None

    def add(draft):
        nonlocal item
        dataset = next(
            (
                d
                for d in active_datasets(draft)
                if d["version_id"] == result["dataset_version"]
            ),
            None,
        )
        if (
            not dataset
            or file_hash(store.path(dataset["snapshot_uri"]))
            != result["snapshot_fingerprint"]
        ):
            raise ProjectError("Metin kaynağı/snapshot değişmiş; yeniden hesaplayın.")
        value = {k: copy.deepcopy(v) for k, v in result.items() if k != "worker_pid"}
        value["previews"] = []
        if value.get("advanced"):
            from veri_ufku.storage.validation_store import prior_uses

            value["prior_test_use_ids"] = prior_uses(draft)
            protected = {
                i
                for r in draft["results"]
                if r.get("text_analysis", {}).get("dataset_version")
                == value["dataset_version"]
                for i in r["text_analysis"]
                .get("advanced", {})
                .get("protected_test_row_ids", [])
            }
            if any(value["advanced"]["partitions"].get(i) != "test" for i in protected):
                raise ProjectError(
                    "Önceden test olarak ayrılan NLP RowId training/active pool olamaz."
                )
            value = stage_nlp(store, value, dataset)
        item = dict(
            id="result:" + uid(),
            dataset_version_ids=[dataset["version_id"]],
            seed=None,
            capability_id=value.get("advanced", {})
            .get("provenance", {})
            .get("capability_id", "text.inspect"),
            text_analysis=value,
        )
        validate_record(item, {dataset["version_id"]: dataset})
        draft["results"].append(item)

    updated = transaction(store, state, add)
    return updated, item


def summarize_nlp(value, uri, fp):
    value = copy.deepcopy(value)
    value["previews"] = []
    a = value["advanced"]
    a["protected_test_row_ids"] = [i for i, p in a["partitions"].items() if p == "test"]
    for key in [
        "model_bundle",
        "source_documents",
        "partitions",
        "topics",
        "topic_scores",
        "embeddings",
        "entities",
        "predictions",
        "search_results",
        "retrieval_corpus_rank",
        "active_learning",
        "fit",
        "annotations",
        "revisions",
    ]:
        a[key] = (
            None
            if key in ["model_bundle", "fit"]
            else {}
            if key == "partitions"
            else []
        )
    a.update(details_uri=uri, details_fingerprint=fp)
    return value


def stage_nlp(store, value, dataset):
    import json

    import polars as pl

    from veri_ufku.analytics.nlp import validate, validate_source
    from veri_ufku.storage.project_model import uid

    validate(value, dataset)
    validate_source(
        value,
        pl.read_parquet(store.path(dataset["snapshot_uri"])),
        dataset["import_metadata"]["columns"],
    )
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
    if len(raw) > 64 * 1024**2:
        raise ProjectError("NLP artifact64MiB sınırı.")
    folder = store.path("staging") / uid()
    folder.mkdir(mode=0o700)
    path = folder / "nlp.bin"
    path.write_bytes(raw)
    fp = file_hash(path)
    uri = "sources/" + uid() + ".bin"
    store.pending[uri] = (path, dict(**fp, kind="source", rows=None, schema=None))
    return summarize_nlp(value, uri, fp)


def load_nlp(store, summary):
    import json

    import polars as pl

    from veri_ufku.analytics.nlp import validate, validate_source

    info = summary["advanced"]
    path = store.path(info["details_uri"])
    if (
        path.stat().st_size > 64 * 1024**2
        or file_hash(path) != info["details_fingerprint"]
    ):
        raise ProjectError("NLP artifact bütünlük/boyut hatası.")

    def unique(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError
            d[k] = v
        return d

    try:
        value = json.loads(
            path.read_bytes(),
            object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ProjectError("NLP safe JSON biçimi geçersiz.") from error
    if (
        summarize_nlp(value, info["details_uri"], info["details_fingerprint"])
        != summary
    ):
        raise ProjectError("NLP summary/artifact uyuşmuyor.")
    d = next(
        d
        for d in store.state["datasets"]
        if d["version_id"] == value["dataset_version"]
    )
    if file_hash(store.path(d["snapshot_uri"])) != value["snapshot_fingerprint"]:
        raise ProjectError("NLP source snapshot değişmiş.")
    validate(value, d)
    validate_source(
        value,
        pl.read_parquet(store.path(d["snapshot_uri"])),
        d["import_metadata"]["columns"],
    )
    return value


def revise(store, state, record_id, patch, reviewer, expected_revision):
    from datetime import UTC, datetime

    from veri_ufku.storage.project_model import digest, encode, uid

    record = next(r for r in state["results"] if r["id"] == record_id)
    value = load(store, record)
    a = value["advanced"]
    if (
        a["revision_id"] != expected_revision
        or not isinstance(reviewer, str)
        or not 1 <= len(reviewer) <= 100
        or not isinstance(patch, dict)
        or set(patch) - {"annotations", "topic_names"}
    ):
        raise ProjectError("NLP optimistic revision/reviewer/patch geçersiz.")
    parent = value["run_id"]
    prior = copy.deepcopy(a["annotations"])
    topic_prior = [t["name"] for t in a["topics"]]
    if "annotations" in patch:
        a["annotations"] = patch["annotations"]
        value["spec"]["advanced"]["annotations"] = copy.deepcopy(patch["annotations"])
        a["metrics"] = None
        a["active_learning"] = []
        a["status"] = "annotation_revision_requires_refit"
        value["status"] = a["status"]
    if "topic_names" in patch:
        names = patch["topic_names"]
        if not isinstance(names, dict) or any(
            not k.isdigit()
            or not 0 <= int(k) < len(a["topics"])
            or not isinstance(v, str)
            or not 1 <= len(v) <= 100
            for k, v in names.items()
        ):
            raise ProjectError("Topic human naming geçersiz.")
        for k, v in names.items():
            a["topics"][int(k)].update(name=v, name_source="human", reviewer=reviewer)
    a["revisions"].append(
        dict(
            id="revision:" + uid(),
            parent_run_id=parent,
            prior_revision_id=expected_revision,
            created_at=datetime.now(UTC).isoformat(),
            reviewer=reviewer,
            previous_annotations=prior,
            previous_topic_names=topic_prior,
            patch=copy.deepcopy(patch),
        )
    )
    a["revision_id"] = "annotation:" + uid()
    value["run_id"] = "text:" + uid()
    value["derived_from_run_id"] = parent
    from veri_ufku.storage.experiment_store import capture

    value["experiment_capture"] = capture(
        dict(
            action="human_review", parent_run_id=parent, spec=value["spec"], patch=patch
        )
    )
    value["experiment_capture"]["config_scope"] = (
        "explicit human revision; inherited model fit from parent run, annotation changes require refit"
    )
    a["fit_from_run_id"] = parent
    a["provenance"]["parameters_hash"] = digest(encode(value["spec"]))
    value["created_at"] = datetime.now(UTC).isoformat()
    return publish(store, state, value)


def export_annotations(store, record, path, include_raw=False):
    import json
    import os
    from pathlib import Path

    import polars as pl

    from veri_ufku.storage.project_model import digest

    value = load(store, record)
    a = value["advanced"]
    docs = {x["row_id"]: x for x in a["source_documents"]}
    raw = {}
    if type(include_raw) is not bool:
        raise ProjectError("Export raw consent boolean olmalı.")
    if include_raw:
        d = next(
            d
            for d in store.state["datasets"]
            if d["version_id"] == value["dataset_version"]
        )
        f = pl.read_parquet(store.path(d["snapshot_uri"]))
        col = next(
            c["name"]
            for c in d["import_metadata"]["columns"]
            if c["id"] == value["spec"]["column"]
        )
        raw = dict(zip(f["__vu_row_id"], f[col]))
    out = dict(
        schema="NLPAnnotationExport/v1",
        dataset_version=value["dataset_version"],
        source_snapshot_id=value["source_snapshot_id"],
        column_id=value["spec"]["column"],
        revision_id=a["revision_id"],
        document_labels=value["spec"]["advanced"]["document_labels"],
        entity_labels=value["spec"]["advanced"]["entity_labels"],
        raw_text_included=include_raw,
        annotations=[
            dict(
                row_id=x["row_id"],
                label=x["label"],
                spans=x["spans"],
                decision=x["decision"],
                reviewer_hash=digest(x["reviewer"].encode()),
                source=docs[x["row_id"]],
                **({"text": raw[x["row_id"]]} if include_raw else {}),
            )
            for x in a["annotations"]
        ],
    )
    destination = Path(path).expanduser()
    with destination.open("x", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, allow_nan=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    return str(destination)
