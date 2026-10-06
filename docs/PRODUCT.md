# Veri_Ufku — ürün ve ilk sürüm kapsamı

Tarih: 2026-10-06. Bu belge hedef davranışı tanımlar; mevcut uygulama özelliği değildir. Kalıcı kurallar: [PROJECT_RULES](PROJECT_RULES.md), [UI_DESIGN_BRIEF](UI_DESIGN_BRIEF.md). Kabul: [REQUIREMENTS_MATRIX](REQUIREMENTS_MATRIX.md).

## Kullanıcı ve değer

Başlangıç kullanıcısı dosyasının anlamını, sorunlarını ve değişiklik etkisini kod yazmadan görür. Öğrenen kullanıcı işin yanında açıklama açar. Uzman aynı veri ve sonuçlar üzerinden yöntem, filtre ve tanılamaya erişir. İstatistik/model kullanmak zorunlu değildir. Açılışta amaç: inceleme, temizleme, grupları karşılaştırma, ilişkiler, tahmin, benzer kayıtları gruplama veya sıra dışı kayıtları bulma. Yalnız geliştirilmiş yollar etkinleşir.

## Kullanıcı hikâyeleri ve sıfır bilgi senaryoları

### US-01 — Dosyamı anlamak istiyorum (Faz 05–08, 12–13)

Bir mağaza çalışanı olarak satış listemde ne olduğunu bilmek istiyorum; dosyam değişmeden satırları, eksikleri ve satış tutarlarının dağılımını anlayabilmeliyim.

Planlanan paket örneği `magaza.csv`: 12 kayıt, kimlikler `0001`–`0012`, gün, şube, tutar; 2 tutar eksik, geçerli tutarlar 10,20,20,30,40,50,60,70,80,100. Veri tamamen yapay; gelecek örnek dosyanın elle doğrulanan bekleneni 12 kayıt, 10 geçerli, toplam 580, ortalama 58, medyan 45. İlk sürüm kabul fixture'ı bu değerleri korur; şu anda dosya/import yok.

1. “Veriyi incelemek” → “Örnek dosya” veya kendi CSV'si.
2. Önizlemede kimliklerin baştaki sıfırını, tarih biçimini ve virgüllü ondalık ayarını görür. Algılama önerisini onaylar; hata varsa düzeltir.
3. Kaynağı projeye kopyalama tercihini görür; kopya kapalı olsa da çalışma snapshot'ı gerekliliği anlatılır.
4. Tablo üstünde “12 kayıt / 4 sütun / tüm veri”; kalite kartında “2 tutar eksik” görür. Kimlik “Kayıt tanımlayıcısı” olarak gösterilir ve ölçüm önerilmez.
5. Tutarı seçer; “Medyan — sıralanmış değerlerin ortası” ve açıklama bağlantısını görür. Histogramı seçer, eksiklerin dışlandığı 10 kayıt kapsamını görür.
6. PNG/SVG veya özet raporunu farklı hedefe kaydeder; proje yeniden açıldığında veri sürümü ve filtre korunur. Kaynak byte hash'i değişmemiştir.

Başarı: ilk kez kullanan kişi sözlü yardım olmadan akışı tamamlar; aynı örnekte n, eksik ve medyanı doğru anlatır. Bu kullanıcı testi Faz 25'te ayrı kanıttır, şu an doğrulanmadı.

### US-02 — Verimi temizlemek istiyorum (Faz 08–11, 13)

Bir ofis çalışanı olarak şube adlarındaki boşlukları düzeltmek istiyorum; önerinin nedenini, değişecek kayıtları ve geri dönüş yolunu görebilmeliyim.

Planlanan `subeler.csv`: 6 kayıt; `Ankara`, ` Ankara `, `İzmir`, `İzmir `, `Bursa`, `Bursa`; benzersiz kaynak kimlikleri. Kırpma tam 2 kaydı değiştirir; kaydı azaltmaz. İçeriği aynı iki Bursa kaydı ayrı kalır.

