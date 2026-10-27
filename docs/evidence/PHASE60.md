# Faz60 — bounded sepet, kohort ve süreç

<a id="e60"></a>
2026-10-15 DEC60-01 açık talimat.11 bounded native C/V/G/H/P teknik kayıt;
resmî durum sürüyor/deneysel/isteğe bağlı. Faz61 başlatılmadı.
[ADR061](../adr/061-patterns-phase60.md),[11 kayıt](phase60/acceptance.json),
[ENV-60](phase60/environment.json),[korunan önceki hafıza](phase60/prior-project_state.txt).

Native Apriori ve koşullu FP-tree; boş sepet dahil transaction paydası, açık
reject/set duplicate davranışı, support/confidence/lift ve candidate/node/rule bütçesi.
5000row/2000entity/64item/32activity, max5itemset/24takvim period. Farklı transaction
ID aynı içerikle ayrı gözlemdir; quantity weighting yapılmaz. Çoklu keşif yanlış
ilişki üretebilir; p/FDR veya causality iddiası yok. Bütçeyi aşan eksik sonuç failed.

IANA takvim cohort/retention: başlangıç ilk gözlenen veya seçili activity; kişi/event
birimi ve paydası ayrı. Tam gözlenmemiş dönem NA, sıfır değil; right-censored ve
left-truncated bayrakları. Funnel kişi ilk attempt/event her stage0 ayrı attempt,
sonraki start önceki attempt'i keser. Tam deadline gözlenmeyenler rate paydasında yok;
gözlenen censored sayımlar ayrıca. Gözlem kapsamı kullanıcı beyanıdır, event yokluğundan
izlemenin tam olduğu çıkarılmaz. First-observed gerçek yaşam başlangıcı sayılmaz.

Gerçek directly-follows edge/node sayımları ve Canvas + metin çizimi; loop/partial
trace korunur, causal DAG değil. Tie default reject, explicit unique integer order
alternatifi. Complete flag yoksa incomplete/unknown. Ayrı native
ActivityTransitionModel/v1 conformance: açık start/geçiş/end denetimi, RowId ihlal
örnekleri; incomplete fitting=true olamaz. Petri concurrency/token replay/alignment
ve PM4Py runtime iddiası yok. Kendi logundan model uydurup bağımsız doğrulama sayılmaz.

Tek Capability/ComputeBudget/Provenance/worker/neural artifact/experiment/ProjectStore
parent-ACK atomik yayın yolu. Source DatasetVersion/ColumnId/RowId/SourceRecordId,
prior test-use defteri ve source hash korunur. Predictive fit veya final test yok.
Worker Qt/ACTIVE almaz. Ayrıntılar safe JSON artifact'ta; compact metadata/QML özeti
kaynak satırlarını çoğaltmaz. Model package üretilmez. Reopen hash/summary bağını denetler;
source dosya byte eşitliği source/wheel GUI assertion'ıdır. Ağ veya yeni dependency yok.

Gerçek kilitli CPython3.13.15 kontrolleri:

- [155source](phase60/source-core-delivery.xml),[155installed-wheel core](phase60/wheel-core-final.xml); hesapları değiştirmeyen son yerel status-caption düzenlemesi öncesi. [27focused native](phase60/patterns-final.xml) bu toplamların içindedir, ayrıca eklenmez. Elle5basket/count/support/confidence/lift, iki backend–brute-force8rastgele fixture, küçük cohort/funnel/DFG/conformance, DST23saat takvim günü, tie/duplicate/bütçe/bozuk hash, safe reopen ve iki backend iç döngüde iptal.
- [Kaynak ilk6 hesap +1 geç kalmış cancel failure](phase60/source-gui/walkthrough.json); hesap ve reopen yolları geçti, cancel sayılmaz. [Checkpoint beklerken canlı worker cancel1pass](phase60/source-cancel-checkpoint/walkthrough.json) ayrı. Bu hesap ortasında GUI iptal kanıtı değildir; algoritma içi iptal iki native testte gerçekten kontrol edilir.
- [Son source3process/conformance/budget](phase60/source-final-review/walkthrough.json),[son caption/compact summary source3process/cancel/budget](phase60/source-delivery-gui/walkthrough.json) ayrı başarılı koşular. Tek birleşik source8passed iddiası yok.
- [Final delivery wheel8 actualGUI](phase60/wheel-delivery-gui/walkthrough.json):6 gerçek compute→save→reopen/help/source immutability, canlı worker checkpoint cancel ve visible budget-failed. Ayrı worker PID;1000/1366 gerçek screenshot. Incomplete trace ekranda unknown, undefined değil. Süreç grafiği data.edges'ten gerçek sayımlarla çizilir.
- [338byte-eşit delivery paket dosyası](phase60/wheel.json),[4fresh-XDG final-wheel smoke](phase60/wheel-smoke.json). Native stdlib/Polars; paket/model indirme yok, yerel wheel kuruldu.
- [7son kapı](phase60/gates.json),14document unit; Ruff check/format, docs/artifacts/learning/usability.388articles/179UI help binding/890named fields. [Frozen hashes](phase60/frozen-head.json).

İlk GUI7failure öğrenme kimliğindeki underscore'u buldu; dış registry/help fp-growth
alias'ı düzeldi, internal task fp_growth korunur: [ilk kayıt](phase60/source-gui-initial-help-id/walkthrough.json).
Sonraki cancel fixture tıklama öncesi rule bütçesine ulaştı; [başarısız eski cancel](phase60/source-final-cancel/walkthrough.json)
iptal kanıtı sayılmaz. Failed bütçe durumu artık açık status/error metniyle görünür.
QML'de5000lineage nesnesi yerine row count kullanılır, tam köken artifact'ta korunur.
QA helper QObject tree ile visual Repeater delegate'lerini bulamadı:
[source2fail/1pass](phase60/source-final-events/walkthrough.json),
[eski wheel6pass/2fail](phase60/wheel-final-gui/walkthrough.json).
Visual childItems traversal ve event-loop beklemesi sonrası son source review3 ve
final wheel8 geçer; eski başarısız koşular başarılı gibi yeniden adlandırılmaz.

Sınırlar: küçük bounded native keşif; significance/FDR, gerçek nedensellik, genel
Petri model conformance veya kullanıcı gözleminin tamlığı garanti edilmez. Physical
masaüstü, insan/AT, minHW, clean offline installer, remote CI ve önceki tüm resmî
açıklar korunur. Uzun repeated-session2GiB retained-heap kapısı bu testlerle kapanmaz.
Kullanıcı ağacı korunur; stage/commit/push yapılmadı.
