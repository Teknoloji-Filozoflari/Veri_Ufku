"""Shared capability registry; CSV/TSV import is implemented in Phase 05."""

from dataclasses import replace as _replace_distribution

from veri_ufku.charts.contracts import COMPOSITION_KINDS, COMPOSITION_SCHEMAS
from veri_ufku.charts.contracts import (
    DISTRIBUTION_KINDS as _distribution_kinds,
)
from veri_ufku.charts.contracts import MULTIVARIATE_KINDS as _multi_kinds
from veri_ufku.charts.contracts import (
    WEIGHT_KINDS as _weight_kinds,
)
from veri_ufku.domain.contracts import Capability, ExecutionKind
from veri_ufku.domain.contracts import InputRole as _DagRole
from veri_ufku.domain.contracts import InputSchema as _DagInput
from veri_ufku.domain.contracts import InputSchema as _LateInput
from veri_ufku.domain.contracts import LearningLink as _LateLearning
from veri_ufku.domain.contracts import MethodSupport as _LateSupport
from veri_ufku.domain.contracts import Parameter as _LateParameter
from veri_ufku.geo import CHART_SCHEMAS as _GEO_SCHEMAS
from veri_ufku.geo import FORMATS as _GEO_FORMATS
from veri_ufku.geo import OPERATION_KINDS as _GEO_OPERATIONS
from veri_ufku.modeling.family_contracts import (
    FAMILY_METHODS,
    OPTIONAL_FAMILIES,
    REGRESSION_FAMILIES,
)
from veri_ufku.statistics.bayes_contracts import BAYES_METHODS
from veri_ufku.statistics.causal_contracts import CAUSAL_METHODS
from veri_ufku.statistics.contracts import ADVANCED_METHODS as _ADVANCED_METHODS
from veri_ufku.statistics.dimension_contracts import DIMENSION_METHODS
from veri_ufku.statistics.experiment_contracts import EXPERIMENT_METHODS
from veri_ufku.statistics.model_contracts import MODEL_METHODS as _MODEL_METHODS
from veri_ufku.statistics.resampling_contracts import (
    RESAMPLING_METHODS as _RESAMPLING_METHODS,
)
from veri_ufku.statistics.survival_contracts import SURVIVAL_METHODS

CAPABILITIES = {
    "demo.cpu": Capability(
        "demo.cpu", ExecutionKind.CPU, "integer_sum", help_links=("tasks",)
    ),
    "demo.io": Capability(
        "demo.io", ExecutionKind.IO, "bounded_file_write", help_links=("tasks",)
    ),
    "demo.unknown": Capability(
        "demo.unknown", ExecutionKind.IO, "unknown_total", help_links=("tasks",)
    ),
    "demo.failure": Capability(
        "demo.failure", ExecutionKind.IO, "controlled_failure", help_links=("tasks",)
    ),
}

for method in (
    "welch_t",
    "paired_t",
    "mann_whitney",
    "wilcoxon",
    "anova",
    "welch_anova",
    "kruskal",
    "chi2",
    "fisher",
    "pearson",
    "spearman",
):
    CAPABILITIES["statistics." + method.replace("_", "-")] = Capability(
        "statistics." + method.replace("_", "-"),
        ExecutionKind.CPU,
        "statistical_" + method,
        kind="analysis",
        maturity="deneysel",
        backend="scipy/polars/numpy",
        input_schema="DatasetVersion/v7",
        output_type="AnalysisResult/v1",
        parameter_schema="AnalysisSpec/v1",
        deterministic_policy="explicit hypotheses; key pairing; complete-case; no automatic selection; no bootstrap",
        supports=(
            ("null", True),
            ("decimal", True),
            ("cancel", True),
            ("safe_serialization", True),
        ),
        limits=(("rows", 100000), ("groups", 20)),
        help_links=("statistics-" + method.replace("_", "-"), "statistics-pvalue"),
        requirement_ids=tuple("F14-S00" + str(i) for i in range(1, 7)),
        evidence_refs=("docs/evidence/PHASE14.md",),
    )

CAPABILITIES["model.prepare"] = Capability(
    "model.prepare",
    ExecutionKind.CPU,
    "unfitted_preparation_plan",
    kind="model",
    input_schema="DatasetVersion/v7",
    output_type="PreparationReport/v1",
    parameter_schema="PreparationSpec/v1",
    backend="polars; no estimator fit",
    deterministic_policy="observational full scan; training-only future plan; immutable source; history retained",
    supports=(("cancel", True), ("safe_serialization", True), ("predict", False)),
    limits=(("rows", 100000), ("columns", 100)),
    help_links=("model-preparation", "model-training-fold"),
    requirement_ids=tuple("F15-S00" + str(i) for i in range(1, 7)),
    evidence_refs=("docs/evidence/PHASE15.md",),
)

for adapter in ("csv", "tsv"):
    CAPABILITIES["import." + adapter] = Capability(
        "import." + adapter,
        ExecutionKind.IO,
        "validated_snapshot_delimited",
        kind="import",
        maturity="deneysel",
        input_schema="ImportSettings/v1",
        output_type="DatasetParquet/v1",
        parameter_schema="ImportSettings/v1",
        backend="python-csv/polars",
        deterministic_policy="immutable source copy; record UUIDs are distinct",
        supports=(
            ("null", True),
            ("nan", False),
            ("inf", False),
            ("decimal", True),
            ("tz", True),
            ("streaming", True),
            ("cancel", True),
            ("safe_serialization", True),
        ),
        limits=(
            ("source_bytes", 1073741824),
            ("columns", 256),
            ("record_bytes", 1048576),
            ("preview_rows", 200),
        ),
        requirement_ids=(
            "F05-S001",
            "F05-S002",
            "F05-S003",
            "F05-S004",
            "F05-S005",
            "F05-S006",
            "F05-S007",
        ),
        help_links=("import-csv",),
        evidence_refs=("docs/evidence/PHASE05.md",),
    )


def get_capability(capability_id):
    try:
        return CAPABILITIES[capability_id]
    except KeyError:
        raise ValueError("Unsupported capability") from None


for adapter in ("json", "jsonl", "xlsx", "parquet"):
    CAPABILITIES["import." + adapter] = Capability(
        "import." + adapter,
        ExecutionKind.IO,
        "validated_snapshot_" + adapter,
        kind="import",
        maturity="deneysel",
        input_schema="StructuredSettings/v1",
        output_type="DatasetParquet/native-v1",
        parameter_schema="StructuredSettings/v1",
        backend="bounded-ooxml/polars"
        if adapter == "xlsx"
        else "polars-native-parquet"
        if adapter == "parquet"
        else "python-json/polars",
        deterministic_policy="immutable snapshot; distinct record UUIDs; explicit nested transformations",
        supports=(
            ("null", True),
            ("nan", adapter == "parquet"),
            ("inf", adapter == "parquet"),
            ("decimal", True),
            ("tz", True),
            ("streaming", adapter in ("jsonl", "parquet")),
            ("cancel", True),
            ("safe_serialization", True),
        ),
        limits=(
            ("source_bytes", 1073741824),
            ("columns", 256),
            ("preview_rows", 200),
            ("json_bytes", 67108864),
            ("record_bytes", 1048576),
        ),
        requirement_ids=tuple("F06-S00" + str(i) for i in range(1, 8)),
        help_links=("import-" + adapter,),
        evidence_refs=("docs/evidence/PHASE06.md",),
    )

for action, execution in (
    ("view", ExecutionKind.CPU),
    ("profile", ExecutionKind.CPU),
    ("roles", ExecutionKind.IO),
):
    CAPABILITIES["dataset." + action] = Capability(
        "dataset." + action,
        execution,
        "immutable_dataset_" + action,
        maturity="deneysel",
        backend="polars/sqlite/decimal",
        deterministic_policy="immutable RowId; explicit scope; input-order sample",
        help_links=("column-role" if action == "roles" else "dataset-profile",),
        requirement_ids=tuple("F07-S00" + str(i) for i in range(1, 8)),
        evidence_refs=("docs/evidence/PHASE07.md",),
    )

CAPABILITIES["dataset.quality"] = Capability(
    "dataset.quality",
    ExecutionKind.CPU,
    "immutable_quality_scan",
    kind="quality",
    input_schema="DatasetVersion/v4",
    output_type="QualityReport/v1",
    parameter_schema="QualityScan/v1",
    supports=(
        ("null", True),
        ("nan", True),
        ("inf", True),
        ("decimal", True),
        ("tz", True),
        ("streaming", True),
        ("cancel", True),
        ("safe_serialization", True),
    ),
    limits=(("rules", 32), ("examples_per_finding", 5), ("category_variants", 200)),
    maturity="deneysel",
    backend="polars/sqlite/decimal",
    deterministic_policy="explicit rules; firstN sample; bounded examples; no mutation",
    help_links=("quality", "duplicates", "missing-mechanism", "outliers"),
    requirement_ids=tuple("F08-S00" + str(i) for i in range(1, 7)),
    evidence_refs=("docs/evidence/PHASE08.md",),
)

for action in ("rename", "drop", "filter"):
    CAPABILITIES["operation." + action.replace("_", "-")] = Capability(
        "operation." + action.replace("_", "-"),
        ExecutionKind.CPU,
        "versioned_" + action,
        kind="transform",
        maturity="deneysel",
        backend="polars",
        input_schema="DatasetVersion/v5",
        output_type="DatasetVersion/v5",
        parameter_schema="OperationSpec/v1",
        deterministic_policy="preserve identities; immutable input; full-data preview artifact publication",
        supports=(
            ("null", True),
            ("decimal", True),
            ("tz", True),
            ("streaming", True),
            ("cancel", True),
            ("safe_serialization", True),
        ),
        limits=(("columns", 256), ("preview_rows", 200)),
        help_links=("operation-preview", "operation-history", "source-working"),
        requirement_ids=tuple("F09-S00" + str(i) for i in range(1, 8)),
        evidence_refs=("docs/evidence/PHASE09.md",),
    )

for action in (
    "missing_rows",
    "missing_columns",
    "fill",
    "dedup",
    "trim",
    "map_categories",
    "convert",
    "ordered_fill",
    "outlier",
):
    CAPABILITIES["operation." + action.replace("_", "-")] = Capability(
        "operation." + action.replace("_", "-"),
        ExecutionKind.CPU,
        "versioned_cleaning_" + action,
        kind="transform",
        maturity="deneysel",
        backend="polars/sqlite/decimal",
        input_schema="DatasetVersion/v6",
        output_type="DatasetVersion/v6",
        parameter_schema="OperationSpec/v1:cleaning",
        deterministic_policy="explicit policies; immutable identities; full preview; stable order; training pipeline is separate",
        supports=(
            ("null", True),
            ("nan", True),
            ("decimal", True),
            ("tz", True),
            ("streaming", True),
            ("cancel", True),
            ("safe_serialization", True),
        ),
        limits=(
            ("columns", 256),
            ("batch_rows", 4096),
            ("preview_rows", 200),
            ("mapping_pairs", 1000),
        ),
        help_links=tuple(
            [
                "clean-fill-constant",
                "clean-fill-mean",
                "clean-fill-median",
                "clean-fill-mode",
            ]
            if action == "fill"
            else ["clean-ordered-fill-forward", "clean-ordered-fill-backward"]
            if action == "ordered_fill"
            else ["clean-" + action.replace("_", "-")]
        ),
        requirement_ids=tuple("F10-S00" + str(i) for i in range(1, 9)),
        evidence_refs=("docs/evidence/PHASE10.md",),
    )

for action in (
    "computed",
    "text_split",
    "text_combine",
    "date_parts",
    "aggregate",
    "pivot",
    "unpivot",
    "append",
    "join",
):
    key = action.replace("_", "-")
    CAPABILITIES["operation." + key] = Capability(
        "operation." + key,
        ExecutionKind.CPU,
        "versioned_transform_" + action,
        kind="transform",
        maturity="deneysel",
        backend="polars/sqlite/decimal",
        input_schema="DatasetVersion/v7",
        output_type="DatasetVersion/v7",
        parameter_schema="OperationSpec/v1:transform",
        deterministic_policy="explicit null/equality/type/order; persistent output UUIDs; immutable input edges; exact full preview",
        supports=(
            ("null", True),
            ("decimal", True),
            ("tz", True),
            ("cancel", True),
            ("safe_serialization", True),
        ),
        limits=(
            ("columns", 256),
            ("batch_rows", 4096),
            ("output_rows", 10000000),
            ("preview_rows", 200),
        ),
        help_links=("transform-" + key,),
        requirement_ids=tuple("F11-S00" + str(i) for i in range(1, 8)),
        evidence_refs=("docs/evidence/PHASE11.md",),
    )

for adapter in ("ods", "sqlite", "ipc", "ipc_stream"):
    key = adapter.replace("_", "-")
    CAPABILITIES["import." + key] = Capability(
        "import." + key,
        ExecutionKind.IO,
        "validated_snapshot_" + adapter,
        kind="import",
        maturity="deneysel",
        backend="python-stdlib/polars",
        input_schema="StructuredSettings/v1",
        output_type="DatasetVersion/v7",
        parameter_schema="StructuredSettings/v1",
        deterministic_policy="immutable capture; readonly SQLite; no extensions; native IPC; explicit support limits",
        supports=(
            ("null", True),
            ("decimal", True),
            ("cancel", True),
            ("safe_serialization", True),
            ("streaming", adapter in ("sqlite", "ipc")),
        ),
        limits=(("columns", 256), ("source_bytes", 1073741824), ("preview_rows", 200)),
        help_links=("import-phase11",),
        requirement_ids=("F11-S004", "F11-S006", "F11-S007"),
        evidence_refs=("docs/evidence/PHASE11.md",),
    )

for kind in ("histogram", "box", "bar", "line", "scatter", "correlation", "missing"):
    CAPABILITIES["chart." + kind] = Capability(
        "chart." + kind,
        ExecutionKind.CPU,
        "chart_" + kind,
        kind="chart",
        maturity="deneysel",
        backend="polars/python/matplotlib-Agg",
        input_schema="ChartSpec/v1",
        output_type="ChartResult/v1",
        parameter_schema="ChartSpec/v1",
        deterministic_policy="immutable version; explicit firstN/systematic/grid; pairwise finite; RowId point membership",
        supports=(
            ("null", True),
            ("nan", True),
            ("decimal", True),
            ("tz", True),
            ("cancel", True),
            ("safe_serialization", True),
        ),
        limits=(
            ("correlation_columns", 20),
            ("scatter_points", 10000),
            ("histogram_bins", 200),
            ("category_top_n", 100),
        ),
        help_links=("chart-" + kind, "chart-summary"),
        requirement_ids=tuple("F12-S00" + str(i) for i in range(1, 8)),
        evidence_refs=("docs/evidence/PHASE12.md",),
    )

for fmt in ("csv", "json", "jsonl", "parquet", "xlsx", "html", "pdf"):
    CAPABILITIES["export." + fmt] = Capability(
        "export." + fmt,
        ExecutionKind.CPU,
        "verified_export_" + fmt,
        kind="export",
        maturity="deneysel",
        backend="polars/stdlib/Qt-local",
        input_schema="DatasetVersion/v7",
        output_type="PublishedReceipt/v1",
        parameter_schema="ReportSpec/v1" if fmt in ("html", "pdf") else "ExportSpec/v1",
        deterministic_policy="immutable version/view; exclusive no-overwrite publication; explicit projection; reopen row/type verification",
        supports=(
            ("null", True),
            ("decimal", True),
            ("cancel", True),
            ("safe_serialization", True),
        ),
        limits=(
            ("xlsx_rows", 100000),
            ("xlsx_columns", 256),
            ("report_table_rows", 200),
            ("report_charts", 10),
        ),
        help_links=("report",) if fmt in ("html", "pdf") else ("export",),
        requirement_ids=("F13-S002", "F13-S003", "F13-S006"),
        evidence_refs=("docs/evidence/PHASE13.md",),
    )

