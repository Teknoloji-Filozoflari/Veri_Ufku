# Faz09 — sürümlü işlem motoru kanıtı

2026-10-07 UTC/Europe/Istanbul; ENV-09: yerel Linux7.2.9 CachyOS x86_64 glibc2.44, CPython3.13.15/PySide6Qt6.11.2/Polars2.0.0, Btrfs/tmpfs, offscreen/software. Yalnız Faz09, deneysel. Başsız/paket kanıtı gerçek masaüstü, minimum donanım veya yeni remote CI kabulü değildir. Kaynak promptu korunur. Karar ADR-012.

<a id="e09-contract"></a>
## F09-S001/S002 — tipli ortak hesap yolu

Yollar operations/contracts.py/engine.py/worker.py, storage/project_model.py. OperationSpec/method1, input dv/ColumnId/output schema, tipli literal, learned_scope, applicability/validation/impact/status/provenance. Unknown kind/version, kolon/ad/tür/çıktı şeması, eski giriş ve bozuk cursor kontrollü reddedilir. Preview full Parquet çıktısı apply tarafından hash doğrulanarak yayımlanır; başka hesap yolu yok. First200 tablo full etki sayımı değildir. tests/test_operations.py bağımsız değerler ve tests/test_operations_gui.py gerçek worker/QML ile doğrular.

<a id="e09-history"></a>
## F09-S003/S006 — değişmez veri, geçmiş ve sonuç bağı

Yollar operations/contracts.py, storage/project_store.py, ui/operations.py/projects.py/dataset.py. Rename [1,2,2,3,null] aynen korundu; filtre [2,2] yalnız orijinal ikinci/üçüncü kaydın ayrı RowId/SourceRecordId'lerini tuttu; drop aynı satırları korudu. Undo/redo tablo eşitliği; eski dalın tutulması/yeni dalda redo temizlenmesi; save/close/reopen ve undo sonrası yeniden açılışta redo aynı kimliklerle doğrulandı. Sonuç dataset_version_ids asla değişmedi; eski profil/sonuç current=false görünür, doğru önceki sürüme dönünce current=true. UI adımın öncesine dönerek parametreyi değiştirmeye izin verir; alt adımları otomatik oynatmaz. Henüz grafik/model yok; gelecekte ortak results sürüm bağı sözleşmesi gerekir, mevcut model hesabı test edilmiş sayılmaz.

<a id="e09-operations"></a>
## F09-S004 — gerçek ilk işlemler ve hata/iptal

OperationsPanel/OperationTable.qml, ui/operations.py. Gerçek QML rename/filter/drop önizle→uygula, önce/sonra şema ve bounded tablo, full değişen/çıkarılan satır ve sütun sayımları. Kaynak hash/snapshot değişmedi. Hatalı ad/son kolon drop/uygulanmayan future kind, canceled compute ve tampered çıktı state değiştirmedi. Testte beş yayım noktası OSError; ayrıca beş gerçek SIGKILL (copy/artifact/metadata/pointer fsync/pointer replace) sonrası reopen eski tam sürümü veya yayımlanmış yeni tam sürümü kabul etti; yarım dataset yok, staging temizlendi. Atomik yayına geçtikten sonra iptal kapalıdır; eski/başarılı committen biri korunur.

<a id="e09-help"></a>
## F09-S005 — yardım

İçerik8/toplam38 makale: önizleme, işlem geçmişi/geri alma, kaynak ile çalışma verisi farkı. prepare ve operation.rename/drop/filter/F1 bağları, çevrimdışı içerik ve capability kapısı; try_action eklenmedi. Katalog sözlük18 korunur.

<a id="e09-lineage"></a>
## F09-S007 — kimlik ve gelecek sözleşmeleri

