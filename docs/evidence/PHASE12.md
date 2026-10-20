# Faz12 — istatistik özeti ve grafik kanıtı

2026-10-07 / ENV-12; yerel CachyOS Linux7.2.9/glibc2.44/Ryzen7 8845HS/32GB/Btrfs ve /tmp tmpfs; locked CPython3.13.15/PySide6Qt6.11.2/Polars2.0.0/Matplotlib3.11.2, offscreen/software. Olgunluk deneysel. [Karar ve sınırlar](../adr/015-charts-phase12.md). Kullanıcı masaüstü, uzak CI, minimum donanım, fiziksel HiDPI ve temiz offline kurulum ayrıca doğrulanmadı.

<a id="e12-engine"></a>
## F12-S001/S002 — gerçek grafik ve özet

Yollar charts/contracts.py/engine.py/plot.py/worker.py, ui/charts.py/ChartPanel.qml. Yedi gerçek tür, elle belirlenmiş referans ve ortak kesin profil. Tür/rol/amaç gerekçeli öneri; customer_id ve açık identifier rolü önerilmez. Kullanıcı alan/tür seçer; kimliği elle seçmek anlamlı ölçüm iddiası oluşturmaz. Source dataset/kaynak değişmez. tests/test_charts.py bağımsız beklenenler; tests/test_charts_gui.py yedi gerçek form/sinyal/spawn/Matplotlib QImage ve save/export/reopen yolu.

<a id="e12-methods"></a>
## Yöntem başına kabul eşlemesi

ENV-12 /2026-10-07. Her tür gerçek QML formu, ayrı process, PNG/SVG, atomik proje kaydı ve yeniden açılış üzerinden denendi. Genel test sayısı yöntem kabulü değildir. Yardım src/veri_ufku/learning/content/tr.json; kayıt storage/chart_store.py.

| Alt kimlik | Bağımsız referans / kapsam | GUI / yardım |
|---|---|---|
| F12-HISTOGRAM | [1,2,3,4,null,NaN,inf] iki bin→2/2, edges1/2.5/4;100k→20×5000 | Bin kontrolü; chart-histogram |
| F12-BOX | [1,2,3,4] Q1=1.75/medyan2.5/Q3=3.25, whisker1/4;100k Q1=24999.75 | Gruplar, tüm sonlu üyelerin seçimi; chart-box |
| F12-BAR | A2/B1/C1/D2 top1→A2/Diğer4, üç dış kategori; null/literal reserved adlar ayrıdır | Count/sum/mean/median/min/max/reject, top-N; chart-bar |
| F12-LINE | Tekrar tarihler native artan: Ocak1sum10/Ocak2sum2/Ocak3sum30, n2/1/3; default reject | Tarih/agregasyon açıklaması; chart-line |
| F12-SCATTER | range10 limit3→0/3/6, dışarı7; grid→(2,4,n5)/(7,14,n5), grup üyeliği korunur | Örnekleme/full/grid açık seçim ve RowId; chart-scatter |
| F12-CORRELATION | Pearson/Spearman ortak3→−1; tied-rank elle0.5; sabit/n<2 null+hata; büyük Float64 offset | Yöntem, her çiftin r/n/hatası; chart-correlation |
| F12-MISSING | Null1/7; NaN/inf ayrı, boş metin null değil;100k null10000→%10 | Sütun seçimi,0…100% ve null üyesi seçimi; chart-missing |

<a id="e12-metadata"></a>
## F12-S003 — tarif, anlam ve kalıcılık

