# ADR-031 — Faz30 gelişmiş yerel import

2026-10-10; DEC-30-01 açık kullanıcı Faz30 talimatıdır. Yalnız Faz30 teknik
geliştirmesi seçildi; önceki insan/AT/donanım/dağıtım kabulleri kapanmaz.
Python/PySide6/QML, mevcut SourceAdapter, ComputeBudget, registry ve atomik
ProjectStore.publish_import korunur. Faz31 başlatılmaz.

## Adaptör ve kaynak

`advanced.py` aynı SourceAdapter sınırında format başına okuyucu kullanır;
`advanced_readers.py` veri/metadata ayrıştırır, GUI veya commit yayımlamaz.
Registry yeni formatları mevcut worker'a yönlendirir. Her yeni format gerçek
küçük fixture+native değer/metadata+proje reopen+QML/spawn yolu ile doğrulanır.
Kütüphanenin bütün format varyantları uygulama desteği sayılmaz.

`sources.py` yerel Parquet/Arrow klasörünü sıralı, deterministik ZIP_STORED
kopyasına alır. Non-seekable ZIP yazımıyla directory hash ve taşınabilir bundle
aynı byte fingerprint'i üretir; parça ekleme/çıkarma/değiştirme algılanır.
Directory symlink/özel dosya reddedilir. Gzip tek akış, ZIP tek veri dosyası
veya homojen dataset taşır. extractall kullanılmaz; güvenli üye adı yalnız
metadata olur, kopya rastgele özel workspace yoluna yazılır. Mutlak/üst/drive/
ters eğik çizgi, duplicate, encrypted, symlink/özel üye reddedilir.
1024 üye,512MiB toplam açılmış veri,1000× ZIP oranı ve disk rezervasyonu
önkontrol/okuma sırasında uygulanır. Raw tek dosya eski1GiB sınırına tabidir.
Eski XLSX/ODS kendi kapsayıcı/adaptör güvenlik sözleşmesini sürdürür.

Yeni formatlar ve gzip/ZIP kaynakları worker öncesi/sonrası ve yayın öncesi
yeniden doğrulanır; değişince yeniden seçim gerekir. Eski düz CSV immutable
kopya politikası korunur. Kaynak dosyaya yazılmaz. İptal işaretli worker ve
zorunlu sonlandırma grace'i, başarısız staging/ACTIVE davranışı aynıdır.

## Native şema ve köken

StructuredSettings/v1 additive `schema_policy`, `format_metadata`, `widths`,
`encoding`, `max_rows`, `weight_column` alanlarıdır. Eski kayıtlar varsayılanla
okunur. Manifest7 değiştirilmez; metadata256KiB sınırında safe JSON'dur.
Sınır aşılınca alan atılmaz, import durur. Bu alanların yeni format kayıtları
eski uygulamaya forward-compatible olduğu iddia edilmez.

Default strict farklı şemayı durdurur. Union açık kullanıcı seçimi ve yeni
önizleme ister: eksik alan null; signed/unsigned integer kesin genişletme,
gerektiğinde Decimal(20,0); Decimal ortak scale/precision≤38; nested struct/list
additive alanlar; aynı timezone'da ms/us/ns kesin genişletme. Integer+float,
sayı+metin, farklı timezone veya precision>38 çatışması kontrollü ret olur.
Safe Arrow cast taşma/değer kaybında durur; otomatik String/Float64 çözümü yok.
Çözüm, giriş parçaları ve hedef fiziksel tür önizlemede görünür.

Arrow IPC şema serialization'ı base64 veri olarak nullable/field/schema
metadata ve orijinal türü taşır; executable payload değildir. Dictionary
değerleri fiziksel native değer olarak saklanır, index türü/ordered/vocabulary
ve parça/kayıt aralığı ayrı metadata'dadır. Yinelenen vocabulary ve nested
dictionary desteklenmez. Hive key=value etiketleri String, leading zero
korunur; null partition işareti açık. Physical sütunla partition çakışırsa durur.

