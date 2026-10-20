# Faz20 — model yaşam döngüsü teknik kabul kaydı

2026-10-09 Europe/Istanbul, ENV-20: Linux x86_64, kilitli CPython3.13.15,
PySide6/Qt6.11.2, offscreen/software ve geçici izole XDG.
[Ortam ve lock hash](phase20/environment.json). Yalnız yarım kalan Faz20
tamamlanır; önceki insan/bağımlılık kabulü açık olduğundan faz sürüyor,
yetenek deneysel. Yeni insan masaüstü, uzak CI veya minimum donanım kabulü yok.

<a id="e20-s001"></a>
## E20-S001 — gerçek masaüstü yolu

Model → Model kartı ve yeni veriye uygulama; kayıtlı koşu veya `.vumodel`
seçimi, yeni paket dosyası, yeni veri sürümü, kolon eşleme, önizleme ve yeni
Parquet çıktı. `ui/lifecycle.py`, `ui/qml/LifecyclePanel.qml`, ayrı bütçeli
`modeling/lifecycle_worker.py`. Yeni dosya mevcut Veri import yolundan gelir.
Proje metadata açılışı model deserialize etmez.

<a id="e20-s002"></a>
## E20-S002 — kart ve yorum sınırları

Amaç, kaynak sürümü/hash, fit RowId/kapsamı, sıralı özellik/ColumnId/tip/birim,
hedef/birim, split üyelikleri, ön işleme tarifi/öğrenilen parametreleri,
aday seçimi, metrik/baseline, seed, exact runtime sürümleri ve sınırlamalar
pakette korunur. UI büyük üyelikleri sayımla sunar. Permutation importance
validation 8–3000 üzerinde üç seeded tekrar; final teste dokunulmaz.
Validation önceden seçimde kullanıldığı için açıklama keşifseldir; nedensellik
ve bağımsız başarı iddiası yok. Büyük validation için gerekçeli unavailable.

<a id="e20-s003"></a>
## E20-S003 — dar güvenli destek matrisi

[ADR-023](../adr/023-model-lifecycle-phase20.md): resmî sklearn/skops/ONNX
destek belgeleri 2026-10-09 yeniden açıldı; özel FoldPreparation converter
gereksinimi nedeniyle dar skops formatı seçildi. Paket yalnız card.json,
pipeline.skops, integrity.json. Sabit incelenmiş tip izin listesi; dış paketten
trusted listesi alınmaz. Exact sürüm/tip/özellik/etiket/preprocessing, hash,
ZIP üye/yol/symlink/duplicate/boyut ve JSON kontrolleri.
Pickle/joblib reddedilir; DBSCAN save/predict desteklemez.
Ek bağımlılıkların gerçek lisansları [envanterde](../third_party/phase20/manifest.json).

<a id="e20-s004"></a>
## E20-S004 — yeni veri ve yayın

ColumnId ardından tam isim; farklı isimde açık eşleme, bire bir özellik bağı,
exact tip/birim, missing/nonfinite/unknown/fazla kolon sayımları. Train
imputasyon/scaler/kategori sözlüğü korunur; yeni veride fit yok. Reject veya
açık drop: drop çıktı satırını silmez, null tahmin/invalid_dropped verir.
Batch 1–4096; en fazla100000 kayıt. RowId ile 1:1 left join ve kaynak sırası,
kolonları, duplicate içerikli farklı satırlar korunur. Filtre/sort görünümü
tahmin kapsamını değiştirmez; ayrı işlem sürümü gerekir.
Olasılık yalnız sağlayan sınıflandırıcıda label sırası/dondurulmuş eşikle;
kalibrasyon veya güven aralığı iddiası yok.

<a id="e20-s005"></a>
## E20-S005 — çevrimdışı yardım

Beş konu: model kartı, özellik önemi, bilinmeyen kategori, yeni veri ve tahmin
belirsizliği. QML/capability bağları, kritik sınırlamalar, Öğren ağacı ve gerçek
LearningController açılışları. Katalog28,136 makale; nihai yardım kapısı aşağıda.

<a id="e20-s006"></a>
## E20-S006 — paket roundtrip ve adversarial kabul

[35 son odaklı test](phase20/targeted-complete-final.txt) geçti: dört regresyon, üç sınıflandırma,
KMeans/IsolationForest/IQR exact predict/proba/score roundtrip; model ve
preprocessing fit çağrılarını yasaklayan spy; hostile pickle/untrusted type,
yanlış sürüm/şema/özellik/tip/etiket/estimator, hash ve ZIP yol/duplicate/symlink
reddi. DBSCAN paketleme engeli. Proje artifact/hash/kart/reopen bağı.
İki gerçek spawn süreç aynı hedef için yarışır; yalnız biri yayımlar.
Symlink/mevcut dosya ezilmez. Paket export doğrulanan sabit byte snapshot'ını
kullanır; dış dosyanın doğrulama sırasında değişmesi test edildi.

<a id="e20-s007"></a>
## E20-S007 — satır ve GUI sınırları

Filtrelenmiş/ters sıralı17 satır, aynı içerikli farklı RowId, ortadaki invalid
kayıt, farklı ve kısmi batch boyutları, tüm satırların invalid olması;
orijinal kolon/sıra/RowId bire bir korunur. Unknown onehot sıfır blok,
eğitim imputasyon/scaler/feature sırası. Gerçek QML/spawn yeni dosya import,
paket kaydet/aç, önizleme/predict, Türkçe/boşluk/# yol, yardım, stale önizleme
reddi ve iptal. Tek feature'ı otomatiğe almak diğer eşlemeleri korur.

