# Faz 04 — proje kaydı ve kurtarma

2026-10-06. Yalnız Faz04 uygulandı. Faz05 içe aktarma/önizleme ve sonraki analitik fazlar başlamadı. Olgunluk deneysel; gereksinim ana kaydı [REQUIREMENTS_MATRIX](../REQUIREMENTS_MATRIX.md). Tasarım ve sınırlar [ADR-007](../adr/007-project-store-phase04.md).

<a id="e04-environment"></a>

ENV-04: CachyOS x86_64, Linux7.2.9/glibc2.44, CPython3.13.15, PySide6/Qt6.11.2, SQLite3.53.1, Polars/runtime-32 2.0.0, uv0.12.23. Ryzen7 8845HS/32GB; önceki ENV-01 donanımı. Testler yerel NVMe Btrfs üzerinde izole geçici proje dizinlerinde; önceki geliştirme denemeleri /tmp tmpfs üzerinde de geçti. Qt offscreen/software, izole XDG. Exact lock/fixture SHA256 ve gerçek render akışı [phase04-headless.json](phase04-headless.json). Kaynak kod SHA256 kaydı phase04-source.sha256; kilitli kontroller [phase04-checks.txt](phase04-checks.txt).

Yeni Polars dependency sandbox DNS başarısızlığından sonra kullanıcı onaylı `uv add polars`, ardından `uv add polars==2.0.0` ile kuruldu/kilitlendi. Kurulu metadata Python>=3.10; runtime wheel gerçek roundtrip ile doğrulandı. Paket içindeki MIT lisansı korundu. Yeni bağımlılık genel analitik yöntem kabulü değildir.

<a id="e04-projects"></a>

F04-S001: storage/project_model.py, storage/project_store.py, ui/projects.py, ui/qml/ProjectPanel.qml, app.py (src/veri_ufku altında); tests/test_projects.py, tests/test_project_gui.py; ENV-04, 2026-10-06. Gerçek QML Yeni proje/path dialog/oluştur düğmesi, proje adı/seed/yardım tercihi, Kaydet, kapat/aç, Farklı kaydet ve son projeler test edildi. İkinci açılışta state eşitliği; kopyada state eşitliği; mevcut/symlink/aynı hedef reddi doğrulandı. UI'nin adı, kayıt kimliği ve dirty/salt okunur bağlamı gerçektir. Başsız ekranlar: [geniş açık](phase04-headless-1366-light.png), [dar koyu %200](phase04-headless-720-dark.png), [dar kaydırılmış kart](phase04-headless-720-dark-scrolled.png). Ajan görsel olarak inceledi; Frame yükseklik çakışması düzeltildi. Bunlar gerçek Wayland veya yeni kullanıcı testi değildir.

<a id="e04-state"></a>

F04-S002: aynı storage yolları ve test_roundtrip_save_as_sources_and_autosave; ENV-04, 2026-10-06. SQLite metadata + şema1 manifest, kaynak SHA256/boyut/path/kopya URI, import ayarları, dataset/version UUIDv4, bağlı işlem/sonuç kayıtları, yardım derinliği ve seed roundtrip eşitliği geçti. Gerçek Parquet `[1,2,null]`, iki aynı metin kaydı ve string kolonu yazıldı; bağımsız beklenen kayıtlarla okuma karşılaştırıldı. Açılışta Parquet şema/satır ve tüm artifact hash/boyut kontrolü var. Analiz motoru veya dataset importu uygulanmadı; testler depo girdisini kurar ve sahte UI analizi üretmez.

<a id="e04-sources"></a>

F04-S003: stage_source/source_statuses/relink/results_status, GUI kaynak/kopya kutusu ve yeniden bağla; test_roundtrip_save_as_sources_and_autosave, test_metadata_open_never_reads_external_source, test_source_changes_during_capture_are_rejected, test_project_io_thread_responsiveness_and_source_watcher; ENV-04, 2026-10-06. Metadata açılışında dış kaynak okuma fail-fast yapılmasına rağmen proje açıldı. Eksik kaynak metadata/snapshot'ı bozmadı. Aynı içerikli başka dosyaya yeniden bağlama geçti; değişmiş içerik reddedildi, eski sonuç güncel=false. Kopya/özgün dosya byte'ları kontrol edildi. Okuma sırasında test üreticisinin kaynağı değiştirmesi yakalandı; publish olmadı. Sonuç UI metni kalıcı dataset_version_ids taşır; kaynak watcher ile değişmiş durum arayüzde görüldü. Kaynak ve Parquet işleme UI'den ayrı I/O thread'de; gerçek Qt timer olayları I/O beklerken devam etti. Kaynak açma import/analiz çalıştırmaz.

