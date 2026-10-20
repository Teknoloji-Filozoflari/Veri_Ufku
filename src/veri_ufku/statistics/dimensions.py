"""Bounded numeric representations, nested CV pipelines and safe array-only transforms."""

import json
import math
import warnings
from pathlib import Path

import numpy as np
import polars as pl
import scipy
import sklearn
from scipy import optimize, sparse
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.decomposition import NMF, PCA, FastICA, IncrementalPCA, TruncatedSVD
from sklearn.feature_selection import (
    RFE,
    SelectFromModel,
    SelectKBest,
    VarianceThreshold,
    f_classif,
    f_regression,
)
from sklearn.impute import SimpleImputer
from sklearn.manifold import TSNE
from sklearn.metrics import balanced_accuracy_score, mean_absolute_error
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import checked, filtered
from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.modeling.classification import estimator as classification_estimator
from veri_ufku.modeling.contracts import identifier
from veri_ufku.modeling.regression import estimator as regression_estimator
from veri_ufku.modeling.validation import ValidationSpec, split_plan
from veri_ufku.statistics.dimension_contracts import DIMENSION_LABELS, SELECTORS, VISUAL
from veri_ufku.storage.project_model import ProjectError, uid

CAUTION = "Latent boyut gerçek sınıf/kişi/temel neden değildir. t-SNE/UMAP lokal komşulukları görselleştirir; global uzaklık, küme sayısı/büyüklüğü ve boşluklar sınıf kanıtı değildir. Test etiketleri grafik/selection için kullanılmaz. Kompresyon full-fit sonucu CV model girdisi diye sunulmaz; selection stabilitesi doğru feature/causality kanıtı değildir."


def load(request, spec, control):
    q, schema, names = filtered(request, ViewSpec())
    p = spec.dimension_plan
    n = q.select(pl.len()).collect(engine="streaming").item()
    limit = (
        1000
        if p["purpose"] == "model_input" or spec.method in SELECTORS
        else 2000
        if spec.method in VISUAL
        else 5000
    )
    if (
        not 12 <= n <= limit
        or n * len(spec.features) * 256 > control.budget.ram_bytes // 2
    ):
        raise ProjectError(
            "Boyut/selection satır veya dense/CSR peak RAM bütçesi aşıldı; sessiz örnekleme yok."
        )
    fields = spec.features + ([spec.y] if spec.y else [])
    semantics = request.get("semantic_metadata", {})
    for c in fields:
        column = next(v for v in request["columns"] if v["id"] == c)
        dt = schema[names[c]]
        if (
            not dt.is_numeric()
            or isinstance(dt, pl.Decimal)
            or c in spec.features
            and (
                identifier(column, semantics)
                or semantics.get(c, {}).get("role")
                in ("category", "ordinal", "ignored")
            )
        ):
            raise ProjectError(
                "Bu şema fiziksel numeric ölçüm ister; kimlik/nominal/ordinal/Decimal ölçüm diye dönüştürülmez."
            )
        if dt.is_integer():
            maximum = (
                q.select(pl.col(names[c]).cast(pl.Float64).abs().max()).collect().item()
            )
            if maximum is not None and maximum > 2**53:
                raise ProjectError("Kayıpsız Float64 integer sınırı aşıldı.")
    internal = [
        c
        for c in (
            "__vu_source_record_id",
            "__vu_source_locator",
            "__vu_expansion_index",
        )
        if c in schema
    ]
    frame = (
        q.select("__vu_row_id", *internal, *[pl.col(names[c]).alias(c) for c in fields])
        .collect(engine="streaming")
        .sort("__vu_row_id")
    )
    if frame.height != n or frame["__vu_row_id"].n_unique() != n:
        raise ProjectError(
            "Snapshot RowId/kapsamı uyuşmuyor; yinelenen kayıt kimliği ret."
        )
    x = frame.select(spec.features).to_numpy().astype(float)
    if np.isinf(x).any() or np.nanmax(np.abs(x)) > 1e12:
        raise ProjectError("Sonsuz/taşan numeric feature reddi.")
    if p["missing"] == "reject" and np.isnan(x).any():
        raise ProjectError(
            "Eksik/NaN feature: reject seçili; açık fold-içi mean planını seçin, sessiz drop yok."
        )
    if np.any(np.all(np.isnan(x), axis=0)):
        raise ProjectError("Tümü eksik feature doldurulamaz.")
    if spec.method == "dimension_nmf" and np.nanmin(x) < 0:
        raise ProjectError(
            "NMF non-negative gereksinimi; negatif değer clip/shift edilmez."
        )
    if spec.method in VISUAL and (p["perplexity"] >= n or p["neighbors"] >= n):
        raise ProjectError("Perplexity/neighbors gözlenen n değerinden küçük olmalı.")
    y = frame[spec.y].to_numpy().astype(float) if spec.y else None
    if y is not None and (
        not np.isfinite(y).all()
        or len(np.unique(y)) < 2
        or p["target_kind"] == "binary"
        and set(y) != {0, 1}
    ):
        raise ProjectError(
            "Target eksiksiz sonlu regression veya explicit0/1 binary olmalı; target impute edilmez."
        )
    control.check()
    return frame, x, y


