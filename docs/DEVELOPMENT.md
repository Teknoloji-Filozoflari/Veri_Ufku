# Veri_Ufku — geliştirme ve doğrulama

Faz00–13 komutları [README](../README.md)'de ve aşağıdaki faz bölümlerindedir. Bu bölümler teslim anındaki kontrolleri korur; güncel çapraz faz kontrolü [AUDIT_00_13](evidence/AUDIT_00_13.md). `.python-version` CPython 3.13.15; `pyproject.toml` ve `uv.lock` sabit runtime/dev bağımlılıklarıdır. Sistem Python'una yazılmaz. `uv sync --locked --group dev` kilit değişikliğini reddeder; çalıştırmada `--frozen` yeniden çözümleme yapmaz. Ruff geliştirme wheel'i kaynak ağacında, hash ve RECORD doğrulaması `scripts/check_artifacts.py` ile yapılır. Ayrıntı [ADR-005](adr/005-runtime-jobs-lock.md).

## Yerel geliştirme

Seçilen logonun paket kaynakları `src/veri_ufku/assets/branding/` içindedir.
Kaynağı değiştirmeden boyutları yeniden üretmek için `uv run --frozen python scripts/prepare_branding.py`;
gerçek Qt render için `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen python scripts/measure_branding.py`.
Linux kullanıcı menüsü kurulumu: `.venv/bin/veri-ufku --install-desktop`.
Kurulum XDG_DATA_HOME applications ve hicolor yollarına yazar; testlerde geçici mutlak yol kullanılır.
[Logo kaydı](evidence/UI_BRANDING.md).

`src/veri_ufku/app.py` tek giriş noktasıdır. Domain Qt'sizdir; services demo kullanımını, jobs görev/süreç/iptali, ui ana thread QObject/QML aktarımını üstlenir. importers Faz05 CSV/TSV ortak parser/worker içerir. storage proje deposu Faz04 ile eklendi; görev geçici alanı ayrı kalır. learning paketinde çevrimdışı Qt çevirisi ve Faz03 sürümlü Türkçe öğrenme içeriği vardır.

Türkçe kaynak: `src/veri_ufku/learning/i18n/tr.ts`. Güncellemeden sonra `.venv/bin/pyside6-lrelease src/veri_ufku/learning/i18n/tr.ts -qm src/veri_ufku/learning/i18n/tr.qm`. QML qsTr ve Python QCoreApplication.translate aynı katalogda. Varsayılan tr; XDG config altında veri içermeyen settings.json ile locale en seçilebilir. Config hatası iş başlatmayı kapatır ve anlaşılır mesaj verir.

Yerel log XDG_STATE_HOME/veri_ufku altında, üç adet en fazla 256KiB dosya ve 0600 izin. Satır/değer, dosya içeriği, exception mesajı veya traceback yazılmaz; görev/hata/takip kimliği ve exception türü yazılır. Config ve cache XDG dizinlerinde; CPU worker Qt nesnesi almaz.

## Test ve CI

Faz01’de32, Faz02’de37; Faz03’te toplam54 test (17 yeni yardım/yerel kayıt/GUI kabulü): bağımsız elle hesaplı 435 toplamı, CPU ayrı PID, I/O temizliği, CPU/I/O iptal, zorunlu sonlandırma, eski veri/config sonucu, bütçe/admission/kuyruk, gözetici dosya hatası, güvenli log, gerçek QML sinyali ve kapanış, locale, config, belge tutarlılığı. Offscreen/software bir başsız GUI kanıtıdır; gerçek masaüstü ve sıfır bilgi kullanıcı testi yerine geçmez.

`.github/workflows/docs.yml` Ubuntu 24.04 üzerinde kilitli kurulum, belge/artefact, Ruff, pytest ve kurulu giriş noktası smoke adımlarını tanımlar. Testlerden önce `sudo apt-get update` ve `sudo apt-get install --no-install-recommends -y libegl1 libgl1` ile Qt sistem kitaplıkları kurulur; offscreen/software seçimi import sırasındaki dinamik kitaplık gereksinimini kaldırmaz. Aynı kontroller yerelde çalıştırıldı. Kullanıcı GitHub gönderimini ve masaüstü kontrollerini tamamladı. İlk sunucu CI koşusu 37499686960 failure ile sonuçlandı. Job env alanındaki desteklenmeyen runner context kullanımı düzeltildi; ikinci koşu 37500010786 QtTest importunda eksik libEGL.so.1 nedeniyle test toplamada başarısız oldu. Sistem kitaplığı kurulumu workflow’a eklendi; üçüncü koşu 37500721689 tüm adımlarıyla başarılı. Kullanıcının paylaştığı CI çıktısı ve commit bağlantısı PHASE01.md#e01-remote-success içinde kayıtlı. Faz01 kabulü tamamlandı; olgunluk deneysel. Ajan API bağlantısı başarısız; .git salt okunur. Yerel testler workflow context geçerliliğini tek başına doğrulamaz; resmî context tablosu ayrıca incelendi.

Ölçüm: `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase01.py`. Geliştirici makinesinde 20 sıcak açılış, 100 Qt fare olayı, 1 CPU/2 I/O, örneklenmiş RAM/disk ve tek iptal deneyi kaydedilir. Soğuk cache ve minimum hedef ölçümü değildir.

## İlerleyen fazların test planı

Import fixture'ları Türkçe/quoted/newline/bozuk satır ve kaynak değişimini; depo crash/fail adımları, iki yazıcı, samefile/symlink durumlarını; işlemler kimlik/lineage ve kaynak hash'ini doğrulayacak. Model testleri fold-içi fit, grup+zaman, final test defteri ve güvenli formatı kapsayacak. Gerçek import/grafik/export geldiğinde erken Linux paket smoke; tüm paket sorunları son faza bırakılmaz. Bu özellikler bu fazda uygulanmadı.

Bu plan Faz01'de kaydedildi: import/depo/işlem/grafik/export kontrolleri Faz04–13'te uygulanmıştır; fit/fold/grup-zaman/final test defteri kontrolleri Faz16 ile uygulanmıştır; sonraki estimator/yeni dosya tahmin kontrolleri gelecek kapsamdır.

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


## Faz12 kontrolleri

`tests/test_charts.py` elle referans grafik tablosu/RowId, Pearson/Spearman/n, Decimal/overflow ve gerçek PNG/SVG/proje yayını; iki SIGKILL/iki süreç/fault/tamper. `tests/test_charts_gui.py` yedi gerçek QML formu, Matplotlib image provider, Qt fare/zoom/reset, worker/export/save/reopen ve eski/iptal senaryoları. `uv run --frozen python scripts/measure_phase12.py`100.000 kayıt yedi grafik,100 input/render, RSS/tick ve gerçek export üretir; `--package-root TARGET --output JSON` kurulu noneditable Linux wheel'de aynı akıştır. `--project-temp PATH` yerel FS seçer. Locked sync/check_docs/check_artifacts/check_learning/Ruff/pytest/unittest/entry smoke kapıları korunur. CI'a erken Linux wheel QML/Matplotlib/process/export adımı eklendi; yeni uzak başarı henüz bildirilmedi. Matplotlib MPLCONFIGDIR worker'a özel geçici dizin. [Karar](adr/015-charts-phase12.md), [kanıt](evidence/PHASE12.md).

## Faz13 kontrolleri

`tests/test_exports.py` beş format elle projeksiyon/değer/tür/null/ns/precision, unsafe başlık/metin/numeric, mevcut/symlink/iki process/cancel, gerçek import adaptörleri, HTML escape ve Türkçe çok sayfalı PDF. `tests/test_exports_gui.py` iki örnekten profil/kalite/temizlik/Matplotlib/worker/yedi export/save/reopen GUI geliştirici walkthrough'u; kullanıcı testi değildir. `uv run --frozen python scripts/measure_phase13.py` yeni XDG+paket font/yardım/örnek/rapor ve Python TCP fail-fast parent/spawn,100k CSV/JSONL/Parquet, iptal/sıra/tür/sayı, screenshot/PDF render. `--package-root TARGET --output JSON` /tmp cwd içindeki noneditable Linux wheel ile aynı deneme. OS ağ arayüzü kapatılmış veya temiz makine offline kurulmuş iddia edilmez. Qt/font çalışma zamanı bootstrap sonrası adres alanı bütçesi, GUI wall/cancel deadline korunur. Locked standart sync/check_docs/check_artifacts/check_learning/Ruff/pytest/unittest/entry smoke komutları korunur. [Karar](adr/016-release-phase13.md), [release](RELEASE_NOTES_0_1_0.md), [kanıt](evidence/PHASE13.md).

