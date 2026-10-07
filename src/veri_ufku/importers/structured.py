"""JSON/JSONL and structured row pipeline: explicit transforms, bounded publication."""

import copy
import itertools
import json
import math
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import polars as pl

from veri_ufku.importers.delimited import (
    MAX_RECORD,
    PREVIEW_ROWS,
    Control,
    dtype,
    hash_artifact,
    headers,
    verify_capture,
)
from veri_ufku.importers.native import (
    EXTRA,
    RESERVED,
    TypeProfile,
    canonical,
    describe,
    native_value,
    selected_value,
)
from veri_ufku.storage.project_model import ProjectError, uid

MAX_JSON = 64 * 1024**2


def pointer_parts(path):
    if path == "":
        return []
    if not path.startswith("/") or any(
        "~" in p.replace("~0", "").replace("~1", "") for p in path.split("/")[1:]
    ):
        raise ProjectError(
            "Kayıt/liste yolu JSON Pointer olmalı: /veri/kayitlar; ~1 slash, ~0 tilde."
        )
    return [p.replace("~1", "/").replace("~0", "~") for p in path.split("/")[1:]]


def escaped(value):
    return value.replace("~", "~0").replace("/", "~1")


def select(root, path):
    value = root
    for key in pointer_parts(path):
        if isinstance(value, dict) and key in value:
            value = value[key]
        elif isinstance(value, list) and key.isdecimal() and int(key) < len(value):
            value = value[int(key)]
        else:
            raise ProjectError(
                "JSON kayıt/liste yolu bulunamadı; önizlemedeki yolları kontrol edin."
            )
    return value


def parse_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ProjectError(
                    "JSON nesnesinde tekrar eden alan adı; sessiz üstüne yazma yapılmadı."
                )
            if len(key) > 4096:
                raise ProjectError("JSON alan adı4096 karakter sınırını aşıyor.")
            result[key] = value
        return result

    def constant(value):
        raise ProjectError(
            "JSON NaN/Infinity standart JSON değildir; değer değiştirilmedi."
        )

    try:
        return json.loads(
            text, parse_float=Decimal, object_pairs_hook=pairs, parse_constant=constant
        )
    except json.JSONDecodeError as error:
        raise ProjectError(
            f"JSON yapısı bozuk: satır {error.lineno}, sütun {error.colno}."
        ) from error
    except (RecursionError, ValueError) as error:
        if isinstance(error, ProjectError):
            raise
        raise ProjectError("JSON sayı/derinlik destek sınırı dışında.") from error


def bounded_shape(value, control, depth=0):
    control.check()
    if depth > 16:
        raise ProjectError("JSON nested derinliği16 sınırını aşıyor.")
    if isinstance(value, dict):
        if any(len(k) > 4096 for k in value):
            raise ProjectError("JSON alan adı 4096 karakter sınırını aşıyor.")
        if len(value) > 256:
            raise ProjectError("JSON nesnesi256 alan sınırını aşıyor.")
        for v in value.values():
            bounded_shape(v, control, depth + 1)
    elif isinstance(value, list):
        for v in value:
            bounded_shape(v, control, depth + 1)


def json_document(snapshot, control):
    if snapshot["fingerprint"]["size"] > MAX_JSON:
        raise ProjectError(
            "JSON belge sınırı64 MiB; büyük kayıtlar için JSONL/NDJSON kullanın."
        )
    control.check()
    try:
        with open(snapshot["path"], encoding="utf-8-sig", errors="strict") as stream:
            value = parse_json(stream.read(MAX_JSON + 1))
    except UnicodeDecodeError as error:
        raise ProjectError("JSON UTF-8 olarak okunamadı.") from error
    bounded_shape(value, control)
    return value


def record_paths(value, path="", depth=0):
    result = []
    if isinstance(value, list) and (
        not value or all(isinstance(v, dict) for v in value[:200])
    ):
        result.append(path)
    if isinstance(value, dict) and depth < 16:
        for key, child in value.items():
            result.extend(record_paths(child, path + "/" + escaped(key), depth + 1))
    return result[:256]


def list_paths(value, path="", depth=0):
    result = []
    if isinstance(value, list):
        result.append(path)
    if isinstance(value, dict) and depth < 16:
        for key, child in value.items():
            result.extend(list_paths(child, path + "/" + escaped(key), depth + 1))
    return result[:256]


