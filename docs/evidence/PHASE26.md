# Faz26 — veri bütünlüğü ve güvenilirlik incelemesi

2026-10-09 UTC / 2026-10-10 Europe/Istanbul; ENV-26/ENV-26-OFFLINE/ENV-26-WHEEL.
Kullanıcı açık Faz26 talimatı. Yalnız sentetik fixture'lar ve geçici projeler;
gerçek kullanıcı veri dosyaları okunmaz. Faz sürüyor/deneysel/zorunlu:
önceki insan/AT/bağımlılık kabulü açık kalır; dağıtım adayı kabulü verilmez.
Faz27 başlatılmadı. [Karar](../adr/029-reliability-phase26.md).

<a id="e26-s001"></a>
## E26-S001 — kaynak incelemesi ve bulunan açıklar

F26-FIND-01: manifest doğrulayıcısı şema4/5/6'yı kabul ettiği halde open/_load
pointer listesi dışlıyordu. Liste eşitlendi; yeni statik fixture'lar ve
salt okunur byte korunumu/yeni commit/SQLite eski payload kontrolleri eklendi.

F26-FIND-02: log leaf symlink/hardlink başka dosyanın içerik/izinlerini
değiştirebilirdi. O_NOFOLLOW/normal-file/tek-link açılışı ve0600 eklendi;
sentinel içerik ve0644 izin korunumu denetlenir.

F26-FIND-03: ODS DTD/entity kontrolü UTF-16/32 null byte kodlamasıyla
atlanabiliyordu; XLSX'in mevcut normalize kontrolü ODS'e uygulandı.
Archive yol/symlink, sabit mimetype boyutu ve göreve ait açılmış disk bütçesi
denetimleri eklendi. Kaynak inspect gerçek bütçeyi erken doğrulamaya taşır.

F26-FIND-04: kurtarma diyaloğu yalnız genel taslak değişim uyarısı taşıyordu.
Gerçek doğrulanmış ad/zaman/sayı önizlemesi ve commit bağı eklendi; stale
önizleme yüklenmez. F26-FIND-05: proje SQLite leaf/companion hardlink'i dış
veritabanına yazmaya neden olabilirdi. Normal-file/tek-link denetimi eklendi.
Kaynak/default bütçe artırılmadı; son sağlam kayıt korunur.

F26-FIND-06: tam koşu temizlik GUI'sinde Qt timer olay dağıtımında exit139
ile çöktü. GDB tam koşu çağrı izi `phase26/gdb-full.log` içinde; odaklı84
kontrol gdb altında geçtiğinden bu tek başına kapanış kanıtı sayılmadı.
ShellController poll timer'ı cleanup'ta durmuyordu ve engine parent'ı yoktu.
Timer engine'e bağlandı; dispose kapanıştan önce timer'ı durdurup manager'ı
kapatır. Kaynak bırakma testi timer'ın aktif kalmadığını da denetler.
İlk lint/pytest hata kayıtları korunur; başarısız koşu kabul olarak sayılmaz.

<a id="e26-s002"></a>
## E26-S002 — saldırgan sentetik girişler ve kaynak yaşam döngüsü

`tests/test_security_audit.py` eski şema/log/ODS/AST/SQL/parser sınırlarını
çalıştırır. Mevcut testler JSON duplicate/depth/nonfinite, XLSX macro/entity/
symlink/oversize, Parquet/IPC tip/hassasiyet, kötü manifest/artifact paths,
AST attribute/import/index/lambda/comprehension, quoted SQL identifier ve
parametre, HTML escape/CSP, güvenli CSV başlık/metin ve XLSX inlineStr,
pickle/joblib/unreviewed type/model archive retlerini denetler.

`tests/test_jobs.py` exception metni/değerlerinin logda olmadığını, job/error
referansını, iptal/kapanış/temp cleanup'ı çalıştırır. Controller/workers eski
binding'i güncel sonuç diye yayımlamaz. Yeni shared control ve yardım bağları
Faz25 kapısında korunur. Başarılı toplu test, tek başına bütün alt yöntemlerin
kanıtı sayılmaz; JUnit ile yöntem/nokta eşlemesi ayrıca çıkarılır.

