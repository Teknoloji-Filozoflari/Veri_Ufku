"""Additional adapters get their own real-server evidence or an explicit skip."""

import io
import json
from dataclasses import replace
from pathlib import Path

import polars as pl
import pytest
from phase31_servers import mariadb_server, s3_server, secret_service
from test_connectors import publish_roundtrip

from veri_ufku.importers import credentials
from veri_ufku.importers.connector_contracts import ConnectorSpec
from veri_ufku.importers.connectors import capture, discover
from veri_ufku.importers.database_connectors import batches, session
from veri_ufku.importers.delimited import Control
from veri_ufku.storage.project_model import ProjectError

BINARIES = Path("/tmp/veri-ufku-f31-servers/root/usr/bin")


@pytest.fixture(scope="module")
def maria(tmp_path_factory):
    if not (BINARIES / "mariadbd").is_file():
        pytest.skip("Real MariaDB server unavailable; not accepted")
    with mariadb_server(tmp_path_factory.mktemp("phase31-maria"), BINARIES) as server:
        yield server


@pytest.fixture(scope="module")
def s3(tmp_path_factory):
    if not (BINARIES / "weed").is_file():
        pytest.skip("Real S3-compatible server unavailable; not accepted")
    with s3_server(tmp_path_factory.mktemp("phase31-s3"), BINARIES / "weed") as server:
        yield server


@pytest.fixture(scope="module")
def mysql(tmp_path_factory):
    binary = Path("/tmp/veri-ufku-f31-servers/mysql/bin")
    if not (binary / "mysqld").is_file():
        pytest.skip("Real MySQL server unavailable; not accepted")
    with mariadb_server(
        tmp_path_factory.mktemp("phase31-mysql"), binary, mysql=True
    ) as server:
        yield server


def maria_spec(maria):
    return ConnectorSpec(
        kind="mariadb",
        table="records",
        terms_acknowledged=True,
        **{
            k: maria[k]
            for k in ("endpoint", "port", "database", "schema", "user", "ca_file")
        },
    )


def test_mariadb_tls_innodb_snapshot_readonly_and_roundtrip(tmp_path, maria):
    spec = maria_spec(maria)
    assert discover(spec, None, Control())["tables"]
    frame, result, _ = publish_roundtrip(tmp_path, spec)
    assert frame["id"].to_list() == [1, 2]
    assert (
        "InnoDB"
        in result["settings"]["format_metadata"]["connector"]["details"]["isolation"]
    )
    with session(spec, None, Control()) as (db, tables, metadata):
        with maria["admin"].cursor() as cursor:
            cursor.execute("INSERT INTO fixture.records VALUES (3,3)")
        try:
            assert pl.concat(list(batches(spec, db, tables, metadata, Control())))[
                "id"
            ].to_list() == [1, 2]
            with db.cursor() as cursor:
                with pytest.raises(Exception):
                    cursor.execute("DELETE FROM fixture.records")
        finally:
            with maria["admin"].cursor() as cursor:
                cursor.execute("DELETE FROM fixture.records WHERE id=3")


def test_mysql_selection_is_not_mariadb_evidence(maria):
    with pytest.raises(ProjectError, match="uyuşmuyor"):
        discover(replace(maria_spec(maria), kind="mysql"), None, Control())


def test_mysql_own_server_tls_snapshot_readonly_roundtrip(tmp_path, mysql):
    spec = replace(maria_spec(mysql), kind="mysql")
    frame, result, _ = publish_roundtrip(tmp_path, spec)
    assert frame["id"].to_list() == [1, 2]
    assert (
        "mariadb"
        not in result["settings"]["format_metadata"]["connector"]["details"][
            "server"
        ].lower()
    )
    with session(spec, None, Control()) as (db, tables, metadata):
        with mysql["admin"].cursor() as cursor:
            cursor.execute("INSERT INTO fixture.records VALUES (3,3)")
        try:
            assert pl.concat(list(batches(spec, db, tables, metadata, Control())))[
                "id"
            ].to_list() == [1, 2]
            with db.cursor() as cursor:
                with pytest.raises(Exception):
                    cursor.execute("DELETE FROM fixture.records")
        finally:
            with mysql["admin"].cursor() as cursor:
                cursor.execute("DELETE FROM fixture.records WHERE id=3")


def test_real_secret_service_store_load_reference_only(tmp_path, monkeypatch):
    if not (BINARIES / "gnome-keyring-daemon").is_file():
        pytest.skip("Real Secret Service unavailable; not accepted")
    with secret_service(tmp_path, BINARIES / "gnome-keyring-daemon") as env:
        for key in ("DBUS_SESSION_BUS_ADDRESS", "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
            monkeypatch.setenv(key, env[key])
        reference, sentinel = "phase31-fixture", "fixture-secret-never-log"
        credentials.store(reference, sentinel)
        assert credentials.load(reference) == sentinel
        assert sentinel not in json.dumps(
            ConnectorSpec(kind="duckdb", credential_ref=reference).data()
        )
        assert all(
            sentinel.encode() not in path.read_bytes()
            for path in tmp_path.rglob("*")
            if path.is_file()
        )


@pytest.mark.parametrize("object_format", ["parquet", "jsonl", "csv", "ipc"])
def test_s3_real_sigv4_readonly_object_native_roundtrip(tmp_path, s3, object_format):
    frame = pl.DataFrame(dict(id=[1, 2], name=["Çağrı", "Işıl"]))
    buffer = io.BytesIO()
    if object_format == "parquet":
        frame.write_parquet(buffer)
    elif object_format == "ipc":
        frame.write_ipc(buffer)
    elif object_format == "csv":
        buffer.write(frame.write_csv().encode())
    else:
        buffer.write(frame.write_ndjson().encode())
    s3["admin"].put_object(
        Bucket="fixture-data", Key="records." + object_format, Body=buffer.getvalue()
    )
    spec = ConnectorSpec(
        kind="s3",
        endpoint=s3["endpoint"],
        ca_file=s3["ca_file"],
        credential_ref="s3-reference",
        bucket="fixture-data",
        object_key="records." + object_format,
        object_format=object_format,
        terms_acknowledged=True,
    )
    imported, result, path = publish_roundtrip(tmp_path, spec, s3["secret"])
    assert imported["id"].to_list() == (
        ["1", "2"] if object_format == "csv" else [1, 2]
    )
    assert result["capture"]["connector"]["details"]["etag"]
    assert "fixture-reader-key" not in json.dumps(result["settings"])
    assert all(
        b"fixture-reader-key" not in p.read_bytes()
        for p in path.rglob("*")
        if p.is_file()
    )
    wrong = tmp_path / "wrong"
    wrong.mkdir()
    with pytest.raises(ProjectError):
        capture(
            spec,
            json.dumps(dict(access_key="fixture-reader", secret_key="invalid")),
            wrong,
            Control(),
        )
