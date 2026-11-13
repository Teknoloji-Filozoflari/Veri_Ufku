# SCHEMA_MAP — alt başlık ↔ modül ↔ QML ↔ test

**Sürüm:** 1.1 · 2026-11-13 · Faz A + B + C
**Durum kaynağı:** [SCHEMA_CONTRACT.md](SCHEMA_CONTRACT.md)

Bu harita, şemadaki 61 alt başlığı mevcut kod yüzeylerine bağlar. Kod yolu ileride
değişirse **bu tablo güncellenir**; tablo ters yönde de bağlayıcıdır: bir alt başlık için
yeni kod yazıldığında burada karşılığı gösterilmeden alt başlık "var" sayılmaz.

Yollar depo köküne görelidir. `—` = karşılığı yok.

## Veri

| # | Alt başlık | Python modülü | QML | Test | Durum |
|---|---|---|---|---|---|
| V-01 | Proje | `src/veri_ufku/ui/projects.py`, `src/veri_ufku/storage/project_store.py` | `DataWorkspacePanel.qml`, `ProjectPanel.qml` | `tests/test_projects.py`, `tests/test_project_gui.py` | var |
| V-02 | Kaynak seçimi | `src/veri_ufku/ui/imports.py`, `src/veri_ufku/importers/registry.py` | `ImportPanel.qml`, `DataWorkspacePanel.qml` | `tests/test_import_gui.py`, `tests/test_advanced_import.py` | var |
| V-03 | Okuma ayarları ve önizleme | `src/veri_ufku/importers/delimited.py`, `src/veri_ufku/ui/imports.py` | `ImportPanel.qml` | `tests/test_delimited.py`, `tests/test_import_gui.py` | var |
| V-04 | Tür ve rol atama | `src/veri_ufku/ui/dataset.py`, `src/veri_ufku/operations/contracts.py` | `DatasetPanel.qml`, `ImportPanel.qml` | `tests/test_dataset.py`, `tests/test_import_gui.py` | var |
| V-05 | Eksik değer eşleştirme | `src/veri_ufku/ui/imports.py`, `src/veri_ufku/analytics/dataset.py` | `ImportPanel.qml`, `DataWorkspacePanel.qml` | `tests/test_ux6_missing_impact.py` | eksik |
| V-06 | İçe aktarma kontrolü | `src/veri_ufku/ui/imports.py` | `DataWorkspacePanel.qml` | `tests/test_import_gui.py` | eksik |
| V-07 | Veri sürümü | `src/veri_ufku/storage/project_store.py`, `src/veri_ufku/storage/lineage.py` | `DataWorkspacePanel.qml` | `tests/test_projects.py`, `tests/test_operations.py` | var |
| V-08 | İlk bakış | `src/veri_ufku/analytics/inspection.py`, `src/veri_ufku/ui/dataset.py` | `DatasetOverview.qml` | `tests/test_data_inspection.py` | var |
| V-09 | Kaynak adaptörleri (Modül) | `src/veri_ufku/importers/connectors.py`, `src/veri_ufku/importers/database_connectors.py`, `src/veri_ufku/importers/http_connectors.py` | `ConnectorPanel.qml` | `tests/test_connectors.py`, `tests/test_connector_gui.py` | var |
| V-10 | Özel kaynaklar (Modül) | `src/veri_ufku/plugins/sdk.py`, `src/veri_ufku/plugins/runtime.py`, `src/veri_ufku/importers/advanced.py`, `src/veri_ufku/importers/arrays.py` | `PluginsPanel.qml` | `tests/test_plugins.py`, `tests/test_advanced_import.py` | var |

## İncele

