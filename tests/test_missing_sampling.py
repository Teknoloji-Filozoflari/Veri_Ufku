"""Phase33 independent hand references, fold boundary, typed weights and durable identities."""

import json
import math
import threading
from contextlib import closing
from dataclasses import replace

import numpy as np
import polars as pl
import pytest
from test_dataset import column, prepare
from test_preparation import request, specification

from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.baseline import FoldPreparation
from veri_ufku.modeling.baseline import calculate as train
from veri_ufku.modeling.preparation import calculate as prep
from veri_ufku.modeling.validation import ValidationSpec
from veri_ufku.statistics.contracts import AnalysisSpec
from veri_ufku.statistics.engine import calculate
from veri_ufku.statistics.missing_sampling import rubin_pool, survey_mean
from veri_ufku.storage.analysis_store import publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def spec(r, method, **kw):
    return AnalysisSpec(
        path="advanced",
        method=method,
        x=column(r, "x"),
        question="Eksiklik ve tasarım",
        hypothesis="Açık varsayım",
        unit="puan",
        observation_unit="kişi / bağımsız PSU",
        independent=True,
        measurement_confirmed=True,
        assumptions_confirmed=True,
        scope="full",
        **kw,
    )


def test_rubin_hand_calculation_and_barnard_rubin_not_average_se():
    r = rubin_pool([[1.0], [2.0], [3.0]], [[[4.0]]] * 3, 20)
    assert r["estimates"] == [2.0]
    assert r["within_covariance"] == [[4.0]]
    assert r["between_covariance"] == [[1.0]]
    assert r["total_covariance"][0][0] == pytest.approx(16 / 3)
    assert r["standard_errors"][0] == pytest.approx(math.sqrt(16 / 3))
    # lambda=1/4, old df=32; observed df=(21/23)*20*(3/4)=315/23
    assert r["df"][0] == pytest.approx(1 / (1 / 32 + 23 / 315))
    assert r["confidence_intervals"][0][0] < 2 < r["confidence_intervals"][0][1]
    with pytest.raises(ProjectError):
        rubin_pool([[1.0]], [[[4.0]]], 20)
    with pytest.raises(ProjectError):
        rubin_pool([[1.0], [2.0]], [[[-4.0]]] * 2, 20)


@pytest.mark.parametrize(
    "weight_type,variance,df", [("frequency", 6.25, 3), ("analytic", 18.75, 1)]
)
def test_hand_weighted_mean_semantics_and_reopen_exportable_identity(
    tmp_path, weight_type, variance, df
):
    store, r, w = prepare(
        tmp_path, pl.DataFrame(dict(x=[10.0, 20.0], weight=[1.0, 3.0]))
    )
    root = store.root
    with closing(store):
        out = calculate(
            r,
            spec(
                r, "weighted_mean", weight_type=weight_type, weight=column(r, "weight")
            ),
            w,
        )
        assert out["advanced"]["estimate"] == 17.5
        assert out["advanced"]["variance"] == pytest.approx(variance)
        assert out["advanced"]["df"] == df
        saved = publish(store, store.state, out)
        artifact = saved["results"][-1]["analysis"]["artifact_uris"]["details"]
        ids = pl.read_parquet(store.path(artifact))
        assert (
            ids["source_record_id"].to_list()
            == pl.read_parquet(r["path"])["__vu_source_record_id"].to_list()
        )
    with closing(ProjectStore.open(root)) as reopened:
        assert reopened.state["results"][-1]["analysis"]["advanced"][
            "variance"
        ] == pytest.approx(variance)


