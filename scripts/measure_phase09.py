"""Actual operation compute/publication/QML/identity roundtrip and installed package smoke."""

import argparse
import hashlib
import json
import os
import platform
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import polars as pl  # noqa: E402
from measure_phase07 import wait  # noqa: E402
from PySide6.QtCore import QObject, QPointF  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import veri_ufku  # noqa: E402
from veri_ufku.app import create_application  # noqa: E402


def run(args):
    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    root = Path(__file__).resolve().parents[1]
    record = dict(
        environment="ENV-09",
        date="2026-10-07",
        python=platform.python_version(),
        polars=pl.__version__,
        platform=platform.platform(),
        backend="offscreen/software",
        rows=100000,
        n=1,
        peak_parent_worker_rss_bytes=0,
        max_tick_gap_ms=0,
        screenshots=[],
        package=str(veri_ufku.__file__),
        lock_sha256=hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest(),
    )
    with tempfile.TemporaryDirectory(prefix="vu-phase09-") as temp:
        base = Path(temp)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        source = base / "data.parquet"
        pl.DataFrame(
            dict(amount=list(range(record["rows"])), code=["001"] * record["rows"])
        ).write_parquet(source)
        original = hashlib.sha256(source.read_bytes()).hexdigest()
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports, data, ops = (
            engine._projects_resources,
            engine._imports_resources,
            engine._dataset_resources,
            engine._operations_resources,
        )
        try:
            assert projects.create(str(base / "project"))
            imports.choose(str(source))
            wait(app, imports, record)
            imports.importData()
            wait(app, imports, record)
            c = data.dataset()["import_metadata"]["columns"][0]["id"]
            data.selectColumn(c)
            data.computeProfile(False, "dataset", 1)
            wait(app, data, record)
            data.saveProfile()
            window.setProperty("selectedSection", 2)
            window.findChild(QObject, "operationCompareTables").setProperty(
                "checked", True
            )
            window.findChild(QObject, "operationShowHistory").setProperty(
                "checked", True
            )
            window.findChild(QObject, "operationName").setProperty("text", "sales")
            window.findChild(QObject, "operationPreview").clicked.emit()
            record["preview_ms"] = wait(app, ops, record)
            assert ops.previewResult["impact"]["before_rows"] == 100000
            assert ops.before.rowCount() == 200
            for width, height, theme, scale in [
                (1366, 900, "light", 1.0),
                (720, 560, "dark", 2.0),
            ]:
                # Preferences are held in the QML context, independent of dataset state.
                prefs = engine.rootContext().contextProperty("preferences")
                prefs.setTheme(theme)
                prefs.setTextScale(scale)
                window.setWidth(width)
                window.setHeight(height)
                app.processEvents()
                QTest.qWait(100)
                output = args.output.with_name(
                    args.output.stem + f"-{width}-{theme}.png"
                )
                assert window.grabWindow().save(str(output))
                record["screenshots"].append(str(output))
                flick = window.findChild(QObject, "workspace").property("contentItem")
                y = (
                    window.findChild(QObject, "operationAfterTable")
                    .mapToItem(flick.property("contentItem"), QPointF(0, 0))
                    .y()
                )
                flick.setProperty("contentY", max(0, y - 40))
                app.processEvents()
                QTest.qWait(100)
                output = args.output.with_name(
                    args.output.stem + f"-{width}-{theme}-after.png"
                )
                assert window.grabWindow().save(str(output))
                record["screenshots"].append(str(output))
                flick.setProperty("contentY", 0)
            ops.apply()
            record["apply_ms"] = wait(app, ops, record)
            assert data.dataset()["import_metadata"]["columns"][0]["name"] == "sales"
            assert not projects._result_statuses()[0]["current"]
            saved = pl.read_parquet(projects.store.path(data.dataset()["snapshot_uri"]))
            version = data.dataset()["version_id"]
            ops.historyAction("undo")
            wait(app, ops, record)
            assert projects._result_statuses()[0]["current"]
            ops.historyAction("redo")
            wait(app, ops, record)
            assert data.dataset()["version_id"] == version
            assert projects.closeProject() and projects.open(str(base / "project"))
            assert pl.read_parquet(
                projects.store.path(data.dataset()["snapshot_uri"])
            ).equals(saved)
            data.selectColumn(c)
            data.addFilter(c, "ge", "99990")
            wait(app, data, record)
            ops.previewOperation("filter", "", "")
            wait(app, ops, record)
            assert ops.previewResult["impact"]["removed_rows"] == 99990
            ops.apply()
            wait(app, ops, record)
            result = pl.read_parquet(
                projects.store.path(data.dataset()["snapshot_uri"])
            )
            assert result["sales"].to_list() == list(range(99990, 100000))
            assert (
                result["__vu_row_id"].to_list() == saved["__vu_row_id"].to_list()[-10:]
            )
            ops.historyAction("undo")
            wait(app, ops, record)
            ops.previewOperation("rename", c, "discarded")
            ops.cancel()
            # cancellation is expected, so wait's no-error assertion remains valid
            wait(app, ops, record)
            assert ops.previewResult == {}
            record.update(
                undo_redo_equal=True,
                reopen_equal=True,
                exact_filter_removed_rows=99990,
                ids_preserved=True,
                stale_result_marked=True,
                cancel_no_result=True,
                source_sha256_unchanged=original,
            )
            assert hashlib.sha256(source.read_bytes()).hexdigest() == original
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "docs/evidence/phase09-headless.json",
    )
    run(parser.parse_args())