def json_records(snapshot, settings, control):
    if settings.adapter_id == "json":
        document = json_document(snapshot, control)
        records = select(document, settings.record_path)
        if not isinstance(records, list):
            raise ProjectError(
                "Seçilen JSON yolu kayıt listesi değil. Kayıt yolu seçin; kök liste için boş bırakın."
            )
        for i, value in enumerate(records):
            control.check()
            raw = canonical(value)
            if len(raw.encode()) > MAX_RECORD:
                raise ProjectError("JSON kaydı1 MiB sınırını aşıyor.")
            yield dict(
                ordinal=i + 1,
                start=0,
                end=0,
                locator=settings.record_path + "/" + str(i),
                values=value,
                raw=raw,
                reason=None,
            )
        return
    try:
        with open(
            snapshot["path"], encoding="utf-8-sig", errors="strict", newline=""
        ) as stream:
            ordinal = 0
            while line := stream.readline(MAX_RECORD + 1):
                control.check()
                ordinal += 1
                if len(line.encode()) > MAX_RECORD:
                    raise ProjectError(f"JSONL satır {ordinal}:1 MiB sınırı aşıldı.")
                try:
                    value = parse_json(line)
                    bounded_shape(value, control)
                    reason = None
                except ProjectError as error:
                    value = None
                    reason = str(error)
                yield dict(
                    ordinal=ordinal,
                    start=ordinal,
                    end=ordinal,
                    locator=f"line:{ordinal}",
                    values=value,
                    raw=line,
                    reason=reason,
                )
    except UnicodeDecodeError as error:
        raise ProjectError(
            "JSONL UTF-8 olarak okunamadı; encoding değiştirilmedi."
        ) from error


def flatten(value, path=""):
    result = {}
    for key, child in value.items():
        field = path + "/" + escaped(key)
        if isinstance(child, dict) and child:
            result.update(flatten(child, field))
        else:
            result[field] = child
    if len(result) > 256:
        raise ProjectError("Düzleştirme256 sütun sınırını aşıyor.")
    return result


def transformed(records, settings, control):
    for record in records:
        control.check()
        value = record["values"]
        if record["reason"] or not isinstance(value, dict):
            yield dict(
                record,
                reason=record["reason"] or "Kayıt JSON nesnesi değil.",
                expansion="{}",
            )
            continue
        arrays = []
        for path in settings.expand_lists:
            parent = value
            for part in pointer_parts(path)[:-1]:
                if not isinstance(parent, dict):
                    break
                parent = parent.get(part, {})
            if not isinstance(parent, dict):
                yield dict(
                    record,
                    reason="Liste açma yolu ara listeden geçiyor; önce üst listeyi açın.",
                    expansion="{}",
                )
                break
            try:
                array = select(value, path)
            except ProjectError:
                array = None
            if array is None:
                arrays.append([(None, None)])
            elif not isinstance(array, list):
                yield dict(
                    record, reason=f"Seçilen alan liste değil: {path}", expansion="{}"
                )
                break
            else:
                arrays.append(list(enumerate(array)) or [(None, None)])
        else:
            count = math.prod(len(a) for a in arrays)
            if count > 100000:
                raise ProjectError(
                    f"Tek kayıtta liste açma {count} satır üretiyor; sınır100000. Kartesyen çoğalmayı azaltın."
                )
            for combination in itertools.product(*arrays):
                control.check()
                expanded = copy.deepcopy(value)
                coordinates = {}
                for path, (index, element) in zip(
                    settings.expand_lists, combination, strict=True
                ):
                    coordinates[path] = index
                    if index is None and element is None:
                        try:
                            select(value, path)
                        except ProjectError:
                            continue
                    parts = pointer_parts(path)
                    parent = expanded
                    for key in parts[:-1]:
                        if not isinstance(parent, dict) or key not in parent:
                            break
                        parent = parent[key]
                    else:
                        if isinstance(parent, dict):
                            parent[parts[-1]] = element
                yield dict(
                    record,
                    values=flatten(expanded) if settings.flatten else expanded,
                    expansion=canonical(coordinates),
                )


