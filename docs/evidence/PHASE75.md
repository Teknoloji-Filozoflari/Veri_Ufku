# Faz75 — son teknik audit ve bounded uçtan uca benchmark

2026-10-16 başlangıç →2026-10-17 son kapılar (Europe/Istanbul), DEC75-01 / ENV-75; yalnız açık Faz75. Faz **sürüyor / deneysel /
isteğe bağlı**. Bütün zorunlu sürüm kapıları kanıtlanmadığından resmî doğrulandı
veya tamamlandı yazılmaz. [Önceki durum](phase75/prior-project_state.txt),
[kapsam](../RELEASE_SCOPE_0_1.md), [insan/uzman protokolü](../RELEASE_REVIEW_PROTOCOL.md).

<a id="e75-validation"></a>

## Kayıt ve tekrar üretme

`scripts/benchmark75_plan.py`: dokuz alan +guardrails/numeric, explicit node seçimleri.
`scripts/benchmark75.py`: group başına ayrı process, time budget, timeout/kill cleanup,
source veya noneditable wheel. Ağ/indirilen model gerekmez; gerçek optional backend
kurulu değilse fail/unavailable, başarılı test sayılmaz. `benchmark75_evidence.py`
post-call/pre-teardown sentetik fixture/artifact dosya byte hash'lerini, test code
hash'i, referans assertion'ları ve numeric witness property'lerini kaydeder. Max1024
file/32MiB each; ephemeral kaybolmuş dosyanın hash'i uydurulmaz. Bu dosyalar kullanıcı
projesi değil test fixture'ıdır. JSON mathematical input hash'i storage file hash'iyle
karıştırılmaz. Test spec/seed/assumptions ilgili test ve result provenance içindedir.

`scripts/audit_phase75.py`: tek runtime Capability registry +ana requirement matrisi
üzerinden bütün76faz/S-P alt kayıt ve416static capability. Support/operation unknown
ve unsupported eksik; supported/conditional deneysel. Registry adjective/test adı
veya modül PASS'i kararlı bilimsel kabul değildir. Test file, GUI file, source path,
help id ve gerçek current JUnit kayıtları ayrı alanlardır. Method-specific test
bulunmadığında module-associated witness açık etikettedir. Çalışmayan plugin-session
capability snapshot'a otomatik verified eklenmez.

[Learning review manifest](phase75/learning-review.json) ve
[boş bağımsız uzman worksheet](phase75/expert-review-worksheet.csv):414article+10lesson,
content version/hash; reviewer/date/decision boş, hepsi pending-independent-expert.
Mevcut teknik review bilimsel/eğitimci approval değildir. Görsel/hesap/JSON otomatik
kapıları uzman review'unun yerini tutmaz.

## Teknik benchmark ve insan kabulü ayrımı

CPython3.13.15 kilitli `.venv`, CachyOS rolling Linux7.2.9-2-cachyos/glibc2.44 x86_64,
Ryzen7 8845HS /yaklaşık32GB, Qt6.11.2/offscreen/software CPU. Bu makinenin fixture
süresi minimum donanım benchmark'ı veya gerçek novice/expert/AT/physical study değildir.
Exact package/backend ve kaynak hashleri audit/summary/result provenance içindedir.

İlk compute source bütün11grup PASS:319vaka; son numeric tanıklar14'e genişletildi,
aynı10ilk tanık iki kez sayılmaz. Ek9audit gate contract testi. Source ve kurulu wheel
son sonuçları nihai özet dosyasında listelenir; ilk koşular yeni başarı diye yazılmaz.
Referans örnekler: histogram2/2, mean17.5/variance6.25, Rubin16/3, Beta(9,3)mean.75,
Brier.075 ve elle logloss, causal2±.2, KM.8/.6/.3,risk10/8/4, IoU1/3,Dice.5,
1kHz sine integratedPSD.08, ranking2/3/.5, PageRank20/43/20/43/3/43.
Ek deney/CRS/Türkçe local cosine/typed DAG tanıkları gerçek motoru çağırır. Sayısal
actual/reference/atol/rtol/inputhash/assumption JSON user properties olarak saklıdır.

