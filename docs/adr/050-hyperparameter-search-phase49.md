# ADR050 — Faz49 bounded nested search

DEC49-01 yalnız açık Faz49. Veri_Ufku Python/PySide6/QML korunur.
Tek Capability registry/ComputeBudget/Provenance/ProjectStore genişletilir.
Grid ve seeded unique random finite conditional discrete space; optional Optuna
TPE categorical configuration-index adapter. Continuous/user-code distributions
kapalı; optional backend ortamı yoksa gerçek eğitim doğrulanmış sayılmaz.

Global ValidationPlan final holdout ve joint group/time/horizon ayrımı aynı kalır.
Her outer train için inner plan bir kez kurulur; bütün triallar bu üyeliği kullanır.
Outer skor trial/winner/pruning seçmez. Full-development inner tuning önerisi
nested outer prosedür tahmininden ayrıdır. Final test yalnız mevcut journal ile
ayrı onaylı evaluation. Yeni search/choice eski test kullanımını silmez.

Raw inner-train preprocessing; variance-only selector training-only non-native
pipeline; native categorical variance kapalı. Bagging bootstrap child ve stacking
inner OOF prep/selection training-only. Calibration/ileri supervised selection/
indicator/MI araması kapalı ve açıkça reddedilir. Stacking time/group_time kapalı;
random fallback yok. Gradient boosting external stopping inner training içinde
ayrı joint validation; inner scoring/outer/final birbirinden ayrı. Pruning explicit
partial inner-validation loss threshold; pruned tam CV diye sunulmaz.

1000rows/32features/12trials per scope/4outer+4inner folds/600nativefit upper,
CPU concurrency1; total nested/stacking/curve cost gösterilir. Wall elapsed resume
ile sıfırlanmaz; RAM/process/cancel kaynak sınırları mevcut budget üzerinden.
Completed/failed/pruned/canceled attempt farklı; terminal attempts immutable.
Resume source/pipeline/space/seeds/joint plans/environment+engine hash uyumluluğu
ister. Değişen bilimsel tarif için yeni arama; final test geçmişi yine korunur.

Parent frozen plan ve source-bound prediction metrics/constraints/winner/scope
kontrolünü yapar. Worker Qt/ProjectStore/ACTIVE almaz/yazmaz. Checkpointler büyük
project JSON içine tekrarlanmaz: safe JSON artifact+hash, kısa ordered chain
summary, atomic transaction; eski kayıtlar ve model korunur. Eski search açılışı
network/fit veya kullanıcı kodu import etmez. Öneriyi modelde eğitmek ayrı mevcut
BaselineRun/lifecycle eylemi; tuning sonrası tekrar CV keşifseldir, dış tahmini
bağımsız final test diye sunmaz. GUI validation curves categorical axes fake
continuous değildir; yalnız numeric çizgi, categorical table.

[scikit-learn nested CV](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html),
[Optuna TPE](https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.TPESampler.html).
[Gerçek kanıt](../evidence/PHASE49.md).
