# Faz63 — sınırlı GUI kod köprüsü ve isteğe bağlı Python süreci

2026-10-15 UTC; DEC63-01; ENV-63. Resmî durum sürüyor/deneysel/isteğe bağlı.
Yalnız açık Faz63 talimatı. Faz64 yetkisi yok. Önceki resmî kapılar korunur.

<a id="e63-scope"></a>
## E63-SCOPE — desteklenen dönüşüm

Rapor → Faz63: seçili dataset ve seçili kolon için önceden hesaplanan numeric
measurement profilini Python/SQLite SQL/notebook ZIP olarak üretir. Full dataset
veya first-N≤10000; ddof0/1. Filtreli/view profile, diğer analiz/modeller ve rastgele
Python'dan GUI'ye ters dönüşüm desteklenmez. Eski başka kolona ait profil reddedilir;
sample sessiz kısaltılmaz. Salt okunur snapshot referansı DatasetVersion,
SourceSnapshotId, ColumnId, boyut/SHA256 taşır; gerçek path/URL/credential bulunmaz.

Her pakette okunabilir run.py, query.sql, recipe.json, dataset-reference.json,
environment.lock.json, requirements.lock, README.txt ve integrity.json vardır.
Notebook paketinde nbformat4.5 analysis.ipynb eklenir: outputs=[],execution_count=null,
cell ID/source hash, recipe/reference/engine metadata. Kaynak veri/satır/örnekler,
profil sonuçları, kolon adları, kullanıcı semantic note, credential veya env token
pakete kopyalanmaz. Girdi alanları kapalı whitelist; kaynak kimlikleri UUID ile
sınanır. Export yeni/proje dışı0600dosya, mevcut kaynak/çıktı/symlink üzerine yazmaz.

Python aynı GUI Decimal precision80 profil motorunu çağırır; örnek satırları dışarı
vermeden counts/numeric/used_n/population_n/scope/sampling özeti döndürür. Script,
`--project /LOCAL/PROJECT --output /NEW/result.json` ile açık çalışır; projeyi
writable=False açar, sürüm/snapshot/kolon/fingerprint doğrular. Kaynak snapshot'a
ve proje ACTIVE'ye yazmaz. Çıktı istatistiklerinin kendisi hassas olabilir; kullanıcı
sonucu ayrıca gözden geçirmelidir.

SQL SQLite dialect'tir: input_data(value) alias'ı, :finite_bound parametresi;
used/null/finite count,min/max/AVG. Median/std/quantile veya bütün GUI profili diye
sunulmaz. Float/Int fiziksel tipler, sonlu |value|≤2^53,≤100000row; NaN/inf,
Decimal/UInt64/nested reddi, sessiz null/coercion yok. Runner yalnız seçili kolonu
geçici memory SQLite'a yükler, ardından query_only transaction +authorizer ile
SELECT/READ/FUNCTION dışını reddeder. SELECT prefix güveni yok. Mean Float64 ile
GUI Decimal'a toleranslı karşılaştırılır, byte eşitliği iddiası yok. query.sql
okunur ve kapalı şablonla karşılaştırılır; edit sessiz göz ardı edilmez, reddedilir.

Environment lock CPython tam sürüm/implementation/machine, mevcut runtime package
closure exact name==version ve ilgili engine source hash içerir. Env değerleri,
index URL veya secret alınmaz. Optional Jupyter backend'i veya model paketleri
çekirdeğe eklenmedi; mevcut core transitive packaging parser kullanılır. Lock aynı
uyumlu wheel/build ortamını doğrular; requirements.lock wheelhouse/hash-pinned
binary installer değildir. Temiz offline kurulum yapılmış sayılmaz. Uygulama kendi
başına paket/model indirmez.

Run sonuç zarfı result+provenance: recipe/reference/environment ve çalıştırılan
script hash'i; SQL'de query hash. Notebook saved-cell source hashleri ile harici
IPython sağlarsa son100input'un yürütme sırası hashleri kaydedilir; kaynak/secret
metni kaydedilmez. Harici editor/history instrumentation kullanıcı tarafından
kaldırılabilir; tüm notebook editlerini otomatik izlediği iddiası yok. Yeni kernel,
restart/run-all ve ortam tutarlılığı görünür. Harici managed Jupyter bağlantısı
mevcut değil/doğrulanmadı; notebook JSON ve sırayla Python-cell fixture doğrulaması,
gerçek Jupyter server/kernel runtime kabulü değildir.

