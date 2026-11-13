# Veri_Ufku — şema hizalama Faz A/B/C kanıt günlüğü

2026-11-13 · Açık kullanıcı talimatı: `veri_ufku_sema_gelistirme_promtu.md` v1.0 (13 Kasım 2026).
Kapsam: **Faz A → B → C**. D–J fazları başlatılmadı.

| Alan | Değer |
|---|---|
| Kimlik | SCHEMA-ABC-20261113 |
| Ortam | CachyOS Linux · CPython 3.13.15 `.venv` · PySide6 6.11.2 · `QT_QPA_PLATFORM=offscreen` `QT_QUICK_BACKEND=software` |
| Başlangıç HEAD | `54efeb1b` (fix: CI Lint için Ruff format düzeltmeleri) |
| Kaynak şema | `veri_ufku_sema.pdf` — 7 aşama, 61 alt başlık |
| Kullanıcı kararları | B-02 bulgu defteri **alta çekmece**; B-03 Raporla **yedi iş birincil sekme**; git: **yerel commit + origin/main push** |

## Faz A — Yol haritası ve çekirdek sözleşme (kod değiştirmez)

| Teslim | Yol |
|---|---|
| 61 alt başlığın durum + gerekçe + çelişkiler | `docs/SCHEMA_CONTRACT.md` |
| Alt başlık ↔ modül ↔ QML ↔ test eşlemesi | `docs/SCHEMA_MAP.md` |
| ADR 076 — şema tek doğruluk kaynağı | `docs/adr/076-schema-single-source.md` |
| ADR 077 — Bulgu defteri omurgası | `docs/adr/077-finding-notebook-spine.md` |
| ADR 078 — Mod 1 / Mod 2 sözleşmesi | `docs/adr/078-mod1-mod2-contract.md` |

Faz A envanteri: 51 `var` · 8 `eksik` · 2 `yok`. Kod yolundaki sapmalar uydurulmadı; katalog
satırı kanıt sayılmadı, her satır kaynak kod ve test dosyası okunarak doğrulandı.

## Faz B — Bulgu defteri omurgası

| Değişiklik | Yol |
|---|---|
| Bulgu varlığı (soru · yöntem · sonuç · yorum · seçim gerekçesi) | `src/veri_ufku/storage/finding_store.py` |
| Denetleyici (ekleme, silme, önizleme, güncellik) | `src/veri_ufku/ui/findings.py` |
| Alta çekmece yüzeyi | `src/veri_ufku/ui/qml/FindingDrawer.qml` |
| Çekmece yerleşimi ve aşama eylemleri | `src/veri_ufku/ui/qml/Main.qml` |
| Aşama yüzeylerine "Bulgu defterine ekle" | `DataWorkspacePanel` · `InspectWorkspacePanel` · `VisualizeWorkspace` · `PrepareWorkspace` · `StatisticsWorkspace` · `ModelWorkspace` · `ReportWorkspace` |
| Proje durumuna `findings` alanı + şema sürümü 8 geçişi | `src/veri_ufku/storage/project_model.py` |
| Rapor tarifine `findings` blok türü | `src/veri_ufku/exports/report_contracts.py`, `src/veri_ufku/exports/report_builder.py`, `src/veri_ufku/storage/report_builder_store.py`, `src/veri_ufku/ui/report_builder.py` |
| Testler | `tests/test_finding_store.py` (9), `tests/test_findings_gui.py` (3) |

Kabul kanıtı:
- Bulgu oluşturulur, **sonuç kayıtlı çalışmadan okunur** (elle yazılmaz; kayıt yoksa
  `not_recorded` görünür).
- Veri sürümü değişince bulgu **"güncel değil"** olarak işaretlenir (türetilmiş sürüm veya
  çalışma alanı sürümü değişimi).
- Rapor çıktısında bulgunun beş alanı ve gerekçesi görünür; kayıt projede yoksa dışa aktarım
  **hata verir**, bulgu sessizce düşmez.
- Bulgu kaydı proje kaydının parçasıdır (ikinci kayıt sistemi yok); proje yeniden açılınca
  bulgular okunur.

## Faz C — Raporla hizalama

