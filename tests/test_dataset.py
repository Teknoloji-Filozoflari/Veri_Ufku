"""Independent Phase07 reference statistics, stable lineage and bounded view contracts."""

import copy
import math
from contextlib import closing
from dataclasses import replace
from decimal import Decimal

import polars as pl
import pytest

from veri_ufku.analytics.contracts import ProfileSpec, ViewSpec, metadata_version
from veri_ufku.analytics.dataset import literal, page, profile
from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Control, capture, hash_artifact
from veri_ufku.importers.native import StructuredSettings
from veri_ufku.importers.registry import get_adapter
from veri_ufku.storage.project_model import ProjectError, uid, validate_state
from veri_ufku.storage.project_store import ProjectStore


def prepare(tmp_path, frame):
    source = tmp_path / "source.parquet"
    frame.write_parquet(source)
    work = tmp_path / "work"
    work.mkdir()
    snapshot = capture(source, work, any_format=True)
    result = get_adapter("parquet").import_data(
        snapshot, StructuredSettings(adapter_id="parquet"), work, Control()
    )
    store = ProjectStore.create(tmp_path / "project")
    store.publish_import(result)
    d = store.state["datasets"][-1]
    request = dict(
        path=str(store.path(d["snapshot_uri"])),
        fingerprint=hash_artifact(store.path(d["snapshot_uri"]), Control()),
        columns=d["import_metadata"]["columns"],
        row_count=frame.height,
        version_id=d["version_id"],
        snapshot_uri=d["snapshot_uri"],
        source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
    )
    return store, request, work


def column(request, name):
    return next(c["id"] for c in request["columns"] if c["name"] == name)


def test_reference_stats_nonfinite_and_methods(tmp_path):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "amount": [
                    1.0,
                    2.0,
                    3.0,
                    4.0,
                    None,
                    float("nan"),
                    float("inf"),
                    float("-inf"),
                ],
                "id": ["00123"] * 8,
            }
        ),
    )
    with closing(store):
        p = profile(request, ProfileSpec(column(request, "amount"), sample=False), work)
        assert p["counts"] == dict(
            null=1,
            nan=1,
            positive_infinity=1,
            negative_infinity=1,
            valid=4,
            empty_string=0,
        )
        assert p["unique"] == 7 and p["null_rate"] == 1 / 8
        n = p["numeric"]
        assert Decimal(n["mean"]) == Decimal("2.5") and Decimal(n["median"]) == Decimal(
            "2.5"
        )
        assert float(n["std"]) == pytest.approx(math.sqrt(5 / 3))
        assert Decimal(n["quantiles"]["0.25"]) == Decimal("1.75")
        assert n["ddof"] == 1 and n["quantile_method"] == "linear h=(n-1)*q"
        assert n["exclusions"] == "null, NaN, +infinity, -infinity"
        q = profile(
            request, ProfileSpec(column(request, "amount"), sample=False, ddof=0), work
        )
        assert float(q["numeric"]["std"]) == pytest.approx(math.sqrt(1.25))
        ident = profile(request, ProfileSpec(column(request, "id"), sample=False), work)
        assert ident["role"] == "identifier" and ident["numeric"]["mean"] is None
        assert ident["examples"] == ["00123"]
        assert not list(work.glob("profile-*.sqlite"))


def test_pages_sort_filter_ids_and_payload_bound(tmp_path):
    store, request, _ = prepare(
        tmp_path, pl.DataFrame({"value": list(range(603)), "code": ["00123"] * 603})
    )
    with closing(store):
        original = pl.read_parquet(request["path"])
        c = column(request, "value")
        first = page(request, ViewSpec(sort_column=c, descending=True))
        second = page(request, ViewSpec(sort_column=c, descending=True), 200)
        assert len(first["rows"]) == len(second["rows"]) == 200
        assert first["rows"][0] == ["602", "00123"] and second["rows"][0][0] == "402"
        assert first["row_ids"][0] == original["__vu_row_id"][602]
        assert set(first["row_ids"]).isdisjoint(second["row_ids"])
        view = ViewSpec(
            filters=({"column_id": c, "operator": "ge", "value": "600"},),
            hidden=(column(request, "code"),),
        )
        result = page(request, view)
        assert result["total"] == 3 and result["rows"] == [["600"], ["601"], ["602"]]
        assert result["row_ids"] == original["__vu_row_id"].tail(3).to_list()
        assert result["payload_bytes"] <= result["page_bytes_limit"]
        assert first["suggestions"] == second["suggestions"]
        assert first["suggestions"][column(request, "code")]["role"] == "identifier"


