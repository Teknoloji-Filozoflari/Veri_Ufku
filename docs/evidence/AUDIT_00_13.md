# Veri_Ufku — verilen Faz00–13 kapsamının teknik taraması

2026-10-07 UTC /2026-10-08 Europe/Istanbul; ENV-AUDIT-00-13. Kullanıcı tüm verilen fazları taramayı istedi ve gerçek kullanıcı testlerini tarama sonrasına bıraktı. Kapsam00–13; Faz14–75 başlatılmadı. Faz00–12 önceki kabul durumunu korur; Faz13 teknik özellikleri mevcut, F13-S005 gerçek insan görevi doğrulanmadığı için sürüyor/deneysel/zorunlu.

<a id="e-audit-reference"></a>
## AUDIT-REFERENCE — ürün senaryoları ve bilimsel referans

US-01 belgesinin580/58 sayıları hatalıydı. Korunan on değer10,20,20,30,40,50,60,70,80,100; elle toplam480, ortalama48, medyan45. CC0 magaza.csv pakete eklendi. tests/test_exports_gui.py::test_documented_shop_reference_import_profile_chart_export gerçek QML/spawn CSV import (text/date/Decimal/null),12 kayıt/10 geçerli/2 null,0001–0012, profil48/45, histogram3 bin[4,3,3], kimlik önerilmeme, native Parquet eşitliği ve save/reopen kanıtıdır. İlk yanlış “elle doğrulandı” kaydı PHASE00'da düzeltme notuyla korunur.

US-02 için CC0 subeler.csv pakete eklendi. Aynı test modülünün test_documented_branches_trim_preserves_legitimate_duplicates testi6 kayıt, yalnız2 metin değişimi, ayrı iki Bursa kaydı, aynı RowId/SourceRecordId, undo/redo/reopen ve kaynak byte korunmasını doğrular. Bu iki senaryo otomatik geliştirici GUI kontrolüdür; insan kullanıcı testi değildir.

<a id="e-audit-fixes"></a>
## AUDIT-FIXES — bulunan ve giderilen teknik eksikler

1. Ürün kabul fixture'ları yoktu ve US-01 aritmetik referansı yanlıştı; yukarıdaki dosya/değer kontrolleri eklendi.
2. GuideController eski ImportController.errorText değerini yeni proje oluşturma aşamasında okuyup rehberi durduruyordu. Aşamanın hata bağı düzeltildi; test_guide_recovers_previous_import_error gerçek hata → yeni satış örneği →6 kayıt yolunu doğrular. İptal edilmiş import, boş dataset ile başarılı örnek diye bildirilmez.
3. QML etiketlerinin AutoText varsayılanı kullanıcı metnini HTML/resim kaynağı gibi yorumlayabiliyordu. Ortak UiLabel229 etikette PlainText kullanır; StateNotice da açık PlainText. test_user_status_text_is_literal_qml_text QML ifadesiyle gerçek metin/format kontrolüdür. Ürün yardım/rapor escape ve yerel resource politikası korunur.
4. Tema onAccent değeri bu Qt runtime'ında geçersiz QColor dönüp ana düğmenin açık temada siyah yazılmasına neden oluyordu. accentText ile açık#ffffff/koyu#111827 gerçek contentItem ve pencere highlightedText değerleri test_primary_button_text_token_follows_theme ile doğrulanır. Qt kök nedenine ilişkin sürümler arası genelleme yapılmaz.
5. Faz05 wheel smoke eski sabit şema4 bekliyordu; SCHEMA_VERSION7 kaydıyla yeniden çalışır. Gerçek kurulu CSV import/reopen ayrıca geçti.
6. Proje sonuçları, kalite önerileri ve geçici öğrenme penceresi eski “motor/temizlik/kalıcı kayıt yok” metinleri gösteriyordu. Güncel yeteneklere yönlendiren metinler ve belge başlangıçları düzeltildi; faz teslim tarihçesi ve gelecek model sınırı korunur.
7. Geçersiz başlangıç yapılandırması demo manager'ını kapatıyordu fakat sonraki fazların iş ekranlarını etkin bırakıyordu. Main çalışma alanı ve Ctrl+O/Ctrl+S kısayolları geçerli yapılandırma ister; uyarı bütün ekranlarda üstte görünür, çevrimdışı Öğren ve yardım erişilebilir kalır. test_bad_configuration_is_visible_and_never_logged_verbatim proje/grafik/export düğmelerinin etkin olmadığını, yardım erişimini ve hassas ayarın loga girmemesini kontrol eder.

<a id="e-audit-checks"></a>
## AUDIT-CHECKS — kontroller

