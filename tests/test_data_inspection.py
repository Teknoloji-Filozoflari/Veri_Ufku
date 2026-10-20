from contextlib import closing
from dataclasses import replace
from decimal import Decimal

import polars as pl
from test_dataset import column, prepare

from veri_ufku.analytics.contracts import ProfileSpec
from veri_ufku.analytics.dataset import profile
from veri_ufku.analytics.inspection import inspect
from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Control


def test_all_column_inventory_and_independent_describe(tmp_path):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "amount": [1.0, 2.0, 3.0, 4.0, None, float("nan")],
                "code": ["01", "02", "03", "04", "05", "06"],
            }
        ),
    )
    with closing(store):
        before = __import__("pathlib").Path(request["path"]).read_bytes()
        result = inspect(request, {"sample": False, "describe": True}, work)
        assert result["scope"] == "full" and result["used_n"] == 6
        amount, code = result["columns"]
        assert (amount["non_null"], amount["null"], amount["nan"]) == (5, 1, 1)
        n = amount["numeric"]
        assert n["finite_n"] == 4 and Decimal(n["mean"]) == Decimal("2.5")
        assert Decimal(n["quantiles"]["0.25"]) == Decimal("1.75")
        assert code["non_null"] == 6 and "numeric" not in code
        assert __import__("pathlib").Path(request["path"]).read_bytes() == before
        sampled = inspect(
            request,
            {"sample": True},
            work,
            Control(budget=replace(ComputeBudget(), sample_limit_rows=2)),
        )
        assert (
            sampled["scope"] == "sample"
            and sampled["used_n"] == 2
            and sampled["population_n"] == 6
        )
        assert not list(work.glob("profile-*.sqlite"))


def test_numeric_identifier_summary_is_suppressed(tmp_path):
    store, request, work = prepare(tmp_path, pl.DataFrame({"record_id": [1, 2, 3, 4]}))
    with closing(store):
        request["semantic_metadata"] = {
            column(request, "record_id"): {"role": "identifier"}
        }
        result = inspect(request, {"sample": False, "describe": True}, work)
        numeric = result["columns"][0]["numeric"]
        assert numeric["suppressed"] and numeric["mean"] is None


def test_unique_paging_search_literals_and_empty_values(tmp_path):
    values = [f"value-{i:03}" for i in range(405)] + [
        "value-000",
        None,
        "",
        "%_' OR 1=1 --",
    ]
    store, request, work = prepare(tmp_path, pl.DataFrame({"label": values}))
    with closing(store):
        spec = ProfileSpec(column(request, "label"), sample=False)
        first = profile(request, spec, work)
        second = profile(request, spec, work, unique_offset=200)
        last = profile(request, spec, work, unique_offset=400)
        assert len(first["unique_values"]) == len(second["unique_values"]) == 200
        assert len(last["unique_values"]) == 7 and first["unique_matching"] == 407
        assert first["unique_values"][0] == dict(value="value-000", count=2)
        assert second["unique_values"][0]["value"] == "value-200"
        search = profile(request, spec, work, unique_query="%_' OR 1=1 --")
        assert (
            search["unique_matching"] == 1 and search["unique_values"][0]["count"] == 1
        )
        assert not list(work.glob("profile-*.sqlite"))


def test_legacy_string_inventory_reports_storage_without_implicit_conversion(
    tmp_path,
):
    from pathlib import Path

    count = 10005
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "PassengerId": [str(i + 1) for i in range(count)],
                "amount": ["1.25"] * (count - 1) + [""],
                "late_mixed": ["7"] * (count - 1) + ["unknown"],
                "code": ["001"] * count,
            }
        ),
    )
    with closing(store):
        before = Path(request["path"]).read_bytes()
        result = inspect(request, {"sample": False}, work)
        cols = {c["name"]: c for c in result["columns"]}
        assert cols["PassengerId"]["content_type"] == "String"
        assert cols["PassengerId"]["physical_type"] == "String"
        assert cols["amount"]["content_type"] == "String"
        assert cols["amount"]["null"] == 0
        assert cols["late_mixed"]["content_type"] == "String"
        assert cols["code"]["content_type"] == "String"
        assert result["types"] == {"String": 4}
        assert result["stored_types"] == {"String": 4}
        assert Path(request["path"]).read_bytes() == before
