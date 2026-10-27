# Faz46 — boyut indirgeme, amaç ve fold-içi selection

<a id="e46"></a>
2026-10-12;DEC46-01;ENV-46. [ADR047](../adr/047-dimensions-phase46.md).
PCA/IPCA/SVD/NMF/ICA; t-SNE görsel,optionalUMAP separatebackend. Variance/model/
univariate/RFE/sequentialselection,nestednumericPipeline veoriginalColumnId
stability. Testetiketleri/rowsplotyok;EV/loadings/inverse/transform destekleri ayrı.
OptionalUMAP ortam yok;çalıştırılmadı/tested sayılmaz. Technicalscope ile resmi
kabul farklı;physical/human/AT/minHW/offlineinstallation/remoteCI açık.

## Son teknik doğrulama

ENV-46: kilitli CPython3.13.15 `.venv`;scikit-learn1.9.1/NumPy2.5.3/SciPy1.18.0/
Polars2.0.0/PySide6.11.2/Matplotlib3.11.2/threadpoolctl3.6.0. Yeni bağımlılık yok.
[Gerçek ortam](phase46/environment.json),[17 kayıt](phase46/acceptance.json):
**16 teknik madde doğrulandı; optional F46-P007 UMAP doğrulanmadı.**
UMAP compute backend yok; tek compute test skip. UnavailableUIguard testi geçmesi
UMAP hesap testinin geçtiği anlamına gelmez. Resmî faz **sürüyor/deneysel/zorunlu**.

**Son Faz46:41passed/1skip** source ve noneditable installedwheel:
[sourceJUnit](phase46/phase-final.xml),[çıktı](phase46/phase-final.txt),
[wheelJUnit](phase46/wheel-targeted.xml),[çıktı](phase46/wheel-targeted.txt).
Son kaynak41/1skip:137.66s;wheel41/1skip:143.39s.
İlgili geniş kaynak regresyonunda **189passed/1skip**,262.86s;
[JUnit](phase46/targeted.xml),[çıktı](phase46/targeted.txt).
Bu related koşu son ColumnId/name export mapping ve integerfeaturetick düzeltmesinden
öncedir; bu iki final artifact değişikliğinde son41source/wheel ve12'şer GUI
walkthrough tekrar doğrulandı. **Tüm depo regresyonu çalıştırılmadı**; önceki full
regression sayıları bu fazda yeniden koşulmuş sayılmaz.
[Tekil testcase/runs/skip gerekçesi](phase46/test-summary.json).

PCAEV/projector/referenceinverse;IPCAtransform/inverse;uncenteredCSR-SVDreference;
NMFnonnegativebasis/sparse/NNLS/noEV;ICAunmix/mix/noEV;t-SNE noEV/newtransform/inverse;
variance rawthreshold/controlledempty,model/univariate/RFE/sequentialrealoutputs.
Nestedregression/binarypipeline;outer/inner/selectioninnerRowIdayrılığı,
preprocessingmeans ve heldouttarget değişiminde fittedmodel/stability değişmemesi.
Sequentialcandidate innertrain için auditedscaler actualfit büyüklüğü/mean,
outer/final wholematrix mean taşınmadığı kontrolü. OriginalColumnIdfrequency ve
pairwiseJaccard bağımsızreferans;method support/safeJSONarray/boyut/no-code,
source/ColumnId/RowId/SourceRecordId/fit-scope/publicationtamper rejection.
Cancel,negative/centering/CSR/missingguards ve finite profile mapping.

**12source+12wheel actualQML/spawn**:11 mevcutbackendmethod+PCAmodelinput;
purpose/scaling/fit/CV/help-F1/Escape/monochromegraph/loadings/safeJSONtransform/
approxinverse/export/save/freshresultreopen/cancel/stalesave/transformguards.
UMAP absentUIguard ayrı actualtest.2width×4position: **96+96PNG ve60+60safe
JSON/Parquet/PNG export**. [Source](phase46/source-gui/walkthrough.json),
[wheel](phase46/wheel-gui/walkthrough.json),[geliştirici görsel inceleme](phase46/visual-review.json).
Finalsource_columns export names/ColumnIds/schema dizisini korur; originalfeature
selection indexleri discrete ticks, wholecolumnmap parent source ile doğrulanır.

