# Veri_Ufku — geliştirme ve doğrulama

Faz 01/02/03 komutları [README](../README.md)'de. `.python-version` CPython 3.13.15; `pyproject.toml` ve `uv.lock` sabit runtime/dev bağımlılıklarıdır. Sistem Python'una yazılmaz. `uv sync --locked --group dev` kilit değişikliğini reddeder; çalıştırmada `--frozen` yeniden çözümleme yapmaz. Ruff geliştirme wheel'i kaynak ağacında, hash ve RECORD doğrulaması `scripts/check_artifacts.py` ile yapılır. Ayrıntı [ADR-005](adr/005-runtime-jobs-lock.md).

## Yerel geliştirme

`src/veri_ufku/app.py` tek giriş noktasıdır. Domain Qt'sizdir; services demo kullanımını, jobs görev/süreç/iptali, ui ana thread QObject/QML aktarımını üstlenir. importers ve storage proje deposu uygulaması içermez; sonraki faz sözleşmeleri ve görev geçici alanı ayrıdır. learning paketinde çevrimdışı Qt çevirisi ve Faz03 sürümlü Türkçe öğrenme içeriği vardır.

Türkçe kaynak: `src/veri_ufku/learning/i18n/tr.ts`. Güncellemeden sonra `.venv/bin/pyside6-lrelease src/veri_ufku/learning/i18n/tr.ts -qm src/veri_ufku/learning/i18n/tr.qm`. QML qsTr ve Python QCoreApplication.translate aynı katalogda. Varsayılan tr; XDG config altında veri içermeyen settings.json ile locale en seçilebilir. Config hatası iş başlatmayı kapatır ve anlaşılır mesaj verir.

Yerel log XDG_STATE_HOME/veri_ufku altında, üç adet en fazla 256KiB dosya ve 0600 izin. Satır/değer, dosya içeriği, exception mesajı veya traceback yazılmaz; görev/hata/takip kimliği ve exception türü yazılır. Config ve cache XDG dizinlerinde; CPU worker Qt nesnesi almaz.

## Test ve CI

Faz01’de32, Faz02’de37; Faz03’te toplam54 test (17 yeni yardım/yerel kayıt/GUI kabulü): bağımsız elle hesaplı 435 toplamı, CPU ayrı PID, I/O temizliği, CPU/I/O iptal, zorunlu sonlandırma, eski veri/config sonucu, bütçe/admission/kuyruk, gözetici dosya hatası, güvenli log, gerçek QML sinyali ve kapanış, locale, config, belge tutarlılığı. Offscreen/software bir başsız GUI kanıtıdır; gerçek masaüstü ve sıfır bilgi kullanıcı testi yerine geçmez.

`.github/workflows/docs.yml` Ubuntu 24.04 üzerinde kilitli kurulum, belge/artefact, Ruff, pytest ve kurulu giriş noktası smoke adımlarını tanımlar. Testlerden önce `sudo apt-get update` ve `sudo apt-get install --no-install-recommends -y libegl1 libgl1` ile Qt sistem kitaplıkları kurulur; offscreen/software seçimi import sırasındaki dinamik kitaplık gereksinimini kaldırmaz. Aynı kontroller yerelde çalıştırıldı. Kullanıcı GitHub gönderimini ve masaüstü kontrollerini tamamladı. İlk sunucu CI koşusu 37499686960 failure ile sonuçlandı. Job env alanındaki desteklenmeyen runner context kullanımı düzeltildi; ikinci koşu 37500010786 QtTest importunda eksik libEGL.so.1 nedeniyle test toplamada başarısız oldu. Sistem kitaplığı kurulumu workflow’a eklendi; üçüncü koşu 37500721689 tüm adımlarıyla başarılı. Kullanıcının paylaştığı CI çıktısı ve commit bağlantısı PHASE01.md#e01-remote-success içinde kayıtlı. Faz01 kabulü tamamlandı; olgunluk deneysel. Ajan API bağlantısı başarısız; .git salt okunur. Yerel testler workflow context geçerliliğini tek başına doğrulamaz; resmî context tablosu ayrıca incelendi.

Ölçüm: `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase01.py`. Geliştirici makinesinde 20 sıcak açılış, 100 Qt fare olayı, 1 CPU/2 I/O, örneklenmiş RAM/disk ve tek iptal deneyi kaydedilir. Soğuk cache ve minimum hedef ölçümü değildir.

## İlerleyen fazların test planı

Import fixture'ları Türkçe/quoted/newline/bozuk satır ve kaynak değişimini; depo crash/fail adımları, iki yazıcı, samefile/symlink durumlarını; işlemler kimlik/lineage ve kaynak hash'ini doğrulayacak. Model testleri fold-içi fit, grup+zaman, final test defteri ve güvenli formatı kapsayacak. Gerçek import/grafik/export geldiğinde erken Linux paket smoke; tüm paket sorunları son faza bırakılmaz. Bu özellikler bu fazda uygulanmadı.

## Faz02 kabuk ve doğrulama

QML Theme singleton ortak tokenları tanımlar; Qt Quick Controls Basic ile palet tutarlı kalır. Main kabuk düzeni, UiButton/UiCombo/StateNotice/InfoPanel ortak etkileşimlerdir. PresentationPreferences, dataset/ComputeBudget’dan ayrı atomik UI tercihi deposudur. Yeni Türkçe metinler mevcut çevrimdışı tr.ts/tr.qm kataloğunda, İngilizce aynı QML yolunda.

Başsız boyut/klavye/state ekranları: `uv run --frozen python scripts/measure_phase02.py`. Gerçek masaüstü: `uv run --frozen python scripts/measure_phase02.py --desktop` (QT_QPA_PLATFORM offscreen verilmeden). Betik geçici XDG alanlarını kendi oluşturur; kullanıcı tercihlerini değiştirmez. Çıktılar docs/evidence/phase02-headless.json veya phase02-desktop.json ve screenshot’larıdır. Betik GUI’yi açar, küçük/büyük pencereleri, tema/yazı ölçeklerini, nav/yardım klavyesini ve gerçek iş loading/canceled/error durumlarını denetler; analiz/import testi değildir. [PHASE02](evidence/PHASE02.md).

## Faz03 yardım geliştirme

[İçerik şeması ve her yeni faz katkısı](LEARNING_CONTENT.md). `uv run --frozen python scripts/check_learning.py` içerik, QML/capability bağları ve deneme allowlist kapısıdır; CI belge/artefact adımında koşar. Paket JSON kaynakları wheel içinde taşınır; yeni bağımlılık gerekmedi. `uv run --frozen python scripts/measure_phase03.py` başsız, aynı komut `--desktop` ile gerçek masaüstü render/girdi kanıtını üretir. Geçici izole XDG, Python bağlantı/urlopen fail-fast; OS ağ arayüzünün kapatıldığı iddiası değildir. Renderer PlainText ve ağ bileşeni içermez. [Faz03 kanıtı](evidence/PHASE03.md).
