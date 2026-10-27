# Faz67 — yerel batch model izleme

2026-10-16 DEC67-01 / ENV-67. Açık Faz67 talimatı. Resmî sürüyor/deneysel/isteğe bağlı;
Faz68 başlatılmaz. Önceki tüm fiziksel/insan/AT/minHW/longheap/offlineinstaller/remoteCI,
Faz65/66 default2GiB büyük model/tuning ve remote/GPU runtime açıkları korunur.

<a id="e67-scope"></a>
## E67-SCOPE

Mevcut Capability, ComputeBudget, Provenance, experiment journal ve ProjectStore
atomik yayını genişletildi. Ayrı monitoring veritabanı/registry yok. Reference/window/
thresholds/ColumnId recipe, immutable dataset/source/model refs, RowId/SourceRecordId,
code/config/env/hardware capture. Model ekranı → Yerel batch model izleme; komut
paletinde model.monitor.batch/route aynı gerçek formu açar, hesap başlatmaz.
Schema/feature/prediction drift, selected-column quality ve mevcut Faz32 kontrat
tek-tablo ihlal sayıları; FK monitoring'de açık unsupported. PSI reference cuts,
counts/tails/smoothing; numeric Wasserstein, conditional KS p/effect/Bonferroni;
categorical JS/unseen count. Limits/min_n/excluded/assumptions raporlu; veri düzeltilmez.

İki frozen güvenli model aynı batch üzerinde shadow; no labels ise başarı/kalibrasyon
uydurulmaz. Delayed labels unique String business/event key+namespace ile; arrival≤as_of,
future/dedup/type/unseen-class kontrolleri, pending/overdue/delay ve observed-subset n.
Reference labels açık seçildiyse performans/reliability değişimi eşikleri; aksi durumda
unavailable. Reference/current row selection açık, label-order sabit. Brier'ın
multiclass sum normalizasyonu açık; ECE/reliability bin n raporlu. Final-test RowId
bypass kapalı. Yeni labels snapshot yeni immutable run üretir. Input drift→concept
veya performans düştü sonucu otomatik kurulmaz.

Yerel champion route/gerçek önceki modele rollback aynı ExperimentEvent hash zinciri;
source/model artifact ve lineage korunur. Route opt-in scoring gerçekten seçili
model/event reference kullanır. Yeni eğitim mevcut açık config/run yoludur; alarm
fit/deploy/promote/model overwrite yapmaz. CLI batch scoring ayrı allow opt-in;
API ayrıca serve/allow-api/system-keyring bearer ve127.0.0.1 bind gerektirir. API açılışta
başlamaz, ham veri/kod/model upload yok; closed JSON64KiB/auth/schema/time/task budget,
response run IDs, request/secret logging yok. Retry exactly-once değildir.
[Detay ve resmî yöntem kaynakları](../adr/068-model-monitoring-phase67.md).

<a id="e67-validation"></a>
## E67-VALIDATION

[Doğrulama](phase67/verification.json), [kabul](phase67/acceptance.json),
[kapılar](phase67/gates.json), [paket](phase67/wheel.json),
[önceki hafıza](phase67/prior-project_state.txt).
Kaynak ve wheel kontrolleri seçilmiş regresyondur; tam depo veya resmî fiziksel kabul
iddiası yok. Ortam CPython3.13.15 .venv; Linux CPU/offscreen/software. Drift GUI2GiB,
model shadow/rollback GUI fixture açık4GiB; tek default2GiB başarı aggregate yapılmaz.

PSI elle sayım/smoothing, KS/ties/constant/empty, Wasserstein10 ve JS1 fixture;
unknown/delayed/future/duplicate label ve label-order/Brier/logloss/reliability;
gerçek sınıflandırıcıda input/prediction drift olmadan observed performance/calibration
farkı; gerçek safe model train/score/shadow/route/rollback/reopen/lineage; mutable/tamper/
stale journal/CLI opt-in/cancel/önceki commit/source bytes korunması testleri.
Gerçek loopback HTTP testleri geçerli/geçersiz bearer, JSON/size/endpoint/schema ve
aynı gerçek batch worker/yayın yolunu kullanır. HTTP test bearer ephemeral memory,
sistem Secret Service kurulum kabulü değildir; uygulama credential yolu mevcut
keyring-only adapter'dır. Sandbox socket yasağı test başarısı sayılmadı, ayrı izinli
localhost koşusu kaydedildi.

İlk geliştirme koşularındaki NameError test importları, değişen envelope sırasında
KeyError ve final-test içeren referansın safe reddi ayrı korunur; final örnek yeni
bağımsız reference dataset kullanır. Erken başarısız/engellenmiş koşular son başarılı
koşularla birleştirilmez. ZIP duplicate tamper uyarısı kasıtlı mevcut fixture'dır.
Yeni model monitoring fiziksel/insan/AT, uzun retained-heap, keyring provisioning,
remote production API/security audit ve minimum donanım kabulü değildir.

