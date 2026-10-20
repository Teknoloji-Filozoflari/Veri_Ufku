"""Representation reference statistics, fold isolation, honest operation and source identity."""

import importlib.util
import json
from contextlib import closing

import numpy as np
import polars as pl
import pytest
from scipy import sparse
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.preprocessing import StandardScaler
from test_dataset import column, prepare

from veri_ufku.importers.delimited import Control
from veri_ufku.statistics.contracts import AnalysisSpec
from veri_ufku.statistics.dimension_contracts import (
    DIMENSION_METHODS,
    SELECTORS,
    VISUAL,
)
from veri_ufku.statistics.dimensions import calculate, transform
from veri_ufku.storage.analysis_store import publish
from veri_ufku.storage.project_model import ProjectError


def fixture(method="dimension_pca", n=120):
    rng = np.random.default_rng(44)
    if method == "dimension_nmf":
        latent = rng.uniform(0.1, 2, (n, 2))
        x = latent @ np.array([[1.0, 0.2, 0.8, 0.5], [0.2, 1.0, 0.3, 0.6]])
    elif method == "dimension_ica":
        sources = np.c_[
            rng.laplace(size=n),
            rng.uniform(-2, 2, size=n),
            rng.standard_t(3, size=n),
            rng.laplace(size=n),
        ]
        x = sources @ np.array(
            [[1, 0.5, 0, 0], [0.2, 1, 0.3, 0], [0, 0, 1, 0.2], [0.1, 0, 0.2, 1.0]]
        )
    else:
        x = rng.normal(size=(n, 4))
        x[:, 3] = 0.8 * x[:, 0] + 0.1 * rng.normal(size=n)
    return pl.DataFrame(
        {
            **{f"x{i}": x[:, i] for i in range(4)},
            "target": 3 * x[:, 0] - 0.5 * x[:, 1],
            "binary": (x[:, 0] > np.median(x[:, 0])).astype(int),
            "person": list(range(n)),
        }
    )


def recipe(r, method="dimension_pca", purpose=None, **changes):
    purpose = purpose or (
        "visual"
        if method in VISUAL
        else "model_input"
        if method in SELECTORS
        else "compression"
    )
    p = dict(
        purpose=purpose,
        fit_scope="development" if purpose == "model_input" else "full",
        target_kind="regression",
        scaling="none" if method == "dimension_nmf" else "standard",
        missing="reject",
        storage="dense",
        components=2,
        variance_threshold=0.0,
        folds=3,
        inner_folds=2,
        batch_size=30,
        perplexity=5.0,
        neighbors=5,
        profile=[0.5] * 4,
    )
    p.update(changes)
    features = [column(r, f"x{i}") for i in range(4)]
    return AnalysisSpec(
        path="dimensions",
        method=method,
        x=features[0],
        y=column(r, "binary" if p["target_kind"] == "binary" else "target")
        if purpose == "model_input"
        else "",
        features=features,
        question="Predeclared representation/selection question",
        observation_unit="independent row",
        scope="full",
        independent=True,
        measurement_confirmed=True,
        assumptions_confirmed=True,
        max_iterations=1000,
        dimension_plan=p,
    )


@pytest.mark.parametrize(
    "method", [m for m in DIMENSION_METHODS if m != "dimension_umap"]
)
def test_numeric_method_real_outputs_and_atomic_publish(tmp_path, method):
    store, r, w = prepare(tmp_path, fixture(method))
    with closing(store):
        s = recipe(r, method)
        out = calculate(r, s, w, Control())
        a = out["dimension_analysis"]
        assert (
            not a["display"]["class_labels"] and not a["display"]["heldout_rows_shown"]
        )
        assert len(a["fit_row_ids"]) == out["used_rows"]
        if method in ("dimension_nmf", "dimension_ica", "dimension_tsne"):
            assert a["explained_variance"] is None
        if method == "dimension_tsne":
            with pytest.raises(ProjectError):
                transform(a["model"], [[0.0] * 4])
        if method in SELECTORS:
            assert a["cv"]["stability"] and not a["cv"]["final_test"]["evaluated"]
            with pytest.raises(ProjectError):
                transform(a["model"], [[0.0, 0.0]], inverse=True)
        state = publish(store, store.state, out)
        assert state["results"][-1]["analysis"]["dimension_analysis"] == a
        assert (
            "__vu_source_record_id" in pl.read_parquet(out["paths"]["details"]).columns
        )