İlk GUI tabular2fail128s: cleaning loop undo/open sonrası project busy guard ret;
chart uzun akışında2GiB resource limit. Ayrı cleaning fixture tek başına PASS48.37s.
GUI4GiB ilk table denemesinde native/process bütçe retleri de görüldü; kaynak/veri
bozulması kanıtı yok, fail-safe sonucu başarı sayılmaz. Test helper doğrudan disabled
button signal emit edebildiği için temizlikte publication/project idle, grafiklerde
source data idle +button enabled beklemesi eklendi; uygulama guard'ı/limitleri
kapatılmadı. Son ayrı denemeler önceki hata kayıtlarını silmez. Root cause bütün eski
longheap sorunları için kapanmış sayılmaz.

GUI weighted/experiment/Bayes actual worker/help/export/save/reopen denemeleri ayrı
kayıtlıdır. Diğer alanlarda nihai results PASS olmadan acceptance yazılmaz. Açık4GiB
functional profile config yalnız sentetik `/tmp/pytest` XDG içinde; default2GiB
başarısızlığına eşdeğer kabul değildir. Kaynak/wheel GUI ve gerçek insan görevleri
ayrı tutulur. GUI assertion/screenshot tek başına bilimsel doğruluk kaynağı değildir.

## Açık sorunlar ve sürüm kararı

P0: Bu bounded koşularda doğrulanmış bilimsel yanlış sonuç veya veri kaybı bulgusu
henüz yok; bütün ürün, kaynaklar ve gerçek veri için garanti verilemez. Başarısız/
timeout GUI koşularının tümü açık kayıtta kalır. Sonuç farklılaşırsa seçili release
kapısı kapalı kalır, sessiz eşik/tolerans gevşetmesi yoktur.

P1: default2GiB uzun/multi-step Qt resource ve async readiness sorunları; gerçek
novice/expert ve bağımsız bilimsel learning review yapılmadı. MinHW/physical/AT ve
clean OS/offlineinstaller kabulü yok. Bunlar production release kapısını engeller.

P2: Pardus/Debian/ayrı Arch/GPU gerçek test yok; optional gerçek DB sunucusu/env yoksa
bu fazda yeniden verified değil. Worker env provisioning/local extras installer,
DP accounting/live project encryption, general remote scheduling ve SDK full native
non-stat adapters eksik kapsam olarak korunur. Kaynak/rapor/bundle hassas veri tespiti
hiçbir secret/PII'yi kaçırmaz garantisi değildir. Unsigned Flatpak integrity hash'i
publisher authenticity/signature değildir; dış release yok.

P3: Ekipler arası büyük veri/performance ve geniş uzmanlık alanı kalite çalışmaları
ayrı; bütün veri bilimi yöntemleri tamamlanmadı. Daha önce ertelenmiş/engelli işler
ana matris ve audit'te açık kalır. Teknik smoke başarıları bunları tamamlanmış yapmaz.

## Son test kapsamı ve referans tablosu

[Makine sonuç özeti](phase75/final-results.json) duplicate testleri aynı kaynak/wheel
kapsamında tekrar saymaz:323source/323wheel compute PASS; ayrıca
[9gate/audit contract](phase75/audit-contracts-final.xml) PASS. Whole repository test
iddiası yoktur. [Sayısal reference CSV](phase75/numeric-references.csv):14actual/reference/
tolerance/assumption/inputhash; [source numeric](phase75/source-numeric-delivery/numeric/fixtures.json),
[wheel numeric](phase75/wheel-numeric-delivery/numeric/fixtures.json).
İlk ek experiment/CRS witness yazımında yanlış dict key/import yolu nedeniyle2test
harness hatası oldu; bilimsel sonuç mismatch değildi, [başarısız log](phase75/numeric-reference-harness-failure.log)
korundu ve doğru API ile son14tanık geçti. İlk xunit2 record_property uyarısı da ayrı;
son runner legacy JUnit ve properties/JSON birlikte kaydeder.

