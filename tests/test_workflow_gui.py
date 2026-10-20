"""Actual QML editor/actions share the headless engine and immutable artifacts."""

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_workflow import node, recipe

CAPTURE = None


def imported(tmp_path, monkeypatch):
    source = tmp_path / "input.parquet"
    pl.DataFrame(
        {"x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0], "y": [2.0, 4.1, 5.9, 8.0, 10.1, 11.9]}
    ).write_parquet(source)
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    c = app._veri_ufku_resources[0]._workflow_resources
    assert c.process is None
    imports.choose(str(source))
    spin(app, lambda: not imports.busy and not projects.busy)
    imports.importData(True)
    spin(app, lambda: not imports.busy and not projects.busy)
    assert not imports.errorText, imports.errorText
    spin(app, lambda: not c.data.busy)
    c.data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
    spin(app, lambda: c.canAct)
    window.setProperty("selectedSection", 2)
    window.findChild(QObject, "workflowExpanded").setProperty("checked", True)
    return app, window, projects, c, source


def test_gui_typed_editor_dry_run_and_cli_equivalence(tmp_path, monkeypatch):
    app, window, projects, c, source = imported(tmp_path, monkeypatch)
    before = source.read_bytes()
    try:
        window.findChild(QObject, "workflowReset").clicked.emit()
        assert len(c.nodes) == 1
        window.findChild(QObject, "workflowColumn").setProperty("currentIndex", 0)
        window.findChild(QObject, "workflowAdd").clicked.emit()
        assert len(c.nodes) == 2, c.errorText
        window.findChild(QObject, "workflowHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert (
            app._veri_ufku_resources[0]._learning_resources.article["id"]
            == "workflow-dag"
        )
        window.setProperty("infoOpen", False)
        window.findChild(QObject, "workflowEdgeTarget").setProperty("text", "summary")
        window.findChild(QObject, "workflowEdgeSource").setProperty("text", "summary")
        window.findChild(QObject, "workflowConnect").clicked.emit()
        assert "port/type" in c.errorText and len(c.nodes) == 2
        window.findChild(QObject, "workflowEdgeSource").setProperty("text", "source")
        window.findChild(QObject, "workflowConnect").clicked.emit()
        assert not c.errorText
        window.findChild(QObject, "workflowEdgeTarget").setProperty("text", "source")
        window.findChild(QObject, "workflowAfter").setProperty("text", "summary")
        window.findChild(QObject, "workflowSetAfter").clicked.emit()
        assert "cycle" in c.errorText
        window.findChild(QObject, "workflowAfter").setProperty("text", "")
        window.findChild(QObject, "workflowSetAfter").clicked.emit()
        assert not c.errorText
        window.findChild(QObject, "workflowDryRun").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.active["status"] == "dry_run"
        assert all(n["status"] == "planned" for n in c.active["nodes"])
        window.findChild(QObject, "workflowRun").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.active["status"] == "completed"
        numeric = next(n for n in c.active["nodes"] if n["node"] == "summary")["value"][
            "report"
        ]["numeric"]
        assert numeric["mean"] == "3.5"
        spec = copy.deepcopy(c.spec)
        # CLI gets its own writable project copy; the GUI keeps its existing writer lock.
        copied = tmp_path / "cli-project"
        import shutil

        shutil.copytree(
            projects.store.root, copied, ignore=shutil.ignore_patterns(".writer.lock")
        )
        dag = tmp_path / "dag.json"
        dag.write_text(json.dumps(spec))
        output = tmp_path / "cli.json"
        error = tmp_path / "cli.stderr"
        env = {
            **os.environ,
            "PYTHONPATH": str(
                Path(__import__("veri_ufku").__file__).resolve().parent.parent
            ),
        }
        with output.open("w") as out, error.open("w") as err:
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "veri_ufku.operations.workflow_cli",
                    "--project",
                    str(copied),
                    "--dag",
                    str(dag),
                    "--cache",
                    str(tmp_path / "cli-cache"),
                ],
                stdout=out,
                stderr=err,
                env=env,
                cwd=tmp_path,
            )
            spin(app, lambda: proc.poll() is not None, timeout=60000)
        assert proc.returncode == 0, error.read_text()
        from contextlib import closing

        from veri_ufku.storage.neural_store import load
        from veri_ufku.storage.project_store import ProjectStore

        with closing(ProjectStore.open(copied)) as store:
            result = load(store, store.state["results"][-1])
            actual = next(n for n in result["nodes"] if n["node"] == "summary")[
                "value"
            ]["report"]["numeric"]
            assert numeric == actual
        assert source.read_bytes() == before
        if CAPTURE:
            CAPTURE(app, window, projects, c, "gui-cli")
        window.findChild(QObject, "workflowOpen").clicked.emit()
        assert c.process is None and c.staleResult
    finally:
        teardown(app, window)


