"""Explicit manifest-only discovery, independent SDK contracts and durable data results."""

import copy
import hashlib
import json
import multiprocessing as mp
import shutil
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.domain.capabilities import CAPABILITIES, result_compatibility
from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.validation import digest
from veri_ufku.plugins import sdk
from veri_ufku.plugins.contract_test import run as contract_run
from veri_ufku.plugins.discovery import inspect
from veri_ufku.plugins.runtime import calculate, worker
from veri_ufku.storage import plugin_store as storage
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore, file_hash

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/plugins/mean"


@pytest.fixture(autouse=True)
def restore_registry():
    before = dict(CAPABILITIES)
    yield
    CAPABILITIES.clear()
    CAPABILITIES.update(before)


def package(tmp_path, code=None, **changes):
    root = tmp_path / "plugin"
    shutil.copytree(EXAMPLE, root)
    if code is not None:
        (root / "plugin.py").write_text(code)
    m = json.loads((root / "manifest.json").read_text())
    m.update(changes)
    m["code_sha256"] = hashlib.sha256((root / "plugin.py").read_bytes()).hexdigest()
    (root / "manifest.json").write_text(json.dumps(m, ensure_ascii=False))
    return root


def setup_run(tmp_path, code=None, **changes):
    root = package(tmp_path, code, **changes)
    store, ref, work = prepare(
        tmp_path, pl.DataFrame({"amount": [1.0, 2.0, 3.0, None]})
    )
    inspected, _ = inspect(root / "manifest.json")
    p = dict(
        manifest_path=str(root / "manifest.json"),
        inspection_hash=inspected["inspection_hash"],
        version=ref["version_id"],
        columns=[column(ref, "amount")],
        params={},
        seed=42,
        trusted=True,
        network_confirmed=False,
    )
    return root, store, ref, work, p


def test_manifest_inspection_never_executes_entry_and_requires_help(tmp_path):
    sentinel = tmp_path / "EXECUTED"
    root = package(
        tmp_path,
        "from pathlib import Path\nPath("
        + repr(str(sentinel))
        + ').write_text("ran")\ndef run(request,context):return {}\n',
    )
    result, code = inspect(root / "manifest.json")
    assert result["compatible"] and not sentinel.exists()
    assert "example-mean" not in CAPABILITIES
    m = result["manifest"]
    m["learning"] = {}
    with pytest.raises(ProjectError):
        sdk.manifest(m)


@pytest.mark.parametrize(
    "change",
    [
        dict(api_version=2),
        dict(python="3.14"),
        dict(entry="setup.py:install"),
        dict(permissions=["result.emit"]),
        dict(version="latest"),
    ],
)
def test_incompatible_manifest_rejected_without_execution(tmp_path, change):
    root = package(tmp_path, **change)
    with pytest.raises(ProjectError):
        inspect(root / "manifest.json")


def test_missing_dependency_is_visible_no_install_or_import(tmp_path):
    root = package(tmp_path, dependencies={"veri-ufku-nonexistent-fixture": "1.0.0"})
    info, _ = inspect(root / "manifest.json")
    assert (
        not info["compatible"]
        and info["environment"]["dependencies"]["veri-ufku-nonexistent-fixture"][
            "actual"
        ]
        == "missing"
    )
    with pytest.raises(ProjectError):
        contract_run(
            root / "manifest.json",
            json.loads((root / "request.json").read_text()),
            True,
        )


def test_independent_example_contract_and_hand_calculation(tmp_path):
    root = package(tmp_path)
    result = contract_run(
        root / "manifest.json", json.loads((root / "request.json").read_text()), True
    )
    assert result["data"]["metrics"] == dict(mean=2.0, n=3)
    with pytest.raises(ProjectError):
        contract_run(
            root / "manifest.json",
            json.loads((root / "request.json").read_text()),
            False,
        )


def test_saved_result_survives_missing_plugin_no_code_loading(tmp_path):
    root, store, ref, work, p = setup_run(tmp_path)
    ident = None
    with closing(store):
        before = file_hash(tmp_path / "source.parquet")
        req = storage.request_for(store, store.state, p)
        value = calculate(req)
        state = storage.publish(store, store.state, value)
        r = state["results"][-1]
        ident = r["capability_id"]
        assert storage.load(store, r)["output"]["data"]["metrics"] == dict(
            mean=2.0, n=3
        )
        assert value["provenance"]["source_snapshot_ids"] == [ref["source_snapshot_id"]]
        assert value["manifest"]["learning"]["id"] == "example-mean-help"
        assert file_hash(tmp_path / "source.parquet") == before
        # No plugin paths or executable code is embedded in saved artifacts.
        raw = store.path(r["plugin_result"]["details_uri"]).read_bytes()
        assert str(root).encode() not in raw and b"def run" not in raw
        target = store.root
    shutil.rmtree(root)
    CAPABILITIES.pop(ident, None)
    with closing(ProjectStore.open(target)) as reopened:
        assert storage.load(reopened, reopened.state["results"][-1]) == value
        assert result_compatibility(ident)[0] == "readonly"
        with pytest.raises(ProjectError):
            storage.request_for(reopened, reopened.state, p)
        artifact = reopened.path(
            reopened.state["results"][-1]["plugin_result"]["details_uri"]
        )
        artifact.write_bytes(b"corrupt")
        with pytest.raises(ProjectError):
            storage.load(reopened, reopened.state["results"][-1])


