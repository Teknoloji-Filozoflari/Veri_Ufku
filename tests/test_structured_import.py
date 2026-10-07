"""Independent reference values, native precision, unsafe files and snapshot contracts."""

import copy
from contextlib import closing
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

import polars as pl
import pytest

from veri_ufku.importers.delimited import Control, capture
from veri_ufku.importers.native import StructuredSettings, describe, restore
from veri_ufku.importers.registry import detect, get_adapter
from veri_ufku.importers.xlsx import excel_date
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore

FIXTURES = Path(__file__).parent / "fixtures/structured"


def captured(tmp_path, source=None, text=None, suffix=".json"):
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    if source is None:
        source = tmp_path / ("source" + suffix)
        source.write_text(text, encoding="utf8")
    snap = capture(source, work, any_format=True)
    snap["adapter_id"] = detect(snap)
    return snap, work


def run(snapshot, settings, work):
    result = get_adapter(settings.adapter_id).import_data(
        snapshot, settings, work, Control()
    )
    return result, pl.read_parquet(result["path"])


def test_nested_selection_decimal_missing_null_and_roundtrip(tmp_path):
    source = FIXTURES / "nested.json"
    original = source.read_bytes()
    snap, work = captured(tmp_path, source)
    adapter = get_adapter("json")
    settings = StructuredSettings(record_path="/payload/records")
    assert (
        "/payload/records" in adapter.inspect(snap, settings, Control())["record_paths"]
    )
    preview = adapter.preview(snap, settings)
    assert preview["importable"] and preview["examined"] == 2
    assert preview["diagnostics"]["fields"]["optional"]["missing"] == 1
    assert preview["diagnostics"]["fields"]["optional"]["explicit_null"] == 1
    result, frame = run(snap, settings, work)
    assert frame["money"].to_list() == [
        Decimal("12345678901234567890.1200"),
        Decimal("0.0100"),
    ]
    assert frame.schema["money"] == pl.Decimal(24, 4)
    assert frame["id"].to_list() == ["001", "001"]
    assert frame["address"].to_list() == [{"city": "İzmir"}] * 2
    assert (
        frame["__vu_row_id"].n_unique()
        == frame["__vu_source_record_id"].n_unique()
        == 2
    )
    assert frame["__vu_missing_fields"].to_list() == [[], ["optional"]]
    with closing(ProjectStore.create(tmp_path / "project")) as store:
        store.publish_import(result)
        before = copy.deepcopy(store.state)
    with closing(ProjectStore.open(tmp_path / "project")) as store:
        assert store.state == before
        operation = store.state["operations"][-1]
        assert operation["capability_id"] == "import.json"
        assert operation["diagnostics"]["scope"] == "full"
        assert operation["provenance"]["source_snapshot_ids"] == [
            result["source_snapshot_id"]
        ]
    assert source.read_bytes() == original


def test_flatten_is_independent_of_explosion_cartesian_lineage(tmp_path):
    snap, work = captured(tmp_path, FIXTURES / "nested.json")
    settings = StructuredSettings(record_path="/payload/records", flatten=True)
    _, frame = run(snap, settings, work)
    assert frame.height == 2 and "/address/city" in frame.columns
    assert frame.schema["/items"] == pl.List(pl.Int64)
    expanded = replace(settings, expand_lists=("/items", "/tags"))
    preview = get_adapter("json").preview(snap, expanded)
    assert preview["diagnostics"]["output_rows"] == 7
    assert preview["diagnostics"]["max_expansion"] == 6
    _, frame = run(snap, expanded, work)
    assert frame.height == frame["__vu_row_id"].n_unique() == 7
    assert frame["__vu_source_record_id"].n_unique() == 2
    assert frame["/items"].to_list() == [1, 1, 1, 2, 2, 2, None]
    assert frame["/tags"].to_list() == ["a", "b", "c", "a", "b", "c", None]
    assert frame["__vu_expansion_index"].n_unique() == 7


