"""Literal values, real TLS servers, read-only grants and consistency failures."""

import json
import os
import threading
import time
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import duckdb
import polars as pl
import pytest
from phase31_servers import api_server, postgres_server

from veri_ufku.importers.connector_contracts import ConnectorSpec, safe_url
from veri_ufku.importers.connectors import capture, discover
from veri_ufku.importers.database_connectors import batches, query, session
from veri_ufku.importers.delimited import Control
from veri_ufku.importers.registry import get_adapter
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore, source_fingerprint


@pytest.fixture
def api(tmp_path):
    with api_server(tmp_path) as server:
        yield server


@pytest.fixture(scope="module")
def pg(tmp_path_factory):
    binaries = Path(
        os.environ.get(
            "VERI_UFKU_TEST_PG_BIN", "/tmp/veri-ufku-f31-servers/root/usr/bin"
        )
    )
    if not (binaries / "postgres").is_file():
        pytest.skip("Real PostgreSQL test server unavailable; connector not accepted")
    with postgres_server(tmp_path_factory.mktemp("phase31-pg"), binaries) as server:
        yield server


def spec_for_pg(pg, **extra):
    return ConnectorSpec(
        kind="postgresql",
        table="records",
        terms_acknowledged=True,
        **{key: pg[key] for key in ("endpoint", "port", "database", "user", "ca_file")},
        **extra,
    )


def publish_roundtrip(tmp_path, spec, secret=None):
    work = tmp_path / "work"
    work.mkdir()
    snapshot, settings = capture(spec, secret, work, Control())
    adapter = get_adapter(spec.kind)
    preview = adapter.preview(snapshot, settings, Control())
    assert preview["examined"] <= 200
    result = adapter.import_data(snapshot, settings, work, Control())
    assert result["accepted"] > 0
    project = ProjectStore.create(tmp_path / "project")
    try:
        project.publish_import(result)
        before = project.state
        dataset = project.state["datasets"][-1]
        frame = pl.read_parquet(project.path(dataset["snapshot_uri"]))
        assert frame["__vu_row_id"].n_unique() == frame.height
        assert frame["__vu_source_record_id"].n_unique() == frame.height
        assert (
            project.state["sources"][-1]["connector"]["spec"]["credential_ref"]
            == spec.credential_ref
        )
        assert (
            project.source_statuses()[project.state["sources"][-1]["id"]] == "captured"
        )
        path = project.root
    finally:
        project.close()
    reopened = ProjectStore.open(path)
    try:
        assert reopened.state == before
        assert reopened.source_statuses()[before["sources"][-1]["id"]] == "captured"
        copied = reopened.save_as(tmp_path / "transferred-project")
        try:
            assert (
                copied.state["sources"][-1]["connector"]["spec"]["credential_ref"]
                == spec.credential_ref
            )
            assert (
                copied.source_statuses()[copied.state["sources"][-1]["id"]]
                == "captured"
            )
        finally:
            copied.close()
    finally:
        reopened.close()
    return frame, result, path


def test_postgresql_native_readonly_publish_snapshot(tmp_path, pg):
    spec = spec_for_pg(pg, filters=({"column": "id", "op": ">=", "value": 1},))
    choices = discover(spec, None, Control())
    assert dict(schema="public", table="records") in choices["tables"]
    frame, result, _ = publish_roundtrip(tmp_path, spec)
    assert frame["id"].to_list() == [1, 2]
    assert frame["amount"].to_list() == [Decimal("1.234567"), None]
    assert json.loads(frame["__vu_source_locator"][0])["source_key"] == 1
    assert (
        result["settings"]["format_metadata"]["connector"]["details"]["consistency"]
        == "single_transaction_snapshot"
    )
    assert pg["admin"].execute("SELECT count(*) FROM records").fetchone()[0] == 2
    with session(spec, None, Control()) as (db, _, _):
        with pytest.raises(Exception):
            db.execute("DELETE FROM records")


def test_postgresql_reject_admin_and_write_grants(tmp_path, pg):
    with pytest.raises(ProjectError, match="yönetici"):
        discover(
            replace(spec_for_pg(pg), user=os.environ.get("USER", "s-oktay")),
            None,
            Control(),
        )
    pg["admin"].execute("GRANT UPDATE ON records TO vu_reader")
    try:
        with pytest.raises(ProjectError, match="yazma"):
            capture(spec_for_pg(pg), None, tmp_path, Control())
    finally:
        pg["admin"].execute("REVOKE UPDATE ON records FROM vu_reader")


