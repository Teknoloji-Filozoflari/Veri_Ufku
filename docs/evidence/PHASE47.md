# Faz47 — gelişmiş kümeleme ve anomali

<a id="e47"></a>

2026-10-12; DEC47-01; ENV-47 kilitli CPython3.13.15 `.venv`, sklearn1.9.1,
Linux offscreen/software. [Ortam](phase47/environment.json),
[ADR048](../adr/048-exploration-phase47.md), [16 C/V/G/H/P](phase47/acceptance.json).
Teknik teslim doğrulandı; resmî faz sürüyor/deneysel/zorunlu. Optional native
sklearn HDBSCAN ortamda kurulu ve test edildi; contrib HDBSCAN kullanılmadı.

Agglomerative/full linkage +last30 collapsed dendrogram; GMM soft membership
ve AIC/BIC; OPTICS/HDBSCAN yoğunluk/noise. DBSCAN/KMeans aynı comparison yolu.
Metric/linkage/scaling, ColumnId/RowId/snapshot/seed kayıtlı. Silhouette/DB/CH
noise dışı; tek/all-noise tanımsız. Manhattan centroid DB/CH kapalı. Stabilite
%80 without replacement, sample-içi scaler fit; seçili RowId ve ARI/noise
agreement. True k/accuracy iddiası yok; mixed category codes reddedilir.

LOF outlier ile heldout novelty ayrı; novelty train rows score/candidate null,
train-only scaler. OneClassSVM ve robust covariance threshold/scope/geometry
kayıtlı, higher score=more unusual; yöntemler arası score ölçeği eşit değil.
0/1 etiket varsa sabit eşikte PR/AP ve FP/FN maliyeti, in-sample/heldout etiketi;
etiket yoksa precision/recall yok. Yeni modellerde safe new-file model reuse
kapalı; sonuç/üyelik JSON/Parquet kaydı destekli. Önceki KMeans/IF/IQR lifecycle
korundu. Parent source+members+scaler+fit+metrics+stability+PR yeniden hesaplar;
ProjectStore atomik yayın; source/hash/SourceRecordId korunur, auto delete yok.

## Gerçek kontroller

- [Kaynak JUnit](phase47/source-final.xml):123passed; [wheel](phase47/wheel-final.xml):61passed. Yeni Faz47 18 backend+14GUI=32 test; legacy/related ayrı. Native her model/novelty, reference metrics/LOF, GMM11parameter AIC/BIC penalty, hand PR/cost, noise/single, budget/cancel/timeout, tamper/atomic/source/identity/reopen.
- [Kaynak](phase47/source/walkthrough.json) ve [wheel](phase47/wheel/walkthrough.json):12şer gerçek QML registry→parametre→preflight→fit→help/Escape→save/reopen;96PNG ve24 safe evidence artifact copy her biri. Bunlar kullanıcı GUI export iddiası değildir.
- [Wheel](phase47/wheel.json):274package byte source/wheel/install eşit; [frozen435code/test/script/lock hash](phase47/frozen-head.json). [Fresh4XDG installed smoke](phase47/smoke.json):GUI_SMOKE PASS.
- `.venv/bin/ruff check src tests scripts`,format--check,check_docs/check_artifacts/check_learning/check_usability;14document unittest geçti. Katalog63/313article,155UIbinding,652namedfield,189coreEnglish.
- Son görsel denetimde Agglomerative/GMM cluster sayısının GUI tarifine aktarımı düzeltildi; seçilen2 değeri final GUI testinde resultspec ile doğrulandı. Qt image enum test erişimi ve cluster örneklerinde undefined score gösterimi düzeltildi. Yukarıdaki kanıt son paket başlığındadır.

## Sınırlar

Advanced/comparison/stability3000rows/20features;KMeans single fit legacy100000.
n²*24 worst RAM precheck,shared CPU/wall/disk/disposable cancel; no implicit
sample. Dendrogram preview collapsed; tam numeric linkage/result kaydı korunur.
Sparse/mixed/weights ve yeni model dosyası persistence kapalı. Physical desktop,
insan/Orca/AT,minhardware,cleanofflineinstall,remoteCI bu fazda koşulmadı.
Önceki F13/F24/F25/F27/F28/F30bigSAS/F31offlinecache ve optionalUMAP açıkları
kapanmadı. Kaynak pytest Qt shutdown157uncollectableobjects ResourceWarning
önceki lifetime sınırlamasıdır; çözülmüş sayılmaz. Tam depo regresyonu koşulmadı.
Stage/commit/push yapılmadı; mevcut kullanıcı değişiklikleri korunur. Faz48 yok.
