"""Independent expected values, stable duplicate identity and atomic history roundtrips."""

import copy
import threading
from contextlib import closing
from decimal import Decimal

import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import page
from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.jobs.workers import Canceled
from veri_ufku.operations.contracts import (
    LINEAGE,
    OperationSpec,
    active_datasets,
    build,
    heads,
    move,
)
from veri_ufku.operations.engine import calculate
from veri_ufku.storage.project_model import ProjectError, uid, validate_state
from veri_ufku.storage.project_store import ProjectStore


def request_for(store, d):
    return dict(
        path=str(store.path(d["snapshot_uri"])),
        fingerprint=hash_artifact(store.path(d["snapshot_uri"]), Control()),
        columns=d["import_metadata"]["columns"],
        row_count=d["import_metadata"]["row_count"],
        version_id=d["version_id"],
        source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
    )


def test_operations_values_identity_branch_redo_reopen_and_stale_results(tmp_path):
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"value": [1, 2, 2, 3, None], "code": ["001"] * 5})
    )
    source = (tmp_path / "source.parquet").read_bytes()
    original = pl.read_parquet(request["path"])
    root = store.root
    with closing(store):
        col = column(request, "value")
        preview = calculate(
            request, build(request, "rename", [col], {"name": "amount"}), work
        )
        assert preview["impact"]["changed_columns"] == 1
        assert preview["before"]["row_ids"] == preview["after"]["row_ids"]
        assert store.state["datasets"][-1]["version_id"] == request["version_id"]
        renamed = store.publish_operation(preview)
        renamed_frame = pl.read_parquet(store.path(renamed["snapshot_uri"]))
        assert renamed_frame["amount"].to_list() == [1, 2, 2, 3, None]
        assert (
            renamed_frame["__vu_row_id"].to_list() == original["__vu_row_id"].to_list()
        )
        # A result stays on its original version; no automatic retargeting.
        store.state["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=[renamed["version_id"]],
                seed=None,
            )
        )
        request2 = request_for(store, renamed)
        filters = [
            dict(
                column_id=col,
                operator="eq",
                literal={"dtype": request2["columns"][0]["type"], "text": "2"},
            )
        ]
        result = calculate(
            request2, build(request2, "filter", [col], {"filters": filters}), work
        )
        assert (
            result["impact"]["scope"] == "full"
            and result["impact"]["removed_rows"] == 3
        )
        filtered = store.publish_operation(result)
        filtered_frame = pl.read_parquet(store.path(filtered["snapshot_uri"]))
        assert filtered_frame["amount"].to_list() == [2, 2]
        assert (
            filtered_frame["__vu_row_id"].to_list()
            == original["__vu_row_id"].to_list()[1:3]
        )
        assert filtered_frame["__vu_row_id"][0] != filtered_frame["__vu_row_id"][1]
        assert not store.results_status()[0]["current"]
        move(store.state, renamed["dataset_id"], "undo")
        assert active_datasets(store.state)[0] == renamed
        assert pl.read_parquet(
            store.path(active_datasets(store.state)[0]["snapshot_uri"])
        ).equals(renamed_frame)
        assert store.results_status()[0]["current"]
        move(store.state, renamed["dataset_id"], "redo")
        assert pl.read_parquet(
            store.path(active_datasets(store.state)[0]["snapshot_uri"])
        ).equals(filtered_frame)
        move(store.state, renamed["dataset_id"], "undo")
        # New drop branch keeps the old filtered snapshot and clears redo only.
        req = request_for(store, renamed)
        drop = calculate(req, build(req, "drop", [column(req, "code")]), work)
        dropped = store.publish_operation(drop)
        assert dropped["import_metadata"]["columns"][0]["id"] == col
        assert (
            pl.read_parquet(store.path(dropped["snapshot_uri"]))[
                "__vu_row_id"
            ].to_list()
            == original["__vu_row_id"].to_list()
        )
        with pytest.raises(ProjectError):
            move(store.state, renamed["dataset_id"], "redo")
        assert filtered in store.state["datasets"]
        assert store.state["results"][0]["dataset_version_ids"] == [
            renamed["version_id"]
        ]
        state = copy.deepcopy(store.state)
    with closing(ProjectStore.open(root)) as reopened:
        assert reopened.state == state
        assert active_datasets(reopened.state)[0] == dropped
        assert pl.read_parquet(reopened.path(filtered["snapshot_uri"])).equals(
            filtered_frame
        )
    assert (tmp_path / "source.parquet").read_bytes() == source


@pytest.mark.parametrize(
    "checkpoint",
    [
        "operation_copy_chunk",
        "artifact_promoted",
        "metadata_committed",
        "manifest_promoted",
        "pointer_fsynced",
    ],
)
def test_failed_publication_keeps_active_dataset(tmp_path, checkpoint):
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    )
    with closing(store):
        before, commit = copy.deepcopy(store.state), store.commit_id
        result = calculate(
            request, build(request, "drop", [column(request, "b")]), work
        )

        def fault(point):
            if point == checkpoint:
                raise OSError("injected failure")

        with pytest.raises(OSError):
            store.publish_operation(result, checkpoint=fault)
        assert store.state == before and store.commit_id == commit
        other = ProjectStore.open(store.root)
        try:
            assert other.state == before
        finally:
            other.close()
        # A retry publishes a whole new version, never a partial frame.
        store.publish_operation(result)
        assert pl.read_parquet(
            store.path(active_datasets(store.state)[0]["snapshot_uri"])
        )["a"].to_list() == [1, 2]


