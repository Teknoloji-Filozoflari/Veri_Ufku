"""Actual QML controls → isolated CPU computation → immutable save/reopen."""

import os

import polars as pl
import pytest
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_patterns import frame, ts

CAPTURE = None
TASKS = ["apriori", "fp_growth", "cohort", "funnel", "process", "conformance"]


def imported(tmp_path, monkeypatch, task, large=False):
    source = tmp_path / "patterns.parquet"
    data = frame(task)
    if large:
        data = pl.DataFrame(
            [
                dict(entity=f"t{i}", activity=f"i{(i + j) % 50}")
                for i in range(500)
                for j in range(10)
            ]
        )
    data.write_parquet(source)
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    controller = engine._pattern_resources
    imports.choose(str(source))
    spin(app, lambda: not imports.busy and not projects.busy)
    assert imports.ready, imports.errorText
    imports.importData(True)
    spin(app, lambda: not imports.busy and not projects.busy)
    spin(app, lambda: not controller.data.busy)
    controller.data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
    spin(app, lambda: not controller.data.busy)
    engine._workspace_resources.activate("model.pattern." + task.replace("_", "-"))
    window.setProperty("selectedSection", 5)
    columns = controller.column_rows()
    for role, name in (
        ("Entity", "entity"),
        ("Activity", "activity"),
        ("Time", "timestamp"),
        ("Order", "order"),
        ("Complete", "complete"),
    ):
        indices = [i for i, c in enumerate(columns) if c["name"] == name]
        if indices:
            window.findChild(QObject, "pattern" + role).setProperty(
                "currentIndex", indices[0]
            )
    if task == "cohort":
        window.findChild(QObject, "patternObservationStart").setProperty(
            "text", str(ts("2026-01-01"))
        )
        window.findChild(QObject, "patternObservationEnd").setProperty(
            "text", str(ts("2026-03-15"))
        )
        window.findChild(QObject, "patternCohortStart").setProperty("currentIndex", 1)
    if task in ("process", "conformance"):
        window.findChild(QObject, "patternUseComplete").setProperty("checked", True)
    window.findChild(QObject, "patternStages").setProperty("text", "view,cart,buy")
    window.findChild(QObject, "patternConformanceModel").setProperty(
        "text",
        '{"schema":"ActivityTransitionModel/v1","starts":["view"],"ends":["buy"],"edges":[["view","cart"],["cart","buy"]]}',
    )
    return app, window, projects, controller, source


@pytest.mark.parametrize("task", TASKS)
def test_real_patterns(tmp_path, monkeypatch, task):
    app, window, projects, controller, source = imported(tmp_path, monkeypatch, task)
    before = source.read_bytes()
    assert "Yerel sepet" in controller.message
    try:
        window.findChild(QObject, "patternHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert (
            app._veri_ufku_resources[0]._learning_resources.article["id"]
            == "pattern-support"
        )
        window.setProperty("infoOpen", False)
        window.findChild(QObject, "patternRun").clicked.emit()
        spin(app, lambda: not controller.busy, timeout=90000)
        assert not controller.errorText, controller.errorText
        assert (
            controller.active["status"] == "completed"
            and controller.active["worker_pid"] != os.getpid()
        )
        assert controller.active["analysis"]
        completed = next(
            v for v in reversed(controller.saved()) if "completed" in v["label"]
        )
        controller.active = None
        controller.openRun(completed["id"])
        assert controller.active["status"] == "completed"
        assert not controller.errorText, controller.errorText
        assert source.read_bytes() == before
        assert task in window.findChild(QObject, "patternSummary").property("text")
        assert "rows" not in controller.historyReport
        if task in ("process", "conformance"):
            assert controller.active["analysis"]["edges"][0]["count"] > 0

            def rendered_labels():
                items = [window.contentItem()]
                labels = []
                while items:
                    item = items.pop()
                    value = item.property("text")
                    if isinstance(value, str):
                        labels.append(value)
                    items.extend(item.childItems())
                return labels

            spin(
                app,
                lambda: any("fitting=unknown" in text for text in rendered_labels()),
            )
            assert not any("fitting=undefined" in text for text in rendered_labels())
        if CAPTURE:
            CAPTURE(app, window, projects, controller, task)
    finally:
        teardown(app, window)


def test_real_pattern_cancel(tmp_path, monkeypatch):
    app, window, projects, controller, _ = imported(
        tmp_path, monkeypatch, "apriori", large=True
    )
    try:
        window.findChild(QObject, "patternSupport").setProperty("text", "0.0001")
        window.findChild(QObject, "patternBudget").setProperty("text", "20000")
        window.findChild(QObject, "patternRun").clicked.emit()
        spin(
            app,
            lambda: (
                controller.stage == "checkpoint"
                and controller._incoming["status"] == "running"
            ),
            timeout=90000,
        )
        window.findChild(QObject, "patternCancel").clicked.emit()
        spin(app, lambda: not controller.busy, timeout=90000)
        assert controller.active["status"] == "canceled", (
            controller.errorText,
            controller.active["status"],
            controller.active["warnings"],
        )
        assert [
            r["model_choice"]["status"]
            for r in projects.draft["results"]
            if "model_choice" in r
        ][-1] == "canceled"
        if CAPTURE:
            CAPTURE(app, window, projects, controller, "canceled")
    finally:
        teardown(app, window)


def test_real_pattern_budget_failure(tmp_path, monkeypatch):
    app, window, projects, controller, _ = imported(tmp_path, monkeypatch, "apriori")
    try:
        window.findChild(QObject, "patternBudget").setProperty("text", "1")
        window.findChild(QObject, "patternRun").clicked.emit()
        spin(app, lambda: not controller.busy, timeout=90000)
        assert controller.active["status"] == "failed"
        assert "bütçe" in controller.errorText
        assert [
            r["model_choice"]["status"]
            for r in projects.draft["results"]
            if "model_choice" in r
        ][-1] == "failed"
        if CAPTURE:
            CAPTURE(app, window, projects, controller, "budget-failed")
    finally:
        teardown(app, window)
