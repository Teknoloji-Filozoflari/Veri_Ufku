# ADR081 — Model aşaması tahmin yoludur; çıkarım İstatistik aşamasındadır

2026-11-13 · Faz D karar kaydı · şema hizalama · çelişki Ç-11'in kapandığı karar.

**Karar.** Şemanın Model aşaması **tahmin** yoludur. Açıklayıcı (çıkarım) regresyon
İstatistik aşamasındaki "İstatistiksel modeller ve tanılama" yüzeyinde kalır.

**Gerekçe.** Şema Model aşamasını "Önce değerlendirme planı · test verisi en son
açılır" başlığıyla tanımlar ve on alt başlığı tahmin yolunu tarif eder
(regresyon · sınıflandırma · kümeleme · boyut azaltma · doğrulama · yorumlama).
Çıkarım (katsayı, p-değeri, VIF, AIC/BIC) ise şemanın **İstatistik** aşamasındaki
"Regresyon (çıkarım)" alt başlığıdır. Uygulamada Model aşaması, veri varken yalnız
çıkarım formunu gösteriyordu; tahmin panelleri (regresyon, sınıflandırma, aile
seçimi, kümeleme, yorumlama) veri varken **görünmez** ve erişilemez durumdaydı.

**Uygulama.**
- `ModelCatalogPanel.qml` şemanın on alt başlığını birebir listeler (ad, modül
  etiketi, çekirdek/opsiyonel katman, kayıt durumu).
- `ModelWorkspace.qml` seçilen alt başlığın yüzeyini merkezde gösterir:
  M-01 hazırlık planı · M-02 devralınanlar (tarifler) · M-03 regresyon ·
  M-04 sınıflandırma · M-05 kümeleme · M-06 boyut azaltma · M-07 doğrulama ve
  karşılaştırma · M-08 yorumlama · M-09 özel veri türü yolları · M-10 ileri yollar.
- Değerlendirme protokolü (hedef/split/fold/seed) `ValidationProtocol.qml` içinde
  ayrıldı ve M-01/M-03/M-04/M-07 yüzeylerinde tek örnek olarak yaşar.
- Model aşaması veri olmasa da açılır (katalog + plan yüzeyi); veri yoksa
  yüzeyler boş durumu gösterir, sahte sonuç üretmez.
- Katalog, çıkarım yüzeyinin İstatistik aşamasında olduğunu açıkça söyler ve
  oraya geçiş düğmesi sunar (`modelCatalogOpenStatistics`).

**Etki.** Model aşamasındaki `modelResponse`/`modelCovariance` gibi çıkarım
alanları kaldırıldı; aynı işlevler `StatisticalModelsPanel.qml` altında
İstatistik aşamasında çalışmaya devam eder. Model aşaması artık veri sürümü
üretmez ve kaynak dosyayı değiştirmez.
