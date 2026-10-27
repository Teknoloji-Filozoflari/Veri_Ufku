# Faz31 — salt okunur bağlantı ve ağ kaynakları

2026-10-11; DEC-31-01 açık kullanıcı Faz31 talimatı. Yalnız bu faz seçildi;
önceki kabul açıkları kapanmaz, Faz32 başlamadı. Ortam ENV-31: CPython3.13.15,
Qt/PySide6 6.11.2, Linux x86_64; başsız offscreen/software, izole geçici XDG.
[Sözleşme ve dar varyantlar](../adr/032-connectors-phase31.md).

<a id="e31-connectors"></a>
## Adaptör başına gerçek ortam

İlk dilim PostgreSQL18.6 ve TLS HTTPS test sunucusunda tamamlandı; literal
native değer/metadata, rol/yazma reddi, eşzamanlı değişimde snapshot,
timeout/iptal ve retry/tutarsız sayfa testleri ayrı çalıştı.
Sonra MySQL8.4.11, MariaDB13.0.2, yerel DuckDB1.5.6 ve S3 uyumlu
SeaweedFS4.48 sunucuları ayrı sentetik fixture ile sınandı. Secret Service51.1
ayrı D-Bus oturumu/XDG içinde gerçek şifreli keyring saklama testidir.
Setup yazıları yalnız bu sentetik sunuculara aittir; connector sorguları salt
okunur, ağ eylemleri GET/HEAD'dir. Kurulum/depolama gerçek kullanıcı kaynağına
yazmadı. Tam paket/regresyon ve son kanıt kayıtları aşağıda tamamlandı.

<a id="e31-consistency"></a>
## Tutarlılık, kayıt kimliği ve güvenlik

PostgreSQL tekrar okunabilir salt okunur transaction, MySQL/MariaDB ayrı
InnoDB snapshot, DuckDB READ_ONLY transaction ayrı tanıklardır.
API duplicate/gap/token mutation/loop/cross-origin/redirect ret; total/token
yokluğunda dürüst observed_pages/unknown kayıtları vardır. Kaynak id locatorda,
UUID kimlikler ve immutable hash/başlangıç-bitiş/limitli scope kalıcıdır.
Önizleme sonrası import ve proje reopen ağ eylemi yapmaz. Bozuk capture veya
iptal önceki ACTIVE'yi değiştirmez. Şifre ve bearer/S3 secret kaynak error/log/
settings/proje exportuna girmez; Secret Service dışı fallback yoktur.

<a id="e31-learning"></a>
## Öğren ve GUI

Katalog47/162: connector-connection/query/snapshot/pagination/freshness.
Gelişmiş → Veritabanı/API/nesne depolama → tablo/şema keşfi veya açık okuma →
snapshot önizlemesi → mevcut İçe aktar düğmesi. Kullanım koşulları/auth sınırı,
TLS/keyring referansı ve tazelik/tek-an belirsizliği görünür. F1/Escape yardımı
ve eski snapshot'ın çevrimdışı açılışı mevcut yol üstündedir.

<a id="e31-final"></a>
## Son kontroller ve kabul sınırı

Nihai tam regression **795 pytest/440.687s**, sıfır failure/error/skip:
[JUnit vaka kimlikleri](phase31/pytest.xml), [gerçek konsol](phase31/pytest.txt).
Son **34 odaklı connector testi** ayrıca başarılı:
[ayrı JUnit](phase31/targeted.xml), [konsol](phase31/targeted.txt).
**14 kilitli unittest** geçti; sistem Python3.14.7 **79 discovery/65 import
hatasıyla başarısız** ayrı kayıttır. [Başarılı](phase31/unittest.txt),
[başarısız](phase31/system-unittest.txt). Ortamı olmayan connector skip'i
bu gerçek yerel koşuda yoktur; başka ortamda skip kabul sayılmaz.

[Kaynak QML](phase31/source-gui/walkthrough.json) ve
[noneditable kurulu wheel](phase31/wheel-gui/walkthrough.json) altı ayrı
sunucu/12 geniş-dar render, native değer/source id/metadata ve6 dataset
reopen'u geçti. Her adaptörde F1/Escape, preview eşitliği ve import/reopen
esnasında ağ çağrısı yapılmaması denetlendi. S3 gerçek keyring referansını
spawn worker'da çözdü; secret alanı temizlendi ve proje state'inde secret yok.
Güncel wheel **218 dosyada** source/wheel/installed byte eşit:
[SHA256/eşitlik](phase31/wheel-integrity.json).

