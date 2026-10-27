# Faz66 — ortak hesaplama bütçesi

2026-10-16 DEC66-01 / ENV-66. Açık Faz66 talimatı; resmî sürüyor,
deneysel, isteğe bağlı. Faz67 başlatılmaz. Önceki fiziksel/insan/AT/minimum
donanım/long retained-heap/temiz offline installer/remoteCI açıkları korunur.

<a id="e66-scope"></a>
## E66-SCOPE

Mevcut ComputeBudget genişletildi; RAM/disk/wall/sample ve CPU/IO concurrency
erken limitleri korunur. Toplam CPU thread ile süreç başına native thread ayrıdır.
Tek parent admission kapısı24 GUI worker, mevcut JobManager ve açık code kernel
Popen yolunda start öncesi process/CPUjob/native thread bütçesini birlikte kontrol
eder. Polars/BLAS spawn öncesi env, worker threadpoolctl/affinity; Torch/DuckDB iş
başına thread ve sklearn n_jobs1. Çekirdek varsayılanı RAM2GiB/disk4GiB/time600s,
CPUjob1/süreç1, toplam2 native thread/iş başına1 olarak kalır. Son değişiklik CPU
thread dağılımıdır; hız artışı garantisi verilmez.

Ana sayfa → Hesaplama bütçesi ve ölçümler: profil/join/tuning/explanation/tensor dahil
aynı controller/process gözetimi; RSS, süre, process ve configured native thread,
geçici disk zirvesi, son64 biten süreç. Bitmek başarı sayılmaz; ilgili iş sonucu
esas alınır.100ms RSS/process-tree,250ms disk örneklemesi; kısa zirveler kaçabilir,
shared-page double counting olabilir. RSS örneklenmemiş iş0MiB başarı iddiasıyla
sunulmaz. GPU/remote ölçümü yok. Yakalanmış alt süreçler cancel/grace/shutdown'da
pidfd/başlangıç kimliğiyle temizlenir; arbitrary code için OS sandbox iddiası yok.

Aynı Capability registry yöntem bazında execution_memory/device_support taşır.
Panel yöntem kimliği aramasında ilk50 gerçek kaydı/limits/sparse desteğini gösterir.
Bilinmeyen lazy/out-of-core fit açıkça doğrulanmamış kalır. Profil4096 batch ve
SQLite frequencies spill; diğer mevcut streaming yollar kendi sözleşmesiyle sınırlı.
Sparse→dense açık izin ve RAM önkontrolü ister; mevcut native-categorical sparse
reddi korunur. Özel spill context quota/cancel/failure sonunda yalnız kendi dizinini
siler. Diğer çalışma dizinlerinde mevcut Control.disk ve supervisor korunur.

Dask2026.8.0 seçildi: CPU-only numeric Parquet iter_batches, chunk≤4096,
pending≤min(max_tasks,8), bounded task dalgaları, kaynak hash önce/sonra,
finite n/excluded/sum; kaynak yazmaz. Core lock/venv değiştirilmedi; gerçek optional
runtime /tmp kurulumunda sınandı. Sınırlı adaptör Python API'sidir; GUI'den Dask
job başlatıcısı yok. Genel estimator/tensor out-of-core/distributed fit yok.
Float64 chunk toplamları farklı sırada yuvarlama farkı gösterebilir.

GPU planı destek/VRAM/transfer quota kontrol eder; CPU worker cuda bütçeyi reddeder.
Gerçek GPU runtime/hardware kabulü yok; implicit fallback yok. RemotePlan yalnız
TLS endpoint/konum/transfer boyutu/keyring referansı önizler, ağ veya credential
okumaz. Remote executor/auth/cluster-wide quota uygulanmış/doğrulanmış sayılmaz;
available=false. Kullanıcı verisi remote'a gönderilmez. Retry/resume exactly-once
garantisi yoktur. [Karar ve resmî backend kaynakları](../adr/067-compute-budgets-phase66.md).

<a id="e66-validation"></a>
## E66-VALIDATION

[Doğrulama](phase66/verification.json), [kabul](phase66/acceptance.json),
[kapılar](phase66/gates.json), [paket](phase66/wheel.json).
Donanım belirtilmiş [Dask benchmark](phase66/dask-benchmark/measurement.json):
AMD Ryzen7 8845HS,16 affinity CPU,32141972kB MemTotal; Linux7.2.9/glibc2.44,
CPython3.13.15.100000 integer /25chunk toplam4999950000; ilk ölçüm0.325s,
RSS208261120byte. Import/cache/host yükü ve hash eklenmesi ölçümü etkiler;
minimum donanım veya önceki sürümden hızlanma kanıtı değildir. Final hashli adapter
ölçümü ayrı dosyada; ilk ölçüm silinmedi.

