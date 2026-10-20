"""Adopt chart artifacts using the existing immutable manifest/ACTIVE transaction."""

import copy
from pathlib import Path

import polars as pl

from veri_ufku.charts.contracts import ChartSpec
from veri_ufku.storage.project_model import ProjectError, decode, encode, uid
from veri_ufku.storage.project_store import file_hash


def publish(store, state, result, checkpoint=lambda point: None):
    store._guard()
    previous, pending = store.state, dict(store.pending)
    commit = store.commit_id
    try:
        dataset = next(
            (
                d
                for d in state["datasets"]
                if d["version_id"] == result["dataset_version"]
            ),
            None,
        )
        if not dataset:
            raise ProjectError("Grafik veri sürümü projede yok.")
        from veri_ufku.operations.contracts import active_datasets

        if dataset["version_id"] not in {
            d["version_id"] for d in active_datasets(state)
        }:
            raise ProjectError("Grafik eski sürüme ait; yeniden oluşturun.")
        spec = ChartSpec.from_dict(result["spec"])
        spec.validate(dataset["import_metadata"]["columns"])
        if spec.kind.startswith("array-") and result["provenance"].get(
            "array_source"
        ) != dataset["import_metadata"]["settings"].get("format_metadata", {}):
            raise ProjectError("Grafik kaynak kesit metadata bağı uyuşmuyor.")
        artifact = store.manifest["artifacts"][dataset["snapshot_uri"]]
        if file_hash(store.path(dataset["snapshot_uri"])) != {
            k: artifact[k] for k in ("size", "sha256")
        }:
            raise ProjectError("Grafik dataset snapshot değişmiş.")
        if result["provenance"]["snapshot_fingerprint"] != {
            k: artifact[k] for k in ("size", "sha256")
        }:
            raise ProjectError("Grafik snapshot bağı uyuşmuyor.")
        tx = store.path("staging") / uid()
        tx.mkdir(mode=0o700)
        uris = {}
        for key in ("data", "members", "png", "svg", "result") + (
            ("pdf",) if "pdf" in result["paths"] else ()
        ):
            source = Path(result["paths"][key])
            fp = result["fingerprints"][key]
            if source.is_symlink() or file_hash(source) != fp:
                raise ProjectError("Grafik artifact değişmiş veya symlink.")
            dest = tx / (key + source.suffix)
            with source.open("rb") as inp, dest.open("xb") as out:
                while chunk := inp.read(1024**2):
                    out.write(chunk)
                    checkpoint("chart_copy_chunk")
            if file_hash(dest) != fp:
                raise ProjectError("Grafik kopyası doğrulanamadı.")
            parquet = key in ("data", "members")
            uri = (
                ("snapshots/" if parquet else "sources/")
                + uid()
                + (".parquet" if parquet else ".bin")
            )
            info = dict(
                **fp,
                kind="parquet" if parquet else "source",
                rows=pl.scan_parquet(dest).select(pl.len()).collect().item()
                if parquet
                else None,
                schema={k: str(v) for k, v in pl.read_parquet_schema(dest).items()}
                if parquet
                else None,
            )
            store.pending[uri] = (dest, info)
            uris[key] = uri
        data = pl.scan_parquet(store.pending[uris["data"]][0])
        members = pl.scan_parquet(store.pending[uris["members"]][0])
        source = pl.scan_parquet(store.path(dataset["snapshot_uri"]))
        if (
            members.join(
                source.select(pl.col("__vu_row_id").alias("row_id")),
                on="row_id",
                how="anti",
            )
            .limit(1)
            .collect()
            .height
            or members.join(data.select("point_id"), on="point_id", how="anti")
            .limit(1)
            .collect()
            .height
        ):
            raise ProjectError("Grafik kökeni var olmayan RowId/nokta içeriyor.")
        if (
            members.unique().select(pl.len()).collect().item()
            != members.select(pl.len()).collect().item()
        ):
            raise ProjectError("Grafik üyeliği tekrarlandı.")
        expected = pl.DataFrame(result["points"]).select(
            "point_id", "x", "y", "n", "label"
        )
        if not data.collect().equals(expected):
            raise ProjectError("Grafik referans tablosu sonuçla uyuşmuyor.")
        actual_counts = dict(members.group_by("point_id").len().collect().iter_rows())
        if any(
            point["n"] != actual_counts.get(point["point_id"], 0)
            for point in result["points"]
        ):
            raise ProjectError("Grafik nokta n ile RowId üyeliği uyuşmuyor.")
        if any(
            file_hash(Path(result["paths"][k])) != result["fingerprints"][k]
            for k in result["paths"]
        ):
            raise ProjectError("Grafik artifact kayıt sırasında değişti.")
        chart = {
            k: copy.deepcopy(result[k])
            for k in (
                "dataset_version",
                "spec",
                "summary",
                "details",
                "warnings",
                "dataset_n",
                "population_n",
                "used_n",
                "scope",
                "filters",
                "provenance",
                "render",
            )
        }
        chart["artifact_uris"] = uris
        chart = decode(encode(chart))
        store.state = copy.deepcopy(state)
        store.state["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=[dataset["version_id"]],
                seed=None,
                capability_id="chart." + spec.kind,
                chart=chart,
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
