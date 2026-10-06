"""Bounded CSV/TSV capture, common preview/import parser and typed conversion."""

import codecs
import csv
import hashlib
import math
import re
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import polars as pl

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError, uid

TYPES = ("text", "int64", "float64", "decimal", "date", "datetime", "boolean")
ENCODINGS = ("utf-8-sig", "cp1254", "iso8859-9")
INTERNAL = ("__vu_row_id", "__vu_source_record_id", "__vu_start_line", "__vu_end_line")
MAX_RECORD = 1024 * 1024
MAX_COLUMNS = 256
PREVIEW_ROWS = 200


@dataclass(frozen=True)
class ImportSettings:
    delimiter: str = ","
    encoding: str = "utf-8-sig"
    header_row: int = 1
    decimal: str = "."
    thousands: str = ""
    null_markers: tuple[str, ...] = ()
    date_format: str = "%Y-%m-%d"
    timezone: str = ""
    bad_rows: str = "stop"
    types: tuple[str, ...] = ()

    def __post_init__(self):
        if (
            self.delimiter not in (",", ";", "\t", "|")
            or self.encoding not in ENCODINGS
        ):
            raise ProjectError("Ayraç veya encoding desteklenmiyor.")
        if type(self.header_row) is not int or not 0 <= self.header_row <= 100:
            raise ProjectError("Başlık kaydı 0 (başlıksız) veya 1–100 olmalı.")
        if (
            self.decimal not in (".", ",")
            or self.thousands not in ("", ".", ",", " ")
            or self.decimal == self.thousands
        ):
            raise ProjectError("Ondalık ve binlik ayracı farklı olmalı.")
        if (
            self.bad_rows not in ("stop", "quarantine")
            or len(self.types) > MAX_COLUMNS
            or any(t not in TYPES for t in self.types)
        ):
            raise ProjectError("Tür veya bozuk kayıt politikası geçersiz.")
        if len(self.null_markers) > 30 or any(
            not isinstance(n, str) or len(n) > 100 for n in self.null_markers
        ):
            raise ProjectError("Null işaretleri sınır dışında.")
        if (
            not isinstance(self.date_format, str)
            or not 1 <= len(self.date_format) <= 100
        ):
            raise ProjectError("Tarih biçimi geçersiz.")
        if self.timezone:
            try:
                ZoneInfo(self.timezone)
            except (ZoneInfoNotFoundError, ValueError) as error:
                raise ProjectError(
                    "Saat dilimi bulunamadı. Örneğin Europe/Istanbul seçin."
                ) from error

    @classmethod
    def from_dict(cls, value):
        value = dict(value)
        value["null_markers"] = tuple(value.get("null_markers", ()))
        value["types"] = tuple(value.get("types", ()))
        try:
            return cls(**value)
        except TypeError as error:
            raise ProjectError("İçe aktarma ayar alanları geçersiz.") from error


class Control:
    def __init__(
        self,
        cancel=None,
        progress=lambda phase, done, total: None,
        budget=ComputeBudget(),
    ):
        self.cancel, self.progress, self.budget = cancel, progress, budget
        self.started = time.monotonic()

    def check(self):
        if self.cancel and self.cancel.is_set():
            raise Canceled()
        if time.monotonic() - self.started > self.budget.max_wall_seconds:
            raise ProjectError("İçe aktarma süre bütçesini aştı.")

    def disk(self, path):
        self.check()
        used = sum(p.stat().st_size for p in Path(path).glob("*") if p.is_file())
        if (
            used > self.budget.temp_disk_bytes
            or shutil.disk_usage(path).free < self.budget.reserve_disk_bytes
        ):
            raise ProjectError(
                "İçe aktarma geçici disk bütçesi aşıldı veya boş alan yetersiz."
            )


