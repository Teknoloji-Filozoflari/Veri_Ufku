# ADR-027 — Faz24 ölçülmüş kaynak bütçesi ve performans

2026-10-09. Açık kullanıcı Faz24 yetkisi; Linux/Python/PySide6/QML korunur.

Mevcut doğrulanmış yollar değiştirilir, yeni model/format veya streaming-fit
vaadi eklenmez. Import native/CSV parçalarla, sorgu/filtre/join Polars lazy
streaming sink ile, exact profil/üyelik SQLite disk spool ve 8MiB cache ile
çalışır. Decimal/tür/RowId/null eşitliği korunur. DuckDB geliştirici bağımsız
SQL referansıdır; ölçülmüş bir üstünlük veya aynı exact tür sözleşmesi olmadan
üretim join backend'i değiştirilmez. DuckDB'nin spill desteği bütün Polars
işlerinin otomatik disk spill yaptığı anlamına gelmez. Kullanılan RAM sınırlı,
sığmayan işlem açıkça reddedilir; genel dış bellek join garantisi verilmez.

Dataset sayfaları parent-owned LRU: en fazla3 bounded gösterim sayfası/64MiB
serileştirilmiş metin; tek widget modeli200 satır. DataFrame veya bütün veri
QML'ye verilmez. Anahtar immutable path/fingerprint/version/metadata/config ve
view/offset içerir. Cache hit de disposable worker'da kaynağın tam SHA256'sını
denetler; bozulmuş kaynak sonucu kabul edilmez. Cache payload byte sınırı Python
nesne overhead'inin kesin RAM üst sınırı değildir;3 sayfa ve toplam RSS bütçesi
ayrıca uygulanır. Geçmiş sayfalar LRU ile atılır, profile suggestions ayrı kopyadır.

Baseline yalnız seçili özellikler/hedef/RowId/grup/zaman kolonlarını okur.
Fit üyeliği skops içinde tek Unicode ndarray olarak saklanır; dış ModelCard/v1
üyelik listesi/evaluation/fit referansları ve eski v1 liste okuması korunur.
Tam veride sayılan kategori kardinalitesi öğrenilmiş eğitim sözlüğü değildir.
Hazırlama raporu yaklaşık seçili giriş ve olası dense matris maliyetini gösterir;
uzun metin, fold kopyaları, kategori genişlemesi ve estimator ek maliyeti belirsizdir.
Kullanıcı özellikleri daraltır veya açık filtreyle daha küçük sürüm seçer;
örnekleme/retraining sessiz yapılmaz.100000 hazırlık sınırı ve yöntem kapıları
korunur; büyük benchmark model fit'i açık10000 ilk-N örneğidir.

JSON ve TextSpec/TimeSeriesSpec/ValidationSpec frontend sözleşmeleri ağır
model kütüphanelerinden ayrılır. Model/veri hesapları worker'da yüklenir;
açılış RAM'i ve ilk frame tekrar ölçülür. Eğitimli proje doğrulama yolları bazı
model kütüphanelerini I/O thread'inde yükleyebilir; boş GUI RSS'i bütün projelerin
idle garantisi değildir.

Native Polars/OpenBLAS/OMP/MKL/NumExpr thread ortamı ilk GUI importlarından
önce bütçeye ayarlanır. Spawn ortamı miras alır, worker affinity ve threadpoolctl
mevcut BLAS/OpenMP havuzlarını sınırlar. CPU thread ayarı görünür affinity üstünde ise ComputeBudget etkili sınırı
saklar;1m ayar native kütüphaneye aktarılmaz. Varsayılan2 compute thread; yardımcı
I/O/runtime thread'leri vardır, toplam Linux thread sayısı2 değildir.
Proje ağır iş admission'ı gerçek controller'lar ve demo için ortak; varsayılan
tek ağır worker, project I/O executor tek sahip. Demo kapanışı ayrı kaldığı için
aktif demo güvenle shutdown olur; gerçek dataset yayınında pencere kapanmaz.

Control100ms RSS, süre/iptal ve250ms recursive private disk/reserve kontrolü;
worker başarı IPC'sinden önce zorunlu final disk kontrolü. Worker RLIMIT_AS
başlangıç sanal alanı+RAM allowance, RLIMIT_CPU ve CPU affinity kullanır.
RLIMIT_AS toplam fiziksel RAM değildir. Qt ResourceSupervisor100ms parent+worker
RSS'i, yaklaşık300ms (100ms timer üzerinde250ms kapısı) paylaşılan cache alanını
izler; bütçe aşımında iptal istenir. Sınırdaki ani/native/uninterruptible I/O
artışları örnekleme aralarında olabilir; cgroup hard-RAM garantisi verilmez.
Disk dosya rename/cleanup yarışında kaybolan dosya örneği atlanır. ENOMEM,
MemoryError, ENOSPC ve EDQUOT anlaşılır hata ile önceki projeyi korur.

Import iptalinde private workspace hemen temizlenir ve yeniden önizleme gerekir.
Publish iptal/hatasında yalnız bu yayının oluşturduğu staging temizlenir;
önceki pending/commit/kurtarma kaydı korunur. Normal save tüketilmiş staging
hard linklerini kaldırır; committed artifact bağımsız hard linki korunur.
ACTIVE tek yayın noktasıdır. Disk reserve normal kayıt için max(1GiB,%10
beklenen artifact/manifest) olur. Cleanup'ın OS izin/I/O hatası altında best-effort
olduğu ve crash kurtarmasının ayrı olduğu korunur; kaynak dosya silinmez.

Kanıt: [PHASE24](../evidence/PHASE24.md), [bütçe/ölçüm/fark](../PERFORMANCE.md).
ENV-24 gerçek Ryzen/32GiB geliştirici donanımı,4 logical CPU affinity/2 native
compute thread; fiziksel4-core/8GiB minimum veya soğuk OS cache ölçümü değildir.
Faz25 başlatılmaz; önceki insan/bağımlılık kabulü ve minimum donanım kapısı açıktır.
