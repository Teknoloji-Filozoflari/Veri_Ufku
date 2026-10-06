# Veri_Ufku — Birleştirilmiş geliştirme promptları

Revizyon: 6 Ekim 2026. Faz 00–75. Bu belge bir geliştirme talimatıdır; uygulamanın mevcut özellikleri veya testlerinin başarılı olduğuna dair kanıt değildir.

## Kullanım ve kapsam

1. İlk oturumda aşağıdaki kalıcı ana proje promptunu ve kalıcı arayüz kurallarını ver; ardından yalnız geliştirmek istediğin fazı gönder. Bu dosyanın tamamını okumak, bütün fazları çalıştırma yetkisi değildir.
2. Faz 00'da bu kalıcı kuralları depodaki proje belgelerine kaydet. Her oturumda yeniden kopyalamak yerine belgeleri okuyarak devam et.
3. Faz 13 ilk kullanılabilir veri inceleme/temizleme sürümü; Faz 20 temel ML; Faz 27 temel dağıtım adayıdır. Faz 21–23 ayrı yeteneklerdir ve açık kapsam kararıyla ertelenebilir. Erteleme tamamlanma değildir.
4. Profesyonel geliştirmeye geçiş için Faz 00–20 ve 24–27'nin zorunlu kabul şartları doğrulanmış olmalı; Faz 21–23'ün durumu ve bunlara bağımlı profesyonel işler açıkça listelenmelidir. Örneğin ileri zaman serisi Faz 53 için Faz 21, ileri NLP Faz 55 için Faz 22, workflow Faz 64 için Faz 23 temelinin tamamlanması gerekir. Bağımlılıkların tamamı Faz 28'de denetlenir; sayısal sıra tek başına güvenlik garantisi değildir.
5. Profesyonel ana prompt Faz 28'den itibaren temel ana prompta eklenir. Profesyonel modüllerin zorunlu/isteğe bağlı teslim kapsamı Faz 28'de seçilir. Kullanıcı tarafından seçilmemiş kapsamı sessizce azaltma.
6. Yalnız seçilen fazı ve zorunlu önceki bağımlılık düzeltmelerini uygula. Sonraki fazları başlatma. Bağımlılık düzeltmesini ayrı kimlikle kaydet; ilgili önceki testleri çalıştır. Kapsamı değiştiren kararları görünür tut.
7. Faz büyüklüğü oturum süresiyle sınırlı değildir. Alt işleri ve kalanları kaydet; yalnız bir kısmı yapıldıysa fazı tamamlandı sayma.
8. Ürün adı tam olarak **Veri_Ufku**. Görünen ad, başlık, rapor, yardım ve belgelerde bu yazımı kullan. Python paket adı gibi teknik kimlikler ayrı ADR'de belirlenir; mevcut teknik kimlik değişikliği veri dizinlerini ve proje uyumluluğunu bozmamalıdır.

## Kalıcı ana proje promptu


---

```text
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
```

---

## Kalıcı arayüz ve tasarım kuralları

```text
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
```

---

## Faz 00 — Kapsam, mimari ve geliştirme planı

```text
Ana proje promptuna bağlı kalarak Faz 00'ı uygula.

Henüz analitik özellikleri kodlama. Depoyu ve ortamı incele. Kullanıcı hikayelerini, ekran akışını, veri modelini ve faz bağımlılıklarını somutlaştır. docs/PRODUCT.md, docs/ARCHITECTURE.md, docs/UX.md, docs/PROGRESS.md ve önemli teknik kararlar için kısa ADR kayıtları oluştur.

Üç kullanıcı yolunu ayrıntılandır: 'Dosyamı anlamak istiyorum', 'Verimi temizlemek istiyorum', 'Tahmin yapmak istiyorum'. Sıfır bilgiyle tamamlanabilen örnek senaryolar tanımla. Ürün adı Veri_Ufku; marka tasarımı kapsamı büyütmesin.

Dataset, ColumnProfile, ColumnRole, OperationSpec, DatasetVersion, AnalysisResult, ChartSpec, Job, LearningArticle, ModelRun ve ProjectManifest sorumluluklarını tanımla. Kalıcı kimliklerle kolon yeniden adlandırma ilişkisini açıkla. İşlem zincirini sürümlü, tipli ve serileştirilebilir kur; veri işlem hattı ile ML pipeline'ı ayrı olsun.

PySide6/Qt Quick ve analitik araçların kurulu ortamla uyumunu resmi belgelerden kontrol et. Öğrenme içeriğinin çevrimdışı ve sürümlü olması, kaynak dosyaların değişmesi, proje taşınabilirliği, örnekleme ve büyük veri sınırlarını planla. Gerçek veri kaybı riskleri ve açık ürün kararlarını yaz.

Kabul: Fazların izlenebildiği belge, anlaşılır ekran haritası, sorumlulukları ayrılmış mimari, geliştirme/test çalıştırma planı ve ölçülebilir ilk sürüm kapsamı hazır. Teknik belirsizlikler gizlenmeden belirtilmiş. Sonraki faza geçme.

Ek kapsam: docs/CORE_CONTRACTS.md, docs/REQUIREMENTS_MATRIX.md ve docs/ACCEPTANCE_POLICY.md oluştur. Kalıcı ana promptu docs/PROJECT_RULES.md'ye, tasarım kurallarını docs/UI_DESIGN_BRIEF.md'ye kaydet. Kaynak kayıt/satır/kolon kimliklerini, ortak hesap anlamını, asgari capability/provenance/ComputeBudget şemalarını tanımla. Proje depolama ve tek yazıcı protokolünü ADR ile kaydet. Python paket/uygulama kimliğini görünen Veri_Ufku adından ayrı tanımla.
Hedef Linux ortamı ve donanımı, küçük/orta/büyük veri sınıflarını; açılış, önizleme, UI yanıtı, iptal, RAM/disk bütçeleri için ölçüm planını belirle. Çevrimdışı kurulum/çalışma kapsamını ayır. Elle hücre/satır düzenleme ve panodan yapıştırma için açık ürün kararı ver; varsayılan ilk sürüm tablosu salt okunurdur, dönüşümler işlem motorundan geçer. Ek düzenleme kapsamı seçilirse alt gereksinimler oluştur.
Ek kabul: Faz bağımlılıkları ve gereksinim kimlikleri kayıtlı; ertelenmiş modüller tamamlandı görünmüyor; tasarım belgeleri sonraki oturumların okuma listesinde.
```

---

## Faz 01 — Çalışan proje iskeleti ve görev altyapısı

```text
Faz 01'i uygula: çalıştırılabilir Python/PySide6 uygulaması, paket yapısı, bağımlılık kilidi ve geliştirme komutları kur.

UI, domain, services, importers, storage, jobs, learning ve tests için sorumluluklara uygun modüller oluştur. Tek uygulama giriş noktası, yapılandırma, yerel loglar ve anlaşılır hata modeli olsun. Loglarda veri satırlarını ve hassas değerleri varsayılan olarak tutma.

Görev yöneticisini job_id, durum, ilerleme, hata, iptal ve sonuç tipleriyle kur. Hafif I/O worker ile ağır CPU process işlerini ayırabilecek API oluştur. İptal edilen veya eski veri sürümüne ait sonuç güncel ekrana yanlışlıkla yazılmasın. Kapanışta görevleri kontrollü sonlandır.

Henüz gerçek analiz yok; küçük deterministik görevle altyapıyı doğrula. Testlerde GUI'nin başsız çalıştırılabileceği yapı ve temel lint kur.

Kabul: README'deki komutla uygulama açılıyor, worker sırasında pencere yanıt veriyor, görev iptali çalışıyor, hatalar ekranda anlaşılır ve teknik logda izlenebilir. Temel testler geçiyor.

Ek kapsam: Temel CI'ı şimdi kur; lint, çekirdek doğruluk ve başsız GUI smoke testini çalıştır. Asgari capability/provenance/ComputeBudget sözleşmelerini gerçek iş yöneticisine bağla. Görev sayısı, RAM/geçici disk ve iptal sürelerinin ölçümünü yap; ölçülemeyen ilerlemeyi yüzde olarak uydurma. worker→UI sonuç aktarımında veri/config sürümü eşleşmesini doğrula. Türkçe UI metinlerini ilk bileşenden itibaren çeviri altyapısına bağla.
```

---

## Faz 02 — Sade modern arayüz ve amaç odaklı gezinme

```text
Faz 02'yi uygula: tasarım tokenları ve gerçek uygulama kabuğu oluştur.

Dar sol navigasyon, üstte proje/dataset bağlamı, ortada çalışma alanı, gerektiğinde açılan sağ bilgi paneli kullan. Ana alanlar: Başlangıç, Veri, Hazırla, İncele, Karşılaştır, Model, Rapor, Öğren. Henüz yapılmayan alanları çalışır gibi gösterme.

Başlangıç ekranında 'Dosya aç' ve 'Örnek veriyle dene' eylemleri baskın olsun. Amaç kartları kısa günlük dil kullansın. Başlangıç/gelişmiş görünüm aynı veriyi kullansın. Gelişmiş mod teknik ayarları açsın; başlangıç modu sonuç bilgisini saklamasın.

Açık, koyu ve sistem teması; tutarlı boşluk, odak halkası, minimum okunabilir yazı, ölçeklenebilir pencere ve ikon yanında metin oluştur. Renk tek anlam taşıyıcısı olmasın. Boş, yükleniyor, hata ve iptal durumlarını ortak bileşen yap. Her ekranda ilgili yardımı açacak aynı 'Bu ne işe yarar?' mekanizması bulunsun.

Kabul: Küçük ve büyük pencerede içerik kullanılabilir; klavyeyle temel gezinme mümkün; tema ve görünüm tercihi korunuyor. Mevcut ortamda GUI'yi açıp kontrol et; ekran görüntüsü alınabiliyorsa üret, alınamıyorsa doğrulanmayan görsel ayrıntıları belirt.
```

---

## Faz 03 — Öğren merkezi ve bağlama bağlı bilgi paneli

```text
Faz 03'ü uygula: çevrimdışı yardım sistemi gerçek uygulama özelliği olsun.

Sürümlü öğrenme içerik şeması kur: id, başlık, sade özet, 'ne işe yarar', 'ne zaman kullanılır', 'ne zaman uygun değildir', küçük önce/sonra örneği, sonucu nasıl yorumlarım, sık hata, ilgili kavramlar, ilgili ekran/işlem ve içerik kaynakları. İçerik güvenli Markdown veya yapılandırılmış bloklardan render edilsin; rastgele HTML/JavaScript çalıştırma.

Üç derinlik sun: tek cümle açıklama; bir dakikalık örnek; ayrıntılı rehber. Panel kullanıcı isteğiyle açılıp kapanmalı. Okumadan işlemler yapılabilmeli. 'Uygulamada dene' yalnız gerçek mevcut özelliğe bağlansın ve kullanıcının kendi verisini değiştirmeden örnek proje açabilsin.

Öğren merkezine arama, kategori, sözlük ve isteğe bağlı yerel okundu/yer imi ekle. 'Veri nedir?', satır/sütun, veri türü, eksik değer, ortalama/medyan, örneklem, korelasyon, tahmin ve veri sızıntısı için başlangıç içerikleri yaz. Türkçe metinler günlük dilde; kesinlik veya nedensellik iddiası üretmesin.

Öğretim içeriğini analitik koda gömme. Her yeni faz kendi yardım içeriğini bu sisteme eklemeli. Kritik yanlış kullanım açıklamaları ileri seviyede de görünür kalsın.

Kabul: İnternetsiz yardım araması ve bilgi paneli çalışıyor; bağlamdan doğru makale açılıyor; kapatmak işlemi kesmiyor; yardım kaydı olmayan bağlar otomatik doğrulamada yakalanıyor.
```

---

## Faz 04 — Proje kaydı, veri sürümleri ve kurtarma temeli

```text
Faz 04'ü uygula: proje oluşturma, açma, kaydetme, farklı kaydetme ve son projeler.

Manifest sürümü, kaynak referansı/fingerprint, import ayarları, dataset kimlikleri, işlemler, sonuçlar, yardım tercihleri ve seed alanlarını sakla. Metadata için SQLite, gerektiğinde veri snapshot'ları için Parquet kullan. Projeyi uygulama sürümünden bağımsız şema sürümüyle yönet.

Kaynak referansı ile taşınabilir veri kopyası seçeneklerini açıkla. Kaynak dosya kaybolursa yeniden bağla; değişmişse eski analizleri güncel sayma. Metadata'nın açılması ile kaynak verinin yeniden işlenmesini ayır. Sonuçların hangi veri sürümüne ait olduğu görülsün.

Atomik kaydetme, işlem tutarlılığı, uygulama kapanışında değişiklik takibi ve otomatik kayıt temeli kur. Otomatik kayıt manuel kayıtlı projeyi sessizce bozmasın. Proje içe açılırken manifest alanlarını, boyutları ve yolları doğrula; arşiv kullanıyorsan yol dışına çıkmayı engelle. Eski proje migrasyonu için ilk fixture oluştur.

Kabul: Proje kapatılıp açıldığında durum korunuyor; eksik kaynak, yarım kayıt ve bilinmeyen gelecek şema sürümü anlaşılır biçimde ele alınıyor. Kaynak dosya değiştirilmemiş. Kaydet/aç testleri geçiyor.

Ek kapsam: SQLite/Parquet/manifest yayınlama protokolünü uygula; geçici artifact ve aktif sürüm ayrımını gerçek kodla kur. Aynı projeye ikinci yazıcıyı engelle; salt okunur açılış ve kontrollü eski kilit kurtarma ekle. Farklı kaydetmede aynı dosya/symlink ve hedef çakışmalarını kontrol et. Ağ dosya sistemi desteğini doğrulanmadıysa destekli sayma.
Ek kabul: Artifact yazımı, metadata commit ve aktif sürüm geçişi arasındaki her kritik noktada zorla sonlandırma testi; açılış son sağlam kaydı kurtarıyor. İki uygulama örneği aynı projeyi bozamıyor. Geçici dosya temizliği bağlı artifact'ları silmiyor.
```

---

## Faz 05 — CSV ve TSV içe aktarma sihirbazı

```text
Faz 05'i uygula: dosya seçme ve sürükleyip bırakmayla CSV/TSV içeri al.

Önizlemede ayraç, encoding, başlık satırı, ondalık/binlik ayracı, null işaretleri, tarih biçimi ve saat dilimi seçimleri bulunsun. Otomatik algılama öneridir; kullanıcı düzeltebilsin. Aynı ayarlar gerçek içe aktarmada da kullanılmalı.

Türkçe karakterler, virgüllü ondalıklar, tırnak içindeki ayraç/satır sonu, boş başlık, tekrar eden başlık, başlıksız dosya, boş dosya ve bozuk satırları ele al. Hatalı satırları sessizce atlama; durdurma veya raporlu karantina seçeneği sun. Önizlemenin sınırlı örnek olduğunu belirt.

Sütun türünü belirsiz örnekten kesin kabul etme; kullanıcı tür seçebilsin. Başında sıfır olan kimlik ve uzun numaralarda bilgi kaybını önle. Büyük dosyada streaming/lazy uygunluğu ve iptal kullan. İçe aktarma tamamlanmadan dataset'i başarılı kaydetme.

Yardım: ayraç, encoding, başlık, tarih biçimi, ondalık ve bozuk satır kavramları.

Kabul: Küçük referans CSV/TSV dosyaları beklenen değerlerle açılıyor; UTF-8 ve en az bir uygun eski Türkçe encoding örneği doğrulanıyor; bozuk kayıt sayısı raporlanıyor; iptal kaynak veya projeyi bozmuyor.

Ek kapsam: Önizleme ile import arasında ve okuma sırasında kaynak değişimini ele al. Tutarlı snapshot veya doğrulanmış değişiklik kontrolü kullan; değişen kaynağı sessiz kabul etme. SourceRecordId/RowId üret; aynı içerikli iki kaydın kimlikleri ayrı kalsın. Bozuk satır karantinasında kaynak konumu ve sebep korunsun.
Ek kabul: Önizleme sonrası değiştirilen CSV yeniden önizleme gerektiriyor veya değişmez snapshot üzerinden açıkça içe alınıyor; karışık dosya sürümlerinden başarılı dataset üretilmiyor.
```

---

## Faz 06 — JSON, JSONL, Excel ve Parquet

