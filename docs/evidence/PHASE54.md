# Faz54 — düzenli sinyal, spektrum ve blok ayrımlı pencereler

<a id="e54"></a>
DEC54-01 açık kullanıcı talimatı; yalnız Faz54. ENV-54 locked CPython3.13.15,
CPU Qt offscreen/software. 13 bounded native teknik kayıt doğrulandı; resmî faz sürüyor/deneysel/zorunlu.
[Ortam](phase54/environment.json),[sözleşme/backend kaynakları](../adr/055-signals-phase54.md).
Mevcut TimeSeriesRun/worker/controller/ProjectStore/safe JSON, tek Capability,
ComputeBudget/Provenance/Faz52 registry kullanılır; ikinci kayıt deposu yok.
Düzensiz FFT kapalı; offline zero-phase/polyphase ve identity-before-window split.
Faz55 yetkisi yok. Önceki resmî fiziksel/insan/AT/hardware/installer/remoteCI kapıları açık.

[408 source core](phase54/source-core.xml), [408 noneditable wheel core](phase54/wheel-core.xml),
[42 source GUI/regression](phase54/source-ui.xml). 35 yeni core ve13 yeni GUI case.
[13 gerçek kaynak GUI](phase54/source-gui/walkthrough.json),
[13 gerçek kurulu GUI](phase54/wheel-gui/walkthrough.json):52PNG/52safeJSON run/masked registry.
[13 C/V/G/H/P kabul](phase54/acceptance.json), [komutlar/sınırlar](phase54/verification.json),
[303 byte-eşit package](phase54/wheel.json), [frozen-head](phase54/frozen-head.json),
[fresh4XDG kurulu smoke](phase54/smoke.json),[kapılar](phase54/gates.json).

Sinüs bin-centered8Hz peak2 (boxcar/Hann/Hamming/Blackman), PSD integral2; DC/even
Nyquist non-double/odd bin double; STFTmean PSD=Welchmean reference. Explicit source
band/cutoff Nyquist and target band-loss guards; numeric ns timestamp integer-origin
precision. Irregular/duplicate/reversed/nonfinite/missing/fs/unit mismatch rejection.
Causal output future-poison invariant; zero-phase future dependence/order/gain explicit.
Source/channel/time/event RowIds, conservative resample dependency, actual normalizers/
padding/phase response stored. Whole recording block split before windows, every
selected identity column disjoint. Overlap allowed only within partition; validation
poison leaves train scaler/model unchanged. Train-only numeric classifier safe validation
and class mapping; no optimization refit/executable import on reopen. Full source spectra/
feature windows/capture hash guarded; malformed/tampered sources rejected.

GUI actual registry activation/options→worker→spectrogram/FFT/Welch/filter/peaks/events/
feature/classification→source unchanged→offline help→safe save/reopen. Spectrogram
cancel launches real spawned worker and leaves prior published result/source intact;
not a successful new run. Images visually inspected: 8Hz line/axis units/power legend,
2unit FFT peak and readable PSD. Whole recordings never straddle train/validation;
window n explicitly not independent people n. Source protected; no new dataset writes.

Bounds32768rows/16recordings/8channels/8192samples perrecord/131072STFTcells/2000windows.
Source acquisition bandwidth is declared, cannot prove absent aliasing. Standard FFT
for irregular data and Lomb-Scargle unsupported. Offline-only zero-phase/polyphase/
whole-record detrend; online mode causal validation, not live streaming serving.
Fixed StandardScaler+LogisticRegression template; no tuning/final test/new-file fitted
prediction. Complete feature windows only; unpadded tail retained/source recorded.
Generic Phase52 run view/capture preserved; native signal model comparison not inferred.
Physical desktop/human/AT/minHW/cleanoffline installer/remoteCI/full repository aggregate
not run. Previous formal/optional gaps preserved. No stage/commit/push; Faz55 not started.
