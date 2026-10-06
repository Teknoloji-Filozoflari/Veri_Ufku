# Veri_Ufku — Kalıcı ana proje promptu

Kaynak: [birleşik talimat](../Veri_Ufku_Birlestirilmis_Gelistirme_Promptlari.md). Faz 00, 2026-10-06. Kullanıcı talimatları bu kayda göre önceliklidir.

Linux üzerinde çalışan, yerel ve çevrimdışı kullanılabilen bir veri bilimi masaüstü uygulaması geliştiriyoruz. Ürünün adı tam olarak Veri_Ufku. Hedef kullanıcı veri bilimi ve programlama bilmeyebilir. Dosyasını açmalı, verisini anlamalı, hangi işlemin neden önerildiğini görmeli, işlem önizlemesini incelemeli, seçerek uygulamalı, sonuçları kaydedebilmelidir. İstatistik veya model kurmadan da uygulamadan yararlanabilmelidir.

ÜRÜN İLKELERİ
- Arayüz sade, modern, tutarlı ve erişilebilir olsun. Açık/koyu/sistem teması; sakin renkler, yeterli boşluk, okunabilir tipografi, az sayıda belirgin ana eylem kullan.
- Varsayılan deneyim başlangıç seviyesine uygun olsun. Gelişmiş seçenekleri aşamalı aç; iki mod arasında veri veya proje kaybı olmasın.
- Kullanıcıya önce amacını sor: veriyi incelemek, temizlemek, grupları karşılaştırmak, ilişkileri araştırmak, tahmin etmek, benzer kayıtları gruplamak, sıra dışı kayıtları bulmak.
- Teknik terimin yanında sade karşılığını göster. Örneğin 'Medyan — sıralanmış değerlerin ortası'. Gereksiz pop-up veya zorunlu ders kullanma.
- Her işlemde isteğe bağlı 'Bu ne işe yarar?' açıklaması, örnek, ne zaman kullanılacağı, ne zaman uygun olmayacağı ve sonuçların yorumlanması bulunsun. Bunun için uygulamaya entegre çevrimdışı bir Öğren merkezi kur.
- Veri ve model sonuçlarını olduğundan kesin gösterme. Korelasyon nedensellik değildir; model tahmini kesin sonuç değildir. İstatistiksel test kullanıcı sorusuna ve varsayımlara bağlıdır.
- Öneriler gerekçeli olsun ve kullanıcının seçimi olmadan veriyi değiştirmesin. Sayısal kimlikleri ölçüm kabul etme. Aykırı değeri otomatik silme.
- İşlem öncesi/sonrası karşılaştırma, etkilenen kayıt sayısı, geri alma ve işlem geçmişi temel davranış olsun.
- Kaynak dosyayı varsayılan olarak koru. Yerel çalış; zorunlu hesap, Docker, internet servisi veya ücretli API kullanma.

TEKNİK BAŞLANGIÇ TASARIMI
- Python tabanlı analiz çekirdeği ve PySide6/Qt Quick Controls tabanlı masaüstü arayüzüyle başla. GUI'yi analitik hesaplamadan ayır. Bu bir web sitesi değildir.
- Tablo işleme için Polars; yerel SQL, büyük veri sorguları ve disk destekli işlemler için ihtiyaç oldukça DuckDB; modelleme için scikit-learn; istatistik için SciPy, gerekli özel analizlerde statsmodels düşün.
- Grafikler için yerel Qt arayüzüne bağlanan, PNG/SVG dışa aktarabilen bir Matplotlib adaptörü kullan. Çizim altyapısını soyutla; UI ile analitik sonuçları birbirine bağlama.
- Proje meta verisi için SQLite, veri anlık görüntüleri için gerektiğinde Parquet ve sürümlü manifest kullan. Kaynak veriyi proje içine kopyalama seçimini kullanıcıya açıkça sun.
- Bu yığını uygulamadan önce ortamı, desteklenen sürümleri, lisans yükümlülüklerini ve Qt entegrasyonunu resmi belgelerden doğrula. Anlamlı uyumsuzluk varsa teknik kararı belgede gerekçelendir; mevcut projeyi sebepsiz yeniden yazma.
- Paket sürümlerini tahmin etme; uyumlu sürümleri seç, kilitle, yinelenebilir kurulum oluştur. Test ve lint araçları geliştirme bağımlılıklarında olsun.
- Uzun işlemler arayüz dışında çalışsın. İlerleme, iptal ve kontrollü hata aktarımı olsun. Ağır CPU işleri için ayrı süreç; hafif I/O için uygun worker kullan. GUI nesnelerini worker'dan değiştirme.
- Tabloyu her hücre için bir widget ile kurma. Model/view, sayfalama veya sanallaştırma kullan. Büyük veriyi sırf görüntülemek için tamamen belleğe alma.

