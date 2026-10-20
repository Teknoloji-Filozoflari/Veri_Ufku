# Faz61 — bounded yerel ağ ve graf

<a id="e61"></a>
2026-10-15 DEC61-01 açık talimat.10 bounded native C/V/G/H/P teknik kayıt;
resmî sürüyor/deneysel/isteğe bağlı. Optional link prediction ve network embedding
mevcut değil/doğrulanmadı. Faz62 başlatılmadı.
[ADR062](../adr/062-graphs-phase61.md),[10kayıt](phase61/acceptance.json),
[ENV-61](phase61/environment.json),[önceki hafıza](phase61/prior-project_state.txt).

Node/edge tabloları; birleşik GraphTable/v1 veya ayrı node DatasetVersion/ColumnId.
String/integer typed kimlikler, RowId/SourceRecordId, iki source snapshot/hash ve
provenance bağları; isolated/disconnected node korunur. Direction, parallel edge ve
self-loop reject/preserve açık. GraphML ve static flat GEXF1.2draft ayrı SourceAdapter:
defusedxml DTD/entity/external kapalı;2MiB/256node/2000edge. Mixed/dynamic/nested/
port/hyperedge/viz varyantları reddedilir. Attribute metin değerleri/declared types
metadata'da, weight numeric; sessiz kimlik veya graph basitleştirmesi yok.

Degree incidence/weighted sum; directed weak/strong ve undirected connected
components; positive-distance Dijkstra, unreachable kontrollü. Strength yalnız
explicit reciprocal1/strength ile distance olabilir; PageRank distance reddi.
PageRank alpha0.85 uniform teleport/dangling,200iteration/1e-10 residual/cancel;
convergence fail başarılı sayılmaz. Community undirected greedy modularity resolution1;
parallel simple projection topology veya sum_strength açık, multiplicity/weight
kaybı görünür. Orijinal graph değişmez; centrality önem/causal etki, community gerçek
sınıf değildir. Optional embedding/prediction kullanılabilir gibi gösterilmez.

Circular/32step spring; filtre ve seeded sample yalnız view. Max128node/512edge,
default64/256; sample consent yoksa aşım failed. Görünen/toplam/excluded sayılar ve
sample etiketi kayıtta/GUI'de. Analiz tüm kaynak graph üzerinde. Directed oklar,
self-loop, izole node; parallel çizgiler örtüşebilir, kimlikli listede ayrı.
JSON tam graph typed ID/köken; XML original string node/edge IDs ve vu_payload ile
kaynak kayıt bağları. Integer/string type kaybında XML reddi ve JSON yönlendirmesi.
Yeni dosya0600/O_EXCL/O_NOFOLLOW; kimlikli hassas export GUI'de açık onay.

Tek Capability/SourceAdapter/ComputeBudget/Provenance/neural safe artifact/experiment/
ProjectStore parent-ACK atomik yayın. Worker Qt/ACTIVE almaz. Predict/model package/
final test yok, önceki test-use defteri korunur. Compact artifact özeti ve iki source
journal bağı, hash/reopen/corrupt artifact reddi. Source dosyalar byte-eşit.
NetworkX3.7 kurulu transitive paketten exact core dependency'ye yükseltildi; offline
lock, yeni paket indirme yok. [BSD license/hash](phase61/license.json); önceki dağıtım
license audit kapıları değişmedi.

Gerçek kilitli CPython3.13.15 kontrolleri:

- [192source core](phase61/source-core-final.xml),[192installed-wheel core](phase61/wheel-core-delivery.xml); son stale-node-source GUI guard öncesi. [37native](phase61/native-delivery.xml) bu toplamların içinde. Son paket [41graph+learning focused](phase61/wheel-focused-final.xml) ayrıca geçti; sayılar toplanmaz.
- Bilinen5distance path/e1-e2 kimliği, unreachable ve reciprocal1/9; two-cycle+isolate elle PageRank3/43 ve20/43 +NetworkX reference; loop/parallel incidence; triangle+isolate community; GraphML/GEXF export/reopen/attrs/source IDs, brute schema/negative weights/ties; explicit view sample/filter analytik graph'ı değiştirmiyor; PageRank/spring iç döngüde cancel.
- [İlk source6pass/1fail](phase61/source-gui/walkthrough.json),[ayrı cancel+viewfail1pass](phase61/source-final-cancel/walkthrough.json). İlk source ikinci eylem sonucu bekleneni karşılamadı; passed sayılmaz. Proje işinin bitmesini bekleyen helper guard eklendi.
- [Son okunur ekran source3shortest/cancel/separate](phase61/source-delivery-gui/walkthrough.json),[source1multi-edge/loop projection+GraphML export](phase61/source-multigraph/walkthrough.json). [Son stale-node-source guard source1](phase61/source-final-node-guard/walkthrough.json) ve [final-wheel1](phase61/wheel-final-node-guard/walkthrough.json) ayrı geçti; başka projeye ait node sürümü artık açık hata, StopIteration yok.
- [Önceki wheel8actualGUI](phase61/wheel-gui/walkthrough.json) geçti. [Daha sonra okunur ekran wheel7pass/1fail](phase61/wheel-delivery-gui/walkthrough.json):6hesap/reopen/import/export ve ayrı node/edge geçti; cancel sonrası ikinci view-budget testinde uygulama+worker toplam2GiB aşımı güvenli canceled durumuyla bitti. Bu koşu tek8pass sayılmaz. İlk temiz tekrar [worker checkpoint bekleme timeout](phase61/wheel-final-cancel/walkthrough.json) ile failed; ready olmayan düğmeyi fixture doğrudan çağırmıştı. Kaynak/proje hazır guard ile [son temiz-process cancel/view-budget1pass](phase61/wheel-final-cancel-ready/walkthrough.json) doğrulandı; bu1vaka içinde hem kalıcı canceled hem failed view-budget görünürlüğü gerçek kontrol edildi. [Wheel1multi-edge/loop export](phase61/wheel-multigraph/walkthrough.json) ayrı geçti.1000/1366 screenshot ve worker PID kayıtlıdır.
- Ayrı node/edge GUI'nin üç ardışık importu default2GiB'de memory gate'e takıldı: [ilk failure](phase61/source-separate/walkthrough.json),[açık nedenli failure](phase61/source-separate-check/walkthrough.json). [Explicit4GiB source1](phase61/source-separate-4g/walkthrough.json) geçti; bütün sonraki separate fixture'lar aynı geçici4GiB config kullanır. Default2GiB değiştirilmedi; uzun retained-heap/minHW kapısı kapanmadı.
- [344byte-eşit final paket dosyası](phase61/wheel.json),[4fresh-XDG final-wheel smoke](phase61/wheel-smoke.json). [7son kapı](phase61/gates.json),14document unit; Ruff check/format, docs/artifacts/learning/usability.391articles/181UIbindings/913named fields; [frozen hashes](phase61/frozen-head.json).

Sonuç ekranı okunur ölçü/yol/topluluk listesi; raw kimlikler technical görünümde.
Yeni projection/weight varsayımları ve partial görünüm kalıcı sonuçta tutulur. Link
prediction negative edges/temporal split/unseen node ve future-edge izolasyonu
uygulanmadığı için başarı üretilmez. Network embedding eğitimi mevcut değil;
community clustering bu eğitim diye isimlendirilmez.

Fiziksel masaüstü, insan/AT, minimum hardware, clean offline installer, remote CI,
uzun2GiB retained-heap ve önceki tüm resmî açıklar korunur. Stage/commit/push yok;
kullanıcı değişiklikleri ve untracked teslim dosyaları silinmedi.
