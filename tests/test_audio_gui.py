"""Actual QML audio source/CPU feature/classification/predict/unavailable paths."""

import os

import pytest
from PySide6.QtCore import QMetaObject, QObject, QPointF
from test_audio import recordings
from test_import_gui import setup, spin, teardown

CAPTURE = None


def imported(tmp_path, monkeypatch, task="features"):
    folder = tmp_path / "recordings"
    recordings(folder)
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    audio = engine._audio_resources
    window.setProperty("selectedSection", 5)
    engine._workspace_resources.activate("model.audio." + task)
    window.findChild(QObject, "audioSource").setProperty(
        "text", str(folder / "audio.json")
    )
    window.findChild(QObject, "audioChoose").clicked.emit()
    spin(app, lambda: not imports.busy)
    assert imports.ready, imports.errorText
    window.findChild(QObject, "audioImport").clicked.emit()
    spin(app, lambda: not imports.busy)
    assert not imports.errorText, imports.errorText
    spin(app, lambda: not audio.data.busy)
    audio.data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
    spin(app, lambda: not audio.data.busy)
    return app, window, projects, imports, audio, folder


@pytest.mark.parametrize("task", ["features", "classification"])
def test_real_audio_gui_reopen_new_data_prediction(tmp_path, monkeypatch, task):
    app, window, projects, imports, audio, folder = imported(
        tmp_path, monkeypatch, task
    )
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    try:
        window.findChild(QObject, "audioHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert (
            app._veri_ufku_resources[0]._learning_resources.article["id"]
            == "audio-features"
        )
        window.setProperty("infoOpen", False)
        button = window.findChild(QObject, "audioRun")
        assert button.property("enabled")
        button.clicked.emit()
        spin(app, lambda: not audio.busy, timeout=90000)
        assert not audio.errorText, audio.errorText
        assert (
            audio.active["status"] == "completed"
            and audio.active["worker_pid"] != os.getpid()
        )
        assert len(audio.active["features"]) == 32
        # Actual rendered spectral tone must be visible, not only a uniform Canvas.
        from PySide6.QtTest import QTest

        items = list(window.contentItem().childItems())
        canvas = None
        while items:
            item = items.pop()
            if item.objectName() == "audioSpectrogram":
                canvas = item
                break
            items.extend(item.childItems())
        assert canvas is not None
        canvas.forceActiveFocus()
        parent = canvas.parentItem()
        while parent is not None:
            if parent.property("contentY") is not None:
                pos = canvas.mapToItem(parent.property("contentItem"), 0, 0)
                parent.setProperty("contentY", max(0, pos.y() - 20))
                break
            parent = parent.parentItem()
        assert QMetaObject.invokeMethod(canvas, "requestPaint")
        QTest.qWait(150)
        pos = canvas.mapToScene(QPointF(0, 0))
        picture = window.grabWindow()
        warm = 0
        for yy in range(
            int(pos.y()), min(picture.height(), int(pos.y() + canvas.height()))
        ):
            for xx in range(
                int(pos.x()), min(picture.width(), int(pos.x() + canvas.width()))
            ):
                color = picture.pixelColor(xx, yy)
                warm += color.red() > 160 and color.green() > 80 and color.blue() < 120
        assert warm > 100, "Known 1000Hz tone not rendered in spectrogram"

        saved = audio.savedRuns[-1]["id"]
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        audio.openRun(saved)
        assert not audio.errorText, audio.errorText
        if task == "classification":
            new = tmp_path / "new-audio"
            recordings(new, seed=63, n=4, human=False, prefix="bankB")
            spin(app, lambda: not projects.busy and not audio.data.busy)
            imports.choose(str(new))
            spin(app, lambda: not imports.busy and not projects.busy)
            assert imports.ready, (
                imports.errorText,
                imports.message,
                projects.busy,
                projects.readOnly,
            )
            imports.importData()
            spin(app, lambda: not imports.busy)
            assert not imports.errorText, imports.errorText
            spin(app, lambda: not audio.data.busy)
            audio.data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
            spin(app, lambda: not audio.data.busy)
            window.findChild(QObject, "audioPredict").clicked.emit()
            spin(app, lambda: not audio.busy, timeout=90000)
            assert not audio.errorText, audio.errorText
            assert (
                audio.predictionReport["fit"] is False
                and len(audio.predictionReport["predictions"]) == 8
            )
            assert all(
                p["status"] == "model" for p in audio.predictionReport["predictions"]
            )
        if task == "classification":
            assert " → " in window.findChild(QObject, "audioPrediction").property(
                "text"
            )
        logs = list((tmp_path / "state").rglob("*.log"))
        assert all("Sensitive konuşma" not in p.read_text() for p in logs)
        assert before == {p.name: p.read_bytes() for p in folder.iterdir()}
        if CAPTURE:
            CAPTURE(app, window, projects, audio, task)
    finally:
        teardown(app, window)


def test_real_audio_gui_missing_speech_model_and_cancel(tmp_path, monkeypatch):
    app, window, projects, _, audio, _ = imported(tmp_path, monkeypatch, "transcribe")
    try:
        window.findChild(QObject, "audioSTTFolder").setProperty(
            "text", str(tmp_path / "missing-model")
        )
        window.findChild(QObject, "audioSTTConsent").setProperty("checked", True)
        window.findChild(QObject, "audioRun").clicked.emit()
        spin(app, lambda: not audio.busy, timeout=90000)
        assert "unavailable" in audio.errorText, audio.errorText
        assert not audio.active or audio.active["status"] != "completed"
        if CAPTURE:
            CAPTURE(app, window, projects, audio, "unavailable")
        # Request cancellation in the checkpoint notification. Polling outside
        # processEvents can observe an old running snapshot after a short feature
        # job has already finished; that is not a test of a live cancellation.
        requested = []

        def cancel_running():
            if (
                not requested
                and audio.busy
                and audio.active
                and audio.active["status"] == "running"
            ):
                requested.append(True)
                window.findChild(QObject, "audioCancel").clicked.emit()

        audio.changed.connect(cancel_running)
        window.findChild(QObject, "audioTask").setProperty("currentIndex", 0)
        window.findChild(QObject, "audioRun").clicked.emit()
        spin(app, lambda: not audio.busy, timeout=90000)
        audio.changed.disconnect(cancel_running)
        assert requested
        choices = [
            r["model_choice"]["status"]
            for r in projects.draft["results"]
            if "model_choice" in r
        ]
        assert choices[-1] == "canceled"
        assert (
            audio.active["status"] == "canceled" and not audio.active["model_weights"]
        )
        if CAPTURE:
            CAPTURE(app, window, projects, audio, "cancel")
    finally:
        teardown(app, window)
