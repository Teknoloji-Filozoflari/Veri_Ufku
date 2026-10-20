"""Phase62 deterministic prequential, bounded state and safe replay references."""

import copy
import json

import numpy as np
import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.special_targets import TargetSpec, evaluate
from veri_ufku.modeling.stream_contracts import StreamSpec
from veri_ufku.modeling.streams import calculate
from veri_ufku.storage.neural_store import load, publish
from veri_ufku.storage.project_model import ProjectError


def fixture(tmp, n=12, **changes):
    rows = dict(
        id=list(range(n)),
        event=list(map(float, range(n))),
        processing=list(map(float, range(n))),
        feedback=list(map(float, range(n))),
        x=[float(i % 2) for i in range(n)],
        y=[i % 2 for i in range(n)],
    )
    rows.update(changes)
    store, request, work = prepare(tmp, pl.DataFrame(rows))
    request.update(
        run_id="run:stream62",
        origin_version=request["version_id"],
        prior_test_use_ids=[],
    )
    spec = StreamSpec(
        event_id=column(request, "id"),
        event_time=column(request, "event"),
        processing_time=column(request, "processing"),
        feedback_time=column(request, "feedback"),
        target=column(request, "y"),
        features=(column(request, "x"),),
        checkpoint_every=2,
    )
    return store, request, work, spec


def test_reference_test_before_fit_and_safe_journal(tmp_path):
    store, r, w, s = fixture(tmp_path)
    try:
        result = calculate(r, s.data(), w)
        assert result["status"] == "completed"
        assert result["state"]["trained"] == 12
        assert result["state"]["scored"] == 11
        assert [p["prediction"] for p in result["state"]["preview"]] == [
            None,
            0,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
        ]
        assert result["metrics"]["accuracy"] == 10 / 11
        assert [v["trained_before"] for v in result["state"]["preview"]] == list(
            range(12)
        )
        assert result["state"]["preview"][0]["prediction"] is None
        assert result["state"]["scaler"]["mean_"] == [0.5]
        state = publish(store, store.state, result)
        actual = load(store, state["results"][-1])
        assert actual["state"] == result["state"]
        assert result["prior_test_use_ids"] == []
    finally:
        store.close()


def test_checkpoint_resume_exact_state_and_compatibility(tmp_path):
    store, r, w, s = fixture(tmp_path, feedback=[i + 3.0 for i in range(12)])

    class Stop(Control):
        stop = False

        def check(self):
            if self.stop:
                raise Canceled()

    c = Stop()
    saved = []

    def checkpoint(value):
        saved.append(value)
        if value["state"]["cursor"] >= 4:
            c.stop = True

    try:
        full = calculate(r, s.data(), w)
        canceled = calculate(r, s.data(), w, c, checkpoint)
        assert canceled["status"] == "canceled" and canceled["state"]["cursor"] == 4
        resumed = calculate(
            {**r, "run_id": "run:resumed", "stream_resume": canceled}, s.data(), w
        )
        assert resumed["state"] == full["state"]
        assert len(resumed["state"]["pending"]) == 3
        bad = copy.deepcopy(canceled)
        bad["compat_id"] = "bad"
        with pytest.raises(ProjectError, match="Resume"):
            calculate({**r, "stream_resume": bad}, s.data(), w)
    finally:
        store.close()


@pytest.mark.parametrize(
    "kind", ["buffer", "duplicate", "late_reject", "missing", "late_quarantine"]
)
def test_policy_and_bounds(tmp_path, kind):
    changes = {}
    if kind == "buffer":
        changes["feedback"] = [100.0] * 12
    if kind == "duplicate":
        changes["id"] = [0] * 12
    if kind.startswith("late"):
        changes["event"] = [float(i) if i != 5 else 0.0 for i in range(12)]
    if kind == "missing":
        changes.update(y=[None] * 12, feedback=[None] * 12)
    store, r, w, s = fixture(tmp_path, **changes)
    raw = s.data()
    if kind == "buffer":
        raw["buffer"] = 2
    if kind == "late_reject":
        raw["late_policy"] = "reject"
    try:
        out = calculate(r, raw, w)
        assert out["status"] == (
            "failed" if kind in ("buffer", "duplicate", "late_reject") else "completed"
        )
        assert out["state"]["peak_pending"] <= raw["buffer"]
        if kind == "missing":
            assert (
                out["metrics"]["accuracy"] is None
                and out["state"]["trained"] == 0
                and out["state"]["missing"] == 12
            )
        if kind == "late_quarantine":
            assert out["state"]["late"] == 1 and out["state"]["trained"] == 11
        assert len(json.dumps(out)) < 100000
    finally:
        store.close()