| Değişiklik | Yol |
|---|---|
| Yedi işlev birincil liste, kaynak-aşama bölümleri ikincil | `src/veri_ufku/ui/qml/ReportCatalogPanel.qml` |
| Word (DOCX) dışa aktarım — bağımlılıksız yerel OOXML | `src/veri_ufku/exports/docx.py` |
| DOCX paket üretimi ve dışa aktarım izni | `src/veri_ufku/exports/report_builder.py`, `src/veri_ufku/storage/report_builder_store.py`, `src/veri_ufku/ui/report_builder.py` |
| Testler | `tests/test_report_functions_gui.py` (2) |

Yedi işlev: Bulgu defteri · Rapor yapısı · Rapor öncesi kontrol · Dışa aktar · Yeniden üretim ·
Gizlilik ve paylaşım · İleri çıktılar (Modül). "İleri çıktılar" modülü kurulu değildir ve
**"Modül: indir"** olarak soluk görünür; indirme otomatik başlamaz.

## Kapılar

| Kontrol | Log | Sonuç |
|---|---|---|
| `scripts/check_docs.py` | `schema-abc/check_docs.log` | PASS — 76 faz, kanıt, ilerleme ve yerel bağlantılar |
| `scripts/check_artifacts.py` | `schema-abc/check_artifacts.log` | PASS — geliştirme tekerleği ve lock bütünlüğü |
| `scripts/check_learning.py` | `schema-abc/check_learning.log` | PASS — 10 ders, 414 çevrimdışı makale, 217 UI bağı |
| `scripts/check_usability.py` | `schema-abc/check_usability.log` | PASS — 414 makale, 1071 adlandırılmış alan |
| `ruff check src tests scripts` | `schema-abc/ruff_check.log` | PASS |
| `ruff format --check src tests scripts` | `schema-abc/ruff_format.log` | PASS |
| `veri-ufku --smoke-test` | `schema-abc/smoke_test.log` | `GUI_SMOKE PASS` |

## Odaklı pytest

| Süit | Sonuç |
|---|---|
| `tests/test_finding_store.py` | 9 passed |
| `tests/test_findings_gui.py` | 3 passed |
| `tests/test_report_functions_gui.py` | 2 passed |
| `tests/test_report_workspace_gui.py` + `tests/test_report_builder_gui.py` | 4 passed |
| Geniş regresyon (projects · operations · statistics · report_builder · exports · ux10 · usability · learning · quality · cleaning + yeni testler) | 188 passed, 2 failed (aşağıdaki önceden mevcut açıklar) |

## Önceden mevcut açıklar (bu çalışmanın ürünü değil)

HEAD `54efeb1b` üzerinde de düşen testler — bu oturumda **düzeltilmedi**:

| Test | Durum |
|---|---|
| `tests/test_data_workspace_gui.py::test_empty_veri_shows_card_without_dock` | HEAD'de de düşüyor |
| `tests/test_model_workspace_gui.py::test_model_workspace_shell_fit_save_unsupported` | HEAD'de de düşüyor |
| `tests/test_usability.py::test_empty_tables_do_not_trap_keyboard_focus` | HEAD'de de düşüyor |
| `tests/test_usability.py::test_textarea_tab_exits_and_picker_survives_type_update` | HEAD'de de düşüyor |

Bu oturumda **düzeltilen** önceden mevcut açık: `scripts/check_usability.py` kapısı, `VisualizeWorkspace.qml`
içindeki ham `TextArea` nedeniyle HEAD'de kırmızıydı; paylaşılan `UiTextArea` kontrolüne geçirildi.

## Teknik teslim / resmî kabul

- Teknik teslim: bu belge + loglar + koda gömülü testler.
- Resmî kabul ayrıdır ve **açık kalır**: fiziksel masaüstü, gerçek ekran okuyucu, insan kullanıcı
  kabulü, minimum donanım, temiz-OS offline kurulum, uzak CI, kurulu tekerlek smoke, tam suite ve
  longheap koşuları bu fazlarda çalıştırılmadı.
- D–J fazları başlatılmadı; B-01, B-04 … B-10 belirsizlikleri kullanıcı kararını bekliyor.
