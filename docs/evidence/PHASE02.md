# Faz 02 — uygulama kabuğu ve tasarım doğrulaması

2026-10-06. Faz02 durumu doğrulandı; olgunluk deneysel; kapsam zorunlu. Yalnız Faz02 uygulandı. Dosya importu, gerçek dataset/tablo, analiz, proje deposu, rapor ve Öğren merkezi henüz mevcut değil. Faz01'in görev denemeleri gerçek manager üzerinde korunur.

<a id="e02-environment"></a>

## Ortam ve kanıt türleri

ENV-02-HEADLESS: CachyOS x86_64, Linux7.2.9-1-cachyos/glibc2.44, CPython3.13.15, PySide6/Qt6.11.2; offscreen/software, geçici izole XDG yolları. ENV-02-DESKTOP: aynı makine/kilit, gerçek Wayland bağlantısı ve software renderer; GUI çalıştırma izniyle masaüstünde açıldı. Ekranlar gerçek QQuickWindow.grabWindow çıktısıdır. [Başsız kayıt](phase02-headless.json), [masaüstü kayıt](phase02-desktop.json); çalışma komutu `uv run --frozen python scripts/measure_phase02.py` ve masaüstü için `.venv/bin/python scripts/measure_phase02.py --desktop`. Makine donanımı/dosya sistemi önceki [ENV-01](../ENVIRONMENT.md) kaydındadır; minimum hedef donanım veya performans bütçesi kabulü değildir.

Kilit SHA256: 0dd1307806957482d1a4c531837750f879d235f909d46a24ed5e698caf59068c. Kaynak hash kaydı phase02-source.sha256. Genel kontroller ve sonuçlar phase02-checks.txt. Aşağıdaki kanıtlar otomatik gerçek Qt girdileri + ajan tarafından screenshot incelemesidir; yeni kullanıcı/ekran okuyucu testi değildir. Uzak Faz02 CI koşusu yapılmadı; Faz01 uzak kanıtı kendi commit'iyle ayrı kalır.

<a id="e02-references"></a>

## Referans görsel kapısı — UI-REF-VIS

ENV-REF-02; 2026-10-06. Beş resmî görsel gerçekten indirildi ve view_image ile yorumlanabilir olarak incelendi. KNIME AVIF, yerel Pillow ile PNG'ye dönüştürüldü; dönüştürme görsel içeriğini değiştirmedi. Kaynak URL, orijinal byte SHA256 ve boyutları [phase02-references.json](phase02-references.json) içinde. İncelenen ekranlar, görülen özellikler ve kabuk kararları [UI_REFERENCES](../UI_REFERENCES.md) içinde. Görseller uygulama varlığı olarak kopyalanmadı; marka/ikon aktarımı yok. Video ve referans uygulamaların etkileşimleri test edilmedi. Önceki Faz00 erişim sınırlaması tarihsel; UI-REF-VIS bu somut statik görsel incelemesiyle doğrulandı.

<a id="e02-tokens"></a>

## F02-S001 — tokenlar

`ui/qml/Theme.qml`, `UiButton.qml`, `UiCombo.qml`, `StateNotice.qml`, `InfoPanel.qml`, `Main.qml` (kök src/veri_ufku). QML singleton tek renk/boşluk/ölçü kaynağıdır; Basic Controls paleti aynı tokenlara bağlıdır. Gövde en az14, yardımcı yazı12 mantıksal piksel; sistem yazı büyüklüğü tabanı + %100/125/150/200 tercih çarpanı, Qt ekran DPI ölçeği ayrıca uygulanır. Düğmeler en az40px, yazı büyüyünce yükseklik artar. Focus halkası2px +3px dış mesafe. [Kontrast hesabı](phase02-contrast.json): metin çiftleri≥4.5 ve accent odak çiftleri≥3. Bu hesap tam UI erişilebilirlik kabulü değildir.

