# ADR-032 — Faz31 açık, salt okunur bağlantı kaynakları

2026-10-11; DEC-31-01 kullanıcının açık Faz31 talimatı yalnız bu fazı
seçer. Önceki insan/AT/donanım/dağıtım kabulleri kapanmaz; Faz32 başlamaz.
Python/PySide6/QML, tek Capability/SourceAdapter registry, ComputeBudget,
Provenance ve ProjectStore atomik yayını korunur.

## Yakalama ve kalıcılık

ConnectorSpec/v1 secret içermeyen sunucu, şema/tablo, bağlı filtre, keyring
referansı, CA, limit/timeout ve API/nesne seçimidir. Ağ/bağlantı sadece
Gelişmiş içindeki açık düğmelerle başlar; tablo keşfi ve veri okuması ayrı
eylemlerdir. Spawn worker Secret Service referansını bellekte çözer; secret
IPC sonucuna, loga veya projeye girmez. Çevrimdışı temel paket optional
connectors bağımlılıklarını import etmez; sessiz kurulum/indirme yapmaz.

Connector kaynakları aynı ADAPTERS içine bağlanır. Önce sınırlı tam sorgu/API
yakalanır; native Parquet ya da exact JSONL, SHA256 ve başlangıç/bitiş kaydı
oluşur. Önizleme200/ekran20; sonraki import ve refreshPreview bu değişmez
kopyayı okur, ağa tekrar gitmez. Kaynak tazeliği bilinmiyor olarak gösterilir.
Kaynak/parça/API kimlikleri locatorda, UUID RowId/SourceRecordId ayrı kalır.
Duplicate kaynak anahtarı disk SQLite unique tablosunda reddedilir.

Manifest7 source kaydı isteğe bağlı connector provenance alanıyla additive
genişler; eski kaynak kaydı aynı okunur. Yeni connector kayıtlarını eski
uygulamanın okuyacağı iddia edilmez. Kaynak kopyası zorunlu ve hash kontrollü
adopt edilir; dataset/metadata/ACTIVE tek yayındır. Source status `captured`
yerel kopya bütünlüğüdür, uzak kaynağın hâlâ aynı olduğu iddiası değildir.
Yeni bağlantı ayrı dataset yaratır; otomatik yenileme veya mevcut veri değişimi
yoktur. Credentials proje aktarımında yalnız referanstır; başka makinede yeniden
keyring kaydı gerekir. Eski snapshot credential/internet olmadan açılır.

## Veritabanı sınırları

Serbest SQL betiği çalıştırılmaz. Ordinary tablo/şema listesinden doğrulanmış
identifier, seçilmiş sütun, benzersiz null olmayan String/Integer kaynak anahtarı,
en fazla8 karşılaştırma ve ayrı bağlı değerlerle SELECT/ORDER BY/LIMIT üretilir.
Fonksiyon/DDL/DML/view/extension sorgusu sunulmaz. Limitli sıralı sorgu tüm
kaynak tablonun boyutu gibi sunulmaz; source_total_unknown/scope kayıtlıdır.

PostgreSQL: verify-full TLS (boş CA alanında system roots), yetkisiz rol; yönetici/create-role/replication/
bypass-RLS ve seçilmiş tablo yazma/schema-create yetkisi reddedilir. REPEATABLE
READ READ ONLY transaction, pg_current_snapshot ve statement_timeout kayıtlıdır.
Cancel watcher sürücü cancel çağırır; parent grace sonrası worker sonlandırabilir.
Parola açık keyring değeri veya explicit boş değerdir; PGPASSWORD/.pgpass
fallback'i boş, secretsiz geçici passfile ile engellenir. GSS, OAuth ve istemci
sertifikası auth kapalı; yalnız password/MD5/SCRAM veya sunucunun auth istemediği
dar yol kabul edilir. Secret bu geçici dosyaya yazılmaz.

