"""Bounded regular multi-channel signals; source identities and block-isolated windows."""

import importlib.metadata
import json
import math
import time
import warnings
from dataclasses import asdict
from datetime import UTC, datetime
from fractions import Fraction

import numpy as np
import polars as pl
from scipy import signal
from scipy.fft import rfft, rfftfreq

from veri_ufku.analytics.dataset import checked
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.signal_contracts import SignalSpec
from veri_ufku.storage.project_model import ProjectError, digest, encode, uid


def token(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ProjectError("Kaynak kimlik/event/label NaN/inf olamaz.")
    return encode([type(value).__name__, str(value)]).decode()


def normalize(frame, columns, base, spec):
    spec.validate(base, columns)
    names = {c["id"]: c["name"] for c in columns}
    time_col = frame[names[base.date]]
    if not time_col.dtype.is_numeric() or time_col.null_count():
        raise ProjectError(
            "Sinyal zamanı sayısal s/ms/us/ns olmalı; Date/Datetime açık hazırlık ister."
        )
    selected = [
        base.date,
        *spec.channels,
        *([base.group] if base.group else []),
        *spec.block_columns,
        *([spec.label] if spec.label else []),
        *([spec.event] if spec.event else []),
    ]
    if (
        frame.height > 32768
        or frame["__vu_row_id"].n_unique() != frame.height
        or any(frame[names[c]].null_count() for c in selected)
    ):
        raise ProjectError(
            "32768 kayıt bütçesi/benzersiz RowId; seçili alanlarda missing desteklenmiyor."
        )
    for c in spec.channels:
        if not frame[names[c]].dtype.is_numeric():
            raise ProjectError("Kanallar sonlu sayısal ölçüm olmalı.")
    labels = (
        frame[names[base.group]].to_list()
        if base.group
        else ["recording"] * frame.height
    )
    groups = {}
    for i, label in enumerate(labels):
        groups.setdefault(token(label), []).append(i)
    if not groups or len(groups) > 16:
        raise ProjectError("1–16 kayıt gerekli.")
    records = []
    factor = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9}[spec.time_unit]
    for key, positions in groups.items():
        if not spec.segment_length <= len(positions) <= 8192:
            raise ProjectError("Her kayıt segment_length..8192 örnek içermeli.")
        raw_time = time_col.gather(positions).to_list()
        # Subtract integer origin before Float64 to preserve large timestamp increments.
        t = np.array([x - raw_time[0] for x in raw_time], float) * factor
        if not np.isfinite(t).all() or not np.allclose(
            np.diff(t), 1 / spec.sample_rate, rtol=1e-6, atol=1e-10 / spec.sample_rate
        ):
            raise ProjectError(
                "Düzensiz/duplicate/ters sampling veya sample_rate uyumsuz: standard FFT kapalı. Sessiz interpolate/sort yok."
            )
        data = {}
        for c in spec.channels:
            raw = frame[names[c]].gather(positions).to_list()
            y = np.array(raw, float)
            if not np.isfinite(y).all() or any(a != float(b) for a, b in zip(raw, y)):
                raise ProjectError("Kanal nonfinite veya Float64 hassasiyet kaybı.")
            data[c] = y
        blocks = {}
        for c in spec.block_columns:
            vals = frame[names[c]].gather(positions).to_list()
            if len({token(x) for x in vals}) != 1:
                raise ProjectError("Kayıt içinde kişi/cihaz/oturum kimliği değişemez.")
            blocks[c] = token(vals[0])
        label = None
        if spec.label:
            vals = frame[names[spec.label]].gather(positions).to_list()
            if len({token(x) for x in vals}) != 1:
                raise ProjectError("Classification label kayıt içinde sabit olmalı.")
            label = token(vals[0])
        events = (
            frame[names[spec.event]].gather(positions).to_list() if spec.event else None
        )
        records.append(
            dict(
                recording_id=key,
                row_ids=frame["__vu_row_id"].gather(positions).to_list(),
                time_origin=str(raw_time[0]),
                t=t,
                values=data,
                blocks=blocks,
                label=label,
                events=events,
                source_digest=digest(
                    encode(
                        dict(
                            time=raw_time,
                            channels={c: y.tolist() for c, y in data.items()},
                            blocks=blocks,
                            label=label,
                            events=events,
                        )
                    )
                ),
            )
        )
    return records


