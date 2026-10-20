"""Chronological, group-isolated forecasting; held-out targets never select a model."""

import math
import warnings
from datetime import UTC, datetime
from itertools import chain

import numpy as np
import pandas as pd
import polars as pl
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from veri_ufku.analytics.dataset import checked
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.contracts import identifier
from veri_ufku.modeling.time_series_contracts import TimeSeriesSpec
from veri_ufku.storage.project_model import ProjectError, uid


def historical_features(values, window):
    """Feature at t uses indices strictly less than t; no centered window or bfill."""
    s = pd.Series(values, dtype=float)
    lag = s.shift(1)
    rolling = lag.rolling(window, min_periods=window).mean()
    return [
        dict(
            index=i,
            lag=None if pd.isna(lag[i]) else float(lag[i]),
            rolling=None if pd.isna(rolling[i]) else float(rolling[i]),
        )
        for i in range(len(s))
    ]


def metrics(actual, predicted):
    error = np.asarray(actual, float) - np.asarray(predicted, float)
    if not len(error) or not np.isfinite(error).all():
        raise ProjectError("Sonlu gerçek değer ve tahmin olmadan skor üretilemez.")
    return dict(
        mae=float(np.mean(np.abs(error))),
        rmse=float(np.sqrt(np.mean(error**2))),
        n=len(error),
        mape=None,
        mape_reason="Sıfırda MAPE tanımsız, sıfıra yakın ölçümde kararsızdır; yüzde hata sunulmaz.",
    )


def forecast(history, steps, method, period, control):
    control.check()
    y = np.asarray(history, float).copy()
    if method == "naive":
        result = np.repeat(y[-1], steps)
    elif method == "seasonal-naive":
        if period < 2 or len(y) < 2 * period:
            raise ProjectError("Seasonal-naive için en az iki tam mevsim gerekli.")
        result = np.resize(y[-period:], steps)
    else:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fit = ExponentialSmoothing(
                y,
                trend="add" if method in ("trend", "seasonal") else None,
                seasonal="add" if method == "seasonal" else None,
                seasonal_periods=period if method == "seasonal" else None,
                initialization_method="estimated",
                missing="raise",
            ).fit(optimized=True, use_brute=False)
            result = np.asarray(fit.forecast(steps), float)
        if any(
            "converg" in str(w.message).lower() for w in caught
        ) or not fit.mle_retvals.get("success", True):
            raise ProjectError(
                "ExponentialSmoothing optimizasyonu yakınsamadı; model başarılı sayılmadı."
            )
    if not np.isfinite(result).all():
        raise ProjectError("Model sonlu tahmin üretemedi; aralık/skor uydurulmadı.")
    control.check()
    return result.tolist()


