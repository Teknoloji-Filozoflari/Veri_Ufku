"""Phase32 independent quality, approval, identity and atomic persistence witnesses."""

import copy
import threading
from contextlib import closing

import polars as pl
import pytest
from test_dataset import column, prepare
from test_operations import request_for

from veri_ufku.analytics.contracts import ViewSpec, metadata_version
from veri_ufku.analytics.dataset import page
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.operations.contracts import active_datasets, build, move
from veri_ufku.operations.data_contracts import contract_validate
from veri_ufku.operations.engine import calculate
from veri_ufku.storage.project_model import ProjectError, uid, validate_state
from veri_ufku.storage.project_store import ProjectStore


def rule(kind, col="", **parameters):
    return dict(
        id=kind + ":" + col,
        kind=kind,
        column_id=col,
        severity="error",
        parameters=parameters,
    )


def contract(*rules):
    return dict(schema_version=1, rules=list(rules))


def approved():
    return dict(
        approved=True,
        reviewer="Sentetik inceleyen",
        reason="Fixture bağımsız müşteri koduyla doğrulandı; ad tek başına yeterli değil.",
        at="2026-10-11T12:00:00+03:00",
    )


def run(request, kind, p, work, selected=()):
    return calculate(request, build(request, kind, selected, p), work)


def test_schema_additive_version_ordinal_and_roundtrip(tmp_path):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame({"level": ["high", "low", "mid", "low"], "weight": [1, 2, 3, 4]}),
    )
    with closing(store):
        col = column(request, "level")
        weight = column(request, "weight")
        meta = metadata_version(
            store.state["datasets"][-1],
            col,
            "ordinal",
            "",
            ["low", "mid", "high"],
            "person",
            "Ordered label",
        )
        semantics = meta["semantic_metadata"]
        semantics[col]["measurement_level"] = "ordinal"
        semantics[weight] = dict(
            role="measurement",
            unit="kg",
            ordinal_order=[],
            confirmed=True,
            description="Mass",
            measurement_level="ratio",
        )
        definition = contract(
            rule("ordinal", col, order=["low", "mid", "high"]),
            rule("unit", weight, expected="kg"),
        )
        result = run(
            request,
            "schema_contract",
            dict(
                contract=definition, semantic_metadata=semantics, analysis_unit="person"
            ),
            work,
        )
        dataset = store.publish_operation(result)
        assert dataset["schema_contract"]["dataset_version"] == dataset["version_id"]
        assert dataset["semantic_metadata"][weight]["unit"] == "kg"
        assert dataset["semantic_metadata"][col]["ordinal_order"] == [
            "low",
            "mid",
            "high",
        ]
        current = dict(
            request_for(store, dataset), semantic_metadata=dataset["semantic_metadata"]
        )
        ordered = page(current, ViewSpec(sort_column=col))
        assert [r[0] for r in ordered["rows"]] == ["low", "low", "mid", "high"]
        original_ids = pl.read_parquet(request["path"])["__vu_row_id"].to_list()
        assert pl.read_parquet(current["path"])["__vu_row_id"].to_list() == original_ids
        note = metadata_version(
            dataset, weight, "measurement", "kg", [], "person", "New note"
        )
        assert note["semantic_metadata"][weight]["measurement_level"] == "ratio"
        assert note["schema_contract"]["status"] == "requires_validation"
        root = store.root
    with closing(ProjectStore.open(root)) as reopened:
        validate_state(reopened.state)
        assert active_datasets(reopened.state)[0]["semantic_metadata"] == semantics
        reopened.save_as(tmp_path / "portable")
    with closing(ProjectStore.open(tmp_path / "portable")) as portable:
        assert (
            active_datasets(portable.state)[0]["schema_contract"]["definition"]
            == definition
        )


