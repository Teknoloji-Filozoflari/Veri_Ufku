"""Bounded cleaning batches, exact decimal statistics and disk-backed duplicate lineage."""

import math
import re
import sqlite3
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

from veri_ufku.importers.native import restore
from veri_ufku.storage.project_model import ProjectError, encode, uid

BATCH = 4096
TOKEN = "__vu_clean_order"


def missing(value, policy):
    return (
        value is None
        or policy == "null_nan"
        and isinstance(value, float)
        and math.isnan(value)
    )


def finite(value):
    return value is not None and (not isinstance(value, float) or math.isfinite(value))


def key(value):
    if value is None:
        return ["null"]
    if isinstance(value, float):
        if math.isnan(value):
            return ["nan"]
        return ["float", value.hex() if value else "0"]
    if isinstance(value, Decimal):
        with localcontext() as ctx:
            ctx.prec = 80
            return ["decimal", str(value.normalize()) if value else "0"]
    if isinstance(value, datetime):
        return [
            "datetime",
            value.astimezone(UTC).isoformat() if value.tzinfo else value.isoformat(),
        ]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, (list, dict, bytes, pl.Series)):
        raise ProjectError(
            "Nested/binary temizlik anahtarı desteklenmiyor; önce desteklenen skaler sütun seçin."
        )
    return [type(value).__name__, str(value)]


def batches(query, control, workspace):
    for frame in query.collect_batches(
        chunk_size=BATCH, maintain_order=True, engine="streaming"
    ):
        control.check()
        control.disk(workspace)
        yield frame


def exact_value(value, dtype, *, date_format="", dst_policy="reject"):
    """No truncation, float overflow, Decimal rounding or implicit local-time correction."""
    if value is None:
        return None
    try:
        if dtype == pl.String:
            return str(value)
        if dtype == pl.Boolean:
            if str(value).lower() not in ("true", "false", "evet", "hayır"):
                raise ValueError("boolean")
            return str(value).lower() in ("true", "evet")
        if dtype.is_numeric():
            number = (
                Decimal.from_float(value)
                if isinstance(value, float)
                else Decimal(str(value))
            )
            if not number.is_finite():
                raise ValueError("nonfinite")
            if dtype.is_integer():
                if number != number.to_integral_value():
                    raise ValueError("fractional integer")
                integer = int(number)
                return pl.Series([integer], dtype=dtype, strict=True)[0]
            if isinstance(dtype, pl.Decimal):
                with localcontext() as ctx:
                    ctx.prec = 80
                    if number != number.quantize(Decimal(1).scaleb(-dtype.scale)):
                        raise ValueError("decimal scale")
                    if abs(number) >= Decimal(10) ** (dtype.precision - dtype.scale):
                        raise ValueError("decimal precision")
                return pl.Series([number], dtype=dtype, strict=True)[0]
            result = pl.Series([float(number)], dtype=dtype, strict=True)[0]
            if not math.isfinite(result) or result == 0 and number != 0:
                raise ValueError("float range")
            if (
                number == number.to_integral_value()
                and Decimal.from_float(result) != number
            ):
                raise ValueError("float integer precision")
            # Converting exact decimal/string to binary float must also be exact.
            if not isinstance(value, float) and Decimal.from_float(result) != number:
                raise ValueError("binary float precision")
            return result
        if dtype == pl.Date or isinstance(dtype, pl.Datetime):
            if isinstance(value, float) or isinstance(value, (int, Decimal)):
                raise ValueError("numeric date needs explicit separate epoch method")
            raw = str(value)
            frac = re.search(r"\.(\d+)", raw)
            if frac and len(frac[1].rstrip("0")) > 6:
                raise ValueError("nanosecond precision")
            parsed = (
                datetime.strptime(raw, date_format)
                if date_format
                else (
                    date.fromisoformat(raw)
                    if dtype == pl.Date
                    else datetime.fromisoformat(raw)
                )
            )
            if dtype == pl.Date:
                if isinstance(parsed, datetime):
                    if parsed.time() != datetime.min.time() or parsed.tzinfo:
                        raise ValueError("date loses time/zone")
                    parsed = parsed.date()
                return parsed
            if not isinstance(parsed, datetime):
                parsed = datetime.combine(parsed, datetime.min.time())
            if dtype.time_zone:
                zone = ZoneInfo(dtype.time_zone)
                if parsed.tzinfo:
                    parsed = parsed.astimezone(zone)
                else:
                    possibilities = []
                    for fold in (0, 1):
                        candidate = parsed.replace(tzinfo=zone, fold=fold)
                        if (
                            candidate.astimezone(UTC)
                            .astimezone(zone)
                            .replace(tzinfo=None)
                            == parsed
                        ):
                            instant = candidate.astimezone(UTC)
                            if instant not in possibilities:
                                possibilities.append(instant)
                    if not possibilities:
                        raise ValueError("nonexistent DST time")
                    if len(possibilities) > 1 and dst_policy == "reject":
                        raise ValueError("ambiguous DST time")
                    parsed = (
                        max(possibilities)
                        if dst_policy == "latest"
                        else min(possibilities)
                    ).astimezone(zone)
            elif parsed.tzinfo:
                raise ValueError("timezone removal")
            return pl.Series([parsed], dtype=dtype, strict=True)[0]
        raise ValueError("unsupported target")
    except (
        ValueError,
        TypeError,
        OverflowError,
        InvalidOperation,
        pl.exceptions.PolarsError,
    ) as error:
        raise ProjectError(
            "Değer hedef türe kayıpsız uymuyor veya tarih/DST geçersiz; sessiz düzeltme yapılmadı."
        ) from error