def prediction_estimator(p, seed):
    return (
        classification_estimator("logistic", {"C": 1}, "prior", seed)
        if p["target_kind"] == "binary"
        else regression_estimator("ridge", {"alpha": 1}, "mean", seed)
    )


def preprocessing(p):
    steps = []
    if p["missing"] == "mean":
        steps.append(("impute", SimpleImputer(strategy="mean")))
    if p["scaling"] != "none":
        steps.append(("scale", StandardScaler(with_mean=p["scaling"] == "standard")))
    return Pipeline(steps) if steps else "passthrough"


def inner_splits(x, y, p, seed):
    count = p["inner_folds"]
    if p["target_kind"] == "binary":
        if min(np.sum(y == a) for a in (0, 1)) < count:
            raise ProjectError("Inner fold sınıf örneklemi yetersiz.")
        return list(StratifiedKFold(count, shuffle=True, random_state=seed).split(x, y))
    return list(KFold(count, shuffle=True, random_state=seed).split(x))


def score(y, pred, p):
    return (
        float(balanced_accuracy_score(y, pred))
        if p["target_kind"] == "binary"
        else -float(mean_absolute_error(y, pred))
    )


class FoldSelector(TransformerMixin, BaseEstimator):
    """Select original numeric columns; sequential candidate preprocessing stays inside inner CV."""

    def __init__(self, method, plan, seed, control):
        self.method = method
        self.plan = plan
        self.seed = seed
        self.control = control

    def fit(self, X, y=None, row_ids=None):
        p = self.plan
        self.fit_row_ids_ = list(row_ids or [])
        self.inner_audit_ = []
        if np.any(np.all(np.isnan(X), axis=0)):
            raise ProjectError("Selection train fold içinde tümü eksik sütun var.")
        k = p["components"]
        if self.method == "dimension_sequential":
            selected = []
            splits = inner_splits(X, y, p, self.seed)
            for train, val in splits:
                self.inner_audit_.append(
                    dict(
                        train=[self.fit_row_ids_[int(i)] for i in train],
                        evaluation=[self.fit_row_ids_[int(i)] for i in val],
                    )
                )
            for _ in range(k):
                candidates = []
                for c in sorted(set(range(X.shape[1])) - set(selected)):
                    self.control.check()
                    cols = selected + [c]
                    values = []
                    for train, val in splits:
                        pipe = Pipeline(
                            [
                                ("prepare", preprocessing(p)),
                                ("baseline", prediction_estimator(p, self.seed)),
                            ]
                        )
                        pipe.fit(X[train][:, cols], y[train])
                        values.append(score(y[val], pipe.predict(X[val][:, cols]), p))
                    candidates.append((float(np.mean(values)), c))
                # Predeclared deterministic index tie-break; no held-out labels.
                selected.append(max(candidates, key=lambda v: (v[0], -v[1]))[1])
            mask = np.zeros(X.shape[1], bool)
            mask[selected] = True
            self.support_ = mask
        else:
            prep = preprocessing(p)
            data = X if prep == "passthrough" else prep.fit_transform(X)
            if self.method == "dimension_variance":
                # Variance is evaluated in original units, after explicit train-only mean imputation; scaling is not used here.
                data = (
                    SimpleImputer(strategy="mean").fit_transform(X)
                    if p["missing"] == "mean"
                    else X
                )
                fitted = VarianceThreshold(p["variance_threshold"]).fit(data)
            elif self.method == "dimension_model":
                fitted = SelectFromModel(
                    prediction_estimator(p, self.seed),
                    threshold=-np.inf,
                    max_features=k,
                ).fit(data, y)
            elif self.method == "dimension_univariate":
                fitted = SelectKBest(
                    f_classif if p["target_kind"] == "binary" else f_regression, k=k
                ).fit(data, y)
            else:
                fitted = RFE(
                    prediction_estimator(p, self.seed), n_features_to_select=k, step=1
                ).fit(data, y)
            self.support_ = fitted.get_support()
        if not self.support_.any():
            raise ProjectError(
                "Selection hiçbir feature bırakmadı; eşik/ölçümleri inceleyin."
            )
        self.n_features_in_ = X.shape[1]
        self.control.check()
        return self

    def transform(self, X):
        return np.asarray(X)[:, self.support_]