Kilitli CPython3.13.15 ortamında **344 pytest**, **9 unittest** geçti; sistem Python3 check_docs, locked offline dev sync, check_docs/check_artifacts/check_learning, Ruff check/format ve offscreen/software kurulu giriş noktası smoke exit0. [Komut/UTC/exit/süre kaydı](audit00-13/checks.json), [pytest sonuçları](audit00-13/pytest.xml), [pytest logu](audit00-13/check-pytest.log), [unittest logu](audit00-13/check-unittest.log). Son yapılandırma kısayolu düzeltmesinden sonra8 GUI regresyonu ayrıca geçti; [son GUI logu](audit00-13/check-gui-final.log). Unittest9 belge testi, pytest344 içindeki aynı belge testlerini tekrar çalıştırır;353 ayrı test iddiası yoktur.

Salt okunur [envanter](audit00-13/inventory.json):92 kalıcı kaynak paragrafı,53 capability (4 altyapı demo +49 ürün işlemi),70 Python uygulama modülü ve254 ürün/belge/test/CI/kilit dosyası. Dosyalar hash'li; Python AST sözdizimi ve Qt bağımsız hesap/depo sınırı taranır. Kaynak paragrafı/capability/path/help/test modülü eşlemesi yapıldı. Envanter çalışma kabulü değildir; aşağıdaki hesap/GUI/worker kontrolleri ayrıca koşuldu.14–75 belge planında kalır. F13-S005 dışındaki91 kaynak paragrafının kabul kaydı var; S005'in export/geçmiş/release teknik parçaları test edilmiştir, gerçek bilgisiz kullanıcı görevi bekler.

| Faz / kaynak paragrafı | Uygulama ve gerçek yeniden kontrol | Erken kurulu wheel bağı |
|---|---|---|
|00 /7 | Ürün/UX/mimari/sözleşme/DAG/traceability/prototip belgeleri;9 negatif belge testi; US-01 aritmetik düzeltmesi | Uygulama özelliği olmayan tasarım fazı |
|01 /6 | config/log/çeviri/binding/bütçe; CPU ayrı süreç, I/O/iptal/kapanış/hata/eski sonuç; test_config/jobs/gui | entry.log |
|02 /5 | QML kabuk/klavye, kalıcı tema/görünüm/ölçek; gerçek renk tokenı ve PlainText; test_presentation_preferences/gui | Faz13 geniş/dar ekranları |
|03 /6 |71 çevrimdışı makale,49 QML bağı, üç derinlik/arama/sözlük/yer imi ve ayrı öğrenme örneği; test_learning/learning_gui | Paket yardım/font/ilk açılış |
|04 /6 | SQLite/manifest/Parquet/ACTIVE/AUTOSAVE, migrasyon, salt okunur ikinci yazıcı, kaynak/dirty/save-as; test_projects/project_gui | Sonraki bütün import/save/reopen akışları |
|05 /7 | CSV/TSV, UTF8/cp1254, ortak snapshot/parser, null/tür/karantina/ID/iptal; test_delimited/import_gui | [CSV worker/reopen](audit00-13/phase05.log) |
|06 /7 | JSON/JSONL/NDJSON, nested/expand; XLSX sayfa/date1900/1904/formül/boyut; native Parquet nullable/Decimal/ns/tz; test_structured_import/import_gui | [Dört format](audit00-13/phase06.log) |
|07 /7 | Bounded200 kayıt sayfa, tüm kapsam filtre/sıra/rol/birim/ordinal/analiz birimi; kesin/örnek profil, null/NaN/inf/ddof/yüzdelik; test_dataset/dataset_gui | [100k tablo/profil](audit00-13/phase07/wheel.json) |
|08 /6 | Tam/filtreli/örnek kalite, aday/kural ayrımı, gerçek RowId örnekleri, deterministik bilgi önerileri; test_quality/quality_gui | [100k kalite/iptal](audit00-13/phase08/wheel.json) |
|09 /7 | Tipli tarif, rename/drop/filter, full önizleme hash kontrollü apply, undo/redo/dal/eski sonuç; test_operations/operations_gui | [100k işlem/kayıt](audit00-13/phase09/wheel.json) |
|10 /8 | Dokuz temizlik discriminator'u; sabit/mean/median/mode, ileri/geri, dedup/trim/map/convert/IQR, null/Decimal/DST/kopya/sızıntı geçmişi; test_cleaning/cleaning_gui | [100k dokuz yöntem](audit00-13/phase10/wheel.json) |
|11 /7 | Dokuz dönüşüm, izinli AST, üç aşamalı join/eşleme/append/pivot, tam üyelik; ODS/readonly SQLite/IPC file+stream; bağımsız DuckDB/Polars; test_relational/relational_gui/relational_backends/phase11_formats | [100k/n:n+formatlar](audit00-13/phase11/wheel.json) |
|12 /7 | Yedi tür, kesin özet, kimlik dışı öneri, bins/topN/Diğer/örneklem/grup/null/çift-n/Pearson/Spearman/sabit kolon; QML-Matplotlib pointer/drag/zoom/reset/RowId/PNG/SVG; test_charts/charts_gui | [100k yedi grafik](audit00-13/phase12/wheel.json) |
|13 /6 | Beş export, güvenli metin ve gerçek negatif sayı, şema kaybı/null/date/XLSX sınırı/reimport; HTML escape/yerel PDF/Türkçe/sayfa, rehber/atla/iki ayrı örnek, CC0 kabul fixture'ları/font/kayıtlı geçmiş; test_exports/exports_gui | [Offline ilk açılış/yedi çıktı/100k](audit00-13/phase13/wheel.json) |

