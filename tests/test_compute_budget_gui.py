"""Actual optional-absent desktop opening and resource panel/process lifecycle."""

from PySide6.QtCore import QObject
from test_dataset_gui import load
from test_import_gui import spin, teardown

from veri_ufku.jobs.dask_backend import available


def CAPTURE(*args):
    pass


def test_real_profile_measurement_panel(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, rows=2000)
    try:
        supervisor = app._veri_ufku_resources[0]._resource_supervisor
        before = source.read_bytes()
        data.selectColumn(data.dataset()["import_metadata"]["columns"][1]["id"])
        data.computeProfile(False, "dataset", 1)
        assert data.process is not None
        supervisor.poll()
        assert supervisor.report["processes"] == 1
        assert any(r["kind"] == "DatasetController" for r in supervisor.report["rows"])
        spin(app, lambda: not data.busy)
        assert not data.errorText, data.errorText
        supervisor.poll()
        assert any(r["state"].startswith("Bitti") for r in supervisor.report["rows"])
        window.setProperty("selectedSection", 0)
        button = window.findChild(QObject, "computeBudgetButton")
        assert button
        button.clicked.emit()
        spin(
            app,
            lambda: window.findChild(QObject, "computeBudgetDialog").property(
                "visible"
            ),
        )
        assert not available(), "This case is the absent optional backend opening path"
        assert source.read_bytes() == before
        CAPTURE(app, window, projects, supervisor)
    finally:
        teardown(app, window)


def test_real_bounded_search_measurement(tmp_path, monkeypatch):
    """Explicit 4GiB, one candidate, no curves; preserves final-test isolation."""
    import json

    from test_validation_gui import imported

    config = tmp_path / "config/veri_ufku"
    config.mkdir(parents=True, exist_ok=True)
    (config / "settings.json").write_text(
        json.dumps({"budget": {"ram_bytes": 4 * 1024**3}})
    )
    app, window, projects, prep, validation, source = imported(tmp_path, monkeypatch)
    try:
        before = source.read_bytes()
        engine = app._veri_ufku_resources[0]
        search = engine._search_resources
        engine._workspace_resources.activate("model.search.grid")
        window.findChild(QObject, "searchSpace").setProperty(
            "text",
            '{"methods":["decision_tree"],"parameters":[{"name":"depth","values":[2]}]}',
        )
        window.findChild(QObject, "searchTrials").setProperty("text", "1")
        window.findChild(QObject, "searchCurves").setProperty("checked", False)
        window.findChild(QObject, "searchRun").clicked.emit()
        spin(app, lambda: not search.busy, timeout=150000)
        supervisor = engine._resource_supervisor
        supervisor.poll()
        CAPTURE(app, window, projects, supervisor)
        assert not search.errorText, search.errorText
        assert search.result["status"] == "completed", search.historyReport
        assert all(t["status"] == "completed" for t in search.result["trials"])
        assert len(search.result["outer_evaluations"]) == 3
        assert not validation.testHistory
        assert source.read_bytes() == before
        assert any(r["kind"] == "SearchController" for r in supervisor.report["rows"])
    finally:
        teardown(app, window)