ChartSpec/v1 title/axes/units/legend/group/aggregation/bins/correlation/sampling/ViewSpec/null/precision/scope taşır. Sonuç dataset_version/snapshot SHA256, dataset/population/used, kesin özet, dışlanan null/NaN/±inf ve üyelikleri saklar. Kaydet data/members/PNG/SVG/JSON beş artifact'ı manifest7 mevcut results alanında atomik yayınlar. Referans Parquet=noktalar ve point n=gerçek RowId üyelik sayısı ayrıca denetlenir. Reopen filtre/spec/veri eşit; kayıtlı form geri yüklenir, eski filtre/sürüm etiketi güncel değildir. Yedi tür roundtrip test edildi. Decimal0.1/0.2 çiziminde default kayıp reddi, açık approximate iki kayıp ve kesin mean0.15;2**53+1 toplam sonucu kaybı ayrıca reddedilir. Source korunur. Tarih tekrar/sıralama ve native timezone/ns kimlik açıklaması ADR-015'te.

<a id="e12-interaction"></a>
## F12-S004/S007 — QML etkileşim, export ve RowId

Gerçek QTest mouseClick QML MouseArea üzerindeki Matplotlib piksel koordinatına gider; dönen RowId tablodaki aynı kimliktir. Tablo seçimi aynı scatter noktasını vurgular. Gerçek mousePress/move/release zoom viewport'u değiştirir; reset başlangıç bounds'ı getirir. Dikdörtgen/nokta seçim üyelik sorgusu ayrı süreçtir; aggregate seçimi tüm üyeler, örneklenmiş nokta yalnız o RowId. İlk200 gösterim limiti seçim sayısını kesmez; mevcut tablo sayfasının üyeliği ayrıca sorgulanır. Örneklenmemiş tablo RowId'si için sahte nokta üretilmez. Grid grubu karıştırmaz, nokta limiti aşıldığında açık ret. PNG/SVG aynı figure/export metadata; her türde okunur çizim ve artifact bütünlüğü test edildi.

Export yeni/proje dışı dosyada exclusive/fsync yayını; source/mevcut/symlink hedefleri reddedilir. Tam tablo/reference/üyelik kaydı hash'li. Eski konfigürasyon sonucu retarget edilmez, iptal son grafiği korur. Kopya/pointer sonrası iki gerçek SIGKILL, ikinci gerçek süreç readonly yayın reddi, pointer_written exception ve tampered SVG testleri mevcut sağlam ACTIVE veya tam yeni kaydı korudu. Ortak ProjectStore crash/two-writer regresyonları korunur.

<a id="e12-help"></a>
## F12-S005 — çevrimdışı yardım

İçerik11,69 makale/sözlük26; yedi grafik ve özet/skew rehberi. Her tür neyi gösterir, eksen okuma, çarpık dağılım, ortalama/medyan farkı; bin/top-N/tekrar tarih/pair n ve korelasyonun neden nedensellik olmadığı açıklanır. F1/ilgili yardım bağlantıları ve capability help_links; yeni try_action yok. Öğren araması/bağlama göre render mevcut testlerle korunur. check_learning dinamik tür bağları ve statik QML bağlarını kontrol eder.

<a id="e12-package"></a>
<a id="e12-measure"></a>
## F12-S006/S007 —100k ve erken gerçek Linux paketi

scripts/measure_phase12.py100.000 kayıt: yedi grafik bağımsız değerleri, gerçek ayrı PID, Qt image, her tür PNG/SVG, proje save/reopen, gerçek pointer/drag zoom/reset, filtre1.000 kayıt ve20/10 histogram binleri, iptal ve kaynak SHA256 korunması. Son source/wheel ölçümleri aynı makinede iki ayrı uygulamayla eşzamanlı yürütüldü; izole makine benchmark iddiası yok. Source ve /tmp cwd/PYTHONPATH üzerinden noneditable kurulu wheel aynı locked runtime kullanır; --package-root assertion kaynak fallback'ini reddeder. [Kaynak ham ölçümü](phase12-headless.json), [kurulu paket ham ölçümü](phase12-wheel.json), [ortam/hashler](phase12-environment.json). Başsız geliştirici donanımı, sıcak N=1/yöntem;100 input+grabWindow p95 fiziksel ekran latency değildir. RSS parent+worker ortak sayfayı iki kez sayabilir. Minimum8GB/soğuk cache/genel veri sınıflarında bütçe kabulü değildir.

