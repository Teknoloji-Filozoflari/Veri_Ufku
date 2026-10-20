"""Model inspection references, original mapping, source scope, fairness and masking."""

import copy
import json
from contextlib import closing

import numpy as np
import polars as pl
import pytest
from test_dataset import column
from test_model_families import fixture as family_fixture
from test_validation import setup_run

from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.baseline import calculate as train
from veri_ufku.modeling.explanation import (
    ExplainSpec,
    calculate,
    feature_mapping,
    redacted_export,
)
from veri_ufku.modeling.lifecycle import load_package
from veri_ufku.storage.explanation_store import load, publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.validation_store import complete


def setup(tmp_path, classification=False, family=None, structure="independent"):
    if family:
        store, r, work, protocol = family_fixture(
            tmp_path, "classification" if classification else "regression", family
        )
    else:
        import test_validation as helper

        original_fixture = helper.fixture
        helper.fixture = lambda: (
            original_fixture().with_columns(
                (
                    2 * pl.col("x")
                    + pl.when(pl.col("cat") == "A").then(3.0).otherwise(0.0)
                ).alias("y")
            )
            if not classification
            else original_fixture().with_columns(
                pl.when(pl.col("x") >= 40)
                .then(pl.lit("risk"))
                .otherwise(pl.lit("normal"))
                .alias("y")
            )
        )
        try:
            store, r, work, protocol = setup_run(tmp_path, structure, classification)
        finally:
            helper.fixture = original_fixture
        if classification:
            r["classification"] = dict(
                candidates=["baseline", "logistic"],
                positive_class="risk",
                threshold_mode="default",
            )
        else:
            r["regression"] = dict(candidates=["baseline", "linear", "ridge"])
    result = train(r, protocol.data(), work)
    model, card = load_package(result["model_package"]["path"])
    return store, r, work, protocol, result, model, card


def run(r, model, card, method, **options):
    frame = pl.read_parquet(r["path"])

    spec = ExplainSpec(method=method, **options)
    return calculate(
        model,
        card,
        frame,
        frame,
        r,
        r,
        spec.data(),
        Control(),
        dict(size=5, sha256="f" * 64),
    )


@pytest.mark.parametrize(
    "method",
    ["permutation", "pdp", "ice", "local-linear", "slices", "what-if", "constrained"],
)
def test_real_native_method_scope_source_and_mapping(tmp_path, method):
    store, r, work, protocol, result, model, card = setup(tmp_path)
    with closing(store):
        original = pl.read_parquet(r["path"])
        x = column(r, "x")
        cat = column(r, "cat")
        rid = card["split"]["membership"]["validation"][0]
        options = dict(features=[x]) if method in ("pdp", "ice") else {}
        if method in ("local-linear", "what-if", "constrained"):
            options["local_row_id"] = rid
        if method == "what-if":
            options["changes"] = {x: 200.0}
        if method == "constrained":
            options.update(
                immutable_features=[cat],
                constraints={
                    x: dict(values=[10.0, 30.0, 50.0], direction="any", cost=1.0)
                },
                desired_min=-100.0,
                desired_max=100.0,
            )
        report = run(r, model, card, method, **options)
        p = report["provenance"]
        assert p["fit_calls"] == 0 and set(p["evaluation_row_ids"]) <= set(
            card["split"]["membership"]["validation"]
        )
        assert not set(p["evaluation_row_ids"] + p["background_row_ids"]) & set(
            card["split"]["membership"]["test"]
        )
        assert report["feature_mapping"]
        assert pl.read_parquet(r["path"]).equals(original)
        if method == "ice":
            np.testing.assert_allclose(
                np.array([v["values"] for v in report["ice"]]).mean(axis=0),
                report["pdp"]["mean"],
            )
        if method == "local-linear":
            assert report["local"]["baseline"] + sum(
                v["value"] for v in report["local"]["contributions"]
            ) == pytest.approx(report["local"]["prediction"])
        if method == "what-if":
            assert (
                report["what_if"]["diagnostics"]["features"][0]["outside_background_n"]
                == 1
            )
        if method == "constrained":
            assert report["constrained"]["matching_count"] > 0