## Faz00–13 teknik tarama

`uv run --frozen python scripts/audit_phases.py --output /tmp/veri-ufku-phase-inventory.json` kaynak paragraf/path/capability/test modülü ve Qt bağımsız hesap sınırlarının salt okunur envanteridir; runtime kabulü yerine geçmez. Bütün regresyonlar ve erken kurulu wheel import/ölçekli iş akışları ayrıca çalıştırılır. Gerçek insan kullanıcı testi bu denetimde çalıştırılmaz. Paket kabul fixture'ları magaza.csv/subeler.csv CC0; GUI değer/kimlik ve geri alma kontrolleri tests/test_exports_gui.py içindedir. Gerçek tarihler ve komut/exit kayıtları [AUDIT_00_13](evidence/AUDIT_00_13.md).

Kullanıcı görsel düzeltmesi: sağ üstte yalnız tema ve başlangıç/gelişmiş simgeleri; yazı boyutu sabit. Eski ölçek kanıtları tarihsel kayıt olarak korunur; güncel doğrulama [UI_HEADER](evidence/UI_HEADER.md).

Son kullanıcı talimatıyla yalnız turuncu vurgulu koyu tema; tema düğmesi kaldırıldı. Eski açık/sistem kayıtları uygulanmaz; sağ üst yalnız seviye simgeleri. [Güncel doğrulama](evidence/UI_DARK_ONLY.md).


## Faz14 kontrolleri

`tests/test_statistics.py` kapalı form t/F/chi-kare, exact kombinasyon, rank ve Fisher-z bağımsız referansları; anahtar/satır sırası, null/nonfinite, hassasiyet, filtre, sabit/yetersiz veri, ties/zero, atomik fault/JSON tamper/kayıt yeniden açma. `tests/test_statistics_gui.py`11 gerçek QML yöntemi, spawn/önkontrol/kayıt/help ve eski/iptal akışı. `uv run --frozen python scripts/measure_phase14.py`11 yöntem ve100000 kayıt, parent+worker RSS/tick, gerçek render, offline Python TCP reddi, kayıt/reopen/resave/iptal/eski bağ. `--package-root TARGET --output JSON` /tmp cwd içindeki kurulu noneditable wheel'de aynı deneme. Kilitli sync/check_docs/check_artifacts/check_learning/Ruff/pytest/unittest/offscreen entry point korunur. [ADR-017](adr/017-statistics-phase14.md), [kanıt](evidence/PHASE14.md).

## Faz15 kontrolleri

tests/test_preparation.py bağımsız tam n/null/sınıf, kimlik/türev/sabit/nonfinite, gerçek kaynak/history/copy-fork, impute sırası/IQR policy, mapping tamper, fault/iki SIGKILL/ikinci process readonly; test_preparation_gui.py dört gerçek QML amaç/worker/save/reopen/help ve eski/iptal/hatalı yeni iş bağını denetler. `uv run --frozen python scripts/measure_phase15.py` dört amaç, gerçek geçmiş mean fill ve kaynak/relocate,100k, RSS/tick, screenshot, F1/kayıt/aç/iptal/eski sonucu çalıştırır; `--package-root TARGET --output JSON` kurulu noneditable wheel akışıdır. Locked sync/check_docs/check_artifacts/check_learning/Ruff/pytest/unittest/offscreen entry kapıları korunur. [ADR-018](adr/018-model-preparation-phase15.md), [kanıt](evidence/PHASE15.md).

Başlangıç tasarımı: `uv run --frozen python scripts/measure_home_compact.py` gerçek720/1366 başsız render, Unicode/boşluk/# klasör, arama/gizli, oluştur/save/isim/aç kontrolleridir. `--package-root TARGET --output JSON` kurulu wheel denemesidir. tests/test_home_folders_gui.py gerçek klasör akışını, mevcut project GUI testleri hata/geri dönüşü doğrular. Standart locked kontroller korunur. [Kanıt](evidence/UI_HOME_COMPACT.md).

## Faz16

`tests/test_validation.py` bağımsız merkez/MAE ve Dummy metrik referansı, gerçek fit spy/poison, seed/grup/time/combined/ufuk/rare fold, ledger/copy/save-as/reopen/fault/SIGKILL/readonly; `tests/test_validation_gui.py` gerçek QML/spawn/final tekrar/help/engelli/iptal/stale/invalid-failed kaydı. `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen python scripts/measure_phase16.py` beş protokol+100k, RSS/tick, üyelik artifact/kaynak hash ve defter reopen; `--package-root TARGET --output JSON` kurulu noneditable Linux wheel yolu. Locked sync/check_docs/check_artifacts/check_learning/Ruff/pytest/unittest/installed entry smoke korunur. [ADR-019](adr/019-validation-baseline-phase16.md), [kanıt](evidence/PHASE16.md).

Faz17: sınırlı sayısal tahmin yolu, Faz15 hazırlığı ve Faz16 split/fold/defteri üstünde gerçek training-only estimator pipeline kullanır. Adaylar baseline/doğrusal/Ridge/RandomForest; seçim yalnız geliştirme CV MAE, final testte tek dondurulmuş aday. MAE/RMSE hedef birimi, R² negatif/sabit hedef sınırı, gerçek-tahmin/artık grafikleri (en fazla1000 örnek; metrik tam bölüm), dar ayar/maliyet sınırları ve test sonrası keşifsel yorum. Ayrıntılı sözleşme [ADR-020](adr/020-regression-phase17.md), gerçek kabul [PHASE17](evidence/PHASE17.md).
`uv run --frozen pytest tests/test_regression.py tests/test_regression_gui.py tests/test_validation.py tests/test_validation_gui.py -q`; `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen python scripts/measure_phase17.py`. Betik `--package-root TARGET --output JSON` ile noneditable Linux wheel çalışmasını doğrular.


Veri içeriği arayüz düzenlemesi: tests/test_dataset_gui.py gerçek import/metadata açıklaması/kayıt/yeniden açma/filtre kapsamı ve dört yol haritası eylemini; tests/test_dataset.py açıklama sınırı ve eski rol çağrısıyla korunumunu doğrular. Standart locked kapılar korunur. [Kanıt](evidence/UI_DATA_CONTENT.md).


## Faz18 kategori tahmini

`uv run --frozen pytest tests/test_classification.py tests/test_classification_gui.py tests/test_validation.py tests/test_validation_gui.py tests/test_regression.py tests/test_regression_gui.py -q` sınıf/matris/eğri/averaging/eşik referansları, fit spy, maliyet ve final karar reddi ile gerçek QML/spawn/iptal/retune/reopen yollarını çalıştırır. `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen python scripts/measure_phase18.py` ikili/çok sınıflı240, combined240, Forest20k ve Baseline/Logistic100k koşularını ölçer. `--package-root TARGET --output JSON` noneditable wheel yolunu doğrular. Kilitli kurulum, check_docs/artifacts/learning, Ruff check/format, full pytest/unittest ve installed entry smoke korunur. [ADR-021](adr/021-classification-phase18.md), [gerçek teknik kayıt](evidence/PHASE18.md).


Faz19 kontrolleri: `uv run --frozen pytest tests/test_unsupervised.py tests/test_unsupervised_gui.py -q`; `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen python scripts/measure_phase19.py`. Betik `--package-root TARGET --output JSON` ile noneditable wheel aynı gerçek akışı çalıştırır. Standart locked sync/docs/artifacts/learning/Ruff/pytest/unittest/installed entry kapıları korunur.

