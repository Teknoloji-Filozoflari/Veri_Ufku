# Faz39 — bağlı dashboard ve figure composer

2026-10-11; ENV-39: kilitli CPython3.13.15, PySide6/Qt6.11.2,
Matplotlib3.11.2, Polars2.0.0; Linux offscreen/software.

<a id="e39"></a>
## E39 — gerçek teknik kanıt

PySide6/QML masaüstü İncele ekranına grafik/tablo/KPI/not dashboard canvas,
12 sütunlu grid sürükleme ve boyut düzenleme, global/local filtre, açık kaynak
ColumnId eşleme, RowId linked brushing, açık drill-down ve kayıtlı görünüm eklendi.
DatasetVersion bağları korunur; kaynağı değişen/eski sürüm görünür uyarı taşır.
KPI pay/agregasyon/payda işlemi/dönem tanımı ve karşılaştırma görünür.

Figure Composer subplot/facet, ortak ve yerel legend, renk/font preset, boyut,
caption/unit/source; yerel SVG/PNG/PDF ve izinli local-svg/v1 HTML üretir.
Çizgi/nokta/alanlar SVG/PDF vektördür; kaynak PNG panelleri gömülmez.
Doğası raster heatmap/image katmanı raster kalır. Pareto iki ekseni sol/sağ
legend ve açık uyarı taşır. Statik çıktı etkileşimi korumaz. HTML kendi paket
JS adapter'ı ve gömülü yerel fontuyla ağsız frozen snapshot seçimini taşır;
yeni veri/KPI yeniden hesaplama yapmaz. Masaüstü mimarisi korunur.

[ADR040](../adr/040-dashboard-figure-phase39.md) kapsam, sınır ve teknik kararları;
[kabul kayıtları](phase39/acceptance.json) F39-S001..004/P001..008 C/V/G/H/P yollarını
ve ENV-39/tarihi bağlar. Profesyonel envanterde P kapsamı isteğe bağlı olarak
korunur; bu kaynak fazın zorunlu S maddelerini karşılayan teknik teslimdir.
Önceki resmî kabul kapıları bu teslimle kapanmaz.

## Kontroller

- [41 hedefli vaka](phase39/targeted.xml), [vaka adları/sonuçları](phase39/test-cases.json):
  40 core +1 gerçek QML/spawn;0 failure/error/skip,28.28s.
- Bağımsız global/local filtre/KPI dönem ve sıfır payda referansı; iki kaynakta
  açık eşleme, yinelenen hedef anahtarlar/null; drill-down gerçek RowId kapsamı.
  Snapshot hash tamper, sahte RowId,10001 satır, RAM admission ve selection başlamadan NaN/inf eşleme anahtarı kontrollü ret.
- Gerçek ProjectStore atomik save/close/open ile grid, filtre, kaynak sürümü ve
  stale bağ. QML widget kontrolü, selection/drill-down/clear/cancel,
  source byte eşitliği, F1/Escape ve odak dönüşü.
- [Ek gerçek GUI eşleme/brush kabulü](phase39/mapping-gui.json), [tekrarlanabilir runner](phase39/mapping-gui-runner.py): QML source/target eşleme düğmesi, global kaynak filtresi, local hedef KPI sum50, gerçek chart pikselinden tam RowId seçimi, duplicate hedef iki satır ve drill-down; iki kaynak byte eşit.
- 17 composition +9 multivariate composer türü/facet; SVG/PDF/PNG iki subplot,
  ortak grup legend, font/context; `<image>` içermeyen scatter vektörü;
  caption/dipnot bounding-box çakışma kontrolü, mevcut output korunur.
- QJSEngine gerçek paket JS'iyle Enter seçimi, duplicate/null anahtar transferi
  ve selection clear; HTML dış script/fetch/network yüklemez, içerik escape edilir.
