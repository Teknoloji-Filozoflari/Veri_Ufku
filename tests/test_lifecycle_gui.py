"""Real QML/spawn model selection, package open/save, preview and safe prediction."""

import os

import polars as pl
from PySide6.QtCore import QObject, QUrl
from test_import_gui import spin, teardown
from test_validation_gui import imported


def test_qml_pipeline_package_roundtrip_new_data_no_overwrite_help(
    tmp_path, monkeypatch
):
    app, window, projects, p, c, source = imported(tmp_path, monkeypatch)
    before = source.read_bytes()
    engine = app._veri_ufku_resources[0]
    lifecycle = engine._lifecycle_resources
    try:
        window.findChild(QObject, "validationRun").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        record = next(r for r in projects.draft["results"] if "baseline" in r)
        assert record["baseline"]["model_package_uri"]
        panel = window.findChild(QObject, "lifecyclePanel")
        assert panel is not None and panel.property("visible")
        window.findChild(QObject, "lifecycleOpenSaved").clicked.emit()
        spin(app, lambda: not lifecycle.busy)
        assert not lifecycle.errorText, lifecycle.errorText
        assert lifecycle.card["estimator"] == "DummyRegressor"
        assert lifecycle.result["worker_pid"] != os.getpid()
        model_file = tmp_path / "Türkçe model #1.vumodel"
        url = QUrl.fromLocalFile(str(model_file)).toString()
        lifecycle.savePackage(url)
        spin(app, lambda: not lifecycle.busy)
        assert not lifecycle.errorText and model_file.is_file(), lifecycle.errorText
        lifecycle.openPackage(url)
        spin(app, lambda: not lifecycle.busy)
        assert not lifecycle.errorText, lifecycle.errorText
        # Imported new file: reordered fields and duplicate content, fresh source/RowIds.
        imports = engine._imports_resources
        new_file = tmp_path / "new.parquet"
        original = pl.read_parquet(source)
        new = pl.concat([original.head(3), original.head(3)]).select(
            "cat", "y", "x", "group", "when"
        )
        new.write_parquet(new_file)
        imports.choose(str(new_file))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        data = engine._dataset_resources
        data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
        spin(app, lambda: not data.busy)
        assert (
            window.findChild(QObject, "lifecycleDataset").property("currentValue")
            == data.selectedDataset
        )
        lifecycle.previewData("reject", 2)
        spin(app, lambda: not lifecycle.busy)
        assert not lifecycle.errorText, lifecycle.errorText
        assert (
            not lifecycle.previewReport["blockers"]
            and lifecycle.previewReport["rows"] == 6
        )
        output = tmp_path / "tahmin.parquet"
        lifecycle.predictData(QUrl.fromLocalFile(str(output)).toString(), "reject", 2)
        spin(app, lambda: not lifecycle.busy)
        assert not lifecycle.errorText, lifecycle.errorText
        result = pl.read_parquet(output)
        data = engine._dataset_resources
        d = data.dataset()
        snapshot = pl.read_parquet(projects.store.path(d["snapshot_uri"]))
        assert result.select(snapshot.columns).equals(snapshot)
        assert result["__vu_row_id"].n_unique() == 6
        assert lifecycle.outputReport["details"]["fit_calls"] == 0
        assert source.read_bytes() == before and pl.read_parquet(new_file).equals(new)
        for context in (
            "model.card",
            "model.importance",
            "model.unknown-category",
            "model.new-data",
            "model.uncertainty",
        ):
            engine._learning_resources.openContext(context)
            assert engine._learning_resources.article["id"].startswith("model-")
        lifecycle.previewData("reject", 2)
        spin(app, lambda: not lifecycle.busy)
        lifecycle.predictData(QUrl.fromLocalFile(str(output)).toString(), "reject", 2)
        spin(app, lambda: not lifecycle.busy)
        assert lifecycle.errorText and output.is_file()
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        lifecycle.selectModel(record["id"])
        spin(app, lambda: not lifecycle.busy)
        assert not lifecycle.errorText, lifecycle.errorText
        assert lifecycle.card["label_order"] == []
        # Resetting one explicit feature keeps the other mapping and the UI in sync.
        ids = [f["id"] for f in lifecycle.card["features"]]
        lifecycle.mapFeature(ids[0], "col:first")
        lifecycle.mapFeature(ids[1], "col:second")
        lifecycle.mapFeature(ids[0], "")
        assert lifecycle.featureMapping == {ids[1]: "col:second"}
        lifecycle.resetMapping()
        lifecycle.previewData("reject", 2)
        spin(app, lambda: not lifecycle.busy)
        lifecycle.invalidate()
        blocked = tmp_path / "stale.parquet"
        lifecycle.predictData(QUrl.fromLocalFile(str(blocked)).toString(), "reject", 2)
        assert lifecycle.errorText and not blocked.exists()
        lifecycle.previewData("reject", 2)
        lifecycle.cancel()
        spin(app, lambda: not lifecycle.busy)
        assert "İptal" in lifecycle.message and not lifecycle.current
    finally:
        teardown(app, window)
