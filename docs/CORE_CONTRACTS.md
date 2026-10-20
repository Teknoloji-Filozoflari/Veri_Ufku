# Veri_Ufku — çekirdek sözleşmeler v1

Normatif tasarım ve Faz00–26 teknik uygulama bağı; faz kabulleri matriste ayrı. Binding, JobSpec/State/Result, Progress, AppError, Capability, Provenance, ComputeBudget; Dataset/Column, OperationSpec, ChartSpec ve export/rapor sözleşmeleri uygulanmıştır. Faz16 BaselineRun/ValidationPlan/final test defteri uygulanmıştır; Sınırlı estimator ModelRun ve güvenli model yaşam döngüsü sonraki faz bölümlerinde tanımlıdır. Aşağıdaki faz bölümleri sözleşmenin hangi aşamada uygulandığını açıklar. Tüm adaptörler bu tek kaydı genişletir; bağımsız registry/bütçe/provenance kopyası kurmaz. Ayrıntılı doğrulama ilgili faza aittir.

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

## Faz10 katkısı

OperationSpec/v1 cleaning tarifleri destination chain/copy ile aynı full preview/yayın yolunda. DatasetVersion6 forked_from_version_id ve dedup lineage_uri; immutable survivor RowId, tam üyelik Parquet. Açık null/NaN, mod/order/equality, hassasiyet ve DST politikaları; hata/null etkileri. learned_scope=dataset ve leakage_review_required geçmişi genel temizliği gelecekte fold-içi ML fit dönüşümünden ayırır. [Karar](adr/013-cleaning-phase10.md), [kanıt](evidence/PHASE10.md).


## Faz11 katkısı

Faz11: OperationSpec/v1 input_version_ids gerçek girdiler, parent_version_ids birincil undo imleci. Yeni join/group/pivot satırları tek SourceRecordId taşımaz; üyelik kenarları bütün gerçek girdi RowId ilişkilerini saklar. Full tahmin, explicit eşitlik/null/sıra/Decimal/tarih politikası; readonly kaynak ve çıktı hedef koruması. Nested hesap yapılmaz, seçilmeyen alanlar ve strict append/join alanları native korunabilir. [Karar](adr/014-transformations-phase11.md), [kanıt](evidence/PHASE11.md).


## Faz12 ChartSpec ve seçim

ChartSpec/v1 alan kimlikleri, title/axes/units/legend, yöntem/grup/agregasyon, ViewSpec filtreleri, kapsam/null/hassasiyet ve görünüm tercihlerini taşır. Grafik sonucu immutable dataset_version/snapshot fingerprint, kesin profil, scope/population/used, sayısal noktalar ve tam RowId üyelik Parquet'i taşır. Sampling/Diğer/çift n/sabit kolon tanımsızlığı gizlenmez. Int/Decimal Float64 kaybı açık onay ister. Tablo→nokta RowId ile; aggregate nokta→tüm üyeler. Grafik ayarı dataset sürümü yaratmaz; eski sonuç güncel bağa taşınmaz. Tam protokol [ADR-015](adr/015-charts-phase12.md).

## Faz13 paylaşım sözleşmesi

ExportSpec/v1/ReportSpec/v1 seçilen DatasetVersion+SHA256/ViewSpec/kapsamı sabitler. Non-Parquet tür kaybı açık kabul; CSV formül güvenliği String ve başlıkta, sayıyı bozmadan; XLSX inlineStr, sınır/precision görünür. Native Parquet şema/kayıt/sıra hash'i; metin/XLSX bağımsız okuyucu projeksiyon/kayıt denetimi. Makbuz veri sürümü/filtre/sayı/kayıp/politika/hash taşır. Rapor ancestor işlem/bulgu sürümleri, güncel grafik, açık örnek sınırı ve kaynak bilgisi saklar. Hiçbir export mevcut dosyayı/source'u değiştirmez. Rehber veri işleme kararı değildir. [ADR-016](adr/016-release-phase13.md).


## Faz14 — çıkarım sözleşmesi

