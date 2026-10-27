# Faz43 — optional Bayes şablonları ve model kontrolü

<a id="e43"></a>
2026-10-12; DEC43-01 açık kullanıcı talimatı; ENV-43.
Teknik kapsam ile resmî faz kabulü ayrıdır; önceki kapılar korunur.

Optional PyMC5.28.5/ArviZ0.23.4/Numba0.68.0 kilitli CPU backend; dört
sınırlı şablon: bağımsız Bernoulli beta-binomial, bilinen observation SD ile
normal mean, Gaussian linear, noncentered group random-intercept regression.
Kaynak veride dönüşüm veya user code import yok; predictor/outcome birimleri
ve raw scale açık. [Tam input/sampling/artifact sözleşmesi](../adr/044-bayes-phase43.md).

Prior ailesi/merkez/SD/şekil seçimi, 200 seeded prior predictive önizleme,
açık onay, iki prior için bütçe, chains/warmup/draws/seed/target_accept.
Posterior mean/SD/equal-tailed credible interval/P(>0); her parametre rank
R-hat/bulk-tail ESS; divergence/tree-depth/BFMI/trace. Diagnostic fail görünür,
hiçbir durumda güvenilir rozeti yok. Posterior olasılığı frequentist p değil.
Posterior predictive mean/SD/max ve misfit flag betimsel eğitim-verisi kontrolü;
held-out başarı değildir. Alternatif prior ikinci gerçek sampler fit ve tanıları.

LOO/WAIC finite pointwise likelihood ve sampling tanıları ister;
Pareto-k/good_k ve WAIC uyarıları saklanır; warning varsa ranking kapalı.
Aynı dataset/outcome/unit/likelihood/ordered RowId ile paired elpd fark/SE.
Chain artifact sayısal h5netcdf/gzip4/draw chunk<=128; posterior/likelihood/
PPC ve ikinci prior grupları, safe JSON, observations/member Parquet ve PNG.
Hash/source/RowId/chain-summary kontrolüyle mevcut atomik ProjectStore.

## Gerçek doğrulama kaydı

Son kaynakta **76 hedefli vaka** geçti:29 Bayes+47 önceki Faz42;170.16s/0skip.
Son F1/odağa dönüş GUI kontrolü ayrıca5passed/77.43s. Tam regresyon **1305passed/19skip/0failure-error**, 1324 vaka; beş temiz pytest sürecinde, suite süreleri toplamı1920.04s (paralel koşuların duvar süresi değildir).
[JUnit](phase43/full-regression.xml),[çıktı](phase43/full-regression.txt),
[özet/skip gerekçeleri](phase43/full-summary.json).19skip eski optional
DB/S3/Secret Service test sunucusu/ortamı yok; test edilmiş sayılmaz.
Faz43 tüm29 vaka passed/0skip.416kaynak/test/script/lock koşuda değişmedi:
[hash](phase43/head-verification.json).
çalıştırılmayan kontrol başarılı sayılmaz.
[76 hedefli test](phase43/targeted-final.xml): dört gerçek CPU sampler + QML,
analitik Beta/Normal conjugate, ayrı uzun sampler yakınsama/referans kontrolü,
actual draw callback cancel, GUI cancel, diagnostic fail, finite likelihood,
ArviZ LOO/WAIC bağımsız referansı/Pareto-WAIC warning gate, raw unit/missing/
weight/budget/source ret ve publish/reopen. [Çıktı](phase43/targeted-final.txt). [Son F1 GUI](phase43/gui-final.xml).

Noneditable installed wheel29passed/86.94s/0skip; [JUnit](phase43/wheel-targeted.xml),
[çıktı](phase43/wheel-targeted.txt). Source/wheel4'er gerçek QML/spawn/preview/
help-F1/Escape/export/save/reopen akışı;32+32 geniş/dar görüntü,24+24safe
JSON/Parquet/NetCDF/PNG artifact. [Source](phase43/source-gui/walkthrough.json),
[wheel](phase43/wheel-gui/walkthrough.json), [geliştirici görsel inceleme](phase43/visual-review.json).
263source/wheel/install paket dosyası byte eşitliği [manifest](phase43/wheel.json);
[installed GUI_SMOKE PASS](phase43/wheel-smoke.txt).
[ENV-43](phase43/environment.json), [lazy registry](phase43/lazy-registry.json),
[14 C/V/G/H/P kayıt](phase43/acceptance.json).
Katalog59/273;147UIbinding,557namedfield,189coreEnglish;14belge unittest ve
docs/artifacts/learning/usability/Ruff check-format.
[Lisans/NOTICE](../third_party/phase43/manifest.json).

