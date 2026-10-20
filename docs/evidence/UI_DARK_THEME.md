# Veri_Ufku — sıcak vurgulu koyu tema

2026-10-07 UTC / 2026-10-08 Europe/Istanbul. Kullanıcı mevcut koyu temanın tek renkten çıkarılıp turuncu vurguyla yeniden düzenlenmesini istedi. ENV-UI-DARK: Linux7.2.9 x86_64, CPython3.13.15/Qt6.11.2, offscreen/software; izole geçici XDG ve sentetik6 kayıt satış projesi. Yeni faz/analitik yöntem yok; gerçek insan kullanıcı testi yapılmadı.

<a id="e-dark-theme"></a>
## UI-DARK-THEME

Theme ortak tokenları antrasit arka plan, ayrı kabuk/kart/düğme/alan katmanları, kayısı turuncusu ana eylem ve sıcak seçim yüzeyiyle yenilendi. Menü simgelerinde ölçülü mavi/turkuaz/lavanta/altın/yeşil; seçili simge/metin turuncu. UiButton hover/pressed/disabled, UiCombo alanı, UiIconButton seçimi ve UiNavigationButton ortak token kullanır. Veri sekmelerindeki çok açık Basic arka planı UiTabButton ile koyu yüzey/turuncu alt çizgiye geçti. Ana/örnek pencere paletleri aynı alan renklerini kullanır. Koyu köşeler8px; sabit yazı/klavye/Accessible.name/konum korunur. Açık paletin ana renkleri korunur; yeni sekme bileşeni açık renkleri de kullanır. Grafik/rapor hesapları ve okunabilir beyaz çıktı figürü aynı kaldı; UI rengi veri anlamına etki etmez.

Kod: src/veri_ufku/ui/qml/Theme.qml, Main.qml, UiButton.qml, UiCombo.qml, UiIconButton.qml, UiNavigationButton.qml, UiTabButton.qml, ExampleWindow.qml. Mevcut gerçek primary düğme/palet testi güncel koyu metin rengiyle denetlenir.

`scripts/measure_dark_theme.py` gerçek ana pencere/örnek import/process histogram ve rapor ekranı oluşturur; worker geçici projede çalışır, kullanıcı dosyasına yazmaz. [Render/ortam ve12 kontrast çifti](ui-dark/render.json): normal metin/ikincil metin/seçili metin/primary idle-hover-pressed ≥4.5; odak ve kontrol kenarlığı/simgeler ≥3. Token kontrastı bütün çizilmiş ekranın erişilebilirlik kabulü değildir.

[Başlangıç koyu](ui-dark/home-dark.png), [dar koyu](ui-dark/home-dark-small.png), [açık kontrol](ui-dark/home-light.png), [satış verisi](ui-dark/data-dark.png), [gerçek grafik](ui-dark/chart-dark.png), [rapor](ui-dark/report-dark.png). Bu gerçek Qt render görüntüleri görsel kontrol içindir; insan görev testi değildir.

İlk14 ilgili Qt/tercih regresyonu geçti; standart locked kurulum, belge/artefact/yardım/Ruff/pytest/unittest/izole giriş noktası ve diff sonuçları [komut kaydında](ui-dark/checks.json). Fiziksel masaüstü/ekran okuyucu/yeni uzak CI bu denemede yapılmadı.

Bu iki tema geçişli revizyonun genel345 pytest/9 belge tekrar kontrolü/locked kapıları/entry smoke kayıtları exit0 verdi; son küçük okunabilirlik düzeltmesinin14 GUI regresyonu da geçti. Kullanıcı devam eden iş sırasında açık temanın kaldırılmasını istedi; güncel son kapsam [UI_DARK_ONLY](UI_DARK_ONLY.md), önceki bu kayıt tarihsel tutulur.