[Core Flatpak Faz75 tekrarı](phase75/core-flatpak-smoke.json) ve
[log](phase75/core-flatpak-smoke.log) gerçek Platform runtime, readonly/no-network,
optional modules absent, GUI/import worker/profile2.5/CPU predict8/reopen/schema4→7
PASS. Small empty legacy fixture; tüm eski model backend migration garantisi değil.
Portal Settings.ReadAll D-Bus warning saklıdır; bu test insan chooser testi değildir.
Faz74 bundle/core-professional hash ve431runtime byte eşleşmesi final-results içindedir;
bu faz runtime değişmediğinden yeni fake release sürümü üretilmedi/yayımlanmadı.

[İlk host entry exit2](phase75/wheel-entry-initial-status.json) inherited user settings
nedeniyle kontrollü default test sayılmaz. Kullanıcı config'i incelenip değiştirilmedi;
[izole XDG default2GiB wheel entry](phase75/wheel-entry-isolated.json) GUI_SMOKE PASS,
CPU435 ve gerçek Qt event loop. Bu entry bütün modüller için benchmark değildir.

[Küçük4GiB source table GUI](phase75/source-table-smoke/summary.json),
[wheel table/workflow/repro GUI](phase75/wheel-gui/summary.json). Küçük table yolunda
source hash sabit, constant fill→histogram→PNG/SVG→save/reopen ve yardım F1/Escape.
Source sampled peak RSS2,167,418,880byte; supervisor sampling kısa zirveleri kaçırabilir,
shared pages double count olabilir.4GiB explicit config, default2GiB kabulünün yerini
almaz. Süreler developer makinesinde eşzamanlı audit jobs ile ölçüldü; kontrollü
throughput/CPU yarış veya minimum hardware karşılaştırması değildir.

[Severity issue listesi](phase75/issues.json) açık/engelli/eksik gate'leri saklar.
Bir calibration GUI önce canTest false verdi, aynı3case ayrı2GiB koşuda geçti;
intermittent issue kapanmadı. NLP/vision/audio combined group240/300/180s timeoutları
başarı sayılmaz; tamamlanmış önceki call witnesses fixtures.json içinde saklı,
bitmeyen test için JUnit PASS uydurulmaz. Tek-case ek denemeler bu uzun scope'un
başarısızlığını silmez. Yeni named-field/usability kapısı gerçek AT/insan görev
çalışması veya bütün test edilmemiş platformları doğrulamaz.

Ek tek-case ses classification GUI4GiB: [1failure](phase75/source-audio-smoke/audio-smoke/tests.xml),
worker busy90s bekleme aşıldı (tüm fixture121s). Audio GUI doğrulanmış sayılmaz;
compute/persistence PASS sonucu GUI için kullanılamaz. NLP/vision first completed
call tanıkları combined timeout klasöründe korunur, bütün media GUI group başarısı
verilmez. P1 E75-AUDIO-GUI açık.
İlk spatial GUI harness parametresi reproject yerine geo_reproject olduğundan
collection ret verdi; plan düzeltilmiş ayrı source koşusu2case PASS78.85s. İlk
collection hatası scientific/CRS failure diye etiketlenmez.

## Nihai alan bazlı durum

Aşağıdaki compute sayıları birbirini dışlar; numeric14 ayrıca ortak referans tanığı,
toplam323'tür. GUI kolonları modül ailesinin tamamlandığı anlamına gelmez.

