# Veri_Ufku — ürün ve ilk sürüm kapsamı

Güncel teknik kapsam: Faz00–26; 2026-10-10 Europe/Istanbul. Veri inceleme, seçilmiş temizlik/dönüşüm, grafik, export, rapor ve soru odaklı istatistik uygulanmıştır; model hazırlığı, ayırma, sınırlı estimator aileleri, etiketsiz analiz, model kartı ve güvenli yeni dosya tahmini mevcuttur. Teknik doğrulama ve gerçek kullanıcı kabulü ayrı tutulur; kullanıcı testleri kullanıcının isteğiyle bu taramadan sonra yapılacaktır. Kalıcı kurallar: [PROJECT_RULES](PROJECT_RULES.md), [UI_DESIGN_BRIEF](UI_DESIGN_BRIEF.md). Kabul: [REQUIREMENTS_MATRIX](REQUIREMENTS_MATRIX.md).

## Kullanıcı ve değer

Başlangıç kullanıcısı dosyasının anlamını, sorunlarını ve değişiklik etkisini kod yazmadan görür. Öğrenen kullanıcı işin yanında açıklama açar. Uzman aynı veri ve sonuçlar üzerinden yöntem, filtre ve tanılamaya erişir. İstatistik/model kullanmak zorunlu değildir. Açılışta amaç: inceleme, temizleme, grupları karşılaştırma, ilişkiler, tahmin, benzer kayıtları gruplama veya sıra dışı kayıtları bulma. Yalnız geliştirilmiş yollar etkinleşir.

## Kullanıcı hikâyeleri ve sıfır bilgi senaryoları

### US-01 — Dosyamı anlamak istiyorum (Faz 05–08, 12–13)

Bir mağaza çalışanı olarak satış listemde ne olduğunu bilmek istiyorum; dosyam değişmeden satırları, eksikleri ve satış tutarlarının dağılımını anlayabilmeliyim.

