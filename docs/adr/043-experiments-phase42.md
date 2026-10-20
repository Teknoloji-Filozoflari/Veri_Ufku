# ADR043: Önceden belirlenen bağımsız iki kol ve sabit ufuk

2026-10-11; DEC42-01 kullanıcı talimatıyla Faz42 teknik uygulaması açıldı;
önceki resmî kabul kapıları korunur. Python/PySide6/QML masaüstü; mevcut
Capability/AnalysisSpec/StatisticsController/spawn/ComputeBudget ve ProjectStore
atomik yayın yolu genişletilir. Worker ACTIVE/Qt almaz; ağ bağımlılığı eklenmez.

42.1 ortak-SD Cohen d TTestIndPower ve arcsine Cohen h NormalIndPower ile
iki yönlü a priori güç ve örneklem hesabı. Mutlak MDE/baseline/SD/alpha/power,
allocation P(B), ratio B/A, recruitment attrition varsayımı ve design effect=1
kayıtlıdır. Güç planı observed power değildir. Yuvarlanan tasarım gücü kaydolur.
Oran güç hesabı normal yaklaşımdır, exact Fisher gücüyle eşdeğer değildir.

42.2 lexicographic benzersiz birim kimliği +seed PCG64 bağımsız Bernoulli
**yerel taslak** listesi. Atama sayıları rastgeledir, tam50/50 garanti değildir.
Kaynak salt okunur; gerçek kişiye tedavi atama veya mesaj yok.

42.3 tam roster, aynı bağımsız randomizasyon/analiz birimi, bir satır/birim.
Randomizasyon kanıtı/plan kimliği ve kullanıcı onayı gerekir; uygulama dış
randomizasyonu kanıtlamaz. Gözlemsel iki kol otomatik randomize etiketlenmez.
Özgün assigned kol korunur. ITT bütün assigned birimler; PP açık0/1 protokol
seçimi, associationdır ve randomize nedensel ITT iddiası değildir.

Exact binomial SRM tam assigned paydada P(B) ile; yalnız bağımsız Bernoulli.
SRM p<0.001 tanılama uyarısı primary çıkarımı kapatır. Fixed-count/block
randomization bu adapterda yok. Baseline pretreatment SMD betimsel; guardrail
önceden seçilen mean/0-1 rate ve mutlak zarar sınırı betimsel, adjusted
çoklu-test/otomatik deney başarısı değildir. En fazla5 baseline/5 guardrail.

Ölçüm null missing sayılır;0 event değildir. Assigned/population/observed/
missing/event/protocol-excluded paydaları ayrı. Eksik outcome varsa tam ITT/PP
p/CI yok; binary worst-case sınırı yalnız tanımlama sınırıdır, CI değildir.
Ortalama: bağımsız birimler ve küçük örneklemde uygun yaklaşık normal
dağılım/ortalama çıkarımı varsayımıyla Welch fark0 p ve mutlak t CI;
varyans eşitliği gerekmez, küçük n/uç değer güvenilirliği otomatik kanıtlanmaz. Relative point baseline0 iken tanımsız,
mean ratio CI sunulmaz. Oran: Fisher iki yönlü p; Bonferroni eşzamanlı
Clopper–Pearson aralıklarından muhafazakâr absolute/relative CI. Fisher p ile
CI tersine eşdeğer değildir. Control alt sınırı0 ise relative CI sınırsız,
sahte sonlu CI yok. Constant mean variance çıkarımı unavailable.

Sabit ufuk ve ölçüm penceresi onayı kullanıcı beyanıdır; dış peeking otomatik
saptanmaz. Planlanan roster eksik veya ufuk onaysızken çıkarım yok.
Sequential monitoring kapalı; doğrulanmış alpha-spending/e-value adapter yok.
42.4 paired;42.5 cluster/design effect;42.6 factorial ayrı **uygulanmamış** alt
işlerdir, yanlış independent hesapla taklit edilmez. Bu teslim ilk basit yolu
bitirir; ek varyantlar için ayrı geliştirme gerekir.

100000 tam roster ve RAM/CPU/disk/iptal bütçesi; filtreli roster ret. Typed
scalar numeric/0-1/key, decimal/nested/time/weights yok. Safe JSON plan/result
ve RowId/details parquet; publish sırasında özgün roster/ölçüm/seed tekrar
kaynakla doğrulanır. Source/config/dataset stale save/export ret.

Backend kaynakları (2026-10-11 kontrol):
- https://www.statsmodels.org/stable/generated/statsmodels.stats.power.NormalIndPower.solve_power.html
- https://www.statsmodels.org/stable/generated/statsmodels.stats.power.TTestIndPower.html
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html

Gerçek test/GUI/paket sonuçları docs/evidence/PHASE42.md içinde kaydedilir.
