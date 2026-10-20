# ADR039 — Faz38 coğrafi veri ve çevrimdışı haritalar

2026-10-11; DEC-38-01; deneysel; yalnız Faz38 yetkisi.

Tek Capability/SourceAdapter registry genişler. Beş yerel kaynak: GeoJSON FeatureCollection; GeoPackage seçilmiş ordinary feature table; aynı basename .shp/.shx/.dbf, optional .prj/.cpg; GeoParquet1.0/1.1 WKB planar; self-contained GeoTIFF. Vektör10k feature ve min(256MiB,RAM/4), raster seçili band/window≤65536hücre; source block byte maliyeti önkontrol. Sidecar/WAL, VRT, spherical/native GeoParquet ve antimeridian crossing desteklenmez; açık ret, sessiz wrap yok. CRS bulunmadığında kullanıcı seçer; dosyada varsa override ret.

Snapshot kaynak byte'ları, source attribute kimlikleri/FID metadata, SourceRecordId/RowId/ColumnId korunur. WKB→tam koordinat WKT açık iç temsil dönüşümüdür; kaynak geometrisi otomatik tamir edilmez. Native parquet format metadata CRS/geometry types/extent/invalid reason/empty, GeoParquet geo JSON; raster affine/window/band/nodata/tags/units/chunks/versions taşır. Raster info piksel okumaz; yalnız window decode. Tablodan raster/çok boyutlu yapı uydurulmaz.

CRS atama koordinat değiştirmez; reprojection ayrı işlemdir. pyproj always_xy/only_best/no-ballpark; PROJ network kapalı. 2D xy zorunlu; latitude/longitude sıra aralıkları ve antimeridian kontrol edilir. Alan/buffer/distance/density metre axis kullanan projected CRS ve kullanım alanı ister; EPSG3857 ölçüm için reddedilir. Projeksiyon distorsiyonu devam eder. Kaynak ve hedef farklı CRS spatial join ret; kullanıcı önce reprojection yapar.

| Yöntem | Input / davranış |
|---|---|
| Nokta | Point WKT veya sayısal X/Y + açık CRS; bir source occurrence bir point |
| Choropleth | Polygon/MultiPolygon + nonnegative numerator; count veya positive finite denominator rate; equal interval/quantile/manual2–10class, eşik eşitliği üst sınıf; ties sınıf azaltır |
| Density | metre projected Point; grid count veya count/m²; KDE değildir; hücrede tüm RowId üyeleri |
| Raster | doğrulanmış GeoTIFF window + physical X/Y/value; nodata mask; seçili band; rotated/sheared plot ret |
| Repair | explicit make_valid linework; old/new types ve değişim sayısı önizleme; apply yeni immutable version; undo eski geometri |
| Spatial join | left geometry + immutable right version/geometry; intersects/within/contains; tüm matches JSON RowId listesi, source lineage artifact; sınırda çoklu eşleşme görünür; rows çoğaltılmaz |
| Clip | WKT mask aynı CRS; empty intersection açık sayımla dışlanır; source IDs korunur |
| Buffer/area/distance | pozitif finite metre radius, m² area veya reference WKT'ye minimum geometry distance; planar; buffer quad_segs16 |
| Spatial block | metre grid + seed +2–10fold; stable block column ve train/validation RowIds; mevcut modeling GROUP validation'a bağlanır; komşu blok bağımlılığı/buffer exclusion garantisi yok |
| Moran I | numeric value, queen/rook/distance komşuluk, binary/row normalization ve seed/permutations0–999;≤500features; isolated/constant ret; I=n/S0 zWz/z²; two-sided permutation expected-I çevresi |

Blok üretilmesi model fit etmez. Rastgele split mekânsal bağımlılığı çözmez; MAUP ve eşik/komşuluk seçimleri sonucu değiştirir. Harita brushing temsili point/hücre üyeliği üzerinden mevcut tablo seçimine bağlanır; filter copy ayrı eylemdir. Polygon yüzey hit-test ve RGB basemap compositor yok. Statik export CRS/scope/payda/threshold/nodata/attribution bağlamını saklar. Yerel harita basemapsiz, internetsizdir; online tile otomatik açılmaz.

Online: açık Read düğmesi, terms acknowledgement, attribution ve project-permitted cache. Public tek XYZ256/512PNG/JPEG tile,≤4MiB,z≤18; GTiff seçili band/window olarak preview. Tile auth yok. Geocoding provider-neutral id/record-list JSON GET ve kullanıcı field mapping; yalnız public veya sistem keyring bearer; adres otomatik gönderilmez, provider SDK/batch/oauth yok. Güvenli TLS, no redirects, bounded retry/rate/timeout/cancel; Cache-Control:no-store snapshot ret. Kaydetme/reopen ağ yapmaz. Gerçek yerel TLS fixture destek sözleşmesini doğrular; kamu sağlayıcı kullanım koşulu/entegrasyonu doğrulaması değildir.

[Pyogrio Arrow](https://pyogrio.readthedocs.io/en/latest/api.html),
[GeoParquet1.1](https://geoparquet.org/releases/v1.1.0/),
[Rasterio window](https://rasterio.readthedocs.io/en/stable/topics/windowed-rw.html),
[pyproj Transformer](https://pyproj4.github.io/pyproj/stable/api/transformer.html),
[Shapely make_valid](https://shapely.readthedocs.io/en/stable/reference/shapely.make_valid.html).

[Gerçek kanıt](../evidence/PHASE38.md). İnsan/AT/physical/minhardware/cleanofflineinstall/remoteCI bu fazda çalıştırılmadı; önceki kabuller açık.

Native coğrafi kütüphaneler yalnız ilgili okuyucu/işlemde yüklenir; registry deklarasyonu native backend yüklemez. Raster tablo value alanı Float64; int64/uint64 raster import kontrollü reddedilir, sessiz hassasiyet kaybı yok. Kaynak dosya korunur.

REV-38-01: Z/M geometri mekânsal işlem/reprojection sınırında reddedilir;
yalnız 2D xy, M değeri sessizce düşürülmez. Complex raster metadata preview
desteklenir fakat Float64 import sanal bileşen kaybına karşı kontrollü ret verir.
Geographic sınır/antimeridian doğrulaması CRS açısal birimini dikkate alır;
koleksiyonların bağımsız parçaları arasında kenar kurulmaz. Moran I kuvvet-iki
ölçekleme sonrası merkezlenir; küçük/büyük sonlu ölçümlerde quadratic
underflow/overflow engellenir. [İnceleme kanıtı](../evidence/PHASE38_REVIEW.md).

REV-38-02: koordinat/Moran ölçümlerinde Integer/Decimal→Float64 kaybı sessizce
uygulanmaz; önce kullanıcı tarafından açık tür/ölçek dönüşümü gerekir.
Moran sayısal fiziksel kolon ister; ortak offset merkezlemeden önce çıkarılır.
Raster map captured x/y/value kolonlarını kimlik üzerinden doğrular;
pixel index veya başka ölçüm kaynak pixel verisi yerine çizilmez.
[Devam incelemesi](../evidence/PHASE38_REVIEW2.md).
