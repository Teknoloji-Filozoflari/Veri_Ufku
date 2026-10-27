# Faz73 — versioned trusted plugin SDK ve bounded result host

2026-10-16 DEC73-01 / ENV-73. Açık Faz73 talimatı; Linux Python/PySide6/QML.
Resmî sürüyor / deneysel / isteğe bağlı. [Önceki durum](phase73/prior-project_state.txt)
ve tüm önceki resmî açıklar korunur. [ADR074 / SDK sözleşmesi](../adr/074-plugin-sdk-phase73.md).

<a id="e73-scope"></a>
## E73-SCOPE

Rapor → Uzman eklentileri / SDK. API1 author Protocol'leri importer/transform/stat/
model/chart/lesson; closed manifest/capability/input/output ve kind-specific data
sözleşmesi. Kaynak32MiB/10000row/1..16kolon; request8MiB/output1MiB/run2MiB.
Finite scalar input; null korunur, Decimal/date/nested/binary/NaN/Inf sessiz çevrilmez.
Module entry self-contained plugin.py:run; code/manifest64KiB. Author contract CLI
GUI/ProjectStore gerektirmez; yalnız explicit --trust-code ile fresh process açar.

Manifest discovery yalnız kullanıcının seçtiği dosyayı veri olarak okur. API/Python,
exact installed dependency versions, code SHA256, permission disclosure ve learning
id/version kontrol edilir; plugin code import edilmez. Açılışta tarama, autoload,
pip/install, dependency environment yaratma veya ağ/model indirme yoktur. Ortam
mevcut kilitli uygulama Pythonudur; dependency uyumsuzluğu görünür/çalıştırma kapalı.
Code/manifest/env inspection hash değişirse önceki trust kullanılamaz. Explicit
trust ve optional bildirilen network için ayrı onay gerekir. Manifest permissions
**OS enforcement değildir**; aynı kullanıcı filesystem/network/keyring hakları
sürer. Ayrı process güvenli sandbox veya hostile-code containment değildir.

Tek Capability registry explicit run'da namespaced kayıtla genişler; core method
üzerine yazılmaz, aynı session id başka code/version ile değiştirilmez. Worker
immutable input envelope/pinned source paths/code bytes +ComputeBudget/admission/
supervisor kullanır; Qt/ACTIVE yok. Host safe finite JSON/shape/RowId/known-secret
kontrolü sonrası mevcut ProjectStore atomik transaction/results journal'a ekler.
Raw plugin code/path persist edilmez, arbitrary object/pickle/checkpoint import yok.
stdout/stderr FD devnull, exception türü gösterilir; exception metni/traceback yok.
Bu eksiksiz secret detector veya malware güvenliği garantisi değildir.

PluginRun/v1 mevcut `sources/` data artifact +plugin_result reference, append-only
journal koruması ve manifest artifact referans doğrulaması. Ortak Provenance:
DatasetVersion/SourceSnapshotId/ColumnId/usedRowId, params hash, method version,
plugin semver/code hash, Python/dependency env, seed ve learning version. Explicit
trust/network/permissions kararı saklanır. Eski eksik provenance uydurulmaz.

Eksik plugin ile artifact/hash ve learning snapshot okunur, read-only proje dahil;
proje açılışı code aramaz/import etmez. Recompute genel sonuç görünümünde readonly;
yeniden çalıştırma aynı manifest/code/env ve explicit trust ile SDK panelindedir.
Çöken, canceled, timeout, incompatible veya invalid output başarı olarak eklenmez.
Kaynak üzerinde host yazma/otomatik aktif dataset değişikliği yoktur; trusted same-user
Python'un düşmanca yazma haklarının engellendiği iddia edilmez.

## Altı türün gerçek destek sınırı

| SDK türü | Bu hostta doğrulanan kapsam | Tam native entegrasyon |
|---|---|---|
| importer | columns/rows/unique source_record_ids tablo preview arşivi | Yeni SourceAdapter/native import wizard ve aktif DatasetVersion publish yok |
| transform | columns/rows/parent_row_ids, kaynak RowId kontrolü, preview arşivi | Native OperationSpec apply/undo dataset adapter yok |
| stat | finite metrics, gerçek ortalama örneği, GUI/result/help/save | Genel inferential doğruluk plugin yazarının ayrıca sorumluluğu |
| model | finite metrics +safe JSON state arşivi | Host fit/CV/predict/load adapter yok; JSON state executable model sayılmaz |
| chart | finite x/y/axis label descriptor arşivi | Native renderer/editor hook yok; bu fazın gerçek GUI örneği analysis/stat |
| lesson | düz metin title/paragraphs snapshot | Otomatik learning catalogue/try_action install yok |