def test_hash_env_trust_network_and_param_binding(tmp_path):
    root, store, ref, work, p = setup_run(tmp_path)
    with closing(store):
        for change in [
            dict(trusted=False),
            dict(inspection_hash="changed"),
            dict(params={"unknown": 1}),
            dict(seed=True),
        ]:
            with pytest.raises(ProjectError):
                storage.request_for(store, store.state, {**p, **change})
        req = storage.request_for(store, store.state, p)
        req["inspection"]["manifest"]["permissions"].append("network")
        with pytest.raises(ProjectError, match="network"):
            calculate(req)
        (root / "plugin.py").write_text('raise RuntimeError("should not run")')
        with pytest.raises(ProjectError, match="hash"):
            storage.request_for(store, store.state, p)


def spawn(request, work, budget=None, cancel_now=False):
    ctx = mp.get_context("spawn")
    cancel = ctx.Event()
    recv, send = ctx.Pipe(False)
    budget = budget or ComputeBudget(max_wall_seconds=10)
    process = ctx.Process(
        target=worker, args=(request, {}, str(work), cancel, send, budget)
    )
    if cancel_now:
        cancel.set()
    process.start()
    send.close()
    try:
        assert recv.poll(15), "Worker deadline"
        try:
            return recv.recv()
        except EOFError:
            return "crashed", None
    finally:
        process.join(0.2)
        if process.is_alive():
            process.kill()
            process.join(2)
        process.close()
        recv.close()


@pytest.mark.parametrize(
    "code,expected",
    [
        (
            'def run(request,context):\n raise RuntimeError("SECRET=DO_NOT_LOG")\n',
            "error",
        ),
        ("import os\nos._exit(17)\n", "crashed"),
        ('def run(request,context):\n return {"not":"the output contract"}\n', "error"),
    ],
)
def test_failure_isolated_no_publish_secret_not_in_error(tmp_path, code, expected):
    root, store, ref, work, p = setup_run(tmp_path, code)
    with closing(store):
        before = store.commit_id
        req = storage.request_for(store, store.state, p)
        kind, value = spawn(req, work)
        assert kind == expected and "DO_NOT_LOG" not in str(value)
        assert store.commit_id == before and not store.state["results"]
        assert pl.read_parquet(tmp_path / "source.parquet").height == 4


def test_cancel_budget_and_timeout_contract(tmp_path):
    root, store, ref, work, p = setup_run(
        tmp_path, "def run(request,context):\n while True: context.check()\n"
    )
    with closing(store):
        req = storage.request_for(store, store.state, p)
        assert spawn(req, work, cancel_now=True)[0] == "canceled"
        assert (
            spawn(req, work, replace(ComputeBudget(), max_wall_seconds=0.01))[0]
            == "error"
        )
        with pytest.raises(ProjectError, match="timeout"):
            contract_run(
                root / "manifest.json",
                json.loads((root / "request.json").read_text()),
                True,
                timeout=0.1,
            )


@pytest.mark.parametrize(
    "kind,data",
    [
        ("stat", dict(metrics=dict(mean=2.0))),
        ("chart", dict(x=[1.0, 2.0], y=[3.0, 4.0], x_label="x", y_label="y")),
        (
            "model",
            dict(
                metrics=dict(mae=1.0),
                state=dict(coefficients=[1.0, 2.0]),
                prediction_supported=False,
            ),
        ),
        (
            "importer",
            dict(columns=["x"], rows=[[1.0], [2.0]], source_record_ids=["r1", "r2"]),
        ),
        (
            "transform",
            dict(columns=["x"], rows=[[1.0], [2.0]], parent_row_ids=["row:1", "row:2"]),
        ),
        ("lesson", dict(title="Örnek", paragraphs=["Hesap ve varsayım açıklaması"])),
    ],
)
def test_six_kind_versioned_output_contracts(kind, data):
    value = dict(
        schema="PluginOutput/v1",
        kind=kind,
        summary="Örnek çıktı",
        data=data,
        used_row_ids=["row:1", "row:2"],
        warnings=[],
    )
    assert sdk.output(value, kind, ["row:1", "row:2"]) == value
    for invalid in [
        dict(value, used_row_ids=["unknown"]),
        dict(value, data={}),
        dict(value, schema="PluginOutput/v2"),
    ]:
        with pytest.raises(ProjectError):
            sdk.output(invalid, kind, ["row:1", "row:2"])


