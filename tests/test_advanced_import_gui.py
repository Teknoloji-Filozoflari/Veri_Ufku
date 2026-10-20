"""Actual QML/spawn import routes, explicit choices and source/cancel failures."""

import hashlib
import json
import time

import polars as pl
import pytest
from phase30_fixtures import fixture
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown

from veri_ufku.importers.advanced import ADVANCED_FORMATS


@pytest.mark.parametrize("adapter", ADVANCED_FORMATS)
def test_gui_format_selection_worker_save_reopen(tmp_path, monkeypatch, adapter):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = fixture(tmp_path, adapter)
    before = (
        hashlib.sha256(source.read_bytes()).hexdigest() if source.is_file() else None
    )
    try:
        window.setProperty("selectedSection", 1)
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        assert imports.formatId == adapter
        if adapter == "hdf5":
            assert not imports.ready and not imports.settings["sheet"]
            assert "/tables/observations" in imports.choices["sheets"]
            imports.setOption("sheet", "/tables/observations")
        elif adapter == "xml":
            assert not imports.ready
            imports.setOption("record_path", "/root/record")
        elif adapter == "fixed_width":
            imports.setOption("widths", "3,7")
            imports.setOption("column_names", "code|name")
        if adapter in ("hdf5", "xml", "fixed_width"):
            imports.refreshPreview()
            spin(app, lambda: not imports.busy)
        assert imports.ready, imports.errorText
        assert imports.model.rowCount() <= 20
        assert json.loads(imports.formatMetadata)["parts"]
        window.findChild(QObject, "importAdvancedButton").clicked.emit()
        app.processEvents()
        if adapter == "xml":
            assert window.findChild(QObject, "xmlRecordPath").property("visible")
        if adapter == "hdf5":
            assert window.findChild(QObject, "hdfKey").property("visible")
        window.findChild(QObject, "importCsvButton").clicked.emit()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        dataset = projects.draft["datasets"][-1]
        metadata = dataset["import_metadata"]["settings"]["format_metadata"]
        assert metadata["parts"]
        frame = pl.read_parquet(projects.store.path(dataset["snapshot_uri"]))
        assert frame.height > 0
        assert projects.closeProject() and projects.open(str(tmp_path / "project"))
        assert (
            projects.draft["datasets"][-1]["import_metadata"]["settings"][
                "format_metadata"
            ]
            == metadata
        )
        if before:
            assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    finally:
        teardown(app, window)


def test_gui_large_preview_cancel_and_changed_source(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "large.xml"
    source.write_text("<root>" + "<record><x>001</x></record>" * 100000 + "</root>")
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.setOption("record_path", "/root/record")
        imports.refreshPreview()
        spin(app, lambda: not imports.busy)
        assert imports.ready and imports.result["examined"] == 200
        before = projects.store.commit_id
        imports.importData()
        spin(app, lambda: imports.busy)
        started = time.monotonic()
        imports.cancel()
        spin(app, lambda: not imports.busy)
        assert time.monotonic() - started < imports.budget.cancel_grace_ms / 1000 + 2
        assert not projects.draft["datasets"] and projects.store.commit_id == before
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.setOption("record_path", "/root/record")
        imports.refreshPreview()
        spin(app, lambda: not imports.busy)
        source.write_text("<root><record><x>new</x></record></root>")
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert "değişti" in imports.errorText
        assert not projects.draft["datasets"] and projects.store.commit_id == before
    finally:
        teardown(app, window)


@pytest.mark.parametrize("container", ["gzip", "zip", "dataset_zip"])
def test_gui_compressed_inputs(tmp_path, monkeypatch, container):
    import gzip
    import zipfile

    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    try:
        source = fixture(
            tmp_path,
            "xml"
            if container == "gzip"
            else "fixed_width"
            if container == "zip"
            else "parquet_dataset",
        )
        target = tmp_path / ("data.xml.gz" if container == "gzip" else "data.zip")
        if container == "gzip":
            with gzip.open(target, "wb") as stream:
                stream.write(source.read_bytes())
        else:
            with zipfile.ZipFile(target, "w") as archive:
                if source.is_dir():
                    for path in source.rglob("*.parquet"):
                        archive.write(path, path.relative_to(source).as_posix())
                    # Two pieces force dataset ZIP recognition.
                    archive.writestr(
                        "region=002/part-1.parquet",
                        next(source.rglob("*.parquet")).read_bytes(),
                    )
                else:
                    archive.write(source, source.name)
        before = target.read_bytes()
        imports.choose(str(target))
        spin(app, lambda: not imports.busy)
        if container == "gzip":
            imports.setOption("record_path", "/root/record")
        elif container == "zip":
            imports.setOption("widths", "3,7")
            imports.setOption("column_names", "code|name")
        if container != "dataset_zip":
            imports.refreshPreview()
            spin(app, lambda: not imports.busy)
        assert imports.ready, imports.errorText
        imports.importData(True)
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        assert target.read_bytes() == before
        assert projects.draft["sources"][-1]["copy_uri"]
        assert projects.closeProject() and projects.open(str(tmp_path / "project"))
        assert (
            projects.store.source_statuses()[projects.draft["sources"][-1]["id"]]
            == "unchanged"
        )
    finally:
        teardown(app, window)
