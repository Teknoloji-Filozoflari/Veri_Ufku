# ADR-038 — kompozisyon, hiyerarşi ve akış grafikleri

2026-10-11; DEC-37-01. Mevcut ChartSpec/v1, tek Capability registry,
Qt'siz worker, ComputeBudget ve ProjectStore atomik yayın yolu genişletilir.
17 tür: stacked/100% bar/area, dot/lollipop, waterfall/Pareto,
treemap/sunburst, Sankey/alluvial, funnel/calendar, pie/donut/advancedradar.
Yeni dependency yok. Her türün input şeması registry ve sonuçta görünür.

Stacked bar kategorik X, area numeric/date artan X, series group,
nonnegative additive Y. Sum/count açık; ortak X×seri grid area için zorunlu,
eksik hücreye sıfır uydurulmaz. En fazla100kategori/12seri/500hücre.
100% payda her X içindeki katkı toplamı; density değildir. Area arası
linear interpolation gözlem uydurmaz; alan integrali kaynak toplamı değildir.
Dot/lollipop açık agregasyon. Pareto azalan katkı ve dahil toplam üzerinden
birikimli yüzde;80/20 evrensel yasa değildir.

Waterfall unique ordered labels, sonlu Y ve start/change/end alanı;
açık sıra start→change…→end. Supplied endpoint start+signedchanges ile
rtol1e-9/atol1e-12 eşleşmeli. Start/end yeniden katkı diye toplanmaz.

Tree unique nonempty string node, nullable parent, nonnegative finite Y;
200node/depth8/single root; disconnectedcycle da denetlenir. İç düğüm
kaynak miktarı0, yalnız leaf kaynak miktarı toplama katılır. Descendant
rollup display değeridir; aynı toplam tekrar toplanmaz. Treemap alternating
slice-and-dice rectangle area; sunburst angular parent fractions/depthrings.
Dış halka alanı value oranı değildir. Zero volume node listesi kayıtlı;
glyph üyeliğinde temsil edilmeyen zero leaf dışlama sayısına girer.

Flow source/target nonemptystring, nonnegativefinite Y;50node/100aggregate
edge DAG. Negatif/eksik/cycle/self-loop ret. Duplicate source/target edges
sum ile toplulaştırılır, tüm kaynak RowId'ler korunur. İç node giriş=çıkış
rtol1e-9/atol1e-12; dengesizlik ret. Boundary source/sink toplamı payda;
internal transit edge toplamı ayrı ve yeniden sayım diye belirtilir.
Alluvial adjacent levels zorunlu; skip-stage için Sankey. Node height/ribbon
width boundary toplamına orantılı, aynı cubic ribbon geometriyle çizilir.
Aggregate miktarlar bireysel entity yolları diye sunulmaz.

Funnel açık stage order/max12. People distinct sourceentity perstage,
nullkimlik ret; nested cohorts doğrulanır; duplicateperson-stage event
sayımı ayrıca kayıtlı. Events rows/repeats dahil, monotone count zorunlu;
kişisel dönüşüm çıkarımı yok. Yüzde payda ilk stage; kaynak satırlar
silinmez/düzeltilmez. Calendar Date/Datetime localcalendar day, singleyear,
Mondayfirst/leapday, missingday blankunknown; zero değil. Stringparse ve
implicit UTCconversion yok; explicit aggregate.

Pie/donut max6 mutuallyexclusive categories, nonnegativepositive total;
dot/bar daha açık alternatif. Eksik kategori include/separate veya exclude;
sum missingY paydadan dışlar, count missingY satırını sayar. Policy/n görünür.
Radar advancedopt-in/max6group/3–6numeric columns; complete-case percolumn
minmax0–1, constant0.5, groupnormalizedmean. Farklı unit ham eksene yığılmaz;
polygon alanı axisorder'a bağlı; dot/parallel alternatif. Unsupported
aggregation/group/facet/weight/nonlinearaxis/zoom açık ret.

Questiongallery aynı registry'den capability soru/inputschema/dependency
availability üretir; ayrı yöntem kaydı yok. Advancedradar normal galeri
aramasında gizli. Yüklenemeyen dependency ready değil, çalışmayan3D/surface
hiç hazır seçenek olarak eklenmez. Brushing/sourceidentity/staticselection/
PNG/SVG/PDF/save/openSaved Phase36'nın aynı yolu; kaynak veri değişmez.

Birincil kaynaklar:
[Matplotlib stackplot](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.stackplot.html),
[Matplotlib Wedge](https://matplotlib.org/stable/api/_as_gen/matplotlib.patches.Wedge.html),
[Matplotlib PathPatch](https://matplotlib.org/stable/api/_as_gen/matplotlib.patches.PathPatch.html).
