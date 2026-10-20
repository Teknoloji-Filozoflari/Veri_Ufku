# ADR-016 — Faz13 veri exportu, yerel rapor ve isteğe bağlı rehber

2026-10-07. Uygulandı; olgunluk deneysel. Kaynak dosya korunur. Sonraki faz başlatılmaz.

## Veri sözleşmesi

ExportSpec/v1 seçilmiş DatasetVersion, snapshot SHA256, full/view kapsamı ve ViewSpec'i bağlar. Kullanıcı CSV/JSON/JSONL/Parquet/XLSX seçer. Hesap/yazma/yeniden açma ayrı spawn process'te, GUI25ms poll ile ilerleme/iptal alır. Sonuç makbuzu tür kaybı, kaynak/çıktı şeması, kayıt sayısı, filtre/sürüm, politikalar, koruma ve sayı→metin adetleri, projeksiyon hash'i ve yayın hash'ini taşır. Proje kaydet makbuzu ve mevcut işlem zincirini korur. Kaynak yeniden yazılmaz. Yeni proje dışı çıktı exclusive link/fsync ile yayınlanır; mevcut/symlink çıktı reddedilir, replace yoktur.

Parquet fiziksel tür/null/date/timezone/Decimal/nested/Binary/Duration/Time değerlerini korur; RowId iç sütunu analitik veri exportunda dışarıda tutulur. Uygulamanın rol/birim/geçmişi proje kaydındadır; Parquet rol/birim taşıdığı iddia edilmez. Parquet yeniden açılan şema/kayıt ve sıra duyarlı native row hash'leriyle doğrulanır. Metin/XLSX projeksiyonunda bağımsız okuyucu aynı kayıt sayısı ve sıralı SHA256 değerlerini doğrular. Test fixture'ları elle beklenen değerleri ayrıca denetler.

CSV UTF8 BOM, RFC csv quoting; null varsayılan `\N`, boş metin ayrı; gerçek token çakışması reddedilir. Yeniden importta null işareti/tür/tarih seçilir. JSON nesne listesi64MiB; JSONL satır başına nesne streaming. JSON native null/bool/int/float; büyük integer JavaScript53-bit okuyucuda kaybolabilir. CSV gerçek sayının lexical değerini korur, spreadsheet15-basamak okuyucusu ayrıca kayıp yaratabilir. Date/datetime tüm non-Parquet formatlarda ISO metin; Polars String cast ile ns korunur, IANA timezone tür metadata'sı kaybolur. Decimal tam metin; NaN/±inf açık metin tokenı, null değil. Nested/Binary/Duration/Time yalnız Parquet, diğerleri anlamlı ret.

Güvenli CSV varsayılan açık: kontrol karakteri veya boşluktan sonra =,+,-,@ ile başlayan gerçek String alanı ve başlık apostrofla korunur; gerçek negatif sayılar/Decimal bozulmaz. Koruma kapalı seçimi görünür riskle açık kullanıcı kararıdır. Null tokenı tehlikeli olamaz; güvenli başlık çakışması reddedilir. XLSX bütün metinleri OOXML inlineStr olarak yazar, `<f>` yoktur; sayılar numeric/bool hücrelerdir. Excel15-basamak kesinliğini aşan integer tam metne aktarılır ve adet kaydedilir. Ürün XLSX sınırı100000 veri kaydı+başlık/256 sütun/32767 metin karakteri/64MiB sheet XML; teorik Excel1048576 satır/16384 sütun değildir. Uygun daha büyük veri Parquet/CSV/JSONL'ye yönlendirilir. Non-Parquet tür kaybı açık onay ister.

## Yerel rapor

