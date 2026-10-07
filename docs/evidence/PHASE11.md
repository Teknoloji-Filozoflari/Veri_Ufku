# Faz11 — dönüşüm, birleştirme ve kaynak adaptörleri kanıtı

2026-10-07 / ENV-11: yerel CachyOS Linux7.2.9 x86_64/glibc2.44, Ryzen7 8845HS/32GB/Btrfs/tmpfs; locked CPython3.13.15/PySide6Qt6.11.2/Polars2.0.0/DuckDB1.5.6(dev), offscreen/software. Olgunluk deneysel; yalnız Faz11. [Karar ve destek sınırları](../adr/014-transformations-phase11.md). Yeni kullanıcı masaüstü/minimum donanım/uzak CI ayrı doğrulanmadı; manuel denemeler kullanıcı isteğiyle sonra toplu yapılacak.

<a id="e11-engine"></a>
## F11-S001 — sürümlü dönüşüm motoru

Yollar operations/formula.py, relational_contracts.py, relational.py, engine.py/contracts.py; storage/project_model.py/project_store.py. Dokuz tipli işlem, manifest7 input_version_ids, kalıcı output schema/ColumnId, immutable Parquet ve aynı full önizleme çıktısının atomik yayını. Undo birincil zincire, redo aynı çıktı/kimliklere; ikinci kaynağın immutable bağı saklanır. Copy, sonraki cleaning/roles ve branch kuralları korunur. tests/test_relational.py ve test_relational_gui.py her dönüşümü apply/undo/redo/reopen veri eşitliğiyle denetler. Kaynak hash kontrolü, eski ikinci sürüm reddi, köken sahte üyelik reddi, çıktı symlink reddi, yayın fault ve iki gerçek join SIGKILL sonrası eski veya tam yeni durum kontrol edildi. Ortak Phase09/10 disk/crash/iptal regresyonları korunur.

<a id="e11-formula"></a>
## F11-S002 — güvenli AST ve hassasiyet

Formula col bağları kalıcı kimliktir; GUI okunabilir ad eşlemesini gösterir. Python ast.parse yalnız parser; eval/exec, attributes/import/lambda/comprehension/file/network çağrısı yok. Whitelist fonksiyonlar ve limitler ADR-014'te. Bağımsız [2.10,0,null] ×2 → [4.20,0,null]; [2,0,null] için8/x reject ve açık null → [4,null,null], bir zero_division/iki yeni null. Yeniden adlandırmada aynı ColumnId formülü çalışır. 0.1→Float64 kaybı ve Int64 overflow reddedilir. Date parçaları Europe/Istanbul aynı UTC anından ay2 üretir; grup minimumu birbirinden1ns farklı girdiden doğru ilk anı korur. CSV timezone toplulaştırmada korunur; timezone kaybettiren naive hedef reddedilir. Null/Boolean/type politikaları tarif/yardımda açıklanır.

<a id="e11-methods"></a>
## Yöntem başına kabul eşlemesi

ENV-11 /2026-10-07. Gerçek GUI/spawn/yayın/undo/redo/reopen testi tests/test_relational_gui.py::test_all_transform_forms_publish_undo_redo_reopen; tam100k ölçüm scripts/measure_phase11.py. Yardım src/veri_ufku/learning/content/tr.json. Genel test sayısı yöntem kabulünün yerine kullanılmaz.

| Alt kimlik | Bağımsız hesap / dayanıklılık | GUI / yardım |
|---|---|---|
| F11-COMPUTED | test_formula_text_date_and_security; test_formula_zero_null_exactness_rename_and_failed_result | Formül/kolon ekle/tür; transform-computed |
| F11-SPLIT | a-b-c → a,b-c; d → d,null; null → null,null | İki alan/literal ayraç; transform-text-split |
| F11-COMBINE |100k A-B + x/y → A-B-x/A-B-y; native source order | Seçili metin alanları/null politikası; transform-text-combine |
| F11-DATE-PARTS | ay [1,null,3]; timezone ayında2 ve ns koruma | Tarih parçası/timezone; transform-date-parts |
| F11-AGGREGATE | Decimal2+10=12/min2; tümü null grup; bütün3 üyelik; DuckDB SQL sum/date min | Grup/çoklu ölçüm/hedef tür; transform-aggregate |
| F11-PIVOT | Duplicate cell default reject; sum12;100k x/y bağımsız çift/tek sayılar | Grup/header/agregasyon; transform-pivot |
| F11-UNPIVOT | Decimal [2,10,null] uzun değerler;100k×2 →200k kayıt/kaynak alanı | Kimlik/değer alanları; transform-unpivot |
| F11-APPEND | [(1,x,null),(1,x,null),(2,null,y)] strict mapping; fault/reopen/undo; DuckDB union all | Eşleme önerisi/düzeltme/açık onay; transform-append |
| F11-JOIN | Dört tür ve null false/true;2×2=4;100k→200k; gerçek üyelik, iki SIGKILL ve budget199 reddi | Üç adım/anahtar/tür/null/ad eki/tam etki; transform-join |

