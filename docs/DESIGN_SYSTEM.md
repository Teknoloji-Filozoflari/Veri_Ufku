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

## Faz03 öğrenme bileşenleri

LearningCenter, ArticleView ve örnek öğrenme penceresi aynı Theme tokenlarını kullanır. Arama ve derinlik seçicisinde görünür odak; ortak FocusScroll arama/combobox/düğmeyi ilgili kaydırmalı alana alır. Kritik uyarı ! Dikkat + metin + warning tokenlarıyla, yalnız renge bağlı olmadan her derinlikte görünür. Yerel kayıt açık/kapalı ve okundu/yer imi durumları metin+sembolle açıklanır. [Gerçek ekranlar ve testler](evidence/PHASE03.md).

## Faz04 proje kartı

ProjectPanel mevcut Frame/UiButton/Theme tokenlarını kullanır; Flow düğmeleri mevcut genişliğe sarılır, ad/seed alanlarının görünür etiketleri vardır. Kart yüksekliği içerik implicitHeight hesabına bağlıdır, sonraki içerikle üst üste gelmez. Proje/kaynak/kurtarma F1 bağları ortak çevrimdışı katalogdadır. Geniş açık ve dar koyu %200 başsız render [Faz04 kaydı](evidence/PHASE04.md); gerçek masaüstü ve assistive teknoloji kontrolü değildir.

## Faz05 uygulama bağı

Faz05 ImportPanel Theme tokenları ve UiButton, CSV TableView/QAbstractTableModel kullanır. Dar alanda ayar formu tek sütundur, başlık/düğmeler sarılır; sütun türleri sanal ListView ve preview hücreleri yalnız görünür TableView delegate ile üretilir. Kesilmiş hücre değerleri hover tooltip ile tam gösterilir. Aynı yardım/focus scroll sözleşmesi korunur; gerçek render [Faz05](evidence/PHASE05.md), native/assistive teknoloji kabulü değildir.

Faz06 StructuredOptions mevcut ColumnLayout/Theme tokenlarını ve kapsama bağlı alan görünürlüğünü kullanır. Yeni formatlar aynı Veri ekranının dosya/önizleme/kaydet akışında; native ayarlarda Türkçe davranış etiketleri, kendi kaynak ve sınırlı örnek açıklamaları vardır. Başsız dar/geniş render kanıtı [Faz06](evidence/PHASE06.md#e06-gui).

## Faz07 katkısı

Faz07: mevcut Theme/UiButton/layout tokenlarıyla Veri tablosu sekmesi; TableView delegate reuse, sabit200 sayfa, bounded frekans ve ayrı sütun detayı. 1366 açık/720 koyu scroll tabloları [kanıt](evidence/PHASE07.md).

## Faz08 katkısı

QualityPanel mevcut Theme/UiCombo/UiButton/StateNotice tokenlarını ve dar ekranda tek sütun düzenini kullanır. Bulgular düz metin ve açıklamalı karttır; renk tek başına durum taşımaz. Teknik işlem/RowId kimlikleri gelişmiş görünümde açılır. [Karar](adr/011-quality-phase08.md), [kanıt](evidence/PHASE08.md).

## Faz10 katkısı

Hazırla temizlik formunda yalnız seçili yöntemin seçenekleri görünür. Tam etki ve uyarılar saklanmaz; önce/sonra tabloları ve geçmiş ayrıntıları isteğe bağlı açılır. Geri al/yinele daima erişilebilir. Faz02 ortak Theme/UiCombo/UiButton tokenları korunur; dar/%200 ekranda kaydırma gerekir. [Karar](adr/013-cleaning-phase10.md), [kanıt](evidence/PHASE10.md).


## Faz11 katkısı

Faz11 TransformationOptions ortak Theme/UiCombo/UiButton ve seçime bağlı form kullanır. Join üç aşamalı, append eşleme onaylı; ham JSON kullanıcıya gösterilmez. Faz02 ortak tasarım korunur; yeni referans marka varlığı alınmadı. Başsız dar/büyük, koyu/açık render kanıtı ayrıca kaydedilir; gerçek kullanıcı masaüstü kabulü açık. [Karar](adr/014-transformations-phase11.md), [kanıt](evidence/PHASE11.md).
