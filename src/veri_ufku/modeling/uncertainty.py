"""Bounded split calibration and conformal predictions; no fit during inference."""

import copy
import importlib.metadata
import math
import warnings
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy.special import expit
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import (
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.exceptions import ConvergenceWarning
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import log_loss

from veri_ufku.modeling.validation import digest, split_plan
from veri_ufku.storage.project_model import ProjectError, uid

LIMITATIONS = (
    "Brier kalibrasyon, ayırt etme ve veri belirsizliğini birlikte ölçer; tek başına kalibrasyon değildir. "
    "Conformal coverage exchangeability gerektirir; grup/zaman ayrımı bunu kanıtlamaz. "
    "Nominal coverage her alt grupta veya gelecek dağılımda garanti değildir. "
    "Predictive interval yeni gözlemi kapsar; parametrenin CI aralığı değildir. "
    "Quantile aralığı kendi başına conformal coverage garantisi taşımaz."
)


@dataclass(frozen=True)
class UncertaintySpec:
    model: str = "logistic"
    calibration: str = "sigmoid"
    prediction: str = "sets"
    alpha: float = 0.1
    bins: int = 10
    threshold: str = "cost"
    positive_class: str = ""
    false_positive_cost: float = 1.0
    false_negative_cost: float = 1.0
    min_precision: float = 0.0
    min_recall: float = 0.0

    @classmethod
    def from_dict(cls, value, purpose):
        try:
            spec = cls(**value)
        except (TypeError, ValueError):
            raise ProjectError("Kalibrasyon/belirsizlik tarifi geçersiz.") from None
        allowed = (
            ("logistic", "forest")
            if purpose == "classification"
            else ("ridge", "forest", "quantile")
        )
        if (
            spec.model not in allowed
            or spec.calibration not in ("none", "sigmoid", "isotonic")
            or spec.prediction not in ("none", "sets", "interval", "quantile", "cqr")
            or spec.threshold not in ("default", "cost", "precision", "recall")
        ):
            raise ProjectError(
                "Bu model/yöntem belirsizlik adaptöründe desteklenmiyor."
            )
        if purpose == "classification":
            if spec.prediction not in ("none", "sets"):
                raise ProjectError(
                    "Sınıflandırmada predictive interval değil prediction set seçin."
                )
        elif purpose == "regression":
            if (
                spec.calibration != "none"
                or spec.threshold != "default"
                or spec.positive_class
                or spec.prediction not in ("none", "interval", "quantile", "cqr")
                or (spec.model == "quantile")
                != (spec.prediction in ("quantile", "cqr"))
            ):
                raise ProjectError(
                    "Quantile/CQR yalnız quantile model; diğer regresyonda split residual interval desteklenir."
                )
        else:
            raise ProjectError("Belirsizlik yalnız supervised tek hedef içindir.")
        for key in (
            "alpha",
            "false_positive_cost",
            "false_negative_cost",
            "min_precision",
            "min_recall",
        ):
            v = getattr(spec, key)
            if type(v) not in (int, float) or not math.isfinite(v):
                raise ProjectError("Coverage/maliyet/constraint sonlu sayı olmalı.")
        if (
            not 0.05 <= spec.alpha <= 0.5
            or type(spec.bins) is not int
            or not 2 <= spec.bins <= 20
            or not 0 <= spec.min_precision <= 1
            or not 0 <= spec.min_recall <= 1
            or min(spec.false_positive_cost, spec.false_negative_cost) < 0
            or spec.false_positive_cost + spec.false_negative_cost <= 0
            or not isinstance(spec.positive_class, str)
            or len(spec.positive_class) > 256
        ):
            raise ProjectError(
                "Alpha .05.. .5; bins2..20; maliyet ≥0 ve toplam >0; constraint0..1 olmalı."
            )
        return spec

    def data(self):
        return asdict(self)


def checked_probability(values, n, labels):
    p = np.asarray(values, dtype=float)
    if (
        p.shape != (n, len(labels))
        or not np.isfinite(p).all()
        or np.any(p < 0)
        or np.any(p > 1)
        or not np.allclose(p.sum(axis=1), 1, atol=1e-8)
    ):
        raise ProjectError("Olasılık boyutu, label order veya normalization geçersiz.")
    return p


def probability_report(y, p, labels, bins):
    y = np.asarray(y)
    if not len(y) or not set(y) <= set(labels):
        raise ProjectError("Evaluation unseen class içeriyor; skor üretilmedi.")
    p = checked_probability(p, len(y), labels)
    actual = np.array([[int(v == label) for label in labels] for v in y])
    # Binary positive squared error; multiclass full sum, explicitly different scales.
    brier = np.mean(np.sum((p - actual) ** 2, axis=1)) / (2 if len(labels) == 2 else 1)
    curves = []
    for j, label in enumerate(labels):
        membership = np.searchsorted(np.linspace(0, 1, bins + 1)[1:-1], p[:, j])
        points = []
        for b in range(bins):
            mask = membership == b
            if mask.any():
                points.append(
                    dict(
                        bin=b,
                        lower=b / bins,
                        upper=(b + 1) / bins,
                        n=int(mask.sum()),
                        mean_probability=float(p[mask, j].mean()),
                        fraction_positive=float(actual[mask, j].mean()),
                    )
                )
        curves.append(
            dict(
                label=label,
                points=points,
                binning="uniform [0,1]; boundary belongs to lower bin; empty bins omitted",
                bins=bins,
                n=len(y),
                empty_bins_omitted=True,
            )
        )
    # sklearn sorts string labels: reorder explicitly rather than silently mislabel columns.
    sorted_labels = sorted(labels)
    loss = log_loss(
        y, p[:, [labels.index(c) for c in sorted_labels]], labels=sorted_labels
    )
    return dict(
        log_loss=float(loss),
        brier=float(brier),
        brier_scale="binary [0,1]" if len(labels) == 2 else "multiclass sum [0,2]",
        reliability=curves,
        n=len(y),
        label_order=list(labels),
        exclusions=0,
        note=LIMITATIONS,
    )


def threshold_choice(y, p, labels, spec):
    if len(labels) != 2:
        if (
            spec.threshold != "default"
            or spec.positive_class
            or spec.min_precision
            or spec.min_recall
        ):
            raise ProjectError(
                "Çok sınıflı modelde binary eşik/maliyet yolu kapalı; argmax kullanılır."
            )
        return None
    if spec.positive_class not in labels:
        raise ProjectError("Binary pozitif sınıfı label order içinden açıkça seçin.")
    p = checked_probability(p, len(y), labels)[:, labels.index(spec.positive_class)]
    actual = np.asarray(y) == spec.positive_class
    if not actual.any() or actual.all():
        raise ProjectError("Threshold validation her iki sınıfı içermeli.")
    grid = sorted(set([0.0, 0.5, 1.0, float(np.nextafter(1.0, 2.0))] + p.tolist()))
    history = []
    for t in grid:
        predicted = p >= t
        tp, fp, fn = (
            int(np.sum(actual & predicted)),
            int(np.sum(~actual & predicted)),
            int(np.sum(actual & ~predicted)),
        )
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn)
        cost = (fp * spec.false_positive_cost + fn * spec.false_negative_cost) / len(y)
        feasible = (
            spec.min_precision == 0
            or precision is not None
            and precision >= spec.min_precision
        ) and recall >= spec.min_recall
        history.append(
            dict(
                threshold=t,
                precision=precision,
                recall=recall,
                cost_per_record=cost,
                tp=tp,
                fp=fp,
                fn=fn,
                feasible=bool(feasible),
            )
        )
    if spec.threshold == "default":
        winner = next(h for h in history if h["threshold"] == 0.5)
        if not winner["feasible"]:
            raise ProjectError("Default eşik validation constraint sağlamıyor.")
    else:
        feasible = [h for h in history if h["feasible"]]
        if not feasible:
            raise ProjectError(
                "Validation eşik constraint karşılanamıyor; test görülmedi."
            )
        if spec.threshold == "precision":
            feasible = [h for h in feasible if h["precision"] is not None]
            if not feasible:
                raise ProjectError("Precision eşik constraint tanımsız.")
            winner = min(
                feasible,
                key=lambda h: (-h["precision"], h["cost_per_record"], h["threshold"]),
            )
        elif spec.threshold == "recall":
            winner = min(
                feasible,
                key=lambda h: (-h["recall"], h["cost_per_record"], h["threshold"]),
            )
        else:
            winner = min(
                feasible,
                key=lambda h: (
                    h["cost_per_record"],
                    abs(h["threshold"] - 0.5),
                    h["threshold"],
                ),
            )
    return dict(
        winner=winner,
        candidates=history,
        selection_scope="validation",
        positive_class=spec.positive_class,
        mode=spec.threshold,
    )


