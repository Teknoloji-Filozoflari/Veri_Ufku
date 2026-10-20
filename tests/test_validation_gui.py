"""Actual QML/spawn/journal blocking, cancellation and repeated final evaluation."""

import json
import os

from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_validation import fixture


def imported(tmp_path, monkeypatch, structure="independent", purpose="regression"):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "baseline.parquet"
    fixture().write_parquet(source)
    imports.choose(str(source))
    spin(app, lambda: not imports.busy)
    imports.importData()
    spin(app, lambda: not imports.busy)
    assert not imports.errorText
    engine = app._veri_ufku_resources[0]
    p = engine._preparation_resources
    c = engine._validation_resources
    cols = {x["name"]: x["id"] for x in p.columns}
    p.create(
        json.dumps(
            dict(
                purpose=purpose,
                features=[cols["x"], cols["cat"]],
                target=cols["y"],
                group=cols["group"] if structure in ("group", "group_time") else "",
                time=cols["when"] if structure in ("time", "group_time") else "",
                prediction_context="Cihaz çalıştırılmadan önce",
            )
        )
    )
    spin(app, lambda: not p.busy)
    assert not p.errorText and not p.result["blockers"]
    window.setProperty("selectedSection", 5)
    panel = window.findChild(QObject, "validationPanel")
    panel.setProperty(
        "availability",
        {
            cols[n]: dict(offset_seconds=0, note="Çalıştırmadan önce mevcut")
            for n in ("x", "cat")
        },
    )
    return app, window, projects, p, c, source


def test_real_qml_group_time_repeat_final_and_reopen(tmp_path, monkeypatch):
    app, window, projects, p, c, source = imported(tmp_path, monkeypatch, "group_time")
    before = source.read_bytes()
    try:
        assert (
            window.findChild(QObject, "validationStructure").property("currentIndex")
            == 3
        )
        run = window.findChild(QObject, "validationRun")
        assert run.property("enabled")
        run.clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert c.current and c.result["mode"] == "development"
        assert c.result["worker_pid"] != os.getpid()
        development = c.result
        record = next(r for r in projects.draft["results"] if "baseline" in r)
        for i in range(2):
            c.openRun(record["id"])
            consent = window.findChild(QObject, "validationTestConsent")
            consent.setProperty("checked", True)
            test = window.findChild(QObject, "validationTest")
            assert test.property("enabled")
            test.clicked.emit()
            spin(app, lambda: not c.busy)
            assert not c.errorText, c.errorText
            assert c.result["mode"] == "final"
            assert c.result["plan"] == development["plan"]
            assert len(c.testHistory) == i + 1
            assert c.testHistory[-1]["status"] == "completed"
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        c.openRun(record["id"])
        assert c.result["mode"] == "development" and len(c.testHistory) == 2
        engine = app._veri_ufku_resources[0]
        engine._learning_resources.openContext("model.validation")
        assert engine._learning_resources.article["id"] == "model-validation"
        assert source.read_bytes() == before
    finally:
        teardown(app, window)


def test_unsupported_qml_protocol_and_canceled_run_not_success(tmp_path, monkeypatch):
    app, window, projects, p, c, source = imported(tmp_path, monkeypatch, "group_time")
    try:
        window.findChild(QObject, "validationEntity").setProperty("currentIndex", 1)
        assert not window.findChild(QObject, "validationRun").property("enabled")
        c.create(json.dumps(dict(structure="group_time", entity_use="same_future")))
        assert c.errorText and not c.busy and not c.result
        window.findChild(QObject, "validationEntity").setProperty("currentIndex", 0)
        window.findChild(QObject, "validationRun").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        old = c.result
        run_id = old["run_id"]
        window.findChild(QObject, "validationRun").clicked.emit()
        c.cancel()
        spin(app, lambda: not c.busy)
        assert c.result is old and not c.current and "İptal" in c.message
        assert [
            r["baseline"]["run_id"]
            for r in projects.draft["results"]
            if "baseline" in r
        ] == [run_id]
        record = next(r for r in projects.draft["results"] if "baseline" in r)
        c.openRun(record["id"])
        c.evaluateTest()
        c.cancel()
        spin(app, lambda: not c.busy)
        assert c.testHistory[-1]["status"] == "canceled"
        assert not any(
            r.get("baseline", {}).get("mode") == "final"
            for r in projects.draft["results"]
        )
        c.openRun(record["id"])
        window.findChild(QObject, "validationRun").clicked.emit()
        c.invalidate()
        spin(app, lambda: not c.busy)
        assert c.result["mode"] == "development" and not c.current
    finally:
        teardown(app, window)


def test_impossible_time_fold_saved_as_failed_and_structured(tmp_path, monkeypatch):
    app, window, projects, p, c, source = imported(tmp_path, monkeypatch, "time")
    try:
        window.findChild(QObject, "validationHorizon").setProperty("text", "1000000000")
        window.findChild(QObject, "validationRun").clicked.emit()
        spin(app, lambda: not c.busy)
        assert c.errorText and c.invalidFolds and not c.result
        entry = next(
            r["model_choice"] for r in projects.draft["results"] if "model_choice" in r
        )
        assert entry["status"] == "failed" and entry["invalid_folds"] == c.invalidFolds
        assert not any("baseline" in r for r in projects.draft["results"])
    finally:
        teardown(app, window)
