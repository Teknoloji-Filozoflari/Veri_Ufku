"""Source-bound bounded model inspection. No fit, causal claims or fairness badges."""

import importlib.metadata
import importlib.util
import itertools
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime

import numpy as np
import polars as pl
from scipy.stats import norm
from sklearn.linear_model import LinearRegression, Ridge

from veri_ufku.domain.contracts import Provenance
from veri_ufku.domain.json import parse, raw_json
from veri_ufku.modeling.baseline import FoldPreparation, numeric
from veri_ufku.modeling.families import FamilyScope
from veri_ufku.modeling.lifecycle import checked_transform, preview
from veri_ufku.modeling.uncertainty import IntervalModel
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError, uid

METHODS = (
    "permutation",
    "pdp",
    "ice",
    "local-linear",
    "shap",
    "slices",
    "fairness",
    "what-if",
    "constrained",
)
LIMITATIONS = (
    "Model açıklaması ilişki/tahmin davranışıdır; SHAP katkısı neden-sonuç değildir. "
    "Correlated features permutation önemini paylaşabilir; PDP/ICE ve SHAP background değişimleri gözlenmeyen kombinasyonlar üretir. "
    "Gözlenen aralık içinde bile extrapolation/ortak destek sorunu olabilir. "
    "Missing eğitimdeki dönüşümle işlenir; indicator ayrı etkidir, otomatik veri düzeltme yok. "
    "Background ve sample seçimi açıklamayı değiştirir; global sample bütün popülasyon değildir. "
    "Dilim keşfi çoklu arama etkisi taşır; küçük gruplar güvenilmezdir. "
    "Fairness metrikleri trade-off taşır; tek metrikle adil model rozeti veya hukuki sonuç yok. "
    "What-if ve kısıtlı aday tahmini causal counterfactual değildir; gerçekleşebilirlik/nedensel etki garantisi yok."
)


@dataclass(frozen=True)
class ExplainSpec:
    method: str = "permutation"
    features: list = field(default_factory=list)
    class_label: str = ""
    sample_rows: int = 100
    background_rows: int = 40
    seed: int = 51
    repeats: int = 3
    grid_points: int = 8
    grid: list = field(default_factory=list)
    local_row_id: str = ""
    slices: list = field(default_factory=list)
    sensitive_columns: list = field(default_factory=list)
    positive_class: str = ""
    changes: dict = field(default_factory=dict)
    constraints: dict = field(default_factory=dict)
    immutable_features: list = field(default_factory=list)
    desired_class: str = ""
    desired_min: float | None = None
    desired_max: float | None = None
    bootstrap_draws: int = 100

    @classmethod
    def from_dict(cls, value, require_backend=True):
        try:
            s = cls(**value)
        except (TypeError, ValueError):
            raise ProjectError("Açıklama tarifi alanları geçersiz.") from None
        if s.method not in METHODS:
            raise ProjectError("Desteklenmeyen model açıklaması.")
        for name, lo, hi in [
            ("sample_rows", 2, 500),
            ("background_rows", 2, 100),
            ("seed", 0, 2**31 - 1),
            ("repeats", 2, 10),
            ("grid_points", 2, 20),
            ("bootstrap_draws", 50, 200),
        ]:
            v = getattr(s, name)
            if type(v) is not int or not lo <= v <= hi:
                raise ProjectError(f"{name} bütçe sınırı {lo}..{hi}.")
        for name, limit in [
            ("features", 16),
            ("sensitive_columns", 16),
            ("immutable_features", 16),
        ]:
            v = getattr(s, name)
            if (
                not isinstance(v, list)
                or len(v) > limit
                or any(not isinstance(i, str) for i in v)
                or len(set(v)) != len(v)
            ):
                raise ProjectError(
                    "Feature/sensitive/immutable ColumnId listesi benzersiz olmalı."
                )
        for name in ("class_label", "positive_class", "desired_class", "local_row_id"):
            if not isinstance(getattr(s, name), str) or len(getattr(s, name)) > 256:
                raise ProjectError("Label/RowId alanı geçersiz.")
        if (
            not isinstance(s.grid, list)
            or len(s.grid) > 20
            or not isinstance(s.changes, dict)
            or not isinstance(s.constraints, dict)
            or len(s.changes) > 16
            or len(s.constraints) > 16
            or not isinstance(s.slices, list)
            or len(s.slices) > 8
        ):
            raise ProjectError(
                "Grid/change/constraint/slice bounded declarative alanı geçersiz."
            )
        for v in s.grid + list(s.changes.values()):
            if v is not None and (
                type(v) not in (str, int, float, bool)
                or isinstance(v, float)
                and not math.isfinite(v)
            ):
                raise ProjectError("Grid/what-if yalnız sonlu scalar değer alır.")
        for sl in s.slices:
            if (
                not isinstance(sl, dict)
                or set(sl) - {"column_id", "kind", "edges"}
                or not isinstance(sl.get("column_id"), str)
                or sl.get("kind") not in ("group", "time", "class", "range")
            ):
                raise ProjectError("Slice group/time/class/range ve ColumnId olmalı.")
            if sl["kind"] in ("range", "time"):
                edges = sl.get("edges", [])
                if (
                    not isinstance(edges, list)
                    or not 2 <= len(edges) <= 11
                    or any(
                        type(v) not in (int, float) or not math.isfinite(v)
                        for v in edges
                    )
                    or any(a >= b for a, b in zip(edges, edges[1:]))
                ):
                    raise ProjectError(
                        "Range/time slice artan2..11 sonlu sınır ister; time UTC epoch seconds."
                    )
        for v in (s.desired_min, s.desired_max):
            if v is not None and (type(v) not in (int, float) or not math.isfinite(v)):
                raise ProjectError("Aday hedef aralığı sonlu olmalı.")
        if (
            s.desired_min is not None
            and s.desired_max is not None
            and s.desired_min > s.desired_max
        ):
            raise ProjectError("Aday hedef aralığı ters.")
        if (
            require_backend
            and s.method == "shap"
            and importlib.util.find_spec("shap") is None
        ):
            raise ProjectError(
                "Optional SHAP backend yok; hesap doğrulanmadı. Otomatik indirme yok."
            )
        return s

    def data(self):
        return asdict(self)


