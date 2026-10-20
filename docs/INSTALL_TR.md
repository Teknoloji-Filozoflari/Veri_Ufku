# Veri_Ufku — core, optional extras ve Linux dağıtımı

Linux/Python3.13.15/PySide6/QML korunur. CPU core kaynak kurulumu:
`uv sync --locked --no-dev`; geliştirme `--group dev`, gereken extra için örneğin
`--extra geospatial --extra arrays`. Bu bir temiz makine offline installer değildir.
Tam geliştirici regresyon ortamı `uv sync --locked --group dev --all-extras` ister;
core kullanımına bütün model stackleri zorunlu değildir.

formats, arrays, geospatial, audio, graphs, statistics-advanced; mevcut bayes,
neural (CPU torch), connectors, privacy ve audio-speech ayrı profillerdir.
Lock123 çözülmüş paketi içerir; core closure28 Python distribution içerir.
Uyumsuz stackler için ayrı worker ortamı gerekir. Otomatik ayrı environment
kurulumu/routing bu sürümde mevcut değildir; metadata import bunu kurmaz.

Rapor → Paket / bağımlılık / worker ortamı durumu; explicit yenileme core/extra
sürümleri, artifact backend farkı, QML/plugin dosyaları, native distribution ve driver
varlığını okur. Varlık/sürüm eşleşmesi çalışma testi değildir. Seçili düz model
klasörü byte/hash incelemesi model deserialize etmez;64dosya/64MiB sınırı vardır.
Export/import yalnız kullanıcı onayıyla kapalı metadata şemasıdır, veri veya secret
gömmez; requirements/komut çalıştırmaz ve ortamı değiştirmez.

Seçili dağıtım Flatpak, AppImage yolu yoktur. Builder:
`python scripts/build_flatpak.py --help`; `--extra geospatial --extra arrays --extra neural`
yalnız seçilmiş, kurulu ve lock/hash ile eşleşen dağıtımları paketler. Qt plugin/native
kitaplıklar ve locked runtime commitleri ayrıca doğrulanır. `.flatpak` runtime,
GPU driver veya işletim sistemi önkoşullarını içermez. Tam offline installer,
genel yerel wheelhouse/extra ve model-weight kurucusu **mevcut değil**; model-specific
yerel klasör desteği kendi adaptör kapsamındadır. Yerel cache hash'i bunu kanıtlamaz.

Güncelleme host Flatpak'ta açık kullanıcı işlemidir; GUI seçili artifact SHA256'sını
bağımsız güvenilen beklenen hash ile karşılaştırır ve plan üretir. Dosya biçimi veya
publisher signature doğrulaması değildir; yerel unsigned candidate authenticated
release değildir. GUI uygulamaz/restart etmez. Uygulama rollback'i için önceki commit,
proje rollback'i için kapalı projenin ayrı tam yedeği gerekir. App sürümünü geri almak
şema migration'ını geri almaz; eski app yeni şemayı reddedebilir. Yedeği yeni ayrı
klasöre açın; son çalışmayı ezmeyin.

[Gerçek paket/sistem matrisi](evidence/PHASE74.md),
[API/eklenti rehberi](PLUGIN_API_EN.md), [lisans/model-data notices](THIRD_PARTY_NOTICES.md).
Pardus, Debian, Arch, GPU, insan file chooser ve temiz OS offline kurulum testleri
başka sistemdeki başarılı smoke'tan çıkarılmaz. Dış release yayımlanmadı.
