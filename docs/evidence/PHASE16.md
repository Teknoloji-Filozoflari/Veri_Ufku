# Faz16 — Ayırma, çapraz doğrulama ve baseline

2026-10-08, ENV-16; açık Faz16 kullanıcı kapsamı. Teknik uygulama deneysel; Faz13 insan kabulü ve Faz15 bağımlılık kabulü açık olduğundan faz durumu sürüyor. Sonraki faz başlatılmadı. Ortam [environment.json](phase16/environment.json), FS [filesystem.txt](phase16/filesystem.txt), kilit uv.lock. Gerçek masaüstü/insan/ekran okuyucu/minimum donanım/yeni uzak CI çalıştırılmadı.

<a id="e16-s001"></a>
## Gerçek ayrı geliştirme ve final değerlendirme

modeling/validation.py, baseline.py, worker.py; ui/validation.py, QML ValidationPanel; storage/validation_store mevcut tek yayın protokolünü kullanır. Baseline model ekranındaki engelsiz regresyon/sınıflandırma planından çalışır; kümelenme/anomali değerlendirmesi desteklenmiyor ve engellenir. Ayar/tahmin anı/ufuk/alanların kullanılabilirliği, sonuç, fold sayıları, kaynak/pipeline/paket/seed, test geçmişi/help gerçek Qt akışıdır. [Kaynak altı koşu](phase16/headless.json), [kurulu Linux wheel](phase16/wheel.json). tests/test_validation_gui.py.

<a id="e16-s002"></a>
## Beş ayırma yolu

Random, stratified, group, time, group_time: scripts/measure_phase16.py beşini gerçek QML→spawn→kayıt yoluyla240 kayıt üzerinde çalıştırır. tests/test_validation.py elle grup üyelik ve zaman eşitsizliğini denetler. Aynı seed+snapshot+RowId aynı split/protokol/üyeliği üretir. Zaman bağları korunur; pozitif hedef ufku training sınırını arındırır. Grup/zaman çakışması ve eksik sınıf fold reddi açık; fallback yoktur. Oranlar group/time bloklarında yaklaşık kayıt oranıdır. Ayrıntılı sınırlar [ADR-019](../adr/019-validation-baseline-phase16.md).

<a id="e16-s003"></a>
## Fit sınırı ve tekrar üretilebilirlik

Test özelliklerine1000000 değeri/TEST_ONLY kategorisi enjekte eden fixture, gerçek transformer.fit çağrılarındaki RowId ve değerleri denetler. Test train'e ulaşırsa assertion hata verir; final fit parametreleri unpoisoned final referansıyla eşit olmalıdır. Impute/onehot/scale/variance her yeni Pipeline'da yalnız train/fold; CV üyelikleri yalnız development içindedir. Merkez yalnız train hedeflerinden bağımsız hesaplanır; test MAE elle kontrol edilir. Test sonuçlarıyla otomatik ayar/estimator seçimi yok. Fingerprint/dataset/ColumnId/RowId/split/protocol/pipeline/seed/paket sürümleri ve içerik18 kaydedilir. Büyük kayıt ayrıntısı hash kontrollü artifact, QML küçük özet kullanır.

<a id="e16-s004"></a>
## Baseline, skor ve maliyet

Mean/median regresyon ve prior/most_frequent/stratified Dummy ayrı çekirdek testlerde; regresyon/kategori GUI akışında gerçek fit edilir. Balanced iki sınıfta çoğunluk baseline için elle accuracy=.5, balanced accuracy=.5, macro F1=1/3; tolerans1e-12. MAE/RMSE minimize; kategori skorları maximize. Her metrik scope/n/status/coverage/averaging; CV unweighted fold mean/ddof1 sapması. Geçersiz fold/protokol atlanmaz, tüm koşu reddedilir ve seçim kaydı failed/invalid_folds olarak kalır. GUI yaklaşık train n/fit sayısı; sonuçta gerçek train/validation/development/test/fold n ve kayıt geçişi maliyeti; süre veya evrensel yeterli satır garantisi yok.

