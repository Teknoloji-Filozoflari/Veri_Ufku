"""Hand references and independent enumeration for all bounded Phase60 algorithms."""

import copy
import itertools
import json
import threading
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime

import numpy as np
import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.pattern_basket import mine
from veri_ufku.modeling.pattern_contracts import PatternSpec
from veri_ufku.modeling.pattern_events import advance, period_start
from veri_ufku.modeling.patterns import calculate
from veri_ufku.modeling.recommendation_contracts import identity
from veri_ufku.storage.neural_store import load, publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def ts(text):
    return datetime.fromisoformat(text).replace(tzinfo=UTC).timestamp()


def frame(task):
    if task in ("apriori", "fp_growth"):
        return pl.DataFrame(
            dict(
                entity=["t1", "t1", "t2", "t3", "t4", "t5", "t5"],
                activity=["A", "B", "A", "B", None, "A", "B"],
            )
        )
    if task == "cohort":
        events = [
            ("a", "signup", "2026-01-01"),
            ("a", "active", "2026-02-01"),
            ("b", "signup", "2026-01-15"),
            ("c", "signup", "2026-02-10"),
            ("c", "active", "2026-03-02"),
        ]
        return pl.DataFrame(
            dict(
                entity=[v[0] for v in events],
                activity=[v[1] for v in events],
                timestamp=[ts(v[2]) for v in events],
            )
        )
    events = [
        ("a", "view", 0, True),
        ("a", "cart", 2, True),
        ("a", "buy", 4, True),
        ("b", "view", 20, False),
        ("b", "cart", 24, False),
        ("c", "view", 95, False),
        ("c", "cart", 97, False),
    ]
    return pl.DataFrame(
        dict(
            entity=[v[0] for v in events],
            activity=[v[1] for v in events],
            timestamp=[float(v[2]) for v in events],
            order=list(range(len(events))),
            complete=[v[3] for v in events],
        )
    )


def fixture(tmp_path, task="apriori"):
    store, request, work = prepare(tmp_path, frame(task))
    request.update(
        origin_version=request["version_id"],
        run_id="run:patterns60",
        prior_test_use_ids=[],
        config_revision=0,
    )
    params = dict(
        task=task,
        entity=column(request, "entity"),
        activity=column(request, "activity"),
    )
    if task not in ("apriori", "fp_growth"):
        params.update(
            time=column(request, "timestamp"), observation_start=0, observation_end=100
        )
    if task == "cohort":
        params.update(
            observation_start=ts("2026-01-01"),
            observation_end=ts("2026-03-15"),
            cohort_start="activity",
        )
    if task in ("process", "conformance"):
        params.update(complete=column(request, "complete"))
    if task == "conformance":
        params["conformance"] = dict(
            schema="ActivityTransitionModel/v1",
            starts=["view"],
            ends=["buy"],
            edges=[["view", "cart"], ["cart", "buy"]],
        )
    return (
        store,
        request,
        work,
        PatternSpec(**params, stages=("view", "cart", "buy"), window_seconds=10),
    )


@pytest.mark.parametrize(
    "task", ["apriori", "fp_growth", "cohort", "funnel", "process", "conformance"]
)
def test_native_artifact_source_lineage_roundtrip(tmp_path, task):
    store, request, work, spec = fixture(tmp_path, task)
    original = (tmp_path / "source.parquet").read_bytes()
    with closing(store):
        out = calculate(request, spec.data(), work)
        state = publish(store, store.state, out)
        record = state["results"][-1]
        assert out["status"] == "completed" and out["analysis"]
        assert load(store, record) == json.loads(json.dumps(out))
        assert not record["neural"].get("model_package_uri")
        assert "rows" not in record["neural"] and "analysis" not in record["neural"]
        assert all(r["source_record_id"] and r["row_id"] for r in out["rows"])
        assert (tmp_path / "source.parquet").read_bytes() == original
    with closing(ProjectStore.open(tmp_path / "project")) as reopened:
        assert load(reopened, record)["analysis"] == out["analysis"]
        reopened.path(record["neural"]["details_uri"]).write_bytes(b"corrupt")
        with pytest.raises(ProjectError, match="hash"):
            load(reopened, record)


@pytest.mark.parametrize("backend", ["apriori", "fp_growth"])
def test_basket_reference_denominator(backend, tmp_path):
    store, r, w, s = fixture(tmp_path, backend)
    with closing(store):
        a = calculate(r, s.data(), w)["analysis"]
        assert a["transaction_total"] == 5
        pair = next(i for i in a["itemsets"] if len(i["items"]) == 2)
        assert pair["count"] == 2 and pair["support"] == 0.4
        assert len(a["rules"]) == 2
        assert all(
            v["confidence"] == pytest.approx(2 / 3)
            and v["lift"] == pytest.approx(10 / 9)
            for v in a["rules"]
        )