class SparseStage(TransformerMixin, BaseEstimator):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return sparse.csr_matrix(X)


def reducer(spec):
    p = spec.dimension_plan
    k = p["components"]
    return {
        "dimension_pca": lambda: PCA(k, svd_solver="full", random_state=spec.seed),
        "dimension_incremental_pca": lambda: IncrementalPCA(
            k, batch_size=max(k, p["batch_size"])
        ),
        "dimension_svd": lambda: TruncatedSVD(k, n_iter=7, random_state=spec.seed),
        "dimension_nmf": lambda: NMF(
            k,
            init="nndsvda",
            max_iter=spec.max_iterations,
            tol=1e-5,
            random_state=spec.seed,
        ),
        "dimension_ica": lambda: FastICA(
            k,
            max_iter=spec.max_iterations,
            tol=1e-4,
            random_state=spec.seed,
            whiten="unit-variance",
        ),
        "dimension_tsne": lambda: TSNE(
            2,
            perplexity=p["perplexity"],
            max_iter=spec.max_iterations,
            random_state=spec.seed,
            init="pca",
            learning_rate="auto",
            n_jobs=1,
        ),
        "dimension_umap": lambda: umap_backend(p, spec.seed, spec.max_iterations),
    }[spec.method]()


def umap_backend(p, seed, iterations):
    try:
        from umap import UMAP
    except ImportError:
        raise ProjectError(
            "Optional UMAP backend yok; kurulu/uygun ortam olmadan UMAP tested sayılmaz."
        ) from None
    return UMAP(
        n_components=2,
        n_neighbors=p["neighbors"],
        n_epochs=iterations,
        min_dist=0.1,
        random_state=seed,
        n_jobs=1,
        transform_seed=seed,
    )


def build_pipeline(spec, control, predictive=False):
    p = spec.dimension_plan
    steps = []
    if spec.method in SELECTORS:
        steps.append(("select", FoldSelector(spec.method, p, spec.seed, control)))
    steps.append(("prepare", preprocessing(p)))
    if p["storage"] == "csr":
        steps.append(("csr", SparseStage()))
    if spec.method not in SELECTORS:
        steps.append(("represent", reducer(spec)))
    if predictive:
        steps.append(("baseline", prediction_estimator(p, spec.seed)))
    return Pipeline(steps)


def fit(pipe, x, y, ids, spec, control):
    if np.any(np.all(np.isnan(x), axis=0)):
        raise ProjectError(
            "Training fold içinde tümü eksik feature: zero fill yapılmaz."
        )
    args = {"select__row_ids": ids} if spec.method in SELECTORS else {}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            pipe.fit(x, y, **args)
        except ProjectError:
            raise
        except (ValueError, FloatingPointError, np.linalg.LinAlgError):
            raise ProjectError(
                "Pipeline fit tanımlanamadı: inner train örneklemi/rank/k, tümü sabit feature veya variance eşiğini inceleyin; sessiz düzeltme yok."
            ) from None
    dangerous = [
        str(w.message)
        for w in caught
        if "converge" in str(w.message).lower()
        or "invalid" in str(w.message).lower()
        or "divide" in str(w.message).lower()
    ]
    if dangerous:
        raise ProjectError(
            "Fit convergence/sayısal tanı başarısız; görünüm/model güvenilir sunulmaz: "
            + dangerous[0][:300]
        )
    control.check()
    return pipe


def preprocessing_state(pipe, x):
    selected = (
        pipe.named_steps["select"].support_
        if "select" in pipe.named_steps
        else np.ones(x.shape[1], bool)
    )
    data = x[:, selected]
    n = data.shape[1]
    means = np.zeros(n)
    scales = np.ones(n)
    impute = None
    prep = pipe.named_steps["prepare"]
    if prep != "passthrough":
        if "impute" in prep.named_steps:
            impute = prep.named_steps["impute"].statistics_.tolist()
        if "scale" in prep.named_steps:
            scale = prep.named_steps["scale"]
            scales = scale.scale_
            if scale.with_mean:
                means = scale.mean_
        data = prep.transform(data)
    return dict(
        selected=selected.tolist(),
        impute=impute,
        center=means.tolist(),
        scale=scales.tolist(),
    ), data


