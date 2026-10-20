# Veri_Ufku0.1.0 — ilk teknik önizleme

2026-10-07; Linux/Python3.13/PySide6/QML; olgunluk deneysel. Faz13 zorunlu kabul kapıları [matriste](REQUIREMENTS_MATRIX.md) ayrı kayıtlıdır. Teknik test başarısı bilgisiz kullanıcı kabulüne çevrilmez; bu kullanıcı görevi ölçülmediği sürece Faz13 sürüyor ve ilk sürüm doğrulanmış dağıtım adayı değildir.

Mevcut: yerel proje/değişmez kaynak/veri sürümleri; CSV/TSV/JSON/JSONL/XLSX/Parquet ve sınırlı ODS/SQLite/IPC import; tür/rol, profil ve kalite; seçilip önizlenen temizlik ve dönüşümler; geri al/redo/dallanmış geçmiş; yedi grafik, istatistik özeti, filtre/RowId seçimi, PNG/SVG; beş veri exportu; HTML/PDF yerel rapor; isteğe bağlı altı adımlı rehber ve iki sentetik CC0 örnek; paketle gelen Türkçe yardım ve DejaVu font.

Rapor ekranı seçilen veri sürümünü ve kapsamını gösterir. Tür kaybını okuyup onaylayarak CSV/JSON/JSONL/XLSX, fiziksel türleri korumak için Parquet seçilebilir. CSV güvenli metin/başlık politikası varsayılan açık; gerçek sayıları bozmaz. XLSX metinleri formülsüz hücredir. Export mevcut dosyayı değiştirmez; yeni proje dışı hedef ister. Kayıt sayısı/tür ve yeniden açma kontrolü makbuzda, temizleme geçmişi Projeyi kaydet ile proje kaydında korunur. [Format ve rapor sınırları](adr/016-release-phase13.md).

Paket ilk açılışta font/yardım/örnek/rapor kaynağı indirmez. Bu erken noneditable Linux wheel denemesi mevcut locked runtime üzerinde yapılır; temiz makineye internetsiz kurucu, AppImage/Flatpak, tüm hedef dağıtımlar ve tam dağıtım lisans kapısı henüz doğrulanmış değildir.

Karşılaştırma, istatistiksel testler, özellik hazırlama, model eğitimi/tahmin, otomatik model seçimi ve profesyonel analiz sonraki fazlardır; mevcut gibi sunulmaz. Gerçek bilgisiz kullanıcı testi, fiziksel masaüstü kabulü ve bu değişikliklerin uzak CI başarısı ayrıca açık kalır. Geliştirici GUI walkthrough'u kullanıcı testi değildir.

Kullanım: Başlangıç → örnek projesi (yeni üst klasör), profil → kalite → istersen seçtiğin temizlik → grafik → Rapor. Sonraki / bu adımı atla ve rehberi kapat her zaman mümkündür. Kendi dosyanda önce Yeni proje → dosya seç/önizle/import. Rapor amacını yazıp HTML veya PDF için yeni dosya seç. Temizlik/grafik/çıktı makbuzunu korumak için projeyi kaydet.

2026-10-08 Europe/Istanbul teknik tarama: ortak düz metin etiketleri, açık/koyu ana düğme yazısı, önceki import hatasından sonra örnek açma ve güncel şema kullanan erken CSV wheel kontrolü düzeltildi. Ürün senaryolarının CC0 magaza.csv/subeler.csv kabul dosyaları paketlendi; mağaza belgesinin hatalı580/58 referansı480/48 olarak düzeltildi (medyan45). [Denetim kanıtı](evidence/AUDIT_00_13.md). Kullanıcı talimatıyla gerçek kullanıcı testleri bu taramadan sonra yapılacaktır; bu teknik kontrol kullanıcı kabulüne çevrilmez.