def test_scope_sample_top_values_and_saved_roles(tmp_path):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {"number": list(range(300)), "label": [f"item{i}" for i in range(300)]}
        ),
    )
    with closing(store):
        c = column(request, "number")
        view = ViewSpec(filters=({"column_id": c, "operator": "ge", "value": "290"},))
        full = profile(
            request, ProfileSpec(c, sample=False, target="dataset", view=view), work
        )
        filtered = profile(
            request, ProfileSpec(c, sample=False, target="view", view=view), work
        )
        assert (
            full["used_n"] == 300 and full["filters"] == [] and full["scope"] == "full"
        )
        assert (
            filtered["used_n"] == 10
            and filtered["scope"] == "filtered"
            and filtered["filters"] == list(view.filters)
        )
        assert len(filtered["provenance"]["filters"]) == 1
        control = Control(budget=replace(ComputeBudget(), sample_limit_rows=10))
        sampled = profile(request, ProfileSpec(c), work, control)
        assert (
            sampled["scope"] == "sample"
            and sampled["used_n"] == 10
            and sampled["population_n"] == 300
        )
        assert sampled["representative_sample"] is False
        label = profile(
            request, ProfileSpec(column(request, "label"), sample=False), work
        )
        assert (
            label["unique"] == 300
            and len(label["frequencies"]) == 20
            and label["frequency_other_count"] == 280
        )
        old = copy.deepcopy(store.state["datasets"][-1])
        new = metadata_version(old, c, "identifier", "", [], "müşteri")
        store.state["datasets"].append(new)
        store.state["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=[old["version_id"]],
                seed=None,
                profile=full,
            )
        )
        assert not store.results_status()[-1]["current"]
        before = hash_artifact(request["path"], Control())
        store.save()
    with closing(ProjectStore.open(tmp_path / "project")) as reopened:
        saved = reopened.state["datasets"][-1]
        assert (
            saved["semantic_metadata"][c]["role"] == "identifier"
            and saved["analysis_unit"] == "müşteri"
        )
        assert (
            saved["import_metadata"] == old["import_metadata"]
            and saved["snapshot_uri"] == old["snapshot_uri"]
        )
        assert saved["parent_version_ids"] == [old["version_id"]]
        request["path"] = str(reopened.path(saved["snapshot_uri"]))
        assert hash_artifact(request["path"], Control()) == before
        req = dict(
            request,
            semantic_metadata=saved["semantic_metadata"],
            version_id=saved["version_id"],
        )
        assert (
            profile(req, ProfileSpec(c, sample=False), work)["numeric"]["mean"] is None
        )


def test_decimal_uint64_dates_empty_and_singleton(tmp_path):
    frame = pl.DataFrame(
        {
            "amount": pl.Series(
                [
                    Decimal("123456789012345678901234567890.12"),
                    Decimal("123456789012345678901234567890.14"),
                ],
                dtype=pl.Decimal(38, 2),
            ),
            "big": pl.Series(
                [18446744073709551614, 18446744073709551615], dtype=pl.UInt64
            ),
            "date": pl.Series([0, 123456789], dtype=pl.Int64).cast(
                pl.Datetime("ns", "UTC")
            ),
            "empty": pl.Series([None, None], dtype=pl.Float64),
        }
    )
    store, req, work = prepare(tmp_path, frame)
    with closing(store):
        p = profile(req, ProfileSpec(column(req, "amount"), sample=False), work)
        assert Decimal(p["numeric"]["mean"]) == Decimal(
            "123456789012345678901234567890.13"
        )
        assert Decimal(p["numeric"]["median"]) == Decimal(
            "123456789012345678901234567890.13"
        )
        assert (
            page(
                req,
                ViewSpec(
                    filters=(
                        {
                            "column_id": column(req, "amount"),
                            "operator": "eq",
                            "value": "123456789012345678901234567890.12",
                        },
                    )
                ),
            )["total"]
            == 1
        )
        p = profile(req, ProfileSpec(column(req, "big"), sample=False), work)
        assert Decimal(p["numeric"]["mean"]) == Decimal("18446744073709551614.5")
        p = profile(req, ProfileSpec(column(req, "date"), sample=False), work)
        assert "123456789" in p["date_range"]["maximum"]
        p = profile(req, ProfileSpec(column(req, "empty"), sample=False), work)
        assert (
            p["unique"] == 0
            and p["counts"]["null"] == 2
            and p["numeric"]["std"] is None
        )
        p = profile(
            req,
            ProfileSpec(
                column(req, "big"),
                sample=False,
                target="view",
                view=ViewSpec(
                    filters=(
                        {
                            "column_id": column(req, "big"),
                            "operator": "eq",
                            "value": "18446744073709551615",
                        },
                    )
                ),
            ),
            work,
        )
        assert p["numeric"]["std"] is None and Decimal(
            p["numeric"]["median"]
        ) == Decimal("18446744073709551615")