| # | Alt başlık | Python modülü | QML | Test | Durum |
|---|---|---|---|---|---|
| I-01 | Tablo ve sütunlar | `src/veri_ufku/ui/dataset.py`, `src/veri_ufku/storage/project_store.py` | `InspectWorkspacePanel.qml`, `DatasetPanel.qml` | `tests/test_dataset.py`, `tests/test_dataset_gui.py` | var |
| I-02 | Temel özet | `src/veri_ufku/analytics/inspection.py` | `InspectSummary.qml`, `DatasetOverview.qml` | `tests/test_data_inspection.py` | var |
| I-03 | Eksik veri | `src/veri_ufku/analytics/quality.py`, `src/veri_ufku/analytics/dataset.py` | `InspectWorkspacePanel.qml`, `MissingSamplingPanel.qml` | `tests/test_quality.py`, `tests/test_ux6_missing_impact.py` | var |
| I-04 | Kalite kontrolleri | `src/veri_ufku/analytics/quality.py`, `src/veri_ufku/ui/dataset.py` | `QualityPanel.qml`, `InspectWorkspacePanel.qml` | `tests/test_quality.py`, `tests/test_quality_gui.py` | var |
| I-05 | Özel veri türleri (Modül) | `src/veri_ufku/modeling/vision.py`, `src/veri_ufku/modeling/audio.py`, `src/veri_ufku/modeling/time_series.py`, `src/veri_ufku/modeling/signals.py`, `src/veri_ufku/analytics/text.py` | `VisionPanel.qml`, `AudioPanel.qml`, `TextPanel.qml`, `TemporalPanel.qml`, `SignalPanel.qml` | `tests/test_vision.py`, `tests/test_audio.py`, `tests/test_text.py`, `tests/test_temporal.py`, `tests/test_signals.py` | var |

## Görselleştir

| # | Alt başlık | Python modülü | QML | Test | Durum |
|---|---|---|---|---|---|
| G-01 | Soru odaklı öneri | `src/veri_ufku/charts/engine.py`, `src/veri_ufku/ui/charts.py` | `ChartPanel.qml`, `VisualizeWorkspace.qml` | `tests/test_charts.py` | var |
| G-02 | Grafik açıklama paneli | `src/veri_ufku/ui/chart_explain.py` | `VisualizeWorkspace.qml` | `tests/test_chart_explain.py` | var |
| G-03 | Dağılım ve eksikler | `src/veri_ufku/charts/distributions.py`, `src/veri_ufku/charts/engine.py` | `ChartPanel.qml`, `DistributionOptions.qml` | `tests/test_distributions.py`, `tests/test_charts.py` | var |
| G-04 | Karşılaştırma ve oran | `src/veri_ufku/charts/composition.py`, `src/veri_ufku/charts/composition_plot.py` | `CompositionOptions.qml` | `tests/test_composition.py` | var |
| G-05 | Zaman ve olay sırası | `src/veri_ufku/charts/engine.py`, `src/veri_ufku/charts/plot.py` | `ChartPanel.qml`, `TimeSeriesPanel.qml` | `tests/test_charts.py`, `tests/test_time_series.py` | eksik |
| G-06 | İlişki ve çok değişen | `src/veri_ufku/charts/multivariate.py`, `src/veri_ufku/charts/multivariate_plot.py` | `MultivariateOptions.qml` | `tests/test_multivariate.py` | var |
| G-07 | Dağılım ve oran (ileri) (Modül) | `src/veri_ufku/charts/distributions.py`, `src/veri_ufku/charts/composition.py` | `DistributionOptions.qml`, `CompositionOptions.qml` | `tests/test_distributions.py`, `tests/test_composition.py` | var |
| G-08 | İlişki ve zaman (ileri) (Modül) | `src/veri_ufku/charts/multivariate.py` | `MultivariateOptions.qml` | `tests/test_multivariate.py` | var |
| G-09 | Hiyerarşi ve akış (Modül) | `src/veri_ufku/charts/composition.py`, `src/veri_ufku/charts/composition_plot.py` | `CompositionOptions.qml` | `tests/test_composition.py` | var |
| G-10 | Ağ ve bağlantılar (Modül) | `src/veri_ufku/modeling/graphs.py`, `src/veri_ufku/importers/graphs.py`, `src/veri_ufku/storage/graph_store.py` | `GraphPanel.qml` | `tests/test_graphs.py`, `tests/test_graphs_gui.py` | var |
| G-11 | Dizi ve coğrafya (Modül) | `src/veri_ufku/importers/arrays.py`, `src/veri_ufku/geo/charts.py`, `src/veri_ufku/geo/operations.py` | `ArrayOptions.qml`, `GeoChartOptions.qml` | `tests/test_arrays.py`, `tests/test_geo.py` | var |
| G-12 | Metin ve ileri seçenekler (Modül) | `src/veri_ufku/analytics/text.py`, `src/veri_ufku/ui/text.py` | `TextPanel.qml`, `TextOptions.qml` | `tests/test_text.py` | var |