Özellik önemi bağımsız doğrusal referans: y=3x+7 için x karıştırma kaybı
3×ortalama|x−karıştırılmış x|; validation RowId sırası, üç tekrarın ortalaması
ve popülasyon standart sapması1e-10 toleransla doğrulandı. İlk referans denemesi
validation üyelerini kaynak sırasına aldığı için başarısızdı; gerçek kayıtlı
RowId sırası ile düzeltilmiş son35 test kanıtı kullanılır.

İlk GUI koşusu önceki veri sürümünü seçtiği için26 geçti/1 başarısızdı; açık
yeni dataset seçimiyle düzeltildi. Dataset seçicisi gerçek selection ile
eşitlendi. İlk ölçümde son kısmi batch ilerlemesi toplamı aşarak ValueError
üretti; gerçek Progress sözleşmesiyle test edildi ve min(done,total) düzeltildi.
Başarısız denemeler başarılı kabul değildir.

## Nihai doğrulama

[Kaynak kayıt](phase20/source-complete.json)/[çıktı](phase20/source-complete.txt),
[noneditable Linux wheel](phase20/wheel-complete.json)/[çıktı](phase20/wheel-complete.txt):
gerçek QML/spawn LinearRegression ve ikili LogisticRegression geliştirme,
model kartı/paket kaydet/aç, yeni6 ve100000 kayıtlı dosya import/eşleme,
batch127 tahmin, kalıcı proje kapat/aç ve kaynak byte koruması geçti.
Sayısal referans3x+7, ikili sınıf/label sırası ve orijinal tüm kolon/RowId
bire bir karşılaştırıldı. Yeni veride fit çağrısı yok.

Kaynak100k preview2.141/2.954s ve prediction4.897/6.915s;
wheel preview2.159/1.439s ve prediction5.983/4.766s.
Kaynak tepe parent+worker RSS1070403584 byte/max tick462.429ms;
wheel1073893376/397.349ms. Geliştirici donanımı/sıcak runtime ve eşzamanlı
test yükü; minimum donanım veya tüm performans bütçelerine kabul verilmez.
İlk okunabilirlik öncesi100k prediction69.846/145.239s ve max tick11.275s
idi; varsayılan ham JSON kaldırılması ve aynı ilerleme mesajının tekrarlı
QML bildirimlerinin kesilmesi sonrası yukarıdaki son ölçümler esas alınır.

[Son build](phase20/build-complete.txt), [kurulum](phase20/install-complete.txt),
[wheel hash](phase20/wheel.sha256),
[172 paket dosyası byte eşleşmesi](phase20/package-integrity.json).
Wheel /tmp cwd'den gerçek package-root assert'iyle çalıştı; bağımlılıklar
kilitli runtime'dan gelir, temiz makine/offline kurulum iddiası değildir.
[Kurulu giriş noktası](phase20/wheel-entry-final.txt) GUI_SMOKE PASS/exit0.
İlk sandbox denemesi exit2 ve boş çıktıyla başarısızdı; başarılı tekrar ayrı
geçici XDG ve gerekli sandbox dışı çalıştırma izniyle yapıldı.

Görseller gerçekten açılıp incelendi:
[1366px model kartı](phase20/source-complete-regression-card-1366.png),
[720px paket önizleme/çıktı](phase20/wheel-complete-classification-preview-720.png).
Okunabilir kart, fit kayıt sayısı, hedef birimi, kritik sınırlama, alan bazlı
önizleme sayımları ve kayıpsız çıktı görünür; fiziksel masaüstü kabulü değildir.

Genel ilk koşu3 başarısız/562 başarılıydı: PHASE20 belgesi henüz yoktu,
yardım sözlüğü eski86 beklentisindeydi;91 ve beş model konusu ayrı kontrol
edildi. Sınıflandırma iptal testi asenkron kayıtlı koşunun açılmasını beklemeden
final eylemini çağırıyordu; gerçek canTest kapısını bekleyecek şekilde düzeltildi.
[İlgili27 regresyon testi](phase20/regression-retry.txt) ve
[52 Faz20/sınıflandırma/yardım testi](phase20/targeted-final.txt) geçti.
[Genel sonraki koşu](phase20/pytest-final.txt)565 test/212.52s geçti.
Model kartına aday parametreleri ve bağımsız önem referansı eklenmesi sonrası
35 odaklı test tekrar geçti. Bütün nihai kaynak koşusu
[566 pytest /200.22s](phase20/pytest-complete.txt) exit0 ile tamamlandı.

[Nihai standart kontrol/exit kaydı](phase20/checks-final.json): locked sync,
sistem+locked check_docs, check_artifacts/check_learning, Ruff check/format,
9 locked unittest ve kaynak giriş noktası smoke exit0.
136 çevrimdışı makale/81 UI bağı; beş yeni yardım konusu geçerli.
Sistem Python3.14.7 discovery55 test/46 import error/exit1:
[başarısız sistem kaydı](phase20/final-system-unittest.txt). Polars/NumPy/PySide6 ve
diğer runtime paketleri sistem Python'unda yok; sistem kurulumu değiştirilmedi.
Bu başarısızlık kilitli CPython3.13.15 test başarısıyla karıştırılmaz.

F20-S001..007 ve11 yöntem kabulü ana matriste ayrı bağlıdır. Önceki F13 insan
kabulü ve bağımlılık kapısı açık; faz sürüyor/deneysel/zorunlu. Faz21 başlamadı.

[223 kaynak/test/lock dosyası SHA256](phase20/source.sha256) nihai uygulama
durumunu kaydeder; kaynak birleşik talimat dosyası değiştirilmedi.
