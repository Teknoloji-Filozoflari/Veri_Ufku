"""Actual offline desktop preview/export/open/diff/review/fork workflow."""

import json

import polars as pl
import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_dataset import column, prepare
from test_import_gui import setup, spin, teardown

CAPTURE = None


@pytest.mark.parametrize("full", [False, True])
def test_real_sharing_gui(tmp_path, monkeypatch, full):
    build = tmp_path / "build"
    build.mkdir()
    store, r, work = prepare(
        build, pl.DataFrame({"x": [1.0, 2.0, 3.0], "label": ["Çağrı", "Işıl", "Oya"]})
    )
    target = str(store.root)
    store.close()
    if full:
        config = tmp_path / "config/veri_ufku"
        config.mkdir(parents=True)
        (config / "settings.json").write_text(
            json.dumps({"budget": {"ram_bytes": 4 * 1024**3}})
        )
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    c = engine._sharing_resources
    try:
        assert projects.closeProject(True) and projects.open(target)
        before = projects.store.commit_id
        engine._workspace_resources.activate("share.bundle")
        spin(
            app,
            lambda: window.findChild(QObject, "sharingExpanded").property("checked"),
        )
        assert not c.busy and projects.store.commit_id == before
        editor = window.findChild(QObject, "sharingRecipe")
        paths = []
        for mode in (
            ("metadata-only", "redacted-sample", "full-copy")
            if full
            else ("metadata-only", "redacted-sample")
        ):
            spec = json.loads(c.template(mode))
            spec["rows"] = 2
            if mode == "redacted-sample":
                spec["keep_numeric"] = [column(r, "x")]
            editor.setProperty("text", json.dumps(spec, ensure_ascii=False, indent=2))
            window.findChild(QObject, "sharingPreview").clicked.emit()
            spin(app, lambda: not c.busy, timeout=60000)
            assert not c.errorText, (
                c.errorText + " resource=" + str(engine._resource_supervisor.report)
            )
            assert c._preview["mode"] == mode and not c._preview["blocked"]
            path = tmp_path / (mode + ".vushare")
            paths.append(path)
            window.findChild(QObject, "sharingDestination").setProperty(
                "text", str(path)
            )
            window.findChild(QObject, "sharingReviewed").setProperty("checked", True)
            window.findChild(QObject, "sharingExport").clicked.emit()
            spin(app, lambda: not c.busy, timeout=60000)
            assert not c.errorText, (
                c.errorText + " resource=" + str(engine._resource_supervisor.report)
            )
            assert path.exists() and projects.store.commit_id == before
            window.findChild(QObject, "sharingArchive").setProperty("text", str(path))
            window.findChild(QObject, "sharingOpen").clicked.emit()
            spin(app, lambda: not c.busy, timeout=60000)
            assert not c.errorText and c._opened["manifest"]["mode"] == mode, (
                c.errorText
            )
            assert (
                c._opened["projection"]["origin"]["project_id"]
                == projects.store.manifest["project_id"]
            )
            if mode == "redacted-sample":
                assert c._opened["sample_preview"][0]["column-2"] == "[redacted]"
        # Persist review of the opened, original artifact context.
        combo = window.findChild(QObject, "sharingTarget")
        combo.setProperty(
            "currentIndex",
            next(
                i
                for i, v in enumerate(c.reviewTargets)
                if v["id"].startswith("dataset:")
            ),
        )
        window.findChild(QObject, "sharingNote").setProperty(
            "text", "Birim ve kaynak kapsamı incelendi."
        )
        window.findChild(QObject, "sharingSaveReview").clicked.emit()
        spin(app, lambda: not c.busy, timeout=60000)
        assert not c.errorText, (
            c.errorText + " resource=" + str(engine._resource_supervisor.report)
        )
        assert (
            len(c.saved) == 1
            and c.saved[0]["event"]["subject"]["entity"]["id"] == r["version_id"]
        )
        note = c.saved[0]["event"].copy()
        fork = tmp_path / "incoming-fork"
        if full:
            window.findChild(QObject, "sharingRestorePath").setProperty(
                "text", str(fork)
            )
            window.findChild(QObject, "sharingReviewed").setProperty("checked", True)
            window.findChild(QObject, "sharingRestore").clicked.emit()
            spin(app, lambda: not c.busy, timeout=60000)
            assert not c.errorText, c.errorText
            assert (fork / "ACTIVE").exists() and str(projects.store.root) == target
        window.findChild(QObject, "sharingRight").setProperty("text", str(paths[0]))
        window.findChild(QObject, "sharingDiff").clicked.emit()
        spin(app, lambda: not c.busy, timeout=60000)
        assert not c.errorText, (
            c.errorText + " resource=" + str(engine._resource_supervisor.report)
        )
        assert c.result["action"] == "diff" and c.result["same_origin"]
        assert all(not v for v in c.result["categories"].values())
        if CAPTURE:
            CAPTURE(app, window, projects, c, paths, fork)
        # Explicit cancellation leaves the previous report and committed notes intact.
        previous = projects.store.commit_id
        window.findChild(QObject, "sharingPreview").clicked.emit()
        window.findChild(QObject, "sharingCancel").clicked.emit()
        spin(app, lambda: not c.busy, timeout=60000)
        assert projects.store.commit_id == previous and "iptal" in c.errorText
        assert projects.closeProject(True), projects.errorText
        assert projects.open(target), projects.errorText
        assert c.saved[0]["event"] == note
        button = window.findChild(QObject, "sharingHelp")
        button.forceActiveFocus()
        button.clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert engine._learning_resources.article["id"] == "review-sharing"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
    finally:
        teardown(app, window)
