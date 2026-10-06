"""Headless project workflow and genuine rendered screenshots, isolated on local FS."""

import hashlib
import json
import os
import platform
import sqlite3
import tempfile
import time
from importlib.metadata import version
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from veri_ufku.app import create_application  # noqa: E402
from veri_ufku.storage.project_store import CRASH_POINTS, filesystem  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence"


def wait(app, projects):
    deadline = time.monotonic() + 10
    while projects.busy and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(10)
    assert not projects.busy, "Project I/O timed out"
    assert not projects.errorText, projects.errorText


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix=".phase04-measure-", dir=ROOT) as temporary:
        base = Path(temporary)
        for name, part in (
            ("XDG_CONFIG_HOME", "config"),
            ("XDG_STATE_HOME", "state"),
            ("XDG_CACHE_HOME", "cache"),
        ):
            os.environ[name] = str(base / part)
        app, window, bridge = create_application()
        projects = app._veri_ufku_resources[0]._projects_resources
        record = dict(
            environment="ENV-04",
            date="2026-10-06",
            os=platform.platform(),
            python=platform.python_version(),
            qt=version("PySide6"),
            polars=version("polars"),
            sqlite=sqlite3.sqlite_version,
            filesystem=filesystem(base),
            backend="offscreen/software",
            lock_sha256=hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
            fixture_sha256=hashlib.sha256(
                (ROOT / "tests/fixtures/projects/schema0.json").read_bytes()
            ).hexdigest(),
            crash_points=list(CRASH_POINTS),
            screenshots=[],
            steps=[],
        )
        try:
            projects.request("create", str(base / "project"))
            wait(app, projects)
            projects.setName("Veri_Ufku kayıt denemesi")
            projects.setSeed("42")
            projects.learning.setDepth(2)
            source = base / "measurements.csv"
            source.write_bytes("ölçüm;etiket\n1;A\n2;B\n".encode())
            source_before = source.read_bytes()
            projects.request("addSource", str(source), "", True)
            wait(app, projects)
            window.findChild(QObject, "saveProjectButton").clicked.emit()
            wait(app, projects)
            assert not projects.dirty
            record["steps"].append("create/name/seed/help/source-copy/save")
            assert projects.closeProject(False)
            projects.request("open", str(base / "project"))
            wait(app, projects)
            assert projects.seedText == "42" and projects.learning.depth == 2
            assert source.read_bytes() == source_before
            record["source_unchanged"] = True
            record["steps"].append("close/reopen/state-preserved")
            for width, height, theme, scale in (
                (1366, 900, "light", 1.0),
                (720, 560, "dark", 2.0),
            ):
                preferences = app._veri_ufku_resources[6]
                preferences.setTheme(theme)
                preferences.setTextScale(scale)
                window.setWidth(width)
                window.setHeight(height)
                app.processEvents()
                QTest.qWait(150)
                filename = f"phase04-headless-{width}-{theme}.png"
                assert window.grabWindow().save(str(EVIDENCE / filename))
                record["screenshots"].append(filename)
                if width == 720:
                    workspace = window.findChild(QObject, "workspace")
                    flickable = workspace.property("contentItem")
                    assert flickable.setProperty("contentY", 900)
                    app.processEvents()
                    QTest.qWait(150)
                    filename = "phase04-headless-720-dark-scrolled.png"
                    assert window.grabWindow().save(str(EVIDENCE / filename))
                    record["screenshots"].append(filename)
            source.unlink()
            projects.refreshSources()
            wait(app, projects)
            assert "eksik" in projects.sourceSummary
            record["steps"].append("missing-source-metadata-remains-open")
            projects.setName("Otomatik kurtarma")
            projects.request("autosave")
            wait(app, projects)
            assert projects.closeProject(True)
            projects.request("open", str(base / "project"))
            wait(app, projects)
            assert projects.name == "Veri_Ufku kayıt denemesi"
            projects.request("restore")
            wait(app, projects)
            assert projects.name == "Otomatik kurtarma" and projects.dirty
            record["steps"].append("autosave-separate/explicit-restore")
            projects.request("saveAs", str(base / "copy"))
            wait(app, projects)
            assert projects.name == "Otomatik kurtarma" and not projects.dirty
            record["steps"].append("save-as-completed-copy")
            record["result"] = "pass"
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
        (EVIDENCE / "phase04-headless.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n"
        )
        print("PHASE04_HEADLESS PASS")
