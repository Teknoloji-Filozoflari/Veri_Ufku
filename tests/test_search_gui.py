"""Actual QML/spawn nested search, model handoff, durable test history and resume."""

import json
import os

import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import spin, teardown
from test_validation_gui import imported

CAPTURE = None
CASES = [
    ("grid", "independent", "regression"),
    ("random", "independent", "regression"),
    ("grid", "group_time", "regression"),
    ("random", "group_time", "regression"),
    ("grid", "independent", "classification"),
]


@pytest.mark.parametrize("method,structure,purpose", CASES)
def test_real_search_controls_and_model_handoff(
    tmp_path, monkeypatch, method, structure, purpose
):
    app, window, projects, prep, validation, source = imported(
        tmp_path, monkeypatch, structure, purpose
    )
    engine = app._veri_ufku_resources[0]
    search = engine._search_resources
    before = source.read_bytes()
    try:
        engine._workspace_resources.activate("model.search." + method)
        assert window.findChild(QObject, "searchExpanded").property("checked")
        assert (
            window.findChild(QObject, "searchMethod").property("currentValue") == method
        )
        window.findChild(QObject, "searchHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert engine._learning_resources.article["id"] == "model-search"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        run = window.findChild(QObject, "searchRun")
        assert run.property("enabled")
        run.clicked.emit()
        spin(app, lambda: not search.busy, timeout=90000)
        assert not search.errorText, search.errorText
        assert search.result and search.result["status"] == "completed", (
            search.historyReport
        )
        assert len(search.result["outer_evaluations"]) == 3
        assert len(search.result["curves"]) == 4
        assert all(t["status"] == "completed" for t in search.result["trials"])
        assert source.read_bytes() == before
        assert not validation.testHistory
        spin(
            app,
            lambda: bool(window.findChild(QObject, "searchApply").property("enabled")),
        )
        assert validation.canRun, dict(
            preparation_current=prep.current,
            prep_binding=prep.result_binding,
            current_binding=prep.current_binding(),
            projects_busy=projects.busy,
            dataset_active=projects.dataset_active,
            read_only=projects.readOnly,
            validation_busy=validation.busy,
            search_stage=search.stage,
        )
        window.findChild(QObject, "searchApply").clicked.emit()
        spin(app, lambda: not validation.busy, timeout=90000)
        assert not validation.errorText, validation.errorText
        assert (
            validation.result["selected_model"]
            == search.result["recommended"]["method"]
        )
        assert validation.result["plan"] == search.result["plan"]
        assert validation.result["worker_pid"] != os.getpid()
        if method == "grid" and structure == "independent" and purpose == "regression":
            window.findChild(QObject, "validationTestConsent").setProperty(
                "checked", True
            )
            window.findChild(QObject, "validationTest").clicked.emit()
            spin(app, lambda: not validation.busy, timeout=90000)
            assert not validation.errorText, validation.errorText
            use = validation.testHistory[-1]
            assert use["status"] == "completed"
            run.clicked.emit()
            spin(app, lambda: not search.busy, timeout=90000)
            assert not search.errorText, search.errorText
            assert len(search.result["prior_test_use_ids"]) == 1
            assert all(
                t["prior_test_use_ids"] == search.result["prior_test_use_ids"]
                for t in search.result["trials"]
            )
            assert {
                k: v
                for k, v in validation.testHistory[-1].items()
                if k != "subsequent_choices"
            } == {k: v for k, v in use.items() if k != "subsequent_choices"}
            assert validation.testHistory[-1]["subsequent_choices"]
        exported = tmp_path / "search-history.json"
        window.findChild(QObject, "searchExportPath").setProperty("text", str(exported))
        window.findChild(QObject, "searchExport").clicked.emit()
        spin(app, lambda: not search.busy)
        assert not search.errorText, search.errorText
        assert json.loads(exported.read_text()) == search.active
        if CAPTURE:
            CAPTURE(app, window, search, method, structure, purpose, projects)
        record = search.savedSearches[-1]["id"]
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        search.openSearch(record)
        assert search.result["status"] == "completed"
        assert source.read_bytes() == before
    finally:
        teardown(app, window)


@pytest.mark.parametrize("structure", ["independent", "group_time"])
def test_real_cancel_resume_preserves_previous_result_and_optional_disabled(
    tmp_path, monkeypatch, structure
):
    app, window, projects, prep, validation, source = imported(
        tmp_path, monkeypatch, structure
    )
    search = app._veri_ufku_resources[0]._search_resources
    try:
        window.findChild(QObject, "searchExpanded").setProperty("checked", True)
        method = window.findChild(QObject, "searchMethod")
        method.setProperty("currentIndex", 2)
        assert not window.findChild(QObject, "searchRun").property("enabled")
        method.setProperty("currentIndex", 1)
        window.findChild(QObject, "searchCurves").setProperty("checked", False)
        run = window.findChild(QObject, "searchRun")
        run.clicked.emit()
        spin(app, lambda: not search.busy, timeout=90000)
        assert not search.errorText, search.errorText
        previous = json.dumps(search.result, sort_keys=True)
        run.clicked.emit()
        spin(
            app,
            lambda: (
                search.active is not None
                and any(t["status"] == "running" for t in search.active["trials"])
            ),
            timeout=90000,
        )
        window.findChild(QObject, "searchCancel").clicked.emit()
        spin(app, lambda: not search.busy, timeout=90000)
        assert not search.errorText, search.errorText
        assert json.dumps(search.result, sort_keys=True) == previous
        latest = search.savedSearches[-1]["id"]
        assert search.active["status"] == "canceled"
        completed = [t for t in search.active["trials"] if t["status"] == "completed"]
        saved = window.findChild(QObject, "searchSaved")
        saved.setProperty("currentIndex", len(search.savedSearches) - 1)
        assert saved.property("currentValue") == latest
        window.findChild(QObject, "searchResume").clicked.emit()
        spin(app, lambda: not search.busy, timeout=90000)
        assert not search.errorText, search.errorText
        assert search.result["status"] == "completed"
        assert all(t in search.result["trials"] for t in completed)
        assert not validation.testHistory
    finally:
        teardown(app, window)


def test_real_early_stopping_and_pruning_controls(tmp_path, monkeypatch):
    app, window, projects, prep, validation, source = imported(tmp_path, monkeypatch)
    search = app._veri_ufku_resources[0]._search_resources
    before = source.read_bytes()
    try:
        window.findChild(QObject, "searchExpanded").setProperty("checked", True)
        window.findChild(QObject, "searchMethod").setProperty("currentIndex", 0)
        window.findChild(QObject, "searchTrials").setProperty("text", "1")
        window.findChild(QObject, "searchCurves").setProperty("checked", False)
        window.findChild(QObject, "searchSpace").setProperty(
            "text",
            json.dumps(
                {
                    "methods": ["gradient_boosting"],
                    "parameters": [{"name": "trees", "values": [20]}],
                }
            ),
        )
        window.findChild(QObject, "searchEarlyStopping").setProperty("checked", True)
        window.findChild(QObject, "searchRun").clicked.emit()
        spin(app, lambda: not search.busy, timeout=90000)
        assert not search.errorText, search.errorText
        assert search.result["status"] == "completed"
        assert all(
            f["early_stopping"] and f["selected_trees"] in (10, 20)
            for t in search.result["trials"]
            for f in t["folds"]
        )
        previous = json.dumps(search.result, sort_keys=True)
        window.findChild(QObject, "searchEarlyStopping").setProperty("checked", False)
        window.findChild(QObject, "searchPruning").setProperty("checked", True)
        window.findChild(QObject, "searchPruneThreshold").setProperty("text", "-1")
        window.findChild(QObject, "searchRun").clicked.emit()
        spin(app, lambda: not search.busy, timeout=90000)
        assert not search.errorText, search.errorText
        assert search.active["status"] == "failed"
        assert any(t["status"] == "pruned" for t in search.active["trials"])
        assert json.dumps(search.result, sort_keys=True) == previous
        assert source.read_bytes() == before
    finally:
        teardown(app, window)
