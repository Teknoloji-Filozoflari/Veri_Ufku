# Öğren sadeleştirmesi ve merdiven kartları

2026-10-09, ENV-UI-LEARNING-REFINEMENT; Linux CPython3.13/PySide6/QML offscreen/software. Açık kullanıcı UI kapsamı; yeni faz/analitik özellik yoktur. İnsan masaüstü kabulü değildir.

| Kabul | Yol | Gerçek kanıt |
|---|---|---|
| UIL-04a Öğren rehber üst alanı, yardım ve üç istenmeyen düğme kaldırıldı | Main.qml; LearningCenter.qml | test_learning_tree_gui.py görünürlük/yokluk |
| UIL-04b Numaralı renkli merdiven, iki düzey açılma animasyonu ve dar ekran | LearningTrail.qml | Gerçek QML Space/odak/açılma; hierarchy-1366.png; data-reader-720.png |
| UIL-04c Veri.md tanım/tipler/yapı/kullanım; eski Veri alt konuları listede yok | taxonomy.py; content/tr.json | Tam/çakışmasız görünür ve bağlamsal konu üyelik testi; Veri alt konuları kaynaklı |
| UIL-04d Başlangıçta Proje yol haritasından sonra | Main.qml | Gerçek mapToScene konum testi; home-order-1366.png |

Yollar `src/veri_ufku/ui/qml`, `src/veri_ufku/learning` ve `tests` altındadır.107 makaleden85 konu ağacında;22 bağlamsal uygulama/kaynak yardımı korunur. Kullanıcı kaynak dosyası/kopyası/hash değiştirilmedi. Veri tanımı ve sekiz ayrıntı konusu dosyadan düzenlenmiştir; anlatım açıklamaları ayrı okuma penceresinde, başlıklar ağaçta sunulur. Yeni konuların örnekleri kendi kavramlarına uygundur. F1 bağlamsal yardım, arama/kategori ve mevcut işler korunur. İstenen düğmeler geri eklenmedi.

[Görünüm](ui-learning-refinement/hierarchy-1366.png), [okuma penceresi](ui-learning-refinement/data-reader-1366.png), [dar ekran](ui-learning-refinement/data-reader-720.png), [başlangıç sırası](ui-learning-refinement/home-order-1366.png), [gerçek walkthrough](ui-learning-refinement/walkthrough.json). Kontrol/exit/tarih `checks.json`, ortam `environment.json`, testler `targeted.txt` ve `pytest.txt` içinde kaydedilir; yürütülmeyen kontrol başarı sayılmaz.

Son doğrulama: [473 pytest testi,137.95s](ui-learning-refinement/pytest.txt); [30 odaklı öğrenme/kabuk/başlangıç/klasör GUI kontrolü,21.95s](ui-learning-refinement/targeted.txt). [9 zorunlu komut](ui-learning-refinement/checks.json) exit0: kilitli dev sync, docs/artifacts/learning, Ruff check/format,9 locked unittest ve kurulu giriş noktası smoke. Test beklentileri güncellendikten sonra Ruff check/format ayrıca geçti. [Kurulu wheel](ui-learning-refinement/wheel.json)107 makale,85 görünür konu,10 aşama ve yeni QML bileşenini `/tmp` altında dış kaynak mountuna bağımlı olmadan yükledi. [Tüm merdiven](ui-learning-refinement/stairs-overview-1366.png), Veri kartları ve başlangıç sırası yerel olarak incelendi.

İlk genel koşu [471 geçti/2 eski beklenti başarısız](ui-learning-refinement/pytest-initial.txt): artık Öğren'de bulunmayan yardım düğmesinin tıklanmasını ve eski54 sözlük makalesini bekleyen kontroller. Yeni beklentiler Öğren'deki düğmenin yokluğunu, Veri ekranındaki düğmenin gerçek tıklanmasını ve62 kaynak kavramını doğrular; nihai genel koşu473 geçti.

[Sistem Python3.14 unittest](ui-learning-refinement/system-unittest.txt)49 discovery içinde40 eksik bağımlılık import hatasıyla başarısızdır; sistem ortamı değiştirilmedi. Kilitli CPython3.13'te9 unittest geçti. İki ortam karıştırılmaz; fiziksel masaüstü insan kabulü ayrıca beklenir.
