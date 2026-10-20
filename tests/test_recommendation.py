"""Independent ranking references, causal-time barriers, typed lineage and safe persistence."""

import copy
import json
import math
import threading
from contextlib import closing
from dataclasses import replace

import numpy as np
import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.recommendation import (
    calculate,
    contexts,
    predict,
    read_rows,
    validate,
)
from veri_ufku.modeling.recommendation_contracts import RecommendationSpec, identity
from veri_ufku.modeling.recommendation_math import als_update, metrics
from veri_ufku.storage.neural_store import load, publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.recommendation_store import export_list


def interactions(ranker=False):
    rr = []
    for j in range(4):
        for i in range(4):
            rr.append(
                dict(
                    user=f"u{j}",
                    item=f"i{i}",
                    strength=float(1 + (i + j) % 2),
                    timestamp=float(i + j + 1),
                    x=float(i % 2),
                    y=float(1 - i % 2),
                    query=f"q{j}",
                )
            )
    if ranker:
        for r in rr:
            j = int(r["user"][1:])
            r["timestamp"] = float(1 + 4 * j)
            r["strength"] = float(int(r["item"][1:]) % 2)
    else:
        rr += [
            dict(
                user="u0",
                item="i2",
                strength=2.0,
                timestamp=20.0,
                x=0.0,
                y=1.0,
                query="q4",
            ),
            dict(
                user="new-sensitive-user",
                item="future-only",
                strength=1.0,
                timestamp=20.0,
                x=1.0,
                y=0.0,
                query="q5",
            ),
        ]
    return pl.DataFrame(rr)


def fixture(tmp_path, task="popularity", **kwargs):
    store, request, work = prepare(tmp_path, interactions(task == "ranker"))
    request.update(
        origin_version=request["version_id"],
        run_id="run:recommendation59",
        prior_test_use_ids=[],
        config_revision=0,
    )
    spec = RecommendationSpec(
        task=task,
        user=column(request, "user"),
        item=column(request, "item"),
        value=column(request, "strength"),
        time=column(request, "timestamp"),
        query=column(request, "query") if task == "ranker" else "",
        features=(column(request, "x"), column(request, "y"))
        if task in ("content", "ranker")
        else (),
        cutoff=8,
        k=2,
        epochs=3,
        seen_filter=kwargs.pop("seen_filter", task != "ranker"),
        **kwargs,
    )
    return store, request, work, spec


def test_hand_metrics_and_empty():
    m = metrics(["bad", "a", "b"], {"a", "b", "c", "d"}, 3)
    assert m["precision"] == 2 / 3
    assert m["recall"] == 0.5
    assert m["ap"] == pytest.approx((1 / 2 + 2 / 3) / 3)
    assert m["ndcg"] == pytest.approx(
        (1 / math.log2(3) + 1 / math.log2(4))
        / (1 + 1 / math.log2(3) + 1 / math.log2(4))
    )
    assert metrics(["a"], {"a"}, 5)["precision"] == 0.2
    assert metrics([], set(), 2) == dict(precision=0, recall=None, ndcg=None, ap=None)
    with pytest.raises(ProjectError):
        metrics(["a", "a"], {"a"}, 2)


def test_typed_ids():
    assert len({identity("001"), identity(1), identity("1")}) == 3
    for bad in (None, True, 1.0, [], ""):
        with pytest.raises(ProjectError):
            identity(bad)


def test_hand_als_explicit_implicit():
    # One factor and two items: explicit missing second item is absent from normal equation.
    other = np.array([[1.0], [2.0]])
    assert als_update(other, np.array([3.0, np.nan]), False, 1, 10)[0] == 1.5
    # Implicit strengths [2,0], alpha2: C=[5,1], p=[1,0], lambda1 => 5/(5+4+1).
    assert als_update(other, np.array([2.0, 0.0]), True, 1, 2)[0] == 0.5


