import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"bayesPanel"
    property string helpContext:"bayes"
    property bool expanded:expand.checked
    property bool restoring:false
    readonly property string method:methodChoice.currentValue||"bayes_beta_binomial"
    property var features:[]
    property var featureUnits:({})
    property var columns:[{id:"",name:"Seçin"}].concat(statistics.columns)
    signal helpRequested(var origin,string context)
    spacing:Theme.md
    function invalidate(){if(!restoring){assumptions.checked=false;statistics.invalidate()}}
    function plan(){return {alpha:Number(alpha.text),beta:Number(beta.text),location:Number(location.text),scale:Number(scale.text),noise_scale:Number(noise.text),group_scale:Number(groupScale.text),chains:chains.value,draws:draws.value,warmup:warmup.value,target_accept:Number(accept.text),sensitivity_factor:Number(sensitivity.text)}}
    function spec(){return {path:"bayes",method:method,x:outcome.currentValue||"",bayes_feature_units:method==="bayes_linear"||method==="bayes_hierarchical"?featureUnits:({}),features:method==="bayes_linear"||method==="bayes_hierarchical"?features:[],group:method==="bayes_hierarchical"?(group.currentValue||""):"",question:question.text,unit:unit.text,observation_unit:observation.text,scope:"full",seed:seed.value,confidence:Number(level.text),bayes_plan:plan(),measurement_confirmed:measurement.checked,independent:independent.checked,assumptions_confirmed:assumptions.checked}}
    function number(v){return typeof v==="number"?Number(v).toPrecision(5):"sunulmuyor"}
    function parameter(label,r){
        if(label.indexOf("beta(")===0){let i=Number(label.split("(")[1].split(",")[0]);let c=statistics.columns.find(c=>c.id===r.spec.features[i]);return "Slope · "+(c?c.name:label)+" ("+r.spec.unit+"/"+r.spec.bayes_feature_units[r.spec.features[i]]+")"}
        if(label.indexOf("group_effect(")===0){let i=Number(label.split("(")[1].split(",")[0]);return "Grup intercept farkı · "+r.group_labels[i]}
        return label
    }
    function summary(d,r){
        let rows=[d.status==="diagnostics_passed"?"Tanı eşikleri geçildi; model doğruluğu garantisi değildir":"TANI BAŞARISIZ · yakınsamış/güvenilir diye yorumlamayın", "Divergence: "+d.divergences+" · tree-depth sınırı: "+d.max_treedepth_hits+" · BFMI: "+d.bfmi.map(number).join(", "),"Eşikler: rank R-hat≤1.01; bulk/tail ESS≥"+d.thresholds.ess_min+"; divergence/treehit0; BFMI≥0.3"]
        for(let v of d.summary)rows.push(parameter(v.parameter,r)+": ortalama="+number(v.mean)+" · SD="+number(v.sd)+" · %"+Math.round(v.level*100)+" credible ["+v.credible_interval.map(number).join(", ")+"] · P(>0)="+number(v.probability_above_zero)+" · R-hat="+number(v.r_hat)+" · ESSbulk/tail="+number(v.ess_bulk)+"/"+number(v.ess_tail))
        return rows.join("\n")
    }
    function checks(ppc){return ppc.checks.map(v=>v.statistic+": gözlenen="+number(v.observed)+" · predictive2.5/50/97.5%="+v.replicate_quantiles.map(number).join("/")+" · predictive tail="+number(v.posterior_predictive_tail_probability)+(v.misfit_flag?" · UYUMSUZLUK İŞARETİ":"")).join("\n")}
    function resultText(r){
        if(!r||!r.bayes)return ""
        let rows=[statistics.current?"Güncel veri / prior tarifi":"ESKİ VERİ/TARİF: güncel olarak kaydedilemez",r.method_label+" · kullanılan n="+r.used_rows+" · dışlanan görünüm="+r.excluded_rows.outside_view,"Outcome birimi: "+r.spec.unit+" · gözlem birimi: "+r.spec.observation_unit,"Posterior · equal-tailed credible interval · posterior olasılığı p-değeri değildir.",summary(r.diagnostics,r),"Posterior predictive · eğitim verisinde betimsel misfit; p-değeri değil",checks(r.posterior_predictive)]
        let c=r.criteria
        rows.push("LOO/WAIC: "+(c.available?"hesaplandı":"kapalı · "+c.reason))
        if(c.available){for(let key of ["loo","waic"])rows.push(key+" log elpd="+number(c[key].elpd)+" · SE="+number(c[key].se)+" · etkin parametre="+number(c[key].effective_parameters)+" · uyarı="+c[key].warning);rows.push("Model sıralaması: "+(c.ranking_allowed?"aynı gözlemlerle karşılaştırılabilir":"uyarı nedeniyle KAPALI"));if(c.loo)rows.push("LOO Pareto-k max="+number(Math.max.apply(null,c.loo.pareto_k))+" · good_k="+number(c.loo.good_k))}
        let a=r.prior_sensitivity
        rows.push("Prior sensitivity · çarpan="+a.alternative_prior.sensitivity_factor+" · alternatif alpha/beta="+number(a.alternative_prior.alpha)+"/"+number(a.alternative_prior.beta)+" · Normal scale="+number(a.alternative_prior.scale)+" · group scale="+number(a.alternative_prior.group_scale),summary(a.diagnostics,r),"Alternatif posterior predictive",checks(a.posterior_predictive),"Uyarılar",r.warnings.join("\n"))
        return rows.join("\n\n")
    }
    function restore(s){
        if(!s||s.path!=="bayes"){expand.checked=false;return}
        restoring=true;expand.checked=true
        for(let pair of [[methodChoice,s.method],[outcome,s.x],[group,s.group]])for(let i=0;i<pair[0].model.length;i++)if(pair[0].model[i].id===pair[1])pair[0].currentIndex=i
        let p=s.bayes_plan
        for(let pair of [[alpha,p.alpha],[beta,p.beta],[location,p.location],[scale,p.scale],[noise,p.noise_scale],[groupScale,p.group_scale],[accept,p.target_accept],[sensitivity,p.sensitivity_factor],[question,s.question],[unit,s.unit],[observation,s.observation_unit],[level,s.confidence]])pair[0].text=String(pair[1])
        chains.value=p.chains;draws.value=p.draws;warmup.value=p.warmup;seed.value=s.seed;features=s.features;featureUnits=s.bayes_feature_units;measurement.checked=s.measurement_confirmed;independent.checked=s.independent;assumptions.checked=false;restoring=false
    }
    Connections {target:expertWorkspace;function onSelectMethod(path,name){if(path!=="bayes"){expand.checked=false;return}expand.checked=true;for(let i=0;i<methodChoice.model.length;i++)if(methodChoice.model[i].id===name)methodChoice.currentIndex=i;panel.invalidate()}function onRestorePreset(value){panel.restore(JSON.parse(value))}}
    UiCheckBox {id:expand;objectName:"bayesExpanded";text:"43 · Bayes şablonları · isteğe bağlı yerel backend"}
    ColumnLayout {
        visible:panel.expanded;Layout.fillWidth:true;spacing:Theme.md
        RowLayout {
            Layout.fillWidth:true
            UiCombo {id:methodChoice;objectName:"bayesMethod";Layout.fillWidth:true;model:statistics.methods("bayes");textRole:"label";valueRole:"id";accessibleLabel:"Bayes model şablonu";onActivated:panel.invalidate()}
            UiButton { visible: false;objectName:"bayesHelp";text:"Bu ne işe yarar?";helpContext:"bayes";onClicked:panel.helpRequested(this,"statistics."+panel.method.split("_").join("-"))}
        }
        UiLabel {text:"Yerel CPU NUTS; serbest probabilistic script çalıştırılmaz. Optional backend yoksa hesap açık hata verir, temel uygulama çalışır. Özel model kodu ileri kod alanının ayrı kapsamıdır. Birim/ölçek seçimini açıkça doğrulayın.";Layout.fillWidth:true;wrapMode:Text.WordWrap}
        GridLayout {
            columns:2;Layout.fillWidth:true
            UiLabel {text:"Soru"}
            UiTextField {id:question;objectName:"bayesQuestion";Accessible.name:placeholderText;placeholderText:"Bayes sorusu";text:"Ölçümün posterior dağılımı";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Outcome"}
            UiCombo {id:outcome;objectName:"bayesOutcome";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Bayes outcome sütunu";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Outcome birimi"}
            UiTextField {id:unit;objectName:"bayesUnit";Accessible.name:placeholderText;placeholderText:"Ölçüm birimi";text:"puan";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Bağımsız gözlem birimi"}
            UiTextField {id:observation;objectName:"bayesObservation";Accessible.name:placeholderText;placeholderText:"Gözlem birimi";text:"kişi";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Grup (yalnız hierarchical)"}
            UiCombo {id:group;objectName:"bayesGroup";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Bayes grup kimliği";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Sayısal predictor seç"}
            UiCombo {id:predictor;objectName:"bayesPredictor";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Ham ölçekte Bayes predictor";Layout.fillWidth:true}
            UiButton {objectName:"bayesAddPredictor";text:"Predictor ekle/çıkar";onClicked:{let x=predictor.currentValue;if(!x)return;panel.features=panel.features.indexOf(x)<0?panel.features.concat([x]):panel.features.filter(v=>v!==x);let u=Object.assign({},panel.featureUnits);if(panel.features.indexOf(x)>=0)u[x]="1";else delete u[x];panel.featureUnits=u;panel.invalidate()}}
            UiLabel {text:panel.features.map(v=>{let c=statistics.columns.find(c=>c.id===v);return c?c.name:v}).join(", ");Layout.fillWidth:true;wrapMode:Text.WordWrap}
        }
        Repeater {model:panel.features;UiTextField {required property string modelData;Accessible.name:"Predictor birimi "+modelData;placeholderText:"Predictor birimi (dimensionless:1)";text:panel.featureUnits[modelData]||"1";Layout.fillWidth:true;onTextEdited:{let u=Object.assign({},panel.featureUnits);u[modelData]=text;panel.featureUnits=u;panel.invalidate()}}}
        UiLabel {text:"Predictor ham ölçekte kalır. Intercept SD outcome biriminde; slope SD outcome/predictor biriminde. Otomatik standardization yok. Beta-binomial: bağımsız0/1, Beta(alpha,beta). Normal mean: Normal(location,scale), bilinen observation SD=noise. Regression: Normal intercept/slopes, HalfNormal noise; hierarchical noncentered HalfNormal group SD.";Layout.fillWidth:true;wrapMode:Text.WordWrap}
        GridLayout {
            columns:4;Layout.fillWidth:true
            UiLabel {text:"Beta alpha"}
            UiTextField {id:alpha;objectName:"bayesAlpha";Accessible.name:"Beta prior alpha";text:"1";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Beta beta"}
            UiTextField {id:beta;objectName:"bayesBeta";Accessible.name:"Beta prior beta";text:"1";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Normal prior merkezi"}
            UiTextField {id:location;objectName:"bayesLocation";Accessible.name:"Normal prior merkezi";text:"0";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Intercept/slope prior SD"}
            UiTextField {id:scale;objectName:"bayesScale";Accessible.name:"Intercept ve slope prior SD";text:"2";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Observation/noise SD"}
            UiTextField {id:noise;objectName:"bayesNoise";Accessible.name:"Bilinen observation veya noise prior SD";text:"1";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Group SD prior ölçeği"}
            UiTextField {id:groupScale;objectName:"bayesGroupScale";Accessible.name:"Grup prior SD";text:"1";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Chains"}
            UiSpinBox {id:chains;objectName:"bayesChains";Accessible.name:"Bayes chain sayısı";from:2;to:4;value:4;onValueModified:panel.invalidate()}
            UiLabel {text:"Draws / chain"}
            UiSpinBox {id:draws;objectName:"bayesDraws";Accessible.name:"Warmup sonrası draw sayısı";from:100;to:2000;value:500;onValueModified:panel.invalidate()}
            UiLabel {text:"Warmup / chain"}
            UiSpinBox {id:warmup;objectName:"bayesWarmup";Accessible.name:"Warmup sayısı";from:100;to:2000;value:500;onValueModified:panel.invalidate()}
            UiLabel {text:"Seed"}
            UiSpinBox {id:seed;objectName:"bayesSeed";Accessible.name:"Bayes seed";from:0;to:1000000;value:42;onValueModified:panel.invalidate()}
            UiLabel {text:"Target accept"}
            UiTextField {id:accept;objectName:"bayesAccept";Accessible.name:"NUTS target accept";text:"0.9";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Credible interval düzeyi"}
            UiTextField {id:level;objectName:"bayesLevel";Accessible.name:"Credible interval düzeyi";text:"0.95";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Alternatif prior çarpanı"}
            UiTextField {id:sensitivity;objectName:"bayesSensitivity";Accessible.name:"Prior sensitivity çarpanı";text:"2";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
        }
        UiCheckBox {id:measurement;objectName:"bayesMeasurement";text:"Birimleri, ham predictor ölçeğini ve prior'ı doğruladım";onToggled:panel.invalidate()}
        UiCheckBox {id:independent;objectName:"bayesIndependent";text:"Bağımsız gözlemler; hierarchical şablonda gruplar arası bağımsızlık";onToggled:panel.invalidate()}
        UiButton {objectName:"bayesPreflight";text:"Maliyet / prior predictive önizle";enabled:!statistics.busy;onClicked:statistics.create(JSON.stringify(panel.spec()),true)}
        UiLabel {objectName:"bayesPreview";visible:statistics.preflightCurrent&&statistics.preflightResult.bayes===true;text:JSON.stringify(statistics.preflightResult.prior_predictive)+"\n"+JSON.stringify(statistics.preflightResult.budget);Layout.fillWidth:true;wrapMode:Text.WordWrap}
        UiCheckBox {id:assumptions;objectName:"bayesAssumptions";text:"Prior predictive, maliyet ve model varsayımlarını inceledim";enabled:statistics.preflightCurrent}
        RowLayout {
            UiButton {objectName:"bayesRun";text:"İki prior ile örnekle";enabled:!statistics.busy&&assumptions.checked;onClicked:statistics.create(JSON.stringify(panel.spec()),false)}
            UiButton {objectName:"bayesCancel";text:"İptal";enabled:statistics.busy;onClicked:statistics.cancel()}
        }
        UiLabel {text:statistics.message;Layout.fillWidth:true;wrapMode:Text.WordWrap}
        UiLabel {text:statistics.errorText;visible:!!statistics.errorText;color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.WordWrap}
        UiLabel {objectName:"bayesStatus";visible:statistics.analysisResult.bayes===true;text:statistics.analysisResult.diagnostics?(statistics.analysisResult.diagnostics.status==="diagnostic_fail"?"TANI BAŞARISIZ · diagnostic_fail":"Tanı eşikleri geçildi; model doğruluğu garantisi değildir"):"";Layout.fillWidth:true;color:Theme.warning}
        UiLabel {objectName:"bayesResult";visible:statistics.analysisResult.bayes===true;text:panel.resultText(statistics.analysisResult);Layout.fillWidth:true;wrapMode:Text.WordWrap}
        Image {objectName:"bayesTrace";visible:statistics.analysisResult.bayes===true&&!!statistics.modelDiagnostic;source:statistics.analysisResult.bayes?statistics.modelDiagnostic:"";Layout.fillWidth:true;Layout.preferredHeight:320;fillMode:Image.PreserveAspectFit}
        RowLayout {
            Layout.fillWidth:true
            UiButton {objectName:"bayesSave";text:"Posterior ve tanıları kaydet";enabled:statistics.current&&!statistics.busy&&statistics.analysisResult.bayes===true;onClicked:statistics.save()}
            UiTextField {id:exportPath;objectName:"bayesExportPath";Accessible.name:placeholderText;placeholderText:"Yeni mutlak export klasörü";Layout.fillWidth:true}
            UiButton {objectName:"bayesExport";text:"Güvenli veriyi export et";enabled:statistics.current&&!statistics.busy&&statistics.analysisResult.bayes===true;onClicked:statistics.exportAdvanced(exportPath.text)}
        }
        RowLayout {
            Layout.fillWidth:true
            UiCombo {id:saved;objectName:"bayesSaved";model:statistics.savedAnalyses.filter(v=>v.path==="bayes");textRole:"label";valueRole:"id";accessibleLabel:"Kayıtlı Bayes sonucu";Layout.fillWidth:true}
            UiButton {objectName:"bayesOpen";text:"Kaydı aç";enabled:!!saved.currentValue&&!statistics.busy;onClicked:{statistics.openSaved(saved.currentValue);panel.restore(statistics.analysisResult.spec)}}
            UiButton {objectName:"bayesCompare";text:"LOO/WAIC karşılaştır";enabled:statistics.current&&!statistics.busy&&!!saved.currentValue&&statistics.analysisResult.bayes===true;onClicked:statistics.compareBayes(saved.currentValue)}
        }
        UiLabel {text:JSON.stringify(statistics.bayesComparison);Layout.fillWidth:true;wrapMode:Text.WordWrap}
    }
}
