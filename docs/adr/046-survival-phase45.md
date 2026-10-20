# ADR046 — Faz45 right-censored sağkalım şablonları

2026-10-12; DEC45-01 açık kullanıcı Faz45 talimatı; Faz46 yetkisi yok.
Mevcut Python/PySide6/QML, Capability/AnalysisSpec/ComputeBudget/Provenance/
ProjectStore genişletilir. Qt-free worker ACTIVE yazmaz; parent source doğrular.

## Backend ve veri şeması

Duration/event/unit identity, optional entry/group ve<=5numeric baselinepredictor.
Zaman birimi second/minute/hour/day/week/year açık; source duration/entry metadata
birimi varsa aynısı gerekli; sessiz dönüştürme yok. Ortak origin, event tanımı,
independent censoring/truncation gerekçesi ve üç açık kullanıcı onayı.
Statik SurvivalObservation/v1 birsubject/birsatır; null/imputation/drop/weight/
cluster/Decimal/Date ve sessizcause recode yok. SourceRowId/SourceRecordId/locator
ve ColumnId korunur. Nonmodel2–10000/model2–2000rows;5predictor/RAM/wall/disk/cancel.

statsmodels0.15.0 SurvfuncRight ve survdiff: right veya left-truncatedright,
entry0<=entry<duration; risk convention entry<t<=duration. PHReg Cox: right veya
left-truncatedright, backend convention entry<=t<=duration; entry aynı event
zamanına eşitse farklı risk set kuralı panel/rapor/risk table içinde görünür.
Entry leftcensoring değildir. CIF CumIncidenceRight sadececompetingright/entryyok,
0censored/1..Kexplicitcause labels;2–5cause;hergrupta tümcauses observed gerekir.
Interval/leftcensoring backend yürütmesi kapalı. Backend desteği registry/panelde
ayrı; desteklenmeyen seçenek exception vererek veri/snapshot korur.

## Hesap, tanı ve metrik

KM risk,event sayıları,GreenwoodSE ve log-logpointwiseCI (S0/1boundaryCIundefined),
median desteklenirse; groups ayrı. Noevent:Survival1,medianNone,tailunknown.
Logrank unweightedchi²/df,p;event/grup azlığında asimptotik sınırlama; zero singular
riskvariance unavailable. Independence assumed; group cluster anlamına gelmez.
CIFcompetingevents risk exits;allcauseincidence sum<=1.1−KM causeincidence değil.

Cox statikbaseline, optionalgroupstrata, tiesBreslow/Efron seçili. Partiallikelihood
score/hessian/fullrank,warning/nonfinite,coefficientextreme ve condition kontrolü;
enaz20/10×predictor events,herstrata5/2×predictor. KatsayıWaldCI/HR;HR eventprobability
değil. PHscreening: each event riskweightedSchoenfeld residual vslogtime,
Spearmantrend>0.3descriptiveflag; formal/calibratedPHtest değil. Efron tiedfit
residualmeansBreslowapproximation açık. FlagconstantHRprediction kapatır;
nonflagPHdoğrulanmış veya güvenilir rozeti vermez. PNGresidualscatter+curve.
Breslowbaseline cumulativeincrements currentevent dahil, originrightprediction.

AFT: sağdansansürlülognormal logduration=Xbeta+sigmaZ; intercept+baselinefeatures.
SciPyL-BFGS-B analyticlikelihood/score; eventslogpdf+censoredlogsf;log-sigma bounded
[-8,8],score/convergence/boundary/rank/observedinformation kontrolü. Analyticgradient
centraldifferenceobservedHessianWaldCI (L-BFGSapproximatecov kullanılmaz).
Ratioexp(beta) durationquantile time ratio;HR değil. Lognormaldistribution yanlışsa
prediction/inference yanlış olabilir. SansürsüzMLE logOLS ve numerictürev/refpdf
referansları testlerle doğrulanır. Aynı20/10×param eventgate.

HarrellC apparenttraining karşılaştırılabilirpairs;earlierobservedevent/laterfollowup;
same-timeevent/censorcomparable,twoeventtiesexcluded,tiedrisk0.5/tol1e-8.
IPCW değil;censoringdistributionsensitive;generalization/heldoutclaim/CIyok.
Delayedentry/poolstrataC kapalı. TimeBrier/AUC: validatedIPCWtrain/evalcensoring
protocol/backend yok;kapalı. OrdinaryMSE/ROC yerine sahte survivalmetric verilmez.

## Prediction ve model persistence

SurvivalModel/v1 safe boundedJSONnumericcoefficients/covariance/baseline/scale,
featureColumnIds,timeunit/trainingtime/predictorranges ve diagnostic gate.
No pickle/import/eval/usercode. Currenthashverified modelde yeni explicitprofile/
time/strata ile conditionalS(t) reused; modelrefit gerekmez. Coxbaselinecumhazard
ve exp(Xbeta);AFTnormalSF. PredictionCI yok; takip/predictor desteği dışıextrapolation
kapalı. Delayedentryoriginprediction doğrulanmadığından kapalı. PHscreenwarning veya
fitfailpredictionengelli. Kalıcımodel reopendathashcheck;source/dataset/config stale
save/export/predictengelli. Fitfail raporu kaydolur, modelNone. Yeni klasör safeexport.

## Time-dependent covariate sınırı

SurvivalCountingProcess/v1 ayrı declarativeid/start/stop/event/features/unit şeması:
0<=start<stop,subjectbaşına disjointcontiguousintervals,sabitid,0/1terminalevent,
eventsonrasırecordyok,no missing. Şema doğrulama uygulanır. PHRegstatikbaseline
longformatfitbackend değildir: countingprocessfit/predictkapalı. Bu validator
GUIyöntemlistesinde çalışırmodel gibi gösterilmez.

## GUI, yardım ve kabul

Karşılaştır→45:five methodforms,visiblebackend/censoringmatrix,preflight+explicit
approval,PNGcurve/PHscreen,risk table,report/modelreuse,atomic save/export/reopen.
F1/Escape/offlineyardım9makale;newtry_actionyok. Registrypredict/persist/interval ve
censoring/metricsupportconditional ayrı. Parent immutabledata/unit/members/details
ve deterministichesap/model tekrar doğrular. Worker currentprojectstate/Qt almaz.
[Faz45 kanıt](../evidence/PHASE45.md); physical/human/AT/minHW/offlineinstall/CIayrı.

## İncelenen birincil kaynaklar

[statsmodels duration](https://www.statsmodels.org/stable/duration.html),
[SurvfuncRight](https://www.statsmodels.org/dev/generated/statsmodels.duration.survfunc.SurvfuncRight.html),
[CumIncidenceRight](https://www.statsmodels.org/dev/generated/statsmodels.duration.survfunc.CumIncidenceRight.html),
[SciPy lognormal](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.lognorm.html),
[HarrellC comparablepairs](https://scikit-survival.readthedocs.io/en/v0.28.0/api/generated/sksurv.metrics.concordance_index_censored.html),
[IPCW Brier requirements](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.metrics.brier_score.html).
