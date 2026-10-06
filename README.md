# Veri_Ufku

Yerel Linux masaüstü uygulaması. Faz 02'de tema/görünüm tercihi korunan gerçek Qt Quick uygulama kabuğu ve görev altyapısı kullanılabilir; veri içe aktarma, analiz ve proje kaydı henüz mevcut değil. Görünen ad Veri_Ufku, Python paketi `veri_ufku`, dağıtım/giriş komutu `veri-ufku`.

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
uv run --frozen ruff check src tests scripts
uv run --frozen ruff format --check src tests scripts
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen pytest -q
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen veri-ufku --smoke-test
```

Başsız ekran çalıştırma doğrulandı. Ajan ortamının Wayland/X11 bağlantısı reddedildi. Kullanıcı kendi masaüstünde CPU/I/O ve belirsiz ilerleme iptal/tamamlanmasını denedi; kalan masaüstü kontrollerini de başarılı bildirdi. [Uzak CI koşusu 37500721689](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/actions/runs/37500721689) tüm adımlarıyla başarılı; Faz 01 kabul durumu **doğrulandı**, altyapı olgunluğu deneysel. Sonraki faz başlamadı.

[Ürün](docs/PRODUCT.md), [ekran akışı](docs/UX.md), [mimari](docs/ARCHITECTURE.md), [çekirdek sözleşmeler](docs/CORE_CONTRACTS.md), [fazlar](docs/PHASE_PLAN.md), [gereksinimler](docs/REQUIREMENTS_MATRIX.md), [ilerleme](docs/PROGRESS.md), [geliştirme](docs/DEVELOPMENT.md), [tasarım kuralları](docs/UI_DESIGN_BRIEF.md), [referanslar](docs/UI_REFERENCES.md), [kabul](docs/ACCEPTANCE_POLICY.md), [Faz 01 kanıtları](docs/evidence/PHASE01.md).

GitHub'a ilk gönderim için normal masaüstü terminalinde `bash scripts/publish_github.sh` çalıştırın. Betik GitHub oturumu gerektiğinde tarayıcı doğrulaması başlatır, boş eski .git dizinini yedekler, main dalını gönderir ve CI sonucunu izler. Sanal ortamlar ve yerel loglar gönderilmez. Uzakta farklı bir geçmiş varsa force push yapmaz; hata metniyle durur. Kullanıcı ilk gönderimi normal terminalde tamamladı. İlk CI koşusu başarısız oldu; aynı betik yerel düzeltmeleri yeni commit ile gönderip yeni koşuyu izlemek için tekrar çalıştırılabilir. Ajanın GitHub API bağlantısı hâlâ başarısız.

Faz02: solda Başlangıç/Veri/Hazırla/İncele/Karşılaştır/Model/Rapor/Öğren alanları, üstte proje/veri bağlamı, ortada kaydırılabilir çalışma alanı ve gerektiğinde sağ bilgi paneli. Dosya aç/Örnek veriyle dene henüz mevcut değil; düğme nedenleri görünürdür. Gelecek alanlar yalnız kullanılabilirlik bilgisini açar. Amaç kartları analiz çalıştırmaz.

Tema (açık/koyu/sistem), görünüm (başlangıç/gelişmiş) ve yazı boyutu (%100–200) üstten seçilir ve `XDG_CONFIG_HOME/veri_ufku/ui-preferences.json` içine kaydedilir. Başlangıç görünümü sonuç/hata/iptal bilgisini korur. Bozuk tercih dosyası otomatik ezilmez; görünür uyarı verir. F1 veya “Bu ne işe yarar?” paneli açar; Escape kapatıp odağı geri verir. Tab/ShiftTab, nav okları/Space ve Ctrl+1..8 temel gezinme yollarıdır.

Faz02 [kanıt kaydı](docs/evidence/PHASE02.md): 720×560–1366×900, %100–200 yazı, başsız ve gerçek Wayland GUI kontrolleri; [masaüstü açık ekran](docs/evidence/phase02-desktop-1366-light-1.0-0.png), [koyu ekran](docs/evidence/phase02-desktop-1366-dark-1.0-0.png). Faz02 doğrulandı, olgunluk deneysel; Faz03 başlamadı. Uzak CI bağlantısı yukarıdaki Faz01 commit’ine aittir; Faz02 henüz uzakta çalıştırılmadı.
