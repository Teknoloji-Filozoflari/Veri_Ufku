# Faz30 — gelişmiş yerel format adaptörleri

2026-10-10; ENV-30-HEADLESS; CPython3.13.15/PySide6 6.11.2 Linux,
Qt offscreen/software. DEC-30-01 kullanıcı açık Faz30 talimatı; yalnız bu
fazın teknik geliştirmesi açıldı. Önceki DEP-28-02..05 kapıları açık,
Faz31 başlamadı. [Karar ve gerçek destek sınırı](../adr/031-advanced-import-phase30.md).

<a id="e30-formats"></a>
## F30-S001/S002/S004 — format başına alt aşamalar

Fixture üretimi `tests/phase30_fixtures.py`, kalıcı
[fixture yolları/hash/lisans](phase30/fixtures.json).
`test_advanced_import.py::test_format_native_metadata_publish_reopen` ve
`test_advanced_import_gui.py::test_gui_format_selection_worker_save_reopen`
parametreleri her adaptöre ayrı gerçek witness verir. Genel toplam tek başına
format kabulü değildir. SPSS/Stata/SAS ortak bitmiş kütüphane adı değil,
aşağıdaki doğrulanmış varyantlardır; diğer varyantlar destekli diye sunulmaz.

| Alt iş | Doğrulanan deneysel format | Gerçek değer/metadata kanıtı | Açık sınır |
|---|---|---|---|
| F30-P001 | Partitioned Parquet / Hive klasör veya ZIP | UInt64 max, nullable Decimal(30,6), ns/IANA, list null, String001 partition, kaynak hash ve reopen | yalnız homojen yerel parçalar; symlink/unrecognized file/partition adı çakışması ret |
| F30-P002 | Arrow IPC file dataset | Aynı native değerler, dictionary vocabulary/index/ordered ve schema metadata | IPC stream dataset/nested dictionary/duplicate vocabulary ret |
| F30-P003 | Avro OCF record | long sınırları, nullable logical Decimal, enum schema, array null, local timestamp us | yalnız null+tek tür union; map/recursive/named reference/unknown logical type ret |
| F30-P004 | ORC tablo | Signed Int64/nullable Decimal/list ve Arrow kaynak şeması | UInt64 ORC source türü değildir; kaynakta olmayan IANA zone uydurulmaz; union/map türleri ret |
| F30-P005 | HDF5 1D compound key | UInt64/fixed binary/Float64, root/dataset attrs ve dtype | explicit key; pandas fixed/pickle/vlen/reference/nested compound/soft/external/virtual/plugin ret |
| F30-P006 | XML düz kayıt yolu | Record attrs, empty String ve absent null ayrımı, source hash/reopen | explicit /root/record; DTD/entity/external, namespace/XPath/nested/repeated/mixed content ret |
| F30-P007 | Sabit genişlik Unicode metin |001 leading zero, Türkçe, trailing spaces, widths/name metadata | byte-width/uyumsuz satır/unknown encoding ret; default String, açık tür dönüşümü |
| F30-P008 | SPSS SAV | System null /99 user-missing, labels/column labels/measure, header weight ve beyan | dates raw source sayı+format; missing/weights otomatik analize uygulanmaz; portable metadata preserved |
| F30-P009 | Stata DTA | `.a` tag /system null /blank String ayrımı, value labels/column labels | tags row map içinde, kaynak numeric format; dataset dışında tanımlanan ağırlık varsayılmaz |
| F30-P010 | SAS sas7bdat | A/B/C/X/Y/Z/_ tags ve system null; gerçek upstream iki fixture format metadata | external sas7bcat ve XPORT bu dilimde desteklenmez; format reference korunur; büyük SAS fixture ölçülmedi |

[51 ilgili ilk regresyon](phase30/targeted.txt) ve
[37 ek kaynak/QML testi](phase30/advanced-final.txt) başarılı.
İlk küçük format denemesinde HDF5 dtype tuple/list kalıcılık farkı görüldü;
metadata JSON biçimine normalize edildi. İlk XML bounded denemesinde root
container çocuk limiti kayıt limiti gibi uygulanmıştı; limit yalnız seçilen
kayda taşındı. Başarısız denemeler başarı sayılmaz.

<a id="e30-schema"></a>
## F30-S002/S003/F30-P013 — şema ve kaynak kökeni

