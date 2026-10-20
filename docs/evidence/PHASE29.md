# Faz 29 — registry ve uzman çalışma alanı

2026-10-10; ENV-29: mevcut kilitli CPython3.13.15/PySide6 6.11.2 Linux geliştirici ortamı; Qt offscreen/software. Kullanıcı “faz 29 bitir önce” talimatı DEC-29-01: yalnız Faz29 teknik geliştirme istisnası, DEP-28-02..05 kabulleri açık. Faz30 başlamadı. Yeni model/bağımlılık/proje şeması yok.

<a id="e29-registry"></a>
## Tek kayıt ve kademeli bağlama

`domain/contracts.py` mevcut Capability üstüne contract_version=2, InputSchema/InputRole/Parameter/MethodSupport/LearningLink/ResultArtifact eklendi. ComputeBudget ve Provenance çoğaltılmadı. `domain/capabilities.py` aynı CAPABILITIES kaydını genişletir; ikinci kayıt yok. Eski supports tuple ve version/semantic_version=1 davranışı korunur. Unknown/unsupported/conditional/supported ayrı. Kütüphane adı uygulama desteği sayılmaz.

11 mevcut istatistik yöntemi gerçek AnalysisSpec/v1 alanlarına, giriş rollerine/dtypes, varsayımlara, maliyet ve dependency kontrolüne bağlıdır. İstatistikte fit/predict/proba/transform/prediction interval yok; güvenli atomik persist var. Frequentist CI prediction interval değildir. Missing complete-case; weights/time/sparse yok. Integer/Decimal Float64 dönüşümü eski açık izin/ret önkontrolünü korur. Diğer mevcut yöntemler eski kayıtları ve açık bilinmeyen ayrıntıları taşır; yeni ayrıntı desteği uydurulmaz. Mevcut aileleri tek oturumda yeniden yazmak bu fazın kademeli bağlama şartına aykırıdır.

StatisticsController.methods/create aynı registry'den seçer ve mevcut AnalysisSpec doğrulaması/spawn/iptal/kaynak gözetimini kullanır. Eksik bağımlılık bildirimi yerel doğrulanmış ortamı etkinleştirmeyi açıklar; shell/download/install çalıştırmaz.

<a id="e29-workspace"></a>
## Gerçek GUI ve kalıcılık

`ui/workspace.py`, `ModuleDiscovery.qml`, `ResultPanel.qml`, `Main.qml`, `StatisticsPanel.qml`: Ctrl+K komut paleti, Türkçe amaç/yöntem araması, favoriler, kayıtlı sonuç sekmeleri, iki sonuç karşılaştırması, adlandırılan istatistik parametre presetleri. Registry ayrıntılarına erişim mevcut. Uzman görünümü seçenekleri açar; başlangıç ekranına keşif listesi yığılmaz. Ortak panel aynı result_version kimliğini başlangıç/uzman görünümünde okur. Metin, gerçek parametre satır tablosu, hash denetimli kayıtlı PNG, model metadata ve log/uyarı artifact'ları ortak render sözleşmesindedir. Model artifact görünümü kod/pickle yüklemez.

Tercihler mevcut ProjectController.config XDG alanında project_id hash'iyle `expert-workspace-*.json`, workspace schema1, 0600/QSaveFile atomik kayıt. En fazla24 sekme/20 preset/18kB; sonuçlar kopyalanmaz, kalıcı sekme yalnız yayımlanmış result_version referansıdır. Eski workspace şeması0 boş tercihten açık ilk kayıtta1'e geçer; eski/future/bozuk dosya salt okunur korunur. Proje manifest7 ve verisi değişmez; proje migration gerekmiyor. **Bu tercihler makineye yereldir; proje export/farklı makine taşıma kapsamında değildir.** Var olan proje commit/migration yedekleri korunur.

Preset uygulamak yalnız taslağı değiştirir, eski varsayım onayını taşımayıp önkontrolü geçersiz kılar. Yeni çalışma açık önkontrol/onay/çalıştırma gerektirir ve yeni run üretir. Kayıtlı iki sonuç farklı veri/filtre/kapsam taşıyorsa kıyas uyarısı gösterilir; otomatik en iyi yöntem veya nedensellik iddiası yok. Uyarı, veri sürümü, filtre, seed, kapsam, yöntem ve parametre sürümü daima görünür; ortam isteğe bağlıdır. Eski kayıttaki eksik bilgi “Eski kayıtta yok” kalır.

<a id="e29-compatibility"></a>
## Uyumluluk

`result_compatibility`: eski bilinen yöntem/parametre v1 → compatible; bilinmeyen capability veya uyumsuz sürüm → readonly. Sessiz parametre göçü/yeniden hesaplama yok; yeni tarifi açıkça oluşturmak gerekir. Bilinen AnalysisResult/v1 içerik doğrulaması, dataset bağları, p, yöntem/spec ve artifact doğrulaması korunur; kayıt ismindeki bilinmeyen capability ortak panelde readonly okunabilir. Bilinmeyen gelecekteki proje veya artifact içerik şeması güvenlik doğrulamasını atlamaz; mevcut kontrollü ret sürer. Bozuk metadata okunabilir gelecek sonuç diye kabul edilmez.

<a id="e29-learning"></a>
## Çevrimdışı yardım

