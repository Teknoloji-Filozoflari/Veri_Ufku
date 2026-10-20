# Faz34 — gerçek teknik kabul kaydı

<a id="e34"></a>
2026-10-11; DEC-34-01; ENV-34 kilitli CPython3.13.15 Linux x86_64,
Qt6.11.2 offscreen/software. Ana kayıt REQUIREMENTS_MATRIX; resmi faz
sürüyor/deneysel/zorunlu; önceki resmî kabul açıkları korunur.

Yerel NetCDF/Zarr/HDF5 için tek registry içinde ayrı adaptörler; lazy kesit,
metadata-first maliyet, CF takvim/coords/chunk/fill/unit, Pint affine
dönüşümü, kimlikli Parquet ve atomik save/reopen. İki array grafik seçili
slice/explicit aggregation taşır; flat tablodan tensor sonucu üretilmez.

Gerçek 19 Faz34 test vakası başarılı:10 çekirdek +6 backend/güvenlik +3 GUI.
Üç format4 hücre beklenen kesit; metadata project roundtrip ve kaynağın
hash koruması. HDF/NetCDF h5py ve Zarr wrapper actual read spy yalnız
seçili indeksleri okur. Patlama önkontrolünde okuyucu poison hiç çağrılmaz.
360_day,5 boyutta ensemble/channel,2D auxiliary height, Zarr2/3;
offset Kelvin/Celsius/Fahrenheit, fill/packing, explicit unit/type ret;
cancel/time/source change/external link/pickle ret. GUI gerçek QML/spawn,
maliyet engeli, cancel,heatmap/profile,PNGexport,save/reopen,4F1/Escape.

Son tam regresyon **872 passed /589,39s /0failure-error-skip**;
[JUnit](phase34/pytest.xml), [çıktı](phase34/pytest.txt),
[19 gerçek faz vaka kimliği](phase34/test-cases.json).
Uygulama/test dosyaları bu koşudan sonra değişmedi; ek format/analiz/ölçek
betikleri ayrı gerçek doğrulamadır. 14 unittest ve son docs/artifacts/
learning/usability/Ruff kapıları [checks](phase34/checks.json) içinde.

Kaynak ve noneditable kurulu wheel üçer actual QML/spawn case,18'er render,
toplam36 PNG; her case dört F1/Escape konu bağı ve odak dönüşü. Gerçek
iptalde ACTIVE değişmez; tekrar kaynak seçimiyle sonuç alınır. Önkontrol
maliyet engeli,heatmap/profil,PNGexport/kayıt/reopen.
[Kaynak](phase34/source-gui/walkthrough.json),
[kurulu](phase34/wheel-gui/walkthrough.json). Dar maliyet/heatmap görselleri
araçla ayrıca incelendi; fiziksel masaüstü kabulü değildir.

226 package file source/wheel/installed byte eşitliği [wheel](phase34/wheel.json);
actual installed console **GUI_SMOKE PASS** [çıktı](phase34/wheel-smoke.txt).
Wheel bağımlılıkları gömmez. Kaynak ve wheel actual Pearson worker üzerinde
kesit provenance +save/reopen: [analysis](phase34/analysis.json),
[wheel analysis](phase34/wheel-analysis.json); r=1/sqrt(5) el referansı.
Gerçek klasik [NetCDF3](phase34/netcdf3.json) ve NetCDF4/Zarr2/3/HDF5 fixture.

[Bir milyar logical hücre](phase34/billion.json),35.728bayt sparseHDF5:
660.000.000.000bayt muhafazakâr tablo tahmini; preflight blocked,0decodedrow.
Aynı kaynakta explicit4hücre kesiti doğru okundu. Bu full1Bscan benchmark
veya gerçek çevresel dataset değildir; synthetic sparse fixture'dır.

[12 teknik madde C/V/G/H/P kaydı](phase34/acceptance.json),
[ENV-34](phase34/environment.json), kaynak/test/script/lock hashleri
[SHA256](phase34/source.sha256). Kaynak prompt hash'i unchanged;
çalıştırılmamış kontrol başarılı değildir.

İlk tanılarda testin ProjectStore.draft yerine mevcut state/publish_import
API'si, HDF DIMENSION_LABELS ndarray metadata, blocked preview uyarı
görünürlüğü, iptal sonrası yeniden kaynak seçimi, Matplotlib yeni tür başlığı
ve profil el referansı düzeltildi. Zarr asyncio sandbox içinde takıldı;
izinli dış ortamda gerçek yerel Zarr dosyaları geçti. Test ortamı ret başarı
sayılmaz. Kaynak belge değiştirilmedi; stage/commit/push yapılmadı.

Sınırlar ADR-035'te: raw CF zaman/kalender korunur, otomatik datetime yok;
HDF axis scale şartı,1–8boyut,16MiBchunk,256KiBmetadata,1024source member;
yerelrootgroups,numeric/fixedstring,200cellsegment,10kplotpoint/grid.
Lazy decode tam byte capture/hash ile karıştırılmaz. Bu testler fiziksel
desktop/insan/AT/minhardware/offlinecleaninstall/remoteCI kabulü değildir.
Önceki F13/F24/F25/F27,Faz30 büyükSAS ve Faz31 temizofflinecache açıkları
PROJECT_STATE içinde korunur.
