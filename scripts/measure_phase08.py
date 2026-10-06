"""Real Linux quality process, QML, source integrity and installed-wheel smoke."""

import argparse
import hashlib
import json
import os
import platform
import tempfile
import time
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
    record = dict(
        environment="ENV-08",
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
        wheel_package=str(veri_ufku.__file__) if args.package_root else None,
        lock_sha256=hashlib.sha256(
            (Path(__file__).resolve().parents[1] / "uv.lock").read_bytes()
        ).hexdigest(),
    )
    with tempfile.TemporaryDirectory(prefix="vu-phase08-") as temp:
        base = Path(temp)
        for name in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + name + "_HOME"] = str(base / name.lower())
        source = base / "reference.parquet"
        n = record["rows"]
        pl.DataFrame(
            dict(
                id=[f"{i:07}" for i in range(n)],
                amount=list(range(n - 1)) + [1000000],
                category=["İZMİR", "izmir", " Ankara ", None] * (n // 4),
                day=["2024-02-30"] + ["2024-01-01"] * (n - 1),
            )
        ).write_parquet(source)
        original = hashlib.sha256(source.read_bytes()).hexdigest()
        app, window, bridge = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports, data = (
            engine._projects_resources,
            engine._imports_resources,
            engine._dataset_resources,
        )
        try:
            assert projects.create(str(base / "project"))
            imports.choose(str(source))
            wait(app, imports, record)
            imports.importData()
            wait(app, imports, record)
            ids = {
                c["name"]: c["id"] for c in data.dataset()["import_metadata"]["columns"]
            }
            rules = [
                dict(column_id=ids["day"], kind="date", value="%Y-%m-%d", upper=""),
                dict(column_id=ids["id"], kind="unique", value="", upper=""),
            ]
            window.setProperty("selectedSection", 1)
            window.findChild(QObject, "datasetTabs").setProperty("currentIndex", 2)
            data.computeQuality(
                False,
                "dataset",
                "clean",
                json.dumps([ids["category"]]),
                json.dumps(rules),
            )
            record["full_scan_ms"] = wait(app, data, record)
            report = data.qualityResult
            assert report["used_n"] == n and report["scope"] == "full"
            expected = {
                "missing": 25000,
                "whitespace": 25000,
                "category_similarity": 50000,
                "invalid_date": 1,
                "outlier": 1,
                "duplicates_selected": 100000,
            }
            for code, count in expected.items():
                assert (
                    next(f for f in report["findings"] if f["code"] == code)["count"]
                    == count
                ), (code, report)
            record["expected_counts"] = expected
            record["findings"] = len(report["findings"])
            data.saveQuality()
            projects.save()
            deadline = time.monotonic() + 10
            while projects.busy:
                app.processEvents()
                QTest.qWait(10)
                assert time.monotonic() < deadline
            assert not projects.dirty
            for width, theme in ((1366, "light"), (720, "dark")):
                window.setWidth(width)
                window.setHeight(900 if width == 1366 else 800)
                app._veri_ufku_resources[-2].setTheme(theme)
                app.processEvents()
                QTest.qWait(120)
                flick = window.findChild(QObject, "workspace").property("contentItem")
                for name, field in (
                    ("form", "qualityPanel"),
                    ("findings", "qualityScope"),
                ):
                    y = (
                        window.findChild(QObject, field)
                        .mapToItem(flick.property("contentItem"), QPointF(0, 0))
                        .y()
                    )
                    flick.setProperty("contentY", max(0, y - 45))
                    app.processEvents()
                    QTest.qWait(100)
                    output = (
                        args.output.parent
                        / f"phase08{'-wheel' if args.package_root else ''}-{width}-{theme}-{name}.png"
                    )
                    assert window.grabWindow().save(str(output))
                    record["screenshots"].append(str(output))
            assert projects.closeProject() and projects.open(str(base / "project"))
            assert projects.draft["results"][-1]["quality"] == report
            data.computeQuality(True, "dataset", "inspect", "[]", "[]")
            wait(app, data, record)
            assert (
                data.qualityResult["scope"] == "sample"
                and data.qualityResult["used_n"] == 10000
            )
            assert not any(
                f["code"] == "outlier" for f in data.qualityResult["findings"]
            )
            record["sample_n"] = 10000
            data.computeQuality(False, "dataset", "inspect", "[]", "[]")
            data.cancel()
            wait(app, data, record)
            assert data.qualityResult == {}
            assert hashlib.sha256(source.read_bytes()).hexdigest() == original
            assert not list(data.cache.glob("view-*"))
            record["source_sha256_unchanged"] = original
            record["cancel_no_result"] = True
            args.output.write_text(
                json.dumps(record, ensure_ascii=False, indent=2) + "\n"
            )
            print(json.dumps(record, ensure_ascii=False))
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "docs/evidence/phase08-headless.json",
    )
    run(parser.parse_args())
