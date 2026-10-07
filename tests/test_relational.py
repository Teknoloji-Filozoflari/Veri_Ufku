"""Independent Phase11 expected values, real identity memberships and safe formulas."""

import copy
from contextlib import closing
from datetime import date
from decimal import Decimal

import polars as pl
import pytest
from test_dataset import column, prepare
from test_operations import request_for

from veri_ufku.importers.delimited import Control, capture
from veri_ufku.importers.native import StructuredSettings, describe
from veri_ufku.importers.registry import get_adapter
from veri_ufku.operations.contracts import active_datasets, build, move
from veri_ufku.operations.engine import calculate
from veri_ufku.operations.formula import parse
from veri_ufku.operations.relational_contracts import EQUALITY
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.project_store import ProjectStore


def out(name, dtype=pl.Int64):
    return dict(id="col:" + uid(), name=name, original_name=name, type=str(dtype))


def add_source(store, work, frame):
    path = work / (uid() + ".parquet")
    frame.write_parquet(path)
    snapshot = capture(path, work, any_format=True)
    result = get_adapter("parquet").import_data(
        snapshot, StructuredSettings(adapter_id="parquet"), work, Control()
    )
    return request_for(store, store.publish_import(result))


def join_params(r, other, how="full", nulls=False):
    return dict(
        secondary_version_id=other["version_id"],
        left_keys=[column(r, "key")],
        right_keys=[column(other, "key")],
        how=how,
        nulls_equal=nulls,
        right_outputs=[
            dict(
                column_id=c["id"],
                output=out(
                    c["name"] + "_right",
                    pl.String if c["type"] == "String" else pl.Int64,
                ),
            )
            for c in other["columns"]
        ],
        max_output_rows=10000,
        equality=EQUALITY,
    )


@pytest.mark.parametrize(
    "how,nulls,expected",
    [
        ("inner", False, 4),
        ("left", False, 6),
        ("right", False, 6),
        ("full", False, 8),
        ("full", True, 7),
    ],
)
def test_join_exact_growth_membership_undo_reopen(tmp_path, how, nulls, expected):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"key": [1, 1, 2, None], "left": ["a", "b", "c", "d"]})
    )
    root = store.root
    with closing(store):
        other = add_source(
            store,
            work,
            pl.DataFrame({"key": [1, 1, 3, None], "value": ["x", "y", "z", "w"]}),
        )
        r["secondary"] = other
        original = pl.read_parquet(r["path"])
        result = calculate(
            r,
            build(r, "join", [column(r, "key")], join_params(r, other, how, nulls)),
            work,
        )
        assert result["impact"]["after_rows"] == expected
        assert result["diagnostics"]["relationship"] == "n:n"
        assert result["diagnostics"]["predicted_rows"] == expected
        frame = pl.read_parquet(result["path"])
        assert frame["__vu_row_id"].n_unique() == expected
        assert frame["__vu_source_record_id"].null_count() == expected
        edges = pl.read_parquet(result["lineage_path"])
        assert edges["input_version_id"].unique().sort().to_list() == sorted(
            [r["version_id"], other["version_id"]]
        )
        assert set(edges["output_row_id"]) == set(frame["__vu_row_id"])
        assert frame.filter(pl.col("key") == 1).select(
            "left", "value_right"
        ).rows() == (
            [("a", "x"), ("b", "x"), ("a", "y"), ("b", "y")]
            if how == "right"
            else [("a", "x"), ("a", "y"), ("b", "x"), ("b", "y")]
        )
        d = store.publish_operation(result)
        move(store.state, d["dataset_id"], "undo")
        assert pl.read_parquet(
            store.path(
                next(
                    x
                    for x in active_datasets(store.state)
                    if x["dataset_id"] == d["dataset_id"]
                )["snapshot_uri"]
            )
        ).equals(original)
        move(store.state, d["dataset_id"], "redo")
        store.save()
        final = copy.deepcopy(store.state)
    with closing(ProjectStore.open(root)) as reopened:
        assert reopened.state == final
        assert pl.read_parquet(reopened.path(d["snapshot_uri"])).equals(frame)


