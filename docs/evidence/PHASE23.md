# Faz23 — tarif yeniden uygulama ve izleme teknik kabul

2026-10-09 Europe/Istanbul, ENV-23. Linux x86_64, kilitli CPython3.13.15,
PySide6/Qt6.11.2, offscreen/software. Açık Faz23 kullanıcı seçimi; önceki
insan/bağımlılık kabulü açık: sürüyor/deneysel/zorunlu. Faz24 başlamadı.

<a id="e23-s001"></a>
## E23-S001 — yeni veride gerçek yeniden uygulama

operations/recipes.py, recipe_worker.py, ui/recipes.py, RecipePanel.qml.
Sürümlü dataset/operation geçmişi aynı proje deposuyla; kaynak korunur.
Yeni CSV/Parquet içe aktarma, gerçek QML/spawn/dry-run/apply/reopen.

<a id="e23-s002"></a>
## E23-S002 — declarative tarif ve güvenli eşleme

AnalysisRecipe/v1 kapalı JSON/OperationSpec/yöntem sürümü, kolon/tür/rol/birim/
ordinal sıra ve parametre önkontrolü. Üç aşama source/column mapping, dry-run,
adım etki/hata/blocked. computed col() AST referansı taşınır; literal korunur;
rename/drop/computed ve iki kaynaklı JOIN yeni kimlik fixture'ları gerçek testli.
Genel cleaning ve relational motorun aynı doğrulayıcıları kullanılır; bu fazda
her önceki alt yöntemin ayrı yeni-dataset fixture'ı çalıştırılmış iddiası yok.

<a id="e23-s003"></a>
## E23-S003 — analiz tarifi ve fitted pipeline ayrı

SafeModelPackage/ModelCard Faz20 yolu; transform/predict, fit spy testleri.
Modeli uygula ayrı; Yeniden eğit aktif veri için hazırlık formunu açar, eğitim
ayrıca başlatılır. Eski model/veri/fit üyeliği korunur. Güvenli metin/DBSCAN
paketinin önceki destek sınırları korunur; sessiz eğitim fallback'i yok.

<a id="e23-s004"></a>
## E23-S004 — drift ve sonradan hedef

Tam snapshot≤100000 betimsel null/kategori/sayısal özet ve schema/rol değişimi;
ilk30 kategori+diğer açık. Test/p/eşik yok; n/toplama etkisi ve model başarısızlığı
olmadığı görünür. Nested/binary/tarih dağılım özeti desteklenmedi etiketli.
DelayedPerformance/v1 unique/non-null aynı türde kimlik eşlemesi; satır sırası
kullanılmaz. MAE/RMSE ve accuracy; unmatched/invalid/scored ayrı. Hedef veya
geçerli eş yoksa metrics=null. Training/model/prediction/target refs+hash ve
mapping yeni raporda saklanır; final test değildir.

<a id="e23-s005"></a>
## E23-S005 — yardım

Katalog31/147; workflow-recipe/drift/model, İzleme ağacı ve capability/QML
bağları. Şema uyumu, tekrar akış, drift/örneklem, apply/retrain ve hedef yokluğu.
Yeni try_action yok. [ADR-026](../adr/026-recipes-monitoring-phase23.md).

<a id="e23-s006"></a>
## E23-S006 — kabul kontrolleri

Testler: tests/test_recipes.py, tests/test_recipes_gui.py ve mevcut
lifecycle testleri. Aynı veri/seed değer ve etki eşitliği; missing/type/role,
hostile JSON, computed literal/ref ve yeni JOIN kaynakları; batch ikinci copy
ve save fault'larında ACTIVE/state/reopen korunumu. Yeni run/version/lineage
UUID'leri ayrı yürütmede yenidir; sonuç değerleri deterministiktir.

## Gerçek kontrol kayıtları

Kontrol sonuçları tamamlanan gerçek komut kayıtlarıyla aşağıda kayıtlıdır.
İnsan masaüstü/Wayland/yeni remote CI/minimum donanım ve temiz offline kurulum
bu yerel teknik kabulden çıkarılmaz.

