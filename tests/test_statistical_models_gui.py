"""Every substage through real QML controls, spawn, offline help and durable reopen."""

import json
import os
from pathlib import Path

import polars as pl
import pytest
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_statistical_models import linear, mixed_frame, repeated_frame
from test_unsupervised_gui import visual_find

from veri_ufku.statistics.model_contracts import MODEL_METHODS


def fixture(method):
    if method == "mixed":
        return mixed_frame()
    if method == "repeated":
        return repeated_frame()
    if method == "glm_binomial":
        return pl.DataFrame(dict(y=[0, 1, 1, 0, 1, 1, 1, 0]))
    if method.startswith("glm_"):
        return pl.DataFrame(dict(y=[0, 1, 2, 3, 1, 4, 5, 2]))
    return linear()


@pytest.mark.parametrize("method", MODEL_METHODS)
def test_substage_real_gui_fit_diagnostic_prediction_save_reopen_help(
    tmp_path, monkeypatch, method, capture=None
):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "models-source.parquet"
    fixture(method).write_parquet(source)
    before = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText
        engine = app._veri_ufku_resources[0]
        controller = engine._statistics_resources
        window.setProperty("selectedSection", 4)

        def obj(name):
            result = window.findChild(QObject, "models" + name) or visual_find(
                window.contentItem(), "models" + name
            )
            assert result is not None, name
            return result

        def field(name, property, value, toggle=False):
            c = obj(name)
            assert c.setProperty(property, value)
            if toggle:
                c.toggled.emit()
            app.processEvents()
            return c

        field("Expanded", "checked", True)
        field("Method", "currentIndex", MODEL_METHODS.index(method))
        app.processEvents()
        cols = {c["name"]: i for i, c in enumerate(controller.columns)}
        field("Response", "currentIndex", cols["y"])
        if method in ("ols", "wls", "quantile"):
            field("Feature_x", "checked", True, True)
        if method == "wls":
            field("Weight", "currentIndex", cols["weight"] + 1)
        if method == "mixed":
            field("Group", "currentIndex", cols["person"] + 1)
        if method == "repeated":
            field("Group", "currentIndex", cols["person"] + 1)
            field("Within_phase", "checked", True, True)
        field("Question", "text", "Gerçek GUI araştırma sorusu: " + method)
        field("Hypothesis", "text", "Katsayı veya omnibus sıfır")
        field("Unit", "text", "puan / adet")
        field("Observation", "text", "bağımsız kişi / grup")
        field("Measurement", "checked", True)
        field("Independent", "checked", True)
        assert not obj("Run").property("enabled")
        obj("Preflight").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText, (method, controller.errorText)
        assert controller.preflightCurrent
        field("Assumptions", "checked", True)
        assert obj("Run").property("enabled")
        obj("Run").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText, (method, controller.errorText)
        assert (
            controller.current
            and controller.result["method"] == method
            and controller.result["worker_pid"] != os.getpid()
        )
        assert "nedensellik" in obj("Summary").property("text")
        diagnostic = Path(controller.result["paths"]["diagnostic"])
        assert diagnostic.stat().st_size > 1000
        spin(app, lambda: obj("Diagnostic").property("ready"))
        assert "DejaVuSans" in diagnostic.read_text()
        assert controller.result["model_support"]["prediction"] == (
            method != "repeated"
        )
        if method != "repeated":
            for c in controller.result["spec"]["features"]:
                field("Predict_" + c, "text", "2")
            obj("Predict").clicked.emit()
            assert not controller.errorText
            assert "value" in controller.modelPrediction
        learning = engine._learning_resources
        obj("MethodHelp").clicked.emit()
        assert window.property("infoOpen")
        assert learning.article["id"] == "statistical-model-" + method.replace("_", "-")
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        QTest.keyClick(window, Qt.Key.Key_Escape)
        assert not window.property("infoOpen")
        if capture:
            capture(app, window, controller, method)
        original_result = json.loads(
            Path(controller.result["paths"]["result"]).read_text()
        )
        obj("Save").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText

        root = str(projects.store.root)
        assert projects.closeProject(True)
        assert projects.open(root)
        obj("Open").clicked.emit()
        app.processEvents()
        assert not controller.errorText
        assert (
            controller.result["prediction_schema"]
            == original_result["prediction_schema"]
        )
        assert controller.result["coefficients"] == original_result["coefficients"]
        assert controller.current
        assert controller.modelDiagnostic.startswith("file:")
        if method != "repeated":
            obj("Predict").clicked.emit()
            assert "value" in controller.modelPrediction
        controller.invalidate()
        assert not controller.current
        controller.predictModel("{}", 0, 1)
        assert controller.errorText and not controller.modelPrediction
        assert source.read_bytes() == before
    finally:
        teardown(app, window)


