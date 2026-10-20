"""Real QML, spawned temporal calculation, final reveal, cancellation and reopen."""

import json
import os

from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_time_series import example


def test_separate_qml_path_spawn_final_help_reopen(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    c = engine._time_series_resources
    source = tmp_path / "series.parquet"
    example().write_parquet(source)
    before = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        data = engine._dataset_resources
        data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
        spin(app, lambda: not data.busy)
        window.setProperty("selectedSection", 5)
        path = window.findChild(QObject, "modelPath")
        path.setProperty("currentIndex", 1)
        assert window.findChild(QObject, "timeSeriesPanel").property("visible")
        d = data.dataset()
        cols = d["import_metadata"]["columns"]
        for name, field in (
            ("timeSeriesDate", "day"),
            ("timeSeriesMeasurement", "value"),
        ):
            control = window.findChild(QObject, name)
            control.setProperty(
                "currentIndex",
                next(i for i, col in enumerate(cols) if col["name"] == field),
            )
        window.findChild(QObject, "timeSeriesModel").setProperty("currentIndex", 3)
        window.findChild(QObject, "timeSeriesRun").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert c.current and c.result["worker_pid"] != os.getpid()
        assert c.result["mode"] == "development"
        assert c.report["groups"][0]["forecast"][0]["actual"] is None
        assert "train_row_ids" not in c.report["groups"][0]
        assert not c.report["groups"][0]["final_metrics"]
        dev_id = c.record_id
        window.findChild(QObject, "timeSeriesFinal").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert c.result["mode"] == "final" and c.result["groups"][0]["final_metrics"]
        use = next(
            r["time_series_test_use"]
            for r in projects.draft["results"]
            if "time_series_test_use" in r
        )
        assert use["status"] == "completed"
        assert source.read_bytes() == before
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
        spin(app, lambda: not data.busy)
        c.openSaved(dev_id)
        spin(app, lambda: not c.busy)
        assert not c.errorText and c.current, c.errorText
        assert c.result["mode"] == "development"
        for context in (
            "model.time-series",
            "timeseries.seasonality",
            "timeseries.lag",
            "timeseries.validation",
        ):
            engine._learning_resources.openContext(context)
            assert engine._learning_resources.article["id"].startswith("timeseries-")
        window.findChild(QObject, "timeSeriesHorizon").setProperty("text", "2")
        assert not c.current
        c.finalTest()
        assert c.errorText
        c.create(json.dumps(dict(c.result["spec"], horizon=2)))
        c.cancel()
        spin(app, lambda: not c.busy)
        assert source.read_bytes() == before
        assert len([r for r in projects.draft["results"] if "time_series" in r]) == 2
        # Dataset/model route remains independent from ordinary regression.
        path.setProperty("currentIndex", 0)
        assert not window.findChild(QObject, "timeSeriesPanel").property("visible")
    finally:
        teardown(app, window)
