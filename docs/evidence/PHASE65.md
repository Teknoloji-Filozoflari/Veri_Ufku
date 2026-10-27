# Faz65 — kayıtlı lineage ve bilimsel yeniden üretim

2026-10-15 DEC65-01, ENV-65. Açık Faz65 talimatı; resmî sürüyor/deneysel/isteğe bağlı. Faz66 başlatılmadı. Önceki resmî fiziksel/insan/AT/minimum donanım/uzun retained heap/offline kurulum/remoteCI açıkları korunur.

<a id="e65-scope"></a>
## E65-SCOPE

Mevcut ProjectStore/OperationSpec/Provenance/Capability ve experiment registry genişletildi; yeni kayıt sistemi yoktur. Kayıtlı source→dataset→operation→analysis/model→report graph, hash/URI/version/schema, params/decisions/capture/backend/hardware alanları ve eski kayıttaki not_recorded boşlukları görünür. Yeni raporlar gerçekten dahil ettikleri kaydedilmiş quality/profile/analysis/chart kimliklerini taşır. Eski rapor için olmayan analysis/model bağı üretilmez. Workflow model/predict/export bağı gerçek typed dependency'dir. RowId çok kaynak ilişkisinin kayıtlı Parquet URI/hash'i gösterilir; genel recursive row reconstruction mevcut değil.

Rapor→Lineage ve bilimsel yeniden üretim: focus graph, node metadata, data inclusion ve redaction preview, safe bundle, hash doğrulamalı açma ve explicit re-run. Varsayılan reference-only; immutable snapshot ayrıca seçilir. Retention mevcut quota/usage ile tarihî artifact tutma; otomatik silme/GC yok. Arşivleme disk boşaltmaz. Snapshot veri bytes kopyası, reference erişim hakkı/yedek değildir.

Bundle closed manifest/config/lineage/reference-report aggregate/env lock/requirements.lock/yöntem-yardım sürümü/hardware/storage policy/redaction preview ve optional native data. Secret/file paths/free text temizlenir; config değişirse rerun destekli sayılmaz. Raw data seçimi hassas değer/RowId içerebilir; secret kolon/örüntüsü reddi evrensel dedektör değildir, kullanıcı incelemesi gerekir. Binary/nested kullanıcı verisi taraması unsupported/reference-only; native missing_fields metadata kontrollü istisnadır. Credential/keyring/env değerleri alınmaz. Executable/model object deserialize/import edilmez. ZIP duplicate/path/symlink/encryption/size/schema/method ve her artifact hash doğrulanır. Hash authenticity imzası değildir.

Verifier ilk kapsam: kaydedilmiş numeric measurement profile (dataset, filtresiz full veya bounded firstN), tamamlanmış Faz64 workflow tanımlı analytical projection. Rapordaki tek destekli kaydedilmiş analysis/run reference'ı karşılaştırılabilir; HTML/PDF layout byte replay değildir. Profil Decimal80/counts/kimlikler exact; numeric yalnız Float64 OLS katsayı/tahmin için rtol1e-9/atol1e-12, yöntem/çıktı birimi gerekçesi policy'de. Değişen veri hash'i tolerance öncesi durdurur. Backend/code/Python/package/platform/schema/method farkı safe failure; otomatik migration yok. Reference/actual/comparison test artifact'ları ayrı saklanır. Seed tek başına yeniden üretim garantisi değildir. [Ayrıntılı sözleşme](../adr/066-reproducibility-phase65.md).

<a id="e65-validation"></a>
## E65-VALIDATION

Gerçek source/wheel, native/GUI ve kapı sonuçları teslim sonunda aşağıya bağlanır. Çalıştırılmayan kontrol başarılı sayılmaz.405 offline makale,5 yeni yardım konusu; yeni deneme eylemi yok.

[Ortam](phase65/environment.json), [kabul kimlikleri](phase65/acceptance.json),
[doğrulama](phase65/verification.json), [kapılar](phase65/gates.json),
[wheel](phase65/wheel.json), [teslim hashleri](phase65/frozen-head.json).

