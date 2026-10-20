# Faz74 — CPU core, seçili extras ve gerçek Flatpak dağıtımı

2026-10-16 DEC74-01, ENV-74. Yalnız açık Faz74 talimatı. Teknik teslim ile resmî
kabul ayrıdır: faz **sürüyor / deneysel / isteğe bağlı**. Önceki insan/AT/minimum
donanım/longheap/offlineinstaller/remoteCI ve Faz72 live keyring açıkları korunur.
[Önceki durum](phase74/prior-project_state.txt), [ADR075](../adr/075-professional-distribution-phase74.md).

## E74 validation

<a id="e74-validation"></a>
Core28 Python distribution; all-extra lock123 package, seçili professional profile60
Python distribution. SBOM uygulama bileşeni dahil29/61. `uv.lock` SHA256
`f9446a2efcd2277e370a7b79a98cf9309e8bb804f4911f64c1b3999b9167bdc1`.
formats/arrays/geospatial/audio/graphs/statistics-advanced optional ayrıldı;
mevcut neural/bayes/connectors/privacy/audio-speech korundu. Lazy optional imports
core startup'ını korur; eksik veya ABI-hatalı backend açıklamalı unavailable.

Rapor → Paket / bağımlılık / worker ortamı durumu; environment.inspect/profile/
update-plan tek Capability registry. Explicit process/admission/ComputeBudget/supervisor,
Qt nesnesi/ACTIVE worker'a gitmez. Metadata-only approved export/import; import
kurulum/requirements/shell/kod çalıştırmaz. Artifact backend karşılaştırması yalnız
kaydedilmiş version metadata kapsamındadır; bulunmayan geçmiş provenance üretilmez.
QML/plugin dosyaları, native distribution ve driver varlığı execution kanıtı değildir.
Cache inspector yalnız explicit flat64file/64MiB bytes/hash; model deserialize etmez.

Hash update planner yalnız integrity denetler, Flatpak dosya biçimi/publisher imzası
veya authenticated release doğrulaması değildir. GUI update uygulamaz/restart etmez;
host Flatpak açık kullanıcı eylemidir. Önceki app commit ve kapalı projenin ayrı tam
yedeği gerekir. App rollback şema migration'ını geri almaz; eski app yeni şemayı
reddedebilir. Yedek ayrı klasöre açılır, son kullanıcı işi ezilmez.

Ayrı worker environment provisioning/routing, genel local extra/wheelhouse ve model
weight kurucusu **mevcut değil**. Uyumsuz bütün modeller tek Python'a sığmış sayılmaz.
Model-specific yerel model yolları eski adaptör kapsamındadır; genel cache incelemesi
model kullanılabilirliğini kanıtlamaz. Tam temiz OS offline installer **mevcut değil**;
`.flatpak` app bundle runtime/driver/OS prerequisites içermez.

Kaynak testleri [source-focused.log](phase74/source-focused.log),
[JUnit](phase74/source-focused.xml); çalıştırılan subset ve gerçek sayı logdadır,
tam depo testi değildir. İlk9native PASS [log](phase74/native-initial.log),
GUI1PASS [ilk log](phase74/gui-initial.log). Son source/wheel/static kapıları aşağıdaki
nihai kabul kaydında ayrıca kimliklendirilir; koşulmamış kontrol başarı değildir.

Gerçek approved refresh/export/import/cache/update-plan/help/Escape/cancel UI:
[source ölçüm](phase74/source-gui/measurement.json),
[1000px](phase74/source-gui/gui-1000.png), [1366px](phase74/source-gui/gui-1366.png).
Bu offscreen/software geliştirici walkthrough'udur; fiziksel/insan/AT testi değildir.
Mevcut proje commit'i değişmedi, default2GiB CPU budget. Eski2GiB longheap sorunlarının
tümü kapandı iddiası yoktur. Öğren content90/414article;416static capabilities,
10interactive/406article-linked. Yeni environment-distribution çevrimdışı yardım.

## E74 platform

<a id="e74-platform"></a>

