"""One full-data calculation for preview and publication, with bounded table samples."""

import copy
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import checked, filtered, page
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.operations.cleaning_contracts import KINDS
from veri_ufku.operations.contracts import (
    LINEAGE,
    RowLineageSpec,
    filter_view,
    validate,
)
from veri_ufku.operations.relational_contracts import KINDS as RELATIONAL
from veri_ufku.operations.relational_contracts import NEW_ROWS
from veri_ufku.storage.project_model import ProjectError, decode, digest, encode, uid


def calculate(request, specification, workspace, control=None):
    control = control or Control()
    checked(request, control)
    spec = validate(specification, request)
    diagnostics = {}
    relation = None
    prepared_output = None
    if spec.kind in RELATIONAL:
        from veri_ufku.operations.relational import execute

        if request.get("secondary"):
            checked(request["secondary"], control)
        spec, prepared_output, diagnostics, relation = execute(
            request, spec, workspace, control
        )
    elif spec.kind in KINDS:
        from veri_ufku.operations.cleaning import execute

        spec, prepared_output, diagnostics, relation = execute(
            request, spec, workspace, control
        )
    query = pl.scan_parquet(request["path"])
    if spec.kind == "rename":
        old = next(
            c["name"] for c in request["columns"] if c["id"] == spec.column_ids[0]
        )
        query = query.rename({old: spec.parameters["name"]})
    elif spec.kind == "drop":
        query = query.drop(
            [c["name"] for c in request["columns"] if c["id"] in spec.column_ids]
        )
    elif spec.kind == "filter":
        query, _, _ = filtered(request, filter_view(spec))
    output = prepared_output or Path(workspace) / (uid() + ".parquet")
    try:
        control.progress("Tam veri üzerinde işlem önizlemesi", 0, None)
        control.disk(workspace)
        if not prepared_output:
            query.sink_parquet(output, maintain_order=True, engine="streaming")
        control.disk(workspace)
        fp = hash_artifact(output, control)
        schema = {k: str(v) for k, v in pl.read_parquet_schema(output).items()}
        # Disk scan validates count and surviving identity uniqueness before acceptance.
        stats = (
            pl.scan_parquet(output)
            .select(pl.len().alias("n"), pl.col("__vu_row_id").n_unique().alias("ids"))
            .collect(engine="streaming")
            .row(0)
        )
        count, unique = stats
        if count != unique or (
            spec.kind not in NEW_ROWS and count > request["row_count"]
        ):
            raise ProjectError("İşlem çıktı satır kimlikleri/sayımı doğrulanamadı.")
        version = "dv:" + uid()
        after_request = dict(
            request,
            path=str(output),
            fingerprint=fp,
            columns=list(spec.output_schema),
            row_count=count,
            version_id=version,
        )
        before = page(request, ViewSpec(), control=control)
        after = page(after_request, ViewSpec(), control=control)
        checked(request, control)
        if request.get("secondary"):
            checked(request["secondary"], control)
        removed = (
            request["row_count"]
            if spec.kind in NEW_ROWS
            else max(0, request["row_count"] - count)
        )
        impact = dict(
            scope="full",
            population_n=request["row_count"],
            used_n=request["row_count"],
            before_rows=request["row_count"],
            after_rows=count,
            removed_rows=removed,
            changed_rows=removed + diagnostics.get("modified_rows", 0),
            added_rows=count if spec.kind in NEW_ROWS else 0,
            before_columns=len(request["columns"]),
            after_columns=len(spec.output_schema),
            changed_columns=len(spec.column_ids)
            if spec.kind in ("rename", "drop", "roles")
            else diagnostics.get("changed_columns", 0),
            removed_columns=len(request["columns"]) - len(spec.output_schema)
            if len(request["columns"]) > len(spec.output_schema)
            else 0,
            added_columns=max(0, len(spec.output_schema) - len(request["columns"])),
            changed_cells=diagnostics.get("changed_cells", 0),
            new_nulls=diagnostics.get("new_nulls", 0),
            parse_errors=diagnostics.get("parse_errors", 0),
            outlier_candidates=diagnostics.get("outlier_candidates", 0),
            input_populations=[
                dict(version_id=r["version_id"], rows=r["row_count"], side=side)
                for side, r in [("primary", request)]
                + (
                    [("secondary", request["secondary"])]
                    if request.get("secondary")
                    else []
                )
            ],
            total_input_occurrences=request["row_count"]
            + (request["secondary"]["row_count"] if request.get("secondary") else 0),
            table_scope="first200_display_only",
        )
        row_contract = (
            asdict(
                RowLineageSpec(
                    "filter",
                    (request["version_id"],),
                    "preserve",
                    "output_rowid_projection",
                ).validate()
            )
            if spec.kind == "filter"
            else asdict(
                RowLineageSpec(
                    "dedup",
                    (request["version_id"],),
                    "retain_stable_survivor",
                    "parquet_duplicate_groups",
                ).validate()
            )
            if spec.kind == "dedup"
            else None
        )
        if spec.kind in NEW_ROWS:
            row_contract = dict(
                kind=spec.kind,
                input_version_ids=list(spec.input_version_ids),
                row_id_policy="new_persistent_uuid_per_output_occurrence",
                provenance_representation="parquet_immutable_membership_edges",
                schema_version=1,
            )
        provenance = Provenance(
            provenance_id="prov:" + uid(),
            dataset_versions=tuple(spec.input_version_ids or (request["version_id"],))
            + (version,),
            config_revision=request.get("config_revision", 0),
            capability_id="operation." + spec.kind.replace("_", "-"),
            parameters_hash=digest(encode(spec.data())),
            environment=(("polars", pl.__version__),),
            created_at=datetime.now(UTC).isoformat(),
            scope="full",
            seed=None,
            seed_reason="Deterministik işlem; örneklem hesabı yok",
            source_snapshot_ids=tuple(
                dict.fromkeys(
                    [request["source_snapshot_id"]]
                    + (
                        [request["secondary"]["source_snapshot_id"]]
                        if request.get("secondary")
                        else []
                    )
                )
            ),
            row_lineage_ref=("membership:" + spec.id)
            if relation
            else "identity_projection:" + request["version_id"],
            column_lineage_ref=spec.id,
            learning_content_version="10",
        )
        return dict(
            spec=spec.data(),
            diagnostics=diagnostics,
            lineage_path=str(relation) if relation else None,
            lineage_fingerprint=hash_artifact(relation, control) if relation else None,
            path=str(output),
            fingerprint=fp,
            output_schema=schema,
            version_id=version,
            applicability={
                "applicable": True,
                "reason": "Giriş sürümü, ColumnId ve tipli parametreler doğrulandı.",
            },
            validation={
                "valid": True,
                "identity_unique": True,
                "snapshot_verified": True,
            },
            status="previewed",
            impact=impact,
            before=before,
            after=after,
            lineage=dict(
                row_contract=decode(encode(row_contract)),
                policy=LINEAGE.get(spec.kind, "preserve identities"),
                input_version=request["version_id"],
                membership="immutable input/output edge Parquet"
                if relation
                else "output RowId projection",
                input_versions=list(spec.input_version_ids or (request["version_id"],)),
            ),
            provenance=decode(encode(asdict(provenance))),
        )
    except BaseException:
        output.unlink(missing_ok=True)
        raise


