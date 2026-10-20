"""Explicit bounded re-run comparison. No arbitrary code/model import from bundles."""

import copy
import math
from contextlib import closing, nullcontext
from pathlib import Path

import polars as pl

from veri_ufku.analytics.dataset import checked
from veri_ufku.exports.code_bridge import CodeRecipe, run_profile
from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.modeling.validation import digest
from veri_ufku.operations.workflow_contracts import DAGSpec
from veri_ufku.storage.project_model import ProjectError, entity_id, uid
from veri_ufku.storage.project_store import ProjectStore


def validate_replay(replay):
    if replay is None:
        return
    if not isinstance(replay, dict):
        raise ProjectError("Re-run recipe kapalı şema.")
    if replay.get("kind") == "profile":
        if set(replay) != {"kind", "version", "recipe", "reference"}:
            raise ProjectError("Profile re-run alanları.")
        entity_id(replay["version"], "dv")
        CodeRecipe.from_dict(replay["recipe"])
    elif replay.get("kind") == "workflow":
        if set(replay) != {"kind", "spec", "reference", "recorded_signature"}:
            raise ProjectError("Workflow re-run alanları.")
        DAGSpec.from_dict(replay["spec"])
    else:
        raise ProjectError("Yöntem için re-run adapter mevcut değil.")


def workflow_projection(data, resolve):
    result = {}
    for n in data["nodes"]:
        if n["status"] not in (
            "completed",
            "cached",
            "exported",
            "already_published",
            "ready_export",
        ):
            raise ProjectError(
                "Başarısız/eksik workflow karşılaştırması desteklenmiyor."
            )
        value = n.get("value") or {}
        report = value.get("report", {})
        kind = n["kind"]
        out = dict(kind=kind)
        if kind == "analysis":
            out["profile"] = report
        elif kind == "quality":
            out["null_count"] = report["null_count"]
        elif kind == "train":
            # Prediction schema coeffs are Float64; no manufactured held-out metric.
            out.update(
                coefficients=value["model"]["prediction_schema"]["coefficients"],
                fit_row_ids=report["fit_row_ids"],
            )
        elif kind == "export":
            out["rows"] = report["rows"]
        elif kind in ("source", "transform", "predict"):
            request = value["request"]
            path = resolve(request["path"])
            frame = pl.read_parquet(path)
            if frame.height > 10000:
                raise ProjectError("Workflow projection10000row sınırı.")
            out.update(
                row_ids=frame["__vu_row_id"].to_list(),
                source_record_ids=frame["__vu_source_record_id"].to_list(),
                columns=[dict(id=c["id"], type=c["type"]) for c in request["columns"]],
            )
            # Original source values remain referenced by hash; only prediction values included.
            if kind == "predict":
                out["predictions"] = frame["prediction"].to_list()
        result[n["case"] + "/" + n["node"]] = out
    return result


def policy(replay, mode):
    if mode not in ("exact", "numeric"):
        raise ProjectError("Exact veya numeric policy seçin.")
    return dict(
        schema="ReproTolerance/v1",
        mode=mode,
        profile="Decimal80 profile strings/counts/scope exact; no epsilon for integers/Decimal/identities",
        float64_workflow=dict(
            rtol="1e-9" if mode == "numeric" else "0",
            atol="1e-12" if mode == "numeric" else "0",
            fields=["coefficients", "predictions"],
            reason="Bounded OLS Float64 coefficient/matrix prediction; small platform rounding allowance in output units. Not a universal statistical equivalence or conditioning guarantee; inspect differences. Environment/backend lock must still match.",
        ),
        identities="RowId/SourceRecordId/ColumnId, integer counts, categories and null masks exact",
        supported_method=replay["kind"],
    )


