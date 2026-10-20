# Veri_Ufku — ortam ve resmî uyumluluk incelemesi

İnceleme tarihi 2026-10-06; ortam kimliği ENV-00. Kanıt [phase00 raporu](evidence/PHASE00.md). Gözlem ≠ paket desteği ≠ release kabulü.

| Alan | Gözlenen |
|---|---|
| OS/session | CachyOS rolling, Linux 7.2.9-1-cachyos, x86_64, Wayland; DISPLAY=:0 mevcut |
| CPU/RAM | Ryzen 7 8845HS, 8 core/16 thread, AVX2; 31,388 MiB RAM, 31,387 MiB swap |
| Disk | NVMe Btrfs, 667 GiB boş; /tmp 16 GiB tmpfs |
| Runtime | Python 3.14.7; glibc 2.44; SQLite 3.53.4 |
| Kurulu | PySide6/Qt 6.11.2, Matplotlib 3.11.2, NumPy 2.5.3, pytest 9.1.1, ruff 0.16.10; uv CLI 0.12.23 |
| Eksik | Polars, DuckDB, scikit-learn, SciPy, statsmodels; Python 3.13; Xvfb |
| Qt/font | Qt plugin path /usr/lib/qt6/plugins; Noto Sans system font |
| Depo | Sadece birleşik prompt vardı; AGENTS.md/kod yoktu. .git boş/salt okunur, git status başarısız; remote/commit yok. |

## Resmî kaynak kaydı

2026-10-06'da aşağıdaki sayfalar web aracıyla okundu. `stable` sayfaları değişebilir; sürüm etiketi paketin burada kurulduğunu veya uyumlu kilit çözüldüğünü göstermez. İncelenen doküman ile yerel runtime sürümü farklı olan yerler özellikle kayıtlıdır.

