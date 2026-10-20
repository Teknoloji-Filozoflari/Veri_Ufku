"""One Qt-free bounded DAG engine used by GUI worker and CLI; no ACTIVE writes."""

import copy
import fcntl
import json
import os
import shutil
import tempfile
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from veri_ufku.analytics.contracts import ProfileSpec, validate_semantics
from veri_ufku.analytics.dataset import checked, profile
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.validation import digest
from veri_ufku.operations.contracts import OperationSpec, build
from veri_ufku.operations.engine import calculate as transform
from veri_ufku.operations.workflow_contracts import DAGSpec, dependencies, order
from veri_ufku.operations.workflow_fingerprint import signature
from veri_ufku.storage.project_model import ProjectError, uid

MAX_JSON = 16 * 1024**2
SUCCESS = ("completed", "cached", "ready_export", "exported", "already_published")


def replace_paths(value, mapping):
    if isinstance(value, str):
        return mapping.get(value, value)
    if isinstance(value, list):
        return [replace_paths(v, mapping) for v in value]
    if isinstance(value, tuple):
        return tuple(replace_paths(v, mapping) for v in value)
    if isinstance(value, dict):
        return {k: replace_paths(v, mapping) for k, v in value.items()}
    return value


def references(store, state):
    result = {}
    for d in state["datasets"]:
        if not d.get("import_metadata"):
            continue
        fp = store.manifest["artifacts"][d["snapshot_uri"]]
        result[d["version_id"]] = dict(
            path=str(store.path(d["snapshot_uri"])).replace(
                "/proc/self/", f"/proc/{os.getpid()}/", 1
            ),
            fingerprint={k: fp[k] for k in ("size", "sha256")},
            columns=copy.deepcopy(d["import_metadata"]["columns"]),
            row_count=d["import_metadata"]["row_count"],
            version_id=d["version_id"],
            source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
            snapshot_uri=d["snapshot_uri"],
            semantic_metadata=copy.deepcopy(d.get("semantic_metadata", {})),
            config_revision=0,
        )
    return result


def verified_source(request, control):
    checked(request, control)
    validate_semantics(
        dict(
            import_metadata=dict(columns=request["columns"]),
            semantic_metadata=request.get("semantic_metadata", {}),
        )
    )
    schema = pl.read_parquet_schema(request["path"])
    if any(
        c["name"] not in schema or str(schema[c["name"]]) != c["type"]
        for c in request["columns"]
    ) or not {"__vu_row_id", "__vu_source_record_id"} <= set(schema):
        raise ProjectError(
            "DAG source schema/identity metadata snapshot ile uyuşmuyor."
        )


def source_for(node, case, requests):
    version = case["sources"].get(node["id"], node["params"].get("version_id"))
    if version not in requests:
        raise ProjectError("Workflow source version projede yok.")
    r = copy.deepcopy(requests[version])
    if not 1 <= r["row_count"] <= 10000 or len(r["columns"]) > 64:
        raise ProjectError("Workflow source1–10000row/64column sınırı.")
    return r


def remap_params(params, mapping):
    if isinstance(params, str):
        return mapping.get(params, params)
    if isinstance(params, list):
        return [remap_params(p, mapping) for p in params]
    if isinstance(params, dict):
        return {k: remap_params(v, mapping) for k, v in params.items()}
    return params


