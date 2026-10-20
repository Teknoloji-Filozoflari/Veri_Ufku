"""Actual QML, bounded spawn, human confirmation, export, retention and reopen."""

import json

import polars as pl
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_dataset import prepare
from test_import_gui import setup, spin, teardown
from test_privacy import orphan

CAPTURE = None


def test_real_privacy_gui(tmp_path, monkeypatch):
    build = tmp_path / "build"
    build.mkdir()
    store, ref, work = prepare(
        build,
        pl.DataFrame({"mail": ["a@example.org", "b@example.org"], "age": [20, 40]}),
    )
    root = str(store.root)
    store.close()
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    c = engine._privacy_resources

    def item(name):
        obj = window.findChild(QObject, name)
        assert obj is not None, name
        return obj

    def wait():
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText

    try:
        assert projects.closeProject(True) and projects.open(root)
        before = projects.store.commit_id
        engine._workspace_resources.activate("privacy.scan")
        spin(app, lambda: item("privacyExpanded").property("checked"))
        assert projects.store.commit_id == before and not c.busy
        item("privacyScan").clicked.emit()
        wait()
        assert c._scan["rows_scanned"] == 2
        p = json.loads(c.template())
        item("privacyPolicy").setProperty("text", json.dumps(p))
        # Missing explicit consent does not save a policy.
        c.savePolicy(json.dumps(p), False)
        assert c.errorText and not c.saved
        item("privacyHuman").setProperty("checked", True)
        item("privacySave").clicked.emit()
        wait()
        assert len(c.saved) == 1
        rid = c.saved[0]["id"]
        item("privacyPreview").clicked.emit()
        wait()
        assert c._preview["review_id"] == rid
        out = tmp_path / "redacted.zip"
        item("privacyDestination").setProperty("text", str(out))
        item("privacyApproved").setProperty("checked", True)
        item("privacyExport").clicked.emit()
        wait()
        assert out.exists() and c.result["status"] == "published"
        assert "a@example.org" not in c.outputText
        item("privacyRetention").clicked.emit()
        wait()
        assert projects.draft["results"][-1]["privacy_event"]["kind"] == "retention"
        old_scratch = orphan(c.cache)
        item("privacyCleanupPreview").clicked.emit()
        wait()
        assert len(c._cleanup["candidates"]) == 1
        item("privacyCleanupConfirmed").setProperty("checked", True)
        item("privacyCleanup").clicked.emit()
        wait()
        assert c.result["removed"] == [old_scratch.name] and not old_scratch.exists()
        assert projects.draft["results"][-1]["privacy_event"]["kind"] == "cleanup"
        assert (build / "source.parquet").exists()
        # Explicit key action: no session service / no mock backend success claim.
        item("privacyKeyRef").setProperty("text", "missing-phase72")
        item("privacySealed").setProperty("text", str(tmp_path / "not-there.vupseal"))
        item("privacyInspect").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert c.errorText
        item("privacyHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert engine._learning_resources.article["id"] == "privacy-governance"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        if CAPTURE:
            CAPTURE(app, window, projects, c, out)
        # Actual worker cancellation preserves existing events.
        before = len(projects.draft["results"])
        c.scan(ref["version_id"])
        c.cancel()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert len(projects.draft["results"]) == before
        assert projects.closeProject(True) and projects.open(root)
        assert c.saved[0]["id"] == rid
        assert len(projects.draft["results"]) == before
    finally:
        teardown(app, window)