def feature_mapping(model, card, sample):
    """Track fitted operations rather than splitting display names on underscores."""
    prep = model.named_steps["prepare"]
    features = {f["id"]: f for f in card["features"]}
    if type(prep) is FamilyScope:
        learner = model.named_steps["baseline"]
        children = learner.children_ or [learner]
        rows = []
        for child_index, child in enumerate(children):
            p = child.preparation_
            for j, name in enumerate(p.feature_names_):
                matches = [
                    ident
                    for ident in features
                    if name == "f_" + ident.removeprefix("col:").replace("-", "")
                    or name.startswith(
                        "f_" + ident.removeprefix("col:").replace("-", "") + "__"
                    )
                ]
                if len(matches) != 1:
                    raise ProjectError(
                        "Family transformed-to-original eşleme belirsiz; desteklenmiyor."
                    )
                ident = matches[0]
                rows.append(
                    dict(
                        component=child_index,
                        index=j,
                        transformed_name=name,
                        column_id=ident,
                        name=features[ident]["name"],
                        dependencies=[ident],
                    )
                )
            shape = p.transform(sample).shape
            if shape[1] != len(p.feature_names_):
                raise ProjectError("Family transformed mapping boyutu uyuşmuyor.")
        return rows
    if type(prep) is not FoldPreparation or card["preparation_spec"].get("text"):
        raise ProjectError(
            "Bu preprocessing transformed mapping adapterinde desteklenmiyor."
        )
    blocks = {}
    for i, step in enumerate(prep.plan["steps"]):
        kind = step["kind"]
        ids = step["input_column_ids"]
        if kind == "numeric":
            blocks[ids[0]] = [("numeric", [ids[0]])]
        elif kind == "calendar":
            blocks[ids[0]] = [(v, [ids[0]]) for v in ("year", "month", "weekday")]
        elif kind == "missing_indicator":
            for ident in ids:
                blocks[ident].append(("missing_indicator", [ident]))
        elif kind == "outlier_iqr_mark":
            for ident in ids:
                blocks[ident].append(("outlier_indicator", [ident]))
        elif kind == "encode_onehot":
            op = prep.steps_[str(i)]
            blocks[ids[0]] = [
                ("category_" + str(j), [ids[0]]) for j in range(len(op.categories_[0]))
            ]
        elif kind == "encode_ordinal":
            blocks[ids[0]] = [("ordinal", [ids[0]])]
        elif kind == "impute_joint":
            # Joint imputation can use every selected input; do not claim isolated source attribution.
            for ident in ids:
                blocks[ident] = [(name, list(ids)) for name, _ in blocks[ident]]
        elif kind in (
            "impute_numeric",
            "impute_category",
            "standard_scale",
            "no_scaling",
            "select_variance",
        ):
            pass
        else:
            raise ProjectError(
                "Bu fitted dönüşüm için mapping adapter doğrulanmadı: " + kind
            )
    entries = []
    for ident in prep.spec.features:
        if ident not in blocks:
            raise ProjectError("Özellik transformed eşlemesi eksik.")
        for label, dependencies in blocks[ident]:
            entries.append(
                dict(
                    component=0,
                    index=len(entries),
                    transformed_name=ident + "__" + label,
                    column_id=ident,
                    name=features[ident]["name"],
                    dependencies=dependencies,
                )
            )
    if hasattr(prep, "selection_"):
        mask = prep.selection_.get_support()
        if len(mask) != len(entries):
            raise ProjectError("Selection mapping mask boyutu uyuşmuyor.")
        entries = [e for e, keep in zip(entries, mask, strict=True) if keep]
    for j, e in enumerate(entries):
        e["index"] = j
    if checked_transform(model, sample).shape[1] != len(entries):
        raise ProjectError(
            "Transformed feature mapping boyutu gerçek dönüşümle uyuşmuyor."
        )
    return entries


class PredictionBudget:
    def __init__(self, control, maximum=300000):
        self.control = control
        self.maximum = maximum
        self.rows = 0
        self.calls = 0

    def check(self, n):
        self.control.check()
        if self.rows + n > self.maximum:
            raise ProjectError(
                "Explanation ComputeBudget prediction row-pass sınırı aşıldı; açık sample/grid azaltın."
            )
        self.rows += n
        self.calls += 1


def prediction(model, card, frame, budget):
    budget.check(len(frame))
    pred = np.asarray(model.predict(frame))
    if (
        card["purpose"] == "classification"
        and card["decision"]
        and len(card["label_order"]) == 2
        and card["probability_supported"]
    ):
        probability = model.predict_proba(frame)
        labels = card["label_order"]
        index = labels.index(card["decision"]["positive_class"])
        threshold = card["decision"]["threshold"]
        pred = np.where(
            probability[:, index] >= threshold, labels[index], labels[1 - index]
        )
    return pred


def response(model, card, frame, spec, budget):
    budget.check(len(frame))
    if card["purpose"] == "classification":
        if (
            not card["probability_supported"]
            or spec.class_label not in card["label_order"]
        ):
            raise ProjectError(
                "PDP/ICE/local/SHAP için desteklenen proba ve açık class label gerekir."
            )
        p = np.asarray(model.predict_proba(frame))
        if (
            p.shape != (len(frame), len(card["label_order"]))
            or not np.isfinite(p).all()
        ):
            raise ProjectError("Response probability eşlemesi geçersiz.")
        return p[:, card["label_order"].index(spec.class_label)]
    values = np.asarray(model.predict(frame), dtype=float)
    if values.shape != (len(frame),) or not np.isfinite(values).all():
        raise ProjectError("Sayısal response tek hedef/sonlu olmalı.")
    return values


def select_sample(frame, count, seed):
    if len(frame) <= count:
        return frame, False
    indices = np.sort(
        np.random.default_rng(seed).choice(len(frame), count, replace=False)
    )
    return frame[indices.tolist()], True


