# Veri_Ufku — Kalıcı arayüz ve tasarım kuralları

Kaynak: [birleşik talimat](../Veri_Ufku_Birlestirilmis_Gelistirme_Promptlari.md). Faz 00, 2026-10-06. Kullanıcı talimatları bu kayda göre önceliklidir.

VERİ_UFKU — ARAYÜZ TASARIMI VE TASARIM BÜTÜNLÜĞÜ TALİMATI

Bu kalıcı talimat bütün fazlarda geçerlidir. Ürünün görünen adı tam olarak Veri_Ufku'dur. Faz 00'da docs/UI_DESIGN_BRIEF.md'ye kaydet; tek seferlik bir bekleme talimatı değildir.

AMAÇ

Veri bilimi bilmeyen kullanıcıların rahat kullanabildiği, profesyonel kullanıcıların gerekli ayrıntılara erişebildiği, sade, modern ve tutarlı bir Linux masaüstü arayüzü oluştur.

REFERANS İNCELEMESİ

Arayüzü tasarlamadan veya mevcut arayüzü iyileştirmeden önce Orange Data Mining, KNIME Analytics Platform, jamovi, JASP ve LabPlot'un resmi ekran görüntülerini, kullanım belgelerini ve mümkünse demo akışlarını incele.

Yalnızca inceleyebildiğin ekranlar üzerinden değerlendirme yap. Görmediğin davranışları tahmin ederek raporlama. Kaynaklara erişemiyorsan bunu açıkça belirt.

Şu kullanım ilkelerini değerlendir:

- Orange: görsel keşif ve analiz araçları arasındaki bağlantılar.
- KNIME: profesyonel iş akışı düzenleme ve işlem yapılandırma.
- jamovi: veri tablosundan analize kolay geçiş.
- JASP: parametrelerle sonuçların birlikte incelenmesi ve gelişmiş seçeneklerin aşamalı açılması.
- LabPlot: grafik düzenleme ve bilimsel figür hazırlama.

Her referans uygulamadan mutlaka bir özellik veya görünüm almak zorunda değilsin. Yalnızca Veri_Ufku'nun kullanıcı ihtiyaçlarını karşılayan fikirleri seç.

TEK VE TUTARLI TASARIM DİLİ

Referans uygulamaların ekranlarını, menülerini, renklerini ve bileşenlerini ayrı ayrı alıp birleştirme. Referanslardan kullanım ilkelerini öğren; seçilen fikirleri Veri_Ufku'nun kendi tasarım diline uyarlayarak uygula.

Önce uygulamanın tamamı için ortak bir tasarım sistemi oluştur:

- Tutarlı navigasyon ve ekran yapısı.
- Ortak tipografi, renkler ve boşluk düzeni.
- Tutarlı düğme, form, panel, tablo ve grafik bileşenleri.
- Aynı işlemler için aynı etkileşim davranışları.
- Açık, koyu ve sistem temasında okunabilirlik.
- Klavye kullanımı, görünür odak ve ekran ölçeklendirmesi.

Görsel kimlik sade, modern ve sakin olsun. Profesyonel araçlara erişim sağlarken başlangıç ekranlarını kalabalıklaştırma.

Marka, ikon ve özgün görsel varlıkları kopyalama. İkonlar ve diğer varlıklar için lisansı uygun kaynaklar kullan; gerekli atıfları kaydet.

BAŞLANGIÇ GÖRÜNÜMÜ

- Dosya, kullanıcının amacı ve sonraki işlem açıkça anlaşılmalı.
- Temel analiz için kod veya görsel düğüm editörü kullanmak zorunlu olmamalı.
- Teknik ayrıntılar gerektiğinde açılmalı.
- “Bu ne işe yarar?”, “Nasıl yorumlarım?” ve “Örnekle öğren” bağlantıları ilgili işlem ve sonucun yanında bulunmalı.
- Açıklamalar isteğe bağlı okunmalı; kapatılması çalışmayı kesmemeli.
- Varsayımlar ve kritik sınırlamalar sade dilde görünür kalmalı.

UZMAN GÖRÜNÜMÜ

- Veri, parametre, sonuç ve tanılamalar arasında hızlı geçiş.
- Analiz sekmeleri ve sonuç karşılaştırma.
- Aranabilir ve açıklamalı ileri parametreler.
- Profesyonel fazlarda görsel workflow ve dashboard düzenleme.
- Veri sürümü, filtre, yöntem, değerlendirme ve hesap kapsamına erişim.

Başlangıç ve uzman görünümü aynı veri, işlem ve sonuçları kullanmalı. Görünüm değiştirmek proje durumunu kaybettirmemeli.

BELGELER VE EKRAN PLANI

Bu talimatı docs/UI_DESIGN_BRIEF.md dosyasına kaydet ve mimari/UX belgelerine bağla.

Faz 00 kapsamında docs/UI_REFERENCES.md oluştur. Kaynak bağlantılarını, gerçekten incelenen ekranları, seçilen kullanım ilkelerini ve tasarım kararlarının gerekçelerini belgele.

Şu ekranların tasarımını planla:

1. Başlangıç ve amaç seçimi.
2. Dosya içe aktarma önizlemesi.
3. Veri tablosu ve kalite paneli.
4. İşlem öncesi/sonrası karşılaştırma.
5. Grafik oluşturma ve düzenleme.
6. Analiz/model parametreleri ve sonuçlar.
7. Bağlama bağlı öğrenme paneli.
8. Profesyonel workflow ve dashboard.

Bu ekranları ilgili geliştirme fazlarında uygula. Gelecek fazların özelliklerini erkenden geliştirme veya çalışıyormuş gibi gösterme.

AŞAMALI TASARIM DOĞRULAMASI

Arayüz yaklaşımını bütün uygulamaya yaymadan önce dosya içe aktarma, veri inceleme ve analiz sonucu ekranlarının temsilî tasarımlarını aynı tasarım sistemiyle oluştur.

Bu üç ekranı tutarlılık, okunabilirlik, bilgi yoğunluğu ve kullanım akışı açısından birlikte değerlendir. Bulunan sorunları diğer ekranlara geçmeden düzelt.

Erken tasarım önizlemelerini açıkça prototip olarak belirt. Gerçek işlevleri ilgili fazlarda geliştir; prototipi tamamlanmış analiz özelliği sayma.

TEKNİK SINIRLAR

Python/PySide6/QML mimarisini koru. Görsel referans çalışması için uygulamayı yeniden yazma veya web uygulamasına dönüştürme.

Henüz geliştirilmemiş özellikleri çalışırmış gibi gösterme. Tasarım tercihleri veri bütünlüğünü, performansı, erişilebilirliği veya öğrenme özelliklerini zayıflatmamalı.

KABUL ÖLÇÜTLERİ

- Tasarım referansları ve kararları belgelenmiş.
- Arayüz bütün ekranlarda tek bir görsel dile sahip.
- Yeni başlayan kullanıcı temel analiz yolunu kod veya düğüm editörü kullanmadan tamamlayabiliyor.
- Uzman kullanıcı gerekli parametre ve tanılamalara erişebiliyor.
- Öğrenme paneli kapatıldığında çalışma kesilmiyor.
- Başlangıç ve uzman görünümü arasında veri veya proje kaybı oluşmuyor.
- Doğrulanmayan görsel veya işlevsel davranışlar başarılı diye raporlanmıyor.