CAPABILITIES["model.baseline"] = Capability(
    "model.baseline",
    ExecutionKind.CPU,
    "split_fold_dummy_baseline",
    kind="model",
    maturity="deneysel",
    backend="scikit-learn/polars/numpy",
    input_schema="DatasetVersion/v7",
    output_type="BaselineRun/v1",
    parameter_schema="ValidationSpec/v1",
    deterministic_policy="explicit seed; persistent RowId membership; development-only CV; final test journal",
    supports=(("cancel", True), ("safe_serialization", True), ("predict", False)),
    limits=(("rows", 100000), ("columns", 100), ("folds", 10)),
    help_links=("model-validation", "model-test-use"),
    requirement_ids=tuple("F16-S00" + str(i) for i in range(1, 7)),
    evidence_refs=("docs/evidence/PHASE16.md",),
)


CAPABILITIES["model.regression"] = Capability(
    "model.regression",
    ExecutionKind.CPU,
    "bounded_regression_cv",
    kind="model",
    maturity="deneysel",
    backend="scikit-learn/polars/numpy",
    input_schema="DatasetVersion/v7",
    output_type="BaselineRun/v1 + regression",
    parameter_schema="RegressionSettings/v1 + ValidationSpec/v1",
    deterministic_policy="seed; development CV MAE selection; frozen final candidate; project test journal",
    supports=(("cancel", True), ("safe_serialization", True), ("predict", True)),
    limits=(
        ("rows", 100000),
        ("forest_rows", 20000),
        ("candidates", 4),
        ("dense_cells", 4000000),
    ),
    help_links=("model-regression", "model-test-use"),
    requirement_ids=tuple("F17-S00" + str(i) for i in range(1, 8)),
    evidence_refs=("docs/evidence/PHASE17.md",),
)

CAPABILITIES["model.classification"] = Capability(
    "model.classification",
    ExecutionKind.CPU,
    "bounded_classification_cv",
    kind="model",
    maturity="deneysel",
    backend="scikit-learn/polars/numpy",
    input_schema="DatasetVersion/v7",
    output_type="BaselineRun/v1 + classification",
    parameter_schema="ClassificationSettings/v1 + ValidationSpec/v1",
    deterministic_policy="seed; development CV F1; validation-only threshold; frozen final decision; append-only journal",
    supports=(("cancel", True), ("safe_serialization", True), ("predict", True)),
    limits=(
        ("rows", 100000),
        ("forest_rows", 20000),
        ("classes", 20),
        ("dense_cells", 4000000),
    ),
    help_links=(
        "model-classification",
        "classification-positive",
        "classification-metrics",
        "classification-threshold",
        "classification-probability",
    ),
    requirement_ids=tuple("F18-S00" + str(i) for i in range(1, 8)),
    evidence_refs=("docs/evidence/PHASE18.md",),
)

for _method, _rows in (
    ("kmeans", 100000),
    ("dbscan", 3000),
    ("agglomerative", 3000),
    ("gmm", 3000),
    ("optics", 3000),
    ("hdbscan", 3000),
    ("lof", 3000),
    ("one-class-svm", 3000),
    ("robust-covariance", 3000),
    ("isolation-forest", 100000),
    ("iqr", 100000),
):
    CAPABILITIES["model." + _method] = Capability(
        "model." + _method,
        ExecutionKind.CPU,
        "full_version_" + _method,
        kind="model",
        maturity="deneysel",
        backend="scikit-learn/polars/numpy",
        input_schema="DatasetVersion/v7 numeric measurements",
        output_type="UnsupervisedRun/v1 + RowId assignments",
        parameter_schema="UnsupervisedSpec/v1",
        deterministic_policy="explicit seed (KMeans/IsolationForest); full fit version; no view filter; no deletion",
        supports=(
            ("cancel", True),
            ("predict", _method in ("kmeans", "isolation-forest", "iqr")),
            ("safe_serialization", True),
        ),
        limits=(
            ("rows", _rows),
            ("features", 1 if _method == "iqr" else 20),
            ("silhouette_rows", 3000),
        ),
        help_links=(
            "unsupervised-cluster",
            "unsupervised-distance",
            "unsupervised-noise",
            "unsupervised-score",
            "unsupervised-evaluation",
            "exploration",
            "exploration-density",
            "exploration-soft",
            "exploration-novelty",
            "exploration-stability",
        ),
        requirement_ids=tuple("F19-S00" + str(i) for i in range(1, 7)),
        evidence_refs=("docs/evidence/PHASE19.md",),
    )


CAPABILITIES["model.lifecycle"] = Capability(
    "model.lifecycle",
    ExecutionKind.CPU,
    "closed_model_lifecycle",
    kind="model",
    maturity="deneysel",
    input_schema="DatasetVersion/v7 + SafeModelPackage/v1",
    output_type="ModelCard/v1 + PredictionParquet/v1",
    parameter_schema="PredictionMapping/v1",
    backend="skops/scikit-learn/polars",
    requirement_ids=tuple("F20-S00" + str(i) for i in range(1, 8)),
    evidence_refs=("docs/evidence/PHASE20.md",),
    supports=(("cancel", True), ("predict", True), ("safe_serialization", True)),
    limits=(("rows", 100000), ("package_bytes", 134217728)),
    help_links=(
        "model-card",
        "model-importance",
        "model-unknown-category",
        "model-new-data",
        "model-uncertainty",
    ),
)


CAPABILITIES["model.time-series"] = Capability(
    "model.time-series",
    ExecutionKind.CPU,
    "chronological_forecast",
    kind="model",
    maturity="deneysel",
    input_schema="DatasetVersion/v7",
    output_type="TimeSeriesRun/v1",
    parameter_schema="TimeSeriesSpec/v1",
    backend="polars/pandas/statsmodels",
    requirement_ids=tuple("F21-S00" + str(i) for i in range(1, 7)),
    evidence_refs=("docs/evidence/PHASE21.md",),
    supports=(
        ("cancel", True),
        ("rolling_origin", True),
        ("prediction_interval", False),
    ),
    limits=(("rows", 100000), ("groups", 20), ("horizon", 60)),
    help_links=(
        "timeseries-frequency",
        "timeseries-seasonality",
        "timeseries-lag",
        "timeseries-validation",
    ),
)


CAPABILITIES["text.inspect"] = Capability(
    "text.inspect",
    ExecutionKind.CPU,
    "local_text_analysis",
    kind="analysis",
    maturity="deneysel",
    input_schema="DatasetVersion/v7 + String/Null column",
    output_type="TextRun/v1",
    parameter_schema="TextSpec/v1",
    backend="polars/scikit-learn/Unicode",
    requirement_ids=tuple("F22-S00" + str(i) for i in range(1, 7)),
    evidence_refs=("docs/evidence/PHASE22.md",),
    supports=(("cancel", True), ("offline", True), ("raw_preview_opt_in", True)),
    limits=(("rows", 100000), ("candidate_vocab", 50000), ("ngram_max", 3)),
    help_links=("text-tokens", "text-language", "text-tfidf", "text-similarity"),
)


CAPABILITIES["workflow.recipe"] = Capability(
    "workflow.recipe",
    ExecutionKind.CPU,
    "declarative_replay",
    kind="transform",
    maturity="deneysel",
    input_schema="DatasetVersion/v7 + AnalysisRecipe/v1",
    output_type="RecipeDryRun/v1 + DatasetChange/v1 + DelayedPerformance/v1",
    parameter_schema="AnalysisRecipe/v1 + explicit ColumnId mapping",
    backend="polars",
    deterministic_policy="same data/seed/parameters yield same values; run/version/new lineage identities differ",
    supports=(("cancel", True), ("safe_serialization", True), ("retraining", False)),
    limits=(("steps", 100), ("recipe_bytes", 2097152), ("monitor_rows", 100000)),
    help_links=("workflow-recipe", "workflow-drift", "workflow-model"),
    requirement_ids=tuple("F23-S00" + str(i) for i in range(1, 7)),
    evidence_refs=("docs/evidence/PHASE23.md",),
)


# Extend the Phase 01 registry in place. Unknown is deliberately distinct from
# unsupported: legacy library/backend strings are never support evidence.
for adapter, dependencies in (
    ("parquet_dataset", ("pyarrow",)),
    ("arrow_dataset", ("pyarrow",)),
    ("avro", ("pyarrow", "fastavro")),
    ("orc", ("pyarrow",)),
    ("hdf5", ("pyarrow", "h5py")),
    ("xml", ("pyarrow", "defusedxml")),
    ("fixed_width", ("pyarrow",)),
    ("spss", ("pyarrow", "pyreadstat")),
    ("stata", ("pyarrow", "pyreadstat")),
    ("sas", ("pyarrow", "pyreadstat")),
):
    ident = "import." + adapter.replace("_", "-")
    CAPABILITIES[ident] = Capability(
        ident,
        ExecutionKind.IO,
        "bounded_native_" + adapter,
        kind="import",
        maturity="deneysel",
        backend="bounded-format/arrow/polars",
        input_schema="SourceRequest/v1 + immutable capture",
        output_type="DatasetVersion/v7 + source format metadata",
        parameter_schema="StructuredSettings/v1 additive Phase30 options",
        deterministic_policy="ordered parts; immutable hashes; explicit union; lossless native types; labels/user-missing/weights retained, never applied automatically",
        supports=(
            ("null", True),
            ("decimal", True),
            ("cancel", True),
            ("safe_serialization", True),
            ("streaming", True),
        ),
        limits=(
            ("columns", 256),
            ("rows", 10000000),
            ("preview_rows", 200),
            ("archive_members", 1024),
            ("expanded_bytes", 536870912),
        ),
        help_links=(
            "import-phase30",
            "import-partition",
            "import-schema-evolution",
            "import-category-labels",
            "import-decimal-precision",
        ),
        dependencies=dependencies,
        requirement_ids=tuple("F30-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE30.md",),
    )


for adapter in ("netcdf", "zarr", "hdf5_array"):
    ident = "import." + adapter.replace("_", "-")
    CAPABILITIES[ident] = Capability(
        ident,
        ExecutionKind.IO,
        "verified_local_array",
        kind="import",
        maturity="deneysel",
        backend="xarray/h5py/Pint/Arrow",
        input_schema="immutable local array capture",
        output_type="DatasetVersion/v7 + multidimensional metadata/v1",
        parameter_schema="StructuredSettings/v1 array options",
        supports=(
            ("cancel", True),
            ("offline", True),
            ("safe_serialization", True),
            ("streaming", True),
        ),
        limits=(("dimensions", 8), ("chunk_bytes", 16777216), ("rows", 10000000)),
        dependencies=("xarray", "h5netcdf", "zarr", "pint", "h5py"),
        help_links=("array-dimensions", "array-chunks", "array-units", "array-raster"),
        requirement_ids=tuple("F34-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE34.md",),
    )
for kind in ("array-heatmap", "array-profile"):
    ident = "chart." + kind
    CAPABILITIES[ident] = Capability(
        ident,
        ExecutionKind.CPU,
        kind,
        kind="chart",
        maturity="deneysel",
        backend="polars/Matplotlib",
        input_schema="verified array slice DatasetVersion/v7",
        output_type="ChartResult/v1",
        parameter_schema="ChartSpec/v1",
        supports=(("cancel", True), ("safe_serialization", True)),
        limits=(("points", 10000),),
        help_links=("array-raster", "array-chunks"),
        requirement_ids=("F34-S003",),
        evidence_refs=("docs/evidence/PHASE34.md",),
    )


# Phase35 extends the same capability registry, including the two existing distributions.

for _kind in _distribution_kinds + ("histogram", "box"):
    _ident = "chart." + _kind
    _capability = CAPABILITIES.get(_ident) or Capability(
        _ident,
        ExecutionKind.CPU,
        "chart_" + _kind,
        kind="chart",
        maturity="deneysel",
        backend="polars/numpy/scipy/Matplotlib Agg",
        input_schema="immutable DatasetVersion",
        output_type="ChartResult/v1",
        parameter_schema="ChartSpec/v1",
        help_links=("chart-" + _kind,),
    )
    CAPABILITIES[_ident] = _replace_distribution(
        _capability,
        supports=tuple(
            (n, v) for n, v in _capability.supports if n not in ("weights", "group")
        )
        + (
            ("weights", _kind in _weight_kinds),
            ("group", True),
            ("weight_frequency", _kind in _weight_kinds),
            ("weight_analytic", _kind in _weight_kinds),
            ("weight_survey", False),
            ("weight_sample_weight", False),
        ),
        limits=(
            ("points", 10000),
            ("facets", 4),
            ("kde_samples", 5000),
            ("swarm_samples", 500),
        ),
        dependencies=("polars", "numpy", "scipy", "matplotlib"),
        help_links=("chart-" + _kind, "chart-density", "chart-log"),
        requirement_ids=tuple("F35-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE35.md",),
    )


# Phase36: same registry and contract enrichment path.

for _kind in _multi_kinds:
    _ident = "chart." + _kind
    CAPABILITIES[_ident] = Capability(
        _ident,
        ExecutionKind.CPU,
        "chart_" + _kind,
        kind="chart",
        maturity="deneysel",
        backend="polars/numpy/scipy/Matplotlib Agg",
        input_schema="immutable DatasetVersion",
        output_type="ChartResult/v1",
        parameter_schema="ChartSpec/v1",
        supports=(("cancel", True), ("safe_serialization", True), ("group", True)),
        limits=(("columns", 6), ("panels", 36), ("facets", 4), ("points", 10000)),
        dependencies=("polars", "numpy", "scipy", "matplotlib"),
        help_links=("chart-" + _kind, "chart-conditional", "chart-overplotting"),
        requirement_ids=tuple("F36-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE36.md",),
    )


# Phase37 extends the sole registry; schema and user question remain discoverable.
for _kind in COMPOSITION_KINDS:
    _question = (
        "Bir bütünde hangi kategori ne kadar pay alıyor? payda bileşim toplam"
        if _kind
        in (
            "stacked-bar",
            "percent-bar",
            "stacked-area",
            "percent-area",
            "pie",
            "donut",
        )
        else "Hiyerarşi ağacında parçalar nerede? aynı toplam iki kez sayılıyor mu?"
        if _kind in ("treemap", "sunburst")
        else "Kaynak nereden nereye akıyor? giriş çıkış süreç geçiş"
        if _kind in ("sankey", "alluvial")
        else "Aşamalar arasında kaç kişi olay kalıyor? dönüşüm süreci"
        if _kind == "funnel"
        else "Başlangıçtan bitişe hangi değişim toplamı etkiledi?"
        if _kind == "waterfall"
        else "Hangi tarihler günler yoğun?"
        if _kind == "calendar"
        else "Hangi nedenler en büyük katkıyı yapıyor? öncelik sıralama"
        if _kind == "pareto"
        else "Ölçümleri kategorilere göre nasıl karşılaştırırım?"
    )
    CAPABILITIES["chart." + _kind] = Capability(
        "chart." + _kind,
        ExecutionKind.CPU,
        "chart_" + _kind,
        kind="chart",
        maturity="deneysel",
        backend="polars/numpy/Matplotlib Agg",
        input_schema=COMPOSITION_SCHEMAS[_kind],
        output_type="ChartResult/v1",
        parameter_schema="ChartSpec/v1",
        deterministic_policy=_question,
        supports=(
            ("cancel", True),
            ("safe_serialization", True),
            (
                "group",
                _kind
                in (
                    "stacked-bar",
                    "percent-bar",
                    "stacked-area",
                    "percent-area",
                    "radar",
                ),
            ),
        ),
        limits=(
            ("hierarchy_nodes", 200),
            ("flow_nodes", 50),
            ("flow_edges", 100),
            ("pie_categories", 6),
        ),
        dependencies=("polars", "numpy", "matplotlib"),
        help_links=("chart-" + _kind, "chart-denominator", "chart-double-counting"),
        requirement_ids=tuple("F37-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE37.md",),
    )


