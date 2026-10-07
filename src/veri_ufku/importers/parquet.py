"""Lazy native Parquet import; original columns never cross Python scalar conversion."""

from dataclasses import replace
from pathlib import Path

import polars as pl

from veri_ufku.importers.delimited import (
    Control,
    hash_artifact,
    headers,
    verify_capture,
)
from veri_ufku.importers.native import EXTRA, RESERVED, describe
from veri_ufku.storage.project_model import ProjectError, uid


def native_query(snapshot, adapter="parquet"):
    if adapter == "ipc":
        return pl.scan_ipc(snapshot["path"])
    if adapter == "ipc_stream":
        # Polars has no lazy IPC-stream reader. Bound decoded allocation at the adapter boundary.
        if Path(snapshot["path"]).stat().st_size > 64 * 1024**2:
            raise ProjectError(
                "Arrow IPC stream64MiB sınırı aşıldı; IPC file/Parquet kullanın."
            )
        frame = pl.read_ipc_stream(snapshot["path"])
        if frame.estimated_size() > 256 * 1024**2:
            raise ProjectError("Arrow IPC stream decoded256MiB sınırı aşıldı.")
        return frame.lazy()
    return pl.scan_parquet(snapshot["path"])


def parquet_schema(snapshot, adapter="parquet"):
    if adapter != "parquet":
        try:
            schema = native_query(snapshot, adapter).collect_schema()
            if not 1 <= len(schema) <= 256:
                raise ProjectError("Arrow sütun sınırı1–256.")
            for dt in schema.values():
                describe(dt)
            return schema
        except pl.exceptions.PolarsError as error:
            raise ProjectError("Arrow IPC içeriği/şeması okunamadı.") from error
    with open(snapshot["path"], "rb") as stream:
        magic = stream.read(4)
        if stream.seek(0, 2) < 8:
            raise ProjectError("Parquet dosyası başlık/son işareti için fazla kısa.")
        stream.seek(-4, 2)
        footer = stream.read(4)
    if magic != b"PAR1" or footer != b"PAR1":
        raise ProjectError(
            "Parquet PAR1 başlık/son işareti yok; uzantı format kanıtı değildir."
        )
    try:
        schema = pl.read_parquet_schema(snapshot["path"])
        if not 1 <= len(schema) <= 256:
            raise ProjectError("Parquet sütun sayısı1–256 olmalı.")
        for dt in schema.values():
            describe(dt)
        return schema
    except pl.exceptions.PolarsError as error:
        raise ProjectError(
            "Parquet metadata/şeması okunamadı; dosya bozuk veya tür desteklenmiyor."
        ) from error


def names_for(originals):
    names, warnings = headers(originals)
    used = set(RESERVED)
    for i, name in enumerate(names):
        base = name
        suffix = 2
        while name in used:
            name = f"{base}_{suffix}"
            suffix += 1
        names[i] = name
        used.add(name)
    return names, warnings


def preview_parquet(snapshot, settings, control=None):
    control = control or Control()
    verify_capture(snapshot, control)
    original = parquet_schema(snapshot, settings.adapter_id)
    names, warnings = names_for(list(original))
    try:
        frame = (
            native_query(snapshot, settings.adapter_id)
            .head(200)
            .collect(engine="streaming")
        )
    except pl.exceptions.PolarsError as error:
        raise ProjectError("Parquet sayfası okunamadı.") from error
    rows = []
    temporal = {
        n: frame[n].cast(pl.String).to_list()
        for n, t in original.items()
        if t.is_temporal()
    }
    for i in range(frame.height):
        control.check()
        values = []
        for n, t in original.items():
            if n in temporal:
                values.append(temporal[n][i] or "∅")
            elif isinstance(t, (pl.List, pl.Struct)):
                # Rust native formatting retains ns/decimal and special float values.
                values.append(str(frame[n].slice(i, 1)))
            else:
                value = frame[n][i]
                values.append("∅" if value is None else str(value))
        rows.append(values)
    types = [str(t) for t in original.values()]
    stats = {
        n: dict(
            null=frame[n].null_count(),
            nan=frame[n].is_nan().sum() if t.is_float() else 0,
            inf=frame[n].is_infinite().sum() if t.is_float() else 0,
        )
        for n, t in original.items()
    }
    warnings.append(
        "Parquet native türler korunur; list/struct açılmaz. Naive tarih UTC varsayılmaz; zaman birimi/timezone, Decimal ölçeği ve UInt64 değiştirilmez. Sütun türü dönüşümü bu adaptörde kapalı."
    )
    verify_capture(snapshot, control)
    return dict(
        schema=dict(
            names=names, original_headers=list(original), types=types, warnings=warnings
        ),
        rows=rows,
        bad=[],
        examined=frame.height,
        limited=frame.height >= 200,
        suggestions=types,
        settings=settings.data(),
        capture=snapshot,
        diagnostics=dict(fields=stats, scope="sample"),
        importable=frame.height > 0,
    )


