"""Separate target schemas; no implicit conversion of ordinal/PU labels to regression."""

import math
from dataclasses import asdict, dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, hamming_loss
from sklearn.multioutput import MultiOutputClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.semi_supervised import LabelPropagation

from veri_ufku.storage.project_model import ProjectError


@dataclass(frozen=True)
class TargetSpec:
    task: str
    order: tuple = ()
    transductive: bool = False

    def validate(self):
        if (
            self.task
            not in ("multilabel", "multioutput", "ordinal", "pu", "semisupervised")
            or type(self.transductive) is not bool
        ):
            raise ProjectError("Özel hedef kapalı şema geçersiz.")
        if self.task == "ordinal" and (
            len(self.order) < 2
            or len(set(self.order)) != len(self.order)
            or not all(isinstance(v, str) for v in self.order)
        ):
            raise ProjectError(
                "Ordinal açık, unique kategori sırası gerektirir; numeric regression seçilmez."
            )
        if self.transductive and self.task != "semisupervised":
            raise ProjectError("Transductive setting yalnız label propagation için.")
        return self


def evaluate(spec, x_train, y_train, x_eval, y_eval, *, unlabeled=None):
    """Bounded development-only evaluation. Caller owns split/identity provenance.

    This low-level adapter does NOT claim a GUI pipeline, persistence or final test.
    """
    spec.validate()
    if spec.task == "pu":
        raise ProjectError(
            "PU unavailable: unlabeled negatif değildir; class-prior/selection assumptions doğrulanmış backend yok."
        )
    a, b = np.asarray(x_train, dtype=float), np.asarray(x_eval, dtype=float)
    y, z = np.asarray(y_train), np.asarray(y_eval)
    if (
        a.ndim != 2
        or b.ndim != 2
        or a.shape[1] != b.shape[1]
        or not 1 <= a.shape[1] <= 16
        or not 2 <= len(a) <= 256
        or not 1 <= len(b) <= 256
        or not np.isfinite(a).all()
        or not np.isfinite(b).all()
        or len(y) != len(a)
        or len(z) != len(b)
    ):
        raise ProjectError("Özel hedef bounded finite train/eval şeması geçersiz.")
    scaler = StandardScaler().fit(a)
    train, ev = scaler.transform(a), scaler.transform(b)
    report = dict(
        recipe={**asdict(spec), "order": list(spec.order)},
        preprocessing=dict(
            kind="StandardScaler", mean=scaler.mean_.tolist(), fit="train only"
        ),
        fit_scope="training rows only",
        metrics={},
        warnings=[],
        safe_persistence=False,
    )
    if spec.task == "multilabel":
        if (
            y.ndim != 2
            or z.ndim != 2
            or y.shape[1] != z.shape[1]
            or not 2 <= y.shape[1] <= 8
            or not np.isin(y, [0, 1]).all()
            or not np.isin(z, [0, 1]).all()
            or any(len(np.unique(y[:, i])) != 2 for i in range(y.shape[1]))
        ):
            raise ProjectError(
                "Multilabel binary indicator2–8 columns; each training label needs both classes."
            )
        pred = (
            MultiOutputClassifier(LogisticRegression(max_iter=200))
            .fit(train, y)
            .predict(ev)
        )
        report["metrics"] = dict(
            hamming_loss=float(hamming_loss(z, pred)),
            subset_accuracy=float(accuracy_score(z, pred)),
        )
    elif spec.task == "multioutput":
        if (
            y.ndim != 2
            or z.ndim != 2
            or y.shape[1] != z.shape[1]
            or not 2 <= y.shape[1] <= 8
            or not np.issubdtype(y.dtype, np.number)
            or not np.issubdtype(z.dtype, np.number)
            or not np.isfinite(y).all()
            or not np.isfinite(z).all()
        ):
            raise ProjectError(
                "Multioutput finite numeric2–8 target columns gerektirir."
            )
        pred = Ridge(alpha=1).fit(train, y).predict(ev)
        report["metrics"] = dict(
            rmse_per_target=np.sqrt(np.mean((z - pred) ** 2, axis=0)).tolist()
        )
        report["warnings"].append(
            "Per-target units retained; no aggregate across incomparable units."
        )
    elif spec.task == "ordinal":
        if (
            y.ndim != 1
            or z.ndim != 1
            or not set(y) <= set(spec.order)
            or not set(z) <= set(spec.order)
            or len(np.unique(y)) < 2
        ):
            raise ProjectError("Ordinal labels açık sıra içinde olmalı.")
        # Nominal probabilities plus ordinal median Bayes decision for absolute rank loss.
        model = LogisticRegression(max_iter=200).fit(train, y)
        proba = model.predict_proba(ev)
        p = np.zeros((len(ev), len(spec.order)))
        for i, c in enumerate(model.classes_):
            p[:, spec.order.index(c)] = proba[:, i]
        indices = np.argmax(np.cumsum(p, axis=1) >= 0.5, axis=1)
        pred = np.asarray(spec.order)[indices]
        report["metrics"] = dict(
            mean_absolute_rank_error=float(
                np.mean(
                    np.abs(
                        [
                            spec.order.index(v) - int(k)
                            for v, k in zip(z, indices, strict=True)
                        ]
                    )
                )
            )
        )
        report["warnings"].append(
            "Nominal logistic probabilities with ordinal median decision; not proportional-odds model, not numeric regression. Rank gaps are a loss assumption."
        )
    else:
        if (
            y.ndim != 1
            or z.ndim != 1
            or not np.isin(y, [-1, 0, 1]).all()
            or not np.isin(z, [0, 1]).all()
            or set(y[y != -1]) != {0, 1}
        ):
            raise ProjectError(
                "Semi-supervised labels {-1 unlabeled,0,1}; eval true labels0/1."
            )
        pool = (
            np.asarray(unlabeled, dtype=float)
            if unlabeled is not None
            else np.empty((0, a.shape[1]))
        )
        if (
            pool.ndim != 2
            or pool.shape[1] != a.shape[1]
            or len(pool) > 128
            or not np.isfinite(pool).all()
        ):
            raise ProjectError("Unlabeled training pool bounded finite olmalı.")
        fit = np.concatenate(
            [
                train,
                scaler.transform(pool) if len(pool) else pool,
                *([ev] if spec.transductive else []),
            ]
        )
        labels = np.concatenate(
            [y, np.full(len(pool) + (len(ev) if spec.transductive else 0), -1)]
        )
        model = LabelPropagation(kernel="rbf", gamma=1, max_iter=200).fit(fit, labels)
        pred = (
            model.transduction_[-len(ev) :] if spec.transductive else model.predict(ev)
        )
        report["metrics"] = dict(accuracy=float(accuracy_score(z, pred)))
        report["fit_scope"] = (
            "train + unlabeled + eval FEATURES; transductive, no eval labels"
            if spec.transductive
            else "train + unlabeled training pool; eval graph excluded"
        )
        report["warnings"].append(
            "Graph smoothness/cluster assumptions; transductive score is not independent inductive test performance."
        )
        report["converged"] = bool(model.n_iter_ < model.max_iter)
    if any(
        not math.isfinite(v) for v in report["metrics"].values() if isinstance(v, float)
    ):
        raise ProjectError("Özel hedef nonfinite metric.")
    report["predictions"] = pred.tolist()
    return report
