# Veri_Ufku — profesyonel teknik yetenek matrisi

2026-10-17; ENV-75. Güncel nihai teknik sınıflandırma aşağıdaki **Faz75 güncel sınıflandırma** bölümündedir. Önceki tablolar Faz28 tarihsel snapshot ve sonraki faz notlarıdır; güncel tam destek iddiası değildir. Kabul/kapsam ana kaydı [REQUIREMENTS_MATRIX](REQUIREMENTS_MATRIX.md), faz durumu [PRO_PROGRESS](PRO_PROGRESS.md). Bu belge mevcut uygulamanın sınırlarını gösterir; önceki resmî giriş kapıları ayrıca açıktır. Deneysel runtime desteği tam faz kabulü veya bilimsel uzman incelemesi değildir.

**UX V2 (2026-10-25, yerel `ux-v2`, teknik teslim):** StageStrip/ContextSidePanel, Verilerim (XDG indeks), eksik-etki önizlemesi, grafik notu+RowId işaret, üç yöntemli aykırı aday, gerekçeli model adayları (`modeling/candidates.py`), rapor UX bağlam notu. Yeni analiz yöntemi ailesi yok; mevcut registry/yetenekler korunur. Resmî ürün kabulü ayrı; kanıt [evidence/UX_V2.md](evidence/UX_V2.md).

Kanıt: [son tam720 başarılı JUnit](evidence/phase28/pytest-final.xml), [714 başarılı / 1 belge hatalı ilk koşu](evidence/phase28/pytest.log), [yöntem tanıkları](evidence/phase28/capability-evidence.json), [kaynak+tipli registry snapshot](evidence/phase28/audit.json), [kaynak GUI](evidence/phase28/gui/walkthrough.json), [noneditable kurulu GUI](evidence/phase28/wheel-gui/walkthrough.json), [kurulu import](evidence/phase28/wheel-import.log). Son onarım kontrolleri [PHASE28](evidence/PHASE28.md). Registry beyanı tek başına hesap kanıtı sayılmaz: aşağıda gerçek test modülleri ve eski yöntem kanıtları da bağlanır. JSON tanık listesinde yönteme doğrudan eşleşen adlar ile yalnız modül akışını doğrulayan vakalar ayrı tutulur. Boş doğrudan liste yöntem başına bu koşuda yeni bilimsel kabul vermez; önceki yöntem kayıtları geçerlidir.

## Veri türü sınırları

| Tür | Gerçek saklama / analiz | GUI / yardım | Regression kanıtı / ana kayıt | Sınır / olgunluk |
|---|---|---|---|---|
| String | Leading zero ve karma CSV metin kalır; profil fiziksel String | Veri → profil/değer/tablo; import ve dataset.profile offline bağları | test_delimited;test_data_inspection; F05-S002;UPT-01; tanık JSON | Boş metin null değildir; deneysel |
| Int64 / UInt64 | CSV Int64 tam; Parquet native UInt64; ortak motor exact kontrol | Veri → profil/değer/tablo; import ve dataset.profile offline bağları | test_delimited;test_structured_import;test_dataset; F05-S003;F06-S004;UPT-01; tanık JSON | Float64 dönüştürmede >2^53 hassasiyet reddi; deneysel |
| Decimal | CSV Decimal(38,6); Parquet native scale korunur | Veri → profil/değer/tablo; import ve dataset.profile offline bağları | test_delimited;test_structured_import;test_dataset; F05-S003;F06-S004;UPT-01; tanık JSON | precision≤38; analitik model Float64 için exact guard; deneysel |
| Float32 / Float64 | Native float; null/NaN/inf ayrı, analizde sonlu dışlama | Veri → profil/değer/tablo; import ve dataset.profile offline bağları | test_dataset;test_structured_import;test_charts; F07-S003;F12-S002; tanık JSON | Tolerans ve dışlama n kayıtlı; deneysel |
| Boolean / Null | Açık import şeması; all-null doldurmada explicit type | Veri → profil/değer/tablo; import ve dataset.profile offline bağları | test_delimited;test_cleaning; F05-S003;F10-S002; tanık JSON | All-null sayısal ölçüm uydurmaz; deneysel |
| Date / Datetime timezone ns | Native metadata ve range korunur; açık DST politikası | Veri → profil/değer/tablo; import ve dataset.profile offline bağları | test_structured_import;test_cleaning;test_dataset; F06-S004;F10-S004; tanık JSON | Analitik yöntem ns/tz varyantı bazında ret; naive UTC sayılmaz; deneysel |
| List / Struct / Categorical | Native Parquet saklama; ortak salt okunur görünüm | Veri → profil/değer/tablo; import ve dataset.profile offline bağları | test_structured_import;test_relational; F06-S004;F11-S002; tanık JSON | Nested özet/dense ML genel desteği yok; kategori sırası semantik metadata ister; deneysel |

## Çalışan yöntem, format ve grafikler

Tüm aşağıdaki gerçek GUI yolları aynı immutable dataset, kaynak koruması, worker/bütçe ve ACTIVE kaydını kullanır. Parametre şeması, limitler ve beyan destekleri [audit snapshot](evidence/phase28/audit-initial.json) içinde birebir asdict; yeni runtime registry kurulmadı. E=deneysel. Eksik destek alanı bilinmiyor/uygunluk kanıtı yok demektir.

