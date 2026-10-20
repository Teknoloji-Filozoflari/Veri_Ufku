"""Real QML imports, five bounded tasks, review, export and immutable predictions."""

import json
import os

import pytest
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_vision import fixture, images

CAPTURE = None


def imported(tmp_path, monkeypatch, task="classification"):
    config = tmp_path / "config/veri_ufku"
    config.mkdir(parents=True)
    (config / "settings.json").write_text(
        json.dumps({"budget": {"ram_bytes": 4 * 1024**3}})
    )
    weights = None
    if task == "transfer":
        from veri_ufku.modeling.vision import calculate
        from veri_ufku.modeling.vision_contracts import VisionSpec
        from veri_ufku.storage.vision_store import export_weights

        parent = tmp_path / "pretraining"
        parent.mkdir()
        store, request, work, _ = fixture(parent)
        try:
            trained = calculate(
                request, VisionSpec(task="classification", epochs=2).data(), work
            )
            weights = tmp_path / "weights"
            weights.mkdir()
            export_weights(
                trained,
                weights / "model.json",
                "CC0-1.0",
                "Synthetic developer fixture",
            )
        finally:
            store.close()
    folder = tmp_path / "images"
    images(
        folder,
        seed=59 if task == "transfer" else 57,
        prefix="bankB" if task == "transfer" else "bankA",
    )
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    vision = engine._vision_resources
    window.setProperty("selectedSection", 5)
    engine._workspace_resources.activate("model.vision." + task)
    window.findChild(QObject, "visionSource").setProperty("text", str(folder))
    window.findChild(QObject, "visionChoose").clicked.emit()
    spin(app, lambda: not imports.busy)
    assert imports.ready, imports.errorText
    button = window.findChild(QObject, "visionImport")
    assert button.property("enabled")
    button.clicked.emit()
    spin(app, lambda: not imports.busy)
    assert not imports.errorText, imports.errorText
    vision.data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
    spin(app, lambda: not vision.data.busy)
    window.findChild(QObject, "visionEpochs").setProperty("text", "3")
    if weights:
        window.findChild(QObject, "visionModelFolder").setProperty("text", str(weights))
    return app, window, projects, imports, vision, folder


@pytest.mark.parametrize(
    "task", ["scan", "classification", "transfer", "detection", "segmentation"]
)
def test_real_gui_task_reopen_and_new_data(tmp_path, monkeypatch, task):
    app, window, projects, imports, vision, folder = imported(
        tmp_path, monkeypatch, task
    )
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    try:
        window.findChild(QObject, "visionHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert (
            app._veri_ufku_resources[0]._learning_resources.article["id"]
            == "vision-images"
        )
        window.setProperty("infoOpen", False)
        button = window.findChild(QObject, "visionRun")
        assert button.property("enabled"), (
            vision.canVisionRun,
            vision.data.dataset(),
            vision.busy,
            projects.busy,
        )
        button.clicked.emit()
        spin(app, lambda: not vision.busy, timeout=90000)
        assert not vision.errorText, vision.errorText
        assert vision.active["status"] == "completed"
        assert vision.active["worker_pid"] != os.getpid()
        assert vision.active["vision_spec"]["task"] == task
        if task == "transfer":
            assert vision.active["backbone_frozen"]
        root = str(projects.store.root)
        record = vision.savedRuns[-1]["id"]
        assert projects.closeProject(True) and projects.open(root)
        vision.openRun(record)
        assert not vision.errorText, vision.errorText
        if task != "scan":
            new = tmp_path / "new-images"
            images(new, seed=60, n=8, prefix="bankB", human=False)
            imports.choose(str(new))
            spin(app, lambda: not imports.busy)
            imports.importData()
            spin(app, lambda: not imports.busy)
            assert not imports.errorText, imports.errorText
            vision.data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
            spin(app, lambda: not vision.data.busy)
            window.findChild(QObject, "visionPredict").clicked.emit()
            spin(app, lambda: not vision.busy, timeout=90000)
            assert not vision.errorText, vision.errorText
            assert vision.predictionReport["fit"] is False
            assert len(vision.predictionReport["predictions"]) == 8
            assert all(
                p["status"] == "model" for p in vision.predictionReport["predictions"]
            )
        assert before == {p.name: p.read_bytes() for p in folder.iterdir()}
        if CAPTURE:
            CAPTURE(app, window, projects, vision, task)
    finally:
        teardown(app, window)


def test_real_gui_review_export_and_cancel(tmp_path, monkeypatch):
    app, window, projects, _, vision, _ = imported(tmp_path, monkeypatch)
    try:
        window.findChild(QObject, "visionRun").clicked.emit()
        spin(app, lambda: not vision.busy, timeout=90000)
        assert not vision.errorText, vision.errorText
        trained_id = vision.active["run_id"]
        plan = vision.active["plan"]
        window.findChild(QObject, "visionReviewer").setProperty(
            "text", "Sensitive Reviewer"
        )
        window.findChild(QObject, "visionHumanConsent").setProperty("checked", True)
        window.findChild(QObject, "visionReview").clicked.emit()
        spin(app, lambda: not vision.busy)
        assert not vision.errorText, vision.errorText
        assert vision.active["annotation_parent"] == trained_id
        assert vision.active["plan"] == plan and not vision.active["model_weights"]
        target = tmp_path / "annotations.json"
        window.findChild(QObject, "visionExportPath").setProperty("text", str(target))
        window.findChild(QObject, "visionExport").clicked.emit()
        spin(app, lambda: not vision.busy)
        assert not vision.errorText, vision.errorText
        assert "Sensitive Reviewer" not in target.read_text()
        window.findChild(QObject, "visionEpochs").setProperty("text", "50")
        window.findChild(QObject, "visionRun").clicked.emit()
        spin(
            app,
            lambda: (
                vision.active is not None
                and vision.active["run_id"] != trained_id
                and vision.active["epoch"] >= 1
            ),
            timeout=90000,
        )
        window.findChild(QObject, "visionCancel").clicked.emit()
        spin(app, lambda: not vision.busy, timeout=90000)
        assert not vision.errorText, vision.errorText
        assert (
            vision.active["status"] == "canceled" and not vision.active["model_weights"]
        )
        if CAPTURE:
            CAPTURE(app, window, projects, vision, "review-export-cancel")
    finally:
        teardown(app, window)