def rows_for(snapshot, settings, control):
    if settings.adapter_id in ("json", "jsonl"):
        return transformed(json_records(snapshot, settings, control), settings, control)
    if settings.adapter_id == "ods":
        from veri_ufku.importers.ods import records

        return records(snapshot, settings, control)
    if settings.adapter_id == "sqlite":
        from veri_ufku.importers.sqlite_source import records

        return records(snapshot, settings, control)
    from veri_ufku.importers.xlsx import excel_records

    return excel_records(snapshot, settings, control)


def profile(snapshot, settings, control, limited=False):
    profiles = {}
    nodes = [0]
    bad = []
    row_count = 0
    source_count = 0
    last = None
    max_expansion = 0
    per_record = 0
    sample = []
    bad_count = 0
    excel_originals = None
    for record in rows_for(snapshot, settings, control):
        if record["ordinal"] != last:
            if limited and source_count >= PREVIEW_ROWS:
                break
            max_expansion = max(max_expansion, per_record)
            per_record = 0
            source_count += 1
            last = record["ordinal"]
        per_record += 1
        if record.get("original_headers") is not None:
            excel_originals = record["original_headers"]
        if record["reason"]:
            bad_count += 1
            if settings.bad_rows == "stop" and not limited:
                raise ProjectError(
                    f"Bozuk kayıt {record['locator']}: {record['reason']}"
                )
            if len(bad) < 200:
                bad.append(record)
            if len(bad) > 10000 and limited:
                raise ProjectError("Önizleme hata sınırı aşıldı.")
            continue
        row_count += 1
        for name, value in record["values"].items():
            if name not in profiles and len(profiles) >= 256:
                raise ProjectError("Alan birleşimi256 sütun sınırını aşıyor.")
            if name not in profiles:
                profiles[name] = TypeProfile(nodes)
            profiles[name].add(value)
        if limited and len(sample) < PREVIEW_ROWS:
            sample.append(record)
        if row_count % 4096 == 0:
            control.progress("Alan/tür doğrulama", row_count, None)
    max_expansion = max(max_expansion, per_record)
    if not profiles:
        raise ProjectError(
            f"Veri alanı yok; {bad_count} bozuk kayıt. Dataset oluşturulmadı."
        )
    # XLSX physical column order is meaningful; JSON key order is never used.
    originals = (
        list(profiles)
        if settings.adapter_id in ("xlsx", "ods", "sqlite")
        else sorted(profiles)
    )
    if (
        settings.types
        and settings.column_names
        and tuple(originals) != settings.column_names
    ):
        raise ProjectError(
            "Tam okuma sütunları önizlemeden farklı. Türleri Otomatik seçerek yeniden önizleyin; indeksler sessizce eşlenmedi."
        )
    if settings.types and len(settings.types) != len(originals):
        raise ProjectError("Sütun sayısı değişti; tür seçimlerini sıfırlayın.")
    names, warnings = headers(originals)
    # Reserve all additional lineage names as well.
    used = set(RESERVED)
    for i, name in enumerate(names):
        base = name
        suffix = 2
        while name in used:
            name = f"{base}_{suffix}"
            suffix += 1
        names[i] = name
        used.add(name)
    dtypes = []
    blocked = False
    type_names = []
    from veri_ufku.importers.delimited import ImportSettings

    for i, name in enumerate(originals):
        kind = settings.types[i] if settings.types else "auto"
        if kind == "float64":
            warnings.append(
                f"{name}: açık Float64 seçimi yaklaşık ikili sayıdır; Decimal için kesinlik tercih edin. Tam import 2^53 üstü integer/underflow/taşmayı reddeder."
            )
        if kind == "auto":
            dt, needs = profiles[name].resolve(settings.mixed_policy)
        else:
            dt, needs = dtype(kind, ImportSettings(timezone=settings.timezone)), False
        dtypes.append(dt)
        blocked |= needs
        type_names.append(str(dt))
    reports = {name: profiles[name].report(row_count) for name in originals}
    mixed = [
        n
        for n, p in profiles.items()
        if len(p.kinds) > 1 and not p.kinds <= {"integer", "decimal"}
    ]
    if mixed:
        warnings.append(
            "Karışık türler: "
            + ", ".join(mixed)
            + ". Otomatik dönüşüm yerine tür veya JSON metni politikasını seçin."
        )
    if blocked:
        warnings.append(
            "Tür/hassasiyet destek sınırı: açık JSON metni dönüşümü veya sütun türü seçin."
        )
    if settings.expand_lists:
        warnings.append(
            f"Liste açma: {source_count} kaynak kaydı → {row_count} satır; tek kayıtta en fazla {max_expansion}. Farklı listeler birlikte açılırsa kartesyen çoğalma oluşur; boş/null listeler bir satır korunur."
        )
    schema = dict(
        names=names,
        original_headers=excel_originals or originals,
        input_names=originals,
        types=type_names,
        warnings=warnings,
    )
    report = dict(
        fields=reports,
        source_records=source_count,
        output_rows=row_count,
        bad_count=bad_count,
        max_expansion=max_expansion,
        scope="sample" if limited else "full",
    )
    return schema, profiles, dtypes, sample, bad, report, blocked