def test_postgresql_consistent_snapshot_while_source_changes(pg):
    spec = spec_for_pg(pg)
    with session(spec, None, Control()) as (db, tables, metadata):
        pg["admin"].execute("INSERT INTO records VALUES (3,'later',3)")
        try:
            frames = list(batches(spec, db, tables, metadata, Control()))
            assert pl.concat(frames)["id"].to_list() == [1, 2]
        finally:
            pg["admin"].execute("DELETE FROM records WHERE id=3")


def test_postgresql_never_uses_environment_or_password_file(tmp_path, pg, monkeypatch):
    sentinel = "fixture-ambient-password-must-not-be-used"
    password_file = tmp_path / "pgpass"
    password_file.write_text("*:*:*:*:" + sentinel + "\n")
    password_file.chmod(0o600)
    monkeypatch.setenv("PGPASSWORD", sentinel)
    monkeypatch.setenv("PGPASSFILE", str(password_file))
    with session(spec_for_pg(pg), None, Control()) as (db, _, _):
        assert db.info.password in (None, "")
        params = db.info.get_parameters()
        assert params["passfile"] != str(password_file)
        assert Path(params["passfile"]).read_bytes() == b""
        assert params["sslcertmode"] == "disable"


def test_postgresql_query_timeout_and_cancel(tmp_path, pg):
    admin = pg["admin"]
    admin.execute("BEGIN")
    admin.execute("LOCK TABLE records IN ACCESS EXCLUSIVE MODE")
    spec = spec_for_pg(pg, timeout=1)
    started = time.monotonic()
    try:
        with pytest.raises(ProjectError, match="timeout"):
            capture(spec, None, tmp_path, Control())
        assert time.monotonic() - started < 4
        work = tmp_path / "cancel"
        work.mkdir()
        event = threading.Event()
        timer = threading.Timer(0.2, event.set)
        timer.start()
        try:
            with pytest.raises(Canceled):
                capture(replace(spec, timeout=10), None, work, Control(event))
        finally:
            timer.join()
    finally:
        admin.execute("ROLLBACK")


def test_http_real_tls_pagination_mapping_retry_roundtrip(tmp_path, api):
    api["state"]["mode"] = "retry"
    spec = ConnectorSpec(
        kind="http",
        endpoint=api["endpoint"],
        ca_file=api["ca_file"],
        snapshot_header="X-Snapshot-ID",
        field_mapping={"amount": "total_amount"},
        terms_acknowledged=True,
    )
    frame, result, _ = publish_roundtrip(tmp_path, spec)
    assert frame["id"].to_list() == [1, 2, 3]
    assert frame["total_amount"].to_list() == [
        Decimal("10.000000"),
        Decimal("20.000000"),
        Decimal("30.000000"),
    ] or frame["total_amount"].to_list() == [10, 20, 30]
    details = result["settings"]["format_metadata"]["connector"]["details"]
    assert details["pages"][0]["retries"] == 1
    assert details["expected_total"] == 3
    assert details["snapshot_token"] == "snapshot-1"
    assert all(method == "GET" for method, _ in api["calls"])


@pytest.mark.parametrize(
    "mode",
    ["duplicate", "gap", "mutation", "loop", "external", "redirect", "missing_next"],
)
def test_http_rejects_unsafe_pagination_no_publish(tmp_path, api, mode):
    api["state"]["mode"] = mode
    spec = ConnectorSpec(
        endpoint=api["endpoint"],
        ca_file=api["ca_file"],
        snapshot_header="X-Snapshot-ID",
        terms_acknowledged=True,
    )
    with pytest.raises(ProjectError):
        capture(spec, None, tmp_path, Control())
    assert not (tmp_path / "ACTIVE").exists()