def test_wrong_unit_type_keys_range_policy_quarantine_and_stop(tmp_path):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame({"key": ["a", "a", "c", None], "amount": [1, 900, 3, None]}),
    )
    with closing(store):
        key, amount = column(request, "key"), column(request, "amount")
        definition = contract(
            rule("unique", key, nulls_equal=False),
            rule("range", amount, minimum="0", maximum="10"),
            rule("nullable", amount, allowed=False),
        )
        result = run(
            request, "contract_check", dict(contract=definition, policy="stop"), work
        )
        report = result["diagnostics"]["contract_report"]
        assert [r["violations"] for r in report["rules"]] == [2, 1, 1]
        assert len(report["rules"][0]["examples"]) == 2
        assert {r["level"] for r in report["rules"]} == {"column", "row"}
        active = (store.base / "ACTIVE").read_bytes()
        with pytest.raises(ProjectError, match="出版|yayın"):
            store.publish_operation(result)
        assert (store.base / "ACTIVE").read_bytes() == active
        quarantined = run(
            request,
            "contract_check",
            dict(contract=definition, policy="quarantine"),
            work,
        )
        assert quarantined["impact"]["after_rows"] == 1
        assert quarantined["diagnostics"]["relation_rows"] == 3
        d = store.publish_operation(quarantined)
        assert d.get("lineage_uri")
        assert pl.read_parquet(store.path(d["lineage_uri"]))["amount"].to_list() == [
            1,
            900,
            None,
        ]
        assert pl.read_parquet(store.path(d["snapshot_uri"]))["key"].to_list() == ["c"]
        move(store.state, d["dataset_id"], "undo")
        store.save()
        assert active_datasets(store.state)[0]["version_id"] == request["version_id"]
        wrong = contract(
            rule("type", amount, expected="String"),
            rule("unit", amount, expected="kg"),
            rule("row_count", minimum=10, maximum=20),
        )
        wrong["rules"][2]["severity"] = "warning"
        result = run(
            request, "contract_check", dict(contract=wrong, policy="quarantine"), work
        )
        assert result["diagnostics"]["contract_report"]["error_violations"] == 8
        assert result["diagnostics"]["contract_report"]["warning_violations"] == 4
        assert result["diagnostics"]["publication_allowed"] is False
        continued = run(
            request, "contract_check", dict(contract=wrong, policy="continue"), work
        )
        output = store.publish_operation(continued)
        assert pl.read_parquet(store.path(output["snapshot_uri"])).equals(
            pl.read_parquet(request["path"])
        )
        assert output["schema_contract"]["status"] == "checked"


def test_foreign_keys_actual_second_version_no_implicit_cast(tmp_path):
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"fk": ["a", "missing", None]})
    )
    second_dir = tmp_path / "second"
    second_dir.mkdir()
    reference, other, _ = prepare(second_dir, pl.DataFrame({"pk": ["a", "b"]}))
    with closing(store), closing(reference):
        # Import the reference through the existing importer, not a second state registry.
        from veri_ufku.importers.delimited import capture
        from veri_ufku.importers.native import StructuredSettings
        from veri_ufku.importers.registry import get_adapter

        imported = get_adapter("parquet").import_data(
            capture(second_dir / "source.parquet", work, any_format=True),
            StructuredSettings(adapter_id="parquet"),
            work,
            Control(),
        )
        second = store.publish_import(imported)
        other = request_for(store, second)
        request["secondary"] = other
        definition = contract(
            rule(
                "foreign_key",
                column(request, "fk"),
                version_id=other["version_id"],
                column_id=column(other, "pk"),
                nullable=True,
            )
        )
        result = run(
            request,
            "contract_check",
            dict(contract=definition, policy="continue"),
            work,
        )
        assert result["diagnostics"]["contract_report"]["rules"][0]["violations"] == 1
        assert (
            result["diagnostics"]["contract_report"]["rules"][0]["level"]
            == "cross_table"
        )
        d = store.publish_operation(result)
        assert d["input_version_ids"] == [request["version_id"], other["version_id"]]
        root = store.root
    with closing(ProjectStore.open(root)) as reopened:
        assert (
            reopened.state["operations"][-1]["spec"]["parameters"]["contract"]
            == definition
        )