@pytest.mark.parametrize("task", ["popularity", "content", "factorization", "ranker"])
def test_methods_persist_new_ids_source_lineage(tmp_path, task):
    store, request, work, spec = fixture(tmp_path, task)
    with closing(store):
        before = (tmp_path / "source.parquet").read_bytes()
        out = calculate(request, spec.data(), work)
        assert out["status"] == "completed"
        assert out["metrics"]["n_queries"] >= 1
        if task == "factorization":
            losses = out["model_weights"]["model"]["objective"]
            assert all(a >= b - 1e-8 for a, b in zip(losses, losses[1:]))
        state = publish(store, store.state, out)
        record = state["results"][-1]
        opened = load(store, record)
        assert opened == json.loads(json.dumps(out))
        assert record["capability_id"] == "model.recommendation." + task
        if task == "ranker":
            query = dict(
                user="new-sensitive-user",
                items=["i0", "i1"],
                features=[
                    dict(item="i0", values=[0, 1]),
                    dict(item="i1", values=[1, 0]),
                ],
            )
        else:
            query = dict(user="new-sensitive-user", items=["i0", "brand-new"])
        result = predict(opened, dict(recommendation_request=query))
        assert result["fit"] is False
        assert (
            any(r["item"] == identity("brand-new") for r in result["recommendations"])
            if task != "ranker"
            else True
        )
        assert all(
            r["source_records"]
            for r in result["recommendations"]
            if r["item"] == identity("i0")
        )
        dest = tmp_path / "masked.json"
        export_list(result, dest)
        assert (
            "new-sensitive-user" not in dest.read_text()
            and "brand-new" not in dest.read_text()
        )
        assert dest.stat().st_mode & 0o777 == 0o600
        with pytest.raises(ProjectError):
            export_list(result, dest)
        assert before == (tmp_path / "source.parquet").read_bytes()
        store.path(record["neural"]["details_uri"]).write_bytes(b"corrupt")
        with pytest.raises(ProjectError, match="hash"):
            load(store, record)


@pytest.mark.parametrize("split", ["temporal", "leave_last_out"])
def test_global_protected_future_and_timestamp_ties(tmp_path, split):
    store, request, work, spec = fixture(tmp_path, split=split)
    with closing(store):
        out = calculate(request, spec.data(), work)
        held = set(out["plan"]["membership"]["validation"])
        rows = {r["row_id"]: r for r in out["rows"]}
        for q in out["queries"]:
            assert not set(q["fit_row_ids"]) & held
            assert all(rows[i]["time"] < q["time"] for i in q["fit_row_ids"])
            assert identity("future-only") not in q["universe_ids"]
        cold = next(
            q for q in out["queries"] if q["user"] == identity("new-sensitive-user")
        )
        assert cold["metrics"]["recall"] == 0
        assert cold["unseen_relevant_ids"] == [identity("future-only")]
        bad = copy.deepcopy(out)
        bad["queries"][0]["fit_row_ids"].append(next(iter(held)))
        with pytest.raises(ProjectError, match="sızıntısı"):
            validate(bad)
        # At the last timestamp, ties are held as a whole, never arbitrary row order.
        r = read_rows(request, spec, Control())
        extra = dict(r[-2], row_id="tied-row")
        qs = contexts(r + [extra], replace(spec, split="leave_last_out"))
        q = next(q for q in qs if q["user"] == extra["user"])
        assert {r["row_id"] for r in q["held"]} >= {extra["row_id"], r[-2]["row_id"]}


