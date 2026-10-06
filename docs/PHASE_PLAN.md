# Veri_Ufku — faz bağımlılık planı

Bu belge uygulama yetkisi değildir. Durum [REQUIREMENTS_MATRIX](REQUIREMENTS_MATRIX.md) içindedir. Temel yol Faz00–13 ilk inceleme/temizleme, 14–20 istatistik/ML, 24–27 doğrulama/dağıtım; 21–23 kullanıcı kararıyla optional, ertelenmiş değil. Profesyonel seçim Faz28. Doğrudan bağımlılıklar aşağıda; transitif atalar da karşılanmalıdır. Ortak güvenlik/sözleşmeler her faza uygulanır.

| Faz | Teslim | Doğrudan önkoşullar |
|---|---|---|
| 00 | Kapsam, mimari ve geliştirme planı | Yok |
| 01 | Çalışan proje iskeleti ve görev altyapısı | 00 |
| 02 | Sade modern arayüz ve amaç odaklı gezinme | 01 |
| 03 | Öğren merkezi ve bağlama bağlı bilgi paneli | 02 |
| 04 | Proje kaydı, veri sürümleri ve kurtarma temeli | 01 |
| 05 | CSV ve TSV içe aktarma sihirbazı | 03, 04 |
| 06 | JSON, JSONL, Excel ve Parquet | 05 |
| 07 | Veri tablosu, profil ve sütun rolleri | 05, 06 |
| 08 | Veri kalitesi ve gerekçeli öneriler | 07 |
| 09 | İşlem motoru, önizleme ve geri alma | 04, 07, 08 |
| 10 | Temizleme ve eksik veri işlemleri | 09 |
| 11 | Dönüştürme, birleştirme ve diğer yerel kaynaklar | 09, 10 |
| 12 | Keşifsel analiz ve etkileşimli grafikler | 07, 09, 11 |
| 13 | İlk kullanılabilir sürüm, raporlar ve rehberli tur | 00, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12 |
| 14 | İstatistiksel karşılaştırma sihirbazı | 03, 07, 12, 13 |
| 15 | Özellik hazırlama ve model öncesi uygunluk | 07, 09, 10, 13 |
| 16 | Veri bölme ve sızıntısız değerlendirme altyapısı | 15 |
| 17 | Sayısal tahmin: regresyon | 12, 16 |
| 18 | Kategori tahmini: sınıflandırma | 12, 16, 17 |
| 19 | Kümeleme ve anomali tespiti | 12, 15, 16 |
| 20 | Model yorumlama, güvenli kaydetme ve yeni veriye uygulama | 17, 18, 19 |
| 21 | Zaman serisi inceleme ve tahmin | 12, 16, 20 |
| 22 | Başlangıç düzeyinde metin analizi | 07, 16, 20 |
| 23 | İş akışını yeniden çalıştırma ve veri değişimi izleme | 09, 11, 20 |
| 24 | Büyük veri, performans ve uzun işlem dayanıklılığı | 13, 20 |
| 25 | Kullanılabilirlik, erişilebilirlik ve öğrenme içerikleri denetimi | 13, 20, 24 |
| 26 | Güvenlik, kurtarma ve uçtan uca doğruluk | 04, 20, 24, 25 |
| 27 | Linux paketleme, belgeler ve dağıtım adayı | 00, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 24, 25, 26 |
| 28 | Mevcut uygulama denetimi ve profesyonel yol haritası | 00, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 24, 25, 26, 27 |
| 29 | Yöntem kayıt sistemi ve profesyonel çalışma alanı | 28 |
| 30 | Gelişmiş tablo formatları ve dosya kaynakları | 06, 24, 29 |
| 31 | Veritabanı ve kullanıcı tarafından açılan ağ kaynakları | 11, 29, 30 |
| 32 | Veri sözlüğü, kalite sözleşmeleri ve varlık eşleme | 07, 08, 29, 30 |
| 33 | İleri eksik veri, örnekleme ve ağırlıklar | 10, 16, 29, 32 |
| 34 | Çok boyutlu bilimsel veri ve birimler | 24, 29, 30, 32 |
| 35 | Profesyonel dağılım ve belirsizlik grafikleri | 12, 29, 33 |
| 36 | Çok değişkenli, ilişkisel ve yüksek boyutlu görseller | 35 |
| 37 | Kompozisyon, hiyerarşi, akış ve iş grafikleri | 35, 36 |
| 38 | Coğrafi veri, haritalar ve mekânsal analiz | 24, 29, 30, 32, 34 |
| 39 | Bağlantılı dashboard ve yayın kalitesinde figür düzenleme | 12, 35, 36, 37 |
| 40 | İstatistiksel modeller ve tanılama | 14, 16, 29, 32, 33, 35 |
| 41 | Bootstrap, permütasyon, çoklu test ve sağlam analiz | 14, 29, 33, 40 |
| 42 | Deney tasarımı, A/B testi ve güç analizi | 14, 32, 40, 41 |
| 43 | Bayesçi analiz ve model kontrolü | 16, 29, 40, 41 |
| 44 | Nedensel çıkarım ve varsayımların görünürlüğü | 16, 29, 32, 40, 41 |
| 45 | Sağkalım ve olay zamanı analizi | 16, 29, 32, 40 |
| 46 | Boyut indirgeme ve özellik seçimi | 16, 29, 35, 36 |
| 47 | Gelişmiş kümeleme, yoğunluk ve anomali yöntemleri | 19, 29, 46 |
| 48 | Profesyonel tabular model kataloğu | 20, 29, 32, 33, 46 |
| 49 | Hiperparametre araması ve bütçeli AutoML | 16, 29, 48 |
| 50 | Kalibrasyon, tahmin belirsizliği ve karar eşikleri | 16, 48, 49 |
| 51 | Açıklanabilirlik, hata dilimleri ve adalet değerlendirmesi | 16, 39, 48, 50 |
| 52 | Deney takibi ve model kayıt sistemi | 20, 29, 49, 50, 51 |
| 53 | İleri zaman serisi ve panel tahmin | 21, 29, 33, 40, 48, 52 |
| 54 | Sinyal işleme, sensör ve frekans analizi | 21, 29, 34, 35 |
| 55 | İleri NLP, arama ve metin etiketleme | 22, 29, 46, 48, 52 |
| 56 | Derin öğrenme çalışma motoru | 16, 29, 48, 52 |
| 57 | Görüntü verisi, annotation ve bilgisayarlı görü | 30, 32, 56 |
| 58 | Ses verisi ve ses analizi | 30, 54, 56 |
| 59 | Öneri sistemleri ve sıralama | 16, 29, 32, 48, 52 |
| 60 | İlişkilendirme kuralları, kohort ve süreç analizi | 29, 32, 35, 40 |
| 61 | Ağ ve graf verisi | 29, 30, 32, 36 |
| 62 | Streaming, online ve özel öğrenme hedefleri | 23, 29, 32, 52, 53 |
| 63 | Profesyonel kod, SQL ve notebook köprüsü | 23, 29, 52 |
| 64 | Görsel workflow ve başsız batch çalıştırma | 23, 29, 39, 52, 63 |
| 65 | Veri kökeni, ortam ve bilimsel yeniden üretilebilirlik | 29, 32, 52, 64 |
| 66 | CPU/GPU, disk ve dağıtık hesaplama bütçeleri | 24, 29, 49, 56, 65 |
| 67 | Model izleme ve operasyonel kalite | 23, 32, 48, 50, 52, 65 |
| 68 | Monte Carlo, duyarlılık ve optimizasyon | 29, 40, 41, 52, 66 |
| 69 | Öğrenme laboratuvarı ve uygulamalı ders yolları | 03, 25, 29, 64 |
| 70 | Profesyonel rapor, dashboard anlatısı ve araştırma notları | 13, 39, 40, 52, 65, 69 |
| 71 | Ekipler arasında proje aktarımı ve inceleme | 26, 32, 65, 70 |
| 72 | Gizlilik, güvenlik ve veri yaşam döngüsü | 26, 32, 65, 71 |
| 73 | Uzman eklentileri ve açık geliştirme SDK'sı | 29, 63, 64, 65, 66, 72 |
| 74 | Profesyonel dağıtım, ortam yönetimi ve kalite matrisi | 27, 29, 66, 72, 73 |
| 75 | Profesyonel sürümün bilimsel ve ürün kabul denetimi | 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74 |