<a id="e04-recovery"></a>

F04-S004/F04-S005: save/restore_autosave/open ve schema0 fixture; tests/test_projects.py, tests/test_project_gui.py; ENV-04, 2026-10-06. Manuel ACTIVE byte'ları autosave sırasında aynı kaldı. Açılış manuel kaydı getirdi; açık kurtarma isteği draft'ı yükledi, manuel kayıt hâlâ değişmedi. Yeni manuel kayıttan eski autosave'e dönme reddedildi, mevcut unsaved draft korundu. Kapanış dirty dialogu pencereyi açık tuttu; kayıt sürerken kapanış engellendi. Gelecek şema99, bilinmeyen alan, negatif seed, artifact traversal/oversize, artifact symlink ve bozuk ACTIVE kontrollü reddedildi. Başarısız yayın retry testi geçti. İlk şema0 fixture salt okunur açıldı ve şema1 kopyaya göç etti; orijinal SQLite/manifest/ACTIVE byte eşit kaldı. Arşiv kullanılmadı. Zorla sonlandırmada son sağlam ACTIVE korunması aşağıdaki ayrı kanıttır. Kullanıcının ayrıca bozduğu ACTIVE'den kör commit seçme yoktur.

<a id="e04-publication"></a>

F04-S006: CRASH_POINTS 14 kritik sınır × kaynak kopyası ve Parquet = 28 gerçek subprocess SIGKILL; ek iki SIGKILL gerçek kaynak/Parquet stream.write çağrısı sırasında = 30 zorla sonlandırma senaryosu. SQLite insert öncesi/sonrası commit, manifest yazma/fsync/rename/dizin fsync, ACTIVE yazma/fsync/replace/kök fsync sınırları ayrı parametreli testlerdir. Test her öldürülen süreç için `-SIGKILL` doğrular, kontrollü eski kilit kurtararak yeniden açar; ACTIVE replace öncesi eski kayıt, sonrası tüm bağlı dosyaları tamamlanmış yeni kayıt açılır. Eski Parquet dosyası okunabilir ve özgün kaynak byte'ları korunur. Açılış tüm bağlı metadata/artifact'ları doğrular. SQLite hot journal açılışta kilit altında rollback edilir. Test kodu tests/test_projects.py; ortam ENV-04 Btrfs ve geliştirme tmpfs, 2026-10-06. SIGKILL güç kesintisi testi değildir.

İki gerçek Python sürecinde kernel kilidi eldeyken ikinci süreç readonly; save ve recovery yazıcıyı devre dışı bırakamadı. İlk süreç SIGKILL sonrası marker normal açılışı readonly yaptı; açık recover_lock ile kernel kilidi edinilerek kayıt devam etti. Ek tests/test_project_gui.py::test_two_application_instances_keep_second_readonly, iki gerçek QQmlApplicationEngine/pencere üzerinde ikinci Kaydet disabled olduğunu ve owner kayıtlarının reader pinned state'ini değiştirmediğini doğruladı.

staging'deki bağlı artifact hard-link'i karantinaya taşınırken snapshots/sources hedefi korunup okunabildi. Kök dizini değiştirilerek symlink'e çevrildiğinde eski writer durdu. Farklı kaydet son hedefe geçmeden hedef yarışta oluşturuldu: renameat2 NOREPLACE hedefteki user-content'i korudu, asıl ACTIVE değişmedi. ACTIVE rename sonrası fsync hatası dayanıklılık belirsiz diye raporlandı; iki commit korundu ve yeniden açılış doğrulandı. NFS mock ile yazma reddi doğrulandı; gerçek NFS/SMB/FUSE testi veya destek iddiası yok.

<a id="e04-checks"></a>

Son kilitli pytest: **100 passed in 23.69s**, yerel Btrfs üzerinde. Kilitli unittest 9 belge testi, kurulu giriş noktası GUI_SMOKE PASS, PHASE04_HEADLESS PASS ve offline wheel build exit0. Gerçek son kontroller ve sonuçları phase04-checks.txt içinde: kilitli dev kurulumu, python3/check_docs ve kilitli check_docs/check_artifacts/check_learning, Ruff check/format, offscreen/software pytest ve kurulu veri-ufku --smoke-test; kilitli unittest discovery ve headless proje ölçüm betiği. Sistem Python3.14 ile doğrudan unittest discovery önce 8 import hatasıyla başarısız oldu; sistem ortamında veri_ufku/Polars kurulu değil. Bu çalıştırma başarılı sayılmaz; kabul kilitli CPython3.13 ortamındaki gerçek pytest/test ve unittest kontrollerine dayanır. unittest yalnız 9 belge testini çalıştırır; pytest işlev testlerinin yerine geçmez.

