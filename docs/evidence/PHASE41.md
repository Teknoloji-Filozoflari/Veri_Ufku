# Faz41 — resampling, robust ölçüler ve açık test ailesi

2026-10-11; ENV-41: kilitli CPython3.13.15, NumPy2.5.3,SciPy1.18.0,
Polars2.0.0,PySide6/Qt6.11.2; Linux offscreen/software. DEC41-01 açık kullanıcı
Faz41 talimatı teknik uygulama yetkisidir; önceki resmî kabul kapıları açık.

<a id="e41"></a>
## Teknik teslim ve sınırlar

41.1 percentile/uygun BCa bootstrap; observation,whole cluster,moving time block.
41.2 iki exchangeable label permutation ve ayrı paired sign-flip.41.3 mean,
median,trimmed mean/raw MAD; açık keep/MAD exclude/winsorize.41.4 seçili
hipotez ailesiyle Holm/Bonferroni/BH.41.5 filtre/outlier/missing/delta/alternatif
ölçü duyarlılığı; baseline farkı,n ve RowId görünür.

Cluster bootstrap bütün cluster satırlarıyla pooled observation estimand;
cluster permutation eşit cluster mean farkı. Grup içinde bağımlı satırları tek
satır örnekleme engellenir; cluster/time missing ölçümü sessiz düşürülmez.
Time unique numeric/temporal order,n≥2L,moving overlapping blocks; son blok
n'ye kesilir,durağanlık/blok uzunluğu açık varsayım. BCa yalnız iid/cluster mean,
delete-one unit jackknife/midrank bias; median/trim/time BCa engellenir.
Missing/nonfinite/sabit bootstrap,degenerate jackknife/bias/acceleration veya
BCa tail<5 resample: CI unavailable. MC CI endpoint bandı simülasyon hatasını
anlatır; veri CI değildir.

Null space≤10000 exhaustive inclusive ties; büyük uzay seed PCG64,MC
(k+1)/(B+1),Clopper–Pearson95% exceedance probability belirsizliği. H0/tail/seed/
tekrar/birim/membership/draw-distribution kaydedilir. Sadece mean eşitliği
heteroskedastic dağılımda otomatik exchangeability değildir. Paired wide x/y,
benzersiz kişi key,after−before−null için symmetric/random-sign onayı ister;
whole group sign uygulanır. Sabit pozitif pair farkının sign nullu geçerlidir;
tüm sıfır merkezli fark için tanımsız test reddedilir. Time permutation yok.

Holm/Bonferroni FWER/arbitrary dependence; BH FDR/independence-PRDS,arbitrary
bağımlılık ret. P-değeri dataset sütunu,biricik testID ve önceden açık aile adı/
kimlikleri; özgün p'nin bilimsel geçerliği kullanıcı varsayımıdır. Seçili eksik
p veya duplicate kimlik ret,aile sessiz küçülmez. Raw/adjusted p,alpha,aile
üyeleri,error-control ve dışarıda bırakılan testIDler exportta korunur.

2000 satır,10000 tekrar,2000000 satır×tekrar; bounded CPU/RAM/disk/cancel.
Kaynak,ColumnId,DatasetVersion,RowId/hash korunur. Safe JSON recipe/result ve
üyelik/draw/null/scenario parquet; mevcut atomik ProjectStore publication.
Kaydedilen unit mapping immutable kaynak satırlarına ve family original p'lere
ayrıca doğrulanır. Kayıt formu geri yükleme yeni config edit olarak sayılmaz.
Eski dataset/view/source/config sonucu save/exportta engellenir. Desktop korunur;
worker Qt/ACTIVE almaz,yeni ağ bağımlılığı yok.

Duyarlılık baseline+en fazla8 planlı senaryo. Filtre/ölçü/outlier/missing mekanizması
ayrı; delta missing observed mean+delta betimsel varsayım,MI/inference değil.
Ret/boş senaryo unavailable kalır. Tüm senaryolar birlikte raporlanır,p-hacking ve
p≠nedensellik öğretilir. [ADR042](../adr/042-resampling-phase41.md).

## Gerçek kontroller

46 hesap referansı geçti: bağımsız exhaustive küçük permutation,whole-cluster
kimlik/draw referansı,seed byte yeniden üretimi,percentile/BCa kapalı jackknife,
paired/group sign-flip,MC +1 p/uncertainty,robust ölçüler,kayıt/aile ve missing/
rank yerine birim/kapsam bütçe kontrollü ret. İlk15 gerçek QML/spawn/save/reopen/
help/export testi geçti /93.09s. Son restore guard için3 aile QML testi ayrıca
geçti /25.52s. İlk kurulu wheel61 hedefli test geçti /132.90s.

Final kaynak80 ilgili test passed/209.24s; aynı80 wheel passed/214.14s.
46 core+15 resampling GUI+19 eski/model/yardım GUI vaka. Son QML metin polish
sonrası kurulu delivery wheel61 passed/139.22s. Kaynak ve wheel14'er gerçek
GUI akışı geçti: yardım/Escape, kayıt/export, proje close/reopen, eski/model
menü geçişi ve stale ret.84 screenshot/112 export artifact;14 sayısal sonuç
birebir eşit. Son257 source/wheel/installation paket dosyası byte eşit;
installed importer/QML smoke PASS.254 çevrimdışı makale/144 UI bağı/499 named field.

Tam1248 vaka regresyon: **1229 passed/19 skipped/0 failure-error /525.24s**.61 Faz41 vaka passed/0skip.
Dört bağımsız dosya shard, collected/JUnit birebir kapsam;
404 source/test/script/lock dosyası koşu boyunca değişmedi.
19 skip haricî isteğe bağlı MariaDB/MySQL/PostgreSQL/S3/Secret Service fixture
eksikliğidir; ayrıntı [regresyon](phase41/regression-summary.json),
[JUnit](phase41/full-regression.xml),[koşu](phase41/full-shards.json).
Son14 belge unittest passed/10.529s. Docs/artifacts/learning/usability,
Ruff check/format ve git diff --check geçti; [komutlar](phase41/checks.json).

İlk80 source/wheel koşusunda eski GUI responsiveness fixture başlangıç frame'i
bitmeden timer/cancel ölçüyordu;8s gerçek CPU işi başlangıçta tüketilebildi.
İlk frame warmup eklenerek gerçek timer20tick/running/cancel assertions korunup
source/wheel80 tekrar geçti. Önceki başarısız sonuçlar
[önceki koşu](phase41/before-window-warmup/final-targeted.xml) içinde korunur.
Family saved-form restore config değişikliği sayılmıyor; blank-family restore
üç ek gerçek GUI vaka ile doğrulandı. Bilinen ürün hatası son kontrollerde yok;
yukarıdaki yöntem/donanım/kabul sınırları geçerlidir.

[15 kabul](phase41/acceptance.json),[kaynak GUI](phase41/source-gui-delivery/walkthrough.json),
[wheel GUI](phase41/wheel-gui-delivery/walkthrough.json),
[numeric parity](phase41/source-wheel-numeric-parity.json),[wheel byte](phase41/wheel.json),
[görsel inceleme](phase41/visual-review.json).

F13 insan;F25 insan/Orca/AT;F24 minHW/cold/physical frame; kullanıcının durdurduğu
F27 dağıtım;F28 giriş;F30 büyük SAS;F31 clean offline cache açık. Physical GUI,
insan/AT/minHW/clean offline install/remote CI koşulmadı. Önceki resmî kapılar
korunur; kullanıcı değişiklikleri silinmedi,stage/commit/push yok. Faz42 başlamadı.
