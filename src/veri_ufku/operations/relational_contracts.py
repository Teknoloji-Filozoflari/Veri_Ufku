"""Phase11 typed schema/column lineage and immutable secondary-version bindings."""

import copy
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import polars as pl

from veri_ufku.importers.native import restore
from veri_ufku.operations.cleaning_contracts import ids, require, text
from veri_ufku.operations.formula import parse
from veri_ufku.storage.project_model import ProjectError, entity_id

KINDS = {
    "computed",
    "text_split",
    "text_combine",
    "date_parts",
    "aggregate",
    "pivot",
    "unpivot",
    "append",
    "join",
}
MULTI = {"append", "join"}
GROUPED = {"aggregate", "pivot"}
NEW_ROWS = GROUPED | MULTI | {"unpivot"}
EQUALITY = (
    "v1:null_equal;nan_reject;zero_equal;decimal_numeric;timezone_instant;text_exact"
)


def output_column(value, used_ids, used_names, dtype=None):
    if not isinstance(value, dict) or set(value) != {
        "id",
        "name",
        "original_name",
        "type",
    }:
        raise ProjectError("Çıktı sütunu tipli kimlik/ad/tür taşımalı.")
    entity_id(value["id"], "col")
    text(value["name"], 200)
    text(value["original_name"], 200)
    if (
        not value["name"].strip()
        or value["name"].startswith("__vu_")
        or "\x00" in value["name"]
        or value["id"] in used_ids
        or value["name"] in used_names
        or dtype is not None
        and value["type"] != str(dtype)
    ):
        raise ProjectError(
            "Çıktı sütun kimliği/adı benzersiz ve türü hesap sözleşmesiyle aynı olmalı."
        )
    used_ids.add(value["id"])
    used_names.add(value["name"])
    return copy.deepcopy(value)


def scalar(dtype):
    return dtype not in (pl.Binary, pl.Time) and not isinstance(
        dtype, (pl.List, pl.Struct, pl.Duration)
    )


def target(params):
    dt = restore(params)
    if dt not in (
        pl.String,
        pl.Boolean,
        pl.Int64,
        pl.UInt64,
        pl.Float64,
    ) and not isinstance(dt, pl.Decimal):
        raise ProjectError(
            "Hesaplanmış hedef String/Boolean/Int64/UInt64/Float64/Decimal olmalı."
        )
    return dt


def input_versions(request, kind, params):
    if kind in MULTI:
        other = request.get("secondary")
        if not other or params.get("secondary_version_id") != other["version_id"]:
            raise ProjectError("İkinci dataset'in değişmez sürümünü açıkça seçin.")
        return (request["version_id"], other["version_id"])
    return (request["version_id"],)


def column_types(request):
    from veri_ufku.importers.delimited import TYPES, ImportSettings, dtype
    from veri_ufku.operations.types import dtype_of

    physical = pl.read_parquet_schema(request["path"]) if request.get("path") else None
    settings = request.get("settings", {})
    return {
        c["id"]: physical[c["name"]]
        if physical is not None
        else dtype(c["type"], ImportSettings(timezone=settings.get("timezone", "")))
        if c["type"] in TYPES
        else dtype_of(c["type"])
        for c in request["columns"]
    }


