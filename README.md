# Veri_Ufku

Yerel Linux masaüstü uygulaması. Faz09 sürümlü işlem motoru, önizleme ve geri alma; Faz08 kalite merkezi ve Faz07 veri tablosu/profil kullanılabilir. Faz 06'da CSV/TSV, JSON, JSONL/NDJSON, XLSX ve Parquet dosya seçme, sürükleyip bırakma, ayarlı önizleme ve doğrulanmış içe aktarma; Faz 04'te proje oluşturma/açma/kaydetme/farklı kaydetme/son projeler; çevrimdışı Öğren merkezi, tema/görünüm tercihi korunan Qt Quick kabuğu ve görev altyapısı kullanılabilir. Analiz yetenekleri henüz mevcut değil. Görünen ad Veri_Ufku, Python paketi `veri_ufku`, dağıtım/giriş komutu `veri-ufku`.

CPython 3.13.15 ve uv 0.12.23 ile:

Ubuntu 24.04'te Qt'nin sistem kitaplıklarını önce kurun: `sudo apt-get update` ve `sudo apt-get install --no-install-recommends -y libegl1 libgl1`. Offscreen/software testleri de bu kitaplıkları gerektirir; Python paket kilidi sistem kitaplıklarını kurmaz.

```sh
uv sync --locked --group dev
uv run --offline --frozen veri-ufku
```

İlk kurulum Python ve bağımlılıkları indirebilir. İnternetsiz kurulum ancak uyumlu Python ve tüm kilitli paketlerin yerel uv cache'inde bulunmasıyla denenmiştir: `uv sync --offline --locked --group dev`. Tam dağıtım wheelhouse'u henüz yoktur. Uygulama çalışırken ağ istemez. Kurulumdan sonra `.venv/bin/veri-ufku` da aynı giriş noktasıdır.

“Altyapı denemeleri” bölümünü açın; “CPU denemesini başlat” ile ayrı süreçte gerçek deterministik toplamı çalıştırın; “Görevi iptal et” ile durdurun. Görev sürerken yapılandırmayı değiştirin: eski sonuç güncel sonuç alanına yazılmaz. I/O görevi geçici dosyaya yazar ve bitince temizler. Üstten Gelişmiş görünümü seçerek yapılandırma/hata denemelerini açın. Hata denemesi anlaşılır mesaj ve teknik log için takip kimliği gösterir. Bunlar açıkça altyapı denemeleridir.

```sh
uv run --frozen python scripts/check_docs.py
uv run --frozen python scripts/check_artifacts.py
uv run --frozen python scripts/check_learning.py
uv run --frozen ruff check src tests scripts
uv run --frozen ruff format --check src tests scripts
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen pytest -q
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen veri-ufku --smoke-test
```

Başsız ekran çalıştırma doğrulandı. Ajan ortamının Wayland/X11 bağlantısı reddedildi. Kullanıcı kendi masaüstünde CPU/I/O ve belirsiz ilerleme iptal/tamamlanmasını denedi; kalan masaüstü kontrollerini de başarılı bildirdi. [Uzak CI koşusu 37500721689](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/actions/runs/37500721689) tüm adımlarıyla başarılı; Faz 01 kabul durumu **doğrulandı**, altyapı olgunluğu deneysel. Sonraki faz başlamadı.

[Ürün](docs/PRODUCT.md), [ekran akışı](docs/UX.md), [mimari](docs/ARCHITECTURE.md), [çekirdek sözleşmeler](docs/CORE_CONTRACTS.md), [fazlar](docs/PHASE_PLAN.md), [gereksinimler](docs/REQUIREMENTS_MATRIX.md), [ilerleme](docs/PROGRESS.md), [geliştirme](docs/DEVELOPMENT.md), [tasarım kuralları](docs/UI_DESIGN_BRIEF.md), [referanslar](docs/UI_REFERENCES.md), [kabul](docs/ACCEPTANCE_POLICY.md), [Faz 01 kanıtları](docs/evidence/PHASE01.md).

GitHub'a ilk gönderim için normal masaüstü terminalinde `bash scripts/publish_github.sh` çalıştırın. Betik GitHub oturumu gerektiğinde tarayıcı doğrulaması başlatır, boş eski .git dizinini yedekler, main dalını gönderir ve CI sonucunu izler. Sanal ortamlar ve yerel loglar gönderilmez. Uzakta farklı bir geçmiş varsa force push yapmaz; hata metniyle durur. Kullanıcı ilk gönderimi normal terminalde tamamladı. İlk CI koşusu başarısız oldu; aynı betik yerel düzeltmeleri yeni commit ile gönderip yeni koşuyu izlemek için tekrar çalıştırılabilir. Ajanın GitHub API bağlantısı hâlâ başarısız.