def decision_performance(actual, predicted, spec):
    truth = np.asarray(actual) == spec.positive_class
    selected = np.asarray(predicted) == spec.positive_class
    tp = int(np.sum(truth & selected))
    fp = int(np.sum(~truth & selected))
    fn = int(np.sum(truth & ~selected))
    tn = int(np.sum(~truth & ~selected))
    return dict(
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
        precision=tp / (tp + fp) if tp + fp else None,
        recall=tp / (tp + fn) if tp + fn else None,
        false_positive_cost=spec.false_positive_cost,
        false_negative_cost=spec.false_negative_cost,
        cost_per_record=(fp * spec.false_positive_cost + fn * spec.false_negative_cost)
        / len(truth),
        selection_scope="validation; final metrics never retune threshold",
    )


def conformal_quantile(scores, alpha):
    scores = np.asarray(scores, dtype=float)
    if not len(scores) or not np.isfinite(scores).all():
        raise ProjectError("Conformal calibration score boş/sonlu değil.")
    rank = math.ceil((len(scores) + 1) * (1 - alpha))
    if rank > len(scores):
        raise ProjectError(
            "Calibration n nominal coverage için yetersiz; sonlu aralık uydurulmadı. Daha fazla calibration kaydı veya daha büyük alpha seçin."
        )
    return float(np.sort(scores)[rank - 1]), rank


class ProbabilityModel(ClassifierMixin, BaseEstimator):
    """Frozen base + reviewed numerical calibration maps. No incoming callable."""

    def __init__(self, base, maps, response, metadata, threshold=None, q=None):
        self.base, self.maps, self.response, self.metadata = (
            base,
            maps,
            response,
            metadata,
        )
        self.threshold, self.q = threshold, q
        self.classes_ = base.classes_.copy()

    def fit(self, X, y=None):
        raise ProjectError("Paket frozen: yeni veri fit edilmez.")

    def __sklearn_is_fitted__(self):
        return True

    def predict_proba(self, X):
        if not self.maps:
            return checked_probability(
                self.base.predict_proba(X), len(X), self.classes_.tolist()
            )
        raw = np.asarray(getattr(self.base, self.response)(X))
        if raw.ndim == 1:
            raw = raw[:, None]
        if self.response == "predict_proba" and len(self.classes_) == 2:
            raw = raw[:, 1:2]
        calibrated = []
        for j, m in enumerate(self.maps):
            calibrated.append(
                expit(-(m["a"] * raw[:, j] + m["b"]))
                if m["method"] == "sigmoid"
                else np.interp(raw[:, j], m["x"], m["y"])
            )
        p = np.column_stack(calibrated)
        if len(self.classes_) == 2:
            p = np.column_stack([1 - p[:, 0], p[:, 0]])
        else:
            totals = p.sum(axis=1)
            p = np.divide(
                p,
                totals[:, None],
                out=np.full_like(p, 1 / len(self.classes_)),
                where=totals[:, None] != 0,
            )
        return checked_probability(p, len(X), self.classes_.tolist())

    def predict(self, X):
        p = self.predict_proba(X)
        if self.threshold is None:
            return self.classes_[p.argmax(axis=1)]
        index = self.classes_.tolist().index(self.metadata["spec"]["positive_class"])
        return np.where(
            p[:, index] >= self.threshold,
            self.classes_[index],
            self.classes_[1 - index],
        )

    def prediction_sets(self, X):
        if self.q is None:
            raise ProjectError("Bu paket conformal prediction sets desteklemiyor.")
        p = self.predict_proba(X)
        return [
            [str(self.classes_[j]) for j in np.flatnonzero(1 - row <= self.q)]
            for row in p
        ]