<a id="e63-workspace"></a>
## E63-WORKSPACE — explicit fresh process, sandbox değil

Kod alanını etkinleştir + Bu Python hücresini açıkça çalıştır ayrı eylemler.
Her çalıştırma CPython -I -u, yeni process/session/group; persistent global/kernel
state yok. Proje veya hash kaydı açmak, source/cell load veya exec yapmaz.
16KiBUTF8/NULsuz cell stdin pipe ile nonblocking≤8192byte/tick ile gider; user code
ne commandline'da ne geçici code file'da saklanır. Cwd özel task cache; argv yalnız
sabit bootstrap/bütçe. Environment PATH/locale/TZ/thread allowlist; keyring çağrısı
ve envsecret/token aktarımı yok. Keyring'e secret yazma veya export yolu eklenmedi.

Arbitrary code aynı kullanıcı dosya/ağ haklarına sahiptir. Ayrı process güvenlik
sınırı değildir; doğrulanmış OS sandbox/seccomp/cgroup/network izolasyonu yok.
Kodun isteyerek kaynak/proje/başka dosyaya yazmasını veya setsid ile kaçan descendant
bütün eylemlerini engellediği iddia edilmez. Bu uyarı ürün ekranında katlanmadan
kodun üstünde, etkinleştirme checkbox'ında ve yardımda görünür.

ComputeBudget ortak RAM/CPU/thread/disk, wall≤min600/global bütçe; parent Qt timer25ms,
nonblocking stdout/stderr toplam64KiB, per-tick drainbounded. Üretim varsayılanı
2GiB/2CPU/600s değiştirilmedi. CPU/RLIMIT_AS/FSIZE/NOFILE/affinity kernel bootstrap'ta;
FSIZE≤min16MiB,tempbudget. Parent ResourceSupervisor toplamRSS/cache disk politikasına
bağlı. Bunlar best-effort resource denetimi, adversarial OS güvenlik sınırı değil.
Timeout/cancel/output_limit ayrı terminal statü; TERM→KILL grace, aynı process-group
çocuklar sonunda öldürülür. Kaçan başka session tam güvenli kısıtlanmış sayılmaz.
RAM hatası child MemoryError/failed veya parent budget_exhausted olarak görünür.

Output plain text, ANSI/control temizleme ve bearer/token/password/URI pattern
maskelemesi; tam secret dedektörü değildir. Exception yalnız tür, mesaj/traceback/
source yok. Ham veya maskeli stdout/stderr/code source proje/log/export'a otomatik
kaydedilmez. Yalnız volatile oturumda gösterilir; notebook çıktısı olarak export
edilmez. Kaydet butonu yalnız hash/config kaydıdır. Hatalı büyük hücre eski geçerli
metni sessiz çalıştırmaz. Her edit hash/config revision'ı değiştirir; explicit save
veya execute mevcut tek neural_store/ProjectStore atomik journal içinde CodeRun/v1
oluşturur. Önce hash/config running kaydı durable, sonra code launch. Worker Qt/ACTIVE
almaz; yayın parent executor'dadır. Status/duration/exit/output bytecount, codehash,
previous hash, revision, environment, Provenance ve önceki test-use IDs korunur.
Kaynak/çıktı saklanmadığından kayıt açma kodu geri getirmez; tekrar çalıştırmak için
kullanıcı yeniden hücre sağlar. Güvenli model artifact veya istatistik/final test
puanı iddiası yok. Experiment registry aynı run ID'leri ve code_recipe paramlarını
kullanır; ikinci registry kurulmadı, önceki Faz16 defteri silinmez.

<a id="e63-validation"></a>
## E63-VALIDATION — gerçek kanıtlar