Katalog45/152 makale: expert-workspace; yöntem seçimi, parametre/preset, taslak/sonuç ayrımı, uzman görünüm ve ayrı sentetik ilişki örneği. Pearson/Spearman mevcut yardım bağları korunur. Elle hesaplanmış r/rho=0,8 örneği gerçek worker testindedir. Yardım aktif veri üstünde işlem yapmaz; örnek ayrı proje talimatı ve mevcut sandbox öğrenme akışıdır. Yeni serbest çalıştırma allowlist'i eklenmedi.

<a id="e29-tests"></a>
## Gerçek kontroller

Çalıştırmalar `phase29/checks.json` ve pytest JUnit/log içinde kaydedilir. Headless geliştirici GUI kanıtı insan/AT/minimum fiziksel donanım/remote CI kabulü değildir. Önceki açık kapılar kapanmış sayılmaz.

İlk özel GUI denemesi mevcut Main ScrollView `workspace` id'siyle yeni context property'sinin çakışmasını yakaladı; context `expertWorkspace` olarak düzeltildi. Dinamik delegate seçimi gerçek childItems yoluyla test edilir. İlk kalıcılık denemesi varsayılan projede UI state alanı olmadığını yakaladı; proje şemasına alan eklemek yerine yerel UI tercihleri kullanıldı. Başarısız denemeler başarı diye sunulmaz.

<a id="e29-limits"></a>
## Sınırlar ve masaüstü deneme adımları

1. Proje aç, iki sayısal sütunlu sentetik veriyi aktar. Ctrl+K → Pearson/Spearman; seçim Karşılaştır ekranına gider.
2. Soru, sütun, ölçüm/gözlem birimi ve onayları doldur; Önkontrol → varsayımları onayla → Çalıştır → Kaydet.
3. Uzman görünümü aç; sonuç sekmesini/favoriyi/preseti kaydet. İkinci parametreyle yeniden çalıştır; iki sonucu karşılaştır.
4. Başlangıç görünümüne dön; aynı sonuç kimliğini doğrula. Projeyi kapat/aç; kayıtlı sekme ve preset geri gelsin. Preseti seçmek hesap başlatmamalı.
5. Öğren’de uzman çalışma alanını ara; kaynak projede otomatik değişiklik olmamalı.

Faz29 teknik teslimi önceki insan/AT/donanım/dağıtım kabulünü tamamlamaz. Yeni fiziksel masaüstü denemesi henüz yapılmadı. Ayrıntılı destek beyanı kademeli olarak11 istatistik yönteminde; diğer legacy yöntemlerde bilinmeyenler açık. Preset form geri yükleme yalnız mevcut istatistik adaptörlerinde; diğer spec aileleri mevcut formlarıyla çalışır. Yerel çalışma alanı tercihleri taşınabilir proje exportuna dahil değil.

<a id="e29-continuation"></a>
## Devam doğrulaması ve dar pencere düzeltmesi

2026-10-10; ENV-29-CONTINUATION; F29-S001..006 ve F29-P001..008 mevcut
teknik kapsamı. [Gerçek ortam](phase29/continuation/environment.json),
[komut/tarih/exit kayıtları](phase29/continuation/checks.json).
Faz30 başlatılmadı; önceki insan/AT/donanım/dağıtım kabulü açık kalır.

`ModuleDiscovery.qml` dar720px pencerede modül düğmesinin asgari genişliği
nedeniyle Ayrıntı düğmesini kesiyordu. ScrollView içerik genişliği kullanılabilir
alana bağlandı; modül adı satır sarar, eksik bağımlılık gerekçesi ayrı satırdadır.
[Önce](phase29/continuation/gui/expert-narrow.png) ve
[düzeltmeden sonra](phase29/continuation/gui-fixed/expert-narrow.png) gerçek
Qt görüntüleri incelendi. Kaynak ve kurulu wheel üzerinde iki yöntem,
Ctrl+K, farklı sonuç kimlikleri, sekme/preset save/reopen ve kaynak SHA256
koruması yeniden geçti. [Kaynak denemesi](phase29/continuation/gui-fixed/walkthrough.json),
[kurulu wheel denemesi](phase29/continuation/wheel-gui/walkthrough.json).

Kilitli dev offline sync, check_docs/artifacts/learning/usability, Ruff check/format,
14 kilitli unittest ve izole XDG giriş smoke geçti. Sistem Python3.14
unittest discovery74/60 import hatasıyla başarısız; kilitli bağımlılıklar sistem
Python'una kurulmadı. İzolesiz ilk entry smoke exit2 oldu; izole XDG tekrarında
GUI_SMOKE PASS. İlk deneme başarı sayılmaz, kullanıcı tercihleri değiştirilmedi.

İzole build cache'inde hatchling bulunmadığı için ilk offline wheel build
başarısız oldu. Mevcut kilitli dev build bağımlılıklarıyla
`uv build --wheel --offline --no-build-isolation` geçti. Wheel ayrı `/tmp`
hedefine noneditable kuruldu; runtime bağımlılıkları mevcut kilitli ortamdan
kullanıldı. Kurulu GUI/CSV import-reopen/entry smoke geçti;
[208 paket dosyası](phase29/continuation/wheel-integrity.json) kaynak, wheel ve
kurulu hedefte byte düzeyinde eşleşti. Temiz dağıtım hedefi kabulü değildir.

Tam pytest regresyonu724 başarılı,335.31s: [çıktı](phase29/continuation/pytest.txt)
ve [JUnit](phase29/continuation/pytest.xml). Koşu sırasında yapılan QML
düzeltmesi ayrıca kaynak ve kurulu wheel GUI tekrarlarıyla doğrulandı.
Bu sonuçlar yeni fiziksel masaüstü/AT/remote CI kabulü değildir.
