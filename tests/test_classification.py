"""Hand-calculated classification references and test/threshold boundary checks."""

import copy
from contextlib import closing
from dataclasses import replace

import numpy as np
import polars as pl
import pytest
from test_dataset import column, prepare
from test_preparation import request, specification

from veri_ufku.modeling.baseline import FoldPreparation, calculate
from veri_ufku.modeling.classification import metrics, settings
from veri_ufku.modeling.preparation import calculate as preparation
from veri_ufku.modeling.validation import ValidationSpec
from veri_ufku.storage.project_model import ProjectError, validate_state
from veri_ufku.storage.validation_store import (
    choice,
    complete,
    load_run,
    prior_uses,
    reserve_test,
)


def synthetic(tmp_path, multiclass=False, n=150):
    x = np.linspace(-3, 3, n)
    y = (
        np.where(x > 1.5, "risk", "normal")
        if not multiclass
        else np.where(x > 1.5, "C", np.where(x > 0, "B", "A"))
    )
    store, _, work = prepare(tmp_path, pl.DataFrame(dict(x=x, y=y)))
    r = request(store)
    p = replace(
        specification(r, purpose="classification", family="linear", scaling="standard"),
        features=(column(r, "x"),),
    )
    report = preparation(r, p, work)
    s = ValidationSpec(
        prediction_moment="Ölçüm öncesi",
        availability={p.features[0]: dict(offset_seconds=0, note="Önceden bilinir")},
    )
    return (
        store,
        dict(
            r,
            preparation=report,
            classification=settings(dict(positive_class="" if multiclass else "risk")),
        ),
        work,
        s,
    )


def test_binary_hand_confusion_auc_and_undefined_classes():
    labels = ["N", "P"]
    config = settings(dict(positive_class="P", averaging="binary"))
    y = np.array(["P", "P", "P", "N", "N", "N"])
    pred = np.array(["P", "P", "N", "P", "N", "N"])
    score = np.array([0.9, 0.8, 0.4, 0.7, 0.3, 0.1])
    prob = np.column_stack([1 - score, score])
    out = metrics(y, pred, prob, labels, config, "validation")
    assert out["confusion_matrix"] == [[2, 1], [1, 2]]
    assert [m["value"] for m in out["metrics"][:4]] == pytest.approx([2 / 3] * 4)
    assert out["curves"][0]["roc_auc"] == pytest.approx(8 / 9)
    assert out["curves"][0]["pr_auc"] == pytest.approx(65 / 72)
    assert out["curves"][0]["average_precision"] == pytest.approx(11 / 12)
    missed = metrics(y, np.array(["N"] * 6), None, labels, config, "validation")
    assert missed["per_class"][1]["precision_status"] == "undefined_no_predictions"
    assert missed["per_class"][1]["recall"] == 0
    assert not missed["curves"][0]["roc"] and missed["metrics"][-1]["value"] is None
    absent = metrics(
        np.array(["N", "N"]),
        np.array(["N", "N"]),
        np.array([[0.9, 0.1], [0.8, 0.2]]),
        labels,
        config,
        "final_test",
    )
    assert absent["per_class"][1]["recall_status"] == "undefined_absent_class"
    assert absent["curves"][0]["status"] == "unavailable"
    assert absent["curves"][0]["roc_auc"] is None


@pytest.mark.parametrize(
    "average, expected", [("macro", 0.4), ("weighted", 0.4), ("micro", 0.5)]
)
def test_multiclass_hand_average(average, expected):
    out = metrics(
        np.array(list("AABBCC")),
        np.array(list("ABBBAA")),
        None,
        list("ABC"),
        settings(dict(averaging=average)),
        "validation",
    )
    assert out["confusion_matrix"] == [[1, 1, 0], [0, 2, 0], [2, 0, 0]]
    assert out["metrics"][0]["value"] == 0.5
    assert out["metrics"][3]["value"] == pytest.approx(expected)
    assert out["per_class"][2]["predicted_n"] == 0