def test_jsonl_bad_location_reordered_keys_and_late_schema(tmp_path):
    snap, work = captured(tmp_path, FIXTURES / "records.ndjson")
    settings = StructuredSettings(adapter_id="jsonl", bad_rows="quarantine")
    preview = get_adapter("jsonl").preview(snap, settings)
    assert preview["bad"][0]["start_line"] == 3
    assert preview["bad"][0]["locator"] == "line:3"
    result, frame = run(snap, settings, work)
    assert result["bad_count"] == 1 and result["accepted"] == 3
    assert frame["id"].to_list() == ["001", "002", "003"]
    assert frame["x"].to_list() == [1, 2, None]
    assert frame["late"].to_list() == [None, True, None]
    bad = pl.read_parquet(result["quarantine"])
    assert bad["locator"].to_list() == ["line:3"] and bad["reason"][0]
    with pytest.raises(ProjectError, match="line:3"):
        run(snap, replace(settings, bad_rows="stop"), work)


@pytest.mark.parametrize(
    "text",
    [
        '[{"x":1},{"x":"1"}]',
        '[{"x":123456789012345678901234567890123456789}]',
        '[{"x":[1,"a"]}]',
    ],
)
def test_mixed_precision_requires_explicit_lossless_policy(tmp_path, text):
    snap, work = captured(tmp_path, text=text)
    settings = StructuredSettings()
    assert not get_adapter("json").preview(snap, settings)["importable"]
    with pytest.raises(ProjectError, match="Karışık"):
        run(snap, settings, work)
    result, frame = run(snap, replace(settings, mixed_policy="json_text"), work)
    assert result["accepted"] > 0
    if text.startswith('[{"x":1},'):
        assert frame["x"].to_list() == ["1", '"1"']
    elif "123456" in text:
        assert frame["x"][0] == "123456789012345678901234567890123456789"
    else:
        assert frame["x"].to_list() == [["1", '"a"']]


def test_big_integer_exact_decimal_and_user_type(tmp_path):
    snap, work = captured(
        tmp_path, text='[{"id":"001","n":18446744073709551615},{"id":"002","n":0}]'
    )
    _, frame = run(snap, StructuredSettings(), work)
    assert frame["n"].to_list() == [Decimal("18446744073709551615"), Decimal(0)]
    assert frame.schema["n"] == pl.Decimal(20, 0)
    _, frame = run(
        snap, StructuredSettings(types=("text", "text"), column_names=("id", "n")), work
    )
    assert frame["n"].to_list() == ["18446744073709551615", "0"]


def test_excel_sheets_range_blank_and_exact_values(tmp_path):
    snap, work = captured(tmp_path, FIXTURES / "workbook.xlsx")
    adapter = get_adapter("xlsx")
    settings = StructuredSettings(adapter_id="xlsx", sheet="Satış")
    choices = adapter.inspect(snap, settings, Control())
    assert (
        choices["sheets"] == ["Satış", "Diğer", "Formüller", "Birleşik"]
        and choices["date_system"] == "1900"
    )
    preview = adapter.preview(snap, settings)
    assert preview["examined"] == 3
    _, frame = run(snap, settings, work)
    assert frame["id"].to_list() == ["001", None, "002"]
    assert frame["tutar"].to_list() == [
        Decimal("12345678901234567890.1200"),
        None,
        Decimal("0.0100"),
    ]
    assert frame["tarih"].to_list() == [datetime(2024, 1, 1), None, None]
    assert frame.schema["tarih"] == pl.Datetime("us")
    _, frame = run(snap, replace(settings, sheet="Diğer"), work)
    assert frame["başlık"].to_list() == ["İkinci"]
    _, frame = run(snap, replace(settings, blank_rows="skip"), work)
    assert frame.height == 2
    _, frame = run(snap, replace(settings, header_row=0, cell_range="A2:B2"), work)
    assert frame["A"].to_list() == ["001"] and frame.schema["B"] == pl.Decimal(24, 4)


