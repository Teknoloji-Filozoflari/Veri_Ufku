# ADR047 — Faz46 sayısal temsil ve fold-içi özellik seçimi

2026-10-12; DEC46-01 açık kullanıcı Faz46 talimatı. Faz47 yetkisi yok.
Mevcut Capability/AnalysisSpec/ValidationSpec+ValidationPlan/ComputeBudget/
Provenance/StatisticsController/ProjectStore genişletilir; ikinci registry yok.
Python/PySide6/QML masaüstü; worker Qt/ACTIVE almaz, parent tek atomik yayıncı.

## Amaç ve sınırlı şema

Üç ayrı amaç: model_input (nested CV; final representation fit yalnız development),
compression (full snapshot fit, CV-ready sayılmaz), visual (full fit; target yok).
PCA/incrementalPCA/SVD/NMF/ICA bu amaçlarda; t-SNE ve optionalUMAP yalnız visual.
Variance filter compression veya modelinput; model/univariate/RFE/sequential
selection yalnız model_input. Initial numeric independent yol:2–20finitefeature,
selection<=10; model<=1000rows/visual<=2000/compression<=5000,minimum12rows.
Target regression veya explicit0/1binary; impute/drop target yok. Encoded/text,
category/ordinal/identifier/Decimal/time/group/weights desteklenmez; mevcut group/
time validation yerine iid fallback yok. Ana encoded model lifecycle değişmez;
bu yeni bounded sayısal template gerçek sklearnPipeline+mevcutbaselinefactory
ile çalışır. Downstreamfinalestimator deployment/test benchmark bu scope değil.

Missing reject veya açıkmean: imputasyon/scaling hertrainingfitte; tümüeksiktrain
column ret. None/StandardScaler(center)/StandardScaler(with_meanFalse) seçili;
NMF negatif/centering ret; shift/clip/MinMax implicit yok. Dense veya explicit
numeric table→CSR (yalnızSVD/NMF,center yok). KaynakParquet yine dense olarak
bounded okunur; sourcebyte/nnz/peakRAM bütçesi belirtilir, native sparse source
veya unlimitedoutofcore iddiası yok. IncrementalPCA gerçekbackendbatchfit;
imputer/scaler ve kaynak bounded matriste, bütünpipeline incremental değildir.

## Algoritma, istatistik ve safe transform

Sklearn1.9.1 PCA(fullSVD),IncrementalPCA(batch),TruncatedSVD(randomized7iterations),
NMF(nndsvda,coordinate descent,Frobenius),FastICA(unitvariancewhitening),
t-SNE(BarnesHut,auto learningrate,perplexity,seed);optionalumap-learn lazy.
Iterations300–1000, explicitseed; convergence/sayısalwarning kontrolü, sonluoutput.
PCAcomponentdirectionsC.T ve loadingC.T*sqrt(eigenvalue),EV/ratio ayrı.
SVDuncentered projectedvariance/ratio PCAfractiondeğil. NMFnonnegativebasis,
ICAunmixing/mixing;bu ikisinde EV yok. t-SNE/UMAPev/loadings/inverse yok.
ReconstructionerrorFrobenius/MSE fitprepared/imputed/scaledspace, originalunit
loss veya heldoutsuccess değildir. Directions/sign/order değişebilir, neden
importance veya gerçek source class değildir. Görünümfirst2, allkartifactta.

RepresentationModel/v1 güvenli boundednumericJSON; sourceColumnId/orderedfeatures,
selectedmask,imputationstats,scale/center,C/mean/mixing ve supportflags. PCA/IPCA
linearcenteredtransform+inverse;SVDuncentered;ICAunmix/mix;NMFfixedbasisnewdata
SciPyNNLS (sklearnCD ile bitidentical değil, explicitnumericadapter),inverseWH.
Selectionrawcolumnsfilter+fittedscale;inversekapalı çünkü kaldırılan bilgi yok.
t-SNEnewdatatransform yok. UMAPbackend native transform olabilir, appsafe
modeladapter doğrulanmadığından newdata/inverse kapalı;kurulu olmayanbackend
çalışmış/tested sayılmaz. 1–50newrows numericmatrix;inverseapproximate, noexactloss
recovery. JSONschema/boyut/sonluarray/supportflaglarvalidate;usercode/pickle/importyok.

## İç CV ve selection stabilitesi

Mevcut ValidationSpec independentrandom/regression veya stratifiedbinary;
20%reservedtest,developmentfolds2–5. TestRowId nefit neeval neplot, targetlabels
keşifte kullanılmaz. Heroutertrain içindeki2–3innerfold yeniPipeline: selection/
prepare(reject/mean/scaling)/reducer/fixedbaseline. RegressionRidgealpha1 veya
binaryLogisticC1 mevcutmodelingbaselinefactory. Fixedk/hyperparameters önceden;
inner skorlar rapor, dışfold/test hedefleriyle bestk/adayı seçme yok.
Final representation refit developmentonly;predictivetest benchmark yok.

VarianceThreshold hamunitsquared,impute varsa trainmean. Modelbased topk
SelectFromModel(coeff magnitude) / F regression/classification SelectKBest /
RFE(step1,fixedk). Targetusingselector yalnız innertrainPipelinefit içinde.
Sequentialforwardselection kendi candidateinnerCV'sinde herfeaturecandidate için
rawsubset→train-onlyprepare→baseline; outerfit prep'ını innercandidatevalidation'a
sızdırmaz. Train/eval/selectioninnerRowIds vepreprocessingstats audit;fits<=3000
uppercost. FullCVtuning/flexibleestimators/group/time selection kapsamda yok.
OutertrainselectedoriginalColumnIds frequency ve pairwiseJaccard;overlappingfolds/
correlatedfeatures stabiliteyi etkiler;yüksekstabilitytruefeature/causalitydeğil.

## GUI, yayın, öğretim

Karşılaştır→46:12yöntem/amaç seçimi,explicitfeatures/target/scaling/missing/CSR/
fitk/seed/budget,parametre sınırları;preflight+approval;monochromeembedding veya
selectionfrequency,EV/loadings/fitrows/stability/inneraudit context, safe reuse,
export/save/hashreopen/cancel/stalesaveguard. Optionalbackend yoksa açıkKAPALI.
SourceRowId/SourceRecordId/locator veColumnId korunur; latentartifact userdataset
üzerine yazılmaz. Parent immutable source/semantic metadata/members/details ve
deterministichesap yenidenvalidate;current source/config/snapshot hash gates.
Learnsignaledger/scikittest claimsno classes. Offlinehelp latent/loading/sparseSVD/
selectionleakage17makale; no newtry_action. [Kanıt](../evidence/PHASE46.md).
Physical/AT/minhardware/cleanofflineinstall/remoteCI ayrı açık kapılardır.

## Birincil kaynaklar

[Sklearn decomposition](https://scikit-learn.org/stable/api/sklearn.decomposition.html),
[Feature selection](https://scikit-learn.org/stable/modules/feature_selection.html),
[TSNE](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.TSNE.html),
[Sequential selection](https://scikit-learn.org/1.9/modules/generated/sklearn.feature_selection.SequentialFeatureSelector.html),
[UMAP official](https://umap-learn.readthedocs.io/en/latest/),
[UMAP clustering limits](https://umap-learn.readthedocs.io/en/latest/clustering.html).
