# Veri Bilimi Yol Haritası — açılabilir kıvrılan aşamalar

2026-10-08, ENV-UI-ROADMAP; açık kullanıcı arayüz kapsamı. Yeni analitik faz başlatılmadı; faz/olgunluk/kapsam aynı kaldı. Python/PySide6/QML Linux masaüstü korunur. Offscreen/software geliştirici kontrolü; gerçek insan veya fiziksel masaüstü kabulü değildir.

| Kabul | Kod yolu | Gerçek kanıt |
|---|---|---|
| UIR-01 Tam başlık Veri Bilimi Yol Haritası | Main.qml, ScienceRoadmap.qml | test_home_folders_gui.py, test_science_roadmap_gui.py |
| UIR-02 On aşama, açıklama ve açılabilir alt başlıklar; analiz için beş Türkçe/İngilizce kavram | RoadmapSteps.js, ScienceRoadmap.qml | Gerçek QML Space ile accordion açma/kapatma; analysis-expanded-1366.png |
| UIR-03 Numaralı kıvrılan çizgi, genişte dönüşümlü iki yan, darda tek sütun | ScienceRoadmap.qml Canvas/Column/Repeater | Gerçek Qt720/1366 geometrisi; overview-1366.png, timeline-720.png |
| UIR-04 Açılma/kapanma240ms, ok dönüşü180ms, ilk kart görünüşü300ms; kalıcı hareket döngüsü yok | ScienceRoadmap.qml | Qt item açılma ve kayıtlı görüntüler; gerçek animasyon koşusu |
| UIR-05 Açılabilir hazır yollar mevcut ekran ve uygun Veri tabına gider; planlanan yol pasif ve handler korumalı | Main.qml navigation, RoadmapSteps.js | test_science_roadmap_gui.py Data profil tab0/nav1 odak; planlanan kuralcı tıklama etkisiz; proje taslağı korunur |
| UIR-06 Çevrimdışı yardım/F1 ve klavye odağı | ScienceRoadmap.qml helpContext/FocusScroll.js, learning/content/tr.json | home.roadmap→home gerçek Qt yardım; check_learning bütün bağlar |

Yollar `src/veri_ufku/ui/qml/` ve testler `tests/` altındadır. Tam akış: Veri → Veriyi Analiz Etme → Veri Temizleme → Veri Görselleştirme → İlişkileri Keşfetme → İstatistiksel Karşılaştırma → Modelleme → Modeli Değerlendirme → Bulguları Paylaşma → İzleme ve İyileştirme. Kullanıcının kabaca verdiği başlıklar ve İngilizce analiz adları yazım olarak düzenlendi. Aşamalar zorunlu tamamlanma sırası değildir; geri dönülebilir. Sınıflandırma/kümeleme/anomali eğitimi, kuralcı karar araçları ve izleme yalnız planlanan alt yoldur; bu düzenleme algoritma veya gelecek faz uygulamaz. İndirgeme model hazırlığındaki özellik seçimine bağlanır; genel boyut indirgeme hazır diye sunulmaz.

[Görsel ölçüm](ui-science-roadmap/walkthrough.json), [ham çıktı](ui-science-roadmap/walkthrough.txt), [tam genel görünüm](ui-science-roadmap/overview-1366.png), [açık analiz başlığı](ui-science-roadmap/analysis-expanded-1366.png), [dar çizelge](ui-science-roadmap/timeline-720.png). Görseller yerel olarak incelendi. Testler ve nihai komut/exit/ortam kayıtları aynı dizinde tutulur; sonucu olmayan kontrol başarı sayılmaz.

Son doğrulama: [470 pytest,135.72s](ui-science-roadmap/pytest.txt); son odak/planlanan handler değişikliğinden sonra [12 GUI testi,20.48s](ui-science-roadmap/targeted.txt). [9 gerçek kontrol komutu](ui-science-roadmap/checks.json) exit0: kilitli dev sync, docs/artifacts/learning, Ruff check/format,9 locked unittest ve kurulu giriş noktası smoke. [Ortam](ui-science-roadmap/environment.json),99 çevrimdışı makale/65 UI bağı.

Sistem Python3.14 [unittest discovery](ui-science-roadmap/system-unittest.txt)38 eksik paket import hatasıyla başarısız; sistem ortamı değiştirilmedi. Kilitli CPython3.13 discovery9 geçti; iki sonuç birbirinin yerine başarılı diye kaydedilmez.