@pytest.mark.parametrize(
    "text,dtype",
    [
        ("18446744073709551616", pl.UInt64),
        ("9007199254740993", pl.Float64),
        ("16777217", pl.Float32),
        ("1e39", pl.Float32),
        ("1e-999", pl.Float64),
        ("1.001", pl.Decimal(10, 2)),
        ("NaN", pl.Float64),
    ],
)
def test_filter_rejects_precision_loss(text, dtype):
    with pytest.raises(ProjectError):
        literal(text, dtype)


def test_snapshot_mutation_rejects_results_and_metadata_validation(tmp_path):
    store, req, work = prepare(tmp_path, pl.DataFrame({"value": [1, 2]}))
    with closing(store):
        c = column(req, "value")
        with pytest.raises(ProjectError):
            metadata_version(store.state["datasets"][-1], c, "ordinal", "", [], "")
        invalid = copy.deepcopy(store.state)
        invalid["datasets"][-1]["semantic_metadata"] = {"unknown": {}}
        with pytest.raises(ProjectError):
            validate_state(invalid)
        with open(req["path"], "ab") as stream:
            stream.write(b"mutated")
        with pytest.raises(ProjectError, match="snapshot"):
            page(req, ViewSpec())
        with pytest.raises(ProjectError, match="snapshot"):
            profile(req, ProfileSpec(c), work)


def test_ordinal_metadata_parent_integrity_and_nested_boundary(tmp_path):
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"grade": ["düşük", "yüksek"], "nested": [[1, 2], None]})
    )
    with closing(store):
        old = store.state["datasets"][-1]
        c = column(request, "grade")
        new = metadata_version(
            old, c, "ordinal", "", ["düşük", "orta", "yüksek"], "kişi"
        )
        store.state["datasets"].append(new)
        validate_state(store.state)
        invalid = copy.deepcopy(store.state)
        invalid["datasets"][0]["parent_version_ids"] = [new["version_id"]]
        with pytest.raises(ProjectError, match="parent"):
            validate_state(invalid)
        store.save()
        p = profile(request, ProfileSpec(column(request, "nested"), sample=False), work)
        assert p["unique"] is None and p["counts"]["null"] == 1 and p["warnings"]
    with closing(ProjectStore.open(tmp_path / "project")) as reopened:
        assert reopened.state["datasets"][-1]["semantic_metadata"][c][
            "ordinal_order"
        ] == ["düşük", "orta", "yüksek"]


def test_wide_page_payload_is_bounded_and_identical_rows_distinct(tmp_path):
    frame = pl.DataFrame({f"col{i}": ["İ" * 512] * 200 for i in range(90)})
    store, request, _ = prepare(tmp_path, frame)
    with closing(store):
        result = page(request, ViewSpec())
        assert result["payload_bytes"] <= 4 * 1024 * 1024
        assert (
            len(set(result["row_ids"])) == len(set(result["source_record_ids"])) == 200
        )
        assert all(len(cell) <= 256 for row in result["rows"] for cell in row)


def test_mid_profile_mutation_discards_mixed_version(tmp_path):
    store, request, work = prepare(tmp_path, pl.DataFrame({"value": [1, 2, 3]}))
    with closing(store):

        def mutate(phase, done, total):
            with open(request["path"], "ab") as stream:
                stream.write(b"changed-during-profile")

        with pytest.raises(ProjectError, match="snapshot"):
            profile(
                request,
                ProfileSpec(column(request, "value"), sample=False),
                work,
                Control(progress=mutate),
            )
        assert not list(work.glob("profile-*.sqlite"))
