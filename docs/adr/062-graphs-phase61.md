# ADR062 — bounded node/edge graph ve yapısal analiz

DEC61-01,2026-10-15: açık Faz61 talimatı. Linux/Python/PySide6/QML; tek
Capability/SourceAdapter/ComputeBudget/Provenance/ProjectStore korunur. GraphRun/v1
mevcut neural artifact/experiment projection içinde, predictive model package yok.
Worker Qt/ACTIVE almaz, parent-ACK ile atomik yayın. Faz62 yetkisi yok.

NetworkX3.7 ortamda kurulu exact sürüm çekirdek bağımlılığa alındı; offline uv lock,
yeni paket indirme yok. CPU256node/2000edge; görünüm max128node/512edge, default64/256.
[NetworkX MultiGraph](https://networkx.org/documentation/stable/reference/classes/multigraph.html),
[shortest paths](https://networkx.org/documentation/stable/reference/algorithms/shortest_paths.html),
[PageRank](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.link_analysis.pagerank_alg.pagerank.html)
resmi kapsam ve weight tanımları kontrol edildi.3.7 greedy modularity generator
merge sınırlarında cancel için kullanılır; sürüm pin gerektirir. GPU gerekmiyor.

Kaynak: mevcut edge tablosu source/target/optional edge_id/weight; node ID'ler typed
string/int. Ayrı node dataset ve ColumnId seçilebilir; bütün endpointler tanımlı
olmalı. İzole node korunur. İki dataset snapshot/hash/RowId/SourceRecordId ve sürüm
bağı artifact/provenance içinde; export kaynağı korur. Birleşik GraphTable/v1:
record_type=node/edge,node_id/source/target/edge_id/weight/attributes. Duplicate declared
node/edge IDs reddedilir. Edge-ID yoksa SourceRecordId kullanılır. Multi-edge/self-loop
reject veya preserve açık. Yön dosya metadata'sıyla aynı olmalı; dönüşüm otomatik yok.

GraphML ve GEXF1.2draft ayrı SourceAdapter, defusedxml0.7.1 DTD/entity/external kapalı;
2MiB sınırı; statik flat tek graph, karma yön/hierarchical/dynamic/port/hyperedge/viz
reddi. Attribute değerleri metin ve JSON object olarak saklı; weight finite numeric.
Node ve edge kimlikleri, explicit/generate edge ID bilgisi, isolated node ve parallel
kimlikler saklı. XML attribute türünün analitik otomatik yorumlanması yok. Yalnız
sınırlı format desteği iddiası; genel her GraphML/GEXF varyantı desteklenmiyor.

Degree incidence count, parallel ayrı, undirected self-loop2; weighted degree seçili
anlamdaki toplam, önem değil. Components undirected/weak/strong ayrı. Shortest Dijkstra
pozitif distance; strength ancak explicit reciprocal1/strength varsayımı. Parallel
minimum distance için geçici simple projection; seçilen edge ID path'ta ve orijinal
graph ayrı. Unreachable=false/None; unseen endpoint reddi. Zero/negative weighted
analiz reddi, sessiz abs/clip yok. Unweighted topoloji seçimi weight'i hesaba katmaz.

PageRank alpha0.85 uniform teleport/dangling, strength/unweighted; distance reddi.
Power iteration200/1e-10 residual, her iteration cancel, convergence fail görünür.
Community greedy modularity resolution1 yalnız undirected strength/unweighted.
Parallel graph için explicit topology (multiplicity/weight kaybı) veya sum_strength
(weight toplama, edge multiplicity kaybı); orijinal graph değişmez. Self-loop etkisi
korunur. Community gerçek sınıf/embedding değildir; PageRank önem/nedensellik kanıtı değil.

Layout circular veya32bounded spring iteration, weight=None: görsel yerleşim mesafesi
analitik distance değil. Typed node filter view-only. Büyük görünüm açık sample/seed
olmadan reddi; görünen/excluded node/edge ve sample etiketi saklı. Analiz tam kaynak
graph üzerinde. Paralel çizgiler örtüşebilir; kimlikli edge listesi kaybı açıklığa
kavuşturur. Export görünüm sample/filter'ını uygulamaz, tam node/edge ve kimlik kökeni.

JSON exact typed IDs; GraphML/GEXF export string orijinal ID'leri korur, integer ID'de
tip kaybı yerine JSON yönlendirmeli reddi. SourceRecordId/RowId/attributes vu_payload
alanında; raw XML birim/formül/object programı çalıştırmaz. Yeni dosya0600/O_EXCL/
O_NOFOLLOW; açık hassas kimlik export onayı GUI'de. Ağ/deploy/otomatik gönderim yok.

Optional link prediction ve network embedding burada mevcut değil. Negative edge,
temporal split/unseen-node/fit scope doğrulanmadan sonuç yok. Gelecek edge'leri graph
feature'ına katmak sızıntıdır; descriptive tüm snapshot analizi predictive test diye
sunulmaz. Önceki final test-use defteri ve resmî açıklar korunur.
[Gerçek kanıtlar](../evidence/PHASE61.md).