| Yetenek / yöntem | Tipli girdi → çıktı / kaynak | Gerçek GUI | Offline yardım | Test / serialization / kabul ID | Sınır / kararlılık / kanıt |
|---|---|---|---|---|---|
| demo.cpu: integer_sum | DemoParameters/v1 → DemoResult/v1; src/veri_ufku/jobs/manager.py | Main.qml; Faz01 gerçek QML regresyonu | tasks | F01-S003, F01-S006; 27 modül vakası; Altyapı örneği; analitik veri veya model değildir | units=1000, chunk_size=1000000; E; docs/evidence/PHASE01.md + tanık JSON |
| demo.io: bounded_file_write | DemoParameters/v1 → DemoResult/v1; src/veri_ufku/jobs/manager.py | Main.qml; Faz01 gerçek QML regresyonu | tasks | F01-S003, F01-S006; 27 modül vakası; Altyapı örneği; analitik veri veya model değildir | units=1000, chunk_size=1000000; E; docs/evidence/PHASE01.md + tanık JSON |
| demo.unknown: unknown_total | DemoParameters/v1 → DemoResult/v1; src/veri_ufku/jobs/manager.py | Main.qml; Faz01 gerçek QML regresyonu | tasks | F01-S003, F01-S006; 27 modül vakası; Altyapı örneği; analitik veri veya model değildir | units=1000, chunk_size=1000000; E; docs/evidence/PHASE01.md + tanık JSON |
| demo.failure: controlled_failure | DemoParameters/v1 → DemoResult/v1; src/veri_ufku/jobs/manager.py | Main.qml; Faz01 gerçek QML regresyonu | tasks | F01-S003, F01-S006; 27 modül vakası; Altyapı örneği; analitik veri veya model değildir | units=1000, chunk_size=1000000; E; docs/evidence/PHASE01.md + tanık JSON |
| statistics.welch-t: statistical_welch_t | DatasetVersion/v7 → AnalysisResult/v1; src/veri_ufku/statistics/engine.py | StatisticsPanel.qml; Faz14 gerçek QML regresyonu | statistics-welch-t, statistics-pvalue | F14-S001, F14-S002, F14-S003, F14-S004, F14-S005, F14-S006; 42 modül vakası; JSON tarif + immutable Parquet | rows=100000, groups=20; E; docs/evidence/PHASE14.md + tanık JSON |
| statistics.paired-t: statistical_paired_t | DatasetVersion/v7 → AnalysisResult/v1; src/veri_ufku/statistics/engine.py | StatisticsPanel.qml; Faz14 gerçek QML regresyonu | statistics-paired-t, statistics-pvalue | F14-S001, F14-S002, F14-S003, F14-S004, F14-S005, F14-S006; 42 modül vakası; JSON tarif + immutable Parquet | rows=100000, groups=20; E; docs/evidence/PHASE14.md + tanık JSON |
| statistics.mann-whitney: statistical_mann_whitney | DatasetVersion/v7 → AnalysisResult/v1; src/veri_ufku/statistics/engine.py | StatisticsPanel.qml; Faz14 gerçek QML regresyonu | statistics-mann-whitney, statistics-pvalue | F14-S001, F14-S002, F14-S003, F14-S004, F14-S005, F14-S006; 42 modül vakası; JSON tarif + immutable Parquet | rows=100000, groups=20; E; docs/evidence/PHASE14.md + tanık JSON |
| statistics.wilcoxon: statistical_wilcoxon | DatasetVersion/v7 → AnalysisResult/v1; src/veri_ufku/statistics/engine.py | StatisticsPanel.qml; Faz14 gerçek QML regresyonu | statistics-wilcoxon, statistics-pvalue | F14-S001, F14-S002, F14-S003, F14-S004, F14-S005, F14-S006; 42 modül vakası; JSON tarif + immutable Parquet | rows=100000, groups=20; E; docs/evidence/PHASE14.md + tanık JSON |
| statistics.anova: statistical_anova | DatasetVersion/v7 → AnalysisResult/v1; src/veri_ufku/statistics/engine.py | StatisticsPanel.qml; Faz14 gerçek QML regresyonu | statistics-anova, statistics-pvalue | F14-S001, F14-S002, F14-S003, F14-S004, F14-S005, F14-S006; 42 modül vakası; JSON tarif + immutable Parquet | rows=100000, groups=20; E; docs/evidence/PHASE14.md + tanık JSON |
| statistics.welch-anova: statistical_welch_anova | DatasetVersion/v7 → AnalysisResult/v1; src/veri_ufku/statistics/engine.py | StatisticsPanel.qml; Faz14 gerçek QML regresyonu | statistics-welch-anova, statistics-pvalue | F14-S001, F14-S002, F14-S003, F14-S004, F14-S005, F14-S006; 42 modül vakası; JSON tarif + immutable Parquet | rows=100000, groups=20; E; docs/evidence/PHASE14.md + tanık JSON |
| statistics.kruskal: statistical_kruskal | DatasetVersion/v7 → AnalysisResult/v1; src/veri_ufku/statistics/engine.py | StatisticsPanel.qml; Faz14 gerçek QML regresyonu | statistics-kruskal, statistics-pvalue | F14-S001, F14-S002, F14-S003, F14-S004, F14-S005, F14-S006; 42 modül vakası; JSON tarif + immutable Parquet | rows=100000, groups=20; E; docs/evidence/PHASE14.md + tanık JSON |
| statistics.chi2: statistical_chi2 | DatasetVersion/v7 → AnalysisResult/v1; src/veri_ufku/statistics/engine.py | StatisticsPanel.qml; Faz14 gerçek QML regresyonu | statistics-chi2, statistics-pvalue | F14-S001, F14-S002, F14-S003, F14-S004, F14-S005, F14-S006; 42 modül vakası; JSON tarif + immutable Parquet | rows=100000, groups=20; E; docs/evidence/PHASE14.md + tanık JSON |
| statistics.fisher: statistical_fisher | DatasetVersion/v7 → AnalysisResult/v1; src/veri_ufku/statistics/engine.py | StatisticsPanel.qml; Faz14 gerçek QML regresyonu | statistics-fisher, statistics-pvalue | F14-S001, F14-S002, F14-S003, F14-S004, F14-S005, F14-S006; 42 modül vakası; JSON tarif + immutable Parquet | rows=100000, groups=20; E; docs/evidence/PHASE14.md + tanık JSON |
| statistics.pearson: statistical_pearson | DatasetVersion/v7 → AnalysisResult/v1; src/veri_ufku/statistics/engine.py | StatisticsPanel.qml; Faz14 gerçek QML regresyonu | statistics-pearson, statistics-pvalue | F14-S001, F14-S002, F14-S003, F14-S004, F14-S005, F14-S006; 42 modül vakası; JSON tarif + immutable Parquet | rows=100000, groups=20; E; docs/evidence/PHASE14.md + tanık JSON |
| statistics.spearman: statistical_spearman | DatasetVersion/v7 → AnalysisResult/v1; src/veri_ufku/statistics/engine.py | StatisticsPanel.qml; Faz14 gerçek QML regresyonu | statistics-spearman, statistics-pvalue | F14-S001, F14-S002, F14-S003, F14-S004, F14-S005, F14-S006; 42 modül vakası; JSON tarif + immutable Parquet | rows=100000, groups=20; E; docs/evidence/PHASE14.md + tanık JSON |
| model.prepare: unfitted_preparation_plan | DatasetVersion/v7 → PreparationReport/v1; src/veri_ufku/modeling/preparation.py | PreparationPanel.qml; Faz15 gerçek QML regresyonu | model-preparation, model-training-fold | F15-S001, F15-S002, F15-S003, F15-S004, F15-S005, F15-S006; 30 modül vakası; JSON tarif/sonuç; fitted paket yalnız F20 allowlist | rows=100000, columns=100; E; docs/evidence/PHASE15.md + tanık JSON |
| import.csv: validated_snapshot_delimited | ImportSettings/v1 → DatasetParquet/v1; src/veri_ufku/importers/delimited.py | ImportPanel.qml; Faz05 gerçek QML regresyonu | import-csv | F05-S001, F05-S002, F05-S003, F05-S004, F05-S005, F05-S006, F05-S007; 57 modül vakası; JSON tarif + immutable Parquet | source_bytes=1073741824, columns=256, record_bytes=1048576, preview_rows=200; E; docs/evidence/PHASE05.md + tanık JSON |
| import.tsv: validated_snapshot_delimited | ImportSettings/v1 → DatasetParquet/v1; src/veri_ufku/importers/delimited.py | ImportPanel.qml; Faz05 gerçek QML regresyonu | import-csv | F05-S001, F05-S002, F05-S003, F05-S004, F05-S005, F05-S006, F05-S007; 57 modül vakası; JSON tarif + immutable Parquet | source_bytes=1073741824, columns=256, record_bytes=1048576, preview_rows=200; E; docs/evidence/PHASE05.md + tanık JSON |
| import.json: validated_snapshot_json | StructuredSettings/v1 → DatasetParquet/native-v1; src/veri_ufku/importers/registry.py | ImportPanel.qml; Faz06 gerçek QML regresyonu | import-json | F06-S001, F06-S002, F06-S003, F06-S004, F06-S005, F06-S006, F06-S007; 49 modül vakası; JSON tarif + immutable Parquet | source_bytes=1073741824, columns=256, preview_rows=200, json_bytes=67108864, record_bytes=1048576; E; docs/evidence/PHASE06.md + tanık JSON |
| import.jsonl: validated_snapshot_jsonl | StructuredSettings/v1 → DatasetParquet/native-v1; src/veri_ufku/importers/registry.py | ImportPanel.qml; Faz06 gerçek QML regresyonu | import-jsonl | F06-S001, F06-S002, F06-S003, F06-S004, F06-S005, F06-S006, F06-S007; 49 modül vakası; JSON tarif + immutable Parquet | source_bytes=1073741824, columns=256, preview_rows=200, json_bytes=67108864, record_bytes=1048576; E; docs/evidence/PHASE06.md + tanık JSON |
| import.xlsx: validated_snapshot_xlsx | StructuredSettings/v1 → DatasetParquet/native-v1; src/veri_ufku/importers/registry.py | ImportPanel.qml; Faz06 gerçek QML regresyonu | import-xlsx | F06-S001, F06-S002, F06-S003, F06-S004, F06-S005, F06-S006, F06-S007; 49 modül vakası; JSON tarif + immutable Parquet | source_bytes=1073741824, columns=256, preview_rows=200, json_bytes=67108864, record_bytes=1048576; E; docs/evidence/PHASE06.md + tanık JSON |
| import.parquet: validated_snapshot_parquet | StructuredSettings/v1 → DatasetParquet/native-v1; src/veri_ufku/importers/registry.py | ImportPanel.qml; Faz06 gerçek QML regresyonu | import-parquet | F06-S001, F06-S002, F06-S003, F06-S004, F06-S005, F06-S006, F06-S007; 49 modül vakası; JSON tarif + immutable Parquet | source_bytes=1073741824, columns=256, preview_rows=200, json_bytes=67108864, record_bytes=1048576; E; docs/evidence/PHASE06.md + tanık JSON |
| dataset.view: immutable_dataset_view | DemoParameters/v1 → DemoResult/v1; src/veri_ufku/analytics/dataset.py | DatasetPanel.qml; Faz07 gerçek QML regresyonu | dataset-profile | F07-S001, F07-S002, F07-S003, F07-S004, F07-S005, F07-S006, F07-S007; 29 modül vakası; JSON tarif + immutable Parquet | units=1000, chunk_size=1000000; E; docs/evidence/PHASE07.md + tanık JSON |
| dataset.profile: immutable_dataset_profile | DemoParameters/v1 → DemoResult/v1; src/veri_ufku/analytics/dataset.py | DatasetPanel.qml; Faz07 gerçek QML regresyonu | dataset-profile | F07-S001, F07-S002, F07-S003, F07-S004, F07-S005, F07-S006, F07-S007; 29 modül vakası; JSON tarif + immutable Parquet | units=1000, chunk_size=1000000; E; docs/evidence/PHASE07.md + tanık JSON |
| dataset.roles: immutable_dataset_roles | DemoParameters/v1 → DemoResult/v1; src/veri_ufku/analytics/dataset.py | DatasetPanel.qml; Faz07 gerçek QML regresyonu | column-role | F07-S001, F07-S002, F07-S003, F07-S004, F07-S005, F07-S006, F07-S007; 29 modül vakası; JSON tarif + immutable Parquet | units=1000, chunk_size=1000000; E; docs/evidence/PHASE07.md + tanık JSON |
| dataset.quality: immutable_quality_scan | DatasetVersion/v4 → QualityReport/v1; src/veri_ufku/analytics/quality.py | QualityPanel.qml; Faz08 gerçek QML regresyonu | quality, duplicates, missing-mechanism, outliers | F08-S001, F08-S002, F08-S003, F08-S004, F08-S005, F08-S006; 6 modül vakası; JSON tarif + immutable Parquet | rules=32, examples_per_finding=5, category_variants=200; E; docs/evidence/PHASE08.md + tanık JSON |
| operation.rename: versioned_rename | DatasetVersion/v5 → DatasetVersion/v5; src/veri_ufku/operations/engine.py | OperationsPanel.qml; Faz09 gerçek QML regresyonu | operation-preview, operation-history, source-working | F09-S001, F09-S002, F09-S003, F09-S004, F09-S005, F09-S006, F09-S007; 16 modül vakası; JSON tarif + immutable Parquet | columns=256, preview_rows=200; E; docs/evidence/PHASE09.md + tanık JSON |
| operation.drop: versioned_drop | DatasetVersion/v5 → DatasetVersion/v5; src/veri_ufku/operations/engine.py | OperationsPanel.qml; Faz09 gerçek QML regresyonu | operation-preview, operation-history, source-working | F09-S001, F09-S002, F09-S003, F09-S004, F09-S005, F09-S006, F09-S007; 16 modül vakası; JSON tarif + immutable Parquet | columns=256, preview_rows=200; E; docs/evidence/PHASE09.md + tanık JSON |
| operation.filter: versioned_filter | DatasetVersion/v5 → DatasetVersion/v5; src/veri_ufku/operations/engine.py | OperationsPanel.qml; Faz09 gerçek QML regresyonu | operation-preview, operation-history, source-working | F09-S001, F09-S002, F09-S003, F09-S004, F09-S005, F09-S006, F09-S007; 16 modül vakası; JSON tarif + immutable Parquet | columns=256, preview_rows=200; E; docs/evidence/PHASE09.md + tanık JSON |
| operation.missing-rows: versioned_cleaning_missing_rows | DatasetVersion/v6 → DatasetVersion/v6; src/veri_ufku/operations/cleaning.py | CleaningOptions.qml; Faz10 gerçek QML regresyonu | clean-missing-rows | F10-S001, F10-S002, F10-S003, F10-S004, F10-S005, F10-S006, F10-S007, F10-S008; 33 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, preview_rows=200, mapping_pairs=1000; E; docs/evidence/PHASE10.md + tanık JSON |
| operation.missing-columns: versioned_cleaning_missing_columns | DatasetVersion/v6 → DatasetVersion/v6; src/veri_ufku/operations/cleaning.py | CleaningOptions.qml; Faz10 gerçek QML regresyonu | clean-missing-columns | F10-S001, F10-S002, F10-S003, F10-S004, F10-S005, F10-S006, F10-S007, F10-S008; 33 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, preview_rows=200, mapping_pairs=1000; E; docs/evidence/PHASE10.md + tanık JSON |
| operation.fill: versioned_cleaning_fill | DatasetVersion/v6 → DatasetVersion/v6; src/veri_ufku/operations/cleaning.py | CleaningOptions.qml; Faz10 gerçek QML regresyonu | clean-fill-constant, clean-fill-mean, clean-fill-median, clean-fill-mode | F10-S001, F10-S002, F10-S003, F10-S004, F10-S005, F10-S006, F10-S007, F10-S008; 33 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, preview_rows=200, mapping_pairs=1000; E; docs/evidence/PHASE10.md + tanık JSON |
| operation.dedup: versioned_cleaning_dedup | DatasetVersion/v6 → DatasetVersion/v6; src/veri_ufku/operations/cleaning.py | CleaningOptions.qml; Faz10 gerçek QML regresyonu | clean-dedup | F10-S001, F10-S002, F10-S003, F10-S004, F10-S005, F10-S006, F10-S007, F10-S008; 33 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, preview_rows=200, mapping_pairs=1000; E; docs/evidence/PHASE10.md + tanık JSON |
| operation.trim: versioned_cleaning_trim | DatasetVersion/v6 → DatasetVersion/v6; src/veri_ufku/operations/cleaning.py | CleaningOptions.qml; Faz10 gerçek QML regresyonu | clean-trim | F10-S001, F10-S002, F10-S003, F10-S004, F10-S005, F10-S006, F10-S007, F10-S008; 33 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, preview_rows=200, mapping_pairs=1000; E; docs/evidence/PHASE10.md + tanık JSON |
| operation.map-categories: versioned_cleaning_map_categories | DatasetVersion/v6 → DatasetVersion/v6; src/veri_ufku/operations/cleaning.py | CleaningOptions.qml; Faz10 gerçek QML regresyonu | clean-map-categories | F10-S001, F10-S002, F10-S003, F10-S004, F10-S005, F10-S006, F10-S007, F10-S008; 33 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, preview_rows=200, mapping_pairs=1000; E; docs/evidence/PHASE10.md + tanık JSON |
| operation.convert: versioned_cleaning_convert | DatasetVersion/v6 → DatasetVersion/v6; src/veri_ufku/operations/cleaning.py | CleaningOptions.qml; Faz10 gerçek QML regresyonu | clean-convert | F10-S001, F10-S002, F10-S003, F10-S004, F10-S005, F10-S006, F10-S007, F10-S008; 33 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, preview_rows=200, mapping_pairs=1000; E; docs/evidence/PHASE10.md + tanık JSON |
| operation.ordered-fill: versioned_cleaning_ordered_fill | DatasetVersion/v6 → DatasetVersion/v6; src/veri_ufku/operations/cleaning.py | CleaningOptions.qml; Faz10 gerçek QML regresyonu | clean-ordered-fill-forward, clean-ordered-fill-backward | F10-S001, F10-S002, F10-S003, F10-S004, F10-S005, F10-S006, F10-S007, F10-S008; 33 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, preview_rows=200, mapping_pairs=1000; E; docs/evidence/PHASE10.md + tanık JSON |
| operation.outlier: versioned_cleaning_outlier | DatasetVersion/v6 → DatasetVersion/v6; src/veri_ufku/operations/cleaning.py | CleaningOptions.qml; Faz10 gerçek QML regresyonu | clean-outlier | F10-S001, F10-S002, F10-S003, F10-S004, F10-S005, F10-S006, F10-S007, F10-S008; 33 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, preview_rows=200, mapping_pairs=1000; E; docs/evidence/PHASE10.md + tanık JSON |
| operation.computed: versioned_transform_computed | DatasetVersion/v7 → DatasetVersion/v7; src/veri_ufku/operations/relational.py | TransformationOptions.qml; Faz11 gerçek QML regresyonu | transform-computed | F11-S001, F11-S002, F11-S003, F11-S004, F11-S005, F11-S006, F11-S007; 36 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, output_rows=10000000, preview_rows=200; E; docs/evidence/PHASE11.md + tanık JSON |
| operation.text-split: versioned_transform_text_split | DatasetVersion/v7 → DatasetVersion/v7; src/veri_ufku/operations/relational.py | TransformationOptions.qml; Faz11 gerçek QML regresyonu | transform-text-split | F11-S001, F11-S002, F11-S003, F11-S004, F11-S005, F11-S006, F11-S007; 36 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, output_rows=10000000, preview_rows=200; E; docs/evidence/PHASE11.md + tanık JSON |
| operation.text-combine: versioned_transform_text_combine | DatasetVersion/v7 → DatasetVersion/v7; src/veri_ufku/operations/relational.py | TransformationOptions.qml; Faz11 gerçek QML regresyonu | transform-text-combine | F11-S001, F11-S002, F11-S003, F11-S004, F11-S005, F11-S006, F11-S007; 36 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, output_rows=10000000, preview_rows=200; E; docs/evidence/PHASE11.md + tanık JSON |
| operation.date-parts: versioned_transform_date_parts | DatasetVersion/v7 → DatasetVersion/v7; src/veri_ufku/operations/relational.py | TransformationOptions.qml; Faz11 gerçek QML regresyonu | transform-date-parts | F11-S001, F11-S002, F11-S003, F11-S004, F11-S005, F11-S006, F11-S007; 36 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, output_rows=10000000, preview_rows=200; E; docs/evidence/PHASE11.md + tanık JSON |
| operation.aggregate: versioned_transform_aggregate | DatasetVersion/v7 → DatasetVersion/v7; src/veri_ufku/operations/relational.py | TransformationOptions.qml; Faz11 gerçek QML regresyonu | transform-aggregate | F11-S001, F11-S002, F11-S003, F11-S004, F11-S005, F11-S006, F11-S007; 36 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, output_rows=10000000, preview_rows=200; E; docs/evidence/PHASE11.md + tanık JSON |
| operation.pivot: versioned_transform_pivot | DatasetVersion/v7 → DatasetVersion/v7; src/veri_ufku/operations/relational.py | TransformationOptions.qml; Faz11 gerçek QML regresyonu | transform-pivot | F11-S001, F11-S002, F11-S003, F11-S004, F11-S005, F11-S006, F11-S007; 36 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, output_rows=10000000, preview_rows=200; E; docs/evidence/PHASE11.md + tanık JSON |
| operation.unpivot: versioned_transform_unpivot | DatasetVersion/v7 → DatasetVersion/v7; src/veri_ufku/operations/relational.py | TransformationOptions.qml; Faz11 gerçek QML regresyonu | transform-unpivot | F11-S001, F11-S002, F11-S003, F11-S004, F11-S005, F11-S006, F11-S007; 36 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, output_rows=10000000, preview_rows=200; E; docs/evidence/PHASE11.md + tanık JSON |
| operation.append: versioned_transform_append | DatasetVersion/v7 → DatasetVersion/v7; src/veri_ufku/operations/relational.py | TransformationOptions.qml; Faz11 gerçek QML regresyonu | transform-append | F11-S001, F11-S002, F11-S003, F11-S004, F11-S005, F11-S006, F11-S007; 36 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, output_rows=10000000, preview_rows=200; E; docs/evidence/PHASE11.md + tanık JSON |
| operation.join: versioned_transform_join | DatasetVersion/v7 → DatasetVersion/v7; src/veri_ufku/operations/relational.py | TransformationOptions.qml; Faz11 gerçek QML regresyonu | transform-join | F11-S001, F11-S002, F11-S003, F11-S004, F11-S005, F11-S006, F11-S007; 36 modül vakası; JSON tarif + immutable Parquet | columns=256, batch_rows=4096, output_rows=10000000, preview_rows=200; E; docs/evidence/PHASE11.md + tanık JSON |
| import.ods: validated_snapshot_ods | StructuredSettings/v1 → DatasetVersion/v7; src/veri_ufku/importers/registry.py | ImportPanel.qml; Faz11 gerçek QML regresyonu | import-phase11 | F11-S004, F11-S006, F11-S007; 36 modül vakası; JSON tarif + immutable Parquet | columns=256, source_bytes=1073741824, preview_rows=200; E; docs/evidence/PHASE11.md + tanık JSON |
| import.sqlite: validated_snapshot_sqlite | StructuredSettings/v1 → DatasetVersion/v7; src/veri_ufku/importers/registry.py | ImportPanel.qml; Faz11 gerçek QML regresyonu | import-phase11 | F11-S004, F11-S006, F11-S007; 36 modül vakası; JSON tarif + immutable Parquet | columns=256, source_bytes=1073741824, preview_rows=200; E; docs/evidence/PHASE11.md + tanık JSON |
| import.ipc: validated_snapshot_ipc | StructuredSettings/v1 → DatasetVersion/v7; src/veri_ufku/importers/registry.py | ImportPanel.qml; Faz11 gerçek QML regresyonu | import-phase11 | F11-S004, F11-S006, F11-S007; 36 modül vakası; JSON tarif + immutable Parquet | columns=256, source_bytes=1073741824, preview_rows=200; E; docs/evidence/PHASE11.md + tanık JSON |
| import.ipc-stream: validated_snapshot_ipc_stream | StructuredSettings/v1 → DatasetVersion/v7; src/veri_ufku/importers/registry.py | ImportPanel.qml; Faz11 gerçek QML regresyonu | import-phase11 | F11-S004, F11-S006, F11-S007; 36 modül vakası; JSON tarif + immutable Parquet | columns=256, source_bytes=1073741824, preview_rows=200; E; docs/evidence/PHASE11.md + tanık JSON |
| chart.histogram: chart_histogram | ChartSpec/v1 → ChartResult/v1; src/veri_ufku/charts/engine.py | ChartPanel.qml; Faz12 gerçek QML regresyonu | chart-histogram, chart-summary | F12-S001, F12-S002, F12-S003, F12-S004, F12-S005, F12-S006, F12-S007; 23 modül vakası; JSON metadata + Parquet/PNG/SVG artifact | correlation_columns=20, scatter_points=10000, histogram_bins=200, category_top_n=100; E; docs/evidence/PHASE12.md + tanık JSON |
| chart.box: chart_box | ChartSpec/v1 → ChartResult/v1; src/veri_ufku/charts/engine.py | ChartPanel.qml; Faz12 gerçek QML regresyonu | chart-box, chart-summary | F12-S001, F12-S002, F12-S003, F12-S004, F12-S005, F12-S006, F12-S007; 23 modül vakası; JSON metadata + Parquet/PNG/SVG artifact | correlation_columns=20, scatter_points=10000, histogram_bins=200, category_top_n=100; E; docs/evidence/PHASE12.md + tanık JSON |
| chart.bar: chart_bar | ChartSpec/v1 → ChartResult/v1; src/veri_ufku/charts/engine.py | ChartPanel.qml; Faz12 gerçek QML regresyonu | chart-bar, chart-summary | F12-S001, F12-S002, F12-S003, F12-S004, F12-S005, F12-S006, F12-S007; 23 modül vakası; JSON metadata + Parquet/PNG/SVG artifact | correlation_columns=20, scatter_points=10000, histogram_bins=200, category_top_n=100; E; docs/evidence/PHASE12.md + tanık JSON |
| chart.line: chart_line | ChartSpec/v1 → ChartResult/v1; src/veri_ufku/charts/engine.py | ChartPanel.qml; Faz12 gerçek QML regresyonu | chart-line, chart-summary | F12-S001, F12-S002, F12-S003, F12-S004, F12-S005, F12-S006, F12-S007; 23 modül vakası; JSON metadata + Parquet/PNG/SVG artifact | correlation_columns=20, scatter_points=10000, histogram_bins=200, category_top_n=100; E; docs/evidence/PHASE12.md + tanık JSON |
| chart.scatter: chart_scatter | ChartSpec/v1 → ChartResult/v1; src/veri_ufku/charts/engine.py | ChartPanel.qml; Faz12 gerçek QML regresyonu | chart-scatter, chart-summary | F12-S001, F12-S002, F12-S003, F12-S004, F12-S005, F12-S006, F12-S007; 23 modül vakası; JSON metadata + Parquet/PNG/SVG artifact | correlation_columns=20, scatter_points=10000, histogram_bins=200, category_top_n=100; E; docs/evidence/PHASE12.md + tanık JSON |
| chart.correlation: chart_correlation | ChartSpec/v1 → ChartResult/v1; src/veri_ufku/charts/engine.py | ChartPanel.qml; Faz12 gerçek QML regresyonu | chart-correlation, chart-summary | F12-S001, F12-S002, F12-S003, F12-S004, F12-S005, F12-S006, F12-S007; 23 modül vakası; JSON metadata + Parquet/PNG/SVG artifact | correlation_columns=20, scatter_points=10000, histogram_bins=200, category_top_n=100; E; docs/evidence/PHASE12.md + tanık JSON |
| chart.missing: chart_missing | ChartSpec/v1 → ChartResult/v1; src/veri_ufku/charts/engine.py | ChartPanel.qml; Faz12 gerçek QML regresyonu | chart-missing, chart-summary | F12-S001, F12-S002, F12-S003, F12-S004, F12-S005, F12-S006, F12-S007; 23 modül vakası; JSON metadata + Parquet/PNG/SVG artifact | correlation_columns=20, scatter_points=10000, histogram_bins=200, category_top_n=100; E; docs/evidence/PHASE12.md + tanık JSON |
| export.csv: verified_export_csv | DatasetVersion/v7 → PublishedReceipt/v1; src/veri_ufku/exports/data.py | ReportPanel.qml; Faz13 gerçek QML regresyonu | export | F13-S002, F13-S003, F13-S006; 22 modül vakası; JSON tarif ve artifact; kayıp formatı ayrı | xlsx_rows=100000, xlsx_columns=256, report_table_rows=200, report_charts=10; E; docs/evidence/PHASE13.md + tanık JSON |
| export.json: verified_export_json | DatasetVersion/v7 → PublishedReceipt/v1; src/veri_ufku/exports/data.py | ReportPanel.qml; Faz13 gerçek QML regresyonu | export | F13-S002, F13-S003, F13-S006; 22 modül vakası; JSON tarif ve artifact; kayıp formatı ayrı | xlsx_rows=100000, xlsx_columns=256, report_table_rows=200, report_charts=10; E; docs/evidence/PHASE13.md + tanık JSON |
| export.jsonl: verified_export_jsonl | DatasetVersion/v7 → PublishedReceipt/v1; src/veri_ufku/exports/data.py | ReportPanel.qml; Faz13 gerçek QML regresyonu | export | F13-S002, F13-S003, F13-S006; 22 modül vakası; JSON tarif ve artifact; kayıp formatı ayrı | xlsx_rows=100000, xlsx_columns=256, report_table_rows=200, report_charts=10; E; docs/evidence/PHASE13.md + tanık JSON |
| export.parquet: verified_export_parquet | DatasetVersion/v7 → PublishedReceipt/v1; src/veri_ufku/exports/data.py | ReportPanel.qml; Faz13 gerçek QML regresyonu | export | F13-S002, F13-S003, F13-S006; 22 modül vakası; JSON tarif ve artifact; kayıp formatı ayrı | xlsx_rows=100000, xlsx_columns=256, report_table_rows=200, report_charts=10; E; docs/evidence/PHASE13.md + tanık JSON |
| export.xlsx: verified_export_xlsx | DatasetVersion/v7 → PublishedReceipt/v1; src/veri_ufku/exports/data.py | ReportPanel.qml; Faz13 gerçek QML regresyonu | export | F13-S002, F13-S003, F13-S006; 22 modül vakası; JSON tarif ve artifact; kayıp formatı ayrı | xlsx_rows=100000, xlsx_columns=256, report_table_rows=200, report_charts=10; E; docs/evidence/PHASE13.md + tanık JSON |
| export.html: verified_export_html | DatasetVersion/v7 → PublishedReceipt/v1; src/veri_ufku/exports/reports.py | ReportPanel.qml; Faz13 gerçek QML regresyonu | report | F13-S002, F13-S003, F13-S006; 22 modül vakası; JSON tarif ve artifact; kayıp formatı ayrı | xlsx_rows=100000, xlsx_columns=256, report_table_rows=200, report_charts=10; E; docs/evidence/PHASE13.md + tanık JSON |
| export.pdf: verified_export_pdf | DatasetVersion/v7 → PublishedReceipt/v1; src/veri_ufku/exports/reports.py | ReportPanel.qml; Faz13 gerçek QML regresyonu | report | F13-S002, F13-S003, F13-S006; 22 modül vakası; JSON tarif ve artifact; kayıp formatı ayrı | xlsx_rows=100000, xlsx_columns=256, report_table_rows=200, report_charts=10; E; docs/evidence/PHASE13.md + tanık JSON |
| model.baseline: split_fold_dummy_baseline | DatasetVersion/v7 → BaselineRun/v1; src/veri_ufku/modeling/baseline.py | ValidationPanel.qml; Faz16 gerçek QML regresyonu | model-validation, model-test-use | F16-S001, F16-S002, F16-S003, F16-S004, F16-S005, F16-S006; 35 modül vakası; JSON tarif/sonuç; fitted paket yalnız F20 allowlist | rows=100000, columns=100, folds=10; E; docs/evidence/PHASE16.md + tanık JSON |
| model.regression: bounded_regression_cv | DatasetVersion/v7 → BaselineRun/v1 + regression; src/veri_ufku/modeling/regression.py | RegressionPanel.qml; Faz17 gerçek QML regresyonu | model-regression, model-test-use | F17-S001, F17-S002, F17-S003, F17-S004, F17-S005, F17-S006, F17-S007; 14 modül vakası; JSON tarif/sonuç; fitted paket yalnız F20 allowlist | rows=100000, forest_rows=20000, candidates=4, dense_cells=4000000; E; docs/evidence/PHASE17.md + tanık JSON |
| model.classification: bounded_classification_cv | DatasetVersion/v7 → BaselineRun/v1 + classification; src/veri_ufku/modeling/classification.py | ClassificationPanel.qml; Faz18 gerçek QML regresyonu | model-classification, classification-positive, classification-metrics, classification-threshold, classification-probability | F18-S001, F18-S002, F18-S003, F18-S004, F18-S005, F18-S006, F18-S007; 26 modül vakası; JSON tarif/sonuç; fitted paket yalnız F20 allowlist | rows=100000, forest_rows=20000, classes=20, dense_cells=4000000; E; docs/evidence/PHASE18.md + tanık JSON |
| model.kmeans: full_version_kmeans | DatasetVersion/v7 numeric measurements → UnsupervisedRun/v1 + RowId assignments; src/veri_ufku/modeling/unsupervised.py | UnsupervisedPanel.qml; Faz19 gerçek QML regresyonu | unsupervised-cluster, unsupervised-distance, unsupervised-noise, unsupervised-score, unsupervised-evaluation | F19-S001, F19-S002, F19-S003, F19-S004, F19-S005, F19-S006; 29 modül vakası; JSON tarif/sonuç; fitted paket yalnız F20 allowlist | rows=100000, features=20, silhouette_rows=3000; E; docs/evidence/PHASE19.md + tanık JSON |
| model.dbscan: full_version_dbscan | DatasetVersion/v7 numeric measurements → UnsupervisedRun/v1 + RowId assignments; src/veri_ufku/modeling/unsupervised.py | UnsupervisedPanel.qml; Faz19 gerçek QML regresyonu | unsupervised-cluster, unsupervised-distance, unsupervised-noise, unsupervised-score, unsupervised-evaluation | F19-S001, F19-S002, F19-S003, F19-S004, F19-S005, F19-S006; 29 modül vakası; JSON tarif/sonuç; fitted paket yalnız F20 allowlist | rows=3000, features=20, silhouette_rows=3000; E; docs/evidence/PHASE19.md + tanık JSON |
| model.isolation-forest: full_version_isolation-forest | DatasetVersion/v7 numeric measurements → UnsupervisedRun/v1 + RowId assignments; src/veri_ufku/modeling/unsupervised.py | UnsupervisedPanel.qml; Faz19 gerçek QML regresyonu | unsupervised-cluster, unsupervised-distance, unsupervised-noise, unsupervised-score, unsupervised-evaluation | F19-S001, F19-S002, F19-S003, F19-S004, F19-S005, F19-S006; 29 modül vakası; JSON tarif/sonuç; fitted paket yalnız F20 allowlist | rows=100000, features=20, silhouette_rows=3000; E; docs/evidence/PHASE19.md + tanık JSON |
| model.iqr: full_version_iqr | DatasetVersion/v7 numeric measurements → UnsupervisedRun/v1 + RowId assignments; src/veri_ufku/modeling/unsupervised.py | UnsupervisedPanel.qml; Faz19 gerçek QML regresyonu | unsupervised-cluster, unsupervised-distance, unsupervised-noise, unsupervised-score, unsupervised-evaluation | F19-S001, F19-S002, F19-S003, F19-S004, F19-S005, F19-S006; 29 modül vakası; JSON tarif/sonuç; fitted paket yalnız F20 allowlist | rows=100000, features=1, silhouette_rows=3000; E; docs/evidence/PHASE19.md + tanık JSON |
| model.lifecycle: closed_model_lifecycle | DatasetVersion/v7 + SafeModelPackage/v1 → ModelCard/v1 + PredictionParquet/v1; src/veri_ufku/modeling/lifecycle.py | LifecyclePanel.qml; Faz20 gerçek QML regresyonu | model-card, model-importance, model-unknown-category, model-new-data, model-uncertainty | F20-S001, F20-S002, F20-S003, F20-S004, F20-S005, F20-S006, F20-S007; 36 modül vakası; JSON tarif/sonuç; fitted paket yalnız F20 allowlist | rows=100000, package_bytes=134217728; E; docs/evidence/PHASE20.md + tanık JSON |
| model.time-series: chronological_forecast | DatasetVersion/v7 → TimeSeriesRun/v1; src/veri_ufku/modeling/time_series.py | TimeSeriesPanel.qml; Faz21 gerçek QML regresyonu | timeseries-frequency, timeseries-seasonality, timeseries-lag, timeseries-validation | F21-S001, F21-S002, F21-S003, F21-S004, F21-S005, F21-S006; 20 modül vakası; JSON tarif/sonuç; fitted paket yalnız F20 allowlist | rows=100000, groups=20, horizon=60; E; docs/evidence/PHASE21.md + tanık JSON |
| text.inspect: local_text_analysis | DatasetVersion/v7 + String/Null column → TextRun/v1; src/veri_ufku/analytics/text.py | TextPanel.qml; Faz22 gerçek QML regresyonu | text-tokens, text-language, text-tfidf, text-similarity | F22-S001, F22-S002, F22-S003, F22-S004, F22-S005, F22-S006; 11 modül vakası; JSON tarif + immutable Parquet | rows=100000, candidate_vocab=50000, ngram_max=3; E; docs/evidence/PHASE22.md + tanık JSON |
| workflow.recipe: declarative_replay | DatasetVersion/v7 + AnalysisRecipe/v1 → RecipeDryRun/v1 + DatasetChange/v1 + DelayedPerformance/v1; src/veri_ufku/operations/recipes.py | RecipePanel.qml; Faz23 gerçek QML regresyonu | workflow-recipe, workflow-drift, workflow-model | F23-S001, F23-S002, F23-S003, F23-S004, F23-S005, F23-S006; 21 modül vakası; JSON tarif + immutable Parquet | steps=100, recipe_bytes=2097152, monitor_rows=100000; E; docs/evidence/PHASE23.md + tanık JSON |

