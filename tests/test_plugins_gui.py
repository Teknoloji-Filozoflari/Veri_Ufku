"""Actual QML manifest→trust→worker→result/help/save; missing/crashed code isolation."""

import hashlib
import json
import shutil

import polars as pl
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_dataset import column, prepare
from test_import_gui import setup, spin, teardown
from test_plugins import package

CAPTURE = None


def test_real_plugin_gui(tmp_path, monkeypatch):
    plugin = package(tmp_path)
    build = tmp_path / "build"
    build.mkdir()
    store, ref, work = prepare(build, pl.DataFrame({"amount": [1.0, 2.0, 3.0, None]}))
    root = str(store.root)
    store.close()
    # An arbitrary plugin-like folder is present during startup; discovery must not execute it.
    ignored = tmp_path / "config/veri_ufku/plugins/ignored"
    ignored.mkdir(parents=True)
    sentinel = tmp_path / "AUTO_EXECUTED"
    (ignored / "plugin.py").write_text(
        "from pathlib import Path\nPath(" + repr(str(sentinel)) + ').write_text("bad")'
    )
    ignored_manifest = json.loads((plugin / "manifest.json").read_text())
    ignored_manifest["id"] = "ignored-valid-manifest"
    ignored_manifest["code_sha256"] = hashlib.sha256(
        (ignored / "plugin.py").read_bytes()
    ).hexdigest()
    (ignored / "manifest.json").write_text(json.dumps(ignored_manifest))
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    c = engine._plugin_resources

    def item(name):
        v = window.findChild(QObject, name)
        assert v is not None, name
        return v

    def wait():
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)

    try:
        assert projects.closeProject(True) and projects.open(root)
        before = projects.store.commit_id
        assert not sentinel.exists()
        engine._workspace_resources.activate("plugin.sdk")
        spin(app, lambda: item("pluginsExpanded").property("checked"))
        item("pluginsManifest").setProperty("text", str(plugin / "manifest.json"))
        item("pluginsInspect").clicked.emit()
        assert not c.errorText and c._inspection["compatible"]
        assert projects.store.commit_id == before and not c.busy
        item("pluginsTemplate").clicked.emit()
        p = json.loads(item("pluginsRecipe").property("text"))
        p["columns"] = [column(ref, "amount")]
        item("pluginsRecipe").setProperty("text", json.dumps(p))
        c.execute(json.dumps(p), False, False)
        assert c.errorText and not projects.draft["results"]
        item("pluginsTrusted").setProperty("checked", True)
        item("pluginsRun").clicked.emit()
        wait()
        assert not c.errorText, c.errorText
        assert c.result["output"]["data"]["metrics"] == dict(mean=2.0, n=3)
        assert len(c.saved) == 1 and "example-mean-help" in c.pluginHelp
        record = projects.draft["results"][-1]
        rid = record["id"]
        prior = projects.store.commit_id
        item("pluginsHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert engine._learning_resources.article["id"] == "plugins-sdk"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        # Crash in a separately selected, trusted plugin cannot publish a successful result.
        m = json.loads((plugin / "manifest.json").read_text())
        m["id"] = "example-crash"
        (plugin / "plugin.py").write_text("import os\nos._exit(17)\n")
        m["code_sha256"] = hashlib.sha256(
            (plugin / "plugin.py").read_bytes()
        ).hexdigest()
        (plugin / "manifest.json").write_text(json.dumps(m))
        item("pluginsInspect").clicked.emit()
        assert not c.errorText
        item("pluginsTrusted").setProperty("checked", True)
        item("pluginsRun").clicked.emit()
        wait()
        assert c.errorText and projects.store.commit_id == prior and len(c.saved) == 1
        # Incompatible API rejected by manifest only.
        m["api_version"] = 2
        (plugin / "manifest.json").write_text(json.dumps(m))
        item("pluginsInspect").clicked.emit()
        assert "API" in c.errorText and not c.busy
        shutil.rmtree(plugin)
        assert projects.closeProject(True) and projects.open(root)
        assert not c._inspection and c.saved[0]["id"] == rid and not sentinel.exists()
        item("pluginsOpen").clicked.emit()
        assert not c.errorText, c.errorText
        assert (
            c.result["output"]["data"]["metrics"]["mean"] == 2.0
            and "example-mean-help" in c.pluginHelp
        )
        if CAPTURE:
            CAPTURE(app, window, projects, c)
    finally:
        teardown(app, window)
