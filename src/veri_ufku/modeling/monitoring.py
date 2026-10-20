"""Bounded snapshot batch drift and delayed-label evaluation; never fit or deploy."""

import hashlib
import json
import math
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl
from scipy.spatial.distance import jensenshannon
from scipy.stats import ks_2samp, wasserstein_distance
from sklearn.metrics import (
    accuracy_score,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
)

from veri_ufku.analytics.dataset import checked
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.monitor_contracts import LIMITATIONS, MonitorSpec, instant
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.project_store import file_hash


def numeric(values):
    a = np.array([np.nan if v is None else float(v) for v in values], dtype=float)
    return a[np.isfinite(a)]


def distribution(reference, current, kind, spec, continuous=False):
    """Reference-fixed bins including tails; categorical support includes unseen values."""
    result = dict(reference_n=len(reference), window_n=len(current), kind=kind)
    if kind == "numeric":
        a, b = numeric(reference), numeric(current)
        result.update(
            reference_excluded=len(reference) - len(a),
            window_excluded=len(current) - len(b),
        )
        if len(a) < spec.min_n or len(b) < spec.min_n:
            return dict(result, status="insufficient_n", alarm=False)
        cuts = np.unique(np.quantile(a, np.linspace(0, 1, spec.bins + 1)[1:-1]))
        edges = np.r_[-np.inf, cuts, np.inf]
        x, y = np.histogram(a, edges)[0], np.histogram(b, edges)[0]
        result.update(
            bin_cuts=cuts.tolist(),
            tails="(-inf, first), last..+inf; numpy histogram rightmost inclusive",
            wasserstein=float(wasserstein_distance(a, b)),
            ks_effect=float(ks_2samp(a, b, method="asymp").statistic),
        )
        if (
            continuous
            and spec.independent
            and len(np.unique(a)) == len(a)
            and len(np.unique(b)) == len(b)
        ):
            result["ks_p"] = float(ks_2samp(a, b, method="asymp").pvalue)
        else:
            result["ks_p"] = None
            result["ks_p_reason"] = (
                "continuous/independent not confirmed or within-sample ties; effect only"
            )
    else:
        # Hash labels, never put raw category/personal text into monitoring summaries.
        def key(v):
            return hashlib.sha256(
                json.dumps(
                    [type(v).__name__, v], ensure_ascii=False, default=str
                ).encode()
            ).hexdigest()

        a, b = (
            [key(v) for v in reference if v is not None],
            [key(v) for v in current if v is not None],
        )
        result.update(
            reference_excluded=len(reference) - len(a),
            window_excluded=len(current) - len(b),
        )
        if len(a) < spec.min_n or len(b) < spec.min_n:
            return dict(result, status="insufficient_n", alarm=False)
        support = sorted(set(a) | set(b))
        if len(support) > 512:
            raise ProjectError(
                "Categorical drift512 kategori sınırı; açık daraltma gerekli."
            )
        from collections import Counter

        ca, cb = Counter(a), Counter(b)
        x, y = np.array([ca[k] for k in support]), np.array([cb[k] for k in support])
        result.update(
            category_hashes=support,
            unseen_count=sum(v for k, v in cb.items() if k not in ca),
            js_distance=float(jensenshannon(x, y, base=2)),
        )
    # Jeffreys-style additive smoothing; same denominator/categories on both sides.
    p = (x + 0.5) / (x.sum() + 0.5 * len(x))
    q = (y + 0.5) / (y.sum() + 0.5 * len(y))
    psi = float(np.sum((q - p) * np.log(q / p)))
    result.update(
        status="measured",
        psi=psi,
        smoothing_count=0.5,
        reference_counts=x.tolist(),
        window_counts=y.tolist(),
        alarm=psi >= spec.psi_threshold
        or result.get("wasserstein", 0) >= spec.wasserstein_threshold
        or result.get("js_distance", 0) >= spec.js_threshold,
    )
    return result


def name(source, column):
    try:
        return next(c["name"] for c in source["columns"] if c["id"] == column)
    except StopIteration:
        raise ProjectError("Seçilen ColumnId kaynak şemasında yok.") from None


