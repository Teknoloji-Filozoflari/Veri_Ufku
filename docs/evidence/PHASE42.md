# Faz42 — ölçüm planı, güç ve bağımsız iki randomize kol

2026-10-11; ENV-42: CPython3.13.15,NumPy2.5.3,SciPy1.18.0,
statsmodels0.15.0,Polars2.0.0,PySide6/Qt6.11.2; Linux offscreen/software.
DEC42-01 açık kullanıcı talimatı ilk bağımsız iki-grup yolunun teknik uygulama
yetkisidir; önceki resmî kabul kapıları korunur.

<a id="e42"></a>
## Teslim ve açık alt işler

42.1 Ölçüm/hipotez planı: birincil metrik/birim, eligibility, ölçüm penceresi,
fixed-horizon stopping, MDE,baseline/SD,alpha/power/allocation/attrition ve
design effect. Mean için ortak-SD Cohen d TTestIndPower; proportion için
arcsine Cohen h NormalIndPower. A priori power, yuvarlanan analyzable/recruitment
n; observed power yok. Proportion power normal yaklaşım, Fisher exact güçle
eşdeğer değil. Missing inflation kayıp yanlılığını düzeltmez.

42.2 Benzersiz birim/RowId ve lexicographic sıra +seed PCG64 Bernoulli yerel
**taslak** assignment. Allocation P(B), tam50/50 garanti değil. Kaynak değişmez;
gerçek kişi tedavisi veya mesaj otomatik atanmaz.

42.3 Tam assigned roster; aynı bağımsız randomizasyon/analiz birimi, bir satır
bir birim. Randomizasyon kanıtı/plan kimliği ve açık kullanıcı onayı; uygulama
kanıtı doğrulamaz, gözlemsel iki grup otomatik randomize etiketlenmez.
Assigned arm, baseline pretreatment SMD, önceden belirlenen descriptive
mean/proportion guardrail ve zarar sınırı; en fazla5 baseline/5guardrail.
Guardrail adjusted çıkarım veya otomatik deney başarı kararı değildir.

Exact binomial SRM tam roster/Bernoulli P(B); p<0.001 diagnostic primary
çıkarımı kapatır. ITT assigned bütün birimler; PP explicit0/1protocol ve
association, randomize nedensel ITT etkisi değil. Assigned/population/observed/
missing/events/PP-excluded paydaları ayrı; attrition kol oranları ve farkı.
Null outcome event0 değildir; eksik outcome tam ITT/PP p/CI'ını kapatır,
proportion worst-case missing sınırı CI değildir.

Mean Welch fark0 p +mutlak t CI; relative point baseline0 iken tanımsız,
mean ratio CI desteklenmez. Proportion Fisher exact p; eşzamanlı Bonferroni
Clopper–Pearson'dan muhafazakâr absolute/relative CI. CI Fisher p ile tersine
eşdeğer değildir; control alt sınır0 ise relative CI sınırsız, sahte sonlu
aralık yok. Constant mean variance için çıkarım unavailable.

Fixed horizon kullanıcı beyanı; planned_total veya ölçüm penceresi tamamlanmadan
çıkarım kapalı. Sequential monitoring kapalı; doğrulanmış alpha-spending/
e-value adapterı yok. F42-P002 paired/P003cluster/P004factorial ayrı alt işler,
bu teslimde **uygulanmadı**. P008/P009sequential de kapalı. Bunlar independent
hesapla taklit edilmez; design effect yalnız1. [ADR043](../adr/043-experiments-phase42.md).

100000 full roster/RAM/CPU/disk/iptal bütçesi; filtreli roster ret. Boolean0/1
rate destekli, decimal/nested/time/weights yok; NaN/inf veya çok büyük ölçüm ret.
Safe JSON plan/result +RowId/typed details parquet; publish kaynak/seed/ölçüm
bağını tekrar doğrular. Dataset/source/config stale save/export engellenir.
Masaüstü QML, mevcut Capability/StatisticsController/spawn/ProjectStore yolu;
worker Qt/ACTIVE almaz, yeni ağ bağımlılığı yok.

## Gerçek doğrulama

İlk37 core passed/1.24s: noncentral t/normal analytic root (allocation0.3/0.5/0.7),
exact SRM küçük fixture, Welch/CP-Bonferroni/Fisher, binary denominators/missing,
PP/full roster, PCG64 seed/ordering, persisted plan/source tamper rollback,
invalid observational/design/sequential/roster ve cancellation.
İlk GUI10 passed/67.13s; GUI açılışta UiTextField türü/accessible purpose düzeltildi.
Görsel kanıt gerçek kaydı açarken yanlış slot çağrısını yakaladı; openSaved ile
fix ve testte bellekteki result temizliği eklendi. İlk koşu final fresh reopen
kanıtı değildir. Son47 source test passed/95.52s;37 core+10 gerçek GUI, fresh reopen için bellekteki
result temizlenir. Source81 ilgili vaka passed/382.91s (ilk fresh-open fix öncesi
başlatılan eski-yeni GUI regresyonu). Son wheel55 hedefli vaka passed/97.09s;
47 Faz42+eski GUI. İlk wheel66 koşu65passed/1eski responsiveness fixture failure:
8s gerçek demo işi timer20tick ölçülmeden bitmiş; ilk izole tekrar timer8s timeout.
Eski test/ürün kodu değişmedi; parallel GUI yükü bittikten sonra son wheel ilgili
tekrar geçti. Önceki başarısız çıktılar korunur; başarı gibi raporlanmaz.

Tam1295 vaka regresyon: **1276 passed/19 skipped/0 failure-error /572.29s**.47 Faz42 passed/0skip.
Dört bağımsız dosya shard; collected/JUnit tam birebir kapsam;
410 source/test/script/lock dosyası koşu boyunca değişmedi.
19 skip haricî isteğe bağlı MariaDB/MySQL/PostgreSQL/S3/Secret Service fixture
eksikliğidir; [ayrıntı](phase42/regression-summary.json),
[JUnit](phase42/full-regression.xml),[koşu](phase42/full-shards.json).

Source/wheel9'ar gerçek QML/spawn/help/Escape/save/fresh-reopen/export/stale ret
akışı;54 screenshot/72 artifact.9 sayısal sonuç birebir eşit.
260 source/wheel/install paket dosyası byte eşit; installed importer/QML smoke
PASS.264 offline article/145 UI bağı/534 named field/189 core English.
Son14 belge unittest passed/8.847s; docs/artifacts/learning/usability/Ruff check-format ve
git diff --check geçti; [gerçek komutlar](phase42/checks.json).
[8 kabul](phase42/acceptance.json),[kaynak GUI](phase42/source-gui-final/walkthrough.json),
[wheel GUI](phase42/wheel-gui-final/walkthrough.json),
[numeric parity](phase42/source-wheel-numeric-parity.json),[paket](phase42/wheel.json),
[görsel inceleme](phase42/visual-review.json).
Bilinen Faz42 ürün hatası son kontrolde yok; yukarıdaki yöntem ve açık alt iş
sınırları geçerlidir. Bu kayıt ilk iki-grup kapsamını tamamlar; bütün varyantlar
veya önceki resmî kapılar tamamlandı iddiası yoktur.

F13 insan;F25 insan/Orca/AT;F24minHW/cold/physical frame; kullanıcının durdurduğu
F27 dağıtım;F28 giriş;F30 büyük SAS;F31clean offline cache açık. Bu fazda physical
GUI/insan/AT/minHW/clean offline install/remote CI koşulmadı. Commit/stage/push
yok; kullanıcı değişiklikleri korundu. Faz43 başlatılmadı.
