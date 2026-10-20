"""Bounded full-version exploratory clustering and anomaly candidates; no row deletion."""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import polars as pl
import sklearn
from sklearn.ensemble import IsolationForest
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from veri_ufku.analytics.dataset import checked
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.contracts import identifier
from veri_ufku.modeling.exploration import (
    anomaly,
    comparison,
    evaluation,
    fit_cluster,
    preflight,
)
from veri_ufku.modeling.unsupervised_contracts import (
    CLUSTER_METHODS,
    LIMITS,
    UnsupervisedSpec,
)
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.project_store import file_hash


def silhouette(x, labels, control=None, metric="euclidean"):
    """Noise excluded explicitly; tiny clusters and bounded-cost omissions are undefined."""
    mask = labels >= 0
    groups, counts = np.unique(labels[mask], return_counts=True)
    report = dict(
        status="unavailable",
        value=None,
        used_rows=int(mask.sum()),
        noise_excluded=int((~mask).sum()),
        scope="all_non_noise",
        metric=metric + "_scaled_features",
    )
    if len(groups) < 2:
        report["reason"] = (
            "Gürültü dışında en az iki küme gerekli; tek küme veya tüm gürültü."
        )
    elif len(groups) >= mask.sum() or counts.min() < 3:
        report["reason"] = (
            "Çok küçük küme: her kümede en az 3 kayıt gerekli (ürün politikası)."
        )
    elif mask.sum() > 3000:
        report["reason"] = (
            "Tam silhouette 3000 kayıt hesap bütçesini aşıyor; sessiz örneklem kullanılmadı."
        )
    else:
        if control:
            control.check()
        value = float(silhouette_score(x[mask], labels[mask], metric=metric))
        if np.isfinite(value):
            report.update(
                status="valid",
                value=value,
                reason="Seçili/ölçeklenmiş uzayda iç ayrışma; gerçek sınıf veya yeni veri başarısı değildir.",
            )
        else:
            report["reason"] = "Sonlu olmayan ayrışma sonucu."
    return report


def numeric_matrix(frame, columns, features, semantics):
    selected = [next(c for c in columns if c["id"] == ident) for ident in features]
    arrays = []
    for col in selected:
        series = frame[col["name"]]
        role = semantics.get(col["id"], {}).get("role", "")
        if (
            identifier(col, semantics)
            or role in ("category", "ordinal", "ignored")
            or semantics.get(col["id"], {}).get("measurement_level")
            in ("nominal", "ordinal")
            or not series.dtype.is_numeric()
        ):
            raise ProjectError(
                "Yalnız sayısal ölçümler desteklenir; kimlik/kategori/sıra/metin ölçüm değildir. Nominal kodlara uzaklık uydurulmaz."
            )
        if series.null_count():
            raise ProjectError(
                "Seçili ölçüm eksik; açık temizlik sonrası yeniden çalıştırın. Kayıt sessizce dışlanmaz/doldurulmaz."
            )
        values = series.cast(pl.Float64).to_numpy()
        if not np.isfinite(values).all():
            raise ProjectError("NaN/inf veya taşma var; sonlu ölçümler gerekli.")
        if not series.dtype.is_float():
            # Reject rather than silently lose Decimal/large-integer precision.
            if any(
                original != float(converted)
                for original, converted in zip(series, values)
            ):
                raise ProjectError(
                    "Integer/Decimal → Float64 hassasiyet kaybı; bu yol yaklaşık dönüşüm yapmaz."
                )
        arrays.append(values)
    return selected, np.column_stack(arrays)