Birim/bağımsızlık/hipotez açık seçilir. Önkontrol, bir normalite p eşiğinden yöntem seçmez. Eşler kullanıcı anahtarı+önce/sonra etiketiyle kurulur; tekrar kişi/etiket veya eksik anahtar reddedilir, yalnız tam eş seçimi ve dışlamaları kayıtlıdır. İstatistik snapshot'ı değişmez. Float64 dönüşüm kaybı varsayılan reddedilir; yaklaşık izin ve kayıp sayısı kayıtlıdır. Analiz n'si, null/nonfinite ve kişi dışlamaları ayrı saklanır. Rank yöntemleri genel medyan farkı iddiası değildir. Analiz başına p/etki, mevcut CI veya açık yokluk gerekçesi saklanır; CI uydurulmaz. Post-hoc bütün grup çiftleri: Welch t veya Mann–Whitney; Holm/Bonferroni/BH/none seçimi aileyle saklanır, birincil test ve ayrı çalıştırmalar aileye eklenmez. Tekil CI'lar aile CI'ı değildir. Bootstrap/seed null, yöntem deterministik; bağımlılık varsayımı provenance içinde kayıtlıdır. [ADR-017](adr/017-statistics-phase14.md).

## PreparationSpec / PreparationReport / PreparationPlan — v1

PreparationSpec amaç/hedef/özellik ColumnId, estimator ailesi, gerçek source_version, history_action, encoding/scaling/impute/date/selection, grup/zaman, açık identifier/nonfinite/precision ve bağlam notlarıdır. Report origin/source/hash, tam n/eligible/excluded_target, profiller, gerekçeli aday/risk/blockers/history ve plan taşır. fitted=false, leakage_certified=false, fit_scope=null. Plan ml-pipeline UUID, fit_state=not_fitted/fitted_parameters={}, planned training_fold/row_local adımları ve source ColumnId/name/dtype → benzersiz output adlarıdır. Onehot şablonları gerçek kategori sözlüğü değildir; category map/vocabulary/selection mask null kalır. Raw/relocate riskli işlemlerden önceki gerçek sürümden sayım ister; yeni plan geçmiş etkisini çözülmüş saymaz. Atomik results safe JSON; [ADR-018](adr/018-model-preparation-phase15.md).

## Faz16

ValidationSpec/v1 → ValidationPlan/v1: seed, yapı/yöntem, varlık kullanımı, tahmin anı, saniye ufuk ve ColumnId kullanılabilirlik beyanı; değişmez dataset/fingerprint/RowId membership hash ile split/protocol kimliği. BaselineRun/v1 tamamlanmış train/fold-only fit ve scoped/directed metrics, paket/pipeline versions. ModelChoice/v1 prior_test_use_ids/status/invalid_folds; FinalTestUse/v1 dataset/snapshot/split/protocol/run/pipeline/tarih/pending-completed-canceled-failed-stale defteri. Büyük ayrıntı artifact hash kontrollü, metadata özet. [ADR-019](adr/019-validation-baseline-phase16.md).

Faz17: sınırlı sayısal tahmin yolu, Faz15 hazırlığı ve Faz16 split/fold/defteri üstünde gerçek training-only estimator pipeline kullanır. Adaylar baseline/doğrusal/Ridge/RandomForest; seçim yalnız geliştirme CV MAE, final testte tek dondurulmuş aday. MAE/RMSE hedef birimi, R² negatif/sabit hedef sınırı, gerçek-tahmin/artık grafikleri (en fazla1000 örnek; metrik tam bölüm), dar ayar/maliyet sınırları ve test sonrası keşifsel yorum. Ayrıntılı sözleşme [ADR-020](adr/020-regression-phase17.md), gerçek kabul [PHASE17](evidence/PHASE17.md).


2026-10-09 Veri sunumu: ColumnId anahtarlı semantic_metadata içinde isteğe bağlı description (en fazla2000 karakter düz metin) desteklenir. Açıklama role/unit/ordinal_order/confirmed ile yeni metadata DatasetVersion ve roles tarifinde saklanır; kaynak snapshot ve kimlikler değişmez. Eski açıklamasız kayıtlar geçerlidir; dört parametreli rol güncellemesi mevcut açıklamayı korur. DataContent toplamları aktif sürüm import_metadata verisinden gelir; görünüm filtreleri bu toplamları değiştirmez. [Gerçek kayıt](evidence/UI_DATA_CONTENT.md).


## Faz18 kategori tahmini

