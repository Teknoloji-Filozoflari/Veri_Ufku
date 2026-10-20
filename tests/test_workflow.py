"""Real local typed DAG computation, cache validation and isolated publication."""

import copy
from contextlib import closing

import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.operations.workflow import calculate
from veri_ufku.operations.workflow_contracts import DAGSpec
from veri_ufku.operations.workflow_service import request_for, run_headless
from veri_ufku.storage.neural_store import load, publish
from veri_ufku.storage.project_model import ProjectError, uid


def node(ident, kind, params, data=None, model=None, after=()):
    inputs = {}
    if data:
        inputs["data"] = dict(node=data, port="data")
    if model:
        inputs["model"] = dict(node=model, port="model")
    return dict(
        id=ident,
        kind=kind,
        params=params,
        inputs=inputs,
        after=list(after),
        method_version=1,
    )


def recipe(r, full=False):
    x, y = column(r, "x"), column(r, "y")
    nodes = [
        node("source", "source", dict(version_id=r["version_id"])),
        node("summary", "analysis", dict(column=x, ddof=1), "source"),
        node("quality", "quality", dict(column=y, fail_on_null=True), "source"),
    ]
    if full:
        nodes += [
            node("fit", "train", dict(feature=x, target=y, confirmed=True), "quality"),
            node(
                "predict",
                "predict",
                dict(prediction_column="col:" + uid()),
                "source",
                "fit",
            ),
            node("export", "export", dict(format="parquet"), "predict"),
        ]
    return DAGSpec(nodes).data()


def run(store, spec, tmp, **kw):
    work = tmp / "dagwork"
    work.mkdir(exist_ok=True)
    r = request_for(store, store.state, spec, tmp / "cache", **kw)
    return calculate(r, spec, work)


def test_ports_cycles_dry_run(tmp_path):
    store, r, _ = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [2.0, 4.0, 6.0, 8.0]})
    )
    with closing(store):
        spec = recipe(r)
        bad = copy.deepcopy(spec)
        bad["nodes"][0]["after"] = ["summary"]
        with pytest.raises(ProjectError, match="cycle"):
            DAGSpec.from_dict(bad)
        bad = copy.deepcopy(spec)
        bad["nodes"][1]["inputs"]["data"]["port"] = "model"
        with pytest.raises(ProjectError, match="port/type"):
            DAGSpec.from_dict(bad)
        value = run(store, spec, tmp_path, dry_run=True)
        assert value["status"] == "dry_run"
        assert all(n["status"] == "planned" for n in value["nodes"])
        assert not (tmp_path / "cache").exists()


def test_compute_cache_and_branch_failure(tmp_path):
    store, r, _ = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [2.0, None, 6.0, 8.0]})
    )
    with closing(store):
        spec = recipe(r)
        spec["nodes"].append(
            node("blocked", "analysis", dict(column=column(r, "x"), ddof=1), "quality")
        )
        first = run(store, spec, tmp_path)
        entries = {n["node"]: n for n in first["nodes"]}
        assert first["status"] == "partial"
        assert entries["quality"]["status"] == "failed"
        assert entries["blocked"]["status"] == "blocked"
        assert float(entries["summary"]["value"]["report"]["numeric"]["mean"]) == 2.5
        second = run(store, spec, tmp_path)
        assert (
            next(n for n in second["nodes"] if n["node"] == "summary")["status"]
            == "cached"
        )
        changed = copy.deepcopy(spec)
        changed["nodes"][1]["params"]["ddof"] = 0
        third = run(store, changed, tmp_path)
        assert (
            next(n for n in third["nodes"] if n["node"] == "summary")["status"]
            == "completed"
        )
        assert (
            next(n for n in third["nodes"] if n["node"] == "source")["status"]
            == "cached"
        )
        state = publish(store, store.state, third)
        loaded = load(store, state["results"][-1])
        assert loaded["status"] == "partial"
        assert state["datasets"] == store.state["datasets"]