# Phase38 extends the single capability registry.


for _adapter in _GEO_FORMATS + ("tile", "geocoding"):
    CAPABILITIES["import." + _adapter] = Capability(
        "import." + _adapter,
        ExecutionKind.IO,
        "geo_source_" + _adapter,
        kind="import",
        maturity="deneysel",
        backend="GDAL/Pyogrio/Rasterio/PROJ/Shapely/Arrow",
        input_schema="StructuredSettings/v1; captured local vector/raster or explicit bounded network source",
        output_type="DatasetVersion/v7 + geospatial metadata",
        parameter_schema="StructuredSettings/v1 or ConnectorSpec/v1",
        deterministic_policy="immutable capture; explicit CRS/window; source identities; no automatic network/repair",
        supports=(
            ("cancel", True),
            ("safe_serialization", True),
            ("offline", _adapter not in ("tile", "geocoding")),
        ),
        limits=(("features", 10000), ("raster_cells", 65536)),
        dependencies=("shapely", "pyproj", "pyogrio", "rasterio"),
        help_links=("geo-crs", "geo-raster", "geo-online"),
        requirement_ids=tuple("F38-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE38.md",),
    )
for _kind, _schema in _GEO_SCHEMAS.items():
    CAPABILITIES["chart." + _kind] = Capability(
        "chart." + _kind,
        ExecutionKind.CPU,
        "offline_" + _kind,
        kind="chart",
        maturity="deneysel",
        backend="Shapely/PROJ/NumPy/Matplotlib",
        input_schema=_schema,
        output_type="ChartResult/v1",
        parameter_schema="ChartSpec/v1",
        deterministic_policy="Nerede yoğunluk var? Hangi bölgede sayım oran farklı? Çevrimdışı yerel harita; CRS/payda/eşik açık",
        supports=(("cancel", True), ("safe_serialization", True)),
        limits=(("features", 10000), ("raster_cells", 65536)),
        dependencies=("shapely", "pyproj", "numpy", "matplotlib"),
        help_links=("geo-crs", "geo-classification", "geo-maup"),
        requirement_ids=tuple("F38-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE38.md",),
    )
for _kind in sorted(_GEO_OPERATIONS):
    CAPABILITIES["operation." + _kind.replace("_", "-")] = Capability(
        "operation." + _kind.replace("_", "-"),
        ExecutionKind.CPU,
        _kind,
        kind="operation",
        maturity="deneysel",
        backend="Shapely/PROJ/NumPy/Polars",
        input_schema="DatasetVersion/v7; WKT or numeric coordinates; CRS; explicit second version for join",
        output_type="DatasetVersion/v7 + preview diagnostics",
        parameter_schema="OperationSpec/v1; declarative geo parameters",
        deterministic_policy="Preview before apply; immutable RowId/source IDs; repair/reprojection separate; metric projected CRS",
        supports=(("cancel", True), ("safe_serialization", True)),
        limits=(("features", 10000), ("Moran_n", 500), ("block_n", 2000)),
        dependencies=("shapely", "pyproj", "numpy", "polars"),
        help_links=("geo-crs", "geo-join", "geo-repair", "geo-leakage", "geo-weights"),
        requirement_ids=tuple("F38-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE38.md",),
    )