@pytest.mark.parametrize(
    "values,kind",
    [
        ([-1.0, 2.0], "frequency"),
        ([None, 2.0], "analytic"),
        ([0.0, 0.0], "sample_weight"),
        ([1.5, 2.0], "frequency"),
        ([0.0, 2.0], "survey"),
        ([math.inf, 2.0], "analytic"),
    ],
)
def test_bad_weights_rejected_without_mutation(tmp_path, values, kind):
    store, r, w = prepare(
        tmp_path,
        pl.DataFrame(
            dict(
                x=[10.0, 20.0],
                z=[0.0, 1.0],
                weight=values,
                h=["A", "A"],
                psu=["1", "2"],
            )
        ),
    )
    with closing(store):
        before = store.commit_id
        s = spec(
            r,
            "weighted_fit"
            if kind == "sample_weight"
            else "survey_mean"
            if kind == "survey"
            else "weighted_mean",
            weight_type=kind,
            weight=column(r, "weight"),
            features=[column(r, "z")] if kind == "sample_weight" else [],
            strata=column(r, "h") if kind == "survey" else "",
            psu=column(r, "psu") if kind == "survey" else "",
        )
        with pytest.raises(ProjectError):
            calculate(r, s, w)
        assert store.commit_id == before


def test_unsupported_weight_old_and_new_methods_rejected(tmp_path):
    store, r, w = prepare(
        tmp_path,
        pl.DataFrame(
            dict(x=[1.0, 2.0, 3.0], weight=[1.0, 1.0, 1.0], z=[2.0, 1.0, 4.0])
        ),
    )
    with closing(store):
        for method, kind in [
            ("mi_mean", "analytic"),
            ("weighted_ols", "survey"),
            ("survey_mean", "frequency"),
            ("weighted_fit", "frequency"),
        ]:
            with pytest.raises(ProjectError, match="desteklemiyor"):
                spec(r, method, weight_type=kind, weight=column(r, "weight")).validate(
                    r["columns"]
                )
        old = replace(
            spec(r, "missing_patterns"),
            path="numeric",
            method="pearson",
            y=column(r, "z"),
            weight_type="frequency",
            weight=column(r, "weight"),
        )
        with pytest.raises(ProjectError, match="desteklemiyor"):
            old.validate(r["columns"])


def test_survey_hand_two_strata_nested_psus_and_no_lonely_adjustment(tmp_path):
    # Weighted mean10. PSU residual totals/W: A=(-2.5,-1.5), B=(1,3).
    # WR Taylor variance2*(.5²+.5²)+2*(1²+1²)=5, df2.
    frame = pl.DataFrame(
        dict(
            x=[0.0, 4.0, 14.0, 22.0],
            w=[1.0, 1.0, 1.0, 1.0],
            h=["A", "A", "B", "B"],
            psu=["1", "2", "1", "2"],
        )
    )
    store, r, w = prepare(tmp_path, frame)
    with closing(store):
        s = spec(
            r,
            "survey_mean",
            weight_type="survey",
            weight=column(r, "w"),
            strata=column(r, "h"),
            psu=column(r, "psu"),
        )
        result = calculate(r, s, w)["advanced"]
        assert result["estimate"] == 10
        # Actual residual totals are (-2.5,-1.5),(1,3); variance=1+4=5.
        assert result["variance"] == 5
        assert result["df"] == 2 and result["psus"] == 4
        assert result["confidence_interval"] == pytest.approx(
            [
                10 - 4.302652729696142 * math.sqrt(5),
                10 + 4.302652729696142 * math.sqrt(5),
            ]
        )
        assert result["design_effect"] == pytest.approx(5 / (74 / 3))
        with pytest.raises(ProjectError, match="PSU"):
            survey_mean(
                np.array([1.0, 2.0, 3.0]),
                np.ones(3),
                ["A", "B", "B"],
                ["1", "1", "2"],
                0.95,
            )


@pytest.mark.parametrize(
    "method", ["sample_random", "sample_stratified", "sample_cluster"]
)
def test_seed_sampling_membership_and_cluster_integrity(tmp_path, method):
    store, r, w = prepare(
        tmp_path,
        pl.DataFrame(dict(x=list(range(12)), g=["A"] * 4 + ["B"] * 4 + ["C"] * 4)),
    )
    with closing(store):
        s = spec(
            r,
            method,
            sample_size=2,
            group=column(r, "g") if method != "sample_random" else "",
        )
        a = calculate(r, s, w)
        b = calculate(r, s, w)
        assert a["advanced"] == b["advanced"]
        members = pl.read_parquet(a["paths"]["members"])
        assert members.height == members["row_id"].n_unique()
        details = pl.read_parquet(a["paths"]["details"])
        if method == "sample_cluster":
            assert details.group_by("g").len()["len"].to_list() == [4, 4]
        if method == "sample_stratified":
            assert details.group_by("g").len()["len"].to_list() == [2, 2, 2]
        assert set(details["source_record_id"]) <= set(
            pl.read_parquet(r["path"])["__vu_source_record_id"]
        )
        assert not a["advanced"]["representation_guaranteed"]
        publish(store, store.state, b)


