# Veri_Ufku — Faz32 teknik kanıt

2026-10-11, ENV-32. Yalnız açıkça istenen Faz32 uygulandı; DEC-32-01 ile
F32-S001..005/P001..008 zorunlu. Teknik teslim tamamlandı; ana matriste faz
**sürüyor / deneysel / zorunlu**: önceki resmî insan/AT/donanım/dağıtım
kabulleri açık kalır. Faz33 başlatılmadı.

<a id="e32-final"></a>
## E32-final

[Ortam](phase32/environment.json), [kontroller](phase32/checks.json),
[C/V/G/H/P kimlikleri](phase32/acceptance.json), [ADR-033](../adr/033-data-contracts-phase32.md).

| Gerçek kontrol | Sonuç | Kanıt |
|---|---|---|
| Kilitli CPython3.13.15 tam pytest | 816 geçti; 0 failure/error/skip | [JUnit](phase32/pytest.xml), [konsol](phase32/pytest.txt) |
| En son Faz32 odaklı koşu | 22 geçti; 0 failure/error/skip | [JUnit](phase32/targeted.xml), [konsol](phase32/targeted.txt) |
| Dataset/operations/projects/workspace ilgili regresyon | 64 geçti | [JUnit](phase32/affected.xml) |
| Kilitli unittest | 14 / OK | [Konsol](phase32/unittest.txt) |
| Kaynak + kurulu noneditable wheel | Her birinde6 gerçek QML/spawn/help/publish/reopen/undo/iptal akışı,6 render; toplam12 ekran | [Kaynak](phase32/source-gui/walkthrough.json), [wheel](phase32/wheel-gui/walkthrough.json) |
| Wheel/source/installed bütünlüğü | 221 dosya byte eşit | [SHA256 kayıtları](phase32/wheel-integrity.json) |
| Kurulu gerçek console entry, izole XDG/cwd | GUI_SMOKE PASS | [Konsol](phase32/wheel-console-smoke.txt) |
| Docs/artifacts/learning/usability; Ruff src/tests/scripts | PASS;167 makale/110 UI bağı/313 named field;253 Python dosyası formatlı | [Docs](phase32/docs.txt), [artifacts](phase32/artifacts.txt), [learning](phase32/learning.txt), [usability](phase32/usability.txt), [Ruff](phase32/ruff-check.txt), [format](phase32/ruff-format.txt) |

Tam816 koşusu son çekirdek rapor/registry değişikliklerini kapsar. Son QML
legacy-ordinal koruması ve ek testi ayrıca **en son22** odaklı koşu ve her iki
paketin altı-case walkthrough'unda doğrulandı; tam817 çalıştırılmış gibi
raporlanmaz. İlk810/1 registry hatası [ilk koşuda](phase32/pytest-initial.xml)
saklıdır; ortak capability zenginleştirmesine bağlanarak düzeltildi. Erken
boş-Parquet-import fixture hatası, geçerli sıfır satırlı filtre çıktısıyla
[son odaklı testte](phase32/targeted.xml) doğrulandı. Export/save-as sonrasında
kapanmış executor'a izleme callback'i erken GUI konsolunda kaldı; closing
koruması kaynak/wheel gerçek ayrı testinde geçti. Yanlış kapsamlı Ruff `.`
upstream lisans örneklerini denetledi ve başarısız oldu; third_party değişmedi,
DEVELOPMENT'teki src/tests/scripts kapsamı geçti. Bu denemeler başarı sayılmaz.

<a id="e32-contract"></a>
## E32-contract

Faz07 description/unit/ordinal_order/role/confirmed aynıdır; measurement_level
additive alanı unknown/nominal/ordinal/interval/ratio taşır. Eski ordinal rol
ve sıra yeni sözlüğe korunarak geçer; anlam güncellemesi onayı sessizce artırmaz.
Kolon sözlüğü ve kapalı Contract/v1, yeni DatasetVersion ile eski definition
sürümüne bağlanır. Değişen sürüm requires_validation; kaldırılan kolon
inapplicable. Primitive kayıpsız literal, valid range (nonfinite dahil), açık
null/unique politikası, fiziksel tür/birim ve FK sürüm/ColumnId doğrulanır.

Kurallar row/column/table/cross-table seviyesinde error/warning ve en fazla10
RowId/SourceRecordId örneğiyle raporlanır. `violations` etkilenen kayıt sayısıdır;
boş tabloda hatalı şema beyanı1 ihlal olarak ayrıca görünür. Ordinal sıra
beyanındaki uyuşmazlık karantina ile çözülemez. Referans key duplicate/tür
uyuşmazlığı raporlanır; sessiz cast veya düzeltme yok. Girdi raporunun sürümü
ile yayın çıktısı ayrı gösterilir; save/reopen yerel raporu tekrar hesaplamaz.

