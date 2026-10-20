"""Real QML mapping/dry-run/apply and full change report through CPU spawn."""

import copy
import os

import polars as pl
from PySide6.QtCore import QObject, QUrl
from test_dataset_gui import load
from test_import_gui import spin, teardown
from test_learning_gui import visual_item


def test_qml_new_dataset_recipe_atomic_apply_and_drift(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    ops, c, imports = (
        engine._operations_resources,
        engine._recipe_resources,
        engine._imports_resources,
    )
    original = source.read_bytes()
    try:
        base = data.dataset()["version_id"]
        col = data.dataset()["import_metadata"]["columns"][0]["id"]
        ops.previewOperation("rename", col, "renamed")
        spin(app, lambda: not ops.busy)
        ops.apply()
        spin(app, lambda: not ops.busy)
        assert not ops.errorText, ops.errorText
        version = data.dataset()["version_id"]
        window.setProperty("selectedSection", 2)
        c.selectRecipe(version)
        assert c.recipeSources
        file = tmp_path / "flow.json"
        c.saveRecipe(QUrl.fromLocalFile(str(file)).toString())
        assert file.exists(), c.errorText
        c.openRecipe(QUrl.fromLocalFile(str(file)).toString())
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.setType(1, "int64")
        imports.refreshPreview()
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        new = projects.draft["datasets"][-1]
        data.selectDataset(new["dataset_id"])
        spin(app, lambda: not data.busy)
        c.mapSource(base, new["version_id"])
        before = copy.deepcopy(projects.draft)
        window.findChild(QObject, "recipeDryRun").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText and c.canApply, (
            c.errorText,
            c.result,
            c.result_binding,
            c.current_binding(),
        )
        assert c.result["worker_pid"] != os.getpid()
        assert projects.draft == before
        assert c.steps[0]["impact"]["after_rows"] == 450
        app.processEvents()
        for column_id, target in c.mappings[base].items():
            assert (
                visual_item(window.contentItem(), "recipeMap_" + column_id).property(
                    "currentValue"
                )
                == target
            )
        window.findChild(QObject, "recipeApply").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        applied = projects.draft["datasets"][-1]
        frame = pl.read_parquet(projects.store.path(applied["snapshot_uri"]))
        assert frame.columns[0] == "renamed"
        assert len(projects.draft["datasets"]) == len(before["datasets"]) + 1
        c.compareData(base, new["version_id"])
        spin(app, lambda: not c.busy)
        assert c.changeReport["metrics"] is None and c.changeReport["scope"] == "full"
        assert c.changeReport["old_version"] == base
        output = tmp_path / "change.json"
        c.saveReport(QUrl.fromLocalFile(str(output)).toString())
        assert output.exists(), c.errorText
        root = str(projects.store.root)
        assert projects.closeProject() and projects.open(root)
        assert source.read_bytes() == original
        window.findChild(QObject, "lifecycleRetrain").clicked.emit()
        assert engine._preparation_resources.source_version == ""
        assert not engine._preparation_resources.busy
        c.dryRun()
        c.cancel()
        spin(app, lambda: not c.busy)
        assert source.read_bytes() == original
    finally:
        teardown(app, window)
