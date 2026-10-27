# Faz72 — bounded yerel privacy teknik teslim

2026-10-16 DEC72-01 / ENV-72. Açık Faz72 talimatı; Linux desktop, CPU,
kilitli CPython3.13.15 `.venv`. Resmî sürüyor / deneysel / isteğe bağlı.
[Önceki durum](phase72/prior-project_state.txt) ve bütün eski kabul açıkları korunur.
[ADR073 / tehdit modeli ve kapsam](../adr/073-privacy-phase72.md).

<a id="e72-scope"></a>
## E72-SCOPE

Rapor → PII, redaction ve retention. Pattern/kolon adı adayları, sayımlar ve ilk5
RowId; ham PII örnekleri bulguya konmaz. Kullanıcı ColumnId kararları ve gerekçeyi
DatasetVersion/fingerprint'e bağlar.1..16kolon mask/drop/pseudonym/keep; keep yalnız
not-pii, secret alan/desen engeli override edilmez. Seçilmemiş kolonlar çıkmaz.
32MiB snapshot/10000row/64scan column; export32MiB expanded, alias kolonlar,
CSV/Parquet/manifest ZIP. Null korunur; CSV formula escape; nested/binary keep kapalı.
Internal RowId/SourceRecordId export edilmez; yerel dataset kimlikleri/kaynak değişmez.

HMAC-SHA256 proje/ColumnId domain separation; standart pyca Fernet authenticated
export encryption. Keys yalnız Linux Secret Service, referans manifestte; dosya/env
fallback veya overwrite yok. Key kaybı decryption/aynı pseudonymi engeller, escrow
ve reset-backdoor yok. Key create servis işlemi iptalden önce tamamlanmış olabilir.
Crypto işlemi explicit worker'da; Qt parent key almaz. Şifreli paket inceleme closed
ZIP members/hash/rows doğrular; model/user-code deserialize veya extract yapmaz.
Fernet memory-only küçük export içindir; canlı proje storage şifreli **değildir**.
Hash/HMAC/mask anonimlik ve DP sağlamaz; linkage/frequency riski açık.

PrivacyEvent/v1 mevcut append-only ProjectStore results journal/Provenance/atomik
ACTIVE protokolünü kullanır. Yerel history güçlü nonrepudiation veya değiştirilemez
audit değildir. Ortak lineage graph genişletildi; dataset düzeyindeki kayıtlı
bağların muhafazakâr closure'ı model/rapor/analiz için **olası** PII bağı gösterir.
Eski eksik provenance, ColumnId/learned parameter ve dış kopya ilişkisi uydurulmaz.

Retention1..3650gün manuel politikadır, otomatik silme yok. Cleanup önizleme+hash+
açık onay ve yeniden doğrulamayla sadece owned idle eski privacy scratch dosyaları
siler.128dizin/toplam32MiB; flat marker/payload.zip/sealed.vupseal allowlist,
symlink/hardlink/unknown file/live PID koruması. Kaynak/current/historical dataset,
manifest/SQLite/ACTIVE/model/rapor/dış export silinmez. General artifact purge,
secure erase veya machine-unlearning yoktur. Silme geri alınamaz; history yayın
hatasında silinen scratch geri getirilmiş gibi sunulmaz.

<a id="e72-validation"></a>
## E72-VALIDATION

[Ortam](phase72/environment.json), [416 byte-eşit kurulu paket](phase72/package-parity.json),
[kurulu modül yolu](phase72/wheel-import.log). [222source](phase72/source-core.xml)/
[222wheel](phase72/wheel-core.xml) PASS:15native privacy dahil share/repro/report/
code/security/learning/jobs/ProjectStore odaklı regresyon. Tam depo testi değildir.
Duplicate config.json uyarısı kasıtlı malicious repro fixture'ıdır.

Native privacy; gerçek Parquet kaynağı, email/secret redaction, kaynak hash/RowId
koruma, policy/source/preview bağı, yanlış karar reddi, journal append-only/reopen,
stdlib HMAC bağımsız referansı ve gerçek Fernet encrypt/decrypt/tamper/wrong-key,
manifestte key olmaması, hatada secret exception metni bastırma, namespace/key
üzerine yazmama, stale cleanup planı/symlink/hardlink/live PID/source koruması ve
mevcut lineage graph'ta gerçek rename/profile ilişkisi. Keyring stub testi yalnız
adapter sözleşmesidir; gerçek servis kanıtı değildir.

[Source GUI](phase72/source-gui/gui.xml)/[wheel GUI](phase72/wheel-gui/gui.xml) birer
PASS: gerçek QML→spawn scan, insan onaysız ret, version-bound policy, preview,
maskeli ZIP export, retention event, gerçek orphan scratch deletion+history,
kaynak koruma, unavailable encrypted-open hata, yardım/Escape, gerçek worker
cancel, yeniden açmada kayıtlar. Şifreli export GUI'si canlı keyring ile bu ortamda
doğrulanmış değildir. İki [source](phase72/source-gui/measurement.json)/
[wheel](phase72/wheel-gui/measurement.json) kayıt default2GiB CPU bütçesindedir.
Örneklenmiş toplam peak source2,025,664,512byte / wheel2,032,570,368byte; 2GiB'ye
yakındır. Geliştirici donanımı, örnekleme ve shared pages sınırları vardır; minHW,
performans garantisi veya önceki longheap açığının kapandığı kanıtı değildir.
[1000px source görüntüsü](phase72/source-gui/gui-1000.png) ajan tarafından incelendi;
[1366px](phase72/source-gui/gui-1366.png), [wheel görüntüsü](phase72/wheel-gui/gui-1000.png).

