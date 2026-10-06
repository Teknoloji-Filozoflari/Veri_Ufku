# Veri_Ufku — üç temsilî ekran tasarım incelemesi

2026-10-06, DESIGN-00. [SVG açık tema](prototypes/triptych.svg), [koyu](prototypes/triptych-dark.svg); PNG render aynı dizinde. Bunlar statik **prototip**; düğmeler ve tablolar çalışmaz, gerçek analiz sonucu yok. Faz00 kodlanmış GUI yok.

## Ortak inceleme

Kompakt ekran taslakları aynı genişlikte yan yana; bu çizimler gerçek pencerenin birebir ölçüsü değil, dar görünümde yardım alt karttır. Gerçek geniş pencerede sağ panel UX/DESIGN_SYSTEM planına göre uygulanacaktır. Üç ekran yan yana aynı üstbilgi/version/scope, sol navigasyon, içerik ve bağlam paneli düzenini kullanır. Import, tablo ve analizde bir ana CTA. Sonuç ekranı veri/filtre/yöntem/kapsamı kaybetmez. SVG, yerel QtSvg ile PNG'ye render edildi ve görsel olarak incelendi; bu referans uygulamalarının resimleri değil, kendi tasarım örneğimizdir.

| Alan | İlk taslak sorunu | Düzeltilen tasarım / kalan gerçek doğrulama |
|---|---|---|
| Tutarlılık | Import ve sonuçta farklı aksiyon yeri riski | Bütün ana eylemler içerik altı, aynı boyut/token; gerçek Qt responsive plan Faz02 |
| Okunabilirlik | Sürüm+filtre+scope uzun tek satır | Ayrı üst bağlam satırı, ana başlık/gövde hiyerarşisi; 200% ölçekte gerçek Qt metin taşması test edilmeli |
| Yoğunluk | Sürekli yardım ve ileri ayarlar başlangıcı kalabalıklaştırır | Sağ panel bağlama göre tek içerik; kapatılabilir, kritik sınır merkezde kalır |
| Akış | Uygula ile Import/Çalıştır anlamı karışabilir | Eylem fiili bağlama özel; preview etki → uygula; analizde gerçek sonuç yok etiketi |
| Belirsizlik | Örnek tablo tam veri sanılabilir | Full/sample badge ve snapshot aşaması; ilk preview örnek, yayın sonrası dataset |
| Erişilebilirlik | Renkle durum anlaşılması | Metin etiket, focus token ve kontrast hedefi; gerçek keyboard/AT denemesi henüz yok |

Statik tasarım kontrolü tema tokenları ve ekran düzeniyle sınırlıdır. Faz02'de gerçek light/dark/system, 1366/1024px ve 100–200% scaling, keyboard/odak/AT; Faz05/07/14+ gerçek iş akışı; Faz25 yeni kullanıcı denemesi ayrı kanıt. UI-REF-VIS resmî referans görsellerinin okunabilir incelemesi halen doğrulanmadı, uygulama tasarımını yayma kapısıdır.