def load_source(source, control):
    if (
        not 1 <= source["row_count"] <= min(10000, control.budget.sample_limit_rows)
        or len(source["columns"]) > 64
    ):
        raise ProjectError(
            "Monitoring kaynak başına1..10000row/64column sınırı; sessiz sample yok."
        )
    checked(source, control)
    f = pl.read_parquet(source["path"])
    if (
        len(f) != source["row_count"]
        or f["__vu_row_id"].null_count()
        or f["__vu_row_id"].n_unique() != len(f)
    ):
        raise ProjectError("Kaynak RowId/count geçersiz.")
    return f


def utc_value(v):
    return instant(v.isoformat() if isinstance(v, datetime) else v)


def source_keys(frame, column):
    if column is None:
        raise ProjectError("Açık kaynak anahtarı gerekli.")
    series = frame[column]
    if (
        series.dtype != pl.String
        or series.null_count()
        or series.n_unique() != len(frame)
        or any(not v or len(v) > 256 for v in series)
    ):
        raise ProjectError(
            "ID eşleme yalnız non-null/unique String anahtar destekler; otomatik coercion yok."
        )
    return series.to_list()


def evaluate(records, labels, spec, label_source, key_field, card, as_of, event_times):
    if labels is None:
        return dict(status="labels_unavailable", n=0, metrics=None, calibration=None)
    keys = source_keys(labels, name(label_source, spec.label_key))
    target = name(label_source, spec.label_value)
    arrived = name(label_source, spec.label_arrived)
    lookup = {}
    for i, key in enumerate(keys):
        if labels[target][i] is not None:
            t = utc_value(labels[arrived][i])
            if t <= as_of:
                lookup[key] = (labels[target][i], t)
    actual, predicted, probability, delays = [], [], [], []
    for r in records:
        key = r[key_field]
        if key not in lookup:
            continue
        y, arrival = lookup[key]
        if key in event_times:
            if arrival < event_times[key]:
                raise ProjectError(
                    "Label arrival event zamanından önce; eşleme/zamanı kontrol edin."
                )
            delays.append(arrival - event_times[key])
        actual.append(y)
        predicted.append(r["prediction"])
        if "probabilities" in r:
            probability.append(r["probabilities"])
    n = len(actual)
    pending = len(records) - n
    aged_pending = sum(
        as_of - event_times[r[key_field]] > spec.label_delay_seconds
        for r in records
        if r[key_field] not in lookup and r[key_field] in event_times
    )
    delay = dict(
        pending=pending,
        matched=n,
        total=len(records),
        matched_fraction=n / len(records) if records else None,
        overdue=aged_pending,
        observed_mean_seconds=float(np.mean(delays)) if delays else None,
        threshold_seconds=spec.label_delay_seconds,
        selection="only labels arrived by as_of; unmatched/future excluded; observed subset may be biased",
    )
    if n < spec.min_n:
        return dict(
            status="insufficient_labels",
            n=n,
            metrics=None,
            calibration=None,
            label_delay=delay,
        )
    calibration = None
    if card["purpose"] == "regression":
        if any(type(v) not in (float, int) or not math.isfinite(v) for v in actual):
            raise ProjectError(
                "Regresyon label numeric/finite olmalı; sessiz type düzeltme yok."
            )
        metrics = dict(
            mae=float(mean_absolute_error(actual, predicted)),
            rmse=math.sqrt(mean_squared_error(actual, predicted)),
        )
    else:
        order = card["label_order"]
        if any(type(v) is not str or v not in order for v in actual):
            raise ProjectError(
                "Unseen/type farklı label reddedildi; model label order korunur."
            )
        metrics = dict(accuracy=float(accuracy_score(actual, predicted)))
        if probability:
            p = np.asarray(probability, float)
            if (
                p.shape != (n, len(order))
                or not np.isfinite(p).all()
                or np.any((p < 0) | (p > 1))
                or not np.allclose(p.sum(axis=1), 1)
            ):
                raise ProjectError("Probability shape/order/value geçersiz.")
            y = np.array([order.index(v) for v in actual])
            metrics["log_loss"] = float(log_loss(y, p, labels=list(range(len(order)))))
            # Multiclass sum-of-squared probabilities; binary also sum across both,
            # so twice the usual positive-class binary Brier; explicit denominator.
            metrics["brier_multiclass_sum"] = float(
                np.mean(np.sum((p - np.eye(len(order))[y]) ** 2, axis=1))
            )
            reliability = []
            for k in range(len(order)):
                bins = []
                for j in range(spec.bins):
                    mask = (p[:, k] >= j / spec.bins) & (
                        (p[:, k] < (j + 1) / spec.bins)
                        if j < spec.bins - 1
                        else (p[:, k] <= 1)
                    )
                    count = int(mask.sum())
                    bins.append(
                        dict(
                            lower=j / spec.bins,
                            upper=(j + 1) / spec.bins,
                            n=count,
                            mean_probability=float(p[mask, k].mean())
                            if count
                            else None,
                            event_rate=float((y[mask] == k).mean()) if count else None,
                        )
                    )
                ece = (
                    sum(
                        v["n"] * abs(v["mean_probability"] - v["event_rate"])
                        for v in bins
                        if v["n"]
                    )
                    / n
                )
                reliability.append(dict(class_index=k, bins=bins, ece=float(ece)))
            calibration = dict(
                method="one-vs-rest fixed equal-width reliability; empirical ECE bin dependent",
                n=n,
                label_order=order,
                class_counts=[int((y == k).sum()) for k in range(len(order))],
                missing_class_indices=[
                    k for k in range(len(order)) if not (y == k).any()
                ],
                reliability=reliability,
                mean_ece=float(np.mean([v["ece"] for v in reliability])),
            )
    return dict(
        status="observed_labels_only",
        n=n,
        metrics=metrics,
        calibration=calibration,
        label_delay=delay,
    )


