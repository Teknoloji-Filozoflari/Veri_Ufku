"""Regular signal reference calculations, offline safety and block/window leakage."""

import math
from contextlib import closing
from dataclasses import replace
from threading import Event
from time import sleep

import numpy as np
import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Canceled, Control
from veri_ufku.modeling.signal_contracts import METHODS, SignalSpec
from veri_ufku.modeling.signals import (
    analyze,
    normalize,
    preflight,
    process,
    spectrum,
    split,
    token,
    validate_source,
)
from veri_ufku.modeling.time_series import TimeSeriesSpec, calculate, validate_run
from veri_ufku.storage.project_model import ProjectError, validate_state
from veri_ufku.storage.project_store import file_hash
from veri_ufku.storage.time_series_store import finish, load


def example(n=512, count=4):
    frames = []
    for i in range(count):
        t = np.arange(n) / 128
        f = 8 if i % 2 == 0 else 16
        y = 2 * np.sin(2 * np.pi * f * t)
        frames.append(
            pl.DataFrame(
                dict(
                    t=t,
                    voltage=y,
                    current=y * 0.5,
                    recording=[f"r{i}"] * n,
                    subject=[f"p{i}"] * n,
                    device=[f"d{i}"] * n,
                    session=[f"s{i}"] * n,
                    label=["A" if i % 2 == 0 else "B"] * n,
                    event=["before"] * (n // 2) + ["after"] * (n - n // 2),
                )
            )
        )
    return pl.concat(frames)


def fixture(tmp_path, operation="spectrogram", task="analysis", frame=None, **kwargs):
    frame = frame if frame is not None else example()
    store = prepare(tmp_path, frame)[0]
    d = store.state["datasets"][-1]
    request = dict(
        path=str(store.path(d["snapshot_uri"])),
        fingerprint=file_hash(store.path(d["snapshot_uri"])),
        columns=d["import_metadata"]["columns"],
        row_count=frame.height,
        version_id=d["version_id"],
        source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
    )
    channels = [column(request, "voltage"), column(request, "current")]
    extra = SignalSpec(
        operation=operation,
        task=task,
        channels=channels,
        channel_units={c: "V" if i == 0 else "A" for i, c in enumerate(channels)},
        event=column(request, "event"),
        **kwargs,
    )
    if task == "classification":
        extra = replace(
            extra,
            label=column(request, "label"),
            block_columns=[
                column(request, c) for c in ["subject", "device", "session"]
            ],
            train_recordings=[token("r0"), token("r1")],
            validation_recordings=[token("r2"), token("r3")],
        )
    base = TimeSeriesSpec(
        date=column(request, "t"),
        measurement=channels[0],
        group=column(request, "recording"),
        advanced=extra.data(),
    )
    return store, request, base, extra


@pytest.mark.parametrize("operation", METHODS)
def test_real_native_signal_operation_source_and_safe_reopen(tmp_path, operation):
    options = {}
    if operation == "resample":
        options["target_rate"] = 64.0
    if operation == "detrend":
        options["detrend"] = "linear"
    if operation == "filter":
        options["filter_type"] = "lowpass"
    if operation == "zero-phase":
        options.update(filter_type="lowpass", zero_phase=True)
    task = "classification" if operation == "classification" else "analysis"
    store, r, base, spec = fixture(tmp_path, operation, task, **options)
    with closing(store):
        before = open(r["path"], "rb").read()
        result = calculate(r, base.data(), tmp_path)
        validate_run(result, store.state["datasets"][-1])
        validate_source(result, pl.read_parquet(r["path"]), r["columns"])
        assert len(result["advanced"]["recordings"]) == 4
        assert (
            result["advanced"]["provenance"]["capability_id"]
            == "model.signal." + operation
        )
        assert result["advanced"]["windows"]
        state, item = finish(store, store.state, result)
        validate_state(state)
        assert load(store, item) == {
            k: v
            for k, v in result.items()
            if k not in ("prior_test_use_ids", "interpretation")
        } | {
            k: state["results"][-1]["time_series"][k]
            for k in ("prior_test_use_ids", "interpretation")
        }
        assert open(r["path"], "rb").read() == before
        records = result["advanced"]["recordings"]
        assert all(
            len(rec["events"]) == 2
            and rec["events"][0]["source_row_ids"] == rec["source_row_ids"][:256]
            for rec in records
        )
        if task == "classification":
            assert result["advanced"]["classifier"]["accuracy"] == 1


@pytest.mark.parametrize("window", ["boxcar", "hann", "hamming", "blackman"])
def test_known_sine_peak_amplitude_and_psd_integral(window):
    fs = 128.0
    n = 1024
    t = np.arange(n) / fs
    y = 2 * np.sin(2 * np.pi * 8 * t)
    s = spectrum(y, fs, window)
    i = np.argmax(s["amplitude"])
    assert s["frequency_hz"][i] == 8 and s["amplitude"][i] == pytest.approx(
        2, rel=1e-10
    )
    assert sum(s["density"]) * (fs / n) == pytest.approx(2, rel=1e-10)
    extra = SignalSpec(segment_length=128, overlap=64, window=window)
    a = analyze(y, fs, extra, Control())
    p = np.array(a["stft"]["power"])
    assert p.mean(axis=1) == pytest.approx(a["welch"]["values"])
    assert a["stft"]["available_at_seconds"][0] == pytest.approx(127 / fs)


def test_dc_even_nyquist_and_odd_final_bin_not_double_error():
    assert spectrum(np.ones(64) * 3, 128, "boxcar")["amplitude"][0] == 3
    assert spectrum(3 * (-1.0) ** np.arange(64), 128, "boxcar")["amplitude"][-1] == 3
    y = 2 * np.sin(2 * np.pi * 4 * np.arange(9) / 9)
    assert spectrum(y, 128, "boxcar")["amplitude"][-1] == pytest.approx(2)


@pytest.mark.parametrize(
    "defect",
    ["irregular", "duplicate", "reversed", "nonfinite", "missing", "rate", "unit"],
)
def test_irregular_standard_fft_and_invalid_signal_rejected(tmp_path, defect):
    store, r, base, extra = fixture(tmp_path, frame=example(count=1))
    with closing(store):
        frame = pl.read_parquet(r["path"])
        if defect in ("irregular", "duplicate", "reversed"):
            ts = frame["t"].to_list()
            ts[7] = (
                ts[6]
                if defect == "duplicate"
                else ts[6] - 0.01
                if defect == "reversed"
                else ts[7] + 0.002
            )
            frame = frame.with_columns(pl.Series("t", ts))
        elif defect == "nonfinite":
            frame = frame.with_columns(
                pl.when(pl.int_range(pl.len()) == 0)
                .then(float("inf"))
                .otherwise(pl.col("voltage"))
                .alias("voltage")
            )
        elif defect == "missing":
            frame = frame.with_columns(
                pl.when(pl.int_range(pl.len()) == 0)
                .then(None)
                .otherwise(pl.col("voltage"))
                .alias("voltage")
            )
        elif defect == "rate":
            extra = replace(extra, sample_rate=100)
        else:
            extra = replace(extra, time_unit="ms")
        with pytest.raises(ProjectError):
            normalize(frame, r["columns"], base, extra)


def test_time_unit_and_source_integer_origin_precision(tmp_path):
    source = example(count=1).with_columns(
        (pl.col("t") * 1e9).cast(pl.Int64).alias("t")
    )
    source = source.with_columns((pl.col("t") + 1_700_000_000_000_000_000).alias("t"))
    store, r, base, extra = fixture(tmp_path, frame=source, time_unit="ns")
    with closing(store):
        rec = normalize(pl.read_parquet(r["path"]), r["columns"], base, extra)[0]
        assert rec["time_origin"] == "1700000000000000000" and rec["t"][
            -1
        ] == pytest.approx(511 / 128)


def test_alias_preflight_cutoff_and_band_loss_are_explicit(tmp_path):
    store, r, base, extra = fixture(tmp_path, frame=example(count=1))
    with closing(store):
        for spec in [
            replace(extra, bandlimit_hz=80),
            replace(extra, filter_type="lowpass", cutoff=[64]),
            replace(extra, filter_type="bandpass", cutoff=[25, 10]),
            replace(extra, target_rate=64, bandlimit_hz=40),
        ]:
            with pytest.raises(ProjectError):
                spec.validate(base, r["columns"])
        s = replace(extra, target_rate=64, bandlimit_hz=40, allow_band_loss=True)
        s.validate(base, r["columns"])
        y, fs, meta = process(
            np.sin(2 * np.pi * 8 * np.arange(512) / 128), s, Control()
        )
        assert fs == 64 and len(y) == 256 and meta["resample"]["offline_only"]
        assert spectrum(y[32:-32], 64, "boxcar")["amplitude"][24] == pytest.approx(
            1, rel=0.02
        )


@pytest.mark.parametrize(
    "option",
    [
        dict(zero_phase=True, filter_type="lowpass"),
        dict(target_rate=64),
        dict(detrend="constant"),
        dict(detrend="linear"),
    ],
)
def test_online_future_using_transforms_rejected(tmp_path, option):
    store, r, base, extra = fixture(tmp_path)
    with closing(store), pytest.raises(ProjectError, match="offline-only"):
        replace(extra, mode="online", **option).validate(base, r["columns"])


def test_causal_filter_future_poison_and_frequency_dependent_phase():
    y = np.sin(2 * np.pi * 8 * np.arange(1024) / 128)
    s = SignalSpec(filter_type="lowpass", cutoff=[20], mode="online")
    a, fs, meta = process(y, s, Control())
    changed = y.copy()
    changed[512:] += 1000
    b, _, _ = process(changed, s, Control())
    assert np.array_equal(a[:512], b[:512])
    f = meta["filter"]
    i = np.argmin(abs(np.array(f["frequency_hz"]) - 20))
    assert f["gain"][i] == pytest.approx(1 / math.sqrt(2), rel=0.01)
    assert np.ptp(f["group_delay_seconds"]) > 0 and f["effective_order"] == 4
    offline = replace(s, mode="offline", zero_phase=True)
    c, _, m = process(y, offline, Control())
    d, _, _ = process(changed, offline, Control())
    assert (
        not np.allclose(c[500:512], d[500:512]) and m["filter"]["effective_order"] == 8
    )
    assert m["filter"]["gain"][i] == pytest.approx(0.5, rel=0.02)


def test_overlap_split_rejects_shared_person_even_with_distinct_device_session(
    tmp_path,
):
    frame = example().with_columns(
        pl.when(pl.col("recording") == "r2")
        .then(pl.lit("p0"))
        .otherwise(pl.col("subject"))
        .alias("subject")
    )
    store, r, base, spec = fixture(tmp_path, task="classification", frame=frame)
    with closing(store), pytest.raises(ProjectError, match="sızıntısı"):
        split(normalize(pl.read_parquet(r["path"]), r["columns"], base, spec), spec)


def test_window_split_train_fit_isolation_and_validation_poison(tmp_path):
    store, r, base, spec = fixture(tmp_path, task="classification")
    with closing(store):
        a = calculate(r, base.data(), tmp_path)
        wa = a["advanced"]["windows"]
        ta = [w for w in wa if w["partition"] == "train"]
        va = [w for w in wa if w["partition"] == "validation"]
        assert set(ta[0]["source_row_ids"]) & set(ta[1]["source_row_ids"])
        assert not {i for w in ta for i in w["source_row_ids"]} & {
            i for w in va for i in w["source_row_ids"]
        }
        frame = pl.read_parquet(r["path"]).with_columns(
            pl.when(pl.col("recording").is_in(["r2", "r3"]))
            .then(pl.col("voltage") + 1000)
            .otherwise(pl.col("voltage"))
            .alias("voltage")
        )
        path = tmp_path / "poison.parquet"
        frame.write_parquet(path)
        b = calculate(
            dict(r, path=str(path), fingerprint=file_hash(path)), base.data(), tmp_path
        )
        assert (
            a["advanced"]["classifier"]["numeric_model"]
            == b["advanced"]["classifier"]["numeric_model"]
        )
        assert (
            a["advanced"]["classifier"]["fit_row_ids"]
            == b["advanced"]["classifier"]["fit_row_ids"]
        )


def test_cost_preflight_cancel_timeout_and_source_tamper(tmp_path):
    store, r, base, spec = fixture(tmp_path)
    with closing(store):
        ev = Event()
        ev.set()
        with pytest.raises(Canceled):
            calculate(r, base.data(), tmp_path, Control(ev))
        c = Control(budget=ComputeBudget(max_wall_seconds=0.001))
        sleep(0.01)
        with pytest.raises(ProjectError):
            calculate(r, base.data(), tmp_path, c)
        rec = normalize(pl.read_parquet(r["path"]), r["columns"], base, spec)
        with pytest.raises(ProjectError):
            preflight(rec, replace(spec, segment_length=2048, overlap=2040), Control())
        out = calculate(r, base.data(), tmp_path)
        out["advanced"]["recordings"][0]["channels"][0]["fft"]["amplitude"][0] += 3
        with pytest.raises(ProjectError):
            validate_source(out, pl.read_parquet(r["path"]), r["columns"])
        out = calculate(r, base.data(), tmp_path)
        out["advanced"]["windows"][0]["source_row_ids"][0] = "row:fake"
        with pytest.raises(ProjectError):
            validate_source(out, pl.read_parquet(r["path"]), r["columns"])