Filter/rename/drop/roles identity projection; sort görünümü mevcut stable tie sözleşmesini kullanır. Sıralanmış/filtrelenmiş Qt tablosunun RowId üyeliği kalıcı filtre sonucuna eşit, aynı içerikli iki kayıt ayrı kaldı; redo/reopen fiziksel snapshot eşitliği source kimliklerini de kapsar. RowLineageSpec future sort/join/explode/aggregate/dedup policy, input arity, method, compact relation format doğrulayıcısı test edildi. Bu türlerde executable/UI yok; içerik hash'i veya görüntü sırası kimlik yerine kabul edilmez. Join/explode occurrence, aggregate lazy immutable membership ve dedup survivor/group ayrı sözleşme. PRODUCT D-01 elle düzenleme seçilmedi: mevcut Qt model salt okunur; hücre/satır/panodan yazma erken eklenmedi.

<a id="e09-measure"></a>
## Büyük veri ve gerçek başsız ekran

scripts/measure_phase09.py100.000 kayıt import/full preview/apply/undo/redo/reopen; 99.990 çıkarılan kayıt ve kalan son10 RowId elle tanımlı beklenenle doğrulanır. Kaynak SHA256 korunur. [Ham ölçüm](phase09-headless.json), geniş açık ve dar koyu/%200 ekranlar; görüntüler view_image ile incelendi. Sıcak geliştirici ortam N=1; peak RSS parent+worker örneklemesi ortak sayfaları çift sayabilir, fiziksel peak garantisi değildir. Minimum donanım veya büyük future join/aggregate lineage benchmarkı değildir.

<a id="e09-checks"></a>
## Regresyon kapıları

Son [komut/exit çıktıları](phase09-checks.txt): locked dev sync, sistem/locked check_docs, check_artifacts, check_learning38 makale/42 UI bağı, Ruff check/format80 dosya,228 pytest (34.94s),9 unittest, izole offscreen/software giriş noktası GUI_SMOKE PASS ve git diff --check geçti. İlk hedefli kontrollerde yardım context/sözlük ve proje şema migration fixture beklentisi, ayrıca lineage descriptor tuple/list roundtrip farkı bulundu; düzeltildi. Kabul yalnız son başarılı kontrollerden çıkarılır. Şema0–3 eski fixture açılış/kopya migration test beklentileri yeni şema5'e taşındı; fixture byte'ları korunur. Hazırla kullanılabilirlik testi gerçek ekrana güncellendi. [İlk başarısız regresyon](phase09-initial-checks.txt) tarihsel kayıttır; kabul değildir.

<a id="e09-package"></a>
## Kurulu Linux wheel

Offline/no-build-isolation wheel+sdist `/tmp/veri-ufku-phase09-dist`, offline/no-deps kurulum `/tmp/veri-ufku-phase09-installed`; ayrı `/tmp` cwd/PYTHONPATH hedefinde `__file__` doğrulandı. Paket QML/katalog/operations worker'ı `scripts/measure_phase09.py` ile aynı100.000 kayıt akışını geçti. [Gerçek paket ölçümü](phase09-wheel.json); preview273.94ms/apply270.83ms, örneklenmiş parent+worker577.32MiB, max UI tick42.71ms. Locked runtime ve mevcut sistem Qt kullanır; bağımsız temiz Linux dağıtımı kabulü değildir.

[Ortam/CPU/RAM/FS/lock/wheel hashleri](phase09-environment.json). Geniş açık ve dar koyu/%200 önce/sonra ekranları gerçekten render edilip view_image ile görüldü; dar ekranda dikey/yatay kaydırma gerekir. Başsız görünüm gerçek masaüstü/ekran okuyucu veya kullanılabilirlik kabulü değildir. F09-USER-DESKTOP/F09-CI-REMOTE isteğe bağlı doğrulanmadı; Faz10 başlamadı.

Sistem CPython3.14 ile doğrudan `python3 -m unittest discover -s tests -v` [denemesi](phase09-system-unittest.txt)17 import hatasıyla başarısız oldu: Polars/PySide6/veri_ufku kilitli .venv dışındaki sistem ortamında kurulu değil. Sistem ortamına bağımlılık yazılmadı; kabul komutu CPython3.13.15 kilitli `uv run --frozen python -m unittest ...` ile9 test geçti. Bu ayrım başarısız sistem denemesini başarıya dönüştürmez. [Doğrulanan dosya hashleri](phase09-source.sha256).