[Gerçek local TLS HTTP11test](phase72/source-http-authorized.xml) PASS: redirect,
pagination duplicate/gap/mutation/loop/external, timeout/cancel, secret reflection,
açık ağ eylemi. İlk [sandbox11error](phase72/source-http.log) socket PermissionError
olduğu için başarı sayılmadı; izinli aynı komutla loopback server'da tekrarlandı.
DB/S3 ve bütün network backend'ler bu fazda yeniden test edildi sayılmaz.

[Secret Service read probe](phase72/keyring-probe.log) kontrollü hata; varsayılan
live daemon yok. [Entegrasyon testi](phase72/keyring-integration.xml) **1skip**;
[keyring log](phase72/keyring-integration.log). `tests/test_privacy_keyring.py`
gerçek daemon verildiğinde generate/load→pseudonym/sealed export→inspect yolunu
çalıştırır; bu ortamda live key handling/pseudonymization entegrasyonu doğrulanmadı.
Kernel crypto testlerini canlı keyring kabulüyle karıştırmayın.

[Optional absent smoke](phase72/optional-absent-smoke.log): cryptography/keyring
import ve discovery yokluğu simüle edildi; kurulu GUI açıldı, explicit crypto
anlaşılır ret verdi. [Probe kodu](phase72/optional-absent-probe.py).
[İzole wheel GUI_SMOKE](phase72/wheel-smoke-isolated.log) PASS. Gerçek temiz OS offline
kurulum veya ağ arayüzü kapalı kabul değildir. İlk non-isolated smoke exit2/çıktısız
oldu; izole XDG tekrarı geçti, kök neden kesin kapandı iddiası yok. İlk optional
probe'da yapay find_spec ImportError Qt property warnings üretti; [log](phase72/optional-probe-initial.log),
son probe gerçek yokluk gibi None discovery +ImportError import ayrımını kullanır.
İlk GUI test teardown ve yanlış yardım property hataları [ilk](phase72/gui-first-failure.log)/
[yardım](phase72/gui-help-failure.log) kayıtlarında; test helper düzeltildi.

<a id="e72-open"></a>
## E72-OPEN

Live Secret Service generate/load ve encrypted/pseudonym GUI yolu doğrulanmadı;
F72-P003/P006 tam entegrasyon kabulü açık. Canlı proje encryption mevcut değil,
ihtiyaç/tehdit modeli değerlendirildi. DP mevcut değil; sensitivity ve cumulative
privacy budget accountant yok. General project artifact purge/secure erase yok.
Import/code/plugin/network hedefli yeniden denetimi pentest, legal compliance veya
üçüncü taraf kod güvenlik sertifikası değildir. Fiziksel/human/AT/minHW/offlineinstaller/
remoteCI ve önceki tüm resmî açıklar korunur. Faz73 için yetki yoktur.

## Çalıştırma

```sh
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest -q tests/test_privacy.py tests/test_share.py tests/test_repro.py tests/test_report_builder.py tests/test_code_bridge.py tests/test_security_audit.py tests/test_learning_lab.py tests/test_learning.py tests/test_jobs.py tests/test_projects.py
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase72.py --output docs/evidence/phase72/source-gui
.venv/bin/python -m pytest -q tests/test_connectors.py -k http
.venv/bin/python -m pytest -q -rs tests/test_privacy_keyring.py
env UV_CACHE_DIR=/tmp/veri-ufku-f72-uv uv build --wheel --no-build-isolation --offline --out-dir /tmp/veri-ufku-f72-dist
env UV_CACHE_DIR=/tmp/veri-ufku-f72-uv uv pip install --no-deps --python .venv/bin/python --target /tmp/veri-ufku-f72-wheel /tmp/veri-ufku-f72-dist/veri_ufku-0.1.0-py3-none-any.whl
```

Wheel testte `PYTHONPATH=/tmp/veri-ufku-f72-wheel`; measure ayrıca
`--package-root /tmp/veri-ufku-f72-wheel`. Paket build/lock/install logs bu dizindedir.
Optional extra privacy kilidi için eksik metadata açık tool izniyle paket dizininden
alındı; ürün ağ eylemi, model indirme veya sistem paket kurulumu yapılmadı.
Belge/artefact/learning/usability/Ruff/document kapıları ayrı loglardadır.

Son kapılar: [docs](phase72/docs-gate-final.log), [artifacts](phase72/artifacts-gate.log),
[learning](phase72/learning-gate.log), [usability](phase72/usability-gate.log),
[Ruff](phase72/ruff-final.log)/[format](phase72/format-final.log),
[14document unittest](phase72/document-tests.log) PASS. Son
[15source/1skip](phase72/source-privacy-delivery.xml)/
[15wheel/1skip](phase72/wheel-privacy-delivery.xml) privacy tekrarları PASS/explicit
unavailable; 222odaklı koşuyla toplanmaz. [Kimlikli kabul kayıtları](phase72/acceptance.json).
412makale/content88;412capability coverage10interactive/402article-linked.

Devir kontrolü: önceki kurulu wheel/build `/tmp/veri-ufku-f72-*` dizinleri artık
bulunmadığından byte karşılaştırması yeniden çalıştırılamadı; bu yeni bir wheel
başarısı sayılmadı. Kalıcı package-parity manifestindeki416kaynak dosyasının SHA256
değerleri güncel kaynakla yeniden karşılaştırıldı ve değişmediği doğrulandı.
Yukarıdaki wheel testleri teslim sırasında kaydedilmiş gerçek koşulardır; son
belge güncellemesi sırasında tekrar çalıştırılmış gibi sunulmaz.
