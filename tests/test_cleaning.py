"""Independent small references for cleaning precision, time, lineage and undo."""

import copy
from contextlib import closing
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest
from test_dataset import column, prepare
from test_operations import request_for

from veri_ufku.operations.cleaning import exact_value
from veri_ufku.operations.cleaning_contracts import defaults
from veri_ufku.operations.contracts import active_datasets, build, heads, move
from veri_ufku.operations.engine import calculate
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def run(store, work, name, kind, params=None, destination="chain"):
    dataset = active_datasets(store.state)[-1]
    request = request_for(store, dataset)
    cols = [column(request, n) for n in ([name] if isinstance(name, str) else name)]
    parameters = defaults(kind)
    if params:
        parameters.update(params)
    result = calculate(
        request, build(request, kind, cols, parameters, destination), work
    )
    old = pl.read_parquet(request["path"])
    d = store.publish_operation(result)
    return result, d, old, pl.read_parquet(store.path(d["snapshot_uri"]))


def test_missing_rows_columns_and_null_nan_are_explicit(tmp_path):
    store, req, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "a": [1.0, None, float("nan"), None],
                "b": [None, None, None, None],
                "keep": [1, 2, 3, 4],
            }
        ),
    )
    with closing(store):
        result, d, before, after = run(
            store, work, "a", "missing_rows", {"rule": "any"}
        )
        assert result["impact"]["removed_rows"] == 2
        assert after["keep"].to_list() == [1, 3]  # NaN is not null.
        move(store.state, d["dataset_id"], "undo")
        result, d, _, after = run(
            store, work, "a", "missing_rows", {"rule": "any", "missing": "null_nan"}
        )
        assert after["keep"].to_list() == [1]
        move(store.state, d["dataset_id"], "undo")
        result, d, _, after = run(store, work, ["a", "b"], "missing_columns")
        assert after.columns == [n for n in before.columns if n != "b"]
        assert result["impact"]["removed_columns"] == 1
        move(store.state, d["dataset_id"], "undo")


@pytest.mark.parametrize(
    "method,expected",
    [("constant", [1, 2, 6, 4]), ("mean", [1, 2, 6, 3]), ("median", [1, 2, 6, 2])],
)
def test_fill_hand_values_counts_and_undo(tmp_path, method, expected):
    store, req, work = prepare(
        tmp_path, pl.DataFrame({"v": [1, 2, 6, None], "id": ["a", "b", "c", "d"]})
    )
    with closing(store):
        source = Path(req["path"]).read_bytes()
        result, d, before, after = run(
            store, work, "v", "fill", {"method": method, "value": "4"}
        )
        assert after["v"].to_list() == expected
        assert (
            result["impact"]["changed_cells"] == 1
            and result["impact"]["new_nulls"] == 0
        )
        assert result["spec"]["learned_scope"] == (
            "none" if method == "constant" else "dataset"
        )
        assert after["__vu_row_id"].to_list() == before["__vu_row_id"].to_list()
        move(store.state, d["dataset_id"], "undo")
        assert pl.read_parquet(
            store.path(active_datasets(store.state)[0]["snapshot_uri"])
        ).equals(before)
        move(store.state, d["dataset_id"], "redo")
        store.save()
        assert pl.read_parquet(store.path(d["snapshot_uri"])).equals(after)
        assert Path(req["path"]).read_bytes() == source


def test_all_missing_fractional_fill_mode_ties_and_zero_variance(tmp_path):
    store, req, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "all": pl.Series([None] * 5, dtype=pl.Int64),
                "tie": ["x", "y", "x", "y", None],
                "fraction": pl.Series([1, 2, None, None, None], dtype=pl.Int64),
                "fixed": [3, 3, 3, 3, None],
            }
        ),
    )
    with closing(store):
        before = copy.deepcopy(store.state)
        for col, method in [
            ("all", "mean"),
            ("all", "median"),
            ("all", "mode"),
            ("fraction", "mean"),
            ("tie", "mode"),
        ]:
            with pytest.raises(ProjectError):
                run(store, work, col, "fill", {"method": method})
            assert store.state == before
        r, d, _, f = run(
            store,
            work,
            "tie",
            "fill",
            {"method": "mode", "tie_policy": "choose", "value": "y"},
        )
        assert f["tie"].to_list() == ["x", "y", "x", "y", "y"]
        move(store.state, d["dataset_id"], "undo")
        r, d, _, f = run(store, work, "fixed", "fill", {"method": "mean"})
        assert f["fixed"].to_list() == [3] * 5
        move(store.state, d["dataset_id"], "undo")
        r, d, _, f = run(store, work, "all", "fill", {"value": "8"})
        assert f["all"].to_list() == [8] * 5


