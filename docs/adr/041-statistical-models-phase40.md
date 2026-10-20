# ADR-041: Faz40 güvenli istatistiksel model yolları

2026-10-11. Kullanıcının Faz40 uygulama talimatı teknik çalışma yetkisidir
(DEC40-01); önceki resmî DEP-28-GATE ve insan/donanım kapıları kapanmaz.

## Backend ve alt aşamalar

Kilitli CPython3.13.15 / statsmodels0.15.0 yerel API ve kaynakları incelendi.
40.1 OLS/WLS → 40.2 GLM → 40.3 quantile → 40.4 mixed → 40.5 repeated.
Tek istatistik controller/spawn worker, ComputeBudget ve registry genişletilir.
Yalnız GUI mevcut analysis_store/ProjectStore atomik ACTIVE yayını yapar.

Formül executable metin değildir: ColumnId üzerinden sayısal matrix, açık
baseline dummy ve seçili iki predictor interaction blokları üretilir.
Intercept her zaman vardır. Response/predictor ve yardımcı roller ayrıdır.
En fazla10000 satır/12 predictor/60 matrix sütunu; sessiz sample yok.
Eksik/NaN/inf varsayılan ret; açık complete-case sayımı/RowId üyeliği kaydedilir.
Decimal/tarih/nested ve Float64'e kayıpsız sığmayan integer reddedilir.
Tam rank/condition ve VIF önkontrol; kategori2–20 gözlenen düzey ister.

## Bilimsel destek sınırları

OLS/WLS: nonrobust/HC3/cluster. WLS ağırlığı pozitif ters-varyans;
survey/frequency değil. Koenker BP whitened residual ile orijinal predictor
varyans tasarımını kullanır (sabit terim korunur); Cook/leverage whitened OLS.
GLM binomial0/1 logit; Poisson ve NB2 negatif olmayan integer/log.
NB2 alpha pozitif kullanıcı sabitidir, dispersion tahmini değildir.
Log-count offset veya pozitif exposure, birlikte değil. GLM nonrobust/HC0/cluster.
Cluster correction backend sandwich; en az5 bağımsız küme uygulama alt sınırı,
50 altı küçük-küme uyarısı; CR2/wild bootstrap sunulmaz.
QuantReg robust/iid covariance,0.05–0.95 quantile. HC/cluster sunulmaz.
Gaussian MixedLM random intercept + en fazla3 numeric slope; ≥5 grup, her grup
random matrix rank/yeterli kayıt. nonrobust; ML veya REML açık seçim.
AnovaRM1–2 within factor, tam dengeli grid, duplicate aggregation yok;
between effects ve GG/HF correction yok, sphericity varsayımı açıklanır.

Singular, separation, iteration/convergence ve mixed covariance boundary/hessian
hatası kontrollü reddedilir; geçersiz p/SE/CI yayımlanmaz. Tanılama tüm üyelerde;
grafikte en fazla1000 açık deterministik örnek. Count Pearson dispersion1.5
uyarı eşiği heuristiktir. Quantile/mixed'e OLS BP/Cook otomatik uygulanmaz.

Katsayı/SE/p/tekil CI ve logit OR/log-count rate ratio dönüştürülmüş CI görünür.
AIC/BIC backend ML tanımı (GLM bic_llf); aynı response, RowId, dataset sürümü,
family/link, weight/offset/alpha/random/covariance bağlamında karşılaştırılır.
Quantile/REML/repeated için bilgi kriteri yok. Küçük p prediction başarısı veya
nedensellik kanıtı değildir; held-out validation ayrı mevcut model ekranındadır.

## Kayıt ve prediction

Safe JSON design/coefficients + RowId parquet + fontları gömülü SVG diagnostic
mevcut result journal içinde hash doğrulanarak saklanır; pickle/eval yok.
OLS/WLS mean, GLM probability/count mean, quantile conditional quantile,
mixed yalnız marginal fixed effect prediction. Yeni kategoriler reddedilir;
offset/exposure eğitim sözleşmesine uyar. Prediction interval sunulmaz.
Repeated yalnız inference result save; predictive model save/prediction yok.
Eski veri/filtre/tarif sonucu açık uyarı taşır ve prediction/save engellenir.

## Doğrulama

Kapalı matrix/sandwich, GLM likelihood, quantile bağımsız LP, balanced mixed
varyans ve repeated F referansları; her yol gerçek QML/spawn/save/reopen/help.
Gerçek koşu sonuçları docs/evidence/PHASE40.md içinde tutulur; fiziksel GUI ve
insan/AT kontrolleri çalıştırılmış kabul edilmez.

AnovaRM backend subject×within saturated design kurar; bu yüzden repeated
kapsam ayrıca300 hücre /100 kişiyle sınırlıdır. Native statsmodels/pandas
mapping'leri ortak RLIMIT_AS baseline alınmadan önce yüklenir; CPU/thread/RSS ve
çalışma RAM/disk limitleri korunur. GUI PNG rasterı gösterir; SVG path fontları
ve PNG birlikte atomik sonuç kaydına girer.

GLM intercept dönüşümü baseline odds / rate-expected-count olarak gösterilir;
interaction exp(beta) odds/rate-ratio multiplier, diğer terimler OR/rate ratio.
Yardım/odak regresyon fixture gerçek demo işini8s aktif tutar; iş tamamlanınca
kaybolan origin yerine mevcut başlık fallback davranışı değiştirilmez.

WLS tam rank/condition kontrolü ağırlıklı design üzerinde de yapılır; aşırı
ağırlık farkında pseudoinverse sessiz kabul edilmez. Model paneli ilk section4
ziyaretinde yüklenir ve state korunur; active flag bağımsız section notify
yoluyla yönetilir. Kayıt listeleri legacy/model türüne filtrelenir.
