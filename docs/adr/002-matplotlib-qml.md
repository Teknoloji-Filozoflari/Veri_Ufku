# ADR-002 — Matplotlib ile Qt Quick arasında çizim sınırı

2026-10-06; kabul edilmiş tasarım; gerçek adaptör Faz 12.

[Matplotlib Qt örneği](https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html) QWidget FigureCanvas/toolbar kullanır; QML item diye gömülmez. [Backend belgeleri](https://matplotlib.org/stable/users/explain/figure/backends.html) Agg ve vektör export yollarını, Qt binding'lerini açıklar. [Qt QQuickImageProvider](https://doc.qt.io/qt-6/qquickimageprovider.html) QImage aktarımı ve cache/thread davranışını belgeler.

Çizim adaptörü ChartSpec + immutable veri artefact'ından ayrı worker/süreçte Agg raster üretir; PNG/SVG kaydetmeyi aynı figure tanımıyla yapar. UI bir QImage kopyasını sürümlü image provider üzerinden yükler. Render id result_version/style_revision/DPI içerir; eski cache yanlış sonuç göstermemelidir. GUI nesnesi worker tarafından değiştirilmez; QPixmap ana thread sınırı korunur.

Yakınlaştırma/pan/reset UI view bounds→yeni render request; nokta seçimi result/RowId map ve coordinate transform ile. Aggregate/örneklenmiş nokta tek kayıt olarak sunulmaz. Event mapping, HiDPI doğruluğu ve SVG/PNG eşdeğerliği Faz 12'nin gerçek QML/paket testleridir; şu an yapılmadı. Faz 00 Agg boş buffer probe yalnız ortam testidir, grafik özelliği değildir.

Alternatif QtAgg+Widgets karışımı ana QML tablo/UX yapısını karmaşıklaştırdığı için seçilmedi. Çizim backend soyutlaması minimal render/export/select sözleşmesi; erken framework veya Qt Graphs lisans/altyapı değişimi yok.
