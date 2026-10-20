import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"searchPanel"
    property var protocol
    property bool protocolBlocked:false
    property string helpContext:"model.search"
    signal helpRequested(var origin,string context)
    readonly property var active:modelSearch.historyReport
    readonly property var result:modelSearch.report
    readonly property var methods:modelSearch.methods
    function config(){return {method:method.currentValue||"random",space:JSON.parse(space.text),options:JSON.parse(options.text),trials:Number(trials.text),attempts:Number(attempts.text),inner_folds:Number(inner.text),seed:Number(seed.text),metric:metric.currentValue||"auto",constraints:JSON.parse(constraints.text),wall_seconds:Number(wall.text),ram_bytes:Number(ram.text)*1024*1024,concurrency:Number(concurrency.text),prune_after_folds:pruning.checked?1:0,prune_loss_above:Number(pruneThreshold.text),early_stopping:stopping.checked,patience:1,curves:curves.checked,calibration:false}}
    function run(resume){try{modelSearch.start(JSON.stringify(protocol),JSON.stringify(config()),resume||"")}catch(error){localError.text="Declarative JSON/number alanlarını kontrol edin: "+error}}
    Connections { target:modelSearch;function onSelectMethod(value){method.currentIndex=panel.methods.findIndex(m=>m.id===value);expanded.checked=true} }
    spacing:Theme.md
    UiCheckBox { id:expanded;objectName:"searchExpanded";text:"Faz49 bütçeli hyperparameter aramasını göster";Layout.fillWidth:true }
    ColumnLayout { visible:expanded.checked;Layout.fillWidth:true;spacing:Theme.sm
        UiLabel { text:"İç CV tuning · dış CV evaluation · final test ayrı";font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { text:"AutoML başlangıç önerisidir; optimum garantisi yok. Dış fold skoru trial seçmez. Grup/zaman/hedef ufku tüm inner folds, pruning ve resume yollarında korunur. Hazırlık/variance selection/bagging yeniden örnekleme yalnız eğitim katında fit edilir. İleri selection/indicator/MI/categorical native variance veya calibration desteklenmiyorsa reddedilir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        ColumnLayout { enabled:!modelSearch.busy;Layout.fillWidth:true
            UiCombo { id:method;objectName:"searchMethod";accessibleLabel:"Arama yöntemi";model:panel.methods;textRole:"label";valueRole:"id";currentIndex:1;Layout.fillWidth:true }
            UiLabel { visible:method.currentValue==="bayesian"&&!panel.methods[2].enabled;text:"Optional Optuna ortamı yok: Bayesian optimization compute doğrulanmadı; ağdan otomatik indirme yok.";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiLabel { text:"Discrete koşullu uzay — methods ve parameters; when.method/when.purpose. Serbest kod veya executable distribution yok.";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiTextArea { id:space;objectName:"searchSpace";Accessible.name:"Koşullu arama uzayı JSON";text:'{"methods":["decision_tree"],"parameters":[{"name":"depth","values":[2,4]}]}';Layout.fillWidth:true;Layout.preferredHeight:130 }
            UiLabel { text:"Sabit family options JSON — {} varsayılan. Örn. sample_weight/imbalance veya sparse/scaling seçimi; unsupported yöntem reddedilir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiTextArea { id:options;objectName:"searchOptions";Accessible.name:"Sabit model seçenekleri JSON";text:'{}';Layout.fillWidth:true;Layout.preferredHeight:75 }
            UiLabel { text:"Trial bütçesi / inner-CV scope (nested toplam maliyeti çarpılır)";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiTextField { id:trials;objectName:"searchTrials";Accessible.name:"Scope başına trial bütçesi";text:"2";Layout.fillWidth:true }
            UiLabel { text:"Toplam attempt bütçesi — canceled retry dahil; resume sıfırlamaz";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiTextField { id:attempts;objectName:"searchAttempts";Accessible.name:"Toplam trial attempt bütçesi";text:"60";Layout.fillWidth:true }
            UiLabel { text:"İç CV fold sayısı";Layout.fillWidth:true }
            UiTextField { id:inner;objectName:"searchInnerFolds";Accessible.name:"İç CV fold sayısı";text:"2";Layout.fillWidth:true }
            UiLabel { text:"Arama seed; model seed mevcut validation protokolünden";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiTextField { id:seed;objectName:"searchSeed";Accessible.name:"Arama seed";text:"49";Layout.fillWidth:true }
            UiCombo { id:metric;objectName:"searchMetric";accessibleLabel:"Primary metric";model:[{id:"auto",label:"Auto: MAE veya macro F1"},{id:"mae",label:"MAE — minimize"},{id:"rmse",label:"RMSE — minimize"},{id:"accuracy",label:"Accuracy — maximize"},{id:"f1_macro",label:"Macro F1 — maximize"}];textRole:"label";valueRole:"id";Layout.fillWidth:true }
            UiLabel { text:"Secondary constraints JSON: max_rmse (regression) veya min_accuracy (classification); eşik yoksa {}. Metric evaluation unweighted; sample_weight yalnız train loss.";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiTextField { id:constraints;objectName:"searchConstraints";Accessible.name:"İkincil metric constraints JSON";text:"{}";Layout.fillWidth:true }
            UiLabel { text:"Toplam arama süre bütçesi (saniye; resume ile sıfırlanmaz)";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiTextField { id:wall;objectName:"searchWall";Accessible.name:"Arama süre bütçesi saniye";text:"120";Layout.fillWidth:true }
            UiLabel { text:"RAM bütçesi MiB (birleşik ComputeBudget üst sınırı)";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiTextField { id:ram;objectName:"searchRam";Accessible.name:"Arama RAM MiB";text:"2048";Layout.fillWidth:true }
            UiLabel { text:"Concurrency — bu CPU adapterde yalnız 1";Layout.fillWidth:true }
            UiTextField { id:concurrency;objectName:"searchConcurrency";Accessible.name:"Trial concurrency";text:"1";Layout.fillWidth:true }
            UiCheckBox { id:pruning;objectName:"searchPruning";text:"İlk inner validation fold sonrası explicit loss threshold pruning";Layout.fillWidth:true }
            UiTextField { id:pruneThreshold;objectName:"searchPruneThreshold";Accessible.name:"Pruning loss üst eşiği";text:"1000000";visible:pruning.checked;Layout.fillWidth:true }
            UiLabel { visible:pruning.checked;text:"Loss = MAE/RMSE veya −accuracy/−F1. Eşik yalnız inner validation'a bakar; outer/final test pruning yönlendirmez.";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiCheckBox { id:stopping;objectName:"searchEarlyStopping";text:"Gradient boosting: ayrıca ayrılmış train-validation ile early stopping";Layout.fillWidth:true }
            UiCheckBox { id:curves;objectName:"searchCurves";text:"Öneri sonrası learning ve controlled validation curves (ek fit maliyeti)";checked:true;Layout.fillWidth:true }
            UiLabel { objectName:"searchCost";text:"Üst scope trial sayısı="+Number(trials.text)*(Number(panel.protocol.folds||0)+1)+" · inner fitler + dış evaluation + curves. Stacking her inner train'de kendi OOF katlarını ekler. 1000satır/32özellik/600nativefit üst sınırı; concurrency1. Kesin joint fold/fit bütçesi işin preflight adımında denetlenir. Calibration arama içinde kapalı; ayrı calibration bölmesi gerekir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiButton { objectName:"searchRun";text:"Bounded nested aramayı başlat";primary:true;multiline:true;Layout.fillWidth:true;enabled:modelSearch.canRun&&!panel.protocolBlocked&&!!(panel.methods[method.currentIndex]||{}).enabled;onClicked:panel.run("") }
        }
        UiLabel { id:localError;text:"";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiButton { objectName:"searchCancel";visible:modelSearch.busy;text:"Aramayı iptal et — kayıtlı sonuç korunur";multiline:true;Layout.fillWidth:true;onClicked:modelSearch.cancel() }
        StateNotice { Layout.fillWidth:true;kind:modelSearch.errorText?"error":modelSearch.busy?"loading":"info";heading:"Arama durumu";detail:modelSearch.errorText||modelSearch.message+(panel.active.reason?" · "+panel.active.reason:"") }
        UiLabel { objectName:"searchHistory";text:panel.active.status?"Durum="+panel.active.status+" · elapsed="+Number(panel.active.elapsed_seconds||0).toFixed(2)+"s · "+JSON.stringify(panel.active.trial_counts)+" · native fit üst maliyet sayacı="+panel.active.native_fit_reservations+"/600"+"\nÖnceki final test kayıtları="+panel.active.prior_test_count+" · "+panel.active.interpretation:"Trial geçmişi henüz yok";Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:panel.active.trials||[];UiLabel { required property var modelData;text:modelData.scope+" · "+modelData.method+" · "+JSON.stringify(modelData.parameters)+" · "+modelData.status+" · inner folds="+modelData.folds_done+" · "+JSON.stringify(modelData.metrics)+(modelData.reason?" · "+modelData.reason:"");Layout.fillWidth:true;wrapMode:Text.Wrap } }
        UiLabel { text:"Nested dış evaluation: arama prosedürünün sınırlandırılmış tahmini; trial seçimi bu skorlara bakmadı.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:panel.result.outer||[];UiLabel { required property var modelData;text:modelData.scope+" · train="+modelData.fit_n+" · evaluation="+modelData.evaluation_n+" · "+JSON.stringify(modelData.metrics);Layout.fillWidth:true;wrapMode:Text.Wrap } }
        SearchCurve { objectName:"searchLearningCurve";points:(panel.result.curves||[]).filter(p=>p.kind==="learning").map(p=>({x:p.x,y:p.value}));title:"Learning curve — development inner validation";xLabel:"Train oranı";yLabel:((panel.result.curves||[])[0]||{}).metric||"Metric";Layout.fillWidth:true;Layout.preferredHeight:220 }
        SearchCurve { objectName:"searchValidationCurve";points:(panel.result.curves||[]).filter(p=>p.kind==="validation"&&typeof p.x==="number").map(p=>({x:p.x,y:p.value}));title:"Controlled validation curve — diğer parametreler sabit";xLabel:"Parametre değeri";yLabel:((panel.result.curves||[])[0]||{}).metric||"Metric";Layout.fillWidth:true;Layout.preferredHeight:220 }
        Repeater { model:panel.result.curves||[];UiLabel { required property var modelData;text:modelData.kind+" · "+modelData.parameter+"="+modelData.x+" · "+modelData.metric+"="+(typeof modelData.value==="number"?modelData.value.toFixed(6):"tanımsız")+" · train n="+JSON.stringify(modelData.training_n)+" · "+modelData.scope;Layout.fillWidth:true;wrapMode:Text.Wrap } }
        UiLabel { text:"Eğriler inner validation'a tekrar bakar; yeni bağımsız performans veya final test skoru değildir. Kategorik curve değerleri tabloda kalır; yapay sürekli eksen yok.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCombo { id:saved;objectName:"searchSaved";accessibleLabel:"Kayıtlı arama checkpoint";model:modelSearch.savedSearches;textRole:"label";valueRole:"id";Layout.fillWidth:true }
        UiButton { objectName:"searchOpen";text:"Kayıtlı arama geçmişini aç (ağ/fit yok)";Layout.fillWidth:true;enabled:!modelSearch.busy;onClicked:modelSearch.openSearch(saved.currentValue||"") }
        UiButton { objectName:"searchResume";text:"Aynı tarif/seed/source/environment ile resume";multiline:true;Layout.fillWidth:true;enabled:modelSearch.canRun;onClicked:panel.run(saved.currentValue||"") }
        UiCombo { id:positive;objectName:"searchPositive";accessibleLabel:"Öneri sonrası sınıflandırma pozitif sınıf";model:(preparation.report.target||{}).class_distribution||[];textRole:"label";valueRole:"label";Layout.fillWidth:true;visible:(preparation.report.spec||{}).purpose==="classification" }
        UiButton { objectName:"searchApply";text:"Öneriyi mevcut model yolunda eğit/değerlendir/kaydet";multiline:true;Layout.fillWidth:true;enabled:!modelSearch.busy&&validation.canRun&&panel.result.status==="completed";onClicked:modelSearch.applyRecommendation(JSON.stringify(panel.protocol),positive.currentValue||"") }
        UiLabel { text:"Bu ayrı eylem mevcut model pipeline'ını kullanır; CV skoru tuning sonrası keşifseldir. Yeni arama final test kullanım geçmişini sıfırlamaz. Final test yalnız aşağıdaki mevcut onaylı defter yolundan açılır; eski model korunur.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiTextField { id:exportPath;objectName:"searchExportPath";Accessible.name:"Trial history safe JSON export yeni mutlak yol";placeholderText:"/tam/yol/search-history.json";Layout.fillWidth:true }
        UiButton { objectName:"searchExport";text:"Trial history safe JSON export — mevcut dosya değişmez";multiline:true;Layout.fillWidth:true;enabled:!modelSearch.busy&&!!panel.active.status;onClicked:modelSearch.exportHistory(exportPath.text) }
        UiButton { objectName:"searchHelp";text:"Hyperparameter, nested CV, trial ve budget öğren";helpContext:"model.search";onClicked:panel.helpRequested(this,helpContext) }
    }
}
