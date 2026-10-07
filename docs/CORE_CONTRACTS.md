# Veri_Ufku — çekirdek sözleşmeler v1

2026-10-06; normatif tasarım; Faz 01 asgari Binding, JobSpec/State/Result, Progress, AppError, Capability, Provenance ve ComputeBudget sınıfları uygulanmıştır. Dataset/Column/Operation/ML sözleşmeleri henüz plan düzeyindedir. Tüm adaptörler bu tek kaydı genişletir; bağımsız registry/bütçe/provenance kopyası kurmaz. Ayrıntılı doğrulama ilgili faza aittir.

## Kimlikler ve soy ilişkileri

Bütün kimlikler isim alanlı UUIDv4 (128 bit); kalıcı kayıtta çakışma unique constraint ile reddedilir. Sıra numarası veya tek başına içerik hash'i kimlik değildir. Hash bütünlük içindir. DatasetId mantıksal tablo; DatasetVersionId değişmez veri+şema+rol+provenance sürümü. Fiziksel snapshot hash'i değişmeden yalnız rol/isim değişen sürüm yeni kimlik alabilir; eski sonuçlar değişmez.

ColumnId kolonun semantik kimliği. Rename aynı ColumnId, yeni display_name/şema sürümü; tarifler isim yerine kimliği referanslar. Drop ve aynı adla yeni kolon yeni ColumnId; derived kolon yeni ColumnId ve parent kolon ilişkisi. Join çakışan/iki kez kullanılan kolonlara yeni çıktı ColumnId + input dataset/kolon bağı üretir. Append kolon eşlemesi kullanıcı onaylı; isim aynı diye otomatik kimlik birleşmez. Yeni dosya/model girdisi eşlemesi açık rol/tür/birim haritasıdır.

SourceRecordId değişmez SourceSnapshotId içindeki her kayıt için tahsis edilir. Aynı içerikli iki kayıt ayrı kimlik. Kaynak konumu (byte aralığı, Excel sayfa/satır, Parquet row-group/offset, JSON yolu) yalnız locator; kimlik değildir. Import edilen temel RowId ayrı UUID + tek SourceRecordId bağı. Aynı snapshot/config ile yeniden çalışma kaydedilmiş kimlik haritasını kullanır; yeni import SourceSnapshotId ve yeni kimlik alır. Kimliklerin farklı importlarda aynı kalacağı iddia edilmez.

| İşlem | Çıktı kimliği ve lineage |
|---|---|
| Hücre dönüşümü, rename, filter, sort | Korunan mantıksal kayıtların RowId'si korunur; sürüm yeni. Filtre görünümü selection spec; kalıcı filtre yeni sürüm. |
| Append | Yeni namespace RowId; input dataset/version/RowId bağları. Aynı dataset'i iki kez append etmek iki kaydı ayırır. |
| Join | Çıktı eşleşmesi başına yeni RowId; sol/sağ RowId, branch occurrence ve join tarifi. Outer unmatched taraf absent, sahte kaynak id yok. |
| Explode | Her çıktı için yeni RowId + parent RowId + liste yol/öğe occurrence. İçeriği aynı öğeler ayrılır. |
| Aggregate/pivot | Her çıktı grup için yeni RowId; tüm katkı kayıtları set referansı + keys/spec. Tek kaynakmış gibi gösterilmez. |
| Dedup | Açık kararlı sıra ile tutulan RowId korunur; elenen RowId/SourceRecordId'ler ayrı duplicate-group relation ile saklanır. |

Büyük lineage: compact ordinal sözlük + delta/range/Roaring benzeri bitmap veya Parquet ilişki parçaları; UUID↔ordinal sözlüğü kalıcıdır. Aggregate üyeleri expression+immutable version ile tembel çözülebilir, algoritma sürümü saklanır. İçerik hash'i ortak diye kayıtlar birleştirilmez. RowCount ile lineage count/kayıp/çoğalma bağı kontrol edilir. Sıkıştırma formatı Faz 09/11'de benchmark ile seçilir; bu aşamada milyonlarca UUID JSON'a açılmaz.

## Domain sorumlulukları ve asgari alanlar