@pytest.mark.parametrize("multiclass", [False, True])
def test_true_candidates_and_fit_threshold_exclude_test(
    tmp_path, monkeypatch, multiclass
):
    store, r, work, s = synthetic(tmp_path, multiclass)
    with closing(store):
        first = calculate(r, s.data(), work)
        test_ids = set(first["plan"]["membership"]["test"])
        original = FoldPreparation.fit
        fits = []

        def spy(self, X, y=None):
            assert not test_ids & set(X["__vu_row_id"])
            fits.append(set(X["__vu_row_id"]))
            return original(self, X, y)

        monkeypatch.setattr(FoldPreparation, "fit", spy)
        if not multiclass:
            r["classification"] = settings(
                dict(
                    positive_class="risk",
                    threshold_mode="validation_f1",
                    cost_note="Kaçırmak daha maliyetli",
                )
            )
        out = calculate(r, s.data(), work)
        assert len(fits) == 13
        candidates = {c["model"]: c for c in out["comparison"]}
        assert candidates["logistic"]["cv_f1"] > 0.8
        assert candidates["forest"]["cv_f1"] > 0.8
        assert candidates["baseline"]["cv_f1"] < 0.5
        assert (
            out["selected_model"]
            == max(out["comparison"], key=lambda c: c["cv_f1"])["model"]
        )
        assert (
            out["decision"]["validation_row_ids"]
            == out["plan"]["membership"]["validation"]
        )
        assert not test_ids & set(out["decision"]["validation_row_ids"])
        if not multiclass:
            assert len(out["decision_validation"]["threshold_candidates"]) == 19
        final = calculate(
            dict(
                r,
                mode="final",
                selected_model=out["selected_model"],
                decision=out["decision"],
                expected_split_id=out["plan"]["split_id"],
                expected_protocol_id=out["plan"]["protocol_id"],
            ),
            s.data(),
            work,
        )
        assert final["comparison"] == [] and final["decision_validation"] is None
        assert fits[-1] == set(out["plan"]["membership"]["development"])
        assert final["evaluations"][0]["threshold"] == out["decision"]["threshold"]
        assert not final["evaluations"][0]["threshold_candidates"]
        assert final["evaluations"][0]["metrics"][0]["value"] > 0.8


def test_ledger_class_threshold_retuning_tamper_and_reopen(tmp_path):
    store, r, work, s = synthetic(tmp_path, n=600)
    root = store.root
    with closing(store):
        r["classification"] = settings(
            dict(
                positive_class="risk",
                threshold_mode="validation_manual",
                threshold=0.35,
                cost_note="Yanlış alarm kabul edilebilir",
            )
        )
        out = calculate(r, s.data(), work)
        state = choice(
            store,
            store.state,
            r["version_id"],
            s.data(),
            out["pipeline_id"],
            out["run_id"],
            classification=r["classification"],
        )
        state = complete(store, state, out, run_id=out["run_id"])
        for i in range(2):
            state, ident = reserve_test(store, state, out, "run:classfinal" + str(i))
            final = calculate(
                dict(
                    r,
                    mode="final",
                    run_id="run:classfinal" + str(i),
                    selected_model=out["selected_model"],
                    decision=out["decision"],
                    prior_test_use_ids=prior_uses(state)[:-1],
                    expected_split_id=out["plan"]["split_id"],
                    expected_protocol_id=out["plan"]["protocol_id"],
                ),
                s.data(),
                work,
            )
            state = complete(store, state, final, ident)
        assert final["interpretation"] == "exploratory"
        r["classification"] = settings(
            dict(
                positive_class="normal",
                C=10,
                threshold_mode="validation_manual",
                threshold=0.65,
            )
        )
        r["prior_test_use_ids"] = prior_uses(state)
        new = calculate(r, s.data(), work)
        state = choice(
            store,
            state,
            r["version_id"],
            s.data(),
            new["pipeline_id"],
            new["run_id"],
            classification=r["classification"],
        )
        state = complete(store, state, new, run_id=new["run_id"])
        assert (
            state["results"][-2]["model_choice"]["classification"]["positive_class"]
            == "normal"
        )
        assert state["results"][-2]["model_choice"]["prior_test_use_ids"] == prior_uses(
            state
        )
        validate_state(state)
        invalid = copy.deepcopy(state)
        next(rec["test_use"] for rec in invalid["results"] if "test_use" in rec)[
            "decision"
        ]["threshold"] = 0.8
        with pytest.raises(ProjectError):
            validate_state(invalid)
    with closing(type(store).open(root)) as reopened:
        records = [rec for rec in reopened.state["results"] if "baseline" in rec]
        assert load_run(reopened, records[0])["decision"]["threshold"] == 0.35
        assert len(prior_uses(reopened.state)) == 2


@pytest.mark.parametrize(
    "change",
    [
        dict(C=True),
        dict(C=3),
        dict(trees=1000),
        dict(depth=1),
        dict(threshold=float("nan")),
        dict(threshold=0),
        dict(threshold=0.6),
        dict(averaging="samples"),
        dict(threshold_mode="test"),
        dict(candidates=["forest"]),
        dict(cost_note="x" * 2001),
    ],
)
def test_settings_reject_invalid(change):
    with pytest.raises(ProjectError):
        settings(change)


