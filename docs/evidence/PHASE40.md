# Faz40 — istatistiksel modeller ve tanılama

2026-10-11; ENV-40: kilitli CPython3.13.15, statsmodels0.15.0,
PySide6/Qt6.11.2, NumPy2.5.3, SciPy1.18.0, Polars2.0.0; Linux offscreen/software.

<a id="e40"></a>
## E40 — teknik teslim

40.1 OLS/WLS,40.2 binomial/Poisson/NB2 GLM,40.3 quantile,
40.4 Gaussian mixed,40.5 balanced repeated-measures ANOVA. Her model aynı
istatistik registry/ComputeBudget/spawn worker ve atomik ProjectStore yolunu
kullanır; masaüstü PySide6/QML korunur. Panel ilk Karşılaştır ziyaretinde
oluşturulur, sonra seçimleri korunur; eski/yeni istatistik modül geçişi çalışır.

ColumnId matrix builder: raw formül/eval/pickle yok. Açık response,predictors,
kategori baseline,interaction,weight,offset/exposure,cluster/group/random slope.
Tam rank/condition/VIF (WLS ağırlıklı rank ayrıca), residual/QQ, uygun
heteroskedasticity/dispersion/influence ve convergence kontrolü. Katsayı/SE/p/
tekil CI; GLM intercept için baseline odds/rate, diğer terimler OR/rate ratio,
interaction için oran çarpanı ve doğru exp(CI). Desteklenmeyen SE/prediction
kombinasyonları engellenir. Model başına ayrı çevrimdışı yardım/support işaretleri.

AIC/BIC aynı immutable veri/RowId/response/likelihood/link/ağırlık/offset/
alpha/random/covariance ML bağlamında; quantile,REML,repeated sunulmaz.
P-değeri nedensellik veya held-out prediction başarısı değildir. Bu ekran
prediction benchmark yaptığını iddia etmez; held-out doğrulama ayrı mevcut yoldur.

[ADR041](../adr/041-statistical-models-phase40.md),
[17 kabul kaydı](phase40/acceptance.json) F40-S001..004/P001..013 C/V/G/H/P bağları.
DEC40-01 açık kullanıcı talimatı teknik uygulama yetkisidir. Resmî faz
sürüyor/deneysel/zorunlu; önceki DEP-28-GATE/insan/donanım/dağıtım kapıları açık.
P envanter kapsamı isteğe bağlı kalır; kaynak S maddeleri zorunludur.

## Son gerçek kontroller

- [65 kaynak kabul testi](phase40/acceptance-targeted.xml):46 core +9 model GUI
  +2 eski yardım GUI +8 temel GUI;65 passed /111.78s,0 failure/error/skip.
- [Noneditable wheel aynı65 test](phase40/wheel-accepted-targeted.xml):65 passed
  /119.33s,0 failure/error/skip. Dosya girişli runner; paket import yolu source
  yerine gerçek kurulu target içindedir.
- OLS/WLS kapalı matrix ve nonrobust/HC3/cluster sandwich SE; GLM intercept
  kapalı katsayı/SE/likelihood/AIC/BIC, bütün desteklenen family/SE için doğrudan
  backend farklı design referansı; offset/exposure eşitliği; açık dummy/interaction.
- Quantile bağımsız scipy LP optimumu; robust/iid SE/CI backend tanığı.
  Balanced random-intercept REML varyansı kapalı between/within hesabı; random
  slope/ML/REML ayrı backend tanığı. Repeated bağımsız balanced F/df/p;
  iki within faktörü. Singular/separation/iteration, missing/weight/count/cluster,
  tamper/cancel, unbalanced/duplicate ve repeated bütçe kontrollü ret.
  Aşırı pozitif WLS ağırlığı nedeniyle efektif rank kaybı ayrı kontrollü ret.
- [Kaynak GUI](phase40/source-gui-accepted/walkthrough.json) ve
  [kurulu wheel GUI](phase40/wheel-gui-accepted/walkthrough.json): her kurulumda
  sekiz modelin gerçek QML seçim/önkontrol/spawn/fit/residual görüntüsü, yöntem
  yardım düğmesi/Escape,prediction,save/close/open ve QML kayıt açma.
  Kaynak byte korunur; eski konfigürasyonla prediction reddedilir. Ek GUI:
  baseline A/interaction/cluster/prediction/filtre stale ve modül menüsünde
  eski istatistik ↔ model geçişi. Final64 artifact/48 screenshot.
  Yeni binding/type/reference/undefined-assignment hatası yok.