Açık/koyu doğrudan seçilir. Sistem teması Application.styleHints.colorScheme bildirimi, Unknown durumunda SystemPalette.window parlaklığı ile çözülür. Başsız platform OS şeması bildirmediği için gerçek uygulama paleti değiştirilerek fallback güncellemesi test edildi; gerçek OS tema değiştirme davranışı ayrıca manuel denenmedi. Qt kaynakları [Application](https://doc.qt.io/qt-6/qml-qtquick-application.html), [SystemPalette](https://doc.qt.io/qt-6/qml-qtquick-systempalette.html).

<a id="e02-shell"></a>

## F02-S002 — gerçek kabuk

Main.qml: dar sol navigasyon; üstte gerçek mevcut durum olan “Proje açık değil / Veri yüklenmedi”; merkez ScrollView; büyük pencerede gerektiğinde açılan sağ panel, küçük pencerede kapanabilir sağ Drawer. Dock eşiği1100×yazı ölçeği, panel320×ölçek. Sekiz alan: Başlangıç/Veri/Hazırla/İncele/Karşılaştır/Model/Rapor/Öğren. Gelecek alanlar kullanılabilirlik bilgisini gösterir; veri/sonuç taklidi veya aktif analiz düğmesi içermez. Nav değişimi bridge/session/iş/sonucu değiştirmez.

Başlangıçtaki Dosya aç ve Örnek veriyle dene öne çıkan iki karttır; henüz import/örnek veri yolu olmadığı için düğmeleri devre dışı ve nedenleri görünür/erişilebilir metinlidir. Amaç kartları günlük dilde, açık “planlanan / henüz mevcut değil” etiketiyle ilgili kullanılabilirlik ekranına götürür. Kaynak dosya okuma/yazma yapılmaz. Bu karar kullanıcıdaki gelecek alanları çalışır göstermeme şartını korur; Faz05/örnek veri yeteneği erkenden geliştirilmez.

<a id="e02-views"></a>

## F02-S003 — tek oturum, kalıcı tercihler

PresentationPreferences ayrı `XDG_CONFIG_HOME/veri_ufku/ui-preferences.json` şema1 kaydına tema/görünüm/yazı ölçeği yazar. QSaveFile, direct-write fallback kapalı, 0600 izin, atomik commit. Başarısız commit'te önceki dosya ve ekrandaki tercih korunur; bozuk/bilinmeyen kayıt silinmez veya üzerine yazılmaz, anlaşılır uyarı gösterilir. `settings.json` locale ve ComputeBudget kaydı değişmez. tests/test_presentation_preferences.py: gerçek yeniden okuma, runtime ayarları byte koruması, bozuk kayıt ve commit hata enjeksiyonu.

tests/test_gui.py::test_phase02_keyboard_preferences_and_view_preserve_session gerçek ComboBox klavye girdileriyle koyu/gelişmiş seçer; I/O işi sürerken aynı binding/job_id korunur. Başlangıç görünümüne dönüşte sonuç korunur ve resultLabel görünür kalır. Yeni Python/Qt sürecinde aynı tercihler geri yüklenir. Gelişmiş görünüm görev kimliği, gerçek oturum/config sürümü ve çalışan yapılandırma/hata denemesi araçlarını açar. Sonuç, hata, görev durumu, ilerleme ve iptal iki görünümde de ortak kalır. Gerçek dataset olmadığından veriyle mod geçişi testi ileride dataset fazına aittir; şu an tek gerçek DemoSession üzerinde kanıt vardır.

<a id="e02-states"></a>

## F02-S004 — ortak durum ve yardım

StateNotice: boş/kullanılamıyor/yükleniyor/hata/iptal, metin + sembol; active işte BusyIndicator, gerçek bilinen progress ayrı ProgressBar. tests/test_gui.py gerçek CPU/loading, iptal/canceled ve failure/error yolunda ortak bileşenin kind değerlerini doğrular. Masaüstü ve başsız state screenshot'ları JSON kayıtlarında listelenir. Safe error mesajı ve correlation id Faz01 yolu ile korunur; ham exception içeriği gösterilmez.

InfoPanel bütün sekiz ekran için aynı “Bu ne işe yarar?” düğmesi/F1 yolunu kullanır; panel açıklaması seçili alana bağlıdır. Öğren merkezi arama/ders sistemi bu fazda uygulanmaz. Escape ve kapat düğmesi açan kontrole odak döndürür. Panelin açılması/kapanması session veya işi değiştirmez. Küçük Drawer modal odak sınırıyla görünür çalışma alanını geçici örter; kapatıldığında iş devam eder. [Qt Drawer](https://doc.qt.io/qt-6/qml-qtquick-controls-drawer.html) davranışı izlendi.

<a id="e02-accept"></a>

## F02-S005 — kabul

Gerçek Qt render: 720×560 ve1366×900 açık/koyu %100;1024×768 sistem %125 ve açık %150;720×560 koyu %200. İş alanı en dar durumda460px genişlik/272px yükseklik; içerik dikey kayar, kartlar tek sütuna ve yardım düğmesi ayrı satıra geçer. Geniş görünümde iki sütun ve sağ dock. UI varsayılan başlangıç1200×800, minimum720×560. Bunların dışındaki her çözünürlük/DPI doğrulanmış sayılmaz.

QtTest fare/klavye: sağ dock/dar Drawer açma, Escape ile kapama ve odak dönüşü; sol nav Down/Space ve Ctrl+1; ComboBox Space/End/Enter ile tema/görünüm; pencere/yazı ölçeği değişimi. Tab/ShiftTab standart Qt focus chain; odaklanan UiButton ilgili ScrollView'da görünür alana alınır. Kullanıcının tema/Tab/F1 bildirimi aşağıda ayrı kayıtlıdır; yardımcı teknoloji testi yapılmadı. Tercih kalıcılığı yeni süreçle doğrulandı. Wayland masaüstü koşusu ve alınan görseller gerçek masaüstü GUI kanıtıdır; başsız kanıtla ayrı tutulur.

Ajan görsel incelemesinde %200 dar başlık/yardım taşması ve Drawer Escape sorunu bulundu, düzeltildi ve kayıtlar yeniden üretildi. Ortak tokenlar/üç eski statik prototip yeniden değerlendirildi: [DESIGN_REVIEW](../DESIGN_REVIEW.md). Prototiplerin tabloları/sonuçları gerçek özellik diye gösterilmez. Yeni screenshot'lar çalışan kabuğu gösterir.

Faz01 regresyonları, yeni kabuk testleri, lint ve belge/artefact kontrolleri phase02-checks.txt içinde. Faz03 veya sonraki fazlar başlatılmadı.

Son yerel kontrol: kilitli dev sync, doğrudan python3 check_docs ve kilitli check_docs/check_artifacts, Ruff check/format, 37 pytest testi (9.49s), kilitli unittest discovery 9 belge testi ve kurulu giriş noktası GUI_SMOKE PASS. `uv build --wheel --offline --no-build-isolation` geçti; ZIP incelemesinde bütün yeni QML bileşenleri, qmldir, preferences.py ve tr.qm mevcut. Yeni wheel ayrıca bağımsız sistem kurulum paketi değildir. Tüm komut çıktıları phase02-checks.txt içinde.

<a id="e02-user-desktop"></a>

## F02-USER-SHELL — kullanıcı masaüstü kontrolü

2026-10-06, ENV-USER-02: kullanıcı mevcut Linux masaüstünde kontrolün ardından “tema tab f1 tamam” bildirdi. Tema seçimi, Tab ile temel gezinme ve F1 yardım açma kullanıcı tarafından başarılı bildirildi. Uygulama yolu src/veri_ufku/ui/qml/Main.qml. Bu bildirim yeniden başlatma sonrası kalıcılık, Escape veya işletim sistemi tema değişimi için ek manuel kanıt sayılmaz. Uzak Faz02 CI sonucu henüz alınmadı.
