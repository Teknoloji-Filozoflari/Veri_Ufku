"""Actual QML preparation, separate worker, durable plans and stale/cancel binding."""

import json
import os

import pytest
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_preparation import frame


def imported(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "source.parquet"
    frame().write_parquet(source)
    imports.choose(str(source))
    spin(app, lambda: not imports.busy)
    imports.importData()
    spin(app, lambda: not imports.busy)
    assert not imports.errorText
    engine = app._veri_ufku_resources[0]
    return app, window, projects, engine, engine._preparation_resources, source


@pytest.mark.parametrize(
    "purpose,family",
    [
        ("regression", "linear"),
        ("classification", "tree"),
        ("clustering", "distance"),
        ("anomaly", "tree"),
    ],
)
def test_real_qml_purposes_save_reopen_and_help(tmp_path, monkeypatch, purpose, family):
    app, window, projects, engine, controller, source = imported(tmp_path, monkeypatch)
    original = source.read_bytes()
    try:
        window.setProperty("selectedSection", 5)
        panel = window.findChild(QObject, "preparationPanel")
        assert panel.property("visible")
        assert not window.findChild(QObject, "availabilityNotice").property("visible")
        cols = {c["name"]: i for i, c in enumerate(controller.columns)}
        for name, value in [
            (
                "Purpose",
                ["regression", "classification", "clustering", "anomaly"].index(
                    purpose
                ),
            ),
            ("Family", ["linear", "distance", "tree"].index(family)),
            ("Target", cols["y"]),
            ("Group", cols["group"] + 1),
            ("Time", cols["when"] + 1),
        ]:
            obj = window.findChild(QObject, "preparation" + name)
            assert obj.setProperty("currentIndex", value)
        panel.setProperty(
            "chosenFeatures",
            [c["id"] for c in controller.columns if c["name"] in ("x", "cat", "when")],
        )
        window.findChild(QObject, "preparationScan").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText, controller.errorText
        assert controller.current and controller.result["fitted"] is False
        assert controller.result["worker_pid"] != os.getpid()
        assert controller.result["spec"]["family"] == family
        assert controller.result["dataset_n"] == 6
        assert "Fit edilmedi" in window.findChild(
            QObject, "preparationSummary"
        ).property("text")
        window.findChild(QObject, "preparationSave").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText
        saved = next(r for r in projects.draft["results"] if "preparation" in r)
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        window.findChild(QObject, "preparationOpen").clicked.emit()
        assert not controller.errorText
        assert controller.result["plan"] == saved["preparation"]["plan"]
        for context in (
            "model",
            "model.prepare",
            "model.features",
            "model.encoding",
            "model.scaling",
            "model.imputation",
            "model.training-fold",
            "model.history",
        ):
            engine._learning_resources.openContext(context)
            assert engine._learning_resources.article["id"].startswith("model-")
        assert source.read_bytes() == original
        controller.invalidate()
        assert not controller.current
    finally:
        teardown(app, window)


def test_cancel_stale_and_failed_new_job_do_not_rebind_previous_plan(
    tmp_path, monkeypatch
):
    app, window, projects, engine, c, source = imported(tmp_path, monkeypatch)
    try:
        cols = {x["name"]: x["id"] for x in c.columns}
        spec = dict(
            purpose="regression", features=[cols["x"], cols["cat"]], target=cols["y"]
        )
        c.create(json.dumps(spec))
        spin(app, lambda: not c.busy)
        old = c.result
        assert c.current
        c.invalidate()
        c.create(json.dumps(dict(spec, encoding="ordinal")))
        spin(app, lambda: not c.busy)
        assert c.errorText and c.result is old and not c.current
        c.create(json.dumps(spec))
        c.cancel()
        spin(app, lambda: not c.busy)
        assert c.result is old and not c.current and "İptal" in c.message
        c.create(json.dumps(spec))
        c.invalidate()
        spin(app, lambda: not c.busy)
        assert c.result is old and not c.current and "Eski" in c.message
        assert not projects.busy
    finally:
        teardown(app, window)