@pytest.mark.parametrize(
    "method",
    [
        "dimension_pca",
        "dimension_incremental_pca",
        "dimension_svd",
        "dimension_nmf",
        "dimension_ica",
    ],
)
def test_transform_inverse_numeric_roundtrip_reference(tmp_path, method):
    store, r, w = prepare(tmp_path, fixture(method))
    with closing(store):
        a = calculate(r, recipe(r, method), w, Control())["dimension_analysis"]
        model = json.loads(json.dumps(a["model"]))
        x = fixture(method).select(["x0", "x1", "x2", "x3"]).to_numpy()[:2]
        z = transform(model, x.tolist())["values"]
        back = transform(model, z, inverse=True)["values"]
        assert np.array(back).shape == x.shape and np.isfinite(back).all()
        if method == "dimension_nmf":
            assert np.min(z) >= 0
        if method == "dimension_pca":
            scaling = StandardScaler().fit(
                fixture().select(["x0", "x1", "x2", "x3"]).to_numpy()
            )
            ref = PCA(2).fit(
                scaling.transform(fixture().select(["x0", "x1", "x2", "x3"]).to_numpy())
            )
            assert a["explained_variance"] == pytest.approx(ref.explained_variance_)
            # Orthogonal projector is invariant to component sign.
            c = np.array(model["components"])
            assert c.T @ c == pytest.approx(ref.components_.T @ ref.components_)
            assert np.array(back) == pytest.approx(
                scaling.inverse_transform(
                    ref.inverse_transform(ref.transform(scaling.transform(x)))
                )
            )


def test_nested_fit_ids_means_and_test_label_mutation_do_not_leak(tmp_path):
    store, r, w = prepare(tmp_path, fixture("dimension_univariate"))
    with closing(store):
        s = recipe(r, "dimension_univariate")
        a = calculate(r, s, w, Control())["dimension_analysis"]
        cv = a["cv"]
        source = pl.read_parquet(r["path"])
        byid = {v["__vu_row_id"]: v for v in source.to_dicts()}
        reserved = set(cv["plan"]["membership"]["test"])
        for fold in cv["folds"]:
            assert not set(fold["train"]) & set(
                fold["evaluation"]
            ) and not reserved & set(fold["train"])
            for inner in fold["inner"]:
                assert set(inner["train"]) <= set(fold["train"]) and not set(
                    inner["train"]
                ) & set(inner["evaluation"])
            selected = [i for i, b in enumerate(fold["preprocessing"]["selected"]) if b]
            expected = np.mean(
                [[byid[row][f"x{i}"] for i in selected] for row in fold["train"]],
                axis=0,
            )
            assert fold["preprocessing"]["center"] == pytest.approx(expected)
        altered = source.with_columns(
            pl.when(pl.col("__vu_row_id").is_in(list(reserved)))
            .then(pl.col("target") + 1000000)
            .otherwise(pl.col("target"))
            .alias("target")
        )
        alt = w / "altered.parquet"
        altered.write_parquet(alt)
        from veri_ufku.statistics.dimensions import analyze, load

        req = dict(r, path=str(alt))
        frame, x, y = load(req, s, Control())
        b, _ = analyze(frame, x, y, s, req, Control())
        assert b["model"] == a["model"] and b["cv"] == a["cv"]
        assert not set(b["fit_row_ids"]) & reserved


