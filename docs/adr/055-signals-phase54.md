# ADR055 — regular signal ve recording identity sınırı

DEC54-01. Existing TimeSeriesSpec/v1 advanced family=signal, SignalSpec/v1;
TimeSeriesRun/v1 advanced SignalRun/v1. Existing worker Qt-free/no ACTIVE; parent
atomic publication. Safe finite JSON, snapshot/hash/RowIds retained; no pickle or
new-file fitted model serving. Numeric elapsed source time s/ms/us/ns, fs explicit;
reject irregular/duplicate/unordered sampling, no implicit interpolation/sort.
Closed native FFT regular-only; Lomb-Scargle not implemented, not an FFT substitute.
32768 rows/16recordings/8channels/8192samples perrecord;131072STFTcells/2000windows.

Periodic DFT window coherent gain; one-sided peak amplitude and density differ;
DC/evenNyquist not doubled. Welch explicit density/spectrum; STFT PSD positive
interior bins doubled, no padded/boundary windows, center time descriptive and
available_at window endpoint. Peak prominence/distance and first128 display limits
stored. Analog bandwidth acquisition declaration cannot prove absent aliasing;
Nyquist gate for declared bandwidth/cutoff; resample FIR loses high-frequency band,
requires explicit loss acknowledgement when declared source band exceeds target.

Butterworth SOS order/cutoff/response/gain and frequency-dependent group delay;
causal zero/rest state retains transient, no time shift. Forward/backward odd
padding zero-phase doubles effective order and squares gain; offline-only. Polyphase
centered FIR and whole-record detrend also offline-only. Online mode is causal
transformation validation, not live streaming deployment. Event contiguous labels
retain original indices/time/RowIds; resample sample identities are derived with
conservative full recording dependency, never masquerade as original source rows.

Classification splits recordings before any filtering/window extraction. Every selected
person/device/session identity column must be disjoint independently, not just tuple
combinations. Recording overlap windows stay one partition; no random window split.
Train-only scaling/fixed LogisticRegression, class mapping/n independent recording
count; validation not final test. Whole record offline transformations cannot read the
other partition. Feature/window lineage remains source-bound; no sample independence
claim or automatic optimum. Full artifact validates actual source spectra/feature
windows and numeric classifier scaling/predictions without optimization refit/import.

Reviewed 2026-10-14 official SciPy1.18 runtime docs:
[Welch](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html),
[polyphase](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample_poly.html),
[STFT](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.stft.html),
[Butterworth](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.butter.html),
[SOS causal](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.sosfilt.html),
[SOS forward/backward](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.sosfiltfilt.html),
[window](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.get_window.html),
[peaks](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html).
