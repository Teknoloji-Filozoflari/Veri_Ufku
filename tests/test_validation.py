"""Independent reference errors, adversarial test features and temporal/group fixtures."""

import copy
import json
import threading
from contextlib import closing
from dataclasses import replace
from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest
from test_dataset import column, prepare
from test_preparation import request, specification

from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.baseline import FoldPreparation, calculate
from veri_ufku.modeling.preparation import calculate as preparation
from veri_ufku.modeling.validation import ValidationSpec, split_plan
from veri_ufku.storage.project_model import ProjectError, uid, validate_state
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.validation_store import choice, complete, reserve_test


def fixture(n=80):
    return pl.DataFrame(
        dict(
            x=[float(i) for i in range(n)],
            cat=["A", "B"] * (n // 2),
            y=[float(i % 7) for i in range(n)],
            group=[f"g{i // 4:03}" for i in range(n)],
            when=[date(2024, 1, 1) + timedelta(days=i) for i in range(n)],
        )
    )


def setup_run(tmp_path, structure="independent", classification=False, **changes):
    store, r, work = prepare(tmp_path, fixture())
    r = request(store)
    p = specification(
        r,
        "classification" if classification else "regression",
        group=column(r, "group") if structure in ("group", "group_time") else "",
        time=column(r, "when") if structure in ("time", "group_time") else "",
        numeric_imputation="mean",
        scaling="standard",
        selection="variance",
    )
    p = replace(p, features=(column(r, "x"), column(r, "cat")))
    report = preparation(r, p, work)
    assert not report["blockers"]
    s = ValidationSpec(
        structure=structure,
        prediction_moment="Ölçüm başlamadan önce",
        availability={
            i: dict(offset_seconds=0, note="Ölçüm öncesi kayıt") for i in p.features
        },
        **changes,
    )
    return store, dict(r, preparation=report), work, s


@pytest.mark.parametrize("method", ["random", "stratified"])
def test_fixed_seed_and_all_classes(method):
    y = np.array(["A", "B"] * 50)
    spec = ValidationSpec(method=method)
    a, parts = split_plan(
        [f"row:{i}" for i in range(100)],
        y,
        None,
        None,
        spec,
        method,
        True,
        "dv:x",
        {"sha256": "x"},
    )
    b, _ = split_plan(
        [f"row:{i}" for i in range(100)],
        y,
        None,
        None,
        spec,
        method,
        True,
        "dv:x",
        {"sha256": "x"},
    )
    assert a == b
    train, val, dev, test, folds = parts
    assert set(train).isdisjoint(val) and set(dev).isdisjoint(test)
    for x, z in folds:
        assert set(x) | set(z) <= set(dev) and set(x).isdisjoint(z)
        assert set(y[x]) == set(y[z]) == {"A", "B"}


@pytest.mark.parametrize("structure", ["independent", "group", "time", "group_time"])
def test_actual_baselines_group_time_and_json_roundtrip(tmp_path, structure):
    store, r, work, s = setup_run(tmp_path, structure)
    with closing(store):
        original = store.path(r["snapshot_uri"]).read_bytes()
        result = calculate(r, s.data(), work)
        members = result["plan"]["membership"]
        frame = pl.read_parquet(r["path"])
        lookup = {row["__vu_row_id"]: row for row in frame.iter_rows(named=True)}
        pairs = [
            (members["train"], members["validation"]),
            (members["development"], members["test"]),
        ] + [(f["train"], f["validation"]) for f in members["folds"]]
        for a, b in pairs:
            if structure in ("group", "group_time"):
                assert {lookup[i]["group"] for i in a}.isdisjoint(
                    {lookup[i]["group"] for i in b}
                )
            if structure in ("time", "group_time"):
                assert max(lookup[i]["when"] for i in a) < min(
                    lookup[i]["when"] for i in b
                )
        for e in result["evaluations"]:
            assert set(e["fit_row_ids"]).isdisjoint(members["test"])
            assert e["baseline_center"] == pytest.approx(
                sum(lookup[i]["y"] for i in e["fit_row_ids"]) / len(e["fit_row_ids"])
            )
            assert all(m["direction"] == "minimize" for m in e["metrics"])
        state = complete(store, store.state, result)
        assert state["results"][-1]["baseline"]["plan"] == result["plan"]
        root = store.root
        assert store.path(r["snapshot_uri"]).read_bytes() == original
    with closing(ProjectStore.open(root)) as reopened:
        assert (
            reopened.state["results"][-1]["baseline"]["packages"]["scikit-learn"]
            == "1.9.1"
        )


def test_test_feature_poison_never_changes_fit_and_hand_error(tmp_path, monkeypatch):
    store, r, work, s = setup_run(tmp_path)
    with closing(store):
        result = calculate(r, s.data(), work)
        test = set(result["plan"]["membership"]["test"])
        reference_final = calculate(
            dict(
                r,
                mode="final",
                expected_split_id=result["plan"]["split_id"],
                expected_protocol_id=result["plan"]["protocol_id"],
            ),
            s.data(),
            work,
        )
        original_fit = FoldPreparation.fit
        observed = []

        def spy(self, X, y=None):
            ids = set(X["__vu_row_id"].to_list())
            assert ids.isdisjoint(test), "Test record reached transformer.fit"
            assert set(X["cat"].to_list()) <= {"A", "B"}
            assert max(X["x"].to_list()) < 1000
            observed.append(ids)
            return original_fit(self, X, y)

        monkeypatch.setattr(FoldPreparation, "fit", spy)
        # Poison only held-out values without touching split keys or labels.
        frame = pl.read_parquet(r["path"])
        poisoned = frame.with_columns(
            pl.when(pl.col("__vu_row_id").is_in(list(test)))
            .then(pl.lit(1000000.0))
            .otherwise(pl.col("x"))
            .alias("x"),
            pl.when(pl.col("__vu_row_id").is_in(list(test)))
            .then(pl.lit("TEST_ONLY"))
            .otherwise(pl.col("cat"))
            .alias("cat"),
        )
        path = work / "poisoned.parquet"
        poisoned.write_parquet(path)
        from veri_ufku.importers.delimited import hash_artifact

        q = dict(
            r,
            path=str(path),
            fingerprint=hash_artifact(path, Control()),
            mode="final",
            expected_split_id="",
            expected_protocol_id="",
        )
        # Recompute deterministic membership/fingerprint identity for the poisoned snapshot.
        dev = calculate(dict(q, mode="development"), s.data(), work)
        q.update(
            expected_split_id=dev["plan"]["split_id"],
            expected_protocol_id=dev["plan"]["protocol_id"],
        )
        final = calculate(q, s.data(), work)
        assert observed and len(observed[-1]) == len(
            final["plan"]["membership"]["development"]
        )
        assert (
            final["evaluations"][0]["fitted_parameters"]
            == reference_final["evaluations"][0]["fitted_parameters"]
        )
        assert (
            final["evaluations"][0]["baseline_center"]
            == reference_final["evaluations"][0]["baseline_center"]
        )
        e = final["evaluations"][0]
        center = e["baseline_center"]
        lookup = {row["__vu_row_id"]: row["y"] for row in frame.iter_rows(named=True)}
        expected = sum(abs(lookup[i] - center) for i in test) / len(test)
        assert e["metrics"][0]["value"] == pytest.approx(expected, abs=1e-12)
        assert all(
            "TEST_ONLY" not in json.dumps(v) for v in e["fitted_parameters"].values()
        )
        tampered = copy.deepcopy(result)
        tampered["evaluations"][0]["fit_row_ids"].append(next(iter(test)))
        with pytest.raises(ProjectError, match="fit"):
            complete(store, store.state, tampered)


@pytest.mark.parametrize(
    "strategy", ["mean", "median", "prior", "most_frequent", "stratified"]
)
def test_dummy_strategies_and_metric_direction(tmp_path, strategy):
    store, r, work, s = setup_run(
        tmp_path, classification=strategy not in ("mean", "median"), baseline=strategy
    )
    with closing(store):
        out = calculate(r, s.data(), work)
        assert out["baseline"] == strategy
        assert all(
            m["direction"]
            == ("minimize" if strategy in ("mean", "median") else "maximize")
            for e in out["evaluations"]
            for m in e["metrics"]
        )


def test_group_time_overlap_rejected_no_fallback():
    n = 80
    with pytest.raises(ProjectError, match="birleşik|çakışıyor"):
        split_plan(
            [str(i) for i in range(n)],
            np.arange(n),
            np.array([str(i % 4) for i in range(n)]),
            np.arange(n),
            ValidationSpec(),
            "group_time",
            False,
            "dv:x",
            {},
        )


def test_horizon_purge_and_time_ties():
    n = 120
    times = np.repeat(np.arange(60) * 100, 2)
    plan, parts = split_plan(
        [str(i) for i in range(n)],
        np.arange(n),
        None,
        times,
        ValidationSpec(horizon_seconds=150),
        "time",
        False,
        "dv:x",
        {},
    )
    train, val, dev, test, folds = parts
    assert plan["membership"]["purged"]
    for a, b in [(train, val), (dev, test)] + folds:
        assert max(times[a] + 150) < min(times[b])
    assert set(times[train]).isdisjoint(times[val])


@pytest.mark.parametrize(
    "method", ["random", "stratified", "group", "time", "group_time"]
)
def test_rare_class_or_missing_fold_rejected(method):
    n = 80
    y = np.array(["A"] * (n - 1) + ["B"])
    with pytest.raises(ProjectError):
        split_plan(
            [str(i) for i in range(n)],
            y,
            np.array([f"g{i // 4}" for i in range(n)]),
            np.arange(n) * 100,
            ValidationSpec(),
            method,
            True,
            "dv:x",
            {},
        )


def test_repeat_test_ledger_subsequent_choice_copy_and_reopen(tmp_path):
    store, r, work, s = setup_run(tmp_path, "group_time")
    with closing(store):
        dev = calculate(r, s.data(), work)
        state = complete(store, store.state, dev)
        for number in range(2):
            run_id = "run:" + uid()
            state, use = reserve_test(store, state, dev, run_id)
            assert state["results"][-1]["test_use"]["status"] == "pending"
            final = calculate(
                dict(
                    r,
                    mode="final",
                    run_id=run_id,
                    expected_split_id=dev["plan"]["split_id"],
                    expected_protocol_id=dev["plan"]["protocol_id"],
                    prior_test_use_ids=[
                        x["id"]
                        for x in state["results"]
                        if "test_use" in x and x["id"] != use
                    ],
                ),
                s.data(),
                work,
            )
            state = complete(store, state, final, use)
        state = choice(
            store, state, r["version_id"], s.data(), dev["pipeline_id"], "run:" + uid()
        )
        entries = [x for x in state["results"] if "test_use" in x]
        assert len(entries) == 2 and entries[1]["test_use"]["prior_test_use_ids"] == [
            entries[0]["id"]
        ]
        assert state["results"][-1]["model_choice"]["prior_test_use_ids"] == [
            e["id"] for e in entries
        ]
        assert all(e["test_use"]["evaluated_at"] for e in entries)
        # A project-internal copy keeps the project-wide journal and source ancestry.
        from test_cleaning import run as clean

        clean(store, work, "x", "outlier", destination="copy")
        assert [x for x in store.state["results"] if "test_use" in x] == entries
        clone = store.save_as(tmp_path / "clone")
        clone.close()
        root = store.root
    with (
        closing(ProjectStore.open(root)) as reopened,
        closing(ProjectStore.open(tmp_path / "clone")) as cloned,
    ):
        assert [x for x in reopened.state["results"] if "test_use" in x] == entries
        assert [x for x in cloned.state["results"] if "test_use" in x] == entries
        old = copy.deepcopy(reopened.state)
        old["results"] = [x for x in old["results"] if "test_use" not in x]
        with pytest.raises(ProjectError, match="silinemez"):
            choice(
                reopened,
                old,
                r["version_id"],
                s.data(),
                dev["pipeline_id"],
                "run:" + uid(),
            )


def test_cancel_invalid_journal_fault_and_unfinished_never_completed(tmp_path):
    store, r, work, s = setup_run(tmp_path)
    with closing(store):
        token = threading.Event()
        token.set()
        with pytest.raises(Canceled):
            calculate(r, s.data(), work, Control(token))
        assert not store.state["results"]
        dev = calculate(r, s.data(), work)
        state = complete(store, store.state, dev)
        state, use = reserve_test(store, state, dev, "run:" + uid())
        before = store.path("ACTIVE").read_bytes()

        def fault(point):
            if point == "pointer_written":
                raise OSError("disk fault")

        with pytest.raises(OSError):
            complete(store, state, test_use_id=use, status="canceled", checkpoint=fault)
        assert store.path("ACTIVE").read_bytes() == before
        assert store.state["results"][-1]["test_use"]["status"] == "pending"
        state = complete(store, store.state, test_use_id=use, status="canceled")
        assert not any(
            x.get("baseline", {}).get("mode") == "final" for x in state["results"]
        )
        broken = copy.deepcopy(state)
        broken["results"][-1]["test_use"]["status"] = "completed"
        with pytest.raises(ProjectError):
            validate_state(broken)


@pytest.mark.parametrize(
    "changes",
    [
        dict(structure="group_time", entity_use="same_future"),
        dict(method="random", structure="time"),
        dict(horizon_seconds=-1),
        dict(folds=1),
        dict(availability={}),
        dict(entity_use="unsupported"),
        dict(test_fraction=0.8),
    ],
)
def test_unsupported_protocol_explicit_rejection(tmp_path, changes):
    store, r, work, s = setup_run(tmp_path)
    with closing(store), pytest.raises(ProjectError):
        calculate(r, replace(s, **changes).data(), work)


def test_dummy_classification_independent_hand_reference(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(dict(x=list(range(80)), cat=["C", "D"] * 40, y=["A", "B"] * 40)),
    )
    with closing(store):
        r = request(store)
        p = specification(r, "classification")
        report = preparation(r, p, work)
        s = ValidationSpec(
            prediction_moment="Ölçümden önce",
            availability={
                i: dict(offset_seconds=0, note="Önceden mevcut") for i in p.features
            },
        )
        out = calculate(dict(r, preparation=report), s.data(), work)
        e = out["evaluations"][0]
        values = {m["metric"]: m["value"] for m in e["metrics"]}
        # Both evaluation classes have8 records. Constant A: TP=8, FP=8, FN=0.
        # F1(A)=2/3; F1(B)=0; macro=1/3, each recall .5 averaged.
        assert values == pytest.approx(
            dict(accuracy=0.5, balanced_accuracy=0.5, f1_macro=1 / 3), abs=1e-12
        )


@pytest.mark.parametrize("point", ["pointer_written", "pointer_replaced"])
def test_test_journal_real_sigkill_and_second_writer(tmp_path, point):
    import signal
    import subprocess
    import sys

    store, r, work, s = setup_run(tmp_path)
    with closing(store):
        out = calculate(r, s.data(), work)
        complete(store, store.state, out)
        file = tmp_path / "baseline.json"
        file.write_text(json.dumps(out))
        root = store.root
    program = """import json,os,signal,sys
from pathlib import Path
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.validation_store import reserve_test
s=ProjectStore.open(sys.argv[1]);original=s.save
def save(*args,**kwargs):
    kwargs['checkpoint']=lambda p:os.kill(os.getpid(),signal.SIGKILL) if p==sys.argv[3] else None
    return original(*args,**kwargs)
s.save=save
reserve_test(s,s.state,json.loads(Path(sys.argv[2]).read_text()),'run:interrupted')
"""
    child = subprocess.run(
        [sys.executable, "-c", program, str(root), str(file), point],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert child.returncode == -signal.SIGKILL, child.stderr
    with closing(ProjectStore.open(root, recover_lock=True)) as reopened:
        uses = [x for x in reopened.state["results"] if "test_use" in x]
        assert len(uses) == (1 if point == "pointer_replaced" else 0)
        assert all(x["test_use"]["status"] == "pending" for x in uses)
        readonly = """import sys
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.validation_store import choice
from veri_ufku.storage.project_model import ProjectError
s=ProjectStore.open(sys.argv[1]);assert s.read_only
try:choice(s,s.state,s.state['datasets'][0]['version_id'],{'seed':42},'pipeline','run:new')
except ProjectError:print('READONLY_REJECTED')
else:raise AssertionError('second writer accepted')
s.close()
"""
        child = subprocess.run(
            [sys.executable, "-c", readonly, str(root)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert child.returncode == 0 and "READONLY_REJECTED" in child.stdout, (
            child.stderr
        )


def test_same_entity_future_requires_entities_seen_in_training():
    n = 160
    ids = [str(i) for i in range(n)]
    y = np.arange(n)
    times = np.arange(n) * 100
    spec = ValidationSpec(structure="time", entity_use="same_future")
    groups = np.array([f"g{i % 8}" for i in range(n)])
    plan, parts = split_plan(ids, y, groups, times, spec, "time", False, "dv:x", {})
    train, val, dev, test, folds = parts
    for a, b in [(train, val), (dev, test)] + folds:
        assert set(groups[b]) <= set(groups[a])
        assert max(times[a]) < min(times[b])
    with pytest.raises(ProjectError, match="yeni varlık"):
        split_plan(
            ids,
            y,
            np.array([f"g{i // 4}" for i in range(n)]),
            times,
            spec,
            "time",
            False,
            "dv:x",
            {},
        )
