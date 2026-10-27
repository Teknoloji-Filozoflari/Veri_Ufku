# Faz57 — yerel görüntü ve bounded CPU şablonları

<a id="e57"></a>
DEC57-01,2026-10-14; açık kullanıcı talimatı; Faz58 yetkisi yok.
ENV-57 kilitli CPython3.13.15/Pillow12.3.0/torch2.13.0+cpu/Qt offscreen software.
[ADR058](../adr/058-vision-phase57.md). 12 bounded CPU/yerel teknik kayıt doğrulandı; resmî sürüyor/deneysel/isteğe bağlı.
Çalışmayan kontrol başarılı sayılmaz. Önceki resmî kapılar [korunan durum](phase57/prior-project_state.txt).

Yerel folder/images.json adapter; immutable original bundle + native metadata table;
class/bbox/LPNGmask ve EXIF/kanal/boyut/corruption. Exact/near+subject/video union split;
train-only flip/resize/crop/normalization preview; classification/CNN safe transfer ilk alt aşama.
Ayrı detection ve segmentation bounded RGB-pixel LogisticRegression CPU şablonlarıdır.
Genel YOLO/U-Net/GPU/full-video desteği yok. Detection all-point AP ve mask pooled-pixel
foreground macro IoU/Dice elle referansla kontrol edilir; COCO101-point iddiası yok.

Human review versioned, model önerisi GT değildir; yeni revision metrics/model invalid,
eski run korunur. Bbox/mask önerileri resize/crop koordinatlarında; insan oriented original
annotation'ına sessiz promotion yok. Reviewer/training group kimliği exportta hash'lenir;
source record/image kimliği kullanıcıya açık kalır. Safe local weights ve optional açık
public HTTPS model indirme, lisans/dataset beyanı, exact bytes/hash ve offline cache.

Gerçek kaynak TLS sunucusu: [E57-TLS](phase57/source-tls.xml),1 pass; localhost socket için
sandbox onayı alındı. Hash/size/cancel ve sunucu kapandıktan sonra cache doğrulaması.
[311source core](phase57/source-core.xml),[311wheel core](phase57/wheel-core.xml);
son source revizyonunda [14source](phase57/source-vision-current.xml)/
[14wheel](phase57/wheel-vision-current.xml) focused. İlk önizleme değişikliği sırasında
geçici NameError yakalandı ve başarılı sayılmadı; nihai14 focused sıfır failure/error.
[6source gerçek GUI](phase57/source-gui/walkthrough.json),
[6wheel gerçek GUI](phase57/wheel-gui/walkthrough.json): scan/classification/transfer/
detection/segmentation/review-export-cancel,24PNG ve24safeJSON.
Review eski transform preview'ı temizleme düzeltmesi ayrıca
[1source](phase57/source-review-current/walkthrough.json)/
[1wheel](phase57/wheel-review-current/walkthrough.json),4PNG/4JSON ile doğrulandı.
Son ortak budget_exhausted status schema guard focused testte geçer; GUI timeout fixture
çalıştırılmadı, normal gerçek cancel ayrı doğrulandı. Final test metric üretilmez;
mevcut test-use history korunur. Safe transfer provenance author beyanıdır, gerçek
kataloğun tüm eski training kaynaklarını kapsadığı garantisi yok.

Manifest dosya yolu; kaynak klasör artık bulunmadan gerçek safe model reopen/prediction,
Python TCP fail-fast ile offline yerel yol; OS ağ arayüzü kapatma iddiası yok. Bozulan
Vision artifact hash'i load sırasında reddedildi. İnsan/model etiketi, invalid mask review,
EXIF/crop/mask nearest ve el hesabı IoU1/3/AP0.5/Dice0.5; validation/test etiket zehirleme
aynı train model ağırlıkları. Kaynak bytes değişmez. Son package
[319byte-eşit file](phase57/wheel.json),[fresh4XDG smoke](phase57/smoke.json),
[12C/V/G/H/P kayıt](phase57/acceptance.json),[7kapı+14documentunit](phase57/gates.json).
Fiziksel masaüstü/human/AT/minimum donanım/temiz offline kurulum/remote CI yapılmadı.
4GiB explicit developer GUI ComputeBudget; core default2GiB değişmedi.

[40source GUI/regression](phase57/source-ui.xml)739.05s: önceki neural/NLP/registry/
validation/import/usability yolları korunur. Son 14focused kaynak/wheel, source manifest
ve offline/tamper fixture'ını da içerir. Toplam test sayıları üst üste binen koşulardır;
311+14 yeni benzersiz test toplamı diye toplanmaz. [E57 doğrulama](phase57/verification.json),
[frozen kaynak/kanıt hashleri](phase57/frozen-head.json). Stage/commit/push yapılmadı.
