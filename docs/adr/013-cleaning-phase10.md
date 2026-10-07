# ADR-013 — Faz10 açık temizlik politikaları ve güvenli köken

2026-10-07. Yalnız Faz10. Python/PySide6/QML korunur; yeni bağımlılık yok. OperationSpec/method1, proje şema6, yardım içeriği9 ayrı sürümlerdir. Şema0–5 dosyaları salt okunarak açılır; açık kayıt migrasyonu önceki commitleri korur.

Temizlik `operations/cleaning_contracts.py` ve `cleaning.py` üzerinden aynı full önizleme/yayın yoluna girer. Dokuz discriminator: missing_rows, missing_columns, fill, dedup, trim, map_categories, convert, ordered_fill, outlier. ColumnId, giriş sürümü, çıktı şeması ve destination=chain/copy saklanır. Yöntemler kendiliğinden uygulanmaz. Uygula önizleme Parquet'ini hash/şema/sayım denetimiyle yayımlar; tekrar hesaplamaz. Etki sayımları tam veridir; ilk200 kayıt yalnız görüntü örneğidir. Değişen sütun sayısı seçilen sütun sayısı değildir: değişen değer/tür, çıkan veya eklenen sütun sayılır.

Kaynak ve geçmiş snapshotlar immutable. Chain mevcut dataset için yeni sürüm; copy aynı immutable girdiyi paylaşan ayrı DatasetId/başlangıç VersionId ve `forked_from_version_id` üretir, onun altına dönüşüm ekler. Kopyanın undo'su kopya başlangıcına döner; özgün dataset'in head'i değişmez. Copy+çıktı+dedup relation aynı ACTIVE yayınına dahildir; başarısız pre-ACTIVE adım hiçbir yarım dataset yayımlamaz. Geçmiş/branch/redo ve eski sonuç politikası ADR-012 ile aynı. Dataset referansları sessiz taşınmaz.

## Eksiklik, doldurma ve metin

Null ve IEEE NaN ayrı: varsayılan yalnız null; null_nan açık kullanıcı seçimi. Mean/median/IQR sonlu sayısal gözlemlerden hesaplanır; NaN/inf istatistiğe katılmaz. Kullanıcı null_nan seçmediyse NaN doldurulmaz. Missing rows/columns herhangi biri veya tümü eksik kuralıyla çalışır; boş dataset üzerinde hiçbir sütun çıkarılmaz. Son veri sütununu kaldırmak reddedilir. Kaynak veride hiçbir otomatik silme yok.

Sabit değer hedef fiziksel türe tam uymalı. Fiziksel türü Null olan tamamen boş sütunda tür tahmin edilmez; önce kullanıcı açık hedef tür dönüşümü yapmalıdır. Ortalama/medyan/mod tümü eksik veya hiç sonlu gözlem yoksa durur; kullanıcı sabit seçebilir. Tam sayı kesirli ortalama/medyanı kabul etmez; Decimal ölçeğine uymayan sonuç yuvarlanmaz. Sıfır varyans doldurması aynı sabit değeri üretir. Mod eşitliğinde varsayılan durdurma; kullanıcı eşit frekanslı gerçek aday değerini açıkça yazar. Yanlış aday reddedilir. Metin kırpma yalnız uç boşluklarını değiştirir, boş metin null olmaz. Kategori eşleme yalnız tam eski/yeni metin çiftleridir; eşlenmeyeni koru veya durdur açık politikadır, otomatik fuzzy/case eşleme yoktur.

## Sıra, gruplar, dedup ve köken

İleri/geri doldurmada en az bir açık grup ve sıra ColumnId zorunlu; doldurulan kolon anahtar olamaz. Zaman sırası fiziksel sayı/tarih, metin tarih önce dönüştürülür. Null/NaN/inf sıra veya grup anahtarı reddedilir. Eşit anahtarda immutable giriş sırası, ardından RowId; işlem sonrası özgün görüntü sırası yeniden korunur. Grup durum belleği batch sınırlarında devam eder, grup değişiminde sıfırlanır. İlk/son doldurulamayan eksikler eksik kalır ve sayılır. Geri doldurma ve azalan sırada ileri doldurmanın gelecek bilgisi kullanabileceği belirtilir.

