"""Expected values, immutable source handling, identities and transactional imports."""

import copy
import multiprocessing as mp
import signal
import subprocess
import sys
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import (
    Control,
    ImportSettings,
    capture,
    convert,
    import_snapshot,
    preview,
    suggest,
)
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import CRASH_POINTS, ProjectStore

FIXTURES = Path(__file__).parent / "fixtures/delimited"


def captured(tmp_path, text=None, source=None):
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    if source is None:
        source = tmp_path / "data.csv"
        source.write_text(text, encoding="utf8", newline="")
    return capture(source, work), work


def test_utf8_expected_values_types_and_distinct_equal_record_ids(tmp_path):
    source = FIXTURES / "reference_utf8.csv"
    original = source.read_bytes()
    snapshot, work = captured(tmp_path, source=source)
    settings = ImportSettings(
        delimiter=";",
        decimal=",",
        thousands=".",
        date_format="%d.%m.%Y",
        types=("text", "text", "decimal", "date", "text"),
    )
    sample = preview(snapshot, settings)
    result = import_snapshot(snapshot, settings, work)
    frame = pl.read_parquet(result["path"])
    assert frame["kimlik"].to_list() == ["0012", "0012", "999999999999999999999"]
    assert frame["ad"].to_list() == ["Çağrı", "Çağrı", "Işıl"]
    assert frame["tutar"].to_list() == [
        Decimal("1234.50"),
        Decimal("1234.50"),
        Decimal("0.25"),
    ]
    assert frame["tarih"].to_list() == [
        date(2026, 10, 6),
        date(2026, 10, 6),
        date(2026, 10, 7),
    ]
    assert frame["not"].to_list() == ["iki;parça", "iki;parça", "iki\nsatır"]
    assert frame["__vu_start_line"].to_list() == [2, 3, 4]
    assert frame["__vu_end_line"].to_list() == [2, 3, 5]
    assert (
        frame["__vu_row_id"].n_unique()
        == frame["__vu_source_record_id"].n_unique()
        == 3
    )
    assert sample["rows"][0][:4] == ["0012", "Çağrı", "1234.50", "2026-10-06"]
    assert source.read_bytes() == original


@pytest.mark.parametrize("encoding", ["cp1254", "iso8859-9"])
def test_old_turkish_encoding(tmp_path, encoding):
    snapshot, work = captured(tmp_path, source=FIXTURES / "reference_cp1254.csv")
    assert suggest(snapshot).encoding == "cp1254"
    result = import_snapshot(
        snapshot,
        ImportSettings(
            delimiter=";", encoding=encoding, decimal=",", types=("text", "decimal")
        ),
        work,
    )
    frame = pl.read_parquet(result["path"])
    assert frame["ad"].to_list() == ["İğdır Şişli", "Çağrı"]
    assert frame["tutar"].to_list() == [Decimal("12.75"), Decimal("0.50")]
    with pytest.raises(ProjectError, match="encoding"):
        preview(snapshot, ImportSettings(delimiter=";"))


def test_tsv_null_and_same_settings(tmp_path):
    snapshot, work = captured(tmp_path, source=FIXTURES / "reference.tsv")
    settings = ImportSettings(
        delimiter="\t", types=("text", "text", "float64"), null_markers=("NA",)
    )
    sample = preview(snapshot, settings)
    result = import_snapshot(snapshot, settings, work)
    assert sample["settings"] == result["settings"]
    assert pl.read_parquet(result["path"]).select("id", "ad", "puan").rows() == [
        ("0007", "Şule", 3.5),
        ("0008", "Özgür", None),
    ]


def test_header_names_and_no_header(tmp_path):
    snapshot, work = captured(tmp_path, ",ad,ad,__vu_row_id\na,b,c,d\n")
    sample = preview(snapshot, ImportSettings())
    assert sample["schema"]["names"] == ["Sütun_1", "ad", "ad_2", "__vu_row_id_2"]
    assert sample["schema"]["original_headers"] == ["", "ad", "ad", "__vu_row_id"]
    assert len(sample["schema"]["warnings"]) == 3
    result = import_snapshot(snapshot, ImportSettings(header_row=0), work)
    assert result["accepted"] == 2
    assert result["schema"]["names"] == ["Sütun_1", "Sütun_2", "Sütun_3", "Sütun_4"]


