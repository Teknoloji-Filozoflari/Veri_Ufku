# ADR-021 — Faz18 kategori tahmini

Tarih: 2026-10-09. Durum: kabul edilmiş teknik karar; yetenek deneysel.

Açık Faz18 isteği, Faz15 hazırlık ve Faz16 split/fold/append-only final test defterini genişletir. Python/PySide6/QML ve immutable kaynak korunur. Baseline (prior/most_frequent/stratified), LogisticRegression (C0.1/1/10, max_iter500), RandomForestClassifier (25/50/100 ağaç, derinlik4/8/12, min_samples_leaf2, n_jobs1) gerçek sklearn estimator'larıdır. Seed ve paket sürümleri kaydedilir. LogisticRegression yakınsamazsa kontrollü hata; başarılı gibi gösterilmez. Forest20.000, diğer adaylar100.000 uygun kayıt; en fazla20 sınıf ve4 milyon yoğun hücre. Sınırsız AutoML, resampling, olasılık kalibrasyonu, model paketi veya yeni veri tahmini eklenmez; Faz19/20 başlamaz.

## Seçim ve dondurulmuş karar

Adaylar yalnız geliştirme CV F1 ortalamasıyla seçilir. Kullanıcının macro/weighted/micro/binary stratejisi CV'ye uygulanır; eşitlikte aday sırası. İkili adaylar0.5 eşiğinde karşılaştırılır. Ayrı train→validation değerlendirmesi, seçilen aday için eşiği değerlendirir. Kullanıcı eşiği0.05..0.95 ya da19 eşikte pozitif sınıf F1 optimizasyonu (eşitlikte0.5'e en yakın, sonra küçük eşik) seçer. Eşik grid'i, validation RowId'leri, pozitif sınıf, hata maliyeti açıklaması ve model ayarları kaydedilir. Maliyet metni F1 amacını parasal kayba dönüştürmez; validation tekrar ayarlanması da aşırı öğrenmeye neden olabilir.

Final testte tek aday, aynı sınıf ve dondurulmuş eşik kullanılır; training kapsamı development'tır. Testte model/eşik araması yapılmaz. Her model choice eğitimden önce; final test reservation hesaplamadan ve sonuç açılmadan önce atomik kaydedilir. İptal/başarısızlık kaydı silinmez. Sonraki sınıf/eşik/model ayarları önceki tüm proje test kullanım kimliklerini taşır; yeniden test keşifsel görünür. Kopya/save-as önceki defteri korur. Proje dışı test görülmesi bilinmez; ilk kullanım dahi mutlak bağımsızlık garantisi değildir. Hiçbir skor sahada güvenli otomatik karar iddiası oluşturmaz.

## Metrik anlamı

Matris satırları gerçek, sütunları tahmin; sınıflar sabit sözlük sırasındadır. Precision/recall/F1 elle sayımlardan hesaplanır, sıfır bölme0 ve per-class tanımsızlık durumuyla kaydedilir. Macro tüm ilan edilen sınıfları, weighted gerçek sınıf desteklerini, micro toplam sayımları kullanır. Tek etiketli micro F1 accuracy'ye eşittir. Binary yalnız açık seçilmiş pozitif sınıf için uygulanır. Hiç tahmin edilmeyen sınıf görünür; çoğunluk başarıları azınlığı saklamaz.

ROC/PR yalnız estimator predict_proba çıktısından ve doğru sınıf eşlemesinden üretilir. ROC-AUC gerçek FPR/TPR alanı; PR-AUC precision/recall trapez alanı; average precision (AP) ayrı basamak ağırlıklı değerdir. Çok sınıf one-vs-rest, ortalamalar kayıtlı stratejidir; micro flatten edilmiş sınıf/kayıt çiftleri üzerinden hesaplanır. Eğri çizimi en fazla1000 nokta, AUC tüm gerçek eşik noktaları üzerindedir. Olasılık desteği olmayan model için sayı/çizgi üretilmez. İlgili bölümde pozitif/negatif yoksa eğri ve AUC tanımsızdır; eksik sınıflar ortalamadan sessiz çıkarılmaz.

Train, CV ve validation tüm hedef sınıflarını içermelidir; yetersiz azınlıkta kontrollü split reddi. Bu fazın final test bölümünde bazı sınıfların bulunmaması kabul edilir ve matris/per-class destek0, tanımsız eğri ile kaydedilir; train'de eksik sınıf kabul edilmez. Faz16 eski baseline yolu bu esnemeyi kullanmaz.

## Saklama, yardım ve kaynak incelemesi

BaselineRun/v1'e additive classification/decision/comparison/decision_validation alanları, ModelChoice/v1'e ayarlar, FinalTestUse/v1'e özet dondurulmuş karar eklenir. Büyük membership/evaluation ayrıntıları hash kontrollü JSON artifact; manifest eğrileri içermez. Rastgele pickle/joblib yok. Kaynak ve full artifact yeniden açıldığında kapsam/matris/metrik/karar bağları kontrol edilir.

Beş çevrimdışı yardım: başlangıç modelleri, pozitif sınıf/hata türleri, precision-recall ve averaging, validation eşiği, olasılık anlamı. Resmî sklearn web erişim denemesi401 token_revoked ile sonuçlandı; sayfaların çevrimiçi incelendiği iddia edilmez. Kurulu sklearn API imzaları ve docstring'leri [API kaydında](../evidence/phase18/api.txt) incelenir. Referanslar: sklearn LogisticRegression, RandomForestClassifier, roc_curve, precision_recall_curve, auc, average_precision_score. Bağımsız küçük elle hesaplar ve gerçek sentetik veriler [kabul kanıtında](../evidence/PHASE18.md).
