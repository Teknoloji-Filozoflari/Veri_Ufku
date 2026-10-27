# Öğren aşamaları ve Veri kaynak anlatımı

2026-10-09, ENV-UI-LEARNING; Linux CPython3.13/PySide6/QML offscreen/software. Açık kullanıcı UI kapsamı; yeni faz veya analitik özellik başlatılmadı. Fiziksel masaüstü/insan kabulü değildir.

| Kabul | Kod/gerçek kontrol | Kanıt |
|---|---|---|
| UIL-01 Her99 konu tek aşama/alt başlık; filtrede yol korunur | learning/taxonomy.py; test_learning_tree.py tam katalog üyelik ve eşsizliği | ui-learning-tree/pytest.txt |
| UIL-02 Veri.md özgün korunması, hash, çevrimdışı başlıklı anlatım | docs/learning_sources/VERI.md ve VERI_PROVENANCE.json; content/tr.json; kaynak bütünlük testi | ui-learning-tree/pytest.txt |
| UIL-03 Aşama/alt başlık Space; konu modal;720×560 uyarlama; Escape odak geri dönüşü; mevcut F1/depth korunması | LearningCenter/Main/ArticleView.qml; test_learning_tree_gui.py ve test_learning_gui.py | ui-learning-tree/targeted.txt; ui-learning-tree/walkthrough.json |

[Başlık ağacı](ui-learning-tree/hierarchy-1366.png), [Veri okuma penceresi](ui-learning-tree/data-reader-1366.png), [dar ekran](ui-learning-tree/data-reader-720.png). Kaynak dış dosya değiştirilmedi; salt okunup birebir proje kopyası alındı. Derlenmiş anlatım katalog içindedir; harici diske çalışma zamanı bağımlılığı yoktur. Yerinde bulunmayan Obsidian görselleri dahil edilmedi. Kesikli/sürekli ile aralık/oran ayrımı resmi kaynaklarla düzeltilerek ayrı başlıklandırıldı; özgün metin korunur. İçeriği olmayan yol haritası başlıkları pasiftir. İsteğe bağlı okundu/yer imi ve sözlük korunur.

Gerçek komut/exit/tarih [checks.json](ui-learning-tree/checks.json), ortam [environment.json](ui-learning-tree/environment.json). Test sonucu aşağıda kaydedilir; çalıştırılmayan kontrol başarı değildir.

Sonuç: [473 pytest testi,132.97s](ui-learning-tree/pytest.txt) ve [20 odaklı öğrenme/GUI testi,5.85s](ui-learning-tree/targeted.txt) geçti. Dokuz zorunlu komut exit0: kilitli dev sync; docs/artifacts/learning; Ruff check/format;9 kilitli unittest; kurulu giriş noktası smoke. [Wheel doğrulaması](ui-learning-tree/wheel.json) `/tmp` altında gerçekten kurulan paketle11 Veri bölümü ve10 aşamayı kaynak mountuna ihtiyaç olmadan yükledi. Geniş/dar pencere görselleri yerel olarak incelendi.

[Sistem Python3.14 unittest](ui-learning-tree/system-unittest.txt)49 test discovery içinde40 eksik bağımlılık import hatasıyla başarısızdır. Bu ortam değiştirilmedi; kilitli CPython3.13 ortamındaki9 başarılı unittest ile karıştırılmaz. Gerçek insan masaüstü kabulü beklenir; faz/olgunluk artırılmaz.
