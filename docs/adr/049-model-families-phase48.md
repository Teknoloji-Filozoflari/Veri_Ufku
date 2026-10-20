# ADR049 — Faz48 model aileleri

2026-10-12; DEC48-01 yalnız açık Faz48. Veri_Ufku Python/PySide6/QML.

Tek Capability registry/BaselineRun/ValidationPlan/ComputeBudget/Provenance/
ProjectStore/model lifecycle genişletilir. Explicit selected family; baseline
aynı outer folds/split/weights training loss. No universal best. Eski modeller,
defter, kaynak snapshot/RowId/ColumnId/SourceRecordId korunur. Test ayrı action.

Reg ElasticNet/Lasso, classifier logistic ElasticNet/L1 (saga);SGD squared/log
loss;tree/ExtraTrees/gradient/histgradient;SVC/SVR/KNN;Gaussian/MultinomialNB;
bagging10tree,voting2,stacking2+metaRidge/logistic. Her child kendi raw training
Frame'inden preprocessing öğrenir; outer FamilyScope identity. Stacking
independent/GroupKFold iç OOF, meta yalnız OOF outputs;no passthrough, inner
preprocessing refit;time/group_time closed no random fallback. Bootstrap içinde
vocab/scale öğrenilir. Numeric precision/null policy mevcut PreparationSpec;
moved advanced/calendar/text/selection/MI/indicator steps reject, no silent skip.

Native histogram categories:typed training vocabulary,unknown->missing,255limit;
no onehot/numeric impute;native categorical mask explicit. HGB internal
ColumnTransformer numeric partial(check_array) safe HGBArrayPreparation ile
learnedOrdinalEncoder/category-first partition preserved; full training matrix
native equality checked. No partial/function trust expansion. Fixed TreePredictor
and CSR numerical containers reviewed closed skops whitelist. Single-target CPU
adapter;multioutput/GPU unsupported boundaries explicit. Native scaling standard
not supported auto/none;non-native category trainonehot or explicit ordinalorder.
CSR explicit noncentering,no implicit densification;dense-equivalent budget.

Sample_weight training loss only;preprocessing and metric evaluation unweighted.
Baseline same weights;balanced class sample weights training-only. KNN/ensembles
weights reject;negative/missing/nonfinite/zero total reject. SVM proba/calibration
closed;no phantom probability or threshold tuning. GaussianNB dense;
MultinomialNB nonnegative and no centering. 5000rows/256transformedfeatures;
SVM/KNN2000,n²upper RAM;ensembles1000,nestednativefit upper count. CPU/wall/disk/
process cancel,convergence/numerical warnings reject;benign deprecation explicit.

Closed model card/label/source/feature order and estimator/native parameters
validated. Safe skops save/reopen and genuine transform/predict with zero fit.
Optional XGB/LGB/CatBoost lazy CPU native-category adapters:environment absent,
not compute verified;safe save/new-file persistence unavailable. RankingSpec/v1
query/relevance/features distinct,whole query split,no ordinary classifier
objective;optional factory only, ranking execution/evaluation GUI unvalidated.

Technical delivery vs formal acceptance separate;prior physical/human/AT/
minimum hardware/offlineinstall/remoteCI gates not closed. [Kanıt](../evidence/PHASE48.md).

2026-10-13 son denetim: ensemble membership/child scope/OOF/meta params closed
validation; meta convergence guard. GUI unsupported ROC/PR None→undefined
finite guard; SVM source/wheel replay. Optional CatBoost CPU depth kullanıcı
parametresi korunur; ranking factory YetiRank:mode=NDCG (runtime doğrulanmadı).
[Resmî CPU depth parametresi](https://catboost.ai/docs/en/references/training-parameters/common),
[rank objective](https://catboost.ai/docs/en/concepts/loss-functions-ranking).
