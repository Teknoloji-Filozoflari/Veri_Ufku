"""Six real local connector servers -> QML/spawn/native/portable/reopen smoke."""

import argparse
import hashlib
import io
import json
import os
import platform
import sys
import tempfile
import time
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase31/gui")
    )
    parser.add_argument("--package-root", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(repo / "tests"))
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
        os.environ["PYTHONPATH"] = str(args.package_root.resolve())
    import duckdb
    import polars as pl
    from phase31_servers import (
        api_server,
        mariadb_server,
        postgres_server,
        s3_server,
        secret_service,
    )
    from PySide6.QtCore import QObject, Qt, qVersion
    from PySide6.QtTest import QTest
    from test_connector_gui import fill

    import veri_ufku
    from veri_ufku.app import create_application
    from veri_ufku.storage.project_store import source_fingerprint

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    binaries = Path("/tmp/veri-ufku-f31-servers/root/usr/bin")
    mysql_binary = Path("/tmp/veri-ufku-f31-servers/mysql/bin")
    with (
        tempfile.TemporaryDirectory(prefix="veri-ufku-phase31-") as temporary,
        ExitStack() as stack,
    ):
        root = Path(temporary)
        folders = {}
        for name in ("pg", "mysql", "maria", "api", "s3", "keyring"):
            folders[name] = root / name
            folders[name].mkdir()
        pg = stack.enter_context(postgres_server(folders["pg"], binaries))
        mysql = stack.enter_context(
            mariadb_server(folders["mysql"], mysql_binary, mysql=True)
        )
        maria = stack.enter_context(mariadb_server(folders["maria"], binaries))
        api = stack.enter_context(api_server(folders["api"]))
        s3 = stack.enter_context(s3_server(folders["s3"], binaries / "weed"))
        keyring = stack.enter_context(
            secret_service(folders["keyring"], binaries / "gnome-keyring-daemon")
        )
        for key in ("DBUS_SESSION_BUS_ADDRESS", "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
            os.environ[key] = keyring[key]
        for name in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + name + "_HOME"] = str(root / name.lower())
        source = root / "source.duckdb"
        db = duckdb.connect(str(source))
        db.execute("CREATE TABLE records(id BIGINT, amount DECIMAL(20,6))")
        db.execute("INSERT INTO records VALUES (1,1.234567),(2,NULL)")
        db.close()
        source_hash = source_fingerprint(source)
        data = io.BytesIO()
        pl.DataFrame(dict(id=[1, 2], name=["Çağrı", "Işıl"])).write_parquet(data)
        s3["admin"].put_object(
            Bucket="fixture-data", Key="records.parquet", Body=data.getvalue()
        )
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        imports, projects = engine._imports_resources, engine._projects_resources
        records, images = [], []

        def spin(predicate):
            deadline = time.monotonic() + 40
            while not predicate():
                app.processEvents()
                QTest.qWait(10)
                if time.monotonic() > deadline:
                    raise RuntimeError("Phase31 GUI timeout")

        try:
            assert projects.create(str(root / "project"))
            for kind in ("postgresql", "http", "mysql", "mariadb", "duckdb", "s3"):
                window.findChild(QObject, "csvImportPanel").setProperty(
                    "detailsOpen", False
                )
                server = {
                    "postgresql": pg,
                    "mysql": mysql,
                    "mariadb": maria,
                    "http": api,
                    "s3": s3,
                }.get(kind)
                if kind == "duckdb":
                    values = dict(
                        connectorEndpoint=str(source),
                        connectorSchema="main",
                        connectorTable="records",
                    )
                else:
                    values = dict(
                        connectorEndpoint=server["endpoint"],
                        connectorCA=server["ca_file"],
                    )
                if kind in ("postgresql", "mysql", "mariadb"):
                    values.update(
                        connectorDatabase=server["database"],
                        connectorUser=server["user"],
                        connectorSchema="public" if kind == "postgresql" else "fixture",
                        connectorTable="records",
                    )
                elif kind == "s3":
                    values.update(
                        connectorBucket="fixture-data",
                        connectorObject="records.parquet",
                        connectorCredentialRef="phase31-s3",
                    )
                fill(window, kind, values)
                if kind in ("postgresql", "mysql", "mariadb"):
                    window.findChild(QObject, "connectorPort").setProperty(
                        "value", server["port"]
                    )
                elif kind == "s3":
                    window.findChild(QObject, "connectorSecret").setProperty(
                        "text", server["secret"]
                    )
                    window.findChild(QObject, "connectorSaveSecret").clicked.emit()
                    assert (
                        window.findChild(QObject, "connectorSecret").property("text")
                        == ""
                    )
                started = time.monotonic()
                window.findChild(QObject, "connectorRead").clicked.emit()
                spin(lambda: not imports.busy)
                assert imports.ready, imports.errorText
                assert imports.model.rowCount() == (3 if kind == "http" else 2)
                for width in (1366, 720):
                    window.setWidth(width)
                    window.setHeight(900)
                    app.processEvents()
                    scroll = window.findChild(QObject, "workspace").property(
                        "contentItem"
                    )
                    scroll.setProperty("contentY", 0)
                    QTest.qWait(100)
                    name = kind + ("-wide.png" if width == 1366 else "-narrow.png")
                    assert window.grabWindow().save(str(output / name))
                    images.append(name)
                before = json.loads(json.dumps(imports.result))
                window.findChild(QObject, "connectorEndpoint").forceActiveFocus()
                QTest.keyClick(window, Qt.Key.Key_F1)
                spin(lambda: window.property("infoOpen"))
                assert (
                    engine._learning_resources.article["id"] == "connector-connection"
                )
                QTest.keyClick(window, Qt.Key.Key_Escape)
                spin(lambda: not window.property("infoOpen"))
                assert imports.result == before
                calls = len(api["calls"])
                window.findChild(QObject, "importCsvButton").clicked.emit()
                spin(lambda: not imports.busy)
                assert not imports.errorText, imports.errorText
                assert len(api["calls"]) == calls
                dataset = projects.draft["datasets"][-1]
                frame = pl.read_parquet(projects.store.path(dataset["snapshot_uri"]))
                assert frame["id"].to_list() == (
                    [1, 2, 3] if kind == "http" else [1, 2]
                )
                capture = projects.draft["sources"][-1]["connector"]
                records.append(
                    dict(
                        kind=kind,
                        requirement="F31-S001..005",
                        dataset_version=dataset["version_id"],
                        rows=frame.height,
                        preview_rows=imports.model.rowCount(),
                        consistency=capture["details"]["consistency"],
                        credential_ref=capture["spec"]["credential_ref"],
                        seconds=round(time.monotonic() - started, 3),
                    )
                )
            assert source_fingerprint(source) == source_hash
            before = json.loads(json.dumps(projects.draft))
            calls = len(api["calls"])
            assert projects.closeProject() and projects.open(str(root / "project"))
            assert projects.draft == before and len(api["calls"]) == calls
            assert "fixture-reader-key" not in json.dumps(before)
            report = dict(
                date=datetime.now(UTC).isoformat(),
                environment="ENV-31",
                python=platform.python_version(),
                qt=qVersion(),
                os=platform.platform(),
                backend="offscreen/software",
                package_file=veri_ufku.__file__,
                lock_sha256=hashlib.sha256((repo / "uv.lock").read_bytes()).hexdigest(),
                records=records,
                images=images,
                reopened_datasets=6,
                source_hash=source_hash,
                physical_desktop_acceptance=False,
                minimum_hardware_acceptance=False,
            )
            (output / "walkthrough.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n"
            )
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
    print("PASS: six real connector/QML/spawn/native/help/portable-reopen paths")


if __name__ == "__main__":
    main()