Faz20: `uv run --frozen pytest tests/test_lifecycle.py tests/test_lifecycle_gui.py -q`
exact roundtrip, hostile paket, şema/sürüm, no-fit, RowId/filter/sort/duplicate/drop/
batch ve gerçek QML/spawn/newfile akışını denetler. `uv run --frozen python scripts/measure_phase20.py`
kaynak/`--package-root TARGET --output JSON` kurulu wheel'de gerçek QML render,
güvenli paket/reopen/tahmin/100k çalıştırır. Locked sync/docs/artifacts/learning,
Ruff check/format, full pytest/unittest ve installed offscreen/software smoke korunur.
[ADR-023](adr/023-model-lifecycle-phase20.md), [kanıt](evidence/PHASE20.md).


Faz21: `uv run --frozen pytest tests/test_time_series.py tests/test_time_series_gui.py -q`;
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen python scripts/measure_phase21.py`.
Betik `--package-root TARGET --output JSON` ile noneditable Linux wheel'de gerçek
QML/spawn/baseline/final/120 ve100000 kayıt/kaynak/reopen/help yolunu doğrular.
Standart locked sync/docs/artifacts/learning/Ruff/pytest/unittest/entry kapıları korunur.
[ADR-024](adr/024-time-series-phase21.md), [kanıt](evidence/PHASE21.md).


Faz22: `uv run --frozen pytest tests/test_text.py tests/test_text_gui.py -q`;
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen python
scripts/measure_phase22.py`. Betik Python TCP bağlantısını parent/spawn'da
engeller;120/100000 metin, gerçek QML/classification/baseline/final/reopen/privacy.
`--package-root TARGET --output JSON` noneditable Linux wheel yoludur. OS ağ
arayüzünü kapatma/temiz makine offline kurulum iddiası değildir. Standart locked
sync/docs/artifacts/learning/Ruff/pytest/unittest/installed entry kapıları korunur.
[ADR-025](adr/025-local-text-phase22.md), [kanıt](evidence/PHASE22.md).


## Faz23

`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen pytest tests/test_recipes.py tests/test_recipes_gui.py tests/test_lifecycle.py tests/test_lifecycle_gui.py -q`; `uv run --frozen python scripts/measure_phase23.py`. Betik `--package-root TARGET --output JSON` ile kurulu noneditable wheel'de aynı recipe/spawn/120–100000/atomic/drift/model/target/reopen yolunu denetler. Standart kilitli kontroller korunur. [ADR-026](adr/026-recipes-monitoring-phase23.md), [kanıt](evidence/PHASE23.md).


## Faz24

`uv run --frozen pytest tests/test_performance.py -q`;
`uv run --frozen python scripts/measure_phase24.py --output docs/evidence/phase24/benchmark.json`;
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen python scripts/measure_phase24_gui.py --output docs/evidence/phase24/gui.json`;
`uv run --frozen python scripts/measure_phase24_projection.py --output docs/evidence/phase24/projection.json`.
GUI betiği `--package-root TARGET` ile noneditable wheel doğrular. Benchmark
10k/100k/1000001 kayıt, üç tekrar;4 logical CPU ve2 native compute thread.
Tam/sample kapsam ve kaynak hash ayrı. Sıcak OS cache; cold OS/minimum fiziksel
donanım veya input→physical frame iddiası yok. Standart locked kapılar korunur.
[ADR-027](adr/027-performance-phase24.md), [kanıt](evidence/PHASE24.md).

Faz24 maliyet paneli görsel kontrolü: `uv run --frozen python scripts/measure_phase24_forecast.py`; gerçek100k hazırlama/worker,1366×768 ve720×560 sarılı metin.

## Faz25

`uv run --frozen python scripts/check_usability.py` yardım alanlarını, ortak
form amaç adlarını ve tamamlanmış temel İngilizceyi denetler; jargon adayları
manuel okunur. `uv run --frozen pytest tests/test_usability.py -q` gerçek
Qt/klavye/tercih/kontrast regresyonudur.
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen python scripts/measure_phase25.py`
beş sentetik senaryoyu gerçek klavye ve worker yollarıyla yürütür;
`--package-root TARGET --output JSON` kurulu noneditable wheel seçer.
`QT_SCALE_FACTOR=2` ve `--layout-only` ayrı başsız DPI/font denemesidir.
Standart kilitli kapılar korunur. AT-SPI/Orca ve insan testi ayrıca açık;
[kanıt](evidence/PHASE25.md), [plan](USER_TEST_PLAN.md).

## Faz26

`uv run --frozen pytest tests/test_security_audit.py tests/test_security_gui.py -q`
sentetik saldırı/parser limit, autosave SIGKILL/ENOSPC, migration ve gerçek QML
kurtarma akışıdır. Tam pytest `--junitxml=docs/evidence/phase26/pytest.xml`
ile kaydedilir; `uv run --frozen python scripts/audit_reliability.py --junit docs/evidence/phase26/pytest.xml --output docs/evidence/phase26/review.json`
gerçek test kimliklerini20 publication checkpoint ve inceleme alanına bağlar.
`uv run --frozen python scripts/measure_phase26.py` ayrı user/network namespace
içinde OS ağsız beş QML senaryosudur; `--package-root TARGET --output JSON`
kurulu wheel yoludur. Kernel user/net namespace izni gerekir; ret başarı
sayılmaz. Standart locked kapılar ve sistem Python kontrolü ayrı korunur.
[ADR-029](adr/029-reliability-phase26.md), [kanıt](evidence/PHASE26.md).

## Veri ekranı düzenlemesi