def test_negative_nmf_centering_sparse_and_missing_guards(tmp_path):
    store, r, w = prepare(tmp_path, fixture())
    with closing(store):
        with pytest.raises(ProjectError, match="non-negative"):
            calculate(r, recipe(r, "dimension_nmf"), w, Control())
        with pytest.raises(ProjectError, match="centering"):
            recipe(r, "dimension_nmf", scaling="standard").validate(r["columns"])
        with pytest.raises(ProjectError, match="CSR"):
            recipe(r, "dimension_pca", storage="csr").validate(r["columns"])
        with pytest.raises(ProjectError):
            recipe(r, "dimension_tsne", purpose="model_input").validate(r["columns"])
    folder = tmp_path / "missing"
    folder.mkdir()
    f = fixture().with_columns(
        pl.when(pl.col("person") % 11 == 0)
        .then(None)
        .otherwise(pl.col("x0"))
        .alias("x0")
    )
    store, r, w = prepare(folder, f)
    with closing(store):
        with pytest.raises(ProjectError, match="Eksik"):
            calculate(r, recipe(r), w, Control())
        a = calculate(
            r, recipe(r, purpose="model_input", missing="mean"), w, Control()
        )["dimension_analysis"]
        assert (
            a["model"]["preprocess"]["impute"]
            and not a["cv"]["final_test"]["evaluated"]
        )


def test_sparse_svd_matches_sparse_backend_no_centering(tmp_path):
    store, r, w = prepare(tmp_path, fixture())
    with closing(store):
        a = calculate(
            r, recipe(r, "dimension_svd", storage="csr", scaling="none"), w, Control()
        )["dimension_analysis"]
        x = fixture().select(["x0", "x1", "x2", "x3"]).to_numpy()
        ref = TruncatedSVD(2, n_iter=7, random_state=42).fit(sparse.csr_matrix(x))
        assert a["explained_variance_ratio"] == pytest.approx(
            ref.explained_variance_ratio_
        )
        assert not a["sparse_layout"]["dense_conversion_allowed"]


@pytest.mark.skipif(
    not importlib.util.find_spec("umap"),
    reason="Optional UMAP backend absent; not tested, no UMAP acceptance claim",
)
def test_optional_umap_only_visual_no_fake_variance(tmp_path):
    store, r, w = prepare(tmp_path, fixture())
    with closing(store):
        a = calculate(r, recipe(r, "dimension_umap"), w, Control())[
            "dimension_analysis"
        ]
        assert a["explained_variance"] is None and not a["model"]["transform_supported"]


@pytest.mark.parametrize(
    "method",
    [
        "dimension_model",
        "dimension_univariate",
        "dimension_rfe",
        "dimension_sequential",
        "dimension_pca",
    ],
)
def test_binary_nested_cv_pipeline_and_stability(tmp_path, method):
    store, r, w = prepare(tmp_path, fixture())
    with closing(store):
        a = calculate(
            r,
            recipe(r, method, purpose="model_input", target_kind="binary"),
            w,
            Control(),
        )["dimension_analysis"]
        assert (
            a["cv"]["score_name"] == "balanced_accuracy"
            and 0 <= a["cv"]["mean_outer_score"] <= 1
        )
        test = set(a["cv"]["plan"]["membership"]["test"])
        assert not test & set(a["fit_row_ids"])
        for outer in a["cv"]["folds"]:
            for record in outer["selection_inner"]:
                assert set(record["train"]) <= set(outer["train"]) and not set(
                    record["train"]
                ) & set(record["evaluation"])
                assert not test & set(record["train"])
            for inner in outer["inner"]:
                for record in inner["selection_inner"]:
                    assert set(record["train"]) <= set(inner["train"])
                    assert not set(record["train"]) & set(record["evaluation"])
        if method != "dimension_pca":
            counts = a["cv"]["stability"]["frequency"]
            assert all(v["selected_folds"] <= v["folds"] for v in counts)
            for pair in a["cv"]["stability"]["pairwise"]:
                f1, f2 = [
                    set(a["cv"]["folds"][i]["selected_features"]) for i in pair["folds"]
                ]
                assert pair["jaccard"] == pytest.approx(len(f1 & f2) / len(f1 | f2))


