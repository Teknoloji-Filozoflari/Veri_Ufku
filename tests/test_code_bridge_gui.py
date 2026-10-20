"""Actual QML export and explicit code lifecycle, with no project-open execution."""

import json
import os
import subprocess
import sys
import time
import zipfile
from contextlib import closing
from pathlib import Path

import polars as pl
import pytest
from PySide6.QtCore import QObject, QTimer
from test_import_gui import setup, spin, teardown

from veri_ufku.storage.project_store import ProjectStore

CAPTURE = None


def imported(tmp_path, monkeypatch):
    source = tmp_path / "profile.parquet"
    pl.DataFrame({"amount": [1.0, 2.0, 3.0, 4.0, None]}).write_parquet(source)
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    c = engine._code_resources
    data = c.data
    assert c.process is None and c.future is None
    imports.choose(str(source))
    spin(app, lambda: not imports.busy and not projects.busy)
    assert imports.ready, imports.errorText
    imports.importData(True)
    spin(app, lambda: not imports.busy and not projects.busy)
    assert not imports.errorText, imports.errorText
    spin(app, lambda: not data.busy)
    data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
    spin(app, lambda: not data.busy)
    window.setProperty("selectedSection", 6)
    window.findChild(QObject, "codeExpanded").setProperty("checked", True)
    spin(app, lambda: c.canAct)
    return app, window, projects, c, source


