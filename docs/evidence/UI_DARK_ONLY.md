# Veri_Ufku — yalnız koyu tema

2026-10-07 UTC / 2026-10-08 Europe/Istanbul. Son kullanıcı talimatı: açık temayı tamamen kaldır, yalnız koyu tema kalsın, tema düğmesini kaldır. ENV-UI-DARK-ONLY: Linux7.2.9 x86_64, CPython3.13.15/Qt6.11.2; offscreen/software, izole XDG ve6 satır sentetik satış örneği. Yeni faz başlatılmadı; insan kullanıcı testi yapılmadı. Önceki [sıcak koyu tema](UI_DARK_THEME.md) bu talimatla tek palete indirildi; önceki ekran/kanıtlar tarihsel korunur.

<a id="e-dark-only"></a>
## UI-DARK-ONLY

Theme.qml açık renk dalları/SystemPalette/styleHints kaldırıldı; turuncu vurgulu koyu renk tokenları sabit. Ana/örnek pencerede OS şeması görünümü değiştirmez. Sağ üst tema düğmesi ve ay/güneş ikon çizimleri kaldırıldı; yalnız filiz ve sürgüler seviye seçer. Seviye geçişi aynı veri/iş/result state üzerinde devam eder; yazı boyutu sabit. Rapor/figür beyaz sayfası çıktı okunabilirliği içindir, uygulama teması seçeneği değildir.

PresentationPreferences şema3 yalnız view saklar; theme getter/setTheme API yoktur. Geçerli şema1/2 light/dark/system ve eski yazı ölçeği okunabilir fakat uygulanmaz; view korunur. Açılış eski dosyayı ezmez, açık seviye değişimi atomik0600 şema3 kaydeder. Bozuk dosyayı koruma ve başarısız kayıt davranışı regresyonda denetlenir. Ölçüm betiklerinin tema seçimi kaldırıldı, güncel çekimler dark etiketlidir. Tarihsel açık tema kanıtları yeniden adlandırılmadı/silinmedi.

Kod: src/veri_ufku/ui/qml/Theme.qml, Main.qml, UiSymbol.qml, ui/preferences.py. tests/test_presentation_preferences.py iki eski şema/üç tema uyumu, schema3 ve atomik hata; tests/test_gui.py tema düğmesinin olmaması, OS beyaz palette rağmen koyu görünüm, yeni süreçte seviye, active job/result korunması ve okunabilir primary/disabled metin; tests/test_learning_gui.py dar drawer/klavye. İlk14 ilgili regresyon geçti.

`scripts/measure_dark_theme.py` gerçek QML/process satış import/grafik/rapor: eski light kaydıyla koyu açılış, tema düğmesi yok, iki seviye düğmesi var, schema3 sadeceview;12 renk çiftinde metin≥4.5/odak ve simge≥3. [Ham render/kontrast kaydı](ui-dark-only/render.json), [başlangıç](ui-dark-only/home-dark.png), [dar pencere](ui-dark-only/home-dark-small.png), [veri](ui-dark-only/data-dark.png), [grafik](ui-dark-only/chart-dark.png), [rapor](ui-dark-only/report-dark.png). Token kontrastı tam ekran okuyucu/erişilebilirlik kabulü değildir.

Son standart kontroller: locked offline dev sync, sistem/locked check_docs, check_artifacts, check_learning (71 makale/49 bağ), Ruff check/format exit0;345 pytest geçti (81.73s),9 belge unittest tekrar kontrolü geçti; izole kurulu giriş noktası GUI_SMOKE PASS, git diff --check exit0. [Komut/tarih/exit kayıtları](ui-dark-only/checks.json), [pytest kanıtı](ui-dark-only/pytest.xml). Güncel geniş başlangıç görüntüsü araçla gerçekten incelendi; sağ üstte yalnız iki seviye simgesi bulunur. Yeni fiziksel masaüstü/insan testi/uzak CI yapılmadı.
