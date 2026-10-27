# Veri profili, tür algılama ve değer görünümü

2026-10-10 Europe/Istanbul, ENV-UI-DATA-REFINEMENT. Açık kullanıcı isteği; UDR-01..04 matriste. Yeni faz, veri migrasyonu veya dağıtım kabulü yoktur. Mevcut Python/PySide6/QML ve worker/snapshot/provenance/yayın protokolü korunur.

Görev açıklama düğmesi kaldırıldı; aktif görev iptal kontrolü F1 bağını korur. PreviewModel bütün adaptörlerde ilk20 kaydı gösterir; worker200 önkontrol penceresi ve tam import ayrı kalır.30 kaynak kaydı/20 görünür kayıt testi gerçek Parquet importunda30 kaydı ve doğru türleri doğrular.

CSV/TSV tüm-metin davranışının nedeni eski varsayılandı. Yeni GUI seçimi infer_types=true ile infer_settings'i worker içinde çağırır; bütün dosyada tür adayları bounded sütun durumuyla daraltılır.205 sayısal kayıt sonrası gelen karma metin, baştaki sıfırlar ve uzun numaralar korunur. Int64/Decimal(38,6)/mevcut biçimde tarih/boolean algılanır; taşan/karma içerik metin kalır. Boş hücre yalnız otomatik metin dışı sütunda null, metin sütununda boş metindir; ayar kaydedilir. Kullanıcı tür seçimi önceliklidir. Eski dataset otomatik değiştirilmez; yeni davranış için yeniden import gerekir. Kullanıcının aktardığı dosyanın kendisi bu oturumda paylaşılmadığı için o dosyanın içerik düzeyinde incelemesi yapılmış sayılmaz.

Veri profili açılırken tüm inventory hesaplanır;10005 kayıtlık test son kayda kadar tam kapsamı doğrular. Sadece iki tablo sütunu (başlık/tür) gösterilir; üstte sütun sayısı/tür özeti/sıkıştırılmış çalışma kopyasının disk boyutu vardır. İş yükü ve iptal mevcut bütçeye bağlıdır.100ms ekran kararlılığı beklenir; profil kapanınca başlamış otomatik tarama iptal edilir. Özet istatistik/değer tarama kapsam seçenekleri ayrı mevcut hesaplar olarak korunur.

Değer listesinde Değer/Tekrar sayısı başlığı, alternating yüzey/hover/ayırıcı, sayı rozetleri ve boş durum vardır.200 değer sayfası, literal arama, metin kırpma ve tüm/sample kapsam semantiği değişmedi.

[İlk hedefli test](ui-data-refinement/targeted.txt):73 başarılı/2 başarısız; klavye testi eski metin başlangıç türünü varsayıyordu; otomatik tarama hızlı notes geçişini bloke ediyordu. Beklenen tür indeksi seçili başlangıca bağlandı; otomatik tarama100ms ekran kararlılığı ve görünürlük/iptal ile düzenlendi. [Son ilgili test](ui-data-refinement/targeted-fix.txt):26 başarılı (24.00s).

[Veri ekranları/ortam](ui-data-refinement/screens/walkthrough.json), [import ekranları/20 kayıt kanıtı](ui-data-refinement/import-screens/walkthrough.json); gerçek QQuickWindow.grabWindow, sentetik/CC0 fixture, kaynak hash koruması. Fiziksel masaüstü veya insan/AT kabulü değildir. Geniş profil ve değer listesi gerçekten görüntülendi. [Tam regresyon çıktısı](ui-data-refinement/pytest.txt); nihai sonuçlar tamamlanınca aşağıda kaydedilir.


Nihai tam pytest:708 başarılı/1 başarısız (230.34s), [JUnit](ui-data-refinement/pytest.xml). Tek başarısızlık önceden değiştirilmiş birleşik kaynak metnin tarihi checksum ile uyuşmamasıdır; UI/import/analitik testleri geçti. Son sade etiket/tek-dataset seçicisi/öğren metni düzenlemelerinden sonra [28 ilgili GUI regresyonu](ui-data-refinement/ui-last.txt) başarılı (28.63s). Tam tarama bu son sunum/metin düzenlemelerinden sonra tekrar edilmedi.

[Son kapılar](ui-data-refinement/checks.json): artifact/learning/usability/Ruff check/format başarılı; kilitli unittest8/9, belge kapısı kaynak/hash uyuşmazlığında başarısız. İzole XDG kurulu giriş noktası GUI_SMOKE PASS. Kaynak birleşik prompt ve eski checksum bu çalışmada değiştirilmedi; başka faz başlatılmadı. Kilitli dev ortamı aynı oturumdaki başarılı uv sync sonucundan korunur; kontroller `.venv/bin` yürütücülerindedir. [Ortam](ui-data-refinement/environment.json).

Son geniş profil görüntüsünde yalnız sütun sayısı/tür özeti/disk boyutu ve başlık/tür tablosu incelendi. Tek dataset varsa profil seçicisi gizlidir; birden fazla dataset varsa seçim korunur. Tür etiketleri Metin/Tam sayı/Ondalıklı sayı/Tarih/Doğru-yanlış olarak sade gösterilir; tooltip gerçek fiziksel türü verir. Dar/%200 görünümde yatay tablo kaydırması gerekir; fiziksel HiDPI/AT kabulü değildir.
