# Kanıt — Şema hizalama Faz D → E (2026-11-13)

**Kapsam:** Açık kullanıcı talimatı ile `veri_ufku_sema_gelistirme_promtu.md` v1.0 çerçevesinde
**Faz D** (Model aşaması tahmin yoluna) ve **Faz E** (Mod 2 gerçek plan/pipeline) uygulandı.
Faz A → C önceki oturumda tamamlanmıştı ([SCHEMA_ABC.md](SCHEMA_ABC.md)).

**Kullanıcı kararları (bu oturum):**
- **B-04 → hibrit:** Mod 2 çıktısı saklanan tarif + Model aşamasında açılıp düzenlenebilen form
  (ADR079).
- **B-06 → temel + keşif çekirdek:** yorum ve ileri yollar isteğe bağlı modül; ortamda yoksa yol
  kapalı ve gerekçesi görünür (ADR080).

---

## Faz D — Model aşaması tahmin yoluna taşındı

**Bulgu (ölçüm):** Şema Model aşamasını "Önce değerlendirme planı · test verisi en son açılır"
başlığıyla tanımlar ve on alt başlığı tahmin yolunu tarif eder. Uygulamada Model kataloğu
çıkarım (OLS/WLS/GLM/kuantil/karışık etki) formunu gösteriyordu; **veri varken tahmin
panelleri (regresyon, sınıflandırma, aile seçimi, kümeleme, yorumlama) hiç görünmüyordu**.
Açıklayıcı regresyon ise zaten İstatistik aşamasında (`StatisticalModelsPanel.qml`) mevcuttu.

**Teslim:**
- `ModelCatalogPanel.qml` yeniden yazıldı: şemanın **on alt başlığı birebir** (ad, modül
  etiketi, çekirdek/opsiyonel katman, kayıt durumu).
- `ModelWorkspace.qml` yeniden yazıldı: seçilen alt başlığın yüzeyini merkezde gösterir
  (M-01 hazırlık planı · M-02 devralınanlar · M-03 regresyon · M-04 sınıflandırma · M-05 kümeleme
  · M-06 boyut azaltma · M-07 doğrulama · M-08 yorumlama · M-09 özel tür yolları · M-10 ileri
  yollar).
- `ValidationPanel.qml` → protokol `ValidationProtocol.qml` bileşenine ayrıldı; protokol
  M-01/M-03/M-04/M-07'de tek örnek olarak yaşar.
- `ModelPathsPanel.qml` (yeni) — M-02 "Hazırla'dan devralınanlar": saklanan tarifler, öğrenilen
  adımlar, sızıntı durumu.
- `ui/model_paths.py` (yeni denetleyici) — tarif listesi, alt başlık durumu, opsiyonel modül
  erişimi.
- `Main.qml` — Model aşaması veri olmasa da açılır; eski `modelPath` rotası ve
  `deferredPreparationPanel` kaldırıldı (çift yüzey/sahte yol riski).
- Model kataloğu çıkarım yüzeyinin İstatistik aşamasında olduğunu söyler ve oraya geçiş
  düğmesi sunar (`modelCatalogOpenStatistics`).
- Kararlar: ADR081 (Model = tahmin), ADR080 (alt paket katmanları).

**Testler:** `tests/test_model_catalog_gui.py` (4) · `tests/test_model_workspace_gui.py` (2,
yeniden yazıldı) · `tests/test_model_family_paths.py` (5).

## Faz E — Mod 2 gerçek plan/pipeline

**Bulgu (ölçüm):** `setPrepareScopeMode()` yalnız bir UI notuydu; Mod 2 seçiliyken bile
"Uygula" tüm veriye uyguluyor ve **yeni veri sürümü** üretiyordu. Eğitim katında fit ve tarif
mekanizması (`modeling/baseline.py::FoldPreparation`) hazırdı ama planı tüketen bir Mod 2
tarifi yoktu.

