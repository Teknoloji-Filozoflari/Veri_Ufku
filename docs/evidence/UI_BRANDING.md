# Veri_Ufku — seçilen Veri Bağları logosu

2026-10-08. Kullanıcı v2/02 Veri Bağları logosunu seçip uygulama genelinde kullanılmasını istedi.
Kapsam mevcut ürünün görsel kimliği; yeni faz veya analitik yetenek başlatılmadı.

<a id="e-branding"></a>
## UI-BRANDING — uygulama

ENV-UI-BRANDING: Linux x86_64, kilitli CPython3.13.15/Qt6.11.2;
offscreen/software ve geçici izole XDG config/state/cache. Fiziksel masaüstü ve insan testi ayrı kapsamdır.

Kaynak `output/branding/v2/02-veri-baglari.png` değişmedi. Paket
`src/veri_ufku/assets/branding/logo.png` kaynağın byte kopyasıdır;
`source.json` kaynak SHA256 ve kullanıcı seçimini kaydeder. Qt smooth scaling
ile 16/24/32/48/64/128/256/512px PNG simgeleri hazırlandı; tasarım yeniden üretilmedi.

`BrandMark.qml` ana başlık ve örnek öğrenme penceresinde aynı paket simgesini kullanır.
Görünen Veri_Ufku adı korunur; yanındaki dekoratif resim ayrı Tab durağı veya ekran okuyucu tekrarı oluşturmaz.
`app.py` QGuiApplication ikonunu ve ADR-001'deki mevcut masaüstü kimliğini ayarlar;
ana ve örnek pencere bu ikonu devralır. HTML raporuna yerel PNG data URI gömülür;
PDF renderer aynı PNG'yi mevcut izinli resim kaynakları üzerinden okur. Ağ gereksinimi yoktur.
README aynı simgeyi kullanır.

`veri-ufku --install-desktop` yalnız kullanıcı XDG_DATA_HOME altına
applications/org.veriufku.Veri_Ufku.desktop ve sekiz hicolor simgesi yerleştirir.
Exec kurulu giriş noktasının mutlak yoludur; proje taşınırsa yeniden kurulum gerekir.
Şablon ve simgeler wheel paketinde yer alır. Alan adı/yayıncı kararı ADR-001'de açık kalır.

## Doğrulama

`tests/test_branding.py`: kaynak hash, sekiz gerçek PNG boyutu/alpha,
geçici XDG launcher/Exec/Icon ve iki gerçek QML pencere/logo/ikon.
`tests/test_exports.py`: self-contained HTML'de logo ve PDF allowlist render yolu.
İlgili testler: 19 passed. İlk denemelerde QML Image implicitHeight read-only ataması
ve Python QQuickImageBase::Status enum dönüştürücüsü hata verdi; width/height ve
QML bool ready kullanımıyla düzeltilip yeniden çalıştırıldı; başarısız denemeler kabul değildir.

`scripts/measure_branding.py`: gerçek 1366×900/720×560 ana pencere ve örnek pencere çekimi.
[Render kaydı](ui-branding/render.json), [geniş](ui-branding/1366-home.png),
[dar](ui-branding/720-home.png), [örnek](ui-branding/example.png).
Üç görüntü araçla incelendi; logo/metin/seviye simgeleri başlıkta sığıyor.
PDF test çıktısının ilk sayfası Poppler ile gerçekten çizilip araçla incelendi:
[PDF logo görüntüsü](ui-branding/report-page1.png). Bu sentetik fixture raporudur.

Genel kontrol [komut/tarih/exit/log kayıtları](ui-branding/checks.json):
locked offline dev sync; sistem/locked check_docs; check_artifacts/check_learning
(71 makale/49 UI bağı); Ruff check/format (124 dosya); 347 pytest passed in81.64s;
9 belge unittest; izole XDG kurulu giriş noktası GUI_SMOKE PASS; git diff --check exit0.
Belge unittest aynı belge testlerinin yeniden kontrolüdür.

[Wheel kaydı](ui-branding/wheel.json): offline/no-build-isolation wheel oluşturuldu,
12 logo/QML/manifest/desktop kaynağı kaynak byte'larıyla eşleşti. Wheel geçici site dizinine
gerçekten kuruldu; repo dışındaki cwd/PYTHONPATH ve izole XDG ile Qt/process GUI_SMOKE PASS.
Kurulu paketin masaüstü kurulum komutu geçici XDG_DATA_HOME üzerinde exit0;
desktop-file-validate exit0. Son desktop şablonunda tek ana kategori ve
StartupWMClass=Veri_Ufku kullanılır; Wayland masaüstü kimliği org.veriufku.Veri_Ufku'dur.

Kullanıcı dosya sistemi izniyle `.venv/bin/veri-ufku --install-desktop` gerçek kullanıcıda exit0:
`/home/s-oktay/.local/share/applications/org.veriufku.Veri_Ufku.desktop` ve
`/home/s-oktay/.local/share/icons/hicolor/{16,24,32,48,64,128,256,512}x{aynı}/apps/org.veriufku.Veri_Ufku.png`.
Gerçek launcher desktop-file-validate exit0; Exec çalışma alanındaki `.venv/bin/veri-ufku` mutlak yoludur.
[Gerçek kullanıcı kurulum kaydı](ui-branding/desktop.json) launcher içeriğini ve sekiz
kurulu simgenin paket kaynaklarıyla birebir eşleşen SHA256 değerlerini kaydeder.
Matris/ilerleme belgeleri güncellendikten sonra sistem/locked check_docs ve
9 belge unittest yeniden geçti; git diff --check exit0.
Başlatıcı/simgeler disk üzerinde kuruldu; fiziksel masaüstü menüsü/görev çubuğu etkileşimi,
compositor cache yenilemesi, ekran okuyucu ve yeni uzak CI bu başsız kontrollerle doğrulanmış sayılmaz.