```text
Faz 06'yı uygula: import adaptör arayüzünü kullanarak JSON, JSONL/NDJSON, XLSX ve Parquet ekle.

JSON'da kökte kayıt listesi ve iç içe kayıt yolu seçimi destekle. Alan düzleştirme ve liste açma ayrı, kullanıcı tarafından seçilen işlemler olsun. Liste açmanın satır sayısını artıracağını ve farklı listeleri birlikte açmanın kartesyen çoğalma yaratabileceğini önizle. Alan eksikliği, açık null ve karışık türleri raporla. JSONL'de bozuk satırları numarasıyla belirt; key sırasına güvenme.

Excel'de sayfa, başlık ve veri aralığı seçimi; birleştirilmiş hücre ve boş satır davranışı açık olsun. Makro çalıştırma. Formül hücrelerinin formül/metin/önbellek değer davranışını anlat; önbellek yoksa sonuç uydurma. Parquet türlerini koru; liste/struct ve desteklenmeyen türleri açıkça ele al.

Dosya uzantısı tek doğrulama olmasın. Format hatalarını anlaşılır göster. Import provenance ve orijinal alan adlarını koru.

Yardım: JSON nesnesi/liste, düzleştirme, Excel sayfası, Parquet ve tür koruma.

Kabul: Her format gerçek örnekle açılıyor; nested JSON seçimi ve satır artışı doğru; Excel sayfa seçimi doğru; Parquet'te nullable ve tarih tipleri kontrol edilmiş.

Ek kapsam: Decimal, büyük integer, nullable tip, timezone ve nested veri dönüşümlerini CORE_CONTRACTS.md ile doğrula. Hassasiyet kaybı destek sınırı veya açık önizlemeli dönüşüm olsun. Excel tarih sistemi ve saat dilimsiz tarih davranışını tanımla. İlk import/worker yolu için hedef Linux paketinden erken smoke test başlat; ortam yoksa engelli kayıt bırak, testi başarılı sayma.
```

---

## Faz 07 — Veri tablosu, profil ve sütun rolleri

```text
Faz 07'yi uygula: sanallaştırılmış/sayfalı veri tablosu, kolon araması, sıralama, filtreleme, kolon gizleme ve sütun detay paneli.

Dataset profili: satır/sütun sayısı, fiziksel türler, eksik oranı, unique sayısı, örnek değerler, sayısal min/max/ortalama/medyan/std/yüzdelikler, kategorik frekanslar, tarih aralığı. Tam ve tahmini/örnek profili ayır; hesap kapsamını göster. NaN, infinity ve null ayrımını uygun biçimde ele al.

Sütun rolü önerileri: kimlik, kategori, ölçüm, tarih, serbest metin. Kullanıcı değiştirip kaydedebilsin. Rol fiziksel türü zorla değiştirmesin. 00123 gibi kimliği koru; kimliklerin otomatik ortalamasını ve korelasyonunu anlamlı bulgu diye sunma. Yüksek kardinaliteli sütunlarda tüm değerleri UI'ye dökme.

Aktif filtreler ve görünümün tüm veri mi alt küme mi olduğu belli olsun. Filtreli tablo ile analiz dataset'inin ilişkisini açık tanımla; gizli filtrelerle sonuç üretme.

Yardım: tür/rol farkı, unique, standart sapma, yüzdelik ve veri profili.

Kabul: Büyük tabloda gezinme belleği kontrolsüz artırmıyor; istatistikler referans veriyle doğru; rol düzeltmesi proje yeniden açıldığında korunuyor.

Ek kapsam: Sıralama ve filtreleme görüntü sıra numarasını kayıt kimliği yerine kullanmasın. Tablo varsayılan olarak salt okunur olduğunu açık göstersin. Ölçüm birimi, ordinal kategori sırası ve analiz birimi için asgari metadata alanlarını ekle; profesyonel veri sözlüğü Faz 32'de genişler. std/ddof, quantile yöntemi ve null/NaN kapsamı profil sonucunda kayıtlı olsun.
```

---

## Faz 08 — Veri kalitesi ve gerekçeli öneriler

```text
Faz 08'i uygula: veri kalitesi merkezini kur.

Eksikler, tam ve seçili kolonlara göre tekrarlar, tip dönüşüm hataları, geçersiz tarihler, boşluklar, kategori tutarsızlık adayları, sabit kolonlar, benzersizlik ihlalleri ve kullanıcı tanımlı aralık/kurallar için rapor üret. Şüpheli değer ile kesin kural ihlalini ayır. Tek evrensel 'kalite puanı' ile yanlış güven oluşturma.

Her bulguda gerekçe, etkilenen kayıt sayısı/oranı, birkaç örnek, kapsam, seçenekler ve yardım bağlantısı olsun. Aykırı gözlem yalnız adaydır. Benzer yazılan kategoriler otomatik birleştirilmesin; Türkçe büyük/küçük harf dönüşümü düşünülmeli.

Öneri motorunu rol, tür, amaç, örnek miktarı ve kural bağlamıyla deterministik kur. Öneri id, gerekçe, önkoşul, etki, işlem id ve learning id taşısın. Henüz olmayan işlem yalnız bilgi olarak gösterilsin; çalıştırma düğmesi olmasın.

Yardım: veri kalitesi, tekrar ile meşru tekrar farkı, eksik veri mekanizması, aykırı değer.

Kabul: Referans problemli veride beklenen kayıtlar işaretleniyor; tarama veriyi değiştirmiyor; her önerinin neden gösterildiği anlaşılır; örneklem taramasını tüm veri taraması diye sunmuyor.
```

---

## Faz 09 — İşlem motoru, önizleme ve geri alma

```text
Faz 09'u uygula: tüm veri değişikliklerinin geçeceği sürümlü işlem motorunu kur.

İşlem sözleşmesinde tipli parametreler, giriş dataset sürümü, kolon kimlikleri, çıktı şeması, uygulanabilirlik, doğrulama, etki özeti, çalışma durumu ve yöntem sürümü olsun. Önizleme ve gerçek uygulama aynı hesap yolunu kullansın. Örneklem etki sayısını gerçek toplam gibi sunma.

Kaynağı immutable tut; dönüşümleri yeni dataset sürümüne bağla. Undo/redo, dallanma veya redo temizleme davranışını belirle. Geçmişten önceki adımı değiştirmek aşağıdaki sonuçları güncel olmaktan çıkarsın. Analiz/grafik/model referanslarını sessizce yeni sürüme taşıma.

İlk gerçek işlemler kolon yeniden adlandırma, kolon çıkarma ve filtre uygulama olsun. Öncesi/sonrası tablo ve şema, değişen satır/sütun sayıları göster. İşlem sırasında hata/iptal durumunda eski dataset korunmalı.

Yardım: önizleme, işlem geçmişi, geri alma, kaynak ile çalışma verisi farkı.

Kabul: İşlem uygula/geri al/yinele sonrası veri eşitliği doğrulanıyor; proje yeniden açıldığında akış korunuyor; hatalı işlem yarım sonuç bırakmıyor; eski analizler açıkça işaretleniyor.

Ek kapsam: Filtre, sıralama, join, explode, aggregate ve dedup için satır kimliği/kökeni sözleşmesini uygula; henüz olmayan işlem türlerinin sözleşmesini tanımla, UI'sini erken geliştirme. Kullanıcı tarafından elle düzenleme kapsamı seçilmişse hücre değişimi, satır ekleme/silme ve panodan yapıştırmayı tipli işlemler olarak uygula: eski/yeni değer, hedef RowId/ColumnId, tür doğrulaması, toplu önizleme ve undo/redo gerekli. Seçilmemişse salt okunur davranış sürsün.
Ek kabul: Sıralanmış/filtrelenmiş tabloda işlem doğru kayıt üzerinde çalışıyor; aynı içerikli kayıtlar karışmıyor; redo ve yeniden açılış kimlikleri koruyor.
```

---

## Faz 10 — Temizleme ve eksik veri işlemleri

```text
Faz 10'u uygula: işlem motoruna temizlik araçları ekle.

Eksik satır/sütun kaldırma; sabit, ortalama, medyan veya en sık değerle doldurma; tam veya seçili kolonlara göre tekrar kaldırma; metin kırpma; güvenli kategori eşleme; veri türü/tarih dönüştürme. Zaman içinde ileri/geri doldurma ancak açık sıralama ve grup seçimiyle yapılsın; geleceği kullanma ihtimali açıklansın.

Kullanıcı yöntem seçsin. Her seçenekte yararı ve kaybı anlat. Tüm değerleri eksik kolon, eşit frekanslı mod, sıfır varyans, dönüştürülemeyen değerler ve tam sayı/ondalık hassasiyeti için tanımlı davranış olsun. Yeni null üretimi raporlansın.

Aykırı değeri işaretleme/filtreleme seçeneklerini ekle; silme varsayılan olmasın. IQR gibi yöntemin istatistiksel aday ürettiğini belirt. Dönüşümün kopya dataset veya mevcut işlem zincirine uygulanması anlaşılır olsun.

ML'de öğrenilecek doldurma işlemi ile genel veri temizliğini ayır. Veri bağımlı temizleme geçmişi gelecekte modelleme ekranında sızıntı açısından görünür olmalı.

Yardım: her yöntem için küçük sayısal önce/sonra örnekleri ve hangi durumda sakıncalı olduğu.

Kabul: Etki sayıları ve sonuçlar doğru; geri alma çalışıyor; otomatik silme yok; ileri doldurma gruplar arasında veri taşımıyor; tarih parse hataları görünür.

Ek kapsam: Dedup için tutulacak kaydı belirleyen sıra ve eşitlik kuralını kullanıcıya göster ve sakla. Mod eşitliği, NaN/null ayrımı, decimal dönüşümü ve timezone/DST belirsiz tarihlerini tanımlı politikayla ele al; sessiz yuvarlama veya tarih düzeltme yapma.
```

---

## Faz 11 — Dönüştürme, birleştirme ve diğer yerel kaynaklar

```text
Faz 11'i uygula: hesaplanmış kolon, metin bölme/birleştirme, tarih parçaları, gruplama/toplulaştırma, pivot/unpivot, alt alta ekleme ve join.

Formül editörü yalnız izinli ifade AST'sini ve fonksiyonları çalıştırsın; Python eval/exec yok. Bölme/sıfır, null yayılımı, tarih saat dilimi ve kolon tipi sonuçları açıklansın. Formüllerde kolonları kalıcı kimlikleriyle izleyip okunabilir isim göster.

Join sihirbazında anahtar, join türü, null davranışı, çakışan kolon adları ve eşleşmeyen kayıtlar gösterilsin. 1:1, 1:n ve n:n ilişkisini ölç; satır patlamasını uygulamadan önce açıkla. Append'de tür ve kolon uyuşmazlığını kullanıcıya çözdür. Pivot'ta aynı hücreye çok kayıt varsa agregasyon istenmeli.

ODS, salt okunur SQLite tablo seçimi ve Feather/Arrow IPC adaptörlerini ekle. Her adaptörde gerçek gerekli bağımlılık ve destek sınırlarını belgele. SQLite kaynak üzerinde yazma veya otomatik extension yükleme yapma.

Yardım: join türleri günlük örneklerle, gruplama, pivot, uzun/geniş veri ve güvenli formül.

Kabul: Çoktan çoğa join tahmini doğru; join/append undo ile geri dönüyor; SQLite kaynak değişmiyor; tüm yeni formatlar gerçek fixture ile açılıyor.

Ek kapsam: Join ve aggregate için çıktı kayıtlarının kaynaklara ilişkisini kaydet; tek kaynağa indirgenemeyen satırı uydurma tek RowId eşleşmesiyle sunma. Polars ve DuckDB desteklenen eşdeğer işlemlerde sözleşme fixture'larıyla karşılaştırılsın; null join, bağ sıraları, decimal ve tarih sonuçları kontrol edilsin. Kaynak salt okunurluğu ve çıktı hedef koruması gerçek testle doğrulansın.
```

---

## Faz 12 — Keşifsel analiz ve etkileşimli grafikler

```text
Faz 12'yi uygula: istatistik özeti ve grafik oluşturma ekranı.

Histogram, kutu grafiği, sütun, çizgi, dağılım, korelasyon ısı haritası ve eksik oranı grafiği ekle. Tür/rol/amaç bazlı öner; kullanıcı grafiği seçebilsin. Kimlikleri analitik eksen diye önermemeye dikkat et.

Başlık, eksen adı, birim, legend, seçilen gruplama/agregasyon, filtre, null davranışı, veri sürümü ve veri kapsamını sakla. Tarih çizgisinde sıralamayı ve tekrar tarihlerin agregasyonunu açıkla. Histogram bin seçimi ayarlanabilir olsun. Korelasyonda Pearson/Spearman ve çift başına geçerli gözlem sayısı göster; sabit kolonlarda NaN'ı anlamlı hata olarak ele al.

Kategorileri top-N ile kesiyorsan 'Diğer' ve dışarıda kalan sayıyı belirt. Büyük scatter için downsampling/aggregation seçimini açık göster. Plot adaptörü yakınlaştırma, reset, seçim ve PNG/SVG export sunabilsin; GUI ile hesap birbirinden ayrı kalsın.

Yardım: her grafik neyi gösterir, eksen nasıl okunur, çarpık dağılım, ortalama/medyan farkı, korelasyon neden nedensellik değildir.

Kabul: Grafik verisi referans tabloyla aynı; filtre ve veri sürümü görünür; büyük grafik UI'yi kilitlemiyor; export okunabilir; örnekleme gizlenmiyor.

Ek kapsam: Grafik seçimi ve tablo seçimi RowId üzerinden eşleşsin; örnekleme veya toplulaştırılmış noktada seçim kapsamı açık olsun. Gerçek QML/Matplotlib etkileşimi, PNG/SVG export ve process worker yolunu erken Linux paketi üzerinde birlikte dene; entegrasyon engelini Faz 27'ye kadar gizleme.
```

---

## Faz 13 — İlk kullanılabilir sürüm, raporlar ve rehberli tur

```text
Faz 13'ü uygula: mevcut özellikleri uçtan uca kullanılabilir ilk sürüme bağla.

Temizlenmiş veriyi CSV/JSON/JSONL/Parquet ve uygun sınırlarda XLSX olarak aktar. Tiplerin hangi formatta korunmadığını, null/date biçimini ve XLSX sınırlarını açıkla. Spreadsheet'e giden metin alanlarının formül olarak yorumlanmasını engelleyecek güvenli export politikası sun; gerçek sayısal değerleri bozma.

Yerel HTML ve PDF raporu üret: amaç, kaynak/provenance, filtreler, kalite bulguları, işlemler, tablolar, grafikler, yöntemler, sınırlamalar ve veri sürümü. Türkçe karakter ve sayfa bölünmesini kontrol et. HTML'de kullanıcı metnini escape et; rapor internetten script/font istemesin.

'Dosyamı anlamak istiyorum' rehberli yolu oluştur: import → profil → kalite → seçilen temizlik → grafik → rapor. Kullanıcı adım atlayabilsin; zorunlu ders yok. Örnek satış ve problemli veri projelerini küçük, sentetik ve lisansı açık olarak ekle.

Kabul: Veri bilimini bilmeyen biri örnek dosyadan rapora GUI'de ulaşabiliyor; export yeniden açılabiliyor; temizleme geçmişi kayıtta korunuyor. İlk sürümün gerçek kapsamını release notunda yaz; gelecek modelleri varmış gibi sunma.

Ek kapsam: Temel yardım, font, örnek veri ve rapor kaynakları paketle gelsin; internetsiz ilk açılış senaryosu çalıştır. Exportta veri türü kaybını ve kayıt sayısını doğrula. Kullanıcı testi varsa görev tamamlama, yardım ihtiyacı ve kritik hata ölç; yalnız geliştirici walkthrough'unu kullanıcı testi diye adlandırma. İlk sürüm durumu zorunlu kabul maddeleri üzerinden belirlensin.
```

---

## Faz 14 — İstatistiksel karşılaştırma sihirbazı

```text
Faz 14'ü uygula: kullanıcı sorusundan hareket eden istatistiksel analiz.

Yollar: iki bağımsız grup, aynı kişilerin önce/sonra ölçümü, üç veya daha fazla grup, kategorik ilişki, sayısal ilişki. Eşleştirme kullanıcı anahtarıyla kurulmalı; satır sırasını eş kabul etme. Ölçüm, grup, birim, bağımsızlık ve hipotez bağlamını sor.

İlk yöntemler: Welch t-testi, eşleştirilmiş t-testi, Mann–Whitney, Wilcoxon, ANOVA/Welch ANOVA uygulanabilirliği, Kruskal–Wallis, ki-kare/Fisher ve Pearson/Spearman. Kurulu resmi API'nin desteklediği yöntemleri doğrula. Varsayımlar ve örneklem koşulları için önkontrol ve açıklama göster. Normalite testinin tek başına otomatik karar vermesini engelle; parametrik olmayan yöntemlerin hipotezini yanlış 'medyan farkı' diye genelleme.

Sonuç: analiz başına n, eksik dışlama, istatistik, p-değeri, uygun etki büyüklüğü ve güven aralığı. CI sunulamayan yöntemde uydurma; sınırlamayı açıkla. Çoklu test/post-hoc için düzeltme seçenekleri ve seçim kaydı olsun. Bootstrap varsa seed, tekrar ve bağımlılık varsayımları kayıtlı olsun.

Yardım: p-değeri ne değildir, etki büyüklüğü, güven aralığı, eşleştirme, çoklu karşılaştırma ve gözlemsel ilişki.

Kabul: Referans hesaplarla sayısal doğrulama; yetersiz veri, sıfır varyans ve eşleşmeyen kişiler anlaşılır; 'p<0.05 kesin sonuç' metni yok.
```