def test_excel_formulas_never_evaluated_or_invented(tmp_path):
    snap, work = captured(tmp_path, FIXTURES / "workbook.xlsx")
    settings = StructuredSettings(adapter_id="xlsx", sheet="Formüller")
    _, frame = run(snap, settings, work)
    assert frame["hesap"].to_list() == ["=1+1", "=2+2"]
    _, frame = run(snap, replace(settings, formulas="text"), work)
    assert frame["hesap"].to_list() == ["1+1", "2+2"]
    with pytest.raises(ProjectError, match="önbelleği yok"):
        run(snap, replace(settings, formulas="cached"), work)
    result, frame = run(
        snap, replace(settings, formulas="cached", bad_rows="quarantine"), work
    )
    assert frame["hesap"].to_list() == [2] and result["bad_count"] == 1
    assert pl.read_parquet(result["quarantine"])["locator"].to_list() == [
        "Formüller!A3:A3"
    ]


def test_excel_merge_original_empty_headers_and_1904(tmp_path):
    snap, work = captured(tmp_path, FIXTURES / "workbook.xlsx")
    settings = StructuredSettings(adapter_id="xlsx", sheet="Birleşik")
    with pytest.raises(ProjectError, match="birleştirilmiş"):
        run(snap, settings, work)
    result, frame = run(snap, replace(settings, merged_cells="anchor"), work)
    assert result["schema"]["original_headers"] == ["", ""]
    assert frame["Sütun_1"].to_list() == ["sol"] and frame["Sütun_2"].to_list() == [
        None
    ]
    snap, work = captured(tmp_path, FIXTURES / "workbook1904.xlsx")
    _, frame = run(snap, StructuredSettings(adapter_id="xlsx", sheet="Satış"), work)
    assert frame["tarih"][0] == datetime(2028, 1, 2)
    assert excel_date(Decimal(0), True) == datetime(1904, 1, 1)
    with pytest.raises(ProjectError, match="1900"):
        excel_date(Decimal(60), False)
    with pytest.raises(ProjectError, match="mikrosaniye"):
        excel_date(Decimal("1.0000000000000001"), False)


def test_native_parquet_nullable_temporal_precision_nested_and_roundtrip(tmp_path):
    source = tmp_path / "values.data"
    native = pl.DataFrame(
        {
            "nullable": pl.Series([1, None], dtype=pl.Int16),
            "date": pl.Series([date(2026, 10, 6), None], dtype=pl.Date),
            "time": pl.Series([1791234000000000001, None], dtype=pl.Int64).cast(
                pl.Datetime("ns", "Europe/Istanbul")
            ),
            "decimal": pl.Series(
                [Decimal("12345678901234567890.1200"), None], dtype=pl.Decimal(24, 4)
            ),
            "uint": pl.Series([18446744073709551615, None], dtype=pl.UInt64),
            "nested": pl.Series(
                [{"x": [1, 2]}, {"x": None}], dtype=pl.Struct({"x": pl.List(pl.Int8)})
            ),
            "float": pl.Series([float("nan"), float("inf")], dtype=pl.Float64),
        }
    )
    native.write_parquet(source)
    snap, work = captured(tmp_path, source)
    assert detect(snap) == "parquet"
    settings = StructuredSettings(adapter_id="parquet")
    preview = get_adapter("parquet").preview(snap, settings)
    assert preview["diagnostics"]["fields"]["float"] == dict(null=0, nan=1, inf=1)
    result, frame = run(snap, settings, work)
    assert frame.select(native.columns).equals(native)
    assert frame["time"].cast(pl.Int64).to_list() == [1791234000000000001, None]
    with closing(ProjectStore.create(tmp_path / "project")) as store:
        store.publish_import(result)
    with closing(ProjectStore.open(tmp_path / "project")) as store:
        assert store.state["operations"][-1]["capability_id"] == "import.parquet"
    for dtype in native.schema.values():
        assert restore(describe(dtype)) == dtype


