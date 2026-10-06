# Veri_Ufku — geliştirme ve doğrulama

Faz 01 komutları [README](../README.md)'de. `.python-version` CPython 3.13.15; `pyproject.toml` ve `uv.lock` sabit runtime/dev bağımlılıklarıdır. Sistem Python'una yazılmaz. `uv sync --locked --group dev` kilit değişikliğini reddeder; çalıştırmada `--frozen` yeniden çözümleme yapmaz. Ruff geliştirme wheel'i kaynak ağacında, hash ve RECORD doğrulaması `scripts/check_artifacts.py` ile yapılır. Ayrıntı [ADR-005](adr/005-runtime-jobs-lock.md).

## Yerel geliştirme

`src/veri_ufku/app.py` tek giriş noktasıdır. Domain Qt'sizdir; services demo kullanımını, jobs görev/süreç/iptali, ui ana thread QObject/QML aktarımını üstlenir. importers ve storage proje deposu uygulaması içermez; sonraki faz sözleşmeleri ve görev geçici alanı ayrıdır. learning paketinde çevrimdışı Qt çevirisi vardır; Öğren merkezi henüz yoktur.

Türkçe kaynak: `src/veri_ufku/learning/i18n/tr.ts`. Güncellemeden sonra `.venv/bin/pyside6-lrelease src/veri_ufku/learning/i18n/tr.ts -qm src/veri_ufku/learning/i18n/tr.qm`. QML qsTr ve Python QCoreApplication.translate aynı katalogda. Varsayılan tr; XDG config altında veri içermeyen settings.json ile locale en seçilebilir. Config hatası iş başlatmayı kapatır ve anlaşılır mesaj verir.

Yerel log XDG_STATE_HOME/veri_ufku altında, üç adet en fazla 256KiB dosya ve 0600 izin. Satır/değer, dosya içeriği, exception mesajı veya traceback yazılmaz; görev/hata/takip kimliği ve exception türü yazılır. Config ve cache XDG dizinlerinde; CPU worker Qt nesnesi almaz.

## Test ve CI

32 test: bağımsız elle hesaplı 435 toplamı, CPU ayrı PID, I/O temizliği, CPU/I/O iptal, zorunlu sonlandırma, eski veri/config sonucu, bütçe/admission/kuyruk, gözetici dosya hatası, güvenli log, gerçek QML sinyali ve kapanış, locale, config, belge tutarlılığı. Offscreen/software bir başsız GUI kanıtıdır; gerçek masaüstü ve sıfır bilgi kullanıcı testi yerine geçmez.

`.github/workflows/docs.yml` Ubuntu 24.04 üzerinde kilitli kurulum, belge/artefact, Ruff, pytest ve kurulu giriş noktası smoke adımlarını tanımlar. Aynı kontroller yerelde çalıştırıldı. Kullanıcı GitHub gönderimini ve masaüstü kontrollerini tamamladı. İlk sunucu CI koşusu 37499686960 failure ile sonuçlandı. Job env alanındaki desteklenmeyen runner context kullanımı düzeltildi; yeni başarılı koşu henüz doğrulanmadı. Ajan API bağlantısı başarısız; .git salt okunur. Yerel testler workflow context geçerliliğini tek başına doğrulamaz; resmî context tablosu ayrıca incelendi.

Ölçüm: `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase01.py`. Geliştirici makinesinde 20 sıcak açılış, 100 Qt fare olayı, 1 CPU/2 I/O, örneklenmiş RAM/disk ve tek iptal deneyi kaydedilir. Soğuk cache ve minimum hedef ölçümü değildir.

## İlerleyen fazların test planı

Import fixture'ları Türkçe/quoted/newline/bozuk satır ve kaynak değişimini; depo crash/fail adımları, iki yazıcı, samefile/symlink durumlarını; işlemler kimlik/lineage ve kaynak hash'ini doğrulayacak. Model testleri fold-içi fit, grup+zaman, final test defteri ve güvenli formatı kapsayacak. Gerçek import/grafik/export geldiğinde erken Linux paket smoke; tüm paket sorunları son faza bırakılmaz. Bu özellikler bu fazda uygulanmadı.