def import_parquet(snapshot, settings, workspace, control=None):
    control = control or Control()
    verify_capture(snapshot, control)
    original = parquet_schema(snapshot, settings.adapter_id)
    names, warnings = names_for(list(original))
    rename = dict(zip(original, names, strict=True))
    schema = {rename[n]: t for n, t in original.items()}
    schema.update(
        {
            "__vu_row_id": pl.String,
            "__vu_source_record_id": pl.String,
            "__vu_start_line": pl.Int64,
            "__vu_end_line": pl.Int64,
            **EXTRA,
        }
    )
    source = native_query(snapshot, settings.adapter_id)
    count = source.select(pl.len()).collect(engine="streaming").item()
    if not 1 <= count <= 10000000:
        raise ProjectError("Parquet kayıt sayısı1–10000000 sınırında olmalı.")
    source = (
        source.rename(rename)
        .with_row_index("__vu_start_line", offset=1)
        .with_columns(pl.col("__vu_start_line").cast(pl.Int64))
    )
    accepted = 0

    def identity(batch):
        nonlocal accepted
        control.check()
        row_ids = []
        source_ids = []
        for i in range(batch.height):
            if i % 512 == 0:
                control.check()
            row_ids.append("row:" + uid())
            source_ids.append("sr:" + uid())
        accepted += batch.height
        control.progress("Native Parquet/kimlik yazımı", accepted, count)
        return batch.with_columns(
            pl.Series("__vu_row_id", row_ids, dtype=pl.String),
            pl.Series("__vu_source_record_id", source_ids, dtype=pl.String),
            pl.col("__vu_start_line").alias("__vu_end_line"),
            pl.concat_str(
                pl.lit(settings.adapter_id + ":row:"),
                pl.col("__vu_start_line").cast(pl.String),
            ).alias("__vu_source_locator"),
            pl.lit([], dtype=pl.List(pl.String)).alias("__vu_missing_fields"),
            pl.lit("{}").alias("__vu_expansion_index"),
        ).select(list(schema))

    output = Path(workspace) / (uid() + ".dataset.parquet")
    source.map_batches(
        identity,
        schema=schema,
        streamable=True,
        predicate_pushdown=False,
        projection_pushdown=False,
        slice_pushdown=False,
    ).sink_parquet(output, engine="streaming")
    control.check()
    control.disk(workspace)
    verify_capture(snapshot, control)
    if accepted != count or pl.read_parquet_schema(output) != schema:
        raise ProjectError(
            "Parquet tür/satır doğrulaması uyuşmadı; sonuç yayımlanmadı."
        )
    saved = replace(settings, native_schema={n: describe(t) for n, t in schema.items()})
    return dict(
        path=str(output),
        quarantine=None,
        artifact_fingerprint=hash_artifact(output, control),
        quarantine_fingerprint=None,
        schema=dict(
            names=names,
            original_headers=list(original),
            types=[str(t) for t in original.values()],
            warnings=warnings,
        ),
        accepted=count,
        bad_count=0,
        examined=count,
        source_snapshot_id="snapshot:" + uid(),
        settings=saved.data(),
        capture=snapshot,
        adapter_id=settings.adapter_id,
        diagnostics=dict(source_records=count, output_rows=count, scope="full"),
        backend="polars-native-" + settings.adapter_id,
    )
