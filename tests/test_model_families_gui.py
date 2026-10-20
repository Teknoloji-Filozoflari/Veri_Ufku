"""Actual per-family QML train/evaluate/save/new-dataset prediction and offline help."""

import json
import os

import numpy as np
import polars as pl
import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown
from test_model_families import CASES
from test_unsupervised_gui import visual_find

CAPTURE = None


@pytest.mark.parametrize("method,purpose", CASES)
def test_family_gui_train_evaluate_predict(tmp_path, monkeypatch, method, purpose):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    preparation = engine._preparation_resources
    validation = engine._validation_resources
    lifecycle = engine._lifecycle_resources
    rng = np.random.default_rng(48)
    x = rng.uniform(0.1, 2.0, 90)
    y = (
        3 * x + rng.normal(0, 0.05, 90)
        if purpose == "regression"
        else np.where(x > 1.0, "risk", "normal")
    )
    raw = pl.DataFrame(
        dict(
            x=x,
            y=y,
            category=["A" if i % 2 else "B" for i in range(90)],
            note=["preserve"] * 90,
        )
    )
    source = tmp_path / "source.parquet"
    raw.write_parquet(source)
    before = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        cols = {c["name"]: c["id"] for c in preparation.columns}
        preparation.create(
            json.dumps(
                dict(
                    purpose=purpose,
                    features=[cols["x"], cols["category"]],
                    target=cols["y"],
                    prediction_context="Before outcome",
                )
            )
        )
        spin(app, lambda: not preparation.busy)
        assert not preparation.errorText, preparation.errorText
        window.setProperty("selectedSection", 5)
        panel = window.findChild(QObject, "modelFamiliesPanel")
        assert panel is not None
        choice = window.findChild(QObject, "familyMethod")
        choice.setProperty("currentIndex", 1 if method == "elasticnet" else 0)
        engine._workspace_resources.activate(
            "model.family." + purpose + "." + method.replace("_", "-")
        )
        spin(app, lambda: choice.property("currentValue") == method)
        assert window.findChild(QObject, "familyExpanded").property("checked")
        # Explicit UI parameters must be the values passed to every candidate fit.
        window.findChild(QObject, "familyTrees").setProperty("text", "10")
        window.findChild(QObject, "familyDepth").setProperty("text", "3")
        window.findChild(QObject, "validationFolds").setProperty("text", "2")
        if purpose == "classification":
            positive = window.findChild(QObject, "familyPositive")
            distribution = preparation.report["target"]["class_distribution"]
            positive.setProperty(
                "currentIndex",
                next(i for i, c in enumerate(distribution) if c["label"] == "risk"),
            )
        for name in ("x", "category"):
            note = visual_find(window.contentItem(), "validationNote_" + name)
            note.setProperty("text", "Before outcome")
            note.textEdited.emit()
            offset = visual_find(window.contentItem(), "validationOffset_" + name)
            offset.setProperty("text", "0")
            offset.textEdited.emit()
        window.findChild(QObject, "familyHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert engine._learning_resources.article["id"] == "model-families"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        button = window.findChild(QObject, "familyRun")
        assert button.property("enabled")
        button.clicked.emit()
        spin(app, lambda: not validation.busy)
        assert not validation.errorText, validation.errorText
        assert validation.current and validation.result["worker_pid"] != os.getpid()
        out = validation.result
        assert out["selected_model"] == method
        assert (out.get("regression") or out["classification"])["family_options"][
            "trees"
        ] == 10
        assert out["selection_rule"].startswith("explicit")
        if purpose == "classification" and method == "svm":
            spin(
                app,
                lambda: (
                    visual_find(window.contentItem(), "validationMetric_roc_auc")
                    is not None
                ),
            )
            for prefix in ("validationMetric_", "classificationMetric_"):
                for metric in ("roc_auc", "pr_auc"):
                    label = visual_find(window.contentItem(), prefix + metric)
                    assert label is not None and "tanımsız" in label.property("text")
        record = next(
            r
            for r in projects.draft["results"]
            if r.get("baseline", {}).get("run_id") == out["run_id"]
        )
        window.findChild(QObject, "lifecycleOpenSaved").clicked.emit()
        spin(app, lambda: not lifecycle.busy)
        assert not lifecycle.errorText, lifecycle.errorText
        assert lifecycle.card["estimator"] == (
            "FamilyRegressor" if purpose == "regression" else "FamilyClassifier"
        )
        original_card = record["baseline"]["model_card"]
        if CAPTURE:
            CAPTURE(app, window, validation, lifecycle, method, purpose, None, record)
        new = raw.head(12).select("note", "category", "x", "y")
        new_source = tmp_path / "new.parquet"
        new.write_parquet(new_source)
        new_before = new_source.read_bytes()
        imports.choose(str(new_source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        data = engine._dataset_resources
        data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
        spin(app, lambda: not data.busy)
        window.findChild(QObject, "lifecyclePreview").clicked.emit()
        spin(app, lambda: not lifecycle.busy)
        assert not lifecycle.errorText, lifecycle.errorText
        assert (
            not lifecycle.previewReport["blockers"]
            and lifecycle.previewReport["invalid_rows"] == 0
        )
        output = tmp_path / "prediction.parquet"
        window.findChild(QObject, "lifecycleOutputPath").setProperty(
            "text", str(output)
        )
        window.findChild(QObject, "lifecyclePredict").clicked.emit()
        spin(app, lambda: not lifecycle.busy)
        assert not lifecycle.errorText, lifecycle.errorText
        assert output.is_file() and lifecycle.outputReport["details"]["fit_calls"] == 0
        result = pl.read_parquet(output)
        dataset = data.dataset()
        snapshot = pl.read_parquet(projects.store.path(dataset["snapshot_uri"]))
        assert result.select(snapshot.columns).equals(snapshot)
        assert result["__vu_row_id"].n_unique() == 12
        assert source.read_bytes() == before and new_source.read_bytes() == new_before
        assert record["baseline"]["model_card"] == original_card
        if CAPTURE:
            CAPTURE(app, window, validation, lifecycle, method, purpose, output, record)
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        lifecycle.selectModel(record["id"])
        spin(app, lambda: not lifecycle.busy)
        assert not lifecycle.errorText, lifecycle.errorText
        assert lifecycle.card["candidate_selection"]["selected"] == method
    finally:
        teardown(app, window)


def test_family_unavailable_cancel_and_timeout_keep_prior_model(tmp_path, monkeypatch):
    import time

    from test_validation_gui import imported

    app, window, projects, preparation, validation, source = imported(
        tmp_path, monkeypatch
    )
    before = source.read_bytes()
    try:
        engine = app._veri_ufku_resources[0]
        choice = window.findChild(QObject, "familyMethod")
        methods = validation.familyMethods("regression")
        window.findChild(QObject, "familyExpanded").setProperty("checked", True)
        run = window.findChild(QObject, "familyRun")
        for method in ("xgboost", "lightgbm", "catboost"):
            choice.setProperty(
                "currentIndex",
                next(i for i, m in enumerate(methods) if m["id"] == method),
            )
            assert not run.property("enabled")
            assert not validation.busy
        engine._workspace_resources.activate("model.family.regression.decision-tree")
        assert run.property("enabled")
        run.clicked.emit()
        spin(app, lambda: not validation.busy)
        assert not validation.errorText, validation.errorText
        saved = [r for r in projects.draft["results"] if "baseline" in r]
        assert len(saved) == 1
        card = json.dumps(saved[0]["baseline"]["model_card"], sort_keys=True)
        run.clicked.emit()
        validation.cancel()
        spin(app, lambda: not validation.busy)
        assert len([r for r in projects.draft["results"] if "baseline" in r]) == 1
        assert projects.draft["results"][-1]["model_choice"]["status"] == "canceled"
        # Real launched worker; expire its unchanged configured wall budget.
        run.clicked.emit()
        spin(app, lambda: validation.process is not None)
        validation.started = time.monotonic() - validation.budget.max_wall_seconds - 1
        validation.poll()
        spin(app, lambda: not validation.busy)
        assert projects.draft["results"][-1]["model_choice"]["status"] == "canceled"
        assert len([r for r in projects.draft["results"] if "baseline" in r]) == 1
        assert json.dumps(saved[0]["baseline"]["model_card"], sort_keys=True) == card
        assert source.read_bytes() == before
    finally:
        teardown(app, window)