<a id="e11-join-append"></a>
## F11-S003 — görünür eşleme ve büyüme

Join tam key frekanslarını çarpar; pair/unmatched/cardinality/ordering/row limit kayıtlıdır. tests/test_relational.py dört join türünde bağımsız beklenen4/6/6/8, null_equal full7 ve kararlı çift sırasını karşılaştırır. Birçok sol/sağ aynı içerikli satır ayrı UUID'dir. Right join sağ-sonra-sol sırası. Append explicit tüm alan eşlemesi/padding ve type mismatch reddi; GUI öneri onaysız uygulanamaz. Pivot tekrar hücre default reject; açık agregasyon sonucu ve çözülmüş başlık/ColumnId tarifte sabit. Başsız sihirbaz sinyalleri ve gerçek spawn yolu çalıştırılır; bu manuel kullanıcı etkileşimi kanıtı değildir.

<a id="e11-formats"></a>
## F11-S004 — gerçek adaptör fixture'ları

Yollar importers/ods.py/sqlite_source.py/parquet.py/registry.py/native.py/structured.py/worker.py; ui/imports.py/ImportPanel.qml/StructuredOptions.qml. tests/test_phase11_formats.py gerçek ODF ZIP/XML, ordinary SQLite SQL dosyası, Polars Feather V2/IPC file ve stream üretir; preview/import/proje/taşınabilir copy/reopen/kaynak bytes eşitliği. Arrow Decimal/ns UTC/List tür şeması tam korunur. SQLite quote içeren ve WITHOUT ROWID tablo gerçek fixture ile okunur; table injection reddi, DML/load_extension denemeleri engellenir, Aktif WAL/journal kaynak kopyalanmadan önce, kopyalama parçalarında ve hash doğrulaması sonunda reddedilir. Kaynak dosyasını proje/çıktı hedefi seçme ve readonly ikinci proje yazma denemeleri engellenir. GUI ayrıca iki tablodan ikinciyi açık seçer ve dört formatı worker/import/reopen üzerinden denetler. Bağımlılık/sınırlar ADR-014'te; SQLite asıl dosyası hiç yazma bağlantısıyla açılmaz.

<a id="e11-help"></a>
## F11-S005 — çevrimdışı yardım

İçerik10/toplam61 makale: dokuz dönüşüm ve dört adaptörün ortak sınır yardımı. Günlük müşteri/sipariş inner/left/right/full örneği, n:n, grouping/pivot/long-wide/güvenli formül, null/zero/type/timezone/kayıp. Yöntem bağları ve13 capability; yeni try_action yok. check_learning43 statik UI bağı ve capability bağlarını doğrular. Yeni ders/form zorunlu değildir.

<a id="e11-lineage-backends"></a>
## F11-S006/S007 — kaynak ilişkileri ve bağımsız motorlar

Join gerçek var olan sol/sağ kayıtlar için üyelik kenarları; aggregate/pivot bütün üyeleri saklar. Tek-kaynak olmayan fiziksel SourceRecordId null; GUI bunu açık söyler. Append/unpivot tek gerçek kaynağı koruyabilir, yeni RowId ve input alan ilişkisi ayrı kayıtlıdır. Staging yayını kenarları gerçek giriş/çıktı RowId/source kimliklerine karşı doğrular. İkinci sürüm aktifliği ve hash yayında yeniden kontrol edilir; eski sonuçlar retarget edilmez.

tests/test_relational_backends.py: DuckDB1.5.6 SQL ile Polars2 dört join türü×iki null politikası, tie sırası, exact Decimal, Date; group sum/date min ve append union all. DuckDB autoinstall/autoload extensions kapalı, parameterized read_parquet yolları; Decimal→double Python köprüsü kullanılmaz. Üretim DuckDB UI desteği veya test edilmemiş yöntemler için eşdeğerlik iddiası yoktur.

