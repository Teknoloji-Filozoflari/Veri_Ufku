# Veri_Ufku — hedef donanım, sınıflar ve ölçüm planı

2026-10-09; bütçeler **hedef**. ENV-24 yerel ölçümleri aşağıda; minimum donanım kabulü açık. Yerel probe ortamı [ENVIRONMENT](ENVIRONMENT.md); minimum hedef üzerinde gerçek ölçüm ayrıca şart.

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

Benchmark fixture'ları sabit seed/digest, UTF8 Türkçe, yüksek cardinality, null/NaN/inf, uzun text, decimal/tz ve duplicate içerik içerir. Her raporda OS/CPU/RAM/FS/Qt/Python/lock hash, artifact hash, yöntem/filter/scope, cache state, örnek sayısı, median/p95/max, peak memory/temp disk, hata ve target/actual/gap sütunları. Full/sample ayrıdır. Başlangıç baseline Faz 01 boş kabuk, Faz 05 ilk gerçek import, Faz 12 export/worker; Faz 24 tekrar hedef donanım. Faz24 ENV-24 ölçüm tablosu aşağıda; minimum donanım hedefinin karşılandığı söylenmez.

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

## ENV-05 ilk gerçek import ölçümü

[Ham JSON](evidence/phase05-headless.json), scripts/measure_phase05.py, 2026-10-06; NVMe Btrfs, offscreen/software, geliştirici donanımı, sıcak cache ve n=1. Küçük fixture yakalama+200 sınırına kadar önizleme 219.67ms; 180000 kayıt/2340006 byte CSV tam import/yayın 1896.61ms. İptal feedback 0.49ms, süreç çıkışı 40.61ms; normal shutdown artakalan private worker dizini0. Örneklenmiş parent+worker RSS peak 527642624 byte (shared sayfa iki kez sayılabilir); worker alanı disk peak 18780098 byte (proje staging dahil değildir). Yaklaşık10ms örneklerde Qt tick max gap 49.96ms; fiziksel input→frame latency veya100 olay p95 değildir. Snapshot/GUI kaynak SHA256 korundu. Minimum8GB/soğuk cache/1GiB veri/remote/native masaüstü bütçe kabulü açık; n=1 gözlem genel hız garantisi değildir.

Faz06: JSON belge64MiB tam parse, XLSX XML parça64MiB/toplam256MiB bounded tam parse; streaming desteği bu ikisinde kapalı. JSONL tam şema profili+chunk ikinci okuma; Parquet native lazy sink. n=1 sıcak geliştirici örneklerinin RSS/disk/UI tick ve süreleri [ham ölçüm](evidence/phase06-headless.json); minimum donanım/p95 kabulü yok.

## Faz07 katkısı

Faz07: 100.000 kayıt,16 sayfa, model≤200 kayıt; parent RSS steady aralığı ve worker+parent peak, sıcak n1 sayfa/profil süreleri scripts/measure_phase07.py ile gerçek ölçülür. 8MiB SQLite spool cache,4MiB görünür sayfa metni. Global sort mevcut ComputeBudget ve OS limit kapsamındadır. Minimum donanım/soğuk cache iddiası yok. [Ölçüm](evidence/phase07-headless.json).

## Faz08 kalite ölçümü

ENV-08, 2026-10-07 Europe/Istanbul; kurulu wheel100.000 kayıt tam kalite3499.1ms, örneklenmiş parent+worker peak513.71MiB, max UI tick45.0ms. N=1 sıcak geliştirici makinesi; minimum donanım veya tüm dosya/türlerde performans kabulü değildir. SQLite disk spool ve bounded5 örnek kullanılır. [Ham kayıt](evidence/phase08-wheel.json).


## Faz12 grafik ölçümü

ENV-12:100.000 kayıt, yedi grafik,100 QTest input+grabWindow, spawn RSS ve yaklaşık10ms Qt tick örnekleri; [kaynak](evidence/phase12-headless.json), [kurulu wheel](evidence/phase12-wheel.json). Sıcak Ryzen7/32GB, her yöntem N=1; input/render p95 tek başsız örneklemden, fiziksel ekran latency değildir. Parent+worker RSS ortak sayfayı iki kez sayabilir; bu ölçüm minimum8GB hedef veya tüm veri sınıflarında performans kabulü değildir. Açık grafik örneklemi/nokta ve RAM/üyelik sınırları [ADR-015](adr/015-charts-phase12.md)'te.

## Faz13 developer gerçek ölçüm