def _extend_contracts():
    from dataclasses import MISSING, fields, replace

    from veri_ufku.domain.contracts import (
        InputRole,
        InputSchema,
        LearningLink,
        MethodSupport,
        Parameter,
    )
    from veri_ufku.statistics.contracts import METHODS, AnalysisSpec
    from veri_ufku.statistics.model_contracts import MODEL_METHODS

    numeric = ("Int*", "UInt*", "Float*", "Decimal")
    scalar = numeric + ("String", "Boolean", "Categorical", "Enum")
    for ident, capability in tuple(CAPABILITIES.items()):
        declared = dict(capability.supports)
        details = tuple(
            MethodSupport(
                name,
                "conditional" if declared[name] else "unsupported",
                "Mevcut adaptörün sınırları ve önkontrolü geçerlidir.",
            )
            if name in declared
            else MethodSupport(name)
            for name in (
                "null",
                "nan",
                "inf",
                "decimal",
                "tz",
                "missing",
                "weights",
                "group",
                "time",
                "sparse",
            )
        )
        operations = tuple(
            MethodSupport(name)
            for name in ("fit", "predict", "proba", "transform", "interval", "persist")
        )
        kwargs = dict(
            inputs=InputSchema(capability.input_schema),
            support_details=details,
            operations=operations,
            learning=tuple(LearningLink(h) for h in capability.help_links),
            assumptions=(capability.deterministic_policy,),
            parameters=(Parameter("spec", capability.parameter_schema),),
            artifact_kinds=("text",),
        )
        if ident.startswith("statistics."):
            method = ident.removeprefix("statistics.").replace("-", "_")
            path = next(
                (p for p, methods in METHODS.items() if method in methods), "advanced"
            )
            if method in MODEL_METHODS:
                path = "models"
            roles = (
                InputRole(
                    "x",
                    scalar if path == "categorical" else numeric,
                    meaning="Ölçüm; kimlik değildir.",
                ),
            )
            if path in ("numeric", "categorical"):
                roles += (InputRole("y", scalar if path == "categorical" else numeric),)
            if path in ("independent", "groups", "paired"):
                roles += (InputRole("group", scalar),)
            if path == "paired":
                roles += (
                    InputRole(
                        "key",
                        scalar,
                        meaning="Kişi/deney birimi; sıra numarası eşleştirme değildir.",
                    ),
                )
            params = tuple(
                Parameter(
                    f.name, str(f.type), None if f.default is MISSING else f.default
                )
                for f in fields(AnalysisSpec)
                if f.name != "view"
            )
            params = tuple(
                replace(p, choices=("two-sided", "less", "greater"))
                if p.name == "alternative"
                else replace(p, minimum=0.8, maximum=0.99)
                if p.name == "confidence"
                else p
                for p in params
            )
            assumptions = {
                "pearson": "Doğrusal ilişki; çıkarım için bağımsız çiftler ve uygun dağılım varsayımları.",
                "spearman": "Monoton ilişki; bağımsız çiftler; sıra bağı ve küçük örnek sınırlarını inceleyin.",
                "paired_t": "Anahtarla eşlenmiş kişiler; kişi içi farkların dağılımını inceleyin.",
                "wilcoxon": "Anahtarla eşleme; farkların simetrisi; genel medyan farkı testi değildir.",
                "anova": "Bağımsız gruplar, uygun artık dağılımı ve eşit varyans.",
                "welch_t": "Bağımsız iki grup; ortalama çıkarımı için dağılım ve örnek büyüklüğünü inceleyin.",
                "welch_anova": "Bağımsız gruplar; ortalama çıkarımının dağılım koşulları.",
                "mann_whitney": "Bağımsız gruplar; sıra üstünlüğü genel medyan farkı değildir.",
                "kruskal": "Bağımsız gruplar; dağılım sıraları genel medyan farkı değildir.",
                "chi2": "Bağımsız kayıtlar; beklenen hücre sayıları yeterli olmalı.",
                "fisher": "Bağımsız kayıtlar ve tam 2×2 kategori tablosu.",
            }
            kwargs.update(
                inputs=InputSchema("AnalysisSpec/v1", roles, "dense"),
                parameters=params,
                assumptions=(
                    assumptions.get(method, capability.deterministic_policy),
                    "Ölçüm ve gözlem birimini açıkça onaylayın.",
                ),
                operations=tuple(
                    MethodSupport(
                        n,
                        "supported" if n == "persist" else "unsupported",
                        "Atomik JSON/RowId artifact kaydı."
                        if n == "persist"
                        else "Bu istatistik adaptörü bu işlemi sunmaz.",
                    )
                    for n in (
                        "fit",
                        "predict",
                        "proba",
                        "transform",
                        "interval",
                        "persist",
                    )
                ),
                support_details=tuple(
                    MethodSupport(n, status, reason)
                    for n, status, reason in (
                        (
                            "missing",
                            "conditional",
                            "Complete-case; dışlamalar ayrı sayılır.",
                        ),
                        (
                            "null",
                            "conditional",
                            "Eksik kayıtlar raporlanarak dışlanır.",
                        ),
                        (
                            "nan",
                            "conditional",
                            "Sonlu olmayan değerler raporlanarak dışlanır.",
                        ),
                        (
                            "inf",
                            "conditional",
                            "Sonlu olmayan değerler raporlanarak dışlanır.",
                        ),
                        (
                            "decimal",
                            "conditional",
                            "Float64 kaybı varsayılan ret; açık yaklaşık izin gerekir.",
                        ),
                        (
                            "tz",
                            "unsupported",
                            "Zaman sütunu ölçüm/kategori olarak kabul edilmez.",
                        ),
                        ("weights", "unsupported", "Ağırlıklı çıkarım uygulanmadı."),
                        (
                            "group",
                            "supported"
                            if path in ("independent", "groups", "paired")
                            else "unsupported",
                            "Bağımsızlık bloklaması değildir; seçilmiş grup/etiket rolü.",
                        ),
                        ("time", "unsupported", "Zamansal bağımlılık düzeltmesi yok."),
                        (
                            "sparse",
                            "unsupported",
                            "Yoğun seçilmiş sütunlar; sparse API yok.",
                        ),
                    )
                ),
                artifact_kinds=("text", "table", "log"),
                dependencies=("scipy", "polars", "numpy"),
                cost="En fazla100.000 kayıt/20 grup; tam seçilmiş sütunlar; mevcut CPU/RAM/disk/iptal bütçesi.",
            )
        if ident.startswith("statistics.dimension-"):
            from veri_ufku.statistics.dimension_contracts import (
                REDUCERS,
                SELECTORS,
                VISUAL,
            )

            kwargs.update(
                inputs=InputSchema(
                    "NumericRepresentation/v1",
                    roles=(
                        InputRole(
                            "features",
                            ("Int*", "Float*"),
                            meaning="ordered numeric baseline measurements, no identifiers/categories",
                        ),
                        InputRole(
                            "y",
                            ("Int*", "Float*"),
                            required=False,
                            meaning="predeclared numeric regression or binary target for nested CV only",
                        ),
                    ),
                    storage="bounded immutable numeric Parquet→dense; explicit CSR only SVD/NMF",
                ),
                parameters=tuple(
                    Parameter(
                        n,
                        str(f.type),
                        default=f.default
                        if isinstance(f.default, (str, int, float, bool))
                        else None,
                    )
                    for n, f in AnalysisSpec.__dataclass_fields__.items()
                ),
                assumptions=(
                    "Independent rows only; model_input uses nested train-fold fits; full-fit compression/visual outputs are not CV-ready. Embedding coordinates are not classes/causes.",
                ),
                operations=tuple(
                    MethodSupport(
                        n,
                        "supported"
                        if n in ("fit", "persist")
                        or n == "transform"
                        and capability.method not in VISUAL
                        else "unsupported",
                        "Numeric safe fitted transform only; no downstream estimator prediction/deployment lifecycle or p/CI from an embedding.",
                    )
                    for n in (
                        "fit",
                        "predict",
                        "proba",
                        "transform",
                        "interval",
                        "persist",
                    )
                ),
                support_details=tuple(
                    MethodSupport(n, status, reason)
                    for n, status, reason in (
                        (
                            "missing",
                            "conditional",
                            "Explicit reject/mean; fit-only imputation; all-missing train column rejected.",
                        ),
                        (
                            "weights",
                            "unsupported",
                            "No weighted PCA/selection in initial numeric path.",
                        ),
                        (
                            "group",
                            "unsupported",
                            "Existing group/time validation must not be replaced with iid random fallback; unsupported here.",
                        ),
                        (
                            "time",
                            "unsupported",
                            "Temporal forecasting representation pipeline separate scope.",
                        ),
                        ("decimal", "unsupported", "No silent precision conversion."),
                        (
                            "sparse",
                            "conditional"
                            if capability.method in ("dimension_svd", "dimension_nmf")
                            else "unsupported",
                            "Explicit table→CSR no centering; source dense materialization and reconstruction cost budgeted; no native sparse source claim.",
                        ),
                        (
                            "inverse",
                            "conditional"
                            if capability.method in REDUCERS
                            else "unsupported",
                            "Approximate reconstructed original numeric feature units for reducers; selected-out columns cannot be recovered; t-SNE/UMAP safe inverse unavailable.",
                        ),
                        (
                            "explained_variance",
                            "supported"
                            if capability.method
                            in (
                                "dimension_pca",
                                "dimension_incremental_pca",
                                "dimension_svd",
                            )
                            else "unsupported",
                            "SVD projected variance is not centered PCA fraction; no invented variance for NMF/ICA/t-SNE/UMAP.",
                        ),
                        (
                            "selection_stability",
                            "supported"
                            if capability.method in SELECTORS
                            else "unsupported",
                            "Original-column support frequency and outer-fold Jaccard; not truth/causal importance.",
                        ),
                    )
                ),
                artifact_kinds=("text", "table", "chart", "model", "log"),
                dependencies=capability.dependencies,
                cost="5000compression/2000visual/1000model rows;20features/10selectionfeatures;3000fit upper bound; current RAM/disk/wall/cancel budget.",
            )
        if ident.startswith("statistics.survival-"):
            from veri_ufku.statistics.survival_contracts import CENSORING, MODELS

            kwargs.update(
                inputs=InputSchema(
                    "SurvivalObservation/v1",
                    roles=(
                        InputRole(
                            "x",
                            ("Int*", "Float*"),
                            meaning="duration in explicit common unit",
                        ),
                        InputRole(
                            "y",
                            ("Int*", "Float*"),
                            meaning="event0censored/1event; CIF explicitly labelled1..K",
                        ),
                        InputRole(
                            "key", scalar, meaning="one independent subject per row"
                        ),
                        InputRole(
                            "group",
                            scalar,
                            required=False,
                            meaning="KM/logrank/CIF group or Cox strata; not dependence clusters",
                        ),
                        InputRole(
                            "features",
                            ("Int*", "Float*"),
                            required=False,
                            meaning="static baseline covariates; counting-process execution unsupported",
                        ),
                    ),
                    storage="immutable Parquet; safe JSON numeric model",
                ),
                parameters=tuple(
                    Parameter(
                        n,
                        str(f.type),
                        default=f.default
                        if isinstance(f.default, (str, int, float, bool))
                        else None,
                    )
                    for n, f in AnalysisSpec.__dataclass_fields__.items()
                ),
                assumptions=(
                    "Independent censoring/truncation, shared time origin/unit, independent subjects; Cox PH or AFT lognormal model conditional assumptions; no causal interpretation.",
                ),
                operations=tuple(
                    MethodSupport(
                        n,
                        "conditional"
                        if n in ("fit", "persist")
                        or n == "predict"
                        and capability.method in MODELS
                        or n == "interval"
                        and capability.method != "survival_cif"
                        else "unsupported",
                        "Safe numeric persistence; models predict only supported right-censoring profile/time support and no diagnostic blocker; no prediction CI; no Brier/AUC backend.",
                    )
                    for n in (
                        "fit",
                        "predict",
                        "proba",
                        "transform",
                        "interval",
                        "persist",
                    )
                ),
                support_details=tuple(
                    MethodSupport(n, status, reason)
                    for n, status, reason in (
                        (
                            "missing",
                            "unsupported",
                            "Null is not censoring; no silent drop/imputation.",
                        ),
                        (
                            "weights",
                            "unsupported",
                            "Survey/frequency/sample weights unsupported.",
                        ),
                        (
                            "group",
                            "conditional",
                            "Independent comparison groups or Cox strata, not cluster dependence; AFT group unsupported.",
                        ),
                        ("time", "supported", "Explicit duration and common unit."),
                        ("decimal", "unsupported", "No implicit precision conversion."),
                        (
                            "sparse",
                            "unsupported",
                            "Dense selected baseline columns only.",
                        ),
                        (
                            "right_censoring",
                            "supported",
                            "All binary-event templates; CIF separately coded competing_right.",
                        ),
                        (
                            "left_truncation",
                            "conditional"
                            if "left_truncated_right" in CENSORING[capability.method]
                            else "unsupported",
                            "KM/logrank entry<t; Cox backend entry<=t. Delayed-entry prediction/metrics unsupported.",
                        ),
                        (
                            "interval_censoring",
                            "unsupported",
                            "No validated interval likelihood/Turnbull backend.",
                        ),
                        (
                            "left_censoring",
                            "unsupported",
                            "No validated left-censoring backend.",
                        ),
                        (
                            "competing_risk",
                            "supported"
                            if capability.method == "survival_cif"
                            else "unsupported",
                            "CIF all observed causes, no silent censoring of competing events.",
                        ),
                        (
                            "time_dependent_covariate",
                            "unsupported",
                            "SurvivalCountingProcess/v1 schema validation only; fit backend not validated.",
                        ),
                        (
                            "c_index",
                            "conditional"
                            if capability.method in MODELS
                            else "unsupported",
                            "Training Harrell comparable-pair C, right only, no pooled strata/entry; censoring sensitive, no IPCW/validation claim.",
                        ),
                        (
                            "time_dependent_brier",
                            "unsupported",
                            "Validated IPCW train/evaluation censoring support not implemented.",
                        ),
                        (
                            "time_dependent_auc",
                            "unsupported",
                            "Validated censoring-aware evaluation backend not implemented.",
                        ),
                    )
                ),
                artifact_kinds=("text", "table", "chart", "model", "log")
                if capability.method in MODELS
                else ("text", "table", "chart", "log"),
                dependencies=("statsmodels", "scipy", "numpy", "polars", "matplotlib"),
                cost="10000 descriptive/2000 model rows;5baseline predictors; bounded iterations, shared cancel/wall/RAM/disk limits.",
            )
        if ident.startswith("statistics.causal-"):
            kwargs.update(
                inputs=InputSchema(
                    "CausalObservation/v1",
                    roles=(
                        InputRole(
                            "x",
                            ("Int*", "Float*"),
                            meaning="complete post-treatment outcome",
                        ),
                        InputRole(
                            "y",
                            ("Int*", "Float*"),
                            meaning="binary treatment or ever-treated group",
                        ),
                        InputRole(
                            "key",
                            scalar,
                            meaning="independent unit; repeated only balanced DiD",
                        ),
                        InputRole(
                            "time_column",
                            ("Int*", "Float*"),
                            meaning="explicit numeric period, user-justified temporal order",
                        ),
                        InputRole(
                            "features",
                            ("Int*", "Float*"),
                            required=False,
                            meaning="pre-treatment adjustment set, <=5",
                        ),
                    ),
                    storage="immutable Parquet",
                ),
                parameters=tuple(
                    Parameter(
                        n,
                        str(f.type),
                        default=f.default
                        if isinstance(f.default, (str, int, float, bool))
                        else None,
                    )
                    for n, f in AnalysisSpec.__dataclass_fields__.items()
                ),
                assumptions=(
                    "DAG/user reasons do not prove identification; consistency, exchangeability, positivity, interference and method-specific conditions.",
                ),
                operations=tuple(
                    MethodSupport(
                        n,
                        "conditional"
                        if n in ("fit", "interval", "persist")
                        else "unsupported",
                        "Explicit template estimand; CI only randomized/DiD and asymptotic n>=100 AIPW/strong IV; point-only adjustment/IPW/matching.",
                    )
                    for n in (
                        "fit",
                        "predict",
                        "proba",
                        "transform",
                        "interval",
                        "persist",
                    )
                ),
                support_details=tuple(
                    MethodSupport(
                        n,
                        "conditional" if n == "time" else "unsupported",
                        "Complete numeric observations, no weighting/imputation/automatic transformations; balanced three-period DiD only.",
                    )
                    for n in (
                        "missing",
                        "weights",
                        "group",
                        "time",
                        "decimal",
                        "sparse",
                    )
                ),
                artifact_kinds=("text", "table", "log"),
                dependencies=("statsmodels", "sklearn", "scipy", "numpy", "polars"),
                cost="2000 iid rows or3000 balanced DiD rows/5 covariates; current ComputeBudget and cancellable worker.",
            )
        if ident.startswith("statistics.bayes-"):
            kwargs.update(
                inputs=InputSchema(
                    "BayesObservation/v1",
                    roles=(
                        InputRole(
                            "x",
                            ("Int*", "Float*", "Boolean"),
                            meaning="outcome; finite complete observations",
                        ),
                        InputRole(
                            "features",
                            ("Int*", "Float*"),
                            required=False,
                            meaning="raw numeric predictors; explicit units",
                        ),
                        InputRole(
                            "group",
                            ("String", "Int32", "Int64"),
                            required=False,
                            meaning="hierarchical random intercept labels",
                        ),
                    ),
                    storage="immutable Parquet",
                ),
                parameters=tuple(
                    Parameter(
                        n,
                        str(f.type),
                        default=f.default
                        if isinstance(f.default, (str, int, float, bool))
                        else None,
                    )
                    for n, f in AnalysisSpec.__dataclass_fields__.items()
                ),
                assumptions=(
                    "User-declared units/prior; Gaussian or Bernoulli likelihood; diagnostic checks do not certify model truth.",
                ),
                operations=tuple(
                    MethodSupport(
                        n,
                        "supported"
                        if n in ("fit", "interval", "persist")
                        else "unsupported",
                        "Bounded NUTS templates; no arbitrary prediction or user code.",
                    )
                    for n in (
                        "fit",
                        "predict",
                        "proba",
                        "transform",
                        "interval",
                        "persist",
                    )
                ),
                support_details=tuple(
                    MethodSupport(
                        n,
                        "conditional"
                        if n == "group" and ident.endswith("hierarchical")
                        else "unsupported",
                        "Complete finite numeric observations; random intercept only for hierarchical template.",
                    )
                    for n in (
                        "missing",
                        "weights",
                        "group",
                        "time",
                        "decimal",
                        "sparse",
                    )
                ),
                artifact_kinds=("text", "table", "chart", "model", "log"),
                dependencies=("pymc", "arviz", "h5netcdf"),
                cost="4–1000 complete rows/5 predictors;2–4chains;2M likelihood cells; two-prior NUTS budget.",
            )
        if capability.method.startswith("experiment_"):
            kwargs.update(
                inputs=InputSchema(
                    "AnalysisSpec/v1",
                    (
                        InputRole(
                            "key",
                            scalar,
                            False,
                            meaning="Unique independent randomization unit, one row per unit.",
                        ),
                        InputRole("x", numeric, False),
                        InputRole("group", scalar, False),
                    ),
                    "dense",
                ),
                support_details=tuple(
                    MethodSupport(n, state, reason)
                    for n, state, reason in (
                        (
                            "missing",
                            "conditional",
                            "Full roster retained; missing outcomes suppress ITT inference.",
                        ),
                        (
                            "null",
                            "conditional",
                            "Measurement null counted; identity/arm null rejected.",
                        ),
                        ("nan", "unsupported", "NaN/inf measurement rejected."),
                        ("inf", "unsupported", "NaN/inf measurement rejected."),
                        ("decimal", "unsupported", "No silent precision loss."),
                        (
                            "weights",
                            "unsupported",
                            "Independent unweighted units only.",
                        ),
                        (
                            "group",
                            "conditional",
                            "Two assigned-arm labels, not cluster dependence.",
                        ),
                        ("time", "unsupported", "Sequential monitoring disabled."),
                        ("sparse", "unsupported", "Dense selected columns."),
                    )
                ),
                dependencies=capability.dependencies,
                cost="100000 full-roster independent units, bounded shared budget; a priori power not observed power.",
            )
        if capability.method.startswith("advanced_"):
            advanced_details = tuple(
                d for d in details if d.name not in dict(capability.supports)
            )
            kwargs.update(
                inputs=InputSchema(
                    "AnalysisSpec/v1",
                    (
                        InputRole("x", scalar),
                        InputRole("features", numeric, False),
                        InputRole("weight", numeric, False),
                        InputRole("strata", scalar, False),
                        InputRole("psu", scalar, False),
                    ),
                    "dense",
                ),
                support_details=advanced_details
                + tuple(
                    MethodSupport(
                        n,
                        "conditional" if yes else "unsupported",
                        "Explicit closed recipe; typed weight and design validation before run.",
                    )
                    for n, yes in capability.supports
                    if not n.startswith("weight_")
                )
                + tuple(
                    MethodSupport(
                        "weight_" + w,
                        "supported"
                        if dict(capability.supports).get("weight_" + w)
                        else "unsupported",
                        "Frequency repeats / analytic inverse variance / survey design / sample loss contribution are distinct.",
                    )
                    for w in ("frequency", "analytic", "survey", "sample_weight")
                ),
                cost="MI <=5000 rows/20 fields/20 realizations/30 iterations; other <=10000 rows; no silent sampling; shared budget/cancel.",
            )
        if capability.method.startswith("immutable_contract_"):
            candidate_only = ident in (
                "operation.entity-candidates",
                "operation.category-candidates",
            )
            kwargs.update(
                artifact_kinds=("text", "table", "log"),
                dependencies=("polars",),
                operations=tuple(
                    MethodSupport(
                        name,
                        "supported"
                        if name in ("transform", "persist") and not candidate_only
                        else "unsupported",
                        "Kapalı tarif / insan onayı / değişmez sürüm ve atomik yayın."
                        if name in ("transform", "persist") and not candidate_only
                        else "Aday incelemesi veya bu yöntemin kapsamı dışında.",
                    )
                    for name in (
                        "fit",
                        "predict",
                        "proba",
                        "transform",
                        "interval",
                        "persist",
                    )
                ),
            )
        if capability.kind == "chart":
            from veri_ufku.charts.contracts import ChartSpec

            kwargs.update(
                parameters=tuple(
                    Parameter(
                        f.name, str(f.type), None if f.default is MISSING else f.default
                    )
                    for f in fields(ChartSpec)
                ),
                artifact_kinds=("table", "png", "svg", "pdf", "json"),
                cost="5000 KDE samples / 500 swarm / 10000 points / 4 facets; RAM and disk admission.",
                operations=tuple(
                    MethodSupport(
                        name,
                        "supported" if name == "persist" else "unsupported",
                        "Immutable ProjectStore artifacts"
                        if name == "persist"
                        else "Chart calculation does not expose this operation.",
                    )
                    for name in (
                        "fit",
                        "predict",
                        "proba",
                        "transform",
                        "interval",
                        "persist",
                    )
                ),
                support_details=details
                + tuple(
                    MethodSupport(
                        "weight_" + w,
                        "conditional"
                        if dict(capability.supports).get("weight_" + w)
                        else "unsupported",
                        "Explicit descriptive weight semantics; not survey inference.",
                    )
                    for w in ("frequency", "analytic", "survey", "sample_weight")
                ),
            )
            if ident.removeprefix("chart.") in COMPOSITION_KINDS:
                kwargs["inputs"] = InputSchema(
                    capability.input_schema,
                    (
                        InputRole("x", scalar + ("Date", "Datetime"), False),
                        InputRole("y", numeric, False),
                        InputRole("group", scalar, False),
                        InputRole("parent", ("String",), False),
                        InputRole("target", ("String",), False),
                        InputRole("entity", scalar, False),
                        InputRole("waterfall_role", ("String",), False),
                        InputRole("columns", numeric, False),
                    ),
                    "dense",
                )
                kwargs["cost"] = (
                    "Bounded:500 composition cells;200 tree nodes/depth8;50 flow nodes/100 edges;6 pie categories;12 funnel stages;1 calendar year;3–6 radar axes. ComputeBudget CPU/RAM/disk/cancel."
                )
        if (
            ident.startswith("statistics.")
            and ident.removeprefix("statistics.").replace("-", "_") in MODEL_METHODS
        ):
            model_method = ident.removeprefix("statistics.").replace("-", "_")
            kwargs.update(
                operations=tuple(
                    MethodSupport(
                        n,
                        "supported"
                        if n in ("fit", "persist")
                        or n == "predict"
                        and model_method != "repeated"
                        else "unsupported",
                        "safe JSON design/coefficients; marginal mixed prediction; no prediction interval",
                    )
                    for n in (
                        "fit",
                        "predict",
                        "proba",
                        "transform",
                        "interval",
                        "persist",
                    )
                ),
                support_details=tuple(
                    MethodSupport(
                        n,
                        "conditional"
                        if n in ("missing", "null", "nan", "inf")
                        else "supported"
                        if n == "weights"
                        and model_method == "wls"
                        or n == "group"
                        and model_method in ("mixed", "repeated")
                        else "unsupported",
                        "explicit model recipe; no silent conversion/unsupported combinations",
                    )
                    for n in (
                        "missing",
                        "null",
                        "nan",
                        "inf",
                        "decimal",
                        "tz",
                        "weights",
                        "group",
                        "time",
                        "sparse",
                    )
                ),
                artifact_kinds=("table", "chart", "model"),
            )
        if (
            ident.startswith("statistics.")
            and ident.removeprefix("statistics.").replace("-", "_")
            in _RESAMPLING_METHODS
        ):
            kwargs.update(
                operations=tuple(
                    MethodSupport(
                        n,
                        "supported" if n == "persist" else "unsupported",
                        "atomic JSON/RowId/draw-distribution export; statistical inference, no predictive model",
                    )
                    for n in (
                        "fit",
                        "predict",
                        "proba",
                        "transform",
                        "interval",
                        "persist",
                    )
                ),
                support_details=tuple(
                    MethodSupport(
                        n,
                        "conditional"
                        if n in ("missing", "null", "nan", "inf", "group", "time")
                        else "unsupported",
                        "explicit whole independent units; missing/nonfinite reject or declared complete case; time-block bootstrap only",
                    )
                    for n in (
                        "missing",
                        "null",
                        "nan",
                        "inf",
                        "decimal",
                        "tz",
                        "weights",
                        "group",
                        "time",
                        "sparse",
                    )
                ),
                artifact_kinds=("table", "text"),
            )
        if capability.kind == "dashboard":
            kwargs.update(
                artifact_kinds=("table", "png", "svg", "pdf", "html", "json"),
                cost="Full immutable snapshot up to10000 rows/source;16figure panels;shared ComputeBudget/process/cancel.",
                operations=tuple(
                    MethodSupport(
                        name,
                        "supported" if name == "persist" else "unsupported",
                        "ProjectStore saved view; local exclusive export",
                    )
                    for name in (
                        "fit",
                        "predict",
                        "proba",
                        "transform",
                        "interval",
                        "persist",
                    )
                ),
            )
        from veri_ufku.modeling.unsupervised_contracts import (
            METHODS as EXPLORATION_METHODS,
        )
        from veri_ufku.modeling.unsupervised_contracts import UnsupervisedSpec

        if ident in {"model." + m.replace("_", "-") for m in EXPLORATION_METHODS}:
            kwargs.update(
                inputs=InputSchema(
                    "DatasetVersion/v7",
                    (
                        InputRole(
                            "features",
                            ("Int*", "UInt*", "Float*"),
                            meaning="Finite numeric measurements; no nominal/ordinal codes; explicit standard/none scaling",
                        ),
                    ),
                ),
                parameters=tuple(
                    Parameter(
                        f.name, str(f.type), None if f.default is MISSING else f.default
                    )
                    for f in fields(UnsupervisedSpec)
                ),
                operations=tuple(
                    MethodSupport(
                        name,
                        "supported"
                        if name in ("fit", "persist")
                        else "conditional"
                        if name == "predict"
                        and ident
                        in ("model.kmeans", "model.isolation-forest", "model.iqr")
                        else "unsupported",
                        "Fit/heldout exploratory scope; Phase47 no new-file model persistence; GMM probabilities only captured fit rows",
                    )
                    for name in (
                        "fit",
                        "predict",
                        "proba",
                        "transform",
                        "interval",
                        "persist",
                    )
                ),
                cost="Bounded numeric fit; quadratic distance/silhouette upper RAM estimate; max3000 advanced/comparison rows; no implicit sample; shared ComputeBudget",
                artifact_kinds=("table", "json"),
                dependencies=("sklearn", "numpy", "polars"),
                requirement_ids=capability.requirement_ids
                + tuple("F47-S00" + str(i) for i in range(1, 5)),
                evidence_refs=capability.evidence_refs + ("docs/evidence/PHASE47.md",),
            )
        if ident.startswith("model.explain."):
            from veri_ufku.modeling.explanation import ExplainSpec

            defaults = ExplainSpec()
            kwargs.update(
                parameters=tuple(
                    Parameter(f.name, str(f.type), getattr(defaults, f.name))
                    for f in fields(ExplainSpec)
                ),
                operations=tuple(
                    MethodSupport(
                        name,
                        "supported"
                        if name == "persist"
                        else "conditional"
                        if name == "predict"
                        else "unsupported",
                        "bounded inspection of already fitted safe model; local-linear model-specific; optional SHAP unavailable until environment acceptance",
                    )
                    for name in (
                        "fit",
                        "predict",
                        "proba",
                        "transform",
                        "interval",
                        "persist",
                    )
                ),
                cost="5000source/500sample/100background/16originalfeatures/300000predictionrowpasses; user sample recorded; shared budget/cancel",
                artifact_kinds=("table", "chart", "json"),
                assumptions=(
                    "explanations are not causal",
                    "correlated features/extrapolation/background dependence",
                    "slice search exploratory; no fair model badge",
                ),
            )
        if ident.startswith("model.uncertainty."):
            from veri_ufku.modeling.uncertainty import UncertaintySpec

            defaults = UncertaintySpec()
            kwargs.update(
                parameters=tuple(
                    Parameter(f.name, str(f.type), getattr(defaults, f.name))
                    for f in fields(UncertaintySpec)
                ),
                operations=tuple(
                    MethodSupport(
                        name,
                        "supported"
                        if name in ("fit", "predict", "persist")
                        or name == "proba"
                        and capability.input_schema.startswith("classification;")
                        or name == "interval"
                        and capability.input_schema.startswith("regression;")
                        else "unsupported",
                        "bounded selected template only; frozen calibration/threshold; source fit isolated; no interval fabrication",
                    )
                    for name in (
                        "fit",
                        "predict",
                        "proba",
                        "transform",
                        "interval",
                        "persist",
                    )
                ),
                assumptions=(
                    "exchangeability for conformal marginal coverage",
                    "same label order; all train/calibration classes observed",
                    "group/time structure and horizon preserved; no random fallback",
                ),
                cost="1000rows/32features; 1base + calibration or 3quantile fits; shared ComputeBudget/process cancel; no final refit",
                artifact_kinds=("table", "chart", "model"),
            )
        if ident.startswith("model.search."):
            from veri_ufku.modeling.search_contracts import SearchSpec

            defaults = SearchSpec()
            kwargs.update(
                parameters=tuple(
                    Parameter(f.name, str(f.type), getattr(defaults, f.name))
                    for f in fields(SearchSpec)
                ),
                operations=tuple(
                    MethodSupport(
                        name,
                        "supported"
                        if name in ("fit", "persist")
                        and ident != "model.search.bayesian"
                        else "unsupported",
                        "Bounded nested tuning; result JSON persistence; recommended model training/new-file prediction separate",
                    )
                    for name in (
                        "fit",
                        "predict",
                        "proba",
                        "transform",
                        "interval",
                        "persist",
                    )
                ),
                cost="<=1000rows/32features/12trials per scope/4outer+4inner folds;600nativefit upper; concurrency1; shared RAM/wall budget; stacking adds internal OOF",
                artifact_kinds=("json",),
                requirement_ids=tuple("F49-S00" + str(i) for i in range(1, 6)),
                evidence_refs=("docs/evidence/PHASE49.md",),
            )
        if ident.startswith("model.family."):
            from veri_ufku.modeling.family_contracts import FamilyOptions, support

            purpose, family = ident.removeprefix("model.family.").split(".")
            family = family.replace("-", "_")
            table = support(family, purpose)
            kwargs.update(
                inputs=InputSchema(
                    "DatasetVersion/v7",
                    (
                        InputRole(
                            "features",
                            scalar,
                            meaning="numeric/category structured; no identifier, single target; train-only/native adapter",
                        ),
                        InputRole(
                            "target", scalar if purpose == "classification" else numeric
                        ),
                    ),
                ),
                parameters=tuple(
                    Parameter(f.name, str(f.type), f.default)
                    for f in fields(FamilyOptions)
                ),
                operations=tuple(
                    MethodSupport(
                        name,
                        "supported"
                        if name in ("fit", "persist", "predict")
                        and family not in OPTIONAL_FAMILIES
                        else "conditional"
                        if name == "proba" and table["predict_proba"]
                        else "unsupported",
                        "Result persistence supported; optional model save/new-file prediction disabled; CPU only; single-target adapter",
                    )
                    for name in (
                        "fit",
                        "predict",
                        "proba",
                        "transform",
                        "interval",
                        "persist",
                    )
                ),
                support_details=tuple(
                    MethodSupport(
                        name,
                        "conditional"
                        if name in ("missing", "null", "nan", "group")
                        or name == "time"
                        and family != "stacking"
                        or name == "weights"
                        and table["weights"] != "unsupported"
                        or name == "sparse"
                        and table["sparse"]
                        else "unsupported",
                        str(
                            table.get(
                                name,
                                table.get("nan")
                                if name in ("missing", "null")
                                else "same ValidationPlan; stacking inner independent/group only; unsupported combinations reject",
                            )
                        ),
                    )
                    for name in (
                        "missing",
                        "null",
                        "nan",
                        "inf",
                        "decimal",
                        "tz",
                        "weights",
                        "group",
                        "time",
                        "sparse",
                    )
                ),
                limits=(
                    ("rows", table["row_limit"]),
                    ("features", 256),
                    ("native_category", 255),
                ),
                artifact_kinds=("table", "model", "json"),
                cost="CPU bounded candidate+baseline same folds; SVM/KNN quadratic admission; stacking nested OOF+full child fits; no silent densification",
            )
        CAPABILITIES[ident] = replace(capability, **kwargs)