Gerçek quota fail/cleanup, negative budget/sparse/VRAM/transfer, toplam process/thread
admission, cancel/timeout/code-kernel descendant cleanup ve immutable önceki commit
kontrolleri pytest kayıtlarında. Optional absent GUI açılışı ve gerçek profil işi
source/kurulu wheel panel walkthrough'larıyla. Offscreen fiziksel masaüstü/insan/AT
kabulü değildir. Seçilmiş regresyonlar tam depo testi değildir; skip başarı değildir.
Dask optional test runtime kanıtı remote distributed/GPU runtime kanıtı değildir.

406 offline makale, yeni compute-resources yardımı; tek registry/Provenance/ProjectStore
korunur. Yeni ölçüm geçmişi ephemeral panel verisidir; ikinci kalıcı run defteri yok.
Stage/commit/push yapılmadı. [Önceki durum](phase66/prior-project_state.txt).

Ek GUI tanılama: [fresh tuning default2GiB fail](phase66/search-gui-investigation.xml), gerçek toplam bellek kotası görünür iptal. Çoklu GUI grubu failures sonrası exit130 ile kesildi; başarı sayılmadı. Tensor test fixture açık4GiB kullanır; son sonuçlar verification.json içinde ayrı, default2GiB kabulünü kapatmaz.

Son parent-env lock düzeltmesi: GUI içindeki tekrarlı native thread env yazımları
kaldırıldı; yalnız admission kilidi altında spawn ayarı yapılır. Manager ve GUI RAM
ölçümü aynı aktif root reservation kümesini/descendants'ı kullanır. GUI panel sinyali
saniyede bir yayımlanır;100ms denetim korunur. Önceki255source/255wheel selected core
(1er absent-Dask skip) son bu düzeltmeden önce; ardından son pakette
[60source](phase66/source-complete.xml)/[60wheel](phase66/wheel-complete.xml),1er skip,
[1source GUI](phase66/source-gui-complete/gui.xml)/[1wheel GUI](phase66/wheel-gui-complete/gui.xml)
default2GiB. Bunlar ayrı koşulardır, tek aggregate değildir.373byte-eşit son paket.

Ayrı [tensor4pass](phase66/gui-investigation.xml) explicit4GiB ve
[basic9pass/1deselected](phase66/gui-basic-final.xml) son env-lock consolidation
öncesidir. [İlk4GiB tuning denemesi](phase66/search-gui-4gib/gui.xml)90s test bekleme
sınırında fail; üretim120s arama bütçesiyle aynı sınır değildir, başarı sayılmaz.
Model default2GiB ve uzun retained heap kabulleri açık kalır.

[Uzun test beklemesiyle4GiB/120s tuning](phase66/search-gui-4gib-complete/gui.xml) gerçekten budget_exhausted:7trial completed/1canceled,19 native-fit reservation,119.82s. Completed değildir; final test kullanılmadı, önceki triallar kaybolmadı. Daha küçük tek-aday/curves-off benchmark ayrı kaydedilir; büyük örneği başarıya çevirmek için bütçe varsayılanı artırılmaz.

[Son küçük tuning GUI](phase66/bounded-search-4gib/gui.xml) source1pass: explicit app4GiB/worker2GiB, tek aday,curves kapalı,üç outer fold; final test kullanılmadı. [Ölçüm](phase66/bounded-search-4gib/measurement.json): SearchController76.236s,490795008byte örneklenmiş worker peak. Test/fixture dahil95.78s. İki-aday120s budget_exhausted örneğiyle veya default2GiB ile birleştirilmez.

Son pidfd kimlik kontrolü: [source9pass/1skip](phase66/source-pidfd-complete.xml), [final wheel+Dask10pass](phase66/wheel-pidfd-dask-complete.xml). Gerçek own-child süreç yanlış başlangıç kimliğinde çalışmaya devam eder, eşleşen pidfd ile sonlandırılır; PID tekrar kullanımında başka sürece sinyal gönderilmez. Koşular paylaşılan geliştirme ortamındadır; idle/dedicated CPU hız kıyası değildir.

[Son wheel küçük tuning1pass](phase66/wheel-bounded-search-4gib/gui.xml), test/fixture100.09s; source ile aynı explicit4GiB/tek-aday/curves-off,3outer fold/test untouched. [Ölçüm](phase66/wheel-bounded-search-4gib/measurement.json). Son environment/cache/repro regresyonu ayrıca [30source](phase66/source-cache-complete.xml)/[30wheel](phase66/wheel-cache-complete.xml), intentional duplicateZIP warning.60şar focused ile ayrı koşular; full repository regression değildir.
