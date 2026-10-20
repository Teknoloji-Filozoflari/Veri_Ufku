"""Bounded export with explicit projection, verified rows and type loss."""

import csv
import hashlib
import json
import math
import zipfile
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

import polars as pl

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import checked
from veri_ufku.exports.files import publish
from veri_ufku.exports.query import scoped
from veri_ufku.importers.delimited import Control
from veri_ufku.storage.project_model import ProjectError

FORMATS = ("csv", "json", "jsonl", "parquet", "xlsx")
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


@dataclass(frozen=True)
class ExportSpec:
    format: str
    scope: str = "view"
    view: dict = field(default_factory=dict)
    spreadsheet_safe: bool = True
    accept_loss: bool = False
    null_marker: str = "\\N"

    def validate(self, columns):
        if self.format not in FORMATS or self.scope not in ("full", "view"):
            raise ProjectError("Export formatı/kapsamı geçersiz.")
        if (
            type(self.spreadsheet_safe) is not bool
            or type(self.accept_loss) is not bool
        ):
            raise ProjectError("Export politikası geçersiz.")
        if (
            not isinstance(self.null_marker, str)
            or not self.null_marker
            or len(self.null_marker) > 32
            or any(v in self.null_marker for v in "\r\n,")
            or (self.spreadsheet_safe and dangerous(self.null_marker))
        ):
            raise ProjectError("CSV null işareti 1–32 karakter ve tek satır olmalı.")
        ViewSpec.from_dict(self.view).validate(columns)


def plan(request, spec):
    spec.validate(request["columns"])
    schema = pl.read_parquet_schema(request["path"])
    columns = [c["name"] for c in request["columns"]]
    losses = []
    for name in columns:
        dtype = schema[name]
        if spec.format != "parquet":
            if dtype.is_nested() or dtype in (pl.Binary, pl.Duration, pl.Time):
                raise ProjectError(
                    "Bu formatta nested/Binary/Duration/Time export desteklenmiyor; türleri korumak için Parquet seçin."
                )
            losses.append(
                dict(
                    column=name,
                    source_type=str(dtype),
                    output_type="text"
                    if spec.format == "csv"
                    or dtype.is_temporal()
                    or isinstance(dtype, pl.Decimal)
                    else "JSON scalar / XLSX cell",
                    reason="Fiziksel şema/rol/birim korunmaz; date/datetime ISO metin, Decimal tam metin; büyük XLSX integer metin. XLSX Float64 hücresi gerçek numeric yazılır; Excel15-basamak okuyucusu yuvarlayabilir, kesin tür/değer için Parquet seçin. Parquet kullanarak fiziksel türleri koruyun. JSON büyük integer değerleri korur; JavaScript gibi 53-bit okuyucularda hassasiyet kaybolabilir. CSV sayıları tam yazar; spreadsheet okuyucusunun 15 basamak sınırı geçerlidir.",
                )
            )
    return dict(
        format=spec.format,
        spreadsheet_safe=spec.spreadsheet_safe,
        null_marker=spec.null_marker,
        loss_accepted=spec.accept_loss,
        columns=columns,
        source_schema={n: str(schema[n]) for n in columns},
        losses=losses,
        null_policy=f"CSV null={spec.null_marker!r}; boş metin ayrı. JSON null; XLSX eksik hücre; Parquet native null. NaN/±inf metin tokenı, null değildir.",
        date_policy="Date/datetime ISO metin; ns kesilmez. IANA timezone fiziksel metadata'sı metin formatlarında kaybolur.",
        limits="XLSX ürün sınırı 100000 veri satırı/256 sütun/32767 hücre karakteri ve64MiB sheet XML; Excel teorik 1048576 satır/16384 sütun. JSON 64MiB; JSONL/CSV streaming. Parquet native.",
        metadata_policy="Rol/birim/geçmiş yalnız proje kaydında korunur. Gizli sütunlar da aktarılır; RowId iç alanları aktarılmaz. Görünüm sıralaması korunur, tam dataset kaynak sırasını kullanır.",
        safe_policy="CSV tehlikeli metin ve başlıklara apostrof eklenir (=,+,-,@ ve kontrol karakteri başlangıçları); gerçek sayılar değişmez. XLSX bütün metinler inlineStr; formül düğümü yok. Güvenli CSV kapatılırsa spreadsheet formül yorumu riski kullanıcı tarafından seçilir.",
    )


def dangerous(value):
    return bool(value) and (
        value[0] in "\t\r\n" or value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@"))
    )


def name_of(index):
    out = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        out = chr(65 + remainder) + out
    return out


