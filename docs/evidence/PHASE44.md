# Faz44 — nedensel soru, tanımlama ve sınırlı şablonlar

<a id="e44"></a>
2026-10-12; DEC44-01 açık talimat; ENV-44. [ADR045](../adr/045-causal-phase44.md)
yöntem/estimand/CI/varsayım ve input sınırları için ana teknik sözleşme.

44.1randomizeATE/adjustment/IPW/AIPW ilk alt aşama;44.2matching matchedATT;
44.3balanced2pre/1postDiD;44.4binaryIVWaldLATE. DAG editor gerekçeli rol/yön;
identification paneli, backdoor/positivity/extremeweights/paralleltrend/weakIV
engelleri kalıcı “belirlenemiyor”; varsayımlar/alternatifler/sensitivity,
ValidationPlan sourceRowId ve matching eşlemesi güvenli JSON/Parquet export.

Gerçek doğrulama dosyaları bu dizindeki koşu kayıtlarıdır; koşulmamış kapı
başarılı değildir. Physical masaüstü, insan/Orca/AT,minhardware,cleanoffline
kurulum ve remoteCI yapılmadı; önceki resmî kabuller korunur. Faz43 önceki
regresyon sayıları bu fazda yeniden çalıştırılmış sayılmaz.

## Gerçek teknik doğrulama

ENV-44: kilitli CPython3.13.15 `.venv`; mevcut NumPy2.5.3/SciPy1.18.0/
statsmodels0.15.0/scikit-learn1.9.1/Polars2.0.0/PySide6.11.2. Yeni bağımlılık yok.
[Ortam](phase44/environment.json), [15 C/V/G/H/P kayıt](phase44/acceptance.json).
F44-S001..004/P001..011 teknik doğrulandı; faz resmî **sürüyor/deneysel/zorunlu**.

**25 Faz44 vakası** source ve noneditable installed wheel üzerinde geçti;
[son source25](phase44/causal-final.xml),[son wheel25](phase44/wheel-targeted.xml).
Son identifier type hardening/negative safe-plan kontrolleri ayrıca source17
[core](phase44/core.xml) ve installed17 [core](phase44/wheel-core-final.xml).
[Son source25 çıktı](phase44/causal-final.txt),[wheel25](phase44/wheel-targeted.txt).
Bilinen Y=2T+0.8X müdahale, randomized Welch referansı, IPW/AIPW/g-formula,
train/eval ayrılığı/tam out-of-fold kapsamı; d-separation/latent/collider/mediator/
cycle ve eksik assumptions; exact separation ve finite extremeweight/overlap;
matching çift RowId+SourceRecordId ve no replacement; balancedDiD/pretrendfail;
IV2SLS bağımsız referans/weak fail; sensitivitybias/placebo ve safe source/publish
mutation ret. Kaynak ve wheel gerçek QML/spawn/explicitpreflight/onay/
help-F1-Escape/export/save/fresh-result-reopen/cancel; positivity “belirlenemiyor”
GUI raporu save/export [test](../../tests/test_causal_gui.py).

İlgili kaynak regresyonlarında **158 farklı vaka** geçti:126 istatistik/deney/
registry/learning/usability [koşu](phase44/targeted.xml),29 önceki Bayes
[koşu](phase44/bayes-regression.xml),son faz/core koşularındaki yeni3vaka;
[tekil testcase özeti](phase44/test-summary.json). Koşular örtüşür; toplam
koşu sayısını tekil vaka sayısı gibi sunma. **Tüm depo regresyonu çalıştırılmadı.**
Son source ve wheel değişiklikleri/byte eşitliği [head](phase44/head-verification.json).
267package source/wheel/install byte eşitliği [manifest](phase44/wheel.json).
Fresh dörtXDG kurulu giriş smoke [PASS](phase44/wheel-smoke.txt).

Source/wheel yedi yöntem×iki genişlik×dört konum:56+56 render ve28+28safe
JSON/Parquet export. [Source](phase44/source-gui/walkthrough.json),
[wheel](phase44/wheel-gui/walkthrough.json),[geliştirici görsel inceleme](phase44/visual-review.json).
DAG ok uçları kutu dışında görünür; uzun adlar elide, tam gerekçe/listede kalır.
Kayıt sayısı ve bağımsız analiz birimi sayısı ayrı (DiD240satır/80birim).
Katalog60/282;150UIbinding/590namedfields/189finishedcoreEnglish;
[learning](phase44/learning.txt),[usability](phase44/usability.txt).
Docs/artifacts/Ruffcheck-format/14belge unittest kapıları geçti.

## Sınırlar ve ilk koşular

Bu implementasyon tam causal-method evreni değildir: complete numeric/dönem,
2000iid/3000balanced3period/5covariate; no weights/imputation/staggeredadoption/
nonbinaryinstrument/arbitrary nuisance learner. Adjustment/IPW/matchingCI
uygulanmadı; AIPW/strongIV≥100asyCI nuisance/validity varsayımlarına koşullu.
Sabit fixture CI kaynağı ve nüfusu doğrular; latent exchangeability kanıtlamaz.
Bias senaryosu confounding tahmini değildir; placebo non-rejection kanıt değil.

İlk randomizedfixture scalar treatment üretti, size=n düzeltildi. İlk collider
testi T→collider yolunu backdoor graph'ta kalır sanıyordu; doğru latent backdoor
fixture ile düzeltildi. [İlk121 koşusu](phase44/initial-targeted.xml) başarısız
kayıttır, kabul değil; gerçek sayısı120passed/1failure. SourceRecordId indexing
NumPyint Polars tarafından reddedildi; açık int indeksine düzeltildi; son17core
ve25GUI/source/wheel geçer. Initial/prior walkthrough klasörleri son kanıt değildir.
Identifier hardening, unit-count metadata ve son çekirdek doğrulamaları ayrı
kaydedildi; eski regression koşusunu değişmeyen son head diye sunulmaz.

Physical masaüstü/insan/Orca/AT/minHW/cleanofflineinstall/remoteCI bu fazda
yapılmadı. Önceki resmî kapılar ve Faz43 monolitik uzun oturum aggregateRAM
sınırı korunur. Connector/sunucu bu fazda test edilmedi. Stage/commit/push yok;
Faz45 başlatılmadı.
