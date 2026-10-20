"""Training-only blueprint execution and Dummy baselines; JSON results only."""

import importlib.metadata
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import IterativeImputer, KNNImputer, SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from veri_ufku.analytics.dataset import checked
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.contracts import PreparationSpec
from veri_ufku.modeling.preparation import calculate as prepare
from veri_ufku.modeling.validation import ValidationSpec, digest, split_plan
from veri_ufku.storage.project_model import ProjectError, uid


def numeric(values, policy):
    result = []
    for value in values:
        if value is None:
            result.append(np.nan)
            continue
        converted = float(value)
        if not math.isfinite(converted):
            if policy.invalid_numeric == "reject":
                raise ProjectError("Sonlu olmayan sayısal özellik reddedildi.")
            converted = np.nan
        elif policy.precision == "reject" and converted != value:
            raise ProjectError(
                "Float64 hassasiyet kaybı; yaklaşık dönüşüm için açık seçim gerekir."
            )
        result.append(converted)
    return np.array(result, dtype=float).reshape(-1, 1)


class FoldPreparation(BaseEstimator, TransformerMixin):
    @property
    def fit_row_ids_(self):
        # Keep the public/card contract as a list, but serialize the fitted
        # membership as one safe ndarray instead of thousands of skops nodes.
        if "fit_row_ids_array_" in self.__dict__:
            return self.fit_row_ids_array_.tolist()
        return self.__dict__["fit_row_ids_"]  # Earlier v1 packages.

    @fit_row_ids_.setter
    def fit_row_ids_(self, values):
        self.fit_row_ids_array_ = np.asarray(values, dtype=np.str_)

    def __init__(self, plan, spec, columns, max_cells=4000000):
        self.plan, self.spec, self.columns, self.max_cells = (
            plan,
            spec,
            columns,
            max_cells,
        )

    def fit(self, X, y=None):
        self.fit_row_ids_ = X["__vu_row_id"].to_list()
        self.steps_ = {}
        self.summary_ = {}
        self._execute(X, True)
        return self

    def transform(self, X):
        return self._execute(X, False)

    def _execute(self, X, fitting):
        blocks = {}
        names = {c["id"]: c["name"] for c in self.columns}
        for i, step in enumerate(self.plan["steps"]):
            kind, params = step["kind"], step["parameters"]
            ids = step["input_column_ids"]
            if kind == "missing_indicator":
                for ident in ids:
                    flag = X[names[ident]].is_null().to_numpy()
                    if X.schema[names[ident]].is_float():
                        flag = (
                            flag
                            | ~X[names[ident]].is_finite().fill_null(False).to_numpy()
                        )
                    blocks[ident] = np.column_stack([blocks[ident], flag.astype(float)])
                continue
            if kind == "impute_joint":
                widths = [blocks[ident].shape[1] for ident in ids]
                arr = np.column_stack([blocks[ident] for ident in ids])
                if (
                    arr.size > self.max_cells
                    or params["strategy"] == "knn"
                    and len(X) > 5000
                ):
                    raise ProjectError(
                        "Çok değişkenli imputasyon bütçesi aşıldı; KNN en fazla5000 eğitim kaydı."
                    )
                key = str(i)
                if (
                    params["strategy"] == "knn"
                    and len(X) * (len(X) if fitting else len(self.steps_[key]._fit_X))
                    > self.max_cells
                ):
                    raise ProjectError(
                        "KNN çift uzaklık matrisi bellek bütçesini aşıyor; açık özellik/satır daraltma gerekli."
                    )
                if fitting:
                    if np.isnan(arr).all(axis=0).any():
                        raise ProjectError(
                            "Eğitim katındaki özellik tamamen eksik; fold reddedildi."
                        )
                    op = (
                        KNNImputer(n_neighbors=params["neighbors"])
                        if params["strategy"] == "knn"
                        else IterativeImputer(
                            max_iter=params["iterations"],
                            random_state=params["seed"],
                            sample_posterior=False,
                        )
                    )
                    self.steps_[key] = op.fit(arr)
                    self.summary_[key] = dict(
                        kind=kind,
                        strategy=params["strategy"],
                        seed=params["seed"],
                        fit_scope="training_fold",
                        fit_n=len(X),
                    )
                filled = self.steps_[key].transform(arr)
                for ident, block in zip(
                    ids, np.split(filled, np.cumsum(widths)[:-1], axis=1)
                ):
                    blocks[ident] = block
                continue
            if kind == "select_variance":
                continue
            ident = ids[0]
            if kind in ("numeric", "calendar"):
                raw = X[names[ident]].to_list()
                if kind == "calendar":
                    blocks[ident] = np.array(
                        [
                            [v.year, v.month, v.weekday()]
                            if v is not None
                            else [np.nan] * 3
                            for v in raw
                        ],
                        dtype=float,
                    )
                else:
                    blocks[ident] = numeric(raw, self.spec)
            elif kind == "outlier_iqr_mark":
                for ident in ids:
                    raw = numeric(X[names[ident]].to_list(), self.spec)
                    key = str(i) + ":" + ident
                    if fitting:
                        observed = raw[np.isfinite(raw)]
                        if len(observed) < 4:
                            raise ProjectError(
                                "IQR eğitim katında en az4 sonlu kayıt ister."
                            )
                        q1, q3 = np.quantile(observed, [0.25, 0.75], method="linear")
                        m = float(params["multiplier"])
                        self.steps_[key] = (q1 - m * (q3 - q1), q3 + m * (q3 - q1))
                        self.summary_[key] = dict(
                            kind=kind, thresholds=list(self.steps_[key])
                        )
                    low, high = self.steps_[key]
                    flag = ((raw < low) | (raw > high)).astype(float)
                    blocks[ident] = np.column_stack([blocks[ident], flag])
            else:
                if ident not in blocks:
                    # Preserve categorical type identity without mixing numbers and strings.
                    blocks[ident] = np.array(
                        [
                            [
                                np.nan
                                if v is None
                                or isinstance(v, float)
                                and not math.isfinite(v)
                                else str(v)
                            ]
                            for v in X[names[ident]].to_list()
                        ],
                        dtype=object,
                    )
                arr = blocks[ident]
                key = str(i)
                if kind == "no_scaling":
                    continue
                if fitting:
                    if kind.startswith("impute_"):
                        if any(
                            all(
                                v is None or isinstance(v, float) and math.isnan(v)
                                for v in arr[:, j]
                            )
                            for j in range(arr.shape[1])
                        ):
                            raise ProjectError(
                                "Eğitim katındaki özellik tamamen eksik; fold reddedildi."
                            )
                        op = SimpleImputer(strategy=params["strategy"])
                    elif kind == "encode_onehot":
                        op = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
                        if (
                            len(set(str(v) for v in arr[:, 0])) * len(X)
                            > self.max_cells
                        ):
                            raise ProjectError(
                                "One-hot eğitim boyutu/bellek bütçesini aşıyor; sessiz daraltma yok."
                            )
                    elif kind == "encode_ordinal":
                        op = OrdinalEncoder(
                            categories=[[str(v) for v in params["order"]]],
                            handle_unknown="error",
                        )
                    elif kind == "standard_scale":
                        op = StandardScaler()
                    else:
                        raise ProjectError(
                            "Hazırlama adımı bu baseline protokolünde desteklenmiyor: "
                            + kind
                        )
                    self.steps_[key] = op.fit(arr)
                    self.summary_[key] = dict(
                        kind=kind,
                        **(
                            {"statistics": op.statistics_.tolist()}
                            if hasattr(op, "statistics_")
                            else {}
                        ),
                        **(
                            {"categories": [v.tolist() for v in op.categories_]}
                            if hasattr(op, "categories_")
                            else {}
                        ),
                        **(
                            {"mean": op.mean_.tolist(), "scale": op.scale_.tolist()}
                            if hasattr(op, "mean_")
                            else {}
                        ),
                    )
                op = self.steps_[key]
                if (
                    kind == "encode_onehot"
                    and len(X) * sum(len(c) for c in op.categories_) > self.max_cells
                ):
                    raise ProjectError("Dönüşüm boyutu/bellek bütçesini aşıyor.")
                blocks[ident] = op.transform(arr)
        result = np.column_stack([blocks[i] for i in self.spec.features]).astype(float)
        if result.size > self.max_cells or not np.isfinite(result).all():
            raise ProjectError(
                "Fold dönüşümü eksik/sonlu olmayan veya bütçeyi aşan çıktı üretti."
            )
        if self.spec.selection == "variance":
            if fitting:
                self.selection_ = VarianceThreshold(0).fit(result)
                self.summary_["selection"] = dict(
                    mask=self.selection_.get_support().tolist(),
                    variances=self.selection_.variances_.tolist(),
                )
            result = self.selection_.transform(result)
        return result


