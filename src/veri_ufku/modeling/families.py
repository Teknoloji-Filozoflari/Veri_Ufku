"""Closed CPU family adapters. Each child learns preprocessing only on its own rows."""

import json
import warnings

import numpy as np
from scipy import sparse
from sklearn.base import (
    BaseEstimator,
    ClassifierMixin,
    RegressorMixin,
    TransformerMixin,
)
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.linear_model import (
    ElasticNet,
    Lasso,
    LogisticRegression,
    Ridge,
    SGDClassifier,
    SGDRegressor,
)
from sklearn.model_selection import GroupKFold, KFold, StratifiedKFold
from sklearn.naive_bayes import GaussianNB, MultinomialNB
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.utils.metaestimators import available_if

from veri_ufku.modeling.contracts import PreparationSpec
from veri_ufku.modeling.family_contracts import (
    OPTIONAL_FAMILIES,
    SCALED_FAMILIES,
    FamilyOptions,
    support,
)
from veri_ufku.storage.project_model import ProjectError


class FamilyScope(BaseEstimator, TransformerMixin):
    """Identity outer step. Preprocessing belongs inside each model/OOF child."""

    def __init__(self, plan, spec, columns, max_cells=4000000):
        self.plan, self.spec, self.columns, self.max_cells = (
            plan,
            spec,
            columns,
            max_cells,
        )

    def fit(self, X, y=None):
        self.fit_row_ids_array_ = np.asarray(X["__vu_row_id"].to_list(), dtype=np.str_)
        self.summary_ = {
            "execution": "raw identity; every learner child fits its own preparation"
        }
        return self

    @property
    def fit_row_ids_(self):
        return self.fit_row_ids_array_.tolist()

    def transform(self, X):
        return X


class HGBArrayPreparation(BaseEstimator, TransformerMixin):
    """Safe replacement for sklearn's partial(check_array) numeric column callable."""

    def __init__(self, encoder, categorical_mask):
        self.encoder, self.categorical_mask = encoder, categorical_mask
        self.n_features_in_ = len(categorical_mask)

    def transform(self, X):
        values = np.asarray(X, dtype=float)
        mask = np.asarray(self.categorical_mask, dtype=bool)
        if values.ndim != 2 or values.shape[1] != len(mask) or np.isinf(values).any():
            raise ProjectError("HGB native feature schema geçersiz.")
        return np.column_stack(
            [self.encoder.transform(values[:, mask]), values[:, ~mask]]
        )