def epoch(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return (v if v.tzinfo else v.replace(tzinfo=UTC)).timestamp()
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day, tzinfo=UTC).timestamp()
    raise ProjectError(
        "Time slice Date/Datetime kolon ister; numeric epoch kolonunu range olarak seçin."
    )


def scalar(v):
    if v is None or isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v if type(v) in (str, int, float, bool) else str(v)


def diagnostic_columns(sample, background, card):
    out = []
    numeric_features = []
    for f in card["features"]:
        name = f["name"]
        vals = sample[name].to_list()
        ref = background[name].to_list()
        entry = dict(
            column_id=f["id"],
            missing_n=sum(
                v is None or isinstance(v, float) and not math.isfinite(v) for v in vals
            ),
            outside_background_n=0,
            unknown_category_n=0,
        )
        if sample.schema[name].is_numeric():
            a = np.array(
                [float(v) for v in vals if v is not None and math.isfinite(float(v))]
            )
            b = np.array(
                [float(v) for v in ref if v is not None and math.isfinite(float(v))]
            )
            if len(b):
                entry.update(
                    background_min=float(b.min()),
                    background_max=float(b.max()),
                    outside_background_n=int(np.sum((a < b.min()) | (a > b.max()))),
                )
            numeric_features.append(f)
        else:
            known = {str(v) for v in ref if v is not None}
            entry["unknown_category_n"] = sum(
                v is not None and str(v) not in known for v in vals
            )
        out.append(entry)
    correlations = []
    for a, b in itertools.combinations(numeric_features, 2):
        pairs = [
            (float(x), float(y))
            for x, y in zip(sample[a["name"]], sample[b["name"]], strict=True)
            if x is not None
            and y is not None
            and math.isfinite(float(x))
            and math.isfinite(float(y))
        ]
        if len(pairs) >= 4:
            v = np.asarray(pairs)
            if min(v.std(axis=0)) > 0:
                r = float(np.corrcoef(v.T)[0, 1])
                if abs(r) >= 0.8:
                    correlations.append(
                        dict(column_ids=[a["id"], b["id"]], pearson=r, n=len(pairs))
                    )
    return dict(
        features=out,
        correlated_pairs=correlations,
        joint_support="not established; observed marginal range is not evidence of feasible combinations",
    )


def numeric_grid(feature, sample, background, spec):
    name = feature["name"]
    values = [
        v
        for v in background[name].to_list()
        if v is not None and (not isinstance(v, float) or math.isfinite(v))
    ]
    if not values:
        raise ProjectError("Background seçili özellik tamamen eksik; grid üretilmedi.")
    is_numeric = background.schema[name].is_numeric()
    if spec.grid:
        grid = spec.grid
    elif is_numeric:
        grid = np.unique(
            np.quantile(
                np.array(values, dtype=float),
                np.linspace(0.05, 0.95, spec.grid_points),
                method="linear",
            )
        ).tolist()
        if background.schema[name].is_integer():
            grid = sorted(set(int(round(v)) for v in grid))
    else:
        grid = sorted(set(str(v) for v in values))
        if len(grid) > 20:
            raise ProjectError("Kategori grid20 üstünde; açık grid seçin.")
    if is_numeric and any(
        type(v) not in (int, float) or not math.isfinite(v) for v in grid
    ):
        raise ProjectError("Numeric grid sonlu sayı olmalı.")
    if not is_numeric and any(str(v) not in set(str(x) for x in values) for v in grid):
        raise ProjectError("Kategori grid background içinde gözlenmiş değer ister.")
    return grid, is_numeric


def changed_frame(frame, updates, card):
    names = {f["id"]: f["name"] for f in card["features"]}
    if set(updates) - set(names):
        raise ProjectError("What-if change ColumnId model özelliklerinden olmalı.")
    out = frame
    for ident, v in updates.items():
        name = names[ident]
        try:
            out = out.with_columns(
                pl.Series(name, [v] * len(out), dtype=out.schema[name], strict=True)
            )
        except (TypeError, ValueError, pl.exceptions.PolarsError):
            raise ProjectError(
                "Grid/change model source türüyle uyuşmuyor; sessiz cast yok."
            ) from None
    return out


def local_linear(model, card, sample, background, mapping, budget, spec):
    prep = model.named_steps["prepare"]
    base = model.named_steps["baseline"]
    if type(base) is IntervalModel:
        base = base.base
    if (
        card["purpose"] != "regression"
        or type(prep) is not FoldPreparation
        or type(base) not in (LinearRegression, Ridge)
        or any(len(m["dependencies"]) != 1 for m in mapping)
    ):
        raise ProjectError(
            "Exact local-linear yalnız FoldPreparation +linear/Ridge regression; joint imputation/family/ensemble desteklenmiyor."
        )
    row = sample.filter(pl.col("__vu_row_id") == spec.local_row_id)
    if len(row) != 1:
        raise ProjectError("Local RowId açık seçilmiş evaluation içinde bulunmalı.")
    x = checked_transform(model, row)
    bg = checked_transform(model, background)
    coef = np.asarray(base.coef_)
    if coef.shape != (len(mapping),):
        raise ProjectError("Local linear coefficient/mapping boyutu uyuşmuyor.")
    reference = bg.mean(axis=0)
    baseline = float(base.intercept_ + reference @ coef)
    contributions = (x[0] - reference) * coef
    target = float(response(model, card, row, spec, budget)[0])
    if not math.isclose(
        baseline + float(contributions.sum()), target, rel_tol=1e-9, abs_tol=1e-9
    ):
        raise ProjectError("Local additive reference eşitliği başarısız.")
    by_id = {}
    for m, v in zip(mapping, contributions, strict=True):
        by_id[m["column_id"]] = by_id.get(m["column_id"], 0) + float(v)
    return dict(
        kind="exact linear additive deviation from transformed background mean; not SHAP or causality",
        row_id=spec.local_row_id,
        baseline=baseline,
        prediction=target,
        contributions=[dict(column_id=k, value=v) for k, v in by_id.items()],
        transformed_contributions=[
            dict(index=m["index"], column_id=m["column_id"], value=float(v))
            for m, v in zip(mapping, contributions, strict=True)
        ],
        identity_error=baseline + float(contributions.sum()) - target,
    )