for adapter, dependencies in (
    ("postgresql", ("psycopg", "keyring")),
    ("mysql", ("pymysql", "keyring")),
    ("mariadb", ("pymysql", "keyring")),
    ("duckdb", ("duckdb",)),
    ("http", ()),
    ("s3", ("boto3", "keyring")),
):
    ident = "import." + adapter
    CAPABILITIES[ident] = Capability(
        ident,
        ExecutionKind.IO,
        "explicit_readonly_" + adapter,
        kind="import",
        maturity="deneysel",
        backend="connector/native-snapshot/polars",
        input_schema="ConnectorSpec/v1; explicit action; Secret Service reference",
        output_type="DatasetVersion/v7; immutable capture; consistency provenance",
        parameter_schema="ConnectorSpec/v1; validated identifiers and bound values",
        deterministic_policy="snapshot native values; source record keys; API without server snapshot guarantee explicitly non-atomic",
        supports=(
            ("cancel", True),
            ("safe_serialization", True),
            ("streaming", True),
            ("source_write", False),
        ),
        limits=(
            ("rows", 1000000),
            ("preview_rows", 200),
            ("bytes", 536870912),
            ("pages", 1000),
        ),
        help_links=(
            "connector-connection",
            "connector-query",
            "connector-snapshot",
            "connector-pagination",
            "connector-freshness",
        ),
        requirement_ids=tuple("F31-S00" + str(i) for i in range(1, 6)),
        evidence_refs=("docs/evidence/PHASE31.md",),
        dependencies=dependencies,
    )

# Phase32 extends the sole registry and the existing operation publication protocol.
for _kind, _help in (
    ("schema-contract", "contract-schema"),
    ("contract-check", "contract-schema"),
    ("entity-candidates", "contract-fuzzy"),
    ("category-candidates", "contract-fuzzy"),
    ("entity-merge", "contract-merge"),
    ("category-map", "contract-fuzzy"),
):
    CAPABILITIES["operation." + _kind] = Capability(
        "operation." + _kind,
        ExecutionKind.CPU,
        "immutable_contract_" + _kind,
        kind="operation",
        maturity="deneysel",
        backend="polars/python-difflib",
        input_schema="DatasetVersion/v7",
        output_type="OperationResult/v1",
        parameter_schema="OperationSpec/v1",
        deterministic_policy="closed rules; bounded candidates; explicit human approval; preserve source identities and inverse",
        supports=(("cancel", True), ("safe_serialization", True)),
        limits=(
            ("rules", 100),
            ("candidate_rows", 20000),
            ("candidate_pairs", 200),
        ),
        help_links=(_help,),
        requirement_ids=tuple("F32-S00" + str(i) for i in range(1, 6)),
        evidence_refs=("docs/evidence/PHASE32.md",),
    )


# Phase33 methods remain in the sole registry; weight support is explicit per method.

for _method in _ADVANCED_METHODS:
    _weights = {
        "weighted_mean": ("frequency", "analytic"),
        "weighted_ols": ("analytic",),
        "weighted_fit": ("sample_weight",),
        "survey_mean": ("survey",),
    }.get(_method, ())
    _help = (
        "missing-assumptions"
        if _method.startswith("missing_")
        else "missing-multiple"
        if _method.startswith("mi_")
        else "sampling-representation"
        if _method.startswith("sample_")
        else "weights-types"
    )
    _ident = "statistics." + _method.replace("_", "-")
    CAPABILITIES[_ident] = Capability(
        _ident,
        ExecutionKind.CPU,
        "advanced_" + _method,
        kind="analysis",
        maturity="deneysel",
        backend="numpy/scipy/sklearn",
        input_schema="DatasetVersion/v7",
        output_type="AnalysisResult/v1",
        parameter_schema="AnalysisSpec/v1",
        deterministic_policy="explicit assumption; no mechanism identification; seed/RowId/SourceRecordId; MI mean/OLS only; stratified WR Taylor survey; no source mutation",
        supports=(
            ("cancel", True),
            ("safe_serialization", True),
            ("weights", bool(_weights)),
        )
        + tuple(
            ("weight_" + w, w in _weights)
            for w in ("frequency", "analytic", "survey", "sample_weight")
        ),
        limits=(
            ("rows", 5000 if _method.startswith("mi_") else 10000),
            ("imputations", 20),
        ),
        help_links=(_help, "sampling-bias"),
        requirement_ids=tuple("F33-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE33.md",),
        dependencies=("numpy", "scipy", "sklearn"),
    )


for _ident, _method, _help, _output in (
    (
        "dashboard.canvas",
        "dashboard_evaluate",
        ("dashboard-question", "dashboard-filter-scope", "dashboard-kpi"),
        "DashboardResult/v1",
    ),
    ("figure.compose", "figure_compose", ("figure-readable",), "FigureExport/v1"),
):
    CAPABILITIES[_ident] = Capability(
        _ident,
        ExecutionKind.CPU,
        _method,
        kind="dashboard",
        input_schema="DatasetVersion/v7 + saved ChartSpec/v1",
        output_type=_output,
        parameter_schema="DashboardSpec/v1 + FigureSpec/v1",
        backend="local-polars-matplotlib-svg",
        deterministic_policy="immutable snapshot; explicit ColumnId mapping; RowId selection; no network or silent rebinding",
        supports=(("cancel", True), ("safe_serialization", True), ("offline", True)),
        limits=(("rows", 10000), ("figure_panels", 16)),
        help_links=_help,
        dependencies=("polars", "matplotlib"),
        requirement_ids=tuple("F39-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE39.md",),
    )


for _method in _MODEL_METHODS:
    _ident = "statistics." + _method.replace("_", "-")
    CAPABILITIES[_ident] = Capability(
        _ident,
        ExecutionKind.CPU,
        "model_" + _method,
        kind="analysis",
        backend="statsmodels",
        input_schema="DatasetVersion/v7",
        output_type="AnalysisResult/v1",
        parameter_schema="AnalysisSpec/v1",
        deterministic_policy="safe matrix; explicit baseline; full rank; no causal claim; bounded complete cases; no pickle",
        supports=(
            ("cancel", True),
            ("safe_serialization", True),
            ("predict", _method != "repeated"),
            ("weights", _method == "wls"),
        ),
        limits=(("rows", 10000), ("design_columns", 60), ("predictors", 12)),
        help_links=(
            "statistical-models",
            "statistical-model-" + _method.replace("_", "-"),
        ),
        requirement_ids=tuple("F40-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE40.md",),
        dependencies=("statsmodels", "numpy", "scipy"),
    )

for _method in _RESAMPLING_METHODS:
    _ident = "statistics." + _method.replace("_", "-")
    CAPABILITIES[_ident] = Capability(
        _ident,
        ExecutionKind.CPU,
        "resampling_" + _method,
        kind="analysis",
        backend="numpy/scipy explicit independent-unit adapter",
        input_schema="DatasetVersion/v7",
        output_type="AnalysisResult/v1",
        parameter_schema="AnalysisSpec/v1",
        deterministic_policy="seed PCG64; independent unit IDs; explicit exchangeability and family; no automatic p-hacking",
        supports=(("cancel", True), ("safe_serialization", True), ("group", True)),
        limits=(("rows", 2000), ("replicates", 10000), ("row_replicate_work", 2000000)),
        help_links=("resampling", "resampling-" + _method.replace("_", "-")),
        requirement_ids=tuple("F41-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE41.md",),
        dependencies=("numpy", "scipy", "polars"),
    )

for _method in EXPERIMENT_METHODS:
    _ident = "statistics." + _method.replace("_", "-")
    CAPABILITIES[_ident] = Capability(
        _ident,
        ExecutionKind.CPU,
        "experiment_" + _method,
        kind="analysis",
        backend="statsmodels/scipy fixed-horizon",
        input_schema="DatasetVersion/v7",
        output_type="AnalysisResult/v1",
        parameter_schema="AnalysisSpec/v1",
        deterministic_policy="predeclared fixed horizon; independent two-arm units; seed local draft, no real assignment or contact",
        supports=(("cancel", True), ("safe_serialization", True)),
        limits=(("rows", 100000),),
        help_links=("experiment-plan", "experiment-" + _method.replace("_", "-")),
        requirement_ids=tuple("F42-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE42.md",),
        dependencies=("statsmodels", "scipy", "numpy", "polars"),
    )

for _method in BAYES_METHODS:
    _ident = "statistics." + _method.replace("_", "-")
    CAPABILITIES[_ident] = Capability(
        _ident,
        ExecutionKind.CPU,
        "bayes_" + _method,
        kind="analysis",
        backend="PyMC CPU NUTS",
        input_schema="DatasetVersion/v7",
        output_type="AnalysisResult/v1",
        parameter_schema="AnalysisSpec/v1",
        deterministic_policy="fixed safe templates; raw units; seeded sampling; diagnostics never certify model truth; no user code",
        supports=(("cancel", True), ("safe_serialization", True)),
        limits=(("rows", 1000), ("predictors", 5), ("chains", 4), ("draws", 2000)),
        help_links=(
            "bayes",
            "bayes-" + _method.removeprefix("bayes_").replace("_", "-"),
        ),
        requirement_ids=tuple("F43-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE43.md",),
        dependencies=("pymc", "arviz", "h5netcdf"),
    )