[Kaynak](evidence/phase13-headless.json) ve [kurulu wheel](evidence/phase13-wheel.json)100000 CSV/JSONL/Parquet exportunu ayrı process'te kayıt sayısı/hash ile ölçer; fresh XDG ilk açılış, gerçek PDF/HTML ve Qt event/RSS kontrolü aynı akıştadır. n=1, sıcak geliştirici runtime; hedef/minimum donanım/soğuk cache kabulü değildir. Ölçüm tüm walkthrough'un maksimum event aralığını saklar;16ms/50ms hedef karşılandı iddia edilmez. Kaynak değişmez/iptal sonrası hedef yok. Zorunlu bilgisiz kullanıcı görevi bu teknik ölçüm değildir.


## Faz14 istatistik ölçümü

ENV-14/source ve noneditable Linux wheel:100000 kapsam kaydı, iki grup n=[50000,50000], önkontrol/hypotez hesap/iptal,11 küçük yöntem fixture'ı, gerçek QML/render/save/reopen. [Sayısal ölçüm](evidence/PHASE14.md#e14-s006) ve [source](evidence/phase14/headless.json)/[wheel](evidence/phase14/wheel.json). N=1 sıcak Ryzen7/32GB; max event aralığı tüm walkthrough'u, parent+worker RSS örneklemesi paylaşılan sayfaları da kapsar. Bu sonuç fiziksel input→frame veya50ms hedef/minimum8GB donanım kabulü değildir; hedef ile gözlem ayrı kalır. Tam kapsam100k/20 grup, açık filtre/Float64 ve RAM sınırları [ADR-017](adr/017-statistics-phase14.md) içinde.

## Faz15 ölçümü — ENV-15, 2026-10-08

100000 kayıt uygunluk/fit edilmemiş plan: kaynak 213.1ms, kurulu wheel 234.7ms. Dört amaç, gerçek geçmiş mean fill/kaynak seçimi/kayıt açma ve büyük veri akışı toplamında parent+worker peak RSS kaynak 626.0MiB / wheel 625.2MiB. GUI tick50ms hedefi; actual maksimum 74.0/87.8ms, gap 24.0/37.8ms. İptal 180.5/238.4ms; önceki plan korundu. Warm developer Linux/offscreen/software ve eşzamanlı regresyon yükü; minimum donanım/temiz kurulum kabulü değil. [Kaynak](evidence/phase15/headless.json), [kurulu wheel](evidence/phase15/wheel.json).

## Faz16 geliştirici ölçümü

[ENV-16](evidence/phase16/environment.json), [kaynak](evidence/phase16/headless.json), [kurulu wheel](evidence/phase16/wheel.json).100000 kayıt/2 özellik/3 fold baseline kaynak 3.409s, kurulu wheel 3.404s. En uzun örneklenen Qt tick aralıkları 231.205/232.105ms. Parent+worker RSS yaklaşık1.12GB. Sıcak geliştirici runtime ve eşzamanlı yerel test yükü; minimum donanım/soğuk cache kabulü değildir.100ms UI hedefi bu gözlemlerde aşılmıştır; bütün performans hedefleri karşılandı denmez. Büyük üyelik kayıtları artifact, QML sunumu küçük özet; dense dönüşüm max4m hücre/RAM bütçesiyle açık reddedilir.

Faz17: sınırlı sayısal tahmin yolu, Faz15 hazırlığı ve Faz16 split/fold/defteri üstünde gerçek training-only estimator pipeline kullanır. Adaylar baseline/doğrusal/Ridge/RandomForest; seçim yalnız geliştirme CV MAE, final testte tek dondurulmuş aday. MAE/RMSE hedef birimi, R² negatif/sabit hedef sınırı, gerçek-tahmin/artık grafikleri (en fazla1000 örnek; metrik tam bölüm), dar ayar/maliyet sınırları ve test sonrası keşifsel yorum. Ayrıntılı sözleşme [ADR-020](adr/020-regression-phase17.md), gerçek kabul [PHASE17](evidence/PHASE17.md).

Faz19 geliştirici makinesi sıcak offscreen/software ölçümü: sekiz gerçek
kaynak/noneditable wheel fit/mark/reopen. KMeans/IF/IQR100.000,
DBSCAN3.000 kayıt;20 ölçüm sınırı, DBSCAN n² bellek kapısı ve silhouette3.000
noise-dışı tam-kapsam sınırı. Kaynak parent+worker peak932290560 byte/tick145.302ms;
wheel934359040/tick147.066ms. Genel donanım/soğuk açılış kabulü değildir.
[Gerçek kayıt](evidence/PHASE19.md), [ham kaynak](evidence/phase19/source-final.json),
[ham wheel](evidence/phase19/wheel.json).

