"""Real QML action, spawned estimators, plots and separate durable final result."""

import os

from PySide6.QtCore import QObject
from test_import_gui import spin, teardown
from test_validation_gui import imported


def test_qml_regression_comparison_plots_final_and_retuning(tmp_path, monkeypatch):
    app, window, projects, p, c, source = imported(tmp_path, monkeypatch)
    before = source.read_bytes()
    try:
        unit = window.findChild(QObject, "regressionUnit")
        run = window.findChild(QObject, "regressionRun")
        assert not run.property("enabled")
        unit.setProperty("text", "TL")
        assert run.property("enabled")
        run.clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert len(c.result["comparison"]) == 4
        assert c.result["worker_pid"] != os.getpid()
        assert c.result["mode"] == "development" and not c.testHistory

        def visual_find(item, name):
            if item.objectName() == name:
                return item
            for child in item.childItems():
                found = visual_find(child, name)
                if found is not None:
                    return found
            return None

        spin(
            app,
            lambda: (
                visual_find(window.contentItem(), "regressionActualPlot") is not None
            ),
        )
        assert visual_find(window.contentItem(), "regressionActualPlot")
        assert visual_find(window.contentItem(), "regressionResidualPlot")
        scope = window.findChild(QObject, "regressionScope")
        assert "GELİŞTİRME" in scope.property("text")
        record = next(r for r in projects.draft["results"] if "baseline" in r)
        consent = window.findChild(QObject, "validationTestConsent")
        consent.setProperty("checked", True)
        window.findChild(QObject, "validationTest").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert c.result["mode"] == "final" and not c.result["comparison"]
        assert "FINAL TEST" in scope.property("text")
        assert c.testHistory[-1]["status"] == "completed"
        assert c.testHistory[-1]["selected_model"] == c.result["selected_model"]
        window.findChild(QObject, "regressionAlpha").setProperty("currentIndex", 2)
        run.clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert c.result["interpretation"] == "exploratory"
        assert c.testHistory[-1]["subsequent_choices"] == [c.result["run_id"]]
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        c.openRun(record["id"])
        spin(app, lambda: not c.busy)
        assert c.result["regression"]["unit"] == "TL"
        assert c.result["mode"] == "development" and len(c.testHistory) == 1
        engine = app._veri_ufku_resources[0]
        engine._learning_resources.openContext("model.regression")
        assert engine._learning_resources.article["id"] == "model-regression"
        assert source.read_bytes() == before
    finally:
        teardown(app, window)


def test_regression_cancellation_and_unsupported_protocol(tmp_path, monkeypatch):
    app, window, projects, p, c, source = imported(tmp_path, monkeypatch, "group_time")
    try:
        window.findChild(QObject, "regressionUnit").setProperty("text", "kg")
        run = window.findChild(QObject, "regressionRun")
        window.findChild(QObject, "validationEntity").setProperty("currentIndex", 1)
        assert not run.property("enabled")
        window.findChild(QObject, "validationEntity").setProperty("currentIndex", 0)
        assert run.property("enabled")
        run.clicked.emit()
        c.cancel()
        spin(app, lambda: not c.busy)
        assert not c.result and not c.current
        choices = [
            r["model_choice"] for r in projects.draft["results"] if "model_choice" in r
        ]
        assert choices[-1]["status"] == "canceled" and choices[-1]["regression"]
        assert not any("baseline" in r for r in projects.draft["results"])
    finally:
        teardown(app, window)