**Teslim:**
- `modeling/plans.py` (yeni) — `Mod2Plan/v1` sözleşmesi: plan yükü, alan doğrulama, plan anahtarı
  (Mod 1/Mod 2 dışlaması), bekleyen planlar.
- `storage/plan_store.py` (yeni) — plan kaydını mevcut atomik proje meta veri işleminde saklar
  (ikinci depo yok).
- `modeling/plan.py` — Mod 2 plan adımları hazırlık planına `learned_scope=training_fold` ile
  eklenir; aynı kolon zaten dolduruluyorsa ikinci adım eklenmez, not düşülür.
- `ui/operations.py` — `planForModel()` yeni veri sürümü **üretmez**; Mod 1/Mod 2 birbirini
  dışlar; `mod2Plans` listesi ve `removePlan()` iptali.
- `PrepareCatalogPanel.qml` — kapsam seçimi gerçek: "Mod 1 — Tüm veriye uygula (yeni veri
  sürümü)" / "Mod 2 — Model için planla (yeni sürüm oluşmaz)"; Model modülü kurulu değilse
  Mod 2 gizlenir.
- `PrepareWorkspace.qml` — Mod 2'de düğme "Model için planla" olur.
- `ModelPathsPanel.qml` — tarif açma (B-04 form yarısı): `recipeOpened` sinyaliyle hazırlık
  formu geri dolar.
- Karar: ADR079.

**Testler:** `tests/test_mod2_plan.py` (işçi testi) — Mod 2 veri sürümü üretmez · Mod 1/Mod 2
dışlaması · eğitim katında fit (gizli test seti ile sızıntı doğrulaması) · plan iptali.

---

## Doğrulama

Ortam: `uv sync --locked --all-extras --group dev` (kilit dosyasıyla birebir), Python 3.13.15,
PySide6, `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software`.

| Kapı | Sonuç |
|---|---|
| `scripts/check_docs.py` | PASS |
| `scripts/check_artifacts.py` | PASS |
| `scripts/check_learning.py` | PASS |
| `scripts/check_usability.py` | PASS |
| `ruff check src tests scripts` | PASS |
| `ruff format --check src tests scripts` | PASS |
| `veri-ufku --smoke-test` | GUI_SMOKE PASS |
| Odaklı pytest (Faz D → E) | **15 passed** — `test_mod2_plan` (4) · `test_model_catalog_gui` (4) · `test_model_workspace_gui` (2) · `test_model_family_paths` (5) |
| Geniş regresyon (310 test) | **80 failed / 230 passed** — HEAD karşılaştırması: **81 failed / 229 passed** |

**Geniş regresyon yorumu.** Koşu `test_advanced_import.py` → `test_composition_gui.py`
dosyalarını (310 test) tek oturumda kapsar. Hata listeleri HEAD ile **birebir aynı**
(küçük fark yalnız üç kararsız GUI testinde: iki test HEAD'de düşüp yeni kodda geçti,
biri tersi yönde döndü; ikisi de izole koşuda flip-flop yapıyor). Yani bu oturumdaki
değişiklikler geniş regresyonda **yeni kırılma üretmedi**.

Kütlü hataların nedeni D/E değil, **oturum uzunluğuna bağlı yapısal bir sınırdır**:
`jobs/admission.py` süreç rezervasyonunu süreç içi global tutar ve `ComputeBudget`
varsayılanı `max_processes=1` / `max_concurrent_cpu_jobs=1` olduğu için **aynı anda
tek işçi süreci** yaşayabilir. Uzun bir oturumda önceki testlerin bıraktığı yaşayan
işçi sonraki tüm işçi başlatmalarını "Toplam süreç/native thread bütçesi dolu" ile
reddeder ve hata kaskadı oluşur. Aynı dosyalar **izole** koşuda geçer (ör. composition +
composition_gui tek başına: 65 passed / 1 failed). Bu, depo için zaten kayıtlı "tam suite
çok sayıda F ile yarıda" durumunun aynısıdır ve bu oturumda giderilmemiştir.