[227source](phase67/source-core.xml)/[227wheel](phase67/wheel-core.xml) selected core,
1er optional-Dask absent skip; metadata contract completion öncesi. Son shared
registry metadata düzeltmesi: geç eklenen kayıtlara eksik inputs/parameters/assumptions/
support/operations/help/artifact alanları doldurulur; var olan typed port korunur,
beyan edilmemiş runtime işlemi unknown kalır, destek uydurulmaz. İlk
[64source pass/1fail](phase67/source-complete.xml)/[64wheel pass/1fail](phase67/wheel-complete.xml)
ve ara workflow metadata eksiği başarısızlıkları korunur. Son
[65source](phase67/source-delivery.xml)/[65wheel](phase67/wheel-delivery.xml) PASS;
19 native monitoring, workspace/registry/repro/workflow dahil, intentional duplicateZIP
uyarısı. Bu sayılar227 ile toplanmaz; tam depo regresyonu değildir.

[İlk source2 GUI](phase67/source-walkthrough/gui.xml)/[wheel2 GUI](phase67/wheel-walkthrough/gui.xml):
drift default2GiB, model shadow/rollback explicit4GiB. Metadata fix sonrası
[ayrı source1](phase67/source-delivery-gui/gui.xml)/[wheel1](phase67/wheel-delivery-gui/gui.xml)
drift tekrar. Son QML sunumunda raw hash JSON yerine drift/n/eşik/label/model özeti
okunabilir olarak gösterilir; config/provenance native artifact'ta kalır. Analitik
hesap değişmedi. Son readable walkthrough ayrı verification kaydındadır.

[Source gerçek HTTP2pass](phase67/source-real-api.xml)/[wheel gerçek HTTP2pass](phase67/wheel-real-api.xml)
izinli loopback testleri; test secret memory dışında saklanmadı.381byte-eşit kurulu
paket, yeni dependency/model/ağ indirmesi yok. Standart kapılar teslim kaydındadır.

Son readable QML paket: [source2pass](phase67/source-readable/gui.xml)/[wheel2pass](phase67/wheel-readable/gui.xml). Her birinde drift default2GiB ve safe model shadow/rollback explicit4GiB; actual komut-paleti/form/spawn/atomic save/cancel/reopen ve model seçim/rollback düğmeleri. [Source ölçüm](phase67/source-readable/measurement.json), [wheel ölçüm](phase67/wheel-readable/measurement.json),1000px/1366px PNG ajan tarafından incelendi. Bunlar insan/AT/fiziksel kabul değildir.381byte-eşit son wheel; hesap Python kodu65şar focused koşusuyla aynı, son fark yalnız QML summary sunumu.

Son görsel denetim sonrası yalnız presentation düzeltmesi: rapor/recipe PlainText
ve WrapAnywhere, rapora bounded-height ScrollView eklendi; uzun ColumnId ve tüm yorum
sınırları yatay kesilmeden kaydırılabilir. Analitik Python değişmedi. Son package
wrapped source/wheel1er drift tekrarının sonucu verification.json içinde ayrı; önceki
readable2şer model/drift GUI kanıtı bu satır kaydırma düzeltmesinden öncedir.

[Son wrapped source1pass/1deselected](phase67/source-wrapped/gui.xml) ve
[wheel1pass/1deselected](phase67/wheel-wrapped/gui.xml) default2GiB. Final görseller
[1000px](phase67/wheel-wrapped/drift-1000.png)/[1366px](phase67/wheel-wrapped/drift-1366.png);
long ColumnId wrap ve rapor scroll görünümü ajan tarafından incelendi.

Son sunum denetiminde TextArea içindeki sol kenar kırpılması görüldü. Sonuç
klavye odaklı ScrollView içinde PlainText/WrapAnywhere UiLabel olarak sunuldu;
recipe shared UiTextArea olarak kaldı. Önceki wrapped görseller silinmedi. Son
label-final GUI/render ve package kaydı verification.json/wheel.json içindedir.
Analitik Python65şar test koşusuyla aynı; GUI sonucu yeniden düzenlemiyor.

Son UiLabel sunumu: [source1pass/1deselected](phase67/source-label-final/gui.xml),
[wheel1pass/1deselected](phase67/wheel-label-final/gui.xml), default2GiB.
[1000px son görünüm](phase67/wheel-label-final/drift-1000.png) ajan tarafından incelendi;
sol kenar kırpılması giderildi. Model shadow/rollback son analitik kanıtı yukarıdaki
readable2şer koşudur; son değişiklik yalnız rapor sunumu.
[Son kapılar](phase67/gates.json): docs/artifacts/learning/usability, Ruff check/format
ve14 belge testi geçti. Kaynak/paket dosya hashleri [teslim kaydında](phase67/delivery.json).
