# Veri_Ufku çalışma sözleşmesi

Yalnız kullanıcının açıkça gönderdiği fazı uygula. Kaynak belgenin tamamı gelecek fazları başlatma yetkisi değildir. Ürün adı tam olarak Veri_Ufku. Bu bir Linux masaüstü uygulamasıdır; Python/PySide6/QML korunur.

Her oturumda önce şu dosyaları oku:
1. docs/PROJECT_RULES.md ve docs/UI_DESIGN_BRIEF.md
2. docs/PRODUCT.md, docs/ARCHITECTURE.md ve docs/CORE_CONTRACTS.md
3. docs/UX.md, docs/UI_REFERENCES.md ve docs/DESIGN_SYSTEM.md
4. docs/ACCEPTANCE_POLICY.md, docs/REQUIREMENTS_MATRIX.md ve docs/PROGRESS.md
5. docs/PHASE_PLAN.md, docs/DEVELOPMENT.md, ilgili ADR ve son kanıt kayıtları.

Profesyonel fazda ayrıca docs/PRO_PROGRESS.md; Faz 28'de üretilecek PRO_PRODUCT, PRO_ARCHITECTURE ve PRO_CAPABILITY_MATRIX belgeleri. Henüz olmayan belgeyi var sayma.

Kullanıcı talimatları önceliklidir. Kaynak dosyayı koru; otomatik veri değişikliği yapma. Faz durumu, yetenek olgunluğu, kapsam ve doğrulamayı ayrı tut. Matris ana kayıttır; özetleri eşleştir. Her kabul için kimlik, yol, ortam, tarih ve gerçek kanıt kaydet. Çalıştırılmayan kontrol başarılı değildir. Veri kaybı belirsizliğinde dur; rutin kararlarla ilerle.

Faz 00 kontrolü: `python3 scripts/check_docs.py` ve `python3 -m unittest discover -s tests -v`. Analitik veya uygulama iskeleti Faz 00 kapsamında değildir. Sonraki fazlarda bu kontroller korunur, gereken gerçek testlerle genişletilir.

Faz 01 ve sonraki oturumlarda gerçek kontroller README/docs/DEVELOPMENT.md komutlarıdır: kilitli dev kurulumu, check_docs/check_artifacts, Ruff check/format, pytest ve offscreen/software kurulu giriş noktası smoke. İlgili son kayıt docs/evidence/PHASE01.md ve ADR-005 okunmalı. Faz 01 kullanıcı masaüstü kabulü tamamlandı; remote CI 37500721689 başarı kanıtıyla kabul tamamlandı; sonraki fazı kendiliğinden başlatma.

Faz02 gerçek kabuk, UI tercihleri, referans görsel incelemesi ve headless/Wayland kontrolleri uygulandı; son kayıt docs/evidence/PHASE02.md. Faz04 ve sonraki fazları kendiliğinden başlatma.

Faz03 ve sonraki her yeni ekran/capability yardımı docs/LEARNING_CONTENT.md sözleşmesiyle eklenir; `uv run --frozen python scripts/check_learning.py` gerçek kontrol listesine dahildir. İlgili son kanıt docs/evidence/PHASE03.md. Faz04 kendiliğinden başlatılmaz.
