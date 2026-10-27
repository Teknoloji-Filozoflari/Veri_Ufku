# Veri_Ufku — ortak tasarım sistemi v0.2

2026-10-25 son kullanıcı kabuğu: yazı ölçeği sabit 1. Açık yüzey beyaz, ana eylem tek mavi (`Theme.action`). Kategori rengi yalnız modül rayı ikonunda. Koyu tema durur. Aşama şeridi ve yazı boyutu seçeneği varsayılan ekranda yoktur.

Faz00 önerisi Faz02 QML kabuğunda, ardından Faz04–13 veri/işlem/grafik/rapor ekranlarında uygulanmıştır. Ortak UiLabel düz metin gösterir: kullanıcı başlığı, dosya adı ve hücre metni HTML/resim kaynağı olarak yorumlanmaz. [Brief](UI_DESIGN_BRIEF.md), [UX](UX.md), [referans kısıtları](UI_REFERENCES.md). Üç tasarım aynı sistemde [SVG prototip](prototypes/triptych.svg).

## Başlangıç yolculuğu — güncel düzen

UI-JOURNEY-01: başlangıçta ana sayfa numaralı düz yol haritasını öne alır;
proje oluştur/aç/kaydet haritanın sonundadır. Öğren aynı aşama kimliklerini/sırasını
ve kart düzenini kullanır; açıklama ve terimler burada açılır. Çalışma ekranlarında
soru/işlem/çıktı/örnek; gelişmişte doğrudan teknik formlar. Seviye tercihi güvenlik
ve compute budget sınırlarını değiştirmez. [Ekran ve kanıt](evidence/UI_JOURNEY.md).

## Ortak yapı ve tokenlar — 2026-10-17

Tek kaynak `src/veri_ufku/ui/qml/Theme.qml`. Açık/koyu tema Preferences ile saklanır. Çalışan yazı ölçeği 1’dir; dosyada kalan %125/%150/%200 uygulanmaz. OS DPI ayrıdır. Aşağıdaki eski revizyon bölümleri tarihsel kullanıcı talepleri/kanıtlarıdır.

Üst şerit proje/veri bağlamı, aç, kaydet, arama, tema ve dil taşır. Sol ray altı modül (Veri, Grafik, İncele, Hazırla, Model, Rapor); dar pencerede simge rayı. Ortada tablo, sağda seçilen aracın formu. Alt satır satır/sütun, sürüm, kayıt ve iş durumunu gösterir. Yardım kapanınca odak geri döner. Ağır formlar ilk ziyarette yüklenir. Öğren varsayılan rayda yoktur.

Aşağıdaki renk tablosu 2026-10-17 yenilemesinin kaydıdır. Güncel açık yüzey, mavi ana eylem ve koyu tema değerleri `Theme.qml` içindedir.

| Token | Koyu | Açık |
|---|---|---|
| background / surface | #11161F / #1B2330 | #F3F5F8 / #FFFFFF |
| chrome | #171E29 | #FFFFFF |
| text / secondary | #F4F1EC / #BAC3CF | #182230 / #40516A |
| accent / accentText | #F6A35D / #24170E | #9B4200 / #FFFFFF |
| border | #344155 | #CBD3DF |
| alternateRow | #1E2938 | #F4F7FA |

Turuncu ana dosya/kayıt, lavanta hazırlama/model, mint öğrenme, cyan veri/inceleme
rolleri korunur. Kontrol sınırı `controlBorder`, dekoratif ayırıcı `border` kullanır;
renk tek başına durum taşımaz. Paketli DejaVu Sans:14px gövde,12px yardımcı,
18px bölüm,24px başlık × kullanıcı ölçeği;4/8/12/16/24/32px aralık,6px radius,
en az40px kontrol yüksekliği. Kontrollerde klavye odak sınırı ve accessible adlar.

