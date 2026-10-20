# Faz64 — typed DAG, GUI/CLI ve bounded batch

2026-10-15; DEC64-01; ENV-64. Açık Faz64 talimatı; resmî sürüyor/deneysel/isteğe bağlı. Faz65 başlamadı. Önceki fiziksel/insan/AT/minimum donanım/retained-heap/temiz offline kurulum/remote CI kabulleri korunur; yeni testler bunların yerine geçmez.

<a id="e64-scope"></a>
## E64-SCOPE

Mevcut zincir OperationSpec motoruna dayanan typed DAG: source/transform/quality/analysis/train/predict/export. Tek Capability registry portları, cycle/type/after doğrulaması, bağımsız branch ve blocked/stale yönetimi. GUI Hazırla → Typed DAG: görsel bağlantı diyagramı, kart/form, port bağlama, dependency ve ileri declarative batch/sweep editörü. Geçersiz edit eski tarifi sessiz çalıştırmaz. GUI ve CLI aynı Qt'siz worker/calculate, ComputeBudget ve parent ProjectStore atomik protokolünü kullanır.

Bounded gerçek kapsam: yerel imported DatasetVersion snapshots; rename/drop/filter; numeric required-null quality; mevcut numeric profile/ddof0/1; tek feature OLS ve güvenli katsayı prediction; Parquet export. Train tüm açık upstream veride fit'tir, held-out değerlendirme veya final test kullanımı değildir. Diğer analiz/model aileleri DAG'da hazır gösterilmez. Run-scoped türetilmiş DatasetVersion/ColumnId/RowId/SourceRecordId ve Provenance native artifact'ta korunur; ana dataset head otomatik değiştirilmez. Aynı experiment registry ve eski test-use ledger bağları korunur. Yeni kayıt sistemi/credential/network yürütmesi yoktur.

Cache kaynak/version/hash/schema/semantic metadata, params/config, method/code/env, parent key ve bütçeyle anahtarlanır; hit öncesi ve sonrası kaynak ile artifact hash doğrulanır. Yeni sürüm başka key; bozulan snapshot failure, bağımlılar blocked. Geçmiş run açmak çalıştırmaz; geçmiş verified_at bugünkü güncellik değildir. Saf transient I/O retry0–2; export otomatik tekrar edilmez. OWNER/LOCK ve sahipli temp temizliği; kaynak veya başka run çıktısı ezilmez. İptal sonrası hazır export yayınlanmaz. Batch case/sweep adları ve export UUID token'ı ayrıdır; yalnız kayıtlı aynı key/hash receipt'i idempotent kabul edilir. Dış dosya ile proje commit arasındaki crash orphan'ı otomatik benimsenmez.

24 node,1–10000 satır/64 kolon/kaynak,8 case×sweep,500000 row×node. Explicit dataset→ColumnId eşlemesi tür/unit/role/ordinal uyumu ister. İlk sweep analysis.ddof0/1. Dry-run plan/hash/önkontrol yapar, compute/cache/export yapmaz; plan run'ı saklanır. Kaynak yazma kapalı. [Ayrıntılı sözleşme ve CLI](../adr/065-typed-workflow-phase64.md).

<a id="e64-schedule"></a>
## E64-SCHEDULE

Optional local schedule mevcut değil/doğrulanmadı. Uygulama kapalıyken iş çalışmaz; kullanıcı CLI'yi açıkça başlatır. Cron/service kurulmadı, kaçırılmış schedule başarılı sayılmaz. Aynı proje GUI/CLI için tek writer gerektirir. CLI SIGINT/SIGTERM/wall/RSS ve worker bütçesiyle sınırlıdır. Temiz offline kurulum ayrı kabul; runtime'ın ağ/model download gereksinimi yoktur.

<a id="e64-validation"></a>
## E64-VALIDATION

