# Faz 01 kanıt kaydı

2026-10-06; ENV-01. CPython 3.13.15/PySide6 6.11.2, CachyOS x86_64; Qt offscreen/software. Faz durumu doğrulandı, uygulanan yetenekler deneysel; son kabul kaydı e01-phase-acceptance. Sonraki faz başlamadı.

<a id="e01-package"></a>

## package

pyproject.toml, uv.lock, app.py; kilitli cache kurulumu ve ikinci temiz venv. Python wheel noneditable yüklenip gerçek giriş noktası smoke geçti. Tam offline dağıtım paketi yok.

<a id="e01-boundaries"></a>

## boundaries

UI/domain/services/importers/storage/jobs/learning ayrıdır; import/depo/analitik özellikleri hazır gösterilmez. XDG config ve 0600 dönen log; config ve error-redaction testleri.

<a id="e01-jobs"></a>

## jobs

tests/test_jobs.py: bağımsız 0..29 toplamı=435, farklı CPU PID, I/O byte toplamı/cleanup, UUID job ve immutable bound provenance; kapatma/kuyruk/bütçe testleri.

<a id="e01-cancel"></a>

## cancel

CPU ve I/O iptal, CPU grace/terminate, queued iptal, sonuç yok; kapanış CPU/I/O/queued temizliği ve yeni submit reddi. Gözetici dosya hatası güvenli hata testidir.

<a id="e01-stale"></a>

## stale

Binding dataset/config eşleşmesi result_for ve UI controller aktarımında zorunludur; hem veri hem config uyumsuzluğu test edilir. QML çalışırken config değişimi eski sonucu bastırır.

<a id="e01-progress"></a>

## progress

Bilinen birimler done/total; bilinmeyen fixture total=None ve QML busy indicator. Uydurma yüzde yok.

<a id="e01-gui"></a>

## gui

tests/test_gui.py gerçek QQmlApplicationEngine/QQuickWindow, Qt sinyalleri, CPU sırasında timer, cancel, hata/takip kimliği, closewait ve İngilizce/Türkçe katalog kontrolü. Başsız screenshot phase01-headless.png; fiziksel desktop kanıtı değil.

<a id="e01-contracts"></a>

## contracts

Capability whitelist, schema v1, ComputeBudget validation/admission/RSS/temp/wall/concurrency; immutable provenance hash/environment/method/scope. İptal/disk/RAM/uygunsuz spec testleri.

<a id="e01-translation"></a>

## translation

QML qsTr ve Python Shell translate, bundled tr.qm; İngilizce kaynak ile locale switch başlangıçta. TS 46 çeviri; katalog wheel içinde, ağ gerekmez.

<a id="e01-ci"></a>

## ci

Workflow locked install, docs/artifact, Ruff check/format, pytest ve kurulu entry smoke içerir. Yerel aynı kontroller phase01-checks.txt; 32 test geçti. Sunucu koşusu ayrı açık gereksinimdir.

<a id="e01-measurement"></a>

## measurement

phase01-measurements.json ve scripts/measure_phase01.py: 20 sıcak açılış,100 Qt fare olayı, CPU1/IO2, RSS/temp ve tek iptal örneği. PERFORMANCE sınırları kaydeder.

<a id="e01-desktop"></a>

## desktop

KULLANICI MASAÜSTÜ KONTROLÜ DOĞRULANDI. Kullanıcı açılış/CPU/I/O/belirsiz ilerleme iptal ve tamamlanma denemelerine ek olarak görev sırasında yapılandırma değişimiyle eski sonucun uygulanmaması, anlaşılır hata ve takip kimliği gösterimi, aktif görevde pencerenin takılmadan kapanması için verilen üç kontrolün hepsinin çalıştığını bildirdi. Başsız testler teknik log izlenebilirliğini ayrıca doğrular. Sandbox Wayland/X11 başarısız denemeleri tarihsel olarak phase01-desktop.txt içinde korunur; kullanıcı masaüstünün başarısız olduğu anlamına gelmez. Kabul bu bildirilen senaryolarla sınırlıdır.

<a id="e01-remote"></a>

## remote

Tarihsel ilk koşu kaydı; güncel başarılı koşu aşağıdaki e01-remote-success kaydındadır. Kullanıcı projeyi b356f1ebe6e67299590e9568eccd33da6c9236ef commit kimliğiyle GitHub main dalına gönderdiğini bildirdi. CI koşusu 37499686960 failure ile bitti. Git metaverisi ve origin artık mevcut; .git ajan için salt okunur. Workflow ve yerel koşu remote başarı kanıtı değildir.

