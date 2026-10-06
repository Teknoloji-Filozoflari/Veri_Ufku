# Veri_Ufku — resmî tasarım referansları

Tarih: 2026-10-06. Referanslar kullanım ilkeleri içindir; ekran/marka/ikon kopyası yapılmadı. [Brief](UI_DESIGN_BRIEF.md), [tasarım sistemi](DESIGN_SYSTEM.md), [ekran planı](UX.md).

## İnceleme yöntemi ve sınır

Beş uygulamanın resmî sayfa metinleri ve ekran akışı açıklamaları okundu. Resmî görsel bağlantılarına erişim ve PDF screenshot denemesi yapıldı; bu oturumda araç görselleri yorumlanabilir image payload olarak göstermedi. Faz00 kaydında **piksel düzeyinde hiçbir referans ekranı görsel olarak doğrulanmış sayılmıyor**; Faz02’de aşağıdaki yeni görsel kanıtla bu kapı kapandı. Aşağıdaki “incelenen” alanı ekranın resmî belge açıklaması anlamındadır. Uygulamalar çalıştırılmadı, videolar izlenmedi; hız, odak, klavye, tema kontrastı ve tüm gelişmiş seçenek davranışları tahmin edilmedi. Görsel referans kontrolü UI-REF-VIS kaydıyla açık, Faz02 tasarımı yaymadan önce kapanmalıdır.

