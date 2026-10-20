# Öğren analiz yaklaşımları ve açılabilir kaynaklar

2026-10-09, ENV-UI-LEARNING-ANALYSIS, Linux CPython3.13/PySide6/QML offscreen/software. Açık kullanıcı UI/eğitim içeriği kapsamı; yeni analitik faz veya optimizasyon algoritması yoktur. Gerçek insan masaüstü kabulü değildir.

| Kabul | Yol | Gerçek kontrol |
|---|---|---|
| UIL-05a Kaynaklar varsayılan kapalı, düğmeyle açık, farklı/aynı konu açılışında tekrar kapalı | ArticleView.qml; ui/learning.py articleOpened | test_learning_tree_gui.py gerçek Space ve kaynak label yokluğu/varlığı |
| UIL-05b Genel analiz ile beş Türkçe/İngilizce analiz türü ve başlıklı anlatım | learning/taxonomy.py; content/tr.json | test_learning_tree.py altı başlık, kaynak kayıt/hash, katalog tam/çakışmasız üyelik |
| UIL-05c Kuralcı kavram okunur, yeni eylem aracı çalışmaz; metin ve görsel sınırları doğru | content/tr.json; RoadmapSteps.js değişmedi | GUI kuralcı kritik açıklaması; mevcut roadmap testi; learning/artifacts kontrolü |

Kullanıcının verdiği metin `docs/learning_sources/VERININ_ANALIZI.md` içinde kayıtlıdır. Sohbet metninin başlık/boşlukları dosya düzenine alınmıştır; byte-birebir dış dosya iddiası kurulmaz. Hash/provenance `ANALIZ_PROVENANCE.json` içindedir. Altı yeni açıklama113 makale/91 görünür konuya ulaşır; mevcut açıklayıcı/teşhis/özet kavramları ilgili alt başlıklarda korunur. Tekniğin adı tahmin ya da otomatik karar garantisi gibi sunulmaz; keşif sonuçları doğrulanmış sayılmaz. Yalnız dosya adları verilen iki görsel eklenmez; keşif adımları okunabilir maddelerle anlatılır. Yeni optimizasyon/otomatik eylem yeteneği eklenmedi. Kaynak görünümü aynı makale yeniden açılırken de kapalıdır; iş ve isteğe bağlı okuma kayıtları kaynak görünümünü sıfırlamaz.

Gerçek kontroller ve tarih/exit `ui-learning-analysis/checks.json`, ortam `environment.json`, testler `targeted.txt`/`pytest.txt`, görüntüler ve açma-kapama `walkthrough.json` içinde tutulur; yürütülmeyen kontrol başarılı sayılmaz.

Nihai doğrulama: [474 pytest testi,139.85s](ui-learning-analysis/pytest.txt), [21 odaklı test,6.75s](ui-learning-analysis/targeted.txt). Dokuz zorunlu komut exit0: kilitli dev sync; docs/artifacts/learning; Ruff check/format;9 kilitli unittest; kurulu giriş noktası smoke. Son kaynak/ekran bağı güncellemesinden sonra learning kontrolü ayrıca113 makale/65 bağı doğruladı. [Kurulu wheel](ui-learning-analysis/wheel.json) `/tmp` altında113 makale, altı yeni analiz açıklaması ve kapalı kaynak bileşenini doğruladı; harici kaynak dosya bağımlılığı yoktur.

[Başlık görünümü](ui-learning-analysis/analysis-headings-1366.png), [kuralcı açıklama](ui-learning-analysis/prescriptive-reader-1366.png), [kapalı kaynaklar](ui-learning-analysis/sources-closed-1366.png), [açık kaynaklar](ui-learning-analysis/sources-open-1366.png), [dar keşif açıklaması](ui-learning-analysis/exploratory-reader-720.png), [gerçek walkthrough](ui-learning-analysis/walkthrough.json). Geniş/dar görseller yerel olarak incelendi. Kaynak yorum düzeltmeleri NIST/IBM ve proje eğitim/test sözleşmesiyle desteklenir; katalogda kaynakları kayıtlıdır.

[Sistem Python3.14 unittest](ui-learning-analysis/system-unittest.txt)49 discovery içinde40 eksik bağımlılık import hatasıyla başarısızdır. Sistem ortamı değiştirilmedi; kilitli CPython3.13'te9 unittest geçti. İnsan masaüstü kabulü/faz olgunluğu artırılmaz.