def test_formula_text_date_and_security(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "x": [Decimal("2.10"), Decimal("0.00"), None],
                "text": ["a-b-c", "d", None],
                "date": [date(2024, 1, 1), None, date(2024, 3, 1)],
            }
        ),
    )
    with closing(store):
        x = column(r, "x")
        params = dict(
            expression=f'10 / col("{x}")',
            target=describe(pl.Float64),
            output=out("ratio", pl.Float64),
            zero_policy="null",
        )
        # Nonrepresentable exact Float64 cannot silently round in computed formulas.
        params["expression"] = f'col("{x}") * 2'
        params["target"] = describe(pl.Decimal(38, 2))
        params["output"] = out("double", pl.Decimal(38, 2))
        result = calculate(r, build(r, "computed", [x], params), work)
        assert pl.read_parquet(result["path"])["double"].to_list() == [
            Decimal("4.20"),
            Decimal("0.00"),
            None,
        ]
        assert result["spec"]["parameters"]["tree"]
        for expression in [
            '__import__("os")',
            'col("x").__class__',
            "[x for x in y]",
            "(lambda:1)()",
            'open("/tmp/a")',
        ]:
            with pytest.raises(ProjectError):
                parse(expression, r["columns"])
        split = dict(
            delimiter="-", outputs=[out("first", pl.String), out("rest", pl.String)]
        )
        a = calculate(r, build(r, "text_split", [column(r, "text")], split), work)
        assert pl.read_parquet(a["path"]).select("first", "rest").rows() == [
            ("a", "b-c"),
            ("d", None),
            (None, None),
        ]
        parts = dict(
            timezone="preserve", parts=[dict(part="month", output=out("month"))]
        )
        a = calculate(r, build(r, "date_parts", [column(r, "date")], parts), work)
        assert pl.read_parquet(a["path"])["month"].to_list() == [1, None, 3]


def test_aggregate_pivot_unpivot_decimal_and_membership(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "group": ["a", "a", "b"],
                "header": ["x", "x", "y"],
                "value": [Decimal("2.00"), Decimal("10.00"), None],
            }
        ),
    )
    with closing(store):
        g, h, v = [column(r, x) for x in ("group", "header", "value")]
        dt = pl.Decimal(38, 2)
        p = dict(
            group_columns=[g],
            equality=EQUALITY,
            max_output_rows=100,
            metrics=[
                dict(
                    column_id=v,
                    method="min",
                    target=describe(dt),
                    output=out("minimum", dt),
                ),
                dict(
                    column_id=v,
                    method="sum",
                    target=describe(dt),
                    output=out("total", dt),
                ),
            ],
        )
        a = calculate(r, build(r, "aggregate", [g, v], p), work)
        assert pl.read_parquet(a["path"]).select(
            "group", "minimum", "total"
        ).rows() == [("a", Decimal("2.00"), Decimal("12.00")), ("b", None, None)]
        assert pl.read_parquet(a["lineage_path"]).height == 3
        store.publish_operation(a)
        p = dict(
            group_columns=[g],
            header_column=h,
            value_column=v,
            aggregation="reject",
            target=describe(dt),
            equality=EQUALITY,
            max_output_rows=100,
        )
        with pytest.raises(ProjectError):
            calculate(r, build(r, "pivot", [g, h, v], p), work)
        p["aggregation"] = "sum"
        a = calculate(r, build(r, "pivot", [g, h, v], p), work)
        assert pl.read_parquet(a["path"])["Pivot_x"].to_list() == [
            Decimal("12.00"),
            None,
        ]
        # Preview binds discovered headers/ColumnIds; revalidation preserves them.
        assert a["spec"]["parameters"]["resolved_headers"]
        p = dict(
            index_columns=[g],
            value_columns=[v],
            variable_output=out("variable", pl.String),
            value_output=out("long_value", dt),
            max_output_rows=100,
        )
        a = calculate(r, build(r, "unpivot", [g, v], p), work)
        assert pl.read_parquet(a["path"])["long_value"].to_list() == [
            Decimal("2.00"),
            Decimal("10.00"),
            None,
        ]