def compile_case(item, requests):
    compiled = {}
    nodes = {n["id"]: n for n in item["nodes"]}
    mapping = {}
    for n in item["nodes"]:
        if n["kind"] != "source":
            continue
        r = source_for(n, item["case"], requests)
        original = requests.get(n["params"].get("version_id"))
        if not original:
            raise ProjectError("Default source version yok.")
        m = item["case"]["columns"].get(n["id"], {})
        for a, b in m.items():
            old = next((c for c in original["columns"] if c["id"] == a), None)
            new = next((c for c in r["columns"] if c["id"] == b), None)
            if (
                not old
                or not new
                or old["type"] != new["type"]
                or any(
                    original.get("semantic_metadata", {}).get(a, {}).get(k)
                    != r.get("semantic_metadata", {}).get(b, {}).get(k)
                    for k in ("unit", "role", "ordinal_order")
                )
            ):
                raise ProjectError(
                    "Batch ColumnId type/unit/role/order eşlemesi uyumsuz."
                )
        if set(mapping) & set(m) and any(
            mapping[a] != b for a, b in m.items() if a in mapping
        ):
            raise ProjectError("Batch mapping çakışması.")
        mapping.update(m)
    for ident in order(item["nodes"]):
        n = nodes[ident]
        kind = n["kind"]
        params = remap_params(n["params"], mapping)
        req = (
            source_for(n, item["case"], requests)
            if kind == "source"
            else copy.deepcopy(compiled[n["inputs"]["data"]["node"]]["request"])
        )
        cols = ()
        if kind == "transform":
            if set(params) != {"kind", "columns", "parameters"} or params[
                "kind"
            ] not in ("rename", "drop", "filter"):
                raise ProjectError(
                    "DAG transform yalnız mevcut rename/drop/filter; diğer zincir işlemleri kapalı."
                )
            op = build(
                req, params["kind"], params["columns"], params["parameters"], "copy"
            )
        else:
            if kind == "source":
                params = {"version_id": req["version_id"]}
            op = build(req, "workflow_" + kind, cols, params, "copy")
        if kind in ("analysis", "quality", "train"):
            wanted = [params[k] for k in ("column", "feature", "target") if k in params]
            for c in req["columns"]:
                if c["id"] in wanted and c["type"] not in (
                    "Float64",
                    "Float32",
                    "Int64",
                    "Int32",
                    "Int16",
                    "Int8",
                    "UInt8",
                    "UInt16",
                    "UInt32",
                ):
                    raise ProjectError(
                        "DAG bounded numeric yöntem; decimal/categorical/sparse burada desteklenmiyor."
                    )
        if kind == "predict":
            model = compiled[n["inputs"]["model"]["node"]]
            features = model["params"].get("feature")
            if features not in {c["id"] for c in req["columns"]}:
                raise ProjectError("Predict training feature ColumnId eşlemesi yok.")
        out = copy.deepcopy(req)
        if kind in ("transform", "predict"):
            out.update(columns=list(op.output_schema))
        compiled[ident] = dict(request=out, operation_spec=op.data(), params=params)
    return compiled