**Çalıştırılmayan kontrol:** tam suite (2424 test) tek oturumda bitirilmedi; bu nedenle
burada PASS iddia edilmez. Zaman aşımına uğramış koşuda 11 alt dosya ~%27'ye kadar
ilerledi; kaskat yukarıda tanımlanan bütçe sınırıyla aynıydı.


**Resmî kabul ayrıdır:** fiziksel masaüstü, AT, insan kabulü, minimum donanım, offline kurulum,
uzak CI ve longheap koşuları bu oturumda çalıştırılmadı.

## Doğrulama sırasında bulunan ve düzeltilen kusurlar

Faz D → E kodu 2026-11-13 oturumunda doğrulanmadan yarım kalmıştı; bu oturumda kapılar
ilk kez gerçekten çalıştırıldı ve üç ayrı kusur ortaya çıktı. Üçü de düzeltildi ve
yeniden doğrulandı.

1. **Ürün hatası — yeni başlatılan iş kendisi tarafından iptal ediliyordu.**
   `OperationsController.start_preview()` işi başlatırken bağlama imzasını
   (`self.signature`) tazelemiyordu; işin sonunda yayınlanan `projects.changed`
   sinyalini `project_changed()` "bağlama değişti" diye okuyup **yeni başlayan işi
   iptal ediyordu**. Bu yüzden hiçbir önizleme sonucu gelmiyor, hata da yazılmıyordu
   (13 Kasım oturumunun "EOF" belirsizliğinin gerçek nedeni bu). Düzeltme: iş
   başlatılırken `self.signature = self.binding`. Aynı bölgede ikinci bir gizli hata
   daha kapatıldı: `self.started` hiç başlatılmadığı için süreç açılırken `poll()`
   `AttributeError` fırlatıyordu; artık `None` ile başlatılıp süre ölçümü
   başlayana kadar korunuyor.
2. **Test izolasyonu — `QCoreApplication` oturumu zehirliyordu.**
   `test_mod2_plan.py` modül kapsamında `QCoreApplication` kuruyordu; bu örnek
   oturum boyunca yaşadığı için **sonraki tüm GUI testleri**
   `create_application()` içinde `setDesktopFileName` hatası alıyordu. Test
   dosyası artık `QGuiApplication` + `QQuickStyle.setStyle("Basic")` kullanıyor —
   `create_application()` ile aynı yol.
3. **Test beklentileri yanlıştı.** Üç assert gerçek sözleşmeyle uyuşmuyordu:
   içe aktarma kaydı bir "işlem" kaydıdır (kayıt listesi değişmemeli, boş olmamalı);
   doğrulama protokolü test oranı %5–40 aralığında olmalı (0.5 reddediliyordu);
   sızıntı kontrolü `float` yerine metin üzerinde yazılmalıydı. Ayrıca "tüm veriye
   uygulanmış dönüşüm" dalı, öğrenilen bir yöntem olan `median` ile **y** kolonunda
   kuruldu (`constant` öğrenilen dönüşüm değildir ve ortalama gibi değerler ikili
   kayan noktada tam temsil edilemediği için kayıpsız dönüşüm sözleşmesini ihlal eder).

Ayrıca `test_text_gui.py` içinde Faz D'de kaldırılan `modelPath` rotasına yapılan
bayat bir gönderme vardı; metin yolu artık Model kataloğunun 9. alt başlığı
(M-09) üzerinden açılıyor ve test buna göre güncellendi.

**Düzeltilmeyen, önceden mevcut kırılma.** `test_missing_sampling_gui.py` içindeki
yardım odağı geri dönüşü beklentisi (`missingHelp*` düğmesine F1 ile açıp Escape ile
odak geri dönüşü) HEAD'de de düşüyor; stash ile HEAD'e dönülerek ayrıca doğrulandı.
Faz D/E ile ilgisi yoktur ve bu oturumda giderilmemiştir; ayrı bir iş olarak
kayda geçmiştir.

