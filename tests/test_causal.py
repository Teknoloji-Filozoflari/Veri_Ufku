"""Known-effect structural fixtures, source membership and identification failures."""

import json
from contextlib import closing
from dataclasses import replace

import numpy as np
import polars as pl
import pytest
from scipy import stats
from test_dataset import column, prepare

from veri_ufku.importers.delimited import Control
from veri_ufku.statistics.causal import calculate, identification
from veri_ufku.statistics.causal_contracts import ASSUMPTIONS, CAUSAL_METHODS
from veri_ufku.statistics.contracts import AnalysisSpec
from veri_ufku.storage.analysis_store import publish
from veri_ufku.storage.project_model import ProjectError


def fixture(method="causal_randomized", n=600):
    rng = np.random.default_rng(41)
    x = rng.normal(size=n)
    t = rng.binomial(
        1, 0.5 if method == "causal_randomized" else 1 / (1 + np.exp(-0.25 * x)), size=n
    )
    if method == "causal_iv":
        z = rng.binomial(1, 0.5, n)
        t = z * rng.binomial(1, 0.8, n)
    else:
        z = rng.binomial(1, 0.5, n)
    y = 2 * t + 0.8 * x
    if method == "causal_did":
        return pl.DataFrame(
            dict(
                person=np.repeat(np.arange(80), 3),
                time=np.tile([0, 1, 2], 80),
                treatment=np.repeat([0, 1] * 40, 3),
                outcome=[
                    float(i % 5 + k + (2 if i % 2 and k == 2 else 0))
                    for i in range(80)
                    for k in range(3)
                ],
                covariate=np.repeat(np.arange(80), 3),
                instrument=np.repeat([0, 1] * 40, 3),
            )
        )
    return pl.DataFrame(
        dict(
            person=np.arange(n),
            time=np.ones(n),
            treatment=t,
            outcome=y,
            covariate=x,
            instrument=z,
        )
    )


def recipe(r, method="causal_randomized"):
    t, y, x = [column(r, k) for k in ("treatment", "outcome", "covariate")]
    features = (
        [x]
        if method
        in ("causal_adjustment", "causal_ipw", "causal_aipw", "causal_matching")
        else []
    )
    nodes = [
        dict(id=t, role="treatment", reason="Assigned exposure", x=0.2, y=0.5),
        dict(id=y, role="outcome", reason="Post exposure measurement", x=0.8, y=0.5),
    ]
    edges = [dict(**{"from": t, "to": y}, reason="Hypothesized effect")]
    if features:
        nodes.append(
            dict(id=x, role="confounder", reason="Baseline cause of both", x=0.5, y=0.1)
        )
        edges.extend(
            [
                dict(**{"from": x, "to": v}, reason="Baseline common cause")
                for v in (t, y)
            ]
        )
    if method == "causal_iv":
        z = column(r, "instrument")
        nodes.append(
            dict(id=z, role="other", reason="Exogenous encouragement", x=0.1, y=0.1)
        )
        edges.append(
            dict(**{"from": z, "to": t}, reason="Encouragement changes exposure")
        )
    plan = dict(
        dag=dict(nodes=nodes, edges=edges),
        assumptions={
            k: "Fixture structural design; not established by observed associations"
            for k in ASSUMPTIONS
        },
        randomization_evidence="seed41 independent Bernoulli",
        allocation=0.5,
        alternatives="Selection/unmeasured confounding/measurement effects",
        folds=3,
        overlap_epsilon=0.01,
        extreme_weight=100,
        caliper=0.1,
        post_time="2",
        instrument=column(r, "instrument") if method == "causal_iv" else "",
        placebo="",
        placebo_reason="",
        bias_deltas=[-1.0, 0.0, 1.0],
    )
    return AnalysisSpec(
        path="causal",
        method=method,
        x=y,
        y=t,
        key=column(r, "person"),
        time_column=column(r, "time"),
        features=features,
        question="ATE under declared structural design?",
        unit="points",
        observation_unit="person",
        scope="full",
        independent=True,
        measurement_confirmed=True,
        assumptions_confirmed=True,
        causal_plan=plan,
    )


@pytest.mark.parametrize("method", CAUSAL_METHODS[:4])
def test_first_stage_known_effect_and_atomic_roundtrip(tmp_path, method):
    store, r, w = prepare(tmp_path, fixture(method))
    with closing(store):
        spec = recipe(r, method)
        result = calculate(r, spec, w, Control())
        a = result["causal_analysis"]
        assert a["effect"] is not None, a
        assert a["effect"]["estimate"] == pytest.approx(2, abs=0.2)
        if method != "causal_randomized":
            seen = []
            for b in a["split_plan"]["nuisance_blocks"]:
                assert not set(b["train"]) & set(b["evaluation"])
                seen += b["evaluation"]
            assert len(seen) == len(set(seen)) == 600
        if method == "causal_aipw":
            assert (
                a["effect"]["interval"][0] < 2 < a["effect"]["interval"][1]
                or a["effect"]["se"] < 1e-12
            )
        state = publish(store, store.state, result)
        assert state["results"][-1]["analysis"]["plan"] == spec.causal_plan
        assert json.loads(open(result["paths"]["result"]).read())["causal_analysis"][
            "identification"
        ]["alternatives"]