def test_text_trim_safe_exact_mapping_and_copy_dataset(tmp_path):
    store, req, work = prepare(
        tmp_path,
        pl.DataFrame(
            {"city": [" Ankara ", "Ankara", "İzmir ", None], "v": [1, 2, 3, 4]}
        ),
    )
    root = store.root
    with closing(store):
        original_dataset = active_datasets(store.state)[0]
        r, d, before, f = run(store, work, "city", "trim", destination="copy")
        assert r["impact"]["changed_cells"] == 2 and f["city"].to_list() == [
            "Ankara",
            "Ankara",
            "İzmir",
            None,
        ]
        assert d["dataset_id"] != original_dataset["dataset_id"]
        assert (
            heads(store.state)[original_dataset["dataset_id"]]
            == original_dataset["version_id"]
        )
        move(store.state, d["dataset_id"], "undo")
        assert pl.read_parquet(
            store.path(
                next(
                    v
                    for v in active_datasets(store.state)
                    if v["dataset_id"] == d["dataset_id"]
                )["snapshot_uri"]
            )
        ).equals(before)
        move(store.state, d["dataset_id"], "redo")
        r, d, _, f = run(
            store,
            work,
            "city",
            "map_categories",
            {
                "mapping": [
                    {"from": "Ankara", "to": "Ank"},
                    {"from": "İzmir", "to": "İZMİR"},
                ]
            },
        )
        assert f["city"].to_list() == ["Ank", "Ank", "İZMİR", None]
        assert r["impact"]["changed_cells"] == 3
        state = copy.deepcopy(store.state)
    with closing(ProjectStore.open(root)) as reopened:
        assert reopened.state == state


@pytest.mark.parametrize(
    "direction,expected",
    [
        ("forward", [None, 10, 10, None, 20, 20]),
        ("backward", [10, 10, None, 20, 20, None]),
    ],
)
def test_ordered_fill_never_crosses_groups_even_interleaved(
    tmp_path, direction, expected
):
    store, req, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "group": ["A", "A", "A", "B", "B", "B"],
                "time": [1, 2, 3, 1, 2, 3],
                "v": pl.Series([None, 10, None, None, 20, None], dtype=pl.Int64),
            }
        ),
    )
    with closing(store):
        r, d, old, f = run(
            store,
            work,
            "v",
            "ordered_fill",
            {
                "direction": direction,
                "order_columns": [column(req, "time")],
                "group_columns": [column(req, "group")],
            },
        )
        assert f["v"].to_list() == expected
        assert f["__vu_row_id"].to_list() == old["__vu_row_id"].to_list()
        assert r["impact"]["changed_cells"] == 2 and r["diagnostics"]["unfilled"] == 2
        assert r["diagnostics"]["warnings"]


@pytest.mark.parametrize(
    "keep,expected_ids", [("first", [2, 3, 4]), ("last", [1, 3, 4])]
)
def test_dedup_order_equality_and_all_member_lineage(tmp_path, keep, expected_ids):
    store, req, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "order": [3, 1, 2, 4],
                "a": [1.0, 1.0, float("nan"), None],
                "b": ["x", "x", "n", "n"],
                "record": [1, 2, 3, 4],
            }
        ),
    )
    with closing(store):
        r, d, old, f = run(
            store,
            work,
            ["a", "b"],
            "dedup",
            {"keep": keep, "order_columns": [column(req, "order")]},
        )
        assert f["record"].to_list() == expected_ids
        assert r["impact"]["removed_rows"] == 1
        relation = pl.read_parquet(store.path(d["lineage_uri"]))
        assert relation.height == 4 and relation["retained"].sum() == 3
        assert set(relation["row_id"]) == set(old["__vu_row_id"])
        members = relation.filter(
            pl.col("row_id").is_in(old["__vu_row_id"].to_list()[:2])
        )
        assert members["survivor_row_id"].n_unique() == 1
        assert members["group_id"].n_unique() == 1
        move(store.state, d["dataset_id"], "undo")
        assert pl.read_parquet(
            store.path(active_datasets(store.state)[0]["snapshot_uri"])
        ).equals(old)


