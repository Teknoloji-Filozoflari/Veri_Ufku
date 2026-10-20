"""Lazy CPU optional adapters. No downloads, GPU, implicit encoding or unsafe save."""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator

from veri_ufku.modeling.family_contracts import OPTIONAL_FAMILIES, available
from veri_ufku.storage.project_model import ProjectError


class OptionalNative(BaseEstimator):
    def __init__(self, method, purpose, options, seed, categorical_mask):
        self.method, self.purpose, self.options, self.seed, self.categorical_mask = (
            method,
            purpose,
            options,
            seed,
            categorical_mask,
        )

    def _frame(self, X, fitting=False):
        if hasattr(X, "toarray"):
            raise ProjectError(
                "Optional native categorical adapter dense-only; implicit densification yok."
            )
        values = np.asarray(X, dtype=float)
        frame = pd.DataFrame(values, columns=[f"f_{i}" for i in range(values.shape[1])])
        if fitting:
            self.category_ranges_ = {}
        for i, is_cat in enumerate(self.categorical_mask):
            if not is_cat:
                continue
            if fitting:
                self.category_ranges_[i] = list(range(int(np.nanmax(values[:, i])) + 1))
            if self.method == "catboost":
                frame[frame.columns[i]] = (
                    frame.iloc[:, i]
                    .map(
                        lambda v: (
                            "__native_missing__"
                            if pd.isna(v)
                            else "category_" + str(int(v))
                        )
                    )
                    .astype(object)
                )
            else:
                frame[frame.columns[i]] = pd.Categorical(
                    frame.iloc[:, i], categories=self.category_ranges_[i]
                )
        return frame

    def fit(self, X, y, sample_weight=None):
        ready, reason = available(self.method)
        if not ready:
            raise ProjectError(reason)
        o = self.options
        classification = self.purpose == "classification"
        if self.method == "xgboost":
            from xgboost import XGBClassifier, XGBRegressor

            self.model_ = (XGBClassifier if classification else XGBRegressor)(
                n_estimators=o.trees,
                max_depth=o.depth,
                learning_rate=o.learning_rate,
                random_state=self.seed,
                n_jobs=1,
                tree_method="hist",
                device="cpu",
                enable_categorical=True,
                verbosity=0,
            )
        elif self.method == "lightgbm":
            from lightgbm import LGBMClassifier, LGBMRegressor

            self.model_ = (LGBMClassifier if classification else LGBMRegressor)(
                n_estimators=o.trees,
                max_depth=o.depth,
                learning_rate=o.learning_rate,
                random_state=self.seed,
                n_jobs=1,
                device_type="cpu",
                verbosity=-1,
            )
        elif self.method == "catboost":
            from catboost import CatBoostClassifier, CatBoostRegressor

            self.model_ = (CatBoostClassifier if classification else CatBoostRegressor)(
                iterations=o.trees,
                depth=o.depth,
                learning_rate=o.learning_rate,
                random_seed=self.seed,
                thread_count=1,
                task_type="CPU",
                verbose=False,
                allow_writing_files=False,
                cat_features=[i for i, c in enumerate(self.categorical_mask) if c],
            )
        else:
            raise ProjectError("Optional model bilinmiyor.")
        self.model_.fit(
            self._frame(X, True),
            y,
            **({"sample_weight": sample_weight} if sample_weight is not None else {}),
        )
        return self

    def predict(self, X):
        return np.asarray(self.model_.predict(self._frame(X))).reshape(-1)

    def predict_proba(self, X):
        return self.model_.predict_proba(self._frame(X))


def estimator(method, purpose, options, seed, categorical_mask):
    return OptionalNative(method, purpose, options, seed, categorical_mask)


def ranking_estimator(spec, options, seed):
    """Only reachable with validated RankingSpec; ordinary classifier objective rejected."""
    if spec.method not in OPTIONAL_FAMILIES:
        raise ProjectError("Ranking optional backend gerektirir.")
    ready, reason = available(spec.method)
    if not ready:
        raise ProjectError(reason)
    if spec.method == "xgboost":
        from xgboost import XGBRanker

        return XGBRanker(
            objective="rank:ndcg",
            n_estimators=options.trees,
            max_depth=options.depth,
            random_state=seed,
            n_jobs=1,
            device="cpu",
            tree_method="hist",
        )
    if spec.method == "lightgbm":
        from lightgbm import LGBMRanker

        return LGBMRanker(
            objective="lambdarank",
            n_estimators=options.trees,
            max_depth=options.depth,
            random_state=seed,
            n_jobs=1,
            device_type="cpu",
            verbosity=-1,
        )
    from catboost import CatBoostRanker

    return CatBoostRanker(
        loss_function="YetiRank:mode=NDCG",
        iterations=options.trees,
        depth=options.depth,
        random_seed=seed,
        thread_count=1,
        task_type="CPU",
        verbose=False,
        allow_writing_files=False,
    )


def ranking_schema(spec, frame, columns, train_query_ids, evaluation_query_ids):
    spec.validate(columns)
    names = {c["id"]: c["name"] for c in columns}
    relevance = frame[names[spec.relevance]]
    query = frame[names[spec.query_group]]
    if (
        relevance.null_count()
        or not relevance.dtype.is_numeric()
        or query.null_count()
        or frame["__vu_row_id"].n_unique() != len(frame)
    ):
        raise ProjectError("Ranking relevance/query/RowId şeması geçersiz.")
    values = relevance.to_numpy()
    if (
        not np.isfinite(values).all()
        or np.any(values < 0)
        or np.any(values != np.floor(values))
    ):
        raise ProjectError("NDCG relevance non-negative integer olmalı.")
    if set(train_query_ids) & set(evaluation_query_ids) or not set(
        train_query_ids
    ) | set(evaluation_query_ids) <= set(query.to_list()):
        raise ProjectError("Ranking query grupları ayrık ve kaynakta mevcut olmalı.")
    return dict(
        schema="RankingSpec/v1",
        objective=spec.objective,
        query_group=spec.query_group,
        relevance=spec.relevance,
        train_query_ids=list(train_query_ids),
        evaluation_query_ids=list(evaluation_query_ids),
        row_ids=frame["__vu_row_id"].to_list(),
        fit_policy="whole query groups; separate NDCG evaluator, no ordinary classification",
    )
