"""Publish verified statistical results through the existing ACTIVE transaction."""

import copy
import json
from pathlib import Path

import polars as pl

from veri_ufku.operations.contracts import active_datasets
from veri_ufku.statistics.contracts import AnalysisSpec
from veri_ufku.storage.project_model import ProjectError, decode, uid
from veri_ufku.storage.project_store import file_hash


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
            raise ProjectError("İstatistik eski veri sürümüne ait; yeniden çalıştırın.")
        spec = AnalysisSpec.from_dict(result["spec"])
        spec.validate(dataset["import_metadata"]["columns"], run=True)
        fingerprint = {
            k: store.manifest["artifacts"][dataset["snapshot_uri"]][k]
            for k in ("size", "sha256")
        }
        if (
            result["provenance"]["snapshot_fingerprint"] != fingerprint
            or file_hash(store.path(dataset["snapshot_uri"])) != fingerprint
        ):
            raise ProjectError("İstatistik veri snapshot bağı/hash uyuşmuyor.")
        if set(result["paths"]) != (
            {"result", "members", "details", "diagnostic_png"}
            if spec.path in ("survival", "dimensions")
            else {"result", "members", "details", "chains", "diagnostic_png"}
            if spec.path == "bayes"
            else {"result", "members", "diagnostic", "diagnostic_png"}
            if spec.path == "models"
            else {"result", "members", "details"}
            if spec.path
            in ("advanced", "resampling", "experiments", "causal", "survival")
            else {"result", "members"}
        ):
            raise ProjectError("İstatistik artifact bağları eksik.")
        transaction = store.path("staging") / uid()
        transaction.mkdir(mode=0o700)
        uris = {}
        for key, source_name in result["paths"].items():
            source = Path(source_name)
            if source.is_symlink() or file_hash(source) != result["fingerprints"][key]:
                raise ProjectError("İstatistik artifact hash değişmiş veya symlink.")
            target = transaction / (key + source.suffix)
            with source.open("rb") as inp, target.open("xb") as out:
                while chunk := inp.read(1024**2):
                    out.write(chunk)
                    checkpoint("analysis_copy_chunk")
            if file_hash(target) != result["fingerprints"][key]:
                raise ProjectError("İstatistik kopya doğrulaması başarısız.")
            parquet = key in ("members", "details")
            uri = (
                ("snapshots/" if parquet else "sources/")
                + uid()
                + (".parquet" if parquet else ".bin")
            )
            info = dict(
                **result["fingerprints"][key],
                kind="parquet" if parquet else "source",
                rows=pl.scan_parquet(target).select(pl.len()).collect().item()
                if parquet
                else None,
                schema={k: str(v) for k, v in pl.read_parquet_schema(target).items()}
                if parquet
                else None,
            )
            store.pending[uri] = (target, info)
            uris[key] = uri
        saved = json.loads(store.pending[uris["result"]][0].read_text())
        expected = {
            k: v
            for k, v in result.items()
            if k not in ("paths", "fingerprints", "member_digest", "worker_pid")
        }
        if saved != expected:
            raise ProjectError("İstatistik JSON sonucu ekrandaki hesapla uyuşmuyor.")
        members = pl.read_parquet(store.pending[uris["members"]][0])
        if (
            members.columns != ["row_id"]
            or members.height != saved["used_rows"]
            or members["row_id"].n_unique() != members.height
        ):
            raise ProjectError("İstatistik n/RowId üyeliği uyuşmuyor.")
        source = pl.scan_parquet(store.path(dataset["snapshot_uri"])).select(
            pl.col("__vu_row_id").alias("row_id")
        )
        if (
            members.lazy()
            .join(source, on="row_id", how="anti")
            .limit(1)
            .collect()
            .height
        ):
            raise ProjectError("İstatistik kökeninde bilinmeyen RowId var.")
        if spec.path == "bayes":
            from veri_ufku.statistics.bayes import verify_chains, verify_source

            verify_source(
                store.path(dataset["snapshot_uri"]),
                dataset["import_metadata"]["columns"],
                saved,
                pl.read_parquet(store.pending[uris["details"]][0]),
                members,
            )
            verify_chains(store.pending[uris["chains"]][0], saved)
        if spec.path == "dimensions":
            from veri_ufku.statistics.dimensions import verify_source

            verify_source(
                store.path(dataset["snapshot_uri"]),
                dataset["import_metadata"]["columns"],
                saved,
                pl.read_parquet(store.pending[uris["details"]][0]),
                members,
                dataset.get("semantic_metadata", {}),
            )
        if spec.path == "survival":
            from veri_ufku.statistics.survival import verify_source

            verify_source(
                store.path(dataset["snapshot_uri"]),
                dataset["import_metadata"]["columns"],
                saved,
                pl.read_parquet(store.pending[uris["details"]][0]),
                members,
                dataset.get("semantic_metadata", {}),
            )
        if spec.path == "causal":
            from veri_ufku.statistics.causal import verify_source

            verify_source(
                store.path(dataset["snapshot_uri"]),
                dataset["import_metadata"]["columns"],
                saved,
                pl.read_parquet(store.pending[uris["details"]][0]),
                members,
            )
        if spec.path == "experiments":
            from veri_ufku.statistics.experiments import verify_source

            verify_source(
                store.path(dataset["snapshot_uri"]),
                dataset["import_metadata"]["columns"],
                saved,
                pl.read_parquet(store.pending[uris["details"]][0]),
                members,
            )
        if spec.path == "resampling":
            from veri_ufku.statistics.resampling import verify_details, verify_source

            verify_details(
                saved, pl.read_parquet(store.pending[uris["details"]][0]), members
            )
            verify_source(
                store.path(dataset["snapshot_uri"]),
                dataset["import_metadata"]["columns"],
                saved,
            )
        if spec.path == "advanced":
            from veri_ufku.statistics.missing_sampling import verify_details

            if saved["source_columns"] != dataset["import_metadata"]["columns"]:
                raise ProjectError("İleri hesap ColumnId şeması değişmiş.")
            verify_details(
                store.path(dataset["snapshot_uri"]),
                spec,
                saved,
                pl.read_parquet(store.pending[uris["details"]][0]),
                members,
            )
        analysis = dict(saved, artifact_uris=uris)
        store.state = copy.deepcopy(state)
        store.state["results"].append(
            dict(
                id="result:" + uid(),
                result_version=saved["result_version"],
                dataset_version_ids=[dataset["version_id"]],
                seed=saved["provenance"].get("seed"),
                capability_id="statistics." + spec.method.replace("_", "-"),
                analysis=analysis,
            )
        )
        store.save(checkpoint=checkpoint)
        return copy.deepcopy(store.state)
    except BaseException:
        if decode(store._read("ACTIVE", 4096))["commit_id"] != commit:
            store._load("ACTIVE")
            store.pending.clear()
        else:
            store.state, store.pending = previous, pending
        raise
