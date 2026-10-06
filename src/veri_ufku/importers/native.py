"""Data-only native type descriptors and exact structured scalar semantics."""

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import polars as pl

from veri_ufku.importers.delimited import INTERNAL, TYPES, ImportSettings, convert
from veri_ufku.storage.project_model import ProjectError

EXTRA = {
    "__vu_source_locator": pl.String,
    "__vu_missing_fields": pl.List(pl.String),
    "__vu_expansion_index": pl.String,
}
RESERVED = INTERNAL + tuple(EXTRA)
PRIMITIVES = {
    str(t): t
    for t in (
        pl.Null,
        pl.String,
        pl.Boolean,
        pl.Int8,
        pl.Int16,
        pl.Int32,
        pl.Int64,
        pl.UInt8,
        pl.UInt16,
        pl.UInt32,
        pl.UInt64,
        pl.Float32,
        pl.Float64,
        pl.Date,
        pl.Time,
        pl.Binary,
    )
}


def describe(dtype, depth=0):
    if depth > 16:
        raise ProjectError("Nested tür derinliği16 sınırını aşıyor.")
    if str(dtype) in PRIMITIVES:
        return {"kind": str(dtype)}
    if isinstance(dtype, pl.Decimal):
        return {
            "kind": "Decimal",
            "precision": dtype.precision or 38,
            "scale": dtype.scale,
        }
    if isinstance(dtype, pl.Datetime):
        return {"kind": "Datetime", "unit": dtype.time_unit, "zone": dtype.time_zone}
    if isinstance(dtype, pl.List):
        return {"kind": "List", "item": describe(dtype.inner, depth + 1)}
    if isinstance(dtype, pl.Struct):
        return {
            "kind": "Struct",
            "fields": {f.name: describe(f.dtype, depth + 1) for f in dtype.fields},
        }
    raise ProjectError(
        f"Parquet türü korunamıyor: {dtype}. Otomatik kayıplı dönüşüm yapılmadı."
    )


def restore(value, depth=0):
    if depth > 16 or not isinstance(value, dict):
        raise ProjectError("Native tür tanımı geçersiz veya aşırı derin.")
    kind = value.get("kind")
    if kind in PRIMITIVES and set(value) == {"kind"}:
        return PRIMITIVES[kind]
    if kind == "Decimal" and set(value) == {"kind", "precision", "scale"}:
        if (
            all(type(value[k]) is int for k in ("precision", "scale"))
            and 1 <= value["precision"] <= 38
            and 0 <= value["scale"] <= value["precision"]
        ):
            return pl.Decimal(value["precision"], value["scale"])
    if kind == "Datetime" and set(value) == {"kind", "unit", "zone"}:
        if value["unit"] in ("ms", "us", "ns") and (
            value["zone"] is None
            or isinstance(value["zone"], str)
            and len(value["zone"]) <= 100
        ):
            if value["zone"] is not None:
                try:
                    ZoneInfo(value["zone"])
                except (ZoneInfoNotFoundError, ValueError) as error:
                    raise ProjectError(
                        "Native timezone IANA kimliği olmalı."
                    ) from error
            return pl.Datetime(value["unit"], value["zone"])
    if kind == "List" and set(value) == {"kind", "item"}:
        return pl.List(restore(value["item"], depth + 1))
    if (
        kind == "Struct"
        and set(value) == {"kind", "fields"}
        and isinstance(value["fields"], dict)
        and len(value["fields"]) <= 256
    ):
        if any(
            not isinstance(k, str) or not k or len(k) > 4096 for k in value["fields"]
        ):
            raise ProjectError("Struct alan adları geçersiz.")
        return pl.Struct({k: restore(v, depth + 1) for k, v in value["fields"].items()})
    raise ProjectError("Native tür destek sınırı dışında.")


