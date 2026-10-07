"""Explicit cleaning policies; schema and choices are serializable without code."""

import copy
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import polars as pl

from veri_ufku.importers.native import restore
from veri_ufku.storage.project_model import ProjectError, entity_id, uid

KINDS = {
    "missing_rows",
    "missing_columns",
    "fill",
    "dedup",
    "trim",
    "map_categories",
    "convert",
    "ordered_fill",
    "outlier",
}
LEARNED = {"missing_rows", "missing_columns", "dedup", "ordered_fill", "outlier"}
EQUALITY = (
    "v1:null_equal;nan_equal;zero_equal;decimal_numeric;timezone_instant;text_exact"
)


def learned(kind, params):
    return (
        "dataset"
        if kind in LEARNED or kind == "fill" and params["method"] != "constant"
        else "none"
    )


def require(params, fields, optional=()):
    if not set(fields) <= set(params) or set(params) - set(fields) - set(optional):
        raise ProjectError("Temizleme parametreleri eksik veya bilinmiyor.")


def text(value, limit=4096):
    if not isinstance(value, str) or len(value) > limit:
        raise ProjectError("Temizleme metin parametresi geçersiz.")


def ids(value, available, allow_empty=False):
    if (
        not isinstance(value, list)
        or not set(value) <= available
        or len(set(value)) != len(value)
        or (not value and not allow_empty)
    ):
        raise ProjectError("Temizleme ColumnId seçimi geçersiz.")


def order(params, available):
    ids(params["order_columns"], available)
    if (
        type(params["descending"]) is not bool
        or params["tie_policy"] != "input_order_then_rowid"
        or params["null_order"] != "reject"
    ):
        raise ProjectError(
            "Açık sıra, eşitlikte giriş sırası/RowId ve null sıra reddi gereklidir."
        )