| Tip | Sorumluluk / zorunlu alanlar |
|---|---|
| Dataset | dataset_id, project_id, kullanıcı adı, versions referansları; aktif sürüm işaretini depo okur. Bellekte tüm tablo değildir. |
| ColumnProfile | version_id, column_id, scope, valid/null/nan/inf counts, min/max ve yöntemli quantiles, sample metadata; rol belirlemez. |
| ColumnRole | column_id, dtype'dan ayrı semantic_role (identifier/measurement/category/ordinal/time/group/target/text/ignored), unit, ordinal_order, proposed/confirmed, gerekçe; sayısal kimlik ölçüm sayılmaz. |
| OperationSpec | operation_id, schema_version, method_id/version, tipli parameters, input_version_ids, input_column_ids, output schema, learned_scope, seed, loss_policy, dependency ids; yürütme sonucu değildir. |
| DatasetVersion | version_id, dataset_id, parent_ids, schema/role_version, recipe_version_id, immutable snapshot_uri/hash, row_count, provenance_id, created_at. |
| AnalysisResult | result_id/version, analysis_spec/config_revision, dataset_version_ids, filters, scope, method/version, metrics/artifact_refs, warnings, provenance_id; UI state taşımaz. |
| ChartSpec | chart_id/version, result_ref, plot_type, ColumnId mapping, aggregation/filter/scope, axes/unit/category_order, bins, style, selection mapping, export size/DPI; veri hesabını gömmez. |
| Job | job_id, capability_id, bound dataset/config versions, budget, state, phase/progress, cancel token, result/error_ref, submitted/started/ended timestamps. |
| LearningArticle | article_id, content_version, locale, method/capability links, plain_summary/example/when/when_not/interpretation/theory/sources; içerik ağsız. |
| ModelRun | run_id, dataset/recipe/ml_pipeline/protocol versions, target/features, train/validation/test membership refs, fitted_scope, params/seeds/backend versions, metrics/artifacts, final_test_ledger_ref. |
| ProjectManifest | format_version, project_id, commit_id, parent_commit, dataset/recipe/result/model versions, relative artifact paths/size/hash, source snapshot metadata, environment/content versions, migration record; active pointer dışarıda. |

DatasetVersion, recipe_version_id, ml_pipeline_version_id ve result_version ayrı. Tarif değişince eski veri/sonuç ezilmez. Job güncel config'e yeniden bağlanamaz. Undo aktif commit/sürüm pointer'ını önceki kayda taşır; redo eski dalı korur. Proje silme ve geçmiş temizleme ayrı kullanıcı seçimi ve referans taraması ister.

## Tipli ve serileştirilebilir tarif

JSON UTF-8; `schema_version` ve discriminated `kind` zorunlu. Decimal/büyük integer kanonik ondalık string + dtype; datetime ISO8601 + timezone; float NaN/inf JSON özel sayı olarak yasak, tag ile ifade edilir. Hash için sıralı anahtarlar ve sabit serialization tanımı, nondeterministic timestamp tarife dahil edilmez. İzinli operation registry parameter type/range kontrolü yapar; unknown kind/version kontrollü reddedilir, migration eski tarifi değiştirerek değil yeni versiyonla. Kod string'i veya Python object pickle'ı tarif değildir.

```json
{
  "schema_version": 1,
  "recipe_version_id": "recipe:<uuid>",
  "nodes": [{
    "operation_id": "op:<uuid>", "kind": "text.trim", "method_version": 1,
    "input_version_ids": ["dv:<uuid>"], "column_ids": ["col:<uuid>"],
    "parameters": {"side": "both", "unicode_whitespace": true},
    "learned_scope": "none", "loss_policy": "reject", "depends_on": []
  }]
}
```

Bu örnek şema taslağıdır; mevcut engine/API değildir. Faz 09 doğrulayıcı gerçek UUID/registry/acyclic dependency/input type doğrulaması ekler. Veri tarifi genel temizleme zinciridir; ML pipeline eğitim fold'unda fit edilen fill/encode/scale/select ve estimator zinciridir. Genel tarifte learned_scope = none/dataset/subset ve fit_version/kapsam bilgisi; model önkontrolü ham veri bağımlı geçmişini de inceler. Hazırlık hedefe veya test dağılımına bakmışsa otomatik olarak sızıntısız sayılmaz.