def score(package, source, frame, mapping, control, workspace):
    from veri_ufku.domain.json import sha
    from veri_ufku.modeling.lifecycle import MAX_BYTES, load_package, predict

    with open(package["path"], "rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if (
        len(raw) > MAX_BYTES
        or dict(size=len(raw), sha256=sha(raw)) != package["fingerprint"]
    ):
        raise ProjectError("Kayıtlı model hash/boyut uyuşmuyor.")
    snapshot = Path(workspace) / (package["fingerprint"]["sha256"] + ".vumodel")
    if not snapshot.exists():
        with open(snapshot, "xb") as output:
            output.write(raw)
    elif snapshot.read_bytes() != raw:
        raise ProjectError("Private model snapshot değişmiş.")
    control.disk(Path(workspace), force=True)
    model, card = load_package(snapshot)
    if card != package["card"] or card["purpose"] not in (
        "regression",
        "classification",
    ):
        raise ProjectError(
            "Monitoring yalnız doğrulanmış regression/classification paketlerini destekler."
        )
    if set(frame["__vu_row_id"]) & set(
        card.get("split", {}).get("membership", {}).get("test", [])
    ):
        raise ProjectError(
            "Kalıcı final-test üyeleri monitoring scoring için kapalı; test kullanım defterini atlamayın."
        )
    result, details = predict(
        model,
        card,
        frame,
        source["columns"],
        mapping or None,
        source.get("semantic_metadata"),
        invalid="reject",
        batch_size=256,
        control=control,
    )
    extras = [c for c in result.columns if c not in frame.columns]
    predictions = [c for c in extras if c.endswith("vu_prediction")]
    if len(predictions) != 1:
        raise ProjectError("Monitoring prediction şeması desteklenmiyor.")
    rows = []
    for i, rid in enumerate(result["__vu_row_id"]):
        r = dict(row_id=rid, prediction=result[predictions[0]][i])
        if card["probability_supported"]:
            names = [
                next(c for c in extras if c.endswith("vu_probability_" + str(k)))
                for k in range(len(card["label_order"]))
            ]
            r["probabilities"] = [result[c][i] for c in names]
        rows.append(r)
    if file_hash(Path(package["path"])) != package["fingerprint"]:
        raise ProjectError("Model hesap sırasında değişti; sonuç reddedildi.")
    return rows, card