@pytest.mark.parametrize("method", ["mi_mean", "mi_ols"])
def test_mi_separate_realizations_observed_cells_and_delta_sensitivity(
    tmp_path, method
):
    z = np.linspace(0, 8, 40)
    x = [float(2 * v + np.sin(v)) if i % 5 else None for i, v in enumerate(z)]
    store, r, w = prepare(tmp_path, pl.DataFrame(dict(x=x, z=z)))
    with closing(store):
        s = spec(r, method, features=[column(r, "z")], imputations=3, iterations=3)
        out = calculate(r, s, w)
        data = out["advanced"]
        details = pl.read_parquet(out["paths"]["details"])
        assert details.height == 120 and data["imputation_kind"] == "multiple"
        assert data["mechanism_detected"] is None
        original = pl.read_parquet(r["path"])
        for k in range(1, 4):
            draw = details.filter(pl.col("imputation") == k)
            assert draw["row_id"].to_list() == original["__vu_row_id"].to_list()
            observed = [i for i, v in enumerate(x) if v is not None]
            assert draw["value_0"][observed].to_list() == [x[i] for i in observed]
            assert draw["value_1"].to_list() == z.tolist()
        if method == "mi_mean":
            minus, base, plus = data["scenarios"]
            assert plus["estimates"][0] - base["estimates"][0] == pytest.approx(8 / 40)
            assert minus["estimates"][0] - base["estimates"][0] == pytest.approx(
                -8 / 40
            )
        else:
            assert len(data["scenarios"][1]["total_covariance"]) == 2
        again = calculate(r, s, w)
        assert again["advanced"] == data
        publish(store, store.state, again)
        assert store.state["results"][-1]["analysis"]["artifact_uris"]["details"]


def test_patterns_indicators_null_not_mechanism(tmp_path):
    store, r, w = prepare(
        tmp_path, pl.DataFrame(dict(x=[1.0, None, 2.0, None], z=[None, 1.0, 2.0, None]))
    )
    with closing(store):
        out = calculate(r, spec(r, "missing_patterns", features=[column(r, "z")]), w)
        assert out["advanced"]["mechanism_detected"] is None
        assert out["advanced"]["column_missing"] == {
            column(r, "x"): 2,
            column(r, "z"): 2,
        }
        assert len(out["advanced"]["patterns"]) == 4
        detail = pl.read_parquet(out["paths"]["details"])
        assert detail["missing_0"].to_list() == [False, True, False, True]
        assert out["primary"]["p_value"] is None
        publish(store, store.state, out)