class FamilyPreparation(BaseEstimator, TransformerMixin):
    def __init__(self, method, options, spec, columns, plan, max_cells=4000000):
        (
            self.method,
            self.options,
            self.spec,
            self.columns,
            self.plan,
            self.max_cells,
        ) = method, options, spec, columns, plan, max_cells

    def fit(self, X, y=None):
        self.fit_row_ids_ = np.asarray(X["__vu_row_id"].to_list(), dtype=np.str_)
        self.steps_ = {}
        self.summary_ = {}
        self.feature_names_ = []
        self.categorical_mask_ = []
        self._execute(X, True)
        return self

    def transform(self, X):
        return self._execute(X, False)

    def _execute(self, X, fitting):
        from veri_ufku.modeling.baseline import numeric

        options = FamilyOptions.from_dict(self.options)
        native = self.method in ("hist_gradient", *OPTIONAL_FAMILIES)
        names = {c["id"]: c["name"] for c in self.columns}
        unsupported = {s["kind"] for s in self.plan["steps"]} - {
            "numeric",
            "impute_numeric",
            "impute_category",
            "encode_onehot",
            "encode_ordinal",
            "standard_scale",
            "no_scaling",
            "select_variance",
        }
        if unsupported:
            raise ProjectError(
                "Bu adapter taşınmış/ileri hazırlık adımını desteklemiyor; sessiz atlama yok."
            )
        ordinal = {
            s["input_column_ids"][0]: s["parameters"]["order"]
            for s in self.plan["steps"]
            if s["kind"] == "encode_ordinal"
        }
        categorical = {
            s["input_column_ids"][0]
            for s in self.plan["steps"]
            if s["kind"] in ("encode_onehot", "encode_ordinal")
        }
        if self.spec.missing_indicator or self.spec.numeric_imputation in (
            "knn",
            "iterative",
        ):
            raise ProjectError(
                "Family adapter simple imputation/variance selection/no indicator destekler; ileri hazırlık adımları kapalı."
            )
        if native and self.spec.selection != "none":
            raise ProjectError(
                "Native categorical variance selection desteklenmiyor; kategorik anlam korunmalı."
            )
        blocks = []
        if fitting:
            self.feature_names_ = []
            self.categorical_mask_ = []
        for ident in self.spec.features:
            values = X[names[ident]].to_list()
            is_cat = ident in categorical
            prefix = "f_" + ident.removeprefix("col:").replace("-", "")
            if is_cat:
                # Typed category keys prevent collisions such as int1/string1/missing.
                arr = np.asarray(
                    [
                        [
                            None
                            if v is None
                            else json.dumps(
                                [type(v).__name__, str(v)], ensure_ascii=False
                            )
                        ]
                        for v in values
                    ],
                    dtype=object,
                )
                if native:
                    if fitting:
                        vocabulary = sorted({v[0] for v in arr if v[0] is not None})
                        if not vocabulary or len(vocabulary) > 255:
                            raise ProjectError(
                                "Native categorical eğitim vocab 1–255 kategori olmalı."
                            )
                        self.steps_[ident] = vocabulary
                        self.summary_[ident] = dict(
                            kind="native_categorical",
                            categories=vocabulary,
                            unknown="missing",
                            missing="native; no mode imputation",
                            fit_n=len(X),
                            fit_scope="training_only",
                        )
                    mapping = {v: i for i, v in enumerate(self.steps_[ident])}
                    block = np.asarray(
                        [[mapping.get(v[0], np.nan)] for v in arr], dtype=float
                    )
                    if fitting:
                        self.feature_names_.append(prefix)
                        self.categorical_mask_.append(True)
                else:
                    if fitting:
                        if self.spec.categorical_imputation != "none":
                            if self.spec.categorical_imputation == "none":
                                raise ProjectError(
                                    "Eksik kategori: explicit imputation gerekli."
                                )
                            observed = [v[0] for v in arr if v[0] is not None]
                            if not observed:
                                raise ProjectError("Eğitim kategorisi tamamen eksik.")
                            fill = min(
                                set(observed), key=lambda v: (-observed.count(v), v)
                            )
                        else:
                            fill = None
                        filled = np.asarray(
                            [[fill if v[0] is None else v[0]] for v in arr],
                            dtype=object,
                        )
                        if ident in ordinal:
                            prototype = next((v for v in values if v is not None), None)
                            if prototype is None:
                                raise ProjectError("Ordinal training tamamen eksik.")
                            order = [
                                json.dumps(
                                    [type(prototype).__name__, str(v)],
                                    ensure_ascii=False,
                                )
                                for v in ordinal[ident]
                            ]
                            encoder = OrdinalEncoder(
                                categories=[order], handle_unknown="error"
                            )
                        else:
                            encoder = OneHotEncoder(
                                handle_unknown="ignore",
                                sparse_output=options.matrix == "sparse",
                            )
                        if len(set(v[0] for v in filled)) > 255:
                            raise ProjectError(
                                "One-hot eğitim vocab 255 kategori sınırını aşıyor."
                            )
                        encoder.fit(filled)
                        self.steps_[ident] = (fill, encoder)
                        self.summary_[ident] = dict(
                            kind="ordinal" if ident in ordinal else "onehot",
                            categories=encoder.categories_[0].tolist(),
                            fill=fill,
                            unknown="reject" if ident in ordinal else "all-zero",
                            fit_n=len(X),
                            fit_scope="training_only",
                        )
                    fill, encoder = self.steps_[ident]
                    filled = np.asarray(
                        [[fill if v[0] is None else v[0]] for v in arr], dtype=object
                    )
                    if any(v[0] is None for v in filled):
                        raise ProjectError(
                            "Yeni eksik kategori; eğitimde fill öğrenilmedi, sessiz doldurma yok."
                        )
                    block = encoder.transform(filled)
                    if fitting:
                        self.feature_names_.extend(
                            prefix + "__" + str(i) for i in range(block.shape[1])
                        )
                        self.categorical_mask_.extend([False] * block.shape[1])
            else:
                dtype = X.schema[names[ident]]
                if not dtype.is_numeric():
                    raise ProjectError(
                        "Faz48 numeric/category structured features; calendar/text native adapter kapalı."
                    )
                arr = numeric(values, self.spec)
                if native:
                    block = arr
                    if fitting:
                        self.summary_[ident] = dict(
                            kind="numeric_native_nan",
                            imputation="none; native missing",
                            scaling="none",
                            fit_n=len(X),
                            fit_scope="training_only",
                        )
                else:
                    if fitting:
                        if np.isnan(arr).all():
                            raise ProjectError("Eğitim ölçümü tamamen eksik.")
                        imputer = (
                            None
                            if self.spec.numeric_imputation == "none"
                            else SimpleImputer(
                                strategy=self.spec.numeric_imputation
                            ).fit(arr)
                        )
                        filled = imputer.transform(arr) if imputer else arr
                        if not np.isfinite(filled).all():
                            raise ProjectError(
                                "Eksik ölçüm: explicit imputation gerekli."
                            )
                        scale = (
                            options.scaling == "standard"
                            or options.scaling == "auto"
                            and self.method in SCALED_FAMILIES
                        )
                        if self.method == "multinomial_nb":
                            scale = False
                        scaler = (
                            StandardScaler(with_mean=options.matrix != "sparse").fit(
                                filled
                            )
                            if scale
                            else None
                        )
                        self.steps_[ident] = (imputer, scaler)
                        self.summary_[ident] = dict(
                            kind="numeric",
                            imputation=imputer.statistics_.tolist()
                            if imputer
                            else None,
                            mean=scaler.mean_.tolist() if scaler else None,
                            scale=scaler.scale_.tolist() if scaler else None,
                            center=bool(scaler and scaler.with_mean),
                            fit_n=len(X),
                            fit_scope="training_only",
                        )
                    imputer, scaler = self.steps_[ident]
                    block = imputer.transform(arr) if imputer else arr
                    block = scaler.transform(block) if scaler else block
                if fitting:
                    self.feature_names_.append(prefix)
                    self.categorical_mask_.append(False)
            blocks.append(
                sparse.csr_matrix(block) if options.matrix == "sparse" else block
            )
        result = (
            sparse.hstack(blocks, format="csr")
            if options.matrix == "sparse"
            else np.column_stack(blocks).astype(float)
        )
        cells = result.shape[0] * result.shape[1]
        if cells > self.max_cells or result.shape[1] > 256:
            raise ProjectError(
                "Temsil maliyeti 256 feature/dense-equivalent ComputeBudget sınırını aşıyor; implicit densification yok."
            )
        actual = result.data if sparse.issparse(result) else result
        if np.isinf(actual).any() or not native and np.isnan(actual).any():
            raise ProjectError("Dönüşüm sonlu değil.")
        if self.method == "multinomial_nb" and np.any(actual < 0):
            raise ProjectError("MultinomialNB non-negative özellik gerektirir.")
        if self.spec.selection == "variance":
            if fitting:
                self.selection_ = VarianceThreshold(0).fit(result)
                self.selection_inputs_ = list(self.feature_names_)
                mask = self.selection_.get_support()
                self.feature_names_ = [
                    v for v, keep in zip(self.feature_names_, mask) if keep
                ]
                self.categorical_mask_ = [
                    v for v, keep in zip(self.categorical_mask_, mask) if keep
                ]
                self.summary_["__selection__"] = dict(
                    kind="variance",
                    threshold=0,
                    fit_n=len(X),
                    fit_scope="training_only",
                    selected_names=self.feature_names_,
                )
            result = self.selection_.transform(result)
        return result