def test_entity_no_unapproved_merge_blocks_and_undo_all_source_ids(tmp_path):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "name": ["Ada Lee", "Ada Lea", "Ada Lee", "different"],
                "town": ["X", "X", "Y", "X"],
            }
        ),
    )
    source_bytes = (tmp_path / "source.parquet").read_bytes()
    original = pl.read_parquet(request["path"])
    with closing(store):
        params = dict(
            name_column=column(request, "name"),
            block_column=column(request, "town"),
            threshold=0.8,
        )
        preview = run(request, "entity_candidates", params, work)
        assert len(preview["diagnostics"]["candidates"]) == 1
        candidate = preview["diagnostics"]["candidates"][0]
        assert candidate["left_source"] != candidate["right_source"]
        with pytest.raises(ProjectError):
            store.publish_operation(preview)
        merge = dict(
            params,
            pairs=[[candidate["left"], candidate["right"]]],
            canonical_column="col:" + uid(),
            approval=approved(),
        )
        invalid = copy.deepcopy(merge)
        invalid["approval"]["approved"] = False
        with pytest.raises(ProjectError, match="onay|geçersiz"):
            run(request, "entity_merge", invalid, work)
        invalid = copy.deepcopy(merge)
        invalid["pairs"] = [[original["__vu_row_id"][0], original["__vu_row_id"][2]]]
        with pytest.raises(ProjectError, match="blocking"):
            run(request, "entity_merge", invalid, work)
        store.state["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=[request["version_id"]],
                seed=None,
            )
        )
        result = run(request, "entity_merge", merge, work)
        dataset = store.publish_operation(result)
        frame = pl.read_parquet(store.path(dataset["snapshot_uri"]))
        assert frame["canonical_id"][0] == frame["canonical_id"][1]
        assert frame["canonical_id"][0] != frame["canonical_id"][2]
        assert frame["__vu_source_record_id"].equals(original["__vu_source_record_id"])
        assert frame["__vu_row_id"].equals(original["__vu_row_id"])
        assert frame.height == original.height
        assert store.state["operations"][-1]["diagnostics"]["approval"] == approved()
        assert store.state["results"][-1]["dataset_version_ids"] == [
            request["version_id"]
        ]
        move(store.state, dataset["dataset_id"], "undo")
        store.save()
        restored = active_datasets(store.state)[0]
        assert pl.read_parquet(store.path(restored["snapshot_uri"])).equals(original)
        assert not restored.get("entity_resolution")
        move(store.state, dataset["dataset_id"], "redo")
        store.save()
        root = store.root
    with closing(ProjectStore.open(root)) as reopened:
        assert (
            active_datasets(reopened.state)[0]["entity_resolution"][
                "decision_operation"
            ]
            == result["spec"]["id"]
        )
    assert (tmp_path / "source.parquet").read_bytes() == source_bytes


def test_categories_manual_mapping_and_cancel(tmp_path):
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"category": ["Ankara", "Ankra", "Izmir", None]})
    )
    with closing(store):
        col = column(request, "category")
        preview = run(request, "category_candidates", dict(threshold=0.7), work, [col])
        assert preview["diagnostics"]["category_candidates"][0][
            "score"
        ] == pytest.approx(10 / 11)
        assert pl.read_parquet(preview["path"]).equals(pl.read_parquet(request["path"]))
        result = run(
            request,
            "category_map",
            dict(mapping={"Ankra": "Ankara"}, approval=approved()),
            work,
            [col],
        )
        d = store.publish_operation(result)
        assert pl.read_parquet(store.path(d["snapshot_uri"]))["category"].to_list() == [
            "Ankara",
            "Ankara",
            "Izmir",
            None,
        ]
        event = threading.Event()
        event.set()
        with pytest.raises(Canceled):
            calculate(
                request,
                build(request, "category_candidates", [col], {"threshold": 0.7}),
                work,
                Control(event),
            )


@pytest.mark.parametrize(
    "bad",
    [
        dict(schema_version=99, rules=[]),
        dict(schema_version=1, rules=[{"kind": "eval"}]),
        dict(schema_version=1, rules=[rule("nullable", "col:" + uid(), allowed=False)]),
    ],
)
def test_closed_declarative_recipe_rejects_unknowns(bad):
    with pytest.raises(ProjectError):
        contract_validate(bad, [])


