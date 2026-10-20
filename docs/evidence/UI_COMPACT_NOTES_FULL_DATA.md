# Kapalı gelişmiş aktarım, kompakt notlar ve tam veri

2026-10-10 Europe/Istanbul; ENV-UI-COMPACT-NOTES-FULL-DATA;
UPT-07/08/09 matriste. Açık kullanıcı UI talepleri; yeni faz yok.

Import ayrıntıları genel beginner/advanced tercihiyle otomatik açılmaz.
İlk açılışta ve gerçek bölüm navigasyonuyla yeniden girişte kapalıdır;
Gelişmiş düğmesiyle kullanıcı açar. Ayarlar kapatmayla sıfırlanmaz.

Kaydedilen notlar profil tablosuyla not girişinin arasında yalnız dolu
sütunlar için ad ve açıklama olarak gösterilir. Gerçek schema sırası,
plain text, uzun ad/not sarma ve220px içinde dikey kaydırma korunur.
Not düzenleme/save/reopen ve kullanıcı snapshot kaynak koruması aynı.

Verini tanı alanının örnek ilk10.000 seçicileri kaldırıldı. Inventory,
özet istatistik, farklı değer ve sütun profil çağrıları sample=false.
Unique sayfalama200, satır görüntüleme200 ve import preview20 ayrı
sunum sınırlarıdır; tam hesabı örnek yapmaz. Tablo görünümü/dataset
profil hedefi filtre sözleşmesi olarak kalır. Backend sample API ve başka
analiz ekranlarının bilimsel kapsam seçenekleri korunur. Öğren sürümü44.

İlk [hedefli sonuç](ui-compact-notes-full-data/first-targeted.txt)30 başarılı/
2 başarısız: delegate QObject ağacı yerine görsel ağacından okunmalıydı;
import yeniden giriş testi gerçek bölüm navigasyonunu kullanmıyordu.
Testler gerçek visual_item ve heading tıklamasıyla düzeltildi; test
kontrolleri kaldırılmadı. Son kontroller aşağıda kayıtlıdır.
[Komut/tarih/ortam/exit](ui-compact-notes-full-data/checks.json).
Qt offscreen/software geliştirici doğrulaması kullanıcı masaüstü kabulü değildir.

Son [32 ilgili GUI testi](ui-compact-notes-full-data/targeted.txt)31.93s
başarılı. Eski notların gerçek save/reopen sonrası iki sütun adıyla listede
bulunması ve veri kaynağı eşitliği; global advanced tercihi olsa bile kapalı
import ve gerçek giriş/çıkışta kapanma; kaldırılan kapsamların yokluğu
kontrol edildi. [Sekiz Qt görüntüsü](ui-compact-notes-full-data/screens/walkthrough.json)
üretildi; geniş kompakt liste/not alanı gerçekten incelendi.

Artifacts/learning/usability/Ruff check/format ve izole kurulu giriş
noktası GUI_SMOKE PASS. Check_docs ve unittest8/9 bilinen kaynak/hash
uyuşmazlığında başarısız; kaynak/checksum değiştirilmedi. Tam regresyon
bu UI düzenlemesinden sonra tekrarlanmadı; önceki sonuçlar korunur.
