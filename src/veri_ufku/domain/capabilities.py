"""Shared capability registry; CSV/TSV import is implemented in Phase 05."""

from veri_ufku.domain.contracts import Capability, ExecutionKind

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
