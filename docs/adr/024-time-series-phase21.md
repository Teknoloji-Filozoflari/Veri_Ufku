# ADR-024 — ayrı zaman serisi yolu

2026-10-09, Faz21; kullanıcı bu isteğe bağlı fazı açıkça seçti. Python/PySide6/QML ve Veri_Ufku adı korunur. Şema7'ye yalnız isteğe bağlı result alanları eklenir; kaynak prompt/veri değiştirilmez.

Model → Zaman serisi ve yol haritasındaki Zaman serisi, normal regresyon hazırlık/split yolundan ayrıdır. Date/Datetime, sayısal ölçüm, isteğe bağlı grup; ColumnId ve immutable snapshot hash ile bağlanır. Her grup ayrı tarih sırası/fit/test/özellik geçmişine sahiptir. Yerel iş ayrı spawn process ve mevcut bütçe/iptal/stale denetimiyle yürür; kaydet/aç dosya I/O executor'dadır. UI tam RowId üyeliğini taşımaz; güvenli JSON artifact tam üyelikleri saklar.

## Zaman ve düzen

Saatlik UTC geçen saat; günlük yerel gece yarısı, haftalık pazartesi gece yarısı, aylık ayın ilk günü. Date takvim günüdür ve saatlikte reddedilir; naive Datetime için açık IANA dilimi gerekir. Aware zamanın dilimi korunur veya açık dilime çevrilir. DST ambiguous/nonexistent reddi, nanosaniye hassasiyet kaybı reddi. Null tarih/ölçüm/grup ve nonfinite ölçüm sessiz dışlanmaz.

Duplicate ve seçilmiş sıklığa hizalanmayan/eksik dönem varsayılan hatadır. Yeniden örnekleme varsayılan kapalı; açık toplam/ortalama ister. Bin [başlangıç, sonraki başlangıç), etiket başlangıçtır. Aynı binin tüm RowId'leri aynı bölümdedir; dönem ortasında bölme yok. Toplam miktar, ortalama kayıt başına ölçüm düzeyidir; zaman ağırlıklı ortalama değildir. Boş bin null kalır, sıfır/gelecekten doldurma yok; tahmin kontrollü reddedilir. Bu faz otomatik gap fill yapmaz.

## Geçmişten geleceğe

Her grupta son `test_periods` final olarak saklanır; test ≥ horizon. Geliştirmede expanding rolling-origin 2–5 fold, her validation bir sonraki horizon (1–60) dönemdir. İlk train ≥ max(12,3×seasonal_period,window+1); minimum toplam ayrıca folds×horizon + test_periods içerir. Mevsim dönemi 0 kapalı veya 2–366; bu eşik ürün politikasıdır, mevsimsellik kanıtı değildir. İlk fit en az üç mevsim içerir; resmî estimated initialization koşulları karşılanır.

Gerçek naive son ölçümü; seasonal-naive son mevsimi tekrarlar. Aday level/toplamsal trend/toplamsal trend+mevsim ExponentialSmoothing veya yalnız baseline. Çarpımsal/ARIMA/otomatik arama yok. Her aday gerçek rolling-origin MAE/RMSE ile karşılaştırılır; seçimin tek ölçütü pooled validation MAE, eşitlikte baseline önce gelir. Yakınsamayan ETS invalid ve görünürdür; başarılı sayılmaz. Final aynı snapshot/spec ve kayıtlı geliştirme seçimiyle fit edilir; yeniden model seçmez. Finalde seçilen aday ve gerçek baseline'lar karşılaştırılır.

Trend eğimi ve mevsim faz ortalamaları yalnız geliştirme hedeflerinden betimseldir. Özellik t için shift(1), ardından geçmiş rolling(window); current/future hedef, merkezli pencere, bfill/interpolasyon yok. Grafik en çok son120 geliştirme noktasıdır; metrik bütün ilgili bölümdendir. MAE/RMSE hedef birimi; MAPE sıfırda tanımsız ve sıfıra yakın değerlerde kararsız olduğundan sunulmaz. Tahmin aralığı desteklenmez ve null kaydedilir.

Geliştirme tahmini eğitim kesiminden sonraki horizon saklı dönem içindir. Ayrıca son kaynak tarihinin ötesinde horizon nokta tahmini verilir: aynı geliştirme fit'i kullanılır ve aradaki saklı test dönemleri toplam mesafeye eklenir. Final gerçekleri bu tahmine de girmez. UI bu daha uzak origin'i açıklar; bütün veriyi kullanarak refit/live update bu fazın yolu değildir.

Final açılmadan ayrı append-only kullanım pending kaydı atomik yazılır; completed/canceled/failed/stale sonucu izlenir. Yeni ayar veya koşu geçmiş kullanımı silmez. Projenin normal model test defteri ve zaman serisi defteri birbirinin önceki kullanımını görür. Güvenli JSON tam/özet artifact hash, kaynak fingerprint, RowId ayrılığı ve kronolojik fold bağı yeniden açılışta denetlenir. Proje dışı test geçmişi bilinmez.

## Resmî API değerlendirmesi

2026-10-09 canlı açılan birincil belgeler: [ExponentialSmoothing](https://www.statsmodels.org/stable/generated/statsmodels.tsa.holtwinters.ExponentialSmoothing.html), [fit](https://www.statsmodels.org/stable/generated/statsmodels.tsa.holtwinters.ExponentialSmoothing.fit.html), [forecast validation örneği](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_forecasting.html), [statsmodels0.15.0 Python desteği](https://pypi.org/project/statsmodels/0.15.0/). Kilitli statsmodels0.15.0 CPython3.13 ile çalıştırılır. Bu yolun nokta forecast API'si aralık garantisi sağlamaz; Gaussian artıkla yapay aralık eklenmedi. Yeni runtime lisansları `docs/third_party/phase21/manifest.json` içindedir.

[Kabul kayıtları](../evidence/PHASE21.md). Önceki insan/bağımlılık kabulü açık: faz sürüyor, yetenek deneysel; Faz22 başlamaz.

İç proje geçmişindeki `dataset_learned` veya `ordered_fill` işlemleri bu yolda reddedilir: eski ham/temiz dataset seçimi istenir. Bu sınırlı yol mevcut bütün-veri imputasyonunu fold-safe gibi göstermez ve zinciri otomatik değiştirmez. Proje dışı geçmiş/kararlar yine bilinmez. Kaydedilen tam üyelikler yeniden açılırken gerçek source grup/tarih sırasından türetilen train/test RowId'leriyle ayrıca eşleştirilir; tahmin yeniden fit edilmez.