<a id="e11-package"></a>
<a id="e11-measure"></a>
## Tam veri/render ve kurulu paket

scripts/measure_phase11.py100.000 kayıt: dokuz full preview/apply/undo/redo/reopen; aggregate50k grup ve beklenen4i+1, pivot çift/tek kaynak sayıları, unpivot/append/join200k. Join400k gerçek üyelik kenarı ve hiçbir sahte singular source. Kaynak hash/iptal, CPU süreç RSS/UI tick ölçümü N=1 sıcak geliştirici ortam; minimum donanım garantisi değildir. İlk200 tablolar örnektir. Resmî Faz02 ortak tasarım dili korunur; yeni resmî görsel incelemesi iddiası yoktur. Geniş/%100 ve dar/koyu/%200 render gerçek PNG; yatay/dikey kaydırma gereken dar boyut ayrıca sınırdır. Yeni masaüstü/native picker/ekran okuyucu kabulü açık. Sekiz son PNG doğrudan görsel olarak incelendi; dar/%200 görünüm kaydırma gerektirir.

[Kaynak ölçümü](phase11-headless.json), [kurulu wheel ölçümü](phase11-wheel.json), [ortam ve hashler](phase11-environment.json), [kaynak dosya hashleri](phase11-source.sha256). Son kaynak koşusunda join önizlemesi2208.08ms, örneklenmiş ebeveyn+worker RSS1333.25MiB ve max UI tick45.06ms. Son kurulu wheel koşusunda join önizlemesi2173.32ms, RSS1328.71MiB ve max UI tick47.93ms. RSS ortak sayfaları iki kez sayabilir; tek sıcak koşu performans garantisi değildir. Dört gerçek format fixture'ında tür/değer eşitliği, kaynak korunması ve yeniden açılış doğrulandı. Kurulu paket aynı locked runtime ve sistem Qt kitaplıklarını kullanır; bağımsız temiz Linux/offline dağıtım kabulü değildir.

Bu oturumdaki offline build çıktısı `/tmp/veri-ufku-phase11-final-dist`, offline/no-deps kurulum `/tmp/veri-ufku-phase11-final-installed`. `uv --cache-dir /tmp/veri-ufku-uv build --offline --no-build-isolation --out-dir /tmp/veri-ufku-phase11-final-dist` wheel ve sdist üretti. `uv --cache-dir /tmp/veri-ufku-uv pip install --offline --no-deps --target /tmp/veri-ufku-phase11-final-installed /tmp/veri-ufku-phase11-final-dist/veri_ufku-0.1.0-py3-none-any.whl` başarılı. `/tmp` cwd/PYTHONPATH ve `--package-root` modül konumu doğrulamasıyla giriş noktası ve100k ölçümü bu kurulu wheel'den geçti; paket/hash/config bilgisi ENV-11 içindedir.

<a id="e11-checks"></a>
## Son kapılar

[Gerçek komut kayıtları](phase11-checks.txt): locked dev sync, sistem ve locked check_docs, check_artifacts, check_learning, Ruff check/format, 297 pytest, 9 locked unittest, kaynak ve kurulu giriş noktası offscreen/software smoke, git diff --check geçti. Diskteki tam suite kaydı297/49.04s; yeni kodun kaynak hashleri kayıtla eşleşiyor. Paket offline build/install ve /tmp çalışma dizininden gerçek kurulu modülle100k ölçüm ve giriş noktası smoke tamamlandı. Qt testleri izole XDG dizinleri kullanır.

[Doğrudan sistem Python unittest denemesi](phase11-system-unittest.txt) bağımlılıksız Python3.14 ortamında32 test/23 import hatasıyla başarısızdır; locked CPython3.13 ortamındaki9 belge unittest ve297 pytest başarısından ayrı tutulur. İlk izolasyonsuz smoke exit2 sonrası izinli /tmp XDG dizinleriyle tekrar GUI_SMOKE PASS alınmıştır; başarısız deneme başarı sayılmaz.

Yeni fiziksel tür korumasının Faz10 convert hedefiyle uyumu düzeltildi. Ardışık dönüşüm→temizlik→kopya→rol testi eski recipe girdilerinin yeni tarife taşınmadığını doğrular. Yalnız Faz11 tamamlandı; Faz12 başlatılmadı. Manuel kullanıcı masaüstü ve uzak CI henüz doğrulanmadı.