def compare(reference, actual, replay, mode):
    p = policy(replay, mode)
    diffs = []
    total = 0

    def fail(path, reason, a, b):
        nonlocal total
        total += 1
        if len(diffs) < 50:
            diffs.append(dict(field=path, reason=reason, reference=a, actual=b))

    def walk(a, b, path="result", tolerant=False):
        if isinstance(a, dict) and isinstance(b, dict):
            if set(a) != set(b):
                fail(path, "keys differ", sorted(a), sorted(b))
                return
            for k in a:
                walk(
                    a[k],
                    b[k],
                    path + "." + k,
                    tolerant
                    or (
                        replay["kind"] == "workflow"
                        and k in ("coefficients", "predictions")
                    ),
                )
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                fail(path, "length differs", len(a), len(b))
                return
            for i, (x, y) in enumerate(zip(a, b, strict=True)):
                walk(x, y, path + "." + str(i), tolerant)
        elif (
            tolerant
            and mode == "numeric"
            and isinstance(a, (int, float))
            and not isinstance(a, bool)
            and isinstance(b, (int, float))
            and not isinstance(b, bool)
        ):
            # This numeric path is restricted to Float64 model outputs; integers elsewhere exact.
            if not math.isfinite(a) or not math.isfinite(b):
                if a != b:
                    fail(path, "nonfinite mismatch", a, b)
            elif not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12):
                fail(path, "outside documented Float64 tolerance", a, b)
        elif type(a) is not type(b) or a != b:
            fail(path, "exact mismatch", a, b)

    walk(reference, actual)
    return dict(
        schema="ReproComparison/v1",
        status="matched" if not total else "different",
        difference_count=total,
        differences=diffs,
        differences_truncated=total > 50,
        policy=p,
        reference_hash=digest(reference),
        actual_hash=digest(actual),
        scope="defined analytical projection only; timestamps/cache/run UUIDs/visual layout not compared; original source hash must match",
    )


def resolve_reference(ref, store, archive, work, control):

    columns = None
    semantics = {}
    if store:
        d = next(
            (
                d
                for d in store.state["datasets"]
                if d["version_id"] == ref["version_id"]
            ),
            None,
        )
        if not d:
            raise ProjectError(
                "Reference DatasetVersion projede yok; otomatik remap yok."
            )
        columns = d["import_metadata"]["columns"]
        semantics = d.get("semantic_metadata", {})
        if (
            d["import_metadata"]["source_snapshot_id"] != ref["source_snapshot_id"]
            or digest(columns) != ref["column_schema_hash"]
            or digest(semantics) != ref["semantic_hash"]
        ):
            raise ProjectError("Reference version/schema/semantic metadata değişti.")
        path = store.path(d["snapshot_uri"])
    else:
        import zipfile

        member = ref.get("included_member")
        if not member:
            raise ProjectError(
                "Reference-only bundle; açık yerel proje erişimi gerekir. Ağ otomatik açılmaz."
            )
        path = Path(work) / (ref["version_id"].removeprefix("dv:") + ".parquet")
        with (
            zipfile.ZipFile(archive) as z,
            z.open(member) as inp,
            path.open("xb") as out,
        ):
            while chunk := inp.read(1024**2):
                control.check()
                out.write(chunk)
        # Native snapshots carry physical column names. Bind IDs using manifest column order.
        schema = pl.read_parquet_schema(path)
        names = [n for n in schema if not n.startswith("__vu_")]
        if len(names) != len(ref["columns"]):
            raise ProjectError("Included native schema/ColumnId order uyuşmuyor.")
        columns = [
            dict(id=c["id"], name=n, original_name=n, type=str(schema[n]))
            for n, c in zip(names, ref["columns"], strict=True)
        ]
        if any(
            c["type"] != r["type"] for c, r in zip(columns, ref["columns"], strict=True)
        ):
            raise ProjectError("Included native type uyuşmuyor.")
        # Semantics affects role-sensitive profile/model behavior; never silently invent it.
        semantics = ref.get("included_semantics", {})
    current_fingerprint = hash_artifact(path, control)
    if current_fingerprint != ref["fingerprint"]:
        raise ProjectError(
            "Dataset fingerprint değişti; beklenen SHA256="
            + ref["fingerprint"]["sha256"]
            + "; yeni SHA256="
            + current_fingerprint["sha256"]
            + ". Re-run durdu, eski çıktı güncel sayılmadı."
        )
    request = dict(
        path=str(path),
        fingerprint=ref["fingerprint"],
        version_id=ref["version_id"],
        columns=columns,
        semantic_metadata=semantics,
        row_count=ref["rows"],
        snapshot_uri=ref["uri"],
        source_snapshot_id=ref["source_snapshot_id"],
        config_revision=0,
    )
    checked(request, control)
    return request