Kaynak test modülleri [envanterde](audit00-13/inventory.json) tam dosya yollarıyla, her testin gerçek sonucu pytest.xml içindedir. Genel test sayısı bir yöntem için bağımsız sayısal referans yerine kullanılmaz: örneklenmiş eski faz kanıtları PHASE00–13 ve ilgili ADR kayıtları korundu; bu tarama yeni fixture/çapraz faz kontrolünü ekler.

Ayrıca gerçek yerel Btrfs üzerinde **46 dayanıklılık kontrolü** exit0: yayın fault injection, gerçek SIGKILL, iki süreç/ikinci yazıcı, migration/ACTIVE/source koruması. [Komut/FS/zaman](audit00-13/durability.json), [sonuç](audit00-13/durability.log), [test kayıtları](audit00-13/durability.xml). Bu46 kontrol,344 test içindeki ilgili senaryoların Btrfs üzerinde tekrar koşusudur; yeni ayrı46 özellik ya da elektrik kesintisi garantisi değildir.

<a id="e-audit-package"></a>
## AUDIT-PACKAGE — gerçek Linux paketi, offline çalışma ve görünüm

Wheel offline/no-build-isolation ile kilitli araçlardan oluşturulur ve ayrı noneditable target'a --no-deps kurulur. Python bağımlılıkları mevcut locked runtime'dır; /tmp cwd + PYTHONPATH target + package-root assertion kaynak ağacına fallback'i reddeder. Wheel tüm src paket dosyalarıyla hash bakımından karşılaştırılır; font/lisans/yardım/QML/örnek CSV+Parquet/rapor HTML+CSS içindedir. [Ortam/hash/komut](audit00-13/environment.json), [wheel dosya karşılaştırması](audit00-13/wheel-contents.json), [paket koşuları](audit00-13/package-runs.json).

Entry, CSV worker, dört native format ve Faz07–13 ölçekli GUI/process/save/reopen komutları ayrı ayrı exit0 verir. Faz13 yeni XDG alanında paket fontu, yerel yardım/örnek/rapor; Python TCP parent/spawn fail-fast, yerel Qt resource allowlist/CSP ile çalışır. OS ağ arayüzü kapatılmadı; temiz Linux makineye internetsiz bağımlılık/kurucu kurulumu iddiası yoktur. Mevcut kaynak dosyası yeni hedefe export edilir, tekrar açılan tür/projeksiyon/kayıt sayısı doğrulanır; hiçbir örnekleme gizlenmez.

Gerçek yeni QML [1366×900/açık/%100](audit00-13/phase13/wheel-1366-light-100.png), [720×560/koyu/%200](audit00-13/phase13/wheel-720-dark-200.png) görüntüleri incelenir. Küçük/%200 ekranda içerik dikey kaydırılır; fiziksel HiDPI/kullanıcı kullanılabilirlik kabulü değildir. [Türkçe HTML](audit00-13/phase13/wheel-example.html), [11 sayfa PDF](audit00-13/phase13/wheel-example.pdf), [Poppler birinci sayfa](audit00-13/phase13/pdf-poppler-page1.png); PDF fontları DejaVuSans/DejaVuSans-Bold embedded/Unicode. QPdfDocument bütün sayfalarda Türkçe metni ve final kaydı denetler; Poppler bağımsız görsel denetim aracıdır, runtime bağımlılığı değildir.

Performans ölçümleri her yöntemde N=1/sıcak geliştirici Ryzen7/32GB makinesindedir.100k işler ayrı worker PID ve ilerleyen Qt event loop ile geçer. Faz07 sabit sayfa modelini ve belleğin sınırlı aralığını doğrular. Faz12/13'te ölçülen en büyük tick boşluğu50ms hedefini aşmaktadır; minimum8GB, soğuk açılış veya16/50ms hedefinin karşılandığı iddia edilmez. Kesin actual değerleri ham JSON'da ve environment.json içinde ayrı tutulur; bu teknik iş akışı geçişi performans garantisi değildir.

<a id="e-audit-user-deferred"></a>
## Gerçek kullanıcı testleri — bu taramanın dışında

Kullanıcı talimatıyla yeni gerçek kullanıcı testleri çalıştırılmadı. Önceki kullanıcı bildirimleri silinmedi; yeni geliştirici walkthrough'u insan testi sayılmadı. F13-S005 gerçek görev tamamlama/yardım ihtiyacı/kritik hata ölçümü bekler; PHASE13_USER_TASK.md protokolü hazırdır. Faz13 bu nedenle sürüyor. Minimum donanım, fiziksel native dosya seçici, yeni uzak CI ve temiz makine offline dağıtım kurulumu bu denemenin kanıtı değildir.
