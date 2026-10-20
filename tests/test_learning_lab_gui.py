"""Offline actual lesson workspace; user's dirty project remains byte-identical."""

import copy
from pathlib import Path

from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown

from veri_ufku.learning.curriculum import KERNELS
from veri_ufku.storage.project_store import file_hash

CAPTURE = None


def test_real_offline_lessons_isolated_project_and_resume_work(tmp_path, monkeypatch):
    import socket
    import urllib.request

    def offline(*args, **kwargs):
        raise AssertionError("Lesson attempted network")

    monkeypatch.setattr(socket, "create_connection", offline)
    monkeypatch.setattr(urllib.request, "urlopen", offline)
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    lab = engine._learning_lab_resources
    learning = engine._learning_resources
    try:
        assert lab.projects.store is None and not lab.busy
        projects.draft["name"] = "Kullanıcı kaydedilmemiş taslak"
        before = copy.deepcopy(projects.draft)
        commit = projects.store.commit_id
        fingerprints = {
            str(p.relative_to(projects.store.root)): file_hash(p)
            for p in Path(projects.store.root).rglob("*")
            if p.is_file()
        }
        window.setProperty("selectedSection", 7)
        engine._workspace_resources.activate("learn.lab.mean-median")
        example = window.findChild(QObject, "learningLabWindow")
        spin(app, lambda: example.isVisible() and lab.projects.store is not None)
        assert lab.projects.store.root != projects.store.root
        for lesson in KERNELS:
            learning.openLesson(lesson)
            assert not lab.busy
            slider = example.findChild(QObject, "lessonSlider")
            slider.setProperty("value", learning.lesson["control"]["default"])
            example.findChild(QObject, "lessonCalculate").clicked.emit()
            spin(app, lambda: not lab.busy, timeout=60000)
            assert not lab.errorText, lab.errorText
            assert lab.result["spec"]["lesson"] == lesson
            assert (
                lab.result["metrics"] and lab.projects.draft == lab.projects.store.state
            )
            assert projects.draft == before and projects.store.commit_id == commit
            if CAPTURE:
                CAPTURE(app, example, projects, lab, lesson)
        # Changing a slider marks the old result stale and does not auto-compute.
        before_lab_commit = lab.projects.store.commit_id
        slider.setProperty("value", 0)
        app.processEvents()
        assert lab.projects.store.commit_id == before_lab_commit
        assert "önceki ayara" in example.findChild(QObject, "lessonStale").property(
            "text"
        )
        learning.answerLesson(1)
        assert "Tekrar düşün" in learning.lessonFeedback
        learning.setMarksEnabled(True)
        learning.completeLesson()
        assert learning.lessonCompleted
        learning.toggleBookmark()
        learning.setMarksEnabled(False)
        assert not learning.lessonCompleted
        assert projects.draft == before
        # Actual saved result reopens from same isolated ProjectStore.
        last = lab.saved[-1]["id"]
        lab.openReport(last)
        assert not lab.errorText
        example.findChild(QObject, "lessonCalculate").clicked.emit()
        lab.cancel()
        spin(app, lambda: not lab.busy, timeout=60000)
        assert (
            lab.projects.store.commit_id == before_lab_commit
            and "iptal" in lab.errorText
        )
        example.findChild(QObject, "lessonClose").clicked.emit()
        assert not example.isVisible()
        # Closing reading does not gate a real data-import workflow.
        source = tmp_path / "own.csv"
        source.write_text("x\n1\n2\n3\n")
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        assert imports.ready and not projects.readOnly
        assert projects.draft == before
        assert fingerprints == {
            str(p.relative_to(projects.store.root)): file_hash(p)
            for p in Path(projects.store.root).rglob("*")
            if p.is_file()
        }
        isolated = Path(lab.projects.store.root)
    finally:
        teardown(app, window)
    assert not isolated.exists()
