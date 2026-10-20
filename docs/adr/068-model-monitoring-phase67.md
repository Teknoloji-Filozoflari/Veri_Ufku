# ADR068 — Faz67 yerel batch model izleme

2026-10-16 DEC67-01. Yalnız açık Faz67 talimatı; Faz68 yetkisi yok.
Python/PySide6/QML Linux Veri_Ufku çekirdeği ve ortak registry/ComputeBudget/
Provenance/ProjectStore korunur. Yeni servis veya training registry yoktur.

## Veri ve hesap sözleşmesi

MonitorSpec kapalı declarative JSON≤64KiB. Ayrı reference/window DatasetVersion,
açık ColumnId feature eşlemesi/kind/continuous, [window_start,window_end),as_of,
eşikler, optional model record IDs veya use_champion_route gerekir. Timestamp ISO
ve timezone offset zorunlu; end≤as_of. event_time seçilirse gerçek satır zamanı
[start,end) ile filtrelenir. Seçilmezse tüm snapshot kullanılır, tarih aralığı yalnız
kullanıcı beyanıdır; timestamp membership uydurulmaz. Sessiz sample yok: kaynak başına
1..10000satır/64kolon,1..32feature, categorical≤512support, bin2..20; erken sample/RAM/
disk/time/tasks/native thread sınırları korunur. Reference/window/labels immutable
hash/source snapshot refs; seçili RowId/SourceRecordId native artifact içinde.
Kaynak/metadataya write/cast/repair yapılmaz. Missing/type/unit/ordinal farkları
ayrı alarm; eksik mapped kolon raporlanır. Semantic metadata birim değişiminde
sayısal karşılaştırma yapılmaz. Kolon adı envanteri eklenen/eksilen adları gösterir,
farklı ColumnId'leri otomatik aynı saymaz.

Numeric: finites only; reference quantile cuts, iki sonsuz tail, additive0.5 count
smoothing PSI; reference/window bin counts ve dışlanan n saklanır. Constant reference
kontrollü; tails yeni değerleri kapsar. PSI betimsel operasyonel eşik, evrensel test
veya0.2 zorunlu bilimsel sınırı değildir. Wasserstein kaynak biriminde; kullanıcı
unit-aware threshold seçer. KS D effect sürekli olmayan numeric veride de betimsel
verilir; p yalnız independent+continuous açık ve within-sample ties yokken asymp
hesaplanır. Geçerli KS p'lerine bu rapor içinde Bonferroni, ayrıca D effect threshold.
Büyük n küçük farkta küçük p üretebilir; tekrar pencereler/global alarm ailesi ayrıca
kontrol gerektirir. Categorical: union support/counts, SHA256 category keys, unseen
count ve base2 Jensen–Shannon distance [0,1]; category raw text summary'ye girmez.

Kalite: seçili feature missing/nonfinite oranları ve eşikleri. Faz32 mevcut dataset
schema_contract definition'ı destekli tek-tablo kurallarıyla aynı motor kullanılarak
seçili pencere üzerinde ölçülür; rule severity/violation sayıları raporlu, raw example
summary'ye taşınmaz. FK rules bu modülde unsupported listesinde; genel kalite ekranı
ayrı cross-table kontrat yoludur. Missing contract için uydurma validasyon yok.
Kalite raporu veri düzeltmez; geçersiz model input için mevcut predict reject yolu.

## Frozen scoring, hedefler, shadow

Yalnız projede completed baseline güvenli .vumodel regression/classification kayıtları.
Native tensor/forecast/unsupervised servis edilmiş sayılmaz. Paket bounded bytes ile
okunup fingerprint doğrulanır; private snapshot aynı bytes ile kapalı loader'a gider.
Expected card/label order/version/type whitelist korunur; pickle/joblib/arbitrary code
load yok. Yeni veri yalnız transform/predict; fit_calls0. Modelin kayıtlı final-test
RowId'leriyle çakışan kaynak scoring reddedilir: Faz16 test-use defteri bypass edilmez.
Yeni dış kaynaktaki aynı kişiyi evrensel olarak bulma iddiası yok; namespace/source
kimlik sorumluluğu görünür. Training/validation referansı genelleme skoru sayılmaz.

Labels yokken metrics/calibration None, status labels_unavailable. Konfigüre labels
unique non-null String key ve açık key_namespace ile eşlenir; sayısal→string cast,
satır sırası/fuzzy eşleme yok. Label arrival≤as_of, hedef non-null; duplicate key,
unseen class/label type ve label time<event time reddi. Referans/current aynı business
key ile çakışıyorsa ayrı event key gerektirir. Gelecek arrival dışlanır; pending,
matched fraction, overdue ve gözlenen label delay yalnız uygun zaman bilgisiyle.
Aynı batch'in daha yeni labels snapshot'ı yeni immutable run üretir; önceki raporu
revize etmez. Gerçek hedef alt kümesi seçilmiş/gecikmiş olabilir; bütün popülasyon
performansı veya concept drift kesin bulundu iddiası kurulmaz.

