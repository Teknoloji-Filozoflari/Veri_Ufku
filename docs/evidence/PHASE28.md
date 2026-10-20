# Faz28 — mevcut uygulama ve profesyonel geçiş denetimi

2026-10-10 UTC / Europe/Istanbul; ENV-28. Kullanıcı yalnız Faz28'i seçti.
Denetim/plan teslim edildi; **Faz28 engelli/deneysel/zorunlu**. Yeni uzman
model, runtime registry veya veri/proje şeması eklenmedi. Faz29–75 engelli,
uygulama başlamadı. Ana kayıt [REQUIREMENTS_MATRIX](../REQUIREMENTS_MATRIX.md).

<a id="e28-audit"></a>
## E28-AUDIT — gerçek kod/test/GUI ve proje

Kilitli dev sync başarılı (46 çözülmüş/44 kurulu paket; lock değişmedi).
İlk tam regresyon: **714 passed,1 failed,234.63s**; tek hata kaynak checksum
izlenebilirliği. [JUnit](phase28/pytest.xml), [log](phase28/pytest.log).
Qt gerçek QML/spawn/import/operations/charts/export/statistics/model/kalıcılık
vakaları bu JUnit'te modül/vaka kimliğiyle eşlenir. [İlk audit](phase28/audit-initial.json)
statik path/registry ve runtime vakaları ayrı alanlarda tutar; kaynak
incelemesi runtime kabulü değildir. İlk AST taraması GUI ResourceSupervisor'ı
jobs içinde bulduğu için audit exit1 verdi; [kaynak](../../src/veri_ufku/jobs/supervision.py)
yalnız app.py GUI parent tarafından import edilir. Kayıt silinmedi;
DEP-28-06 olarak açık mimari yerleşim sınırıdır, analitik Qt ihlali sayılmaz.

[Kaynak GUI](phase28/gui/walkthrough.json) ve [kurulu noneditable GUI](phase28/wheel-gui/walkthrough.json)
8'er gerçek Qt ekranı: Başlangıç, Veri başlıkları, fiziksel tür tablosu,
unique, describe, kısa not,720/%200 not/profil. Profil ve kompakt not görüntüleri
araçla gerçekten incelendi. Native masaüstü/insan/Orca testi değildir.
Sentetik kaynak hash'leri korunur; not açık save/reopen ile saklanır.
[Kurulu import](phase28/wheel-import.log) ayrı /tmp cwd'de aynı sürüm şeması ve
kaynak byte eşitliğiyle gerçek spawn import/proje yeniden açma doğrulamasıdır.

İlk offline isolated build cache'inde hatchling yoktu: [başarısız log](phase28/wheel-build.log).
Kilitli dev ortamın build-system bağımlılıklarıyla offline no-build-isolation
build geçti: [build](phase28/wheel-build-locked.log), [kurulum](phase28/wheel-install.log).
Bu noneditable wheel runtime testi temiz Linux dağıtım paketi kabulü değildir.

[Mevcut Titanic](phase28/existing-project.json) writable=False açıldı: manifest7,
5 dataset sürümü/5 işlem, ACTIVE ve metadata.sqlite byte hash değişmez.
Bu fazda migration/save/conversion yok; kişisel satır/kolon içeriği rapora
alınmadı. Sentetik eski şema0–6, model paketleri ve source fixtures gerçek
full regresyonda açma/migration/backup/readonly/RowId/safe load ile test edildi.

<a id="e28-source"></a>
## E28-SOURCE — açık kaynak revizyonu / DEC-28-03

İlk belge hatası önceden kullanıcı tarafından eklenmiş veri ekranı talimatının
eski kaynak hash'ine uymamasıydı. Eklenen metin Faz26 ile27 arasında, faz
promptlarının dışında1446 UTF-8 byte'dır. Kaynak dosyası ve orijinal
source.sha256 değiştirilmedi. [Tam önceki diff](phase28/source-existing.diff),
[revizyon kaydı](phase28/source-revision.json): offset63716'daki kayıtlı
**tek eklemeyi çıkarmak orijinal efae07bc… hash'ini tam geri üretir**.
Aktif kaynak hash'i1e0f59d3…; iki hash ayrı tutulur.

DEC-28-03, kullanıcının Faz28 gerçek kabul/izlenebilirlik denetimi kapsamında
bu önceden eklenmiş kullanıcı talimatını ayrıca kaydetme kararıdır; yeni kaynak
metni yazma/değiştirme yetkisi değildir. scripts/check_docs.py yalnız tam
kayıtlı ekleme, aktif hash, original hash yeniden yapımı ve bu karar anchor'ı
geçerliyse kabul eder. Sonradan farklı edit/ekleme, bozuk revizyon veya eski
hash'in değiştirilmesi negatif testte reddedilir. Baseline checksum yenilenerek
hata gizlenmedi. İlk başarısız koşu saklanır; onarım sonrası kontroller ayrı.

