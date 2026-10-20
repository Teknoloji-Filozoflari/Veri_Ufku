# Profil türlerine ait sütun adları

2026-10-10 Europe/Istanbul; ENV-UI-PROFILE-TYPE-COLUMNS; UPT-05.
Açık kullanıcı UI talebi; yeni faz yok. Kullanıcının df.info ekranı ve alt
sütun gruplarını içeren data_info.png görseli incelendi; [referans hash/yol](ui-profile-type-columns/reference.json).
Üst özet artık her gerçek fiziksel tür için ayrı satırda tür/sayı ve tüm
ilgili sütun adlarını gösterir. Örnek: Int64:4 — PassengerId, Pclass…
Gerçek adlar tablo sırasıyla listelenir; değiştirilmez, uzun adlar sarılır.
Plain text ile başlıklardaki markup yorumlanmaz. Sütun sayısı, disk boyutu
ve alttaki beş sütunlu tablo korunur. Veri/proje dosyası değişmez.
Öğren içerik sürümü42. [Kontroller](ui-profile-type-columns/checks.json).
Headless Qt geliştirici doğrulaması insan/fiziksel masaüstü kabulü değildir.

Nihai gerçek sonuç:6 GUI testi başarılı (7.22s), sütun isimlerinin fiziksel
tür gruplarıyla eşleşmesi ve kaynak byte koruması kontrol edildi.
Artifacts/learning/usability/Ruff check/format başarılı; check_docs daha
önceki kaynak belge/hash uyuşmazlığı nedeniyle başarısız. Hash/source
bu çalışmada değiştirilmedi. Tam regresyon veya fiziksel kullanıcı testi
tekrarlanmadı. [Sekiz Qt ekranı](ui-profile-type-columns/screens/walkthrough.json)
üretildi; geniş profil ekranı gerçekten incelendi. Tür/sayı/ad listeleri
ayrı satırlarda görünür; alttaki gerçek fiziksel tür tablosu korunur.
