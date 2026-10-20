"""Real QML buttons, explicit network, spawned capture and native reopen."""

import io
import json
import time
from pathlib import Path

import duckdb
import polars as pl
import pytest
from phase31_servers import api_server, secret_service
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_connector_optional_servers import maria, mysql, s3  # noqa: F401
from test_connectors import pg  # noqa: F401
from test_import_gui import setup, spin, teardown


def fill(window, kind, values):
    window.setProperty("selectedSection", 1)
    window.findChild(QObject, "datasetTabs").setProperty("currentIndex", 1)
    window.findChild(QObject, "importAdvancedButton").clicked.emit()
    QTest.qWait(50)
    if not window.findChild(QObject, "connectorPanel").property("expanded"):
        window.findChild(QObject, "connectorToggle").clicked.emit()
    combo = window.findChild(QObject, "connectorKind")
    index = ["postgresql", "mysql", "mariadb", "duckdb", "http", "s3"].index(kind)
    combo.setProperty("currentIndex", index)
    combo.activated.emit(index)
    for name, value in values.items():
        window.findChild(QObject, name).setProperty("text", str(value))
    window.findChild(QObject, "connectorTerms").setProperty("checked", True)


@pytest.mark.parametrize("kind", ["postgresql", "http", "duckdb"])
def test_real_qml_connector_capture_import_help_reopen(tmp_path, monkeypatch, pg, kind):  # noqa: F811
    server_root = tmp_path / "server"
    server_root.mkdir()
    with api_server(server_root) as api:
        source = tmp_path / "source.duckdb"
        db = duckdb.connect(str(source))
        db.execute("CREATE TABLE records(id BIGINT, amount DECIMAL(20,6))")
        db.execute("INSERT INTO records VALUES (1,1.234567),(2,NULL)")
        db.close()
        app, window, _, projects, imports = setup(tmp_path, monkeypatch)
        try:
            values = (
                dict(connectorEndpoint=api["endpoint"], connectorCA=api["ca_file"])
                if kind == "http"
                else dict(
                    connectorEndpoint=source,
                    connectorSchema="main",
                    connectorTable="records",
                )
                if kind == "duckdb"
                else dict(
                    connectorEndpoint=pg["endpoint"],
                    connectorDatabase=pg["database"],
                    connectorUser=pg["user"],
                    connectorCA=pg["ca_file"],
                    connectorTable="records",
                )
            )
            if kind == "postgresql":
                # Port is kept separately from host, never a DSN with credentials.
                values["connectorPort"] = pg["port"]
            fill(
                window, kind, {k: v for k, v in values.items() if k != "connectorPort"}
            )
            if kind == "postgresql":
                window.findChild(QObject, "connectorPort").setProperty(
                    "value", pg["port"]
                )
            calls = len(api["calls"])
            app.processEvents()
            assert not imports.busy and len(api["calls"]) == calls
            if kind != "http":
                window.findChild(QObject, "connectorListTables").clicked.emit()
                spin(app, lambda: not imports.busy)
                assert imports.connectorTables, imports.errorText
            window.findChild(QObject, "connectorRead").clicked.emit()
            spin(app, lambda: not imports.busy)
            assert imports.ready, imports.errorText
            assert imports.model.rowCount() == (3 if kind == "http" else 2)
            assert imports.formatId == kind
            before = json.loads(json.dumps(imports.result))
            focus = window.findChild(QObject, "connectorEndpoint")
            focus.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_F1)
            spin(app, lambda: window.property("infoOpen"))
            learning = app._veri_ufku_resources[0]._learning_resources
            assert learning.article["id"] == "connector-connection"
            QTest.keyClick(window, Qt.Key.Key_Escape)
            spin(app, lambda: not window.property("infoOpen"))
            assert imports.result == before
            calls = len(api["calls"])
            window.findChild(QObject, "importCsvButton").clicked.emit()
            spin(app, lambda: not imports.busy)
            assert not imports.errorText, imports.errorText
            assert len(api["calls"]) == calls  # import never reconnects silently
            state = json.loads(json.dumps(projects.draft))
            dataset = projects.draft["datasets"][-1]
            frame = pl.read_parquet(projects.store.path(dataset["snapshot_uri"]))
            assert frame["id"].to_list() == ([1, 2, 3] if kind == "http" else [1, 2])
            root = str(projects.store.root)
            assert projects.closeProject() and projects.open(root)
            assert projects.draft == state and len(api["calls"]) == calls
        finally:
            teardown(app, window)


