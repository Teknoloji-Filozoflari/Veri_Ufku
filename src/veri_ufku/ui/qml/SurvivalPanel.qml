import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"survivalPanel"
    property string helpContext:"survival"
    property bool expanded:expand.checked
    property bool restoring:false
    property var features:[]
    property var columns:[{id:"",name:"Seçin"}].concat(statistics.columns)
    readonly property string method:methodChoice.currentValue||"survival_km"
    readonly property bool modelMethod:method==="survival_cox"||method==="survival_aft"
    signal helpRequested(var origin,string context)
    spacing:Theme.md
    function invalidate(){if(!restoring){assumptions.checked=false;statistics.invalidate()}}
    function numbers(text){return text.trim()?text.split(",").map(Number):[]}
    function plan(){return {censoring:censoring.currentValue||"right",entry:entry.currentValue||"",ties:ties.currentText,event_definition:eventDefinition.text,origin:origin.text,censoring_assumption:censorReason.text,unit_confirmation:sameUnit.checked,cause_labels:method==="survival_cif"?JSON.parse(causeLabels.text):({}),risk_times:numbers(riskTimes.text),prediction_times:numbers(predTimes.text),prediction_profile:modelMethod?numbers(profile.text):[],prediction_group:method==="survival_cox"?predGroup.text:""}}
    function spec(){return {path:"survival",method:method,x:duration.currentValue||"",y:event.currentValue||"",key:person.currentValue||"",group:group.currentValue||"",features:modelMethod?features:[],question:question.text,unit:unit.currentText,observation_unit:observation.text,scope:"full",confidence:Number(level.text),max_iterations:iterations.value,survival_plan:plan(),measurement_confirmed:measurement.checked,independent:independent.checked,assumptions_confirmed:assumptions.checked}}
    function run(preflight){try{statistics.create(JSON.stringify(spec()),preflight);formError.text=""}catch(e){formError.text="Cause kodları geçerli JSON olmalı; veri korunuyor."}}
    function number(v){return typeof v==="number"?Number(v).toPrecision(5):"sunulmuyor"}
    function label(id){let c=panel.columns.find(c=>c.id===id);return c?c.name:id}
    function describe(r){
        if(!r||!r.survival)return ""
        let a=r.survival_analysis,lines=[r.result_version?(statistics.current?"Güncel veri / censoring / model tarifi":"ESKİ VERİ/TARİF · save/export/prediction kapalı"):"Önkontrol · henüz kalıcı sonuç değil",r.method_label+" · kayıt/birim="+r.used_rows+" · event="+a.events+" · censored="+a.censored+" · dışlanan=0", "Durum: "+a.status,"Censoring: "+r.plan.censoring+" · birim="+(r.spec?r.spec.unit:unit.currentText)+" · origin="+r.plan.origin,"Maliyet: "+JSON.stringify(r.budget),"Event tanımı: "+r.plan.event_definition,"Censoring varsayımı: "+r.plan.censoring_assumption]
        if(a.logrank)lines.push("Log-rank χ²="+number(a.logrank.statistic)+" · df="+a.logrank.df+" · p="+number(a.logrank.p_value),a.logrank.limitations)
        for(let c of a.coefficients)lines.push((c.parameter==="intercept"?c.parameter:label(c.parameter))+" · beta="+number(c.beta)+" · SE="+number(c.se)+" · ratio="+number(c.ratio)+" · %"+Math.round(c.confidence*100)+"CI="+c.ratio_interval.map(number).join(" / ")+" · "+c.ratio_meaning)
        if(a.model)lines.push("Model: "+a.model.kind+" · score max="+number(a.model.score_max)+" · "+a.model.inference,"Prediction/persistence: safe numeric JSON; support="+JSON.stringify(a.model.training_support)+" · "+(a.model.prediction_allowed?"conditional profile prediction":"KAPALI · "+a.model.prediction_limit))
        if(a.diagnostics.failure)lines.push("TANI BAŞARISIZ · "+a.diagnostics.failure)
        if(a.diagnostics.ph)lines.push("PH tanısı: "+a.diagnostics.ph.status+" · "+a.diagnostics.ph.interpretation,"Schoenfeld log-time trend: "+a.diagnostics.ph.trend.map(v=>label(v.column_id)+" rho="+number(v.spearman_logtime)+(v.large_trend_flag?" · UYARI":"")).join(" / "),a.diagnostics.ph.method)
        lines.push("Ties/event kontrolü: "+JSON.stringify({ties:a.diagnostics.ties,event_min:a.diagnostics.minimum_events,tied_events:a.diagnostics.tied_event_times}),"C-index: "+JSON.stringify(a.metrics.c_index),"Brier/AUC KAPALI · "+a.metrics.time_dependent_brier.reason,"Prediction: "+JSON.stringify(a.prediction),a.interpretation||"",a.warnings.join("\n"))
        return lines.filter(x=>x).join("\n\n")
    }
    function restore(s){
        if(!s||s.path!=="survival"){expand.checked=false;return}
        restoring=true;expand.checked=true
        let p=s.survival_plan
        for(let pair of [[methodChoice,s.method],[duration,s.x],[event,s.y],[person,s.key],[entry,p.entry],[group,s.group],[censoring,p.censoring]])for(let i=0;i<pair[0].model.length;i++)if(pair[0].model[i].id===pair[1])pair[0].currentIndex=i
        for(let pair of [[question,s.question],[observation,s.observation_unit],[eventDefinition,p.event_definition],[origin,p.origin],[censorReason,p.censoring_assumption],[riskTimes,p.risk_times.join(",")],[predTimes,p.prediction_times.join(",")],[profile,p.prediction_profile.join(",")],[predGroup,p.prediction_group],[causeLabels,JSON.stringify(p.cause_labels)],[level,s.confidence]])pair[0].text=String(pair[1])
        unit.currentIndex=unit.model.indexOf(s.unit);ties.currentIndex=ties.model.indexOf(p.ties);features=s.features;iterations.value=s.max_iterations;sameUnit.checked=p.unit_confirmation;measurement.checked=s.measurement_confirmed;independent.checked=s.independent;assumptions.checked=false;restoring=false
    }
    Connections {target:expertWorkspace;function onSelectMethod(path,name){if(path!=="survival"){expand.checked=false;return}expand.checked=true;for(let i=0;i<methodChoice.model.length;i++)if(methodChoice.model[i].id===name)methodChoice.currentIndex=i;panel.invalidate()}function onRestorePreset(value){panel.restore(JSON.parse(value))}}
    UiCheckBox {id:expand;objectName:"survivalExpanded";text:"45 · Sağkalım / olay zamanı / risk set"}
    ColumnLayout {
        visible:panel.expanded;Layout.fillWidth:true;spacing:Theme.md
        RowLayout {
            Layout.fillWidth:true
            UiCombo {id:methodChoice;objectName:"survivalMethod";model:statistics.methods("survival");textRole:"label";valueRole:"id";accessibleLabel:"Sağkalım yöntem/backend";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiButton { visible: false;objectName:"survivalHelp";text:"Bu ne işe yarar?";helpContext:"survival";onClicked:panel.helpRequested(this,"statistics."+panel.method.split("_").join("-"))}
        }
        UiLabel {text:"Censored0 bilinen son takip: null/kayıp veri değildir. Event1 gerçekleşti; competing risks tüm cause kodları ayrı. HR event probability değildir;1−KM her cause için incidence değildir. Statik baseline covariate/tek unit satırı; tam veri sürümü.";wrapMode:Text.WordWrap;Layout.fillWidth:true}
        UiLabel {objectName:"survivalSupport";text:"Backend desteği: KM/log-rank/Cox right + left truncation; AFT log-normal yalnız right; CIF competing_right, entry yok. Interval/left censoring KAPALI. Time-dependent covariate SurvivalCountingProcess/v1 şema doğrulaması ayrı; fit/prediction KAPALI. IPCW Brier/time-AUC KAPALI. Delayed-entry/strata C-index ve delayed-entry survival prediction KAPALI.";wrapMode:Text.WordWrap;Layout.fillWidth:true;color:Theme.warning}
        GridLayout {
            columns:2;Layout.fillWidth:true
            UiLabel {text:"Duration"}
            UiCombo {id:duration;objectName:"survivalDuration";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Duration";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Event0censored/1event veya CIF1..K"}
            UiCombo {id:event;objectName:"survivalEvent";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Event0censored/1event veya CIF1..K";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Bağımsız unit kimliği"}
            UiCombo {id:person;objectName:"survivalPerson";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Bağımsız unit kimliği";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Entry (yalnız left truncation)"}
            UiCombo {id:entry;objectName:"survivalEntry";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Entry (yalnız left truncation)";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Group / Cox strata (isteğe bağlı)"}
            UiCombo {id:group;objectName:"survivalGroup";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Group / Cox strata (isteğe bağlı)";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Censoring"}
            UiCombo {id:censoring;objectName:"survivalCensoring";model:[{id:"right",name:"Right censoring · event0/1"},{id:"left_truncated_right",name:"Left truncation + right · KM/logrank/Cox"},{id:"competing_right",name:"Competing right · yalnız CIF"},{id:"interval",name:"KAPALI · interval censoring"},{id:"left",name:"KAPALI · left censoring"}];textRole:"name";valueRole:"id";accessibleLabel:"Censoring türü; desteklenmeyen seçenek hata verir";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Zaman birimi"}
            UiCombo {id:unit;objectName:"survivalUnit";model:["second","minute","hour","day","week","year"];currentIndex:3;accessibleLabel:"Duration/entry ortak zaman birimi";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Cox ties"}
            UiCombo {id:ties;objectName:"survivalTies";model:["breslow","efron"];accessibleLabel:"Cox tied event approximation";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Soru"}
            UiTextField {id:question;objectName:"survivalQuestion";Accessible.name:"Soru";placeholderText:"Soru";text:"Olay gerçekleşmeden survival ne kadar?";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Bağımsız analiz birimi"}
            UiTextField {id:observation;objectName:"survivalObservation";Accessible.name:"Bağımsız analiz birimi";placeholderText:"Bağımsız analiz birimi";text:"kişi";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Event / censoring kod tanımı"}
            UiTextField {id:eventDefinition;objectName:"survivalEventDefinition";Accessible.name:"Event / censoring kod tanımı";placeholderText:"Event / censoring kod tanımı";text:"";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Ortak zaman başlangıcı"}
            UiTextField {id:origin;objectName:"survivalOrigin";Accessible.name:"Ortak zaman başlangıcı";placeholderText:"Ortak zaman başlangıcı";text:"";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Independent censoring/truncation gerekçesi"}
            UiTextField {id:censorReason;objectName:"survivalCensorReason";Accessible.name:"Independent censoring/truncation gerekçesi";placeholderText:"Independent censoring/truncation gerekçesi";text:"";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"CIF cause etiketleri (JSON)"}
            UiTextField {id:causeLabels;objectName:"survivalCauseLabels";Accessible.name:"CIF cause etiketleri (JSON)";placeholderText:"CIF cause etiketleri (JSON)";text:"{\"1\":\"hedef olay\",\"2\":\"diğer olay\"}";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Risk table zamanları (virgüllü)"}
            UiTextField {id:riskTimes;objectName:"survivalRiskTimes";Accessible.name:"Risk table zamanları (virgüllü)";placeholderText:"Risk table zamanları (virgüllü)";text:"0,1,2,3";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Prediction zamanları (virgüllü)"}
            UiTextField {id:predTimes;objectName:"survivalPredTimes";Accessible.name:"Prediction zamanları (virgüllü)";placeholderText:"Prediction zamanları (virgüllü)";text:"0,1,2,3";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Baseline prediction profili (predictor sırası)"}
            UiTextField {id:profile;objectName:"survivalProfile";Accessible.name:"Baseline prediction profili (predictor sırası)";placeholderText:"Baseline prediction profili (predictor sırası)";text:"";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Cox prediction strata etiketi"}
            UiTextField {id:predGroup;objectName:"survivalPredGroup";Accessible.name:"Cox prediction strata etiketi";placeholderText:"Cox prediction strata etiketi";text:"";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Pointwise/Wald CI düzeyi"}
            UiTextField {id:level;objectName:"survivalLevel";Accessible.name:"Pointwise/Wald CI düzeyi";placeholderText:"Pointwise/Wald CI düzeyi";text:"0.95";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Maksimum fit iterations"}
            UiSpinBox {id:iterations;objectName:"survivalIterations";from:20;to:300;value:100;Accessible.name:"Sağkalım fit iteration bütçesi";onValueModified:panel.invalidate()}
        }
        RowLayout {
            visible:panel.modelMethod;Layout.fillWidth:true
            UiCombo {id:predictor;objectName:"survivalPredictor";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Baseline sayısal predictor";Layout.fillWidth:true}
            UiButton {objectName:"survivalAddPredictor";text:"Predictor ekle";onClicked:{if(predictor.currentValue&&!panel.features.includes(predictor.currentValue)){panel.features=panel.features.concat([predictor.currentValue]);panel.invalidate()}}}
            UiButton {text:"Predictor temizle";onClicked:{panel.features=[];panel.invalidate()}}
        }
        UiLabel {text:"Predictor sırası: "+panel.features.map(panel.label).join(", ");wrapMode:Text.WordWrap;Layout.fillWidth:true}
        UiCheckBox {id:sameUnit;objectName:"survivalSameUnit";text:"Duration, entry ve bütün zamanlar aynı seçili birimde; ortak origin doğrulandı";onToggled:panel.invalidate()}
        UiCheckBox {id:measurement;objectName:"survivalMeasurement";text:"Event kodları, takip penceresi ve baseline ölçüm zamanı doğrulandı";onToggled:panel.invalidate()}
        UiCheckBox {id:independent;objectName:"survivalIndependent";text:"Bir unit/bir satır; bağımsız subjects, group strata cluster değildir";onToggled:panel.invalidate()}
        UiButton {objectName:"survivalPreflight";text:"Censoring / risk / tanı / maliyet önkontrolü";enabled:!statistics.busy;onClicked:panel.run(true)}
        UiLabel {objectName:"survivalPreview";visible:statistics.preflightCurrent&&statistics.preflightResult.survival===true;text:panel.describe(statistics.preflightResult);Layout.fillWidth:true;wrapMode:Text.WordWrap}
        UiCheckBox {id:assumptions;objectName:"survivalAssumptions";text:"Risk set, independent censoring, PH/AFT koşulları ve kapalı yetenekleri inceledim";enabled:statistics.preflightCurrent}
        RowLayout {
            UiButton {objectName:"survivalRun";text:"Sağkalım raporunu hesapla";enabled:!statistics.busy&&assumptions.checked;onClicked:panel.run(false)}
            UiButton {objectName:"survivalCancel";text:"İptal";enabled:statistics.busy;onClicked:statistics.cancel()}
        }
        UiLabel {id:formError;objectName:"survivalFormError";color:Theme.warning;wrapMode:Text.WordWrap;Layout.fillWidth:true}
        UiLabel {text:statistics.message;wrapMode:Text.WordWrap;Layout.fillWidth:true}
        UiLabel {objectName:"survivalError";text:statistics.errorText;visible:!!statistics.errorText;color:Theme.warning;wrapMode:Text.WordWrap;Layout.fillWidth:true}
        UiLabel {objectName:"survivalResult";visible:statistics.analysisResult.survival===true;text:panel.describe(statistics.analysisResult);wrapMode:Text.WordWrap;Layout.fillWidth:true}
        Image {objectName:"survivalCurve";visible:statistics.analysisResult.survival===true&&!!statistics.modelDiagnostic;source:statistics.analysisResult.survival?statistics.modelDiagnostic:"";Layout.fillWidth:true;Layout.preferredHeight:440;fillMode:Image.PreserveAspectFit}
        ColumnLayout {
            objectName:"survivalRiskTable";visible:statistics.analysisResult.survival===true;Layout.fillWidth:true
            UiLabel {text:"Risk table · hemen önce risk altında / o anda event / o anda censored"}
            Repeater {
                model:statistics.analysisResult.survival?statistics.analysisResult.survival_analysis.risk_tables:[]
                ColumnLayout {
                    required property var modelData;Layout.fillWidth:true
                    UiLabel {text:"Grup: "+modelData.group+" · n="+modelData.rows}
                    Repeater {
                        model:modelData.risk_table
                        UiLabel {required property var modelData;text:"t="+modelData.time+" · risk="+modelData.at_risk+" · event="+modelData.events_at_time+" · censored="+modelData.censored_at_time+" · henüz girmeyen="+modelData.not_yet_entered+" · "+modelData.risk_convention;wrapMode:Text.WordWrap;Layout.fillWidth:true}
                    }
                }
            }
        }
        UiLabel {text:"Safe model reuse · sadece güncel hash doğrulanmış model; takip desteği dışına extrapolation yok. Prediction CI ve bireysel prognosis doğrulaması yok.";wrapMode:Text.WordWrap;Layout.fillWidth:true}
        RowLayout {
            Layout.fillWidth:true
            UiTextField {id:reuseProfile;objectName:"survivalReuseProfile";text:"[0]";Accessible.name:"Safe model predictor profili JSON";Layout.fillWidth:true}
            UiTextField {id:reuseTimes;objectName:"survivalReuseTimes";text:"[0,1,2,3]";Accessible.name:"Safe model prediction zamanları JSON";Layout.fillWidth:true}
            UiTextField {id:reuseGroup;objectName:"survivalReuseGroup";Accessible.name:"Safe model prediction strata etiketi";Layout.fillWidth:true}
            UiButton {objectName:"survivalPredict";text:"Modelden S(t)";enabled:statistics.current&&!statistics.busy&&statistics.analysisResult.survival===true&&!!statistics.analysisResult.survival_analysis.model;onClicked:statistics.predictSurvival(reuseProfile.text,reuseTimes.text,reuseGroup.text)}
        }
        UiLabel {objectName:"survivalPrediction";text:JSON.stringify(statistics.survivalPrediction);wrapMode:Text.WordWrap;Layout.fillWidth:true}
        RowLayout {
            Layout.fillWidth:true
            UiButton {objectName:"survivalSave";text:"Risk / model / tanılarla kaydet";enabled:statistics.current&&!statistics.busy&&statistics.analysisResult.survival===true;onClicked:statistics.save()}
            UiTextField {id:exportPath;objectName:"survivalExportPath";Accessible.name:placeholderText;placeholderText:"Yeni mutlak export klasörü";Layout.fillWidth:true}
            UiButton {objectName:"survivalExport";text:"JSON / PNG / RowId export";enabled:statistics.current&&!statistics.busy&&statistics.analysisResult.survival===true;onClicked:statistics.exportAdvanced(exportPath.text)}
        }
        RowLayout {
            Layout.fillWidth:true
            UiCombo {id:saved;objectName:"survivalSaved";model:statistics.savedAnalyses.filter(v=>v.path==="survival");textRole:"label";valueRole:"id";accessibleLabel:"Kayıtlı sağkalım raporu/modeli";Layout.fillWidth:true}
            UiButton {objectName:"survivalOpen";text:"Kaydı/modeli aç";enabled:!!saved.currentValue&&!statistics.busy;onClicked:{statistics.openSaved(saved.currentValue);panel.restore(statistics.analysisResult.spec)}}
        }
    }
}
