# Başlangıç ve kompakt butonlar

2026-10-08, ENV-UI-HOME-COMPACT / UI-HOME-COMPACT; kullanıcının açık görsel düzeltme talimatı. Yeni faz başlatılmaz; önceki veri/analiz fazlarının durumu değişmez. Linux Python/PySide6/QML korunur.

Başlangıç altındaki genel tanıtım/rehber açıklamaları ve boş altyapı durum yazıları gizlendi. Proje önce gelir, başlık Proje oldu. Kaynak/seed/kurtarma ayrıntıları isteğe bağlı Proje ayrıntıları içinde; hata ve işlem sonuçları görünür. Rehber/örnekler erişilebilir. Dosya/örnek ve amaç düğmeleri büyük tam genişlikli kartlar yerine kompakt Flow yerleşiminde.

Ortak UiButton doğal metin genişliğine göre, en fazla340px,40px asgari yüksekliği koruyarak küçültüldü;14px yatay/8px iç boşluk, metin sarmalama, klavye/odak korunur. Form alanları/veri tabloları düğme gibi daraltılmadı. Dar/geniş kaynak ve kurulu wheel görüntüleri aşağıdaki ölçümlerde.

Yeni proje/Farklı kaydet modalında düzenlenebilir dizin yolu yok. Klasör seç, salt okunur seçilen klasör adı ve açık oluştur/kaydet eylemi var. Yeni_Proje ve ad doluysa sayısal ek; mevcut hedef üzerine yazılmaz. İptal seçim yapmaz ve eski dosyaları değiştirmez. Proje aç aynı temalı FolderPicker kullanır: hızlı konumlar, geri/üst klasör, arama, gizli klasörler, seçim adı; tek tıklama seçim, çift tıklama/Enter alt klasöre geçiş.

Klasör taraması salt okunur ve tek I/O thread'de.100000 öğe/10000 klasör sınırı; hata açık. Son navigasyon isteği önceki bekleyen taramayı eskimiş sayar. Unicode, boşluk ve # içeren yollar QUrl.fromLocalFile/toLocalFile ile korunur. İlk Qt.labs FolderListModel denemesi gerçek # içeren klasör testinde başarısız oldu; üretim bunun yerine sınırlı Python scandir/list ve Qt GUI controller kullanır. Başarısız ilk deneme başarılı kabul sayılmaz.

Son projeler yalnız kayıtlı proje adı gösterir; açmak için iç yol bağı saklanır. Recent cache eski string listeleri okur; yeni kayıtlar path/name nesneleriyle QSaveFile atomik yazılır. Proje manifest/veri şeması değişmedi. Kaydet/aç isimleri yeniler; bozuk cache korunur. Proje yardım makalesi ve paket içerik17 yeni klasör akışını anlatır; F1 bağlamı project.

Gerçek QML oluştur/aç/save/cache/encoded path/search/hidden/up/navigation akışı tests/test_home_folders_gui.py; var olan tests/test_project_gui.py yeni yol alanı kaldırıldığı için iç seçim property'sine uyarlanır. [Proje kontrolleri](ui-home-compact/project-tests.txt), [tam regresyon](ui-home-compact/pytest.txt), [standart kapılar](ui-home-compact/checks.txt). Son standardın komut/exit kayıtları [JSON](ui-home-compact/checks.json).

[Kaynak render/işlev ölçümü](ui-home-compact/headless.json), [kurulu noneditable Linux wheel](ui-home-compact/wheel.json), [ortam/son kaynak eşleşmesi](ui-home-compact/environment.json). Başlangıç720/1366, yeni proje720, klasör picker720/1366 ve son proje ismi screenshot'ları gerçek QQuickWindow.grabWindow'dur; fiziksel masaüstü/insan kabulü değildir. Yeni uzak CI, minimum donanım veya temiz offline kurulum iddiası yok.

Nihai yerel kontroller:420 pytest,9 locked unittest, check_docs/artifacts/learning (içerik17,96 makale), Ruff check/format ve offscreen/software entry smoke geçti. Son seçim bağlamı düzeltmesinden sonra6 proje GUI testi ve source/noneditable wheel ölçümleri tekrar geçti. Kurulu paketin145 üyesi son kaynak byte/hash ile eşleşti. Sistem Python3.14 ayrı ortamında33 modül import hatası ([kayıt](ui-home-compact/system-unittest.txt)); locked CPython3.13 esas alınır.
