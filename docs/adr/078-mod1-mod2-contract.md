# ADR078 — Mod 1 / Mod 2 sözleşmesi

2026-11-13 · Faz A karar kaydı · şema geliştirme çerçevesi v1.0 · açık kullanıcı talimatı.

Hazırla aşamasındaki "öğrenilen dönüşümler" iki modda sunulur.

**Mod 1 — Tüm veriye uygula.** Doldurma istatistikleri, standardizasyon, ölçekleme ve
benzeri öğrenilen dönüşümler tüm veriye uygulanır; betimleme ve çıkarım analizleri için
kullanılır. Mod 1 **yeni veri sürümü oluşturur** ve işlem geçmişine yazılır. Bugün çalışıyor:
öğrenilen dönüşümler `learned_scope=dataset` ile tüm veriye uygulanır.

**Mod 2 — Model için planla.** Aynı öğrenilen dönüşümler **yalnız eğitim katında** öğrenilir
ve eğitim dışı satırlara istatistik sızmaz. Mod 2 **yeni veri sürümü yazmaz.** Uygulanan şey
veri sürümü değil, eğitim zamanı işlem hattıdır (tarif/pipeline); bu, Model aşamasının
"veriyi değiştirmez" kuralıyla çelişmez.

Bugünkü durum: Mod 1 gerçek, **Mod 2 yalnız uyarı metni**. `PrepareCatalogPanel` Mod 2
kutusu seçilebilir ama train-only fit yoktur; öğrenilen dönüşümler Model aşamasında
tüketilmez (`modeling/history.py` sızıntı sertifikası `leakage_certified=False`).
Şema envanterinde bu satır `eksik` olarak işaretlenmiştir.

Karar: Mod 1 / Mod 2 **görünür bir üst seçimdir** ve Hazırla ekranının en üstünde durur.
İkisi birbirini dışlar. Mod 2 seçiliyken "Uygula" yeni veri sürümü üretmez; bunun yerine
tarif üretir ve kaydeder. Model modülü kurulu değilse Mod 2 gizlenir; Mod 1 her zaman
kullanılabilir.

Sızıntı uyarısı: tüm veriye uygulanmış bir Mod 1 dönüşümünden sonra Model aşaması açılırsa
kullanıcıya veri sızıntısı uyarısı verilir. Bu uyarı, öğrenilmiş parametrelerin eğitim
dışına taşınmış olma ihtimalini bildirir; ilişki nedensellik değildir.

Öğrenme sınırı: doldurma/kodlama/ölçekleme/özellik seçimi istatistikleri yalnız eğitim
katında fit edilir; test kümesi hiperparametre seçiminde kullanılmaz. Zaman ve grup bilgisine
göre uygun ayrım (independent · group · time · group_time) kullanılır. Öğrenilen dönüşümler
dışarıdan gelen pickle/joblib modeliyle otomatik açılmaz.

Bu ADR sözleşmeyi tanımlar; gerçek Mod 2 uygulaması **Faz E**'nin kapsamındadır ve bu
oturumda başlatılmaz. Faz A yalnızca sözleşmeyi ve eksikliği kayda geçirir.