def calculate(request, parameters, workspace, control=None):
    control = control or Control()
    spec = (
        parameters
        if isinstance(parameters, UnsupervisedSpec)
        else UnsupervisedSpec.from_dict(parameters)
    )
    spec.validate(request["columns"])
    n = request["row_count"]
    if (
        not 2 <= n <= LIMITS[spec.method]
        or n * len(spec.features) * 64 > control.budget.ram_bytes // 2
    ):
        raise ProjectError(
            f"Tam fit bütçesi: 2–{LIMITS[spec.method]} kayıt/20 ölçüm; sessiz örnekleme yok."
        )
    if spec.method == "dbscan" and n * n * 24 > control.budget.ram_bytes // 2:
        raise ProjectError(
            "DBSCAN komşuluklarının en kötü durum bellek bütçesi aşılıyor."
        )
    cost = preflight(spec, n, control.budget)
    checked(request, control)
    control.progress("Seçili ölçümler ve değişmez veri sürümü okunuyor", 0, n)
    selected_names = [
        next(c["name"] for c in request["columns"] if c["id"] == feature)
        for feature in spec.features
    ]
    label_name = next(
        (c["name"] for c in request["columns"] if c["id"] == spec.label_column), None
    )
    frame = pl.read_parquet(
        request["path"],
        columns=["__vu_row_id"] + selected_names + ([label_name] if label_name else []),
    )
    if frame.height != n or frame["__vu_row_id"].n_unique() != n:
        raise ProjectError("Veri kapsamı/RowId uyuşmuyor.")
    selected, raw = numeric_matrix(
        frame, request["columns"], spec.features, request.get("semantic_metadata", {})
    )
    scaler = (
        StandardScaler()
        if spec.scaling == "standard" and spec.method != "iqr"
        else None
    )
    with threadpool_limits(limits=control.budget.cpu_threads):
        train_indices = np.arange(n)
        if spec.anomaly_mode == "novelty":
            train_indices = np.sort(
                np.random.default_rng(spec.seed).choice(
                    n, int(n * spec.training_fraction), replace=False
                )
            )
        if scaler:
            scaler.fit(raw[train_indices])
        x = scaler.transform(raw) if scaler else raw.copy()
        if not np.isfinite(x).all():
            raise ProjectError(
                "Ölçekleme sonucu sonlu değil; değer büyüklüklerini inceleyin."
            )
        control.check()
        control.progress(
            "Etiketsiz analiz: kayıtlı tam sürüm veya ayrılmış novelty eğitim kapsamı",
            0,
            n,
        )
        labels = flags = scores = None
        threshold = None
        method_state = {}
        if spec.method in CLUSTER_METHODS:
            model, labels, method_state = fit_cluster(x, spec, control)
            method_state["comparison"] = comparison(
                raw,
                x,
                labels,
                method_state,
                spec,
                control,
                frame["__vu_row_id"].to_list(),
            )
        elif spec.method in ("lof", "one_class_svm", "robust_covariance"):
            scores, flags, threshold, method_state = anomaly(x, spec, control)
        elif spec.method == "isolation_forest":
            model = IsolationForest(
                n_estimators=100,
                max_samples=min(256, n),
                contamination=spec.contamination
                if spec.threshold_mode == "fraction"
                else "auto",
                random_state=spec.seed,
                n_jobs=1,
            )
            model.fit(x)
            scores = -model.score_samples(x)
            threshold = (
                float(-model.offset_)
                if spec.threshold_mode == "fraction"
                else spec.score_threshold
            )
            flags = scores > threshold
            method_state = dict(
                n_estimators=100,
                max_samples=min(256, n),
                threshold_rule="score > threshold; equal is not flagged",
            )
        else:
            q1, q3 = np.quantile(raw[:, 0], [0.25, 0.75], method="linear")
            width = q3 - q1
            lower, upper = (
                q1 - spec.iqr_multiplier * width,
                q3 + spec.iqr_multiplier * width,
            )
            if not np.isfinite([q1, q3, width, lower, upper]).all():
                raise ProjectError(
                    "IQR eşikleri taşma üretti; değer büyüklüklerini inceleyin."
                )
            flags = (raw[:, 0] < lower) | (raw[:, 0] > upper)
            # Raw-unit excess beyond the selected fences: zero means within/on fence.
            scores = np.maximum(np.maximum(lower - raw[:, 0], raw[:, 0] - upper), 0)
            threshold = 0.0
            method_state = dict(
                q1=float(q1),
                q3=float(q3),
                iqr=float(width),
                lower=float(lower),
                upper=float(upper),
                quantile="linear h=(n-1)*q",
                zero_iqr="Strictly outside equal fences is a candidate",
                threshold_rule="score > 0; fence equality is not flagged",
            )
        control.check()
        separation = (
            silhouette(x, labels, control, spec.metric) if labels is not None else None
        )
    scored_mask = np.isfinite(scores) if scores is not None else np.ones(n, dtype=bool)
    profiles = []
    for label in np.unique(labels) if labels is not None else [False, True]:
        mask = labels == label if labels is not None else (flags == label) & scored_mask
        indices = np.flatnonzero(mask)
        name = (
            ("Gürültü noktaları" if label == -1 else f"Küme {int(label)}")
            if labels is not None
            else ("Anomali adayı" if label else "İşaretlenmeyen kayıtlar")
        )
        profiles.append(
            dict(
                label=int(label),
                name=name,
                count=len(indices),
                measurements=[
                    dict(
                        column_id=c["id"],
                        name=c["name"],
                        mean=float(raw[mask, j].mean()) if mask.any() else None,
                        min=float(raw[mask, j].min()) if mask.any() else None,
                        max=float(raw[mask, j].max()) if mask.any() else None,
                    )
                    for j, c in enumerate(selected)
                ],
                examples=[
                    dict(
                        row_id=frame["__vu_row_id"][int(i)],
                        values={
                            c["name"]: float(raw[i, j]) for j, c in enumerate(selected)
                        },
                        score=float(scores[i]) if scores is not None else None,
                    )
                    for i in indices[:5]
                ],
            )
        )
    if not scored_mask.all():
        profiles.append(
            dict(
                label=2,
                name="Novelty eğitim kayıtları — skorlanmadı",
                count=int((~scored_mask).sum()),
                measurements=[],
                examples=[],
            )
        )
    assignments = frame.select("__vu_row_id")
    if labels is not None:
        assignments = assignments.with_columns(
            pl.Series("cluster", labels.astype(np.int64))
        )
    else:
        if not np.isfinite(scores[scored_mask]).all():
            raise ProjectError("Anomali skorları sonlu değil.")
        assignments = assignments.with_columns(
            pl.Series(
                "anomaly_score",
                [float(v) if np.isfinite(v) else None for v in scores],
                dtype=pl.Float64,
            ),
            pl.Series(
                "anomaly_candidate",
                [bool(v) if scored_mask[i] else None for i, v in enumerate(flags)],
                dtype=pl.Boolean,
            ),
        )
    path = Path(workspace) / "assignments.parquet"
    assignments.write_parquet(path)
    result = dict(
        schema="UnsupervisedRun/v1",
        run_id="unsupervised:" + uid(),
        dataset_version=request["version_id"],
        spec=spec.data(),
        config_revision=request.get("config_revision", 0),
        rows=n,
        fit_scope="full_selected_dataset_version; no view filters; no holdout"
        if spec.anomaly_mode == "outlier"
        else "seeded disjoint training/heldout novelty; train-only scaling; no view filters",
        compute_preflight=cost,
        cpu_threads=control.budget.cpu_threads,
        row_ids=frame["__vu_row_id"].to_list(),
        fit_row_ids=frame["__vu_row_id"].gather(train_indices).to_list(),
        selected_measurements=selected,
        scaling_state=dict(mean=scaler.mean_.tolist(), scale=scaler.scale_.tolist())
        if scaler
        else None,
        method_state=method_state,
        profiles=profiles,
        silhouette=separation,
        noise_count=int((labels == -1).sum()) if labels is not None else 0,
        flagged_count=int(flags.sum()) if flags is not None else 0,
        threshold=threshold,
        score_direction="higher = more unusual; candidate only"
        if scores is not None
        else None,
        score_units="raw measurement units beyond IQR fences"
        if spec.method == "iqr"
        else method_state.get("score_origin", "negative sklearn score_samples")
        if scores is not None
        else None,
        evaluation=dict(
            labels_available=False,
            precision=None,
            recall=None,
            reason="Gerçek etiket yok; precision/recall hesaplanamaz. İç ayrışma doğruluk değildir.",
        ),
        new_data=dict(
            native_support=spec.method
            in (
                "kmeans",
                "isolation_forest",
                "iqr",
                "gmm",
                "one_class_svm",
                "robust_covariance",
            )
            or (spec.method == "lof" and spec.anomaly_mode == "novelty"),
            available=False,
            reason="DBSCAN doğal predict sağlamaz; yeni veriye atama desteklenmiyor."
            if spec.method == "dbscan"
            else "Yöntem yeni veriye uygulanabilir; bu fazda yalnız fit kapsamı işaretlenir. Güvenli model/yeni dosya uygulaması henüz mevcut değil.",
        ),
        projection=None,
        warning="Kümeler fiziksel gerçek sınıflar değildir; gürültü/anomali adayları kesin veri hatası değildir. Otomatik silme yok.",
        provenance=dict(
            snapshot_fingerprint=request["fingerprint"],
            snapshot_uri=request["snapshot_uri"],
            source_snapshot_id=request["source_snapshot_id"],
            created_at=datetime.now(timezone.utc).isoformat(),
            backend="scikit-learn",
            backend_version=sklearn.__version__,
            numpy_version=np.__version__,
            seed=spec.seed,
            seed_used=spec.method
            in ("kmeans", "isolation_forest", "gmm", "robust_covariance")
            or bool(spec.stability_runs)
            or spec.anomaly_mode == "novelty",
            help_content_version=63,
        ),
    )
    if label_name:
        truth_series = frame[label_name]
        if truth_series.null_count() or set(truth_series.unique().to_list()) != {0, 1}:
            raise ProjectError("Anomali etiketi eksiksiz 0/1 olmalı.")
        result["evaluation"] = evaluation(truth_series.to_numpy(), scores, flags, spec)
    if spec.method not in ("kmeans", "dbscan", "isolation_forest", "iqr"):
        result["new_data"]["reason"] = (
            "Phase47: yalnız kaydedilen fit/heldout kapsamı; yeni dosya ve safe model persistence kapalı."
        )
    if spec.method in ("kmeans", "isolation_forest", "iqr"):
        from sklearn.pipeline import Pipeline

        from veri_ufku.modeling.lifecycle import (
            IQRBounds,
            Measurements,
            card_for,
            save_package,
        )

        result["fit_row_ids"] = frame["__vu_row_id"].to_list()
        estimator = (
            IQRBounds(float(lower), float(upper)) if spec.method == "iqr" else model
        )
        fitted = Pipeline(
            [("prepare", Measurements(selected_names, scaler)), ("baseline", estimator)]
        )
        card = card_for(
            fitted, result, request["columns"], request.get("semantic_metadata")
        )
        package_path = Path(workspace) / ("model-" + uid() + ".vumodel")
        save_package(package_path, fitted, card)
        result["model_card"] = card
        result["model_package"] = dict(
            path=str(package_path), fingerprint=file_hash(package_path)
        )
        result["new_data"] = dict(
            native_support=True,
            available=True,
            reason="Kayıtlı güvenli pipeline ile yeni veri önizlemesi/tahmini desteklenir; tekrar fit yok.",
        )
    checked(request, control)
    control.disk(Path(workspace))
    control.check()
    return dict(
        result, assignment_path=str(path), assignment_fingerprint=file_hash(path)
    )
