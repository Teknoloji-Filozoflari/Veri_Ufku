"""Data-only plugin artifact publication in the existing ProjectStore journal."""

import copy
from pathlib import Path

from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.validation import digest
from veri_ufku.operations.workflow import references
from veri_ufku.plugins.discovery import inspect, register
from veri_ufku.plugins.sdk import json_data, manifest, output, parameters
from veri_ufku.storage.project_model import ProjectError, decode, encode, uid
from veri_ufku.storage.project_store import file_hash
from veri_ufku.storage.validation_store import transaction


def request_for(store, state, p):
    if not isinstance(p, dict) or set(p) != {
        "manifest_path",
        "inspection_hash",
        "version",
        "columns",
        "params",
        "seed",
        "trusted",
        "network_confirmed",
    }:
        raise ProjectError("PluginRun recipe kapalı şema gerekli.")
    inspected, code = inspect(p["manifest_path"])
    if (
        p["trusted"] is not True
        or type(p["network_confirmed"]) is not bool
        or p["inspection_hash"] != inspected["inspection_hash"]
        or not inspected["compatible"]
    ):
        raise ProjectError(
            "Uyumluluk, bağımlılık ve aynı hash için explicit trust onayı gerekli."
        )
    if type(p["seed"]) is not int or not 0 <= p["seed"] <= 2**32 - 1:
        raise ProjectError("Plugin seed uint32 gerekli.")
    parameters(inspected["manifest"], p["params"])
    refs = references(store, state)
    if p["version"] not in refs:
        raise ProjectError("Plugin dataset version yok.")
    if not isinstance(p["columns"], list) or any(
        not isinstance(c, str) for c in p["columns"]
    ):
        raise ProjectError("Plugin ColumnId listesi gerekli.")
    req = copy.deepcopy(p)
    req.pop("manifest_path")
    req.update(
        inspection=inspected,
        code=code,
        source=refs[p["version"]],
        capability_id=register(inspected),
    )
    return req


def validate(v):
    fields = {
        "schema",
        "run_id",
        "dataset_version",
        "manifest",
        "package_hash",
        "inspection_hash",
        "environment",
        "params",
        "seed",
        "columns",
        "source_fingerprint",
        "source_snapshot_id",
        "output",
        "status",
        "decision",
        "warnings",
        "provenance",
        "result_hash",
    }
    if (
        not isinstance(v, dict)
        or set(v) != fields
        or v["schema"] != "PluginRun/v1"
        or v["status"] != "completed"
        or v["result_hash"]
        != digest({k: x for k, x in v.items() if k != "result_hash"})
    ):
        raise ProjectError("Plugin result hash/schema geçersiz.")
    m = manifest(v["manifest"])
    parameters(m, v["params"])
    output(v["output"], m["capability"]["kind"], v["output"]["used_row_ids"])
    if v["package_hash"] != digest(dict(manifest=m, code_sha256=m["code_sha256"])):
        raise ProjectError("Plugin manifest provenance hash geçersiz.")
    if (
        v["provenance"]["capability_id"]
        != "plugin." + m["id"] + "." + m["capability"]["id"]
        or v["provenance"]["dataset_versions"] != [v["dataset_version"]]
        or v["provenance"]["method_version"] != m["capability"]["method_version"]
    ):
        raise ProjectError("Plugin method/source provenance uyuşmuyor.")
    if (
        v["provenance"]["parameters_hash"] != digest(v["params"])
        or v["provenance"]["source_snapshot_ids"] != [v["source_snapshot_id"]]
        or v["provenance"]["seed"] != v["seed"]
    ):
        raise ProjectError("Plugin parametre/source/seed provenance farklı.")
    if (
        not isinstance(v["decision"], dict)
        or set(v["decision"])
        != {"trusted", "network_confirmed", "permissions", "enforcement"}
        or v["decision"]["trusted"] is not True
        or type(v["decision"]["network_confirmed"]) is not bool
        or v["decision"]["permissions"] != m["permissions"]
    ):
        raise ProjectError("Plugin explicit trust karar kaydı eksik.")
    json_data(v, 2 * 1024**2)


def publish(store, state, value, control=None):
    control = control or Control()
    validate(value)
    # Publication uses only data, never imports or re-executes the plugin.
    refs = references(store, state)
    ref = refs.get(value["dataset_version"])
    if (
        not ref
        or ref["fingerprint"] != value["source_fingerprint"]
        or file_hash(Path(ref["path"])) != ref["fingerprint"]
    ):
        raise ProjectError("Plugin kaynak yayından önce değişmiş.")
    import pyarrow.parquet as pq

    ids = set(pq.read_table(ref["path"], columns=["__vu_row_id"]).column(0).to_pylist())
    output(value["output"], value["manifest"]["capability"]["kind"], ids)
    raw = encode(value)

    def add(draft):
        control.check()
        control.disk(store.root, force=True)
        stage = store.path("staging") / uid()
        stage.mkdir(mode=0o700)
        path = stage / "plugin.bin"
        path.write_bytes(raw)
        control.disk(store.root, force=True)
        fp = file_hash(path)
        uri = "sources/" + uid() + ".bin"
        store.pending[uri] = (path, dict(**fp, kind="source", rows=None, schema=None))
        draft["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=[value["dataset_version"]],
                seed=value["seed"],
                capability_id=value["provenance"]["capability_id"],
                plugin_result=dict(
                    schema="PluginResultRef/v1",
                    run_id=value["run_id"],
                    dataset_version=value["dataset_version"],
                    plugin_id=value["manifest"]["id"],
                    plugin_version=value["manifest"]["version"],
                    kind=value["manifest"]["capability"]["kind"],
                    learning_id=value["manifest"]["learning"]["id"],
                    package_hash=value["package_hash"],
                    result_hash=value["result_hash"],
                    provenance=value["provenance"],
                    details_uri=uri,
                    details_fingerprint=fp,
                    status="completed",
                    recompute="requires explicit manifest/hash/env/trust; opening never loads code",
                ),
            )
        )
        control.check()

    return transaction(store, state, add)


def load(store, record):
    s = record["plugin_result"]
    path = store.path(s["details_uri"])
    if file_hash(path) != s["details_fingerprint"]:
        raise ProjectError("Plugin artifact hash bozuk.")
    v = decode(path.read_bytes())
    validate(v)
    if (
        v["result_hash"] != s["result_hash"]
        or v["run_id"] != s["run_id"]
        or v["provenance"] != s["provenance"]
    ):
        raise ProjectError("Plugin summary/artifact farklı.")
    return v


def validate_records(state):
    versions = {d["version_id"] for d in state["datasets"]}
    for r in state["results"]:
        if "plugin_result" not in r:
            continue
        s = r["plugin_result"]
        if (
            s.get("schema") != "PluginResultRef/v1"
            or s.get("status") != "completed"
            or s["details_fingerprint"]["size"] > 2 * 1024**2
            or r["dataset_version_ids"] != [s["dataset_version"]]
            or s["dataset_version"] not in versions
        ):
            raise ProjectError("Plugin archived result referansı geçersiz.")