- [Wheel](phase40/wheel.json):254 source/wheel/installed paket dosyası byte eşit.
  [Installed importer/QML smoke](phase40/wheel-smoke.log) PASS.
- [Model numerical parity](phase40/source-wheel-numeric-parity.json):sekiz final
  source/wheel model hesabında katsayı/SE/p/CI ve etiketler eşit, rtol1e-9/atol1e-10.
- [14 belge unittest](phase40/unittest.log),
  [docs/artifacts/learning/usability ve Ruff](phase40/checks.json).
  244 çevrimdışı makale/142 statik UI bağı/460 erişilebilir alan/189 core English.
- [Final tam1187 vaka regresyon](phase40/full-regression.xml):1168 passed,
  19 skipped,0 failure/error /459.53s. Faz40'ın55 vakası geçti/0skip.
  [Özet ve gerçek skip nedenleri](phase40/regression-summary.json),
  [dört bağımsız dosya grubu ve tam collection kapsamı](phase40/full-shards.json).
  398 kaynak/test/script/lock dosyası koşu boyunca değişmedi;
  [son kaynak doğrulaması](phase40/head-verification.json).
  Skip nedenleri haricî MariaDB/MySQL/PostgreSQL/S3/Secret Service fixture'larıdır;
  gerçek sunucu kanıtı yokken başarı sayılmaz.

## Önceki koşular ve düzeltmeler

[İlk tam koşu](phase40/full-before-final-fixes/full-regression.xml):1166 passed,
19 skipped,1 failed /463.06s; yardım testi biten demo işinin kaybolan iptal
kontrolüne odak bekliyordu. Mevcut app header fallback doğruydu. Test gerçek
workerı odak dizisi boyunca aktif tutan80×0.1s bounded fixture ile düzeltildi.

[İkinci tam koşu](phase40/full-before-lazy-and-fixture/full-regression.xml):1166
passed,19 skipped,1 failed /491.13s; bu kez eski responsiveness testi20 timer
tick sırasında kısa demo işinin bitmesini running diye bekliyordu. CPU işine
bounded8s fixture verildi; timer/running/cancel/assertion gevşetilmedi.
19 ilgili GUI birlikte geçti /104.52s ve sonraki kaynak/wheel65 koşularında geçti.

WLS BP sabit terimi: whitened residual + orijinal varyans predictor tasarımı.
QML replaceAll → split/join, Repeater testi visual tree; SVG yerine GUI PNG.
GLM intercept ve interaction etiketleri düzeltildi. Native statsmodels mapping'leri
worker limit baseline öncesi yüklenir; CPU/thread/RSS/working RAM korunur.
Lazy panel active/visited döngüsü bağımsız section notify ile giderildi;
kayıt listeleri ilgili panel türüne filtrelendi. Ara yarıda durdurulan full
koşular tamamlanmış kabul edilmedi. Sandbox Zarr/asyncio sorunu nedeniyle
final full izinli dış ortamda dört bağımsız dosya grubuyla koşulur; gerçek
collection/JUnit kapsaması ve koşu boyunca kaynak byte'ları karşılaştırılır.

## Destek sınırları ve resmî açıklar

10000 satır/12 predictor/60 terim; eksik varsayılan ret veya açık complete-case.
Repeated ayrıca300 hücre/100 kişi,1–2 within,balanced complete grid;
between/GG/HF ve duplicate aggregation yok. WLS ters-varyans,survey/frequency değil.
NB2 alpha sabit; tahmin/zero-inflation/hurdle yok. Mixed ≥5 grup,random intercept
+en fazla3 numeric slope,nonrobust; prediction marginal fixed effect.
Quantile robust/iid; cluster/HC/Cook/OLS BP yok. GLM nonrobust/HC0/cluster;
OLS/WLS nonrobust/HC3/cluster. Minimum5 cluster uygulama alt sınırı,garanti değil;
50 altı küçük-küme uyarısı; CR2/wild bootstrap yok. Prediction interval yok.
Repeated yalnız result save; predictive model save/prediction yok.
Diğer model yolları safe JSON matrix/coefficients üzerinden prediction yapar.

F13 insan;F25 insan/Orca/AT;F24 minHW/cold/physical frame; kullanıcının durdurduğu
F27 dağıtım;F28 giriş;F30 büyük SAS;F31 clean offline cache açık. Fiziksel GUI,
insan/AT/minHW/clean offline install/remote CI koşulmadı; offscreen bunların yerine
geçmez. Kullanıcı değişiklikleri korundu; stage/commit/push yok. Faz41 başlamadı.