def test_gui_baseline_interaction_cluster_prediction_and_stale_filter(
    tmp_path, monkeypatch
):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "categorical.parquet"
    linear().write_parquet(source)
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        engine = app._veri_ufku_resources[0]
        controller = engine._statistics_resources
        window.setProperty("selectedSection", 4)

        def get(name):
            c = window.findChild(QObject, "models" + name) or visual_find(
                window.contentItem(), "models" + name
            )
            assert c is not None, name
            return c

        def toggle(name):
            c = get(name)
            c.setProperty("checked", True)
            c.toggled.emit()
            app.processEvents()

        get("Expanded").setProperty("checked", True)
        cols = {c["name"]: i for i, c in enumerate(controller.columns)}
        get("Response").setProperty("currentIndex", cols["y"])
        toggle("Feature_x")
        toggle("Feature_g")
        toggle("Category_g")
        baseline = get("Baseline_g")
        baseline.setProperty("text", "A")
        baseline.textEdited.emit()
        # Both real interaction selectors in the panel are named for inspection.
        get("InteractionA").setProperty("currentIndex", cols["x"])
        get("InteractionB").setProperty("currentIndex", cols["g"])
        get("AddInteraction").clicked.emit()
        get("Covariance").setProperty("currentIndex", 2)
        get("Cluster").setProperty("currentIndex", cols["cluster"] + 1)
        for name, text in [
            ("Question", "Kategori ve interaction etkisi?"),
            ("Hypothesis", "Beta0"),
            ("Unit", "puan"),
            ("Observation", "bağımsız küme"),
        ]:
            get(name).setProperty("text", text)
        toggle("Measurement")
        toggle("Independent")
        get("Preflight").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText, controller.errorText
        assert "referans: A" in get("PreflightText").property("text")
        toggle("Assumptions")
        get("Run").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText, controller.errorText
        assert (
            len(controller.result["coefficients"]) == 4
            and controller.result["spec"]["covariance"] == "cluster"
        )
        fields = {c["name"]: c["id"] for c in controller.columns}
        get("Predict_" + fields["x"]).setProperty("text", "2")
        get("Predict_" + fields["g"]).setProperty("text", "B")
        get("Predict").clicked.emit()
        assert "value" in controller.modelPrediction
        get("Save").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText
        from dataclasses import replace

        data = engine._dataset_resources
        data.view = replace(
            data.view, filters=[dict(column_id=fields["x"], operator="gt", value="5")]
        )
        data.changed.emit()
        assert not controller.current
        assert "ESKİ" in get("Status").property("text")
        controller.predictModel(json.dumps({fields["x"]: 2, fields["g"]: "B"}), 0, 1)
        assert controller.errorText and not controller.modelPrediction
        engine._workspace_resources.activate("statistics.welch-t")
        app.processEvents()
        assert not get("Expanded").property("checked")
        assert window.findChild(QObject, "statisticsPanel").property("visible")
        engine._workspace_resources.activate("statistics.ols")
        app.processEvents()
        assert get("Expanded").property("checked")
        assert controller.savedAnalyses[0]["path"] == "models"
    finally:
        teardown(app, window)