class IntervalModel(RegressorMixin, BaseEstimator):
    def __init__(self, base, metadata, q=None, lower=None, upper=None):
        self.base, self.metadata, self.q = base, metadata, q
        self.lower, self.upper = lower, upper

    def fit(self, X, y=None):
        raise ProjectError("Paket frozen: yeni veri fit edilmez.")

    def __sklearn_is_fitted__(self):
        return True

    def predict(self, X):
        return self.base.predict(X)

    def intervals(self, X):
        mode = self.metadata["spec"]["prediction"]
        if mode == "none":
            raise ProjectError("Bu paket interval desteklemiyor.")
        if self.lower is None:
            pred = self.predict(X)
            return np.column_stack((pred - self.q, pred + self.q)), 0
        lo, hi = self.lower.predict(X), self.upper.predict(X)
        crossing = int(np.count_nonzero(lo > hi))
        # Explicit monotone rearrangement is part of the declared prediction method.
        lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
        q = self.q if mode == "cqr" else 0
        return np.column_stack((lo - q, hi + q)), crossing


def partitions(
    row_ids, y, groups, times, spec, method, classification, outer, dataset, fingerprint
):
    train, val, dev, test, folds = outer
    inner_spec = replace(spec, folds=2)
    inner_plan, (fit, pcal, _, ccal, _) = split_plan(
        [row_ids[i] for i in train],
        y[train],
        groups[train] if groups is not None else None,
        times[train] if times is not None else None,
        inner_spec,
        method,
        classification,
        dataset,
        fingerprint,
    )
    mapped = [train[s] for s in (fit, pcal, ccal)]
    pools = dict(
        fit=mapped[0],
        probability_calibration=mapped[1],
        conformal_calibration=mapped[2],
        validation=val,
        test=test,
    )
    # Nested time purging is retained, not silently appended back to fit.
    pools["unused"] = np.array(
        sorted(
            set(range(len(row_ids)))
            - set(np.concatenate(list(pools.values())).tolist())
        ),
        dtype=int,
    )
    return pools, inner_plan


