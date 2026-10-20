"""Real imported binary/multiclass QML and spawned estimators, with durable choices."""

import json
import os

import numpy as np
import polars as pl
import pytest
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown


def imported(tmp_path, monkeypatch, multiclass=False):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    x = np.linspace(-3, 3, 300)
    y = (
        np.where(x > 1.5, "risk", "normal")
        if not multiclass
        else np.where(x > 1.5, "C", np.where(x > 0, "B", "A"))
    )
    source = tmp_path / "classification.parquet"
    pl.DataFrame(dict(x=x, y=y)).write_parquet(source)
    imports.choose(str(source))
    spin(app, lambda: not imports.busy)
    imports.importData()
    spin(app, lambda: not imports.busy)
    assert not imports.errorText
    engine = app._veri_ufku_resources[0]
    p, c = engine._preparation_resources, engine._validation_resources
    cols = {col["name"]: col["id"] for col in p.columns}
    p.create(
        json.dumps(
            dict(
                purpose="classification",
                features=[cols["x"]],
                target=cols["y"],
                scaling="standard",
                prediction_context="Ölçüm öncesi",
            )
        )
    )
    spin(app, lambda: not p.busy)
    assert not p.errorText and not p.result["blockers"]
    window.setProperty("selectedSection", 5)
    panel = window.findChild(QObject, "validationPanel")
    panel.setProperty(
        "availability", {cols["x"]: dict(offset_seconds=0, note="Önceden mevcut")}
    )
    return app, window, projects, p, c, source


@pytest.mark.parametrize("multiclass", [False, True])
def test_actual_qml_category_models_threshold_final_history_help(
    tmp_path, monkeypatch, multiclass
):
    app, window, projects, p, c, source = imported(tmp_path, monkeypatch, multiclass)
    before = source.read_bytes()
    try:
        run = window.findChild(QObject, "classificationRun")
        positive = window.findChild(QObject, "classificationPositive")
        if not multiclass:
            assert not run.property("enabled")
            positive.setProperty(
                "currentIndex",
                next(
                    i
                    for i, v in enumerate(p.report["target"]["class_distribution"])
                    if v["label"] == "risk"
                ),
            )
            window.findChild(QObject, "classificationThresholdMode").setProperty(
                "currentIndex", 2
            )
        assert run.property("enabled")
        window.findChild(QObject, "classificationCost").setProperty(
            "text", "Kaçırmak daha maliyetli"
        )
        run.clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        out = c.result
        assert out["worker_pid"] != os.getpid() and len(out["comparison"]) == 3
        assert out["decision"]["cost_note"] == "Kaçırmak daha maliyetli"
        assert out["decision_validation"]["confusion_matrix"]
        assert all(v["status"] == "valid" for v in out["decision_validation"]["curves"])
        assert len(c.choiceHistory) == 1 and not c.testHistory
        record = next(r for r in projects.draft["results"] if "baseline" in r)
        for number in range(2):
            c.openRun(record["id"])
            spin(app, lambda: not c.busy)
            window.findChild(QObject, "validationTestConsent").setProperty(
                "checked", True
            )
            window.findChild(QObject, "validationTest").clicked.emit()
            spin(app, lambda: not c.busy)
            assert not c.errorText, c.errorText
            assert c.result["decision"] == out["decision"]
            assert len(c.testHistory) == number + 1
        assert c.result["interpretation"] == "exploratory"
        window.findChild(QObject, "classificationC").setProperty("currentIndex", 2)
        if not multiclass:
            positive.setProperty("currentIndex", 1 - positive.property("currentIndex"))
            window.findChild(QObject, "classificationThresholdMode").setProperty(
                "currentIndex", 1
            )
            window.findChild(QObject, "classificationThreshold").setProperty(
                "text", "0.35"
            )
        run.clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert (
            len(c.choiceHistory) == 2
            and len(c.choiceHistory[-1]["prior_test_use_ids"]) == 2
        )
        assert c.choiceHistory[-1]["classification"]["C"] == 10
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        assert len(c.choiceHistory) == 2 and len(c.testHistory) == 2
        c.openRun(record["id"])
        spin(app, lambda: not c.busy)
        assert c.result["decision"] == out["decision"]
        learning = app._veri_ufku_resources[0]._learning_resources
        for context in (
            "model.classification",
            "classification.positive",
            "classification.metrics",
            "classification.threshold",
            "classification.probability",
        ):
            learning.openContext(context)
            assert learning.article["id"] == context.replace(".", "-")
        assert source.read_bytes() == before
    finally:
        teardown(app, window)


def test_category_invalid_and_canceled_choices_not_success(tmp_path, monkeypatch):
    app, window, projects, p, c, source = imported(tmp_path, monkeypatch)
    try:
        panel = window.findChild(QObject, "validationPanel")
        c.createClassification(
            json.dumps(
                dict(
                    prediction_moment="Ölçüm öncesi",
                    availability=panel.property("availability"),
                )
            ),
            json.dumps(dict(positive_class="missing")),
        )
        spin(app, lambda: not c.busy)
        assert c.errorText and not c.result
        positive = window.findChild(QObject, "classificationPositive")
        positive.setProperty("currentIndex", 0)
        button = window.findChild(QObject, "classificationRun")
        button.clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        old = c.result
        button.clicked.emit()
        c.cancel()
        spin(app, lambda: not c.busy)
        assert c.result is old and not c.current
        assert sum("baseline" in r for r in projects.draft["results"]) == 1
        assert c.choiceHistory[-1]["status"] == "canceled"
        c.openRun(next(r["id"] for r in projects.draft["results"] if "baseline" in r))
        spin(app, lambda: not c.busy)
        assert c.canTest, c.errorText
        c.evaluateTest()
        c.cancel()
        spin(app, lambda: not c.busy)
        assert c.testHistory[-1]["status"] == "canceled"
    finally:
        teardown(app, window)
