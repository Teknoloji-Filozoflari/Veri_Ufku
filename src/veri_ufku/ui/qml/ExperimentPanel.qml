import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"experimentPanel"
    property bool expanded:expand.checked
    property bool restoring:false
    readonly property string method:methodChoice.currentValue||"power_mean"
    readonly property bool power:method.indexOf("power_")===0
    readonly property bool analysis:method.indexOf("experiment_")===0
    readonly property bool proportion:method.indexOf("proportion")>=0
    property string methodHelp:"statistics."+method.split("_").join("-")
    property var optionalColumns:[{id:"",name:"Seçin"}].concat(statistics.columns)
    property var baselineIds:[]
    property var guards:[]
    signal helpRequested(var origin,string context)
    spacing:Theme.md
    function key(c){return c.currentValue||""}
    function number(v){return typeof v==="number"?Number(v).toPrecision(6):v===null||v===undefined?"sunulmuyor":String(v)}
    function invalidate(){if(restoring)return;assumptions.checked=false;statistics.invalidate()}
    function plan(){return {design:"two_group_independent",randomization_unit:randomUnit.text,analysis_unit:analysisUnit.text,primary_metric:metricName.text,measurement_window:measurementWindow.text,eligibility:eligibility.text,stop_rule:stopRule.text,monitoring:"fixed_horizon",alpha:Number(alpha.text),power:Number(targetPower.text),mde:Number(mde.text),baseline_value:Number(baselineValue.text),sd:Number(sd.text),allocation:Number(allocation.text),expected_attrition:Number(attrition.text),design_effect:Number(designEffect.text),planned_total:plannedTotal.value,randomized_confirmed:randomized.checked,randomization_evidence:evidence.text,horizon_complete:horizon.checked,analysis_population:key(population),protocol_column:analysis&&key(population)==="PP"?key(protocol):"",baseline_columns:analysis?baselineIds:[],guardrails:analysis?guards:[]}}
    function spec(){return {path:"experiments",method:method,x:analysis?key(outcome):"",key:!power?key(person):"",group:analysis?key(arm):"",before:controlLabel.text,after:treatmentLabel.text,scope:"full",experiment_plan:plan(),seed:seed.value,confidence:1-Number(alpha.text),alternative:"two-sided",question:question.text,hypothesis:hypothesis.text,unit:unit.text,observation_unit:analysisUnit.text,measurement_confirmed:measurement.checked,independent:independent.checked,assumptions_confirmed:assumptions.checked}}
    function restore(s){
        if(!s||s.path!=="experiments"){expand.checked=false;return}
        restoring=true;expand.checked=true
        let p=s.experiment_plan
        for(let pair of [[methodChoice,s.method],[outcome,s.x],[person,s.key],[arm,s.group],[protocol,p.protocol_column],[population,p.analysis_population]])for(let i=0;i<pair[0].model.length;i++)if(pair[0].model[i].id===pair[1])pair[0].currentIndex=i
        for(let pair of [[randomUnit,p.randomization_unit],[analysisUnit,p.analysis_unit],[metricName,p.primary_metric],[measurementWindow,p.measurement_window],[eligibility,p.eligibility],[stopRule,p.stop_rule],[alpha,p.alpha],[targetPower,p.power],[mde,p.mde],[baselineValue,p.baseline_value],[sd,p.sd],[allocation,p.allocation],[attrition,p.expected_attrition],[designEffect,p.design_effect],[evidence,p.randomization_evidence],[controlLabel,s.before],[treatmentLabel,s.after],[question,s.question],[hypothesis,s.hypothesis],[unit,s.unit]])pair[0].text=String(pair[1])
        plannedTotal.value=p.planned_total;seed.value=s.seed;randomized.checked=p.randomized_confirmed;horizon.checked=p.horizon_complete;baselineIds=p.baseline_columns;guards=p.guardrails;measurement.checked=s.measurement_confirmed;independent.checked=s.independent;assumptions.checked=false;restoring=false
    }
    function resultText(r){
        if(!r||!r.experiment)return ""
        let rows=[statistics.current?"Güncel veri / ölçüm planı sonucu":"ESKİ VERİ / PLAN: güncel diye kaydedilemez veya export edilemez",r.method_label,"Birincil metrik: "+r.plan.primary_metric+" · alpha="+number(r.plan.alpha)+" · sabit ufuk: "+r.plan.planned_total+" · ölçüm penceresi: "+r.plan.measurement_window,"Randomizasyon birimi: "+r.plan.randomization_unit+" · analiz birimi: "+r.plan.analysis_unit+" · design effect="+number(r.plan.design_effect)]
        if(r.power_plan){let p=r.power_plan;rows.push("A priori güç="+number(r.plan.power)+" · mutlak MDE="+number(r.plan.mde)+" · allocation(B)="+number(r.plan.allocation),"Analiz edilebilir A="+p.analyzable_control+" / B="+p.analyzable_treatment+" · recruitment A="+p.recruit_control+" / B="+p.recruit_treatment,"Yuvarlanan tasarım gücü="+number(p.rounded_design_power)+" · "+p.method,"Observed power değildir; beklenen kayıp şişirmesi attrition bias düzeltmez.")}
        if(r.assignment){let a=r.assignment;rows.push("YEREL TASLAK: gerçek kişiye atama/mesaj yapılmadı.","Bernoulli · seed="+a.seed+" · PCG64 · A="+a.control+" / B="+a.treatment+" · birim="+a.units,"Tam birim/kol listesi details.parquet içinde; kaynak değiştirilmedi.")}
        if(r.experiment_analysis){let a=r.experiment_analysis;let e=a.effect;rows.push("Kullanıcı beyanı randomize tasarım; uygulama kanıtı doğrulamaz. Plan/kanıt: "+r.plan.randomization_evidence,"Popülasyon: "+a.analysis_population+" · "+(a.analysis_population==="ITT"?"Assigned kola göre, bütün ölçümler gerekli":"Protokol seçimi; randomize nedensel ITT etkisi değildir"),"SRM tam roster="+a.srm.denominator+" · A="+a.srm.control+" / B="+a.srm.treatment+" · beklenen B="+number(a.srm.expected_treatment_fraction)+" · exact binomial p="+number(a.srm.p_value)+(a.srm.flag?" · SRM UYARISI: çıkarım kapalı":" · eşik0.001 aşılmadı"))
            for(let g of a.arms)rows.push(g.arm+": assigned="+g.assigned+" · popülasyon="+g.population+" · observed="+g.observed+" · missing="+g.missing+" · PP dışlanan="+g.protocol_excluded+" · attrition="+number(g.attrition_rate)+(g.events!==null?" · event="+g.events:""))
            rows.push("Attrition oran farkı B−A="+number(a.attrition_rate_difference),"Etki durumu: "+e.status)
            if(e.absolute_effect!==undefined)rows.push("Mutlak B−A="+number(e.absolute_effect)+" · CI="+(e.absolute_ci?e.absolute_ci.map(number).join(" / "):"sunulmuyor"),"Göreli değişim="+number(e.relative_effect)+" · CI="+(e.relative_ci?e.relative_ci.map(number).join(" / "):"sunulmuyor: "+e.relative_ci_status),"İki yönlü H0 fark0 · p="+number(e.p_value)+" · "+(e.method||""))
            if(a.missing_binary_worst_case_effect_bounds)rows.push("Eksik sonuç0/1 worst-case sınırı (CI değil)="+a.missing_binary_worst_case_effect_bounds.map(number).join(" / "))
            for(let b of a.baseline)rows.push("Baseline "+b.column_id+": A="+number(b.control_mean)+" / B="+number(b.treatment_mean)+" · SMD="+number(b.smd)+" · betimsel, p ile değişken seçimi yok")
            for(let g of a.guardrails)rows.push("Guardrail "+g.plan.name+": mutlak değişim="+number(g.absolute_change)+" · eksik="+g.missing+" · betimsel zarar sınırı aşımı="+g.descriptive_limit_crossed+" · çoklu-test düzeltilmiş çıkarım değil")
        }
        rows.push("Sequential monitoring KAPALI. Paired/cluster/factorial ayrı, uygulanmamış alt işler.",...(r.warnings||[]));return rows.join("\n")
    }
    Connections {target:expertWorkspace;function onSelectMethod(path,name){if(path!=="experiments"){expand.checked=false;return}expand.checked=true;for(let i=0;i<methodChoice.model.length;i++)if(methodChoice.model[i].id===name)methodChoice.currentIndex=i}function onRestorePreset(value){panel.restore(JSON.parse(value))}}
    UiCheckBox {id:expand;objectName:"experimentExpanded";text:"Faz42 · Ölçüm planı, güç ve randomize deney";onToggled:panel.invalidate()}
    ColumnLayout {
        visible:panel.expanded;Layout.fillWidth:true;spacing:Theme.md
        UiLabel {Layout.fillWidth:true;wrapMode:Text.WordWrap;text:"Bağımsız iki grup önce tamamlanır. Randomizasyon ve analiz birimi ayrı kaydedilir; bu yol aynı bağımsız birimi ister. Paired/cluster/factorial ve sequential alt işleri kapalı. Sabit ufukta tekrar bakarak durdurmak hata oranını korumaz."}
        RowLayout {
            Layout.fillWidth:true
            UiCombo {id:methodChoice;objectName:"experimentMethod";Layout.fillWidth:true;model:statistics.methods("experiments");textRole:"label";valueRole:"id";accessibleLabel:"Faz42 yöntem";onActivated:panel.invalidate()}
            UiButton { visible: false;objectName:"experimentHelp";text:"Yöntem yardımı";helpContext:panel.methodHelp;onClicked:panel.helpRequested(this,helpContext)}
            UiButton { visible: false;text:"Deney planı nedir?";helpContext:"experiment-plan";onClicked:panel.helpRequested(this,helpContext)}
        }
        UiTextField {Accessible.name:placeholderText;id:question;objectName:"experimentQuestion";Layout.fillWidth:true;placeholderText:"Deney sorusu";text:"Önceden belirlenen deney sorusu";onTextEdited:panel.invalidate()}
        UiTextField {Accessible.name:placeholderText;id:hypothesis;objectName:"experimentHypothesis";Layout.fillWidth:true;placeholderText:"Önceden belirlenen hipotez";text:"H0: tedavi−kontrol birincil metrik farkı0";onTextEdited:panel.invalidate()}
        GridLayout {
            Layout.fillWidth:true;columns:2
            UiLabel {text:"Birincil metrik"}
            UiTextField {Accessible.name:placeholderText;id:metricName;objectName:"experimentMetricName";Layout.fillWidth:true;placeholderText:"Birincil metrik adı";text:"7 günlük birincil ölçüm";onTextEdited:panel.invalidate()}
            UiLabel {text:"Metrik birimi"}
            UiTextField {Accessible.name:placeholderText;id:unit;objectName:"experimentMetricUnit";Layout.fillWidth:true;placeholderText:"Metrik birimi";text:panel.proportion?"kişi başına event0/1":"puan";onTextEdited:panel.invalidate()}
            UiLabel {text:"Randomizasyon birimi"}
            UiTextField {Accessible.name:placeholderText;id:randomUnit;objectName:"experimentRandomUnit";Layout.fillWidth:true;placeholderText:"Randomizasyon birimi";text:"kişi";onTextEdited:panel.invalidate()}
            UiLabel {text:"Analiz birimi · ayrı sözleşme"}
            UiTextField {Accessible.name:placeholderText;id:analysisUnit;objectName:"experimentAnalysisUnit";Layout.fillWidth:true;placeholderText:"Analiz birimi";text:"kişi";onTextEdited:panel.invalidate()}
            UiLabel {text:"Ölçüm penceresi"}
            UiTextField {Accessible.name:placeholderText;id:measurementWindow;objectName:"experimentWindow";Layout.fillWidth:true;placeholderText:"Ölçüm penceresi";text:"7 gün";onTextEdited:panel.invalidate()}
            UiLabel {text:"Kayıt öncesi uygunluk"}
            UiTextField {Accessible.name:placeholderText;id:eligibility;objectName:"experimentEligibility";Layout.fillWidth:true;placeholderText:"Uygunluk planı";text:"Önceden uygun bütün bağımsız birimler";onTextEdited:panel.invalidate()}
            UiLabel {text:"Durdurma kuralı · fixed horizon"}
            UiTextField {Accessible.name:placeholderText;id:stopRule;objectName:"experimentStopRule";Layout.fillWidth:true;placeholderText:"Durdurma kuralı";text:"Planlanan tam roster ve ölçüm penceresi tamamlanır";onTextEdited:panel.invalidate()}
            UiLabel {text:"Alpha · iki yönlü; CI=1−alpha"}
            UiTextField {Accessible.name:placeholderText;id:alpha;objectName:"experimentAlpha";Layout.fillWidth:true;placeholderText:"Alpha";text:"0.05";onTextEdited:panel.invalidate()}
            UiLabel {text:"Hedef güç"}
            UiTextField {Accessible.name:placeholderText;id:targetPower;objectName:"experimentPower";Layout.fillWidth:true;placeholderText:"A priori power";text:"0.8";onTextEdited:panel.invalidate()}
            UiLabel {text:"Mutlak MDE · oran için puan farkı"}
            UiTextField {Accessible.name:placeholderText;id:mde;objectName:"experimentMde";Layout.fillWidth:true;placeholderText:"Mutlak MDE";text:"0.2";onTextEdited:panel.invalidate()}
            UiLabel {text:"Planlanan baseline · observed power yok"}
            UiTextField {Accessible.name:placeholderText;id:baselineValue;objectName:"experimentBaselineValue";Layout.fillWidth:true;placeholderText:"Baseline varsayımı";text:"0.3";onTextEdited:panel.invalidate()}
            UiLabel {text:"Planlanan ortak SD · mean power"}
            UiTextField {Accessible.name:placeholderText;id:sd;objectName:"experimentSd";Layout.fillWidth:true;placeholderText:"Planlanan SD";text:"1";onTextEdited:panel.invalidate()}
            UiLabel {text:"Allocation · bağımsız Bernoulli P(B)"}
            UiTextField {Accessible.name:placeholderText;id:allocation;objectName:"experimentAllocation";Layout.fillWidth:true;placeholderText:"Tedavi allocation olasılığı";text:"0.5";onTextEdited:panel.invalidate()}
            UiLabel {text:"Beklenen ölçüm kaybı · recruitment"}
            UiTextField {Accessible.name:placeholderText;id:attrition;objectName:"experimentAttrition";Layout.fillWidth:true;placeholderText:"Beklenen attrition";text:"0.1";onTextEdited:panel.invalidate()}
            UiLabel {text:"Design effect · bağımsız yol yalnız1"}
            UiTextField {Accessible.name:placeholderText;id:designEffect;objectName:"experimentDesignEffect";Layout.fillWidth:true;placeholderText:"Design effect";text:"1";onTextEdited:panel.invalidate()}
            UiLabel {text:"Sabit ufuk toplam randomize birim"}
            UiSpinBox {id:plannedTotal;objectName:"experimentPlannedTotal";from:4;to:100000;value:20;Accessible.name:"Planlanan toplam birim";onValueModified:panel.invalidate()}
            UiLabel {text:"Yerel taslak seed · analizde randomization üretmez"}
            UiSpinBox {id:seed;objectName:"experimentSeed";from:0;to:2147483647;value:42;Accessible.name:"Assignment seed";onValueModified:panel.invalidate()}
            UiLabel {visible:!panel.power;text:"Benzersiz randomizasyon/analiz birim kimliği"}
            UiCombo {id:person;objectName:"experimentPerson";visible:!panel.power;Layout.fillWidth:true;model:panel.optionalColumns;textRole:"name";valueRole:"id";accessibleLabel:"Benzersiz birim sütunu";onActivated:panel.invalidate()}
            UiLabel {visible:panel.analysis;text:panel.proportion?"Outcome · kişi başına0/1 event":"Outcome · sayısal ölçüm"}
            UiCombo {id:outcome;objectName:"experimentOutcome";visible:panel.analysis;Layout.fillWidth:true;model:panel.optionalColumns;textRole:"name";valueRole:"id";accessibleLabel:"Birincil outcome sütunu";onActivated:panel.invalidate()}
            UiLabel {visible:panel.analysis;text:"Özgün assigned arm · alınan tedavi değil"}
            UiCombo {id:arm;objectName:"experimentArm";visible:panel.analysis;Layout.fillWidth:true;model:panel.optionalColumns;textRole:"name";valueRole:"id";accessibleLabel:"Assigned arm sütunu";onActivated:panel.invalidate()}
            UiLabel {text:"Kontrol etiketi"}
            UiTextField {Accessible.name:placeholderText;id:controlLabel;objectName:"experimentControlLabel";Layout.fillWidth:true;placeholderText:"Kontrol etiketi";text:"A";onTextEdited:panel.invalidate()}
            UiLabel {text:"Tedavi etiketi"}
            UiTextField {Accessible.name:placeholderText;id:treatmentLabel;objectName:"experimentTreatmentLabel";Layout.fillWidth:true;placeholderText:"Tedavi etiketi";text:"B";onTextEdited:panel.invalidate()}
            UiLabel {visible:panel.analysis;text:"Analiz popülasyonu"}
            UiCombo {id:population;objectName:"experimentPopulation";visible:panel.analysis;Layout.fillWidth:true;model:[{id:"ITT",label:"ITT · assigned kola göre bütün birimler"},{id:"PP",label:"PP · açık protokol seçimi; association"}];textRole:"label";valueRole:"id";accessibleLabel:"ITT veya PP";onActivated:panel.invalidate()}
            UiLabel {visible:panel.analysis&&population.currentValue==="PP";text:"Protokole uygunluk · eksiksiz0/1"}
            UiCombo {id:protocol;objectName:"experimentProtocol";visible:panel.analysis&&population.currentValue==="PP";Layout.fillWidth:true;model:panel.optionalColumns;textRole:"name";valueRole:"id";accessibleLabel:"Protokol uygunluğu sütunu";onActivated:panel.invalidate()}
        }
        ColumnLayout {
            visible:panel.analysis;Layout.fillWidth:true
            UiLabel {text:"Baseline · önceden seçilen en fazla5 sayısal pretreatment sütun"}
            Repeater {model:statistics.columns;UiCheckBox {required property var modelData;text:modelData.name;checked:panel.baselineIds.indexOf(modelData.id)>=0;onToggled:{let a=panel.baselineIds.slice();if(checked&&a.indexOf(modelData.id)<0)a.push(modelData.id);if(!checked)a=a.filter(v=>v!==modelData.id);panel.baselineIds=a;panel.invalidate()}}}
            UiLabel {text:"Guardrail · en fazla5 betimsel ölçü; otomatik başarı kararı veya çoklu-test çıkarımı yok";Layout.fillWidth:true;wrapMode:Text.WordWrap}
            UiCombo {id:guardColumn;objectName:"experimentGuardColumn";Layout.fillWidth:true;model:panel.optionalColumns;textRole:"name";valueRole:"id";accessibleLabel:"Guardrail sütunu"}
            UiTextField {Accessible.name:placeholderText;id:guardName;objectName:"experimentGuardName";Layout.fillWidth:true;placeholderText:"Guardrail adı";text:"zarar ölçümü"}
            RowLayout {
                UiCombo {id:guardMetric;objectName:"experimentGuardMetric";model:[{id:"mean",label:"Ortalama"},{id:"proportion",label:"Oran0/1"}];textRole:"label";valueRole:"id";accessibleLabel:"Guardrail metriği"}
                UiCombo {id:guardDirection;objectName:"experimentGuardDirection";model:[{id:"increase",label:"Artış zararlı"},{id:"decrease",label:"Azalış zararlı"}];textRole:"label";valueRole:"id";accessibleLabel:"Guardrail zarar yönü"}
                UiTextField {Accessible.name:placeholderText;id:guardLimit;objectName:"experimentGuardLimit";placeholderText:"Mutlak zarar sınırı";text:"0.05";Layout.fillWidth:true}
                UiButton {objectName:"experimentGuardAdd";text:"Guardrail ekle";enabled:panel.guards.length<5&&!!guardColumn.currentValue;onClicked:{panel.guards=panel.guards.concat([{column_id:panel.key(guardColumn),name:guardName.text,metric:panel.key(guardMetric),limit:Number(guardLimit.text),direction:panel.key(guardDirection)}]);panel.invalidate()}}
            }
            UiLabel {text:panel.guards.map(g=>g.name+" · "+g.metric+" · sınır="+g.limit).join("; ");Layout.fillWidth:true;wrapMode:Text.WordWrap}
            UiButton {text:"Guardrail listesini temizle";onClicked:{panel.guards=[];panel.invalidate()}}
            UiTextField {Accessible.name:placeholderText;id:evidence;objectName:"experimentEvidence";Layout.fillWidth:true;placeholderText:"Gerçek randomizasyon plan/kanıt kimliği";onTextEdited:panel.invalidate()}
            UiCheckBox {id:randomized;objectName:"experimentRandomized";text:"Gerçek bağımsız Bernoulli randomizasyon tasarımını onaylıyorum; gözlemsel veriyi randomize saymıyorum";onToggled:panel.invalidate()}
            UiCheckBox {id:horizon;objectName:"experimentHorizon";text:"Önceden planlanan sabit ufuk ve ölçüm penceresi tamamlandı; peeking ile durdurmadım";onToggled:panel.invalidate()}
        }
        UiLabel {text:"Tam roster kapsamı zorunlu: outcome/PP sonrası filtre uygulanmaz. Oran paydası kişi sayısıdır; null sonuç0 sayılmaz.";Layout.fillWidth:true;wrapMode:Text.WordWrap}
        UiCheckBox {id:measurement;objectName:"experimentMeasurement";text:"Metrik/birim/ölçüm penceresi ve kolon rollerini doğruladım";onToggled:panel.invalidate()}
        UiCheckBox {id:independent;objectName:"experimentIndependent";text:"Bir satır bir bağımsız randomizasyon/analiz birimi; cluster/repeated yok";onToggled:panel.invalidate()}
        UiButton {objectName:"experimentPreflight";text:"Ölçüm planı ve roster önkontrol";enabled:!statistics.busy;onClicked:statistics.create(JSON.stringify(panel.spec()),true)}
        UiLabel {objectName:"experimentPreflightText";text:statistics.preflightResult.experiment?JSON.stringify(statistics.preflightResult,null,2):"Önkontrol çalıştırın";visible:statistics.preflightCurrent;Layout.fillWidth:true;wrapMode:Text.WordWrap}
        UiCheckBox {id:assumptions;objectName:"experimentAssumptions";text:"Önkontrol, missing, SRM ve fixed-horizon varsayımlarını inceledim";enabled:statistics.preflightCurrent}
        RowLayout {
            UiButton {objectName:"experimentRun";text:"Planı / deneyi hesapla";enabled:!statistics.busy&&assumptions.checked;onClicked:statistics.create(JSON.stringify(panel.spec()),false)}
            UiButton {objectName:"experimentCancel";text:"İptal";enabled:statistics.busy;onClicked:statistics.cancel()}
        }
        UiLabel {text:statistics.errorText;visible:!!statistics.errorText;Layout.fillWidth:true;wrapMode:Text.WordWrap;color:Theme.warning}
        UiLabel {objectName:"experimentResult";text:panel.resultText(statistics.analysisResult);visible:statistics.analysisResult.experiment===true;Layout.fillWidth:true;wrapMode:Text.WordWrap}
        RowLayout {
            Layout.fillWidth:true
            UiButton {objectName:"experimentSave";text:"Plan / sonuç / roster kaydet";enabled:statistics.current&&!statistics.busy&&statistics.analysisResult.experiment===true;onClicked:statistics.save()}
            UiTextField {Accessible.name:placeholderText;id:exportPath;objectName:"experimentExportPath";placeholderText:"Yeni mutlak export klasörü";Layout.fillWidth:true}
            UiButton {objectName:"experimentExport";text:"Plan / roster export";enabled:statistics.current&&!statistics.busy&&statistics.analysisResult.experiment===true;onClicked:statistics.exportAdvanced(exportPath.text)}
        }
        RowLayout {
            Layout.fillWidth:true
            UiCombo {id:saved;objectName:"experimentSaved";Layout.fillWidth:true;model:statistics.savedAnalyses.filter(v=>v.path==="experiments");textRole:"label";valueRole:"id";accessibleLabel:"Kayıtlı deney planı"}
            UiButton {objectName:"experimentOpen";text:"Kaydı aç";enabled:!!saved.currentValue&&!statistics.busy;onClicked:{statistics.openSaved(saved.currentValue);panel.restore(statistics.analysisResult.spec)}}
        }
    }
}