def shap_values(model, card, sample, background, mapping, spec, budget):
    if importlib.util.find_spec("shap") is None:
        raise ProjectError("Optional SHAP ortamı yok/notvalidated.")
    # Reviewed backend only. A future environment/version needs its own real reference acceptance.
    version = importlib.metadata.version("shap")
    if version not in ("0.51.0",):
        raise ProjectError(
            "SHAP sürümü doğrulanmış adapter sınırında değil; compute kapalı."
        )
    import shap

    prep = model.named_steps["prepare"]
    base = model.named_steps["baseline"]
    if (
        type(prep) is not FoldPreparation
        or len(mapping) > 8
        or len(sample) > 20
        or any(len(m["dependencies"]) != 1 for m in mapping)
    ):
        raise ProjectError(
            "Exact SHAP dense8transformedfeatures/20rows/FoldPreparation; joint imputation kapalı."
        )
    X = checked_transform(model, sample)
    B = checked_transform(model, background)

    def callback(values):
        budget.check(len(values))
        if card["purpose"] == "classification":
            if (
                not hasattr(base, "predict_proba")
                or spec.class_label not in card["label_order"]
            ):
                raise ProjectError("SHAP proba/classlabel gerekli.")
            return base.predict_proba(values)[
                :, card["label_order"].index(spec.class_label)
            ]
        return base.predict(values)

    explainer = shap.ExactExplainer(
        callback, shap.maskers.Independent(B, max_samples=len(B))
    )
    result = explainer(X, max_evals=2 ** len(mapping), batch_size=64)
    v = np.asarray(result.values)
    baseline = np.asarray(result.base_values)
    target = response(model, card, sample, spec, budget)
    if (
        v.shape != (len(sample), len(mapping))
        or baseline.shape != (len(sample),)
        or not np.isfinite(v).all()
        or not np.allclose(v.sum(axis=1) + baseline, target, rtol=1e-7, atol=1e-7)
    ):
        raise ProjectError("SHAP additive reference/shape başarısız.")
    grouped = {
        ident: np.zeros(len(sample)) for ident in {m["column_id"] for m in mapping}
    }
    for j, m in enumerate(mapping):
        grouped[m["column_id"]] += v[:, j]
    return dict(
        backend="shap",
        version=version,
        algorithm="ExactExplainer; independent empirical transformed background; NOT conditional or causal SHAP",
        approximation="exact subset enumeration for finite selected background; population/background approximation remains",
        global_values=[
            dict(column_id=k, mean_abs=float(np.mean(abs(a))))
            for k, a in grouped.items()
        ],
        local=[
            dict(
                row_id=rid,
                baseline=float(baseline[i]),
                prediction=float(target[i]),
                contributions=[
                    dict(column_id=k, value=float(a[i])) for k, a in grouped.items()
                ],
            )
            for i, rid in enumerate(sample["__vu_row_id"])
        ],
    )


def wilson(success, n):
    if n == 0:
        return None
    z = float(norm.ppf(0.975))
    p = success / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return dict(
        lower=center - half,
        upper=center + half,
        level=0.95,
        method="Wilson; independent Bernoulli records only",
    )


def slice_metrics(actual, pred, classification, structure, draws, seed):
    n = len(actual)
    error = (pred != actual).astype(float) if classification else abs(pred - actual)
    value = float(error.mean()) if n else None
    uncertainty = None
    if structure == "independent" and n >= 2:
        if classification:
            uncertainty = wilson(int(np.sum(pred == actual)), n)
        else:
            rng = np.random.default_rng(seed)
            means = [float(error[rng.integers(0, n, n)].mean()) for _ in range(draws)]
            lo, hi = np.quantile(means, [0.025, 0.975], method="linear")
            uncertainty = dict(
                lower=float(lo),
                upper=float(hi),
                level=0.95,
                method="iid percentile bootstrap MAE; exploratory not simultaneous",
                draws=draws,
                seed=seed,
            )
    return dict(
        n=n,
        metric="accuracy" if classification else "mae",
        value=1 - value if classification and n else value,
        uncertainty=uncertainty,
        uncertainty_status="conditional independent-record approximation"
        if uncertainty
        else "unavailable: too small or group/time dependence; no iid CI fabricated",
        small_group=n < 30,
        note="Small n and repeated slice searches are unreliable; no adjusted simultaneous inference or fairness badge",
    )


