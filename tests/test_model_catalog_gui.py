"""Model kataloğu: şemanın on alt başlığı, tahmin yolları ve çıkarım/tahmin ayrımı."""

import polars as pl
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_learning_gui import visual_item

# Şemanın Model aşamasındaki alt başlıkları (veri_ufku_sema.pdf, Model kutusu).
SCHEMA_TITLES = [
    "Hedef ve plan",
    "Hazırla'dan devralınanlar",
    "Regresyon",
    "Sınıflandırma",
    "Kümeleme",
    "Boyut azaltma",
    "Doğrulama ve karşılaştırma",
    "Yorumlama",
    "Özel veri türü yolları",
    "İleri yollar",
]


def item(window, name):
    return window.findChild(QObject, name) or visual_item(window.contentItem(), name)


def imported(tmp_path, monkeypatch, name="model-catalog"):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / f"{name}.parquet"
    pl.DataFrame(
        dict(
            y=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            x=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
        )
    ).write_parquet(source)
    imports.choose(str(source))
    spin(app, lambda: not imports.busy)
    imports.importData()
    spin(app, lambda: not imports.busy)
    assert not imports.errorText
    return app, window, projects, imports


def test_model_catalog_lists_ten_schema_entries(tmp_path, monkeypatch):
    app, window, projects, imports = imported(tmp_path, monkeypatch)
    try:
        window.setProperty("selectedSection", 5)
        spin(app, lambda: window.property("modelStageOpen"))
        panel = item(window, "modelCatalogPanel")
        assert panel is not None
        entries = panel.property("schemaEntries")
        if hasattr(entries, "toVariant"):
            entries = entries.toVariant()
        assert len(entries) == 10
        assert [entry["title"] for entry in entries] == SCHEMA_TITLES
        assert [entry["index"] for entry in entries] == list(range(1, 11))
        # M-09 şemada "Modül · Tür modülleri"; diğerleri "Modül · Model".
        assert entries[8]["module"] == "Modül · Tür modülleri"
        assert entries[0]["module"] == "Modül · Model"
        # B-06: çekirdek = temel + keşif; yorum ve ileri yollar isteğe bağlı modül.
        tiers = [entry["tier"] for entry in entries]
        assert tiers[:7] == ["core"] * 7
        assert tiers[7:] == ["optional"] * 3
        for index in range(1, 11):
            chip = item(window, f"modelBlockChip_{index}")
            assert chip is not None, index
            assert chip.property("visible")
    finally:
        teardown(app, window)


def test_model_catalog_routes_to_prediction_paths(tmp_path, monkeypatch):
    app, window, projects, imports = imported(tmp_path, monkeypatch)
    try:
        window.setProperty("selectedSection", 5)
        spin(app, lambda: window.property("modelStageOpen"))
        routes = {
            1: "preparationPanel",
            2: "modelPathsPanel",
            3: "regressionPanel",
            4: "classificationPanel",
            5: "unsupervisedPanel",
            6: "dimensionPanel",
            7: "validationPanel",
            8: "explanationPanel",
        }
        for index, name in routes.items():
            item(window, f"modelBlockChip_{index}").clicked.emit()
            app.processEvents()
            surface = item(window, name)
            assert surface is not None, name
            assert surface.property("visible"), name
        # Özel veri türü yolları ve ileri yollar da Model altındadır.
        item(window, "modelBlockChip_9").clicked.emit()
        app.processEvents()
        assert item(window, "timeSeriesPanel").property("visible")
        item(window, "modelBlockChip_10").clicked.emit()
        app.processEvents()
        assert item(window, "lifecyclePanel").property("visible")
    finally:
        teardown(app, window)


def test_explanatory_regression_belongs_to_statistics_stage(tmp_path, monkeypatch):
    app, window, projects, imports = imported(tmp_path, monkeypatch)
    try:
        window.setProperty("selectedSection", 5)
        spin(app, lambda: window.property("modelStageOpen"))
        # Model aşamasında çıkarım (OLS/WLS/GLM) formu kalmaz.
        assert item(window, "modelResponse") is None
        assert item(window, "modelCovariance") is None
        pointer = item(window, "modelCatalogOpenStatistics")
        assert pointer is not None
        pointer.clicked.emit()
        spin(app, lambda: window.property("selectedSection") == 4)
        # Açıklayıcı regresyon İstatistik aşamasındadır.
        window.setProperty("examineTool", 7)
        spin(app, lambda: item(window, "statisticalModelsPanel") is not None)
        assert item(window, "modelsResponse") is not None
    finally:
        teardown(app, window)


def test_model_stage_exposes_protocol_and_recipe_surfaces(tmp_path, monkeypatch):
    app, window, projects, imports = imported(tmp_path, monkeypatch)
    try:
        window.setProperty("selectedSection", 5)
        spin(app, lambda: window.property("modelStageOpen"))
        # Değerlendirme protokolü Model aşamasındadır (hedef/split/fold).
        assert item(window, "validationProtocol") is not None
        assert item(window, "validationRun") is not None
        # Mod 2 tarif yüzeyi ve sızıntı uyarısı.
        assert item(window, "modelPathsPanel") is not None
        assert item(window, "modelPathsPlanTitle") is not None
        assert item(window, "modelLeakageNotice") is not None
        # Model aşaması veri varken de açılır (önceden yalnız çıkarım yüzeyi vardı).
        assert window.property("centerOpen")
    finally:
        teardown(app, window)