def capture(
    source, workspace, control=None, checkpoint=lambda step: None, *, any_format=False
):
    control = control or Control()
    source = Path(source).resolve(strict=True)
    if (
        not any_format and source.suffix.lower() not in {".csv", ".tsv"}
    ) or not source.is_file():
        raise ProjectError("Yalnız yerel CSV/TSV dosyası seçin.")
    before = source.stat()
    if before.st_size > min(1024**3, control.budget.temp_disk_bytes // 4):
        raise ProjectError(
            "Bu sürümde kaynak en fazla 1 GiB ve geçici disk bütçesinin dörtte biri olabilir."
        )
    destination = Path(workspace) / (uid() + ".source")
    h = hashlib.sha256()
    with open(source, "rb") as original, open(destination, "xb") as copied:
        while chunk := original.read(1024 * 1024):
            control.check()
            copied.write(chunk)
            h.update(chunk)
            control.progress("Kaynak kopyası", copied.tell(), before.st_size)
            control.disk(workspace)
            checkpoint("copy_chunk")
    second = hashlib.sha256()
    with open(source, "rb") as original:
        while chunk := original.read(1024 * 1024):
            control.check()
            second.update(chunk)
    after = source.stat()

    def identity(s):
        return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

    if (
        h.digest() != second.digest()
        or identity(before) != identity(after)
        or source.stat().st_size != destination.stat().st_size
    ):
        raise ProjectError(
            "Kaynak kopyalama sırasında değişti. Yazmayı durdurup yeniden önizleyin."
        )
    return dict(
        path=str(destination),
        original=str(source),
        fingerprint=dict(sha256=h.hexdigest(), size=before.st_size),
        captured_at=datetime.now(UTC).isoformat(),
        capture_id=uid(),
    )


def suggest(snapshot):
    raw = (
        Path(snapshot["path"]).read_bytes()[:65536]
        if snapshot["fingerprint"]["size"] <= 65536
        else open_sample(snapshot["path"])
    )
    encoding = "utf-8-sig"
    try:
        sample = codecs.getincrementaldecoder(encoding)().decode(raw, final=False)
    except UnicodeDecodeError:
        encoding = "cp1254"
        try:
            sample = codecs.getincrementaldecoder(encoding)().decode(raw, final=False)
        except UnicodeDecodeError as error:
            raise ProjectError(
                "Encoding algılanamadı. Dosyanın UTF-8 veya Türkçe eski encoding ile kaydedildiğini kontrol edin."
            ) from error
    delimiter = "\t" if snapshot["original"].lower().endswith(".tsv") else ","
    header = 1
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        header = 1 if csv.Sniffer().has_header(sample) else 0
    except csv.Error:
        pass
    return ImportSettings(
        delimiter=delimiter,
        encoding=encoding,
        header_row=header,
        decimal="," if delimiter == ";" else ".",
    )


def open_sample(path):
    with open(path, "rb") as stream:
        return stream.read(65536)


class Lines:
    def __init__(self, stream, control):
        self.stream, self.control = stream, control
        self.parts, self.size = [], 0

    def __iter__(self):
        return self

    def __next__(self):
        self.control.check()
        line = self.stream.readline(MAX_RECORD + 1)
        if not line:
            raise StopIteration
        self.size += len(line.encode("utf8"))
        if self.size > MAX_RECORD:
            raise ProjectError(
                "Tek bir CSV kaydı 1 MiB sınırını aştı; güvenli biçimde durduruldu."
            )
        self.parts.append(line)
        return line

    def reset(self):
        self.parts, self.size = [], 0


def records(snapshot, settings, control):
    csv.field_size_limit(MAX_RECORD)
    try:
        with open(
            snapshot["path"], encoding=settings.encoding, errors="strict", newline=""
        ) as stream:
            lines = Lines(stream, control)
            reader = csv.reader(lines, delimiter=settings.delimiter, strict=True)
            ordinal = 0
            while True:
                start = reader.line_num + 1
                lines.reset()
                try:
                    row = next(reader)
                    reason = None
                except StopIteration:
                    break
                except csv.Error:
                    row, reason = (
                        None,
                        "Tırnak/CSV yapısı bozuk; bu kaynak aralığı güvenle ayrıştırılamadı.",
                    )
                ordinal += 1
                if row is not None and len(row) > MAX_COLUMNS:
                    raise ProjectError("Dosya 256 sütun sınırını aştı.")
                yield ordinal, start, reader.line_num, row, "".join(lines.parts), reason
    except UnicodeDecodeError as error:
        raise ProjectError(
            "Dosya seçilen encoding ile okunamadı. Encoding'i düzeltip yeniden önizleyin; hiçbir kayıt sessizce atlanmadı."
        ) from error


def headers(row):
    if not row:
        raise ProjectError("Boş dosya veya boş başlık kaydı. Ayarları kontrol edin.")
    names, warnings, used = [], [], set(INTERNAL)
    for index, original in enumerate(row):
        base = original.strip() or f"Sütun_{index + 1}"
        name, suffix = base, 2
        while name in used:
            name = f"{base}_{suffix}"
            suffix += 1
        if name != original:
            warnings.append(f"Başlık {index + 1}: {original!r} → {name!r}")
        used.add(name)
        names.append(name)
    return names, warnings


def number(value, settings):
    text = value.strip()
    if settings.thousands:
        integer = text.split(settings.decimal)[0].lstrip("+-")
        if settings.thousands in text:
            groups = integer.split(settings.thousands)
            if (
                not re.fullmatch(r"\d{1,3}", groups[0])
                or any(not re.fullmatch(r"\d{3}", g) for g in groups[1:])
                or settings.thousands in text[len(text.split(settings.decimal)[0]) :]
            ):
                raise ValueError("Binlik gruplama geçersiz.")
        text = text.replace(settings.thousands, "")
    text = text.replace(settings.decimal, ".")
    if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", text):
        raise ValueError("Sayı biçimi geçersiz.")
    if re.match(r"[+-]?0\d", text):
        raise ValueError("Baştaki sıfırlar kaybolabilir; metin türünü seçin.")
    return Decimal(text)


def convert(value, kind, settings):
    if value in settings.null_markers:
        return None
    if kind == "text":
        return value
    if kind in {"int64", "float64", "decimal"}:
        n = number(value, settings)
        if kind == "int64":
            if n != n.to_integral_value() or not -(2**63) <= n < 2**63:
                raise ValueError("Tam sayı Int64 sınırı veya kesir kaybı.")
            return int(n)
        if kind == "float64":
            if n == n.to_integral_value() and n.copy_abs() > 2**53:
                raise ValueError(
                    "Uzun numara Float64 dönüşümünde bilgi kaybedebilir; metin/Int64 seçin."
                )
            value = float(n)
            if value == 0.0 and n != 0:
                raise ValueError("Float64 alt sınırı bilgi kaybı; metin/Decimal seçin.")
            if not math.isfinite(value):
                raise ValueError("Sonlu sayı gerekli.")
            return value
        if n.as_tuple().exponent < -6 or n.copy_abs() >= Decimal("1e32"):
            raise ValueError("Decimal(38,6) hassasiyet sınırı; yuvarlama yapılmadı.")
        return n
    if kind in {"date", "datetime"}:
        value = datetime.strptime(value, settings.date_format)
        if kind == "date":
            return value.date()
        if value.tzinfo:
            raise ValueError("Biçimde timezone offset yerine ayrı saat dilimi seçin.")
        if not settings.timezone:
            return value
        zone = ZoneInfo(settings.timezone)
        first, second = (
            value.replace(tzinfo=zone, fold=0),
            value.replace(tzinfo=zone, fold=1),
        )
        if (
            first.utcoffset() != second.utcoffset()
            or first.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != value
        ):
            raise ValueError("Saat diliminde belirsiz veya bulunmayan saat.")
        return first
    if kind == "boolean":
        if value.casefold() in {"true", "false", "evet", "hayır", "1", "0"}:
            return value.casefold() in {"true", "evet", "1"}
        raise ValueError("Boolean için true/false, evet/hayır veya 1/0 gerekli.")
    raise ValueError("Desteklenmeyen tür.")


def parsed(snapshot, settings, control):
    names, warnings = None, []
    types = settings.types
    for ordinal, start, end, row, raw, reason in records(snapshot, settings, control):
        if settings.header_row and ordinal < settings.header_row:
            continue
        if names is None:
            if reason:
                raise ProjectError(
                    "Başlık/ilk kayıt CSV yapısı bozuk; ayarları kontrol edin."
                )
            original = (
                row
                if settings.header_row
                else [f"Sütun_{i + 1}" for i in range(len(row))]
            )
            names, warnings = headers(original)
            if types and len(types) != len(names):
                raise ProjectError(
                    "Sütun sayısı değişti. Tür seçimlerini sıfırlayıp yeniden önizleyin."
                )
            types = types or ("text",) * len(names)
            yield (
                "schema",
                dict(
                    names=names,
                    original_headers=original,
                    warnings=warnings,
                    types=types,
                ),
            )
            if settings.header_row:
                continue
        values = None
        if reason is None and len(row) != len(names):
            reason = f"Sütun sayısı {len(row)}; beklenen {len(names)}."
        if reason is None:
            try:
                values = []
                for v, t in zip(row, types, strict=True):
                    values.append(convert(v, t, settings))
            except (ValueError, InvalidOperation, OverflowError):
                reason = f"Tür dönüşümü başarısız; seçilen sütun türü/sayı/tarih ayarlarını kontrol edin (sütun {len(values) + 1})."
        record = dict(
            record_number=ordinal,
            start_line=start,
            end_line=end,
            raw=raw,
            reason=reason,
            values=values,
        )
        if reason and settings.bad_rows == "stop":
            raise ProjectError(
                f"Bozuk kayıt: {ordinal}, kaynak satırları {start}–{end}. {reason} Karantina politikasıyla raporlu içe aktarabilir veya ayarları düzeltebilirsiniz."
            )
        yield "record", record
    if names is None:
        raise ProjectError(
            "Dosya boş veya seçilen başlık kaydı yok. Dataset oluşturulmadı."
        )


def preview(snapshot, settings, control=None):
    control = control or Control()
    schema, rows, bad, examined = None, [], [], 0
    for kind, record in parsed(snapshot, settings, control):
        if kind == "schema":
            schema = record
            continue
        examined += 1
        if record["reason"]:
            bad.append(
                {
                    k: record[k]
                    for k in ("record_number", "start_line", "end_line", "reason")
                }
            )
        else:
            rows.append(["null" if v is None else str(v) for v in record["values"]])
        if examined >= PREVIEW_ROWS:
            break
    suggestions = []
    for i in range(len(schema["names"])):
        vals = [r[i] for r in rows if r[i] != "null"]
        suggestion = "text"
        if vals and all(re.fullmatch(r"[1-9]\d{0,14}|0", v) for v in vals):
            suggestion = "int64"
        elif vals and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) for v in vals):
            suggestion = "date"
        suggestions.append(suggestion)
    return dict(
        schema=schema,
        rows=rows,
        bad=bad,
        examined=examined,
        limited=examined >= PREVIEW_ROWS,
        suggestions=suggestions,
        settings={
            k: list(v) if isinstance(v, tuple) else v
            for k, v in asdict(settings).items()
        },
        capture=snapshot,
    )


