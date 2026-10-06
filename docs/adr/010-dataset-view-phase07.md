# ADR-010 — Faz07 salt okunur görünüm, profil ve semantik sürüm

Tarih: 2026-10-06. Durum: uygulandı; kapsam yalnız Faz07. Python/PySide6/QML korunur. Uygulama0.1.0; proje şeması4 bağımsızdır. Şema1/2/3 açılışında otomatik migration yazılmaz; açık kaydet yeni manifest4 yayımlar. Şema0 ayrı kopya migrasyon sınırını korur.

## Görünüm ve kimlik

Polars lazy Parquet taraması, bütün dataset üzerinde en fazla8 AND filtre ve kararlı sıralama, ardından200 kayıtlık sayfa. Ana Qt model yalnız son sayfayı tutar; QML TableView delegate reuse açıktır. UI hücre metni256 karakter; sayfa metni4MiB; kırpma fiziksel snapshot'ı değiştirmez. Yüksek kardinaliteli bütün değerler arayüze aktarılmaz. Sütun araması metadata listesini arar; gizleme yalnız projeksiyondur. Görünüm sırası RowId değildir. RowId ve SourceRecordId orijinal snapshot'tan birlikte taşınır; eşit sıralama anahtarlarında özgün kayıt sırası korunur. Nested/binary sıralama ve değer karşılaştırması bu sürümde açık hata verir; null filtresi desteklenir.

Filtre ColumnId ve tipli literal ile oluşturulur; eval/SQL ifade kabul edilmez. Büyük integer/Decimal filtre değerinin hassasiyet veya aralık kaybı reddedilir. Tarih ISO, saat/saat dilimi fiziksel türe göre uygulanır. Sıradan float karşılaştırmaları yalnız sonlu değerleri kapsar; NaN/sonsuz için ayrı operatör gerekir. Null, NaN ve sonsuz birbirinin yerine geçmez.

Görünüm filtresi analiz dataset'ini değiştirmez. Profil kapsamı açıkça tüm dataset veya filtreli görünüm seçilir; görünüm filtresi tüm dataset profilinde uygulanmaz. Sıralama/gizleme profil kapsamını değiştirmez. Görünüm tercihleri oturumluk; filtreler saklanan profil parametreleri ve provenance içinde bulunur. Gizli filtreyle analiz üretme yolu yoktur. Sayfa kaynak doğrulamasının maliyeti vardır: her sorgu öncesi/sonrası immutable artifact hash/boyutu kontrol edilir.

## Kaynak, süreç ve bütçe

Sorgu/profil spawn Linux süreçte; Qt ana thread dosya taramaz. Import ve sorgu aynı ComputeBudget/process limit helper kullanır. Timeout, RAM/CPU, disk ve iptal kontrolü var; iptal veya eski binding sonucu projeye yayımlanmaz. Ana süreç proje yayınlama/kilitleme sahibi kalır; dataset işi boyunca kayıt/kapatma engellenir, iptal ardından serbest kalır. Private workspace temizliği yalnız o işin SQLite spool'unu kaldırır. Worker project-store'un O_NOFOLLOW ile tuttuğu dizinin `/proc/PARENT_PID/fd/FD` yolunu kullanır; spawn çocuğunun `/proc/self` tanıtıcısı kullanılamaz. Parent descriptor ömrü iş boyunca korunur. Son dosyada symlink ve değişmiş hash reddedilir.

Polars tarama streaming, profil4096 kayıt batch, örnek ilk10.000 kayıt. Global sort streaming motorun bütçesine tabidir; sonsuz kaynak veya sınırsız sort RAM desteği iddia edilmez. Kontrollü başarısız iş dataset'i değiştirmez. Ağ dosya sistemi desteği önceki local-only sınırını korur.

## Profil sözleşmesi

