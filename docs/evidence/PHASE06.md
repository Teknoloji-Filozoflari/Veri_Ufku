# Faz06 — yapılandırılmış dosya adaptörleri

2026-10-06; deneysel; yalnız Faz06. [Ana kayıt](../REQUIREMENTS_MATRIX.md), [ADR-009](../adr/009-structured-import-phase06.md).

<a id="e06-environment"></a>

ENV-06: ENV-05 ile aynı geliştirici Linux/CPython3.13.15, PySide6/Qt6.11.2, Polars2.0.0 locked runtime. Yeni dependency yok. Qt offscreen/software; yerel Btrfs proje alanı ve /tmp test dizinleri, izole XDG. Gerçek kullanıcı/native masaüstü, minimum donanım, yeni remote CI, ağ FS veya temiz Linux offline installer kabulü değildir. Ortam/hash/ölçümler phase06-headless.json ve phase06-source.sha256 içinde kaydedilir.

<a id="e06-json"></a>

F06-S001/S002/S004/S006: importers/contracts.py, registry.py, native.py, structured.py, worker.py; tests/test_structured_import.py ve fixtures/structured/nested.json, records.ndjson; ENV-06,2026-10-06. Kök/nested JSON Pointer seçimi, flatten/liste ayrı seçenekler, Cartesian2×3=6 + boş-listeli dış satır=7 beklenen değeri. Eksik optional1/açık null1 ayrı rapor; aynı id001 iki kaynak kaydı farklı kimlik. JSONL sırası değişmiş keys ve sonradan alan late doğru birleşti; bozuk3.satır locator line:3/raw/reason ile karantinada. Decimal12345678901234567890.1200 ve UInt64 üst sınır değeri JSON'da Decimal(20,0) kesin. Karışık sayı/string, list içi karışık ve39hane reddi; açık JSON metni kayıpsız seçim test edildi.

<a id="e06-excel"></a>

F06-S003/S006/S007: xlsx.py ve fixtures/structured/workbook.xlsx/workbook1904.xlsx, test_structured_import.py. Gerçek OOXML ZIP fixture dört sayfa; Satış/Diğer seçimi, header0 veA2:B2, keep3/skip2, Türkçe İkinci/id001, büyük Decimal, nullable naive2024-01-01,1904 aynı seri2028-01-02; sahte1900seri60 ve sub-us ret. Formula =1+1/=2+2 ve text1+1/2+2; cached2, eksik cache üçüncü satır durdurma/konumlu karantina. Birleşim default ret/anchor yalnız sol üst; boş özgün başlıklar saklandı. Makro/formül yürütme yok, kapsam [ADR](../adr/009-structured-import-phase06.md).

<a id="e06-parquet"></a>

F06-S003/S004/S006/S007: parquet.py/native.py, test_structured_import.py; yerel fixture gerçek Parquet olarak yazılır. Nullable Int16/Date, UInt64max, Decimal(24,4), List(Int8) nestedStruct, NaN/Inf ve Datetime(ns,Europe/Istanbul) kontrol edildi. Epoch1791234000000000001 nanosaniye tam kaldı; native çerçeve eşitliği yanında bağımsız scalar beklentiler var. Duration açık ret. .data uzantılı gerçek Parquet magic ile tanındı; kısa sahte Parquet ve JSON içerikli.xlsx uzantıdan bağımsız ele alındı.

<a id="e06-gui"></a>

F06-S001/S002/S003/S006: ui/imports.py, ImportPanel.qml, StructuredOptions.qml; test_import_gui.py::test_phase06_four_formats_real_worker_qml_controls_and_reopen. Gerçek QML path, flatten, liste ve Excel sheet seçimleri; gerçek spawn worker/atomik parent kayıt ve dört dataset kapat-aç kontrolü. CSV/TSV drop/FileDialog regresyonları korunur. Bu QML signal/headless testidir, native dosya seçicinin kullanıcı denemesi değildir.

<a id="e06-help"></a>

F06-S005: learning/content/tr.json sürüm5/toplam26 makale; JSON nesne/liste, JSONL, düzleştirme/liste açma, Excel sayfa/formül, Parquet/tür koruma. Dört native capability yardım bağlı; check_learning gerçek katalog/QML bağlarını kontrol eder. Yardım ve kaynaklar ağsız paketlidir.

<a id="e06-package"></a>