def test_random_apriori_fp_tree_against_brute_force():
    rng = np.random.default_rng(60)
    for _ in range(8):
        baskets = [{str(i) for i in range(7) if rng.random() < 0.35} for _ in range(30)]
        expected = {
            part: sum(set(part) <= b for b in baskets)
            for n in range(1, 4)
            for part in itertools.combinations([str(i) for i in range(7)], n)
        }
        expected = {k: v for k, v in expected.items() if v / 30 >= 0.2}
        for backend in ("apriori", "fp_growth"):
            spec = PatternSpec(task=backend, entity="e", activity="a", max_length=3)
            out = mine(baskets, spec, Control())
            assert {tuple(v["items"]): v["count"] for v in out["itemsets"]} == expected


def test_cohort_reference_and_right_censoring(tmp_path):
    store, r, w, s = fixture(tmp_path, "cohort")
    with closing(store):
        a = calculate(r, s.data(), w)["analysis"]
        jan = [c for c in a["cells"] if c["cohort"].startswith("2026-01")]
        assert [
            (c["observed_count"], c["denominator"], c["retention"]) for c in jan
        ] == [(2, 2, 1), (1, 2, 0.5), (0, 2, None)]
        feb = [c for c in a["cells"] if c["cohort"].startswith("2026-02")]
        assert (
            feb[0]["retention"] == 1
            and feb[1]["right_censored"]
            and feb[1]["retention"] is None
        )
        event = calculate(r, replace(s, unit="event").data(), w)["analysis"]
        assert "not person" in event["denominator"]
        left = calculate(
            r, replace(s, observation_start=ts("2025-12-31") + 12 * 3600).data(), w
        )
        assert left["analysis"]


def test_calendar_dst_not_86400():
    start = period_start(ts("2026-03-08") + 12 * 3600, "America/New_York", "day")
    assert advance(start, "day").timestamp() - start.timestamp() == 23 * 3600
    assert advance(period_start(ts("2026-01-31"), "UTC", "month"), "month").month == 2


def test_funnel_reference_censored_people_and_attempts(tmp_path):
    store, r, w, s = fixture(tmp_path, "funnel")
    with closing(store):
        a = calculate(r, s.data(), w)["analysis"]
        assert a["denominator"] == 2 and a["censored_attempts"] == 1
        assert [v["count"] for v in a["stages"]] == [2, 2, 1]
        assert [v["fraction"] for v in a["stages"]] == [1, 1, 0.5]
        assert (
            calculate(r, replace(s, unit="event").data(), w)["analysis"]["denominator"]
            == 2
        )


def test_dfg_reference_incomplete_and_conformance(tmp_path):
    store, r, w, s = fixture(tmp_path, "conformance")
    with closing(store):
        a = calculate(r, s.data(), w)["analysis"]
        assert {(v["source"], v["target"]): v["count"] for v in a["edges"]} == {
            ("view", "cart"): 3,
            ("cart", "buy"): 1,
        }
        assert a["incomplete_traces"] == 2 and a["fitting_complete"] == 1
        assert [t["fitting"] for t in a["traces"]] == [True, None, None]
        b = calculate(r, replace(s, complete="").data(), w)["analysis"]
        assert b["incomplete_traces"] == 3 and b["fitting_complete"] == 0
        invalid = copy.deepcopy(s.conformance)
        invalid["edges"] = []
        b = calculate(r, replace(s, conformance=invalid).data(), w)["analysis"]
        assert b["traces"][0]["fitting"] is False and b["traces"][0]["violations"]


@pytest.mark.parametrize(
    "change",
    [
        dict(min_support=0),
        dict(candidate_budget=True),
        dict(timezone="Missing/Zone"),
        dict(task="fp"),
        dict(max_length=9),
        dict(observation_end=float("nan")),
    ],
)
def test_closed_parameters(change):
    with pytest.raises(ProjectError):
        PatternSpec.from_dict(PatternSpec(entity="e", activity="a").data() | change)


def test_budget_cardinality_cancel():
    spec = PatternSpec(entity="e", activity="a", candidate_budget=2)
    with pytest.raises(ProjectError, match="bütçe"):
        mine([{str(i) for i in range(8)}], spec, Control())
    with pytest.raises(ProjectError, match="64item"):
        mine(
            [{str(i) for i in range(65)}],
            replace(spec, candidate_budget=100),
            Control(),
        )