@pytest.mark.parametrize("text", ["", "\n", "a,b\n"])
def test_empty_no_success(tmp_path, text):
    snapshot, work = captured(tmp_path, text)
    with pytest.raises(ProjectError):
        import_snapshot(snapshot, ImportSettings(), work)


def test_quarantine_exact_count_reason_raw_and_source_ranges(tmp_path):
    snapshot, work = captured(
        tmp_path, 'id,tutar\na,1\nb,2,extra\nc,x\nd,3\n"unfinished\nstill\n'
    )
    with pytest.raises(ProjectError, match="Bozuk kayıt"):
        import_snapshot(snapshot, ImportSettings(types=("text", "int64")), work)
    settings = ImportSettings(types=("text", "int64"), bad_rows="quarantine")
    sample = preview(snapshot, settings)
    result = import_snapshot(snapshot, settings, work)
    assert result["accepted"] == 2 and result["bad_count"] == len(sample["bad"]) == 3
    bad = pl.read_parquet(result["quarantine"])
    assert bad["record_number"].to_list() == [3, 4, 6]
    assert bad["start_line"].to_list() == [3, 4, 6]
    assert bad["end_line"].to_list() == [3, 4, 7]
    assert bad["raw"].to_list() == ["b,2,extra\n", "c,x\n", '"unfinished\nstill\n']
    assert bad["source_record_id"].n_unique() == 3
    assert all(bad["reason"].to_list())
    assert "sütun 2" in bad["reason"][1]


def test_source_modified_after_preview_imports_explicit_immutable_copy(tmp_path):
    snapshot, work = captured(tmp_path, "id,ad\n001,Çağrı\n")
    before = preview(snapshot, ImportSettings())
    Path(snapshot["original"]).write_text("id,ad\n002,Ece\n003,Ada\n")
    result = import_snapshot(snapshot, ImportSettings(), work)
    assert before["capture"]["fingerprint"] == result["capture"]["fingerprint"]
    assert pl.read_parquet(result["path"])["id"].to_list() == ["001"]
    store = ProjectStore.create(tmp_path / "project")
    try:
        dataset = store.publish_import(result, portable=True)
        assert store.source_statuses()[dataset["source_id"]] == "changed"
        assert (
            store.path(store.state["sources"][0]["copy_uri"]).read_text()
            == "id,ad\n001,Çağrı\n"
        )
    finally:
        store.close()


