# ADR-030 — Tek Linux paketleme yolu

2026-10-09 UTC; karar: Flatpak, x86_64, org.kde.Platform/6.11. Docker gerekmez.

[Resmî Qt rehberi](https://docs.flatpak.org/en/latest/qt.html) KDE runtime/SDK ile Wayland ve fallback-X11 düzenini önerir. Mevcut SDK Python3.13.15 sağlıyor; uygulamanın kilitli cp313 scientific/PySide6.11.2 wheel dosyaları /app içine doğrulanmış RECORD/hash ile alınır. Qt plug-in/QML/library yolları kendi bundle'ına sabitlenir; runtime Qt sürümüyle karışmaz. CLI build-init/build/build-finish/build-export/build-bundle yolu [resmî referansa](https://docs.flatpak.org/en/latest/flatpak-command-reference.html) dayanır; bundle.json flatpak-builder manifest'i değildir, kendi build scriptimizin kilitli sözleşmesidir.

[AppImage önerisi](https://docs.appimage.org/reference/best-practices.html) en eski desteklenen hedef üzerinde build gerektirir. Mevcut glibc2.44 hosttan AppImage üretmek eski Debian/Pardus uyumunu kanıtlamaz. Bu yüzden AppImage daha sonra eski glibc build tabanı ve gerçek hedef testleri ile eklenebilir.

[Sandbox izinleri](https://docs.flatpak.org/en/latest/sandbox-permissions.html): ağ izni yok; Belgeler rw, İndirilenler ro, başka dosyalar portal. GPU/display/IPC izinleri açık listelenir. XDG config/cache/data Flatpak özel alanında, state/log data/state altında bulunur. Uygulama Python kaynak tarball'ı yerine gerçek OSTree .flatpak üretilir.

[Tek bundle](https://docs.flatpak.org/en/latest/single-file-bundles.html) runtime içermez; çevrimdışı kurulum için runtime ayrıca sağlanmalı ve temiz kurulum denemesi yapılmalıdır. Yeni release yayımlanmaz. Temiz hedef launch veya gerçek GUI akışı başarısızsa Faz27 engellidir.