def normalize(frame, columns, spec, semantics=None):
    spec.validate(columns)
    names = {c["id"]: c for c in columns}
    dc, mc = names[spec.date], names[spec.measurement]
    dates, measurements = frame[dc["name"]], frame[mc["name"]]
    if dates.dtype != pl.Date and not isinstance(dates.dtype, pl.Datetime):
        raise ProjectError(
            "Tarih sütunu Date/Datetime olmalı; metni açık dönüşümle hazırlayın."
        )
    if not measurements.dtype.is_numeric() or identifier(mc, semantics or {}):
        raise ProjectError("Sayısal ölçüm gerekli; kimlik ölçüm değildir.")
    if any(
        s.null_count()
        for s in [dates, measurements]
        + ([frame[names[spec.group]["name"]]] if spec.group else [])
    ):
        raise ProjectError(
            "Tarih, ölçüm veya grup eksik; kayıt sessizce atılmaz/doldurulmaz."
        )
    values = measurements.cast(pl.Float64).to_numpy()
    if not np.isfinite(values).all():
        raise ProjectError("NaN/inf ölçümler desteklenmez.")
    if not measurements.dtype.is_float() and any(
        a != float(b) for a, b in zip(measurements, values)
    ):
        raise ProjectError("Float64 ölçüm dönüşümünde hassasiyet kaybı.")
    if (
        isinstance(dates.dtype, pl.Datetime)
        and dates.dtype.time_unit == "ns"
        and (dates.cast(pl.Int64) % 1000 != 0).any()
    ):
        raise ProjectError(
            "Nanosaniye hassasiyeti desteklenmiyor; açık dönüşüm gerekli."
        )
    index = pd.DatetimeIndex(dates.to_list())
    civil = dates.dtype == pl.Date
    if civil and spec.frequency == "h":
        raise ProjectError("Saatlik seri için saat içeren Datetime gerekli.")
    if not civil:
        if index.tz is None:
            if not spec.timezone:
                raise ProjectError(
                    "Saat dilimsiz Datetime için IANA saat dilimini açıkça seçin."
                )
            try:
                index = index.tz_localize(
                    spec.timezone, ambiguous="raise", nonexistent="raise"
                )
            except Exception as error:
                raise ProjectError(
                    "Belirsiz/olmayan yerel saat (DST); saat dilimini/veriyi düzeltin."
                ) from error
        elif spec.timezone:
            index = index.tz_convert(spec.timezone)
        # Hourly means elapsed hours; calendar frequencies use selected/native zone.
        if spec.frequency == "h":
            index = index.tz_convert("UTC")
    labels = (
        frame[names[spec.group]["name"]].to_list()
        if spec.group
        else ["Tüm seri"] * frame.height
    )
    if (
        spec.group
        and frame[names[spec.group]["name"]].dtype.is_float()
        and not frame[names[spec.group]["name"]].is_finite().all()
    ):
        raise ProjectError("NaN/inf grup anahtarı desteklenmez.")
    rowids = frame["__vu_row_id"].to_list()
    grouped = {}
    for i, label in enumerate(labels):
        key = (type(label).__name__, str(label))
        grouped.setdefault(key, []).append(i)
    if len(grouped) > 20 or frame.height > 100000:
        raise ProjectError(
            "Zaman serisi bütçesi: en çok 20 grup ve 100.000 kayıt; sessiz örneklem yok."
        )
    output = []
    for key, positions in grouped.items():
        series = pd.Series(values[positions], index=index[positions]).sort_index(
            kind="stable"
        )
        duplicate_count = int(series.index.duplicated().sum())
        members = pd.Series(
            [rowids[i] for i in positions], index=index[positions]
        ).sort_index(kind="stable")
        if spec.resample:
            bins = series.resample(spec.frequency, closed="left", label="left")
            series = bins.sum(min_count=1) if spec.aggregation == "sum" else bins.mean()
            membership = members.resample(
                spec.frequency, closed="left", label="left"
            ).apply(list)
        else:
            if duplicate_count:
                raise ProjectError(
                    f"{key[1]}: {duplicate_count} duplicate tarih; açık yeniden örnekleme ve agregasyon seçin."
                )
            membership = members.map(lambda v: [v])
        expected = pd.date_range(series.index[0], series.index[-1], freq=spec.frequency)
        anchor = series.index[0]
        aligned = (
            spec.frequency == "h"
            and anchor.minute == anchor.second == anchor.microsecond == 0
            or spec.frequency == "D"
            and anchor.hour == anchor.minute == anchor.second == anchor.microsecond == 0
            or spec.frequency == "W-MON"
            and anchor.weekday() == 0
            and anchor.hour == anchor.minute == anchor.second == anchor.microsecond == 0
            or spec.frequency == "MS"
            and anchor.day == 1
            and anchor.hour == anchor.minute == anchor.second == anchor.microsecond == 0
        )
        missing = int(series.isna().sum()) + len(expected.difference(series.index))
        if not aligned or not series.index.equals(expected) or missing:
            raise ProjectError(
                f"{key[1]}: düzensiz sıklık / eksik dönem ({missing}). Yeniden örnekleme açık seçimdir; boş dönem sıfır sayılmaz, gelecekten doldurulmaz. Eksik dönemleri kaynakta açıkça hazırlayın."
            )
        output.append(
            dict(
                group=key[1],
                group_type=key[0],
                series=series,
                members=membership.tolist(),
                duplicates=duplicate_count,
                timezone=str(series.index.tz)
                if series.index.tz
                else "Date: takvim günü (saat dilimi yok)",
            )
        )
    return output


