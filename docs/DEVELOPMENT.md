# Veri_Ufku — geliştirme ve doğrulama

Faz 01/02/03/04/05 komutları [README](../README.md)'de. `.python-version` CPython 3.13.15; `pyproject.toml` ve `uv.lock` sabit runtime/dev bağımlılıklarıdır. Sistem Python'una yazılmaz. `uv sync --locked --group dev` kilit değişikliğini reddeder; çalıştırmada `--frozen` yeniden çözümleme yapmaz. Ruff geliştirme wheel'i kaynak ağacında, hash ve RECORD doğrulaması `scripts/check_artifacts.py` ile yapılır. Ayrıntı [ADR-005](adr/005-runtime-jobs-lock.md).

## Yerel geliştirme

`src/veri_ufku/app.py` tek giriş noktasıdır. Domain Qt'sizdir; services demo kullanımını, jobs görev/süreç/iptali, ui ana thread QObject/QML aktarımını üstlenir. importers Faz05 CSV/TSV ortak parser/worker içerir. storage proje deposu Faz04 ile eklendi; görev geçici alanı ayrı kalır. learning paketinde çevrimdışı Qt çevirisi ve Faz03 sürümlü Türkçe öğrenme içeriği vardır.

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

## Faz04 proje geliştirme

Depo Qt'siz `storage/project_model.py` ve `project_store.py`; tek yayın noktası ACTIVE. UI QObject `ui/projects.py`, dosya I/O thread'inden dönen state'i main thread'de uygular. Kayıt sürerken ekran değişiklik ve kapanışı durdurur; worker Qt nesnesi değiştirmez. `ProjectPanel.qml` gerçek proje yollarını açar. `Polars==2.0.0` ve runtime-32 exact lock'ta; yalnız Parquet depolama/metadata doğrulamasında kullanılır.

README kilitli kontrolleri korunur. `uv run --frozen python scripts/measure_phase04.py` izole geçici Btrfs projeleriyle GUI render/kaydet/aç/eksik kaynak/kurtarma/farklı kaydet akışını kaydeder. Depo testleri `uv run --frozen pytest -q tests/test_projects.py tests/test_project_gui.py`; tüm regresyonlar için standart pytest komutu. SIGKILL alt süreçleri kernel kilidini terk eder, hiçbir worker ACTIVE'yi atlayarak metadata'yı güncel saymaz. [Ayrıntılı protokol ve sınırlar](adr/007-project-store-phase04.md), [gerçek kanıt](evidence/PHASE04.md). Native dosya seçici ve yeni masaüstü/remote CI ayrıca yapılmalıdır.

## Faz05 uygulama bağı

Faz05 testleri tests/test_delimited.py ve test_import_gui.py; CSV/TSV UTF8/cp1254 fixture, değişmez kaynak, sınır/karantina, kimlik, şema1→2 migrasyon,16 gerçek import SIGKILL, Qt drop ve gerçek süreç iptali. `uv run --frozen python scripts/measure_phase05.py` Btrfs izole projede gerçek full import/preview/iptal/render ve RSS/disk/tick örnekler. İlk import için wheel build/install ve paket içinden gerçek spawn import smoke yapılır; yalnız source tree smoke ile kabul edilmez. Standart kilitli kontroller korunur. [ADR-008](adr/008-delimited-import-phase05.md), [kanıt](evidence/PHASE05.md).

## Faz06 kontrolleri

`uv run --frozen pytest -q tests/test_structured_import.py tests/test_import_gui.py` dört format değer/tür ve gerçek worker/QML kontrolleridir. Standard kilitli check_docs/check_artifacts/check_learning/Ruff/pytest/offscreen giriş noktası korunur. `scripts/smoke_structured_wheel.py --package-root TARGET --fixtures ABS_PATH` ayrı /tmp cwd içinde kurulu wheel ve locked runtime ile dört formatın gerçek worker/yayın/reopen yolunu doğrular. `scripts/measure_phase06.py` başsız render ve ölçüm üretir. [Kanıt](evidence/PHASE06.md).

## Faz07 katkısı

Faz07: tests/test_dataset.py ve test_dataset_gui.py referans istatistik/ID/scope/proje roundtrip/spawn/iptal kontrolleri. scripts/measure_phase07.py büyük tablo RSS ve gerçek QML ekranları; --package-root TARGET --output JSON kurulu wheel içinde aynı işi doğrular. Standart kilitli kapılar korunur. [Kanıt](evidence/PHASE07.md).

## Faz08 katkısı

Faz08 gerçek kontroller: tests/test_quality.py ve test_quality_gui.py bağımsız değer/RowId/kapsam/snapshot/deterministik öneri, gerçek QML/spawn/iptal/roundtrip. `uv run --frozen python scripts/measure_phase08.py`100.000 kayıt, kaynak hash ve dar/geniş gerçek render ölçer; --package-root TARGET --output JSON aynı kurulu wheel yolunu çalıştırır. Standart kilitli kapılar korunur. [Karar](adr/011-quality-phase08.md), [kanıt](evidence/PHASE08.md).

## Faz09 kontrolleri

`tests/test_operations.py` elle belirlenmiş değer/RowId, branch/redo/reopen, hatalı/iptal/eski/tampered çıktı, disk yayın fault injection ve gerçek SIGKILL; `tests/test_operations_gui.py` gerçek QML düğmesi/spawn/apply/undo/redo/reopen ve eski sonuç etiketi. `uv run --frozen python scripts/measure_phase09.py`100.000 kayıt full preview/apply/filtre/kaynak hash/iptal ve dar/geniş başsız render üretir; --package-root TARGET --output JSON aynı işi kurulu wheel içinde denetler. Standart kilitli kapılar korunur. [Karar](adr/012-versioned-operations-phase09.md), [kanıt](evidence/PHASE09.md).

## Faz10 katkısı

`tests/test_cleaning.py` bağımsız değer/kimlik/hassasiyet/grup/disk fault kontrolleri; `tests/test_cleaning_gui.py` gerçek dokuz yöntem formu/spawn/yayın/undo/redo/reopen ve tarih hata/iptal. `uv run --frozen python scripts/measure_phase10.py`100.000 kayıt dokuz yöntem ve render; `--package-root TARGET --output JSON` kurulu wheel içinde aynı işi çalıştırır. Standart locked sync/check_docs/check_artifacts/check_learning/Ruff/pytest/unittest/offscreen giriş noktası kapıları korunur. [Karar](adr/013-cleaning-phase10.md), [kanıt](evidence/PHASE10.md).


## Faz11 katkısı

`tests/test_relational.py`, `test_relational_gui.py`, `test_relational_backends.py`, `test_phase11_formats.py` gerçek hesap/üyelik/AST, QML/spawn/üç adımlı join, readonly format fixture ve DuckDB karşılaştırmalarını kapsar. DuckDB1.5.6 yalnız locked dev bağımlılığı; üretim Polars2.0.0. `uv run --frozen python scripts/measure_phase11.py`100.000 kayıt dokuz yöntem, tam n:n tahmin ve undo/redo/reopen/render; `--package-root TARGET --output JSON` kurulu wheel yolunu çalıştırır. Standart kontroller korunur. [Karar](adr/014-transformations-phase11.md), [kanıt](evidence/PHASE11.md).