def test_full_native_train_predict_export_and_idempotency(tmp_path):
    store, r, _ = prepare(
        tmp_path,
        pl.DataFrame(
            {"x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0], "y": [2.0, 4.1, 5.9, 8.0, 10.1, 11.9]}
        ),
    )
    out = tmp_path / "out"
    out.mkdir()
    with closing(store):
        spec = recipe(r, True)
        token = uid()
        first = run(
            store,
            spec,
            tmp_path,
            allow_export=True,
            output_dir=str(out),
            export_token=token,
        )
        assert first["status"] == "completed", first["nodes"]
        state = publish(store, store.state, first)
        full = load(store, state["results"][-1])
        assert full["export_receipts"][0]["status"] == "exported"
        file = next(out.glob("*.parquet"))
        exported = pl.read_parquet(file)
        assert exported.height == 6 and exported[
            "prediction"
        ].to_list() == pytest.approx([2.0, 4.0, 6.0, 8.0, 10.0, 12.0], abs=0.1)
        second = run(
            store,
            spec,
            tmp_path,
            allow_export=True,
            output_dir=str(out),
            export_token=token,
        )
        state = publish(store, state, second)
        assert (
            load(store, state["results"][-1])["export_receipts"][0]["status"]
            == "already_published"
        )
        file.write_bytes(b"owned by user now")
        third = run(
            store,
            spec,
            tmp_path,
            allow_export=True,
            output_dir=str(out),
            export_token=token,
        )
        state = publish(store, state, third)
        assert load(store, state["results"][-1])["status"] == "partial"
        assert file.read_bytes() == b"owned by user now"


def test_headless_shared_worker(tmp_path):
    store, r, _ = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [2.0, 4.0, 6.0, 8.0]})
    )
    with closing(store):
        spec = recipe(r)
        state = run_headless(store, spec, tmp_path / "cache")
        full = load(store, state["results"][-1])
        assert full["status"] == "completed"
        assert (
            float(
                next(n for n in full["nodes"] if n["node"] == "summary")["value"][
                    "report"
                ]["numeric"]["mean"]
            )
            == 2.5
        )


def test_source_mutation_rejects_cached_descendants(tmp_path):
    store, r, _ = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    )
    with closing(store):
        spec = recipe(r)
        run(store, spec, tmp_path)
        path = store.path(r["snapshot_uri"])
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"changed")
            result = run(store, spec, tmp_path)
            assert result["status"] == "partial"
            assert result["nodes"][0]["status"] == "failed"
            assert all(n["status"] == "blocked" for n in result["nodes"][1:])
            assert all(n.get("value") is None for n in result["nodes"])
        finally:
            path.write_bytes(original)


def test_corrupt_cache_recomputed_and_owned_temp_cleanup(tmp_path):
    from veri_ufku.importers.delimited import Control
    from veri_ufku.operations.workflow import Cache

    store, r, _ = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    )
    with closing(store):
        spec = recipe(r)
        first = run(store, spec, tmp_path)
        summary = next(n for n in first["nodes"] if n["node"] == "summary")
        directory = tmp_path / "cache" / "workflow-v1"
        (directory / summary["cache_key"] / "entry.json").write_text("{}")
        orphan = directory / ".tmp-dag-crashed"
        orphan.mkdir()
        (orphan / "partial").write_text("leftover")
        second = run(store, spec, tmp_path)
        current = next(n for n in second["nodes"] if n["node"] == "summary")
        assert current["status"] == "completed" and current["cache_invalidated"]
        assert not orphan.exists()
        owner = Cache(tmp_path / "cache", Control())
        try:
            with pytest.raises(ProjectError, match="başka runner"):
                Cache(tmp_path / "cache", Control())
        finally:
            owner.close()