def test_overlapping_merge_canonical_changes_inverse_and_linked_results(tmp_path):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {"name": ["Ada Lee", "Ada Lea", "Ada Li", "Ada Lei"], "town": ["X"] * 4}
        ),
    )
    with closing(store):
        params = dict(
            name_column=column(request, "name"),
            block_column=column(request, "town"),
            threshold=0.5,
        )
        original = pl.read_parquet(request["path"])
        rows = original["__vu_row_id"].to_list()
        canonical = "col:" + uid()
        first = run(
            request,
            "entity_merge",
            dict(
                params,
                pairs=[[rows[0], rows[1]], [rows[2], rows[3]]],
                canonical_column=canonical,
                approval=approved(),
            ),
            work,
        )
        d1 = store.publish_operation(first)
        f1 = pl.read_parquet(store.path(d1["snapshot_uri"]))
        assert f1["canonical_id"].n_unique() == 2
        linked = dict(
            id="result:" + uid(), dataset_version_ids=[d1["version_id"]], seed=None
        )
        store.state["results"].append(linked)
        req2 = dict(request_for(store, d1), entity_resolution=d1["entity_resolution"])
        second = run(
            req2,
            "entity_merge",
            dict(
                params,
                pairs=[[rows[1], rows[2]]],
                canonical_column=canonical,
                approval=approved(),
            ),
            work,
        )
        d2 = store.publish_operation(second)
        f2 = pl.read_parquet(store.path(d2["snapshot_uri"]))
        assert f2["canonical_id"].n_unique() == 1
        inverse = pl.read_parquet(store.path(d2["lineage_uri"]))
        assert (
            inverse["previous_canonical_id"].to_list() == f1["canonical_id"].to_list()
        )
        assert inverse["canonical_id"].to_list() == f2["canonical_id"].to_list()
        assert (
            inverse["source_record_id"].to_list()
            == original["__vu_source_record_id"].to_list()
        )
        assert inverse["input_version_id"].unique().to_list() == [d1["version_id"]]
        move(store.state, d2["dataset_id"], "undo")
        store.save()
        assert active_datasets(store.state)[0]["version_id"] == d1["version_id"]
        assert store.state["results"][-1] == linked
        assert (
            sum(
                o.get("spec", {}).get("kind") == "entity_merge"
                for o in store.state["operations"]
            )
            == 2
        )
        root = store.root
    with closing(ProjectStore.open(root)) as reopened:
        current = active_datasets(reopened.state)[0]
        assert pl.read_parquet(reopened.path(current["snapshot_uri"])).equals(f1)


def test_publication_rechecks_diagnostics_and_approved_values(tmp_path):
    store, request, work = prepare(tmp_path, pl.DataFrame({"amount": [1, 99]}))
    with closing(store):
        col = column(request, "amount")
        p = dict(
            contract=contract(rule("range", col, minimum="0", maximum="10")),
            policy="stop",
        )
        result = run(request, "contract_check", p, work)
        result["diagnostics"]["publication_allowed"] = True
        active = (store.base / "ACTIVE").read_bytes()
        with pytest.raises(ProjectError, match="yeniden doğrulanamadı"):
            store.publish_operation(result)
        assert (store.base / "ACTIVE").read_bytes() == active
        p["policy"] = "continue"
        result = run(request, "contract_check", p, work)
        result["diagnostics"]["contract_report"]["rules"][0]["violations"] = 0
        with pytest.raises(ProjectError, match="yeniden doğrulanamadı"):
            store.publish_operation(result)
        assert (store.base / "ACTIVE").read_bytes() == active


def test_wrong_ordinal_metadata_table_error_is_not_quarantined(tmp_path):
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"grade": ["high", "low", "unknown"]})
    )
    with closing(store):
        col = column(request, "grade")
        request["semantic_metadata"] = {
            col: dict(
                role="ordinal", ordinal_order=["high", "low"], confirmed=True, unit=""
            )
        }
        result = run(
            request,
            "contract_check",
            dict(
                contract=contract(rule("ordinal", col, order=["low", "high"])),
                policy="quarantine",
            ),
            work,
        )
        report = result["diagnostics"]["contract_report"]
        assert report["rules"][0]["violations"] == 1
        assert "sıra" in report["rules"][0]["reason"]
        assert (
            report["unquarantinable"]
            and not result["diagnostics"]["publication_allowed"]
        )