def test_invalid_canceled_stale_and_tampered_output_leave_no_result(tmp_path):
    store, request, work = prepare(tmp_path, pl.DataFrame({"a": [1, 2], "b": [3, 4]}))
    with closing(store):
        before = copy.deepcopy(store.state)
        for kind, cols, params in [
            ("rename", [column(request, "a")], {"name": "b"}),
            ("drop", [c["id"] for c in request["columns"]], {}),
            ("join", [], {}),
        ]:
            with pytest.raises(ProjectError):
                build(request, kind, cols, params)
        spec = build(request, "rename", [column(request, "a")], {"name": "z"})
        bad = spec.data()
        bad["method_version"] = True
        with pytest.raises(ProjectError):
            OperationSpec.from_dict(bad)
        event = threading.Event()
        event.set()
        with pytest.raises(Canceled):
            calculate(request, spec, work, Control(event))
        assert store.state == before
        result = calculate(request, spec, work)
        pl.DataFrame({"bad": [1]}).write_parquet(result["path"])
        with pytest.raises(ProjectError):
            store.publish_operation(result)
        assert store.state == before
        result = calculate(request, spec, work)
        store.publish_operation(result)
        with pytest.raises(ProjectError):
            store.publish_operation(calculate(request, spec, work))
        state = copy.deepcopy(store.state)
        state["workflow"]["heads"][request["version_id"]] = "missing"
        with pytest.raises(ProjectError):
            validate_state(state)


def test_sorted_filtered_preview_exact_duplicate_membership_and_decimal(tmp_path):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {"a": [Decimal("2.10"), Decimal("1.05"), Decimal("2.10")], "tag": ["x"] * 3}
        ),
    )
    with closing(store):
        col = column(request, "a")
        view = ViewSpec(
            filters=({"column_id": col, "operator": "ge", "value": "2.10"},),
            sort_column=col,
            descending=True,
        )
        shown = page(request, view)
        spec = build(
            request,
            "filter",
            [col],
            {
                "filters": [
                    dict(
                        column_id=col,
                        operator="ge",
                        literal={
                            "dtype": request["columns"][0]["type"],
                            "text": "2.10",
                        },
                    )
                ]
            },
        )
        result = calculate(request, spec, work)
        d = store.publish_operation(result)
        frame = pl.read_parquet(store.path(d["snapshot_uri"]))
        assert frame["a"].to_list() == [Decimal("2.10"), Decimal("2.10")]
        assert frame["__vu_row_id"].to_list() == shown["row_ids"]
        assert set(LINEAGE) >= {
            "filter",
            "sort",
            "join",
            "explode",
            "aggregate",
            "dedup",
        }
        assert heads(store.state)[d["dataset_id"]] == d["version_id"]


@pytest.mark.parametrize(
    "point",
    [
        "operation_copy_chunk",
        "artifact_promoted",
        "metadata_committed",
        "pointer_fsynced",
        "pointer_replaced",
    ],
)
def test_real_sigkill_operation_recovery(tmp_path, point):
    import signal
    import subprocess
    import sys

    from veri_ufku.storage.project_model import encode

    store, request, work = prepare(
        tmp_path, pl.DataFrame({"a": [1, 2], "b": ["x", "x"]})
    )
    result = calculate(request, build(request, "drop", [column(request, "b")]), work)
    recipe = tmp_path / "result.json"
    recipe.write_bytes(encode(result))
    path = store.root
    old = copy.deepcopy(store.state)
    store.close()
    code = """
import os, signal, sys
from pathlib import Path
from veri_ufku.storage.project_model import decode
from veri_ufku.storage.project_store import ProjectStore
store = ProjectStore.open(sys.argv[1])
def checkpoint(point):
    if point == sys.argv[3]:
        os.kill(os.getpid(), signal.SIGKILL)
store.publish_operation(decode(Path(sys.argv[2]).read_bytes()), checkpoint=checkpoint)
"""
    child = subprocess.run(
        [sys.executable, "-c", code, str(path), str(recipe), point],
        capture_output=True,
        timeout=20,
    )
    assert child.returncode == -signal.SIGKILL, child.stderr
    with closing(ProjectStore.open(path, recover_lock=True)) as recovered:
        if point == "pointer_replaced":
            assert (
                active_datasets(recovered.state)[0]["version_id"]
                == result["version_id"]
            )
        else:
            assert recovered.state == old
        assert pl.read_parquet(recovered.path(old["datasets"][0]["snapshot_uri"]))[
            "a"
        ].to_list() == [1, 2]
        assert list(recovered.path("staging").iterdir()) == []


def test_future_lineage_contracts_are_typed_and_not_executable():
    from veri_ufku.operations.contracts import RowLineageSpec

    versions = ("dv:" + uid(), "dv:" + uid())
    for kind, policy, representation in [
        ("sort", "preserve", "ordered_output_rowids"),
        ("join", "new_per_match_occurrence", "parquet_left_right_occurrence"),
        ("explode", "new_per_item_occurrence", "parquet_parent_path_occurrence"),
        ("aggregate", "new_per_group", "lazy_immutable_membership"),
        ("dedup", "retain_stable_survivor", "parquet_duplicate_groups"),
    ]:
        inputs = versions if kind == "join" else versions[:1]
        assert (
            RowLineageSpec(kind, inputs, policy, representation).validate().kind == kind
        )
        with pytest.raises(ProjectError):
            RowLineageSpec(kind, inputs, "content_hash", representation).validate()
