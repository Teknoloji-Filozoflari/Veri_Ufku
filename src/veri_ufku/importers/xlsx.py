"""Bounded, read-only SpreadsheetML adapter. No macro/formula execution or extraction."""

import posixpath
import re
import stat
import zipfile
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, localcontext
from xml.etree import ElementTree as ET

from veri_ufku.importers.delimited import MAX_RECORD, Control, headers
from veri_ufku.importers.native import canonical
from veri_ufku.storage.project_model import ProjectError

MAX_PART = 64 * 1024**2
MAX_XML_TOTAL = 256 * 1024**2


def local(tag):
    return tag.rsplit("}", 1)[-1]


def children(element, name):
    return [e for e in element if local(e.tag) == name]


def first(element, name):
    return next((e for e in element if local(e.tag) == name), None)


def location(value):
    match = re.fullmatch(r"\$?([A-Za-z]{1,3})\$?([1-9]\d{0,6})", value)
    if not match:
        raise ProjectError("Excel aralığı A1:D20 gibi olmalı.")
    column = 0
    for c in match[1].upper():
        column = column * 26 + ord(c) - 64
    row = int(match[2])
    if column > 16384 or row > 1048576:
        raise ProjectError("Excel hücre konumu sınır dışında.")
    return column, row


def cell_range(value):
    items = value.split(":")
    if len(items) not in (1, 2):
        raise ProjectError("Excel aralığı geçersiz.")
    left, top = location(items[0])
    right, bottom = location(items[-1])
    if left > right or top > bottom or right - left >= 256:
        raise ProjectError("Excel aralığı ters veya256 sütundan geniş.")
    return left, top, right, bottom


def column_name(column):
    name = ""
    while column:
        column, remainder = divmod(column - 1, 26)
        name = chr(65 + remainder) + name
    return name