`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen pytest -q tests/test_data_inspection.py tests/test_data_workspace_gui.py`
bağımsız sütun/describe/unique referanslarını, gerçek QML klavye seçimini,
notların kaydet/aç davranışını ve iptal/eski sonuç korumasını denetler.
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen python scripts/measure_data_inspection.py --output /tmp/veri-ufku-data-inspection`
sekiz geniş/dar ekran görüntüsü ve örnek kaynak hash kontrolü üretir.
`--package-root TARGET` aynı akışı noneditable wheel kurulumu üzerinden çalıştırır;
çıktıdaki `package_file` yüklenen paketi gösterir. Standart kilitli kontroller korunur.
[Kanıt ve sınırlar](evidence/UI_DATA_INSPECTION.md).


Sade import görsel kontrolü: `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_import_simple.py`; gerçek sentetik CSV, yedi geniş/dar Qt görüntüsü ve kaynak SHA256 koruması. `tests/test_import_gui.py::test_basic_import_project_route_advanced_settings_and_success` proje yönlendirmesi, temel/Gelişmiş geçişinde ayar koruması ve gerçek kayıt davranışını doğrular. [Kayıt](evidence/UI_IMPORT_SIMPLE.md).


Veri inceleme iyileştirmesi: `tests/test_delimited.py` tüm dosyada geç gelen karma tür, kesin Decimal/tarih/boolean/eksik ve kimlik korumasını; `test_import_gui.py`20 görünür/30 gerçek importu; `test_data_workspace_gui.py`10005 kayıt üzerinde otomatik tam profil ve sade bilgileri denetler. `measure_import_simple.py --output docs/evidence/ui-data-refinement/import-screens` ve `measure_data_inspection.py --output docs/evidence/ui-data-refinement/screens` gerçek Qt görüntüleri üretir. [Kayıt](evidence/UI_DATA_REFINEMENT.md).

2026-10-10: Profil/tür düzeltmesi: test_delimited/test_data_inspection/test_data_workspace_gui/test_import_gui gerçek Int64 sınırları,10005 kayıt sonrası karışık değer, legacy String tür ayrımı ve byte koruma kontrolünü içerir. Kanıt: evidence/UI_PROFILE_TYPES.md. [Kanıt](evidence/UI_PROFILE_TYPES.md).


## Faz28 denetimi

`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest -q --junitxml=docs/evidence/phase28/pytest-final.xml` gerçek regresyonu üretir. Ardından `.venv/bin/python scripts/audit_phase28.py --junit docs/evidence/phase28/pytest-final.xml --output docs/evidence/phase28/audit.json` salt okunur kod/registry/kanıt/graph envanterini vaka kimliklerine bağlar; envanter faz kabulü değildir. Kaynak ve noneditable kurulu GUI için mevcut `measure_data_inspection.py` ve `--package-root TARGET`; gerçek importer/reopen için `smoke_import_wheel.py` kullanıldı. [Komut/exit/ortam](evidence/phase28/checks.json), [kapılar ve masaüstü deneme adımları](evidence/PHASE28.md). `check_docs.py` eski kaynak checksumunu koruyarak yalnız kayda alınmış tek kullanıcı eklemesini doğrular; Faz29–75 yöntem kapsamı/bağımlılık/alt iş çelişkisini de reddeder.

## Faz29

`tests/test_workspace.py`: tek registry, ayrı işlem destekleri, eksik dependency, iki gerçek Qt/spawn yöntem, bağımsız r/rho0,8 referansı, immutable yeni run, preset/onay/sekme/favori/reopen ve bilinmeyen yöntem readonly. Mevcut statistics/GUI/projects/migration/fold-leakage kontrolleri korunur. Kilitli sync, docs/artifacts/learning/usability, Ruff, pytest/unittest ve offscreen/software kurulu giriş smoke aynı kapılardır. [Kanıt](evidence/PHASE29.md).

## Faz30

`uv sync --locked --group dev`; standart docs/artifacts/learning/usability/Ruff/pytest/unittest/izole entry smoke kapıları korunur. `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen pytest tests/test_advanced_import.py tests/test_advanced_import_gui.py -q` gerçek format/native/metadata/şema/güvenlik/kaynak/iptal/atomik kayıt ve reopen kontrolüdür. `uv run --frozen python scripts/measure_phase30.py --output docs/evidence/phase30/gui` kaynak GUI; `--package-root TARGET` noneditable wheel yolunu doğrular. `uv run --frozen python scripts/measure_phase30_large.py` dokuz10005 kayıt preview200/iptal ölçümü; SAS büyük fixture ölçülmedi. [Karar](adr/031-advanced-import-phase30.md), [kanıt](evidence/PHASE30.md).

`measure_phase30.py` her adaptörde gerçek F1/Escape, odak dönüşü ve
önizleme/proje durumunun korunmasını da denetler; beş yeni çevrimdışı
yardım örneğini açar. Kurulu wheel doğrulamasında `uv pip install --no-deps
--no-index --target TARGET WHEEL` ile ayrı hedef kullanılır; kilitli Python
bağımlılıkları korunur. Betiği ayrı geçici çalışma dizininden
`--package-root TARGET --output ABSOLUTE_OUTPUT` ile çalıştırın.
[2026-10-11 teknik kapanış ve gerçek komut kayıtları](evidence/PHASE30.md#e30-continuation).


## Faz31

Temel locked kurulum aynı kalır. İsteğe bağlı bağlantılar ve gerçek kabul:
`uv sync --locked --group dev --extra connectors`.
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen --extra connectors pytest tests/test_connectors.py tests/test_connector_optional_servers.py tests/test_connector_gui.py -q`.
Gerçek sunucu fixture'ları TLS sertifikası, geçici veri ve salt okunur test
rolünü kurup kapatır; /tmp altında paket binary yolları veya sağlanan ortam
gerekir. Ortam yoksa test skip olur; bu connector kabulü değildir. Socket/D-Bus
izni gerekir. Standart docs/artifacts/learning/usability/Ruff/pytest/unittest
ve kurulu entry smoke korunur. [Ortam/komut/kabul](evidence/PHASE31.md).


Faz32: `.venv/bin/python -m pytest tests/test_data_contracts.py tests/test_data_contracts_gui.py -q`;
GUI için `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software`. Kilitli
CPython3.13.15 kullanılır. docs/artifacts/learning/usability, Ruff check/format,
regresyon, unittest ve kurulu noneditable wheel/offscreen smoke gerçek kapılardır.
[ADR-033](adr/033-data-contracts-phase32.md), [kanıt](evidence/PHASE32.md).


## Faz33

Kilitli CPython3.13.15 `.venv` korunur; bağımlılık/lock değişmedi.
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest -q tests/test_missing_sampling.py tests/test_missing_sampling_gui.py`
core ve gerçek QML/spawn/export/save/reopen/iptal kapısıdır.
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase33.py --output docs/evidence/phase33/source-gui`
kaynak; `--package-root TARGET` ayrı noneditable kurulu wheel yoludur.
Standart docs/artifacts/learning/usability/Ruff check+format/full pytest ve
`.venv/bin/python -m unittest discover -s tests -p test_document_contracts.py`
korunur. Fiziksel/insan/AT/offline install/remote CI ayrı kabul.
[Gerçek kayıt](evidence/PHASE33.md), [karar](adr/034-missing-sampling-phase33.md).


Faz34: `.venv/bin/python -m pytest tests/test_arrays.py tests/test_arrays_safety.py tests/test_arrays_gui.py -q`; `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase34.py --output docs/evidence/phase34/source-gui`. Betik `--package-root TARGET` ile noneditable kurulu wheel doğrular. Kilitli CPython3.13.15; xarray2026.9.0/h5netcdf1.8.1/Zarr3.4.1/Pint0.26.1. Yerel Zarr asyncio socketpair gerektirir; sandbox engeli kabul sayılmaz. Standart docs/artifacts/learning/usability/Ruff/pytest/unittest/installed smoke kapıları korunur. [Gerçek komutlar](evidence/PHASE34.md).


Faz35: `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest -q tests/test_distributions.py tests/test_distributions_gui.py`; kaynak/wheel walkthrough betiği `scripts/measure_phase35.py`. Standart docs/artifacts/learning/usability/Ruff check+format, tam pytest, belge unittest ve kurulu wheel smoke kapıları korunur. [ADR](adr/036-distribution-charts-phase35.md), [kanıt](evidence/PHASE35.md).


Faz36: `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest -q tests/test_multivariate.py tests/test_multivariate_gui.py`; `scripts/measure_phase36.py --output PATH` ve `--package-root TARGET`. Kilitli CPython3.13.15; docs/artifacts/learning/usability, Ruff, tam pytest, belge unittest, noneditable installed-wheel smoke kapıları. [ADR](adr/037-multivariate-charts-phase36.md), [kanıt](evidence/PHASE36.md).


Faz37: `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest -q tests/test_composition.py tests/test_composition_gui.py`; `scripts/measure_phase37.py --output PATH` ve `--package-root TARGET`. CPython3.13.15 locked; docs/artifacts/learning/usability/Ruff/fullpytest/unittest/installedsmoke kapıları. [ADR038](adr/038-composition-charts-phase37.md), [kanıt](evidence/PHASE37.md).


Faz38: locked `.venv/bin/python -m pytest -q tests/test_geo.py tests/test_geo_gui.py tests/test_geo_network.py`; gerçek yerel TLS sunucusu için localhost socket izni gerekir. Core gerçek GeoJSON/GPKG/Shapefile/GeoParquet/GeoTIFF fixture, CRS/mesafe/alan/join/Moran referansı ve raster window spy; GUI preview/apply/undo ve explicit online read/reopen. `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase38.py --output docs/evidence/phase38/source-gui`; aynı komutta `--package-root TARGET --output docs/evidence/phase38/wheel-gui` noneditable wheel yollarını çalıştırır. [ADR039](adr/039-geospatial-phase38.md), [kanıt](evidence/PHASE38.md).

Faz39: `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest -q tests/test_dashboard.py tests/test_dashboard_gui.py`; gerçek kaynak/wheel QML akışı `scripts/measure_phase39.py --output PATH` ve `--package-root TARGET`. Betik dört export, geniş/dar canvas, PDF font/text kontrolü, save/reopen, F1/Escape, iptal ve stale sürüm kanıtı üretir. `.venv/bin/python -m hatchling build -t wheel -d PATH`; `uv pip install --no-deps --target TARGET WHEEL`. Standart docs/artifacts/learning/usability, `ruff check src tests scripts`, `ruff format --check src tests scripts`, tam pytest ve `python -m unittest discover -s tests -p test_document_contracts.py` kapıları korunur. [ADR040](adr/040-dashboard-figure-phase39.md), [kanıt](evidence/PHASE39.md).