Dolayısıyla SDK çekirdeği ve bounded result host doğrulandı; bütün native importer/
transform/model/chart/lesson entegrasyonları tamamlanmış sayılmaz. Ana matriste bu
geniş alt işler doğrulanmadı kalır. Interface/data contract kanıtı full native
feature kabulüyle karıştırılmaz. [Bağımsız örnek paket](../../examples/plugins/mean/README.md).

<a id="e73-validation"></a>
## E73-VALIDATION

[Ortam](phase73/environment.json): kilitli CPython3.13.15 `.venv`, CPU, Qt offscreen/
software; yeni dependency yok. [424byte-eşit noneditable package](phase73/package-parity.json),
[build](phase73/build.log)/[install](phase73/install.log). Source/wheel odaklı koşular
JUnit/loglarla bu dizinde; tam depo veya formal bilimsel/insan kabulü değildir.

[30native source](phase73/source-native.xml) PASS: manifest top-level code execute
etmez; API/Python/entry/permissions/semver/help/dependency ret; stdlib author CLI
ve elle mean2/n3; current source hash, ColumnId/RowId/provenance ve params/trust/env
binding; kaynak korunması; old artifact hash tamper; missing plugin/read-only reopen;
worker exception/exit17/invalid output izolasyonu; cooperative cancel/time budget;
contract hard timeout; altı kind gerçek calculate→ProjectStore archive→load;
nonfinite/unsafe object/known-secret output reddi. Testler yalnız trusted/sentetik
kod içindir, hostile-code sandbox doğrulaması değildir.

Gerçek [source GUI](phase73/source-gui-final/gui.xml)/
[wheel GUI](phase73/wheel-gui/gui.xml): birer çok adımlı PASS. Açılışta mevcut geçerli
manifest/kod klasörü autoexecute edilmez; explicit inspect no-code/no-commit;
onaysız run reddi; gerçek mean2/n3 worker sonucu, saved artifact ve `example-mean-help`
learning snapshot; platform help/Escape; ayrı crash plugin exit17 sonucu bozmaz;
incompatible API2 ret. Paket silinip proje yeniden açılır, plugin yüklemeden kayıtlı
sonuç okunur. Arayüz yolu gerçek QML sinyalidir; insan testi değildir.

[Source ölçüm](phase73/source-gui-final/measurement.json)/
[wheel ölçüm](phase73/wheel-gui/measurement.json) default2GiB CPU: örneklenmiş toplam
peak source1,465,688,064byte / wheel1,465,073,664byte. Shared pages iki kez sayılabilir,
kısa zirveler kaçabilir; minHW/performance garantisi değildir. [1000px source](phase73/source-gui-final/gui-1000.png)
ajan tarafından incelendi; [1366px](phase73/source-gui-final/gui-1366.png),
[wheel](phase73/wheel-gui/gui-1000.png). Screenshot saved-result/missing-plugin
bağlamındadır; testteki ölçülmüş sonuç ayrıca result.json içindedir.

[Bağımsız örnek source CLI](phase73/example-contract.log)/
[wheel CLI](phase73/wheel-example-contract.log) PASS; manifest/API/dependencies/
finite JSON/kind/RowId sözleşmesini test eder. Beklenen mean2/n3 pytest assertion'ı
ayrıdır. Contract testi bilimsel doğruluk veya güvenlik sertifikası değildir.
[Wheel GUI_SMOKE](phase73/wheel-smoke.log) izole XDG; package opening plugin başlatmaz.

İlk [native failure](phase73/native-initial-failure.log) Capability constructor'ında
method_version yerine mevcut version/semantic_version ayrımı gerektirdi; düzeltildi.
[Contract stale hash](phase73/contract-stale-hash-failure.log) Ruff sonrası örnek
kod hash'i değiştiği için doğru ret verdi; manifest yeni reviewed bytes ile güncellendi.
[Ara input validator import hatası](phase73/native-intermediate-failure.log) son
koşulardan önce düzeltildi. Bu failures korunur, successful gibi sayılmaz.
İlk174focused koşu ayrı revision'dır; son odaklı koşuyla sayılar toplanmaz.

<a id="e73-open"></a>
## E73-OPEN

