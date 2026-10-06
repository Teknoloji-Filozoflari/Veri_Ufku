# Faz05 — CSV/TSV içe aktarma

2026-10-06; olgunluk deneysel; yalnız Faz05. Gereksinim ana kaydı [REQUIREMENTS_MATRIX](../REQUIREMENTS_MATRIX.md); [ADR-008](../adr/008-delimited-import-phase05.md). Gerçek masaüstü/native seçici, yeni remote CI ve minimum donanım ayrı doğrulanmadı. Kaynak belgenin tamamı sonraki faz yetkisi değildir.

<a id="e05-environment"></a>

ENV-05: CachyOS x86_64, Linux7.2.9/glibc2.44, CPython3.13.15, PySide6/Qt6.11.2, Polars/runtime-32 2.0.0, mevcut uv.lock. Geliştirici Ryzen7 8845HS/32GB; minimum8GB kabulü değildir. Qt offscreen/software ve izole XDG. Pytest geçici dizinleri /tmp; ayrıca gerçek GUI tam import ölçümü yerel NVMe Btrfs proje alanında yapıldı. [Ortama bağlı ham ölçüm](phase05-headless.json), [komut çıktıları](phase05-checks.txt), phase05-source.sha256 kod/fixture kayıtları. Yeni bağımlılık veya ağ çalışma gereksinimi yok.

<a id="e05-gui"></a>

F05-S001/F05-S002: src/veri_ufku/ui/imports.py, ui/qml/ImportPanel.qml, ui/qml/Main.qml, app.py; tests/test_import_gui.py, ENV-05, 2026-10-06. Gerçek QML Veri ekranı Dosya seç/FileDialog CSV/TSV filtresi ve DropArea bağlıdır. Qt QMimeData/QDragEnterEvent/QDropEvent gerçek pencereye gönderilerek bir TSV'nin preview modeline ulaşması doğrulandı. Çoklu dosya anlaşılır reddedildi. QML FileDialog selectedFile/accepted sinyaliyle yerel CSV yolu gerçek importer/model akışına ulaştı. Native dosya seçicinin kullanıcı masaüstü etkileşimi ayrı açıktır; bu test native seçiciyi kullanmış sayılmaz.

Ayraç, encoding, başlık kaydı, ondalık/binlik, null işaretleri, tarih biçimi/saat dilimi ve stop/quarantine gerçek ImportSettings alanlarına gider. Ayar/tür değişimi valid önizlemeyi geçersiz kılar; aynı kopyayı yeniden önizleme sonrasında import açılır. QML düğmesi üzerinden gerçek spawn worker ve proje yayını çalıştı. İlk malformed preview'den karantinaya geçip aynı yakalanmış kopyayı yeniden önizleme/import test edildi. Kalıcı dataset sürümü/sayım/karantina özeti metadata açılışıyla yeniden görünür.

Model QAbstractTableModel + Qt TableView; en fazla200 incelenen kayıt ve sınırlı örnek açıklaması; her gerçek dataset hücresine widget oluşturulmaz. Başsız [geniş form](phase05-headless-1366-light.png), [geniş tablo](phase05-headless-1366-light-table.png), [dar %200 koyu](phase05-headless-720-dark.png), [dar form](phase05-headless-720-dark-form.png), [dar tablo](phase05-headless-720-dark-preview.png), [dar kayıt eylemi](phase05-headless-720-dark-table.png) gerçek render'dır. Ajan görüntüleri inceledi; dar pencere alanları tek sütuna geçti ve başlık/düğmeler sarıldı. Gerçek Wayland/X11 veya assistive teknoloji kabulü değildir.

<a id="e05-parser"></a>

F05-S003/F05-S004/F05-S006: src/veri_ufku/importers/delimited.py, worker.py; tests/test_delimited.py ve tests/fixtures/delimited/{reference_utf8.csv,reference_cp1254.csv,reference.tsv}, ENV-05, 2026-10-06. Elle belirlenen bağımsız beklentiler: 0012 ve21 haneli kimlik metin olarak aynı; Çağrı/Işıl/İğdır Şişli; Decimal1234.50/0.25; date2026-10-06/07; tırnakta iki;parça ve iki\nsatır; TSV3.5/null. UTF-8, cp1254 ve aynı Türkçe örnekte ISO-8859-9 gerçek okuma; yanlış UTF-8 decode durdu. Boş/tekrar/rezerve başlık adlandırma/özgün başlık, başlıksız ilk kaydın korunması ve boş/header-only dosyada başarısız import test edildi.