## Faz40 modeller

Hedefli: `.venv/bin/python -m pytest -q tests/test_statistical_models.py tests/test_statistical_models_gui.py`.
Gerçek GUI: `.venv/bin/python scripts/measure_phase40.py --output /tmp/phase40-gui`.
Noneditable wheel: aynı komuta `--package-root /tmp/veri-ufku-phase40-installed` eklenir.
Kilitli statsmodels0.15.0; [kapsam/sınırlar](adr/041-statistical-models-phase40.md).

## Faz41 resampling

`.venv/bin/python -m pytest -q tests/test_resampling.py tests/test_resampling_gui.py`
hedefli kontrollerdir. Gerçek GUI/export: `.venv/bin/python scripts/measure_phase41.py --output /tmp/phase41-gui`.
Noneditable wheel için `--package-root /tmp/veri-ufku-phase41-final-installed`.
[Bilimsel sözleşme ve bütçe](adr/042-resampling-phase41.md).


Faz42: `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest -q tests/test_experiments.py tests/test_experiments_gui.py`; gerçek source/wheel `scripts/measure_phase42.py --output PATH` ve `--package-root TARGET`. Kilitli CPython3.13.15; docs/artifacts/learning/usability/Ruff/fullpytest/unittest/installed smoke kapıları korunur. [ADR043](adr/043-experiments-phase42.md), [kanıt](evidence/PHASE42.md).


Faz43: `.venv/bin/python -m pytest -q tests/test_bayes.py tests/test_bayes_gui.py`; `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase43.py --output PATH` ve `--package-root TARGET`. Optional bayes extra sabit, kaynak/wheel/GUI/offline CPU doğrulaması; docs/artifacts/learning/usability/Ruff/fullpytest/unittest kapıları. [ADR044](adr/044-bayes-phase43.md).

## Faz44 kontrolleri

`.venv/bin/python -m pytest -q tests/test_causal.py tests/test_causal_gui.py` bilinen sentetik etki, positivity/backdoor/collider/mediator,fold isolation,matchingRowId,DiDpretrend/IVweak, gerçekQMLworker/help/cancel/save/export/reopen. `.venv/bin/python scripts/measure_phase44.py --output docs/evidence/phase44/source-gui` source; `--package-root TARGET` noneditablewheel aynı akış. Kilitli docs/artifacts/learning/usability/Ruff kapıları; [kanıt](evidence/PHASE44.md).

## Faz45 kontrolleri

`.venv/bin/python -m pytest -q tests/test_survival.py tests/test_survival_gui.py` küçükelleKM/riskset/CIF,invalidduration/entry,censoringgate,lognormalAFTMLE/score,independentCoxpartiallikelihood/Breslow/Efronbaseline,safe modelreuse,source/units/RowId, gerçekQtworker/help/cancel/export/save/reopen. `.venv/bin/python scripts/measure_phase45.py --output docs/evidence/phase45/source-gui` gerçeksourceakışı; `--package-root TARGET` noneditableinstalledwheel. LockedCPython3.13.15;docs/artifacts/learning/usability/Ruff ve14belgeunit; [Faz45](evidence/PHASE45.md).

## Faz46 kontrolleri

`.venv/bin/python -m pytest -q tests/test_dimensions.py tests/test_dimensions_gui.py` PCA/SVDreference,non-negative/missing/CSRguards,transform/inverse,safeJSON,originalColumnIdstability,inner/outer/heldoutfitisolation,sequentialcandidatepipeline,actualQtworker/help/cancel/export/save/reopen/stale. OptionalUMAPabsentcompute skip testeddeğil; unavailableUItestayrı. `.venv/bin/python scripts/measure_phase46.py --output docs/evidence/phase46/source-gui` actualsource;`--package-root TARGET` noneditablewheel. LockedCPython3.13.15/docs/artifacts/learning/usability/Ruff/14belgeunit. [Kanıt](evidence/PHASE46.md).

## Faz48 kontrolleri

Kilitli `.venv/bin/python -m pytest -q tests/test_model_families.py tests/test_model_family_support.py tests/test_model_families_gui.py`; GUI için `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software`. Per-model gerçek dense/CSR/weights/missing/OOF/persistence/GUI; convergence/n² gate ve actual cancel/wall expiry. `.venv/bin/python scripts/measure_phase48.py --output PATH`; `--package-root TARGET` noneditable installed wheel; `--case svm:classification` affected-case replay. Standard docs/artifacts/learning/usability/Ruff/14documentunit ve installed smoke korunur. Optional backend yoksa unavailable guard başarısı compute doğrulaması değildir. [Kapsam, komut grupları ve gerçek sayılar](evidence/PHASE48.md).

## Faz49 kontrolleri

`.venv/bin/python -m pytest -q tests/test_search.py tests/test_search_store.py tests/test_search_gui.py`; GUI için `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software`. `scripts/measure_phase49.py --output PATH` kaynak; `--package-root TARGET` noneditable wheel. Kilitli CPython3.13.15; docs/artifacts/learning/usability/Ruff/documentunittest/installed entry smoke. Source poison/reference/spies/joint plans/cumulative budgets/tamper/rollback/safe archive/export ve gerçek GUI/model handoff/final test defteri/cancel-resume. Optional absent guard compute başarı değildir;[gerçek komut grupları ve sayılar](evidence/PHASE49.md).

## Faz50 kontrolleri

Kilitli `.venv/bin/python` CPython3.13.15 ile
`.venv/bin/pytest -q tests/test_uncertainty.py tests/test_search.py tests/test_search_store.py tests/test_model_families.py tests/test_model_family_support.py tests/test_regression.py tests/test_classification.py tests/test_lifecycle.py tests/test_validation.py tests/test_learning_tree.py`;
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/pytest -q tests/test_uncertainty_gui.py tests/test_classification_gui.py tests/test_lifecycle_gui.py tests/test_validation_gui.py tests/test_usability.py`.
`.venv/bin/python scripts/measure_phase50.py --output docs/evidence/phase50/source-gui`
real Qt/spawn training/calibration/validation, safe package export/import/predict,
zero-fit final journal/reopen; binary cost/constraints/cancel/newfile ve joint
group-time path; 1366/1000 render ve safe JSON/model artifact kopyaları. Aynı betik
`--package-root /tmp/veri-ufku-f50-installed --output docs/evidence/phase50/wheel-gui`
ile byte-doğrulanmış noneditable wheel'i kullanır. Paket build:
`.venv/bin/python -m hatchling build -t wheel -d /tmp/veri-ufku-f50-wheel`.
Std docs/artifacts/learning/usability/Ruff check/format ve freshXDG installed smoke
korunur. Formal physical/human/AT/minHW/cleanoffline/remoteCI ayrı, burada koşmadı.
[Karar](adr/051-uncertainty-phase50.md), [kanıt](evidence/PHASE50.md).

## Faz51 kontrolleri

Kilitli `.venv/bin/python` CPython3.13.15. Core:
`.venv/bin/pytest -q tests/test_explanation.py tests/test_uncertainty.py tests/test_search.py tests/test_search_store.py tests/test_model_families.py tests/test_model_family_support.py tests/test_regression.py tests/test_classification.py tests/test_lifecycle.py tests/test_validation.py tests/test_learning_tree.py`.
GUI/regression:
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/pytest -q tests/test_explanation_gui.py tests/test_uncertainty_gui.py tests/test_lifecycle_gui.py tests/test_classification_gui.py tests/test_validation_gui.py tests/test_usability.py`.
`.venv/bin/python scripts/measure_phase51.py --output docs/evidence/phase51/source-gui`;
`--package-root /tmp/veri-ufku-f51-installed --output docs/evidence/phase51/wheel-gui`
noneditable byte-verified wheel. Eight real native explanation/scenario paths plus
cancel/SHAP-unavailable/no-overwrite; safe maskedJSON/atomic archive/reopen/help,
1366/1000width actual Qt/CPU spawn. Runtime optionalSHAPabsent is unavailable
control proof, not SHAP compute evidence. Build `.venv/bin/python -m hatchling build -t wheel -d /tmp/veri-ufku-f51-wheel`.
Standard docs/artifacts/learning/usability/Ruff check+format/document unit/installed
fresh4XDG smoke retained. Formal physical/human/AT/minHW/cleanoffline/remoteCI
and whole-repo regression are separate. [Kanıt](evidence/PHASE51.md),
[ADR052](adr/052-explanation-phase51.md).

