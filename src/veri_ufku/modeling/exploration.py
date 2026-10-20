"""Bounded, shared Phase47 clustering and anomaly computations; no inferred truth."""

import warnings
from dataclasses import replace

import numpy as np
from sklearn.cluster import DBSCAN, OPTICS, AgglomerativeClustering, KMeans
from sklearn.covariance import EllipticEnvelope
from sklearn.metrics import (
    adjusted_rand_score,
    average_precision_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    precision_recall_curve,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

from veri_ufku.modeling.unsupervised_contracts import CLUSTER_METHODS
from veri_ufku.storage.project_model import ProjectError


def preflight(spec, n, budget):
    quadratic = (
        (spec.method in CLUSTER_METHODS and (spec.method != "kmeans" or n <= 3000))
        or bool(spec.compare_methods)
        or spec.method in ("lof", "one_class_svm")
    )
    estimate = n * n * 24 if quadratic else n * len(spec.features) * 64
    bounded = (
        spec.compare_methods
        or spec.stability_runs
        or spec.method not in ("kmeans", "iqr", "isolation_forest")
    )
    if bounded and n > 3000 or estimate > budget.ram_bytes // 2:
        raise ProjectError(
            f"n² distance önkontrolü: {n} kayıt, en kötü {estimate} byte; RAM/3000 kayıt sınırı. Sessiz örnekleme yok."
        )
    return dict(
        rows=n,
        features=len(spec.features),
        worst_case_bytes=estimate,
        quadratic=quadratic,
        stability_fits=spec.stability_runs
        * len(set((spec.method,) + spec.compare_methods)),
        policy="no implicit sampling; full-version exploratory fit",
    )


def fit_cluster(x, spec, control):
    control.check()
    m = spec.method
    if m in ("kmeans", "gmm", "agglomerative") and (
        spec.clusters > len(x) or spec.clusters > len(np.unique(x, axis=0))
    ):
        raise ProjectError("Küme sayısı kayıt/farklı vektör sayısını aşamaz.")
    if m == "kmeans":
        model = KMeans(
            n_clusters=spec.clusters,
            random_state=spec.seed,
            n_init=10,
            max_iter=300,
            algorithm="lloyd",
        )
    elif m == "dbscan":
        model = DBSCAN(
            eps=spec.eps,
            min_samples=spec.min_samples,
            metric=spec.metric,
            algorithm="brute",
            n_jobs=1,
        )
    elif m == "agglomerative":
        model = AgglomerativeClustering(
            n_clusters=spec.clusters,
            metric=spec.metric,
            linkage=spec.linkage,
            compute_distances=True,
            compute_full_tree=True,
        )
    elif m == "gmm":
        model = GaussianMixture(
            n_components=spec.clusters,
            covariance_type=spec.covariance_type,
            random_state=spec.seed,
            n_init=3,
            reg_covar=1e-6,
            max_iter=300,
        )
    elif m == "optics":
        if spec.min_samples > len(x):
            raise ProjectError("OPTICS min_samples kayıt sayısını aşamaz.")
        model = OPTICS(
            min_samples=spec.min_samples,
            metric=spec.metric,
            xi=spec.xi,
            cluster_method="xi",
            n_jobs=1,
        )
    elif m == "hdbscan":
        try:
            from sklearn.cluster import HDBSCAN
        except ImportError as error:
            raise ProjectError(
                "Optional sklearn HDBSCAN backend ortamı yok; test edilmiş sayılmaz."
            ) from error
        if max(spec.min_cluster_size, spec.min_samples) > len(x):
            raise ProjectError(
                "HDBSCAN minimum küme/komşu sayısı kayıt sayısını aşamaz."
            )
        model = HDBSCAN(
            min_cluster_size=spec.min_cluster_size,
            min_samples=spec.min_samples,
            metric=spec.metric,
            n_jobs=1,
            copy=True,
        )
    else:
        raise ProjectError("Küme yöntemi desteklenmiyor.")
    labels = model.fit_predict(x)
    control.check()
    state = dict(
        metric=spec.metric,
        linkage=spec.linkage if m == "agglomerative" else None,
        scaling=spec.scaling,
    )
    if m == "kmeans":
        state.update(
            centers=model.cluster_centers_.tolist(),
            inertia=float(model.inertia_),
            n_init=10,
            max_iter=300,
        )
    if m == "dbscan":
        state["core_count"] = len(model.core_sample_indices_)
    if m == "gmm":
        if not model.converged_:
            raise ProjectError(
                "GMM convergence başarısız; güvenilir sonuç yayınlanmadı."
            )
        state.update(
            aic=float(model.aic(x)),
            bic=float(model.bic(x)),
            covariance_type=spec.covariance_type,
            soft_membership=model.predict_proba(x).tolist(),
            converged=True,
            criterion_scope="same rows, representation and likelihood; lower AIC/BIC, not true k",
        )
    if m == "agglomerative":
        counts = np.zeros(len(model.children_))
        for i, pair in enumerate(model.children_):
            counts[i] = sum(
                1 if child < len(x) else counts[child - len(x)] for child in pair
            )
        state["dendrogram_linkage"] = np.column_stack(
            [model.children_, model.distances_, counts]
        ).tolist()
        from scipy.cluster.hierarchy import dendrogram

        tree = dendrogram(
            np.asarray(state["dendrogram_linkage"]),
            no_plot=True,
            truncate_mode="lastp",
            p=30,
        )
        max_height = max(model.distances_.max(), 1e-12)
        leaf_count = len(tree["leaves"])
        lines = []
        for horizontal, vertical in zip(tree["icoord"], tree["dcoord"]):
            points = " ".join(
                f"{35 + a / (10 * leaf_count) * 830:.4f},{300 - b / max_height * 250:.4f}"
                for a, b in zip(horizontal, vertical)
            )
            lines.append(
                f'<polyline points="{points}" fill="none" stroke="#3d65aa" stroke-width="1.5"/>'
            )
        state["dendrogram_svg"] = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="350" viewBox="0 0 900 350"><rect width="900" height="350" fill="white"/><text x="30" y="25" fill="black">Dendrogram: selected metric/linkage; last 30 nodes (collapsed leaves)</text>'
            + "".join(lines)
            + "</svg>"
        )

    if m == "optics":
        state.update(
            ordering=model.ordering_.tolist(),
            reachability=[
                float(v) if np.isfinite(v) else None for v in model.reachability_
            ],
            xi=spec.xi,
        )
    if m == "hdbscan":
        state.update(
            membership_strength=model.probabilities_.tolist(),
            backend="sklearn HDBSCAN; min_samples includes self; no contrib equivalence claim",
        )
    return model, labels, state