| Sistem | Gerçek kapsam | Durum |
|---|---|---|
| CachyOS rolling, Linux7.2.9-2-cachyos x86_64, host glibc2.44 | CPython3.13.15 kaynak/wheel; Flatpak1.18.4 | Test edildi; aşağıdaki bounded paket proofları |
| KDE Platform6.11, CPython3.13.15/glibc2.42 sandbox | core ve seçili arrays/geospatial/CPU torch; network unshared | Gerçek Platform runtime smoke PASS |
| Pardus | sürüm/ortam yok | Test edilmedi |
| Debian | sürüm/ortam yok | Test edilmedi |
| Arch Linux ayrı dağıtım | CachyOS'tan çıkarılmaz | Test edilmedi |
| GPU/CUDA/ROCm/driver uyumu | presence yalnız metadata | Compute test edilmedi |
| Temiz OS offline installer / native insan FileChooser | runtime önceden mevcut, chooser insan etkileşimi yok | Test edilmedi |

CPU Ryzen7 8845HS / yaklaşık32GB RAM. Bu donanımda fixture smoke performans benchmark
veya minimum donanım kabulü değildir. Seçili yol Flatpak; AppImage uygulanmadı.
Exact runtime commit `fe192771c0992ad873e6a9ccc6e4f087c76314ce5ced165650cc7ea045a6bbaa`,
SDK `305b8ec8d506448558798256bd9afcfd856c7e62357a42e320a6678a08f81465`,
BaseApp `a6cddcbcf58032e3f22c66a98779cc07685d376e52718e5aee307ad9aeb1bb8e`.
Native copied file hashleri builder tarafından ayrıca doğrulandı.

İlk core269MiB ve professional460MiB unsigned local candidates. Build komutları
kaydedildi: [core](phase74/package/core-build.json),
[professional](phase74/package/professional-build.json). Son notices/SBOM buildleri
ayrı tutulur. Builder mevcut çıktıyı ezmez, exact installed distribution RECORD/hash
ve lock version denetler. Uygulama dış release yayımlanmadı.

[Core Platform proof](phase74/package/core-platform.json),
[professional Platform proof](phase74/package/professional-platform.json).
İlk SDK build testi ayrıca saklanır; Platform runtime testiyle karıştırılmaz.
Gerçek `.flatpak` core bundle yeni `/tmp` FLATPAK_USER_DIR alanına `--bundle --no-deps`
ile kuruldu; pinned runtime deployment mevcut kullanıcı alanından yalnız yeniden
kullanıldı. [Installed core smoke](phase74/package/core-installed.json) app `/app/`
altından açıldığını, sys.path'in host .venv/kaynak içermediğini, full QML startup ve
GUI/spawn import worker → Parquet4row → mean2.5 → sklearnCPU predict8 → save/reopen
akışını doğrular. Backendlerin yokluğu core startup'ı bozmadı. Ağ paylaşımı kapalı.
Bu fresh uygulama kurulumu, temiz OS veya komple offline kurulum paketi değildir.

Professional gerçek native hesap: pyproj4326→3857 one-degree111319.49m referansı,
Shapely area6, pyogrio GeoJSON1row, rasterio MemoryFile GeoTIFF sum10; xarray/h5netcdf
3D fixture slice ve Pint0°C→273.15K; CPU torch2.13.0+cpu MLP30SGD step loss düşüşü.
Model ağırlığı indirilmedi, GPU çalıştırılmadı. Diğer bütün extras/native/backendler
bu paket testinden otomatik verified sayılmaz.

Eski proje: small empty schema4 fixture → current7; eski manifest bytes korunur.
Karmaşık eski model backend migration veya downgrade güvenliği garantisi değildir.

### Portal ve sandbox yolu

