"""Real QML, spawn preflight/run, cancellation, provenance, save/reopen and help."""

import json
import os

import polars as pl
import pytest
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_statistics import paired_frame, table_frame

from veri_ufku.statistics.contracts import METHODS


def fixture(path):
    if path == "paired":
        return paired_frame()
    if path == "categorical":
        return table_frame([[30, 10], [10, 30]])
    if path == "numeric":
        return pl.DataFrame(dict(x=[-2, -1, 0, 1, 2], y=[-2, 0, -1, 2, 1]))
    if path == "groups":
        return pl.DataFrame(
            dict(x=list(range(1, 16)), g=["A"] * 5 + ["B"] * 5 + ["C"] * 5)
        )
    return pl.DataFrame(dict(x=[1, 2, 3, 4, 3, 4, 5, 7], g=["A"] * 4 + ["B"] * 4))


@pytest.mark.parametrize(
    "path,method", [(p, m) for p, ms in METHODS.items() for m in ms]
)
def test_every_method_real_qml_preflight_spawn_save_and_reopen(
    tmp_path, monkeypatch, path, method
):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "statistics-source.parquet"
    fixture(path).write_parquet(source)
    original = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText
        engine = app._veri_ufku_resources[0]
        controller = engine._statistics_resources
        window.setProperty("selectedSection", 4)
        window.setProperty("examineTool", 0)
        spin(app, lambda: window.property("istatistikOpen"))
        assert not window.findChild(QObject, "availabilityNotice").property("visible")
        panel = window.findChild(QObject, "statisticsPanel")
        if panel is not None:
            panel.setProperty("liveEnabled", False)
            panel.setProperty("liveArmed", False)
        chip = window.findChild(QObject, "statisticsCatalogChip_3")
        if chip is not None:
            chip.clicked.emit()
            app.processEvents()
        cols = {c["name"]: i for i, c in enumerate(controller.columns)}

        def field(name, property, value):
            obj = window.findChild(QObject, "statistics" + name)
            assert obj is not None, name
            assert obj.setProperty(property, value)
            return obj

        field("Path", "currentIndex", list(METHODS).index(path))
        app.processEvents()
        field("Method", "currentIndex", list(METHODS[path]).index(method))
        field("X", "currentIndex", cols["x"])
        if path in ("numeric", "categorical"):
            field("Y", "currentIndex", cols["y"])
        if path in ("independent", "groups", "paired"):
            field("Group", "currentIndex", cols["phase" if path == "paired" else "g"])
        if path == "paired":
            field("Key", "currentIndex", cols["person"])
            field("Before", "text", "before")
            field("After", "text", "after")
        field("Question", "text", "Kullanıcının gerçek sorusu: " + method)
        field("Hypothesis", "text", "Seçili yöntemin sıfır hipotezi")
        field("Unit", "text", "puan" if path != "categorical" else "birimsiz")
        field("Observation", "text", "bağımsız kişi")
        field("Measurement", "checked", True)
        field("Independent", "checked", True)
        field("Posthoc", "checked", path == "groups")
        correction_index = {"anova": 1, "welch_anova": 2, "kruskal": 3}.get(method, 0)
        field("Correction", "currentIndex", correction_index)
        run = window.findChild(QObject, "statisticsRun")
        assert not run.property("enabled")
        window.findChild(QObject, "statisticsPreflight").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText, (method, controller.errorText)
        assert controller.preflightCurrent
        field("Assumptions", "checked", True)
        assert run.property("enabled")
        run.clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText, (method, controller.errorText)
        assert controller.result["worker_pid"] != os.getpid()
        assert controller.current and controller.result["method"] == method
        assert (
            controller.result["correction"]["method"]
            == ("holm", "bonferroni", "bh", "none")[correction_index]
        )
        text = window.findChild(QObject, "statisticsPrimary").property("text")
        assert "p=" in text and ("Güven" in text or "güven" in text)
        window.findChild(QObject, "statisticsSave").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText
        record = next(r for r in projects.draft["results"] if "analysis" in r)
        root = str(projects.store.root)
        assert projects.closeProject(True)
        assert projects.open(root)
        controller.openSaved(record["id"])
        assert not controller.errorText
        assert controller.result["primary"] == record["analysis"]["primary"]
        engine._learning_resources.openContext("statistics." + method.replace("_", "-"))
        assert engine._learning_resources.article[
            "id"
        ] == "statistics-" + method.replace("_", "-")
        assert source.read_bytes() == original
        controller.invalidate()
        assert not controller.current
    finally:
        teardown(app, window)


def test_stale_and_cancel_keep_previous_result(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "source.parquet"
    fixture("independent").write_parquet(source)
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        engine = app._veri_ufku_resources[0]
        controller = engine._statistics_resources
        cols = {c["name"]: c["id"] for c in controller.columns}
        spec = dict(
            path="independent",
            method="welch_t",
            x=cols["x"],
            group=cols["g"],
            question="Fark var mı?",
            hypothesis="Ortalamalar eşit",
            unit="puan",
            observation_unit="kişi",
            independent=True,
            measurement_confirmed=True,
            assumptions_confirmed=False,
        )
        controller.create(json.dumps(spec), True)
        controller.invalidate()
        spin(app, lambda: not controller.busy)
        assert controller.preflight_result is None and "Eski" in controller.message
        controller.create(json.dumps(spec), True)
        spin(app, lambda: not controller.busy)
        assert controller.preflightCurrent
        controller.create(json.dumps(dict(spec, assumptions_confirmed=True)), False)
        controller.cancel()
        spin(app, lambda: not controller.busy)
        assert controller.result is None and "İptal" in controller.message
        assert not projects.busy
    finally:
        teardown(app, window)
