import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"causalPanel"
    property string helpContext:"causal"
    property bool expanded:expand.checked
    property bool restoring:false
    property var features:[]
    property var assumptionsMap:({consistency:"",exchangeability:"",positivity:"",no_interference:"",time_order:"",parallel_trends:"",no_anticipation:"",exclusion:"",instrument_independence:"",monotonicity:""})
    property var assumptionKeys:["consistency","exchangeability","positivity","no_interference","time_order","parallel_trends","no_anticipation","exclusion","instrument_independence","monotonicity"]
    property var columns:[{id:"",name:"Seçin"}].concat(statistics.columns)
    readonly property string method:methodChoice.currentValue||"causal_randomized"
    readonly property bool observational:["causal_adjustment","causal_ipw","causal_aipw","causal_matching"].includes(method)
    signal helpRequested(var origin,string context)
    spacing:Theme.md
    function invalidate(){if(!restoring){assumptions.checked=false;statistics.invalidate()}}
    function plan(){return {dag:dag.graph,assumptions:assumptionsMap,randomization_evidence:evidence.text,allocation:Number(allocation.text),alternatives:alternatives.text,folds:folds.value,overlap_epsilon:Number(epsilon.text),extreme_weight:Number(extreme.text),caliper:Number(caliper.text),post_time:post.text,instrument:method==="causal_iv"?(instrument.currentValue||""):"",placebo:placebo.currentValue||"",placebo_reason:placeboReason.text,bias_deltas:bias.text.split(",").map(Number)}}
    function spec(){return {path:"causal",method:method,x:outcome.currentValue||"",y:treatment.currentValue||"",key:unitId.currentValue||"",time_column:time.currentValue||"",features:observational?features:[],question:question.text,unit:unit.text,observation_unit:observation.text,scope:"full",seed:seed.value,confidence:Number(level.text),causal_plan:plan(),measurement_confirmed:measurement.checked,independent:independent.checked,assumptions_confirmed:assumptions.checked}}
    function number(x){return typeof x==="number"?Number(x).toPrecision(5):"sunulmuyor"}
    function describe(r){
        if(!r||!r.causal)return ""
        let a=r.causal_analysis,i=a.identification,e=a.effect,lines=[r.method_label+" · kayıt="+r.used_rows+" · analiz birimi="+r.n.analysis_units,a.estimand,a.conclusion,"Maliyet / bütçe: "+JSON.stringify(r.budget),"Birim: "+(r.spec?r.spec.unit:unit.text)+" · bağımsız analiz birimi: "+observation.text,"Identification: "+i.status+" · backdoor ayrılığı="+i.backdoor_separated,i.blockers.join("\n")]
        if(e)lines.push("Etki="+number(e.estimate)+" · SE="+number(e.se)+" · interval="+(e.interval?e.interval.map(number).join(" / "):"desteklenmiyor"),e.inference)
        let d=a.diagnostics
        if(d.overlap)lines.push("Overlap ε="+d.overlap.epsilon+" · ε dışında="+d.overlap.outside_epsilon+" · max weight="+number(d.overlap.maximum_weight)+" · ESS="+d.overlap.ess.map(number).join(" / "),"Propensity kol aralıkları/binleri: "+JSON.stringify(d.overlap.arms),"Balance before/IPW SMD: "+JSON.stringify(d.overlap.balance_before)+" / "+JSON.stringify(d.overlap.balance_ipw))
        if(d.matching)lines.push("Matching: "+JSON.stringify(d.matching)+" · kaynak RowId pairs="+a.pairs.length)
        if(d.pretrend_placebo)lines.push("Parallel trend/placebo: "+JSON.stringify(d.pretrend_placebo))
        if(d.iv)lines.push("IV relevance / validity sınırı: "+JSON.stringify(d.iv))
        if(d.srm)lines.push("Randomize allocation/SRM: "+JSON.stringify(d.srm))
        if(d.placebo)lines.push("Placebo: "+JSON.stringify(d.placebo))
        if(a.split_plan)lines.push("Cross-fitting: "+a.split_plan.validation_plan.split_id+" · her satır bir kez out-of-fold; scaler train içinde fit · test bloğu development ile değerlendirilir")
        lines.push("Sensitivity: "+JSON.stringify(a.sensitivity),"Alternatif açıklamalar: "+i.alternatives,"Varsayım gerekçeleri: "+JSON.stringify(i.assumptions),i.caveat)
        return lines.filter(x=>x).join("\n\n")
    }
    function restore(s){
        if(!s||s.path!=="causal"){expand.checked=false;return}
        restoring=true;expand.checked=true
        for(let pair of [[methodChoice,s.method],[outcome,s.x],[treatment,s.y],[unitId,s.key],[time,s.time_column],[instrument,s.causal_plan.instrument],[placebo,s.causal_plan.placebo]])for(let j=0;j<pair[0].model.length;j++)if(pair[0].model[j].id===pair[1])pair[0].currentIndex=j
        let p=s.causal_plan
        for(let pair of [[question,s.question],[unit,s.unit],[observation,s.observation_unit],[level,s.confidence],[evidence,p.randomization_evidence],[allocation,p.allocation],[alternatives,p.alternatives],[epsilon,p.overlap_epsilon],[extreme,p.extreme_weight],[caliper,p.caliper],[post,p.post_time],[placeboReason,p.placebo_reason],[bias,p.bias_deltas.join(",")]])pair[0].text=String(pair[1])
        features=s.features;dag.graph=p.dag;assumptionsMap=p.assumptions;folds.value=p.folds;seed.value=s.seed;measurement.checked=s.measurement_confirmed;independent.checked=s.independent;assumptions.checked=false;restoring=false
    }
    Connections {target:expertWorkspace;function onSelectMethod(path,name){if(path!=="causal"){expand.checked=false;return}expand.checked=true;for(let i=0;i<methodChoice.model.length;i++)if(methodChoice.model[i].id===name)methodChoice.currentIndex=i;panel.invalidate()}function onRestorePreset(value){panel.restore(JSON.parse(value))}}
    UiCheckBox {id:expand;objectName:"causalExpanded";text:"44 · Nedensel soru / identification · dört alt aşama"}
    ColumnLayout {
        visible:panel.expanded;Layout.fillWidth:true;spacing:Theme.md
        RowLayout {
            Layout.fillWidth:true
            UiCombo {id:methodChoice;objectName:"causalMethod";model:statistics.methods("causal");textRole:"label";valueRole:"id";accessibleLabel:"Nedensel yöntem / alt aşama";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiButton {objectName:"causalHelp";text:"Bu ne işe yarar?";helpContext:"causal";onClicked:panel.helpRequested(this,"statistics."+panel.method.split("_").join("-"))}
        }
        UiLabel {text:"Önce44.1 randomize/adjustment/IPW/AIPW;44.2matching;44.3DiD;44.4IV. Tam seçili sürüm, eksiksiz sayısal alanlar ve dönem sütunu gerekir. Gözlemsel ilişki nedensellik kanıtı değildir; feature importance neden sıralaması değildir.";Layout.fillWidth:true;wrapMode:Text.WordWrap}
        GridLayout {
            columns:2;Layout.fillWidth:true
            UiLabel {text:"Soru"}
            UiTextField {id:question;objectName:"causalQuestion";Accessible.name:"Soru";text:"Tedavinin outcome üzerindeki etkisi?";placeholderText:"Soru";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Outcome"}
            UiCombo {id:outcome;objectName:"causalOutcome";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Outcome";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Treatment (0/1)"}
            UiCombo {id:treatment;objectName:"causalTreatment";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Treatment (0/1)";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Analiz birimi kimliği"}
            UiCombo {id:unitId;objectName:"causalUnitId";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Analiz birimi kimliği";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Sayısal zaman/dönem"}
            UiCombo {id:time;objectName:"causalTime";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Sayısal zaman/dönem";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Outcome birimi"}
            UiTextField {id:unit;objectName:"causalUnit";Accessible.name:"Outcome birimi";text:"puan";placeholderText:"Outcome birimi";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Bağımsız analiz birimi"}
            UiTextField {id:observation;objectName:"causalObservation";Accessible.name:"Bağımsız analiz birimi";text:"kişi";placeholderText:"Bağımsız analiz birimi";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"IV instrument (0/1)"}
            UiCombo {id:instrument;objectName:"causalInstrument";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"IV instrument (0/1)";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Ön-tedavi placebo (isteğe bağlı)"}
            UiCombo {id:placebo;objectName:"causalPlacebo";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Ön-tedavi placebo (isteğe bağlı)";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Placebo gerekçesi"}
            UiTextField {id:placeboReason;objectName:"causalPlaceboReason";Accessible.name:"Placebo gerekçesi";text:"";placeholderText:"Placebo gerekçesi";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Bernoulli randomizasyon kanıtı"}
            UiTextField {id:evidence;objectName:"causalEvidence";Accessible.name:"Bernoulli randomizasyon kanıtı";text:"";placeholderText:"Bernoulli randomizasyon kanıtı";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Planlanan treatment oranı"}
            UiTextField {id:allocation;objectName:"causalAllocation";Accessible.name:"Planlanan treatment oranı";text:"0.5";placeholderText:"Planlanan treatment oranı";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Alternatif açıklamalar"}
            UiTextField {id:alternatives;objectName:"causalAlternatives";Accessible.name:"Alternatif açıklamalar";text:"";placeholderText:"Alternatif açıklamalar";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Overlap ε"}
            UiTextField {id:epsilon;objectName:"causalEpsilon";Accessible.name:"Overlap ε";text:"0.05";placeholderText:"Overlap ε";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Extreme weight eşiği"}
            UiTextField {id:extreme;objectName:"causalExtreme";Accessible.name:"Extreme weight eşiği";text:"20";placeholderText:"Extreme weight eşiği";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Matching raw propensity caliper"}
            UiTextField {id:caliper;objectName:"causalCaliper";Accessible.name:"Matching raw propensity caliper";text:"0.05";placeholderText:"Matching raw propensity caliper";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"DiD ortak post dönem"}
            UiTextField {id:post;objectName:"causalPost";Accessible.name:"DiD ortak post dönem";text:"2";placeholderText:"DiD ortak post dönem";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Hipotetik additive bias senaryoları"}
            UiTextField {id:bias;objectName:"causalBias";Accessible.name:"Hipotetik additive bias senaryoları";text:"-1,0,1";placeholderText:"Hipotetik additive bias senaryoları";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"CI düzeyi (desteklenen yöntem)"}
            UiTextField {id:level;objectName:"causalLevel";Accessible.name:"CI düzeyi (desteklenen yöntem)";text:"0.95";placeholderText:"CI düzeyi (desteklenen yöntem)";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Cross-fitting folds"}
            UiSpinBox {id:folds;objectName:"causalFolds";from:2;to:5;value:3;Accessible.name:"Nuisance fold sayısı";onValueModified:panel.invalidate()}
            UiLabel {text:"Seed"}
            UiSpinBox {id:seed;objectName:"causalSeed";from:0;to:1000000000;value:42;Accessible.name:"Nedensel split seed";onValueModified:panel.invalidate()}
        }
        RowLayout {
            visible:panel.observational;Layout.fillWidth:true
            UiCombo {id:predictor;objectName:"causalPredictor";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Ön-tedavi covariate";Layout.fillWidth:true}
            UiButton {objectName:"causalAddPredictor";text:"Covariate ekle";onClicked:{if(predictor.currentValue&&!panel.features.includes(predictor.currentValue)){panel.features=panel.features.concat([predictor.currentValue]);panel.invalidate()}}}
            UiButton {text:"Covariate temizle";onClicked:{panel.features=[];panel.invalidate()}}
        }
        UiLabel {text:"Seçili covariate: "+panel.features.map(id=>panel.columns.find(c=>c.id===id)?.name||id).join(", ");Layout.fillWidth:true;wrapMode:Text.WordWrap}
        CausalDagEditor {id:dag;objectName:"causalDagEditor";columns:panel.columns;Layout.fillWidth:true;onEdited:panel.invalidate()}
        UiLabel {text:"Identification / assumptions · Gerekçesi boş gerekli koşul hesaplanan etkiyi engeller. Exchangeability/ölçülmemiş confounding, consistency, interference ve zaman sırası veriden kanıtlanmaz. DiD: parallel trends/no anticipation; IV: relevance/exclusion/independence/monotonicity; AIPW: nuisance consistency/product rates. Sadece iki pre dönem paralel trendi kanıtlamaz.";wrapMode:Text.WordWrap;Layout.fillWidth:true}
        Repeater {
            model:panel.assumptionKeys
            RowLayout {
                required property string modelData;Layout.fillWidth:true
                UiLabel {text:modelData;Layout.preferredWidth:180}
                UiTextField {objectName:"causalAssumption_"+modelData;Accessible.name:"Varsayım gerekçesi "+modelData;text:panel.assumptionsMap[modelData]||"";placeholderText:"Alan/zaman/tasarım gerekçesi; otomatik onay yok";Layout.fillWidth:true;onTextEdited:{let a=Object.assign({},panel.assumptionsMap);a[modelData]=text;panel.assumptionsMap=a;panel.invalidate()}}
            }
        }
        UiCheckBox {id:measurement;objectName:"causalMeasurement";text:"Outcome birimi, treatment/covariate zaman sırası ve tam rosterı doğruladım";onToggled:panel.invalidate()}
        UiCheckBox {id:independent;objectName:"causalIndependent";text:"Analiz birimleri bağımsız; DiD'de birimler arası bağımsızlık";onToggled:panel.invalidate()}
        UiButton {objectName:"causalPreflight";text:"Identification / overlap / maliyet önkontrolü";enabled:!statistics.busy;onClicked:statistics.create(JSON.stringify(panel.spec()),true)}
        UiLabel {objectName:"causalPreview";visible:statistics.preflightCurrent&&statistics.preflightResult.causal===true;text:panel.describe(statistics.preflightResult);Layout.fillWidth:true;wrapMode:Text.WordWrap}
        UiCheckBox {id:assumptions;objectName:"causalAssumptions";text:"Identification, varsayımlar, estimand, tanılar ve sınırlı CI desteğini inceledim";enabled:statistics.preflightCurrent}
        RowLayout {
            UiButton {objectName:"causalRun";text:"Koşullu etki / belirlenemiyor raporu";enabled:!statistics.busy&&assumptions.checked;onClicked:statistics.create(JSON.stringify(panel.spec()),false)}
            UiButton {objectName:"causalCancel";text:"İptal";enabled:statistics.busy;onClicked:statistics.cancel()}
        }
        UiLabel {text:statistics.message;Layout.fillWidth:true;wrapMode:Text.WordWrap}
        UiLabel {text:statistics.errorText;visible:!!statistics.errorText;color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.WordWrap}
        UiLabel {objectName:"causalResult";visible:statistics.analysisResult.causal===true;text:panel.describe(statistics.analysisResult);Layout.fillWidth:true;wrapMode:Text.WordWrap}
        RowLayout {
            Layout.fillWidth:true
            UiButton {objectName:"causalSave";text:"Varsayımlar / kaynak eşlemeyle kaydet";enabled:statistics.current&&!statistics.busy&&statistics.analysisResult.causal===true;onClicked:statistics.save()}
            UiTextField {id:exportPath;objectName:"causalExportPath";Accessible.name:placeholderText;placeholderText:"Yeni mutlak export klasörü";Layout.fillWidth:true}
            UiButton {objectName:"causalExport";text:"Rapor / RowId export";enabled:statistics.current&&!statistics.busy&&statistics.analysisResult.causal===true;onClicked:statistics.exportAdvanced(exportPath.text)}
        }
        RowLayout {
            Layout.fillWidth:true
            UiCombo {id:saved;objectName:"causalSaved";model:statistics.savedAnalyses.filter(v=>v.path==="causal");textRole:"label";valueRole:"id";accessibleLabel:"Kayıtlı nedensel rapor";Layout.fillWidth:true}
            UiButton {objectName:"causalOpen";text:"Kaydı aç";enabled:!!saved.currentValue&&!statistics.busy;onClicked:{statistics.openSaved(saved.currentValue);panel.restore(statistics.analysisResult.spec)}}
        }
    }
}
