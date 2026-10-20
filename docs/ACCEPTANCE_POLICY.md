# Veri_Ufku — kabul ve kanıt politikası

Faz durumu `başlanmadı`, `sürüyor`, `engelli`, `doğrulandı`; yetenek olgunluğu `mevcut değil`, `deneysel`, `kararlı`; kapsam `zorunlu`, `isteğe bağlı`, `ertelendi`. Alanlar birbirine çevrilemez. Engel/erteleme açıklaması kabul kanıtı değildir. Faz00 kararlı alanı yalnız belge/kontrol artefact'ları içindir; uygulamanın güncel olgunluğu sonraki faz kayıtlarında ayrı belirtilir.

Ana kayıt REQUIREMENTS_MATRIX.md. PROGRESS.md/PRO_PROGRESS.md özetleri aynı faz alanlarını taşır; çelişki CI/yerel checker hatası. PHASE_PLAN.md aynı dependency tablosunu taşır. Genel test başarısı listelenmiş bütün alt yöntemlere kabul vermez. Bir format/istatistik/estimator/grafik eklendiğinde source paragrafına bağlı kalıcı alt kimlik ve GUI/hesap/yardım/save/export/dayanıklılık kanıtları açılır. Ana gereksinim metni kaybolmaz; değişiklik kimliği yeniden numaralandırılmaz.

Her kabul kaydı ID, faz, kapsam, olgunluk, doğrulama, gerçek kod/GUI/belge yolu, kanıt, ortam, çalıştırma tarihi taşır. Henüz doğrulanmayanlar `doğrulanmadı`, kanıt/env/tarih `—` olabilir. Deneme yapılmış fakat geçmemiş kayıtta sınır açık belirtilir. `doğrulandı` için mevcut artefact yolu, kalıcı kanıt dosyası/anchor, ENV kimliği ve ISO tarih şart. İlgili fazın zorunlu satırları doğrulanmadıysa faz doğrulandı olamaz; optional seçilip zorunlu hale geldiyse aynı kural geçerli. Ertelenen seçilmiş işin kararı/bağımlılık etkisi korunur.

Kanıt türleri ayrı: belge tasarım incelemesi; ortam probe; çekirdek bağımsız hesap; headless GUI; gerçek masaüstü; kullanıcı testi; gerçek Linux paket; offline çalışma; offline kurulum; optional yerel paket kurulum. Türler birbirini ikame etmez. Faz00 belge incelemesi bir fonksiyonun doğru çalıştığı kanıtı değildir. “Sorun bulunmadı” yalnız koşulan kontrol kapsamında kullanılabilir.

Ortam kaydı OS/kernel/CPU/RAM/FS/Qt/Python/bağımlılık lock hash/config/fixture hash taşır; şu an lock yoksa açık yazılır. Performans hedefleri ayrı target/actual/gap, donanım ve örnek sayısıyla; ölçülmediyse karşılandı yazılmaz. Bilimsel örnekler elle hesap, analitik çözüm veya bağımsız uygun referans; tolerans gerekçeli. Aynı üretim kütüphanesinin aynı çağrısını tekrar etmek bağımsız referans değildir.

Kritik veri kaybı veya bilimsel/sızıntı hatası dağıtım adayı kapısını kapatır. Publish/lock/source değişimi fault injection ve real two-process test ister. Migration eski sağlam kaydı korumalı. Test edilmemiş FS/platform/model formatına destek verilmez.

Faz00 bitiş kapsamı: plan, kimlik, sözleşme, referans erişim kayıtları, üç açıkça statik prototip ve kontrol planı. Resmî ekran görselleri okunabilir biçimde gelmediği için UI-REF-VIS **doğrulanmadı** kalır; kullanıcının “erişemiyorsan belirt” talimatına göre erişim sınırı Faz00 belgesinde yazılır, gerçek UI yayma kapısı Faz02 öncesindedir. Bütün referansların görsel karşılaştırması yapılmış iddiası yok. Görsel kabul kapsamı bu sınırlamayla kaldırılmamıştır.

CI workflow kaydı ile uzakta CI koşusu farklıdır. Faz00 incelemesi sırasında `.git` geçersizdi ve uzak koşu yoktu; sonraki fazların uzak başarıları matriste ayrı kanıtlarla kayıtlıdır. Yeni yerel tarama uzak CI başarısı sayılmaz. Faz06/12 erken gerçek paket smoke, Faz27 temiz paket kabulü kapılarıdır. Faz00 kapsamı analitik ya da iskelet kodu içermez.

2026-10-08 Europe/Istanbul kullanıcı talimatı: Faz00–13 teknik taramasında gerçek kullanıcı testleri atlanır, taramadan sonra yapılır. Bu talimat mevcut kullanıcı kanıtlarını silmez ve F13-S005'i doğrulanmış yapmaz. Teknik yeniden doğrulama [AUDIT_00_13](evidence/AUDIT_00_13.md) kaydında, kullanıcı görevi ayrı bekler.


Faz14 açık kullanıcı talimatıyla uygulanır. F14 teknik gereksinimlerinin doğrulanması, Faz13 F13-S005 insan kullanıcı testinin tamamlanması anlamına gelmez. Faz14 bağımlılık kapısı bu kabul açık olduğu sürece sürüyor kalır; matris teknik kabulü ve faz durumunu ayrı kaydeder. Deneysel olgunluk korunur. [Gerçek kayıt](evidence/PHASE14.md).