def calculate_run(
    request,
    workspace,
    control,
    p,
    frame,
    y,
    groups,
    times,
    protocol,
    method,
    strategy,
    reason,
    plan,
    outer,
    excluded,
):
    from veri_ufku.modeling.baseline import checked, pipeline
    from veri_ufku.modeling.lifecycle import card_for, load_package, save_package
    from veri_ufku.storage.project_store import file_hash

    classification = p["spec"]["purpose"] == "classification"
    config_key = "classification" if classification else "regression"
    from veri_ufku.modeling.classification import settings as classification_settings
    from veri_ufku.modeling.regression import settings as regression_settings

    config = (classification_settings if classification else regression_settings)(
        request[config_key]
    )
    spec = UncertaintySpec.from_dict(config["uncertainty"], p["spec"]["purpose"])
    if len(frame) > 1000 or len(p["spec"]["features"]) > 32:
        raise ProjectError(
            "Belirsizlik adapter ComputeBudget: 1000 kayıt/32 özellik üst sınırı."
        )
    if config.get("family_options") or p["spec"].get("text"):
        raise ProjectError(
            "Bu belirsizlik adapter family weight/sparse/ensemble/TF-IDF desteklemiyor."
        )
    row_ids = frame["__vu_row_id"].to_list()
    pools, inner_plan = partitions(
        row_ids,
        y,
        groups,
        times,
        protocol,
        method,
        classification,
        outer,
        request["version_id"],
        request["fingerprint"],
    )
    membership = {k: sorted(row_ids[i] for i in v) for k, v in pools.items()}
    pool_id = "uncertainty:" + digest(
        dict(
            membership=membership,
            spec=spec.data(),
            outer=plan["split_id"],
            inner=inner_plan["split_id"],
        )
    )
    metadata = dict(
        schema="UncertaintyModel/v1",
        spec=spec.data(),
        membership=membership,
        partition_id=pool_id,
        inner_plan=inner_plan,
        train_n=len(pools["fit"]),
        calibration_n=len(pools["probability_calibration"]),
        probability_calibration_used_n=len(pools["probability_calibration"])
        if classification and spec.calibration != "none"
        else 0,
        conformal_calibration_used_n=len(pools["conformal_calibration"])
        if spec.prediction in ("sets", "interval", "cqr")
        else 0,
        conformal_n=len(pools["conformal_calibration"]),
        validation_n=len(pools["validation"]),
        limitations=LIMITATIONS,
        probability_fit_scope="independent held-out probability_calibration",
        conformal_fit_scope="separate held-out conformal_calibration",
        threshold_fit_scope="validation",
        exchangeability="required, not verified or asserted; group/time preservation alone does not establish it",
        preprocessing_fit_scope="fit only",
        nominal_coverage=1 - spec.alpha if spec.prediction != "none" else None,
    )
    frozen = request.get("frozen_uncertainty_package")
    if request.get("mode") == "final":
        if not frozen or file_hash(frozen["path"]) != frozen["fingerprint"]:
            raise ProjectError("Final test dondurulmuş belirsizlik paketi gerektirir.")
        model, old_card = load_package(frozen["path"])
        learner = model.named_steps["baseline"]
        if (
            type(learner) not in (ProbabilityModel, IntervalModel)
            or learner.metadata["partition_id"] != pool_id
            or old_card["split"] != plan
            or old_card["candidate_selection"]["parameters"] != config
            or old_card["decision"] != request.get("decision")
            or old_card["snapshot_fingerprint"] != request["fingerprint"]
        ):
            raise ProjectError(
                "Final calibration/model/threshold frozen karar uyuşmuyor."
            )
        metadata = copy.deepcopy(learner.metadata)
        decision = copy.deepcopy(old_card["decision"])
        fit_calls = 0
    else:
        fit, pc, cc = (
            pools[k]
            for k in ("fit", "probability_calibration", "conformal_calibration")
        )
        max_cells = min(5000 * 512, control.budget.ram_bytes // 64)
        model = pipeline(p, strategy, protocol.seed, max_cells)
        if classification:
            base = (
                LogisticRegression(
                    C=config["C"], max_iter=500, random_state=protocol.seed
                )
                if spec.model == "logistic"
                else RandomForestClassifier(
                    n_estimators=config["trees"],
                    max_depth=config["depth"],
                    min_samples_leaf=2,
                    n_jobs=1,
                    random_state=protocol.seed,
                )
            )
        else:
            base = (
                Ridge(alpha=config["alpha"])
                if spec.model == "ridge"
                else RandomForestRegressor(
                    n_estimators=config["trees"],
                    max_depth=config["depth"],
                    min_samples_leaf=2,
                    n_jobs=1,
                    random_state=protocol.seed,
                )
                if spec.model == "forest"
                else GradientBoostingRegressor(
                    loss="squared_error",
                    n_estimators=50,
                    max_depth=3,
                    random_state=protocol.seed,
                )
            )
        model.steps[-1] = ("baseline", base)
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            model.fit(frame[fit.tolist()], y[fit])
        fit_calls = 1
        control.check()
        prep = model.named_steps["prepare"]
        if classification:
            labels = base.classes_.tolist()
            if (
                set(labels) != set(y)
                or set(y[pc]) != set(labels)
                or set(y[cc]) != set(labels)
                or set(y[pools["validation"]]) != set(labels)
            ):
                raise ProjectError(
                    "Train/calibration/validation sınıfları tam olmalı; unseen class engellendi."
                )
            if len(labels) != 2 and (
                spec.threshold != "default" or spec.positive_class
            ):
                raise ProjectError(
                    "Multiclass eşik desteklenmiyor; default argmax seçin."
                )
            maps, response = [], "predict_proba"
            if spec.calibration != "none":
                calibrated = CalibratedClassifierCV(
                    FrozenEstimator(base),
                    method=spec.calibration,
                    # FrozenEstimator.fit is a no-op; explicit identity prediction
                    # avoids sklearn's default random CV inside held-out calibration.
                    cv=[(np.arange(len(pc)), np.arange(len(pc)))],
                    ensemble=False,
                ).fit(prep.transform(frame[pc.tolist()]), y[pc])
                fit_calls += 1
                c = calibrated.calibrated_classifiers_[0]
                response = (
                    "decision_function"
                    if hasattr(base, "decision_function")
                    else "predict_proba"
                )
                for cal in c.calibrators:
                    maps.append(
                        dict(method="sigmoid", a=float(cal.a_), b=float(cal.b_))
                        if spec.calibration == "sigmoid"
                        else dict(
                            method="isotonic",
                            x=cal.X_thresholds_.tolist(),
                            y=cal.y_thresholds_.tolist(),
                        )
                    )
                metadata["warnings"] = (
                    ["Isotonic küçük calibration örneğinde aşırı öğrenebilir; n<1000."]
                    if spec.calibration == "isotonic" and len(pc) < 1000
                    else []
                )
            learner = ProbabilityModel(base, maps, response, metadata)
            if spec.prediction == "sets":
                proba = learner.predict_proba(prep.transform(frame[cc.tolist()]))
                scores = 1 - proba[np.arange(len(cc)), [labels.index(v) for v in y[cc]]]
                learner.q, rank = conformal_quantile(scores, spec.alpha)
                metadata.update(
                    conformal_scores=scores.tolist(),
                    conformal_rank=rank,
                    conformal_q=learner.q,
                    conformal_score="1 - calibrated p(true class)",
                )
            vp = learner.predict_proba(
                prep.transform(frame[pools["validation"].tolist()])
            )
            selected = threshold_choice(y[pools["validation"]], vp, labels, spec)
            if selected:
                learner.threshold = selected["winner"]["threshold"]
            decision = dict(
                model=spec.model,
                positive_class=spec.positive_class,
                threshold=learner.threshold,
                mode=spec.threshold,
                selection_scope="validation",
                validation_row_ids=membership["validation"],
                objective=spec.threshold,
                cost_note="validation-only bounded uncertainty constraints",
                threshold_report=selected,
            )
        else:
            learner = IntervalModel(base, metadata)
            if spec.model == "quantile":
                for key, alpha in (
                    ("lower", spec.alpha / 2),
                    ("upper", 1 - spec.alpha / 2),
                ):
                    control.check()
                    estimator = GradientBoostingRegressor(
                        loss="quantile",
                        alpha=alpha,
                        n_estimators=50,
                        max_depth=3,
                        random_state=protocol.seed,
                    )
                    estimator.fit(prep.transform(frame[fit.tolist()]), y[fit])
                    setattr(learner, key, estimator)
                    fit_calls += 1
                metadata["quantile_rearrangement"] = (
                    "pointwise lower=min(q_low,q_high), upper=max; crossing count reported"
                )
            if spec.prediction in ("interval", "cqr"):
                xc = prep.transform(frame[cc.tolist()])
                if spec.prediction == "interval":
                    scores = np.abs(y[cc] - base.predict(xc))
                else:
                    bounds, _ = (
                        learner.intervals(xc)
                        if spec.prediction == "quantile"
                        else (
                            np.sort(
                                np.column_stack(
                                    [
                                        learner.lower.predict(xc),
                                        learner.upper.predict(xc),
                                    ]
                                ),
                                axis=1,
                            ),
                            0,
                        )
                    )
                    scores = np.maximum(bounds[:, 0] - y[cc], y[cc] - bounds[:, 1])
                    # Conservative nonnegative CQR expansion avoids empty intervals.
                    scores = np.maximum(scores, 0)
                learner.q, rank = conformal_quantile(scores, spec.alpha)
                metadata.update(
                    conformal_scores=scores.tolist(),
                    conformal_rank=rank,
                    conformal_q=learner.q,
                    conformal_score="absolute residual"
                    if spec.prediction == "interval"
                    else "max(lower-y,y-upper,0); conservative CQR",
                )
            decision = None
        model.steps[-1] = ("baseline", learner)
    control.check()
    evaluation_index = (
        pools["test"] if request.get("mode") == "final" else pools["validation"]
    )
    scope = "final_test" if request.get("mode") == "final" else "validation"
    batch, actual = frame[evaluation_index.tolist()], y[evaluation_index]
    pred = model.predict(batch)
    transformed = model.named_steps["prepare"].transform(batch)
    records = [
        dict(
            row_id=row_ids[i],
            actual=str(actual[j]) if classification else float(actual[j]),
            predicted=str(pred[j]) if classification else float(pred[j]),
        )
        for j, i in enumerate(evaluation_index)
    ]
    report = dict(
        n=len(actual),
        scope=scope,
        nominal_coverage=1 - spec.alpha if spec.prediction != "none" else None,
        empirical_coverage=None,
        mean_width=None,
        mean_set_size=None,
        limitations=LIMITATIONS,
    )
    metrics = []
    if classification:
        labels = learner.classes_.tolist()
        proba = model.predict_proba(batch)
        report["probability"] = probability_report(actual, proba, labels, spec.bins)
        report["uncalibrated_probability"] = probability_report(
            actual, learner.base.predict_proba(transformed), labels, spec.bins
        )
        if len(labels) == 2:
            report["decision"] = decision_performance(actual, pred, spec)
        for name in ("log_loss", "brier"):
            metrics.append(
                dict(
                    metric=name,
                    value=report["probability"][name],
                    n=len(actual),
                    scope=scope,
                    direction="minimize",
                    status="valid",
                )
            )
        metrics.append(
            dict(
                metric="accuracy",
                value=float(np.mean(pred == actual)),
                n=len(actual),
                scope=scope,
                direction="maximize",
                status="valid",
            )
        )
        for j, r in enumerate(records):
            r["probabilities"] = proba[j].tolist()
        if spec.prediction == "sets":
            sets = learner.prediction_sets(transformed)
            report.update(
                empirical_coverage=float(
                    np.mean([v in s for v, s in zip(actual, sets, strict=True)])
                ),
                mean_set_size=float(np.mean([len(s) for s in sets])),
                empty_set_n=sum(not s for s in sets),
                full_set_n=sum(len(s) == len(labels) for s in sets),
            )
            for r, s in zip(records, sets, strict=True):
                r["prediction_set"] = s
    else:
        from veri_ufku.modeling.baseline import regression_scores

        metrics = regression_scores(actual, pred, scope)
        if spec.prediction != "none":
            intervals, crossing = learner.intervals(transformed)
            if not np.isfinite(intervals).all() or np.any(
                intervals[:, 0] > intervals[:, 1]
            ):
                raise ProjectError("Predictive interval sonlu/sıralı değil.")
            report.update(
                empirical_coverage=float(
                    np.mean((actual >= intervals[:, 0]) & (actual <= intervals[:, 1]))
                ),
                mean_width=float(np.mean(intervals[:, 1] - intervals[:, 0])),
                quantile_crossing_n=crossing,
                interval_kind="predictive, not parameter CI",
                coverage_status="empirical only; quantile alone has no conformal guarantee"
                if spec.prediction == "quantile"
                else "marginal under exchangeability; not subgroup/future guarantee",
            )
            for r, bounds in zip(records, intervals, strict=True):
                r.update(lower=float(bounds[0]), upper=float(bounds[1]))
    evaluation = dict(
        scope=scope,
        status="valid",
        train_n=len(pools["fit"]),
        evaluation_n=len(actual),
        fit_row_ids=membership["fit"],
        fitted_parameters=model.named_steps["prepare"].summary_,
        metrics=metrics,
        uncertainty_report=report,
        prediction_records=records,
    )
    result = dict(
        schema="BaselineRun/v1",
        status="completed",
        run_id=request.get("run_id", "run:" + uid()),
        mode=request.get("mode", "development"),
        dataset_version=request["version_id"],
        origin_version=request["origin_version"],
        source_snapshot_id=request["source_snapshot_id"],
        snapshot_fingerprint=request["fingerprint"],
        pipeline_id=p["plan"]["version_id"],
        pipeline=p["plan"],
        preparation_spec=p["spec"],
        history=p["history"],
        spec=protocol.data(),
        plan=plan,
        baseline=strategy,
        default_reason=reason,
        seed=protocol.seed,
        excluded_target_row_ids=excluded,
        evaluations=[evaluation],
        invalid_folds=[],
        cv_summary=[],
        comparison=[],
        selected_model=spec.model,
        selection_rule="explicit bounded uncertainty template; train/calibration/validation/test isolated; final frozen package without refit",
        prior_test_use_ids=request.get("prior_test_use_ids", []),
        interpretation="exploratory"
        if request.get("prior_test_use_ids")
        else "project_test_not_previously_used",
        external_test_use_known=False,
        data_access_at=request.get("data_access_at"),
        evaluated_at=datetime.now(UTC).isoformat(),
        config_revision=request.get("config_revision", 0),
        packages={
            n: importlib.metadata.version(n)
            for n in ("scikit-learn", "numpy", "scipy", "polars", "veri-ufku")
        },
        help_content_version=66,
        leakage_certified=False,
        uncertainty=metadata,
        decision=decision,
        fit_count=fit_calls,
        estimated_cost=dict(
            train_n=len(pools["fit"]),
            validation_n=len(pools["validation"]),
            development_n=len(outer[2]),
            test_n=len(pools["test"]),
            fold_train_n=[],
            fit_count=fit_calls,
            estimated_fit_row_passes=len(pools["fit"]),
            calibration_n=len(pools["probability_calibration"]),
            conformal_n=len(pools["conformal_calibration"]),
        ),
        **{config_key: config},
    )
    if classification:
        result.update(classes=learner.classes_.tolist(), decision_validation=None)
    card = card_for(model, result, request["columns"], request.get("semantic_metadata"))
    card.update(
        uncertainty=metadata,
        fit_scope="isolated proper train; calibrator/threshold frozen; no final refit",
        limitations=LIMITATIONS,
    )
    package_path = Path(workspace) / ("model-" + uid() + ".vumodel")
    save_package(package_path, model, card)
    result.update(
        model_card=card,
        model_package=dict(path=str(package_path), fingerprint=file_hash(package_path)),
    )
    checked(request, control)
    control.disk(Path(workspace))
    control.check()
    return result


def validate_metadata(metadata, card=None):
    purpose = (
        "classification"
        if metadata["spec"]["model"] == "logistic"
        or metadata["spec"]["prediction"] == "sets"
        else (card["purpose"] if card else "regression")
    )
    spec = UncertaintySpec.from_dict(metadata["spec"], purpose)
    if (
        metadata.get("schema") != "UncertaintyModel/v1"
        or metadata.get("limitations") != LIMITATIONS
        or metadata.get("spec") != spec.data()
    ):
        raise ProjectError("Belirsizlik metadata sözleşmesi geçersiz.")
    members = metadata["membership"]
    if set(members) != {
        "fit",
        "probability_calibration",
        "conformal_calibration",
        "validation",
        "test",
        "unused",
    } or any(
        not isinstance(v, list) or len(set(v)) != len(v) or len(v) > 1000
        for v in members.values()
    ):
        raise ProjectError("Belirsizlik partition üyelikleri geçersiz.")
    seen = set()
    for key, ids in members.items():
        if seen & set(ids) or key != "unused" and len(ids) < 2:
            raise ProjectError(
                "Train/calibration/validation/test çakışıyor veya yetersiz."
            )
        seen.update(ids)
    for key, field in (
        ("fit", "train_n"),
        ("probability_calibration", "calibration_n"),
        ("conformal_calibration", "conformal_n"),
        ("validation", "validation_n"),
    ):
        if metadata[field] != len(members[key]):
            raise ProjectError("Calibration n üyelikle uyuşmuyor.")
    if spec.prediction in ("sets", "interval", "cqr"):
        if len(metadata["conformal_scores"]) != len(members["conformal_calibration"]):
            raise ProjectError("Conformal score n uyuşmuyor.")
        q, rank = conformal_quantile(metadata["conformal_scores"], spec.alpha)
        if q != metadata["conformal_q"] or rank != metadata["conformal_rank"] or q < 0:
            raise ProjectError("Conformal rank/score/q uyuşmuyor.")
    if card:
        identity = "uncertainty:" + digest(
            dict(
                membership=members,
                spec=spec.data(),
                outer=card["split"]["split_id"],
                inner=metadata["inner_plan"]["split_id"],
            )
        )
        if (
            metadata["partition_id"] != identity
            or members["test"] != card["split"]["membership"]["test"]
            or members["validation"] != card["split"]["membership"]["validation"]
            or members["fit"] != sorted(card["fit_row_ids"])
        ):
            raise ProjectError("Belirsizlik frozen split/fit kartıyla uyuşmuyor.")
    return spec


def validate_model(model, card):
    spec = validate_metadata(model.metadata, card)
    if model.metadata != card["uncertainty"]:
        raise ProjectError("Calibrator metadata model kartıyla uyuşmuyor.")
    if type(model) is ProbabilityModel:
        if (
            card["purpose"] != "classification"
            or type(model.base) not in (LogisticRegression, RandomForestClassifier)
            or model.classes_.tolist() != model.base.classes_.tolist()
            or model.response not in ("decision_function", "predict_proba")
        ):
            raise ProjectError(
                "Probability wrapper base/label/response desteklenmiyor."
            )
        expected_type = (
            LogisticRegression if spec.model == "logistic" else RandomForestClassifier
        )
        if (
            type(model.base) is not expected_type
            or model.base.random_state != card["seed"]
        ):
            raise ProjectError("Probability base seed/model uyuşmuyor.")
        expected_maps = (
            0
            if spec.calibration == "none"
            else 1
            if len(model.classes_) == 2
            else len(model.classes_)
        )
        if len(model.maps) != expected_maps:
            raise ProjectError("Calibrator sınıf haritası eksik.")
        for m in model.maps:
            if m.get("method") != spec.calibration:
                raise ProjectError("Calibrator yöntem uyuşmuyor.")
            if spec.calibration == "sigmoid":
                if set(m) != {"method", "a", "b"} or not all(
                    type(m[k]) in (int, float) and math.isfinite(m[k])
                    for k in ("a", "b")
                ):
                    raise ProjectError("Sigmoid numeric map geçersiz.")
            elif (
                set(m) != {"method", "x", "y"}
                or len(m["x"]) != len(m["y"])
                or not m["x"]
                or not np.isfinite(m["x"] + m["y"]).all()
                or np.any(np.diff(m["x"]) <= 0)
                or np.any(np.diff(m["y"]) < 0)
                or min(m["y"]) < 0
                or max(m["y"]) > 1
            ):
                raise ProjectError("Isotonic numeric map geçersiz.")
        if (
            model.threshold != card["decision"]["threshold"]
            or model.metadata["spec"]["positive_class"]
            != card["decision"]["positive_class"]
        ):
            raise ProjectError("Model threshold karar/kart uyuşmuyor.")
        config = card["candidate_selection"]["parameters"]
        if (
            type(model.base) is LogisticRegression
            and (model.base.C != config["C"] or model.base.max_iter != 500)
            or type(model.base) is RandomForestClassifier
            and (
                model.base.n_estimators != config["trees"]
                or model.base.max_depth != config["depth"]
                or model.base.n_jobs != 1
                or model.base.min_samples_leaf != 2
            )
        ):
            raise ProjectError("Base classifier kapalı parametre sözleşmesi uyuşmuyor.")
    elif type(model) is IntervalModel:
        expected_type = {
            "ridge": Ridge,
            "forest": RandomForestRegressor,
            "quantile": GradientBoostingRegressor,
        }[spec.model]
        if card["purpose"] != "regression" or type(model.base) is not expected_type:
            raise ProjectError("Interval wrapper base desteklenmiyor.")
        config = card["candidate_selection"]["parameters"]
        if (
            type(model.base) is Ridge
            and model.base.alpha != config["alpha"]
            or type(model.base) is RandomForestRegressor
            and (
                model.base.random_state != card["seed"]
                or model.base.n_estimators != config["trees"]
                or model.base.max_depth != config["depth"]
                or model.base.n_jobs != 1
                or model.base.min_samples_leaf != 2
            )
        ):
            raise ProjectError("Base regressor parametre sözleşmesi uyuşmuyor.")
        if spec.model == "quantile":
            for base, loss, alpha in (
                (model.base, "squared_error", 0.9),
                (model.lower, "quantile", spec.alpha / 2),
                (model.upper, "quantile", 1 - spec.alpha / 2),
            ):
                if (
                    type(base) is not GradientBoostingRegressor
                    or base.loss != loss
                    or base.alpha != alpha
                    or base.random_state != card["seed"]
                    or base.n_estimators != 50
                    or base.max_depth != 3
                ):
                    raise ProjectError(
                        "Quantile kapalı estimator/parametre sözleşmesi uyuşmuyor."
                    )
        elif model.lower is not None or model.upper is not None:
            raise ProjectError("Desteksiz modelde quantile estimator uydurulamaz.")
    else:
        raise ProjectError("Belirsizlik estimator tipi desteklenmiyor.")
    if model.q != model.metadata.get("conformal_q"):
        raise ProjectError("Conformal frozen q uyuşmuyor.")


def validate_saved_run(r):
    from veri_ufku.modeling.classification import settings as classification_settings
    from veri_ufku.modeling.regression import settings as regression_settings

    config = (
        classification_settings(r["classification"])
        if r.get("classification")
        else regression_settings(r["regression"])
    )
    card = r["model_card"]
    spec = validate_metadata(r["uncertainty"], card)
    if (
        config["uncertainty"] != spec.data()
        or card["candidate_selection"]["parameters"] != config
        or card["uncertainty"] != r["uncertainty"]
        or {k: v for k, v in card["split"].items() if k != "membership"}
        != {k: v for k, v in r["plan"].items() if k != "membership"}
        or card["decision"] != r["decision"]
        or r["selected_model"] != spec.model
    ):
        raise ProjectError("Belirsizlik model/seçim/karar kaydı uyuşmuyor.")
    if r.get("details_uri"):
        return
    plan = r["plan"]
    protocol = "protocol:" + digest(dict(spec=r["spec"], method=plan["method"]))
    split = "split:" + digest(
        dict(
            dataset_version=r["dataset_version"],
            fingerprint=r["snapshot_fingerprint"],
            protocol_id=protocol,
            membership=plan["membership"],
        )
    )
    if (
        (protocol, split) != (plan["protocol_id"], plan["split_id"])
        or r["mode"] not in ("development", "final")
        or len(r["evaluations"]) != 1
        or r["cv_summary"]
        or r["comparison"]
    ):
        raise ProjectError("Belirsizlik run split/kapsam uyuşmuyor.")
    e = r["evaluations"][0]
    scope = "final_test" if r["mode"] == "final" else "validation"
    members = r["uncertainty"]["membership"]
    ids = members["test"] if r["mode"] == "final" else members["validation"]
    records = e["prediction_records"]
    if (
        e["scope"] != scope
        or e["status"] != "valid"
        or e["train_n"] != len(members["fit"])
        or sorted(e["fit_row_ids"]) != members["fit"]
        or e["evaluation_n"] != len(ids)
        or sorted(x["row_id"] for x in records) != ids
        or e["fitted_parameters"] != card["fitted_preprocessing"]
    ):
        raise ProjectError("Belirsizlik prediction RowId/fit scope uyuşmuyor.")
    report = e["uncertainty_report"]
    if (
        report["n"] != len(ids)
        or report["scope"] != scope
        or report["limitations"] != LIMITATIONS
        or report["nominal_coverage"]
        != (1 - spec.alpha if spec.prediction != "none" else None)
    ):
        raise ProjectError("Coverage scope/n/varsayım uyuşmuyor.")
    if r.get("classification"):
        labels = r["classes"]
        actual = np.array([x["actual"] for x in records])
        probs = np.array([x["probabilities"] for x in records])
        if (
            labels != card["label_order"]
            or probability_report(actual, probs, labels, spec.bins)
            != report["probability"]
        ):
            raise ProjectError("Probability skor/label order uyuşmuyor.")
        if len(labels) == 2 and report.get("decision") != decision_performance(
            actual, [x["predicted"] for x in records], spec
        ):
            raise ProjectError(
                "Final karar maliyeti/precision/recall raporu uyuşmuyor."
            )
        if r["mode"] == "development":
            threshold = threshold_choice(actual, probs, labels, spec)
            if (
                threshold != r["decision"]["threshold_report"]
                or (threshold["winner"]["threshold"] if threshold else None)
                != r["decision"]["threshold"]
            ):
                raise ProjectError(
                    "Threshold yalnız validation constraint ile seçilmeli."
                )
        index = labels.index(spec.positive_class) if len(labels) == 2 else None
        threshold = r["decision"]["threshold"]
        expected = (
            [
                labels[index] if v[index] >= threshold else labels[1 - index]
                for v in probs
            ]
            if index is not None
            else [labels[int(np.argmax(v))] for v in probs]
        )
        if expected != [x["predicted"] for x in records]:
            raise ProjectError("Prediction frozen threshold/label order uyuşmuyor.")
        if spec.prediction == "sets":
            q = r["uncertainty"]["conformal_q"]
            sets = [
                [label for label, p in zip(labels, v, strict=True) if 1 - p <= q]
                for v in probs
            ]
            if (
                sets != [x["prediction_set"] for x in records]
                or report["empirical_coverage"]
                != float(np.mean([a in s for a, s in zip(actual, sets, strict=True)]))
                or report["mean_set_size"] != float(np.mean([len(s) for s in sets]))
            ):
                raise ProjectError(
                    "Conformal prediction set/empirical coverage uyuşmuyor."
                )
        metric_values = dict(
            log_loss=report["probability"]["log_loss"],
            brier=report["probability"]["brier"],
            accuracy=float(np.mean(actual == np.array(expected))),
        )
    else:
        from veri_ufku.modeling.baseline import regression_scores

        actual = np.array([x["actual"] for x in records])
        predicted = np.array([x["predicted"] for x in records])
        metric_values = {
            m["metric"]: m["value"] for m in regression_scores(actual, predicted, scope)
        }
        if spec.prediction != "none":
            lo, hi = (
                np.array([x["lower"] for x in records]),
                np.array([x["upper"] for x in records]),
            )
            if (
                not np.isfinite(lo).all()
                or not np.isfinite(hi).all()
                or np.any(lo > hi)
                or report["empirical_coverage"]
                != float(np.mean((actual >= lo) & (actual <= hi)))
                or report["mean_width"] != float(np.mean(hi - lo))
            ):
                raise ProjectError("Predictive width/empirical coverage uyuşmuyor.")
    if {m["metric"]: m["value"] for m in e["metrics"]} != metric_values or any(
        m["scope"] != scope
        or m["n"] != len(ids)
        or m["direction"]
        != ("maximize" if m["metric"] in ("accuracy", "r2") else "minimize")
        for m in e["metrics"]
    ):
        raise ProjectError("Belirsizlik metric/kapsam/yön uyuşmuyor.")


def validate_source(store, run):
    """Parent verifies frozen memberships/actuals against the immutable snapshot; no fit."""
    import polars as pl

    from veri_ufku.modeling.baseline import numeric
    from veri_ufku.modeling.contracts import PreparationSpec
    from veri_ufku.modeling.validation import ValidationSpec

    dataset = next(
        d for d in store.state["datasets"] if d["version_id"] == run["dataset_version"]
    )
    columns = {c["id"]: c["name"] for c in dataset["import_metadata"]["columns"]}
    prep = run["preparation_spec"]
    names = ["__vu_row_id", columns[prep["target"]]] + [
        columns[prep[k]] for k in ("group", "time") if prep[k]
    ]
    frame = pl.read_parquet(
        store.path(dataset["snapshot_uri"]), columns=list(dict.fromkeys(names))
    )
    target = columns[prep["target"]]
    valid = frame[target].is_not_null()
    if frame[target].dtype.is_float():
        valid &= frame[target].is_finite()
    if frame.filter(~valid)["__vu_row_id"].to_list() != run["excluded_target_row_ids"]:
        raise ProjectError("Belirsizlik excluded target üyeliği source ile uyuşmuyor.")
    frame = frame.filter(valid)
    classification = prep["purpose"] == "classification"
    y = (
        np.array([str(v) for v in frame[target].to_list()])
        if classification
        else numeric(frame[target].to_list(), PreparationSpec.from_dict(prep)).ravel()
    )
    groups = (
        np.array(frame[columns[prep["group"]]].to_list(), dtype=object)
        if prep["group"]
        else None
    )
    times = None
    if prep["time"]:
        times = np.array(
            [
                v.timestamp()
                if isinstance(v, datetime) and v.tzinfo
                else v.replace(tzinfo=UTC).timestamp()
                if isinstance(v, datetime)
                else datetime(v.year, v.month, v.day, tzinfo=UTC).timestamp()
                if v
                else np.nan
                for v in frame[columns[prep["time"]]].to_list()
            ]
        )
    spec = ValidationSpec.from_dict(run["spec"])
    method, _, _ = spec.resolved(dict(spec=prep))
    ids = frame["__vu_row_id"].to_list()
    plan, outer = split_plan(
        ids,
        y,
        groups,
        times,
        spec,
        method,
        classification,
        run["dataset_version"],
        run["snapshot_fingerprint"],
        allow_missing_test_class=classification,
    )
    pools, inner = partitions(
        ids,
        y,
        groups,
        times,
        spec,
        method,
        classification,
        outer,
        run["dataset_version"],
        run["snapshot_fingerprint"],
    )
    if (
        plan != run["plan"]
        or inner != run["uncertainty"]["inner_plan"]
        or {k: sorted(ids[i] for i in v) for k, v in pools.items()}
        != run["uncertainty"]["membership"]
    ):
        raise ProjectError("Kalibrasyon source-bound group/time partition uyuşmuyor.")
    actual = {ids[i]: str(v) if classification else float(v) for i, v in enumerate(y)}
    if any(
        actual[r["row_id"]] != r["actual"]
        for r in run["evaluations"][0]["prediction_records"]
    ):
        raise ProjectError(
            "Belirsizlik evaluation hedefi source kayıtlarıyla uyuşmuyor."
        )