Sınırlar: gerçek masaüstü/native dosya seçici, yeni kullanıcı kabulü ve yeni remote CI yapılmadı. ext4 bu oturumda ayrıca denenmedi; tmpfs kalıcı disk değildir. Ağ ve eşzamanlı sync klasörlerine dayanıklılık yok. Disk güç kaybı, firmware ve tam offline installer doğrulanmadı. Kaynak okuma/kopya için iki hash + stat eşzamanlı düşmanca yazara matematiksel snapshot garantisi değildir. Geçmiş/karantina otomatik silinmez. Proje kopyası aktif state/artifact'ları taşır; eski commit ağacı taşınmaz.

<a id="e04-user-projects"></a>

## Kullanıcı masaüstü proje kontrolü

2026-10-06; F04-USER-PROJECTS; ENV-USER-04. Kullanıcı önce `/home/Belgeler` yoluyla genel hata gördüğünü, ardından kendi kullanıcı klasöründe (`/home/s-oktay/belgeler` olarak bildirdi) yeni proje oluşturduğunu, açtığını, isim değişikliğini kaydettiğini ve projeyi kapattığını doğruladı. Tam proje alt dizini, başlangıç komutu, Qt backend ve binary hash ayrıca bildirilmedi; ENV-04 ile birebir eşitlik varsayılmadı. Bu bildirim sayılan eylemlerle sınırlı manuel kabul kanıtıdır. Native dosya seçici, farklı kaydet, kaynak/kurtarma ve aynı projede iki masaüstü uygulaması ayrıca kullanıcı tarafından doğrulanmış sayılmaz. F04-USER-DESKTOP kapsamındaki native seçim kontrolü açık kalır.

<a id="e04-path-fix"></a>

## Yeni proje yol hatasının açıklanması

2026-10-06; F04-FIX-PATH; ENV-04. `/home/Belgeler` kullanıcıya ait Belgeler dizini değildir; kullanıcı kendi dizinine geçince temel proje akışının çalıştığını bildirdi. Kullanıcının ilk işletim sistemi exception/errno değeri alınmadı; izin hatası kesin ölçülmüş sayılmaz. Yerelde olmayan üst klasörle aynı eski genel mesaj yoluna giren FileNotFoundError tekrarlandı.

storage/project_store.py yeni hedefin üst dizinini oluşturmadan önce kontrol eder; eksik/dosya olan üst yol için açıklayıcı mesaj verir. ui/projects.py izin, salt okunur konum, boş alan/kota ve SQLite hata türlerini ayrı açıklar; ham exception mesajı/satır içerikleri gösterilmez. ProjectPanel.qml Yeni proje/Farklı kaydet diyaloğuna Klasör seç eklendi; var olan klasörü seçince Yeni_Proje alt yolu önerilir. Başarısız asenkron işlemde diyalog açık kalır ve hata yanında görünür; kullanıcı yolu düzelterek devam eder. Yardım katalog/makale sürümü güncellendi.

Regresyon: tests/test_project_gui.py::test_new_project_path_error_stays_visible_and_can_be_corrected gerçek QML diyalog/düğme üzerinden yanlış yol→açık hata→düzeltilmiş yol→başarılı proje akışını doğrular; test_project_error_messages_distinguish_path_permissions_and_disk izin/disk/SQLite ayrımını ve hassas ham mesajın gösterilmediğini denetler. Son kontroller [phase04-path-fix-checks.txt](phase04-path-fix-checks.txt); yeni kod/hash kaydı phase04-path-fix-source.sha256. Native klasör seçim penceresinin masaüstü etkileşimi bu başsız kontrolle kabul edilmiş sayılmaz.

Yol düzeltmesinin son yerel kontrolü: 102 pytest testi, 9 kilitli unittest belge testi, check_docs/check_artifacts/check_learning, Ruff check/format, kilitli dev sync ve kurulu giriş noktası GUI_SMOKE PASS geçti. Komutlar ve gerçek sonuçlar phase04-path-fix-checks.txt içinde; bu düzeltme sonrası yeni remote CI veya native dosya seçici masaüstü testi yapılmadı.
