"""Phase47 reference geometry, real backend support, novelty and durable identity."""

import threading
from contextlib import closing
from dataclasses import replace

import numpy as np
import polars as pl
import pytest
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from test_dataset import column, prepare

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.exploration import evaluation, preflight
from veri_ufku.modeling.unsupervised import calculate
from veri_ufku.modeling.unsupervised_contracts import CLUSTER_METHODS, UnsupervisedSpec
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.unsupervised_store import load, publish, transfer


def fixture(tmp_path):
    rng = np.random.default_rng(7)
    x = np.vstack(
        [rng.normal(-4, 0.3, (30, 2)), rng.normal(4, 0.3, (30, 2)), [[20.0, 20.0]]]
    )
    store, request, work = prepare(
        tmp_path, pl.DataFrame(dict(x=x[:, 0], y=x[:, 1], label=[0] * 60 + [1]))
    )
    return store, request, work, x


def spec(r, method, **kw):
    return UnsupervisedSpec(
        method,
        (column(r, "x"), column(r, "y")),
        clusters=2,
        min_samples=5,
        eps=0.8,
        scaling="none",
        **kw,
    )


@pytest.mark.parametrize("method", CLUSTER_METHODS)
def test_every_cluster_backend_reference_save_reopen_transfer(tmp_path, method):
    store, r, work, x = fixture(tmp_path)
    root = store.root
    with closing(store):
        before = pl.read_parquet(r["path"])
        out = calculate(r, spec(r, method, stability_runs=2), work)
        members = pl.read_parquet(out["assignment_path"])
        labels = members["cluster"].to_numpy()
        report = out["method_state"]["comparison"][0]
        mask = labels >= 0
        if report["metrics"]["silhouette"] is not None:
            assert report["metrics"]["silhouette"] == pytest.approx(
                silhouette_score(x[mask], labels[mask])
            )
            assert report["metrics"]["davies_bouldin"] == pytest.approx(
                davies_bouldin_score(x[mask], labels[mask])
            )
            assert report["metrics"]["calinski_harabasz"] == pytest.approx(
                calinski_harabasz_score(x[mask], labels[mask])
            )
        assert len(report["stability"]) == 2
        if method == "gmm":
            assert np.allclose(
                np.sum(out["method_state"]["soft_membership"], axis=1), 1
            )
            assert np.isfinite([report["aic"], report["bic"]]).all()
        if method == "agglomerative":
            assert len(out["method_state"]["dendrogram_linkage"]) == len(x) - 1
            assert "<svg" in out["method_state"]["dendrogram_svg"]
        _, record = publish(store, store.state, out)
        state, version = transfer(store, store.state, record["id"])
        ds = next(d for d in state["datasets"] if d["version_id"] == version)
        assert (
            pl.read_parquet(store.path(ds["snapshot_uri"]))
            .select(before.columns)
            .equals(before)
        )
    with closing(ProjectStore.open(root)) as reopened:
        saved, m, source, _ = load(reopened, record)
        assert (
            saved["method_state"] == out["method_state"]
            and m.equals(members)
            and source.equals(before)
        )


def test_shared_comparison_and_noise_edge(tmp_path):
    store, r, work, _ = fixture(tmp_path)
    with closing(store):
        out = calculate(
            r,
            spec(r, "kmeans", compare_methods=CLUSTER_METHODS, stability_runs=1),
            work,
        )
        assert {p["method"] for p in out["method_state"]["comparison"]} == set(
            CLUSTER_METHODS
        )
        one = calculate(r, replace(spec(r, "agglomerative"), clusters=1), work)
        assert one["method_state"]["comparison"][0]["metrics"]["silhouette"] is None
        noise = calculate(r, replace(spec(r, "dbscan"), eps=1e-10), work)
        assert noise["noise_count"] == 61
        assert (
            noise["method_state"]["comparison"][0]["metrics"]["calinski_harabasz"]
            is None
        )


@pytest.mark.parametrize("method", ["lof", "one_class_svm", "robust_covariance"])
@pytest.mark.parametrize("mode", ["outlier", "novelty"])
def test_anomaly_direction_disjoint_novelty_and_durable_nulls(tmp_path, method, mode):
    store, r, work, x = fixture(tmp_path)
    with closing(store):
        out = calculate(r, spec(r, method, anomaly_mode=mode), work)
        m = pl.read_parquet(out["assignment_path"])
        scored = m["anomaly_score"].is_not_null()
        assert (m["anomaly_score"].drop_nulls() > out["threshold"]).to_list() == m[
            "anomaly_candidate"
        ].drop_nulls().to_list()
        assert out["evaluation"]["precision"] is None
        if mode == "novelty":
            train = out["method_state"]["training_indices"]
            test = out["method_state"]["scored_indices"]
            assert not set(train) & set(test) and sorted(train + test) == list(
                range(len(x))
            )
            assert m["anomaly_score"].null_count() == len(train)
            assert out["fit_row_ids"] == m["__vu_row_id"].gather(train).to_list()
            assert "disjoint" in out["fit_scope"]
        else:
            assert scored.all()
            assert m["anomaly_score"][-1] > np.median(m["anomaly_score"].to_numpy())
        _, record = publish(store, store.state, out)
        saved, actual, _, _ = load(store, record)
        assert actual.equals(m) and saved["score_direction"].startswith("higher")
        if mode == "novelty":
            _, version = transfer(store, store.state, record["id"])
            ds = next(d for d in store.state["datasets"] if d["version_id"] == version)
            assert pl.read_parquet(store.path(ds["snapshot_uri"]))[
                "anomali_skoru"
            ].null_count() == len(train)


