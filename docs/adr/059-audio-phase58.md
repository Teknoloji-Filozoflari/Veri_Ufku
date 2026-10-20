# ADR-059 — yerel ses, sabit feature ve bounded CPU classification

2026-10-14 DEC58-01; açık kullanıcı talimatı. Yalnız Faz58.

SoundFile0.13.1/libsndfile WAV/FLAC okuyucu core lock'a eklendi. PCM16/24/32 ve WAV FLOAT,
1–2kanal,8–96kHz,60s/2Mframe/16MiBfile;64recording/256segment,512MiB source bundle.
Reader format/subtype/frame/duration/nonfinite önkontrolü; kaynak sessiz trim/peak-normalize/
clip/downmix edilmez. Channel index açık. Dosya/segment/source-recording/speaker/session,
kaynak frame aralığı ve source RowId/SourceRecordId/DatasetVersion korunur. Orijinal dosya
her durumda immutable source kopyası; ZIP ve single WAV/FLAC gerçek offline yoldur.

Tek SourceAdapter/Capability/ComputeBudget/Provenance/ProjectStore genişletilir. Metadata
native Parquet; ImageAdapter mevcut native writer'ı record locator parametrizasyonuyla
paylaşılır. AudioRun/v1 mevcut neural safe artifact/journal/experiment projection içinde;
yeni registry yok. Worker Qt/ACTIVE almaz; parent ACK/atomic checkpoint. Safe classifier
JSON means/scales/coefficients/label order; pickle/arbitrary object yok. Model yeni snapshot
prediction yapar; fit edilmez. Vision/Neural kayıt şemaları ayrıdır ve korunur.

Kaynak aynı recording/source_recording, declared speaker/session veya exact decoded PCM
hash ile union component. Overlap segmentler aynı kayıt bileşeninde kalır. Bilinmeyen
speaker kimliğini audio'dan çıkarma veya bağımsız konuşmacı genelleme garantisi yok.
Classification ortak ValidationSpec group holdout train/validation/test; final test metric
kapalı. Same dataset classification refit frozen split'i değiştirirse reddi; Faz16 önceki
test-use history korunur. Deterministik sabit spectral feature fit içermez. StandardScaler/
LogisticRegression yalnız train; gain augmentation train'de original+gain dB, örnek rate/
zaman kimliği değişmez. >full-scale augmentation reddi; validation/test augmentation yok.
Same holdout Dummy baseline, confusion label order/n kayıtlı; genel acoustic/SOTA kalite yok.

SciPy1.18 resample_poly Kaiser5 FIR anti-alias, gerçek up/down≤1000; rate metadata yeniden
etiketlenmez. 2Moutputframe/segment,4M toplam seçili işlem frame preflight;8192spectrum
window/segment. Hann periodic, FFT128/256/512/1024,hop açık; one-sided PSD power/Hz,
non-DC/non-Nyquist bin doubling; HTK triangular unnormalized mel integration df, natural
log floor1e-12; DCT-II orthonormal includingC0. Summary per-segment means/std. FFT grid'de
boş mel veya Nyquist dışı band reddi. Tail sample count kayıtlı; waveform min/max256bin;
spectrogram preview≤128timeframe, frequency bins korunur; görsel[-120,0]dB clamp analytic
sonucu değiştirmez. Clipping/silence original selected segment VE processed output ayrı;
digital full-scale1, fiziksel SPL veya speech-VAD iddiası yok. Bu yol offline kayıttır.

Optional `audio-speech` extra Vosk0.3.45 installed; model ağırlığı indirilmedi. Yerel
LocalVosk/v1 audio-model.json language/license/training_dataset/filesSHA manifest;
explicitconsent,512MiB modelcap,symlink/filehash guards. Backend `Model(model_path=...)`,
lang/name auto downloader kullanılmaz. STT bu ortamda gerçek küçük model olmadığından
runtime notvalidated/unavailable; package varlığı recognition testi değildir. UI explicit
hata ve no-network/local path. Timestamp/confidence sadece backend word alanları; kaynak
segment origin saniye offset, bounded word start/end kontrolü; aggregate confidence yok.
WER/CER exact case/Unicode/punctuation/whitespace tarifli edit distance, gerçek human
referans tam seçili segmentle eşleşince; whole recording reference alt segmentte tekrar
kullanılmaz. Referans yoksa skor yok. Output-contract fixture gerçek recognition değildir.
Diarization/event detection ve mikrofon canlı kayıt ayrı kapalı kapsamlar; transcription
var diye destekli gösterilmez. Vosk native log kapalı; ses/text app log'a yazılmaz.

Resmî belgeler geliştirme sırasında okundu: [SoundFile](https://python-soundfile.readthedocs.io/en/latest/),
[SciPy resample_poly](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample_poly.html),
[DCT](https://docs.scipy.org/doc/scipy/reference/generated/scipy.fft.dct.html),
[Vosk local constructor](https://github.com/alphacep/vosk-api/blob/master/python/vosk/__init__.py).
Teknik/offscreen geliştirici kanıtı [Faz58](../evidence/PHASE58.md); human/AT/physical/minHW/
offlineinstaller/remoteCI/tam-repo aggregate ve önceki kabuller ayrı kalır.