def test_probability_absent_is_not_invented_and_classes_guarded():
    from veri_ufku.modeling.classification import probabilities, validate_classes

    assert probabilities(object(), np.zeros((2, 1)), ["A", "B"]) is None
    with pytest.raises(ProjectError, match="ikili"):
        validate_classes(settings(dict(averaging="binary")), list("ABC"))
    with pytest.raises(ProjectError, match="açıkça"):
        validate_classes(settings({}), list("AB"))


def test_missing_final_class_time_protocol_is_controlled_and_persistent(tmp_path):
    from datetime import date, timedelta

    n = 150
    frame = pl.DataFrame(
        dict(
            x=[float(i % 2) for i in range(n)],
            y=["risk" if i % 2 and i < 120 else "normal" for i in range(n)],
            when=[date(2024, 1, 1) + timedelta(days=i) for i in range(n)],
        )
    )
    store, _, work = prepare(tmp_path, frame)
    with closing(store):
        r = request(store)
        p = replace(
            specification(r, purpose="classification", time=column(r, "when")),
            features=(column(r, "x"),),
        )
        r.update(
            preparation=preparation(r, p, work),
            classification=settings(dict(positive_class="risk")),
        )
        s = ValidationSpec(
            structure="time",
            prediction_moment="Ölçüm öncesi",
            availability={p.features[0]: dict(offset_seconds=0, note="Önceden mevcut")},
        )
        out = calculate(r, s.data(), work)
        state = choice(
            store,
            store.state,
            r["version_id"],
            s.data(),
            out["pipeline_id"],
            out["run_id"],
            classification=r["classification"],
        )
        state = complete(store, state, out, run_id=out["run_id"])
        state, ident = reserve_test(store, state, out, "run:missingclass")
        final = calculate(
            dict(
                r,
                mode="final",
                run_id="run:missingclass",
                selected_model=out["selected_model"],
                decision=out["decision"],
                expected_split_id=out["plan"]["split_id"],
                expected_protocol_id=out["plan"]["protocol_id"],
            ),
            s.data(),
            work,
        )
        e = final["evaluations"][0]
        assert e["per_class"][1]["support"] == 0
        assert (
            e["curves"][0]["status"] == "unavailable"
            and e["metrics"][-1]["value"] is None
        )
        state = complete(store, state, final, ident)
        validate_state(state)


def test_forest_budget_rejected_before_fit(tmp_path, monkeypatch):
    store, r, work, s = synthetic(tmp_path, n=20001)
    with closing(store):

        def forbidden(*args, **kwargs):
            raise AssertionError("Maliyet reddinden önce fit yapılamaz")

        monkeypatch.setattr(FoldPreparation, "fit", forbidden)
        with pytest.raises(ProjectError, match="maliyet"):
            calculate(r, s.data(), work)


def test_final_invalid_threshold_rejected_before_fit(tmp_path, monkeypatch):
    store, r, work, s = synthetic(tmp_path)
    with closing(store):
        out = calculate(r, s.data(), work)

        def forbidden(*args, **kwargs):
            raise AssertionError("Geçersiz final karardan önce fit yapılamaz")

        monkeypatch.setattr(FoldPreparation, "fit", forbidden)
        decision = dict(out["decision"], threshold=0.7)
        with pytest.raises(ProjectError, match="dondurulmalı"):
            calculate(
                dict(
                    r,
                    mode="final",
                    selected_model=out["selected_model"],
                    decision=decision,
                    expected_split_id=out["plan"]["split_id"],
                    expected_protocol_id=out["plan"]["protocol_id"],
                ),
                s.data(),
                work,
            )


def test_imbalanced_macro_weighted_and_micro_reference():
    # Actual A3/B1/C2, predicted A4/B1/C1; F1 A=4/7 B=0 C=2/3.
    for averaging, f1 in (("macro", 26 / 63), ("weighted", 32 / 63), ("micro", 1 / 2)):
        out = metrics(
            np.array(list("AAABCC")),
            np.array(list("ABAACA")),
            None,
            list("ABC"),
            settings(dict(averaging=averaging)),
            "validation",
        )
        assert out["confusion_matrix"] == [[2, 1, 0], [1, 0, 0], [1, 0, 1]]
        assert out["metrics"][3]["value"] == pytest.approx(f1)
