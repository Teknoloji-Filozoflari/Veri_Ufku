# Veri_Ufku — hedef donanım, sınıflar ve ölçüm planı

2026-10-06; bütçeler **hedef**, henüz karşılandığı ölçülmedi. Yerel probe ortamı [ENVIRONMENT](ENVIRONMENT.md); minimum hedef üzerinde gerçek ölçüm ayrıca şart.

## Hedef

Birincil Linux x86_64 CPU-only, 4 fiziksel core, 8 GiB RAM, SSD en az 10 GiB boş, 1366×768; Wayland ve X11. Debian/Pardus ve Arch/CachyOS aileleri hedef; exact desteklenen sürümler temiz ortam testleriyle belirlenir. AVX2 olmayan makineler rtcompat ve ayrı doğrulama gerektirir. ARM/GPU desteği vaat edilmez. Geliştirici 32GB Ryzen ölçümü 8GB hedefin karşılandığı anlamına gelmez.

| Sınıf | Boyut üst sınırı / referans | Plan |
|---|---|---|
| Küçük | ≤10 MiB ve ≤10k kayıt, ≤50 kolon | Tam profil/özet, ilk snapshot ve tablo sayfası |
| Orta | ≤250 MiB ve ≤1M kayıt, ≤100 kolon | Lazy scan, chunk import, bounded page cache; ağır grafik örneklemi açık |
| Büyük | ≤2 GiB ve ≤10M kayıt, ≤200 kolon | Preview sınırlı; disk/spill ve maliyet önkontrolü; tam hesap yöntem bazlı, dense ML genel garanti yok |
| Sınır dışı | Bu üst sınırların herhangi biri aşılmış | Unsupported/deneysel sınır ve maliyet açıklaması; otomatik tam belleğe load yok |

Satır boyutu/text cardinality/nested veriler boyut sınıfını ağırlaştırır. Dosya bytes tek başına RAM garantisi değil. İlk kullanılabilir sürüm küçük/orta yolların işlevsel doğruluğu, büyükte güvenli önizleme ve açık ret şart; büyükte tüm işlemlerin hız iddiası Faz 24 ölçümlerine bağlı. Bu güvenli ret ağır zorunlu yöntemi erteleme kabulü değildir; ilgili yöntem hâlâ doğrulanmadı.

## Bütçeler ve yöntem

| Metrik | Minimum donanım hedefi | Ölçüm / kabul fazı |
|---|---|---|
| Açılış | warm p95≤2 s, cold≤5 s | launch monotonic→ilk frame+etkin ana eylem; 20 warm/5 cold, cache politikası kayıtlı; Faz01/02 |
| Önizleme | küçük p95≤1 s; orta/büyük sınırlı ilk 200 kayıt≤3 s | file seçimi→rendered sayfa, parser ve snapshot yakalama süresi ayrıca tam süreyle gösterilir; uzun snapshot aşaması responsive/iptal; Faz05/06 |
| UI yanıtı | input→frame p95≤100 ms, max≤250 ms | import/CPU işinde 100 input olayı, frame timestamp ve Qt event-loop lag; Faz01/07/12 |
| İptal | UI feedback≤100 ms; iş durması p95≤2 s; cleanup≤5 s | cancel request→ack→worker exit→staging temizliği, uninterruptible I/O ayrı sınır; Faz01/09/24 |
| RAM | idle≤300 MiB; uygulama+workers toplam peak≤2 GiB | /proc RSS/PSS veya cgroup, 100ms örnek; mmap/shared çifte sayım politikasını kaydet; dataset sayfası cache≤64 MiB/3 sayfa; Faz01/07/24 |
| Geçici disk | varsayılan≤4 GiB, reserve max(1 GiB,%10 beklenen çıktı) | staging/spill toplamını 250ms ölç; ENOSPC injection. Büyük işlem sığmıyorsa bütçe onayı veya ret; Faz04/24 |
| Tablo sayfası | 200 satır, 3 sayfa cache, görünür sütunları yükle | initial/query page ve scroll p95; sırf görüntüleme tam load yok; Faz07 |

Snapshot yakalama için “büyük 2GiB dosyanın hash/kopyası≤3s” iddiası yok; toplam snapshot süresi ayrı metrik. UI önizleme ilk aşama örneği açık sınırlıdır, sabit kaynak garanti edilmeden import başarılı değildir. Bütçeye sığmayan işlem sonucu publish edilmez; OOM güvenli başarısızlık + son sağlam commit testi gerekir.

Benchmark fixture'ları sabit seed/digest, UTF8 Türkçe, yüksek cardinality, null/NaN/inf, uzun text, decimal/tz ve duplicate içerik içerir. Her raporda OS/CPU/RAM/FS/Qt/Python/lock hash, artifact hash, yöntem/filter/scope, cache state, örnek sayısı, median/p95/max, peak memory/temp disk, hata ve target/actual/gap sütunları. Full/sample ayrıdır. Başlangıç baseline Faz 01 boş kabuk, Faz 05 ilk gerçek import, Faz 12 export/worker; Faz 24 tekrar hedef donanım. Şu an ölçüm tablosu yok; hedef başarılı değildir.

## ENV-01 ilk altyapı ölçümü

[Ham JSON](evidence/phase01-measurements.json), `scripts/measure_phase01.py`, 2026-10-06. Offscreen/software geliştirici donanımı; analitik veri veya minimum donanım testi değildir.

| Ölçüm | Gözlem | Sınır |
|---|---|---|
| Sıcak ilk frame, 20 yeni süreç | p95 117.54ms | OS cache sıcak; cold ölçülmedi |
| 100 Qt fare olayı ve grabWindow | p95 0.523ms | Başsız software render, fiziksel frame latency değil |
| Boş GUI peak RSS | 97,677,312 byte | Bu ortam |
| Parent+CPU örneklenmiş RSS | 140,038,144 byte | Ortak sayfa mükerrer olabilir |
| Yönetilen geçici alan örneklenmiş peak | 815,104 byte | Tüm sistem diski değil |
| Eşzamanlı görev | 1 CPU / 2 I/O | Gerçek manager örneklemesi |
| Tek iptal/worker exit+cleanup | 18.08ms | n=1; p95 iddiası yok |
| İptal geri bildirimi | 0.252ms | Başsız tek ölçüm |
| Artakalan görev dizini | 0 | Ölçüm sonu |

Önizleme/import henüz yok ve ölçülmedi. Gerçek desktop, soğuk açılış, minimum donanım ve büyük veri kabul bütçeleri açık kalır.
