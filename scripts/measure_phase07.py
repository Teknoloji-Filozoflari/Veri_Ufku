"""Linux QML/spawn paging/profile benchmark, also runs from an installed wheel."""

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
from PySide6.QtCore import QObject, QPointF  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import veri_ufku  # noqa: E402
from veri_ufku.app import create_application  # noqa: E402


def rss(pid):
    try:
        return next(
            int(line.split()[1]) * 1024
            for line in Path(f"/proc/{pid}/status").read_text().splitlines()
            if line.startswith("VmRSS:")
        )
    except (OSError, StopIteration):
        return 0


def wait(app, controller, record):
    start = last = time.monotonic()
    while controller.busy:
        app.processEvents()
        QTest.qWait(10)
        now = time.monotonic()
        record["max_tick_gap_ms"] = max(record["max_tick_gap_ms"], (now - last) * 1000)
        last = now
        process = controller.process
        record["peak_parent_worker_rss_bytes"] = max(
            record["peak_parent_worker_rss_bytes"],
            rss(os.getpid()) + (rss(process.pid) if process else 0),
        )
        assert now - start < 60
    assert controller.errorText == "", controller.errorText
    return (time.monotonic() - start) * 1000


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "docs/evidence/phase07-headless.json",
    )
    args = parser.parse_args()
    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    record = dict(
        environment="ENV-07",
        date="2026-10-06",
        python=platform.python_version(),
        polars=pl.__version__,
        platform=platform.platform(),
        backend="offscreen/software",
        rows=100000,
        n=1,
        cache="warm developer host; no minimum hardware or cold cache claim",
        peak_parent_worker_rss_bytes=0,
        max_tick_gap_ms=0,
        page_parent_rss_bytes=[],
        page_ms=[],
        screenshots=[],
    )
    with tempfile.TemporaryDirectory(prefix="vu-phase07-") as temp:
        base = Path(temp)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        source = base / "large.parquet"
        pl.DataFrame(
            {
                "id": [f"{i:07}" for i in range(record["rows"])],
                "amount": list(range(record["rows"])),
                "category": ["A", "B"] * (record["rows"] // 2),
            }
        ).write_parquet(source)
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
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
            window.setProperty("selectedSection", 1)
            window.findChild(QObject, "datasetTabs").setProperty("currentIndex", 0)
            for i in range(16):
                data.goPage(i * 200)
                record["page_ms"].append(wait(app, data, record))
                record["page_parent_rss_bytes"].append(rss(os.getpid()))
                assert (
                    data.model.rowCount() == 200
                    and data.model.result["payload_bytes"] <= 4 * 1024 * 1024
                )
                assert data.model.data(data.model.index(0, 0)) == f"{i * 200:07}"
            amount = data.dataset()["import_metadata"]["columns"][1]["id"]
            data.selectColumn(amount)
            data.computeProfile(False, "dataset", 1)
            record["full_profile_ms"] = wait(app, data, record)
            assert (
                data.profileResult["unique"] == 100000
                and float(data.profileResult["numeric"]["mean"]) == 49999.5
            )
            assert float(data.profileResult["numeric"]["median"]) == 49999.5
            assert (
                len(data.profileResult["frequencies"]) == 20
                and data.profileResult["used_n"] == 100000
            )
            data.saveProfile()
            data.applyRole("measurement", "kg", "", "satış")
            projects.save()
            deadline = time.monotonic() + 10
            while projects.busy and time.monotonic() < deadline:
                app.processEvents()
                QTest.qWait(10)
            assert not projects.busy and not projects.dirty
            assert projects.closeProject() and projects.open(str(base / "project"))
            assert data.dataset()["semantic_metadata"][amount]["unit"] == "kg"
            data.selectColumn(amount)
            data.refresh()
            wait(app, data, record)
            data.computeProfile(True, "dataset", 1)
            wait(app, data, record)
            assert (
                data.profileResult["scope"] == "sample"
                and data.profileResult["used_n"] == 10000
            )
            for width, theme in ((1366, "light"), (720, "dark")):
                window.setWidth(width)
                window.setHeight(900 if width == 1366 else 800)
                preferences = app._veri_ufku_resources[-2]
                preferences.setTheme(theme)
                app.processEvents()
                QTest.qWait(150)
                flick = window.findChild(QObject, "workspace").property("contentItem")
                for section, field in (
                    ("table", "datasetTable"),
                    ("column", "columnRole"),
                    ("profile", "columnProfileSummary"),
                ):
                    top = (
                        window.findChild(QObject, field)
                        .mapToItem(flick.property("contentItem"), QPointF(0, 0))
                        .y()
                    )
                    flick.setProperty("contentY", max(0, top - 70))
                    app.processEvents()
                    QTest.qWait(120)
                    path = args.output.parent / f"phase07-{width}-{theme}-{section}.png"
                    assert window.grabWindow().save(str(path))
                    record["screenshots"].append(str(path))
            assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
            assert not list(Path(data.cache).glob("view-*"))
            record["source_sha256_unchanged"] = source_hash
            record["max_page_model_rows"] = 200
            values = record["page_parent_rss_bytes"][3:]
            record["steady_parent_rss_range_bytes"] = max(values) - min(values)
            assert record["steady_parent_rss_range_bytes"] < 32 * 1024 * 1024
            record["wheel_package"] = (
                str(veri_ufku.__file__) if args.package_root else None
            )
            args.output.write_text(
                json.dumps(record, ensure_ascii=False, indent=2) + "\n"
            )
            print(json.dumps(record, ensure_ascii=False))
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
