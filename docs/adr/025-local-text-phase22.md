# ADR-025 — yerel, açıklanabilir metin

2026-10-09, açık Faz22; Linux/Python/PySide6/QML, kaynak prompt/veri korunur.
Yeni bağımlılık/ağ API/embedding/model indirme yok. Model → Yerel metin incelemesi;
normal sınıflandırma hazırlığına tek String metin TF-IDF seçeneği eklenir.

`analytics/text.py` Qt'siz hesap, `TextSpec/v1`, `TextRun/v1`, `TextPreparation`.
Yerel spawn ve mevcut bütçe/iptal/eskimiş binding, atomik `storage/text_store.py`
özet kaydı. Proje şema7'ye isteğe bağlı sonuç alanı; eski veriyi yeniden yazmaz.

Dil Türkçe varsayılan; kullanıcı İngilizce/diğer-karışık seçebilir. Otomatik dil
algılama yok. Unicode NFC veya açık NFKC; isteğe bağlı casefold. Türkçede NFC
sonrası I→ı/İ→i ve Unicode casefold; genel/İngilizce İ→i+birleşen nokta.
Casefold ß/ligatür gibi karakterleri de genişletebilir; aksan silme/kök bulma yok.
Unicode kategori L/M (seçilirse N) token, diğer karakter ayırıcı. N-gram1–3;
durak sözcük çıkarıldıktan sonra yeni komşuluk oluşabilir. Küçük, proje tarafından
yazılan Türkçe15/İngilizce12 listeler ve açık özel stopword; tam dil sözlüğü değil.

Null, boş string, whitespace ve temizlendikten sonra token kalmayan belge ayrı.
Ham uzunluk Unicode kod noktası; bayt/grapheme sayısı değil. Boş kolon incelemesi
skorsuz/vocab0 olarak geçerlidir; tümü boş eğitim fold'unda sınıflandırma reddi.
Frekans/doc-frequency en yüksek100 tablo ve15 terim grafik; vocab ayarı1–10000,
frekans+Unicode tie sırası ile açık daraltma. Aday50000, üretilen n-gram5m,
seyrek matrix nnz5m,100000 belge, belge10000 karakter/3000 token, toplam10m
karakter. Kontrollü ret/128 belge ilerleme/parent force-cancel; sessiz örneklem yok.

TF ham frekans; smooth IDF=1+log((1+N)/(1+df)); L2 belge normu. Betimsel inceleme
vocab seçili bütün kolondan gelir ve sınıflandırmaya asla taşınmaz. Mevcut
PreparationSpec'e opsiyonel `text`; tek metin feature, ayrı mevcut kategori target.
`TextPreparation` sklearn Pipeline prepare adımıdır: her fit yalnız o fold'un
train belgelerinden vocab ve IDF öğrenir, RowId/öğrenilen parametre kapsamını
kaydeder. Validation/test yalnız frozen transform; bilinmeyen token yok sayılır,
boş belge sıfır sparse vektör. Mevcut classifier/baseline/CV/eşik/final kullanım
journal protokolü aynıdır; otomatik anlam/duygu/konu veya target üretilmez.

Metin custom-transformer güvenli model paket izin listesinde yoktur. Bu faz
unsafe pickle/skops trust eklemek yerine açık `model_package_unavailable`
bildirir; metin sınıflandırması değerlendirme sonuçlarını saklar fakat güvenli
model paketi/yeni dosya tahmini desteklenmez. Diğer ailelerin paketleri korunur.

Kosinüs ayrı opt-in seçenektir: ≤1000 belgenin tüm sparse çiftleri, en yüksek30
pozitif çift ve gerçek RowId'ler. Boş belgede pozitif benzerlik yok; ortak kelime
anlamsal eşdeğerlik veya etiket değildir. Etiketsiz otomatik gruplama seçilmedi;
isteğe bağlı temel benzerlik gerçek hesapla sunulur.

Ham önce/sonra preview varsayılan kapalı; açık onayla ilk5 ×200 karakter/token30
sadece sonuç belleğinde. `text_store.publish` ham preview'ları atomik kayıt öncesi
çıkarır; load onları getiremez. Kaynak snapshot'ın kullanıcı verisini yerel
saklaması ile ham preview loglama ayrı davranıştır. Frekans/vocab terimleri
analiz çıktısıdır; özel yerel proje metadata/artifact içinde saklanabilir, loglarda
yazılmaz. Error/progress genel ve içeriksizdir; worker traceback/document basmaz.

Resmî sklearn1.9.1 API 2026-10-09 canlı açıldı:
[TF-IDF API](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html),
[feature extraction](https://scikit-learn.org/stable/modules/feature_extraction.html).
Callable analyzer n-gram/stopword işlemini kendisi yürütür; sklearn default
İngilizce lower/token_pattern kullanılmaz. Fit/transform ve sparse yol kurulu
kilitli API ile gerçek çalıştırılır. Yeni lisans/indirme gerektirmez.

[Gerçek kabul](../evidence/PHASE22.md). Önceki insan/bağımlılık kabulü açık:
sürüyor/deneysel/zorunlu. Faz23 başlamaz.