## Geçiş kapıları

Faz13 bütün 00–12 zorunlu şartları; Faz20 model yöntem başına gerçek fit/evaluate/predict/save/help sınırları; Faz27 bütün 00–20 ve 24–26 + erken paket hataları kapanmış olmalı. 21–23 ertelemesi açık kullanıcı kararı ve release notu ister. Faz28 giriş 00–20 ve24–27 kanıt denetimi; karar verilmemiş 21–23 belirsizliği görünür. Faz53→21, Faz55→22 ve Faz64→23 gereklidir; bu temeller ertelenirse ilgili profesyonel modül engelli kalır.

Profesyonel fazların listede olması seçilmiş zorunlu teslim anlamına gelmez. Faz28 yöntem/modül seçimi yapınca kapsam alanları güncellenir; seçilen faz içindeki source gereksinimleri zorunludur, optional backend ayrı alt capability. Faz75 seçilmiş bütün modüllerin kanıtını denetler; bu tablodaki bütün 29–74 kenarları seçilmiş kapsamla incelenir, erteleme kabul kanıtı değildir.

## Alt iş ilkesi

Format, dönüşüm, istatistik, grafik veya model başına Fxx-Snnn.<method> kimliği; GUI/hesap/help/save/export/cancel alt kanıtları. Önce küçük uçtan uca bir yöntem, sonra kalan alt işler; genel pytest başarısı paragraftaki bütün yöntemleri doğrulamaz. Faz30 formatları, Faz35–38 grafikleri, Faz40 modelleri, Faz48 estimator aileleri ve diğer profesyonel alt yöntemler ilgili faz başlamadan ayrı satırlara açılır; kaynak paragraf kapsamı aynı kalır. Zorunlu önceki faz düzeltmesi DEP-Fxx-* ve önceki regression kanıtıyla kayıtlıdır.

Ağır modül, registry v2 veya GPU Faz 00 kapsamında geliştirilmez. Minimal sözleşmeler [CORE_CONTRACTS](CORE_CONTRACTS.md) tek kaynak; profesyonel fazlar genişletir.
