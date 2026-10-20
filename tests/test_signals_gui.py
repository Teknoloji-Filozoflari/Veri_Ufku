"""Real QML signal operations, source protection, spawn/cancel and safe artifact reopen."""

import json
import os

import pytest
from PySide6.QtCore import QMetaObject, QObject
from test_import_gui import setup, spin, teardown
from test_signals import example

from veri_ufku.modeling.signal_contracts import METHODS
from veri_ufku.modeling.signals import token

CAPTURE = None


@pytest.mark.parametrize("method", METHODS)
def test_real_signal_gui(tmp_path, monkeypatch, method):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    c = engine._time_series_resources
    source = tmp_path / "signal.parquet"
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
        columns = data.dataset()["import_metadata"]["columns"]
        ids = {c["name"]: c["id"] for c in columns}
        for name, col in [
            ("timeSeriesDate", "t"),
            ("timeSeriesMeasurement", "voltage"),
            ("timeSeriesGroup", "recording"),
        ]:
            choice = window.findChild(QObject, name)
            choice.setProperty(
                "currentIndex",
                next(i for i, colinfo in enumerate(columns) if colinfo["name"] == col)
                + (1 if name == "timeSeriesGroup" else 0),
            )
        engine._workspace_resources.activate("model.signal." + method)
        app.processEvents()
        assert window.findChild(QObject, "signalEnabled").property("checked")
        window.findChild(QObject, "signalChannels").setProperty(
            "text", json.dumps([ids["voltage"], ids["current"]])
        )
        window.findChild(QObject, "signalChannelUnits").setProperty(
            "text", json.dumps({ids["voltage"]: "V", ids["current"]: "A"})
        )
        window.findChild(QObject, "signalEvent").setProperty(
            "currentIndex",
            next(i for i, col in enumerate(columns) if col["name"] == "event") + 1,
        )
        if method == "classification":
            window.findChild(QObject, "signalLabel").setProperty(
                "currentIndex",
                next(i for i, col in enumerate(columns) if col["name"] == "label") + 1,
            )
            window.findChild(QObject, "signalBlocks").setProperty(
                "text", json.dumps([ids[x] for x in ["subject", "device", "session"]])
            )
            window.findChild(QObject, "signalTrain").setProperty(
                "text", json.dumps([token("r0"), token("r1")])
            )
            window.findChild(QObject, "signalValidation").setProperty(
                "text", json.dumps([token("r2"), token("r3")])
            )
        button = window.findChild(QObject, "signalRun")
        assert button.property("enabled")
        button.clicked.emit()
        spin(app, lambda: not c.busy, timeout=90000)
        assert not c.errorText, c.errorText
        assert c.result and c.result["worker_pid"] != os.getpid()
        a = c.result["advanced"]
        assert a["schema"] == "SignalRun/v1" and len(a["recordings"]) == 4
        assert (
            a["spec"]["operation"] == method
            and a["provenance"]["capability_id"] == "model.signal." + method
        )
        assert source.read_bytes() == before
        spec = a["spec"]
        if method == "zero-phase":
            assert spec["zero_phase"] and spec["mode"] == "offline"
        if method == "classification":
            assert a["classifier"]["accuracy"] == 1
        # Native help, not a link to an external website.
        window.findChild(QObject, "signalHelp").clicked.emit()
        app.processEvents()
        learning = engine._learning_resources
        assert learning.article["id"] == "signal-sampling"
        assert QMetaObject.invokeMethod(window, "closeInformation")
        app.processEvents()
        if CAPTURE:
            CAPTURE(app, window, projects, c, method)
        record = c.record_id
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        c.openSaved(record)
        spin(app, lambda: not c.busy, timeout=90000)
        assert not c.errorText, c.errorText
        assert c.result["advanced"]["recordings"] == a["recordings"]
        assert window.findChild(QObject, "signalEnabled").property("checked")
        if method == "spectrogram":
            saved = [r["id"] for r in projects.draft["results"]]
            button.clicked.emit()
            assert c.busy and c.process.pid
            window.findChild(QObject, "timeSeriesCancel").clicked.emit()
            spin(app, lambda: not c.busy, timeout=90000)
            assert [r["id"] for r in projects.draft["results"]] == saved
            assert source.read_bytes() == before
    finally:
        teardown(app, window)