def metrics(x, labels, metric, control):
    mask = labels >= 0
    used = int(mask.sum())
    groups = np.unique(labels[mask])
    report = dict(
        used_rows=used,
        noise_excluded=int((~mask).sum()),
        metric=metric,
        scope="non_noise",
        silhouette=None,
        davies_bouldin=None,
        calinski_harabasz=None,
        reason="Internal geometry; no universal true cluster count or labeled accuracy.",
    )
    if not 2 <= len(groups) < used or used > 3000:
        report["reason"] = (
            "Undefined: requires 2..n-1 non-noise clusters and <=3000 rows."
        )
        return report
    control.check()
    report["silhouette"] = float(silhouette_score(x[mask], labels[mask], metric=metric))
    if metric == "euclidean":
        report["davies_bouldin"] = float(davies_bouldin_score(x[mask], labels[mask]))
        report["calinski_harabasz"] = float(
            calinski_harabasz_score(x[mask], labels[mask])
        )
    else:
        report["centroid_metrics_reason"] = (
            "DB/CH Euclidean centroid geometry; not reported for Manhattan comparison."
        )
    return report


def comparison(raw, x, labels, state, spec, control, row_ids=None):
    reports = []
    for method in dict.fromkeys((spec.method,) + spec.compare_methods):
        control.check()
        candidate = replace(spec, method=method, compare_methods=())
        if method == spec.method:
            base, fitted = labels, state
        else:
            _, base, fitted = fit_cluster(x, candidate, control)
        stability = []
        rng = np.random.default_rng(spec.seed)
        for run in range(spec.stability_runs):
            control.check()
            indices = np.sort(
                rng.choice(len(raw), max(2, int(0.8 * len(raw))), replace=False)
            )
            sub = raw[indices]
            sub = (
                StandardScaler().fit_transform(sub)
                if spec.scaling == "standard"
                else sub
            )
            try:
                _, other, _ = fit_cluster(
                    sub, replace(candidate, seed=(spec.seed + run + 1) % 2**32), control
                )
            except ProjectError as error:
                stability.append(
                    dict(
                        status="unavailable",
                        reason=str(error),
                        selected_indices=indices.tolist(),
                    )
                )
                continue
            mask = (base[indices] >= 0) & (other >= 0)
            valid = (
                mask.sum() > 1
                and len(np.unique(base[indices][mask])) > 1
                and len(np.unique(other[mask])) > 1
            )
            stability.append(
                dict(
                    status="valid" if valid else "unavailable",
                    adjusted_rand=float(
                        adjusted_rand_score(base[indices][mask], other[mask])
                    )
                    if valid
                    else None,
                    non_noise_overlap=int(mask.sum()),
                    noise_agreement=float(np.mean((base[indices] < 0) == (other < 0))),
                    selected_indices=indices.tolist(),
                )
            )
        if row_ids is not None:
            for resample in stability:
                resample["selected_row_ids"] = [
                    row_ids[i] for i in resample["selected_indices"]
                ]
        reports.append(
            dict(
                method=method,
                metrics=metrics(x, base, spec.metric, control),
                noise_count=int((base < 0).sum()),
                cluster_count=len(np.unique(base[base >= 0])),
                assignments=base.tolist(),
                aic=fitted.get("aic"),
                bic=fitted.get("bic"),
                stability=stability,
                stability_policy="80% subsample without replacement; scaler refit in each sample; ARI only shared non-noise rows; no truth claim",
            )
        )
    return reports


