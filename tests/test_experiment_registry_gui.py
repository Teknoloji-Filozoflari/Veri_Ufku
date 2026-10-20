"""Actual QML train, local registry, revision, compare/export and preserved journal."""

import json

from PySide6.QtCore import QObject, QUrl
from test_import_gui import spin, teardown
from test_validation_gui import imported

CAPTURE = None


def test_real_registry_qml_revision_compare_export_and_final_history(
    tmp_path, monkeypatch
):
    app, window, projects, p, c, source = imported(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    lifecycle = engine._lifecycle_resources
    before = source.read_bytes()
    try:
        window.findChild(QObject, "validationRun").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        row = lifecycle.experimentRuns[0]
        run_id = row["run_id"]
        assert row["code_hash"] and row["data_access_at"]
        panel = window.findChild(QObject, "experimentRegistryPanel")
        assert panel is not None and panel.property("visible")
        panel.setProperty("selected", [run_id])
        window.findChild(QObject, "experimentCompare").clicked.emit()
        spin(app, lambda: not lifecycle.busy)
        assert not lifecycle.errorText, lifecycle.errorText
        assert (
            lifecycle.experimentReport["comparable"]
            and lifecycle.experimentReport["points"]
        )
        window.findChild(QObject, "experimentMetricRevision").clicked.emit()
        spin(app, lambda: not lifecycle.busy)
        assert not lifecycle.errorText, lifecycle.errorText
        lifecycle.reviseExperiment(run_id, "model_status", '"selected"')
        spin(app, lambda: not lifecycle.busy)
        assert lifecycle.experimentRuns[0]["model_status"] == "selected"
        output = tmp_path / "registry.json"
        lifecycle.exportExperiments(
            json.dumps([run_id]), "mae", QUrl.fromLocalFile(str(output)).toString()
        )
        spin(app, lambda: not lifecycle.busy)
        assert not lifecycle.errorText and output.is_file(), lifecycle.errorText
        assert "params" not in json.loads(output.read_text())["rows"][0]
        window.findChild(QObject, "validationTest").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        journal = [r for r in projects.draft["results"] if "test_use" in r]
        assert journal and lifecycle.experimentRuns[0]["test_uses"]
        # A new training choice preserves the old test journal and exposes prior access.
        window.findChild(QObject, "validationRun").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert [r for r in projects.draft["results"] if "test_use" in r] == journal
        assert lifecycle.experimentRuns[-1]["test_seen_before"]
        engine._learning_resources.openContext("experiment.registry")
        assert engine._learning_resources.article["id"] == "experiment-registry"
        lifecycle.compareExperiments(json.dumps([run_id]), "mae")
        spin(app, lambda: not lifecycle.busy)
        if CAPTURE is not None:
            CAPTURE(window, lifecycle, projects, source)
        assert source.read_bytes() == before
        root = str(projects.store.root)
        assert projects.closeProject(True)
        assert lifecycle.experimentReport == {}
        assert projects.open(root)
        assert any(
            r["model_status"] == "selected"
            for r in lifecycle.experimentRuns
            if r.get("model_version")
        )
    finally:
        teardown(app, window)