def write_xlsx(rows, columns, path, control, row_count):
    sheet = Path(path).with_suffix(".xml")
    with sheet.open("w", encoding="utf-8") as out:
        out.write(
            f'<worksheet xmlns="{NS}"><dimension ref="A1:{name_of(len(columns))}{row_count + 1}"/><sheetData>'
        )
        count = 0
        for row in [columns]:
            write_row(out, row, 1)
        for count, row in enumerate(rows, 1):
            control.check()
            write_row(out, row, count + 1)
            if count > 100000 or out.tell() > 64 * 1024**2:
                raise ProjectError(
                    "XLSX export 100000 satır/64MiB sheet XML sınırını aştı; Parquet veya CSV seçin."
                )
        out.write("</sheetData></worksheet>")
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        )
        z.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        )
        z.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Veri" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        z.write(sheet, "xl/worksheets/sheet1.xml")


def write_row(out, row, number):
    out.write(f'<row r="{number}">')
    for j, value in enumerate(row, 1):
        ref = name_of(j) + str(number)
        if value is None:
            continue
        if isinstance(value, bool):
            out.write(f'<c r="{ref}" t="b"><v>{int(value)}</v></c>')
        elif isinstance(value, (int, float)):
            out.write(f'<c r="{ref}"><v>{value}</v></c>')
        else:
            value = str(value)
            if len(value) > 32767 or any(
                ord(c) < 32 and c not in "\t\r\n" for c in value
            ):
                raise ProjectError(
                    "XLSX metin hücresi 32767 karakter sınırını veya XML karakter kurallarını aşıyor."
                )
            out.write(
                f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(value)}</t></is></c>'
            )
    out.write("</row>")


