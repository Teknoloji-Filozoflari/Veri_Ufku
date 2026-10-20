"""Independent replay, rollback, hostile JSON and delayed-label references."""

import copy
from contextlib import closing

import polars as pl
import pytest
from test_dataset import column, prepare
from test_operations import request_for

from veri_ufku.operations.contracts import build
from veri_ufku.operations.engine import calculate
from veri_ufku.operations.monitoring import compare, evaluate
from veri_ufku.operations.recipes import dry_run, export, publish, read
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def chain(tmp_path):
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"x": [1, 2, 3, None], "kind": ["a", "a", "b", "b"]})
    )
    renamed = store.publish_operation(
        calculate(
            request,
            build(request, "rename", [column(request, "x")], {"name": "amount"}),
            work,
        )
    )
    second = request_for(store, renamed)
    dropped = store.publish_operation(
        calculate(second, build(second, "drop", [column(second, "kind")]), work)
    )
    recipe = export(store.state, dropped["version_id"], store.manifest["artifacts"])
    # Target is the same source, reactivated without deleting recorded branch.
    store.state["workflow"]["heads"][renamed["dataset_id"]] = request["version_id"]
    store.save()
    mappings = {request["version_id"]: {c["id"]: c["id"] for c in request["columns"]}}
    return store, request, work, recipe, mappings


def test_recipe_roundtrip_deterministic_atomic_reopen(tmp_path):
    store, request, work, recipe, mappings = chain(tmp_path)
    with closing(store):
        from veri_ufku.modeling.lifecycle import raw_json

        path = tmp_path / "recipe.json"
        path.write_bytes(raw_json(recipe))
        assert read(path) == recipe
        previous, commit = copy.deepcopy(store.state), store.commit_id
        a = dry_run(recipe, {request["version_id"]: request}, mappings, work)
        b = dry_run(recipe, {request["version_id"]: request}, mappings, work)
        assert a["valid"] and b["valid"]
        assert store.state == previous and store.commit_id == commit
        assert [
            {k: v for k, v in s["impact"].items() if k != "input_populations"}
            for s in a["steps"]
        ] == [
            {k: v for k, v in s["impact"].items() if k != "input_populations"}
            for s in b["steps"]
        ]
        assert pl.read_parquet(a["results"][-1]["path"]).equals(
            pl.read_parquet(b["results"][-1]["path"])
        )
        state = publish(store, store.state, a)
        root = store.root
        assert store.commit_id != commit
        assert (
            state["datasets"][-1]["import_metadata"]["columns"][0]["name"] == "amount"
        )
        assert len(state["datasets"]) == len(previous["datasets"]) + 2
    with closing(ProjectStore.open(root)) as reopened:
        assert reopened.state == state
        assert pl.read_parquet(reopened.path(state["datasets"][-1]["snapshot_uri"]))[
            "amount"
        ].to_list() == [1, 2, 3, None]


@pytest.mark.parametrize(
    "point",
    [
        "operation_copy_chunk",
        "artifact_promoted",
        "metadata_committed",
        "manifest_promoted",
    ],
)
def test_atomic_batch_failure_keeps_project(tmp_path, point):
    store, r, w, recipe, mappings = chain(tmp_path)
    with closing(store):
        preview = dry_run(recipe, {r["version_id"]: r}, mappings, w)
        previous, commit = copy.deepcopy(store.state), store.commit_id
        count = 0

        def fail(p):
            nonlocal count
            if p == point:
                count += 1
                if point != "operation_copy_chunk" or count == 2:
                    raise OSError("injected")

        with pytest.raises(OSError):
            publish(store, store.state, preview, fail)
        assert store.state == previous and store.commit_id == commit
        with closing(ProjectStore.open(store.root, writable=False)) as reopened:
            assert reopened.state == previous