def summarize(pipe, x, spec):
    state, data = preprocessing_state(pipe, x)
    rep = pipe.named_steps.get("represent")
    n = data.shape[1]
    model = dict(
        schema="RepresentationModel/v1",
        method=spec.method,
        features=spec.features,
        preprocess=state,
        components=None,
        mean=None,
        mixing=None,
        transform_supported=spec.method not in VISUAL,
        inverse_supported=spec.method not in VISUAL + SELECTORS,
        fit_scope=spec.dimension_plan["fit_scope"],
        storage=spec.dimension_plan["storage"],
    )
    scores = (
        data
        if rep is None
        else rep.transform(
            sparse.csr_matrix(data) if spec.dimension_plan["storage"] == "csr" else data
        )
        if spec.method not in VISUAL
        else rep.embedding_
    )
    info = dict(
        explained_variance=None,
        explained_variance_ratio=None,
        directions=None,
        loadings=None,
        loading_definition=None,
        reconstruction_error=None,
        iteration=getattr(rep, "n_iter_", None),
        visual_class_labels=False,
    )
    if rep is not None and spec.method not in VISUAL:
        model["components"] = rep.components_.tolist()
        model["mean"] = getattr(rep, "mean_", np.zeros(n)).tolist()
        if spec.method == "dimension_ica":
            model["mixing"] = rep.mixing_.tolist()
        reconstructed = rep.inverse_transform(scores)
        info["reconstruction_error"] = dict(
            frobenius=float(np.linalg.norm(data - reconstructed)),
            mse=float(np.mean((data - reconstructed) ** 2)),
            scope="fit rows; prepared/imputed/scaled feature space; not held-out accuracy or original-unit loss",
        )
        info["directions"] = rep.components_.T.tolist()
        info["loading_definition"] = (
            "Component directions in prepared numeric feature space; signs/order may change, not causal importance."
        )
        if hasattr(rep, "explained_variance_"):
            info["explained_variance"] = rep.explained_variance_.tolist()
            info["explained_variance_ratio"] = rep.explained_variance_ratio_.tolist()
        if spec.method in ("dimension_pca", "dimension_incremental_pca"):
            info["loadings"] = (
                rep.components_.T * np.sqrt(rep.explained_variance_)
            ).tolist()
            info["loading_definition"] = (
                "PCA loading=C.T*sqrt(explained_variance); directions=C.T; raw/scaled units explicit."
            )
        if spec.method == "dimension_svd":
            info["loading_definition"] = (
                "Uncentered SVD directions; explained variance uses projected sample variance, not centered PCA eigenvalue fraction."
            )
        if spec.method == "dimension_nmf":
            info["loading_definition"] = (
                "Non-negative basis H.T, not explained variance or statistical PCA loading."
            )
        if spec.method == "dimension_ica":
            info["loading_definition"] = (
                "ICA unmixing directions; mixing retained for approximate inverse, independent-source assumption not proven."
            )
    if spec.method == "dimension_tsne":
        info["kl_divergence"] = float(rep.kl_divergence_)
    if not np.isfinite(scores).all():
        raise ProjectError("Sonlu olmayan latent representation reddi.")
    return model, info, np.asarray(scores)


