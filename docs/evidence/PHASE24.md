# Faz24 — mevcut yolların performans ve kaynak dayanıklılığı

2026-10-09 Europe/Istanbul, ENV-24. Açık Faz24 kullanıcı yetkisi. Gerçek
Linux x86_64/CPython3.13.15/Qt6.11.2 kilitli ortam; donanım ve lock
[benchmark JSON](phase24/benchmark.json) içinde.4 logical CPU affinity,
2 compute thread; host yaklaşık32GiB RAM/NVMe Btrfs. Ölçüm fiziksel8GiB
minimum kabulü değildir. Faz sürüyor/deneysel/zorunlu; Faz25 başlamadı.

<a id="e24-s001"></a>
## E24-S001 — mevcut yolların uygulanmış iyileştirmesi

jobs/limits ve supervision, importers/Control, analytics/PageCache ve worker,
modeling/baseline/preparation, lightweight sözleşmeler, storage/ProjectStore,
QML kaynak maliyeti. [ADR-027](../adr/027-performance-phase24.md).
Column projection, bounded page LRU, native thread sınırı, toplam RSS/cache
supervision, güvenli kaynak/disk/bellek hatası, iptal ve staging temizliği.

<a id="e24-s002"></a>
## E24-S002 — üç veri sınıfı / yedi gerçek üretim yolu

`scripts/measure_phase24.py`:10k,100k,1000001 kayıt; sınıf başına3 fresh trial,
sabit formül fixture/hash ve model seed42. Capture+native import+publish,
exact tam profil, kalıcı filtre, left join+RowId lineage, grafik hesap/render,
HTML rapor publish ve gerçek baseline CV/model package ayrı ölçülür.
Ek200 satır sayfa ve model önkontrolü ayrı kayıtlıdır. Lazy/native yolu
CSV GUI importundan ayrıdır. Başlangıç oluşturma fixture süresi ölçüme katılmaz.

[Ham JSON](phase24/benchmark.json), her trial JSON aynı dizinde. Median/max,
örneklenmiş RSS ve scratch disk/thread sayısı kayıtlı; N=3'te p95 hız iddiası yok.
Trial içinde üretim çekirdek yolları ardışık çalışır; native allocator önceki
alanları tutabilir. Model fit ayrı OS-limitli süreçte çalışır, onun RSS'i
orchestrator'a eklenir. Bu benchmark'ın her aşaması GUI parent'ı içermiyor;
gerçek GUI parent+worker ayrıca aşağıda ölçülür. Shared RSS mükerrer olabilir.
Anlık peak örnekleme arasında kaçabilir; ölçülen peak alt sınırdır.

Grafik ilk10000 kayıt açık örneklem, rapor tam count+ilk100 tablo; bütün
raporun100 kayıtla sınırlı bir popülasyon hesabı olduğu söylenmez. Büyükte
1000001 kayıt model hazırlığı açık reddedilir; fit yalnız açık10000 ilk-N
sürümündedir, tam1M fit veya temsili örneklem iddiası yoktur.

<a id="e24-s003"></a>
## E24-S003 — bounded veri ve açık model maliyeti

Mevcut streaming Polars/chunk/SQLite disk spool8MiB cache ve yeni3-page LRU;
RowId/tür/null/Decimal testleri korunur. DuckDB önceki SQL doğruluk referansıdır;
üretimde DuckDB disk-spill veya bütün yöntemlerde streaming-fit eklendi denmez.
[Projection bağımsız reader ölçümü](phase24/projection.json):100000 kayıt,
12 kullanılmayan uzun metin kolonuyla15→3 kolon okuma; fresh süreçte üçer tekrar,
10ms RSS. Bu yalnız Parquet okuyucu farkı; tam model hız artışı değildir.
ModelResourceForecast yaklaşık maliyet+özellik azaltma/açık filtre seçeneği,
streaming_fit=false, eski v1 üyelik listesi açılması ve paket/no-refit testleri.
Yeni hazırlama provenance yardım sürümü32 kaydeder; eski kayıtlar değiştirilmez.
Katalog32: model-preparation ve tasks kaynak/örneklem/iptal açıklamaları;147
makale/102 sözlük korunur. Gerçek100000 satırda maliyet metni1366×768 ve720×560
pencerelerde görünür/sarılıdır: [dar görünüm](phase24/forecast-720.png),
[masaüstü](phase24/forecast-1366.png), [alan/ölçü JSON](phase24/forecast.json);
`scripts/measure_phase24_forecast.py` aynı QML/worker yolunu çalıştırır. `check_learning` kapısı ayrı gerçek kayıtlıdır.

<a id="e24-s004"></a>
## E24-S004 — kaynak sınırı, ağır iş paylaşımı ve güvenli iptal