class Cache:
    def __init__(self, parent, control):
        self.control = control
        self.root = Path(parent).resolve() / "workflow-v1"
        if self.root.is_symlink():
            raise ProjectError("Workflow cache symlink reddi.")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        marker = self.root / "OWNER"
        if not marker.exists():
            if list(self.root.iterdir()):
                raise ProjectError(
                    "Workflow cache sahiplik marker yok; mevcut dizin kullanılmadı."
                )
            marker.write_text("Veri_UfkuWorkflowCache/v1")
        if marker.is_symlink() or marker.read_text() != "Veri_UfkuWorkflowCache/v1":
            raise ProjectError("Workflow cache sahipliği geçersiz.")
        self.fd = os.open(
            self.root / "LOCK", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600
        )
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(self.fd)
            raise ProjectError(
                "Workflow cache başka runner tarafından kullanılıyor."
            ) from None
        # SIGKILL leftovers are confined to this owned private cache, never user sources.
        for p in self.root.glob(".tmp-dag-*"):
            if p.is_dir() and not p.is_symlink():
                shutil.rmtree(p)

    def close(self):
        os.close(self.fd)

    def load(self, key):
        directory = self.root / key
        if not directory.exists():
            return None, False
        try:
            if directory.is_symlink():
                raise ValueError()
            path = directory / "entry.json"
            if path.is_symlink() or path.stat().st_size > MAX_JSON:
                raise ValueError()
            entry = json.loads(path.read_text())
            if (
                set(entry) != {"key", "value", "files", "value_hash"}
                or entry["key"] != key
                or digest(entry["value"]) != entry["value_hash"]
            ):
                raise ValueError()
            for name, fp in entry["files"].items():
                if (
                    Path(name).name != name
                    or (directory / name).is_symlink()
                    or hash_artifact(directory / name, self.control) != fp
                ):
                    raise ValueError()
            value = replace_paths(
                entry["value"],
                {f"@artifact/{name}": str(directory / name) for name in entry["files"]},
            )
            return (
                value,
                {str(directory / name): fp for name, fp in entry["files"].items()},
            ), False
        except (ValueError, KeyError, TypeError, OSError):
            if directory.is_symlink():
                raise ProjectError(
                    "Cache artifact symlink; cache güvenle temizlenmeli."
                ) from None
            shutil.rmtree(directory)
            return None, True

    def save(self, key, value, files):
        directory = self.root / key
        tmp = Path(tempfile.mkdtemp(prefix=".tmp-dag-", dir=self.root))
        mapping = {}
        fps = {}
        try:
            for i, path in enumerate(dict.fromkeys(str(p) for p in files)):
                self.control.check()
                p = Path(path)
                if p.is_symlink() or not p.is_file():
                    raise ProjectError("Cache input artifact normal dosya değil.")
                name = f"{i}{p.suffix}"
                shutil.copyfile(p, tmp / name)
                fps[name] = hash_artifact(tmp / name, self.control)
                mapping[path] = "@artifact/" + name
            canonical = replace_paths(value, mapping)
            entry = dict(
                key=key, value=canonical, files=fps, value_hash=digest(canonical)
            )
            raw = json.dumps(
                entry, ensure_ascii=False, allow_nan=False, sort_keys=True
            ).encode()
            if len(raw) > MAX_JSON:
                raise ProjectError("Cache entry16MiB sınırı.")
            (tmp / "entry.json").write_bytes(raw)
            self.control.disk(self.root, force=True)
            os.rename(tmp, directory)
            return replace_paths(
                canonical, {f"@artifact/{n}": str(directory / n) for n in fps}
            ), {str(directory / n): fp for n, fp in fps.items()}
        finally:
            if tmp.exists():
                shutil.rmtree(tmp)