def canonical(row):
    return (
        json.dumps(row, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        + "\n"
    ).encode()


def read_rows(path, fmt, columns, null_marker):
    if fmt == "csv":
        csv.field_size_limit(1024**2)
        with Path(path).open(encoding="utf-8-sig", newline="") as inp:
            reader = csv.reader(inp)
            if next(reader) != columns:
                raise ProjectError("Export başlık doğrulaması başarısız.")
            yield from (
                [None if v == null_marker else v for v in row] for row in reader
            )
    elif fmt in ("json", "jsonl"):
        with Path(path).open(encoding="utf-8") as inp:
            records = (
                json.load(inp) if fmt == "json" else (json.loads(line) for line in inp)
            )
            for record in records:
                yield [record[n] for n in columns]
    else:
        with zipfile.ZipFile(path) as z, z.open("xl/worksheets/sheet1.xml") as inp:
            for _, element in ET.iterparse(inp, events=("end",)):
                if element.tag != f"{{{NS}}}row":
                    continue
                if element.attrib["r"] == "1":
                    element.clear()
                    continue
                row = [None] * len(columns)
                for cell in element:
                    index = 0
                    for c in cell.attrib["r"]:
                        if not c.isalpha():
                            break
                        index = index * 26 + ord(c) - 64
                    typ = cell.attrib.get("t")
                    raw = cell.findtext(f"{{{NS}}}v")
                    row[index - 1] = (
                        "".join(cell.itertext())
                        if typ == "inlineStr"
                        else bool(int(raw))
                        if typ == "b"
                        else float(raw)
                        if "." in raw or "e" in raw.lower()
                        else int(raw)
                    )
                yield row
                element.clear()


def generate(request, spec, workspace, control=None):
    control = control or Control()
    control.disk(Path(workspace))
    spec = spec if isinstance(spec, ExportSpec) else ExportSpec(**spec)
    info = plan(request, spec)
    if info["losses"] and not spec.accept_loss:
        raise ProjectError(
            "Format tür kayıplarını okuyup açık onay verin veya Parquet seçin."
        )
    checked(request, control)
    query, schema, view = scoped(request, spec)
    columns = info["columns"]
    query = query.select(columns)
    count = query.select(pl.len()).collect().item()
    if spec.format == "xlsx" and (count > 100000 or len(columns) > 256):
        raise ProjectError("XLSX 100000 satır/256 sütun sınırını aşıyor.")
    path = Path(workspace) / ("data." + spec.format)
    info.update(
        rows=count,
        dataset_version=request["version_id"],
        scope=spec.scope,
        filters=list(view.filters),
        view=view.data(),
        spreadsheet_escaped=0,
        numeric_to_text=0,
        nonfinite_to_text=0,
        snapshot_fingerprint=request["fingerprint"],
    )
    output_columns = [
        "'" + n
        if spec.format == "csv" and spec.spreadsheet_safe and dangerous(n)
        else n
        for n in columns
    ]
    if len(set(output_columns)) != len(output_columns):
        raise ProjectError(
            "Güvenli CSV başlıkları çakışıyor; Parquet seçin veya sütunları açıkça yeniden adlandırın."
        )
    info["output_columns"] = output_columns
    info["escaped_headers"] = sum(a != b for a, b in zip(columns, output_columns))
    if spec.format == "parquet":
        query.sink_parquet(path, maintain_order=True)
        read = pl.scan_parquet(path)
        if (
            read.collect_schema() != query.collect_schema()
            or read.select(pl.len()).collect().item() != count
        ):
            raise ProjectError("Parquet tür/kayıt doğrulaması başarısız.")

        # Sequential row hashes include order, nulls and native values without Python temporal conversion.
        def native_digest(frame):
            digest = hashlib.sha256()
            for batch in frame.select(
                pl.struct(pl.all()).hash(seed=13).alias("hash")
            ).collect_batches(chunk_size=4096, maintain_order=True):
                control.check()
                for value in batch["hash"]:
                    digest.update(value.to_bytes(8, "little"))
            return digest.hexdigest()

        info["projection_sha256"] = native_digest(read)
        if info["projection_sha256"] != native_digest(query):
            raise ProjectError("Parquet değer/satır sırası doğrulaması başarısız.")
    else:
        expected = hashlib.sha256()
        written = [0]

        def projected():
            batches = query.collect_batches(chunk_size=4096, maintain_order=True)
            try:
                for batch in batches:
                    control.check()
                    batch = batch.with_columns(
                        pl.col(n).cast(pl.String)
                        for n in columns
                        if schema[n].is_temporal()
                    )
                    for row in batch.iter_rows():
                        out = []
                        for value in row:
                            text_value = isinstance(value, str)
                            if isinstance(value, Decimal):
                                value = str(value)
                                info["numeric_to_text"] += 1
                            elif isinstance(value, float) and not math.isfinite(value):
                                value = str(value)
                                info["nonfinite_to_text"] += 1
                                text_value = True
                            elif (
                                spec.format == "xlsx"
                                and isinstance(value, int)
                                and not isinstance(value, bool)
                                and len(str(abs(value))) > 15
                            ):
                                value = str(value)
                                info["numeric_to_text"] += 1
                            if spec.format == "csv" and value is not None:
                                if (
                                    text_value
                                    and spec.spreadsheet_safe
                                    and dangerous(value)
                                ):
                                    value = "'" + value
                                    info["spreadsheet_escaped"] += 1
                                value = str(value)
                                if value == spec.null_marker:
                                    raise ProjectError(
                                        "CSV null işareti gerçek metinle çakışıyor; başka işaret seçin."
                                    )
                            out.append(value)
                        expected.update(canonical(out))
                        written[0] += 1
                        yield out
                    control.progress("Export kayıtları", written[0], count)
                    control.disk(Path(workspace))
            finally:
                del batches

        if spec.format == "xlsx":
            write_xlsx(projected(), columns, path, control, count)
        else:
            with path.open(
                "w",
                encoding="utf-8-sig" if spec.format == "csv" else "utf-8",
                newline="",
            ) as out:
                if spec.format == "csv":
                    writer = csv.writer(out)
                    writer.writerow(output_columns)
                    for row in projected():
                        writer.writerow(
                            [spec.null_marker if v is None else v for v in row]
                        )
                else:
                    if spec.format == "json":
                        out.write("[")
                    for i, row in enumerate(projected()):
                        if spec.format == "json" and i:
                            out.write(",")
                        out.write(
                            json.dumps(
                                dict(zip(columns, row)),
                                ensure_ascii=False,
                                allow_nan=False,
                            )
                        )
                        if spec.format == "jsonl":
                            out.write("\n")
                        if spec.format == "json" and out.tell() > 64 * 1024**2:
                            raise ProjectError(
                                "JSON 64MiB sınırını aşıyor; JSONL seçin."
                            )
                    if spec.format == "json":
                        out.write("]")
        actual = hashlib.sha256()
        verified = 0
        for row in read_rows(path, spec.format, output_columns, spec.null_marker):
            control.check()
            actual.update(canonical(row))
            verified += 1
        if (
            verified != count
            or written[0] != count
            or actual.digest() != expected.digest()
        ):
            raise ProjectError("Export yeniden açma değer/kayıt doğrulaması başarısız.")
        info["projection_sha256"] = actual.hexdigest()
    checked(request, control)
    control.disk(Path(workspace))
    info.update(
        verified_rows=count,
        types_verified=True,
        projection_verified=True,
        artifact=str(path),
    )
    return info


def export(request, spec, workspace, destination, project_root, control=None):
    control = control or Control()
    fmt = spec.format if isinstance(spec, ExportSpec) else spec["format"]
    if Path(destination).suffix.lower() != "." + fmt:
        raise ProjectError("Export formatıyla dosya uzantısı aynı olmalı.")
    result = generate(request, spec, workspace, control)
    result["published"] = publish(
        result["artifact"], destination, project_root, control
    )
    return result
