"""One source adapter boundary for delimited, JSON, XLSX and native Parquet."""

from pathlib import Path

from veri_ufku.importers.contracts import SourceRequest
from veri_ufku.importers.delimited import (
    ImportSettings,
    import_snapshot,
    preview,
    suggest,
)
from veri_ufku.importers.native import EXTRA, StructuredSettings, restore
from veri_ufku.importers.parquet import import_parquet, parquet_schema, preview_parquet
from veri_ufku.importers.structured import (
    import_structured,
    json_document,
    list_paths,
    preview_structured,
    record_paths,
)
from veri_ufku.importers.xlsx import Workbook
from veri_ufku.storage.project_model import ProjectError

FORMATS = (
    "csv",
    "tsv",
    "json",
    "jsonl",
    "xlsx",
    "parquet",
    "ods",
    "sqlite",
    "ipc",
    "ipc_stream",
)


def settings_from_dict(data):
    return (
        StructuredSettings.from_dict(data)
        if "adapter_id" in data
        else ImportSettings.from_dict(data)
    )


def default_settings(adapter_id):
    if adapter_id in ("csv", "tsv"):
        return ImportSettings(delimiter="\t" if adapter_id == "tsv" else ",")
    return StructuredSettings(adapter_id=adapter_id)


def detect(snapshot):
    with open(snapshot["path"], "rb") as stream:
        raw = stream.read(65536)
    if raw.startswith(b"PAR1"):
        return "parquet"
    if raw.startswith(b"SQLite format 3\x00"):
        return "sqlite"
    if raw.startswith(b"ARROW1"):
        return "ipc"
    if raw.startswith(b"\xff\xff\xff\xff"):
        return "ipc_stream"
    if raw.startswith(b"PK"):
        import zipfile

        with zipfile.ZipFile(snapshot["path"]) as archive:
            return (
                "ods"
                if "mimetype" in archive.namelist()
                and archive.read("mimetype")
                == b"application/vnd.oasis.opendocument.spreadsheet"
                else "xlsx"
            )
    suffix = Path(snapshot["original"]).suffix.lower()
    if suffix in (".jsonl", ".ndjson"):
        return "jsonl"
    if raw.lstrip(b"\xef\xbb\xbf \r\n\t").startswith((b"[", b"{")):
        return "json"
    hints = {
        ".csv": "csv",
        ".tsv": "tsv",
        ".json": "json",
        ".xlsx": "xlsx",
        ".parquet": "parquet",
    }
    if suffix in hints:
        return hints[suffix]
    raise ProjectError(
        "Format algılanamadı. Formatı elle seçin; CSV/TSV, JSON/JSONL, XLSX ve Parquet desteklenir."
    )