@pytest.mark.parametrize("strategy", ["knn", "iterative"])
def test_fold_joint_fit_validation_values_never_learned_and_all_missing_rejected(
    tmp_path, strategy, monkeypatch
):
    n = 80
    frame = pl.DataFrame(
        dict(
            x=[None if i % 7 == 0 else float(i) for i in range(n)],
            z=[float(i) + np.sin(i) for i in range(n)],
            y=[float(i % 11) for i in range(n)],
        )
    )
    store, _, w = prepare(tmp_path, frame)
    with closing(store):
        r = request(store)
        p = replace(
            specification(r, numeric_imputation=strategy, scaling="none"),
            features=(column(r, "x"), column(r, "z")),
            missing_indicator=True,
            imputation_iterations=3,
        )
        report = prep(r, p, w)
        assert not report["blockers"]
        original = pl.read_parquet(r["path"])
        f = FoldPreparation(report["plan"], p, r["columns"]).fit(original.head(40))
        before = json.dumps(f.summary_, sort_keys=True)
        validation = original.tail(40).with_columns(pl.lit(1e8).alias("z"))
        transformed = f.transform(validation)
        assert transformed.shape == (40, 4)
        assert f.fit_row_ids_ == original.head(40)["__vu_row_id"].to_list()
        assert before == json.dumps(f.summary_, sort_keys=True)
        # Transform-only validation changes cannot alter fitted training transform.
        after = f.transform(original.head(40))
        np.testing.assert_allclose(
            after[:, 1], original.head(40)["x"].is_null().to_numpy()
        )
        with pytest.raises(ProjectError, match="tamamen eksik"):
            FoldPreparation(report["plan"], p, r["columns"]).fit(
                original.head(40).with_columns(
                    pl.lit(None, dtype=pl.Float64).alias("x")
                )
            )
        calls = []
        fit = FoldPreparation.fit

        def spy(self, X, y=None):
            calls.append(set(X["__vu_row_id"]))
            return fit(self, X, y)

        monkeypatch.setattr(FoldPreparation, "fit", spy)
        v = ValidationSpec(
            prediction_moment="Ölçüm öncesi",
            availability={
                i: dict(offset_seconds=0, note="Önceden bilinir") for i in p.features
            },
        )
        result = train(dict(r, preparation=report), v.data(), w)
        test = set(result["plan"]["membership"]["test"])
        assert calls and all(ids.isdisjoint(test) for ids in calls)
        assert all(len(ids) < n for ids in calls)
        membership = result["plan"]["membership"]
        allowed = [
            set(membership["train"]),
            *[set(f["train"]) for f in membership["folds"]],
        ]
        assert all(ids in allowed for ids in calls)
        assert all(
            set(f["train"]).isdisjoint(f["validation"]) for f in membership["folds"]
        )


def test_advanced_cancel_before_work_and_source_untouched(tmp_path):
    store, r, w = prepare(
        tmp_path, pl.DataFrame(dict(x=[1.0, None, 3.0, 4.0], z=[1.0, 2.0, 3.0, 4.0]))
    )
    with closing(store):
        before = pl.read_parquet(r["path"])
        cancel = threading.Event()
        cancel.set()
        with pytest.raises(Canceled):
            calculate(
                r, spec(r, "mi_mean", features=[column(r, "z")]), w, Control(cancel)
            )
        assert pl.read_parquet(r["path"]).equals(before)


def test_sample_weight_linear_loss_without_survey_inference(tmp_path):
    store, r, w = prepare(
        tmp_path,
        pl.DataFrame(
            dict(
                x=[1.0, 3.0, 5.0, 7.0],
                z=[0.0, 1.0, 2.0, 3.0],
                weight=[0.0, 1.0, 1.0, 2.0],
            )
        ),
    )
    with closing(store):
        for method, kind in [
            ("weighted_fit", "sample_weight"),
            ("weighted_ols", "analytic"),
        ]:
            s = spec(
                r,
                method,
                features=[column(r, "z")],
                weight_type=kind,
                weight=column(r, "weight"),
            )
            if kind == "analytic":
                with pytest.raises(ProjectError):
                    calculate(r, s, w)
            else:
                out = calculate(r, s, w)["advanced"]
                assert out["estimates"] == pytest.approx([1.0, 2.0])
                assert out["covariance"] is None and not out["inference"]


def test_parent_rejects_forged_mi_covariance_before_active(tmp_path):
    store, r, w = prepare(
        tmp_path,
        pl.DataFrame(
            dict(x=[1.0, None, 3.0, 4.0, 5.0, 6.0], z=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
        ),
    )
    with closing(store):
        s = spec(r, "mi_mean", features=[column(r, "z")], imputations=3, iterations=3)
        result = calculate(r, s, w)
        result["advanced"]["per_imputation_covariances"][0][0][0] += 10
        content = {
            k: v
            for k, v in result.items()
            if k not in ("paths", "fingerprints", "member_digest")
        }
        from pathlib import Path

        from veri_ufku.importers.delimited import hash_artifact

        path = Path(result["paths"]["result"])
        path.write_text(
            json.dumps(content, ensure_ascii=False, allow_nan=False, sort_keys=True)
        )
        result["fingerprints"]["result"] = hash_artifact(path, Control())
        before = store.commit_id
        with pytest.raises(ProjectError, match="kovaryans"):
            publish(store, store.state, result)
        assert store.commit_id == before and not store.state["results"]
