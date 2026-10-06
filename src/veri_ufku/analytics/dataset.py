"""Bounded pages and disk backed exact profiles of immutable Parquet versions."""

import math
import re
import sqlite3
from dataclasses import asdict
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

import polars as pl

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.storage.project_model import ProjectError, digest, encode, uid

PAGE_ROWS = 200
PAGE_BYTES = 4 * 1024 * 1024
CELL_CHARS = 256
TOP_VALUES = 20
QUANTILES = (
    Decimal(".05"),
    Decimal(".25"),
    Decimal(".5"),
    Decimal(".75"),
    Decimal(".95"),
)


def checked(request, control):
    control.check()
    if (
        Path(request["path"]).is_symlink()
        or hash_artifact(request["path"], control) != request["fingerprint"]
    ):
        raise ProjectError(
            "Dataset snapshot değişmiş; tablo/profil sonucu kabul edilmedi. Projeyi sağlam kopyadan açın."
        )


def literal(text, dtype):
    try:
        if dtype == pl.String:
            return pl.lit(text)
        if dtype.is_integer():
            if not re.fullmatch(r"[+-]?\d+", text):
                raise ValueError()
            return pl.lit(pl.Series([int(text)], dtype=dtype, strict=True))
        if isinstance(dtype, pl.Decimal):
            with localcontext() as ctx:
                ctx.prec = 80
                value = Decimal(text)
                if not value.is_finite() or value != value.quantize(
                    Decimal(1).scaleb(-dtype.scale)
                ):
                    raise ValueError()
            return pl.lit(pl.Series([value], dtype=dtype, strict=True))
        if dtype.is_float():
            value = pl.Series([float(text)], dtype=dtype, strict=True)[0]
            if (
                not math.isfinite(value)
                or (value == 0 and Decimal(text) != 0)
                or (
                    Decimal(text) == Decimal(text).to_integral_value()
                    and Decimal.from_float(value) != Decimal(text)
                )
            ):
                raise ValueError()
            return pl.lit(value, dtype=dtype)
        if dtype == pl.Boolean:
            if text.casefold() not in ("true", "false", "evet", "hayır"):
                raise ValueError()
            return pl.lit(text.casefold() in ("true", "evet"))
        if dtype == pl.Date:
            return pl.lit(date.fromisoformat(text), dtype=pl.Date)
        if dtype == pl.Time:
            if re.search(r"\.\d{7,}", text):
                raise ValueError()
            return pl.lit(time.fromisoformat(text), dtype=pl.Time)
        if isinstance(dtype, pl.Datetime):
            match = re.search(r"\.(\d+)", text)
            digits = {"ms": 3, "us": 6, "ns": 9}[dtype.time_unit]
            if match and len(match[1].rstrip("0")) > digits:
                raise ValueError()
            value = pl.Series([text]).str.to_datetime(
                time_unit=dtype.time_unit, time_zone=dtype.time_zone, strict=True
            )
            if value.dtype.time_zone != dtype.time_zone:
                raise ValueError()
            return pl.lit(value)
        raise ProjectError(
            "Bu fiziksel türde değer karşılaştırması desteklenmiyor; null filtresini kullanın."
        )
    except (
        ValueError,
        OverflowError,
        TypeError,
        InvalidOperation,
        pl.exceptions.PolarsError,
    ) as error:
        raise ProjectError(
            "Filtre değeri fiziksel türe kayıpsız uymuyor. Türü/değeri kontrol edin."
        ) from error


def filtered(request, view):
    columns = request["columns"]
    view.validate(columns)
    schema = pl.read_parquet_schema(request["path"])
    names = {c["id"]: c["name"] for c in columns}
    query = pl.scan_parquet(request["path"])
    for item in view.filters:
        name = names[item["column_id"]]
        dt = schema[name]
        col = pl.col(name)
        op = item["operator"]
        if op == "is_null":
            predicate = col.is_null()
        elif op == "not_null":
            predicate = col.is_not_null()
        elif op in ("is_nan", "is_inf"):
            if not dt.is_float():
                raise ProjectError(
                    "NaN/infinity filtresi yalnız fiziksel float türündedir."
                )
            predicate = col.is_nan() if op == "is_nan" else col.is_infinite()
        elif op == "contains":
            if dt != pl.String:
                raise ProjectError("İçerir filtresi yalnız fiziksel metin türündedir.")
            predicate = col.str.contains(item["value"], literal=True)
        else:
            value = literal(item["value"], dt)
            predicate = {
                "eq": col.eq,
                "ne": col.ne,
                "gt": col.gt,
                "ge": col.ge,
                "lt": col.lt,
                "le": col.le,
            }[op](value)
            # Nonfinite values never enter ordinary finite numeric comparisons implicitly.
            if dt.is_float():
                predicate = predicate & col.is_finite()
        query = query.filter(predicate.fill_null(False))
    return query, schema, names