def anomaly(x, spec, control):
    n = len(x)
    train = np.arange(n)
    if spec.anomaly_mode == "novelty":
        train = np.sort(
            np.random.default_rng(spec.seed).choice(
                n, int(n * spec.training_fraction), replace=False
            )
        )
    test = (
        np.setdiff1d(np.arange(n), train) if spec.anomaly_mode == "novelty" else train
    )
    if len(train) <= spec.min_samples:
        raise ProjectError(
            "LOF/novelty eğitim kapsamı min_samples sayısından büyük olmalı."
        )
    if spec.method == "lof":
        model = LocalOutlierFactor(
            n_neighbors=spec.min_samples,
            metric=spec.metric,
            contamination=spec.contamination,
            novelty=spec.anomaly_mode == "novelty",
            n_jobs=1,
        )
    elif spec.method == "one_class_svm":
        model = OneClassSVM(nu=spec.nu, gamma=spec.gamma, kernel="rbf", max_iter=10000)
    else:
        if (
            len(train) <= 2 * x.shape[1]
            or np.linalg.matrix_rank(x[train] - x[train].mean(axis=0)) < x.shape[1]
        ):
            raise ProjectError(
                "Robust covariance yeterli kayıt ve full-rank Gaussian/elliptical temsil gerektirir."
            )
        model = EllipticEnvelope(
            contamination=spec.contamination, random_state=spec.seed
        )
    control.check()
    with warnings.catch_warnings(record=True) as caught:
        if spec.method == "lof" and spec.anomaly_mode == "outlier":
            model.fit_predict(x[train])
            scored = -model.negative_outlier_factor_
        else:
            model.fit(x[train])
            scored = -model.score_samples(x[test])
    if getattr(model, "fit_status_", 0) != 0 or caught:
        raise ProjectError(
            "Anomali backend tanılama uyarısı/convergence; sonuç yayınlanmadı."
        )
    control.check()
    threshold = float(-np.asarray(model.offset_).reshape(-1)[0])
    scores = np.full(n, np.nan)
    scores[test] = scored
    flags = scores > threshold
    return (
        scores,
        flags,
        threshold,
        dict(
            training_indices=train.tolist(),
            scored_indices=test.tolist(),
            mode=spec.anomaly_mode,
            score_geometry=spec.metric
            if spec.method == "lof"
            else "rbf squared Euclidean"
            if spec.method == "one_class_svm"
            else "robust Mahalanobis squared",
            threshold_rule="score > threshold; training rows unscored in novelty",
            score_origin="negative_outlier_factor_"
            if spec.method == "lof" and spec.anomaly_mode == "outlier"
            else "negative score_samples",
            contamination=spec.contamination
            if spec.method != "one_class_svm"
            else None,
            nu=spec.nu if spec.method == "one_class_svm" else None,
            gamma=spec.gamma if spec.method == "one_class_svm" else None,
            no_reuse="Safe new-file model persistence not implemented for Phase47 methods; disjoint heldout novelty only",
        ),
    )


