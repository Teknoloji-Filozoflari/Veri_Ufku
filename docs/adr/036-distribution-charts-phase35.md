# ADR-036 — dağılım ve belirsizlik grafikleri

2026-10-11; DEC-35-01. Python/PySide6/QML, mevcut ChartSpec/v1 ve
tek Capability registry genişletilir. Dataset, RowId üyelikleri ve
ProjectStore atomik yayın yolu korunur. Görünüm veri dönüştürmez.

Violin/KDE Gaussian kernel kullanır. Violin genişliği her grup/facette
peak yoğunluğu 0.35 yarı genişliğe ölçekler; sayım genişliği değildir. Scott/Silverman ve açık bandwidth
çarpanı; en az üç değişken gözlem, en fazla5000 örnek/128 grid noktası.
Frekans ağırlığı tekrar sayısıdır; varyans W-1 ve Scott N=W ile tekrar
edilmiş örneğe eşdeğerdir. Analitik ağırlık betimsel kütle olarak açık
seçilir; etkili n=(sum w)^2/sum(w^2), covariance ağırlıklı payda kullanır.
Survey/sample_weight ve desteklenmeyen grafik ağırlıkları reddedilir.
Bu tanım istatistik yöntemlerindeki analitik ters-varyans ağırlığıyla
otomatik eşitlenmez. Sıfır ağırlık sayılır ve açık dışlanır; eksik/negatif
reddedilir. Kaynak değişmez.

Histogram ortak bin sınırları, her facet/grupta ayrı normalizasyon:
count, probability, density, percent. Box frekans için sanal tekrarın
linear quantile'ı, analitik için inverse weighted CDF; yöntem kaydedilir.
ECDF sağ sürekli ve eşit değerler tek sıçrama; üyeler sıçramayı oluşturan
RowId'lerdir. QQ standart normal quantile'a karşı gözlenen değer; PP fit
normal CDF'ye karşı (i+0.5)/n. Referans mean/SD aynı örnekte fit edilir;
normalite testi diye sunulmaz.

Belirsizlik grafiklerinde yalnız mean agregasyonu desteklenir; başka tarif
reddedilir ve formda geçersiz seçenek sunulmaz. SD s(ddof=1), SE=s/sqrt(n),
CI mean±t(df=n-1)*SE; her hücrede n>=2.
Bağımsız gözlem ve uygun ortalama çıkarımı varsayımları görünür. CI band
noktasaldır; eşzamanlı/survey çıkarımı değildir. Kaynak fingerprint,
ColumnId, tarif ve RowId üyelikleri hesabı bağlar.

Strip deterministik yatay jitter, swarm ölçüm uzayında sınırlı şerit
yerleşimi;500 gözlem ve dolu şeritte dur. Piksel çakışmasızlık garantisi
vermez. Missing-pattern yalnız null bit desenidir; mekanizma çıkarmaz.
Facet en fazla4; kategorik sıra tüm etiketleri açık içermeli. Eksik ve
metin etiketleri çakışmaz. Sessiz grup birleştirme yok.

Log sıfır/negatif çizim değeri/interval endpoint/bin sınırında durur.
Symlog eşik seçimi kaydedilir. Palet, font, annotation, başlık/eksen ve
DPI görünümdür. Kırpma ve yüzde ölçek açık metadata/footer taşır.
PNG/SVG yanında PDF ek artifact; eski beş artifact'lı kayıt okunur.
Yeni kayıt aynı atomik protokolle altı artifact doğrular.

Birincil kaynaklar:
[SciPy gaussian_kde](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gaussian_kde.html),
[Matplotlib eksen ölçekleri](https://matplotlib.org/stable/users/explain/axes/axes_scales.html),
[Matplotlib errorbar](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.errorbar.html).