def test_append_explicit_padding_atomic_secondary_and_undo(tmp_path):
    store, r, work = prepare(tmp_path, pl.DataFrame({"a": [1, 1], "b": ["x", "x"]}))
    with closing(store):
        other = add_source(store, work, pl.DataFrame({"a": [2], "c": ["y"]}))
        r["secondary"] = other
        p = dict(
            secondary_version_id=other["version_id"],
            max_output_rows=100,
            mapping=[
                dict(
                    left_column=column(r, "a"),
                    right_column=column(other, "a"),
                    output=out("a"),
                ),
                dict(
                    left_column=column(r, "b"),
                    right_column=None,
                    output=out("b", pl.String),
                ),
                dict(
                    left_column=None,
                    right_column=column(other, "c"),
                    output=out("c", pl.String),
                ),
            ],
        )
        a = calculate(r, build(r, "append", [c["id"] for c in r["columns"]], p), work)
        frame = pl.read_parquet(a["path"])
        assert frame.select("a", "b", "c").rows() == [
            (1, "x", None),
            (1, "x", None),
            (2, None, "y"),
        ]
        assert frame["__vu_row_id"].n_unique() == 3
        before = copy.deepcopy(store.state)

        def fault(point):
            if point == "lineage_copy_chunk":
                raise OSError("fault")

        with pytest.raises(OSError):
            store.publish_operation(a, checkpoint=fault)
        assert store.state == before
        d = store.publish_operation(a)
        move(store.state, d["dataset_id"], "undo")
        move(store.state, d["dataset_id"], "redo")
        store.save()
        assert pl.read_parquet(store.path(d["snapshot_uri"])).equals(frame)


def test_formula_zero_null_exactness_rename_and_failed_result(tmp_path):
    store, r, work = prepare(tmp_path, pl.DataFrame({"value": [2, 0, None]}))
    with closing(store):
        c = column(r, "value")
        p = dict(
            expression=f'8 / col("{c}")',
            target=describe(pl.Int64),
            output=out("ratio"),
            zero_policy="reject",
        )
        before = copy.deepcopy(store.state)
        with pytest.raises(ProjectError, match="sıfıra"):
            calculate(r, build(r, "computed", [c], p), work)
        assert store.state == before
        p["zero_policy"] = "null"
        a = calculate(r, build(r, "computed", [c], p), work)
        assert pl.read_parquet(a["path"])["ratio"].to_list() == [4, None, None]
        assert a["diagnostics"]["zero_divisions"] == 1 and a["impact"]["new_nulls"] == 2
        renamed = store.publish_operation(
            calculate(r, build(r, "rename", [c], dict(name="renamed")), work)
        )
        newer = request_for(store, renamed)
        a = calculate(newer, build(newer, "computed", [c], p), work)
        assert pl.read_parquet(a["path"])["ratio"].to_list() == [4, None, None]
        p["expression"] = "0.1"
        p["target"] = describe(pl.Float64)
        p["output"] = out("lossy", pl.Float64)
        with pytest.raises(ProjectError):
            calculate(newer, build(newer, "computed", [], p), work)
        p["expression"] = "9223372036854775808"
        p["target"] = describe(pl.Int64)
        p["output"] = out("overflow")
        with pytest.raises(ProjectError):
            calculate(newer, build(newer, "computed", [], p), work)