def statistic(request, name, dtype, method, params, workspace, control):
    """Exact frequencies/quantile ranks on disk, with Decimal80 arithmetic."""
    path = Path(workspace) / (uid() + ".sqlite")
    db = sqlite3.connect(path)
    db.create_collation(
        "numeric", lambda a, b: (Decimal(a) > Decimal(b)) - (Decimal(a) < Decimal(b))
    )
    db.execute("CREATE TABLE v (k TEXT PRIMARY KEY, value TEXT, n INTEGER)")
    total = 0
    summation = Decimal(0)
    try:
        with localcontext() as ctx:
            ctx.prec = 80
            for frame in batches(
                pl.scan_parquet(request["path"]).select(name), control, workspace
            ):
                for value in frame[name].to_list():
                    if not finite(value):
                        continue
                    if method in ("mean", "median", "iqr"):
                        if not dtype.is_numeric():
                            raise ProjectError(
                                "Ortalama/medyan/IQR sayısal fiziksel tür gerektirir."
                            )
                        number = (
                            Decimal.from_float(value)
                            if isinstance(value, float)
                            else Decimal(value)
                        )
                        k = str(number)
                        summation += number
                    else:
                        k = encode(key(value)).decode()
                    total += 1
                    # The first typed scalar can be recovered from input by its canonical key.
                    db.execute(
                        "INSERT INTO v VALUES(?,?,1) ON CONFLICT(k) DO UPDATE SET n=n+1",
                        (k, str(value)),
                    )
                db.commit()
                control.disk(workspace)
            if not total:
                raise ProjectError(
                    "Tüm değerler eksik/geçersiz; öğrenilecek değer yok. Sabit doldurma veya başka sütun seçin."
                )
            if method == "mean":
                return summation / total, {"valid_n": total}
            if method in ("median", "iqr"):

                def quantile(q):
                    position = Decimal(total - 1) * q
                    lower = int(position)
                    upper = min(total - 1, lower + 1)
                    offset = 0
                    a = b = None
                    for number, count in db.execute(
                        "SELECT k,n FROM v ORDER BY k COLLATE numeric"
                    ):
                        control.check()
                        if offset <= lower < offset + count:
                            a = Decimal(number)
                        if offset <= upper < offset + count:
                            b = Decimal(number)
                            break
                        offset += count
                    return a + (b - a) * (position - lower)

                if method == "median":
                    return quantile(Decimal(".5")), {
                        "valid_n": total,
                        "quantile_method": "linear",
                    }
                return (quantile(Decimal(".25")), quantile(Decimal(".75"))), {
                    "valid_n": total,
                    "quantile_method": "linear",
                }
            frequency = db.execute("SELECT max(n) FROM v").fetchone()[0]
            tie_n = db.execute(
                "SELECT count(*) FROM v WHERE n=?", (frequency,)
            ).fetchone()[0]
            selected = None
            if tie_n > 1:
                if params["tie_policy"] == "reject":
                    examples = [
                        v[:80]
                        for (v,) in db.execute(
                            "SELECT value FROM v WHERE n=? ORDER BY k LIMIT 5",
                            (frequency,),
                        )
                    ]
                    raise ProjectError(
                        f"Mod eşitliği: {tie_n} değer aynı sıklıkta. İlk en fazla5 aday (görüntü örneği): {examples}. Açık bir değer seçin veya başka yöntem kullanın."
                    )
                selected = exact_value(params["value"], dtype)
                chosen = encode(key(selected)).decode()
                match = db.execute("SELECT n FROM v WHERE k=?", (chosen,)).fetchone()
                if not match or match[0] != frequency:
                    raise ProjectError(
                        "Seçilen mod değeri eşit frekanslı adaylardan biri değil."
                    )
            else:
                chosen = db.execute(
                    "SELECT k FROM v WHERE n=?", (frequency,)
                ).fetchone()[0]
                for frame in batches(
                    pl.scan_parquet(request["path"]).select(name), control, workspace
                ):
                    for value in frame[name].to_list():
                        if finite(value) and encode(key(value)).decode() == chosen:
                            selected = value
                            break
                    if selected is not None:
                        break
            return selected, {
                "valid_n": total,
                "mode_frequency": frequency,
                "mode_tie_n": tie_n,
            }
    finally:
        db.close()
        path.unlink(missing_ok=True)


