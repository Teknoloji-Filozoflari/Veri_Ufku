"""Real QML local replay and separate target recipes, no network action."""

import json
import os
import threading

import polars as pl
import pytest
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown

CAPTURE = None


def imported(tmp_path, monkeypatch, task=None):
    n = 40
    frame = pl.DataFrame(
        dict(
            id=list(range(n)),
            event=[float(i) for i in range(n)],
            processing=[float(i) for i in range(n)],
            feedback=[float(i) for i in range(n)],
            x=[float(i) for i in range(n)],
            y=[0] * 20 + [1] * 20,
            y2=[1] * 20 + [0] * 20,
            role=["train"] * 16 + ["eval"] * 4 + ["train"] * 16 + ["eval"] * 4,
            ordinal=["low"] * 20 + ["high"] * 20,
        )
    )
    source = tmp_path / "stream.parquet"
    frame.write_parquet(source)
    # Explicit test environment: total parent+worker4GiB. Production2GiB unchanged.
    config = tmp_path / "config" / "veri_ufku"
    config.mkdir(parents=True)
    (config / "settings.json").write_text(
        json.dumps({"budget": {"ram_bytes": 4 * 1024**3}})
    )
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    controller = engine._stream_resources
    window.setProperty("selectedSection", 5)
    window.findChild(QObject, "streamExpanded").setProperty("checked", True)
    imports.choose(str(source))
    spin(app, lambda: not imports.busy and not projects.busy)
    assert imports.ready, imports.errorText
    imports.importData(True)
    spin(app, lambda: not imports.busy and not projects.busy)
    assert not imports.errorText, imports.errorText
    spin(app, lambda: not controller.data.busy)
    controller.data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
    spin(app, lambda: not controller.data.busy)
    cols = controller.column_rows()
    for role, name in [
        ("EventID", "id"),
        ("EventTime", "event"),
        ("ProcessingTime", "processing"),
        ("FeedbackTime", "feedback"),
        ("Target", "ordinal" if task == "ordinal" else "y"),
        ("Feature", "x"),
    ]:
        window.findChild(QObject, "stream" + role).setProperty(
            "currentIndex", next(i for i, c in enumerate(cols) if c["name"] == name)
        )
    if task:
        window.findChild(QObject, "specialTask").setProperty(
            "currentIndex",
            ["multilabel", "multioutput", "ordinal", "semisupervised"].index(
                "semisupervised" if task == "transductive" else task
            ),
        )
        for obj, name in (("specialRole", "role"), ("specialTarget2", "y2")):
            window.findChild(QObject, obj).setProperty(
                "currentIndex", next(i for i, c in enumerate(cols) if c["name"] == name)
            )
    if task == "transductive":
        window.findChild(QObject, "specialTransductive").setProperty("checked", True)
    spin(app, lambda: controller.canStreamRun)
    return app, window, projects, controller, source


@pytest.mark.parametrize(
    "task",
    [None, "multilabel", "multioutput", "ordinal", "semisupervised", "transductive"],
)
def test_real_replay_and_special_targets(tmp_path, monkeypatch, task):
    app, window, projects, c, source = imported(tmp_path, monkeypatch, task)
    before = source.read_bytes()
    try:
        window.findChild(QObject, "streamHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert (
            app._veri_ufku_resources[0]._learning_resources.article["id"]
            == "stream-window"
        )
        window.setProperty("infoOpen", False)
        window.findChild(QObject, "specialRun" if task else "streamRun").clicked.emit()
        spin(app, lambda: not c.busy, timeout=90000)
        assert not c.errorText, c.errorText
        assert c.active["status"] == "completed", c.active["warnings"]
        assert c.active["worker_pid"] != os.getpid()
        if task:
            assert c.active["metrics"]
            assert len(c.active["analysis"]["predictions"]) == 8
            assert "DEVELOPMENT" in window.findChild(
                QObject, "specialSummary"
            ).property("text")
        else:
            assert (
                c.active["state"]["trained"] == 40 and c.active["state"]["scored"] == 39
            )
        if task == "transductive":
            assert "transductive" in c.active["analysis"]["fit_scope"]
        if CAPTURE:
            CAPTURE(app, window, projects, c, task or "replay")
        saved = next(r for r in reversed(c.saved()) if "completed" in r["label"])
        c.active = None
        c.openRun(saved["id"])
        assert c.active["status"] == "completed" and source.read_bytes() == before
    finally:
        teardown(app, window)


def test_live_cancel_and_explicit_resume(tmp_path, monkeypatch):
    app, window, projects, c, source = imported(tmp_path, monkeypatch)
    # Hold a real parent publication while the spawned worker waits for ACK.
    # This is a controlled I/O boundary, not a claim of naturally slow computation.
    import veri_ufku.ui.neural as lifecycle

    real_publish = lifecycle.publish
    gate = threading.Event()

    def held_publish(store, state, data):
        if (
            data.get("schema") == "StreamRun/v1"
            and data["status"] == "running"
            and data["state"]["cursor"] == 16
        ):
            if not gate.wait(20):
                raise AssertionError("Controlled publication gate timed out")
        return real_publish(store, state, data)

    monkeypatch.setattr(lifecycle, "publish", held_publish)
    try:
        spin(
            app,
            lambda: (
                c.canStreamRun
                and not projects.busy
                and window.findChild(QObject, "streamRun").property("enabled")
            ),
        )
        window.findChild(QObject, "streamRun").clicked.emit()
        assert c.busy, c.errorText
        spin(
            app,
            lambda: (
                not c.busy
                or (c.stage == "checkpoint" and c._incoming["state"]["cursor"] >= 16)
            ),
            timeout=90000,
        )
        assert c.busy, (c.errorText, c.message, c.stage)
        window.findChild(QObject, "streamCancel").clicked.emit()
        gate.set()
        spin(app, lambda: not c.busy, timeout=90000)
        assert c.active["status"] == "canceled", c.errorText
        cursor = c.active["state"]["cursor"]
        prior = c.active["run_id"]
        assert 16 <= cursor < 40
        spin(app, lambda: c.canStreamRun)
        window.findChild(QObject, "streamResume").clicked.emit()
        spin(app, lambda: not c.busy, timeout=90000)
        assert not c.errorText, c.errorText
        assert c.active["status"] == "completed" and c.active["resume_from"] == prior
        assert c.active["state"]["trained"] == 40 and c.active["state"]["scored"] == 39
        if CAPTURE:
            CAPTURE(app, window, projects, c, "cancel-resume")
    finally:
        gate.set()
        teardown(app, window)
