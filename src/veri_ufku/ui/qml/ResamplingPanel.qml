import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"resamplingPanel"
    property bool expanded:expand.checked
    property string helpContext:"resampling"
    property string methodHelp:"statistics."+method.split("_").join("-")
    readonly property string method:methodChoice.currentValue||"bootstrap_percentile"
    readonly property bool family:method.indexOf("adjust_")===0
    readonly property bool paired:method==="paired_sign_flip"
    property bool restoring:false
    property var scenarioList:[]
    property var optionalColumns:[{id:"",name:"Seçin"}].concat(statistics.columns)
    signal helpRequested(var origin,string context)
    spacing:Theme.md
    function key(p){return p.currentValue||""}
    function number(v){return typeof v==="number"?Number(v).toPrecision(6):v===null||v===undefined?"sunulmuyor":String(v)}
    function invalidate(){if(restoring)return;assumptions.checked=false;statistics.invalidate()}
    function spec(){return {path:"resampling",method:method,x:key(x),y:paired?key(y):"",group:method==="permutation"?key(group):"",key:paired||family?key(person):"",before:before.text,after:after.text,resampling_unit:key(unitChoice),dependence:key(dependence),cluster:key(unitChoice)==="cluster"?key(cluster):"",time_column:key(unitChoice)==="time_block"?key(time):"",block_length:block.value,resamples:replicates.value,seed:seed.value,statistic:key(statisticChoice),trim_fraction:Number(trim.text),null_value:Number(nullValue.text),alternative:key(tail),exchangeability_confirmed:exchangeable.checked,symmetry_confirmed:symmetric.checked,missing_policy:complete.checked?"complete":"reject",missing_assumption:key(missingAssumption),outlier_policy:(method==="robust_summary"||method==="sensitivity")?key(outlier):"keep",family_name:family?familyName.text:"",family_ids:family?familyIds.text.split("\n").map(v=>v.trim()).filter(v=>v.length):[],family_dependence:key(familyDependence),scenarios:method==="sensitivity"?scenarioList:[],scope:full.checked?"full":"view",confidence:Number(confidence.currentValue),question:question.text,hypothesis:hypothesis.text,unit:measurementUnit.text,observation_unit:observation.text,independent:independent.checked,measurement_confirmed:measurement.checked,assumptions_confirmed:assumptions.checked}}
    function restore(s){
        if(!s||s.path!=="resampling"){expand.checked=false;return}
        restoring=true;expand.checked=true
        for(let i=0;i<methodChoice.model.length;i++)if(methodChoice.model[i].id===s.method)methodChoice.currentIndex=i
        for(let pair of [[x,s.x],[y,s.y],[group,s.group],[person,s.key],[cluster,s.cluster],[time,s.time_column],[unitChoice,s.resampling_unit],[dependence,s.dependence],[statisticChoice,s.statistic],[tail,s.alternative],[missingAssumption,s.missing_assumption],[outlier,s.outlier_policy],[familyDependence,s.family_dependence]])for(let i=0;i<pair[0].model.length;i++)if(pair[0].model[i].id===pair[1])pair[0].currentIndex=i
        question.text=s.question;hypothesis.text=s.hypothesis;measurementUnit.text=s.unit;observation.text=s.observation_unit;before.text=s.before;after.text=s.after;trim.text=String(s.trim_fraction);nullValue.text=String(s.null_value);block.value=s.block_length;replicates.value=s.resamples;seed.value=s.seed;confidence.currentIndex=[.95,.90,.99].indexOf(s.confidence);complete.checked=s.missing_policy==="complete";full.checked=s.scope==="full";familyName.text=s.family_name;familyIds.text=s.family_ids.join("\n");scenarioList=s.scenarios;exchangeable.checked=s.exchangeability_confirmed;symmetric.checked=s.symmetry_confirmed;measurement.checked=s.measurement_confirmed;independent.checked=s.independent;assumptions.checked=false;restoring=false
    }
    Connections {target:expertWorkspace;function onSelectMethod(path,name){if(path!=="resampling"){expand.checked=false;return}expand.checked=true;for(let i=0;i<methodChoice.model.length;i++)if(methodChoice.model[i].id===name)methodChoice.currentIndex=i}function onRestorePreset(value){panel.restore(JSON.parse(value))}}
    UiCheckBox {id:expand;objectName:"resamplingExpanded";text:"Faz41 · Resampling, sağlam ölçüler ve test ailesi";onToggled:panel.invalidate()}
    ColumnLayout {
        visible:panel.expanded;Layout.fillWidth:true;spacing:Theme.md
        UiLabel {Layout.fillWidth:true;wrapMode:Text.WordWrap;text:"Bağımlı ölçüm tek satır örneklenmez. Grup bütünlüğü ve zaman sırası açık seçilir. Exchangeability ve null hypothesis tasarım varsayımlarıdır; p-değeri nedensellik kanıtı değildir. Filtre/yöntem/aileyi p gördükten sonra seçmek p-hacking yaratır."}
        RowLayout {
            Layout.fillWidth:true
            UiCombo {id:methodChoice;objectName:"resamplingMethod";Layout.fillWidth:true;model:statistics.methods("resampling");textRole:"label";valueRole:"id";accessibleLabel:"Faz41 yöntem";onActivated:panel.invalidate()}
            UiButton {objectName:"resamplingHelp";text:"Yöntem yardımı";helpContext:panel.methodHelp;onClicked:panel.helpRequested(this,helpContext)}
            UiButton {text:"Resampling nedir?";helpContext:"resampling";onClicked:panel.helpRequested(this,helpContext)}
        }
        UiCombo {id:x;objectName:"resamplingX";Layout.fillWidth:true;model:statistics.columns;textRole:"name";valueRole:"id";accessibleLabel:panel.family?"Ham p-değeri sütunu":"Ölçüm / paired önce sütunu";onActivated:panel.invalidate()}
        GridLayout {
            Layout.fillWidth:true;columns:2
            UiLabel {text:"Bağımlılık tasarımı"}
            UiCombo {id:dependence;objectName:"resamplingDependence";Layout.fillWidth:true;model:[{id:"independent",label:"Bağımsız gözlemler"},{id:"grouped",label:"Grup içinde bağımlı"},{id:"temporal",label:"Zaman bağımlılığı"}];textRole:"label";valueRole:"id";accessibleLabel:"Bağımlılık tasarımı";onActivated:panel.invalidate()}
            UiLabel {text:"Resampling birimi"}
            UiCombo {id:unitChoice;objectName:"resamplingUnit";Layout.fillWidth:true;model:[{id:"observation",label:"Gözlem / bağımsız çift"},{id:"cluster",label:"Grup / cluster bütünü"},{id:"time_block",label:"Ardışık moving time block"}];textRole:"label";valueRole:"id";accessibleLabel:"Resampling birimi";onActivated:panel.invalidate()}
            UiLabel {visible:unitChoice.currentValue==="cluster";text:"Bağımsız cluster kimliği"}
            UiCombo {id:cluster;objectName:"resamplingCluster";visible:unitChoice.currentValue==="cluster";Layout.fillWidth:true;model:panel.optionalColumns;textRole:"name";valueRole:"id";accessibleLabel:"Cluster sütunu";onActivated:panel.invalidate()}
            UiLabel {visible:unitChoice.currentValue==="time_block";text:"Benzersiz zaman / sıra sütunu"}
            UiCombo {id:time;objectName:"resamplingTime";visible:unitChoice.currentValue==="time_block";Layout.fillWidth:true;model:panel.optionalColumns;textRole:"name";valueRole:"id";accessibleLabel:"Time block sıralama sütunu";onActivated:panel.invalidate()}
            UiLabel {visible:unitChoice.currentValue==="time_block";text:"Block uzunluğu · durağan seri varsayımı"}
            UiSpinBox {id:block;objectName:"resamplingBlock";visible:unitChoice.currentValue==="time_block";from:2;to:500;value:5;Accessible.name:"Moving block uzunluğu";onValueModified:panel.invalidate()}
            UiLabel {visible:panel.paired;text:"Paired sonra (after−before)"}
            UiCombo {id:y;objectName:"resamplingY";visible:panel.paired;Layout.fillWidth:true;model:panel.optionalColumns;textRole:"name";valueRole:"id";accessibleLabel:"Paired sonra ölçümü";onActivated:panel.invalidate()}
            UiLabel {visible:panel.paired||panel.family;text:panel.family?"Benzersiz testID":"Benzersiz kişi / pair key"}
            UiCombo {id:person;objectName:"resamplingKey";visible:panel.paired||panel.family;Layout.fillWidth:true;model:panel.optionalColumns;textRole:"name";valueRole:"id";accessibleLabel:"Test veya pair anahtarı";onActivated:panel.invalidate()}
            UiLabel {visible:panel.method==="permutation";text:"İki grup label sütunu"}
            UiCombo {id:group;objectName:"resamplingGroup";visible:panel.method==="permutation";Layout.fillWidth:true;model:panel.optionalColumns;textRole:"name";valueRole:"id";accessibleLabel:"Exchangeable grup labels";onActivated:panel.invalidate()}
        }
        RowLayout {visible:panel.method==="permutation";Layout.fillWidth:true
            UiTextField {id:before;objectName:"resamplingBefore";text:"A";placeholderText:"Before label";Accessible.name:placeholderText;onTextEdited:panel.invalidate()}
            UiTextField {id:after;objectName:"resamplingAfter";text:"B";placeholderText:"After label";Accessible.name:placeholderText;onTextEdited:panel.invalidate()}
        }
        UiLabel {visible:panel.method==="bootstrap_bca";Layout.fillWidth:true;wrapMode:Text.WordWrap;text:"BCa: bu adapterda yalnız gözlem/cluster mean; delete-one bağımsız birim jackknife. Median/trimmed/time-block BCa engellenir. Eksik/sabit dağılım veya kararsız tail için CI sunulmaz."}
        UiCheckBox {id:exchangeable;objectName:"resamplingExchangeable";visible:panel.method==="permutation"||panel.paired;text:"Null altında birimler exchangeable; label/sign dönüşümü tasarımla geçerli";onToggled:panel.invalidate()}
        UiCheckBox {id:symmetric;objectName:"resamplingSymmetric";visible:panel.paired;text:"Paired farklar null etrafında simetrik / işaretler randomize tasarımdan";onToggled:panel.invalidate()}
        RowLayout {Layout.fillWidth:true
            UiCombo {id:statisticChoice;objectName:"resamplingStatistic";model:[{id:"mean",label:"Mean"},{id:"median",label:"Median"},{id:"trimmed_mean",label:"Trimmed mean"}];textRole:"label";valueRole:"id";accessibleLabel:"Estimand / istatistik";onActivated:panel.invalidate()}
            UiTextField {id:trim;objectName:"resamplingTrim";text:"0.2";placeholderText:"Her tail trim0–0.4";Accessible.name:placeholderText;onTextEdited:panel.invalidate()}
            UiCombo {id:tail;objectName:"resamplingTail";model:[{id:"two-sided",label:"Two-sided |T|"},{id:"less",label:"Less"},{id:"greater",label:"Greater"}];textRole:"label";valueRole:"id";accessibleLabel:"Null test tail";onActivated:panel.invalidate()}
            UiTextField {id:nullValue;objectName:"resamplingNull";text:"0";placeholderText:"Null değeri (paired fark)";Accessible.name:placeholderText;onTextEdited:panel.invalidate()}
        }
        RowLayout {
            UiSpinBox {id:seed;objectName:"resamplingSeed";from:0;to:2147483647;value:42;Accessible.name:"PCG64 seed";onValueModified:panel.invalidate()}
            UiSpinBox {id:replicates;objectName:"resamplingReplicates";from:100;to:10000;value:1000;Accessible.name:"Monte Carlo / bootstrap tekrar sayısı";onValueModified:panel.invalidate()}
            UiCombo {id:confidence;objectName:"resamplingConfidence";model:[{id:.95,label:"%95 CI / alpha .05"},{id:.90,label:"%90 CI / alpha .10"},{id:.99,label:"%99 CI / alpha .01"}];textRole:"label";valueRole:"id";accessibleLabel:"Güven düzeyi / aile alpha";onActivated:panel.invalidate()}
        }
        UiLabel {Layout.fillWidth:true;wrapMode:Text.WordWrap;text:"En fazla2000 satır ve2000000 satır×tekrar. Küçük null uzayı≤10000 exhaustive hesaplanır; aksi durumda Monte Carlo +1 p ve belirsizliği. Cluster bootstrap pooled row estimand; cluster permütasyon eşit ağırlıklı cluster mean farkıdır."}
        RowLayout {
            UiCheckBox {id:complete;objectName:"resamplingComplete";text:"Complete-case açık dışlama";onToggled:panel.invalidate()}
            UiCheckBox {id:full;objectName:"resamplingFull";text:"Tam dataset (görünüm filtresi yerine)";onToggled:panel.invalidate()}
            UiCombo {id:missingAssumption;objectName:"resamplingMissingAssumption";model:[{id:"MAR",label:"MAR varsayımı"},{id:"MCAR",label:"MCAR varsayımı"},{id:"MNAR",label:"MNAR varsayımı"}];textRole:"label";valueRole:"id";accessibleLabel:"Eksik veri mekanizması varsayımı";onActivated:panel.invalidate()}
        }
        UiLabel {Layout.fillWidth:true;wrapMode:Text.WordWrap;text:"Cluster/time ölçümlerinde eksik satır düşürülmez: cluster bütünlüğü veya zaman bitişikliği bozulur. Önceden belirlenmiş eksiksiz kapsam seçin; mekanizma otomatik bulunmaz."}
        UiCombo {id:outlier;objectName:"resamplingOutlier";visible:panel.method==="robust_summary"||panel.method==="sensitivity";Layout.fillWidth:true;model:[{id:"keep",label:"Outlier tut"},{id:"mad_exclude",label:"|x−median| >3×1.4826×MAD dışla (MAD0 ret)"},{id:"winsorize",label:"Trim quantile sınırında winsorize"}];textRole:"label";valueRole:"id";accessibleLabel:"Açık outlier politikası";onActivated:panel.invalidate()}
        ColumnLayout {visible:panel.family;Layout.fillWidth:true
            UiTextField {id:familyName;objectName:"resamplingFamilyName";Layout.fillWidth:true;placeholderText:"Önceden belirlenen test ailesinin adı";Accessible.name:placeholderText;onTextEdited:panel.invalidate()}
            UiTextArea {id:familyIds;objectName:"resamplingFamilyIds";Layout.fillWidth:true;placeholderText:"Seçili testID'ler · her satırda bir kimlik";Accessible.name:placeholderText;onTextChanged:panel.invalidate()}
            UiCombo {id:familyDependence;objectName:"resamplingFamilyDependence";Layout.fillWidth:true;model:[{id:"arbitrary",label:"Keyfi bağımlılık (Holm/Bonferroni)"},{id:"independent",label:"Bağımsız testler (BH uygun)"},{id:"positive",label:"Pozitif bağımlılık / PRDS (BH uygun)"}];textRole:"label";valueRole:"id";accessibleLabel:"Test ailesi bağımlılık varsayımı";onActivated:panel.invalidate()}
            UiLabel {Layout.fillWidth:true;wrapMode:Text.WordWrap;text:"FWER: ailede en az1 yanlış ret olasılığını kontrol eder. BH/FDR: retler içindeki beklenen yanlış keşif oranı; bağımsız/PRDS varsayımı gerekir. Aile p görüldükten sonra küçültülmemeli; özgün p'ler ve seçilen tüm kimlikler exportta korunur."}
        }
        ColumnLayout {visible:panel.method==="sensitivity";Layout.fillWidth:true
            UiLabel {Layout.fillWidth:true;wrapMode:Text.WordWrap;text:"Önceden belirlenmiş senaryolar: alternatif filtre + robust ölçü + outlier + missing/delta. Betimsel değişimdir; yeni p araması veya otomatik nedensel çıkarım değildir. Delta missing değeri observed mean+delta kabul eder, çoklu imputasyon değildir."}
            UiTextField {id:scenarioName;objectName:"resamplingScenarioName";Layout.fillWidth:true;placeholderText:"Senaryo adı";Accessible.name:placeholderText}
            RowLayout {Layout.fillWidth:true
                UiCombo {id:scenarioColumn;objectName:"resamplingScenarioColumn";Layout.fillWidth:true;model:panel.optionalColumns;textRole:"name";valueRole:"id";accessibleLabel:"Senaryo ek filtre sütunu (yok ise aynı kapsam)"}
                UiCombo {id:scenarioOperator;model:[{id:"gt",label:">"},{id:"lt",label:"<"},{id:"eq",label:"="},{id:"ne",label:"≠"}];textRole:"label";valueRole:"id";accessibleLabel:"Senaryo filtre operator"}
                UiTextField {id:scenarioValue;objectName:"resamplingScenarioValue";placeholderText:"Fiziksel filtre değeri";Accessible.name:placeholderText}
            }
            RowLayout {Layout.fillWidth:true
                UiCombo {id:scenarioStatistic;objectName:"resamplingScenarioStatistic";model:statisticChoice.model;textRole:"label";valueRole:"id";accessibleLabel:"Senaryo alternatif ölçü"}
                UiCombo {id:scenarioOutlier;objectName:"resamplingScenarioOutlier";model:outlier.model;textRole:"label";valueRole:"id";accessibleLabel:"Senaryo outlier politikası"}
                UiCombo {id:scenarioMissing;objectName:"resamplingScenarioMissing";model:[{id:"complete",label:"Complete-case"},{id:"reject",label:"Missing ret"},{id:"delta",label:"Observed mean+delta missing duyarlılığı"}];textRole:"label";valueRole:"id";accessibleLabel:"Senaryo missing politikası"}
            }
            RowLayout {
                UiCombo {id:scenarioAssumption;objectName:"resamplingScenarioAssumption";model:missingAssumption.model;textRole:"label";valueRole:"id";accessibleLabel:"Senaryo missing varsayımı"}
                UiTextField {id:scenarioDelta;objectName:"resamplingScenarioDelta";text:"0";placeholderText:"Missing delta";Accessible.name:placeholderText}
                UiButton {objectName:"resamplingAddScenario";text:"Senaryoyu ekle";onClicked:{let v=JSON.parse(JSON.stringify(statistics.viewSpec));if(!v)v={};if(panel.key(scenarioColumn)){if(!v.filters)v.filters=[];v.filters.push({column_id:panel.key(scenarioColumn),operator:panel.key(scenarioOperator),value:scenarioValue.text})}panel.scenarioList=panel.scenarioList.concat([{name:scenarioName.text,view:v,statistic:panel.key(scenarioStatistic),outlier_policy:panel.key(scenarioOutlier),missing_policy:panel.key(scenarioMissing),missing_assumption:panel.key(scenarioAssumption),missing_delta:Number(scenarioDelta.text)}]);panel.invalidate()}}
                UiButton {text:"Senaryoları temizle";onClicked:{panel.scenarioList=[];panel.invalidate()}}
            }
            Repeater {model:panel.scenarioList;delegate:UiLabel {required property var modelData;Layout.fillWidth:true;wrapMode:Text.WordWrap;text:modelData.name+" · "+modelData.statistic+" · "+modelData.outlier_policy+" · "+modelData.missing_policy+" / "+modelData.missing_assumption+" · delta="+modelData.missing_delta+" · filtre="+JSON.stringify(modelData.view.filters||[])}}
        }
        UiTextField {id:question;objectName:"resamplingQuestion";Layout.fillWidth:true;placeholderText:"Araştırma sorusu / önceden belirlenmiş plan";Accessible.name:placeholderText;onTextEdited:panel.invalidate()}
        UiTextField {id:hypothesis;objectName:"resamplingHypothesis";Layout.fillWidth:true;placeholderText:"Null hypothesis / estimand";Accessible.name:placeholderText;onTextEdited:panel.invalidate()}
        UiTextField {id:measurementUnit;objectName:"resamplingMeasurementUnit";Layout.fillWidth:true;placeholderText:"Ölçüm birimi";Accessible.name:placeholderText;onTextEdited:panel.invalidate()}
        UiTextField {id:observation;objectName:"resamplingObservation";Layout.fillWidth:true;placeholderText:"Bağımsız gözlem / cluster / zaman block açıklaması";Accessible.name:placeholderText;onTextEdited:panel.invalidate()}
        UiCheckBox {id:measurement;objectName:"resamplingMeasurement";text:"Ölçümü, hipotezi ve resampling birimini doğruladım";onToggled:panel.invalidate()}
        UiCheckBox {id:independent;objectName:"resamplingIndependent";text:"Seçili resampling birimleri için bağımsızlık / zaman seri varsayımını doğruladım";onToggled:panel.invalidate()}
        RowLayout {
            UiButton {objectName:"resamplingPreflight";text:"Birim / kapsam önkontrol";enabled:!statistics.busy;onClicked:statistics.create(JSON.stringify(panel.spec()),true)}
            UiCheckBox {id:assumptions;objectName:"resamplingAssumptions";text:"Önkontrol / varsayımları inceledim";enabled:statistics.preflightCurrent}
            UiButton {objectName:"resamplingRun";text:"Hesapla";enabled:!statistics.busy&&statistics.preflightCurrent&&assumptions.checked;onClicked:statistics.create(JSON.stringify(panel.spec()),false)}
            UiButton {objectName:"resamplingCancel";text:"İptal";enabled:statistics.busy;onClicked:statistics.cancel()}
        }
        UiLabel {objectName:"resamplingPreflightText";Layout.fillWidth:true;wrapMode:Text.WordWrap;text:statistics.preflightCurrent?"Birim="+statistics.preflightResult.resampling_unit+" · birim sayısı="+statistics.preflightResult.unit_count+" · kullanılan n="+statistics.preflightResult.used_rows+" · missing dışlanan="+statistics.preflightResult.excluded_rows+"\n"+(statistics.preflightResult.warnings||[]).join("\n"):"Güncel birim/kapsam önkontrolü gerekli."}
        UiLabel {Layout.fillWidth:true;wrapMode:Text.WordWrap;text:statistics.errorText||statistics.message}
        ColumnLayout {
            visible:!!statistics.analysisResult.spec&&statistics.analysisResult.spec.path==="resampling";Layout.fillWidth:true
            UiLabel {objectName:"resamplingStatus";Layout.fillWidth:true;wrapMode:Text.WordWrap;text:statistics.current?"Güncel dataset / filtre / tarif sonucu":"ESKİ veya farklı dataset/filtre/tarif sonucu; yeniden hesaplayın"}
            UiLabel {objectName:"resamplingResult";Layout.fillWidth:true;wrapMode:Text.WordWrap;text:panel.resultText(statistics.analysisResult)}
            Repeater {model:statistics.analysisResult.family?statistics.analysisResult.family.tests:[];delegate:UiLabel {required property var modelData;Layout.fillWidth:true;wrapMode:Text.WordWrap;text:modelData.test_id+" · raw p="+panel.number(modelData.p_raw)+" · adjusted p="+panel.number(modelData.p_adjusted)+" · ret="+modelData.reject}}
            Repeater {model:statistics.analysisResult.sensitivity||[];delegate:UiLabel {required property var modelData;Layout.fillWidth:true;wrapMode:Text.WordWrap;text:modelData.name+" · sonuç="+panel.number(modelData.estimate)+" · değişim="+panel.number(modelData.change)+" · n="+modelData.n+" · missing="+modelData.missing+" · imputed="+modelData.imputed+" · "+modelData.status}}
            RowLayout {
                UiButton {objectName:"resamplingSave";text:"Sonuç / birim kimliklerini kaydet";enabled:statistics.current&&!statistics.busy&&!projects.readOnly;onClicked:statistics.save()}
                UiTextField {id:destination;objectName:"resamplingExportPath";Layout.fillWidth:true;placeholderText:"Var olmayan mutlak export klasörü";Accessible.name:placeholderText}
                UiButton {objectName:"resamplingExport";text:"Aile / tarif / dağılım export";enabled:statistics.current&&!statistics.busy;onClicked:statistics.exportAdvanced(destination.text)}
            }
        }
        RowLayout {
            UiCombo {id:saved;objectName:"resamplingSaved";Layout.fillWidth:true;model:statistics.savedAnalyses.filter(r=>r.path==="resampling");textRole:"label";valueRole:"id";accessibleLabel:"Kaydedilen resampling/aile sonucu"}
            UiButton {objectName:"resamplingOpen";text:"Kaydı aç";onClicked:{statistics.openSaved(panel.key(saved));panel.restore(statistics.analysisResult.spec)}}
        }
    }
    function resultText(r){
        if(!r.resampling)return ""
        let lines=[r.method_label+" · seed="+r.seed+(r.bootstrap||r.permutation?" · istenen tekrar="+r.requested_replicates:" (uygulanmadı) · deterministik hesap, resampling tekrarı yok")+" · birim="+r.resampling_unit,"Null: "+r.null_hypothesis+" · tail="+r.tail]
        if(r.bootstrap){let b=r.bootstrap,c=b.confidence_interval;lines.push("Tahmin="+number(b.estimate)+" · bootstrap SD="+number(b.bootstrap_sd)+" · "+b.estimand);lines.push(c.method+" CI ["+number(c.low)+", "+number(c.high)+"] · "+c.status);if(c.monte_carlo)lines.push("MC endpoint belirsizliği: "+c.monte_carlo.endpoint_bands.map(v=>"["+number(v.low)+", "+number(v.high)+"]").join(" / "))}
        if(r.permutation){let p=r.permutation;lines.push("Etki="+number(p.estimate)+" · p="+number(p.p_value)+" · "+(p.exact?"exhaustive":"Monte Carlo")+" · yapılan="+p.performed+" · "+p.estimand);if(p.monte_carlo)lines.push("MC exceedance probability %95 aralığı ["+number(p.monte_carlo.low)+", "+number(p.monte_carlo.high)+"] · resolution="+number(p.monte_carlo.p_resolution))}
        if(r.summary){let s=r.summary;lines.push("Mean="+number(s.mean)+" · median="+number(s.median)+" · trimmed mean="+number(s.trimmed_mean)+" · raw MAD="+number(s.mad)+" · outlier="+s.outlier_policy+" · dışlanan="+s.outlier_removed+" · inference yok")}
        if(r.family)lines.push("Aile: "+r.family.name+" · seçili test="+r.family.size+" · "+r.family.method+" · "+(r.family.method==="bh"?"FDR: retler içindeki beklenen yanlış keşif oranı; bağımsızlık/PRDS gerekli":"FWER: ailede en az1 yanlış ret olasılığı; keyfi bağımlılık uygun")+" · alpha="+number(r.family.alpha))
        return lines.concat(r.warnings||[]).join("\n")
    }
}
