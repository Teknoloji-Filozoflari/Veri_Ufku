# Faz38 — coğrafi kaynaklar, haritalar ve mekânsal işlemler

<a id="e38"></a>
2026-10-11; DEC-38-01; ENV-38; kilitli CPython3.13.15.
24 teknik madde [C/V/G/H/P kaydı](phase38/acceptance.json).
Resmî kabul ve önceki bağımlılık kapıları ayrı; olgunluk deneysel.

Tek SourceAdapter/Capability registry; immutable capture/native DatasetVersion,
RowId/SourceRecordId/ColumnId, Qt-free worker, ComputeBudget ve atomik
ProjectStore preview/apply/undo protokolü genişletildi. Beş gerçek okuyucu:
GeoJSON, GeoPackage layer, Shapefile bileşenleri, GeoParquet, GeoTIFF window.
CRS/xy/type/extent/nodata/invalid reason paneli; source geometry/FID ve
GeoParquet/raster metadata korunur. CRS atama/reprojection ayrıdır;
pyproj offline/always_xy/no-ballpark. Metre hesaplarında uygun projected
CRS, kullanım alanı; geographic degree ve ölçümde EPSG3857 ret.
Antimeridian crossing ve unsupported geometri/encoding açık ret.

Dört offline harita: nokta, choropleth, projected grid density ve raster.
Choropleth count/rate/positive denominator/equal interval/quantile/manual;
eşik equality üst sınıf, quantile ties açık. Density count veya count/m²,
KDE değildir. Seçili band/window raster nodata mask/physical coordinates.
Legend, CRS/payda/eşik/nodata/attribution metadata ve exportta görünür.
11 mekânsal işlem: koordinattan geometri, CRS atama/reprojection,
önizlemeli make_valid, buffer, area/distance, clip, tüm eşleşmeli join,
seeded spatial blocks ve explicit neighborhood Moran I.

[74 hedefli test](phase38/targeted.xml):30core+20offlineGUI+9TLS/onlineGUI +15 lifecycle/imputation compatibility;
171.13s,0failure/error/skip. Gerçek Pyogrio/Arrow/Rasterio fixture:
1derece→111319.490793m referansı,3–4–5mesafe, buffer/area,
sınırda çoklu spatial join ve right RowId kökeni; repair kaynak değiştirmez,
apply/undo geometriyi geri getirir. Raster metadata decode yapmaz;
read spy yalnız seçili Window'u doğrular. Moran elle I=0,S0=4,
expected=-.5; explicit seed/permutation. Üretilen spatial block sütunu
mevcut GroupShuffleSplit/GroupKFold yolunda group leakage yapmaz;
komşu blokların bağımsızlık garantisi yok, random split çözüm değildir.
[Gerçek vaka listesi](phase38/test-cases.json).

Gerçek yerel TLS fixture'da public tile/geocoding GET; açık QML Read,
terms/attribution/cache zorunlu, bounded retry/timeout/cancel/redirect ret.
Cache-Control:no-store ret; reopen/save HTTP sayısı artmaz. Test tokenları
ve keyring sınırı önceki connector protokolünde; log/export credential yok.
Kamu sağlayıcı entegrasyonu veya servis koşulu kabulü iddia edilmez.
[9 ağ/QML vaka çıktısı](phase38/network.txt).

Kaynak ve noneditable installed wheel20'şer gerçek QML/worker/preview/
apply/undo/save/reopen veya maps F1/Escape/export/openSaved yolu.
40+40geniş/dar görüntü;12+12PNG/SVG/PDF export.
[Kaynak](phase38/source-gui/walkthrough.json),
[kurulu](phase38/wheel-gui/walkthrough.json).
PDF Poppler metin+raster ve SVG CRS/offline bağlam kontrolü;
[geliştirici görsel inceleme](phase38/visual-review.json).
int64/uint64 raster Float64 precision kaybına karşı kontrollü ret; kaynak değişmez. Registry native GIS kütüphanelerini yüklemez; ilgili backend yalnız eylemde yüklenir.

244paket dosyası kaynak/wheel/installed byte eşitliği
[manifest](phase38/wheel.json); fresh XDG installed GUI_SMOKE PASS
[çıktı](phase38/wheel-smoke.txt).

