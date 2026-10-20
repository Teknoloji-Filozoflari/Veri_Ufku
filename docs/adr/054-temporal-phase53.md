# ADR054 — temporal diagnostics, panel forecast ve güvenli origin sınırı

DEC53-01 only Phase53. Existing TimeSeriesSpec optional advanced data descriptor;
old data() omits advanced=None, old archives and basic21 behavior preserved.
TemporalSpec/v1 closed finite templates, single Capability registry; worker Qt-free,
no ACTIVE;parent existing TimeSeriesStore transaction atomic publication/test reveal.
TimeSeriesRun/v1 advanced marker/commonProvenance/capture+budget, safeJSON not models.
Shared source checks/dataset lineage/RowId/type-group tokens and finaltest journal;
reopen reconstructs actual targets,origin membership,train-only MASE/prob metrics,
per-horizon andhierarchy sums withoutrefit. Source changes stop, no silent data edits.

Regular4000rows/8groups/1000periods/200fits. Calendar equality beforeglobal pooled
Ridge/hierarchy/clustering;no random row/segment split. Origins expanding chronological,
additive gap+embargo withheld fromfit,lead recorded; final allheld testperiods frozen
selected model. Pastcov fixedlag≥max(horizon,testperiods)+gap+embargo;early target
warmup discarded, no bfill; knownfuture explicit rationale andobserved external
availability remains user assumption. MASE seasonal train denominator;undefined scale
visible. SARIMAX/ARIMA conditional Gaussian sd getscoverage/pinball/CRPS/intervalscore;
not meanCI andnot guaranteed future/subgroupcoverage. VAR primary+2–4vector model,
stationarity reason/stability/rank;difference1 cumulative means,interval closed.

Centered development STL/decompose onlydescriptive, never forecastfeatures. ADFunitroot
andKPSSlevelstationarity differentnulls;lag/boundwarnings preserved,noproofbadge.
Change point explicit single penalizedRSS meanshift,serial/repeated-search limits.
Whole series entities classification:past summaryfeatures,train-onlyScaler+Nearest
Centroid,explicitdisjointwholetrain/validationIDs;no randomsegments. Shape clustering
wholealignedz-standardizedprefixKMeans,exploratory. Croston nonnegativepoint,notSBA/
unbiased/distribution. Hierarchy bottom-up tree withleavesonly/cycle/multipleparent/
coverageguards,notMinT;aggregateCI closedwithoutcovariance. Out-of-source futureexog,
fittedmodelpersistence/serving,newentityclassification andDTW/deep/classifier search
unsupported and visible. Local core independent of external backend/network.

Backend docs reviewed2026-10-13 against runtime statsmodels0.15.0/sklearn1.9.1:
[ARIMA](https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMA.html),
[SARIMAX](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html),
[VAR](https://www.statsmodels.org/stable/generated/statsmodels.tsa.vector_ar.var_model.VAR.html),
[STL](https://www.statsmodels.org/stable/generated/statsmodels.tsa.seasonal.STL.html),
[decomposition](https://www.statsmodels.org/stable/generated/statsmodels.tsa.seasonal.seasonal_decompose.html),
[ACF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.acf.html),
[PACF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.pacf.html),
[ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html),
[KPSS](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.kpss.html),
[Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html),
[NearestCentroid](https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.NearestCentroid.html),
[KMeans](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html).
Method references [accuracy](https://otexts.com/fpp3/toolbox.html),
[hierarchy](https://otexts.com/fpp3/hierarchical-forecasting.html),
[Croston](https://otexts.com/fpp3/practical.html). Declarations aren't acceptance;
source/noneditable actual compute/GUI tests provide bounded runtime evidence separately.
