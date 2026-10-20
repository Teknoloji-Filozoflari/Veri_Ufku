# ADR074 — versioned explicit trusted Python plugin SDK

2026-10-16 DEC73-01. Yalnız açık Faz73 talimatı; Python3.13/PySide6/QML korunur.
Tek Capability registry, ComputeBudget, Provenance ve ProjectStore genişletilir.

## Sözleşme ve bounded host kapsamı

`plugins/sdk.py` API1 protocol: ImporterV1, TransformV1, StatisticV1, ModelV1,
ChartV1, LessonV1; ortak `run(request, context) -> PluginOutput/v1`. Context API
version, ComputeBudget snapshot ve cooperative cancel/time kontrolü verir.
PluginInput/v1 seçilmiş DatasetVersion, ColumnId tanımları, immutable RowId/
SourceRecordId ile finite scalar JSON satırları, seed ve scalar typed parameters.
Kaynak32MiB/10000row;1..16kolon, request8MiB, output1MiB, saved run2MiB.
NaN/Inf/Decimal/date/binary/nested input sessiz dönüştürülmez; unsupported ret.

Altı kind için farklı data output şeması ve contract test vardır:

| Tür | Çıktı / gerçek sınır |
|---|---|
| importer | columns/rows/source_record_ids tablo preview artifact; arbitrary format parser olarak trusted code kullanılabilir, aktif DatasetVersion yayını bu SDK hostunda yok |
| transform | columns/rows/parent_row_ids; kaynak RowId kontrolü, tablo preview artifact; active dataset apply/undo adapter yok |
| stat | finite numeric metrics; örnek mean/n gerçek analiz |
| model | finite metrics ve safe JSON state; arbitrary object/pickle yok, host prediction/reload adapter yok; validation/split doğruluğu plugin yazarının sorumluluğu |
| chart | numeric x/y/axis-label descriptor artifact; tam native chart editor/renderer hook yok |
| lesson | title/paragraphs safe düz metin snapshot; çekirdek lesson katalog/try_action otomatik install yok |

Bu faz genel importer/pipeline/model GUI native adapter'ları tamamlanmış saymaz;
versioned author SDK ve bounded result host sağlar. Her kind gerçek calculate→
artifact→readback testinden geçer. UI kabul örneği stat/analysis'tir. Çıktı plugin
iddiasıdır, host bilimsel doğruluk/learning uzman incelemesi yapmış sayılmaz.

## Manifest discovery ve explicit trust

Self-contained klasörde manifest.json ve plugin.py:run. Metadata ve kod64KiB;
manifest closed schema Veri_UfkuPlugin/v1/API1, id/semver/Python3.13/entry/code SHA256,
permissions/exact dependency versions/capability/input/output/parameters/method_version,
learning id/version/title/summary/limitations zorunlu. Plugin label/path veri olarak
okunur, HTML/QML import veya model deserialize yapılmaz. Kod hash'i publisher imzası,
kimlik doğrulaması veya kod güvenliği kanıtı değildir.

Uygulama açılışında plugin klasörlerini taramaz/import etmez. Kullanıcı manifest
seçip inceleyince yalnız metadata, kaynak bytes/hash ve importlib.metadata exact
installed sürümleri okunur; plugin module import yoktur. Uygulamanın kilitli mevcut
Python ortamı kullanılır; ayrı dependency environment yaratma, pip/install, user
site activation veya indirme yok. Ortam/dependency uyuşmazsa çalıştırma kapalıdır.
Bildirilmeyen importlar Python tarafından yine mümkün olabilir; dependency listesi
OS enforcement değildir. Ayrı ortam desteği gelecekte ayrı doğrulama gerektirir.

Run için aynı code/manifest/environment inspection hash, kullanıcı trust onayı,
seed ve ColumnId/parametreler zorunlu; source hash worker'da okumadan önce/sonra
kontrol edilir. Manifestte network varsa ayrı kullanıcı onayı gerekir. Explicit
activation mevcut Capability registry'ye namespaced plugin.id.method ekler; core
id üstüne yazılmaz. Aynı session namespaced id başka code/version ile yeniden
kaydedilemez. Proje açılışı registry'yi code'dan yeniden yaratmaz. Method semantic
version ve parameter API version ayrı saklanır. Sahte metadata eksik API/help ile
çalışmaz. Plugin learning snapshot sonuçta PlainText gösterilir; platform yardım
kataloğunda plugins-sdk F1/Escape bağı vardır, plugin metni kod değildir.