@pytest.mark.parametrize("fmt", ["python", "sql", "notebook"])
def test_gui_profile_export(tmp_path, monkeypatch, fmt):
    app, window, projects, c, source = imported(tmp_path, monkeypatch)
    before = source.read_bytes()
    try:
        c.data.column_id = c.data.dataset()["import_metadata"]["columns"][0]["id"]
        c.data.computeProfile(False, "dataset", 1)
        spin(app, lambda: not c.data.busy and not projects.busy, timeout=60000)
        assert (
            c.data.profile_result and c.data.profile_result["numeric"]["mean"] == "2.5"
        )
        window.findChild(QObject, "codeHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert (
            app._veri_ufku_resources[0]._learning_resources.article["id"]
            == "code-equivalence"
        )
        window.setProperty("infoOpen", False)
        dest = tmp_path / (fmt + ".zip")
        window.findChild(QObject, "codeFormat").setProperty(
            "currentIndex", ["python", "sql", "notebook"].index(fmt)
        )
        window.findChild(QObject, "codeDestination").setProperty("text", str(dest))
        spin(app, lambda: c.canAct)
        window.findChild(QObject, "codeExport").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert (
            dest.is_file()
            and c.receipt["format"] == fmt
            and source.read_bytes() == before
        )
        folder = tmp_path / ("unpacked-" + fmt)
        folder.mkdir()
        with zipfile.ZipFile(dest) as z:
            z.extractall(folder)
        output = tmp_path / (fmt + "-result.json")
        env = {
            **os.environ,
            "PYTHONPATH": str(
                Path(__import__("veri_ufku").__file__).resolve().parent.parent
            ),
        }
        runner = subprocess.Popen(
            [
                sys.executable,
                str(folder / "run.py"),
                "--project",
                str(projects.store.root),
                "--output",
                str(output),
                *(["--sql"] if fmt == "sql" else []),
            ],
            cwd=tmp_path,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        spin(app, lambda: runner.poll() is not None, timeout=60000)
        stderr = runner.stderr.read().decode()
        runner.stderr.close()
        assert runner.returncode == 0, stderr
        replay = json.loads(output.read_text())["result"]
        if fmt == "sql":
            assert (
                replay["mean"] == 2.5
                and replay["finite_n"] == c.data.profile_result["numeric"]["finite_n"]
            )
        else:
            assert replay["numeric"] == c.data.profile_result["numeric"]
        assert c.process is None and not [
            r
            for r in projects.draft["results"]
            if r.get("neural", {}).get("schema") == "CodeRun/v1"
        ]
        if CAPTURE:
            CAPTURE(app, window, projects, c, "export-" + fmt)
    finally:
        teardown(app, window)


@pytest.mark.parametrize("mode", ["success", "cancel", "timeout"])
def test_gui_explicit_code_run_and_reopen_no_autorun(tmp_path, monkeypatch, mode):
    app, window, projects, c, source = imported(tmp_path, monkeypatch)
    ticks = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(time.monotonic()))
    timer.start()
    try:
        window.findChild(QObject, "codeEnable").setProperty("checked", True)
        editor = window.findChild(QObject, "codeEditor")
        text = (
            'print("Türkçe çıktı")\nprint("token=TOP_SECRET_GUI")'
            if mode == "success"
            else 'import time\nprint("started",flush=True)\ntime.sleep(30)'
        )
        editor.setProperty("text", text)
        hash1 = c.codeHash
        rev = c.revision
        assert c.process is None
        window.findChild(QObject, "codeSaveHash").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy)
        assert c.active["status"] == "draft" and c.process is None
        # Different code edit changes config lineage, still no execution.
        editor.setProperty("text", text + "\n# edit changes lineage")
        assert c.codeHash != hash1 and c.revision > rev
        window.findChild(QObject, "codeTimeout").setProperty(
            "text", ".3" if mode == "timeout" else "5"
        )
        spin(app, lambda: c.canAct)
        window.findChild(QObject, "codeRun").clicked.emit()
        if mode == "cancel":
            spin(app, lambda: c.process is not None and "started" in c.outputText)
            start = time.monotonic()
            window.findChild(QObject, "codeCancel").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=30000)
        assert not c.errorText, c.errorText
        expected = {"success": "completed", "cancel": "canceled", "timeout": "timeout"}[
            mode
        ]
        assert c.active["status"] == expected, c.active
        assert c.active["kernel_pid"] != os.getpid() and c.active["kernel_pid"] > 0
        if mode == "cancel":
            assert time.monotonic() - start < 4
        assert len(ticks) > 3
        assert "TOP_SECRET_GUI" not in c.outputText
        if mode == "success":
            assert "Türkçe çıktı" in c.outputText and "[MASKED]" in c.outputText
            assert (
                window.findChild(QObject, "codeOutput").property("text") == c.outputText
            )
            if CAPTURE:
                CAPTURE(app, window, projects, c, "success-output")
        assert c.active["code_recipe"]["cell_hash"] == c.codeHash
        logroot = tmp_path / "state"
        for log in logroot.rglob("*.log"):
            assert (
                "TOP_SECRET_GUI" not in log.read_text()
                and "Türkçe çıktı" not in log.read_text()
            )
        raw = json.dumps(projects.draft)
        assert "TOP_SECRET_GUI" not in raw and "Türkçe çıktı" not in raw
        # Opening a persisted record has no code source or auto-run action.
        saved = next(r for r in reversed(c.savedRuns) if expected in r["label"])
        c.openRecord(saved["id"])
        assert (
            c.process is None and c.outputText == "" and c.active["status"] == expected
        )
        if CAPTURE:
            CAPTURE(app, window, projects, c, mode)
        root = Path(projects.store.root)
        with closing(ProjectStore.open(root, writable=False)) as reopened:
            assert any(
                r.get("neural", {}).get("status") == expected
                for r in reopened.state["results"]
            )
        assert c.process is None
        assert projects.closeProject(False)
        assert c.process is None
        assert projects.open(str(root))
        assert c.process is None and c.future is None
        app.processEvents()
        assert c.process is None
    finally:
        timer.stop()
        teardown(app, window)


def test_invalid_code_never_runs_old_editor(tmp_path, monkeypatch):
    app, window, projects, c, source = imported(tmp_path, monkeypatch)
    try:
        c.setCode('print("old")')
        c.setCode("x" * 17000)
        c.execute(True, 1)
        assert c.process is None and c.future is None and c.errorText
        c.setCode('print("new")')
        c.execute(False, 1)
        assert c.process is None and c.future is None and "sandbox" in c.errorText
    finally:
        teardown(app, window)