def dtype(kind, settings):
    return {
        "text": pl.String,
        "int64": pl.Int64,
        "float64": pl.Float64,
        "decimal": pl.Decimal(38, 6),
        "date": pl.Date,
        "datetime": pl.Datetime("us", settings.timezone or None),
        "boolean": pl.Boolean,
    }[kind]


def import_snapshot(snapshot, settings, workspace, control=None):
    control = control or Control()
    verify_capture(snapshot, control)
    schema, rows, rejected, parts, bad_parts = None, [], [], [], []
    accepted, bad_count, examined, chunk_bytes = 0, 0, 0, 0
    snapshot_id = "snapshot:" + uid()

    def flush():
        nonlocal rows, rejected
        control.check()
        if rows:
            path = Path(workspace) / (uid() + ".part.parquet")
            pl.DataFrame(
                rows,
                schema=[
                    (n, dtype(t, settings))
                    for n, t in zip(schema["names"], schema["types"], strict=True)
                ]
                + [
                    (n, pl.String if i < 2 else pl.Int64)
                    for i, n in enumerate(INTERNAL)
                ],
                orient="row",
            ).write_parquet(path)
            parts.append(path)
            if len(parts) + len(bad_parts) > 16384:
                raise ProjectError("Parça sayısı bütçesi aşıldı.")
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
                    "raw": pl.String,
                    "reason": pl.String,
                },
            ).write_parquet(path)
            bad_parts.append(path)
            if len(parts) + len(bad_parts) > 16384:
                raise ProjectError("Parça sayısı bütçesi aşıldı.")
            rejected = []
        control.disk(workspace)

    for kind, record in parsed(snapshot, settings, control):
        if kind == "schema":
            schema = record
            continue
        examined += 1
        source_record_id = "sr:" + uid()
        if record["reason"]:
            bad_count += 1
            rejected.append(
                dict(
                    source_record_id=source_record_id,
                    **{
                        k: record[k]
                        for k in (
                            "record_number",
                            "start_line",
                            "end_line",
                            "raw",
                            "reason",
                        )
                    },
                )
            )
        else:
            accepted += 1
            rows.append(
                record["values"]
                + [
                    "row:" + uid(),
                    source_record_id,
                    record["start_line"],
                    record["end_line"],
                ]
            )
        chunk_bytes += len(record["raw"].encode("utf8"))
        if len(rows) + len(rejected) >= 4096 or chunk_bytes >= 8 * 1024**2:
            flush()
            chunk_bytes = 0
            control.progress("Kayıt doğrulama", examined, None)
    flush()
    if not accepted:
        raise ProjectError(
            f"Geçerli veri kaydı yok ({bad_count} bozuk kayıt). Dataset oluşturulmadı."
        )
    control.check()
    if len(parts) + len(bad_parts) > 16384:
        raise ProjectError("Parça sayısı bütçesi aşıldı.")
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
    control.disk(workspace)
    verify_capture(snapshot, control)
    return dict(
        path=str(output),
        artifact_fingerprint=hash_artifact(output, control),
        quarantine_fingerprint=hash_artifact(quarantine, control)
        if quarantine
        else None,
        quarantine=str(quarantine) if quarantine else None,
        schema=schema,
        accepted=accepted,
        bad_count=bad_count,
        examined=examined,
        source_snapshot_id=snapshot_id,
        settings={
            k: list(v) if isinstance(v, tuple) else v
            for k, v in asdict(settings).items()
        },
        capture=snapshot,
    )


def hash_artifact(path, control):
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as stream:
        while block := stream.read(1024 * 1024):
            control.check()
            h.update(block)
            size += len(block)
    return dict(sha256=h.hexdigest(), size=size)


def verify_capture(snapshot, control):
    if hash_artifact(snapshot["path"], control) != snapshot["fingerprint"]:
        raise ProjectError("Önizleme kopyası değişmiş; yeniden dosya seçip önizleyin.")
