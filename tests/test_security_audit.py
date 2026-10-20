"""Phase26 hostile synthetic inputs and preservation of known-good state."""

import copy
import errno
import os
import signal
import sqlite3
import subprocess
import sys
import zipfile
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import pytest
from test_projects import populate

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Control
from veri_ufku.importers.native import StructuredSettings
from veri_ufku.importers.ods import document
from veri_ufku.importers.sqlite_source import records
from veri_ufku.logging_setup import EventLog
from veri_ufku.operations.formula import parse
from veri_ufku.storage.project_model import (
    SCHEMA_VERSION,
    ProjectError,
    decode,
    digest,
    encode,
)
from veri_ufku.storage.project_store import CRASH_POINTS, ProjectStore


@pytest.mark.parametrize("version", [4, 5, 6])
def test_old_schema_fixture_open_migrate_retains_backup(tmp_path, version):
    manifest = decode(
        (Path(__file__).parent / f"fixtures/projects/schema{version}.json").read_bytes()
    )
    root = tmp_path / "legacy"
    with closing(ProjectStore.create(root)):
        pass
    raw = encode(manifest)
    commit = root / "commits" / manifest["commit_id"]
    commit.mkdir()
    (commit / "manifest.json").write_bytes(raw)
    with sqlite3.connect(root / "metadata.sqlite") as db:
        db.execute(
            "INSERT INTO commits VALUES (?,?,?)",
            (manifest["commit_id"], digest(raw), raw),
        )
    pointer = encode(
        dict(
            commit_id=manifest["commit_id"],
            format_version=version,
            manifest_sha256=digest(raw),
        )
    )
    (root / "ACTIVE").write_bytes(pointer)
    db_before = (root / "metadata.sqlite").read_bytes()
    with closing(ProjectStore.open(root, writable=False)) as reader:
        assert reader.manifest["format_version"] == version
    assert (root / "ACTIVE").read_bytes() == pointer
    assert (root / "metadata.sqlite").read_bytes() == db_before
    with closing(ProjectStore.open(root)) as writer:
        writer.save()
        assert writer.manifest["format_version"] == SCHEMA_VERSION
        assert writer.manifest["migration"][-1] == dict(
            from_version=version,
            to_version=SCHEMA_VERSION,
            original_commit=manifest["commit_id"],
        )
        assert writer.state == manifest["state"]
    assert (commit / "manifest.json").read_bytes() == raw
    with sqlite3.connect(root / "metadata.sqlite") as db:
        assert db.execute(
            "SELECT payload FROM commits WHERE commit_id=?", (manifest["commit_id"],)
        ).fetchone() == (raw,)


@pytest.mark.parametrize("link", ["symlink", "hardlink"])
def test_log_link_cannot_modify_other_file_or_permissions(tmp_path, link):
    target = tmp_path / "sentinel"
    target.write_bytes(b"PRIVATE SYNTHETIC DATA")
    target.chmod(0o644)
    folder = tmp_path / "log"
    folder.mkdir()
    path = folder / "application.log"
    if link == "symlink":
        path.symlink_to(target)
    else:
        os.link(target, path)
    with pytest.raises(OSError):
        EventLog(folder)
    assert target.read_bytes() == b"PRIVATE SYNTHETIC DATA"
    assert target.stat().st_mode & 0o777 == 0o644


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-16-be", "utf-32"])
def test_ods_encoded_entity_rejected_without_expansion(tmp_path, encoding):
    file = tmp_path / "hostile.ods"
    xml = (
        '<?xml version="1.0" encoding="'
        + encoding
        + '"?><!DOCTYPE root [<!ENTITY marker "SYNTHETIC">]><root>&marker;</root>'
    )
    with zipfile.ZipFile(file, "w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet")
        archive.writestr("content.xml", xml.encode(encoding))
    original = file.read_bytes()
    with pytest.raises(ProjectError, match="DTD/entity"):
        document(file)
    assert file.read_bytes() == original


