"""Actual offscreen QML → isolated CPU worker → ProjectStore → list/export/reopen routes."""

import json
import os

import polars as pl
import pytest
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_recommendation import interactions

CAPTURE = None


def imported(tmp_path, monkeypatch, task, large=False):
    source = tmp_path / "events.parquet"
    frame = interactions(task == "ranker")
    if large:
        frame = pl.DataFrame(
            [
                dict(
                    user=f"u{u}",
                    item=f"i{i}",
                    strength=1.0,
                    timestamp=float(i + 1),
                    x=0.0,
                    y=1.0,
                    query=f"q{u}",
                )
                for u in range(32)
                for i in range(60)
            ]
            + [
                dict(
                    user=f"u{u}",
                    item="i0",
                    strength=1.0,
                    timestamp=200.0,
                    x=0.0,
                    y=1.0,
                    query=f"q{u}",
                )
                for u in range(32)
            ]
        )
    frame.write_parquet(source)
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    controller = engine._recommendation_resources
    imports.choose(str(source))
    spin(app, lambda: not imports.busy and not projects.busy)
    assert imports.ready, imports.errorText
    imports.importData(True)
    spin(app, lambda: not imports.busy and not projects.busy)
    assert not imports.errorText, imports.errorText
    spin(app, lambda: not controller.data.busy)
    controller.data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
    spin(app, lambda: not controller.data.busy)
    engine._workspace_resources.activate("model.recommendation." + task)
    window.setProperty("selectedSection", 5)
    spin(
        app,
        lambda: window.findChild(QObject, "recommendationExpanded").property("checked"),
    )
    columns = controller.column_rows()
    for role, name in (
        ("User", "user"),
        ("Item", "item"),
        ("Value", "strength"),
        ("Time", "timestamp"),
        ("Query", "query"),
    ):
        window.findChild(QObject, "recommendation" + role).setProperty(
            "currentIndex", next(i for i, c in enumerate(columns) if c["name"] == name)
        )
    if task in ("content", "ranker"):
        window.findChild(QObject, "recommendationFeatures").setProperty(
            "text", ",".join(c["id"] for c in columns if c["name"] in ("x", "y"))
        )
    window.findChild(QObject, "recommendationCutoff").setProperty("text", "8")
    window.findChild(QObject, "recommendationK").setProperty("text", "2")
    window.findChild(QObject, "recommendationEpochs").setProperty("text", "3")
    return app, window, projects, controller, source


@pytest.mark.parametrize("task", ["popularity", "content", "factorization", "ranker"])
def test_real_recommendation_gui(tmp_path, monkeypatch, task):
    app, window, projects, controller, source = imported(tmp_path, monkeypatch, task)
    original = source.read_bytes()
    try:
        window.findChild(QObject, "recommendationHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert (
            app._veri_ufku_resources[0]._learning_resources.article["id"]
            == "recommendation-feedback"
        )
        window.setProperty("infoOpen", False)
        button = window.findChild(QObject, "recommendationRun")
        assert button.property("enabled")
        button.clicked.emit()
        spin(app, lambda: not controller.busy, timeout=90000)
        assert not controller.errorText, controller.errorText
        assert controller.active["status"] == "completed"
        assert controller.active["worker_pid"] != os.getpid()
        record = projects.draft["results"][
            -2
        ]  # final complete choice follows checkpoint
        saved = controller.saved()
        completed = next(r for r in reversed(saved) if "completed" in r["label"])
        controller.active = None
        controller.openRun(completed["id"])
        assert controller.active["status"] == "completed", record
        payload = dict(user="private-new-user", items=["i0", "new-item"])
        if task == "ranker":
            payload["features"] = [
                dict(item="i0", values=[0, 1]),
                dict(item="new-item", values=[1, 0]),
            ]
        window.findChild(QObject, "recommendationRequest").setProperty(
            "text", json.dumps(payload)
        )
        window.findChild(QObject, "recommendationPredict").clicked.emit()
        spin(app, lambda: not controller.busy, timeout=90000)
        assert not controller.errorText, controller.errorText
        result = controller.predictionReport
        assert result["schema"] == "RecommendationList/v1" and result["fit"] is False
        assert len(result["recommendations"]) == 2
        assert "RecommendationList/v1" in window.findChild(
            QObject, "recommendationPrediction"
        ).property("text")
        destination = tmp_path / "recommendations.json"
        window.findChild(QObject, "recommendationDestination").setProperty(
            "text", str(destination)
        )
        window.findChild(QObject, "recommendationExport").clicked.emit()
        assert (
            destination.exists() and "private-new-user" not in destination.read_text()
        )
        assert source.read_bytes() == original
        assert all(
            "private-new-user" not in p.read_text()
            for p in (tmp_path / "state").rglob("*.log")
        )
        if CAPTURE:
            CAPTURE(app, window, projects, controller, task)
    finally:
        teardown(app, window)


def test_real_recommendation_cancel(tmp_path, monkeypatch):
    app, window, projects, controller, _ = imported(
        tmp_path, monkeypatch, "factorization", large=True
    )
    try:
        window.findChild(QObject, "recommendationCutoff").setProperty("text", "100")
        window.findChild(QObject, "recommendationEpochs").setProperty("text", "50")
        window.findChild(QObject, "recommendationFactors").setProperty("text", "16")
        window.findChild(QObject, "recommendationRun").clicked.emit()
        spin(
            app,
            lambda: (
                controller.active is not None
                and controller.active["status"] == "running"
            ),
            timeout=90000,
        )
        window.findChild(QObject, "recommendationCancel").clicked.emit()
        spin(app, lambda: not controller.busy, timeout=90000)
        assert [
            r["model_choice"]["status"]
            for r in projects.draft["results"]
            if "model_choice" in r
        ][-1] == "canceled", (
            controller.errorText,
            controller.stage,
            controller.active.get("status"),
        )
        assert controller.active["status"] == "canceled"
        if CAPTURE:
            CAPTURE(app, window, projects, controller, "canceled")
    finally:
        teardown(app, window)