GÜVENİLİRLİK
- Dosya içeriğini kod olarak çalıştırma. Excel makrolarını çalıştırma. Formül editöründe eval/exec kullanma. SQL değerlerini parametrele; seçilen kolon ve tablo adlarını doğrula.
- Dışarıdan gelen pickle/joblib modellerini otomatik açma. Model saklama/yükleme güvenli format ve desteklenen türlerle sınırlandırılsın.
- Model için öğrenilen doldurma, kodlama, ölçekleme ve özellik seçimi yalnızca eğitim katında fit edilmeli. Pipeline kullan. Ham veri üstünde kullanıcı tarafından önceden yapılan veri bağımlı dönüşümler de sızıntı incelemesine dahil olsun.
- Zaman ve grup bilgisine göre uygun ayırma kullan. Test kümesini hiperparametre veya model seçimi için tekrar tekrar kullanma.
- Örneklem ve tüm veri sonuçlarını açıkça ayır; sonuçların veri sürümünü, filtrelerini, yöntemini ve seed'ini kaydet.
- Dosya yolu, kaydetme, hatalı veri, iptal, bellek yetersizliği ve proje sürüm geçişlerini ele al.

GELİŞTİRME BİÇİMİ
- AGENTS.md ve mevcut kodu oku. Yalnız gönderdiğim fazı uygula; sonraki fazları başlatma.
- Her fazda gerçek uçtan uca davranış üret. Sahte düğme, uydurulmuş analiz sonucu ve boş yer tutucu ile fazı bitmiş sayma.
- Henüz geliştirilmemiş özellikleri açıkça 'henüz mevcut değil' göster veya navigasyondan çıkar; çalışıyormuş gibi gösterme.
- UI, domain modelleri, analitik servisler, dosya adaptörleri, proje deposu, görev yöneticisi ve yardım içeriği ayrı sorumluluklar olsun. Gereksiz framework veya soyutlama ekleme.
- Önemli hesaplar, veri bütünlüğü, kaydetme, sızıntı ve import için anlamlı testler yaz. Sırf kapsam yüzdesi yükseltmek için uygulamayı taklit eden testler yazma.
- Her faz sonunda ilgili kontrolleri çalıştır; yapılmayanları açıkça belirt. Belgeleri ve docs/PROGRESS.md'yi güncelle.
- Sonuç mesajında değişen davranışı, çalıştırılan doğrulamaları, bilinen sınırlamaları ve benim deneyebileceğim kısa GUI adımlarını yaz.
- Rutin kararları alarak ilerle. Veri kaybına yol açabilecek belirsizlikte dur; eksikleri sessizce kapsam dışı bırakma.
ORTAK SÖZLEŞMELER VE DOĞRULAMA
- Bu belgedeki kurallar birlikte geçerlidir. Sonraki yöntem maddesi ortak veri bütünlüğü ve kabul şartlarını zayıflatamaz. Belirsizliği görünür kaydet; keyfî kapsam azaltma yapma.
- Faz durumu: başlanmadı, sürüyor, engelli, doğrulandı. Yetenek olgunluğu ayrı alandır: mevcut değil, deneysel, kararlı. Kapsam kararı ayrı alandır: zorunlu, isteğe bağlı, ertelendi. Engel açıklaması ve erteleme kabul kanıtı değildir.
- Her kabul maddesinin kalıcı gereksinim kimliği olsun. Kod/GUI yolu, test veya manuel kontrol kanıtı, ortam, çalıştırma tarihi ve sonuç ile eşleştir. Genel test başarısı tek başına tüm alt yöntemleri doğrulamaz. Test edilemeyen madde doğrulanmadı kalır.
- docs/REQUIREMENTS_MATRIX.md tüm temel/profesyonel gereksinimler için ana kayıt olsun. docs/PROGRESS.md ve docs/PRO_PROGRESS.md bu kayda referans veren faz özetleridir; çelişen durumlar otomatik kontrolde hata üretmelidir.
- DatasetVersion, ColumnId, SourceRecordId ve RowId ayrımını tanımla. Satır sıra numarası veya yalnız içerik hash'i kalıcı kimlik değildir. Aynı içerikli farklı kayıtlar ayırt edilsin. Join, explode, aggregate ve dedup sonrası kaynak ilişkisi ve kimlik üretimi belgeli olsun; büyük provenance için sıkıştırılmış/tembel temsil kullan.
- Dataset, işlem tarifi, model pipeline'ı ve sonuç sürümleri ayrı olsun. Her görev başladığı veri/config sürümüne bağlı kalsın; eski iş sonucu güncel ekrana sessiz yazılmasın.
- Polars/DuckDB/NumPy ve model adaptörleri için ortak hesap anlamı tanımla: null/NaN/inf/boş metin, decimal ve integer hassasiyeti, timezone, kategori sırası, sıralama bağları, ddof, quantile yöntemi, join null davranışı ve aggregate tanımı. Motor farklılığı sessiz sonuç değişikliğine dönüşmesin; desteklenmeyen dönüşümü engelle veya kaybı önizle.
- SQLite, Parquet ve manifest için tek yayınlama protokolü kullan: yeni çıktıyı geçici yerde hazırla, doğrula, kalıcı hâle getir, sonra aktif sürüm işaretçisini değiştir. Desteklenen dosya sisteminde dayanıklılık sınırlarını açıkla. Başarısız adım son sağlam kaydı değiştirmesin. Açılışta yarım işlemleri güvenli temizle/kurtar.
- Aynı projeye tek yazıcı ilkesi uygula. İkinci süreç salt okunur açsın veya anlaşılır biçimde reddedilsin. Kilit kurtarma aktif yazıcıyı devre dışı bırakmasın. Kaynak ve hedefin aynı dosya olması, symlink ve desteklenmeyen ağ dosya sistemi durumlarını ele al.
- Kaynak dosyanın önizleme, import ve uzun okuma sırasında değişmesi için politika belirle. Mümkünse değişmez snapshot kullan; değilse tutarlılık kontrolleriyle değişimi yakala ve yeniden önizleme iste. Yalnız dosya adı/tarihini içerik bütünlüğü garantisi sayma.
- ComputeBudget, capability kaydı ve provenance'ın asgari sözleşmeleri başlangıç mimarisinin parçasıdır. Profesyonel fazlar bunları genişletir. Ağır modülleri erkenden geliştirme; aynı sözleşmenin farklı modüllerde bağımsız kopyalarını oluşturma.
- Hedef donanım, veri sınıfları ve performans kabul bütçelerini Faz 00'da tanımla; başlangıç ölçümleriyle güncelle. Açılış, önizleme, UI yanıtı, iptal, RAM ve geçici disk için ölçüm yöntemi olsun. Ölçülmeyen hedefi karşılanmış gösterme.
- CI ilk iskeletten itibaren çalışsın. İlk gerçek import, grafik/export ve worker yolu hazır olduğunda erken Linux paket smoke testi yap; bütün paket sorunlarını son faza bırakma. Başsız test, gerçek masaüstü testi ve kullanıcı testi ayrı kanıtlardır.
- Çevrimdışı çalışma, çevrimdışı kurulum ve isteğe bağlı model/modülün yerel paketten kurulumu ayrı yeteneklerdir. Destek düzeyini bildir. Temel paket yardım, örnek veri, font ve rapor kaynaklarını içersin; ilk kullanımda gizli indirme istemesin.
- Grup ve zaman kısıtları birlikte gerekiyorsa değerlendirme planında birlikte uygula. Tahmin anında bilinen bilgi, hedef ufku ve aynı varlık/yeni varlık kullanımını sor. Geçerli split yoksa gerekçesiyle dur.
- Final test değerlendirmelerini proje boyunca veri/protokol/run kimliğiyle kaydet. Testin tekrar görülmesini yeni run açarak görünmez kılma. Keşifsel kullanım ve yeniden ayarlama sonrası bağımsız değerlendirme ihtiyacı açık olsun; kullanıcı davranışını tamamen denetlediğin iddiası kurma.
- Referans testler yalnız üretimdeki kütüphaneyi aynı parametrelerle yeniden çağırmasın. Küçük elle hesaplanan değerler, analitik örnekler ve uygun bağımsız referanslar kullan; toleransı gerekçelendir.
- Kritik veri kaybı veya bilimsel doğruluk hatası varken ilgili sürüme dağıtım adayı kabulü verme. “Sorun bulunmadı” ifadesi yalnız gerçekleştirilen kontrollerin kapsamıyla sınırlıdır.

Bu ana prompt proje boyunca geçerlidir. Yalnız açıkça gönderilen fazı uygula.