def rerun(archive, project, mode, workspace, control=None, *, project_view=None):
    from veri_ufku.exports.repro import environment, open_bundle

    control = control or Control()
    opened = open_bundle(archive, control)
    payload = opened["payload"]
    manifest = opened["manifest"]
    replay = payload["config.json"]["replay"]
    if not replay or not manifest["rerun_supported"]:
        raise ProjectError(
            "Bu kaydın re-run adapter/recipe/provenance bilgisi desteklenmiyor."
        )
    validate_replay(replay)
    policy(replay, mode)
    expected = payload["environment.lock.json"]
    if environment() != expected:
        raise ProjectError(
            "Environment/backend/code/platform sürümü farklı; safe failure. Otomatik migration/model import yok."
        )
    from veri_ufku.jobs.limits import configure_threads

    configure_threads(control.budget.worker_threads)
    # Verify again after every input is read; original project always read-only.
    with (
        nullcontext(project_view)
        if project_view is not None
        else closing(ProjectStore.open(project, writable=False))
        if project
        else nullcontext(None) as store
    ):
        requests = {
            r["version_id"]: resolve_reference(r, store, archive, workspace, control)
            for r in manifest["references"]
        }
        if replay["kind"] == "profile":
            actual = run_profile(
                requests[replay["version"]], replay["recipe"], workspace, control
            )
        else:
            from veri_ufku.operations.workflow import calculate, signature

            if replay["recorded_signature"] != signature():
                raise ProjectError(
                    "Historical workflow backend signature differs; unsafe migration refused."
                )
            source = next(n for n in replay["spec"]["nodes"] if n["kind"] == "source")
            request = copy.deepcopy(requests[source["params"]["version_id"]])
            request.update(
                run_id="run:" + uid(),
                origin_version=request["version_id"],
                workflow_sources=requests,
                workflow_runtime=dict(
                    cache=str(Path(workspace) / "cache"),
                    output_dir=str(workspace),
                    allow_export=True,
                    dry_run=False,
                    export_token=uid(),
                ),
                prior_test_use_ids=[],
            )
            result = calculate(request, replay["spec"], workspace, control)
            # Export artifacts are prepared in private temp only; NO parent publication/receipts.
            actual = workflow_projection(result, lambda path: Path(path))
        for req in requests.values():
            checked(req, control)
    reference = payload["reference-report.json"]
    if reference != replay["reference"]:
        raise ProjectError("Reference report/config uyuşmuyor.")
    if hash_artifact(archive, control) != opened["bundle_fingerprint"]:
        raise ProjectError("Bundle re-run sırasında değişti; çıktı yayınlanmadı.")
    result = compare(reference, actual, replay, mode)
    result.update(
        bundle_fingerprint=opened["bundle_fingerprint"],
        source_status="all exact hashes verified",
        data_access="explicit included snapshots"
        if not project
        else "explicit read-only local project",
        environment_hash=digest(expected),
        replay_kind=replay["kind"],
    )
    files = {
        "comparison.json": result,
        "reference-report.json": reference,
        "actual-report.json": actual,
    }
    for name, value in files.items():
        from veri_ufku.exports.repro import raw

        (Path(workspace) / name).write_bytes(raw(value))
    return result