---

## Faz 15 — Özellik hazırlama ve model öncesi uygunluk

```text
Faz 15'i uygula: modelleme için veri hazırlığını genel temizlikten ayıran ekran.

Amaç ve hedef seçimine göre uygunluk raporu üret: eksik hedef, sabit hedef, kimlikler, yüksek kardinalite, sınıf dağılımı, tarih/grup yapısı, örnek miktarı ve şüpheli hedef türevleri. Riskler gerekçeli olsun; hedef sızıntısını otomatik kesin tespit ettiğini iddia etme.

Model hazırlama planında kategorik encoding, sayısal scaling, eğitim katında imputasyon, tarih özellikleri ve isteğe bağlı özellik seçimi yer alsın. Her işlemin estimatöre göre gerekliliğini açıklayarak gereksiz scaling'i önerme. Üretilen kolon adları ve orijinal kolon ilişkisini sakla.

Önceki temizleme zincirini incele: tüm veriden öğrenilmiş ortalama doldurma, outlier eşikleri veya seçim kararları varsa sızıntı riskini göster. Kullanıcıya bu işlemleri fold içinde öğrenilen pipeline adımlarına taşıma ya da temiz kaynak sürümünden modelleme başlatma yolu sun. Sadece yeni pipeline kurarak geçmiş riski giderilmiş sayma.

Yardım: özellik/hedef, encoding, scaling, imputasyon ve neden eğitimde öğrenildiği.

Kabul: Hazırlık henüz tüm dataset üzerinde fit etmiyor; pipeline planı kaydediliyor; kimlik ve geçmiş veri bağımlı işlemler görünür; kolon eşlemesi tutarlı.
```

---

## Faz 16 — Veri bölme ve sızıntısız değerlendirme altyapısı

```text
Faz 16'yı uygula: train/validation/test, çapraz doğrulama ve baseline altyapısı.

Rastgele, sınıflı stratified, grup bazlı ve zaman bazlı ayırma ekle. Kullanıcı bağımsız kayıt mı, aynı kişiye/cihaza bağlı kayıt mı, zaman sırası mı seçsin; uygun varsayılan gerekçeli olsun. Gruplar bölümler arasında karışmasın; zaman testinde gelecek eğitimde bulunmasın. Sınıf azlığı ve split imkansızlığını açıkça ele al.

Ön işleme ve seçme yalnız train/fold içine fit edilsin. Cross-validation yalnız geliştirme verisinde yapılsın. Test sonuçlarını model ayarlarını yönlendirmek için kullanma. Seed, split üyelikleri veya tekrar üretilebilir kimlikler, veri sürümü, pipeline ve paket sürümleri kaydedilsin.

Baseline regresyonda basit merkez tahmini, sınıflandırmada uygun Dummy yaklaşımı olsun. Skor yönü, geçersiz fold ve metrik kapsamını yapılandırılmış sakla. Uygun train boyutu ve tahmini maliyet göster; evrensel 'bu kadar satır yeter' garantisi verme.

Kabul: Test kayıtlarının fit'e katılmadığını yakalayan anlamlı test; grup/time ayırma doğrulamaları; sabit seed ile aynı ayrım; iptal edilen koşu yarım başarılı görünmüyor.

Ek kapsam: Tahmin anı, hedef ufku, aynı varlığın geleceği/yeni varlık ayrımı ve bilginin kullanılabilirlik zamanını kaydet. Grup ve zamanı birlikte koruyan validation planını destekle; çakışan kısıtlar için sessiz random split fallback yapma. Küçük/sınıfı eksik fold ve imkânsız ayrımı açıkça reddet.
Final test kullanım defterini kur: dataset/split/protokol/run, değerlendirme zamanı ve kullanıcının sonraki seçimleriyle ilişki. Yeni run veya proje içi kopya açılması önceki test kullanımını görünmez kılmasın; proje dışı kullanımı bildiğin iddiası kurma.
Ek kabul: Birleşik grup/zaman fixture'ı ve tekrar test değerlendirmesi geçmişi doğru; desteklenmeyen protokol GUI'de açıkça engelleniyor.
```

---

## Faz 17 — Sayısal tahmin: regresyon

```text
Faz 17'yi uygula: 'Bir sayıyı tahmin etmek istiyorum' uçtan uca yolu.

Hedef ölçüm kolonu, kullanılacak özellikler, bölme planı ve hazırlık planını seçtir. Baseline, doğrusal/Ridge ve RandomForest gibi sınırlı başlangıç adayları sun; her modelin kısa açıklaması ve maliyet sınırı olsun. Hiperparametreleri başlangıçta makul ve dar tut; sınırsız AutoML yok.

MAE, RMSE, R²; gerçek/tahmin ve artık grafikleri göster. MAE'yi hedefin birimiyle anlat. R²'nin negatif olabileceğini, sabit hedefte yorum sorunlarını belirt. 'Doğruluk yüzde 95' gibi regresyona yanlış genel skor sunma.

Model karşılaştırması validation/CV üstünden yapılsın. Seçilen modelin test değerlendirmesi ayrı ve kayıtlı olsun. Aynı testte sürekli model seçmeyi önle veya sonuçları keşifsel olarak açıkça işaretle. Koşu, pipeline, seed ve provenance sakla.

Yardım: regresyon, baseline, hata birimi, artık ve aşırı öğrenme.

Kabul: Sentetik veri üstünde gerçek tahmin üretimi; baseline karşılaştırması; target'ın özelliklere sızmaması; eksik/hedef tür hataları anlaşılır; modelleme tüm veriyle rastgele eğitim yapmıyor.

Ek kapsam: Validation/CV karşılaştırması ile final test görünümünü ayır; final test kullanımını Faz 16 defterine kaydet. Test sonucunu gördükten sonra ayarlanan modelin değerlendirmesini bağımsız final değerlendirme gibi sunma.
```

---

## Faz 18 — Kategori tahmini: sınıflandırma

```text
Faz 18'i uygula: 'Bir kategori tahmin etmek istiyorum' yolu.

Baseline, LogisticRegression ve RandomForest başlangıç modelleri; ikili/çok sınıflı hedef, pozitif sınıf seçimi ve sınıf dağılımı görünümü ekle. Dengesiz sınıflarda accuracy'nin yanıltıcı olabileceğini sade örnekle açıkla.

Karışıklık matrisi, accuracy, precision, recall, F1; uygun durumda ROC-AUC/PR-AUC. Çok sınıfta averaging stratejisi ve sınıf bazlı metrikler kaydedilsin. Olasılık desteklenmeyen model için eğri uydurma. Hiç tahmin edilmeyen sınıf, sıfır bölme ve testte bulunmayan sınıf kontrollü olsun.

Eşik değiştirme varsa validation üzerinde seçtir; test üzerinde optimize etme. Kullanıcının hata maliyeti tercihini açıklama olarak kaydet; uygulama otomatik kararın sahada güvenli olduğunu iddia etmesin. Resampling eklenirse yalnız eğitim fold'unda uygulansın.

Yardım: pozitif sınıf, yanlış alarm/kaçırılan kayıt, precision-recall farkı, eşik ve tahmin olasılığının anlamı.

Kabul: İkili ve çok sınıflı örnekler gerçek çalışıyor; azınlık sınıfı görünür; metrikler referansla aynı; model seçiminde test kullanılmıyor.

Ek kapsam: Eşik seçimi, sınıf seçimi ve sonraki model ayarlarının protokol geçmişini sakla. Final test yeniden kullanımı görünür olsun; testin tekrar görülmediğini garanti edemediğin durumda bunu açıkça belirt.
```

---

## Faz 19 — Kümeleme ve anomali tespiti

```text
Faz 19'u uygula: etiketsiz analiz için iki ayrı yol oluştur.

Kümelemede seçili ölçümler, ölçekleme ve uygun kategorik kullanım sınırlarını anlat. KMeans ve DBSCAN ile başla. Küme sayısı/mesafe ayarlarını anlamlı açıklamalarla sun. Küme profilleri, boyutları ve örnek kayıtlar göster. Görsel için boyut indirgeme kullanılıyorsa bunun orijinal uzayın tamamını göstermediğini belirt. Silhouette yalnız koşullar uygunsa hesapla; tek küme, tüm noise ve çok küçük kümelerde kontrollü ol.

Anomalide IsolationForest ve basit sütun IQR adayları ayrı yöntemler olsun. Skor yönü ve seçilen eşik açık; flagged kayıtlar adaydır. Gerçek etiket yoksa precision/recall uydurma. Sonuçları işaretli kolon veya yeni dataset'e aktar; otomatik silme yok.

Küme/anomali sonucu fiziksel gerçek sınıf veya veri hatası gibi etiketlenmesin. Parametre, seed, fit kapsamı ve dataset sürümü kayıtlı olsun. Yeni veri atama yalnız model gerçekten destekliyorsa açık olsun; DBSCAN'in doğal predict özelliği varmış gibi davranma.

Yardım: küme, uzaklık/ölçek, gürültü noktası, anomaly skoru ve etiket yokken değerlendirme sınırı.

Kabul: Kümeler gerçek hesaplanıyor; geçersiz silhouette engelleniyor; anomali silmiyor; desteklenmeyen yeni veri tahmini açıkça belirtiliyor.
```

---

## Faz 20 — Model yorumlama, güvenli kaydetme ve yeni veriye uygulama

```text
Faz 20'yi uygula: model yaşam döngüsünü tamamla.

Model kartı oluştur: amaç, veri sürümü, eğitim kapsamı, özellikler, hedef, split, ön işleme, aday seçimi, metrikler, baseline, seed, sürümler ve sınırlamalar. Katsayı/önemler nedensel etki değildir. Permutation importance için uygun değerlendirme bölümü kullan; ilişkili değişkenlerde yorum sınırını açıkla.

Model paketi şema, preprocessing ve desteklenen güvenli model formatı içersin. Uygun güvenli serileştirme seçeneğini resmi destek matrisinden değerlendir; desteklenmeyen estimator'ın kaydını açıkça engelle. Rastgele pickle/joblib dosyalarını açma; 'yerel' diye güvenilir sayma. Paket hash/integrity ve versiyon uyumluluğunu kontrol et.

Yeni dosyada kolon isimleri/kimlik eşlemesi, türler, eksikler, bilinmeyen kategoriler ve fazla kolonlar için önizlemeli kontrol yap. Eğitim pipeline'ını transform/predict için kullan; yeni veride tekrar fit etme. Sonuçları orijinal satırlarla doğru eşleştir; kaynak veriyi ezmeden aktar. Sınıflandırmada olasılık destek sınırını göster.

Yardım: model kartı, özellik önemi, bilinmeyen kategori, yeni veri ve tahmin belirsizliği.

Kabul: Kaydet/aç sonrası tahmin eşdeğerliği; uyumsuz paket güvenli reddediliyor; yeni veride fit çağrısı yok; sonuç satır eşlemesi doğru.

Ek kabul: Filtre/sıralama, duplicate içerik, düşürülen geçersiz kayıt ve parçalı batch prediction durumlarında sonuçlar doğru RowId ile eşleşiyor. Model paketinde feature sırası, label sırası, veri tipi/birim ve preprocessing sözleşmesi korunuyor.
```

---

## Faz 21 — Zaman serisi inceleme ve tahmin

```text
Faz 21'i uygula: zaman serisini normal rastgele regresyondan ayrı bir yol olarak ekle.

Tarih, ölçüm, isteğe bağlı grup; sıklık, duplicate tarih, eksik dönem, saat dilimi ve agregasyon kontrolü yap. Düzensiz veriyi sessizce düzenli sayma; yeniden örnekleme kullanıcı seçimi olsun. Toplam ve ortalama seçiminin anlamını anlat.

Trend, mevsimsellik ve uygun hareketli ortalama incelemesi; naive/seasonal-naive baseline; resmi API'nin uygunluğuna göre ExponentialSmoothing gibi sınırlı tahmin modeli ekle. Minimum geçmiş ve mevsim dönemi koşullarını açıkla. Basit baseline'ı karşılaştırmadan gelişmiş modeli başarı sayma.

Rolling-origin doğrulama ve gelecekte kalan test aralığı kullan. Lag ve rolling özellikler yalnız geçmişi görsün; merkezli pencere veya gelecekle doldurma sızıntı yaratmasın. Grup bazlı serileri karıştırma. MAE/RMSE; sıfır değerlerde MAPE sorununu açıkla. Tahmin aralığı desteklenmiyorsa uydurma.

Yardım: sıklık, mevsimsellik, lag, tahmin ufku ve geçmişten geleceğe doğrulama.

Kabul: Gelecek kayıt eğitim/özellik üretimine girmiyor; düzensiz zaman davranışı açık; baseline gerçek; çok kısa seri kontrollü reddediliyor.
```

---

## Faz 22 — Başlangıç düzeyinde metin analizi

```text
Faz 22'yi uygula: serbest metin sütunları için yerel ve açıklanabilir modül.

Boş metin, uzunluk, kelime/n-gram sıklığı, seçilebilir durak sözcükleri ve TF-IDF incelemesi ekle. Türkçe karakter, I/İ/ı/i ve Unicode davranışını açık test et. Dil varsayımını kullanıcı düzeltebilsin. Görselleştirmede frekans tablosu/sütun grafiği öncelikli olsun.

Etiketli metin varsa mevcut sınıflandırma altyapısına eğitim fold'unda fit edilen TF-IDF pipeline bağla. Etiketsiz metinde benzerlik/temel gruplama ayrı seçenek olabilir; embedding veya dış API zorunlu ekleme. Otomatik duygu/konu analizi varmış gibi uydurma etiket üretme.

Tokenizasyon ve temizliğin sonuçları değiştirdiğini önce/sonra örnekle göster. Önizlemede hassas metinlerin loglara gitmesini önle. Büyük vocab ve n-gram için sınır/ilerleme/iptal koy.

Yardım: token, n-gram, stopword, TF-IDF, benzerliğin anlamı ve dil sınırları.

Kabul: Türkçe örnekler ve boş kolonlar çalışıyor; vocab yalnız eğitimden öğreniliyor; internet olmadan modül çalışıyor; hassas içerik loglanmıyor.
```

---

## Faz 23 — İş akışını yeniden çalıştırma ve veri değişimi izleme

```text
Faz 23'ü uygula: kayıtlı işlemleri yeni dataset'e güvenle uygulama.

İşlem akışını sürümlü declarative tarif olarak aktar/al. Gerekli kolonlar, türler, roller ve yöntem parametreleri doğrulansın. Yeni veriye eşleme sihirbazı, dry-run, etki özeti ve her adımın hatası olsun. Tarif kod çalıştırmasın.

Analiz tarifi ile eğitimde öğrenilmiş model pipeline'ını ayır. Yeni veri gelince 'modeli uygula' ve 'yeniden eğit' farklı, açık eylemler olsun; sessiz retraining yok. Eğitim/veri sürümü referansları korunsun.

Eski/yeni dataset arasında eksik oranı, kategori dağılımı, sayısal dağılım ve şema değişimini göster. Drift testi/eşik varsa yöntemi ve örneklem etkisini anlat; dağılım değişimini otomatik model başarısızlığı sayma. Gerçek hedef sonradan geldiyse satır/kimlik eşlemesiyle yeni performans ölçümü yap; hedef yoksa başarı metriği uydurma.

Yardım: tekrar kullanılabilir akış, şema uyumu, drift, model uygulama/yeniden eğitim farkı.

Kabul: Aynı veri/seed aynı sonucu üretiyor; eksik kolon dry-run'da yakalanıyor; başarısız yeniden uygulama mevcut projeyi bozmuyor; model yeniden fit edilmeden uygulanabiliyor.
```

---

## Faz 24 — Büyük veri, performans ve uzun işlem dayanıklılığı

