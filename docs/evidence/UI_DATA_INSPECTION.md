# Veri ekranını tanıma ve öğrenme düzenlemesi

2026-10-09 UTC (2026-10-10 Europe/Istanbul); ENV-UI-DATA-INSPECTION, CachyOS Linux, kilitli CPython3.13.15/PySide6.11.2, QML offscreen/software. Açık kullanıcı UI talimatı; Faz27 durdurulmuş olarak kalır, yeni faz veya release yoktur.

UDI-01–06 REQUIREMENTS_MATRIX ana kayıtlarıdır. Başlangıç ilk kullanım düğmesi kaldırıldı; yol haritası ve hemen ardından proje alanı korunur. Veri ekranı ilk açılışta yalnız başlıklar gösterir. Bir başlık seçildiğinde kendi altında gerçek içeriği açılır. Başlangıç alt yolları işlemlere, Öğren açıklamalara gider; bu dört inceleme başlığı Öğren Veri aşamasında çevrimdışı açıklanır.

Kullanıcının beş yerel görseli gerçekten incelendi. Kaynak yolları/hashler [references.json](ui-data-inspection/references.json) içinde; dış dosyalar değiştirilmedi, görsellerdeki kullanıcı/veri hücreleri test fixture'ı olarak kullanılmadı. Amaç df.info/unique/describe ve sütun sözlüğü işlevlerini kod yazdırmadan sunmaktır; Pandas kodu GUI'de çalıştırılmaz.

Tüm sütun özeti Polars streaming taramayla tür ve dolu/null/NaN sayılarını çıkarır. Dolu null olmayan demektir; NaN ayrıca sayılır, boş metin null değildir. İlk10.000 örneği ve tam tarama açık seçimdir; snapshot byte boyutu RAM tüketimi diye sunulmaz. Describe mevcut Decimal80 sayısal profil motoru, ddof1 ve linear quantile anlamını kullanır; null/NaN/sonsuz dışarıda, kimlik/kategori özetleri bastırılır. İstatistik tablosu ve sütun tablosu sanallaştırılmış TableView'dür.

Unique kaynak değer eşitliğiyle disk üzerinde kesin hesaplanır; görüntü200 değer/sayfa ve256 karakter/metin sınırındadır. Arama görünen metne literal SQL parametresiyle uygulanır. İki farklı uzun değerin aynı kırpılmış metni olabileceği, örnekte bulunmayan değerin tüm veride yok sayılamayacağı ve nested unique'nin desteklenmediği açıktır. Sayfa değiştirmek yeniden tarama yapar; büyük veride maliyetlidir. İptal/eski sürüm mevcut worker bütçe/binding/cleanup yoluyla sonuç yayımlamaz.

Sütun notu/birim/kategori anlamları kullanıcı tarafından yazılır. Taslağa ekleme metadata sürümüdür; açık Projeyi kaydet kalıcılaştırır. Gerçek save/reopen ve kaynak byte eşitliği GUI testindedir. Bellek bütçesi/timeout/worker iptali korunur. Yeni otomatik temizlik, model fit veya hücre değişikliği yapılmaz.

Gerçek komut/tarih/exit kayıtları [checks.json](ui-data-inspection/checks.json), test çıktıları ve [walkthrough.json](ui-data-inspection/walkthrough.json) yanındaki dosyalardadır. Görseller QQuickWindow.grabWindow ile üretilir; fiziksel Wayland/X11, insan ve yardımcı teknoloji kabulü değildir.

<a id="udi-continuation"></a>

## Veri ekranı devam çalışması — 2026-10-10 Europe/Istanbul

UDI-07; ENV-UI-DATA-CONTINUATION. Sütun özeti tablosunda ok tuşlarıyla
seçilen satır, describe tablosunda seçilen hücre görünür vurgulanır. Seçim
tablo içinde görünür konuma kaydırılır; Enter/Space gerçek sütunun değer
ekranını açar. Tab tablodan çıkar; boş sonuç etkin sütun açmaz.
`tests/test_data_workspace_gui.py` gerçek QTest tuşlarıyla sütun kimliğini,
ekran geçişini, Tab çıkışını ve kaynak byte korunumunu denetler.

Önceki [checks.json](ui-data-inspection/checks.json) iki pytest hatası,
bir unittest hatası ve başarısız klavye denemesi içerir; bu sonuçlar korunur.
Belge negatif testi güncel zorunlu kabulü açık Faz28 satırına sahte
tamamlanma yazarak kontrol eder. Öğren testi değişken katalog sayısı yerine
beklenen konu kimliklerini ve uygulama konusunun sözlükten dışlanmasını
denetler. Klavye ölçümü kaldırılan giriş düğmesi yerine gerçek import
başlığını kullanır.

[Komut, tarih ve exit kayıtları](ui-data-inspection-continuation/checks.json),
[ortam](ui-data-inspection-continuation/environment.json) ve
[nihai kaynak/wheel kontrolleri](ui-data-inspection-continuation/final-package-checks.json)
ayrı dosyalardır. `measure_data_inspection.py --package-root TARGET` yüklenen
wheel yolunu doğrular ve `package_file` alanında kaydeder. Kaynak ve
noneditable wheel sekizer geniş/dar gerçek Qt ekranı üretmiştir; paket örnek
dosyalarının SHA256 değerleri değişmemiştir. Kurulu wheel giriş noktası
GUI_SMOKE PASS. [203 paket dosyası](ui-data-inspection-continuation/wheel-hashes.json)
kaynakla byte düzeyinde eşleşir. Görsel incelemede dar/%200 profil ve geniş describe
görüntüleri okundu; yatay tablo kaydırması korunur.

İlk devam taramasında Ruff import sırası hatası düzeltildi; ilk başarısız
kayıt korunur, sonraki [nihai kontroller](ui-data-inspection-continuation/final-checks.json)
lint/format/docs/learning ve31 hedefli testi başarılı kaydeder. İlk tam pytest
703 başarılı/1 başarısızdır: yeni klavye testi Qt'nin asenkron tablo yerleşimini
beklemiyordu. Test artık görünür TableView satır/sütun sayıları ile gerçek
modelin eşleşmesini bekler; keyfi uyku veya işlevi atlama kullanılmaz.
Kilitli unittest9 belge testi, beş gerçek klavye senaryosu ve giriş noktası
smoke başarılıdır. Nihai tam regresyon ayrı
[komut kaydına](ui-data-inspection-continuation/regression-final.json) yazılır.

Nihai tam pytest:704 başarılı,235.32 saniye;
[JUnit](ui-data-inspection-continuation/pytest-final.xml) ve
[çıktı](ui-data-inspection-continuation/pytest-final.txt). Son belge güncellemelerinin
docs/artifacts/learning/usability/Ruff kontrolü
[ayrı kayıttadır](ui-data-inspection-continuation/post-document-checks.json).

[Sistem Python kontrolleri](ui-data-inspection-continuation/system-checks.json)
ayrı: check_docs geçti, unittest 68 testte59 import hatasıyla başarısız
(Polars/PySide6/pytest gibi kilitli ortam bağımlılıkları sistem Python'unda
yok). Sistem Python'una paket kurulmadı. Headless QML kanıtı fiziksel
Wayland/X11, insan veya ekran okuyucu kabulü değildir. Faz27 durdurulmuş
olarak kalır; yeni faz veya dağıtım adayı başlamadı.