def test_batch_dataset_mapping_sweep_and_native_ids(tmp_path):
    from veri_ufku.importers.delimited import Control, capture
    from veri_ufku.importers.native import StructuredSettings
    from veri_ufku.importers.registry import get_adapter

    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    )
    with closing(store):
        path = tmp_path / "other.parquet"
        pl.DataFrame({"x": [10.0, 20.0, 30.0], "y": [20.0, 40.0, 60.0]}).write_parquet(
            path
        )
        snapshot = capture(path, work, any_format=True)
        result = get_adapter("parquet").import_data(
            snapshot, StructuredSettings(adapter_id="parquet"), work, Control()
        )
        store.publish_import(result)
        d = store.state["datasets"][-1]
        mapping = {
            c["id"]: next(
                v["id"]
                for v in d["import_metadata"]["columns"]
                if v["name"] == c["name"]
            )
            for c in r["columns"]
        }
        spec = recipe(r)
        spec["cases"] = [
            dict(id="one", sources={}, columns={}),
            dict(
                id="two",
                sources=dict(source=d["version_id"]),
                columns=dict(source=mapping),
            ),
        ]
        spec["sweep"] = [dict(node="summary", parameter="ddof", values=[0, 1])]
        value = run(store, spec, tmp_path)
        assert value["status"] == "completed"
        means = {
            n["case"]: float(n["value"]["report"]["numeric"]["mean"])
            for n in value["nodes"]
            if n["node"] == "summary"
        }
        assert means == {"one-s0": 2.0, "one-s1": 2.0, "two-s0": 20.0, "two-s1": 20.0}
        state = publish(store, store.state, value)
        assert set(state["results"][-1]["dataset_version_ids"]) == {
            r["version_id"],
            d["version_id"],
        }
        assert load(store, state["results"][-1])["status"] == "completed"
        broken = copy.deepcopy(spec)
        broken["cases"][1]["columns"] = {}
        with pytest.raises(ProjectError, match="ColumnId"):
            run(store, broken, tmp_path)


def test_retry_pure_io_and_cancel_never_publishes_export(tmp_path, monkeypatch):
    import veri_ufku.operations.workflow as engine
    from veri_ufku.jobs.workers import Canceled

    store, r, _ = prepare(
        tmp_path,
        pl.DataFrame(
            {"x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0], "y": [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]}
        ),
    )
    out = tmp_path / "out"
    out.mkdir()
    original = engine.execute
    failures = []

    def execute(n, *args):
        if n["id"] == "summary" and not failures:
            failures.append(True)
            raise OSError("temporary")
        return original(n, *args)

    monkeypatch.setattr(engine, "execute", execute)
    with closing(store):
        spec = recipe(r)
        spec["retries"] = 1
        value = run(store, spec, tmp_path)
        assert value["status"] == "completed"
        assert (
            next(n for n in value["nodes"] if n["node"] == "summary")["attempts"] == 2
        )
        spec = recipe(r, True)
        value = run(store, spec, tmp_path, allow_export=True, output_dir=str(out))
        # Simulate cancellation after computation, before the parent publication barrier.
        value["status"] = "canceled"
        state = publish(store, store.state, value)
        assert not list(out.iterdir())
        assert load(store, state["results"][-1])["status"] == "canceled"
        assert not list((tmp_path / "dagwork").glob("dag-node-*"))

        def canceled(*args):
            raise Canceled()

        monkeypatch.setattr(engine, "execute", canceled)
        changed = copy.deepcopy(spec)
        changed["nodes"][0]["method_version"] = 2
        with pytest.raises(ProjectError):
            run(store, changed, tmp_path, allow_export=True, output_dir=str(out))


def test_transform_row_identity_and_artifact_corruption(tmp_path):
    ROW_ID, SOURCE_ID = "__vu_row_id", "__vu_source_record_id"

    store, r, _ = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [2.0, 4.0, 6.0, 8.0]})
    )
    with closing(store):
        spec = recipe(r)
        rename = node(
            "rename",
            "transform",
            dict(
                kind="rename", columns=[column(r, "x")], parameters=dict(name="renamed")
            ),
            "source",
        )
        spec["nodes"].insert(1, rename)
        spec["nodes"][2]["inputs"]["data"]["node"] = "rename"
        first = run(store, spec, tmp_path)
        transformed = next(n for n in first["nodes"] if n["node"] == "rename")
        path = __import__("pathlib").Path(transformed["value"]["request"]["path"])
        frame = pl.read_parquet(path)
        original = pl.read_parquet(r["path"])
        assert frame.select(ROW_ID, SOURCE_ID).equals(
            original.select(ROW_ID, SOURCE_ID)
        )
        assert "renamed" in frame.columns and "x" not in frame.columns
        path.write_bytes(b"corrupted")
        second = run(store, spec, tmp_path)
        entry = next(n for n in second["nodes"] if n["node"] == "rename")
        assert entry["cache_invalidated"] and entry["status"] == "completed"
        assert (
            pl.read_parquet(entry["value"]["request"]["path"])
            .select(ROW_ID, SOURCE_ID)
            .equals(original.select(ROW_ID, SOURCE_ID))
        )


