# ADR-023 — Faz20 model yaşam döngüsü

2026-10-09. Yalnız açık Faz20 talimatı. Python/PySide6/QML ve proje şeması7
korunur; yeni alanlar isteğe bağlıdır, eski koşular fitted model varmış gibi açılmaz.

Değerlendirmede zaten fit edilen seçilmiş validation pipeline saklanır. Final koşuda
aynı dondurulmuş adayın development fit'i saklanır. Paketleme veya yeni veri kullanımı
tekrar fit yapmaz. Model kartı amaç, immutable kaynak sürümü/hash, fit RowId/kapsam,
sıralı özellik/ColumnId/tip/birim, hedef/birim, split, plan/spec/öğrenilen hazırlama,
aday ve parametre/seçim, metrikler/baseline, seed, exact runtime sürümleri ve sınırları içerir.
Arayüz büyük split üyeliklerini sayımlarla sunar; paket gerçek üyelikleri korur.

Permutation importance yalnız validation8–3000 üzerinde3 tekrar/seed ile hesaplanır;
regresyon negative MAE, sınıflandırma estimator'ın doğal predict accuracy'si.
Validation daha önce aday/eşik seçiminde kullanılmıştır: keşifsel açıklama, bağımsız
başarı kanıtı değildir. Final modelin bağımsız açıklama bölümü yoksa hesaplanmaz.
Katsayı/önem nedensellik değildir; korelasyon önem paylaşabilir/gizleyebilir.

## Resmî serileştirme seçenekleri ve uygulama destek matrisi

[scikit-learn persistence](https://scikit-learn.org/stable/model_persistence.html)
pickle/joblib/cloudpickle yüklemenin kod çalıştırma riskini, sürüm uyumunun
kısıtını ve skops/ONNX seçeneklerini açıklar. Pickle tabanlı biçimler reddedildi.
[sklearn-onnx resmî estimator matrisi](https://onnx.ai/sklearn-onnx/supported.html)
çekirdek estimator dönüştürücülerini listeler; uygulamanın Polars FoldPreparation
sınıfına hazır dönüştürücü sağlamaz. Bu fazda ayrıca farklı inference runtime ve
özel converter geliştirilmedi; ONNX seçilmedi.
[skops resmî destek belgesi](https://skops.readthedocs.io/en/stable/persistence.html)
Pipeline, ağaç/native durum ve çoğu sklearn/numpy/scipy tipini destekler; keyfî
Python kodunu saklamaz. İncelenmemiş tipleri otomatik trusted listesine almak
tehlikelidir, sklearn sürümleri arasında davranış garantisi yoktur.
Bu nedenle skops0.16.0 locked ve dar uygulama izin listesi seçildi.

| Estimator | Güvenli paket/yeni veri | Gerçek doğrulama |
|---|---|---|
| DummyRegressor / LinearRegression / Ridge / RandomForestRegressor | skops + fitted FoldPreparation | exact predict roundtrip |
| DummyClassifier / LogisticRegression / RandomForestClassifier | skops + fitted FoldPreparation; label/proba sırası | exact predict/proba roundtrip |
| KMeans | skops + değişmez Measurements/scaler | fitted küme eşdeğerliği |
| IsolationForest | skops + Measurements/scaler; negatif score_samples/eşik | skor ve aday eşdeğerliği |
| Tek kolon IQR | incelenmiş sabit IQRBounds + Measurements | eşik/skor/adayı eşdeğerliği |
| DBSCAN | engelli; doğal predict yok | desteklenmeyen save/GUI reddi |
| Diğer estimator / callback / üçüncü taraf tip | engelli | tip/estimator reddi |

İncelenmiş ek tipler yalnız numpy.dtype, sklearn.tree._tree.Tree ve repodaki
FoldPreparation/PreparationSpec/Measurements/IQRBounds. Tip listesi paket içinden
genişletilmez. Model objesi exact Pipeline/prepare/estimator sınıfı, özellik/label
sırası ve hazırlama durumuyla doğrulanır. Her yükleme ayrı bütçeli spawn süreçte;
proje açma/GUI thread'i modeli deserialize etmez.

`.vumodel` yalnız card.json, pipeline.skops, integrity.json üyelerini içerir.
SHA256 üye ve proje artifact hash'leri; exact Python/sklearn/numpy/scipy/polars/skops/
Veri_Ufku sürümleri; JSON duplicate/NaN, ZIP duplicate/fazla/yol/symlink/boyut ve
iç skops açılmış boyut sınırları kontrol edilir.128MiB toplam,10000 üye sınırı.
Hash bütünlüktür, imza veya kaynak kimliği değildir; yerellik güven gerekçesi değildir.
Çıplak skops/pickle/joblib açma veya dönüştürme eylemi yoktur.

## Yeni dosya

Mevcut import sihirbazıyla yeni dosya immutable DatasetVersion olarak alınır.
Model seçimi ardından yeni dataset seçimi; tam sürüm kapsamı (görünüm filtresi değil).
Özellikler kimlik, ardından tam isimle eşlenir; farklı isimler açık ColumnId seçimi.
Tek kolon iki özelliğe bağlanamaz. Exact tip ve birim kontrolü, eksik/nonfinite,
bilinmeyen kategori, dönüşemeyen RowId ve fazla kolon sayımları önizlenir.
Tür/birim dönüşümü otomatik değildir: kullanıcı açık işlem/metadata sürümü oluşturur.
One-hot unknown sıfır blok, ordinal unknown geçersiz kayıt; imputasyon/statistik/sözlük
train'den korunur. Önizleme hash token'ı model/veri/eşleme/politika/batch bağını korur.

Tahmin yalnız transform/predict; explicit reject/drop politika. Drop satır silmez:
null tahmin + invalid_dropped durumu. RowId bire bir left join ile orijinal sıra/
bütün alanlar korunur; duplicate içerik üzerinden join yapılmaz.1–4096 batch,
100000 kayıt. Tüm kayıtlar geçersiz olduğunda da null sonuç alanları korunur.
Olasılık yalnız gerçekten predict_proba sağlayan estimator'da, label_order ile
anlatılır; binary dondurulmuş pozitif sınıf/eşik kullanılır. Güven aralığı veya
kalibrasyon başarısı uydurulmaz. Çıktı yeni Parquet; package save yeni dosya.
Sibling staging + no-clobber link; kaynak, mevcut dosya ve symlink ezilmez.
Faz21 veya yeniden eğitim/izleme başlatılmadı.

Paket worker her eylemde128MiB sınırında sabit byte snapshot alır; hash bu aynı byte'lardan hesaplanır ve save doğrulanan snapshot'ı yayımlar. Dış dosyanın doğrulamadan sonra değişmesi doğrulanmamış byte exportuna dönüşmez. Son kısmi batch ilerlemesi toplamla sınırlıdır; aynı progress phase için QML bildirim tekrarı kesilir. UI kart/önizleme varsayılan okunabilir sayımları sunar; büyük teknik JSON yalnız açık ayrıntı seçimiyle hazırlanır.
