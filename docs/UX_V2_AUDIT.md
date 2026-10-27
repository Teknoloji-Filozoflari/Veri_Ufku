# Veri_Ufku — UX V2 denetimi (UX0)

2026-10-25 Europe/Istanbul. Salt okunur denetim; uygulama kodu değiştirilmedi.
Kaynak görev: Project store `docs/veri-ufku-gelistirme-promptu.md` (UX0–UX10).
Dal: yerel `ux-v2`. Teknik Faz72+ başlatılmadı.

**Teknik teslim:** bu belge + [kanıt](evidence/UX_V2.md).
**Resmî kabul:** kullanıcıya ve ayrı kanıtlara aittir; bu denetim resmi ürün kabulü değildir.

## Ortam ve başlangıç

| Alan | Değer |
|---|---|
| Kimlik | UX0-AUDIT-20261025 |
| Depo | `/home/s-oktay/Belgeler/Veri_Ufku` |
| Dal / HEAD | `ux-v2` / `54c3a891` (başlangıç) |
| Python | CPython 3.13.15 (`.venv`) |
| Başlangıç `git status --short` | `?? docs/PRODUCT_DIRECTION_JASP_ORANGE.md` (kullanıcı untracked; commit’e karıştırılmadı) |
| Bilinen açıklar (AGENTS.md) | Default 2GiB full generic-cancel ve source close/open ara failures; longheap, minHW, fiziksel masaüstü, insan/AT, offline installer, remote CI — **bilinen**, bu görevde düzeltilmez |

## Hipotezler

| ID | Hipotez | Sonuç | Kanıt |
|---|---|---|---|
| H1 | Veri tablosu çalışma alanında yeterince merkezi değil | **Doğrulandı** | `Main.qml` varsayılan `selectedSection=0`; veri sekmesinde `dataPane=""` iken tablo mount edilmez; tablo yalnız `rows` alt bölümünde ve “Tabloyu aç / yenile” ile (`DatasetPanel.qml` 35–42, `Main.qml` 32–36 / 725–731) |
| H2 | İstenen yeteneklerin çoğu zaten var; asıl iş akışa dizmek | **Kısmen doğrulandı** | Import/profil/kalite/grafik/temizlik/hazırlama/model/rapor panelleri mevcut; JourneyGuide 6 adım, UX 10 aşamayla bire bir değil |
| H3 | Projeler arası kullanıcı veri kütüphanesi yok | **Doğrulandı** | “Verilerim” ekranı/API yok; kaynaklar proje `sources[]` içinde; `learning.exampleLibrary` yalnız öğrenme sandbox |
| H4 | Grafik yorumu ve sütun notları mevcut not/rapor yapısına bağlanabilir | **Kısmen** | `ReportPanel` / `ReportBuilderPanel` grafik bloğu ve serbest metin var; sütun notlarının rapora otomatik bağlanması bu denetimde doğrulanmadı |

## On aşama + Verilerim durumu

| # | Öğe | Durum | Gerekçe | Ana dosyalar |
|---|---|---|---|---|
| 0 | Amaç ve kaynak | kısmi | Yol haritası + proje oluştur/aç var; amaç kartları/Verilerim kaynağı yok | `ScienceRoadmap.qml`, `RoadmapSteps.js`, `ProjectPanel.qml` |
| 1 | Yükle ve kontrol et | kısmi | Güçlü import önizleme; “kontrol” kalite alt sekmesine dağılmış | `ImportPanel.qml`, `QualityPanel.qml` |
| 2 | Sütunları tanı | mevcut | Profil, değer inceleme, rol/not | `DatasetPanel.qml`, `ColumnNotes.qml`, `ValueInspection.qml` |
| 3 | Temel veri özeti | mevcut | Envanter + describe; korelasyon/ısı haritası grafik/istatistik yollarında | `DatasetOverview.qml`, `ChartPanel.qml`, `StatisticsPanel.qml` |
| 4 | Eksik veri | kısmi | Kalite taraması + gelişmiş MI; başlangıç “silersem N satır” etki paneli yok | `QualityPanel.qml`, `MissingSamplingPanel.qml` |
| 5 | Desenleri keşfet | mevcut | Galeri + amaç önerisi + katalog; brushing→RowId | `ChartPanel.qml`, `ui/charts.py` |
| 6 | Aykırı değerleri incele | kısmi | Kalite/temizlik/IQR; üç yöntem yan yana + grafik–liste aynı aday kümesi yok | `quality.py`, `CleaningOptions.qml`, `UnsupervisedPanel.qml` |
| 7 | Veriyi hazırla | mevcut | Önizle + Uygula, yeni sürüm, geri alma | `OperationsPanel.qml`, `CleaningOptions.qml` |
| 8 | Yöntem/model seç | mevcut | Hazırlık planı (fit yok), validation günlüğü, sınıflandırma/regresyon | `PreparationPanel.qml`, `ValidationPanel.qml`, `ClassificationPanel.qml` |
| 9 | Bulguları anlat | mevcut | HTML/PDF rapor + builder | `ReportPanel.qml`, `ReportBuilderPanel.qml` |
| — | Verilerim | eksik | Çapraz proje kullanıcı kütüphanesi yok | — |

Durum sözlüğü: **mevcut** kullanılabilir çekirdek var; **kısmi** parçalar var ama hedef UX eksik; **eksik** bulunamadı; **belirsiz** bu oturumda kanıtlanamadı.

