import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "modelFamiliesPanel"
    property var protocol
    property bool protocolBlocked: false
    readonly property string purpose: (preparation.report.spec||{}).purpose||"regression"
    readonly property var methods: validation.familyMethods(purpose)
    readonly property var selected: methods[methodChoice.currentIndex]||({})
    readonly property var support: selected.support||({})
    readonly property string method: selected.id||""
    signal helpRequested(var origin, string context)
    spacing: Theme.md
    property string helpContext: "model.families"
    function config() {
        let result={method:method, family_options:{matrix:matrix.currentIndex===0?"dense":"sparse",scaling:["auto","none","standard"][scaling.currentIndex],alpha:Number(alpha.text),l1_ratio:Number(ratio.text),C:Number(c.text),trees:Number(trees.text),depth:Number(depth.text),learning_rate:Number(rate.text),neighbors:Number(neighbors.text),max_iter:Number(iterations.text),kernel:kernel.currentIndex===0?"rbf":"linear",gamma:"scale",class_balance:balance.currentIndex===0?"none":"balanced",weight_column:weight.currentValue||"",weight_kind:["sample_weight","frequency","analytic","survey"][weightKind.currentIndex],inner_folds:Number(inner.text),objective:"supervised",device:"cpu"}}
        if(purpose==="classification")result.positive_class=positive.currentValue||""
        else result.unit=unit.text
        return result
    }
    Connections { target:validation
        function onSelectFamily(purpose,method) {
            methodChoice.currentIndex=panel.methods.findIndex(m=>m.id===method)
            expanded.checked=true
        }
    }
    UiCheckBox { id:expanded;objectName:"familyExpanded";text:"Faz48 model ailelerini göster";Layout.fillWidth:true }
    ColumnLayout { visible:expanded.checked;Layout.fillWidth:true;spacing:Theme.sm
        UiLabel { text:"Model ailesini açıkça seç — baseline aynı validation planında";font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { text:"Mevcut modeller korunur. Burada seçtiğin aile CV skoruyla otomatik değiştirilmez; tek bir evrensel en iyi algoritma yoktur. Final test ayrı eylemdir. Preprocessing her eğitim katında; stacking iç OOF katlarında da yeniden öğrenilir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCombo { id:methodChoice;objectName:"familyMethod";accessibleLabel:"Model ailesi";model:panel.methods;textRole:"label";valueRole:"id";Layout.fillWidth:true;onActivated:validation.invalidate() }
        UiLabel { objectName:"familySupport";text:"Temsil: dense"+(panel.support.sparse?" / CSR":"; CSR kapalı")+" · Scaling: "+panel.support.scaling+"\nKategori: "+panel.support.categorical+" · NaN: "+panel.support.nan+"\nWeight: "+panel.support.weights+" · Imbalance: "+panel.support.imbalance+"\nProbability: "+panel.support.predict_proba+" · Model kaydı: "+panel.support.safe_persistence;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { visible:!panel.selected.enabled;text:panel.selected.reason||"";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { text:"Native categorical ailelerde eğitim vocab korunur; one-hot yapılmaz. Hist-gradient numeric/category eksikleri native işler. Diğer aileler seçili simple imputasyon ve eğitim one-hot/declared ordinal kullanır. Unknown kategori politikası sonuçta kayıtlıdır. Structured single target; calendar/TF-IDF/MI/indicator/selection ayrı mevcut yollarındadır. Multioutput ve GPU bu adapterde kapalı.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCombo { id:matrix;objectName:"familyMatrix";accessibleLabel:"Dense veya sparse temsil";model:["Dense","Sparse CSR — implicit densification yok"];Layout.fillWidth:true;onActivated:validation.invalidate() }
        UiCombo { id:scaling;objectName:"familyScaling";accessibleLabel:"Aile scaling seçimi";model:["Aile için otomatik training-only scaling","Scaling yok","Standard — training-only"];Layout.fillWidth:true;onActivated:validation.invalidate() }
        UiLabel { text:"Regularization alpha";visible:alpha.visible;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiTextField { id:alpha;objectName:"familyAlpha";visible:["elasticnet","lasso","sgd","multinomial_nb","voting","stacking"].indexOf(panel.method)>=0;Accessible.name:"Regularization alpha";text:"0.1";Layout.fillWidth:true;onTextEdited:validation.invalidate() }
        UiLabel { text:"ElasticNet L1 oranı";visible:ratio.visible;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiTextField { id:ratio;objectName:"familyL1Ratio";visible:["elasticnet","sgd","voting","stacking"].indexOf(panel.method)>=0;Accessible.name:"ElasticNet L1 oranı";text:"0.5";Layout.fillWidth:true;onTextEdited:validation.invalidate() }
        UiLabel { text:"SVM logistic C";visible:c.visible;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiTextField { id:c;objectName:"familyC";visible:panel.method==="svm"||(panel.purpose==="classification"&&["elasticnet","lasso","voting","stacking"].indexOf(panel.method)>=0);Accessible.name:"SVM logistic C";text:"1";Layout.fillWidth:true;onTextEdited:validation.invalidate() }
        UiLabel { text:"Ağaç veya boosting iterasyon sayısı";visible:trees.visible;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiTextField { id:trees;objectName:"familyTrees";visible:["extra_trees","gradient_boosting","hist_gradient","xgboost","lightgbm","catboost"].indexOf(panel.method)>=0;Accessible.name:"Ağaç veya boosting iterasyon sayısı";text:"25";Layout.fillWidth:true;onTextEdited:validation.invalidate() }
        UiLabel { text:"Maksimum ağaç derinliği";visible:depth.visible;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiTextField { id:depth;objectName:"familyDepth";visible:["decision_tree","extra_trees","gradient_boosting","hist_gradient","bagging","voting","stacking","xgboost","lightgbm","catboost"].indexOf(panel.method)>=0;Accessible.name:"Maksimum ağaç derinliği";text:"4";Layout.fillWidth:true;onTextEdited:validation.invalidate() }
        UiLabel { text:"Boosting öğrenme hızı";visible:rate.visible;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiTextField { id:rate;objectName:"familyLearningRate";visible:["gradient_boosting","hist_gradient","xgboost","lightgbm","catboost"].indexOf(panel.method)>=0;Accessible.name:"Boosting öğrenme hızı";text:"0.1";Layout.fillWidth:true;onTextEdited:validation.invalidate() }
        UiLabel { text:"KNN komşu sayısı";visible:neighbors.visible;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiTextField { id:neighbors;objectName:"familyNeighbors";visible:panel.method==="knn";Accessible.name:"KNN komşu sayısı";text:"5";Layout.fillWidth:true;onTextEdited:validation.invalidate() }
        UiLabel { text:"Convergence iterasyon bütçesi";visible:iterations.visible;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiTextField { id:iterations;objectName:"familyIterations";visible:["elasticnet","lasso","sgd","svm","voting","stacking"].indexOf(panel.method)>=0;Accessible.name:"Convergence iterasyon bütçesi";text:"5000";Layout.fillWidth:true;onTextEdited:validation.invalidate() }
        UiCombo { id:kernel;objectName:"familyKernel";visible:panel.method==="svm";accessibleLabel:"SVM kernel";model:["RBF — gamma scale","Linear"];Layout.fillWidth:true;onActivated:validation.invalidate() }
        UiCombo { id:balance;objectName:"familyBalance";accessibleLabel:"Imbalance eğitim politikası";visible:panel.purpose==="classification";model:["Yeniden ağırlıklandırma yok","Training-only balanced sample weights"];Layout.fillWidth:true;onActivated:validation.invalidate() }
        UiCombo { id:weight;objectName:"familyWeight";accessibleLabel:"Training sample weight sütunu";model:[{id:"",name:"Weight yok"}].concat(preparation.columns);textRole:"name";valueRole:"id";Layout.fillWidth:true;onActivated:validation.invalidate() }
        UiCombo { id:weightKind;objectName:"familyWeightKind";accessibleLabel:"Weight anlamı";model:["sample_weight — training loss","Frequency (bu adapterde kapalı)","Analytic (kapalı)","Survey (kapalı)"];Layout.fillWidth:true;onActivated:validation.invalidate() }
        UiLabel { text:"Training sample_weight yalnız model fit kaybına uygulanır; imputasyon/scaling ve rapor metrikleri unweighted. KNN/ensemble weight kapalı. SVM probability kalibrasyonu kapalı: predict_proba/eşik optimizasyonu sunulmaz. GaussianNB dense; MultinomialNB non-negative özellik ister.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { text:"Stacking iç OOF fold sayısı";visible:inner.visible;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiTextField { id:inner;objectName:"familyInnerFolds";Accessible.name:"Stacking iç OOF fold sayısı";text:"3";visible:panel.method==="stacking";Layout.fillWidth:true;onTextEdited:validation.invalidate() }
        UiLabel { visible:panel.method==="stacking";text:"Stacking: ElasticNet/logistic + decision tree, meta Ridge/logistic; iç OOF independent veya group. Time/group_time için random fallback yok. Bagging10 bootstrap tree; voting iki tam eğitim modelinin ortalamasıdır. OOF kayıt kimlikleri saklanır.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCombo { id:positive;objectName:"familyPositive";accessibleLabel:"İkili hedef pozitif sınıfı";visible:panel.purpose==="classification";model:(preparation.report.target||{}).class_distribution||[];textRole:"label";valueRole:"label";Layout.fillWidth:true;onActivated:validation.invalidate() }
        UiLabel { text:"Regresyon hedef birimi";visible:unit.visible;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiTextField { id:unit;objectName:"familyUnit";Accessible.name:"Regresyon hedef birimi";text:"hedef birimi";visible:panel.purpose==="regression";Layout.fillWidth:true;onTextEdited:validation.invalidate() }
        UiLabel { objectName:"familyCost";text:"CPU-only: "+(preparation.report.eligible_n||0)+" kaynak kaydı · family limit="+(panel.support.row_limit||0)+" · "+(Number(panel.protocol.folds||0)+1)+" outer fit/adayı + baseline. SVM/KNN n²; ensemble/stacking child ve iç fold maliyeti çarpılır. RAM/row/disk/wall/cancel worker sınırları uygulanır; süre garantisi yok.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiButton { objectName:"familyRun";text:"Seçili aile ve baseline eğit/değerlendir/kaydet";primary:true;multiline:true;Layout.fillWidth:true;enabled:validation.canRun&&!panel.protocolBlocked&&!!panel.selected.enabled;onClicked:validation.createFamily(JSON.stringify(panel.protocol),JSON.stringify(panel.config())) }
        UiButton { visible: false; objectName:"familyHelp";text:"Regularization, boosting, kernel ve ensemble öğren";helpContext:"model.families";onClicked:panel.helpRequested(this,"model.families") }
        UiLabel { objectName:"familyDiagnostics";text:JSON.stringify(validation.familyDiagnostics);Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { text:"Tahmin yolu: aşağıdaki mevcut Model kartı/yeni veri panelinde bu koşunun güvenli modelini seç. Unsupported save açıkça raporlanır; pickle/joblib import yok. Optional backend yokken compute başarılı sayılmaz. Ranking ayrı query-group/relevance şemasıdır; sıradan sınıf hedefi veya bu butonla çalışmaz.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    }
}
