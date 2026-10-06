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