[Ortam](phase63/environment.json),[kabul kayıtları](phase63/acceptance.json),
[doğrulama](phase63/verification.json),[kapılar](phase63/gates.json),
[frozen kaynak](phase63/frozen-head.json),[wheel](phase63/wheel.json).
Kaynak core ve kurulu noneditable wheel core ayrı JUnit; gerçek QML export/başlat/
timeout/iptal/hash/edit/reopen ve okunur screenshot yolları ayrı tutulur. Önceki
başarısız alt koşular silinmez. Tam depo regresyonu/physical/human/AT/minimum hardware/
clean offlineinstaller/remoteCI veya managed Jupyter doğrulaması iddiası yok.

İlk native1fail fixture semantic_metadata private_note içerip role alanı eksikti
[source-native-first](phase63/source-native-first.xml); fixture düzeltildi. İkinci
native1fail ProjectStore context-manager varsayımı
[source-native-second](phase63/source-native-second.xml); contextlib.closing ile
readonly referans resolver onarıldı. Sonra15pass
[source-native-third](phase63/source-native-third.xml),15pass provenance,
19pass/1fail boş Parquet fixture (mevcut adapter boş tabloyu reddeder)
[source-native-current](phase63/source-native-current.xml); Null fiziksel tip
reddi ve sample kontrolüne çevrildi.22pass final/22pass stdin öncesi/sonrası ayrı
koşulardır; son24native [source-native-latest](phase63/source-native-latest.xml).
İlk GUI3pass/1fail test helper aynı context-manager varsayımı
[source-gui-first](phase63/source-gui-first.xml); sonraki7pass
[source-gui-current](phase63/source-gui-current.xml). Bunlar tek birleşik başarılı
koşu olarak toplanmaz; final counts verification.json içinde.

İnceleme kaynakları2026-10-15:
[Jupyter notebook format](https://nbformat.readthedocs.io/en/latest/format_description.html),
[Python subprocess](https://docs.python.org/3.13/library/subprocess.html).
Uygulama yardımındaki adresler metin referansıdır; otomatik ağ isteği yok.

## Açıklar

Diğer GUI yöntemlerinin kod üretimi, serbest Python→GUI dönüşümü, persistent kernel,
managed Jupyter bağlantısı, güvenli OS sandbox yok. Kodun keyfi I/O'su provenance
ile otomatik veri lineage'a çevrilmez. GUI2GiB uzun retainedheap ve önceki resmî
kabuller [önceki hafızada](phase63/prior-project_state.txt) korunur; bu fazdaki küçük
GUI yollarının geçmesi onları kapatmaz. Faz64 başlamadı; stage/commit/push yapılmadı.

## Son teknik sayılar ve sınırları

142source [core](phase63/source-core-final.xml) /142wheel
[core](phase63/wheel-core-final.xml);24native dahil, tam depo regresyonu değil.
[Source GUI](phase63/source-delivery-gui/walkthrough.json),
[wheel GUI](phase63/wheel-final-gui/walkthrough.json):7şer case;3format exportunun
script runner'ı aynı GUI profil referansına karşı da çalıştırılır,7case içinde.
[Source outputcaption](phase63/source-output-caption/walkthrough.json),
[wheel outputcaption](phase63/wheel-output-caption/walkthrough.json): ayrı1şer başarı;
7+1tek8pass aggregate diye sunulmaz. Ekrandaki masked stdout Türkçe metin ve[MASKED]
ile testlidir, log/proje çıktısında secret sentinel yoktur. UI timer tick ve cancel
<4s; kernelPID GUIpid'den farklı. Proje close/open ve record open code launch yapmaz.
355byte-eşit finalpackage;4freshXDG;7kapı/14docunit. Önceki source7pass
[source-final-gui](phase63/source-final-gui/walkthrough.json) PIDguard/GUIrunner
assertion öncesi ayrı koşudur; son deliverykanıtlarıyla karıştırılmaz.

Tekrarlama: `.venv/bin/python -m pytest -q tests/test_code_bridge.py`;
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase63.py --output ABS_PATH`;
`--package-root TARGET` noneditable wheel ve `--only success` dar outputcaption yolu.
Üretim2GiB bütçe fixture'da artırılmadı. Küçük bu akışların geçmesi önceki uzun
retainedheap/minimum hardware kapısını kapatmaz. Final verification gerçek JUnit
counts, wheel/source hashes, gateexit ve smoke kayıtlarını assert eder.