def evaluation(truth, scores, flags, spec):
    mask = np.isfinite(scores)
    y, score, predicted = truth[mask], scores[mask], flags[mask]
    if set(np.unique(y)) != {0, 1}:
        raise ProjectError("Skorlanan kapsamda anomali etiketi hem 0 hem 1 içermeli.")
    tp = int(np.sum((y == 1) & predicted))
    fp = int(np.sum((y == 0) & predicted))
    fn = int(np.sum((y == 1) & ~predicted))
    precision, recall, thresholds = precision_recall_curve(y, score)
    return dict(
        labels_available=True,
        precision=tp / (tp + fp) if tp + fp else None,
        recall=tp / (tp + fn),
        average_precision=float(average_precision_score(y, score)),
        pr_curve=dict(
            precision=precision.tolist(),
            recall=recall.tolist(),
            thresholds=thresholds.tolist(),
        ),
        false_positive=fp,
        false_negative=fn,
        total_cost=fp * spec.false_positive_cost + fn * spec.false_negative_cost,
        cost_units="user cost per error",
        evaluated_rows=len(y),
        scope="heldout novelty"
        if spec.anomaly_mode == "novelty"
        else "apparent in-sample outlier; not generalization",
        reason="Labels supplied by user; threshold fixed before evaluation; no automatic optimization.",
    )


def verify_source(value, members, source, dataset):
    """Recompute Phase47 numeric outputs before atomic publication and on saved reopen."""
    from threadpoolctl import threadpool_limits

    from veri_ufku.domain.contracts import ComputeBudget
    from veri_ufku.importers.delimited import Control
    from veri_ufku.modeling.unsupervised import numeric_matrix
    from veri_ufku.modeling.unsupervised_contracts import UnsupervisedSpec

    spec = UnsupervisedSpec.from_dict(value["spec"])
    if "compute_preflight" not in value:
        return  # legacy Phase19 records keep their original validation
    columns = dataset["import_metadata"]["columns"]
    _, raw = numeric_matrix(
        source, columns, spec.features, dataset.get("semantic_metadata", {})
    )
    row_ids = source["__vu_row_id"].to_list()
    if value["row_ids"] != row_ids:
        raise ProjectError("Phase47 RowId ilişkisi değişmiş.")
    train = np.arange(len(raw))
    if spec.anomaly_mode == "novelty":
        train = np.sort(
            np.random.default_rng(spec.seed).choice(
                len(raw), int(len(raw) * spec.training_fraction), replace=False
            )
        )
    if value["fit_row_ids"] != source["__vu_row_id"].gather(train).to_list():
        raise ProjectError("Phase47 eğitim RowId kapsamı değişmiş.")
    control = Control(budget=replace(ComputeBudget(), cpu_threads=value["cpu_threads"]))
    with threadpool_limits(limits=control.budget.cpu_threads):
        scaler = (
            StandardScaler().fit(raw[train])
            if spec.scaling == "standard" and spec.method != "iqr"
            else None
        )
        x = scaler.transform(raw) if scaler else raw.copy()
        expected_scaling = (
            dict(mean=scaler.mean_.tolist(), scale=scaler.scale_.tolist())
            if scaler
            else None
        )
        if value["scaling_state"] != expected_scaling:
            raise ProjectError("Phase47 scaler eğitim kapsamı değişmiş.")
        if spec.method in CLUSTER_METHODS:
            _, labels, state = fit_cluster(x, spec, control)
            state["comparison"] = comparison(
                raw, x, labels, state, spec, control, row_ids
            )
            if (
                labels.tolist() != members["cluster"].to_list()
                or state != value["method_state"]
            ):
                raise ProjectError(
                    "Phase47 küme/metric/stabilite/soft membership kaynağa uymuyor."
                )
        elif spec.method in ("lof", "one_class_svm", "robust_covariance"):
            scores, flags, threshold, state = anomaly(x, spec, control)
            if (
                [float(v) if np.isfinite(v) else None for v in scores]
                != members["anomaly_score"].to_list()
                or threshold != value["threshold"]
                or state != value["method_state"]
            ):
                raise ProjectError("Phase47 anomaly/novelty skor kaynağa uymuyor.")
            if spec.label_column:
                name = next(c["name"] for c in columns if c["id"] == spec.label_column)
                if (
                    evaluation(source[name].to_numpy(), scores, flags, spec)
                    != value["evaluation"]
                ):
                    raise ProjectError("Phase47 etiketli PR/maliyet kaynağa uymuyor.")