Paket kabul örneği [magaza.csv](../src/veri_ufku/assets/examples/magaza.csv): 12 kayıt, kimlikler `0001`–`0012`, gün, şube, tutar; 2 tutar eksik, geçerli tutarlar 10,20,20,30,40,50,60,70,80,100. Veri tamamen yapay ve CC0. Elle hesap: toplam 480, ortalama 480/10=48, medyan (40+50)/2=45. Önceki belge toplam580/ortalama58 diyordu; bu aritmetik hata [tarama kaydında](evidence/AUDIT_00_13.md#e-audit-reference) düzeltildi. CSV ayarları: ayraç `;`, null işareti `\N`, kimlik/metin, gün/date `%Y-%m-%d`, tutar/Decimal. Gerçek GUI import/profil/histogram/Parquet export/yeniden açma bu referansla denetlenir.

1. “Veriyi incelemek” → “Örnek dosya” veya kendi CSV'si.
2. Önizlemede kimliklerin baştaki sıfırını, tarih biçimini ve virgüllü ondalık ayarını görür. Algılama önerisini onaylar; hata varsa düzeltir.
3. Kaynağı projeye kopyalama tercihini görür; kopya kapalı olsa da çalışma snapshot'ı gerekliliği anlatılır.
4. Tablo üstünde “12 kayıt / 4 sütun / tüm veri”; kalite kartında “2 tutar eksik” görür. Kimlik “Kayıt tanımlayıcısı” olarak gösterilir ve ölçüm önerilmez.
5. Tutarı seçer; “Medyan — sıralanmış değerlerin ortası” ve açıklama bağlantısını görür. Histogramı seçer, eksiklerin dışlandığı 10 kayıt kapsamını görür.
6. PNG/SVG veya özet raporunu farklı hedefe kaydeder; proje yeniden açıldığında veri sürümü ve filtre korunur. Kaynak byte hash'i değişmemiştir.

Başarı: ilk kez kullanan kişi sözlü yardım olmadan akışı tamamlar; aynı örnekte n, eksik ve medyanı doğru anlatır. Bu kullanıcı testi Faz 25'te ayrı kanıttır, şu an doğrulanmadı.

### US-02 — Verimi temizlemek istiyorum (Faz 08–11, 13)

Bir ofis çalışanı olarak şube adlarındaki boşlukları düzeltmek istiyorum; önerinin nedenini, değişecek kayıtları ve geri dönüş yolunu görebilmeliyim.

Paket kabul örneği [subeler.csv](../src/veri_ufku/assets/examples/subeler.csv): 6 kayıt; `Ankara`, ` Ankara `, `İzmir`, `İzmir `, `Bursa`, `Bursa`; benzersiz kaynak kimlikleri. Ayraç `;`, iki sütun metin. Kırpma tam 2 kaydı değiştirir; kaydı azaltmaz. İçeriği aynı iki Bursa kaydı ayrı kalır. Gerçek GUI önizleme/apply/undo/redo/yeniden açma ve RowId/SourceRecordId korunumu denetlenir.

1. Temizleme amacı → import → kalite paneli “2 kayıtta baş/son boşluk var; farklı gruplar oluşabilir”.
2. “Metin boşluklarını temizle” seçer. Açıklama alan içinde anlamlı boşlukları koruduğunu anlatır.
3. Önizleme aynı RowId ile önce/sonra yan yana; 2/6 etkilenen kayıt, 0 silme, 0 yeni null. Hiçbir dönüşüm seçimden önce uygulanmaz.
4. “Uygula” yeni DatasetVersion üretir. Tekrar kayıt önerisi ayrı kalır; kimliğin farkı görünür. Kullanıcı dedup seçmeden silme olmaz.
5. Geri al → önceki sürüm; yeniden uygula → yeni dal. İşlem geçmişinde tarif, karar ve etki korunur.
6. “Farklı dosyaya aktar” CSV hedefini seçer, ardından proje kaydı. Kaynak korunur. Kaydetme hatasında son sağlam sürüm açılabilir.

Başarı: 6 kayıt ve iki farklı Bursa SourceRecordId'si korunur, 2 metin değişir, geri alma byte/değer bütünlüğünü korur. Genel doldurma seçilirse model yolunda veri bağımlı geçmiş olarak işaretlenir.

### US-03 — Tahmin yapmak istiyorum (Faz 15–18, 20)

Bir bakım sorumlusu olarak yeni ekipmanın enerji tüketimini tahmin etmek istiyorum; sonucu kesin gerçek sanmadan basit bir karşılaştırma ve hata birimi görebilmeliyim.

Planlanan yapay eğitim örneği: 60 cihaz × 12 ay = 720 kayıt; cihaz kimliği, ölçüm zamanı, yaş, çalışma süresi, tüketim kWh; hedef ufku gelecek ay. Ek dosya 5 yeni cihaz için tahmin anında bilinen özellikler içerir. Gelecek ayın tüketimi veya arıza sonucu özellik olamaz. Sayısal cihaz kodu ölçüm değildir.

1. “Tahmin etmek” → “Bir sayıyı” → hedef `tuketim_kwh`. Hedefin neyi anlattığını sade dille teyit eder.
2. “Ne zaman tahmin?”, “Kaç ay sonrası?”, “Aynı cihazlar mı yeni cihazlar mı?” sorulur; cihaz ve zamanı seçer.
3. Yeni cihaz ve gelecek zaman hedefinde hem cihaz ayrılığı hem zaman sınırı sağlanır. Eğitimde daha eski aylar/eski cihazlar; validation ve testte ayrık cihazlar/daha ileri aylar. Yeterli örnek/sınıf yoksa geçerli plan bulunamadığı gerekçesiyle durur. Rastgele split'e sessiz dönmez.
4. Eksik doldurma/ölçekleme yalnız eğitim fold'unda fit edilen ML pipeline'ında önerilir. Önceden tüm veriyle yapılan doldurma/özellik seçimi geçmişi incelenir; bağımsız ham sürüme dönme veya keşifsel kullanım seçimi gerekir.
5. Baseline ve dar model adayları validation/CV ile karşılaştırılır. MAE kWh cinsinden anlatılır; örnek sonucun sayısı hesap gerçekleşmeden yazılmaz.
6. Final testi ayrı açar; veri/protokol/run kimliğiyle deftere kaydedilir. Sonraki ayar yeni run olsa da aynı test yeniden kullanımı görünürdür. Bağımsız değerlendirme gereği açıklanır; kullanıcı davranışının tamamını denetleme iddiası yoktur.
7. Desteklenen güvenli model paketini kaydeder; yeni dosya eşlemesini önizler. Eğitim pipeline'ı yalnız transform/predict; 5 satır sonucu RowId ile eşlenir. Güvensiz dış pickle/joblib açılmaz.

Başarı: target/gelecek bilgi sızmaz; grup ve zaman birlikte ayrılır; baseline, hata birimi, fit sınırı, tekrar test kaydı ve sonuç eşlemesi bağımsız testlerle kanıtlanır. Model yolları Faz 13 sürümünde henüz mevcut değil.

## Ölçülebilir teslim sınırları

İlk kullanılabilir inceleme/temizleme sürümü Faz 00–13'ün zorunlu şartlarıdır: CSV/TSV, JSON/JSONL, XLSX, Parquet; proje aç/kaydet/farklı kaydet/kurtarma; sayfalı tablo/rol/profil/kalite; işlem önizlemesi/geçmiş/geri alma; Faz 10–11 dönüşümleri; Faz 12'deki yedi grafik türü, PNG/SVG ve Faz 13 raporları; çevrimdışı yardım ve örnekler. Dosya biçimi, dönüşüm ve grafik başına ayrı kabul kaydı gerekir. US-01/02 gerçek masaüstünde tamamlanmalıdır. [Performans hedefleri](PERFORMANCE.md) ayrıca ölçülür.

Faz 20 temel ML eşiği, Faz 27 temel dağıtım adayıdır. Faz21–23 açık kullanıcı seçimiyle teknik olarak uygulandı; insan/bağımlılık kabulü açık. Faz 28–75 profesyonel kapsam Faz 28'de seçilecektir; liste onların geliştirilmesini başlatmaz. Dağıtım adayı erken paket smoke hatalarını, kritik kayıp/sızıntı hatalarını ve zorunlu kabul açıklarını kapatmadan verilemez.

## Açık ürün kararları ve riskler

| Kimlik | Karar / risk | Politika ve kapanış |
|---|---|---|
| D-01 | Hücre/satır düzenleme ve tabloya panodan yapıştırma | İlk sürüm salt okunur. Veri dönüşümleri yalnız işlem motoru. Kopyalama serbest; kayıtlara yapıştırma yok. Ek kapsam seçilmedi; seçilirse EDIT-* kimlikleri, parse/undo/kimlik/transaction/ölçek/sızıntı testleri zorunlu. |
| D-02 | Kaynak kopyalama | Varsayılan orijinal dosya kopyası kapalı; tutarlı çalışma snapshot'ı zorunlu. Disk ve gizlilik maliyeti importtan önce açıklanır. |
| D-03 | Marka | Kullanıcının seçtiği Veri Bağları (v2/02) logosu; metin adı tam olarak Veri_Ufku. [Uygulama kanıtı](evidence/UI_BRANDING.md). |
| D-04 | Proje taşınabilirliği | Çalışma verisi ve yardım kimlikleri projede; asıl kaynak yoksa yeniden import sınırlıdır. Paylaşım önizlemesi içerilen veri miktarını gösterir; metadata-only paylaşım profesyonel faza bağlı. |
| O-01 | Uygulama lisansı / uygulama-ID alan adı | Kullanıcı/yayıncı kararı açık; ADR-001/004. Paket release kapısı; Faz 00 planını engellemez. |
| O-02 | 21–23 ve profesyonel modüllerin seçimi | Faz21–23 kullanıcı tarafından seçilmiş zorunlu kapsam; profesyonel Faz29–75 önceki isteğe bağlı kapsamını korur, teslim seçimi bekleniyor (DEC-28-02). |
| R-01 | Kaynak okuma sırasında değişir | Sabit snapshot + digest doğrulaması; güçlü snapshot alınamıyorsa işlemi durdur. |
| R-02 | Disk dolması/elektrik kesilmesi | ADR-003 yayınlama sırası, yerinde ezme yok; backup ve fault injection. |
| R-03 | Örneklem tüm veri sanılır | Her sonuçta kapsam/n/seed/seçim yolu, seçimin sınırlamaları. |
| R-04 | Öğrenilmiş temizlik model sızıntısı | Tarifin learned_scope bilgisi, ham sürüm, fold-içi fit. |
| R-05 | Dönüşüm hassasiyet kaybı | Sözleşme tip sınırı; kaybı önizle veya reddet. |
| R-06 | Yeni format/model desteği olduğundan geniş gösterilir | Capability yöntem başına gerçek destek ve mevcut değil durumu; desteklenmeyen yükleme durur. |

Bu kararlar Faz00'da kaydedildi; uygulanan bölümlerin kanıtı matriste yöntem başına bağlıdır. Gelecek kararlar uygulanmış güvence sayılmaz. Kullanıcı yetkisi olmadan veri kopyalarını silme, kayıplı migration veya mevcut projeyi yeniden yazma yok.


## Faz14 — Kullanıcı sorusundan istatistiksel analize

Karşılaştır ekranı iki bağımsız grup, aynı kişilerin önce/sonrası, üç veya daha çok grup, iki kategori ve iki sayısal ölçüm sorularını sunar. Kullanıcı ölçüm/grup/kişi anahtarını, birimi, bağımsız gözlem birimini, soruyu ve hipotezi belirtir. Önkontrolü ve dağılım/uç değerleri inceleyip varsayımları onaylar; yöntem otomatik seçilmez. Sonuç n/dışlamalar, istatistik/p, birimli fark veya uygun sıra/korelasyon/odds etkisi, mevcut CI ve olmayan CI gerekçesini gösterir. Kullanıcı sonuçları projeye kaydedebilir; kaydedilmiş analiz HTML/PDF raporuna dahil olur. Bootstrap, permutation, eşleştirilmiş kategoriler, ağırlık/küme/zaman bağımlı çıkarım bu sürümde sunulmaz. [Sınırlar ve kanıt](evidence/PHASE14.md).

## Faz15 — Modelleme için ayrı hazırlık

Model ekranında regression/classification/clustering/anomaly amaçları, hedef/özellikler ve aile seçilir. Tam kaynak n/eksik hedef/sabit/kimlik/kardinalite/sınıf/tarih/grup ve şüpheli türevler gerekçelidir. Geçmiş tüm-veri öğrenimi veya seçim kararları görünür; gerçek önceki temiz sürüm ve desteklenen kuralları eğitim katına taşıma seçenekleri vardır. Eğitim değil, fit edilmemiş plan kaydedilir. [Kanıt](evidence/PHASE15.md).

## Faz16

Model ekranı Faz16 ile ayırma/validation/CV ve basit mean/median/Dummy karşılaştırması sunar. Kayıt yapısı, tahmin anı/ufuk, yeni varlık/aynı varlığın geleceği ve alan kullanılabilirliği açıkça sorulur. Kısıtlar çakışırsa durur. Final test ayrı eylem ve proje geneli kalıcı defterdir. Sonraki estimator aileleri/yeni dosya tahmini henüz yok. [Kanıt](evidence/PHASE16.md).

Faz17: sınırlı sayısal tahmin yolu, Faz15 hazırlığı ve Faz16 split/fold/defteri üstünde gerçek training-only estimator pipeline kullanır. Adaylar baseline/doğrusal/Ridge/RandomForest; seçim yalnız geliştirme CV MAE, final testte tek dondurulmuş aday. MAE/RMSE hedef birimi, R² negatif/sabit hedef sınırı, gerçek-tahmin/artık grafikleri (en fazla1000 örnek; metrik tam bölüm), dar ayar/maliyet sınırları ve test sonrası keşifsel yorum. Ayrıntılı sözleşme [ADR-020](adr/020-regression-phase17.md), gerçek kabul [PHASE17](evidence/PHASE17.md).


## Faz18 kategori tahmini

Kullanıcı etiketli bir hedef için kategori tahmin eder: Baseline, LogisticRegression ve sınırlı RandomForest başlangıç adayları, ikili/çok sınıflı hedef, açık pozitif sınıf ve azınlık dağılımı. Matris ve sınıf bazlı metrikler accuracy yanında görünür. Model geliştirme CV F1 ile, eşik ayrı validation üzerinde seçilir. Final ayrı onay ve dondurulmuş karar kullanır. Hata maliyeti açıklaması kaydedilir; saha güvenliği garantisi verilmez. Geçmişteki test tekrarları ve sonraki ayarlar keşifseldir; proje dışı kullanım bilinmez. Teknik yetenek deneysel, insan kabulü açık. [ADR-021](adr/021-classification-phase18.md), [gerçek teknik kayıt](evidence/PHASE18.md).


Faz19: Model amaçlarından iki ayrı etiketsiz yol; KMeans/DBSCAN küme keşfi ve IsolationForest/tek sütun IQR anomali adayları. İşaretli yeni dataset tüm kayıtları korur; gerçek sınıf/hata veya etiketli başarı iddiası yok. Yeni dosya model yolu henüz mevcut değil.

Faz20: Model alanında kayıtlı fitted model kartı/güvenli .vumodel kaydet-aç ve
önizlemeli yeni DatasetVersion tahmini. Yeni dosya mevcut Veri import akışından
alınır; kolon eşleme, exact tip/birim, eksik/unknown/fazla alanlar görünür. Sonuç
kaynak satırları/RowId ile yeni Parquet'e aktarılır; kaynak ezilmez, yeni veride fit
ve otomatik silme yok. DBSCAN ve diğer destek matrisi dışı modeller engelli.
[ADR-023](adr/023-model-lifecycle-phase20.md), [kanıt](evidence/PHASE20.md).


Faz21 teknik kapsamı: normal regresyondan ayrı, kaynak değiştirmeyen zaman serisi
inceleme/tahmin; gerçek naive/seasonal-naive ve sınırlı toplamsal
ExponentialSmoothing, grup bazlı rolling-origin ve gelecekte saklı final test.
Açık frekans/agregasyon kontrolü ve minimum geçmiş retleri; aralık desteklenmez.
[Kabul ve sınırlamalar](evidence/PHASE21.md).


Faz22 kullanıcı tarafından seçildi: yerel, açık dil/Unicode/token/stopword/n-gram
ve TF-IDF incelemesi; ham önizleme opt-in/logsuz. Etiketli metinde mevcut
classifier/baseline/final defteri ve train-only vocab; etiketsizde ayrı opsiyonel
kosinüs, otomatik duygu/konu etiketi yok. [Teknik kabul](evidence/PHASE22.md).


## Faz23

Faz23 yeni veri için güvenli tekrar kullanılabilir akış, betimsel drift ve sonradan gelen hedefle kimlik bazlı performans sunar. Hedef yoksa başarı metriği yok; dağılım değişimi otomatik model başarısızlığı değil. Analiz tarifi eğitim pipeline değildir. [ADR-026](adr/026-recipes-monitoring-phase23.md), [kanıt](evidence/PHASE23.md).


## Faz24

Mevcut import/analiz/model yolları ölçülmüş kaynak bütçesiyle çalışır; model maliyet öngörüsü ve açık özellik daraltma, bounded sayfa cache ve iptal/önceki proje koruması. Benchmark örneklemi tam hesap yerine gösterilmez. [ADR-027](adr/027-performance-phase24.md), [kanıt](evidence/PHASE24.md).

## Faz25

Mevcut denetim devam talimatıyla sürdürüldü: ortak klavye/erişilebilirlik
kontrolleri, isteğe bağlı görünüm/dil ayarları, temel İngilizce ve çevrimdışı
yardım incelemesi. Beş gerçek geliştirici walkthrough’u insan testi değildir.
[Kanıt ve açık kabul](evidence/PHASE25.md). Faz26 başlatılmadı.

## Faz26

Sentetik güvenilirlik denetimi, kayıtlı sürümün korunması ve önizlemeli
kurtarma, eski şema açılışı, parser/log/SQLite korumaları mevcut yolda
uygulanır. Teknik kabul insan/AT veya dağıtım adayı kabulü değildir.
[Gerçek kapsam ve sınırlar](evidence/PHASE26.md). Faz27 başlatılmadı.


Faz28 yeni model eklemeden mevcut ürünü denetledi. [Profesyonel ürün/üç akış](PRO_PRODUCT.md) ve [teknik yetenek matrisi](PRO_CAPABILITY_MATRIX.md) gelecekteki seçilmiş kapsamı mevcut davranışlardan ayırır. Giriş kabulü açık, yeni uzman geliştirme engelli.

Faz30 açık teknik kapsam: partitioned Parquet/Arrow dataset, Avro OCF, ORC, seçilmiş HDF5 compound key, XML düz kayıt yolu, sabit karakter genişliği, SPSS SAV/Stata DTA/SAS sas7bdat ve bounded gzip/ZIP. Yalnız gerçek doğrulanan varyantlar deneysel; [format tablosu](evidence/PHASE30.md#e30-formats). Önceki ürün kabul kapıları açık; Faz31 başlamadı.


Faz31 teknik bağlantı kaynakları: PostgreSQL/MySQL/MariaDB salt okunur
ordinary tablo/sorgu, yerel DuckDB, HTTP GET/JSON next sayfalama ve tek S3
nesnesi. Gelişmiş altında açık eylemle kopya alınıp önizlenir; mevcut veri
otomatik değişmez. Credential Secret Service keyring'inde, projede referans;
snapshot çevrimdışı yeniden açılır. [Varyantlar/kabul](evidence/PHASE31.md).


Faz32: sürümlü kolon sözlüğü/kalite sözleşmesi ve insan onaylı canonical ilişki
teknik kapsamı eklendi. Fiziksel kaynaklar korunur; onaysız merge yok;
kaydedilmiş kontrol ve insan kararları sürümlerle izlenir. [ADR-033](adr/033-data-contracts-phase32.md).


Faz33 Karşılaştır → Eksik veri, örnekleme ve ağırlıklar. Önkontrol/onay/Hesapla, ayrı kimlikli çıktı kaydı/export/reopen. Model hazırlığı: missing indicator, KNN ve iterative yalnız eğitim katında. MI mean/OLS çıkarımı ayrı; ağırlık türü açık kullanıcı seçimi. [Gerçek kanıt ve sınırlar](evidence/PHASE33.md).


Faz34: Veri → İçe aktar → Gelişmiş; NetCDF/yerel Zarr/HDF5 array formatı, ölçüm değişkeni, JSON boyut kesiti ve koordinat seçimi. Maliyet tablodan önce gösterilir. Fill/scale çözümü ve hedef birim açık seçilir. İncele → array2D ısı haritası/profil; kaynak kanıtı gerekir, ek boyutlar için toplulaştırma açık seçilir. [Sınırlar](evidence/PHASE34.md).


Faz35: İncele → grafik türü içinde violin/KDE/ECDF/rug/strip/swarm/QQ/PP/error-bar/CI band/missing-pattern. Histogram/box grup/facet ve açık ağırlık türü; dağılım/belirsizlik/görünüm ayarları ile normalizasyon, bandwidth, SD/SE/CI, eksen, font/palet/annotation/DPI. Teknik doğrulama ve resmî kabul [Faz35 kaydında](evidence/PHASE35.md) ayrıdır.


Faz36 İncele ekranı: pair/scatter matrix, CPU hexbin/2D histogram density, bubble, grouped/clustered heatmap, sayısal parallel, facet ve koşullu ilişki. Açık ölçek/örnek/üyelik; brushing görünüm ve yeni dataset önizleme ayrı eylemler. 3D/surface isteğe bağlı uygulanmadı. [Kayıt](evidence/PHASE36.md).


Faz37 İncele ekranı:17 kompozisyon/hiyerarşi/akış/işgrafiği ve soru araması. Pie/donut6kategori; advancedradar minmax. Payda/eksik/tekrar/balance/doublecounting açık. [Kayıt](evidence/PHASE37.md).