```text
Faz 24'ü uygula: mevcut çalışan yolları gerçek ölçümlerle iyileştir.

Import, profil, filtre, join, grafik, rapor ve model aşamaları için zaman/bellek ölç. Ortam bilgisiyle küçük/orta/büyük sentetik benchmark kaydet; ölçmeden performans iddiası yazma. Veri satırını widget'lara veya büyük DataFrame kopyalarına yığma.

Uygun yerde Polars lazy, DuckDB disk/spill, chunk ve bounded cache kullan. Örneklenmiş analizi tam hesap diye gösterme. Modelin belleğe sığması gerektiği durumlarda maliyet öngörüsü, özellik daraltma veya açık örneklem seçeneği sun; her model streaming destekliyormuş gibi davranma.

İlerleme bilinemiyorsa sahte yüzde yerine aşama/belirsiz ilerleme göster. İptal edilen süreç geçici dosyaları temizlesin ve dataset transaction'ı yarım bırakmasın. Aynı anda ağır iş sayısını sınırla. Kaynak değişimi, düşük disk ve bellek hatalarını anlaşılır ele al.

Kabul: Belgelenmiş donanımda benchmark sonuçları; import/analiz sırasında GUI kullanılabilir; tekrar işlem belleği sınırsız büyütmüyor; ağır görev iptali güvenli.

Ek kapsam: Faz 00 performans bütçelerini temsilî donanımda ölç; hedef/ölçüm/fark tablosu oluştur. UI yanıtı ve iptal gecikmesini ayrıca ölç. Bellek ve disk sınırı aşımının güvenli hata davranışını test et; kaynak paylaşımı ve aşırı thread oluşturmayı kontrol et.
```

---

## Faz 25 — Kullanılabilirlik, erişilebilirlik ve öğrenme içerikleri denetimi

```text
Faz 25'i uygula: ürünün sıfır bilgiyle kullanılabilirliğini denetle ve bulunan sorunları düzelt.

Tam klavye akışı, odak sırası, Qt erişilebilirlik adları, ekran okuyucu uyumu, yüksek DPI, büyük font, açık/koyu kontrast ve renk körlüğüne uygun grafikler kontrol edilsin. Gerçekte çalıştırılmayan assistive teknoloji testlerini yapılmış gösterme.

Tüm işlemler için yardım kapsamını denetle: sade özet, somut örnek, uygun/uygunsuz durum, sonuç yorumu ve ilgili ekran. Broken learning id, eksik açıklama, teknik jargon ve yanlış kesinlik ifadelerini otomatik + manuel kontrol et. Gelişmiş seçenekler bilgi panelini kaybettirmesin.

Türkçe varsayılan ve İngilizce altyapısı/tamamlanmış temel çeviriler; sayı/tarih formatının veri içe aktarma ayarlarıyla karışmamasını sağla. UI'de metin taşmalarını kontrol et. İlk kullanım turu atlanabilir ve yeniden açılabilir olsun; okundu bilgisi not veya değerlendirme değildir.

Beş senaryo yürüt: dosya aç/profil; eksik temizle/geri al; grafik/rapor; iki grubu karşılaştır; model/yeni veriye tahmin. Senaryo walkthrough'unu gerçek kullanıcı testi diye sunma. Kullanıcı testi yapılmadıysa ayrı belirt.

Kabul: Yardım bağlantıları eksiksiz; temel yollar klavyeyle tamamlanıyor; yeni başlayan anlatımında teknik varsayımlar saklanmıyor; denetim bulguları ve kalanlar belgeli.

Ek kapsam: Kullanıcı testi planında yeni başlayan ve uzman görevleri, başarı tanımı, yardım alma ve kritik hata kaydı olsun. Gerçek kullanıcı testi yapılmadıysa bu ürün doğrulama açığını açık bırak. Erişilebilirlik kontrolünü yalnız bu faza bırakma; her yeni ortak bileşenin önceki kontrollerini sürdür.
```

---

## Faz 26 — Güvenlik, kurtarma ve uçtan uca doğruluk

```text
Faz 26'yı uygula: dağıtım öncesi veri bütünlüğü ve güvenilirlik incelemesi.

Import parser'ları, kötü manifest/path traversal, formül AST, SQL parametreleri, HTML escape, spreadsheet formula injection, güvenli model yükleme, log gizliliği ve geçici dosya yaşam döngüsünü denetle. Güvenlik testi için gerçek kullanıcı verisi kullanma.

Bozuk/yarım proje, ani kapanma, kaydetme sırasında disk dolması, kaynak kaybı ve concurrent job sonuçlarını dene. Otomatik kayıttan kurtarma kullanıcıya neyin kurtarılacağını açıklasın; son iyi kopyayı koru. Eski şema migrasyonlarını fixture'larla doğrula; geri dönüşü mümkün olmayan geçişte yedek olsun.

Altın referans veriyle istatistik, join, dönüşüm ve ML metriklerini doğrula. Sızıntı, group/time split ve yeni veride fit yokluğu testlerini yeniden değerlendir. Çevrimdışı temel yolların ağ bağlantısı olmadan tamamlandığını doğrula. Kaynak dosyaların hash'leri korunmalı.

Kabul: Kritik bulgular giderilmiş; gerçek test raporu ve destek sınırları yazılmış; sahte GUI/analiz davranışı yok; kurtarma ve iptal veri kaybına yol açmıyor.

Ek kapsam: Proje kayıt protokolünün bütün kesilme noktaları, aynı projeye iki süreç, import sırasında kaynak değişimi, RowId eşlemesi ve motorlar arası hesap anlamı testlerini denetle. Altın referansların bağımsızlığını kontrol et. Örnek kullanıcı verisi kullanmadan temel parser kaynak tüketimi sınırlarını doğrula.
```

---

## Faz 27 — Linux paketleme, belgeler ve dağıtım adayı

```text
Faz 27'yi uygula: Linux'ta kurulabilir dağıtım adayı oluştur.

Önce tek güvenilir paketleme yolunu seç: ortam ve Qt/Python gereksinimlerine göre AppImage veya Flatpak yaklaşımını resmi belgelerle değerlendir ve kararını yaz. Diğerini daha sonra eklenebilir olarak belgele. Sadece Python kaynak kodunu paket varmış gibi sunma. Docker zorunlu olmasın.

Desktop entry, ikon, sürüm, uygulama kimliği, dosya açma ve kullanıcı veri/cache/log dizinleri için XDG uyumu oluştur. Paket içindeki bağımlılıklar, Qt plug-in'leri, QML modülleri, font/rapor export ve process worker'ları gerçek paketten çalıştır. Flatpak seçilirse dosya portalı/izinleri; AppImage seçilirse glibc/host uyumluluk sınırlarını belgele. Wayland/X11 ve yüksek DPI uygun ortamlarda kontrol et.

Debian/Pardus ailesi ve Arch/CachyOS ailesi için mevcut gerçek test ortamlarında smoke test yap. Ortam yoksa test edilmedi yaz; dağıtım logosu kullanarak destek iddiası üretme.

Lisans seçimini açık proje kararı olarak kaydet; bağımlılık lisans yükümlülüklerini, Qt dağıtım gerekliliklerini ve third-party notices dosyasını tamamla. README, GUI kullanım rehberi, örnek veri, katkı rehberi, hata raporu şablonu, CHANGELOG ve bilinen sınırlamalar olsun. CI'da anlamlı test/lint/paket kontrolü kur; yeni release yayınlama ayrı açık kullanıcı talebine bağlı kalsın.

Kabul: En az bir paket gerçekten üretilip temiz uygun ortamda başlatılmış; paket GUI'de import → temizlik → grafik → rapor akışını tamamlıyor; çalıştırılan dağıtım testleri listeli. Test edilmemiş platform uyumunu garanti etme.

Ek kabul politikası: Paket üretilmemiş veya temiz hedef ortamda başlatılmamışsa faz engellidir; yalnız engelin belgelenmesi dağıtım adayı kabulü sağlamaz. İnternetsiz çalıştırma ve internetsiz kurulum ayrı ayrı destekli/doğrulanmadı olarak raporlansın. Faz 21–23 erteleme kararları release kapsamına yansısın. Erken paket smoke testlerinden kalan engeller kapatılmadan dağıtım adayı denmesin.
```

---

## Profesyonel geliştirme ana promptu — Faz 28'den itibaren

```text
Mevcut Veri_Ufku Linux masaüstü veri bilimi uygulamasını profesyonel analiz ve öğrenme platformuna geliştiriyoruz. İlk projenin ana promptu geçerlidir; bu prompt onun devamıdır. Mevcut depoyu, AGENTS.md'yi, ürün/mimari/ilerleme belgelerini oku. Uygulamayı sıfırdan yazma; doğrulanmış özellikleri koru. Veri/proje şeması değişirse sürümlü migration ve yedek kullan.

ÜRÜN
- Başlangıç kullanıcıları ve profesyonel veri bilimciler aynı uygulamada çalışır. Varsayılan görünüm sade; uzman görünüm parametre, varsayım, tanılama, fold/seed ve yöntem ayrıntılarını açar. İki ayrı veri gerçekliği oluşturma.
- Modül araması, favoriler, komut paleti ve amaç odaklı araç keşfi kullan. Yüzlerce seçeneği tek menüye yığma.
- Her analizde uygunluk önkontrolü, parametre seçimi, maliyet/kapsam, önizleme, işlem, sonuç, tanılama, yorum ve export olsun.
- Her yeni grafik/yöntem/modelin çevrimdışı yardım kaydı ve çalışır örneği olsun. Basit açıklama, kullanım koşulları, yanlış kullanımlar, varsayımlar, sonuç okuma, ileri teori ve kaynaklar farklı derinlikte sunulsun.
- Sonuç yanında 'Nasıl hesaplandı?', 'Nasıl yorumlarım?' ve 'Örnekle öğren' erişimi olsun. Öğrenme zorunlu değildir. Derslerin mevcut veri üstünde sessiz işlem yapması yasak; ayrı sandbox proje kullan.
- Yetenekleri kararlı/deneysel/mevcut değil olarak dürüst işaretle. Modül kapalıysa sonuç uydurma. 'Veriye uygun en iyi yöntem' veya nedensellik gibi kanıtlanmamış otomatik iddialar kurma.

MİMARİ
- Mevcut Python/PySide6 analitik/GUI ayrımını koru. Model/view, görev süreçleri, iptal, atomik proje kaydı ve kaynak korumasını bütün modüllerde sürdür.
- Yeni yöntemler için tipli adapter ve capability registry oluştur. InputSchema, AnalysisSpec, ResultArtifact, ValidationPlan, ComputeBudget, LearningLink ve Provenance sözleşmeleri kullan.
- Ağır uzmanlık paketleri optional extras veya doğrulanmış worker ortamlarında olsun. GPU veya model ağırlığı eksikliği temel uygulamayı çökertmesin. Uyumlu sürümleri resmi belgelerden doğrula; lisans/model veri kullanım koşullarını kaydet.
- Her modülün veri boyutu, dtype, sparse/dense, ağırlık, missing, group/time, determinism, predict/proba/interval, serialization ve CPU/GPU yeteneklerini gerçek destekle belirt.
- Gerçek GUI yolunu tamamla. Yalnız kütüphane çağrısı veya notebook örneği üretmek fazı bitirmez. Büyük fazı alt görevlere böl; yapılmayanı tamamlandı gösterme.

BİLİMSEL DOĞRULUK
- Analiz birimi, bağımlı gözlemler, ölçüm düzeyi, zaman/grup/coğrafi bloklar ve ağırlıkların anlamını hesaba kat.
- Hipotez, keşifsel/doğrulayıcı amaç, etki büyüklüğü, belirsizlik, çoklu karşılaştırma ve duyarlılık analizi kayıtlı olsun.
- Data leakage önkontrolü bütün learned preprocessing/selection/embedding/tuning/calibration/stacking aşamalarına yayılsın. Eğitim fold'u dışındaki hedef veya gelecek bilgi öğrenilmesin.
- Test kümesi final değerlendirme içindir. İç/dış CV, temporal/group validation, calibration ve conformal calibration ayrımlarını açık modelle.
- Eksik/yanlı/temsilsiz veri, confounding ve seçim yanlılığı çözüldü varsayılmasın. Nedensel yöntem varsayımları sonuçtan ayrı gösterilsin.
- Tahmin olasılığı, frequentist CI, Bayesian credible interval ve prediction interval aynı kavram olarak sunulmasın. Bir yöntemin desteklemediği çıktı uydurulmasın.
- Aynı seed'in tüm donanım/sürüm koşullarında birebir sonuç garantisi olmadığını belirt. Ortam, veri hash'i ve toleransları kaydet.

GÜVENLİK VE ÇALIŞMA
- Dosya/HTML/formül importu kod çalıştırmasın. Özgür Python/SQL/notebook çalıştırma açıkça kullanıcı başlatılan ayrı yetenektir; ayrı process tek başına güvenlik sandbox'ı değildir.
- Credential, token, kişisel veri ve örnek kayıtları log/proje exportuna istemeden koyma. Güvenli model import politikası tüm model ailelerinde korunsun.
- Zorunlu bulut, ücretli servis, Docker, telemetry veya hesap yok. Ağ kaynağı kullanıcı seçimiyle açılır; çevrimdışı işler kullanılabilir kalır.
- Yalnız gönderdiğim fazı uygula. Her fazdan sonra testler, GUI deneme adımları, bilinen sınırlar, yardım kapsamı ve docs/PRO_PROGRESS.md güncellemesi teslim et.
- Testler bilimsel referans, veri bütünlüğü ve kullanıcı akışını doğrulasın. Çalıştırılmayan testi/geçilmeyen kabul ölçütünü başarılı diye raporlama.

Şimdi yalnız aşağıda gönderdiğim profesyonel geliştirme fazını uygula.
```

---

## Faz 28 — Mevcut uygulama denetimi ve profesyonel yol haritası

```text
Faz 28'i uygula. Mevcut uygulamayı, projelerini ve Faz 00–27 kabul ölçütlerini gerçek kod/test/GUI üzerinden denetle. Yeni uzman modelleri henüz ekleme.

docs/PRO_CAPABILITY_MATRIX.md oluştur: veri türü, yöntem, grafik, import/export, GUI, yardım, test, serialization, kaynak sınırlaması ve kararlılık durumu. Her satırı kanıtla; belgede yazıyor olması çalıştığı anlamına gelmez. Eksik önceki fazlar için düzeltme listesini önceliklendir.

Bu belgedeki Faz 29–75 için bağımlılık grafiği ve alt iş planı çıkar; sıralı geliştirmenin güvenli olduğundan emin ol. Ağır fazları test edilebilir alt parçalara böl. Büyük kapsamı tek oturumda bitirmeye çalışma. docs/PRO_PRODUCT.md, docs/PRO_ARCHITECTURE.md ve docs/PRO_PROGRESS.md oluştur.

Sade kullanıcı, öğrenen kullanıcı ve uzman için aynı örnek problemin üç ekran akışını tasarla. Önceki davranışları koruyacak regression fixtures ve eski proje dosyaları seç. Veri boyutu/donanım hedeflerini ölçülebilir fakat gerçekçi tanımla.

Kabul: Mevcut durum kanıtlı; yeniden yazım yok; tüm yeni fazlar, bağımlılıklar ve açık eksikler listeli. Önceki kritik veri bütünlüğü/sızıntı sorunları varsa devamdan önce düzeltilmiş. Çözülmeyen kritik sorun varsa faz engelli kalır ve bağımlı geliştirmeye geçilmez.

Ek kapsam: Faz 00–20 ve 24–27 kabul kanıtlarını giriş kapısı olarak denetle. Faz 21–23 ertelendiyse bunlara bağlı profesyonel işleri bağımlılık çözülene kadar engelli tut. Kritik veri bütünlüğü/sızıntı sorunu giderilmediyse engel kaydı aç ve bağımlı geliştirmeye geçme.
Her profesyonel yöntem için zorunlu/isteğe bağlı/ertelendi kapsamını, bağımlılıklarını ve alt iş kimliklerini gereksinim matrisine yaz. Önceden seçilmiş kapsamı değiştirirken kullanıcı kararını kaydet. docs/PRO_CAPABILITY_MATRIX.md teknik yetenek ayrıntılarını ana gereksinim matrisine bağlasın. Yeni çekirdek registry, bütçe veya provenance kopyası kurma; önceki sözleşmeleri genişlet.
```

---

## Faz 29 — Yöntem kayıt sistemi ve profesyonel çalışma alanı

