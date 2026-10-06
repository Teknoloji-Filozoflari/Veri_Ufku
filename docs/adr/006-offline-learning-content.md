# ADR-006 — çevrimdışı içerik, düz metin ve deneme sınırı

2026-10-06, Faz03 uygulama kararı. Python/PySide6/QML korunur. Yeni Markdown veya web bağımlılığı eklenmez. Paket JSON şema1, pozitif katalog/makale sürümü ve paragraph/note blokları kullanılır; QML Text.PlainText ile gösterilir. Böylece kaynak URL ve HTML görünümlü metin ağ/kod yüklemesine dönüşmez. Katalog Qt ve hesap kodundan ayrı; UI yerel makale state'ini yönetir.

Yardım bağları context kayıtları ve capability.help_links ile otomatik kontrol edilir. İçerikten serbest işlev/komut dispatch yoktur. Sadece UI'da gerçekten uygulanmış allowlist eylemi kabul edilir. Yeni faz kendi makale/kritik uyarı/kaynak ve bağını ekleyerek aynı CI kapısından geçer. [Tam sözleşme](../LEARNING_CONTENT.md).

Proje deposu ve analitik araçlar henüz yoktur. Uygulamada dene yalnız mevcut Öğren aramasını bağımsız, geçici örnek öğrenme projesi penceresinde gösterir; kullanıcı oturumu, kaynak ve worker bağı değişmez. Model/temizleme/istatistik makalesi erken fake eylem sunmaz. Gerçek veri örnekleri ilgili veri/proje fazlarında aynı izolasyon sınırını genişletecek.

Okundu/yer imi varsayılan kapalıdır; kullanıcı açarsa makale kimlikleri ayrı QSaveFile kaydına atomik/0600 yazılır. Çökme/commit hatası veya bozuk şema önceki dosyayı ezmez. Eşzamanlı uygulama süreçlerinden işaret birleştirme garanti edilmez; bunlar proje verisi değildir. Açık kapat-ve-temizle tercihi tek yayında geçmiş işaretleri kaldırır.

Türkçe ilk13 makale pakete dahildir. İngilizce kabuk çalışmaya devam eder; yardımın içerik dili açıkça Türkçedir. Çevrimdışı çalışma, temiz makineye çevrimdışı kurulum ve gelecekteki bilimsel uzman incelemesi ayrı kabuller olarak korunur. [Kanıt](../evidence/PHASE03.md).
