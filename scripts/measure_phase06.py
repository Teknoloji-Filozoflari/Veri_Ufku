"""Real native preview/import timing, bounded UI render and immutable-source hashes."""

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
from PySide6 import __version__ as qt_version  # noqa: E402
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
    start = last = time.monotonic()
    while imports.busy:
        app.processEvents()
        QTest.qWait(10)
        now = time.monotonic()
        record["max_tick_gap_ms"] = max(record["max_tick_gap_ms"], (now - last) * 1000)
        last = now
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
        assert now - start < 45
    return (time.monotonic() - start) * 1000


if __name__ == "__main__":
    record = dict(
        environment="ENV-06",
        date="2026-10-06",
        python=platform.python_version(),
        os=platform.platform(),
        qt=qt_version,
        polars=pl.__version__,
        backend="offscreen/software",
        lock_sha256=hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
        cpu=next(
            (
                line.split(":", 1)[1].strip()
                for line in Path("/proc/cpuinfo").read_text().splitlines()
                if line.startswith("model name")
            ),
            platform.processor(),
        ),
        ram_bytes=os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE"),
        n=1,
        cache="warm; no cold-cache or minimum-hardware claim",
        max_tick_gap_ms=0,
        sampled_peak_rss_bytes=0,
        sampled_peak_worker_disk_bytes=0,
        screenshots=[],
        cases=[],
    )
    with tempfile.TemporaryDirectory(prefix=".phase06-measure-", dir=ROOT) as temporary:
        base = Path(temporary)
        record["filesystem"] = filesystem(base)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        parquet = base / "nullable.parquet"
        pl.DataFrame(
            {
                "nullable": pl.Series([1, None], dtype=pl.Int16),
                "date": pl.Series([None, None], dtype=pl.Date),
            }
        ).write_parquet(parquet)
        app, window, bridge = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports = engine._projects_resources, engine._imports_resources
        try:
            assert projects.create(str(base / "project"))
            window.setProperty("selectedSection", 1)
            fixture = ROOT / "tests/fixtures/structured"
            for path, adapter, options in (
                (
                    fixture / "nested.json",
                    "json",
                    {
                        "record_path": "/payload/records",
                        "flatten": True,
                        "expand_lists": "/items|/tags",
                    },
                ),
                (fixture / "records.ndjson", "jsonl", {"bad_rows": "quarantine"}),
                (fixture / "workbook.xlsx", "xlsx", {"sheet": "Diğer"}),
                (parquet, "parquet", {}),
            ):
                before = hashlib.sha256(path.read_bytes()).hexdigest()
                imports.choose(str(path))
                capture_ms = wait(app, imports, record)
                for key, value in options.items():
                    imports.setOption(key, value)
                imports.refreshPreview()
                preview_ms = wait(app, imports, record)
                assert imports.ready, imports.errorText
                for width, height, theme, scale in (
                    (1366, 900, "light", 1.0),
                    (720, 560, "dark", 2.0),
                ):
                    app._veri_ufku_resources[-2].setTheme(theme)
                    app._veri_ufku_resources[-2].setTextScale(scale)
                    window.setWidth(width)
                    window.setHeight(height)
                    app.processEvents()
                    QTest.qWait(120)
                    flick = window.findChild(QObject, "workspace").property(
                        "contentItem"
                    )
                    field = window.findChild(
                        QObject,
                        "jsonRecordPath"
                        if adapter == "json"
                        else "excelSheet"
                        if adapter == "xlsx"
                        else "csvPreviewTable",
                    )
                    top = field.mapToItem(
                        flick.property("contentItem"), QPointF(0, 0)
                    ).y()
                    flick.setProperty("contentY", max(0, top - 70))
                    app.processEvents()
                    QTest.qWait(120)
                    name = f"phase06-{adapter}-{width}-{theme}.png"
                    assert window.grabWindow().save(str(OUT / name))
                    record["screenshots"].append(name)
                imports.importData(True)
                import_ms = wait(app, imports, record)
                assert not imports.errorText, imports.errorText
                d = projects.draft["datasets"][-1]
                assert hashlib.sha256(path.read_bytes()).hexdigest() == before
                record["cases"].append(
                    dict(
                        adapter=adapter,
                        fixture_sha256=before,
                        bytes=path.stat().st_size,
                        capture_preview_ms=capture_ms,
                        repreview_ms=preview_ms,
                        full_import_publish_ms=import_ms,
                        rows=d["import_metadata"]["row_count"],
                        bad=d["import_metadata"]["bad_count"],
                    )
                )
            assert projects.closeProject() and projects.open(str(base / "project"))
            assert len(projects.draft["datasets"]) == 4
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
    (OUT / "phase06-headless.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    )
    print("PHASE06_HEADLESS PASS", json.dumps(record, ensure_ascii=False))