F06-S007 erken hedef Linux paket smoke gerçekten çalıştırıldı. Locked runtime ile offline/no-build-isolation wheel/sdist /tmp/veri-ufku-phase06-dist, wheel --offline --no-deps --target /tmp/veri-ufku-phase06-installed içine kuruldu. Ayrı /tmp cwd/PYTHONPATH target; package __file__ target içinde doğrulandı. scripts/smoke_structured_wheel.py kurulu QML/yardım, dört format FileDialog sinyali→spawn worker→native Parquet→atomik yayın→reopen çalıştırdı. INSTALLED_WHEEL_JSON/JSONL/XLSX/PARQUET_WORKER_IMPORT PASS ve PHASE06_INSTALLED_WHEEL_REOPEN PASS. Mevcut .venv locked runtime/system libraries kullanılır; bağımsız temiz sistem kurulumunu kanıtlamaz. İlk smoke, son kontrollerden önce başlatıldı; son artifact ayrıca yeniden doğrulanır.

<a id="e06-integrity"></a>

Değişen kaynak için önizleme ve import aynı deklarasyonu görünen özel snapshot kullanır; eski1/1 değerleri ve fingerprint, farklı SourceRecordId korunur. Snapshot mutasyonu ret; cancel yayın yapmaz. Native şema descriptor ve actual artifact eşitliği metadata'da doğrulanır. Şema3,0/1/2 açık migration geçmişiyle yönetilir. Daha önceki46 gerçek SIGKILL, tek yazıcı, readonly ve güvenli cleanup regresyonları korunur; ek native JSON kaydı import_copy_begin/artifact_written/metadata_committed/manifest_written/pointer_replaced/root_synced altı noktada gerçek SIGKILL (returncode=-SIGKILL) ile test edildi; eski veya tam yeni Decimal dataset açıldı. İlk200 JSONL kaydından sonraki karışık tür ve yeni alan tam importta reddedildi; type indeksleri sessiz yeniden bağlanmadı. Gerçek120000 kayıt JSONL import iptalinde kaynak/ACTIVE aynı, dataset yok. ZIP traversal/duplicate/symlink/DTD/entity/macro/boyut ret, 1900/1904, explicit IANA ve2^53 kayıp ret, schema2 byte-korumalı açılış/açık3 migrasyonu geçti. Şema0/1 migrasyon regresyonları güncel3 hedefiyle geçer; önceki Faz05 kaydı tarihsel2 kanıtıdır.

<a id="e06-checks"></a>

Son doğrulama: **188 pytest passed**, **9 unittest OK**; locked dev sync, sistem/locked check_docs, check_artifacts, check_learning (26 makale/29 statik QML bağı), Ruff check/format (59 dosya), GUI_SMOKE PASS, PHASE06_HEADLESS PASS ve iki kurulu wheel native/CSV worker smoke geçti. [Gerçek komut/çıktı/exit kayıtları](phase06-checks.txt). Erken paket smoke ardından final wheel tekrar build/install/test edildi. Ara koşulardaki QML nested item sözdizimi, yardım bağlarının eski eşlemesini koruma, şema2 pointer kabulü düzeltildi; başarısız ara koşular kabul sayılmadı.

<a id="e06-limits"></a>

JSON64MiB ve bounded XLSX tam XML belleği kullanır; CSV/JSONL/Parquet parça/lazy yolları ayrı. Decimal38,256 sütun,1MiB kayıt,depth16/toplam4096 şema düğümü ve kartesyen100000/record sınırları. JSONL UTF-8, xlsx OOXML bounded destek; genel xls/xlsm motoru değildir. Büyük native sink anlık peak hard quota değildir. Gerçek native masaüstü/remote CI/minimum donanım/clean offline installer/ağ FS doğrulanmadı. Faz07 başlamadı.

## Ölçülen ve görülen arayüz

ENV-06,2026-10-06; scripts/measure_phase06.py, [ham kayıt](phase06-headless.json). Dört küçük gerçek fixture için n=1/sıcak cache; RSS parent+worker örneklenir, hard peak değildir. JSON, JSONL, Excel ve Parquet geniş1366×900/açık/%100 ve dar720×560/koyu/%200 toplam8 gerçek render. Ajan görüntüleri inceledi; dar JSON checkbox metnindeki kırpılma Label wrap ile düzeltildi ve son render tekrar incelendi. Parametreler kaydırılabilir, tablo yatay kayar; tarih/aralık etiketleri görünür. Yeni ana ekran tasarımı yapılmadı; Faz02 resmî referans incelemesi ve mevcut Theme tasarım dili korunur. Native masaüstü kabulü değildir.

[JSON geniş](phase06-json-1366-light.png), [JSON dar](phase06-json-720-dark.png), [JSONL geniş](phase06-jsonl-1366-light.png), [JSONL dar](phase06-jsonl-720-dark.png), [Excel geniş](phase06-xlsx-1366-light.png), [Excel dar](phase06-xlsx-720-dark.png), [Parquet geniş](phase06-parquet-1366-light.png), [Parquet dar](phase06-parquet-720-dark.png). Kaynak birleşik prompt SHA256 efae07bc3a6fc6b9c48a00c2f3e09c530f5c894d228090c9e09c596f1e79d214 önceki kayıtla aynıdır.
