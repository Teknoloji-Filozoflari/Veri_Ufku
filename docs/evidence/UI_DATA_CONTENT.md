# Veri içeriği ve dosya başlangıç alanı

2026-10-09, ENV-UI-DATA-CONTENT. Kullanıcının açık Veri sayfası düzenlemesi; sonraki analitik faz başlatılmadı. Faz/olgunluk durumları değiştirilmedi.

UID-01: Main.qml üst dosya kartı, RoadmapSteps.js üzerinden dört ortak eylem. UID-02: DataContent.qml aktif veri sürümünden toplam/kaynak/satır birimi ve sütun sözlüğü; ColumnDetails.qml kullanıcı açıklaması; analytics/contracts.py sınır/geriye uyum ve yeni metadata sürümü. UID-03: DatasetPanel.qml tablo/profil kapsamı ayrı; mevcut çevrimdışı dataset-profile yardımı güncellendi.

Kaynak hücreler değişmez. Açıklama alanı gerçek anlamı otomatik tahmin etmez; kullanıcı girer. Rol/açıklama ekleme yeni metadata sürümüdür; kayıt önce taslağa, açık Projeyi kaydet eylemiyle kalıcıdır.

Kullanıcı üç Kaggle notebook adresindeki Data Content / Read and Analyse Data başlıklarını referans verdi. Web erişim denemesi401 token_revoked ile başarısız; notebook metni/görselleri incelenmiş sayılmaz. Yerleşim kullanıcının tarifinden ve mevcut ortak tasarım sisteminden oluşturuldu. Başlık veya notebook hesapları kopyalanmadı.

Gerçek komutlar/çıkışlar ui-data-content/checks.json ve ayrı metin kayıtlarında; ortam ve gerçek QML ekranları environment.json/walkthrough.json içindedir. İnsan masaüstü/native dosya seçici kabulü veya uzak CI başarısı iddia edilmez.

Görsel inceleme: [1366px başlangıç](ui-data-content/data-content-1366.png), [720px başlangıç](ui-data-content/data-content-720.png), [1366px sözlük](ui-data-content/data-dictionary-1366.png), [720px sözlük](ui-data-content/data-dictionary-720.png) gerçek QQuickWindow.grabWindow çıktılarıdır ve yerel olarak incelendi. Dar üst kart metin sarması düzeltilip yeniden render edildi. Sözlük kullanıcı açıklaması ve TL birimini gösterir; fiziksel hücreler değiştirilmez.

İlk tam koşuda iki eski test Dosya içe aktar sekmesinin varsayılan görünmesini beklediği için başarısızdı; çıktılar initial-pytest.txt ve initial-targeted.txt içinde korundu. Yeni varsayılan Veri tablosu olduğundan drop testi sekmeyi açıkça seçer, kabuk testi üst dataImportStart ve dataContentPanel görünürlüğünü doğrular. Sonraki hedefli koşu27 test geçti.

Nihai kontrol: [476 pytest testi141.87s](ui-data-content/pytest.txt), [27 hedefli test13.61s](ui-data-content/targeted.txt), [9 kilitli unittest](ui-data-content/unittest.txt), kurulu giriş noktası [GUI_SMOKE PASS](ui-data-content/entry.txt). Locked dev sync, sistem/kilitli check_docs, check_artifacts, check_learning (121 makale/64 statik bağ), Ruff check/format exit0. [Komut/exit/tarih](ui-data-content/checks.json), [ortam](ui-data-content/environment.json), [gerçek render](ui-data-content/walkthrough.json).

Sistem Python3.14 unittest discovery49 test içinde40 eksik bağımlılık import hatasıyla başarısız; [gerçek çıktı](ui-data-content/system-unittest.txt). Sistem Python değiştirilmedi. Desteklenen kilitli CPython3.13 ortamındaki kontroller geçti; sistem kontrolü başarılı sayılmaz. Gerçek insan/native dosya seçici/uzak CI kabulü yapılmadı.