def pipeline(preparation, strategy, seed, max_cells):
    spec = PreparationSpec.from_dict(preparation["spec"])
    dummy = (
        DummyRegressor(strategy=strategy)
        if spec.purpose == "regression"
        else DummyClassifier(strategy=strategy, random_state=seed)
    )
    if spec.text is not None:
        from veri_ufku.analytics.text import TextPreparation

        return Pipeline(
            [
                ("prepare", TextPreparation(spec.text, preparation["columns"])),
                ("baseline", dummy),
            ]
        )
    return Pipeline(
        [
            (
                "prepare",
                FoldPreparation(
                    preparation["plan"], spec, preparation["columns"], max_cells
                ),
            ),
            ("baseline", dummy),
        ]
    )


def scores(y, pred, classification, scope):
    values = (
        [
            ("accuracy", accuracy_score(y, pred), "maximize"),
            ("balanced_accuracy", balanced_accuracy_score(y, pred), "maximize"),
            (
                "f1_macro",
                f1_score(y, pred, average="macro", zero_division=0),
                "maximize",
            ),
        ]
        if classification
        else [
            ("mae", mean_absolute_error(y, pred), "minimize"),
            ("rmse", math.sqrt(mean_squared_error(y, pred)), "minimize"),
        ]
    )
    return [
        dict(
            metric=k,
            value=float(v),
            direction=d,
            scope=scope,
            n=len(y),
            status="valid",
            coverage="all eligible records in this evaluation partition",
            averaging="macro"
            if k in ("balanced_accuracy", "f1_macro")
            else "per_record",
        )
        for k, v, d in values
    ]