Faz15 teknik hazırlık raporu ve data-only plan doğrulaması gerçek estimator fit/evaluate/predict kabulü değildir. Dört amaç hazırlama niyetidir; öğrenilmiş parametre üretilmez. F13-S005 açık olduğundan faz sürüyor/deneysel; sonraki faz yetkisi verilmez. [Kanıt](evidence/PHASE15.md).

## Faz16

Faz16 teknik baseline fit/evaluate yalnız basit karşılaştırma ve protokol altyapısıdır; Faz17/18 estimator veya Faz20 güvenli eğitilmiş model kabulü değildir. F13-S005/F15 bağımlılık kabulü açık olduğu için faz sürüyor; kullanıcı açık Faz16 yetkisi teknik uygulamayı kapsar. [Kanıt](evidence/PHASE16.md).


## Faz18 kategori tahmini

F18-S001..007 teknik kanıtı ikili/çok sınıflı gerçek estimator çalışması, bağımsız elle matris/F1/ROC/PR referansı, train-only fit spy, validation eşiği, eksik sınıf/proba ve sıfır bölme, maliyet reddi, yanlış karar tamper, QML/spawn/iptal/defter tekrar/retune/reopen ve noneditable Linux wheel içerir.502 pytest ve9 kilitli unittest geçti. Sistem Python eksik bağımlılık keşfi ayrı başarısız kayıt; başarılı kilitli ortamın yerine geçirilmez. İnsan masaüstü, bilgisiz kullanıcı, yeni uzak CI veya minimum donanım kabulü yapılmadı; faz sürüyor/yetenek deneysel. Saha güvenliği veya proje dışı test bağımsızlığı garantisi kabul iddiası değildir. [ADR-021](adr/021-classification-phase18.md), [gerçek teknik kayıt](evidence/PHASE18.md).


## Faz23

F23 teknik kabul, önceki insan/bağımlılık kabulünü tamamlamaz. Declarative analiz tarifi eğitim pipeline paketinden ayrıdır; dağılım özeti model başarısızlığı kanıtı değildir. Yeni hedef performansı keşifseldir ve final testin yerine geçmez. [ADR-026](adr/026-recipes-monitoring-phase23.md), [kanıt](evidence/PHASE23.md).


## Faz24

ENV-24 geliştirici4 logical CPU/32GiB koşuludur, fiziksel minimum donanım kabulü değildir. Ölçüm/target/gap ve scope ayrı; F24-S006 cold OS/minimum/physical latency ölçülmediği için doğrulanmadı. Önceki insan kapısı korunur. [ADR-027](adr/027-performance-phase24.md), [kanıt](evidence/PHASE24.md).

Faz26 teknik incelemesi, önceki insan/AT/bağımlılık kabulünü veya Faz27 dağıtım
adayını tamamlamaz. JUnit yöntem/nokta eşlemesi, bağımsız referans incelemesi,
Linux ağ namespace deneyi ve kaynak/kurulu wheel yolları ayrı kanıtlardır.
SIGKILL/ENOSPC injection fiziksel güç kesintisi değildir; bozuk ACTIVE kör
kurtarılmaz, eski kayıt korunur. [Gerçek kayıt](evidence/PHASE26.md).


Faz28 denetim teslimi profesyonel giriş kapısını atlamaz. F00–20 ve24–27 bütün zorunlu kabul kapanmadan F28 doğrulandı olamaz. Kapsam kararı DEC-28-01/02, kaynak revizyonu DEC-28-03 ve ek bilimsel bağımlılık DEC-28-04 [kanıtta](evidence/PHASE28.md) kayıtlıdır; önceki source.sha256 ve kaynak metni korunur.

## Faz75 seçilmiş sürüm kapısı

DEC75-01: yalnız değerlendirme öncesi açık seçilen kapsamın **bütün zorunlu**
gereksinimleri kanıtlanırsa sürüm/faz doğrulandı olabilir. Birkaç modelin fixture'ı,
modül test adı, registry supported beyanı, hash eşleşmesi veya AI review'u bu kararın
yerini tutmaz. Fail/timeout/skip/unavailable ve çalıştırılmayan kabul başarılı değildir.
Engelli/ertelenmiş işler açık kalır. Kapsamı başarısız testten sonra daraltıp eski
başarısızlığı gizleyerek release onaylanmaz. Yeni bounded alt deneme ayrı etiketlenir.

Bilimsel/veri kaybı hatası bulunmadı ifadesi yalnız belirtilen test kapsamı ve ortamı
kapsar. Bağımsız expert learning review, gerçek novice/expert/AT/physical/minHW ve
uyumluluk kabulü teknik smoke'tan ayrıdır. Gereksinim, ilerleme ve capability audit'i
aynı durumları göstermek zorundadır; [sürüm kapsamı](RELEASE_SCOPE_0_1.md),
[açık kapılar](evidence/PHASE75.md). `scripts/audit_phase75.py` gate'i eksik zorunlu,
failed check veya eksik independent review'da false döner. Resmî kaynak ana matrisi
önceki gerçek kabulleri saklar; bu aşamada yeniden koşulmuş gibi raporlamaz.