def validate_parameters(kind, column_ids, params, columns):
    available = {c["id"] for c in columns}
    ids(list(column_ids), available)
    output = copy.deepcopy(columns)
    if kind in ("missing_rows", "missing_columns"):
        require(params, ["missing", "rule"], ["resolved_drop_ids"])
        if params["missing"] not in ("null", "null_nan") or params["rule"] not in (
            "any",
            "all",
        ):
            raise ProjectError(
                "Eksiklik null veya açık null+NaN; seçim herhangi biri/tümü olmalı."
            )
        if kind == "missing_columns":
            drop = params.get("resolved_drop_ids", [])
            ids(drop, set(column_ids), True)
            output = [c for c in output if c["id"] not in drop]
            if not output:
                raise ProjectError(
                    "Tüm sütunları kaldırmak engellendi; en az bir sütun koruyun."
                )
        elif "resolved_drop_ids" in params:
            raise ProjectError("Satır işleminde kolon kaldırma tarifi olamaz.")
    elif kind == "fill":
        require(params, ["method", "missing", "value", "tie_policy"])
        if (
            params["method"] not in ("constant", "mean", "median", "mode")
            or params["missing"] not in ("null", "null_nan")
            or params["tie_policy"] not in ("reject", "choose")
        ):
            raise ProjectError(
                "Doldurma yöntemi/eksiklik/mod eşitliği politikası geçersiz."
            )
        text(params["value"])
    elif kind == "trim":
        require(params, ["side"])
        if params["side"] not in ("both", "left", "right"):
            raise ProjectError("Kırpma yönü geçersiz.")
    elif kind == "map_categories":
        require(params, ["mapping", "unmapped"])
        mapping = params["mapping"]
        if (
            not isinstance(mapping, list)
            or not 1 <= len(mapping) <= 1000
            or params["unmapped"] not in ("keep", "reject")
        ):
            raise ProjectError(
                "Kategori eşleme listesi veya eşlenmeyen politikası geçersiz."
            )
        keys = set()
        for item in mapping:
            if not isinstance(item, dict) or set(item) != {"from", "to"}:
                raise ProjectError("Eşleme eski/yeni metin çiftleri içermeli.")
            text(item["from"])
            text(item["to"])
            if item["from"] in keys:
                raise ProjectError("Aynı kategori için iki hedef seçilemez.")
            keys.add(item["from"])
    elif kind == "convert":
        require(params, ["target", "on_error", "date_format", "dst_policy"])
        target = restore(params["target"])
        if target not in (
            pl.String,
            pl.Int64,
            pl.UInt64,
            pl.Float64,
            pl.Boolean,
            pl.Date,
        ) and not isinstance(target, (pl.Decimal, pl.Datetime)):
            raise ProjectError("Bu dönüşüm hedefi henüz desteklenmiyor.")
        if isinstance(target, pl.Datetime) and target.time_unit != "us":
            raise ProjectError(
                "Yeni tarih dönüşümü microsecond hassasiyetlidir; ns kaybı reddedilir."
            )
        if params["on_error"] not in ("reject", "null") or params["dst_policy"] not in (
            "reject",
            "earliest",
            "latest",
        ):
            raise ProjectError("Dönüşüm hata/DST politikası geçersiz.")
        text(params["date_format"], 100)
        if isinstance(target, pl.Datetime) and target.time_zone:
            try:
                ZoneInfo(target.time_zone)
            except (ZoneInfoNotFoundError, ValueError) as error:
                raise ProjectError(
                    "Timezone yerel IANA veritabanında bulunmalı."
                ) from error
        for c in output:
            if c["id"] in column_ids:
                c["type"] = str(target)
    elif kind == "ordered_fill":
        require(
            params,
            [
                "direction",
                "missing",
                "order_columns",
                "group_columns",
                "descending",
                "tie_policy",
                "null_order",
            ],
        )
        if params["direction"] not in ("forward", "backward") or params[
            "missing"
        ] not in ("null", "null_nan"):
            raise ProjectError("İleri/geri doldurma yönü/eksiklik politikası geçersiz.")
        order(params, available)
        ids(params["group_columns"], available)
        if set(column_ids) & (
            set(params["order_columns"]) | set(params["group_columns"])
        ):
            raise ProjectError("Doldurulan sütun sıralama/grup anahtarı olamaz.")
    elif kind == "dedup":
        require(
            params,
            [
                "keep",
                "order_columns",
                "descending",
                "tie_policy",
                "null_order",
                "equality",
            ],
        )
        order(params, available)
        if params["keep"] not in ("first", "last") or params["equality"] != EQUALITY:
            raise ProjectError(
                "Dedup ilk/son kayıt ve kayıtlı eşitlik v1 politikası gerektirir."
            )
    elif kind == "outlier":
        require(params, ["action", "multiplier", "flag_name", "flag_column_id"])
        if len(column_ids) != 1 or params["action"] not in ("mark", "filter"):
            raise ProjectError(
                "IQR için tek ölçüm sütunu ve açık işaretle/filtrele seçin."
            )
        from decimal import Decimal, InvalidOperation

        try:
            if (
                not Decimal(params["multiplier"]).is_finite()
                or Decimal(params["multiplier"]) <= 0
            ):
                raise ValueError
        except (InvalidOperation, ValueError, TypeError) as error:
            raise ProjectError("IQR çarpanı pozitif sonlu ondalık olmalı.") from error
        if params["action"] == "mark":
            name = params["flag_name"]
            text(name, 200)
            entity_id(params["flag_column_id"], "col")
            if (
                not name.strip()
                or name.startswith("__vu_")
                or "\x00" in name
                or any(
                    c["name"] == name or c["id"] == params["flag_column_id"]
                    for c in output
                )
            ):
                raise ProjectError("Aday işaret sütunu adı/kimliği benzersiz olmalı.")
            output.append(
                dict(
                    id=params["flag_column_id"],
                    name=name,
                    original_name=name,
                    type="Boolean",
                )
            )
    else:
        raise ProjectError("Temizlik yöntemi bilinmiyor.")
    if len(output) > 256:
        raise ProjectError("Çıktı256 sütun sınırını aşamaz.")
    return output


def defaults(kind):
    common_order = dict(
        order_columns=[],
        descending=False,
        tie_policy="input_order_then_rowid",
        null_order="reject",
    )
    if kind in ("missing_rows", "missing_columns"):
        return dict(missing="null", rule="all")
    if kind == "fill":
        return dict(method="constant", missing="null", value="", tie_policy="reject")
    if kind == "trim":
        return dict(side="both")
    if kind == "map_categories":
        return dict(mapping=[], unmapped="keep")
    if kind == "convert":
        return dict(
            target={"kind": "String"},
            on_error="reject",
            date_format="",
            dst_policy="reject",
        )
    if kind == "ordered_fill":
        return dict(
            **common_order, direction="forward", missing="null", group_columns=[]
        )
    if kind == "dedup":
        return dict(**common_order, keep="first", equality=EQUALITY)
    if kind == "outlier":
        return dict(
            action="mark",
            multiplier="1.5",
            flag_name="Aykırı_adayı",
            flag_column_id="col:" + uid(),
        )
    raise ProjectError("Temizlik yöntemi bilinmiyor.")
