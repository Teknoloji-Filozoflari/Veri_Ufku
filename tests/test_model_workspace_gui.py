"""Model yerleşimi: katalog + tahmin yolları; çıkarım yüzeyi İstatistik aşamasında."""

import copy

import polars as pl
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_learning_gui import visual_item


def item(window, name):
    return window.findChild(QObject, name) or visual_item(window.contentItem(), name)


def test_model_workspace_shows_prediction_paths_only(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "model-ws.parquet"
    pl.DataFrame(
        dict(
            y=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            x=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
        )
    ).write_parquet(source)
    original = source.read_bytes()

    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText
        data = app._veri_ufku_resources[0]._dataset_resources
        version_before = data.dataset()["version_id"]
        before = copy.deepcopy(projects.draft)

        assert window.property("modelInstalled")
        window.setProperty("selectedSection", 5)
        spin(app, lambda: window.property("modelStageOpen"))
        assert window.property("centerOpen")
        assert item(window, "modelWorkspace") is not None
        assert item(window, "modelWorkspace").property("visible")
        panel = item(window, "modelCatalogPanel")
        assert panel is not None and panel.property("visible")
        assert item(window, "modelCatalogTitle").property("text") == "Model"
        for index in range(1, 11):
            assert item(window, f"modelBlockChip_{index}") is not None

        # Model aşaması tahmin yoludur: çıkarım formu burada değildir.
        assert item(window, "modelResponse") is None
        assert item(window, "modelPreflight") is None
        assert item(window, "modelPrimaryAction") is None

        # Tahmin yolları katalog üzerinden açılır.
        item(window, "modelBlockChip_3").clicked.emit()
        app.processEvents()
        assert panel.property("selectedBlock") == 3
        assert item(window, "regressionPanel").property("visible")
        item(window, "modelBlockChip_4").clicked.emit()
        app.processEvents()
        assert item(window, "classificationPanel").property("visible")

        # Model aşaması veri sürümü üretmez ve kaynak dosyayı değiştirmez.
        assert data.dataset()["version_id"] == version_before
        assert projects.draft["datasets"] == before["datasets"]
        assert item(window, "modelLayerStrip") is not None
        assert (
            "held-out" in (item(window, "modelTestN").property("text") or "").lower()
            or "yok" in (item(window, "modelTestN").property("text") or "").lower()
        )
        assert source.read_bytes() == original
    finally:
        teardown(app, window)


def test_model_workspace_explains_inference_moved_to_statistics(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "model-b7.parquet"
    pl.DataFrame(dict(y=[1.0, 2.0, 3.0, 4.0], x=[1.0, 2.0, 3.0, 4.0])).write_parquet(
        source
    )

    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        window.setProperty("selectedSection", 5)
        spin(app, lambda: window.property("modelStageOpen"))
        note = item(window, "modelCatalogInferenceNote")
        assert note is not None
        assert "İstatistik" in (note.property("text") or "")
        pointer = item(window, "modelCatalogOpenStatistics")
        assert pointer is not None
        pointer.clicked.emit()
        spin(app, lambda: window.property("selectedSection") == 4)
        # Açıklayıcı regresyon yalnız İstatistik aşamasında üretilir.
        window.setProperty("examineTool", 7)
        spin(app, lambda: item(window, "statisticalModelsPanel") is not None)
        assert item(window, "modelsResponse") is not None
    finally:
        teardown(app, window)