[Kaynak testleri](phase24/resources.log), tests/test_performance.py:
recursive spill disk limiti; gerçek Qt worker toplam RAM ve shared disk bütçesi
reddi; ENOMEM/MemoryError/ENOSPC/EDQUOT açıklaması; gerçek SQLite page-kota dolması için SQLITE_FULL disk mesajı; ENOSPC transaction fault
sonrası ACTIVE/reopen; import yayınında copy-chunk iptali ve önceki staging
koruması; cache hit kaynak tamper; native Polars/BLAS/OpenMP2 thread/affinity;
model projection/compact membership ve eski liste; import/demo admission;
görünür CPU üstünde1m thread ayarı gerçek etkili bütçeye daraltılır.
Önceki import kaynak değişimi, tamper, kill/transaction testleri tam suite içindedir.
Toplam bilinmeyen kayıt aşamasında yüzde yok; yöntem aşaması/kayıt sayısı gösterilir.

<a id="e24-s005"></a>
## E24-S005 — gerçek GUI, tekrar RSS ve ağır parser iptali

`scripts/measure_phase24_gui.py`,100000 satırlı gerçek CSV, QML/spawn.
100 gerçek QTest input→client-render olayı importta ve profilde; busy olay
sayısı ham kayıtta, fiziksel ekran latency değil.24 aynı bounded sayfa isteği,
steady RSS aralığı/3-page cache.10 parser aşamasında iptal; feedback ve
worker-exit+cleanup ayrı; her denemede workspace yok ve ACTIVE aynı.
GUI RAM sınırında worker iptali kaynak hash'ini ve commit'i korur.
[Kaynak JSON](phase24/gui.json), [görsel](phase24/gui.png);
[gerçek Wayland client JSON](phase24/wayland.json)/[görsel](phase24/wayland.png),
[noneditable wheel](phase24/wheel.json). Import/profilin her birinde100 olay
gerçekten busy sırasında işlendi;24 tekrar ve10 parser iptali üç ortamda geçti.
Eski açılış/lazy öncesi [JSON](phase24/gui-before-lazy.json) korunur;
hız karşılaştırması kontrollü donanım garantisi değildir.

<a id="e24-s006"></a>
## E24-S006 — hedef / ölçüm / fark ve açık kapılar

[PERFORMANCE](../PERFORMANCE.md#faz24-hedef-olcum-fark) tablo ve örnek sayıları.
20 sıcak açılış,5 fresh XDG/QML-cache-kapalı açılış; OS cache warm kalır.
Cold OS/physical input→display/minimum4physical-core8GiB makine/Wayland ve X11
birlikte kabulü ölçülmedi; F24-S006 doğrulanmadı kalır. Yerel ölçülmüş RAM/disk,
UI input ve iptal hedefleri minimum donanım sonucuna dönüştürülmez.

## Gerçek kontrol ve paket kayıtları

Standart locked sync/docs/artifacts/learning/Ruff/pytest/unittest ve noneditable
wheel entry smoke çalıştırılır. Nihai sonuçlar:628 pytest216.25s ([tam log](phase24/pytest-final.log));
9 locked unittest ([log](phase24/unittest-final.log));147 learning/91 UI bağları;
sync/check_docs/check_artifacts/Ruff check ve format başarılı.
[Komut/exit/date kaydı](phase24/checks.json);95 kaynak/job/GUI/model regresyon kontrolü
[log](phase24/resources-final.log). Yardım provenance ve hazırlama/lifecycle için
68 hedefli kontrol de geçti ([log](phase24/help-provenance-final.log)).
[Wheel build/install/GUI/entry kaydı](phase24/package-checks.json),
[entry GUI_SMOKE PASS](phase24/wheel-entry.log). Son görsel betik için ek
Ruff/format/docs/learning kapısı `final-review.log` içinde.
Sistem `/usr/bin/python3`3.14.7 unittest62 test/53 modül hatasıyla başarısız;
PySide6/Polars ve kilitli analitik bağımlılıkları sistem Python'da yok
([gerçek hata logu](phase24/system-unittest-final.log)); sistem kontrolü başarılı
yazılmaz. Mevcut locked3.13 kurulumu noneditable wheel bağımlılıklarını sağlar;
temiz makine/offline kurulum kabulü değildir.
Önceki insan/bağımlılık kabulü, fiziksel8GiB/cold OS/physical panel/X11 ve
yeni remote CI yapılmadı. Faz25 başlamadı.
Sistem Python bağımlılık eksikliği kilitli runtime başarısıyla karıştırılmaz.
İlk benchmark'taki tek-süreç RLIMIT_AS birikimi/model JSON MemoryError ve
geçici test/QML/GUI kapanış hataları düzeltildi; ilk hata kayıtları saklıdır.
Ölçüm betiğinin tamamlanmış final kaydı başarılı stage sonuçları ve büyük
modelin beklenen kapsam retlerini ayrı tutar.