Katalog54/231;10 yeni çevrimdışı konu ve134UIbinding.
[Learning](phase38/learning.txt),[usability](phase38/usability.txt),
14belge unittest [çıktısı](phase38/unittest.txt).
Shapely2.2.0/pyproj3.7.2/Rasterio1.5.1/Pyogrio0.13.0 ve4transitive
runtime dependency kilitlendi; [gerçek lisans/NOTICE envanteri](../third_party/phase38/manifest.json).
[Ortam](phase38/environment.json),[ADR039/input şemaları](../adr/039-geospatial-phase38.md).

Sınırlar: Vektör10k feature, raster65536hücre ve captured block/RAM maliyeti;
rotated/sheared raster plot, external sidecar/VRT, GeoParquet spherical
ve native encoding, antimeridian wrap desteklenmez. Harita basemapsizdir.
Brushing temsili point/hücre üyeliği; polygon yüzey hit-test yok.
Online tile tek public XYZ256/512 color band/window preview; RGB basemap
compositor ve tile auth yok. Geocoding provider-neutral id/record-list JSON
GET/field mapping; public veya keyring bearer, provider SDK/oauth/batch ve
otomatik adres gönderimi yok. Bu kapsam UI/yardımda açık.

İlk regresyonda conditional local math importunun eski grafik doğrulamasını
bozduğu görüldü, import düzeltildi; [ilk hata](phase38/initial-regression-error.txt)
ve [durdurulan koşu](phase38/interrupted-regression.txt) saklandı.
REST ProjectError ile cache no-store kuralı genel bağlantı hatası olarak yeniden denenmiyor; [gerçek tek GET/ret](phase38/geocoding-cache.json). [10×10m polygon area100m²](phase38/area-reference.json) kaynak/RowId korunumuyla ek doğrulandı.
Sözlük F1 testinde export sonrası kaynak-directory refresh işlemi bitmeden devre dışı Grid alanına odak gönderildiği görüldü. Test projects.busy/alan enabled durumunu bekler ve gerçek activeFocus'u doğrular; hesap/yayın davranışı değişmedi. [Hata kaydı](phase38/focus-disabled-error.xml).
30geo/network/lifecycle sıra testi aynı budget ile geçti; Qt DeferredDelete test temizliği [kanıt](phase38/memory-sequence.txt). Önceki monolithic koşu eski GUI fixture nesneleriyle memory budget'e takıldı; [hata](phase38/memory-regression-error.xml). Son fixture temizliği kapalı Qt nesnelerinin DeferredDelete yayınını işler, uygulama kaynak referansını bırakır ve kullanılmayan Arrow/glibc heap alanını iade eder. GIS backendleri de yalnız ilgili kullanıcı eyleminde yüklenir. [Lazy registry kontrolü](phase38/lazy-registry.txt). Bütçe gevşetilmedi.
Başarısız koşular kabul olarak sayılmaz. Son kaynakta **1075 tam pytest** / 1124.90s / 0failure-error-skip geçti. [JUnit](phase38/full-regression.xml), [çıktı](phase38/full-regression.txt), [özet](phase38/full-summary.json). 379 kaynak/test/script/lock dosyası koşu boyunca değişmedi: [hash kontrolü](phase38/head-verification.json). Export sonrası gerçek refresh/aktif odak beklemesiyle [13 connector/sözleşme GUI](phase38/focus-sequence.txt) ayrıca geçti.

F13insan,F25insan/Orca/AT,F24minhardware/cold/physicalframe,F27kullanıcının
 durdurduğu dağıtım,F30büyükSAS,F31cleanofflinecache açıkları korunur.
Fiziksel/insan/AT/minHW/cleanofflineinstall/remoteCI bu fazda koşulmadı.
Mevcut locked ortamda local offline çalışma, temiz offline kurulum değildir.
Kaynak belge ve kullanıcı değişiklikleri korunur; stage/commit/push yapılmadı.

2026-10-11 yeniden inceleme: [REV-38-01](PHASE38_REVIEW.md).
Z/M dönüşüm kaybı, complex raster kaybı, grad birimi, koleksiyonlarda
antimeridian kenarı ve Moran sayısal ölçek sorunları ek regresyonlarla düzeltildi.
Önceki teslim kanıtları korunur; güncel doğrulama ve eşzamanlı Faz39 etkisi ayrı kayıttadır.

[REV-38-02 devam incelemesi](PHASE38_REVIEW2.md): kayıpsız sayısal koordinat/Moran
sınırı, captured raster sütun eşlemesi ve büyük offsette Moran merkezleme
ek referanslarla düzeltildi; test ve wheel kanıtları ayrı kaydedildi.