## Ortak hesap anlamı — semantics_version=1

| Alan | Ortak davranış / sınır |
|---|---|
| Null / NaN / inf / empty | Null eksik; NaN kayan nokta geçersiz sayısı, ±inf sonlu olmayan değer, boş string geçerli metin. Ayrı sayılır. Kullanıcı null marker/trim dönüşümü seçmeden birleştirilmez. İstatistik/model sonlu sayılardan hesaplar; dışlanan null/nan/inf ayrı sayım. All-missing sonuç null + uyarı, 0 uydurulmaz. |
| Integer / decimal | Int64/UInt64 aralığı ve tamlık korunur; büyük kimlik string önerilir. Decimal precision≤38 ve scale açık; round half-even yalnız kullanıcı seçtiğinde. Float64'e dönüşümde 2^53 üzeri integer ve temsil edilemeyen decimal kaybı raporlu/izinli veya reddedilir. |
| Time / timezone | Naive tarih UTC varsayılmaz; kullanıcı tz seçer. Zoned instant UTC microseconds + IANA zone saklar. DST ambiguous/nonexistent reddet veya açık fold/shift tercihini önizle. ns→us kaybı reddet/önizle. Excel 1900/1904 sistem ve sahte 1900-02-29 ayrı importer kararı. |
| Category | Nominal sırasız; görünüm sırası ilk karşılaşma + kaydedilen stable ordinal veya açık kullanıcı sırası. Ordinal semantic_order zorunlu. ML label/feature order ayrı kaydedilir. |
| Sorting ties | Seçili keys, nulls last; eşitlikte immutable input order token + RowId. Token konum olabilir ama kalıcı kimlik değildir. Unicode metin sırası code-point, Türkçe collation otomatik varsayılmaz. |
| ddof | Örnek varyansı/std ddof=1; n≤1 tanımsız. Popülasyon ddof=0 ancak açık yöntem. Sonlu kayıt n'si görünür. |
| Quantile | linear interpolation: h=(n−1)q, iki komşu arasını doğrusal; median q=.5. Büyük veri approximate quantile ayrı capability/method, hata ve kapsam etiketi. |
| Join null / NaN | Null keys eşleşmez (`nulls_equal=false`); NaN/inf keys ilk ortak destek kapsamında reddedilir. Boş metin boşla eşleşebilir. Çoklu eşleşme ve row explosion önizlemesi zorunlu. |
| Aggregate | count_rows tüm satırlar; count_valid sonlu/non-null ölçümler. Sum yalnız valid, hiç valid yoksa null. Mean sum/n; mod eşitliğinde tüm adaylar + açık seçim, sessiz tek kazanan yok. Group null ayrı eksik grup. |
| Dedup equality | Null=null yalnız dedup eşdeğerliğinde; NaN NaN ile tek kategori, +0/−0 eşit. Decimal scale numerik normalize; tz instant eşitliği; varsayılan byte string, trim yok. Seçili kolonlar ve ilk/son kararlı kayıt tercihi kayıtlı. |
| Correlation | Pairwise sonlu gözlem, her çiftte n; Pearson/Spearman method/version, ties average-rank; sabit kolon tanımsız. Nedensellik iddiası yok. |
| Filtering | Null predicate sonucu seçilmez; null seçmek açık `is_null`. Filtre view ve kalıcı drop farklı tarifler. |

Motor adapte edemiyorsa desteklenmedi hatası veya ayrı capability; farklı varsayılanı sessiz kullanamaz. Elle hesaplanan fixture: [1,2,3,4] ortalama 2.5, medyan 2.5, örnek varyans 5/3, q.25=1.75; [null,NaN,inf," ",""] ayrı sınıflar. Float64 birikim toleransı gerekçeli (örn. küçük fixture absolute 1e−12); integer/decimal eşitliği tam. Her motor karşılaştırması gelecekte bağımsız beklenenle test edilir, aynı kütüphaneyi yeniden çağırmak referans değildir.

## Asgari capability kaydı

