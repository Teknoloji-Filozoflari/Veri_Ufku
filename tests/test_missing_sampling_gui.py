"""Real Phase33 QML/spawn, approval boundary, export/reopen, F1 and cancellation."""

import json
import os
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown

from veri_ufku.statistics.contracts import ADVANCED_METHODS


def run_case(tmp_path, monkeypatch, method, render=None):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "phase33.parquet"
    z = np.linspace(0, 5, 40)
    values = [
        float(2 * t + np.sin(t))
        if not (method.startswith("mi_") or method.startswith("missing_")) or i % 5
        else None
        for i, t in enumerate(z)
    ]
    pl.DataFrame(
        dict(
            x=values,
            z=z,
            weight=[1.0, 2.0, 1.0, 3.0] * 10,
            g=["A"] * 20 + ["B"] * 20,
            psu=["1"] * 10 + ["2"] * 10 + ["1"] * 10 + ["2"] * 10,
        )
    ).write_parquet(source)
    original = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        engine = app._veri_ufku_resources[0]
        stats = engine._statistics_resources
        window.setProperty("selectedSection", 4)
        window.findChild(QObject, "missingMode").setProperty("checked", True)
        cols = {c["name"]: i for i, c in enumerate(stats.columns)}

        def field(name, prop, value):
            obj = window.findChild(QObject, "missing" + name)
            assert obj is not None, name
            assert obj.setProperty(prop, value), name
            return obj

        field("Method", "currentIndex", ADVANCED_METHODS.index(method))
        field("X", "currentIndex", cols["x"])
        for name, value in (
            ("Question", "Gerçek QML araştırma sorusu"),
            ("Hypothesis", "Varsayım ve bağımsız tasarım"),
            ("Unit", "puan"),
            ("Observation", "kişi / PSU"),
        ):
            field(name, "text", value)
        field("Measurement", "checked", True)
        field("Design", "checked", True)
        if method in (
            "mi_mean",
            "mi_ols",
            "weighted_ols",
            "weighted_fit",
            "missing_patterns",
            "missing_indicators",
        ):
            panel = window.findChild(QObject, "missingSamplingPanel")
            col = next(c["id"] for c in stats.columns if c["name"] == "z")
            assert panel.setProperty("chosenFeatures", [col])
        if method.startswith("sample_"):
            field("SampleSize", "value", 2)
            field("Group", "currentIndex", cols["g"])
        if method in ("weighted_mean", "weighted_ols", "weighted_fit", "survey_mean"):
            field("Weight", "currentIndex", cols["weight"])
            field(
                "WeightType",
                "currentIndex",
                {
                    "weighted_mean": 1,
                    "weighted_ols": 2,
                    "weighted_fit": 4,
                    "survey_mean": 3,
                }[method],
            )
        if method == "survey_mean":
            field("Strata", "currentIndex", cols["g"])
            field("Psu", "currentIndex", cols["psu"])
        field("Imputations", "value", 3)
        field("Iterations", "value", 3)
        run = window.findChild(QObject, "missingRun")
        assert not run.property("enabled")
        field("Preflight", "visible", True).clicked.emit()
        spin(app, lambda: not stats.busy)
        assert not stats.errorText, (method, stats.errorText)
        assert stats.preflightCurrent
        field("Approval", "checked", True)
        assert run.property("enabled")
        run.clicked.emit()
        spin(app, lambda: not stats.busy)
        assert not stats.errorText, (method, stats.errorText)
        assert stats.result["worker_pid"] != os.getpid()
        assert stats.current and stats.result["method"] == method
        assert stats.result["advanced"]
        if method == "survey_mean":
            summary = window.findChild(QObject, "missingResultSummary").property("text")
            assert "Tasarım etkisi=" in summary and "sunulmuyor" not in summary
            assert type(stats.result["advanced"]["design_effect"]) is float
        if render:
            render(app, window, method)
        export = tmp_path / "exported"
        field("ExportPath", "text", str(export))
        window.findChild(QObject, "missingExport").clicked.emit()
        assert not stats.errorText, stats.errorText
        assert (export / "details.parquet").is_file() and json.loads(
            (export / "recipe.json").read_text()
        )["spec"]["method"] == method
        window.findChild(QObject, "missingSave").clicked.emit()
        spin(app, lambda: not stats.busy)
        assert not stats.errorText, (method, stats.errorText)
        record = next(r for r in projects.draft["results"] if "analysis" in r)
        saved = record["analysis"]["advanced"]
        root = str(projects.store.root)
        assert projects.closeProject(True)
        assert projects.open(root)
        stats.openSaved(record["id"])
        assert not stats.errorText and stats.result["advanced"] == saved
        identity = pl.read_parquet(Path(stats.result["paths"]["details"]))
        assert {"row_id", "source_record_id"} <= set(identity.columns)
        for suffix, article in (
            ("Assumptions", "missing-assumptions"),
            ("Multiple", "missing-multiple"),
            ("Representation", "sampling-representation"),
            ("Bias", "sampling-bias"),
            ("Weights", "weights-types"),
        ):
            origin = window.findChild(QObject, "missingHelp" + suffix)
            origin.forceActiveFocus()
            QTest.keyClick(window, Qt.Key_F1)
            app.processEvents()
            assert engine._learning_resources.article["id"] == article
            QTest.keyClick(window, Qt.Key_Escape)
            app.processEvents()
            assert origin.hasActiveFocus()
        assert source.read_bytes() == original
        return dict(
            method=method,
            worker_pid=stats.result.get("worker_pid"),
            source_unchanged=True,
            export=True,
            reopen=True,
            rows=identity.height,
        )
    finally:
        teardown(app, window)