def split(records, spec):
    ids = {r["recording_id"] for r in records}
    train, val = set(spec.train_recordings), set(spec.validation_recordings)
    if train & val or train | val != ids:
        raise ProjectError(
            "Classification tüm kayıtları açık ve ayrık train/validation olarak seçmeli."
        )
    a, b = ([r for r in records if r["recording_id"] in side] for side in (train, val))
    for col in spec.block_columns:
        if {r["blocks"][col] for r in a} & {r["blocks"][col] for r in b}:
            raise ProjectError(
                "Overlap sızıntısı: seçili kişi/cihaz/oturum kimliği iki tarafta ortak."
            )
    if {i for r in a for i in r["row_ids"]} & {i for r in b for i in r["row_ids"]}:
        raise ProjectError("Overlap kaynak RowId train/validation arasında ortak.")
    classes = {r["label"] for r in a}
    if len(classes) < 2 or not {r["label"] for r in b} <= classes:
        raise ProjectError(
            "Train en az2 sınıf; validation unseen class desteklenmiyor."
        )
    return a, b


def ratio(spec):
    if not spec.target_rate:
        return (1, 1)
    f = Fraction(spec.target_rate / spec.sample_rate).limit_denominator(100)
    if max(f.numerator, f.denominator) > 100 or not math.isclose(
        float(f), spec.target_rate / spec.sample_rate, rel_tol=1e-9
    ):
        raise ProjectError("Resampling oranı tam up/down≤100 rasyonel oran olmalı.")
    return f.numerator, f.denominator


