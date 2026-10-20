"""Real QML actions, CPU spawn, durable safe checkpoints and target-free new prediction."""

import json
import os

import numpy as np
import polars as pl
import pytest
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown

CAPTURE = None


def imported(tmp_path, monkeypatch, template="mlp", classification=False):
    config = tmp_path / "config/veri_ufku"
    config.mkdir(parents=True, exist_ok=True)
    (config / "settings.json").write_text(
        json.dumps({"budget": {"ram_bytes": 4 * 1024**3}})
    )
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    rng = np.random.default_rng(56)
    values = rng.normal(size=(80, 16 if template == "cnn" else 2))
    frame = pl.DataFrame({f"x{i}": values[:, i] for i in range(values.shape[1])})
    frame = frame.with_columns(
        pl.Series(
            "y",
            np.where(values[:, 0] > 0, "evet", "hayır")
            if classification
            else 2 * values[:, 0] + values[:, 1],
        )
    )
    source = tmp_path / "tensor.parquet"
    frame.write_parquet(source)
    imports.choose(str(source))
    spin(app, lambda: not imports.busy)
    imports.importData()
    spin(app, lambda: not imports.busy)
    assert not imports.errorText
    engine = app._veri_ufku_resources[0]
    prep = engine._preparation_resources
    cols = {c["name"]: c["id"] for c in prep.columns}
    features = [cols[f"x{i}"] for i in range(values.shape[1])]
    prep.create(
        json.dumps(
            dict(
                purpose="classification" if classification else "regression",
                features=features,
                target=cols["y"],
                prediction_context="Ölçüm öncesi",
                numeric_imputation="mean",
            )
        )
    )
    spin(app, lambda: not prep.busy)
    assert not prep.errorText and not prep.result["blockers"]
    panel = window.findChild(QObject, "validationPanel")
    panel.setProperty(
        "availability",
        {c: dict(offset_seconds=0, note="known before") for c in features},
    )
    window.setProperty("selectedSection", 5)
    engine._workspace_resources.activate("model.neural." + template)
    window.findChild(QObject, "neuralEpochs").setProperty("text", "6")
    window.findChild(QObject, "neuralPatience").setProperty("text", "10")
    if template == "cnn":
        window.findChild(QObject, "neuralPixels").setProperty(
            "text", "16 gerçek piksel: NCHW row-major 1×4×4"
        )
        window.findChild(QObject, "neuralFlip").setProperty("checked", True)
    return app, window, projects, imports, engine._neural_resources, frame, source


@pytest.mark.parametrize(
    "template,classification", [("mlp", False), ("mlp", True), ("cnn", True)]
)
def test_real_gui_training_reopen_new_data_prediction(
    tmp_path, monkeypatch, template, classification
):
    app, window, projects, imports, neural, frame, source = imported(
        tmp_path, monkeypatch, template, classification
    )
    before = source.read_bytes()
    try:
        assert window.findChild(QObject, "neuralExpanded").property("checked")
        window.findChild(QObject, "neuralHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert (
            app._veri_ufku_resources[0]._learning_resources.article["id"]
            == "neural-training"
        )
        window.setProperty("infoOpen", False)
        button = window.findChild(QObject, "neuralRun")
        assert button.property("enabled")
        button.clicked.emit()
        spin(app, lambda: not neural.busy, timeout=90000)
        assert not neural.errorText, neural.errorText
        assert neural.active["status"] == "completed"
        assert neural.active["worker_pid"] != os.getpid()
        assert len(neural.active["curves"]) == 6
        record = neural.savedRuns[-1]["id"]
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        neural.openRun(record)
        assert not neural.errorText and neural.active["status"] == "completed"
        new_path = tmp_path / "new-tensor.parquet"
        frame.drop("y").head(5).write_parquet(new_path)
        imports.choose(str(new_path))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText
        neural.data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
        spin(app, lambda: not neural.data.busy)
        window.findChild(QObject, "neuralPredict").clicked.emit()
        spin(app, lambda: not neural.busy, timeout=90000)
        assert not neural.errorText, neural.errorText
        assert len(neural.predictionReport["values"]) == 5
        assert neural.predictionReport["fit"] is False
        d = neural.data.dataset()
        expected = pl.read_parquet(projects.store.path(d["snapshot_uri"]))[
            "__vu_row_id"
        ].to_list()
        assert neural.predictionReport["row_ids"] == expected
        assert source.read_bytes() == before
        from veri_ufku.storage.experiment_store import rows, verify

        item = next(r for r in rows(projects.store) if r["kind"] == "neural")
        assert item["status"] == "completed" and verify(projects.store, item)
        if CAPTURE:
            CAPTURE(app, window, projects, neural, template, classification)
    finally:
        teardown(app, window)


def test_real_gui_pause_resume_and_cancel(tmp_path, monkeypatch):
    app, window, projects, _, neural, _, source = imported(tmp_path, monkeypatch)
    try:
        window.findChild(QObject, "neuralEpochs").setProperty("text", "60")
        window.findChild(QObject, "neuralPatience").setProperty("text", "100")
        window.findChild(QObject, "neuralRun").clicked.emit()
        spin(
            app,
            lambda: neural.active is not None and neural.active["epoch"] >= 1,
            timeout=90000,
        )
        window.findChild(QObject, "neuralPause").clicked.emit()
        spin(app, lambda: not neural.busy, timeout=90000)
        assert not neural.errorText, neural.errorText
        assert neural.active["status"] == "paused"
        first = neural.active["epoch"]
        window.findChild(QObject, "neuralResume").clicked.emit()
        spin(app, lambda: neural.active["epoch"] > first, timeout=90000)
        window.findChild(QObject, "neuralCancel").clicked.emit()
        spin(app, lambda: not neural.busy, timeout=90000)
        assert not neural.errorText, neural.errorText
        assert neural.active["status"] == "canceled"
        assert all(
            r["model_choice"]["status"] != "completed"
            for r in projects.draft["results"]
            if "model_choice" in r
        )
        if CAPTURE:
            CAPTURE(app, window, projects, neural, "pause-resume-cancel", False)
    finally:
        teardown(app, window)