Faz52 DEC52-01: mevcut run/test defteri üzerinde yerel registry; bounded native yol ve sınırlar [kanıt](evidence/PHASE52.md). Optional tracking unconfigured/notvalidated; fiziksel silme kapalı, arşiv disk boşaltmaz.

Faz52 gerçek komutlar: `.venv/bin/pytest -q tests/test_experiment_registry.py`; GUI:
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/pytest -q tests/test_experiment_registry_gui.py`.
`scripts/measure_phase52.py --output PATH` ve `--package-root /tmp/veri-ufku-f52-installed`:
noneditable installed actual QML flow, synthetic data, source protected, model/test journal.
Locked runtime, docs/artifacts/learning/usability/Ruff/unit/installed smoke gates preserved.
[332+332/13 regression command evidence](evidence/phase52/verification.json).

Faz53 DEC53-01 native temporal slice:19 capabilities,chronological/panel/availability/MASE/proper forecast scores, safeJSON/journal;[kanıt](evidence/PHASE53.md). Formal prior gates separate; bounded templates/out-of-source prediction limitations explicit.

Faz53 kontrolleri: `.venv/bin/pytest -q tests/test_temporal.py tests/test_time_series.py tests/test_experiment_registry.py`; GUI: `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/pytest -q tests/test_temporal_gui.py tests/test_time_series_gui.py tests/test_experiment_registry_gui.py tests/test_usability.py`. Gerçek 19 yol: `.venv/bin/python scripts/measure_phase53.py --output PATH`; noneditable wheel için `--package-root TARGET`. Wheel: `.venv/bin/python -m hatchling build -t wheel -d /tmp/veri-ufku-f53-wheel`. Çapraz faz core kapsamı, komutlar ve gerçek sayılar [verification](evidence/phase53/verification.json); docs/artifacts/learning/usability/Ruff/14belge unit [gates](evidence/phase53/gates.json). Fiziksel/insan/AT/minimum donanım/temiz offline kurulum/remoteCI ayrı.

Faz54 DEC54-01 regular signal ve recording blok pencereleri:13 bounded native template teknik doğrulandı; resmî kabul ayrı. Offline zero-phase, amplitude/PSD/availability ve kaynak kimliği açık. [Kanıt](evidence/PHASE54.md);Faz55 yetkisi yok.

Faz54 komutları: `.venv/bin/pytest -q tests/test_signals.py`; GUI için `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/pytest -q tests/test_signals_gui.py tests/test_temporal_gui.py tests/test_time_series_gui.py tests/test_experiment_registry_gui.py tests/test_usability.py`. Actual source: `.venv/bin/python scripts/measure_phase54.py --output PATH`; noneditable wheel için `--package-root TARGET`. `.venv/bin/python -m hatchling build -t wheel -d /tmp/veri-ufku-f54-wheel`. Core kapsamı [verification](evidence/phase54/verification.json); docs/artifacts/learning/usability/Ruff/14documentunit [gates](evidence/phase54/gates.json). Fiziksel/insan/AT/minimum donanım/temiz offline installer/remoteCI ayrı.

Faz55 DEC55-01 bounded native NLP:12 bounded native records teknik doğrulandı; resmî kabul ayrı; transformer/spaCy/ONNX unsupported. Static/literal/linear limits, original offset ve versioned human review açık. [Kanıt](evidence/PHASE55.md);Faz56 yetkisi yok.

Faz55 gerçek komutlar: `.venv/bin/pytest -q tests/test_nlp.py tests/test_text.py -k 'not real_https'`; GUI: `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/pytest -q tests/test_nlp_gui.py tests/test_text_gui.py tests/test_experiment_registry_gui.py tests/test_usability.py`. `.venv/bin/python scripts/measure_phase55.py --output PATH`; `--package-root TARGET` noneditable wheel. Build `.venv/bin/python -m hatchling build -t wheel -d /tmp/veri-ufku-f55-wheel`. Source TLS: `.venv/bin/pytest -q tests/test_nlp.py -k real_https` localhost socket sandbox approval requires. [Gerçek kapsam/sayılar](evidence/phase55/verification.json),[docs/artifacts/learning/usability/Ruff/14documentunit](evidence/phase55/gates.json). Neural production benchmark/wheel network/desktop/human/AT/installer/remoteCI ayrı yapılmadı.

## Faz56 CPU tensor motoru

Optional backend: `uv sync --locked --group dev --all-extras` mevcut Bayes/connectors
ortamını da korur; yalnız `--extra neural` diğer optional paketleri kaldırabilir.
Runtime startup otomatik indirme yapmaz. CPU2.13.0+cpu/CPython3.13.15 exact; GPU kapalı.
`.venv/bin/pytest -q tests/test_neural.py tests/test_neural_gui.py`;
`scripts/measure_phase56.py --output ABS_DIRECTORY` kaynak gerçek QML/spawn/checkpoint/
reopen/new-data prediction/pause/resume/cancel; `--package-root NONEDITABLE` aynı kurulu wheel
akışıdır. Ortak docs/artifacts/learning/usability/Ruff check+format ve ilgili validation/search/
lifecycle/registry regresyonları gerekir. [Kanıt](evidence/PHASE56.md).

## Faz57 yerel görüntü

`.venv/bin/pytest -q tests/test_vision.py -k 'not real_https'` gerçek immutable adapter,
CPU CNN/transfer/pixel detection/pixel segmentation, metric reference, fold izolasyonu
ve review/export. TLS: `.venv/bin/pytest -q tests/test_vision.py -k real_https`; gerçek
localhost TLS socket sandbox izni gerekir. Model indirme uygulamada açık opt-in'dir.
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase57.py --output ABS_DIRECTORY`
beş gerçek QML/CPU aşama/reopen/new-data ve review/export/cancel; `--package-root TARGET`
noneditable wheel aynı akış. GUI geliştirici fixture4GiB; default2GiB korunur.
Ortak docs/artifacts/learning/usability/Ruff/14 documentunit, ilgili import/source/neural/
NLP/validation/registry testleri ve installed smoke gerekir. [Kapsam/kanıt](evidence/PHASE57.md).

## Faz58 yerel ses

SoundFile0.13.1 core, optional `audio-speech` extra Vosk0.3.45. `uv sync --locked --group dev --all-extras`
önceki optional backendleri korur; model ağırlığı indirilmez. `.venv/bin/pytest -q tests/test_audio.py tests/test_audio_gui.py`;
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase58.py --output ABS_DIRECTORY`
actual native features/classification/reopen/predict/unavailable/cancel; `--package-root TARGET`
noneditable wheel. Küçük Vosk model yok; STT runtime test edilmiş sayılmaz. Ortak kapılar ve
ilgili signals/vision/neural/validation/import/registry kontrolleri gerekir. [Kanıt](evidence/PHASE58.md).

Faz59 DEC59-01 bounded native CPU recommendation ve ayrı query-group ranking;
[gerçek kapsam/kanıt](evidence/PHASE59.md),[ADR060](adr/060-recommendation-phase59.md).
Tek registry/journal; resmî kabul ayrı; Faz60 başlatılmaz.

Faz59 gerçek kontroller: `.venv/bin/python -m pytest -q tests/test_recommendation.py`;
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase59.py --output docs/evidence/phase59/source-gui`.
Aynı script `--package-root /tmp/veri-ufku-f59-installed` ile kurulu wheel'i doğrular;
`--task ranker` tek son GUI seçimi. Önceki kanıtı yeniden üretirken ayrı output yolu
kullanın. [Kaydedilmiş komut/ortam/sonuç](evidence/PHASE59.md).