Stop hata varsa yayın engeller; warning kalır. Quarantine hata satırlarını tam
kimlikleriyle ayrı immutable Parquet lineage artifact'ına alır, warning kalır;
global tablo/tür/birim/sıra beyanı hatasında durur. Continue hataları ve değerleri
korur. Atomik parent yayın, worker'ın spec/diagnostics/output/inverse hash'lerini
girdilerden yeniden doğrular. Adaylarda publish engellidir; ACTIVE worker'da yazılmaz.

<a id="e32-identity"></a>
## E32-identity

String kategori ve entity adayları NFKC/casefold/strip üzerinden SequenceMatcher
ile puanlanır; kaynak metin değişmez. Entity blocking yalnız aynı nonempty
normalize gruptadır. Skor kimlik olasılığı değildir; benzer ad yeterli değil.
Onay reviewer/gerekçe/timezone-aware zamanla kaydedilir; adaylar tekrar hesaplanıp
onaylı çift doğrulanır. İnsan onayı ardından ayrı Uygula gerekir.

Canonical assignment satır silmez. RowId/SourceRecordId ve tüm kullanıcı
kolonları korunur; yalnız yeni veya önceki onaylı canonical alan kullanılır.
Tam inputVersion/row/source/previousCanonical/newCanonical inverse Parquet
saklanır; overlapping gruplar bölünmez, canonical değişimi izlenir. Undo/redo
immutable eski/yeni snapshot'a geçer. Kaynak ve eski kararlar/sonuçlar silinmez;
bağlı sonuçlar sürümlerine bağlı kalır. Karar günlüğü parent/input/fork/derived
ilişkilerinden bağlı dataset ve result kimliklerini, inverse artifact'ı gösterir.
Kategori mapping yalnız açıkça onaylanan kaynak→hedef değerleri yeni sürümde değiştirir.

<a id="e32-learning"></a>
## E32-learning

Katalog48/167: ölçüm düzeyi, veri sözleşmesi, referans bütünlüğü, fuzzy skor,
yanlış birleştirme. Beş F1/Escape bağında runtime makale kimlikleri doğrulandı;
yardım kaynak/capture/publish çalıştırmaz. Yeni try_action yok. Kaynak incelemesi
kurulu CPython difflib docstring/kod ve mevcut proje sözleşmeleriyle sınırlıdır;
çevrimiçi inceleme veya bilimsel uzman/AT kabulü iddia edilmez.

<a id="e32-limits"></a>
## E32-limits

String ordinal/fuzzy; scalar bound grammar; tek referans dataset/kontrol,
referans kontrolü aktif seçilmiş immutable sürüme bağlı. Composite FK/genel
kod DSL/SQL/birim dönüşümü yok. Entity20k kayıt/20k karşılaştırma/200 aday,
kategori200 benzersiz değer,100 kural; aşım açık hata, sessiz truncation yok.
Reviewer self-reported metindir; kimlik sertifikası veya doğruluk garantisi değildir.
Temel kurallar yereldir; F1/rapor/reopen ağ eylemi yapmaz. Manifest7 additive
alanları yeni okuyucu ister; eski sürümün ileri uyumluluğu iddia edilmez.

Fiziksel masaüstü, insan/AT, minimum donanım, temiz offline kurulum, remote CI
bu fazda çalıştırılmadı. Önceki F13/F24/F25/F27 açıkları ve Faz30 SAS büyük
ölçümü korunur. Sistem Python sonucu kilitli ortamla karıştırılmadı; bu fazda
sistem Python unittest yeniden çalıştırılmadı. Yeni dependency/lock değişikliği yok.
Kaynak combined prompt SHA256 değişmedi:
`1e0f59d3c25185b325395d791ce43abf1868ce3516be0823090ba899ee93ed9d`.
Stage/commit/push yapılmadı; untracked dosyalar teslimin parçasıdır.

## Deneme

Veri → Verini tanı → “Veri sözlüğü, kalite sözleşmesi ve kimlik eşlemeyi aç”.
Kolon anlam/birim/düzey/sıra ve kuralları önizle, sonra Uygula. Form seçili
sütunun kurallarını form değerleriyle değiştirir; karma dereceler/aynı-kind
çoklu kurallar için JSON tarifi kullan. Kayıtlı sözleşmeyi policy ile kontrol et;
hata varsa stop'ta Uygula pasif, quarantine/continue açıkça farklı davranır.
Ad ve blocking seç, aday üret; reviewer/gerekçe girip belirli çifti açıkça
onayla, yeni önizlemede Uygula. Geri al/yinele ve karar günlüğünde kimlik bağlarını incele.

<a id="e32-p001"></a>
## E32-p001