1. Temizleme amacı → import → kalite paneli “2 kayıtta baş/son boşluk var; farklı gruplar oluşabilir”.
2. “Metin boşluklarını temizle” seçer. Açıklama alan içinde anlamlı boşlukları koruduğunu anlatır.
3. Önizleme aynı RowId ile önce/sonra yan yana; 2/6 etkilenen kayıt, 0 silme, 0 yeni null. Hiçbir dönüşüm seçimden önce uygulanmaz.
4. “Uygula” yeni DatasetVersion üretir. Tekrar kayıt önerisi ayrı kalır; kimliğin farkı görünür. Kullanıcı dedup seçmeden silme olmaz.
5. Geri al → önceki sürüm; yeniden uygula → yeni dal. İşlem geçmişinde tarif, karar ve etki korunur.
6. “Farklı dosyaya aktar” CSV hedefini seçer, ardından proje kaydı. Kaynak korunur. Kaydetme hatasında son sağlam sürüm açılabilir.

Başarı: 6 kayıt ve iki farklı Bursa SourceRecordId'si korunur, 2 metin değişir, geri alma byte/değer bütünlüğünü korur. Genel doldurma seçilirse model yolunda veri bağımlı geçmiş olarak işaretlenir.

### US-03 — Tahmin yapmak istiyorum (Faz 15–18, 20)

Bir bakım sorumlusu olarak yeni ekipmanın enerji tüketimini tahmin etmek istiyorum; sonucu kesin gerçek sanmadan basit bir karşılaştırma ve hata birimi görebilmeliyim.

Planlanan yapay eğitim örneği: 60 cihaz × 12 ay = 720 kayıt; cihaz kimliği, ölçüm zamanı, yaş, çalışma süresi, tüketim kWh; hedef ufku gelecek ay. Ek dosya 5 yeni cihaz için tahmin anında bilinen özellikler içerir. Gelecek ayın tüketimi veya arıza sonucu özellik olamaz. Sayısal cihaz kodu ölçüm değildir.

1. “Tahmin etmek” → “Bir sayıyı” → hedef `tuketim_kwh`. Hedefin neyi anlattığını sade dille teyit eder.
2. “Ne zaman tahmin?”, “Kaç ay sonrası?”, “Aynı cihazlar mı yeni cihazlar mı?” sorulur; cihaz ve zamanı seçer.
3. Yeni cihaz ve gelecek zaman hedefinde hem cihaz ayrılığı hem zaman sınırı sağlanır. Eğitimde daha eski aylar/eski cihazlar; validation ve testte ayrık cihazlar/daha ileri aylar. Yeterli örnek/sınıf yoksa geçerli plan bulunamadığı gerekçesiyle durur. Rastgele split'e sessiz dönmez.
4. Eksik doldurma/ölçekleme yalnız eğitim fold'unda fit edilen ML pipeline'ında önerilir. Önceden tüm veriyle yapılan doldurma/özellik seçimi geçmişi incelenir; bağımsız ham sürüme dönme veya keşifsel kullanım seçimi gerekir.
5. Baseline ve dar model adayları validation/CV ile karşılaştırılır. MAE kWh cinsinden anlatılır; örnek sonucun sayısı hesap gerçekleşmeden yazılmaz.
6. Final testi ayrı açar; veri/protokol/run kimliğiyle deftere kaydedilir. Sonraki ayar yeni run olsa da aynı test yeniden kullanımı görünürdür. Bağımsız değerlendirme gereği açıklanır; kullanıcı davranışının tamamını denetleme iddiası yoktur.
7. Desteklenen güvenli model paketini kaydeder; yeni dosya eşlemesini önizler. Eğitim pipeline'ı yalnız transform/predict; 5 satır sonucu RowId ile eşlenir. Güvensiz dış pickle/joblib açılmaz.

Başarı: target/gelecek bilgi sızmaz; grup ve zaman birlikte ayrılır; baseline, hata birimi, fit sınırı, tekrar test kaydı ve sonuç eşlemesi bağımsız testlerle kanıtlanır. Model yolları Faz 13 sürümünde henüz mevcut değil.

