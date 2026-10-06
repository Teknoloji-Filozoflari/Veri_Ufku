# Veri_Ufku — ortak tasarım sistemi v0.2

Faz00 önerisi Faz02 QML kabuğunda uygulanmıştır; veri/analitik ekranları gelecek fazların planıdır. [Brief](UI_DESIGN_BRIEF.md), [UX](UX.md), [referans kısıtları](UI_REFERENCES.md). Üç tasarım aynı sistemde [SVG prototip](prototypes/triptych.svg).

## Yapı ve tokenlar

Üst şerit: Veri_Ufku / proje / kaynak ve sürüm / hesap kapsamı. Sol sabit amaç navigasyonu; merkez tab/seçili işlem, sağ 320px bağlam paneli. Alt durum şeridi job/iptal/kayıt durumu. 1366×900 doğrulama, minimum720×560; 1100×yazı ölçeği altında sağ panel overlay drawer; ana işi kapatmaz. Gelecek fazların nav öğeleri çıkarılır veya açık “henüz mevcut değil”; yanıltıcı CTA yok.

| Token | Açık | Koyu |
|---|---|---|
| background / surface | #F4F6F8 / #FFFFFF | #111827 / #1F2937 |
| text / secondary | #17212B / #475569 | #F3F4F6 / #CBD5E1 |
| accent / on-accent | #245C74 / #FFFFFF | #8CC9E0 / #111827 |
| border / focus | #CBD5E1 / #245C74 | #64748B / #8CC9E0 |
| warning text / surface | #713F12 / #FEF3C7 | #FDE68A / #422006 |

Tek accent; renk tek başına durum taşımaz. Success/error metin+ikonla, grafik palette contrast/colorblind test Faz12. Hedef normal metin≥4.5:1, büyük metin/odak≥3:1. Sistem teması Qt style hints ile; kullanıcı tercihi light/dark/system, veri state'inden bağımsız.

Tipografi yerel sistem sans, paket font adayı Noto Sans (lisans/paket doğrulaması açık); 14px gövde, 12px yardımcı metin, 18px bölüm ve 24px sayfa başlığı; font scale kullanıcı/OS ile artar. 4/8/12/16/24/32px boşluk; 6px radius; 40px asgari kontrol yüksekliği; tablolarda 32px satır, büyük text scale'de otomatik büyüme. Hover tek erişim yolu değil.

## Etkileşim sözleşmesi

Her ekranda en fazla bir belirgin ana eylem: önizle / içe aktar / uygula / çalıştır / kaydet. Cancel ve geri secondary. Düğme disabled nedenini erişilebilir açıklama verir. Formlarda label üstte, hata alan yanında; ileri parametreler aranabilir accordion; kritik varsayım katlanmaz.

Tablo read-only; sütun seçimi, satır seçimi, column detail. Filtre ve sıralama işleme otomatik dönüşmez. “Bu ne işe yarar?”, “Nasıl yorumlarım?”, “Örnekle öğren” ilgili işlem/sonuç yanında aynı yerde; yardım drawer kapatılınca parametre/scroll/job/selection korunur. Pop-up yalnız dosya seçim ve veri kaybı riski gibi kararlar; ders zorunlu değil.

Preview etki sayısı, kayıp/yeni null, önce/sonra aynı RowId. Uygula publication sonrası aktif sürüm. Save durumu açık “kaydediliyor/kaydedildi/hata”; dirty state görünür. Başlangıç ve uzman sunum aynı service/config/result referansları, ayrı dataset kopyası değil. Uzman görünüm fold/seed/method/scope/diagnostics açar.

## Erişilebilirlik doğrulama planı

Tab/ShiftTab sıra görsel akışla uyumlu; 2px focus ring+offset, Escape yardım drawer kapatır ve açan kontrole odak döner; Ctrl+O dosya, Ctrl+S proje, Ctrl+Z yalnız işlem undo context, kontrol içinde metin undo ayrılır. Ekran okuyucu accessible names/roles, sayı ve graph text summary, tooltips keyboard ile. Qt erişilebilirlik gerçek assistive teknolojiyle test edilir; başsız Qt load bunu doğrulamaz.

100/125/150/200% scale; 1366×768 ve 1024 genişlik; light/dark/system; uzun Türkçe ve çeviri alanları. Kontrast token hesabı yalnız renk çiftleri; çizilmiş tüm kontrollerin erişilebilirliği değil. Faz02 ortak tasarım uygulanmadan önce üç temsilî ekran kontrolü, Faz25 gerçek kullanıcı denetimi.

## Faz02 uygulama ve kanıt

Tek token kaynağı `src/veri_ufku/ui/qml/Theme.qml`; Basic Controls paleti, UiButton/UiCombo/StateNotice/InfoPanel aynı renkleri kullanır. Hata açık #991B1B/#FEF2F2, koyu #FECACA/#450A0A. Sistem şeması Qt Application.styleHints, bilinmiyorsa SystemPalette; canlı uygulama paleti fallback testi var. Sidebar en az150px ve yazı büyüyünce genişler; merkez ve sidebar ayrı dikey kayar. %100/125/150/200 yerel yazı tercihi kaydedilir; OS DPI bağımsızdır. Gövde max(14,sistem font pikseli)×tercih, yardımcı12×tercih; controls max(40,gövde+24).

F1 yardım, Escape panel kapatma/odak dönüşü; Ctrl+1..8 nav, nav Up/Down ve Space, Tab/ShiftTab standart Qt zinciri. Odaklanan düğme ilgili scroll alanına alınır. Gelecek eylemler disabled + görünür neden, gelecek nav ekranları kullanılabilirlik bilgisi. Boş/yükleniyor/hata/iptal StateNotice ile sembol/metin taşır. [Faz02](evidence/PHASE02.md), [kontrast](evidence/phase02-contrast.json). Ekran okuyucu ve gerçek OS tema değiştirme ayrı doğrulanmadı; otomatik Qt palette notification kontrolü fiziksel OS davranışı kanıtı değildir.