Her satır UUID RowId ve SourceRecordId, parça yolu/SHA256/kayıt ordinali
taşır. SourceSnapshotId bütün immutable capture'a bağlıdır. Sıra kimlik değildir.
`__vu_missing_fields` eksik alanları, `__vu_expansion_index` additive
`user_missing` map'i SAS/Stata missing tag'lerini korur. Eski lineage alanları
ve mevcut işlem/geri alma davranışı değiştirilmez.

## Format anlamı ve riskler

SPSS numeric user-missing kodu değer olarak kalır, missing_ranges ve value
labels ayrı saklanır. Numeric system-missing null'dır. Stata/SAS character blank ham String olarak kalır; satırdaki system_missing flag kaynak eksik anlamını korur. SAS/Stata tagged missing null
hücre+satırdaki tag olarak saklanır; tag'siz system-missing ayırt edilir.
İstatistik tarihleri source sayısı+orijinal format metadata olarak korunur;
takvim epoch'una sessiz çevrilmez. SPSS header weight fiziksel indeksi
kolona çözümlenir; kullanıcı ağırlık beyanı ayrı, otomatik analiz yoktur.
SAS dış catalog reference metadata'da kalır; catalog dosyası bu dilimde
çözümlenmez ve yokmuş gibi yorumlanmaz. XPORT tagged-missing varyantı reddedilir.

HDF5 yalnız seçilmiş1D compound Dataset; attrs/root attrs/dtype/enum korunur.
Key otomatik seçilmez. Hardlink döngüsü bounded visited set; soft/external/
virtual/external storage ve özel filter plugin reddedilir. Chunk≤16MiB;
vlen/reference/complex/array/nested compound ve pandas pickled fixed HDF
desteklenmez. XML seçilmiş mutlak basit kayıt yolu, düz children+record attrs;
DTD/entities/external tamamen kapalı. Namespace/XPath/nested/repeated/mixed
content desteklenmez. Derinlik16, alan256 ve tek kayıt/alan1MiB sınırıdır.
Sabit genişlik Unicode karakter sayısına göre, boşlukları koruyarak okunur;
farklı byte-width düzeni veya uyumsuz satır kontrollü reddedilir.

Önizleme en fazla200 kaydı inceler, GUI ilk20'yi gösterir; batch1024,
decoded batch≤64MiB ve ortak process/RSS/wall/disk budget uygulanır. Native
kitaplık tek compressed block/stripe/chunk'ı kendi içinde açabilir; bu reader
ve process budget kesin donanım peak RAM garantisi değildir. Eager bütün veri
okuma yok; schema metadata veya kaynak fingerprint okumak preview satırı sayılmaz.

## Resmî inceleme ve kilit

Kurulu kilit CPython3.13.15; pyarrow26.0.0, fastavro1.13.1, h5py3.16.0,
pyreadstat1.3.6, defusedxml0.7.1 gerçek paket metadata/API ile doğrulandı.
Mevcut paketler yeniden çözülüp keyfî güncellenmedi. Kaynaklar2026-10-10:
[Arrow dataset](https://arrow.apache.org/docs/python/dataset.html),
[Arrow ORC](https://arrow.apache.org/docs/python/orc.html),
[h5py dataset](https://docs.h5py.org/en/stable/high/dataset.html),
[h5py link](https://docs.h5py.org/en/stable/high/group.html),
[fastavro](https://fastavro.readthedocs.io/en/latest/reader.html),
[pyreadstat](https://github.com/Roche/pyreadstat/blob/master/README.md),
[defusedxml](https://pypi.org/project/defusedxml/).
API ve variant davranışı ayrıca gerçek fixture testlerine bağlıdır;
remote CI/temiz dağıtım/insan kabulü bu incelemeden çıkarılmaz.