Seçili sütun için kapsam satır sayısı, dataset toplam satır/sütun sayısı, fiziksel tür, null oranı, non-null unique, ilk5 farklı örnek, en fazla20 frekans ve kalan kayıt sayısı. Bütün sütunların fiziksel türleri metadata listesinde erişilebilir; istatistikler sütun seçilerek hesaplanır. Tam profil bütün seçili kapsamı tarar. Örnek profil özgün immutable giriş sırasındaki ilk N kaydı kullanır; temsili/tahmini population sonucu olarak sunulmaz. Unique/frekans örnek içinde kesin; population unique tahmini üretilmez. Küçük kapsam tamamen tarandıysa scope full/filtered olur.

Null, boş metin, NaN, +infinity, -infinity ve geçerli değer sayıları ayrı. Unique null'u dışlar; NaN tek değer, ±inf ayrı, -0/+0 aynı. Sayısal hesaplar sonlu değerlerde; kimlik/kategori/serbest metin/ordinal/ignored rolünde ortalama, medyan, std ve yüzdelik bulgusu bastırılır. Korelasyon motoru bu fazda yoktur. Fiziksel min/max aralık bilgisi korunur. Decimal/int kayıpsız okunur; Float64 binary değeri Decimal.from_float ile hesaplanır. Ortalama/Welford varyans80 basamak Decimal; sqrt half-even80; UI std ≈10 anlamlı basamakla okunur gösterilir, kayıt80 basamaklı sonucu tutar; yuvarlama yöntem kayıtlıdır. std ddof=1 varsayılan veya kullanıcı0; n≤ddof tanımsız. Quantile linear h=(n−1)q, q=.05/.25/.50/.75/.95, medyan q=.50. Tarih min/max native Polars hesap/cast ile timezone ve ns korunarak gösterilir.

Unique/frekanslar private SQLite disk spool içinde;8MiB SQLite cache ve FILE temp. Tam farklı değer listesi Python RAM'e veya UI'ye gelmez. Nested list/struct için fiziksel tür/null/5 örnek korunur; exact nested unique/frekans bu sürümde destek sınırı olarak görünür. Frekans/örnek metinleri256 karakter kırpılabilir, özgün veriler korunur.

Profil sonucu dataset version, ColumnId, snapshot fingerprint, kapsam, filtreler, sample yöntemi, seed gerekçesi, ddof, quantile yöntemi, dışlamalar,80 basamak aritmetik ve content6 provenance taşır. Profil taslağa açık kullanıcı eylemiyle eklenir; projeyi kaydet ile atomik manifest/SQLite yayınına girer. Önceki veri/metadata sürümü sonucu güncel gösterilmez.

## Semantik metadata

Rol önerisi ilk200 immutable giriş kaydından ve fiziksel tür/alan adından; öneridir. Kimlik, kategori, ölçüm, tarih, serbest metin yanında ordinal ve ignored seçilebilir. ColumnId anahtarlı role/unit/ordinal_order/confirmed; dataset analysis_unit ve parent_version_ids asgari alanlardır. Rol değişimi yeni DatasetVersion yaratır; aynı snapshot ve aynı fiziksel import_metadata tutulur. Parent daha önceki aynı dataset/snapshot olmalıdır; cycle/yabancı parent reddedilir. Ordinal sıra1000 benzersiz metinle sınırlı; units/analysis_unit200 karakter. Kaydet sonrası reopen korunur. Metadata değişiminde görünüm filtreleri açık mesajla sıfırlanır. Profesyonel sözlük Faz32 kapsamındadır; burada başlatılmadı.

Resmî API dayanağı: [Polars lazy streaming](https://docs.pola.rs/api/python/version/2/reference/lazyframe/index.html), [std/quantile](https://docs.pola.rs/api/python/stable/reference/expressions/index.html), [Qt TableView reuse](https://doc.qt.io/qt-6/qml-qtquick-tableview.html). Gerçek kanıt [PHASE07](../evidence/PHASE07.md).