def calculate(request, parameters, workspace, control=None):
    job_started = time.monotonic()
    control = control or Control()
    control.check()
    request = dict(request, data_access_at=datetime.now(UTC).isoformat())
    p = request["preparation"]
    spec = ValidationSpec.from_dict(parameters)
    method, strategy, reason = spec.resolved(p)
    # Recompute history and blueprint from immutable source; a supplied plan is never trusted.
    fresh = prepare(request, p["spec"], workspace, control)
    if fresh["blockers"]:
        raise ProjectError(
            "Hazırlık engellerini çözün: "
            + "; ".join(
                r["reason"] for r in fresh["risks"] if r["severity"] == "blocker"
            )
        )
    if fresh["spec"] != p["spec"] or {
        k: v for k, v in fresh["plan"].items() if k != "version_id"
    } != {k: v for k, v in p["plan"].items() if k != "version_id"}:
        raise ProjectError("Hazırlama pipeline tarifi güncel kaynakla uyuşmuyor.")
    p = dict(fresh, plan=p["plan"], columns=request["columns"])
    row_name = request.get("row_id_column", "__vu_row_id")
    names = {c["id"]: c["name"] for c in request["columns"]}
    selected = list(
        dict.fromkeys(
            [row_name]
            + [names[c] for c in p["spec"]["features"]]
            + [names[p["spec"]["target"]]]
            + [names[p["spec"][k]] for k in ("group", "time") if p["spec"][k]]
        )
    )
    family_config = request.get("regression") or request.get("classification") or {}
    if family_config.get("family_options", {}).get("weight_column"):
        ident = family_config["family_options"]["weight_column"]
        if ident not in names:
            raise ProjectError("Weight ColumnId mevcut olmalı.")
        selected = list(dict.fromkeys(selected + [names[ident]]))
    frame = pl.read_parquet(request["path"], columns=selected)
    if row_name not in frame.columns:
        raise ProjectError("Kalıcı RowId sütunu bulunamadı.")
    target = names[p["spec"]["target"]]
    valid = frame[target].is_not_null()
    if frame[target].dtype.is_float():
        valid &= frame[target].is_finite()
    excluded = frame.filter(~valid)[row_name].to_list()
    frame = frame.filter(valid)
    classification = p["spec"]["purpose"] == "classification"
    y = (
        np.array([str(v) for v in frame[target].to_list()])
        if classification
        else numeric(
            frame[target].to_list(), PreparationSpec.from_dict(p["spec"])
        ).ravel()
    )
    groups = (
        np.array(frame[names[p["spec"]["group"]]].to_list(), dtype=object)
        if p["spec"]["group"]
        else None
    )
    if groups is not None and any(
        g is not None and isinstance(g, float) and not math.isfinite(g) for g in groups
    ):
        raise ProjectError("Grup anahtarı sonlu olmalı.")
    times = None
    if p["spec"]["time"]:
        col = frame[names[p["spec"]["time"]]]
        if col.dtype != pl.Date and not isinstance(col.dtype, pl.Datetime):
            raise ProjectError("Zaman sütunu Date/Datetime olmalı.")
        times = np.array(
            [
                v.timestamp()
                if isinstance(v, datetime) and v.tzinfo
                else v.replace(tzinfo=UTC).timestamp()
                if isinstance(v, datetime)
                else datetime(v.year, v.month, v.day, tzinfo=UTC).timestamp()
                if v
                else np.nan
                for v in col.to_list()
            ]
        )
    plan, (train, val, development, test, folds) = split_plan(
        frame["__vu_row_id"].to_list(),
        y,
        groups,
        times,
        spec,
        method,
        classification,
        request["version_id"],
        request["fingerprint"],
        allow_missing_test_class=bool(request.get("classification")),
    )
    if request.get("mode") == "final" and (
        plan["split_id"] != request["expected_split_id"]
        or plan["protocol_id"] != request["expected_protocol_id"]
    ):
        raise ProjectError(
            "Final test ayrımı/protokolü kayıtlı geliştirme koşusuyla uyuşmuyor."
        )
    regression = request.get("regression")
    if regression:
        from veri_ufku.modeling.regression import settings

        regression = settings(regression)
        if len(frame) > (20000 if "forest" in regression["candidates"] else 100000):
            raise ProjectError(
                "Regresyon maliyet sınırı: Forest en fazla 20.000, diğer adaylar 100.000 uygun kayıt. Forest seçimini kaldırın veya açıkça daha küçük veri sürümü seçin."
            )
        if p["spec"]["purpose"] != "regression":
            raise ProjectError("Sayısal tahmin için sayısal hedef hazırlığı seçin.")
    category_config = request.get("classification")
    labels = sorted(set(y)) if classification else []
    if category_config:
        from veri_ufku.modeling import classification as category

        category_config = category.settings(category_config)
        if not classification:
            raise ProjectError("Kategori hedef hazırlığı seçin.")
        category.validate_classes(category_config, labels)
        if len(frame) > (
            20000 if "forest" in category_config["candidates"] else 100000
        ):
            raise ProjectError(
                "Sınıflandırma maliyet sınırı: Forest20.000, diğer adaylar100.000 uygun kayıt."
            )
    if family_config.get("uncertainty"):
        from veri_ufku.modeling.uncertainty import calculate_run

        result = calculate_run(
            request,
            workspace,
            control,
            p,
            frame,
            y,
            groups,
            times,
            spec,
            method,
            strategy,
            reason,
            plan,
            (train, val, development, test, folds),
            excluded,
        )
        result["elapsed_seconds"] = time.monotonic() - job_started
        return result
    from veri_ufku.modeling.family_contracts import (
        FAMILY_METHODS,
        FamilyOptions,
        support,
        validate_family,
    )

    if family_config.get("family_options"):
        options = FamilyOptions.from_dict(family_config["family_options"])
        for candidate in family_config["candidates"]:
            if candidate not in FAMILY_METHODS:
                continue
            validate_family(candidate, p["spec"]["purpose"], options, p["spec"], spec)
            limit = support(candidate, p["spec"]["purpose"])["row_limit"]
            quadratic = candidate in ("svm", "knn")
            estimated = (
                len(frame) ** 2 * 24
                if quadratic
                else len(frame) * len(p["spec"]["features"]) * 256
            )
            if len(frame) > limit or estimated > control.budget.ram_bytes // 2:
                raise ProjectError(
                    f"Model ComputeBudget: {candidate} en fazla {limit} kayıt; distance/dense üst maliyet {estimated} byte."
                )
    max_cells = min(4000000, control.budget.ram_bytes // 64)

    fitted_models = {}

    def evaluate(
        a, b, scope, candidate="baseline", decision_threshold=None, tune=False
    ):
        control.check()
        control.progress("Baseline / " + scope, 0, len(a) + len(b))
        model = pipeline(p, strategy, spec.seed, max_cells)
        if regression and candidate not in FAMILY_METHODS:
            from veri_ufku.modeling.regression import estimator

            model.steps[-1] = (
                "baseline",
                estimator(candidate, regression, strategy, spec.seed),
            )
        if category_config and candidate not in FAMILY_METHODS:
            model.steps[-1] = (
                "baseline",
                category.estimator(candidate, category_config, strategy, spec.seed),
            )
        if candidate in FAMILY_METHODS:
            from veri_ufku.modeling.families import (
                FamilyClassifier,
                FamilyRegressor,
                FamilyScope,
            )

            prep_spec = PreparationSpec.from_dict(p["spec"])
            model = Pipeline(
                [
                    (
                        "prepare",
                        FamilyScope(p["plan"], prep_spec, p["columns"], max_cells),
                    ),
                    (
                        "baseline",
                        (FamilyClassifier if classification else FamilyRegressor)(
                            candidate,
                            family_config["family_options"],
                            prep_spec,
                            p["columns"],
                            p["plan"],
                            spec.seed,
                            max_cells,
                            names.get(prep_spec.group, ""),
                            spec.structure,
                        ),
                    ),
                ]
            )
        started = time.monotonic()
        try:
            import warnings

            from sklearn.exceptions import ConvergenceWarning

            with warnings.catch_warnings():
                warnings.simplefilter("error", ConvergenceWarning)
                fit_kwargs = {}
                if candidate not in FAMILY_METHODS and family_config.get(
                    "family_options"
                ):
                    options = FamilyOptions.from_dict(family_config["family_options"])
                    fit_weights = None
                    if options.weight_column:
                        fit_weights = numeric(
                            frame[names[options.weight_column]].gather(a).to_list(),
                            PreparationSpec.from_dict(p["spec"]),
                        ).ravel()
                        if (
                            not np.isfinite(fit_weights).all()
                            or np.any(fit_weights < 0)
                            or fit_weights.sum() <= 0
                        ):
                            raise ProjectError("Baseline training weights geçersiz.")
                    if classification and options.class_balance == "balanced":
                        from sklearn.utils.class_weight import compute_sample_weight

                        balanced = compute_sample_weight("balanced", y[a])
                        fit_weights = (
                            balanced if fit_weights is None else fit_weights * balanced
                        )
                    if fit_weights is not None:
                        fit_kwargs["baseline__sample_weight"] = fit_weights
                model.fit(frame[a.tolist()], y[a], **fit_kwargs)
                if candidate in FAMILY_METHODS:
                    model.named_steps["prepare"].summary_ = model.named_steps[
                        "baseline"
                    ].metadata_
            control.check()
            pred = model.predict(frame[b.tolist()])
        except ProjectError as error:
            error.invalid_folds = [
                dict(
                    scope=scope,
                    status="invalid",
                    reason=str(error),
                    train_n=len(a),
                    evaluation_n=len(b),
                )
            ]
            raise
        except (ValueError, ConvergenceWarning) as error:
            invalid = dict(
                scope=scope,
                status="invalid",
                reason="Eğitim katında dönüşüm/seçim veya kategori uygulanamadı.",
                train_n=len(a),
                evaluation_n=len(b),
            )
            failure = ProjectError(invalid["reason"])
            failure.invalid_folds = [invalid]
            raise failure from error
        extra = {}
        if category_config:
            probability = category.probabilities(model, frame[b.tolist()], labels)
            threshold = 0.5 if decision_threshold is None else decision_threshold
            grid = []
            if tune:
                threshold, grid = category.choose_threshold(
                    y[b], pred, probability, labels, category_config
                )
            chosen = category.predictions(
                pred, probability, labels, category_config["positive_class"], threshold
            )
            extra = category.metrics(
                y[b], chosen, probability, labels, category_config, scope
            )
            extra.update(
                train_distribution=category.distribution(y[a], labels),
                threshold=threshold,
                probability_supported=probability is not None,
                threshold_candidates=grid,
            )
        evaluation = dict(
            scope=scope,
            status="valid",
            train_n=len(a),
            evaluation_n=len(b),
            fit_row_ids=model.named_steps["prepare"].fit_row_ids_,
            fitted_parameters=model.named_steps["prepare"].summary_,
            baseline_center=float(model.named_steps["baseline"].constant_[0, 0])
            if not classification and candidate == "baseline"
            else None,
            metrics=(
                [] if category_config else scores(y[b], pred, classification, scope)
            )
            + (regression_scores(y[b], pred, scope) if regression else []),
            **(prediction_records(frame, b, y[b], pred) if regression else {}),
            elapsed_seconds=time.monotonic() - started,
        )
        evaluation.update(extra)
        if scope in ("validation", "validation_threshold", "final_test"):
            fitted_models[candidate] = model
        return evaluation

    comparison = []
    selected = request.get("selected_model", "baseline")
    if regression and request.get("mode") != "final":
        for candidate in regression["candidates"]:
            evaluations = [evaluate(train, val, "validation", candidate)]
            evaluations += [
                evaluate(a, b, f"cv:{i + 1}", candidate)
                for i, (a, b) in enumerate(folds)
            ]
            comparison.append(
                dict(
                    model=candidate,
                    evaluations=evaluations,
                    cv_mae=float(
                        np.mean([e["metrics"][0]["value"] for e in evaluations[1:]])
                    ),
                )
            )
        selected = (
            regression.get("explicit_model")
            or min(comparison, key=lambda c: c["cv_mae"])["model"]
        )
        evaluations = next(
            c["evaluations"] for c in comparison if c["model"] == selected
        )
    elif category_config and request.get("mode") != "final":
        for candidate in category_config["candidates"]:
            evaluations = [evaluate(train, val, "validation", candidate)]
            evaluations += [
                evaluate(a, b, f"cv:{i + 1}", candidate)
                for i, (a, b) in enumerate(folds)
            ]
            comparison.append(
                dict(
                    model=candidate,
                    evaluations=evaluations,
                    cv_f1=float(
                        np.mean([e["metrics"][3]["value"] for e in evaluations[1:]])
                    ),
                )
            )
        selected = (
            category_config.get("explicit_model")
            or max(comparison, key=lambda c: c["cv_f1"])["model"]
        )
        evaluations = next(
            c["evaluations"] for c in comparison if c["model"] == selected
        )
    elif request.get("mode") == "final":
        if regression and selected not in regression["candidates"]:
            raise ProjectError("Final aday geliştirme planında bulunmuyor.")
        threshold = None
        if category_config:
            if selected not in category_config["candidates"]:
                raise ProjectError(
                    "Final kategori adayı geliştirme koşusunda bulunmuyor."
                )
            decision = request.get("decision")
            if (
                not decision
                or decision["model"] != selected
                or decision["positive_class"] != category_config["positive_class"]
                or decision["mode"] != category_config["threshold_mode"]
                or decision["cost_note"] != category_config["cost_note"]
                or decision["selection_scope"] != "validation"
                or decision["validation_row_ids"] != plan["membership"]["validation"]
                or type(decision["threshold"]) not in (int, float)
                or not 0.05 <= decision["threshold"] <= 0.95
                or (
                    category_config["threshold_mode"] != "validation_f1"
                    and decision["threshold"] != category_config["threshold"]
                )
            ):
                raise ProjectError(
                    "Final sınıf/eşik kararı geliştirme koşusunda dondurulmalı."
                )
            threshold = decision["threshold"]
        evaluations = [evaluate(development, test, "final_test", selected, threshold)]
    else:
        evaluations = [evaluate(train, val, "validation")]
        evaluations += [evaluate(a, b, f"cv:{i + 1}") for i, (a, b) in enumerate(folds)]
    decision_validation = None
    if category_config and request.get("mode") != "final":
        decision_validation = evaluate(
            train, val, "validation_threshold", selected, tune=True
        )
        decision = dict(
            model=selected,
            positive_class=category_config["positive_class"],
            threshold=decision_validation["threshold"],
            mode=category_config["threshold_mode"],
            selection_scope="validation",
            validation_row_ids=plan["membership"]["validation"],
            objective="positive_class_f1"
            if category_config["threshold_mode"] == "validation_f1"
            else "user_selected_or_default",
            cost_note=category_config["cost_note"],
        )
    control.check()
    cv_metrics = [e["metrics"] for e in evaluations if e["scope"].startswith("cv:")]
    cv_summary = []
    if cv_metrics:
        for position, metric in enumerate(cv_metrics[0]):
            values = [
                m[position]["value"]
                for m in cv_metrics
                if m[position]["value"] is not None
            ]
            if not values:
                continue
            cv_summary.append(
                dict(
                    metric=metric["metric"],
                    direction=metric["direction"],
                    scope="development_cv",
                    mean=float(np.mean(values)),
                    standard_deviation=float(np.std(values, ddof=1))
                    if len(values) > 1
                    else 0.0,
                    ddof=1,
                    valid_folds=len(values),
                    invalid_folds=0,
                    aggregation="unweighted fold mean; not pooled record error",
                )
            )
    result = dict(
        cv_summary=cv_summary,
        help_content_version=19 if regression else 18,
        history=p["history"],
        leakage_certified=False,
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
        spec=spec.data(),
        plan=plan,
        baseline=strategy,
        default_reason=reason,
        seed=spec.seed,
        excluded_target_row_ids=excluded,
        evaluations=evaluations,
        invalid_folds=[],
        estimated_cost=dict(
            train_n=len(train),
            validation_n=len(val),
            development_n=len(development),
            test_n=len(test),
            fold_train_n=[len(a) for a, b in folds],
            fit_count=1 if request.get("mode") == "final" else len(folds) + 1,
            estimated_fit_row_passes=len(development)
            if request.get("mode") == "final"
            else len(train) + sum(len(a) for a, b in folds),
            dense_cell_limit=max_cells,
            note="İş yükü tahmini; saniye veya yeterli örnek garantisi değildir. Train miktarı sınıf/grup/zaman kapsamı ve öğrenme eğrisiyle incelenmeli.",
        ),
        data_access_at=request["data_access_at"],
        evaluated_at=datetime.now(UTC).isoformat(),
        packages={
            name: importlib.metadata.version(name)
            for name in ("scikit-learn", "numpy", "scipy", "polars", "veri-ufku")
        },
        config_revision=request.get("config_revision", 0),
        prior_test_use_ids=request.get("prior_test_use_ids", []),
    )
    if regression:
        result.update(
            regression=regression,
            selected_model=selected,
            comparison=comparison,
            selection_rule="minimum development CV mean MAE; ties follow candidate order",
            interpretation="exploratory"
            if result["prior_test_use_ids"]
            else "project_test_not_previously_used",
            fit_count=len(evaluations) * (len(comparison) or 1),
        )
        result["estimated_cost"]["fit_count"] = result["fit_count"]
        result["estimated_cost"]["estimated_fit_row_passes"] *= len(comparison) or 1
    if category_config:
        result.update(
            classification=category_config,
            selected_model=selected,
            comparison=comparison,
            classes=labels,
            decision=decision,
            decision_validation=decision_validation,
            selection_rule="maximum development CV mean F1; declared averaging; candidate-order ties; thresholds chosen separately on validation",
            interpretation="exploratory"
            if result["prior_test_use_ids"]
            else "project_test_not_previously_used",
            external_test_use_known=False,
            fit_count=(len(folds) + 1) * len(comparison) + 1 if comparison else 1,
            help_content_version=26,
        )
        result["estimated_cost"]["fit_count"] = result["fit_count"]
        result["estimated_cost"]["estimated_fit_row_passes"] = (
            (
                (len(train) + sum(len(a) for a, b in folds)) * len(comparison)
                + len(train)
            )
            if comparison
            else len(development)
        )
    if family_config.get("family_options"):
        options = FamilyOptions.from_dict(family_config["family_options"])
        factors = {
            m: 10
            if m == "bagging"
            else 2
            if m == "voting"
            else 2 * (options.inner_folds + 1) + 1
            if m == "stacking"
            else 1
            for m in family_config["candidates"]
        }
        result["estimated_cost"]["native_fits_per_pipeline"] = factors
        result["estimated_cost"]["native_fit_upper_bound"] = (
            factors.get(selected, 1)
            if result["mode"] == "final"
            else (len(folds) + 1) * sum(factors.values())
            + (factors[selected] if category_config else 0)
        )
        result["estimated_cost"]["fit_count_meaning"] = (
            "outer pipeline fits; native child/OOF fits reported separately"
        )
    if family_config.get("explicit_model"):
        result["selection_rule"] = (
            "explicit user family selection fixed before CV; baseline same split/folds; no universal best algorithm"
        )
        result["help_content_version"] = 64
    if not p["spec"].get("text") and selected not in (
        "xgboost",
        "lightgbm",
        "catboost",
    ):
        from veri_ufku.modeling.lifecycle import card_for, permutation, save_package
        from veri_ufku.storage.project_store import file_hash

        model = fitted_models[selected]
        card = card_for(
            model, result, request["columns"], request.get("semantic_metadata")
        )
        if result["mode"] == "development" and selected not in FAMILY_METHODS:
            card["importance"] = permutation(
                model, frame[val.tolist()], y[val], card, control
            )
        package_path = Path(workspace) / ("model-" + uid() + ".vumodel")
        save_package(package_path, model, card)
        result["model_card"] = card
        result["model_package"] = dict(
            path=str(package_path), fingerprint=file_hash(package_path)
        )
    else:
        result["model_package_unavailable"] = (
            "Seçili optional/TF-IDF model için safe persistence/yeni dosya tahmini kapalı; değerlendirme kayıtları korunur."
        )
    checked(request, control)
    Path(workspace, "baseline-report.json").write_text(
        json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )
    control.disk(Path(workspace))
    control.check()
    result["elapsed_seconds"] = time.monotonic() - job_started
    return result


def validate_saved(record, versions):
    r = record["baseline"]
    if (
        r["schema"] != "BaselineRun/v1"
        or r["status"] != "completed"
        or record["capability_id"]
        != (
            "model.classification"
            if r.get("classification")
            else "model.regression"
            if r.get("regression")
            else "model.baseline"
        )
        or record["seed"] != r["seed"]
        or r["dataset_version"] not in versions
        or record["dataset_version_ids"]
        != list(dict.fromkeys([r["origin_version"], r["dataset_version"]]))
    ):
        raise ProjectError("Baseline kayıt/sürüm bağı geçersiz.")
    source = versions[r["dataset_version"]]
    prep = PreparationSpec.from_dict(r["preparation_spec"])
    prep.validate(source["import_metadata"]["columns"])
    if prep.source_version != r["dataset_version"]:
        raise ProjectError("Baseline hazırlığı kaynak sürümüyle uyuşmuyor.")
    from veri_ufku.modeling.plan import blueprint

    expected = blueprint(
        prep,
        source["import_metadata"]["columns"],
        source.get("semantic_metadata", {}),
        r["history"],
    )
    if {k: v for k, v in r["pipeline"].items() if k != "version_id"} != expected or r[
        "pipeline_id"
    ] != r["pipeline"]["version_id"]:
        raise ProjectError("Baseline pipeline tarifi geçmiş/kolonlarla uyuşmuyor.")
    spec = ValidationSpec.from_dict(r["spec"])
    spec.resolved(dict(spec=r["preparation_spec"]))
    if r.get("uncertainty"):
        from veri_ufku.modeling.uncertainty import validate_saved_run

        validate_saved_run(r)
        return
    if r.get("classification"):
        from veri_ufku.modeling.classification import validate_run

        validate_run(r, record, versions)
    if r.get("regression"):
        from veri_ufku.modeling.regression import settings

        config = settings(r["regression"])
        if r.get("interpretation") != (
            "exploratory"
            if r["prior_test_use_ids"]
            else "project_test_not_previously_used"
        ):
            raise ProjectError("Regresyon yorum durumu test geçmişini gizleyemez.")
        if (
            r["selected_model"] not in config["candidates"]
            or prep.purpose != "regression"
        ):
            raise ProjectError("Kayıtlı regresyon seçimi geçersiz.")
        if not r.get("details_uri"):
            if r["mode"] == "development":
                if [c["model"] for c in r["comparison"]] != config["candidates"]:
                    raise ProjectError("Aday karşılaştırma kapsamı eksik.")
                winner = (
                    next(
                        c
                        for c in r["comparison"]
                        if c["model"] == config["explicit_model"]
                    )
                    if config.get("explicit_model")
                    else min(r["comparison"], key=lambda c: c["cv_mae"])
                )
                if (
                    winner["model"] != r["selected_model"]
                    or winner["evaluations"] != r["evaluations"]
                ):
                    raise ProjectError(
                        "Model seçimi geliştirme CV karşılaştırmasıyla uyuşmuyor."
                    )
                for c in r["comparison"]:
                    child = dict(r, evaluations=c["evaluations"])
                    child.pop("regression")
                    validate_saved(
                        dict(record, baseline=child, capability_id="model.baseline"),
                        versions,
                    )
                    mean = float(
                        np.mean(
                            [e["metrics"][0]["value"] for e in c["evaluations"][1:]]
                        )
                    )
                    if c["cv_mae"] != mean:
                        raise ProjectError(
                            "Aday CV MAE değeri fold skorlarıyla uyuşmuyor."
                        )
            elif r["comparison"]:
                raise ProjectError("Final test aday karşılaştırması yapamaz.")
    if r.get("details_uri"):
        from veri_ufku.storage.project_model import fingerprint, relative

        relative(r["details_uri"])
        fingerprint(r["details_fingerprint"])
        if r["plan"]["membership"] is not None or any(
            e.get("fit_row_ids") is not None or e.get("fitted_parameters") is not None
            for e in r["evaluations"]
        ):
            raise ProjectError("Büyük koşu özeti ayrıntı artifactına bağlı olmalı.")
        return
    membership = r["plan"]["membership"]
    test = set(membership["test"])
    if (
        not test
        or test & set(membership["development"])
        or set(membership["train"]) & set(membership["validation"])
    ):
        raise ProjectError("Kayıtlı test/train/validation ayrımı çakışıyor.")
    protocol = "protocol:" + digest(dict(spec=r["spec"], method=r["plan"]["method"]))
    split = "split:" + digest(
        dict(
            dataset_version=r["dataset_version"],
            fingerprint=r["snapshot_fingerprint"],
            protocol_id=protocol,
            membership=membership,
        )
    )
    if (r["plan"]["protocol_id"], r["plan"]["split_id"]) != (protocol, split):
        raise ProjectError("Split/protokol kimliği üyeliklerle uyuşmuyor.")
    for e in r["evaluations"]:
        if (
            set(e["fit_row_ids"]) & test
            or not set(e["fit_row_ids"]) <= set(membership["development"])
            or e["status"] != "valid"
        ):
            raise ProjectError(
                "Final test kayıtları fit'e katılmış veya fold geçersiz."
            )
    if (
        r["mode"] not in ("development", "final")
        or not r["evaluations"]
        or any(
            (e["scope"] == "final_test") != (r["mode"] == "final")
            for e in r["evaluations"]
        )
    ):
        raise ProjectError("Metrik değerlendirme kapsamı geçersiz.")

    members = membership
    expected_scopes = (
        {"final_test": (members["development"], members["test"])}
        if r["mode"] == "final"
        else {
            "validation": (members["train"], members["validation"]),
            **{
                f"cv:{i + 1}": (f["train"], f["validation"])
                for i, f in enumerate(members["folds"])
            },
        }
    )
    if [e["scope"] for e in r["evaluations"]] != list(expected_scopes):
        raise ProjectError("Koşuda beklenen bütün fold değerlendirmeleri bulunmalı.")
    if not set(members["train"] + members["validation"]) <= set(members["development"]):
        raise ProjectError("Holdout geliştirme kapsamıyla uyuşmuyor.")
    for e in r["evaluations"]:
        a, b = expected_scopes[e["scope"]]
        if (
            sorted(e["fit_row_ids"]) != sorted(a)
            or e["train_n"] != len(a)
            or e["evaluation_n"] != len(b)
            or set(a) & set(b)
        ):
            raise ProjectError("Fit üyelikleri kayıtlı train/fold ile tam eşleşmeli.")
        if r.get("regression"):
            if [m["metric"] for m in e["metrics"]] != ["mae", "rmse", "r2"]:
                raise ProjectError("Regresyon metrik kapsamı MAE/RMSE/R² olmalı.")
            points = e["predictions"]
            evaluation_ids = set(b)
            if (
                len(points) != min(1000, len(b))
                or len({p["row_id"] for p in points}) != len(points)
                or any(
                    p["row_id"] not in evaluation_ids
                    or not all(
                        math.isfinite(p[k]) for k in ("actual", "predicted", "residual")
                    )
                    or not math.isclose(
                        p["residual"],
                        p["actual"] - p["predicted"],
                        rel_tol=1e-12,
                        abs_tol=1e-12,
                    )
                    for p in points
                )
            ):
                raise ProjectError(
                    "Tahmin/artık örneği değerlendirme bölümüyle uyuşmuyor."
                )
        if any(
            m["scope"] != e["scope"]
            or m["n"] != len(b)
            or m["status"] not in ("valid", "undefined_constant_target", "undefined")
            or (
                m["value"] is None
                and not (
                    m["status"] == "undefined_constant_target"
                    and m["metric"] == "r2"
                    or m["status"] == "undefined"
                    and prep.purpose == "classification"
                    and m["metric"] in ("roc_auc", "pr_auc")
                )
            )
            or (m["value"] is not None and not math.isfinite(m["value"]))
            or m["direction"]
            != (
                "maximize"
                if prep.purpose == "classification" or m["metric"] == "r2"
                else "minimize"
            )
            for m in e["metrics"]
        ):
            raise ProjectError("Metrik yönü/kapsamı/değeri geçersiz.")


def regression_scores(y, pred, scope):
    from sklearn.metrics import r2_score

    constant = bool(np.all(y == y[0]))
    return [
        dict(
            metric="r2",
            value=None if constant else float(r2_score(y, pred)),
            direction="maximize",
            scope=scope,
            n=len(y),
            status="undefined_constant_target" if constant else "valid",
            coverage="all eligible records in this evaluation partition",
            averaging="per_record",
        )
    ]


def prediction_records(frame, indices, actual, predicted):
    # Bounded deterministic chart sample; all records contribute to metrics.
    positions = np.linspace(0, len(indices) - 1, min(1000, len(indices)), dtype=int)
    return dict(
        predictions=[
            dict(
                row_id=frame["__vu_row_id"][int(indices[i])],
                actual=float(actual[i]),
                predicted=float(predicted[i]),
                residual=float(actual[i] - predicted[i]),
            )
            for i in positions
        ],
        prediction_coverage=dict(
            total=len(indices),
            displayed=len(positions),
            sampling="evenly spaced partition positions; not a random fit sample",
        ),
    )
