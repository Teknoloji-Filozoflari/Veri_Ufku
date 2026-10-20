# Faz13 — ilk teknik sürüm, export, rapor ve isteğe bağlı rehber

2026-10-07 / ENV-13. Linux geliştirici ortamı; locked Python3.13.15/PySide6Qt6.11.2/Polars2.0.0/Matplotlib3.11.2, offscreen/software. Olgunluk deneysel; faz sürüyor: **F13-S005 gerçek bilgisiz kullanıcı görev kabulü ölçülmedi**. Geliştirici walkthrough'u kullanıcı testi değildir. [Karar](../adr/016-release-phase13.md), [release](../RELEASE_NOTES_0_1_0.md).

<a id="e13-data"></a>
## F13-S002 — veri exportu

Yollar src/veri_ufku/exports/data.py/files.py/worker.py, ui/exports.py ve ReportPanel.qml. Beş format yeniden açılan kayıt sayısı/şema/projeksiyon kontrolü, elle fixture değerleri ve uygulamanın gerçek import adaptörleriyle test edilir. Parquet fiziksel tür, native null/date/timezone/ns/Decimal ve sıralı değerleri korur; iç RowId dışarıda, yeniden import yeni kimlik üretir. Metin/XLSX tür kaybı açık onay/makbuzla. CSV null token/boş metin, tehlikeli başlık/metin apostrof, gerçek negatif integer/Decimal korunumu; XLSX inlineStr/no-formula, büyük integer tam metin ve precision/satır/sütun/hücre sınırları açık. NaN/±inf metin tokenıdır; null değildir. Uyumsuz nested tür ret. XLSX explicit dimension son tamamen null satırları da kapsar; gerçek adaptörde dört kayıt/boş metin/null yeniden import testi geçti. Kaynak/mevcut/symlink dosya korunur. İki spawn yayın yarışında tek kazanan; iptalde hedef/temp yok.

Her alt kimlik deneysel, ENV-13 /2026-10-07; tests/test_exports.py ve tests/test_exports_gui.py. Aynı genel test sayısı farklı format kabulü yerine kullanılmaz:

| Kimlik | Hesap / bağımsız referans | GUI / kayıt |
|---|---|---|
| F13-CSV | UTF8 Türkçe/boş/null/−12/Decimal−1.25/tarih; başlık `=header` ve iki metin korunur; gerçek adaptörde3 kayıt | Sentetik6/7 kayıt, açık politika/kayıp ve process makbuzu/save/reopen |
| F13-JSON | Aynı5 kayıt projeksiyon; native bool/int/null, Decimal/date metin; gerçek adaptörde3 kayıt |6/7 kayıt açık şema kaybı ve process makbuzu |
| F13-JSONL | Satır başına nesne; aynı5 kayıt; gerçek adaptörde3 kayıt |6/7 ve100000 kayıt process/tick/reopen |
| F13-PARQUET | Fiziksel şema/null/ns/timezone/Decimal ve sıra; gerçek adaptörde3 kayıt |6/7 ve100000 kayıt, referans çalışma tablo eşitliği |
| F13-XLSX | OOXML bağımsız okuyucu5 kayıt, all-null satır/boş metin/native−12/bool; hiçbir `<f>`;15 basamağı aşan int exact text;32768 hücre ret; gerçek adaptörde3 kayıt |6/7 kayıt ve açık ürün100k/256/32767 sınırı; makbuz/save/reopen |

<a id="e13-report"></a>
## F13-S003 — HTML ve PDF

Amaç, kaynak/köken, filtre/kapsam/sürüm, ancestor kalite/profil ve uygulanmış işlem zinciri, ilk tablo kayıtları, aynı sürümün grafikleri ve kendi yöntem/null/örneklem tarifleri; sınırlamalar. Bulgu yoksa sonuç uydurulmaz. Rapor PDF/HTML yerel kaynaklar ve kullanıcı metni escape; HTML CSP, embedded PNG/DejaVu ve statik CSS, dış script/font yok. Qt loadResource yalnız kayıtlı image bytes alır. Unicode İıŞşÇçĞğÖöÜü ve200 kayıt çok sayfalı PDF'de son kayıt bağımsız QPdfDocument metin kontrolünden geçer. Aynı sentetik rapor gerçek worker'da HTML/PDF üretilir; PNG görüntü ve yeniden açma saklanır. PDF ayrıca yerel Poppler ile görsel incelenir; bu araç runtime bağımlılığı değildir.

F13-HTML/F13-PDF deneysel ENV-13/2026-10-07. tests/test_exports.py malicious kaynak/hücre/başlık escape; tests/test_exports_gui.py grafikle gerçek GUI/worker/export/save/reopen. [Sentetik HTML](phase13-headless-example.html), [PDF](phase13-headless-example.pdf). Büyük teknik yöntem ayrıntıları raporda ayrıca bulunur; görüntü örneği bütün veri değildir.

<a id="e13-guide"></a>
## F13-S001/S004 — mevcut özellikleri bağlama

GuidePanel/GuideController: import → profil → kalite → kullanıcı seçimiyle temizlik → grafik → rapor. Atla/geri/adım seç/kapat; hiçbir ders veya temizlik zorunlu değil. Sales6/problem7 sentetik CC0 CSV+tipli Parquet paketle; açık eylem ayrı proje oluşturur. Açık taslak korunur. tests/test_exports_gui.py iki örnekle seçilmiş trim önizleme/apply, önceki kalite/profil, histogram/Agg, yedi export, save/reopen; aynı sürüm tablo/grafik ve geçmiş/makbuz eşleşir. Atlamak sürümü değiştirmez. Başlangıç ve Rapor gerçek QML kontrolleridir.