@dataclass(frozen=True)
class StructuredSettings:
    adapter_id: str = "json"
    record_path: str = ""
    flatten: bool = False
    expand_lists: tuple[str, ...] = ()
    mixed_policy: str = "reject"
    sheet: str = ""
    cell_range: str = ""
    header_row: int = 1
    merged_cells: str = "reject"
    blank_rows: str = "keep"
    formulas: str = "formula"
    excel_dates: str = "dates"
    bad_rows: str = "stop"
    types: tuple[str, ...] = ()
    column_names: tuple[str, ...] = ()
    date_format: str = "%Y-%m-%d"
    timezone: str = ""
    native_schema: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.adapter_id not in ("json", "jsonl", "xlsx", "parquet"):
            raise ProjectError("Adaptör bulunamadı.")
        if any(
            not isinstance(getattr(self, k), str) or len(getattr(self, k)) > 4096
            for k in ("record_path", "sheet", "cell_range", "date_format", "timezone")
        ):
            raise ProjectError("Format seçim metni sınır dışında.")
        if (
            type(self.flatten) is not bool
            or type(self.header_row) is not int
            or not 0 <= self.header_row <= 1048576
        ):
            raise ProjectError("Düzleştirme/başlık seçimi geçersiz.")
        if (
            self.mixed_policy not in ("reject", "json_text")
            or self.merged_cells not in ("reject", "anchor")
            or self.blank_rows not in ("keep", "skip")
            or self.formulas not in ("formula", "text", "cached")
            or self.excel_dates not in ("dates", "serial")
            or self.bad_rows not in ("stop", "quarantine")
        ):
            raise ProjectError("Format davranışı geçersiz.")
        if (
            len(self.expand_lists) > 8
            or any(
                not isinstance(p, str) or not p.startswith("/") or len(p) > 4096
                for p in self.expand_lists
            )
            or len(set(self.expand_lists)) != len(self.expand_lists)
        ):
            raise ProjectError("En fazla8 farklı JSON Pointer listesi seçin.")
        for pointer in (self.record_path, *self.expand_lists):
            if pointer and (
                not pointer.startswith("/") or re.search(r"~(?![01])", pointer)
            ):
                raise ProjectError(
                    "JSON Pointer yolu geçersiz; ~0 ve ~1 kaçışlarını kullanın."
                )
        paths = sorted(self.expand_lists)
        if any(
            b.startswith(a + "/") for i, a in enumerate(paths) for b in paths[i + 1 :]
        ):
            raise ProjectError(
                "Bir listenin kendisi ve iç listesi aynı anda açılamaz; ayrı seçim yapın."
            )
        if (
            len(self.types) > 256
            or any(t not in TYPES + ("auto",) for t in self.types)
            or len(self.column_names) > 256
            or any(not isinstance(n, str) or len(n) > 4096 for n in self.column_names)
        ):
            raise ProjectError("Sütun türü/ad bağı geçersiz.")
        ImportSettings(date_format=self.date_format, timezone=self.timezone)
        if not isinstance(self.native_schema, dict) or len(self.native_schema) > 263:
            raise ProjectError("Native şema boyutu geçersiz.")
        for key, value in self.native_schema.items():
            if not isinstance(key, str) or len(key) > 4096:
                raise ProjectError("Native sütun adı geçersiz.")
            restore(value)
        if self.adapter_id == "parquet" and (
            self.types or self.flatten or self.expand_lists
        ):
            raise ProjectError(
                "Parquet türleri korunur; örtük tür/liste dönüşümü desteklenmiyor."
            )

    @classmethod
    def from_dict(cls, value):
        data = dict(value)
        for key in ("expand_lists", "types", "column_names"):
            data[key] = tuple(data.get(key, ()))
        try:
            return cls(**data)
        except TypeError as error:
            raise ProjectError("Yapılandırılmış import alanları geçersiz.") from error

    def data(self):
        return {
            k: list(v) if isinstance(v, tuple) else v for k, v in asdict(self).items()
        }


def canonical(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, Decimal)):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return json.dumps(value.isoformat(), ensure_ascii=False)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(canonical(v) for v in value) + "]"
    if isinstance(value, dict):
        return (
            "{"
            + ",".join(
                json.dumps(k, ensure_ascii=False) + ":" + canonical(value[k])
                for k in sorted(value)
            )
            + "}"
        )
    raise ProjectError("JSON değeri desteklenmiyor.")


