"""Bind Phase26 review areas and all publication checkpoints to real JUnit results."""

import argparse
import ast
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

AREAS = {
    "parser": [
        "test_structured_import",
        "test_phase11_formats",
        "test_delimited",
        "test_security_audit.test_parser_actual_limits",
        "test_security_audit.test_ods",
    ],
    "manifest_paths": [
        "test_projects.test_future_version",
        "test_projects.test_corrupt_active",
        "test_projects.test_samefile_symlink",
        "test_security_audit.test_project_metadata_hardlink",
    ],
    "formula_ast": [
        "test_relational.test_formula_text_date_and_security",
        "test_security_audit.test_untrusted_formula_ast",
    ],
    "sql_identifiers": [
        "test_security_audit.test_hostile_sql_identifier",
        "test_phase11_formats.test_real_formats",
    ],
    "html_spreadsheet": [
        "test_exports.test_local_html_escape",
        "test_exports.test_safety_loss",
        "test_exports.test_null_collision",
        "test_statistics.test_saved_analysis_report",
    ],
    "safe_models": [
        "test_lifecycle.test_unsafe_pickle",
        "test_lifecycle.test_hostile_archive",
        "test_lifecycle.test_incompatible_packages",
    ],
    "private_logs": [
        "test_jobs.test_failure_redacts",
        "test_security_audit.test_log_link",
    ],
    "temporary_lifecycle": [
        "test_jobs.test_cancel_removes",
        "test_performance.test_cancel_during_import_publication",
        "test_delimited.test_cancel_parse",
    ],
    "recovery": [
        "test_projects.test_old_autosave",
        "test_security_audit.test_recovery_preview",
        "test_security_gui.test_recovery_dialog",
        "test_projects.test_metadata_open_never_reads",
    ],
    "migration": [
        "test_projects.test_legacy_fixture",
        "test_delimited.test_schema1",
        "test_structured_import.test_schema2",
        "test_structured_import.test_schema3",
        "test_security_audit.test_old_schema",
    ],
    "atomicity_and_two_processes": [
        "test_projects.test_sigkill",
        "test_projects.test_two_real_processes",
        "test_security_audit.test_autosave_sigkill",
        "test_security_audit.test_disk_full",
        "test_lifecycle.test_two_process",
        "test_recipes.test_real_sigkill",
    ],
    "golden_statistics": [
        "test_statistics.test_two_groups_closed",
        "test_statistics.test_key_pairing",
        "test_statistics.test_three_groups_closed",
        "test_statistics.test_categorical_exact",
        "test_statistics.test_numeric_closed",
        "test_statistics.test_multiple_adjustments",
    ],
    "golden_transform_join": [
        "test_relational.test_join_exact",
        "test_relational.test_aggregate_pivot",
        "test_cleaning",
        "test_relational_backends",
    ],
    "golden_metrics_leakage": [
        "test_classification.test_binary_hand",
        "test_classification.test_multiclass_hand",
        "test_validation.test_test_feature_poison",
        "test_validation.test_actual_baselines_group_time",
        "test_validation.test_dummy_classification_independent",
        "test_regression.test_true_predictions_cv",
        "test_lifecycle.test_classification_roundtrip",
        "test_lifecycle.test_regression_roundtrip",
        "test_preparation",
    ],
    "row_identity_stale_sources": [
        "test_lifecycle.test_rowid_filter",
        "test_delimited.test_utf8_expected",
        "test_delimited.test_source_modified",
        "test_delimited.test_capture_tampered",
        "test_operations_gui.test_qml_apply",
        "test_quality_gui.test_quality_cancel",
        "test_regression_gui",
        "test_classification_gui",
    ],
}


def build(root, junit):
    root = Path(root)
    cases = []
    for case in ElementTree.parse(junit).findall(".//testcase"):
        ident = case.get("classname") + "." + case.get("name")
        status = (
            "passed"
            if not any(
                case.find(n) is not None for n in ("failure", "error", "skipped")
            )
            else "not-passed"
        )
        cases.append(dict(id=ident, status=status, seconds=case.get("time")))
    areas = []
    for area, prefixes in AREAS.items():
        selected = []
        for prefix in prefixes:
            matches = [
                c for c in cases if c["id"].removeprefix("tests.").startswith(prefix)
            ]
            if not matches or any(c["status"] != "passed" for c in matches):
                raise ValueError(f"Missing/unpassed acceptance: {prefix}")
            selected.extend(matches)
        areas.append(
            dict(area=area, cases=list({c["id"]: c for c in selected}.values()))
        )
    path = root / "src/veri_ufku/storage/project_store.py"
    tree = ast.parse(path.read_text())
    points = sorted(
        {
            node.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == "checkpoint")
                or (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "checkpoint"
                )
            )
        }
    )
    checkpoints = []
    for point in points:
        if point in ("source_chunk_written", "parquet_chunk_written"):
            suffix = "source" if point.startswith("source") else "parquet"
            matches = [
                c
                for c in cases
                if c["id"]
                .removeprefix("tests.")
                .startswith("test_projects.test_sigkill_during_actual_artifact_writing")
                and "[" + suffix + "]" in c["id"]
            ]
        else:
            matches = [
                c
                for c in cases
                if point in c["id"]
                and ("sigkill" in c["id"] or "real_sigkill" in c["id"])
            ]
        if not matches or any(c["status"] != "passed" for c in matches):
            raise ValueError(f"Untested real kill boundary: {point}")
        checkpoints.append(dict(point=point, cases=matches))
    return dict(
        date=datetime.now(UTC).isoformat(),
        environment="ENV-26",
        junit_sha256=hashlib.sha256(Path(junit).read_bytes()).hexdigest(),
        areas=areas,
        publication_checkpoints=checkpoints,
        tests=len(cases),
        passed=sum(c["status"] == "passed" for c in cases),
        scope="Source audit bound to real parameterized JUnit test cases. Independent golden reference derivations reviewed in docs/GOLDEN_REFERENCES.md. Not a proof against arbitrary same-user concurrent mutation, power loss, or all library vulnerabilities.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(Path(__file__).resolve().parents[1], args.junit)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        "RELIABILITY AUDIT PASS",
        result["passed"],
        "tests",
        len(result["publication_checkpoints"]),
        "real kill checkpoints",
    )