BaselineRun/v1 additive classification/classes/comparison/decision/decision_validation alanları, ModelChoice/v1 sınıf/eşik/model ayarları ve FinalTestUse/v1 dondurulmuş karar özeti içerir. Kaynak immutable; öğrenilen hazırlık yalnız train/fold içine fit edilir. CV aday seçimi kayıtlı averaging ile F1; threshold seçimi validation RowId üyeliğiyle sınırlı. Final testte grid/aday araması yok. Matrisin sınıf sırası sabit; precision/recall/F1 sıfır bölme0 ve per-class durumuyla raporlanır. Eksik final sınıfı/proba için eğri/AUC tanımsız; PR-AUC trapez, AP ayrı.20 sınıf, Forest20k/diğer100k ve4 milyon yoğun hücre sınırı; resampling/kalibrasyon eklenmez. Yeni veri tahmini veya model paketi Faz20 kapsamı olarak kalır. [ADR-021](adr/021-classification-phase18.md), [gerçek teknik kayıt](evidence/PHASE18.md).


Faz19 UnsupervisedRun/v1 ayrı sonuç sürümüdür; seçilmiş immutable DatasetVersion ve tam fit kapsamı, ölçüm ColumnId, spec/seed/backend/tarih/hash ve ayrı Parquet tüm RowId üyelikleri. İşaretli yeni dataset kaynak kolon/RowId/SourceRecordId değerlerini korur; derived_analysis kaynak sürüm/result bağını denetler. DBSCAN native predict yok, tüm yöntemlerde yeni dosya yolu available=false. Etiketsiz precision/recall=null; silhouette yalnız açık koşullarda.

Faz20 SafeModelPackage/v1: .vumodel ZIP(card.json ModelCard/v1 + pipeline.skops +
SHA256 integrity.json),128MiB/exact runtime/fixed type allowlist. Feature/label
sırası, dtype/unit, fit RowId ve learned preprocessing korunur. PredictionPreview/v1
hash token'ı immutable model/dataset/mapping/policy/batch bağını korur. Tahmin hiç
fit etmez; RowId bire bir left join, dropped-invalid null sonuç/durum ve bütün
orijinal satırlar. Model paket hash'i kaynak kimliği/imza değildir. [ADR-023](adr/023-model-lifecycle-phase20.md).


Faz21 `TimeSeriesSpec/v1` ve `TimeSeriesRun/v1`: tarih/ölçüm/isteğe bağlı grup,
açık sıklık/timezone/resample/agregasyon, ufuk/final/fold/mevsim/pencere/model.
Rolling-origin ve final train/test RowId ayrık, her grup geçmişi ayrı; lag1/trailing
özellik current/future hedefi görmez. Baseline karşılaştırması gerçek; frozen final
seçim, persistent test kullanım defteri, MAE/RMSE ve interval=null. Düzensiz/gap
veri otomatik düzenli/fill sayılmaz. [Sözleşme](adr/024-time-series-phase21.md).


Faz22 TextSpec/v1 ve TextRun/v1: seçilmiş kolon/dil/Unicode/token/ngram/stopword
ve sınırlarla safe summary; ham preview yalnız opt-in ephemeral. Classification
PreparationSpec.text → sparse TextPreparation: vocab/IDF fit RowId yalnız
training fold, evaluation transform-only. Betimsel vocab eğitimde kullanılmaz.
Blank doc sıfır vektör; blank train kontrollü ret. Source hash ve similarity RowId
reopen denetlenir. [Sözleşme](adr/025-local-text-phase22.md).


## Faz23

AnalysisRecipe/v1 kaynak şema/rol/fingerprint ve sürümlü OperationSpec zinciri/seed; RecipeReplay/v1 hash/origin/step/mapping; DatasetChange/v1 full scope; DelayedPerformance/v1 kimlikle eşlenmiş yeni performans. ModelCard/SafeModelPackage ayrı; sessiz fit yok. [ADR-026](adr/026-recipes-monitoring-phase23.md), [kanıt](evidence/PHASE23.md).


## Faz24

ModelResourceForecast yaklaşık maliyettir; estimator fit streaming değildir. Baseline seçili kolonları okur, fit üyeliği güvenli Unicode ndarray ile paketlenir; ModelCard/v1 ve eski üyelik listesi korunur. Cache hit tam fingerprint doğrulamasından sonra kullanılabilir. ACTIVE iptal/hata halinde önceki sağlam yayını korur. [ADR-027](adr/027-performance-phase24.md), [kanıt](evidence/PHASE24.md).

## Faz26 kurtarma ve migration

