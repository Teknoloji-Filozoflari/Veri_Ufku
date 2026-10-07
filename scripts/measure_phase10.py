"""Real QML/spawn cleaning and installed-wheel acceptance on bounded full data."""

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
from veri_ufku.operations.cleaning_contracts import defaults  # noqa: E402


def run(args):
    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    record = dict(
        environment="ENV-10",
        date="2026-10-07",
        python=platform.python_version(),
        polars=pl.__version__,
        platform=platform.platform(),
        backend="offscreen/software",
        rows=100000,
        n=1,
        peak_parent_worker_rss_bytes=0,
        max_tick_gap_ms=0,
        package=str(veri_ufku.__file__),
        methods={},
        screenshots=[],
    )
    with tempfile.TemporaryDirectory(prefix="vu-phase10-") as temp:
        base = Path(temp)
        for k in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + k + "_HOME"] = str(base / k.lower())
        source = base / "data.parquet"
        n = record["rows"]
        pl.DataFrame(
            {
                "v": pl.Series(
                    [None if i % 10 == 1 else 2 for i in range(n)], dtype=pl.Int64
                ),
                "text": [" A " if i % 2 == 0 else "B" for i in range(n)],
                "time": range(n),
                "group": ["x" if i % 2 == 0 else "y" for i in range(n)],
                "missing": pl.Series([None] * n, dtype=pl.Int64),
                "date": ["bad" if i % 10 == 0 else "2026-01-01" for i in range(n)],
            }
        ).write_parquet(source)
        original = hashlib.sha256(source.read_bytes()).hexdigest()
        record["fixture_sha256"] = original
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
            cols = {
                c["name"]: c["id"] for c in data.dataset()["import_metadata"]["columns"]
            }

            def frame():
                return pl.read_parquet(
                    projects.store.path(data.dataset()["snapshot_uri"])
                )

            initial = frame()
            window.setProperty("selectedSection", 2)
            window.findChild(QObject, "operationKind").setProperty("currentIndex", 3)
            methods = [
                ("fill", "v"),
                ("missing_rows", "v"),
                ("missing_columns", "missing"),
                ("dedup", "text"),
                ("trim", "text"),
                ("map_categories", "text"),
                ("convert", "date"),
                ("ordered_fill", "v"),
                ("outlier", "v"),
            ]
            for index, (kind, name) in enumerate(methods):
                p = defaults(kind)
                if kind == "fill":
                    p.update(method="mean")
                if kind in ("ordered_fill", "dedup"):
                    p.update(order_columns=[cols["time"]])
                if kind == "ordered_fill":
                    p.update(group_columns=[cols["group"]])
                if kind == "map_categories":
                    p.update(mapping=[{"from": "B", "to": "C"}])
                if kind == "convert":
                    p.update(target={"kind": "Date"}, on_error="null")
                window.findChild(QObject, "cleaningMethod").setProperty(
                    "currentIndex", index
                )
                ops.previewCleaning(
                    kind,
                    json.dumps([cols[name]]),
                    json.dumps(p),
                    "copy" if kind == "trim" else "chain",
                )
                duration = wait(app, ops, record)
                assert ops.canApply
                impact = ops.previewResult["impact"]
                assert impact["population_n"] == n and ops.before.rowCount() == 200
                expected_removed = (
                    10000 if kind == "missing_rows" else n - 2 if kind == "dedup" else 0
                )
                assert impact["removed_rows"] == expected_removed
                if kind == "fill":
                    assert impact["changed_cells"] == 10000
                if kind == "convert":
                    assert impact["new_nulls"] == impact["parse_errors"] == 10000
                if kind == "ordered_fill":
                    assert impact["changed_cells"] == 9999
                if kind == "outlier":
                    assert (
                        impact["outlier_candidates"] == 0
                        and impact["added_columns"] == 1
                    )
                record["methods"][kind] = dict(preview_ms=duration, impact=impact)
                ops.apply()
                wait(app, ops, record)
                saved = frame()
                version = data.dataset()["version_id"]
                assert projects.closeProject() and projects.open(str(base / "project"))
                assert data.dataset()["version_id"] == version and frame().equals(saved)
                ops.historyAction("undo")
                wait(app, ops, record)
                assert frame().equals(initial)
                ops.historyAction("redo")
                wait(app, ops, record)
                assert frame().equals(saved)
                ops.historyAction("undo")
                wait(app, ops, record)
            assert ops.leakageHistory
            # Render uncluttered form and the optional comparison, in both supported sizes/scales.
            window.findChild(QObject, "cleaningMethod").setProperty("currentIndex", 0)
            window.findChild(QObject, "cleaningFillMethod").setProperty(
                "currentIndex", 1
            )
            ops.previewCleaning(
                "fill",
                json.dumps([cols["v"]]),
                json.dumps(dict(defaults("fill"), method="mean")),
                "chain",
            )
            wait(app, ops, record)
            prefs = engine.rootContext().contextProperty("preferences")
            flick = window.findChild(QObject, "workspace").property("contentItem")
            for width, height, theme, scale in [
                (1366, 900, "light", 1.0),
                (720, 560, "dark", 2.0),
            ]:
                prefs.setTheme(theme)
                prefs.setTextScale(scale)
                window.setWidth(width)
                window.setHeight(height)
                flick.setProperty("contentY", 0)
                app.processEvents()
                QTest.qWait(100)
                output = args.output.with_name(
                    args.output.stem + f"-{width}-{theme}.png"
                )
                assert window.grabWindow().save(str(output))
                record["screenshots"].append(str(output))
                window.findChild(QObject, "operationCompareTables").setProperty(
                    "checked", True
                )
                app.processEvents()
                target = window.findChild(QObject, "operationAfterTable")
                y = target.mapToItem(flick.property("contentItem"), QPointF(0, 0)).y()
                flick.setProperty("contentY", max(0, y - 40))
                app.processEvents()
                QTest.qWait(100)
                output = args.output.with_name(
                    args.output.stem + f"-{width}-{theme}-after.png"
                )
                assert window.grabWindow().save(str(output))
                record["screenshots"].append(str(output))
                window.findChild(QObject, "operationCompareTables").setProperty(
                    "checked", False
                )
            ops.discardPreview()
            ops.previewCleaning(
                "fill", json.dumps([cols["v"]]), json.dumps(defaults("fill")), "chain"
            )
            ops.cancel()
            wait(app, ops, record)
            assert not ops.previewResult and frame().equals(initial)
            assert hashlib.sha256(source.read_bytes()).hexdigest() == original
            record.update(
                source_unchanged=True,
                undo_redo_equal=True,
                reopen_equal=True,
                cancel_preserved=True,
                scope="full; tables first200 only",
                cache="warm developer host; minimum hardware unverified",
            )
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
        / "docs/evidence/phase10-headless.json",
    )
    run(parser.parse_args())