for _method in CAUSAL_METHODS:
    _ident = "statistics." + _method.replace("_", "-")
    CAPABILITIES[_ident] = Capability(
        _ident,
        ExecutionKind.CPU,
        _method,
        kind="analysis",
        backend="NumPy/SciPy/statsmodels fixed causal templates",
        input_schema="DatasetVersion/v7",
        output_type="AnalysisResult/v1",
        parameter_schema="AnalysisSpec/v1",
        deterministic_policy="declared DAG and assumptions; seeded out-of-fold nuisance; no causal feature ranking",
        supports=(("cancel", True), ("safe_serialization", True)),
        limits=(("rows", 3000), ("predictors", 5)),
        help_links=(
            "causal",
            "causal-" + _method.removeprefix("causal_").replace("_", "-"),
        ),
        requirement_ids=tuple("F44-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE44.md",),
        dependencies=("statsmodels", "sklearn", "scipy", "numpy", "polars"),
    )

for _method in SURVIVAL_METHODS:
    _ident = "statistics." + _method.replace("_", "-")
    CAPABILITIES[_ident] = Capability(
        _ident,
        ExecutionKind.CPU,
        _method,
        kind="analysis",
        backend="statsmodels right-censored KM/logrank/Cox/CIF; scipy lognormal AFT MLE",
        input_schema="DatasetVersion/v7",
        output_type="AnalysisResult/v1",
        parameter_schema="AnalysisSpec/v1",
        deterministic_policy="independent censoring declared; no silent censoring recode; numeric safe models only",
        supports=(
            ("cancel", True),
            ("safe_serialization", True),
            ("predict", _method in ("survival_cox", "survival_aft")),
            ("persist", True),
        ),
        limits=(("rows", 10000), ("model_rows", 2000), ("predictors", 5)),
        help_links=("survival", "survival-" + _method.removeprefix("survival_")),
        requirement_ids=tuple("F45-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE45.md",),
        dependencies=("statsmodels", "scipy", "numpy", "polars", "matplotlib"),
    )

for _method in DIMENSION_METHODS:
    _ident = "statistics." + _method.replace("_", "-")
    CAPABILITIES[_ident] = Capability(
        _ident,
        ExecutionKind.CPU,
        _method,
        kind="analysis",
        backend="sklearn numeric decomposition/selection pipelines; optional umap-learn",
        input_schema="DatasetVersion/v7",
        output_type="AnalysisResult/v1",
        parameter_schema="AnalysisSpec/v1",
        deterministic_policy="seeded predeclared purpose/scope; inner train-only preprocessing/selection; test rows/labels not plotted; no real-class discovery claim",
        supports=(
            ("cancel", True),
            ("safe_serialization", True),
            ("transform", _method not in ("dimension_tsne", "dimension_umap")),
            ("inverse", _method in DIMENSION_METHODS[:5]),
        ),
        limits=(
            ("rows", 5000),
            ("model_rows", 1000),
            ("visual_rows", 2000),
            ("predictors", 20),
            ("selection_predictors", 10),
        ),
        help_links=(
            "dimensions",
            "dimension-" + _method.removeprefix("dimension_").replace("_", "-"),
        ),
        requirement_ids=tuple("F46-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE46.md",),
        dependencies=("sklearn", "scipy", "numpy", "polars", "matplotlib")
        + (("umap",) if _method == "dimension_umap" else ()),
    )


for _purpose, _methods in (
    ("regression", REGRESSION_FAMILIES),
    ("classification", FAMILY_METHODS),
):
    for _family in _methods:
        _id = "model.family." + _purpose + "." + _family.replace("_", "-")
        CAPABILITIES[_id] = Capability(
            _id,
            ExecutionKind.CPU,
            "family_" + _family,
            kind="model",
            maturity="deneysel",
            backend=_family if _family in OPTIONAL_FAMILIES else "scikit-learn",
            input_schema="DatasetVersion/v7; structured single-target; same ValidationPlan",
            output_type="BaselineRun/v1 + ModelCard/v1 + safe RowId prediction",
            parameter_schema="FamilyOptions/v1 + explicit_model",
            deterministic_policy="explicit family, CPU seed; no universal best; preprocessing train/inner-fold only; stacking meta OOF only",
            supports=(
                ("cancel", True),
                ("predict", _family not in OPTIONAL_FAMILIES),
                ("safe_serialization", _family not in OPTIONAL_FAMILIES),
            ),
            dependencies=(_family,)
            if _family in OPTIONAL_FAMILIES
            else ("sklearn", "skops"),
            help_links=("model-families", "family-" + _family.replace("_", "-")),
            requirement_ids=tuple("F48-S00" + str(i) for i in range(1, 5)),
            evidence_refs=("docs/evidence/PHASE48.md",),
        )

for _search_method in ("grid", "random", "bayesian"):
    _id = "model.search." + _search_method
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "bounded_search_" + _search_method,
        kind="model",
        maturity="deneysel",
        backend="optuna" if _search_method == "bayesian" else "scikit-learn",
        input_schema="DatasetVersion/v7 + PreparationSpec + joint ValidationPlan",
        output_type="SearchRun/v1; recommendation, nested evaluation, immutable trial JSON",
        parameter_schema="SearchSpec/v1 conditional discrete space",
        deterministic_policy="fixed inner/outer memberships and seed; final test outside search; resume source/space/environment checked",
        supports=(("cancel", True), ("safe_serialization", True)),
        limits=(("rows", 1000), ("features", 32), ("trials", 12), ("concurrency", 1)),
        dependencies=("sklearn", "optuna")
        if _search_method == "bayesian"
        else ("sklearn",),
        help_links=("model-search", "search-" + _search_method),
        requirement_ids=tuple("F49-S00" + str(i) for i in range(1, 6)),
        evidence_refs=("docs/evidence/PHASE49.md",),
    )

# Phase50 extends the same registry; interval support is template-specific.
for _uncertainty, _purpose, _label in (
    ("sigmoid", "classification", "Sigmoid probability calibration"),
    ("isotonic", "classification", "Isotonic probability calibration"),
    ("sets", "classification", "Conformal prediction sets"),
    ("interval", "regression", "Split conformal predictive interval"),
    ("quantile", "regression", "Gradient quantile predictive interval"),
    ("cqr", "regression", "Conformalized quantile regression"),
):
    _id = "model.uncertainty." + _uncertainty
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        _label,
        kind="model",
        backend="sklearn/native bounded CPU",
        input_schema=_purpose
        + "; PreparationSpec/v1 + ValidationPlan/v1; separate proper train/probability calibration/conformal calibration/validation/test",
        parameter_schema="UncertaintySpec/v1; finite costs/constraints/alpha; no user code",
        output_type="BaselineRun/v1 + ModelCard/v1 uncertainty extension; reliability table/coverage/width/set size",
        supports=(
            ("fit", True),
            ("predict", True),
            ("proba", _purpose == "classification"),
            ("interval", _purpose == "regression"),
            ("safe_serialization", True),
            ("cancel", True),
            ("gpu", False),
        ),
        limits=(("rows", 1000), ("features", 32)),
        dependencies=("sklearn", "skops"),
        deterministic_policy="shared seed/group/time/purge; frozen calibrator and validation threshold; final no refit; marginal exchangeability assumption only",
        help_links=(
            "model-uncertainty",
            "uncertainty-coverage",
            "uncertainty-probability",
            "uncertainty-threshold",
        ),
        requirement_ids=tuple(
            "F50-P" + str(i).zfill(3)
            for i in (
                (1, 2, 3, 4, 6, 9, 10)
                if _uncertainty == "sigmoid"
                else (1, 2, 3, 5, 6, 9, 10)
                if _uncertainty == "isotonic"
                else (1, 2, 3, 9, 10)
                if _uncertainty == "sets"
                else (7, 8, 10)
                if _uncertainty == "cqr"
                else (7, 10)
                if _uncertainty == "quantile"
                else (8, 10)
            )
        ),
        evidence_refs=("docs/evidence/PHASE50.md",),
    )

# Phase51 model inspections; optional SHAP computation requires its own environment evidence.
for _method in (
    "permutation",
    "pdp",
    "ice",
    "local-linear",
    "shap",
    "slices",
    "fairness",
    "what-if",
    "constrained",
):
    _id = "model.explain." + _method
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "Model explanation: " + _method,
        kind="model",
        input_schema="Safe supervised ModelCard/v1 + original immutable source validation/background fit RowIds",
        output_type="ExplanationRun/v1; global/local original-feature mapping; safe JSON/ProjectStore artifact",
        parameter_schema="ExplainSpec/v1; finite samples/grid/slices/explicit sensitive/constraints/immutable",
        backend="sklearn/native"
        if _method != "shap"
        else "optional shap ExactExplainer",
        supports=(
            ("predict", True),
            ("cancel", True),
            ("safe_serialization", True),
            ("fit", False),
            ("source_write", False),
        ),
        limits=(
            ("source_rows", 5000),
            ("sample_rows", 500),
            ("background_rows", 100),
            ("features", 16),
            ("prediction_row_passes", 300000),
        ),
        dependencies=("sklearn", "shap") if _method == "shap" else ("sklearn",),
        deterministic_policy="seeded explicit samples; frozen validation/background; original ColumnId mapping; no causal or fairness badge; source-bound atomic save",
        help_links=(
            "model-explanation",
            "explanation-correlated",
            "explanation-slices",
            "explanation-fairness",
            "explanation-scenarios",
        ),
        requirement_ids=tuple("F51-S00" + str(i) for i in range(1, 6)),
        evidence_refs=("docs/evidence/PHASE51.md",),
    )

# Phase53 temporal modules share the existing TimeSeriesRun/store/final-use journal.
for _method in (
    "decomposition",
    "stl",
    "acf",
    "pacf",
    "stationarity",
    "arima",
    "sarima",
    "sarimax",
    "var",
    "change-point",
    "local",
    "global-ridge",
    "rolling-origin",
    "mase",
    "probabilistic",
    "reconciliation",
    "croston",
    "classification",
    "clustering",
):
    _id = "model.temporal." + _method
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "Temporal: " + _method,
        kind="model",
        maturity="deneysel",
        input_schema="Immutable regular temporal panel, preserved group/RowId, explicit availability",
        parameter_schema="TimeSeriesSpec/v1 advanced TemporalSpec/v1",
        output_type="TimeSeriesRun/v1 safe JSON, actual model/origin/horizon metrics",
        backend="statsmodels/native/sklearn",
        dependencies=("statsmodels", "sklearn", "scipy", "polars"),
        supports=(
            ("cancel", True),
            ("group", True),
            ("time", True),
            ("safe_serialization", True),
            ("predict", False),
            ("source_write", False),
        ),
        limits=(
            ("rows", 4000),
            ("groups", 8),
            ("periods_per_group", 1000),
            ("fits", 200),
        ),
        help_links=("temporal-advanced",),
        requirement_ids=tuple("F53-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE53.md",),
        deterministic_policy="train-only chronological origins; explicit gap/embargo/covariate access; diagnostic significance not predictive success; no pickle model persistence",
    )

# Phase54: regular signal templates reuse TimeSeriesRun and the same atomic artifact store.
for _method in (
    "schema",
    "resample",
    "detrend",
    "window",
    "fft",
    "welch",
    "stft",
    "spectrogram",
    "peak",
    "filter",
    "zero-phase",
    "events",
    "classification",
):
    _id = "model.signal." + _method
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "Sinyal: " + _method,
        kind="model",
        maturity="deneysel",
        input_schema="Regular numeric time with explicit s/ms/us/ns, fs, channel units and recording/source RowIds",
        parameter_schema="TimeSeriesSpec/v1 advanced SignalSpec/v1; bounded closed templates",
        output_type="TimeSeriesRun/v1 SignalRun/v1 safe JSON, spectra/windows/source identity",
        backend="scipy/native/sklearn",
        dependencies=("scipy", "sklearn", "polars"),
        supports=(
            ("cancel", True),
            ("group", True),
            ("time", True),
            ("safe_serialization", True),
            ("source_write", False),
            ("predict", False),
        ),
        limits=(
            ("rows", 32768),
            ("recordings", 16),
            ("channels", 8),
            ("samples_per_recording", 8192),
            ("stft_cells", 131072),
            ("windows", 2000),
        ),
        help_links=("signal-sampling",),
        requirement_ids=tuple("F54-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE54.md",),
        deterministic_policy="explicit fs/units; FFT regular-only; offline zero-phase/polyphase; identity split before windows; no streaming deploy or unsafe model import",
    )

# Phase55 bounded native adapters reuse text worker/run/artifact and source identities.
for _method in (
    "tfidf",
    "nmf",
    "lda",
    "embeddings",
    "search",
    "ner",
    "sentiment",
    "classification",
    "annotation",
    "active-learning",
    "retrieval",
    "model",
):
    _id = "text.nlp." + _method
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "NLP: " + _method,
        kind="model",
        maturity="deneysel",
        input_schema="Immutable String/ColumnId/RowIds, explicit language and train/validation/test annotation schema",
        parameter_schema="TextSpec/v1 advanced NLPSpec/v1, safe LocalNLPBundle/v1 static vectors/literal NER/linear scores",
        output_type="TextRun/v1 NLPRun/v1 safe JSON artifact; human revisions and original codepoint/UTF16 offsets",
        backend="native/sklearn",
        dependencies=("sklearn", "polars"),
        supports=(
            ("cancel", True),
            ("safe_serialization", True),
            ("source_write", False),
            ("predict", False),
        ),
        limits=(
            ("rows", 500),
            ("characters", 500000),
            ("topic_count", 8),
            ("model_bytes", 16777216),
        ),
        help_links=("nlp-model-language",),
        requirement_ids=tuple("F55-S00" + str(i) for i in range(1, 6)),
        evidence_refs=("docs/evidence/PHASE55.md",),
        deterministic_policy="train-only vocab/topics/classifier/active pool; local safe bundles; original offsets; explicit user download; no transformer support/quality badge",
    )

# Phase56 closed CPU templates; GPU is deliberately unavailable pending real evidence.
for _template in ("mlp", "cnn"):
    _id = "model.neural." + _template
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "cpu_tensor_" + _template,
        kind="model",
        backend="torch2.13.0+cpu",
        dependencies=("torch",),
        input_schema="Numeric DatasetVersion/v7; explicit CNN NCHW row-major schema",
        output_type="NeuralRun/v1 safe full-state JSON checkpoint",
        parameter_schema="NeuralSpec/v1",
        deterministic_policy="Closed CPU architecture + seed + framework/thread/RNG; no cross-device guarantee",
        supports=(
            ("cancel", True),
            ("predict", True),
            ("safe_serialization", True),
            ("gpu", False),
            ("mixed_precision", False),
        ),
        limits=(("rows", 2000), ("features", 1024), ("epochs", 100)),
        help_links=("neural-training", "neural-checkpoint"),
        requirement_ids=tuple("F56-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE56.md",),
    )

# Phase57: separate bounded real image tasks; no general YOLO/U-Net claim.
for _vision in ("scan", "classification", "transfer", "detection", "segmentation"):
    _id = "model.vision." + _vision
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "Local image " + _vision,
        kind="model",
        backend="tiny RGB CNN"
        if _vision in ("classification", "transfer")
        else "native RGB pixel logistic"
        if _vision in ("detection", "segmentation")
        else "Pillow",
        dependencies=("PIL", "torch")
        if _vision in ("classification", "transfer")
        else ("PIL", "sklearn"),
        input_schema="VisionManifest/v1; DatasetVersion images+human annotations; whole-component group split",
        output_type="VisionRun/v1 safe JSON via neural artifacts",
        supports=(
            ("predict", _vision != "scan"),
            ("safe_serialization", True),
            ("cancel", True),
            ("gpu", False),
        ),
        limits=(("images", 256), ("pixels", 4000000)),
        help_links=("vision-images", "vision-iou"),
        requirement_ids=tuple("F57-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE57.md",),
        deterministic_policy="immutable image hash/RowId/SourceRecordId; human labels; duplicate/subject/video whole-group split; crop recorded; no auto download",
    )
