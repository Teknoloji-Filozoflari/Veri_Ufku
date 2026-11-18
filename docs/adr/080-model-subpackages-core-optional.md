# ADR080 — Model alt paketleri: çekirdek (temel + keşif) ve isteğe bağlı modüller

2026-11-13 · Faz D karar kaydı · şema belirsizliği B-06 · kullanıcı kararı.

**Karar.** Model aşamasının dört alt paketinden **temel** ve **keşif** çekirdek
kurulumda bulunur; **yorum** ve **ileri yollar** isteğe bağlı modüldür.

| Paket | Alt başlıklar | Durum |
|---|---|---|
| Temel | M-01 Hedef ve plan · M-02 Hazırla'dan devralınanlar · M-03 Regresyon · M-04 Sınıflandırma · M-07 Doğrulama ve karşılaştırma | Çekirdek |
| Keşif | M-05 Kümeleme · M-06 Boyut azaltma · M-09 Özel veri türü yolları | Çekirdek (tür yolları tür modülüyle açılır) |
| Yorum | M-08 Yorumlama | İsteğe bağlı modül |
| İleri yollar | M-10 İleri yollar | İsteğe bağlı modül |

**Gerekçe.** Çekirdek yolun tamamı sklearn/numpy ile yerelde çalışır; ek paket
gerektirmez. Yorum yolunda SHAP, ileri yollarda sinir ağı ise opsiyonel bağımlılıktır
(`model.explain.shap` → `shap`, `model.neural.*` → `torch==2.13.0+cpu`). Bu paketler
kurulu değilse yol ** kapalıdır ve gerekçesi yüzeyde görünür**; sahte bir sonuç
gösterilmez, hesap "başarılı" sayılmaz.

**Uygulama.**
- `ModelCatalogPanel.qml` on alt başlığı da modül etiketiyle listeler ve
  `core` / `optional` katmanını gösterir.
- `ui/model_paths.py::ModelPathsController.optionalModules`, opsiyonel modüllerin
  ortamdaki durumunu `domain/capabilities.py::availability` üzerinden bildirir;
  katalog bu bilgiyi düz metin olarak gösterir.
- Aile adaptörlerinde opsiyonel backend'ler (`xgboost`, `lightgbm`, `catboost`)
  `family_contracts.OPTIONAL_FAMILIES` ile ayrılır ve kurulu değilse kapalıdır.

**Kapsam dışı.** Bu karar paket eklemez/çıkarmaz; yalnız hangi paketlerin
çekirdek olduğunu ve opsiyonellerin nasıl bildirileceğini tanımlar.

Bu ADR B-06'yı kapatır.
