# ADR-029 — Faz26 veri bütünlüğü ve güvenilirlik incelemesi

2026-10-09 UTC / 2026-10-10 Europe/Istanbul. Python/PySide6/QML ve ACTIVE
yayınlama protokolü korunur. Kullanıcı açık Faz26 yetkisi; Faz27 başlatılmaz.

Manifest okuyucusu desteklenen0–7 şemalarını aynı listeyle kabul eder.
Şema0 salt okunur/Farklı kaydet;1–6 açık Kaydet ile yeni commit7 üretir.
Eski manifest, SQLite payload ve veri artefact'ları korunur. Kaynak üzerinde
kayıplı migration yapılmaz; geçmiş temizleme eklenmez.

SQLite metadata ve yardımcı dosyaları tek bağlantılı normal dosya olmalıdır;
symlink ve dış dosyaya hardlink ile yazma reddedilir. Proje içi salt okunur
artefact'ların yayın sırasında kullanılan hardlink protokolü korunur.
Log açılışında O_NOFOLLOW, normal-file/nlink kontrolü ve0600 vardır;
log dosyasının izlenerek başka dosyanın içerik/izinlerini değiştirmesi önlenir.

ODS kodlanmış XML'de UTF-16/32 DTD/entity denetimi XLSX ile aynı null-byte
normalizasyonunu kullanır. Archive yol/tekrar/symlink/şifre ve açılmış boyut
sınırları; küçük sabit mimetype boyutu ve gerçek ComputeBudget korunur.
Kaynak doğrulaması inspect'te görevin bütçesini taşır. Belge parser'ı64MiB
content XML sınırında tam belge belleği kullanır; streaming XML iddiası yoktur.

Kurtarma önce I/O worker'da doğrulanır ve ad/zaman/veri/işlem/sonuç sayısı
gösterilir. Onaylanan commit kimliği restore'a taşınır; sonraki autosave aynı
önizleme diye sessiz yüklenmez. Hata/bozuk/farklı-parent durumda taslak ve
ACTIVE korunur. Restore yalnız taslağı değiştirir; açık Kaydet gerekir.
Yeni açıklama mevcut project.recovery yardımına eklenir; genel yeni ekran yok.

14 ortak yayın sınırı manuel kayıt/import ve ayrıca autosave için gerçek
SIGKILL ile denetlenir. Kaynak/Parquet/chunk/lineage ek noktaları da test
kimliğine bağlanır. ENOSPC fault injection bütün ortak sınırları denetler;
pointer değişiminden sonra yeni tam commit görünür olabilir, kör rollback yok.
Bu kontrollü ENOSPC, fiziksel diski doldurma veya güç kesintisi deneyi değildir.

Gerçek offline deneme Linux user+network namespace içinde loopback dışında
arayüz ve route olmadan yapılır; IPv4/IPv6 native bağlantı retleri ve spawn
namespace kalıtımı kaydedilir. Host ağını kapatmaz; native kütüphaneler de
bu namespace'te dış ağa erişemez. Temiz makine/offline kurulum iddiası yoktur.

[Bağımsız referanslar](../GOLDEN_REFERENCES.md), [gerçek kanıt](../evidence/PHASE26.md).

GUI shell poll timer’ı engine parent’ına bağlıdır; cleanup dispose ile
zamanlayıcıyı durdurur. Eski shell callback’i yeni shell’in olay döngüsünde
çalışmaz. Qt timer dağıtımı çökmesi için tam regresyon ve kapanış testi gerekir;
yalnız odaklı başarı çökme kabulünü tamamlamaz.
