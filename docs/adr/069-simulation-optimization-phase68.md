# ADR069 — bounded yerel senaryo, Monte Carlo ve solver

2026-10-16 DEC68-01. Kullanıcının açık Faz68 talimatı teknik kapsamı açar;
önceki resmî kabul kapıları kapanmaz. Faz69 yetkisi değildir.

Mevcut Capability, ComputeBudget, Provenance, RunCapture, experiment journal,
lineage ve ProjectStore atomik yayını genişletilir. İkinci registry/depo yok.
ScenarioSpec/v1 kapalı declarative JSON, executable expression/kod yok.
ScenarioRun/v1 hashli ≤2MiB native artifact; GUI özeti kaynak RowId/SourceRecordId
listelerini gizler. Sentetik dağılımda kaynak dataset/RowId uydurulmaz. Model
bağlanırsa gerçek eğitim DatasetVersion/fingerprint/fit RowId kökeni korunur.
Worker immutable envelope/pinned path alır; Qt/ProjectStore/ACTIVE yazmaz.
Kaydedilmiş rapor hash kontrolüyle açılır; hesap/ağ/model eğitimi başlamaz.

## Distribution şablonları

1..16 input; normal(mean,sd>0), uniform(low<high), triangular(low≤mode≤high).
Her input açık unit ve uncertainty=parameter/measurement taşır. Bağımsızlık
explicit dependence=independent; correlated yol yalnız bütün inputlar normal,
açık Pearson correlation matrix (simetrik, diagonal1, PSD). Genel copula,
truncated normal veya otomatik korelasyon tahmini yok. Parametre belirsizliği
ve ölçüm belirsizliği kayıtlı fakat nested epistemic/measurement variance
ayrıştırması hesaplanmış gibi sunulmaz.

NumPy PCG64, açık seed0..2³²−1; draw256..100000,1024lük control/cancel checkpoint.
Output offset + linear·x +0.5 xᵀQx; Q simetrik. Katsayılar value/unit; Pint ile
katsayı×input birimleri output'a çevrilir. Offset output birimindedir. Offset
Celsius cebiri reddedilir; basit çarpma uygulanmaz, açık uygun birime dönüşüm gerekir.
SD ddof1; quantiles .025/.25/.5/.75/.975 linear; mean MCSE=s/√n. Quantile MCSE
16 bağımsız blok quantile'ının örnek SD'si/√16: yaklaşık, küçük draw/kuyruklarda
kararsız. Bu error dağılım/model varsayımı belirsizliği veya predictive CI değildir.
Sensitivity marjinal Spearman ve sample mean'de algebraic local derivative;
correlated inputta bağımsız varyans payı/nedensel etki değildir. Affine joint-normal
şablonda analitik mean/variance ayrıca kayıtlı. Seed tek başına cihaz/sürüm bağımsız
bitwise yeniden üretilebilirlik garantisi değildir; RNG/chunk/env/code da saklanır.

## Solver adapter'ları

SciPy1.18.0 linprog(method=highs), milp(HiGHS) ve minimize(SLSQP). LP/MILP objective
linear; nonlinear bounded quadratic veya frozen model prediction. Constraints
ilk kapsamda linear le/ge/eq; bütün katsayılar ve RHS birimi açık.1..16variable,
≤64constraint, maxiter/nodes1..10000, seconds1e−6..600. Ortak600s/RAM/disk/native
thread/process/tasks limitleri devre dışı bırakılmaz. HiGHS threads ortak
worker_threads, parallel=false açık forward edilir; SciPy forward uyarıları raporda.
MILP presolve kapalı; bilinen unbounded/infeasible ayrımı ambiguous presolve sonucu
üretmez. Genel solver failure/ambiguous durumda kanıt uydurulmaz.

Solver raw_status, normalized status, direction, point, objective, gap/bound,
tolerance/time/nodes ve duration saklanır. Feasibility ayrıca bounds, constraint,
integrality ihlalleriyle yeniden hesaplanır; tolerance her gösterilen birimde
mutlaktır. Farklı birim ihlalleri fiziksel tek toplam gibi birleştirilmez. MILP
relative gap solver'ın constant hariç linear objective ölçeğindedir; objective
bound constant ile geri çevrilir. LP'de MILP gap üretilmez. SLSQP global bound/gap
üretmez; başarılı sonuç local_candidate, optimal=false. No convergence global
infeasible kanıtı değildir. HiGHS status2 infeasible,3 unbounded,1 limit; timeout
optimum değildir. Solver süre sınırı native çağrıyı içerir; SLSQP objective içinde
ve parent process supervisor'da da cancel/time denetlenir. Parent toplam bütçe
keserse yeni sonuç yayınlanmaz; önceki kayıt korunur. Solver'ın kendi süre/iteration
sonucu hesap tamamlanmış run olarak saklanabilir; output status başarıyla karışmaz.

## Frozen model senaryosu

Optional kullanıcı seçimi: completed safe regression .vumodel; genel model object
import yok. Kapalı loader/fingerprint/card/env sürüm doğrulama; private same-byte
model snapshot. Bütün özellikler Float64, eğitim ColumnId sırası ve birebir kart
birimleri; hedef birimi karttan. Native categorical/integer/classification/forecast/
tensor model objective yok. Fit/preprocessing tekrar öğrenilmez. Girdi yeni sentetik
point; kaynak row değiştirilmez, türetilmiş kaynak gözlemi gibi kaydedilmez.

Model eğitim snapshot fingerprint ve fit_row_ids doğrulanır. Yalnız fit feature
kolonları aralık için kullanılır; target değerleri okunmaz ve final-test satırları
aralık hesabına girmez. Kaynak≤min(10000,sample_limit_rows),16selectedfeatures. What-if
dış aralığı görünür işaretler. Model-optimize lower/upper fit min/max dışında ise
ret; optimizer bounded SLSQP. Aralık içinde olmak joint support, model doğruluğu,
operasyonel uygulanabilirlik veya causal effect kanıtı değildir. Fit RowId/source
record eşlemesi native artifact'ta, summary'de gizli; modele gerçek lineage edge.
Yeni run eski model/source/test geçmişini değiştirmez. Dış kaynak yazma/eğitim/deploy yok.

## Resmî kaynak incelemesi

2026-10-16 geliştirme incelemesi; runtime erişim gerekmez:
[SciPy HiGHS LP](https://docs.scipy.org/doc/scipy/reference/optimize.linprog-highs.html),
[SciPy milp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html),
[SLSQP](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html),
[SciPy joint-normal](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.multivariate_normal.html).
LP/MILP status/time/gap ve SLSQP ftol/local sınırı bu adapter kararına temel olur.
Kanıtlar [E68](../evidence/PHASE68.md); fiziksel/insan/AT/minHW/offlineinstaller/
remoteCI ve önceki açıklar ayrı kalır.