class Adapter:
    def __init__(self, adapter_id):
        self.adapter_id = adapter_id

    def validate_source(self, request: SourceRequest):
        if request.adapter_id != self.adapter_id or not request.path.is_file():
            raise ProjectError("Adaptör/kaynak bağı geçersiz.")
        # Validation is parsing/magic based, never extension-only.
        if self.adapter_id in ("parquet", "ipc", "ipc_stream"):
            parquet_schema({"path": str(request.path)}, self.adapter_id)
        elif self.adapter_id == "ods":
            from veri_ufku.importers.ods import document

            document(request.path)
        elif self.adapter_id == "sqlite":
            from veri_ufku.importers.sqlite_source import tables

            tables({"path": str(request.path)})
        elif self.adapter_id == "xlsx":
            book = Workbook(request.path)
            book.close()
        else:
            with request.path.open("rb") as stream:
                raw = stream.read(4096)
            if raw.startswith((b"PAR1", b"PK")) or b"\x00" in raw:
                raise ProjectError("Seçilen metin formatı ile dosya içeriği uyuşmuyor.")

    def inspect(self, snapshot, settings, control):
        self.validate_source(SourceRequest(Path(snapshot["path"]), self.adapter_id))
        choices = {}
        if self.adapter_id == "json":
            document = json_document(snapshot, control)
            choices["record_paths"] = record_paths(document)
            try:
                from veri_ufku.importers.structured import select

                records = select(document, settings.record_path)
                choices["list_paths"] = (
                    sorted(
                        {
                            p
                            for r in records[:200]
                            if isinstance(r, dict)
                            for p in list_paths(r)
                        }
                    )
                    if isinstance(records, list)
                    else []
                )
            except ProjectError:
                choices["list_paths"] = []
        elif self.adapter_id == "sqlite":
            from veri_ufku.importers.sqlite_source import tables

            choices = dict(
                sheets=tables(snapshot),
                formula_behavior="SQLite yalnız ordinary tablolar: mode=ro, immutable, query_only; extension yüklenmez. BLOB, view/virtual table ve etkin WAL/journal desteklenmez. Türler gerçek değerlerden çıkarılır; tarih otomatik parse edilmez.",
            )
        elif self.adapter_id == "ods":
            from veri_ufku.importers.ods import document

            choices = dict(
                sheets=list(document(snapshot["path"])),
                date_system="ISO 8601",
                formula_behavior="ODS formülleri çalıştırılmaz; cached yalnız dosyadaki değer. Tüm sayfa okunur; duration ve256'dan geniş tekrarlar reddedilir.",
            )
        elif self.adapter_id == "xlsx":
            book = Workbook(snapshot["path"], control)
            choices = dict(
                sheets=list(book.sheets),
                date_system="1904" if book.date1904 else "1900",
                formula_behavior="Formüller çalıştırılmaz. Önbellek yalnız dosyada kayıtlı değerdir; güncelliği garanti edilmez. Eksik önbellek hata verir. Birleşik hücrelerde yalnız sol üst değer korunabilir; yayılmaz. Tarihler saat dilimsizdir. 1900 sisteminin sahte 60. günü ve mikrosaniyeye tam çevrilemeyen kesirler reddedilir; seri sayı seçimi asıl değeri korur.",
            )
            book.close()
        return choices

    def preview(self, snapshot, settings, control=None):
        if self.adapter_id in ("csv", "tsv"):
            return preview(snapshot, settings, control)
        if self.adapter_id in ("parquet", "ipc", "ipc_stream"):
            return preview_parquet(snapshot, settings, control)
        return preview_structured(snapshot, settings, control)

    def import_data(self, snapshot, settings, workspace, control):
        if self.adapter_id in ("csv", "tsv"):
            result = import_snapshot(snapshot, settings, workspace, control)
            result["adapter_id"] = self.adapter_id
            return result
        if self.adapter_id in ("parquet", "ipc", "ipc_stream"):
            return import_parquet(snapshot, settings, workspace, control)
        return import_structured(snapshot, settings, workspace, control)


ADAPTERS = {name: Adapter(name) for name in FORMATS}


def get_adapter(adapter_id):
    if adapter_id not in ADAPTERS:
        raise ProjectError("Import adaptörü desteklenmiyor.")
    return ADAPTERS[adapter_id]


def suggest_settings(snapshot, adapter_id):
    return (
        suggest(snapshot)
        if adapter_id in ("csv", "tsv")
        else default_settings(adapter_id)
    )


def validate_native_metadata(metadata, artifact):
    settings = StructuredSettings.from_dict(metadata["settings"])
    expected = {n: str(restore(t)) for n, t in settings.native_schema.items()}
    if not expected or expected != artifact["schema"]:
        raise ProjectError("Native dataset şeması metadata ile uyuşmuyor.")
    columns = metadata["columns"]
    for c in columns:
        if c["name"] not in expected or c["type"] != expected[c["name"]]:
            raise ProjectError("Native sütun türü/adı uyuşmuyor.")
    internals = {
        "__vu_row_id": "String",
        "__vu_source_record_id": "String",
        "__vu_start_line": "Int64",
        "__vu_end_line": "Int64",
        **{k: str(v) for k, v in EXTRA.items()},
    }
    if set(expected) != set(c["name"] for c in columns) | set(internals) or any(
        expected.get(k) != v for k, v in internals.items()
    ):
        raise ProjectError("Native lineage şeması geçersiz.")