def calculate(request, parameters, workspace, control=None):
    control = control or Control()
    spec = TimeSeriesSpec.from_dict(parameters)
    if spec.advanced is not None and spec.advanced.get("family") == "signal":
        from veri_ufku.modeling.signals import calculate as signal_calculate

        return signal_calculate(request, spec, workspace, control)
    if spec.advanced is not None:
        from veri_ufku.modeling.temporal import calculate as temporal_calculate

        return temporal_calculate(request, spec, workspace, control)
    mode = request.get("mode", "development")
    if mode not in ("development", "final"):
        raise ProjectError("Zaman serisi çalışma modu geçersiz.")
    checked(request, control)
    if request["row_count"] > 100000:
        raise ProjectError("100.000 kayıt bütçesi aşıldı; sessiz örneklem yok.")
    selected = [
        next(c["name"] for c in request["columns"] if c["id"] == ident)
        for ident in [spec.date, spec.measurement]
        + ([spec.group] if spec.group else [])
    ]
    frame = pl.read_parquet(request["path"], columns=["__vu_row_id"] + selected)
    if (
        frame.height != request["row_count"]
        or frame["__vu_row_id"].n_unique() != frame.height
    ):
        raise ProjectError("Kaynak kayıt sayısı/RowId uyuşmuyor.")
    series = normalize(
        frame, request["columns"], spec, request.get("semantic_metadata")
    )
    previous = request.get("development")
    if mode == "final" and (
        not previous
        or previous["mode"] != "development"
        or previous["spec"] != spec.data()
        or previous["snapshot_fingerprint"] != request["fingerprint"]
    ):
        raise ProjectError(
            "Final için aynı ayar/snapshot ile kayıtlı geliştirme koşusu gerekli."
        )
    groups = []
    methods = ["naive"] + (["seasonal-naive"] if spec.seasonal_period else [])
    if spec.model != "none":
        methods.append(spec.model)
    for g in series:
        control.check()
        s = g["series"]
        cutoff = len(s) - spec.test_periods
        first_origin = cutoff - spec.folds * spec.horizon
        if first_origin < spec.minimum_history:
            raise ProjectError(
                f"{g['group']}: çok kısa seri. En az {spec.minimum_history + spec.folds * spec.horizon + spec.test_periods} dönem gerekli; her ilk eğitimde ≥{spec.minimum_history} geçmiş ve mevsimsel seçimde ≥3 tam dönem."
            )
        y = s.iloc[:cutoff].to_numpy()
        comparisons, folds, failed = [], [], []
        if mode == "development":
            for method in methods:
                actuals, predictions, method_folds = [], [], []
                try:
                    for origin in range(first_origin, cutoff, spec.horizon):
                        pred = forecast(
                            y[:origin],
                            spec.horizon,
                            method,
                            spec.seasonal_period,
                            control,
                        )
                        actual = y[origin : origin + spec.horizon].tolist()
                        actuals.extend(actual)
                        predictions.extend(pred)
                        method_folds.append(
                            dict(
                                method=method,
                                train_end=s.index[origin - 1].isoformat(),
                                validation_start=s.index[origin].isoformat(),
                                validation_end=s.index[
                                    origin + spec.horizon - 1
                                ].isoformat(),
                                train_row_ids=list(
                                    chain.from_iterable(g["members"][:origin])
                                ),
                                validation_row_ids=list(
                                    chain.from_iterable(
                                        g["members"][origin : origin + spec.horizon]
                                    )
                                ),
                                metrics=metrics(actual, pred),
                            )
                        )
                    comparisons.append(
                        dict(method=method, **metrics(actuals, predictions))
                    )
                    folds.extend(method_folds)
                except ProjectError as error:
                    if method in ("naive", "seasonal-naive"):
                        raise
                    failed.append(
                        dict(method=method, reason=str(error), status="invalid")
                    )
            chosen = min(comparisons, key=lambda c: c["mae"])["method"]
        else:
            saved = next(
                (
                    p
                    for p in previous["groups"]
                    if (p["group"], p["group_type"]) == (g["group"], g["group_type"])
                ),
                None,
            )
            if not saved or saved["train_end"] != s.index[cutoff - 1].isoformat():
                raise ProjectError("Kayıtlı grup/kesim tarihi uyuşmuyor.")
            chosen = saved["chosen"]
            comparisons, failed = saved["comparisons"], saved["invalid_models"]
        steps = spec.horizon if mode == "development" else spec.test_periods
        full_predictions = forecast(
            y, spec.test_periods + spec.horizon, chosen, spec.seasonal_period, control
        )
        predictions = full_predictions[:steps]
        future_dates = pd.date_range(
            s.index[-1], periods=spec.horizon + 1, freq=spec.frequency
        )[1:]
        future_points = [
            dict(date=t.isoformat(), predicted=p, actual=None)
            for t, p in zip(future_dates, full_predictions[spec.test_periods :])
        ]
        points = [
            dict(
                date=s.index[cutoff + i].isoformat(),
                predicted=p,
                actual=float(s.iloc[cutoff + i]) if mode == "final" else None,
            )
            for i, p in enumerate(predictions)
        ]
        final = []
        if mode == "final":
            actual = s.iloc[cutoff:].to_list()
            for method in list(
                dict.fromkeys([*methods[: 1 + bool(spec.seasonal_period)], chosen])
            ):
                pred = forecast(y, steps, method, spec.seasonal_period, control)
                final.append(dict(method=method, **metrics(actual, pred)))
        features = historical_features(y, spec.window)
        tail = [
            dict(date=s.index[i].isoformat(), actual=float(y[i]), **features[i])
            for i in range(max(0, cutoff - 120), cutoff)
        ]
        seasonal = (
            [
                dict(phase=i, mean=float(np.mean(y[i :: spec.seasonal_period])))
                for i in range(spec.seasonal_period)
            ]
            if spec.seasonal_period
            else []
        )
        groups.append(
            dict(
                group=g["group"],
                group_type=g["group_type"],
                timezone=g["timezone"],
                periods=len(s),
                duplicate_dates=g["duplicates"],
                missing_periods=0,
                train_end=s.index[cutoff - 1].isoformat(),
                test_start=s.index[cutoff].isoformat(),
                test_end=s.index[-1].isoformat(),
                train_row_ids=list(chain.from_iterable(g["members"][:cutoff])),
                test_row_ids=list(chain.from_iterable(g["members"][cutoff:])),
                chosen=chosen,
                comparisons=comparisons,
                invalid_models=failed,
                folds=folds,
                trend_per_period=float(np.polyfit(np.arange(len(y)), y, 1)[0]),
                seasonal_profile=seasonal,
                history=tail,
                forecast=points,
                future_forecast=future_points,
                final_metrics=final,
            )
        )
    return dict(
        schema="TimeSeriesRun/v1",
        run_id="ts:" + uid(),
        dataset_version=request["version_id"],
        snapshot_fingerprint=request["fingerprint"],
        source_snapshot_id=request["source_snapshot_id"],
        created_at=datetime.now(UTC).isoformat(),
        spec=spec.data(),
        mode=mode,
        development_run_id=previous["run_id"] if mode == "final" else None,
        groups=groups,
        interval=None,
        feature_policy="shift(1), trailing only; no future fill",
        scope="Her grupta son dönem final test; geliştirme yalnız önceki kayıtlar. Rastgele bölme yok.",
        warning="Mevsim profili betimseldir; trend kalıcılığı kanıtı değildir. Tahmin aralığı desteklenmiyor. MAE/RMSE ölçüm biriminde; MAPE sıfırda tanımsız.",
    )


