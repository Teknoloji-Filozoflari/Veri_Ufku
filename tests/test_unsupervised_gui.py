"""Actual QML controls, spawned fit, all-row marking, reopen/help and canceled/stale runs."""

import json
import os

import polars as pl
import pytest
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown


def visual_find(item, name):
    if item.objectName() == name:
        return item
    for child in item.childItems():
        found = visual_find(child, name)
        if found is not None:
            return found
    return None


def imported(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "measurements.parquet"
    pl.DataFrame(
        dict(x=[0.0, 0.1, 0.2, 10.0, 10.1, 10.2, 50.0], note=["keep"] * 7)
    ).write_parquet(source)
    imports.choose(str(source))
    spin(app, lambda: not imports.busy)
    imports.importData()
    spin(app, lambda: not imports.busy)
    assert not imports.errorText, imports.errorText
    window.setProperty("selectedSection", 5)
    c = app._veri_ufku_resources[0]._unsupervised_resources
    return app, window, projects, c, source


@pytest.mark.parametrize("method", ["kmeans", "dbscan", "isolation_forest", "iqr"])
def test_actual_qml_fit_mark_reopen_and_context_help(tmp_path, monkeypatch, method):
    app, window, projects, c, source = imported(tmp_path, monkeypatch)
    before = source.read_bytes()
    try:
        purpose = window.findChild(QObject, "preparationPurpose")
        purpose.setProperty("currentIndex", 2 if method in ("kmeans", "dbscan") else 3)
        panel = window.findChild(QObject, "unsupervisedPanel")
        spin(
            app,
            lambda: (
                visual_find(window.contentItem(), "unsupervisedFeature_x") is not None
            ),
        )
        feature = visual_find(window.contentItem(), "unsupervisedFeature_x")
        feature.setProperty("checked", True)
        feature.clicked.emit()
        assert panel.property("visible")
        method_choice = window.findChild(QObject, "unsupervisedMethod")
        method_choice.setProperty("currentIndex", int(method in ("dbscan", "iqr")))
        window.findChild(QObject, "unsupervisedScaling").setProperty("currentIndex", 1)
        window.findChild(QObject, "unsupervisedClusters").setProperty("text", "2")
        window.findChild(QObject, "unsupervisedEps").setProperty("text", "0.3")
        window.findChild(QObject, "unsupervisedNeighbors").setProperty("text", "3")
        button = window.findChild(QObject, "unsupervisedRun")
        assert button.property("enabled")
        button.clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert c.report["spec"]["method"] == method
        assert c.result["worker_pid"] != os.getpid() and c.current
        record_id = c.record_id
        assert len(c.savedRuns) == 1
        for context in ("cluster", "distance", "noise", "score", "evaluation"):
            library = app._veri_ufku_resources[0]._learning_resources
            library.openContext("unsupervised." + context)
            assert library.article["id"] == "unsupervised-" + context
        window.findChild(QObject, "unsupervisedTransfer").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert len(projects.draft["datasets"]) == 2
        d = projects.draft["datasets"][-1]
        marked = pl.read_parquet(projects.store.path(d["snapshot_uri"]))
        assert marked.height == 7 and marked["note"].to_list() == ["keep"] * 7
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        c.openSaved(record_id)
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert c.report["spec"]["method"] == method
        assert source.read_bytes() == before
        if method == "dbscan":
            assert "doğal predict" in window.findChild(
                QObject, "unsupervisedPrediction"
            ).property("text")
    finally:
        teardown(app, window)


def test_invalid_canceled_and_stale_new_jobs_preserve_previous_result(
    tmp_path, monkeypatch
):
    app, window, projects, c, source = imported(tmp_path, monkeypatch)
    try:
        feature = next(col["id"] for col in c.columns if col["name"] == "x")
        valid = json.dumps(dict(method="kmeans", features=[feature], clusters=2))
        c.create(valid)
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        old = c.result
        c.create(json.dumps(dict(method="dbscan", features=[feature], eps=0)))
        assert c.errorText and c.result is old and not c.current
        c.create(valid)
        c.cancel()
        spin(app, lambda: not c.busy)
        assert c.result is old and not c.current
        assert len(c.savedRuns) == 1
        c.create(valid)
        c.invalidate()
        spin(app, lambda: not c.busy)
        assert c.result is old and not c.current
        assert len(c.savedRuns) == 1 and "Eski" in c.message
    finally:
        teardown(app, window)