def execute(node, req, params, inputs, work, control):
    kind = node["kind"]
    files = []
    if kind == "transform":
        op = build(req, params["kind"], params["columns"], params["parameters"], "copy")
        result = transform(req, op, work, control)
        out = copy.deepcopy(req)
        out.update(
            path=result["path"],
            fingerprint=result["fingerprint"],
            columns=list(result["spec"]["output_schema"]),
            version_id=result["version_id"],
            row_count=result["impact"]["after_rows"],
            semantic_metadata={
                k: v
                for k, v in req.get("semantic_metadata", {}).items()
                if k in {c["id"] for c in result["spec"]["output_schema"]}
            },
        )
        files = [result["path"]]
        value = dict(
            request=out,
            report={k: result[k] for k in ("impact", "lineage", "provenance")},
            operation_spec=result["spec"],
        )
        return value, files
    op = build(req, "workflow_" + kind, (), params, "copy")
    value = dict(operation_spec=op.data())
    if kind == "source":
        value.update(request=req, report=dict(row_count=req["row_count"]))
    elif kind == "quality":
        from veri_ufku.analytics.quality import scan

        report = scan(
            req,
            dict(
                sample=False,
                target="dataset",
                purpose="inspect",
                duplicate_columns=[],
                rules=[
                    dict(
                        column_id=params["column"], kind="required", value="", upper=""
                    )
                ],
                view={},
            ),
            work,
            control,
        )
        nulls = (
            pl.scan_parquet(req["path"])
            .select(
                next(c["name"] for c in req["columns"] if c["id"] == params["column"])
            )
            .null_count()
            .collect()
            .item()
        )
        if nulls and params["fail_on_null"]:
            raise ProjectError(
                "Quality required ihlali; dur politikası; veri düzeltilmedi."
            )
        value.update(
            request=req,
            report=dict(
                null_count=nulls,
                findings=report["findings"],
                warnings=report["warnings"],
            ),
        )
    elif kind == "analysis":
        report = profile(
            req,
            ProfileSpec(params["column"], sample=False, ddof=params["ddof"]),
            work,
            control,
        )
        if report["numeric"]["suppressed"]:
            raise ProjectError("Analysis numeric measurement rolü gerekir.")
        value["report"] = {
            k: report[k] for k in ("counts", "numeric", "used_n", "scope")
        }
    elif kind == "train":
        from veri_ufku.statistics.contracts import AnalysisSpec
        from veri_ufku.statistics.models import calculate

        spec = AnalysisSpec(
            path="models",
            method="ols",
            x=params["target"],
            features=[params["feature"]],
            question="DAG explicit OLS fit",
            hypothesis="coefficient0",
            unit="source unit",
            observation_unit="independent rows; user confirmed",
            measurement_confirmed=True,
            independent=True,
            assumptions_confirmed=True,
            scope="dataset",
        )
        result = calculate(req, spec, work, control)
        value.update(
            model={
                k: result[k]
                for k in (
                    "prediction_schema",
                    "dataset_version",
                    "model_support",
                    "coefficients",
                    "fit",
                    "diagnostics",
                    "spec",
                )
            },
            report=dict(
                method="OLS",
                fit_scope="all upstream rows; no held-out score; no final-test access",
                fit_row_ids=pl.read_parquet(result["paths"]["members"])[
                    "row_id"
                ].to_list(),
            ),
        )
    elif kind == "predict":
        from veri_ufku.statistics.models import predict

        model = inputs["model"]["model"]
        names = {c["id"]: c["name"] for c in req["columns"]}
        frame = pl.read_parquet(req["path"])
        pred = []
        for row in frame.iter_rows(named=True):
            control.check()
            pred.append(
                predict(
                    model,
                    {c: row[names[c]] for c in model["prediction_schema"]["features"]},
                )["value"]
            )
        frame = frame.with_columns(pl.Series("prediction", pred, dtype=pl.Float64))
        path = Path(work) / "prediction.parquet"
        frame.write_parquet(path)
        out = copy.deepcopy(req)
        out.update(
            path=str(path),
            fingerprint=hash_artifact(path, control),
            columns=list(op.output_schema),
            version_id="dv:" + uid(),
        )
        value.update(
            request=out,
            report=dict(
                predicted_n=len(pred),
                row_policy="preserve RowId/SourceRecordId; add explicit ColumnId, no overwrite",
            ),
        )
        files = [path]
    elif kind == "export":
        from veri_ufku.exports.data import ExportSpec, generate

        result = generate(req, ExportSpec("parquet", scope="full"), work, control)
        value.update(
            report={
                k: result[k]
                for k in (
                    "rows",
                    "verified_rows",
                    "projection_verified",
                    "types_verified",
                )
            },
            export_artifact=result["artifact"],
        )
        files = [result["artifact"]]
    return value, files