@pytest.mark.parametrize("family", ["decision_tree", "hist_gradient", "stacking"])
def test_family_mapping_matches_actual_transformation(tmp_path, family):
    store, r, work, protocol, result, model, card = setup(tmp_path, family=family)
    with closing(store):
        report = run(r, model, card, "permutation")
        assert {m["column_id"] for m in report["feature_mapping"]} == {
            f["id"] for f in card["features"]
        }
        assert len(
            {(m["component"], m["index"]) for m in report["feature_mapping"]}
        ) == len(report["feature_mapping"])


def test_local_exact_independent_reference_and_permutation_repeat_reference(tmp_path):
    store, r, work, protocol, result, model, card = setup(tmp_path)
    with closing(store):
        rid = card["split"]["membership"]["validation"][0]
        report = run(r, model, card, "local-linear", local_row_id=rid)
        frame = pl.read_parquet(r["path"])
        row = frame.filter(pl.col("__vu_row_id") == rid)
        bg = frame.filter(
            pl.col("__vu_row_id").is_in(report["provenance"]["background_row_ids"])
        )
        prep = model.named_steps["prepare"]
        base = model.named_steps["baseline"]
        contributions = (
            prep.transform(row)[0] - prep.transform(bg).mean(axis=0)
        ) * base.coef_
        np.testing.assert_allclose(
            [c["value"] for c in report["local"]["transformed_contributions"]],
            contributions,
        )
        assert report["local"]["prediction"] == pytest.approx(model.predict(row)[0])
        importance = run(r, model, card, "permutation", repeats=3)
        sample = frame.filter(
            pl.col("__vu_row_id").is_in(importance["provenance"]["evaluation_row_ids"])
        )
        y = sample["y"].to_numpy()
        base = -np.mean(abs(model.predict(sample) - y))
        rng = np.random.default_rng(51)
        for f, row in zip(
            card["features"], importance["permutation"]["values"], strict=True
        ):
            references = []
            for _ in range(3):
                shuffled = sample.with_columns(
                    sample[f["name"]].gather(rng.permutation(len(sample)).tolist())
                )
                references.append(
                    float(base + np.mean(abs(model.predict(shuffled) - y)))
                )
            np.testing.assert_allclose(references, row["repeat_values"])


def test_reference_pdp_ice_and_explicit_extrapolation(tmp_path):
    store, r, work, protocol, result, model, card = setup(tmp_path)
    with closing(store):
        x = column(r, "x")
        report = run(r, model, card, "ice", features=[x], grid=[0.0, 20.0, 1000.0])
        frame = pl.read_parquet(r["path"]).filter(
            pl.col("__vu_row_id").is_in(report["provenance"]["evaluation_row_ids"])
        )
        reference = np.column_stack(
            [
                model.predict(frame.with_columns(pl.lit(v).alias("x")))
                for v in (0.0, 20.0, 1000.0)
            ]
        )
        np.testing.assert_allclose(
            reference, np.array([v["values"] for v in report["ice"]])
        )
        assert report["pdp"]["outside_background_grid_n"] >= 1


def test_small_group_range_time_slices_and_no_iid_ci_for_group_time(tmp_path):
    store, r, work, protocol, result, model, card = setup(
        tmp_path, structure="group_time"
    )
    with closing(store):
        report = run(
            r,
            model,
            card,
            "slices",
            slices=[
                dict(column_id=column(r, "group"), kind="group"),
                dict(column_id=column(r, "x"), kind="range", edges=[0.0, 40.0, 100.0]),
                dict(
                    column_id=column(r, "when"),
                    kind="time",
                    edges=[1704067200.0, 1707523200.0, 1714435200.0],
                ),
            ],
        )
        assert report["slices"] and all(
            v["uncertainty"] is None for v in report["slices"]
        )
        assert any(v["small_group"] and v["n"] for v in report["slices"])
        for group in report["slices"]:
            assert group["n"] == len(group["row_ids"])