def native_estimator(method, purpose, options, seed, categorical_mask):
    o = FamilyOptions.from_dict(options)
    classification = purpose == "classification"
    if method == "elasticnet":
        return (
            LogisticRegression(
                C=o.C,
                l1_ratio=o.l1_ratio,
                solver="saga",
                max_iter=o.max_iter,
                random_state=seed,
            )
            if classification
            else ElasticNet(
                alpha=o.alpha,
                l1_ratio=o.l1_ratio,
                max_iter=o.max_iter,
                random_state=seed,
            )
        )
    if method == "lasso":
        return (
            LogisticRegression(
                C=o.C,
                l1_ratio=1.0,
                solver="saga",
                max_iter=o.max_iter,
                random_state=seed,
            )
            if classification
            else Lasso(alpha=o.alpha, max_iter=o.max_iter, random_state=seed)
        )
    if method == "sgd":
        return (
            SGDClassifier(
                loss="log_loss",
                penalty="elasticnet",
                alpha=o.alpha,
                l1_ratio=o.l1_ratio,
                max_iter=o.max_iter,
                tol=1e-4,
                random_state=seed,
            )
            if classification
            else SGDRegressor(
                penalty="elasticnet",
                alpha=o.alpha,
                l1_ratio=o.l1_ratio,
                max_iter=o.max_iter,
                tol=1e-4,
                random_state=seed,
            )
        )
    if method == "decision_tree":
        return (DecisionTreeClassifier if classification else DecisionTreeRegressor)(
            max_depth=o.depth, min_samples_leaf=2, random_state=seed
        )
    if method == "extra_trees":
        return (ExtraTreesClassifier if classification else ExtraTreesRegressor)(
            n_estimators=o.trees,
            max_depth=o.depth,
            min_samples_leaf=2,
            random_state=seed,
            n_jobs=1,
        )
    if method == "gradient_boosting":
        return (
            GradientBoostingClassifier if classification else GradientBoostingRegressor
        )(
            n_estimators=o.trees,
            max_depth=o.depth,
            learning_rate=o.learning_rate,
            random_state=seed,
        )
    if method == "hist_gradient":
        return (
            HistGradientBoostingClassifier
            if classification
            else HistGradientBoostingRegressor
        )(
            max_iter=o.trees,
            max_leaf_nodes=15,
            max_depth=o.depth,
            learning_rate=o.learning_rate,
            categorical_features=categorical_mask,
            early_stopping=False,
            random_state=seed,
        )
    if method == "svm":
        return (
            SVC(
                C=o.C,
                kernel=o.kernel,
                gamma=o.gamma,
                probability=False,
                max_iter=o.max_iter,
                random_state=seed,
            )
            if classification
            else SVR(C=o.C, kernel=o.kernel, gamma=o.gamma, max_iter=o.max_iter)
        )
    if method == "knn":
        return (KNeighborsClassifier if classification else KNeighborsRegressor)(
            n_neighbors=o.neighbors, algorithm="brute", n_jobs=1
        )
    if method == "gaussian_nb":
        return GaussianNB()
    if method == "multinomial_nb":
        return MultinomialNB(alpha=o.alpha)
    if method in OPTIONAL_FAMILIES:
        from veri_ufku.modeling.optional_families import estimator

        return estimator(method, purpose, o, seed, categorical_mask)
    raise ProjectError("Native model ailesi desteklenmiyor.")