Offline build `/tmp/veri-ufku-phase12-final-dist`, offline/no-deps install `/tmp/veri-ufku-phase12-final-installed`. Gerçek seven-chart paket smoke CI workflow'a eklendi; yeni uzak koşu yok. Yerel paket mevcut sistem Qt native kitaplıklarına ve locked runtime'a bağlıdır; AppImage/Flatpak temiz makine veya ağ kapalı tam kurulum kabulü yerine geçmez.100k ve kontrollü nokta/üyelik RAM sınırları bu fazda görünür; entegrasyon Faz27'ye bırakılmadı.

[Histogram PNG](phase12-histogram.png), [SVG](phase12-histogram.svg), [korelasyon PNG](phase12-correlation.png), [SVG](phase12-correlation.svg) gerçek export örnekleri. Açık/%1001366 ve koyu/%200720 başsız ekran görüntüleri ham ölçümde; dar/%200 görünüm kaydırma ister. Native SaveFile diyaloğu kullanıcı testi ve yeni gerçek masaüstü ayrı açıktır.

<a id="e12-integration"></a>
## Erken bulunan ve düzeltilen engeller

Qt6.11.2 requestImage Python override'ında (QImage,QSize) dönüşü TypeError verdi; QImage dönüşü ve output QSize güncellemesiyle gerçek GUI testleri geçti. Empty-members durumunda Polars2 lazy join optimizer min>max panic üretti; küçük nokta-count karşılaştırması bounded dict olarak yapıldı, boş null üyelik fixture'ı geçti. İlk suite eski Faz02 “İncele henüz yok” ve sözlük18 beklentileriyle iki hata verdi; gerçek yeni ekran/sözlük26 beklentileri güncellendi. Bu denemeler başarılı kabul edilmedi. Kategori null/literal ad ve Diğer sentinel çakışmaları, Float64 integer toplam kaybı, grid grup üyeliği ve bar piksel offseti bağımsız regression fixture'larıyla düzeltildi.

<a id="e12-checks"></a>
## Son kapılar

[Gerçek komut kayıtları](phase12-checks.txt): offline locked dev sync, sistem/locked check_docs, check_artifacts, check_learning69 makale/45 UI bağı, Ruff check/format107 dosya,320 pytest73.78s,9 locked unittest, source ve /tmp cwd kurulu entry-point Qt/process smoke ve git diff --check geçti. [Kaynak hashleri](phase12-source.sha256) son test kodunu taşır. Kaynak ve final wheel ölçümleri gerçek mouse drag zoom'u da içerir.

Son source100k RSS805.83MiB, max tick186.00ms; final installed wheel RSS787.46MiB, max tick148.63ms. Wheel100 input/render p95=0.897ms/max1.512ms; iptal feedback2.61ms/exit178.68ms (N=1). Grafik hesap+render source/wheel sırasıyla ham kayıtlarda; final wheel histogram2491.51ms/korelasyon5427.82ms. Sıcak geliştirici donanımı ve eşzamanlı source/wheel koşuları; minimum donanım veya fiziksel frame kabulü değildir. PNG/SVG ve geniş/dar son ekranlar doğrudan görsel incelendi; dar/%200 kaydırma gerekir.

[Doğrudan sistem Python unittest](phase12-system-unittest.txt) bağımlılıksız Python3.14 ortamında34 test/25 import hatasıyla başarısızdır (Polars/veri_ufku import); locked3.13 ortamındaki320 pytest/9 unittest ve entry smoke başarısından ayrı tutulur. Sistem Python'una paket yazılmadı. Yeni masaüstü/native picker/uzak CI/offline temiz kurulum kabulü açık. Yalnız Faz12 tamamlandı; Faz13 başlamadı.