def test_unsupported_parquet_type_and_content_validation(tmp_path):
    source = tmp_path / "unsupported.parquet"
    pl.DataFrame({"x": pl.Series([1], dtype=pl.Duration("ns"))}).write_parquet(source)
    snap, work = captured(tmp_path, source)
    with pytest.raises(ProjectError, match="korunamıyor"):
        run(snap, StructuredSettings(adapter_id="parquet"), work)
    bad = tmp_path / "fake.parquet"
    bad.write_bytes(b"no")
    with pytest.raises(ProjectError, match="kısa"):
        get_adapter("parquet").preview(
            captured(tmp_path, bad)[0], StructuredSettings(adapter_id="parquet")
        )
    snap, _ = captured(tmp_path, text='[{"x":1}]', suffix=".xlsx")
    assert detect(snap) == "json"
    with pytest.raises(ProjectError, match="ZIP"):
        get_adapter("xlsx").preview(snap, StructuredSettings(adapter_id="xlsx"))


@pytest.mark.parametrize(
    "name", ["../outside.xml", "/absolute.xml", "a/../../bad.xml", "a\\bad.xml"]
)
def test_xlsx_path_traversal_refused_without_extraction(tmp_path, name):
    source = tmp_path / "attack.xlsx"
    with ZipFile(source, "w") as z:
        z.writestr(name, "bad")
    snap, work = captured(tmp_path, source)
    with pytest.raises(ProjectError):
        run(snap, StructuredSettings(adapter_id="xlsx"), work)
    assert not (tmp_path / "outside.xml").exists()


def test_changed_original_uses_declared_immutable_snapshot_and_cancel(tmp_path):
    snap, work = captured(tmp_path, text='[{"x":1},{"x":1}]')
    adapter = get_adapter("json")
    settings = StructuredSettings()
    adapter.preview(snap, settings)
    Path(snap["original"]).write_text('[{"x":2}]')
    result, frame = run(snap, settings, work)
    assert (
        frame["x"].to_list() == [1, 1]
        and frame["__vu_source_record_id"].n_unique() == 2
    )
    assert result["capture"]["fingerprint"] == snap["fingerprint"]

    class Cancel:
        def is_set(self):
            return True

    with pytest.raises(Canceled):
        adapter.import_data(snap, settings, work, Control(Cancel()))
    Path(snap["path"]).write_text('[{"x":9}]')
    with pytest.raises(ProjectError, match="kopya"):
        run(snap, settings, work)


@pytest.mark.parametrize("pointer", ["x", "/bad~2escape", "/~"])
def test_invalid_json_pointer_rejected(pointer):
    with pytest.raises(ProjectError):
        StructuredSettings(record_path=pointer)


def test_full_jsonl_profile_catches_type_and_new_field_after_preview(tmp_path):
    text = '{"id":"001","x":1}\n' * 200 + '{"id":"002","x":"bad","late":true}\n'
    snap, work = captured(tmp_path, text=text, suffix=".ndjson")
    adapter = get_adapter("jsonl")
    settings = StructuredSettings(adapter_id="jsonl")
    sample = adapter.preview(snap, settings)
    assert sample["importable"] and len(sample["rows"]) == 200
    with pytest.raises(ProjectError, match="Karışık"):
        run(snap, settings, work)
    with pytest.raises(ProjectError, match="önizlemeden farklı"):
        run(
            snap,
            replace(settings, types=("text", "int64"), column_names=("id", "x")),
            work,
        )


@pytest.mark.parametrize(
    "attack", ["macro", "entity", "duplicate", "oversize", "symlink"]
)
def test_xlsx_unsafe_container_support_limits(tmp_path, attack):
    import stat
    import warnings
    from zipfile import ZipInfo

    source = tmp_path / "unsafe.xlsx"
    with ZipFile(FIXTURES / "workbook.xlsx") as original:
        parts = {name: original.read(name) for name in original.namelist()}
    if attack == "macro":
        parts["xl/vbaProject.bin"] = b"no execution"
    if attack == "entity":
        parts["xl/workbook.xml"] = (
            b'<!DOCTYPE workbook [<!ENTITY x "boom">]><workbook>&x;</workbook>'
        )
    if attack == "oversize":
        parts["oversize.xml"] = b"x" * 1024
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with ZipFile(source, "w") as z:
            for name, value in parts.items():
                z.writestr(name, value)
            if attack == "duplicate":
                z.writestr("xl/workbook.xml", parts["xl/workbook.xml"])
            if attack == "symlink":
                info = ZipInfo("link.xml")
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(info, "/outside")
    snap, work = captured(tmp_path, source)
    settings = StructuredSettings(adapter_id="xlsx")
    from veri_ufku.importers.xlsx import Workbook

    if attack == "oversize":
        from veri_ufku.domain.contracts import ComputeBudget

        with pytest.raises(ProjectError, match="boyut"):
            Workbook(
                snap["path"],
                Control(budget=replace(ComputeBudget(), temp_disk_bytes=100)),
            )
    else:
        with pytest.raises(ProjectError):
            run(snap, settings, work)