@pytest.mark.parametrize("method", CAUSAL_METHODS[4:])
def test_later_substages_known_effect_and_mapping(tmp_path, method):
    store, r, w = prepare(tmp_path, fixture(method))
    with closing(store):
        s = recipe(r, method)
        out = calculate(r, s, w, Control())["causal_analysis"]
        assert out["effect"] is not None, out
        assert out["effect"]["estimate"] == pytest.approx(2, abs=0.2)
        if method == "causal_matching":
            f = pl.read_parquet(r["path"])
            source = {row["__vu_row_id"]: row for row in f.to_dicts()}
            deltas = []
            ids = []
            for p in out["pairs"]:
                a, b = source[p["treated_row_id"]], source[p["control_row_id"]]
                assert a["treatment"] == 1 and b["treatment"] == 0
                assert p["treated_source_record_id"] == a["__vu_source_record_id"]
                assert p["control_source_record_id"] == b["__vu_source_record_id"]
                deltas.append(a["outcome"] - b["outcome"])
                ids.extend([p["treated_row_id"], p["control_row_id"]])
            assert len(set(ids)) == len(ids)
            assert np.mean(deltas) == pytest.approx(out["effect"]["estimate"])
        if method == "causal_did":
            assert out["diagnostics"]["pretrend_placebo"]["estimate"] == 0


def test_positivity_separation_visible(tmp_path):
    f = fixture("causal_aipw").with_columns(
        (pl.col("covariate") > 0).cast(pl.Int64).alias("treatment")
    )
    store, r, w = prepare(tmp_path, f)
    with closing(store):
        out = calculate(r, recipe(r, "causal_aipw"), w, Control())["causal_analysis"]
        assert out["effect"] is None
        assert out["identification"]["status"] == "not_identified"
        assert "positivity" in str(out).lower() or "separation" in str(out).lower()


def test_missing_assumptions_latent_backdoor_mediator_and_cycle(tmp_path):
    store, r, w = prepare(tmp_path, fixture("causal_aipw"))
    with closing(store):
        s = recipe(r, "causal_aipw")
        p = s.causal_plan
        p["assumptions"]["consistency"] = ""
        assert calculate(r, s, w, Control())["causal_analysis"]["effect"] is None
        p["assumptions"]["consistency"] = "consistent"
        p["dag"]["nodes"].append(
            dict(id="latent:U", role="confounder", reason="unmeasured", x=0.1, y=0.1)
        )
        p["dag"]["edges"].extend(
            [
                dict(**{"from": "latent:U", "to": v}, reason="unmeasured cause")
                for v in (s.x, s.y)
            ]
        )
        assert not identification(s)["backdoor_separated"]
        p["dag"]["edges"].append(dict(**{"from": s.x, "to": s.y}, reason="cycle"))
        with pytest.raises(ProjectError, match="cycle|döngü|DAG"):
            s.validate(r["columns"])


def test_randomized_reference_cancel_and_source_tamper(tmp_path):
    store, r, w = prepare(tmp_path, fixture())
    with closing(store):
        s = recipe(r)
        out = calculate(r, s, w, Control())
        f = fixture()
        a = f.filter(pl.col("treatment") == 1)["outcome"].to_numpy()
        b = f.filter(pl.col("treatment") == 0)["outcome"].to_numpy()
        ref = stats.ttest_ind(a, b, equal_var=False).confidence_interval()
        assert out["causal_analysis"]["effect"]["interval"] == pytest.approx(
            [ref.low, ref.high]
        )
        bad = replace(s, features=[column(r, "covariate")])
        with pytest.raises(ProjectError):
            bad.validate(r["columns"])
        out["causal_analysis"]["effect"]["estimate"] += 1
        with pytest.raises(ProjectError):
            publish(store, store.state, out)


