"""Real QML/spawn transformation and installed-wheel acceptance on bounded full data."""

import argparse
import hashlib
import json
import os
import platform
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from decimal import Decimal
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import polars as pl  # noqa: E402
from measure_phase07 import wait  # noqa: E402
from PySide6.QtCore import QObject, QPointF  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import veri_ufku  # noqa: E402
from veri_ufku.app import create_application  # noqa: E402
from veri_ufku.operations.relational_contracts import EQUALITY  # noqa: E402


def run(args):
    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    record = dict(
        environment="ENV-11",
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
    with tempfile.TemporaryDirectory(prefix="vu-phase11-") as temp:
        base = Path(temp)
        for k in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + k + "_HOME"] = str(base / k.lower())
        source = base / "data.parquet"
        n = record["rows"]
        pl.DataFrame(
            {
                "v": range(n),
                "key": [i // 2 for i in range(n)],
                "text": ["A-B"] * n,
                "header": ["x" if i % 2 == 0 else "y" for i in range(n)],
                "date": ["2024-01-01"] * n,
            }
        ).with_columns(pl.col("date").str.to_date()).write_parquet(source)
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
            window.findChild(QObject, "operationKind").setProperty("currentIndex", 4)
            window.findChild(QObject, "operationKind").setProperty("currentIndex", 4)

            def out(name, dtype):
                return dict(
                    id=ops.newColumnId(), name=name, original_name=name, type=dtype
                )

            dt = {"kind": "Int64"}
            version = data.dataset()["version_id"]
            methods = [
                (
                    "computed",
                    [cols["v"]],
                    dict(
                        expression='col("' + cols["v"] + '") * 2',
                        target=dt,
                        output=out("double", "Int64"),
                        zero_policy="reject",
                    ),
                ),
                (
                    "text_split",
                    [cols["text"]],
                    dict(
                        delimiter="-",
                        outputs=[out("first", "String"), out("last", "String")],
                    ),
                ),
                (
                    "text_combine",
                    [cols["text"], cols["header"]],
                    dict(
                        separator="-",
                        null_policy="propagate",
                        output=out("combined", "String"),
                    ),
                ),
                (
                    "date_parts",
                    [cols["date"]],
                    dict(
                        timezone="preserve",
                        parts=[dict(part="month", output=out("month", "Int64"))],
                    ),
                ),
                (
                    "aggregate",
                    [cols["key"], cols["v"]],
                    dict(
                        group_columns=[cols["key"]],
                        metrics=[
                            dict(
                                column_id=cols["v"],
                                method="sum",
                                target=dt,
                                output=out("total", "Int64"),
                            )
                        ],
                        equality=EQUALITY,
                        max_output_rows=n,
                    ),
                ),
                (
                    "pivot",
                    [cols["key"], cols["header"], cols["v"]],
                    dict(
                        group_columns=[cols["key"]],
                        header_column=cols["header"],
                        value_column=cols["v"],
                        aggregation="reject",
                        target=dt,
                        equality=EQUALITY,
                        max_output_rows=n,
                    ),
                ),
                (
                    "unpivot",
                    [cols["key"], cols["v"]],
                    dict(
                        index_columns=[],
                        value_columns=[cols["key"], cols["v"]],
                        variable_output=out("variable", "String"),
                        value_output=out("value", "Int64"),
                        max_output_rows=n * 2,
                    ),
                ),
                (
                    "append",
                    list(cols.values()),
                    dict(
                        secondary_version_id=version,
                        mapping=[
                            dict(
                                left_column=c["id"],
                                right_column=c["id"],
                                output=out(c["name"], c["type"]),
                            )
                            for c in data.dataset()["import_metadata"]["columns"]
                        ],
                        max_output_rows=n * 2,
                    ),
                ),
                (
                    "join",
                    [cols["key"]],
                    dict(
                        secondary_version_id=version,
                        left_keys=[cols["key"]],
                        right_keys=[cols["key"]],
                        how="inner",
                        nulls_equal=False,
                        right_outputs=[
                            dict(
                                column_id=c["id"],
                                output=out(c["name"] + "_right", c["type"]),
                            )
                            for c in data.dataset()["import_metadata"]["columns"]
                        ],
                        equality=EQUALITY,
                        max_output_rows=n * 2,
                    ),
                ),
            ]
            for index, (kind, selected, p) in enumerate(methods):
                window.findChild(QObject, "transformMethod").setProperty(
                    "currentIndex", index
                )
                ops.previewTransform(kind, json.dumps(selected), json.dumps(p), "chain")
                duration = wait(app, ops, record)
                assert ops.canApply, ops.errorText
                impact = ops.previewResult["impact"]
                expected = (
                    n // 2
                    if kind in ("aggregate", "pivot")
                    else n * 2
                    if kind in ("append", "join", "unpivot")
                    else n
                )
                assert (
                    impact["after_rows"] == expected
                    and impact["population_n"] == n
                    and ops.before.rowCount() == 200
                )
                record["methods"][kind] = dict(
                    preview_ms=duration,
                    impact=impact,
                    diagnostics=ops.previewResult["diagnostics"],
                )
                ops.apply()
                wait(app, ops, record)
                saved = frame()
                if kind == "computed":
                    assert saved["double"].to_list() == [i * 2 for i in range(n)]
                if kind == "text_split":
                    assert saved["first"].unique().to_list() == ["A"] and saved[
                        "last"
                    ].unique().to_list() == ["B"]
                if kind == "text_combine":
                    assert saved["combined"][0] == "A-B-x"
                if kind == "date_parts":
                    assert saved["month"].unique().to_list() == [1]
                if kind == "aggregate":
                    assert saved["total"].to_list() == [
                        i * 4 + 1 for i in range(n // 2)
                    ]
                if kind == "pivot":
                    assert saved["Pivot_x"].to_list() == list(range(0, n, 2)) and saved[
                        "Pivot_y"
                    ].to_list() == list(range(1, n, 2))
                if kind == "join":
                    assert (
                        ops.preview is None
                        and saved["__vu_source_record_id"].null_count() == n * 2
                    )
                version_out = data.dataset()["version_id"]
                assert projects.closeProject() and projects.open(str(base / "project"))
                assert data.dataset()["version_id"] == version_out and frame().equals(
                    saved
                )
                ops.historyAction("undo")
                wait(app, ops, record)
                assert frame().equals(initial)
                ops.historyAction("redo")
                wait(app, ops, record)
                assert frame().equals(saved)
                ops.historyAction("undo")
                wait(app, ops, record)
            kind, selected, p = methods[-1]
            ops.previewTransform(kind, json.dumps(selected), json.dumps(p), "chain")
            wait(app, ops, record)
            window.findChild(QObject, "transformationOptions").setProperty(
                "keyPairs", [{"left": cols["key"], "right": cols["key"]}]
            )
            window.findChild(QObject, "joinLeftKey").setProperty("currentIndex", 1)
            window.findChild(QObject, "joinRightKey").setProperty("currentIndex", 1)
            window.findChild(QObject, "joinRightSuffix").setProperty("text", "_right")
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
                app.processEvents()
                QTest.qWait(100)
                flick.setProperty("contentY", 0)
                if width == 720:
                    form = window.findChild(QObject, "transformationOptions")
                    fy = form.mapToItem(
                        flick.property("contentItem"), QPointF(0, 0)
                    ).y()
                    flick.setProperty("contentY", max(0, fy))
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
            kind, selected, p = methods[0]
            ops.previewTransform(kind, json.dumps(selected), json.dumps(p), "chain")
            ops.cancel()
            wait(app, ops, record)
            assert not ops.previewResult and frame().equals(initial)
            assert hashlib.sha256(source.read_bytes()).hexdigest() == original
            fixtures = {}
            arrow = pl.DataFrame(
                {
                    "amount": [Decimal("2.10"), None],
                    "time": pl.Series([1706740200000000001, None], dtype=pl.Int64).cast(
                        pl.Datetime("ns", "UTC")
                    ),
                    "items": [[1, 2], []],
                }
            )
            file_path = base / "sample.feather"
            arrow.write_ipc(file_path)
            stream_path = base / "sample.arrows"
            arrow.write_ipc_stream(stream_path)
            sqlite_path = base / "sample.sqlite"
            with closing(sqlite3.connect(sqlite_path)) as db:
                db.execute("CREATE TABLE first(a INTEGER)")
                db.execute("INSERT INTO first VALUES(1)")
                db.execute("CREATE TABLE second(a INTEGER)")
                db.executemany("INSERT INTO second VALUES(?)", [(2,), (3,)])
                db.commit()
            ods_path = base / "sample.ods"
            xml = '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"><office:body><office:spreadsheet><table:table table:name="Veri"><table:table-row><table:table-cell office:value-type="string"><text:p>amount</text:p></table:table-cell></table:table-row><table:table-row table:number-rows-repeated="2"><table:table-cell office:value-type="float" office:value="2.10"/></table:table-row></table:table></office:spreadsheet></office:body></office:document-content>'
            with zipfile.ZipFile(ods_path, "w") as archive:
                archive.writestr(
                    "mimetype", "application/vnd.oasis.opendocument.spreadsheet"
                )
                archive.writestr("content.xml", xml)
            for path, adapter in [
                (ods_path, "ods"),
                (sqlite_path, "sqlite"),
                (file_path, "ipc"),
                (stream_path, "ipc_stream"),
            ]:
                before = hashlib.sha256(path.read_bytes()).hexdigest()
                imports.choose(str(path))
                wait(app, imports, record)
                assert imports.formatId == adapter
                if adapter == "sqlite":
                    imports.setOption("sheet", "second")
                    imports.refreshPreview()
                    wait(app, imports, record)
                imports.importData()
                wait(app, imports, record)
                dataset = projects.draft["datasets"][-1]
                assert dataset["import_metadata"]["row_count"] == 2
                loaded = pl.read_parquet(projects.store.path(dataset["snapshot_uri"]))
                if adapter in ("ipc", "ipc_stream"):
                    assert loaded.select(arrow.columns).equals(arrow)
                if adapter == "sqlite":
                    assert loaded["a"].to_list() == [2, 3]
                if adapter == "ods":
                    assert loaded["amount"].to_list() == [Decimal("2.10")] * 2
                fixtures[adapter] = dict(sha256=before, rows=2, values_types_equal=True)
                assert projects.closeProject() and projects.open(str(base / "project"))
                assert pl.read_parquet(
                    projects.store.path(dataset["snapshot_uri"])
                ).equals(loaded)
                assert hashlib.sha256(path.read_bytes()).hexdigest() == before
            record["format_fixtures"] = fixtures
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
        / "docs/evidence/phase11-headless.json",
    )
    run(parser.parse_args())
