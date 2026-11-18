# ADR079 — Mod 2 çıktısı: saklanan tarif + düzenlenebilir form (hibrit)

2026-11-13 · Faz E karar kaydı · şema belirsizliği B-04 · kullanıcı kararı.

**Karar.** "Model için planla" (Mod 2) çıktısı **hibrit**tir: kalıcı bir **tarif**
(pipeline planı) olarak saklanır ve Model aşamasında **açılıp düzenlenebilen bir
form** olarak görünür.

**Gerekçe.** Tarif tek kayıt sisteminde kanıt zincirini korur: hangi dönüşümün,
hangi parametreyle, hangi sürümde planlandığı proje durumunda yaşar ve yeniden
açılabilir. Form ise kullanıcıya değiştirilebilir bir yüzey verir: açılan tarif
tekrar kaydedilebilir, eskisi ezilmez. Yalnız tarif seçilseydi parametre değişimi
yeniden planlama gerektirirdi; yalnız form seçilseydi tekrarlanabilirlik ve
provenance kaydı kaybolurdu.

**Uygulama.**
- Mod 2 planı `modeling/plans.py` sözleşmesiyle saklanır; bir **sonuç kaydıdır**
  (`mod2_plan`), ikinci bir proje deposu veya ayrı yetenek kaydı yoktur.
- Hazırlık planı (fit edilmemiş pipeline tarifi) zaten `preparation` sonuç kaydıdır;
  Model aşamasındaki "Hazırla'dan devralınanlar" yüzeyi her iki türü listeler.
- Tarif açıldığında `ui/model_paths.py::ModelPathsController.openRecipe` planı
  hazırlık denetleyicisine yükler ve `recipeOpened` sinyaliyle **formu geri doldurur**
  (B-04'ün form yarısı). Açılan form yeniden kaydedilebilir.
- Mod 2 **hiçbir zaman yeni veri sürümü üretmez.** Uygulanan şey veri sürümü değil,
  eğitim zamanı işlem hattıdır; bu, Model aşamasının "veriyi değiştirmez" kuralıyla
  çelişmez.
- Mod 1 ve Mod 2 aynı dönüşüm için birbirini dışlar: Mod 1 ile tüm veriye uygulanmış
  bir dönüşüm Mod 2 ile planlanamaz; bekleyen bir Mod 2 planı varken aynı dönüşüm
  Mod 1 ile uygulanamaz.

**Öğrenme sınırı.** Tarifin adımları eğitim katında fit edilir; test/doğrulama
satırları fit edilmiş parametrelere girmez. Son test, geliştirme seçimleri
dondurulduktan sonra açılır.

Bu ADR B-04'ü kapatır.
