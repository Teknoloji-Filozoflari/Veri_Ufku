"""Actual bounded CPU lab solvers. All data are explicit synthetic fixtures."""

import json
from dataclasses import asdict
from datetime import UTC, datetime

import numpy as np
from scipy import stats

from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control
from veri_ufku.learning.curriculum import spec
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import uid


def curve(name, x, y):
    return dict(
        name=name, points=[[float(a), float(b)] for a, b in zip(x, y, strict=True)]
    )


def calculate(request, parameters, workspace, control=None):
    control = control or Control()
    p, lesson, curriculum = spec(parameters)
    control.check()
    if control.budget.device != "cpu" or control.budget.ram_bytes < 128 * 1024**2:
        raise ValueError("Lab CPU/RAM budget unavailable")
    v = p["value"]
    rng = np.random.default_rng(p["seed"])
    kind = p["lesson"]
    metrics = {}
    curves = []
    records = []
    details = {}
    split = {}
    solver = "numpy/scipy"

    def rows(**columns):
        return [
            dict(zip(columns, values, strict=True))
            for values in zip(*columns.values(), strict=True)
        ]

    if kind == "mean-median":
        x = np.array([10.0, 20.0, float(v)])
        metrics = dict(mean=float(x.mean()), median=float(np.median(x)), n=3)
        records = rows(x=x.tolist())
        curves = [curve("Tutar", range(3), x)]
    elif kind == "cleaning":
        original = [10.0, None, 30.0, None, 50.0]
        changed = [float(v) if x is None else x for x in original]
        metrics = dict(
            missing_n=2,
            n=5,
            observed_mean=float(np.mean([x for x in original if x is not None])),
            preview_mean=float(np.mean(changed)),
        )
        records = rows(original=original, preview=changed)
        curves = [curve("Açık doldurma önizlemesi", range(5), changed)]
        details = dict(
            action="explicit synthetic preview only; original retained", fill_value=v
        )
    elif kind == "histogram":
        x = rng.normal(0, 1, 200)
        counts, edges = np.histogram(x, bins=v)
        records = rows(x=x.tolist())
        metrics = dict(n=200, count_total=int(counts.sum()), bins=v)
        curves = [curve("Bin sayımı", (edges[:-1] + edges[1:]) / 2, counts)]
        details = dict(
            edges=edges.tolist(),
            counts=counts.tolist(),
            normalization="counts; not density",
            excluded=0,
        )
    elif kind == "sampling":
        population = np.arange(100, dtype=float)
        indices = rng.choice(100, size=v, replace=False)
        sample = population[indices]
        metrics = dict(
            n=v,
            population_n=100,
            population_mean=float(population.mean()),
            sample_mean=float(sample.mean()),
        )
        records = rows(
            x=population.tolist(), selected=[int(i in indices) for i in range(100)]
        )
        curves = [curve("Seçilen sentetik kayıt", indices, sample)]
        details = dict(
            selected_indices=indices.tolist(),
            design="simple random without replacement; fixed finite population; not survey inference",
        )
    elif kind == "ci":
        values = rng.normal(0, 1, (100, v))
        means = values.mean(axis=1)
        se = values.std(axis=1, ddof=1) / np.sqrt(v)
        critical = float(stats.t.ppf(0.975, v - 1))
        low = means - critical * se
        high = means + critical * se
        metrics = dict(
            repetitions=100,
            n_per_sample=v,
            nominal_coverage=0.95,
            observed_coverage=float(np.mean((low <= 0) & (high >= 0))),
            first_mean=float(means[0]),
            first_low=float(low[0]),
            first_high=float(high[0]),
        )
        records = rows(
            repetition=np.repeat(np.arange(100), v).tolist(), x=values.ravel().tolist()
        )
        curves = [
            curve("CI alt", range(100), low),
            curve("CI üst", range(100), high),
            curve("Bilinen μ=0", [0, 99], [0, 0]),
        ]
        details = dict(
            method="two-sided Student t mean interval; iid normal, unknown variance; ddof1",
            critical=critical,
            level=0.95,
            not_prediction_interval=True,
        )
    elif kind in ("overfitting", "leakage"):
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import mean_squared_error
        from sklearn.tree import DecisionTreeRegressor

        x = rng.uniform(-3, 3, 200)
        y = np.sin(x) + rng.normal(0, 0.4, 200)
        train = np.arange(40)
        validation = np.arange(40, 200)
        split = dict(
            train=train.tolist(),
            validation=validation.tolist(),
            scope="fixed exploratory teaching validation reused by slider; no final test",
        )
        records = rows(
            x=x.tolist(), y=y.tolist(), role=["train"] * 40 + ["validation"] * 160
        )
        if kind == "overfitting":
            model = DecisionTreeRegressor(max_depth=v, random_state=p["seed"]).fit(
                x[train, None], y[train]
            )
            prediction = model.predict(x[:, None])
            order = np.argsort(x[validation])
            curves = [
                curve("Validation gözlem", x[validation][order], y[validation][order]),
                curve(
                    "Ağacın tahmini",
                    x[validation][order],
                    prediction[validation][order],
                ),
            ]
            metrics = dict(
                train_mse=float(mean_squared_error(y[train], prediction[train])),
                validation_mse=float(
                    mean_squared_error(y[validation], prediction[validation])
                ),
                max_depth=v,
            )
            solver = "sklearn DecisionTreeRegressor"
        else:
            proxy = v / 100 * y + (1 - v / 100) * rng.normal(0, 1, 200)
            honest = LinearRegression().fit(x[train, None], y[train])
            leaky = LinearRegression().fit(
                np.column_stack((x[train], proxy[train])), y[train]
            )
            honest_prediction = honest.predict(x[validation, None])
            bad = leaky.predict(np.column_stack((x[validation], proxy[validation])))
            metrics = dict(
                honest_validation_mse=float(
                    mean_squared_error(y[validation], honest_prediction)
                ),
                contaminated_mse=float(mean_squared_error(y[validation], bad)),
                future_proxy_strength=v / 100,
            )
            curves = [
                curve(
                    "Dürüst validation hata",
                    range(160),
                    (y[validation] - honest_prediction) ** 2,
                ),
                curve("Geçersiz sızmış hata", range(160), (y[validation] - bad) ** 2),
            ]
            for r, z in zip(records, proxy, strict=True):
                r["forbidden_future_proxy"] = float(z)
            details = dict(
                leaked=True,
                warning="deliberately invalid teaching comparison; proxy uses outcome even in validation; never production performance",
            )
            solver = "sklearn LinearRegression; intentionally contaminated comparator labelled invalid"
    elif kind == "calibration":
        from scipy.special import expit
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import brier_score_loss, log_loss

        x = rng.normal(0, 1, 600)
        y = rng.binomial(1, expit(1.5 * x))
        base = LogisticRegression().fit(x[:200, None], y[:200])
        logit = base.decision_function(x[:, None]) * v
        calibrator = LogisticRegression(C=1e6).fit(logit[200:400, None], y[200:400])
        raw = expit(logit[400:])
        calibrated = calibrator.predict_proba(logit[400:, None])[
            :, list(calibrator.classes_).index(1)
        ]
        metrics = dict(
            evaluation_n=200,
            raw_brier=float(brier_score_loss(y[400:], raw)),
            calibrated_brier=float(brier_score_loss(y[400:], calibrated)),
            raw_log_loss=float(
                log_loss(y[400:], np.column_stack((1 - raw, raw)), labels=[0, 1])
            ),
            calibrated_log_loss=float(
                log_loss(
                    y[400:],
                    np.column_stack((1 - calibrated, calibrated)),
                    labels=[0, 1],
                )
            ),
        )
        records = rows(
            x=x.tolist(),
            y=y.tolist(),
            role=["train"] * 200 + ["calibration"] * 200 + ["evaluation"] * 200,
        )
        split = dict(
            train=list(range(200)),
            calibration=list(range(200, 400)),
            evaluation=list(range(400, 600)),
            scope="disjoint synthetic train/calibration/exploratory evaluation; no final test",
        )
        bins = []
        for name, prob in [("Ham", raw), ("Sigmoid", calibrated)]:
            points = []
            for i in range(10):
                chosen = (prob >= i / 10) & (
                    prob < ((i + 1) / 10) if i < 9 else prob <= 1
                )
                if chosen.any():
                    points.append(
                        [float(prob[chosen].mean()), float(y[400:][chosen].mean())]
                    )
                bins.append(dict(series=name, bin=i, n=int(chosen.sum())))
            curves.append(dict(name=name, points=points))
        curves.append(curve("Referans y=x", [0, 1], [0, 1]))
        details = dict(
            reliability_bins=bins,
            label_order=[0, 1],
            warning="Brier/logloss also reflect discrimination; small bins uncertain; calibration need not improve every draw",
        )
        solver = "sklearn LogisticRegression base + disjoint sigmoid calibration"
    elif kind == "time-series":
        period = v
        t = np.arange(72)
        y = 0.05 * t + np.sin(2 * np.pi * t / period) + rng.normal(0, 0.15, 72)
        origin = 60
        prediction = np.array([y[origin - period + j % period] for j in range(12)])
        metrics = dict(
            horizon=12, period=period, mae=float(np.mean(np.abs(y[60:] - prediction)))
        )
        records = rows(
            time=t.tolist(),
            y=y.tolist(),
            role=["history"] * 60 + ["exploratory_future"] * 12,
        )
        curves = [
            curve("Gerçek gelecek", t[60:], y[60:]),
            curve("Seasonal naive", t[60:], prediction),
        ]
        split = dict(
            train=list(range(60)),
            evaluation=list(range(60, 72)),
            scope="one fixed chronological origin; repeated slider exploration not production backtest",
        )
        details = dict(
            method="last observed seasonal cycle repeats; no future covariates used"
        )
    elif kind == "confounding":
        from scipy.special import expit
        from sklearn.linear_model import LinearRegression

        z = rng.normal(0, 1, 400)
        t = rng.binomial(1, expit(v * z))
        y = 2 * t + v * z + rng.normal(0, 0.5, 400)
        naive = LinearRegression().fit(t[:, None], y)
        adjusted = LinearRegression().fit(np.column_stack((t, z)), y)
        metrics = dict(
            n=400,
            known_synthetic_effect=2.0,
            naive_coefficient=float(naive.coef_[0]),
            adjusted_coefficient=float(adjusted.coef_[0]),
            strength=v,
        )
        records = rows(treatment=t.tolist(), confounder=z.tolist(), outcome=y.tolist())
        curves = [
            curve(
                "Bilinen / naif / adjusted",
                [0, 1, 2],
                [2, naive.coef_[0], adjusted.coef_[0]],
            )
        ]
        details = dict(
            dag=["z → treatment", "z → outcome", "treatment → outcome"],
            assumptions="synthetic known DGP, measured z, consistency/exchangeability/positivity; adjustment in arbitrary real data does not prove causation",
            treatment_counts=np.bincount(t, minlength=2).tolist(),
        )
        solver = "sklearn OLS, known confounded synthetic DGP"
    control.check()
    fixture_hash = digest(records)
    for i, r in enumerate(records):
        r["fixture_row_id"] = "synthetic:" + fixture_hash[:16] + ":" + str(i)
    split_ids = {
        k: [records[i]["fixture_row_id"] for i in indices]
        for k, indices in split.items()
        if isinstance(indices, list)
    }
    value = dict(
        schema="LearningLabRun/v1",
        run_id="run:" + uid(),
        status="completed",
        spec=p,
        lesson_version=lesson["version"],
        content_version=curriculum.data["content_version"],
        article_id=lesson["article_id"],
        article_version=lesson["review"]["article_version"],
        review=lesson["review"],
        fixture_hash=fixture_hash,
        input_records=records,
        metrics=metrics,
        curves=curves,
        details=details,
        split=split,
        split_ids=split_ids,
        solver=solver,
        experiment_capture=request["experiment_capture"],
        workspace_id=request["workspace_id"],
        budget=asdict(control.budget),
        limitations=[
            "Synthetic teaching fixture; no user data or production evaluation.",
            "Slider reuses exploratory evaluation; no certification or unseen final-test guarantee.",
            "Prerequisites and self-check optional; reading does not gate tools.",
        ],
    )
    value["provenance"] = asdict(
        Provenance(
            provenance_id="provenance:" + uid(),
            dataset_versions=(),
            config_revision=0,
            capability_id="learn.lab." + kind,
            parameters_hash=digest(p),
            environment=(("solver", solver),),
            created_at=datetime.now(UTC).isoformat(),
            seed=p["seed"],
            seed_reason="synthetic fixture RNG; library/environment versions also required",
            scope="separate ephemeral ProjectStore; synthetic row ids only; no user source",
            learning_content_version=str(curriculum.data["content_version"]),
        )
    )
    value = json.loads(json.dumps(value, allow_nan=False))
    value["identity"] = digest(value)
    if len(records) > control.budget.sample_limit_rows:
        raise ValueError("Lab input rows exceed shared budget")
    return value
