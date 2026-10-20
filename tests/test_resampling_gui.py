"""Real desktop choices, worker, family export, durable units and offline help."""

import json
import os
from dataclasses import replace
from pathlib import Path

import polars as pl
import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown
from test_resampling import frame
from test_unsupervised_gui import visual_find

CASES = (
    ("bootstrap_percentile", "observation"),
    ("bootstrap_bca", "observation"),
    ("bootstrap_percentile", "cluster"),
    ("bootstrap_bca", "cluster"),
    ("bootstrap_percentile", "time_block"),
    ("permutation", "observation"),
    ("permutation", "cluster"),
    ("paired_sign_flip", "observation"),
    ("paired_sign_flip", "cluster"),
    ("robust_summary", "observation"),
    ("adjust_holm", "observation"),
    ("adjust_bonferroni", "observation"),
    ("adjust_bh", "observation"),
    ("sensitivity", "observation"),
)


def fixture(method):
    if method.startswith("adjust_"):
        return pl.DataFrame(
            dict(
                x=[0.01, 0.04, 0.03, 0.2, 0.9],
                test_id=["t1", "t2", "t3", "t4", "outside"],
            )
        )
    if method == "permutation":
        return frame().with_columns(
            pl.Series("cluster", ["c0"] * 3 + ["c1"] * 3 + ["c2"] * 3 + ["c3"] * 3)
        )
    return frame()


@pytest.mark.parametrize("method,unit", CASES)
def test_resampling_qml_unit_fit_save_reopen_export_help(
    tmp_path, monkeypatch, method, unit, capture=None
):
    from veri_ufku.statistics.resampling_contracts import RESAMPLING_METHODS

    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "resampling-source.parquet"
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

        def get(name):
            c = window.findChild(QObject, "resampling" + name) or visual_find(
                window.contentItem(), "resampling" + name
            )
            assert c is not None, name
            return c

        def field(name, property, value):
            c = get(name)
            assert c.setProperty(property, value)
            app.processEvents()
            return c

        field("Expanded", "checked", True)
        field("Method", "currentIndex", RESAMPLING_METHODS.index(method))
        cols = {c["name"]: i for i, c in enumerate(controller.columns)}
        field("X", "currentIndex", cols["x"])
        field(
            "Unit", "currentIndex", ["observation", "cluster", "time_block"].index(unit)
        )
        field(
            "Dependence",
            "currentIndex",
            ["observation", "cluster", "time_block"].index(unit),
        )
        field("Replicates", "value", 1000)
        if unit == "cluster":
            field("Cluster", "currentIndex", cols["cluster"] + 1)
        if unit == "time_block":
            field("Time", "currentIndex", cols["time"] + 1)
            field("Block", "value", 3)
        if method == "permutation":
            field("Group", "currentIndex", cols["label"] + 1)
            field("Exchangeable", "checked", True)
        if method == "paired_sign_flip":
            field("Y", "currentIndex", cols["after"] + 1)
            field("Key", "currentIndex", cols["pair"] + 1)
            field("Exchangeable", "checked", True)
            field("Symmetric", "checked", True)
        if method.startswith("adjust_"):
            field("Key", "currentIndex", cols["test_id"] + 1)
            field("FamilyName", "text", "Önceden belirlenen birincil uçlar")
            field("FamilyIds", "text", "t1\nt2\nt3\nt4")
            if method == "adjust_bh":
                field("FamilyDependence", "currentIndex", 1)
        if method == "sensitivity":
            field("ScenarioName", "text", "Filtre / median / MNAR")
            field("ScenarioColumn", "currentIndex", cols["x"] + 1)
            field("ScenarioValue", "text", "5")
            field("ScenarioStatistic", "currentIndex", 1)
            field("ScenarioAssumption", "currentIndex", 2)
            get("AddScenario").clicked.emit()
        for name, text in [
            ("Question", "Resampling planı: " + method),
            ("Hypothesis", "H0 açık exchangeability / fark0"),
            ("MeasurementUnit", "puan"),
            ("Observation", "bağımsız " + unit),
        ]:
            field(name, "text", text)
        field("Measurement", "checked", True)
        field("Independent", "checked", True)
        assert not get("Run").property("enabled")
        get("Preflight").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText, (method, controller.errorText)
        assert (
            controller.preflightCurrent
            and controller.preflight_result["resampling_unit"] == unit
        )
        field("Assumptions", "checked", True)
        assert get("Run").property("enabled")
        get("Run").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText, (method, unit, controller.errorText)
        assert controller.current and controller.result["worker_pid"] != os.getpid()
        assert "seed=42" in get("Result").property("text")
        assert "nedensellik" in get("Result").property("text")
        get("Help").clicked.emit()
        assert window.property("infoOpen")
        assert engine._learning_resources.article[
            "id"
        ] == "resampling-" + method.replace("_", "-")
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        export = tmp_path / "explicit-export"
        field("ExportPath", "text", str(export))
        get("Export").clicked.emit()
        assert not controller.errorText
        exported = json.loads((export / "result.json").read_text())
        recipe = json.loads((export / "recipe.json").read_text())
        assert exported["spec"] == recipe["spec"]
        assert exported["provenance"]["seed"] == 42
        if method.startswith("adjust_"):
            assert exported["family"]["ids"] == ["t1", "t2", "t3", "t4"] and exported[
                "family"
            ]["outside_family"] == ["outside"]
        assert (export / "members.parquet").is_file() and (
            export / "details.parquet"
        ).is_file()
        if capture:
            capture(app, window, controller, method, unit, export)
        primary = json.loads(Path(controller.result["paths"]["result"]).read_text())
        get("Save").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText
        if method.startswith("adjust_"):
            field("FamilyIds", "text", "")
        root = str(projects.store.root)
        assert projects.closeProject(True)
        assert projects.open(root)
        get("Open").clicked.emit()
        app.processEvents()
        assert not controller.errorText
        assert controller.current
        assert controller.result["unit_members"] == primary["unit_members"]
        assert controller.result["spec"] == primary["spec"]
        engine._workspace_resources.activate("statistics.ols")
        app.processEvents()
        assert not get("Expanded").property("checked")
        engine._workspace_resources.activate("statistics." + method.replace("_", "-"))
        app.processEvents()
        assert get("Expanded").property("checked")
        controller.invalidate()
        assert not controller.current
        assert "ESKİ" in get("Status").property("text")
        controller.exportAdvanced(str(tmp_path / "stale-export"))
        assert controller.errorText and not (tmp_path / "stale-export").exists()
        assert source.read_bytes() == before
    finally:
        teardown(app, window)


