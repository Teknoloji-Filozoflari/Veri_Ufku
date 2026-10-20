# ADR048 — Faz47 numeric exploration

2026-10-12; DEC47-01 açık kullanıcı talimatı. Yalnız Faz47.

Mevcut UnsupervisedSpec/UnsupervisedRun ve tek Capability registry genişler.
KMeans/DBSCAN/Agglomerative/GMM/OPTICS/sklearn HDBSCAN aynı numeric matrix,
metric, scaling, noise ve iç metrik karşılaştırmasına bağlıdır. Yeni dependency
ve ağ eylemi yok. Optional HDBSCAN kurulu sklearn1.9.1 backendidir; contrib
paketiyle min_samples eşitliği iddiası yok. Ward/KMeans/GMM Euclidean;
Manhattan average/complete/single ve density yollarında. DB/CH Euclidean
centroid geometri gerektirir. Mixed-type/native sparse desteklenmez; kimlik,
kategori/ordinal, null/inf ve hassasiyet kayıplı dönüşüm reddedilir.

Advanced/comparison/stability 3000 kayıt/20feature sınırı. n²*24 üst RAM
önkontrolü; CPU/wall/temp/cancel mevcut disposable worker protokolü.
Örnekleme kendiliğinden yapılmaz. Stabilite açık 0–10 tekrar, %80 subsample
without replacement, scaler her örnekte fit; ortak non-noise ARI ve ayrı noise
agreement, seed/selected RowId ilişkisi kayıtlı. Gerçek k/başarı iddiası yok.
GMM full/tied/diag/spherical ve soft memberships/AIC/BIC; convergence ret.
Dendrogram tam linkage numeric JSON; grafik last30 collapsed-node önizlemesi.

LOF outlier fit_predict/negative_outlier_factor_; novelty yalnız seed ile
ayrılmış heldout score_samples. Eğitim satırlarında score/candidate null;
eksik kaynak veri anlamına gelmez. Scaler yalnız eğitimde fit. OneClassSVM
nu/gamma ve robust covariance contamination/nativeoffset kayıtlı. Tüm score
higher=more unusual, ölçekler yöntemler arası eşit değil. PR/cost varsa ayrı
0/1 etikette, sabit eşikte, in-sample/heldout kapsam etiketiyle; etiketsiz başarı
yok. Yeni Phase47 modellerinde yeni-dosya prediction/model persistence kapalı;
sonuç/üyelik kaydı destekli. Önceki güvenli KMeans/IF/IQR lifecycle korunur.

Worker Qt nesnesi/ACTIVE almaz. Parent immutable source/RowId/scaler/model/
metrics/stability/PR yeniden hesaplar, atomik ProjectStore yayınlar. Saved reopen
aynı doğrulamayı yapar; güvenli declarative JSON/Parquet, kullanıcı kodu yok.
Kaynak verisi değiştirilmez; açık işaretli yeni dataset tüm RowId/SourceRecordId
ve kaynak locator kolonlarını korur; novelty unscored nulls korunur.

Teknik kanıt resmî faz kabulünden ayrıdır. Physical desktop/human/AT/minimum
hardware/clean offline install/remote CI önceki açık kapılardır; çalıştırılmayan
kontrol başarılı sayılmaz. [Kanıt](../evidence/PHASE47.md).