def validate_run(value, dataset):
    if value.get("advanced", {}).get("schema") == "SignalRun/v1":
        from veri_ufku.modeling.signals import validate

        return validate(value, dataset)
    if value.get("advanced"):
        from veri_ufku.modeling.temporal import validate

        return validate(value, dataset)

    spec = TimeSeriesSpec.from_dict(value["spec"])
    spec.validate(dataset["import_metadata"]["columns"])
    if (
        value["schema"] != "TimeSeriesRun/v1"
        or value["dataset_version"] != dataset["version_id"]
        or value["interval"] is not None
        or value["mode"] not in ("development", "final")
    ):
        raise ProjectError("Zaman serisi kayıt kapsamı geçersiz.")
    if not value["groups"] or len(value["groups"]) > 20:
        raise ProjectError("Seri grup kaydı geçersiz.")
    all_ids = []
    for g in value["groups"]:
        train, test = g["train_row_ids"], g["test_row_ids"]
        if (
            set(train) & set(test)
            or len(set(train + test)) != len(train + test)
            or not train
            or not test
        ):
            raise ProjectError("Geçmiş/final RowId ayrımı geçersiz.")
        if (
            pd.Timestamp(g["train_end"]) >= pd.Timestamp(g["test_start"])
            or g["missing_periods"] != 0
        ):
            raise ProjectError("Geçmişten geleceğe tarih ayrımı geçersiz.")
        if g["chosen"] not in {
            c["method"] for c in g["comparisons"]
        } or "naive" not in {c["method"] for c in g["comparisons"]}:
            raise ProjectError("Gerçek baseline karşılaştırması eksik.")
        if value["mode"] == "development" and (
            g["final_metrics"] or any(p["actual"] is not None for p in g["forecast"])
        ):
            raise ProjectError("Geliştirme sonucunda final hedefleri açılamaz.")
        for fold in g["folds"]:
            if (
                set(fold["train_row_ids"]) & set(fold["validation_row_ids"])
                or not set(fold["train_row_ids"] + fold["validation_row_ids"])
                <= set(train)
                or pd.Timestamp(fold["train_end"])
                >= pd.Timestamp(fold["validation_start"])
            ):
                raise ProjectError("Rolling-origin eğitim/doğrulama sızıntısı.")
        for c in g["comparisons"] + g["final_metrics"]:
            if (
                any(not math.isfinite(c[k]) or c[k] < 0 for k in ("mae", "rmse"))
                or c["mape"] is not None
            ):
                raise ProjectError("Seri skor kaydı geçersiz.")
        all_ids += train + test
    if (
        len(set(all_ids)) != len(all_ids)
        or len(all_ids) != dataset["import_metadata"]["row_count"]
    ):
        raise ProjectError("Gruplar kaynak kayıtları tam ve ayrık korumalı.")
