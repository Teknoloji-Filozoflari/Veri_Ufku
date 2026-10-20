# Veri_Ufku — sağ üst simgeler ve sabit yazı boyutu

Kullanıcı görsel düzeltmesi, 2026-10-07 UTC / 2026-10-08 Europe/Istanbul. Kapsam mevcut kabuk; yeni faz başlatılmadı. ENV-UI-HEADER: Linux x86_64, CPython3.13.15, Qt6.11.2; offscreen/software ve izole geçici XDG. Gerçek kullanıcı testi yapılmadı.

<a id="e-header"></a>
## UI-HEADER — uygulama ve gerçek Qt kontrolü

Tema/görünüm başlıkları, koyu/açık yazılı seçici ve yazı boyutu alanı kaldırıldı. Üst satırın sağında başlangıç filizi, gelişmiş sürgüleri ve ay/güneş tema düğmesi var. Özgün QML Canvas çizimleri paketlidir; ikon fontu/internet gerekmez. Seçili seviye vurgu kenarlığıyla gösterilir; düğmelerde görünür metin yoktur. Tooltip hover/klavye odağında, erişilebilir adlar ekran okuyucu için korunur.

Theme tipografisi sabit gövde14/yardımcı12/bölüm18/başlık24px. Uygulama içi yazı büyütme API ve kontrolü kaldırıldı; OS DPI bundan bağımsızdır. Tercih şema2 yalnız tema/seviyeyi atomik0600 kaydeder. Geçerli şema1 dosyasındaki100/125/150/200% değer uygulanmaz, tema/seviye korunur; açılış eski dosyayı değiştirmez, açık tercih değişimi şema2 kaydeder. Bozuk dosya ve başarısız atomik kayıt politikası korunur.

Kod: src/veri_ufku/ui/qml/Main.qml, UiIconButton.qml, Theme.qml; ui/preferences.py. QtTest gerçek Space/Tab ve tema/seviye geçişi tests/test_gui.py; çalışan işin binding/job/result korunması ve yeni süreçte tercih yükleme. tests/test_presentation_preferences.py eski şema ve atomik kayıt; tests/test_learning_gui.py dar drawer klavye kontrolü. Eski ölçüm betikleri sabit100% uygulama boyutuna güncellendi; tarihsel kanıtlar yeniden yazılmadı. Home yardımı mevcut örnek/import/rapor ve simge açıklamasına güncellendi; katalog13, home2.

[Gerçek render/mouse/geometri kaydı](ui-header/render.json), [geniş açık](ui-header/1366-light-beginner.png), [dar açık](ui-header/720-light-beginner.png), [dar koyu](ui-header/720-dark-advanced.png). Geniş açık ve dar koyu görüntüler araçla gerçekten incelendi. Başlıktaki simgeler sağda, eski yazı seçicileri yok; dar içerik kaydırılır. Eski200% tercihinin14px gövdeyi değiştirmediği QML expression ile denetlendi. Gerçek fare tıklaması koyudan açığa geçer.

## Kontroller

İlk ilgili regresyon:14 test geçti. `uv --cache-dir /tmp/veri-ufku-uv sync --offline --locked --group dev` exit0;29 resolved/28 checked. Genel regresyon345 pytest geçti (81.64s);9 unittest aynı belge testlerinin tekrar kontrolüdür. Sistem ve locked check_docs, check_artifacts, check_learning (71 makale/49 UI bağı), Ruff check/format (119 dosya), izole XDG kurulu giriş noktası GUI_SMOKE PASS ve git diff --check exit0. Tarih/komut/exit/log sonuçları [komut kaydında](ui-header/checks.json). İlk giriş noktası denemesi izole XDG verilmeden controller oluşturulamayıp exit2 döndü; bu deneme başarı sayılmadı, nedeni bu kayıtta kesinleştirilmedi. Kullanıcı ayarlarına müdahale edilmeden yeni geçici XDG ile aynı giriş noktası exit0 verdi. Bu ortam izolasyonu diğer Qt render/test kontrolleriyle aynıdır. Fiziksel masaüstü/ekran okuyucu/yeni remote CI ve kullanıcı testi bu kayıt değildir.