def test_real_qml_network_cancel_and_failed_source_preserve_active(
    tmp_path, monkeypatch
):
    with api_server(tmp_path) as api:
        app, window, _, projects, imports = setup(tmp_path, monkeypatch)
        try:
            fill(
                window,
                "http",
                dict(connectorEndpoint=api["endpoint"], connectorCA=api["ca_file"]),
            )
            before = projects.store.commit_id
            api["state"]["mode"] = "slow"
            window.findChild(QObject, "connectorRead").clicked.emit()
            spin(app, lambda: imports.busy)
            QTest.qWait(500)
            started = time.monotonic()
            window.findChild(QObject, "cancelImportButton").clicked.emit()
            spin(app, lambda: not imports.busy)
            assert time.monotonic() - started < 4
            assert projects.store.commit_id == before and not projects.draft["datasets"]
            api["state"]["mode"] = "duplicate"
            window.findChild(QObject, "connectorRead").clicked.emit()
            spin(app, lambda: not imports.busy)
            assert imports.errorText and projects.store.commit_id == before
        finally:
            teardown(app, window)


@pytest.mark.parametrize("kind", ["mysql", "mariadb", "s3"])
def test_additional_real_qml_connector_save_reopen(
    tmp_path, monkeypatch, request, kind
):
    server = request.getfixturevalue("maria" if kind == "mariadb" else kind)
    if kind == "s3":
        data = io.BytesIO()
        pl.DataFrame(dict(id=[1, 2], name=["Çağrı", "Işıl"])).write_parquet(data)
        server["admin"].put_object(
            Bucket="fixture-data", Key="records.parquet", Body=data.getvalue()
        )
    keyring_root = tmp_path / "keyring"
    keyring_root.mkdir()
    binary = Path("/tmp/veri-ufku-f31-servers/root/usr/bin/gnome-keyring-daemon")
    if not binary.is_file():
        pytest.skip("Real Secret Service unavailable; GUI auth not accepted")
    with secret_service(keyring_root, binary) as env:
        for key in ("DBUS_SESSION_BUS_ADDRESS", "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
            monkeypatch.setenv(key, env[key])
        app, window, _, projects, imports = setup(tmp_path, monkeypatch)
        try:
            values = dict(
                connectorEndpoint=server["endpoint"], connectorCA=server["ca_file"]
            )
            if kind == "s3":
                values.update(
                    connectorBucket="fixture-data",
                    connectorObject="records.parquet",
                    connectorCredentialRef="s3-gui-fixture",
                )
            else:
                values.update(
                    connectorDatabase="fixture",
                    connectorSchema="fixture",
                    connectorTable="records",
                    connectorUser="vu_reader",
                )
            fill(window, kind, values)
            if kind == "s3":
                window.findChild(QObject, "connectorSecret").setProperty(
                    "text", server["secret"]
                )
                window.findChild(QObject, "connectorSaveSecret").clicked.emit()
                assert (
                    window.findChild(QObject, "connectorSecret").property("text") == ""
                )
                assert not imports.errorText, imports.errorText
            else:
                window.findChild(QObject, "connectorPort").setProperty(
                    "value", server["port"]
                )
            window.findChild(QObject, "connectorRead").clicked.emit()
            spin(app, lambda: not imports.busy)
            assert imports.ready, imports.errorText
            window.findChild(QObject, "importCsvButton").clicked.emit()
            spin(app, lambda: not imports.busy)
            assert not imports.errorText, imports.errorText
            state = json.loads(json.dumps(projects.draft))
            assert "fixture-reader-key" not in json.dumps(state)
            root = str(projects.store.root)
            assert projects.closeProject() and projects.open(root)
            assert projects.draft == state
        finally:
            teardown(app, window)
