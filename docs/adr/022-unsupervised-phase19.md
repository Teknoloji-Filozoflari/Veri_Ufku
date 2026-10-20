# ADR-022 — Faz19: etiketsiz keşif ve kayıpsız işaretleme

2026-10-09 Europe/Istanbul. Kabul edilen deneysel teknik kapsam yalnız Faz19;
Faz20 model/yeni dosya dağıtımı ve profesyonel yöntemler başlamaz.

Model ekranındaki amaç seçicisi iki ayrı yol açar: kümeleme KMeans/DBSCAN,
anomali IsolationForest/tek sütun IQR. Hazırlık taraması fit edilmemiş plan olarak
kalır; bu yollar kendi açık ölçüm/ölçek/parametre seçimiyle çalışır. Etiketsiz
fit kapsamı seçilen değişmez DatasetVersion'ın tamamıdır; görünüm filtreleri,
hedef, holdout, precision/recall veya final-test başarısı uydurulmaz.

İlk dört yöntem yalnız 1–20 sonlu, eksiksiz sayısal ölçüm kabul eder. Kimlik,
nominal/ordinal kategori, tarih, metin reddedilir. Kategori kodlarına Öklid
anlamı yüklenmez; one-hot/karma kategorik uzaklık bu başlangıç yolunda yoktur.
Integer/Decimal Float64 kaybı reddedilir. Standardizasyon tam fit kapsamında
öğrenilir; none açık seçimdir. IQR kaynak biriminde çalışır ve ölçekleme yapmaz.
Kaynak/model hazırlama zincirini kendiliğinden değiştirmez.

KMeans: k=1..20, kmeans++, n_init=10, max_iter=300, Lloyd, açık seed.
DBSCAN: Öklid, eps>0, min_samples=2..100 (kendisi dahil), brute; -1 gürültüdür.
KMeans/IsolationForest/IQR tam fit 100.000, DBSCAN 3.000 kayıt; 20 ölçüm ve
DBSCAN en kötü n² komşuluk bellek kapısı. Sessiz fit örnekleme yoktur. Bütçe
ve iptal mevcut Control/spawn gözeticisindedir; worker proje yazmaz.

Silhouette: ölçeklenmiş seçili uzay, gürültü açıkça hariç. En az iki gerçek
küme, her kümede en az üç kayıt (temkinli ürün politikası), en fazla 3.000
noise-dışı kayıt. Bu koşullar yoksa value=null ve gerekçe; 3.000 üstünde
örneklem skoru tüm veri gibi gösterilmez. Profiller kaynak biriminde tam küme
ortalama/min/max/boyutu ve ilk beş gerçek RowId örneğidir. Boyut indirgeme
görseli bu fazda kullanılmaz. İç ayrışma gerçek sınıf veya yeni veri başarısı değildir.

IsolationForest: 100 ağaç, max_samples=min(256,n), açık seed. Skor
`-score_samples`, büyük daha sıra dışı; eşik ya aday oranı (0,0.5] ile
`-offset_`, ya açık skor (0,1]. `score > threshold` işaretler; eşitlik işaretlemez.
Aday oranı etiketli gerçek oran değildir. IQR tek sütun, linear h=(n-1)q,
Q1−çarpan×IQR / Q3+çarpan×IQR; skor kaynak biriminde sınır dışı pozitif
uzaklık, eşik 0. IQR=0'da eşit sınırların dışı adaydır. İki yöntem birbirinin
başarı ölçüsü gibi karşılaştırılmaz; precision/recall=null.

Güvenli sonuç, parametre/seed/backend/tarih/fit kapsamı/snapshot hash ve ayrı
Parquet RowId üyelikleriyle mevcut ACTIVE işleminde kaydedilir. Parametre/veri
revizyonu değişirse eski iş yayımlanmaz. Kayıt açılırken üyelik/kolon/RowId/sayı
ve eşik bağı denetlenir. Pickle/joblib/model çalıştırılabilir formatı yoktur.
Sonuç açılırken kayıtlı form seçenekleri geri yüklenir.

Aktarım açık kullanıcı eylemiyle yeni dataset oluşturur; tüm satırlar, özgün
kolonlar ve RowId/SourceRecordId korunur. Kaynak dataset'in aktif head'i
korunur. Eklenen kolonlar keşif kümesi veya anomali skoru/aday işaretidir;
isim çakışması yeni adla çözülür. `derived_analysis` sonuç ve kaynak sürümüne
bağlıdır; manifest kaynak+ek kolon şemasını ayrı doğrular. Eski sürüm aktarımı,
readonly yazıcı, bozuk üyelik ve disk/yayın hatası reddedilir. Sonraki gerçek
veri işlemleri kendi parent/provenance zincirine geçer.

DBSCAN doğal predict sağlamaz: native_support=false. Diğer yöntemlerin doğal
yeni veri yeteneği açıklanır, fakat available=false: bu fazda güvenli model
saklama/yeni dosya atama yolu henüz sunulmaz (Faz20). Capability predict=false
uygulamanın sunduğu özelliği yansıtır, estimator'ın doğal yeteneğini değil.

Birincil belgeler 2026-10-09 gerçekten web üzerinden okundu:
[KMeans](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html),
[DBSCAN](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.DBSCAN.html),
[IsolationForest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html),
[silhouette](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.silhouette_score.html).
[Orange DBSCAN](https://orangedatamining.com/widget-catalog/unsupervised/DBSCAN/)
ölçek/komşuluk açıklaması ve işaretli veri çıktısı ilkeleri için incelendi;
marka/görünüm kopyalanmadı. Önceki beş referans kaydı UI_REFERENCES'ta korunur.

Gerçek kabul ve sınırlar: [PHASE19](../evidence/PHASE19.md).