def preflight(records, spec, control):
    up, down = ratio(spec)
    cells = windows = outputs = 0
    for r in records:
        n = math.ceil(len(r["t"]) * up / down)
        if not spec.segment_length <= n <= 8192:
            raise ProjectError(
                "Resample sonrası kayıt segment_length..8192 bütçesi dışında."
            )
        count = 1 + (n - spec.segment_length) // (spec.segment_length - spec.overlap)
        cells += count * (spec.segment_length // 2 + 1) * len(spec.channels)
        windows += count
        outputs += n * len(spec.channels)
    ram = (cells * 5 + outputs * 12) * 8
    if cells > 131072 or windows > 2000 or ram > control.budget.ram_bytes:
        raise ProjectError(
            f"Sinyal önkontrolü: {cells} STFT hücresi, {windows} pencere, yaklaşık {ram} RAM bytes;131072cells/2000windows/budget sınırı."
        )
    return dict(
        stft_cells=cells,
        windows=windows,
        estimated_ram_bytes=ram,
        resample_up=up,
        resample_down=down,
    )


def process(y, spec, control):
    control.check()
    fs = spec.sample_rate
    out = y.copy()
    meta = dict(
        detrend=spec.detrend,
        mode=spec.mode,
        window=spec.window,
        resample=None,
        filter=None,
    )
    if spec.detrend != "none":
        out = signal.detrend(out, type=spec.detrend)
    if spec.target_rate:
        up, down = ratio(spec)
        out = signal.resample_poly(
            out, up, down, window=("kaiser", 5.0), padtype="constant", cval=0
        )
        fs = spec.target_rate
        meta["resample"] = dict(
            up=up,
            down=down,
            filter="polyphase zero-phase anti-alias FIR Kaiser beta5",
            boundary="constant zero padding",
            offline_only=True,
            loss_acknowledged=spec.allow_band_loss,
            lineage="all source recording rows conservative FIR dependency; nominal times are derived",
        )
    if spec.filter_type != "none":
        sos = signal.butter(
            spec.order,
            spec.cutoff if len(spec.cutoff) == 2 else spec.cutoff[0],
            btype=spec.filter_type,
            fs=fs,
            output="sos",
        )
        try:
            out = (
                signal.sosfiltfilt(sos, out, padtype="odd")
                if spec.zero_phase
                else signal.sosfilt(sos, out)
            )
        except ValueError as error:
            raise ProjectError(
                "Filtre için kayıt/padding uzunluğu uygun değil."
            ) from error
        f, response = signal.freqz_sos(sos, worN=256, fs=fs)
        gain = abs(response) ** (2 if spec.zero_phase else 1)
        phase = np.zeros(len(f)) if spec.zero_phase else np.unwrap(np.angle(response))
        # Group delay is frequency-dependent, not a universal shift to remove silently.
        delay = -np.gradient(phase, f * 2 * np.pi)
        meta["filter"] = dict(
            type=spec.filter_type,
            cutoff_hz=spec.cutoff,
            design_order=spec.order,
            effective_order=spec.order
            * (2 if spec.filter_type.startswith("band") else 1)
            * (2 if spec.zero_phase else 1),
            zero_phase=spec.zero_phase,
            initial_state="odd extension forward/backward"
            if spec.zero_phase
            else "zero/rest; start transient retained",
            frequency_hz=f.tolist(),
            gain=gain.tolist(),
            group_delay_seconds=delay.tolist(),
            cutoff_definition="single-pass -3dB; forward/backward -6dB at same cutoff",
            warning="Offline future dependence/edge transient; no online prediction"
            if spec.zero_phase
            else "Causal IIR; frequency-dependent delay/start transient; no silent time shift",
        )
    if not np.isfinite(out).all():
        raise ProjectError("Filtre sonlu çıktı üretmedi.")
    control.check()
    return out, fs, meta


def spectrum(y, fs, window):
    w = signal.get_window(window, len(y), fftbins=True)
    z = rfft(y * w)
    amplitude = abs(z) / w.sum()
    density = abs(z) ** 2 / (fs * np.sum(w**2))
    end = -1 if len(y) % 2 == 0 else None
    amplitude[1:end] *= 2
    density[1:end] *= 2
    return dict(
        frequency_hz=rfftfreq(len(y), 1 / fs).tolist(),
        amplitude=amplitude.tolist(),
        density=density.tolist(),
        window=window,
        coherent_gain=float(w.mean()),
        energy_sum=float(np.sum(w**2)),
        normalization="one-sided peak amplitude |FFT|/sum(window), interior×2; PSD |FFT|²/(fs sum(window²)), interior×2; DC/even Nyquist not doubled",
        resolution_hz=fs / len(y),
    )


def analyze(y, fs, spec, control):
    fft = spectrum(y, fs, spec.window)
    w = signal.get_window(spec.window, spec.segment_length, fftbins=True)
    f, p = signal.welch(
        y,
        fs=fs,
        window=w,
        nperseg=spec.segment_length,
        noverlap=spec.overlap,
        nfft=spec.segment_length,
        detrend=False,
        scaling=spec.scaling,
        average="mean",
    )
    control.check()
    sf, st, z = signal.stft(
        y,
        fs=fs,
        window=w,
        nperseg=spec.segment_length,
        noverlap=spec.overlap,
        nfft=spec.segment_length,
        detrend=False,
        boundary=None,
        padded=False,
        scaling="psd",
    )
    power = abs(z) ** 2
    power[1:-1] *= (
        2  # segment_length can be odd: include last positive bin below Nyquist.
    )
    if spec.segment_length % 2:
        power[-1] *= 2
    peaks, props = signal.find_peaks(
        np.array(fft["amplitude"]),
        prominence=spec.prominence,
        distance=spec.peak_distance,
    )
    time_peaks, tp = signal.find_peaks(
        y, prominence=spec.prominence, distance=spec.peak_distance
    )
    return dict(
        fft=fft,
        welch=dict(
            frequency_hz=f.tolist(),
            values=p.tolist(),
            scaling=spec.scaling,
            unit_suffix="²/Hz" if spec.scaling == "density" else "²",
            segment_length=spec.segment_length,
            overlap=spec.overlap,
            nfft=spec.segment_length,
            average="mean",
            detrend=False,
        ),
        stft=dict(
            frequency_hz=sf.tolist(),
            center_seconds=st.tolist(),
            available_at_seconds=(st + (spec.segment_length / 2 - 1) / fs).tolist(),
            power=power.tolist(),
            scaling="one-sided PSD, linear power/unit²/Hz; no dB clipping",
            complex_normalization="SciPy psd sqrt(fs sum(window²)); positive interior power×2",
            boundary=None,
            padded=False,
            segment_length=spec.segment_length,
            overlap=spec.overlap,
        ),
        frequency_peaks=[
            dict(
                bin=int(i),
                frequency_hz=fft["frequency_hz"][i],
                amplitude=fft["amplitude"][i],
                prominence=float(props["prominences"][j]),
            )
            for j, i in enumerate(peaks[:128])
        ],
        time_peaks=[
            dict(
                index=int(i),
                seconds=float(i / fs),
                value=float(y[i]),
                prominence=float(tp["prominences"][j]),
            )
            for j, i in enumerate(time_peaks[:128])
        ],
        peaks_total=dict(
            frequency=len(peaks), time=len(time_peaks), displayed_limit=128
        ),
    )


def event_segments(record):
    if record["events"] is None:
        return []
    result = []
    start = 0
    events = record["events"]
    for end in range(1, len(events) + 1):
        if end == len(events) or token(events[end]) != token(events[start]):
            result.append(
                dict(
                    event=token(events[start]),
                    start_index=start,
                    stop_index=end,
                    start_seconds=float(record["t"][start]),
                    end_seconds=float(record["t"][end - 1]),
                    source_row_ids=record["row_ids"][start:end],
                    dependency_scope="segmentation of source event labels; processing metadata may reference full recording",
                )
            )
            start = end
    if len(result) > 512:
        raise ProjectError("Event segmentation512 segment sınırı.")
    return result


def features(record, processed, fs, spec, partition, control):
    result = []
    n = len(next(iter(processed.values())))
    stride = spec.segment_length - spec.overlap
    up, down = ratio(spec)
    for start in range(0, n - spec.segment_length + 1, stride):
        control.check()
        end = start + spec.segment_length
        vals = []
        for c in spec.channels:
            y = processed[c][start:end]
            s = spectrum(y, fs, spec.window)
            a = np.array(s["amplitude"])
            f = np.array(s["frequency_hz"])
            p = np.array(s["density"])
            vals.extend(
                [
                    float(y.mean()),
                    float(y.std()),
                    float(np.sqrt(np.mean(y**2))),
                    float(f[np.argmax(a[1:]) + 1]) if a[1:].max() > 1e-12 else 0.0,
                    float(np.sum(f * p) / p.sum()) if p.sum() > 0 else 0.0,
                ]
            )
        lo, hi = (
            max(0, int(start * down / up)),
            min(len(record["row_ids"]), math.ceil(end * down / up)),
        )
        result.append(
            dict(
                window_id="window:"
                + digest(encode([record["recording_id"], start, end]))[:24],
                recording_id=record["recording_id"],
                partition=partition,
                start_index=start,
                stop_index=end,
                available_at_seconds=(end - 1) / fs,
                source_row_ids=record["row_ids"][lo:hi],
                dependency_recording_id=record["recording_id"],
                dependency_scope="whole own recording for offline detrend/FIR/zero-phase; causal history through window end otherwise",
                values=vals,
                label=record["label"],
            )
        )
    return result


def classify(windows, spec, control):
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    a = [w for w in windows if w["partition"] == "train"]
    b = [w for w in windows if w["partition"] == "validation"]
    x = np.array([w["values"] for w in a])
    y = [w["label"] for w in a]
    control.check()
    pipeline = make_pipeline(
        StandardScaler(), LogisticRegression(max_iter=500, random_state=spec.seed)
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pipeline.fit(x, y)
    if any(issubclass(w.category, ConvergenceWarning) for w in caught):
        raise ProjectError(
            "Signal classifier convergence başarısız; güvenilir rozet yok."
        )
    pred = pipeline.predict(np.array([w["values"] for w in b])).tolist()
    control.check()
    classes = pipeline[-1].classes_.tolist()
    majority = max(classes, key=y.count)
    return dict(
        method="train-only StandardScaler + LogisticRegression; fixed template no tuning",
        classes=classes,
        feature_names=[
            c + ":" + f
            for c in spec.channels
            for f in ("mean", "std", "rms", "peak_hz", "centroid_hz")
        ],
        original_column_ids=spec.channels,
        numeric_model=dict(
            mean=pipeline[0].mean_.tolist(),
            scale=pipeline[0].scale_.tolist(),
            coefficient=pipeline[-1].coef_.tolist(),
            intercept=pipeline[-1].intercept_.tolist(),
        ),
        fit_window_ids=[w["window_id"] for w in a],
        fit_row_ids=sorted({i for w in a for i in w["source_row_ids"]}),
        validation_window_ids=[w["window_id"] for w in b],
        predictions=[
            dict(
                window_id=w["window_id"],
                recording_id=w["recording_id"],
                actual=w["label"],
                predicted=v,
            )
            for w, v in zip(b, pred)
        ],
        accuracy=sum(w["label"] == v for w, v in zip(b, pred)) / len(b),
        baseline_accuracy=sum(w["label"] == majority for w in b) / len(b),
        n=len(b),
        independent_validation_recordings=len({w["recording_id"] for w in b}),
        warnings=[str(w.message) for w in caught],
        warning="Overlapping windows within partition correlated; window n is not independent-person n; no prospective accuracy/causality claim. Fitted model persistence/new-file prediction closed.",
    )


def calculate(request, base, workspace, control=None):
    from veri_ufku.storage.experiment_store import capture

    control = control or Control()
    started = time.monotonic()
    spec = SignalSpec.from_dict(base.advanced, base, request["columns"])
    if request.get("mode", "development") != "development":
        raise ProjectError(
            "Signal final test serving ayrı desteklenmiyor; validation test diye sunulmaz."
        )
    if request["row_count"] > 32768:
        raise ProjectError("32768 signal source rows bütçesi.")
    checked(request, control)
    access = datetime.now(UTC).isoformat()
    frame = pl.read_parquet(request["path"])
    control.check()
    if frame.height != request["row_count"]:
        raise ProjectError("Kaynak kayıt sayısı uyuşmuyor.")
    records = normalize(frame, request["columns"], base, spec)
    if spec.task == "classification":
        split(records, spec)  # before filtering/features/window production
    budget = preflight(records, spec, control)
    output = []
    windows = []
    for ri, r in enumerate(records):
        control.progress("signal", ri, len(records))
        control.check()
        channels = []
        processed = {}
        for c, y in r["values"].items():
            v, fs, meta = process(y, spec, control)
            processed[c] = v
            analysis = analyze(v, fs, spec, control)
            ii = np.unique(np.linspace(0, len(v) - 1, min(1024, len(v)), dtype=int))
            preview = dict(
                indices=ii.tolist(),
                seconds=(ii / fs).tolist(),
                values=v[ii].tolist(),
                n_total=len(v),
                n_preview=len(ii),
                scope="uniform index visual preview only; calculations use all selected samples",
                source_identity="derived sample ids if resampled; full source recording RowIds retained",
            )
            for peak in analysis["time_peaks"]:
                peak["source_row_id"] = (
                    r["row_ids"][peak["index"]] if not spec.target_rate else None
                )
                peak["derived_sample_id"] = (
                    f"sample:{r['recording_id']}:{c}:{peak['index']}"
                    if spec.target_rate
                    else None
                )
            channels.append(
                dict(
                    column_id=c,
                    unit=spec.channel_units[c],
                    processing=meta,
                    preview=preview,
                    **analysis,
                )
            )
        partition = (
            ("train" if r["recording_id"] in spec.train_recordings else "validation")
            if spec.task == "classification"
            else "analysis"
        )
        windows.extend(features(r, processed, fs, spec, partition, control))
        output.append(
            dict(
                recording_id=r["recording_id"],
                source_row_ids=r["row_ids"],
                source_digest=r["source_digest"],
                source_time_origin=r["time_origin"],
                source_time_unit=spec.time_unit,
                source_start_seconds=float(r["t"][0]),
                source_end_seconds=float(r["t"][-1]),
                source_n=len(r["t"]),
                output_n=len(next(iter(processed.values()))),
                unused_tail_samples=(
                    len(next(iter(processed.values()))) - spec.segment_length
                )
                % (spec.segment_length - spec.overlap),
                window_policy="complete windows only; incomplete trailing samples retained in source, not feature windows",
                sample_rate_hz=fs,
                blocks=r["blocks"],
                partition=partition,
                channels=channels,
                events=event_segments(r),
                source_snapshot_id=request["source_snapshot_id"],
            )
        )
    classifier = (
        classify(windows, spec, control) if spec.task == "classification" else None
    )
    cap = "model.signal." + spec.operation
    created = datetime.now(UTC).isoformat()
    prov = asdict(
        Provenance(
            provenance_id="provenance:" + uid(),
            dataset_versions=(request["version_id"],),
            config_revision=0,
            capability_id=cap,
            parameters_hash=digest(encode(base.data())),
            environment=(("scipy", importlib.metadata.version("scipy")),),
            created_at=created,
            scope="whole recording isolated transforms; split before windows; available_at endpoint; no source edits",
            seed=spec.seed,
            seed_reason="deterministic LBFGS initialization/spectra; seed retained in recipe, no sampling",
            source_snapshot_ids=(request["source_snapshot_id"],),
        )
    )
    capture_data = capture(dict(spec=base.data()))
    capture_data["environment"]["scipy"] = importlib.metadata.version("scipy")
    capture_data["environment_hash"] = digest(encode(capture_data["environment"]))
    capture_data["config_scope"] = (
        "full regular signal schema, preprocessing and explicit recording/block window split"
    )
    return dict(
        schema="TimeSeriesRun/v1",
        run_id="ts:" + uid(),
        status="completed",
        dataset_version=request["version_id"],
        snapshot_fingerprint=request["fingerprint"],
        source_snapshot_id=request["source_snapshot_id"],
        created_at=created,
        data_access_at=access,
        elapsed_seconds=time.monotonic() - started,
        seed=spec.seed,
        spec=base.data(),
        mode="development",
        development_run_id=None,
        groups=[],
        interval=None,
        scope="regular multi-channel signal; no silent interpolation",
        warning="Nyquist cannot prove absence of acquisition aliasing. Analog band is a declaration. Offline processing uses future samples; online mode has causal-only transforms, not a streaming deployment.",
        capture=capture_data,
        plan=dict(
            split_id="split:"
            + digest(
                encode(
                    [
                        spec.train_recordings,
                        spec.validation_recordings,
                        spec.block_columns,
                    ]
                )
            ),
            protocol_id="protocol:" + digest(encode(spec.data())),
        ),
        advanced=dict(
            schema="SignalRun/v1",
            spec=spec.data(),
            provenance=json.loads(encode(prov)),
            compute_budget=asdict(control.budget),
            preflight=budget,
            recordings=output,
            windows=windows,
            classifier=classifier,
        ),
    )


def validate(value, dataset):
    from veri_ufku.domain.capabilities import CAPABILITIES
    from veri_ufku.modeling.time_series_contracts import TimeSeriesSpec

    try:
        base = TimeSeriesSpec.from_dict(value["spec"])
        spec = SignalSpec.from_dict(
            base.advanced, base, dataset["import_metadata"]["columns"]
        )
        a = value["advanced"]
        p = a["provenance"]
        if (
            value["schema"] != "TimeSeriesRun/v1"
            or a["schema"] != "SignalRun/v1"
            or a["spec"] != spec.data()
            or value["dataset_version"] != dataset["version_id"]
            or value["source_snapshot_id"]
            != dataset["import_metadata"]["source_snapshot_id"]
            or value["mode"] != "development"
            or value["groups"]
            or value["status"] != "completed"
            or value["interval"] is not None
        ):
            raise ValueError
        if (
            p["parameters_hash"] != digest(encode(base.data()))
            or p["capability_id"] != "model.signal." + spec.operation
            or p["capability_id"] not in CAPABILITIES
            or p["dataset_versions"] != [value["dataset_version"]]
            or p["source_snapshot_ids"] != [value["source_snapshot_id"]]
        ):
            raise ValueError
        ids = [i for r in a["recordings"] for i in r["source_row_ids"]]
        if len(ids) != dataset["import_metadata"]["row_count"] or len(set(ids)) != len(
            ids
        ):
            raise ValueError
        encode(value)  # finite safe JSON, not executable model input
        if spec.task == "classification":
            windows = a["windows"]
            t = {
                i
                for w in windows
                if w["partition"] == "train"
                for i in w["source_row_ids"]
            }
            v = {
                i
                for w in windows
                if w["partition"] == "validation"
                for i in w["source_row_ids"]
            }
            if t & v or len({w["window_id"] for w in windows}) != len(windows):
                raise ValueError
            validate_classifier(a)
            c = a["classifier"]
            pred = c["predictions"]
            if c["n"] != len(pred) or c["accuracy"] != sum(
                x["actual"] == x["predicted"] for x in pred
            ) / len(pred):
                raise ValueError
    except (KeyError, ValueError, TypeError, ZeroDivisionError) as error:
        raise ProjectError(
            "Signal artifact şema/provenance/kimlik/metric uyuşmuyor."
        ) from error


def validate_source(value, frame, columns):
    from veri_ufku.modeling.time_series_contracts import TimeSeriesSpec

    base = TimeSeriesSpec.from_dict(value["spec"])
    spec = SignalSpec.from_dict(base.advanced, base, columns)
    records = normalize(frame, columns, base, spec)
    a = value["advanced"]
    control = Control()
    if spec.task == "classification":
        split(records, spec)
    try:
        expected_windows = []
        for r, saved in zip(records, a["recordings"], strict=True):
            if (
                r["recording_id"] != saved["recording_id"]
                or r["source_digest"] != saved["source_digest"]
                or r["row_ids"] != saved["source_row_ids"]
                or r["blocks"] != saved["blocks"]
                or r["time_origin"] != saved["source_time_origin"]
                or spec.time_unit != saved["source_time_unit"]
                or len(r["t"]) != saved["source_n"]
                or float(r["t"][-1]) != saved["source_end_seconds"]
                or saved["source_start_seconds"] != 0
                or saved["sample_rate_hz"] != (spec.target_rate or spec.sample_rate)
                or event_segments(r) != saved["events"]
            ):
                raise ValueError
            processed = {}
            for channel, c in zip(saved["channels"], spec.channels, strict=True):
                y, fs, meta = process(r["values"][c], spec, control)
                processed[c] = y
                actual = analyze(y, fs, spec, control)
                if (
                    channel["column_id"] != c
                    or channel["unit"] != spec.channel_units[c]
                    or meta != channel["processing"]
                ):
                    raise ValueError
                for peak in actual["time_peaks"]:
                    peak["source_row_id"] = (
                        r["row_ids"][peak["index"]] if not spec.target_rate else None
                    )
                    peak["derived_sample_id"] = (
                        f"sample:{r['recording_id']}:{c}:{peak['index']}"
                        if spec.target_rate
                        else None
                    )
                ii = np.unique(np.linspace(0, len(y) - 1, min(1024, len(y)), dtype=int))
                preview = channel["preview"]
                if (
                    preview["indices"] != ii.tolist()
                    or preview["seconds"] != (ii / fs).tolist()
                    or preview["values"] != y[ii].tolist()
                    or preview["n_total"] != len(y)
                    or preview["n_preview"] != len(ii)
                ):
                    raise ValueError
                for key in ("fft", "welch", "stft", "frequency_peaks", "peaks_total"):
                    if actual[key] != channel[key]:
                        raise ValueError
            partition = (
                (
                    "train"
                    if r["recording_id"] in spec.train_recordings
                    else "validation"
                )
                if spec.task == "classification"
                else "analysis"
            )
            if saved["partition"] != partition:
                raise ValueError
            expected_windows.extend(
                features(r, processed, fs, spec, partition, control)
            )
        if spec.task == "classification":
            validate_classifier(a)
        if expected_windows != a["windows"]:
            raise ValueError
    except (ValueError, KeyError, TypeError) as error:
        raise ProjectError(
            "Signal artifact gerçek kaynak/spektrum/pencere kimliği ile uyuşmuyor; refit yapılmadı."
        ) from error


def validate_classifier(advanced):
    """Validate safe numeric parameters and actual predictions without fitting/importing models."""
    windows = advanced["windows"]
    c = advanced["classifier"]
    a = [w for w in windows if w["partition"] == "train"]
    b = [w for w in windows if w["partition"] == "validation"]
    x = np.asarray([w["values"] for w in a], float)
    mean = np.mean(x, axis=0)
    scale = np.std(x, axis=0)
    variance = np.var(x, axis=0)
    eps = np.finfo(np.float64).eps
    scale[variance <= len(x) * eps * variance + (len(x) * mean * eps) ** 2] = 1
    m = c["numeric_model"]
    mu = np.asarray(m["mean"])
    sc = np.asarray(m["scale"])
    coef = np.asarray(m["coefficient"])
    intercept = np.asarray(m["intercept"])
    classes = sorted({w["label"] for w in a})
    if (
        c["classes"] != classes
        or not np.allclose(mu, mean, atol=1e-12)
        or not np.allclose(sc, scale, atol=1e-12)
        or not np.isfinite(coef).all()
        or not np.isfinite(intercept).all()
        or coef.shape != (1 if len(classes) == 2 else len(classes), x.shape[1])
    ):
        raise ValueError
    score = ((np.asarray([w["values"] for w in b]) - mu) / sc) @ coef.T + intercept
    pred = (
        [classes[int(v > 0)] for v in score[:, 0]]
        if len(classes) == 2
        else [classes[i] for i in np.argmax(score, axis=1)]
    )
    expected = [
        dict(
            window_id=w["window_id"],
            recording_id=w["recording_id"],
            actual=w["label"],
            predicted=v,
        )
        for w, v in zip(b, pred)
    ]
    if (
        expected != c["predictions"]
        or c["fit_window_ids"] != [w["window_id"] for w in a]
        or c["fit_row_ids"] != sorted({i for w in a for i in w["source_row_ids"]})
        or c["validation_window_ids"] != [w["window_id"] for w in b]
        or c["independent_validation_recordings"] != len({w["recording_id"] for w in b})
    ):
        raise ValueError
    majority = max(classes, key=[w["label"] for w in a].count)
    if c["baseline_accuracy"] != sum(w["label"] == majority for w in b) / len(b):
        raise ValueError
