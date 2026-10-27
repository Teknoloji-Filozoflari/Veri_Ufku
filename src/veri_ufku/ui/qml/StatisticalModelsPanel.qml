import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "statisticalModelsPanel"
    property bool expanded: expand.checked
    property string helpContext: "statistical-models"
    readonly property string methodHelp: "statistics."+method.split("_").join("-")
    property var featureState: ({})
    property var interactions: []
    property var withinIds: []
    property var comparison: ({})
    readonly property string method: methodChoice.currentValue || "ols"
    readonly property bool countModel: method === "glm_poisson" || method === "glm_negative_binomial"
    signal helpRequested(var origin, string context)
    spacing: Theme.md
    function number(v) { return typeof v==="number" ? Number(v).toPrecision(6) : v===null||v===undefined ? "sunulmuyor" : String(v) }
    function baselineText(v) { let out=[];for(let c in (v||{}))out.push(v[c].name+" → referans: "+v[c].reference+" · düzeyler: "+v[c].levels.join(" / "));return out.join("; ")||"Kategorik predictor yok" }
    function supportText(s) { if(!s)return "";return "Tahmin: "+(s.prediction ? s.prediction_kind : "desteklenmiyor (yalnız inference)")+" · Tahmin aralığı: sunulmuyor\nSonuç kaydı: destekleniyor · Predictive model kaydı: "+(s.model_save?"destekleniyor":"desteklenmiyor") }
    function fitText(f) { if(!f)return "";let labels={r_squared:"R²",adjusted_r_squared:"Düzeltilmiş R²",pseudo_r_squared:"Pseudo-R²",log_likelihood:"Log-likelihood",aic:"AIC",bic:"BIC",deviance:"Deviance",pearson_chi2:"Pearson chi²",residual_variance:"Residual varyansı"};let rows=[];for(let k in labels)if(f[k]!==undefined)rows.push(labels[k]+"="+number(f[k]));if(f.random_covariance)rows.push("Random covariance: "+f.random_covariance.map(row=>row.map(number).join(", ")).join("; "));return rows.join(" · ") }
    function diagnosticText(d) { if(!d)return "";let rows=[];if(d.heteroskedasticity)rows.push(d.heteroskedasticity.p!==undefined?"Koenker BP: p="+number(d.heteroskedasticity.p):"Heteroskedasticity testi: bu yöntemde sunulmuyor");if(d.overdispersion)rows.push("Pearson dispersion="+number(d.overdispersion.pearson_ratio)+" · "+(d.overdispersion.warning?"Overdispersion uyarısı":"1.5 uyarı eşiği aşılmadı")+" (heuristik)");if(d.influence)rows.push(d.influence.points?"Influential aday="+d.influence.influential_count+" · Cook cutoff="+number(d.influence.cutoff):"Cook/leverage: bu yöntemde sunulmuyor");return rows.join("\n") }
    function interactionText() { let names={};for(let c of statistics.columns)names[c.id]=c.name;return interactions.map(p=>(names[p[0]]||"?")+" × "+(names[p[1]]||"?")).join("; ")||"Yok" }
    function key(picker) { return picker.currentValue || "" }
    function changedConfig() { assumptions.checked=false; comparison={}; statistics.invalidate() }
    function updateFeature(column, attribute, value) {
        let next=JSON.parse(JSON.stringify(featureState)); if(!next[column])next[column]={selected:false,categorical:false,reference:"",random:false};next[column][attribute]=value;featureState=next;changedConfig()
    }
    function spec() {
        let features=[],refs={},slopes=[]
        for(let c of statistics.columns){let f=featureState[c.id];if(f&&f.selected){features.push(c.id);if(f.categorical)refs[c.id]=f.reference;if(f.random)slopes.push(c.id)}}
        return {path:"models",method:method,x:key(response),features:method==="repeated"?[]:features,references:method==="repeated"?{}:refs,interactions:method==="repeated"?[]:interactions,covariance:key(covariance),weight:method==="wls"?key(weight):"",offset:countModel?key(offset):"",exposure:countModel?key(exposure):"",cluster:key(covariance)==="cluster"?key(cluster):"",group:(method==="mixed"||method==="repeated")?key(group):"",random_slopes:method==="mixed"?slopes:[],within:method==="repeated"?withinIds:[],quantile:Number(quantile.text),nb_alpha:Number(alpha.text),reml:reml.checked,max_iterations:iterations.value,missing_policy:complete.checked?"complete":"reject",question:question.text,hypothesis:hypothesis.text,unit:unit.text,observation_unit:observation.text,independent:independent.checked,measurement_confirmed:measurement.checked,assumptions_confirmed:assumptions.checked,scope:full.checked?"full":"view",confidence:Number(confidence.currentValue)}
    }
    function restore(s) {
        if(!s||s.path!=="models"){expand.checked=false;return}
        expand.checked=true
        for(let i=0;i<methodChoice.model.length;i++)if(methodChoice.model[i].id===s.method)methodChoice.currentIndex=i
        let next={};for(let c of s.features)next[c]={selected:true,categorical:s.references[c]!==undefined,reference:s.references[c]||"",random:s.random_slopes.indexOf(c)>=0};featureState=next;interactions=s.interactions;withinIds=s.within
        Qt.callLater(function(){for(let pair of [[response,s.x],[weight,s.weight],[offset,s.offset],[exposure,s.exposure],[cluster,s.cluster],[group,s.group],[covariance,s.covariance]])for(let i=0;i<pair[0].model.length;i++)if(pair[0].model[i].id===pair[1])pair[0].currentIndex=i})
        question.text=s.question;hypothesis.text=s.hypothesis;unit.text=s.unit;observation.text=s.observation_unit;measurement.checked=s.measurement_confirmed;independent.checked=s.independent;complete.checked=s.missing_policy==="complete";full.checked=s.scope==="full";quantile.text=String(s.quantile);alpha.text=String(s.nb_alpha);reml.checked=s.reml;iterations.value=s.max_iterations;assumptions.checked=false;confidence.currentIndex=[.95,.90,.99].indexOf(s.confidence)
    }
    Connections { target: expertWorkspace; function onSelectMethod(path,name){if(path!=="models"){expand.checked=false;return}expand.checked=true;for(let i=0;i<methodChoice.model.length;i++)if(methodChoice.model[i].id===name)methodChoice.currentIndex=i} function onRestorePreset(value){panel.restore(JSON.parse(value))} }
    UiCheckBox { id: expand; objectName:"modelsExpanded"; text:"Faz40 · İstatistiksel modeller ve tanılama"; onToggled: panel.changedConfig() }
    ColumnLayout {
        visible: panel.expanded
        Layout.fillWidth: true
        spacing: Theme.md
        UiLabel { Layout.fillWidth:true; wrapMode:Text.WordWrap; text:"Çıkarım / prediction ayrı: p-değeri nedensellik kanıtı değildir. Bu ekran in-sample fit üretir; prediction başarısı için ayrı held-out doğrulama gerekir. Formül serbest kod çalıştırmaz; seçili kimliklerden matrix oluşturulur." }
        RowLayout {
            Layout.fillWidth:true
            UiCombo { id:methodChoice; objectName:"modelsMethod"; Layout.fillWidth:true; model:statistics.methods("models"); textRole:"label";valueRole:"id";accessibleLabel:"Model ve alt aşama";onActivated:panel.changedConfig() }
            UiButton { visible: false; text:"Bu ne işe yarar?"; helpContext:"statistical-models";onClicked:panel.helpRequested(this,helpContext) }
            UiButton { visible: false; objectName:"modelsMethodHelp";text:"Yöntem yardımı"; helpContext:panel.methodHelp;onClicked:panel.helpRequested(this,helpContext) }
        }
        UiCombo { id:response; objectName:"modelsResponse";Layout.fillWidth:true;model:statistics.columns;textRole:"name";valueRole:"id";accessibleLabel:"Response / yanıt sütunu";onActivated:panel.changedConfig() }
        UiLabel { text: panel.method==="repeated"?"Within faktörleri: en fazla300 hücre /100 kişi; tam dengeli kişi × faktör grid; between effects / GG-HF correction yok.":"Predictors · Kategori ise baseline açıkça yazın; sayısal kategoriler de açık seçim ister."; Layout.fillWidth:true;wrapMode:Text.WordWrap }
        Repeater {
            model:statistics.columns
            delegate: RowLayout {
                required property var modelData
                Layout.fillWidth:true
                UiCheckBox { objectName:"modelsFeature_"+modelData.name; visible:panel.method!=="repeated";text:modelData.name;checked:!!(panel.featureState[modelData.id]&&panel.featureState[modelData.id].selected);onToggled:panel.updateFeature(modelData.id,"selected",checked) }
                UiCheckBox { objectName:"modelsWithin_"+modelData.name;visible:panel.method==="repeated";text:modelData.name+" · within";checked:panel.withinIds.indexOf(modelData.id)>=0;onToggled:{let ids=panel.withinIds.filter(c=>c!==modelData.id);if(checked)ids.push(modelData.id);panel.withinIds=ids;panel.changedConfig()} }
                UiCheckBox { objectName:"modelsCategory_"+modelData.name;visible:panel.method!=="repeated";text:"Kategorik";checked:!!(panel.featureState[modelData.id]&&panel.featureState[modelData.id].categorical);onToggled:panel.updateFeature(modelData.id,"categorical",checked) }
                UiTextField { objectName:"modelsBaseline_"+modelData.name;visible:panel.method!=="repeated";Layout.fillWidth:true;placeholderText:"Referans kategori · "+modelData.name;Accessible.name:placeholderText;text:panel.featureState[modelData.id]?panel.featureState[modelData.id].reference:"";enabled:!!(panel.featureState[modelData.id]&&panel.featureState[modelData.id].categorical);onTextEdited:panel.updateFeature(modelData.id,"reference",text) }
                UiCheckBox { objectName:"modelsRandom_"+modelData.name;visible:panel.method==="mixed";text:"Random slope";checked:!!(panel.featureState[modelData.id]&&panel.featureState[modelData.id].random);onToggled:panel.updateFeature(modelData.id,"random",checked) }
            }
        }
        RowLayout {
            visible:panel.method!=="repeated";Layout.fillWidth:true
            UiCombo { id:interactionA;objectName:"modelsInteractionA";Layout.fillWidth:true;model:statistics.columns;textRole:"name";valueRole:"id";accessibleLabel:"Interaction ilk predictor" }
            UiCombo { id:interactionB;objectName:"modelsInteractionB";Layout.fillWidth:true;model:statistics.columns;textRole:"name";valueRole:"id";accessibleLabel:"Interaction ikinci predictor" }
            UiButton { objectName:"modelsAddInteraction";text:"Interaction ekle";onClicked:{panel.interactions=panel.interactions.concat([[panel.key(interactionA),panel.key(interactionB)]]);panel.changedConfig()} }
            UiButton { text:"Interaction temizle";onClicked:{panel.interactions=[];panel.changedConfig()} }
        }
        UiLabel { Layout.fillWidth:true;wrapMode:Text.WordWrap;text:"Interaction çiftleri: "+panel.interactionText()+". Etki, diğer predictor/baseline sabitken yorumlanır." }
        GridLayout {
            columns:2;Layout.fillWidth:true
            UiLabel { text:"SE / covariance" }
            UiCombo { id:covariance;objectName:"modelsCovariance";Layout.fillWidth:true;accessibleLabel:"Yöntemin desteklediği SE";textRole:"label";valueRole:"id";model:(panel.method==="quantile"?["robust","iid"]:(panel.method==="mixed"||panel.method==="repeated")?["nonrobust"]:panel.method.startsWith("glm_")?["nonrobust","HC0","cluster"]:["nonrobust","HC3","cluster"]).map(v=>({id:v,label:v}));onActivated:panel.changedConfig() }
            UiLabel { text:"WLS · pozitif ters-varyans ağırlığı";visible:panel.method==="wls" }
            UiCombo { id:weight;objectName:"modelsWeight";visible:panel.method==="wls";Layout.fillWidth:true;model:[{id:"",name:"Seçin"}].concat(statistics.columns);textRole:"name";valueRole:"id";accessibleLabel:"WLS ağırlık sütunu";onActivated:panel.changedConfig() }
            UiLabel { text:"Offset · log ölçeğinde katsayısı1";visible:panel.countModel }
            UiCombo { id:offset;objectName:"modelsOffset";visible:panel.countModel;Layout.fillWidth:true;model:[{id:"",name:"Yok"}].concat(statistics.columns);textRole:"name";valueRole:"id";accessibleLabel:"Offset sütunu";onActivated:panel.changedConfig() }
            UiLabel { text:"Exposure · pozitif süre/alan; log(exposure)";visible:panel.countModel }
            UiCombo { id:exposure;objectName:"modelsExposure";visible:panel.countModel;Layout.fillWidth:true;model:[{id:"",name:"Yok"}].concat(statistics.columns);textRole:"name";valueRole:"id";accessibleLabel:"Exposure sütunu";onActivated:panel.changedConfig() }
            UiLabel { text:"Cluster · bağımsız küme";visible:covariance.currentValue==="cluster" }
            UiCombo { id:cluster;objectName:"modelsCluster";visible:covariance.currentValue==="cluster";Layout.fillWidth:true;model:[{id:"",name:"Seçin"}].concat(statistics.columns);textRole:"name";valueRole:"id";accessibleLabel:"Cluster sütunu";onActivated:panel.changedConfig() }
            UiLabel { text:"Group / kişi · random intercept";visible:panel.method==="mixed"||panel.method==="repeated" }
            UiCombo { id:group;objectName:"modelsGroup";visible:panel.method==="mixed"||panel.method==="repeated";Layout.fillWidth:true;model:[{id:"",name:"Seçin"}].concat(statistics.columns);textRole:"name";valueRole:"id";accessibleLabel:"Random group / repeated kişi sütunu";onActivated:panel.changedConfig() }
            UiLabel { text:"Quantile · hedef koşullu yüzdelik";visible:panel.method==="quantile" }
            UiTextField { id:quantile;objectName:"modelsQuantile";visible:panel.method==="quantile";text:"0.5";placeholderText:"Quantile 0.05–0.95";Accessible.name:placeholderText;onTextEdited:panel.changedConfig() }
            UiLabel { text:"NB2 alpha · sabit, tahmin edilmez";visible:panel.method==="glm_negative_binomial" }
            UiTextField { id:alpha;objectName:"modelsAlpha";visible:panel.method==="glm_negative_binomial";text:"1";placeholderText:"Pozitif NB alpha";Accessible.name:placeholderText;onTextEdited:panel.changedConfig() }
        }
        UiCheckBox { id:reml;objectName:"modelsReml";visible:panel.method==="mixed";checked:true;text:"REML · AIC/BIC sunulmaz; ML için kapat";onToggled:panel.changedConfig() }
        UiLabel { Layout.fillWidth:true;wrapMode:Text.WordWrap;text:"Cluster SE: en az5 bağımsız küme uygulama alt sınırıdır; güvenilirlik garantisi değildir.50 altı küçük-küme yanlılığına dikkat; CR2 / wild bootstrap yok. Desteklenmeyen SE yöntem listesinde yer almaz." }
        RowLayout {
            UiCombo { id:confidence;objectName:"modelsConfidence";model:[{id:.95,label:"%95 CI"},{id:.90,label:"%90 CI"},{id:.99,label:"%99 CI"}];textRole:"label";valueRole:"id";accessibleLabel:"Katsayı güven düzeyi";onActivated:panel.changedConfig() }
            UiSpinBox { id:iterations;objectName:"modelsIterations";from:1;to:2000;value:1000;Accessible.name:"Maksimum fit iterasyonu";onValueModified:panel.changedConfig() }
            UiCheckBox { id:complete;objectName:"modelsComplete";text:"Complete-case dışlamasına izin ver";onToggled:panel.changedConfig() }
            UiCheckBox { id:full;objectName:"modelsFull";text:"Tam dataset (tablo filtresi yerine)";onToggled:panel.changedConfig() }
        }
        UiTextField { id:question;objectName:"modelsQuestion";Layout.fillWidth:true;placeholderText:"Araştırma sorusu";Accessible.name:placeholderText;onTextEdited:panel.changedConfig() }
        UiTextField { id:hypothesis;objectName:"modelsHypothesis";Layout.fillWidth:true;placeholderText:"Önceden seçilmiş hipotez / etki";Accessible.name:placeholderText;onTextEdited:panel.changedConfig() }
        UiTextField { id:unit;objectName:"modelsUnit";Layout.fillWidth:true;placeholderText:"Response birimi";Accessible.name:placeholderText;onTextEdited:panel.changedConfig() }
        UiTextField { id:observation;objectName:"modelsObservation";Layout.fillWidth:true;placeholderText:"Bağımsız gözlem birimi veya kişi/grup";Accessible.name:placeholderText;onTextEdited:panel.changedConfig() }
        UiCheckBox { id:measurement;objectName:"modelsMeasurement";text:"Ölçüm, category baseline ve response anlamını doğruladım";onToggled:panel.changedConfig() }
        UiCheckBox { id:independent;objectName:"modelsIndependent";text:"Gözlemler / mixed-repeated-cluster için gruplar arasında bağımsızlık tasarımını doğruladım";onToggled:panel.changedConfig() }
        RowLayout {
            UiButton { objectName:"modelsPreflight";text:"Design / VIF önkontrol";enabled:!statistics.busy;onClicked:statistics.create(JSON.stringify(panel.spec()),true) }
            UiCheckBox { id:assumptions;objectName:"modelsAssumptions";text:"Önkontrolü ve yöntem varsayımlarını inceledim";enabled:statistics.preflightCurrent }
            UiButton { objectName:"modelsRun";text:"Modeli hesapla";enabled:!statistics.busy&&statistics.preflightCurrent&&assumptions.checked;onClicked:statistics.create(JSON.stringify(panel.spec()),false) }
            UiButton { text:"İptal";enabled:statistics.busy;onClicked:statistics.cancel() }
        }
        UiLabel { objectName:"modelsPreflightText";Layout.fillWidth:true;wrapMode:Text.WordWrap;text:statistics.preflightCurrent?"Formül: "+statistics.preflightResult.formula+"\nBaseline: "+panel.baselineText(statistics.preflightResult.categorical_baselines)+"\nVIF: "+(statistics.preflightResult.vif||[]).map(v=>v.term+"="+panel.number(v.value)).join("; ")+"\nDışlanan: "+statistics.preflightResult.excluded_rows+"\n"+(statistics.preflightResult.warnings||[]).join("\n"):"Güncel önkontrol gerekli." }
        UiLabel { Layout.fillWidth:true;wrapMode:Text.WordWrap;text:statistics.errorText||statistics.message }
        ColumnLayout {
            visible:!!statistics.analysisResult.spec&&statistics.analysisResult.spec.path==="models"
            Layout.fillWidth:true
            UiLabel { objectName:"modelsStatus";text:statistics.current?"Güncel model sürümü":"ESKİ / farklı veri-filtre-tarif sürümü; prediction engelli";Layout.fillWidth:true;wrapMode:Text.WordWrap }
            UiLabel { objectName:"modelsSummary";Layout.fillWidth:true;wrapMode:Text.WordWrap;text:panel.supportText(statistics.analysisResult.model_support)+"\nFormül: "+statistics.analysisResult.formula+"\nBaseline: "+panel.baselineText(statistics.analysisResult.categorical_baselines)+"\nLink: "+statistics.analysisResult.link+"\nUyum: "+panel.fitText(statistics.analysisResult.fit)+"\nTanılama: "+panel.diagnosticText(statistics.analysisResult.diagnostics)+"\n"+(statistics.analysisResult.warnings||[]).join("\n") }
            Repeater { model:statistics.analysisResult.coefficients||[];delegate:UiLabel { required property var modelData;Layout.fillWidth:true;wrapMode:Text.WordWrap;text:modelData.term+" · beta="+panel.number(modelData.estimate)+" · SE="+panel.number(modelData.se)+" · p="+panel.number(modelData.p)+" · %"+Math.round(100*modelData.confidence)+" CI ["+panel.number(modelData.low)+", "+panel.number(modelData.high)+"] · "+modelData.effect_label+"="+panel.number(modelData.effect)+" · effect CI ["+panel.number(modelData.effect_low)+", "+panel.number(modelData.effect_high)+"]" } }
            UiLabel { Layout.fillWidth:true;wrapMode:Text.WordWrap;text:"Repeated omnibus testleri: "+(statistics.analysisResult.model_tests||[]).map(t=>t.term+" · F="+panel.number(t.f)+" · df="+t.numerator_df+" / "+t.denominator_df+" · p="+panel.number(t.p)).join("; ") }
            Image { objectName:"modelsDiagnostic"; property bool ready: status===Image.Ready;Layout.fillWidth:true;Layout.preferredHeight:400;source:statistics.modelDiagnostic;fillMode:Image.PreserveAspectFit;Accessible.name:"Model residual QQ ve influence grafikleri" }
            UiButton { objectName:"modelsSave";text:"Sonuç / desteklenen model JSON kaydet";enabled:statistics.current&&!statistics.busy&&!projects.readOnly;onClicked:statistics.save() }
            ColumnLayout {
                visible:!!statistics.analysisResult.model_support&&statistics.analysisResult.model_support.prediction
                Layout.fillWidth:true
                Repeater { id:predictionInputs;model:statistics.analysisResult.prediction_schema?statistics.analysisResult.prediction_schema.features:[];delegate:UiTextField { required property var modelData;objectName:"modelsPredict_"+modelData;Layout.fillWidth:true;placeholderText:"Yeni gözlem · "+(statistics.analysisResult.prediction_schema.columns[modelData]||modelData);Accessible.name:placeholderText;text:"0" } }
                UiTextField { id:predictionOffset;objectName:"modelsPredictionOffset";visible:!!(statistics.analysisResult.prediction_schema&&statistics.analysisResult.prediction_schema.offset);text:"0";placeholderText:"Yeni gözlem log-offset";Accessible.name:placeholderText }
                UiTextField { id:predictionExposure;objectName:"modelsPredictionExposure";visible:!!(statistics.analysisResult.prediction_schema&&statistics.analysisResult.prediction_schema.exposure);text:"1";placeholderText:"Yeni gözlem pozitif exposure";Accessible.name:placeholderText }
                UiButton { objectName:"modelsPredict";text:"Yeni gözlem prediction (CI yok)";enabled:statistics.current&&!statistics.busy;onClicked:{let values={},s=statistics.analysisResult.prediction_schema;for(let i=0;i<predictionInputs.count;i++){let c=predictionInputs.itemAt(i);values[c.modelData]=s.baselines[c.modelData]?c.text:Number(c.text)}statistics.predictModel(JSON.stringify(values),Number(predictionOffset.text),Number(predictionExposure.text))} }
                UiLabel { objectName:"modelsPredictionText";Layout.fillWidth:true;wrapMode:Text.WordWrap;text:statistics.modelPrediction.value!==undefined?"Prediction="+panel.number(statistics.modelPrediction.value)+" · "+statistics.modelPrediction.kind+" · "+statistics.modelPrediction.warning:"Yeni gözlem değerlerini yazın; kategori varsa gözlenen düzeylerden birini girin." }
            }
            UiLabel { Layout.fillWidth:true;wrapMode:Text.WordWrap;text:"AIC/BIC yalnız aynı response/satır/likelihood/link/weight/offset bağlamında karşılaştırılır. REML ve quantile için sunulmaz; prediction skoru değildir." }
            RowLayout {
                UiCombo { id:comparisonChoice;model:statistics.savedAnalyses.filter(r=>r.path==="models");textRole:"label";valueRole:"id";accessibleLabel:"AIC/BIC karşılaştırılacak kayıt";Layout.fillWidth:true }
                UiButton { objectName:"modelsCompare";text:"AIC/BIC bağlamını kontrol et";onClicked:panel.comparison=statistics.compareModel(panel.key(comparisonChoice)) }
            }
            UiLabel { Layout.fillWidth:true;wrapMode:Text.WordWrap;text:panel.comparison.delta_aic!==undefined?"ΔAIC="+panel.number(panel.comparison.delta_aic)+" · ΔBIC="+panel.number(panel.comparison.delta_bic)+" · "+panel.comparison.warning:"Bağlamı doğrulanmış karşılaştırma yok." }
        }
        RowLayout {
            UiCombo { id:saved;objectName:"modelsSaved";Layout.fillWidth:true;model:statistics.savedAnalyses.filter(r=>r.path==="models");textRole:"label";valueRole:"id";accessibleLabel:"Kaydedilen istatistiksel model / sonuç" }
            UiButton { objectName:"modelsOpen";text:"Kaydı aç";onClicked:{statistics.openSaved(panel.key(saved));panel.restore(statistics.analysisResult.spec)} }
        }
    }
}