def nested_cv(frame, x, y, spec, request, control):
    p = spec.dimension_plan
    binary = p["target_kind"] == "binary"
    ids = frame["__vu_row_id"].to_list()
    v = ValidationSpec(
        method="stratified" if binary else "random", folds=p["folds"], seed=spec.seed
    )
    plan, indices = split_plan(
        ids,
        y,
        None,
        None,
        v,
        v.method,
        binary,
        request["version_id"],
        request["fingerprint"],
    )
    _, _, development, test, folds = indices
    reports = []
    masks = []
    for index, (train, val) in enumerate(folds):
        control.check()
        inner = inner_splits(x[train], y[train], p, spec.seed + index)
        inner_reports = []
        for j, (a, b) in enumerate(inner):
            ia, ib = train[a], train[b]
            pipe = fit(
                build_pipeline(spec, control, True),
                x[ia],
                y[ia],
                [ids[i] for i in ia],
                spec,
                control,
            )
            inner_reports.append(
                dict(
                    train=[ids[i] for i in ia],
                    evaluation=[ids[i] for i in ib],
                    score=score(y[ib], pipe.predict(x[ib]), p),
                    selection_inner=pipe.named_steps["select"].inner_audit_
                    if "select" in pipe.named_steps
                    else [],
                )
            )
        # Fixed predeclared hyperparameters/k: inner scores reported, no post-hoc best-k chosen on outer/test labels.
        pipe = fit(
            build_pipeline(spec, control, True),
            x[train],
            y[train],
            [ids[i] for i in train],
            spec,
            control,
        )
        selected = (
            pipe.named_steps["select"].support_
            if "select" in pipe.named_steps
            else None
        )
        if selected is not None:
            masks.append(selected)
        prep, _ = preprocessing_state(pipe, x[train])
        reports.append(
            dict(
                fold=index,
                train=[ids[i] for i in train],
                evaluation=[ids[i] for i in val],
                inner=inner_reports,
                score=score(y[val], pipe.predict(x[val]), p),
                selected_features=[f for f, m in zip(spec.features, selected) if m]
                if selected is not None
                else None,
                preprocessing=prep,
                selection_inner=pipe.named_steps["select"].inner_audit_
                if "select" in pipe.named_steps
                else [],
            )
        )
    stability = None
    if masks:
        sets = [set(np.flatnonzero(mask)) for mask in masks]
        pairs = []
        for a in range(len(sets)):
            for b in range(a):
                pairs.append(
                    dict(
                        folds=[b, a],
                        jaccard=len(sets[a] & sets[b]) / len(sets[a] | sets[b]),
                    )
                )
        stability = dict(
            frequency=[
                dict(
                    column_id=f,
                    selected_folds=int(sum(m[i] for m in masks)),
                    folds=len(masks),
                )
                for i, f in enumerate(spec.features)
            ],
            pairwise=pairs,
            interpretation="Original-column support stability across outer training fits; overlap of training folds and correlated features affect it; not causal truth or guarantee.",
        )
    return (
        dict(
            plan=plan,
            folds=reports,
            stability=stability,
            score_name="balanced_accuracy" if binary else "negative_MAE",
            mean_outer_score=float(np.mean([r["score"] for r in reports])),
            final_test=dict(
                evaluated=False,
                reason="Reserved test never fitted/scored/plotted; no final model benchmarking or label-based 2D choice.",
            ),
            policy="Nested pipeline per inner train; fixed-k/parameters predeclared; final representation refit on development only; iid numeric scope",
        ),
        development,
        test,
    )