class Workbook:
    def __init__(self, path, control=None):
        self.control = control or Control()
        try:
            self.archive = zipfile.ZipFile(path)
        except (zipfile.BadZipFile, OSError) as error:
            raise ProjectError(
                "XLSX geçerli ZIP/Office Open XML dosyası değil."
            ) from error
        try:
            files = self.archive.infolist()
            names = set()
            total = 0
            if len(files) > 10000:
                raise ProjectError("XLSX parça sayısı sınır dışında.")
            for info in files:
                self.control.check()
                if (
                    info.filename in names
                    or info.filename.startswith("/")
                    or "\\" in info.filename
                    or any(
                        p in ("..", "") for p in info.filename.rstrip("/").split("/")
                    )
                    or stat.S_ISLNK(info.external_attr >> 16)
                ):
                    raise ProjectError(
                        "XLSX arşiv yolu/tekrar/symlink geçersiz; dışarı dosya açılmadı."
                    )
                names.add(info.filename)
                total += info.file_size
                if (
                    info.file_size > MAX_PART
                    or total > min(MAX_XML_TOTAL, self.control.budget.temp_disk_bytes)
                    or info.flag_bits & 1
                ):
                    raise ProjectError(
                        "XLSX sıkıştırılmamış boyut/parça sınırı veya şifreli dosya desteklenmiyor."
                    )
            content = self.xml("[Content_Types].xml")
            if any(
                "macroEnabled" in e.get("ContentType", "")
                or "vbaProject" in e.get("ContentType", "")
                for e in content
            ) or any("vbaproject" in n.lower() for n in names):
                raise ProjectError(
                    "Makrolu çalışma kitabı bu XLSX adaptöründe desteklenmiyor; makro çalıştırılmadı."
                )
            roots = self.relationships("", "_rels/.rels")
            workbooks = [
                v for _, (kind, v) in roots.items() if kind.endswith("/officeDocument")
            ]
            if len(workbooks) != 1:
                raise ProjectError("XLSX çalışma kitabı ilişkisi bulunamadı.")
            self.workbook_path = workbooks[0]
            book = self.xml(self.workbook_path)
            if local(book.tag) != "workbook":
                raise ProjectError("XLSX workbook yapısı geçersiz.")
            relpath = posixpath.join(
                posixpath.dirname(self.workbook_path),
                "_rels",
                posixpath.basename(self.workbook_path) + ".rels",
            )
            relations = self.relationships(self.workbook_path, relpath)
            props = first(book, "workbookPr")
            self.date1904 = props is not None and props.get("date1904") in ("1", "true")
            sheets = first(book, "sheets")
            self.sheets = {}
            if sheets is None:
                raise ProjectError("Excel sayfaları bulunamadı.")
            for sheet in sheets:
                rid = next(
                    (v for k, v in sheet.attrib.items() if local(k) == "id"), None
                )
                relation = relations.get(rid)
                if not relation or not relation[0].endswith("/worksheet"):
                    continue
                name = sheet.get("name", "")
                if not name or name in self.sheets:
                    raise ProjectError("Excel sayfa adı eksik/tekrar.")
                self.sheets[name] = relation[1]
            if not self.sheets:
                raise ProjectError("Okunabilir Excel sayfası yok.")
            self.strings = []
            self.styles = []
            for kind, path in relations.values():
                if kind.endswith("/sharedStrings"):
                    root = self.xml(path)
                    for item in root:
                        value = "".join(
                            e.text or "" for e in item.iter() if local(e.tag) == "t"
                        )
                        if len(value.encode()) > MAX_RECORD:
                            raise ProjectError(
                                "Excel metin hücresi1 MiB sınırını aşıyor."
                            )
                        self.strings.append(value)
                if kind.endswith("/styles"):
                    root = self.xml(path)
                    custom = {
                        int(e.get("numFmtId")): e.get("formatCode", "")
                        for e in root.iter()
                        if local(e.tag) == "numFmt"
                    }
                    xfs = first(root, "cellXfs")
                    for xf in xfs if xfs is not None else []:
                        fmt = int(xf.get("numFmtId", "0"))
                        code = custom.get(fmt, "")
                        stripped = re.sub(r'"[^"]*"|\\.|\[[^]]*\]', "", code).lower()
                        date_format = (
                            fmt in range(14, 23)
                            or fmt in (45, 46, 47)
                            or bool(re.search(r"[ymdhs]", stripped))
                        )
                        elapsed = fmt == 46 or bool(
                            re.search(r"\[[hms]+\]", code.lower())
                        )
                        self.styles.append((date_format, elapsed))
        except BaseException:
            self.archive.close()
            raise

    def close(self):
        self.archive.close()

    def xml(self, path):
        try:
            raw = self.archive.read(path)
            self.control.check()
            if (
                b"<!DOCTYPE" in raw.replace(b"\x00", b"").upper()
                or b"<!ENTITY" in raw.replace(b"\x00", b"").upper()
            ):
                raise ProjectError("XLSX XML DTD/entity tanımı desteklenmiyor.")
            return ET.fromstring(raw)
        except (KeyError, ET.ParseError, zipfile.BadZipFile) as error:
            raise ProjectError("XLSX XML parçası eksik veya bozuk.") from error

    def relationships(self, base, path):
        root = self.xml(path)
        result = {}
        for e in root:
            rid = e.get("Id")
            target = e.get("Target", "")
            kind = e.get("Type", "")
            if e.get("TargetMode") == "External":
                continue
            if not rid or rid in result or "\\" in target or ":" in target:
                raise ProjectError("XLSX ilişkisi geçersiz.")
            target = (
                posixpath.normpath(posixpath.join(posixpath.dirname(base), target))
                if not target.startswith("/")
                else target.lstrip("/")
            )
            if target == ".." or target.startswith("../") or not target:
                raise ProjectError("XLSX ilişkisi arşiv dışına çıkıyor.")
            result[rid] = (kind, target)
        return result

    def sheet_xml(self, name):
        if name not in self.sheets:
            raise ProjectError("Excel sayfası bulunamadı; sayfa seçimini düzeltin.")
        root = self.xml(self.sheets[name])
        if local(root.tag) != "worksheet":
            raise ProjectError("Excel worksheet yapısı geçersiz.")
        return root