def test_unsafe_result_types_and_nonfinite_rejected():
    for v in [float("nan"), float("inf"), object(), b"pickle", {"x": object()}]:
        with pytest.raises(ProjectError):
            sdk.json_data(v)


@pytest.mark.parametrize(
    "kind", ["importer", "transform", "stat", "model", "chart", "lesson"]
)
def test_each_sdk_kind_executes_and_archives_its_data_contract(tmp_path, kind):
    root, store, ref, work, p = setup_run(tmp_path)
    with closing(store):
        source = """def run(request,context):
    ids=[r['row_id'] for r in request['records']]
    kind=request['kind']
    data={
        'stat':dict(metrics=dict(n=len(ids))),
        'model':dict(metrics=dict(n=len(ids)),state=dict(coefficients=[1.]),prediction_supported=False),
        'chart':dict(x=[1.,2.],y=[3.,4.],x_label='x',y_label='y'),
        'importer':dict(columns=['x'],rows=[[1.],[2.]],source_record_ids=['record-1','record-2']),
        'transform':dict(columns=['x'],rows=[[1.],[2.]],parent_row_ids=ids[:2]),
        'lesson':dict(title='Örnek ders',paragraphs=['Hesap ve sınırlar']),
    }[kind]
    return dict(schema='PluginOutput/v1',kind=kind,summary='Gerçek fixture çıktısı',data=data,used_row_ids=ids,warnings=[])
"""
        (root / "plugin.py").write_text(source)
        m = json.loads((root / "manifest.json").read_text())
        m["capability"]["kind"] = kind
        m["code_sha256"] = hashlib.sha256(source.encode()).hexdigest()
        (root / "manifest.json").write_text(json.dumps(m))
        info, _ = inspect(root / "manifest.json")
        p["inspection_hash"] = info["inspection_hash"]
        req = storage.request_for(store, store.state, p)
        value = calculate(req)
        state = storage.publish(store, store.state, value)
        assert storage.load(store, state["results"][-1])["output"]["kind"] == kind
        assert (
            len(state["datasets"]) == 1
        )  # Table previews never silently replace the source dataset.


def test_parameter_contract_versions_and_source_change_rejection(tmp_path):
    root, store, ref, work, p = setup_run(tmp_path)
    with closing(store):
        req = storage.request_for(store, store.state, p)
        value = calculate(req)
        damaged = copy.deepcopy(value)
        damaged["output"]["used_row_ids"] = ["row:invented"]
        damaged["result_hash"] = digest(
            {k: v for k, v in damaged.items() if k != "result_hash"}
        )
        with pytest.raises(ProjectError):
            storage.publish(store, store.state, damaged)
        Path(ref["path"]).write_bytes(b"changed")
        with pytest.raises(ProjectError):
            calculate(req)


def test_manifest_params_output_secret_patterns_not_persisted(tmp_path):
    root = package(tmp_path)
    info, _ = inspect(root / "manifest.json")
    m = info["manifest"]
    m["learning"]["summary"] = "password=NEVER_PERSIST"
    with pytest.raises(ProjectError):
        sdk.manifest(m)
    for value in [{"password": "raw"}, {"x": "token=NEVER_PERSIST"}]:
        with pytest.raises(ProjectError):
            sdk.no_secrets(value)


def test_readonly_project_missing_plugin_artifact_can_be_read(tmp_path):
    root, store, ref, work, p = setup_run(tmp_path)
    with closing(store):
        req = storage.request_for(store, store.state, p)
        storage.publish(store, store.state, calculate(req))
        shutil.rmtree(root)
        with closing(ProjectStore.open(store.root)) as reader:
            assert reader.read_only
            assert (
                storage.load(reader, reader.state["results"][-1])["output"]["data"][
                    "metrics"
                ]["mean"]
                == 2.0
            )


def test_disk_quota_before_publication_preserves_previous_project(tmp_path):
    root, store, ref, work, p = setup_run(tmp_path)
    with closing(store):
        value = calculate(storage.request_for(store, store.state, p))
        before = store.commit_id
        state = copy.deepcopy(store.state)
        used = sum(
            x.stat().st_size
            for x in store.root.rglob("*")
            if x.is_file() and not x.is_symlink()
        )
        control = Control(budget=replace(ComputeBudget(), temp_disk_bytes=used + 64))
        with pytest.raises(ProjectError, match="disk"):
            storage.publish(store, store.state, value, control)
        assert store.commit_id == before and store.state == state and not store.pending
        assert pl.read_parquet(tmp_path / "source.parquet").height == 4