<a id="e26-s003"></a>
## E26-S003 — kurtarma, disk, şema ve iki süreç

`tests/test_security_gui.py` gerçek QML düğmesi/I/O worker/modal önizleme/
onay/restore/manuel Kaydet akışıdır. ACTIVE restore'da aynı, ancak ayrı
Kaydet'te yeni commit olur. Bozuk/stale/farklı-parent autosave taslağı ve
ACTIVE'yi değiştirmez. Kaynak eksik olsa da kayıtlı snapshot açılır; metadata
açılışı dış kaynağı yeniden import etmez. Salt okunur ikinci süreç aktif
yazıcı kilidini devre dışı bırakamaz. Şema0–6 fixture'ları eski kayıtları
koruyarak migration'ı sınar;4–6 için yeni fixture'lar eklendi.

14 ortak sınır autosave SIGKILL ve ENOSPC injection için yeni parametreli
testtir. Mevcut manuel14×2, import16 ve ek artifact/chunk/lineage SIGKILL
kontrolleri tekrar koşulur. Her açılış hash/payload/Parquet metadata doğrular;
önceki veya yeni tam yayın dışında karışık ACTIVE kabul edilmez.
ENOSPC sonrası pointer zaten yayımlanmışsa yeni commit korunur; atomiklik
“her hata mutlaka eski pointer'a döner” anlamına gelmez.

<a id="e26-s004"></a>
## E26-S004 — bağımsız referans, sızıntı, offline ve hash

[GOLDEN_REFERENCES](../GOLDEN_REFERENCES.md) bağımsız elle/kapalı form,
ayrı DuckDB motoru ve roundtrip/fit-spy ayrımını kaydeder. İstatistik,
join/dönüşüm/RowId, MAE/RMSE/R², sınıf matris/F1/ROC/PR, train-only fit,
test poison, group/time/group_time/ufuk ve yeni veride no-fit tekrar denetlenir.
“Aynı kütüphaneyi tekrar çağırdık” bağımsız referans kabul edilmez.

[OS offline kaynak denemesi](phase26/offline.json): farklı net namespace,
yalnız lo, route yok; native IPv4 errno101, IPv6 errno99. Spawn aynı namespace.
Beş gerçek QML/worker/proje/grafik/HTML/model/new CSV senaryosu tamamlanır;
kaynak hash assert'i ve yeni veride fit_calls=0 korunur. Host ağ arayüzleri
kapatılmadı; OS namespace içindeki süreçlerin ağa erişimi yoktur. Çevrimdışı
kurulum, fiziksel masaüstü veya gerçek bilgisiz kullanıcı testi değildir.

<a id="e26-s005"></a>
## E26-S005 — destek sınırları ve kalan kabul

Destek: kilitli Linux x86_64/Qt offscreen ve yerel Btrfs test ortamı;
ext4 CI hedefi/tarihsel kanıt ayrı. tmpfs kalıcı elektrik kesintisi garantisi
değildir. NFS/SMB/FUSE/sync klasörü yazma dayanıklılığı desteklenmez.
Hash kazara bozulmayı yakalar; dosyaların hepsini aynı kullanıcı yetkisiyle
eşzamanlı değiştirene karşı imza/sandbox güvenliği değildir. Bütün üçüncü
taraf C parser/library açıklarını kanıtlama iddiası yoktur.

Kaynak değişimi yakalanır veya açık değişmez snapshot kullanılır; source
sonradan değiştiyse yeniden seçim gerekir. Model paket trust listesi sabittir;
paketin yerel olması otomatik güvenilirlik değildir. Görev RAM/disk/wall
limitleri örneklemeli supervision ve worker OS limitleri taşır; cgroup değildir.
Bozuk ACTIVE'den kör geçmiş seçimi yapılmaz; dosyalar korunarak kontrollü ret
verilir. Eski sağlam commit'ler otomatik silinmez. Yeni insan/AT, minimum
donanım, temiz makine/offline kurulum ve uzak CI kabulü bu fazda yapılmadı.

<a id="e26-s006"></a>
## E26-S006 — kesilme noktaları ve parser maliyeti

