# Faz17 — Bir sayıyı tahmin etmek istiyorum

2026-10-08, ENV-17; Linux CPython3.13 kilitli uv ortamı, Qt offscreen/software. Yalnız açık Faz17 kapsamı. Teknik yetenek deneysel; önceki insan/bağımlılık kabulü açık olduğu için faz sürüyor. Gerçek kullanıcı, fiziksel masaüstü, ekran okuyucu, minimum donanım ve yeni uzak CI kabulü çalıştırılmadı.

<a id="e17-s001"></a>
## Uçtan uca regresyon

Faz15 hedef/özellik/hazırlama planı ve Faz16 split/tahmin anı/ufuk/kullanılabilirlik formundan QML RegressionPanel gerçek ayrı process eğitimine gider. Baseline, LinearRegression, Ridge ve RandomForestRegressor sınırlı adayları, hedef birimi, dar ayarlar ve maliyet sınırları görünür. Her aday train/fold pipeline; kaynak değişmez. Kayıt güvenli JSON, pipeline/seed/paket/RowId/split/protokol/provenance, yeniden açma. [ADR-020](../adr/020-regression-phase17.md).

<a id="e17-s002"></a>
## Adaylar, maliyet ve gerçek tahmin

`tests/test_regression.py::test_true_predictions_cv_baseline_reference_and_test_fit_spy`: y=3x+7,120 kayıt; gerçek doğrusal tahmin ve MAE<1e-10, bağımsız NumPy train merkezi/validation MAE referansı, Ridge ve Forest baseline karşılaştırması. Dört aday × (holdout+3 fold)=16 gerçek fit çağrısı; spy test RowId veya hedef özelliğe girdiğinde başarısız olur. Seed aynı split üretir. Forest20.000, diğer adaylar100.000 uygun kayıt; yoğun hücre/RAM/duvar süresi sınırları. Narrow ayarların reddi ayrı parametrik testler. Süre/yeterli satır garantisi yok.

<a id="e17-s003"></a>
## Metrikler ve grafikler

MAE/RMSE minimize, hedefin birimi kullanıcı beyanı; R² maximize, negatif olabilir. Sabit değerlendirme hedefi null/undefined_constant_target olarak test edildi ve kaydedildi; bütün kaynak sabitse hazırlık açık reddeder. Gerçek/tahmin ve gerçek−tahmin artık grafikleri validation veya ayrı final kapsamındadır. En fazla1000 deterministik görsel örnek; metrik n bölümün tamamını kapsar. Qt GUI testi gerçek visual item/points ve kapsam metnini doğrular. Yüzdelik genel regresyon doğruluğu sunulmaz.

<a id="e17-s004"></a>
## Final test ve geçmiş

Minimum development CV ortalama MAE seçimi; holdout/CV karşılaştırması final test görünümünden ayrıdır. Final yalnız seçilen dondurulmuş adayın development fit/test predict adımıdır; finalde aday karşılaştırması boş olmalıdır. Phase16 test defteri pending rezervasyonu sonuçtan önce, completed yayın sonuç gösterilmeden önce. Aday ve ayarlar ledger/geliştirme/final bağına eklenmiştir. İki final değerlendirme, sonraki retune/choice ilişkisi, büyük artifact hydrate/hash ve reopen çekirdek testi; gerçek GUI final/retune/reopen. Önceki test kullanımından sonraki run keşifsel; bağımsız final diye sunulmaz. Proje dışı kullanımı bildiği iddia edilmez. Phase16 copy/farklı kaydet/transaction/SIGKILL testleri korunur.

<a id="e17-s005"></a>
## Çevrimdışı yardım

İçerik19, model-regression: regresyon/baseline/hata birimi/artık/aşırı öğrenme, negatif/sabit R², test seçim sınırı. model.regression bağlamı gerçek Qt yardım açma testinde; check_learning UI/capability bağlarını doğrular.

<a id="e17-s006"></a>
## Hata, sızıntı ve iptal

Hedef özellik olarak engellenir; sayısal olmayan/boş-sabit hedef anlaşılır hazırlık açıklamasıyla reddedilir. Eksik hedef RowId dışlama kaydı, hedef doldurulmaz. Eksik özellik işlemleri eğitim katındadır. `test_group_time_regression_candidates_and_constant_fold` dört aday için birleşik protokolü ve test fit dışlamasını doğrular. GUI unsupported birleşik protokol düğmesi engelli; iptal edilmiş seçim canceled ve sonuç yok. Phase16 fold/imkânsız split/iptal/stale/fault testleri yeniden koşulur.

<a id="e17-s007"></a>
## Gerçek kontrol kayıtları

[49 odaklı test](phase17/targeted.txt): regresyon çekirdek/GUI ile korunmuş Faz16 çekirdek/GUI. [Kaynak çalışma ölçümü](phase17/headless.json), [ham çıktı](phase17/headless.txt); kurulu wheel ve nihai komut kayıtları bu dizinde tutulur. Sonuç bulunmayan kontrol başarı kabul edilmez. İlk düzeltme denemeleri kabul kanıtı değildir; nihai kayıtlar kullanılır.

Son kontrol listesi [checks.json](phase17/checks.json): kilitli dev sync, docs/artifacts/learning, Ruff check/format,9 locked unittest ve kurulu giriş noktası smoke exit0. [Noneditable wheel çalışma](phase17/wheel.json), [build](phase17/build.txt), [kurulum](phase17/install.txt), [wheel entry](phase17/wheel-entry.txt). Kaynak240 bağımsız/combined,20.000 Forest ve100.000 doğrusal aday koşuları sırasıyla1.305/1.235/3.638/5.790s; tepe parent+worker RSS1528647680 byte, en büyük tick770.544ms. Eşzamanlı yerel test yükünde geliştirici makinesi ölçümü; minimum donanım veya bütün performans hedeflerinin karşılandığı kabulü değildir. Grafik görsel incelemesi [720px](phase17/headless-result-720.png) ve [1366px](phase17/headless-result-1366.png): scope/keşifsel uyarı, gerçek tahmin ve artık grafikleri.

Nihai tam pytest: [469 geçti,138.72s](phase17/pytest-final.txt). İlk tam deneme [pytest.txt](phase17/pytest.txt) yeni yardım makalesinin sözlük sayımındaki53→54 fixture güncellemesinden önce1 başarısız/467 geçti; başarı sayılmadı. Sistem Python3.14 unittest [37 import hatası](phase17/system-unittest.txt) ile başarısız; sistem ortamına Polars/PySide6/pytest/sklearn kurulmadı. Kilitli CPython3.13 ortamında aynı discovery9 unittest geçti; iki sonuç birbirinin yerine kullanılmaz.

Son durumda49 odaklı test18.45s; tüm9 kilitli kontrol exit0. Nihai source çalışması [headless-final.txt](phase17/headless-final.txt), noneditable wheel4 koşu ve iki completed final/reopen [wheel.json](phase17/wheel.json). Kaynak hashleri koşu öncesi/sonrası eşit doğrulandı.
