# Sade Veri aktarımı ve başlık kartları

2026-10-10 Europe/Istanbul, ENV-UI-IMPORT-SIMPLE. Yalnız açık kullanıcı UI isteği; yeni faz başlatılmadı. UIS-01..03 ana kayıtları REQUIREMENTS_MATRIX içinde. Python/PySide6/QML ve mevcut import parser/snapshot/yayınlama protokolü korunur.

Sayfa sağ üst genel “Bu ne işe yarar?” düğmesi gösterilmez. Öğren ve F1 mevcut çevrimdışı içerikleri açar; kapatınca odak görünür kontrolüne döner. Veri başlıkları açıklama/numara/+/− kartlarıdır; klavye Space ile aç/kapa gerçek testtedir.

Import başlığından önceki proje açıklaması ve dosya yolu satırları kaldırıldı. Proje yokken Veri içe aktar altında Proje oluştur / aç Başlangıç’a götürür; dosya kontrolleri gösterilmez. Proje açıkken bu düğme gösterilmez. Dosya seç/bırak mevcut algılama ve worker önizlemesini başlatır. Gelişmiş yol, format, okuma ayarları, sütun türleri ve kaynak kopyası tercihini açar; kapanınca ayarlar kaybolmaz. Hatalar, sınırlı örnek kapsamı, uyarılar ve kayıt/iptal sonucu temel görünümde kalır. Tür önerileri otomatik uygulanmaz; kimlikler/uzun sayılar korunur.

`tests/test_import_gui.py::test_basic_import_project_route_advanced_settings_and_success` gerçek proje kapatma/açma, yönlendirme, ayar/tür/yeniden önizleme, bölüm kapanınca ayar koruması ve kaynak byte eşitliğiyle tam import kaydını denetler. Mevcut CSV/TSV/drop/native-format/iptal/regresyon yolları da koşulur.

[Ortam ve yedi Qt ekranı](ui-import-simple/walkthrough.json), [kontrol komutları](ui-import-simple/checks.json), [tam pytest](ui-import-simple/pytest.txt), [JUnit](ui-import-simple/pytest.xml). Görseller gerçek QQuickWindow.grabWindow çıktısıdır; fiziksel masaüstü, insan/AT kabulü değildir. Geniş başlıklar ve temel önizleme, dar önizleme gerçekten view_image ile incelendi. Önceki resmi referans incelemesi UI_REFERENCES içindedir; yeni referans uygulaması çalıştırılmadı.

İlk hedefli koşu20 başarılı/2 başarısız; testte kontrol adı düzeltildi ve F1 öncesi pencere etkinleştirildi. İkinci koşu22 başarılı/1 başarısız; testin kullanılan QPointF importu geri eklendi. Bu başarısız koşular kabul değildir. Nihai tam koşu aşağıda kaydedilir.

Belge bütünlük kapısı: birleşik kaynak metin oturum başında zaten değiştirilmişti. `check_docs.py` eski `docs/evidence/source.sha256` ile uyuşmadığını bildirir; kaynak metin ve tarihi checksum bu UI çalışmasında değiştirilmedi. Bu nedenle belge kontrolü ve ilgili unittest başarılı gösterilmez. Kaynak bütünlük kayıtlarını uzlaştırmak bu UI isteğinin kapsamına dahil edilmedi.


Nihai sonuçlar: ilk tam regresyon702 başarılı/3 başarısız (227.44s); iki UI testi yeni görünümde gizli kontrolleri doğrudan odaklamaya çalışıyordu. Boş import önizlemesinin Tab zincirine girmemesi ve Gelişmiş açıkken tür seçicisi odağının korunması test edildi. Son ilgili31 testin tamamı başarılı (32.91s), [çıktı](ui-import-simple/targeted-final.txt). Tam regresyon bu test güncellemesinden sonra tekrar edilmedi; eski başarısız çıktı/JUnit korunur. Ayrı son dört UI kontrolü4/4 başarılıdır.

[Son kapılar](ui-import-simple/final-checks.json): artefact/learning/usability/Ruff check/format başarılı; check_docs yalnız önceden değişmiş birleşik kaynak/hash uyumsuzluğu yüzünden başarısız. Kilitli unittest8/9 başarılı, aynı belge bütünlük kontrolü başarısız. SistemPython discovery59 bağımlılık import hatası ve belge kontrol hatası üretir; [çıktı](ui-import-simple/system-unittest.txt); kilitli ortamın yerine geçmez. Sistem koşusunda pytest.xml henüz yazılmadığı için geçici kırık kanıt bağlantısı da raporlandı; son belge kontrolünde bu hata yoktur.

`uv sync --locked --group dev` başarılı; uv cache yazımı sandbox dışında izin gerektirdi. Son kontroller bu kilitli ortamın `.venv/bin` yürütücülerinden çağrıldı. İlk giriş noktası denemesi izole olmayan, yazılamayan XDG yollarında exit2 verdi; geçici XDG ile kurulu giriş noktası `GUI_SMOKE PASS`, [son kayıt](ui-import-simple/entry.json). Kaynak dosya ve tarihi checksum korunmuştur. Fiziksel masaüstü ve insan testi yapılmadı; yeni faz/dağıtım kabulü verilmedi.


<a id="project-visibility-fix"></a>

2026-10-10 ENV-UI-IMPORT-SIMPLE, UIS-03 kullanıcı düzeltmesi: önceki düzenlemede proje yokken dosya kontrollerinin tamamen gizlenmesi kullanıcının istediği akışı bozuyordu. Dosya seç/bırak, Gelişmiş ve aktarım düğmesi görünür tutuldu. ImportController.choose proje açılmadan değişmez kopyadan önizleme hazırlar; mevcut salt okunur proje reddi ve proje içi dosya reddi korunur. ready halen geçerli önizleme ve yazılabilir açık proje gerektirir; proje olmadan kalıcı veri aktarılmaz. İlgili GUI testi proje olmadan gerçek CSV önizlemesini, pasif aktarım düğmesini ve sonrasında açık projeye gerçek kaydı denetler. [Test çıktısı](ui-import-simple/project-visibility-fix.txt).

Düzeltme doğrulaması:21 ilgili pytest başarılı (17.59s); Ruff check/format, learning ve artifact kapıları başarılı. Yedi yeni Qt görüntüsü üretildi; proje kapalı ekranı view_image ile gerçekten incelendi. İzole XDG kurulu giriş noktası GUI_SMOKE PASS. Belge kontrolünde önceki kaynak/hash uyumsuzluğu devam eder. Tam test taraması bu küçük düzeltmeden sonra yinelenmedi.
