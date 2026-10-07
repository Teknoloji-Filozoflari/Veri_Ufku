# Faz10 — temizlik araçları kanıtı

2026-10-07; ENV-10: yerel CachyOS Linux7.2.9 x86_64/glibc2.44, Ryzen7 8845HS, 32GB, Btrfs ve /tmp tmpfs; CPython3.13.15/PySide6Qt6.11.2/Polars2.0.0 kilitli ortam, offscreen/software. Yalnız Faz10; olgunluk deneysel. [Politika](../adr/013-cleaning-phase10.md). Başsız/paket kanıtı yeni kullanıcı masaüstü, minimum donanım veya remote CI değildir.

<a id="e10-engine"></a>
## F10-S001 — işlem motoru ve atomik yayın

Yollar src/veri_ufku/operations/cleaning_contracts.py, cleaning.py, contracts.py, engine.py; storage/project_model.py/project_store.py. Dokuz tipli temizlik tarifi aynı full hesap/önizleme çıktısını yayımlar. Şema6 migration, destination chain/copy ve immutable köken. tests/test_cleaning.py: copy+dedup relation yayımlanırken dört pre-ACTIVE disk fault noktası (lineage_copy_chunk/artifact_promoted/metadata_committed/pointer_fsynced) sonrası state/reopen eski tam veri ve temiz staging doğrulandı. İki gerçek copy+dedup SIGKILL: lineage_copy_chunk öncesi eski state; pointer_replaced sonrası iki tam dataset ve3 satır köken. Ortak Phase09 beş SIGKILL testi regresyonda korunur. Hata/iptal eski veriyi bırakır.

<a id="e10-methods"></a>
## F10-S002 — yöntem başına bağımsız sonuçlar

Yol tests/test_cleaning.py. Eksik satır null vs null+NaN ayrı üyelik; tümü eksik sütun çıkarma ve son kolon reddi. [1,2,6,null] sabit4 → [1,2,6,4], mean3 → [1,2,6,3], median2 → [1,2,6,2]; mode eşit aday seçimi. Tamamen eksik Int64 sabit8 ile doldu, öğrenilen yöntemler reddedildi. Fiziksel türü Null olan boş kolon açık Int64 dönüşümünden sonra doldu; önceki tür/satırlar undo ile geri geldi. Metin uçları ve exact kategori eşlemesi beklenen dizilerle karşılaştırıldı. Sıra/group açık ileri/geri doldurma, iki grubun karışmaması, interleaved4100 kayıtla batch sınırı ve ns farklı grup kimlikleri; dedup ilk/son survivor RowId ve bütün üyelerin Parquet kökeni kontrol edildi. Decimal/date/Datetime ve IQR sonuçları elle belirlenen referanslarla doğrulandı. Her yöntem apply/undo/redo veri eşitliği test edilir; kaynak hash değişmez.


Alt kabul eşlemesi: bütün satırlar ENV-10/2026-10-07. Hesap yolları tests/test_cleaning.py; GUI tests/test_cleaning_gui.py, ortak save/undo/redo/reopen ve dört disk fault/iki SIGKILL kontrolleri; yardım src/veri_ufku/learning/content/tr.json. Bunlar ayrı yöntem kontrolleridir, genel test sayısı tek başına kabul değildir.

| Kimlik | Bağımsız hesap testi / referans | GUI seçimi / yardım |
|---|---|---|
| F10-MISSING-ROWS | test_missing_rows_columns_and_null_nan_are_explicit: null ile NaN ayrı üyelik | Eksik satır / clean-missing-rows |
| F10-MISSING-COLUMNS | aynı test: yalnız tümü eksik alan; son sütun reddi | Eksik sütun / clean-missing-columns |
| F10-FILL-CONSTANT | test_fill_hand_values_counts_and_undo[constant]: sabit4 | Sabit / clean-fill-constant |
| F10-FILL-MEAN | aynı test[mean]: (1+2+6)/3=3 | Ortalama / clean-fill-mean |
| F10-FILL-MEDIAN | aynı test[median]: sıralı orta2 | Medyan / clean-fill-median |
| F10-FILL-MODE | test_all_missing_fractional_fill_mode_ties_and_zero_variance: eşit mod açık y | Mod eşit aday3 / clean-fill-mode |
| F10-DEDUP | test_dedup_order_equality_and_all_member_lineage ve test_full_column_dedup_keeps_distinct_events_and_stable_ties | Seçili/tüm anahtar / clean-dedup |
| F10-TRIM | test_text_trim_safe_exact_mapping_and_copy_dataset: Ankara/İzmir uç boşluğu,2 hücre | Kırp / clean-trim |
| F10-MAP | aynı test: tam kategori eşlemesi | Eşleme çiftini ekle / clean-map-categories |
| F10-CONVERT | test_decimal_date_parse_dst_policies_and_new_null_reporting ve native_timezone/ns testi | Tarih reject/null ve RowId / clean-convert |
| F10-FORWARD | test_ordered_fill_never_crosses_groups_even_interleaved[forward],4100 batch ve ns grup kimliği | İleri/açık grup / clean-ordered-fill-forward |
| F10-BACKWARD | aynı test[backward]: iki değişim/iki boş kalan | Geri/açık grup / clean-ordered-fill-backward |
| F10-IQR-MARK | test_iqr_mark_is_default_zero_iqr_and_explicit_filter: yalnız100 aday,5 satır korunur | Varsayılan işaretle / clean-outlier |
| F10-IQR-FILTER | aynı test: açık filter100 kaydını çıkarır | Açık filtrele / clean-outlier |