| Kimlik | Gerçek kontrol | Sonuç / kanıt |
|---|---|---|
| E23-LOCK | `uv sync --locked --group dev` | Geçti; [sync](phase23/sync.txt); yeni bağımlılık yok |
| E23-DOCS | Sistem ve kilitli check_docs | Geçti; [sistem](phase23/system-docs.txt), [kilitli](phase23/docs.txt) |
| E23-ARTIFACT | Kilitli check_artifacts | Geçti; [artifact](phase23/artifacts.txt) |
| E23-HELP | Kilitli check_learning | Geçti;147 makale/91 UI bağı; [learning](phase23/learning.txt) |
| E23-RUFF | Ruff check ve format --check | Geçti; [check](phase23/ruff-check.txt), [format](phase23/ruff-format.txt) |
| E23-TARGET | Recipe/GUI/lifecycle hedefli pytest |56 geçti; [targeted](phase23/targeted.txt) |
| E23-UNIT | Kilitli unittest discover |9 belge testi geçti; [unittest](phase23/unittest.txt) |
| E23-SYSTEM-UNIT | Sistem python3 unittest discover | Başarısız: sistem Python3.14.7 PySide6/Polars içermiyor;61 kontrol/52 import hatası; [system](phase23/system-unittest.txt). Başarılı sayılmadı. |
| E23-SOURCE | Offscreen/software source ölçümü |120/100000 tam kayıt; [source](phase23/source.json), [log](phase23/source.txt) |
| E23-WHEEL | Build/install + noneditable wheel aynı ölçüm | Geçti; [build](phase23/build.txt), [install](phase23/install.txt), [wheel](phase23/wheel.json), [log](phase23/wheel.txt) |
| E23-ENTRY | Kurulu bin/veri-ufku --smoke-test | GUI_SMOKE PASS; [entry](phase23/entry.txt) |
| E23-INTEGRITY | Son14 source/wheel dosya SHA256 | Tam eşitlik; [integrity](phase23/integrity.json); [ENV-23](phase23/environment.json), kaynak prompt hash kayıtlı/kaynak korunmuş |

Batch ikinci adım copy, artifact/metadata/manifest fault injection ve üç gerçek
SIGKILL noktasında before/after ACTIVE sınırı denetlendi; ikinci örnek read-only.
Recipe new ColumnId/scoped forked source/AST literal/type alias testleri gerçek.
Çalışma sırasında ilk Ruff biçim/import düzeltmesi ve iki eski öğrenme katalog
fixture'ı güncellendi: sözlük102 ve yayımlanan İzleme aşaması10. İlk başarısız
[pytest](phase23/pytest-initial.txt), [Ruff](phase23/ruff-check-initial.txt),
[format](phase23/ruff-format-initial.txt) korunmuştur; son sonuç yerine geçmez.

Kaynak/wheel gerçek Qt ekranları: [source geniş](phase23/source-recipe-120-1366.png),
[source dar](phase23/source-recipe-120-720.png),
[wheel geniş](phase23/wheel-recipe-120-1366.png),
[wheel dar](phase23/wheel-recipe-120-720.png). Dar kaynak ve wheel görüntüleri
incelendi; seçiciler kayıtlı eşlemeyi görünür tutar (QML currentValue testi).
Kaynak/kurulu paket120/100000 akışı Python TCP bağlantısı parent ve spawn'da
engellenerek geçti. Bu çalışma kanıtıdır; OS arayüzleri veya temiz offline
kurulum doğrulanmadı. Model no-fit kabulü monkeypatch fit spy ve paket hash/
training reference kontrolüyle; hedefli gerçek GUI ölçümde120 kimlik eşleşti.
Performans raporu yeni hedefin keşifsel sonucu, hedef yokken metrics=null.

Tarif sınırı2MiB/100 adım/100 kaynak; izleme/performans100000 kayıt ve kategori
ilk30+diğer. Integer/Decimal dağılım özetleri Decimal80 metinle tam hassas;
performans Decimal ve2^53 üzeri ölçümde kontrollü ret. Yeni execution ve köken
UUID'leri aynı bilimsel değer çıktısına rağmen ayrı kimliklerdir. Gerekli
şema tam kayıtlı kaynak kontratıdır; sessiz eksik kolon kabulü yok. Otomatik
istatistiksel drift testi/alarm eşiği veya başarı/failure kararı üretilmez.

E23-FULL — Kilitli `uv run --frozen pytest -q`: 618 test geçti (221.43s (0:03:41)). [Tam regresyon](phase23/pytest.txt).
Kaynak120/100000 dry-run:1.580/1.994 saniye; wheel1.561/2.185 saniye.
Bu sentetik üç kolonlu ölçüm minimum donanım/latency garantisi değildir.
Son teknik kabul tamamlandı; insan/bağımlılık kapısı açık olduğundan faz
sürüyor, yetenek deneysel, kapsam zorunlu. Faz24 başlatılmadı.