def test_decimal_date_parse_dst_policies_and_new_null_reporting(tmp_path):
    store, req, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "money": ["1.25", "1.234", "bad", None],
                "day": ["2024-02-29", "2024-02-30", "not date", None],
                "local": [
                    "2024-11-03T01:30:00",
                    "2024-03-10T02:30:00",
                    "2024-11-03T03:30:00",
                    None,
                ],
            }
        ),
    )
    with closing(store):
        state = copy.deepcopy(store.state)
        with pytest.raises(ProjectError):
            run(
                store,
                work,
                "money",
                "convert",
                {"target": {"kind": "Decimal", "precision": 10, "scale": 2}},
            )
        assert store.state == state
        r, d, _, f = run(
            store,
            work,
            "money",
            "convert",
            {
                "target": {"kind": "Decimal", "precision": 10, "scale": 2},
                "on_error": "null",
            },
        )
        assert f["money"].to_list() == [Decimal("1.25"), None, None, None]
        assert r["impact"]["new_nulls"] == r["impact"]["parse_errors"] == 2
        assert len(r["diagnostics"]["examples"]) == 2
        move(store.state, d["dataset_id"], "undo")
        r, d, _, f = run(
            store,
            work,
            "day",
            "convert",
            {"target": {"kind": "Date"}, "date_format": "%Y-%m-%d", "on_error": "null"},
        )
        assert str(f["day"][0]) == "2024-02-29" and r["impact"]["parse_errors"] == 2
        move(store.state, d["dataset_id"], "undo")
        target = {"kind": "Datetime", "unit": "us", "zone": "America/New_York"}
        r, d, _, f = run(
            store, work, "local", "convert", {"target": target, "on_error": "null"}
        )
        assert (
            f["local"][0] is None
            and f["local"][1] is None
            and r["impact"]["new_nulls"] == 2
        )
        move(store.state, d["dataset_id"], "undo")
        r, d, _, f = run(
            store,
            work,
            "local",
            "convert",
            {"target": target, "on_error": "null", "dst_policy": "latest"},
        )
        assert f["local"][0].astimezone(UTC) == datetime(2024, 11, 3, 6, 30, tzinfo=UTC)
        assert f["local"][1] is None and r["impact"]["new_nulls"] == 1


@pytest.mark.parametrize(
    "value,target",
    [
        ("9007199254740993", pl.Float64),
        ("1.5", pl.Int64),
        ("1.234", pl.Decimal(8, 2)),
        ("0.1", pl.Float64),
        ("2024-02-30", pl.Date),
    ],
)
def test_no_silent_precision_or_date_correction(value, target):
    with pytest.raises(ProjectError):
        exact_value(value, target)


def test_iqr_mark_is_default_zero_iqr_and_explicit_filter(tmp_path):
    store, req, work = prepare(
        tmp_path,
        pl.DataFrame({"v": [1, 2, 3, 4, 100], "id": ["a", "b", "c", "d", "e"]}),
    )
    with closing(store):
        r, d, old, f = run(store, work, "v", "outlier")
        assert f.height == 5 and f["Aykırı_adayı"].to_list() == [False] * 4 + [True]
        assert (
            r["impact"]["outlier_candidates"] == 1 and r["impact"]["removed_rows"] == 0
        )
        assert f["__vu_row_id"].to_list() == old["__vu_row_id"].to_list()
        move(store.state, d["dataset_id"], "undo")
        r, d, _, f = run(store, work, "v", "outlier", {"action": "filter"})
        assert f["v"].to_list() == [1, 2, 3, 4] and r["impact"]["removed_rows"] == 1


def test_dedup_nan_null_signed_zero_and_ns_precision(tmp_path):
    store, req, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "order": [1, 2, 3, 4, 5, 6],
                "a": [None, None, float("nan"), float("nan"), 0.0, -0.0],
            }
        ),
    )
    with closing(store):
        r, d, old, f = run(
            store, work, "a", "dedup", {"order_columns": [column(req, "order")]}
        )
        assert f["order"].to_list() == [1, 3, 5]
        assert r["impact"]["removed_rows"] == 3
    base = tmp_path / "ns"
    base.mkdir()
    frame = pl.DataFrame(
        {
            "order": [1, 2, 3],
            "t": pl.Series([1001, 1002, 1001], dtype=pl.Datetime("ns")),
        }
    )
    store, req, work = prepare(base, frame)
    with closing(store):
        r, d, _, f = run(
            store, work, "t", "dedup", {"order_columns": [column(req, "order")]}
        )
        assert f["order"].to_list() == [1, 2]
        assert f["t"].cast(pl.Int64).to_list() == [1001, 1002]
        with pytest.raises(ProjectError):
            run(store, work, "t", "fill", {"value": "2024-01-01"})