`scripts/audit_reliability.py` gerçek JUnit kaydındaki her parametreli başarıyı
inceleme alanlarına ve `project_store.py` içindeki bütün20 checkpoint adına
bağlar. Eksik/başarısız/skip nokta kabul edilmez; statik envanter tek başına
runtime başarısı değildir. Kaynak/Parquet yazım callback'leri de ayrı gerçek
SIGKILL testleriyle eşlenir.

CSV/JSONL gerçek1MiB+ kayıt, JSON18 derinlik ve64MiB+ sparse belge,
XLSX64MiB+ açılmış ZIP parçası, ODS görev disk bütçesi retleri kaynak hash'i
değişmeden denenir. Bunlar adversarial kaynak tüketimi sınırlarıdır;
performans hedefi/minimum donanım ölçümü değildir. Ortak üç sınıf benchmark
Faz24 kanıtı olarak korunur.

## Nihai gerçek kontrol ve artefact kayıtları

Son kapı: **695 pytest/234.54s**,9 locked unittest;262 hedefli güvenlik,
proje/import/export/model/QML test. Önceki timer düzeltmesinden sonra ayrı
fresh koşuda694 pytest/233.33s de geçti; son ek parametre büyük-font recovery'dir.
[Son pytest](phase26/pytest.log), [önceki başarı](phase26/pytest-first-success.log),
[hedefli](phase26/targeted.log), [unittest](phase26/unittest.log).
[Komut/exit/tarih](phase26/checks.json), [gerçek JUnit](phase26/pytest.xml),
[15 alan/20 nokta eşlemesi](phase26/review.json).
Locked sync/docs/artifacts/learning/usability/Ruff check-format/entry exit0.
147 çevrimdışı makale/251 named form/189 tamamlanmış temel İngilizce mesaj;
katalog35 projects/project.recovery yardımı güncellendi.

[Kaynak ve kurulu wheel komutları](phase26/package-checks.json): iki farklı
OS network namespace içinde native IPv4/IPv6 retleri, ayrı spawn probe,
beş temel QML senaryosu/62 kayıtlı klavye eylemi ve gerçek recovery preview/
load/save/cancel geçti. [Kurulu offline JSON](phase26/wheel.json),
[normal kurtarma](phase26/offline-recovery.png),
[720×560/%200](phase26/offline-recovery-200-small.png).
Qt diyaloğu büyük yazıda pencereyi aşmaz; metin gerektiğinde kaydırılır.
[Kurulu giriş noktası](phase26/wheel-entry.log) GUI_SMOKE PASS;
[199 paket dosyası kaynak byte eşitliği](phase26/wheel-hashes.json).

Sistem Python3.14.7 unittest65 keşif/56 eksik bağımlılık import hatası ile
exit1 ([log](phase26/system-unittest.log)); başarılı kilitli runtime'la
karıştırılmaz. Sistem Python belge kapısı exit0. Hedefli koşu shutdown'da
PySide/Python GC159 uncollectable-object ResourceWarning yazdı; log saklıdır.
Çalışan shell timer'ı, engine destruction ve kaynak bütçesi regresyonları
geçti; bu uyarı bütün Python/native heap'lerde sıfır birikim iddiasına çevrilmez.
İlk lint hatası, fixture snapshot alanı eksikliği ve Qt çökmesi test başarısı
olarak sayılmadı. [Çökme](phase26/pytest-first-crash.log),
[GDB Qt timer izi](phase26/gdb-full.log) ve ilk kapı kayıtları korunur.
CI'ın tam pytest adımı JUnit üretir ve20 gerçek checkpoint eşlemesini
çalıştırır; yeni uzak CI koşusu yapılmadı. Bilinen altı bulgu teknik kapsamda
kapatıldı; önceki insan/AT/bağımlılık kabulleri açık, Faz26 sürüyor/deneysel,
Faz27 başlatılmadı. Kaynak birleşik prompt SHA256 değişmedi.

Son belge/yardım/artefact/Ruff/JUnit kapıları, matris güncellemesinden sonra
ayrıca exit0: [final-review](phase26/final-review.json)/[log](phase26/final-review.log).
[ENV-26](phase26/environment.json) kernel/CPU/RAM/FS/Python/Qt/exact paket,
kilit ve şema fixture hash'lerini taşır; minimum donanım kabulü değildir.
