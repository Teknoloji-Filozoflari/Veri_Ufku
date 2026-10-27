import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"explanationPanel"
    property string helpContext:"model.explanation"
    signal helpRequested(var origin,string context)
    readonly property var methods:lifecycle.explanationMethods()
    readonly property var result:lifecycle.explanationReport
    readonly property var features:lifecycle.card.features||[]
    function shown(value){return typeof value === "number" && isFinite(value)?Number(value.toPrecision(6)).toString():"tanımsız"}
    function featureName(id){let f=((panel.result.card||{}).features||[]).find(f=>f.id===id);return f?f.name+(f.unit?" · "+f.unit:""):"Original feature"}
    function defaults(){let r=lifecycle.card;let ids=features.map(f=>f.id);feature.currentIndex=0;changes.text="{}";constraints.text="{}";immutable.text="[]";slices.text="[]";sensitive.text="[]";let d=dataView.datasets;for(let i=0;i<d.length;i++)if(d[i].version===r.dataset_version)background.currentIndex=i}
    function config(){return {method:method.currentValue||"permutation",features:method.currentValue==="pdp"||method.currentValue==="ice"?[feature.currentValue||""]:[],class_label:label.currentText||"",sample_rows:Number(sample.text),background_rows:Number(bgN.text),seed:Number(seed.text),repeats:Number(repeats.text),grid_points:Number(gridN.text),grid:JSON.parse(grid.text),local_row_id:rowId.text,slices:JSON.parse(slices.text),sensitive_columns:JSON.parse(sensitive.text),positive_class:positive.currentText||"",changes:JSON.parse(changes.text),constraints:JSON.parse(constraints.text),immutable_features:JSON.parse(immutable.text),desired_class:desiredClass.currentText||"",desired_min:desiredMin.text.trim()?Number(desiredMin.text):null,desired_max:desiredMax.text.trim()?Number(desiredMax.text):null,bootstrap_draws:100}}
    Connections { target:lifecycle;function onSelectExplanation(value){expanded.checked=true;method.currentIndex=panel.methods.findIndex(m=>m.id===value)} }
    property string modelRun:""
    Connections { target:lifecycle;function onLifecycleChanged(){if(panel.modelRun!==(lifecycle.card.run_id||"")){panel.modelRun=lifecycle.card.run_id||"";panel.defaults()}} }
    spacing:Theme.sm
    UiCheckBox { id:expanded;objectName:"explanationExpanded";text:"Faz51 model açıklaması, hata dilimleri ve senaryolar";Layout.fillWidth:true }
    ColumnLayout { visible:expanded.checked;Layout.fillWidth:true;spacing:Theme.sm
        UiLabel { text:"Global/local açıklama · validation only · final test burada açılmaz";font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { text:"Önce yukarıdan kayıtlı development modelini açın. Evaluation modelin immutable source validation bölümü; background aynı datasetin model fit RowIds bölümünden seçilir. Başka kaynak/background ve final refitted model bu bounded adapterde kapalı. Açıklama sample500/background100/source5000/16feature; training fit yok.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        ColumnLayout { enabled:!lifecycle.busy&&!projects.busy;Layout.fillWidth:true;spacing:Theme.sm
            UiCombo { id:method;objectName:"explanationMethod";accessibleLabel:"Model açıklama yöntemi";model:panel.methods;textRole:"label";valueRole:"id";Layout.fillWidth:true }
            UiLabel { text:(panel.methods[method.currentIndex]||{}).reason||"";visible:!!text;color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiLabel { text:"Explicit background dataset — bu sürümde yalnız modelin training source snapshot'ı desteklenir";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiCombo { id:background;objectName:"explanationBackground";accessibleLabel:"Explanation background dataset";model:dataView.datasets;textRole:"label";valueRole:"version";Layout.fillWidth:true }
            UiCombo { id:feature;objectName:"explanationFeature";accessibleLabel:"PDP ICE özgün özellik";model:panel.features;textRole:"name";valueRole:"id";Layout.fillWidth:true }
            UiCombo { id:label;objectName:"explanationClass";accessibleLabel:"Probability response sınıfı";model:lifecycle.card.label_order||[];Layout.fillWidth:true }
            UiLabel { text:"Evaluation sample n / background n / seed / permutation repeat / PDP grid n";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiTextField { id:sample;objectName:"explanationSample";Accessible.name:"Explanation sample kayıt bütçesi";text:"100";Layout.fillWidth:true }
            UiTextField { id:bgN;objectName:"explanationBackgroundN";Accessible.name:"Background kayıt bütçesi";text:"40";Layout.fillWidth:true }
            UiTextField { id:seed;objectName:"explanationSeed";Accessible.name:"Explanation seed";text:"51";Layout.fillWidth:true }
            UiTextField { id:repeats;objectName:"explanationRepeats";Accessible.name:"Permutation repeat sayısı";text:"3";Layout.fillWidth:true }
            UiTextField { id:gridN;objectName:"explanationGridN";Accessible.name:"PDP ICE grid nokta sayısı";text:"8";Layout.fillWidth:true }
            UiTextField { id:grid;objectName:"explanationGrid";Accessible.name:"Explicit PDP grid JSON";text:"[]";Layout.fillWidth:true }
            UiLabel { text:"Local RowId (local-linear/what-if/constrained): kayıtlı validation üyeliklerinden açık seçin. Exact local-linear yalnız linear/Ridge regression; SHAP optional ortam yoksa hesap kapalı. Family/ensemble local-linear desteklenmez.";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiCombo { id:localRows;objectName:"explanationRowChoice";accessibleLabel:"Local validation RowId seçimi";model:lifecycle.explanationRows;Layout.fillWidth:true;onActivated:rowId.text=currentText }
            UiTextField { id:rowId;objectName:"explanationRowId";Accessible.name:"Local explanation RowId";text:"";Layout.fillWidth:true }
            UiLabel { text:"Dilimler JSON: [{column_id:ColumnId,kind:group|class|range|time,edges:[...]}]. Time sınırları UTC epoch saniye; Date/Datetime kolon gerekir. Range son sınır kapalı; outside/missing ayrı. Boş [] amaç için hedef dilimi.";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiTextArea { id:slices;objectName:"explanationSlices";Accessible.name:"Error slice declarative JSON";text:"[]";Layout.fillWidth:true;Layout.preferredHeight:80 }
            UiLabel { text:"Korunan/hassas ColumnIds JSON — kullanıcı açıkça seçer. Otomatik sensitive inference yok. Fairness yalnız binary classification; çok sınıflı fairness burada desteklenmiyor. Export hassas etiket/değer/kimlik/yerel katkıları maskeler; n<30 hücreler dışa aktarılmaz.";Layout.fillWidth:true;wrapMode:Text.Wrap;color:Theme.warning }
            UiCombo { id:sensitiveChoice;objectName:"explanationSensitiveChoice";accessibleLabel:"Sensitive kaynak kolonunu açık seç";model:lifecycle.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true }
            UiButton { objectName:"explanationAddSensitive";text:"Seçili kolonu sensitive listesine ekle";Layout.fillWidth:true;onClicked:{try{let ids=JSON.parse(sensitive.text);let id=sensitiveChoice.currentValue;if(id&&ids.indexOf(id)<0)ids.push(id);sensitive.text=JSON.stringify(ids)}catch(e){localError.text="Sensitive listesi JSON olmalı"}} }
            UiTextField { id:sensitive;objectName:"explanationSensitive";Accessible.name:"Explicit sensitive ColumnIds JSON";text:"[]";Layout.fillWidth:true }
            UiCombo { id:positive;objectName:"explanationPositive";accessibleLabel:"Fairness pozitif sınıf";model:lifecycle.card.label_order||[];Layout.fillWidth:true }
            UiLabel { text:"What-if changes JSON {ColumnId:value}; ham model senaryosudur, causal counterfactual değil. Kısıtlı arama: tüm özellikler immutable veya constraint olmalı. Immutable [] boş olamaz; finite100aday üst sınırı.";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiTextField { id:changes;objectName:"explanationChanges";Accessible.name:"What if changes JSON";text:"{}";Layout.fillWidth:true }
            UiTextField { id:immutable;objectName:"explanationImmutable";Accessible.name:"Explicit immutable feature ColumnIds JSON";text:"[]";Layout.fillWidth:true }
            UiTextArea { id:constraints;objectName:"explanationConstraints";Accessible.name:"Constrained candidate domains JSON";text:"{}";Layout.fillWidth:true;Layout.preferredHeight:80 }
            UiLabel { text:"Constraint {ColumnId:{values:[...],direction:any|increase|decrease,cost:positive}}. Numeric domain background range içinde; categorical observed values/direction any. Desired class veya numeric min/max seçin; koşulların gerçek hayatta yapılabilirliğini kanıtlamaz.";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiCombo { id:desiredClass;objectName:"explanationDesiredClass";accessibleLabel:"Candidate desired class";model:lifecycle.card.label_order||[];Layout.fillWidth:true }
            UiTextField { id:desiredMin;objectName:"explanationDesiredMin";Accessible.name:"Candidate desired minimum numeric target";text:"";Layout.fillWidth:true }
            UiTextField { id:desiredMax;objectName:"explanationDesiredMax";Accessible.name:"Candidate desired maximum numeric target";text:"";Layout.fillWidth:true }
            UiButton { objectName:"explanationRun";text:"Açıklamayı/senaryoyu hesapla ve projeye atomik kaydet";primary:true;multiline:true;Layout.fillWidth:true;enabled:lifecycle.explanationHasModel&&!lifecycle.busy&&!projects.busy&&!!(panel.methods[method.currentIndex]||{}).enabled;onClicked:{try{lifecycle.explain(JSON.stringify(panel.config()),background.currentValue||"")}catch(e){localError.text="JSON/sayı alanını kontrol edin: "+e}} }
        }
        UiLabel { id:localError;text:"";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiButton { objectName:"explanationCancel";text:"Açıklamayı iptal et";visible:lifecycle.busy;onClicked:lifecycle.cancel() }
        UiLabel { text:"Kayıtlı açıklama kendi frozen kaynak/modeline aittir; form değişikliği onu yeniden hesaplamaz. Şu an açık modelle karşılaştırırken model/snapshot kimliklerini kontrol edin.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { objectName:"explanationScope";text:panel.result.provenance?panel.result.provenance.scope+"\nSample="+panel.result.provenance.n+"/"+panel.result.provenance.eligible_n+" · "+(panel.result.provenance.sampled?"SAMPLED":"tam validation")+" · background="+panel.result.provenance.background_n+"/"+panel.result.provenance.background_eligible_n+" · seed="+panel.result.provenance.seed+"\nPrediction row-pass="+panel.result.provenance.prediction_row_passes+"/"+panel.result.provenance.prediction_row_pass_budget+" · fit calls="+panel.result.provenance.fit_calls:"Henüz açıklama sonucu yok";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { text:panel.result.limitations||"Açıklama/SHAP neden-sonuç değildir. Correlated features/extrapolation/missing/background ve approximation sınırlarını öğren. Tek metrikle adil model rozeti yok.";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:(panel.result.permutation||{}).values||[];UiLabel { required property var modelData;text:modelData.name+" · importance="+modelData.mean.toFixed(6)+" · shuffle std="+modelData.std.toFixed(6);Layout.fillWidth:true;wrapMode:Text.Wrap } }
        SearchCurve { visible:!!panel.result.pdp&&panel.result.pdp.numeric_axis;points:panel.result.pdp?panel.result.pdp.grid.map((v,i)=>({x:v,y:panel.result.pdp.mean[i]})):[];title:"PDP · "+panel.featureName((panel.result.pdp||{}).column_id)+" · n="+((panel.result.pdp||{}).n||0);xLabel:panel.featureName((panel.result.pdp||{}).column_id);yLabel:(panel.result.card||{}).purpose==="classification"?"p("+((panel.result.spec||{}).class_label||"")+")":"Model prediction";Layout.fillWidth:true;Layout.preferredHeight:230 }
        UiLabel { objectName:"explanationPDP";text:panel.result.pdp?"Grid: "+panel.result.pdp.grid.join(", ")+"\nMean response: "+panel.result.pdp.mean.map(v=>panel.shown(v)).join(", ")+"\n"+panel.result.pdp.grid_method+" · background aralığı dışında grid n="+panel.result.pdp.outside_background_grid_n:"";Layout.fillWidth:true;wrapMode:Text.Wrap }
        ICEPlot { visible:!!panel.result.pdp&&panel.result.pdp.numeric_axis&&(panel.result.ice||[]).length>0;grid:(panel.result.pdp||{}).grid||[];lines:(panel.result.ice||[]).slice(0,10);mean:(panel.result.pdp||{}).mean||[];Layout.fillWidth:true;Layout.preferredHeight:240 }
        Repeater { model:(panel.result.ice||[]).slice(0,10);UiLabel { required property var modelData;text:"ICE · "+modelData.row_id+" · "+modelData.values.map(v=>v.toFixed(4)).join(", ");Layout.fillWidth:true;wrapMode:Text.Wrap } }
        UiLabel { objectName:"explanationLocal";text:panel.result.local?"Exact local additive · baseline="+panel.result.local.baseline+" · prediction="+panel.result.local.prediction+" · identity error="+panel.result.local.identity_error+"\n"+JSON.stringify(panel.result.local.contributions):"";Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:panel.result.slices||[];UiLabel { required property var modelData;text:modelData.kind+" · "+JSON.stringify(modelData.label)+" · n="+modelData.n+" · "+modelData.metric+"="+(typeof modelData.value==="number"?modelData.value.toFixed(4):"tanımsız")+" · "+(modelData.small_group?"küçük grup: güvenilmez":"")+"\n"+JSON.stringify(modelData.uncertainty||{})+" · "+modelData.uncertainty_status;Layout.fillWidth:true;wrapMode:Text.Wrap } }
        UiLabel { objectName:"explanationFairness";text:panel.result.fairness?panel.result.fairness.trade_off+"\n"+JSON.stringify(panel.result.fairness.disparities):"";Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:(panel.result.fairness||{}).groups||[];UiLabel { required property var modelData;text:"Sensitive group "+(modelData.label===undefined||modelData.label===null?"Eksik":modelData.label)+" · n="+modelData.n+" · selection="+panel.shown(modelData.selection_rate)+" · TPR="+panel.shown(modelData.tpr)+" · FPR="+panel.shown(modelData.fpr)+" · precision="+panel.shown(modelData.precision)+" · base rate="+panel.shown(modelData.base_rate)+" · "+(modelData.small_group?"küçük grup: güvenilmez":"")+"\n"+JSON.stringify(modelData.intervals);Layout.fillWidth:true;wrapMode:Text.Wrap } }
        UiLabel { text:panel.result.shap?JSON.stringify({global:panel.result.shap.global_values,local:panel.result.shap.local,approximation:panel.result.shap.approximation}):"";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { objectName:"explanationScenario";text:JSON.stringify(panel.result.what_if||panel.result.constrained||{});Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCheckBox { id:technical;text:"Mapping, diagnostics ve kayıt kimliklerini göster";Layout.fillWidth:true }
        UiLabel { objectName:"explanationMapping";visible:technical.checked;text:JSON.stringify({mapping:panel.result.feature_mapping||[],diagnostics:panel.result.diagnostics||{},provenance:panel.result.provenance||{}},null,2);Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCombo { id:saved;objectName:"explanationSaved";accessibleLabel:"Saved explanation";model:lifecycle.savedExplanations;textRole:"label";valueRole:"id";Layout.fillWidth:true }
        UiButton { objectName:"explanationOpen";text:"Kayıtlı açıklamayı aç — fit/ağ yok";enabled:!lifecycle.busy&&!projects.busy&&saved.currentIndex>=0;Layout.fillWidth:true;onClicked:lifecycle.openExplanation(saved.currentValue||"") }
        UiTextField { id:output;objectName:"explanationExportPath";Accessible.name:"Masked explanation JSON export yeni mutlak dosya yolu";text:"";Layout.fillWidth:true }
        UiButton { objectName:"explanationExport";text:"Maskeli safe JSON export — hassas alanlar/kimlikler çıkmaz";multiline:true;enabled:!!panel.result.schema&&!lifecycle.busy&&!projects.busy;Layout.fillWidth:true;onClicked:lifecycle.exportExplanation(output.text) }
        UiButton { visible: false; objectName:"explanationHelp";text:"Explanation/causation, correlated feature, subgroup ve fairness öğren";helpContext:"model.explanation";Layout.fillWidth:true;onClicked:panel.helpRequested(this,helpContext) }
    }
}