MySQL/MariaDB: sertifika/hostname TLS, yalnız SELECT/USAGE grant'li hesap,
gerçek sunucu türü denetimi, yalnız InnoDB ordinary tablolar. REPEATABLE READ,
WITH CONSISTENT SNAPSHOT READ ONLY; sürücü socket timeout ve ayrı MySQL
max_execution_time/MariaDB max_statement_time kullanılır. Ortak parent iptal
grace'i bloklanan driver'ı sonlandırır. MariaDB testi MySQL kabulü sayılmaz.

DuckDB: yerel READ_ONLY dosya/transaction; external access ve otomatik
extension yükleme kapalı, native thread/RAM bütçesi ve interrupt watcher.
PostgreSQL numeric ve MySQL decimal precision≤38 açık; PG zamanlı timestamp
UTC/us, diğer naive zamanlar us. Desteklenmeyen SQL türü veya taşma durur;
unsigned/MySQL TIME gibi geniş varyantlar doğrulanmadan destekli sayılmaz.

## HTTP/REST ve S3

REST yalnız doğrulanmış HTTPS GET/JSON, seçilmiş records/next/total alanları
ve bire bir alan adı eşlemesi. Bearer token yalnız keyring'den; query auth,
cookie/interactive OAuth ve keyfi header yok. Yerel test HTTP'si yalnız açık
loopback tercihi. Redirect izlenmez; next same-origin, visited/page/row/byte
sınırları var. 429/502/503/504 ve geçici okumada en fazla5 retry; Retry-After
en fazla30s ve cancellable rate-limit/backoff. Sayfa tamamlanmadan kayıt
kabul edilmez; kaynak id duplicate, total değişimi/uyuşmazlığı ve snapshot
token değişimi yayını durdurur. Yanıt/exception gövdesi loglanmaz.

Token yoksa `observed_pages; no single-time snapshot guarantee`; total yoksa
atlanan kayıt kontrolü unknown. Aynı total tek-an kanıtı değildir. Seçilmiş
snapshot header sağlayıcı beyanıdır; gerçek sağlayıcı sözleşmesi ayrıca gerekir.
ETag/Last-Modified/page hash/okuma aralığı saklanır; auth echo metadata reddedilir.
Seçilmiş next alanı yanıtta yoksa ilk sayfa tamamlanmış gibi kabul edilmez.

S3 ayrı adaptör: tek explicit bucket/key GET/HEAD; SigV4 veya unsigned public
okuma, ortam credential zinciri kapalı. VersionId ya da HEAD/IfMatch validator,
boyut/timeout/limited retry ve redirect ret. ETag SHA256 sanılmaz; yerel kopya
ayrı SHA256 taşır. Upload/listing/delete veya otomatik credential discovery
yoktur; Parquet/JSONL/CSV/IPC nesneleri mevcut okuyucularla açılır. CSV ve JSONL
özel parse ayarı olan nesneler bu dar GUI'de defaults sınırındadır.

## Ortam ve resmî kaynaklar

Connectors extra: psycopg[binary]3.3.6, PyMySQL1.2.3, keyring25.7.0,
boto3/botocore1.43.111, DuckDB1.5.6; gerçek resolver/metadata ile kilitlendi.
Temel bağımlılıklar güncellenmedi. Linux Secret Service dışında plaintext,
null veya üçüncü parti backend fallback'i kabul edilmez.

2026-10-11 incelenen birincil kaynaklar:
[psycopg transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html),
[libpq auth/TLS](https://www.postgresql.org/docs/current/libpq-connect.html),
[PostgreSQL transaction](https://www.postgresql.org/docs/current/sql-set-transaction.html),
[MySQL consistent read](https://dev.mysql.com/doc/refman/8.4/en/commit.html),
[PyMySQL TLS](https://pymysql.readthedocs.io/en/latest/modules/connections.html),
[DuckDB güvenlik](https://duckdb.org/docs/stable/operations_manual/securing_duckdb/overview),
[Secret Service](https://keyring.readthedocs.io/en/stable/),
[S3 GetObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html).
Native test sunucuları /tmp altında kullanıcıya ait sentetik ortamda kurulur;
sistem servisi/kullanıcı veritabanı değiştirilmez. Gerçek kabul ve açık sınırlar
[PHASE31](../evidence/PHASE31.md) içinde, yöntem başına matrise bağlanır.