def test_sample_universe_seed_and_seen_denominators(tmp_path):
    store, request, work, spec = fixture(tmp_path, candidates="sampled", negatives=1)
    with closing(store):
        a = calculate(request, spec.data(), work)
        b = calculate(request, spec.data(), work)
        assert [q["candidate_ids"] for q in a["queries"]] == [
            q["candidate_ids"] for q in b["queries"]
        ]
        q = next(q for q in a["queries"] if q["user"] == identity("u0"))
        assert identity("i2") in q["seen_relevant_ids"] and q["metrics"]["recall"] == 0
        assert identity("i2") not in q["candidate_ids"]
        full = calculate(request, replace(spec, candidates="full").data(), work)
        assert full["metrics"]["comparability_key"] != a["metrics"][
            "comparability_key"
        ] or all(
            q["candidate_ids"] == v["candidate_ids"]
            for q, v in zip(a["queries"], full["queries"])
        )
        nofilter = calculate(request, replace(spec, seen_filter=False).data(), work)
        assert any(identity("i2") in q["candidate_ids"] for q in nofilter["queries"])


@pytest.mark.parametrize(
    "changes",
    [
        dict(k=0),
        dict(seed=True),
        dict(cutoff=float("nan")),
        dict(regularization=0),
        dict(task="ranker"),
        dict(rating_min=5, rating_max=1),
        dict(features=("x", "x")),
    ],
)
def test_bad_contracts(tmp_path, changes):
    store, _, _, spec = fixture(tmp_path)
    store.close()
    with pytest.raises(ProjectError):
        RecommendationSpec.from_dict({**spec.data(), **changes})


def test_cancel_preserves_non_success_and_export_opt_in(tmp_path):
    store, request, work, spec = fixture(tmp_path, "factorization")
    with closing(store):
        event = threading.Event()
        saved = []

        def checkpoint(v):
            saved.append(v)
            if v["status"] == "running":
                event.set()

        out = calculate(request, spec.data(), work, Control(event), checkpoint)
        assert out["status"] == "canceled" and not out["model_weights"]
        assert [v["status"] for v in saved] == ["running", "canceled"]
        state = publish(store, store.state, out)
        assert "model_package_uri" not in state["results"][-1]["neural"]
        with pytest.raises(Canceled):
            read_rows(request, spec, Control(event))


def test_rating_feedback_no_observed_missing_fill(tmp_path):
    store, request, work, spec = fixture(tmp_path, "factorization", feedback="explicit")
    with closing(store):
        out = calculate(request, spec.data(), work)
        assert "explicit" in out["model_weights"]["model"]["objective_type"]
        spec = replace(spec, rating_min=3, relevant_rating=4)
        with pytest.raises(ProjectError, match="rating"):
            calculate(request, spec.data(), work)


def test_registry_protocol_and_prior_test_ledger(tmp_path):
    from veri_ufku.storage.experiment_store import compare, rows

    store, request, work, spec = fixture(tmp_path)
    with closing(store):
        a = calculate(request, spec.data(), work)
        publish(store, store.state, a)
        b = calculate(
            dict(request, run_id="run:second59"),
            replace(spec, candidates="sampled", negatives=1).data(),
            work,
        )
        publish(store, store.state, b)
        registry = rows(store)
        assert len(registry) == 2
        assert all(
            r["kind"] == "neural"
            and r["data_access_at"]
            and r["params"]["recommendation_spec"]
            for r in registry
        )
        report = compare(store, [a["run_id"], b["run_id"]], "ndcg")
        assert not report["comparable"] and report["warnings"]
        assert all(r["verified_artifacts"] for r in report["rows"])
        from veri_ufku.storage.experiment_store import event

        state = event(store, store.state, a["run_id"], "metric_revision", "ndcg")
        assert state["results"][-1]["experiment_event"]["value"] == "ndcg"
        # Single journal validator rejects even a fabricated/reset prior-test list.
        from veri_ufku.storage.neural_store import validate_journal

        fake = copy.deepcopy(store.state)
        fake["results"].insert(0, dict(id="test-use:earlier", test_use={}))
        versions = {d["version_id"]: d for d in fake["datasets"]}
        with pytest.raises(ProjectError, match="journal"):
            validate_journal(fake, versions)
        for r in fake["results"][1:]:
            if "neural" not in r:
                continue
            r["neural"]["prior_test_use_ids"] = ["test-use:earlier"]
        validate_journal(fake, versions)