İlk `flatpak build` yolunda gerçek Documents grant oluşturulmasına rağmen mount
bulunamadı: [başarısız kayıt](phase74/portal-build-failure.json). Bunun üzerine
bundle gerçek ayrı kurulumdan `flatpak run` ile çalıştırıldı.
[Portal komutu](phase74/package/portal-command.json),
[GUI/worker proof](phase74/package/portal-package.json) PASS: transient Documents
read grant, `--nofilesystem=home/xdg-documents/xdg-download`, `--unshare=network`;
origin klasörü doğrudan açılmadı. Portal dosyasının hash'i aynı, GUI→worker2row import
başarılı, kaynak bytes değişmedi. İnsan FileChooser açıp seçim yapma testi değildir.
Normal manifestte eski DocumentsRW/DownloadsRO statik izinleri korunur; portal
proof'u bunları kaldırarak daha dar erişimi sınar. Python plugin process güvenli
OS sandbox iddiası buradan türetilmez.

## E74 supply chain

<a id="e74-supply-chain"></a>
[Core packaged SBOM](phase74/core-package-sbom.cdx.json),
[professional SBOM](phase74/professional-sbom.cdx.json): CycloneDX1.6 selected Python
inventory, app GPL-3.0-or-later, lisans metadata eksikse review marker. Paket dosya
inventory hash'i property'dir; distribution wheel hash'i diye etiketlenmez.
OS/native/runtime/GPU/model-data tam SBOM değildir; exact runtime/native hashleri
ayrı kayıttadır. Türkçe/İngilizce install/contribution/API ve önceki exact lisans/
model-data notices korunur; model ağırlığı bundle'a eklenmedi.

2026-10-16 explicit HTTPS OSV public name/version scan:
[core](phase74/dependency-scan-authorized.json),
[professional](phase74/professional-dependency-scan.json)
`no-matches-in-scanned-scope`. Yalnız seçili Python scope ve sorgu anındaki advisory
veritabanı; bütün optional/native/OS güvenlik sertifikası değildir.
[İlk sandbox ağ hatası](phase74/dependency-scan.json) unavailable olarak korunur,
clean sayılmadı. Pagination/incomplete veya ağ hatası non-success çıkar.

`.github/workflows/release-candidate.yml`: manual dispatch, read-only contents,
pinned checkout/upload action SHA, credential persistence yok, locked core test,
SBOM/scan/wheel artifact. Dış release/package push/deploy token yok. Resmî action
version tag SHA'ları official remote refs ile doğrulandı; CI **uzakta çalıştırılmadı**.
Yerel kontroller remote Ubuntu başarısı değildir. Local candidates unsigned;
authenticated signing/release dağıtımı ayrı ve açık gate olarak kalır.

### Ortam farkı — Zarr fixture

İlk geniş sandbox koşusu55kontrolden sonra Zarr fixture oluştururken bekledi;
[source-tests.log](phase74/source-tests.log) tamamlanmış suite değildir.
[Ayrı75s bounded diagnostic](phase74/arrays-diagnostic.log) xarray.to_zarr →
Zarr synchronous/async loop wait stack'ini kaydeder; application adapter'a gelmeden
fixture oluşturma aşamasındadır. Aynı kilitli Python ve testler sandbox dışında
[10/10source PASS](phase74/arrays-authorized.log); bu fark salt optional import
regresyonu olarak kesin teşhis edilmez, ortam ilişkisi açıktır. Restricted sandbox
koşusu başarılı sayılmaz; ilk uzun süreç sonlandırıldı.

### Disk bütçesi ve yeniden kontrol

İki candidate'ın eşzamanlı üretimi `/tmp` boşluğunu1GiB rezervin altına indirdi.
[source disk quota failure](phase74/source-disk-quota-failure.log) / [JUnit](phase74/source-disk-quota-failure.xml)
50fail/97pass: snapshot/import/save fail-safe retleri; optional importer hatası diye
sunulmaz. İlk başarısız build'in yalnız üretilmiş geçici staging alanı temizlendi;
kaynak veya kullanıcı projesi silinmedi. Daha sonra yeterli alanla source subset
tekrarlandı; ilk başarısız suite silinmedi. Rezerv/ComputeBudget limiti gevşetilmedi.
Belge kontrolü eksik henüz yazılmamış JUnit linkine karşı ilk iki kez ret verdi;
kanıt oluşmadan başarı yazılmadı. Son belge kapısı ayrıca kayıtlıdır.