def values_for(record, schema, profiles, dtypes, settings):
    result = []
    for i, name in enumerate(schema.get("input_names", schema["original_headers"])):
        value = record["values"].get(name)
        kind = settings.types[i] if settings.types else "auto"
        try:
            result.append(
                native_value(value, dtypes[i], profiles[name])
                if kind == "auto"
                else selected_value(value, kind, settings)
            )
        except (ValueError, OverflowError, TypeError) as error:
            raise ProjectError(
                f"Sütun {i + 1} seçilen türe/hassasiyete dönüştürülemedi."
            ) from error
    return result


def preview_structured(snapshot, settings, control=None):
    control = control or Control()
    verify_capture(snapshot, control)
    schema, profiles, dtypes, sample, bad, report, blocked = profile(
        snapshot, settings, control, True
    )
    rows = []
    for record in sample:
        # Preview shows the original typed values; conversion failure remains explicit.
        try:
            vals = values_for(record, schema, profiles, dtypes, settings)
        except ProjectError as error:
            bad.append(dict(record, reason=str(error)))
            report["bad_count"] += 1
            continue
        rows.append(
            [
                "∅"
                if v is None
                else canonical(v)
                if isinstance(v, (dict, list))
                else str(v)
                for v in vals
            ]
        )
    verify_capture(snapshot, control)
    lines = []

    def summarize(fields, prefix="", depth=0):
        for name, stats in fields.items():
            if len(lines) >= 40:
                return
            path = prefix + name
            lines.append(
                f"{path}: {', '.join(stats['observed_types']) or 'yalnız null'} · eksik {stats['missing']} · açık null {stats['explicit_null']}"
            )
            if depth < 4:
                summarize(stats["fields"], path + "/", depth + 1)
            if stats.get("item") and len(lines) < 40:
                item = stats["item"]
                lines.append(
                    f"{path} liste elemanları: {', '.join(item['observed_types']) or 'yalnız null'} · açık null {item['explicit_null']}"
                )

    summarize(report["fields"])
    diagnostics = (
        "Alan raporu (sınırlı örnek):\n"
        + "\n".join(lines)
        + "\nTam import raporu proje işlem kaydında saklanır."
    )
    schema["warnings"].append(diagnostics)
    return dict(
        schema=schema,
        rows=rows,
        bad=[
            dict(
                record_number=b["ordinal"],
                start_line=b["start"],
                end_line=b["end"],
                reason=b["reason"],
                locator=b["locator"],
            )
            for b in bad[:200]
        ],
        examined=report["source_records"],
        limited=report["source_records"] >= 200,
        suggestions=schema["types"],
        settings=settings.data(),
        capture=snapshot,
        diagnostics=report,
        importable=not blocked and (not bad or settings.bad_rows == "quarantine"),
    )