@pytest.mark.parametrize(
    "mutation",
    [
        "negative",
        "missing",
        "bad_time",
        "content_change",
        "group_boundary",
        "too_many",
        "snapshot",
    ],
)
def test_invalid_source_contracts(tmp_path, mutation):
    from veri_ufku.importers.delimited import hash_artifact

    task = "ranker" if mutation == "group_boundary" else "content"
    store, request, work, spec = fixture(tmp_path, task)
    with closing(store):
        frame = pl.read_parquet(request["path"])
        if mutation == "negative":
            frame = frame.with_columns(pl.lit(-1.0).alias("strength"))
        elif mutation == "missing":
            frame = frame.with_columns(pl.lit(None, dtype=pl.Float64).alias("strength"))
        elif mutation == "bad_time":
            frame = frame.with_columns(pl.lit("2026-01-01").alias("timestamp"))
        elif mutation == "content_change":
            frame = (
                frame.with_row_index("j")
                .with_columns(pl.col("j").cast(pl.Float64).alias("x"))
                .drop("j")
            )
        elif mutation == "group_boundary":
            frame = (
                frame.with_row_index("j")
                .with_columns(pl.col("j").cast(pl.Float64).alias("timestamp"))
                .drop("j")
            )
        elif mutation == "too_many":
            request["row_count"] = 2001
        frame.write_parquet(request["path"])
        if mutation != "snapshot":
            request["fingerprint"] = hash_artifact(request["path"], Control())
        else:
            request["fingerprint"]["sha256"] = "0" * 64
        with pytest.raises(ProjectError):
            calculate(request, spec.data(), work)


def test_local_only_source_missing_and_known_content_reference(tmp_path, monkeypatch):
    import socket

    from veri_ufku.modeling.recommendation_math import fit, recommend

    store, request, work, spec = fixture(tmp_path, "content")
    with closing(store):
        (tmp_path / "source.parquet").unlink()

        def no_network(*args, **kwargs):
            raise AssertionError("Offline recommendation tried network")

        monkeypatch.setattr(socket.socket, "connect", no_network)
        out = calculate(request, spec.data(), work)
        assert out["status"] == "completed"
        historical = [
            dict(
                user=identity("u"),
                item=identity("a"),
                value=1,
                time=1,
                features=[1, 0],
                row_id="r1",
                query="",
            ),
            dict(
                user=identity("other"),
                item=identity("b"),
                value=1,
                time=2,
                features=[0, 1],
                row_id="r2",
                query="",
            ),
        ]
        model = fit(historical, spec, Control())
        result = recommend(
            model, identity("u"), [identity("a"), identity("b")], 2, False
        )
        assert [r["score"] for r in result] == [1, 0]
        assert recommend(model, identity("u"), [identity("a"), identity("b")], 2, True)[
            0
        ]["item"] == identity("b")
        listed = predict(
            out,
            dict(
                recommendation_request=dict(
                    user="new-secret-user", items=["new-item", "i0"]
                )
            ),
        )
        raw = tmp_path / "raw.json"
        export_list(listed, raw, True)
        assert "new-secret-user" in raw.read_text() and "new-item" in raw.read_text()


def test_ltr_new_query_needs_features_and_respects_query_order(tmp_path):
    store, request, work, spec = fixture(tmp_path, "ranker")
    with closing(store):
        out = calculate(request, spec.data(), work)
        assert all(
            q["metrics"]["ndcg"] == 1 and q["diversity"] is None for q in out["queries"]
        )
        with pytest.raises(ProjectError, match="feature"):
            predict(out, dict(recommendation_request=dict(user="new", items=["i0"])))
        model = out["model_weights"]["model"]
        assert model["query_ids"] and model["pair_count"] > 0
        assert all(
            r["time"] < spec.cutoff
            for r in out["rows"]
            if r["row_id"] in model["fit_row_ids"]
        )