@pytest.mark.parametrize(
    "task", ["multilabel", "multioutput", "ordinal", "semisupervised", "pu"]
)
def test_special_target_support(task):
    a = np.arange(20, dtype=float).reshape(-1, 1)
    b = np.array([[2.0], [18.0]])
    y = np.array([0] * 10 + [1] * 10)
    if task == "multilabel":
        yt = np.column_stack([y, 1 - y])
        ye = np.array([[0, 1], [1, 0]])
    elif task == "multioutput":
        yt = np.column_stack([a[:, 0], 2 * a[:, 0]])
        ye = np.array([[2, 4], [18, 36]])
    elif task == "ordinal":
        yt = np.array(["low"] * 10 + ["high"] * 10)
        ye = np.array(["low", "high"])
    else:
        yt = y.copy()
        ye = np.array([0, 1])
    spec = TargetSpec(task, order=("low", "high") if task == "ordinal" else ())
    if task == "pu":
        with pytest.raises(ProjectError, match="unavailable"):
            evaluate(spec, a, yt, b, ye)
        return
    out = evaluate(spec, a, yt, b, ye)
    assert len(out["predictions"]) == 2 and out["metrics"]
    if task == "multioutput":
        np.testing.assert_allclose(out["predictions"], ye, atol=2)
    elif task == "ordinal":
        assert out["predictions"] == ["low", "high"]
    else:
        trans = (
            evaluate(TargetSpec("semisupervised", transductive=True), a, y, b, [0, 1])
            if task == "semisupervised"
            else None
        )
        if trans:
            assert "transductive" in trans["fit_scope"]


def test_special_schema_rejects_bad_labels():
    with pytest.raises(ProjectError, match="Ordinal"):
        TargetSpec("ordinal").validate()
    with pytest.raises(ProjectError, match="Multilabel"):
        evaluate(
            TargetSpec("multilabel"), [[0], [1]], [[0, 0], [0, 1]], [[1]], [[1, 0]]
        )


def test_mid_update_cancel_rolls_back_to_durable_cursor(tmp_path):
    store, r, w, s = fixture(tmp_path, n=80)

    class Stop(Control):
        calls = 0

        def check(self):
            self.calls += 1
            if self.calls == 93:
                raise Canceled()

    try:
        full = calculate(r, s.data(), w)
        canceled = calculate(r, s.data(), w, Stop())
        assert canceled["status"] == "canceled"
        assert canceled["state"]["cursor"] % s.checkpoint_every == 0
        resumed = calculate({**r, "stream_resume": canceled}, s.data(), w)
        assert resumed["state"] == full["state"]
    finally:
        store.close()


@pytest.mark.parametrize("policy", ["alarm_only", "reset"])
def test_explicit_drift_retrain_policy(tmp_path, policy):
    store, r, w, s = fixture(tmp_path, n=100, x=[0.0] * 100, y=[0] * 50 + [1] * 50)
    try:
        spec = {**s.data(), "retrain": policy, "drift_threshold": 0.2}
        result = calculate(r, spec, w)
        assert result["status"] == "completed"
        assert result["state"]["alarms"] > 0
        assert (result["state"]["generation"] > 0) == (policy == "reset")
    finally:
        store.close()


def test_bounded_windows_and_preview(tmp_path):
    store, r, w, s = fixture(tmp_path, n=1024)
    try:
        result = calculate(
            r, {**s.data(), "checkpoint_every": 128, "buffer": 8, "window": 1}, w
        )
        assert result["status"] == "completed"
        state = result["state"]
        assert (
            len(state["preview"]) == 64
            and len(state["pending"]) <= 8
            and len(state["windows"]) <= 8
        )
        assert state["closed_windows"] == 1023 and list(state["windows"].values()) == [
            1
        ]
        assert len(json.dumps(state)) < 18000
    finally:
        store.close()


