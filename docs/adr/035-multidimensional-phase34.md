# ADR-035 — Faz34 yerel çok boyutlu bilimsel veri

2026-10-11, DEC-34-01 açık kullanıcı talimatı. Yalnız Faz34.

Mevcut SourceAdapter/Capability registry, StructuredSettings, ComputeBudget ve
ProjectStore ACTIVE protokolü genişler. NetCDF3 SciPy; NetCDF4 h5netcdf;
Zarr2/3 xarray; açık dimension-scale HDF5 h5py read-only. Yeni tensor registry
veya tabela kolonlarından boyut çıkarımı yok.

Kaynak byte capture/hash korunur. Zarr kaynak parçaları güvenli ZIP capture,
doğrulanmış üyelerden yerel hardlink ağacı; canlı kaynak açılmaz. Parse öncesi
codec allowlist, external/soft/virtual/link ve16MiB chunk ret;256KiB metadata.
Lazy decoded erişim200 hücre segment: `.values` yalnız isel sonrası.
Önkontrol bütün seçili kesitin satır/muhafazakâr RAM/disk maliyetini hesaplar;
bütçe aşımı preview alanında görünür, veri okunmaz, yayın engellenir.

1–8 boyut, bir ölçüm değişkeni, bağımsız koordinat seçimi, sıfır tabanlı
pozitif adımlı indeks kesiti. Her boyut ve kaynak indeksleri tabloda korunur;
CF auxiliaries uyumlu alt boyutlarla tutulur. Takvim ham sayısal koordinat+
CF units/calendar olarak kalır; Gregorian varsayımı yok. Raw fill/scale
korunur, decode açık seçim; hedef dönüşüm yalnız decode ile Pint Quantity.to
üzerinden affine Celsius/Fahrenheit dahil. Uyumsuz birim reddedilir.

Native metadata kaynak dtype/shape/attrs/chunk ve normalize kesit taşır.
SourceRecordId/RowId mevcut format lineage ile, indeks/variable expansion
locator ile korunur. Table artifact ve portable raw capture aynı atomik
proje yayınına katılır; save/reopen ağı açmaz. Snapshot roundtrip metadata
korumasıdır; flat tabloyu NetCDF tensor export diye sunma yok.

Array heatmap iki farklı1D boyut koordinatı/indeks ve value; profile bir
boyut ve value ister. Verifiable origin zorunlu; ek boyut/duplicate için
explicit reject/mean/sum/median/min/max. Fill/scale decoded slice ister.
10k nokta ve dense grid boyutu kontrolü; boş hücre interpolasyonu yok.
Chart/analysis provenance kesiti korur; grafik aggregation ayrıca spec/details.
Kaynak membership mevcut immutable chart-members artifact içinde kalır.

Sınırlar: yerel kaynak, numeric/bool/fixed string; root NetCDF/Zarr group;
HDF5 her eksen tek scale ister. Object/vlen/complex, özel codec/plugin,
remote Zarr, CRS/reprojection, interval/time decode ve volume render yok.
Lazy decode kaynak bayt capture/hash'in bütün dosyayı okumasından farklıdır.
İnsan/AT/fiziksel/minimum donanım/temiz offline kurulum/uzak CI ayrı açık.

Birincil dayanaklar: [xarray lazy indexing](https://docs.xarray.dev/en/stable/generated/xarray.open_dataset.html),
[Zarr reader](https://docs.xarray.dev/en/stable/generated/xarray.open_zarr.html),
[HDF scales](https://docs.h5py.org/en/stable/high/dims.html),
[Pint offset units](https://pint.readthedocs.io/en/stable/user/nonmult.html).
Gerçek kabul: [PHASE34](../evidence/PHASE34.md).