class _FamilyBase(BaseEstimator):
    def __init__(
        self,
        method,
        options,
        spec,
        columns,
        plan,
        seed=42,
        max_cells=4000000,
        group_name="",
        structure="independent",
    ):
        (
            self.method,
            self.options,
            self.spec,
            self.columns,
            self.plan,
            self.seed,
            self.max_cells,
            self.group_name,
            self.structure,
        ) = method, options, spec, columns, plan, seed, max_cells, group_name, structure

    def _child(self, method, seed):
        return type(self)(
            method,
            self.options,
            self.spec,
            self.columns,
            self.plan,
            seed,
            self.max_cells,
            self.group_name,
            self.structure,
        )

    def fit(self, X, y):
        options = FamilyOptions.from_dict(self.options)
        if np.asarray(y).ndim != 1:
            raise ProjectError(
                "Application multioutput schema kapalı; single-target seçin."
            )
        classification = isinstance(self, FamilyClassifier)
        self.fit_row_ids_ = np.asarray(X["__vu_row_id"].to_list(), dtype=np.str_)
        self.classes_ = (
            np.asarray(sorted(set(y)), dtype=np.str_)
            if classification
            else np.asarray([], dtype=np.str_)
        )
        labels = {v: i for i, v in enumerate(self.classes_)}
        target = (
            np.asarray([labels[v] for v in y])
            if classification
            else np.asarray(y, dtype=float)
        )
        self.children_ = []
        self.oof_ = []
        if self.method in ("bagging", "voting", "stacking"):
            members = (
                ("decision_tree",) * 10
                if self.method == "bagging"
                else ("elasticnet", "decision_tree")
            )
            if self.method == "stacking":
                if self.structure == "group":
                    groups = X[self.group_name].to_numpy()
                    splits = list(
                        GroupKFold(n_splits=options.inner_folds).split(
                            np.zeros(len(X)), target, groups
                        )
                    )
                else:
                    splitter = (
                        StratifiedKFold(
                            options.inner_folds, shuffle=True, random_state=self.seed
                        )
                        if classification
                        else KFold(
                            options.inner_folds, shuffle=True, random_state=self.seed
                        )
                    )
                    splits = list(splitter.split(np.zeros(len(X)), target))
                meta = np.full(
                    (
                        len(X),
                        len(members) * (len(self.classes_) if classification else 1),
                    ),
                    np.nan,
                )
                for fold, (a, b) in enumerate(splits):
                    if classification and set(y[a]) != set(self.classes_):
                        raise ProjectError(
                            "Stacking inner training fold bazı sınıfları içermiyor."
                        )
                    parts = []
                    for method in members:
                        child = self._child(method, (self.seed + fold + 1) % 2**32).fit(
                            X[a.tolist()], y[a]
                        )
                        parts.append(
                            child._aligned_probability(X[b.tolist()], self.classes_)
                            if classification
                            else child.predict(X[b.tolist()]).reshape(-1, 1)
                        )
                    meta[b] = np.column_stack(parts)
                    self.oof_.append(
                        dict(
                            fold=fold,
                            fit_row_ids=X[a.tolist()]["__vu_row_id"].to_list(),
                            prediction_row_ids=X[b.tolist()]["__vu_row_id"].to_list(),
                        )
                    )
                if not np.isfinite(meta).all():
                    raise ProjectError(
                        "Stacking OOF coverage tam değil; in-sample fallback yok."
                    )
                self.meta_ = (
                    LogisticRegression(max_iter=5000, random_state=self.seed)
                    if classification
                    else Ridge(alpha=1.0)
                )
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    self.meta_.fit(meta, target)
                if any(
                    w.category.__name__ not in ("FutureWarning", "DeprecationWarning")
                    for w in caught
                ):
                    raise ProjectError("Stacking meta-model convergence başarısız.")
                self.meta_training_values_ = meta
                self.meta_training_row_ids_ = self.fit_row_ids_.copy()
            rng = np.random.default_rng(self.seed)
            for i, method in enumerate(members):
                indices = (
                    rng.integers(0, len(X), len(X))
                    if self.method == "bagging"
                    else np.arange(len(X))
                )
                self.children_.append(
                    self._child(method, (self.seed + i + 1) % 2**32).fit(
                        X[indices.tolist()], y[indices]
                    )
                )
            self.metadata_ = dict(
                method=self.method,
                fit_row_ids=self.fit_row_ids_.tolist(),
                ensemble_members=[c.method for c in self.children_],
                child_preprocessing=[c.metadata_ for c in self.children_],
                oof=self.oof_,
                meta_training_row_ids=self.fit_row_ids_.tolist()
                if self.method == "stacking"
                else [],
                meta_rule="OOF predictions only; no original features passthrough"
                if self.method == "stacking"
                else None,
            )
            return self
        self.preparation_ = FamilyPreparation(
            self.method,
            self.options,
            self.spec,
            self.columns,
            self.plan,
            self.max_cells,
        ).fit(X)
        values = self.preparation_.transform(X)
        self.estimator_ = native_estimator(
            self.method,
            "classification" if classification else "regression",
            self.options,
            self.seed,
            self.preparation_.categorical_mask_,
        )
        weights = None
        if options.weight_column:
            col = next(
                (c for c in self.columns if c["id"] == options.weight_column), None
            )
            if (
                not col
                or col["id"] in self.spec.features
                or col["id"] == self.spec.target
            ):
                raise ProjectError("Weight ayrı mevcut ColumnId olmalı.")
            series = X[col["name"]]
            if not series.dtype.is_numeric() or series.null_count():
                raise ProjectError("Weight eksiksiz numeric olmalı.")
            from veri_ufku.modeling.baseline import numeric

            weights = numeric(series.to_list(), self.spec).ravel()
            if (
                not np.isfinite(weights).all()
                or np.any(weights < 0)
                or weights.sum() <= 0
            ):
                raise ProjectError(
                    "Weight sonlu/non-negative ve toplam pozitif olmalı."
                )
        if classification and options.class_balance == "balanced":
            balanced = compute_sample_weight("balanced", target)
            weights = balanced if weights is None else weights * balanced
        if (
            classification
            and weights is not None
            and any(weights[target == i].sum() <= 0 for i in range(len(self.classes_)))
        ):
            raise ProjectError("Her eğitim sınıfı pozitif weight toplamı gerektirir.")
        if self.method == "knn" and options.neighbors > len(X):
            raise ProjectError("KNN komşu sayısı eğitim kayıtlarını aşıyor.")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self.estimator_.fit(
                values,
                target,
                **({"sample_weight": weights} if weights is not None else {}),
            )
        if self.method == "hist_gradient" and self.estimator_._preprocessor is not None:
            original = self.estimator_._preprocessor
            replacement = HGBArrayPreparation(
                original.named_transformers_["encoder"],
                self.preparation_.categorical_mask_,
            )
            if not np.array_equal(
                original.transform(values),
                replacement.transform(values),
                equal_nan=True,
            ):
                raise ProjectError(
                    "HGB native categorical order safe replacement uyuşmuyor."
                )
            self.estimator_._preprocessor = replacement
        serious = [
            w
            for w in caught
            if w.category.__name__ not in ("FutureWarning", "DeprecationWarning")
        ]
        if serious or getattr(self.estimator_, "fit_status_", 0) != 0:
            raise ProjectError(
                "Model convergence/numerical tanılama başarısız; güvenilir sonuç yayınlanmadı."
            )
        self.metadata_ = dict(
            method=self.method,
            fit_row_ids=self.fit_row_ids_.tolist(),
            feature_names=self.preparation_.feature_names_,
            categorical_mask=self.preparation_.categorical_mask_,
            preprocessing=self.preparation_.summary_,
            class_mapping=[dict(label=v, index=i) for i, v in enumerate(self.classes_)],
            matrix=options.matrix,
            weights="estimator fit only; preprocessing/evaluation unweighted"
            if weights is not None
            else "none",
            convergence="passed; native warnings guarded",
            iterations=np.asarray(getattr(self.estimator_, "n_iter_", [])).tolist(),
            support=support(
                self.method, "classification" if classification else "regression"
            ),
            backend_notices=sorted({w.category.__name__ for w in caught}),
        )
        if self.method not in OPTIONAL_FAMILIES:
            self.metadata_["native_parameters"] = {
                k: v.tolist() if isinstance(v, np.ndarray) else v
                for k, v in self.estimator_.get_params(deep=False).items()
            }
        return self

    def _aligned_probability(self, X, labels):
        probability = self.predict_proba(X)
        out = np.zeros((len(X), len(labels)))
        for i, label in enumerate(self.classes_):
            out[:, list(labels).index(label)] = probability[:, i]
        return out

    def predict(self, X):
        classification = isinstance(self, FamilyClassifier)
        if self.children_:
            if classification:
                encoded = np.argmax(self.predict_proba(X), axis=1)
            elif self.method == "stacking":
                encoded = self.meta_.predict(
                    np.column_stack([c.predict(X) for c in self.children_])
                )
            else:
                encoded = np.mean([c.predict(X) for c in self.children_], axis=0)
        else:
            encoded = self.estimator_.predict(self.preparation_.transform(X))
        return (
            self.classes_[np.asarray(encoded, dtype=int)]
            if classification
            else np.asarray(encoded, dtype=float)
        )

    @available_if(
        lambda self: isinstance(self, FamilyClassifier) and self.method != "svm"
    )
    def predict_proba(self, X):
        if self.children_:
            parts = [c._aligned_probability(X, self.classes_) for c in self.children_]
            return (
                self.meta_.predict_proba(np.column_stack(parts))
                if self.method == "stacking"
                else np.mean(parts, axis=0)
            )
        return self.estimator_.predict_proba(self.preparation_.transform(X))