def slices_report(sample, actual, pred, card, spec):
    columns = {c["id"]: c["name"] for c in card["columns"]}
    classification = card["purpose"] == "classification"
    structure = (
        card["split"]["structure"]
        if "structure" in card["split"]
        else card["split"].get("method", "random")
    )
    structure = (
        "independent"
        if structure in ("random", "stratified", "independent")
        else structure
    )
    results = []
    selections = spec.slices or [
        dict(
            column_id=card["target"]["id"],
            kind="class" if classification else "range",
            **(
                {}
                if classification
                else dict(edges=[float(np.min(actual)) - 1, float(np.max(actual)) + 1])
            ),
        )
    ]
    for sl in selections:
        if sl["column_id"] not in columns:
            raise ProjectError("Slice ColumnId source içinde olmalı.")
        name = columns[sl["column_id"]]
        values = sample[name].to_list()
        kind = sl["kind"]
        if kind == "class" and sl["column_id"] != card["target"]["id"]:
            raise ProjectError("Class slice model target ColumnId ister.")
        if kind == "time":
            values = [epoch(v) for v in values]
        elif kind == "range":
            if not sample.schema[name].is_numeric():
                raise ProjectError("Range slice numeric kolon ister.")
            values = [float(v) if v is not None else None for v in values]
        masks = []
        if kind in ("time", "range"):
            edges = sl["edges"]
            for i, (lo, hi) in enumerate(zip(edges, edges[1:])):
                mask = np.array(
                    [
                        v is not None
                        and math.isfinite(v)
                        and v >= lo
                        and (v <= hi if i == len(edges) - 2 else v < hi)
                        for v in values
                    ]
                )
                masks.append(
                    (dict(lower=lo, upper=hi, last_closed=i == len(edges) - 2), mask)
                )
            masks.append(
                (
                    "outside_declared_ranges",
                    np.array(
                        [
                            v is not None
                            and math.isfinite(v)
                            and (v < edges[0] or v > edges[-1])
                            for v in values
                        ]
                    ),
                )
            )
        else:
            distinct = sorted(set(str(v) for v in values if v is not None))
            if len(distinct) > 20:
                raise ProjectError(
                    "Slice kategori20 üstünde; açık yeni veri daraltması gerekir."
                )
            masks = [
                (v, np.array([x is not None and str(x) == v for x in values]))
                for v in distinct
            ]
        masks.append(
            (
                "missing",
                np.array(
                    [
                        v is None or isinstance(v, float) and not math.isfinite(v)
                        for v in values
                    ]
                ),
            )
        )
        for label, mask in masks:
            stats = slice_metrics(
                actual[mask],
                pred[mask],
                classification,
                structure,
                spec.bootstrap_draws,
                spec.seed,
            )
            results.append(
                dict(
                    column_id=sl["column_id"],
                    kind=kind,
                    label=label,
                    row_ids=sample.filter(pl.Series(mask))["__vu_row_id"].to_list(),
                    **stats,
                )
            )
    return dict(
        slices=results,
        slice_count=len(results),
        multiple_search_warning="Exploratory multiple slice search; small n, no simultaneous CI or correction claimed",
        structure=structure,
    )


def fairness_report(sample, actual, pred, card, spec):
    if (
        card["purpose"] != "classification"
        or len(card["label_order"]) != 2
        or spec.positive_class not in card["label_order"]
        or not spec.sensitive_columns
    ):
        raise ProjectError(
            "Fairness binary classification +explicit positive class/sensitive ColumnIds ister; otomatik korunan nitelik seçimi yok."
        )
    names = {c["id"]: c["name"] for c in card["columns"]}
    if (
        set(spec.sensitive_columns) - set(names)
        or card["target"]["id"] in spec.sensitive_columns
    ):
        raise ProjectError(
            "Hassas kaynak nitelikleri açık seçilmeli; hedef sensitive olamaz."
        )
    groups = []
    iid = card["split"]["method"] in ("random", "stratified")
    for ident in spec.sensitive_columns:
        values = sample[names[ident]].to_list()
        levels = sorted(set(str(v) for v in values if v is not None))
        if len(levels) > 20:
            raise ProjectError(
                "Fairness sensitive groups20 üstünde; continuous attribute için açık kategorileştirilmiş sürüm gerekir."
            )
        for label in levels + [None]:
            mask = np.array(
                [
                    v is None if label is None else v is not None and str(v) == label
                    for v in values
                ]
            )
            a = actual[mask] == spec.positive_class
            p = pred[mask] == spec.positive_class
            n = len(a)
            tp = int(np.sum(a & p))
            fp = int(np.sum(~a & p))
            fn = int(np.sum(a & ~p))
            tn = int(np.sum(~a & ~p))
            rates = {
                k: (s / d if d else None)
                for k, s, d in [
                    ("selection_rate", tp + fp, n),
                    ("tpr", tp, tp + fn),
                    ("fpr", fp, fp + tn),
                    ("precision", tp, tp + fp),
                    ("base_rate", tp + fn, n),
                ]
            }
            intervals = {
                k: wilson(s, d) if iid else None
                for k, s, d in [
                    ("selection_rate", tp + fp, n),
                    ("tpr", tp, tp + fn),
                    ("fpr", fp, fp + tn),
                    ("precision", tp, tp + fp),
                ]
            }
            groups.append(
                dict(
                    column_id=ident,
                    label=label,
                    n=n,
                    tp=tp,
                    fp=fp,
                    fn=fn,
                    tn=tn,
                    **rates,
                    intervals=intervals,
                    small_group=n < 30,
                    row_ids=sample.filter(pl.Series(mask))["__vu_row_id"].to_list(),
                )
            )
    disparities = []
    for ident in spec.sensitive_columns:
        rows = [g for g in groups if g["column_id"] == ident and g["n"]]
        differences = {}
        for metric in ("selection_rate", "tpr", "fpr", "precision"):
            vals = [g[metric] for g in rows if g[metric] is not None]
            differences[metric + "_max_minus_min"] = (
                max(vals) - min(vals) if len(vals) >= 2 else None
            )
        disparities.append(
            dict(
                column_id=ident,
                demographic_parity_difference=differences[
                    "selection_rate_max_minus_min"
                ],
                equal_opportunity_difference=differences["tpr_max_minus_min"],
                equalized_odds_difference=max(
                    differences["tpr_max_minus_min"], differences["fpr_max_minus_min"]
                )
                if differences["tpr_max_minus_min"] is not None
                and differences["fpr_max_minus_min"] is not None
                else None,
                predictive_parity_difference=differences["precision_max_minus_min"],
            )
        )
    return dict(
        groups=groups,
        disparities=disparities,
        positive_class=spec.positive_class,
        uncertainty="Wilson iid only, descriptive if group/time; no disparity CI or simultaneous guarantee",
        trade_off="Selection parity, error-rate parity and predictive parity can conflict with differing base rates; context and cost matter; no fair badge",
        sensitive_selection="explicit user ColumnIds only; no inference",
        intersectional="separate per attribute; intersectional fairness not evaluated",
    )