def test_safe_model_shape_support_and_canceled_source_tamper(tmp_path):
    import threading

    from veri_ufku.jobs.workers import Canceled

    store, r, w = prepare(tmp_path, fixture())
    with closing(store):
        s = recipe(r)
        out = calculate(r, s, w, Control())
        model = out["dimension_analysis"]["model"]
        for field, value in (
            ("components", [[float("nan")] * 4] * 2),
            ("preprocess", {}),
            ("features", [None] * 4),
            ("transform_supported", False),
        ):
            bad = json.loads(json.dumps(model))
            bad[field] = value
            with pytest.raises(ProjectError):
                transform(bad, [[0.0] * 4])
        bad = dict(model, user_code="exec")
        with pytest.raises(ProjectError):
            transform(bad, [[0.0] * 4])
        cancel = threading.Event()
        cancel.set()
        with pytest.raises(Canceled):
            calculate(r, s, w, Control(cancel))
        out["dimension_analysis"]["fit_scope"] = "full-unsafe"
        with pytest.raises(ProjectError):
            publish(store, store.state, out)


def test_nmf_sparse_nonnegative_basis_and_nnls_reference(tmp_path):
    store, r, w = prepare(tmp_path, fixture("dimension_nmf"))
    with closing(store):
        a = calculate(
            r,
            recipe(r, "dimension_nmf", storage="csr", scaling="standard_no_center"),
            w,
            Control(),
        )["dimension_analysis"]
        assert (
            a["explained_variance"] is None and a["reconstruction_error"]["mse"] < 0.01
        )
        with pytest.raises(ProjectError, match="non-negative"):
            transform(a["model"], [[-1.0, 0.0, 0.0, 0.0]])
        z = transform(a["model"], [[0.5] * 4])["values"][0]
        h = np.array(a["model"]["components"])
        scale = np.array(a["model"]["preprocess"]["scale"])
        from scipy.optimize import nnls

        assert z == pytest.approx(nnls(h.T, np.full(4, 0.5) / scale)[0])


def test_variance_empty_scope_is_controlled_and_transform_ids_are_correct(tmp_path):
    store, r, w = prepare(tmp_path, fixture())
    with closing(store):
        with pytest.raises(ProjectError, match="variance"):
            calculate(
                r, recipe(r, "dimension_variance", variance_threshold=1e6), w, Control()
            )
        a = calculate(r, recipe(r, "dimension_univariate"), w, Control())[
            "dimension_analysis"
        ]
        transformed = transform(a["model"], [[0.5] * 4])
        assert transformed["input_feature_order"] == a["model"]["features"]
        assert transformed["output_feature_order"] == a["selected_features"]


def test_sequential_preparation_moments_are_fit_inside_candidate_inner_train(
    tmp_path, monkeypatch
):
    import veri_ufku.statistics.dimensions as implementation
    from veri_ufku.statistics.dimensions import FoldSelector

    x = fixture().select(["x0", "x1", "x2", "x3"]).to_numpy()
    y = fixture()["target"].to_numpy()
    # An extreme evaluation row makes accidental all-data scaling detectable.
    x[0] = [1000, 2000, 3000, 4000]
    audit = []
    original = implementation.preprocessing

    class AuditedScaler(StandardScaler):
        def fit(self, X, y=None, sample_weight=None):
            out = super().fit(X, y, sample_weight=sample_weight)
            audit.append((X.copy(), self.mean_.copy()))
            return out

    from sklearn.pipeline import Pipeline

    monkeypatch.setattr(
        implementation,
        "preprocessing",
        lambda p: Pipeline([("scale", AuditedScaler())]),
    )
    p = dict(
        target_kind="regression",
        inner_folds=2,
        components=2,
        scaling="standard",
        missing="reject",
        variance_threshold=0.0,
    )
    selector = FoldSelector("dimension_sequential", p, 42, Control()).fit(
        x, y, row_ids=[str(i) for i in range(len(x))]
    )
    assert selector.inner_audit_ and len(audit) > 1
    assert all(
        len(train) == len(x) // 2 and mean == pytest.approx(train.mean(axis=0))
        for train, mean in audit
    )
    monkeypatch.setattr(implementation, "preprocessing", original)