Kaynak100000 kayıt random regresyon denemesinde3.409s baseline, parent+worker tepe RSS1120944128 byte, en büyük tick aralığı231.205ms ölçüldü. Geliştirici makinesi/sıcak runtime; minimum donanım veya bütün performans hedeflerinin karşılandığı kabulü değildir. Önceki denemede full sonuç QVariant dönüşümü19GB/11.6s tick sorunu doğurdu; küçük summaryReport aktarımıyla düzeltildi. Eski sorun çıktıları başarı kanıtı değildir; güncel JSON son ölçümdür. Kurulu noneditable Linux wheel100000 kayıt: 3.404s baseline, parent+worker RSS1119432704 byte, tick232.105ms. Son kaynak/paket ölçümleri eşzamanlı yerel regresyon yükü sırasında yapıldı; performans benchmark izolasyonu iddia edilmez.

<a id="e16-s005"></a>
## İptal, atomiklik ve veri koruma

tests/test_validation.py: fit sızıntı spy, fixed seed, group/time/combined fixture; önceden set iptal; final pending transaction fault; tamamlanmış gibi değiştirilmiş ledger reddi; pointer_written/pointer_replaced gerçek SIGKILL ve ikinci process readonly. test_validation_gui.py: metadata rezervasyonu sırasında geliştirme/final iptali, eski revision, imkânsız ufuk, durum ve structured failed seçim kaydı. İptal sonucunda başarılı baseline/final kaydı üretilmez; eski sonuç güncel görünmez. Final metrikler kalıcı completed defter yayınlanmadan gösterilmez. Source SHA256, dataset/workflow korunumu, reopen/copy/farklı kaydet çekirdek testleri. [Hedef test kaydı](phase16/targeted.txt).

<a id="e16-s006"></a>
## Birleşik protokol ve tekrar test defteri

240 kayıt/60 grup combined classification fixture: sıkı kronoloji ve ayrık varlıkları validation, expanding development CV ve final testte birlikte korur; her bölüm bütün sınıfları içerir. İki gerçek final değerlendirme aynı split/protokolü kullanır; ikinci prior_test_use_ids ilk kayda bağlı. Yeni development seçimi iki testi referanslar; proje içi copy-fork ve farklı kaydet/reopen defteri taşır. GUI defteri durum/tarih/önceki kullanım/sonraki seçim ilişkisini gösterir. Group_time+same_future çakışması GUI düğmesinde engelli ve controller açıklaması; sabit süre dışı protokol yardımda desteklenmiyor. Proje dışı kullanım bilinmez; pending durum sonuç belirsizdir.

## Kontrol kayıtları

Kilitli sync, check_docs/check_artifacts/check_learning, Ruff, tam pytest, sistem unittest, kurulu giriş noktası smoke ve Linux wheel workflow bu dizindeki gerçek komut/exit kayıtlarıyla raporlanır. Genel pytest her yöntemin kanıtı yerine geçmez; yukarıdaki fixture ve GUI yolları ayrı bağlıdır. Kontrol sonucu henüz yoksa geçmiş faz başarısı yeni kabul sayılmaz.

Sistem `python3 -m unittest discover -s tests -v` Python3.14 üzerinde35 eksik Polars/PySide6/pytest/sklearn import hatasıyla başarısız: [ham kayıt](phase16/check-03.txt). Sistem Python değiştirilmedi. Kilitli CPython3.13 ile aynı discovery9 unittest geçti: [kayıt](phase16/locked-unittest.txt). Bu sonuçlar birbirinin yerine başarılı diye yazılmadı.

Son teknik kayıtlar: [kilitli kontrol komutları/exit](phase16/checks-final.json), [tam pytest](phase16/pytest-final-state.txt), [Faz16 odaklı35 test](phase16/targeted-final.txt), [wheel giriş noktası](phase16/wheel-entry.txt), [build](phase16/build-final.txt), [noneditable kurulum](phase16/install-final.txt). Sunucu yeniden başlatmasıyla kesilen pytest çıktısı [ayrı tutuldu](phase16/pytest-interrupted.txt); başarılı kontrol sayılmadı.

Son durum:455 pytest ve kilitli ortam9 unittest geçti;9 final kontrol komutunun tamamı exit0.35 Faz16 odaklı test, kaynak/kurulu Linux wheel altı koşu ve wheel giriş noktası geçti. Aynı varlığın geleceği fixture'ında her evaluation varlığı ilgili train içinde görülür; yeni varlık karışan time planı açık reddedilir. Sistem Python denemesinin başarısızlığı yukarıdaki ayrı kayıtta korunur.
