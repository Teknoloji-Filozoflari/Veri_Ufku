# Faz07 — tablo, profil ve semantik metadata kanıtı

Tarih2026-10-06, ortam ENV-07 Linux geliştirici Btrfs, CPython3.13.15/PySide6Qt6.11.2/Polars2.0.0, offscreen/software. Kapsam yalnız Faz07; olgunluk deneysel. Kaynak prompt hash [phase07-source.sha256](phase07-source.sha256); kaynak CSV/Parquet değiştirilmez. Yerel kontrollerin tamamı gerçek çalıştırma; masaüstü/minimum donanım/remote CI ayrıca doğrulanmadı.

<a id="e07-table"></a>
## F07-TABLE — F07-S001/S004/S007

Yollar: src/veri_ufku/analytics/dataset.py, ui/dataset.py, ui/qml/DatasetPanel.qml, tests/test_dataset.py, test_dataset_gui.py. Gerçek QML/spawn sayfa, global azalan sıralama, AND filtre, kapsam, RowId/SourceRecordId, salt okunur model ve iptal/eski binding testi. 603 kayıt iki200 sayfa; sıralı ve filtreli kimliklerin snapshot ile birebir bağı kontrol edildi. Sütun arama/gizleme metadata üzerinden; görünüm analiz dataset'ini değiştirmez. Profil target açık dataset/view; gizli filtre testi full scope filtre listesinin boş olduğunu doğrular. Tablo görüntüsü ve tür listesi [1366](phase07-1366-light-table.png), [720](phase07-720-dark-table.png).

<a id="e07-profile"></a>
## F07-PROFILE — F07-S002/S006/S007

Bağımsız 1,2,3,4,null,NaN,+inf,-inf referansı: finite n4, null1, NaN1, ±inf1/1, unique7, null oranı1/8; mean/median2.5, q25=1.75, ddof1 std sqrt(5/3), ddof0 sqrt(1.25). Empty/singleton tanımsız std, Decimal38 ve UInt64 büyük değer hassasiyeti, ns/UTC tarih aralığı, ilk10 örnek kapsamı, filtreli10/tam300 ayrımı, unique300/top20/diğer280 kontrol edildi. Profil yöntemi, dışlamalar ve filtreler provenance/result içinde kayıtlı. [Profil görüntüsü](phase07-1366-light-profile.png). Nested unique/frekans açık destek sınırı; örnek firstN population tahmini değildir.

<a id="e07-roles"></a>
## F07-ROLES — F07-S003/S006/S007

Yollar: analytics/contracts.py, storage/project_model.py/project_store.py, ui/projects.py/dataset.py; referans ve gerçek Qt save/close/reopen testleri. 00123 korunur. Rol değişiminde yeni metadata dv, eski aynı Parquet/import metadata/ColumnId/RowId kalır. Kimlik rolünde ortalama/std/quantile bulgusu üretilmez; eski profil güncel değildir. unit/ordinal_order/analysis_unit alanları tipli; invalid ordinal/parent reddedilir. Manifest4, schema3 fixture açık migration4; eski manifest/SQLite read-only açılışında değişmez. [Sütun paneli](phase07-1366-light-column.png).

<a id="e07-help"></a>
## F07-HELP — F07-S005

Katalog content6,31 makale; tür/rol, unique, std/ddof, yüzdelik/linear ve profil kapsamı rehberleri. Beş yeni makale ve dataset.view/profile/roles capability bağları; F1 ve düğmeler. Yardım okuma işlemi dataset/config/result üretmez. check_learning gerçek statik bağ ve katalog doğrulamasıdır.

<a id="e07-memory"></a>
## F07-MEMORY — F07-S006