İlgili komut/log kanıtı: `phase01-checks.txt`. Yerel geliştirme wheel lisansı/hash kaydı tools/wheels/manifest.json ve ADR-005. Kaynak promptu değiştirilmedi.

Gerçek desktop deneme çıktısı `phase01-desktop.txt`; doğrulanan kaynak dosyaların SHA256 kaydı `phase01-source.sha256`. Son ölçüm aynı kaynak kodundan alındı; PERFORMANCE ham JSON değerlerini yansıtır.

<a id="e01-user-desktop"></a>

## Kullanıcının masaüstü kontrolü

2026-10-06; ENV-USER-01; kanıt türü kullanıcı tarafından bildirilen manuel masaüstü denemesi. Kullanıcı CPU denemesinin çalıştığını ("problem yok gibi"), I/O denemesinin tamamlandığını, belirsiz ilerleme görevinde iptalin çalıştığını ve görevin iptal edilmeyen koşuda normal tamamlandığını bildirdi. Böylece uygulamanın kendi masaüstünde açılıp bu eylemlerin kullanılabildiği doğrulanır. Fiziksel ekranı ajan görmedi; süre, RAM veya kapsamlı kullanılabilirlik başarısı çıkarılmaz.

Çalıştırılan tam komut, desktop backend, runtime sürümleri ve binary/source hash kullanıcı tarafından ayrıca bildirilmedi; ENV-01 ile birebir eşitliği doğrulanmadı. Daha önce tarif edilen yerel Faz01 uygulaması üzerinden bildirilen davranış kanıtıdır. İlk bildirimde görev sırasında yapılandırma/eski sonuç, hata ve aktif görevde kapanış denenmiş sayılmadı. Sonraki kullanıcı bildirimi aşağıda bu kontrolleri tamamlar. Remote CI için yeni kanıt yok.

<a id="e01-user-final"></a>

## Kalan üç manuel kontrolün sonucu

2026-10-06; ENV-USER-01; kullanıcı, önceki mesajdaki üç somut kontrolün ardından "hepsi çalışıyor" bildiriminde bulundu. Bu bildirim şu kontrollerin başarı kanıtıdır: (1) CPU görevi sürerken deneme yapılandırması değiştirilince eski sonuç uygulanmıyor, (2) hata aktarımı denemesinde anlaşılır mesaj ve takip kimliği görünüyor, (3) görev sürerken pencere takılmadan kapanıyor. Teknik log redaksiyonu/korelasyonu ENV-01 otomatik testleriyle ayrı desteklenir; kullanıcının log dosyasını incelediği iddia edilmez.

Kullanıcı tarafından bildirilen işlevsel masaüstü kabulü kapandı. Erişilebilirlik, performans veya tüm kullanım senaryoları için genel başarı çıkarılmaz. Uzaktaki CI koşusu F01-CI-REMOTE açık; Faz01 bu nedenle engelli, Faz02 başlamadı.

## GitHub yayınlama girişimi — 2026-10-06

Kullanıcı projeyi https://github.com/Teknoloji-Filozoflari/Veri_Ufku.git deposuna göndermeyi açıkça yetkilendirdi. Uzak URL yapılandırma hedefidir; erişim doğrulanmadı. Git ls-remote exit128: Could not resolve host github.com. gh auth status exit1: mevcut hesabın oturumu geçersiz. Workspace .git boş ve salt okunur; Git geçmişi yok. Bu girişimde push veya remote CI koşusu gerçekleşmedi. Erişim anahtarı okunmadı/yazdırılmadı.

Normal kullanıcı terminalinde kimlik doğrulama, boş .git yedeği, proje yollarını açık seçerek commit/push ve CI izleme için scripts/publish_github.sh hazırlandı. bash -n geçti. Ağ/kimlik doğrulama ve push bölümü bu ortamda çalıştırılamadığı için başarılı sayılmaz. Force push yok; mevcut uzak geçmiş farklıysa push reddedilerek korunur. F01-CI-REMOTE açık kalır.

## İlk remote CI başarısızlığı ve workflow düzeltmesi

2026-10-06. Kullanıcı kanıtı: [commit](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/commit/b356f1ebe6e67299590e9568eccd33da6c9236ef), [başarısız koşu](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/actions/runs/37499686960). ENV-CI-01: hedef Ubuntu24.04; jobların fiilen çalışıp çalışmadığı ve runtime metadata log olmadan doğrulanmadı. gh run view --log-failed bu ortamda api.github.com bağlantı hatası verdi; web erişimi de log sağlamadı.

