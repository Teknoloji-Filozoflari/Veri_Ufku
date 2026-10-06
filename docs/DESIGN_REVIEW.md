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

## Faz02 ortak kabuk incelemesi — 2026-10-06

Üç açık/koyu statik prototip yeniden view_image ile incelendi: importta kaynak/ayar, tablo incelemede sürüm/kalite, sonuçta yöntem/kapsam aynı token hiyerarşisini kullanıyor. Gerçek kabuk screenshot’larıyla renk, metin hiyerarşisi ve isteğe bağlı yardım ilkeleri karşılaştırıldı. Prototipler gerçek import/table/analysis özelliği sayılmadı; bunların gelecekteki Qt ekranları için yeniden doğrulama gerekir. Uygulama şimdi yalnız sekiz alanın kabuğunu ve kullanılabilirlik bilgisini içerir.

Gerçek Qt küçük/büyük açık/koyu ekranları ve %125/150/200 yazı kontrolü üretildi. %200 dar başlık/yardım aynı satırda sığmıyordu: ayrı satıra geçiş + metin kırılması uygulandı. Dar Drawer interactive=false iken Escape kapanmıyordu: interaktif Drawer, dragMargin0 ve closePolicy ile düzeltildi. QML focus halkası ve kaydırmada odağın görünür tutulması kontrol edildi. Masaüstü Wayland screenshot’ları gerçekten incelendi; kullanıcı/ekran okuyucu testi yapılmadı.

Beş resmî referans ekranı bu oturumda yorumlanabilir biçimde görüldü; UI-REF-VIS kapandı ([UI_REFERENCES](UI_REFERENCES.md)). Son kanıt [PHASE02](evidence/PHASE02.md), ölçü/klavye kayıtları ve screenshot’lar aynı dizindedir. İlgili gelecek fazların gerçek iş akışı hâlâ henüz mevcut değil.
