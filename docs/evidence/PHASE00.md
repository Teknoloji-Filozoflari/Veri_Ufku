# Veri_Ufku — Faz 00 kabul kanıtı

Tarih: 2026-10-06. Ortam: ENV-00 (CachyOS, Python3.14.7, Qt6.11.2; ayrıntı ENVIRONMENT.md). Kanıt türü: belge/tasarım incelemesi ve ortam probe; gerçek uygulama özelliği değildir. Bağımlılık lock henüz yok.

## Yapılan kontroller

- Belge checker: tüm 76 faz, kaynak şart kimlikleri/tam metin, DAG, özet tutarlılığı, kanıt/path/anchor, ISO tarih ve yerel link kontrolü. Son komut çıktısı `checks.txt` içinde.
- Dokuz unittest: sağlam kayıt; progress conflict; kanıtsız/eksik şartla false completion; missing evidence; cycle; unverified dependency; source scope loss; duplicate ID; broken local link.
- Ruff yalnız scripts/tests için kurulu 0.16.10: lint ve format. Dev bağımlılık lock Faz01.
- QML offscreen bir root, Agg boş100×100 buffer40k; tekrarlanabilir [JSON](environment-probe.json). Bu uygulama launch/performance testi değildir.
- İki tema SVG render/PNG view, [token contrast](token-contrast.json). Gerçek erişilebilirlik kabulü değil.

## Alt gereksinim kayıtları

<a id="e00-001"></a>

**F00-001:** PROJECT_RULES/UI_DESIGN_BRIEF tam kaynak text karşılaştırması; AGENTS okuma listesi. Kalıcı sözleşmeler korunmuş. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-002"></a>

**F00-002:** pwd/list/rg/git status, OS/Python/package metadata/CPU/RAM/FS/Qt probe; resmî kaynak web okuması. Eksik paket, Git ve Python uyumu açık. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-003"></a>

**F00-003:** PRODUCT US-01/02/03 adım-girdi-çıktı/başarı senaryoları incelendi; 580 toplam/58 ortalama/45 medyan elle kontrolü. Bunlar gelecek kabul örnekleri. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-004"></a>

**F00-004:** UX SCR-01..08 ve navigation/state/geri dönüş çizelgesi; sekiz ekran listesi, başlangıç/uzman aynı state tasarımı. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-005"></a>

**F00-005:** ARCHITECTURE Qt UI/domain/services/adapters/storage/jobs/charts/learning ayrımı ve worker→UI versiyon kontrolü; analitik kod eklenmedi. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-006"></a>

**F00-006:** CORE_CONTRACTS on bir domain tipinin alan/sorumlulukları, dataset/recipe/ML/result version ayrımı. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-007"></a>

**F00-007:** UUID/SourceSnapshotId/SourceRecordId/RowId/ColumnId ayrımı, rename ve join/explode/aggregate/dedup lineage tablosu; compressed/lazy büyük lineage sınırı. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-008"></a>

**F00-008:** Tipli JSON recipe ve semantik tablosu, null/NaN/inf/empty/decimal/tz/ties/ddof/quantile/join/aggregate; ML fold fit ve genel learned cleanup riski. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-009"></a>

**F00-009:** Capability v1/Provenance v1/ComputeBudget v1 alanlar, job state machine ve bound versions; ağır registry geliştirilmedi. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-010"></a>

**F00-010:** ADR-003 tek ACTIVE yayın noktası, SQLite/Parquet/manifest hazırlama/validate/fsync/publish, flock tek writer/recovery; source mutation ve symlink/network FS sınırı. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-011"></a>

**F00-011:** ADR-001 teknik kimlik ve provisional desktop ID; ADR-004 offline çalışma/kurulum/optional yerel paket ayrı, lisans/Qt yükümlülük planı. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-012"></a>

**F00-012:** PERFORMANCE minimum target + small/medium/large, launch/preview/UI/cancel/RAM/disk metodları; ölçüm başarılı iddiası yok. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-013"></a>

**F00-013:** PHASE_PLAN ve MATRIX 76 faz DAG, source kabul paragrafları, CORE/UI/PRO şart kimlikleri; checker çelişki ve kapsam kaybını reddetme testleri. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-014"></a>

**F00-014:** DEVELOPMENT çalışma/test/lint/CI/early package planı; ACCEPTANCE_POLICY kanıt tipleri ve release kapıları. Remote CI çalıştırılmadı. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-015"></a>

**F00-015:** Orange/KNIME/jamovi/JASP/LabPlot resmi metin ve ekran akış kaynakları okundu; resim/PDF erişim denemeleri ve görsel payload sınırı açık kaydedildi. Görsel kabul UI-REF-VIS bekliyor. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-016"></a>

**F00-016:** Üç ortak sistem statik SVG ve light/dark QtSvg PNG render valid; view_image ile incelendi. Alt CTA/typography/scope/prototype tutarlılığı, tablo görünümü ve bilgi yoğunluğu iyileştirildi. Altı token contrast≥4.5; gerçek AT/keyboard/scaling yok. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-017"></a>

**F00-017:** PRODUCT D-01 read-only ve panodan kayıt yapıştırmama; ek edit kapsamı seçilmedi; D/O/R açık karar ve risk kayıtları. Sonuç: Faz00 belge kapsamı doğrulandı.

<a id="e00-source"></a>

F00-S001..S007 özgün faz paragrafları sırasıyla F00-001..017 belge kontrollerine bağlıdır: S001 genel kapsam; S002→002/005/013/014, S003→003/017, S004→006/007/008, S005→002/010/011/012, S006→003/004/005/013/014, S007→001/007/008/009/010/011/012/013/017. Belgeler kullanıcı faz00 talebiyle karşılaştırıldı; sonraki faz başlatılmadı.

## Yapılmayanlar ve açık kapılar

Analitik import/hesap/model/gerçek QML adaptörü, masaüstü kullanıcı akışı, minimum8GB benchmark, uygulama lock çözümü, Linux paket smoke, çevrimdışı kurulum/çalışma kabulü, remote CI ve Git commit yapılmadı. Resmi referans görselleri yorumlanabilir payload vermedi; UI-REF-VIS doğrulanmadı. Python3.13 aday runtime kurulu değil, tüm yığın uyumlu olduğu iddiası yok. Bu işler ilgili faz kapısıdır, belge başarısı onları kabul etmez.

## Faz kararı

Faz00 belge/plan kabulü: doğrulandı. Uygulama henüz mevcut değil. Faz01–75 başlanmadı; hiçbiri tamamlandı/ertelendi sayılmadı. Kullanıcı istemeden sonraki faza geçilmedi.