- [Kaynak QML](phase39/source-gui/walkthrough.json) ve
  [noneditable wheel QML](phase39/wheel-gui/walkthrough.json): dört biçimde gerçek
  export, iki boyutta ekran görüntüsü; PDF pdftotext + pdffonts, DejaVuSerif gömülü.
  Kaynak/wheel toplam8 export ve4 canvas screenshot. PDF rasterize edilip gerçek
  [figure](phase39/source-gui/figure-pdf.png) ve
  [dar canvas](phase39/source-gui/dashboard-720.png) görsel incelendi.
- [Wheel](phase39/wheel.json):251 paket dosyasında source/wheel/installation byte
  eşitliği; QML, JS adapter, dört makale ve font dahil.
  [Installed importer/QML smoke](phase39/wheel-smoke.txt) PASS.
- [Belge unittest](phase39/unittest.txt):14 geçti. Docs/artifacts/learning/usability
  ve Ruff check/format gerçek kapıları son [komut kaydında](phase39/checks.json).
 235 çevrimdışı makale,140 UI bağı,436 erişilebilir alan,189 core English mesajı.

[Kurulu wheel hedefli testi](phase39/wheel-targeted.xml):41 passed /31.96s,0 failure/error/skip; stdin üzerinden spawn mümkün olmadığı için doğrulama dosya girişli runner ile çalıştırıldı. [Tam regresyon](phase39/full-regression.xml):1113 passed,19 skipped,0 failure/error;433.07s. [Özet/atlanma nedenleri](phase39/regression-summary.json). Atlananlar eski fazların haricî isteğe bağlı sunucu/Secret Service fixture'larıdır; Faz39'un41 vakası bu koşuda da geçti,0 skip. Sandbox içindeki bilinen Zarr/asyncio takılması başarı sayılmadı; izinli dış ortamda son kod koşuldu. [Koşu kaynak bütünlüğü](phase39/head-verification.json):392 dosya değişmedi.

## Teslim dosyaları

`charts/dashboard.py`, `dashboard_engine.py`, `dashboard_worker.py`, `figure.py`,
`local_svg_adapter.js`; mevcut `charts/plot.py` SubFigure desteği ve
`composition_plot.py` açık Pareto legend; `ui/dashboard.py`, `qml/DashboardPanel.qml`,
`app.py`, `qml/Main.qml`, `ui/workspace.py`; `storage/project_model.py`,
`domain/capabilities.py`, learning `content/tr.json` ve `taxonomy.py`;
`tests/test_dashboard.py`, `tests/test_dashboard_gui.py`, `tests/test_usability.py`, `scripts/measure_phase39.py`;
hafıza/matris/progress/ADR/development/learning/README ve gerçek kanıtlar.

## Sınırlar ve resmî kabul

Kaynak başına10000 satır, ortak RAM admission,100 widget/12×48grid/16figure paneli.
Tablo ilk200 satırı çizdiğini söyler; hesap tüm izinli snapshot kapsamındadır.
HTML dondurulmuş selection görünümüdür; canlı hesap veya ağ bağlantısı değildir.
Statik export selection etkileşimini korumaz. Fiziksel masaüstü, insan/Orca/AT,
minimum donanım, clean offline install ve remote CI bu fazda koşulmadı.
F13/F24/F25/F27/F28 önceki kabul açıkları, F30 büyük SAS ve F31 clean offline cache
korunur. Teknik teslim ile resmî sürüyor/deneysel/zorunlu durum ayrıdır.
Faz40 uygulanmadı.

Son sırayla tam koşu1112 passed/19 skipped/1 failure verdi: test_usability eski231 makale sayısını bekliyordu. Yeni235 sayı ve dört Faz39 makale kimliği beklentisi düzeltildi; ilgili testler yeniden çalıştırıldı. Uygulama kodu değişmedi. Son tam [paralel dosya grupları](phase39/full-shards.json), [tekrarlanabilir runner](phase39/full-suite-runner.py) ilk koşudaki1132 testcase kimliğini eksiksiz eşler; orijinal shard JUnit/logları korunur. [İlk gerçek sonuç](phase39/full-before-catalog-count-fix.xml) başarısız sonuç olarak saklanır, başarılı gibi sunulmaz.