def test_labeled_pr_cost_hand_reference_and_actual(tmp_path):
    truth = np.array([0, 0, 1, 1])
    scores = np.array([0.1, 0.8, 0.7, 0.9])
    flags = scores > 0.75
    s = UnsupervisedSpec("lof", ("x",), false_positive_cost=2, false_negative_cost=3)
    report = evaluation(truth, scores, flags, s)
    assert report["precision"] == report["recall"] == 0.5 and report["total_cost"] == 5
    assert report["average_precision"] == pytest.approx((1 + 2 / 3) / 2)
    store, r, work, _ = fixture(tmp_path)
    with closing(store):
        out = calculate(r, spec(r, "lof", label_column=column(r, "label")), work)
        assert (
            out["evaluation"]["labels_available"]
            and out["evaluation"]["evaluated_rows"] == 61
        )
        publish(store, store.state, out)


def test_metric_rules_resource_cancel_mixed_and_rank(tmp_path):
    store, r, work, _ = fixture(tmp_path)
    with closing(store):
        s = spec(r, "agglomerative")
        with pytest.raises(ProjectError, match="Euclidean"):
            replace(s, metric="manhattan").validate(r["columns"])
        out = calculate(r, replace(s, metric="manhattan", linkage="average"), work)
        assert out["method_state"]["comparison"][0]["metrics"]["davies_bouldin"] is None
        with pytest.raises(ProjectError, match="n²"):
            preflight(s, 3001, ComputeBudget())
        with pytest.raises(ProjectError, match="n²"):
            preflight(s, 61, replace(ComputeBudget(), ram_bytes=100))
        event = threading.Event()
        event.set()
        with pytest.raises(Canceled):
            calculate(r, s, work, Control(event))
        r["semantic_metadata"] = {column(r, "x"): dict(role="category")}
        with pytest.raises(ProjectError, match="kategori"):
            calculate(r, s, work)


def test_novelty_train_only_scaler_and_lof_reference(tmp_path):
    from sklearn.neighbors import LocalOutlierFactor
    from sklearn.preprocessing import StandardScaler

    store, r, work, raw = fixture(tmp_path)
    with closing(store):
        settings = replace(spec(r, "lof", anomaly_mode="novelty"), scaling="standard")
        out = calculate(r, settings, work)
        train = out["method_state"]["training_indices"]
        test = out["method_state"]["scored_indices"]
        scaler = StandardScaler().fit(raw[train])
        assert out["scaling_state"]["mean"] == scaler.mean_.tolist()
        assert out["scaling_state"]["mean"] != raw.mean(axis=0).tolist()
        x = scaler.transform(raw)
        model = LocalOutlierFactor(n_neighbors=5, contamination=0.05, novelty=True).fit(
            x[train]
        )
        assignments = pl.read_parquet(out["assignment_path"])
        assert assignments["anomaly_score"].gather(test).to_numpy() == pytest.approx(
            -model.score_samples(x[test])
        )
        labeled = calculate(r, replace(settings, label_column=column(r, "label")), work)
        assert labeled["evaluation"]["scope"] == "heldout novelty"
        assert labeled["evaluation"]["evaluated_rows"] == len(test)


def test_metric_soft_membership_tamper_atomic_reject_and_optional_unavailable(
    tmp_path, monkeypatch
):
    import builtins
    import copy

    store, r, work, _ = fixture(tmp_path)
    with closing(store):
        out = calculate(r, spec(r, "gmm"), work)
        before = copy.deepcopy(store.state)
        out["method_state"]["soft_membership"][0] = [0.0, 1.0]
        with pytest.raises(ProjectError, match="kaynağa"):
            publish(store, store.state, out)
        assert store.state == before
        original = builtins.__import__

        def unavailable(name, *args, **kwargs):
            if name == "sklearn.cluster" and "HDBSCAN" in (
                args[2] if len(args) > 2 else kwargs.get("fromlist", ())
            ):
                raise ImportError("simulated absent optional adapter")
            return original(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", unavailable)
        with pytest.raises(ProjectError, match="ortamı yok"):
            calculate(r, spec(r, "hdbscan"), work)


def test_gmm_aic_bic_parameter_penalty_and_intrinsic_anomaly_geometry(tmp_path):
    from sklearn.mixture import GaussianMixture

    store, r, work, raw = fixture(tmp_path)
    with closing(store):
        out = calculate(r, spec(r, "gmm"), work)
        model = GaussianMixture(
            n_components=2,
            covariance_type="full",
            random_state=42,
            n_init=3,
            reg_covar=1e-6,
            max_iter=300,
        ).fit(raw)
        state = out["method_state"]
        assert state["aic"] == pytest.approx(model.aic(raw))
        assert state["bic"] == pytest.approx(model.bic(raw))
        # full Gaussian k=2,d=2: (k-1) mixing + k*d means + k*d*(d+1)/2 covariance =11.
        assert state["bic"] - state["aic"] == pytest.approx((np.log(61) - 2) * 11)
        for method in ("one_class_svm", "robust_covariance"):
            with pytest.raises(ProjectError, match="Euclidean"):
                replace(spec(r, method), metric="manhattan").validate(r["columns"])