@pytest.mark.parametrize("name", ["../escape", "/absolute", "folder\\escape"])
def test_ods_container_path_rejected_without_extraction(tmp_path, name):
    file = tmp_path / "hostile.ods"
    with zipfile.ZipFile(file, "w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet")
        archive.writestr("content.xml", "<root/>")
        archive.writestr(name, "SYNTHETIC")
    with pytest.raises(ProjectError):
        document(file)
    assert not (tmp_path / "escape").exists()


def test_ods_declared_expansion_obeys_job_disk_budget(tmp_path):
    file = tmp_path / "bounded.ods"
    with zipfile.ZipFile(file, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet")
        archive.writestr("content.xml", b" " * (1024 * 1024))
    budget = replace(ComputeBudget(), temp_disk_bytes=1024)
    with pytest.raises(ProjectError, match="boyut"):
        document(file, Control(budget=budget))


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('false')",
        "(lambda: 1)()",
        "col('x').__class__",
        "[x for x in []]",
        "2 ** 1000000",
        "col('x')[0]",
        "abs(x=1)",
    ],
)
def test_untrusted_formula_ast_never_executes(tmp_path, expression):
    with pytest.raises(ProjectError):
        parse(expression, [dict(id="x")])


def test_hostile_sql_identifier_is_data_and_source_is_readonly(tmp_path):
    file = tmp_path / "quoted.db"
    name = 'x"; DROP TABLE sentinel; --'
    quoted = '"' + name.replace('"', '""') + '"'
    with sqlite3.connect(file) as db:
        db.execute("CREATE TABLE sentinel(value TEXT)")
        db.execute(f'CREATE TABLE {quoted}("v" TEXT)')
        db.execute(
            f"INSERT INTO {quoted} VALUES (?)", ("'); DELETE FROM sentinel; --",)
        )
    original = file.read_bytes()
    rows = list(
        records(
            dict(path=str(file)),
            StructuredSettings(adapter_id="sqlite", sheet=name),
            Control(),
        )
    )
    assert rows[0]["values"]["v"] == "'); DELETE FROM sentinel; --"
    assert file.read_bytes() == original
    with sqlite3.connect(file) as db:
        assert db.execute("SELECT count(*) FROM sentinel").fetchone() == (0,)


@pytest.mark.parametrize("point", CRASH_POINTS)
def test_autosave_sigkill_every_boundary_preserves_manual_commit(tmp_path, point):
    source = tmp_path / "source.csv"
    source.write_bytes(b"SYNTHETIC\n")
    root = tmp_path / "project"
    with closing(ProjectStore.create(root, "manual")) as store:
        populate(store, source)
        store.save()
    before = (root / "ACTIVE").read_bytes()
    source_before = source.read_bytes()
    code = """
import os, signal, sys
import polars as pl
from veri_ufku.storage.project_store import ProjectStore
s=ProjectStore.open(sys.argv[1]);s.state['name']='recovery'
s.stage_parquet(pl.DataFrame({'v':[1,2]}))
def checkpoint(point):
    if point==sys.argv[2]:os.kill(os.getpid(),signal.SIGKILL)
s.save(autosave=True,checkpoint=checkpoint)
"""
    child = subprocess.run(
        [sys.executable, "-c", code, str(root), point], capture_output=True, timeout=20
    )
    assert child.returncode == -signal.SIGKILL, child.stderr
    with closing(ProjectStore.open(root, recover_lock=True)) as store:
        assert store.state["name"] == "manual"
        assert (root / "ACTIVE").read_bytes() == before
        if point in ("pointer_replaced", "root_synced"):
            preview = store.preview_autosave()
            assert preview["name"] == "recovery"
            store.restore_autosave(preview["commit_id"])
            assert store.state["name"] == "recovery"
            assert (root / "ACTIVE").read_bytes() == before
        else:
            assert not (root / "AUTOSAVE").exists()
    assert source.read_bytes() == source_before