## Nihai doğrulama kaydı

[Kimlikli kabul/kapsam kaydı](phase74/acceptance.json).
[147source](phase74/source-focused.xml) PASS76.31s;
[100wheel](phase74/wheel-tests.xml) PASS80.29s ve ayrı
[47wheel audio/graph](phase74/wheel-audio-graphs.xml) PASS3.16s.
[10source array](phase74/arrays-authorized.xml) PASS2.47s ve
[10wheel array](phase74/wheel-arrays-authorized.xml) PASS2.18s yalnız sandbox dışında.
Böylece157source/157wheel disjoint focused test; tam depo suite değil.
Ayrı [source GUI1](phase74/source-gui/gui.xml) ve
[wheel GUI1](phase74/wheel-gui/gui.xml) PASS, default2GiB CPU.
[431byte-eşit dosya](phase74/wheel-parity.json); wheel import `/tmp` noneditable,
yeni source importlarına karışmaz. [Wheel render/ölçüm](phase74/wheel-gui/measurement.json).
[Learning](phase74/learning.log), [usability](phase74/usability.log),
[artifact](phase74/artifacts.log), [Ruff](phase74/ruff.log), [format](phase74/format.log),
[locked123](phase74/lock-check.log) ve [docs](phase74/docs-final.log) kapıları.
Son14document unittest sonucu ayrı [log](phase74/document-tests.log) içinde;
ilk eksik JUnit-link retleri tarihsel kanıt olarak korunur.

Son candidate core: [build ve hash](phase74/package/final-core-build.json),
[komutlar](phase74/package/final-core-commands.json),
[actual bundle install log](phase74/final-core-install.log),
[no-network installed smoke](phase74/package/final-core-installed.json).
Host app kurulumu değişmedi; yalnız `/tmp` izole kullanıcı installation alanı.
Üretim/signed release değildir. Runtime/core ve professional SBOM paket içindedir;
TR/EN install/API/contribution notices ve exact lock/helper kaynakları taşınır.

Son profesyonel `.flatpak` bundle da aynı izole installation'da gerçek `flatpak install`
ile kuruldu; [install komutu/logu](phase74/final-professional-install.log) ve
[installed Platform no-network GUI/worker/native smoke](phase74/package/final-professional-installed.json)
PASS. Staging-only test ile sınırlı değildir.
[Son build/hash](phase74/package/final-professional-build.json),
[komutlar](phase74/package/final-professional-commands.json),
[son readonly Platform testi](phase74/package/final-professional-platform.json).
Her iki paket de [431byte source parity](phase74/flatpak-source-parity.json) doğrular.
[Gerçek artifact integrity-only update planı](phase74/candidate-update-plan.json)
kendi unsigned local candidate hash'ini kontrol eder; bağımsız publisher signature
kanıtı veya uygulanan update/rollback değildir.

| Son local candidate | SHA256 |
|---|---|
| core, /tmp/veri-ufku-f74-final-core/Veri_Ufku-0.1.0-candidate-x86_64.flatpak | 77388ea671ffc5dfe042a3004de5fad1109188ee67fd5c18908db71a0c85994a |
| geospatial/arrays/neural, /tmp/veri-ufku-f74-final-professional/Veri_Ufku-0.1.0-candidate-x86_64.flatpak | 1431fa1d675250562aa63e4388090310709bf85cdeeb6778124b1e815028672a |

Son14document contracts PASS16.566s. Disk rezervi1GiB korunur; staging cleanup sonrası
paket kurulumu ve son smoke için yeterli boşluk mevcuttu. Dış release/yayınlama,
stage/commit/push ve Faz75 başlatma yoktur. Üretilmiş büyük candidate dosyaları /tmp
altındadır; yeniden üretme için repo builder/lock/native pins ve hash kanıtı tutulur.
