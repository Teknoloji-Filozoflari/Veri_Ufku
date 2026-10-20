"""Closed model packages and RowId based inference. Never import pickle/joblib."""

import importlib.metadata
import io
import os
import platform
import zipfile

import numpy as np
import polars as pl
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cluster import KMeans
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (
    IsolationForest,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import IterativeImputer, KNNImputer, SimpleImputer
from sklearn.linear_model import (
    BayesianRidge,
    LinearRegression,
    LogisticRegression,
    Ridge,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from veri_ufku.domain.json import parse, raw_json, sha
from veri_ufku.modeling.baseline import FoldPreparation
from veri_ufku.modeling.contracts import PreparationSpec
from veri_ufku.modeling.families import (
    FamilyClassifier,
    FamilyRegressor,
    FamilyScope,
    validate_estimator,
)
from veri_ufku.modeling.uncertainty import (
    IntervalModel,
    ProbabilityModel,
    validate_model,
)
from veri_ufku.storage.project_model import ProjectError

MAX_BYTES = 128 * 1024**2
VERSIONS = ("scikit-learn", "numpy", "scipy", "polars", "skops", "veri-ufku")
LIMITATION = (
    "Katsayı ve önemler nedensel etki değildir. İlişkili özellikler önemi paylaşabilir veya gizleyebilir. "
    "Yeni veri dağılımı değişebilir; olasılık kesinlik veya kalibrasyon garantisi değildir. "
    "Küme ve anomali adayları gerçek sınıf/veri hatası değildir; otomatik silme yok."
)


class Measurements(BaseEstimator, TransformerMixin):
    """Reviewed fixed transform for already fitted unsupervised measurements."""

    def __init__(self, names, scaler=None):
        self.names, self.scaler = names, scaler

    def transform(self, X):
        values = X.select(self.names).to_numpy().astype(float)
        if not np.isfinite(values).all():
            raise ProjectError("Etiketsiz tahminde eksik/sonlu olmayan ölçüm var.")
        return self.scaler.transform(values) if self.scaler is not None else values


class IQRBounds(BaseEstimator):
    def __init__(self, lower, upper):
        self.lower, self.upper = lower, upper

    def fit(self, X, y=None):
        raise ProjectError("IQR paketi eğitim eşiklerini korur; yeni fit engellendi.")

    def __sklearn_is_fitted__(self):
        return True

    def score_samples(self, X):
        return -np.maximum(np.maximum(self.lower - X[:, 0], X[:, 0] - self.upper), 0)

    def predict(self, X):
        return (-self.score_samples(X) > 0).astype(int)


ESTIMATORS = (
    DummyRegressor,
    DummyClassifier,
    LinearRegression,
    Ridge,
    RandomForestRegressor,
    LogisticRegression,
    RandomForestClassifier,
    KMeans,
    IsolationForest,
    IQRBounds,
    FamilyClassifier,
    FamilyRegressor,
    ProbabilityModel,
    IntervalModel,
)
TRANSFORMS = (
    SimpleImputer,
    KNNImputer,
    IterativeImputer,
    OneHotEncoder,
    OrdinalEncoder,
    StandardScaler,
)
# This list is code reviewed, NEVER populated from an incoming file.
TRUSTED = [
    "numpy.dtype",
    "veri_ufku.modeling.uncertainty.ProbabilityModel",
    "veri_ufku.modeling.uncertainty.IntervalModel",
    "scipy.sparse._csr.csr_matrix",
    "sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor",
    "veri_ufku.modeling.families.FamilyScope",
    "veri_ufku.modeling.families.HGBArrayPreparation",
    "veri_ufku.modeling.families.FamilyPreparation",
    "veri_ufku.modeling.families.FamilyClassifier",
    "veri_ufku.modeling.families.FamilyRegressor",
    "sklearn.tree._tree.Tree",
    "sklearn.impute._iterative._ImputerTriplet",
    # Reviewed transform already in TRANSFORMS. skops default trust for this
    # experimental class depends on its import order; use the closed list.
    "sklearn.impute._iterative.IterativeImputer",
    "veri_ufku.modeling.baseline.FoldPreparation",
    "veri_ufku.modeling.contracts.PreparationSpec",
    "veri_ufku.modeling.lifecycle.Measurements",
    "veri_ufku.modeling.lifecycle.IQRBounds",
]


def versions():
    return {
        **{n: importlib.metadata.version(n) for n in VERSIONS},
        "python": platform.python_version(),
    }


def archive(raw, names=None):
    if len(raw) > MAX_BYTES:
        raise ProjectError("Model paketi 128MiB sınırını aşıyor.")
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
        items = z.infolist()
        if (
            len(items) > 10000
            or len({i.filename for i in items}) != len(items)
            or sum(i.file_size for i in items) > MAX_BYTES
            or any(
                i.flag_bits & 1
                or i.file_size < 0
                or i.filename.startswith("/")
                or ".." in i.filename.split("/")
                or ((i.external_attr >> 16) & 0o170000) == 0o120000
                for i in items
            )
            or names is not None
            and set(z.namelist()) != set(names)
        ):
            raise ProjectError("Paket üye/boyut/yol sözleşmesi reddedildi.")
        return z
    except (zipfile.BadZipFile, OSError) as error:
        raise ProjectError(
            "Yalnız Veri_Ufku güvenli model paketi açılabilir; pickle/joblib açılmaz."
        ) from error


def validate_pipeline(model, card):
    if type(model) is not Pipeline or [s[0] for s in model.steps] != [
        "prepare",
        "baseline",
    ]:
        raise ProjectError("Desteklenmeyen pipeline engellendi.")
    prep, estimator = (s[1] for s in model.steps)
    if (
        type(estimator) not in ESTIMATORS
        or type(estimator).__name__ != card["estimator"]
    ):
        raise ProjectError(
            "Desteklenmeyen estimator kaydı/açılması engellendi; DBSCAN predict yok."
        )
    if type(prep) is FamilyScope:
        if (
            prep.spec.data() != card["preparation_spec"]
            or prep.plan != card["preprocessing"]
            or prep.columns != card["columns"]
            or prep.fit_row_ids_ != card["fit_row_ids"]
            or prep.summary_ != card["fitted_preprocessing"]
        ):
            raise ProjectError("FamilyScope kart/preprocessing/fit bağı geçersiz.")
        validate_estimator(estimator, card)
    elif type(prep) is FoldPreparation:
        if (
            type(prep.spec) is not PreparationSpec
            or prep.spec.data() != card["preparation_spec"]
            or prep.plan != card["preprocessing"]
            or prep.columns != card["columns"]
            or prep.spec.features != tuple(f["id"] for f in card["features"])
            or prep.fit_row_ids_ != card["fit_row_ids"]
            or prep.summary_ != card["fitted_preprocessing"]
        ):
            raise ProjectError("Özellik sırası/fit/preprocessing sözleşmesi uyuşmuyor.")
        if any(
            type(op) not in TRANSFORMS and type(op) is not tuple
            for op in prep.steps_.values()
        ):
            raise ProjectError("Desteklenmeyen hazırlama adımı.")
        for i, step in enumerate(prep.plan["steps"]):
            if step["kind"] != "impute_joint":
                continue
            op = prep.steps_[str(i)]
            parameters = step["parameters"]
            if parameters["strategy"] == "knn":
                valid = (
                    type(op) is KNNImputer
                    and op.n_neighbors == parameters["neighbors"]
                    and op.weights == "uniform"
                    and op.metric == "nan_euclidean"
                    and not op.add_indicator
                    and not op.keep_empty_features
                )
            else:
                valid = (
                    type(op) is IterativeImputer
                    and op.estimator is None
                    and not op.sample_posterior
                    and op.random_state == parameters["seed"]
                    and op.max_iter == parameters["iterations"]
                    and all(
                        type(part.estimator) is BayesianRidge
                        for part in op.imputation_sequence_
                    )
                )
            if not valid:
                raise ProjectError(
                    "Joint imputasyon kapalı parametre/estimator sözleşmesi uyuşmuyor."
                )
        if (
            hasattr(prep, "selection_")
            and type(prep.selection_) is not VarianceThreshold
        ):
            raise ProjectError("Desteklenmeyen özellik seçimi.")
    elif type(prep) is Measurements:
        if (
            prep.names != [f["name"] for f in card["features"]]
            or prep.scaler is not None
            and type(prep.scaler) is not StandardScaler
        ):
            raise ProjectError("Etiketsiz ölçüm sırası/ölçek sözleşmesi geçersiz.")
        state = (
            None
            if prep.scaler is None
            else dict(
                mean=prep.scaler.mean_.tolist(), scale=prep.scaler.scale_.tolist()
            )
        )
        if state != card["fitted_preprocessing"]:
            raise ProjectError("Etiketsiz ölçek durumu uyuşmuyor.")
    else:
        raise ProjectError("Desteklenmeyen preprocessing engellendi.")
    if type(estimator) in (ProbabilityModel, IntervalModel):
        validate_model(estimator, card)
    elif card.get("uncertainty"):
        raise ProjectError("Belirsizlik kartı uygun estimator gerektirir.")
    classes = estimator.classes_.tolist() if hasattr(estimator, "classes_") else []
    if classes != card["label_order"]:
        raise ProjectError("Label sırası uyuşmuyor.")
    if bool(hasattr(model, "predict_proba")) != card["probability_supported"]:
        raise ProjectError("Olasılık desteği sözleşmesi uyuşmuyor.")


def validate_card(card):
    required = {
        "schema",
        "purpose",
        "dataset_version",
        "snapshot_fingerprint",
        "fit_scope",
        "fit_row_ids",
        "features",
        "columns",
        "target",
        "split",
        "preprocessing",
        "preparation_spec",
        "fitted_preprocessing",
        "candidate_selection",
        "metrics",
        "baseline",
        "seed",
        "versions",
        "limitations",
        "estimator",
        "label_order",
        "probability_supported",
        "decision",
        "importance",
        "run_id",
        "method",
        "threshold",
    }
    if (
        not isinstance(card, dict)
        or set(card)
        != (
            required
            | (
                {"uncertainty"}
                if card.get("estimator") in ("ProbabilityModel", "IntervalModel")
                else set()
            )
        )
        or card["schema"] != "ModelCard/v1"
    ):
        raise ProjectError("Model kartı şeması/sürümü desteklenmiyor.")
    if card["estimator"] not in [t.__name__ for t in ESTIMATORS]:
        raise ProjectError(
            "Desteklenmeyen estimator kaydı/açılması engellendi; DBSCAN predict yok."
        )
    features = card["features"]
    if (
        not isinstance(features, list)
        or not 1 <= len(features) <= 256
        or len({f["id"] for f in features}) != len(features)
        or any(set(f) != {"id", "name", "type", "unit"} for f in features)
        or not isinstance(card["fit_row_ids"], list)
        or len(card["fit_row_ids"]) > 100000
        or len(set(card["fit_row_ids"])) != len(card["fit_row_ids"])
        or card["estimator"] not in [t.__name__ for t in ESTIMATORS]
        or not isinstance(card["label_order"], list)
    ):
        raise ProjectError("Model kartı özellik/etiket/fit sözleşmesi geçersiz.")
    by_id = {c["id"]: c for c in card["columns"]}
    if any(
        f["id"] not in by_id
        or any(f[k] != by_id[f["id"]][k] for k in ("id", "name", "type"))
        for f in features
    ):
        raise ProjectError("Özellik şeması model kolon sözleşmesiyle uyuşmuyor.")
    if card["versions"] != versions():
        raise ProjectError(
            "Model paketi sürüm uyumsuzluğu; otomatik migrasyon/refit yok."
        )
    return card


def save_package(path, model, card):
    import skops.io as sio

    validate_card(card)
    validate_pipeline(model, card)
    payload = sio.dumps(model)
    if set(sio.get_untrusted_types(data=payload)) - set(TRUSTED):
        raise ProjectError(
            "Güvenli destek matrisi dışındaki estimator/tip kaydedilemez."
        )
    contents = {"card.json": raw_json(card), "pipeline.skops": payload}
    contents["integrity.json"] = raw_json({n: sha(v) for n, v in contents.items()})
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for n, value in contents.items():
            z.writestr(n, value)
    raw = stream.getvalue()
    if len(raw) > MAX_BYTES or sum(map(len, contents.values())) > MAX_BYTES:
        raise ProjectError("Model paketi boyut sınırını aşıyor.")
    with open(path, "xb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    # Validate with the exact same loader used for an external package.
    loaded, _ = load_package(path)
    return loaded


def load_package(path):
    import skops.io as sio

    try:
        with open(path, "rb") as f:
            raw = f.read(MAX_BYTES + 1)
        with archive(raw, ["card.json", "pipeline.skops", "integrity.json"]) as z:
            parts = {n: z.read(n) for n in z.namelist()}
        integrity = parse(parts["integrity.json"])
        if integrity != {n: sha(parts[n]) for n in ("card.json", "pipeline.skops")}:
            raise ProjectError("Model paketi hash/bütünlük kontrolü başarısız.")
        card = validate_card(parse(parts["card.json"]))
        with archive(parts["pipeline.skops"]):
            pass
        if set(sio.get_untrusted_types(data=parts["pipeline.skops"])) - set(TRUSTED):
            raise ProjectError(
                "Paket izin verilmeyen tip içeriyor; yerel dosya güvenilir sayılmaz."
            )
        model = sio.loads(parts["pipeline.skops"], trusted=TRUSTED)
        validate_pipeline(model, card)
        return model, card
    except ProjectError:
        raise
    except Exception as error:
        raise ProjectError(
            "Güvenli model paketi bozuk veya uyumsuz; açılmadı."
        ) from error


def card_for(model, result, columns, semantics=None):
    semantics = semantics or {}
    prep = model.named_steps["prepare"]
    supervised = type(prep) in (FoldPreparation, FamilyScope)
    spec = result["preparation_spec"] if supervised else result["spec"]
    features = [
        dict(
            id=c["id"],
            name=c["name"],
            type=c["type"],
            unit=semantics.get(c["id"], {}).get("unit", ""),
        )
        for ident in spec["features"]
        for c in columns
        if c["id"] == ident
    ]
    e = model.named_steps["baseline"]
    card = dict(
        schema="ModelCard/v1",
        purpose=spec["purpose"] if supervised else spec["method"],
        dataset_version=result["dataset_version"],
        snapshot_fingerprint=result["snapshot_fingerprint"]
        if supervised
        else result["provenance"]["snapshot_fingerprint"],
        fit_scope=(
            "development_train; validation previously used for selection"
            if result["mode"] == "development"
            else "development_train_plus_validation; frozen final model"
        )
        if supervised
        else result["fit_scope"],
        fit_row_ids=prep.fit_row_ids_ if supervised else result["fit_row_ids"],
        features=features,
        columns=columns,
        target=next(
            (
                dict(
                    c,
                    unit=result.get("regression", {}).get(
                        "unit", semantics.get(c["id"], {}).get("unit", "")
                    ),
                )
                for c in columns
                if c["id"] == spec.get("target")
            ),
            None,
        ),
        split=result["plan"] if supervised else None,
        preprocessing=prep.plan if supervised else dict(scaling=spec["scaling"]),
        preparation_spec=spec if supervised else None,
        fitted_preprocessing=prep.summary_ if supervised else result["scaling_state"],
        candidate_selection=dict(
            selected=result.get("selected_model", spec.get("method", "baseline")),
            rule=result.get("selection_rule", "explicit method; no candidate search"),
            parameters=result.get("regression")
            or result.get("classification")
            or (dict(baseline=result["baseline"]) if supervised else spec),
        ),
        metrics=[
            {
                k: e[k]
                for k in ("scope", "train_n", "evaluation_n", "metrics", "status")
                if k in e
            }
            for e in result["evaluations"]
        ]
        if supervised
        else result["evaluation"],
        baseline=dict(
            strategy=result["baseline"],
            comparison=[
                dict(scope=e["scope"], metrics=e["metrics"])
                for c in result.get("comparison", [])
                if c["model"] == "baseline"
                for e in c["evaluations"]
            ],
            limitation="Final koşuda yeniden baseline seçimi yapılmaz; geliştirme koşusu kartına bakın.",
        )
        if supervised
        else None,
        seed=result.get("seed", spec.get("seed")),
        versions=versions(),
        limitations=LIMITATION,
        estimator=type(e).__name__,
        label_order=e.classes_.tolist() if hasattr(e, "classes_") else [],
        probability_supported=hasattr(model, "predict_proba"),
        decision=result.get("decision"),
        importance=dict(
            status="unavailable",
            reason="Bağımsız değerlendirme bölümü yok; nedensellik çıkarılamaz.",
        ),
        run_id=result["run_id"],
        method=spec.get("method"),
        threshold=result.get("threshold"),
    )
    return parse(raw_json(card))


def permutation(model, frame, y, card, control):
    """Explicit validation-only exploratory importance; no final test reuse."""
    if len(frame) > 3000 or frame.height < 8:
        return dict(
            status="unavailable", reason="Validation 8–3000 kayıt bütçesi dışında."
        )
    classification = card["purpose"] == "classification"

    def score(data):
        pred = model.predict(data)
        return (
            float(np.mean(pred == y))
            if classification
            else -float(np.mean(abs(pred - y)))
        )

    base = score(frame)
    rng = np.random.default_rng(card["seed"])
    rows = []
    for f in card["features"]:
        values = []
        for _ in range(3):
            control.check()
            shuffled = frame.with_columns(
                frame[f["name"]].gather(rng.permutation(len(frame)).tolist())
            )
            values.append(base - score(shuffled))
        rows.append(
            dict(
                column_id=f["id"],
                name=f["name"],
                mean=float(np.mean(values)),
                std=float(np.std(values)),
            )
        )
    return dict(
        status="available",
        scope="validation; exploratory; already used for model/threshold selection",
        row_ids=frame["__vu_row_id"].to_list(),
        metric="accuracy" if classification else "negative_MAE",
        repeats=3,
        seed=card["seed"],
        values=rows,
        limitation="İlişkili değişkenler önemi paylaşır/gizler; negatif önem mümkün. Nedensellik değildir; final test kullanılmadı.",
    )


def checked_transform(model, batch):
    if type(model.named_steps["prepare"]) is FamilyScope:
        learner = model.named_steps["baseline"]
        for child in learner.children_ or [learner]:
            child.preparation_.transform(batch)
        return np.ones((len(batch), 1))
    values = model.named_steps["prepare"].transform(batch)
    if not np.isfinite(values).all():
        raise ProjectError("Dönüşüm sonlu değil.")
    return values


def preview(model, card, frame, columns, mapping=None, semantics=None, control=None):
    if (
        "__vu_row_id" not in frame
        or frame["__vu_row_id"].null_count()
        or frame["__vu_row_id"].n_unique() != len(frame)
    ):
        raise ProjectError("Tahmin girişi benzersiz, eksiksiz RowId gerektirir.")
    if not 1 <= len(frame) <= 100000:
        raise ProjectError("Yeni veri 1–100.000 kayıt olmalı.")
    mapping = mapping or {}
    if set(mapping) - {f["id"] for f in card["features"]}:
        raise ProjectError("Eşleme bilinmeyen eğitim özelliği içeriyor.")
    semantics = semantics or {}
    reports, selected, blockers = [], [], []
    for feature in card["features"]:
        ident = feature["id"]
        candidates = [c for c in columns if c["id"] == mapping.get(ident, ident)]
        if not candidates and ident not in mapping:
            candidates = [c for c in columns if c["name"] == feature["name"]]
        if len(candidates) != 1:
            blockers.append(
                feature["name"] + ": eksik/belirsiz kolon; açık eşleme gerekli"
            )
            continue
        c = candidates[0]
        selected.append(c)
        series = frame[c["name"]]
        unit = semantics.get(c["id"], {}).get("unit", "")
        reason = []
        # Delimited import uses fixed primitive aliases; native import uses
        # Polars names. Normalize only exact storage-equivalent primitive types.
        aliases = {
            "text": "String",
            "int64": "Int64",
            "float64": "Float64",
            "boolean": "Boolean",
            "date": "Date",
        }
        expected_type = aliases.get(feature["type"], feature["type"])
        declared_type = aliases.get(c["type"], c["type"])
        if str(series.dtype) != expected_type or declared_type != expected_type:
            reason.append("Veri tipi uyuşmuyor; açık dönüşüm sonrası yeniden seçin")
        if unit != feature["unit"]:
            reason.append("Birim uyuşmuyor veya bilinmiyor; metadata ile doğrulayın")
        unknown = 0
        prep = model.named_steps["prepare"]
        if type(prep) is FoldPreparation:
            for i, step in enumerate(prep.plan["steps"]):
                if step["input_column_ids"] == [ident] and step["kind"] in (
                    "encode_onehot",
                    "encode_ordinal",
                ):
                    categories = set(prep.steps_[str(i)].categories_[0].tolist())
                    unknown = sum(
                        v is not None and str(v) not in categories for v in series
                    )
                    # Ordinal unknowns are invalid rows: explicit reject/drop policy below.
        if type(prep) is FamilyScope:
            import json

            family = model.named_steps["baseline"]
            children = family.children_ or [family]
            for child in children:
                state = child.preparation_.summary_.get(ident, {})
                if state.get("kind") in ("onehot", "ordinal", "native_categorical"):
                    known = set(state["categories"])
                    count = sum(
                        v is not None
                        and json.dumps([type(v).__name__, str(v)], ensure_ascii=False)
                        not in known
                        for v in series
                    )
                    unknown = max(unknown, count)
        blockers += [feature["name"] + ": " + r for r in reason]
        reports.append(
            dict(
                feature_id=ident,
                feature_name=feature["name"],
                column_id=c["id"],
                column_name=c["name"],
                expected_type=feature["type"],
                actual_type=str(series.dtype),
                expected_unit=feature["unit"],
                actual_unit=unit,
                missing=series.null_count(),
                nonfinite=int((~series.is_finite()).fill_null(False).sum())
                if series.dtype.is_float()
                else 0,
                unknown_categories=unknown,
                unknown_policy="native missing; onehot all-zero; ordinal reject"
                if type(prep) is FamilyScope
                else "onehot all-zero; ordinal reject",
                issues=reason,
            )
        )
    if len({c["id"] for c in selected}) != len(selected):
        blockers.append("Aynı giriş kolonu birden çok özelliğe eşlenemez")
    invalid_ids = []
    if not blockers:
        names = {c["id"]: c["name"] for c in columns}
        aligned = frame.select(
            "__vu_row_id",
            *[pl.col(names[r["column_id"]]).alias(r["feature_name"]) for r in reports],
        )

        for batch in aligned.iter_slices(512):
            if control:
                control.check()
            try:
                transformed = checked_transform(model, batch)
                if not np.isfinite(transformed).all():
                    raise ValueError("nonfinite")
            except (ValueError, TypeError, ProjectError, OverflowError):
                for row in batch.iter_slices(1):
                    if control:
                        control.check()
                    try:
                        values = checked_transform(model, row)
                        if not np.isfinite(values).all():
                            raise ValueError("nonfinite")
                    except (ValueError, TypeError, ProjectError, OverflowError):
                        invalid_ids.append(row["__vu_row_id"][0])
    return dict(
        schema="PredictionPreview/v1",
        rows=len(frame),
        features=reports,
        invalid_row_ids=invalid_ids,
        invalid_rows=len(invalid_ids),
        extra_columns=[c["name"] for c in columns if c not in selected],
        blockers=blockers,
        mapping={r["feature_id"]: r["column_id"] for r in reports},
        policy="Fazla kolonlar modelde kullanılmaz; kaynak çıktıda korunur. Eksikler eğitim imputasyonu ile işlenir; dönüşemeyen kayıt reject/drop seçimine bağlıdır.",
        scope="full selected immutable DatasetVersion; table view filters/sort do not alter inference scope",
        probability_supported=card["probability_supported"],
        uncertainty=LIMITATION,
    )


def predict(
    model,
    card,
    frame,
    columns,
    mapping=None,
    semantics=None,
    invalid="reject",
    batch_size=512,
    control=None,
):
    from veri_ufku.importers.delimited import Control

    control = control or Control()
    if (
        invalid not in ("reject", "drop")
        or type(batch_size) is not int
        or not 1 <= batch_size <= 4096
    ):
        raise ProjectError("Kayıt politikası/batch boyutu geçersiz.")
    report = preview(model, card, frame, columns, mapping, semantics, control)
    if invalid == "reject" and report["invalid_rows"]:
        raise ProjectError(
            "Geçersiz yeni kayıt; tahmin durdu. Açık drop politikasıyla yeniden önizleyin."
        )
    if report["blockers"]:
        raise ProjectError("; ".join(report["blockers"]))
    # Select aliases in TRAINING feature order; never join by values or row position.
    names = {c["id"]: c["name"] for c in columns}
    data = frame.select(
        "__vu_row_id",
        *[
            pl.col(names[report["mapping"][f["id"]]]).alias(f["name"])
            for f in card["features"]
        ],
    )
    accepted, dropped = [], []
    for batch in data.iter_slices(batch_size):
        control.check()
        try:
            transformed = checked_transform(model, batch)
            if not np.isfinite(transformed).all():
                raise ValueError("nonfinite")
            accepted.append(batch)
        except (ValueError, TypeError, ProjectError, OverflowError):
            if invalid == "reject":
                raise ProjectError(
                    "Geçersiz yeni kayıt; tahmin durdu. Açık drop politikasıyla yeniden önizleyin."
                ) from None
            for row in batch.iter_slices(1):
                control.check()
                try:
                    transformed = checked_transform(model, row)
                    if not np.isfinite(transformed).all():
                        raise ValueError("nonfinite")
                    accepted.append(row)
                except (ValueError, TypeError, ProjectError, OverflowError):
                    dropped.append(row["__vu_row_id"][0])
    valid = pl.concat(accepted) if accepted else data.head(0)
    outputs = []
    for batch in valid.iter_slices(batch_size):
        control.check()
        pred = model.predict(batch)
        probability = (
            model.predict_proba(batch) if card["probability_supported"] else None
        )
        decision = card["decision"]
        if decision and len(card["label_order"]) == 2 and probability is not None:
            labels = card["label_order"]
            pos = labels.index(decision["positive_class"])
            pred = np.where(
                probability[:, pos] >= decision["threshold"],
                labels[pos],
                labels[1 - pos],
            )
        out = batch.select("__vu_row_id").with_columns(pl.Series("prediction", pred))
        if probability is not None:
            for i in range(len(card["label_order"])):
                out = out.with_columns(
                    pl.Series("probability_" + str(i), probability[:, i])
                )
        learner = model.named_steps["baseline"]
        if type(learner) is ProbabilityModel and learner.q is not None:
            out = out.with_columns(
                pl.Series(
                    "prediction_set",
                    learner.prediction_sets(
                        model.named_steps["prepare"].transform(batch)
                    ),
                    dtype=pl.List(pl.String),
                )
            )
        elif (
            type(learner) is IntervalModel
            and learner.metadata["spec"]["prediction"] != "none"
        ):
            bounds, crossing = learner.intervals(
                model.named_steps["prepare"].transform(batch)
            )
            out = out.with_columns(
                pl.Series("predictive_lower", bounds[:, 0]),
                pl.Series("predictive_upper", bounds[:, 1]),
            )
        if card["method"] in ("isolation_forest", "iqr"):
            scores = -model.named_steps["baseline"].score_samples(
                model.named_steps["prepare"].transform(batch)
            )
            out = out.drop("prediction").with_columns(
                pl.Series("anomaly_score", scores),
                pl.Series("anomaly_candidate", scores > card["threshold"]),
            )
        outputs.append(out)
        control.progress(
            "Yeni veri: yalnız transform/predict, fit yok",
            min(len(outputs) * batch_size, len(valid)),
            len(valid),
        )
    if outputs:
        members = pl.concat(outputs)
    else:
        members = pl.DataFrame(
            {"__vu_row_id": pl.Series([], dtype=frame["__vu_row_id"].dtype)}
        )
        fields = (
            {"anomaly_score": pl.Float64, "anomaly_candidate": pl.Boolean}
            if card["method"] in ("iqr", "isolation_forest")
            else {
                "prediction": pl.String
                if card["label_order"]
                else pl.Int64
                if card["method"] == "kmeans"
                else pl.Float64
            }
        )
        if card["probability_supported"]:
            fields.update(
                {
                    "probability_" + str(i): pl.Float64
                    for i in range(len(card["label_order"]))
                }
            )
        learner = model.named_steps["baseline"]
        if type(learner) is ProbabilityModel and learner.q is not None:
            fields["prediction_set"] = pl.List(pl.String)
        elif (
            type(learner) is IntervalModel
            and learner.metadata["spec"]["prediction"] != "none"
        ):
            fields.update(predictive_lower=pl.Float64, predictive_upper=pl.Float64)
        members = members.with_columns(
            *[pl.Series(name, [], dtype=dtype) for name, dtype in fields.items()]
        )
    # Null results and status retain dropped records in the source output.
    used = set(frame.columns)
    for name in list(members.columns)[1:]:
        target = "vu_" + name
        while target in used:
            target = "_" + target
        used.add(target)
        members = members.rename({name: target})
    result = frame.join(
        members, on="__vu_row_id", how="left", validate="1:1", maintain_order="left"
    )
    status = "vu_prediction_status"
    while status in used:
        status = "_" + status
    dropped_set = set(dropped)
    result = result.with_columns(
        pl.Series(
            status,
            [
                "invalid_dropped" if i in dropped_set else "predicted"
                for i in frame["__vu_row_id"]
            ],
        )
    )
    if result["__vu_row_id"].to_list() != frame["__vu_row_id"].to_list():
        raise ProjectError("Tahmin RowId eşleşmesi bozuk; çıktı verilmedi.")
    return result, dict(
        preview=report,
        predicted_rows=len(valid),
        dropped_row_ids=dropped,
        label_order=card["label_order"],
        batch_size=batch_size,
        fit_calls=0,
        uncertainty=card.get("uncertainty"),
    )