def test_secondary_stale_tampered_lineage_and_output_symlink_protected(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"key": [1, 1], "left": ["a", "b"]})
    )
    with closing(store):
        other = add_source(
            store, work, pl.DataFrame({"key": [1, 1], "value": ["x", "y"]})
        )
        r["secondary"] = other
        p = join_params(r, other)
        a = calculate(r, build(r, "join", [column(r, "key")], p), work)
        before = copy.deepcopy(store.state)
        from pathlib import Path

        from veri_ufku.importers.delimited import hash_artifact

        output = Path(a["path"])
        source = Path(r["path"])
        data = source.read_bytes()
        output.unlink()
        output.symlink_to(source)
        with pytest.raises(ProjectError):
            store.publish_operation(a)
        assert source.read_bytes() == data and store.state == before
        a = calculate(r, build(r, "join", [column(r, "key")], p), work)
        edges = pl.read_parquet(a["lineage_path"]).with_columns(
            pl.lit("row:" + uid()).alias("input_row_id")
        )
        edges.write_parquet(a["lineage_path"])
        a["lineage_fingerprint"] = hash_artifact(a["lineage_path"], Control())
        with pytest.raises(ProjectError, match="kimliği"):
            store.publish_operation(a)
        assert store.state == before
        a = calculate(r, build(r, "join", [column(r, "key")], p), work)
        store.publish_operation(
            calculate(
                other,
                build(other, "rename", [column(other, "value")], dict(name="changed")),
                work,
            )
        )
        before = copy.deepcopy(store.state)
        with pytest.raises(ProjectError, match="İkinci"):
            store.publish_operation(a)
        assert store.state == before


def test_many_many_budget_and_cancel_leave_old_dataset(tmp_path):
    import threading

    from veri_ufku.jobs.workers import Canceled

    store, r, work = prepare(
        tmp_path, pl.DataFrame({"key": [1] * 10, "left": ["a"] * 10})
    )
    with closing(store):
        other = add_source(
            store, work, pl.DataFrame({"key": [1] * 20, "value": ["b"] * 20})
        )
        r["secondary"] = other
        p = join_params(r, other)
        p["max_output_rows"] = 199
        before = copy.deepcopy(store.state)
        with pytest.raises(ProjectError, match="200"):
            calculate(r, build(r, "join", [column(r, "key")], p), work)
        p["max_output_rows"] = 200
        event = threading.Event()
        event.set()
        with pytest.raises(Canceled):
            calculate(r, build(r, "join", [column(r, "key")], p), work, Control(event))
        assert store.state == before


@pytest.mark.parametrize("point", ["lineage_copy_chunk", "pointer_replaced"])
def test_real_sigkill_join_atomic_recovery(tmp_path, point):
    import signal
    import subprocess
    import sys

    from veri_ufku.storage.project_model import encode

    store, r, work = prepare(
        tmp_path, pl.DataFrame({"key": [1, 1], "left": ["a", "b"]})
    )
    other = add_source(store, work, pl.DataFrame({"key": [1, 1], "value": ["x", "y"]}))
    r["secondary"] = other
    a = calculate(r, build(r, "join", [column(r, "key")], join_params(r, other)), work)
    path = store.root
    before = copy.deepcopy(store.state)
    recipe = tmp_path / "recipe.json"
    recipe.write_bytes(encode(a))
    store.close()
    code = """import os,signal,sys
from pathlib import Path
from veri_ufku.storage.project_model import decode
from veri_ufku.storage.project_store import ProjectStore
store=ProjectStore.open(sys.argv[1])
def checkpoint(p):
    if p==sys.argv[3]:os.kill(os.getpid(),signal.SIGKILL)
store.publish_operation(decode(Path(sys.argv[2]).read_bytes()),checkpoint=checkpoint)
"""
    child = subprocess.run(
        [sys.executable, "-c", code, str(path), str(recipe), point],
        capture_output=True,
        timeout=20,
    )
    assert child.returncode == -signal.SIGKILL, child.stderr
    with closing(ProjectStore.open(path, recover_lock=True)) as reopened:
        if point == "lineage_copy_chunk":
            assert reopened.state == before
        else:
            d = next(
                d
                for d in active_datasets(reopened.state)
                if d["dataset_id"] == before["datasets"][0]["dataset_id"]
            )
            assert d["version_id"] == a["version_id"]
            assert pl.read_parquet(reopened.path(d["lineage_uri"])).height == 8
            assert pl.read_parquet(reopened.path(d["snapshot_uri"])).height == 4
        assert list(reopened.path("staging").iterdir()) == []