- Seçilmiş core: [382 source](phase65/source-core-release.xml), [382 wheel](phase65/wheel-core-release.xml). Son secret-pair/canonical sorting düzeltmelerinden önce; tam depo regresyonu değildir. Shutdown sırasında226 uncollectable object ResourceWarning kaydı vardır; uzun retained-heap kabulü değildir.
- Son delivery-focused: [39 source](phase65/source-delivery-focused.xml), [39 wheel](phase65/wheel-delivery-focused.xml).16native repro+13workflow+10performance; son maskeleme, canonical ordering, üç ayrı Python hash seed ve hafif RSS probe dahil. Intentional duplicate ZIP fixture warning başarısız test değildir.
- Default2GiB temel gerçek GUI: [4 source](phase65/source-basic-final/gui.xml), [4 wheel](phase65/wheel-basic-final/gui.xml). Report→recorded profile→dataset→source graph, redaction/reference bundle, open/hash (noexec), exact comparison, opt-in standalone included data, source-change stop, cancel ve corrupt archive. Bunlar son canonical sorting değişiminden önceki temel GUI koşularıdır; son değişim model/focused ve ayrı final profile tekrarında doğrulandı.
- Son profile exact GUI tekrarları: [source](phase65/source-profile-delivery/gui.xml), [wheel](phase65/wheel-profile-delivery/gui.xml); her biri1pass/4deselected ve default2GiB. Bunlar önceki dört testle tek yeni aggregate değildir.
- Model numeric yolu: [source explicit4GiB](phase65/source-model-delivery-4gib/gui.xml), [wheel explicit4GiB](phase65/wheel-model-delivery-4gib/gui.xml); her biri1pass/4deselected. Gerçek workflow fit/predict, graph model node, safe bundle, reopen ve numeric comparison tamamlandı. Default2GiB model setup hem mixed hem fresh süreçte budget reject verdi; bu kapı açık. Üretim varsayılanı değiştirilmedi.
- Graph görseli için [ayrı source1pass](phase65/source-lineage-final/gui.xml), [1000px](phase65/source-lineage-final/report-reference-1000.png), [1366px](phase65/source-lineage-final/report-reference-1366.png). Sonuç ve model policy görüntüleri ilgili walkthrough/screenshot dizinlerinde. Caption konumu ve görünürlüğü gerçek QML scene'de doğrulanır; görseller ajan tarafından incelenir, insan/AT kabulü değildir.
- Final kurulu noneditable wheel gerçek QML/CSV import smoke PASS.370 paket dosyası kaynakla byte eşit. Bağımlılık/model indirilmedi; uv yalnız /tmp task cache ve yerel wheel ile kuruldu.
- Yedi yerel kapı: docs/artifacts/learning/usability/Ruff check/format/14 documentunit.405 makale,5 yeni offline konu; registry/UI yardım bağları. Kaynak ve eski evidence dosyaları korunur.

[Erken başarısız koşular](phase65/early-failures.json) silinmedi. İlk worker memory,
metadata import/RSS, metadata cancel boundary ve preview hash sırası hataları ayrı
JUnit/metadata ile tutulur. [source4pass/1fail](phase65/source-gui-final/gui.xml),
[wheel4pass/1fail](phase65/wheel-gui-final/gui.xml),
[fresh source2GiB fail](phase65/source-model-fresh/gui.xml),
[fresh wheel2GiB fail](phase65/wheel-model-fresh/gui.xml) başarıya çevrilmez.
İlk4GiB source preview failure; sonraki canonical node/redaction sıralama ve
in-memory/JSON/hash-seed regression ile düzeltildi. Source ilk202core201pass/1fail
(yeni testte environment import eksik) sonrası202pass; bunlar382 ile toplanmaz.

Bellek düzeltmesi shared RSS helper ve source fingerprint'in ağır backend import
etmemesidir; budget yükseltilmesi değildir. Modelin4GiB kanıtı üretim2GiB kapısını,
önceki long retained-heap/minimum hardware veya physical/human/AT/clean offline
installation/remoteCI kabulünü kapatmaz. Generic model/analysis rerun ve recursive
row reconstruction uygulanmış sayılmaz; unsupported durum görünür.

Re-run kıyaslama artifact'ları yalnız tanımlı analytical projection içindir; tüm
render, rastgele UUID/timestamp/cache veya bilimsel eşdeğerlik iddiası yoktur.
Ortam lock mevcut trusted runtime'dır, tarihî eski ortam eksikse onu uydurmaz.
Kaynak hash farkı beklenen/yeni SHA ile görünür; numeric tolerance veriyi değiştirmez.
Retain policy otomatik silmez. Stage/commit/push yapılmadı; resmî kabul ayrı sürer.

Son legacy metadata guard: import metadata olmayan eski dataset graph'ta not_recorded
kalır; data inclusion/re-run reddedilir. [Son40source](phase65/source-legacy-final.xml)
ve [son40completewheel](phase65/wheel-legacy-final.xml):17repro+13workflow+10performance.
Önceki39şar focused bu koşuyla tek aggregate yapılmaz. Last model4GiB GUI, bu yalnız
legacy-metadata guard değişiminden önceki delivery build'indedir; son core/focused
ve ayrı profile smoke guard sonrası complete paketi doğrular.

Son complete paket profil GUI: [source1pass](phase65/source-profile-complete/gui.xml),
[wheel1pass](phase65/wheel-profile-complete/gui.xml), ikisi default2GiB. Son legacy
metadata guard sonrası final kurulu paket import smoke PASS;370byte-eşit dosya.
Matris kabul tarihleri doğrulayıcı sözleşmesi gereği UTC2026-10-15; yerel teslim tarihi
Europe/Istanbul2026-10-16'dır. İlk belge kapısı yerel tarihle future-date hatası verdi,
UTC tarihiyle düzeltildi ve yeniden doğrulandı; ilk koşu gates kaydında korunur.