def test_sensitive_redaction_fail_closed_and_explicit_selection(tmp_path):
    store, r, work, protocol, result, model, card = setup(tmp_path)
    with closing(store):
        cat = column(r, "cat")
        rid = card["split"]["membership"]["validation"][0]
        report = run(
            r, model, card, "local-linear", local_row_id=rid, sensitive_columns=[cat]
        )
        out = redacted_export(report)
        raw = json.dumps(out)
        assert "local" not in out and cat not in raw and rid not in raw
        report = run(
            r,
            model,
            card,
            "slices",
            slices=[dict(column_id=cat, kind="group")],
            sensitive_columns=[cat],
        )
        out = redacted_export(report)
        assert out["slices"] == []
        report = run(r, model, card, "permutation", sensitive_columns=[column(r, "x")])
        assert all(
            v["name"] != "x" for v in redacted_export(report)["permutation"]["values"]
        )
        with pytest.raises(ProjectError):
            run(r, model, card, "fairness")


def test_support_gate_optional_shap_and_local_invalid_model(tmp_path):
    store, r, work, protocol, result, model, card = setup(
        tmp_path, family="decision_tree"
    )
    with closing(store):
        with pytest.raises(ProjectError, match="Exact local"):
            run(
                r,
                model,
                card,
                "local-linear",
                local_row_id=card["split"]["membership"]["validation"][0],
            )
        import importlib.util

        if importlib.util.find_spec("shap") is None:
            with pytest.raises(ProjectError, match="Optional SHAP"):
                ExplainSpec.from_dict(dict(method="shap"))
        with pytest.raises(ProjectError, match="immutable"):
            run(
                r,
                model,
                card,
                "constrained",
                local_row_id=card["split"]["membership"]["validation"][0],
            )


def test_atomic_store_reopen_tamper_and_journal(tmp_path):
    store, r, work, protocol, result, model, card = setup(tmp_path)
    with closing(store):
        from veri_ufku.storage.project_store import ProjectStore

        # Adopt actual model through the existing baseline transaction.
        store.state = complete(store, store.state, result)

        frame = pl.read_parquet(r["path"])
        report = calculate(
            model,
            card,
            frame,
            frame,
            r,
            r,
            ExplainSpec(method="ice", features=[column(r, "x")]).data(),
            Control(),
            result["model_package"]["fingerprint"],
        )
        store.state = publish(store, store.state, report)
        record = next(v for v in store.state["results"] if "explanation" in v)
        assert load(store, record) == report
        root = store.root
        tampered = copy.deepcopy(report)
        tampered["feature_mapping"][0]["column_id"] = "col:wrong"
        with pytest.raises(ProjectError):
            publish(store, store.state, tampered)
        assert load(store, record) == report
    with closing(ProjectStore.open(root)) as reopened:
        record = next(v for v in reopened.state["results"] if "explanation" in v)
        assert load(reopened, record) == report


def test_hand_fairness_counts_disparities_wilson_and_mask():
    from veri_ufku.modeling.explanation import fairness_report, wilson

    frame = pl.DataFrame(
        {
            "__vu_row_id": ["r0", "r1", "r2", "r3", "r4", "r5"],
            "protected": [
                "secret-A",
                "secret-A",
                "secret-A",
                "secret-B",
                "secret-B",
                None,
            ],
        }
    )
    card = dict(
        purpose="classification",
        label_order=["no", "yes"],
        columns=[dict(id="col:s", name="protected")],
        target=dict(id="col:y"),
        split=dict(method="random"),
    )
    spec = ExplainSpec(
        method="fairness", sensitive_columns=["col:s"], positive_class="yes"
    )
    actual = np.array(["yes", "yes", "no", "yes", "no", "no"])
    pred = np.array(["yes", "no", "yes", "yes", "no", "no"])
    result = fairness_report(frame, actual, pred, card, spec)
    a = next(v for v in result["groups"] if v["label"] == "secret-A")
    b = next(v for v in result["groups"] if v["label"] == "secret-B")
    assert (a["tp"], a["fp"], a["fn"], a["tn"]) == (1, 1, 1, 0)
    assert a["tpr"] == 0.5 and a["fpr"] == 1 and a["precision"] == 0.5
    assert (b["tp"], b["fp"], b["fn"], b["tn"]) == (1, 0, 0, 1)
    assert result["disparities"][0]["equalized_odds_difference"] == 1
    assert result["disparities"][0]["demographic_parity_difference"] == pytest.approx(
        2 / 3
    )
    assert wilson(0, 0) is None
    assert wilson(1, 1)["lower"] < 1 and wilson(1, 1)["upper"] <= 1 + 1e-12
    # A real '<missing>' label must not get mistaken for missing values.
    collision = frame.with_columns(
        pl.when(pl.col("protected") == "secret-A")
        .then(pl.lit("<missing>"))
        .otherwise(pl.col("protected"))
        .alias("protected")
    )
    report = fairness_report(collision, actual, pred, card, spec)
    assert sum(g["n"] for g in report["groups"]) == len(frame)
    assert next(g for g in report["groups"] if g["label"] is None)["n"] == 1