```text
Faz 29'u uygula. Tipli capability registry ve modül keşfi kur; mevcut yöntemleri aynı sözleşmeye kademeli bağla.

Her yöntem için input roles/dtypes, varsayımlar, parametre şeması, maliyet, missing/weights/group/time/sparse destekleri, çıktı türleri, yardım id ve kararlılık tanımla. Kütüphane özelliği var diye uygulamada destekli sayma. Fit/predict/proba/transform/interval/persist yeteneklerini ayrı bildir.

Uzman çalışma alanı: kaydedilen sekmeler, analiz karşılaştırma, komut paleti, favoriler ve parametre presetleri. Parametre değişikliği eski sonucu sessizce güncellemesin; yeni run üret. Metin, tablo, grafik, model ve log artifact'ları ortak sonuç paneline bağla. Başlangıç ekranını seçeneklerle şişirme.

Her sonuçta veri sürümü, filtre, yöntem/sürüm, parametre, seed, hesap kapsamı ve warning görünür. Modül eksik bağımlılıkta anlaşılır etkinleştirme bilgisi göstersin; rastgele shell komutu otomatik çalıştırmasın.

Öğren: yöntem seçimi, parametre, çalışma/sonuç farkı ve uzman görünüm. Kabul: İki mevcut yöntem registry üzerinden GUI'de çalışıyor; eski projeler açılıyor; başlangıç/uzman modu aynı sonuç kimliğini gösteriyor.

Ek kapsam: Faz 01 asgari capability kaydını genişlet; ayrı ve çelişen ikinci kayıt sistemi kurma. Yöntem/parametre sürüm geçişleri için geriye uyumluluk ve bilinmeyen yetenekte salt okunur sonuç gösterimi davranışı tanımla.
```

---

## Faz 30 — Gelişmiş tablo formatları ve dosya kaynakları

```text
Faz 30'u uygula. Adaptör sözleşmesiyle partitioned Parquet/Arrow dataset, Avro, ORC, HDF5 tablo, XML kayıt, sabit genişlikli metin ve SPSS/Stata/SAS içe alma ekle. Büyük işi format başına alt aşamalara böl; yalnız gerçekten doğrulanan formatı destekli işaretle.

Schema evolution, dictionary/category labels, nullable decimal, nested types, timezone ve büyük integer korumasını ele al. İstatistik paketlerindeki user-missing ile system-missing, value labels, ağırlık tanımı ve metadata'yı kaybetme. HDF5 key ve XML kayıt yolu kullanıcı tarafından seçilsin; entity expansion gibi parser risklerini kapat.

Gzip/zip gibi uygun sıkıştırılmış girişlere boyut/satır sınırı ve archive path doğrulaması koy. Çok dosyalı importta kaynak provenance'ı satır/parça düzeyinde izleyebil. Tür çatışmasını sessiz stringleştirme; çözüm önizlemesi göster. Kaynak dosya değişimini algıla.

Öğren: partition, schema evolution, etiketli kategoriler, decimal hassasiyeti. Kabul: Format başına gerçek küçük fixture ve roundtrip/metadata testi; desteklenmeyen varyant açık; büyük dosya önizlemesi sınırlı ve iptal edilebilir.
```

---

## Faz 31 — Veritabanı ve kullanıcı tarafından açılan ağ kaynakları

```text
Faz 31'i uygula. Mevcut salt okunur SQLite'ın yanında PostgreSQL, MySQL/MariaDB, yerel DuckDB; HTTP/REST ve nesne depolama dataset kaynağı için ayrı adaptörler ekle. Bir veritabanı ve bir HTTP kaynağını önce tamamla, kalan adaptörleri alt görevlerle doğrula.

Tablo/şema seçimi, parametreli salt okunur sorgu, limit/preview, timeout, cancel ve snapshot provenance olsun. Salt okunurluğu yalnız SQL metninin SELECT ile başlamasına göre varsayma; bağlantı yetkisi/transaction ile uygula. Credential sistem keyring'inde, exportta referans olsun. Güvenli TLS varsayılanı, gizli alan maskeleme kullan.

API pagination, retry/backoff, rate limit, içerik boyutu, alan eşleme ve HTTP hatalarını yönet. Sonsuz sayfalama/redirect yok. Ağ eylemi açıkça başlatılsın; servis kullanım koşulları ve auth destek sınırı görünür. Temel uygulama internetsiz çalışsın.

Öğren: bağlantı, sorgu, snapshot, API sayfalama, kaynak tazeliği. Kabul: Gerçek uygun test sunucusunda okuma doğrulanmış; secret loglanmıyor; timeout/iptal çalışıyor; kaynak üzerinde yazma yok. Ortamı olmayan connector test edilmiş sayılmıyor.

Ek kapsam: Sayfalı API veya uzun veritabanı okumasında snapshot/tutarlılık seviyesini kaydet. Kaynak aynı anda değişiyorsa tüm çıktıyı tek zamanlı snapshot diye sunma. Retry durumunda yinelenen/atlanan kayıt kontrolü ve kaynak kayıt kimliklerini koru.
```

---

## Faz 32 — Veri sözlüğü, kalite sözleşmeleri ve varlık eşleme

```text
Faz 32'yi uygula. Kolon sözlüğüne anlam, birim, ölçüm düzeyi, ordinal sıralama, valid range, nullable/unique ve foreign-key kuralları ekle. Şema sözleşmesini dataset sürümüyle bağla.

Kurallar satır/kolon/tablo/tablolar arası seviyelerde; uyarı/hata derecesi ve ihlal örnekleriyle raporlansın. Kuralları taşınabilir declarative tarif olarak sakla. Kural ihlalinde dur/karantinaya al/devam et davranışı açık; veri sessizce düzeltilmesin.

Fuzzy kategori eşleme ve entity resolution için aday üretimi, blocking, benzerlik skoru ve manuel onay ekle. Benzer isimleri aynı kişi kabul etme. Kaynak kimliklerle canonical kimlik ilişkisi ve birleşme geri alma korunsun. İnsan onaylarının provenance'ı tutulsun.

Öğren: ölçüm düzeyi, veri sözleşmesi, referans bütünlüğü, fuzzy skor ve yanlış birleştirme. Kabul: Yanlış unit/type ve key ihlalleri yakalanıyor; ordinal sıralama korunuyor; onaysız merge yok; geri alma kaynak kimlikleri geri getiriyor.

Ek kapsam: Faz 07 birim/ölçüm düzeyi metadata alanlarını genişlet; yeniden tanımlama yapma. Entity merge kararları, canonical kimlik değişimi ve geri alma tüm bağlı kayıt/sonuçlarda izlenebilir olsun.
```

---

## Faz 33 — İleri eksik veri, örnekleme ve ağırlıklar

```text
Faz 33'ü uygula. Eksiklik desenleri, missing indicator, eğitim katında KNN/iterative imputasyon ve istatistiksel çıkarım için multiple-imputation yolu ekle. Tek doldurma sonucu ile çoklu doldurmayı ayrı tut; uygun parametre havuzlaması desteklenen modellerle sınırlı olsun.

MCAR/MAR/MNAR'ı basit örneklerle anlat; gözlenen veriden mekanizma kesin bulundu iddiası kurma. Eksik varsayımı duyarlılık senaryoları göster. İmputasyon yöntemini tüm veride fit ederek CV sızdırma.

Basit rastgele, stratified ve cluster örnekleme; seed ve seçili satır kimlikleri. Frekans, analitik, survey ve sample_weight aynı anlam değildir: kullanıcı tür seçsin, yöntem registry'si destek doğrulasın. Survey strata/PSU ile tasarım etkili SE/CI için doğrulanmış yöntem kullan; yalnız ağırlıklı ortalamayı profesyonel survey inference sayma.

Öğren: eksiklik varsayımları, temsil, örneklem yanlılığı, ağırlık türleri. Kabul: Negatif/eksik ağırlık kontrollü; desteklenmeyen weight reddi; fold izolasyonu; küçük elle hesaplanan ağırlıklı örnek ve multiple-imputation havuzlama doğrulaması.
```

---

## Faz 34 — Çok boyutlu bilimsel veri ve birimler

```text
Faz 34'ü uygula. NetCDF, Zarr ve çok boyutlu HDF5 için xarray benzeri doğrulanmış adapter; dimension/coordinate/variable seçimi, lazy slice ve tabloya dönüşüm ekle.

Zaman/takvim, latitude/longitude, ensemble ve kanal boyutlarını koru. Tüm tensoru tabloya açmadan önce çıktı boyutu/maliyet göster. CF metadata, no-data/fill value, chunk layout ve unit bilgisi kaybolmasın. Tablo kolonlarından multidimensional yapı varmış gibi sonuç uydurma.

Birim doğrulama/dönüştürme için güvenilir unit registry kullan; Celsius gibi offset birimlerinde basit çarpma yapma. İlgili grafik ve analizin seçili slice/aggregation'ını sakla. 2D heatmap ve profil çizgisi; daha ileri hacim render ayrı yetenek olabilir.

Öğren: dimension/coordinate, raster-array farkı, unit dönüşümü, chunk ve slice. Kabul: Küçük 3D fixture'da seçili kesit doğru; metadata roundtrip; lazy slice tam veriyi yüklemiyor; boyut patlaması önkontrolde gösteriliyor.
```

---

## Faz 35 — Profesyonel dağılım ve belirsizlik grafikleri

```text
Faz 35'i uygula. Violin, KDE/yoğunluk, ECDF, rug, strip/swarm, QQ/PP, error-bar/CI band ve missing-pattern grafikleri ekle. Mevcut histogram/boxplot'ı grup/facet ve ağırlık desteğiyle registry üzerinden genişlet.

Her grafikte kullanılan örnekler, bandwidth/bin, normalize biçimi, agregasyon, dışlanan kayıtlar ve n görünür. KDE küçük/sabit örnekte kontrollü; swarm büyük n'de limitli. Error bar standart sapma mı, SE mi, CI mı açık seçilsin; belirsizlik üreten hesabı metadata'ya bağla.

Log/symlog eksen, kategorik sıra, renk paleti, font, annotation ve export DPI ayarları olsun. Log eksende sıfır/negatif sessiz kaybolmasın. Kırpılmış/yüzde ölçek açık; başlık/eksen düzenlemeleri analitik veri değiştirmesin.

Öğren: density ile sayım farkı, ECDF, QQ, hata çubuğunun anlamı, log ölçek. Kabul: Plot girdileri referans istatistikle aynı; boş/sabit dağılımlar düzgün; PNG/SVG/PDF export okunabilir; her grafik için yardım ve gerçek GUI yolu.
```

---

## Faz 36 — Çok değişkenli, ilişkisel ve yüksek boyutlu görseller

```text
Faz 36'yı uygula. Pair plot/scatter matrix, hexbin/2D density, bubble, grouped heatmap, clustered heatmap, parallel coordinates, facet/small multiples ve koşullu ilişki grafikleri ekle.

Kolon sayısı büyürse hesap/panel patlaması önkontrolü; kullanıcı kolon seçimi ve açık örnekleme. Heatmap ölçek/sıralama/clustering metodu kayıtlı. Bubble boyutunun alanla mı yarıçapla mı değer kodladığını doğru uygula ve legend koy. Kategorik koordinatta yapay sürekli anlam oluşturma.

Brushing/seçim ile ilgili satırları tabloya gösterebil; seçim yalnız görünüm mü filtreli yeni dataset mi açık eylem olsun. Büyük n'de GPU zorunluluğu olmadan aggregation kullan. 3D scatter/surface yalnız ilgili veri/yöntem için optional; perspektif/occlusion sınırını anlat, daha açık 2D seçeneği öner.

Öğren: conditional ilişki, Simpson paradoksu, overplotting, boyut görsellerinin sınırı. Kabul: Seçilen nokta kimlikleri doğru; sample etiketi görünür; facet aynı ölçek davranışı açık; etkileşim export edilen statik çıktıda gerekli bağlamla korunuyor.
```

---

## Faz 37 — Kompozisyon, hiyerarşi, akış ve iş grafikleri

```text
Faz 37'yi uygula. Stacked/100% stacked bar/area, dot/lollipop, waterfall, Pareto, treemap, sunburst, Sankey/alluvial, funnel ve takvim heatmap ekle. Pie/donut yalnız az kategori ve doğru toplam bağlamında seçenek olsun.

Hiyerarşide cycle ve double counting; akışta source/target/value, negatif değer ve dengesiz giriş/çıkış; waterfall'da başlangıç/bitiş/ara değişim doğrula. Funnel için aşama sırası ve kişi/olay tekrarını açıklığa kavuştur. Yüzde payda ve eksiklerin paydaya katılımı görünür.

Radar gibi alan/perspektif açısından yanıltıcı olabilen grafikler advanced seçenek ve açıklamalı alternatifle gelsin; farklı birimleri normalize etmeden aynı eksene yığma. Grafik galerisi türden değil kullanıcı sorusundan da aranabilsin.

Öğren: payda, akış/hiyerarşi, alan algısı, aynı toplamın iki kez sayılması. Kabul: Referans toplamlar doğru; negatif/uyumsuz akış kontrollü; her grafiğin input şeması açık; çalışmayan şekilleri gallery'de hazır gibi gösterme.
```

---

## Faz 38 — Coğrafi veri, haritalar ve mekânsal analiz

```text
Faz 38'i uygula. GeoJSON, GeoPackage, Shapefile bileşenleri ve GeoParquet; koordinat kolonları; GeoTIFF raster için ayrı okuyucu/preview ekle. CRS, geometri türü, extent, nodata ve geçersiz geometri paneli olsun.

Nokta/choropleth/yoğunluk haritası; raster kesit, spatial join, clip, buffer ve mesafe. Geographic derecede metre hesabı yapma. CRS atama ile reprojection ayrı işlemler; area/mesafe için uygun CRS gereksinimini anlat. Koordinat eksen sırası, antimeridian ve matching sınırlarını ele al.

Choropleth sınıflandırma/eşik ve sayım-oran farkı; yerel harita internetsiz görüntülenebilsin. Online tile/geocoding açık kullanıcı seçimi, kaynak/attribution ve cache koşullarıyla. Mekânsal bağımlılık için spatial-block validation; Moran's I gibi desteklenen analizlerde komşuluk ağırlığını açık seçtir.

Öğren: CRS, projeksiyon, mekânsal join, MAUP ve mekânsal sızıntı. Kabul: CRS dönüşümü/mesafe referansı; geometry repair önizlemeli; offline yol gerçek; rastgele split'in mekânsal bağımlılığı çözmediği açıklanmış.
```

---

## Faz 39 — Bağlantılı dashboard ve yayın kalitesinde figür düzenleme

```text
Faz 39'u uygula. Proje içinde dashboard canvas: grafik/tablo/KPI/not, grid yerleşim, global/local filtre, linked brushing, drill-down ve kaydedilen görünüm.

Tüm widget'lar dataset sürümü ve filtre sözleşmesiyle bağlı olsun; farklı veri kaynaklarının filtre eşlemesini kullanıcı seçsin. KPI'ın agregasyonu/payda/önceki dönem tanımı görünür. Grafik çift eksen kullanıyorsa açık uyarı/legend; otomatik yanıltıcı eksen yok.

Figure composer: subplot/facet, ortak legend, renk/typography preset, boyut, vektör/raster export, caption, unit ve kaynak bilgisi. Etkileşimli HTML export için yerel bağımlılık/izinli rendering adapter seç; ağdan JS çekme. Masaüstü GUI'yi web uygulamasına dönüştürme. Statik exportun etkileşimi korumadığını belirt.

Öğren: dashboard sorusu, filtre kapsamı, KPI ve okunabilir figür. Kabul: Filtre/selection satır eşlemesi doğru; reopening layout korunuyor; exportta font/legend/bağlam var; eski sonuçlar güncel veri gibi görünmüyor.
```

---

## Faz 40 — İstatistiksel modeller ve tanılama

```text
Faz 40'ı uygula. OLS/WLS, GLM binomial/Poisson/uygun negative-binomial, quantile regression, mixed-effects ve repeated-measures yollarını doğrulanmış backend ile ekle. Modelleri ayrı alt aşamalarda gerçek GUI ve yardım ile bitir.

Response, predictors, interaction, reference category, offset/exposure ve random/group effects seçimleri anlaşılır. Formül builder güvenli; tam rank, multicollinearity/VIF, residual, heteroskedasticity, overdispersion, influential point ve convergence kontrolleri yap. Robust/cluster SE yalnız yöntem gerçekten destekliyorsa; cluster sayısının sınırını anlat.

Katsayı, uygun transform edilmiş etki/odds ratio, CI, model uyumu ve diagnostic grafikler. AIC/BIC yalnız karşılaştırılabilir model/veri bağlamında; prediction başarısını istatistiksel anlamlılıkla karıştırma. Model tipine uygun tahmin ve save desteğini ayrı işaretle.

Öğren: inference/prediction farkı, link, offset, interaction, random effect, residual. Kabul: Referans stats hesapları; singular/convergence hata; kategorik baseline açık; desteklenmeyen kombinasyon engelleniyor; p-değeri nedensellik kanıtı değil.
```

---

## Faz 41 — Bootstrap, permütasyon, çoklu test ve sağlam analiz