<a id="e10-policies"></a>
## F10-S003/S008 — hassasiyet, null ve zaman politikaları

tests/test_cleaning.py: kesirli Int64 öğrenilen değer reddi, 2^53 üstü Float64 kaybı, 0.1 binary kaybı, Decimal ölçek kaybı, bozuk tarih; eşit modda dur/gerçek adayı seç; sabit kolon ve IQR=0 seyrek aday. Native ns dedup iki farklı anı ayrı tutar; ns→us kaybı reddedilir, metne ns tam aktarılır. Native timezone dönüşümü aynı UTC anını korur. America/New_York DST çift saatte açık latest, var olmayan saatte null hata; UTC bekleneni bağımsız datetime ile karşılaştırılır. NaN/null ayrı gruplar, signed-zero eşitliği ve kullanıcıya gösterilen/saklanan equality/order/keep politikası. Yeni null, hata, değiştirilmiş hücre/sütun/satır sayıları kontrol edildi. Değişmeyen trim ve eksik satır işlemi seçilen kolon sayısını değişmiş kolon diye sunmaz.

<a id="e10-copy-outlier"></a>
## F10-S004 — açık kopya ve işaretleme

tests/test_cleaning.py ve test_cleaning_gui.py: ayrı DatasetId'li kopya, özgün head korunur, undo kopya başlangıcına döner; reopen eşitlik. IQR varsayılan Boolean işaret sütunu ve aynı satırlar; açık filter yalnız elle beklenen adayı çıkarır. Kaynak silinmez, otomatik işlem yok. QML işlem hedefinin iki açıklamasını ve IQR'ın aday niteliğini gösterir.

<a id="e10-leakage"></a>
## F10-S005 — gelecekte ML sızıntı incelemesi

contracts learned_scope, publish_operation leakage_review_required/diagnostics; ui/operations.py leakageHistory, OperationsPanel.qml geçmiş uyarısı. Genel mean/median/mode doldurma dataset kapsamıdır; sabit doldurma none. Veri bağımlı geçmiş copy/undo/reopen ile saklanır ve GUI testinde görünür. Parametreler/giriş sürümü/öğrenilen değerler korunur; gelecekte fold-içi eğitim dönüşümü için ayrı fit sözleşmesi gerekir. Henüz ML UI/fit uygulanmış veya sızıntısız eğitim test edilmiş sayılmaz.

<a id="e10-help"></a>
## F10-S006 — yöntem yardımları

src/veri_ufku/learning/content/tr.json içerik9/toplam51 makale, sözlük18. On üç yeni makale: eksik satır/sütun, sabit/mean/median/mode, dedup/trim/eşleme/dönüşüm, ileri/geri doldurma ve IQR. Her birinde küçük önce/sonra örneği, bilgi kaybı ve sakıncalı kullanım. Capability ve dinamik QML yöntem bağları; yeni try_action yok. check_learning51 makale/42 statik UI bağı ve tüm capability bağlarını doğrular; öğrenme testleri çevrimdışı katalog/PlainText/F1/regresyonu korur.

<a id="e10-gui"></a>
## F10-S007 — gerçek QML ve iptal

