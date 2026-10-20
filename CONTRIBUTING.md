# Katkı rehberi

GPL-3.0-or-later kapsamında katkı gönderin. Kullanıcı verisini fixture, log veya hata kaydına koymayın; sentetik örnekler kullanın. Kaynak dosyayı değiştirmeyen, RowId/provenance koruyan işlemler geliştirin. AGENTS.md ve docs/DEVELOPMENT.md sözleşmesini okuyun.

`uv sync --locked --group dev`, `uv run --frozen ruff check src tests scripts`, `uv run --frozen ruff format --check src tests scripts`, `uv run --frozen pytest -q` ve geliştirme belgesindeki belge/öğrenme/paket kontrollerini çalıştırın. Sonucu ortam/tarih/komutla kaydedin. Release yayımlamak ayrı kullanıcı kararıdır.


Faz74: yalnız core geliştirme için `uv sync --locked --group dev`; tam mevcut
regresyon paketleri için `uv sync --locked --group dev --all-extras` gerekir.
Optional backend testleri kurulmadan başarılı sayılmaz. Yeni extras lock/profile ve
license notice güncellemesi ister; `scripts/generate_environment_profile.py` çıktısı
güncel tutulur. [English API/contribution](docs/PLUGIN_API_EN.md),
[dağıtım sınırları](docs/INSTALL_TR.md), [gerçek testler](docs/evidence/PHASE74.md).
CI/release candidate build yayınlama yetkisi değildir.