@pytest.mark.parametrize("method", ["causal_did", "causal_iv"])
def test_method_specific_diagnostics_fail_visible(tmp_path, method):
    f = fixture(method)
    if method == "causal_did":
        f = f.with_columns(
            (pl.col("outcome") + pl.col("treatment") * pl.col("time") * 5).alias(
                "outcome"
            )
        )
    else:
        # Instrument independent of treatment: zero first stage, not weak-IV CI.
        f = f.with_columns(
            (pl.col("person") % 2).alias("treatment"),
            ((pl.col("person") // 2) % 2).alias("instrument"),
        )
    store, r, w = prepare(tmp_path, f)
    with closing(store):
        out = calculate(r, recipe(r, method), w, Control())["causal_analysis"]
        assert out["effect"] is None
        assert out["identification"]["status"] == "not_identified"
        assert out["diagnostics"]


def test_collider_adjustment_and_dag_dseparation(tmp_path):
    store, r, w = prepare(tmp_path, fixture("causal_aipw"))
    with closing(store):
        s = recipe(r, "causal_aipw")
        x = s.features[0]
        s.causal_plan["dag"]["edges"] = [
            dict(**{"from": v, "to": x}, reason="Collider") for v in (s.y, s.x)
        ]
        s.causal_plan["dag"]["nodes"][-1]["role"] = "collider"
        s.causal_plan["dag"]["nodes"].append(
            dict(id="latent:U", role="confounder", reason="Common cause", x=0.1, y=0.1)
        )
        s.causal_plan["dag"]["edges"] = [
            dict(**{"from": a, "to": b}, reason="Collider backdoor")
            for a, b in [("latent:U", s.y), ("latent:U", x), (s.x, x)]
        ]
        i = identification(s)
        assert not i["backdoor_separated"] and i["blockers"]
        s.causal_plan["dag"]["edges"] = [
            dict(**{"from": s.y, "to": x}, reason="Mediator"),
            dict(**{"from": x, "to": s.x}, reason="Mediator"),
        ]
        s.causal_plan["dag"]["nodes"][-1]["role"] = "mediator"
        assert "descendant" in str(identification(s))


def test_cancel_budget_missing_repeated_and_safe_plan(tmp_path):
    import threading

    from veri_ufku.jobs.workers import Canceled

    store, r, w = prepare(tmp_path, fixture())
    with closing(store):
        cancel = threading.Event()
        cancel.set()
        with pytest.raises(Canceled):
            calculate(r, recipe(r), w, Control(cancel))
        with pytest.raises(ProjectError):
            replace(recipe(r), causal_plan={"code": "exec"}).validate(r["columns"])
        with pytest.raises(ProjectError):
            replace(recipe(r), time_column=[]).validate(r["columns"])
        bad = recipe(r)
        bad.causal_plan["instrument"] = []
        with pytest.raises(ProjectError):
            bad.validate(r["columns"])
        bad = recipe(r)
        bad.causal_plan["dag"]["edges"][0]["from"] = []
        with pytest.raises(ProjectError):
            bad.validate(r["columns"])
        f = pl.read_parquet(r["path"]).with_columns(pl.lit(1).alias("person"))
        f.write_parquet(w / "repeated.parquet")
        from veri_ufku.statistics.causal import load

        with pytest.raises(ProjectError, match="tek satır"):
            load(dict(r, path=str(w / "repeated.parquet")), recipe(r), Control())


def test_iv_against_independent_2sls_reference(tmp_path):
    from statsmodels.sandbox.regression.gmm import IV2SLS

    f = fixture("causal_iv")
    store, r, w = prepare(tmp_path, f)
    with closing(store):
        estimate = calculate(r, recipe(r, "causal_iv"), w, Control())[
            "causal_analysis"
        ]["effect"]["estimate"]
        exog = np.column_stack([np.ones(f.height), f["treatment"].to_numpy()])
        instrument = np.column_stack([np.ones(f.height), f["instrument"].to_numpy()])
        reference = IV2SLS(f["outcome"].to_numpy(), exog, instrument).fit()
        assert estimate == pytest.approx(reference.params[1], abs=1e-12)


def test_placebo_and_bias_scenarios_are_assumptions_not_corrections(tmp_path):
    store, r, w = prepare(tmp_path, fixture())
    with closing(store):
        s = recipe(r)
        s.causal_plan["placebo"] = column(r, "covariate")
        s.causal_plan["placebo_reason"] = (
            "Pretreatment structural X, not affected by treatment"
        )
        out = calculate(r, s, w, Control())["causal_analysis"]
        assert out["diagnostics"]["placebo"]["association"]["estimate"] is not None
        assert [a["estimate"] for a in out["sensitivity"]] == pytest.approx(
            [
                out["effect"]["estimate"] - delta
                for delta in s.causal_plan["bias_deltas"]
            ]
        )
        assert "Hypothetical" in out["sensitivity"][0]["interpretation"]
        s.causal_plan["placebo_reason"] = ""
        with pytest.raises(ProjectError, match="Placebo"):
            s.validate(r["columns"])


def test_finite_overlap_extreme_weight_diagnostics_without_clipping(tmp_path):
    f = fixture("causal_aipw")
    rng = np.random.default_rng(23)
    x = f["covariate"].to_numpy()
    t = rng.binomial(1, 1 / (1 + np.exp(-1.2 * x)))
    f = f.with_columns(pl.Series("treatment", t), pl.Series("outcome", 2 * t + 0.8 * x))
    store, r, w = prepare(tmp_path, f)
    with closing(store):
        s = recipe(r, "causal_aipw")
        s.causal_plan.update(overlap_epsilon=0.2, extreme_weight=5)
        out = calculate(r, s, w, Control())["causal_analysis"]
        assert out["effect"] is None
        d = out["diagnostics"]["overlap"]
        assert d["outside_epsilon"] > 0 and d["maximum_weight"] > 5
        assert len(d["propensity_by_row"]) == f.height
        assert all(sum(a["histogram"]) > 0 for a in d["arms"])
        assert len(d["balance_before"]) == len(d["balance_ipw"]) == 1
        assert "clipping/trimming" in str(out)
