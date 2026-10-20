# ADR075 — core/extras, Flatpak candidate and explicit environment operations

2026-10-16 DEC74-01; yalnız Faz74. Flatpak seçili mevcut yol korunur. Core CPU
Python/PySide6/QML/polars/Arrow/SciPy/sklearn/Matplotlib/skops ve safe parser;
formats/arrays/geospatial/audio/graphs/statistics-advanced ayrı optional extras.
Neural/bayes/connectors/privacy/audio-speech mevcut optional profiller sürer.
`uv.lock`123paket için tüm extra resolution kilididir; core install hepsini kurmaz.
Derlenen EnvironmentLock/v1 Linux/x86_64/CPython3.13.15 core/extra transitive
closure'larını, extra dependency edges dahil (psycopg[binary]), ayrı tutar.

Optional arrays/audio/networkx modülleri startup'ta import edilmez; explicit kullanımda
missing/ABI failure açıklamalı ret, sahte hesap/fallback yok. Version metadata match
runtime compatibility kanıtı değildir. Native backend yükleme, QML plugin, GPU driver
ve model bytes durumları bu ayrımla gösterilir. Artifact recorded backend versions
ile installed versions karşılaştırılır, eski artifact otomatik import edilmez.

Environment paneli kullanıcı refresh/export/import/selected cache/update plan
başlatır. Export yalnız closed metadata, proje verisi/secret/env değişkenleri ve
dış file paths yoktur. Import hash+closed schema doğrular ve farkları gösterir;
requirements/komut çalıştırmaz veya Python değiştirmez. Ayrı worker environment
provision/routing ve yerel extra wheelhouse kurucusu mevcut değildir. Tüm model
stacklerinin tek Python'a sığdığı varsayılmaz; bu kurulumda yalnız uyumlu seçili
extras aynı runtime'ı paylaşır. Her backend kendi artifact/load uyumluluğunu denetler.

Update paneli yerel .flatpak artifact SHA256 ve mevcut commit alır, explicit onayla
integrity+rollback planı üretir. Hash publisher kimliği/signature değildir; expected
hash bağımsız trusted kanaldan gelmelidir. Panel host paket yöneticisini çalıştırmaz,
restart/overwrite/deploy yapmaz. Application commit rollback, project schema
migration rollback değildir: kapalı projenin tam ayrı yedeği gerekir; eski app yeni
şemayı reddedebilir, yedek ayrı klasöre açılır. Sonraki kullanıcı işini ezme yoktur.

## Gerçek paket ve offline sınırı

Flatpak KDE6.11 Platform/SDK ve PySide BaseApp exact OSTree commit/native file
hash'leri korunur. Builder installed wheel RECORD/hash ve lock version kontrolüyle
core veya explicit selected extras stage eder; kaynaklar/notices/lock/smoke pakette.
AppImage yolu eklenmez. `--share=network` yok, documents RW/download RO static
izinleri mevcut yolun sınırıdır; portal file chooser/document access ayrıca gerçek
paketle test edilir. Worker process sandbox içinden aynı Python/QML/native paths
ile açılmalıdır. Optional geospatial/arrays/CPU torch özel pakette gerçek native
hesapla doğrulanır; driver presence GPU training kanıtı değildir.

Tek uygulama Flatpak bundle runtime/driver/OS prerequisites içermez. Runtime önceden
varsa fresh application sandbox, clean OS offline installer kabulü değildir.
Tam offline installer/local extras provisioning capability mevcut değil olarak
görünür. Yerel model klasör seçimi model-specific eski yeteneklerce doğrulanır;
genel cache inspector yalnız flat64file/64MiB byte hash, model deserialize/license
ve model kalitesi garantisi yoktur. Büyük model burada verified sayılmaz.

Resmî kaynaklar: [Flatpak bundle sınırı](https://docs.flatpak.org/en/latest/single-file-bundles.html),
[portal/sandbox](https://docs.flatpak.org/en/latest/basic-concepts.html),
[uv extra sync/lock](https://docs.astral.sh/uv/concepts/projects/sync/).
Bunlar ürün testinin yerine geçmez; [E74](../evidence/PHASE74.md) gerçek sistem/
revision/package kanıtlarını ve test edilmemiş Pardus/Debian/Arch/GPU sınırlarını tutar.

SBOM/dependency scan ve CI locked candidates içindir; scan unavailable/unknown clean
sayılmaz. Scan veritabanı tarihi/scope ve seçili paketler kayıtlıdır. Local candidate
unsigned, dış release yayınlama/auto deploy yoktur. Türkçe/İngilizce install/contribution
rehberleri ve mevcut lisans/model-data notices kaynakları korunur.