def execute(request, spec, workspace, control):
    p = spec.parameters
    schema = pl.read_parquet_schema(request["path"])
    by_id = {c["id"]: c["name"] for c in request["columns"]}
    names = [by_id[c] for c in spec.column_ids]
    query = pl.scan_parquet(request["path"])
    diagnostics = {
        "changed_cells": 0,
        "modified_rows": 0,
        "new_nulls": 0,
        "parse_errors": 0,
        "null_before": 0,
        "nan_before": 0,
        "outlier_candidates": 0,
        "unfilled": 0,
        "examples": [],
        "learned_values": {},
        "warnings": [],
    }
    changed_names = set()
    mapping = {i["from"]: i["to"] for i in p.get("mapping", [])}
    k = spec.kind
    if k == "fill" and any(schema[n] == pl.Null for n in names):
        raise ProjectError(
            "Fiziksel türü Null olan sütunda hedef tür bilinmiyor; önce açık tür dönüşümü, ardından doldurma seçin."
        )
    if k in ("trim", "map_categories") and any(schema[n] != pl.String for n in names):
        raise ProjectError("Kırpma/kategori eşleme yalnız metin sütunlarında çalışır.")
    if k in ("fill", "dedup", "ordered_fill") and any(
        isinstance(schema[n], (pl.List, pl.Struct)) or schema[n] == pl.Binary
        for n in names
    ):
        raise ProjectError("Bu temizlik nested/binary türde desteklenmiyor.")
    if k in ("fill", "ordered_fill") and any(
        schema[n] == pl.Time
        or isinstance(schema[n], (pl.Datetime, pl.Duration))
        and schema[n].time_unit == "ns"
        for n in names
    ):
        raise ProjectError(
            "ns tarih doldurması hassasiyet kaybı riski nedeniyle reddedilir. Açık kayıpsız us dönüşümü yapın; metin veya native kaynak korunur."
        )
    values = {}
    relation = None
    db = None
    parts = []
    lineage_parts = []
    if k == "missing_columns":
        counters = {n: 0 for n in names}
        for frame in batches(query.select(names), control, workspace):
            for n in names:
                for v in frame[n].to_list():
                    counters[n] += missing(v, p["missing"])
                    diagnostics["null_before"] += v is None
                    diagnostics["nan_before"] += isinstance(v, float) and math.isnan(v)
        drops = [
            c
            for c in spec.column_ids
            if (
                counters[by_id[c]] > 0
                if p["rule"] == "any"
                else request["row_count"] > 0
                and counters[by_id[c]] == request["row_count"]
            )
        ]
        if len(drops) == len(request["columns"]):
            raise ProjectError(
                "Tüm sütunları kaldırmak engellendi; en az bir sütun koruyun."
            )
        from veri_ufku.operations.contracts import build

        parameters = dict(p, resolved_drop_ids=drops)
        rebuilt = build(request, k, spec.column_ids, parameters)
        from dataclasses import replace

        spec = replace(spec, parameters=parameters, output_schema=rebuilt.output_schema)
        query = query.drop([by_id[c] for c in drops])
        diagnostics["removed_columns"] = len(drops)
    elif k == "fill":
        for n in names:
            if p["method"] == "constant":
                value = exact_value(p["value"], schema[n])
                detail = {}
            else:
                value, detail = statistic(
                    request, n, schema[n], p["method"], p, workspace, control
                )
                value = (
                    exact_value(value, schema[n])
                    if p["method"] in ("mean", "median")
                    else value
                )
            values[n] = value
            diagnostics["learned_values"][n] = dict(value=str(value), **detail)
        if p["method"] != "constant":
            diagnostics["warnings"].append(
                "Tam veriden öğrenildi; ML eğitim/test ayrımından önce kullanmak sızıntı oluşturabilir. Model pipeline doldurması ayrı eğitim katında öğrenilmelidir."
            )
    elif k == "outlier":
        (q1, q3), detail = statistic(
            request, names[0], schema[names[0]], "iqr", p, workspace, control
        )
        with localcontext() as ctx:
            ctx.prec = 80
            span = q3 - q1
            low = q1 - Decimal(p["multiplier"]) * span
            high = q3 + Decimal(p["multiplier"]) * span
        values.update(low=low, high=high, span=span)
        diagnostics["learned_values"]["IQR"] = dict(
            q1=str(q1), q3=str(q3), lower=str(low), upper=str(high), **detail
        )
        diagnostics["warnings"].append(
            "IQR istatistiksel aday üretir, hata/yanlış kayıt kanıtı değildir. Sıfır IQR durumunda eşik Q1/Q3 değeridir; sabit kolonda aday yoktur."
        )
    if k in ("ordered_fill", "dedup"):
        sort = [by_id[c] for c in p.get("group_columns", [])] + [
            by_id[c] for c in p["order_columns"]
        ]
        if k == "ordered_fill" and any(
            not (schema[by_id[c]].is_numeric() or schema[by_id[c]].is_temporal())
            for c in p["order_columns"]
        ):
            raise ProjectError(
                "Zamansal doldurma sırası fiziksel sayı/tarih olmalı; metin tarihini önce açık biçimle dönüştürün."
            )
        if (
            query.select(
                pl.any_horizontal(
                    [
                        pl.col(n).is_null()
                        | (
                            pl.col(n).is_nan() | pl.col(n).is_infinite()
                            if schema[n].is_float()
                            else pl.lit(False)
                        )
                        for n in sort
                    ]
                ).any()
            )
            .collect(engine="streaming")
            .item()
        ):
            raise ProjectError(
                "Sıra/grup anahtarında null/NaN/inf var; önce açıkça düzeltin veya başka anahtar seçin."
            )
        query = query.with_row_index(TOKEN)
        reverse = k == "ordered_fill" and p["direction"] == "backward"
        group_count = len(p.get("group_columns", []))
        query = query.sort(
            sort + [TOKEN, "__vu_row_id"],
            descending=[False] * group_count
            + [p["descending"] != reverse] * (len(sort) - group_count)
            + [reverse, reverse],
            nulls_last=True,
        )
        if k == "ordered_fill":
            diagnostics["warnings"].append(
                "Geri doldurma sonraki gözlemi; azalan sırada ileri doldurma daha sonraki zamanı kullanabilir. Tahmin anında bilinmeyen değerler veri sızıntısı oluşturabilir."
            )
        else:
            db = sqlite3.connect(Path(workspace) / "dedup.sqlite")
            db.execute("CREATE TABLE chosen (k TEXT PRIMARY KEY, rid TEXT, grp TEXT)")
            for frame in batches(query, control, workspace):
                temporal_keys = {
                    n: frame[n].cast(pl.Int64).to_list()
                    for n in names
                    if schema[n].is_temporal()
                }
                for index, row in enumerate(frame.iter_rows(named=True)):
                    control.check()
                    group = encode(
                        [
                            key(
                                temporal_keys[n][index]
                                if n in temporal_keys
                                else row[n]
                            )
                            for n in names
                        ]
                    ).decode()
                    if p["keep"] == "first":
                        db.execute(
                            "INSERT OR IGNORE INTO chosen VALUES(?,?,?)",
                            (group, row["__vu_row_id"], "dup:" + uid()),
                        )
                    else:
                        db.execute(
                            "INSERT INTO chosen VALUES(?,?,?) ON CONFLICT(k) DO UPDATE SET rid=excluded.rid",
                            (group, row["__vu_row_id"], "dup:" + uid()),
                        )
                db.commit()
            relation = Path(workspace) / (uid() + "-lineage.parquet")
    last_group = None
    last_values = {}
    used = 0
    try:
        for frame in batches(query, control, workspace):
            if k == "missing_columns":
                changed_frame = frame
            else:
                temporal_keys = (
                    {
                        n: frame[n].cast(pl.Int64).to_list()
                        for n in (
                            names
                            if k == "dedup"
                            else [by_id[c] for c in p.get("group_columns", [])]
                        )
                        if schema[n].is_temporal()
                    }
                    if k in ("dedup", "ordered_fill")
                    else {}
                )
                transformed = {n: [] for n in names}
                kept = []
                flags = []
                relations = []
                # Polars string conversion preserves sub-microsecond digits for checked date conversion.
                converted_input = {
                    n: (
                        frame[n].dt.strftime(
                            "%Y-%m-%dT%H:%M:%S%.9f"
                            + ("%:z" if schema[n].time_zone else "")
                        )
                        if isinstance(schema[n], pl.Datetime)
                        else frame[n].cast(pl.String)
                    ).to_list()
                    for n in names
                    if k == "convert"
                    and (schema[n].is_temporal() or p["target"]["kind"] == "String")
                }
                for index, row in enumerate(frame.iter_rows(named=True)):
                    control.check()
                    used += 1
                    if k == "ordered_fill":
                        group = encode(
                            [
                                key(
                                    temporal_keys[by_id[c]][index]
                                    if by_id[c] in temporal_keys
                                    else row[by_id[c]]
                                )
                                for c in p["group_columns"]
                            ]
                        )
                        if group != last_group:
                            last_group = group
                            last_values = {}
                    retain = True
                    changed = False
                    absent = []
                    for n in names:
                        value = row[n]
                        diagnostics["null_before"] += value is None
                        diagnostics["nan_before"] += isinstance(
                            value, float
                        ) and math.isnan(value)
                        absent.append(missing(value, p.get("missing", "null")))
                        new = value
                        if k == "fill" and absent[-1]:
                            new = values[n]
                        elif k == "trim" and value is not None:
                            new = {
                                "both": str.strip,
                                "left": str.lstrip,
                                "right": str.rstrip,
                            }[p["side"]](value)
                        elif k == "map_categories" and value is not None:
                            if value not in mapping and p["unmapped"] == "reject":
                                raise ProjectError(
                                    "Eşleme dışında kategori bulundu; işlem uygulanmadı."
                                )
                            new = mapping.get(value, value)
                        elif k == "convert" and value is not None:
                            try:
                                new = exact_value(
                                    converted_input[n][index]
                                    if n in converted_input
                                    else value,
                                    restore(p["target"]),
                                    date_format=p["date_format"],
                                    dst_policy=p["dst_policy"],
                                )
                            except ProjectError:
                                diagnostics["parse_errors"] += 1
                                if len(diagnostics["examples"]) < 5:
                                    diagnostics["examples"].append(
                                        dict(
                                            row_id=row["__vu_row_id"],
                                            column_id=next(
                                                c
                                                for c in spec.column_ids
                                                if by_id[c] == n
                                            ),
                                            reason="Tür/hassasiyet/tarih/DST reddi",
                                        )
                                    )
                                if p["on_error"] == "reject":
                                    raise ProjectError(
                                        f"Dönüşüm hatası: RowId {row['__vu_row_id']}, sütun {n}; hiçbir sonuç uygulanmadı. Hataları yeni null olarak raporlamak için açık null politikasını seçebilirsiniz."
                                    )
                                new = None
                                diagnostics["new_nulls"] += 1
                        elif k == "ordered_fill":
                            if absent[-1]:
                                new = last_values.get(n, value)
                                if missing(new, p["missing"]):
                                    diagnostics["unfilled"] += 1
                            else:
                                last_values[n] = value
                        if k == "outlier":
                            candidate = False
                            if finite(value):
                                number = (
                                    Decimal.from_float(value)
                                    if isinstance(value, float)
                                    else Decimal(value)
                                )
                                candidate = (
                                    number < values["low"] or number > values["high"]
                                )
                            diagnostics["outlier_candidates"] += candidate
                            flags.append(candidate)
                            if p["action"] == "filter":
                                retain = not candidate
                        if k == "missing_rows":
                            retain = not (
                                any(absent) if p["rule"] == "any" else all(absent)
                            )
                        same = (
                            (new == value)
                            or isinstance(new, float)
                            and isinstance(value, float)
                            and math.isnan(new)
                            and math.isnan(value)
                        )
                        if not same:
                            changed_names.add(n)
                            diagnostics["changed_cells"] += 1
                            changed = True
                        transformed[n].append(new)
                    diagnostics["modified_rows"] += changed
                    if k == "dedup":
                        group = encode(
                            [
                                key(
                                    temporal_keys[n][index]
                                    if n in temporal_keys
                                    else row[n]
                                )
                                for n in names
                            ]
                        ).decode()
                        chosen, group_id = db.execute(
                            "SELECT rid,grp FROM chosen WHERE k=?", (group,)
                        ).fetchone()
                        retain = row["__vu_row_id"] == chosen
                        relations.append(
                            dict(
                                group_id=group_id,
                                row_id=row["__vu_row_id"],
                                source_record_id=row["__vu_source_record_id"],
                                survivor_row_id=chosen,
                                retained=retain,
                            )
                        )
                    kept.append(retain)
                changed_frame = frame
                if k in ("fill", "trim", "map_categories", "convert", "ordered_fill"):
                    changed_frame = frame.with_columns(
                        [
                            pl.Series(
                                n,
                                transformed[n],
                                dtype=restore(p["target"])
                                if k == "convert"
                                else schema[n],
                                strict=True,
                            )
                            for n in names
                        ]
                    )
                if k == "outlier" and p["action"] == "mark":
                    changed_frame = changed_frame.with_columns(
                        pl.Series(p["flag_name"], flags, dtype=pl.Boolean)
                    )
                changed_frame = changed_frame.filter(pl.Series(kept, dtype=pl.Boolean))
                if relations:
                    part = Path(workspace) / (uid() + "-relation.parquet")
                    pl.DataFrame(relations).write_parquet(part)
                    lineage_parts.append(part)
            part = Path(workspace) / (uid() + "-part.parquet")
            changed_frame.write_parquet(part)
            parts.append(part)
            control.disk(workspace)
            control.progress("Temizlik: tam veri", used, request["row_count"])
        if not parts:
            output_schema = {
                c["name"]: restore(p["target"])
                if k == "convert" and c["id"] in spec.column_ids
                else schema.get(c["name"], pl.Boolean)
                for c in spec.output_schema
            }
            output_schema.update(
                {n: t for n, t in schema.items() if n.startswith("__vu_")}
            )
            part = Path(workspace) / (uid() + "-part.parquet")
            pl.DataFrame(schema=output_schema).write_parquet(part)
            parts.append(part)
        output = Path(workspace) / (uid() + ".parquet")
        final = pl.scan_parquet(parts)
        if k in ("ordered_fill", "dedup"):
            final = final.sort(TOKEN).drop(TOKEN)
        final.sink_parquet(output, maintain_order=True, engine="streaming")
        if relation:
            if lineage_parts:
                pl.scan_parquet(lineage_parts).sink_parquet(
                    relation, maintain_order=True, engine="streaming"
                )
            else:
                pl.DataFrame(
                    schema={
                        "group_id": pl.String,
                        "row_id": pl.String,
                        "source_record_id": pl.String,
                        "survivor_row_id": pl.String,
                        "retained": pl.Boolean,
                    }
                ).write_parquet(relation)
        control.disk(workspace)
        if k == "convert":
            changed_names.update(n for n in names if schema[n] != restore(p["target"]))
        diagnostics["changed_columns"] = (
            len(request["columns"]) - len(spec.output_schema)
            if k == "missing_columns"
            else 1
            if k == "outlier" and p["action"] == "mark"
            else len(changed_names)
        )
        return spec, output, diagnostics, relation
    finally:
        if db:
            db.close()
            (Path(workspace) / "dedup.sqlite").unlink(missing_ok=True)
        for part in parts + lineage_parts:
            part.unlink(missing_ok=True)