def what_if(model, card, sample, background, spec, budget):
    row = sample.filter(pl.col("__vu_row_id") == spec.local_row_id)
    if len(row) != 1:
        raise ProjectError("What-if local RowId evaluation havuzunda olmalı.")
    changed = changed_frame(row, spec.changes, card)
    return dict(
        kind="what-if model prediction; not causal counterfactual",
        row_id=spec.local_row_id,
        changes=spec.changes,
        original=str(prediction(model, card, row, budget)[0])
        if card["purpose"] == "classification"
        else float(prediction(model, card, row, budget)[0]),
        modified=str(prediction(model, card, changed, budget)[0])
        if card["purpose"] == "classification"
        else float(prediction(model, card, changed, budget)[0]),
        diagnostics=diagnostic_columns(changed, background, card),
        feasibility="not established; no causal effect guarantee",
    )


def constrained(model, card, sample, background, spec, budget):
    ids = {f["id"] for f in card["features"]}
    immutable = set(spec.immutable_features)
    mutable = set(spec.constraints)
    if (
        not immutable
        or immutable & mutable
        or immutable | mutable != ids
        or not mutable
        or spec.changes
    ):
        raise ProjectError(
            "Kısıtlı aday tüm özellikleri explicit immutable veya constraint-domain olarak ister; immutable boş/çakışma/eksik reddedilir."
        )
    names = {f["id"]: f["name"] for f in card["features"]}
    domains = []
    for ident, rule in spec.constraints.items():
        if (
            not isinstance(rule, dict)
            or set(rule) != {"values", "direction", "cost"}
            or rule["direction"] not in ("any", "increase", "decrease")
            or not isinstance(rule["values"], list)
            or not 1 <= len(rule["values"]) <= 10
            or type(rule["cost"]) not in (int, float)
            or not math.isfinite(rule["cost"])
            or rule["cost"] <= 0
        ):
            raise ProjectError(
                "Constraint finite values1..10/direction/cost>0 zorunlu; kod değil declarative domain."
            )
        domains.append(rule["values"])
    size = math.prod(len(v) for v in domains)
    if size > 100:
        raise ProjectError("Kısıtlı finite aday önkontrol100 üstünde; domain daraltın.")
    row = sample.filter(pl.col("__vu_row_id") == spec.local_row_id)
    if len(row) != 1:
        raise ProjectError("Constrained RowId evaluation havuzunda olmalı.")
    if card["purpose"] == "classification":
        if spec.desired_class not in card["label_order"]:
            raise ProjectError("Aday hedef sınıfı açık seçin.")
    elif spec.desired_min is None or spec.desired_max is None:
        raise ProjectError("Sayısal aday desired_min/max açık ister.")
    candidates = []
    skipped = 0
    for values in itertools.product(*domains):
        updates = dict(zip(spec.constraints, values, strict=True))
        cost = 0.0
        valid = True
        for ident, v in updates.items():
            original = row[names[ident]][0]
            rule = spec.constraints[ident]
            if (
                original is None
                or v is None
                or type(v) not in (str, int, float, bool)
                or isinstance(v, float)
                and not math.isfinite(v)
            ):
                raise ProjectError("Kısıtlı missing/invalid value desteklenmiyor.")
            if row.schema[names[ident]].is_numeric():
                bg = [
                    float(x)
                    for x in background[names[ident]]
                    if x is not None and math.isfinite(float(x))
                ]
                if type(v) not in (int, float) or not bg or not min(bg) <= v <= max(bg):
                    raise ProjectError(
                        "Constraint numeric değer background observed range içinde olmalı."
                    )
                if (
                    rule["direction"] == "increase"
                    and v < original
                    or rule["direction"] == "decrease"
                    and v > original
                ):
                    valid = False
                cost += (
                    rule["cost"] * abs(v - float(original)) / (max(bg) - min(bg) or 1)
                )
            else:
                if rule["direction"] != "any" or str(v) not in {
                    str(x) for x in background[names[ident]]
                }:
                    raise ProjectError(
                        "Kategori constraint observed background ve direction any ister."
                    )
                cost += rule["cost"] * int(str(v) != str(original))
        if not valid:
            skipped += 1
            continue
        modified = changed_frame(row, updates, card)
        if any(modified[names[i]][0] != row[names[i]][0] for i in immutable):
            raise ProjectError("Immutable feature değişti; aday reddedildi.")
        value = prediction(model, card, modified, budget)[0]
        match = (
            str(value) == spec.desired_class
            if card["purpose"] == "classification"
            else spec.desired_min <= float(value) <= spec.desired_max
        )
        if match:
            candidates.append(
                dict(
                    changes=updates,
                    cost=float(cost),
                    prediction=str(value)
                    if card["purpose"] == "classification"
                    else float(value),
                )
            )
    candidates.sort(key=lambda v: v["cost"])
    return dict(
        kind="bounded constrained what-if candidate search; not causal counterfactual",
        row_id=spec.local_row_id,
        domain_size=size,
        direction_skipped=skipped,
        matching_count=len(candidates),
        candidates=candidates[:10],
        immutable_features=spec.immutable_features,
        constraints=spec.constraints,
        feasibility="not established; declared domain/immutability constraints only; no causal/real-world actionable guarantee",
        status="candidates" if candidates else "no_candidate_in_declared_finite_domain",
    )