def display(value):
    if value is None:
        return "∅"
    if isinstance(value, bytes):
        return "0x" + value.hex()[:CELL_CHARS]
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "+∞" if value > 0 else "−∞"
    return str(value)[:CELL_CHARS]


def suggest_role(name, dtype, values):
    folded = name.casefold().replace("ı", "i")
    if re.search(
        r"(^|[_/ ])(id|kimlik|identifier|kod|numara)([_/ ]|$)", folded
    ) or folded.endswith("_id"):
        return (
            "identifier",
            "Alan adı kayıt kimliği/kodu izlenimi veriyor; kullanıcı onayı gerekir.",
        )
    if dtype.is_temporal():
        return "time", "Fiziksel tür tarih/zaman; saat dilimi değiştirilmez."
    if dtype == pl.String:
        texts = [v for v in values if isinstance(v, str) and v]
        if any(re.fullmatch(r"0\d+", v) for v in texts):
            return "identifier", "Başında sıfır olan kodlar var; metin türü korunur."
        if texts and (max(map(len, texts)) > 80 or len(set(texts)) > 20):
            return (
                "text",
                "Örnekte uzun veya çok farklı metinler var; örnek temsili garanti değil.",
            )
        return (
            "category",
            "Örnekte tekrar eden/kısa etiketler olabilir; tam kardinalite henüz ölçülmedi.",
        )
    if dtype == pl.Boolean:
        return "category", "İki fiziksel değer taşıyan boolean sütunu."
    if dtype.is_numeric():
        return (
            "measurement",
            "Sayısal fiziksel tür; kimlik veya kategori ise rolü düzeltin.",
        )
    return (
        "text",
        "Nested/binary değer; bu profil sürümünde sayısal ölçüm olarak kullanılmaz.",
    )


def page(request, view, offset=0, control=None):
    control = control or Control()
    checked(request, control)
    if type(offset) is not int or not 0 <= offset <= 10000000:
        raise ProjectError("Sayfa konumu sınır dışında.")
    query, schema, names = filtered(request, view)
    count = query.select(pl.len()).collect(engine="streaming").item()
    columns = [c for c in request["columns"] if c["id"] not in view.hidden]
    if view.sort_column:
        name = names[view.sort_column]
        if isinstance(schema[name], (pl.List, pl.Struct)) or schema[name] == pl.Binary:
            raise ProjectError("Nested/binary sıralama bu görünümde desteklenmiyor.")
        token = "__vu_view_order"
        while token in schema:
            token += "_"
        query = query.with_row_index(token).sort(
            [name, token, "__vu_row_id"],
            descending=[view.descending, False, False],
            nulls_last=True,
        )
    selected = [c["name"] for c in columns]
    frame = (
        query.select(selected + ["__vu_row_id", "__vu_source_record_id"])
        .slice(offset, PAGE_ROWS)
        .collect(engine="streaming")
    )
    rows = []
    payload_bytes = 0
    for row in range(frame.height):
        control.check()
        values = []
        for name in selected:
            dt = schema[name]
            if dt.is_temporal():
                value = frame[name].slice(row, 1).cast(pl.String)[0]
            elif isinstance(dt, (pl.List, pl.Struct)):
                value = str(frame[name].slice(row, 1))
            else:
                value = frame[name][row]
            text = display(value)
            if payload_bytes + len(text.encode("utf8")) > PAGE_BYTES:
                text = ""
            payload_bytes += len(text.encode("utf8"))
            values.append(text)
        rows.append(values)
    suggestions = {}
    advisory = (
        pl.scan_parquet(request["path"])
        .select([c["name"] for c in request["columns"]])
        .head(PAGE_ROWS)
        .collect(engine="streaming")
    )
    for c in request["columns"]:
        name = c["name"]
        dt = schema[name]
        values = (
            advisory[name].to_list()
            if name in advisory.columns
            and not dt.is_temporal()
            and not isinstance(dt, (pl.List, pl.Struct))
            else []
        )
        role, reason = suggest_role(name, dt, values)
        suggestions[c["id"]] = dict(role=role, reason=reason, physical_type=str(dt))
    checked(request, control)
    return dict(
        rows=rows,
        columns=columns,
        row_ids=frame["__vu_row_id"].to_list(),
        source_record_ids=frame["__vu_source_record_id"].to_list(),
        offset=offset,
        total=count,
        dataset_rows=request["row_count"],
        dataset_version=request["version_id"],
        view=view.data(),
        suggestions=suggestions,
        page_rows=PAGE_ROWS,
        cell_chars=CELL_CHARS,
        payload_bytes=payload_bytes,
        page_bytes_limit=PAGE_BYTES,
        display_truncation="Hücre metni en fazla256 karakter; toplam sayfa4MiB. Kırpılmış görünüm fiziksel veriyi değiştirmez.",
    )