CAPABILITIES["import.image-dataset"] = Capability(
    "import.image-dataset",
    ExecutionKind.IO,
    "Local image manifest",
    backend="Pillow12.3.0",
    help_links=("vision-images",),
    requirement_ids=("F57-S001",),
    evidence_refs=("docs/evidence/PHASE57.md",),
    dependencies=("PIL",),
    supports=(("source_write", False), ("cancel", True)),
    input_schema="local folder/immutable bundle; VisionManifest/v1",
    output_type="DatasetVersion/v7 + real image source snapshot",
)

# Phase58 separate offline audio tasks; speech runtime requires a user local model.
for _audio in ("features", "classification", "transcribe"):
    _id = "model.audio." + _audio
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "Local audio " + _audio,
        kind="model",
        backend="SoundFile/SciPy/sklearn"
        if _audio != "transcribe"
        else "optional local Vosk0.3.45; model required, runtime unvalidated",
        dependencies=("soundfile", "scipy", "sklearn")
        if _audio != "transcribe"
        else ("soundfile", "vosk"),
        input_schema="AudioManifest/v1; explicit channel/source frame segments; human labels, whole speaker/session/source components",
        output_type="AudioRun/v1 safe JSON through existing neural artifacts",
        supports=(
            ("predict", _audio == "classification"),
            ("safe_serialization", True),
            ("cancel", True),
            ("microphone", False),
            ("diarization", False),
            ("event_detection", False),
        ),
        limits=(("recordings", 64), ("segments", 256), ("frames", 2000000)),
        help_links=("audio-features", "audio-leakage", "audio-wer"),
        requirement_ids=tuple("F58-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE58.md",),
        deterministic_policy="immutable original PCM/file/frame IDs; fixed spectral features, train-only scaler/gain; no downloads",
    )
CAPABILITIES["import.audio-dataset"] = Capability(
    "import.audio-dataset",
    ExecutionKind.IO,
    "Local WAV/FLAC recordings",
    backend="SoundFile0.13.1/libsndfile",
    dependencies=("soundfile",),
    supports=(("source_write", False), ("cancel", True)),
    help_links=("audio-files",),
    requirement_ids=("F58-S001",),
    evidence_refs=("docs/evidence/PHASE58.md",),
    input_schema="bounded WAV/FLAC or AudioManifest/v1 local snapshot",
    output_type="DatasetVersion/v7 immutable audio source + segment metadata",
)

_extend_contracts()


def discover(query=""):
    from veri_ufku.learning.catalog import fold

    needle = fold(query)
    return tuple(
        c
        for c in CAPABILITIES.values()
        if not c.capability_id.startswith("demo.")
        and needle in fold(" ".join((c.capability_id, c.method, c.kind, *c.help_links)))
    )


CAPABILITIES["model.experiment-registry"] = Capability(
    "model.experiment-registry",
    ExecutionKind.IO,
    "Yerel experiment/model registry",
    kind="model",
    maturity="deneysel",
    backend="ProjectStore/native",
    input_schema="Existing BaselineRun/SearchRun/ModelChoice/FinalTestUse immutable identities",
    output_type="ExperimentComparison/v1 + append-only ExperimentEvent/v1",
    parameter_schema="run IDs, explicit metric/tags/model status/quota",
    supports=(
        ("source_write", False),
        ("safe_serialization", True),
        ("network", False),
        ("cancel", True),
    ),
    limits=(("comparison_runs", 32), ("tags", 16)),
    help_links=("experiment-registry",),
    requirement_ids=tuple("F52-S00" + str(i) for i in range(1, 6)),
    evidence_refs=("docs/evidence/PHASE52.md",),
    deterministic_policy="Existing run IDs retained; no reconstructed old hashes; protocol mismatch warns; state is local, no deploy",
)


def availability(capability):
    if capability.capability_id in ("model.special.pu", "model.stream.broker"):
        return (
            False,
            "Faz62 doğrulanmış backend/adaptör mevcut değil; ağ/PU otomatik başlatılmaz.",
        )
    from importlib.util import find_spec

    if capability.capability_id == "compute.dask-summary":
        from veri_ufku.jobs.dask_backend import available

        return (
            available(),
            "Optional Dask2026.8.0 yerel chunk adaptörü; GUI çalıştırıcısı ve remote executor yok.",
        )
    if capability.capability_id in ("model.monitor.cli", "model.monitor.api"):
        return (
            False,
            "Ayrı terminal eylemi: python -m veri_ufku.modeling.monitor_cli --help; batch/API opt-in gerekir, GUI veya proje açılışı server başlatmaz.",
        )
    if capability.capability_id == "workflow.schedule":
        return (
            False,
            "Yerel scheduler/daemon yok; uygulama kapalıyken otomatik koşu yok. CLI açıkça başlatılır.",
        )
    if capability.capability_id == "code.jupyter":
        return (
            False,
            "Managed Jupyter bağlantısı mevcut değil; notebook export harici Jupyter ile opsiyonel açılır.",
        )

    if capability.capability_id.startswith(
        "model.neural."
    ) or capability.capability_id in (
        "model.vision.classification",
        "model.vision.transfer",
    ):
        from importlib.metadata import PackageNotFoundError, version

        try:
            if version("torch") != "2.13.0+cpu":
                return (
                    False,
                    "Doğrulanmış optional torch2.13.0+cpu yok; otomatik indirme yapılmaz.",
                )
        except PackageNotFoundError:
            return False, "Optional CPU tensor backend yok; otomatik indirme yapılmaz."
    missing = [name for name in capability.dependencies if find_spec(name) is None]
    return (
        not missing,
        ""
        if not missing
        else "Eksik yerel bağımlılık: "
        + ", ".join(missing)
        + ". Doğrulanmış uygulama ortamını/yerel modül paketini etkinleştirin; uygulama komut çalıştırmaz.",
    )


def result_compatibility(capability_id, method_version=1, parameter_version=1):
    if capability_id.startswith("plugin.") and capability_id != "plugin.sdk":
        return (
            "readonly",
            "Kayıtlı plugin sonucu okunur; recompute yalnız explicit manifest/hash/environment/trust ile SDK panelinden başlatılır.",
        )
    capability = CAPABILITIES.get(capability_id)
    if capability is None:
        return (
            "readonly",
            "Bilinmeyen yöntem: kayıtlı sonuç salt okunur; yeniden çalıştırma kapalı.",
        )
    if (
        type(method_version) is not int
        or type(parameter_version) is not int
        or method_version != capability.semantic_version
        or parameter_version != capability.version
    ):
        return (
            "readonly",
            "Yöntem/parametre sürümü uyumsuz: sonucu okuyabilirsiniz; yeni tarifi açıkça yeniden oluşturun.",
        )
    return "compatible", ""


# Phase59 bounded native CPU recommendation, distinct query/group ranking schema.
for _recommendation in ("popularity", "content", "factorization", "ranker"):
    _id = "model.recommendation." + _recommendation
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "Offline recommendation " + _recommendation,
        kind="model",
        backend="native NumPy CPU",
        dependencies=("numpy", "polars"),
        input_schema="typed user/item/value/Unix seconds ColumnIds; LTR separate single-time query groups",
        output_type="RecommendationRun/v1 and RecommendationList/v1; shared neural safe artifacts",
        supports=(
            ("predict", True),
            ("safe_serialization", True),
            ("cancel", True),
            ("online_delivery", False),
        ),
        limits=(
            ("rows", 2000),
            ("users", 32),
            ("items", 128),
            ("features", 16),
            ("queries", 64),
        ),
        help_links=(
            "recommendation-feedback",
            "recommendation-evaluation",
            "recommendation-cold-start",
        ),
        requirement_ids=tuple("F59-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE59.md",),
        deterministic_policy="strict historical prefix; globally protected heldout; typed source IDs; recorded universe and seed",
    )

# Phase60 native descriptive discovery; no causal/predictive badge.
for _pattern in ("apriori", "fp_growth", "cohort", "funnel", "process", "conformance"):
    _id = "model.pattern." + _pattern.replace("_", "-")
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "Pattern discovery " + _pattern,
        kind="model",
        backend="native bounded Python/Polars",
        dependencies=("polars",),
        input_schema="transaction/item or entity/activity/offset timestamp; explicit duplicates, observation end and completion",
        output_type="PatternRun/v1 safe JSON in existing neural artifact journal; descriptive only",
        supports=(
            ("predict", False),
            ("cancel", True),
            ("safe_serialization", True),
            ("causal", False),
        ),
        limits=(("rows", 5000), ("entities", 2000), ("items", 64), ("activities", 32)),
        help_links=("pattern-support", "pattern-retention", "pattern-trace"),
        requirement_ids=tuple("F60-S00" + str(i) for i in range(1, 6)),
        evidence_refs=("docs/evidence/PHASE60.md",),
        deterministic_policy="typed source IDs, calendar/observation/tie policy, no silent data repair",
    )

# Phase61 bounded descriptive NetworkX graphs; predictive graph methods remain closed.
for _graph in ("degree", "centrality", "components", "shortest", "community", "layout"):
    _id = "model.graph." + _graph
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "Graph " + _graph,
        kind="model",
        backend="NetworkX3.7 CPU",
        dependencies=("networkx", "polars"),
        input_schema="GraphTable/v1 node/edge rows or edge table plus declared node dataset; explicit direction/weight/multiplicity",
        output_type="GraphRun/v1 existing safe artifact journal; full identity export",
        supports=(
            ("cancel", True),
            ("safe_serialization", True),
            ("predict", False),
            ("embedding", False),
            ("link_prediction", False),
        ),
        limits=(
            ("nodes", 256),
            ("edges", 2000),
            ("visual_nodes", 128),
            ("visual_edges", 512),
        ),
        help_links=("graph-structure", "graph-measures", "graph-leakage"),
        requirement_ids=tuple("F61-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE61.md",),
        deterministic_policy="typed IDs, original multigraph, explicit weight distance/strength, seeded view-only sample/layout",
    )
for _fmt in ("graphml", "gexf"):
    _id = "import." + _fmt
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "Static graph " + _fmt,
        kind="source",
        backend="defusedxml0.7.1",
        dependencies=("defusedxml", "polars"),
        input_schema="static flat GraphML/GEXF1.2; reject DTD/entity/mixed/dynamic/hierarchy",
        output_type="GraphTable/v1 immutable DatasetVersion",
        help_links=("graph-structure",),
        requirement_ids=("F61-S001",),
        evidence_refs=("docs/evidence/PHASE61.md",),
    )

# Phase62 local simulator; network broker and PU are deliberately unavailable.
for _stream in ("replay", "scaler", "partial-fit"):
    _id = "model.stream." + _stream
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "Yerel stream " + _stream,
        kind="model",
        backend="scikit-learn1.9.1 CPU",
        dependencies=("sklearn", "polars"),
        parameter_schema="StreamSpec/v1",
        input_schema="StreamEvent/v1 ordered integer ID; event/processing/feedback seconds; binary target; finite numeric features",
        output_type="StreamRun/v1 safe JSON numeric checkpoint; prequential development only",
        supports=(
            ("partial_fit", True),
            ("streaming", True),
            ("prequential", True),
            ("resume", True),
            ("cancel", True),
            ("safe_serialization", True),
            ("network_broker", False),
            ("offline_model_auto_online", False),
        ),
        limits=(
            ("rows", 100000),
            ("pending", 256),
            ("active_windows", 256),
            ("preview", 64),
            ("features", 16),
        ),
        help_links=("stream-window", "stream-prequential", "special-targets"),
        requirement_ids=("F62-S001", "F62-S002", "F62-S004"),
        evidence_refs=("docs/evidence/PHASE62.md",),
        deterministic_policy="fixed immutable snapshot, monotonic processing clock, next durable cursor, duplicate/reorder reject; explicit retrain",
    )

for _target in ("multilabel", "multioutput", "ordinal", "semisupervised"):
    _id = "model.special." + _target
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "Özel hedef " + _target,
        kind="model",
        backend="scikit-learn1.9.1 CPU",
        dependencies=("sklearn", "polars"),
        parameter_schema="TargetRecipe/v1",
        input_schema="TargetRecipe/v1 explicit train/pool/eval development roles; separate target schemas",
        output_type="SpecialTargetRun/v1 safe result and identity lineage; no new-data model package",
        supports=(
            ("predict", False),
            ("safe_serialization", True),
            ("cancel", True),
            ("final_test", False),
        ),
        limits=(("train", 256), ("eval", 256), ("pool", 128), ("features", 16)),
        help_links=("special-targets",),
        requirement_ids=("F62-S003", "F62-S004"),
        evidence_refs=("docs/evidence/PHASE62.md",),
        deterministic_policy="explicit development roles, train-only scaler; optional transductive eval FEATURES only, never eval labels",
    )

for _id in ("model.special.pu", "model.stream.broker"):
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "Unavailable: " + _id,
        kind="model",
        maturity="mevcut değil",
        input_schema="separate optional schema; no validated runtime",
        output_type="unavailable",
        supports=(("predict", False), ("network", False)),
        help_links=("special-targets", "stream-window"),
        requirement_ids=("F62-S001", "F62-S003"),
        evidence_refs=("docs/evidence/PHASE62.md",),
    )

# Phase63: a closed GUI profile bridge and explicit fresh-process workspace.
for _fmt in ("python", "sql", "notebook"):
    _id = "code." + _fmt
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.IO,
        "GUI numeric profile → " + _fmt,
        kind="export",
        parameter_schema="CodeRecipe/v1",
        input_schema="full dataset numeric measurement profile; no view/filter/other methods",
        output_type="reference-only ZIP; script/SQL/notebook plus environment lock",
        supports=(
            ("data_embedding", False),
            ("secret_embedding", False),
            ("arbitrary_python_reverse", False),
            ("safe_serialization", True),
        ),
        limits=(("sample", 10000), ("sql_rows", 100000)),
        dependencies=("polars",),
        help_links=("code-equivalence", "code-notebook-state", "code-sql-query"),
        requirement_ids=("F63-S001", "F63-S003", "F63-S004"),
        evidence_refs=("docs/evidence/PHASE63.md",),
        deterministic_policy="version/ColumnId/snapshot hash references; exact environment and engine lock; SQL subset explicit float tolerance",
    )
CAPABILITIES["code.workspace"] = Capability(
    "code.workspace",
    ExecutionKind.CPU,
    "Explicit user Python cell",
    kind="code",
    parameter_schema="CodeRun/v1 hash-only cell/config provenance",
    input_schema="user cell UTF8<=16KiB; explicit opt-in and execute",
    output_type="volatile bounded plain stdout/stderr; persistent status/hash only",
    supports=(
        ("cancel", True),
        ("timeout", True),
        ("os_sandbox", False),
        ("auto_execute", False),
        ("persistent_kernel", False),
    ),
    limits=(("cell_bytes", 16384), ("output_bytes", 65536), ("wall_seconds", 600)),
    help_links=("code-equivalence", "code-notebook-state"),
    requirement_ids=("F63-S002", "F63-S003", "F63-S004"),
    evidence_refs=("docs/evidence/PHASE63.md",),
    deterministic_policy="fresh interpreter each execute; no persistent notebook state or security sandbox claim",
)
CAPABILITIES["code.jupyter"] = Capability(
    "code.jupyter",
    ExecutionKind.IO,
    "Managed Jupyter integration unavailable",
    kind="code",
    maturity="mevcut değil",
    input_schema="separate optional external kernel integration",
    output_type="unavailable",
    supports=(("auto_execute", False), ("network", False)),
    help_links=("code-notebook-state",),
    requirement_ids=("F63-S003",),
    evidence_refs=("docs/evidence/PHASE63.md",),
)

# Phase64: a single registry supplies typed workflow ports and method versions.

