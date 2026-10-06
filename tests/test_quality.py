"""Independent problematic references, exact RowIds and immutable quality scope."""

import copy
from contextlib import closing
from dataclasses import replace

import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.quality import scan, turkish_fold
from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.storage.project_model import ProjectError


def parameters(**changes):
    p = dict(
        sample=False,
        target="dataset",
        purpose="inspect",
        duplicate_columns=[],
        rules=[],
        view=ViewSpec().data(),
    )
    p.update(changes)
    return p


def rule(cid, kind, value="", upper=""):
    return dict(column_id=cid, kind=kind, value=value, upper=upper)


def test_reference_records_counts_recommendations_immutable(tmp_path):
    frame = pl.DataFrame(
        dict(
            id=["001", "001", "003", "004", "005", "006", "007", "008"],
            amount=[1, 1, 2, 3, 4, 5, 6, 100],
            category=[
                "İZMİR",
                "İZMİR",
                "izmir",
                "Ankara",
                "Ankara",
                " Ankara ",
                "ankra",
                None,
            ],
            number=["1", "1", "oops", "3", "4", "5", "6", "7"],
            day=[
                "2024-01-01",
                "2024-01-01",
                "2024-02-30",
                "2024-03-01",
                "2024-03-01",
                "2024-03-01",
                "2024-03-01",
                "2024-03-01",
            ],
            fixed=["x"] * 8,
        )
    )
    store, request, work = prepare(tmp_path, frame)
    with closing(store):
        before = copy.deepcopy(store.state)
        fingerprint = hash_artifact(request["path"], Control())
        ids = {name: column(request, name) for name in frame.columns}
        p = parameters(
            duplicate_columns=[ids["id"]],
            rules=[
                rule(ids["id"], "unique"),
                rule(ids["number"], "number"),
                rule(ids["day"], "date", "%Y-%m-%d"),
                rule(ids["amount"], "range", "0", "10"),
                rule(ids["category"], "required"),
                rule(ids["category"], "allowed", "İZMİR|izmir|Ankara| Ankara |ankra"),
            ],
        )
        report = scan(request, p, work)
        data = pl.read_parquet(request["path"])
        findings = {(f["code"], f["column_id"]): f for f in report["findings"]}
        for code, name, expected in [
            ("missing", "category", [7]),
            ("whitespace", "category", [5]),
            ("conversion", "number", [2]),
            ("invalid_date", "day", [2]),
            ("uniqueness", "id", [0, 1]),
            ("outlier", "amount", [7]),
            ("category_similarity", "category", [0, 1, 2, 3, 4, 5, 6]),
            ("constant", "fixed", list(range(8))),
        ]:
            f = findings[code, ids[name]]
            assert f["count"] == len(expected)
            assert [e["row_id"] for e in f["examples"]] == [
                data["__vu_row_id"][i] for i in expected[:5]
            ]
            assert f["ratio"] == len(expected) / 8
        assert findings["duplicates_full", ""]["count"] == 2
        assert findings["duplicates_selected", ""]["count"] == 2
        assert findings["invalid_date", ids["day"]]["classification"] == "violation"
        assert findings["outlier", ids["amount"]]["classification"] == "candidate"
        for f in report["findings"]:
            r = f["recommendation"]
            assert set(r) == {
                "id",
                "reason",
                "precondition",
                "impact",
                "operation_id",
                "learning_id",
                "available",
            }
            assert (
                "Amaç: veriyi incelemek" in r["reason"]
                and "kullanılan 8/8" in r["reason"]
            )
            assert not r["available"] and r["learning_id"]
        repeated = scan(request, p, work)
        assert report["findings"] == repeated["findings"]
        assert report["parameters"] == repeated["parameters"]
        assert (
            report["provenance"]["parameters_hash"]
            == repeated["provenance"]["parameters_hash"]
        )
        assert report["provenance"]["source_snapshot_ids"] == [
            request["source_snapshot_id"],
        ]
        assert (
            store.state == before
            and hash_artifact(request["path"], Control()) == fingerprint
        )
        assert not list(work.glob("quality*"))