Kurtarma önizlemesi commit kimliğine bağlıdır; başka autosave geldiğinde
yükleme yeniden inceleme ister. Restore ACTIVE’yi değiştirmez. Desteklenen
şema0–7 açılış/manifest listeleri aynıdır; eski commit/data korunur. SQLite
metadata/companion dış dosyaya hardlink olamaz; geçici artefact hardlink
yayın protokolü korunur. [ADR-029](adr/029-reliability-phase26.md).


2026-10-10 açık kullanıcı tür algılama isteği: yeni CSV/TSV GUI seçimi infer_types=true ayarıyla tüm dosyada türleri doğrular. Tür adayı hiçbir gözlenen değerle uyumsuz olamaz; karışık içerik metin, leading-zero değerler metin kalır; başlık adı ve rakam sayısı türü belirlemez, Int64 sınırındaki tam sayılar kesin saklanır. Sayılar Int64 veya kesin Decimal(38,6), tarih mevcut date_format, boolean true/false/evet/hayır sınırındadır. Otomatik tür etkin olduğunda boş hücre yalnız metin dışı sütunda null olur; metin boşu korunur. Eski/manual infer_types=false sözleşmesi ve açık null_markers korunur; ayar provenance içinde saklanır. Kaynak dosya ve daha önce kaydedilmiş dataset değiştirilmez. [Gerçek test](evidence/UI_DATA_REFINEMENT.md).

2026-10-10 profil düzeltmesi: String fiziksel türündeki eski sütunların içerik türü bütün seçili kapsamda salt okunur, bounded taramayla hesaplanır. content_type ayrı alan, physical_type değişmez; farklıysa tabloda Int64 (kayıt: String) gibi gösterilir. Dolu/null/NaN sayıları gerçek kayıtlı değerlerindir; boş metin null sayılmaz. Tür özeti content_type, stored_types gerçek fiziksel şemadır. Describe/analitik hesaplar fiziksel tür ve rol sözleşmesini korur. [Kanıt](evidence/UI_PROFILE_TYPES.md).

2026-10-10 son kullanıcı gösterim isteği: profil tablosu ve üst tür özetinde teknik tür adları (Int64/String/Decimal…) kullanılır. İçerik türü hücrede tek başına; farklı fiziksel kayıt türü tooltip içinde açıklanır. Veri dönüşümü yapılmaz. [Güncel kanıt](evidence/UI_PROFILE_TYPE_LABELS.md).

2026-10-10 son saklama talebi önceki içerik türü gösterimini geçersiz kıldı: profil yalnız gerçek physical_type gösterir; aktarımda Int64/Decimal fiziksel olarak saklanır. Titanic mevcut aktif sürümü kullanıcı izniyle mevcut convert operasyonu üzerinden dönüştürüldü; kaynak, satır kimlikleri ve geri alma geçmişi korunur. [Gerçek kayıt](evidence/UI_ACTUAL_STORAGE.md).

2026-10-10 kullanıcı kısa not isteği: Anlam ve notlar ayrı Veri başlığı olmaktan çıktı, profil tablosunun altına sütun seçimi/kısa açıklama/Notu kaydet alanı taşındı. Her sütunun taslağı seçimler arasında korunur; açık kayıt projeyi kalıcı kaydeder. applyDescription mevcut rol/birim/sıra/analiz birimi ve confirmed durumunu korur; yeni not role önerisini onaylamaz. Analitik profil onaylanmamış rolün yerine mevcut öneri politikasını kullanır. Kaynak/snapshot/RowId değişmez. [Kanıt](evidence/UI_PROFILE_NOTES.md).


Faz28 mevcut tip ve artifact sözleşmelerini [PRO_ARCHITECTURE](PRO_ARCHITECTURE.md) altında gerçek kod/planlı tip ayrımıyla eşledi. InputSchema, ResultArtifact ve LearningLink genişlemeleri F29 alt işidir; varmış gibi kabul verilmedi. Registry/ComputeBudget/Provenance tek kaynak kalır.

Faz29 aynı Capability registry contract_version2: InputSchema/InputRole/Parameter/MethodSupport/ResultArtifact/LearningLink; legacy yöntem/parametre v1 okunur. Unknown veya uyumsuz capability/sürüm salt okunur; güvenlik/schema doğrulaması atlanmaz. ComputeBudget/Provenance tek kaynak korunur. [Kanıt](evidence/PHASE29.md).