Temel wheel ayrı core ortamında **psycopg/PyMySQL/DuckDB/keyring/boto3
fiziksel olarak bulunmadan**, OS ağsız user/network namespace içinde
GUI_SMOKE PASS verdi. [Gerçek core ortamı](phase31/core-environment.json),
[ağsız giriş noktası](phase31/core-offline-smoke.txt).
Bu core ortamı mevcut exact runtime dağıtımlarından test amacıyla hazırlanmıştır.
İlk temiz offline uv sync, cache'te PySide6-Addons wheel bulunmadığı için
başarısızdı; temiz offline kurulum veya yeni bundle kabulü verilmez.

Locked sync/dev/extra, docs/artifacts/learning/usability ve Ruff check/format
kapıları geçti.162 makale/100 UI bağ/293 named field/189 temel İngilizce mesaj.
Server/driver/CPU/RAM/FS/kilit/source hash bilgisi
[ENV-31](phase31/environment.json), [kaynak hashleri](phase31/source.sha256).
Komut ve exit kayıtları [checks](phase31/checks.json) içinde.
Her F31-P001..008 **C/V/G/H/P** kimliği
[ayrı gerçek witness kaydına](phase31/acceptance.json) bağlandı;
F31-S001..005 ve P001..008 teknik olarak doğrulandı.

İlk başarısız kontroller gizlenmez: sandbox soket reddi; metadata tuple/list
kalıcılığı; GUI'nin görünür import pane'i açılmadan çağrılması; fixture adı;
CSV'nin diagnostics alanı; testin eski psycopg info API adı. İlk snapshot
konsol ve JUnit'leri phase31 altında tarihsel saklanır. MinIO adresi410 döndü;
gerçek S3 uyumlu SeaweedFS kullanıldı. MySQL ayrıca resmî8.4.11 binary'yle
doğrulandı; MariaDB sonucu onun yerine geçirilmedi.

İlk geniş koşu793; API missing-next guard sonrası794; son libpq auth fallback
ve form korumaları sonrası nihai795 koşusu ayrı kaydedildi. Bağlantı formu
yalnız ilk Gelişmiş açılışında yüklenir, kapanıp açılınca ayarları korur;
iş sürerken düzenleme kapalıdır. Tür değişince credential ref temizlenir;
eski snapshot'ın parametreleri sessiz değişmez. Dosya yeniden-bağla ve genel
format seçicisi remote capture için sunulmaz; yeni kaynak açık read eylemidir.

Destek sınırı: ordinary tablo ve null olmayan tek String/Integer source key;
bound karşılaştırma sorgusu, serbest SQL yok. REST JSON envelope/next URL,
bearer; interaktif OAuth/cookie/query-auth yok. Snapshot token sağlayıcı
beyanıdır; totalsiz/token'siz API'de atlanan kayıt/tek-an garantisi yok.
S3 tek nesne/VersionId-IfMatch/SigV4; AWS canlı hesabı/SLA doğrulanmadı.
S3 Parquet/JSONL/CSV/IPC gerçek nesne witness'ları ayrı JUnit parametreleridir;
CSV default comma/UTF8/String, JSONL default native parse sınırındadır.
Fiziksel masaüstü/insan/AT, minimum donanım, canlı sağlayıcı SLA ve dağıtım
adayı kabulü değildir; faz sürüyor/deneysel/zorunlu kalır.


## Masaüstünde deneme

1. Proje oluştur/aç → Veri → Gelişmiş → Veritabanı/API/nesne depolama.
2. Tür/sunucu, TLS CA ve credential referansını gir. Gizli değeri maskeli
   alandan sistem keyring'ine kaydet; role yalnız kaynak okuma yetkisi ver.
3. Veritabanında şema/tablo listesini açık düğmeyle oku; kaynak key ve bağlı
   filtreyi seç. API'de records/next/total alanlarını ve sınırları düzenle.
4. Koşulları onayla → Snapshot önizle; garanti/tazelik ve native sütunları
   incele → İçe aktar. Kaydet/kapat/aç; eski snapshot çevrimdışı açılır.