Int64 sınır/kesir, leading zero, Float64 uzun integral/inf/underflow, Decimal ölçek ve kapasite, binlik gruplama, açık timezone ve DST ambiguity ret testleri vardır. Türlerin varsayılanı metin; öneri uygulanmaz. Önizlemedeki200 geçerli kayıttan sonra gelen tip hatası tam okumayı durdurdu. Önizleme/import aynı settings roundtrip; sonuç metadata, yardım/seed, ColumnId ve settings kapat/aç ile aynı kaldı.

Raporlu karantina örneği tam sayımda2 kabul/3 bozuk: fazla sütun, tür hatası ve açık tırnak/EOF. Beklenen ordinal3/4/6, satır aralıkları3–3/4–4/6–7, özgün raw ve ayrı SourceRecordId bağımsız olarak doğrulandı. Hatalı satır atlama yoktur. Stop politikası yayın yapmaz; karantina ayrı Parquet artifact olarak saklanır.

<a id="e05-integrity"></a>

F05-S007: aynı importer + storage/project_store.py::publish_import ve project_model.py; test_source_modified_after_preview_imports_explicit_immutable_copy, test_source_modified_during_capture_rejected, test_capture_tampered_during_read_no_mixed_success, gerçek GUI immutable kaynak akışı; ENV-05, 2026-10-06. Önizleme sonrası kaynak başka sürüme değiştirildi: eski doğrulanmış kopyadan açıkça import edildi, eski değerler/fingerprint korundu, kaynak status changed ve taşınabilir eski kopya doğru kaldı. Kaynak yakalama sırasında mutasyon reddedildi. Worker sonrası aynı satır sayılı Parquet değer mutasyonu da parent hash kontrolünde reddedildi; ACTIVE aynı kaldı. Okunan özel kopya mutasyonu post-read hash kontrolünde reddedildi; karışık dataset yayımlanmadı. UI kopya zamanı/fingerprint ve güncel kaynak için yeniden seçim gereğini gösterir.

İki aynı içerikli kaydın RowId ve SourceRecordId değerleri farklı; UUIDv4 tahsis edilir, ordinal/hash kimlik değildir. SourceSnapshotId, sütunlar için ayrı ColumnId, kaynak satır aralığı ve shared Provenance/full/config_revision/seed/backend bilgisi saklanır. Yeni import yeni kimlik alır; proje yeniden açma Parquet haritasını korur.

<a id="e05-publication"></a>

F05-PUBLISH/F05-CANCEL: tests/test_delimited.py ve tests/test_import_gui.py, ENV-05, 2026-10-06. Yeni gerçek import için2 kopyalama sınırı +14 artifact/SQLite/manifest/ACTIVE sınırı =16 gerçek SIGKILL alt süreci; returncode=-SIGKILL doğrulandı. ACTIVE geçişinden önce önceki sağlam state, sonra tamamlanmış dataset tüm bağlı artifact/hash/sayım/şema ile açıldı. Faz04 iki yazıcı, readonly, staging temizliğinin bağlı artifact'ı koruması ve30 diğer SIGKILL regresyonları korunur. Şema2 bağımsızdır; schema1 fixture readonly açılışında ACTIVE/SQLite byte'ları aynı, açık save sonrasında2/migration, eski manifest aynı. Şema0→2 farklı kaydet migrasyonu ve bilinmeyen gelecek şema ret regresyonu geçti.

Gerçek180000 kayıt CSV spawn import sürerken Qt timer en az15 tick aldı; proje kapat/farklı kaydet engellendi. QML İptal düğmesiyle süreç3s test sınırı içinde durdu; kaynak SHA256 ve önceki ACTIVE byte'ları aynı, dataset yok. Ayrı metadata_committed iptal testi SQLite'da hazırlanmış commit bulunmasına rağmen eski ACTIVE/state'in açıldığını doğrular. Başarı yalnız parent'ın atomik yayını sonrasında görünür. ACTIVE sonrası iptal eski kaydı geri yazmaz.

