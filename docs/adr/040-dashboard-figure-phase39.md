# ADR-040: Faz39 sürüm bağlı dashboard ve yerel figure composer

- Durum: Kabul edildi; teknik uygulama tamamlandı, önceki resmî kabul kapıları açık
- Tarih: 2026-10-11
- Yetki: Kullanıcı “Faz 39'u uygula” ve “faz 39 tamamla” talimatları

## Karar

Explore içindeki PySide6/QML DashboardPanel grafik, tablo, KPI ve not kartlarını
12 sütunlu gridde düzenler. DashboardController mevcut ProjectController, ortak
ComputeBudget ve ResourceSupervisor yaşam döngüsüne bağlanır. Hesap/export ayrı
spawn sürecindedir; worker Qt almaz, kaynak veya ACTIVE yazmaz. Kaydedilmiş görünüm
ProjectStore results günlüğüne atomik mevcut save yoluyla eklenir.

Her widget immutable DatasetVersion ve ColumnId üzerinden bağlanır. Global filtre
kaynak sürümünü açıkça taşır; local filtre yalnız widget sürümünde uygulanır.
Başka kaynakta filtre/selection transferi kullanıcı seçimi olan source/target
version/ColumnId eşlemesi ister. Ad/konumla otomatik join veya tür dönüşümü yok.
Selection RowId ile başlar; çoklu eşleme anahtarları AND tuple olur; yinelenen
hedef anahtarların tüm satırları dahil edilir, null anahtar eşleşmez. İç içe/binary
ve sonlu olmayan anahtar kontrollü reddedilir. Eşlenmeyen filtre/selection kartta
anlatılır. Selection görüntüleme ve açık drill-down ayrı; kaynak değişmez.

Grafik kayıtlı base filtrelerini ve açık sample kararını korur. Tam dashboard
snapshot kaynağı başına 10000 satır, kaynakların toplam tahmini RAM admission'ı,
100 widget, 12×48 grid ve 16 composer paneli sınırı vardır. Büyük veri sessizce
örneklenmez; kullanıcı daha küçük açık veri sürümü seçer. Tablo ilk200 satırı
çizdiğini belirtir; hesap/seçim tüm izinli snapshot kapsamındadır.

KPI agregasyonu, dahil/sonlu/dışlanan n, pay, payda işlemi ve açıklaması görünür.
Paydasız ham agregasyon ile rows/non-null/column-sum oranı ayrı seçilir. Sıfır/boş
payda tanımsızdır. Önceki dönem açık ayrı local predicate ister; global ve kayıtlı
base filtreleri korunur, dönem filtresi current local filtre yerine geçer. Fark
ham ölçekte verilir; otomatik tarih veya yüzde değişimi tahmin edilmez.

Aktif dataset sürümünden ayrılan veya kaynağı değişen kart görünür şekilde eski
olarak işaretlenir; yeniden açılışta güncel veri gibi gösterilmez. Filtre/ayar
revizyonu değişince önceki hesap görünür uyarı taşır, yeniden hesap olmadan export
yapılamaz. Snapshot hash ve RowId bütünlüğü hesap öncesinde doğrulanır.

## Figure ve export

FigureSpec subplot grid, kaynak facet, ortak legend, accessible/colorblind/grayscale
renk ve üç DejaVu typography preset, font boyutu, inç boyutu, caption, unit ve kaynak
bağlamını saklar. Mevcut chart renderer Matplotlib SubFigure üzerinde koordinatları
yeniden çizer: SVG/PDF çizgi/nokta/alan/metin vektördür; paneller PNG olarak gömülmez.
Doğası raster olan heatmap/image katmanı raster kalabilir; çıktı bu ayrımı gizlemez.
PNG raster seçeneğidir. Ortak legend aynı grup renklerini kullanır; farklı kodlamalı
aynı legend etiketi kontrollü ret verir, ayrı legend seçilebilir. Bubble size/colorbar
gibi yerel açıklamalar korunur. Pareto çift ekseni açık uyarı ve sol/sağ legend taşır;
yanıltıcı otomatik eksen kırpma sözleşmede reddedilir. Statik export etkileşimi korumaz
uyarısı GUI/yardım/çıktıda vardır. Mevcut çıktı ve proje/source dosyaları değiştirilmez.

İzinli rendering adapter `local-svg/v1`: kendi paketimizdeki
`charts/local_svg_adapter.js`, mevcut yerel SVG ve gömülü DejaVuSans fontu tek HTML
belgesinde sunar. Ağdan JS/font veya veri çekmez; CSP connect-src none, dış script yok.
HTML kayıtlı grid, sürüm, filtre/KPI tanımı ve caption/unit/source bağlamını korur.
Tablo ve grafik tıklaması/klavye seçimi aynı RowId/açık eşleme sözleşmesini kullanır.
Bu dondurulmuş snapshot etkileşimidir: KPI/aggregate yeniden hesaplanmaz, yeni veri
alınmaz; kullanıcıya açıkça yazılır. Masaüstü GUI web uygulamasına dönüşmez.

## Doğrulama ve sınırlar

[Gerçek kanıt](../evidence/PHASE39.md): bağımsız row/KPI referansları, gerçek
ProjectStore save/reopen, 17 composition ve9 multivariate composer, QJSEngine'de
adapter klavye/duplicate/null transferi, kaynak ve noneditable wheel QML walkthrough,
SVG/PDF font/legend/bağlam ve source byte eşitliği. Öğrenme kataloğunda dashboard
sorusu, filtre kapsamı, KPI ve okunabilir figür için dört makale/bağ vardır.

Offscreen/software fiziksel masaüstü, insan/Orca/AT veya minimum donanım kabulü
sayılmaz. Önceki F13/F24/F25/F27/F28 kapıları kapanmadı; teknik teslim ve resmî
sürüyor/deneysel/zorunlu durumu ayrı kayıtlıdır. Faz40 uygulanmaz.