class TypeProfile:
    def __init__(self, nodes=None):
        self.nodes = nodes if nodes is not None else [0]
        self.nodes[0] += 1
        if self.nodes[0] > 4096:
            raise ProjectError("Nested şema toplam 4096 alan sınırını aştı.")
        self.json_text = False
        self.kinds = set()
        self.count = 0
        self.nulls = 0
        self.integer_min = 0
        self.integer_max = 0
        self.scale = 0
        self.digits = 1
        self.fields = {}
        self.item = None

    def add(self, value, depth=0):
        if depth > 16:
            raise ProjectError("JSON nested derinliği16 sınırını aştı.")
        self.count += 1
        if value is None:
            self.nulls += 1
            return
        if type(value) is bool:
            kind = "boolean"
        elif isinstance(value, int):
            kind = "integer"
            self.integer_min = min(self.integer_min, value)
            self.integer_max = max(self.integer_max, value)
            self.digits = max(self.digits, len(str(abs(value))))
        elif isinstance(value, Decimal):
            kind = "decimal"
            self.scale = max(self.scale, max(0, -value.as_tuple().exponent))
            self.digits = max(self.digits, max(1, value.adjusted() + 1))
        elif isinstance(value, datetime):
            kind = "datetime"
        elif isinstance(value, date):
            kind = "date"
        elif isinstance(value, time):
            kind = "time"
        elif isinstance(value, str):
            kind = "text"
        elif isinstance(value, list):
            kind = "list"
            self.item = self.item or TypeProfile(self.nodes)
            for v in value:
                self.item.add(v, depth + 1)
        elif isinstance(value, dict):
            kind = "struct"
            if len(value) > 256:
                raise ProjectError("JSON nesnesi256 alan sınırını aştı.")
            for k, v in value.items():
                if k not in self.fields and len(self.fields) >= 256:
                    raise ProjectError("Nested alan birleşimi256 sınırını aştı.")
                if k not in self.fields:
                    self.fields[k] = TypeProfile(self.nodes)
                self.fields[k].add(v, depth + 1)
        else:
            raise ProjectError("Yapılandırılmış değer türü desteklenmiyor.")
        self.kinds.add(kind)

    def resolve(self, policy, depth=0):
        kinds = self.kinds
        if not kinds:
            return pl.Null, False
        if kinds <= {"integer", "decimal"}:
            if (
                kinds == {"integer"}
                and -(2**63) <= self.integer_min
                and self.integer_max < 2**63
            ):
                return pl.Int64, False
            precision = self.digits + self.scale
            if precision <= 38:
                return pl.Decimal(max(1, precision), self.scale), False
            self.json_text = True
            return pl.String, policy == "reject"
        if len(kinds) > 1:
            self.json_text = True
            return pl.String, policy == "reject"
        kind = next(iter(kinds))
        if kind == "list":
            dtype, blocked = (
                self.item.resolve(policy, depth + 1) if self.item else (pl.Null, False)
            )
            return pl.List(dtype), blocked
        if kind == "struct":
            if not self.fields:
                self.json_text = True
                return pl.String, policy == "reject"
            resolved = {
                k: v.resolve(policy, depth + 1) for k, v in sorted(self.fields.items())
            }
            return pl.Struct({k: v[0] for k, v in resolved.items()}), any(
                v[1] for v in resolved.values()
            )
        return {
            "text": pl.String,
            "boolean": pl.Boolean,
            "date": pl.Date,
            "datetime": pl.Datetime("us"),
            "time": pl.Time,
        }[kind], False

    def report(self, rows, depth=0):
        return dict(
            observed_types=sorted(self.kinds),
            missing=rows - self.count,
            explicit_null=self.nulls,
            item=self.item.report(self.item.count, depth + 1)
            if self.item and depth < 16
            else None,
            fields={
                k: v.report(self.count - self.nulls, depth + 1)
                for k, v in self.fields.items()
            }
            if depth < 16
            else {},
        )


def native_value(value, dtype, profile=None):
    if value is None:
        return None
    if dtype == pl.String and (
        not isinstance(value, str) or profile is not None and profile.json_text
    ):
        return canonical(value)
    if isinstance(dtype, pl.Decimal):
        return Decimal(value)
    if isinstance(dtype, pl.List):
        return [
            native_value(v, dtype.inner, profile.item if profile else None)
            for v in value
        ]
    if isinstance(dtype, pl.Struct):
        return {
            f.name: native_value(
                value.get(f.name),
                f.dtype,
                profile.fields.get(f.name) if profile else None,
            )
            for f in dtype.fields
        }
    return value


def selected_value(value, kind, settings):
    if value is None:
        return None
    if kind == "text":
        return value if isinstance(value, str) else canonical(value)
    return convert(
        value if isinstance(value, str) else str(value),
        kind,
        ImportSettings(date_format=settings.date_format, timezone=settings.timezone),
    )