def test_cancel_durable_status(tmp_path):
    store, r, w, s = fixture(tmp_path)
    with closing(store):
        event = threading.Event()

        def checkpoint(v):
            if v["status"] == "running":
                event.set()

        out = calculate(r, s.data(), w, Control(event), checkpoint)
        assert out["status"] == "canceled" and not out["analysis"]
        state = publish(store, store.state, out)
        assert state["results"][-1]["neural"]["status"] == "canceled"


def test_duplicates_empty_basket_and_budget_failure(tmp_path):
    from veri_ufku.modeling.patterns import baskets_for

    rows = [
        dict(entity=identity("t"), activity=identity("a")),
        dict(entity=identity("t"), activity=identity("a")),
    ]
    spec = PatternSpec(entity="e", activity="a")
    with pytest.raises(ProjectError, match="duplicate"):
        baskets_for(rows, spec)
    baskets, duplicates = baskets_for(rows, replace(spec, duplicates="set"))
    assert duplicates == 1 and baskets == [{identity("a")}]
    with pytest.raises(ProjectError, match="empty-basket"):
        baskets_for(
            rows + [dict(entity=identity("t"), activity=None)],
            replace(spec, duplicates="set"),
        )
    store, r, w, s = fixture(tmp_path)
    with closing(store):
        out = calculate(r, replace(s, candidate_budget=1).data(), w)
        assert out["status"] == "failed" and not out["analysis"]
        state = publish(store, store.state, out)
        assert state["results"][-1]["neural"]["status"] == "failed"


def test_ties_order_incomplete_and_order_conflict():
    from veri_ufku.modeling.pattern_events import process

    rows = [
        dict(
            entity="case",
            activity_raw="A",
            time=1,
            order=1,
            complete=False,
            row_id="r1",
        ),
        dict(
            entity="case",
            activity_raw="B",
            time=1,
            order=2,
            complete=False,
            row_id="r2",
        ),
    ]
    spec = PatternSpec(
        task="process", entity="e", activity="a", time="t", observation_end=5
    )
    with pytest.raises(ProjectError, match="timestamp"):
        process(rows, spec, Control())
    ordered = replace(spec, ties="order", order="o")
    out = process(rows, ordered, Control())
    assert out["edges"] == [dict(source="A", target="B", count=1)]
    assert out["traces"][0]["fitting"] is None
    rows[1]["complete"] = True
    with pytest.raises(ProjectError, match="complete"):
        process(rows, ordered, Control())


def test_funnel_multiple_attempts_cannot_reuse_event():
    from veri_ufku.modeling.pattern_events import funnel

    rows = [
        dict(entity="u", activity_raw=a, time=t, order=None, row_id=str(t))
        for t, a in [(0, "view"), (2, "view"), (3, "buy")]
    ]
    spec = PatternSpec(
        task="funnel",
        entity="e",
        activity="a",
        time="t",
        observation_end=20,
        window_seconds=10,
        unit="event",
    )
    a = funnel(rows, spec, Control())
    assert a["denominator"] == 2 and [s["count"] for s in a["stages"]] == [2, 1]
    assert len({r for attempt in a["attempts"] for r in attempt["row_ids"]}) == 3


def test_naive_time_and_unknown_source_rejected(tmp_path):
    from veri_ufku.importers.delimited import hash_artifact

    store, r, w, s = fixture(tmp_path, "process")
    with closing(store):
        f = pl.read_parquet(r["path"]).with_columns(
            pl.lit("2026-01-01T00:00:00").alias("timestamp")
        )
        f.write_parquet(r["path"])
        r["fingerprint"] = hash_artifact(r["path"], Control())
        with pytest.raises(ProjectError, match="offset"):
            calculate(r, s.data(), w)
        with pytest.raises(ProjectError, match="ColumnId"):
            calculate(r, replace(s, time="missing-column").data(), w)


@pytest.mark.parametrize("backend", ["apriori", "fp_growth"])
def test_cancel_inside_algorithm(backend):
    from veri_ufku.jobs.workers import Canceled

    flag = threading.Event()

    class DuringMining(Control):
        checks = 0

        def check(self):
            self.checks += 1
            if self.checks == 100:
                flag.set()
            super().check()

    control = DuringMining(flag)
    with pytest.raises(Canceled):
        mine(
            [{str(j) for j in range(12)} for _ in range(30)],
            PatternSpec(task=backend, entity="e", activity="a", candidate_budget=20000),
            control,
        )
    assert control.checks == 100
