# ADR-017 — Soru odaklı istatistik ve kalıcı sonuç

- Durum: kabul edildi, uygulandı
- Tarih: 2026-10-08
- Kapsam: yalnız Faz14; Faz15/model ve bootstrap başlatılmaz.

SciPy1.18.0 exact locked runtime seçildi; kurulu API f_oneway(equal_var=False) ile Welch ANOVA ve native t/Pearson/koşullu odds CI'yı destekliyor. Karar resmi [SciPy stats API](https://docs.scipy.org/doc/scipy/reference/stats.html) ve kurulu signature/result deneyleriyle doğrulandı; statsmodels gerekmedi.

Yöntem otomatik seçilmez. Soru, hipotez, ölçüm/grup/anahtar, birim ve bağımsızlık onayı zorunludur. Kullanıcı grafik/özet/önkontrolü inceleyip yöntem varsayımını ayrıca onaylar. Normalite tek başına karar vermez. Gözlemsel ilişki nedensellik değildir.

Uzun tablo eşleşmesi kullanıcı kişi anahtarı+etiketle yapılır; sıra kullanılmaz. Anahtar eksikliği ve tekrar kişi/etiket reddedilir. Eşleşmeyen kişilerde varsayılan dur, açık yalnız tam eş seçimiyle dışlamaları kaydet. Ölçümü eksik çiftler birlikte dışlanır.

Uygulamanın muhafazakâr koşulları:100000 kapsam kaydı/20 grup, skaler alanlar, sonlu Float64 ölçümü; en az2 t/rank/grup/eş,3 korelasyon,5 Kruskal grup gözlemi. Welch/ANOVA/Pearson/Spearman için grup/alan varyansı pozitif; paired t için fark varyansı pozitif; Wilcoxon sıfırları çıkardıktan sonra en az2 eş. Ki-kare tüm beklenen hücrelerde≥5; Fisher yalnız2×2. Bunlar kütüphanenin bütün geçerli sınır durumlarını desteklediğimiz iddiası değildir. Decimal/int → Float64 kaybı açık izin olmadan durur, izin ve kayıp sayısı kaydedilir.

Etki: t testinde birimli ortalama farkı, MW/Wilcoxon sıra biserial, ANOVA betimsel eta-kare (Welch sınırlaması açık), Kruskal epsilon-kare, ki-kare Cramér V, Fisher koşullu odds oranı, Pearson r/Spearman rho. Native t CI, n>3 Pearson Fisher-z CI ve Fisher koşullu exact CI kullanılır; diğerlerine CI eklenmez, gerekçe görünür. Fisher örneklem OR istatistiği ile koşullu OR etkisi ayrıdır. Tek yönlü CI açık sonsuz sınır taşıyabilir. Sonsuz değer JSON'da metin, NaN geçerli sonuç değildir.

MW küçük/ties yoksa exact, diğerinde continuity ile asimptotik. Wilcoxon sıfır/ties yok ve n≤50 exact; diğerinde wilcox/asimptotik, continuity yok. Float64 farkları otomatik yuvarlanmaz. Kruskal ties düzeltilir; Spearman p asimptotik/n≤500 sınırı belirtilir, permutation sunulmaz. Rank hipotezleri genel medyan farkı diye adlandırılmaz.

Post-hoc bütün seçili grup çiftleri; ANOVA/Welch sonrası Welch t, Kruskal sonrası MW. Dunn/Tukey değildir. Holm/Bonferroni aile hata kontrolü, BH bağımsız/pozitif bağımlı testlerde FDR veya açık none seçimi. Birincil omnibus test/diğer run'lar aileye dahil edilmez. Tekil CI'lar eşzamanlı/düzeltilmiş CI değildir. Bootstrap yok; seed/bootstrap null ve bağımsızlık varsayımı kaydedilir.

Qt bağımsız engine spawn CPU süreçte ortak deadline/RAM/disk/thread/iptal bütçesine tabidir; GUI SciPy yüklemez. Sonuç config/view/veri sürümüne bağlanır. JSON hesap ve gerçek RowId üyeliği hash+kök kontrolü sonrası mevcut ACTIVE atomik publication protokolüne girer; schema7 additive results, eski proje migration yok. Kaynak değişmez. Kaydedilmiş analiz HTML/PDF raporuna eklenir.

Kanıt: [PHASE14](../evidence/PHASE14.md), tests/test_statistics.py ve test_statistics_gui.py; source/kurulu Linux wheel ölçümleri. Faz13 insan kullanıcı kabulü açık olduğu için Faz14 teknik doğrulaması faz bağımlılık kabulü yerine geçmez.
