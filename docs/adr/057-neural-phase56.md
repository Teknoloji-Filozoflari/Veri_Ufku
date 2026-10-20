# ADR-057 — bounded CPU tensor motoru

2026-10-14; DEC56-01 açık kullanıcı talimatı. Yalnız Faz56.

Optional extra `neural`, exact `torch==2.13.0+cpu` resmi CPU index ve uv.lock hash'leri.
Temel kurulum Torch gerektirmez; capability ve panel absent/version mismatch durumunu
kapatır. Runtime ağ/weight/package download yapmaz. CPU float32 zorunlu; GPU/VRAM/
mixed precision gerçek ortam olmadığından uygulanmış veya doğrulanmış sayılmaz.

Kapalı MLP (Linear/ReLU/Linear) regresyon/sınıflandırma; kapalı CNN (Conv2d/ReLU/
AdaptiveAvgPool/Linear) açık NCHW row-major piksel kolonları. CNN şablonu kullanıcı
kaynak/sıra gerekçesi ister; sıradan kolonlardan görüntü yapısı çıkarmaz. Bağımsız görüntü
manifest/transfer-learning/detection gelecek Faz57 yetkisi değildir. 2000rows/1024numeric
features/100epochs/64hidden/128batch sınırları; CPU/RAM/disk/süre ortak ComputeBudget.
Küçük CPU convolutions oneDNN workspace kullanmaz; ortamda kaydedilir.
Tekrarlanan GUI koşularında framework/Qt heap toplam2GiB sınırını aşabilir; developer
akışları açık geçici4GiB ayarıyla doğrulanır, çekirdek default2GiB değiştirilmez.
Bu minimum donanım kabulü veya2GiB her koşulda eğitim garantisi değildir. GPU olgunluğu
ayrı kalır. Sayısal mean/median/none, train-only standardization; ileri categorical/text/
selection/imputation bu adapterde kapalı ve açıklamalı reddedilir.

Mevcut ValidationSpec/split_plan independent/group/time/group_time, horizon purge,
RowId/ColumnId/DatasetVersion/SourceSnapshotId/hash korunur. Model yalnız plan.train;
validation eval/no_grad, early stopping/best epoch seçer; final test dokunulmaz.
Bu motor holdout development tahminidir; CV veya bağımsız final inference uydurulmaz.
Mevcut sklearn Dummy stratejisi aynı train/validation üyeliğiyle gerçek karşılaştırılır.
Class weights train sayımından; horizontal_flip yalnız açık CNN train mini-batch'lerinde.
Train/validation loss ve lr/gradient norm/n eğrileri; gradient_norm_max clip öncesi normdur,
uygulanan clipping sınırı5 olduğundan ham norm5 üzerinde olabilir; Adam veya momentumSGD, StepLR/none.

Tek worker/registry/Provenance/ProjectStore genişletilir. Worker Qt/ACTIVE bilmez.
Her epoch safe JSON checkpoint parent executor tarafından atomik yayımlanır; worker ACK
almadan ilerlemez. Model weights + best weights + optimizer buffers/step + scheduler +
framework/loader RNG + epoch/early stopping + preprocessing + split/config/source/environment
compatibility hash. Pause epoch sınırında; cancel kısmi epoch'u atar, son kalıcı optimizer/RNG
sınırından tekrar başlar. Cumulative elapsed resume ile sıfırlanmaz. Zorla stop eski atomik
checkpoint'i korur, başarılı olarak gösterilmez. Weight-only reload tam resume sayılmaz.

JSON16MiB, bounded primitive tree ve kapalı tensor dtype/shape/data. `torch.load`, pickle,
Python object/remote code/import hook yok. `.pt/.pkl` pretrained object import desteklenmez;
yalnız uygulamanın hash-doğrulanmış kapalı checkpoint/modeli proje içinden açılır. Büyük
veya serbest mimari desteği iddiası yok. Yeni hedef gerektirmeyen immutable dataset üzerinde
explicit prediction; feature order/name/dtype guard, RowId + SourceSnapshot + hash.
Model/optimizer aynı CPU/framework/thread kapsamı için determinism kaydı; aynı seed her
cihazda birebir garanti değildir. Yerel experiment registry mevcut run IDs/defteri korur;
NeuralRun generic comparison legacy/unknown; eşdeğer CV ranking üretilmez.

Backend resmi kaynakları (2026-10-14):
[CPU sürümleri](https://pytorch.org/get-started/previous-versions/),
[optimizer/checkpoint](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html),
[serialization sınırları](https://docs.pytorch.org/docs/stable/notes/serialization.html).
API sözleşmeleri gerçek installed CPU tests ile kontrol edilir; belge tek başına kabul değildir.

Fiziksel masaüstü, insan/AT, minimum hardware, temiz offline installer, remote CI ve tüm
repo aggregate ayrı açık kabul kapılarıdır. [Teknik kanıt](../evidence/PHASE56.md).