def transform(model, rows, inverse=False):
    if (
        not isinstance(model, dict)
        or set(model)
        != {
            "schema",
            "method",
            "features",
            "preprocess",
            "components",
            "mean",
            "mixing",
            "transform_supported",
            "inverse_supported",
            "fit_scope",
            "storage",
        }
        or model["schema"] != "RepresentationModel/v1"
    ):
        raise ProjectError(
            "Safe representation model şeması geçersiz; user code/import yok."
        )
    from veri_ufku.statistics.dimension_contracts import DIMENSION_METHODS

    if (
        model["method"] not in DIMENSION_METHODS
        or not isinstance(model["features"], list)
        or not 2 <= len(model["features"]) <= 20
        or any(not isinstance(f, str) for f in model["features"])
        or len(set(model["features"])) != len(model["features"])
    ):
        raise ProjectError("Safe model method/features şeması geçersiz.")
    if (
        model["transform_supported"] != (model["method"] not in VISUAL)
        or model["inverse_supported"] != (model["method"] not in VISUAL + SELECTORS)
        or model["fit_scope"] not in ("full", "development")
        or model["storage"] not in ("dense", "csr")
    ):
        raise ProjectError(
            "Safe transform/inverse support flagları yöntemle uyuşmuyor."
        )
    pre = model["preprocess"]
    if (
        not isinstance(pre, dict)
        or set(pre) != {"selected", "impute", "center", "scale"}
        or not isinstance(pre["selected"], list)
        or len(pre["selected"]) != len(model["features"])
        or any(type(v) is not bool for v in pre["selected"])
    ):
        raise ProjectError("Safe preprocessing selection şeması geçersiz.")
    count = sum(pre["selected"])

    def numeric_vector(v, n):
        return (
            isinstance(v, list)
            and len(v) == n
            and all(
                type(x) in (int, float) and math.isfinite(x) and abs(x) <= 1e12
                for x in v
            )
        )

    if (
        not count
        or not numeric_vector(pre["center"], count)
        or not numeric_vector(pre["scale"], count)
        or any(v <= 0 for v in pre["scale"])
        or pre["impute"] is not None
        and not numeric_vector(pre["impute"], count)
    ):
        raise ProjectError("Safe preprocessing array/scale şeması geçersiz.")
    if model["method"] in SELECTORS + VISUAL:
        if any(model[k] is not None for k in ("components", "mean", "mixing")):
            raise ProjectError("Bu modelde sahte components/inverse bilgisi olamaz.")
    else:
        c = model["components"]
        if (
            not isinstance(c, list)
            or not 2 <= len(c) <= count
            or any(not numeric_vector(row, count) for row in c)
            or not numeric_vector(model["mean"], count)
        ):
            raise ProjectError("Safe reducer component boyutu/array şeması geçersiz.")
        if model["method"] == "dimension_nmf" and any(v < 0 for row in c for v in row):
            raise ProjectError("NMF non-negative basis bozulmuş.")
        if model["method"] == "dimension_ica":
            if (
                not isinstance(model["mixing"], list)
                or len(model["mixing"]) != count
                or any(not numeric_vector(row, len(c)) for row in model["mixing"])
            ):
                raise ProjectError("Safe ICA mixing şeması geçersiz.")
        elif model["mixing"] is not None:
            raise ProjectError("Mixing yalnız ICA için geçerli.")
    if (
        inverse
        and not model["inverse_supported"]
        or not inverse
        and not model["transform_supported"]
    ):
        raise ProjectError(
            "Bu adapter inverse/new-data transform desteklemiyor; t-SNE/UMAP embedding mevcut fit satırları için."
        )
    if (
        not isinstance(rows, list)
        or not 1 <= len(rows) <= 50
        or any(not isinstance(r, list) for r in rows)
    ):
        raise ProjectError("1–50row numeric JSON matrix gerekli.")
    try:
        values = np.array(rows, dtype=float)
    except (ValueError, TypeError):
        raise ProjectError("Numeric profile/matrix geçersiz.") from None
    if (
        values.ndim != 2
        or not np.isfinite(values).all()
        or np.max(np.abs(values)) > 1e12
    ):
        raise ProjectError(
            "Sonlu bounded profile matrix gerekli; eksik new-data profile bu ilkadapterda ret."
        )
    p = model["preprocess"]
    support = np.array(p["selected"], bool)
    center = np.array(p["center"])
    scale = np.array(p["scale"])
    components = (
        np.array(model["components"]) if model["components"] is not None else None
    )
    if not inverse:
        if values.shape[1] != len(model["features"]):
            raise ProjectError("Feature order/profile boyutu uyuşmuyor.")
        data = (values[:, support] - center) / scale
        if components is None:
            out = data
        elif model["method"] == "dimension_nmf":
            if np.any(data < 0):
                raise ProjectError(
                    "NMF new-data non-negative gereksinimi; clip/shift yok."
                )
            out = np.array(
                [optimize.nnls(components.T, row, maxiter=1000)[0] for row in data]
            )
        else:
            out = (data - np.array(model["mean"])) @ components.T
    else:
        if components is None or values.shape[1] != components.shape[0]:
            raise ProjectError(
                "Inverse latent boyut uyuşmuyor; selected columns için inverse yok."
            )
        out = (
            values @ np.array(model["mixing"]).T + np.array(model["mean"])
            if model["method"] == "dimension_ica"
            else values @ components + np.array(model["mean"])
        )
        out = out * scale + center
    if not np.isfinite(out).all():
        raise ProjectError("Transform nonfinite output reddi.")
    return dict(
        values=out.tolist(),
        feature_order=model["features"],
        input_feature_order=[
            "representation_" + str(i + 1) for i in range(values.shape[1])
        ]
        if inverse
        else model["features"],
        output_feature_order=model["features"]
        if inverse
        else [f for f, m in zip(model["features"], support) if m]
        if model["method"] in SELECTORS
        else ["representation_" + str(i + 1) for i in range(out.shape[1])],
        method=model["method"],
        inverse=inverse,
        interpretation="Approximate reconstruction, not exact lost information"
        if inverse
        else "Fitted representation transform; coordinates are not real class labels",
        nmf_solver="Safe NNLS with fixed non-negative basis, not exact bit-identical sklearn CD transform"
        if model["method"] == "dimension_nmf"
        else None,
    )