@pytest.mark.parametrize("method", ADVANCED_METHODS)
def test_all_advanced_methods_real_qml_spawn_export_save_reopen(
    tmp_path, monkeypatch, method
):
    run_case(tmp_path, monkeypatch, method)


def test_real_worker_cancel_does_not_publish(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "cancel.parquet"
    pl.DataFrame(
        dict(
            x=[None if i % 3 == 0 else float(i) for i in range(2000)],
            z=[float(i % 23) for i in range(2000)],
        )
    ).write_parquet(source)
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        stats = app._veri_ufku_resources[0]._statistics_resources
        cols = {c["name"]: c["id"] for c in stats.columns}
        s = dict(
            path="advanced",
            method="mi_mean",
            x=cols["x"],
            features=[cols["z"]],
            question="İptal testi",
            hypothesis="MAR",
            unit="puan",
            observation_unit="kişi",
            independent=True,
            measurement_confirmed=True,
            assumptions_confirmed=True,
            scope="full",
            imputations=20,
            iterations=30,
        )
        stats.create(json.dumps(s), True)
        spin(app, lambda: not stats.busy)
        assert not stats.errorText
        before = projects.store.commit_id
        stats.create(json.dumps(s), False)
        assert stats.process is not None
        stats.cancel()
        spin(app, lambda: not stats.busy)
        assert projects.store.commit_id == before and not projects.draft["results"]
        assert "iptal" in stats.message.lower().replace("\u0307", "")
    finally:
        teardown(app, window)


@pytest.mark.parametrize("strategy,index", [("knn", 3), ("iterative", 4)])
def test_preparation_qml_phase33_parameters_and_plan_reopen(
    tmp_path, monkeypatch, strategy, index
):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "folds.parquet"
    n = 80
    pl.DataFrame(
        dict(
            x=[None if i % 7 == 0 else float(i) for i in range(n)],
            z=[float(i) + np.sin(i) for i in range(n)],
            y=[float(i % 11) for i in range(n)],
        )
    ).write_parquet(source)
    imports.choose(str(source))
    spin(app, lambda: not imports.busy)
    imports.importData()
    spin(app, lambda: not imports.busy)
    assert not imports.errorText
    engine = app._veri_ufku_resources[0]
    controller = engine._preparation_resources
    before = source.read_bytes()
    try:
        window.setProperty("selectedSection", 5)
        cols = {c["name"]: i for i, c in enumerate(controller.columns)}
        window.findChild(QObject, "preparationTarget").setProperty(
            "currentIndex", cols["y"]
        )
        panel = window.findChild(QObject, "preparationPanel")
        panel.setProperty(
            "chosenFeatures",
            [c["id"] for c in controller.columns if c["name"] in ("x", "z")],
        )
        window.findChild(QObject, "preparationNumericFill").setProperty(
            "currentIndex", index
        )
        window.findChild(QObject, "preparationMissingIndicator").setProperty(
            "checked", True
        )
        window.findChild(QObject, "preparationImputationNeighbors").setProperty(
            "value", 2
        )
        window.findChild(QObject, "preparationImputationIterations").setProperty(
            "value", 11
        )
        window.findChild(QObject, "preparationImputationSeed").setProperty("value", 11)
        window.findChild(QObject, "preparationScan").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText, controller.errorText
        assert controller.result["worker_pid"] != os.getpid()
        s = controller.result["spec"]
        assert s["numeric_imputation"] == strategy and s["missing_indicator"]
        assert (
            s["imputation_seed"] == 11
            and s["imputation_neighbors"] == 2
            and s["imputation_iterations"] == 11
        )
        kinds = [s["kind"] for s in controller.result["plan"]["steps"]]
        assert "impute_joint" in kinds and "missing_indicator" in kinds
        window.findChild(QObject, "preparationSave").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText
        validation = engine._validation_resources
        ids = [c["id"] for c in controller.columns if c["name"] in ("x", "z")]
        vp = window.findChild(QObject, "validationPanel")
        vp.setProperty(
            "availability",
            {i: dict(offset_seconds=0, note="Ölçüm öncesi mevcut") for i in ids},
        )
        window.findChild(QObject, "validationMoment").setProperty(
            "text", "Ölçüm öncesi"
        )
        window.findChild(QObject, "validationRun").clicked.emit()
        spin(app, lambda: not validation.busy)
        assert not validation.errorText, validation.errorText
        assert validation.current and validation.result["worker_pid"] != os.getpid()
        assert validation.result["preparation_spec"]["numeric_imputation"] == strategy
        record = next(r for r in projects.draft["results"] if "baseline" in r)
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        window.findChild(QObject, "preparationOpen").clicked.emit()
        assert not controller.errorText and controller.result["spec"] == s
        validation.openRun(record["id"])
        assert (
            not validation.errorText
            and validation.result["preparation_spec"]["numeric_imputation"] == strategy
        )
        assert source.read_bytes() == before
    finally:
        teardown(app, window)