Dedup tüm veya seçili veri sütunlarının anahtarına, açık sıra sütunlarına ve first/last seçimine bağlıdır; tablo görünümündeki sıralamayı gizlice kullanmaz. Kayıtlı eşitlik v1: null=null, NaN=NaN fakat null≠NaN, +0=−0, Decimal sayısal eşitlik, timezone aynı an, metin tam eşitlik. Temporal anahtar fiziksel Int64 ile karşılaştırılır; ns farkı kaybolmaz. Survivor özgün RowId/SourceRecordId taşır. Disk tabanlı grup seçimi ve immutable Parquet relation her giriş kaydı için group_id,row_id,source_record_id,survivor_row_id,retained taşır; milyonlarca üyelik JSON'a açılmaz. Undo/redo/reopen aynı kimlik ve relation'ı kullanır. Join/explode/aggregate/sort henüz executable değildir; UI eklenmedi.

## Tür, Decimal, tarih ve IQR

Int64/UInt64 aralık ve kesir doğrulaması; Decimal precision≤38/scale≤precision, sonlu değer ve ölçeğe tam uyum. Binary Float64'te tam temsil edilmeyen kesin metin/Decimal (örn. 0.1) reddedilir; kullanıcı Decimal seçebilir. Float→integer/Decimal da kaynak float'ın gerçek binary değeri üzerinden doğrulanır. Sessiz yuvarlama, overflow veya underflow kabul edilmez. Hata politikasında varsayılan tüm işlemi reddet; açık null seçimi hata ve yeni null sayısını, ilk5 RowId/ColumnId örneğini raporlar. Mevcut null hata sayılmaz. Tarih biçimi açık strptime veya boş ISO; sayısal epoch yorumu yoktur. Geçersiz tarih düzeltilmez.

Datetime hedef us; ns→us yalnız tam temsil edilebiliyorsa geçer. Native tarihler ISO metin/offset ile doğrulanır; timezone kaybı reddedilir. IANA timezone yerel ZoneInfo'dan gelir. DST fold: reject varsayılan; earliest/latest kullanıcı seçerse iki gerçek UTC anından açık seçim. Var olmayan yerel saat bütün politikalarda reddedilir. ns doldurma, Python datetime us sınırı nedeniyle reddedilir; kullanıcı önce kayıpsız us dönüşümü seçebilir. Native ns dedup ve metne dönüşüm hassasiyeti korur.

IQR doğrusal çeyreklerle Q1−k·IQR / Q3+k·IQR dışında istatistiksel aday üretir. Varsayılan Boolean aday sütunu ekleme, açık alternatif filtrelemedir. Null/nonfinite aday değildir. IQR=0 durumunda strict dış eşik uygulanır: sabit kolon aday üretmez, meşru seyrek uç değer aday olabilir. Yöntem kayıt hatası kanıtı değildir. Sayısal hesap Decimal80 bağlamındadır; genel sınırsız hassasiyet iddiası yoktur.

## ML ayrımı, ekran ve sınırlar

Genel doldurma verinin tamamından öğrenir; eğitim fold'unda fit yapan ML dönüşümü değildir. Veri bağımlı yöntemler learned_scope=dataset ve `leakage_review_required` ile sürüm/parametre/öğrenilen değer geçmişinde kalır. QObject leakageHistory ve geçmişteki açık uyarı, gelecekte modelleme ekranının sızıntı incelemesi için veri sözleşmesidir; henüz model ekranı uygulanmadı.

Hazırla'da tek temizlik yöntemi formu görünür; önce/sonra tabloları ve geçmiş ayrıntıları kullanıcı açar. Geri al/yinele görünür kalır. Her yöntem küçük örnek, yarar/kayıp ve risk yardımıyla bağlıdır. D-01 elle düzenleme seçilmediği için tablo salt okunur. Kullanıcı manuel denemeleri daha sonra toplamak istedi; her faz otomatik kontrol edilir, yeni masaüstü/kullanıcı kabulü tamamlandı sayılmaz. Faz11 ve sonrası bu ADR ile başlatılmaz.

Polars collect_batches4096 ve disk tabanlı SQLite istatistik/grup işlemleri geçici çalışma alanında, ComputeBudget/Control sınırlarıyla çalışır. Tam preview, Parquet staging kopyası ve lineage toplam disk maliyeti vardır; iptal yayından önce geçerli, atomik yayın başladıktan sonra kapanır. 100.000 kayıt N=1 ölçümü minimum donanım veya sınırsız veri garantisi değildir.

Resmî API incelemesi: [Polars collect_batches](https://docs.pola.rs/api/python/stable/reference/lazyframe/api/polars.LazyFrame.collect_batches.html), [Python3.13 ZoneInfo/fold](https://docs.python.org/3.13/library/zoneinfo.html). Yerel kilitli Polars2.0.0/CPython3.13.15 üzerinde gerçek testler kanıttır; dokümana erişim tek başına kabul değildir.
