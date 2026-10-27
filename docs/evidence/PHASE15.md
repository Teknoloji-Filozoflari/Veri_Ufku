# Faz15 — Modelleme için veri hazırlığı

2026-10-08, ENV-15; yalnız açık kullanıcı Faz15 talimatı. Genel temizlikten ayrı hazırlık; sonraki faz başlatılmadı. Faz13 F13-S005 gerçek insan kullanıcı kabulü açık olduğundan Faz15 sürüyor/deneysel; teknik doğrulama bu kabulün yerine geçmez.

<a id="e15-s001"></a>
## Ayrı Model ekranı

PreparationPanel/QML, ui/preparation ve ayrı spawn worker: amaç/hedef/özellik/model ailesi, tam kaynak n ve risk raporu → plan → kaydet/yeniden aç. Dört amaç gerçek QML'den çalıştırıldı; worker PID farklı. Ayarlar sonuçtan sonra katlanır ve tekrar açılır. Kimlik adayları varsayılan seçilmez; hedef/grup özellik dışındadır. Genel temizlik ve kaynak dosya değiştirilmez. [Kaynak ölçümü](phase15/headless.json), [kurulu wheel](phase15/wheel.json), tests/test_preparation_gui.py.

<a id="e15-s002"></a>
## Uygunluk ve gerekçeli risk

Eksik/sonlu olmayan hedef, sabit/boş hedef/özellik, fiziksel hedef türü, kimlik adı/rol adayı, yüksek kardinalite, tam sınıf sayımı/minimumu, tarih/grup tekrarı/eksik anahtar, örnek miktarı ve hedef türevi adayları. Hedef ad/işlem bağı/birebir eşlik şüphedir; otomatik kesin sızıntı tespiti veya sızıntısızlık garantisi yok. Eksik hedef doldurulmaz; sayımda dışlama açık. Sınıf gösterimi ilk20; min class bütün sınıflardan hesaplanır. Uzun etiket gösterimi256+hash; kategori sözlüğü değildir. Küçük örnek/kardinalite/baskın sınıf eşikleri heuristik, güç/genelleme garantisi değil. tests/test_preparation.py bağımsız6 kayıt,5 geçerli hedef,1 dışlama,3/2 sınıf, null/nonfinite/sabit/kimlik örneklerini doğrular.

<a id="e15-s003"></a>
## Eğitim katında öğrenilecek plan ve kolon eşlemesi

Encoding onehot veya açık semantik sıra ile ordinal; sayısal impute mean/median/none ve kategori most_frequent/none; ağaçta auto scaling yok, doğrusal/uzaklıkta standard; açık override gerekçesi kaydedilir. Date/Datetime yıl/ay/haftanın günü satırdan; opsiyonel sıfır varyans seçimi yalnız eğitim katında. Tümü planned, fitted_parameters boş; scale/impute değerleri/kategori sözlüğü/feature mask henüz yoktur.

Kaynak ColumnId/name/dtype → UUID tabanlı benzersiz isim/şablon ilişkisi kaydedilir. Onehot şablonları eğitim kategori indeksiyle ileride bağlanacak; henüz üretilmiş dataset kolonu değildir. Saved plan tariften yeniden oluşturulup karşılaştırılır; bozuk eşleme reddedilir. Sklearn resmî pipeline/preprocessing belgeleri tasarım için incelendi; kurulu sklearn estimator veya fit API doğrulaması iddia edilmez, runtime bağımlılık eklenmedi. [ADR-018](../adr/018-model-preparation-phase15.md).

<a id="e15-s004"></a>
## Gerçek geçmiş ve temiz kaynak

Audit bütün parent/input/fork atalarını izler; kopya geçmişi gizlemez. Dataset learned mean/median/mod/outlier ve seçim/türetme kararları görünürdür. Etkilenmiş mevcut kaynağa yeni pipeline eklemek riski kaldırmaz; review blocked kalır. Raw/relocate gerçekten önceki temiz sürüm gerektirir; bu sürümün hash ve gerçek null sayımlarından rapor üretilir. Workflow head değiştirilmez.

Desteklenen doldurma/IQR mark kuralları yalnız eğitim katında yeniden öğrenilecek şekilde taşınır; eski fill değerleri/threshold aktarılmaz, IQR multiplier korunur. Doldurma encoding/scaling öncesindedir. Aynı alandaki birden fazla geçmiş işlem sessizce birleştirilmez; temiz kaynak ve açık plan yolu açıklanır. Desteklenmeyen silme/seçim/karmaşık işlemler yeniden kurulmuş sayılmaz; proje dışındaki geçmiş bilinemez. Gerçek GUI worker akışında mean fill uygulanıp aktif kaynağın x null0, önceki kaynak seçimiyle null1 olduğu ve taşımanın mean strategy/null threshold olduğu doğrulandı.