def test_sampling_budget_and_missing_background_values(tmp_path):
    store, r, work, protocol, result, model, card = setup(tmp_path)
    with closing(store):
        report = run(r, model, card, "permutation", sample_rows=5, background_rows=4)
        assert report["provenance"]["sampled"] and report["provenance"]["n"] == 5
        assert report["provenance"]["background_n"] == 4
        assert report["provenance"]["compute_budget"]["device"] == "cpu"
        assert (
            report["provenance"]["common"]["capability_id"]
            == "model.explain.permutation"
        )
        again = run(r, model, card, "permutation", sample_rows=5, background_rows=4)
        assert report["permutation"] == again["permutation"]
        assert (
            report["provenance"]["evaluation_row_ids"]
            == again["provenance"]["evaluation_row_ids"]
        )
        with pytest.raises(ProjectError, match="bütçe"):
            ExplainSpec.from_dict(dict(sample_rows=501))


def test_constrained_immutable_direction_and_domain_limits(tmp_path):
    store, r, work, protocol, result, model, card = setup(tmp_path)
    with closing(store):
        rid = card["split"]["membership"]["validation"][0]
        x = column(r, "x")
        cat = column(r, "cat")
        frame = pl.read_parquet(r["path"])
        original = frame.filter(pl.col("__vu_row_id") == rid)["x"][0]
        options = dict(
            local_row_id=rid,
            immutable_features=[cat],
            constraints={
                x: dict(values=[5.0, 30.0, 50.0], direction="increase", cost=1.0)
            },
            desired_min=-100.0,
            desired_max=500.0,
        )
        out = run(r, model, card, "constrained", **options)
        assert all(
            v["changes"][x] >= original for v in out["constrained"]["candidates"]
        )
        options["constraints"][x]["values"] = [10000.0]
        with pytest.raises(ProjectError, match="background observed"):
            run(r, model, card, "constrained", **options)
        options["immutable_features"] = [x, cat]
        with pytest.raises(ProjectError, match="immutable"):
            run(r, model, card, "constrained", **options)


def test_atomic_failure_source_metrics_tamper_and_old_journal_guard(tmp_path):
    store, r, work, protocol, result, model, card = setup(tmp_path)
    with closing(store):
        store.state = complete(store, store.state, result)
        frame = pl.read_parquet(r["path"])
        report = calculate(
            model,
            card,
            frame,
            frame,
            r,
            r,
            ExplainSpec(method="slices").data(),
            Control(),
            result["model_package"]["fingerprint"],
        )
        state = copy.deepcopy(store.state)
        store.state = publish(store, store.state, report)
        tamper = copy.deepcopy(report)
        tamper["slices"][0]["value"] = 123.0
        from veri_ufku.modeling.validation import digest

        tamper["identity"] = "explanation:" + digest(
            {k: v for k, v in tamper.items() if k != "identity"}
        )
        with pytest.raises(ProjectError, match="slice metric"):
            publish(store, store.state, tamper)
        with pytest.raises(ProjectError, match="defteri silinemez"):
            publish(store, state, report)
        assert sum("explanation" in r for r in store.state["results"]) == 1


