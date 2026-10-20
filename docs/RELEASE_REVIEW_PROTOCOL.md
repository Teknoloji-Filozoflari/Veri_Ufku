# Veri_Ufku — insan ve uzman kabul protokolü

Bu dosya hazır protokoldür; gerçekleştirilmiş kullanıcı/uzman çalışması değildir.
Katılımcı kişisel bilgileri paylaşım paketine gömülmez. Gerçek reviewer kimliği
kurumun onaylı yerel kayıt sisteminde tutulur; bu repo boş alanları doldurup onay
uydurmaz. Eğitim başarısı meslek sertifikası olarak sunulmaz.

Yeni başlayan ve uzman ayrı çalışmalardır. Her kişi için sürüm/artifact hash,
OS/donanım/input device/ekran ve accessibility tooling, görev/veri hash'i, bağımsız
beklenen sonuç, yardım düzeyi, tamamlanma/yanlış yorum/süre ve kritik hata kaydı
alınır. Öğren ekranını okumadan araca gidebilme ve F1/Escape dönüşü sınanır.
Sentetik ayrı workspace kullanılır; kişisel projeyi değiştirmez.

Yeni başlayan görevleri: yerel CSV aç, veri sözlüğünü oku, null/NaN ayrımını açıkla,
önizlemeli cleaning/undo yap, grafik n/payda/CI anlamını yorumla ve maskeli rapor
export et. Uzman görevleri: grup+zaman split/holdout geçmişini doğrula, typed weight
ve MI varsayımını seç, calibration ile discrimination farkını açıkla, belirsizlik/
causal assumptions ve unsupported backend sınırını rapora taşı, bundle re-run farkını
incele. Otomatik Qt emit/screenshot bu görevleri bir insanın yapmasının yerine geçmez.

Bağımsız alan uzmanı her article/lesson için
`docs/evidence/phase75/expert-review-worksheet.csv` satırında content SHA256,
kaynak/sürüm, denklemler/numeric reference/tolerans, varsayım/yanlış yorum, birim/
ölçüm düzeyi ve gerçek GUI correspondence kontrol eder. Karar: pending / needs-changes /
approved-with-scope / rejected. Reviewer, tarih, gerekçe ve referans kanıt olmadan
approved olmaz. İçerik değişirse eski karar eski hash bağlamında kalır; yeni hash
pending'dir. Otomatik doğru JSON/bağ denetimi bilimsel uzman review'u değildir.

Erişilebilirlik: klavye-only focus/order/escape, en az iki yazı ölçeği/dar ekran,
kontrast, screen reader/AT duyuruları ve insan görev çıktısı ayrı kaydedilir.
Offscreen named-field taraması AT oturumunun yerini tutmaz. Fiziksel Wayland/X11,
minimum donanım ve temiz OS offline kurulum kendi ortam kimliğiyle değerlendirilir.

Kabul kararı bütün zorunlu kapılar ve açık issue listesi üzerinden verilir. P0
bilimsel yanlış sonuç/veri kaybı teslimi durdurur; P1 kaynak/işlev/kabul kapısı engeli
kapanmadan production-onay yok; P2 sınırlama/uyumluluk, P3 açıklama/polish kayıtlıdır.
İşin engelli/ertelenmiş olması kapanış değildir; tek test tekrarı bütün sorunların
kök nedenini kapatmaz. [Kapsam ve gerçek sonuçlar](evidence/PHASE75.md).