def excel_date(value, date1904):
    if not value.is_finite():
        raise ProjectError("Excel tarih seri değeri sonlu olmalı.")
    with localcontext() as context:
        context.prec = 60
        day = int(value // 1)
        fraction = value - Decimal(day)
        if not date1904 and day == 60:
            raise ProjectError(
                "Excel1900 seri60: gerçek olmayan1900-02-29. Seri sayı seçin; tarih uydurulmadı."
            )
        micros = fraction * Decimal(86400000000)
        if micros != micros.to_integral_value():
            raise ProjectError(
                "Excel tarih kesri mikrosaniyeye kayıpsız çevrilemiyor. Seri sayı seçin; yuvarlama yapılmadı."
            )
        epoch = datetime(1904, 1, 1) if date1904 else datetime(1899, 12, 31)
        if not date1904 and day > 60:
            day -= 1
        try:
            return epoch + timedelta(days=day, microseconds=int(micros))
        except OverflowError as error:
            raise ProjectError("Excel tarihi destek aralığı dışında.") from error


def cell_value(cell, book, settings):
    formula = first(cell, "f")
    value = first(cell, "v")
    text = value.text if value is not None else None
    if formula is not None:
        if settings.formulas in ("formula", "text"):
            if not formula.text:
                raise ProjectError(
                    "Paylaşılan/array formül metni bu hücrede yok; formül uydurulmadı. Önbellek seçin."
                )
            return ("=" if settings.formulas == "formula" else "") + formula.text
        if text is None:
            raise ProjectError(
                "Formül önbelleği yok. Formül/metin seçin; sonuç hesaplanmadı."
            )
    kind = cell.get("t", "n")
    if kind == "inlineStr":
        return "".join(e.text or "" for e in cell.iter() if local(e.tag) == "t")
    if text is None:
        return None
    if kind == "s":
        try:
            index = int(text)
            if index < 0:
                raise ValueError("negative string index")
            return book.strings[index]
        except (ValueError, IndexError) as error:
            raise ProjectError("Excel shared-string indeksi geçersiz.") from error
    if kind in ("str",):
        return text
    if kind == "b":
        if text not in ("0", "1"):
            raise ProjectError("Excel boolean hücresi geçersiz.")
        return text == "1"
    if kind == "e":
        raise ProjectError("Excel hata hücresi; otomatik null yapılmadı.")
    if kind == "d":
        try:
            dt = datetime.fromisoformat(text)
            if dt.tzinfo:
                raise ProjectError(
                    "Excel ISO tarih timezone içeriyor; XLSX naive tarih sözleşmesi dışında."
                )
            return dt
        except ValueError as error:
            raise ProjectError("Excel ISO tarih hücresi geçersiz.") from error
    if kind != "n":
        raise ProjectError("Excel hücre türü desteklenmiyor.")
    try:
        number = Decimal(text)
    except InvalidOperation as error:
        raise ProjectError("Excel sayı hücresi geçersiz.") from error
    if not number.is_finite():
        raise ProjectError("Excel NaN/inf desteklenmiyor.")
    style = int(cell.get("s", "0"))
    if style < 0 or style and style >= len(book.styles):
        raise ProjectError("Excel stil indeksi geçersiz.")
    date_format, elapsed = book.styles[style] if book.styles else (False, False)
    if date_format and settings.excel_dates == "dates":
        if elapsed:
            raise ProjectError(
                "Excel elapsed süre biçimi tarih değildir. Seri sayı seçin."
            )
        return excel_date(number, book.date1904)
    return int(number) if number == number.to_integral_value() else number


def excel_records(snapshot, settings, control):
    book = Workbook(snapshot["path"], control)
    try:
        name = settings.sheet or next(iter(book.sheets))
        root = book.sheet_xml(name)
        dimension = first(root, "dimension")
        if settings.cell_range:
            bounds = cell_range(settings.cell_range)
        elif dimension is not None and dimension.get("ref"):
            bounds = cell_range(dimension.get("ref"))
        else:
            coords = [
                location(c.get("r", "")) for c in root.iter() if local(c.tag) == "c"
            ]
            if not coords:
                raise ProjectError("Excel sayfası boş.")
            bounds = (
                min(c[0] for c in coords),
                min(c[1] for c in coords),
                max(c[0] for c in coords),
                max(c[1] for c in coords),
            )
        left, top, right, bottom = bounds
        if right - left >= 256 or bottom - top >= 1000000:
            raise ProjectError("Excel seçim boyutu destek sınırı dışında.")
        merge = first(root, "mergeCells")
        merged_ranges = []
        if merge is not None:
            for item in merge:
                a, b, c, d = cell_range(item.get("ref", ""))
                if a <= right and c >= left and b <= bottom and d >= top:
                    merged_ranges.append((a, b, c, d))
                    if settings.merged_cells != "reject":
                        continue
                    raise ProjectError(
                        "Seçimde birleştirilmiş hücre var. Yalnız sol üst hücre seçeneğini açıkça seçin; değer yayılmaz."
                    )
        data = first(root, "sheetData")
        if data is None:
            raise ProjectError("Excel sheetData bulunamadı.")
        row_elements = {}
        for row in data:
            number = int(row.get("r", "0"))
            if not 1 <= number <= 1048576 or number in row_elements:
                raise ProjectError("Excel satır konumu geçersiz/tekrar.")
            row_elements[number] = row
        columns = None
        originals = None
        if settings.header_row and not top <= settings.header_row <= bottom:
            raise ProjectError(
                "Excel başlık satırı seçilen aralık içinde olmalı;0 başlıksız."
            )
        for row_number in range(top, bottom + 1):
            control.check()
            if settings.header_row and row_number < settings.header_row:
                continue
            row = row_elements.get(row_number)
            cells = {}
            reason = None
            for cell in row if row is not None else []:
                col, cell_row = location(cell.get("r", ""))
                if cell_row != row_number or col in cells:
                    raise ProjectError("Excel hücre konumu uyuşmuyor/tekrar.")
                if left <= col <= right and not any(
                    a <= col <= c
                    and b <= row_number <= d
                    and (col, row_number) != (a, b)
                    for a, b, c, d in merged_ranges
                ):
                    cells[col] = cell
            vals = []
            for col in range(left, right + 1):
                try:
                    vals.append(
                        cell_value(cells[col], book, settings) if col in cells else None
                    )
                except (ProjectError, ValueError) as error:
                    vals.append(None)
                    reason = f"{column_name(col)}{row_number}: {error}"
            if columns is None:
                originals = (
                    [str(v) if v is not None else "" for v in vals]
                    if settings.header_row
                    else [column_name(c) for c in range(left, right + 1)]
                )
                columns, _ = headers(originals)
                if settings.header_row:
                    if reason:
                        raise ProjectError("Excel başlığı okunamadı: " + reason)
                    continue
            if (
                settings.blank_rows == "skip"
                and not reason
                and all(v is None for v in vals)
            ):
                continue
            values = dict(zip(columns, vals, strict=True))
            raw = canonical(
                {
                    "cells": {
                        column_name(c): ET.tostring(cell, encoding="unicode")
                        for c, cell in cells.items()
                    }
                }
            )
            if len(raw.encode()) > MAX_RECORD:
                raise ProjectError("Excel satırı1 MiB sınırını aşıyor.")
            # Keep original headers alongside unique names; adapter metadata owns this mapping.
            locator = f"{name}!{column_name(left)}{row_number}:{column_name(right)}{row_number}"
            yield dict(
                ordinal=row_number,
                start=row_number,
                end=row_number,
                locator=locator,
                values=values,
                raw=raw,
                reason=reason,
                expansion="{}",
                original_headers=originals,
            )
    finally:
        book.close()