def test_transform_followed_by_cleaning_role_and_copy_history(tmp_path):
    from veri_ufku.analytics.contracts import metadata_version
    from veri_ufku.operations.cleaning_contracts import defaults
    from veri_ufku.operations.contracts import activate

    store, r, work = prepare(
        tmp_path, pl.DataFrame({"value": [1, None], "key": ["a", "b"]})
    )
    with closing(store):
        c = column(r, "value")
        p = dict(
            expression=f'col("{c}") * 2',
            target=describe(pl.Int64),
            output=out("double"),
            zero_policy="reject",
        )
        d = store.publish_operation(calculate(r, build(r, "computed", [c], p), work))
        newer = request_for(store, d)
        params = defaults("fill")
        params["value"] = "8"
        result = calculate(newer, build(newer, "fill", [c], params), work)
        cleaned = store.publish_operation(result)
        assert not cleaned.get("input_version_ids")
        newer = request_for(store, cleaned)
        result = calculate(
            newer,
            build(
                newer,
                "computed",
                [c],
                dict(p, output=out("triple"), expression=f'col("{c}") * 3'),
                destination="copy",
            ),
            work,
        )
        copied = store.publish_operation(result)
        assert copied["dataset_id"] != cleaned["dataset_id"]
        move(store.state, copied["dataset_id"], "undo")
        move(store.state, copied["dataset_id"], "redo")
        store.save()
        # Metadata helper must clear the previous recipe's dependencies before binding a new role step.
        meta = metadata_version(copied, c, "measurement", "", [], "")
        assert not meta.get("input_version_ids")
        role = build(
            dict(
                columns=copied["import_metadata"]["columns"],
                version_id=copied["version_id"],
            ),
            "roles",
            [c],
            dict(semantic_metadata=meta["semantic_metadata"], analysis_unit=""),
        )
        meta.update(
            operation_id=role.id,
            output_schema=store.manifest["artifacts"][copied["snapshot_uri"]]["schema"],
        )
        store.state["datasets"].append(meta)
        store.state["operations"].append(
            dict(
                id=role.id,
                dataset_version_ids=[copied["version_id"], meta["version_id"]],
                seed=None,
                spec=role.data(),
                output_version_id=meta["version_id"],
            )
        )
        activate(store.state, meta)
        store.save()


def test_nested_unselected_arrow_columns_preserved_by_formula_and_append(tmp_path):
    source = pl.DataFrame(
        {"value": [1, 2], "nested": [[1], [2, 3]], "struct": [{"a": 1}, {"a": 2}]}
    )
    store, r, work = prepare(tmp_path, source)
    with closing(store):
        c = column(r, "value")
        p = dict(
            expression=f'col("{c}")+1',
            target=describe(pl.Int64),
            output=out("new"),
            zero_policy="reject",
        )
        a = calculate(r, build(r, "computed", [c], p), work)
        assert (
            pl.read_parquet(a["path"])
            .select("nested", "struct")
            .equals(source.select("nested", "struct"))
        )
        other = add_source(store, work, source)
        r["secondary"] = other
        p = dict(
            secondary_version_id=other["version_id"],
            max_output_rows=100,
            mapping=[
                dict(
                    left_column=c["id"],
                    right_column=column(other, c["name"]),
                    output=out(c["name"], source.schema[c["name"]]),
                )
                for c in r["columns"]
            ],
        )
        a = calculate(r, build(r, "append", [c["id"] for c in r["columns"]], p), work)
        d = store.publish_operation(a)
        assert (
            pl.read_parquet(store.path(d["snapshot_uri"]))
            .select(source.columns)
            .equals(pl.concat([source, source]))
        )