@pytest.mark.parametrize("point", CRASH_POINTS)
def test_disk_full_each_publication_boundary_keeps_valid_old_or_new_commit(
    tmp_path, point
):
    source = tmp_path / "source.csv"
    source.write_bytes(b"SYNTHETIC\n")
    root = tmp_path / "project"
    with closing(ProjectStore.create(root, "old")) as store:
        populate(store, source)
        store.save()
        old = store.commit_id
        store.state["name"] = "new"
        populate(store, source)
        # Reuse the first dataset rather than creating duplicate identity fields.
        store.state["datasets"] = store.state["datasets"][:1]

        def fail(at):
            if at == point:
                raise OSError(errno.ENOSPC, "synthetic full disk")

        with pytest.raises(OSError):
            store.save(checkpoint=fail)
    with closing(ProjectStore.open(root)) as store:
        published = point in ("pointer_replaced", "root_synced")
        assert store.state["name"] == ("new" if published else "old")
        assert (store.commit_id != old) == published
    assert source.read_bytes() == b"SYNTHETIC\n"


def test_recovery_preview_stale_and_corrupt_preserve_draft_and_manual(tmp_path):
    with closing(ProjectStore.create(tmp_path / "project", "manual")) as store:
        active = (store.root / "ACTIVE").read_bytes()
        store.state["name"] = "first"
        store.save(autosave=True)
        draft = copy.deepcopy(store.state)
        preview = store.preview_autosave()
        assert store.state == draft and store.commit_id == preview["active_commit"]
        store.state["name"] = "second"
        store.save(autosave=True)
        with pytest.raises(ProjectError, match="değişti"):
            store.restore_autosave(preview["commit_id"])
        assert (
            store.state["name"] == "second"
            and (store.root / "ACTIVE").read_bytes() == active
        )
        (store.root / "AUTOSAVE").write_bytes(b'{"corrupt":true}')
        with pytest.raises(ProjectError):
            store.preview_autosave()
        assert (
            store.state["name"] == "second"
            and (store.root / "ACTIVE").read_bytes() == active
        )


@pytest.mark.parametrize(
    "adapter", ["csv", "jsonl", "json-depth", "json-size", "xlsx-part"]
)
def test_parser_actual_limits_reject_without_changing_source(tmp_path, adapter):
    from veri_ufku.importers.delimited import (
        MAX_RECORD,
        ImportSettings,
    )
    from veri_ufku.importers.delimited import (
        records as csv_records,
    )
    from veri_ufku.importers.structured import MAX_JSON, json_document, json_records
    from veri_ufku.importers.xlsx import MAX_PART, Workbook

    file = tmp_path / ("hostile." + adapter)
    if adapter == "csv":
        file.write_bytes(b"x\n" + b"a" * (MAX_RECORD + 1) + b"\n")
    elif adapter == "jsonl":
        file.write_text('{"x":"' + "a" * MAX_RECORD + '"}\n')
    elif adapter == "json-depth":
        file.write_text("[" * 18 + "0" + "]" * 18)
    elif adapter == "json-size":
        with file.open("wb") as stream:
            stream.truncate(MAX_JSON + 1)
    else:
        with zipfile.ZipFile(file, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("oversize.xml", b" " * (MAX_PART + 1))

    def action():
        snapshot = dict(path=str(file), fingerprint={"size": file.stat().st_size})
        if adapter == "csv":
            return list(csv_records(snapshot, ImportSettings(), Control()))
        if adapter == "jsonl":
            return list(
                json_records(
                    snapshot, StructuredSettings(adapter_id="jsonl"), Control()
                )
            )
        if adapter in ("json-depth", "json-size"):
            return json_document(snapshot, Control())
        return Workbook(file, Control())

    from veri_ufku.storage.project_store import file_hash

    original = file_hash(file)
    with pytest.raises(ProjectError):
        action()
    assert file_hash(file) == original


def test_project_metadata_hardlink_refused_before_external_database_changes(tmp_path):
    root = tmp_path / "project"
    with closing(ProjectStore.create(root)):
        pass
    outside = tmp_path / "external.sqlite"
    os.link(root / "metadata.sqlite", outside)
    original = outside.read_bytes()
    active = (root / "ACTIVE").read_bytes()
    with pytest.raises(ProjectError, match="bağ sayısı"):
        ProjectStore.open(root)
    assert outside.read_bytes() == original
    assert (root / "ACTIVE").read_bytes() == active
