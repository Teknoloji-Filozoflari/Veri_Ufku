"""Budgeted trusted-code worker; no Qt, no automatic activation, no ACTIVE writes."""

import contextlib
import hashlib
import io
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.validation import digest
from veri_ufku.plugins.sdk import (
    ContextV1,
    input_contract,
    json_data,
    manifest,
    output,
    parameters,
)
from veri_ufku.storage.project_model import ProjectError, decode, encode, uid
from veri_ufku.storage.project_store import file_hash


def input_data(request, control):
    import pyarrow.parquet as pq

    ref = request["source"]
    selected = request["columns"]
    if (
        ref["row_count"] > 10000
        or ref["fingerprint"]["size"] > 32 * 1024**2
        or not 1 <= len(selected) <= 16
    ):
        raise ProjectError("Plugin dataset10000row/32MiB/16column sınırı.")
    if file_hash(Path(ref["path"])) != ref["fingerprint"]:
        raise ProjectError("Plugin source hash değişmiş.")
    columns = {c["id"]: c for c in ref["columns"]}
    if not set(selected) <= columns.keys() or len(selected) != len(set(selected)):
        raise ProjectError("Plugin ColumnId seçim hatası.")
    records = []
    ids = []
    for batch in pq.ParquetFile(ref["path"]).iter_batches(
        batch_size=256,
        columns=[columns[c]["name"] for c in selected]
        + ["__vu_row_id", "__vu_source_record_id"],
    ):
        control.check()
        for row in batch.to_pylist():
            values = {c: row[columns[c]["name"]] for c in selected}
            # No silent float/decimal/datetime coercion; authors see only finite JSON scalar values.
            json_data(values, 65536)
            records.append(
                dict(
                    row_id=row["__vu_row_id"],
                    source_record_id=row["__vu_source_record_id"],
                    values=values,
                )
            )
            ids.append(row["__vu_row_id"])
    data = dict(
        schema="PluginInput/v1",
        api_version=1,
        kind=request["inspection"]["manifest"]["capability"]["kind"],
        dataset_version=ref["version_id"],
        source_snapshot_id=ref["source_snapshot_id"],
        columns=[columns[c] for c in selected],
        records=records,
        params=request["params"],
        seed=request["seed"],
    )
    input_contract(data, data["kind"])
    if file_hash(Path(ref["path"])) != ref["fingerprint"]:
        raise ProjectError("Plugin source okuma sırasında değişmiş.")
    return data, ids


def calculate(request, control=None):
    control = control or Control()
    control.check()
    m = manifest(request["inspection"]["manifest"])
    source = request["code"]
    if (
        request["trusted"] is not True
        or request["inspection_hash"] != request["inspection"]["inspection_hash"]
        or not request["inspection"]["compatible"]
    ):
        raise ProjectError(
            "Plugin için aynı manifest/env/hash explicit güven onayı gerekli."
        )
    if "network" in m["permissions"] and request["network_confirmed"] is not True:
        raise ProjectError("Bildirilen network izni ayrı açık kullanıcı onayı gerekli.")
    if hashlib.sha256(source).hexdigest() != m["code_sha256"]:
        raise ProjectError("Plugin kod hash değişmiş.")
    parameters(m, request["params"])
    data, ids = input_data(request, control)
    if "dataset.read" not in m["permissions"]:
        raise ProjectError("Dataset girdisi için manifest dataset.read gerekli.")
    scope = {"__name__": "veri_ufku_explicit_plugin", "__file__": "<trusted-plugin>"}
    # No pickle/module-object IPC. Suppress untrusted stdout/stderr; never persist its exception messages.
    with (
        contextlib.redirect_stdout(io.StringIO()),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        exec(compile(source, "<trusted-plugin>", "exec"), scope)
        if not callable(scope.get("run")):
            raise ProjectError("Plugin run(request, context) giriş noktası yok.")
        result = output(
            scope["run"](data, ContextV1(control)), m["capability"]["kind"], ids
        )
    control.check()
    if file_hash(Path(request["source"]["path"])) != request["source"]["fingerprint"]:
        raise ProjectError("Plugin çalışırken kaynak değişmiş; sonuç yayınlanmadı.")
    now = datetime.now(UTC).isoformat()
    value = dict(
        schema="PluginRun/v1",
        run_id="pluginrun:" + uid(),
        dataset_version=request["source"]["version_id"],
        manifest=m,
        package_hash=request["inspection"]["package_hash"],
        inspection_hash=request["inspection_hash"],
        environment=request["inspection"]["environment"],
        params=request["params"],
        seed=request["seed"],
        columns=request["columns"],
        source_fingerprint=request["source"]["fingerprint"],
        source_snapshot_id=request["source"]["source_snapshot_id"],
        output=result,
        status="completed",
        decision=dict(
            trusted=True,
            network_confirmed=request["network_confirmed"],
            permissions=m["permissions"],
            enforcement="declaration only; NOT OS sandbox",
        ),
        warnings=[
            "Trusted Python, not sandboxed; permissions not OS enforced. Output is a plugin claim, not host scientific validation.",
            "Importer/transform outputs are archived table previews; active dataset mutation/apply unavailable. Model predict/reload unavailable.",
        ],
        provenance=asdict(
            Provenance(
                provenance_id="provenance:" + uid(),
                dataset_versions=(request["source"]["version_id"],),
                config_revision=0,
                capability_id=request["capability_id"],
                parameters_hash=digest(request["params"]),
                environment=(
                    ("plugin", m["id"] + "@" + m["version"]),
                    ("code_sha256", m["code_sha256"]),
                    ("python", request["inspection"]["environment"]["python"]),
                ),
                created_at=now,
                method_version=m["capability"]["method_version"],
                scope="explicit trusted plugin; bounded selected dataset; recorded JSON result only",
                seed=request["seed"],
                source_snapshot_ids=(request["source"]["source_snapshot_id"],),
                row_lineage_ref="output.used_row_ids; selected source only",
                learning_content_version=str(m["learning"]["version"]),
            )
        ),
    )
    value = decode(encode(value))
    value["result_hash"] = digest(value)
    json_data(value, 2 * 1024**2)
    return value


def worker(request, spec, workspace, cancel, sender, budget):
    import os

    try:
        apply_process_limits(budget)
        # Real FD redirection also suppresses native/uncaught plugin prints, bounded by host process budget.
        null = os.open(os.devnull, os.O_WRONLY)
        os.dup2(null, 1)
        os.dup2(null, 2)
        os.close(null)
        sender.send(("result", calculate(request, Control(cancel, budget=budget))))
    except Canceled:
        sender.send(("canceled", None))
    except Exception as e:
        sender.send(
            (
                "error",
                resource_error_text(
                    e,
                    "Plugin çalışmadı ("
                    + type(e).__name__
                    + "); önceki proje/sonuç korundu.",
                ),
            )
        )
    finally:
        sender.close()
