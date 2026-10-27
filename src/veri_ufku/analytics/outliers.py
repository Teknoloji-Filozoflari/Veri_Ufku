"""Read-only outlier candidate lists; decisions happen only in prepare/apply."""

from __future__ import annotations

import math

import polars as pl

from veri_ufku.storage.project_model import ProjectError


def candidate_methods(path: str, column_name: str, row_id_name: str = "__vu_row_id"):
    frame = pl.scan_parquet(path).collect(engine="streaming")
    if column_name not in frame.columns:
        raise ProjectError("Aykırı aday sütunu bulunamadı.")
    working = frame
    if row_id_name not in working.columns:
        working = working.with_row_index(row_id_name)
    values = (
        working[column_name].drop_nulls().cast(pl.Float64, strict=False).drop_nans()
    )
    if values.len() < 4:
        raise ProjectError("Aykırı aday listesi için en az4 sonlu değer gerekir.")
    q1 = float(values.quantile(0.25, interpolation="linear"))
    q3 = float(values.quantile(0.75, interpolation="linear"))
    iqr = q3 - q1
    median = float(values.median())
    mad = float((values - median).abs().median())
    mean = float(values.mean())
    std = float(values.std(ddof=0)) or 0.0

    rows = working.select([row_id_name, column_name]).drop_nulls()
    rows = rows.with_columns(pl.col(column_name).cast(pl.Float64, strict=False))
    rows = rows.filter(pl.col(column_name).is_not_nan())

    def collect(mask_expr, method, threshold, note):
        matched = rows.filter(mask_expr)
        return dict(
            method=method,
            threshold=threshold,
            note=note,
            count=matched.height,
            row_ids=matched[row_id_name].to_list(),
        )

    iqr_low, iqr_high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    iqr_set = collect(
        (pl.col(column_name) < iqr_low) | (pl.col(column_name) > iqr_high),
        "iqr",
        1.5,
        "Çeyrekler arası yöntem; çarpık dağılımda klasik z’den daha dayanıklıdır.",
    )
    if mad == 0:
        robust = dict(
            method="robust_z",
            threshold=3.5,
            note="MAD sıfır; dayanıklı z adayı üretilemedi.",
            count=0,
            row_ids=[],
        )
    else:
        robust = collect(
            ((0.6745 * (pl.col(column_name) - median) / mad).abs() > 3.5),
            "robust_z",
            3.5,
            "Medyan ve MAD ile dayanıklı z; simetrik/normal varsayımı yumuşatır.",
        )
    if std == 0 or math.isclose(std, 0.0):
        classic = dict(
            method="classic_z",
            threshold=3.0,
            note="Standart sapma sıfır; klasik z adayı yok.",
            count=0,
            row_ids=[],
        )
    else:
        classic = collect(
            ((pl.col(column_name) - mean) / std).abs() > 3.0,
            "classic_z",
            3.0,
            "Klasik z-skoru; çarpık dağılımda yanıltıcı olabilir.",
        )
    union = sorted(
        set(iqr_set["row_ids"]) | set(robust["row_ids"]) | set(classic["row_ids"])
    )
    return dict(
        column=column_name,
        used_n=int(values.len()),
        excluded_missing=int(working.height - values.len()),
        methods=[iqr_set, robust, classic],
        union_row_ids=union,
        applied=False,
        disclaimer="Adaylar inceleme içindir; hata veya silme kararı değildir.",
    )