def test_correlated_missing_diagnostics_and_group_uncertainty():
    from veri_ufku.modeling.explanation import diagnostic_columns, slice_metrics

    sample = pl.DataFrame(
        dict(
            x=[1.0, 2.0, 3.0, 4.0, None],
            z=[2.0, 4.0, 6.0, 8.0, 10.0],
            cat=["a", "a", "b", None, "unseen"],
        )
    )
    bg = pl.DataFrame(dict(x=[1.0, 2.0, 3.0], z=[2.0, 4.0, 6.0], cat=["a", "b", "a"]))
    card = dict(
        features=[
            dict(id="col:x", name="x"),
            dict(id="col:z", name="z"),
            dict(id="col:c", name="cat"),
        ]
    )
    out = diagnostic_columns(sample, bg, card)
    assert (
        out["features"][0]["missing_n"] == 1
        and out["features"][0]["outside_background_n"] == 1
    )
    assert (
        out["features"][2]["unknown_category_n"] == 1
        and out["features"][2]["missing_n"] == 1
    )
    assert out["correlated_pairs"][0]["pearson"] == pytest.approx(1)
    score = slice_metrics(
        np.array([0.0, 1.0, 2.0]),
        np.array([0.0, 1.0, 3.0]),
        False,
        "group_time",
        100,
        51,
    )
    assert score["uncertainty"] is None and score["small_group"]


def test_cancel_and_prediction_budget_control(tmp_path):
    import threading

    from veri_ufku.jobs.workers import Canceled
    from veri_ufku.modeling.explanation import PredictionBudget

    event = threading.Event()
    event.set()
    with pytest.raises(Canceled):
        PredictionBudget(Control(event)).check(1)
    budget = PredictionBudget(Control(), maximum=10)
    budget.check(10)
    with pytest.raises(ProjectError, match="ComputeBudget"):
        budget.check(1)
    assert budget.rows == 10 and budget.calls == 1


def test_original_column_onehot_and_variance_mask_reference(tmp_path):
    store, r, work, protocol, result, model, card = setup(tmp_path)
    with closing(store):
        sample = pl.read_parquet(r["path"]).head(2)
        rows = feature_mapping(model, card, sample)
        assert [m["column_id"] for m in rows] == [
            column(r, "x"),
            column(r, "cat"),
            column(r, "cat"),
        ]
        assert len(rows) == model.named_steps["prepare"].transform(sample).shape[1]
        # Raw categorical ICE varies whole feature, never independently toggles dummy columns.
        out = run(r, model, card, "ice", features=[column(r, "cat")], grid=["A", "B"])
        assert not out["pdp"]["numeric_axis"]
        np.testing.assert_allclose(
            np.array([v["values"] for v in out["ice"]]).mean(axis=0), out["pdp"]["mean"]
        )


def test_final_refit_and_other_background_rejected(tmp_path):
    store, r, work, protocol, result, model, card = setup(tmp_path)
    with closing(store):
        frame = pl.read_parquet(r["path"])
        bad = dict(r, version_id="dv:other")
        with pytest.raises(ProjectError, match="aynı immutable"):
            calculate(
                model,
                card,
                frame,
                frame,
                r,
                bad,
                ExplainSpec().data(),
                Control(),
                {"size": 5, "sha256": "f" * 64},
            )
        frozen = copy.deepcopy(card)
        frozen["fit_scope"] = "development_train_plus_validation"
        with pytest.raises(ProjectError, match="Final refitted"):
            calculate(
                model,
                frozen,
                frame,
                frame,
                r,
                r,
                ExplainSpec().data(),
                Control(),
                {"size": 5, "sha256": "f" * 64},
            )


def test_archived_export_requires_no_model_deserialize_or_network(
    tmp_path, monkeypatch
):
    store, r, work, protocol, result, model, card = setup(tmp_path)
    with closing(store):
        report = run(
            r, model, card, "permutation", sensitive_columns=[column(r, "cat")]
        )
        import veri_ufku.modeling.lifecycle as lifecycle
        from veri_ufku.modeling.lifecycle_worker import calculate as worker

        monkeypatch.setattr(
            lifecycle, "load_package", lambda *a: pytest.fail("export imported model")
        )
        import socket

        monkeypatch.setattr(
            socket,
            "create_connection",
            lambda *a, **k: pytest.fail("offline export made network request"),
        )
        dest = work / "archived-masked.json"
        out = worker(
            dict(package="/missing/model", explanation=report, destination=str(dest)),
            "explain-export",
            work,
            Control(),
        )
        assert (
            out["output"] == str(dest)
            and json.loads(dest.read_text())["schema"] == "ExplanationExport/v1"
        )
        assert column(r, "cat") not in dest.read_text()