Strict önizleme uyuşmazlığı gösterir ve importable=false. Kullanıcının union
seçimi yeniden önizlenir; Int64+UInt64→Decimal(20,0), eksik alan→null,
nested additive schema gerçek değerlerle doğrulandı. Integer+Float64,
sayı+String, farklı timezone, Decimal256 unsupported örnekleri ret verir.
Dictionary fiziksel değerleri ve orijinal sözlük scope'u ayrı saklanır.
Her source part hash/name ve her satır part/hash/ordinal kalıcıdır;
UUID RowId/SourceRecordId sıralama kimliği değildir. SourceSnapshotId capture'a
bağlıdır. Immutable bundle, metadata, kaynak/proje hash ve reopen kontrolü
gerçek source ve GUI testlerinde çalışır. Stata/SAS karakter blank ham String'i korurken satırdaki `system_missing` map'i kaynak eksik anlamını saklar.

<a id="e30-archives"></a>
## F30-S003/F30-P011/P012 — sıkıştırma, sınırlar ve iptal

Gzip/XML, ZIP/fixed width ve multi-Parquet ZIP gerçek QML/spawn/portable/reopen
testleri başarılı. Üst/mutlak/drive/ters yol, symlink, duplicate ve küçük disk
bütçesinde decompression bomb kontrollü reddedildi. Archive üyesi dış yola
extract edilmez. Kaynak değişimi import worker'da ve publication öncesinde
yeniden doğrulanır; eski sağlam commit korunur.

100000 XML kayıt GUI önizlemesi200/ekran20; iptal ve kaynak değişimiyle önceki
ACTIVE koruması geçti. [10005 kayıt ölçümleri](phase30/large.json) dokuz formatta
preview200 ve okuma sırasında cooperative iptal verir; SAS büyük fixture
ayrı açık ölçümdür. Native compressed block/stripe iç bellek peak garantisi
değildir; ortak worker wall/RSS/temp/cancel-grace koruması sürer.

<a id="e30-learning"></a>
## F30-S004 — çevrimdışı öğrenme

Katalog46/157 makale. `import-phase30`, `import-partition`,
`import-schema-evolution`, `import-category-labels`, `import-decimal-precision`
Veri öğrenme yolunda ve ilgili import/F1/registry bağındadır. Aynı gerçek
fixture değerlerinden örnekler; yeni silent-active-data eylemi yok.

<a id="e30-checks"></a>
## Ortam, kontroller ve teslim sınırı

[Kaynak GUI](phase30/gui-final/walkthrough.json) on format/on gerçek render,
source hashes/metadata ve bütün datasetlerin reopen sonucunu kaydeder.
İlk tam regresyon757 başarılı/1 hata: tests/test_usability.py eski152 katalog sayısını bekliyordu. Beş yeni konu157 sayısıyla eşlendi; başarılı yeni tam koşu e30-continuation altında ayrı kaydedildi. Son ek format kontrolleri37 başarılı; CSV/eski import yollarıyla93 test de geçti.
Başsız geliştirici kanıtı fiziksel masaüstü/insan/AT veya yeni remote CI
kabulü değildir. Yarım kalan tam regresyon ve kurulu wheel kontrolleri
2026-10-11 devamında aşağıdaki gerçek sonuçlarla tamamlandı.

## Masaüstünde deneme

1. Proje oluştur/aç → Veri → Dosya seç veya Dataset klasörü seç.
2. Gelişmiş'i aç. HDF5 key ya da XML kayıt yolunu seç; fixed width için
   genişlikleri/sütun adlarını gir → Önizlemeyi güncelle.
3. Şema uyuşmazlığında Şema çözümü seç → yeniden önizle; gösterilen hedef
   türleri/metadata ve uyarıları incele → İçe aktar.
4. Kaydet/kapat/aç; native değerleri ve metadata'yı doğrula. Öğren → Veri →
   Gelişmiş dosya formatları bölümü dört kavramı ve destek sınırını açıklar.


<a id="e30-continuation"></a>
## 2026-10-11 — yarım kalan teknik teslimin kapanışı

ENV-30-CONTINUATION: CPython3.13.15/PySide6/Qt6.11.2, Linux7.2.9-2,
Ryzen7 8845HS/32GiB, Btrfs; offscreen/software ve izole geçici XDG.
[Gerçek ortam/kilit/paket sürümleri](phase30/continuation/environment.json),
[kaynak SHA256 kayıtları](phase30/continuation/source.sha256).
Bu geliştirici donanımı minimum hedef kabulü değildir.

Kaldığı yer: eski pytest-final.txt yalnız %28'e kadar yazılmış, son başarılı
wheel denemeleri matrise/özetlere bağlanmamıştı. Eksik koşu başarı sayılmadı;
aynı Faz30 kapsamı yeniden doğrulandı. Kaynak birleşik prompt ve kullanıcı
datasetleri değiştirilmedi; Faz31 başlatılmadı.