Gerçek native, source GUI ve noneditable wheel testleri, ortam ve JUnit kayıtları bu dosyaya teslim sonunda bağlanır. Çalıştırılmayan kontrol başarılı sayılmaz. Öğrenme kataloğu400 makale, üç yeni offline DAG/cache/batch makalesi ve gerçek F1/yardım yolu içerir.

[Ortam](phase64/environment.json), [kabul kimlikleri ve alt işler](phase64/acceptance.json),
[doğrulama özeti](phase64/verification.json), [kapılar](phase64/gates.json),
[wheel/hash](phase64/wheel.json), [teslim dosya hashleri](phase64/frozen-head.json).

- Kaynak ve noneditable wheel seçilmiş core: [275 source](phase64/source-core.xml), [275 wheel](phase64/wheel-core.xml). Son yayın bariyeri/transform metadata düzeltmesinden önceki koşulardır; tam depo regresyonu değildir.
- Son yayın ve bağlantılı journal testleri: [157 source](phase64/source-publication-final.xml), [157 final wheel](phase64/wheel-publication-final.xml);13 native DAG testi dahildir. Önceki12 native [ayrı koşu](phase64/source-native.xml).
- Son gerçek QML: [5 source](phase64/source-gui-release/gui.xml), [5 final wheel](phase64/wheel-gui-release/gui.xml). GUI→CLI numeric sonuç eşdeğerliği, typed port/after-cycle reddi,7node rename/quality/analysis/OLS/predict/export, cache/idempotent tekrar, invalid edit, cancel/timeout ve mevcut zincir köprüsü. Her case1000/1366 genişlik screenshot/caption konumu doğrulanır; [source metadata](phase64/source-gui-release/walkthrough.json), [wheel metadata](phase64/wheel-gui-release/walkthrough.json). İptal/timeout case'leri başarı değil terminal hata/iptal davranışını doğrular.
- Son editor diyagramı için [ayrı1 source repeat](phase64/source-editor-release/gui.xml), [1000px](phase64/source-editor-release/train-export-1000.png), [1366px](phase64/source-editor-release/train-export-1366.png). Görsel ok/kartlar ve okunur sonuç paneli ajan tarafından incelendi; insan/AT kabulü değildir.
- Final kurulu wheel gerçek QML/import smoke PASS;362 paket dosyası kaynakla byte eşit. Bağımlılık veya model indirilmedi; paket kurma ilk uv varsayılan cache denemesinde salt okunur dosya sistemiyle durdu, izinli yerel kurulum sonrası son build /tmp task cache ile kuruldu.
- Yedi kapı docs/artifacts/learning/usability/Ruff check/format/14 documentunit. Katalog içerik80,400 makale;3yeni DAG/cache/batch makalesi.

İlk hata ve fixture düzeltmeleri [early-failures](phase64/early-failures.json) içinde
korunur. [source-gui-final](phase64/source-gui-final/gui.xml) ve
[source-gui-current](phase64/source-gui-current/gui.xml) ayrı3pass/1fail koşulardır;
sonraki [source4pass](phase64/source-gui-verified/gui.xml) ve
[wheel4pass](phase64/wheel-gui-verified/gui.xml) ara koşular son5pass ile tek toplam
olarak birleştirilmez. Önceki başarısız testler silinmedi.

Kısıtlar: scheduler, uzak runner, dağıtık cache ve keyfi analiz/model düğümleri
mevcut değil. Batch sweep yalnız analysis.ddof; source yerel snapshot. Run-scoped
native artifact ana dataset zincirine otomatik eklenmez. Kaynak yazma kapalı.
Sistem kimlikleri iç artifact'ta korunur, kullanıcı exportunda çıkarılır. Dış dosya
ile proje commit arasında crash orphan bırakabilir; otomatik sahiplenme/overwrite yok.
Varsayılan2GiB değişmedi; bu küçük koşular önceki uzun retained-heap/minimum donanım
kapısını kapatmaz. Fiziksel masaüstü, insan/AT, temiz offline installer ve remote CI
çalıştırılmadı; önceki resmî kabuller açık. Stage/commit/push yapılmadı.
