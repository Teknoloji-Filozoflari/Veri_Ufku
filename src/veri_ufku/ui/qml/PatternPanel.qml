import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"patternPanel"
    property string helpContext:"model.pattern"
    signal helpRequested(var origin,string context)
    readonly property var tasks:["apriori","fp_growth","cohort","funnel","process","conformance"]
    readonly property var result:patterns.historyReport
    readonly property var analysis:result.analysis||{}
    function label(v){try{return String(JSON.parse(v)[1])}catch(e){return String(v)}}
    function fmt(v){return typeof v==="number"?v.toFixed(4):"NA — gözlem tamamlanmadı"}
    function key(c){return c.currentValue||""}
    function config(){return {task:tasks[task.currentIndex],entity:key(entity),activity:key(activity),time:key(time),order:useOrder.checked?key(order):"",complete:useComplete.checked?key(complete):"",duplicates:duplicates.currentIndex===0?"reject":"set",min_support:Number(support.text),min_confidence:Number(confidence.text),max_length:Number(length.text),candidate_budget:Number(budget.text),rule_budget:Number(rules.text),timezone:zone.text,period:["day","week","month"][period.currentIndex],cohort_start:start.currentIndex===0?"first_observed":"activity",start_activity:startActivity.text,unit:unit.currentIndex===0?"person":"event",observation_start:Number(left.text),observation_end:Number(right.text),stages:stages.text.split(",").map(function(x){return x.trim()}),window_seconds:Number(horizon.text),ties:useOrder.checked?"order":"reject",conformance:task.currentIndex===5?JSON.parse(model.text):null,seed:60}}
    Connections {target:patterns;function onSelectPattern(value){expanded.checked=true;task.currentIndex=panel.tasks.indexOf(value)}}
    UiCheckBox {id:expanded;objectName:"patternExpanded";text:"Faz60 sepet, kohort, funnel ve süreç analizi";Layout.fillWidth:true}
    ColumnLayout {visible:expanded.checked;Layout.fillWidth:true;spacing:Theme.sm
        UiLabel {text:"Yerel ilişki ve olay keşfi";font.bold:true;Layout.fillWidth:true}
        UiLabel {text:"Önce tabloyu içe aktarın.5000row/2000transaction veya kişi/case,64item/32activity. Sepet: transaction/item uzun tablo; null item yalnız tek satırlı açık boş sepet işareti. Farklı transaction ID'lerde aynı içerik ayrı sayılır. Kaynak değiştirilmez.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        ColumnLayout {enabled:!patterns.busy;Layout.fillWidth:true
            UiCombo {id:task;objectName:"patternTask";accessibleLabel:"Sepet veya olay analiz yöntemi";model:["Apriori","FP-growth — koşullu FP-tree","Cohort / retention","Sıralı event funnel","Directly-follows süreç grafiği","Conformance — açık activity transition modeli"];Layout.fillWidth:true}
            UiCombo {id:entity;objectName:"patternEntity";accessibleLabel:"Transaction kişi veya case kimlik kolonu";model:patterns.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiCombo {id:activity;objectName:"patternActivity";accessibleLabel:"Item veya activity kolonu";model:patterns.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiCombo {id:time;objectName:"patternTime";accessibleLabel:"Event timestamp kolonu";model:patterns.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiLabel {text:"Sepet support paydası boşlar dahil tüm transaction ID'leridir. Aynı transaction/item tekrarı reject veya açık set politikası. Quantity/frequency weighting yok. Rule çoklu keşiftir: yanlış ilişki/FDR kontrolü veya causality iddiası yok.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiCombo {id:duplicates;objectName:"patternDuplicates";accessibleLabel:"Sepet duplicate davranışı";model:["Duplicate pair reddet","Duplicate pair açıkça set olarak say"];Layout.fillWidth:true}
            UiTextField {id:support;objectName:"patternSupport";Accessible.name:"Minimum support oranı";text:"0.2";Layout.fillWidth:true}
            UiTextField {id:confidence;objectName:"patternConfidence";Accessible.name:"Minimum confidence oranı";text:"0.5";Layout.fillWidth:true}
            UiTextField {id:length;objectName:"patternLength";Accessible.name:"En büyük itemset uzunluğu";text:"4";Layout.fillWidth:true}
            UiTextField {id:budget;objectName:"patternBudget";Accessible.name:"Candidate veya FP node bütçesi";text:"5000";Layout.fillWidth:true}
            UiTextField {id:rules;objectName:"patternRules";Accessible.name:"İncelenen rule bütçesi";text:"1000";Layout.fillWidth:true}
            UiLabel {text:"Olay zamanı: Unix seconds veya offset içeren ISO. Naif saat reddedilir. Gözlem aralığı [start,end); bu aralık dışı satır varsa durur. Timezone IANA; dönemler yerel takvimde gün/hafta(Pazartesi)/ay. Geçişlerde gün24s varsayılmaz. İlk gözlenen olay gerçek yaşam başlangıcı olmayabilir.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiTextField {id:zone;objectName:"patternZone";Accessible.name:"IANA olay timezone";text:"UTC";Layout.fillWidth:true}
            UiTextField {id:left;objectName:"patternObservationStart";Accessible.name:"Gözlem başlangıcı Unix seconds dahil";text:"0";Layout.fillWidth:true}
            UiTextField {id:right;objectName:"patternObservationEnd";Accessible.name:"Gözlem bitişi Unix seconds hariç";text:"100";Layout.fillWidth:true}
            UiCombo {id:period;objectName:"patternPeriod";accessibleLabel:"Kohort takvim dönemi";model:["Gün","Hafta","Ay"];currentIndex:2;Layout.fillWidth:true}
            UiCombo {id:start;objectName:"patternCohortStart";accessibleLabel:"Kohort başlangıç tanımı";model:["Gözlem penceresinde ilk olay","İlk seçili başlangıç activity"];Layout.fillWidth:true}
            UiTextField {id:startActivity;objectName:"patternStartActivity";Accessible.name:"Kohort başlangıç activity etiketi";text:"signup";Layout.fillWidth:true}
            UiCombo {id:unit;objectName:"patternUnit";accessibleLabel:"Kişi veya olay birimi";model:["Kişi: unique active / ilk kohort kişi sayısı; funnel ilk attempt","Olay: dönem0 event paydası; funnel her stage0 ayrı attempt"];Layout.fillWidth:true}
            UiLabel {text:"Retention yalnız tam gözlenen takvim hücrelerinde hesaplanır; partial hücre NA, sıfır değil. Event-volume retention kişi olasılığı değildir ve1'i aşabilir. Funnel kişi başına ilk başlangıç; event modunda her stage0 yeni attempt, önceki attempt sonraki startta biter. Tam deadline gözlenmeyenler rate paydasına girmez; gözlenen sayıları ayrıca görünür.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiTextField {id:stages;objectName:"patternStages";Accessible.name:"Funnel aşamaları sıralı virgüllü activity etiketleri";text:"view,buy";Layout.fillWidth:true}
            UiTextField {id:horizon;objectName:"patternHorizon";Accessible.name:"Funnel attempt zaman penceresi saniye";text:"10";Layout.fillWidth:true}
            UiCheckBox {id:useOrder;objectName:"patternUseOrder";text:"Eşit timestamp için açık kaynak order kolonu kullan";Layout.fillWidth:true}
            UiCombo {id:order;objectName:"patternOrder";accessibleLabel:"Event integer sıra kolonu";model:patterns.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiCheckBox {id:useComplete;objectName:"patternUseComplete";text:"Case tamamlanma bool kolonu seç; yoksa bütün trace'ler incomplete/unknown";Layout.fillWidth:true}
            UiCombo {id:complete;objectName:"patternComplete";accessibleLabel:"Case complete bool kolonu";model:patterns.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiLabel {text:"DFG gerçek ardışık event sayımıdır; tekrar/cycle olabilir, causal DAG değildir. Timestamp tie reject veya unique integer order. Complete flag trace boyunca sabit. Conformance yalnız beyan edilen activity start/geçiş/end modelini denetler; incomplete trace hiçbir zaman fitting=true olmaz. Petri concurrency/token replay/alignment desteklenmiyor.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiTextField {id:model;objectName:"patternConformanceModel";Accessible.name:"Açık conformance model JSON";text:'{"schema":"ActivityTransitionModel/v1","starts":["view"],"ends":["buy"],"edges":[["view","buy"]]}';Layout.fillWidth:true}
            UiButton {objectName:"patternRun";text:"Yerel keşfi CPU'da başlat";primary:true;enabled:patterns.canPatternRun;onClicked:{try{patterns.startPattern(JSON.stringify(panel.config()))}catch(e){localError.text="Tarif veya model JSON geçersiz"}}Layout.fillWidth:true}
        }
        UiLabel {id:localError;text:"";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiButton {objectName:"patternCancel";text:"Keşif işini iptal et";visible:patterns.busy;onClicked:patterns.cancel();Layout.fillWidth:true}
        StateNotice {heading:"Keşif durumu";detail:patterns.errorText||patterns.message;kind:patterns.errorText?"error":patterns.busy?"loading":"info";Layout.fillWidth:true}
        Repeater {model:panel.result.warnings||[];UiLabel {required property string modelData;text:modelData;color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap}}
        UiLabel {visible:!!panel.analysis.cells;text:"Başlangıç activity olmadan hariç kişi n="+(panel.analysis.excluded_entities_without_start||[]).length;Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiLabel {objectName:"patternSummary";text:panel.result.status?panel.result.status+" · "+(panel.result.pattern_spec||{}).task+" · kaynak kayıt="+(panel.result.row_count||0)+" · önceki test kullanımı="+(panel.result.prior_test_use_ids||[]).length:"Henüz pattern sonucu yok";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiLabel {visible:panel.analysis.transaction_total!==undefined;text:"Transaction total="+panel.analysis.transaction_total+" · unique item="+panel.analysis.distinct_items+" · duplicate pair="+panel.analysis.duplicate_rows+"\n"+panel.analysis.denominator+"\nCandidate/node="+panel.analysis.candidates_or_nodes+" · rules examined="+panel.analysis.rules_examined;Layout.fillWidth:true;wrapMode:Text.Wrap}
        Repeater {model:panel.analysis.itemsets||[];UiLabel {required property var modelData;text:modelData.items.map(panel.label).join(" + ")+" · n="+modelData.count+" · support="+panel.fmt(modelData.support);Layout.fillWidth:true;wrapMode:Text.Wrap}}
        Repeater {model:panel.analysis.rules||[];UiLabel {required property var modelData;text:modelData.antecedent.map(panel.label).join(" + ")+" → "+modelData.consequent.map(panel.label).join(" + ")+" · support="+panel.fmt(modelData.support)+" · confidence="+panel.fmt(modelData.confidence)+" · lift="+panel.fmt(modelData.lift);Layout.fillWidth:true;wrapMode:Text.Wrap}}
        Repeater {model:panel.analysis.cells||[];UiLabel {required property var modelData;text:modelData.cohort+" · dönem="+modelData.period_index+" · gözlenen="+modelData.observed_count+" / payda="+modelData.denominator+" · "+panel.fmt(modelData.retention)+" · complete="+modelData.complete+" · right-censored="+modelData.right_censored+" · left-truncated="+modelData.left_truncated;Layout.fillWidth:true;wrapMode:Text.Wrap}}
        UiLabel {visible:!!panel.analysis.stages;text:"Funnel payda (tam gözlenen attempt)="+panel.analysis.denominator+" · censored="+panel.analysis.censored_attempts+" · "+(panel.analysis.policy||"");Layout.fillWidth:true;wrapMode:Text.Wrap}
        Repeater {model:panel.analysis.stages||[];UiLabel {required property var modelData;text:modelData.activity+" · tam gözlenen n="+modelData.count+" · censored dahil gözlenen="+modelData.observed_including_censored+" · oran="+panel.fmt(modelData.fraction);Layout.fillWidth:true;wrapMode:Text.Wrap}}
        UiLabel {visible:!!panel.analysis.nodes;text:"Directly-follows · incomplete trace="+panel.analysis.incomplete_traces+" · "+(panel.analysis.graph_meaning||"");Layout.fillWidth:true;wrapMode:Text.Wrap}
        Canvas {objectName:"patternGraph";visible:!!panel.analysis.nodes;Layout.preferredWidth:500;Layout.preferredHeight:300;property var graph:panel.analysis;onGraphChanged:requestPaint();onPaint:{var c=getContext("2d"),ns=graph.nodes||[],es=graph.edges||[];c.fillStyle="#202532";c.fillRect(0,0,width,height);if(!ns.length)return;var pos={};for(var i=0;i<ns.length;i++){var a=2*Math.PI*i/ns.length;pos[ns[i].activity]={x:width/2+(ns.length>1?170*Math.cos(a):0),y:height/2+(ns.length>1?100*Math.sin(a):0)}}c.font="12px sans-serif";for(var e of es){var p=pos[e.source],q=pos[e.target];c.strokeStyle="#ff983e";c.fillStyle="#ffffff";c.beginPath();if(e.source===e.target){c.arc(p.x,p.y-25,20,0,2*Math.PI);c.stroke();c.fillText("↻ "+e.count,p.x+20,p.y-35)}else{c.moveTo(p.x,p.y);c.lineTo(q.x,q.y);c.stroke();var dx=q.x-p.x,dy=q.y-p.y,l=Math.sqrt(dx*dx+dy*dy),x=q.x-26*dx/l,y=q.y-26*dy/l;c.beginPath();c.moveTo(x,y);c.lineTo(x-9*dx/l+5*dy/l,y-9*dy/l-5*dx/l);c.lineTo(x-9*dx/l-5*dy/l,y-9*dy/l+5*dx/l);c.closePath();c.fill();c.fillText(String(e.count),(p.x+q.x)/2,(p.y+q.y)/2-7)}}for(var node of ns){var v=pos[node.activity];c.fillStyle="#343b50";c.beginPath();c.arc(v.x,v.y,25,0,2*Math.PI);c.fill();c.fillStyle="#ffffff";c.fillText(node.activity+" n="+node.count,v.x-22,v.y+4)}}}
        Repeater {model:panel.analysis.edges||[];UiLabel {required property var modelData;text:modelData.source+" → "+modelData.target+" · observed directly-follows n="+modelData.count;Layout.fillWidth:true;wrapMode:Text.Wrap}}
        Repeater {model:panel.analysis.traces||[];UiLabel {required property var modelData;text:"Case "+panel.label(modelData.case)+" · "+modelData.activities.join(" → ")+"\n"+modelData.completion+" · fitting="+(modelData.fitting===true?"true":modelData.fitting===false?"false":"unknown")+" · ihlaller="+JSON.stringify(modelData.violations);Layout.fillWidth:true;wrapMode:Text.Wrap}}
        UiCombo {id:saved;objectName:"patternSaved";accessibleLabel:"Kalıcı pattern kayıtları";model:patterns.savedRuns;textRole:"label";valueRole:"id";Layout.fillWidth:true}
        UiButton {objectName:"patternOpen";text:"Kalıcı keşif snapshot'ını aç";enabled:!patterns.busy&&saved.currentIndex>=0;onClicked:patterns.openRun(saved.currentValue);Layout.fillWidth:true}
        UiButton { visible: false;objectName:"patternHelp";text:"Support/lift, retention paydası, case ve trace öğren";helpContext:"model.pattern";onClicked:panel.helpRequested(this,helpContext);Layout.fillWidth:true}
    }
}