Full native importer/transform pipeline/model prediction/chart renderer/lesson
catalogue install, ayrı plugin dependency env, imzalı publisher/OS permissions sandbox
yoktur. Bounded SDK arşiv çıktısı bu yeteneklerin tümü uygulanmış gibi gösterilmez.
Accidental worker failure izolasyonu ≠ aynı kullanıcı kötü niyetli koda karşı
source/proje koruma garantisi. Önceki Faz72 live keyring/DP/encrypted project açığı,
Faz71 opaque/full/default budget ve önceki longheap/process/minHW/fiziksel/insan/AT/
offlineinstaller/remoteCI kabulleri korunur. Faz74 başlatılmaz.

## Komutlar

```sh
.venv/bin/python -m pytest -q tests/test_plugins.py
.venv/bin/python -m veri_ufku.plugins.contract_test --manifest examples/plugins/mean/manifest.json --request examples/plugins/mean/request.json --trust-code
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase73.py --output docs/evidence/phase73/source-gui-final
env UV_CACHE_DIR=/tmp/veri-ufku-f73-uv uv build --wheel --no-build-isolation --offline --out-dir /tmp/veri-ufku-f73-dist
env UV_CACHE_DIR=/tmp/veri-ufku-f73-uv uv pip install --no-deps --python .venv/bin/python --target /tmp/veri-ufku-f73-wheel /tmp/veri-ufku-f73-dist/veri_ufku-0.1.0-py3-none-any.whl
```

Wheel testte PYTHONPATH target; measure ayrıca --package-root target. Odaklı suite:
test_plugins/test_privacy/test_share/test_repro/test_code_bridge/test_learning_lab/
test_learning/test_projects/test_workspace. Statik kapılar ve document unittest
ayrı gerçek loglara bağlıdır; bu ürün dış servise yayınlama içermez.

Son odaklı [176source](phase73/source-core-final.xml)/
[176wheel](phase73/wheel-core.xml) PASS; privacy/share/repro/code/learning/ProjectStore/
workspace regresyonu,30SDKnative dahil. Kasıtlı duplicate config.json repro warning'i
ayrı tutulur. Son disk quota publication kontrolü bu geniş koşudan sonra eklendi;
[31source](phase73/source-native-delivery.xml)/[31wheel](phase73/wheel-native-delivery.xml)
SDK tekrarları PASS. Kota aşımında önceki commit/state/pending ve kaynak korunur.
Sayılar toplanmaz; tam depo koşusu denmez.

Son [source GUI](phase73/source-gui-delivery/gui.xml)/
[wheel GUI](phase73/wheel-gui-delivery/gui.xml) birer PASS; aynı çok adımlı kabulün
quota kontrolü sonrası revision'ıdır. Son ölçüm [source](phase73/source-gui-delivery/measurement.json)/
[wheel](phase73/wheel-gui-delivery/measurement.json): peak1,457,778,688byte/
1,467,138,048byte, default2GiB. Önceki ölçümler ayrı revision kaydıdır.
[Son424byte-eşit package](phase73/package-parity-delivery.json),
[build](phase73/build-delivery.log)/[install](phase73/install-delivery.log),
[son bağımsız wheel contract](phase73/wheel-example-contract-delivery.log),
[son wheel GUI_SMOKE](phase73/wheel-smoke-delivery.log). Son screenshotlar
[source](phase73/source-gui-delivery/gui-1000.png)/[wheel](phase73/wheel-gui-delivery/gui-1000.png).

Belge unittest'in [ilk13pass/1fail](phase73/document-fixture-initial-failure.log)
koşusunda, test fixture yeni examples/plugins klasörünü geçici köke kopyalamadığı
için gerçek yerel linkler fixture'da bulunamadı. Fixture yeni örnek klasörünü de
kopyalayacak şekilde düzeltildi; belge kontrolleri zayıflatılmadı. Bu app/runtime
hatası değildir; gerçek son unittest kaydı ayrı tutulur.

Son kapılar: [docs](phase73/docs-gate-delivery.log), [artifact](phase73/artifacts-gate.log),
[learning](phase73/learning-gate.log), [usability](phase73/usability-gate.log),
[Ruff](phase73/ruff-delivery.log)/[format](phase73/format-delivery.log),
[14document unittest15.221s](phase73/document-tests-final.log),
[123package locked check](phase73/lock.log) PASS.413makale/content89;
413static capability coverage10interactive/403article-linked; explicit plugin
activation mevcut registry'de dinamik namespaced ek kayıt oluşturabilir.
[Kimlikli acceptance kayıtları](phase73/acceptance.json). Kaynakta kullanıcı
değişiklikleri/untracked teslimler korunur; stage/commit/push yapılmadı.
