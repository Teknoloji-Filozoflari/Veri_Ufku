"""Defined Hann one-sided PSD, HTK triangular mel power and orthonormal DCT MFCC."""

from fractions import Fraction

import numpy as np
from scipy import signal
from scipy.fft import dct, rfft, rfftfreq

from veri_ufku.storage.project_model import ProjectError


def resample(y, rate, target):
    if not target or target == rate:
        return (
            y.copy(),
            rate,
            dict(up=1, down=1, method="identity", source_rate=rate, target_rate=rate),
        )
    ratio = Fraction(target, rate)
    if max(ratio.numerator, ratio.denominator) > 1000:
        raise ProjectError("Resample ratio up/down≤1000 gerekir.")
    out = signal.resample_poly(
        y, ratio.numerator, ratio.denominator, window=("kaiser", 5.0)
    )
    return (
        out,
        target,
        dict(
            up=ratio.numerator,
            down=ratio.denominator,
            method="scipy resample_poly Kaiser5 FIR anti-alias; offline",
            source_rate=rate,
            target_rate=target,
            amplitude="no peak normalization",
            removed_above_hz=min(rate, target) / 2,
        ),
    )


def features(y, rate, spec):
    if len(y) < spec.n_fft or len(y) > 2_000_000:
        raise ProjectError("Segment FFT window'dan kısa veya2Mframe sınırında.")
    high = spec.f_max or rate / 2
    if not 0 <= spec.f_min < high <= rate / 2:
        raise ProjectError("Mel band Nyquist sınırı dışında; sessiz kırpma yok.")
    frames = np.lib.stride_tricks.sliding_window_view(y, spec.n_fft)[:: spec.hop]
    if len(frames) > 8192:
        raise ProjectError(
            "8192spectrum frame bütçesi; hop artırın veya açık segment seçin."
        )
    w = signal.windows.hann(spec.n_fft, sym=False)
    z = rfft(frames * w, axis=1)
    power = np.abs(z) ** 2 / (rate * np.sum(w * w))
    power[:, 1:-1] *= 2
    freq = rfftfreq(spec.n_fft, 1 / rate)

    def hz(m):
        return 700 * (10 ** (m / 2595) - 1)

    def mel(f):
        return 2595 * np.log10(1 + f / 700)

    edges = hz(np.linspace(mel(spec.f_min), mel(high), spec.n_mels + 2))
    bank = np.array(
        [
            np.maximum(
                0,
                np.minimum(
                    (freq - edges[i]) / (edges[i + 1] - edges[i]),
                    (edges[i + 2] - freq) / (edges[i + 2] - edges[i + 1]),
                ),
            )
            for i in range(spec.n_mels)
        ]
    )
    if (bank.sum(1) == 0).any():
        raise ProjectError(
            "Mel filtresi FFT grid'de boş; FFT artırın veya mel sayısını azaltın."
        )
    logmel = np.log(np.maximum(power @ bank.T * (rate / spec.n_fft), 1e-12))
    mfcc = dct(logmel, type=2, norm="ortho", axis=1)[:, : spec.n_mfcc]
    summary = np.concatenate([mfcc.mean(0), mfcc.std(0), logmel.mean(0), logmel.std(0)])
    bins = np.array_split(np.arange(len(y)), min(256, len(y)))
    waveform = [
        dict(
            start_frame=int(i[0]),
            end_frame=int(i[-1] + 1),
            min=float(y[i].min()),
            max=float(y[i].max()),
        )
        for i in bins
    ]
    rms = np.sqrt((frames * frames).mean(1))
    quality = dict(
        clipped_sample_fraction=float(np.mean(np.abs(y) >= spec.clip_level)),
        outside_fullscale_fraction=float(np.mean(np.abs(y) > 1)),
        silence_window_fraction=float(np.mean(rms <= 10 ** (spec.silence_dbfs / 20))),
        rms=float(np.sqrt(np.mean(y * y))),
        peak=float(np.max(np.abs(y))),
        clip_level=spec.clip_level,
        silence_dbfs=spec.silence_dbfs,
        reference="digital full-scale1; not physical SPL; no silent repair/trim",
    )
    view = power[:: max(1, int(np.ceil(len(power) / 128)))]
    return summary, dict(
        sample_rate=rate,
        frames=len(y),
        duration_seconds=len(y) / rate,
        quality=quality,
        waveform=waveform,
        frequency_hz=freq.tolist(),
        spectrogram_db=(10 * np.log10(np.maximum(view, 1e-12))).tolist(),
        spectrogram_frame_stride=max(1, int(np.ceil(len(power) / 128))),
        mfcc_mean=mfcc.mean(0).tolist(),
        logmel_mean=logmel.mean(0).tolist(),
        frame_n=len(frames),
        excluded_tail_samples=len(y) - ((len(frames) - 1) * spec.hop + spec.n_fft),
        definition="Hann periodic; one-sided PSD power/Hz, integration df; HTK triangular unnormalized mel, natural log floor1e-12; DCT-II ortho including C0; summary means/std per segment; preview reduced time frames only",
    )
