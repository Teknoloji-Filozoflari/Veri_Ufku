"""Real QML/spawn explanation, offline help, atomics, masking and archived reopening."""

import json
import os

import polars as pl
import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import spin, teardown
from test_validation_gui import imported

CAPTURE = None
CASES = [
    "permutation",
    "pdp",
    "ice",
    "local-linear",
    "slices",
    "fairness",
    "what-if",
    "constrained",
]


def setup(tmp_path, monkeypatch, purpose="regression", family=False):
    import test_validation_gui as helper

    old_fixture = helper.fixture

    def frame():
        f = old_fixture()
        if purpose == "classification":
            return f.with_columns(
                pl.when(pl.col("x") >= 40)
                .then(pl.lit("risk"))
                .otherwise(pl.lit("normal"))
                .alias("y")
            )
        return f.with_columns(
            (
                2 * pl.col("x") + pl.when(pl.col("cat") == "A").then(3.0).otherwise(0.0)
            ).alias("y")
        )

    monkeypatch.setattr(helper, "fixture", frame)
    app, window, projects, prep, c, source = imported(
        tmp_path, monkeypatch, purpose=purpose
    )
    panel = window.findChild(QObject, "validationPanel")
    protocol = (
        panel.spec().toVariant() if hasattr(panel.spec(), "toVariant") else panel.spec()
    )
    for key in ("seed", "folds", "horizon_seconds"):
        protocol[key] = int(protocol[key])
    for entry in protocol["availability"].values():
        entry["offset_seconds"] = int(entry["offset_seconds"])
    if purpose == "classification":
        c.createClassification(
            json.dumps(protocol),
            json.dumps(
                dict(candidates=["baseline", "logistic"], positive_class="risk")
            ),
        )
    else:
        c.createRegression(
            json.dumps(protocol),
            json.dumps(dict(candidates=["baseline", "linear", "ridge"])),
        )
    spin(app, lambda: not c.busy, timeout=90000)
    assert not c.errorText, c.errorText
    engine = app._veri_ufku_resources[0]
    lifecycle = engine._lifecycle_resources
    record = next(
        r
        for r in projects.draft["results"]
        if r.get("baseline", {}).get("run_id") == c.result["run_id"]
    )
    lifecycle.selectModel(record["id"])
    spin(app, lambda: not lifecycle.busy, timeout=90000)
    assert not lifecycle.errorText, lifecycle.errorText
    return app, window, projects, prep, c, source, lifecycle


@pytest.mark.parametrize("method", CASES)
def test_actual_inspection_gui_save_export_mask_reopen(tmp_path, monkeypatch, method):
    app, window, projects, prep, c, source, lifecycle = setup(
        tmp_path,
        monkeypatch,
        "classification" if method == "fairness" else "regression",
    )
    engine = app._veri_ufku_resources[0]
    before = source.read_bytes()
    try:
        engine._workspace_resources.activate("model.explain." + method)
        assert window.findChild(QObject, "explanationExpanded").property("checked")
        assert (
            window.findChild(QObject, "explanationMethod").property("currentValue")
            == method
        )
        card = lifecycle.expected_card
        cols = {x["name"]: x["id"] for x in lifecycle.columns}
        rid = card["split"]["membership"]["validation"][0]
        window.findChild(QObject, "explanationRowId").setProperty("text", rid)
        window.findChild(QObject, "explanationBackground").setProperty(
            "currentIndex", 0
        )
        assert (
            window.findChild(QObject, "explanationBackground").property("currentValue")
            == card["dataset_version"]
        )
        if method == "what-if":
            window.findChild(QObject, "explanationChanges").setProperty(
                "text", json.dumps({cols["x"]: 200.0})
            )
        if method == "constrained":
            window.findChild(QObject, "explanationImmutable").setProperty(
                "text", json.dumps([cols["cat"]])
            )
            window.findChild(QObject, "explanationConstraints").setProperty(
                "text",
                json.dumps(
                    {
                        cols["x"]: dict(
                            values=[10.0, 30.0, 50.0], direction="any", cost=1.0
                        )
                    }
                ),
            )
            window.findChild(QObject, "explanationDesiredMin").setProperty(
                "text", "-100"
            )
            window.findChild(QObject, "explanationDesiredMax").setProperty(
                "text", "500"
            )
        if method == "slices":
            window.findChild(QObject, "explanationSlices").setProperty(
                "text",
                json.dumps(
                    [
                        dict(column_id=cols["group"], kind="group"),
                        dict(
                            column_id=cols["when"],
                            kind="time",
                            edges=[1704067200.0, 1707523200.0, 1714435200.0],
                        ),
                    ]
                ),
            )
        if method == "fairness":
            window.findChild(QObject, "explanationSensitive").setProperty(
                "text", json.dumps([cols["cat"]])
            )
            window.findChild(QObject, "explanationPositive").setProperty(
                "currentIndex", 1
            )
        window.findChild(QObject, "explanationHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert engine._learning_resources.article["id"] == "model-explanation"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        run = window.findChild(QObject, "explanationRun")
        assert run.property("enabled")
        run.clicked.emit()
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert not lifecycle.errorText, lifecycle.errorText
        assert (
            lifecycle.explanation and lifecycle.explanation["spec"]["method"] == method
        )
        assert lifecycle.result["worker_pid"] != os.getpid()
        assert lifecycle.explanation["provenance"]["fit_calls"] == 0
        record = next(
            r
            for r in projects.draft["results"]
            if r.get("explanation", {}).get("run_id") == lifecycle.explanation["run_id"]
        )
        previous = lifecycle.explanation
        output = tmp_path / (method + "-masked.json")
        window.findChild(QObject, "explanationExportPath").setProperty(
            "text", str(output)
        )
        window.findChild(QObject, "explanationExport").clicked.emit()
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert not lifecycle.errorText, lifecycle.errorText
        export = json.loads(output.read_text())
        assert (
            export["schema"] == "ExplanationExport/v1" and rid not in output.read_text()
        )
        if method == "fairness":
            assert "groups" not in export["fairness"]
        lifecycle.explanation = None
        lifecycle.openExplanation(record["id"])
        assert lifecycle.explanation == previous
        project = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(project)
        lifecycle.openExplanation(record["id"])
        assert lifecycle.explanation == previous and not lifecycle.errorText
        assert source.read_bytes() == before
        if CAPTURE:
            CAPTURE(app, window, projects, lifecycle, method, output)
    finally:
        teardown(app, window)


def test_optional_disabled_and_cancel_preserves_saved_explanation(
    tmp_path, monkeypatch
):
    app, window, projects, prep, c, source, lifecycle = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    try:
        methods = lifecycle.explanationMethods()
        assert not next(m for m in methods if m["id"] == "shap")["enabled"]
        engine._workspace_resources.activate("model.explain.permutation")
        window.findChild(QObject, "explanationRun").clicked.emit()
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert not lifecycle.errorText
        previous = lifecycle.explanation
        window.findChild(QObject, "explanationRun").clicked.emit()
        window.findChild(QObject, "explanationCancel").clicked.emit()
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert lifecycle.explanation == previous
        assert sum("explanation" in r for r in projects.draft["results"]) == 1
        export = tmp_path / "same.json"
        lifecycle.exportExplanation(str(export))
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert export.is_file() and not lifecycle.errorText
        before = export.read_bytes()
        lifecycle.exportExplanation(str(export))
        spin(app, lambda: not lifecycle.busy, timeout=90000)
        assert lifecycle.errorText and export.read_bytes() == before
    finally:
        teardown(app, window)
