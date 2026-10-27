# Ortak işlem/öğrenme yol haritası ve ön işleme anlatımı

2026-10-09, ENV-UI-SHARED-ROADMAP; Linux CPython3.13/PySide6/QML offscreen/software. Açık kullanıcı UI/eğitim kapsamı; yeni analitik faz/algoritma yoktur. İnsan masaüstü kabulü değildir.

| Kabul | Yol | Gerçek kontrol |
|---|---|---|
| UIL-06a Aynı kıvrılan çizgi/kart/numara: Başlangıç işlem, Öğren açıklama | ScienceRoadmap.qml, LearningTrail.qml | test_learning_tree_gui.py geniş/dar aynı kart x/genişlik; test_science_roadmap_gui.py root Data/Hazırla işlem yönlendirmesi; bilgi açılmaz |
| UIL-06b Alt işlem doğru araç ve güvenli kullanıcı eylemi | RoadmapSteps.js; Main.qml | Gerçek Qt Temizleme→operationKind3; Birleştirme→operationKind4/transformMethod8 JOIN; kaynak/proje taslağı korunur; fit/preview/apply başlatılmaz |
| UIL-06c Kodsuz kaynak, dört ön işleme bölümü ve üç ölçekleme açıklaması | content/tr.json; taxonomy.py; docs/learning_sources/VERI_TEMIZLEME.md | test_learning_tree.py kaynakta kod yokluğu; başlıklar; aykırı otomatik silme yok; train-only minmax ve zscore normal dağılım garantisi yok |
| UIL-06d Açıklama/kaynak/arama/F1/iptal akışı korunur | ArticleView.qml; Main.qml | Mevcut test_learning_gui.py ve test_learning_tree_gui.py; roadmap planlanan handler engeli |

Python kodları kaynak metne ve anlatıma dahil edilmedi; yeni script/pipeline olarak çalıştırılmadı. Kaynak proje kaydı ve hash `TEMIZLEME_PROVENANCE.json` içinde; sohbetten aktarılmış düzenli metindir, byte-birebir dış dosya iddiası yoktur. İndirgeme, kullanıcının başlıkta saydığı fakat ayrıntı vermediği bölüm olarak kavramsal tamamlandı. Yeni normalizasyon/düzgünleştirme/kümeleme/genel boyut indirgeme algoritması uygulanmadı. Öğrenmede planlanan kavram okunabilmesi Başlangıçta aracın etkin olması anlamına gelmez. Aykırı/tekrar/eksik kayıtlar otomatik silinmez; doldurma/ölçekleme eğitim/fold içinde öğrenilir; train/final test birleştirme örneği kullanılmadı.121 çevrimdışı makale/99 görünür konu/62 statik yardım bağı.

Başlangıç ana başlığı doğrudan işlem ekranını açar; ayrıca okla alt eylemler görünür. Proje alanına giden yol yeni proje düğmesine odaklanır ve görünür alana getirir. Araç seçimi hazır önizlemeyi aynı normal kullanıcı seçimindeki gibi bırakır; veri sürümü değiştirilmez. Çalışan işlem varken devre dışı seçim zorla değiştirilmez. Model doğrulama/regresyon yolu ilgili kontrolü görünür alana getirir; çalıştırma düğmesine basılmaz.

Ham komut/exit/tarih `ui-shared-roadmap/checks.json`, ortam `environment.json`, testler `targeted.txt`/`pytest.txt`, gerçek görüntüler `walkthrough.json` içinde tutulur. Yürütülmeyen kontrol başarılı sayılmaz; faz ve olgunluk artırılmaz.

Nihai doğrulama: [475 pytest testi,140.46s](ui-shared-roadmap/pytest.txt) ve [24 odaklı öğrenme/yol haritası/klasör testi,9.52s](ui-shared-roadmap/targeted.txt) geçti. [9 zorunlu komut](ui-shared-roadmap/checks.json) exit0: kilitli dev sync; docs/artifacts/learning; Ruff check/format;9 locked unittest; kurulu giriş noktası smoke. Son açıklama güncellemesinden sonra learning kontrolü121 makale/62 statik bağı doğruladı; modlu yol haritasının dinamik yardım bağları gerçek F1 testleriyle kontrol edildi.

[Kurulu wheel](ui-shared-roadmap/wheel.json), gerçek QML ile `/tmp` altında121 makale/99 konu/10 aşamayı ve kodsuz temizleme anlatımını yükledi; harici kaynak mountuna çalışma zamanı bağımlılığı yoktur. [Başlangıç genel görünüm](ui-shared-roadmap/home-overview-1366.png), [aynı Öğren genel görünüm](ui-shared-roadmap/learn-overview-1366.png), [temizleme alt başlıkları](ui-shared-roadmap/learn-cleaning-1366.png), [temizleme açıklaması](ui-shared-roadmap/cleaning-reader-1366.png), [dar açıklama](ui-shared-roadmap/cleaning-reader-720.png), [gerçek walkthrough](ui-shared-roadmap/walkthrough.json). Geniş/dar ekran görselleri yerel olarak incelendi.

[Sistem Python3.14 unittest](ui-shared-roadmap/system-unittest.txt)49 discovery içinde40 eksik bağımlılık import hatasıyla başarısızdır. Sistem ortamı değiştirilmedi; kilitli CPython3.13'te9 unittest geçti. İnsan masaüstü kabulü ve faz olgunluğu artırılmadı.
