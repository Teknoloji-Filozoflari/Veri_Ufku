"""Independent DuckDB SQL versus production Polars contracts; no Python float Decimal bridge."""

from contextlib import closing
from datetime import date
from decimal import Decimal

import duckdb
import polars as pl
import pytest
from test_dataset import column, prepare
from test_relational import add_source, out

from veri_ufku.importers.native import describe
from veri_ufku.operations.contracts import build
from veri_ufku.operations.engine import calculate
from veri_ufku.operations.relational_contracts import EQUALITY


@pytest.mark.parametrize("how", ["inner", "left", "right", "full"])
@pytest.mark.parametrize("null_equal", [False, True])
def test_join_null_ties_decimal_date_equivalent(tmp_path, how, null_equal):
    left = pl.DataFrame(
        {
            "key": [1, 1, None, 2],
            "amount": [Decimal("2.10"), Decimal("10.20"), None, Decimal("1.00")],
            "date": [date(2024, 1, 1), date(2024, 1, 2), None, date(2024, 2, 1)],
        }
    )
    right = pl.DataFrame(
        {
            "key": [1, 1, None, 3],
            "value": [Decimal("0.10"), Decimal("0.20"), None, Decimal("3.00")],
        }
    )
    store, r, work = prepare(tmp_path, left)
    with (
        closing(store),
        closing(
            duckdb.connect(
                config={
                    "autoinstall_known_extensions": "false",
                    "autoload_known_extensions": "false",
                }
            )
        ) as db,
    ):
        other = add_source(store, work, right)
        r["secondary"] = other
        p = dict(
            secondary_version_id=other["version_id"],
            left_keys=[column(r, "key")],
            right_keys=[column(other, "key")],
            how=how,
            nulls_equal=null_equal,
            right_outputs=[
                dict(
                    column_id=c["id"],
                    output=out(
                        c["name"] + "_right",
                        pl.Int64 if c["name"] == "key" else right.schema[c["name"]],
                    ),
                )
                for c in other["columns"]
            ],
            equality=EQUALITY,
            max_output_rows=100,
        )
        result = calculate(r, build(r, "join", [column(r, "key")], p), work)
        frame = pl.read_parquet(result["path"]).select(
            "key", "amount", "date", "key_right", "value_right"
        )
        left.with_row_index("pos").write_parquet(work / "l.parquet")
        right.with_row_index("pos").write_parquet(work / "r.parquet")
        equality = "IS NOT DISTINCT FROM" if null_equal else "="
        order = (
            "r.pos NULLS LAST,l.pos NULLS LAST"
            if how == "right"
            else "l.pos NULLS LAST,r.pos NULLS LAST"
        )
        sql = f"SELECT l.key,l.amount,l.date,r.key,r.value FROM read_parquet(?) l {how.upper()} JOIN read_parquet(?) r ON l.key {equality} r.key ORDER BY {order}"
        expected = db.execute(
            sql, [str(work / "l.parquet"), str(work / "r.parquet")]
        ).fetchall()
        assert frame.rows() == expected
        assert result["diagnostics"]["predicted_rows"] == len(expected)


def test_aggregate_and_append_decimal_date_equivalent(tmp_path):
    frame = pl.DataFrame(
        {
            "key": [1, 1, 2, None],
            "amount": [Decimal("2.10"), Decimal("10.20"), None, Decimal("1.00")],
            "day": [date(2024, 1, 1), date(2024, 1, 2), None, date(2024, 2, 1)],
        }
    )
    store, r, work = prepare(tmp_path, frame)
    with (
        closing(store),
        closing(
            duckdb.connect(
                config={
                    "autoinstall_known_extensions": "false",
                    "autoload_known_extensions": "false",
                }
            )
        ) as db,
    ):
        g, v, d = [column(r, n) for n in ("key", "amount", "day")]
        params = dict(
            group_columns=[g],
            equality=EQUALITY,
            max_output_rows=100,
            metrics=[
                dict(
                    column_id=v,
                    method="sum",
                    target=describe(pl.Decimal(38, 2)),
                    output=out("total", pl.Decimal(38, 2)),
                ),
                dict(
                    column_id=d,
                    method="min",
                    target=describe(pl.Date),
                    output=out("first_day", pl.Date),
                ),
            ],
        )
        result = calculate(r, build(r, "aggregate", [g, v, d], params), work)
        frame.with_row_index("pos").write_parquet(work / "f.parquet")
        expected = db.execute(
            "SELECT key, sum(amount), min(day) FROM read_parquet(?) GROUP BY key ORDER BY min(pos)",
            [str(work / "f.parquet")],
        ).fetchall()
        assert (
            pl.read_parquet(result["path"]).select("key", "total", "first_day").rows()
            == expected
        )
        other = add_source(store, work, frame)
        r["secondary"] = other
        params = dict(
            secondary_version_id=other["version_id"],
            max_output_rows=100,
            mapping=[
                dict(
                    left_column=c["id"],
                    right_column=column(other, c["name"]),
                    output=out(c["name"], frame.schema[c["name"]]),
                )
                for c in r["columns"]
            ],
        )
        result = calculate(
            r, build(r, "append", [c["id"] for c in r["columns"]], params), work
        )
        expected = db.execute(
            "SELECT key,amount,day FROM read_parquet(?) UNION ALL SELECT key,amount,day FROM read_parquet(?)",
            [str(work / "f.parquet")] * 2,
        ).fetchall()
        assert (
            pl.read_parquet(result["path"]).select("key", "amount", "day").rows()
            == expected
        )