def test_gui_rejects_dependent_row_sampling_and_cancels_without_publish(
    tmp_path, monkeypatch
):
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
            return window.findChild(QObject, "resampling" + name) or visual_find(
                window.contentItem(), "resampling" + name
            )

        get("Expanded").setProperty("checked", True)
        get("Dependence").setProperty("currentIndex", 1)
        for name, text in [
            ("Question", "Önceden plan"),
            ("Hypothesis", "Mean"),
            ("MeasurementUnit", "puan"),
            ("Observation", "kişiler"),
        ]:
            get(name).setProperty("text", text)
        get("Measurement").setProperty("checked", True)
        get("Independent").setProperty("checked", True)
        get("Preflight").clicked.emit()
        assert c.errorText and "tek satır" in c.errorText
        get("Dependence").setProperty("currentIndex", 0)
        get("Preflight").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText
        get("Assumptions").setProperty("checked", True)
        get("Replicates").setProperty("value", 10000)
        # Preflight fingerprint binds the explicit repetitions, so rerun it.
        get("Preflight").clicked.emit()
        spin(app, lambda: not c.busy)
        get("Assumptions").setProperty("checked", True)
        get("Run").clicked.emit()
        assert c.busy
        get("Cancel").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText
        assert not projects.draft["results"]
        data = engine._dataset_resources
        data.view = replace(data.view, filters=[])
        data.changed.emit()
    finally:
        teardown(app, window)
