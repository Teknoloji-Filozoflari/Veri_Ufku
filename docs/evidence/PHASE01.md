# Faz 01 kanıt kaydı

2026-10-06; ENV-01. CPython 3.13.15/PySide6 6.11.2, CachyOS x86_64; Qt offscreen/software. Faz durumu engelli, uygulanan yetenekler deneysel. Sonraki faz başlamadı.

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

DOĞRULANMADI. .git boş/salt okunur, geçerli repository/remote yok; remote CI koşusu üretilemedi. Workflow ve yerel koşu remote başarı kanıtı değildir.

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