def test_environment_and_schema_metadata_invalidate_cache(tmp_path, monkeypatch):
    import veri_ufku.operations.workflow as engine

    store, r, _ = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    )
    with closing(store):
        spec = recipe(r)
        first = run(store, spec, tmp_path)
        sig = engine.signature()
        sig["environment"]["test_fixture"] = "new-runtime"
        monkeypatch.setattr(engine, "signature", lambda: sig)
        second = run(store, spec, tmp_path)
        assert all(n["status"] == "completed" for n in second["nodes"])
        assert [n["cache_key"] for n in first["nodes"]] != [
            n["cache_key"] for n in second["nodes"]
        ]
        req = request_for(store, store.state, spec, tmp_path / "cache")
        root = req["workflow_sources"][r["version_id"]]
        root["semantic_metadata"][column(r, "x")] = dict(
            role="measurement", unit="", ordinal_order=[], confirmed=True
        )
        changed = calculate(req, spec, tmp_path / "dagwork")
        assert changed["nodes"][0]["status"] == "completed"


def test_batch_exports_unique_and_foreign_collision(tmp_path):
    store, r, _ = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    )
    out = tmp_path / "out"
    out.mkdir()
    with closing(store):
        spec = recipe(r)
        spec["nodes"].append(node("export", "export", dict(format="parquet"), "source"))
        spec["cases"] = [
            dict(id=k, sources={}, columns={}) for k in ("first", "second")
        ]
        token = uid()
        collision = out / (token + "-first-export.parquet")
        collision.write_bytes(b"other run or source")
        value = run(
            store,
            spec,
            tmp_path,
            allow_export=True,
            output_dir=str(out),
            export_token=token,
        )
        state = publish(store, store.state, value)
        full = load(store, state["results"][-1])
        assert full["status"] == "partial"
        assert collision.read_bytes() == b"other run or source"
        assert pl.read_parquet(out / (token + "-second-export.parquet")).height == 3
        assert (
            next(
                n
                for n in full["nodes"]
                if n["node"] == "summary" and n["case"] == "first"
            )["status"]
            == "completed"
        )


def test_budget_cancel_and_closed_methods(tmp_path):
    from dataclasses import replace
    from threading import Event

    from veri_ufku.domain.contracts import ComputeBudget
    from veri_ufku.importers.delimited import Control

    store, r, _ = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    )
    with closing(store):
        spec = recipe(r)
        request = request_for(store, store.state, spec, tmp_path / "cache")
        event = Event()
        event.set()
        result = calculate(request, spec, tmp_path / "work", Control(event))
        assert result["status"] == "canceled" and not result["nodes"]
        with pytest.raises(ProjectError, match="süre bütçesi"):
            calculate(
                request,
                spec,
                tmp_path / "work",
                Control(budget=replace(ComputeBudget(), max_wall_seconds=0.000001)),
            )
        for kind in ("sort", "python", "network"):
            bad = copy.deepcopy(spec)
            bad["nodes"][1]["kind"] = kind
            with pytest.raises(ProjectError):
                DAGSpec.from_dict(bad)
        from veri_ufku.domain.capabilities import availability, get_capability

        assert not availability(get_capability("workflow.schedule"))[0]


def test_ledger_publication_barrier_precedes_external_effect(tmp_path):
    store, r, _ = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    )
    out = tmp_path / "out"
    out.mkdir()
    with closing(store):
        spec = recipe(r)
        spec["nodes"].append(node("export", "export", dict(format="parquet"), "source"))
        value = run(store, spec, tmp_path, allow_export=True, output_dir=str(out))
        value["prior_test_use_ids"] = ["result:" + uid()]
        previous = copy.deepcopy(store.state)
        with pytest.raises(ProjectError, match="test geçmişi"):
            publish(store, store.state, value)
        assert not list(out.iterdir()) and store.state == previous