def test_quality_empty_table_and_null_uniqueness(tmp_path):
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"id": [None, None, "a"]}, schema={"id": pl.String})
    )
    with closing(store):
        col = column(request, "id")
        for nulls_equal, expected in [(True, 2), (False, 0)]:
            result = run(
                request,
                "contract_check",
                dict(
                    contract=contract(rule("unique", col, nulls_equal=nulls_equal)),
                    policy="continue",
                ),
                work,
            )
            assert (
                result["diagnostics"]["contract_report"]["rules"][0]["violations"]
                == expected
            )


def test_range_nonfinite_wrong_bounds_and_empty_filtered_table(tmp_path):
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"amount": [1.0, float("nan"), float("inf"), None]})
    )
    with closing(store):
        col = column(request, "amount")
        p = dict(
            contract=contract(rule("range", col, minimum="0", maximum="10")),
            policy="continue",
        )
        result = run(request, "contract_check", p, work)
        assert result["diagnostics"]["contract_report"]["rules"][0]["violations"] == 2
        p["contract"]["rules"][0]["parameters"] = dict(minimum="10", maximum="0")
        with pytest.raises(ProjectError, match="alt sınır"):
            run(request, "contract_check", p, work)
    empty = tmp_path / "empty"
    empty.mkdir()
    store, request, work = prepare(
        empty, pl.DataFrame({"amount": [1]}, schema={"amount": pl.Int64})
    )
    with closing(store):
        col = column(request, "amount")
        filtered = run(
            request,
            "filter",
            dict(
                filters=[
                    dict(
                        column_id=col,
                        operator="eq",
                        literal=dict(dtype="Int64", text="0"),
                    )
                ]
            ),
            work,
            [col],
        )
        empty_dataset = store.publish_operation(filtered)
        request = request_for(store, empty_dataset)
        assert request["row_count"] == 0
        result = run(
            request,
            "contract_check",
            dict(
                contract=contract(rule("type", col, expected="String")), policy="stop"
            ),
            work,
        )
        assert result["diagnostics"]["contract_report"]["rules"][0]["violations"] == 1
        assert not result["diagnostics"]["publication_allowed"]


def test_canonical_user_field_cannot_be_overwritten_without_previous_decision(tmp_path):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "name": ["Ada Lee", "Ada Lea"],
                "town": ["X", "X"],
                "canonical_id": ["user-key-a", "user-key-b"],
            }
        ),
    )
    with closing(store):
        frame = pl.read_parquet(request["path"])
        p = dict(
            name_column=column(request, "name"),
            block_column=column(request, "town"),
            threshold=0.8,
            pairs=[frame["__vu_row_id"].to_list()],
            canonical_column=column(request, "canonical_id"),
            approval=approved(),
        )
        with pytest.raises(ProjectError, match="kullanıcı sütunu"):
            run(request, "entity_merge", p, work)
        assert pl.read_parquet(request["path"])["canonical_id"].to_list() == [
            "user-key-a",
            "user-key-b",
        ]


@pytest.mark.parametrize(
    "keys, message", [(["a", "a"], "benzersiz"), ([1, 2], "fiziksel tür")]
)
def test_foreign_reference_invalid_key_reports_without_coercion(
    tmp_path, keys, message
):
    store, request, work = prepare(tmp_path, pl.DataFrame({"fk": ["a", "x", None]}))
    target = tmp_path / "target"
    target.mkdir()
    reference, other, _ = prepare(target, pl.DataFrame({"pk": keys}))
    with closing(store), closing(reference):
        request["secondary"] = other
        result = run(
            request,
            "contract_check",
            dict(
                contract=contract(
                    rule(
                        "foreign_key",
                        column(request, "fk"),
                        version_id=other["version_id"],
                        column_id=column(other, "pk"),
                        nullable=False,
                    )
                ),
                policy="quarantine",
            ),
            work,
        )
        report = result["diagnostics"]["contract_report"]
        assert report["rules"][0]["violations"] == 3
        assert message in report["rules"][0]["reason"]
        assert report["unquarantinable"]
        assert not result["diagnostics"]["publication_allowed"]
