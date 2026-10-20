# Faz48 — model aileleri

<a id="e48"></a>
2026-10-13 Europe/Istanbul (matris doğrulama tarihi UTC:2026-10-12); DEC48-01; ENV-48 kilitli CPython3.13.15 `.venv`, sklearn1.9.1,
skops0.16.0; Linux CPU/offscreen/software. [Ortam](phase48/environment.json),
[ADR049](../adr/049-model-families-phase48.md), [20 alt iş](phase48/acceptance.json).
Yerel kapsam teknik doğrulandı: 26 purpose/model kombinasyonu. 16 kayıt sınırlı
teknik doğrulandı; üç optional backend ve ranking runtime doğrulanmadı.
Resmî faz sürüyor / deneysel / zorunlu; önceki kabul kapıları kapanmadı.

Regresyon ElasticNet/Lasso, sınıflandırma ElasticNet/L1 logistic; SGD squared/log
loss; decision tree/ExtraTrees/gradient/hist-gradient; SVC/SVR/KNN;
Gaussian/MultinomialNB; bagging10tree, voting2 ve stacking2 + Ridge/logistic meta.
Model → “Faz48 model ailelerini göster”; tek registry’den explicit model seçimi,
parametre/preflight, gerçek worker eğitimi ve baseline ile aynı validation planı.
Eski modeller korunur. Aile CV skoruyla otomatik değiştirilmez. Final test ayrı
eylem; seçili model, sınıf/eşik kararı ve split dondurulur.

Her learner ve ensemble child raw eğitim Frame’inde imputasyon/vocab/scaling
öğrenir. Stacking iç independent/GroupKFold OOF; meta yalnız OOF tahminlerden
öğrenir, preprocessing iç katlarda da fit edilir. Time/group_time stacking kapalı;
random fallback yok. CSR explicit/non-centering, implicit dense dönüşüm yok.
Histogram categorical eğitim vocab ve native NaN korunur; unknown → missing.
GaussianNB dense; MultinomialNB non-negative. SVC probability/calibration kapalı;
ROC/PR değerleri tanımsız gösterilir. KNN/ensembles weights kapalı; diğerlerinde
sample_weight yalnız training loss; preprocessing ve rapor metrikleri unweighted.
Baseline aynı training weights. Frequency/analytic/survey weights reddedilir.

5000rows/256 transformed features; SVM/KNN2000 + n² RAM üst maliyeti;
ensembles1000 + inner/native fit upper cost. Bütçe, süreç iptali/wall timeout ve
convergence/numerical warning kapıları korunur. Fold başarısızlığında başarı veya
model artifact yayımlanmaz. Kaynak/snapshot/ColumnId/RowId/SourceRecordId korunur.
Closed skops model paketi, kaynak/fit/feature/class order/native parameter/ensemble
membership/OOF kapsamı denetlenir; arbitrary function trust, pickle/joblib yok.
Yeni veride preview/transform/predict sıfır fit; ayrı prediction Parquet içinde
kaynak kolonları ve RowId korunur. Worker Qt nesnesi veya ACTIVE yazmaz.

## Gerçek kontroller

- [Kontrol özeti](phase48/verification.json): kaynakta 285 benzersiz ilgili pytest vakası. [Çekirdek](phase48/source-core.xml):201; [destek](phase48/source-support.xml):106; [integration](phase48/source-integration.xml):50; [son UI/destek](phase48/source-ui-final.xml):111. Bu gruplar örtüşür; sayıları toplanmaz. CSR, missing/train-only, elle weighted baseline, OOF refit/reference, negative/missing/zero weights, unknown/ordinal/native NaN, multioutput/GPU/save gates, convergence, n² admission, actual cancel/wall expiry, prior model/source preservation.
- [Kurulu wheel testleri](phase48/wheel-tests.xml):235 passed; kilitli aynı runtime, /tmp noneditable package. [Paket](phase48/wheel.json):278 dosya source/wheel/install byte eşit; [443 code/test/script/lock hash](phase48/frozen-head.json) kontrol edildi. [Fresh4XDG smoke](phase48/smoke.json):GUI_SMOKE PASS.
- [Kaynak GUI](phase48/source-gui/walkthrough.json) ve [wheel GUI](phase48/wheel-gui/walkthrough.json):26şar gerçek QML train/evaluate/save/model-open/new-data-preview/predict/reopen/help-Escape yolu; 208 PNG ve78 safe evidence copies her ortamda. Bunlar kullanıcı GUI export iddiası değildir.
- İlk GUI turunda SVM’nin unsupported ROC/PR None değeri Qt QVariant’da undefined oldu; iki eski QML label düzeltildi. [Son kaynak SVM](phase48/source-svm-final/walkthrough.json) ve [son wheel SVM](phase48/wheel-svm-final/walkthrough.json):gerçek “tanımsız” label assertion,8şer PNG/3artifact; TypeError yok. İlk walkthrough’ların önceki geçerli native hesapları korunur; bu iki affected-case replay ve son legacy GUI kontrolleri gösterim düzeltmesini doğrular.
- [Son kapılar](phase48/gates.json): Ruff check/format; docs/artifacts/learning/usability ve14 belge unittest geçti. İçerik64/336 article,157UIbinding,670namedfield,189coreEnglish. Tam depo regresyonu bu fazda koşulmadı. Qt teardown ResourceWarning200uncollectableobjects önceki yaşam döngüsü sınırı olarak açık; test başarısızlığı olarak gizlenmedi.

## Kapsam ve açık kabul

Optional XGBoost/LightGBM/CatBoost CPU/native-category adapters lazy; bu ortamda
paketler yok. Availability/disabled UI/rejection guard testleri geçti; gerçek
train/evaluate/predict başarısı değildir. Safe optional model save/new-file model
reuse kapalı. RankingSpec/v1 query/relevance/features ayrı; whole-query split
şeması ve ordinary-class objective rejection testli; optional ranker factory var,
ranking execution/evaluation GUI doğrulanmadı. Multioutput/GPU uygulama yolu kapalı;
26 adapterde multioutput rejection test edildi, multioutput eğitim iddiası yok.
F48-S001/S002 ve optional/ranking tam runtime kayıtları bu nedenle doğrulanmadı.

Physical desktop/human/Orca/AT/minHW/clean offline install/remoteCI bu fazda
koşulmadı. Önceki F13/F24/F25/F27/F28, büyük SAS, connector clean-cache,
F43 aggregate RAM ve optional UMAP açıkları korunur. Temel uygulama offline;
ağ veya optional dependency indirme yapılmadı. Kaynak değişiklikleri/untracked
korundu; stage/commit/push yok. Faz49 yetkisi yok.
