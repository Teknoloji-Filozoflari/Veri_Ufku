# ADR-037 — çok değişkenli grafikler

2026-10-11; DEC-36-01. Tek Capability registry, ChartSpec/v1 ve immutable
RowId üyeliği genişletilir. Qt bağımsız worker; mevcut ComputeBudget ve
ProjectStore atomik yayın protokolü. Yeni bağımlılık yok.

Pair/scatter matrix2–6 açık sütun, en fazla36 panel; diagonal histogram
count, off-diagonal pairwise sonlu kaynak çiftleri. Complete-case ile
pairwise ayrımı saklanır. Panel×satır üyelik maliyeti collect öncesi,
ölçüm matrisine ek olarak RAM admission ile denetlenir. Nokta grafikleri
point_limit aşımında durur; örnek otomatik seçilmez. Açık ilk-N örnek
kaynak sırasına bağlı, temsil iddiası yok. CPU hexbin veya rectangular
2D histogram density büyük n alternatifi; density KDE değildir.

Hexbin iki staggered lattice / normalize x²+3y² en yakın merkez;
SciPy cKDTree ile üyelik atanır; Voronoi altıgeni aynı geometriyle çizilir.
Her hücre tüm kaynak RowId'lerini taşır. Density hücre sayım/(n×alan),
sum(density×cell_area)=1. Extent/bin/grid saklanır; GPU gerekmez.

Bubble marker alanı s=400*v/max veya yarıçap kodlamasında
s=400*(v/max)^2. Pozitif ölçümler; zero açık dışlanır, eksik/negatif ret.
Boyut legend zorunlu; boyut ölçeği ve formül saklanır.

Grouped heatmap açık mean/sum/median/min/max/count; boş hücre ret,
otomatik doldurma yok. Ham veya sütun z-score ddof0; sabit divisor1.
İlk görülen/alfabetik grup sırası; clustering average/complete/Ward,
Euclidean uzaklık, optimal_ordering=False. SciPy linkage ve row/column
leaf order, center/divisor/color_limits saklanır. En fazla100 grup×6 alan;
kümeleme maliyeti sınırlandırılır. Cluster gerçek sınıf kanıtı değildir.

Parallel yalnız sayısal kolon; per-column minmax, sabit0.5. Kaynak değer,
sınırlar ve RowId çizgi üyeliği saklanır; kategorileri ordinal kodlayıp
sürekli anlam uydurmak yerine açıkça ret. Facet en fazla4 panel;
koşullu ilişkide pooled+en fazla4 grup. Shared/independent gerçek eksen
sınırları render metadata ve statik çıktıda; pair shared sütun X / satır
Y, diagonal sayım ayrı. Koşullama nedensellik/Simpson teşhisi değildir.

Brushing yalnız tablo vurgusu. Ayrı eylem filtreli yeni dataset kopyası
önizler; kullanıcı Dönüştür ekranında uygular. Kaynak RowId/SourceRecordId,
grafik kimliği ve geri alma kökeni korunur. En fazla10000 tam seçili kayıt;
daha büyük seçim dataset dönüşümünde açık ret, ilk200 gösterim sessiz
filtreye çevrilmez. Mevcut filter OperationSpec/v1 aynı registry ve yayın
yolunda genişletilir. Eski tipli filtre tarifleri okunur.

Statik export için ayrı seçim işleme eylemi; immutable üyelik üzerinden
seçili gerçek kayıt sayısı, glyph IDs ve ilk5 RowId bağlamı footer'da;
tam seçili kimlikler result JSON'da saklanır. PNG/SVG/PDF; aynı dataset
ve snapshot bağı. 3D/surface isteğe bağlı ve uygulanmadı; perspektif ve
occlusion sınırı açıklanır,2D pair/facet önerilir.

Birincil kaynaklar:
[Matplotlib hexbin](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.hexbin.html),
[SciPy linkage](https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.linkage.html).
