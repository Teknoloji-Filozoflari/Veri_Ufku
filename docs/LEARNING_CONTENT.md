# Veri_Ufku — çevrimdışı öğrenme içerik sözleşmesi v1

Faz03, 2026-10-06. Ürün içeriği `src/veri_ufku/learning/content/tr.json`, Qt'siz doğrulayıcı `learning/catalog.py`, sunum `ui/learning.py`, render `ui/qml/ArticleView.qml` içindedir. Analitik veya worker kodunda öğretim metni tutulmaz. Türkçe içerik ilk pakete dahildir; uygulama açılışında kaynak indirme yoktur. Kaynak URL'leri atıf metnidir, uygulama bunları açmaz/indirmez.

## Şema ve sürümler

Katalog tam alanları: `schema_version=1`, pozitif `content_version`, `locale=tr`, `articles`, `contexts`, `actions`. Bilinmeyen şema sürümü reddedilir; yeni içerik yayını katalog sürümünü artırır, değişen makalenin sürümü ayrıca artırılır. Kalıcı makale kimliği yeniden kullanılmaz. Şema değişimi yeni okuyucu/migration kararı gerektirir; içerik sürümü yöntem sürümü değildir.

Her makale tam alanları:

| Alan | Anlam / doğrulama |
|---|---|
| id / content_version / locale | Küçük ASCII kalıcı kimlik, pozitif tam sürüm, tr |
| title / category / summary | Başlık, arama kategorisi, tek cümle sade açıklama |
| purpose / when / when_not | Ne işe yarar, ne zaman kullanılır, ne zaman uygun değildir |
| example.before / example.after | Küçük önce/sonra; yazılı öğretim örneği, hesap motoru sonucu değildir |
| interpretation / common_mistake | Sonucu nasıl yorumlarım, sık hata |
| guide | Sadece paragraph veya note türünde `{kind, text}` blokları |
| critical | Her derinlikte ve başlangıç/gelişmiş modda katlanmadan gösterilen uyarı |
| related | Katalogda var olan makale kimlikleri |
| contexts | Kayıtlı ekran/işlem anahtarları; görünen başlıklar sunumda çözülür |
| sources | title, reference, reviewed; HTTPS veya yerel docs/*.md atfı ve inceleme tarihi |
| try_action | null veya uygulanan allowlist eylemi; serbest fonksiyon/komut adı olamaz |

Makale metni boş olamaz, alan başına4000 karakter; katalog en fazla500 makale/2MB; rehber en fazla30 blok. Aynı kimlik, eksik alan, bozuk kavram/ekran/işlem bağı, HTML blok türü, tehlikeli kaynak URL şeması ve uygulanmayan deneme eylemi reddedilir. Render tüm içerik alanlarında `Text.PlainText` kullanır; HTML görünümlü metin de düz yazıdır. WebView/WebEngine, eval/exec, JavaScript içeriği veya Markdown HTML eklentisi yoktur. QML uygulama kodu ile içerik metni ayrı güven sınırlarıdır.

## Derinlik ve bağlam

Tek cümle: özet + kritik uyarı. Bir dakikalık örnek: bunlara önce/sonra ve yorum eklenir. Ayrıntılı rehber: uygunluk, sık hata, rehber blokları, ilgili ekran/işlem ve kaynaklar eklenir. İlgili kavramlar bütün derinliklerde erişilebilir. Okumak zorunlu değildir; F1 veya aynı “Bu ne işe yarar?” eylemiyle panel açılır, Escape/kapat ile açan kontrole odak döner. İş/config/result değişmez.

`contexts` ekran anahtarını makaleye eşler; sekiz kabuk ekranı ve dört gerçek demo capability bağı zorunludur. F1 odaklanan kontrolün helpContext bağını önceliklendirir, yoksa seçili ekran bağını kullanır. Görevlerin yanında ayrıca yardım düğmesi vardır. Öğren listesi veya ilgili kavram doğrudan makale açar. Yardım paneli açıkken navigasyon bağlamı yeni ekranın makalesine geçer; metin okumak ekranı değiştirmez.

## Gerçek deneme sınırı

Faz03'te allowlist yalnız `learn.example → learn.search` içerir. “Yardımı kendi hızında oku” makalesindeki Uygulamada dene, aynı gerçek LearningCenter/ArticleView bileşenlerini ayrı geçici **örnek öğrenme projesinde** açar. Bu proje yalnız bağımsız sorgu, kategori, makale ve derinlik state'i taşır; dosya/dataset yükleme, proje kaydetme veya analitik motor gibi sunulmaz. Ayrı learning-example UUID, ana DemoSession Binding/JobSpec'e girmez. Yerel okuma kaydı bu örnekte kapalıdır; her yeniden açılış bağımsız başlangıçla hazırlanır. Kullanıcının oturumu ve dosyası değiştirilmez. Analitik makalelerde deneme eylemi yoktur. Gerçek veri projesi deposu Faz04 ve sonraki fazlara aittir.

## Yerel tercihler

Arama Türkçe İ/ı ve aksanları sorgu için normalize eder; veri sıralama sözleşmesini değiştirmez. Sözlük dokuz temel kavramı, kategori ilgili konuları seçer. Okundu/yer imi varsayılan kapalı, otomatik geçmiş yoktur. Kullanıcı açıkça açarsa yalnız makale kimlikleri `XDG_CONFIG_HOME/veri_ufku/learning-marks.json` şema1 dosyasına QSaveFile/direct-write-fallback kapalı/0600 ile atomik yazılır. İşaretler kullanıcı eylemiyle değişir; makale açmak otomatik okundu yazmaz. Kapatma ve temizleme tek atomik yayında işaretleri kaldırır. Bozuk/uyumsuz dosya korunur, uyarı gösterilir; kayıt hatası yardımı veya işi kapatmaz. Aynı anda birden fazla uygulamadan okuma işareti düzenleme birleştirme desteği yoktur. İşaretler kimliğe bağlıdır; içerik revizyonu otomatik yeniden okunmadı ilan edilmez.

## Her yeni faz için katkı ve kapı

1. Yeni ekran/işlem için makale veya uygun mevcut makale bağı ekle. Yöntemin uygun olmayan kullanımını ve sonuç kapsamını günlük dille yaz; ilgili kavramlar ve kaynakları belirt.
2. Katalog/makale içerik sürümünü güncelle. Yeni capability `help_links` boş bırakılamaz; ilgili contexts eşlemesini ekle. QML düğmesinde `helpContext: "kayıtlı-anahtar"` belirt.
3. Uygulamada dene ancak gerçek yetenek ve bağımsız örnek proje yolu varsa UI allowlist ve testiyle eklenir. İçerik dosyasına komut yazmak yetenek oluşturmaz.
4. `uv run --frozen python scripts/check_learning.py` ve pytest çalıştır. CI aynı kapıyı zorunlu koşar. Bozuk QML/capability/makale bağları için testler var; çalışma zamanında bilinmeyen bağ anlaşılır hata verir.

İlk içerikler: Veri nedir, satır/sütun, veri türü, eksik değer, ortalama/medyan, örneklem, korelasyon, tahmin, veri sızıntısı; ayrıca dört gerçek kabuk/yardım/görev/paylaşım rehberi. NIST ve scikit-learn kaynakları geliştirme sırasında incelendi; Türkçe açıklamalar özgün sade anlatımdır. Çalışma sırasında kaynağa erişim gerektirmez. Bilimsel/kullanılabilirlik uzman incelemesi ve sıfır bilgi kullanıcı testi Faz25'te ayrıca yapılır.

## Faz04 içerik katkısı

Katalog içerik sürümü2, 14 makale. projects makalesi v1; project/project.source/project.recovery ekran ve işlem bağları, uygunluk/yanlış kullanım, kaynak referansı ve taşınabilir kopya örneği, sonuç sürümü/kilit/otomatik kurtarma sınırlamaları eklendi. Proje yardımı yeni analiz veya deneme allowlist eylemi oluşturmaz. Proje yardım derinliği manifestte saklanır; makineye ait okuma işaretleri taşınmaz. [Faz04](evidence/PHASE04.md).

Faz04 yol düzeltmesi: katalog içerik sürümü3, projects makalesi v2. Var olan üst klasör seçme ve yeni proje dizininin yolu açıklaması güncellendi.

## Faz05 uygulama bağı

Faz05 katalog içerik sürümü4/toplam21 makale. import-csv ve ayraç, encoding, başlık, tarih/saat dilimi, ondalık/binlik/null, bozuk kayıt/karantina rehberleri; import.csv/import.tsv capability bağları ve seçeneklere F1 bağları eklendi. Tür önerisi/sample sınırı, kaynak kopyası, bilgi kaybı ve karantina kapsamı her ilgili kritik açıklamada görünür. Yeni try_action yok; [kanıt](evidence/PHASE05.md).

## Faz06 katkısı

İçerik sürümü5/toplam26 makale. Dört native import capability ve JSON liste/nesne, JSONL, düzleştirme/liste açma, Excel sayfa/formül/tarih sistemi, Parquet tür koruma rehberleri; seçimlere F1 bağları. Yeni try_action yok. [Kanıt](evidence/PHASE06.md#e06-help).

## Faz07 katkısı

Faz07: içerik sürümü6/toplam31 makale; sözlük14 kavram. Tür/rol, unique, standart sapma/ddof, yüzdelik/linear ve veri profili/firstN kapsamı. dataset.view/profile/roles capability/F1 bağları. try_action eklenmedi. [Kanıt](evidence/PHASE07.md#e07-help).

## Faz08 katkısı

İçerik7: kalite, meşru tekrar, eksik veri mekanizması, aykırı gözlem için dört makale (toplam35); dataset.quality ve dört kavram bağı. Yardım hiçbir tarama/düzeltme başlatmaz; yeni try_action yok. [Karar](adr/011-quality-phase08.md), [kanıt](evidence/PHASE08.md).

## Faz09 katkısı

İçerik8/toplam38 makale; önizleme, işlem geçmişi/geri alma ve kaynak/çalışma verisi farkı. prepare/operation.rename/drop/filter bağları; yeni try_action yok, sözlük18 korunur. [Kanıt](evidence/PHASE09.md#e09-help).

## Faz10 katkısı

İçerik9/toplam51 makale, sözlük18. On üç yöntem yardımı küçük önce/sonra örnekleri ve riskleri açıklar; fill ve ordered_fill alt yöntemleri dinamik yardım bağlarıyla açılır. Dokuz capability bağı ve check_learning kapısı; yeni try_action yok. [Karar](adr/013-cleaning-phase10.md), [kanıt](evidence/PHASE10.md).


## Faz11 katkısı

İçerik10/toplam61 makale, sözlük18. Dokuz dönüşüm yöntemi ve yerel adaptör yardımı; küçük önce/sonra ve sakıncalı durumlar. join günlük müşteri/sipariş örneği, dört join türü ve n:n; grouping/pivot/long-wide/güvenli AST/null/tür/timezone açıklamaları. 13 capability bağı, yeni try_action yok. [Karar](adr/014-transformations-phase11.md), [kanıt](evidence/PHASE11.md).


## Faz12 içerik katkısı

İçerik11/toplam69 makale, sözlük26. Yedi grafik ve istatistik özeti/skew rehberi; her grafik neyi gösterir/eksen okuma, uygun olmayan kullanım, bin/grup/tekrar tarih, örnekleme ve null sayımı; ortalama/medyan farkı, çarpık dağılım ve korelasyon≠nedensellik. chart.histogram/box/bar/line/scatter/correlation/missing/summary bağları, capability help_links ve explore giriş yardımı. Yeni try_action yok; yardım veri değiştirmez. [Kanıt](evidence/PHASE12.md#e12-help).

## Faz13 katkısı

İçerik12/toplam71 makale; report makalesi gerçek rapor davranışıyla revize edildi, export ve guide eklendi; sözlük26 korunur. Beş formatın tür/null/date/kayıt/güvenlik kayıpları, yerel HTML/PDF kapsamı ve isteğe bağlı rehber bağları; yedi export capability. Yeni try_action yok; örnek proje açık GUI eylemiyle, ayrı projede açılır. [Karar](adr/016-release-phase13.md), [kanıt](evidence/PHASE13.md#e13-help).

Sağ üst simge düzeltmesi: katalog içerik13, home makalesi v2. Filiz/sürgü/ay-güneş, tooltip/klavye ve sabit yazı boyutu açıklaması mevcut home yardımına eklendi; artık mevcut olan import/proje yolu güncellendi. Yeni ekran, capability veya try_action yok. [Kanıt](evidence/UI_HEADER.md).

Tek koyu tema düzeltmesi: katalog14/home3; tema seçimi olmadığı, sabit yazı boyutu ve iki seviye simgesi anlatılır. [Kanıt](evidence/UI_DARK_ONLY.md).


## Faz14 yardım

İçerik sürümü15/toplam89 makale. Yeni18 makale: soru yolu, p-değerinin anlamı ve anlamadığı şeyler, etki büyüklüğü, güven aralığı, anahtarla eşleştirme, çoklu karşılaştırma, gözlemsel ilişki; 11 yöntem için hipotez/varsayım/etki/CI sınırı. compare/statistics.* bağları ve her capability help_links kayıtlıdır. Yardım veri değiştirmez; bootstrap örneği çalıştırılmış gibi sunulmaz. [Kanıt](evidence/PHASE14.md#e14-s005).

Faz15 içerik16: model-preparation, model-features, model-encoding, model-scaling, model-imputation, model-training-fold ve model-history. Model/F1 bağları hazırlığa taşındı. Örnek, kullanım/uygunsuzluk, hata, yorum, kritik uyarı ve resmî kaynaklar çevrimdışı paketlidir; gerçek model eğitim eylemi üretilmez. Toplam96 makale. [Kanıt](evidence/PHASE15.md#e15-s005).

Başlangıç görsel düzeltmesi: içerik17,96 makale. projects makalesi yeni klasör/seçim/son isim/ayrıntı akışını anlatır; FolderPicker içeriği ve yeni proje modalı F1/project bağını taşır. [Kanıt](evidence/UI_HOME_COMPACT.md).

## Faz16

İçerik18/toplam98 makale: model-validation ve model-test-use; model.validation/model.baseline/model.test-use bağları. Beş split varsayılanı/kısıtı, küçük/sınıfsız fold reddi, training-only fit, baseline yön/kapsam/maliyet ve final test defteri/keşifsel tekrar/proje dışı bilinmezlik anlatılır. Yeni try_action yok. [Kanıt](evidence/PHASE16.md).

Faz17: sınırlı sayısal tahmin yolu, Faz15 hazırlığı ve Faz16 split/fold/defteri üstünde gerçek training-only estimator pipeline kullanır. Adaylar baseline/doğrusal/Ridge/RandomForest; seçim yalnız geliştirme CV MAE, final testte tek dondurulmuş aday. MAE/RMSE hedef birimi, R² negatif/sabit hedef sınırı, gerçek-tahmin/artık grafikleri (en fazla1000 örnek; metrik tam bölüm), dar ayar/maliyet sınırları ve test sonrası keşifsel yorum. Ayrıntılı sözleşme [ADR-020](adr/020-regression-phase17.md), gerçek kabul [PHASE17](evidence/PHASE17.md).

2026-10-08 kullanıcı yol haritası düzenlemesi: Veri Bilimi Yol Haritası on numaralı kıvrılan aşama, açılabilir alt başlıklar ve yalnız etkileşim/ilk görünüş animasyonlarıyla sunulur. Genişte iki yana, darda tek sütuna yerleşir; alt yollar mevcut ekranlara bağlı, planlanan araçlar pasiftir. İçerik20/home.roadmap çevrimdışı yardım mevcut home makalesinde. Yeni faz veya analitik capability başlamadı. [Gerçek kayıt](evidence/UI_SCIENCE_ROADMAP.md).

### Öğren hiyerarşisi ve kullanıcı kaynak metni (2026-10-09)

`learning/taxonomy.py` yayımlanmış her konuya tek bir aşama/alt başlık atar; bütünlük testi eksik ve yinelenen üyeliği yakalar. Rehber blokları isteğe bağlı, doğrulanan düz metin `heading` alanını destekler; HTML/Markdown çalıştırılmaz. `data` açıklaması sağlanan Veri.md kaynağından düzenlenmiştir. Özgün kopya `docs/learning_sources/VERI.md`, kaynak yolu/hash ve düzenleme notu `VERI_PROVENANCE.json` içindedir. Dış dosya değiştirilmez; çalışma anında harici diske ihtiyaç yoktur. Kesikli/sürekli ayrımı ile aralık/oran ölçekleri ayrılmış, resmi Statistics Canada/OpenStax kaynakları kaydedilmiştir. Kaynakta adı geçen ve verilen dizinde bulunmayan görseller yüklenmiş gibi gösterilmez. Metin paketlenen Türkçe katalogda çevrimdışı okunur.

Öğren sadeleştirmesi (2026-10-09): Veri.md anlatımından sekiz ayrı, başlıklı konu oluşturuldu; katalog107 makale içerir. `CONTEXT_ONLY` içindeki22 eski kaynak/uygulama kavramı bağlamsal yardımda korunur, Öğren konu ağacı ve arama listesine eklenmez.85 yayımlanan konu tek alt başlığa atanır; test, bu üyeliklerle bağlamsal makalelerin kataloğu tam ve çakışmadan kapsadığını denetler. Kaynak metin/hash aynıdır. Yeni konu anlatımları düz metin, örnek ve kaynaklarla paketlenir; harici dosya runtime bağımlılığı oluşturulmaz.

Analiz metni ve kapalı kaynaklar (2026-10-09): `docs/learning_sources/VERININ_ANALIZI.md` sohbetle sağlanan metnin proje kaydıdır; `ANALIZ_PROVENANCE.json` kayıt hash'ini ve düzenleme notunu taşır. Genel bakış+beş yaklaşım açıklaması katalogda113 makale/91 görünür konuya ulaşır. Kesin tür sınırları kurulmaz; keşif geçerlilik garantisi, kümeleme/doğal dil işleme otomatik gelecek tahmini, kuralcı analiz zorunlu yapay zekâ/otomasyon gibi anlatılmaz. Yalnız isimleri verilen görseller yüklenmiş gibi gösterilmez; keşif adımları düz metinle anlatılır. Kaynaklar düğmeyle açılır; `articleOpened` bildirimi aynı konu yeniden açıldığında da kaynakları sıfırlar. Paketlenen anlatımlar çevrimdışıdır; kaynak bölümünde dış URL otomatik açılmaz.

2026-10-09 — Ön işleme kaynak metni `docs/learning_sources/VERI_TEMIZLEME.md` içine kullanıcının isteğiyle Python kodları hariç kaydedildi; provenance/hash `TEMIZLEME_PROVENANCE.json`. Sekiz yeni açıklama: genel ön işleme, temizleme, birleştirme, dönüştürme, indirgeme, min-max, z-score, ondalık ölçekleme.121 makale/99 görünür konu,62 statik yardım bağı. Kodlar içerik/pipeline olarak kullanılmaz; veri bağımlı dönüşümler yalnız train/fold içine fit edilir. Aykırı veya tekrar kayıt otomatik silinmez; ilk keşif ve hazırlık birlikte ilerler. Kullanıcı metninde ayrıntısı olmayan indirgeme kısa kavramsal anlatımla tamamlandı; genel boyut indirgeme/ondalık ölçekleme/kümeleme/düzgünleştirme araçları eklenmiş gibi sunulmaz. Yalnız adları verilen görseller kullanılmadı. Ortak yol haritası öğrenme modunda konu açar, uygulama modunda ekran yönlendirir.


2026-10-09 Veri içeriği: katalog25; dataset-profile makalesi2. Üst kart, sözlükte kullanıcı açıklaması, yeni metadata sürümü ve açık proje kaydı anlatılır. Mevcut dataset.profile/column-role/import.csv bağları kullanılır; yeni analitik capability veya try_action yoktur.


## Faz18 kategori tahmini

Katalog26/126 makale; model-classification ve classification-positive/metrics/threshold/probability eklendi.70 statik UI bağı ve model.classification capability help_links; yeni try_action yok. Pozitif sınıf/FP/FN, precision-recall-F1/averaging, validation eşiği, olasılık/kalibrasyon sınırı ve test kullanımının bilinmezliği çevrimdışı örneklerle anlatılır. Yeni konular Modelleme ağacında tek alt başlıktadır. Kaynak incelemesi kurulu sklearn birincil API/docstring kaydına dayanır; başarısız401 web erişimi çevrimiçi inceleme olarak gösterilmez. [ADR-021](adr/021-classification-phase18.md), [gerçek teknik kayıt](evidence/PHASE18.md).


Faz19 içerik27: beş yeni etiketsiz konu ve beş QML bağ; Öğren ağacında Kümeleme ve Anomali alt grupları. Kümeler gerçek sınıf değildir; noise/anomali adayı kesin hata değildir, etiket yokken precision/recall bilinmez ve otomatik silme yok. Her dört capability makale bağları gerçek check_learning kontrolündedir.

Faz20 katalog28/toplam136: model-card/importance/unknown-category/new-data/uncertainty;
beş statik QML bağ ve model.lifecycle capability bağları. Model kartı/fit kapsamı,
keşifsel validation importance/korelasyon≠nedensellik, frozen unknown/eksik,
güvenli paket/hash≠kimlik/DBSCAN sınırı, RowId ve olasılık/kalibrasyon belirsizliği.
Yeni try_action yok. [ADR-023](adr/023-model-lifecycle-phase20.md).


Faz21 katalog29/140 makale: sıklık, mevsimsellik, lag ve geçmişten geleceğe doğrulama
(ufuk dahil) dört yeni konu. Dört statik QML bağı ve model.time-series capability
yardımı; yeni try_action yok. Açık resample/toplam/ortalama, IANA/DST/gap, geçmiş
koşulu/baseline, final defteri ve MAPE/aralık sınırları çevrimdışı paketlidir.
[ADR-024](adr/024-time-series-phase21.md).


Faz22 katalog30/144 makale: text-tokens/language/tfidf/similarity; token/n-gram,
stopword ve dil/Unicode, eğitim fold'unda TF-IDF vocab, benzerliğin anlamı.
Beş QML yardım bağı, text.inspect capability ve Modelleme Öğren ağacı; yeni
try_action yok. Yerel örnekler/sınırlar ve sensitivity/preview kaydı açıklanır.
[ADR-025](adr/025-local-text-phase22.md).


## Faz23

Katalog31/toplam147: workflow-recipe (şema/rol ve atomic dry-run), workflow-drift (tam dağılım/örneklem etkisi/hedef eşleme), workflow-model (apply/retrain farkı). İzleme ağacı/capability/QML bağları; yeni try_action yok. [ADR-026](adr/026-recipes-monitoring-phase23.md), [kanıt](evidence/PHASE23.md).


## Faz24

Katalog32,147 makale/102 sözlük; model-preparation ve tasks yardımı maliyetin yaklaşık oluşunu, bellek fit/özellik daraltma/açık örneklem, belirsiz ilerleme ve kaynak paylaşımı/iptal farklarını anlatır. Yeni try_action yok. [ADR-027](adr/027-performance-phase24.md), [kanıt](evidence/PHASE24.md).

Faz25: katalog34,147 makale; erişilebilirlik/görünüm bağları ve mevcut kritik
açıklamalarda fingerprint/fold/fit/vocab/ddof/scope jargonunun sade anlatımı.
`check_usability.py` yapısal alan/ortak kontrol/temel İngilizce denetimi;
bilimsel kesinlik ve jargon adayları otomatik başarı sayılmaz, manuel okunur.
Gelişmiş görünüm açık yardım makalesini korur. [Gerçek denetim](evidence/PHASE25.md).

Faz26 katalog35: mevcut projects/project.recovery bağında adı/zamanı/sayıları
incelenen kurtarma ve commit değişimi/manuel Kaydet ayrımı açıklanır. Yeni
analitik capability/deneme yok. Temel İngilizce189 mesaj; Türkçe varsayılan.
[Gerçek kapsam](evidence/PHASE26.md).


2026-10-10 kullanıcı veri inceleme düzenlemesi: kapalı başlıklar, gerçek tüm-sütun tablosu, sayfalı unique, describe ve not sözlüğü. Öğren Veri aşamasına dört çevrimdışı konu eklendi (katalog36/151 makale). [Gerçek kapsam](evidence/UI_DATA_INSPECTION.md); Faz27 durdurulmuş olarak kalır.


2026-10-10 sade aktarım: katalog37; home/import-csv rehberlerinde numaralı Veri başlıkları, proje yönlendirmesi, temel/Gelişmiş aktarım, sınırlı örnek ve CSV tür koruması anlatıldı. Sayfa sağ üstündeki genel yardım düğmesi kaldırıldı; Öğren ve odaklı F1 bağları korunur. Yeni capability veya faz yoktur.


2026-10-10 katalog38: home/import-csv otomatik türler,20 görünür kayıt ve boş hücre politikasını; inspection-inventory otomatik tam taramayı ve iki sütunlu tabloyu; dataset-profile hesap ayrımını anlatır. Görev açıklama düğmesi kaldırıldı; aktif görevin iptal kontrolündeki F1 aynı çevrimdışı tasks makalesini açar. Yeni capability/analitik faz yoktur. [Kanıt](evidence/UI_DATA_REFINEMENT.md).

2026-10-10: Veri profili yardım metni beş sütun ve algılanan içerik/kayıtlı tür ayrımını açıklar; kayıtlı değer sayımları ve salt okunur tarama korunur. [Kanıt](evidence/UI_PROFILE_TYPES.md).

2026-10-10 son kullanıcı gösterim isteği: profil tablosu ve üst tür özetinde teknik tür adları (Int64/String/Decimal…) kullanılır. İçerik türü hücrede tek başına; farklı fiziksel kayıt türü tooltip içinde açıklanır. Veri dönüşümü yapılmaz. [Güncel kanıt](evidence/UI_PROFILE_TYPE_LABELS.md).

2026-10-10 son saklama talebi önceki içerik türü gösterimini geçersiz kıldı: profil yalnız gerçek physical_type gösterir; aktarımda Int64/Decimal fiziksel olarak saklanır. Titanic mevcut aktif sürümü kullanıcı izniyle mevcut convert operasyonu üzerinden dönüştürüldü; kaynak, satır kimlikleri ve geri alma geçmişi korunur. [Gerçek kayıt](evidence/UI_ACTUAL_STORAGE.md).

2026-10-10 profil tür özeti her fiziksel türü ayrı satırda sayı ve ilgili sütun adlarıyla gösterir: Int64:4 — sütunlar. Uzun adlar sarılır, plain text korunur. Kullanıcının data_info.png referansı gerçekten incelendi. [Kanıt](evidence/UI_PROFILE_TYPE_COLUMNS.md).

2026-10-10 kullanıcı kısa not isteği: Anlam ve notlar ayrı Veri başlığı olmaktan çıktı, profil tablosunun altına sütun seçimi/kısa açıklama/Notu kaydet alanı taşındı. Her sütunun taslağı seçimler arasında korunur; açık kayıt projeyi kalıcı kaydeder. applyDescription mevcut rol/birim/sıra/analiz birimi ve confirmed durumunu korur; yeni not role önerisini onaylamaz. Analitik profil onaylanmamış rolün yerine mevcut öneri politikasını kullanır. Kaynak/snapshot/RowId değişmez. [Kanıt](evidence/UI_PROFILE_NOTES.md).

2026-10-10 sade veri akışı: import Gelişmiş alanı tüm seviye tercihlerinde ve yeniden girişte kapalıdır; kullanıcı tıklayarak açar. Profil not girişinin üstünde yalnız açıklaması olan sütunlar ad/açıklama biçiminde kompakt, plain-text ve220px bounded listede görünür. Verini tanı altında inventory/describe/unique/sütun profili GUI çağrıları sample=false; ilk10.000 seçicileri kaldırıldı, tam veri hesabı ve200 değer görüntü sayfası ayrı tutulur. [Kanıt](evidence/UI_COMPACT_NOTES_FULL_DATA.md).

Faz29 katalog45/152: expert-workspace yöntem seçimi, parametre, taslak/sonuç ve uzman görünüm makalesi; r/rho0,8 ayrı sentetik örneği worker testiyle doğrulanır. Yeni silent-active-data action yok. [Kanıt](evidence/PHASE29.md#e29-learning).

Faz30 katalog46/157: import-phase30, import-partition, import-schema-evolution, import-category-labels, import-decimal-precision; Veri öğrenme yolu, import/F1 ve yeni registry bağları. Aynı gerçek fixture değerlerinden örnekler, yeni otomatik veri eylemi yok. [Kanıt](evidence/PHASE30.md#e30-learning).


Faz31 katalog47/162: bağlantı, bağlı sorgu, snapshot/tutarlılık, API sayfalama
ve kaynak tazeliği için beş çevrimdışı konu. Altı capability ve ConnectorPanel
F1 bağları aynı katalogdadır; credential/network yürütme yardım okumayla
başlamaz. Örnekler sentetik id1/2/3 ve role/snapshot kapsamıyla sınırlıdır.
[Kanıt](evidence/PHASE31.md#e31-learning).


Faz32: katalog48/167 makale; ölçüm düzeyi, veri sözleşmesi, referans bütünlüğü,
fuzzy skor ve yanlış birleşme için beş çevrimdışı konu; altı aynı-registry
capability ve beş F1 bağı. Yardım hesap/onay/yayın başlatmaz. Yeni try_action yok.
[ADR-033](adr/033-data-contracts-phase32.md), [kanıt](evidence/PHASE32.md#e32-learning).


Faz33 katalog49/172 makale;5 yeni konu: missing-assumptions, missing-multiple, sampling-representation, sampling-bias, weights-types. Mevcut model-imputation genişledi. MCAR/MAR/MNAR varsayımdır; tek/çoklu, model kapsamı ve weight semantiği açık. F1/registry bağları; yeni try_action yok. [Gerçek kanıt ve sınırlar](evidence/PHASE33.md).


Faz34: katalog50/176; array-dimensions, array-raster, array-units, array-chunks ve Veri öğrenme yolu. NetCDF/Zarr/HDF5 ve array grafik context bağları; üç gerçek F1/Escape kontrolü her GUI vakasında. Yeni try_action yok. [Kanıt](evidence/PHASE34.md).


Faz35: katalog51/190; 14 yeni grafik/kavram makalesi. Yeni her türün chart.* F1 bağı ve density/ECDF/QQ/SD-SE-CI/log açıklaması var; yeni try_action yok. [Kayıt](evidence/PHASE35.md).


Faz36: katalog52/200; dokuz grafik ve overplotting/boyut sınırı. Koşullu ilişki/Simpson, kategori mesafesi, panel maliyeti, ilk-N örnek ve seçim kapsamı; gerçek F1 bağı. [Kayıt](evidence/PHASE36.md).


Faz37: katalog53/221;17grafik ve4payda/hiyerarşi-akış/alan/doublecounting konusu. Her tür inputşeması ve F1bağı; yeni try_action yok. [Kayıt](evidence/PHASE37.md).


Faz38: katalog54/231; CRS, projection, join, MAUP, spatial leakage, repair, raster, classification, neighborhood weights ve online terms/cache için10 çevrimdışı konu. Mevcut registry/F1 bağları; yardım ağ veya veri değişikliği başlatmaz. [Kanıt](evidence/PHASE38.md).

Faz39 dört çevrimdışı makale/bağ ekler: `dashboard-question` → `dashboard.canvas`, `dashboard-filter-scope` → `dashboard.filters`, `dashboard-kpi` → `dashboard.kpi`, `figure-readable` → `figure.compose`. Dashboard sorusu, sürüme bağlı filtre/anahtar seçimi, KPI payda/dönem ayrımı, okunabilir subplot/legend/font ve statik/yerel HTML export sınırı anlatılır. F1/Escape ve odağa dönüş gerçek QML testindedir. Katalog version55;235 makale/140 bağ; [kanıt](evidence/PHASE39.md).

## Faz40 çevrimdışı katkı

Katalog56/toplam244 makale: statistical-models +sekiz yöntem. Inference/prediction,
link/offset/interaction/random effect/residual; varsayımlar/baseline/SE-cluster/
convergence/save ve AIC-BIC bağlamı.142 statik UI bağı; her model yöntemi dinamik
yardım bağında ayrıca gerçek QML düğmesi/Escape ile doğrulanır. Yeni try_action
yok. [Gerçek kayıt](evidence/PHASE40.md).

## Faz41 çevrimdışı katkı

Katalog57/toplam254 makale: resampling +dokuz yöntem. Sampling unit,
exchangeability/symmetry/null/tail/MC,percentile/BCa uygunluğu,robust ölçü,
FWER/FDR,aile seçimi,missing-delta sensitivity ve p-hacking.144 statik UI bağı;
yöntem dinamik yardımları gerçek QML düğmesi/Escape ile sınanır. Yeni try_action
yok. [Gerçek kayıt](evidence/PHASE41.md).


## Faz42 çevrimdışı katkı

Katalog58/toplam264 makale: measurement/randomization/MDE-power/stopping/failed measurement ve5 yöntem; ITT/PP, SRM/attrition, denominator/CI ve sequential sınırları.145 statik UI bağı/534 named field; yöntem dinamik help gerçek düğme/Escape ile doğrulanır. Yeni try_action yok. [Kayıt](evidence/PHASE42.md).


Faz43 katalog59/273;9 çevrimdışı Bayes/prior/posterior/interval/MCMC/predictive/LOO-WAIC/sensitivity konu;147 statik binding,557 named field. BayesPanel ve4capability aynı registry/F1; yeni try_action yok. [ADR044](adr/044-bayes-phase43.md).

## Faz44 katkısı

Katalog60/282: association/causation, DAG/identification,ATE,adjustment,IPW,AIPW,cross-fitting,matching,DiD,IV ve sensitivity için dokuz makale; gerçek panel F1/Escape ve yöntem help. Yeni try_action yok. Tanımlama gerekçeleri kanıt değildir; CI/estimand sınırı her yöntemde görünür. [ADR045](adr/045-causal-phase44.md).

## Faz45 katkısı

Katalog61/291;9sağkalımmakalesi:censored/riskset/KM/logrank/hazard/PH/AFT/CIF/entry/metrics/prediction, gerçekformF1/Escape. Unsupportedbackendkapalı,HarrellCapparenttraining veIPCWsınırıaçık. Yeni try_actionyok. [ADR046](adr/046-survival-phase45.md).

## Faz46 katkısı

Katalog62/308:17makale latentpurpose,12method,loading/sparse/selectionleakage/stability. Gerçekpurpose/scaling/fit/CV/reuseformF1/Escape,monochromeembeddingnotclass. OptionalUMAPunvalidated/noEV;newtry_actionyok. [ADR047](adr/047-dimensions-phase46.md).


Faz47 katalog63/313: exploration,density,soft membership,novelty,stability için
beş çevrimdışı konu; yeni model capability bağları ve gerçek QML yardım/Escape.
Yeni try_action yok. [ADR048](adr/048-exploration-phase47.md).


Faz48 katalog64/336:23model family/regularization/boosting/kernel/bias-variance/
ensemble konu. Same validation plan/explicit family,OOF preprocessing,native
categorical/NaN,safe persistence/optional absence sınırları. Yeni try_action yok.
[ADR049](adr/049-model-families-phase48.md).

Faz49 katalog65/348:12hyperparameter/grid/random/optionalTPE/nestedCV/trial/
validationoverfit/budget/curve/stopping-pruning/resume konu.159statikhelpbinding;
F1/Escape gerçek GUI. New try_action yok;finaltestdefter ve optionalavailability
sınırları görünür. [ADR050](adr/050-hyperparameter-search-phase49.md).

Faz50 içerik66/toplam352: mevcut model-uncertainty makalesi genişletildi;
probability/reliability/Brier, validation decision cost, conformal coverage/sets,
CI-vs-predictive/quantile için dört yeni makale. Altı registry context, F1/Escape,
aynı offline plain-text renderer; try_action eklenmedi. Split/label/n, isotonic
small-n, unseen/absent class, coverage/width/set size ve subgroup/future
exchangeability sınırı örneklerle açık. [Kanıt](evidence/PHASE50.md).

Faz51 içerik67/toplam357: beş explanation/causation, correlated/background,
subgroup/small-n/multiple-search, fairness trade-off ve constrained/what-if
makalesi. Nine capability contexts/F1/Escape; same offline plain-text renderer,
no executable try_action. Sensitive export/no-anonymity, mapping/n/budget,
optional unavailable ve unsupportedlocal açıklamaları görünür. [Kanıt](evidence/PHASE51.md).

Faz52 DEC52-01: mevcut run/test defteri üzerinde yerel registry; bounded native yol ve sınırlar [kanıt](evidence/PHASE52.md). Optional tracking unconfigured/notvalidated; fiziksel silme kapalı, arşiv disk boşaltmaz.

Faz53 DEC53-01 native temporal slice:19 capabilities,chronological/panel/availability/MASE/proper forecast scores, safeJSON/journal;[kanıt](evidence/PHASE53.md). Formal prior gates separate; bounded templates/out-of-source prediction limitations explicit.

Faz54 DEC54-01 regular signal ve recording blok pencereleri:13 bounded native template teknik doğrulandı; resmî kabul ayrı. Offline zero-phase, amplitude/PSD/availability ve kaynak kimliği açık. [Kanıt](evidence/PHASE54.md);Faz55 yetkisi yok.

Faz55 DEC55-01 bounded native NLP:12 bounded native records teknik doğrulandı; resmî kabul ayrı; transformer/spaCy/ONNX unsupported. Static/literal/linear limits, original offset ve versioned human review açık. [Kanıt](evidence/PHASE55.md);Faz56 yetkisi yok.

Faz56: üç yeni çevrimdışı makale: tensor/epoch/batch/loss/gradient/lr/overfitting;
tam optimizer/scheduler/RNG resume; açık CNN NCHW şema ve train-only augmentation.
Aynı seed farklı cihazda garanti değildir; validation seçimi final inference değildir.
Mevcut learning taxonomy ve capability/F1 bağları; yeni try_action yok.
[Gerçek kanıt](evidence/PHASE56.md).

## Faz59

Üç yeni çevrimdışı makale: recommendation-feedback/evaluation/cold-start; toplam385.
Dört native capability ve gerçek QML yardım yolu; try_action yok.
[Kanıt](evidence/PHASE59.md),[ADR060](adr/060-recommendation-phase59.md).

## Faz60

Üç yeni makale: pattern-support/retention/trace;388 toplam,179UI binding.
Native6capability, gerçek yardım; try_action yok. [Kanıt](evidence/PHASE60.md).

## Faz61

Üç çevrimdışı makale graph-structure/measures/leakage;391article/181UIbinding.
Altı hesap+iki source capability, gerçek GUI yardım; try_action eklenmedi.
[Kanıt](evidence/PHASE61.md).

Faz62 DEC62-01 açık talimatla bounded local replay, incremental scaler/SGD, prequential/checkpoint ve ayrı özel hedefler; [kapsam/kanıt](evidence/PHASE62.md), [ADR063](adr/063-streams-phase62.md). PU/broker unavailable; default2GiB GUI kapısı açık,4GiB işlevsel test ayrı. Resmî kabul sürüyor/deneysel/isteğe bağlı; Faz63 başlatılmaz.

Faz63 DEC63-01: sınırlı numeric GUI profile Python/SQLite/notebook reference-only export ve explicit fresh Python process; [kanıt](evidence/PHASE63.md),[ADR064](adr/064-code-bridge-phase63.md). OS sandbox/managed Jupyter yok; resmî sürüyor/deneysel/isteğe bağlı, önceki kapılar korunur. Faz64 başlatılmaz.

Faz64: katalog içerik80/toplam400 makale; workflow-dag/cache/batch. Typed port, cycle/dependency, verified cache ve geçmiş zaman, bounded retry/idempotency, açık batch eşleme/dry-run ve schedule unavailable sınırları. workflow.* capability/UI yardım bağları; yeni try_action yok. [Kanıt](evidence/PHASE64.md).

Faz65 içerik81/toplam405: repro-lineage/snapshot/environment/tolerance/record. Kayıtlı köken ve legacy gaps, RowId/multi-source sınırı, reference/snapshot/retention, ortam/backend safe failure, yöntem/dtype bazında tolerance ve araştırma kaydı. Üç repro capability ve GUI bağları, yeni try_action yok. [Kanıt](evidence/PHASE65.md).

Faz66: içerik82/toplam406, compute-resources; thread/process, native oversubscription,
lazy/out-of-core/sparse, GPU transfer ve distributed retry maliyeti. compute.resources
panel/F1 ve compute.dask-summary capability bağı; yeni try_action yok. Remote/GPU
unavailable sınırı açık; yardım iş başlatmaz. [Kanıt](evidence/PHASE66.md).

Faz67 içerik83/toplam407: model-monitoring; data/concept drift farkı, delayed labels,
shadow ve alarm threshold; PSI/bin/smoothing, KS/büyük n/çoklu alarm, Brier/reliability
sınırları. model.monitor.batch/route/cli/api context; aynı gerçek monitoring formu,
API/CLI ayrı açık terminal eylemi; yeni try_action yok. [Kanıt](evidence/PHASE67.md).


Faz68: content84/408makale; scenario-simulation, altı scenario.* capability ve gerçek formun F1 bağları. Seed/draw/correlation, parameter/measurement/MCerror, marjinal sensitivity, objective/constraint/units/status ve feasible/uygulanabilir ayrımı. Yeni try_action yok; [kanıt](evidence/PHASE68.md).


Faz69: içerik85/409makale; LessonCatalog/v1 content1/10ders/8yol. Her derste amaç/veri/problem/varsayım/adım/beklenen/yanlış yorum/kendi veri/günlük örnek/denklem/review; advisory DAG/optional self-check.403capability coverage:10interactive,393article-linked; yeni modül eklenmesi manifest kapısını gerektirir. Mevcut learning-marks şema1→2 read migration; yazım explicit opt-in versioned lesson mark, opt-out atomik temizler. Teknik referans review bağımsız bilimsel/eğitimci review değildir. [Sözleşme](adr/070-learning-laboratory-phase69.md), [kanıt](evidence/PHASE69.md).


Faz70 content86/toplam410makale; scientific-report: bilimsel rapor, caption, limitations, bulgu/yorum, exploratory/confirmatory, test history ve redaction sınırları. report.builder/F1 gerçek GUI bağı; try_action yok.404module coverage (10interactive/394article-linked). [Kanıt](evidence/PHASE70.md).


Faz71 içerik87/toplam411makale; review-sharing: review/diff/redaction/paylaşım, native identity, single-writer ve no-merge sınırı. Dört share.* context/F1, yeni try_action yok.408module coverage (10interactive/398article-linked). [Kanıt](evidence/PHASE71.md).

Faz72: içerik88/412makale, privacy-governance; PII aday/insan kararı, pseudonym ile
anonimlik farkı, linkage/frequency, key loss/threat model, retention/silme kapsamı,
DP sensitivity/accountant yokluğu. privacy.scan/review/export/retention bağları;
412capability coverage10interactive/402article-linked, yeni try_action yok.
Kaynaklar resmi Fernet/Secret Service; [E72](evidence/PHASE72.md). Otomatik içerik
kapısı uzman/hukuk incelemesi sayılmaz.

Faz73: içerik89/413makale; plugins-sdk, plugin.sdk/F1/Escape bağı. Eklenti yeteneği,
trusted code, eksik/version uyuşmayan bağımlılık, same-user process'in OS sandbox
olmaması ve permissions disclosure sınırı. Kayıtlı learning snapshot PlainText;
çekirdek makale/try_action code'dan otomatik kurulmaz.413capability coverage
10interactive/403article-linked. [E73](evidence/PHASE73.md); otomatik içerik kapısı
pluginin bilimsel yöntemini/uzman doğruluğunu doğrulamış sayılmaz.

Faz75: içerik version90/414article+10lesson değişmedi. Hash/version-bound
`phase75/learning-review.json` +expert-review-worksheet.csv bağımsız uzman review'u
için hazırlanır; pending durumları teknik doğruluk/AI üretimi nedeniyle approved
olmaz. Reviewer/tarih/karar/kanıt ve checklist [protokolde](RELEASE_REVIEW_PROTOCOL.md).
Dolu insan worksheet'i generator tarafından ezilmez. Uzman veya pedagojik bilimsel
onay bu fazda gerçekleştirilmedi; offline lesson/link hesap kontrolleri ayrıdır.

## UI/UX yenileme içerik güncellemesi

2026-10-17 katalog91: home10 ve dataset-profile4 güncel tema/ölçek, görünür yardım,
proje konumu, sütun boyutlandırma ve yalnız görünen kayıtları kopyalama davranışını
anlatır.414article kimliği korunur. Faz75 uzman inceleme çalışma sayfası katalog90
hash'leriyle tarihsel kayıttır; değişen iki makale yeniden uzman review bekler.
Bu teknik metin düzeltmesi uzman bilimsel onay değildir. [Kanıt](evidence/UI_RENEWAL.md).

## Başlangıç yolculuğu revizyonu

2026-10-17 katalog92/home11: başlangıç ana haritası→proje sırası, Öğren'deki aynı
harita ve çalışma ekranından kavram açma, explicit gelişmiş sunum farkı.414kimlik
korundu. Kaynak ve hesaplar değişmedi; uzman review durumu pending kalır.
[Kanıt](evidence/UI_JOURNEY.md).
