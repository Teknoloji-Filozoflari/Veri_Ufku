# Faz03 — çevrimdışı yardım uygulama kanıtı

Tarih: 2026-10-06. Kapsam yalnız Faz03; Faz04 ve sonraki fazlar başlatılmadı. Kaynak birleşik prompt korunur. Olgunluk deneysel; otomatik, masaüstü ve kullanıcı kanıtları ayrı tutulur.

<a id="e03-environment"></a>

## Ortam ve yöntem

ENV-03-HEADLESS: Linux7.2.9-1-cachyos x86_64/glibc2.44, CPython3.13.15, PySide6/Qt6.11.2; offscreen/software; geçici izole XDG. ENV-03-DESKTOP: aynı makine/kilit, gerçek Wayland/software masaüstü bağlantısı. Makine/disk kaydı [ENVIRONMENT](../ENVIRONMENT.md). Kilit SHA256: 0dd1307806957482d1a4c531837750f879d235f909d46a24ed5e698caf59068c. İçerik hash'i JSON kayıtlarında; kaynak hash'leri phase03-source.sha256 içinde kayıtlıdır.

[Başsız kayıt](phase03-headless.json), [masaüstü kayıt](phase03-desktop.json). Komut `uv run --frozen python scripts/measure_phase03.py`, masaüstü `--desktop`; ajan GUI izniyle gerçek masaüstünde çalıştırdı. Betik Python bağlantı/urlopen çağrılarını fail-fast engeller. Paket PlainText render ile Qt Network/WebEngine veya uzak resim isteği içermez. İnternetsiz yardım arama/render yolu bu sınırla doğrulanır; işletim sistemi ağ arayüzü fiziksel olarak kapatılmadı. Çevrimdışı kurulum veya bütün platform kabulü değildir.

<a id="e03-schema"></a>

## F03-S001/S002 — sürümlü içerik ve güvenli render

Gerçek katalog `src/veri_ufku/learning/content/tr.json`: şema1, katalog ve makale içerik sürümleri, Türkçe 13 makale; her istenen alan, küçük önce/sonra, yorum, sık hata, ilgili kavram/ekran/işlem ve kaynaklar mevcut. `learning/catalog.py` Qt/analitik bağımsız okuyucu ve şema doğrulayıcıdır. [İçerik sözleşmesi](../LEARNING_CONTENT.md).

`tests/test_learning.py` eksik/bozuk kavram ve ekran bağını, çift kimliği, bilinmeyen şemayı, HTML blok türünü, javascript kaynak şemasını ve uygulanmayan deneme eylemini reddeder. `tests/test_learning_gui.py::test_article_markup_is_rendered_as_plain_text` HTML/img/script görünümündeki gerçek label metninin QML Text.PlainText olduğunu sorgular; HTML/JavaScript/resim çalıştırılmaz. UI dosyası `ArticleView.qml`; içerik hiçbir eval, komut veya serbest QML blok alanı taşımaz.

<a id="e03-depth"></a>

## F03-S003 — derinlik ve bağımsız örnek

Gerçek QML bilgi panelinde Tek cümle, Bir dakikalık örnek ve Ayrıntılı rehber seçicisi var. Tek cümle özet/kritik uyarı; örnek önce/sonra/yorum; rehber uygunluk/sık hata/bloklar/kaynaklar gösterir. Makale/ilgili kavram seçimi alanı veya işi değiştirmez. F1/aynı yardım düğmesiyle isteğe bağlı açılır; Escape/kapat odağı geri verir. `test_offline_qml_search_context_depth_critical_close_and_example_isolation` gerçek nav/arama/ilgili kavram/derinlik/widget girdilerini denetler, aktif işin aynı kimlik/binding ile sürdüğünü ve geçerli sonuç ürettiğini doğrular.

Uygulamada dene yalnız `learn.example → learn.search` gerçek özelliğine bağlanır. Ayrı ExampleWindow'da bağımsız LearningController ile geçici örnek öğrenme projesi açılır; ana query/kategori/makale/iş/binding ve dosyalar değiştirilmez. Örnek okuma kaydı kapalıdır. Test ayrı state'i, diske yazmama ve uygulanmayan model makalesinden eylem yürütmeme sınırını denetler. Gerçek veri projesi deposu/import/analitik bu fazda uygulanmaz; bu nedenle analitik makalelerde deneme eylemi sunulmaz.