## Ölçülebilir teslim sınırları

İlk kullanılabilir inceleme/temizleme sürümü Faz 00–13'ün zorunlu şartlarıdır: CSV/TSV, JSON/JSONL, XLSX, Parquet; proje aç/kaydet/farklı kaydet/kurtarma; sayfalı tablo/rol/profil/kalite; işlem önizlemesi/geçmiş/geri alma; Faz 10–11 dönüşümleri; Faz 12'deki yedi grafik türü, PNG/SVG ve Faz 13 raporları; çevrimdışı yardım ve örnekler. Dosya biçimi, dönüşüm ve grafik başına ayrı kabul kaydı gerekir. US-01/02 gerçek masaüstünde tamamlanmalıdır. [Performans hedefleri](PERFORMANCE.md) ayrıca ölçülür.

Faz 20 temel ML eşiği, Faz 27 temel dağıtım adayıdır. Faz 21–23 henüz mevcut değil ve kapsam kararı verilmedi; isteğe bağlı olabilir fakat kullanıcı ertelemesi yok. Faz 28–75 profesyonel kapsam Faz 28'de seçilecektir; liste onların geliştirilmesini başlatmaz. Dağıtım adayı erken paket smoke hatalarını, kritik kayıp/sızıntı hatalarını ve zorunlu kabul açıklarını kapatmadan verilemez.

## Açık ürün kararları ve riskler

| Kimlik | Karar / risk | Politika ve kapanış |
|---|---|---|
| D-01 | Hücre/satır düzenleme ve tabloya panodan yapıştırma | İlk sürüm salt okunur. Veri dönüşümleri yalnız işlem motoru. Kopyalama serbest; kayıtlara yapıştırma yok. Ek kapsam seçilmedi; seçilirse EDIT-* kimlikleri, parse/undo/kimlik/transaction/ölçek/sızıntı testleri zorunlu. |
| D-02 | Kaynak kopyalama | Varsayılan orijinal dosya kopyası kapalı; tutarlı çalışma snapshot'ı zorunlu. Disk ve gizlilik maliyeti importtan önce açıklanır. |
| D-03 | Marka | Yalnız Veri_Ufku metin adı ve ortak tasarım tokenları; logo/mascot çalışması yok. |
| D-04 | Proje taşınabilirliği | Çalışma verisi ve yardım kimlikleri projede; asıl kaynak yoksa yeniden import sınırlıdır. Paylaşım önizlemesi içerilen veri miktarını gösterir; metadata-only paylaşım profesyonel faza bağlı. |
| O-01 | Uygulama lisansı / uygulama-ID alan adı | Kullanıcı/yayıncı kararı açık; ADR-001/004. Paket release kapısı; Faz 00 planını engellemez. |
| O-02 | 21–23 ve profesyonel modüllerin seçimi | Henüz karar yok; Faz 27/28'de açık kapsam kararı gerekir. |
| R-01 | Kaynak okuma sırasında değişir | Sabit snapshot + digest doğrulaması; güçlü snapshot alınamıyorsa işlemi durdur. |
| R-02 | Disk dolması/elektrik kesilmesi | ADR-003 yayınlama sırası, yerinde ezme yok; backup ve fault injection. |
| R-03 | Örneklem tüm veri sanılır | Her sonuçta kapsam/n/seed/seçim yolu, seçimin sınırlamaları. |
| R-04 | Öğrenilmiş temizlik model sızıntısı | Tarifin learned_scope bilgisi, ham sürüm, fold-içi fit. |
| R-05 | Dönüşüm hassasiyet kaybı | Sözleşme tip sınırı; kaybı önizle veya reddet. |
| R-06 | Yeni format/model desteği olduğundan geniş gösterilir | Capability yöntem başına gerçek destek ve mevcut değil durumu; desteklenmeyen yükleme durur. |

Bu kararlar Faz 00 tasarım kararlarıdır; uygulamada kanıtlanmış güvence değildir. Kullanıcı yetkisi olmadan veri kopyalarını silme, kayıplı migration veya mevcut projeyi yeniden yazma yok.