def calculate(request, parameters, workspace, control=None):
    control = control or Control()
    spec = MonitorSpec.from_dict(parameters)
    sources = request["sources"]
    ref = sources[spec.reference]
    win = sources[spec.window]
    reference = load_source(ref, control)
    window = load_source(win, control)
    raw_window_n = len(window)
    if spec.event_time:
        event_name = name(win, spec.event_time)
        times = [utc_value(v) for v in window[event_name]]
        keep = [
            spec.window_start
            and instant(spec.window_start) <= v < instant(spec.window_end)
            for v in times
        ]
        window = window.filter(pl.Series(keep))
    else:
        times = []
    if not len(window):
        raise ProjectError("Seçili pencere boş.")
    now = datetime.now(UTC).isoformat()
    run_id = "monitor:" + uid()
    data = dict(
        schema="MonitoringRun/v1",
        run_id=run_id,
        status="completed",
        created_at=now,
        spec=spec.data(),
        limitations=LIMITATIONS,
        reference=dict(
            version=spec.reference, fingerprint=ref["fingerprint"], n=len(reference)
        ),
        window=dict(
            version=spec.window,
            fingerprint=win["fingerprint"],
            n=len(window),
            source_n=raw_window_n,
            excluded_by_window=raw_window_n - len(window),
            selection="explicit event interval [start,end)"
            if spec.event_time
            else "whole snapshot; window timestamps user declared, not inferred event times",
        ),
        schema_drift=[],
        features=[],
        prediction_drift=[],
        models=[],
        fit_calls=0,
    )
    for f in spec.features:
        control.check()
        try:
            an, bn = name(ref, f["reference"]), name(win, f["window"])
        except ProjectError:
            data["schema_drift"].append(
                dict(
                    reference_column=f["reference"],
                    window_column=f["window"],
                    alarm=True,
                    status="missing_mapped_column",
                )
            )
            data["features"].append(
                dict(
                    **f,
                    distribution=dict(status="missing_mapped_column", alarm=True),
                    quality=dict(status="column_unavailable"),
                )
            )
            continue
        at, bt = str(reference[an].dtype), str(window[bn].dtype)
        sema = ref.get("semantic_metadata", {}).get(f["reference"], {})
        semb = win.get("semantic_metadata", {}).get(f["window"], {})
        metadata_difference = {
            k: dict(reference=sema.get(k), window=semb.get(k))
            for k in ("unit", "measurement_level", "ordinal_order")
            if sema.get(k) != semb.get(k)
        }
        mismatch = at != bt or bool(metadata_difference)
        data["schema_drift"].append(
            dict(
                reference_column=f["reference"],
                window_column=f["window"],
                reference_type=at,
                window_type=bt,
                metadata_difference=metadata_difference,
                alarm=mismatch,
            )
        )
        if f["kind"] == "numeric" and (
            not reference[an].dtype.is_numeric() or not window[bn].dtype.is_numeric()
        ):
            measured = dict(status="type_mismatch", alarm=True)
        elif f["kind"] == "categorical" and (
            reference[an].dtype not in (pl.String, pl.Boolean)
            or window[bn].dtype not in (pl.String, pl.Boolean)
        ):
            measured = dict(status="unsupported_categorical_type", alarm=True)
        elif metadata_difference:
            measured = dict(
                status="unit_or_measurement_contract_mismatch; no conversion",
                alarm=True,
            )
        else:
            measured = distribution(
                reference[an].to_list(),
                window[bn].to_list(),
                f["kind"],
                spec,
                f["continuous"],
            )

        def missing(series):
            values = series.to_list()
            return sum(
                v is None or isinstance(v, float) and not math.isfinite(v)
                for v in values
            ) / len(values)

        quality = dict(
            reference_missing_rate=missing(reference[an]),
            window_missing_rate=missing(window[bn]),
        )
        quality["alarm"] = quality["window_missing_rate"] >= spec.missing_threshold
        data["features"].append(dict(**f, distribution=measured, quality=quality))
    data["schema_inventory"] = dict(
        added_names=sorted(
            set(window.columns)
            - set(reference.columns)
            - {"__vu_row_id", "__vu_source_record_id"}
        ),
        missing_names=sorted(
            set(reference.columns)
            - set(window.columns)
            - {"__vu_row_id", "__vu_source_record_id"}
        ),
        policy="names descriptive; no inferred ColumnId equivalence; selected mappings control comparisons",
    )
    data["data_quality"] = {}
    for side, source, frame in (("reference", ref, reference), ("window", win, window)):
        contract = source.get("schema_contract")
        if not contract:
            data["data_quality"][side] = dict(
                contract_status="not_configured", silent_corrections=0
            )
            continue
        if contract["status"] == "inapplicable":
            data["data_quality"][side] = dict(
                contract_status="inapplicable", silent_corrections=0
            )
            continue
        definition = contract["definition"]
        supported = [r for r in definition["rules"] if r["kind"] != "foreign_key"]
        unsupported = [
            r["id"] for r in definition["rules"] if r["kind"] == "foreign_key"
        ]
        from veri_ufku.operations.data_quality import evaluate as quality_check

        path = Path(workspace) / (side + "-quality.parquet")
        frame.write_parquet(path)
        _, _, quality = quality_check(
            dict(source, path=str(path), row_count=len(frame)),
            dict(schema_version=1, rules=supported),
            workspace,
            control,
        )
        data["data_quality"][side] = dict(
            contract_status="measured selected window",
            definition_version=contract["definition_version"],
            rules=[
                {
                    k: r[k]
                    for k in ("rule_id", "kind", "level", "severity", "violations")
                }
                for r in quality["rules"]
            ],
            error_violations=quality["error_violations"],
            warning_violations=quality["warning_violations"],
            unsupported_foreign_key_rules=unsupported,
            silent_corrections=0,
        )
        control.disk(Path(workspace), force=True)
    alltests = [v["distribution"] for v in data["features"]]
    labels = load_source(sources[spec.labels], control) if spec.labels else None
    source_records = {}
    cards = {}
    evaluations = {}
    for role, record_id in (
        ("champion", request["resolved_champion"]),
        ("challenger", spec.challenger),
    ):
        if not record_id:
            continue
        package = request["models"][record_id]
        if spec.labels and spec.reference_key:
            refkeys = source_keys(reference, name(ref, spec.reference_key))
            winkeys = source_keys(window, name(win, spec.window_key))
            if set(refkeys) & set(winkeys):
                raise ProjectError(
                    "Referans/pencere label anahtarları çakışıyor; ayrı namespace veya event key gerekli."
                )
        records, card = score(
            package, win, window, spec.window_mapping, control, workspace
        )
        rr, rcard = score(
            package, ref, reference, spec.reference_mapping, control, workspace
        )
        if card != rcard:
            raise ProjectError("Shadow/reference model kartı değişti.")
        source_records[role] = records
        cards[role] = card
        if role == "challenger" and (
            card["purpose"] != cards["champion"]["purpose"]
            or card["label_order"] != cards["champion"]["label_order"]
            or card["target"] != cards["champion"]["target"]
        ):
            raise ProjectError(
                "Shadow model hedef/purpose/label-order farklı; karşılaştırma kapalı."
            )
        if spec.window_key:
            keys = source_keys(window, name(win, spec.window_key))
            for r, key in zip(records, keys, strict=True):
                r["source_key"] = key
        if spec.reference_key:
            keys = source_keys(reference, name(ref, spec.reference_key))
            for r, key in zip(rr, keys, strict=True):
                r["source_key"] = key
        event_times = {}
        if spec.event_time and spec.window_key:
            event_times = dict(
                zip(
                    source_keys(window, name(win, spec.window_key)),
                    [utc_value(v) for v in window[name(win, spec.event_time)]],
                    strict=True,
                )
            )
        observed = evaluate(
            records,
            labels,
            spec,
            sources.get(spec.labels),
            "source_key",
            card,
            instant(spec.as_of),
            event_times,
        )
        baseline = (
            evaluate(
                rr,
                labels,
                spec,
                sources.get(spec.labels),
                "source_key",
                card,
                instant(spec.as_of),
                {},
            )
            if spec.reference_key
            else dict(
                status="reference_labels_not_configured",
                metrics=None,
                calibration=None,
                n=0,
            )
        )
        evaluations[role] = observed
        drift = distribution(
            [r["prediction"] for r in rr],
            [r["prediction"] for r in records],
            "numeric" if card["purpose"] == "regression" else "categorical",
            spec,
            continuous=False,
        )
        data["prediction_drift"].append(dict(role=role, distribution=drift))
        alltests.append(drift)
        changes = []
        if baseline["metrics"] and observed["metrics"]:
            for metric, value in observed["metrics"].items():
                delta = value - baseline["metrics"][metric]
                changes.append(
                    dict(
                        metric=metric,
                        delta=delta,
                        threshold=spec.performance_delta,
                        alarm=(-delta if metric == "accuracy" else delta)
                        >= spec.performance_delta,
                        interpretation="observed matched subsets; no causal deterioration claim",
                    )
                )
        calchange = None
        if baseline["calibration"] and observed["calibration"]:
            delta = (
                observed["calibration"]["mean_ece"]
                - baseline["calibration"]["mean_ece"]
            )
            calchange = dict(
                delta=delta,
                threshold=spec.calibration_delta,
                alarm=delta >= spec.calibration_delta,
            )
        data["models"].append(
            dict(
                role=role,
                record_id=record_id,
                run_id=package["card"]["run_id"],
                fingerprint=package["fingerprint"],
                reference_evaluation=baseline,
                window_evaluation=observed,
                performance_changes=changes,
                calibration_change=calchange,
            )
        )
    valid = [d for d in alltests if d.get("ks_p") is not None]
    for d in valid:
        d["ks_p_bonferroni"] = min(1.0, d["ks_p"] * len(valid))
        d["ks_alarm"] = (
            d["ks_p_bonferroni"] < spec.alpha
            and d["ks_effect"] >= spec.ks_effect_threshold
        )
        d["alarm"] = d["alarm"] or d["ks_alarm"]
    data["multiplicity"] = dict(
        method="Bonferroni within this report only",
        valid_ks_tests=len(valid),
        repeated_windows="not adjusted; thresholds operational, not universal",
    )
    data["shadow"] = dict(status="not_configured")
    if spec.challenger:
        a, b = source_records["champion"], source_records["challenger"]
        if [r["row_id"] for r in a] != [r["row_id"] for r in b]:
            raise ProjectError("Shadow RowId eşleşmesi bozuk.")
        values = [
            abs(x["prediction"] - y["prediction"])
            if cards["champion"]["purpose"] == "regression"
            else x["prediction"] != y["prediction"]
            for x, y in zip(a, b, strict=True)
        ]
        data["shadow"] = dict(
            status="same_batch_no_deploy",
            n=len(a),
            mean_absolute_prediction_difference=float(np.mean(values)),
            comparison="MAE between predictions"
            if cards["champion"]["purpose"] == "regression"
            else "label disagreement fraction",
            performance_available=all(
                v["metrics"] is not None for v in evaluations.values()
            ),
        )
    # Private source identities remain bound to immutable snapshots; never generic export.
    data["membership"] = dict(
        reference_row_ids=reference["__vu_row_id"].to_list(),
        window_row_ids=window["__vu_row_id"].to_list(),
        window_source_record_ids=window["__vu_source_record_id"].to_list(),
    )
    data["prediction_records"] = source_records
    for s in sources.values():
        checked(s, control)
    data["provenance"] = json.loads(
        json.dumps(
            asdict(
                Provenance(
                    provenance_id="provenance:" + uid(),
                    dataset_versions=tuple(sources),
                    config_revision=0,
                    capability_id="model.monitor.batch",
                    parameters_hash=digest(spec.data()),
                    environment=(("backend", "scipy/sklearn/native"),),
                    created_at=now,
                    scope="bounded immutable local snapshots; explicit window; no training/test selection",
                    seed=None,
                    source_snapshot_ids=tuple(
                        s["source_snapshot_id"] for s in sources.values()
                    ),
                )
            )
        )
    )
    data["source_refs"] = {
        k: dict(
            fingerprint=v["fingerprint"], source_snapshot_id=v["source_snapshot_id"]
        )
        for k, v in sources.items()
    }
    data["experiment_capture"] = request["experiment_capture"]
    data["route_event_id"] = request["route_event_id"]
    data["prior_test_use_ids"] = request["prior_test_use_ids"]
    data["model_refs"] = {
        k: {n: v[n] for n in ("fingerprint", "record_id", "run_id")}
        for k, v in request["models"].items()
    }
    data["identity"] = digest(data)
    control.check()
    control.disk(Path(workspace), force=True)
    return data


def public_report(value):
    """Aggregate GUI/API view; source keys, predictions and raw labels stay private."""
    return {
        k: v for k, v in value.items() if k not in ("prediction_records", "membership")
    }
