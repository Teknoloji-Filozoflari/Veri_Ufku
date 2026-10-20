# Üçüncü taraf kayıtları — Faz 01

2026-10-06. Faz27 kullanıcı kararı: GPL-3.0-or-later; dağıtım adayı kabulü yoktur. uv.lock sürüm/hash ana kaydıdır.

| Bileşen | Lisans kaynağı / yükümlülük |
|---|---|
| PySide6, shiboken6, Qt paketleri 6.11.2 | Kurulu dist-info LICENSES ve [Qt lisans belgeleri](https://doc.qt.io/qt-6/licensing.html); LGPLv3/GPL/commercial ve modül bazlı koşullar. Yeniden dağıtımda ilgili metin/bildirim, LGPL değiştirme/yeniden bağlama imkânı gerekir. |
| Ruff 0.16.10 yerel dev wheel | Wheel içindeki ruff-0.16.10.dist-info/licenses/LICENSE (MIT); yeniden paketlemede korundu. Manifest sha256 ve RECORD kontrolü uygulanır. Runtime'a paketlenmez. |
| pytest 9.1.1 | dist-info lisans (MIT), dev bağımlılığı. |
| Python / build ve transitif dev paketleri | Dağıtılan artefactın dist-info lisansları korunmalı; tam uygulama bundle lisans envanteri paketleme fazında doğrulanacak. |

Marka, ikon veya referans uygulama varlıkları alınmadı. QML native controls ve metin kullanır. Bu kayıt tüm gelecekteki analitik paketlerin lisans kabulü değildir.

Faz04: Polars 2.0.0 ve polars-runtime-32 2.0.0, kurulu dist-info/licenses/LICENSE içinde MIT izin/bildirim metni taşır. Ritchie Vink ve NVIDIA katkı bildirimleri korunur. uv.lock tam sürüm/hash kaydıdır; Parquet roundtrip gerçek kurulu paketle geçti. Uygulama wheel’i dependency wheel’lerinin yerine geçmez; dağıtım bundle lisans envanteri sonraki paketleme fazında tamamlanacaktır.

Faz11: DuckDB1.5.6 yalnız kilitli dev karşılaştırma bağımlılığıdır; runtime uygulama wheel'ine paketlenmez. Kurulu `duckdb-1.5.6.dist-info/licenses/LICENSE` MIT metni içerir; yeniden dağıtılırsa bildirim korunmalıdır. ODS/SQLite stdlib, IPC Polars okuyucusu kullanır; odfpy/PyArrow/pandas bağımlılığı eklenmedi. [ADR-014](adr/014-transformations-phase11.md).


Faz14: SciPy1.18.0 runtime dependency, BSD-3-Clause ve wheel içinde OpenBLAS/LAPACK/GCC runtime ile ilgili ayrı bildirimler. Kurulu gerçek lisanslar/hash'ler [phase14 envanterinde](third_party/phase14/manifest.json) kopyalandı; dependency wheel'leri uygulama wheel'ine gömülmez. uv.lock tam artifact sürüm/hash ana kaydıdır. Bu kayıt tüm dağıtım bundle lisans kabulü değildir.

## Faz16

scikit-learn1.9.1 ve yeni transitif joblib1.6.0/cloudpickle3.1.2/narwhals2.26.0/threadpoolctl3.7.0 exact runtime lock. Gerçek kurulu lisans metinleri/hash/expression [phase16 envanterinde](third_party/phase16/manifest.json) korunur. Uygulama wheel bağımlılıkları içine gömmez; bundle lisans kabulü ayrı gelecek kapsamdır.

Faz19 mevcut kilitli scikit-learn1.9.1/NumPy/Polars/threadpoolctl paketlerini
kullanır; yeni bağımlılık, indirme veya dış sprite/görsel/model eklenmedi.
Önceki lisans envanteri korunur; KMeans/DBSCAN/IsolationForest API belgeleri
kaynak bağlantısı olarak yardımda yer alır, belge/görsel metinleri kopyalanmaz.

Faz20 ek kilitli runtime: skops0.16.0 (BSD-3-Clause), prettytable3.18.0
(BSD-3-Clause), wcwidth0.9.2 (MIT); dağıtım lisansları paket dist-info içinde
korunur. Gerçek lisans kopyaları/hash [Faz20 envanterinde](third_party/phase20/manifest.json). Skops güvenlik sürüm/tip kısıtları ADR-023'te kayıtlıdır.


Faz21 kilitli statsmodels0.15.0 ve pandas3.0.6/patsy1.0.3/formulaic1.2.2/
interface-meta2.0.1/typing-extensions4.16.0/wrapt2.5.0 transitif runtime. Gerçek
kurulu lisansların kaynak yolları ve SHA256 [Faz21 envanterinde](third_party/phase21/manifest.json)
korunur; bağımlılık wheel'leri uygulama wheel'ine gömülmez. Bu kayıt tam bundle kabulü değildir.


Faz22 mevcut kilitli scikit-learn/NumPy/SciPy/Polars ve Python Unicode
veritabanını kullanır; yeni paket/embedding/API/model indirme eklenmedi. Küçük
TR/EN stopword listeleri projede yazılmıştır; harici dil kaynağı taşınmaz.
Mevcut bağımlılık lisans kayıtları korunur.


Faz27: tam runtime RECORD/hash envanteri gerçek bundle içinde /app/share/veri-ufku/runtime-inventory.json yolundadır. Qt/PySide wheel metinleri eksikse upstream kaynak/license tamamlanmadan lisans dağıtım kapısı kabul edilmez. [Karar ve koşullar](LICENSING.md).

Faz30 yeni exact runtime: pyarrow26.0.0 (Apache-2.0), fastavro1.13.1 (MIT), h5py3.16.0 (BSD-3-Clause; bundled component lisansları dahil), pyreadstat1.3.6 (Apache-2.0/ReadStat MIT), defusedxml0.7.1 (PSF). Gerçek kurulu metinler/hash [envanterde](third_party/phase30/manifest.json). SAS küçük fixture kaynak revision/blob ve lisansı [fixture envanterinde](evidence/phase30/fixtures.json); PYREADSTAT_LICENSE korunur. Sentetik fixture'lar projede üretilen CC0 örneklerdir. Bu wheel bağımlılıkları içine gömmez; temiz bundle/dağıtım kabulü ayrı açık.

Faz31 isteğe bağlı connectors: psycopg/psycopg-binary3.3.6 (LGPL-3.0-only),
PyMySQL1.2.3/keyring25.7.0 (MIT), boto3/botocore1.43.111 (Apache-2.0),
DuckDB1.5.6 (MIT); SecretStorage3.5.0 (BSD-3-Clause) ve transitif paketler.
[Gerçek kurulu lisans/NOTICE metinleri ve SHA256](third_party/phase31/manifest.json)
korunur. Uygulama wheel'i bu bağımlılıkları veya test sunucusu binary'lerini
gömmez; psycopg-binary bundled component ve temiz dağıtım kabulü ayrıca
Faz27 kapısına bağlıdır. PostgreSQL/MySQL/MariaDB/SeaweedFS/GNOME-keyring
yalnız /tmp sentetik kabul ortamında kullanıldı; sistem servisi kurulmadı.


Faz34 xarray/h5netcdf/Zarr/Pint ve12 yeni runtime dependency için gerçek kurulu lisans/NOTICE metinleri/hashleri [envanterde](third_party/phase34/manifest.json). Sürümler uv.lock/pyproject ile kilitlidir. Wheel bağımlılıkları gömmez; temiz dağıtım Faz27 ayrı kapıdır.


Faz38: Shapely2.2.0, pyproj3.7.2, Rasterio1.5.1, Pyogrio0.13.0 ve dört transitive dependency kilitli. Gerçek kurulu dağıtım lisans/NOTICE metinleri ve hashleri [manifestte](third_party/phase38/manifest.json); PROJ/GEOS/GDAL bundled notices dahil. Uygulama wheel'i bu bağımlılıkları gömmez. Temiz offline dağıtım ayrı kabul kapısıdır.


Faz43 optional backend ve18 transitives için kurulu dağıtım lisans dosyaları [manifest](third_party/phase43/manifest.json) içinde; PyMC/ArviZ/Numba/LLVM/PyTensor bir executable kullanıcı model paketi değildir. Önceki envanter korunur.

Faz56 optional `torch2.13.0+cpu` resmi CPU index; uygulama wheel'i framework wheel'ini
ve pretrained model ağırlıklarını içermez. Torch ve yeni transitif paketlerin installed
lisans metni/hash/expression [envanterde](third_party/phase56/manifest.json) korunur.
uv.lock sürüm/URL/hash kaydıdır; tüm bundle dağıtım/lisans kabulü ayrı açık kalır.

## Faz58 ses paketleri

SoundFile0.13.1 core + optional Vosk0.3.45/audio-speech ve yeni transitives.
Kurulu distribution lisans metinleri [phase58](third_party/phase58/) altında;
[hash/sürüm kaydı](evidence/phase58/licenses.json). Vosk metadata UNKNOWN; bu kayıt
binary/source lisans dağıtım kapanışı değildir. Model ağırlığı indirilmedi; kullanıcı
local model için dil/lisans/dataset/hash beyanı sağlar. Önceki dağıtım audit açıkları korunur.

Faz61 NetworkX3.7 BSD-3-Clause çekirdek graph backend; [installed LICENSE](third_party/phase61/networkx-3.7-LICENSE.txt),[hash](evidence/phase61/license.json). Önceki dağıtım audit açıkları korunur.

Faz66 optional Dask2026.8.0 (BSD-3-Clause), distributed2026.8.0 (BSD-3-Clause)
izole /tmp doğrulama ortamında; çekirdek venv/lock değiştirilmedi. Yerel adaptör
Dask local-threads kullanır, distributed/remote executor unavailable.
Resmî API/TLS/memory/retry kaynakları [ADR067](adr/067-compute-budgets-phase66.md).

Faz72 optional privacy extra `cryptography50.0.2` ve `keyring25.7.0` mevcut Faz31
kilitli paketlerini kullanır; yeni kripto uygulaması yoktur. Lisans kayıtları
[mevcut manifestte](third_party/phase31/manifest.json) korunur; Fernet uygulama
wheel'ine gömülü özel kripto değildir. Secret Service oturum desteği ayrı sistem
bağımlılığıdır; canlı daemon bulunmayan ortam doğrulanmış kabul edilmez.


## Faz74 dağıtım profilleri

Yeni third-party runtime sürümü eklenmedi. Faz58 SoundFile ve Faz61 NetworkX artık
core zorunluluğu yerine sırasıyla audio/graphs extras; fastavro/pyreadstat formats,
array/native geospatial paketleri kendi extras grubundadır. Torch CPU/neural optional
kalır. Önceki exact lisans kayıtları geçerlidir; bu ayrım model/data lisansını uygulama
lisansına dönüştürmez. Model ağırlığı indirilmedi veya candidate'a gömülmedi.
`release_inventory.py` CycloneDX1.6 Python SBOM scope'unu core veya seçili extras
olarak kaydeder. OS/runtime/native/driver/model-data tam SBOM olduğu iddiası yoktur;
license-expression bulunmayan metadata review ister. Flatpak native dosya hash'leri
ve exact Platform/BaseApp commitleri ayrıca paket kaydındadır.
[Gerçek scan ve kapsam](evidence/PHASE74.md#e74-supply-chain).
