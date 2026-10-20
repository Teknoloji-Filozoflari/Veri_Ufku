# Faz36 — çok değişkenli ilişkisel grafikler

<a id="e36"></a>
2026-10-11; DEC-36-01; ENV-36; teknik uygulama tamamlandı.
Resmî faz sürüyor / deneysel / zorunlu; önceki kabuller açık.
Ana kayıt REQUIREMENTS_MATRIX;15 teknik kayıt doğrulandı.
3D scatter/surface isteğe bağlı, uygulanmadı ve test edilmiş sayılmıyor.

950 tam pytest / 781.08s JUnit,0failure/error/skip:
[JUnit](phase36/pytest.xml), [çıktı](phase36/pytest.txt).
33 Faz36 vaka (24core+9 gerçekGUI); [vaka kimlikleri](phase36/test-cases.json).
35 hedefli kontrol (33yeni+2mevcutGUI): [JUnit](phase36/target.xml).
Tam koşu boyunca359 uygulama/test/script/lock dosyası byte değişmedi:
[başlangıç hashleri](phase36/full-start-head.json). [Ortam](phase36/environment.json),
[gerçek komutlar](phase36/checks.json), [C/V/G/H/P](phase36/acceptance.json).

Pair/scatter matrix2–6 açık alan /36 panel; diagonal count histogram,
off-diagonal pairwise sonlu çiftler. Panel×satır üyelik maliyeti collect
öncesi RAM admission; nokta limiti aşımında dur, otomatik sample yok.
Açık ilk-N etiketi ve kullanılmış/population n; ilk-N temsil iddiası yok.
CPU hexbin iki staggered lattice/normalized x²+3y² nearest-center;
Voronoi altıgenler ve RowId üyelikleri.10.001 kaynak satırı /grid12
hücrelerine tüm kimlikler korunarak toplulaştırılır.2D yoğunluk rectangular
histogram: sayım/(n×cell_area), alan integral1; KDE değildir. NumPy
histogram2d ile bağımsız sayım eşleşir.

Bubble alan s=400*v/max veya radius s=400*(v/max)^2; gerçek marker alan
oranı4/16 testi; zorunlu size legend. Eksik/negatif/NaN/inf ret;zero açık
sayılıp dışlanır. Grouped heatmap mean/sum/median/min/max/count;
column z-score ddof0, sabit divisor1. Ortalama matris elle doğrulanır.
Cluster average/complete/Ward Euclidean; linkage ve leaf sırası bağımsız
SciPy referansıyla eşleşir. Renk sınırları/center/divisor/row-column sırası
saklanır; boş hücre doldurulmaz. Parallel yalnız sayısal minmax; orijinal
değer ve sınırlar saklanır, kategori ret. Facet shared/independent gerçek
panel sınırları test edilir; conditional pooled ile within-group r/n ayrı,
Simpson olasılığı nedensellik kanıtı diye sunulmaz.

Her yeni tür için kaynak ve noneditable kurulu wheel9'ar gerçek QML/
spawn/F1-Escape/export/save/açılış ve seçim→tablo→ayrı filter copy preview/
apply denemesi. Her iki yol18'er geniş/dar görüntü ve27'şer PNG/SVG/PDF:
**36 ekran,54 export**. PDF sistem Poppler metin ve raster kontrolü;
SVG/JSON tam dataset sürümü ve üyelik fingerprint. Kaynak byte değişmez.
[Kaynak](phase36/source-gui/walkthrough.json),
[kurulu](phase36/wheel-gui/walkthrough.json),
[görsel geliştirici incelemesi](phase36/visual-review.json).

Seçim yalnız görünüm; ayrı eylem statik çıktıya işler. Footer seçili RowId
sayısı, glyph IDs/ilk5RowId, örnek/facet/heatmap/bubble yöntemini taşır;
resultJSON tam seçim kimliklerini saklar. Ayrı yeni dataset kopyası eylemi
preview üretir, Dönüştür ekranında açık apply gerekir. Mevcut filter
OperationSpec/v1 genişletildi; RowId/SourceRecordId/ColumnId korunur,
sourcechart result kimliği ve geri alma/provenance mevcut yayın yolunda.
Dataset kopyası en fazla10000 tam seçim; daha büyüğü açık ret. İlk200
liste gösterimi sessiz yeni dataset filtresine çevrilmez.

232paket dosyası kaynak/wheel/installed byte eşitliği [manifest](phase36/wheel.json).
Kurulu console GUI_SMOKE PASS [çıktı](phase36/wheel-smoke.txt).
14belge unittest;12registry/usability; docs/artifacts/learning/usability/
Ruff check+format geçti. Katalog52/200,10yeni çevrimdışı konu;130UIbinding,
365namedfield. Yeni dependency/lock değişikliği yok; CPython3.13.15.

Sınırlar: Çok değişkenli eksenler linear; unsupported log/symlog ve
uyumsuz facet/grup ret. Facet/pair/kategorik panellerde zoom için açık
filtre; kategorik sürekli interpolation yok.3D/surface yok; perspektif/
occlusion ve2Dalternatif açıklaması GUI/yardımda. GUI geliştirici kanıtı
fiziksel masaüstü/insan/AT kabulü değildir. Önceki F13/F25insan/Orca/AT,
F24minhardware/cold/physicalframe,F27kullanıcı durdurduğu dağıtım,
F30büyükSAS,F31cleanofflinecache açıkları korunur. Cleanofflineinstall/
remoteCI burada koşulmadı; wheel mevcut locked bağımlılıklarla kurulmuştur.
Önceki kaynak/test/kanıtlar korunur; stage/commit/push yapılmadı.

[Karar](../adr/037-multivariate-charts-phase36.md).