F32-P001.C/V/G/H/P: [kimlikli tanık](phase32/acceptance.json); `test_schema_additive_version_ordinal_and_roundtrip` ve `test_qml_dictionary_quality_policy_export_help_reopen`; [22 gerçek vaka](phase32/targeted.xml); [kaynak](phase32/source-gui/walkthrough.json) ve [kurulu wheel](phase32/wheel-gui/walkthrough.json); çevrimdışı `contract-level`. ENV-32,2026-10-11; deneysel teknik doğrulama, resmî insan kabulü değildir.

<a id="e32-p002"></a>
## E32-p002

F32-P002.C/V/G/H/P: [kimlikli tanık](phase32/acceptance.json); `test_schema_additive_version_ordinal_and_roundtrip` ve `test_phase07_ordinal_dictionary_extension_preserves_existing_order`; [22 gerçek vaka](phase32/targeted.xml); [kaynak](phase32/source-gui/walkthrough.json) ve [kurulu wheel](phase32/wheel-gui/walkthrough.json); çevrimdışı `contract-level`. ENV-32,2026-10-11; deneysel teknik doğrulama, resmî insan kabulü değildir.

<a id="e32-p003"></a>
## E32-p003

F32-P003.C/V/G/H/P: [kimlikli tanık](phase32/acceptance.json); `test_wrong_unit_type_keys_range_policy_quarantine_and_stop` ve `test_qml_foreign_key_unique_wrong_unit_type_actual_second_dataset`; [22 gerçek vaka](phase32/targeted.xml); [kaynak](phase32/source-gui/walkthrough.json) ve [kurulu wheel](phase32/wheel-gui/walkthrough.json); çevrimdışı `contract-schema`. ENV-32,2026-10-11; deneysel teknik doğrulama, resmî insan kabulü değildir.

<a id="e32-p004"></a>
## E32-p004

F32-P004.C/V/G/H/P: [kimlikli tanık](phase32/acceptance.json); `test_foreign_keys_actual_second_version_no_implicit_cast` ve `test_qml_foreign_key_unique_wrong_unit_type_actual_second_dataset`; [22 gerçek vaka](phase32/targeted.xml); [kaynak](phase32/source-gui/walkthrough.json) ve [kurulu wheel](phase32/wheel-gui/walkthrough.json); çevrimdışı `contract-reference`. ENV-32,2026-10-11; deneysel teknik doğrulama, resmî insan kabulü değildir.

<a id="e32-p005"></a>
## E32-p005

F32-P005.C/V/G/H/P: [kimlikli tanık](phase32/acceptance.json); `test_publication_rechecks_diagnostics_and_approved_values` ve `test_qml_dictionary_quality_policy_export_help_reopen`; [22 gerçek vaka](phase32/targeted.xml); [kaynak](phase32/source-gui/walkthrough.json) ve [kurulu wheel](phase32/wheel-gui/walkthrough.json); çevrimdışı `contract-schema`. ENV-32,2026-10-11; deneysel teknik doğrulama, resmî insan kabulü değildir.

<a id="e32-p006"></a>
## E32-p006

F32-P006.C/V/G/H/P: [kimlikli tanık](phase32/acceptance.json); `test_categories_manual_mapping_and_cancel` ve `test_qml_categories_manual_approval_and_real_worker_cancel`; [22 gerçek vaka](phase32/targeted.xml); [kaynak](phase32/source-gui/walkthrough.json) ve [kurulu wheel](phase32/wheel-gui/walkthrough.json); çevrimdışı `contract-fuzzy`. ENV-32,2026-10-11; deneysel teknik doğrulama, resmî insan kabulü değildir.

<a id="e32-p007"></a>
## E32-p007

F32-P007.C/V/G/H/P: [kimlikli tanık](phase32/acceptance.json); `test_entity_no_unapproved_merge_blocks_and_undo_all_source_ids` ve `test_qml_no_automatic_merge_human_decision_journal_undo`; [22 gerçek vaka](phase32/targeted.xml); [kaynak](phase32/source-gui/walkthrough.json) ve [kurulu wheel](phase32/wheel-gui/walkthrough.json); çevrimdışı `contract-fuzzy`. ENV-32,2026-10-11; deneysel teknik doğrulama, resmî insan kabulü değildir.

<a id="e32-p008"></a>
## E32-p008

F32-P008.C/V/G/H/P: [kimlikli tanık](phase32/acceptance.json); `test_overlapping_merge_canonical_changes_inverse_and_linked_results` ve `test_qml_no_automatic_merge_human_decision_journal_undo`; [22 gerçek vaka](phase32/targeted.xml); [kaynak](phase32/source-gui/walkthrough.json) ve [kurulu wheel](phase32/wheel-gui/walkthrough.json); çevrimdışı `contract-merge`. ENV-32,2026-10-11; deneysel teknik doğrulama, resmî insan kabulü değildir.