def test_missing_type_role_and_bad_last_step_dry_run(tmp_path):
    store, r, w, recipe, mappings = chain(tmp_path)
    with closing(store):
        previous = copy.deepcopy(store.state)
        missing = copy.deepcopy(mappings)
        missing[r["version_id"]].pop(column(r, "x"))
        out = dry_run(recipe, {r["version_id"]: r}, missing, w)
        assert not out["valid"] and "Eksik kolon" in out["errors"][0]
        wrong = copy.deepcopy(r)
        wrong["columns"][0]["type"] = "String"
        assert not dry_run(recipe, {r["version_id"]: wrong}, mappings, w)["valid"]
        role = copy.deepcopy(recipe)
        role["sources"][r["version_id"]]["semantic_metadata"] = {
            column(r, "x"): {
                "role": "measurement",
                "unit": "",
                "ordinal_order": [],
                "confirmed": True,
            }
        }
        assert not dry_run(role, {r["version_id"]: r}, mappings, w)["valid"]
        bad = copy.deepcopy(recipe)
        bad["steps"][-1]["spec"]["parameters"] = {
            "code": "__import__('os').system('false')"
        }
        out = dry_run(bad, {r["version_id"]: r}, mappings, w)
        assert not out["valid"] and out["steps"][-1]["status"] == "failed"
        with pytest.raises(ProjectError):
            publish(store, store.state, out)
        assert store.state == previous


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema":"AnalysisRecipe/v1","schema":"x"}',
        b'{"seed":NaN}',
        b'{"schema":"Python","code":"pass"}',
    ],
)
def test_hostile_recipe_rejected(tmp_path, raw):
    path = tmp_path / "hostile.json"
    path.write_bytes(raw)
    with pytest.raises(ProjectError):
        read(path)


def test_full_drift_and_no_target_metrics(tmp_path):
    store, r, w = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0, None], "c": ["a", "a", "b", None]})
    )
    with closing(store):
        mapping = {c["id"]: c["id"] for c in r["columns"]}
        out = compare(r, r, mapping)
        assert out["metrics"] is None
        x = out["columns"][0]["before"]
        assert (
            x["missing_rate"] == 0.25
            and x["mean"] == 2
            and x["q25"] == 1.5
            and x["q75"] == 2.5
        )
        c = out["columns"][1]["before"]
        assert {v["value"]: v["rate"] for v in c["categories"]} == {"a": 0.5, "b": 0.25}
        assert out["old_version"] == r["version_id"] and out["scope"] == "full"
        out = compare(r, r, {column(r, "x"): column(r, "x")})
        assert [x["schema_change"] for x in out["columns"]] == [
            "same",
            "removed/unmapped",
            "added/unmapped",
        ]


def test_delayed_targets_keyed_reference_no_fabrication():
    predictions = pl.DataFrame({"id": ["a", "b", "c", "d"], "p": [1.0, 4.0, None, 5.0]})
    targets = pl.DataFrame({"key": ["b", "a", "c", "e"], "y": [2.0, 2.0, 3.0, 7.0]})
    out = evaluate(predictions, targets, "id", "key", "p", "y", "regression")
    assert out["metrics"]["mae"] == 1.5
    assert out["metrics"]["rmse"] == pytest.approx(2.5**0.5)
    assert (
        out["matched"],
        out["scored"],
        out["invalid"],
        out["unmatched_predictions"],
        out["unmatched_targets"],
    ) == (3, 2, 1, 1, 1)
    empty = targets.filter(pl.col("key") == "e")
    assert (
        evaluate(predictions, empty, "id", "key", "p", "y", "regression")["metrics"]
        is None
    )
    with pytest.raises(ProjectError):
        evaluate(
            predictions,
            pl.concat([targets, targets.head(1)]),
            "id",
            "key",
            "p",
            "y",
            "regression",
        )