Veri tablosu mevcut200kayıtlık model/view sayfasıdır; yeniden boyutlanabilir
başlık, değişen satır yüzeyi, seçili satır ve gerçek null için `∅ eksik` rolü.
Metin `∅` null sayılmaz. Ctrl+C yalnız yüklenmiş seçimin görüntülenen değerlerini
ve RowId'lerini JSON olarak kopyalar; tam hassasiyetli veri exportu değildir.
Grafik bilimsel renkleri/ölçekleri mevcut tariften gelir; kabuk teması sayısal
sonucu veya export paletini sessizce değiştirmez. Responsive tuval görüntünün
en-boy oranını korur; görüntü dışında başlatılan seçim reddedilir.

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

## UX-Veri (2026-10-27)

Veri üst şeridi yalnız `Veri_Ufku` + bağlam + çerçeveli Geri·Kaydet (arama/ayar/kapat gizli). Boş kart seyrek kahraman: «Verinle çalışmaya başla» + Dosya seç · Verilerim · Örnek; proje adı / klasör+Gözat / kaynak; ipucu/kart-footer/ikinci kaynak Gözat gizli (objectName kalır). Önizleme/gelişmiş/İçe aktar yalnız kaynak seçilince. Drop yok. Yüklü tablo salt okunur; başlık ad + tür·rol (`ColumnHeaderMenu`); satır seçim şeridi yalnız seçimde. Alt durum: `N satır · M sütun · sürüm …` (sayfa aralığı / «Sayfa en fazla 200» Veri tablosunda zayıf/gizli). Sağ «Veri»+sağlık, 2×5 kısa çip (`cyanSurface` seçili), Geri + geniş İçe aktar. Dock kabuk başlığı/Kapat gizli. Theme dosyası yok.

## UX-İncele tarama (2026-10-27)

İncele (`moduleKey=incele`, `dataPane=quality`): merkezde `InspectScanStrip` + salt okunur `DatasetPanel` (başlıkta `N eksik` rozeti); sağda `InspectWorkspacePanel` — «İncele»+sağlık, tek sütun 5 çip, altta Taramayı çalıştır / İptal / Raporu proje taslağına ekle. Describe/değerler/profil Veri accordion’dan çıktı; blok 1–2’de. Kalite puanı yok; örneklem «tam veri» yazılmaz. Bulgu → `operations.inspectDraft` (bellek; sürüm yok) → Hazırla önseçim + köken. `QualityPanel` blok 4’te yeniden kullanılır. Özel tür: Loader. Theme dosyası yok.

## UX-Görselleştir keşif (2026-10-27)

Görselleştir (`moduleKey=gorsellestir`, `chartTool=0`): merkez `VisualizeWorkspace` — `Grafik|Çıktı|Tablo`; 6 amaç kartı; tuval + kapsam rozeti; Python popup varsayılan kapalı. Sağ `ChartPanel` — Değişkenler X/Y/Grup/Facet, ayarlar, debounce `create` (Grafiği oluştur yok). Çıktı: `chart_explain` + özet; Tablo: aynı `DatasetPanel`. İleri grafikler yalnız `advanced`. Ağ/metin ayrı panel; sahte çizim yok. Theme dosyası yok.

## UX-Hazırla önizleme A (2026-10-27)

Hazırla (`moduleKey=hazirla`, `prepareTool=0`): merkez `PrepareWorkspace` — etki rozetleri, salt okunur sürüm zinciri, önce/sonra `OperationTable`, alt İptal·Önizle·Uygula. Sağ `PrepareCatalogPanel` — Gelen taslaklar (`inspectDraft`) + tek sütun 10 blok (sütun temizliği…uygulama); parametre gövdesi mevcut `CleaningOptions`/`TransformationOptions`/rename-drop-filter. Mod 1 varsayılan; Mod 2 yalnız LEARNED için UI uyarısı (train-only motor yok; `prepare_scope_mode=mod2` apply notu). Yeni cleaning API yok. Theme dosyası yok.

## UX-İstatistik soru odaklı A (2026-10-27)

