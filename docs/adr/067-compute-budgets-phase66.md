# ADR067 — Faz66 ortak hesaplama bütçesi

2026-10-16 DEC66-01. Yalnız açık Faz66 talimatı; Faz67 yetkisi yok.

Mevcut ComputeBudget genişletilir: max_processes, max_tasks, threads_per_process,
device_memory_bytes ve transfer_bytes. RAM2GiB/disk4GiB/time600s/örnek10000/CPUjob1
varsayılanları korunur. cpu_threads toplam native compute bütçesidir;
worker_threads=min(cpu_threads, threads_per_process). Varsayılan iş başına1 native
thread, toplam2; gerçek hız artışı iddiası yoktur. Parent-only tek admission lock
GUI spawn, JobManager ve explicit code kernel Popen için süreç başlatmadan önce
CPU job/process ve toplam native thread rezervasyonlarını denetler. Kuyruk üst
sınırı min(32,max_tasks). İşletim sistemi/native servislerin idle housekeeping
thread sayısı compute thread sayısı değildir. Alt kütüphane n_jobs=1 tutulur;
Polars/BLAS environment spawn öncesi, threadpoolctl/affinity worker içinde;
Torch ve DuckDB worker_threads kullanır. Arbitrary code bu sınırları aşmayı
deneyebilir: ayrı process güvenlik sandbox'ı değildir.

Kaynak gözetimi100ms RSS/process-tree örneklemesi ve250ms disk taramasıdır;
pidfd/başlangıç kimliği ile yakalanmış alt süreçleri iptal/grace/shutdown'da
sonlandırır. RSS shared pages double count yapabilir, kısa zirveler kaçabilir;
cgroup/OS sandbox/hard multi-tenant enforcement değildir. Erken RAM/disk/wall,
quota/reserve, grace, mevcut atomic publication ve user data koruması sürer.
Panel son64 süreç ölçümünü saklar; job başarı/iptal sonucunun ikinci registry'si
değildir. Eski ölçüm uydurulmaz; GPU/remote RSS ölçümü yoktur.

Capability.execution_memory/device_support aynı registry'yi genişletir.
Mevcut streaming bayrağı olanlar koşullu bounded streaming; diğerleri conservative
in-memory/unvalidated lazy fit. Lazy source tüm estimator'un lazy fit olduğu
iddiası değildir. Panel yöntem kimliği aramasında ilk50 gerçek kaydı ve mevcut
limits/sparse desteğini gösterir. checked_dense açık izin ve conservatif RAM
önkontrolü ister; mevcut optional categorical sparse reddi korunur. Spill context
yalnız işe ait temporary directory'yi quota/check/cancel sonrası temizler;
mevcut worker disk gözetimi diğer çalışma dizinlerinde sürer. Genel otomatik GC yok.

Dask2026.8.0 seçildi: ihtiyaç numeric immutable Parquet chunk reduction/task waves;
Ray/cluster yönetimi eklenmedi. Optional modül importu Dask veya ağ yüklemez.
CPU-only local-threads, Arrow iter_batches≤4096, pending≤min(max_tasks,8),
preflight/RSS/time/cancel; reducer mevcut numeric integer/float kolonda n/excluded/
sum üretir. Float64 chunk sırası rounding değiştirir. Tensor/model fit distributed
veya out-of-core yapılmış sayılmaz. Dask core lock'a zorunlu eklenmedi;
izole /tmp test kurulumu gerçek runtime kanıtıdır, offline core bağımsızdır.

GPU budget planı transfer/VRAM/destek kontrol eder; native CPU worker cuda bütçeyi
reddeder, otomatik fallback yapmaz. Gerçek GPU backend/hardware kanıtı yok.
RemotePlan sadece tls://host:port, konum, keyring referansı ve transfer boyutu
önizlemesidir; network call, credential load veya remote executor içermez.
Remote runtime unavailable: doğrulanmış cluster quota/mTLS/keyring-in-memory auth
yolu olmadığından kullanıcı verisi gönderilmez. Remote auth/runtime kabulü açık.
Dask TLS'nin hostname doğrulamaması kuruluş CA/trust kararı gerektirir; remote
çalıştırma arbitrary-code trust sınırıdır. Retry/resume exactly-once değildir;
source write/export distributed retry uygulanmaz. Remote plan bağlantı izni değildir.

Resmî kaynaklar (2026-10-16 incelendi):
- https://distributed.dask.org/en/stable/worker-memory.html
- https://distributed.dask.org/en/stable/worker.html
- https://distributed.dask.org/en/stable/tls.html
- https://distributed.dask.org/en/stable/killed.html

Teknik bounded CPU teslimi ile tüm fazın resmî kabulü ayrıdır.

Son concurrency denetimi: GUI'deki eski env yazımları kaldırılır; thread env ayarı
yalnız start lock altında gerçekleşir. GUI/manager RSS aynı canlı root reservation
kümesini kullanır. Ölçüm100ms sürerken UI changed yayını1s ile sınırlıdır; kapalı
panelde her100ms tüm satırları yeniden oluşturarak iş yükünü büyütmez.
