# Veri_Ufku — UI/UX yenileme teknik teslimi

2026-10-17; kapsam kimliği **UI-RENEWAL-01**. Kullanıcının kapsamlı UI/UX ve kod
iyileştirme talimatı. Faz76 veya yeni bir bilimsel yöntem fazı değildir.
Durum: aşağıda sınırlandırılmış teknik uygulama/test teslimi; bütün modüller için
üretim, insan kabulü veya resmî release doğrulaması değildir.

## Güvenli başlangıç ve inceleme

Çalışma ağacı başlangıçta çok sayıda değiştirilmiş/untracked dosya içeriyordu.
[Git başlangıcı](ui-renewal/baseline-git.txt),
[677 Python/QML/JS kaynak hash'i](ui-renewal/baseline-source.json) alındı.
Kaynak/test/betiklerin değişiklik öncesi kopyası aynı makinede
`/tmp/veri-ufku-ui-renewal-before.tar.gz`; kalıcı yedekleme hizmeti değildir.
.git yazma yetkisi olmadığı için main dalı korundu. Stage, commit, push, reset ve
kullanıcı dosyası silme yapılmadı. Mevcut kullanıcı çalışmalarının tümü bu teslimin
değişikliği olarak gösterilmez. [Değişen dosya manifesti](ui-renewal/delivery-manifest.json)
başlangıç hash'i ile bu görev farkını ayırır.

Dizin/entry incelemesinden sonra hedefli olarak `app.py`, `ui/`, ilgili QML,
`analytics/dataset.py`, `modeling/lifecycle.py`, jobs/proje sınırları ve aşağıdaki
testler incelendi. Yüzlerce bilimsel modülün her satırı yeniden denetlenmedi.

| Alan | Bulunan mimari / karar |
|---|---|
| Başlatma | app.py tek QApplication/QQmlApplicationEngine; mevcut entry korunur |
| Kabuk | Main.qml sekiz amaç bölümü, ortak Ui kontrolleri; formlar ilk ziyarette yüklenir |
| Veri | Polars/Arrow, immutable dataset sürümü,200 kayıtlık QAbstractTableModel sayfası |
| Hesap | Mevcut worker/process, ComputeBudget ve controller; ikinci görev sistemi yok |
| Depo | Tek ProjectStore atomik yayın, RowId/ColumnId ve mevcut lineage |
| Grafik | Worker Matplotlib Agg/image provider; bilimsel hesap ve export tarifi korunur |
| Ayarlar | Mevcut Preferences açık/koyu/yazı ölçeği/locale; izole test XDG |
| Hata/log | Mevcut sınırlı/allowlist log, kullanıcıya durum/iptal/hata; veri loglanmaz |
| Kalite | Kilitli CPython3.13.15, pytest/Qt, Ruff, belge/learning/artifact kapıları |
| Optional | Lazy yükleme ve registry availability; eksiklik tüm uygulamayı kapatmamalı |

Uygulanan sıra: başlangıç ölçümü → ortak kontroller/kabuk → ilk ziyarette form
yükleme → veri tablosu/grafik → rapor editörü → model/yardım yaşam döngüsü
regresyonları → kurulu wheel ve görsel kanıt. Ara başarısızlıklar saklandı.

## Sorunlar ve uygulanan düzeltmeler

| Kimlik / önem / sınıf | Yer / etki | Düzeltme ve kanıt |
|---|---|---|
| UI-01 P2 performans | Main,20.231 başlangıç Qt nesnesi |18 panelde WorkspacePanel,6046 nesne; gezinmede form korunur |
| UI-02 P1 yanıt verme | Gizli ModuleDiscovery her iş değişiminde optional backend tarıyordu; başlangıç GUI timer testi fail | Görünürlük koşulu + ListView delegate virtualization; gizlide sıfırprobe, unchanged responsiveness PASS |
| UI-03 P2 performans/bağımlılık | Lifecycle global skops importu dolaylı torch yükler | Save/load içine import; başlangıç subprocess no-skops/no-torch, safe persistence testleri PASS |
| UI-04 P2 UX | Yoğun navigasyon, proje kartı aşağıda, ortak alan görünümü tutarsız | Kompakt ray, üst arama/ayar, proje önce, durum satırı, ortak tema/alanlar |
| UI-05 P2 veri sunumu | Null ile gerçek `∅` metni ayırt edilemiyor; index bounds yok | Sayfa null koordinatları/MissingRole; geçersiz index None; veri değişmez |
| UI-06 P2 UX/veri | Tablo boyutu/klavye/kopya kapsamı belirsiz | Sütun resize, sayfada genişlik koruma, RowId'li bounded JSON clipboard |
| UI-07 P2 grafik | Sabit tuval ve letterbox alanından yanlış seçim riski | Aspect-fit responsive tuval; görüntü hazır/değişkenboyut/konum guard |
| UI-08 P2 rapor | Basit başlık/metin için JSON düzenlemek gerekiyor | Başlık/bölüm/caption formu, explicit apply; advanced recipe korunur |
| UI-09 P1 regresyon | Lazy Validation ilk mevcut planı kaçırdı | Component.onCompleted current plan/defaults; group/time/leakage ve calibration GUI PASS |
| UI-10 P2 regresyon | Üst düğmeden açılan yardımın odak dönüşü | Header/footer dahil görünür öğe araması; Escape/odak testi PASS |
| UI-11 P2 test | Audio küçük işte polling iptal yarışıyordu | Gerçek running sinyalinde iptal; canceled durum ve önceki artifact kontrolleri korunur |

UiTextField/TextArea/Combo, NavigationButton, Symbol, OperationTable, ResultPanel
ortak stil/erişilebilirlik düzeni tüm kullanan ekranlara uygulanır. Hazırla,
İncele, Karşılaştır, Model, Rapor, Öğren ve veri ekranları render edildi; seçilmiş
kritik yollar aşağıda gerçek worker'larla doğrulandı. Bütün416 yeteneğin tüm
ayar kombinasyonları için GUI kabulü yapılmadı. Mevcut istatistik/ML hesap
formülleri ve algoritma seçimi değiştirilmedi. Yeni dependency eklenmedi.

Kopyala eylemi yalnız mevcut yüklenmiş sayfadaki seçili satırların **görüntülenen**
metnini ve RowId'yi JSON verir; kırpılmış görüntü değeri tam hassasiyetli export
sayılmaz. Sayfa dışında seçili kayıt kopyalanmaz. Kaynak hash'i testte sabittir.
Rapor metni düzenleme mevcut bağlı hesapları yeniden çalıştırmaz, dataset/run
bağlarını ve redaction alanlarını korur. Clipboard açık kullanıcı eylemidir.

## Görsel kanıt

Gerçek PySide6/QML offscreen/software render; çizim maketi veya üretilmiş görsel değil.
Geliştirici görsel incelemesi yapıldı; fiziksel masaüstü/insan/AT çalışması değildir.

- [Önce ana pencere](ui-renewal/before/home.png)
- [Son ana pencere](ui-renewal/after/home.png)
- [Açık tema](ui-renewal/after/home-light.png)
- [720px / %200 yazı](ui-renewal/after/home-large-text.png)
- [Gerçek sayfalı tablo / null / seçim](ui-renewal/final-actual/data-table.png)
- [Hesaplanan histogram](ui-renewal/final-actual/computed-histogram.png)
- [Rapor metin editörü](ui-renewal/final-actual/report-editor.png)
- [Ayarlar](ui-renewal/final-actual/settings.png)

## Ölçüm ve sınırı

Aynı geliştirici makinesi; Linux7.2.9 CachyOS x86_64/glibc2.44,
CPython3.13.15/PySide6.11.2. Betik `scripts/measure_ui_renewal.py` her koşuda ayrı
geçici XDG kullanır. İlk Qt event processing +100ms bekleme sonrası elapsed/RSS;
disk cache kontrol edilmedi, tek örnek, median veya cold-boot SLA değildir.

| Ölçüm | Önce | Sonra |
|---|---:|---:|
| İlk görüntü gözlemi |3,491s|1,742s|
| Başlangıç Qt QObject |20.231|6.046|
| Başlangıç süreç RSS |885.976KiB (~865MiB)|569.656KiB (~556MiB)|

[Önce](ui-renewal/before/measurement.json) /
[sonra](ui-renewal/after/measurement.json). Tüm modülleri açınca kullanılan bellek
başlangıç ölçümünden yüksektir. RAM/task/thread limitleri azaltılmadı/kaldırılmadı.
Tablo için yeni tam veri kopyası yapılmadı; null işaretleri yalnız mevcut sayfada.

## Gerçek test sonuçları

Aşağıdaki koşular aynı testleri tekrar içerebilir; sayılar toplanarak yeni benzersiz
test sayısı veya bütün depo başarısı oluşturulmaz. JUnit test kimliklerini/tarihi
ve süreleri, loglar uyarıları korur. Testler kilitli `.venv` ile çalıştırıldı.

| Koşu / kanıt | Sonuç | Kapsam |
|---|---|---|
| [Baseline](ui-renewal/baseline.xml) |11PASS /1FAIL| Başlangıç GUI responsiveness fail, değişiklik öncesi |
| [Scientific integrity](ui-renewal/scientific-integrity.xml) |110PASS| Grafik referansları, işlemler, jobs, atomik depo/crash/cancel,14 numeric witness |
| [Workflows](ui-renewal/workflows.xml) |19PASS| Temizle/grafik/export/reopen; istatistik GUI; environment ve export GUI |
| [Model/validation](ui-renewal/model-validation-final.xml) |8PASS| Gerçek regression/classification/predict; calibration, group/time planı, final test |
| [Accessibility/persistence](ui-renewal/accessibility-persistence.xml) |44PASS| Qt erişilebilir adlar/odak, safe persistence saldırı/bozulma, audio cancel |
| [Report/table](ui-renewal/report-table.xml) |13PASS| Rapor metni/bağ koruma, gerçek rapor oluşturma/export ve UI contracts |
| [Lazy final](ui-renewal/lazy-final.xml) |10PASS| Yeni6 UI test +4 workspace; bounded table/RowId ve başlangıç import |
| [Final regression](ui-renewal/final-regression.xml) |34PASS| GUI, dataset, roadmap, learning, tema/tercih, optional absence |
| [Installed wheel](ui-renewal/wheel-tests.xml) |17PASS| UI6 +GUI8 +reportGUI2 +gerçek temizleme/grafik/export1 |
| [Son görsel wheel](ui-renewal/wheel-visual-final.xml) |7PASS| Kurulu pakette güncel görsel/UI kontrolleri |
| [Son görsel source](ui-renewal/visual-final.xml) |7PASS| Yeni6 UI kontrolü ve hesaplanan histogram render/export/reopen |
| [Histogram retry](ui-renewal/chart-retry.xml) |1PASS| Gerçek grafik input guard,PNG/SVG,save/reopen |

[Model/media ara koşusu](ui-renewal/model-media.xml)2PASS/6FAIL;
2PASS gerçek audio feature/classification/reopen/newprediction. Beş model failure
ilk form planı problemiydi; model-validation-final ile giderildi. Audio iptal
race'i accessibility-persistence ile giderildi. Başarısız first/second/core-ui
koşuları QML syntax, eager widget varsayımı ve focus regresyonlarını kaydeder;
loglar silinmedi. Eski beklenti yalnız yeni tasarımın açık davranışına göre
uyarlandı; bilimsel/RowId/iptal/leakage assertion'ları kaldırılmadı.

Son ek ekran koşuları, statik kapılar, package parity ve kaynak hash'leri
[teslim manifestinde](ui-renewal/delivery-manifest.json). Bu dosya actual JUnit/log
sonuçlarını listeler; failed kayıtları pass'e çevirmez. Ruff, format,
check_docs/check_artifacts/check_learning/check_usability ve14 document contract
kontrolü PASS: [Ruff](ui-renewal/ruff-final.log), [format563dosya](ui-renewal/format-final.log), [belge](ui-renewal/docs-final.log), [artifact](ui-renewal/artifacts-final.log), [learning](ui-renewal/learning-final.log), [usability](ui-renewal/usability-final.log), [14document test](ui-renewal/doc-contracts-final.log).

[Kilitli source/wheel giriş smoke](ui-renewal/entry-locked.json) ikisinde de
GUI_SMOKE PASS/exit0. İlk yardımcı komut `.venv/bin/python` symlinkini resolve
edip temel Python yolunu çağırdığı için PySide6 bulunamadı
([başarısız kontrol](ui-renewal/entry-final.json)); komut düzeltildi, ürün kodu
değiştirilmedi. Bu hata kilitli uygulama testi sonucu olarak sayılmaz.

Yerel wheel hatchling ile üretildi ve uv `--offline --no-deps --target` ile
ayrı `/tmp/veri-ufku-ui-renewal-wheel` dizinine kuruldu. İlk install sandbox
uv-cache erişim reddi verdi; yetkili yeniden koşu başarılı oldu. /tmp cwd/PYTHONPATH
ile kurulu package importu ve17 test doğrulandı.432 paket dosyası kaynak/wheel/kurulu dizinde byte-eşit. Bu temiz OS kurulumu/offline
wheelhouse/Flatpak testi değildir. Mevcut Faz74 Flatpak adayları bu UI değişikliklerini
**içermez**; dağıtım adayı yeniden paketlenmeden güncel diye sunulamaz.

## Açık sorunlar / kapsam sınırı

| Kimlik | Önem | Durum ve sonraki doğrulama |
|---|---|---|
| UI-R01 |P1| [chart-final](ui-renewal/chart-final.xml) süreç/native thread bütçesi iptali; aynıkomut retry PASS. Supervisor aktif süreç ağacı limitini uyguladı; kaynakçıktısı yayınlanmadı. Hangi kısa ömürlü alt sürecin tetiklediği kanıtlanmadı; process-tree ölçümüyle tekrar gerekli. Limit gevşetilmedi. |
| UI-R02 |P2| accessibility-persistence sonunda307 uncollectable object ResourceWarning. Assertion failure değil; kaynağı/uzun oturum artışı henüz ayrıştırılmadı. “Bellek sızıntısı yok” iddiası yok. |
| UI-R03 |P1| Faz75 uzun combined GUI/default RAM/timeout ve kaynak kapanış açıkları ayrı kanıttır; bu küçük testlerin geçmesi onları kapatmaz. |
| UI-R04 |P2| Bütün uzman modüllerin form tasarımı ayrı ayrı yenilenmedi; ortak kontrol stili uygulanır. Bazı ileri tarifler JSON ve bazı eski metinler yalnız Türkçe. |
| UI-R05 |Kabul engeli| Fiziksel masaüstü/native portal, yeni başlayan/uzman insan, AT, minHW, Pardus/Debian/ayrı Arch, GPU, temiz offlineinstaller ve yeni remote CI yapılmadı. |
| UI-R06 |Kabul engeli| Faz75 bilimsel uzman review pending; katalog91 home10/dataset-profile4 değişiklikleri eski hash-review onayı sayılmaz. |

Bu test kapsamı içinde kaynak hash/RowId, seçilmiş bilimsel referanslar ve atomik
proje yayın kontrolleri geçti; bütün ürün için kritik hata/veri kaybı yok garantisi
verilmez. [Faz75 açık kabul kapıları](PHASE75.md) ve capability olgunluğu korunur.

## Başlatma / yeniden doğrulama

Repo kökünde mevcut kilitli ortamla `.venv/bin/veri-ufku` veya
`.venv/bin/python -m veri_ufku`. İlk kurulum gerekiyorsa `uv sync --locked --group dev`;
yerel paket önbelleği yoksa kurulum internet gerektirebilir. Uygulama açılışı model
indirme/kod yürütme/ağ kaynağı açma başlatmaz. Kullanıcının gerçek projeleri testte
kullanılmadı. [Geliştirme komutları](../DEVELOPMENT.md) ve ölçüm betiğiyle yeni
output dizininde tekrar alınabilir.

Uygulama tercihleri: üst görüntü ayarı; yöntem arama Ctrl+K; yardım F1/Escape;
bölümler Ctrl+1…8; veri tablosu satırında ok tuşları ve Ctrl+C.

Teknik kaynaklar: Qt resmi [Loader](https://doc.qt.io/qt-6/qml-qtquick-loader.html)
ve [TableView](https://doc.qt.io/qt-6/qml-qtquick-tableview.html). Kullanılan davranışlar
kurulu Qt6.11.2 üzerinde test edildi; çevrimiçi belge sürümü tek başına doğrulama değildir.