| Uygulama / erişilen resmî kaynak | Gerçekten okunan ekran/akış açıklaması | Seçilen ilke ve Veri_Ufku kararı |
|---|---|---|
| Orange [File](https://orange3.readthedocs.io/projects/orange-visual-programming/en/latest/widgets/data/file.html) | File giriş bilgileri/rol seçimi ve File→Data Table/Box Plot örneği; [File ekran resmi](https://orange3.readthedocs.io/projects/orange-visual-programming/en/latest/_images/File-stamped.png), [workflow resmi](https://orange3.readthedocs.io/projects/orange-visual-programming/en/latest/_images/File-Workflow.png) URL'leri açıldı fakat görsel gözlem yok | Bir kaynağı farklı inceleme sonuçlarına bağlama; Veri_Ufku tablodan grafik seçimi ve görünür işlem geçmişi. Başlangıçta düğüm editörü zorunlu değil. |
| KNIME [User Guide 5.8](https://docs.knime.com/ap/5.8/analytics_platform_user_guide/) ve [latest](https://docs.knime.com/ap/latest/analytics_platform_user_guide/) | Workbench/entry/workflow, node configuration ve typed ports anlatımı; latest sayfa 5.12 başlığı, 5.8 tarihsel doküman. General layout resim açımı hata; [2024 PDF](https://docs.knime.com/2024-06/analytics_platform_user_guide/index.pdf) okundu, screenshot cache miss | Tipli girdiler ve işlem yapılandırması aynı bağlamda; uzman sağ parametre paneli. Workflow Faz64, başlangıç akışını kalabalıklaştırmaz. |
| jamovi [Getting started](https://www.jamovi.org/getting-started.html) | Open data→variable setup→analysis→annotation→save anlatımı; [open image](https://www.jamovi.org/media/gs-01-open-poster.webp), [analysis image](https://www.jamovi.org/media/gs-03-analysis-poster.jpg) görsel payload sunmadı | Tablodan analiz/sonuç görünümüne kısa yol; Veri_Ufku ortak veri üstbilgisi ve sonuç sekmesi. Elle hücre düzenleme aktarılmadı; ilk tablo salt okunur. |
| JASP [Getting started](https://jasp-stats.org/getting-started/) ve [resmî özellikler](https://jasp-stats.org/) | Analiz input sol/output sağ anlatımı, önceki sonuçtan parametreye dönme; resmî sayfa progressive disclosure belirtir. 2022 student guide PDF URL 404 | Parametre/sonuç beraber, ileri ayrıntı açılır. Veri_Ufku pahalı hesaplarda otomatik tekrar yerine açık çalıştır/iptal/maliyet. JASP'ın tüm kontrol davranışları görülmüş sayılmadı. |
| LabPlot [Gallery](https://labplot.org/pages/gallery/) ve [KDE Handbook](https://docs.kde.org/trunk_kf6/en/labplot/labplot/labplot.pdf) | Basic plots/custom worksheet layout açıklamaları; Handbook interface/property explorer/export bölümleri okundu. PDF p7 screenshot çağrısı yalnız URL referansı döndürdü, görsel yorum yapılmadı | Grafik verisi ile görsel özelliklerin ayrılması ve boyut/export kontrolü. Basit grafik Faz12, profesyonel figür/dashboard Faz39; tüm LabPlot menüleri aktarılmaz. |

## Kaynak erişim sorunları

Orange ana visual-programming adresi erişilemedi; proje ReadTheDocs sayfası erişildi. KNIME workbench/latest ilk adres timeout/error verdi; user guide 5.8/latest ve PDF erişildi. jamovi user-manual yönlendirmesi getting-started'dan tamamlandı. LabPlot `/screenshots/` ve eski KDE domaini erişilemedi; `/pages/gallery/` ve KDE handbook erişildi. Terminal urllib DNS başarısız, web kaynak metin erişimi başarılı. Bu kısıt görsel kontrol için mazeretle kabul üretmez: UI-REF-VIS doğrulanmadı.

## Tasarım gerekçesi

Başlangıç kullanıcısına dosya→amaç→önizleme→inceleme→seçili işlem→sonuç→kaydet yolu verilir. Ortak soldaki navigasyon, merkez çalışma alanı, sağ bağlama bağlı yardım/parametre paneli ve üstte veri sürümü her ekranda aynı kalır. Referansların renk/ikon/menu kümeleri birleştirilmez. Üç temsilî tasarım [triptych](prototypes/triptych.svg) ve değerlendirme [DESIGN_REVIEW](DESIGN_REVIEW.md); bunlar referans ekranlarının görsel incelemesini veya gerçek kullanıcı testini ikame etmez.

## Faz02 gerçek görsel inceleme — 2026-10-06

Beş resmî görsel indirildi, view_image ile görüldü; URL/hash/boyut [kayıtta](evidence/phase02-references.json). Önceki erişim başarısızlıkları tarihsel olarak korunur. UI-REF-VIS doğrulandı; uygulamalar çalıştırılmadı, animasyon/klavye/tema davranışları bu görüntülerden çıkarılmaz.

| Referans / görülen statik ekran | Gerçek görsel gözlem | Veri_Ufku kararı |
|---|---|---|
| [Orange File](https://orange3.readthedocs.io/projects/orange-visual-programming/en/latest/_images/File-stamped.png) | Üstte dosya seçimi, ortada veri boyutu ve kolon tür/rol listesi, altta örnek/veri ve rapor eylemleri | Dosya bağlamı sürekli üstte; başta dosya/örnek girişleri. Tür/rol yolu Faz07’ye kalır. |
| [KNIME modern layout](https://docs.knime.com/assets/04_knime_modern_ui_general_layout.BnLLqhkG.avif) | Açıklamalı görselde dar sol araç şeridi, yan panel, merkez workflow, üst sekmeler, alt node monitor | Dar sabit alan navigasyonu + merkez iş alanı; düğüm/workflow editörü bu faza alınmadı. |
| [jamovi analiz](https://www.jamovi.org/media/gs-03-analysis-poster.jpg) | Üstte metinli analiz ikonları, solda değişken/parametreler, sağda tablo/grafik sonucu | İkon yanında metin, parametre değişiminden bağımsız görünür sonuç. Çok sayıda analiz düğmesi kopyalanmadı. |
| [JASP ana ekran](https://jasp-stats.org/wp-content/uploads/2026/07/front.page_.0.98.1-scaled.png) | Üst araç şeridi, sol analiz parametreleri, sağ sonuçlar; sağ alt kısım tanıtım rozetiyle örtülü | Teknik ayrıntılar görünüm tercihiyle açılır; sonuç her iki görünümde kalır. Örtülü kısımlar değerlendirilmedi, marka/mascot alınmadı. |
| [LabPlot temel grafikler](https://labplot.org/images/gallerie-section/01_basic_plots_linux.png) | Sol proje ağacı, merkez çoklu grafik worksheet, sağ Fit özellik/sonuç paneli | Proje bağlamı ve ayrı kapanabilir bilgi paneli. Grafik/fit/DAG bu fazda geliştirilmedi. |

Referanslardan yalnız kullanım ilkeleri seçildi; tokenlar Veri_Ufku’nun kendi sisteminden gelir. Orijinal resimler /tmp içinde incelendi; ürün varlıklarına veya repo görsellerine kopyalanmadı. KNIME AVIF yerel Pillow ile PNG’ye çevrilerek görüldü. [Kanıt](evidence/PHASE02.md#e02-references).
