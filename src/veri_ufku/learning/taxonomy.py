"""Ordered learning paths; every packaged topic has one explicit home."""

CONTEXT_ONLY = frozenset(
    "rows-columns data-types column-role projects source-working import-csv import-delimiter import-encoding import-header import-date import-decimal import-bad-rows import-json import-jsonl import-flatten import-xlsx import-parquet import-phase11 home learn tasks guide".split()
)

STAGES = (
    (
        "data",
        "Veri",
        (
            (
                "inventory",
                "Veri profili · sütunlara genel bakış",
                "inspection-inventory",
            ),
            ("values", "Sütun değerlerini inceleme", "inspection-values"),
            ("describe", "Özet istatistikler", "inspection-describe"),
            ("notes", "Sütunların anlamı ve notlar", "inspection-notes"),
            (
                "advanced-import",
                "Gelişmiş dosya formatları",
                "import-phase30 import-partition import-schema-evolution import-category-labels import-decimal-precision connector-connection connector-query connector-snapshot connector-pagination connector-freshness",
            ),
            (
                "contracts",
                "Veri sözleşmeleri ve kimlik eşleme",
                "contract-level contract-schema contract-reference contract-fuzzy contract-merge",
            ),
            ("definition", "Veri Nedir?", "data"),
            (
                "arrays",
                "Çok boyutlu bilimsel veri",
                "array-dimensions array-raster array-units array-chunks",
            ),
            ("types", "Veri Tipleri", "data-numeric data-categorical data-scales"),
            ("structure", "Verinin Yapısı", "data-structured data-unstructured"),
            (
                "context",
                "Kullanım ve Bağlam",
                "data-access data-computing data-statistics",
            ),
        ),
    ),
    (
        "analysis",
        "Veriyi Analiz Etme",
        (
            (
                "causal",
                "Nedensel soru ve identification",
                "causal causal-randomized causal-adjustment causal-ipw causal-aipw causal-matching causal-did causal-iv causal-sensitivity",
            ),
            (
                "survival",
                "Sağkalım ve risk set",
                "survival survival-km survival-logrank survival-cox survival-aft survival-cif survival-entry survival-metrics survival-prediction",
            ),
            (
                "dimensions",
                "Latent boyut ve özellik seçimi",
                "dimensions dimension-pca dimension-incremental-pca dimension-svd dimension-nmf dimension-ica dimension-tsne dimension-umap dimension-variance dimension-model dimension-univariate dimension-rfe dimension-sequential dimension-loading dimension-leakage dimension-sparse dimension-stability",
            ),
            (
                "exploration",
                "Yoğunluk, üyelik ve novelty",
                "exploration exploration-density exploration-soft exploration-novelty exploration-stability",
            ),
            (
                "model-families",
                "Regularization, boosting ve ensemble",
                "model-families family-regularization family-boosting family-kernel family-bias-variance family-ensemble family-elasticnet family-lasso family-sgd family-decision-tree family-extra-trees family-gradient-boosting family-hist-gradient family-svm family-knn family-gaussian-nb family-multinomial-nb family-bagging family-voting family-stacking family-xgboost family-lightgbm family-catboost",
            ),
            (
                "model-search",
                "Hyperparameter ve nested arama",
                "model-search search-grid search-random search-bayesian search-hyperparameter search-nested search-trial search-validation-overfit search-budget search-curves search-early-prune search-resume",
            ),
            (
                "model-uncertainty",
                "Kalibrasyon ve predictive belirsizlik",
                "uncertainty-probability uncertainty-threshold uncertainty-coverage uncertainty-types",
            ),
            (
                "model-explanation",
                "Model açıklaması ve hata dilimleri",
                "model-explanation explanation-correlated explanation-slices explanation-fairness explanation-scenarios experiment-registry scenario-simulation scientific-report review-sharing privacy-governance plugins-sdk environment-distribution",
            ),
            ("analysis-intro", "Verinin Analizi — Genel Bakış", "analysis-overview"),
            (
                "descriptive",
                "Açıklayıcı Analiz (Descriptive Analysis)",
                "analysis-descriptive dataset-profile profile-unique profile-std profile-quantile mean-median sample",
            ),
            (
                "diagnostic",
                "Teşhis Analizi (Diagnostic Analysis)",
                "analysis-diagnostic quality missing-mechanism duplicates outliers missing missing-assumptions missing-multiple sampling-representation sampling-bias weights-types",
            ),
            (
                "predictive",
                "Tahmine Dayalı Analiz (Predictive Analysis)",
                "analysis-predictive prediction",
            ),
            (
                "prescriptive",
                "Kuralcı Analiz (Prescriptive Analysis)",
                "analysis-prescriptive",
            ),
            (
                "exploratory",
                "Keşifsel Veri Analizi (Exploratory Data Analysis)",
                "analysis-exploratory chart-summary chart-violin chart-kde chart-ecdf chart-rug chart-strip chart-swarm chart-qq chart-pp chart-error-bar chart-ci-band chart-missing-pattern chart-density chart-uncertainty chart-log chart-pair chart-hexbin chart-density-2d chart-bubble chart-grouped-heatmap chart-clustered-heatmap chart-parallel chart-facets chart-conditional chart-overplotting chart-stacked-bar chart-percent-bar chart-stacked-area chart-percent-area chart-dot chart-lollipop chart-waterfall chart-pareto chart-treemap chart-sunburst chart-sankey chart-alluvial chart-funnel chart-calendar chart-pie chart-donut chart-radar chart-denominator chart-hierarchy-flow chart-area-perception chart-double-counting geo-crs geo-projection geo-join geo-maup geo-leakage geo-repair geo-raster geo-classification geo-weights geo-online",
            ),
        ),
    ),
    (
        "cleaning",
        "Veri Temizleme",
        (
            ("cleaning-intro", "Verinin Temizlenmesi — Ön İşleme", "cleaning-overview"),
            (
                "clean",
                "Temizleme",
                "cleaning-clean clean-missing-rows clean-missing-columns clean-fill-constant clean-fill-mean clean-fill-median clean-fill-mode clean-dedup clean-trim clean-map-categories clean-convert clean-ordered-fill-forward clean-ordered-fill-backward clean-outlier operation-preview operation-history",
            ),
            (
                "merge",
                "Birleştirme",
                "cleaning-merge transform-append transform-join transform-text-combine",
            ),
            (
                "transform",
                "Dönüştürme",
                "cleaning-transform cleaning-minmax cleaning-zscore cleaning-decimal transform-computed transform-text-split transform-date-parts transform-aggregate transform-pivot transform-unpivot",
            ),
            ("reduce", "İndirgeme", "cleaning-reduce model-features"),
        ),
    ),
    (
        "visualization",
        "Veri Görselleştirme",
        (
            (
                "distribution",
                "Dağılım ve kategoriler",
                "chart-histogram chart-box chart-bar chart-missing",
            ),
            ("time", "Zamanın sırası", "chart-line"),
        ),
    ),
    (
        "relations",
        "İlişkileri Keşfetme",
        (
            (
                "association",
                "İlişki ve yorum sınırları",
                "correlation chart-scatter chart-correlation expert-workspace statistics-observational statistics-pearson statistics-spearman",
            ),
        ),
    ),
    (
        "statistics",
        "İstatistiksel Karşılaştırma",
        (
            (
                "interpretation",
                "Soru, varsayımlar ve yorum",
                "bayes bayes-beta-binomial bayes-normal-mean bayes-linear bayes-hierarchical bayes-interval bayes-mcmc bayes-predictive bayes-comparison statistics statistics-pvalue statistics-effect statistics-ci statistics-pairing statistics-multiple resampling resampling-bootstrap-percentile resampling-bootstrap-bca resampling-permutation resampling-paired-sign-flip resampling-robust-summary resampling-adjust-holm resampling-adjust-bonferroni resampling-adjust-bh resampling-sensitivity experiment-plan experiment-randomization experiment-mde-power experiment-stopping experiment-measurement experiment-power-mean experiment-power-proportion experiment-random-assignment experiment-experiment-mean experiment-experiment-proportion statistical-models statistical-model-ols statistical-model-wls statistical-model-glm-binomial statistical-model-glm-poisson statistical-model-glm-negative-binomial statistical-model-quantile statistical-model-mixed statistical-model-repeated",
            ),
            (
                "tests",
                "Grup ve kategori karşılaştırmaları",
                "statistics-welch-t statistics-mann-whitney statistics-paired-t statistics-wilcoxon statistics-anova statistics-welch-anova statistics-kruskal statistics-chi2 statistics-fisher",
            ),
        ),
    ),
    (
        "modeling",
        "Modelleme",
        (
            (
                "preparation",
                "Özellik hazırlama",
                "model-preparation model-encoding model-scaling model-imputation",
            ),
            ("regression", "Bir sayıyı tahmin etme", "model-regression"),
            (
                "neural",
                "CPU tensor eğitimi",
                "neural-training neural-checkpoint neural-tensor-schema vision-images vision-duplicate vision-augmentation vision-iou audio-files audio-features audio-leakage audio-wer recommendation-feedback recommendation-evaluation recommendation-cold-start pattern-support pattern-retention pattern-trace graph-structure graph-measures graph-leakage stream-window stream-prequential special-targets code-equivalence code-notebook-state code-sql-query",
            ),
            (
                "text",
                "Metin incelemesi",
                "text-tokens text-language text-tfidf text-similarity nlp-model-language nlp-topic-label nlp-offset-review nlp-pool-retrieval",
            ),
            (
                "timeseries",
                "Zaman serisi",
                "timeseries-frequency timeseries-seasonality timeseries-lag timeseries-validation temporal-advanced temporal-exogenous temporal-horizon temporal-hierarchy temporal-regime signal-sampling signal-spectrum signal-filter signal-windows",
            ),
            (
                "clustering",
                "Benzer kayıtları keşfetme",
                "unsupervised-cluster unsupervised-distance unsupervised-noise",
            ),
            (
                "anomaly",
                "Anomali adayları ve değerlendirme",
                "unsupervised-score unsupervised-evaluation",
            ),
            (
                "classification",
                "Bir kategori tahmin etme",
                "model-classification classification-positive classification-metrics classification-threshold classification-probability",
            ),
        ),
    ),
    (
        "evaluation",
        "Modeli Değerlendirme",
        (
            (
                "validation",
                "Ayırma, doğrulama ve baseline",
                "model-validation model-training-fold",
            ),
            (
                "leakage",
                "Sızıntı ve final test disiplini",
                "leakage model-history model-test-use",
            ),
        ),
    ),
    (
        "sharing",
        "Bulguları Paylaşma",
        (
            (
                "outputs",
                "Rapor ve dışa aktarma",
                "report export dashboard-question dashboard-filter-scope dashboard-kpi figure-readable",
            ),
            (
                "lifecycle",
                "Model kartı ve yeni veri",
                "model-card model-importance model-unknown-category model-new-data model-uncertainty",
            ),
        ),
    ),
    (
        "monitoring",
        "İzleme ve İyileştirme",
        (
            (
                "followup",
                "Sonuçları izleme",
                "workflow-recipe workflow-drift workflow-model",
            ),
            ("laboratory", "Ders laboratuvarı", "learning-laboratory"),
            ("batchmonitor", "Yerel model izleme", "model-monitoring"),
            (
                "dag",
                "Dallanan işler ve batch",
                "workflow-dag workflow-cache workflow-batch",
            ),
            (
                "reproducibility",
                "Köken ve araştırma kaydı",
                "repro-lineage repro-snapshot repro-environment repro-tolerance repro-record compute-resources",
            ),
        ),
    ),
)


def learning_tree(results, *, include_empty=False):
    topics = {topic["id"]: topic for topic in results}
    return [
        dict(
            id=key,
            title=title,
            groups=[
                dict(
                    id=group,
                    title=label,
                    topics=[topics[k] for k in ids.split() if k in topics],
                )
                for group, label, ids in groups
                if include_empty or any(k in topics for k in ids.split())
            ],
        )
        for key, title, groups in STAGES
        if include_empty
        or any(k in topics for _, _, ids in groups for k in ids.split())
    ]