Faz60: `.venv/bin/python -m pytest -q tests/test_patterns.py`;
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase60.py --output /tmp/vu60-gui`.
Kurulu wheel için `--package-root /tmp/veri-ufku-f60-installed-final`; `--only` pytest
filtre ifadesiyle dar gerçek GUI kontrolü. Eski kanıta yazmayın; ayrı output seçin.
[Kaydedilmiş gerçek sonuçlar](evidence/PHASE60.md).

Faz61 `.venv/bin/python -m pytest -q tests/test_graphs.py`;
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase61.py --output /tmp/vu61-gui`.
Kurulu wheel için `--package-root /tmp/veri-ufku-f61-installed`; `--only` dar GUI filtresi.
Ayrı node/edge tablosu fixture'ı geçici4GiB config seçer; uygulama varsayılanı değişmez.
Kaydedilmiş eski output üstüne yazmayın; [gerçek sonuçlar](evidence/PHASE61.md).

Faz62 DEC62-01 açık talimatla bounded local replay, incremental scaler/SGD, prequential/checkpoint ve ayrı özel hedefler; [kapsam/kanıt](evidence/PHASE62.md), [ADR063](adr/063-streams-phase62.md). PU/broker unavailable; default2GiB GUI kapısı açık,4GiB işlevsel test ayrı. Resmî kabul sürüyor/deneysel/isteğe bağlı; Faz63 başlatılmaz.

Faz63 DEC63-01: sınırlı numeric GUI profile Python/SQLite/notebook reference-only export ve explicit fresh Python process; [kanıt](evidence/PHASE63.md),[ADR064](adr/064-code-bridge-phase63.md). OS sandbox/managed Jupyter yok; resmî sürüyor/deneysel/isteğe bağlı, önceki kapılar korunur. Faz64 başlatılmaz.

Faz64 DEC64-01: bounded typed DAG source/transform/quality/analysis/train/predict/export, aynı GUI/CLI worker ve batch/sweep/dry-run. [Kanıt](evidence/PHASE64.md), [sözleşme/CLI kullanımı](adr/065-typed-workflow-phase64.md). Schedule mevcut değil; resmî kabul ayrı, önceki kapılar korunur. Faz65 başlatılmaz.

Faz64 kontrolleri: `.venv/bin/python -m pytest -q tests/test_workflow.py`;
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase64.py --output PATH`;
aynı komut `--package-root TARGET` ile noneditable wheel. `--only` dar GUI filtresidir.
Gates docs/artifacts/learning/usability/Ruff ve14 documentunit; ilgili Operations/recipes,
ProjectStore/neural journal/experiment registry ve source/installed core koşuları ayrı kaydedilir.
Aynı çıktı dizinine eski kanıtın üstüne yazmayın. CLI `python -m veri_ufku.operations.workflow_cli --help`;
proje tek writer, ağ/schedule yoktur. Native frame kimlikleri korunur; kullanıcı Parquet export sistem kolonlarını çıkarır.

Faz65 DEC65-01 açık talimat: kayıtlı source/dataset/operation/analysis/model/report lineage, reference-only veya explicit data-inclusion safe bundle ve sınırlı exact/numeric verifier. [Kapsam/kanıt](evidence/PHASE65.md), [sözleşme](adr/066-reproducibility-phase65.md). Geçmiş provenance uydurulmaz; genel row traversal/model rerun yok; önceki resmî kapılar ayrı, Faz66 başlatılmaz.

Faz65 kontrolleri: `.venv/bin/python -m pytest -q tests/test_repro.py`;
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase65.py --output PATH`;
kurulu noneditable wheel için `--package-root TARGET`; `--only` dar pytest seçimi,
`--view editor` lineage diyagramı screenshot'u. Ayrı kanıt dizini kullanın.
Ortak docs/artifacts/learning/usability/Ruff check/format/14 documentunit kapıları,
ProjectStore/operations/relational/workflow/exports/registry/code bridge ilgili regresyonu.
Worker parent-validated immutable envelope/pinned paths alır; ProjectStore/Qt/ACTIVE almaz.
Bundle metadata açma otomatik rerun/import/exec yapmaz. Silme/GC bu kapsamda yok.

Faz66 DEC66-01: [sözleşme](adr/067-compute-budgets-phase66.md),
[gerçek kapsam/kanıt](evidence/PHASE66.md). `.venv/bin/pytest -q tests/test_compute_budget.py tests/test_jobs.py tests/test_performance.py tests/test_code_bridge.py`;
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase66.py --output YENI_DIZIN`;
noneditable wheel için `--package-root TARGET`. Optional Dask2026.8.0 izole dizini
PYTHONPATH başına eklenip `tests/test_compute_budget.py` ve
`scripts/measure_phase66.py --dask --output YENI_DIZIN` çalıştırılır;
Dask yoksa skip gerçek runtime doğrulaması değildir. Remote/GPU runtime kapalıdır.
Kaynak ve wheel selected regresyon/gates sayıları verification.json içinde;
standart docs/artifacts/learning/usability/Ruff/14documentunit kapıları korunur.

Faz66 son dar tuning walkthrough: `scripts/measure_phase66.py --bounded-search-4gib --output YENI_DIZIN`;
`.venv/bin/python`/offscreen env ile çalıştırın; aynı `--package-root TARGET` desteklenir.
Bu test açık4GiB/tek-aday/curves-off kullanır; varsayılan2GiB veya120s iki-aday fail
sonucunu başarıya çevirmek için varsayılan değiştirmez. Son package60şar focused,
30şar cache/repro ve pidfd/optional backend sonuçları E66 içinde ayrı kayıtlıdır.

Faz67 DEC67-01: [sözleşme/CLI/API kullanımı](adr/068-model-monitoring-phase67.md),
[kanıt](evidence/PHASE67.md). `.venv/bin/pytest -q tests/test_monitoring.py`;
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase67.py --output YENI_DIZIN`;
noneditable wheel için `--package-root TARGET`, dar seçim `--only`.
`tests/test_monitoring_api.py` gerçek loopback socket ister; sandbox izni yoksa
başarı/skip diye raporlanmaz, izinli ortamda ayrı çalıştırılır. Testler ephemeral
auth kullanır, Secret Service provisioning kabulü ayrı. Standart docs/artifacts/
learning/usability/Ruff/14documentunit kapıları; core/focused/walkthrough sayıları E67.


Faz68: `.venv/bin/python -m pytest tests/test_scenarios.py tests/test_monitoring.py tests/test_workspace.py`; gerçek GUI için `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase68.py --output YENI_DIZIN`, kurulu wheel için `--package-root TARGET`. Ortak kaynak/bütçe, docs/artifacts/learning/usability/Ruff ve belge sözleşmesi kapıları geçerli. GUI açılışı hesap başlatmaz; model senaryosu4GiB ayrı ölçülür.


Faz69 native `.venv/bin/python -m pytest tests/test_learning_lab.py tests/test_learning.py tests/test_learning_tree.py`; gerçek GUI `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase69.py --output YENI_DIZIN`, noneditable wheel için `--package-root TARGET`. Tek walkthrough10dersi, dirty kullanıcı proje hashleri, cancel/reopen/progress opt-out ve iş akışı dönüşünü sınar. check_learning tüm403coverage ve DAG/version link kapısıdır. Standart docs/artifacts/learning/usability/Ruff/14documentunit geçerli.


## Faz70 rapor oluşturucu

