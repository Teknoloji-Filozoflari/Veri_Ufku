import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"dimensionPanel"
    property string helpContext:"dimensions"
    property bool expanded:expand.checked
    property bool restoring:false
    property var features:[]
    property var columns:[{id:"",name:"Seçin"}].concat(statistics.columns)
    readonly property string method:methodChoice.currentValue||"dimension_pca"
    readonly property bool available:methodChoice.currentIndex>=0&&methodChoice.model[methodChoice.currentIndex].enabled
    readonly property string selectedPurpose:purpose.currentValue||"compression"
    signal helpRequested(var origin,string context)
    spacing:Theme.md
    function invalidate(){if(!restoring){assumptions.checked=false;statistics.invalidate()}}
    function numbers(text){return text.trim()?text.split(",").map(Number):[]}
    function plan(){return {purpose:selectedPurpose,fit_scope:selectedPurpose==="model_input"?"development":"full",target_kind:targetKind.currentText,scaling:scaling.currentText,missing:missing.currentText,storage:storage.currentText,components:components.value,variance_threshold:Number(threshold.text),folds:folds.value,inner_folds:innerFolds.value,batch_size:batch.value,perplexity:Number(perplexity.text),neighbors:neighbors.value,profile:profile.text.trim()?numbers(profile.text):features.map(()=>0.5)}}
    function spec(){return {path:"dimensions",method:method,x:features[0]||"",y:selectedPurpose==="model_input"?(targetColumn.currentValue||""):"",features:features,question:question.text,observation_unit:observation.text,scope:"full",seed:seed.value,max_iterations:iterations.value,dimension_plan:plan(),independent:independent.checked,measurement_confirmed:measurement.checked,assumptions_confirmed:assumptions.checked}}
    function label(id){let c=columns.find(c=>c.id===id);return c?c.name:id}
    function number(v){return typeof v==="number"?Number(v).toPrecision(5):"desteklenmiyor"}
    function describe(r){
        if(!r||!r.dimensions)return ""
        let a=r.dimension_analysis,m=a.model,cv=a.cv,lines=[r.result_version?(statistics.current?"Güncel veri / amaç / fit tarifi":"ESKİ VERİ/TARİF · save/export/transform kapalı"):"Önkontrol",r.method_label+" · amaç="+a.purpose+" · fit kapsamı="+a.fit_scope+" · fit n="+r.used_rows+" / population="+r.n.population,"Dışlanan / saklı test: "+JSON.stringify(r.excluded_rows),"Maliyet: "+JSON.stringify(r.budget),"Scaling="+r.plan.scaling+" · missing="+r.plan.missing+" · sparse="+JSON.stringify(a.sparse_layout),"Explained variance: "+(a.explained_variance?a.explained_variance.map(number).join(", "):"yöntemde yok; üretilmedi"),"Variance ratio: "+(a.explained_variance_ratio?a.explained_variance_ratio.map(number).join(", "):"yok"),"Loadings/basis: "+(a.loading_definition||"bu yöntem için yok"),"Reconstruction: "+JSON.stringify(a.reconstruction_error),"Seçili orijinal feature: "+a.selected_features.map(panel.label).join(", "),"Yeni veri transform="+m.transform_supported+" · inverse="+m.inverse_supported+" · inverse yaklaşık, bilgi kaybını geri getirmez","Görünüm: "+JSON.stringify(a.display)]
        if(cv){lines.push("Validation plan="+cv.plan.split_id+" · "+cv.score_name+" outer mean="+number(cv.mean_outer_score),cv.policy,"Final test: "+cv.final_test.reason);for(let f of cv.folds)lines.push("Fold"+f.fold+" · train="+f.train.length+" · evaluation="+f.evaluation.length+" · score="+number(f.score)+" · inner pipeline fits="+f.inner.length+" · selected="+(f.selected_features?f.selected_features.map(panel.label).join(", "):"latent reducer"));if(cv.stability)lines.push("Selection stabilitesi: "+cv.stability.frequency.map(v=>label(v.column_id)+"="+v.selected_folds+"/"+v.folds).join(" · "),"Jaccard: "+JSON.stringify(cv.stability.pairwise),cv.stability.interpretation)}
        if(a.native_umap_transform)lines.push(a.native_umap_transform)
        lines.push("Profile preview: "+JSON.stringify(a.profile_preview),a.warnings.join("\n"))
        return lines.join("\n\n")
    }
    function restore(s){
        if(!s||s.path!=="dimensions"){expand.checked=false;return}
        restoring=true;expand.checked=true
        let p=s.dimension_plan
        for(let pair of [[methodChoice,s.method],[purpose,p.purpose],[targetColumn,s.y]])for(let i=0;i<pair[0].model.length;i++)if(pair[0].model[i].id===pair[1])pair[0].currentIndex=i
        for(let pair of [[targetKind,p.target_kind],[scaling,p.scaling],[missing,p.missing],[storage,p.storage]])pair[0].currentIndex=pair[0].model.indexOf(pair[1])
        for(let pair of [[question,s.question],[observation,s.observation_unit],[threshold,p.variance_threshold],[perplexity,p.perplexity],[profile,p.profile.join(",")]])pair[0].text=String(pair[1])
        components.value=p.components;folds.value=p.folds;innerFolds.value=p.inner_folds;batch.value=p.batch_size;neighbors.value=p.neighbors;seed.value=s.seed;iterations.value=s.max_iterations;features=s.features;independent.checked=s.independent;measurement.checked=s.measurement_confirmed;assumptions.checked=false;restoring=false
    }
    Connections {target:expertWorkspace;function onSelectMethod(path,name){if(path!=="dimensions"){expand.checked=false;return}expand.checked=true;for(let i=0;i<methodChoice.model.length;i++)if(methodChoice.model[i].id===name)methodChoice.currentIndex=i;panel.invalidate()}function onRestorePreset(value){panel.restore(JSON.parse(value))}}
    UiCheckBox {id:expand;objectName:"dimensionExpanded";text:"46 · Boyut indirgeme / özellik seçimi / amaç"}
    ColumnLayout {
        visible:panel.expanded;Layout.fillWidth:true;spacing:Theme.md
        RowLayout {
            Layout.fillWidth:true
            UiCombo {id:methodChoice;objectName:"dimensionMethod";model:statistics.methods("dimensions");textRole:"label";valueRole:"id";accessibleLabel:"Boyut/selection yöntemi";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiButton { visible: false;objectName:"dimensionHelp";text:"Bu ne işe yarar?";helpContext:"dimensions";onClicked:panel.helpRequested(this,"statistics."+panel.method.split("_").join("-"))}
        }
        UiLabel {objectName:"dimensionAvailability";text:panel.available?"Yerel backend mevcut; amaç/fit/transform sınırları aşağıda":"KAPALI · "+(methodChoice.currentIndex>=0?methodChoice.model[methodChoice.currentIndex].reason:"");color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.WordWrap}
        UiLabel {text:"Model girdisi: nested CV / development fit. Kompresyon: açık full-fit, CV hazır sayılmaz. Görsel keşif: target/test etiketi yok. t-SNE ve optional UMAP yalnız görsel; uzaklık/küme/boşluk gerçek sınıf değildir. Sayısal independent kapsam; metin/encoded/grup/zaman pipeline genişletmesi ayrı.";Layout.fillWidth:true;wrapMode:Text.WordWrap}
        GridLayout {
            columns:2;Layout.fillWidth:true
            UiLabel {text:"Amaç"}
            UiCombo {id:purpose;objectName:"dimensionPurpose";model:[{id:"model_input",name:"Model girdisi · nested CV"},{id:"compression",name:"Kompresyon · full fit"},{id:"visual",name:"Yalnız görsel keşif · full fit"}];currentIndex:1;textRole:"name";valueRole:"id";accessibleLabel:"Representation amacı / fit kapsamı";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Model target"}
            UiCombo {id:targetColumn;objectName:"dimensionTarget";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Nested CV target; görselde kullanılmaz";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Target türü"}
            UiCombo {id:targetKind;objectName:"dimensionTargetKind";model:["regression","binary"];accessibleLabel:"Regression veya0/1 binary target";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Scaling"}
            UiCombo {id:scaling;objectName:"dimensionScaling";model:["none","standard","standard_no_center"];currentIndex:1;accessibleLabel:"Ölçekleme; CSR/NMF centering ret";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Missing"}
            UiCombo {id:missing;objectName:"dimensionMissing";model:["reject","mean"];accessibleLabel:"Missing reject veya train-only mean";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Matrix storage"}
            UiCombo {id:storage;objectName:"dimensionStorage";model:["dense","csr"];accessibleLabel:"Açık table→CSR yalnız SVD/NMF";Layout.fillWidth:true;onActivated:panel.invalidate()}
            UiLabel {text:"Soru"}
            UiTextField {id:question;objectName:"dimensionQuestion";text:"Representation sorusu";Accessible.name:"Soru";placeholderText:"Soru";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Bağımsız analiz birimi"}
            UiTextField {id:observation;objectName:"dimensionObservation";text:"sat\u0131r";Accessible.name:"Bağımsız analiz birimi";placeholderText:"Bağımsız analiz birimi";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Variance threshold · ham birim²"}
            UiTextField {id:threshold;objectName:"dimensionThreshold";text:"0";Accessible.name:"Variance threshold · ham birim²";placeholderText:"Variance threshold · ham birim²";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"t-SNE perplexity"}
            UiTextField {id:perplexity;objectName:"dimensionPerplexity";text:"5";Accessible.name:"t-SNE perplexity";placeholderText:"t-SNE perplexity";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Preview profili · feature sırası"}
            UiTextField {id:profile;objectName:"dimensionProfile";text:"";Accessible.name:"Preview profili · feature sırası";placeholderText:"Preview profili · feature sırası";Layout.fillWidth:true;onTextEdited:panel.invalidate()}
            UiLabel {text:"Bileşen / seçili k (variance için eşik kullanılır)"}
            UiSpinBox {id:components;objectName:"dimensionComponents";enabled:panel.method!=="dimension_variance";from:1;to:20;value:2;Accessible.name:"Bileşen veya seçili k";onValueModified:panel.invalidate()}
            UiLabel {text:"Outer development folds"}
            UiSpinBox {id:folds;objectName:"dimensionFolds";from:2;to:5;value:3;Accessible.name:"Outer development folds";onValueModified:panel.invalidate()}
            UiLabel {text:"Inner folds"}
            UiSpinBox {id:innerFolds;objectName:"dimensionInnerFolds";from:2;to:3;value:2;Accessible.name:"Inner folds";onValueModified:panel.invalidate()}
            UiLabel {text:"Incremental PCA batch"}
            UiSpinBox {id:batch;objectName:"dimensionBatch";from:10;to:1000;value:30;Accessible.name:"Incremental PCA batch";onValueModified:panel.invalidate()}
            UiLabel {text:"UMAP neighbors"}
            UiSpinBox {id:neighbors;objectName:"dimensionNeighbors";from:3;to:50;value:5;Accessible.name:"UMAP neighbors";onValueModified:panel.invalidate()}
            UiLabel {text:"Seed"}
            UiSpinBox {id:seed;objectName:"dimensionSeed";from:0;to:1000000000;value:42;Accessible.name:"Seed";onValueModified:panel.invalidate()}
            UiLabel {text:"Iteration bütçesi"}
            UiSpinBox {id:iterations;objectName:"dimensionIterations";from:300;to:1000;value:1000;Accessible.name:"Iteration bütçesi";onValueModified:panel.invalidate()}
        }
        RowLayout {
            Layout.fillWidth:true
            UiCombo {id:feature;objectName:"dimensionFeature";model:panel.columns;textRole:"name";valueRole:"id";accessibleLabel:"Numeric feature ekle";Layout.fillWidth:true}
            UiButton {objectName:"dimensionAddFeature";text:"Feature ekle";onClicked:{if(feature.currentValue&&!panel.features.includes(feature.currentValue)){panel.features=panel.features.concat([feature.currentValue]);panel.invalidate()}}}
            UiButton {text:"Feature temizle";onClicked:{panel.features=[];panel.invalidate()}}
        }
        UiLabel {text:"Feature sırası: "+panel.features.map(panel.label).join(", ");Layout.fillWidth:true;wrapMode:Text.WordWrap}
        UiLabel {text:"NMF non-negative: centering/shift/clip otomatik değil. CSR centering kapalı; kaynak tablo yine bounded dense okunur, maliyet hesaba katılır. Missing tümü eksik train sütunu ret. Variance ham ölçekte; model/univariate/RFE/sequential selection target yalnız training pipeline içinde. k/parametreler önceden seçilir; inner skorlar sonradan best-k diye değiştirilmez.";Layout.fillWidth:true;wrapMode:Text.WordWrap}
        UiCheckBox {id:measurement;objectName:"dimensionMeasurement";text:"Baseline numeric ölçümleri/ölçekleri ve target ile ayrı feature seçimini doğruladım";onToggled:panel.invalidate()}
        UiCheckBox {id:independent;objectName:"dimensionIndependent";text:"Bağımsız satırlar; group/time desteği olmadan rastgele fallback istemiyorum";onToggled:panel.invalidate()}
        UiButton {objectName:"dimensionPreflight";text:"Amaç / maliyet / nested fit önkontrolü";enabled:panel.available&&!statistics.busy;onClicked:statistics.create(JSON.stringify(panel.spec()),true)}
        UiLabel {objectName:"dimensionPreview";visible:statistics.preflightCurrent&&statistics.preflightResult.dimensions===true;text:panel.describe(statistics.preflightResult);Layout.fillWidth:true;wrapMode:Text.WordWrap}
        UiCheckBox {id:assumptions;objectName:"dimensionAssumptions";text:"Fit kapsamı, nested CV/kompresyon farkı, loading ve embedding sınırlarını inceledim";enabled:statistics.preflightCurrent}
        RowLayout {
            UiButton {objectName:"dimensionRun";text:"Temsil / selection hesapla";enabled:panel.available&&!statistics.busy&&assumptions.checked;onClicked:statistics.create(JSON.stringify(panel.spec()),false)}
            UiButton {objectName:"dimensionCancel";text:"İptal";enabled:statistics.busy;onClicked:statistics.cancel()}
        }
        UiLabel {text:statistics.message;Layout.fillWidth:true;wrapMode:Text.WordWrap}
        UiLabel {objectName:"dimensionError";text:statistics.errorText;visible:!!statistics.errorText;color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.WordWrap}
        UiLabel {objectName:"dimensionResult";visible:statistics.analysisResult.dimensions===true;text:panel.describe(statistics.analysisResult);Layout.fillWidth:true;wrapMode:Text.WordWrap}
        Image {objectName:"dimensionPlot";visible:statistics.analysisResult.dimensions===true&&!!statistics.modelDiagnostic;source:statistics.analysisResult.dimensions?statistics.modelDiagnostic:"";Layout.fillWidth:true;Layout.preferredHeight:400;fillMode:Image.PreserveAspectFit}
        ColumnLayout {
            objectName:"dimensionLoadings";visible:statistics.analysisResult.dimensions===true;Layout.fillWidth:true
            UiLabel {text:"Loadings / directions · feature sırası ve tanımı korunur"}
            Repeater {
                model:statistics.analysisResult.dimensions&&statistics.analysisResult.dimension_analysis.directions?statistics.analysisResult.dimension_analysis.directions:[]
                UiLabel {required property var modelData;required property int index;text:panel.label(statistics.analysisResult.spec.features[index])+" · direction="+modelData.map(panel.number).join(", ")+" · loading="+(statistics.analysisResult.dimension_analysis.loadings?statistics.analysisResult.dimension_analysis.loadings[index].map(panel.number).join(", "):"bu yöntemde yok");Layout.fillWidth:true;wrapMode:Text.WordWrap}
            }
        }
        RowLayout {
            Layout.fillWidth:true
            UiTextField {id:matrix;objectName:"dimensionMatrix";Accessible.name:"Safe numeric new-data veya inverse matrix JSON";placeholderText:"[[feature1,feature2,...]] / inverse latent matrix";Layout.fillWidth:true}
            UiButton {objectName:"dimensionTransform";text:"Yeni veri transform";enabled:statistics.current&&!statistics.busy&&statistics.analysisResult.dimensions===true&&statistics.analysisResult.dimension_analysis.model.transform_supported;onClicked:statistics.transformDimension(matrix.text,false)}
            UiButton {objectName:"dimensionInverse";text:"Yaklaşık inverse";enabled:statistics.current&&!statistics.busy&&statistics.analysisResult.dimensions===true&&statistics.analysisResult.dimension_analysis.model.inverse_supported;onClicked:statistics.transformDimension(matrix.text,true)}
        }
        UiLabel {objectName:"dimensionTransformResult";text:JSON.stringify(statistics.dimensionTransform);Layout.fillWidth:true;wrapMode:Text.WordWrap}
        RowLayout {
            Layout.fillWidth:true
            UiButton {objectName:"dimensionSave";text:"Fit / RowId / CV ile kaydet";enabled:statistics.current&&!statistics.busy&&statistics.analysisResult.dimensions===true;onClicked:statistics.save()}
            UiTextField {id:exportPath;objectName:"dimensionExportPath";Accessible.name:placeholderText;placeholderText:"Yeni mutlak export klasörü";Layout.fillWidth:true}
            UiButton {objectName:"dimensionExport";text:"Temsil / JSON / PNG export";enabled:statistics.current&&!statistics.busy&&statistics.analysisResult.dimensions===true;onClicked:statistics.exportAdvanced(exportPath.text)}
        }
        RowLayout {
            Layout.fillWidth:true
            UiCombo {id:saved;objectName:"dimensionSaved";model:statistics.savedAnalyses.filter(v=>v.path==="dimensions");textRole:"label";valueRole:"id";accessibleLabel:"Kayıtlı representation / selection";Layout.fillWidth:true}
            UiButton {objectName:"dimensionOpen";text:"Kaydı/modeli aç";enabled:!!saved.currentValue&&!statistics.busy;onClicked:{statistics.openSaved(saved.currentValue);panel.restore(statistics.analysisResult.spec)}}
        }
    }
}