Faz02: solda Başlangıç/Veri/Hazırla/İncele/Karşılaştır/Model/Rapor/Öğren alanları, üstte proje/veri bağlamı, ortada kaydırılabilir çalışma alanı ve gerektiğinde sağ bilgi paneli. Dosya aç Faz05 ile CSV/TSV için çalışır; Örnek veriyle dene henüz mevcut değil. Veri/analitik için gelecek alanlar kullanılabilirlik bilgisini açar; Öğren Faz03 ile çalışır. Amaç kartları analiz çalıştırmaz.

Tema (açık/koyu/sistem), görünüm (başlangıç/gelişmiş) ve yazı boyutu (%100–200) üstten seçilir ve `XDG_CONFIG_HOME/veri_ufku/ui-preferences.json` içine kaydedilir. Başlangıç görünümü sonuç/hata/iptal bilgisini korur. Bozuk tercih dosyası otomatik ezilmez; görünür uyarı verir. F1 veya “Bu ne işe yarar?” paneli açar; Escape kapatıp odağı geri verir. Tab/ShiftTab, nav okları/Space ve Ctrl+1..8 temel gezinme yollarıdır.

Faz02 [kanıt kaydı](docs/evidence/PHASE02.md): 720×560–1366×900, %100–200 yazı, başsız ve gerçek Wayland GUI kontrolleri; [masaüstü açık ekran](docs/evidence/phase02-desktop-1366-light-1.0-0.png), [koyu ekran](docs/evidence/phase02-desktop-1366-dark-1.0-0.png). Faz02 doğrulandı, olgunluk deneysel; [Faz02 uzak CI](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/actions/runs/37504698665) başarılı.

Faz03: Öğren alanında internet olmadan konu ara, kategori veya sözlük seç; makaleyi açıp Tek cümle / Bir dakikalık örnek / Ayrıntılı rehber derinliklerini dene. F1 ilgili ekran veya odaklı işlemi açıklar; Escape yardımı kapatır. Okundu/yer imi kaydı isteğe bağlı ve yereldir. Yardım rehberindeki Uygulamada dene ayrı geçici örnek öğrenme projesi açar; analitik araçlar henüz mevcut değil. [İçerik ve katkı sözleşmesi](docs/LEARNING_CONTENT.md). Ek CI kontrolü: `uv run --frozen python scripts/check_learning.py`.

Faz03 [kanıt kaydı](docs/evidence/PHASE03.md): 54 test ve gerçek Wayland kontrolü geçti; [Öğren ekranı](docs/evidence/phase03-desktop-search.png). Faz03 doğrulandı/deneysel; [Faz03 uzak CI](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/actions/runs/37511231471) başarılı (Linux38s).

Faz04: Başlangıçtaki Yeni proje → Klasör seç ile var olan bir üst klasör seçin; önerilen Yeni_Proje adını değiştirebilirsiniz. Elle yazarsanız `/home/s-oktay/Belgeler/Projem` gibi kendi kullanıcı klasörünüzde **henüz mevcut olmayan bir proje dizini** belirtin. Proje adı/seed veya yardım derinliğini değiştirin, Kaydet (Ctrl+S), Projeyi kapat ve Proje aç (Ctrl+O) ile aynı dizini açın. Farklı kaydet yeni bir dizinde aktif durumun kopyasını oluşturur; aynı/symlink/mevcut hedefi ezmez. Son projeler listesi açılışlarınızı tutar.

Kaynak dosyası bağla, yalnız referans veya taşınabilir dosya kopyası ekler; dosya içe aktarma/analiz çalıştırmaz ve özgün dosyaya yazmaz. Referans yolu kaybolursa dosyayı ayrıca götürüp Yeniden bağla seçin; yalnız aynı SHA256/boyut kabul edilir. Değişmiş kaynak eski sonuçları güncel yapmaz. Proje metadata açılışı yeniden işleme değildir.

Otomatik kayıt 60 saniyede ayrı kurtarma dalına yazar; manuel kaydı değiştirmez. Kurtarma kaydını yükle ile inceleyip Kaydet seçin. Kapanış kaydedilmemiş değişiklikler için karar ister. İkinci uygulama salt okunur açılır. Temiz kapanmamış projede Önceki kilidi kurtararak aç seçeneğiyle dizini seçin; aktif yazıcının kilidi kaldırılmaz.

