"""Real QML/Matplotlib pointer, export, persistence and spawn in source or Linux wheel."""

import argparse
import hashlib
import json
import os
import platform
import time
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import polars as pl  # noqa: E402
from measure_phase07 import wait  # noqa: E402
from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QTimer  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import veri_ufku  # noqa: E402
from veri_ufku.app import create_application  # noqa: E402


def run(args):
    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    record = dict(
        environment="ENV-12",
        date="2026-10-07",
        python=platform.python_version(),
        platform=platform.platform(),
        polars=pl.__version__,
        backend="offscreen/software",
        package=str(veri_ufku.__file__),
        rows=100000,
        n=1,
        cache="warm developer Ryzen7/32GB; no minimum hardware/cold-cache claim",
        peak_parent_worker_rss_bytes=0,
        max_tick_gap_ms=0,
        methods={},
        screenshots=[],
        input_frame_ms=[],
        source_unchanged=False,
    )
    with TemporaryDirectory(prefix="vu-phase12-", dir=args.project_temp) as temp:
        base = Path(temp)
        for k in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + k + "_HOME"] = str(base / k.lower())
        os.environ["MPLCONFIGDIR"] = str(base / "mpl")
        n = record["rows"]
        source = base / "large.parquet"
        pl.DataFrame(
            {
                "x": range(n),
                "y": [2 * i for i in range(n)],
                "category": ["Grup " + str(i % 30) for i in range(n)],
                "day": [date(2024, 1, 1) + timedelta(days=i % 100) for i in range(n)],
                "nullable": [None if i % 10 == 0 else i for i in range(n)],
                "customer_id": range(n),
            }
        ).write_parquet(source)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        record["fixture_sha256"] = digest
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports, data, charts = (
            engine._projects_resources,
            engine._imports_resources,
            engine._dataset_resources,
            engine._charts_resources,
        )
        timer = QTimer()

        def sample_input():
            if charts.process and len(record["input_frame_ms"]) < 100:
                start = time.monotonic()
                QTest.mouseMove(window, QPoint(25, 25))
                assert not window.grabWindow().isNull()
                record["input_frame_ms"].append((time.monotonic() - start) * 1000)

        timer.timeout.connect(sample_input)
        timer.start(20)
        try:
            assert projects.create(str(base / "project"))
            imports.choose(str(source))
            wait(app, imports, record)
            imports.importData()
            wait(app, imports, record)
            data.refresh()
            wait(app, data, record)
            cols = {c["name"]: c["id"] for c in data.datasetColumns}
            assert cols["customer_id"] not in [
                c["column_id"] for c in charts.recommendations("relationship")
            ]
            snapshot = pl.read_parquet(
                projects.store.path(data.dataset()["snapshot_uri"])
            )
            window.setProperty("selectedSection", 3)

            def field(name, prop, value):
                obj = window.findChild(QObject, name)
                assert obj is not None, name
                obj.setProperty(prop, value)

            def click(name):
                window.findChild(QObject, name).clicked.emit()

            kinds = [
                "histogram",
                "box",
                "bar",
                "line",
                "scatter",
                "correlation",
                "missing",
            ]
            for index, kind in enumerate(kinds):
                field("chartKind", "currentIndex", index)
                field(
                    "chartX",
                    "currentIndex",
                    2 if kind == "bar" else 3 if kind == "line" else 0,
                )
                field("chartY", "currentIndex", 1)
                field("chartAggregation", "currentIndex", 1)
                field("chartTopN", "value", 5)
                field("chartPointLimit", "value", 200)
                field(
                    "chartPanel",
                    "selected",
                    [cols["x"], cols["y"]]
                    if kind == "correlation"
                    else [cols["nullable"], cols["x"]],
                )
                field("chartTitle", "text", "Veri_Ufku · " + kind + " · 100.000 kayıt")
                click("chartCreate")
                pid = charts.process.pid
                duration = wait(app, charts, record)
                result = charts.result
                assert result and result["worker_pid"] == pid != os.getpid()
                assert result["used_n"] == n and charts.current
                assert not charts.provider.image.isNull()
                points = result["points"]
                if kind == "histogram":
                    assert [p["n"] for p in points] == [5000] * 20
                elif kind == "box":
                    assert (points[0]["q1"], points[0]["y"], points[0]["q3"]) == (
                        24999.75,
                        49999.5,
                        74999.25,
                    )
                elif kind == "bar":
                    assert (
                        sum(p["n"] for p in points) == n
                        and result["details"]["other_categories"] == 25
                    )
                elif kind == "line":
                    assert points[0]["y"] == 99900000 and all(
                        p["n"] == 1000 for p in points
                    )
                elif kind == "scatter":
                    assert [p["x"] for p in points] == [500.0 * i for i in range(200)]
                    assert result["details"]["omitted_rows"] == 99800
                elif kind == "correlation":
                    assert all(
                        p["n"] == n and abs(p["coefficient"] - 1) < 1e-12
                        for p in points
                    )
                else:
                    assert points[0]["null_count"] == 10000 and points[0]["y"] == 0.1
                method = dict(
                    ms=duration,
                    worker_pid=pid,
                    points=len(points),
                    used_n=n,
                    reference_equal=True,
                    scope=result["scope"],
                    details=result["details"],
                    exports={},
                )
                for fmt in ("png", "svg"):
                    target = base / (kind + "." + fmt)
                    charts.export(str(target), fmt)
                    wait(app, charts, record)
                    assert target.stat().st_size > 1000
                    method["exports"][fmt] = dict(
                        bytes=target.stat().st_size,
                        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                    )
                    if kind in ("histogram", "correlation") and not args.package_root:
                        import shutil

                        shutil.copyfile(
                            target, args.output.parent / ("phase12-" + kind + "." + fmt)
                        )
                charts.save()
                wait(app, charts, record)
                record["methods"][kind] = method
            assert len(charts.savedCharts) == 7
            saved = charts.savedCharts[4]["id"]
            assert projects.closeProject() and projects.open(str(base / "project"))
            charts.openSaved(saved)
            assert charts.current and charts.result["spec"]["kind"] == "scatter"
            data.refresh()
            wait(app, data, record)
            data.selectRow(0)
            wait(app, charts, record)
            assert charts.selection["point_ids"] == [0]
            workspace = window.findChild(QObject, "workspace")
            flick = workspace.property("contentItem")
            image = window.findChild(QObject, "chartImage")
            mouse = window.findChild(QObject, "chartMouse")
            location = image.mapToItem(flick.property("contentItem"), QPointF(0, 0))
            flick.setProperty("contentY", max(0, location.y() - 20))
            app.processEvents()
            QTest.qWait(50)
            meta = charts.result["render"]
            p = meta["pixels"][0]
            pw, ph = image.property("paintedWidth"), image.property("paintedHeight")
            pos = mouse.mapToScene(
                QPointF(
                    (image.property("width") - pw) / 2 + p["x"] / meta["width"] * pw,
                    (image.property("height") - ph) / 2 + p["y"] / meta["height"] * ph,
                )
            )
            QTest.mouseClick(
                window,
                Qt.LeftButton,
                Qt.NoModifier,
                QPoint(round(pos.x()), round(pos.y())),
            )
            wait(app, charts, record)
            assert (
                charts.selection["row_ids"]
                == [snapshot["__vu_row_id"][0]]
                == data.selectedRowIds
            )
            bounds = meta["bounds"]
            field("chartMode", "currentIndex", 1)

            def position(fx, fy):
                return mouse.mapToScene(
                    QPointF(
                        (image.property("width") - pw) / 2 + fx * pw,
                        (image.property("height") - ph) / 2 + fy * ph,
                    )
                ).toPoint()

            QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, position(0.35, 0.30))
            QTest.mouseMove(window, position(0.65, 0.45))
            QTest.mouseRelease(
                window, Qt.LeftButton, Qt.NoModifier, position(0.65, 0.45)
            )
            wait(app, charts, record)
            assert charts.result["render"]["bounds"] != bounds
            click("chartReset")
            wait(app, charts, record)
            assert charts.result["render"]["bounds"] == bounds
            field("chartMode", "currentIndex", 0)
            record["real_drag_zoom"] = True
            click("chartZoom")
            wait(app, charts, record)
            assert charts.result["render"]["bounds"] != bounds
            click("chartReset")
            wait(app, charts, record)
            assert charts.result["render"]["bounds"] == bounds
            record["pointer_rowid_table_roundtrip"] = record["zoom_reset"] = record[
                "reopen"
            ] = True
            # Filter is immutable dataset context, never secretly full data.
            data.addFilter(cols["x"], "ge", "99000")
            wait(app, data, record)
            assert not charts.current
            charts.create(json.dumps(dict(kind="histogram", x=cols["x"], bins=10)))
            wait(app, charts, record)
            assert charts.result["used_n"] == 1000 and charts.result["filters"]
            assert [p["n"] for p in charts.result["points"]] == [100] * 10
            record["filter_visible"] = True
            previous = charts.result
            charts.create(json.dumps(dict(kind="scatter", x=cols["x"], y=cols["y"])))
            before = time.monotonic()
            charts.cancel()
            record["cancel_feedback_ms"] = (time.monotonic() - before) * 1000
            record["cancel_exit_ms"] = wait(app, charts, record)
            assert charts.result is previous
            record["cancel_preserved"] = True
            for width, height, theme, scale in [
                (1366, 768, "dark", 1.0),
                (720, 800, "dark", 1.0),
            ]:
                window.setWidth(width)
                window.setHeight(height)
                app.processEvents()
                QTest.qWait(100)
                flick.setProperty("contentY", 0)
                name = f"phase12-{width}-{theme}-{int(scale * 100)}.png"
                target = args.output.parent / name
                if args.package_root:
                    target = args.output.parent / ("wheel-" + name)
                assert window.grabWindow().save(str(target))
                record["screenshots"].append(str(target))
            record["source_unchanged"] = (
                hashlib.sha256(source.read_bytes()).hexdigest() == digest
            )
            assert record["source_unchanged"]
            assert len(record["input_frame_ms"]) == 100
            ordered = sorted(record["input_frame_ms"])
            record["input_frame_p95_ms"] = ordered[94]
            record["input_frame_max_ms"] = ordered[-1]
        finally:
            timer.stop()
            app._veri_ufku_resources[-1]()
            assert not list((base / "cache/charts").glob("chart-*"))
            window.deleteLater()
            app.processEvents()
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in record.items() if k not in ("methods", "input_frame_ms")},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--project-temp", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "docs/evidence/phase12-headless.json",
    )
    run(parser.parse_args())