| Alan | Source/wheel compute | Gerçek GUI kanıtı | Sınır |
|---|---|---|---|
| Tablo cleaning/chart | 13/13 PASS | küçük4GiB source1/wheel1 PASS | uzun9method/seven-chart sequence fail/timeout açık |
| Ağırlıklı istatistik/MI/survey | 12/12 PASS | source weighted1 PASS | typed weight ve WR Taylor varsayımları; bütün survey tasarımları değil |
| Deney/Bayes | 6/6 PASS | experiment/Bayes2 PASS | optional gerçek CPU backend, küçük şablonlar; diagnostic fail görünür |
| Reg/class calibration | 15/15 PASS | source ayrı3PASS | önceki canTest false ve4GiB group timeout açık |
| Spatial/time split | 31/31 PASS | source2PASS | CRS/block/group/time seçilmiş yöntemler; tüm geo backendler değil |
| Causal/survival | 12/12 PASS | source2PASS | varsayımlı ATE/KM ve sınırlı backend; nedensellik kanıtı değil |
| NLP/vision/audio | 15/15 PASS | partial NER/vision call PASS; media group timeout/audio1fail | güncel media GUI bütünlüğü doğrulanmadı |
| Recommendation/graph | 11/11 PASS | source2PASS | seçili popularity/centrality; bütün ranker/community metotları değil |
| Workflow/repro | 18/18 PASS | source2/wheel2 PASS | GUI/CLI+profile bundle, tüm arbitrary code/model rerun değil |
| Leakage/cancel/crash/integrity/optional/persistence guards | 176/176 PASS | gerçek GUI sonuçları yukarıda ayrı | tüm kaynak/backend/adversarial state uzayı değildir |
| Explicit numeric witnesses | 14/14 PASS | hesap tanığı | inputhash/math serialization, gerçek fixture bytes ayrıca |

[Final sonuç JSON](phase75/final-results.json),
[kimlikli acceptance](phase75/acceptance.json),
[son audit](phase75/audit-final.log), [gerçek audit komutu](phase75/audit-command.json).
Static top-level capability sınıfı kararlı0/deneysel412/eksik4;
unknown/unsupported support ve operation hücreleri ayrıca eksik, yalnız4eksik yöntem
varmış gibi yorumlanmaz.76faz/S-P alt kayıtlarının sınıfları ve resmî durumları
[ana capability tablosunda](../PRO_CAPABILITY_MATRIX.md) birlikte görünür.

İlk source GUI run14case11pass3fail;4GiB run13case11pass2fail ve ayrıca timeout;
ayrı2GiB run14**tamamlanmış**case14PASS fakat media group240s timeout olduğu için
run bütünü başarılı değildir. Ek source table1PASS/audio1FAIL, wheel GUI3PASS.
Runlar arasında aynı testler tekrarlandığı için sayılar birbirine toplanmaz.
Timeout grubunun tamamlanmış call kayıtları ayrı partial alanında; yarım kalmış case
veya hiç koşulmamış task başarılı sayılmadı. Kaynak/worker/source identity guard'ları
korunur; GUI failure varlığı nedeniyle bütünleşik release kabulü verilmedi.

[Öğren](phase75/learning.log), [usability](phase75/usability.log),
[artifact](phase75/artifacts.log), [Ruff](phase75/ruff.log),
[format](phase75/format.log), [docs](phase75/docs-final.log),
[14document sözleşmesi](phase75/document-tests.log),
[9source audit gate](phase75/audit-contracts-final.xml),
[9wheel audit gate](phase75/wheel-audit-contracts.xml).
Son belge kapıları terminal exit sonuçlarına bağlıdır; teknik Qt/offscreen evidence
ile gerçek novice/expert/AT/physical/minHW/offlineinstaller kabulleri ayrıdır.

**Karar:** Teknik bounded audit ve doğrulanmış alt kapsam belgeli; seçili sürümün
bütün zorunlu kabul kapıları tamamlanmadı. Faz75 ve candidate resmî olarak doğrulandı
sayılmıyor. Bilimsel yanlış sonuç/veri kaybı bulunmadı ifadesi yalnız geçen323source/
323wheel ve belirtilen başarılı GUI/guard testlerine sınırlıdır. Açık P1/P2/P3,
engelli ve ertelenmiş işler kapatılmadı; dış release/stage/commit/push yapılmadı.