def _analyze(frame, x, y, spec, request, control):
    p = spec.dimension_plan
    cv = None
    test = []
    if p["purpose"] == "model_input":
        cv, chosen, test = nested_cv(frame, x, y, spec, request, control)
    else:
        chosen = np.arange(len(x))
    fitx = x[chosen]
    ids = frame["__vu_row_id"].to_list()
    fitids = [ids[i] for i in chosen]
    if p["components"] > min(fitx.shape) and spec.method not in SELECTORS:
        raise ProjectError(
            "Train fit scope için n_components rank/dimension sınırı aşıldı."
        )
    pipe = fit(
        build_pipeline(spec, control),
        fitx,
        None if y is None else y[chosen],
        fitids,
        spec,
        control,
    )
    model, info, coordinates = summarize(pipe, fitx, spec)
    info["fit_row_ids"] = fitids
    info["cv"] = cv
    info["model"] = model
    info["purpose"] = p["purpose"]
    info["fit_scope"] = p["fit_scope"]
    info["sparse_layout"] = dict(
        requested=p["storage"],
        source_is_dense_parquet=True,
        source_dense_bytes=x.nbytes,
        prepared_nonzero=int(np.count_nonzero(preprocessing_state(pipe, fitx)[1])),
        dense_conversion_allowed=False if p["storage"] == "csr" else True,
        explanation="Explicit bounded table→CSR; sparse algorithms avoid centering; source is not native sparse input, source dense read budget included.",
    )
    info["warnings"] = [CAUTION]
    info["selected_features"] = [
        f for f, m in zip(spec.features, model["preprocess"]["selected"]) if m
    ]
    info["profile_preview"] = None
    if model["transform_supported"]:
        info["profile_preview"] = transform(model, [p["profile"]])
    info["native_umap_transform"] = (
        "UMAP backend can transform, but this application safe numeric adapter is not validated for it; new-data/inverse disabled."
        if spec.method == "dimension_umap"
        else None
    )
    ordered = frame[chosen.tolist()].drop(spec.y) if spec.y else frame[chosen.tolist()]
    for j in range(coordinates.shape[1]):
        ordered = ordered.with_columns(
            pl.Series("representation_" + str(j + 1), coordinates[:, j])
        )
    info["display"] = dict(
        columns=["representation_" + str(i + 1) for i in range(coordinates.shape[1])],
        first_two_only=coordinates.shape[1] > 2,
        class_labels=False,
        heldout_rows_shown=False,
        seed=spec.seed,
    )
    control.check()
    return info, ordered


def analyze(frame, x, y, spec, request, control):
    # Parent revalidation and spawned worker must use the same BLAS/OpenMP
    # reduction order; publication stays exact, not a permissive allclose check.
    with threadpool_limits(limits=control.budget.cpu_threads):
        return _analyze(frame, x, y, spec, request, control)


def plot(payload, details, spec, path):
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 6), layout="constrained")
    if spec.method in SELECTORS:
        if payload["cv"] and payload["cv"]["stability"]:
            freq = payload["cv"]["stability"]["frequency"]
            ax.bar(range(len(freq)), [v["selected_folds"] / v["folds"] for v in freq])
            ax.set(
                ylim=(0, 1.05),
                ylabel="Outer-fold selection frequency",
                xlabel="Original feature index (order in companion JSON)",
            )
        else:
            mask = payload["model"]["preprocess"]["selected"]
            ax.set_xticks(range(len(mask)))
            ax.bar(range(len(mask)), list(map(int, mask)))
            ax.set(
                ylim=(0, 1.05),
                ylabel="Selected original feature",
                xlabel="Original feature index",
            )
    else:
        ax.scatter(
            details["representation_1"],
            details["representation_2"],
            s=12,
            alpha=0.65,
            color="#4F6FC7",
        )
        ax.set(xlabel="Representation1", ylabel="Representation2")
    ax.set_title(
        spec.method
        + " · "
        + payload["purpose"]
        + " · fit n="
        + str(details.height)
        + " · seed="
        + str(spec.seed)
    )
    ax.text(
        0,
        -0.2,
        "Coordinates/selected features are not real classes or causes.\nNo test labels/rows shown. First2 dimensions only if k>2; method/settings in companion JSON.",
        transform=ax.transAxes,
        fontsize=9,
    )
    fig.savefig(path, dpi=150)
    plt.close(fig)