Statik incelemede kesin workflow hatası: jobs.linux.env alanında runner.temp kullanılmış; bu alanda runner context desteklenmez. [Resmî context tablosu](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability) doğrular. XDG yolları artık ilk run adımında RUNNER_TEMP ile GITHUB_ENV dosyasına yazılıyor. Uzak log olmadan ilk koşunun tek/kesin hata nedeni iddiası yok. Bu düzeltmenin sunucuda geçmesi henüz doğrulanmadı; yeni push ve CI koşusu gerekir. Başarısız önceki koşu kabul kanıtı değildir.

Workflow düzeltmesi yerel doğrulama: üç XDG değişkeninin gerçek Bash adımından beklenen geçici yollara yazılması geçti; publish betiği bash -n geçti; check_docs, Ruff check/format ve 32 test geçti. GitHub API erişimi yok; yeni remote koşusu başarılı diye raporlanmaz.

## İkinci remote CI koşusu — test adımı başarısız

2026-10-06; kullanıcı çıktısı: [commit 4200acb9b33911c192bd64c2a6c6d739ac28b7ce](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/commit/4200acb9b33911c192bd64c2a6c6d739ac28b7ce), [koşu 37500010786](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/actions/runs/37500010786), linux job112394305969. Kurulum, XDG ayarı, kilitli bağımlılıklar, belge/artefact ve lint geçti; Core correctness and headless QML test exit2 ile başarısız; entry smoke çalışmadı. Bu nedenle F01-CI-REMOTE doğrulanmadı. Node20 checkout bildirimi warning'dir; eldeki çıktı test hatasının sebebini göstermez.

Ajan gh run view --log-failed denemesi api.github.com bağlantı hatası verdi. Test ayrıntı günlüğü henüz alınamadı; import/native library/collection/başka sebeplerden biri olduğu tahmin edilerek kod değiştirilmez. İlk workflow context düzeltmesi artık runner üzerinde geçmiş; sonraki teşhis test günlüğünü gerektirir.

<a id="e01-egl-fix"></a>

## İkinci koşunun ayrıntı günlüğü ve Qt sistem kitaplığı düzeltmesi

2026-10-06; F01-CI-REMOTE; ENV-CI-01. Kullanıcının bu oturumda gönderdiği gerçek log: 2026-10-06T16:59:34Z, `uv run --frozen pytest -q`, offscreen/software; `tests/test_gui.py:7` satırında `from PySide6.QtTest import QTest` importu `ImportError: libEGL.so.1: cannot open shared object file: No such file or directory` verdi. Test toplama 1 hata ile kesildi; exit2. Testler çalışmadı; başsız QML davranışı bu koşuda doğrulanmadı. Önceki günlüğün beklenmesi kaydı tarihsel; hata nedeni artık bu logla belirli.

