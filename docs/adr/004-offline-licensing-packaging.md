# ADR-004 — Çevrimdışı paket sınırı ve lisans kayıtları

2026-10-06; kabul edilmiş plan, paketleme yolu henüz seçilmedi.

Çevrimdışı çalışma: kurulu çekirdek, yardım, yapay örnek veri, font, rapor şablonları internet olmadan kullanılacak; hesap/telemetry/download yok. Çevrimdışı kurulum: ayrıca Python/Qt/QML/native wheel/font/kurucu/runtime'ın yerel pakette olması ve temiz makinede ağ kapalı denemesi gerekir. Optional modül/model ağırlığını yerel paketten yükleme üçüncü ayrı capability; henüz mevcut değil. Geliştirme resmî kaynak/registry erişimi son kullanıcıda zorunlu internet anlamına gelmez.

Faz 01 bağımlılık kilidi; Faz 06 ilk import/worker Linux paket smoke; Faz 12 grafik/QML/export/process paket smoke; Faz 27 AppImage veya Flatpak için resmî gereksinimlerle tek yol kararı. Faz 00'da sahte paket veya iki paket yolu geliştirilmiyor. Debian/Pardus ve Arch/CachyOS hedef aileleri yalnız gerçek test sürümüyle desteklenmiş sayılır.

[Qt lisans belgesi](https://doc.qt.io/qt-6/licensing.html) ve [LGPL yükümlülükleri](https://www.qt.io/development/open-source-lgpl-obligations): seçilmiş Qt modüllerinin lisansı, dinamik kitaplığı değiştirme/relink hakkı, notices/lisans metinleri, kullanılan LGPL kaynaklarına erişim ve değişikliklerin kaynak yükümlülükleri paketle sağlanmalı; GPL-only modül farkı incelenmeli. Ürün lisansı henüz kullanıcı/yayıncı kararı; permissive bağımlılıkların kullanımı otomatik uygulama lisansı seçimi değildir. Hukuki/dağıtım uygunluğu gerçek paket envanteriyle release kapısıdır.

[Polars](https://github.com/pola-rs/polars/blob/main/LICENSE) MIT, [DuckDB](https://github.com/duckdb/duckdb/blob/main/LICENSE) MIT, [scikit-learn](https://scikit-learn.org/stable/about.html) BSD, [SciPy](https://github.com/scipy/scipy/blob/main/LICENSE.txt) BSD-3, [statsmodels](https://www.statsmodels.org/stable/about.html) BSD, [Matplotlib](https://matplotlib.org/stable/project/license.html) kendi BSD-compatible lisans metni. Seçilen sabit wheel'in BLAS/native/transitif lisansları ve copyright metinleri ayrıca SBOM/THIRD_PARTY_NOTICES'a kaydedilecek. Bu liste dağıtım lisans envanteri tamamlandı iddiası değildir.

Font için yerel Noto Sans aday; exact font sürümü/OFL kaynağı ve redistribution henüz doğrulanmadı. İlk paket uygun font içermezse gizli indirme yok, sistem fallback açık sınır. İkon/marka görselleri kopyalanmaz; Faz 02'de seçilen ikon setinin exact lisansı ve atıf dosyası zorunlu. Faz 00'da dış görsel/font kopyası yok.
