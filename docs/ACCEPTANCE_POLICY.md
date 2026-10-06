# Veri_Ufku — kabul ve kanıt politikası

Faz durumu `başlanmadı`, `sürüyor`, `engelli`, `doğrulandı`; yetenek olgunluğu `mevcut değil`, `deneysel`, `kararlı`; kapsam `zorunlu`, `isteğe bağlı`, `ertelendi`. Alanlar birbirine çevrilemez. Engel/erteleme açıklaması kabul kanıtı değildir. Faz00 kararlı alanı belge/kontrol artefact'ları içindir; uygulama henüz mevcut değildir.

Ana kayıt REQUIREMENTS_MATRIX.md. PROGRESS.md/PRO_PROGRESS.md özetleri aynı faz alanlarını taşır; çelişki CI/yerel checker hatası. PHASE_PLAN.md aynı dependency tablosunu taşır. Genel test başarısı listelenmiş bütün alt yöntemlere kabul vermez. Bir format/istatistik/estimator/grafik eklendiğinde source paragrafına bağlı kalıcı alt kimlik ve GUI/hesap/yardım/save/export/dayanıklılık kanıtları açılır. Ana gereksinim metni kaybolmaz; değişiklik kimliği yeniden numaralandırılmaz.

Her kabul kaydı ID, faz, kapsam, olgunluk, doğrulama, gerçek kod/GUI/belge yolu, kanıt, ortam, çalıştırma tarihi taşır. Henüz doğrulanmayanlar `doğrulanmadı`, kanıt/env/tarih `—` olabilir. Deneme yapılmış fakat geçmemiş kayıtta sınır açık belirtilir. `doğrulandı` için mevcut artefact yolu, kalıcı kanıt dosyası/anchor, ENV kimliği ve ISO tarih şart. İlgili fazın zorunlu satırları doğrulanmadıysa faz doğrulandı olamaz; optional seçilip zorunlu hale geldiyse aynı kural geçerli. Ertelenen seçilmiş işin kararı/bağımlılık etkisi korunur.

Kanıt türleri ayrı: belge tasarım incelemesi; ortam probe; çekirdek bağımsız hesap; headless GUI; gerçek masaüstü; kullanıcı testi; gerçek Linux paket; offline çalışma; offline kurulum; optional yerel paket kurulum. Türler birbirini ikame etmez. Faz00 belge incelemesi bir fonksiyonun doğru çalıştığı kanıtı değildir. “Sorun bulunmadı” yalnız koşulan kontrol kapsamında kullanılabilir.

Ortam kaydı OS/kernel/CPU/RAM/FS/Qt/Python/bağımlılık lock hash/config/fixture hash taşır; şu an lock yoksa açık yazılır. Performans hedefleri ayrı target/actual/gap, donanım ve örnek sayısıyla; ölçülmediyse karşılandı yazılmaz. Bilimsel örnekler elle hesap, analitik çözüm veya bağımsız uygun referans; tolerans gerekçeli. Aynı üretim kütüphanesinin aynı çağrısını tekrar etmek bağımsız referans değildir.

Kritik veri kaybı veya bilimsel/sızıntı hatası dağıtım adayı kapısını kapatır. Publish/lock/source değişimi fault injection ve real two-process test ister. Migration eski sağlam kaydı korumalı. Test edilmemiş FS/platform/model formatına destek verilmez.

Faz00 bitiş kapsamı: plan, kimlik, sözleşme, referans erişim kayıtları, üç açıkça statik prototip ve kontrol planı. Resmî ekran görselleri okunabilir biçimde gelmediği için UI-REF-VIS **doğrulanmadı** kalır; kullanıcının “erişemiyorsan belirt” talimatına göre erişim sınırı Faz00 belgesinde yazılır, gerçek UI yayma kapısı Faz02 öncesindedir. Bütün referansların görsel karşılaştırması yapılmış iddiası yok. Görsel kabul kapsamı bu sınırlamayla kaldırılmamıştır.

CI workflow kaydı ile uzakta CI koşusu farklıdır. Faz00 doküman CI'ı tanımlandı; mevcut `.git` geçersiz ve remote yok, uzak koşu yok. Faz01 ilk gerçek iskelet lint/çekirdek/headless GUI CI'ı çalıştırmalıdır. Faz06/12 erken gerçek paket smoke, Faz27 temiz paket kabulü kapılarıdır. Faz00 kapsamı analitik ya da iskelet kodu içermez.
