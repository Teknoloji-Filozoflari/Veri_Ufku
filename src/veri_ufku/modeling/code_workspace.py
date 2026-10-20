"""Hash-only code-cell provenance. Code and output are deliberately never persisted."""

import hashlib
import json
import platform
import re
from dataclasses import asdict
from datetime import UTC, datetime

from veri_ufku.domain.contracts import Provenance
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError

SCHEMA = "CodeRun/v1"
STATUSES = (
    "draft",
    "running",
    "completed",
    "failed",
    "canceled",
    "timeout",
    "budget_exhausted",
    "output_limit",
)


def cell_hash(source):
    if not isinstance(source, str) or len(source.encode()) > 16384 or "\x00" in source:
        raise ProjectError("Code cell UTF8<=16KiB; NUL yok.")
    return hashlib.sha256(source.encode()).hexdigest()


def kernel_environment():
    return dict(
        python=platform.python_version(),
        implementation=platform.python_implementation(),
        machine=platform.machine(),
        isolation="fresh process; no OS sandbox; same user filesystem/network rights",
        state="no persistent notebook/kernel globals",
        jupyter="external optional; managed kernel unavailable",
    )


def record(request, code_hash, revision, timeout, action="execute", previous_hash=None):
    now = datetime.now(UTC).isoformat()
    env = kernel_environment()
    recipe = dict(
        action=action,
        cell_hash=code_hash,
        previous_cell_hash=previous_hash,
        revision=revision,
        timeout_seconds=timeout,
        environment_hash=digest(env),
    )
    compat = digest(dict(dataset=request["version_id"], recipe=recipe))
    scope = "user initiated arbitrary Python; hash-only provenance, no persisted source/output; no evaluation score"
    result = dict(
        schema=SCHEMA,
        run_id=request["run_id"],
        training_id=request["run_id"],
        dataset_version=request["version_id"],
        origin_version=request["version_id"],
        source_snapshot_id=request["source_snapshot_id"],
        snapshot_fingerprint=request["fingerprint"],
        seed=0,
        spec={},
        code_recipe=recipe,
        epoch=0,
        curves=[],
        elapsed_seconds=0,
        created_at=now,
        data_access_at=now,
        prior_test_use_ids=request.get("prior_test_use_ids", []),
        plan=dict(
            split_id="code:" + compat,
            scope=scope,
            membership=dict(train=[], validation=[], test=[]),
        ),
        tensor_schema={},
        model_weights=None,
        runtime=None,
        compat_id=compat,
        metrics={},
        mode="code_workspace",
        environment=env,
        experiment_capture=request.get("experiment_capture", {}),
        warnings=[
            "Separate process is not a security boundary. No validated OS sandbox; arbitrary code retains same-user filesystem/network access.",
            "Only cell/config hash, environment, status and byte counts are persisted. Source/output are volatile and not exported. Restart loses interactive state.",
            "No Python-to-GUI reverse conversion. Edited code is not guaranteed equivalent to generated recipe. No statistical/final-test result claimed.",
        ],
        status="draft" if action == "save_hash" else "running",
        output_bytes=0,
        exit_code=None,
        kernel_pid=None,
    )
    result["provenance"] = asdict(
        Provenance(
            provenance_id="provenance:" + compat,
            dataset_versions=(request["version_id"],),
            config_revision=revision,
            capability_id="code.workspace",
            parameters_hash=digest(recipe),
            environment=(("python", env["python"]),),
            created_at=now,
            scope=scope,
            source_snapshot_ids=(request["source_snapshot_id"],),
            row_lineage_ref="none: arbitrary code does not claim row-level results",
        )
    )
    validate(result)
    return result


def validate(data):
    allowed = {
        "schema",
        "run_id",
        "training_id",
        "dataset_version",
        "origin_version",
        "source_snapshot_id",
        "snapshot_fingerprint",
        "seed",
        "spec",
        "code_recipe",
        "epoch",
        "curves",
        "elapsed_seconds",
        "created_at",
        "data_access_at",
        "prior_test_use_ids",
        "plan",
        "tensor_schema",
        "model_weights",
        "runtime",
        "compat_id",
        "metrics",
        "mode",
        "environment",
        "experiment_capture",
        "warnings",
        "status",
        "output_bytes",
        "exit_code",
        "kernel_pid",
        "provenance",
        "details_uri",
        "details_fingerprint",
    }
    if (
        set(data) - allowed
        or data.get("schema") != SCHEMA
        or data.get("status") not in STATUSES
        or data["epoch"] != 0
        or data["curves"]
        or data["metrics"]
        or data.get("model_weights") is not None
    ):
        raise ProjectError("CodeRun closed metadata/status schema geçersiz.")
    if data.get("schema") != SCHEMA or data.get("status") not in STATUSES:
        raise ProjectError("CodeRun schema/status geçersiz.")
    r = data["code_recipe"]
    if (
        set(r)
        != {
            "action",
            "cell_hash",
            "previous_cell_hash",
            "revision",
            "timeout_seconds",
            "environment_hash",
        }
        or r["action"] not in ("execute", "save_hash")
        or not re.fullmatch("[0-9a-f]{64}", r["cell_hash"])
        or r["previous_cell_hash"] is not None
        and not re.fullmatch("[0-9a-f]{64}", r["previous_cell_hash"])
        or type(r["revision"]) is not int
        or r["revision"] < 0
        or type(r["timeout_seconds"]) not in (int, float)
        or not 0 < r["timeout_seconds"] <= 600
        or digest(data["environment"]) != r["environment_hash"]
    ):
        raise ProjectError("CodeRun cell/config/environment hash geçersiz.")
    if (
        type(data["output_bytes"]) is not int
        or not 0 <= data["output_bytes"] <= 65536
        or data.get("exit_code") is not None
        and type(data["exit_code"]) is not int
    ):
        raise ProjectError("CodeRun output byte/exit schema geçersiz.")
    if data.get("kernel_pid") is not None and (
        type(data["kernel_pid"]) is not int or data["kernel_pid"] <= 0
    ):
        raise ProjectError("CodeRun kernel PID geçersiz.")
    expected = digest(dict(dataset=data["dataset_version"], recipe=r))
    if (
        data["compat_id"] != expected
        or data["provenance"]["parameters_hash"] != digest(r)
        or data["provenance"]["config_revision"] != r["revision"]
    ):
        raise ProjectError("CodeRun lineage/config hash uyuşmuyor.")
    if len(json.dumps(data, allow_nan=False).encode()) > 32768:
        raise ProjectError("CodeRun32KiB metadata sınırı.")
