# Faz18 — kategori tahmini teknik kabul kaydı

2026-10-08 UTC / 2026-10-09 Europe/Istanbul, ENV-18; kilitli CPython3.13.15/PySide6 Qt6.11.2/scikit-learn1.9.1, Linux offscreen/software. Yalnız açık Faz18 kapsamı. Teknik yetenek deneysel; önceki insan/bağımlılık kabulü açık olduğu için faz sürüyor. İnsan masaüstü, bilgisiz kullanıcı, ekran okuyucu, minimum donanım ve yeni uzak CI kabulü çalıştırılmadı. Yürütülmemiş kontrol başarı değildir.

<a id="e18-s001"></a>
## E18-S001

Uygulama yolu: Model → kategori hedefi/özellik hazırlığı → değerlendirme protokolü → kategori adayları → ayrı final test onayı. Yol haritası kategori adımı hazırlık amacını seçer. [ADR-021](../adr/021-classification-phase18.md), ClassificationPanel.qml ve validation controller; gerçek QML/spawn çekirdek ve GUI kontrolleri [targeted.txt](phase18/targeted.txt).

<a id="e18-s002"></a>
## E18-S002

Gerçek Baseline/LogisticRegression/RandomForest, ikili/çok sınıflı sentetik x→kategori örnekleri. Azınlık kaynak dağılımında ve her değerlendirme sınıf desteği/tahmin sayılarında görünür.95 normal/5 sorunlu örneği %95 accuracy'nin recall0 olabileceğini anlatır. Dar C/ağaç/derinlik, Forest20k/diğer100k ve20 sınıf sınırları; eğitimden önce maliyet reddi testi.

<a id="e18-s003"></a>
## E18-S003

Elle hesap: ikili matris[[2,1],[1,2]], accuracy/precision/recall/F1=2/3; ROC-AUC8/9; trapez PR-AUC65/72; AP11/12. Çok sınıf[[1,1,0],[0,2,0],[2,0,0]], accuracy/micro F1=0.5, macro/weighted F1=0.4. Production estimator çağrısını aynı parametreyle tekrarlamak yerine küçük elle referanslar. Sıfır bölme, hiç tahmin edilmeyen C, proba desteği olmayan obje ve zaman protokolünde final risk sınıfının bulunmadığı gerçek koşu kontrollü; kalıcı defter validate_state geçer. Gerçek eğriler, ayrı tanımsızlık durumları ve averaging saklanır.

<a id="e18-s004"></a>
## E18-S004

Fit spy13 geliştirme fit'inin hiçbirinde final test RowId'si bulunmadığını doğrular; final yalnız development fit. Aday seçimi development CV F1; threshold kararı validation üyeliğine bağlı ayrı hesap.19 validation eşik adayının F1 ve seçilmiş eşiği kayıtlı. Final karşılaştırma/grid boş; threshold dondurulmuş. Geçersiz final eşik fit'ten önce reddedilir. Hata maliyeti metni kalıcı; resampling/kalibrasyon yok; saha güvenliği iddiası yok.

<a id="e18-s005"></a>
## E18-S005

Katalog26/toplam126 çevrimdışı makale,70 statik UI bağı. Beş yeni konu ve capability yardım bağları, pozitif sınıf, FP/FN, precision/recall, eşik ve olasılığı açıklar. QML/controller üzerinden her bağ açılır; yardım hesap/veri değişikliği yapmaz. Resmî web API erişimi401 token_revoked nedeniyle başarısız; kurulu birincil API/docstring incelemesi [api.txt](phase18/api.txt), çevrimiçi sayfa incelemesi iddiası yok.

<a id="e18-s006"></a>
## E18-S006

İkili/çok sınıflı tüm üç aday gerçek çalışır; azınlık hataları görünür; bağımsız elle metrik referansları ve fit spy. Gerçek spawned worker PID uygulamadan ayrı, immutable kaynak byte/hash kontrolü; yanlış sınıf ve iptal tamamlanmış sonuç olarak sunulmaz. [Ölçüm betiği](../../scripts/measure_phase18.py) kaynak/noneditable wheel üzerinden aynı uygulama eylemlerini yürütür.

<a id="e18-s007"></a>
## E18-S007

Choice geçmişi sınıf, averaging, eşik modu/değeri, model adayları/C/ağaç/derinlik/maliyet/tarih/status/prior test kimliklerini saklar ve gösterir. Karar sonucunda seçilmiş validation eşiği ayrıca saklanır. İki final kullanımı, sonrasında pozitif sınıf/C/eşik değişikliği ve reopen kontrolü; önceki kayıtlar değişmez. Dondurulmuş kararda tamper reddi. Sonraki seçim keşifsel; ilk kullanımda bile proje dışı tekrarın bilinmediği açık. Faz16 defteri korunur.

## Gerçek doğrulama kayıtları

Odaklı75 test (26 yeni sınıflandırma +49 korunmuş regresyon/doğrulama) [targeted.txt](phase18/targeted.txt). Kaynak [headless.json](phase18/headless.json)/[çıktı](phase18/headless.txt); kurulu wheel [wheel.json](phase18/wheel.json)/[çıktı](phase18/wheel.txt). Nihai kontroller [checks.json](phase18/checks.json), [tüm pytest](phase18/pytest.txt), [sistem unittest](phase18/system-unittest.txt). İlk başarısız denemeler kabul kanıtı değildir; aşağıdaki nihai sonuçlar kullanılır.


Nihai kilitli test: **502 pytest / 169.32s**, **9 unittest**;75 odaklı test /38.84s. Locked dev sync, sistem+locked check_docs, check_artifacts/check_learning, Ruff check/format ve kurulu giriş noktası smoke exit0. Sistem Python3.14 keşfi **51 test /42 import errors /exit1**; eksik NumPy/Polars/PySide6/sklearn/dev paketleri nedeniyle başarısız, ayrı ham kayıt korunur.

Kaynak ve noneditable wheel: ikili240, çok sınıf240, group_time ikili240, Forest20.000 ve Baseline/Logistic100.000 olmak üzere beş gerçek koşu; iki completed final, pozitif sınıf/C/eşik retune, kaynak hash eşitliği ve yeniden açılmış defter. Wheel `__file__` /tmp/veri-ufku-phase18-package içindedir, editable kaynak olmadığı betikte assert edilir. [Build](phase18/build.txt), [install](phase18/install.txt), [wheel hash](phase18/wheel.sha256), [wheel entry](phase18/wheel-entry.txt).

Son kaynak süreleri1.703/1.799/2.167/4.269/7.328s; tepe parent+worker RSS1474846720 byte, max tick628.233ms. Wheel süreleri1.737/1.788/2.078/4.154/7.534s; RSS1466224640 byte, max tick701.761ms. Sıcak runtime ve eşzamanlı yerel test yükünde geliştirici makinesi ölçümüdür; minimum donanım veya bütün performans hedeflerinin karşılandığı kabulü değildir.

Görsel inceleme: [ikili720px](phase18/headless-result-720.png), [matris/eğriler1366px](phase18/headless-matrix-1366.png), [çok sınıf wheel720px](phase18/wheel-multiclass-matrix-720.png). Ayrı final kapsamı/keşifsel uyarı, matris yönleri, sınıf sayıları, gerçek ROC/PR ve kaydırmalı dar ekran görüntülendi. Yeni fiziksel masaüstü/insan kabulü iddia edilmez. Faz19+ başlamadı.