İstatistik (`moduleKey=istatistik`, `examineTool=0`): merkez `StatisticsWorkspace` — öneri kartı (`statistics.advice`), sonuç özeti (n/p/etki/CI), grafik alanı (mevcut charts), varsayım onayı, alt Sıfırla·Önizle·Uygula ve kaydet. Sağ `StatisticsCatalogPanel` — 8 çip; `StatisticsPanel` catalogMode + debounce önkontrol; assumptions→tam create. Blok 1/8 dürüst «desteklenmiyor»; 6→Modeller, 7→Yeniden örnekleme köprüsü. Yeni motor/Bootstrap yok. Theme dosyası yok.

## UX-Model yerleşim A (2026-10-27)

Model (`moduleKey=model`, `modelInstalled`, dataset var): merkez `ModelWorkspace` — Özet|Katsayılar|Artıklar|Tanılama; rozetler (katsayı/SE/t|z/p/VIF/AIC·BIC); eğitim/test n şeridi (held-out skor uydurulmaz); diagnostic Image. Sağ `ModelCatalogPanel` — 10 çip (OLS…AIC/BIC), Y/X/param, Sıfırla·Eğit ve kaydet → `statistics` path `models` + `analysis_store`. ML `modelPath` Layout A’da gizli. İstatistik `StatisticalModelsPanel` korunur. Theme dosyası yok.

## UX-Raporla yerleşim A (2026-10-27)

Raporla (`moduleKey=raporla`, `reportTool=0`, proje açık): merkez `ReportWorkspace` — Önizleme|HTML|PDF; freshness (STALE); LIMITATIONS bandı. Sağ `ReportCatalogPanel` — 8 çip (özet…Ekler), başlık/protokol, oluştur+inceleme, HTML/PDF dışa aktar → `reportBuilder.composeLayout` / `run` / `exportReport`. Legacy `ReportBuilderPanel` Layout A’da gizli (Loader kalır). Yeni motor/DOCX/LLM yok. Theme dosyası yok.

