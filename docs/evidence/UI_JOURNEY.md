# Veri_Ufku — başlangıç yolculuğu ve gelişmiş çalışma

2026-10-17 / UI-JOURNEY-01. Kullanıcının yol haritası, sayfa/başlık düzeni ve
başlangıç/gelişmiş görünüm talimatı uygulandı. Önceki UI_RENEWAL teknik teslimini
genişletir; yeni faz veya yöntem kabulü değildir. Kirli/untracked çalışma ağacı
korundu; stage/commit/push, dependency değişimi ve kullanıcı verisi üzerinde işlem yok.

## Uygulanan düzen

- İlk kullanımda mevcut `PresentationPreferences` başlangıç seçimini kullanır.
  Kullanıcının sonradan seçtiği gelişmiş tercih sonraki açılışlarda korunur.
- Başlangıç ana sayfası: numaralı, aynı hizada bağlantılı Veri Bilimi Yol Haritası;
  sonunda **Kendi yolculuğunu başlat** ve gerçek proje oluştur/aç/kaydet alanı.
- Harita başlıkları ve alt işlemleri ilgili GUI alanlarını açar. Senaryo ve izleme
  artık mevcut ileri araçlara bağlıdır; Gelişmiş etiketi bu geçişi önceden gösterir.
  Yol haritası yönlendirmesi hesap çalıştırmaz veya veri değiştirmez.
- Başlangıç menüsü eylemleri anlatır: Veriyi tanı, Veriyi hazırla, Desenleri keşfet,
  Farkları karşılaştır, Model kur, Bulguları paylaş. Veri/analiz/model/rapor ekranları
  soru, yapılacak iş, beklenen çıktı ve kısa gündelik örnekle başlar.
- Her çalışma ekranındaki kavram bağlantısı Öğren'i ve ilgili makaleyi açar.
  Öğren'de aynı aşama kimlikleri/sırası/başlıkları vardır; terimler, açıklamalar ve
  arama sonuçları o haritanın altında açılır. Ek laboratuvarlar haritanın sonunda.
- Gelişmiş görünüm başlangıç anlatısını kaldırır; workflow/recipe/dashboard,
  ileri istatistik, senaryo/monitoring ve code/environment/plugin/repro/share
  panellerine doğrudan erişim sağlar. Formlar seviye değişince silinmez.
  Yöntem aramasından uzman araç seçmek açık bir gelişmiş görünüm geçişidir.
- Seviye bir sunum tercihidir; kaynak bütçesi, doğrulama, güvenli import/export,
  salt okunurluk, veri erişimi veya kod çalıştırma onayı bypass edilmez.

Değişen kaynaklar: Main.qml, ScienceRoadmap.qml, RoadmapSteps.js, LearningCenter.qml;
yeni JourneyGuide.qml. `home` makalesi11/katalog92 güncellendi.414makale kimliği
korundu. Geliştirici içerik güncellemesi uzman bilimsel onayı sayılmaz.

## Referans ve kapsam

Kullanıcının [DataiTeam Titanic EDA](https://www.kaggle.com/code/kanncaa1/dataiteam-titanic-eda)
bağlantısı açıldı fakat notebook hücreleri araç çıktısında okunamadı. İçeriğin
birebir incelendiği veya kopyalandığı iddia edilmez. Kullanıcının anlattığı
örnekle öğrenme akışı esas alındı: kaynağı/sütunları tanı → eksikleri/desenleri
incele → hazırlama/karşılaştırma → ayrı model değerlendirmesi → bulguyu anlat.
Uygulamaya Kaggle veri indirmesi, hesap sonucu veya yeni Titanic dataset'i eklenmedi.
Yolcu/yaş örnekleri açıklamadır; hesaplanmış Titanic bulgusu değildir.

## Gerçek doğrulama

CPython3.13.15 kilitli `.venv`, PySide6.11.2; CachyOS Linux; izole geçici proje/XDG,
Qt offscreen/software. Fiziksel masaüstü veya yeni başlayan insan testi değildir.

| Kanıt | Sonuç / kapsam |
|---|---|
| [initial](ui-journey/initial.xml) |20PASS; mevcut kabuk, tercihler, yardım ve UI kontrolleri |
| [workflows](ui-journey/workflows.xml) |23PASS; proje klasörü, hazırlama, istatistik, rapor, environment ve harita |
| [final navigation](ui-journey/final-navigation.xml) |9PASS; gerçek yönlendirme, makale/sözlük, iki seviye, ortak harita, UI contracts |
| [shell final](ui-journey/shell-final.xml) |14PASS; son kabuk/tercih ve güncel ekran kanıtı |
| [wheel](ui-journey/wheel.xml) |4PASS; kurulu noneditable wheel yolculuk/harita/okuma ve gerçek temizleme→grafik→export→reopen |
| [package](ui-journey/package.json) |433dosya kaynak/wheel/kurulu dizinde byte-eşit |
| [Ruff](ui-journey/ruff-final.log), [format](ui-journey/format-final.log) | PASS |
| [learning](ui-journey/learning.log), [usability](ui-journey/usability.log), [artifact](ui-journey/artifacts.log), [docs](ui-journey/docs.log) | PASS |

Test sayıları örtüşür; toplanmaz. İlk yeni test QObject ağacında Repeater öğesini
bulamadı; mevcut görsel-ağaç yardımcısı kullanılarak düzeltildi (journey.xml1fail).
Klasör/okuma testlerinin önceki gizli-yardım beklentileri görünür yardım davranışına
uyarlandı; dosya işlemi/odak/kimlik/hesap kontrolleri korunur. Roadmap testi artık
mevcut senaryo aracının açık gelişmiş yönlendirmesini doğrular. Öğrenme başlıkları
ve geniş/dar kart hizası için beklenti yeni ortak doğrusal tasarıma güncellendi.

Yeni test `tests/test_journey_gui.py`: first-run beginner, proje haritanın sonunda,
altı açıklama bağlantısı gerçek makale, home/learn aynı aşama kimlikleri,
advanced alan erişimi/form koruma,720px/%200 ve proje draft değişmezliği.
Görseller gerçek Qt render'dır; maket değildir.

## Ekranlar

- [Başlangıç](ui-journey/final-screens/beginner-home.png)
- [Harita sonunda proje](ui-journey/final-screens/project-at-journey-end.png)
- [Veriyi tanı](ui-journey/final-screens/beginner-data.png)
- [Aynı haritayla Öğren](ui-journey/final-screens/learn-map.png)
- [Gelişmiş başlangıç](ui-journey/final-screens/advanced-home.png)
- [Dar pencere / %200 yazı](ui-journey/final-screens/home-720-2.0.png)

Bu görevde yeni performans benchmark'ı yapılmadı; önceki startup ölçümü yeni
sürüm ölçümü olarak sunulmaz. Önceki uzun oturum/RAM/process-budget, GC uyarısı,
insan/AT/minHW/offlineinstaller/remoteCI ve uzman review açıkları korunur.
Faz74 Flatpak adayları bu UI'yı içermez. Yerel wheel test paketi dış release değildir.
Başlatma: repo kökünde `.venv/bin/veri-ufku`.
