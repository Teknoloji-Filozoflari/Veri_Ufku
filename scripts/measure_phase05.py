"""Actual first-import baseline and rendered UI, isolated on the local filesystem."""

import hashlib
import json
import os
import platform
import tempfile
import time
from importlib.metadata import version
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject, QPointF  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from veri_ufku.app import create_application  # noqa: E402
from veri_ufku.storage.project_store import filesystem  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence"


def rss(pid):
    try:
        return next(
            int(line.split()[1]) * 1024
            for line in Path(f"/proc/{pid}/status").read_text().splitlines()
            if line.startswith("VmRSS:")
        )
    except (OSError, StopIteration):
        return 0


def wait(app, imports, record):
    started = time.monotonic()
    while imports.busy:
        app.processEvents()
        QTest.qWait(10)
        now = time.monotonic()
        record["max_tick_gap_ms"] = max(
            record["max_tick_gap_ms"], (now - started) * 1000
        )
        started = now
        pid = imports.process.pid if imports.process else None
        record["sampled_peak_rss_bytes"] = max(
            record["sampled_peak_rss_bytes"],
            rss(os.getpid()) + (rss(pid) if pid else 0),
        )
        used = (
            sum(
                p.stat().st_size
                for p in Path(imports.workspace).glob("*")
                if p.is_file()
            )
            if imports.workspace
            else 0
        )
        record["sampled_peak_worker_disk_bytes"] = max(
            record["sampled_peak_worker_disk_bytes"], used
        )
        assert now - imports.started < 90, "measurement timed out"
    assert not imports.errorText, imports.errorText


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix=".phase05-measure-", dir=ROOT) as temporary:
        base = Path(temporary)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        app, window, bridge = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports = engine._projects_resources, engine._imports_resources
        record = dict(
            environment="ENV-05",
            date="2026-10-06",
            python=platform.python_version(),
            os=platform.platform(),
            qt=version("PySide6"),
            polars=version("polars"),
            filesystem=filesystem(base),
            backend="offscreen/software",
            lock_sha256=hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
            sampled_peak_rss_bytes=0,
            sampled_peak_worker_disk_bytes=0,
            max_tick_gap_ms=0,
            screenshots=[],
            n=1,
            cache="warm; no cold-cache claim",
        )
        try:
            assert projects.create(str(base / "project"))
            window.setProperty("selectedSection", 1)
            fixture = ROOT / "tests/fixtures/delimited/reference_utf8.csv"
            original = hashlib.sha256(fixture.read_bytes()).hexdigest()
            record["fixture_sha256"] = original
            start = time.monotonic()
            imports.choose(str(fixture))
            wait(app, imports, record)
            record["small_capture_preview_ms"] = (time.monotonic() - start) * 1000
            imports.setOption("thousands", ".")
            imports.setOption("date_format", "%d.%m.%Y")
            imports.setType(2, "decimal")
            imports.setType(3, "date")
            imports.refreshPreview()
            wait(app, imports, record)
            for width, height, theme, scale in (
                (1366, 900, "light", 1.0),
                (720, 560, "dark", 2.0),
            ):
                preferences = app._veri_ufku_resources[-2]
                preferences.setTheme(theme)
                preferences.setTextScale(scale)
                window.setWidth(width)
                window.setHeight(height)
                app.processEvents()
                window.findChild(QObject, "workspace").property(
                    "contentItem"
                ).setProperty("contentY", 0)
                QTest.qWait(150)
                name = f"phase05-headless-{width}-{theme}.png"
                assert window.grabWindow().save(str(OUT / name))
                record["screenshots"].append(name)
                button = window.findChild(QObject, "importCsvButton")
                button.forceActiveFocus()
                flick = window.findChild(QObject, "workspace").property("contentItem")
                button_top = button.mapToItem(
                    flick.property("contentItem"), QPointF(0, 0)
                ).y()
                flick.setProperty(
                    "contentY", max(0, button_top + button.height() - flick.height())
                )
                app.processEvents()
                QTest.qWait(150)
                name = f"phase05-headless-{width}-{theme}-table.png"
                assert window.grabWindow().save(str(OUT / name))
                record["screenshots"].append(name)
                if width == 720:
                    field = window.findChild(QObject, "importDelimiter")
                    top = field.mapToItem(
                        flick.property("contentItem"), QPointF(0, 0)
                    ).y()
                    flick.setProperty("contentY", top - 50)
                    app.processEvents()
                    QTest.qWait(100)
                    name = "phase05-headless-720-dark-form.png"
                    assert window.grabWindow().save(str(OUT / name))
                    record["screenshots"].append(name)
                    table = window.findChild(QObject, "csvPreviewTable")
                    top = table.mapToItem(
                        flick.property("contentItem"), QPointF(0, 0)
                    ).y()
                    flick.setProperty("contentY", top - 60)
                    app.processEvents()
                    QTest.qWait(100)
                    name = "phase05-headless-720-dark-preview.png"
                    assert window.grabWindow().save(str(OUT / name))
                    record["screenshots"].append(name)
            imports.importData(True)
            wait(app, imports, record)
            assert len(projects.draft["datasets"]) == 1 and not projects.dirty
            assert hashlib.sha256(fixture.read_bytes()).hexdigest() == original
            assert projects.closeProject() and projects.open(str(base / "project"))
            assert projects.draft["datasets"][0]["import_metadata"]["row_count"] == 3
            large = base / "large.csv"
            with large.open("w") as stream:
                stream.write("id,ad\n")
                for _ in range(180000):
                    stream.write("001,Çağrı\n")
            record["cancel_fixture_bytes"] = large.stat().st_size
            record["cancel_fixture_rows"] = 180000
            imports.choose(str(large))
            wait(app, imports, record)
            start = time.monotonic()
            imports.importData()
            wait(app, imports, record)
            record["full_import_rows"] = 180000
            record["full_import_ms"] = (time.monotonic() - start) * 1000
            assert (
                projects.draft["datasets"][-1]["import_metadata"]["row_count"] == 180000
            )
            imports.refreshPreview()
            wait(app, imports, record)
            active = projects.store.path("ACTIVE").read_bytes()
            imports.importData()
            QTest.qWait(200)
            app.processEvents()
            start = time.monotonic()
            imports.cancel()
            record["cancel_feedback_ms"] = (time.monotonic() - start) * 1000
            wait(app, imports, record)
            record["cancel_exit_ms"] = (time.monotonic() - start) * 1000
            assert projects.store.path("ACTIVE").read_bytes() == active
            record["source_unchanged"] = True
            record["result"] = "pass"
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
        record["worker_directories_after_cleanup"] = len(
            list((base / "cache/veri_ufku/imports").glob("csv-*"))
        )
        (OUT / "phase05-headless.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n"
        )
        print("PHASE05_HEADLESS PASS", json.dumps(record, ensure_ascii=False))
