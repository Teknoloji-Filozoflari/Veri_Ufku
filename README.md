# Veri_Ufku

Yerel Linux masaüstü uygulaması. Faz 01'de gerçek Qt Quick ekranı ve görev altyapısı kullanılabilir; veri içe aktarma, analiz ve proje kaydı henüz mevcut değil. Görünen ad Veri_Ufku, Python paketi `veri_ufku`, dağıtım/giriş komutu `veri-ufku`.

CPython 3.13.15 ve uv 0.12.23 ile:

```sh
uv sync --locked --group dev
uv run --offline --frozen veri-ufku
```

İlk kurulum Python ve bağımlılıkları indirebilir. İnternetsiz kurulum ancak uyumlu Python ve tüm kilitli paketlerin yerel uv cache'inde bulunmasıyla denenmiştir: `uv sync --offline --locked --group dev`. Tam dağıtım wheelhouse'u henüz yoktur. Uygulama çalışırken ağ istemez. Kurulumdan sonra `.venv/bin/veri-ufku` da aynı giriş noktasıdır.

Ekranda “CPU denemesini başlat” ile ayrı süreçte gerçek deterministik toplamı çalıştırın; “Görevi iptal et” ile durdurun. Görev sürerken yapılandırmayı değiştirin: eski sonuç güncel sonuç alanına yazılmaz. I/O görevi geçici dosyaya yazar ve bitince temizler. Hata denemesi anlaşılır mesaj ve teknik log için takip kimliği gösterir. Bunlar açıkça altyapı denemeleridir.

```sh
uv run --frozen python scripts/check_docs.py
uv run --frozen python scripts/check_artifacts.py
uv run --frozen ruff check src tests scripts
uv run --frozen ruff format --check src tests scripts
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen pytest -q
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run --frozen veri-ufku --smoke-test
```

Başsız ekran çalıştırma doğrulandı. Ajan ortamının Wayland/X11 bağlantısı reddedildi. Kullanıcı kendi masaüstünde CPU/I/O ve belirsiz ilerleme iptal/tamamlanmasını denedi; kalan masaüstü kontrollerini de başarılı bildirdi. Git deposu/remote olmadığı için uzaktaki CI doğrulanmadı; Faz 01 kabul durumu **engelli**, altyapı olgunluğu deneysel. Sonraki faz başlamadı.

[Ürün](docs/PRODUCT.md), [ekran akışı](docs/UX.md), [mimari](docs/ARCHITECTURE.md), [çekirdek sözleşmeler](docs/CORE_CONTRACTS.md), [fazlar](docs/PHASE_PLAN.md), [gereksinimler](docs/REQUIREMENTS_MATRIX.md), [ilerleme](docs/PROGRESS.md), [geliştirme](docs/DEVELOPMENT.md), [tasarım kuralları](docs/UI_DESIGN_BRIEF.md), [referanslar](docs/UI_REFERENCES.md), [kabul](docs/ACCEPTANCE_POLICY.md), [Faz 01 kanıtları](docs/evidence/PHASE01.md).

GitHub'a ilk gönderim için normal masaüstü terminalinde `bash scripts/publish_github.sh` çalıştırın. Betik GitHub oturumu gerektiğinde tarayıcı doğrulaması başlatır, boş eski .git dizinini yedekler, main dalını gönderir ve CI sonucunu izler. Sanal ortamlar ve yerel loglar gönderilmez. Uzakta farklı bir geçmiş varsa force push yapmaz; hata metniyle durur. Bu çalışma ortamından gönderim DNS/oturum engeli nedeniyle gerçekleşmedi.