273packagefile source/wheel/installbyteeşit [manifest](phase46/wheel.json);
278finalapplication/test/script/lockhash [head](phase46/head-verification.json).
Walkthroughrunner yanlış singular test_dimension_gui importunu correctedplural
moduleye çevirdi; [ilkerror](phase46/initial-source-gui-import-error.txt),
[runnerfix](phase46/walkthrough-runner-fix.json). Bu fixture/runner değişikliği
compute implementation değildir; son actualwalkthroughlar doğru guardedrunner.
Fresh4XDGinstalledentry [GUI_SMOKE PASS](phase46/wheel-smoke.txt).
308offlinearticle/154UIbinding/640namedfield/189coreEnglish.17newlearningcontent;
[learning](phase46/learning.txt),[usability](phase46/usability.txt).
Docs/artifacts/Ruffcheck-format ve14belge unittest geçti.

## Yöntem ve kapsam sınırları

Initialnumericindependenttemplate:compression<=5000,visual<=2000,model<=1000rows;
2–20features/selection<=10/fitupper<=3000. Encoded/text/group/time/weight/Decimal
pipelinekombinasyonları desteklenmez; ana model lifecycle bu template ile otomatik
genişletilmedi. Burada actualnested numericPipeline fixedRidge/Logisticfactory ile
modelgirdi yolunu doğrular; finalestimatordeployment veya heldoutbenchmark yok.
Kaynağın daha önceden bütün veride fit edilmiş işlemleri bu yeni pipeline ile
kendiliğinden geri alınmaz; existing model-preparation history incelemesi ve
sızdırmasız kaynak seçimi ayrı sorumluluktur. CVscopereport suppliednumeric source
üzerindeki yeni fit izolasyonunu gösterir, bütün dışkaynak geçmişinin doğruluk
sertifikası değildir.

Fullfitcompression/visual CV-ready değil. Native sparse source/infiniteoutofcore
iddiası yok:explicitboundedtable→CSR yalnızSVD/NMFnocenter;sourceDenseRead bütçesi
dahil. IPCAmodel batch,source/scaler/imputer boundedfulltrainingmatrix.
NMFnewdatasafeNNLS backendCD ile bitidentical değil; inverseapproximate bilgi
kaybını geri getirmez. Selectioninverse removedcolumns değerleri üretmez.
Finite-onlynewdata profiles; missing training/evaluation imputation ayrı açıkplan.
UMAPadapterlazy/unvalidated/notinstalled;newdatasafeadapter/inversekapalı;
nativeUMAPtransformvarlığı uygulamada tested/persistedmodel anlamına gelmez.
t-SNE/UMAP globaldistance/gap/cluster count gerçek class değil; EV/loadings yok.
Stabilitytrainingfoldoverlap/correlatedfeatures etkilenir;truefeature/causalitykanıtı
veya uncertaintyinterval değil. Fixedk/hyperparametersönceden;outer/testilebestk
seçilmiyor. İçskorları görüp tekrardeneyler dışCV üzerinde seçim yanlılığı yaratabilir;
reservedtest hiçbirscore/plot/fitte kullanılmadı.

İlkGUI5methodpassed, t-SNE parentrecalc metadata exact mismatch yakalandı ve
publish reddedildi. Threadpoollimits her iki hesapta aynı native thread count/reduction
order sağlar; source/artifact validation allclose ile gevşetilmedi. Son t-SNEGUI,
core/phase/wheel exactpublish/reopen geçti. İlk runner import error kabul değil;
pre-column-map klasörleri ara artifact, sonwalkthroughlar currentpackage.
İlk core iteration fixture/directimport düzeltmeleri yalnız test tarafı;
başarısız kontrol başarılı sayılmadı. Qtshutdown ResourceWarning varsa insan/AT/
lifetime/performance kabulü diye sunulmaz.

Physicaldesktop/insan/Orca/AT/minhardware/cleanofflineinstall/remoteCI bu fazda
koşulmadı. Önceki resmîkapılar/Faz43monolithicaggregateRAM sınırı korunur;
budget gevşetilmedi. Connector/testsunucusu bu fazda sınanmadı. Çalışma ağacı/
untracked korundu; stage/commit/push yok. Faz47 başlatılmadı.
