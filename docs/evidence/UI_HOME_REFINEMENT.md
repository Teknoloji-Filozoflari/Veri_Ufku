# Başlangıç ve ortak klasör seçici düzenlemesi

2026-10-08, ENV-UI-HOME-02; kullanıcının altı açık arayüz isteği. Faz durumları, yetenek olgunluğu ve kapsam değişmedi; yeni faz başlatılmadı. Linux CPython3.13/PySide6, offscreen/software; geliştirici kontrolü, insan kullanıcı testi değildir.

| Kabul | Yol | Gerçek kanıt |
|---|---|---|
| UIH-01 Başlangıç üst yardım düğmesi kaldırıldı; proje yardım düğmesi kaldırıldı. F1 ve diğer ekranların yardım erişimi korunur | Main.qml, ProjectPanel.qml | tests/test_gui.py, tests/test_home_folders_gui.py; home-1366.png |
| UIH-02 Alt Kapat düğmesi üstte gelişmişin yanında erişilebilir X simgesine taşındı; aynı window.close/kayıt/iş temizliği akışı | Main.qml, UiSymbol.qml | tests/test_gui.py kapanış ve klavye odağı; tests/test_project_gui.py kirli proje; tests/test_home_folders_gui.py konum |
| UIH-03 Son projeler isimli kompakt düğmelerle yan yana, dar alanda sarılır | ProjectPanel.qml | tests/test_home_folders_gui.py iki gerçek kayıt x/y yerleşimi, kayıt/aç; home-720.png ve home-1366.png |
| UIH-04 Dosya sistemi kısayolu/başlığı kaldırıldı, geri/üst klasör simgeleri, açık yeni klasör oluşturma, ortak oval seçimler ve tek FolderPicker | FolderPicker.qml, UiCheckBox.qml, GuidePanel.qml, ui/folders.py, ui/projects.py; tüm QML checkbox kullanımları | Gerçek GUI klasör oluşturma/gezinti/hidden/search, mevcut isim üzerine yazmama, ../ reddi; walkthrough.json gerçek örnek proje tek seçiciyle açıldı; folder-720.png |
| UIH-05 Proje ile yol haritası arasındaki rehber/örnek/dosya aç/kapsam satırları Başlangıçtan kaldırıldı; örnek projeler Öğren ekranında | Main.qml | home-720.png, home-1366.png; gerçek örnek seçici→import→dataset walkthrough |
| UIH-06 Başlık Veri bilimi yol haritası | Main.qml | tests/test_home_folders_gui.py gerçek text; iki boyutta görüntü |

Bütün yollar `src/veri_ufku/ui/` altındadır. Oval kontrol32×22, klavye/check-state/erişilebilir CheckBox semantiği korunur. Yeni klasör yalnız açık kullanıcı tıklamasıyla tek mevcut üst dizinde, arka plan thread ile `mkdir` oluşturur; mevcut dosya/dizine yazılmaz, anahtar veya veri içeriği değiştirilmez. Klasör seçicinin bütün kullanımları Proje aç/yeni/farklı kaydet konumu ve Öğren örnek projelerinde ortak bileşendir; eski FolderDialog kalmadı. Dosya seçen FileDialog ayrı dosya seçimidir.

[469 pytest,136.08s](ui-home-refinement/pytest.txt). [Gerçek Qt walkthrough](ui-home-refinement/walkthrough.json), [ham çıktı](ui-home-refinement/walkthrough.txt), [1366px](ui-home-refinement/home-1366.png), [720px](ui-home-refinement/home-720.png), [klasör seçici](ui-home-refinement/folder-720.png). Yeni klasör anlamlı kabulü mevcut GUI testi genişletilerek sınandı; ayrı görünüm kopyalayan test eklenmedi. Görseller yerel olarak incelendi. Kontrol komutları, ortam ve exit değerleri aynı alt dizinde kayıtlıdır; çalıştırılmamış fiziksel masaüstü veya yeni CI başarı iddiası yok.

Son [9 kontrol komutu](ui-home-refinement/checks.json) exit0: kilitli dev sync, docs/artifacts/learning, Ruff check/format,9 locked unittest ve kurulu giriş noktası smoke. [3 odaklı GUI testi](ui-home-refinement/targeted.txt) son Öğren yerleşiminden sonra6.19s içinde geçti. [Ortam](ui-home-refinement/environment.json). Sistem Python3.14 [discovery](ui-home-refinement/system-unittest.txt)37 eksik paket import hatasıyla başarısız; kilitli CPython3.13 discovery9 geçti. Sistem Python denemesi başarı sayılmaz.

Sonraki kullanıcı yol haritası düzenlemesinde Başlangıç görselleri yeni çizelge görünümüyle yenilendi; bu dosyanın önceki test/komut kayıtları tarihsel kontrol olarak korunur. Yeni çizelgenin ayrı kabul kaydı [UI_SCIENCE_ROADMAP](UI_SCIENCE_ROADMAP.md).