def calculate(
    model,
    card,
    frame,
    background,
    source,
    background_source,
    value,
    control,
    package_fingerprint,
):
    spec = ExplainSpec.from_dict(value)
    if card["purpose"] not in ("regression", "classification") or not card["split"]:
        raise ProjectError(
            "Açıklama adapter supervised safe model +stored validation split ister."
        )
    if (
        source["version_id"] != card["dataset_version"]
        or source["fingerprint"] != card["snapshot_fingerprint"]
        or background_source["version_id"] != card["dataset_version"]
        or background_source["fingerprint"] != card["snapshot_fingerprint"]
    ):
        raise ProjectError(
            "Bu bounded adapter evaluation/model-source ve background aynı immutable training-source snapshot ister; yeni veri/background mapping ayrı desteklenmiyor."
        )
    if len(frame) > 5000 or len(card["features"]) > 16:
        raise ProjectError(
            "Explanation preflight5000source rows/16original features; explicit separate dataset needed."
        )
    if card["fit_scope"].startswith("development_train_plus_validation"):
        raise ProjectError(
            "Final refitted modelde bağımsız validation kalmadı; development paketi seçin. Final test burada tekrar açılmaz."
        )
    # Always exclude fit, calibration and final test; never a second test ledger.
    ids = card["split"]["membership"]["validation"]
    bg_ids = card["fit_row_ids"]
    eligible = frame.filter(pl.col("__vu_row_id").is_in(ids))
    bg = background.filter(pl.col("__vu_row_id").is_in(bg_ids))
    if len(eligible) != len(ids) or len(bg) != len(bg_ids):
        raise ProjectError(
            "Evaluation/background RowId membership source ile uyuşmuyor."
        )
    report = preview(
        model,
        card,
        eligible,
        source["columns"],
        semantics=source.get("semantic_metadata"),
        control=control,
    )
    if report["blockers"] or report["invalid_rows"]:
        raise ProjectError(
            "Explanation geçersiz kayıtları sessiz dışlamaz; önce model feature/invalid source sorununu inceleyin."
        )
    sample, sampled = select_sample(eligible, spec.sample_rows, spec.seed)
    bg, bg_sampled = select_sample(bg, spec.background_rows, spec.seed + 1)
    if spec.local_row_id and spec.local_row_id not in sample["__vu_row_id"].to_list():
        row = eligible.filter(pl.col("__vu_row_id") == spec.local_row_id)
        if len(row) != 1:
            raise ProjectError(
                "Local RowId validation içinde olmalı; final veya training row açıklama hedefi yapılamaz."
            )
        sample = pl.concat([sample.head(spec.sample_rows - 1), row]).unique(
            "__vu_row_id", maintain_order=True
        )
    features = {f["id"]: f for f in card["features"]}
    selected = spec.features or list(features)
    if set(selected) - set(features):
        raise ProjectError("Seçili feature ColumnId model kartında olmalı.")
    if spec.method in ("pdp", "ice") and len(selected) != 1:
        raise ProjectError("PDP/ICE tek original feature seçimi ister.")
    mapping = feature_mapping(model, card, sample.head(2))
    budget = PredictionBudget(control)
    required = (
        (len(sample) * len(selected) * spec.repeats + len(sample))
        if spec.method == "permutation"
        else len(sample) * max(spec.grid_points, len(spec.grid))
        if spec.method in ("pdp", "ice")
        else len(sample)
    )
    if (
        required > budget.maximum
        or len(sample) * max(1, len(mapping)) * 64 > control.budget.ram_bytes // 4
    ):
        raise ProjectError(
            "Explanation sample/grid/transform bütçesi aşıldı; açık seçim küçültün."
        )
    if (
        spec.method == "shap"
        and len(sample) * len(bg) * (2 ** len(mapping)) > budget.maximum
    ):
        raise ProjectError(
            "Exact SHAP preflight prediction row-pass bütçesi aşıldı; sample/background/feature azaltın."
        )
    columns = {c["id"]: c["name"] for c in source["columns"]}
    if set(spec.sensitive_columns) - set(columns):
        raise ProjectError("Sensitive ColumnId source içinde olmalı.")
    target = card["target"]
    target_name = target["name"]
    y = sample[target_name].to_list()
    classification = card["purpose"] == "classification"
    if classification:
        y = np.array([str(v) for v in y])
        if not set(y) <= set(card["label_order"]):
            raise ProjectError("Slice/importance unseen target class engellendi.")
    else:
        y = numeric(y, model.named_steps["prepare"].spec).ravel()
    if (
        not classification
        and not np.isfinite(y).all()
        or any(v is None for v in sample[target_name])
    ):
        raise ProjectError("Evaluation target missing/nonfinite; sessiz dışlama yok.")
    pred = prediction(model, card, sample, budget)
    output = {}
    if spec.method == "permutation":

        def score(pred):
            return (
                float(np.mean(pred == y))
                if classification
                else -float(np.mean(abs(pred - y)))
            )

        base = score(pred)
        rng = np.random.default_rng(spec.seed)
        values = []
        for ident in selected:
            f = features[ident]
            losses = []
            for _ in range(spec.repeats):
                changed = sample.with_columns(
                    sample[f["name"]].gather(rng.permutation(len(sample)).tolist())
                )
                losses.append(base - score(prediction(model, card, changed, budget)))
            values.append(
                dict(
                    column_id=ident,
                    name=f["name"],
                    mean=float(np.mean(losses)),
                    std=float(np.std(losses, ddof=1)),
                    repeat_values=losses,
                )
            )
        output = dict(
            permutation=dict(
                metric="accuracy" if classification else "negative_mae",
                baseline=base,
                values=values,
                repeats=spec.repeats,
                uncertainty="shuffle repeat std ddof1; not population confidence interval",
            )
        )
    elif spec.method in ("pdp", "ice"):
        f = features[selected[0]]
        grid, is_numeric = numeric_grid(f, sample, bg, spec)
        matrix = []
        for v in grid:
            matrix.append(
                response(
                    model, card, changed_frame(sample, {f["id"]: v}, card), spec, budget
                ).tolist()
            )
        a = np.array(matrix)
        out_of_range = 0
        if is_numeric:
            ref = [
                float(v)
                for v in bg[f["name"]]
                if v is not None and math.isfinite(float(v))
            ]
            out_of_range = sum(v < min(ref) or v > max(ref) for v in grid)
        output = dict(
            pdp=dict(
                column_id=f["id"],
                grid=grid,
                mean=a.mean(axis=1).tolist(),
                numeric_axis=is_numeric,
                n=len(sample),
                grid_method="explicit"
                if spec.grid
                else "background .05.. .95 quantiles/observed categories",
                outside_background_grid_n=out_of_range,
            ),
            ice=[
                dict(row_id=rid, values=a[:, j].tolist())
                for j, rid in enumerate(sample["__vu_row_id"])
            ]
            if spec.method == "ice"
            else [],
        )
    elif spec.method == "local-linear":
        output = dict(
            local=local_linear(model, card, sample, bg, mapping, budget, spec)
        )
    elif spec.method == "shap":
        output = dict(shap=shap_values(model, card, sample, bg, mapping, spec, budget))
    elif spec.method == "slices":
        output = slices_report(sample, y, pred, card, spec)
    elif spec.method == "fairness":
        output = dict(fairness=fairness_report(sample, y, pred, card, spec))
    elif spec.method == "what-if":
        output = dict(what_if=what_if(model, card, sample, bg, spec, budget))
    elif spec.method == "constrained":
        output = dict(constrained=constrained(model, card, sample, bg, spec, budget))
    control.check()
    sampleids = sample["__vu_row_id"].to_list()
    bgids = bg["__vu_row_id"].to_list()
    provenance = dict(
        model_run_id=card["run_id"],
        model_package_fingerprint=package_fingerprint,
        dataset_version=source["version_id"],
        snapshot_fingerprint=source["fingerprint"],
        source_snapshot_id=source["source_snapshot_id"],
        background_dataset_version=background_source["version_id"],
        background_snapshot_fingerprint=background_source["fingerprint"],
        background_row_ids=bgids,
        evaluation_row_ids=sampleids,
        scope="validation only; already used for model/threshold selection; exploratory; final test not read",
        seed=spec.seed,
        sampled=sampled,
        eligible_n=len(eligible),
        n=len(sample),
        background_sampled=bg_sampled,
        background_eligible_n=len(bg_ids),
        background_n=len(bg),
        fit_calls=0,
        prediction_calls=budget.calls,
        prediction_row_passes=budget.rows,
        prediction_row_pass_budget=budget.maximum,
        prior_test_use_ids=source.get("prior_test_use_ids", []),
        sensitive_columns=spec.sensitive_columns,
        packages={
            name: importlib.metadata.version(name)
            for name in ("scikit-learn", "numpy", "polars")
        },
    )
    common = Provenance(
        provenance_id="provenance:" + uid(),
        dataset_versions=(source["version_id"],),
        config_revision=source.get("config_revision", 0),
        capability_id="model.explain." + spec.method,
        parameters_hash=digest(spec.data()),
        environment=tuple(provenance["packages"].items()),
        created_at=datetime.now(UTC).isoformat(),
        scope=provenance["scope"],
        seed=spec.seed,
        seed_reason="explicit deterministic evaluation/background sample and permutations",
        source_snapshot_ids=(source["source_snapshot_id"],),
    )
    provenance["common"] = asdict(common)
    provenance["compute_budget"] = asdict(control.budget)
    result = dict(
        schema="ExplanationRun/v1",
        run_id="explanation:" + uid(),
        status="completed",
        created_at=datetime.now(UTC).isoformat(),
        spec=spec.data(),
        card=card,
        provenance=provenance,
        prediction_records=[
            dict(
                row_id=rid,
                actual=str(y[i]) if classification else float(y[i]),
                prediction=str(pred[i]) if classification else float(pred[i]),
            )
            for i, rid in enumerate(sampleids)
        ],
        feature_mapping=mapping,
        diagnostics=diagnostic_columns(sample, bg, card),
        limitations=LIMITATIONS,
        **output,
    )
    result = parse(raw_json(result))
    result["identity"] = "explanation:" + digest(
        {k: v for k, v in result.items() if k != "identity"}
    )
    return result


