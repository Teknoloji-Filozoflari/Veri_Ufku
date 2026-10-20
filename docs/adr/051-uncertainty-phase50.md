# ADR051 — bağımsız calibration, frozen karar ve predictive belirsizlik

DEC50-01 yalnız açık Faz50 talimatı. Tek registry ve mevcut BaselineRun/v1,
ValidationPlan/v1, ComputeBudget, ProjectStore atomic yayın/final journal,
ModelCard/v1 optional typed uncertainty extension kullanılır; ikinci defter yok.

Outer validation/final holdout planı değişmez. Outer train içinde aynı splitter
proper train/probability-calibration/conformal-calibration bölümleri oluşturur;
class/group/time/equal-time/connected intervals/purge korunur, yetersiz plan
reddedilir. Bu sınırlı adapter inner CV eğitimi çalıştırmaz; splitter'ın frozen
CV planı kaynak-protokol üyelik kanıtıdır. Her iki calibration bölümü ve validation
eğitimden ayrı; calibration/none veya quantile-only seçilince ilgili ayrılmış
bölüm kullanılmaz, fit'e eklenmez. Fold-içi hazırlık proper train'de.

Sklearn CalibratedClassifierCV +FrozenEstimator ile explicit identity prediction
split; FrozenEstimator.fit no-op, yeni train/calibration CV veya random split yok.
Sigmoid a/b ve isotonic numeric monotone x/y maps yalnız incelenmiş typed wrapper'da;
multiclass OvR normalization ve label order exact sklearn reference ile denetlenir.
Brier binary half-sum [0,1], multiclass sum [0,2]; log-loss explicit string sort;
uniform-bin boundaries lower-bin; bin n/empty omission/provenance saklı.

Binary validation threshold cost, precision/recall constraints finite unique
probability grid; infeasible durur, no-positive precision tanımsız. Multiclass
argmax ayrı. Validation tekrar kullanımı iyimserdir; final rapor yeni seçim yapmaz.
Final test önce append-only reserve; yayınlanmış safe model calibration/maps/
threshold/q/source/plan/config eşleşmesiyle yüklenir; hiç refit yok.

Residual split-conformal Ridge/forest, quantile gradient50depth3 ve conservative
nonnegative CQR; rank ceil((n+1)(1-alpha)), sonlu rank mümkün değilse durur.
Classification score1-p(true class), ayrı conformal calibration. Coverage/width/
set-size tüm evaluation records, RowId ve gerçek n; quantile crossing açık min/max
rearrangement/count. Nominal marginal coverage exchangeability koşulludur;
grupsal/zamansal bağımlılığı çözmüş iddiası, subgroup/future garanti veya parametre
CI iddiası yok. Empty/full sets korunur. Native scope1000rows/32features CPU;
family/sparse/weights/TF-IDF burada kapalı, mevcut native ailesi bozulmaz.

Writer executable deserialize yapmaz: package card JSON/source hash/RowId/target/
shared split ve metrik referansları denetlenir. Closed skops whitelist, no user-code
import; immutable source/newprediction/table kimlikleri; atomic save/error/cancel
rollback mevcut protokol. Old cards unchanged; optional extra field yalnız typed
uncertainty wrappers. Öğren model-uncertainty makalesi genişletilir; yeni dört kavram.