Kod yolu `.github/workflows/docs.yml`: Python kurulumundan ve testlerden önce `sudo apt-get update`, ardından `sudo apt-get install --no-install-recommends -y libegl1 libgl1` eklendi. [Ubuntu 24.04 libegl1](https://packages.ubuntu.com/noble/libegl1) sistem EGL paketidir. Yerel kilitli PySide6 wheel'inin `libQt6Quick.so.6` bağımlılıkları `ldd` ile incelendi: libGL.so.1 ve libEGL.so.1 sistemden çözülüyor. Software backend seçimi Qt importundaki bu dinamik bağlantı gereksinimini kaldırmıyor. Python/Qt sürümleri, kilit ve GUI testleri korunuyor.

2026-10-06; ENV-01; yerel doğrulama: [phase01-egl-checks.txt](phase01-egl-checks.txt). `uv sync --locked --group dev`, check_docs/check_artifacts, Ruff check/format, 32 pytest testi ve `veri-ufku --smoke-test` exit0. İzole XDG yolları ve offscreen/software kullanıldı. Sistem Python 3.14 ile `python3 -m unittest discover -s tests -v` paket kurulu olmadığı için 3 import hatasıyla başarısız oldu; kilitli CPython 3.13.15 ortamında unittest discovery 9 belge testini geçti (pytest işlev testlerini unittest çalıştırmaz). Test günlüğü bu ayrımı korur.

Ubuntu apt kurulumu yerel CachyOS ortamında çalıştırılmadı. Yeni push/remote koşusu bu oturumda gerçekleşmedi; F01-CI-REMOTE doğrulanmadı ve Faz01 engelli kalır. README, DEVELOPMENT, matris ve ilerleme özeti eksik kitaplık teşhisini yansıtır. Sonraki faz başlatılmadı.


<a id="e01-remote-success"></a>

## Başarılı remote CI — 2026-10-06

F01-CI-REMOTE; ENV-CI-01; kanıt türü kullanıcı tarafından paylaşılan gerçek GitHub Actions sonuç çıktısı. [Commit 603d54a7aae24da275b8a777b93a8d86066b1599](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/commit/603d54a7aae24da275b8a777b93a8d86066b1599), [koşu 37500721689](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/actions/runs/37500721689), main/push, linux job112396721151: success, 28 saniye. Ajan GitHub API'sinden bağımsız sorgulama yapmadı; kullanıcı çıktısı kabul kanıtıdır.

Ortam: workflow hedefi Ubuntu24.04 x86_64; kilitli CPython3.13.15/PySide6 6.11.2, uv0.12.23; QT_QPA_PLATFORM=offscreen, QT_QUICK_BACKEND=software, izole XDG yolları. Bunlar workflow/kilit yapılandırmasıdır; runner kernel/CPU/RAM ve fiilî paket metadata/hash çıktısı sonuç özetinde verilmedi.

Kullanıcının paylaştığı sonuçta şu adımların tamamı geçti: checkout, Qt native runtime kitaplıkları kurulumu, izole yollar, sabit uv kurulumu, sabit Python ve kilitli bağımlılıklar, belge/artefact doğrulama, lint, Core correctness and headless QML test, Installed entry point Qt and process smoke, job kapanışı. Test sayısı/süreleri özette ayrıca verilmedi; yerel 32 test sonucu önceki ayrı kanıttır. Eksik EGL nedeniyle başarısız ikinci koşu tarihsel kayıtta korunur; yeni koşuda test ve smoke adımları başarılıdır.

Node20 checkout bildirimi uyarı olarak kaldı; kullanıcı çıktısı actions/checkout@v4'ün Node24 üzerinde çalıştırıldığını bildiriyor. Koşu başarıyla tamamlandı; bu uyarı CI kabulünü engellemiyor. Bu belge güncellemesi başarılı commit'ten sonradır ve yeni bir remote koşusu yapılmış sayılmaz.

<a id="e01-phase-acceptance"></a>

## Faz 01 kabulü

2026-10-06; F01-S006 ve F01-CI-REMOTE doğrulandı. F01-S006 birleşik kanıtları: e01-ci/e01-remote-success (lint, çekirdek, başsız GUI, entry smoke), e01-contracts (capability/provenance/ComputeBudget), e01-measurement (görev sayısı/RAM/temp/iptal ve ölçüm sınırları), e01-progress (belirsiz ilerleme), e01-stale (veri/config eşleşmesi), e01-translation (Türkçe katalog). İlgili gerçek yollar: .github/workflows/docs.yml, src/veri_ufku/app.py, domain/contracts.py, jobs/manager.py, ui/controller.py, learning/i18n/tr.ts, scripts/measure_phase01.py ve tests/test_gui.py/tests/test_jobs.py (src alt yolları src/veri_ufku köküne göredir). Ortam ENV-01 + ENV-CI-01; mevcut alt kanıtların ölçüm sınırları korunur.

Matrisin bütün zorunlu Faz01 satırları doğrulandı; kullanıcı masaüstü kabulü e01-user-desktop/e01-user-final ile ayrı kayıtlıdır. Faz01 durumu doğrulandı, yetenek olgunluğu deneysel, kapsam zorunlu. Faz02 ve sonraki fazlar başlamadı. UI-REF-VIS, minimum donanım ve tam offline dağıtım ayrı açık kabul başlıklarıdır; bu CI başarısı bunları doğrulamaz.

Kabul güncellemesinin yerel kontrolü — 2026-10-06, ENV-01: check_docs geçti; belge negatif testinde doğrulanmamış bağımlılık artık geçici fixture içinde açıkça oluşturuluyor (tests/test_document_contracts.py); gerçek Faz01 kabulüne bağlı varsayım kaldırıldı. Bu düzeltmeden sonra offscreen/software kilitli pytest: 32 passed in 5.56s. Ruff check/format ve check_artifacts geçti. Bu test dosyası değişikliği başarılı remote commit'ten sonradır; remote üzerinde yeniden denenmiş sayılmaz.
