# ADR070 — Öğren yolları ve ayrı sentetik laboratuvar

2026-10-16 DEC69-01. Açık kullanıcı Faz69 talimatı; Faz70 yetkisi değil.
Mevcut Öğren merkezi, Catalog ve Capability genişletilir. Ayrı ders aracı registry'si,
model deposu veya bağımsız analitik kayıt sistemi oluşturulmaz.

## İçerik ve kapsam

LessonCatalog/v1 data-only JSON:10ders/8yol (veri, temizleme, görselleştirme,
istatistik, ML, belirsizlik, zaman serisi, uzman). Her ders amaç/veri/problem/
varsayım/adım/beklenen/yanlış yorum/kendi verine uygulama, günlük örnek, ileri
denklem, article id/version ve teknik review içerir. Prerequisite DAG eksik node/
cycle reddeder; GUI'de clickable öneri oklarıdır, erişim kilidi veya zorunlu sınav değil.
Her dersin bounded slider şeması ve seed vardır. İçerik executable program değildir.

409makale/content85; lesson catalog content1. Mevcut arama/sözlük/yer imi korunur;
ders araması aynı Türkçe-normalized query kullanır. Makale yer imi dersle article_id
üzerinden ilişkilidir. Otomatik coverage403capability'nin tamamını geçerli yol ve
makale bağlantısıyla denetler.10interactive lesson ayrı; diğer393makale bağlıdır,
her modülün ayrı uygulama laboratuvarı varmış gibi sunulmaz. Yeni capability eklendiğinde
coverage manifest güncellenmezse kapı başarısız olur. Review article version değişimine
duyarlıdır. Teknik reference fixtures/link review bağımsız bilimci/eğitimci veya
insan usability incelemesi değildir; bunlar not_recorded/açık kalır.

Optional self-check iki seçenek ve her seçime açıklama verir. Puan, sertifika veya
uzman rozeti yok; yanlış yanıt ders/araç açmayı engellemez. Tamamlandı işareti kullanıcı
beyanıdır, test sonucu değil. Mevcut learning-marks.json şema1 okuması korunur;
yazım şema2 (read/bookmarks+lesson_id:version). Eski kayıtlar in-memory göçer; yeni
sürüm tamamlandı sayılmaz. QSaveFile/direct-write fallback kapalı/0600; varsayılan
kapalı. Opt-out bütün işaretleri aynı atomik yazımda temizler. Okuma otomatik kayıt
veya ilerleme üretmez. Bozuk dosya korunur; öğrenmek/araçlar çalışmaya devam eder.

## Ayrı workspace ve iş yaşam döngüsü

Öğren merkezinden veya learn.lab.* komut paletinden açık eylem yeni geçici ProjectStore
oluşturur. LearningLabController ana ProjectController/store/taslak referansı almaz;
kendi ProjectController'ı aynı mevcut storage/transaction protokolünü kullanır.
Kendi recents/config'i geçici köktedir. Açılışta proje/hazır hesap oluşturulmaz.
Slider değişikliği hesap başlatmaz; Hesapla explicit spawn worker çalıştırır.
Önceki ayarın sonucu açık stale etiketi taşır. Pencere nonmodal; kapatmak araçları
ve asıl projeyi kilitlemez, aktif lab işi iptal edilir. Geçici hesaplar uygulama
oturumu boyunca yeniden açılır; normal shutdown store kapanır ve workspace temizlenir.
Crash sonrası cache kalıntısı olabilir; kalıcı kullanıcı projesi gibi sunulmaz.

Worker immutable request, content hash ve ComputeBudget alır; Qt/ProjectStore/ACTIVE
yazmaz. Ortak CPU/process/native-thread/RAM/time/disk admission/supervision ve mevcut
supervised MonitoringController yaşam döngüsü kullanılır. CPU zorunlu, GPU/remote yok.
Synthetic fixture≤10000row; safe JSON≤2MiB; grafik aynı hesap x/y dizilerinden çizilir.
DatasetVersion/gerçek kaynak RowId uydurulmaz. input_records native artifact'ta
synthetic:fixture-hash:index kimliklidir, user RowId değildir. Kaynak/dataset listesi
boş; Provenance bu sentetik kapsamı açık kaydeder. Seed/spec/content/article/review,
code/config/env/hardware ve fixture hash/kimlik/split/metric/curve aynı run'a bağlıdır.
Safe artifact unique URI ile tek ProjectStore transaction'ında yayınlanır. Önceki
başarılı sonuç cancel/failure ile değişmez. Kalıcı kaynak veya model değiştirilmez.

## Hesaplar

- mean/median NumPy;10,20,90→40/20 referansı. Temizleme explicit constant-fill preview,
  orijinal null kayıtları korunur. Histogram gerçek bin count/edges, counts normalize.
- sampling:0..99sonlu popülasyonda simple random without replacement; seed ve seçili
  kimlikler kayıtlı, survey inference iddiası yok.
- CI:100iid N(0,1) tekrar, her örnekte n5..100; Student t interval x̄±t s/√n,
  ddof1. Coverage gerçekten sayılır; observed coverage tam nominal olmak zorunda değil.
  Tek CI posterior olasılık veya prediction interval diye sunulmaz.
- overfitting: gerçek DecisionTreeRegressor,40train/160validation, kontrollü max_depth.
  leakage: dürüst OLS ile kasıtlı GEÇERSİZ outcome-proxy OLS karşılaştırması; proxy
  validation hedefini görür, düşük hata performans sonucu sayılmaz.
- calibration: gerçek LogisticRegression base fit200train; distortion sonrası ayrı
  200calibration sigmoid fit;200evaluation üzerinde label_order0/1 Brier/logloss ve
  fixed10bin reliability/n. Küçük bin/variance ve Brier≠yalnız calibration sınırı açık.
- time series:72regular sentetik nokta, history60/origin60/horizon12 seasonal naive;
  forecast yalnız son gözlenmiş döngüyü kullanır.
- confounding: bilinen synthetic y=2t+γz+ε; treatment~Bernoulli(σ(γz));400record,
  gerçek naive ve z-adjusted OLS. Sadece bu bilinen DGP'de etki2 referans; gerçek
  gözlemsel veride adjustment nedensellik kanıtı değildir.

Sliderlarla aynı evaluation/validation tekrar görülür; bütün lab sonuçları keşifseldir,
final test değildir. Kaynak dosyası/model indirmesi/internet/servis gerekmez. Fiziksel
OS ağ arayüzü kapalı kabulü değil, fail-fast network guard ve local solver kanıtıdır.

## GUI hataları ve kontrol

İlk QML seed alanında Accessible.name yerine olmayan property kullanımı düzeltildi.
Yeni subclass özelliklerinde inherited notify ile Qt meta-property cache çökmesi
GDB'de görüldü; yeni özellikler kendi labChanged signal'ına bağlanıp base changed'e
köprülendi. Tüm yeni QMetaProperty notify metadata native kontrol ve gerçek QML load
ile doğrulanır. Palette ayrı ApplicationWindow'a da uygulanır. Bu başarısız koşular
[E69](../evidence/PHASE69.md) içinde ayrı korunur, başarılı GUI sayılmaz.

Resmî kaynaklar geliştirme sırasında2026-10-16 incelendi:
[sklearn common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html),
[sklearn calibration](https://scikit-learn.org/stable/modules/calibration.html),
[SciPy t-test confidence interval](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_1samp.html).
Kullanımda bu kaynaklara ağ isteği yapılmaz. Önceki resmî kabuller ayrı açık.