def import_structured(snapshot, settings, workspace, control=None):
    control = control or Control()
    verify_capture(snapshot, control)
    schema, profiles, dtypes, _, _, report, blocked = profile(
        snapshot, settings, control
    )
    if blocked:
        raise ProjectError(
            "Karışık tür/hassasiyet için açık tür veya JSON metni dönüşümü seçin; dataset yayımlanmadı."
        )
    parts = []
    bad_parts = []
    rows = []
    rejected = []
    chunk_bytes = 0
    accepted = bad_count = 0
    last = None
    source_id = None
    all_schema = dict(zip(schema["names"], dtypes, strict=True))
    all_schema.update(
        {
            "__vu_row_id": pl.String,
            "__vu_source_record_id": pl.String,
            "__vu_start_line": pl.Int64,
            "__vu_end_line": pl.Int64,
            **EXTRA,
        }
    )

    def flush():
        nonlocal rows, rejected
        control.check()
        if rows:
            path = Path(workspace) / (uid() + ".part.parquet")
            pl.DataFrame(rows, schema=all_schema, orient="row").write_parquet(path)
            parts.append(path)
            rows = []
        if rejected:
            path = Path(workspace) / (uid() + ".bad.parquet")
            pl.DataFrame(
                rejected,
                schema={
                    "source_record_id": pl.String,
                    "record_number": pl.Int64,
                    "start_line": pl.Int64,
                    "end_line": pl.Int64,
                    "locator": pl.String,
                    "raw": pl.String,
                    "reason": pl.String,
                },
            ).write_parquet(path)
            bad_parts.append(path)
            rejected = []
        if len(parts) + len(bad_parts) > 16384:
            raise ProjectError("Parça bütçesi aşıldı.")
        control.disk(workspace)

    for record in rows_for(snapshot, settings, control):
        if last != record["ordinal"]:
            last = record["ordinal"]
            source_id = "sr:" + uid()
        reason = record["reason"]
        if not reason:
            try:
                values = values_for(record, schema, profiles, dtypes, settings)
            except ProjectError as error:
                reason = str(error)
        if reason:
            if settings.bad_rows == "stop":
                raise ProjectError(f"Bozuk kayıt {record['locator']}: {reason}")
            bad_count += 1
            rejected.append(
                dict(
                    source_record_id=source_id,
                    record_number=record["ordinal"],
                    start_line=record["start"],
                    end_line=record["end"],
                    locator=record["locator"],
                    raw=record["raw"],
                    reason=reason,
                )
            )
        else:
            accepted += 1
            missing = [
                n
                for n in schema.get("input_names", schema["original_headers"])
                if n not in record["values"]
            ]
            rows.append(
                values
                + [
                    "row:" + uid(),
                    source_id,
                    record["start"],
                    record["end"],
                    record["locator"],
                    missing,
                    record.get("expansion", "{}"),
                ]
            )
        chunk_bytes += len(record["raw"].encode())
        if len(rows) + len(rejected) >= 4096 or chunk_bytes >= 8 * 1024**2:
            flush()
            chunk_bytes = 0
            control.progress("Kayıt dönüştürme", accepted + bad_count, None)
    flush()
    if not accepted:
        raise ProjectError(
            f"Geçerli kayıt yok; bozuk {bad_count}. Dataset oluşturulmadı."
        )
    output = Path(workspace) / (uid() + ".dataset.parquet")
    pl.concat([pl.scan_parquet(p) for p in parts]).sink_parquet(
        output, engine="streaming"
    )
    control.check()
    quarantine = None
    if bad_parts:
        quarantine = Path(workspace) / (uid() + ".quarantine.parquet")
        pl.concat([pl.scan_parquet(p) for p in bad_parts]).sink_parquet(
            quarantine, engine="streaming"
        )
    actual = pl.read_parquet_schema(output)
    if actual != all_schema:
        raise ProjectError(
            "Native türler Parquet yazımında değişti; sonuç yayımlanmadı."
        )
    saved = replace(
        settings, native_schema={n: describe(t) for n, t in all_schema.items()}
    )
    verify_capture(snapshot, control)
    control.disk(workspace)
    report.update(
        accepted_rows=accepted, quarantined_rows=bad_count, bad_count=bad_count
    )
    return dict(
        path=str(output),
        quarantine=str(quarantine) if quarantine else None,
        artifact_fingerprint=hash_artifact(output, control),
        quarantine_fingerprint=hash_artifact(quarantine, control)
        if quarantine
        else None,
        schema=schema,
        accepted=accepted,
        bad_count=bad_count,
        examined=report["source_records"],
        source_snapshot_id="snapshot:" + uid(),
        settings=saved.data(),
        capture=snapshot,
        adapter_id=settings.adapter_id,
        diagnostics=report,
        backend="python-json/polars"
        if settings.adapter_id in ("json", "jsonl")
        else "bounded-ooxml/polars",
    )