def test_gui_full_dag_export_cache_and_invalid_edit(tmp_path, monkeypatch):
    app, window, projects, c, source = imported(tmp_path, monkeypatch)
    try:
        d = c.data.dataset()
        spec = recipe(
            dict(version_id=d["version_id"], columns=d["import_metadata"]["columns"]),
            True,
        )
        x = d["import_metadata"]["columns"][0]["id"]
        spec["nodes"].insert(
            1,
            node(
                "rename",
                "transform",
                dict(kind="rename", columns=[x], parameters=dict(name="renamed")),
                "source",
            ),
        )
        next(n for n in spec["nodes"] if n["kind"] == "quality")["inputs"]["data"][
            "node"
        ] = "rename"
        next(n for n in spec["nodes"] if n["kind"] == "predict")["inputs"]["data"][
            "node"
        ] = "rename"
        window.findChild(QObject, "workflowEditor").setProperty(
            "text", json.dumps(spec)
        )
        window.findChild(QObject, "workflowApply").clicked.emit()
        assert len(c.nodes) == 7, c.errorText
        out = tmp_path / "exports"
        out.mkdir()
        window.findChild(QObject, "workflowOutput").setProperty("text", str(out))
        window.findChild(QObject, "workflowExportConsent").setProperty("checked", True)
        window.findChild(QObject, "workflowRun").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.active["status"] == "completed", c.active["nodes"]
        assert pl.read_parquet(next(out.glob("*.parquet"))).height == 6
        window.findChild(QObject, "workflowToken").setProperty(
            "text", c.active["workflow_runtime"]["export_token"]
        )
        window.findChild(QObject, "workflowRun").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.active["export_receipts"][0]["status"] == "already_published"
        assert (
            next(n for n in c.active["nodes"] if n["kind"] == "train")["status"]
            == "cached"
        )
        if CAPTURE:
            CAPTURE(app, window, projects, c, "train-export")
        window.findChild(QObject, "workflowEditor").setProperty("text", "{}")
        window.findChild(QObject, "workflowApply").clicked.emit()
        assert c.spec is None and c.errorText
        old = len(projects.draft["results"])
        c.start(False, True, str(out), "")
        assert c.process is None and len(projects.draft["results"]) == old
    finally:
        teardown(app, window)


@pytest.mark.parametrize("mode", ["cancel", "timeout"])
def test_gui_cancel_timeout_keeps_previous_result(tmp_path, monkeypatch, mode):
    from dataclasses import replace

    app, window, projects, c, _ = imported(tmp_path, monkeypatch)
    try:
        c.reset()
        c.start(True, False, "", "")
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        previous = copy.deepcopy(projects.draft["results"])
        if mode == "timeout":
            c.budget = replace(c.budget, max_wall_seconds=0.001)
        window.findChild(QObject, "workflowRun").clicked.emit()
        if mode == "cancel":
            window.findChild(QObject, "workflowCancel").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert projects.draft["results"][: len(previous)] == previous
        assert c.errorText or c.active["status"] != "completed"
        assert c.process is None
        if CAPTURE:
            CAPTURE(app, window, projects, c, mode)
    finally:
        teardown(app, window)


def test_gui_existing_chain_to_dag(tmp_path, monkeypatch):
    from veri_ufku.operations.contracts import build
    from veri_ufku.operations.engine import calculate
    from veri_ufku.operations.workflow_service import references

    app, window, projects, c, _ = imported(tmp_path, monkeypatch)
    try:
        original = c.data.dataset()
        r = references(projects.store, projects.draft)[original["version_id"]]
        with __import__("tempfile").TemporaryDirectory() as work:
            result = calculate(
                r,
                build(r, "rename", [r["columns"][0]["id"]], dict(name="renamed")),
                work,
            )
            renamed = projects.store.publish_operation(result)
        projects.draft = copy.deepcopy(projects.store.state)
        projects.saved = copy.deepcopy(projects.draft)
        projects.changed.emit()
        spin(app, lambda: not c.data.busy and not projects.busy)
        assert c.data.dataset()["version_id"] == renamed["version_id"]
        window.findChild(QObject, "workflowChain").clicked.emit()
        assert not c.errorText, c.errorText
        assert [n["kind"] for n in c.nodes] == ["source", "transform"]
        window.findChild(QObject, "workflowRun").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.active["status"] == "completed"
        transform = next(n for n in c.active["nodes"] if n["kind"] == "transform")
        native = pl.read_parquet(
            projects.store.path(transform["value"]["request"]["path"])
        )
        assert "renamed" in native.columns and native.height == 6
        if CAPTURE:
            CAPTURE(app, window, projects, c, "chain")
    finally:
        teardown(app, window)
