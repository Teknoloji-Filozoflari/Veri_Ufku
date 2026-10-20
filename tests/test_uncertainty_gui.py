"""Actual Qt/QML spawn, package, test journal, help and preserved cancel result."""

import os

import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import spin, teardown
from test_validation_gui import imported

CAPTURE = None
CASES = [
    ("sigmoid", "classification"),
    ("isotonic", "classification"),
    ("sets", "classification"),
    ("interval", "regression"),
    ("quantile", "regression"),
    ("cqr", "regression"),
]


@pytest.mark.parametrize("method,purpose", CASES)
def test_actual_uncertainty_gui_safe_model_final_and_reopen(
    tmp_path, monkeypatch, method, purpose, base_index=0
):
    app, window, projects, prep, c, source = imported(
        tmp_path, monkeypatch, purpose=purpose
    )
    engine = app._veri_ufku_resources[0]
    before = source.read_bytes()
    try:
        engine._workspace_resources.activate("model.uncertainty." + method)
        assert window.findChild(QObject, "uncertaintyExpanded").property("checked")
        assert (
            window.findChild(QObject, "uncertaintyMethod").property("currentValue")
            == method
        )
        window.findChild(QObject, "uncertaintyBase").setProperty(
            "currentIndex", base_index
        )
        if purpose == "classification":
            window.findChild(QObject, "uncertaintyThreshold").setProperty(
                "currentIndex", 0
            )
        window.findChild(QObject, "uncertaintyHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert engine._learning_resources.article["id"] == "model-uncertainty"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        button = window.findChild(QObject, "uncertaintyRun")
        assert button.property("enabled")
        button.clicked.emit()
        spin(app, lambda: not c.busy, timeout=90000)
        assert not c.errorText, c.errorText
        assert c.result and c.result["uncertainty"]["schema"] == "UncertaintyModel/v1"
        assert c.result["worker_pid"] != os.getpid()
        assert any(
            r.get("baseline", {}).get("model_package_uri")
            for r in projects.draft["results"]
        )
        dev = c.result
        assert "empirical coverage" in window.findChild(
            QObject, "uncertaintyCoverage"
        ).property("text")
        if CAPTURE:
            CAPTURE(
                app,
                window,
                projects,
                c,
                "forest-" + method if base_index else method,
                purpose,
                "development",
            )
        c.invalidate()
        assert not c.canTest
        saved = next(
            r["id"]
            for r in projects.draft["results"]
            if r.get("baseline", {}).get("run_id") == dev["run_id"]
        )
        lifecycle = engine._lifecycle_resources
        lifecycle.selectModel(saved)
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert not lifecycle.errorText, lifecycle.errorText
        import polars as pl
        from PySide6.QtCore import QUrl

        package = tmp_path / (method + ".vumodel")
        lifecycle.savePackage(QUrl.fromLocalFile(str(package)).toString())
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert not lifecycle.errorText and package.is_file()
        lifecycle.openPackage(QUrl.fromLocalFile(str(package)).toString())
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert not lifecycle.errorText
        lifecycle.previewData("reject", 17)
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert not lifecycle.errorText and not lifecycle.previewReport["blockers"]
        destination = tmp_path / (method + "-prediction.parquet")
        lifecycle.predictData(
            QUrl.fromLocalFile(str(destination)).toString(), "reject", 17
        )
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert not lifecycle.errorText, lifecycle.errorText
        output = pl.read_parquet(destination)
        assert (
            "vu_prediction_set" in output.columns
            if purpose == "classification"
            else "vu_predictive_lower" in output.columns
        )
        assert len(output) == 80 and output["__vu_row_id"].n_unique() == 80
        assert lifecycle.outputReport["details"]["fit_calls"] == 0
        c.openRun(saved)
        spin(app, lambda: not c.busy)
        assert c.canTest and not c.errorText
        window.findChild(QObject, "validationTestConsent").setProperty("checked", True)
        test = window.findChild(QObject, "validationTest")
        assert test.property("enabled")
        test.clicked.emit()
        spin(app, lambda: not c.busy, timeout=90000)
        assert not c.errorText, c.errorText
        assert c.result["mode"] == "final" and c.result["fit_count"] == 0
        assert c.result["uncertainty"] == dev["uncertainty"]
        assert c.testHistory[-1]["status"] == "completed"
        if CAPTURE:
            CAPTURE(
                app,
                window,
                projects,
                c,
                "forest-" + method if base_index else method,
                purpose,
                "final",
            )
        assert source.read_bytes() == before
    finally:
        teardown(app, window)


def test_binary_cost_constraints_cancel_and_new_file_prediction(tmp_path, monkeypatch):
    import polars as pl
    import test_validation_gui as helper
    from PySide6.QtCore import QUrl

    old_fixture = helper.fixture
    monkeypatch.setattr(
        helper,
        "fixture",
        lambda: old_fixture().with_columns(
            pl.when(pl.col("y") >= 3)
            .then(pl.lit("risk"))
            .otherwise(pl.lit("normal"))
            .alias("y")
        ),
    )
    app, window, projects, prep, c, source = imported(
        tmp_path, monkeypatch, purpose="classification"
    )
    engine = app._veri_ufku_resources[0]
    lifecycle = engine._lifecycle_resources
    before = source.read_bytes()
    try:
        engine._workspace_resources.activate("model.uncertainty.sigmoid")
        window.findChild(QObject, "uncertaintyPositive").setProperty("currentIndex", 1)
        window.findChild(QObject, "uncertaintyFNCost").setProperty("text", "4")
        window.findChild(QObject, "uncertaintyMinRecall").setProperty("text", "0.8")
        window.findChild(QObject, "uncertaintyRun").clicked.emit()
        spin(app, lambda: not c.busy, timeout=90000)
        assert not c.errorText, c.errorText
        dev = c.result
        assert dev["decision"]["mode"] == "cost"
        assert dev["decision"]["threshold_report"]["winner"]["recall"] >= 0.8
        assert dev["classification"]["uncertainty"]["false_negative_cost"] == 4
        # Cancel a new explicit action before/during worker without removing previous result.
        window.findChild(QObject, "uncertaintyRun").clicked.emit()
        assert c.busy
        window.findChild(QObject, "validationCancel").clicked.emit()
        spin(app, lambda: not c.busy, timeout=90000)
        assert c.result["run_id"] == dev["run_id"]
        assert projects.draft["results"][-1]["model_choice"]["status"] == "canceled"
        # Return to published model; final evaluation reports cost but never retunes.
        record = next(
            r
            for r in projects.draft["results"]
            if r.get("baseline", {}).get("run_id") == dev["run_id"]
        )
        c.openRun(record["id"])
        spin(app, lambda: not c.busy)
        window.findChild(QObject, "validationTestConsent").setProperty("checked", True)
        window.findChild(QObject, "validationTest").clicked.emit()
        spin(app, lambda: not c.busy, timeout=90000)
        assert not c.errorText, c.errorText
        assert c.result["decision"] == dev["decision"]
        assert (
            c.result["evaluations"][0]["uncertainty_report"]["decision"][
                "false_negative_cost"
            ]
            == 4
        )
        lifecycle.selectModel(record["id"])
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert not lifecycle.errorText, lifecycle.errorText
        package = tmp_path / "calibrated.vumodel"
        lifecycle.savePackage(QUrl.fromLocalFile(str(package)).toString())
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert package.is_file() and not lifecycle.errorText
        lifecycle.openPackage(QUrl.fromLocalFile(str(package)).toString())
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert not lifecycle.errorText
        new = pl.concat([pl.read_parquet(source).head(3)] * 2).select(
            "cat", "x", "group", "when", "y"
        )
        new_file = tmp_path / "new.parquet"
        new.write_parquet(new_file)
        imports = engine._imports_resources
        imports.choose(str(new_file))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText
        data = engine._dataset_resources
        data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
        spin(app, lambda: not data.busy)
        lifecycle.previewData("reject", 2)
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert not lifecycle.errorText and not lifecycle.previewReport["blockers"]
        output = tmp_path / "prediction.parquet"
        lifecycle.predictData(QUrl.fromLocalFile(str(output)).toString(), "reject", 2)
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert not lifecycle.errorText, lifecycle.errorText
        result = pl.read_parquet(output)
        assert "vu_prediction_set" in result.columns
        assert len(result) == 6 and result["__vu_row_id"].n_unique() == 6
        assert lifecycle.outputReport["details"]["fit_calls"] == 0
        assert source.read_bytes() == before and pl.read_parquet(new_file).equals(new)
        if CAPTURE:
            CAPTURE(app, window, projects, c, "binary-cost", "classification", "final")
    finally:
        teardown(app, window)


def test_group_time_calibration_gui_and_coverage_scope(tmp_path, monkeypatch):
    app, window, projects, prep, c, source = imported(
        tmp_path, monkeypatch, "group_time", "regression"
    )
    engine = app._veri_ufku_resources[0]
    before = source.read_bytes()
    try:
        engine._workspace_resources.activate("model.uncertainty.interval")
        window.findChild(QObject, "uncertaintyAlpha").setProperty("text", "0.5")
        window.findChild(QObject, "uncertaintyRun").clicked.emit()
        spin(app, lambda: not c.busy, timeout=90000)
        assert not c.errorText, c.errorText
        assert c.result["plan"]["method"] == "group_time"
        assert c.result["uncertainty"]["inner_plan"]["method"] == "group_time"
        assert (
            "exchangeability"
            in c.result["evaluations"][0]["uncertainty_report"]["limitations"]
        )
        assert source.read_bytes() == before
        if CAPTURE:
            CAPTURE(app, window, projects, c, "group-time", "regression", "development")
    finally:
        teardown(app, window)


@pytest.mark.parametrize(
    "method,purpose", [("isotonic", "classification"), ("interval", "regression")]
)
def test_forest_probability_and_interval_gui(tmp_path, monkeypatch, method, purpose):
    test_actual_uncertainty_gui_safe_model_final_and_reopen(
        tmp_path, monkeypatch, method, purpose, base_index=1
    )