<a id="e28-gates"></a>
## E28-GATES — Faz00–27 giriş kapısı

Aşağıdaki sayımlar ilk tam koşunun gerçek vakalarıdır; alt yöntem tanıkları
[capability-evidence](phase28/capability-evidence.json) içindedir. Historical
faz durumları korunur; belgeye yazılmış kabul bu koşuda bütün ölçütlerin
çalıştırıldığı anlamına gelmez. 21–23 zaten kullanıcı tarafından seçilmiş
zorunlu/teknik mevcut/sürüyor; ertelendi değildir. Test edilen sınırdaki kritik
veri kaybı/sızıntı vakaları geçti; genel kusursuzluk veya saha başarısı iddiası yok.

| Faz | Giriş kapısı | Gerçek modül vaka sonucu | Ana kayıttaki açık kaynak kabulü | Eski yöntem / ortam kanıtı |
|---|---|---|---|---|
| 00 | zorunlu giriş | 0 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE00.md#e00-source |
| 01 | zorunlu giriş | 27 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE01.md#e01-boundaries, docs/evidence/PHASE01.md#e01-desktop, docs/evidence/PHASE01.md#e01-gui, docs/evidence/PHASE01.md#e01-jobs, docs/evidence/PHASE01.md#e01-package, docs/evidence/PHASE01.md#e01-phase-acceptance |
| 02 | zorunlu giriş | 12 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE02.md#e02-accept, docs/evidence/PHASE02.md#e02-shell, docs/evidence/PHASE02.md#e02-states, docs/evidence/PHASE02.md#e02-tokens, docs/evidence/PHASE02.md#e02-views |
| 03 | zorunlu giriş | 22 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE03.md#e03-bindings, docs/evidence/PHASE03.md#e03-center, docs/evidence/PHASE03.md#e03-depth, docs/evidence/PHASE03.md#e03-schema |
| 04 | zorunlu giriş | 106 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE04.md#e04-projects, docs/evidence/PHASE04.md#e04-publication, docs/evidence/PHASE04.md#e04-recovery, docs/evidence/PHASE04.md#e04-sources, docs/evidence/PHASE04.md#e04-state |
| 05 | zorunlu giriş | 57 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE05.md#e05-gui, docs/evidence/PHASE05.md#e05-help, docs/evidence/PHASE05.md#e05-integrity, docs/evidence/PHASE05.md#e05-parser |
| 06 | zorunlu giriş | 49 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE06.md#e06-excel, docs/evidence/PHASE06.md#e06-gui, docs/evidence/PHASE06.md#e06-help, docs/evidence/PHASE06.md#e06-integrity, docs/evidence/PHASE06.md#e06-json, docs/evidence/PHASE06.md#e06-package, docs/evidence/PHASE06.md#e06-parquet |
| 07 | zorunlu giriş | 29 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE07.md#e07-help, docs/evidence/PHASE07.md#e07-memory, docs/evidence/PHASE07.md#e07-profile, docs/evidence/PHASE07.md#e07-roles, docs/evidence/PHASE07.md#e07-table |
| 08 | zorunlu giriş | 6 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE08.md#e08-center, docs/evidence/PHASE08.md#e08-findings, docs/evidence/PHASE08.md#e08-help, docs/evidence/PHASE08.md#e08-recommendations |
| 09 | zorunlu giriş | 16 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE09.md#e09-contract, docs/evidence/PHASE09.md#e09-help, docs/evidence/PHASE09.md#e09-history, docs/evidence/PHASE09.md#e09-lineage, docs/evidence/PHASE09.md#e09-operations |
| 10 | zorunlu giriş | 33 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE10.md#e10-copy-outlier, docs/evidence/PHASE10.md#e10-engine, docs/evidence/PHASE10.md#e10-gui, docs/evidence/PHASE10.md#e10-help, docs/evidence/PHASE10.md#e10-leakage, docs/evidence/PHASE10.md#e10-methods, docs/evidence/PHASE10.md#e10-policies |
| 11 | zorunlu giriş | 36 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE11.md#e11-engine, docs/evidence/PHASE11.md#e11-formats, docs/evidence/PHASE11.md#e11-formula, docs/evidence/PHASE11.md#e11-help, docs/evidence/PHASE11.md#e11-join-append, docs/evidence/PHASE11.md#e11-lineage-backends |
| 12 | zorunlu giriş | 23 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE12.md#e12-engine, docs/evidence/PHASE12.md#e12-help, docs/evidence/PHASE12.md#e12-interaction, docs/evidence/PHASE12.md#e12-measure, docs/evidence/PHASE12.md#e12-metadata, docs/evidence/PHASE12.md#e12-methods, docs/evidence/PHASE12.md#e12-package |
| 13 | zorunlu giriş | 22 passed/0 failure/0 error/0 skip | F13-S005 | docs/evidence/AUDIT_00_13.md#e-audit-user-deferred, docs/evidence/PHASE13.md#e13-data, docs/evidence/PHASE13.md#e13-guide, docs/evidence/PHASE13.md#e13-package, docs/evidence/PHASE13.md#e13-report |
| 14 | zorunlu giriş | 42 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE14.md#e14-s001, docs/evidence/PHASE14.md#e14-s002, docs/evidence/PHASE14.md#e14-s003, docs/evidence/PHASE14.md#e14-s004, docs/evidence/PHASE14.md#e14-s005, docs/evidence/PHASE14.md#e14-s006 |
| 15 | zorunlu giriş | 30 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE15.md#e15-s001, docs/evidence/PHASE15.md#e15-s002, docs/evidence/PHASE15.md#e15-s003, docs/evidence/PHASE15.md#e15-s004, docs/evidence/PHASE15.md#e15-s005, docs/evidence/PHASE15.md#e15-s006 |
| 16 | zorunlu giriş | 35 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE16.md#e16-s001, docs/evidence/PHASE16.md#e16-s002, docs/evidence/PHASE16.md#e16-s003, docs/evidence/PHASE16.md#e16-s004, docs/evidence/PHASE16.md#e16-s005, docs/evidence/PHASE16.md#e16-s006 |
| 17 | zorunlu giriş | 14 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE17.md#e17-s001, docs/evidence/PHASE17.md#e17-s002, docs/evidence/PHASE17.md#e17-s003, docs/evidence/PHASE17.md#e17-s004, docs/evidence/PHASE17.md#e17-s005, docs/evidence/PHASE17.md#e17-s006, docs/evidence/PHASE17.md#e17-s007 |
| 18 | zorunlu giriş | 26 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE18.md#e18-s001, docs/evidence/PHASE18.md#e18-s002, docs/evidence/PHASE18.md#e18-s003, docs/evidence/PHASE18.md#e18-s004, docs/evidence/PHASE18.md#e18-s005, docs/evidence/PHASE18.md#e18-s006, docs/evidence/PHASE18.md#e18-s007 |
| 19 | zorunlu giriş | 29 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE19.md#e19-s001, docs/evidence/PHASE19.md#e19-s002, docs/evidence/PHASE19.md#e19-s003, docs/evidence/PHASE19.md#e19-s004, docs/evidence/PHASE19.md#e19-s005, docs/evidence/PHASE19.md#e19-s006 |
| 20 | zorunlu giriş | 36 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE20.md#e20-s001, docs/evidence/PHASE20.md#e20-s002, docs/evidence/PHASE20.md#e20-s003, docs/evidence/PHASE20.md#e20-s004, docs/evidence/PHASE20.md#e20-s005, docs/evidence/PHASE20.md#e20-s006, docs/evidence/PHASE20.md#e20-s007 |
| 21 | seçilmiş temel bağımlılık | 20 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE21.md#e21-s001, docs/evidence/PHASE21.md#e21-s002, docs/evidence/PHASE21.md#e21-s003, docs/evidence/PHASE21.md#e21-s004, docs/evidence/PHASE21.md#e21-s005, docs/evidence/PHASE21.md#e21-s006 |
| 22 | seçilmiş temel bağımlılık | 11 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE22.md#e22-s001, docs/evidence/PHASE22.md#e22-s002, docs/evidence/PHASE22.md#e22-s003, docs/evidence/PHASE22.md#e22-s004, docs/evidence/PHASE22.md#e22-s005, docs/evidence/PHASE22.md#e22-s006 |
| 23 | seçilmiş temel bağımlılık | 21 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE23.md#e23-s001, docs/evidence/PHASE23.md#e23-s002, docs/evidence/PHASE23.md#e23-s003, docs/evidence/PHASE23.md#e23-s004, docs/evidence/PHASE23.md#e23-s005, docs/evidence/PHASE23.md#e23-s006 |
| 24 | zorunlu giriş | 10 passed/0 failure/0 error/0 skip | F24-S006 | docs/evidence/PHASE24.md#e24-s001, docs/evidence/PHASE24.md#e24-s002, docs/evidence/PHASE24.md#e24-s003, docs/evidence/PHASE24.md#e24-s004, docs/evidence/PHASE24.md#e24-s005, docs/evidence/PHASE24.md#e24-s006 |
| 25 | zorunlu giriş | 8 passed/0 failure/0 error/0 skip | F25-S001, F25-S002, F25-S004, F25-S006, F25-S007 | docs/evidence/PHASE25.md#e25-s001, docs/evidence/PHASE25.md#e25-s002, docs/evidence/PHASE25.md#e25-s003, docs/evidence/PHASE25.md#e25-s004, docs/evidence/PHASE25.md#e25-s005, docs/evidence/PHASE25.md#e25-s006, docs/evidence/PHASE25.md#e25-s007 |
| 26 | zorunlu giriş | 58 passed/0 failure/0 error/0 skip | Kaynak satırları kabul kayıtlı; yeni fiziksel/insan kanıtı değil | docs/evidence/PHASE26.md#e26-s001, docs/evidence/PHASE26.md#e26-s002, docs/evidence/PHASE26.md#e26-s003, docs/evidence/PHASE26.md#e26-s004, docs/evidence/PHASE26.md#e26-s005, docs/evidence/PHASE26.md#e26-s006 |
| 27 | zorunlu giriş | 2 passed/0 failure/0 error/0 skip | F27-S001, F27-S002, F27-S003, F27-S004, F27-S005, F27-S006, F27-S007 | Yok; Faz27 kabulü eksik |

