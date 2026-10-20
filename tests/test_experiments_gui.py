"""Real QML selection, spawn, offline help, fixed horizon and persisted plans."""

import json
import os

import polars as pl
import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_experiments import frame
from test_import_gui import setup, spin, teardown
from test_unsupervised_gui import visual_find

CASES = (
    ("power_mean", "ITT"),
    ("power_proportion", "ITT"),
    ("random_assignment", "ITT"),
    ("experiment_mean", "ITT"),
    ("experiment_proportion", "ITT"),
    ("experiment_mean", "PP"),
    ("experiment_proportion", "PP"),
    ("experiment_proportion", "missing"),
    ("experiment_mean", "SRM"),
)


@pytest.mark.parametrize("method,population", CASES)
def test_experiment_desktop_plan_calculate_export_reopen_help(
    tmp_path, monkeypatch, method, population, capture=None
):
    from veri_ufku.statistics.experiment_contracts import EXPERIMENT_METHODS

    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "experiment-source.parquet"
    f = frame("proportion" in method)
    if population == "missing":
        f = f.with_columns(pl.Series("outcome", [None] + f["outcome"].to_list()[1:]))
    if population == "SRM":
        f = f.with_columns(pl.Series("arm", ["A"] * 5 + ["B"] * 35))
    f.write_parquet(source)
    original = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText
        engine = app._veri_ufku_resources[0]
        c = engine._statistics_resources
        window.setProperty("selectedSection", 4)

        def get(name):
            item = window.findChild(QObject, "experiment" + name) or visual_find(
                window.contentItem(), "experiment" + name
            )
            assert item is not None, name
            return item

        def field(name, prop, value):
            item = get(name)
            assert item.setProperty(prop, value)
            app.processEvents()
            return item

        field("Expanded", "checked", True)
        field("Method", "currentIndex", EXPERIMENT_METHODS.index(method))
        columns = {v["name"]: i + 1 for i, v in enumerate(c.columns)}
        if not method.startswith("power_"):
            field("Person", "currentIndex", columns["person"])
        if method.startswith("experiment_"):
            field("Outcome", "currentIndex", columns["outcome"])
            field("Arm", "currentIndex", columns["arm"])
            field("Evidence", "text", "R1 independent Bernoulli trial")
            field("Randomized", "checked", True)
            field("Horizon", "checked", True)
            if population == "PP":
                field("Population", "currentIndex", 1)
                field("Protocol", "currentIndex", columns["protocol"])
            panel = window.findChild(QObject, "experimentPanel")
            panel.setProperty("baselineIds", [c.columns[columns["baseline"] - 1]["id"]])
            field("GuardColumn", "currentIndex", columns["guard"])
            field("GuardMetric", "currentIndex", 1)
            get("GuardAdd").clicked.emit()
        field("Measurement", "checked", True)
        field("Independent", "checked", True)
        assert not get("Run").property("enabled")
        get("Preflight").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, (method, c.errorText)
        assert c.preflightCurrent
        field("Assumptions", "checked", True)
        assert get("Run").property("enabled")
        get("Run").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, (method, population, c.errorText)
        assert c.current and c.result["worker_pid"] != os.getpid()
        text = get("Result").property("text")
        assert "Sequential monitoring KAPALI" in text and "nedensellik" in text
        if population in ("missing", "SRM"):
            assert c.result["primary"]["p_value"] is None and "unavailable" in text
        if population == "PP":
            assert "nedensel ITT" in text
        get("Help").clicked.emit()
        assert window.property("infoOpen")
        assert engine._learning_resources.article[
            "id"
        ] == "experiment-" + method.replace("_", "-")
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        export = tmp_path / "explicit-export"
        field("ExportPath", "text", str(export))
        get("Export").clicked.emit()
        assert not c.errorText
        result = json.loads((export / "result.json").read_text())
        recipe = json.loads((export / "recipe.json").read_text())
        assert result["spec"] == recipe["spec"]
        assert result["plan"]["monitoring"] == "fixed_horizon"
        assert (export / "details.parquet").exists()
        if capture:
            capture(app, window, c, method, population, export)
        get("Save").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText
        root = str(projects.store.root)
        assert projects.closeProject(True)
        assert projects.open(root)
        c.result = None
        c.changed.emit()
        field("Evidence", "text", "")
        get("Open").clicked.emit()
        app.processEvents()
        assert not c.errorText
        assert c.current
        assert c.result["plan"] == result["plan"]
        if method.startswith("experiment_"):
            assert (
                get("Evidence").property("text")
                == result["plan"]["randomization_evidence"]
            )
        assert c.result["spec"] == result["spec"]
        engine._workspace_resources.activate("statistics.bootstrap-percentile")
        app.processEvents()
        assert not get("Expanded").property("checked")
        engine._workspace_resources.activate("statistics." + method.replace("_", "-"))
        app.processEvents()
        assert get("Expanded").property("checked")
        c.invalidate()
        assert not c.current and "ESKİ" in get("Result").property("text")
        c.exportAdvanced(str(tmp_path / "stale-export"))
        assert c.errorText and not (tmp_path / "stale-export").exists()
        assert source.read_bytes() == original
    finally:
        teardown(app, window)


def test_observational_not_randomized_and_peeking_gui(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "source.parquet"
    frame().write_parquet(source)
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        engine = app._veri_ufku_resources[0]
        c = engine._statistics_resources
        window.setProperty("selectedSection", 4)

        def get(name):
            return window.findChild(QObject, "experiment" + name) or visual_find(
                window.contentItem(), "experiment" + name
            )

        get("Expanded").setProperty("checked", True)
        get("Method").setProperty("currentIndex", 3)
        cols = {v["name"]: i + 1 for i, v in enumerate(c.columns)}
        for name, column in [
            ("Person", "person"),
            ("Outcome", "outcome"),
            ("Arm", "arm"),
        ]:
            get(name).setProperty("currentIndex", cols[column])
        get("Measurement").setProperty("checked", True)
        get("Independent").setProperty("checked", True)
        get("Preflight").clicked.emit()
        assert not c.busy and "randomize" in c.errorText
        assert c.result is None
        get("Evidence").setProperty("text", "R1")
        get("Randomized").setProperty("checked", True)
        get("Preflight").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText
        get("Assumptions").setProperty("checked", True)
        get("Run").clicked.emit()
        assert not c.busy and "ufuk" in c.errorText
        assert c.result is None and not projects.draft["results"]
    finally:
        teardown(app, window)