class FamilyRegressor(RegressorMixin, _FamilyBase):
    pass


class FamilyClassifier(ClassifierMixin, _FamilyBase):
    pass


def validate_estimator(model, card):
    """Closed tree validation after skops deserialization; no incoming trust expansion."""
    if (
        type(model) not in (FamilyClassifier, FamilyRegressor)
        or type(model.spec) is not PreparationSpec
    ):
        raise ProjectError("Kapalı family model şeması geçersiz.")
    if (
        type(model.seed) is not int
        or not 0 <= model.seed < 2**32
        or model.method != card["candidate_selection"]["selected"]
        or model.options
        != card["candidate_selection"]["parameters"].get("family_options")
    ):
        raise ProjectError("Family source/options/seed sözleşmesi geçersiz.")
    FamilyOptions.from_dict(model.options)
    if (
        model.spec.data() != card["preparation_spec"]
        or model.columns != card["columns"]
        or model.plan != card["preprocessing"]
        or model.fit_row_ids_.tolist() != card["fit_row_ids"]
    ):
        raise ProjectError("Family model source/feature/fit sözleşmesi uyuşmuyor.")

    def check(child):
        if type(child) not in (FamilyClassifier, FamilyRegressor):
            raise ProjectError("Bilinmeyen ensemble child engellendi.")
        if (
            child.spec.data() != model.spec.data()
            or child.columns != model.columns
            or child.plan != model.plan
            or child.options != model.options
            or type(child.seed) is not int
            or not 0 <= child.seed < 2**32
        ):
            raise ProjectError("Ensemble child source/options kapsamı geçersiz.")
        if child.children_:
            expected_members = (
                ["decision_tree"] * 10
                if child.method == "bagging"
                else ["elasticnet", "decision_tree"]
                if child.method in ("voting", "stacking")
                else []
            )
            if [c.method for c in child.children_] != expected_members:
                raise ProjectError("Ensemble üyelik sözleşmesi değişmiş.")
            source_ids = set(child.fit_row_ids_)
            for c in child.children_:
                if not set(c.fit_row_ids_) <= source_ids or (
                    child.method != "bagging" and set(c.fit_row_ids_) != source_ids
                ):
                    raise ProjectError("Ensemble child fit kapsamı geçersiz.")
            for c in child.children_:
                check(c)
            if child.method == "stacking" and type(child.meta_) not in (
                Ridge,
                LogisticRegression,
            ):
                raise ProjectError("Stacking meta-model kapalı değil.")
            if child.method == "stacking":
                classification = isinstance(child, FamilyClassifier)
                expected_meta = (
                    LogisticRegression(max_iter=5000, random_state=child.seed)
                    if classification
                    else Ridge(alpha=1.0)
                )
                rows = child.meta_training_row_ids_.tolist()
                width = 2 * (len(child.classes_) if classification else 1)
                predicted = []
                for fold in child.oof_:
                    train = set(fold["fit_row_ids"])
                    held = set(fold["prediction_row_ids"])
                    if train & held or train | held != source_ids:
                        raise ProjectError(
                            "Stacking OOF fit/prediction kapsamı geçersiz."
                        )
                    predicted.extend(fold["prediction_row_ids"])
                if (
                    rows != child.fit_row_ids_.tolist()
                    or len(child.oof_)
                    != FamilyOptions.from_dict(child.options).inner_folds
                    or len(predicted) != len(source_ids)
                    or set(predicted) != source_ids
                    or child.meta_training_values_.shape != (len(rows), width)
                    or not np.isfinite(child.meta_training_values_).all()
                    or child.meta_.get_params(deep=False)
                    != expected_meta.get_params(deep=False)
                ):
                    raise ProjectError("Stacking OOF/meta-model sözleşmesi geçersiz.")
        else:
            expected = native_estimator(
                child.method,
                "classification"
                if isinstance(child, FamilyClassifier)
                else "regression",
                child.options,
                child.seed,
                child.preparation_.categorical_mask_,
            )
            if (
                child.method == "hist_gradient"
                and child.estimator_._preprocessor is not None
                and (
                    type(child.estimator_._preprocessor) is not HGBArrayPreparation
                    or type(child.estimator_._preprocessor.encoder)
                    is not OrdinalEncoder
                    or child.estimator_._preprocessor.categorical_mask
                    != child.preparation_.categorical_mask_
                )
            ):
                raise ProjectError("HGB safe numeric/category partition geçersiz.")
            if (
                type(child.estimator_) is not type(expected)
                or type(child.preparation_) is not FamilyPreparation
            ):
                raise ProjectError("Family native estimator/preparation kapalı değil.")
            if (
                child.preparation_.method != child.method
                or child.preparation_.options != child.options
                or child.preparation_.spec.data() != child.spec.data()
                or child.preparation_.columns != child.columns
                or child.preparation_.plan != child.plan
            ):
                raise ProjectError(
                    "Family preprocessing kaynak/parametre bağı geçersiz."
                )
            actual = child.estimator_.get_params(deep=False)
            if child.spec.selection == "variance" and (
                type(child.preparation_.selection_) is not VarianceThreshold
                or child.preparation_.selection_.threshold != 0
                or [
                    v
                    for v, keep in zip(
                        child.preparation_.selection_inputs_,
                        child.preparation_.selection_.get_support(),
                    )
                    if keep
                ]
                != child.preparation_.feature_names_
            ):
                raise ProjectError("Family variance selection kapsamı geçersiz.")
            expected_params = expected.get_params(deep=False)
            for name, value in expected_params.items():
                a = actual.get(name)
                if isinstance(a, np.ndarray) or isinstance(value, np.ndarray):
                    same = np.array_equal(a, value, equal_nan=True)
                else:
                    same = a == value
                if not same:
                    raise ProjectError("Family native parametre desteği değişmiş.")
            for op in child.preparation_.steps_.values():
                if type(op) is list:
                    if any(type(v) is not str for v in op):
                        raise ProjectError("Native categorical vocabulary geçersiz.")
                elif type(op) is tuple:
                    if any(
                        v is not None
                        and type(v)
                        not in (
                            str,
                            SimpleImputer,
                            StandardScaler,
                            OneHotEncoder,
                            OrdinalEncoder,
                        )
                        for v in op
                    ):
                        raise ProjectError("Bilinmeyen transform engellendi.")
                else:
                    raise ProjectError("Bilinmeyen preparation state engellendi.")

    check(model)