Açık zorunlu kapılar: F13-S005 gerçek bilgisiz kullanıcı; F24-S006 minimum
fiziksel donanım/cold/input-frame; F25-S001/002/004/006/007 insan/AT ve güncel
çeviri; F27-S001..007 durdurulmuş paket çalışması. F14–20/26 teknik başarıları
F13 bağımlılık kabulünü tamamlamaz. Ortak CORE/UI satırlarının henüz
kapalı olmayanları [audit](phase28/audit.json) ve ana matriste ayrıca korunur.
Yeni remote CI, Debian/Pardus temiz ortam, native Wayland/X11, offline installer
ve fiziksel güç kesintisi bu fazda çalıştırılmadı.

<a id="e28-plan"></a>
## E28-PLAN — kapsam / 47 faz / alt işler

[PRO_CAPABILITY_MATRIX](../PRO_CAPABILITY_MATRIX.md)76 registry kaydı +7 dtype
dilimi,10 fitted model ve DBSCAN ret sınırını test/GUI/yardım/serialization/
limit/maturity ile ana gereksinimlere bağlar. [PRO_PRODUCT](../PRO_PRODUCT.md)
aynı magaza.csv probleminin sade/öğrenen/uzman akışını, fixture seçimi ve gerçek
hedef donanım/ölçüm ayrımını tanımlar. [PRO_ARCHITECTURE](../PRO_ARCHITECTURE.md)
mevcut sözleşmeleri genişletir; InputSchema/ResultArtifact/LearningLink bugün
aynı isimli gerçek sınıfmış gibi sunulmaz. Yeniden yazım yok.