## Hazırla

| # | Alt başlık | Python modülü | QML | Test | Durum |
|---|---|---|---|---|---|
| H-01 | Eksik veri | `src/veri_ufku/operations/cleaning.py`, `src/veri_ufku/operations/cleaning_contracts.py` | `CleaningOptions.qml`, `PrepareCatalogPanel.qml` | `tests/test_cleaning.py`, `tests/test_cleaning_gui.py` | var |
| H-02 | Aykırı değerler | `src/veri_ufku/analytics/outliers.py`, `src/veri_ufku/operations/cleaning.py` | `CleaningOptions.qml`, `OperationsPanel.qml` | `tests/test_ux7_ux8_outliers.py`, `tests/test_cleaning.py` | var |
| H-03 | Sütun temizliği | `src/veri_ufku/operations/cleaning.py` | `CleaningOptions.qml` | `tests/test_cleaning.py` | var |
| H-04 | Kalite düzeltmeleri | `src/veri_ufku/operations/cleaning.py`, `src/veri_ufku/operations/data_quality.py` | `PrepareCatalogPanel.qml`, `CleaningOptions.qml` | `tests/test_cleaning.py`, `tests/test_quality.py` | var |
| H-05 | Yeni sütun üret | `src/veri_ufku/operations/relational.py`, `src/veri_ufku/operations/formula.py` | `TransformationOptions.qml` | `tests/test_relational.py` | var |
| H-06 | Tablo birleştirme ve şekil | `src/veri_ufku/operations/relational.py` | `TransformationOptions.qml` | `tests/test_relational.py` | var |
| H-07 | Özel veri türleri (Modül) | — | `PrepareCatalogPanel.qml` (boş kutu notu) | — | yok |
| H-08 | Öğrenilen dönüşümler | `src/veri_ufku/operations/cleaning_contracts.py`, `src/veri_ufku/operations/contracts.py` | `PrepareCatalogPanel.qml` | `tests/test_cleaning.py`, `tests/test_prepare_workspace_gui.py` | eksik |
| H-09 | Uygula ve kayıt | `src/veri_ufku/ui/operations.py`, `src/veri_ufku/storage/project_store.py` | `OperationsPanel.qml`, `PrepareWorkspace.qml` | `tests/test_operations.py` | var |

## İstatistik

| # | Alt başlık | Python modülü | QML | Test | Durum |
|---|---|---|---|---|---|
| İ-01 | Dağılım ve normallik | `src/veri_ufku/statistics/engine.py`, `src/veri_ufku/charts/distribution_plot.py` | `StatisticsCatalogPanel.qml` | `tests/test_distributions.py`, `tests/test_statistics.py` | eksik |
| İ-02 | İlişki ölçüleri | `src/veri_ufku/statistics/engine.py` | `StatisticsCatalogPanel.qml` | `tests/test_statistics.py` | var |
| İ-03 | Hipotez testi | `src/veri_ufku/statistics/engine.py` | `StatisticsPanel.qml` | `tests/test_statistics.py` | var |
| İ-04 | Etki büyüklüğü ve belirsizlik | `src/veri_ufku/statistics/engine.py` | `StatisticsCatalogPanel.qml` | `tests/test_statistics.py` | var |
| İ-05 | Test öneri kartı | `src/veri_ufku/ui/statistics_advice.py` | `StatisticsCatalogPanel.qml` | `tests/test_statistics_advice.py` | var |
| İ-06 | Regresyon (çıkarım) | `src/veri_ufku/statistics/models.py`, `src/veri_ufku/statistics/model_contracts.py` | `StatisticalModelsPanel.qml` | `tests/test_statistical_models.py` | var |
| İ-07 | Sağlamlık ve deneme kaydı | `src/veri_ufku/statistics/resampling.py`, `src/veri_ufku/statistics/experiments.py`, `src/veri_ufku/storage/experiment_store.py` | `ResamplingPanel.qml`, `ExperimentPanel.qml`, `ExperimentRegistryPanel.qml` | `tests/test_resampling.py`, `tests/test_experiments.py` | var |
| İ-08 | İleri istatistik (Modül) | `src/veri_ufku/statistics/bayes.py`, `causal.py`, `survival.py`, `missing_sampling.py`, `dimensions.py` | `BayesPanel.qml`, `CausalPanel.qml`, `SurvivalPanel.qml`, `MissingSamplingPanel.qml`, `DimensionsPanel.qml` | `tests/test_bayes.py`, `tests/test_causal.py`, `tests/test_survival.py`, `tests/test_missing_sampling.py`, `tests/test_dimensions.py` | var |