Regression MAE/RMSE; classification accuracy/log-loss ve explicit multiclass Brier
sum: binary pozitif sınıf Brier'ının iki katıdır. Label order aynı; class counts/
missing classes ve fixed-width one-vs-rest reliability bin n/mean_probability/
event_rate/ECE kaydedilir. Brier/log-loss kalibrasyon, discriminative power ve hedef
belirsizliğini birlikte yansıtır; tek başına kalibrasyon metriği değildir. ECE bin
seçimine/n'ye bağlı. Referans labels açık seçilmişse observed-subset metrik ve ECE
farkı/eşik raporlu; aksi durumda değişim unavailable. Min_n sağlanmazsa metrik yok.

Champion/challenger aynı window RowId ve SourceRecordId, aynı target/purpose/label
order ile frozen scoring; disagreement/mean absolute prediction difference raporu.
Labels varsa her model aynı matched subset üzerinde evaluate; yoksa performans
karşılaştırması yok. Shadow üretim etkisi/online A/B veya deploy değildir.

## Audit, rollback ve lineage

Yeni MonitoringRun/v1 existing results journal + hashli private16MiB JSON artifact;
summary identity/refs/config/provenance/capture; kaynak keys/prediction records yalnız
private artifact. Tek ProjectStore atomic publish, quota/reserve, stale draft ve
kalıcı test-use geçmişi denetimi. Worker Qt/ProjectStore/ACTIVE almaz; parent pinned
read-only paths/immutable envelope verir. Parent model/source/membership/test ledger
bağlarını doğrular. Monitor sonuçları eski draft ile silinemez. Açmak hash kontrolü
yapar, hesap/API/eğitim başlatmaz. Ortam/code/hardware RunCapture yeni run'da gerçek;
eski provenance uydurulmaz. Hash özgünlük imzası değildir.

Yerel champion seçimi ExperimentEvent/v1 aynı append-only hash zincirinde model_route
revision: model record/fingerprint, previous record/event, reason/rollback/scope.
Rollback yalnız son kaydın gerçek previous model referansına döner; eski artifact,
run/dataset lineage, test geçmişi korunur. use_champion_route:true scoring mevcut
route modelini çözer ve kullandığı event ID'yi run'a sabitler. Explicit model seçimi
route'u izlemez. Bu yerel scoring referansıdır; dış deploy/auto promotion değildir.
Alarm yeniden eğitim başlatmaz. Yeni eğitim mevcut kullanıcı başlatılan config/run
ve model ailesinin onay/preparation/test-use sözleşmesi üzerinden ayrı yapılır.

## CLI ve loopback API

`python -m veri_ufku.modeling.monitor_cli --project PROJE --cache PROJE_DISI_CACHE
--spec RECIPE.json --allow-batch-scoring` açık eylemdir; response yalnız run/record
kimliği/status/labels kapsamı. Aynı supervised spawn+ComputeBudget+ProjectStore;
SIGINT/SIGTERM cancel, eksik sonuç başarılı olmaz; output/model overwrite yok.

API yalnız aynı CLI'de `--serve --allow-api --allow-batch-scoring
--credential-ref KEYRING_REFERANSI --bind 127.0.0.1 --port 8767`. Sistem keyring
Linux Secret Service dışında plaintext/env fallback yok. Bearer32..128 random
URL-safe karakter yalnız memory; log/config/export'ta değer yok.127.0.0.1 harici bind
reddedilir;127.0.0.1 plaintext local-user/process trust sınırıdır, TLS/internet
servisi veya OS sandbox değildir. Browser CORS açılmaz; auth timing-safe compare.
POST /score body yalnız {"spec": MonitoringSpec}; raw data/path/model upload/code,
query-token, duplicate JSON fields, chunked transfer, auth duplicate, invalid
Content-Type ve >64KiB body reddedilir. Request socket2s; tek concurrent request,
bounded task budget. Header/parser sınırlamaları Python HTTPServer sınırlarıdır;
untrusted remote production exposure iddiası yok. Response run IDs; kişisel satır,
label/prediction/secret yok. Request/error payload loglanmaz. Tekrar POST yeni run
üretir; exactly-once/idempotent retry garantisi yok. API training/rollback endpoint'i
yok. GUI komut paleti CLI/API'yi otomatik başlatmaz, ayrı terminal eylemini açıklar.

Auth sistem keyring adapter yolu mevcut sözleşme; gerçek HTTP testleri ephemeral
test bearer ile auth/schema/real scoring yapar. Bu, kurulu desktop Secret Service
credential provisioning veya fiziksel çok kullanıcı güvenlik testi değildir.

## Resmî yöntem kaynakları

2026-10-16 incelendi:
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ks_2samp.html
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wasserstein_distance.html
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.distance.jensenshannon.html
- https://scikit-learn.org/stable/modules/calibration.html

PSI formülü açık count/smoothing/bin tarifiyle test edilir; backend'e olmayan PSI
API'si atfedilmez. Resmî kabul, bounded teknik teslimden ayrıdır.

Paylaşılan capability sözleşmesi düzeltmesi: Faz52 sonrası bazı geç kayıtlar ortak
metadata tamamlama geçişinden sonra eklendiği için boş alan taşıyordu. Son fallback
sadece eksikleri doldurur; typed DAG inputs ve var olan declarative limits/support
aynen korunur. Bilinmeyen fit/predict/proba/transform/interval/persist unknown'dır;
metadata varlığı backend test edildiği iddiası oluşturmaz. Ana GUI raporu readable
aggregate özetidir; code/env hashes ve ayrıntılı config native artifact/lineage'da
kalır, beginner akışında raw code file listesi gösterilmez.