```text
Faz 41'i uygula. Parametrik olmayan bootstrap, percentile/BCa uygunluğu, permutation test, trimmed/robust summary ve multiple-testing düzeltmeleri ekle.

Resampling birimi kullanıcı tarafından gözlem/grup/zaman blok olarak seçilsin. Bağımlı ölçümler rastgele tek satır örneklenmesin. Permütasyon exchangeability ve paired sign-flip bağlamını kontrol et; tüm durumlarda label shuffle uygun varsayma. Seed, tekrar, null hypothesis, tail ve Monte Carlo belirsizliği kayıtlı olsun.

Holm/Bonferroni/BH gibi düzeltmelerde test ailesi açık seçilsin. Düzeltme yönteminin error-control anlamını öğret. Eksik/sabit bootstrap dağılımında sahte CI üretme. Duyarlılık karşılaştırması: filtre, outlier politikası, missing varsayımı ve alternatif yöntem; sonuç değişikliğini görünür yap.

Öğren: resampling, exchangeability, FWER/FDR, robust ölçü ve p-hacking. Kabul: Küçük exhaustive permutation referansı; cluster bootstrap kimlik testi; seed yeniden üretimi; analiz ailesi exportta kayıtlı.
```

---

## Faz 42 — Deney tasarımı, A/B testi ve güç analizi

```text
Faz 42'yi uygula. Ölçüm/hipotez planı, birincil metrik, minimum detectable effect, alpha/power ve uygun sample-size hesapları ekle. Basit randomize iki grup senaryosunu önce tamamla; paired/cluster/factorial varyantlar ayrı alt işler olsun.

Random assignment ve analiz birimi ayrı; seed ile assignment listesi üretilebilir ama gerçek kişilere otomatik mesaj/atama yapma. Allocation, baseline, guardrail metrics, sample-ratio mismatch ve attrition kontrolü. Oran/ortalama, mutlak/göreli etki, uygun CI; intention-to-treat ile per-protocol ayrımı.

Repeated peeking için sabit ufuk testini güvenli sequential sanma. Sequential monitoring ancak doğrulanmış alpha-spending/e-value gibi açık yöntem ve varsayımla ayrı modda; aksi durumda özelliği kapalı belirt. Power hesabında effect varsayımı ve design effect kayıtlı olsun.

Öğren: randomization, güç, MDE, durdurma kuralı ve başarısız ölçüm. Kabul: Analitik referansla örneklem hesabı; SRM fixture; oran paydası doğru; deney dışı gözlemsel veriye randomize etiket koymuyor.
```

---

## Faz 43 — Bayesçi analiz ve model kontrolü

```text
Faz 43'ü uygula. Optional doğrulanmış Bayes backend ile beta-binomial, normal mean ve Bayesian linear/hierarchical regression şablonları ekle. Serbest model programı ileri kod alanına bırak; başlangıç kullanıcıya kontrolsüz probabilistic script sunma.

Prior seçimi, ölçek/birim, prior predictive preview; sampling bütçesi/chains/warmup/seed; posterior summary, credible interval, posterior predictive checks. R-hat, ESS, divergences ve trace gibi diagnostics sonuçla birlikte; convergence sorununda 'güvenilir' rozeti verme. Posterior olasılığı ve frequentist p farklı.

Model karşılaştırma LOO/WAIC için log-likelihood ve diagnostic koşullarını doğrula; uyarıların üstünü örtme. Prior sensitivity, posterior predictive ve model misfit raporları. Büyük chain artifact'ları chunk/compression ile sakla; safe data serialization, kullanıcı kodu import değil.

Öğren: prior/posterior, credible interval, MCMC ve predictive check. Kabul: Conjugate küçük referans; sampler iptal; diagnostic fail görünür; CPU ile küçük örnek offline çalışıyor.
```

---

## Faz 44 — Nedensel çıkarım ve varsayımların görünürlüğü

```text
Faz 44'ü uygula. Treatment/outcome/covariate, zaman ve analiz birimi seçimi; DAG editor ve identification/assumptions paneli. DAG çizmek nedensellik kanıtı değildir; collider/mediator/confounder rolü kullanıcı gerekçesiyle kaydedilsin.

Önce randomize deney ATE ve gözlemsel adjustment/IPW/AIPW yolları; sonra matching, difference-in-differences ve uygun IV şablonları ayrı alt aşamalar. Her birinde consistency, exchangeability/unmeasured confounding, positivity ve yönteme özgü koşullar göster. Propensity overlap/balance, extreme weights, DiD parallel-trend değerlendirmesi ve IV validity sınırları açık.

Cross-fitting gerekiyorsa bölme planına bağla. Sensitivity/placebo kontrolleri ve tanımlanamayan sorular için 'bu veri/varsayımla belirlenemiyor' sonucu. 'En etkili neden' şeklinde otomatik feature importance çevirisi yok.

Öğren: association/causation, DAG, ATE, propensity ve tanımlama. Kabul: Bilinen sentetik causal fixture; positivity sorunu görünür; matching satır eşlemesi doğru; rapor varsayımları ve alternatif açıklamaları saklıyor.
```

---

## Faz 45 — Sağkalım ve olay zamanı analizi

```text
Faz 45'i uygula. Duration/event ve isteğe bağlı entry/group seçimi; censoring türleri ve zaman birimi doğrulaması. İlk kapsam right-censoring; left truncation/interval censoring/competing risk destekleri backend bazında ayrı olsun.

Kaplan–Meier ve risk table, log-rank, Cox proportional hazards ve uygun AFT modeli. Hazard ratio ile event probability ayrımı; PH diagnostics, ties, event azlığı ve separation/convergence kontrolleri. C-index ve zaman-bağımlı/Brier metrikleri yalnız uygun censoring işleme ile.

Competing risks için cumulative incidence yolu; KM complement'i her koşulda event incidence diye sunma. Time-dependent covariate formatını ayrı şema olarak doğrula. Prediction ve model persistence yeteneklerini registry'ye işle.

Öğren: censored kayıt kayıp veri değildir, risk set, hazard, survival probability. Kabul: Küçük referans KM eğrisi; negatif süre/invalid entry reddi; risk sayıları doğru; desteklenmeyen censoring yöntemi kapalı.
```

---

## Faz 46 — Boyut indirgeme ve özellik seçimi

```text
Faz 46'yı uygula. PCA/incremental PCA, truncated SVD, NMF, ICA; görsel keşif için t-SNE ve optional UMAP ekle. Yöntemleri ayrı amaçlarla göster: model girdisi, kompresyon ve yalnız görsel keşif.

Scaling, non-negative gereksinim, missing, sparse dönüşüm, fit kapsamı, explained variance, loadings ve yeniden yapılandırma hatası uygun şekilde. t-SNE/UMAP grafiğindeki uzaklık ve küme yorumlarının sınırını öğret; olmayan explained variance üretme. Yeni veri transform yalnız yöntem destekliyorsa.

Variance filter, model-based, univariate ve RFE/sequential selection yolları; hedef kullanan selection iç CV pipeline'ında. Feature selection stabilitesini fold'lar arasında karşılaştır. İki boyut görünümüne göre test etiketlerini seçmeye teşvik etme.

Öğren: latent boyut, loading, sparse SVD, selection leakage. Kabul: Fold izolasyonu; non-negative kontrol; inverse/transform yetenekleri dürüst; görsel embedding sonucu gerçek sınıf diye etiketlenmiyor.
```

---

## Faz 47 — Gelişmiş kümeleme, yoğunluk ve anomali yöntemleri

```text
Faz 47'yi uygula. Agglomerative/dendrogram, Gaussian mixture, OPTICS ve uygun optional HDBSCAN; DBSCAN/KMeans'i aynı karşılaştırma altyapısına bağla. Distance metric, linkage, cluster/noise ve ölçek kararları kayıtlı.

Silhouette, Davies–Bouldin, Calinski–Harabasz; GMM AIC/BIC; yeniden örnekleme stabilitesi. Metrikleri evrensel gerçek küme sayısı olarak sunma. Mixed-type veride desteklenen mesafe/temsil açık; Euclidean ölçüyle kategori kodunu doğal uzaklık sayma.

LOF, OneClassSVM, robust covariance ve novelty/outlier ayrımı. LOF fit_predict ile novelty predict aynı davranış değildir. Eğitim kapsamı, contamination/eşik ve score yönünü açıkla. Etiketli anomaly varsa PR ve maliyet tabanlı değerlendirme; yoksa başarı iddiası yok.

Öğren: yoğunluk, soft membership, novelty ve cluster stability. Kabul: Model başına destek testi; noise/single cluster edge case; skor yönleri tutarlı; n² distance maliyeti önkontrolde.
```

---

## Faz 48 — Profesyonel tabular model kataloğu

```text
Faz 48'i uygula. Regresyon/sınıflandırmaya ElasticNet/Lasso, SGD, decision tree, ExtraTrees, gradient/hist-gradient boosting, SVM/SVR, KNN, Naive Bayes; optional XGBoost/LightGBM/CatBoost adaptörleri ekle. Her aileyi alt görev halinde tamamla.

Sparse/dense, scaling, categorical/NaN, imbalance, weights, multioutput, predict_proba ve GPU desteğini model özelinde doğrula. Native categorical destek varsa sırf ortak API için bilgi kaybettiren encoding yapma. Ranking objective ayrı grup şemasına bağlansın, sıradan sınıf hedefi sayılmasın.

Bagging/voting ve stacking; stacking meta-modeli out-of-fold prediction öğrenmeli. Feature isimleri, label mapping ve safe persistence destek tablosu. Mevcut modeli koru, tek 'en iyi' algoritma önermeye çalışma. CPU/bellek maliyeti ve convergence tanılaması sun.

Öğren: regularization, boosting, kernel, bias/variance ve ensemble. Kabul: Her destekli ailede gerçek train/evaluate/predict GUI yolu; uygun preprocessing; desteklenmeyen save açık; baseline ve aynı validation planıyla karşılaştırma.
```

---

## Faz 49 — Hiperparametre araması ve bütçeli AutoML

```text
Faz 49'u uygula. Grid/random search ve optional Bayesian optimization; zaman/trial/bellek/concurrency bütçesi, önkoşullu arama uzayı, metric/secondary constraints ve trial history.

İç CV tuning ve dış CV değerlendirme ayrımı; time/group fold planı tüm trial'larda korunmalı. Preprocessing, selection ve resampling trial fold içinde. Final test dışarıda. Learning/validation curves, early stopping ve pruning yalnız ayrılmış validation görsün.

Trial fail/cancel/prune/resume durumlarını ayrı sakla; seed/arama uzayı/ortam değiştiğinde resume uyumunu doğrula. AutoML başlangıç önerisidir, optimum garantisi yok. Stacking veya calibration arama içindeyse ekstra veri bölmesi/maliyet anlaşılır olsun.

Öğren: hyperparameter, nested CV, trial, overfitting to validation ve budget. Kabul: Sızıntı testleri; iptal devamı mevcut sonucu bozmuyor; test skoruyla arama yönlenmiyor; küçük bounded arama gerçekten tamamlanıyor.

Ek kapsam: Bütün trial, pruning ve resume yolları birleşik grup/zaman validation planını ve kalıcı final test kullanım kaydını korusun. Yeni arama açılması test kullanım geçmişini sıfırlamasın.
```

---

## Faz 50 — Kalibrasyon, tahmin belirsizliği ve karar eşikleri

```text
Faz 50'yi uygula. Reliability diagram, log-loss/Brier ve sigmoid/isotonic calibration; Brier'ın kalibrasyonu tek başına ölçmediğini anlat. Calibration train-fit verisinden bağımsız veya uygun CV ile; time/group yapısını bozma.

Validation üstünde maliyet/precision/recall constraint eşik seçimi; testte final rapor. Binary/multiclass farkı, calibration n ve unseen class kontrolü. Model paketine calibrator ve threshold ekle.

Regresyonda quantile prediction ve desteklenen conformal prediction interval; sınıflandırmada conformal prediction sets. Train/calibration/test ayrımı, exchangeability varsayımı, coverage/width veya set size ölçümü. Nominal coverage'ı her alt grupta/gelecek dağılımda garanti etme. CI ile predictive interval ayrı.

Öğren: güvenilir olasılık, karar maliyeti, coverage, prediction set ve belirsizlik türleri. Kabul: Kalibrasyon sızıntısı testi; label order doğru; empirical coverage raporlu; desteksiz modelde interval uydurulmuyor.
```

---

## Faz 51 — Açıklanabilirlik, hata dilimleri ve adalet değerlendirmesi

```text
Faz 51'i uygula. Permutation importance, PDP/ICE ve doğrulanmış optional SHAP adapter; global/local açıklama, background dataset ve transformed-to-original feature mapping.

Correlated features, extrapolation, missing ve explainer approximation sınırları görünür. SHAP katkısı neden-sonuç değildir. Büyük açıklamada sample/budget kayıtlı; bazı modeller desteklenmiyorsa açık.

Hata dilimleri: grup, zaman, sınıf, sayısal aralık; n, metrik ve belirsizlik. Korunan/hassas nitelikleri kullanıcı açıkça seçer; grup eşitsizliği raporu ve uygun fairness metriklerinin trade-off'u. Tek metrikle 'adil model' rozeti yok. Slice keşfi çoklu arama etkisi ve küçük gruplarda güvenilmezlik belirt.

Actionable counterfactual yalnız constraints/immutable features ile optional; gerçekleşebilirlik veya nedensel etki garantisi verme. Basit what-if tahminini causal counterfactual diye isimlendirme.

Öğren: explanation/causation, correlated feature, subgroup ve fairness sınırları. Kabul: Feature mapping kontrolü; local açıklama referansı; küçük grup raporu; hassas veri export maskelemesi.
```

---

## Faz 52 — Deney takibi ve model kayıt sistemi

```text
Faz 52'yi uygula. Yerel experiment registry: run id, dataset/lineage, code/config/ortam hash, split, params, seeds, metrics, duration, artifact, warnings ve tags. Karşılaştırma aynı evaluation protocol değilse uyar.

Model registry sürüm, aday/seçili/arsiv durumu, model kartı, training lineage ve safe artifact saklama. Durum değişimi otomatik dış deploy değildir. Metrik seçimi/threshold/kalibrasyon değişikliği yeni run veya açık revision üretsin.

Run search/filter, karşılaştırma tabloları, fold dağılımları ve Pareto maliyet/başarı görseli. Optional açık tracking backend entegrasyonu yalnız kullanıcı seçimiyle; yerel çekirdek bağımsız. Artifact bütünlük hash'i, immutable metadata ve disk quota politikası olsun; silme veri kaybını açıklasın.

Öğren: run/model/version, aynı test protokolü ve reproducibility. Kabul: Aynı dataset farklı split karşılaştırması işaretli; eski artifact bozulması yakalanıyor; export secrets içermiyor; iptal run'ı başarılı görünmüyor.

Ek kapsam: Faz 16 test kullanım defterini ve temel run kimliklerini experiment registry ile ilişkilendir; mevcut kayıtları kaybetme. Karşılaştırma protokolü, veri erişim zamanı ve testin önce görülmüş olması görünür olsun.
```

---

## Faz 53 — İleri zaman serisi ve panel tahmin

```text
Faz 53'ü uygula. Seasonal decomposition/STL, ACF/PACF, stationarity testleri, ARIMA/SARIMA/SARIMAX, uygun VAR ve change-point/forecast diagnostics modülleri. Testlerin tek başına durağanlık kanıtı olmadığını anlat.

Çoklu seri/panel için yerel/global tahmin, bilinen gelecek covariate ile yalnız geçmişte bilinen değişken ayrımı. Rolling-origin, gap/embargo gerektiğinde, ufuk bazlı MAE/RMSE/MASE; MASE denominator yalnız eğitim dönemi. Probabilistic forecast için coverage/pinball/uygun skor.

Hierarchical reconciliation, intermittent demand ve time-series classification/clustering ayrı alt yetenekler. Backend desteklerini resmi belgelerden kontrol et; örnek bazlı tabular split'i tüm seri parçalarına uygulama. Anomaly/change point ile predictive başarı farklı.

Öğren: differencing, exogenous, forecast horizon, hierarchy ve regime change. Kabul: Gelecek covariate sızıntısı testi; seasonal baseline; panel kimliği korunuyor; model/ufuk başına gerçek backtest raporu.
```

---

## Faz 54 — Sinyal işleme, sensör ve frekans analizi

