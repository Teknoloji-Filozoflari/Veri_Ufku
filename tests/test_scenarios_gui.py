"""Actual desktop recipes, process budget, cancel, publication and saved reopen."""

import json

import pytest
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_scenarios import lp

from veri_ufku.modeling.scenario_contracts import example

CAPTURE = None


@pytest.mark.parametrize(
    "method", ["monte-carlo", "linear", "mixed-integer", "nonlinear"]
)
def test_real_scenario_gui(tmp_path, monkeypatch, method):
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    c = engine._scenario_resources
    try:
        before = projects.store.commit_id
        engine._workspace_resources.activate("scenario." + method)
        spin(
            app,
            lambda: window.findChild(QObject, "scenarioExpanded").property("checked"),
        )
        assert projects.store.commit_id == before and not c.busy
        spec = lp(method) if method in ("linear", "mixed-integer") else example(method)
        editor = window.findChild(QObject, "scenarioRecipe")
        editor.setProperty("text", json.dumps(spec))
        window.findChild(QObject, "scenarioRun").clicked.emit()
        spin(app, lambda: not c.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert (
            c.result["status"] == "completed" and projects.draft == projects.store.state
        )
        output = c.result["output"]
        assert (
            output["status"] == "completed"
            if method == "monte-carlo"
            else output["feasibility"]["feasible"]
        )
        report = window.findChild(QObject, "scenarioReport").property("text")
        assert spec["assumptions"] in report and "Yorum sınırları" in report
        assert (
            "draw=10000" in report
            if method == "monte-carlo"
            else "Feasible=true" in report
        )
        ident = c.saved[-1]["id"]
        if CAPTURE:
            CAPTURE(app, window, projects, c, method)
        if method == "monte-carlo":
            previous = projects.store.commit_id
            result = c.result.copy()
            window.findChild(QObject, "scenarioRun").clicked.emit()
            window.findChild(QObject, "scenarioCancel").clicked.emit()
            spin(app, lambda: not c.busy, timeout=60000)
            assert projects.store.commit_id == previous and c.result == result
            assert "iptal" in c.errorText
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        c.openReport(ident)
        assert not c.errorText and c.result["output"] == output
    finally:
        teardown(app, window)


def test_real_frozen_model_scenario_gui(tmp_path, monkeypatch):
    from test_monitoring import trained_fixture

    build = tmp_path / "build"
    build.mkdir()
    store, r, w, work, monitor = trained_fixture(build)
    target = str(store.root)
    frozen = store.state["results"][-1].copy()
    store.close()
    config = tmp_path / "config/veri_ufku"
    config.mkdir(parents=True, exist_ok=True)
    (config / "settings.json").write_text(
        json.dumps({"budget": {"ram_bytes": 4 * 1024**3}})
    )
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    c = engine._scenario_resources
    try:
        assert projects.closeProject(True) and projects.open(target)
        engine._workspace_resources.activate("scenario.what-if")
        spin(
            app,
            lambda: window.findChild(QObject, "scenarioExpanded").property("checked"),
        )
        combo = window.findChild(QObject, "scenarioModel")
        combo.setProperty(
            "currentIndex",
            next(i for i, v in enumerate(c.models) if v["id"] == monitor.champion),
        )
        for method in ("what-if", "model-optimize"):
            window.findChild(QObject, "scenarioMethod").setProperty(
                "currentIndex", list(c.methods).index(method)
            )
            window.findChild(QObject, "scenarioModelTemplate").clicked.emit()
            recipe = json.loads(
                window.findChild(QObject, "scenarioRecipe").property("text")
            )
            assert recipe["model"]["record_id"] == monitor.champion
            window.findChild(QObject, "scenarioRun").clicked.emit()
            spin(app, lambda: not c.busy, timeout=60000)
            assert not c.errorText, c.errorText
            assert (
                c.result["output"]["feasibility"]["feasible"]
                and not c.result["output"]["optimal"]
            )
            assert c.result["fit_calls"] == 0
            if CAPTURE:
                CAPTURE(app, window, projects, c, method)
        assert frozen in projects.draft["results"]
    finally:
        teardown(app, window)


def test_real_solver_status_gui(tmp_path, monkeypatch):
    from test_scenarios import q

    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    c = app._veri_ufku_resources[0]._scenario_resources
    try:
        window.setProperty("selectedSection", 5)
        window.findChild(QObject, "scenarioExpanded").setProperty("checked", True)
        for status in ("infeasible", "unbounded", "timeout"):
            spec = lp()
            if status == "infeasible":
                spec["constraints"].append(
                    dict(linear=[q(1), q(0)], sense="ge", rhs=3, unit="dimensionless")
                )
            elif status == "unbounded":
                spec["constraints"] = []
            else:
                spec["seconds"] = 1e-6
            window.findChild(QObject, "scenarioRecipe").setProperty(
                "text", json.dumps(spec)
            )
            window.findChild(QObject, "scenarioRun").clicked.emit()
            spin(app, lambda: not c.busy, timeout=60000)
            assert not c.errorText, c.errorText
            assert c.result["output"]["status"] == status
            assert not c.result["output"]["optimal"]
            assert "optimum=false" in window.findChild(
                QObject, "scenarioReport"
            ).property("text")
            if CAPTURE:
                CAPTURE(app, window, projects, c, status)
    finally:
        teardown(app, window)