[PRO_WORK_PLAN](../PRO_WORK_PLAN.md) ve [plan JSON](phase28/work-plan.json)
Faz29–75 bütün47 düğümü/kenarı ve552 planlı yöntem/alt yeteneği listeler.
Her yöntem için C/V/G/H/P alt iş kimliği ana matriste; seçilmiş fazda hiçbir
source şartı kaldırılmaz. Tüm transitif atalar graph audit'inde hesaplanır.
Topolojik sayı sırası geçerlidir; kabul kapıları açısından geliştirme engellidir.
DEC-28-01 kullanıcı açık yalnız Faz28; DEC-28-02 önceki isteğe bağlı profesyonel
seçim korunur/erteleme yok. DEC-28-04 F44 randomize ATE→F42 deney kabulü yeni
bilimsel önkoşulu; bağımlılık matrisi/özet/plan aynı kenarı taşır.

F53/F54→21; F55→22; F62/F63/F64/F67→23 ve transitif işler temel kabul
kapanmadan başlamaz. Gelecek F65/66, şimdiki provenance/bütçe güvenliğini
erteme gerekçesi değildir. Büyük faz tek oturumda vaat edilmez; tek yöntem
C/V/G/H/P uçtan uca sonra bir sonraki yöntem.

<a id="e28-limits"></a>
## E28-LIMITS — düzeltme ve açık engeller