def test_scope_rules_null_and_role(tmp_path):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {"amount": [1, 2, 3, 4, 100, None], "id": ["a", "b", "c", "d", "e", "f"]}
        ),
    )
    with closing(store):
        cid = column(request, "amount")
        control = Control(budget=replace(ComputeBudget(), sample_limit_rows=4))
        p = parameters(sample=True)
        a = scan(request, p, work, control)
        assert (a["scope"], a["used_n"], a["population_n"]) == ("sample", 4, 6)
        assert not any(f["code"] == "outlier" for f in a["findings"])
        view = ViewSpec(
            filters=({"column_id": cid, "operator": "gt", "value": "50"},)
        ).data()
        full = scan(request, parameters(view=view), work)
        assert full["used_n"] == 6 and not full["provenance"]["filters"]
        subset = scan(request, parameters(view=view, target="view"), work)
        assert subset["scope"] == "filtered" and subset["used_n"] == 1
        request["semantic_metadata"] = {cid: dict(role="identifier")}
        suppressed = scan(
            request, parameters(rules=[rule(cid, "range", "0", "10")]), work
        )
        assert not any(f["code"] == "outlier" for f in suppressed["findings"])
        assert (
            next(f for f in suppressed["findings"] if f["code"] == "rule")["count"] == 1
        )
        assert turkish_fold("IŞIK") == turkish_fold("ışık")
        assert turkish_fold("İZMİR") == turkish_fold("izmir")
        assert turkish_fold("I") != turkish_fold("i")
        with pytest.raises(ProjectError):
            scan(request, parameters(rules=[rule(cid, "range", "10", "0")]), work)
        with pytest.raises(ProjectError):
            scan(request, parameters(rules=[rule(cid, "date", "%bad")]), work)


def test_empty_nonfinite_and_nested(tmp_path):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {"amount": [float("nan"), float("inf"), None], "nested": [[1], [1], None]}
        ),
    )
    with closing(store):
        r = scan(request, parameters(), work)
        assert next(f for f in r["findings"] if f["code"] == "nonfinite")["count"] == 2
        assert all(f["classification"] != "violation" for f in r["findings"])


def test_conversion_precision_allowed_and_empty_scope(tmp_path):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "text": ["1", "1.5", "9007199254740993", "bad", None],
                "id": ["a", "a", "b", "c", "d"],
                "boolean": ["true", "false", "evet", "oops", None],
                "date": ["2024-02-29", "2024-02-30", "bad", "2024-01-01", None],
            }
        ),
    )
    with closing(store):
        cid = column(request, "text")
        p = parameters(
            rules=[
                rule(cid, "convert", "int64"),
                rule(cid, "convert", "float64"),
                rule(cid, "allowed", "1|1.5"),
                rule(column(request, "boolean"), "convert", "boolean"),
                rule(column(request, "date"), "convert", "date"),
                rule(column(request, "boolean"), "required"),
            ]
        )
        r = scan(request, p, work)
        int_f = next(
            f for f in r["findings"] if f["rule"] and f["rule"]["value"] == "int64"
        )
        float_f = next(
            f for f in r["findings"] if f["rule"] and f["rule"]["value"] == "float64"
        )
        allowed = next(
            f for f in r["findings"] if f["rule"] and f["rule"]["kind"] == "allowed"
        )
        assert (int_f["count"], float_f["count"], allowed["count"]) == (2, 2, 2)
        assert (
            next(
                f
                for f in r["findings"]
                if f["rule"] and f["rule"]["value"] == "boolean"
            )["count"]
            == 1
        )
        assert (
            next(
                f for f in r["findings"] if f["rule"] and f["rule"]["value"] == "date"
            )["count"]
            == 2
        )
        assert (
            next(
                f
                for f in r["findings"]
                if f["rule"] and f["rule"]["kind"] == "required"
            )["count"]
            == 1
        )
        idcol = column(request, "id")
        repeat = scan(request, parameters(duplicate_columns=[idcol]), work)
        assert (
            next(f for f in repeat["findings"] if f["code"] == "duplicates_selected")[
                "count"
            ]
            == 2
        )
        assert not any(f["classification"] == "violation" for f in repeat["findings"])
        empty = scan(
            request,
            parameters(
                target="view",
                view=ViewSpec(
                    filters=({"column_id": idcol, "operator": "eq", "value": "absent"},)
                ).data(),
            ),
            work,
        )
        assert (
            empty["used_n"] == 0
            and empty["findings"] == []
            and empty["scope"] == "filtered"
        )
        assert not list(work.glob("quality*"))