<a id="e05-help"></a>

F05-S005: src/veri_ufku/learning/content/tr.json içerik sürümü4, toplam21 makale; import-csv ve altı kavram rehberi. Capability import.csv/import.tsv ortak kayıt/yardım bağı; QML seçeneklerinde ayraç/encoding/başlık/tarih/ondalık/bozuk kayıt F1 bağları. check_learning katalog/QML/capability ve kapalı try_action allowlist kontrolüdür. Yardım ağ istemez ve veri değiştirmez.

<a id="e05-checks"></a>

Son kilitli pytest **150 passed**; kilitli unittest9 belge testi; sync --locked --group dev, sistem python3 check_docs, check_artifacts/check_learning, Ruff check/format, kurulu giriş noktası GUI_SMOKE PASS ve PHASE05_HEADLESS PASS geçti. Gerçek komut/süre/çıktılar phase05-checks.txt içinde. Wheel offline/no-build-isolation olarak locked build araçlarıyla oluşturuldu; /tmp/veri-ufku-f05-final-installed içine --no-deps kuruldu. Ayrı /tmp çalışma dizininden PYTHONPATH yalnız kurulan pakete yöneltildi; veri_ufku.__file__ target içinde doğrulandı, paket QML/21 makale kaynakları yüklendi, gerçek spawn CSV import/şema2/kapat-aç geçti: PHASE05_INSTALLED_WHEEL_IMPORT PASS. Runtime bağımlılıkları mevcut locked .venv'den kullanıldı; temiz Linux kurulum veya tüm bağımlılıkların ayrı installer'ı sayılmaz. Başlangıç kontrollerinde QML sözdizimi, tuple→QVariant list aktarımı ve eski Faz02 availability beklentisi düzeltildi. Bir ara tüm regresyonda144 işlev testi geçti, belge testi henüz olmayan PHASE05.md bağlantısı nedeniyle başarısız oldu; bu ara koşu tam başarı sayılmadı.

<a id="e05-limits"></a>

Ölçüm yalnız geliştirici/başsız ortamında n=1 sıcak fixture ve180000 kayıt tam import/iptaldir; ham JSON gerçek sayıları taşır, p95/minimum donanım/1GiB benchmark iddiası yok. Kaynak1GiB, sütun256, kayıt1MiB ve budget sınırları UI'de görünür. Native sink sırasında geçici alanın anlık peak hard quota garantisi yok; chunk/son kontrol ve parent süre/iptal sonlandırması var. Sert ölüm cache dizinleri global olarak silinmez. Ağ FS, eşzamanlı sync klasörü, güç kesintisi, tam offline installer, yeni remote CI ve native seçim/bırakma yolu ayrıca doğrulanmadı; aşağıdaki kullanıcı bildirimi temel CSV/kaydet/yeniden aç akışıyla sınırlıdır. Analiz/tablo profil ve Faz06+ mevcut değildir.

<a id="e05-user-roundtrip"></a>

## Kullanıcının CSV ve proje yeniden açılış kontrolü

2026-10-06; F05-USER-ROUNDTRIP; ENV-USER-05. Kullanıcı eklediği CSV'nin alındığını, klasöre kaydedildiğini ve projeyi kapatıp yeniden açınca CSV'yi projede gördüğünü bildirdi. Bu bildirim temel CSV içe aktarma/kaydetme/yeniden açılış akışının manuel kabulüdür. CSV içeriği/boyutu/encoding'i, tam proje yolu, başlangıç komutu, backend/binary hash ve dosya seçme veya bırakma yöntemi bildirilmedi; ENV-05 ile birebir eşitlik varsayılmaz. Tür/değer hassasiyeti, karantina, iptal ve kaynak değişimi kullanıcı tarafından ayrıca doğrulanmış sayılmaz; otomatik kanıtları ayrı kalır.