def test_source_modified_during_capture_rejected(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    source = tmp_path / "data.csv"
    source.write_text("id\nold\n")

    def mutate(point):
        source.write_text("id\nnew\n")

    with pytest.raises(ProjectError, match="sırasında değişti"):
        capture(source, work, checkpoint=mutate)


def test_capture_tampered_during_read_no_mixed_success(tmp_path):
    snapshot, work = captured(tmp_path, "id\n" + "old\n" * 5000)

    class Mutating(Control):
        calls = 0

        def check(self):
            super().check()
            self.calls += 1
            if self.calls == 1000:
                Path(snapshot["path"]).write_text("id\n" + "new\n" * 5000)

    with pytest.raises(ProjectError, match="kopyası değişmiş"):
        import_snapshot(snapshot, ImportSettings(), work, Mutating())


def test_cancel_parse_and_publication_preserve_active_and_source(tmp_path):
    snapshot, work = captured(tmp_path, "id\n" + "001\n" * 5000)
    original = Path(snapshot["original"]).read_bytes()
    cancel = mp.get_context("spawn").Event()
    cancel.set()
    with pytest.raises(Canceled):
        import_snapshot(snapshot, ImportSettings(), work, Control(cancel))
    result = import_snapshot(snapshot, ImportSettings(), work)
    store = ProjectStore.create(tmp_path / "project")
    active = store.path("ACTIVE").read_bytes()
    state = copy.deepcopy(store.state)

    def canceled(point):
        if point == "metadata_committed":
            raise Canceled()

    with pytest.raises(Canceled):
        store.publish_import(result, checkpoint=canceled)
    assert store.state == state and store.path("ACTIVE").read_bytes() == active
    assert Path(snapshot["original"]).read_bytes() == original
    store.close()
    reopened = ProjectStore.open(tmp_path / "project")
    assert reopened.state == state
    reopened.close()


def test_roundtrip_metadata_quarantine_types_and_help_seed(tmp_path):
    snapshot, work = captured(tmp_path, "id;v\n001;2,5\nx;no\n")
    result = import_snapshot(
        snapshot,
        ImportSettings(
            delimiter=";", decimal=",", types=("text", "decimal"), bad_rows="quarantine"
        ),
        work,
    )
    store = ProjectStore.create(tmp_path / "project")
    store.state["seed"] = 42
    store.state["help_preferences"] = {"depth": 2}
    store.publish_import(result, portable=True)
    expected = copy.deepcopy(store.state)
    store.close()
    reopened = ProjectStore.open(tmp_path / "project")
    assert reopened.state == expected
    d = reopened.state["datasets"][0]
    assert d["import_metadata"]["row_count"] == d["import_metadata"]["bad_count"] == 1
    assert d["import_metadata"]["columns"][0]["type"] == "text"
    assert pl.read_parquet(reopened.path(d["snapshot_uri"]))["id"].to_list() == ["001"]
    assert pl.read_parquet(reopened.path(d["quarantine_uri"]))["raw"].to_list() == [
        "x;no\n"
    ]
    assert reopened.state["operations"][0]["seed"] == 42
    reopened.close()


@pytest.mark.parametrize(
    "kind,value",
    [
        ("int64", "0012"),
        ("int64", "9223372036854775808"),
        ("float64", "999999999999999999999"),
        ("decimal", "1.0000001"),
        ("decimal", "100000000000000000000000000000000"),
        ("float64", "1e9999"),
    ],
)
def test_lossy_numeric_conversion_rejected(kind, value):
    with pytest.raises(ValueError):
        convert(value, kind, ImportSettings())
    assert convert(value, "text", ImportSettings()) == value


def test_timezone_explicit_and_dst_rejected():
    settings = ImportSettings(date_format="%Y-%m-%d %H:%M", timezone="Europe/Istanbul")
    assert (
        convert("2026-10-06 12:00", "datetime", settings).utcoffset().total_seconds()
        == 10800
    )
    assert (
        convert("2026-10-06 12:00", "datetime", replace(settings, timezone="")).tzinfo
        is None
    )
    with pytest.raises(ValueError, match="belirsiz"):
        convert(
            "2026-10-25 02:30", "datetime", replace(settings, timezone="Europe/Berlin")
        )


def test_preview_bounded_and_disk_time_record_limits(tmp_path):
    snapshot, work = captured(tmp_path, "id\n" + "001\n" * 201)
    sample = preview(snapshot, ImportSettings())
    assert len(sample["rows"]) == 200 and sample["limited"]
    assert sample["schema"]["types"] == ("text",) and sample["suggestions"] == ["text"]
    with pytest.raises(ProjectError, match="disk bütçesi"):
        import_snapshot(
            snapshot,
            ImportSettings(),
            work,
            Control(
                budget=replace(ComputeBudget(), temp_disk_bytes=1, reserve_disk_bytes=1)
            ),
        )
    Path(snapshot["path"]).write_text("id\n" + "x" * (1024**2 + 1))
    with pytest.raises(ProjectError, match="1 MiB"):
        preview(snapshot, ImportSettings())


@pytest.mark.parametrize(
    "point", ("import_copy_begin", "import_copy_chunk") + CRASH_POINTS
)
def test_sigkill_import_publication_recovers_whole_dataset_or_previous(tmp_path, point):
    snapshot, work = captured(tmp_path, "id,v\n001,1\n002,2\n")
    store = ProjectStore.create(tmp_path / "project")
    previous = store.commit_id
    store.close()
    script = """import os,signal,sys
from pathlib import Path
from veri_ufku.importers.delimited import capture,ImportSettings,import_snapshot
from veri_ufku.storage.project_store import ProjectStore
store=ProjectStore.open(sys.argv[1])
work=Path(sys.argv[2]); work.mkdir()
result=import_snapshot(capture(sys.argv[3],work),ImportSettings(),work)
def die(point):
    if point==sys.argv[4]: os.kill(os.getpid(),signal.SIGKILL)
store.publish_import(result,portable=True,checkpoint=die)
"""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(tmp_path / "project"),
            str(tmp_path / "child"),
            snapshot["original"],
            point,
        ],
        capture_output=True,
        timeout=25,
    )
    assert completed.returncode == -signal.SIGKILL, completed.stderr
    reopened = ProjectStore.open(tmp_path / "project", recover_lock=True)
    if point in {"pointer_replaced", "root_synced"}:
        assert len(reopened.state["datasets"]) == 1
        d = reopened.state["datasets"][0]
        assert pl.read_parquet(reopened.path(d["snapshot_uri"]))["id"].to_list() == [
            "001",
            "002",
        ]
    else:
        assert reopened.commit_id == previous and not reopened.state["datasets"]
    reopened.close()


