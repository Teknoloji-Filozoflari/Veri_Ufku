# Veri_Ufku — UX V2 kanıt günlüğü

Yerel dal `ux-v2`. Push yok. Untracked kullanıcı dosyası `docs/PRODUCT_DIRECTION_JASP_ORANGE.md` commit’lere karıştırılmaz.
Ana denetim: [UX_V2_AUDIT.md](../UX_V2_AUDIT.md). Ayrıntılı loglar: `docs/evidence/ux-v2/`.

## UX0 — Denetim (2026-10-25)

| Alan | Değer |
|---|---|
| Kimlik | UX0-AUDIT-20261025 |
| Ortam | CachyOS Linux; CPython 3.13.15 `.venv`; `QT_QPA_PLATFORM=offscreen` `QT_QUICK_BACKEND=software` |
| HEAD başlangıç | `54c3a891` |
| Kod değişikliği | Yok (salt okunur) |

### Kapılar

| Dosya / log | Sonuç |
|---|---|
| `ux-v2/baseline-env.txt` | Ortam + başlangıç git status |
| `ux-v2/baseline-gates.log` | check_docs/artifacts/learning/usability, ruff, format, smoke, focused pytest özeti |
| `ux-v2/check_docs.log` … `ruff_format.log` | Tekil exit 0 |
| `ux-v2/smoke_test.log` | `GUI_SMOKE PASS` |
| `ux-v2/pytest_ui_focused.log` | 26 passed in 44.13s |
| `ux-v2/baseline-ui-junit.xml` | JUnit |

Bilinen açıklar (düzeltilmedi): Default 2GiB full generic-cancel; source close/open ara failures; longheap; minHW; fiziksel; insan/AT; offline installer; remote CI.

### Teknik teslim / resmî kabul

- Teknik teslim: denetim raporu + bu kanıt.
- Resmî kabul: açık.

## UX1 — Şartname (2026-10-25)

| Alan | Değer |
|---|---|
| Kimlik | UX1-SPEC-20261025 |
| Çıktı | [UX_WORKSPACE_V2.md](../UX_WORKSPACE_V2.md) |
| Kod | Yok |
| Belge kapısı | `check_docs.py` (commit öncesi) |
| Kullanıcıya bırakılan | Gerçek yeni başlayanlarla gösterim (§8) |

## UX2 — Kabuk (2026-10-25)

| Alan | Değer |
|---|---|
| Kimlik | UX2-SHELL-20261025 |
| Kod | `Main.qml`, `StageStrip.qml`, `ContextSidePanel.qml`, `UxStages.js`, `tests/test_ux2_shell_gui.py` |
| Kapılar | docs/artifacts/learning/usability/Ruff/format PASS; smoke PASS; odaklı UI 28 PASS (`ux2-pytest.log`) |
| Korunan | selectedSection 0–7, nav0–7, proje draft/sürüm değişmedi |
| Resmî kabul | açık |

## UX3 — Tablo (2026-10-25)

| Alan | Değer |
|---|---|
| Kimlik | UX3-TABLE-20261025 |
| Kod | `DatasetPanel.qml`, `dataset.py` header/annotate, `UxStages.js`, `Main.qml` accordion sırası, `tests/test_ux3_table_gui.py` |
| Kapılar | docs/…/Ruff/smoke; `ux3-pytest.log` 23 PASS |
| Korunan | RowId/ColumnId; filtre→sürüm yok; kaynak byte eşit |
| Resmî kabul | açık |

## UX4 — Veri alanı (2026-10-25)

| Alan | Değer |
|---|---|
| Kimlik | UX4-LIBRARY-20261025 |
| Kod | `catalog.json`, `storage/user_library.py`, `ui/data_library.py`, `DataLibraryPanel.qml`, ImportPanel kancası, `tests/test_ux4_library*.py` |
| Karar | Verilerim = XDG indeks + kopya; ProjectStore şema göçüsü yok; import `choose` yolu |
| Kapılar | docs/artifacts/learning/usability/Ruff/smoke; `ux4-pytest.log` 8 PASS |
| Test düzeltmesi | `test_import_gui` helpButton: kabuk F1 her zaman görünür (hatalı “gizli” beklentisi) |
| Resmî kabul | açık |

## UX5 — Öğretim (2026-10-25)

| Alan | Değer |
|---|---|
| Kimlik | UX5-TEACH-20261025 |
| Kod | `ux_v2_stages.json`, `ui/ux_content.py`, `FirstRunTour.qml`, ContextSidePanel, `tests/test_ux5_content.py` |
| Kapılar | docs/…/Ruff/smoke; `ux5-pytest.log` |
| Kullanıcıya bırakılan | Taslak metinlerin son onayı |
| Resmî kabul | açık |

## UX6 — Özet / eksik (2026-10-25)

| Alan | Değer |
|---|---|
| Kimlik | UX6-MISSING-20261025 |
| Kod | `missing_drop_impact`, `previewMissingDrop`, QualityPanel UI, `tests/test_ux6_missing_*.py` |
| Kapılar | `ux6-pytest.log` 2 PASS; Ruff/docs/smoke |
| Resmî kabul | açık |

## UX7 — Keşif (2026-10-25)

| Alan | Değer |
|---|---|
| Kimlik | UX7-EXPLORE-20261025 |
| Kod | ChartPanel yorum, `saveChartNote` / `markChartRows` |
| Kapı | grafik veri değiştirmez (mevcut chart testleri + smoke) |

## UX8 — Aykırı (2026-10-25)

| Alan | Değer |
|---|---|
| Kimlik | UX8-OUTLIER-20261025 |
| Kod | `analytics/outliers.py`, OperationsPanel aday çerçevesi, `tests/test_ux7_ux8_outliers.py` |
| Kapı | `ux7-ux8-pytest.log`; üç yöntem; applied=false |

## UX9 — Yöntem/model (2026-10-25)

| Alan | Değer |
|---|---|
| Kimlik | UX9-MODEL-20261025 |
| Ortam | CPython 3.13.15 `.venv`; QT offscreen/software |
| Kod | `modeling/candidates.py`, `PreparationController.modelCandidates`, ValidationPanel aday çerçevesi, `tests/test_ux9_model_candidates.py` |
| Kapılar | `ux9-pytest.log` 3 PASS; docs/learning/usability/artifacts PASS; smoke GUI_SMOKE PASS; Ruff PASS |
| Kabul | aday işaretli; auto_fit=false; learned_scope=training_fold; yapı korunur; fit kullanıcı düğmesi; test tek final onay |
| Resmî kabul | açık |