Capability v1: capability_id, version, kind(import/transform/stat/model/chart/export), maturity(mevcut değil/deneysel/kararlı), method/backend/version, input_schema/dtypes/roles, supports {null,nan,inf,decimal,tz,sparse,weights,group,time,streaming,predict,proba,interval,safe_serialization,cancel}, limits {rows,cols,ram,temp_disk}, deterministic_policy, output_types, parameter_schema, semantic_version, help_links, requirement_ids, evidence_refs. Destek alanı bool veya enum + gerekçe; bilinmiyor destekli değildir. Disabled optional modül discovery uygulamayı çökertmez. Ağır kataloğun kendisi Faz 29; temel job aynı v1 kaydını Faz 01'de kullanır.

## Asgari provenance kaydı

Provenance v1: provenance_id, source_snapshot_ids/hash/size, dataset_versions, row_lineage_ref, column_lineage_ref, operation/recipe/analysis/model/result versions, scope {full/sample/filtered, population_n, used_n, sampling_method, seed, membership_ref}, filters, method/backend/environment versions, parameters_hash, config_revision, exclusions/reasons, created_at, user_decision_refs, learning_content_version. Seed yoksa null + reason; scope ölçülemediyse unknown açık. Ham kişisel satırlar loga girmez; lineage dosyası proje gizlilik politikasına tabidir.

## Asgari ComputeBudget ve görev

ComputeBudget v1: ram_bytes, temp_disk_bytes, cpu_threads, max_wall_seconds, max_concurrent_cpu_jobs, max_concurrent_io_jobs, device(cpu varsayılan), sample_limit_rows, cancel_grace_ms, reserve_disk_bytes. Pozitif integer, total hardware/free disk önkontrolü. Varsayılan minimum donanım için RAM 2 GiB toplam uygulama+süreç, temp 4 GiB, threads 2, CPU jobs 1, I/O jobs 2, wall 600 s, sample 10k, cancel grace 2000 ms, disk reserve max(1 GiB,%10 çıktı). Kullanıcı maliyet genişletmesi görünür.

Limitler admission + chunk ölçümü + mümkün Linux resource limitleri ile uygulanır; Polars/sklearn RAM tahmini kesin garanti değil. Sınır aşımı worker controlled fail/terminate, yayın yapılmaz. Device desteği CPU; GPU ileride capability seçimi. İş state machine queued→running→succeeded/failed/canceled; running→cancel_requested→canceled veya tamamlanmışsa açık cancel_too_late. Publication ayrı servis state'i. Result yalnız matching versions ise bağlanır.

## Kaynak, örneklem ve final test

Kaynak önizleme okuma sınırı vardır; bütünlük sadece isim/mtime ile kurulmaz. ADR-003 değişmez snapshot tercih eder. Önizlemenin küçük örneği tür kanıtı değildir; gerçek import bütün kayıt doğrulaması/karantina yapar. Örnek membership_ref RowId'lerden veya kayıtlı deterministik selection expression'dan gelir; kaynak sıra değişince seed tek başına aynı kayıt garantisi vermez. Full ile sample sonuç sürümleri ayrıdır.

FinalTestLedger v1: project_id, dataset_version/hash, protocol_id/hash, split_membership_ref, run_id, model/config_version, viewed_at, metrics_artifact, prior_view_refs, post_view_tuning, evaluation_kind(confirmatory/exploratory), independent_evaluation_needed. Append-only kayıt; yeni run aynı test kullanımını gizleyemez. Proje dışındaki kullanıcı davranışı tamamen izlenemez.

## Faz 01 bağlama

`domain/contracts.py` ve `domain/capabilities.py` tek asgari Python kayıtlarıdır. Demo provenance scope=infrastructure_demo, kaynak/lineage boş, seed kullanılmama gerekçesi deterministiktir; veri analizi gibi kaydedilmez. Demo-session sürüm etiketi import edilmiş kalıcı DatasetVersionId değildir. Manager bütçe ve capability'yi submit sırasında doğrular; worker çıktısı original dataset/config bağıyla JobResult olur. `result_for` yalnız başarılı ve her iki sürümü eşleşen sonucu açar. Metot birimleri ölçülebilirken progress done/total, bilinmiyorsa total=None. Ölçülen RSS/temp örneklenir; fiziksel peak garantisi değildir. [ADR-005](adr/005-runtime-jobs-lock.md).