def validate_parameters(request, kind, column_ids, p):
    columns = copy.deepcopy(request["columns"])
    by = {c["id"]: c for c in columns}
    available = set(by)
    ids(list(column_ids), available, True)
    # Metadata is sufficient for history validation; canonical dtype strings come from Polars schema.

    types = column_types(request)
    used_ids = set(by)
    used_names = {c["name"] for c in columns}

    def add(value, dt):
        return output_column(value, used_ids, used_names, dt)

    if kind == "computed":
        require(p, ["expression", "target", "output", "zero_policy"], ["tree"])
        tree, refs = parse(p["expression"], columns)
        if set(refs) != set(column_ids) or any(
            not scalar(types[i]) or types[i].is_temporal() for i in refs
        ):
            raise ProjectError(
                "Formül kolonları kalıcı kimliklere bağlı skaler sayı/metin/Boolean olmalı; tarih için Tarih parçaları seçin."
            )
        if "tree" in p and p["tree"] != tree:
            raise ProjectError("Saklanan formül AST'si metinle uyuşmuyor.")
        p["tree"] = tree
        if p["zero_policy"] not in ("reject", "null"):
            raise ProjectError("Sıfıra bölme reject/null politikası gerektirir.")
        columns.append(add(p["output"], target(p["target"])))
    elif kind in ("text_split", "text_combine"):
        if not column_ids or any(types[i] != pl.String for i in column_ids):
            raise ProjectError(
                "Metin işlemleri String sütunları gerektirir; önce açık tür dönüşümü seçin."
            )
        if kind == "text_split":
            require(p, ["delimiter", "outputs"])
            text(p["delimiter"], 100)
            if (
                len(column_ids) != 1
                or not p["delimiter"]
                or not isinstance(p["outputs"], list)
                or not 2 <= len(p["outputs"]) <= 16
            ):
                raise ProjectError(
                    "Bölme tek metin, boş olmayan ayraç ve2–16 çıktı gerektirir."
                )
            columns.extend(add(c, pl.String) for c in p["outputs"])
        else:
            require(p, ["separator", "null_policy", "output"])
            text(p["separator"], 100)
            if p["null_policy"] not in ("propagate", "skip"):
                raise ProjectError("Birleştirme null politikası propagate/skip olmalı.")
            columns.append(add(p["output"], pl.String))
    elif kind == "date_parts":
        require(p, ["timezone", "parts"])
        text(p["timezone"], 100)
        if len(column_ids) != 1 or not (
            types[column_ids[0]] == pl.Date
            or isinstance(types[column_ids[0]], pl.Datetime)
        ):
            raise ProjectError(
                "Tarih parçaları native Date/Datetime gerektirir; önce tarih parse edin."
            )
        dt = types[column_ids[0]]
        if p["timezone"] != "preserve":
            if not isinstance(dt, pl.Datetime) or not dt.time_zone:
                raise ProjectError(
                    "Saat dilimsiz veriye örtük timezone atanmaz; önce açık DST doğrulamalı dönüşüm yapın."
                )
            try:
                ZoneInfo(p["timezone"])
            except (ZoneInfoNotFoundError, ValueError) as error:
                raise ProjectError("IANA timezone geçersiz.") from error
        if not isinstance(p["parts"], list) or not 1 <= len(p["parts"]) <= 8:
            raise ProjectError("En az bir tarih parçası seçin.")
        seen = set()
        for part in p["parts"]:
            if (
                not isinstance(part, dict)
                or set(part) != {"part", "output"}
                or part["part"]
                not in (
                    "year",
                    "month",
                    "day",
                    "weekday",
                    "week",
                    "quarter",
                    "hour",
                    "minute",
                )
                or part["part"] in seen
                or dt == pl.Date
                and part["part"] in ("hour", "minute")
            ):
                raise ProjectError("Tarih parçası/türü geçersiz veya tekrar ediyor.")
            seen.add(part["part"])
            columns.append(add(part["output"], pl.Int64))
    elif kind in GROUPED:
        fields = ["group_columns", "equality", "max_output_rows"]
        require(
            p,
            fields
            + (
                ["metrics"]
                if kind == "aggregate"
                else ["header_column", "value_column", "aggregation", "target"]
            ),
            [] if kind == "aggregate" else ["resolved_headers"],
        )
        groups = p["group_columns"]
        ids(groups, available, kind == "aggregate")
        if p["equality"] != EQUALITY or any(not scalar(types[i]) for i in groups):
            raise ProjectError("Grup eşitliği/skaler anahtar politikası geçersiz.")
        columns = [copy.deepcopy(by[i]) for i in groups]
        used_ids = {c["id"] for c in columns}
        used_names = {c["name"] for c in columns}
        if kind == "aggregate":
            if not isinstance(p["metrics"], list) or not 1 <= len(p["metrics"]) <= 64:
                raise ProjectError("1–64 toplulaştırma ölçümü seçin.")
            referenced = set(groups)
            for m in p["metrics"]:
                if (
                    not isinstance(m, dict)
                    or set(m) != {"column_id", "method", "target", "output"}
                    or m["method"]
                    not in ("count", "count_valid", "sum", "mean", "min", "max")
                ):
                    raise ProjectError("Toplulaştırma ölçümü geçersiz.")
                i = m["column_id"]
                if (
                    m["method"] != "count"
                    and i not in by
                    or i is not None
                    and i not in by
                ):
                    raise ProjectError("Ölçüm sütunu bulunamadı.")
                if i is not None:
                    referenced.add(i)
                dt = restore(m["target"])
                if m["method"] in ("count", "count_valid"):
                    if dt != pl.Int64:
                        raise ProjectError("Sayım çıktısı Int64 olmalı.")
                elif m["method"] in ("sum", "mean"):
                    if not types[i].is_numeric() or not dt.is_numeric():
                        raise ProjectError("Sum/mean sayısal giriş/çıktı gerektirir.")
                elif not scalar(types[i]) or dt != types[i]:
                    raise ProjectError("Min/max giriş türünü tam korumalı.")
                columns.append(add(m["output"], dt))
            if referenced != set(column_ids):
                raise ProjectError("Toplulaştırma ColumnId bağı uyuşmuyor.")
        else:
            ids([p["header_column"], p["value_column"]], available)
            if (
                p["header_column"] in groups
                or p["value_column"] in groups
                or p["header_column"] == p["value_column"]
                or types[p["header_column"]] not in (pl.String, pl.Int64, pl.UInt64)
            ):
                raise ProjectError(
                    "Pivot başlığı String/Int64/UInt64 ve grup/değerden ayrı olmalı."
                )
            if p["aggregation"] not in ("reject", "count", "sum", "mean", "min", "max"):
                raise ProjectError("Pivot çakışma için açık agregasyon seçin.")
            dt = restore(p["target"])
            if p["aggregation"] in ("sum", "mean") and (
                not types[p["value_column"]].is_numeric() or not dt.is_numeric()
            ):
                raise ProjectError("Pivot sum/mean sayısal tür gerektirir.")
            if (
                p["aggregation"] == "count"
                and dt != pl.Int64
                or p["aggregation"] in ("min", "max", "reject")
                and dt != types[p["value_column"]]
            ):
                raise ProjectError("Pivot hedef türü yöntemle uyuşmuyor.")
            if set(column_ids) != set(groups + [p["header_column"], p["value_column"]]):
                raise ProjectError("Pivot ColumnId bağı uyuşmuyor.")
            headers = p.get("resolved_headers", [])
            if not isinstance(headers, list) or len(headers) > 256 - len(groups):
                raise ProjectError("Pivot başlık sınırı aşıldı.")
            seen = set()
            for h in headers:
                if (
                    not isinstance(h, dict)
                    or set(h) != {"value", "output"}
                    or not isinstance(h["value"], str)
                    or h["value"] in seen
                ):
                    raise ProjectError("Çözülmüş pivot başlığı geçersiz.")
                seen.add(h["value"])
                columns.append(add(h["output"], dt))
    elif kind == "unpivot":
        require(
            p,
            [
                "index_columns",
                "value_columns",
                "variable_output",
                "value_output",
                "max_output_rows",
            ],
        )
        ids(p["index_columns"], available, True)
        ids(p["value_columns"], available)
        if set(p["index_columns"]) & set(p["value_columns"]) or set(column_ids) != set(
            p["index_columns"] + p["value_columns"]
        ):
            raise ProjectError("Unpivot kimlik/değer sütunları ayrı olmalı.")
        dt = types[p["value_columns"][0]]
        if not scalar(dt) or any(types[i] != dt for i in p["value_columns"]):
            raise ProjectError(
                "Unpivot değer türleri tam aynı olmalı; önce açık dönüşüm seçin."
            )
        columns = [copy.deepcopy(by[i]) for i in p["index_columns"]]
        used_ids = {c["id"] for c in columns}
        used_names = {c["name"] for c in columns}
        columns.extend(
            [add(p["variable_output"], pl.String), add(p["value_output"], dt)]
        )
    elif kind in MULTI:
        input_versions(request, kind, p)
        other = request["secondary"]
        right = {c["id"]: c for c in other["columns"]}
        right_types = column_types(other)
        if kind == "join":
            require(
                p,
                [
                    "secondary_version_id",
                    "left_keys",
                    "right_keys",
                    "how",
                    "nulls_equal",
                    "right_outputs",
                    "max_output_rows",
                    "equality",
                ],
            )
            ids(p["left_keys"], available)
            ids(p["right_keys"], set(right))
            if (
                len(p["left_keys"]) != len(p["right_keys"])
                or set(column_ids) != set(p["left_keys"])
                or p["how"] not in ("inner", "left", "right", "full")
                or type(p["nulls_equal"]) is not bool
                or p["equality"] != EQUALITY
            ):
                raise ProjectError("Join türü/anahtar/null/eşitlik seçimi geçersiz.")
            for a, b in zip(p["left_keys"], p["right_keys"], strict=True):
                if types[a] != right_types[b] or not scalar(types[a]):
                    raise ProjectError(
                        "Join anahtar türleri aynı skaler tür olmalı; önce açık tür dönüşümü yapın."
                    )
            if not isinstance(p["right_outputs"], list) or len(
                p["right_outputs"]
            ) != len(right):
                raise ProjectError(
                    "Sağ sütunların ad/kimlik çakışmalarını açıkça çözün."
                )
            seen = set()
            for item in p["right_outputs"]:
                if (
                    not isinstance(item, dict)
                    or set(item) != {"column_id", "output"}
                    or item["column_id"] not in right
                    or item["column_id"] in seen
                ):
                    raise ProjectError("Sağ çıktı sütun eşlemesi geçersiz.")
                seen.add(item["column_id"])
                columns.append(add(item["output"], right_types[item["column_id"]]))
        else:
            require(p, ["secondary_version_id", "mapping", "max_output_rows"])
            if not isinstance(p["mapping"], list) or not 1 <= len(p["mapping"]) <= 256:
                raise ProjectError("Append için açık sütun eşleme seçin.")
            columns = []
            used_ids = set()
            used_names = set()
            left_seen = set()
            right_seen = set()
            for m in p["mapping"]:
                if (
                    not isinstance(m, dict)
                    or set(m) != {"left_column", "right_column", "output"}
                    or m["left_column"] not in available | {None}
                    or m["right_column"] not in set(right) | {None}
                    or m["left_column"] is None
                    and m["right_column"] is None
                ):
                    raise ProjectError(
                        "Append alan eşlemesi geçersiz; eksik taraf açık null ile seçilebilir."
                    )
                a = by.get(m["left_column"])
                b = right.get(m["right_column"])
                if a and b and types[a["id"]] != right_types[b["id"]]:
                    raise ProjectError(
                        "Append türleri uyuşmuyor; önce açık tür dönüştürün, örtük yuvarlama yok."
                    )
                if a:
                    left_seen.add(a["id"])
                if b:
                    right_seen.add(b["id"])
                columns.append(
                    add(m["output"], types[a["id"]] if a else right_types[b["id"]])
                )
            if (
                left_seen != available
                or right_seen != set(right)
                or set(column_ids) != available
            ):
                raise ProjectError(
                    "Append hiçbir sütunu sessiz düşürmez; tüm alanları eşleyin veya önce açık sütun çıkarma yapın."
                )
    else:
        raise ProjectError("Dönüşüm türü bilinmiyor.")
    if kind in NEW_ROWS:
        if (
            type(p["max_output_rows"]) is not int
            or not 1 <= p["max_output_rows"] <= 10000000
        ):
            raise ProjectError("Çıktı sınırı1–10000000 satır olmalı.")
    if not 1 <= len(columns) <= 256:
        raise ProjectError("Çıktı şeması1–256 veri sütunu olmalı.")
    return columns