Kaynak native: `.venv/bin/python -m pytest tests/test_report_builder.py tests/test_code_bridge.py -q`.
GUI: `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase70.py --output /tmp/veri-ufku-phase70-gui`.
Kurulu wheel için aynı komuta `--package-root /ABS/NONEDITABLE/INSTALL` eklenir.
Script yeni geçici projelerle gerçek GUI oluştur/export/cancel/reopen ve PDF render
çalıştırır; fiziksel veya insan/AT kabulü değildir. Basic2GiB/model+chart4GiB ayrıdır.
[Karar](adr/071-report-builder-phase70.md),[tüm gerçek kontroller](evidence/PHASE70.md).


## Faz71 yerel review/share

Native: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_share.py -q`.
Gerçek GUI: `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase71.py --output /tmp/veri-ufku-phase71-gui`.
Noneditable wheel için `--package-root /ABS/INSTALL` ekleyin. Script2GUI vakası:
metadata/sample2GiB ve full4GiB; ephemeral source/project, export/diff/note/fork/cancel/reopen.
Yüklenen veri/kullanıcı projesi değiştirilmez. [Karar](adr/072-local-review-sharing-phase71.md),
[gerçek sonuçlar](evidence/PHASE71.md). Fiziksel/human/AT/minHW kabulü değildir.

## Faz72 privacy kontrolleri

Kilitli `.venv` ile `tests/test_privacy.py` bounded redaction/HMAC/Fernet/journal/
cleanup/lineage; `tests/test_privacy_gui.py` gerçek QML/spawn/onay/export/cleanup/
help/cancel/reopen yoludur. `scripts/measure_phase72.py --output PATH` source,
`--package-root TARGET` kurulu wheel aynı akışı çalıştırır. GUI default2GiB sınırına
yakındır; minHW garantisi değildir. `tests/test_privacy_keyring.py` gerçek Secret
Service daemon yoksa **skip**, test edildi sayılmaz; opsiyonel
`VERI_UFKU_TEST_KEYRING_DAEMON` yalnız test ortamında daemon yoludur, key/fallback
kaynağı değildir. `privacy` extra cryptography50.0.2/keyring25.7.0; temel GUI optional
backend olmadan açılır. [Gerçek komut ve kanıtlar](evidence/PHASE72.md).

## Faz73 plugin SDK

Kilitli `.venv`: `tests/test_plugins.py` API/manifest/trust/env/hash/shape/RowId/
Provenance/failure/cancel/timeout/archive/readonly/quota kontrolleri; gerçek UI
`tests/test_plugins_gui.py`. `scripts/measure_phase73.py --output PATH` veya
`--package-root TARGET` installed wheel aynı akışı ölçer. Bağımsız author testi:

```sh
.venv/bin/python -m veri_ufku.plugins.contract_test --manifest examples/plugins/mean/manifest.json --request examples/plugins/mean/request.json --trust-code
```

Bu komut trusted Python çalıştırır, sandbox değildir. SDK native integration
sınırları, exact dependency ortamı ve test revision ayrımı [E73](evidence/PHASE73.md),
[API sözleşmesi](adr/074-plugin-sdk-phase73.md) ve [örnek paket](../examples/plugins/mean/README.md).
Import açılışı/manifest inspect kod çalıştırmaz; testlerde yalnız sentetik trusted
kod kullanılır. Bütün plugin türlerinde full native adapter testi yapıldığı
iddia edilmez; non-stat türlerde data contract/archive doğrulanır.


## Faz74 kontrolleri

Core install `uv sync --locked --group dev`; tüm geçmiş optional testler için
`--all-extras`. `scripts/generate_environment_profile.py` uv.lock'tan exact closure
üretir; `scripts/release_inventory.py --output /tmp/core-sbom.json` çevrimdışı inventory,
`--scan --online` explicit public package metadata advisory sorgusudur. Ağsız veya
başarısız scan clean değildir. Seçili extra için tekrar `--extra NAME` kullanılabilir.

`.venv/bin/python -m pytest -q tests/test_environment_distribution.py tests/test_environment_gui.py tests/test_packaging.py`
ve standart docs/artifacts/learning/usability/Ruff/format/14document kapıları.
`scripts/measure_phase74.py --output PATH` source; `--package-root TARGET` kurulu
wheel için gerçek GUI/render/worker/export/import/cache/update-plan/help/cancel.
`scripts/build_flatpak.py --output PATH` core; explicit `--extra` professional profili.
Paket launcher `--environment-smoke` CPU/no-download fixture ve migration çalıştırır.
`scripts/portal_smoke74.py --installation PATH --output PATH` yalnız /tmp izole
FLATPAK_USER_DIR kurulumundan gerçek Documents grant/worker yolunu sınar.
Fresh application installation, önceden kurulu runtime ile temiz OS değildir.
Komut/log/hash ve tüm sınırlar [E74](evidence/PHASE74.md) içinde.

## Faz75 bounded son denetim

Kilitli `.venv` CPython3.13.15 ve gerçek kurulu backendler kullanılır.
`scripts/benchmark75_plan.py` açık node seçimini tutar; model download/ağ yoktur.
`.venv/bin/python scripts/benchmark75.py --output /tmp/f75-source` compute;
`--kind gui --output /tmp/f75-gui` gerçek QML/spawn; `--package-root /tmp/installed-wheel`
noneditable wheel. `--ram-gib 4` yalnız açık sentetik `/tmp/pytest` config profilidir;
varsayılan2GiB testinin yerine geçmez. Runner1..900s timeoutta kendi process group'unu
sonlandırır, timeout başarı değildir; aynı output group yeniden yazılmaz.

`benchmark75_evidence.py` sentetik fixture/artifact/test SHA256, reference assertions,
numeric actual/reference/absolute tolerance/relative tolerance/assumptions ve GUI
screenshot'larını kaydeder. Kullanıcı projesi üzerinde çalıştırılmaz. Süreler birden
çok audit job'u olan geliştirici makinesindedir; controlled perf/minHW karşılaştırması
değildir. İlk hatalar ayrı klasörde kalır; yeni deneme etiketiyle tekrarlanır.

`audit_phase75.py --output PATH --junit ABS_XML ... --update-matrix` tek registry ve
requirement matrisi üstünden76faz/416capability/source/help/test/evidence hash denetimi.
Current JUnit phase-associated module witness, direct tüm alt yöntem kanıtı değildir.
`finalize_phase75.py --output docs/evidence/phase75` gerçek kayıtları dedup ederek
source/wheel/GUI/failed process gruplarını ayrı özetler, candidate hash/parity denetler.
Expert worksheet insan alanı doluysa audit overwrite reddeder; yeni output klasörü seçin.
Testler `tests/test_release_benchmarks.py`, `tests/test_release_benchmark_gui.py`,
`tests/test_release_audit.py`; standart docs/artifacts/learning/usability/Ruff/format/
14document ve uygun noneditable wheel kapıları sürer. [Son gerçek kanıt](evidence/PHASE75.md).

## Kapsamlı UI/UX yenileme — 2026-10-17

[İnceleme, düzeltme ve gerçek sonuçlar](evidence/UI_RENEWAL.md).
`.venv/bin/python -m pytest -q tests/test_ui_renewal.py tests/test_gui.py
 tests/test_release_benchmark_gui.py` ortak kabuk, form yaşam döngüsü,
sayfalı tablo/clipboard/RowId ve gerçek temizleme→grafik→export→reopen yoludur.
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python
 scripts/measure_ui_renewal.py --output /tmp/vu-ui-new` yeni bir klasöre sekiz
bölüm ve720px/%200/açık/koyu görüntüleri yazar. Mevcut output dizinini reddeder;
izole XDG kullanır. Tekil startup/RSS gözlemi insan testi veya minHW benchmark değildir.
`VERI_UFKU_UI_EVIDENCE=/tmp/vu-ui-actual` ilgili GUI testlerinde gerçek tablo,
rapor formu, ayarlar ve hesaplanan histogram ekran görüntülerini etkinleştirir.
Yeni çeviriler `en.ts`/`en.qm` içinde; QML Türkçe kaynak dili korunur.
WorkspacePanel yükledikten sonra formu yok etmez; component ilk yüklemede
Validation/Preparation mevcut controller planını okumalıdır. Global serializer
importu eklemeyin: safe model IO açık save/load çağrısında yüklenir.