## Model başına gerçek destek

CPU-only; weights GUI tarafından desteklenmez, grup/zaman değerlendirmesi ortak ValidationPlan üzerinden; modelin grup etkisi veya zaman serisi estimator olduğu anlamına gelmez. Fold içi fill/encode/scale/variance selection, missing dışlama kararı ve dense dönüşüm bütçesi korunur. Dense tabular / sparse text farkı test_text içinde ayrıca doğrulanmıştır; native estimator özelliği genel GUI garantisi değildir.

| Model | Predict / proba / interval | Serialization | Boyut / doğrulama | Kanıt / kayıt |
|---|---|---|---|---|
| DummyRegressor | predict var; proba yok; interval yok | F20 .vumodel, allowlist/exact backend sürümü; yeni veride fit=0 | 100k; tabular dense≤4m hücre; unsupervised≤20 özellik (IQR1); train-only/group-time yalnız etiketli model | F20-M001; test_lifecycle roundtrip + F17/18/19 GUI; pytest.xml |
| LinearRegression | predict var; proba yok; interval yok | F20 .vumodel, allowlist/exact backend sürümü; yeni veride fit=0 | 100k; tabular dense≤4m hücre; unsupervised≤20 özellik (IQR1); train-only/group-time yalnız etiketli model | F20-M002; test_lifecycle roundtrip + F17/18/19 GUI; pytest.xml |
| Ridge | predict var; proba yok; interval yok | F20 .vumodel, allowlist/exact backend sürümü; yeni veride fit=0 | 100k; tabular dense≤4m hücre; unsupervised≤20 özellik (IQR1); train-only/group-time yalnız etiketli model | F20-M003; test_lifecycle roundtrip + F17/18/19 GUI; pytest.xml |
| RandomForestRegressor | predict var; proba yok; interval yok | F20 .vumodel, allowlist/exact backend sürümü; yeni veride fit=0 | 20k; tabular dense≤4m hücre; unsupervised≤20 özellik (IQR1); train-only/group-time yalnız etiketli model | F20-M004; test_lifecycle roundtrip + F17/18/19 GUI; pytest.xml |
| DummyClassifier | predict var; proba destekli; kalibre değildir; interval yok | F20 .vumodel, allowlist/exact backend sürümü; yeni veride fit=0 | 100k; tabular dense≤4m hücre; unsupervised≤20 özellik (IQR1); train-only/group-time yalnız etiketli model | F20-M005; test_lifecycle roundtrip + F17/18/19 GUI; pytest.xml |
| LogisticRegression | predict var; proba destekli; kalibre değildir; interval yok | F20 .vumodel, allowlist/exact backend sürümü; yeni veride fit=0 | 100k; tabular dense≤4m hücre; unsupervised≤20 özellik (IQR1); train-only/group-time yalnız etiketli model | F20-M006; test_lifecycle roundtrip + F17/18/19 GUI; pytest.xml |
| RandomForestClassifier | predict var; proba destekli; kalibre değildir; interval yok | F20 .vumodel, allowlist/exact backend sürümü; yeni veride fit=0 | 20k; tabular dense≤4m hücre; unsupervised≤20 özellik (IQR1); train-only/group-time yalnız etiketli model | F20-M007; test_lifecycle roundtrip + F17/18/19 GUI; pytest.xml |
| KMeans | predict var; proba yok; interval yok | F20 .vumodel, allowlist/exact backend sürümü; yeni veride fit=0 | 100k; tabular dense≤4m hücre; unsupervised≤20 özellik (IQR1); train-only/group-time yalnız etiketli model | F20-M008; test_lifecycle roundtrip + F17/18/19 GUI; pytest.xml |
| IsolationForest | predict var; proba yok; interval yok | F20 .vumodel, allowlist/exact backend sürümü; yeni veride fit=0 | 100k; tabular dense≤4m hücre; unsupervised≤20 özellik (IQR1); train-only/group-time yalnız etiketli model | F20-M009; test_lifecycle roundtrip + F17/18/19 GUI; pytest.xml |
| IQRBounds | predict var; proba yok; interval yok | F20 .vumodel, allowlist/exact backend sürümü; yeni veride fit=0 | 100k; tabular dense≤4m hücre; unsupervised≤20 özellik (IQR1); train-only/group-time yalnız etiketli model | F20-M010; test_lifecycle roundtrip + F17/18/19 GUI; pytest.xml |
| DBSCAN | yeni veri predict/proba/interval yok | fitted model paketi reddedilir; sonuç JSON saklanır | ≤3000, n² distance önkontrolü | F20-M011; test_dbscan_unsupported_save_explicitly_blocked; test_unsupervised_gui |

F21 naive/seasonal-naive/ExponentialSmoothing sonuç/üyelik JSON kaydı vardır; genel F20 fitted paket desteği yok, interval=null. F22 sparse TF-IDF classification fold içinde öğrenilir; vocab/IDF test verisinden fit edilmez. F23 recipe yeniden çalıştırma fitted modeli yeniden eğitmez. F53/F54/F55/F62/F63/F64/F67 giriş kabulüne bağlı kalır.

## Teknik beyan boşlukları ve mevcut olmayanlar

Mevcut Capability bool tuple şeması istatistikte grup ve classification’da proba gibi bazı gerçek davranışları ayrı alanla tam ifade etmiyor. Örneğin model.classification supports tuple’ında proba yokken lifecycle/classification testleri proba’yı doğruluyor; bulunmayan alanı false sanıp veya kütüphaneden tahmin edip doldurmadık. F29-P001.C/V mevcut kayıt üstünde yöntem bazında gerçek alanlara geçiş yapmalı. Fiziksel dtype, sparse/dense, ağırlık türü, group/time, predict/proba/interval, persistence, determinism ve CPU/GPU bu geçişin zorunlu boyutlarıdır.

GPU, dağıtık executor, uzaktan connector, dashboard composer, arbitrary Python/notebook, plugin SDK, yeni uzman istatistik/model/grafikler mevcut değildir. [552 planlı yöntem/alt yetenek](PRO_WORK_PLAN.md) ana matriste F29-P001…F75-Pnnn kimlikleriyle mevcut değil/doğrulanmadı ve isteğe bağlıdır; her biri C/V/G/H/P alt kapısına bağlıdır. Ders başlığı mevcut olması çalışan analitik yöntem sayılmaz.

## Önceki faz düzeltme sırası

| Kimlik | Öncelik | Açık sorun / kapanış kanıtı | Bağımlı gelişim |
|---|---|---|---|
| DEP-28-01 | P1 | Kaynak checksum izlenebilirliği; DEC-28-03 eklemeyi çıkarınca orijinal hash eşit; negatif testler | Belge kapısı; onarıldı, PHASE28 final kontrolü |
| DEP-28-02 | P1 | F13-S005 gerçek bilgisiz kullanıcı ve uzman görev kaydı; başarı/yardım/kritik hata | Faz28 ve tüm profesyonel uygulama |
| DEP-28-03 | P1 | F25 insan/Orca AT, tamamlanmış güncel temel çeviri; kaldırılan kontrolleri eski testte etkin sayma | Faz25/26/27/28 |
| DEP-28-04 | P1 | F24-S006 fiziksel4core/8GiB/cold/input-frame; hedef ile actual ayrı | Faz24/27/28 |
| DEP-28-05 | P1 | Faz27 kullanıcı tarafından durduruldu, Flatpak seçimi iptal; seçilmiş gerçek paket + temiz hedef + import/clean/chart/report | Faz27/28/74 |
| DEP-28-06 | P2 | GUI ResourceSupervisor jobs altında; yalnız app.py import ediyor. UI katmanına taşıma gelecekte regression ile | Mimari adlandırma; kritik veri kaybı değil |
| DEP-28-07 | P2 | Capability alanları yöntem başına eksik; InputSchema/ResultArtifact/LearningLink normatif plan gerçek tip sanılmamalı | F29 mevcut sözleşme genişlemesi |
| DEP-28-08 | P2 | Eski walkthrough betikleri kaldırılmış GUI kontrollerine başvuruyor (profileMethod/helpButton) | Güncel audit testleri geçti; eski scriptler yeni kabul değildir |

Çalıştırılan veri bütünlüğü/fit-spy/poison/grup-zaman/RowId/atomik yayın vakalarında yeni P0 saptanmadı; bu sınırlı test iddiasıdır. Çözümsüz P0 ortaya çıkarsa ayrıca DEP-28-CRITICAL-* kaydı ve bağımlı faz engeli zorunlu; genel başarıyla kapatılamaz.

## Faz29 registry genişlemesi

F29-S001..006/F29-P001..008: aynı CAPABILITIES76 kayıt üstünde contract_version2; InputSchema, parametre, destek ve ayrı işlem alanları.11 istatistik adaptörü ayrıntılı; diğer legacy kayıtlar unknown alanlarıyla dürüst kademeli geçiş. discovery/palette/favorite/preset/result GUI ve yöntem/sürüm readonly uyumluluğu [gerçek kanıtta](evidence/PHASE29.md). DEP-28-07 istatistik boyutunda giderildi; diğer ailelerin ayrıntılı adapter beyanları açık.


## Faz30 doğrulanan yerel import varyantları

