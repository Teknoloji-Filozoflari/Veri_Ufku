import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "missingSamplingPanel"
    property string helpContext: "missing.assumptions"
    signal helpRequested(var origin, string context)
    readonly property string methodId: method.currentValue || "missing_patterns"
    readonly property bool mi: methodId.indexOf("mi_")===0
    readonly property bool sample: methodId.indexOf("sample_")===0
    readonly property bool weighted: methodId.indexOf("weighted_")===0 || methodId==="survey_mean"
    readonly property bool survey: methodId==="survey_mean"
    readonly property bool featuresUsed: mi || methodId==="missing_patterns" || methodId==="missing_indicators" || methodId==="weighted_ols" || methodId==="weighted_fit"
    property var chosenFeatures: []
    spacing: Theme.sm
    function key(p) { return p.currentIndex>=0 ? p.currentValue : "" }
    function spec() {
        return {path:"advanced",method:methodId,x:key(x),features:featuresUsed?chosenFeatures:[],group:methodId==="sample_stratified"||methodId==="sample_cluster"?key(group):"",weight_type:weighted?["none","frequency","analytic","survey","sample_weight"][weightType.currentIndex]:"none",weight:weighted?key(weight):"",strata:survey?key(strata):"",psu:survey?key(psu):"",seed:seed.value,sample_size:size.value,imputations:imputations.value,iterations:iterations.value,deltas:deltas.text.split(",").map(v=>Number(v.trim())),missing_assumption:["MCAR","MAR","MNAR"][assumption.currentIndex],question:question.text,hypothesis:hypothesis.text,unit:unit.text,observation_unit:observation.text,independent:design.checked,measurement_confirmed:measurement.checked,assumptions_confirmed:approval.checked,scope:scope.currentIndex===0?"full":"view",precision:approximate.checked?"approximate":"reject",confidence:[.95,.90,.99][confidence.currentIndex]}
    }
    function select(name) {
        for(let i=0;i<method.model.length;i++) if(method.model[i].id===name)method.currentIndex=i
        approval.checked=false
    }
    function restore(s) {
        if(!s||s.path!=="advanced")return
        select(s.method)
        let picks=[x,group,weight,strata,psu], keys=[s.x,s.group,s.weight,s.strata,s.psu]
        for(let j=0;j<picks.length;j++)for(let i=0;i<picks[j].model.length;i++)if(picks[j].model[i].id===keys[j])picks[j].currentIndex=i
        chosenFeatures=s.features||[];question.text=s.question;hypothesis.text=s.hypothesis;unit.text=s.unit;observation.text=s.observation_unit
        weightType.currentIndex=["none","frequency","analytic","survey","sample_weight"].indexOf(s.weight_type)
        seed.value=s.seed;size.value=s.sample_size;imputations.value=s.imputations;iterations.value=s.iterations;deltas.text=(s.deltas||[]).join(",")
        assumption.currentIndex=["MCAR","MAR","MNAR"].indexOf(s.missing_assumption);scope.currentIndex=s.scope==="full"?0:1;approximate.checked=s.precision==="approximate";design.checked=s.independent;measurement.checked=s.measurement_confirmed;approval.checked=false
    }
    UiLabel { text:"Eksik veri, örnekleme ve ağırlıklar";font.bold:true;Layout.fillWidth:true }
    UiLabel { text:"MCAR: rastgele cihaz kaybı. MAR: kayıtlı yaşa göre yanıt eksikliği. MNAR: bilinmeyen yüksek geliri bildirmeme. Gözlenen veriden mekanizma kesin tespit edilmez. Kaynak veri değişmez; çıktılar ayrı kayıtlı sonuçlardır.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCombo { id:method;objectName:"missingMethod";accessibleLabel:"Eksiklik / örnekleme / ağırlık yöntemi";model:statistics.methods("advanced");textRole:"label";valueRole:"id";Layout.fillWidth:true;onActivated:{statistics.invalidate();approval.checked=false} }
    UiTextField { id:question;objectName:"missingQuestion";Accessible.name:"Araştırma sorusu";placeholderText:"Araştırma sorusu";maximumLength:1000;Layout.fillWidth:true;onTextEdited:statistics.invalidate() }
    UiTextField { id:hypothesis;objectName:"missingHypothesis";Accessible.name:"Varsayım ve tasarım açıklaması";placeholderText:"Varsayım / tasarım / analiz bağlamı";maximumLength:1000;Layout.fillWidth:true;onTextEdited:statistics.invalidate() }
    UiCombo { id:x;objectName:"missingX";accessibleLabel:"Ölçüm veya desen için ilk alan";model:statistics.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true;onActivated:statistics.invalidate() }
    UiLabel { visible:featuresUsed;text:mi?"Yardımcı sayısal özellikler (MI ortalama) veya OLS açıklayıcıları; ölçümden farklı seçin":"Ek desen/gösterge alanları veya doğrusal model özellikleri";Layout.fillWidth:true;wrapMode:Text.Wrap }
    Flow {
        visible:featuresUsed;Layout.fillWidth:true;spacing:Theme.sm
        Repeater { model:statistics.columns
            UiCheckBox { required property var modelData; objectName:"missingFeature_"+modelData.name;text:modelData.name;checked:panel.chosenFeatures.indexOf(modelData.id)>=0;onClicked:{let a=panel.chosenFeatures.slice();if(checked)a.push(modelData.id);else a=a.filter(v=>v!==modelData.id);panel.chosenFeatures=a;statistics.invalidate()} }
        }
    }
    UiCombo { id:group;objectName:"missingGroup";visible:methodId==="sample_stratified"||methodId==="sample_cluster";accessibleLabel:"Strata veya cluster grubu";model:statistics.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true;onActivated:statistics.invalidate() }
    UiLabel { visible:sample;text:"Yerine koymadan seçim. Basit rastgelede satır adedi; stratified'da her stratadan adet; cluster'da küme adedi. Seçili RowId ve SourceRecordId ile dahil edilme olasılıkları saklanır. Temsil garantisi değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiSpinBox { id:size;objectName:"missingSampleSize";visible:sample;from:1;to:10000;value:10;Accessible.name:"Satır / strata başına adet / küme sayısı";onValueModified:statistics.invalidate() }
    UiCombo { id:weightType;objectName:"missingWeightType";visible:weighted;accessibleLabel:"Ağırlık türü — açık seçim";model:["Tür seç (gerekli)","Frekans — tamsayı tekrar sayısı","Analitik — göreli ters varyans","Survey — dahil edilme olasılığının tersi","sample_weight — kayıp katkısı"];Layout.fillWidth:true;onActivated:statistics.invalidate() }
    UiCombo { id:weight;objectName:"missingWeight";visible:weighted;accessibleLabel:"Ağırlık sütunu";model:statistics.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true;onActivated:statistics.invalidate() }
    UiCombo { id:strata;objectName:"missingStrata";visible:survey;accessibleLabel:"Survey strata";model:statistics.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true;onActivated:statistics.invalidate() }
    UiCombo { id:psu;objectName:"missingPsu";visible:survey;accessibleLabel:"Survey PSU";model:statistics.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true;onActivated:statistics.invalidate() }
    UiLabel { visible:survey;text:"Her stratada en az2 bağımsız PSU; PSU kimliği strata içinde yorumlanır. WR ultimate-cluster Taylor SE ve t CI. FPC, kalibrasyon, replicate weights ve filtreli domain çıkarımı desteklenmez.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { visible:weighted;text:"Negatif/eksik ağırlık reddedilir. Analitik/survey kesin pozitif ister. Frekans/sample_weight sıfır katkı kabul eder. Registry seçili yöntemin tür desteğini doğrular; türler birbirine çevrilmez.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCombo { id:assumption;objectName:"missingAssumption";visible:mi;accessibleLabel:"Eksiklik varsayımı";model:["MCAR varsayımı","MAR varsayımı","MNAR duyarlılık varsayımı"];currentIndex:1;Layout.fillWidth:true;onActivated:statistics.invalidate() }
    RowLayout {
        visible:mi;Layout.fillWidth:true
        UiSpinBox { id:imputations;objectName:"missingImputations";from:2;to:20;value:5;Accessible.name:"MI realizasyon sayısı";onValueModified:statistics.invalidate() }
        UiSpinBox { id:iterations;objectName:"missingIterations";from:1;to:30;value:10;Accessible.name:"Posterior iterative iterasyon";onValueModified:statistics.invalidate() }
    }
    UiTextField { id:deltas;objectName:"missingDeltas";visible:mi;text:"-1,0,1";Accessible.name:"MNAR duyarlılık deltaları — ölçüm biriminde";maximumLength:100;Layout.fillWidth:true;onTextEdited:statistics.invalidate() }
    UiLabel { visible:mi;text:"MI ayrı sayısal posterior realizasyonları saklar; yalnız ortalama/OLS katsayı ve kovaryansları Rubin/Barnard–Rubin ile havuzlanır. Delta yalnız özgün eksik ölçüm hücrelerine, aynı posterior çekilişlerle uygulanır. Yöntem MAR çalışma modeli kullanır; MNAR seçimi deltayla duyarlılık analizidir. Gaussian varsayım, yakınsama ve yardımcı özellikleri inceleyin. Bu yol predictive CV değildir; KNN/tek iterative doldurma Model hazırlığında fold içinde uygulanır.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiSpinBox { id:seed;objectName:"missingSeed";from:0;to:2147483647;value:42;Accessible.name:"Örnekleme / MI seed";onValueModified:statistics.invalidate() }
    UiTextField { id:unit;objectName:"missingUnit";Accessible.name:"Ölçüm ve delta birimi";placeholderText:"Ölçüm birimi (kg / TL / birimsiz)";maximumLength:1000;Layout.fillWidth:true;onTextEdited:statistics.invalidate() }
    UiTextField { id:observation;objectName:"missingObservation";Accessible.name:"Gözlem birimi";placeholderText:"Gözlem birimi / bağımsız PSU";maximumLength:1000;Layout.fillWidth:true;onTextEdited:statistics.invalidate() }
    UiCombo { id:scope;objectName:"missingScope";accessibleLabel:"Hesap kapsamı";model:["Tam dataset","Mevcut filtre — survey domain çıkarımı desteklenmez"];Layout.fillWidth:true;onActivated:statistics.invalidate() }
    UiCombo { id:confidence;objectName:"missingConfidence";accessibleLabel:"Güven düzeyi";model:["%95 güven","%90 güven","%99 güven"];Layout.fillWidth:true;onActivated:statistics.invalidate() }
    UiCheckBox { id:approximate;objectName:"missingApproximate";text:"Float64 yaklaşık hesap kaybına açık izin ver";Layout.fillWidth:true;onClicked:statistics.invalidate() }
    UiCheckBox { id:measurement;objectName:"missingMeasurement";text:"Ölçüm rollerini ve birimleri inceledim";Layout.fillWidth:true;onClicked:statistics.invalidate() }
    UiCheckBox { id:design;objectName:"missingDesign";text:"Bağımsızlık / örnekleme / PSU tasarımını inceledim";Layout.fillWidth:true;onClicked:statistics.invalidate() }
    Flow { Layout.fillWidth:true;spacing:Theme.sm
        UiButton { objectName:"missingPreflight";text:"Önkontrolü çalıştır";enabled:!statistics.busy&&!projects.busy;onClicked:{approval.checked=false;statistics.create(JSON.stringify(panel.spec()),true)} }
        UiButton { text:"Eksiklik varsayımlarını öğren";objectName:"missingHelpAssumptions";helpContext:"missing.assumptions";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { text:"Temsil ve örnekleme";objectName:"missingHelpRepresentation";helpContext:"sampling.representation";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { text:"Örneklem yanlılığı";objectName:"missingHelpBias";helpContext:"sampling.bias";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { text:"Ağırlık türleri";objectName:"missingHelpWeights";helpContext:"weights.types";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { text:"Çoklu imputasyon";objectName:"missingHelpMultiple";helpContext:"missing.multiple";onClicked:panel.helpRequested(this,helpContext) }
    }
    StateNotice { Layout.fillWidth:true;heading:"İleri hesap durumu";kind:statistics.errorText?"error":statistics.busy?"loading":"info";detail:statistics.errorText||statistics.message }
    Repeater { model:statistics.preflightCurrent?(statistics.preflightResult.warnings||[]):[];UiLabel { required property string modelData;text:modelData;wrapMode:Text.Wrap;Layout.fillWidth:true;color:Theme.warning } }
    UiCheckBox { id:approval;objectName:"missingApproval";text:"Önkontrolü, yöntemin destek sınırlarını ve varsayımları inceledim";Layout.fillWidth:true }
    RowLayout {
        Layout.fillWidth:true
        UiButton { objectName:"missingRun";text:"Hesapla";enabled:statistics.preflightCurrent&&approval.checked&&!statistics.busy&&!projects.busy;onClicked:statistics.create(JSON.stringify(panel.spec()),false) }
        UiButton { objectName:"missingCancel";text:"İptal";enabled:statistics.busy;onClicked:statistics.cancel() }
    }
    ColumnLayout {
        visible:!!statistics.analysisResult.advanced;Layout.fillWidth:true
        UiLabel { objectName:"missingResult";text:(statistics.current?"Güncel sonuç":"Kayıtlı/eski sonuç — sürümü kontrol edin")+"\n"+(statistics.analysisResult.method_label||"")+"\nSürüm: "+(statistics.analysisResult.dataset_version||"")+" · kullanılan kayıt: "+statistics.analysisResult.used_rows;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { objectName:"missingResultDetails";text:JSON.stringify(statistics.analysisResult.advanced||{},null,2);Layout.fillWidth:true;wrapMode:Text.Wrap;visible:preferences && preferences.view==="advanced" }
        UiLabel { objectName:"missingResultSummary";text:panel.resultText();Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:statistics.analysisResult.advanced?statistics.analysisResult.advanced.scenarios||[]:[];UiLabel { required property var modelData;text:"Delta="+modelData.delta+" · katsayı/ortalama="+panel.numbers(modelData.estimates)+" · SE="+panel.numbers(modelData.standard_errors)+" · marjinal CI="+panel.intervals(modelData.confidence_intervals);Layout.fillWidth:true;wrapMode:Text.Wrap } }
        Repeater { model:statistics.analysisResult.warnings||[];UiLabel { required property string modelData;text:modelData;Layout.fillWidth:true;wrapMode:Text.Wrap;color:Theme.warning } }
        UiButton { objectName:"missingSave";text:"Sonucu ve kimlikli çıktılarını projeye kaydet";enabled:statistics.current&&!statistics.busy&&!projects.busy&&!projects.readOnly;onClicked:statistics.save() }
        UiButton { objectName:"missingExport";text:"Kimlikli çıktıyı ve tarifi dışa aktar";enabled:statistics.current&&!statistics.busy;onClicked:statistics.exportAdvanced(exportPath.text) }
        UiTextField { id:exportPath;objectName:"missingExportPath";Accessible.name:"Yeni çıktı klasörü — mutlak yol";placeholderText:"Yeni çıktı klasörünün mutlak yolu";maximumLength:4096;Layout.fillWidth:true }
    }
    UiCombo { id:saved;objectName:"missingSaved";accessibleLabel:"Kayıtlı analiz";model:statistics.savedAnalyses;textRole:"label";valueRole:"id";Layout.fillWidth:true }
    UiButton { objectName:"missingOpen";text:"Kayıtlı sonucu aç";enabled:saved.currentIndex>=0&&!statistics.busy&&!projects.busy;onClicked:{statistics.openSaved(saved.currentValue);panel.restore(statistics.analysisResult.spec)} }
    function columnLabel(ident) {
        if(ident==="intercept")return "Sabit"
        let columns=statistics.analysisResult.source_columns||statistics.columns
        for(let c of columns)if(c.id===ident)return c.name
        return ident
    }
    function number(v) { return typeof v==="number" ? Number(v).toPrecision(6) : "sunulmuyor" }
    function numbers(values) { return (values||[]).map(v=>number(v)).join(" / ") }
    function intervals(values) { return (values||[]).map(v=>"["+number(v[0])+", "+number(v[1])+"]").join(" / ") }
    function resultText() {
        let r=statistics.analysisResult.advanced||{}
        if(r.estimate!==undefined)return "Ortalama="+number(r.estimate)+" · SE="+number(r.standard_error)+" · CI="+intervals([r.confidence_interval])+" · df="+r.df+(r.design_effect===undefined?"":"\nTasarım etkisi="+number(r.design_effect)+" · gözlenen ağırlıksız SRS s²/n referansı; kalibre popülasyon etkisi değildir")
        if(r.selected_row_ids)return "Seçilen satır="+r.selected_row_ids.length+" · seed="+r.seed+" · grup sayısı="+r.groups.length+"\n"+JSON.stringify(r.groups.slice(0,20))+"\nİlk20 grup gösterilir; tüm seçim kimlikleri ve olasılıklar kayıtlı çıktıda korunur."
        if(r.column_missing){
            let counts=Object.keys(r.column_missing).map(k=>columnLabel(k)+": "+r.column_missing[k]).join(" · ")
            let patterns=r.patterns.slice(0,20).map(p=>Object.keys(p).filter(k=>k!=="len").map(k=>columnLabel(k)+": "+(p[k]?"eksik":"gözlenen")).join(" · ")+" · n="+p.len).join("\n")
            return "Kolon eksikleri: "+counts+"\nDesenler (ilk20/"+r.patterns.length+"; tamamı kayıtlı sonuçta):\n"+patterns
        }
        if(r.estimates)return "Parametre sırası: "+r.parameter_names.map(k=>columnLabel(k)).join(" / ")+"\nKatsayılar="+numbers(r.estimates)+" · SE="+numbers(r.standard_errors)+" · CI="+intervals(r.confidence_intervals)
        return r.imputation_kind?"Çoklu imputasyon: "+r.imputations+" realizasyon · model="+r.model+" · varsayım="+r.assumption+"\nParametre sırası: "+(r.parameter_names||[]).map(k=>columnLabel(k)).join(" / "):""
    }
}