def calculate(
    request, parameters, workspace, control=None, checkpoint=lambda value: None
):
    control = control or Control()
    start = time.monotonic()
    spec = DAGSpec.from_dict(parameters)
    runtime = request["workflow_runtime"]
    requests = request["workflow_sources"]
    sig = signature()
    plans = []
    total = 0
    for item in spec.expanded():
        compiled = compile_case(item, requests)
        cost = sum(v["request"]["row_count"] for v in compiled.values())
        total += cost
        plans.append((item, compiled))
    if total > 500000:
        raise ProjectError("DAG batch önkontrol500000row×node bütçesi.")
    if (
        any(n["kind"] == "export" for n in spec.nodes)
        and not runtime["dry_run"]
        and not runtime["allow_export"]
    ):
        raise ProjectError(
            "Export side effect açık onay ve output directory gerektirir."
        )
    now = datetime.now(UTC).isoformat()
    compat = digest(
        dict(
            spec=spec.data(),
            roots={k: v["fingerprint"] for k, v in requests.items()},
            signature=sig,
            runtime=runtime,
        )
    )
    data = dict(
        schema="WorkflowRun/v1",
        run_id=request["run_id"],
        training_id=request["run_id"],
        dataset_version=request["version_id"],
        origin_version=request["origin_version"],
        source_snapshot_id=request["source_snapshot_id"],
        snapshot_fingerprint=request["fingerprint"],
        seed=spec.seed,
        spec={},
        workflow_spec=spec.data(),
        workflow_runtime=runtime,
        epoch=0,
        curves=[],
        elapsed_seconds=0,
        created_at=now,
        data_access_at=now,
        prior_test_use_ids=request.get("prior_test_use_ids", []),
        plan=dict(
            split_id="dag:" + compat,
            scope="bounded DAG run artifacts; no automatic dataset head activation, no evaluation score",
            membership=dict(train=[], validation=[], test=[]),
        ),
        tensor_schema={},
        model_weights=None,
        runtime=None,
        compat_id=compat,
        metrics={},
        mode="workflow",
        environment=sig,
        experiment_capture=request.get("experiment_capture", {}),
        warnings=[
            "OLS fit on explicit upstream data is not held-out evaluation; predict on train rows is not a generalization score.",
            "Schedule unavailable: application closed means no automatic work. Explicit CLI invocation is required.",
            "Derived DatasetVersions are run-scoped artifacts; original project dataset heads and source snapshots are never overwritten.",
        ],
        nodes=[],
        artifact_paths={},
        source_references=[],
        dry_run=runtime["dry_run"],
        estimated_work=total,
    )
    roots = {}
    for item, _ in plans:
        for n in item["nodes"]:
            if n["kind"] == "source":
                r = source_for(n, item["case"], requests)
                roots[r["version_id"]] = r
    data["source_references"] = [
        {
            k: r[k]
            for k in ("version_id", "fingerprint", "source_snapshot_id", "snapshot_uri")
        }
        for r in roots.values()
    ]
    data["provenance"] = asdict(
        Provenance(
            provenance_id="provenance:" + compat,
            dataset_versions=tuple(roots),
            config_revision=request.get("config_revision", 0),
            capability_id="workflow.source",
            parameters_hash=digest(spec.data()),
            environment=(("workflow_signature", digest(sig)),),
            created_at=now,
            scope=data["plan"]["scope"],
            seed=spec.seed,
            source_snapshot_ids=tuple(r["source_snapshot_id"] for r in roots.values()),
            row_lineage_ref="workflow-node-artifact-membership:" + compat,
        )
    )
    cache = None
    try:
        if not runtime["dry_run"]:
            cache = Cache(runtime["cache"], control)
        for item, compiled in plans:
            completed = {}
            nodes = {n["id"]: n for n in item["nodes"]}
            for ident in order(item["nodes"]):
                control.check()
                n = nodes[ident]
                kind = n["kind"]
                c = compiled[ident]
                parents = dependencies(n)
                entry = dict(
                    case=item["id"],
                    node=ident,
                    kind=kind,
                    status="planned",
                    attempts=0,
                    operation_spec=c["operation_spec"],
                    cache_key=None,
                    cache_invalidated=False,
                    verified_at=None,
                )
                data["nodes"].append(entry)
                if any(
                    completed[p]["status"] not in SUCCESS and not runtime["dry_run"]
                    for p in parents
                ):
                    entry["status"] = "blocked"
                    completed[ident] = entry
                    continue
                try:
                    involved = set()
                    for p in parents:
                        involved.update(completed[p].get("root_versions", []))
                    req = (
                        source_for(n, item["case"], requests)
                        if kind == "source"
                        else copy.deepcopy(
                            completed[n["inputs"]["data"]["node"]]
                            .get("value", {})
                            .get("request", c["request"])
                        )
                    )
                    if kind == "source":
                        involved.add(req["version_id"])
                    entry["root_versions"] = sorted(involved)
                    for version in involved:
                        verified_source(roots[version], control)
                    key = digest(
                        dict(
                            node=n,
                            params=c["params"],
                            input_keys={
                                p: completed[p]["cache_key"] for p in sorted(parents)
                            },
                            roots={
                                v: {
                                    k: roots[v][k]
                                    for k in (
                                        "fingerprint",
                                        "version_id",
                                        "source_snapshot_id",
                                        "columns",
                                        "semantic_metadata",
                                    )
                                }
                                for v in sorted(involved)
                            },
                            signature=sig,
                            budget=asdict(control.budget),
                        )
                    )
                    entry["cache_key"] = key
                    if runtime["dry_run"]:
                        entry.update(
                            status="planned", verified_at=datetime.now(UTC).isoformat()
                        )
                        completed[ident] = entry
                        continue
                    hit, invalid = cache.load(key)
                    entry["cache_invalidated"] = invalid
                    if hit:
                        value, files = hit
                        entry.update(value=value, status="cached", attempts=0)
                        data["artifact_paths"].update(files)
                    else:
                        for attempt in range(spec.retries + 1):
                            entry["attempts"] = attempt + 1
                            try:
                                with tempfile.TemporaryDirectory(
                                    prefix="dag-node-", dir=workspace
                                ) as work:
                                    inputs = {
                                        k: completed[e["node"]]["value"]
                                        for k, e in n["inputs"].items()
                                    }
                                    value, files = execute(
                                        n, req, c["params"], inputs, work, control
                                    )
                                    value, files = cache.save(key, value, files)
                                entry.update(value=value, status="completed")
                                data["artifact_paths"].update(files)
                                break
                            except OSError:
                                if attempt == spec.retries:
                                    raise ProjectError(
                                        "Workflow transient I/O retry tükendi; side effect otomatik tekrarlanmadı."
                                    ) from None
                    # Cache hits are never current without AGAIN validating immutable roots.
                    for version in involved:
                        verified_source(roots[version], control)
                    if kind in ("source", "quality"):
                        entry["value"]["request"] = copy.deepcopy(req)
                    entry["operation_spec"] = entry["value"]["operation_spec"]
                    entry["verified_at"] = datetime.now(UTC).isoformat()
                    if kind == "export":
                        entry["status"] = "ready_export"
                        entry["destination"] = str(
                            Path(runtime["output_dir"])
                            / (
                                runtime["export_token"]
                                + "-"
                                + item["id"]
                                + "-"
                                + ident
                                + ".parquet"
                            )
                        )
                    entry["provenance"] = asdict(
                        Provenance(
                            provenance_id="provenance:" + key,
                            dataset_versions=tuple(involved),
                            config_revision=request.get("config_revision", 0),
                            capability_id="workflow." + kind,
                            parameters_hash=digest(entry["operation_spec"]),
                            environment=(("workflow_signature", digest(sig)),),
                            created_at=entry["verified_at"],
                            scope="run scoped node output; verified cache"
                            if hit
                            else "computed node output",
                            seed=spec.seed,
                            source_snapshot_ids=tuple(
                                roots[v]["source_snapshot_id"] for v in sorted(involved)
                            ),
                            row_lineage_ref="OperationSpec:"
                            + entry["operation_spec"]["id"],
                        )
                    )
                except ProjectError as e:
                    entry.update(status="failed", error=str(e), value=None)
                completed[ident] = entry
                control.progress(
                    "DAG " + item["id"] + " / " + ident,
                    len(data["nodes"]),
                    len(spec.nodes) * len(plans),
                )
        data["status"] = (
            "dry_run"
            if runtime["dry_run"]
            else "partial"
            if any(n["status"] in ("failed", "blocked") for n in data["nodes"])
            else "completed"
        )
    except Canceled:
        data["status"] = "canceled"
    finally:
        if cache:
            cache.close()
    data["elapsed_seconds"] = time.monotonic() - start
    validate(data)
    checkpoint(copy.deepcopy(data))
    return data


def validate(data):
    DAGSpec.from_dict(data["workflow_spec"])
    if (
        data.get("schema") != "WorkflowRun/v1"
        or data.get("status")
        not in (
            "completed",
            "partial",
            "failed",
            "canceled",
            "budget_exhausted",
            "dry_run",
        )
        or data["epoch"] != 0
        or data["curves"]
        or len(data["nodes"]) > 192
    ):
        raise ProjectError("WorkflowRun closed schema/status geçersiz.")
    for n in data["nodes"]:
        OperationSpec.from_dict(n["operation_spec"])
    if len(json.dumps(data, allow_nan=False).encode()) > MAX_JSON:
        raise ProjectError("WorkflowRun16MiB safe JSON sınırı.")