def test_computed_and_literal_remapping_new_dataset(tmp_path):
    from test_relational import add_source, out

    store, r, w = prepare(tmp_path, pl.DataFrame({"x": [1, 2], "c": ["a", "b"]}))
    with closing(store):
        x = column(r, "x")
        spec = build(
            r,
            "computed",
            [x],
            dict(
                expression=f'col("{x}") * 2',
                target={"kind": "Int64"},
                output=out("double"),
                zero_policy="reject",
            ),
        )
        d = store.publish_operation(calculate(r, spec, w))
        recipe = export(store.state, d["version_id"], store.manifest["artifacts"])
        new = add_source(store, w, pl.DataFrame({"x": [10, 20], "c": ["a", "b"]}))
        mapping = {
            r["version_id"]: {c["id"]: column(new, c["name"]) for c in r["columns"]}
        }
        preview = dry_run(recipe, {r["version_id"]: new}, mapping, w)
        assert preview["valid"], preview["errors"]
        assert pl.read_parquet(preview["results"][-1]["path"])["double"].to_list() == [
            20,
            40,
        ]
        publish(store, store.state, preview)
        from veri_ufku.operations.recipes import parameters_for

        original = {"kind": "fill", "parameters": {"value": x}}
        assert parameters_for(original, {x: column(new, "x")}, [])["value"] == x


def test_two_source_join_recipe_new_identities_lineage_atomic(tmp_path):
    from test_relational import add_source, join_params

    store, r, w = prepare(tmp_path, pl.DataFrame({"key": [1, 2], "x": [10, 20]}))
    with closing(store):
        other = add_source(store, w, pl.DataFrame({"key": [1, 2], "label": ["a", "b"]}))
        request = dict(r, secondary=other)
        d = store.publish_operation(
            calculate(
                request,
                build(request, "join", [column(r, "key")], join_params(r, other)),
                w,
            )
        )
        recipe = export(store.state, d["version_id"], store.manifest["artifacts"])
        new_left = add_source(store, w, pl.DataFrame({"key": [2, 3], "x": [200, 300]}))
        new_right = add_source(
            store, w, pl.DataFrame({"key": [2, 3], "label": ["c", "d"]})
        )
        sources = {r["version_id"]: new_left, other["version_id"]: new_right}
        mappings = {
            k: {
                c["id"]: column(sources[k], c["name"])
                for c in recipe["sources"][k]["columns"]
            }
            for k in sources
        }
        preview = dry_run(recipe, sources, mappings, w)
        assert preview["valid"], preview["errors"]
        state = publish(store, store.state, preview)
        output = pl.read_parquet(store.path(state["datasets"][-1]["snapshot_uri"]))
        assert output["x"].to_list() == [200, 300] and output[
            "label_right"
        ].to_list() == ["c", "d"]
        assert state["datasets"][-1]["lineage_uri"]


def test_monitoring_exact_integer_decimal_precision():
    from decimal import Decimal

    from veri_ufku.operations.monitoring import summary

    result = summary(pl.Series([2**60, 2**60 + 2], dtype=pl.Int64))
    assert result["mean"] == str(2**60 + 1)
    result = summary(
        pl.Series(
            [Decimal("1.000000000000000001"), Decimal("1.000000000000000003")],
            dtype=pl.Decimal(38, 18),
        )
    )
    assert Decimal(result["median"]) == Decimal("1.000000000000000002")