Faz06 StructuredOptions mevcut ColumnLayout/Theme tokenlarını ve kapsama bağlı alan görünürlüğünü kullanır. Yeni formatlar aynı Veri ekranının dosya/önizleme/kaydet akışında; native ayarlarda Türkçe davranış etiketleri, kendi kaynak ve sınırlı örnek açıklamaları vardır. Başsız dar/geniş render kanıtı [Faz06](evidence/PHASE06.md#e06-gui).

## Faz07 katkısı

Faz07: mevcut Theme/UiButton/layout tokenlarıyla Veri tablosu sekmesi; TableView delegate reuse, sabit200 sayfa, bounded frekans ve ayrı sütun detayı. 1366 açık/720 koyu scroll tabloları [kanıt](evidence/PHASE07.md).

## Faz08 katkısı

QualityPanel mevcut Theme/UiCombo/UiButton/StateNotice tokenlarını ve dar ekranda tek sütun düzenini kullanır. Bulgular düz metin ve açıklamalı karttır; renk tek başına durum taşımaz. Teknik işlem/RowId kimlikleri gelişmiş görünümde açılır. [Karar](adr/011-quality-phase08.md), [kanıt](evidence/PHASE08.md).

## Faz10 katkısı

Hazırla temizlik formunda yalnız seçili yöntemin seçenekleri görünür. Tam etki ve uyarılar saklanmaz; önce/sonra tabloları ve geçmiş ayrıntıları isteğe bağlı açılır. Geri al/yinele daima erişilebilir. Faz02 ortak Theme/UiCombo/UiButton tokenları korunur; dar/%200 ekranda kaydırma gerekir. [Karar](adr/013-cleaning-phase10.md), [kanıt](evidence/PHASE10.md).


## Faz11 katkısı

Faz11 TransformationOptions ortak Theme/UiCombo/UiButton ve seçime bağlı form kullanır. Join üç aşamalı, append eşleme onaylı; ham JSON kullanıcıya gösterilmez. Faz02 ortak tasarım korunur; yeni referans marka varlığı alınmadı. Başsız dar/büyük, koyu/açık render kanıtı ayrıca kaydedilir; gerçek kullanıcı masaüstü kabulü açık. [Karar](adr/014-transformations-phase11.md), [kanıt](evidence/PHASE11.md).


## Faz12 grafik katkısı

ChartPanel mevcut Theme/UiCombo/UiButton/StateNotice ve kaydırılan çalışma alanını kullanır. Parametre ve referans ayrıntıları katlanabilir. Gruplar renk+scatter şekli/çizgi deseni ile ayrılır; korelasyon -1…1 ortak diverging skala ve r/n metni taşır. Selection koyu halka + RowId/sayı açıklaması; null/örnekleme/Diğer bilgi metni salt renge bağlı değildir. Görüntü PreserveAspectFit; Qt input letterbox ve çizim piksel transform'u kullanır.100–200 yazı,1366/720 genişlik gerçek headless PNG incelendi; dar/%200 kaydırma gerektirir. Fiziksel HiDPI, ekran okuyucu ve yeni native masaüstü ayrı açık. [Karar](adr/015-charts-phase12.md).

Faz13: GuidePanel ve ReportPanel mevcut UiButton/UiCombo/Theme/StateNotice ve dikey kaydırma düzenini kullanır. Rapor fontu aynı paket DejaVu Sans; HTML sabit yerel CSS ile veri tablosu/başlık/uyarı, PDF A4 sayfa ayrımı. Rehber dersi zorunlu kılmaz; çıktı makbuzu önce sade sürüm/sayı/yol, isteğe bağlı teknik ayrıntı gösterir.

## Sağ üst simge kontrolleri — kullanıcı düzeltmesi

Tema/görünüm metinleri ve üç seçici kaldırıldı. Tek üst satırın sağında filiz (başlangıç), sürgüler (gelişmiş), ay/güneş (tema geçişi) bulunur. Seçili seviye iki piksel vurgu kenarlığı taşır. Simgeler özgün QML Canvas çizimidir; uzak kaynak veya ikon fontu gerekmez. Düğmeler 40×40px, Tab/Space ile erişilebilir; açıklamaları tooltip ve Accessible.name ile sağlanır. Eski şema1 yazı tercihleri uygulanmaz; tema/seviye korunur, ilk açık tercih değişiminde yalnız bu iki alanı taşıyan şema2 atomik kaydedilir. Yukarıdaki Faz02 ölçek kanıtı tarihsel teslim kaydıdır; yeni davranış [UI_HEADER](evidence/UI_HEADER.md).

Sol menü görsel düzeltmesi: sekiz özgün ortak çizgi simgesi,184px menü,44px sola hizalı düğmeler; planlanan alan açıklaması kaldırıldı. [Gerçek Qt kanıtı](evidence/UI_NAVIGATION.md).

## Koyu tema — sıcak turuncu revizyon

Kullanıcının görsel düzenleme talimatıyla antrasit zemin (#141820), koyu üst/sol kabuk (#191F29), kart (#202733), yükseltilmiş düğme (#293342) ve gömülü alan (#171E28) ayrılır. Ana eylem/odak/seçim kayısı turuncusu #F6A35D; seçim yüzeyi #3A2B23. Hover/pressed farklı tonlar; pasif düğme metni soluktur. Menü simgeleri veri için mavi/turkuaz, model için lavanta, rapor için altın, öğrenme için yeşil; etiketler ve simge biçimleri korunur. Kontrol kenarlığı #718096, dekoratif panel kenarlığı #3E4A5B. Koyu köşe8px, açık6px. Veri sekmelerinde açık gri varsayılan kaldırıldı; turuncu alt çizgi ve koyu yüzeyler ortak UiTabButton içinde. Açık paletin ana renkleri korunur; aynı sekme bileşeni açık palete uyarlanır. Yazı boyutu sabit. [Gerçek ekran/kontrast kanıtı](evidence/UI_DARK_THEME.md).

Son kullanıcı talimatı: açık/sistem paleti, tema değiştirme API/düğmesi ve ay/güneş simgeleri kaldırıldı. Tema tokenları sabit koyu renklerdir; şema3 yalnız seviye saklar, eski şema1/2 tema/ölçek değerlerini uygulamadan okuyabilir. Önceki açık/koyu kayıtları tarihsel kanıttır. [Güncel kanıt](evidence/UI_DARK_ONLY.md).

## Çok renkli koyu tema — güncel rol sistemi

Kullanıcı turuncu/turkuaz ağırlığını azaltıp mor ve yeşilin bütün temaya katılmasını istedi. Sabit koyu zemin #151722, kabuk #1B1E2A, kart #232735, düğme #2C3243 ve alan #191D2A hafif mor/antrasit tabanlıdır. Turuncu #F6A35D başlangıç/ana dosya-kayıt; lavanta #C3A6EF Hazırla/Karşılaştır/Model; mint #91D7B2 Öğren ve bütün bağlamsal yardım; turkuaz #94C9DF Veri/İncele. Mor seçim #30273F, yeşil seçim/öğren kartı #20372F, turkuaz seçim #223541.

UiButton toneColor/toneSurface/hover/pressed ve UiNavigationButton tone ortak Theme fonksiyonlarıdır. Seçili menü/metin/sol işaret/odak alan rengini kullanır. Gelişmiş seviye simgesi mor; başlıklar alan rengiyle, normal metin nötr beyazla gösterilir. Öğren kartları ve sağ yardım yüzeyi yeşil; metin, kritik uyarı ve kapama davranışı korunur. Veri sekmeleri ve grafik oluşturma turkuaz; işlem önizle/uygula mor. Yardım düğmeleri yeşil; renk tek başına anlam taşımaz, başlık/simge/işaret korunur. Pasif kontroller nötr. Ana/örnek pencere ve seçiciler ilgili vurguya uyar.

Yalnız koyu tema ve sabit yazı boyutu geçerlidir; tema düğmesi yoktur. Önceki tema teslim kayıtları tarihsel kanıttır. [Güncel ekranlar/kontrast/gerçek kontroller](evidence/UI_MULTICOLOR.md).

## Seçilen logo — Veri Bağları

Kullanıcı v2/02 Veri Bağları logosunu seçti. Turuncu/mor/mint/turkuaz bağlı düğümler,
paketli şeffaf PNG olarak üst başlıkta ve örnek penceresinde 36px kullanılır.
Görünen Veri_Ufku adı yanında kalır; logo dekoratiftir, odak durağı değildir.
Aynı kaynak Linux pencere/uygulama menüsü simgesi ve yerel HTML/PDF rapor markasıdır.
Boyutlar 16–512px; kaynak taslak korunur. [Gerçek uygulama ve kanıt](evidence/UI_BRANDING.md).


Faz14: StatisticsPanel dar alanda tek sütunlu form, katlanabilir ayarlar, taşmayı önleyen UiCheckBox metin sarması ve okunabilir sonuç akışı kullanır. Sayısal değer alt sınırda sıfıra yuvarlandığında kesinlik iddiası kurulmaz. p-değeri, etki ve CI aynı sonuç grubundadır; uyarı renkleri varsayım/dışlama açıklamalarıyla birlikte kullanılır. [Kanıt](evidence/PHASE14.md).

Faz15 PreparationPanel mevcut UiLabel/UiCombo/UiCheckBox/UiButton/StateNotice/Theme bileşenlerini kullanır. Başlangıçta amaç/alan/plan formu, sonuçta gerekçeli risk ve geçmiş; uzun profil/kolon eşlemesi/adım ayrıntısı isteğe bağlı açılır. 720/1366 offscreen render [Faz15 kanıtında](evidence/PHASE15.md); gerçek insan erişilebilirlik testi yerine geçmez.

Kullanıcının2026-10-08 minimal tasarım talimatıyla UiButton doğal içerik genişliği ve340px üst sınır,40px minimum yükseklik/8px iç/14px yatay boşluk kullanır; Flow yerleşimleri dar ekrana sarılır. Başlangıçta büyük eylem kartları ve genel açıklamalar kaldırıldı; Proje/ayrıntılar/son isimler önde. Temalı FolderPicker720/1366 ve klavye korunur. [Kanıt](evidence/UI_HOME_COMPACT.md).

## Faz16

ValidationPanel ortak Theme/UiLabel/UiCombo/UiButton/UiCheckBox/StateNotice ile tek sütun, katlanabilir form, sade fit boyutları/skor kapsamı ve isteğe bağlı teknik kimlikleri sunar. Aynı grup+zaman/varlık kısıtı çakışması açık engel; test tekrar kullanımı metinle uyarılır.720/1366 gerçek sonuç ekranı [PHASE16](evidence/PHASE16.md); insan erişilebilirlik kabulü değildir.

2026-10-08 kullanıcı arayüz düzenlemesi: Başlangıç yardım ve ara rehber/dosya/örnek satırları kaldırıldı; Veri bilimi yol haritası başlığı; üst gelişmiş yanında uygulama kapatma simgesi; son projeler yatay sarılan düğmeler. Bütün tik kutuları ortak oval UiCheckBox; tek FolderPicker geri/üst simgeleri ve üzerine yazmayan yeni klasör oluşturma. Örnek projeler Öğren ekranında aynı seçiciye bağlı. Faz/olgunluk/kapsam değişmedi. [Gerçek kontrol](evidence/UI_HOME_REFINEMENT.md).

2026-10-08 kullanıcı yol haritası düzenlemesi: Veri Bilimi Yol Haritası on numaralı kıvrılan aşama, açılabilir alt başlıklar ve yalnız etkileşim/ilk görünüş animasyonlarıyla sunulur. Genişte iki yana, darda tek sütuna yerleşir; alt yollar mevcut ekranlara bağlı, planlanan araçlar pasiftir. İçerik20/home.roadmap çevrimdışı yardım mevcut home makalesinde. Yeni faz veya analitik capability başlamadı. [Gerçek kayıt](evidence/UI_SCIENCE_ROADMAP.md).

Öğren konu ağacı (2026-10-09): mint aşama düğmeleri, içeriden girintili alt başlık kartları ve konu bağlantıları. Okuma penceresi en çok850 ölçekli piksel genişlikte, pencere sınırlarına uyarlanır; başlık ve kapatma üstte, düz metin alt başlıklar kaydırılabilir alandadır.

Öğren merdiveni (2026-10-09): mint/cyan/violet/warm aşama kartları,01..10 yuvarlak numaralar ve bağlantı çizgisi. Genişte üç kademeli girinti, darda tek hizalı aşamalar; alt başlıklar küçük kademelerle açılır. Aşama240ms/alt başlık200ms yükseklik animasyonu; ok180ms dönüş. Klavye odağı görünür alana taşınır; konu açıklaması mevcut okuma penceresinde açılır.

2026-10-09 — Öğren için ayrı merdiven çizimi yerine ortak ScienceRoadmap kullanılır; LearningTrail yalnız öğrenme modu sarmalayıcısıdır. Kıvrılan bağlantı, numaralı düğümler, genişte dönüşümlü sağ/sol kartlar ve darda tek sütun iki ekranda aynıdır. Filtrede aşama numarası özgün yol haritasındaki numaradır. Başlangıç başlık/ok ayrı eylemler; Öğren başlık açma eylemidir. Alt konu200ms, aşama240ms açılır; kaynakların kapalı varsayılanı korunur.


2026-10-09 Veri içeriği: ortak Frame/Theme/UiLabel/UiButton ile üst dosya kartı, sarılan Veri yol haritası eylemleri, turkuaz Veri içeriği kartı. Sütun sözlüğü260px sınırında sanal ListView; açıklamalar düz metin ve sarılır. Tam veri bilgisi filtreli tablo kapsamından ayrı etiketlenir. [Ekran kanıtı](evidence/UI_DATA_CONTENT.md).

## Faz25 denetimi

Varsayılan koyu görünüm korunur; Ctrl+, / Görünüm ve dil üzerinden isteğe
bağlı açık palet ve %100–200 yazı vardır. Ortak metin/uyarı/hata/eylem
kontrast çiftleri, büyük yazıda uzun navigasyon başlığının sarılması,
Tab çıkışı ve görünür odak denetlendi. [Sınırlar](evidence/PHASE25.md).


2026-10-10 Veri başlıkları: Theme.surface/cyanSurface üzerinde 01–07 numara rozeti, başlık, kısa açıklama ve +/− işareti; seçili kartın solunda vurgu, klavye odağında iki piksel kenarlık. Ortak Theme tipografi/boşluk/renk tokenları korunur. Başlıklar Button klavye ve erişilebilirlik davranışını taşır; içerik kartın altında açılır. Sade import ayrıntıları Gelişmiş ile açılır; küçük önizleme yüksekliği kayıt sayısına uyarlanır.


2026-10-10 Veri profili üç özet alanı ve turkuaz tablo başlığı kullanır; iki sütun genişliğe yayılır. Sütun değerlerinde Değer/Tekrar sayısı başlığı,48px minimum satır, değişen yüzey rengi, hover ve sayısal rozet; uzun metin sarılır. Tema/ölçek/klavye ve sayfalama korunur. [Gerçek görüntüler](evidence/UI_DATA_REFINEMENT.md).

2026-10-10: Veri profili beş sütunlu tablo:250/290/170px ölçekli genişlikler ve yatay kaydırma; fiziksel türden farklı içerik türünde kayıt: String açıklaması görünür. Üç özet kartı korunur. [Kanıt](evidence/UI_PROFILE_TYPES.md).

2026-10-10 son kullanıcı gösterim isteği: profil tablosu ve üst tür özetinde teknik tür adları (Int64/String/Decimal…) kullanılır. İçerik türü hücrede tek başına; farklı fiziksel kayıt türü tooltip içinde açıklanır. Veri dönüşümü yapılmaz. [Güncel kanıt](evidence/UI_PROFILE_TYPE_LABELS.md).

2026-10-10 son saklama talebi önceki içerik türü gösterimini geçersiz kıldı: profil yalnız gerçek physical_type gösterir; aktarımda Int64/Decimal fiziksel olarak saklanır. Titanic mevcut aktif sürümü kullanıcı izniyle mevcut convert operasyonu üzerinden dönüştürüldü; kaynak, satır kimlikleri ve geri alma geçmişi korunur. [Gerçek kayıt](evidence/UI_ACTUAL_STORAGE.md).

2026-10-10 profil tür özeti her fiziksel türü ayrı satırda sayı ve ilgili sütun adlarıyla gösterir: Int64:4 — sütunlar. Uzun adlar sarılır, plain text korunur. Kullanıcının data_info.png referansı gerçekten incelendi. [Kanıt](evidence/UI_PROFILE_TYPE_COLUMNS.md).

2026-10-10 kullanıcı kısa not isteği: Anlam ve notlar ayrı Veri başlığı olmaktan çıktı, profil tablosunun altına sütun seçimi/kısa açıklama/Notu kaydet alanı taşındı. Her sütunun taslağı seçimler arasında korunur; açık kayıt projeyi kalıcı kaydeder. applyDescription mevcut rol/birim/sıra/analiz birimi ve confirmed durumunu korur; yeni not role önerisini onaylamaz. Analitik profil onaylanmamış rolün yerine mevcut öneri politikasını kullanır. Kaynak/snapshot/RowId değişmez. [Kanıt](evidence/UI_PROFILE_NOTES.md).

2026-10-10 sade veri akışı: import Gelişmiş alanı tüm seviye tercihlerinde ve yeniden girişte kapalıdır; kullanıcı tıklayarak açar. Profil not girişinin üstünde yalnız açıklaması olan sütunlar ad/açıklama biçiminde kompakt, plain-text ve220px bounded listede görünür. Verini tanı altında inventory/describe/unique/sütun profili GUI çağrıları sample=false; ilk10.000 seçicileri kaldırıldı, tam veri hesabı ve200 değer görüntü sayfası ayrı tutulur. [Kanıt](evidence/UI_COMPACT_NOTES_FULL_DATA.md).
