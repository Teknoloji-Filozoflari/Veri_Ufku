# ADR061 — Faz60 bounded betimsel sepet/kohort/süreç

DEC60-01,2026-10-15: yalnız açık Faz60 talimatı; Faz61 başlatılmaz. Python/PySide6/QML,
tek SourceAdapter/Capability/ComputeBudget/Provenance/ProjectStore korunur. PatternRun/v1
mevcut neural safe artifact ve experiment projection içinde; model/predict iddiası yok.
Worker Qt/ACTIVE almaz; parent ACK atomik yayın, source hash ve prior test-use defteri.
Küçük metadata özeti; ayrıntılı RowId/SourceRecordId ve hesap çıktıları hash'li artifact.

Native Apriori ve gerçek conditional FP-tree backend: transaction/item uzun tablo,
string/integer kimlik tipi korunur. Null item yalnız tek satır empty basket; karışık
null/ürün reddedilir. Aynı transaction/item reject veya açık set; farklı transaction
ID'de aynı içerik ayrı sepet. Payda bütün transaction ID'leridir; boşlar dahil.
Support count/N, confidence count(A+B)/count(A), lift confidence/support(B).
[Agrawal/Srikant](https://research.google/pubs/fast-algorithms-for-mining-association-rules-in-large-databases/)
Apriori yaklaşımının birincil kaynağıdır. FP-tree weighted conditional prefix yolları
ve global support paydası kullanır. [Han/Pei/Yin/Mao birincil yayını](https://doi.org/10.1023/B:DAMI.0000005258.31418.83) FP-tree/pattern growth yaklaşımını tanımlar. Her ikisi bağımsız brute-force ile karşılaştırılır.
64item/2000basket/5000source row, max5itemset;20k candidate/node,2k incelenen rule üst
sınırı; seçimler daha düşük olabilir. Bütçeyi aşan eksik liste başarılı sayılmaz.
Rule exploratory multiple discovery; p/FDR, significance veya causality iddiası yok.

Olaylar finite Unix seconds veya offset ISO/aware datetime. Naif timestamp reddi;
[observation_start,end) dışı satırda durur, otomatik filtre yok. IANA ZoneInfo; yerel
takvim gün/hafta(Pazartesi)/ay sınırları; DST günü24s sayılmaz. Nonexistent boundary
reddi, ambiguous boundary ilk fold deterministik. Gözlem penceresi veri kapsamının
kullanıcı beyanıdır; event yokluğundan tam izleme çıkarılmaz. İlk gözlenen başlangıç
window-local'dır, gerçek yaşam signup'ı olduğu iddia edilmez. Activity start seçilebilir;
start olmayan kişiler açıkça hariç listesinde. Önceki event'ler source lineage'da kalır.

Cohort kişi modu unique active / initial cohort people. Event modu period count /
cohort period0 event count: hacim oranı, kişi retention olasılığı değil ve1üstü olabilir.
24dönem sınırı. Tüm kohort calendar hücresinin sağ sınırı gözlem sonunda değilse
retention=None; gözlenen count ayrıca gösterilir. Observation_start cohort sınırından
sonraysa left_truncated, rate kapalı. Genç kohort tamamlanmış gibi karşılaştırılmaz.

Funnel unique ordered stage labels; kişi modunda ilk start/kişi, event modunda her
stage0 bir attempt ve önceki attempt sonraki startta kesilir. Stage event'i attemptler
arasında yeniden kullanılamaz. Window deadline exclusive; event order gerekir. Sadece
deadline'ı tam gözlenmiş attempt rate paydasında; censored observed sayımları ayrı.

Process case/activity/timestamp, optional integer order/boolean complete. Tie default
reject; açık source order tie'ı unique çözer. Complete trace boyunca sabit; yoksa unknown.
DFG düğümleri event count, kenarları gerçek adjacent event count; partial trace'ler dahil.
Başlangıçlar observed; terminal counts yalnız declared complete. Cycle/repeated activity
korunur; çizim konumu analitik model değil. Bu graph causal DAG değildir.
[PM4Py resmi açıklaması](https://github.com/process-intelligence-solutions/pm4py/blob/release/docs/source/getting_started.rst)
DFG count tanımıyla aynı kapsamdadır; PM4Py bağımlılığı veya runtime doğrulaması iddiası yok.

Ayrı native ActivityTransitionModel/v1 adapter: açık starts/ends/edges against trace.
Start, yasak adjacent transition ve completed end ihlalleri RowId örnekleriyle. İhlal
false; ihlalsiz completed true; ihlalsiz incomplete unknown.32activity/256model edge.
Bu yalnız adjacency-language conformance: Petri net concurrency, token replay veya
alignment fitness değildir. Kullanıcı modeli girmeli; aynı logdan otomatik keşfedip
bağımsız doğrulama diye sunulmaz. Eksik trace terminal event'i uydurulmaz.

Önceki Faz59/58 ve resmî açıklar korunur. [Gerçek kanıt](../evidence/PHASE60.md).