[Proje saklama kararı](docs/adr/007-project-store-phase04.md), [Faz04 kanıtları](docs/evidence/PHASE04.md). Yazma yerel Btrfs/ext4, geçici deneme tmpfs içindir; bu oturumdaki dayanıklılık testleri Btrfs/tmpfs üzerindedir. Ağ ve eşzamanlı sync klasörlerinde destek yoktur; güç kesintisi garantisi verilmez. Yeni masaüstü/native dosya seçici ve remote CI kontrolü henüz yapılmadı. Başsız proje ölçümü: `uv run --frozen python scripts/measure_phase04.py`.

Faz05: Önce proje oluşturun/açın. Veri → Dosya seç veya tek CSV/TSV dosyasını bırakın. Algılama önerilerini (ayraç/encoding/başlık) kontrol edin; sayı/null/tarih/saat dilimi ve sütun türlerini seçin. Değişiklikten sonra Aynı kopyayı yeniden önizle; ardından İçe aktar ve projeye kaydet. Bu eylem mevcut proje değişikliklerini de kaydeder. Tüm sütunlar varsayılan metin; leading-zero kimlikler korunur. Bozuk kayıt için Durdur veya Raporlu karantina seçin; sayım ve özgün satır aralığı/sebep saklanır.

Önizleme en fazla200 kayıtlık örnektir. İçe aktarma ekranda zamanı/SHA256'sı görünen doğrulanmış kopyadan yapılır; kaynak sonradan değiştiyse güncel veriyi almak için dosyayı tekrar seçin. Özgün kaynak değiştirilmez. Dataset her durumda Parquet saklanır; isteğe bağlı özgün taşınabilir kopya eklenir. Sınırlar1GiB kaynak/256 sütun/1MiB kayıt; chunk/lazy import, süreç iptali ve atomik proje yayını. Proje şema2; eski şema1 açık kayıt sonrasında migrasyonla2 olur, eski commit korunur. [Karar](docs/adr/008-delimited-import-phase05.md), [kanıtlar](docs/evidence/PHASE05.md). `uv run --frozen python scripts/measure_phase05.py` başsız import/render/iptal ölçümü; gerçek masaüstü/native dosya seçici ve yeni remote CI ayrı doğrulanmadı.

Faz06: Veri ekranında CSV/TSV yanında JSON, JSONL/NDJSON, XLSX ve Parquet dosya seçimi/bırakma. JSON iç içe kayıt yolu ve ayrı düzleştirme/liste açma; Excel sayfa/aralık/formül davranışları; native Parquet tür koruma. Kaynak dosya korunur. [Destek sınırları](docs/adr/009-structured-import-phase06.md), [test/paket kanıtı](docs/evidence/PHASE06.md). Faz07 başlatılmadı.

Faz07: **Veri → Veri tablosu → Tabloyu aç / yenile**. Sütunu seçerek sıralama, filtre, gizleme, rol/birim ve profil kapsamını düzenleyin. Rol/profil taslağı için **Projeyi kaydet** kullanın. Tablo salt okunur; filtre analiz dataset’ini değiştirmez. [Kapsam ve kanıt](docs/evidence/PHASE07.md).

Faz08: **Veri → Veri kalitesi**. Tarama miktarı/kapsamı/amacı seçin; isteğe bağlı tekrar anahtarı ve açık kurallar ekleyin. **Kaliteyi tara**, sonra bulgu gerekçesi ve yardımını inceleyin. **Raporu proje taslağına ekle → Projeyi kaydet** raporu saklar. Tarama ve öneriler veriyi değiştirmez; düzeltme işlemleri henüz mevcut değil. [Kanıt](docs/evidence/PHASE08.md).

Faz09: **Hazırla → Sütunu yeniden adlandır / Sütunu çıkar / Görünüm filtrelerini veriye uygula → Önizle → Uygula ve projeye kaydet**. Filtreyi önce Veri → Veri tablosunda hazırlayın. Önce/sonra tablolar ilk200 kayıttır; etki sayımları tam veri üzerindendir. **Geri al / Yinele** kalıcı sürümleri açar; eski adımın öncesine dönüp yeni işlem oluşturmak eski dalı korur, redo zincirini temizler. Eski sonuçlar güncel değil etiketiyle kalır. Bu eylemler proje taslağını da kaydeder; kaynak değiştirilmez, elle hücre/satır düzenleme seçilmediği için tablo salt okunur kalır. [Faz09 kanıtı](docs/evidence/PHASE09.md).