def test_iqr_zero_spread_and_rare_tail_defined(tmp_path):
    store, req, work = prepare(
        tmp_path, pl.DataFrame({"constant": [3] * 5, "rare": [1, 1, 1, 1, 100]})
    )
    with closing(store):
        r, d, _, f = run(store, work, "constant", "outlier")
        assert r["impact"]["outlier_candidates"] == 0
        move(store.state, d["dataset_id"], "undo")
        r, d, _, f = run(store, work, "rare", "outlier")
        assert f["Aykırı_adayı"].to_list() == [False] * 4 + [True]


def test_forward_interleaved_and_batch_boundary(tmp_path):
    # Boundary is at4096; nearest A observation must survive across batches, never B.
    n = 4100
    groups = ["A", "B"] * (n // 2)
    values = [10, 20] + [None] * (n - 2)
    store, req, work = prepare(
        tmp_path,
        pl.DataFrame(
            {"g": groups, "t": list(range(n)), "v": pl.Series(values, dtype=pl.Int64)}
        ),
    )
    with closing(store):
        r, d, old, f = run(
            store,
            work,
            "v",
            "ordered_fill",
            {"order_columns": [column(req, "t")], "group_columns": [column(req, "g")]},
        )
        assert f["v"].to_list() == [10, 20] * (n // 2)
        assert r["impact"]["changed_cells"] == n - 2
        assert f["__vu_row_id"].to_list() == old["__vu_row_id"].to_list()


def test_all_missing_column_removal_and_required_group_reject(tmp_path):
    store, req, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "a": pl.Series([None, None], dtype=pl.Int64),
                "b": pl.Series([None, None], dtype=pl.Int64),
            }
        ),
    )
    with closing(store):
        state = copy.deepcopy(store.state)
        with pytest.raises(ProjectError):
            run(store, work, ["a", "b"], "missing_columns")
        with pytest.raises(ProjectError):
            run(store, work, "a", "ordered_fill", {"order_columns": [column(req, "b")]})
        assert store.state == state


@pytest.mark.parametrize(
    "point",
    [
        "lineage_copy_chunk",
        "artifact_promoted",
        "metadata_committed",
        "pointer_fsynced",
    ],
)
def test_dedup_copy_atomic_lineage_and_dataset_creation(tmp_path, point):
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"v": [1, 1, 2], "order": [3, 1, 2]})
    )
    root = store.root
    with closing(store):
        before = copy.deepcopy(store.state)
        p = defaults("dedup")
        p["order_columns"] = [column(request, "order")]
        result = calculate(
            request, build(request, "dedup", [column(request, "v")], p, "copy"), work
        )

        def fail(checkpoint):
            if checkpoint == point:
                raise OSError("injected disk fault")

        with pytest.raises((OSError, ProjectError)):
            store.publish_operation(result, checkpoint=fail)
        assert store.state == before
    with closing(ProjectStore.open(root)) as reopened:
        assert reopened.state == before
        assert not list(reopened.path("staging").iterdir())


def test_effect_columns_are_actual_changes_not_selected_columns(tmp_path):
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"a": ["x", "y"], "b": [1, 2]})
    )
    with closing(store):
        result, d, _, _ = run(store, work, "a", "trim")
        assert (
            result["impact"]["changed_columns"] == result["impact"]["changed_rows"] == 0
        )
        result, _, _, _ = run(store, work, "b", "missing_rows")
        assert (
            result["impact"]["changed_columns"] == result["impact"]["removed_rows"] == 0
        )


def test_native_timezone_and_nanosecond_conversion_never_discards_precision(tmp_path):
    from zoneinfo import ZoneInfo

    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "z": pl.Series(
                    [
                        datetime(
                            2024,
                            11,
                            3,
                            1,
                            30,
                            tzinfo=ZoneInfo("America/New_York"),
                            fold=1,
                        )
                    ],
                    dtype=pl.Datetime("ns", "America/New_York"),
                ),
                "ns": pl.Series([1001], dtype=pl.Datetime("ns")),
                "id": [1],
            }
        ),
    )
    with closing(store):
        _, d, before, after = run(
            store,
            work,
            "z",
            "convert",
            {"target": {"kind": "Datetime", "unit": "us", "zone": "UTC"}},
        )
        assert after["z"][0].astimezone(UTC) == before["z"][0].astimezone(UTC)
        move(store.state, d["dataset_id"], "undo")
        state = copy.deepcopy(store.state)
        with pytest.raises(ProjectError):
            run(
                store,
                work,
                "ns",
                "convert",
                {"target": {"kind": "Datetime", "unit": "us", "zone": None}},
            )
        assert store.state == state
        _, _, _, text = run(store, work, "ns", "convert")
        assert text["ns"][0].endswith(".000001001")