```text
Faz 54'ü uygula. Düzenli sampling rate, kanal ve zaman birimiyle sinyal şeması; resampling, detrending, window, FFT, Welch PSD, STFT/spectrogram, peak ve güvenilir filtreleme.

Nyquist/aliasing, amplitude/power normalization, filter cutoff/order ve phase delay açık. Zero-phase ileri/geri filtreleme geleceği kullandığı için online prediction yolunda yasak veya açık offline-only. Kanal grupları ve event segmentation kaynak zaman kimliğini korusun.

Feature extraction ve classification için kişiye/cihaza/oturuma göre split; aynı sinyalin overlap window'ları train/test arasında sızmasın. Düzensiz sampling'de standard FFT doğru kabul edilmesin; uygun özel yöntem varsa ayrı.

Öğren: sample rate, frequency, window, spectrum ve offline/online filtre. Kabul: Bilinen sinüs peak/amplitude referansı; aliasing önkontrol; overlap sızıntı testi; GUI spectrogram okunabilir ve iptal edilebilir.
```

---

## Faz 55 — İleri NLP, arama ve metin etiketleme

```text
Faz 55'i uygula. TF-IDF altyapısını NMF/LDA topic exploration, local embeddings/semantic search, NER ve uygun sentiment/classification adaptörleriyle genişlet.

Dil/model/dataset/model-license, training assumptions ve özellikle Türkçe destek açık. Model ağırlıkları kullanıcı isteğiyle indirilebilir veya yerel klasörden seçilebilir; offline cache/hash ve download size göster. Model adıyla kalite garantisi verme.

Topic naming insan düzenlemesi; NER offset/orijinal metin eşlemesi; semantic cosine score'u kalibre probability diye sunma. Annotate/review/export, label schema ve train/validation/test ayrımı. Etiket düzeltmeleri versioned; pretrained model çıktısını ground truth sayma.

Active-learning önerisi training unlabeled pool'dan; test etiketlerini seçme sürecine karıştırma. Retrieval evaluation varsa gerçek relevance etiketleri gerekir; yoksa başarı skoru uydurma.

Öğren: topic/label, embedding, offset, annotation ve model dili. Kabul: Türkçe offset fixture; yanlış dil görünür; model yoksa açıklamalı durum; offline yerel model yolu gerçek.
```

---

## Faz 56 — Derin öğrenme çalışma motoru

```text
Faz 56'yı uygula. Optional PyTorch benzeri doğrulanmış backend; dataset loader, tensor schema, device, training loop, checkpoints, gradient/epoch/batch/lr, early stopping ve resource budget.

Önce küçük MLP tabular ve bir örnek CNN şablonu; mevcut sklearn baseline ile karşılaştır. CPU çalışma şartı; GPU opsiyonel, VRAM kontrolü ve mixed precision yeteneklerine göre. Determinism ayarı/limitleri, framework/CUDA sürümü ve seed kaydı. Aynı seed her cihazda birebir garanti değildir.

Train/validation curves, optimizer/scheduler, class weights ve augmentation yalnız train. Pretrained weight import güvenli politika; arbitrary object checkpoint otomatik deserialize edilmesin. Pause/resume gerçekten aynı optimizer/scheduler durumunu gerektirir; yalnız weight reload'ı tam resume diye sunma.

Öğren: tensor, epoch/batch, loss, gradient, learning rate ve overfitting. Kabul: Küçük CPU training gerçek; cancel/checkpoint; validation training'e karışmıyor; güvenli destekli model kaydı ve yeni data prediction.
```

---

## Faz 57 — Görüntü verisi, annotation ve bilgisayarlı görü

```text
Faz 57'yi uygula. Yerel görüntü klasörü/manifest, sınıf etiketi, bounding box ve mask şemaları; görüntü boyutu, kanal, orientation, corrupted file ve duplicate/near-duplicate kontrolü.

Önce classification/transfer learning yolu, sonra detection ve segmentation ayrı alt aşamalar. Group/subject/video-source bazlı split; yakın kopyaların train/test'e dağılmasını önle. Resize/crop/normalization ve augmentation preview kayıtlı.

Classification confusion; detection IoU/mAP threshold ve matching; segmentation IoU/Dice pixel/class aggregation açık. Annotate/review/export ve model ön etiketini insan etiketiyle ayır. Saliency'yi nedensel açıklama diye sunma. Video frame import kaynak/sequence kimliğini korusun, tüm video analizini varmış gibi iddia etme.

Öğren: bbox/mask, augmentation, IoU, duplicate leakage. Kabul: Görüntü/etiket eşlemesi; metric referansı; CPU küçük örnek; bozuk/çok büyük resim kontrollü; model download isteğe bağlı.
```

---

## Faz 58 — Ses verisi ve ses analizi

```text
Faz 58'i uygula. WAV/FLAC gibi doğrulanmış formatlar; sample rate/channel/duration, waveform/spectrogram, clipping/silence kalite kontrolü ve kontrollü resampling.

MFCC/log-mel feature, audio classification ve kullanıcı tarafından seçilen yerel speech-to-text backend optional. Konuşmacı/oturum/kaynak kayıt bazlı split; aynı kaydın segmentleri bölümler arasında sızmasın. Augmentation yalnız eğitimde ve ses düzeyi/sampling anlamı korunarak.

Transkript timestamp ve confidence yalnız backend sağlıyorsa; WER/CER gerçek referans metni varsa. Speaker diarization ve event detection ayrı yetenek; transcription var diye destekli sayma. Ses dosyası/konuşma loglara yazılmasın; mikrofon canlı kayıt ayrı açık eylem ve kapsam olsun.

Öğren: spectrogram, MFCC, resampling, WER/CER ve konuşmacı sızıntısı. Kabul: Bilinen sinyal feature; speaker split; dosya/segment kimliği; yerel küçük model yoksa açıklamalı unavailable; internet zorunluluğu yok.
```

---

## Faz 59 — Öneri sistemleri ve sıralama

```text
Faz 59'u uygula. User/item/interaction/time şeması; explicit rating ve implicit event farkı. Popularity baseline, content similarity ve matrix-factorization başlangıç yöntemleri; learning-to-rank ayrı query/group yoluna bağla.

Temporal/leave-last-out değerlendirme, negative sampling varsayımı ve candidate universe. Precision/Recall/NDCG/MAP@K; coverage/diversity/cold-start. Full-catalog ile sampled candidate metriğini karşılaştırılabilir sanma. Tek kişiye ait future event eğitimde olmasın.

Seen-item filtresi, kullanıcı/item kimlik eşleme ve yeni kullanıcı/ürün fallback'ı. Recommendation score'u click probability diye yorumlama. Offline ranking skoru gerçek kullanıcı faydasının kesin ölçümü değildir. Yeni öneri listeleri güvenli dışa aktarılır; gerçek kullanıcıya otomatik gönderilmez.

Öğren: implicit feedback, top-K, negative sample ve cold start. Kabul: Elle hesaplanan ranking metric; unknown ids fallback; timestamp leakage kontrolü; kaynak kimlik doğru korunuyor.
```

---

## Faz 60 — İlişkilendirme kuralları, kohort ve süreç analizi

```text
Faz 60'ı uygula. Transaction/basket şeması, frequent itemsets ve Apriori/FP-growth benzeri doğrulanmış backend; support/confidence/lift ve minimum support/budget.

Rule listelerinde çoklu keşif/yanlış ilişki sınırı; support denominator/transaction duplicate davranışı. Kural causality değildir. Yüksek item cardinality önkontrolü ve iptal; metricleri elle hesaplanan örnekle doğrula.

Cohort/retention ve event funnel: cohort başlangıcı, dönem sınırı, timezone, kişi/olay birimi ve right-censoring. Tam gözlem süresi olmayan kohortlar eşit karşılaştırılmasın.

Process mining için case/activity/timestamp şeması, event ordering, directly-follows graph ve uygun conformance adapter. Aynı timestamp tie ve incomplete trace belirli davranış. Süreç grafiği nedensel DAG olarak etiketlenmesin.

Öğren: support/lift, retention paydası, case/event, trace. Kabul: Basket total doğru; küçük cohort reference; eksik trace açık; süreç modeli gerçek hesap, süs görseli değil.
```

---

## Faz 61 — Ağ ve graf verisi

```text
Faz 61'i uygula. Edge/node tabloları, GraphML/GEXF gibi doğrulanmış formatlar; directed/undirected, weights, multi-edge, self-loop ve disconnected graph şeması.

Degree/centrality, connected components, shortest paths ve community detection; graph visualization/filtre/layout. Weight distance mı güç mü kullanıcı seçsin; yanlış anlamla shortest path hesaplama. PageRank/centrality önem veya nedensel etki kanıtı değildir.

Büyük graph'ta görsel node/edge bütçesi ve sample açık. Link prediction optional: negative edges, temporal split ve unseen nodes; graph feature'larının future edges'i görmesini önle. Network embedding ile clustering ayrı eğitim kapsamı.

Öğren: edge/node, direction, centrality/community, connectivity ve graph leakage. Kabul: Bilinen küçük graph referansı; unreachable path kontrollü; multi-edge dönüşüm kaybı açıklamalı; export identities korunuyor.
```

---

## Faz 62 — Streaming, online ve özel öğrenme hedefleri

```text
Faz 62'yi uygula. Dosya append/event stream simülatörüyle bounded buffer, event/processing time, late events, window ve checkpoint altyapısı. Ağ broker adaptörü ayrı kullanıcı seçimli yetenek.

Incremental scaler/model ve partial_fit destekleri registry ile; test-then-train/prequential evaluation, drift alarmı ve explicit retrain policy. Label delay ve missing feedback kontrolü. Her offline model online değildir; replay reproducibility sınırını kaydet.

Multi-label, multi-output, ordinal hedef, positive-unlabeled/semi-supervised öğrenme ayrı şema/yöntem alt modülleri. Label propagation'da eval/test graph'a dahil edilmenin transductive setting olduğunu açık belirt. Ordinal numeric encoding'i otomatik regression sayma.

Öğren: stream/window, prequential, drift, multi-label ve semi-supervised varsayımlar. Kabul: Deterministik stream fixture; bellek sınırı; test-before-fit doğru; checkpoint sonrası tekrar kayıt politikası; her özel hedef için destekli/eksik durum dürüst.
```

---

## Faz 63 — Profesyonel kod, SQL ve notebook köprüsü

```text
Faz 63'ü uygula. GUI analiz tariflerinden okunabilir Python/SQL üretme; runnable script ve notebook export. Export ham veri/secret gömmesin; env lock ve dataset reference ile yeniden çalışma açıklaması.

İsteğe bağlı kod çalışma alanı: ayrı kernel/process, output capture, timeout/cancel ve resource budget. 'Kod çalıştırma' kullanıcı başlatılan açık eylem; projeyi açmak kod çalıştırmasın. Arbitrary code'a izin verildiğinde ayrı process'in güvenlik sınırı olmadığını açık ürün açıklaması yap; doğrulanmış OS sandbox desteği yoksa güvenli sandbox iddiası yok.

GUI → kod dönüşümü desteklenen işlemlerle sınırlı; rastgele Python'u GUI tarifine kayıpsız çevirdiğini iddia etme. Code cell değişikliği lineage/config hash'e gitsin. Kernel environment bilgi ve optional Jupyter entegrasyonunu masaüstü çekirdeğine bağımlı yapma.

Öğren: kod/GUI eşdeğerliği, notebook state, SQL query ve çalışma ortamı. Kabul: Export script küçük projede eşdeğer sonucu üretiyor; açılışta otomatik kod yok; cancel GUI'yi kilitlemiyor; secret export testi.
```

---

## Faz 64 — Görsel workflow ve başsız batch çalıştırma

```text
Faz 64'ü uygula. Mevcut işlem zincirini typed DAG editor ile genişlet: source, transform, quality, analysis, train, predict ve export düğümleri. Cycle/port/type kontrolü, branch, dependency ve stale result yönetimi.

Cache key veri/config/code/env referanslarıyla; kaynak değişirse invalidate. Failure/retry/idempotency ve kaynak yazma eylemlerinde kontrollü politika. Aynı DAG GUI ve CLI/headless runner'da çalışabilsin. Artifact path çakışması ve geçici dosya temizliği kontrolü.

Batch dataset listesi/parametre sweep, dry-run ve compute budget; local schedule optional, kullanıcı seçimiyle ve açık durum. Çalışma planı uygulama kapalıyken nasıl çalışır belgeli; gerçekleşmeyen schedule'ı başarılı sayma.

Öğren: DAG, dependency, cache, idempotency ve batch. Kabul: GUI/CLI aynı küçük workflow sonucu; cycle reddi; source değişimi cache invalidation; başarısız dal diğer sonucu yanlış güncellemiyor.

Ek kapsam: Her düğüm temel OperationSpec/RowId/provenance/ComputeBudget sözleşmesini kullansın. Cache hit sırasında kaynak/config/yöntem sürümü doğrulaması yapılmadan eski artifact güncel sayılamaz. Batch export aynı kaynak veya başka run çıktısını sessizce ezmesin.
```

---

## Faz 65 — Veri kökeni, ortam ve bilimsel yeniden üretilebilirlik

```text
Faz 65'i uygula. Source→dataset→operation→analysis→model→report lineage graph; hash/URI/version/schema, user decisions, code/params ve package/backend/hardware bilgisi.

Dataset snapshot ve referans farkı, retention ve storage budget. Repro bundle: manifest, config, güvenli artifact, env lock, yöntem/yardım sürümü ve veri erişim şartları; veri inclusion ayrı seçim. Dış secret/file paths redaction önizlemesi.

Re-run verifier exact veya tanımlı numeric tolerance; determinism/unsupported platform sınırları. Seed tek başına reproducibility değil. Migrasyon ve farklı model backend sürümünde safe failure. Reference report ile yeni sonucu karşılaştıran test artifact'ları.

Öğren: lineage, snapshot, environment, tolerance ve araştırma kaydı. Kabul: Rapordan kaynağa izleme gerçek; paket yeniden açıldığında hash doğrulanıyor; değişen veri farkı görülebilir; bundle içinde credential yok.

Ek kapsam: Başlangıçtan beri tutulan veri kökenini grafik ve repro bundle ile genişlet; geçmiş kayıtlar için bulunmayan provenance üretme. RowId ve çok kaynaklı dönüşüm ilişkilerinin destek sınırı görünsün. Re-run toleransları yöntem ve veri türü bazında gerekçeli olsun.
```

---

## Faz 66 — CPU/GPU, disk ve dağıtık hesaplama bütçeleri

```text
Faz 66'yı uygula. Ortak ComputeBudget: RAM/disk/threads/device/time/tasks; thread oversubscription kontrolü ve process görevleri. Profil, join, tuning, explainers ve tensor jobs için ölçüm paneli.

Out-of-core/lazy/chunk desteğini her yöntem bazında belirt. Sparse matrix kontrolsüz dense olmasın. Disk spill quota ve cleanup; GPU transfer/device fallback açık, CPU fallback ile hesap anlamı değişiyorsa belirt.

Optional Dask/Ray gibi backend'lerden ihtiyaçla birini resmi destek üzerinden seç; remote executor kullanıcı açıkça yapılandırır. Veri transfer boyutu/konumu/auth açık; yerel uygulamanın remote'a sessiz veri yollaması yok. Distributed resume/retry tek işlem tam bir kez yapılmış garantisi diye sunulmasın.

Öğren: thread/process, out-of-core, sparse, GPU ve dağıtık maliyet. Kabul: Donanım belirtilmiş benchmark; quota fail güvenli; cancel process temizliği; optional backend yokken uygulama açılıyor; performans iddiaları ölçülü.

Ek kapsam: Temel ComputeBudget sözleşmesini GPU/dağıtık yürütmeye genişlet. Erken faz limitlerini devre dışı bırakma; toplam eşzamanlı süreç ve alt kütüphane thread bütçesini birlikte denetle.
```

---

## Faz 67 — Model izleme ve operasyonel kalite

```text
Faz 67'yi uygula. Yerel batch monitoring: schema/feature/prediction drift, data quality, label delay, performance ve calibration değişimi. Referans/pencere ve thresholds kayıtlı.

PSI/KS/uygun dağılım mesafelerini varsayımlarıyla sun; büyük n küçük farkı anlamlı gösterebilir, çoklu kolon alarmı false positive yaratır. Drift→performans düştü sonucunu otomatik kurma. Gerçek hedef geldiğinde güvenli id eşlemeyle evaluate.

Champion/challenger shadow batch karşılaştırma, rollback referansı ve audit trail. Yeni eğitim kullanıcı onayı/konfigürasyonu ile açık run; silent model overwrite yok. CLI batch scoring ve local API yalnız ayrı opt-in; auth, bind address ve request schema güvenli.

Öğren: data/concept drift farkı, delayed label, shadow evaluation, alarm eşiği. Kabul: Drift fixture; labels yokken başarı uydurulmuyor; API kapalı varsayılan; model rollback gerçek ve lineage korunuyor.
```

---

## Faz 68 — Monte Carlo, duyarlılık ve optimizasyon