## Faz20 — ENV-20, 2026-10-09

Yeni100000 satırlı dosyada batch127 ile gerçek transform/predict ve tüm
RowId/kolon koruması. Kaynak LinearRegression4.897s/LogisticRegression6.915s;
noneditable Linux wheel5.983s/4.766s. Tepe parent+worker RSS1070403584 /
1073893376 byte; paylaşılan sayfalar mükerrer sayılabilir. Bütün akışın max
Qt tick aralığı462.429 /397.349ms; max250ms bütçesiyle sayısal fark
212.429 /147.349ms. Tick ile fiziksel input→frame aynı ölçüm değildir.
Bu ölçüm p95 veya fiziksel input→frame değildir; tüm performans bütçelerine
kabul verilmez. Sıcak geliştirici donanımı/eşzamanlı testler, n=1.
[Kaynak](evidence/phase20/source-complete.json),
[wheel](evidence/phase20/wheel-complete.json), [kanıt](evidence/PHASE20.md).


<a id="faz24-hedef-olcum-fark"></a>
## Faz24 — hedef / ölçüm / fark

2026-10-09, ENV-24. Ryzen7 8845HS/8core16thread/31.388MiB host RAM,
NVMe Btrfs; fixture/proje/worker cache bu kez SSD üzerinde.4 logical CPU
affinity/2 native compute thread; fiziksel8GiB minimum testi değildir.
CPython3.13.15/Qt6.11.2 ve kilit/library/OS bilgileri
[benchmark](evidence/phase24/benchmark.json) içinde. Warm OS cache, fresh
trial process/project.50ms RSS (model child eklenir; shared RSS mükerrer olabilir),
250ms worker+staging logical disk; yayımlanmış artifact ve fixture hariç.
Örneklenmiş peak anlık peak alt sınırıdır. Önceki tmpfs/lazy öncesi kayıtlar
karşılaştırma arşividir; final SSD kaydının yerine geçirilmez.

| Metrik | Hedef | Ölçüm | Fark (ölçüm−hedef) | Örnek/kapsam |
|---|---|---|---|---|
| Warm ilk frame | ≤2000ms | 697.7ms p95 | -1302.3ms | 20 |
| Cold OS ilk frame | ≤5000ms | ölçülmedi | — | 0; OS cache düşürülmedi |
| Fresh uygulama cache / OS warm | cold OS hedefiyle eşdeğer değil | 720.7ms max | — | 5 fresh XDG/QML cache kapalı |
| CSV kaynak capture+200 preview | ≤3000ms (orta) | 239.7ms | -2760.3ms | 1; hash/kopya dahil |
| import input→client-render p95 | ≤100ms | 8.88ms | -91.12ms | 100 input; busy=100 |
| import input→client-render max | ≤250ms | 13.92ms | -236.08ms | offscreen/software |
| profile input→client-render p95 | ≤100ms | 11.62ms | -88.38ms | 100 input; busy=100 |
| profile input→client-render max | ≤250ms | 18.14ms | -231.86ms | offscreen/software |
| GUI event-loop en uzun aralık | input frame hedefiyle eşdeğer değil | 82.59ms | — | 5ms QTest bekleme; tüm akış |
| İptal feedback max | ≤100ms | 0.99ms | -99.01ms | 10 |
| Worker exit+cleanup p95 | exit≤2000ms / cleanup≤5000ms | 74.21ms birlikte | -1925.79ms exit bütçesine göre | 10 |
| Boş GUI RSS | ≤300MiB | 235.9MiB | -64.1MiB | 20 yeni süreç max |
| GUI parent+worker RSS | ≤2048MiB | 436.1MiB | -1611.9MiB | 100ms konservatif shared RSS |
| Paylaşılan GUI cache disk | ≤4096MiB | 28.3MiB | -4067.7MiB | 300ms supervisor |
| Gösterilen sayfa / page cache | ≤200 satır / 3 sayfa / 64MiB | 200 / LRU3 / 0.051MiB | sınır içinde | 24 tekrar; cache payload bytes |
| Tekrar parent RSS aralığı | sonsuz büyüme yok | 4.80MiB steady range | sayısal hedef yok | 24 tekrar, ilk4 hariç |
| Ağır worker / kalan staging | ≤1 / 0 | 1 / 0 | 0 | import/profile/cancel/RAM fault |