Yol scripts/measure_phase07.py. Gerçek 100.000 kayıt Parquet import→16 ayrı spawn sayfa→full profile→rol/unit kaydet→kapat/aç→sample profil. [Ham ölçüm](phase07-headless.json):200 kayıt üst sınırı; ilk3 sayfa sonrası parent RSS aralığı 1.94MiB; örneklenmiş parent+worker peak 482.73MiB; full profil 872.7ms ve max UI tick aralığı 45.1ms.16 sayfa 177.4–189.4ms. UI heap kaçağı iddiası yerine sınırlı model ve gerçek RSS plateau deneyi. N=1 sıcak geliştirici ortamı; minimum cihaz, soğuk cache veya tüm dosya boyutları performans kabulü değildir. SQLite unique spool private ve iş bitiminde temiz; proje artifact'ı yerinde. Kaynak hash eşit. Polars global sort/resource limit kapsamında kontrollü hata verebilir.

<a id="e07-package"></a>
## F07-PACKAGE — erken kurulu Linux wheel

Offline/no-build-isolation wheel/sdist /tmp/veri-ufku-phase07-final-dist, offline/no-deps /tmp/veri-ufku-phase07-final-installed. Ayrı /tmp cwd ve PYTHONPATH target; module __file__ target doğrulanır. scripts/measure_phase07.py --package-root ile gerçek kurulu QML/spawn büyük import/sayfa/full profil/metadata/reopen/sample akışı. Locked runtime ve mevcut sistem Qt kitaplıkları kullanılır; bağımsız temiz Linux kurulum kabulü değildir. Kaydedilmiş çıktı [phase07-wheel.json](phase07-wheel.json). İlk paket testi son doğrulama öncesi çalıştırıldı.

<a id="e07-checks"></a>
## F07-CHECKS — regresyon kapıları

[Komut/çıktı/exit kanıtı](phase07-checks.txt) gerçek son koşuyu içerir. **206 pytest passed,9 unittest OK**; locked dev sync, sistem/locked check_docs, check_artifacts, check_learning (31 makale/36 UI bağı), Ruff check/format (68 dosya), izole XDG kurulu giriş noktası GUI_SMOKE PASS ve git diff --check geçti. Kurulu final wheel büyük tablo/profil yanında JSON/JSONL/XLSX/Parquet ve CSV/TSV eski worker smoke regresyonları da geçti. İzole edilmemiş XDG ile sandbox giriş smoke exit2 verdi; o koşu kabul sayılmadı, geçici config/state/cache ile tekrar exit0 alındı. Şema4 ve yeni14 kavram için eski beklenen değerler açıkça güncellendi; Phase04 crash/lock, Phase05/06 import kaynak/karantina/iptal regresyonları korunur. Başarısız ara kontroller kabul değildir. Native yeni masaüstü ve remote CI çalıştırılmadı.

Faz02 resmî Orange/jamovi/KNIME/JASP/LabPlot cache görselleri bu oturumda gerçekten yeniden incelendi; [kaynak kayıtları](phase02-references.json). Dataset listesi, açık kapsam, sütun bilgisi ve okunur ayrım ilkeleri uygulandı; bu uygulamaları çalıştırma/uzman inceleme iddiası yoktur. Başsız küçük/büyük, açık/koyu tablo/sütun/profil görüntüleri incelendi.

<a id="e07-user-table"></a>
## F07-USER-TABLE — kullanıcı masaüstü bildirimi

2026-10-06, ENV-USER-07. Kullanıcı: “tamam verideki tabloları açtı yenielrdik”. Veri tablosunun açılması ve yenilenmesi kullanıcı tarafından başarılı bildirildi. Yol: src/veri_ufku/ui/qml/DatasetPanel.qml; src/veri_ufku/ui/dataset.py. Bildirimde dosya boyutu, işletim sistemi/ekran ayrıntısı belirtilmedi. Filtre/sıralama, profil değerleri ve rol kaydet/yeniden aç manuel kontrolleri ayrıca bildirilmedi; bu kayıt yalnız açma/yenileme kapsamındadır.