## İzin modelinin gerçek sınırı

`dataset.read`, `result.emit`, `python.same-user`, optional `network` beyan/onay
alanlarıdır. Host yalnız seçilmiş bounded dataset girdisini ve kontrollü output
protokolünü sunar; **OS-level syscall permission enforcement yoktur**. Python kodu
aynı kullanıcının filesystem/network/keyring haklarıyla çalışır; kötü niyetli kod
ProjectStore/source dosyasına erişebilir, child process yaratabilir veya ağ isteği
yapabilir. Ayrı process güvenli sandbox değildir; bu kodu çalıştırma onayı, yalnız
bilinen/trusted kod için verilmelidir. Ağ izni beyan etmemek ağ erişimini OS'de
engellemez. Resource limit/cancel uygulama hatası/çökme izolasyonudur, hostile-code
containment veya malware güvenliği değildir. Seccomp/container/OS sandbox yoktur.

Worker Qt almaz/ACTIVE yazmaz. Trusted host input okur, pinned code bytes'ını yalnız
explicit run'da compile/exec eder. Parent process kod import etmez. stdout/stderr
FD'leri /dev/null'a yönlenir; exception metni/traceback/log yok, hata türü gösterilir.
Safe finite JSON, çıktı şekli, kaynak RowId ve bilinen secret pattern/key engelleri
uygulanır. Secret taraması eksiksiz detector değildir. Secret/credential parametre
ve output içine yazılmaz; SDK otomatik credential verme veya keyring export yapmaz.

ComputeBudget process/native thread admission ve runtime resource limits; GUI
supervisor time/RAM/cancel/forced terminate. Arbitrary subprocess tree/escaped
children güvenlik garantisi verilmez. CLI contract runner da ortak admission ve
bounded fresh process kullanır; headless author testi açık --trust-code ister.

## Persistence, failure ve eksik plugin

PluginRun/v1 safe JSON artifact mevcut ProjectStore sources namespace altında;
plugin_result reference aynı results journal'a atomik eklenir. Ortak Provenance
source snapshot/DatasetVersion/params hash/method version/code hash/plugin version/
Python/dependency environment/seed/learning version tutar. Artifact raw kod ve
plugin dosya yolu içermez; missing code halinde okunabilir. Kayıtlı parametre/sonuç
hassas veri içerebilir; export/privacy politikaları ayrı geçerlidir.

Kaynak hash publication öncesi yeniden eşleşir, RowId subset yeniden kontrol edilir;
yeni global RowId uydurulmaz. Table previews canonical DatasetVersion/ColumnId diye
etiketlenmez. Host ProjectStore transaction/journal/manifest ref validation ve mevcut
tek yazıcı kilidi korunur. Çöken/kayıp/timeout/invalid output plugin başarı diye
kaydedilmez; eski sonuç korunur. Bu accidental failure izolasyonudur, hostile aynı
kullanıcı koduna karşı veri koruma garantisi değildir.

Eksik plugin ile proje açılışı manifest code path aramaz/import etmez; data-only
artifact/hash ve yardım snapshot okunur (read-only proje dahil). Recompute yalnız
aynı paket hash'i, uyumlu environment ve yeni explicit trust ile mümkündür. Otomatik
artifact migrasyonu veya bilinmeyen backend kodu deserialize yok; method API
uyumsuzluğunda safe failure. JSON state model runtime persistence desteği sayılmaz.

## Yazar testi ve örnek

`examples/plugins/mean`: CC0 self-contained plugin.py/manifest.json/request.json.
math.fsum/n, null exclusion, finite numeric ve >2^53 integer guard. Bağımsız test:

```sh
.venv/bin/python -m veri_ufku.plugins.contract_test --manifest examples/plugins/mean/manifest.json --request examples/plugins/mean/request.json --trust-code
```

Beklenen mean2/n3 bağımsız pytest assertion'ı ile de doğrulanır. Contract CLI GUI veya
ProjectStore açmaz. API/shape/finite/RowId kontrolleri istatistik veya güvenlik
sertifikası değildir. [Gerçek kanıt](../evidence/PHASE73.md), test ortamı ve önceki
formal açıklar ayrı; Faz74 başlamaz.
