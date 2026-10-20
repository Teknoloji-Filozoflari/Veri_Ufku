"""Actual environment panel metadata/export/import/cache/update-plan/help/cancel."""

import hashlib

from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown

CAPTURE = None


def test_real_environment_gui(tmp_path, monkeypatch):
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    c = engine._environment_resources

    def item(name):
        v = window.findChild(QObject, name)
        assert v is not None, name
        return v

    def wait():
        spin(app, lambda: not c.busy, timeout=60000)
        assert not c.errorText, c.errorText

    window.findChild(QObject, "advancedButton").clicked.emit()
    try:
        before = projects.store.commit_id
        engine._workspace_resources.activate("environment.inspect")
        spin(app, lambda: item("environmentExpanded").property("checked"))
        assert not c.inventory and not c.busy
        item("environmentRefresh").clicked.emit()
        wait()
        assert (
            c.inventory["groups"]["core"]["status"]
            == "versions-match-not-runtime-validation"
        )
        profile = tmp_path / "profile.json"
        item("environmentProfilePath").setProperty("text", str(profile))
        c.exportProfile(str(profile), False)
        assert c.errorText and not profile.exists()
        item("environmentApproved").setProperty("checked", True)
        item("environmentExport").clicked.emit()
        wait()
        assert profile.exists()
        item("environmentImport").clicked.emit()
        wait()
        assert c.result["action"] == "import-review" and c.result["lock_match"]
        model = tmp_path / "model"
        model.mkdir()
        (model / "weights.bin").write_bytes(b"synthetic weights, not executable")
        item("environmentCachePath").setProperty("text", str(model))
        item("environmentCache").clicked.emit()
        wait()
        assert (
            c.result["action"] == "model-cache-inspection"
            and len(c.result["files"]) == 1
        )
        bundle = tmp_path / "candidate.flatpak"
        bundle.write_bytes(b"synthetic integrity planner only")
        item("environmentUpdatePath").setProperty("text", str(bundle))
        item("environmentUpdateHash").setProperty(
            "text", hashlib.sha256(bundle.read_bytes()).hexdigest()
        )
        item("environmentCurrentCommit").setProperty("text", "a" * 64)
        item("environmentUpdatePlan").clicked.emit()
        wait()
        assert (
            c.result["schema"] == "UpdatePlan/v1"
            and "NOT undo" in c.result["rollback"]["project"]
        )
        assert projects.store.commit_id == before
        item("environmentHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert engine._learning_resources.article["id"] == "environment-distribution"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        if CAPTURE:
            CAPTURE(app, window, projects, c, profile)
        c.refresh()
        c.cancel()
        spin(app, lambda: not c.busy, timeout=60000)
        assert c.inventory and projects.store.commit_id == before
    finally:
        teardown(app, window)