def test_source_scoped_column_ids_for_forked_join(tmp_path):
    from test_relational import add_source, join_params

    store, r, w = prepare(tmp_path, pl.DataFrame({"key": [1, 2], "x": [10, 20]}))
    with closing(store):
        fork = store.publish_operation(
            calculate(
                r, build(r, "rename", [column(r, "x")], {"name": "other_x"}, "copy"), w
            )
        )
        other = request_for(store, fork)
        assert column(r, "key") == column(other, "key")
        request = dict(r, secondary=other)
        d = store.publish_operation(
            calculate(
                request,
                build(request, "join", [column(r, "key")], join_params(r, other)),
                w,
            )
        )
        recipe = export(store.state, d["version_id"], store.manifest["artifacts"])
        # Export includes fork's rename, whose input is the same original root.
        # A repeated ColumnId in independent source contracts must remain scoped.
        recipe["steps"] = [recipe["steps"][-1]]
        recipe["sources"][other["version_id"]] = dict(
            columns=other["columns"],
            semantic_metadata={},
            fingerprint=other["fingerprint"],
        )
        new_left = add_source(store, w, pl.DataFrame({"key": [3], "x": [100]}))
        new_right = add_source(store, w, pl.DataFrame({"key": [3], "other_x": [200]}))
        sources = {r["version_id"]: new_left, other["version_id"]: new_right}
        mappings = {
            k: {
                c["id"]: column(sources[k], c["name"])
                for c in recipe["sources"][k]["columns"]
            }
            for k in sources
        }
        preview = dry_run(recipe, sources, mappings, w)
        assert preview["valid"], preview["errors"]
        assert pl.read_parquet(preview["results"][-1]["path"])[
            "other_x_right"
        ].to_list() == [200]


@pytest.mark.parametrize(
    "point", ["operation_copy_chunk", "metadata_committed", "pointer_replaced"]
)
def test_real_sigkill_batch_recovery(tmp_path, point):
    import signal
    import subprocess
    import sys

    from veri_ufku.storage.project_model import encode

    store, r, w, recipe, mappings = chain(tmp_path)
    preview = dry_run(recipe, {r["version_id"]: r}, mappings, w)
    previous = copy.deepcopy(store.state)
    root = store.root
    path = tmp_path / "preview.json"
    path.write_bytes(encode(preview))
    store.close()
    code = """
import os, signal, sys
from pathlib import Path
from veri_ufku.storage.project_model import decode
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.operations.recipes import publish
store=ProjectStore.open(sys.argv[1])
count=0
def checkpoint(point):
    global count
    if point==sys.argv[3]:
        count+=1
        if point!="operation_copy_chunk" or count==2:
            os.kill(os.getpid(),signal.SIGKILL)
publish(store,store.state,decode(Path(sys.argv[2]).read_bytes()),checkpoint)
"""
    child = subprocess.run(
        [sys.executable, "-c", code, str(root), str(path), point],
        capture_output=True,
        timeout=20,
    )
    assert child.returncode == -signal.SIGKILL, child.stderr
    with closing(ProjectStore.open(root, recover_lock=True)) as recovered:
        if point == "pointer_replaced":
            assert len(recovered.state["datasets"]) == len(previous["datasets"]) + 2
            assert (
                recovered.state["datasets"][-1]["version_id"]
                == preview["results"][-1]["version_id"]
            )
        else:
            assert recovered.state == previous
        assert list(recovered.path("staging").iterdir()) == []
        with closing(ProjectStore.open(root)) as second:
            assert second.read_only


def test_physical_type_alias_compatible_and_unknown_method_rejected(tmp_path):
    store, r, w, recipe, mappings = chain(tmp_path)
    with closing(store):
        recipe["sources"][r["version_id"]]["columns"][0]["type"] = "int64"
        preview = dry_run(recipe, {r["version_id"]: r}, mappings, w)
        assert preview["valid"], preview["errors"]
        recipe["steps"][0]["spec"]["method_version"] = 2
        from veri_ufku.modeling.lifecycle import raw_json

        path = tmp_path / "unsupported.json"
        path.write_bytes(raw_json(recipe))
        with pytest.raises(ProjectError):
            read(path)


def test_delayed_classification_reordered_and_invalid_targets():
    predictions = pl.DataFrame({"id": [1, 2, 3], "p": ["a", "b", None]})
    targets = pl.DataFrame({"key": [3, 2, 1], "y": ["a", "a", "a"]})
    report = evaluate(predictions, targets, "id", "key", "p", "y", "classification")
    assert report["scored"] == 2 and report["metrics"] == {"accuracy": 0.5}
    with pytest.raises(ProjectError):
        evaluate(predictions, targets, "id", "key", "p", "missing", "classification")
