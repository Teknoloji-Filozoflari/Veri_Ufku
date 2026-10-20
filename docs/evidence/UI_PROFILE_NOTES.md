# Profil altında kısa sütun açıklamaları

2026-10-10 Europe/Istanbul; ENV-UI-PROFILE-NOTES; UPT-06.
Açık kullanıcı UI talebi; yeni faz yok. Ayrı Anlam ve notlar Veri başlığı
kaldırıldı. Profil tablosunun altında yalnız sütun seçici, kısa açıklama ve
Notu kaydet bulunur. Her sütunun mevcut notu görünür; yazılan taslaklar
sütun seçimi ve worker güncellemeleri arasında yerel olarak korunur.
Açık Notu kaydet metadata sürümünü proje kaydet yoluyla kalıcılaştırır.
Readonly/busy engelleri, backend2000 karakter sınırı ve F1 yardım korunur.

applyDescription mevcut rol, birim, ordinal sıra, analiz birimi ve onay
bayrağını korur. Yeni notta fiziksel türe dayalı öneri onaylanmaz; profil
onaylanmamış rolü açık onay gibi kullanmaz. Kaynak/snapshot ve RowId aynı.
İleri rol/profile formları mevcut Veri tablosu ekranında kalır; sade
profil not alanı bunları kullanıcıya zorunlu kılmaz. Öğren sürümü43.

[41 hedefli kontrol](ui-profile-notes/targeted.txt)27.78s başarılı: gerçek
QML/save/reopen, iki sütun arasında taslak, metadata onayı/birim korunumu,
snapshot/kaynak byte eşitliği, eski role formu ve klavye akışı.
[Kapılar](ui-profile-notes/checks.json) gerçek tarih/ortam/exit kayıtlarıdır.
Qt offscreen/software kanıtı insan/fiziksel masaüstü kabulü değildir.

Geniş ve dar/%200 kısa not ekranları gerçekten incelendi:
[Qt ekran kayıtları](ui-profile-notes/screens/walkthrough.json). Betik
sade profile not alanını gerçek save yoluyla kullanır; profil zaten açıksa
tekrar tıklayıp kapatmaz. Son ordinal sıra koruma düzenlemesi sonrası
[gerçek not testi](ui-profile-notes/final-note.txt)1 başarılı (1.47s).

Tam koşuda onay bayrağı bulunmayan eski salt rol test girdisi KeyError
üretti. Gerçek kayıt sözleşmesindeki confirmed=false öneri onaylanmış
sayılmaz; eski doğrudan profil girdilerinde bayrak yoksa mevcut explicit
rol davranışı korunur. [Düzeltme sonrası26 kontrol](ui-profile-notes/roles-final.txt)
9.26s başarılı; inventory/istatistik/Qt not kalıcılığı ve metadata koruması.
Öğren altyapısının22 ek testi7.22s başarılı; tam sonuç aşağıda ayrıca yazılır.
Kapılarda artifacts/learning/usability/Ruff/format ve kurulu izole XDG
GUI_SMOKE PASS. check_docs ve unittest8/9 tarihi kaynak belge/hash
uyuşmazlığında başarısız; kaynak/checksum değiştirilmedi.

Tam regresyon ilk sürümde712 başarılı/2 başarısız,235.70s;
[JUnit](ui-profile-notes/pytest.xml), [çıktı](ui-profile-notes/pytest.txt).
Bir hata eski confirmed alanı olmayan profil girdisiydi; yukarıdaki26
son test bu düzeltmeden sonra başarılıdır. Diğeri bilinen kaynak/hash
belge hatasıdır. Düzeltmeden sonra tam714 test yeniden çalıştırılmadı;
tam koşuya başarı etiketi verilmez. [22 öğren testi](ui-profile-notes/learning-tests.txt)
ayrı başarılıdır. Son Ruff/format/learning/usability kapıları başarılı.
