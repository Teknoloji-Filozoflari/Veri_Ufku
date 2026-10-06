# ADR-003 — Değişmez proje kayıtları, tek yayın ve tek yazıcı

2026-10-06; kabul edilmiş tasarım; uygulanacak Faz 04, snapshot/import Faz 05. Kaynaklar: [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html), [SQLite locking](https://www.sqlite.org/lockingv3.html). SQLite transaction'ı dış Parquet/manifest dosyalarını atomik yapmaz; bu nedenle tek commit pointer gereklidir.

## Yayın protokolü

Yerel ext4/Btrfs üzerinde aynı mount/proje dizininde staging; yeni snapshot/lineage/result ve manifest önce burada hazırlanır. Kaynak dosya yerinde yazılmaz. İş worker'ı çıktı verir; tek servis yayını yapar.

1. Tek yazıcı kilidi tutarken base commit/config/version doğrula; disk önkontrolü ve reserve uygula.
2. staging/<transaction_id> içinde yeni artefact yaz. Boyut/hash, Parquet schema/row counts/lineage, manifest format/referanslar doğrula. Dosyaları flush+fsync yap.
3. Artefact'ları değişmez son isimlerine aynı dosya sisteminde rename et; ilgili dizinleri fsync. Mevcut dosyayı aynı id ile ezme; hash çakışmasında dur.
4. metadata.sqlite transaction'ında commit_id altında append-only version kayıtlarını hazırla; `synchronous=FULL`, başlangıçta DELETE journal. Manifest yeni commits/<id>/manifest.json içine geçer; hash doğrulanır, dosya/dizin fsync. SQLite henüz bu commit'i aktif olarak yorumlamaz.
5. ACTIVE.tmp dosyasına {commit_id,manifest_sha256,format_version} yaz, fsync; ACTIVE üstüne atomic rename; proje dizinini fsync. **Bu tek yayınlama noktasıdır.** SQLite aktif sorguları ACTIVE commit_id ile bağlıdır; başka bağımsız active pointer yok.
6. Eski commit durur; bağlı okuyucular açık sürümünü kullanır. Staging temizliği ayrı, referanslı dosyaları silmez. UI yalnız publication succeeded aldıktan sonra sürüm değiştirir.

SQLite commit sonrası ACTIVE öncesi çöküşte eski ACTIVE sağlam kalır; yeni commit orphan olarak kayıtlıdır. ACTIVE sonrası yeni kayıt/dosyalar önceden dayanıklı olmalıdır. ENOSPC/hash/izin/fsync hatası publish öncesinde fail; eski ACTIVE değişmez. ACTIVE rename sonrası fsync hatası publication durability_unknown: yeni veri başarısı iddia edilmez, iki commit korunur ve açılış doğrulaması gerekir; son sağlam pointer'a otomatik kör geri yazma yok.

Açılış ACTIVE+manifest+SQLite+artefact hash tutarlılığını doğrular. Yarım staging güvenli karantinaya alınır; yalnız referanssız geçici veriler silinir. ACTIVE bozuksa son sağlam commit adayları listelenir, kayıp yaratabilecek seçim kullanıcıya sorulur. Migration orijinal commit'i koruyarak yeni kopyada ve versioned migration record ile; unsupported future version salt okunur metadata veya açık ret.

## Tek yazıcı / path

Proje kökü canonical path ve device/inode üzerinden açılır. Sabit `.writer.lock` dosya descriptor'ı `flock(LOCK_EX|LOCK_NB)` ile tutulur; PID/boot_id tanılama içindir, kilit otoritesi kernel lock'tır. Lock dosyası aktifken unlink edilmez; aktif yazıcının kilidi PID/timeout bahanesiyle kaldırılmaz. Process exit kernel kilidini bırakır. İkinci süreç committed snapshot üzerinden salt okunur açabilir; basit ilk uygulama anlaşılır ret seçebilir ve capability bildirir. Lock edinmeden recovery/cleanup/migration yok. Depo bütün write yollarını aynı kilide bağlar; yalnız SQLite lock'a güvenmez.

Kaynak/hedef canonical equality + samefile(device/inode) + symlink çözümü ile aynıysa export engellenir; overwrite ayrı kullanıcı hedef onayı ister. Proje içi artefact path relatif ve root altında, `..`/symlink escape reddedilir. Kaynak symlink seçilirse çözülen inode snapshot'a bağlanır; hedef symlink/dizin değişimi TOCTOU descriptor tabanlı kontrol edilir. Ağ FS (NFS/SMB/FUSE belirsiz), cross-mount rename ve eşzamanlı sync klasörlerine dayanıklılık garantisi yok; ilk sürüm yazma reddi veya yerel kopya istenir. Tanınmayan FS varsayılan supported kabul edilmez. /tmp bu ortamda RAM tmpfs, büyük staging burada yapılmaz.

## Kaynak değişimi

Varsayılan inceleme için kaynak kopyasının projede tutulması kapalıdır, fakat doğrulanmış değişmez çalışma snapshot'ı gereklidir; maliyet UI'de açık. Önizleme kaynak sabit snapshot'ından alınır, import aynı snapshot/config'i kullanır. Kullanıcı özgün dosyayı sonradan değiştirse o önizleme sabit kopyayı import eder ve snapshot zamanını açık gösterir; güncel kaynak istenirse tekrar snapshot+önizleme.

Ürün kendi immutable dosyasında hash/size/fsync'i korur. Dış dosyadan snapshot yakalarken platform immutable CoW snapshot veya güvenilir producer/advisory lock altında okuma tercih edilir. Yoksa open fd inode/size/stat + iki tam içerik hash'li okuma karşılaştırması değişimi tespit eder; yalnız mtime yeterli değildir. Bu kontrol kötü niyetli/eşzamanlı yazara matematiksel değişmezlik garantisi değildir. Kaynak yazılıyor olabileceğinde başarılı import verilmez; “Yazmayı durdurun / sabit kopya seçin” mesajı ve yeniden önizleme. Tutarlı yakalama doğrulanmadan mixed bytes dataset'i publish edilmez. Geçici kontrollü kopya projeye dönüştürülen Parquet snapshot'ına bağlanır; asıl dosyanın ayrıca saklanması yalnız kullanıcı tercihi.

Durability sınırı: yerel FS rename/fsync ve depolama flush davranışına bağlı; hatalı disk/firmware veya uzak sync mutlak garanti değildir. Her adımda crash/ENOSPC/failure injection, iki süreç, symlink/samefile ve değiştirilmiş kaynak testleri yapılmadan dayanıklı özelliği kararlı sayılmaz.