<a id="e13-help"></a>
## Yardım / paket kaynakları

Katalog12/toplam71/sözlük26; export, report ve guide; yedi capability/help_links ve QML bağları. Yeni try_action yok. Font DejaVuSans.ttf + tam lisans, CC0 örnekler, HTML/CSS ve temel yardım wheel'de bulunur. Ana uygulama fontu paketten yüklenir. [Kaynaklar](../../src/veri_ufku/assets), [lisans kararı](../adr/004-offline-licensing-packaging.md).

<a id="e13-package"></a>
## F13-S006 — erken Linux wheel ve offline ilk açılış

scripts/measure_phase13.py kaynak ve noneditable kurulu Linux wheel üzerinde /tmp cwd + yeni XDG config/state/cache ile; parent/spawn Python TCP fail-fast. Qt/QML yerel kaynak, PDF kaynak allowlist'i; HTML data kaynak/CSP. OS ağ arayüzlerinin kapatıldığı iddia edilmez. Uygulamanın font/yardım/örnek/rapor için ağ gereksinimi yoktur. Bu çalışma offline çalışma kanıtıdır; temiz makineye offline kurulum veya tam wheelhouse değildir.100000 CSV/JSONL/Parquet kayıt doğrulaması, Qt event loop/RSS, cancellation, kaynak hash ve kayıt roundtrip. [Kaynak ölçümü](phase13-headless.json), [kurulu wheel ölçümü](phase13-wheel.json). Boyut/tema/yazı ekranları aynı gerçek QML yolundan alınır; fiziksel masaüstü/HiDPI değildir.

<a id="e13-checks"></a>
## Gerçek kontroller ve ilk entegrasyon bulguları

Standart locked sync/check_docs/check_artifacts/check_learning/Ruff/pytest/unittest ve offscreen kurulu giriş noktası smoke korunur. Nihai sonuçlar [phase13-checks.txt](phase13-checks.txt) dosyasına kaydedilir. Çalıştırılmayan kontrole başarı verilmez. Sistem Python3.14 paket/sürüm ortamı değildir; kilitli testler ayrı kayıttır.

İlk entegrasyon: QML semicolon parse ve yanlış opened property düzeltilip giriş noktası yeniden geçti. Polars2.0.0 collect_batches iterator stop() yoktu; kod kurulu sürüme uyarlandı. Grafik içeren PDF worker'ında Qt/font yükleme öncesi RLIMIT_AS takılma yarattı; önce disposable Qt/font bootstrap, ardından ortak CPU/adres/wall/cancel bütçesi ile gerçek worker geçti. Çıktı makbuzları synchronous legacy save yolunda kayboldu; draft kopyası depoya taşındı. GUI'nin request(save) yolu ve reopen makbuz/temizlik zinciri ayrıca test edildi. Entegrasyon engelleri Faz27'ye ertelenmedi.

<a id="e13-user-pending"></a>
## F13-S005 — zorunlu gerçek kullanıcı görevi açık

Bu oturumda gerçek veri bilimini bilmeyen katılımcı yok; görev tamamlama/yardım ihtiyacı/kritik hata kullanıcı ölçümü yok. Geliştirici otomatik GUI walkthrough'ları teknik kullanılabilirlik yolunu gösterir; kullanıcı testi sayılmaz. Faz sürüyor, ilk sürüm teknik önizleme. [Görev protokolü](PHASE13_USER_TASK.md) gerçek katılımcı için hazırdır. Fiziksel masaüstü kabulü, uzak yeni CI, temiz offline kurulum/minimum donanım ve tüm dağıtımlar ayrıca doğrulanmadı.

Son XLSX integration kontrolü: dimension olmayan boş son satır, uygulamanın gerçek adaptöründe kapsam dışında kalıyordu. Export explicit A1:lastColumn:lastRow boyutu yazıyor; trailing all-null kayıtlar ve boş metin gerçek adapter reimportta korunuyor. Native dosya seçici widget'ı fiziksel masaüstünde kullanılmadı; QML düğmesi ve FileDialog accepted sinyali otomatik kontrol edildi.

## Nihai yerel sonuç

339 pytest ve9 locked unittest geçti; locked offline dev sync, check_docs/check_artifacts/check_learning, Ruff check/format ve source kurulu giriş noktası smoke exit0. Yardım71 makale/49 QML bağı. Source ve noneditable Linux wheel aynı rehber/cleaning/grafik/yedi export/PDF process yolunu geçti; wheel bin/veri-ufku smoke da exit0. Beş formatın kaybı/kayıt ve gerçek adaptör reimportu, trailing null XLSX, güvenli/kapalı CSV policy ve doğru format capability makbuzu test edildi. Tam kaynak/kanıt eşlemesi [source SHA256](phase13-source.sha256); [ortam](phase13-environment.json), [font embedding](phase13-pdf-fonts.txt), [Poppler PDF görseli](phase13-pdf-poppler-page1.png).

Sistem Python3.14 unittest importları paket/PySide6/Polars eksikliğiyle başarısız: [ayrı kayıt](phase13-system-unittest.txt). Üretim projesinin >=3.13,<3.14 sözleşmesine uygun locked runtime kontrolleri başarılıdır; sistem komutu başarı olarak kaydedilmedi. Uzak bu değişikliklere ait CI koşusu yok; workflow'a erken wheel/offline rapor kontrolü eklendi. F13-S005 kullanıcı görevi çalıştırılmadığı için faz sürüyor ve release teknik önizlemedir.