ReportSpec/v1 amaç/başlık/kapsam ve ilk1–200 tablo kaydını saklar. İlk20 sütun/hücre ilk500 karakter ve en fazla10 grafik açıkça belirtilir. Kaynak ve köken; ancestor sürümlerdeki kayıtlı profil/kalite; seçili sürüme bağlı işlem zinciri; sürüm/filtre/kapsam; güncel sürümün kaydedilmiş veya halen güncel grafiği; yöntem ve sınırlama bulunur. Eski bulgu kendi sürümüyle gösterilir, güncel temiz veri iddiasına çevrilmez. Farklı bağımsız dataset'in geçici bulgusu rapora girmez. Olmayan bölüm uydurulmaz.

HTML kullanıcı kaynak/başlık/amaç/hücre/metadata metnini escape eder. Statik CSS, data-URI PNG/font ve CSP default-src none; script, font/CDN/ağ gereksinimi yok.16MiB sınırı. PDF disposable process QGuiApplication offscreen, yerel DejaVu Sans + QTextDocument/QPdfWriter A4/15mm, resim kaynak allowlist'i, QPdfDocument yeniden açma/sayfa/metin kontrolü. Türkçe harf ve çok sayfalı son kayıt ayrıca test edilir. PDF/HTML render'ı kullanıcı metnini çalıştırmaz.

## Rehber ve ilk sürüm kapısı

Dosyamı anlamak istiyorum altı adım: import/profil/kalite/seçilen temizlik/grafik/rapor. Adım seç/atla/geri/kapat; ders veya otomatik temizlik yok. Satış6 ve problemli7 kayıt, CC0 sentetik CSV ve tipli Parquet; ayrı yeni projeye explicit eylemle aktarılır. Paket DejaVu Sans font+tam lisans, yerel yardım, iki örnek ve HTML/CSS rapor kaynakları içerir. Uygulama lisansı ve tam temiz offline kurulum/dağıtım Faz27 kararı değildir.

Teknik geliştirici walkthrough, gerçek son kullanıcı testi yerine geçmez. F13-S005 bilgisiz kullanıcı görev kabulü gerçek katılımcı ölçümü olmadan doğrulanmış sayılmaz; faz durumu bu kapı açıkken sürüyor kalır. İlk sürüm teknik önizlemedir. Gelecek istatistik/model ekranları mevcut özellik diye sunulmaz. [Release notu](../RELEASE_NOTES_0_1_0.md), [kanıt](../evidence/PHASE13.md).

## İncelenen birincil kaynaklar

- [Polars streaming batches](https://docs.pola.rs/api/python/stable/reference/lazyframe/api/polars.LazyFrame.collect_batches.html): installed2.0.0 iterator stop() sağlamıyor; iterasyonu bitirme ve worker kapanışı kullanılır.
- [Qt QTextDocument](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QTextDocument.html), [QPdfWriter](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QPdfWriter.html), [QFontDatabase](https://doc.qt.io/qtforpython-6.8/PySide6/QtGui/QFontDatabase.html).
- [Excel sınırları](https://support.microsoft.com/en-us/excel/excel-specifications-and-limits), [sayısal kesinlik](https://support.microsoft.com/en-us/excel/change-formula-recalculation-iteration-or-precision-in-excel).
- [OWASP CSV injection](https://community.owasp.org/attacks/CSV_Injection), [CC0 dedication](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en).

Yöntem/sınır kararı exact locked sürüm ve gerçek fixture testine dayanır; doküman güncel sürümden davranış varsayımı yaratmaz.

Görünüm exportu tabloyla aynı filtre ve stable/null-last sıralamayı kullanır; eşit anahtarlar kaynak sırasını korur. Gizlenen sütunlar yalnız sunum tercihidir ve exportta dahil olduğu açıkça yazılır. Full kapsam filtre/sort kullanmaz. Makbuz ViewSpec'i saklar. Rapor ilk tablo örneğini aynı sıradan alır. Qt/font başlangıcı ortak adres alanı sınırının baseline'ına dahildir; bundan sonraki büyüme2GiB/default, CPU2/thread affinity ve wall600s/cancel2s sınırları korunur.