## Model

| # | Alt başlık | Python modülü | QML | Test | Durum |
|---|---|---|---|---|---|
| M-01 | Hedef ve plan | `src/veri_ufku/modeling/plan.py`, `src/veri_ufku/modeling/contracts.py`, `src/veri_ufku/storage/preparation_store.py` | `PreparationPanel.qml` | `tests/test_preparation.py` | var |
| M-02 | Hazırla'dan devralınanlar | `src/veri_ufku/modeling/history.py`, `src/veri_ufku/modeling/families.py` | `PreparationPanel.qml` | `tests/test_preparation.py`, `tests/test_model_leakage.py` | eksik |
| M-03 | Regresyon (tahmin) | `src/veri_ufku/modeling/regression.py`, `src/veri_ufku/modeling/baseline.py` | `RegressionPanel.qml` | `tests/test_regression.py` | var |
| M-04 | Sınıflandırma | `src/veri_ufku/modeling/classification.py` | `ClassificationPanel.qml` | `tests/test_classification.py` | var |
| M-05 | Kümeleme | `src/veri_ufku/modeling/unsupervised.py`, `src/veri_ufku/modeling/unsupervised_contracts.py` | `UnsupervisedPanel.qml` | `tests/test_unsupervised.py` | var |
| M-06 | Boyut azaltma | `src/veri_ufku/statistics/dimensions.py`, `src/veri_ufku/statistics/dimension_contracts.py` | `DimensionsPanel.qml` | `tests/test_dimensions.py` | var |
| M-07 | Doğrulama ve karşılaştırma | `src/veri_ufku/modeling/validation.py`, `src/veri_ufku/modeling/search.py`, `src/veri_ufku/storage/validation_store.py` | `ValidationPanel.qml`, `SearchPanel.qml` | `tests/test_validation.py`, `tests/test_search.py` | var |
| M-08 | Yorumlama | `src/veri_ufku/modeling/explanation.py`, `src/veri_ufku/storage/explanation_store.py` | `ExplanationPanel.qml` | `tests/test_explanation.py` | var |
| M-09 | Özel veri türü yolları | `src/veri_ufku/modeling/time_series.py`, `streams.py`, `graphs.py`, `audio.py`, `vision.py`, `src/veri_ufku/analytics/nlp.py` | `TimeSeriesPanel.qml`, `StreamPanel.qml`, `GraphPanel.qml`, `AudioPanel.qml`, `VisionPanel.qml`, `TextPanel.qml` | `tests/test_time_series.py`, `tests/test_streams.py`, `tests/test_graphs.py`, `tests/test_audio.py`, `tests/test_vision.py`, `tests/test_text.py` | var |
| M-10 | İleri yollar | `src/veri_ufku/modeling/neural.py`, `monitoring.py`, `scenarios.py`, `patterns.py`, `lifecycle.py`, `uncertainty.py` | `NeuralPanel.qml`, `MonitoringPanel.qml`, `ScenarioPanel.qml`, `PatternPanel.qml` | `tests/test_neural.py`, `tests/test_monitoring.py`, `tests/test_scenarios.py`, `tests/test_patterns.py`, `tests/test_lifecycle.py` | var |

## Raporla