İlk backend çözümlemesinde Numba0.63.0b1 NumPy2.5 ile import hatası verdi;
kilitli Numba0.68.0/PyTensor2.38.2 ile gerçek sampler doğrulandı. Test fixture
iki eksik `x` argümanı düzeltildi; başarısız [ilk](phase43/initial-core-error.txt)
ve [ikinci](phase43/second-core-error.txt) koşular kabul değildir.
Directory watcher, başka controller dataset kaydı sırasında pending refresh'i
kuyruğa aldı ama `ProjectsController._poll` kendi future'ı yokken işlemiyordu.
İş boşaldığında read-only source freshness recheck eklendi; kaynak tazeliği
sessizce unchanged sayılmaz. [Yakalanan GUI hata](phase43/source-refresh-error.txt).
Gerçek GUI testinde kayıt sırasında directory event zorlanır.
Yeni numeric chain-summary mutation testi doğrulamanın yanlış experiments
dalına bağlandığını yakaladı; Bayes dalına taşındı; son76 vaka bunu ve eski
Faz42 yayınını birlikte doğrular. İlk tam koşu28passed/1failure ile kontrollü
durduruldu; [kayıt](phase43/interrupted-full-regression.txt) kabul değildir.
İlk installed pytest koşucusunda __main__ guard eksikliği spawn ile testi
rekürsif başlattı; [ilk24passed/1GUIerror](phase43/initial-wheel-targeted.xml)
kabul değildir. Correct guarded runner ile son29passed.
İlk console smoke XDG_STATE_HOME izolasyonu eksikliği nedeniyle configuration
ret verdi; fresh bütün XDG dizinleriyle son GUI_SMOKE PASS. Uygulama startup
ayar güvenliği gevşetilmedi.

## Sınırlar ve açık kabuller

4–1000 complete rows/5 numeric predictors;2–4chains;2M likelihood cells;
bounded two-prior work/RAM/disk/time. Gaussian known-SD mean, single group
random intercept; unknown-variance mean/random slope/GLM/nested group/weights
uygulanmadı. İki prior tüm duyarlılık evreni değildir. MCMC draws önce bellekte;
unlimited streaming iddiası yok. Serbest model/script ileri kod alanının ayrı
kapsamıdır; bu faz o alanı uygulamaz. Temel uygulama backend olmadan çalışır.

Kurulu locked ortamda internetsiz CPU çalışması temiz offline kurulum değildir.
F13 insan/F25 insan-Orca-AT/F24minHW-cold-physical/F27durdurulan dağıtım/
F28giriş/F30büyükSAS/F31cleanofflinecache açık. Fiziksel masaüstü/insan/AT/
minimum hardware/cleanofflineinstall/remoteCI burada koşulmadı. Önceki Faz42
paired/cluster/factorial/sequential kapalı alt işler korunur. Faz44 yetkisi yok.
Kaynak/kullanıcı çalışma ağacı korunur; stage/commit/push yok.


Monolithic tam koşu687passed/19skip sonrasında eski lifecycle GUI testinde
uygulama+iş toplam2GiB bütçe reddi verdi; [kayıt](phase43/monolithic-memory-full-regression.txt)
başarı değildir. Optional backend core testleri PyMC/ArviZyi test ana
sürecinde tutar; üretim hesapları ayrı worker sınırındadır. [Fresh backend
import RSS farkı](phase43/backend-rss.json) minimum-hardware/GUI peak ölçümü
değildir. Bütçe gevşetilmedi; tam koleksiyonu backend24 ve application1300
olarak doğrulama denendi; uzun application koşusu da889passed/19skip sonrasında
eski regression GUI testinde aggregate2GiB ret verdi:
[kayıt](phase43/long-application-memory-full-application.txt).
Uzun tek-süreç/session kararlılığı kabulü verilmez. Tüm koleksiyon dört temiz
application grubu338/309/338/315 +24backend şeklinde doğrulandı; aynı
bellek sınırı, [grup planı](phase43/regression-groups.json).


İzole süreç grubu mevcut iterative-imputation model paketlemesinde import
sırasına bağlı skops trust farkını yakaladı: [ilk grup](phase43/full-app3.txt).
Yalnız mevcut TRANSFORMS içindeki reviewed IterativeImputer kapalı TRUSTED
listesine açık eklendi; wildcard/dış model/kullanıcı tipi kabul edilmez.
[İzole iterative +35lifecycle test](phase43/serialization-reference.xml):36passed/9.37s.
Son full gruplar ve paket kontrolleri bu son kaynak üzerinde doğrulandı.


Son kurulu wheel Bayes29 + reviewed serialization36 toplam65passed/104.19s:
[JUnit](phase43/wheel-final-compat.xml),[çıktı](phase43/wheel-final-compat.txt).
Son paket [263byte-match](phase43/wheel.json) ve [GUI_SMOKE](phase43/wheel-smoke.txt)
doğrulandı. Bayes QML/engine/calculate dosyaları walkthrough sonrasında değişmedi;
son değişiklik yalnız mevcut sklearn reviewed-type listesi, yukarıdaki65
kurulu testte ayrıca doğrulandı.