```text
Faz 68'i uygula. Distribution-based simulation şablonları, correlated input gereksinimi, seed/draw budget, output quantiles ve sensitivity analizi. Parametre/ölçüm belirsizliği ayrımı ve Monte Carlo error kayıtlı.

What-if senaryoları prediction modeline bağlanabilir; nedensel varsayım yoksa causal etki değildir. Solver adapter ile linear/mixed-integer ve bounded nonlinear optimization yolları: objective, constraints, units, feasibility, status, optimality gap/tolerance ve timeout.

Tahmin modeline göre optimum önerinin model geçerlilik alanı dışına çıkması kontrol edilsin; feasible öneri ile gerçek dünyada uygulanabilirlik ayrı. Simülasyon/optimizasyon mevcut kayıtları veya dış kaynakları değiştirmesin.

Öğren: senaryo, Monte Carlo, sensitivity, objective/constraint ve solver status. Kabul: Analitik bilinen dağılım/LP örneği; infeasible/unbounded doğru; timeout optimum diye gösterilmiyor; raporda input varsayımları var.
```

---

## Faz 69 — Öğrenme laboratuvarı ve uygulamalı ders yolları

```text
Faz 69'u uygula. Mevcut Öğren merkezini ders/uygulama laboratuvarına genişlet; özellikleri öğretmek için ayrı örnek workspace kullan.

Yollar: sıfırdan veri, temizleme, görselleştirme, istatistik, ML, belirsizlik, zaman serisi ve uzman modüller. Prerequisite kavram haritası, arama/sözlük/favori ve isteğe bağlı yerel ilerleme. Kullanıcı okumadan araç kullanabilsin; zorunlu sınav yok.

Her ders: amaç, veri, problem, varsayım, adım, beklenen sonuç, yanlış yorum ve 'kendi verime nasıl uygularım'. Gerçek solver'la mean/median, sampling, CI, overfitting, leakage, calibration ve confounding için kontrollü slider/simülasyon; görsel değerleri uydurma.

Optional self-check çoktan seçmeli/sonuç yorumlama ve açıklamalı feedback; puanı uzmanlık sertifikası gibi sunma. İleri açıklamada denklemler ve kaynak; basit katmanda günlük örnek. İçerik sürümü ve doğruluk review kayıtlı. Tüm modüllerin learning coverage'ını otomatik denetle.

Kabul: Offline ders tamamlanıyor; örnek proje gerçek hesapla sonuç üretiyor; kullanıcının projesi değişmiyor; broken/eksik article id yok; okuma kapatılınca iş akışı devam ediyor.
```

---

## Faz 70 — Profesyonel rapor, dashboard anlatısı ve araştırma notları

```text
Faz 70'i uygula. Rapor builder: bölüm, not, yöntem, varsayım, veri sözlüğü, grafik, tablo, model kartı, belirsizlik, diagnostic ve kaynakça.

Rapor template/preset, Markdown/HTML/PDF ve gerekiyorsa DOCX export; her format gerçek doğrulanan desteğe sahip. Grafik SVG/PDF, tablo CSV/Parquet ve script/notebook paketine bağlantı. Rapor eski dataset/run'a bağlıysa stale işareti; recompute açık kullanıcı eylemi.

Keşifsel ile doğrulayıcı analiz, model seçim protokolü ve test kullanımını belirt. Otomatik anlatı önce deterministik şablon; optional yerel LLM açıklaması doğrulanmış sayısal sonuçlara referans versin. LLM hesap motoru/istatistiksel doğruluk kaynağı olmasın; dış servise veri gönderme ayrı açık seçim.

Öğren: bilimsel rapor, caption, limitations ve sonuç/bulguyu ayırma. Kabul: Türkçe font/sayfa, kaynakça ve artifact eşlemesi; hallucinated metrik yok; offline export; redaction preview.
```

---

## Faz 71 — Ekipler arasında proje aktarımı ve inceleme

```text
Faz 71'i uygula. Önce yerel review/share bundle: tam kopya, redacted örnek veya metadata-only; secret/PII tarama ve inclusion preview. Bu ürün özelliğidir, dışarı otomatik yayınlama değildir.

Proje compare/diff: schema, operation, params, run/metric ve learning notes. İnsan yorumları/review checklist yerel kayıt; artifact değişince eski yorumun bağlamı korunur. Dosya çakışmasında last-write-wins ile veri ezme; açık merge/review davranışı.

Optional ekip sunucusu daha sonra ayrı deployment/identity/permissions tasarımı gerektirir; bu fazda çevrimdışı masaüstüne gizli SaaS ekleme. File lock ve birden fazla process yazma sınırı; SQLite paylaşımlı ağ klasöründe güvenilir çok kullanıcı DB sanılmasın.

Öğren: review, diff, redaction ve veri paylaşımı. Kabul: İki bundle farkı doğru; secret dışarı çıkmıyor; unsupported concurrent edit açık; comment artifact sürümüne bağlı.

Ek kapsam: Faz 04 tek yazıcı kilidini koru; ekip aktarımı çok kullanıcılı ortak yazma yeteneği anlamına gelmez. Bundle açılışında kaynak RowId/ColumnId ve proje kökeni korunmalı; kimlik çakışmaları sessiz birleşmeye dönüşmemeli.
```

---

## Faz 72 — Gizlilik, güvenlik ve veri yaşam döngüsü

```text
Faz 72'yi uygula. PII detection adayları, kullanıcı doğrulaması, masking/pseudonymization ve export redaction. Hash'leme anonimlik garantisi değildir; yeniden tanımlama ve linkage risklerini açıkla.

Şifreli proje storage ihtiyacını tehdit modeliyle değerlendir; güvenilir encryption/key handling kullan, özel kripto yazma. Keys log/manifestte yok; key kaybının etkisi ve recovery davranışı açık. Yerel application history ile değiştirilemez audit kanıtı farklı; desktop log'unu güçlü nonrepudiation sayma.

Retention, artifact/cache cleanup, model/rapor kaynak PII ilişkisi ve deletion scope önizlemesi. Güvenli import/code/plugin/network modelini yeniden denetle. Differential privacy ancak doğrulanmış mekanizma, sensitivity ve toplam privacy budget accounting ile optional ayrı alt modül; rastgele noise ekleyip DP etiketi koyma.

Öğren: PII, pseudonymization/anonymization, retention ve privacy budget. Kabul: Redaction testleri; key/secret log sızıntısı yok; deletion kaynakları istemeden silmiyor; unsupported privacy guarantee yok.
```

---

## Faz 73 — Uzman eklentileri ve açık geliştirme SDK'sı

```text
Faz 73'ü uygula. Yeni importer/transform/stat/model/chart/lesson ekleme SDK'sı; versioned interfaces, capability schema, contract tests ve example plugin.

Plugin discovery manifest üzerinden; uygulama açılırken rastgele eklenti kodu auto-execute edilmesin. Yükleme kullanıcı seçimi, trust/permissions, dependency environment ve uyumluluk kontrolüyle. Python plugin'in process isolation ile güvenli sandbox olduğu iddiası yok; izin modelinin gerçek enforcement sınırını anlat.

Eksik veya çöken plugin temel projeyi bozmasın. Projeyi plugin olmadan açarken ilgili artifact okunabilsin; recompute unavailable. Plugin API de learning id ve method/source provenance gerektirsin.

Öğren: eklenti yeteneği, trusted code ve eksik bağımlılık. Kabul: Küçük gerçek chart veya analysis plugin UI→result→help→save akışı; incompatible API reddi; plugin failure izolasyonu; örnek paket bağımsız contract testten geçiyor.
```

---

## Faz 74 — Profesyonel dağıtım, ortam yönetimi ve kalite matrisi

```text
Faz 74'ü uygula. Mevcut Linux paketini profesyonel modüller için güncelle; core install ve optional extras/worker environments net ayrılmış olsun.

Dependency compatibility/lock, artifact backend sürümü, optional native libs, QML/plugin, GPU driver ve model-cache durum paneli. Environment export/import user approved; paket güncelleme kullanıcı seçimi, doğrulanmış artifact ve rollback planıyla. Tüm modellerin aynı tek Python ortamına sığacağını varsayma.

CPU core dağıtımı offline çalışsın. AppImage/Flatpak seçili yolunda file portal, worker launch, sandbox path ve native/geospatial/deep learning bağımlılıklarını gerçek paketle dene. Pardus/Debian ve CachyOS/Arch test matrisi yalnız gerçekten test edilen sürümleri işaretlesin.

Lisans/model-data notices, açık örnekler, Türkçe/İngilizce docs ve contribution/API rehberi güncel. SBOM/dependency scan ve güvenli release CI; dış release yayınlamak ayrı talep.

Kabul: Temiz ortamdan core paket çalışıyor; optional modül yokluğunda crash yok; eski proje migration; smoke test raporu ve test edilmemiş sistem sınırları dürüst.

Ek kapsam: Çevrimdışı kurulum paketi ve optional extras/model ağırlıklarının yerel dosyadan eklenmesi destekleniyorsa gerçek temiz ortamda doğrula; değilse ayrı yetenek olarak mevcut değil işaretle. Güncelleme uygulaması ile proje şema göçünün geri dönüş sınırlarını ayrı belirt.
```

---

## Faz 75 — Profesyonel sürümün bilimsel ve ürün kabul denetimi

```text
Faz 75'i uygula. docs/PRO_CAPABILITY_MATRIX.md'yi gerçek kod/GUI/testle son kez doğrula. Her faz ve alt yöntemi kararlı/deneysel/eksik sınıflandır; eksik olanı 'tamamlandı' yazma.

Uçtan uca benchmark projeleri: tablo temizlik/grafik; ağırlıklı istatistik; deney/Bayes; regression/classification calibration; spatial/time split; causal/survival; NLP/vision/audio; recommendation/graph; workflow/repro bundle. Tümünü tek aşamada ağır gerçek veriyle yapmak zorunda değil; küçük sentetik alt fixture'larla bilimsel hesap ve gerçek GUI yollarını doğrula.

Metriğin referans değeri, tolerans, veri hash'i, yöntem/ortam ve varsayımı kayıtlı. Train/test/group/time leakage, cancel/crash/data integrity, optional missing dependencies ve model persistence yeniden kontrol. Teknik smoke test ile gerçek yeni başlayan/uzman kullanıcı testini ayrı raporla.

Öğren içerikleri uzman doğruluk review sürecine hazır olsun; yalnız AI yazdı diye onaylı uzman içerik iddiası yok. Performans/uyumluluk erişilebilirlik kanıtlı; kalan sorunlar önem derecesiyle listeli.

Kabul: Kritik bilimsel hata/veri kaybı yok; belgelendirilmiş doğrulanmış kapsam; öğrenme/GUI/hesap/export bütün; dağıtım adayı ve açık kalan uzmanlık alanları raporu. 'Veri bilimindeki her yöntem tamamlandı' iddiası kurma.

Ek kabul politikası: Yalnız seçilmiş sürüm kapsamının bütün zorunlu gereksinimleri kanıtlandığında doğrulandı yaz. Kritik hata bulunmadığı iddiasını test kapsamıyla sınırla. Engelli ve ertelenmiş işler açık listede kalsın; bu durumlar tamamlanma sayılmaz. Gereksinim, ilerleme ve capability matrislerinde çelişkili durum kalmasın.
```

---

## Her fazın ortak tamamlanma kontrolü

Bir yöntem yalnız kütüphanede mevcut olduğu için uygulamanın özelliği sayılmaz. Her destekli yöntemin bu kontrol listesinden geçmesi gerekir:

| Kontrol | Beklenen kanıt |
|---|---|
| GUI | Girdi/parametre→çalıştır→sonuç yolu gerçek |
| Uygunluk | Veri türü, analiz birimi, missing, weights ve varsayımlar doğrulanmış |
| Hesap | Referans örnek ve edge case doğrulaması |
| Değerlendirme | Uygun split/metric/uncertainty, sızıntı kontrolü |
| Öğrenme | Özet, örnek, sınırlar, yorum, teori/kaynak; mevcut yöntemle bağlantılı |
| Kaydetme | Parametre, kaynak, dataset/run sürümü ve yöntem sürümü korunmuş |
| Yeniden çalışma | Desteklenen ortamda eşdeğerlik/tolerans ve açık determinism sınırı |
| Dayanıklılık | İptal, hata, az veri, büyük maliyet, optional dependency yokluğu |
| Export | Tablo/grafik/rapor doğru bağlamla; secret ve PII kontrolü |
| Durum | Kararlı/deneysel/eksik dürüstçe matriste kayıtlı |

Bu kontrol bütün fazlarda uygulanabilir maddeler için geçerlidir. Uygulanamaz maddede gerekçe kaydet; testi çalıştıramamayı uygulanamazlık sayma. Analiz içermeyen mimari/iskele fazından model metriği bekleme.

---

## Faz sonu teslim biçimi

```text
Her faz sonunda şu bilgileri ver:
1. Kullanıcı açısından değişen gerçek davranış.
2. Tamamlanan alt gereksinim kimlikleri ve kod/test/GUI kanıtları.
3. Çalıştırılan kontroller, ortam ve sonuç; çalıştırılmayanlar ayrı.
4. Kısa GUI deneme adımları.
5. Bilinen sınırlamalar, engeller ve kalan alt işler.
6. Faz durumu ve güncellenen gereksinim/ilerleme kayıtları.
Zorunlu madde doğrulanmadıysa fazı doğrulandı sayma. Engel raporu tamamlanma değildir. Kullanıcı istemeden sonraki faza geçme.
```

## Eksik fazı tamamlama promptu

```text
Veri_Ufku için gönderdiğim fazı ana proje kuralları, ilgili faz metni ve gereksinim matrisiyle yeniden karşılaştır. Her yöntem/format/grafik alt maddesinin gerçek GUI, hesap, yardım, kaydetme ve test durumunu kontrol et. Eksikleri alt kimliklerle kaydet ve seçilmiş faz kapsamında tamamla. Gerekli önceki bağımlılık hatalarını ayrı düzeltme kaydıyla gider; sonraki fazları başlatma. Kabul şartlarını sessizce daraltma. Doğrulanmayan kontrolü ve engeli açık bırak; yalnız belge güncellemekle tamamlandı sayma.
```

## Yeni oturumda devam promptu

```text
Veri_Ufku Linux masaüstü veri bilimi uygulamasına devam ediyoruz. AGENTS.md, docs/PROJECT_RULES.md, docs/UI_DESIGN_BRIEF.md, docs/PRODUCT.md, docs/ARCHITECTURE.md, docs/CORE_CONTRACTS.md, docs/ACCEPTANCE_POLICY.md, docs/REQUIREMENTS_MATRIX.md ve docs/PROGRESS.md'yi oku. Profesyonel aşamadaysak ayrıca docs/PRO_PRODUCT.md, docs/PRO_ARCHITECTURE.md, docs/PRO_CAPABILITY_MATRIX.md ve docs/PRO_PROGRESS.md'yi oku. Henüz üretilmemiş belgeyi mevcut varsayma; ilgili faz bağımlılığı olarak kaydet.
Mevcut kodu ve son kanıtları incele; doğrulanmış özellikleri sebepsiz yeniden yazma. Aşağıda göndereceğim fazın zorunlu bağımlılıklarını doğrula. Yalnız bu fazı, kalan alt işlerini ve zorunlu önceki bağımlılık düzeltmelerini uygula. Kaynak dokümandaki diğer fazların varlığı onları başlatma talimatı değildir. Faz durumu, yetenek olgunluğu ve erteleme kararını ayrı tut. Sonuçta gerçek doğrulama kanıtlarını ve kalanları bildir.
```

## Kapsam dışında bırakılan uzmanlıklar

Reinforcement learning ve gerçek ortamda agent kontrolü, federated learning, genomik/omics, medikal görüntü protokolleri, ileri video/multimodal modeller, spatial econometrics, ileri financial econometrics, tam GIS/BI sunucusu ve bulut ölçeğinde gerçek zamanlı serving bu belgenin tamamlanmış ürün vaadi değildir. Gerektiğinde ayrı uzmanlık fazlarıyla eklenir. Bunların yokluğu seçilmiş sürümün zorunlu kapsamını sessizce değiştirmek için gerekçe olamaz.

## Teknik kaynak doğrulama politikası

Bu belge paket sürümlerinin veya API uyumluluğunun doğrulandığı anlamına gelmez. İlgili geliştirme fazında seçilen sabit sürümün resmi belgeleri, lisansı ve gerçek destek matrisi kontrol edilir; erişilemeyen kaynak doğrulanmış sayılmaz. Kullanılan URL, sürüm ve doğrulama tarihi ADR veya yöntem kaydında saklanır. Geliştirme için internet gerekmesi, son kullanıcının temel uygulamasına zorunlu ağ bağımlılığı ekleme gerekçesi değildir.