def redacted_export(result):
    """Fail-closed export: never export source rows, IDs, sensitive labels/values or mappings."""
    sensitive = set(result["spec"]["sensitive_columns"])
    features = {f["id"]: f for f in result["card"]["features"]}
    safe = dict(
        schema="ExplanationExport/v1",
        method=result["spec"]["method"],
        created_at=result["created_at"],
        limitations=LIMITATIONS,
        scope=result["provenance"]["scope"],
        n=result["provenance"]["n"],
        eligible_n=result["provenance"]["eligible_n"],
        sampled=result["provenance"]["sampled"],
        background_n=result["provenance"]["background_n"],
        seed=result["spec"]["seed"],
        redaction="Source record/RowIds, model card, raw rows, sensitive feature names/values/labels/contributions, sensitive group metrics, what-if/constraint values omitted; aggregate small cells suppressed n<30. Not an anonymity guarantee.",
        model_package_sha256=result["provenance"]["model_package_fingerprint"][
            "sha256"
        ],
        data_fingerprint=result["provenance"]["snapshot_fingerprint"],
    )
    if "permutation" in result:
        safe["permutation"] = dict(
            result["permutation"],
            values=[
                {k: v for k, v in r.items() if k != "column_id"}
                for r in result["permutation"]["values"]
                if r["column_id"] not in sensitive
            ],
        )
    if "pdp" in result and result["pdp"]["column_id"] not in sensitive:
        safe["pdp"] = {k: v for k, v in result["pdp"].items() if k != "column_id"}
    if "local" in result and not sensitive:
        safe["local"] = {
            k: v
            for k, v in result["local"].items()
            if k not in ("row_id", "transformed_contributions")
        }
        safe["local"]["contributions"] = [
            dict(feature=features[v["column_id"]]["name"], value=v["value"])
            for v in safe["local"]["contributions"]
        ]
    if "slices" in result:
        safe["slices"] = [
            {k: v for k, v in r.items() if k not in ("row_ids", "column_id")}
            for r in result["slices"]
            if r["column_id"] not in sensitive and r["n"] >= 30
        ]
    if "fairness" in result:
        safe["fairness"] = dict(
            trade_off=result["fairness"]["trade_off"],
            redacted="Sensitive group labels, counts, rates and disparities omitted; review inside project only.",
        )
    if "what_if" in result or "constrained" in result:
        safe["scenario"] = dict(
            kind="bounded model scenario; not causal",
            redacted="Individual predictions/changes/constraints/immutable identities omitted.",
        )
    if "shap" in result and not sensitive:
        safe["shap_global"] = [
            dict(feature=features[v["column_id"]]["name"], mean_abs=v["mean_abs"])
            for v in result["shap"]["global_values"]
        ]
    return safe