def test_timezone_parts_and_nanosecond_group_min_preserve_physical_values(tmp_path):
    instants = pl.Series(
        "time", [1706740200000000001, 1706740200000000002, None], dtype=pl.Int64
    ).cast(pl.Datetime("ns", "UTC"))
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"group": ["a", "a", "b"], "time": instants})
    )
    with closing(store):
        c = column(r, "time")
        g = column(r, "group")
        p = dict(
            timezone="Europe/Istanbul", parts=[dict(part="month", output=out("month"))]
        )
        a = calculate(r, build(r, "date_parts", [c], p), work)
        assert pl.read_parquet(a["path"])["month"].to_list() == [2, 2, None]
        dt = pl.Datetime("ns", "UTC")
        p = dict(
            group_columns=[g],
            equality=EQUALITY,
            max_output_rows=100,
            metrics=[
                dict(
                    column_id=c,
                    method="min",
                    target=describe(dt),
                    output=out("first", dt),
                )
            ],
        )
        a = calculate(r, build(r, "aggregate", [g, c], p), work)
        assert pl.read_parquet(a["path"])["first"].cast(pl.Int64).to_list() == [
            1706740200000000001,
            None,
        ]
        store.publish_operation(a)


def test_native_nonfinite_join_keys_are_rejected(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"key": [1.0, float("nan")], "left": ["a", "b"]})
    )
    with closing(store):
        other = add_source(
            store, work, pl.DataFrame({"key": [1.0, 2.0], "value": ["a", "b"]})
        )
        r["secondary"] = other
        p = join_params(r, other)
        for c in p["right_outputs"]:
            if c["output"]["name"] == "key_right":
                c["output"]["type"] = "Float64"
        with pytest.raises(ProjectError, match="NaN"):
            calculate(r, build(r, "join", [column(r, "key")], p), work)


def test_csv_timezone_aggregate_never_erases_zone(tmp_path):
    from veri_ufku.importers.delimited import ImportSettings

    source = tmp_path / "source.csv"
    source.write_text("group,when\na,2024-01-01 00:00:00\na,2024-01-02 00:00:00\n")
    work = tmp_path / "work"
    work.mkdir()
    snapshot = capture(source, work, any_format=True)
    imported = get_adapter("csv").import_data(
        snapshot,
        ImportSettings(
            types=("text", "datetime"), timezone="UTC", date_format="%Y-%m-%d %H:%M:%S"
        ),
        work,
        Control(),
    )
    with closing(ProjectStore.create(tmp_path / "project")) as store:
        d = store.publish_import(imported)
        r = request_for(store, d)
        g, c = column(r, "group"), column(r, "when")
        dt = pl.Datetime("us", "UTC")
        p = dict(
            group_columns=[g],
            equality=EQUALITY,
            max_output_rows=100,
            metrics=[
                dict(
                    column_id=c,
                    method="min",
                    target=describe(dt),
                    output=out("first", dt),
                )
            ],
        )
        a = calculate(r, build(r, "aggregate", [g, c], p), work)
        output = store.publish_operation(a)
        assert pl.read_parquet(store.path(output["snapshot_uri"]))["first"].dtype == dt
        assert (
            store.state["operations"][-1]["spec"]["parameters"]["metrics"][0]["target"][
                "zone"
            ]
            == "UTC"
        )
        p["metrics"][0]["target"] = describe(pl.Datetime("us"))
        p["metrics"][0]["output"] = out("lost", pl.Datetime("us"))
        with pytest.raises(ProjectError):
            build(r, "aggregate", [g, c], p)