- Tam regresyon **761 pytest/462.492s**, sıfır failure/error/skip:
  [JUnit vaka kimlikleri](phase30/continuation-pytest.xml),
  [gerçek konsol](phase30/continuation-pytest.txt).
- Kilitli ortamda **14 unittest** geçti. Sistem Python3.14.7 kontrolü
  **76 discovery/62 bağımlılık import hatasıyla başarısız**; kilitli ortam
  başarısıyla birleştirilmez. [Başarılı](phase30/continuation/unittest.txt),
  [başarısız](phase30/continuation/system-unittest.txt).
- `uv sync --locked --group dev` geçti; docs/artifacts/learning/usability,
  Ruff check/format ve izole giriş noktası exit0.
  [Komut/tarih/exit kayıtları](phase30/continuation/checks.json).
- Kaynak ve noneditable wheel: on format native snapshot/metadata/source
  hash/atomik kayıt ve on dataset reopen geçti. Beş adaptörün720/1366
  toplam on gerçek render'ı üretildi. HDF5 dar ve partitioned Parquet geniş
  görüntüleri ajan tarafından incelendi; içerik dikey kaydırmayla erişilir.
  [Kaynak](phase30/continuation/source-help/walkthrough.json),
  [kurulu paket](phase30/continuation/installed-help/walkthrough.json).
- Aynı walkthrough artık her adaptörde gerçek **F1/Escape** ve odak dönüşünü
  denetler; preview/proje draft eşitliği yardımın veri değiştirmediğini
  doğrular. Beş yeni çevrimdışı makalenin önce/sonra örnekleri gerçek QML
  yardımında açıldı.157 makale/96 UI bağ ve266 named field/189 temel
  İngilizce mesaj kontrolü geçti.
- Dokuz format **10005 kayıt/preview200**, cooperative iptal ve kaynak/kurulu
  wheel ölçümü geçti. [Kaynak](phase30/continuation/source-large.json),
  [paket](phase30/continuation/installed-large.json).
  SAS büyük fixture ölçümü açık kalır; küçük sas7bdat metadata/tag ve reopen
  witness'ı büyük SAS performans/peak RAM kabulü değildir.
- Locked hatchling ile wheel üretildi; `uv pip install --no-deps --no-index`
  ile ayrı `/tmp` target içinde paket kuruldu. **211 paket dosyası** source/wheel/target byte eşit;
  gerçek CSV spawn import ve izole kurulu giriş smoke exit0.
  [Paket SHA256 ve eşitlik](phase30/continuation/wheel-integrity.json).

F30-S001..004 ve F30-P001..013 teknik kabul kayıtları matrise bağlandı.
Her P kimliğinin **C/V/G/H/P** boyutu, parametreli gerçek native/GUI vakası,
yardım ve yayın/reopen yolu [ayrı witness kaydında](phase30/continuation/acceptance.json).
Format kabulü yukarıdaki doğrulanmış varyantlarla sınırlıdır; dış SAS catalog,
XPORT, pandas/pickled HDF5, namespace/nested XML gibi açıklanan varyantlar
desteklenmez. İnsan/AT/minimum donanım/temiz dağıtım ve önceki bağımlılıklar
açık olduğundan **faz sürüyor / deneysel / zorunlu** kalır; bu teknik teslim
dağıtım adayı veya fiziksel masaüstü kabulü değildir.

Başarısız yardımcı denemeler: ilk uv sync sandbox'taki salt okunur cache
nedeniyle durdu; kullanıcı onaylı cache erişimiyle aynı locked komut geçti.
Ortam envanterinde psutil bulunmadı; bağımlılık eklenmeden stdlib ve /proc
ile gerçek ortam kaydı üretildi. Başarısız denemeler uygulama test başarısı
diye etiketlenmedi. Önceki757/1 katalog ve HDF/XML ilk denemeleri korunur.

<a id="e30-recheck"></a>
## Bağımsız tekrar koşusu

Aynı2026-10-11 devamında [ikinci tam pytest](phase30/continuation/pytest.txt)
761 passed in463.81s; [JUnit](phase30/continuation/pytest.xml) sıfır
error/failure/skip. [14 kilitli unittest](phase30/continuation/unittest.txt)
başarılı. [Format ve arşiv/şema test kimlikleri](phase30/continuation/witnesses.json)
JUnit ile ayrıca eşlendi. [Ayrı wheel komutları](phase30/continuation/wheel-checks.json)
on format/reopen, dokuz büyük önizleme/iptal, CSV import ve entry smoke
kontrollerini yeniden geçti; aynı SHA256 wheel kullanıldı. Büyük SAS
ölçümü bu tekrarda da yapılmadı; genel destek/performans garantisi verilmez.
