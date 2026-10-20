# ADR052 — model inspection, dilimler ve maskeli paylaşım

DEC51-01 yalnız açık Faz51. Tek Capability registry, LifecycleController/worker,
ComputeBudget, mevcut Provenance ve atomic ProjectStore result artifact extended.
ModelCard değişmez; ExplanationRun/v1 mevcut results listesinde safe JSON artifact;
append-only transaction previous explanations/model/test journals korunur.
Writer model/usercode deserialize etmez; kaynak fingerprint/RowId/actual target,
sample/group metric/reference uncertainty, model-card/package ve history kontrolü.

Only same immutable training snapshot, validation evaluation ve model fit-row
background; external/new-source background ve final-refitted development model
kapalı. Final holdout açıklamada açılmaz; scope exploratory after selection.
User selects background dataset, local RowId/class/feature and sample/budget/seed.
5000source rows/500sample/100background/16features/300000predictionrowpasses;
SHAP exact2^d preflight and checkpointcancel; no GPU. Worker Qt/ACTIVE yok, no fit.

Permutation entire original column grouped one-hot, seed/repeats/std ddof1; not
population CI. PDP empirical brute replacement one original feature; numeric
background quantile grid or explicit finite grid, category observedvalues table;
ICE perrow predictions and sample mean. Marginal support/outside/background,
correlation, missing/native imputation and impossible combinations warned.

FoldPreparation mapping fitted onehot/calendar/indicator/selection masks; joint
imputation dependency edges not hidden. Family child fit/preparation representation
component indices/source IDs separate; ensemble latent meta-input not falsely
mapped to raw features. Exact local linear/Ridge regression sum coef*(x-background
mean) with additive reference check; aggregate original ColumnId. Joint imputation/
family local-linear unsupported. This native reference is not labeled SHAP.
Optional SHAP ExactExplainer typed finite transformed independent background,
dense8features/20rows, allowlisted version0.51.0 numeric response, additivity/shape
check; backend absent here, runtime NOT validated, UI disabled, no auto-install.
A new backend version/environment requires reference/actualGUI evidence before
verified acceptance. Algorithm enumeration exact for empirical background; data/
background/population approximation and causal limits remain.

Slices explicit group/class/timeUTC/rangeedges plus missing/outside; n/accuracy/
MAE. Wilson for iid binary correctness/fairness rates, seeded percentile iid MAE
bootstrap; group/time protocol disables iid CI, not fabricated. Smalln<30 warning
and multiple searches/no simultaneous CI. Binary fairness only, explicit sensitive
ColumnIds/positiveclass, perattribute (not intersectional) counts/rates and max-min
DP/EO/EOdds/PPV differences. Base-rate tradeoffs and no badge. User chooses sensitive;
attribute labels remain inside project, never automatically inferred.

Sharing safeJSON rejects overwrite/symlink via existing atomic publish_file;
exclude modelcard/rawrecords/sourceRowIds/backgroundmembership/sensitive feature
names, grids, local contributions; sensitive group counts/rates/disparities omitted,
smalln<30 exported cells suppressed. No anonymity guarantee. Project archives
retain raw sensitive metadata for explicit analysis; model package export is not
claimed anonymized. Export does not silently change analytical data.

What-if frozen predictions, not causal counterfactual. Optional constrained finite
search all features assigned explicit immutable or values/direction/cost domains;
requires at least one immutable feature, finite100 candidate upper; numeric observed
background range/categories, complete source types, immutable check, userdesired
predictionclass/range, unitless range-scaled weighted cost; not universal optimum,
feasibility/actionability/causal guarantee. No-candidate only selected domain.

Sources: scikit-learn partial dependence/permutation primary docs,
https://scikit-learn.org/stable/modules/partial_dependence.html;
https://scikit-learn.org/stable/modules/permutation_importance.html;
SHAP ExactExplainer https://shap.readthedocs.io/en/latest/generated/shap.ExactExplainer.html;
Fairlearn metrics https://fairlearn.org/main/user_guide/assessment/common_fairness_metrics.html.
