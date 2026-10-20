# ADR044 — optional Bayes CPU şablonları

2026-10-12; DEC43-01; açık kullanıcı Faz43 talimatı. Önceki resmî kabul
kapıları korunur; Faz44 yetkisi yok. Python/PySide6/QML, mevcut tek registry,
StatisticsController/spawn/ComputeBudget ve ProjectStore yayın protokolü.

Optional `bayes` extra: PyMC5.28.5, ArviZ0.23.4, NumPy ile uyumlu
Numba0.68.0; uv.lock bütün transitives. Native backend temel açılışta import
edilmez; yalnız açık hesap eyleminde yüklenir. CPU sequential chains/cores1,
PyTensor interpreter graph; compiler/GPU/user script/pickle kullanılmaz.
Serbest model programı ileri kod alanının ayrı gelecek kapsamıdır; bu faz
herhangi bir kullanıcı programı çalıştırmaz veya import etmez.

## Şablonlar ve birimler

- Beta-binomial: bağımsız satır başına Bernoulli0/1; Beta(alpha,beta).
  Toplam success/trial sütun şablonu değildir; posterior Beta(alpha+sum,
  beta+n-sum) bağımsız analitik kontrolü ve equal-tailed interval kaydolur.
- Normal mean: Normal(location,scale) prior ve **bilinen** observation SD.
  Normal conjugate reference ayrıca kaydolur; unknown variance şablonu yok.
- Linear: Gaussian likelihood, Normal(location,scale) intercept,
  Normal(0,scale) raw numeric slopes ve HalfNormal(noise_scale) residual SD.
- Hierarchical: aynı linear + noncentered Normal group_z × HalfNormal
  group_scale random intercept;3–30 grup/her grupta2 gözlem. Random slope,
  GLM, nested/multiple group, time/spatial dependence bu şablonda yok.

Outcome ve her predictor birimi açık seçilir; slope birimi outcome/predictor;
otomatik standardization/dönüştürme yok. Kullanıcı ölçek ve gözlem/grup
bağımsızlığını doğrular. Eksik/null/nonfinite, Decimal/nested/time, kayıplı
integer, weights/interactions/offset ve rank-deficient design kontrollü ret.
Kaynak ve immutable snapshot/RowId/ColumnId/SourceRecordId değişmez.

## Prior, predictive ve sampler

Prior ailesi şablonla belirli; alpha/beta/merkez/SD ölçekleri seçilebilir.
Önkontrol 200 seeded prior predictive simülasyon: Bernoulli örnek başarı
payı veya Gaussian örnek ortalaması, gözlem tasarımı/n ve birimler görünür.
Likelihood fit etmez. Açık onaydan sonra NUTS:2–4 chain,100–2000 warmup ve
post-warmup draws, target accept0.8–0.99, seed ve CPU bütçesi saklanır.
4–1000 satır,5 predictor,2M likelihood hücresi, iki prior için8M
row×chain×draw/tune iş ve RAM/disk/wall sınırı önkontrolü. Bütçe tahminidir;
OS süreç limitleri ve callback cancellation ek sınır uygular. Derleme/başlangıç
sırasında parent grace sonrası süreç sonlandırma; sampling callback her draw
cancel/time/RSS kontrol eder. Worker Qt veya ACTIVE yazmaz.

Posterior mean/SD/equal-tailed credible interval/P(parameter>0), rank R-hat,
bulk/tail ESS, divergences/max-tree-depth/BFMI; tüm değişkenler trace panelinde,
aynı numeric chain artifact'ında. R-hat<=1.01, ESS>=100×chains, divergence0,
treehit0, BFMI>=0.3. Geçmeyen veya eksik/nonfinite tanı diagnostic_fail.
**Güvenilir rozeti hiçbir durumda verilmez**; tanı başarısı model doğruluğu,
prior uygunluğu veya nedensellik değildir. Posterior olasılığı p değildir.

PPC aynı gözlemlerde mean/SD/max replicated95% quantile ve posterior
discrepancy tail probability; misfit flag betimsel, frequentist test değildir.
Held-out predictive başarı iddia edilmez. Prior sensitivity ikinci tam NUTS
fit: Beta alpha/beta concentration çarpanı veya Normal scale/group-scale
çarpanı1.1–4. Merkez/noise prior değişmez; değiştirilmiş prior ve bütün ikinci
fit tanıları görünür. İki scenario tüm prior belirsizliğini kapsamıyor.

## LOO/WAIC ve güvenli saklama

Sonlu pointwise log-likelihood `[chain,draw,observation]` gereklidir. Sampling
tanısı geçmeden hesap/ranking yok. ArviZ PSIS-LOO Pareto-k/good_k ve WAIC
posterior variance uyarıları saklanır, uyarı varsa ranking kapalı. Log scale
elpd/se/effective parameters/pointwise kayıtlı; karşılaştırma aynı veri sürümü,
outcome, birim, likelihood ailesi ve sıralı RowId evreni ister. Paired elpd
fark SE; posterior model probability veya kesin kazanan etiketi değildir.

Artifact: safe JSON recipe/result; Parquet üyelik ve özgün observations;
sayısal h5netcdf grupları (posterior/sample_stats/log_likelihood/PPC ve
sensitivity posterior/stats), gzip4/draw chunk<=128; trace PNG. Parent
publication hash/source/RowId/details/numeric chain-summary bağını doğrular;
aynı atomik staging/ACTIVE transaction. Export yeni klasör; reopen yalnız
hash doğrulayıp veriyi okur, model/sample/user-code import etmez. Büyük chain
bellekte önce üretildiği için bounded admission gerekir; unlimited streaming
sampler iddiası yok. Credentials/ağ/provider yok; mevcut kurulmuş ortam
internetsiz hesap yapar; temiz offline kurulum ayrı kabul.

Birincil kaynaklar: [PyMC sampling](https://www.pymc.io/projects/docs/en/stable/api/generated/pymc.sample.html),
[ArviZ R-hat](https://python.arviz.org/en/v0.22.0/api/generated/arviz.rhat.html),
[ESS](https://python.arviz.org/en/v0.22.0/api/generated/arviz.ess.html),
[PSIS-LOO](https://python.arviz.org/en/v0.22.0/api/generated/arviz.loo.html),
[WAIC](https://python.arviz.org/en/v0.22.0/api/generated/arviz.waic.html).
Runtime sözleşmesi ayrıca kurulu kilitli backend imza/docstring ve gerçek
referans fixture'ında doğrulanır; live kullanıcı ağı yok.
