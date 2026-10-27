# Faz50 — kalibrasyon ve predictive belirsizlik

<a id="e50"></a>
DEC50-01 açık kullanıcı talimatı; 2026-10-13 UTC / Europe/Istanbul;
ENV-50 kilitli CPython3.13.15, scikit-learn1.9.1, CPU/offscreen/software.
[Ortam](phase50/environment.json), [ADR051](../adr/051-uncertainty-phase50.md),
[10 C/V/G/H/P](phase50/acceptance.json), [gerçek kontrol kaydı](phase50/verification.json).
Native bounded kapsam teknik doğrulandı; resmî sürüyor/deneysel/zorunlu.

Model → Faz50 paneli: label-stable uniform-bin reliability diagram; sınıf,
evaluation scope, n, bin n ve boş-bin policy görünür; before/after log-loss/Brier.
Brier binary half-sum [0,1], multiclass full sum [0,2]; kalibrasyonu tek başına
ölçmez. Sigmoid/isotonic, küçük isotonic n uyarısı, unseen sınıf reddi; bilinen ama
final bölümde bulunmayan sınıf ayrı. Binary positive class açık, multiclass argmax.
Validation maliyet/precision/recall constraints, unique bounded threshold grid;
infeasible durur, no-positive precision tanımsız. Final cost/precision/recall
raporu dondurulmuş eşiği değiştirmez.

Outer validation/final holdout planı korunur. Outer train içinde shared splitter
proper train / probability calibration / conformal calibration ayırır; same
seed/group/time/equal timestamps/connected intervals/horizon-purge. Random
fallback yok. Sklearn FrozenEstimator ve explicit identity prediction split:
base fit no-op; default random calibration CV yok. Calibration ve quantile-only
modlarda kullanılmayan rezerv bölüm fit'e eklenmez; allocated/used n ayrı.
Hazırlık yalnız proper train; CV planı metadata'da olsa da bu bounded adapter
CV fit/score hesapladığını iddia etmez. Yeni seçimler/arama eski final test
kullanım defterini silemez; final reserve yayınlanmadan sonuç açılmaz.

Regresyon Ridge/forest residual split conformal; gradient50depth3 quantile ve
conservative nonnegative CQR; classification score1-p(true class) prediction
sets. Rank ceil((n+1)(1-alpha)), sonlu rank yetersizse durur. Quantile crossing
pointwise min/max rearrangement ve sayısı açık. Empirical coverage/mean width/
mean set size/empty/full sets tüm evaluation records'ta; ilk20 okunur önizleme,
RowId isteğe bağlı görünüm. Prediction:none için nominal/empirical coverage veya
interval/set üretilmez. Exchangeability gereklidir, doğrulanmış varsayılmaz;
stratified/grup/zaman ayrımı bunu kanıtlamaz. Nominal alt grup/gelecek garantisi
veya parametre CI iddiası yok; predictive interval yeni gözlemi hedefler.

Calibrator numeric maps, threshold ve q closed typed safe skops paketinde;
ModelCard/v1 yalnız reviewed wrapper'larda uncertainty extension. Eski kartlar
korunur, user-code/pickle import yok. Final test yayınlanmış paketi source/plan/
config/decision eşleşmesiyle sıfır fit ile kullanır. Writer executable deserialize
yapmaz; safe card JSON, immutable source hash, actual target/RowId/shared joint
memberships, metric/coverage ve frozen final state doğrular. Büyük1000 kayıt
raporu mevcut JSON artifact/atomik ProjectStore summary protokolünde reopened.
Model/source/ColumnId/RowId/DatasetVersion/snapshot/lineage korunur; kullanıcı
verisi sessizce düzeltilmez. Native CPU1000rows/32features; logistic/forest
probability, Ridge/forest residual interval, gradient quantile/CQR. Family/sparse/
weights/TF-IDF burada kapalı; F49 search-internal calibration hâlâ kapalı.

[Source core](phase50/source-core.xml):295 pass; [installed core](phase50/wheel-core.xml):295 pass.
[Source GUI/regression](phase50/source-ui.xml):23 pass; [forest GUI](phase50/source-forest-ui.xml):2 pass.
Yeni23 core ve10 GUI. [Source walkthrough](phase50/source-gui/walkthrough.json),
[wheel walkthrough](phase50/wheel-gui/walkthrough.json):10'ar gerçek workflow,
18'er stage capture,108'er PNG ve36'şar safeJSON/model artifact kopyası.
Six template +binary cost/constraint/cancel/newfile +joint group-time +forest
probability/interval. Her native template package export/import/predict,
zero-fit final journal ve reopen; F1/Escape; cancel eski sonuca zarar vermedi.
Sklearn frozen calibration exact reference, reversed label order/logloss/Brier/bin,
hand cost/rank, fit spy, heldout target/feature poison, group/time/horizon,
unseen/absent/infeasible/unsupported/point-only, actual coverage, tamper/frozen q,
source-bound publication ve1000row archive/reopen doğrulandı.

[Wheel](phase50/wheel.json):287 package file byteequal source/wheel/install;
[aktif source freeze](phase50/frozen-head.json):28 hedef dosya; runtime/lock değişmedi.
[Fresh4XDG installed smoke](phase50/smoke.json):GUI_SMOKE PASS.
Docs/artifacts/learning/usability/Ruff check+format ve14documentunit pass.
İçerik66/352 makale;161 bindings/698 named fields/189 coreEnglish; yeni dört kavram,
mevcut model-uncertainty makalesi genişletildi. Kontrol çerçevesi
[DEVELOPMENT](../DEVELOPMENT.md) içinde. Stage/commit/push yapılmadı.

Physical desktop, human/AT, minimumHW, cleanofflineinstall ve remoteCI çalışmadı;
full-repo aggregate koşulmadı. Önceki F13/F24/F25/F27/F28/F30SAS/F31cache/F43RAM,
optionalUMAP/XGB/LGB/CatBoost/Optuna ve QtResourceWarning kapıları korunur.
Bu kayıt önceki kontrolleri yeniden çalıştırılmış saymaz; formal kabul ayrıca açık.
