"""Real ODS, SQLite, Feather/IPC file and stream fixtures, immutable source boundaries."""

import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, datetime
from decimal import Decimal

import polars as pl
import pytest

from veri_ufku.importers.delimited import Control, capture
from veri_ufku.importers.native import StructuredSettings
from veri_ufku.importers.registry import detect, get_adapter
from veri_ufku.importers.sqlite_source import connect
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def ods_fixture(path):
    xml = """<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"><office:body><office:spreadsheet><table:table table:name="Satış"><table:table-row><table:table-cell office:value-type="string"><text:p>ürün</text:p></table:table-cell><table:table-cell office:value-type="string"><text:p>tutar</text:p></table:table-cell></table:table-row><table:table-row table:number-rows-repeated="2"><table:table-cell office:value-type="string"><text:p>çay</text:p></table:table-cell><table:table-cell office:value-type="float" office:value="2.10"/></table:table-row></table:table></office:spreadsheet></office:body></office:document-content>"""
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet")
        z.writestr("content.xml", xml)


@pytest.mark.parametrize("adapter", ["ods", "sqlite", "ipc", "ipc_stream"])
def test_real_formats_types_source_unchanged_and_reopen(tmp_path, adapter):
    path = tmp_path / ("source." + adapter)
    if adapter == "ods":
        ods_fixture(path)
        expected = pl.DataFrame(
            {"ürün": ["çay", "çay"], "tutar": [Decimal("2.10")] * 2}
        )
    elif adapter == "sqlite":
        with closing(sqlite3.connect(path)) as db:
            db.execute('CREATE TABLE "satış" (id INTEGER, tutar REAL, gün TEXT)')
            db.executemany(
                'INSERT INTO "satış" VALUES (?,?,?)',
                [(2, 3.5, "2024-01-02"), (1, None, "2024-01-01")],
            )
            db.commit()
        expected = pl.DataFrame(
            {"id": [2, 1], "tutar": [3.5, None], "gün": ["2024-01-02", "2024-01-01"]}
        )
    else:
        expected = pl.DataFrame(
            {
                "number": [Decimal("1.23"), None],
                "time": [datetime(2024, 1, 1, tzinfo=UTC), None],
                "list": [[1, 2], []],
            }
        )
        expected = expected.with_columns(pl.col("time").cast(pl.Datetime("ns", "UTC")))
        if adapter == "ipc":
            expected.write_ipc(path)
        else:
            expected.write_ipc_stream(path)
    original = path.read_bytes()
    work = tmp_path / "work"
    work.mkdir()
    snapshot = capture(path, work, any_format=True)
    assert detect(snapshot) == adapter
    a = get_adapter(adapter)
    settings = StructuredSettings(
        adapter_id=adapter,
        sheet="satış" if adapter == "sqlite" else "Satış" if adapter == "ods" else "",
    )
    choices = a.inspect(snapshot, settings, Control())
    if adapter == "sqlite":
        assert choices["sheets"] == ["satış"]
        with closing(connect(snapshot)) as db:
            with pytest.raises(sqlite3.OperationalError):
                db.execute('DELETE FROM "satış"')
            with pytest.raises(sqlite3.OperationalError):
                db.execute("SELECT load_extension('anything')")
    preview = a.preview(snapshot, settings, Control())
    assert preview["importable"]
    result = a.import_data(snapshot, settings, work, Control())
    frame = pl.read_parquet(result["path"]).select(expected.columns)
    # Structured ODS Decimal scale inferred from lexical input; native IPC exactly matches schema.
    assert frame.rows() == expected.rows()
    if adapter in ("ipc", "ipc_stream"):
        assert frame.schema == expected.schema
    root = tmp_path / "project"
    with closing(ProjectStore.create(root)) as store:
        d = store.publish_import(result, portable=True)
    with closing(ProjectStore.open(root)) as store:
        assert (
            pl.read_parquet(store.path(d["snapshot_uri"]))
            .select(expected.columns)
            .equals(frame)
        )
    assert path.read_bytes() == original
    assert not list(tmp_path.glob("*-wal")) and not list(tmp_path.glob("*-journal"))


def test_sqlite_wal_unsafe_source_rejected(tmp_path):
    path = tmp_path / "live.db"
    work = tmp_path / "work"
    work.mkdir()
    with closing(sqlite3.connect(path)) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE t(a)")
        db.execute("INSERT INTO t VALUES (1)")
        db.commit()
        before = path.read_bytes()
        with pytest.raises(ProjectError, match="WAL"):
            capture(path, work, any_format=True)
        assert path.read_bytes() == before


def test_sqlite_source_as_output_target_and_readonly_project_protected(tmp_path):
    path = tmp_path / "source.db"
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TABLE t(value INTEGER)")
        db.execute("INSERT INTO t VALUES (1)")
        db.commit()
    work = tmp_path / "work"
    work.mkdir()
    snapshot = capture(path, work, any_format=True)
    result = get_adapter("sqlite").import_data(
        snapshot, StructuredSettings(adapter_id="sqlite", sheet="t"), work, Control()
    )
    source = path.read_bytes()
    with pytest.raises((ProjectError, FileExistsError)):
        ProjectStore.create(path)
    with closing(ProjectStore.create(tmp_path / "project")) as writer:
        writer.publish_import(result)
        with closing(ProjectStore.open(writer.root)) as reader:
            assert reader.read_only
            with pytest.raises(ProjectError):
                reader.publish_import(result)
        with pytest.raises(ProjectError):
            writer.save_as(path)
    assert path.read_bytes() == source


def test_sqlite_quoted_table_without_rowid_and_no_virtual_tables(tmp_path):
    path = tmp_path / "source.db"
    work = tmp_path / "work"
    work.mkdir()
    with closing(sqlite3.connect(path)) as db:
        db.execute(
            'CREATE TABLE "odd""table" (key TEXT PRIMARY KEY, value INTEGER) WITHOUT ROWID'
        )
        db.executemany('INSERT INTO "odd""table" VALUES (?,?)', [("b", 2), ("a", 1)])
        db.commit()
    snapshot = capture(path, work, any_format=True)
    a = get_adapter("sqlite")
    settings = StructuredSettings(adapter_id="sqlite", sheet='odd"table')
    assert a.inspect(snapshot, settings, Control())["sheets"] == ['odd"table']
    result = a.import_data(snapshot, settings, work, Control())
    assert pl.read_parquet(result["path"]).select("key", "value").rows() == [
        ("a", 1),
        ("b", 2),
    ]
    with pytest.raises(ProjectError):
        a.import_data(
            snapshot,
            StructuredSettings(adapter_id="sqlite", sheet='"; DROP TABLE x;--'),
            work,
            Control(),
        )