def test_json_duplicate_keys_empty_object_and_array_intermediate_boundary(tmp_path):
    snap, work = captured(tmp_path, text='[{"x":1,"x":2}]')
    with pytest.raises(ProjectError, match="tekrar"):
        run(snap, StructuredSettings(), work)
    snap, work = captured(tmp_path, text='[{"x":{}}]')
    with pytest.raises(ProjectError, match="Karışık"):
        run(snap, StructuredSettings(), work)
    _, frame = run(snap, StructuredSettings(mixed_policy="json_text"), work)
    assert frame["x"].to_list() == ["{}"]
    snap, work = captured(tmp_path, text='[{"items":[{"x":[1,2]}]}]')
    with pytest.raises(ProjectError, match="ara listeden"):
        run(snap, StructuredSettings(expand_lists=("/items/0/x",)), work)


@pytest.mark.parametrize(
    "point",
    [
        "import_copy_begin",
        "artifact_written",
        "metadata_committed",
        "manifest_written",
        "pointer_replaced",
        "root_synced",
    ],
)
def test_native_sigkill_publication_recovers_complete_version(tmp_path, point):
    import signal
    import subprocess
    import sys

    store = ProjectStore.create(tmp_path / "project")
    previous = store.commit_id
    store.close()
    script = """import sys,os,signal
from pathlib import Path
from veri_ufku.importers.delimited import capture,Control
from veri_ufku.importers.native import StructuredSettings
from veri_ufku.importers.registry import get_adapter
from veri_ufku.storage.project_store import ProjectStore
work=Path(sys.argv[2]);work.mkdir()
result=get_adapter('json').import_data(capture(sys.argv[3],work,any_format=True),StructuredSettings(record_path='/payload/records'),work,Control())
store=ProjectStore.open(sys.argv[1])
def die(point):
    if point==sys.argv[4]:os.kill(os.getpid(),signal.SIGKILL)
store.publish_import(result,portable=True,checkpoint=die)
"""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(tmp_path / "project"),
            str(tmp_path / "child"),
            str(FIXTURES / "nested.json"),
            point,
        ],
        capture_output=True,
        timeout=25,
    )
    assert completed.returncode == -signal.SIGKILL, completed.stderr
    with closing(ProjectStore.open(tmp_path / "project", recover_lock=True)) as store:
        if point in ("pointer_replaced", "root_synced"):
            dataset = store.state["datasets"][0]
            assert pl.read_parquet(store.path(dataset["snapshot_uri"]))["money"][
                0
            ] == Decimal("12345678901234567890.1200")
            assert dataset["import_metadata"]["settings"]["adapter_id"] == "json"
        else:
            assert store.commit_id == previous and not store.state["datasets"]


