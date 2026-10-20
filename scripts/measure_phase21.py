"""Actual source/installed-wheel temporal worker, QML render and final-test evidence."""

import argparse
import hashlib
import json
import os
import platform
import tempfile
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("POLARS_MAX_THREADS", "2")

import polars as pl  # noqa: E402
from PySide6.QtCore import QObject, QPointF  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import veri_ufku  # noqa: E402
from veri_ufku.app import create_application  # noqa: E402


def run(args):
    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record = dict(
        environment="ENV-21",
        evaluated_at=datetime.now(UTC).isoformat(),
        python=platform.python_version(),
        platform=platform.platform(),
        package=str(veri_ufku.__file__),
        backend="offscreen/software",
        user_test=False,
        runs=[],
        screenshots=[],
        max_tick_ms=0,
    )
    with tempfile.TemporaryDirectory(prefix="vu-phase21-") as temporary:
        base = Path(temporary)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports, data, controller = (
            engine._projects_resources,
            engine._imports_resources,
            engine._dataset_resources,
            engine._time_series_resources,
        )

        def wait(obj):
            start = last = time.monotonic()
            while obj.busy:
                app.processEvents()
                QTest.qWait(10)
                now = time.monotonic()
                record["max_tick_ms"] = max(record["max_tick_ms"], (now - last) * 1000)
                last = now
                assert now - start < 180, obj.message
            assert not obj.errorText, obj.errorText
            return time.monotonic() - start

        try:
            assert projects.create(str(base / "project"))
            window.setProperty("selectedSection", 5)
            window.findChild(QObject, "modelPath").setProperty("currentIndex", 1)
            for n, method, period in ((120, "seasonal", 7), (100000, "none", 0)):
                source = base / f"series-{n}.parquet"
                dates = [date(1900, 1, 1) + timedelta(days=i) for i in range(n)]
                pl.DataFrame(
                    dict(day=dates, value=[10.0 + i * 0.01 + (i % 7) for i in range(n)])
                ).write_parquet(source)
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                imports.choose(str(source))
                wait(imports)
                imports.importData()
                wait(imports)
                data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
                wait(data)
                d = data.dataset()
                columns = d["import_metadata"]["columns"]
                spec = dict(
                    date=next(c["id"] for c in columns if c["name"] == "day"),
                    measurement=next(c["id"] for c in columns if c["name"] == "value"),
                    model=method,
                    seasonal_period=period,
                    horizon=3,
                    test_periods=6,
                )
                from veri_ufku.modeling.time_series import TimeSeriesSpec

                spec = TimeSeriesSpec.from_dict(spec).data()
                controller.restoreRequested.emit(json.dumps(spec))
                controller.create(json.dumps(spec))
                elapsed = wait(controller)
                assert (
                    controller.current
                    and controller.result["worker_pid"] != os.getpid()
                )
                worker_pid = controller.result["worker_pid"]
                dev_id = controller.record_id
                g = controller.result["groups"][0]
                assert not set(g["train_row_ids"]) & set(g["test_row_ids"])
                assert all(p["actual"] is None for p in g["forecast"])
                assert g["future_forecast"][0]["date"] > g["test_end"]
                controller.finalTest()
                final_seconds = wait(controller)
                assert controller.result["mode"] == "final"
                assert (
                    source.read_bytes()
                    and hashlib.sha256(source.read_bytes()).hexdigest() == digest
                )
                if n == 120:
                    for width, height in ((1366, 900), (720, 560)):
                        window.resize(width, height)
                        app.processEvents()
                        QTest.qWait(150)
                        for tag, target_name in (
                            ("settings", "timeSeriesPanel"),
                            ("result", "timeSeriesFinal"),
                        ):
                            target = window.findChild(QObject, target_name)
                            flick = window.findChild(QObject, "workspace").property(
                                "contentItem"
                            )
                            pos = target.mapToItem(
                                flick, QPointF(0, 0)
                            ).y() + flick.property("contentY")
                            flick.setProperty(
                                "contentY",
                                max(
                                    0,
                                    min(
                                        pos,
                                        flick.property("contentHeight")
                                        - flick.property("height"),
                                    ),
                                ),
                            )
                            QTest.qWait(150)
                            path = args.output.with_name(
                                args.output.stem + f"-{tag}-{width}.png"
                            )
                            assert window.grabWindow().save(str(path))
                            record["screenshots"].append(str(path))
                root = str(projects.store.root)
                assert projects.closeProject(True), projects.errorText
                assert projects.open(root), projects.errorText
                data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
                wait(data)
                controller.openSaved(dev_id)
                wait(controller)
                assert controller.current and controller.result["groups"][0] == g
                record["runs"].append(
                    dict(
                        rows=n,
                        method=method,
                        seasonal_period=period,
                        development_seconds=elapsed,
                        final_seconds=final_seconds,
                        chosen=g["chosen"],
                        comparisons=g["comparisons"],
                        source_sha256=digest,
                        worker_pid=worker_pid,
                        train_rows=len(g["train_row_ids"]),
                        test_rows=len(g["test_row_ids"]),
                        future_forecast=g["future_forecast"],
                    )
                )
                print(
                    f"PASS time-series rows={n} development={elapsed:.3f}s final={final_seconds:.3f}s",
                    flush=True,
                )
            for context in (
                "model.time-series",
                "timeseries.seasonality",
                "timeseries.lag",
                "timeseries.validation",
            ):
                engine._learning_resources.openContext(context)
                assert engine._learning_resources.article["id"].startswith(
                    "timeseries-"
                )
            record["status"] = "passed"
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(
        "PASS Phase21 chronological forecast, real baselines, final ledger, reopen and help",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase21/source.json")
    )
    run(parser.parse_args())
