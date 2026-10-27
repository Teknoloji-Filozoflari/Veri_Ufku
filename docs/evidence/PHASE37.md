# Faz37 — kompozisyon, hiyerarşi ve akış

<a id="e37"></a>
2026-10-11; DEC-37-01; ENV-37. Teknik uygulama tamamlandı.
Resmî faz sürüyor / deneysel / zorunlu; önceki kabuller açık.
Ana kayıt REQUIREMENTS_MATRIX;21 teknik kayıt doğrulandı.
Faz38 başlatılmadı; bu teslim gelecek faz yetkisi vermez.

1016 tam pytest / 978.62s JUnit,0 failure/error/skip:
[JUnit](phase37/pytest.xml), [çıktı](phase37/pytest.txt).
66 Faz37 vaka (49core+17 gerçekGUI); [vaka kimlikleri](phase37/test-cases.json).
68 hedefli kontrol (66yeni+2mevcutGUI): [JUnit](phase37/target.xml).
Tam koşu boyunca366 uygulama/test/script/lock dosyası byte değişmedi:
[başlangıç](phase37/full-start-head.json), [son doğrulama](phase37/head-verification.json).
[Ortam](phase37/environment.json), [komutlar](phase37/checks.json),
[21 C/V/G/H/P](phase37/acceptance.json).

17 tür: stacked/100% stacked bar ve area, dot/lollipop, waterfall/Pareto,
treemap/sunburst, Sankey/alluvial, funnel/takvim heatmap, pie/donut ve
advanced radar. Tek Capability registry; input şemaları GUI/registry ve
result metadata'da. Soru araması aynı registry üstünden; radar advanced
onayıyla görünür. Bağımlılık kullanılabilirliği kontrol edilir; uygulanmamış
3D/surface gibi şekiller gallery'de hazır olarak gösterilmez.

Stacked her X içinde payda; yüzde toplam100. Area fiziksel sayısal/tarih X,
sıralı ve tam X×seri grid; boş kombinasyon sessiz0 yapılmaz. Linear
interpolasyon kaydedilir, alan integrali toplam diye sunulmaz. Pie/donut
1–6 ayrı kategori/pozitif toplam/nonnegative değer; kategori kırpma yok.
Eksik kategori ayrı dahil veya açık hariç; eksik Y toplam/payda dışı,
count modunda kaynak satırı dahil. Seçilen payda ve dışlanan n görünür.

Hiyerarşi tek kök, unique ID, var olan parent, cycle kontrolü; internal
value0, yalnız yaprak toplamları rollup edilir. 200node/depth8. Treemap
slice-and-dice leaf alanı; sunburst parent içindeki açı/pay ve depthring,
halka alanı miktar karşılaştırması diye sunulmaz. Sıfır alan gösterilmez,
sıfır node listesi ve temsil edilen n kayıtlıdır. Fixture leaf total10;
treemap alan toplam1; sunburst açı360/360/144.

Akış source/target/value strict; negative/nonfinite/selfloop/cycle ret.
DAG internal giriş=çıkış toleransı1e-9relative/1e-12absolute; sources=sinks.
Duplicate edge fsum ile toplanır ve tüm kaynak kimlikler korunur. 50node/
100edge. Boundary10 ile transit edge_sum20 ayrı; width1/.5/.5 referansı.
Alluvial bitişik katman şartı; atlanan katmanda Sankey alternatifi.

Waterfall start/change…/end açık rol ve sıra; başlangıç+değişimler=bitiş,
bitiş ikinci kez toplanmaz (10+4−2=12). Funnel aşama sırası açık; people
per-stage unique kimlik ve nested cohort, repeated kişi/olay source RowId
kaybolmaz (3→2, duplicate2). Events tekrarları sayar (4→3), kişi dönüşüm
iddiası kurmaz. Takvim physical Date/Datetime, local calendar/timezone,
tek yıl/366day, no-data boş; leapday değeri5/Thursday doğrulanır.

Radar advanced onay,3–6 numeric alan; per-column minmax, constant.5,
complete-case group mean ve orijinal scale kaydı. Raw farklı birimler
aynı eksene konmaz. Alanın eksen sırasına bağlı olduğu ve dot/parallel
alternatifi GUI, statik footer ve yardımda açık.

Kaynak ve noneditable installed wheel17'şer gerçek QML/spawn/F1Escape/
export/save/openSaved/seçim→tablo→ayrı filtercopy preview/apply akışı.
Her yol34 geniş/dar Qt görüntü ve51 PNG/SVG/PDF: **68ekran,102export**.
PDF Poppler metin+raster, SVGdatasetversion ve resultJSON metadata,
kaynak byte değişmez. [Kaynak](phase37/source-gui/walkthrough.json),
[kurulu](phase37/wheel-gui/walkthrough.json),
[geliştirici görsel inceleme](phase37/visual-review.json).
Brushing görünüm; ayrı freeze eylemi statik seçimi saklar, ayrı filtercopy
preview/apply yeni dataset üretir. RowId/SourceRecordId/ColumnId ve
provenance mevcut ProjectStore atomik protokolünde korunur.

235paket dosyası kaynak/wheel/installed byte eşitliği [manifest](phase37/wheel.json).
Installed console GUI_SMOKE PASS [çıktı](phase37/wheel-smoke.txt).
14belge unittest; docs/artifacts/learning/usability/Ruff check+format geçti.
Katalog53/221,21yeni çevrimdışı konu;130UIbinding,373namedfield.
Yeni dependency/lock değişikliği yok; kilitli CPython3.13.15.

Sınırlar: Kompozisyon linear/singlepanel; weight/facet/size uyumsuzlukları
ret. Girdi limitlerinde açık dur, sessiz TopN/sample/aggregation yok.
Dar GUI'de görüntü ölçeklenir; ayrıntılar method summary ve tam exportta.
GUI geliştirici kanıtı fiziksel/insan/AT kabulü değildir. F13insan,
F25insan/Orca/AT,F24minhardware/cold/physicalframe,F27kullanıcının
 durdurduğu dağıtım,F30büyükSAS,F31cleanofflinecache açıkları korunur.
Cleanofflineinstall/remoteCI burada koşulmadı. Wheel mevcut locked
bağımlılıklarla kurulmuştur. Kaynak belge/user değişiklikleri korunur;
stage/commit/push yapılmadı.

[Karar ve input şemaları](../adr/038-composition-charts-phase37.md).