def transformed_dataset(parent, result, uri, secondary=None):
    spec = validate(
        result["spec"],
        {
            "columns": parent["import_metadata"]["columns"],
            "settings": parent["import_metadata"]["settings"],
            "version_id": parent["version_id"],
            **(
                {
                    "secondary": {
                        "version_id": secondary["version_id"],
                        "columns": secondary["import_metadata"]["columns"],
                        "settings": secondary["import_metadata"]["settings"],
                    }
                }
                if secondary
                else {}
            ),
        },
    )
    dataset = copy.deepcopy(parent)
    dataset.pop("forked_from_version_id", None)
    dataset.pop("input_version_ids", None)
    dataset.update(
        version_id=result["version_id"],
        parent_version_ids=[parent["version_id"]],
        snapshot_uri=uri,
        operation_id=spec.id,
        output_schema=result["output_schema"],
    )
    if spec.input_version_ids:
        dataset["input_version_ids"] = list(spec.input_version_ids)
    dataset["import_metadata"]["columns"] = copy.deepcopy(list(spec.output_schema))
    dataset["import_metadata"]["row_count"] = result["impact"]["after_rows"]
    if "semantic_metadata" in dataset:
        ids = {c["id"] for c in spec.output_schema}
        dataset["semantic_metadata"] = {
            k: v for k, v in dataset["semantic_metadata"].items() if k in ids
        }
    if spec.kind == "convert":
        for column_id in spec.column_ids:
            dataset.get("semantic_metadata", {}).pop(column_id, None)
    if spec.kind == "roles":
        dataset.update(copy.deepcopy(spec.parameters))
    return dataset