def value_key(value):
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "+inf" if value > 0 else "-inf"
        return value.hex() if value else "0x0"
    if isinstance(value, Decimal):
        with localcontext() as ctx:
            ctx.prec = 80
            return str(value.normalize()) if value else "0"
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


def profile(request, spec, workspace, control=None):
    control = control or Control()
    checked(request, control)
    spec.validate(request["columns"])
    view = spec.view if spec.target == "view" else ViewSpec()
    query, schema, names = filtered(request, view)
    name = names[spec.column_id]
    dtype = schema[name]
    population = query.select(pl.len()).collect(engine="streaming").item()
    source = query.head(control.budget.sample_limit_rows) if spec.sample else query
    limit = (
        min(population, control.budget.sample_limit_rows) if spec.sample else population
    )
    role_data = request.get("semantic_metadata", {}).get(spec.column_id)
    nested = isinstance(dtype, (pl.List, pl.Struct))
    temporal = dtype.is_temporal()
    expression = pl.col(name).cast(pl.String) if temporal else pl.col(name)
    stream = source.select(expression.alias("value"))
    stats = dict(
        null=0, nan=0, positive_infinity=0, negative_infinity=0, valid=0, empty_string=0
    )
    original_values = []
    examples = []
    used = 0
    numeric = dtype.is_numeric()
    n = 0
    mean = Decimal(0)
    m2 = Decimal(0)
    minimum = maximum = None
    path = Path(workspace) / ("profile-" + uid() + ".sqlite")
    db = sqlite3.connect(path)
    db.execute("PRAGMA temp_store=FILE")
    db.execute("PRAGMA cache_size=-8192")
    db.create_collation(
        "exact_number",
        lambda a, b: (Decimal(a) > Decimal(b)) - (Decimal(a) < Decimal(b)),
    )
    db.execute(
        "CREATE TABLE frequencies (key TEXT PRIMARY KEY, value TEXT, number TEXT, count INTEGER NOT NULL, first_seen INTEGER NOT NULL)"
    )
    try:
        with localcontext() as ctx:
            ctx.prec = 80
            for batch in stream.collect_batches(
                chunk_size=4096, maintain_order=True, engine="streaming"
            ):
                control.check()
                records = []
                for i in range(batch.height):
                    used += 1
                    if used % 512 == 0:
                        control.check()
                    value = batch["value"][i]
                    if nested:
                        if value is None:
                            stats["null"] += 1
                        else:
                            stats["valid"] += 1
                            if len(examples) < 5:
                                examples.append(
                                    display(str(batch["value"].slice(i, 1)))
                                )
                        continue
                    if value is None:
                        stats["null"] += 1
                        continue
                    special = False
                    if isinstance(value, float) and not math.isfinite(value):
                        stats[
                            "nan"
                            if math.isnan(value)
                            else "positive_infinity"
                            if value > 0
                            else "negative_infinity"
                        ] += 1
                        special = True
                    else:
                        stats["valid"] += 1
                    if value == "":
                        stats["empty_string"] += 1
                    if used <= 200:
                        original_values.append(value)
                    if len(examples) < 5 and display(value) not in examples:
                        examples.append(display(value))
                    number = None
                    if numeric and not special:
                        exact = (
                            Decimal.from_float(value)
                            if isinstance(value, float)
                            else Decimal(value)
                        )
                        number = str(exact)
                        n += 1
                        delta = exact - mean
                        mean += delta / n
                        m2 += delta * (exact - mean)
                        minimum = exact if minimum is None else min(minimum, exact)
                        maximum = exact if maximum is None else max(maximum, exact)
                    records.append((value_key(value), display(value), number, used))
                db.executemany(
                    "INSERT INTO frequencies VALUES (?,?,?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1",
                    records,
                )
                db.commit()
                control.disk(workspace)
                control.progress("Sütun profilini tarama", used, limit)
            proposal, reason = suggest_role(name, dtype, original_values)
            role = role_data["role"] if role_data else proposal
            unique = (
                None
                if nested
                else db.execute("SELECT count(*) FROM frequencies").fetchone()[0]
            )
            top = (
                []
                if nested
                else [
                    dict(value=value, count=count)
                    for value, count in db.execute(
                        "SELECT value,count FROM frequencies ORDER BY count DESC,first_seen LIMIT ?",
                        (TOP_VALUES,),
                    )
                ]
            )
            quantiles = {}
            median = None
            std = None
            average = None
            if numeric and role == "measurement" and n:
                positions = {q: Decimal(n - 1) * q for q in QUANTILES}
                needed = {int(p) for p in positions.values()} | {
                    min(n - 1, int(p) + 1) for p in positions.values()
                }
                values = {}
                index = 0
                for number, count in db.execute(
                    "SELECT number,count FROM frequencies WHERE number IS NOT NULL ORDER BY number COLLATE exact_number"
                ):
                    control.check()
                    for rank in needed:
                        if index <= rank < index + count:
                            values[rank] = Decimal(number)
                    index += count
                    if index > max(needed):
                        break
                for q, p in positions.items():
                    low = int(p)
                    high = min(n - 1, low + 1)
                    quantiles[str(q)] = str(
                        values[low] + (values[high] - values[low]) * (p - low)
                    )
                median = quantiles["0.5"]
                average = str(mean)
                if n > spec.ddof:
                    std = str(max(Decimal(0), m2 / (n - spec.ddof)).sqrt())
            date_range = None
            if temporal and stats["valid"]:
                frame = source.select(
                    pl.col(name).min().cast(pl.String).alias("minimum"),
                    pl.col(name).max().cast(pl.String).alias("maximum"),
                ).collect(engine="streaming")
                date_range = dict(
                    minimum=frame["minimum"][0], maximum=frame["maximum"][0]
                )
        checked(request, control)
        scope = (
            "sample"
            if spec.sample and used < population
            else "filtered"
            if view.filters
            else "full"
        )
        parameters = dict(
            column_id=spec.column_id,
            target=spec.target,
            sample=spec.sample,
            ddof=spec.ddof,
            filters=list(view.filters),
            role=role,
        )
        provenance = Provenance(
            provenance_id="prov:" + uid(),
            dataset_versions=(request["version_id"],),
            config_revision=request.get("config_revision", 0),
            capability_id="dataset.profile",
            parameters_hash=digest(encode(parameters)),
            environment=(
                ("polars", pl.__version__),
                ("arithmetic", "Decimal precision80"),
            ),
            created_at=datetime.now(UTC).isoformat(),
            scope=scope,
            seed=None,
            seed_reason="İlk N kayıt örneği; rastgele örnekleme yok"
            if spec.sample
            else "Tam tarama; örnekleme yok",
            source_snapshot_ids=(request["source_snapshot_id"],),
            row_lineage_ref=request["snapshot_uri"],
            column_lineage_ref=spec.column_id,
            learning_content_version="6",
            filters=tuple(encode(f).decode("utf8") for f in view.filters),
            exclusions=("null", "NaN", "+infinity", "-infinity"),
        )
        return dict(
            dataset_version=request["version_id"],
            column_id=spec.column_id,
            column_name=name,
            physical_type=str(dtype),
            role=role,
            role_proposal=proposal,
            role_reason=reason,
            scope=scope,
            parent_scope="filtered" if view.filters else "full",
            target=spec.target,
            filters=list(view.filters),
            population_n=population,
            dataset_rows=request["row_count"],
            used_n=used,
            column_count=len(request["columns"]),
            sampling_method="first_in_immutable_input_order"
            if spec.sample and used < population
            else "none",
            representative_sample=False if scope == "sample" else None,
            counts=stats,
            null_rate=stats["null"] / used if used else None,
            unique=unique,
            unique_method="exact non-null; NaN collapsed; +/-inf separate; -0=+0"
            if not nested
            else "unsupported nested exact unique",
            examples=examples,
            frequencies=top,
            frequency_other_count=used - stats["null"] - sum(t["count"] for t in top)
            if not nested
            else None,
            numeric=dict(
                minimum=str(minimum) if minimum is not None else None,
                maximum=str(maximum) if maximum is not None else None,
                mean=average,
                median=median,
                std=std,
                quantiles=quantiles,
                finite_n=n,
                ddof=spec.ddof,
                quantile_method="linear h=(n-1)*q",
                exclusions="null, NaN, +infinity, -infinity",
                arithmetic="Decimal precision80; sqrt rounded half-even",
                suppressed=role != "measurement",
            ),
            date_range=date_range,
            warnings=(
                [
                    "Nested list/struct: exact unique/frekans/sayısal profil desteklenmiyor; fiziksel tür ve null sayımı korunur."
                ]
                if nested
                else []
            )
            + (
                [
                    "Kimlik/kategori/metin rolünde ortalama, std, yüzdelik ve korelasyon bulgusu üretilmez."
                ]
                if role != "measurement"
                else []
            )
            + (
                [
                    "Örnek ilk N kayıttır; unique/frekanslar örnek içinde kesin, tüm veriye genellenmez."
                ]
                if scope == "sample"
                else []
            ),
            provenance=asdict(provenance),
            snapshot_fingerprint=request["fingerprint"],
        )
    finally:
        db.close()
        path.unlink(missing_ok=True)