def test_bad_record_beyond_preview_stops_full_import(tmp_path):
    snapshot, work = captured(tmp_path, "id,v\n" + "001,1\n" * 200 + "x,bad\n")
    settings = ImportSettings(types=("text", "int64"))
    assert preview(snapshot, settings)["bad"] == []
    with pytest.raises(ProjectError, match="Bozuk kayıt: 202"):
        import_snapshot(snapshot, settings, work)


def test_decimal_int_limits_and_thousands_are_exact():
    settings = ImportSettings(decimal=",", thousands=".")
    assert (
        convert("9.223.372.036.854.775.807", "int64", settings) == 9223372036854775807
    )
    assert convert(
        "99999999999999999999999999999999,000001", "decimal", settings
    ) == Decimal("99999999999999999999999999999999.000001")
    with pytest.raises(ValueError, match="Binlik"):
        convert("12.34,50", "decimal", settings)
    with pytest.raises(ValueError, match="alt sınırı"):
        convert("1e-9999", "float64", ImportSettings())


def test_schema1_fixture_open_does_not_migrate_until_explicit_save(tmp_path):
    import sqlite3

    from veri_ufku.storage.project_model import decode, digest, encode

    fixture = decode(
        (Path(__file__).parent / "fixtures/projects/schema1.json").read_bytes()
    )
    store = ProjectStore.create(tmp_path / "legacy")
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
            format_version=1,
        )
    )
    (root / "ACTIVE").write_bytes(pointer)
    before_db = (root / "metadata.sqlite").read_bytes()
    reader = ProjectStore.open(root, writable=False)
    assert reader.read_only and reader.state["seed"] == 42
    reader.close()
    assert (root / "ACTIVE").read_bytes() == pointer
    assert (root / "metadata.sqlite").read_bytes() == before_db
    writer = ProjectStore.open(root)
    assert not writer.read_only and writer.manifest["format_version"] == 1
    assert (root / "ACTIVE").read_bytes() == pointer
    writer.save()
    assert writer.manifest["format_version"] == 7
    assert writer.manifest["environment"]["application"] == "0.1.0"
    assert writer.manifest["migration"][-1] == dict(
        from_version=1, to_version=7, original_commit="legacy-v1"
    )
    assert (commit / "manifest.json").read_bytes() == raw
    writer.close()


def test_completed_worker_artifact_tamper_prevents_publication(tmp_path):
    snapshot, work = captured(tmp_path, "id,v\n001,1\n")
    result = import_snapshot(snapshot, ImportSettings(), work)
    frame = pl.read_parquet(result["path"])
    frame.with_columns(pl.lit("999").alias("id")).write_parquet(result["path"])
    store = ProjectStore.create(tmp_path / "project")
    active = store.path("ACTIVE").read_bytes()
    try:
        with pytest.raises(ProjectError, match="kopyası değişmiş"):
            store.publish_import(result)
        assert not store.state["datasets"]
        assert store.path("ACTIVE").read_bytes() == active
    finally:
        store.close()