<a id="e15-s005"></a>
## Çevrimdışı yardım

İçerik16/toplam96 makale. Hazırlık, özellik/hedef, encoding, scaling, imputasyon, eğitim katı ve geçmiş; kullanım/uygunsuzluk/örnek/sık hata/yorum/kritik uyarı/resmî kaynaklarla paketli. Model/F1 bağlamı model-preparation. Dört gerçek QML amaç testinde tüm yeni bağlar açıldı; kurulu wheel F1 gerçek tuş olayı çalıştırıldı. Yardım eğitim eylemi üretmez; normal kaynak/veri durumunu değiştirmez.

<a id="e15-s006"></a>
## No-fit, atomik plan ve regresyon

Hazırlık yalnız betimsel sayım ve seri hale getirilebilir blueprint üretir; estimator/transformer yok, tüm veri üzerinde fit yok. Kaynak immutable; güncel project/origin/source/revision zorunlu. Başarısız yeni iş, iptal veya eski sonuç önceki planı güncelmiş gibi bağlamaz. blocked plan risk taslağı olarak kaydedilebilir; eğitim onayı değildir. Kayıt sonrası plan aynı eşleme/strateji/geçmişle tekrar açılır.

Hash/aktif origin/history/tarif/eşleme kontrolü sonrası güvenli JSON metadata, mevcut atomik ACTIVE protokolüyle saklanır; schema7 additive results. Fault pointer_written önceki ACTIVE'yi korur. İki gerçek SIGKILL pointer_written/pointer_replaced sonrasında önceki veya yeni tam commit açıldı; gerçek ikinci süreç readonly publication reddedildi. Testler kaynak/workflow korunmasını ve mapping tamper reddini doğrular.

Yerel locked standart kontrol sonuçları [pytest](phase15/pytest.txt), [kapılar](phase15/checks.json), [komut çıktıları](phase15/checks.txt); [kurulum](phase15/sync.txt), [build](phase15/build.txt), [wheel kurulum](phase15/install.txt). Kaynak100k ve kurulu wheel dört amaç/history/100k/iptal/eski sonuç ölçümleri yukarıda bağlı. Yerel geliştirme offscreen/software kanıtı; yeni fiziksel Wayland/insan kabulü/uzak CI/temiz offline kurulum/minimum donanım iddiası yok. CI'a wheel hazırlığı adımı eklendi, uzakta çalıştırılmadı.

<a id="e15-environment"></a>
## Ortam ve ölçüm sınırı

ENV-15: mevcut locked Linux CPython3.13.15/Qt6.11.2/Polars2.0.0; yeni runtime dependency yok. Python TCP parent/spawn reddi, yeni XDG; OS ağ arayüzleri kapatılmadı. [Ortam/hash kaydı](phase15/environment.json). GUI tick/RSS süreleri belirli geliştirici makinesinde ölçümdür; minimum donanım kabulü değildir. Sistem Python ortamı kilitli runtime değildir; test komutları kilitli Python ile yürütülür.

İlk kontrol kayıtları korunur: kanıt dosyaları henüz tamamlanırken yerel link kontrolleri hata verdi; eski yardım testi beklentileri yeni bağ/glossary sayımına uyarlanıp yeniden çalıştırıldı. Ara regresyon turunda yeni test import adı hatası düzeltildi. Bunlar başarılı kontrol sayılmaz; son kapı kayıtları ayrı dosyalardadır. Sistem Python3.14 unittest32 modül import hatası verdi ([kayıt](phase15/system-unittest.txt)); kilitli Python3.13 kontrolü esas alınır.

Son ölçüm:100k kaynak 213.1ms / wheel 234.7ms; iptal 180.5/238.4ms, parent+worker peak 626.0/625.2MiB.50ms GUI tick hedefi, actual 74.0/87.8ms. Geliştirici ortamında eşzamanlı regresyon yükü; ölçüm tam akışta import/layout dahil, minimum donanım kabulü değil.

Nihai regresyon:419 pytest ve9 locked unittest başarılı. Frozen dev sync, check_docs (sistem ve locked), check_artifacts, check_learning (96 makale/56 bağ), Ruff check/format ve offscreen/software kurulu giriş noktası smoke geçti. Kaynak ve kurulu wheel üyeleri son kaynakla byte/hash eşleşir. Dört amaç hazırlık kabulü F15-PREP-REGRESSION/CLASSIFICATION/CLUSTERING/ANOMALY matris alt kayıtlarıyla ayrı izlenir.
