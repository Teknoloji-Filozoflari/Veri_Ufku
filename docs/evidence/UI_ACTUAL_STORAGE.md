# Gerçek fiziksel tür saklama

2026-10-10 Europe/Istanbul; ENV-UI-ACTUAL-STORAGE; UPT-04.
Kullanıcı eski metin aktarımının yerini gerçek sayısal saklamanın almasını
istedi; projeyi kaydedip kapattığını bildirdi. Yazma kilidi serbestliği
kontrol edildi. Çalışma dizini dışındaki proje yazımı açık dosya sistemi
onayıyla uygulandı. Yeni faz yoktur.

Dönüşüm önce geçici proje kopyasında mevcut convert işlemiyle hazırlandı.
418 kayıt, RowId/SourceRecordId ve metin sütunları korundu; tüm dolu sayılar
Decimal karşılaştırmasıyla kesin doğrulandı. PassengerId/Pclass/SibSp/Parch
Int64, Age/Fare Decimal(38,6) oldu. Sayısal87 boş metin hücresi null oldu;
dolu değerlerden null üretilmedi, yuvarlama veya satır silme olmadı.

Asıl projede giriş commit eşitliği ve yazma kilidi doğrulandı; iki dönüşüm
tek save yayınıyla atomik etkinleştirildi. Eski metin sürümü aktif değildir;
geri alma geçmişi ve orijinal snapshot korunur. Önceki tam proje kopyası
geçici backup yolunda tutulur. [Uygulama kaydı](ui-actual-storage/applied.json)
ve [salt okunur yeniden açma](ui-actual-storage/reopen.json) fiziksel şema,
metadata ve tam profil uyumunu doğrular. Kullanıcı satırları kanıta alınmadı.
İlk yeniden açma kontrolü metadata text aliasını String ile ham eşitlikle
karşılaştırdığından başarısız oldu; dtype_of ile kapalı tür gramerinde
normalleştirilen gerçek kontrol geçti. Veri yayını başarılıydı.

Profil artık yalnız gerçek physical_type bildirir; içerik algılamasıyla
String üstüne Int64 etiketi yazılmaz. Türler tablo ve özet içinde teknik
adlarıyla gösterilir. UPT-02/03 önceki gösterim kararı bu taleple aşılmıştır.
Öğren sürümü41 günceldir. [66 hedefli test](ui-actual-storage/targeted.txt)
19.37s başarılı; aktarım, exact Int64/Decimal, legacy String fiziksel
raporlama ve Qt profil testleri. Tam regresyon bu düzeltmeden sonra
tekrarlanmadı; önceki711/1 tarihsel sonuç UI_PROFILE_TYPES içindedir.

[Kapılar](ui-actual-storage/checks.json) gerçek komut, ortam, tarih ve exit
içerir. Fiziksel masaüstü/insan kabulü değildir; kaynak belge/hash problemi
ayrıdır, kullanıcı kaynağı/checksum değiştirilmedi.