## Faz04 kalıcı durum bağı

`storage/project_model.py` ProjectManifest format_version=1 ve bounded JSON state doğrulayıcısıdır. Dataset kimlikleri/sürümleri, işlem/sonuçların dataset_version_ids bağı ve seed değerleri kalıcıdır; tam Dataset/Operation yürütme modelinin yerini almaz. Source fingerprint sha256+size; immutable artifact URI/hash/size ve Parquet rows/schema ayrı. `storage/project_store.py` ACTIVE ile yayınlar; AUTOSAVE parent_commit bağını kontrol eder. Sonuç uyumu kaynak doğrulaması bilinmediğinde güncel sayılmaz. [Uygulama kararı](adr/007-project-store-phase04.md).

## Faz05 uygulama bağı

Faz05: ImportSettings/v1 tek preview/full parser girdisidir; varsayılan metin/null seçimi açık, float yaklaşık/Decimal(38,6) sınırı kesin. SourceSnapshotId yeni importta, SourceRecordId her veri kaydında, RowId her kabul edilen kayıtta UUIDv4; locator fiziksel satır başlangıcı/bitişi. ColumnId metadata listesinde; kabul haritası dataset Parquet, karantina kendi kaynak kimlik/konum/raw/reason Parquet dosyasında. Shared Provenance full/config_revision/seed/parameters_hash/backend taşır; source fingerprint metadata ile bağlanır. Manifest2 dataset import_metadata/quarantine_uri doğrular; metadata count/schema artifact ile uyuşmalı. [ADR-008](adr/008-delimited-import-phase05.md).

## Faz06 native import bağı

StructuredSettings/v1 ve data-only native_schema; manifest3. JSON/JSONL eksik/null recursive rapor, Decimal≤38/kayıpsız açık metin sınırı; XLSX1900/1904/naive us/serial; Parquet native nullable/list/struct/Decimal/UInt64/ms-us-ns/timezone korunur. Native saklama ortak analitik us normalizasyonuna sessiz dönüşüm yapmaz. JSON liste açmada ortak SourceRecordId, her çıktı ayrı RowId/expansion_index/locator. [Kesin davranış ve destek sınırları](adr/009-structured-import-phase06.md).

## Faz07 katkısı

Faz07: Role fiziksel type değildir. ColumnId semantik metadata ve parent dv; aynı immutable snapshot metadata sürümleri. RowId görüntü sırası değildir. Profil açık dataset/view/full/firstN kapsamı, null/NaN/±inf ayrı sayımları, ddof0/1, linear quantile, Decimal80 aritmetik ve provenance taşır. Integer/Decimal tam; timezone/ns native range; nested unique destek sınırı açık. [ADR-010](adr/010-dataset-view-phase07.md).

## Faz08 katkısı

Faz08 kalite: full/filtered/sample ve used/population/dataset n ayrı; bulgu observation/candidate/violation, ilk5 RowId örnekleri ve taranan kayıt paydası. İhlal açık kullanıcı kuralına göredir. Öneri deterministik id/reason/precondition/impact/operation_id/learning_id/available taşır; olmayan işlem available=false. Tek puan ve otomatik veri değişikliği yok. [Karar](adr/011-quality-phase08.md), [kanıt](evidence/PHASE08.md).

## Faz09 uygulama bağı

OperationSpec/v1 + RowLineageSpec/v1 `operations/contracts.py`; full preview/apply ortak çıktı `operations/engine.py`. applicability/validation/impact/status/provenance yürütme kaydında, yöntem/schema/input/ColumnId/output_schema tarifte. DatasetVersion5 operation_id/output_schema ve immutable parent; workflow.heads/redo state içinde kalıcı. Rename/drop/filter çalışır, roles aynı metadata geçmişindedir. Future sort/join/explode/aggregate/dedup yalnız tipli köken sözleşmesidir. [ADR-012](adr/012-versioned-operations-phase09.md), [kanıt](evidence/PHASE09.md).