| # | Alt başlık | Python modülü | QML | Test | Durum |
|---|---|---|---|---|---|
| R-01 | Bulgu defteri | `src/veri_ufku/storage/finding_store.py`, `src/veri_ufku/ui/findings.py` | `FindingDrawer.qml`, `Main.qml` (çekmece + aşama eylemleri) | `tests/test_finding_store.py`, `tests/test_findings_gui.py` | var |
| R-02 | Rapor yapısı | `src/veri_ufku/exports/report_builder.py`, `src/veri_ufku/exports/report_contracts.py`, `src/veri_ufku/storage/report_builder_store.py` | `ReportBuilderPanel.qml`, `ReportCatalogPanel.qml` | `tests/test_report_builder.py` | var |
| R-03 | Rapor öncesi kontrol | `src/veri_ufku/storage/report_builder_store.py` | `ReportCatalogPanel.qml` | `tests/test_report_builder.py`, `tests/test_report_privacy.py` | var |
| R-04 | Dışa aktar | `src/veri_ufku/exports/reports.py`, `src/veri_ufku/exports/data.py`, `src/veri_ufku/charts/export.py`, `src/veri_ufku/exports/docx.py` | `ReportPanel.qml`, `ReportBuilderPanel.qml`, `ReportCatalogPanel.qml` | `tests/test_exports.py`, `tests/test_charts.py`, `tests/test_report_builder.py`, `tests/test_report_functions_gui.py` | var |
| R-05 | Yeniden üretim | `src/veri_ufku/exports/repro.py`, `src/veri_ufku/exports/repro_worker.py` | `ReproPanel.qml` | `tests/test_repro.py` | var |
| R-06 | Gizlilik ve paylaşım | `src/veri_ufku/exports/privacy.py`, `privacy_keys.py`, `share_bundle.py`, `share_privacy.py`, `src/veri_ufku/storage/privacy_store.py`, `review_store.py` | `PrivacyPanel.qml`, `SharingPanel.qml` | `tests/test_privacy.py`, `tests/test_share.py`, `tests/test_report_privacy.py` | var |
| R-07 | İleri çıktılar (Modül) | `src/veri_ufku/exports/repro.py`, `src/veri_ufku/exports/share_bundle.py` | `ReproPanel.qml`, `SharingPanel.qml` | `tests/test_repro.py`, `tests/test_share.py` | eksik |

## Katalog yüzeyleri ile şema kutularının karşılaştırması

Mevcut katalog panelleri şema kutularıyla birebir değildir. Faz G/C'de bu fark kapanacaktır.

| Panel | Mevcut blok sayısı | Şema beklentisi | Faz |
|---|---|---|---|
| `PrepareCatalogPanel.qml` | 10 (Sütun temizliği · Aykırı · Kalite · Yeni sütun · Birleştirme/şekil · Özel tür · Öğrenilen · Diğer · Uygunluk · Uygulama) | 9 (Eksik veri · Aykırı değerler · Sütun temizliği · Kalite düzeltmeleri · Yeni sütun üret · Tablo birleştirme ve şekil · Özel veri türleri · Öğrenilen dönüşümler · Uygula ve kayıt) | G (açık, bu oturumda uygulanmadı) |
| `ReportCatalogPanel.qml` | 8 kaynak-aşama bölümü (Faz C sonrası: "Rapor yapısı" işlevi içinde ikincil) | 7 işlev birincil (Bulgu defteri · Rapor yapısı · Rapor öncesi kontrol · Dışa aktar · Yeniden üretim · Gizlilik ve paylaşım · İleri çıktılar) | C — **tamamlandı** |
| `StatisticsCatalogPanel.qml` | 8 | 8 (adlar birebir) | I (yalnız bayat metin) |
| `ModelCatalogPanel.qml` | 10 | 10 | D (ad/adet birebir, yüzey derinliği farklı) |
| `DataWorkspacePanel.qml` | 10 | 10 | G |
| `InspectWorkspacePanel.qml` | 5 | 5 | G |

## Bu haritanın güncellenmesi

Yeni bir şema alt başlığı için kod yazıldığında:

1. İlgili Python modülü, QML dosyası ve test dosyası bu tabloya eklenir.
2. [SCHEMA_CONTRACT.md](SCHEMA_CONTRACT.md) içindeki durum satırı `eksik` → `var` olarak güncellenir.
3. Durum metni üç durumu da göstermeye devam eder; "yok" satırı boş yer tutucuyla doldurulmaz.
