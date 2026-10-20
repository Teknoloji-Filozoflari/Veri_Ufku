# ADR-058 — yerel görüntü ve bounded CPU bilgisayarlı görü

2026-10-14; DEC57-01 açık kullanıcı talimatı. Yalnız Faz57.

Tek SourceAdapter/Capability, ComputeBudget, Provenance ve ProjectStore genişletildi.
Görüntü metadata'sı native DatasetVersion/v7 Parquet; orijinal dosyalar değişmez ZIP
source kopyasında, portable seçimi kapalı olsa da korunur. Model/review/checkpoint
mevcut neural artifact ve experiment projection içinde; ikinci registry yok.
Worker Qt nesnesi/ACTIVE almaz; epoch checkpoint parent ACK+atomik yayınla kalıcılaşır.
DatasetVersion/ColumnId/RowId/SourceRecordId ve source/annotation-parent kimlikleri korunur.

PNG/JPEG/WebP tek frame RGB/L;256 görüntü,4M pixel/16MiB dosya,512MiB kaynak bundle.
Alpha/CMYK/animated/bozuk/limit aşımı durdurulur; sessiz düzeltme veya düşürme yok.
EXIF orientation kopyada uygulanır, annotation oriented original half-open XYXY pixels.
Mask aynı oriented boyutlu tek frame L PNG,0 background/class index label schema.
Klasör adından üretilen class etiketi proposed; insan reviewer/onay yoksa training reddi.
Annotation JSON formu versioned review üretir, mevcut model/metrics korunur fakat yeni
revision fit/metrics invalid olur. Eksik/geçersiz mask review sırasında reddedilir.
Export kimlikleri/mask kaynak referansını ve human/model statüsünü korur; reviewer ve
training group/subject/video identity exportta SHA256 ile pseudonymize edilir.
Bu hash anonimlik garantisi değildir; kullanıcı image/member/source kimliklerini görür.

Decoded exact SHA+dHash64 Hamming≤4 ve RGB mean Euclidean≤8 near heuristic. Group,
subject ve video_source ile union components ortak ValidationSpec group split'e girer;
komponentler train/validation/test arasında bölünmez. Genel semantik duplicate garantisi
verilmez. Aynı dataset review/refit frozen split'i değiştirirse reddedilir. Faz16 test
geçmişi korunur; bu panel final test metric üretmez. Holdout validation seçimi bağımsız
final kalite kanıtı değildir. Training-only flip, sabit RGB/255 ve CNN0.5/0.5 scaling;
image bilinear/mask nearest, normalized crop ve crop dışı bbox kaybı kayıtlıdır.

İlk alt aşama gerçek küçük RGB Conv2d CNN classification, aynı holdout Dummy baseline.
Optional torch2.13.0+cpu exact; CPU gerçek, GPU kapalı. Transfer kapalı CNN safe JSON
VisionWeights/v1'dan conv backbone freeze/yeni head fit eder. Bilinen pretraining kaynak
near/group heldout örtüşmesi reddedilir. Lisans/training dataset/assumptions author beyanı;
ImageNet kalite veya bağımsız doğrulanmış training provenance iddiası yok. Arbitrary .pt,
pickle, remote-code, serbest architecture yüklenmez. Optimizer safe checkpoint var;
Vision panelde pause/full resume özelliği yok, Phase56 desteği korunur.

Detection ayrı bounded RGB pixel LogisticRegression: insan bbox rasterization weak
supervision, foreground4-neighbor components→box, region mean score/eşik. Segmentation
ayrı aynı kapalı pixel classifier, insan L PNG mask supervision. Genel YOLO/U-Net/
production recognition desteklenmiş gösterilmez. Maksimum256×16² pixel eğitim bütçesi.
Detection all-point interpolated AP, score-ranked/class/per-image unique greedy best IoU;
COCO101-point/crowd/area mAP değil. AbsentGT class AP undefined/excluded. Mask pooled
pixel confusion, present foreground macro IoU/Dice; background ayrı, absent-both undefined.
Human original bbox/mask ile resized/cropped model output aynı koordinatmış gibi onaylanmaz.
Saliency üretimi/causal explanation yok; pre-extracted video frame source/sequence/index/time
kimliği var; video decoding/tüm video inference yok.

Yerel model klasörü gerçek; optional indirme yalnız açık UI koşul/lisans onayıyla public
HTTPS/exactSHA/exactbytes. Mevcut TLS-default NLP downloader validator/namespace genişletildi;
3same-origin redirect,16MiB üst sınır, timeout/cancel, hash-checked offline cache.
Auth/query URL desteklenmez; startup/open/prediction ağ isteği yapmaz. Optional package
indirme/install uygulama içinde yok; kullanıcı kurulu CPU backend seçer.

Gerçek kontroller [Faz57 kanıtında](../evidence/PHASE57.md). Qt offscreen/software geliştirici
fixture; fiziksel/human/AT/minHW/cleanofflineinstaller/remoteCI önceki açık kabullerdir.