def test_schema2_open_unchanged_explicit_migration_to_current(tmp_path):
    import sqlite3

    from veri_ufku.storage.project_model import decode, digest, encode

    fixture = decode(
        (Path(__file__).parent / "fixtures/projects/schema2.json").read_bytes()
    )
    store = ProjectStore.create(tmp_path / "legacy2")
    root = store.root
    store.close()
    raw = encode(fixture)
    commit = root / "commits" / fixture["commit_id"]
    commit.mkdir()
    (commit / "manifest.json").write_bytes(raw)
    with sqlite3.connect(root / "metadata.sqlite") as db:
        db.execute(
            "INSERT INTO commits VALUES (?,?,?)",
            (fixture["commit_id"], digest(raw), raw),
        )
    pointer = encode(
        dict(
            commit_id=fixture["commit_id"],
            manifest_sha256=digest(raw),
            format_version=2,
        )
    )
    (root / "ACTIVE").write_bytes(pointer)
    before = (root / "metadata.sqlite").read_bytes()
    with closing(ProjectStore.open(root, writable=False)) as reader:
        assert reader.manifest["format_version"] == 2
    assert (root / "ACTIVE").read_bytes() == pointer and (
        root / "metadata.sqlite"
    ).read_bytes() == before
    with closing(ProjectStore.open(root)) as writer:
        writer.save()
        assert writer.manifest["format_version"] == 5
        assert writer.manifest["migration"][-1] == dict(
            from_version=2, to_version=5, original_commit="legacy-v2"
        )
    assert (commit / "manifest.json").read_bytes() == raw


def test_schema3_open_unchanged_explicit_migration_to_current(tmp_path):
    import sqlite3

    from veri_ufku.storage.project_model import decode, digest, encode

    fixture = decode(
        (Path(__file__).parent / "fixtures/projects/schema3.json").read_bytes()
    )
    store = ProjectStore.create(tmp_path / "legacy3")
    root = store.root
    store.close()
    raw = encode(fixture)
    commit = root / "commits" / fixture["commit_id"]
    commit.mkdir()
    (commit / "manifest.json").write_bytes(raw)
    with sqlite3.connect(root / "metadata.sqlite") as db:
        db.execute(
            "INSERT INTO commits VALUES (?,?,?)",
            (fixture["commit_id"], digest(raw), raw),
        )
    pointer = encode(
        dict(
            commit_id=fixture["commit_id"],
            manifest_sha256=digest(raw),
            format_version=3,
        )
    )
    (root / "ACTIVE").write_bytes(pointer)
    before = (root / "metadata.sqlite").read_bytes()
    with closing(ProjectStore.open(root, writable=False)) as reader:
        assert reader.manifest["format_version"] == 3
    assert (root / "ACTIVE").read_bytes() == pointer and (
        root / "metadata.sqlite"
    ).read_bytes() == before
    with closing(ProjectStore.open(root)) as writer:
        writer.save()
        assert writer.manifest["format_version"] == 5
        assert writer.manifest["migration"][-1] == dict(
            from_version=3, to_version=5, original_commit="legacy-v3"
        )
    assert (commit / "manifest.json").read_bytes() == raw


def test_copy_mutation_during_json_read_cannot_produce_success(tmp_path):
    snap, work = captured(tmp_path, text='[{"x":1}]' * 1)

    class Mutating(Control):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def check(self):
            super().check()
            self.calls += 1
            if self.calls == 5:
                Path(snap["path"]).write_text('[{"x":9}]')

    with pytest.raises(ProjectError):
        get_adapter("json").import_data(snap, StructuredSettings(), work, Mutating())


def test_explicit_datetime_timezone_and_lossy_number_guards(tmp_path):
    snap, work = captured(tmp_path, text='[{"time":"2026-10-06 12:30:00"}]')
    settings = StructuredSettings(
        types=("datetime",),
        column_names=("time",),
        date_format="%Y-%m-%d %H:%M:%S",
        timezone="Europe/Istanbul",
    )
    _, frame = run(snap, settings, work)
    assert frame["time"].cast(pl.Int64).to_list() == [1791279000000000]
    assert frame.schema["time"] == pl.Datetime("us", "Europe/Istanbul")
    with pytest.raises(ProjectError, match="timezone"):
        restore({"kind": "Datetime", "unit": "ns", "zone": "Invalid/Zone"})
    snap, work = captured(tmp_path, text='[{"x":9007199254740993}]')
    settings = StructuredSettings(types=("float64",), column_names=("x",))
    preview = get_adapter("json").preview(snap, settings)
    assert not preview["importable"] and preview["bad"]
    with pytest.raises(ProjectError):
        run(snap, settings, work)