def test_full_column_dedup_keeps_distinct_events_and_stable_ties(tmp_path):
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"v": [1, 1, 1], "event": [1, 1, 2]})
    )
    with closing(store):
        names = [c["name"] for c in request["columns"]]
        r, d, before, after = run(
            store, work, names, "dedup", {"order_columns": [column(request, "event")]}
        )
        assert after["__vu_row_id"].to_list() == [
            before["__vu_row_id"][0],
            before["__vu_row_id"][2],
        ]
        assert r["impact"]["removed_rows"] == 1
        move(store.state, d["dataset_id"], "undo")
        _, _, _, after = run(
            store,
            work,
            "v",
            "dedup",
            {"order_columns": [column(request, "event")], "keep": "last"},
        )
        assert after["__vu_row_id"].to_list() == [before["__vu_row_id"][2]]


@pytest.mark.parametrize("point", ["lineage_copy_chunk", "pointer_replaced"])
def test_real_sigkill_copy_dedup_recovery(tmp_path, point):
    import signal
    import subprocess
    import sys

    from veri_ufku.storage.project_model import encode

    store, request, work = prepare(
        tmp_path, pl.DataFrame({"v": [1, 1, 2], "order": [1, 2, 3]})
    )
    p = defaults("dedup")
    p["order_columns"] = [column(request, "order")]
    result = calculate(
        request, build(request, "dedup", [column(request, "v")], p, "copy"), work
    )
    recipe = tmp_path / "result.json"
    recipe.write_bytes(encode(result))
    root = store.root
    before = copy.deepcopy(store.state)
    store.close()
    code = """
import os, signal, sys
from pathlib import Path
from veri_ufku.storage.project_model import decode
from veri_ufku.storage.project_store import ProjectStore
store=ProjectStore.open(sys.argv[1])
def checkpoint(point):
    if point == sys.argv[3]:
        os.kill(os.getpid(), signal.SIGKILL)
store.publish_operation(decode(Path(sys.argv[2]).read_bytes()), checkpoint=checkpoint)
"""
    child = subprocess.run(
        [sys.executable, "-c", code, str(root), str(recipe), point],
        capture_output=True,
        timeout=20,
    )
    assert child.returncode == -signal.SIGKILL, child.stderr
    with closing(ProjectStore.open(root, recover_lock=True)) as reopened:
        if point == "lineage_copy_chunk":
            assert reopened.state == before
        else:
            assert len(active_datasets(reopened.state)) == 2
            dataset = active_datasets(reopened.state)[-1]
            assert dataset["version_id"] == result["version_id"]
            assert pl.read_parquet(reopened.path(dataset["snapshot_uri"]))[
                "order"
            ].to_list() == [1, 3]
            assert pl.read_parquet(reopened.path(dataset["lineage_uri"])).height == 3
        assert not list(reopened.path("staging").iterdir())


def test_nanosecond_group_identity_does_not_mix_time_groups(tmp_path):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "group": pl.Series([1001, 1002, 1001, 1002], dtype=pl.Datetime("ns")),
                "t": [0, 0, 1, 1],
                "v": pl.Series([10, None, None, 20], dtype=pl.Int64),
            }
        ),
    )
    with closing(store):
        _, _, _, after = run(
            store,
            work,
            "v",
            "ordered_fill",
            {
                "order_columns": [column(request, "t")],
                "group_columns": [column(request, "group")],
            },
        )
        assert after["v"].to_list() == [10, None, 10, 20]
        assert after["group"].cast(pl.Int64).to_list() == [1001, 1002, 1001, 1002]


def test_untyped_all_null_requires_explicit_type_before_fill(tmp_path):
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"v": [None, None], "id": [1, 2]})
    )
    with closing(store):
        state = copy.deepcopy(store.state)
        with pytest.raises(ProjectError, match="önce açık tür dönüşümü"):
            run(store, work, "v", "fill", {"value": "2"})
        assert store.state == state
        _, _, before, converted = run(
            store, work, "v", "convert", {"target": {"kind": "Int64"}}
        )
        assert converted["v"].dtype == pl.Int64 and converted["v"].null_count() == 2
        _, d, _, after = run(store, work, "v", "fill", {"value": "2"})
        assert after["v"].to_list() == [2, 2]
        assert after["__vu_row_id"].to_list() == before["__vu_row_id"].to_list()
        move(store.state, d["dataset_id"], "undo")
        move(store.state, d["dataset_id"], "undo")
        assert pl.read_parquet(
            store.path(active_datasets(store.state)[0]["snapshot_uri"])
        ).equals(before)
