"""Real QML/spawn scan, cancellation, immutable project and report roundtrip."""

import copy

from PySide6.QtCore import QObject
from test_dataset_gui import load
from test_import_gui import spin, teardown


def test_quality_qml_scan_save_reopen(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch)
    original = source.read_bytes()
    before = copy.deepcopy(projects.draft)
    try:
        window.setProperty("selectedSection", 1)
        window.findChild(QObject, "datasetTabs").setProperty("currentIndex", 2)
        window.findChild(QObject, "qualityRuleColumn").setProperty("currentIndex", 1)
        window.findChild(QObject, "qualityRuleKind").setProperty("currentIndex", 2)
        window.findChild(QObject, "qualityRuleValue").setProperty("text", "0")
        window.findChild(QObject, "qualityRuleUpper").setProperty("text", "10")
        window.findChild(QObject, "qualityAddRule").clicked.emit()
        window.findChild(QObject, "qualityScanButton").clicked.emit()
        spin(app, lambda: not data.busy)
        assert not data.errorText
        report = data.qualityResult
        assert report["scope"] == "full" and report["used_n"] == 450
        assert any(f["code"] == "constant" for f in report["findings"])
        assert (
            next(f for f in report["findings"] if f["code"] == "rule")["count"] == 439
        )
        assert projects.draft == before and source.read_bytes() == original
        assert window.findChild(QObject, "qualityPanel").property("visible")
        window.findChild(QObject, "qualitySaveButton").clicked.emit()
        assert projects.dirty
        projects.save()
        spin(app, lambda: not projects.busy)
        assert projects.closeProject() and projects.open(str(tmp_path / "project"))
        assert projects.draft["results"][-1]["quality"] == report
        assert data.qualityResult == report
        assert source.read_bytes() == original
        assert not list(data.cache.glob("view-*"))
    finally:
        teardown(app, window)


def test_quality_cancel_and_stale(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 10000)
    before = copy.deepcopy(projects.draft)
    try:
        data.computeQuality(False, "dataset", "clean", "[]", "[]")
        data.cancel()
        spin(app, lambda: not data.busy)
        assert data.qualityResult == {} and projects.draft == before
        data.computeQuality(False, "dataset", "model", "[]", "[]")
        data.selectColumn(data.dataset()["import_metadata"]["columns"][1]["id"])
        spin(app, lambda: not data.busy)
        assert data.qualityResult == {} and "Eski veri" in data.message
        assert projects.draft == before
        data.computeQuality(False, "dataset", "inspect", "[]", "not JSON")
        assert data.errorText and not data.busy
    finally:
        teardown(app, window)