<a id="e03-center"></a>

## F03-S004 — Öğren merkezi ve Türkçe içerik

Gerçek LearningCenter: çevrimdışı Türkçe normalize arama (MEDYAN, SIZINTI), kategori, dokuz temel kavram sözlüğü, bulunamadı durumu ve isteğe bağlı okundu/yer imi işaretleri. Başlangıç dokuz konu Veri nedir, satır/sütun, veri türü, eksik değer, ortalama/medyan, örneklem, korelasyon, tahmin ve veri sızıntısıdır. Dört ek rehber başlangıç, görev, paylaşım ve yardımı açıklar. Açıklamalar özgün günlük Türkçe; korelasyon nedensellik değildir, tahmin kesin değildir, örneklem bütün veri diye sunulmaz. NIST ve scikit-learn kaynak sayfaları geliştirme sırasında incelendi; kaynak URL/tarihleri içeriktedir, çalışma sırasında indirilmez.

Elle editoryal fixture: [10,20,90] ortalama40, medyan20; çift örnek [10,20,30,40] medyan25. Öğretim metni motor çıktısı gibi sunulmaz. Metinlerin eğitim etkisi/bilimsel uzman incelemesi bu otomatik fixture testiyle tamamlanmış sayılmaz.

Yerel kayıt varsayılan kapalı; makale okumak otomatik geçmiş yazmaz. Kullanıcı açıp işaretlerse QSaveFile/direct-write-fallback kapalı/0600 ile yalnız makale kimlikleri yazılır. Test gerçek yeniden okuma, açık kapama/temizleme, bozuk kaydı koruma, atomik commit hata enjeksiyonu ve runtime settings.json byte korumasını denetler. Birden çok eşzamanlı uygulamadan işaret birleştirme test edilmedi/desteklenmiyor.

<a id="e03-bindings"></a>

## F03-S005/S006 — ortak sistem, kritik uyarı ve bağ kapısı

Eğitim içeriği ayrı learning paketindedir; analitik/worker koduna gömülmedi. [Her yeni faz katkı adımları](../LEARNING_CONTENT.md) kalıcı AGENTS/DEVELOPMENT kayıtlarına eklendi. `scripts/check_learning.py` CI'da zorunlu: 13 makale, altı açık QML helpContext bağı, dört capability.help_links, sekiz ekran context eşlemesi; ilgili makale ve allowlist eylemleri çözülür. Geçersiz QML ve capability link enjeksiyonu otomatik kontrolde hata verir. Çalışma zamanında bilinmeyen bağ anlaşılır yardım hatasıdır.

Kritik uyarı başlangıç/gelişmiş görünüm ve bütün üç derinlikte ArticleView içinde katlanmaz. Gerçek masaüstü veri sızıntısı + advanced + tek cümle ekranında uyarı görüldü. Panel kapanınca çalışan I/O iptal edilmedi ve eski binding'e bağlı geçerli sonuç tamamlandı. Sekiz ekranın F1 açılışında beklenen makale kimliği betikte birebir denetlendi. Kaydırmalı panel, dar720×560 ve büyük1366×900, açık/koyu/sistem teması ve %200 metin render'ı kaydedildi. Büyük yazıda içerik doğal olarak kaydırılır; tek ekrana bütün rehber sığdığı iddia edilmez. Ortak FocusScroll, odaklanan arama/derinlik/düğmeyi görünür alana alır; Faz02 regresyon testleri korunur.

<a id="e03-checks"></a>

## Kontroller ve sınırlar

