"""Workflow artifacts/effects use existing ProjectStore transaction and neural journal."""

import copy
import shutil
from pathlib import Path

from veri_ufku.exports.files import publish as publish_file
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.project_store import file_hash


def attach(store, state, data):
    from veri_ufku.operations.workflow import SUCCESS, replace_paths

    data = copy.deepcopy(data)
    mapping = {}
    safe_roots = {}
    versions = {d["version_id"]: d for d in state["datasets"]}
    for ref in data["source_references"]:
        d = versions.get(ref["version_id"])
        if (
            not d
            or d["snapshot_uri"] != ref["snapshot_uri"]
            or d["import_metadata"]["source_snapshot_id"] != ref["source_snapshot_id"]
        ):
            raise ProjectError("DAG source version/snapshot journal bağı geçersiz.")
        safe_roots[ref["version_id"]] = (
            file_hash(store.path(ref["snapshot_uri"])) == ref["fingerprint"]
        )
    # Invalidate only affected descendants; no stale result is promoted or exported.
    for node in data["nodes"]:
        if node["status"] in SUCCESS and any(
            not safe_roots.get(v, False) for v in node.get("root_versions", [])
        ):
            node.update(
                status="stale",
                value=None,
                error="Source fingerprint yayın öncesi değişti; sonuç güncel değil.",
            )
    owned = []
    for r in state["results"]:
        old = r.get("neural", {})
        if (
            old.get("schema") == "WorkflowRun/v1"
            and old.get("workflow_runtime", {}).get("export_token")
            == data["workflow_runtime"]["export_token"]
        ):
            owned.extend(old.get("export_receipts", []))
    receipts = []
    if data["status"] not in ("completed", "partial"):
        for node in data["nodes"]:
            if node["status"] == "ready_export":
                node.update(
                    status="canceled",
                    value=None,
                    error="Run iptal edildi; dış eylem yayınlanmadı.",
                )
    for node in data["nodes"]:
        if node["status"] != "ready_export":
            continue
        destination = Path(node["destination"])
        source = Path(node["value"]["export_artifact"])
        expected = file_hash(source)
        try:
            owner = next(
                (
                    o
                    for o in owned
                    if o["case"] == node["case"]
                    and o["node"] == node["node"]
                    and o["cache_key"] == node["cache_key"]
                    and o["path"] == str(destination)
                    and o["fingerprint"] == expected
                ),
                None,
            )
            if destination.exists() or destination.is_symlink():
                if (
                    not owner
                    or destination.is_symlink()
                    or file_hash(destination) != expected
                ):
                    raise ProjectError(
                        "DAG export collision/unowned/orphan artifact: overwrite yapılmadı."
                    )
                status = "already_published"
            else:
                publish_file(source, destination, store.root)
                status = "exported"
            receipt = dict(
                case=node["case"],
                node=node["node"],
                cache_key=node["cache_key"],
                path=str(destination),
                fingerprint=expected,
                status=status,
                owner_token=data["workflow_runtime"]["export_token"],
            )
            node["status"] = status
            receipts.append(receipt)
        except (ValueError, OSError) as e:
            node.update(
                status="failed",
                value=None,
                error=str(e)
                if isinstance(e, ProjectError)
                else "DAG external publication I/O failure; automatic retry yok.",
            )
    data["export_receipts"] = receipts
    staging = store.path("staging") / uid()
    staging.mkdir(mode=0o700)
    uris = {}
    try:
        # Every worker artifact is copied and rehashed through the sole project store.
        for i, (path, fp) in enumerate(data.pop("artifact_paths", {}).items()):
            p = Path(path)
            if p.is_symlink() or file_hash(p) != fp:
                raise ProjectError("DAG artifact hash değişti; yayın reddedildi.")
            local = staging / (str(i) + p.suffix)
            shutil.copyfile(p, local)
            if file_hash(local) != fp:
                raise ProjectError("DAG artifact copy hash değişti.")
            uri = "sources/" + uid() + p.suffix
            store.pending[uri] = (
                local,
                dict(**fp, kind="source", rows=None, schema=None),
            )
            mapping[path] = uri
            uris[uri] = fp
        for node in data["nodes"]:
            value = node.get("value") or {}
            r = value.get("request")
            if node["kind"] == "source" and r:
                mapping[r["path"]] = r["snapshot_uri"]
        data = replace_paths(data, mapping)
        data["artifact_uris"] = uris
        if data["status"] == "completed" and any(
            n["status"] in ("failed", "blocked", "stale") for n in data["nodes"]
        ):
            data["status"] = "partial"
        return data
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def validate_journal(data, versions):
    refs = data["source_references"]
    for r in refs:
        d = versions.get(r["version_id"])
        if (
            not d
            or d["snapshot_uri"] != r["snapshot_uri"]
            or d["import_metadata"]["source_snapshot_id"] != r["source_snapshot_id"]
        ):
            raise ProjectError("Workflow root lineage journal geçersiz.")
    for uri, fp in data.get("artifact_uris", {}).items():
        if (
            not uri.startswith("sources/")
            or Path(uri).as_posix() != uri
            or len(Path(uri).parts) != 2
            or Path(uri).parts[0] != "sources"
            or Path(uri).parts[1] in (".", "..")
            or set(fp) != {"size", "sha256"}
        ):
            raise ProjectError("Workflow artifact reference geçersiz.")