def calculate(request, spec, workspace, control, preflight=False):
    spec.validate(request["columns"], run=not preflight)
    checked(request, control)
    frame, x, y = load(request, spec, control)
    p = spec.dimension_plan
    maxfits = p["folds"] * (p["inner_folds"] + 1) + 1
    if spec.method == "dimension_rfe":
        maxfits *= len(spec.features) - p["components"] + 2
    elif spec.method in SELECTORS:
        maxfits *= 2
    if spec.method == "dimension_sequential":
        maxfits *= len(spec.features) * p["components"] * p["inner_folds"]
    if maxfits > 3000:
        raise ProjectError(
            "Nested sequential selection fit maliyeti3000üstünde; feature/k/fold azaltın."
        )
    payload, details = analyze(frame, x, y, spec, request, control)
    common = dict(
        source_columns=request["columns"],
        dimensions=True,
        method=spec.method,
        method_label=DIMENSION_LABELS[spec.method],
        plan=p,
        dimension_analysis=payload,
        n=dict(population=frame.height, fit=details.height),
        used_rows=details.height,
        excluded_rows=dict(
            reserved_test_not_fitted_or_displayed=frame.height - details.height
        ),
        warnings=payload["warnings"],
        budget=dict(
            rows=frame.height,
            predictors=len(spec.features),
            source_dense_bytes=x.nbytes,
            estimated_peak_bytes=x.nbytes * 32,
            upper_fit_estimate=maxfits,
            ram_limit=control.budget.ram_bytes,
        ),
    )
    if preflight:
        return dict(
            common,
            spec=spec.data(),
            dataset_version=request["version_id"],
            config_revision=request.get("config_revision", 0),
        )
    result = dict(
        common,
        primary=dict(method=spec.method, p_value=None, statistic=None, effect=None),
        spec=spec.data(),
        comparisons=[],
        correction=dict(
            method="none",
            family="predeclared representation/selection question; no significance test",
            family_size=1,
            ci_adjusted=False,
        ),
        dataset_version=request["version_id"],
        config_revision=request.get("config_revision", 0),
        result_version="analysis:" + uid(),
        method_version=1,
        parameter_version=1,
        provenance=dict(
            schema="AnalysisResult/v1",
            backend="sklearn numeric pipelines; safe numeric transform adapters",
            sklearn_version=sklearn.__version__,
            numpy_version=np.__version__,
            scipy_version=scipy.__version__,
            snapshot_fingerprint=request["fingerprint"],
            snapshot_uri=request["snapshot_uri"],
            source_snapshot_id=request["source_snapshot_id"],
            semantic_metadata=request.get("semantic_metadata", {}),
            help_content_version=62,
            seed=spec.seed,
        ),
    )
    checked(request, control)
    directory = Path(workspace)
    paths = dict(
        result=str(directory / "dimension-result.json"),
        members=str(directory / "dimension-members.parquet"),
        details=str(directory / "dimension-details.parquet"),
        diagnostic_png=str(directory / "dimension.png"),
    )
    details.select(pl.col("__vu_row_id").alias("row_id")).write_parquet(
        paths["members"]
    )
    details.rename({"__vu_row_id": "row_id"}).write_parquet(paths["details"])
    plot(payload, details, spec, paths["diagnostic_png"])
    control.check()
    Path(paths["result"]).write_text(
        json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )
    result["paths"] = paths
    result["fingerprints"] = {
        k: hash_artifact(Path(v), control) for k, v in paths.items()
    }
    control.disk(directory)
    control.check()
    return result


def verify_source(path, columns, result, details, members, semantics):
    from veri_ufku.statistics.contracts import AnalysisSpec

    spec = AnalysisSpec.from_dict(result["spec"])
    spec.validate(columns, run=True)
    control = Control()
    if columns != result["source_columns"]:
        raise ProjectError(
            "Representation exported ColumnId/name/schema bağı değişmiş."
        )
    if semantics != result["provenance"]["semantic_metadata"]:
        raise ProjectError("Dimension semantic/source ColumnId metadata bağı değişmiş.")
    request = dict(
        path=str(path),
        columns=columns,
        semantic_metadata=semantics,
        version_id=result["dataset_version"],
        fingerprint=result["provenance"]["snapshot_fingerprint"],
    )
    frame, x, y = load(request, spec, control)
    payload, expected = analyze(frame, x, y, spec, request, control)
    if not expected.rename({"__vu_row_id": "row_id"}).equals(
        details
    ) or not expected.select(pl.col("__vu_row_id").alias("row_id")).equals(members):
        raise ProjectError(
            "Representation source/RowId/fit-scope/coordinates artifact uyuşmuyor."
        )
    if payload != result["dimension_analysis"]:
        raise ProjectError("Dimension fit/CV/model/source hesabı değişmiş.")
