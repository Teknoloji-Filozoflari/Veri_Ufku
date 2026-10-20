# ADR-034 — Faz33 eksik veri, örnekleme ve ağırlık semantiği

2026-10-11; DEC-33-01 açık kullanıcı talimatı. Yalnız Faz33 uygulanır.

Faz15/16 FoldPreparation, aynı Capability registry, ComputeBudget ve mevcut
AnalysisResult/ProjectStore atomik ACTIVE protokolü genişletilir. İkinci yöntem
veya kayıt sistemi yok. Kaynakta otomatik doldurma, satır silme veya ağırlık
uygulama yok. Yeni metadata varsayılanları legacy tariflerde omit edilir.

KNN ve iterative tek doldurma ortak sayısal matris üzerinde yalnız eğitim
fold'una fit edilir; validation/test transform'dur. KNN ham birimlerin
nan-euclidean uzaklığını kullanır; ölçek ve birimler açıkça incelenir, gizli
standardizasyon yok. Iterative varsayılan BayesianRidge, sabit seed, posterior
kapalıdır. Tamamen eksik eğitim alanı ve bütçe taşması reddedilir. Missing
indicator özgün null/nonfinite politikasından, doldurma öncesi hücrelerden
üretilir; validation'da yeni eksikler de işaretlenir. Eski fill relocation,
KNN/iterative diye sessizce yeniden yorumlanamaz. Permutation importance
Polars gather kullanır: null hücreyi NumPy NaN'a dönüştürmez. Güvenli model
paketi KNN/Iterative ve sabit `_ImputerTriplet` tipini destekler, parametreleri
ve yalnız BayesianRidge koşullu estimatorlarını doğrular; serbest code yok.

MI ayrı inferential selected-sample yoludur; predictive CV sonucu değildir.
En fazla5000 satır/20 alan/20 realizasyon/30 iterasyon. Numeric Gaussian
conditional posterior (IterativeImputer, sample_posterior=True), her realizasyonda
ayrı seed; en az3 gözlenen değer/alan. Ortalama için en az bir yardımcı alan;
OLS tam rank ve pozitif residual df ister. Kategorik, bounded/discrete,
weighted/survey MI ve başka modeller havuzlanmaz. Rubin: Q̄, Ū, B ve
T=Ū+(1+1/m)B; marjinal Barnard–Rubin df/t CI. P/prediction/R² ortalaması yok.
Her realizasyon, gözlenen hücreler, null maskesi, RowId/SourceRecordId,
parametreler ve kovaryanslar kalıcıdır. Parent kimlik, gözlenen hücre,
katsayı/kovaryans ve baseline pooling'i ACTIVE öncesi tekrar doğrular.
Delta senaryoları aynı realizasyonlarda yalnız özgün eksik x hücrelerini,
x'in biriminde kaydırır; yardımcı özellikler kaydırılmaz. MAR çalışma modeli;
MCAR/MAR/MNAR seçimi varsayımdır. Yakınsama ve dağılım incelemesi insandadır.

Eksiklik desenleri null'a dayanır; NaN/inf ayrı kalite uyarısıdır.1024 desen,
20 seçili alan,10000 satır sınırı; sessiz kırpma yok. Göstergeler kimlikli
ayrı çıktı artifact'idir. Basit rastgele satır adedi; stratified her strata
sabit adet (herhangi biri küçükse ret); cluster seçili kümelerin bütün satırları.
Yerine koymadan, explicit seed ve stabil kimlikler; dahil edilme olasılıkları
grup bazında kaydedilir. Temsil veya yanlılık giderme garantisi yok.

Ağırlıklar açık tür seçimiyle registry üzerinden doğrulanır. Tümü sonlu,
eksiksiz, nonnegative ve toplam>0; analytic/survey strictly positive;
frequency integer ve toplam<=1e9. Frekans ortalama varyansı bağımsız tekrar
sayısıyla hesaplanır. Analytic mean/WLS göreli inverse variance ve estimated
residual scale kullanır. sample_weight yalnız doğrusal weighted-loss fit'tir;
SE/CI, survey veya predictive değerlendirme sunmaz. Eski yöntemlere ağırlık
verilirse ret; varsayılan olarak uygulanmaz veya türler birbirine çevrilmez.

Survey ortalaması stratified ultimate-cluster WR Taylor linearization:
U_hj=Σ_i w_i(y_i−μ)/Σw; V=Σ_h n_h/(n_h−1)Σ_j(U_hj−Ū_h)²;
df=Σ_h(n_h−1), t CI. PSU strata içinde nested; her stratada>=2 PSU,
lonely-PSU düzeltmesi yok. FPC, kalibrasyon, replicate weights ve filtreli
domain çıkarımı desteklenmez. Tasarım etkisi observed unweighted iid SRS
s²/n referansına göre açıklayıcı oran olarak adlandırılır; survey::deff'in
kalibre popülasyon karşılığı gibi sunulmaz. Sıfır varyans ayrıca işaretlenir.
Elle fixture V=5,df=2 doğrular; kaynak formül SAS/R birincil dokümanında.
R survey binary bu ortamda yok; R çalıştırılmış gibi raporlanmaz.

Arayüz Karşılaştır → Eksik veri, örnekleme ve ağırlıklar; Model hazırlığı
KNN/iterative/indicator. Önkontrol ve varsayım onayından sonra ayrı Hesapla.
Sonuçlar yerel JSON/members/details Parquet olarak mevcut atomik depoya kaydolur;
yeni mutlak klasöre açık export, tarif+sürüm+hash bağı. Kaynak yazımı yok.
Örnek çıktıda user row_id/source_record_id çakışması açık rename ister.

[Gerçek kontroller ve sınırlar](../evidence/PHASE33.md).
Birincil kaynaklar: [sklearn imputation](https://scikit-learn.org/stable/modules/impute.html),
[statsmodels MICE](https://www.statsmodels.org/stable/imputation.html),
[R survey](https://r-survey.r-forge.r-project.org/survey/html/surveysummary.html),
[SAS SURVEYMEANS](https://support.sas.com/documentation/onlinedoc/stat/121/surveymeans.pdf).