for _kind, _out, _ports in (
    ("source", "dataset", ()),
    ("transform", "dataset", (("data", "dataset"),)),
    ("quality", "dataset", (("data", "dataset"),)),
    ("analysis", "report", (("data", "dataset"),)),
    ("train", "model", (("data", "dataset"),)),
    ("predict", "dataset", (("data", "dataset"), ("model", "model"))),
    ("export", "receipt", (("data", "dataset"),)),
):
    _id = "workflow." + _kind
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "Typed DAG " + _kind,
        kind="workflow",
        parameter_schema="OperationSpec/v1 + TypedDAG/v1",
        input_schema="typed ports + immutable DatasetVersion/RowId",
        inputs=_DagInput(_id, roles=tuple(_DagRole(p, (t,)) for p, t in _ports)),
        output_type=_out,
        supports=(
            ("cancel", True),
            ("cache", True),
            ("source_write", False),
            ("safe_serialization", True),
        ),
        limits=(("nodes", 24), ("cases", 8), ("source_rows", 10000)),
        help_links=("workflow-dag", "workflow-cache", "workflow-batch"),
        requirement_ids=tuple("F64-S00" + str(i) for i in range(1, 6)),
        evidence_refs=("docs/evidence/PHASE64.md",),
        deterministic_policy="validated roots/config/method/code/environment/artifact hash; isolated branches; no silent overwrite",
    )
CAPABILITIES["workflow.schedule"] = Capability(
    "workflow.schedule",
    ExecutionKind.IO,
    "Local schedule unavailable",
    kind="workflow",
    maturity="mevcut değil",
    help_links=("workflow-batch",),
    requirement_ids=("F64-S003",),
    evidence_refs=("docs/evidence/PHASE64.md",),
)

# Phase65: read-only recorded provenance and explicit reproducibility actions.
for _task, _out in (
    ("lineage", "LineageGraph/v1"),
    ("bundle", "ReproBundle/v1"),
    ("verify", "ReproComparison/v1"),
):
    _id = "repro." + _task
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "Recorded provenance / bounded reproducibility " + _task,
        kind="reproducibility",
        parameter_schema="ReproPlan/v1",
        input_schema="existing recorded IDs + immutable snapshot refs",
        output_type=_out,
        supports=(
            ("cancel", True),
            ("safe_serialization", True),
            ("source_write", False),
        ),
        limits=(("graph_nodes", 2000), ("bundle_bytes", 134217728), ("snapshots", 32)),
        help_links=(
            "repro-lineage",
            "repro-snapshot",
            "repro-environment",
            "repro-tolerance",
            "repro-record",
        ),
        requirement_ids=tuple("F65-S00" + str(i) for i in range(1, 6)),
        evidence_refs=("docs/evidence/PHASE65.md",),
        deterministic_policy="exact locked environment; profile Decimal80 exact; Float64 OLS coefficients/predictions bounded numeric policy; unsupported fail closed",
    )

# Conservative per-method execution declarations: absence is never lazy-fit support.
# Existing method-specific limits/support flags remain authoritative.
for _id, _cap in tuple(CAPABILITIES.items()):
    _streaming = dict(_cap.supports).get("streaming", False)
    CAPABILITIES[_id] = _replace_distribution(
        _cap,
        execution_memory=(
            "Sınırlı akış yolu beyanlı; fit/transform kapsamı yöntem sözleşmesine bağlı"
            if _streaming
            else "Bellekte/sınırlı; bellek dışı fit doğrulanmadı. Lazy okuma lazy fit anlamına gelmez"
        ),
    )

CAPABILITIES["compute.dask-summary"] = Capability(
    "compute.dask-summary",
    ExecutionKind.CPU,
    "bounded local numeric parquet reduction",
    kind="infrastructure",
    backend="optional dask 2026.8.0",
    input_schema="immutable numeric Parquet column",
    output_type="ChunkSummary/v1",
    help_links=("compute-resources",),
    requirement_ids=("F66-S001", "F66-S002", "F66-S003"),
    limits=(("chunk_rows", 4096), ("pending_tasks", 8)),
    execution_memory="Bellek dışı iter_batches; sınırlı yerel task dalgası; tensor/model lazy fit yok",
    dependencies=("dask",),
    supports=(("streaming", True), ("cancel", True), ("source_write", False)),
    evidence_refs=("docs/evidence/PHASE66.md",),
)

CAPABILITIES["dataset.profile"] = _replace_distribution(
    CAPABILITIES["dataset.profile"],
    execution_memory="4096 satırlık collect_batches; Decimal80/SQLite frekans spill; quantile disk sorgusu; RAM/disk quota geçerli",
)

for _task in ("batch", "route", "cli", "api"):
    _id = "model.monitor." + _task
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU if _task in ("batch", "cli", "api") else ExecutionKind.IO,
        "explicit local batch monitoring " + _task,
        kind="monitoring",
        input_schema="MonitoringSpec/v1; immutable DatasetVersion/ColumnId; frozen safe model",
        output_type="MonitoringRun/v1" if _task != "route" else "ExperimentEvent/v1",
        supports=(
            ("cancel", True),
            ("source_write", False),
            ("safe_serialization", True),
        ),
        limits=(
            ("source_rows", 10000),
            ("source_columns", 64),
            ("features", 32),
            ("report_bytes", 16777216),
        ),
        execution_memory="bounded in-memory snapshots; no out-of-core model fit",
        help_links=("model-monitoring",),
        requirement_ids=tuple("F67-S00" + str(i) for i in range(1, 5)),
        evidence_refs=("docs/evidence/PHASE67.md",),
        assumptions=(
            "drift is not evidence of deterioration; labels may be delayed/selected",
            "loopback API separately opt-in/auth; no implicit network/deploy",
        ),
    )

for _task in (
    "monte-carlo",
    "linear",
    "mixed-integer",
    "nonlinear",
    "what-if",
    "model-optimize",
):
    _id = "scenario." + _task
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "bounded declarative scenario " + _task,
        kind="analysis",
        backend="numpy PCG64 / scipy HiGHS SLSQP / Pint",
        input_schema="ScenarioSpec/v1: units, explicit assumptions; immutable frozen model optional",
        output_type="ScenarioRun/v1",
        dependencies=("numpy", "scipy", "pint"),
        supports=(
            ("cancel", True),
            ("source_write", False),
            ("safe_serialization", True),
        ),
        limits=(
            ("variables", 16),
            ("draws", 100000),
            ("constraints", 64),
            ("model_source_rows", 10000),
            ("report_bytes", 2097152),
        ),
        execution_memory="bounded dense CPU draws; no sparse coercion/out-of-core/GPU/distributed solver",
        deterministic_policy="PCG64 seed/chunk recorded; solver numerical/platform tolerance; no cross-platform bitwise guarantee",
        assumptions=(
            "explicit independence or joint-normal PSD correlation",
            "local nonlinear result is not global optimum; model prediction is not causal",
            "feasibility only within declared constraints and units",
        ),
        help_links=("scenario-simulation",),
        requirement_ids=tuple("F68-S00" + str(i) for i in range(1, 5)),
        operations=tuple(
            _LateSupport(
                n,
                "supported" if n == "persist" else "unsupported",
                "safe declarative result only; no model fitting",
            )
            for n in ("fit", "predict", "proba", "transform", "interval", "persist")
        ),
        evidence_refs=("docs/evidence/PHASE68.md",),
    )

for _task in (
    "mean-median",
    "cleaning",
    "histogram",
    "sampling",
    "ci",
    "overfitting",
    "leakage",
    "calibration",
    "time-series",
    "confounding",
):
    _id = "learn.lab." + _task
    CAPABILITIES[_id] = Capability(
        _id,
        ExecutionKind.CPU,
        "separate synthetic teaching workspace " + _task,
        kind="learning",
        backend="numpy/scipy/sklearn CPU",
        input_schema="LabSpec/v1: closed lesson/seed/bounded slider; synthetic fixture only",
        output_type="LearningLabRun/v1",
        dependencies=("numpy", "scipy", "sklearn"),
        supports=(
            ("cancel", True),
            ("source_write", False),
            ("safe_serialization", True),
        ),
        limits=(
            ("input_rows", 10000),
            ("curve_points", 600),
            ("report_bytes", 2097152),
        ),
        execution_memory="bounded in-memory synthetic fixture; shared process/thread/RAM/time budget",
        deterministic_policy="explicit seed and sklearn/scipy version; exploratory teaching evaluation reused by slider",
        assumptions=(
            "synthetic examples only, no production validation/certification",
            "prerequisites/self-check optional; tools do not require reading",
        ),
        help_links=("learning-laboratory",),
        requirement_ids=tuple("F69-S00" + str(i) for i in range(1, 6)),
        evidence_refs=("docs/evidence/PHASE69.md",),
    )

CAPABILITIES["report.builder"] = Capability(
    "report.builder",
    ExecutionKind.CPU,
    "pinned_report_builder_v1",
    kind="export",
    backend="pyarrow/stdlib/Qt-local",
    deterministic_policy="Pinned recorded values; no inference; review hash and exclusive publication; PDF layout platform-bounded",
    execution_memory="Bounded table batches100rows;64MiB snapshot/16MiB artifact/32MiB report; no model fit, no GPU",
    supports=(
        ("null", True),
        ("decimal", True),
        ("cancel", True),
        ("safe_serialization", True),
    ),
    input_schema="Recorded dataset/result/artifact references; explicit text and masks",
    parameter_schema="ReportSpec/v1 closed blocks1..32, selected columns1..16, table preview1..100",
    output_type="ScientificReport/v1",
    artifact_kinds=("text",),
    help_links=("scientific-report",),
    assumptions=(
        "No analysis recompute; recorded metrics only; manual narrative is not evidence",
        "Offline bounded export; explicit redaction preview; DOCX/LLM unsupported",
    ),
    limits=(("report_bytes", 33554432), ("blocks", 32), ("table_rows", 100)),
    evidence_refs=("docs/evidence/PHASE70.md",),
    requirement_ids=("F70-S001", "F70-S002", "F70-S003", "F70-S004"),
)

for _share in ("bundle", "diff", "review", "restore"):
    CAPABILITIES["share." + _share] = Capability(
        "share." + _share,
        ExecutionKind.CPU,
        "local_review_share_v1_" + _share,
        kind="export",
        backend="stdlib/pyarrow/local ProjectStore",
        input_schema="Pinned project/ReviewShare/v1",
        parameter_schema="Explicit local action/inclusion/review; no server or shared edits",
        output_type="ReviewShare/v1",
        supports=(("cancel", True), ("safe_serialization", True)),
        limits=(("bundle_bytes", 67108864), ("members", 128), ("sample_rows", 1000)),
        deterministic_policy="Pinned commit, hashes and stable IDs; human review declaration, no automatic merge",
        execution_memory="bounded scan/batch; unknown binary full-copy unavailable; no GPU/remote",
        assumptions=(
            "Pattern scan is not complete PII detection; explicit inclusion preview",
            "Single local writer; no network SQLite collaboration; restore only new fork",
        ),
        help_links=("review-sharing",),
        requirement_ids=("F71-S001", "F71-S002", "F71-S003", "F71-S004", "F71-S005"),
        evidence_refs=("docs/evidence/PHASE71.md",),
    )

for _privacy in ("scan", "review", "export", "retention"):
    CAPABILITIES["privacy." + _privacy] = Capability(
        "privacy." + _privacy,
        ExecutionKind.CPU,
        "local_privacy_v1_" + _privacy,
        kind="export",
        backend="pyarrow/stdlib HMAC; optional pyca Fernet/Secret Service",
        input_schema="Pinned DatasetVersion/ColumnId; human review",
        parameter_schema="Closed privacy action; explicit confirmation; no automatic cleanup",
        output_type="PrivacyEvent/v1 or PrivacyExport/v1",
        supports=(("cancel", True), ("safe_serialization", True)),
        limits=(("rows", 10000), ("bytes", 33554432), ("columns", 16)),
        deterministic_policy="Source/policy/preview hashes; keyed project/ColumnId pseudonyms; no anonymity guarantee",
        execution_memory="Bounded snapshot/export; Fernet memory-only small bundle; no remote/GPU",
        assumptions=(
            "Pattern candidates require human review; incomplete PII detection",
            "Live project encryption and differential privacy unavailable; local history is not immutable audit",
        ),
        help_links=("privacy-governance",),
        requirement_ids=("F72-S001", "F72-S002", "F72-S003", "F72-S004"),
        evidence_refs=("docs/evidence/PHASE72.md",),
    )

CAPABILITIES["plugin.sdk"] = Capability(
    "plugin.sdk",
    ExecutionKind.CPU,
    "explicit_plugin_api_v1",
    kind="analysis",
    backend="trusted local Python3.13; data-only manifest/result",
    input_schema="PluginInput/v1",
    parameter_schema="Manifest scalar parameters; explicit hash/trust/network consent",
    output_type="PluginRun/v1",
    supports=(("cancel", True), ("safe_serialization", True)),
    assumptions=(
        "Same-user Python is not an OS sandbox; permissions are disclosures",
        "Opening projects never imports plugin code; missing plugin only disables recompute",
    ),
    limits=(("rows", 10000), ("output_bytes", 1048576)),
    help_links=("plugins-sdk",),
    requirement_ids=("F73-S001", "F73-S002", "F73-S003", "F73-S004"),
    evidence_refs=("docs/evidence/PHASE73.md",),
)

for _environment in ("inspect", "profile", "update-plan"):
    CAPABILITIES["environment." + _environment] = Capability(
        "environment." + _environment,
        ExecutionKind.IO,
        "explicit_environment_v1",
        kind="export",
        backend="stdlib metadata; pinned package profile; external host Flatpak update only",
        input_schema="EnvironmentLock/v1 and selected local files",
        parameter_schema="explicit local action/approval; no automatic install",
        output_type="EnvironmentReport/v1 or UpdatePlan/v1",
        supports=(("cancel", True), ("safe_serialization", True)),
        assumptions=(
            "Metadata match is not backend/GPU runtime validation",
            "Profile import compares only; managed isolated workers/offline installer/local extra installer unavailable",
        ),
        limits=(("report_bytes", 2097152), ("cache_bytes", 67108864)),
        help_links=("environment-distribution",),
        requirement_ids=(
            "F74-S001",
            "F74-S002",
            "F74-S003",
            "F74-S004",
            "F74-S005",
            "F74-S006",
        ),
        evidence_refs=("docs/evidence/PHASE74.md",),
    )

# Late-added entries must also expose the common contract. Unknown is deliberate:
# metadata completion is not evidence of a backend operation being supported.

for _id, _cap in tuple(CAPABILITIES.items()):
    if all(
        (
            _cap.inputs,
            _cap.parameters,
            _cap.assumptions,
            _cap.support_details,
            _cap.operations,
            _cap.learning,
            _cap.artifact_kinds,
        )
    ):
        continue
    CAPABILITIES[_id] = _replace_distribution(
        _cap,
        inputs=_cap.inputs or _LateInput(_cap.input_schema),
        parameters=_cap.parameters or (_LateParameter("spec", _cap.parameter_schema),),
        assumptions=_cap.assumptions
        or (
            "Yöntemin kayıtlı sınırları geçerlidir; beyan edilmemiş backend işlemi doğrulanmış sayılmaz.",
        ),
        support_details=_cap.support_details
        or tuple(
            _LateSupport(n)
            for n in (
                "missing",
                "null",
                "nan",
                "inf",
                "weights",
                "group",
                "time",
                "sparse",
            )
        ),
        operations=_cap.operations
        or tuple(
            _LateSupport(n)
            for n in ("fit", "predict", "proba", "transform", "interval", "persist")
        ),
        learning=_cap.learning or tuple(_LateLearning(h) for h in _cap.help_links),
        artifact_kinds=_cap.artifact_kinds or ("text",),
    )