| Araç ve kaynak | Görülen destek bilgisi | Bu ortam kararı |
|---|---|---|
| [Qt for Python getting started](https://doc.qt.io/qtforpython-6/gettingstarted.html) | Python≥3.10, izole ortam önerisi; wheel Qt içerir | Yerel Qt 6.11.2 QML Controls offscreen load 1 root; sistem paketini lock sanma |
| [Qt Quick Controls](https://doc.qt.io/qt-6/qtquickcontrols-index.html) | Qt Quick kontrol seti; sayfa Qt 6.12 etiketiyle geldi | Exact 6.11.2 paket QML API/plugin testi Faz 01'de, resmî sayfa yeni sürüm olabilir |
| [Polars install](https://docs.pola.rs/user-guide/installation/) | CPU uyumluluğu/rtcompat, lazy/optional deps, varsayılan 2^32 row index sınırı | CPU AVX2 var; kurulu değil; exact Python wheel uyumu henüz doğrulanmadı |
| [DuckDB Python](https://duckdb.org/docs/current/clients/python/overview) | Python≥3.10, sayfa stable 1.5.6 bildiriyor | Kurulu değil; disk/SQL gerektiğinde; stable redirect ilk URL'de yalnız yönlendirme verdi, current okundu |
| [scikit-learn install](https://scikit-learn.org/stable/install.html) | İzole binary wheel önerisi, bağımlılık alt sınırları; doküman 1.9.1 | Kurulu değil; Python minimum tek başına 3.14 ABI uyumu kanıtlamaz |
| [SciPy toolchain](https://docs.scipy.org/doc/scipy/dev/toolchain.html) | Tablo 1.16 için Python≥3.11,<3.14, NumPy≥1.25.2,<2.6 | Yerel 3.14 ile bu satır uyumsuz; yeni 1.18 başlıklı sayfa tüm yeni sürüm destek tablosunu göstermedi. CPython3.13 başlangıç adayı; çözüm doğrulanmadı |
| [statsmodels install](https://www.statsmodels.org/stable/install.html) | Python≥3.9; NumPy/SciPy/Pandas/Patsy bağımlılıkları, doküman 0.15.0 | İhtiyaçta optional; kurulu değil; Pandas'ı genel tablo çekirdeği yapma gerekçesi yok |
| [Matplotlib backend](https://matplotlib.org/stable/users/explain/figure/backends.html), [Qt example](https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html) | Agg/render/export ve Qt bindings; QWidget örneği | Agg blank render çalıştı; QML bridge ADR-002; gerçek grafik/export etkileşimi yok |
| [QQuickImageProvider](https://doc.qt.io/qt-6/qquickimageprovider.html) | QImage async/thread/cache davranışı; doküman Qt6.12 | Sürümlü QImage aktarımı planı; exact API Faz 12 |

Lisans kaynakları/yükümlülükleri [ADR-004](adr/004-offline-licensing-packaging.md). Çekirdeğin tümüyle Python3.14 destekli olduğu iddia edilmez. Sürümler tahminle requirements'a yazılmadı. Faz 01 exact patch+ABI/wheel+transitif solver+import smoke+uv.lock ile karar kapanır. Faz 00 görevimiz bu çözümün planını hazırlamaktır; uygulama iskeleti veya kurulum yapılmadı.

## Gerçek denemeler ve sınırlar

`QT_QPA_PLATFORM=offscreen` altında geçici ApplicationWindow+Button QML 1 root üretti; yaklaşık 37 ms tek probe süresi uygulama açılış benchmark'ı değildir. Qt6.11.2 runtime; Agg 100×100 RGBA buffer=40,000 byte. Matplotlib sistem config path'i yazılamadı ve /tmp fallback uyarısı çıktı; yeniden üretilebilir probe `MPLCONFIGDIR` writable temp kullanır. Ürün XDG cache seçimini Faz 01'de uygular.

Masaüstü kullanıcı testi, X11, HiDPI, hedef 8GB donanım, analitik import veya paket smoke yapılmadı. Terminal ağ DNS erişimi başarısız; resmî belgeler web aracıyla erişilebilir. Gerçek registry çözümü yapılmadı. Ağ/izin belirsizliğini kurulmuş/locked saymayacağız.

## ENV-01 — 2026-10-06 Faz 01

CachyOS x86_64 Linux 7.2.9, Ryzen 7 8845HS, 32GB, Btrfs; /tmp tmpfs. CPython 3.13.15 uv-managed kurulum bu fazda bulundu; ENV-00 bulgusu tarihseldir. Sistem Python 3.14.7 değiştirilmedi. İzole .venv PySide6 6.11.2, pytest 9.1.1, Ruff 0.16.10, uv 0.12.23. Lock gerçek offline resolver ile üretildi. İkinci temiz venv ve noneditable wheel headless smoke çalıştı. Terminal registry DNS erişemedi; önceden mevcut cache kullanıldı.

Qt offscreen/software ekran ve worker testi geçti. Wayland wl_display Operation not permitted ile, X11 display :0 bağlantı hatası ile açılmadı (exit134); gerçek desktop doğrulanmadı. Ubuntu CI hedefi burada çalıştırılmadı; remote yok. [Faz 01 kanıtı](evidence/PHASE01.md), [ADR](adr/005-runtime-jobs-lock.md).

## ENV-USER-01 — 2026-10-06 kullanıcı masaüstü bildirimi

Kullanıcı yerel uygulamada CPU, I/O ve belirsiz ilerleme iptal/tamamlanma denemelerini bildirdi. Masaüstü backend, tam çalıştırma komutu, Python/Qt/binary hash ayrıca bildirilmedi; ENV-01 ile birebir ortam eşitliği varsayılmaz. Bu kanıt bildirilen eylemlerle sınırlı manuel kullanıcı kontrolüdür; performans veya bağımsız ajan masaüstü testi değildir. [Kanıt](evidence/PHASE01.md#e01-user-desktop).

ENV-USER-01 devam bildirimi: kullanıcı görev sırasında yapılandırma/eski sonuç, anlaşılır hata/takip kimliği ve aktif görevde kapanış için verilen üç kontrolün hepsinin çalıştığını bildirdi. Bu senaryolar manuel kabul kaydına eklendi; runtime/backend/hash belirsizliği korunur.

## ENV-04 — 2026-10-06

CachyOS x86_64 Linux7.2.9/glibc2.44; CPython3.13.15, PySide6/Qt6.11.2, SQLite3.53.1, Polars/runtime-32 2.0.0. Btrfs NVMe üzerinde izole proje testleri ve offscreen/software Qt; geliştirme testleri tmpfs üzerinde de geçti. Tam lock/fixture hash, runtime ve fs [phase04-headless.json](evidence/phase04-headless.json); [kabul sınırları](evidence/PHASE04.md). Yeni remote/gerçek masaüstü/ağ FS/güç kaybı deneyi yapılmadı.

## Faz05 uygulama bağı

ENV-05 mevcut locked CPython3.13.15/PySide6 6.11.2/Polars2.0.0 üzerinde ilk gerçek CSV/TSV import, Qt offscreen/software, yerel Btrfs GUI ölçümü ve /tmp pytest. Kaynak resmi Python CSV/Polars sink_parquet belgeleri incelendi; yeni dependency yok. [Kanıt](evidence/PHASE05.md), [ham ölçüm](evidence/phase05-headless.json). Minimum donanım/native masaüstü/uzak CI ayrı açıktır.

ENV-06: ENV-05 locked Linux/CPython3.13.15/Qt6.11.2/Polars2.0.0 aynı; native import için ek paket yok. Wheel target kurulum /tmp/veri-ufku-phase06-installed, runtime locked .venv. [Ham ortam/ölçüm](evidence/phase06-headless.json), [kanıt](evidence/PHASE06.md#e06-environment).

## Faz07 katkısı

ENV-07 (2026-10-06): aynı yerel Linux7.2.9 CachyOS/glibc2.44/Btrfs; CPython3.13.15/Qt6.11.2/Polars2.0.0, offscreen/software. 100.000 kayıt16 sayfa/full profil ve kurulu Linux wheel worker. Minimum donanım/native masaüstü/remote CI ayrıca doğrulanmadı. [Ham kayıt](evidence/phase07-headless.json).

ENV-USER-07 (2026-10-06): kullanıcı masaüstünde Veri tablosunun açılması ve yenilenmesi başarılı bildirildi. Dosya/ortam ayrıntısı verilmedi; diğer manuel kabul kapsamlarına genellenmez. [Kayıt](evidence/PHASE07.md#e07-user-table).

## Faz08 katkısı

ENV-08, 2026-10-07: locked CPython3.13.15/PySide6Qt6.11.2/Polars2.0.0, Linux7.2.9/glibc2.44 geliştirici Btrfs ve /tmp tmpfs; offscreen/software. Yeni bağımlılık yok; gerçek masaüstü ve minimum donanım ayrı doğrulanmadı; uzak CI başarı kaydı ENV-CI-08 içindedir. [Karar](adr/011-quality-phase08.md), [kanıt](evidence/PHASE08.md).

## ENV-CI-08 — kullanıcı uzak CI bildirimi

Kayıt 2026-10-06 UTC / 2026-10-07 Europe/Istanbul. Linux işi112505393392, koşu37532581621,1m12s,success. Yerel workflow Ubuntu24.04/offscreen/software/izole XDG hedefler; fiilî runner metadata/runtime sürümleri/lock hash özette yoktur. Başarı kullanıcı çıktısı ve sonradan gh API sorgusuyla doğrulandı; headSha e9fd13f41afb83daaca1c3790e8dc1e14a58d3cb Faz08 dosyalarını içerir. [Kayıt](evidence/PHASE08.md#e08-ci-remote).

## ENV-10 — 2026-10-07 temizlik araçları

Aynı yerel CachyOS/Ryzen7/32GB/Btrfs/tmpfs; kilitli CPython3.13.15/PySide6Qt6.11.2/Polars2.0.0, offscreen/software. Şema6, kaynak ve lock SHA256, gerçek wheel ve fixture hashleri [ortam kaydında](evidence/phase10-environment.json). Sistem Python3.14 ortamındaki unittest import hataları ayrı başarısız kayıt; kilitli kontroller ve gerçek paket akışı [Faz10 kanıtında](evidence/PHASE10.md). Yeni masaüstü/remote CI/minimum donanım kabulü değildir.


## Faz11 katkısı

ENV-11 /2026-10-07: aynı yerel CachyOS Linux7.2.9/Ryzen7/32GB/Btrfs/tmpfs, locked CPython3.13.15/PySide6Qt6.11.2/Polars2.0.0/DuckDB1.5.6(dev), offscreen/software. Şema7. Kaynak/lock/fixture/wheel hashleri ve gerçek kapılar Faz11 kanıtında; yeni masaüstü/remote/minimum donanım ayrı açık. [Karar](adr/014-transformations-phase11.md), [kanıt](evidence/PHASE11.md).


## ENV-12 —2026-10-07

Yerel CachyOS Linux7.2.9/glibc2.44/Ryzen7 8845HS/32GB; Btrfs proje ve /tmp tmpfs; locked CPython3.13.15/PySide6Qt6.11.2/Polars2.0.0/Matplotlib3.11.2. Yeni NumPy/font/native transitifler uv.lock'ta; lisans metinleri [envanterde](third_party/phase12/inventory.json). Offscreen/software kaynak ve kurulu noneditable Linux wheel100k gerçek grafik/QML/export/process testleri. Sistem Python3.14 ayrı ortamdır. [Ham ortam/hashler](evidence/phase12-environment.json), [kanıt](evidence/PHASE12.md). Yeni fiziksel masaüstü/minimum donanım/uzak CI ve temiz offline kurulum doğrulanmadı.

## ENV-13 — Faz13 yerel teknik kanıt

2026-10-07, aynı CachyOS/Linux7.2.9/glibc2.44/Ryzen7 8845HS/32GB ortamı; Btrfs proje/tmpfs temp, CPython3.13.15/Qt6.11.2/Polars2.0.0/Matplotlib3.11.2 locked. [Ayrıntı](evidence/phase13-environment.json), [kaynak](evidence/phase13-headless.json), [noneditable wheel](evidence/phase13-wheel.json). Offscreen/software, fresh XDG ve Python TCP fail-fast parent/spawn; OS ağ arayüzü kapatıldı veya temiz offline kurulum yapıldı iddiası yok. Sistem Python3.14 uygun runtime değil ve ayrı unittest başarısızlığı kaydedildi; locked kontroller kullanılır. Gerçek bilgisiz kullanıcı yok.


## ENV-14 — 2026-10-08

Linux yerel geliştirici çalışma alanı, Python3.13 locked runtime, PySide6/QML offscreen/software, SciPy1.18.0 ve NumPy2.5.3. Gerçek sürüm/API, paket yolu, süre/RSS/tick ve kaynak hash'leri [source](evidence/phase14/headless.json) ve [kurulu wheel](evidence/phase14/wheel.json) kayıtlarındadır. Sistem Python ayrı kontrol edilir. İnsan kullanıcı, fiziksel masaüstü ve minimum donanım kabulü iddiası yok. [Kontroller](evidence/phase14/checks.json).

## ENV-15 — 2026-10-08

ENV-14 locked Linux/CPython3.13.15/PySide6Qt6.11.2/Polars2.0.0 aynı; yeni runtime bağımlılığı yok. Sklearn resmî rehberi yalnız tasarım için incelendi; kurulu sklearn API veya eğitim desteği yok. Kaynak ve kurulu Linux noneditable wheel offscreen/software hazırlık akışları; fresh XDG/Python TCP reddi, OS ağ kapama veya temiz offline kurulum iddiası yok. [Kanıt](evidence/PHASE15.md), [kaynak](evidence/phase15/headless.json), [wheel](evidence/phase15/wheel.json).

## ENV-UI-HOME-COMPACT — 2026-10-08

Mevcut locked CPython3.13.15/PySide6Qt6.11.2 Linux, offscreen/software, geçici XDG. Yeni bağımlılık yok. Başlangıç/klasör dialogları kaynak ve kurulu noneditable wheel ile doğrulanır; fiziksel masaüstü/insan testi ayrı. [Ortam](evidence/ui-home-compact/environment.json), [kanıt](evidence/UI_HOME_COMPACT.md).

## ENV-20 — 2026-10-09

Linux7.2.9-2-cachyos x86_64/glibc2.44, Ryzen7 8845HS/32GB/Btrfs;
kilitli CPython3.13.15/PySide6Qt6.11.2/scikit-learn1.9.1/skops0.16.0,
offscreen/software ve geçici XDG. Exact bağımlılıklar ve lock SHA256
[ortam kaydında](evidence/phase20/environment.json). Kaynak ve /tmp cwd'deki
noneditable wheel ayrı package-root assert'iyle çalıştı. İnsan masaüstü,
yeni uzak CI, minimum donanım/temiz offline kurulum kabulü değil.
Sistem Python3.14.7 eksik bağımlılık discovery başarısızlığı ayrı kayıtlı;
başarılı kilitli unittest ile karıştırılmaz. [Kanıt](evidence/PHASE20.md).

## ENV-25 / ENV-25-WHEEL

2026-10-09 UTC / 2026-10-10 Europe/Istanbul; aynı Linux x86_64 host, kilitli
CPython3.13.15/Qt6.11.2, offscreen/software ve izole XDG.
QT_SCALE_FACTOR=2 ayrı başsız denemedir; fiziksel panel veya Orca kabulü değil.
Sistem Python3.14.7 kontrol orchestrator’ıdır; kilitli uygulama runtime’ı
değildir. [Gerçek ortam](evidence/phase25/walkthrough.json),
[komutlar](evidence/phase25/checks.json), [paket](evidence/phase25/package-checks.json).

## ENV-26 / ENV-26-OFFLINE / ENV-26-WHEEL

Kilitli CPython3.13.15/Qt6.11.2, aynı Linux x86_64/Btrfs geliştirici host,
sentetik fixture ve izole XDG. Offline deneme ayrı Linux user+net namespace: lo
dışında arayüz/route yok; native IPv4/IPv6 retleri ve spawn kalıtımı
[gerçek JSON](evidence/phase26/offline.json) içinde. Host bağlantısı kapatılmaz;
fiziksel masaüstü/minimum donanım/temiz makine offline kurulum kabulü değildir.
[PHASE26](evidence/PHASE26.md).

## ENV-UI-DATA-CONTINUATION

2026-10-09 UTC / 2026-10-10 Europe/Istanbul. Aynı Linux geliştirme hostu;
kilitli CPython3.13.15/PySide6/Qt6.11.2, offscreen/software ve izole XDG.
Sistem Python3.14.7 ayrı kontrol ortamıdır. Sentetik CSV ve paketlenmiş CC0
örnekler; kaynak ve noneditable wheel'de geniş/dar %200 QML render.
[OS/CPU/RAM/kilit hash kaydı](evidence/ui-data-inspection-continuation/environment.json),
[yüklenen kaynak paketi](evidence/ui-data-inspection-continuation/source-final/walkthrough.json),
[yüklenen wheel](evidence/ui-data-inspection-continuation/wheel-final/walkthrough.json).
Fiziksel masaüstü, insan/AT veya temiz makine dağıtım kabulü değildir.

## ENV-30-CONTINUATION

2026-10-11 UTC/Europe-Istanbul. Kilitli CPython3.13.15/PySide6 6.11.2,
Linux7.2.9-2-cachyos x86_64, Btrfs,16 logical CPU/32GiB geliştirici host.
Qt offscreen/software ve geçici XDG; kaynak pytest ve noneditable wheel
özel geçici kurulum/cwd üzerinden sınandı. [Paket sürümleri/kilit hash ve
ortam](evidence/phase30/continuation/environment.json),
[kurulu paket bütünlüğü](evidence/phase30/continuation/wheel-integrity.json),
[kabul sınırları](evidence/PHASE30.md#e30-continuation).
Sistem Python3.14.7 bağımlılıkları eksik ayrı kontroldür; minimum donanım,
fiziksel masaüstü, insan/AT, remote CI ve temiz offline kurulum yapılmadı.


## ENV-30-CONTINUATION

2026-10-11. CPython3.13.15/PySide6/Qt6.11.2, Linux7.2.9-2/glibc2.44,
Ryzen7 8845HS/32GiB, Btrfs; offscreen/software ve izole geçici XDG.
Sistem Python3.14.7 bağımlılık eksikliği ayrı başarısız kontrol ortamıdır.
[Gerçek paket/CPU/RAM/FS/kilit hash kaydı](evidence/phase30/continuation/environment.json),
[kaynak ve kurulu wheel teknik doğrulama](evidence/PHASE30.md#e30-continuation).
Fiziksel masaüstü/insan/AT/minimum donanım/dağıtım kabulü değildir.


## ENV-31 / ENV-31-CORE

2026-10-11; CPython3.13.15/Qt6.11.2, Ryzen7 8845HS/32GiB, Linux7.2.9-2,
Btrfs ve izole XDG/Secret Service D-Bus. PostgreSQL18.6, MySQL8.4.11,
MariaDB13.0.2, HTTPS TLS test server, yerel DuckDB1.5.6 ve SeaweedFS4.48
gerçek ayrı sentetik ortamlar. [Binary/driver/hash/donanım](evidence/phase31/environment.json).
Core ortamı connector paketleri olmadan ağsız namespace'te kurulu wheel smoke
geçti; [assembly/eksik client listesi](evidence/phase31/core-environment.json).
Temiz offline cache kurulumu başarısızlığı ayrı; minimum donanım, fiziksel
masaüstü, insan/AT veya canlı sağlayıcı/uzak CI kabulü değildir.


## ENV-33

2026-10-11: locked CPython3.13.15 /Qt6.11.2/sklearn1.9.1/SciPy1.18.0/Polars2.0.0; Linux x86_64, izole XDG/offscreen/software. [Gerçek ortam JSON](evidence/phase33/environment.json), [kontroller](evidence/PHASE33.md). Physical desktop/AT/min hardware/clean offline install/remote CI/R survey binary bu fazda koşulmadı.


ENV-34,2026-10-11: kilitli CPython3.13.15, Qt6.11.2, xarray2026.9.0/h5netcdf1.8.1/Zarr3.4.1/Pint0.26.1/h5py3.16.0/Polars2.0.0. Gerçek sentetik NetCDF/HDF5/Zarr dosyaları; GUI offscreen/software. Zarr asyncio sandbox içinde takıldı; izinli dış ortam denemesi ayrı doğrulanır. Fiziksel/AT/minimum hardware/offline clean install/remote CI kabulü değildir.

Faz35 kilitli CPython3.13.15 `.venv`, mevcut NumPy/SciPy/Matplotlib/PySide6 bağımlılıklarıyla doğrulanır; pyproject/uv.lock değişmedi. Qt offscreen/software kaynak ve noneditable wheel denemeleri, sistem Poppler PDF metin/raster kontrolü ayrı kanıttır. [ENV-35 ve komut kaydı](evidence/PHASE35.md). Fiziksel masaüstü, insan/AT, minimum donanım, temiz çevrimdışı kurulum ve remote CI bu kaydın yerine geçmez.

Faz56 ENV-56:locked CPython3.13.15/torch2.13.0+cpu; isolated developer GUI RAM4GiB, CPU/offscreen/software. CPU wheel CUDA backend içermez; fiziksel GPU denetlenmedi, GPU runtime unvalidated; no GPU/minHW claim. [Gerçek ortam](evidence/phase56/environment.json).

Faz57 ENV-57:CPython3.13.15/Pillow12.3.0/torch2.13.0+cpu, Qt offscreen/software explicit4GiB GUI; core default2GiB. Gerçek localhost TLS ve offline cache kaynak testidir; wheel ağ testi yapılmadı. [Ortam](evidence/phase57/environment.json).

Faz58 ENV-58 SoundFile0.13.1/libsndfile/SciPy1.18.0, optional Vosk0.3.45 package/no model; CPython3.13.15. Gerçek isolated2GiB developer offscreen; mixed uzun GUI retained heap2GiB kapısı ayrıca açık. [Ortam](evidence/phase58/environment.json).

Faz59 ENV-59 kilitli CPython3.13.15/NumPy/Polars CPU; yeni dependency yok.
Developer Linux offscreen gerçek worker; fiziksel masaüstü/hardware kabulü değildir.
[Ortam ve gerçek kontroller](evidence/PHASE59.md).

Faz60 ENV-60 kilitli CPython3.13.15/native Python/Polars/ZoneInfo; yeni dependency yok.
Linux developer offscreen/software; [ortam](evidence/phase60/environment.json).
Fiziksel masaüstü/minHW/AT/clean offline installer/remote CI değildir.

Faz61 ENV-61 NetworkX3.7 core pinned; CPython3.13.15/Polars/defusedxml.
[Ortam](evidence/phase61/environment.json). Offscreen developer Linux; ayrı tablolarda
repeated-import GUI yalnız explicit4GiB test; default2GiB değişmedi/minHW kabulü değil.

Faz62 bounded local stream/prequential/checkpoint ve özel development hedefleri: [kanıt](evidence/PHASE62.md).129şer seçilmiş source/wheel core,350byte-eşit paket; GUI explicit4GiB fixture ayrı,default2GiB kapısı açık. PU/broker/live tail ve özel hedef fitted-model prediction yok. Faz63 başlamadı.

Faz63 bounded numeric GUI profile Python/SQLite subset/notebook ve explicit fresh process: [kanıt](evidence/PHASE63.md).142şer seçilmiş core,355byte-eşit package; arbitrary code OS sandbox değildir. Managed Jupyter unavailable, yalnız harici notebook opsiyonel; önceki resmî/2GiB longheap açıkları korunur. Faz64 başlamadı.

ENV-66 (2026-10-16): CPython3.13.15 kilitli .venv, Linux7.2.9/glibc2.44,
AMD Ryzen7 8845HS/16 affinity CPU,32141972kB MemTotal; Qt offscreen/software.
373byte-eşit noneditable wheel. Optional Dask2026.8.0/distributed2026.8.0 ve
[gerçek izole paketler](evidence/phase66/optional-environment.json) /tmp altında,
core venv/lock değiştirilmedi. Remote cluster/GPU runtime yok/not validated;
[benchmark, test ve bütçe farkları](evidence/PHASE66.md). Shared development load,
minimum hardware/idle-host performance/physical desktop kanıtı değildir.

ENV-67 (2026-10-16): locked CPython3.13.15 .venv/Linux CPU Qt offscreen/software;
yeni dependency yok. Source/wheel actual GUI drift2GiB, shadow model explicit4GiB;
real API loopback izinli ortamda ephemeral bearer ile. Secret Service provisioning/
fiziksel/insan/AT/minHW/longheap/remoteCI/offlineinstaller ayrı açık. Gerçek donanım,
hash/komut ve test sayıları [E67](evidence/PHASE67.md) içinde.


ENV-68 /2026-10-16: kilitli CPython3.13.15 .venv, Linux CPU/offscreen/software; NumPy2.5.3, SciPy1.18.0, Pint0.26.1 mevcut kilit. Yeni dependency veya ağ indirmesi yok. [Gerçek ölçüm/kapsam](evidence/PHASE68.md); fiziksel/human/AT/minHW/remoteCI/offlineinstaller ayrı.


ENV-69 /2026-10-16: kilitli CPython3.13.15 .venv, Linux CPU Qt6.11.2 offscreen/software. Mevcut NumPy/SciPy/sklearn, yeni dependency/model/network download yok. [Gerçek kapsam/ölçüm](evidence/PHASE69.md). GDB native notify crash teşhisi izinli ptrace ile; fiziksel/minHW/human/AT/remoteCI/offlineinstaller ayrı.


ENV-70 /2026-10-16: locked CPython3.13.15 .venv, Linux CPU Qt6.11.2 offscreen/software; existing PyArrow/Qt/DejaVuSans, no new dependency/download. Basic GUI2GiB, model+chart GUI explicit4GiB; [real commands/measurements](evidence/PHASE70.md). Physical/human/AT/minHW/offlineinstaller/remoteCI separate.


ENV-71 /2026-10-16: locked CPython3.13.15 .venv/Linux CPU Qt offscreen/software, yeni dependency/download yok. Metadata/sample GUI2GiB; full-copy native validation explicit4GiB; önceki default2GiB full iptal ayrı başarısızlık. [Gerçek kapsam/ölçüm](evidence/PHASE71.md). Fiziksel/human/AT/minHW/remoteCI/offlineinstaller ayrı.


## ENV-74 — 2026-10-16

CachyOS rolling, Linux7.2.9-2-cachyos x86_64; host glibc2.44, AMD Ryzen7 8845HS,
yaklaşık32GB RAM. Kilitli `.venv` CPython3.13.15; Flatpak1.18.4 KDE Platform6.11
sandbox CPython3.13.15/glibc2.42. Host Python sonucu değildir.
[E74 gerçek test matrisi](evidence/PHASE74.md#e74-platform).
Pardus/Debian/Arch ayrı işletim sistemi testleri yapılmadı; GPU hesap doğrulanmadı.