DEP-28-01 P1 kaynak izlenebilirliği onarıldı; final belge/negatif kontrolüyle.
DEP-28-02 P1 insan görev kabulü, DEP-28-03 P1 AT/çeviri, DEP-28-04 P1 minimum
donanım, DEP-28-05 P1 Faz27 seçilmiş dağıtım yolu ve temiz paket kabulü açık.
DEP-28-06 P2 supervisor yerleşimi, DEP-28-07 P2 registry destek ayrıntısı,
DEP-28-08 P2 eski measure_phase25 gibi kaldırılmış profileMethod/helpButton'a
başvuran walkthrough araçları. Eski betik bu fazda başarılı diye sunulmadı;
güncel GUI testleri ve measure_data_inspection kaynak/kurulu yolları kullanıldı.

Yeni P0 veri kaybı/sızıntı bulunmadı ifadesi sadece bu JUnit ve salt okunur
proje denemesine ilişkindir. Çözülmeyen P0 ortaya çıkarsa reproducer ve
DEP-28-CRITICAL-* ana kaydıyla Faz28/bağımlıları engelli kalır. Kapıların açık
olması yeterlidir: Faz28 doğrulandı yapılmaz, Faz29 uygulanmaz.

<a id="e28-final"></a>
## E28-FINAL — çalıştırılan son kontroller

Komut/tarih/exit için [checks](phase28/checks.json) ve
[ilk shell koşuları](phase28/execution-records.json); [final audit](phase28/audit.json).
İlk tam714/1 koşu saklanır. Onarımdan sonra belge/artefact/yardım/kullanılabilirlik,
Ruff check/format,14 belge sözleşmesi negatif/pozitif test ve unittest,
kurulu entry smoke ayrıca koşulur. Son tam regresyon **720 passed /236.65s**, [log](phase28/pytest-final.log) ve
[JUnit](phase28/pytest-final.xml).14 belge sözleşmesi testi ve14 kilitli
unittest geçti.151 çevrimdışı makale/91 UI bağı; usability254 named field ve
189 tamamlanmış temel İngilizce mesajı kontrol etti. Docs/artifacts/learning/
usability/Ruff check-format/izole kurulu entry exit0.

Sistem Python unittest73 keşif/59 import hatasıyla exit1: sistem ortamında
PySide6/polars ve diğer kilitli bağımlılıklar yoktur; [başarısız log](phase28/system-unittest.log).
Bu başarısızlık gizlenmez; desteklenen kilitli çalışma ortamı CPython3.13.15
ile14 unittest ve720 pytest başarısı ayrı kayıttır.

[Wheel kanıtı](phase28/wheel-proof.json)205 paket dosyasının kaynak byte
eşitliği, wheel SHA256 ve yüklenen /tmp paketini kaydeder.
[Ortam](phase28/environment.json), [seçilmiş fixture hash listesi](phase28/fixtures.json)
ve [tarihsel performans özeti](phase28/performance-history.json) birlikte okunur;
Faz24 benchmark bu fazda yeniden çalıştırılmadı, minimum hedef kabulü yok.
[Son belge denetimi](phase28/final-review.json) ile rapor sonrası link/plan
kontrolleri ayrıca kaydedilir; çalıştırılmamış gate başarılı değildir.

## Gerçek masaüstü kabul deneme adımları (henüz çalıştırılmadı)

1. Kilitli uygulamayı normal Linux masaüstünde aç; yeni proje oluştur. Dosyayı
   proje olmadan da önizle; proje açıkken oluştur/aç butonu olmamalı.
2. magaza.csv aktar; Gelişmiş kapalı,20 kayıt üst sınırı, kimlik0001 metin,
   tutar Decimal. Verini tanı tam profil; sütun/type adları gerçek şemayla aynı.
3. Tutar için kısa not kaydet/kapat/aç; kompakt sütun adı ve not aynı olmalı.
   Görünüm değişiminde dataset/result kimliği değişmemeli.
4. Histogram ve HTML/PDF/Parquet exportu yeni hedefe yaz; kaynak SHA256 aynı;
   12 kayıt/null2 ve n10/medyan45 doğru. Öğren/F1→Escape akışı işi korumalı.
5. subeler.csv trim preview2/6,apply/undo/redo; aynı içerikli iki Bursa ayrı
   kimlik. Model için sentetik group-time/test-poison fixture'larında test
   ayrılığı, kaynak/no-fit ve tekrar final defteri gerçek GUI'de incelenmeli.
6. Yeni başlayan ve uzman görev süresi/başarı/yardım/kritik hata ayrı kaydedilir;
   Orca, fiziksel8GiB/cold ve temiz paket deneyi uygun ortamında yapılır.
