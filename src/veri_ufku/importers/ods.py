"""Bounded ODS table reader using stdlib; no formula, script or link execution."""

import zipfile
from datetime import date
from decimal import Decimal
from xml.etree import ElementTree as ET

from veri_ufku.importers.delimited import headers
from veri_ufku.importers.native import canonical
from veri_ufku.storage.project_model import ProjectError

NS = {
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}


def attr(cell, ns, name, default=None):
    return cell.get("{" + NS[ns] + "}" + name, default)


def document(path):
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if (
                len(entries) > 10000
                or len({e.filename for e in entries}) != len(entries)
                or any(e.flag_bits & 1 for e in entries)
                or sum(e.file_size for e in entries) > 256 * 1024**2
            ):
                raise ProjectError("ODS arşiv boyutu/şifre/tekrar sınırı dışında.")
            if (
                archive.read("mimetype")
                != b"application/vnd.oasis.opendocument.spreadsheet"
            ):
                raise ProjectError("ODS mimetype uyuşmuyor.")
            info = archive.getinfo("content.xml")
            if info.file_size > 64 * 1024**2:
                raise ProjectError("ODS content.xml64MiB sınırını aşıyor.")
            raw = archive.read("content.xml")
            if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
                raise ProjectError("ODS XML DTD/entity kabul edilmez.")
            root = ET.fromstring(raw)
            sheets = root.findall("./office:body/office:spreadsheet/table:table", NS)
            result = {attr(s, "table", "name"): s for s in sheets}
            if not result or len(result) != len(sheets) or None in result:
                raise ProjectError("ODS sayfa adları eksik/tekrar.")
            return result
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as error:
        raise ProjectError("ODS ZIP/XML okunamadı.") from error


def value(cell, settings):
    formula = attr(cell, "table", "formula")
    if formula and settings.formulas != "cached":
        return formula if settings.formulas == "text" else "=" + formula
    if (
        attr(cell, "table", "number-columns-spanned", "1") != "1"
        or attr(cell, "table", "number-rows-spanned", "1") != "1"
    ):
        if settings.merged_cells == "reject":
            raise ProjectError("ODS birleşik hücre: durdur veya yalnız sol üstü seçin.")
    kind = attr(cell, "office", "value-type")
    if formula and kind is None:
        raise ProjectError("ODS formül önbelleği yok; formül çalıştırılmadı.")
    if kind in ("float", "currency", "percentage"):
        number = Decimal(attr(cell, "office", "value"))
        if not number.is_finite():
            raise ProjectError("ODS sonlu olmayan sayı desteklenmiyor.")
        return number
    if kind == "boolean":
        raw = attr(cell, "office", "boolean-value")
        if raw not in ("true", "false"):
            raise ProjectError("ODS Boolean geçersiz.")
        return raw == "true"
    if kind == "date":
        raw = attr(cell, "office", "date-value")
        if "T" not in raw:
            return date.fromisoformat(raw)
        # Nanosecond loss and timezone/DST correction never happen implicitly.
        import polars as pl

        from veri_ufku.operations.cleaning import exact_value

        return exact_value(raw, pl.Datetime("us"))
    if kind == "time":
        raise ProjectError(
            "ODS ISO duration/time desteklenmiyor; açık metin dışa aktarımı kullanın."
        )
    if kind in (None, "string"):
        paragraphs = cell.findall("text:p", NS)
        return (
            "\n".join("".join(p.itertext()) for p in paragraphs) if paragraphs else None
        )
    raise ProjectError("ODS hücre türü desteklenmiyor: " + str(kind))


def records(snapshot, settings, control):
    sheets = document(snapshot["path"])
    if settings.sheet not in sheets:
        raise ProjectError("ODS sayfasını seçin.")
    if settings.cell_range:
        raise ProjectError(
            "ODS aralık seçimi desteklenmez; tüm sayfa ve açık başlık satırı okunur."
        )
    columns = None
    originals = None
    number = 0
    for row in sheets[settings.sheet].findall(".//table:table-row", NS):
        control.check()
        repeat = int(attr(row, "table", "number-rows-repeated", "1"))
        if not 1 <= repeat <= 1000000:
            raise ProjectError("ODS tekrar satır sınırı aşıldı.")
        vals = []
        for cell in row:
            if cell.tag not in (
                "{" + NS["table"] + "}table-cell",
                "{" + NS["table"] + "}covered-table-cell",
            ):
                continue
            n = int(attr(cell, "table", "number-columns-repeated", "1"))
            if not 1 <= n <= 256 or len(vals) + n > 256:
                raise ProjectError(
                    "ODS sütun/tekrar sınırı256 aşıldı; biçimlendirilmiş boş kolonları kaynakta kaldırın."
                )
            vals.extend([value(cell, settings)] * n)
        for _ in range(repeat):
            control.check()
            number += 1
            if number > 10000000:
                raise ProjectError("ODS kayıt sınırı aşıldı.")
            if settings.header_row and number < settings.header_row:
                continue
            if columns is None:
                originals = (
                    [str(v) if v is not None else "" for v in vals]
                    if settings.header_row
                    else [f"Kolon{i + 1}" for i in range(len(vals))]
                )
                columns, _ = headers(originals)
                if settings.header_row:
                    continue
            if len(vals) > len(columns):
                raise ProjectError("ODS satırı başlık genişliğini aşıyor.")
            padded = vals + [None] * (len(columns) - len(vals))
            if settings.blank_rows == "skip" and all(v is None for v in padded):
                continue
            values = dict(zip(columns, padded, strict=True))
            yield dict(
                ordinal=number,
                start=number,
                end=number,
                locator=f"ods:{settings.sheet}:row:{number}",
                values=values,
                raw=canonical(values),
                reason=None,
                expansion="{}",
                original_headers=originals,
            )