DEC-30-01 yalnız Faz30 teknik geliştirmesidir. On adaptör aynı registry ve
worker/atomik publish yolundadır; [format başına gerçek fixture/QML witness
ve desteklenmeyen varyantlar](evidence/PHASE30.md#e30-formats). Strict/union
şema çözümü, sourcepart/hash/ordinal, SPSS/SAS/Stata metadata/user-missing ve
explicit ağırlık beyanı korunur; dictionary fiziksel değer+vocabulary scope
olarak saklanır. Gzip/ZIP1024 üye/512MiB, streaming kayıt10m; preview200,
ekran20. [Kesin temsil/sınırlar](adr/031-advanced-import-phase30.md).
Dokuz format10005 kayıt preview/cancel ile ölçüldü; SAS büyük fixture ölçülmedi.
Deneysel teknik destek, insan/AT/minimum donanım/dağıtım kabulü değildir.


2026-10-11 Faz30 teknik devamı: F30-S001..004/F30-P001..013 doğrulanan
varyantlar için matrise gerçek native/QML/help/publish-reopen C/V/G/H/P
witness'larıyla bağlandı. 761 pytest/14 kilitli unittest ve on format kurulu
wheel geçti; 211 paket dosyası kaynakla eşit. Dokuz10005 kayıt preview/iptal
ölçümü mevcut, SAS büyük ölçümü açık. Önceki faz kabulleri değiştirilmedi;
[kanıt ve sınırlar](evidence/PHASE30.md#e30-continuation).


Faz31 F31-P001..008: PostgreSQL18.6/MySQL8.4.11/MariaDB13.0.2 gerçek TLS
ordinary tablo, yerel DuckDB1.5.6 READ_ONLY, HTTPS JSON next sayfalama ve
SeaweedFS4.48 SigV4 tek nesne. Secret Service51.1 ayrı D-Bus/XDG tanığıdır.
Serbest SQL/interactive OAuth/çoklu nesne listing yok; API totalsiz/token'siz
tek-an veya eksiksizlik garantisi verilmez. [Tanıklar/sınırlar](evidence/PHASE31.md).


Faz32: operation.schema-contract/contract-check/entity-candidates/
category-candidates/entity-merge/category-map aynı registry'de profesyonel
InputSchema/Parameter/support/learning/artifact alanları taşır. Adaylarda
persist/transform desteklenmez; onaylı metadata/kalite/eşleme atomic publish
edilir. En fazla100 kural, tek referans sürümü/kontrol, entity20k kayıt/20k
karşılaştırma/200 aday, kategori200 benzersiz değer; sessiz truncation yok.
String fuzzy ve scalar aralık; serbest kod/SQL veya olasılık kalibrasyonu yok.
[Gerçek tanıklar](evidence/PHASE32.md), [sözleşme](adr/033-data-contracts-phase32.md).


Faz33 teknik kapsam DEC-33-01 ile zorunlu/deneysel. Eksiklik desenleri/gösterge, KNN/iterative, mean/OLS MI ve delta, üç sampling yolu, frequency/analytic/survey/sample_weight ayrı desteğe bağlı. F33-S001..004/P001..013 ana matriste; resmî kabuller ayrı. [Gerçek kanıt ve sınırlar](evidence/PHASE33.md).


Faz34: tek SourceAdapter/Capability registry içinde import.netcdf/import.zarr/import.hdf5-array; chart.array-heatmap/chart.array-profile. Metadata-first önkontrol, bounded lazy slice, ham CF takvim, kaynak kimlikleri, Pint affine dönüşümü ve mevcut ACTIVE yayını. NetCDF3/4, yerel Zarr2/3, HDF dimension scales; scalar numeric/fixed string,1–8 boyut,16MiB chunk/256KiB metadata; özel codec/link/CRS inference/hacim render yok. [Gerçek test ve sınırlar](evidence/PHASE34.md).

Faz35 aynı registry içinde chart.violin/kde/ecdf/rug/strip/swarm/qq/pp/error-bar/ci-band/missing-pattern ve mevcut histogram/box tariflerini genişletir. Parametreler, açık frequency/analytic ağırlık desteği, grup/facet, yardım ve artifact türleri kayıtlıdır. Survey/sample_weight ile desteklenmeyen grafik ağırlığı reddedilir. En fazla4 facet,5000 KDE örneği,500 swarm,10000 nokta; bin/bandwidth/normalizasyon ve SD/SE/CI hesabı kaynak fingerprint ve RowId üyelikleriyle saklanır. [Sınırlar ve gerçek kanıt](evidence/PHASE35.md), [ADR036](adr/036-distribution-charts-phase35.md).

## Faz40 model adapterları

DEC40-01; [kanıt](evidence/PHASE40.md), [ADR041](adr/041-statistical-models-phase40.md).
OLS/WLS nonrobust/HC3/cluster; binomial/Poisson/NB2 GLM nonrobust/HC0/cluster;
quantile robust/iid; Gaussian mixed nonrobust; balanced AnovaRM inference-only.
NB alpha sabit; mixed prediction marginal; repeated300 hücre/100 kişi.
Tam rank/VIF/residual/uygun BP-dispersion-Cook/convergence; safe JSON result/model
save desteği ayrı, prediction interval yok. Fiziksel/insan/AT kabulleri açık.

## Faz41 resampling adapterları

Observation/whole-cluster/time-block percentile; iid/cluster mean BCa.
Exchangeable two-label permutation / paired whole-unit sign-flip; exact≤10000
ve PCG64 MC+1 p/uncertainty. Mean/median/trim/raw MAD; açık outlier.
Explicit family testID/raw p: Holm/Bonferroni FWER, BH independent/PRDS FDR.
Filtre/outlier/missing-delta/alternatif ölçü descriptive sensitivity.
[Kanıt](evidence/PHASE41.md), [sınırlar](adr/042-resampling-phase41.md).


## Faz42 ilk bağımsız iki kol

TTestIndPower common-SD / NormalIndPower arcsine a priori power; yerel PCG64 Bernoulli draft; full-roster SRM; Welch mean / Fisher proportion ve konservatif CP-Bonferroni CI. ITT missing inference kapalı, PP association. Baseline/guardrail betimsel. Paired/cluster/factorial/sequential kapalı; [kanıt](evidence/PHASE42.md).

Faz50 DEC50-01 mevcut registry/BaselineRun/ValidationPlan/ProjectStore ve safe model
kartı/paketini genişletir: altı bounded native calibration/conformal/quantile
adapter ve10 C/V/G/H/P kayıt. CPU1000rows/32features; logistic/forest probability,
Ridge/forest residual interval, gradient50depth3 quantile/CQR; family/sparse/weights/
TF-IDF burada kapalı. Kalibrasyon ve eşik kaynak üyelikleri ayrı; final paketi
refit yapmadan kullanır. Group/time/horizon shared plan, implicit random CV yok.
Nominal marginal coverage yalnız exchangeability altında; future/subgroup
ve parametre CI garantisi yok. [Gerçek kapsam/kanıt](evidence/PHASE50.md).

Faz51 DEC51-01 single registry/Baseline model/Lifecycle/ComputeBudget/Provenance/
ProjectStore extends: permutation, PDP/ICE, exactlinear local mapping/reference,
error slices/binaryfairness, constrainedfinite/what-if and safe maskedJSON export.
5000source/500sample/100background/16features/300000predictionrowpass; group/time
uncertainty disables iidCI. Same model snapshot validation vs fit-row background,
no finaltest/fit; otherbackground/finalrefitted/externalmodel here closed. Optional
SHAP typed exact adapter absent/notvalidated; no ready claim. Native local-linear
not SHAP, contributions not causality; sensitive chosen explicitly, no fair badge.
[Kanıt/kapsam](evidence/PHASE51.md),[ADR052](adr/052-explanation-phase51.md).

Faz52 DEC52-01: mevcut run/test defteri üzerinde yerel registry; bounded native yol ve sınırlar [kanıt](evidence/PHASE52.md). Optional tracking unconfigured/notvalidated; fiziksel silme kapalı, arşiv disk boşaltmaz.

Faz53 DEC53-01 native temporal slice:19 capabilities,chronological/panel/availability/MASE/proper forecast scores, safeJSON/journal;[kanıt](evidence/PHASE53.md). Formal prior gates separate; bounded templates/out-of-source prediction limitations explicit.

Faz54 DEC54-01 regular signal ve recording blok pencereleri:13 bounded native template teknik doğrulandı; resmî kabul ayrı. Offline zero-phase, amplitude/PSD/availability ve kaynak kimliği açık. [Kanıt](evidence/PHASE54.md);Faz55 yetkisi yok.

Faz55 DEC55-01 bounded native NLP:12 bounded native records teknik doğrulandı; resmî kabul ayrı; transformer/spaCy/ONNX unsupported. Static/literal/linear limits, original offset ve versioned human review açık. [Kanıt](evidence/PHASE55.md);Faz56 yetkisi yok.

Faz59 DEC59-01 bounded native CPU recommendation ve ayrı query-group ranking;
[gerçek kapsam/kanıt](evidence/PHASE59.md),[ADR060](adr/060-recommendation-phase59.md).
Tek registry/journal; resmî kabul ayrı; Faz60 başlatılmaz.

Faz60 DEC60-01 native bounded sepet/event/süreç keşfi; [kapsam/kanıt](evidence/PHASE60.md),[ADR061](adr/061-patterns-phase60.md). Resmî kabul ayrı, Faz61 başlatılmaz.

Faz61 DEC61-01 bounded native GraphML/GEXF ve NetworkX3.7: [kanıt](evidence/PHASE61.md),[ADR062](adr/062-graphs-phase61.md). Optional link prediction/embedding unavailable; resmî kabul ayrı, Faz62 başlatılmaz.

Faz62 DEC62-01 açık talimatla bounded local replay, incremental scaler/SGD, prequential/checkpoint ve ayrı özel hedefler; [kapsam/kanıt](evidence/PHASE62.md), [ADR063](adr/063-streams-phase62.md). PU/broker unavailable; default2GiB GUI kapısı açık,4GiB işlevsel test ayrı. Resmî kabul sürüyor/deneysel/isteğe bağlı; Faz63 başlatılmaz.

Faz63 DEC63-01: sınırlı numeric GUI profile Python/SQLite/notebook reference-only export ve explicit fresh Python process; [kanıt](evidence/PHASE63.md),[ADR064](adr/064-code-bridge-phase63.md). OS sandbox/managed Jupyter yok; resmî sürüyor/deneysel/isteğe bağlı, önceki kapılar korunur. Faz64 başlatılmaz.


Faz68 DEC68-01:6bounded native scenario capability; Monte Carlo/sensitivity, LP/MILP, bounded local SLSQP, frozen regression what-if/model-optimize. Genel copula/nested uncertainty/general code/GPU/remote solver yok. [Sınırlar ve kanıt](evidence/PHASE68.md). Önceki kabuller ayrı.


Faz69 DEC69-01:10bounded native synthetic teaching labs/8paths;403capability coverage (10interactive/393article-linked), advisory prerequisite and optional progress/self-check. [Kapsam/kanıt](evidence/PHASE69.md). Human/scientific/formal gates ayrı açık.


Faz70 DEC70-01: report.builder,32closed blocks,16columns/100preview rows; immutable source/result/artifact binding and review hash; built-in/saved presets, real MD/HTML/PDF/ZIP, SVG/PDF/CSV/Parquet and bounded reference-code attachment. DOCX/local LLM unsupported. [Kanıt](evidence/PHASE70.md).


Faz71 DEC71-01: share.bundle/diff/review/restore; üç bounded inclusion modu, pattern scan/preview, semantic category diff ve cross-origin identity collision, immutable human checklist. Full-copy opaque artifact kapalı; native validate ağır. Local-only single-writer, server/automatic merge yok. [Kanıt](evidence/PHASE71.md).

Faz72: privacy.scan/review/export/retention bounded desktop; kayıtlı ColumnId kararları, maskeli CSV/Parquet ZIP, optional HMAC/Fernet kernels, yalnız owned idle scratch cleanup. Live keyring/şifreli GUI unvalidated; DP ve canlı proje encryption yok. [E72](evidence/PHASE72.md), [ADR073](adr/073-privacy-phase72.md).

Faz73: plugin.sdk ve explicit namespaced Capability kayıtları, API1 six-kind data contracts; stat örneği gerçek UI/result/help/save. Diğer türler bounded data artifact, full native adapter değil; OS sandbox yok. [E73](evidence/PHASE73.md).


Faz74 DEC74-01: environment.inspect/profile/update-plan; core/extras lock closure,
explicit approved data-only report, cache bytes ve integrity-only update plan.
Flatpak core ve arrays/geospatial/CPU torch gerçek native paket yolları; ayrı worker
provisioning/offline installer/local extras installer yok. [E74](evidence/PHASE74.md).
Resmî kabul ve önceki açıklar ayrı; Faz75 başlatılmaz.

<!-- PHASE75 GENERATED AUDIT -->
## Faz75 güncel sınıflandırma — ana denetim tablosu

Bu bölüm güncel sınıflandırmadır; yukarıdaki Faz28 kayıtları tarihsel kapsamdır. Kararlı=bağımsız kabul gerektirir; bu denetim hiçbir yöntemi kararlıya yükseltmez. Deneysel=bounded teknik yol; eksik=mevcut değil/unknown/unsupported. Alt işlemlerden birinin eksikliği yöntem ailesini tamamlandı yapmaz. Test dosyası/GUI testi varlığı çalıştırılmış yöntem kabulü değildir.

[Makine denetimi ve kod/test hashleri](evidence/phase75/capability-audit.json), [gerçek koşular ve sınırlar](evidence/PHASE75.md). GUI tanığı yalnız karşılık gelen current JUnit case PASS ise bu koşuya aittir. Özel plugin session kayıtları static snapshot kapsamına girmez.

| Faz | Teknik sınıf | Resmî durum / kapsam | Kanıtlanmamış zorunlu sayısı |
|---|---|---|---|
| 00 | deneysel | doğrulandı / zorunlu | 0 |
| 01 | deneysel | doğrulandı / zorunlu | 0 |
| 02 | deneysel | doğrulandı / zorunlu | 0 |
| 03 | deneysel | doğrulandı / zorunlu | 0 |
| 04 | deneysel | doğrulandı / zorunlu | 0 |
| 05 | deneysel | doğrulandı / zorunlu | 0 |
| 06 | deneysel | doğrulandı / zorunlu | 0 |
| 07 | deneysel | doğrulandı / zorunlu | 0 |
| 08 | deneysel | doğrulandı / zorunlu | 0 |
| 09 | deneysel | doğrulandı / zorunlu | 0 |
| 10 | deneysel | doğrulandı / zorunlu | 0 |
| 11 | deneysel | doğrulandı / zorunlu | 0 |
| 12 | deneysel | doğrulandı / zorunlu | 0 |
| 13 | deneysel | sürüyor / zorunlu | 1 |
| 14 | deneysel | sürüyor / zorunlu | 0 |
| 15 | deneysel | sürüyor / zorunlu | 0 |
| 16 | deneysel | sürüyor / zorunlu | 0 |
| 17 | deneysel | sürüyor / zorunlu | 0 |
| 18 | deneysel | sürüyor / zorunlu | 0 |
| 19 | deneysel | sürüyor / zorunlu | 0 |
| 20 | deneysel | sürüyor / zorunlu | 0 |
| 21 | deneysel | sürüyor / zorunlu | 0 |
| 22 | deneysel | sürüyor / zorunlu | 0 |
| 23 | deneysel | sürüyor / zorunlu | 0 |
| 24 | deneysel | sürüyor / zorunlu | 1 |
| 25 | deneysel | sürüyor / zorunlu | 5 |
| 26 | deneysel | sürüyor / zorunlu | 0 |
| 27 | eksik | sürüyor / zorunlu | 7 |
| 28 | deneysel | engelli / zorunlu | 1 |
| 29 | deneysel | sürüyor / zorunlu | 0 |
| 30 | deneysel | sürüyor / zorunlu | 0 |
| 31 | deneysel | sürüyor / zorunlu | 0 |
| 32 | deneysel | sürüyor / zorunlu | 0 |
| 33 | deneysel | sürüyor / zorunlu | 0 |
| 34 | deneysel | sürüyor / zorunlu | 0 |
| 35 | deneysel | sürüyor / zorunlu | 0 |
| 36 | deneysel | sürüyor / zorunlu | 0 |
| 37 | deneysel | sürüyor / zorunlu | 0 |
| 38 | deneysel | sürüyor / zorunlu | 0 |
| 39 | deneysel | sürüyor / zorunlu | 0 |
| 40 | deneysel | sürüyor / zorunlu | 0 |
| 41 | deneysel | sürüyor / zorunlu | 0 |
| 42 | deneysel | sürüyor / zorunlu | 0 |
| 43 | deneysel | sürüyor / zorunlu | 0 |
| 44 | deneysel | sürüyor / zorunlu | 0 |
| 45 | deneysel | sürüyor / zorunlu | 0 |
| 46 | deneysel | sürüyor / zorunlu | 0 |
| 47 | deneysel | sürüyor / zorunlu | 0 |
| 48 | deneysel | sürüyor / zorunlu | 3 |
| 49 | deneysel | sürüyor / zorunlu | 1 |
| 50 | deneysel | sürüyor / zorunlu | 0 |
| 51 | deneysel | sürüyor / zorunlu | 1 |
| 52 | deneysel | sürüyor / zorunlu | 2 |
| 53 | deneysel | sürüyor / zorunlu | 0 |
| 54 | deneysel | sürüyor / zorunlu | 0 |
| 55 | deneysel | sürüyor / zorunlu | 0 |
| 56 | deneysel | sürüyor / isteğe bağlı | 0 |
| 57 | deneysel | sürüyor / isteğe bağlı | 0 |
| 58 | deneysel | sürüyor / isteğe bağlı | 1 |
| 59 | deneysel | sürüyor / isteğe bağlı | 0 |
| 60 | deneysel | sürüyor / isteğe bağlı | 0 |
| 61 | deneysel | sürüyor / isteğe bağlı | 0 |
| 62 | deneysel | sürüyor / isteğe bağlı | 0 |
| 63 | deneysel | sürüyor / isteğe bağlı | 0 |
| 64 | deneysel | sürüyor / isteğe bağlı | 0 |
| 65 | deneysel | sürüyor / isteğe bağlı | 0 |
| 66 | deneysel | sürüyor / isteğe bağlı | 1 |
| 67 | deneysel | sürüyor / isteğe bağlı | 0 |
| 68 | deneysel | sürüyor / isteğe bağlı | 0 |
| 69 | deneysel | sürüyor / isteğe bağlı | 0 |
| 70 | deneysel | sürüyor / isteğe bağlı | 0 |
| 71 | deneysel | sürüyor / isteğe bağlı | 0 |
| 72 | deneysel | sürüyor / isteğe bağlı | 2 |
| 73 | deneysel | sürüyor / isteğe bağlı | 1 |
| 74 | deneysel | sürüyor / isteğe bağlı | 4 |
| 75 | deneysel | sürüyor / isteğe bağlı | 6 |

### Her fazın alt gereksinimleri

Kaynak S ve plan P kayıtları aynen ana matrise bağlıdır. `doğrulanmadı` tamamlandı değildir. Engelli/ertelendi bağımsız açık kalır.

| Alt gereksinim | Sınıf | Doğrulama | Kapsam |
|---|---|---|---|
| F00-S001 | deneysel | doğrulandı | zorunlu |
| F00-S002 | deneysel | doğrulandı | zorunlu |
| F00-S003 | deneysel | doğrulandı | zorunlu |
| F00-S004 | deneysel | doğrulandı | zorunlu |
| F00-S005 | deneysel | doğrulandı | zorunlu |
| F00-S006 | deneysel | doğrulandı | zorunlu |
| F00-S007 | deneysel | doğrulandı | zorunlu |
| F01-S001 | deneysel | doğrulandı | zorunlu |
| F01-S002 | deneysel | doğrulandı | zorunlu |
| F01-S003 | deneysel | doğrulandı | zorunlu |
| F01-S004 | deneysel | doğrulandı | zorunlu |
| F01-S005 | deneysel | doğrulandı | zorunlu |
| F01-S006 | deneysel | doğrulandı | zorunlu |
| F02-S001 | deneysel | doğrulandı | zorunlu |
| F02-S002 | deneysel | doğrulandı | zorunlu |
| F02-S003 | deneysel | doğrulandı | zorunlu |
| F02-S004 | deneysel | doğrulandı | zorunlu |
| F02-S005 | deneysel | doğrulandı | zorunlu |
| F03-S001 | deneysel | doğrulandı | zorunlu |
| F03-S002 | deneysel | doğrulandı | zorunlu |
| F03-S003 | deneysel | doğrulandı | zorunlu |
| F03-S004 | deneysel | doğrulandı | zorunlu |
| F03-S005 | deneysel | doğrulandı | zorunlu |
| F03-S006 | deneysel | doğrulandı | zorunlu |
| F04-S001 | deneysel | doğrulandı | zorunlu |
| F04-S002 | deneysel | doğrulandı | zorunlu |
| F04-S003 | deneysel | doğrulandı | zorunlu |
| F04-S004 | deneysel | doğrulandı | zorunlu |
| F04-S005 | deneysel | doğrulandı | zorunlu |
| F04-S006 | deneysel | doğrulandı | zorunlu |
| F05-S001 | deneysel | doğrulandı | zorunlu |
| F05-S002 | deneysel | doğrulandı | zorunlu |
| F05-S003 | deneysel | doğrulandı | zorunlu |
| F05-S004 | deneysel | doğrulandı | zorunlu |
| F05-S005 | deneysel | doğrulandı | zorunlu |
| F05-S006 | deneysel | doğrulandı | zorunlu |
| F05-S007 | deneysel | doğrulandı | zorunlu |
| F06-S001 | deneysel | doğrulandı | zorunlu |
| F06-S002 | deneysel | doğrulandı | zorunlu |
| F06-S003 | deneysel | doğrulandı | zorunlu |
| F06-S004 | deneysel | doğrulandı | zorunlu |
| F06-S005 | deneysel | doğrulandı | zorunlu |
| F06-S006 | deneysel | doğrulandı | zorunlu |
| F06-S007 | deneysel | doğrulandı | zorunlu |
| F07-S001 | deneysel | doğrulandı | zorunlu |
| F07-S002 | deneysel | doğrulandı | zorunlu |
| F07-S003 | deneysel | doğrulandı | zorunlu |
| F07-S004 | deneysel | doğrulandı | zorunlu |
| F07-S005 | deneysel | doğrulandı | zorunlu |
| F07-S006 | deneysel | doğrulandı | zorunlu |
| F07-S007 | deneysel | doğrulandı | zorunlu |
| F08-S001 | deneysel | doğrulandı | zorunlu |
| F08-S002 | deneysel | doğrulandı | zorunlu |
| F08-S003 | deneysel | doğrulandı | zorunlu |
| F08-S004 | deneysel | doğrulandı | zorunlu |
| F08-S005 | deneysel | doğrulandı | zorunlu |
| F08-S006 | deneysel | doğrulandı | zorunlu |
| F09-S001 | deneysel | doğrulandı | zorunlu |
| F09-S002 | deneysel | doğrulandı | zorunlu |
| F09-S003 | deneysel | doğrulandı | zorunlu |
| F09-S004 | deneysel | doğrulandı | zorunlu |
| F09-S005 | deneysel | doğrulandı | zorunlu |
| F09-S006 | deneysel | doğrulandı | zorunlu |
| F09-S007 | deneysel | doğrulandı | zorunlu |
| F10-S001 | deneysel | doğrulandı | zorunlu |
| F10-S002 | deneysel | doğrulandı | zorunlu |
| F10-S003 | deneysel | doğrulandı | zorunlu |
| F10-S004 | deneysel | doğrulandı | zorunlu |
| F10-S005 | deneysel | doğrulandı | zorunlu |
| F10-S006 | deneysel | doğrulandı | zorunlu |
| F10-S007 | deneysel | doğrulandı | zorunlu |
| F10-S008 | deneysel | doğrulandı | zorunlu |
| F11-S001 | deneysel | doğrulandı | zorunlu |
| F11-S002 | deneysel | doğrulandı | zorunlu |
| F11-S003 | deneysel | doğrulandı | zorunlu |
| F11-S004 | deneysel | doğrulandı | zorunlu |
| F11-S005 | deneysel | doğrulandı | zorunlu |
| F11-S006 | deneysel | doğrulandı | zorunlu |
| F11-S007 | deneysel | doğrulandı | zorunlu |
| F12-S001 | deneysel | doğrulandı | zorunlu |
| F12-S002 | deneysel | doğrulandı | zorunlu |
| F12-S003 | deneysel | doğrulandı | zorunlu |
| F12-S004 | deneysel | doğrulandı | zorunlu |
| F12-S005 | deneysel | doğrulandı | zorunlu |
| F12-S006 | deneysel | doğrulandı | zorunlu |
| F12-S007 | deneysel | doğrulandı | zorunlu |
| F13-S001 | deneysel | doğrulandı | zorunlu |
| F13-S002 | deneysel | doğrulandı | zorunlu |
| F13-S003 | deneysel | doğrulandı | zorunlu |
| F13-S004 | deneysel | doğrulandı | zorunlu |
| F13-S005 | deneysel | doğrulanmadı | zorunlu |
| F13-S006 | deneysel | doğrulandı | zorunlu |
| F14-S001 | deneysel | doğrulandı | zorunlu |
| F14-S002 | deneysel | doğrulandı | zorunlu |
| F14-S003 | deneysel | doğrulandı | zorunlu |
| F14-S004 | deneysel | doğrulandı | zorunlu |
| F14-S005 | deneysel | doğrulandı | zorunlu |
| F14-S006 | deneysel | doğrulandı | zorunlu |
| F15-S001 | deneysel | doğrulandı | zorunlu |
| F15-S002 | deneysel | doğrulandı | zorunlu |
| F15-S003 | deneysel | doğrulandı | zorunlu |
| F15-S004 | deneysel | doğrulandı | zorunlu |
| F15-S005 | deneysel | doğrulandı | zorunlu |
| F15-S006 | deneysel | doğrulandı | zorunlu |
| F16-S001 | deneysel | doğrulandı | zorunlu |
| F16-S002 | deneysel | doğrulandı | zorunlu |
| F16-S003 | deneysel | doğrulandı | zorunlu |
| F16-S004 | deneysel | doğrulandı | zorunlu |
| F16-S005 | deneysel | doğrulandı | zorunlu |
| F16-S006 | deneysel | doğrulandı | zorunlu |
| F17-S001 | deneysel | doğrulandı | zorunlu |
| F17-S002 | deneysel | doğrulandı | zorunlu |
| F17-S003 | deneysel | doğrulandı | zorunlu |
| F17-S004 | deneysel | doğrulandı | zorunlu |
| F17-S005 | deneysel | doğrulandı | zorunlu |
| F17-S006 | deneysel | doğrulandı | zorunlu |
| F17-S007 | deneysel | doğrulandı | zorunlu |
| F18-S001 | deneysel | doğrulandı | zorunlu |
| F18-S002 | deneysel | doğrulandı | zorunlu |
| F18-S003 | deneysel | doğrulandı | zorunlu |
| F18-S004 | deneysel | doğrulandı | zorunlu |
| F18-S005 | deneysel | doğrulandı | zorunlu |
| F18-S006 | deneysel | doğrulandı | zorunlu |
| F18-S007 | deneysel | doğrulandı | zorunlu |
| F19-S001 | deneysel | doğrulandı | zorunlu |
| F19-S002 | deneysel | doğrulandı | zorunlu |
| F19-S003 | deneysel | doğrulandı | zorunlu |
| F19-S004 | deneysel | doğrulandı | zorunlu |
| F19-S005 | deneysel | doğrulandı | zorunlu |
| F19-S006 | deneysel | doğrulandı | zorunlu |
| F20-S001 | deneysel | doğrulandı | zorunlu |
| F20-S002 | deneysel | doğrulandı | zorunlu |
| F20-S003 | deneysel | doğrulandı | zorunlu |
| F20-S004 | deneysel | doğrulandı | zorunlu |
| F20-S005 | deneysel | doğrulandı | zorunlu |
| F20-S006 | deneysel | doğrulandı | zorunlu |
| F20-S007 | deneysel | doğrulandı | zorunlu |
| F21-S001 | deneysel | doğrulandı | zorunlu |
| F21-S002 | deneysel | doğrulandı | zorunlu |
| F21-S003 | deneysel | doğrulandı | zorunlu |
| F21-S004 | deneysel | doğrulandı | zorunlu |
| F21-S005 | deneysel | doğrulandı | zorunlu |
| F21-S006 | deneysel | doğrulandı | zorunlu |
| F22-S001 | deneysel | doğrulandı | zorunlu |
| F22-S002 | deneysel | doğrulandı | zorunlu |
| F22-S003 | deneysel | doğrulandı | zorunlu |
| F22-S004 | deneysel | doğrulandı | zorunlu |
| F22-S005 | deneysel | doğrulandı | zorunlu |
| F22-S006 | deneysel | doğrulandı | zorunlu |
| F23-S001 | deneysel | doğrulandı | zorunlu |
| F23-S002 | deneysel | doğrulandı | zorunlu |
| F23-S003 | deneysel | doğrulandı | zorunlu |
| F23-S004 | deneysel | doğrulandı | zorunlu |
| F23-S005 | deneysel | doğrulandı | zorunlu |
| F23-S006 | deneysel | doğrulandı | zorunlu |
| F24-S001 | deneysel | doğrulandı | zorunlu |
| F24-S002 | deneysel | doğrulandı | zorunlu |
| F24-S003 | deneysel | doğrulandı | zorunlu |
| F24-S004 | deneysel | doğrulandı | zorunlu |
| F24-S005 | deneysel | doğrulandı | zorunlu |
| F24-S006 | deneysel | doğrulanmadı | zorunlu |
| F25-S001 | deneysel | doğrulanmadı | zorunlu |
| F25-S002 | deneysel | doğrulanmadı | zorunlu |
| F25-S003 | deneysel | doğrulandı | zorunlu |
| F25-S004 | deneysel | doğrulanmadı | zorunlu |
| F25-S005 | deneysel | doğrulandı | zorunlu |
| F25-S006 | deneysel | doğrulanmadı | zorunlu |
| F25-S007 | deneysel | doğrulanmadı | zorunlu |
| F26-S001 | deneysel | doğrulandı | zorunlu |
| F26-S002 | deneysel | doğrulandı | zorunlu |
| F26-S003 | deneysel | doğrulandı | zorunlu |
| F26-S004 | deneysel | doğrulandı | zorunlu |
| F26-S005 | deneysel | doğrulandı | zorunlu |
| F26-S006 | deneysel | doğrulandı | zorunlu |
| F27-S001 | eksik | doğrulanmadı | zorunlu |
| F27-S002 | eksik | doğrulanmadı | zorunlu |
| F27-S003 | eksik | doğrulanmadı | zorunlu |
| F27-S004 | eksik | doğrulanmadı | zorunlu |
| F27-S005 | eksik | doğrulanmadı | zorunlu |
| F27-S006 | eksik | doğrulanmadı | zorunlu |
| F27-S007 | eksik | doğrulanmadı | zorunlu |
| F28-S001 | deneysel | doğrulandı | zorunlu |
| F28-S002 | deneysel | doğrulandı | zorunlu |
| F28-S003 | deneysel | doğrulandı | zorunlu |
| F28-S004 | deneysel | doğrulandı | zorunlu |
| F28-S005 | deneysel | doğrulanmadı | zorunlu |
| F28-S006 | deneysel | doğrulandı | zorunlu |
| F29-S001 | deneysel | doğrulandı | zorunlu |
| F29-S002 | deneysel | doğrulandı | zorunlu |
| F29-S003 | deneysel | doğrulandı | zorunlu |
| F29-S004 | deneysel | doğrulandı | zorunlu |
| F29-S005 | deneysel | doğrulandı | zorunlu |
| F29-S006 | deneysel | doğrulandı | zorunlu |
| F29-P001 | deneysel | doğrulandı | zorunlu |
| F29-P002 | deneysel | doğrulandı | zorunlu |
| F29-P003 | deneysel | doğrulandı | zorunlu |
| F29-P004 | deneysel | doğrulandı | zorunlu |
| F29-P005 | deneysel | doğrulandı | zorunlu |
| F29-P006 | deneysel | doğrulandı | zorunlu |
| F29-P007 | deneysel | doğrulandı | zorunlu |
| F29-P008 | deneysel | doğrulandı | zorunlu |
| F30-S001 | deneysel | doğrulandı | zorunlu |
| F30-S002 | deneysel | doğrulandı | zorunlu |
| F30-S003 | deneysel | doğrulandı | zorunlu |
| F30-S004 | deneysel | doğrulandı | zorunlu |
| F30-P001 | deneysel | doğrulandı | zorunlu |
| F30-P002 | deneysel | doğrulandı | zorunlu |
| F30-P003 | deneysel | doğrulandı | zorunlu |
| F30-P004 | deneysel | doğrulandı | zorunlu |
| F30-P005 | deneysel | doğrulandı | zorunlu |
| F30-P006 | deneysel | doğrulandı | zorunlu |
| F30-P007 | deneysel | doğrulandı | zorunlu |
| F30-P008 | deneysel | doğrulandı | zorunlu |
| F30-P009 | deneysel | doğrulandı | zorunlu |
| F30-P010 | deneysel | doğrulandı | zorunlu |
| F30-P011 | deneysel | doğrulandı | zorunlu |
| F30-P012 | deneysel | doğrulandı | zorunlu |
| F30-P013 | deneysel | doğrulandı | zorunlu |
| F31-S001 | deneysel | doğrulandı | zorunlu |
| F31-S002 | deneysel | doğrulandı | zorunlu |
| F31-S003 | deneysel | doğrulandı | zorunlu |
| F31-S004 | deneysel | doğrulandı | zorunlu |
| F31-S005 | deneysel | doğrulandı | zorunlu |
| F31-P001 | deneysel | doğrulandı | zorunlu |
| F31-P002 | deneysel | doğrulandı | zorunlu |
| F31-P003 | deneysel | doğrulandı | zorunlu |
| F31-P004 | deneysel | doğrulandı | zorunlu |
| F31-P005 | deneysel | doğrulandı | zorunlu |
| F31-P006 | deneysel | doğrulandı | zorunlu |
| F31-P007 | deneysel | doğrulandı | zorunlu |
| F31-P008 | deneysel | doğrulandı | zorunlu |
| F32-S001 | deneysel | doğrulandı | zorunlu |
| F32-S002 | deneysel | doğrulandı | zorunlu |
| F32-S003 | deneysel | doğrulandı | zorunlu |
| F32-S004 | deneysel | doğrulandı | zorunlu |
| F32-S005 | deneysel | doğrulandı | zorunlu |
| F32-P001 | deneysel | doğrulandı | zorunlu |
| F32-P002 | deneysel | doğrulandı | zorunlu |
| F32-P003 | deneysel | doğrulandı | zorunlu |
| F32-P004 | deneysel | doğrulandı | zorunlu |
| F32-P005 | deneysel | doğrulandı | zorunlu |
| F32-P006 | deneysel | doğrulandı | zorunlu |
| F32-P007 | deneysel | doğrulandı | zorunlu |
| F32-P008 | deneysel | doğrulandı | zorunlu |
| F33-S001 | deneysel | doğrulandı | zorunlu |
| F33-S002 | deneysel | doğrulandı | zorunlu |
| F33-S003 | deneysel | doğrulandı | zorunlu |
| F33-S004 | deneysel | doğrulandı | zorunlu |
| F33-P001 | deneysel | doğrulandı | zorunlu |
| F33-P002 | deneysel | doğrulandı | zorunlu |
| F33-P003 | deneysel | doğrulandı | zorunlu |
| F33-P004 | deneysel | doğrulandı | zorunlu |
| F33-P005 | deneysel | doğrulandı | zorunlu |
| F33-P006 | deneysel | doğrulandı | zorunlu |
| F33-P007 | deneysel | doğrulandı | zorunlu |
| F33-P008 | deneysel | doğrulandı | zorunlu |
| F33-P009 | deneysel | doğrulandı | zorunlu |
| F33-P010 | deneysel | doğrulandı | zorunlu |
| F33-P011 | deneysel | doğrulandı | zorunlu |
| F33-P012 | deneysel | doğrulandı | zorunlu |
| F33-P013 | deneysel | doğrulandı | zorunlu |
| F34-S001 | deneysel | doğrulandı | zorunlu |
| F34-S002 | deneysel | doğrulandı | zorunlu |
| F34-S003 | deneysel | doğrulandı | zorunlu |
| F34-S004 | deneysel | doğrulandı | zorunlu |
| F34-P001 | deneysel | doğrulandı | zorunlu |
| F34-P002 | deneysel | doğrulandı | zorunlu |
| F34-P003 | deneysel | doğrulandı | zorunlu |
| F34-P004 | deneysel | doğrulandı | zorunlu |
| F34-P005 | deneysel | doğrulandı | zorunlu |
| F34-P006 | deneysel | doğrulandı | zorunlu |
| F34-P007 | deneysel | doğrulandı | zorunlu |
| F34-P008 | deneysel | doğrulandı | zorunlu |
| F35-S001 | deneysel | doğrulandı | zorunlu |
| F35-S002 | deneysel | doğrulandı | zorunlu |
| F35-S003 | deneysel | doğrulandı | zorunlu |
| F35-S004 | deneysel | doğrulandı | zorunlu |
| F35-P001 | deneysel | doğrulandı | zorunlu |
| F35-P002 | deneysel | doğrulandı | zorunlu |
| F35-P003 | deneysel | doğrulandı | zorunlu |
| F35-P004 | deneysel | doğrulandı | zorunlu |
| F35-P005 | deneysel | doğrulandı | zorunlu |
| F35-P006 | deneysel | doğrulandı | zorunlu |
| F35-P007 | deneysel | doğrulandı | zorunlu |
| F35-P008 | deneysel | doğrulandı | zorunlu |
| F35-P009 | deneysel | doğrulandı | zorunlu |
| F35-P010 | deneysel | doğrulandı | zorunlu |
| F35-P011 | deneysel | doğrulandı | zorunlu |
| F35-P012 | deneysel | doğrulandı | zorunlu |
| F35-P013 | deneysel | doğrulandı | zorunlu |
| F35-P014 | deneysel | doğrulandı | zorunlu |
| F35-P015 | deneysel | doğrulandı | zorunlu |
| F36-S001 | deneysel | doğrulandı | zorunlu |
| F36-S002 | deneysel | doğrulandı | zorunlu |
| F36-S003 | deneysel | doğrulandı | zorunlu |
| F36-S004 | deneysel | doğrulandı | zorunlu |
| F36-P001 | deneysel | doğrulandı | zorunlu |
| F36-P002 | deneysel | doğrulandı | zorunlu |
| F36-P003 | deneysel | doğrulandı | zorunlu |
| F36-P004 | deneysel | doğrulandı | zorunlu |
| F36-P005 | deneysel | doğrulandı | zorunlu |
| F36-P006 | deneysel | doğrulandı | zorunlu |
| F36-P007 | deneysel | doğrulandı | zorunlu |
| F36-P008 | deneysel | doğrulandı | zorunlu |
| F36-P009 | deneysel | doğrulandı | zorunlu |
| F36-P010 | deneysel | doğrulandı | zorunlu |
| F36-P011 | deneysel | doğrulandı | zorunlu |
| F36-P012 | eksik | doğrulanmadı | isteğe bağlı |
| F36-P013 | eksik | doğrulanmadı | isteğe bağlı |
| F37-S001 | deneysel | doğrulandı | zorunlu |
| F37-S002 | deneysel | doğrulandı | zorunlu |
| F37-S003 | deneysel | doğrulandı | zorunlu |
| F37-S004 | deneysel | doğrulandı | zorunlu |
| F37-P001 | deneysel | doğrulandı | zorunlu |
| F37-P002 | deneysel | doğrulandı | zorunlu |
| F37-P003 | deneysel | doğrulandı | zorunlu |
| F37-P004 | deneysel | doğrulandı | zorunlu |
| F37-P005 | deneysel | doğrulandı | zorunlu |
| F37-P006 | deneysel | doğrulandı | zorunlu |
| F37-P007 | deneysel | doğrulandı | zorunlu |
| F37-P008 | deneysel | doğrulandı | zorunlu |
| F37-P009 | deneysel | doğrulandı | zorunlu |
| F37-P010 | deneysel | doğrulandı | zorunlu |
| F37-P011 | deneysel | doğrulandı | zorunlu |
| F37-P012 | deneysel | doğrulandı | zorunlu |
| F37-P013 | deneysel | doğrulandı | zorunlu |
| F37-P014 | deneysel | doğrulandı | zorunlu |
| F37-P015 | deneysel | doğrulandı | zorunlu |
| F37-P016 | deneysel | doğrulandı | zorunlu |
| F37-P017 | deneysel | doğrulandı | zorunlu |
| F38-S001 | deneysel | doğrulandı | zorunlu |
| F38-S002 | deneysel | doğrulandı | zorunlu |
| F38-S003 | deneysel | doğrulandı | zorunlu |
| F38-S004 | deneysel | doğrulandı | zorunlu |
| F38-P001 | deneysel | doğrulandı | zorunlu |
| F38-P002 | deneysel | doğrulandı | zorunlu |
| F38-P003 | deneysel | doğrulandı | zorunlu |
| F38-P004 | deneysel | doğrulandı | zorunlu |
| F38-P005 | deneysel | doğrulandı | zorunlu |
| F38-P006 | deneysel | doğrulandı | zorunlu |
| F38-P007 | deneysel | doğrulandı | zorunlu |
| F38-P008 | deneysel | doğrulandı | zorunlu |
| F38-P009 | deneysel | doğrulandı | zorunlu |
| F38-P010 | deneysel | doğrulandı | zorunlu |
| F38-P011 | deneysel | doğrulandı | zorunlu |
| F38-P012 | deneysel | doğrulandı | zorunlu |
| F38-P013 | deneysel | doğrulandı | zorunlu |
| F38-P014 | deneysel | doğrulandı | zorunlu |
| F38-P015 | deneysel | doğrulandı | zorunlu |
| F38-P016 | deneysel | doğrulandı | zorunlu |
| F38-P017 | deneysel | doğrulandı | zorunlu |
| F38-P018 | deneysel | doğrulandı | zorunlu |
| F38-P019 | deneysel | doğrulandı | zorunlu |
| F38-P020 | deneysel | doğrulandı | zorunlu |
| F39-S001 | deneysel | doğrulandı | zorunlu |
| F39-S002 | deneysel | doğrulandı | zorunlu |
| F39-S003 | deneysel | doğrulandı | zorunlu |
| F39-S004 | deneysel | doğrulandı | zorunlu |
| F39-P001 | deneysel | doğrulandı | isteğe bağlı |
| F39-P002 | deneysel | doğrulandı | isteğe bağlı |
| F39-P003 | deneysel | doğrulandı | isteğe bağlı |
| F39-P004 | deneysel | doğrulandı | isteğe bağlı |
| F39-P005 | deneysel | doğrulandı | isteğe bağlı |
| F39-P006 | deneysel | doğrulandı | isteğe bağlı |
| F39-P007 | deneysel | doğrulandı | isteğe bağlı |
| F39-P008 | deneysel | doğrulandı | isteğe bağlı |
| F40-S001 | deneysel | doğrulandı | zorunlu |
| F40-S002 | deneysel | doğrulandı | zorunlu |
| F40-S003 | deneysel | doğrulandı | zorunlu |
| F40-S004 | deneysel | doğrulandı | zorunlu |
| F40-P001 | deneysel | doğrulandı | isteğe bağlı |
| F40-P002 | deneysel | doğrulandı | isteğe bağlı |
| F40-P003 | deneysel | doğrulandı | isteğe bağlı |
| F40-P004 | deneysel | doğrulandı | isteğe bağlı |
| F40-P005 | deneysel | doğrulandı | isteğe bağlı |
| F40-P006 | deneysel | doğrulandı | isteğe bağlı |
| F40-P007 | deneysel | doğrulandı | isteğe bağlı |
| F40-P008 | deneysel | doğrulandı | isteğe bağlı |
| F40-P009 | deneysel | doğrulandı | isteğe bağlı |
| F40-P010 | deneysel | doğrulandı | isteğe bağlı |
| F40-P011 | deneysel | doğrulandı | isteğe bağlı |
| F40-P012 | deneysel | doğrulandı | isteğe bağlı |
| F40-P013 | deneysel | doğrulandı | isteğe bağlı |
| F41-S001 | deneysel | doğrulandı | zorunlu |
| F41-S002 | deneysel | doğrulandı | zorunlu |
| F41-S003 | deneysel | doğrulandı | zorunlu |
| F41-S004 | deneysel | doğrulandı | zorunlu |
| F41-P001 | deneysel | doğrulandı | isteğe bağlı |
| F41-P002 | deneysel | doğrulandı | isteğe bağlı |
| F41-P003 | deneysel | doğrulandı | isteğe bağlı |
| F41-P004 | deneysel | doğrulandı | isteğe bağlı |
| F41-P005 | deneysel | doğrulandı | isteğe bağlı |
| F41-P006 | deneysel | doğrulandı | isteğe bağlı |
| F41-P007 | deneysel | doğrulandı | isteğe bağlı |
| F41-P008 | deneysel | doğrulandı | isteğe bağlı |
| F41-P009 | deneysel | doğrulandı | isteğe bağlı |
| F41-P010 | deneysel | doğrulandı | isteğe bağlı |
| F41-P011 | deneysel | doğrulandı | isteğe bağlı |
| F42-S001 | deneysel | doğrulandı | zorunlu |
| F42-S002 | deneysel | doğrulandı | zorunlu |
| F42-S003 | deneysel | doğrulandı | zorunlu |
| F42-S004 | deneysel | doğrulandı | zorunlu |
| F42-P001 | deneysel | doğrulandı | isteğe bağlı |
| F42-P002 | eksik | doğrulanmadı | isteğe bağlı |
| F42-P003 | eksik | doğrulanmadı | isteğe bağlı |
| F42-P004 | eksik | doğrulanmadı | isteğe bağlı |
| F42-P005 | deneysel | doğrulandı | isteğe bağlı |
| F42-P006 | deneysel | doğrulandı | isteğe bağlı |
| F42-P007 | deneysel | doğrulandı | isteğe bağlı |
| F42-P008 | eksik | doğrulanmadı | isteğe bağlı |
| F42-P009 | eksik | doğrulanmadı | isteğe bağlı |
| F43-S001 | deneysel | doğrulandı | zorunlu |
| F43-S002 | deneysel | doğrulandı | zorunlu |
| F43-S003 | deneysel | doğrulandı | zorunlu |
| F43-S004 | deneysel | doğrulandı | zorunlu |
| F43-P001 | deneysel | doğrulandı | zorunlu |
| F43-P002 | deneysel | doğrulandı | zorunlu |
| F43-P003 | deneysel | doğrulandı | zorunlu |
| F43-P004 | deneysel | doğrulandı | zorunlu |
| F43-P005 | deneysel | doğrulandı | zorunlu |
| F43-P006 | deneysel | doğrulandı | zorunlu |
| F43-P007 | deneysel | doğrulandı | zorunlu |
| F43-P008 | deneysel | doğrulandı | zorunlu |
| F43-P009 | deneysel | doğrulandı | zorunlu |
| F43-P010 | deneysel | doğrulandı | zorunlu |
| F44-S001 | deneysel | doğrulandı | zorunlu |
| F44-S002 | deneysel | doğrulandı | zorunlu |
| F44-S003 | deneysel | doğrulandı | zorunlu |
| F44-S004 | deneysel | doğrulandı | zorunlu |
| F44-P001 | deneysel | doğrulandı | zorunlu |
| F44-P002 | deneysel | doğrulandı | zorunlu |
| F44-P003 | deneysel | doğrulandı | zorunlu |
| F44-P004 | deneysel | doğrulandı | zorunlu |
| F44-P005 | deneysel | doğrulandı | zorunlu |
| F44-P006 | deneysel | doğrulandı | zorunlu |
| F44-P007 | deneysel | doğrulandı | zorunlu |
| F44-P008 | deneysel | doğrulandı | zorunlu |
| F44-P009 | deneysel | doğrulandı | zorunlu |
| F44-P010 | deneysel | doğrulandı | zorunlu |
| F44-P011 | deneysel | doğrulandı | zorunlu |
| F45-S001 | deneysel | doğrulandı | zorunlu |
| F45-S002 | deneysel | doğrulandı | zorunlu |
| F45-S003 | deneysel | doğrulandı | zorunlu |
| F45-S004 | deneysel | doğrulandı | zorunlu |
| F45-P001 | deneysel | doğrulandı | zorunlu |
| F45-P002 | deneysel | doğrulandı | zorunlu |
| F45-P003 | deneysel | doğrulandı | zorunlu |
| F45-P004 | deneysel | doğrulandı | zorunlu |
| F45-P005 | deneysel | doğrulandı | zorunlu |
| F45-P006 | deneysel | doğrulandı | zorunlu |
| F45-P007 | deneysel | doğrulandı | zorunlu |
| F45-P008 | deneysel | doğrulandı | zorunlu |
| F45-P009 | deneysel | doğrulandı | zorunlu |
| F45-P010 | deneysel | doğrulandı | zorunlu |
| F45-P011 | deneysel | doğrulandı | zorunlu |
| F45-P012 | deneysel | doğrulandı | zorunlu |
| F45-P013 | deneysel | doğrulandı | zorunlu |
| F45-P014 | deneysel | doğrulandı | zorunlu |
| F46-S001 | deneysel | doğrulandı | zorunlu |
| F46-S002 | deneysel | doğrulandı | zorunlu |
| F46-S003 | deneysel | doğrulandı | zorunlu |
| F46-S004 | deneysel | doğrulandı | zorunlu |
| F46-P001 | deneysel | doğrulandı | zorunlu |
| F46-P002 | deneysel | doğrulandı | zorunlu |
| F46-P003 | deneysel | doğrulandı | zorunlu |
| F46-P004 | deneysel | doğrulandı | zorunlu |
| F46-P005 | deneysel | doğrulandı | zorunlu |
| F46-P006 | deneysel | doğrulandı | zorunlu |
| F46-P007 | deneysel | doğrulanmadı | isteğe bağlı |
| F46-P008 | deneysel | doğrulandı | zorunlu |
| F46-P009 | deneysel | doğrulandı | zorunlu |
| F46-P010 | deneysel | doğrulandı | zorunlu |
| F46-P011 | deneysel | doğrulandı | zorunlu |
| F46-P012 | deneysel | doğrulandı | zorunlu |
| F46-P013 | deneysel | doğrulandı | zorunlu |
| F47-S001 | deneysel | doğrulandı | zorunlu |
| F47-S002 | deneysel | doğrulandı | zorunlu |
| F47-S003 | deneysel | doğrulandı | zorunlu |
| F47-S004 | deneysel | doğrulandı | zorunlu |
| F47-P001 | deneysel | doğrulandı | zorunlu |
| F47-P002 | deneysel | doğrulandı | zorunlu |
| F47-P003 | deneysel | doğrulandı | zorunlu |
| F47-P004 | deneysel | doğrulandı | isteğe bağlı |
| F47-P005 | deneysel | doğrulandı | zorunlu |
| F47-P006 | deneysel | doğrulandı | zorunlu |
| F47-P007 | deneysel | doğrulandı | zorunlu |
| F47-P008 | deneysel | doğrulandı | zorunlu |
| F47-P009 | deneysel | doğrulandı | zorunlu |
| F47-P010 | deneysel | doğrulandı | zorunlu |
| F47-P011 | deneysel | doğrulandı | zorunlu |
| F47-P012 | deneysel | doğrulandı | zorunlu |
| F47-P013 | deneysel | doğrulandı | zorunlu |
| F47-P014 | deneysel | doğrulandı | zorunlu |
| F47-P015 | deneysel | doğrulandı | zorunlu |
| F47-P016 | deneysel | doğrulandı | zorunlu |
| F48-S001 | deneysel | doğrulanmadı | zorunlu |
| F48-S002 | deneysel | doğrulanmadı | zorunlu |
| F48-S003 | deneysel | doğrulandı | zorunlu |
| F48-S004 | deneysel | doğrulandı | zorunlu |
| F48-P001 | deneysel | doğrulandı | zorunlu |
| F48-P002 | deneysel | doğrulandı | zorunlu |
| F48-P003 | deneysel | doğrulandı | zorunlu |
| F48-P004 | deneysel | doğrulandı | zorunlu |
| F48-P005 | deneysel | doğrulandı | zorunlu |
| F48-P006 | deneysel | doğrulandı | zorunlu |
| F48-P007 | deneysel | doğrulandı | zorunlu |
| F48-P008 | deneysel | doğrulandı | zorunlu |
| F48-P009 | deneysel | doğrulandı | zorunlu |
| F48-P010 | deneysel | doğrulandı | zorunlu |
| F48-P011 | deneysel | doğrulandı | zorunlu |
| F48-P012 | deneysel | doğrulanmadı | isteğe bağlı |
| F48-P013 | deneysel | doğrulanmadı | isteğe bağlı |
| F48-P014 | deneysel | doğrulanmadı | isteğe bağlı |
| F48-P015 | deneysel | doğrulandı | zorunlu |
| F48-P016 | deneysel | doğrulandı | zorunlu |
| F48-P017 | deneysel | doğrulandı | zorunlu |
| F48-P018 | deneysel | doğrulanmadı | zorunlu |
| F48-P019 | deneysel | doğrulandı | zorunlu |
| F48-P020 | deneysel | doğrulandı | zorunlu |
| F49-S001 | deneysel | doğrulanmadı | zorunlu |
| F49-S002 | deneysel | doğrulandı | zorunlu |
| F49-S003 | deneysel | doğrulandı | zorunlu |
| F49-S004 | deneysel | doğrulandı | zorunlu |
| F49-S005 | deneysel | doğrulandı | zorunlu |
| F49-P001 | deneysel | doğrulandı | zorunlu |
| F49-P002 | deneysel | doğrulandı | zorunlu |
| F49-P003 | deneysel | doğrulanmadı | isteğe bağlı |
| F49-P004 | deneysel | doğrulandı | zorunlu |
| F49-P005 | deneysel | doğrulandı | zorunlu |
| F49-P006 | deneysel | doğrulandı | zorunlu |
| F49-P007 | deneysel | doğrulandı | zorunlu |
| F49-P008 | deneysel | doğrulandı | zorunlu |
| F49-P009 | deneysel | doğrulandı | zorunlu |
| F50-S001 | deneysel | doğrulandı | zorunlu |
| F50-S002 | deneysel | doğrulandı | zorunlu |
| F50-S003 | deneysel | doğrulandı | zorunlu |
| F50-S004 | deneysel | doğrulandı | zorunlu |
| F50-P001 | deneysel | doğrulandı | zorunlu |
| F50-P002 | deneysel | doğrulandı | zorunlu |
| F50-P003 | deneysel | doğrulandı | zorunlu |
| F50-P004 | deneysel | doğrulandı | zorunlu |
| F50-P005 | deneysel | doğrulandı | zorunlu |
| F50-P006 | deneysel | doğrulandı | zorunlu |
| F50-P007 | deneysel | doğrulandı | zorunlu |
| F50-P008 | deneysel | doğrulandı | zorunlu |
| F50-P009 | deneysel | doğrulandı | zorunlu |
| F50-P010 | deneysel | doğrulandı | zorunlu |
| F51-S001 | deneysel | doğrulanmadı | zorunlu |
| F51-S002 | deneysel | doğrulandı | zorunlu |
| F51-S003 | deneysel | doğrulandı | zorunlu |
| F51-S004 | deneysel | doğrulandı | zorunlu |
| F51-S005 | deneysel | doğrulandı | zorunlu |
| F51-P001 | deneysel | doğrulandı | zorunlu |
| F51-P002 | deneysel | doğrulandı | zorunlu |
| F51-P003 | deneysel | doğrulandı | zorunlu |
| F51-P004 | deneysel | doğrulanmadı | isteğe bağlı |
| F51-P005 | deneysel | doğrulandı | zorunlu |
| F51-P006 | deneysel | doğrulandı | zorunlu |
| F51-P007 | deneysel | doğrulandı | zorunlu |
| F51-P008 | deneysel | doğrulandı | zorunlu |
| F51-P009 | deneysel | doğrulandı | isteğe bağlı |
| F51-P010 | deneysel | doğrulandı | zorunlu |
| F52-S001 | deneysel | doğrulanmadı | zorunlu |
| F52-S002 | deneysel | doğrulandı | zorunlu |
| F52-S003 | deneysel | doğrulanmadı | zorunlu |
| F52-S004 | deneysel | doğrulandı | zorunlu |
| F52-S005 | deneysel | doğrulandı | zorunlu |
| F52-P001 | deneysel | doğrulandı | zorunlu |
| F52-P002 | deneysel | doğrulandı | zorunlu |
| F52-P003 | deneysel | doğrulandı | zorunlu |
| F52-P004 | deneysel | doğrulandı | zorunlu |
| F52-P005 | deneysel | doğrulandı | zorunlu |
| F52-P006 | deneysel | doğrulandı | zorunlu |
| F52-P007 | deneysel | doğrulandı | zorunlu |
| F52-P008 | eksik | doğrulanmadı | isteğe bağlı |
| F53-S001 | deneysel | doğrulandı | zorunlu |
| F53-S002 | deneysel | doğrulandı | zorunlu |
| F53-S003 | deneysel | doğrulandı | zorunlu |
| F53-S004 | deneysel | doğrulandı | zorunlu |
| F53-P001 | deneysel | doğrulandı | zorunlu |
| F53-P002 | deneysel | doğrulandı | zorunlu |
| F53-P003 | deneysel | doğrulandı | zorunlu |
| F53-P004 | deneysel | doğrulandı | zorunlu |
| F53-P005 | deneysel | doğrulandı | zorunlu |
| F53-P006 | deneysel | doğrulandı | zorunlu |
| F53-P007 | deneysel | doğrulandı | zorunlu |
| F53-P008 | deneysel | doğrulandı | zorunlu |
| F53-P009 | deneysel | doğrulandı | zorunlu |
| F53-P010 | deneysel | doğrulandı | zorunlu |
| F53-P011 | deneysel | doğrulandı | zorunlu |
| F53-P012 | deneysel | doğrulandı | zorunlu |
| F53-P013 | deneysel | doğrulandı | zorunlu |
| F53-P014 | deneysel | doğrulandı | zorunlu |
| F53-P015 | deneysel | doğrulandı | zorunlu |
| F53-P016 | deneysel | doğrulandı | zorunlu |
| F53-P017 | deneysel | doğrulandı | zorunlu |
| F53-P018 | deneysel | doğrulandı | zorunlu |
| F53-P019 | deneysel | doğrulandı | zorunlu |
| F54-S001 | deneysel | doğrulandı | zorunlu |
| F54-S002 | deneysel | doğrulandı | zorunlu |
| F54-S003 | deneysel | doğrulandı | zorunlu |
| F54-S004 | deneysel | doğrulandı | zorunlu |
| F54-P001 | deneysel | doğrulandı | zorunlu |
| F54-P002 | deneysel | doğrulandı | zorunlu |
| F54-P003 | deneysel | doğrulandı | zorunlu |
| F54-P004 | deneysel | doğrulandı | zorunlu |
| F54-P005 | deneysel | doğrulandı | zorunlu |
| F54-P006 | deneysel | doğrulandı | zorunlu |
| F54-P007 | deneysel | doğrulandı | zorunlu |
| F54-P008 | deneysel | doğrulandı | zorunlu |
| F54-P009 | deneysel | doğrulandı | zorunlu |
| F54-P010 | deneysel | doğrulandı | zorunlu |
| F54-P011 | deneysel | doğrulandı | zorunlu |
| F54-P012 | deneysel | doğrulandı | zorunlu |
| F54-P013 | deneysel | doğrulandı | zorunlu |
| F55-S001 | deneysel | doğrulandı | zorunlu |
| F55-S002 | deneysel | doğrulandı | zorunlu |
| F55-S003 | deneysel | doğrulandı | zorunlu |
| F55-S004 | deneysel | doğrulandı | zorunlu |
| F55-S005 | deneysel | doğrulandı | zorunlu |
| F55-P001 | deneysel | doğrulandı | zorunlu |
| F55-P002 | deneysel | doğrulandı | zorunlu |
| F55-P003 | deneysel | doğrulandı | zorunlu |
| F55-P004 | deneysel | doğrulandı | zorunlu |
| F55-P005 | deneysel | doğrulandı | zorunlu |
| F55-P006 | deneysel | doğrulandı | zorunlu |
| F55-P007 | deneysel | doğrulandı | zorunlu |
| F55-P008 | deneysel | doğrulandı | zorunlu |
| F55-P009 | deneysel | doğrulandı | zorunlu |
| F55-P010 | deneysel | doğrulandı | zorunlu |
| F55-P011 | deneysel | doğrulandı | zorunlu |
| F55-P012 | deneysel | doğrulandı | zorunlu |
| F56-S001 | deneysel | doğrulandı | zorunlu |
| F56-S002 | deneysel | doğrulandı | zorunlu |
| F56-S003 | deneysel | doğrulandı | zorunlu |
| F56-S004 | deneysel | doğrulandı | zorunlu |
| F56-P001 | deneysel | doğrulandı | isteğe bağlı |
| F56-P002 | deneysel | doğrulandı | isteğe bağlı |
| F56-P003 | deneysel | doğrulandı | isteğe bağlı |
| F56-P004 | deneysel | doğrulandı | isteğe bağlı |
| F56-P005 | eksik | doğrulanmadı | isteğe bağlı |
| F56-P006 | deneysel | doğrulandı | isteğe bağlı |
| F56-P007 | deneysel | doğrulandı | isteğe bağlı |
| F56-P008 | deneysel | doğrulandı | isteğe bağlı |
| F56-P009 | deneysel | doğrulandı | isteğe bağlı |
| F56-P010 | deneysel | doğrulandı | isteğe bağlı |
| F56-P011 | deneysel | doğrulandı | isteğe bağlı |
| F57-S001 | deneysel | doğrulandı | zorunlu |
| F57-S002 | deneysel | doğrulandı | zorunlu |
| F57-S003 | deneysel | doğrulandı | zorunlu |
| F57-S004 | deneysel | doğrulandı | zorunlu |
| F57-P001 | deneysel | doğrulandı | isteğe bağlı |
| F57-P002 | deneysel | doğrulandı | isteğe bağlı |
| F57-P003 | deneysel | doğrulandı | isteğe bağlı |
| F57-P004 | deneysel | doğrulandı | isteğe bağlı |
| F57-P005 | deneysel | doğrulandı | isteğe bağlı |
| F57-P006 | deneysel | doğrulandı | isteğe bağlı |
| F57-P007 | deneysel | doğrulandı | isteğe bağlı |
| F57-P008 | deneysel | doğrulandı | isteğe bağlı |
| F57-P009 | deneysel | doğrulandı | isteğe bağlı |
| F57-P010 | deneysel | doğrulandı | isteğe bağlı |
| F57-P011 | deneysel | doğrulandı | isteğe bağlı |
| F57-P012 | deneysel | doğrulandı | isteğe bağlı |
| F58-S001 | deneysel | doğrulandı | zorunlu |
| F58-S002 | deneysel | doğrulandı | zorunlu |
| F58-S003 | deneysel | doğrulanmadı | zorunlu |
| F58-S004 | deneysel | doğrulandı | zorunlu |
| F58-P001 | deneysel | doğrulandı | isteğe bağlı |
| F58-P002 | deneysel | doğrulandı | isteğe bağlı |
| F58-P003 | deneysel | doğrulandı | isteğe bağlı |
| F58-P004 | deneysel | doğrulandı | isteğe bağlı |
| F58-P005 | deneysel | doğrulandı | isteğe bağlı |
| F58-P006 | deneysel | doğrulandı | isteğe bağlı |
| F58-P007 | deneysel | doğrulandı | isteğe bağlı |
| F58-P008 | deneysel | doğrulandı | isteğe bağlı |
| F58-P009 | deneysel | doğrulandı | isteğe bağlı |
| F58-P010 | deneysel | doğrulanmadı | isteğe bağlı |
| F58-P011 | deneysel | doğrulanmadı | isteğe bağlı |
| F58-P012 | deneysel | doğrulandı | isteğe bağlı |
| F58-P013 | deneysel | doğrulandı | isteğe bağlı |
| F58-P014 | eksik | doğrulanmadı | isteğe bağlı |
| F58-P015 | eksik | doğrulanmadı | isteğe bağlı |
| F58-P016 | eksik | doğrulanmadı | isteğe bağlı |
| F59-S001 | deneysel | doğrulandı | zorunlu |
| F59-S002 | deneysel | doğrulandı | zorunlu |
| F59-S003 | deneysel | doğrulandı | zorunlu |
| F59-S004 | deneysel | doğrulandı | zorunlu |
| F59-P001 | deneysel | doğrulandı | isteğe bağlı |
| F59-P002 | deneysel | doğrulandı | isteğe bağlı |
| F59-P003 | deneysel | doğrulandı | isteğe bağlı |
| F59-P004 | deneysel | doğrulandı | isteğe bağlı |
| F59-P005 | deneysel | doğrulandı | isteğe bağlı |
| F59-P006 | deneysel | doğrulandı | isteğe bağlı |
| F59-P007 | deneysel | doğrulandı | isteğe bağlı |
| F59-P008 | deneysel | doğrulandı | isteğe bağlı |
| F59-P009 | deneysel | doğrulandı | isteğe bağlı |
| F59-P010 | deneysel | doğrulandı | isteğe bağlı |
| F59-P011 | deneysel | doğrulandı | isteğe bağlı |
| F59-P012 | deneysel | doğrulandı | isteğe bağlı |
| F60-S001 | deneysel | doğrulandı | zorunlu |
| F60-S002 | deneysel | doğrulandı | zorunlu |
| F60-S003 | deneysel | doğrulandı | zorunlu |
| F60-S004 | deneysel | doğrulandı | zorunlu |
| F60-S005 | deneysel | doğrulandı | zorunlu |
| F60-P001 | deneysel | doğrulandı | isteğe bağlı |
| F60-P002 | deneysel | doğrulandı | isteğe bağlı |
| F60-P003 | deneysel | doğrulandı | isteğe bağlı |
| F60-P004 | deneysel | doğrulandı | isteğe bağlı |
| F60-P005 | deneysel | doğrulandı | isteğe bağlı |
| F60-P006 | deneysel | doğrulandı | isteğe bağlı |
| F60-P007 | deneysel | doğrulandı | isteğe bağlı |
| F60-P008 | deneysel | doğrulandı | isteğe bağlı |
| F60-P009 | deneysel | doğrulandı | isteğe bağlı |
| F60-P010 | deneysel | doğrulandı | isteğe bağlı |
| F60-P011 | deneysel | doğrulandı | isteğe bağlı |
| F61-S001 | deneysel | doğrulandı | zorunlu |
| F61-S002 | deneysel | doğrulandı | zorunlu |
| F61-S003 | deneysel | doğrulandı | zorunlu |
| F61-S004 | deneysel | doğrulandı | zorunlu |
| F61-P001 | deneysel | doğrulandı | isteğe bağlı |
| F61-P002 | deneysel | doğrulandı | isteğe bağlı |
| F61-P003 | deneysel | doğrulandı | isteğe bağlı |
| F61-P004 | deneysel | doğrulandı | isteğe bağlı |
| F61-P005 | deneysel | doğrulandı | isteğe bağlı |
| F61-P006 | deneysel | doğrulandı | isteğe bağlı |
| F61-P007 | deneysel | doğrulandı | isteğe bağlı |
| F61-P008 | deneysel | doğrulandı | isteğe bağlı |
| F61-P009 | deneysel | doğrulandı | isteğe bağlı |
| F61-P010 | eksik | doğrulanmadı | isteğe bağlı |
| F61-P011 | eksik | doğrulanmadı | isteğe bağlı |
| F61-P012 | deneysel | doğrulandı | isteğe bağlı |
| F62-S001 | deneysel | doğrulandı | zorunlu |
| F62-S002 | deneysel | doğrulandı | zorunlu |
| F62-S003 | deneysel | doğrulandı | zorunlu |
| F62-S004 | deneysel | doğrulandı | zorunlu |
| F62-P001 | deneysel | doğrulandı | isteğe bağlı |
| F62-P002 | deneysel | doğrulandı | isteğe bağlı |
| F62-P003 | deneysel | doğrulandı | isteğe bağlı |
| F62-P004 | deneysel | doğrulandı | isteğe bağlı |
| F62-P005 | deneysel | doğrulandı | isteğe bağlı |
| F62-P006 | deneysel | doğrulandı | isteğe bağlı |
| F62-P007 | deneysel | doğrulandı | isteğe bağlı |
| F62-P008 | deneysel | doğrulandı | isteğe bağlı |
| F62-P009 | deneysel | doğrulandı | isteğe bağlı |
| F62-P010 | deneysel | doğrulandı | isteğe bağlı |
| F62-P011 | eksik | doğrulanmadı | isteğe bağlı |
| F62-P012 | deneysel | doğrulandı | isteğe bağlı |
| F62-P013 | deneysel | doğrulandı | isteğe bağlı |
| F62-P014 | eksik | doğrulanmadı | isteğe bağlı |
| F63-S001 | deneysel | doğrulandı | zorunlu |
| F63-S002 | deneysel | doğrulandı | zorunlu |
| F63-S003 | deneysel | doğrulandı | zorunlu |
| F63-S004 | deneysel | doğrulandı | zorunlu |
| F63-P001 | deneysel | doğrulandı | isteğe bağlı |
| F63-P002 | deneysel | doğrulandı | isteğe bağlı |
| F63-P003 | deneysel | doğrulandı | isteğe bağlı |
| F63-P004 | deneysel | doğrulandı | isteğe bağlı |
| F63-P005 | deneysel | doğrulandı | isteğe bağlı |
| F63-P006 | deneysel | doğrulandı | isteğe bağlı |
| F63-P007 | deneysel | doğrulandı | isteğe bağlı |
| F63-P008 | eksik | doğrulanmadı | isteğe bağlı |
| F64-S001 | deneysel | doğrulandı | zorunlu |
| F64-S002 | deneysel | doğrulandı | zorunlu |
| F64-S003 | deneysel | doğrulandı | zorunlu |
| F64-S004 | deneysel | doğrulandı | zorunlu |
| F64-S005 | deneysel | doğrulandı | zorunlu |
| F64-P001 | deneysel | doğrulandı | isteğe bağlı |
| F64-P002 | deneysel | doğrulandı | isteğe bağlı |
| F64-P003 | deneysel | doğrulandı | isteğe bağlı |
| F64-P004 | deneysel | doğrulandı | isteğe bağlı |
| F64-P005 | deneysel | doğrulandı | isteğe bağlı |
| F64-P006 | deneysel | doğrulandı | isteğe bağlı |
| F64-P007 | deneysel | doğrulandı | isteğe bağlı |
| F64-P008 | deneysel | doğrulandı | isteğe bağlı |
| F64-P009 | eksik | doğrulanmadı | isteğe bağlı |
| F65-S001 | deneysel | doğrulandı | zorunlu |
| F65-S002 | deneysel | doğrulandı | zorunlu |
| F65-S003 | deneysel | doğrulandı | zorunlu |
| F65-S004 | deneysel | doğrulandı | zorunlu |
| F65-S005 | deneysel | doğrulandı | zorunlu |
| F65-P001 | deneysel | doğrulandı | isteğe bağlı |
| F65-P002 | deneysel | doğrulandı | isteğe bağlı |
| F65-P003 | deneysel | doğrulandı | isteğe bağlı |
| F65-P004 | deneysel | doğrulandı | isteğe bağlı |
| F65-P005 | deneysel | doğrulandı | isteğe bağlı |
| F65-P006 | deneysel | doğrulandı | isteğe bağlı |
| F65-P007 | deneysel | doğrulandı | isteğe bağlı |
| F65-P008 | deneysel | doğrulandı | isteğe bağlı |
| F65-P009 | deneysel | doğrulandı | isteğe bağlı |
| F66-S001 | deneysel | doğrulandı | zorunlu |
| F66-S002 | deneysel | doğrulandı | zorunlu |
| F66-S003 | deneysel | doğrulanmadı | zorunlu |
| F66-S004 | deneysel | doğrulandı | zorunlu |
| F66-S005 | deneysel | doğrulandı | zorunlu |
| F66-P001 | deneysel | doğrulandı | isteğe bağlı |
| F66-P002 | deneysel | doğrulandı | isteğe bağlı |
| F66-P003 | deneysel | doğrulandı | isteğe bağlı |
| F66-P004 | deneysel | doğrulandı | isteğe bağlı |
| F66-P005 | deneysel | doğrulandı | isteğe bağlı |
| F66-P006 | deneysel | doğrulanmadı | isteğe bağlı |
| F66-P007 | deneysel | doğrulanmadı | isteğe bağlı |
| F66-P008 | deneysel | doğrulanmadı | isteğe bağlı |
| F66-P009 | deneysel | doğrulandı | isteğe bağlı |
| F67-S001 | deneysel | doğrulandı | zorunlu |
| F67-S002 | deneysel | doğrulandı | zorunlu |
| F67-S003 | deneysel | doğrulandı | zorunlu |
| F67-S004 | deneysel | doğrulandı | zorunlu |
| F67-P001 | deneysel | doğrulandı | isteğe bağlı |
| F67-P002 | deneysel | doğrulandı | isteğe bağlı |
| F67-P003 | deneysel | doğrulandı | isteğe bağlı |
| F67-P004 | deneysel | doğrulandı | isteğe bağlı |
| F67-P005 | deneysel | doğrulandı | isteğe bağlı |
| F67-P006 | deneysel | doğrulandı | isteğe bağlı |
| F67-P007 | deneysel | doğrulandı | isteğe bağlı |
| F67-P008 | deneysel | doğrulandı | isteğe bağlı |
| F67-P009 | deneysel | doğrulandı | isteğe bağlı |
| F67-P010 | deneysel | doğrulandı | isteğe bağlı |
| F67-P011 | deneysel | doğrulandı | isteğe bağlı |
| F67-P012 | deneysel | doğrulandı | isteğe bağlı |
| F67-P013 | deneysel | doğrulandı | isteğe bağlı |
| F68-S001 | deneysel | doğrulandı | zorunlu |
| F68-S002 | deneysel | doğrulandı | zorunlu |
| F68-S003 | deneysel | doğrulandı | zorunlu |
| F68-S004 | deneysel | doğrulandı | zorunlu |
| F68-P001 | deneysel | doğrulandı | isteğe bağlı |
| F68-P002 | deneysel | doğrulandı | isteğe bağlı |
| F68-P003 | deneysel | doğrulandı | isteğe bağlı |
| F68-P004 | deneysel | doğrulandı | isteğe bağlı |
| F68-P005 | deneysel | doğrulandı | isteğe bağlı |
| F68-P006 | deneysel | doğrulandı | isteğe bağlı |
| F68-P007 | deneysel | doğrulandı | isteğe bağlı |
| F68-P008 | deneysel | doğrulandı | isteğe bağlı |
| F69-S001 | deneysel | doğrulandı | zorunlu |
| F69-S002 | deneysel | doğrulandı | zorunlu |
| F69-S003 | deneysel | doğrulandı | zorunlu |
| F69-S004 | deneysel | doğrulandı | zorunlu |
| F69-S005 | deneysel | doğrulandı | zorunlu |
| F69-P001 | deneysel | doğrulandı | isteğe bağlı |
| F69-P002 | deneysel | doğrulandı | isteğe bağlı |
| F69-P003 | deneysel | doğrulandı | isteğe bağlı |
| F69-P004 | deneysel | doğrulandı | isteğe bağlı |
| F69-P005 | deneysel | doğrulandı | isteğe bağlı |
| F69-P006 | deneysel | doğrulandı | isteğe bağlı |
| F69-P007 | deneysel | doğrulandı | isteğe bağlı |
| F69-P008 | deneysel | doğrulandı | isteğe bağlı |
| F69-P009 | deneysel | doğrulandı | isteğe bağlı |
| F69-P010 | deneysel | doğrulandı | isteğe bağlı |
| F69-P011 | deneysel | doğrulandı | isteğe bağlı |
| F70-S001 | deneysel | doğrulandı | zorunlu |
| F70-S002 | deneysel | doğrulandı | zorunlu |
| F70-S003 | deneysel | doğrulandı | zorunlu |
| F70-S004 | deneysel | doğrulandı | zorunlu |
| F70-P001 | deneysel | doğrulandı | isteğe bağlı |
| F70-P002 | deneysel | doğrulandı | isteğe bağlı |
| F70-P003 | deneysel | doğrulandı | isteğe bağlı |
| F70-P004 | deneysel | doğrulandı | isteğe bağlı |
| F70-P005 | deneysel | doğrulandı | isteğe bağlı |
| F70-P006 | deneysel | doğrulandı | isteğe bağlı |
| F70-P007 | eksik | doğrulanmadı | isteğe bağlı |
| F70-P008 | deneysel | doğrulandı | isteğe bağlı |
| F70-P009 | deneysel | doğrulandı | isteğe bağlı |
| F70-P010 | deneysel | doğrulandı | isteğe bağlı |
| F70-P011 | deneysel | doğrulandı | isteğe bağlı |
| F70-P012 | deneysel | doğrulandı | isteğe bağlı |
| F70-P013 | eksik | doğrulanmadı | isteğe bağlı |
| F71-S001 | deneysel | doğrulandı | zorunlu |
| F71-S002 | deneysel | doğrulandı | zorunlu |
| F71-S003 | deneysel | doğrulandı | zorunlu |
| F71-S004 | deneysel | doğrulandı | zorunlu |
| F71-S005 | deneysel | doğrulandı | zorunlu |
| F71-P001 | deneysel | doğrulandı | isteğe bağlı |
| F71-P002 | deneysel | doğrulandı | isteğe bağlı |
| F71-P003 | deneysel | doğrulandı | isteğe bağlı |
| F71-P004 | deneysel | doğrulandı | isteğe bağlı |
| F71-P005 | deneysel | doğrulandı | isteğe bağlı |
| F71-P006 | deneysel | doğrulandı | isteğe bağlı |
| F71-P007 | deneysel | doğrulandı | isteğe bağlı |
| F71-P008 | deneysel | doğrulandı | isteğe bağlı |
| F71-P009 | eksik | doğrulanmadı | isteğe bağlı |
| F72-S001 | deneysel | doğrulanmadı | zorunlu |
| F72-S002 | deneysel | doğrulandı | zorunlu |
| F72-S003 | deneysel | doğrulanmadı | zorunlu |
| F72-S004 | deneysel | doğrulandı | zorunlu |
| F72-P001 | deneysel | doğrulandı | isteğe bağlı |
| F72-P002 | deneysel | doğrulandı | isteğe bağlı |
| F72-P003 | deneysel | doğrulanmadı | isteğe bağlı |
| F72-P004 | deneysel | doğrulandı | isteğe bağlı |
| F72-P005 | deneysel | doğrulandı | isteğe bağlı |
| F72-P006 | deneysel | doğrulanmadı | isteğe bağlı |
| F72-P007 | deneysel | doğrulandı | isteğe bağlı |
| F72-P008 | deneysel | doğrulandı | isteğe bağlı |
| F72-P009 | eksik | doğrulanmadı | isteğe bağlı |
| F73-S001 | deneysel | doğrulanmadı | zorunlu |
| F73-S002 | deneysel | doğrulandı | zorunlu |
| F73-S003 | deneysel | doğrulandı | zorunlu |
| F73-S004 | deneysel | doğrulandı | zorunlu |
| F73-P001 | deneysel | doğrulanmadı | isteğe bağlı |
| F73-P002 | deneysel | doğrulanmadı | isteğe bağlı |
| F73-P003 | deneysel | doğrulandı | isteğe bağlı |
| F73-P004 | deneysel | doğrulanmadı | isteğe bağlı |
| F73-P005 | deneysel | doğrulanmadı | isteğe bağlı |
| F73-P006 | deneysel | doğrulanmadı | isteğe bağlı |
| F73-P007 | deneysel | doğrulandı | isteğe bağlı |
| F73-P008 | deneysel | doğrulandı | isteğe bağlı |
| F73-P009 | deneysel | doğrulandı | isteğe bağlı |
| F73-P010 | deneysel | doğrulandı | isteğe bağlı |
| F74-S001 | deneysel | doğrulandı | zorunlu |
| F74-S002 | deneysel | doğrulanmadı | zorunlu |
| F74-S003 | deneysel | doğrulanmadı | zorunlu |
| F74-S004 | deneysel | doğrulanmadı | zorunlu |
| F74-S005 | deneysel | doğrulanmadı | zorunlu |
| F74-S006 | deneysel | doğrulandı | zorunlu |
| F74-P001 | deneysel | doğrulandı | isteğe bağlı |
| F74-P002 | deneysel | doğrulanmadı | isteğe bağlı |
| F74-P003 | deneysel | doğrulandı | isteğe bağlı |
| F74-P004 | deneysel | doğrulandı | isteğe bağlı |
| F74-P005 | deneysel | doğrulandı | isteğe bağlı |
| F74-P006 | deneysel | doğrulanmadı | isteğe bağlı |
| F74-P007 | deneysel | doğrulanmadı | isteğe bağlı |
| F74-P008 | deneysel | doğrulanmadı | isteğe bağlı |
| F74-P009 | deneysel | doğrulandı | isteğe bağlı |
| F74-P010 | deneysel | doğrulanmadı | isteğe bağlı |
| F74-P011 | eksik | doğrulanmadı | isteğe bağlı |
| F74-P012 | eksik | doğrulanmadı | isteğe bağlı |
| F75-S001 | deneysel | doğrulanmadı | zorunlu |
| F75-S002 | deneysel | doğrulanmadı | zorunlu |
| F75-S003 | deneysel | doğrulanmadı | zorunlu |
| F75-S004 | deneysel | doğrulanmadı | zorunlu |
| F75-S005 | deneysel | doğrulanmadı | zorunlu |
| F75-S006 | deneysel | doğrulanmadı | zorunlu |
| F75-P001 | deneysel | doğrulanmadı | isteğe bağlı |
| F75-P002 | deneysel | doğrulanmadı | isteğe bağlı |
| F75-P003 | deneysel | doğrulanmadı | isteğe bağlı |
| F75-P004 | deneysel | doğrulanmadı | isteğe bağlı |
| F75-P005 | deneysel | doğrulanmadı | isteğe bağlı |
| F75-P006 | deneysel | doğrulanmadı | isteğe bağlı |
| F75-P007 | deneysel | doğrulanmadı | isteğe bağlı |
| F75-P008 | deneysel | doğrulanmadı | isteğe bağlı |
| F75-P009 | deneysel | doğrulanmadı | isteğe bağlı |
| F75-P010 | deneysel | doğrulanmadı | isteğe bağlı |
| F75-P011 | deneysel | doğrulanmadı | isteğe bağlı |
| F75-P012 | deneysel | doğrulanmadı | isteğe bağlı |
| F75-P013 | eksik | doğrulanmadı | isteğe bağlı |
| F75-P014 | eksik | doğrulanmadı | isteğe bağlı |
| F75-P015 | deneysel | doğrulanmadı | isteğe bağlı |

### Runtime yöntemleri ve alt işlem destekleri

JSON her method için backend/input/output/limits/assumptions/source/help/test/JUnit ve support_details ayrımını taşır. Aşağıdaki test sayısı phase-module ilişkisidir; direct bilimsel doğrulama sayısı değildir. `?` unknown ve `-` unsupported eksik kapsamdır.

| Capability | Sınıf | Faz | GUI test dosyası | Alt işlem desteği | Güncel ilişkili PASS/fail/skip |
|---|---|---|---|---|---|
| chart.alluvial | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.array-heatmap | deneysel | 34 | test_arrays_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.array-profile | deneysel | 34 | test_arrays_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.bar | deneysel | 12 | test_charts_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 8/2/0 |
| chart.box | deneysel | 35 | test_distributions_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.bubble | deneysel | 36 | test_multivariate_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.calendar | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.ci-band | deneysel | 35 | test_distributions_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.clustered-heatmap | deneysel | 36 | test_multivariate_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.conditional | deneysel | 36 | test_multivariate_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.correlation | deneysel | 12 | test_charts_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 8/2/0 |
| chart.density-2d | deneysel | 36 | test_multivariate_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.donut | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.dot | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.ecdf | deneysel | 35 | test_distributions_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.error-bar | deneysel | 35 | test_distributions_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.facets | deneysel | 36 | test_multivariate_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.funnel | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.grouped-heatmap | deneysel | 36 | test_multivariate_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.hexbin | deneysel | 36 | test_multivariate_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.histogram | deneysel | 35 | test_distributions_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.kde | deneysel | 35 | test_distributions_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.line | deneysel | 12 | test_charts_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 8/2/0 |
| chart.lollipop | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.map-choropleth | deneysel | 38 | test_geo_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 5/0/0 |
| chart.map-density | deneysel | 38 | test_geo_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 5/0/0 |
| chart.map-point | deneysel | 38 | test_geo_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 5/0/0 |
| chart.map-raster | deneysel | 38 | test_geo_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 5/0/0 |
| chart.missing | deneysel | 12 | test_charts_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 8/2/0 |
| chart.missing-pattern | deneysel | 35 | test_distributions_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.pair | deneysel | 36 | test_multivariate_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.parallel | deneysel | 36 | test_multivariate_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.pareto | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.percent-area | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.percent-bar | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.pie | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.pp | deneysel | 35 | test_distributions_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.qq | deneysel | 35 | test_distributions_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.radar | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.rug | deneysel | 35 | test_distributions_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.sankey | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.scatter | deneysel | 12 | test_charts_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 8/2/0 |
| chart.stacked-area | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.stacked-bar | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.strip | deneysel | 35 | test_distributions_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.sunburst | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.swarm | deneysel | 35 | test_distributions_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.treemap | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.violin | deneysel | 35 | test_distributions_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| chart.waterfall | deneysel | 37 | test_composition_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| code.jupyter | eksik | 63 | test_code_bridge_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| code.notebook | deneysel | 63 | test_code_bridge_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| code.python | deneysel | 63 | test_code_bridge_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| code.sql | deneysel | 63 | test_code_bridge_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| code.workspace | deneysel | 63 | test_code_bridge_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| compute.dask-summary | deneysel | 66 | test_compute_budget_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| dashboard.canvas | deneysel | 39 | test_dashboard_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| dataset.profile | deneysel | 07 | test_data_workspace_gui.py, test_dataset_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| dataset.quality | deneysel | 08 | test_quality_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| dataset.roles | deneysel | 07 | test_data_workspace_gui.py, test_dataset_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| dataset.view | deneysel | 07 | test_data_workspace_gui.py, test_dataset_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| demo.cpu | deneysel | 01 | test_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 18/0/0 |
| demo.failure | deneysel | 01 | test_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 18/0/0 |
| demo.io | deneysel | 01 | test_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 18/0/0 |
| demo.unknown | deneysel | 01 | test_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 18/0/0 |
| environment.inspect | deneysel | 74 | test_environment_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 9/0/0 |
| environment.profile | deneysel | 74 | test_environment_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 9/0/0 |
| environment.update-plan | deneysel | 74 | test_environment_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 9/0/0 |
| export.csv | deneysel | 13 | test_exports_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| export.html | deneysel | 13 | test_exports_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| export.json | deneysel | 13 | test_exports_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| export.jsonl | deneysel | 13 | test_exports_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| export.parquet | deneysel | 13 | test_exports_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| export.pdf | deneysel | 13 | test_exports_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| export.xlsx | deneysel | 13 | test_exports_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| figure.compose | deneysel | 39 | test_dashboard_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| import.arrow-dataset | deneysel | 30 | test_advanced_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.audio-dataset | deneysel | 58 | test_audio_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/1/0 |
| import.avro | deneysel | 30 | test_advanced_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.csv | deneysel | 05 | test_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.duckdb | deneysel | 31 | test_connector_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.fixed-width | deneysel | 30 | test_advanced_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.geocoding | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| import.geojson | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| import.geopackage | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| import.geoparquet | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| import.geotiff | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| import.gexf | deneysel | 61 | test_graphs_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 6/0/0 |
| import.graphml | deneysel | 61 | test_graphs_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 6/0/0 |
| import.hdf5 | deneysel | 30 | test_advanced_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.hdf5-array | deneysel | 34 | test_arrays_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.http | deneysel | 31 | test_connector_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.image-dataset | deneysel | 57 | test_vision_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 6/0/0 |
| import.ipc | deneysel | 11 | test_relational_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.ipc-stream | deneysel | 11 | test_relational_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.json | deneysel | 06 | test_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.jsonl | deneysel | 06 | test_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.mariadb | deneysel | 31 | test_connector_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.mysql | deneysel | 31 | test_connector_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.netcdf | deneysel | 34 | test_arrays_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.ods | deneysel | 11 | test_relational_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.orc | deneysel | 30 | test_advanced_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.parquet | deneysel | 06 | test_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.parquet-dataset | deneysel | 30 | test_advanced_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.postgresql | deneysel | 31 | test_connector_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.s3 | deneysel | 31 | test_connector_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.sas | deneysel | 30 | test_advanced_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.shapefile | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| import.spss | deneysel | 30 | test_advanced_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.sqlite | deneysel | 11 | test_relational_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.stata | deneysel | 30 | test_advanced_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.tile | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| import.tsv | deneysel | 05 | test_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.xlsx | deneysel | 06 | test_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.xml | deneysel | 30 | test_advanced_import_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| import.zarr | deneysel | 34 | test_arrays_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| learn.lab.calibration | deneysel | 69 | test_learning_lab_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 15/0/0 |
| learn.lab.ci | deneysel | 69 | test_learning_lab_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 15/0/0 |
| learn.lab.cleaning | deneysel | 69 | test_learning_lab_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 15/0/0 |
| learn.lab.confounding | deneysel | 69 | test_learning_lab_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 15/0/0 |
| learn.lab.histogram | deneysel | 69 | test_learning_lab_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 15/0/0 |
| learn.lab.leakage | deneysel | 69 | test_learning_lab_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 15/0/0 |
| learn.lab.mean-median | deneysel | 69 | test_learning_lab_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 15/0/0 |
| learn.lab.overfitting | deneysel | 69 | test_learning_lab_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 15/0/0 |
| learn.lab.sampling | deneysel | 69 | test_learning_lab_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 15/0/0 |
| learn.lab.time-series | deneysel | 69 | test_learning_lab_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 15/0/0 |
| model.agglomerative | deneysel | 19,47 | test_unsupervised_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.audio.classification | deneysel | 58 | test_audio_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/1/0 |
| model.audio.features | deneysel | 58 | test_audio_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/1/0 |
| model.audio.transcribe | deneysel | 58 | test_audio_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/1/0 |
| model.baseline | deneysel | 16 | test_validation_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 9/0/0 |
| model.classification | deneysel | 18 | test_classification_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.dbscan | deneysel | 19,47 | test_unsupervised_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.experiment-registry | deneysel | 52 | test_experiment_registry_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.explain.constrained | deneysel | 51 | test_explanation_gui.py | fit:- eksik, predict:E koşullu, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.explain.fairness | deneysel | 51 | test_explanation_gui.py | fit:- eksik, predict:E koşullu, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.explain.ice | deneysel | 51 | test_explanation_gui.py | fit:- eksik, predict:E koşullu, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.explain.local-linear | deneysel | 51 | test_explanation_gui.py | fit:- eksik, predict:E koşullu, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.explain.pdp | deneysel | 51 | test_explanation_gui.py | fit:- eksik, predict:E koşullu, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.explain.permutation | deneysel | 51 | test_explanation_gui.py | fit:- eksik, predict:E koşullu, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.explain.shap | deneysel | 51 | test_explanation_gui.py | fit:- eksik, predict:E koşullu, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.explain.slices | deneysel | 51 | test_explanation_gui.py | fit:- eksik, predict:E koşullu, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.explain.what-if | deneysel | 51 | test_explanation_gui.py | fit:- eksik, predict:E koşullu, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.classification.bagging | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:E koşullu, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.classification.catboost | deneysel | 48 | test_model_families_gui.py | fit:- eksik, predict:- eksik, proba:E koşullu, transform:- eksik, interval:- eksik, persist:- eksik | 0/0/0 |
| model.family.classification.decision-tree | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:E koşullu, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.classification.elasticnet | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:E koşullu, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.classification.extra-trees | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:E koşullu, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.classification.gaussian-nb | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:E koşullu, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.classification.gradient-boosting | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:E koşullu, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.classification.hist-gradient | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:E koşullu, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.classification.knn | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:E koşullu, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.classification.lasso | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:E koşullu, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.classification.lightgbm | deneysel | 48 | test_model_families_gui.py | fit:- eksik, predict:- eksik, proba:E koşullu, transform:- eksik, interval:- eksik, persist:- eksik | 0/0/0 |
| model.family.classification.multinomial-nb | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:E koşullu, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.classification.sgd | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:E koşullu, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.classification.stacking | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:E koşullu, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.classification.svm | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.classification.voting | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:E koşullu, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.classification.xgboost | deneysel | 48 | test_model_families_gui.py | fit:- eksik, predict:- eksik, proba:E koşullu, transform:- eksik, interval:- eksik, persist:- eksik | 0/0/0 |
| model.family.regression.bagging | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.regression.catboost | deneysel | 48 | test_model_families_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:- eksik | 0/0/0 |
| model.family.regression.decision-tree | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.regression.elasticnet | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.regression.extra-trees | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.regression.gradient-boosting | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.regression.hist-gradient | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.regression.knn | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.regression.lasso | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.regression.lightgbm | deneysel | 48 | test_model_families_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:- eksik | 0/0/0 |
| model.family.regression.sgd | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.regression.stacking | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.regression.svm | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.regression.voting | deneysel | 48 | test_model_families_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.family.regression.xgboost | deneysel | 48 | test_model_families_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:- eksik | 0/0/0 |
| model.gmm | deneysel | 19,47 | test_unsupervised_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.graph.centrality | deneysel | 61 | test_graphs_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 6/0/0 |
| model.graph.community | deneysel | 61 | test_graphs_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 6/0/0 |
| model.graph.components | deneysel | 61 | test_graphs_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 6/0/0 |
| model.graph.degree | deneysel | 61 | test_graphs_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 6/0/0 |
| model.graph.layout | deneysel | 61 | test_graphs_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 6/0/0 |
| model.graph.shortest | deneysel | 61 | test_graphs_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 6/0/0 |
| model.hdbscan | deneysel | 19,47 | test_unsupervised_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.iqr | deneysel | 19,47 | test_unsupervised_gui.py | fit:E, predict:E koşullu, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.isolation-forest | deneysel | 19,47 | test_unsupervised_gui.py | fit:E, predict:E koşullu, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.kmeans | deneysel | 19,47 | test_unsupervised_gui.py | fit:E, predict:E koşullu, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.lifecycle | deneysel | 20 | test_lifecycle_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 35/0/0 |
| model.lof | deneysel | 19,47 | test_unsupervised_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.monitor.api | deneysel | 67 | test_monitoring_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.monitor.batch | deneysel | 67 | test_monitoring_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.monitor.cli | deneysel | 67 | test_monitoring_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.monitor.route | deneysel | 67 | test_monitoring_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.neural.cnn | deneysel | 56 | test_neural_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.neural.mlp | deneysel | 56 | test_neural_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.one-class-svm | deneysel | 19,47 | test_unsupervised_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.optics | deneysel | 19,47 | test_unsupervised_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.pattern.apriori | deneysel | 60 | test_patterns_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.pattern.cohort | deneysel | 60 | test_patterns_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.pattern.conformance | deneysel | 60 | test_patterns_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.pattern.fp-growth | deneysel | 60 | test_patterns_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.pattern.funnel | deneysel | 60 | test_patterns_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.pattern.process | deneysel | 60 | test_patterns_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.prepare | deneysel | 15 | test_preparation_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.recommendation.content | deneysel | 59 | test_recommendation_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 11/0/0 |
| model.recommendation.factorization | deneysel | 59 | test_recommendation_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 11/0/0 |
| model.recommendation.popularity | deneysel | 59 | test_recommendation_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 11/0/0 |
| model.recommendation.ranker | deneysel | 59 | test_recommendation_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 11/0/0 |
| model.regression | deneysel | 17 | test_regression_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.robust-covariance | deneysel | 19,47 | test_unsupervised_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| model.search.bayesian | deneysel | 49 | test_search_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:- eksik | 23/0/0 |
| model.search.grid | deneysel | 49 | test_search_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 23/0/0 |
| model.search.random | deneysel | 49 | test_search_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 23/0/0 |
| model.signal.classification | deneysel | 54 | test_signals_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.signal.detrend | deneysel | 54 | test_signals_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.signal.events | deneysel | 54 | test_signals_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.signal.fft | deneysel | 54 | test_signals_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.signal.filter | deneysel | 54 | test_signals_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.signal.peak | deneysel | 54 | test_signals_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.signal.resample | deneysel | 54 | test_signals_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.signal.schema | deneysel | 54 | test_signals_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.signal.spectrogram | deneysel | 54 | test_signals_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.signal.stft | deneysel | 54 | test_signals_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.signal.welch | deneysel | 54 | test_signals_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.signal.window | deneysel | 54 | test_signals_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.signal.zero-phase | deneysel | 54 | test_signals_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.special.multilabel | deneysel | 62 | test_streams_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.special.multioutput | deneysel | 62 | test_streams_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.special.ordinal | deneysel | 62 | test_streams_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.special.pu | eksik | 62 | test_streams_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.special.semisupervised | deneysel | 62 | test_streams_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.stream.broker | eksik | 62 | test_streams_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.stream.partial-fit | deneysel | 62 | test_streams_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.stream.replay | deneysel | 62 | test_streams_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.stream.scaler | deneysel | 62 | test_streams_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| model.temporal.acf | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.arima | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.change-point | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.classification | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.clustering | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.croston | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.decomposition | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.global-ridge | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.local | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.mase | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.pacf | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.probabilistic | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.reconciliation | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.rolling-origin | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.sarima | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.sarimax | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.stationarity | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.stl | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.temporal.var | deneysel | 53 | test_temporal_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 22/0/0 |
| model.time-series | deneysel | 21 | test_time_series_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 1/0/0 |
| model.uncertainty.cqr | deneysel | 50 | test_uncertainty_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:E, persist:E | 20/1/0 |
| model.uncertainty.interval | deneysel | 50 | test_uncertainty_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:E, persist:E | 20/1/0 |
| model.uncertainty.isotonic | deneysel | 50 | test_uncertainty_gui.py | fit:E, predict:E, proba:E, transform:- eksik, interval:- eksik, persist:E | 20/1/0 |
| model.uncertainty.quantile | deneysel | 50 | test_uncertainty_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:E, persist:E | 20/1/0 |
| model.uncertainty.sets | deneysel | 50 | test_uncertainty_gui.py | fit:E, predict:E, proba:E, transform:- eksik, interval:- eksik, persist:E | 20/1/0 |
| model.uncertainty.sigmoid | deneysel | 50 | test_uncertainty_gui.py | fit:E, predict:E, proba:E, transform:- eksik, interval:- eksik, persist:E | 20/1/0 |
| model.vision.classification | deneysel | 57 | test_vision_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 6/0/0 |
| model.vision.detection | deneysel | 57 | test_vision_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 6/0/0 |
| model.vision.scan | deneysel | 57 | test_vision_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 6/0/0 |
| model.vision.segmentation | deneysel | 57 | test_vision_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 6/0/0 |
| model.vision.transfer | deneysel | 57 | test_vision_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 6/0/0 |
| operation.aggregate | deneysel | 11 | test_relational_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| operation.append | deneysel | 11 | test_relational_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| operation.category-candidates | deneysel | 32 | test_data_contracts_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:- eksik | 0/0/0 |
| operation.category-map | deneysel | 32 | test_data_contracts_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:E, interval:- eksik, persist:E | 0/0/0 |
| operation.computed | deneysel | 11 | test_relational_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| operation.contract-check | deneysel | 32 | test_data_contracts_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:E, interval:- eksik, persist:E | 0/0/0 |
| operation.convert | deneysel | 10 | test_cleaning_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/2/0 |
| operation.date-parts | deneysel | 11 | test_relational_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| operation.dedup | deneysel | 10 | test_cleaning_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/2/0 |
| operation.drop | deneysel | 09 | test_operations_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| operation.entity-candidates | deneysel | 32 | test_data_contracts_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:- eksik | 0/0/0 |
| operation.entity-merge | deneysel | 32 | test_data_contracts_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:E, interval:- eksik, persist:E | 0/0/0 |
| operation.fill | deneysel | 10 | test_cleaning_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/2/0 |
| operation.filter | deneysel | 09 | test_operations_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| operation.geo-area | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| operation.geo-assign | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| operation.geo-block | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| operation.geo-buffer | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| operation.geo-clip | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| operation.geo-coordinates | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| operation.geo-distance | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| operation.geo-join | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| operation.geo-moran | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| operation.geo-repair | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| operation.geo-reproject | deneysel | 38 | test_geo_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/0/0 |
| operation.join | deneysel | 11 | test_relational_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| operation.map-categories | deneysel | 10 | test_cleaning_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/2/0 |
| operation.missing-columns | deneysel | 10 | test_cleaning_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/2/0 |
| operation.missing-rows | deneysel | 10 | test_cleaning_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/2/0 |
| operation.ordered-fill | deneysel | 10 | test_cleaning_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/2/0 |
| operation.outlier | deneysel | 10 | test_cleaning_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/2/0 |
| operation.pivot | deneysel | 11 | test_relational_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| operation.rename | deneysel | 09 | test_operations_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| operation.schema-contract | deneysel | 32 | test_data_contracts_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:E, interval:- eksik, persist:E | 0/0/0 |
| operation.text-combine | deneysel | 11 | test_relational_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| operation.text-split | deneysel | 11 | test_relational_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| operation.trim | deneysel | 10 | test_cleaning_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 5/2/0 |
| operation.unpivot | deneysel | 11 | test_relational_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| plugin.sdk | deneysel | 73 | test_plugins_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 31/0/0 |
| privacy.export | deneysel | 72 | test_privacy_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| privacy.retention | deneysel | 72 | test_privacy_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| privacy.review | deneysel | 72 | test_privacy_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| privacy.scan | deneysel | 72 | test_privacy_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| report.builder | deneysel | 70 | test_report_builder_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| repro.bundle | deneysel | 65 | test_repro_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 9/0/0 |
| repro.lineage | deneysel | 65 | test_repro_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 9/0/0 |
| repro.verify | deneysel | 65 | test_repro_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 9/0/0 |
| scenario.linear | deneysel | 68 | test_scenarios_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| scenario.mixed-integer | deneysel | 68 | test_scenarios_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| scenario.model-optimize | deneysel | 68 | test_scenarios_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| scenario.monte-carlo | deneysel | 68 | test_scenarios_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| scenario.nonlinear | deneysel | 68 | test_scenarios_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| scenario.what-if | deneysel | 68 | test_scenarios_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| share.bundle | deneysel | 71 | test_share_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| share.diff | deneysel | 71 | test_share_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| share.restore | deneysel | 71 | test_share_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| share.review | deneysel | 71 | test_share_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| statistics.adjust-bh | deneysel | 41 | test_resampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.adjust-bonferroni | deneysel | 41 | test_resampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.adjust-holm | deneysel | 41 | test_resampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.anova | deneysel | 14 | test_statistics_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.bayes-beta-binomial | deneysel | 43 | test_bayes_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:E, persist:E | 7/0/0 |
| statistics.bayes-hierarchical | deneysel | 43 | test_bayes_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:E, persist:E | 7/0/0 |
| statistics.bayes-linear | deneysel | 43 | test_bayes_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:E, persist:E | 7/0/0 |
| statistics.bayes-normal-mean | deneysel | 43 | test_bayes_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:E, persist:E | 7/0/0 |
| statistics.bootstrap-bca | deneysel | 41 | test_resampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.bootstrap-percentile | deneysel | 41 | test_resampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.causal-adjustment | deneysel | 44 | test_causal_gui.py | fit:E koşullu, predict:- eksik, proba:- eksik, transform:- eksik, interval:E koşullu, persist:E koşullu | 9/0/0 |
| statistics.causal-aipw | deneysel | 44 | test_causal_gui.py | fit:E koşullu, predict:- eksik, proba:- eksik, transform:- eksik, interval:E koşullu, persist:E koşullu | 9/0/0 |
| statistics.causal-did | deneysel | 44 | test_causal_gui.py | fit:E koşullu, predict:- eksik, proba:- eksik, transform:- eksik, interval:E koşullu, persist:E koşullu | 9/0/0 |
| statistics.causal-ipw | deneysel | 44 | test_causal_gui.py | fit:E koşullu, predict:- eksik, proba:- eksik, transform:- eksik, interval:E koşullu, persist:E koşullu | 9/0/0 |
| statistics.causal-iv | deneysel | 44 | test_causal_gui.py | fit:E koşullu, predict:- eksik, proba:- eksik, transform:- eksik, interval:E koşullu, persist:E koşullu | 9/0/0 |
| statistics.causal-matching | deneysel | 44 | test_causal_gui.py | fit:E koşullu, predict:- eksik, proba:- eksik, transform:- eksik, interval:E koşullu, persist:E koşullu | 9/0/0 |
| statistics.causal-randomized | deneysel | 44 | test_causal_gui.py | fit:E koşullu, predict:- eksik, proba:- eksik, transform:- eksik, interval:E koşullu, persist:E koşullu | 9/0/0 |
| statistics.chi2 | deneysel | 14 | test_statistics_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.dimension-ica | deneysel | 46 | test_dimensions_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:E, interval:- eksik, persist:E | 0/0/0 |
| statistics.dimension-incremental-pca | deneysel | 46 | test_dimensions_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:E, interval:- eksik, persist:E | 0/0/0 |
| statistics.dimension-model | deneysel | 46 | test_dimensions_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:E, interval:- eksik, persist:E | 0/0/0 |
| statistics.dimension-nmf | deneysel | 46 | test_dimensions_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:E, interval:- eksik, persist:E | 0/0/0 |
| statistics.dimension-pca | deneysel | 46 | test_dimensions_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:E, interval:- eksik, persist:E | 0/0/0 |
| statistics.dimension-rfe | deneysel | 46 | test_dimensions_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:E, interval:- eksik, persist:E | 0/0/0 |
| statistics.dimension-sequential | deneysel | 46 | test_dimensions_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:E, interval:- eksik, persist:E | 0/0/0 |
| statistics.dimension-svd | deneysel | 46 | test_dimensions_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:E, interval:- eksik, persist:E | 0/0/0 |
| statistics.dimension-tsne | deneysel | 46 | test_dimensions_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.dimension-umap | deneysel | 46 | test_dimensions_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.dimension-univariate | deneysel | 46 | test_dimensions_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:E, interval:- eksik, persist:E | 0/0/0 |
| statistics.dimension-variance | deneysel | 46 | test_dimensions_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:E, interval:- eksik, persist:E | 0/0/0 |
| statistics.experiment-mean | deneysel | 42 | test_experiments_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 5/0/0 |
| statistics.experiment-proportion | deneysel | 42 | test_experiments_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 5/0/0 |
| statistics.fisher | deneysel | 14 | test_statistics_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.glm-binomial | deneysel | 40 | test_statistical_models_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.glm-negative-binomial | deneysel | 40 | test_statistical_models_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.glm-poisson | deneysel | 40 | test_statistical_models_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.kruskal | deneysel | 14 | test_statistics_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.mann-whitney | deneysel | 14 | test_statistics_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.mi-mean | deneysel | 33 | test_missing_sampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 15/0/0 |
| statistics.mi-ols | deneysel | 33 | test_missing_sampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 15/0/0 |
| statistics.missing-indicators | deneysel | 33 | test_missing_sampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 15/0/0 |
| statistics.missing-patterns | deneysel | 33 | test_missing_sampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 15/0/0 |
| statistics.mixed | deneysel | 40 | test_statistical_models_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.ols | deneysel | 40 | test_statistical_models_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.paired-sign-flip | deneysel | 41 | test_resampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.paired-t | deneysel | 14 | test_statistics_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.pearson | deneysel | 14 | test_statistics_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.permutation | deneysel | 41 | test_resampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.power-mean | deneysel | 42 | test_experiments_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 5/0/0 |
| statistics.power-proportion | deneysel | 42 | test_experiments_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 5/0/0 |
| statistics.quantile | deneysel | 40 | test_statistical_models_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.random-assignment | deneysel | 42 | test_experiments_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 5/0/0 |
| statistics.repeated | deneysel | 40 | test_statistical_models_gui.py | fit:E, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.robust-summary | deneysel | 41 | test_resampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.sample-cluster | deneysel | 33 | test_missing_sampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 15/0/0 |
| statistics.sample-random | deneysel | 33 | test_missing_sampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 15/0/0 |
| statistics.sample-stratified | deneysel | 33 | test_missing_sampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 15/0/0 |
| statistics.sensitivity | deneysel | 41 | test_resampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.spearman | deneysel | 14 | test_statistics_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.survey-mean | deneysel | 33 | test_missing_sampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 15/0/0 |
| statistics.survival-aft | deneysel | 45 | test_survival_gui.py | fit:E koşullu, predict:E koşullu, proba:- eksik, transform:- eksik, interval:E koşullu, persist:E koşullu | 9/0/0 |
| statistics.survival-cif | deneysel | 45 | test_survival_gui.py | fit:E koşullu, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E koşullu | 9/0/0 |
| statistics.survival-cox | deneysel | 45 | test_survival_gui.py | fit:E koşullu, predict:E koşullu, proba:- eksik, transform:- eksik, interval:E koşullu, persist:E koşullu | 9/0/0 |
| statistics.survival-km | deneysel | 45 | test_survival_gui.py | fit:E koşullu, predict:- eksik, proba:- eksik, transform:- eksik, interval:E koşullu, persist:E koşullu | 9/0/0 |
| statistics.survival-logrank | deneysel | 45 | test_survival_gui.py | fit:E koşullu, predict:- eksik, proba:- eksik, transform:- eksik, interval:E koşullu, persist:E koşullu | 9/0/0 |
| statistics.weighted-fit | deneysel | 33 | test_missing_sampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 15/0/0 |
| statistics.weighted-mean | deneysel | 33 | test_missing_sampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 15/0/0 |
| statistics.weighted-ols | deneysel | 33 | test_missing_sampling_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 15/0/0 |
| statistics.welch-anova | deneysel | 14 | test_statistics_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.welch-t | deneysel | 14 | test_statistics_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.wilcoxon | deneysel | 14 | test_statistics_gui.py | fit:- eksik, predict:- eksik, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| statistics.wls | deneysel | 40 | test_statistical_models_gui.py | fit:E, predict:E, proba:- eksik, transform:- eksik, interval:- eksik, persist:E | 0/0/0 |
| text.inspect | deneysel | 22 | test_text_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| text.nlp.active-learning | deneysel | 55 | test_nlp_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 4/0/0 |
| text.nlp.annotation | deneysel | 55 | test_nlp_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 4/0/0 |
| text.nlp.classification | deneysel | 55 | test_nlp_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 4/0/0 |
| text.nlp.embeddings | deneysel | 55 | test_nlp_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 4/0/0 |
| text.nlp.lda | deneysel | 55 | test_nlp_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 4/0/0 |
| text.nlp.model | deneysel | 55 | test_nlp_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 4/0/0 |
| text.nlp.ner | deneysel | 55 | test_nlp_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 4/0/0 |
| text.nlp.nmf | deneysel | 55 | test_nlp_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 4/0/0 |
| text.nlp.retrieval | deneysel | 55 | test_nlp_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 4/0/0 |
| text.nlp.search | deneysel | 55 | test_nlp_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 4/0/0 |
| text.nlp.sentiment | deneysel | 55 | test_nlp_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 4/0/0 |
| text.nlp.tfidf | deneysel | 55 | test_nlp_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 4/0/0 |
| workflow.analysis | deneysel | 64 | test_workflow_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 17/0/0 |
| workflow.export | deneysel | 64 | test_workflow_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 17/0/0 |
| workflow.predict | deneysel | 64 | test_workflow_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 17/0/0 |
| workflow.quality | deneysel | 64 | test_workflow_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 17/0/0 |
| workflow.recipe | deneysel | 23 | test_recipes_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 0/0/0 |
| workflow.schedule | eksik | 64 | test_workflow_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 17/0/0 |
| workflow.source | deneysel | 64 | test_workflow_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 17/0/0 |
| workflow.train | deneysel | 64 | test_workflow_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 17/0/0 |
| workflow.transform | deneysel | 64 | test_workflow_gui.py | fit:? eksik, predict:? eksik, proba:? eksik, transform:? eksik, interval:? eksik, persist:? eksik | 17/0/0 |