[Kaynak ham GUI](evidence/phase24/gui.json), [kurulu wheel](evidence/phase24/wheel.json).
N=1 preview bütçe gözlemidir, p95 preview kabulü değildir. Fiziksel ekran/compositor
latency ölçülmedi.10 iptal parser aşamasında, aynı ACTIVE ve sıfır workspace;
exit+cleanup birlikte ölçüldüğü için ayrı OS exit timestamp iddiası yoktur.

Yerel [Wayland/software](evidence/phase24/wayland.json): import100 olay p95 5.46ms/max 12.44ms; tam profil100 olay p95 8.13ms/max 20.06ms. İptal10 tekrar p95 45.71ms; tick max 55.73ms. Native Qt client render ölçümü, gerçek insan veya physical panel latency değil. X11 bu fazda çalıştırılmadı.

### Üç boyut benchmark

Her hücre median saniye / örneklenmiş peak MiB. N=3, p95 hız iddiası yok;
10k / 100k / 1000001 kayıt. Veri sınıfı satır sayısına göre; sıkıştırılmış Parquet
bytes tek başına RAM boyutu değildir. Trial içinde native allocator önceki
aşamaları tutabilir; GUI parent bu tabloya dahil değil, model child dahildir.

| Aşama | Küçük10k | Orta100k | Büyük1000001 | Kapsam |
|---|---|---|---|---|
| Capture/import/publish | 0.096s / 175.4MiB | 0.657s / 316.9MiB | 5.753s / 723.6MiB | tam |
| Exact profil | 0.080s / 194.5MiB | 0.616s / 318.0MiB | 4.629s / 610.8MiB | tam |
| Filtre/yaz/doğrula | 0.020s / 194.8MiB | 0.071s / 270.3MiB | 0.465s / 596.1MiB | tam |
| Left join/lineage | 0.113s / 222.3MiB | 0.979s / 772.6MiB | 9.161s / 1678.1MiB | tam |
| Grafik/çizim | 0.210s / 226.0MiB | 0.224s / 489.1MiB | 0.320s / 458.7MiB | açık ilk10000 örnek |
| HTML rapor | 0.019s / 224.9MiB | 0.025s / 311.2MiB | 0.063s / 358.0MiB | tam count / tablo ilk100 |
| Baseline CV/paket | 1.183s / 497.0MiB | 2.899s / 741.4MiB | 1.159s / 511.6MiB | küçük/orta tam; büyük açık10000 örnek |
| Tablo sayfası | 0.010s / 188.4MiB | 0.018s / 312.8MiB | 0.057s / 640.2MiB | bounded200 |
| Model önkontrolü | 0.008s / 224.7MiB | 0.033s / 311.2MiB | 0.023s / 356.0MiB | büyük tam kapsam açık ret |

Büyükte model hazırlığı100k destek kapısından reddedilir; tam1M model eğitildi
denmez. Model ilk-N ayrı veri sürümü/seed42; temsili örneklem garantisi yok.
Grafik10k ilk-N scope açık; filtre/profil/join tam veri. Dataset/RowId lineage
ve immutable fingerprint kontrolü işlem süresine dahildir. Disk peak/table
scope, native/helper thread sayıları ve beklenen retler [ham JSON](evidence/phase24/benchmark.json) içindedir.

[Kolon projection referansı](evidence/phase24/projection.json), üç fresh reader süreç/100k kayıt/12 uzun kullanılmayan metin alanı:15 kolon okumada median 94.9ms, peak 502.4MiB;3 seçili kolonda 8.0ms/106.8MiB. Yalnız reader karşılaştırmasıdır, bütün modelde aynı hız kazancı iddiası yok.

Native compute thread budget görünür CPU affinity ile sınırlandırılır; varsayılan2.
Linux helper thread toplamı2 değildir. Gerçek spawn pool/affinity, aşırı1m thread
ayarının clamp edilmesi, shared RAM/disk reddi, ENOSPC transaction ve cleanup
koruması [kaynak testleri](evidence/phase24/resources-final.log) ile doğrulanır.
Minimum fiziksel4-core8GiB/soğuk OS cache/physical panel ve X11 kapıları
açık: F24-S006 doğrulanmadı; ölçümler tüm performans hedefleri kabulü değildir.

Faz66 ENV-66: [donanımlı bounded Dask benchmark ve GUI ölçümü](evidence/PHASE66.md#e66-validation).
Tek makine fixture; genel speedup/cluster/GPU/minHW iddiası yok.100ms RSS sample
zirve kaçırabilir/shared pages double count olabilir. İş başına native thread1,
toplam2 varsayılan; eski RAM2GiB/disk4GiB/time600s limitleri korunur.