@pytest.mark.parametrize(
    "task", ["multilabel", "multioutput", "ordinal", "semisupervised"]
)
def test_special_run_identity_and_journal(tmp_path, task):
    from veri_ufku.modeling.special_runs import TargetRecipe
    from veri_ufku.modeling.special_runs import calculate as special

    n = 24
    frame = pl.DataFrame(
        dict(
            x=list(map(float, range(n))),
            y=[0] * 12 + [1] * 12,
            z=[1] * 12 + [0] * 12,
            role=["train"] * 10 + ["eval"] * 2 + ["train"] * 10 + ["eval"] * 2,
            label=["low"] * 12 + ["high"] * 12,
        )
    )
    store, r, w = prepare(tmp_path, frame)
    r.update(
        run_id="run:special62", origin_version=r["version_id"], prior_test_use_ids=[]
    )
    spec = TargetRecipe(
        task,
        features=(column(r, "x"),),
        targets=(column(r, "y"), column(r, "z"))
        if task in ("multilabel", "multioutput")
        else (column(r, "label" if task == "ordinal" else "y"),),
        role=column(r, "role"),
        order=("low", "high") if task == "ordinal" else (),
    )
    try:
        out = special(r, spec.data(), w)
        assert out["status"] == "completed"
        members = out["plan"]["membership"]
        assert not {v["row_id"] for v in members["train"]} & {
            v["row_id"] for v in members["eval"]
        }
        assert len(members["eval"]) == len(out["analysis"]["predictions"]) == 4
        state = publish(store, store.state, out)
        assert load(store, state["results"][-1])["analysis"] == out["analysis"]
    finally:
        store.close()


def test_delayed_labels_do_not_change_earlier_predictions(tmp_path):
    store, r, w, s = fixture(tmp_path, feedback=[100.0] * 12)
    try:
        result = calculate(r, s.data(), w)
        assert result["state"]["trained"] == 0
        assert all(v["prediction"] is None for v in result["state"]["preview"])
    finally:
        store.close()


def test_eval_features_do_not_fit_scaler():
    report = evaluate(
        TargetSpec("multilabel"),
        [[0.0], [2.0], [4.0], [6.0]],
        [[0, 1], [0, 1], [1, 0], [1, 0]],
        [[10000.0]],
        [[1, 0]],
    )
    assert report["preprocessing"]["mean"] == [3.0]


def test_final_test_roles_rejected(tmp_path):
    from veri_ufku.modeling.special_runs import TargetRecipe
    from veri_ufku.modeling.special_runs import calculate as special

    store, r, w = prepare(
        tmp_path,
        pl.DataFrame(
            dict(x=[0.0, 1.0, 2.0], y=[0, 1, 0], role=["train", "train", "test"])
        ),
    )
    r.update(run_id="run:reject", origin_version=r["version_id"], prior_test_use_ids=[])
    s = TargetRecipe(
        "semisupervised",
        features=(column(r, "x"),),
        targets=(column(r, "y"),),
        role=column(r, "role"),
    )
    try:
        with pytest.raises(ProjectError, match="final test"):
            special(r, s.data(), w)
    finally:
        store.close()


def test_transductive_eval_truth_never_fits():
    spec = TargetSpec("semisupervised", transductive=True)
    a = np.arange(8, dtype=float).reshape(-1, 1)
    y = [0, 0, -1, -1, -1, -1, 1, 1]
    first = evaluate(spec, a, y, [[1.0], [6.0]], [0, 1])
    changed = evaluate(spec, a, y, [[1.0], [6.0]], [1, 0])
    assert first["predictions"] == changed["predictions"]
    assert first["metrics"] != changed["metrics"]


def test_unavailable_registry_and_source_resume_journal(tmp_path):
    from veri_ufku.domain.capabilities import CAPABILITIES, availability

    for key in ("model.special.pu", "model.stream.broker"):
        assert availability(CAPABILITIES[key])[0] is False
    store, r, w, s = fixture(tmp_path)
    try:
        data = calculate(r, s.data(), w)
        data["resume_from"] = "run:nonexistent"
        with pytest.raises(ProjectError, match="resume parent"):
            publish(store, store.state, data)
    finally:
        store.close()