tests/test_cleaning_gui.py gerçek form seçimleri, eşleme çifti düğmesi, grup seçimi property aktarımı, önizle/uygula düğmeleri ve spawn hesabıyla dokuz yöntemi ve ayrıca mean/median/mode, full-key dedup, backward ve açık IQR filter seçimlerini çalıştırdı. Dinamik fill yardım bağları seçili alt yönteme eşit doğrulandı. Sıra modeli değişince seçim temizlenir; gizlice ilk kolona bağlanmaz. Uygula/undo/redo/reopen snapshot eşitliği; bozuk tarih default reject ve açık null yolunda bir parse hatası/yeni null/ilgili RowId; gerçek süreç iptali state'i korudu. Copy median, learned geçmiş ve readonly tablonun önceki GUI kabulü regresyonda geçti. Bu otomasyon gerçek kullanıcı elle etkileşimi kabulü değildir.

<a id="e10-measure"></a>
## Tam veri ve render

scripts/measure_phase10.py100.000 kayıt N=1: dokuz yöntemde tam preview/apply/undo/redo/reopen. Beklenen 10.000 doldurma, 10.000 eksik satır çıkarma, bir eksik sütun, 99.998 dedup çıkarma, 10.000 tarih parse hatası/yeni null ve 9.999 grup içi ileri doldurma bağımsız fixture kurallarıyla kontrol edildi; ilk eksik grup kaydı boş kalır. Kaynak SHA256, iptal ve eşitlik doğrulandı. [Ham kayıt](phase10-headless.json). Geniş açık/%100, dar koyu/%200 gerçek render PNG'leri view_image ile incelendi. Dar/%200 ekranda dikey/yatay kaydırma gerekir; minimum donanım/ekran okuyucu kabulü değildir. Önce/sonra ve geçmiş ayrıntıları varsayılan kapalı, undo/redo görünür. Faz02'nin onaylı ortak tasarım tokenları kullanılır; yeni bağımsız resmî referans görsel incelemesi iddiası yok.

<a id="e10-package"></a>
## Kurulu paket

Offline/no-build-isolation wheel+sdist `/tmp/veri-ufku-phase10-dist`; offline/no-deps kurulum `/tmp/veri-ufku-phase10-installed`. Ayrı `/tmp` cwd/PYTHONPATH ve package __file__ doğrulamasıyla scripts/measure_phase10.py aynı100.000 kayıt/dokuz yöntem akışını geçti. [Ham paket ölçümü](phase10-wheel.json), [ortam/lock/fixture/wheel hashleri](phase10-environment.json). N=1 sıcak geliştirici ortam: dedup önizleme 2238.69ms; örneklenmiş parent+worker RSS 769.61MiB, max UI tick 49.44ms. Paylaşılan sayfalar çift sayılabilir; minimum donanım/bağımsız temiz Linux paketi kabulü değildir. Kurulu paket aynı locked runtime ve sistem Qt kullanır.

<a id="e10-checks"></a>
## Son kapılar ve sınırlar

Son [komut/exit çıktıları](phase10-checks.txt): offline locked dev sync, sistem/locked check_docs, check_artifacts, check_learning51 makale/42 statik UI bağı, Ruff check/format85 dosya,261 pytest/41.29s,9 locked unittest, kurulu offscreen/software giriş noktası GUI_SMOKE PASS ve git diff --check geçti. Gerçek kaynak ve paket100.000 kayıt ölçümleri son kodla tekrar üretildi. İlk yerel tam regresyon255 test geçti; native timezone/ns, full-key dedup, copy SIGKILL, ns grup ve türsüz Null testleri eklendi. Sonradan değişen etki etiketi/dinamik yardım bağı üç GUI regresyonuyla ayrıca kontrol edildi. Katalog bağlarında underscore geçersizliği ilk hedefli denemede bulundu, yardım/capability kimlikleri izinli hyphen biçimine düzeltildi; son check_learning geçti. Eksik satır/değişmeyen trim etki sütun sayıları düzeltildi. Kabul son başarılı kontrol çıktısına bağlıdır.

Kullanıcı manuel denemeleri daha sonraki toplu kabulde yapmak istedi; F10-USER-DESKTOP ve F10-CI-REMOTE doğrulanmadı. Gelecek fazları başlatma yetkisi verilmedi. D-01 elle düzenleme seçilmedi; salt okunur davranış sürer. Tam yeniden kullanılabilir fold-içi ML, join/explode/aggregate ve kalıcı sort bu fazda uygulanmadı.

Doğrudan sistem CPython3.14 `python3 -m unittest discover -s tests -v` [denemesi](phase10-system-unittest.txt)19 import hatasıyla başarısız: Polars/PySide6/veri_ufku kilitli .venv dışındaki sistem ortamına kurulmadı. Bu başarısız deneme ayrı tutulur; kilitli CPython3.13.15 unittest9 test geçti. [Doğrulanan kaynak hashleri](phase10-source.sha256).