Son genel kontrol [çıktıları](phase03-checks.txt): kilitli dev sync, python3 ve kilitli check_docs, check_artifacts/check_learning, Ruff check/format, 54 pytest (13.88s), kilitli unittest discovery 9 belge testi ve kurulu giriş noktası GUI_SMOKE PASS. Offline/no-build-isolation wheel build geçti. Wheel açılımındaki10 içerik/QML/JS/çeviri modülü kaynak byte'larıyla eşleşti; repo dışındaki geçici açılımdan gerçek QML, çevrimdışı sızıntı araması ve model→tahmin bağlamı çalıştı. Bu bağımsız dağıtım/temiz sistem kurulum kabulü değildir. Tek/çift tırnak yardım bağ enjeksiyonu ve arama sonucu odağına dönüş de son54 test içindedir. Gerçek QQuickWindow.grabWindow görüntüleri JSON listelerinde; compositor çerçevesi değildir. [Arama](phase03-desktop-search.png), [ayrıntılı rehber](phase03-desktop-depth-2.png), [gelişmiş kritik uyarı](phase03-desktop-critical-advanced.png), [küçük panel](phase03-desktop-drawer-light-1.0.png), [geçici örnek](phase03-desktop-example.png). Ajan bu ekranları gerçekten görüntüleyerek inceledi. Fiziksel kullanıcı F1/arama/okuma testi, ekran okuyucu ve yeni başlayan eğitim etkisi henüz doğrulanmadı. Faz03 uzak CI başarısı aşağıda ayrı kayıtlıdır. İngilizce kabuk korunur; ilk makale paketi açıkça Türkçedir. Faz04 başlamadı.

Masaüstü tekrar kaydı: bir tekrarın kritik uyarı sonrası Escape adımı8 saniyede zaman aşımına uğradı; bu tekrar başarılı sayılmadı. Probe, klavye gönderiminden önce pencereyi etkinleştirip kapatma kontrolüne odak verme koşuluyla genişletildi. Son Wayland tekrarı `Critical help focus: True helpCloseButton` ve `PASS: Phase03 desktop, 6 checks, 11 screenshots` çıktılarıyla geçti. İlk başarısız tekrarın odak durumu ölçülmediği için kesin kök neden iddiası yoktur; gerçek kullanıcının klavye kontrolü ayrı açık kabul olarak kalır.

<a id="e03-user-example"></a>

## F03-USER-EXAMPLE — kullanıcı örnek pencere kontrolü

2026-10-06, ENV-USER-03: kullanıcı Uygulamada dene konumunu izledikten sonra “TAMAM YENİ BİR SEKME AÇTI UFAK BİR ÖNRKE VERDİ” bildirdi. Ayrı örnek öğrenme penceresinin açılması ve küçük örneğin görünmesi kullanıcı tarafından doğrulandı. Yol src/veri_ufku/ui/qml/ExampleWindow.qml. Bu bildirim örnekte arama, F1/Escape veya yerel işaretlerin yeniden açılış kalıcılığı için ek manuel kanıt sayılmaz.

<a id="e03-ci-remote"></a>

## F03-CI-REMOTE — uzak Linux CI

2026-10-06, ENV-CI-03: kullanıcı GitHub Actions gerçek sonuç çıktısını paylaştı. [Koşu 37511231471](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/actions/runs/37511231471), Veri_Ufku core and Qt smoke, success. Linux işi112432592915, 38 saniye: Qt native runtime kitaplıkları, izole yerel yollar, sabit uv/Python ve kilitli bağımlılıklar, belge/artefact doğrulaması, lint, çekirdek/başsız QML testleri ve kurulu giriş noktası Qt/process smoke adımları başarılı. İş akışı yolu .github/workflows/docs.yml; belge/artefact adımı check_learning.py yardım bağ kapısını da içerir. Kanıt kaynağı kullanıcının paylaştığı CI çıktısıdır; uzak API ayrıca sorgulanmadı. Yerel yayımlama sonrası HEAD: 922a889a2be577834ee03f8839c6f6df6424a2eb; koşunun commit eşlemesi uzak API üzerinden ayrıca doğrulanmadı. Çıktıda actions/checkout@v4 için Node.js20 kullanımdan kaldırma annotation'ı var; iş ve koşu success sonucuyla tamamlandı. Faz03 yerel/başsız, Wayland, sınırlı kullanıcı örnek pencere ve uzak CI kanıtları kayıtlı; olgunluk deneysel kalır.