def test_http_freshness_unknown_tls_bounds_timeout_cancel(tmp_path, api):
    spec = ConnectorSpec(
        endpoint=api["endpoint"], ca_file=api["ca_file"], terms_acknowledged=True
    )
    api["state"]["mode"] = "unknown"
    snapshot, _ = capture(spec, None, tmp_path, Control())
    assert "no single-time" in snapshot["connector"]["details"]["consistency"]
    assert "unknown" in snapshot["connector"]["details"]["skipped_check"]
    for name, changed in (
        ("tls", replace(spec, ca_file="", retries=0)),
        ("size", replace(spec, max_bytes=10)),
        ("pages", replace(spec, max_pages=1)),
        ("rows", replace(spec, max_rows=1)),
    ):
        work = tmp_path / name
        work.mkdir()
        with pytest.raises(ProjectError):
            capture(changed, None, work, Control())
    api["state"]["mode"] = "slow"
    work = tmp_path / "slow"
    work.mkdir()
    with pytest.raises(ProjectError, match="timeout"):
        capture(replace(spec, timeout=1, retries=0), None, work, Control())
    event = threading.Event()
    event.set()
    work = tmp_path / "canceled"
    work.mkdir()
    with pytest.raises(Canceled):
        capture(spec, None, work, Control(event))


def test_http_secret_not_in_export_or_errors(tmp_path, api):
    api["state"]["mode"] = "auth"
    sentinel = "fixture-secret-never-log"
    spec = ConnectorSpec(
        endpoint=api["endpoint"],
        ca_file=api["ca_file"],
        credential_ref="fixture-reference",
        terms_acknowledged=True,
    )
    _, result, path = publish_roundtrip(tmp_path, spec, sentinel)
    assert sentinel not in json.dumps(result["settings"])
    assert all(
        sentinel.encode() not in p.read_bytes() for p in path.rglob("*") if p.is_file()
    )
    with pytest.raises(ProjectError) as caught:
        capture(spec, "wrong-secret", tmp_path / "project" / "staging", Control())
    assert sentinel not in str(caught.value) and "wrong-secret" not in str(caught.value)


def test_duckdb_native_readonly_external_disabled_and_source_hash(tmp_path):
    source = tmp_path / "source.duckdb"
    db = duckdb.connect(str(source))
    db.execute("CREATE TABLE records(id BIGINT, amount DECIMAL(20,6))")
    db.execute("INSERT INTO records VALUES (1,1.234567),(2,NULL)")
    db.close()
    fingerprint = source_fingerprint(source)
    spec = ConnectorSpec(
        kind="duckdb",
        endpoint=str(source),
        schema="main",
        table="records",
        terms_acknowledged=True,
    )
    frame, _, _ = publish_roundtrip(tmp_path, spec)
    assert frame["amount"].to_list() == [Decimal("1.234567"), None]
    assert source_fingerprint(source) == fingerprint
    with session(spec, None, Control()) as (db, _, _):
        with pytest.raises(Exception):
            db.execute("DELETE FROM records")
        with pytest.raises(Exception):
            db.execute("SELECT * FROM read_csv('/etc/passwd')")


def test_connection_contract_no_ambient_network_credentials_or_sql_execution():
    for url in (
        "http://example.org/data",
        "https://user:secret@example.org/data",
        "https://example.org/data?api_key=secret",
    ):
        with pytest.raises(ProjectError):
            safe_url(url, True)
    assert safe_url("http://localhost:1234/data", True)
    spec = ConnectorSpec(
        kind="duckdb",
        table="records",
        schema="main",
        filters=({"column": "name", "op": "=", "value": "'; DELETE FROM records;--"},),
    )
    sql, values, _ = query(spec, ["id", "name"])
    assert "DELETE" not in sql and "DELETE" in values[0]
    with pytest.raises(ProjectError):
        ConnectorSpec.from_dict(dict(kind="duckdb", password="secret"))


def test_failed_connector_publication_keeps_previous_active(tmp_path, api):
    work = tmp_path / "work"
    work.mkdir()
    spec = ConnectorSpec(
        endpoint=api["endpoint"], ca_file=api["ca_file"], terms_acknowledged=True
    )
    snapshot, settings = capture(spec, None, work, Control())
    result = get_adapter("http").import_data(snapshot, settings, work, Control())
    project = ProjectStore.create(tmp_path / "project")
    try:
        before = project.commit_id
        Path(snapshot["path"]).write_text('{"id":99}\n')
        with pytest.raises(ProjectError):
            project.publish_import(result)
        assert project.commit_id == before
        assert not project.state["datasets"]
    finally:
        project.close()


def test_explicit_connector_action_required_before_any_http(tmp_path, api):
    spec = ConnectorSpec(endpoint=api["endpoint"], ca_file=api["ca_file"])
    with pytest.raises(ProjectError, match="onay"):
        capture(spec, None, tmp_path, Control())
    assert api["calls"] == []
