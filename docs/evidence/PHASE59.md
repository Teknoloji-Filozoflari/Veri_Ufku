# Faz59 — offline recommendation teknik kanıt

<a id="e59"></a>
2026-10-15 DEC59-01 açık Faz59 talimatı.12 bounded native C/V/G/H/P kayıt teknik
doğrulandı; faz resmî durumu sürüyor/deneysel/isteğe bağlı. Faz60 başlatılmadı.
[ADR060](../adr/060-recommendation-phase59.md),[12 kabul kaydı](phase59/acceptance.json),
[ENV-59](phase59/environment.json),[korunan önceki durum](phase59/prior-project_state.txt).

Typed user/item/value/Unix-second ColumnId şeması; unique positive-user popularity,
cosine content, observed explicit / confidence implicit ALS; ayrı query/group
pairwise LTR.2000row/32user/128item/16feature/64query,16factor/50epoch/10000LTRpair
sınırı; CPU/ComputeBudget/cancel. Kaynak değişmez; DatasetVersion/RowId/SourceRecordId
ve source snapshot hash korunur. Tek Capability/worker/neural artifact/experiment/
Provenance/ProjectStore parent-ACK atomik yayın yolu; ikinci registry yok.

Temporal ve tie-preserving leave-last-out: her query strict global historical
prefix; bütün heldout satırlar bütün fitlerden hariç. Tarihsel gözlenen katalog,
seen filter, sampled candidate list/hash/seed, future-only/seen relevant paydaları,
macro Precision/Recall/binary NDCG/MAP@K, coverage/diversity/cold start açık.
Yeni LTR query feature'ları açık istekle; seen filter bu şemada kapalı. Query
özellikleri diversity content'i diye kullanılmaz: ayrı content temeli yoksa
hesaplanamaz. Full/sample registry karşılaştırması uyarılır; metric revision
mevcut append-only olay yolunda. Prior test-use defteri korunur; final test
bu panelde kapalı. Yeni run bağımsız başarı iddiası taşımaz.

Model JSON olarak açılır; yeni user/item isteklerinde fit yok. Unknown user
popularity, unknown item zero popularity reason; LTR nonpersonal query score ve
zorunlu candidate feature. Kaynak item kayıt kimlikleri saklı, unknown item için
kaynak satırı uydurulmaz. Yeni yerel JSON export varsayılan salted pseudonym,
raw IDs ayrı açık onay;0600/O_EXCL/O_NOFOLLOW. Ağ veya kullanıcıya gönderim yok.
Kaynak dosya olmadan immutable snapshot ile TCP-connect-deny fixture çalıştı;
bu OS ağ arayüzü veya temiz offline kurulum deneyi değildir.

Gerçek kilitli CPython3.13.15 kontrolleri:

- [177 source core](phase59/source-core-final.xml) ve [177 installed-wheel core](phase59/wheel-core.xml), birer eski HTTPS testi ayrı deselected. Faz59 native29 vaka bu toplamların içinde; [41 son focused recommendation+registry](phase59/core-final.xml) ayrıca aynı kapalı şema/revision kontrolüdür, toplamına eklenmez.
- Sandbox'ın localhost soket açmayı engellediği önceki vision HTTPS testi, izinli localhost ortamında [ayrı1 passed](phase59/legacy-https.xml). Önceki failed aggregate çıktısı [saklı](phase59/source-core.xml); tek178passed koşu diye sunulmaz.
- [Source5 gerçek QML flow](phase59/source-gui/walkthrough.json): popularity/content/ALS/query-LTR train→evaluate→safe open→unknown IDs list→masked export;1952-row live worker cancel. Son LTR seen-filter ve okunur sonuç ekranı düzenlemesinden sonra [source1 final ranker](phase59/source-final-ranker/walkthrough.json) ayrıca passed; tek6-case koşu iddiası yok.
- [Final installed-wheel5 aynı GUI flow](phase59/wheel-gui/walkthrough.json),1000/1366 screenshot'ları; ayrı worker PID, tamamlanan/canceled kalıcı durum, source byte equality ve loglarda private fixture user bulunmaması assertion'ları.
- [332 byte-eşit paket dosyası](phase59/wheel.json), yerel wheel kuruldu; [4 fresh-XDG wheel smoke](phase59/wheel-smoke.json).
- [Yedi son kapı](phase59/gates.json): docs/artifacts/learning/usability/Ruff check+format/document unit.385 article/177 UI help binding; yeni3 çevrimdışı rehber,867 named field;14 document unit. [Frozen hashes](phase59/frozen-head.json).

İlk küçük cancel fixture worker bitişine yetişmedi; live cancel kanıtı sayılmadı.
Daha büyük fixture ayrıntıların hem artifact hem proje özetine yazılarak2MiB
metadata sınırını aşmasını buldu: [ilk GUI4pass/1fail](phase59/source-gui-before-summary-fix/walkthrough.json),
[ilk büyük cancel failure](phase59/gui-cancel.xml). Düzeltme ayrıntıları immutable
artifact'ta, küçük metadata özetini lineage hash/fit/query count ile tek journal'da
tutar; load hem bütünlük hem özet bağını doğrular. Son source/wheel live cancel
geçer; eski başarısız koşular başarılı gibi yeniden adlandırılmaz.

Kapsam: küçük numeric item content, bounded ALS ve native pairwise query ranking.
Ticari gerçek full-catalog availability/serving sistemi, optional üçüncü taraf
ranker runtime veya optimum kullanıcı faydası iddiası yok. Skor click probability
değil; missing event dislike kanıtı değil. Fiziksel masaüstü, insan/AT, minimum
hardware, clean offline installer, remote CI ve önceki bütün resmî açıklar korunur.
Core shutdown GC ResourceWarning görünür; uzun repeated-session2GiB retained-heap
kapısı kapanmadı. Kaynak ağacı korunur; stage/commit/push yapılmadı.