Faz30: format_metadata source Arrow schema token, dictionary scope, value labels/user-missing/weight declaration ve parça hash/name bağlarını korur. RowId/SourceRecordId UUID; locator part/hash/ordinal. __vu_expansion_index additive user_missing map tagged missing'i system-null'dan ayırır; system_missing map Stata/SAS character blank ham String anlamını korur. Strict/union çözümü önizlenir; kaynak mutation publication öncesinde denetlenir. Manifest7/tek registry/ComputeBudget aynı kalır. [Kesin sınırlar](adr/031-advanced-import-phase30.md).


Faz31 ConnectorSpec/v1 yalnız secret-free endpoint/query/filter/keyring-ref/
TLS/budget/API/nesne seçimidir. Source.connector spec + started_at/finished_at
+ details tutarlılık kaydıdır; UUID kimlikler kaynak key locator'undan ayrı.
`captured` source status yerel hash doğrulamasıdır, uzak tazelik garantisi
değildir. Manifest7 eski source kayıtları aynı okunur; yeni additive connector
kaydının eski okuyucuyla forward-compatible olduğu iddia edilmez.
[Sınırlar ve kalıcılık](adr/032-connectors-phase31.md).


Faz32, 2026-10-11: Faz07 ColumnId semantic_metadata alanları additive
measurement_level ile genişletilir. Contract/v1 tanımı ve kontrol durumu
DatasetVersion'a bağlıdır; kapalı declarative kurallar aynı OperationSpec,
ComputeBudget/worker ve ProjectStore ACTIVE protokolündedir. Hata politikası
stop/quarantine/continue açık; kaynakta otomatik düzeltme yok. Onaylı entity
ataması RowId/SourceRecordId'yi korur; tam önceki/yeni canonical ilişki inverse
Parquet artifact'ında, insan kararı Provenance/operation kaydındadır.
Undo/redo immutable sürüme geçer; bağlı sonuçlar otomatik retarget edilmez.
[ADR-033](adr/033-data-contracts-phase32.md), [kanıt](evidence/PHASE32.md).


Faz33 AnalysisSpec additive ağırlık türü/strata/PSU/seed/MI alanları. Registry destek reddi; kaynak dönüşümü yok. AnalysisResult aynı sürümde opsiyonel advanced ve source_columns; advanced artifact seti result/members/details. Parent source kimlik, gözlenen MI hücre ve coefficient covariance/Rubin bağını ACTIVE öncesi doğrular. FoldPreparation joint impute ve özgün missing indicator; legacy defaults tarifte omit. [Gerçek kanıt ve sınırlar](evidence/PHASE33.md).

Faz66 ComputeBudget: toplam cpu_threads ile threads_per_process ayrımı;
max_processes/max_tasks/device_memory_bytes/transfer_bytes aynı frozen sözleşmede.
worker_threads=min(cpu_threads,threads_per_process). Erken limits korunur; start
kapısı CPUjob/process/thread toplamını denetler. Capability execution_memory/device
aynı registry; eski yöntem için out-of-core fit uydurulmaz. Ölçüm ikinci run defteri
değildir. [Sözleşme](adr/067-compute-budgets-phase66.md).

Faz67 MonitoringRun/v1 mevcut results/immutable artifact; MonitorSpec bounded closed
recipe, RowId/SourceRecordId/source/model/capture binding. Labels unique String
business/event key+namespace, arrival≤as_of. Frozen safe scoring fit0; final-test
bypass yok. Model route/rollback mevcut ExperimentEvent zincirinde; gerçek önceki
model referansı ve artifact korunur. API default off/loopback/auth/opt-in; otomatik
ağ/eğitim/deploy yok. [ADR068](adr/068-model-monitoring-phase67.md).


Faz68 ScenarioSpec/v1→ScenarioRun/v1: kapalı declarative tarif; ortak ComputeBudget/Provenance/RunCapture/ProjectStore; synthetic girdi için kaynak/RowId uydurulmaz. Frozen model seçilirse gerçek fit RowId/SourceRecordId/kart/hash bağı ve güvenli same-byte paket. Solver output status run completion durumundan ayrıdır; timeout optimum değil. [ADR069](adr/069-simulation-optimization-phase68.md).


Faz69 LabSpec/v1→LearningLabRun/v1; aynı Capability/ComputeBudget/RunCapture/Provenance/ProjectStore, ayrı geçici örnek ProjectController. Sentetik fixture kimliği user RowId değildir; kaynak/dataset versiyonu uydurulmaz.403module learning coverage, advisory prerequisites; okumak/quiz araçları kilitlemez. [ADR070](adr/070-learning-laboratory-phase69.md).
