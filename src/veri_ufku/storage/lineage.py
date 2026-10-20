"""Read-only projection of recorded lineage; never infer historical provenance."""

import copy

from veri_ufku.storage.project_model import ProjectError

UNKNOWN = "not_recorded"


def graph(state, manifest, focus=""):
    nodes, edges = {}, []
    artifacts = manifest["artifacts"]

    def add(ident, kind, metadata):
        nodes[ident] = dict(id=ident, kind=kind, metadata=copy.deepcopy(metadata))

    def edge(source, target, relation):
        if source in nodes and target in nodes:
            item = dict(source=source, target=target, relation=relation)
            if item not in edges:
                edges.append(item)

    def artifact(uri):
        return (
            dict(
                uri=uri, fingerprint={k: artifacts[uri][k] for k in ("size", "sha256")}
            )
            if uri in artifacts
            else dict(uri=uri, fingerprint=UNKNOWN)
        )

    for s in state["sources"]:
        add(
            s["id"],
            "source",
            dict(
                version=s.get("fingerprint"),
                snapshot=artifact(s.get("copy_uri")),
                source_location=s.get("path"),
                source_adapter=(
                    s.get("connector", {}).get("spec", {}).get("adapter_id")
                    or s.get("format", UNKNOWN)
                ),
                provenance=s.get("provenance", UNKNOWN),
            ),
        )
    for d in state["datasets"]:
        add(
            d["version_id"],
            "dataset",
            dict(
                dataset_id=d["dataset_id"],
                version=d["version_id"],
                snapshot=artifact(d["snapshot_uri"]),
                schema=d.get("import_metadata", {}).get("columns", UNKNOWN),
                schema_contract=d.get("schema_contract", UNKNOWN),
                semantic_metadata=d.get("semantic_metadata", {}),
                rows=d.get("import_metadata", {}).get("row_count"),
                row_lineage=artifact(d.get("lineage_uri"))
                if d.get("lineage_uri")
                else dict(
                    status="preserved_identity_or_not_recorded; inspect operation policy"
                ),
                source_snapshot_id=d.get("import_metadata", {}).get(
                    "source_snapshot_id", UNKNOWN
                ),
            ),
        )
        edge(d["source_id"], d["version_id"], "import_or_source_reference")
    for o in state["operations"]:
        add(
            o["id"],
            "operation",
            dict(
                spec=o.get("spec", UNKNOWN),
                status=o.get("status", UNKNOWN),
                provenance=o.get("provenance", UNKNOWN),
                lineage=o.get("lineage", UNKNOWN),
                user_decisions=o.get("spec", {}).get("parameters", UNKNOWN),
                method_version=o.get("spec", {}).get("method_version", UNKNOWN),
            ),
        )
        output = o.get("output_version_id")
        for version in o.get("dataset_version_ids", []):
            if version != output:
                edge(version, o["id"], "input")
        if output:
            edge(o["id"], output, "produces")
    for d in state["datasets"]:
        if not d.get("operation_id") or d["operation_id"] not in nodes:
            for parent in sorted(
                set(d.get("parent_version_ids", []) + d.get("input_version_ids", []))
            ):
                edge(
                    parent,
                    d["version_id"],
                    "recorded_parent; operation details may be missing",
                )
    for r in state["results"]:
        kind = next(
            (
                k
                for k in (
                    "scientific_report",
                    "review_event",
                    "privacy_event",
                    "plugin_result",
                    "export",
                    "neural",
                    "baseline",
                    "analysis",
                    "profile",
                    "chart",
                    "quality",
                    "search",
                    "unsupervised",
                    "time_series",
                    "text",
                    "text_analysis",
                    "monitoring",
                    "scenario",
                    "learning_lab",
                    "explanation",
                    "model_choice",
                    "test_use",
                    "experiment_event",
                )
                if k in r
            ),
            None,
        )
        run = r.get(kind, {}) if kind else {}
        typ = (
            "report"
            if kind in ("export", "scientific_report")
            else "model"
            if kind in ("baseline", "search", "model_choice")
            or run.get("model_package_uri")
            else "analysis"
        )
        if kind == "neural" and run.get("schema") == "WorkflowRun/v1":
            typ = "workflow"
        add(
            r["id"],
            typ,
            dict(
                record_kind=kind or UNKNOWN,
                run_id=run.get("run_id", UNKNOWN),
                schema=run.get("schema", UNKNOWN),
                params={
                    k: run[k]
                    for k in (
                        "spec",
                        "workflow_spec",
                        "code_recipe",
                        "params",
                        "parameters",
                        "plan",
                    )
                    if k in run
                },
                provenance=run.get("provenance", UNKNOWN),
                capture=run.get("experiment_capture", UNKNOWN),
                recorded_environment=run.get("environment", UNKNOWN),
                hardware=run.get("experiment_capture", {}).get("hardware", UNKNOWN),
                model_artifact=artifact(run["model_package_uri"])
                if run.get("model_package_uri")
                else UNKNOWN,
                details_artifact=artifact(run["details_uri"])
                if run.get("details_uri")
                else UNKNOWN,
                status=run.get("status", UNKNOWN),
                privacy_decision=run.get("payload", UNKNOWN)
                if kind == "privacy_event"
                else UNKNOWN,
                review_subject=run.get("subject", UNKNOWN),
                review_import_origin=run.get("origin", UNKNOWN),
                report_reference={
                    k: run[k]
                    for k in (
                        "format",
                        "published",
                        "dataset_version",
                        "lineage_record_ids",
                        "lineage_context_version",
                        "file_refs",
                        "record_refs",
                        "stale",
                    )
                    if k in run
                },
                legacy_gaps="Only recorded fields. Package/hardware/code/user decision may be not_recorded.",
            ),
        )
        for v in r.get("dataset_version_ids", []):
            edge(v, r["id"], "recorded_dataset_input")
        if (
            kind == "review_event"
            and run.get("subject", {}).get("origin", {}).get("project_id")
            == manifest["project_id"]
        ):
            edge(
                run["subject"]["entity"]["id"], r["id"], "human_review_original_context"
            )
        if kind == "scientific_report":
            for record_id in run.get("record_refs", {}):
                edge(record_id, r["id"], "report_pinned_result")
        if kind == "scenario":
            for model_id in run.get("model_refs", {}):
                edge(model_id, r["id"], "scenario_frozen_model")
        if kind == "monitoring":
            for model_id in run.get("model_refs", {}):
                edge(model_id, r["id"], "monitoring_frozen_model")
        if kind == "experiment_event" and run.get("kind") == "model_route":
            edge(run["value"]["record_id"], r["id"], "local_champion_reference")
            if run["value"].get("previous_record_id"):
                edge(run["value"]["previous_record_id"], r["id"], "rollback_reference")
        if run.get("schema") == "WorkflowRun/v1":
            # Compact journal nodes contain the actual specs and dependency graph.
            for n in run["nodes"]:
                ident = r["id"] + "/" + n["case"] + "/" + n["node"]
                add(
                    ident,
                    "model"
                    if n["kind"] == "train"
                    else "report"
                    if n["kind"] == "export"
                    else "operation"
                    if n["kind"] == "transform"
                    else "analysis",
                    dict(
                        workflow_kind=n["kind"],
                        status=n["status"],
                        operation_spec=n["operation_spec"],
                        cache_key=n["cache_key"],
                        verified_at=n["verified_at"],
                        row_lineage="run-scoped native artifact; open workflow details for membership; no universal row reconstruction",
                    ),
                )
                edge(ident, r["id"], "member_of_run")
            for n in run["nodes"]:
                target = r["id"] + "/" + n["case"] + "/" + n["node"]
                spec = next(
                    v for v in run["workflow_spec"]["nodes"] if v["id"] == n["node"]
                )
                for parent in sorted(
                    {v["node"] for v in spec["inputs"].values()} | set(spec["after"])
                ):
                    edge(
                        r["id"] + "/" + n["case"] + "/" + parent,
                        target,
                        "typed_dependency",
                    )
                if n["kind"] == "source":
                    for v in n.get("root_versions", []):
                        edge(v, target, "source_snapshot")
    for r in state["results"]:
        info = r.get("export", {})
        for ident in info.get("lineage_record_ids", []):
            edge(ident, r["id"], "included_in_report")
    if focus:
        if focus not in nodes:
            raise ProjectError("Lineage focus kimliği bulunamadı.")
        selected = {focus}
        while True:
            old = len(selected)
            selected |= {e["source"] for e in edges if e["target"] in selected}
            if len(selected) == old:
                break
        nodes = {k: v for k, v in nodes.items() if k in selected}
        edges = [e for e in edges if e["source"] in nodes and e["target"] in nodes]
    if len(nodes) > 2000 or len(edges) > 10000:
        raise ProjectError("Lineage2000node/10000edge bütçesi; daha dar focus seçin.")
    return dict(
        schema="LineageGraph/v1",
        focus=focus,
        nodes=list(nodes.values()),
        edges=edges,
        limits=[
            "Dataset-level links use only recorded identities.",
            "RowId is not global across all datasets. Multi-source row edges only when a lineage Parquet was recorded; no reverse relation is fabricated.",
            "Old reports without record IDs trace to dataset only; analyses/models not guessed.",
            "Current machine information is not historical run hardware.",
        ],
    )
