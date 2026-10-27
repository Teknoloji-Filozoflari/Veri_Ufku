# Veri_Ufku — sol menü görsel düzeltmesi

2026-10-07 UTC / 2026-10-08 Europe/Istanbul. Kullanıcı isteği: sekiz navigasyon alanına tutarlı simge, sola hizalı başlık ve alttaki planlanan alan metninin kaldırılması. ENV-UI-NAV: Linux x86_64/CPython3.13.15/Qt6.11.2, offscreen/software, izole XDG. Yeni faz başlatılmadı; gerçek kullanıcı testi yapılmadı.

<a id="e-navigation"></a>
## UI-NAVIGATION

Başlangıç ev, Veri tablo, Hazırla sihirli değnek, İncele çizgi grafiği, Karşılaştır karşılıklı oklar, Model bağlı düğümler, Rapor belge, Öğren açık kitap simgesini kullanır. Sekiz özgün çizgi simgesi QML Canvas UiSymbol içinde; sağ üstteki önceki simgeler aynı bileşeni paylaşır. Uzak dosya/ikon fontu/ek bağımlılık yoktur. UiNavigationButton sabit20px simge,12px aralık ve sola hizalı düz metin içerir. Menü184px;44px düğmeler ve seçili bölüm için vurgu rengi/sol işaret vardır. Ortak UiButton diğer alanlarda korunur. Accessible.name, nav0..7 kimlikleri, Tab/ShiftTab/ok/Space/Ctrl+1..8 ve odak kaydırma davranışı devam eder.

“Planlanan alanların durumu içeride açıklanır” etiketi menüden çıkarıldı. Karşılaştır/Model ekranlarındaki gerçek kullanılabilirlik bilgisi ve erişilebilir açıklama korunur.

Kod: src/veri_ufku/ui/qml/Main.qml, UiNavigationButton.qml, UiSymbol.qml, UiIconButton.qml. İlgili10 gerçek GUI regresyonu geçti (tests/test_gui.py ve tests/test_learning_gui.py). [Render/geometri kaydı](ui-navigation/render.json) üç pencere/tema durumunda bütün yazıların aynı x hizasını, sola hizalanmasını, mevcut genişliğe sığmasını ve sekiz düğmenin görünür olmasını QML/Qt ile doğrular. [1366px açık](ui-navigation/1366-light.png), [720px açık](ui-navigation/720-light.png), [720px koyu](ui-navigation/720-dark.png); geniş açık ve dar koyu görüntüler gerçekten incelendi.

Standart locked dev sync, sistem ve locked check_docs, check_artifacts, check_learning, Ruff check/format exit0;345 pytest geçti (81.99s),9 belge unittest tekrar kontrolü geçti; izole kurulu giriş noktası GUI_SMOKE PASS ve git diff --check exit0. [Komut/tarih/exit kayıtları](ui-navigation/checks.json), [pytest kaydı](ui-navigation/pytest.xml). Başsız Qt kanıtı fiziksel masaüstü, ekran okuyucu veya gerçek kullanıcı testi yerine geçmez.