## Hedefli bulgular

### Kabuk ve gezinme

Başlangıç görünümü 8 sekme: Başlangıç → Veriyi tanı → Veriyi hazırla → Desenleri keşfet → Farkları karşılaştır → Model kur → Bulguları paylaş → Öğren (`Main.qml` 56–65). Sol aşama şeridi UX hedefindeki 10 aşamalı şerit değil; mevcut dikey/kompakt navigasyon + JourneyGuide (sekme 1–6). Dar pencerede `compactNavigation` (`width < 1000 * Theme.scale`).

### Tablo

`DatasetPanel` + `TableView` `reuseItems`, sayfa 200, `RowId` rolü (`DatasetPanel.qml`, `ui/dataset.py`). Görünüm filtresi/sıralama/gizleme salt okunur görünüm; yeni sürüm üretmez (öğrenme metni ve mevcut testlerle uyumlu). Proje açılışında tablo merkez yüzey değil (H1).

### Eksik / aykırı / özet

- Eksik: kalite bulguları + `recommendation.impact`; işlem önizlemesinde `previewResult.impact`. Tek “eksik satır silinirse N/%” simülasyon paneli **yok** (kısmi).
- Aykırı: kalite 1.5×IQR; temizlik IQR; unsupervised IQR/IsolationForest/LOF. Dayanıklı z (MAD) kalite/EDA yolunda yok (resampling’te MAD istatistiği var). Grafik brushing `page_row_ids` → `selectChartRows` ile tablo seçimi aynı RowId kümesine bağlanır; “aşama 5 işaretleri = aşama 6 aday listesi” tek aday sistemi olarak **kurulmamış**.
- Korelasyon/ısı haritası grafik motorunda mevcut; Aşama 3’e sabitlenmiş tek özet yüzeyi değil.

### Anlık sonuç (JASP)

`ComputeBudget` ve worker zarfı mevcut (`domain/contracts.py`, `analytics/worker.py`, `jobs/admission.py` — Qt nesnesi worker’a gitmez). Grafik/formda çoğu yerde `invalidate()` revision artırır; ChartPanel’de otomatik debounce yenileme **yok** — “Grafiği oluştur” gerekir. Altyapı uygun, UX kuralı henüz yok.

### Mimari sözleşmeler

Tek `CAPABILITIES` registry, `ProjectStore` / `DatasetVersion` / `ColumnId` / `RowId` / `SourceRecordId` / `Provenance` / `ComputeBudget` korunuyor. İkinci proje kayıt sistemi yok. Core-only açılış smoke: `veri-ufku --smoke-test` → `GUI_SMOKE PASS` (bu oturum).

### Öğrenme

`docs/LEARNING_CONTENT.md` sözleşmesi + `tr.json` / F1 / sözlük mevcut. Otomatik ≤1 dk ilk açılış turu (tablo/sütun/aşama/öğren) **bulunamadı**; GuidePanel ve öğrenme lab ayrı.

## Taban çizgisi (gerçek sonuçlar)

Kanıt dizini: `docs/evidence/ux-v2/`. Ortam: `baseline-env.txt`.

| Kontrol | Komut | Sonuç |
|---|---|---|
| Belge | `uv run --frozen python scripts/check_docs.py` | PASS (exit 0) |
| Artefact | `… check_artifacts.py` | PASS |
| Öğrenme | `… check_learning.py` | PASS (414 makale, 10 lesson / 8 path) |
| Kullanılabilirlik | `… check_usability.py` | PASS |
| Ruff | `ruff check src tests scripts` | PASS |
| Format | `ruff format --check …` | PASS (566 dosya) |
| Smoke | `uv run --frozen veri-ufku --smoke-test` (offscreen/software) | `GUI_SMOKE PASS` (exit 0, ~3s) |
| Odaklı UI pytest | `pytest -q tests/test_gui.py tests/test_ui_renewal.py tests/test_journey_gui.py tests/test_data_inspection.py tests/test_data_workspace_gui.py` | **26 passed** in 44.13s (exit 0); junit: `baseline-ui-junit.xml` |
| Tam pytest paketi | — | **çalıştırılmadı** (UX0 tabanında odaklı UI + kapılar; tam paket UX10’da) |
| Wheel kurulum smoke | — | **çalıştırılmadı** |
| Fiziksel masaüstü / insan / AT / minHW / offline installer / remote CI / longheap | — | **bilinen açık / bu görevde yok** |

## Kapı (UX0)

| Koşul | Kanıt |
|---|---|
| Rapor kanıtlı | Bu belge + `docs/evidence/UX_V2.md` |
| Belirsizler işaretli | H4 sütun-not→rapor otomatik bağ; tam suite |
| Taban sonuçları gerçek | Yukarıdaki tablo; loglar `docs/evidence/ux-v2/` |
| Kod değişmedi | Yalnız belge/kanıt/durum |

## Kullanıcıya bırakılan işler (otomatik tamamlanmış sayılmaz)

- Gerçek yeni başlayanlarla gösterim
- Resmî ürün kabulü
- AGENTS.md ayrı kanıt alanları (fiziksel, AT, minHW, offline installer, remote CI, longheap)
- Untracked `docs/PRODUCT_DIRECTION_JASP_ORANGE.md` kullanıcı dosyası; bu faza dahil değil
