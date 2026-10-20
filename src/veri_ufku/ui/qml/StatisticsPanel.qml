import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "statisticsPanel"
    property string helpContext: "statistics"
    property var pathValues: ["independent", "paired", "groups", "categorical", "numeric"]
    readonly property string path: pathValues[pathChoice.currentIndex]
    signal helpRequested(var origin, string context)
    spacing: Theme.md
    function key(picker) { return picker.currentIndex >= 0 ? picker.currentValue : "" }
    function spec() {
        if(advancedMode.checked)return advancedPanel.spec()
        return {path:path, method:key(method), x:key(x), y:(path==="numeric"||path==="categorical") ? key(y):"", group:(path==="independent"||path==="groups"||path==="paired") ? key(group):"", key:path==="paired" ? key(person):"", before:before.text, after:after.text, pair_policy:pairPolicy.currentIndex===0 ? "reject":"complete", question:question.text, hypothesis:hypothesis.text, unit:unit.text, observation_unit:observation.text, independent:independent.checked, measurement_confirmed:measurement.checked, assumptions_confirmed:assumptions.checked, alternative:["two-sided","less","greater"][alternative.currentIndex], confidence:[.95,.90,.99][confidence.currentIndex], scope:scope.currentIndex===0 ? "view":"full", precision:approximate.checked ? "approximate":"reject", posthoc:path==="groups" && posthoc.checked ? "pairwise":"none", correction:["holm","bonferroni","bh","none"][correction.currentIndex]}
    }
    function restore() {
        let s=arguments.length ? arguments[0] : statistics.analysisResult.spec
        if(!s) return
        if(s.path==="models"||s.path==="resampling"||s.path==="experiments"||s.path==="bayes"||s.path==="causal"||s.path==="survival"||s.path==="dimensions")return
        if(s.path==="advanced"){advancedMode.checked=true;advancedPanel.restore(s);return}
        advancedMode.checked=false
        pathChoice.currentIndex=pathValues.indexOf(s.path)
        for(let i=0;i<method.model.length;i++) if(method.model[i].id===s.method) method.currentIndex=i
        for(let p of [x,y,group,person]) for(let i=0;i<p.model.length;i++) {
            let id=p===x?s.x:p===y?s.y:p===group?s.group:s.key
            if(p.model[i].id===id) p.currentIndex=i
        }
        question.text=s.question;hypothesis.text=s.hypothesis;unit.text=s.unit;observation.text=s.observation_unit
        before.text=s.before;after.text=s.after;pairPolicy.currentIndex=s.pair_policy==="reject"?0:1
        independent.checked=s.independent;measurement.checked=s.measurement_confirmed;assumptions.checked=false
        alternative.currentIndex=["two-sided","less","greater"].indexOf(s.alternative)
        confidence.currentIndex=[.95,.90,.99].indexOf(s.confidence)
        scope.currentIndex=s.scope==="view"?0:1;approximate.checked=s.precision==="approximate"
        posthoc.checked=s.posthoc==="pairwise";correction.currentIndex=["holm","bonferroni","bh","none"].indexOf(s.correction)
        settings.checked=false
    }
    Connections {
        target: expertWorkspace
        function onSelectMethod(path, name) {
            if(path==="models"||path==="resampling"||path==="experiments"||path==="bayes"||path==="causal"||path==="survival"||path==="dimensions")return
            if(path==="advanced"){advancedMode.checked=true;advancedPanel.select(name);statistics.invalidate();return}
            advancedMode.checked=false
            pathChoice.currentIndex=panel.pathValues.indexOf(path)
            for(let i=0;i<method.model.length;i++) if(method.model[i].id===name) method.currentIndex=i
            assumptions.checked=false
            statistics.invalidate()
            settings.checked=true
        }
        function onRestorePreset(value) { panel.restore(JSON.parse(value)); settings.checked=true }
    }
    function exclusions(e) {
        e=e||{}
        return "Eksik alanlı kayıt: "+(e.null_rows||0)+" · sonlu olmayan değer: "+(e.nonfinite_rows||0)+" · eksik/geçersiz kişi anahtarı: "+(e.missing_key_rows||0)+" · eşleşmeyen kişi: "+(e.unmatched_people||0)+" · eksik ölçümlü çift: "+(e.incomplete_pairs||0)+" · seçilmeyen ölçüm etiketi: "+(e.unselected_phase_rows||0)
    }
    function correctionText(c) {
        c=c||{}
        let names={holm:"Holm",bonferroni:"Bonferroni",bh:"Benjamini–Hochberg (FDR)",none:"Düzeltme yok"}
        return "Düzeltme seçimi: "+(names[c.method]||"")+" · "+(c.family==="all selected group pairs" ? "Bütün seçili grup çiftleri":"Tek analiz; düzeltilecek çift ailesi yok")+" · aile büyüklüğü: "+(c.family_size||1)+". Bu çalıştırma ile sınırlı; güven aralıkları aile için düzeltilmedi."
    }
    function statistic(method) { return {welch_t:"t",paired_t:"t",mann_whitney:"U",wilcoxon:"W",anova:"F",welch_anova:"F",kruskal:"H",chi2:"Ki-kare",fisher:"Örneklem odds oranı",pearson:"r",spearman:"rho"}[method]||"İstatistik" }
    function number(value) { return typeof value==="number" ? Number(value).toPrecision(6) : value===null ? "sunulmuyor" : String(value) }
    function pvalue(value) { return value===0 ? "0 (Float64 alt sınırı; kesinlik değildir)" : number(value) }
    function interval(effect) {
        if(!effect) return ""
        let c=effect.confidence_interval
        return c ? "%"+Math.round(c.level*100)+" güven aralığı: ["+number(c.low)+", "+number(c.high)+"] · "+c.method+" · "+c.target : "Güven aralığı: "+effect.ci_limitation
    }
    UiCheckBox { id:advancedMode; objectName:"missingMode";text:"Eksik veri, örnekleme ve ağırlıklar";Layout.fillWidth:true;onClicked:statistics.invalidate() }
    MissingSamplingPanel { id:advancedPanel;visible:advancedMode.checked;Layout.fillWidth:true;onHelpRequested:(origin,context)=>panel.helpRequested(origin,context) }
    ColumnLayout {
    visible:!advancedMode.checked
    Layout.fillWidth:true
        RowLayout {
        visible: preferences && preferences.view === "advanced"
        Layout.fillWidth: true
        UiTextField { id: presetName; objectName: "presetName"; Accessible.name: "Preset adı"; placeholderText: "Parametre presetinin adı"; maximumLength:80; Layout.fillWidth:true }
        UiButton { objectName:"savePreset"; text:"Parametre presetini kaydet"; onClicked:expertWorkspace.savePreset(presetName.text, JSON.stringify(panel.spec())) }
    }
    UiLabel { text:"İstatistiksel analiz — sorundan sonuca"; font.pixelSize:Theme.heading; font.bold:true; Layout.fillWidth:true; wrapMode:Text.Wrap }
    UiLabel { text:"p-değeri hipotezin doğru olma olasılığı değildir. Küçük p kesinlik veya pratik önem göstermez; gözlemsel ilişki nedensellik değildir."; color:Theme.warning; Layout.fillWidth:true; wrapMode:Text.Wrap }
    UiCheckBox { id:settings; objectName:"statisticsSettings"; text:"Soru ve yöntem ayarlarını göster"; checked:true; Layout.fillWidth:true }
    ColumnLayout {
    visible:settings.checked; Layout.fillWidth:true; spacing:Theme.md
    UiCombo { accessibleLabel: qsTr("Veri kümesi"); objectName:"statisticsDataset"; model:dataView.datasets; textRole:"label"; valueRole:"id"; Layout.fillWidth:true; Layout.minimumWidth:0; onActivated:{dataView.selectDataset(currentValue);statistics.invalidate()} }
    UiLabel { text:dataView.viewSummary; Layout.fillWidth:true; wrapMode:Text.Wrap; color:Theme.secondary }
    UiLabel { text:"Ne öğrenmek istiyorsun?"; Layout.fillWidth:true }
    UiTextField { id:question; objectName:"statisticsQuestion"; placeholderText:"Örneğin: iki şubenin ortalama satış tutarı farklı mı?"; maximumLength:1000; Layout.fillWidth:true; onTextEdited:statistics.invalidate(); Accessible.name:"Araştırma sorusu" }
    UiCombo { accessibleLabel: "Araştırma sorusu türü"; id:pathChoice; objectName:"statisticsPath"; model:["İki bağımsız grubu karşılaştır","Aynı kişilerin önce/sonra ölçümü","Üç veya daha fazla bağımsız grup","İki kategori arasında ilişki","İki sayısal ölçüm arasında ilişki"]; Layout.fillWidth:true; onActivated:{method.currentIndex=0;assumptions.checked=false;statistics.invalidate()} }
    GridLayout {
        columns:panel.width>650 ? 2:1
        Layout.fillWidth:true
        UiLabel { text:panel.path==="categorical" ? "İlk kategori":"Ölçüm / ilk sayısal alan"; Layout.fillWidth:true }
        UiCombo { accessibleLabel: "İlk ölçüm sütunu"; id:x; objectName:"statisticsX"; model:statistics.columns; textRole:"name"; valueRole:"id"; Layout.fillWidth:true; Layout.minimumWidth:0; onActivated:{unit.text=model[currentIndex].unit||unit.text;statistics.invalidate()} }
        UiLabel { text:panel.path==="categorical" ? "İkinci kategori":"İkinci sayısal ölçüm"; visible:panel.path==="numeric"||panel.path==="categorical"; Layout.fillWidth:true }
        UiCombo { accessibleLabel: "İkinci ölçüm sütunu"; id:y; objectName:"statisticsY"; model:statistics.columns; textRole:"name"; valueRole:"id"; Layout.fillWidth:true; Layout.minimumWidth:0; visible:panel.path==="numeric"||panel.path==="categorical"; onActivated:statistics.invalidate() }
        UiLabel { text:panel.path==="paired" ? "Önce/sonra etiketi sütunu":"Grup sütunu"; visible:panel.path==="independent"||panel.path==="groups"||panel.path==="paired"; Layout.fillWidth:true }
        UiCombo { accessibleLabel: "Grup sütunu"; id:group; objectName:"statisticsGroup"; model:statistics.columns; textRole:"name"; valueRole:"id"; Layout.fillWidth:true; Layout.minimumWidth:0; visible:panel.path==="independent"||panel.path==="groups"||panel.path==="paired"; onActivated:statistics.invalidate() }
        UiLabel { text:"Kişi/deney birimi anahtarı (satır sırası kullanılmaz)"; visible:panel.path==="paired"; Layout.fillWidth:true; wrapMode:Text.Wrap }
        UiCombo { accessibleLabel: "Kişi anahtarı"; id:person; objectName:"statisticsKey"; model:statistics.columns; textRole:"name"; valueRole:"id"; Layout.fillWidth:true; Layout.minimumWidth:0; visible:panel.path==="paired"; onActivated:statistics.invalidate() }
    }
    ColumnLayout {
        visible:panel.path==="paired"; Layout.fillWidth:true
        UiLabel { text:"Uzun tablo: her kişi/etiket için tek kayıt. Önce ve sonra etiketleri birebir eşleşir."; Layout.fillWidth:true; wrapMode:Text.Wrap }
        UiTextField { id:before; objectName:"statisticsBefore"; text:"önce"; placeholderText:"Önce etiketi"; maximumLength:256; Layout.fillWidth:true; onTextEdited:statistics.invalidate(); Accessible.name:"Önce ölçüm etiketi" }
        UiTextField { id:after; objectName:"statisticsAfter"; text:"sonra"; placeholderText:"Sonra etiketi"; maximumLength:256; Layout.fillWidth:true; onTextEdited:statistics.invalidate(); Accessible.name:"Sonra ölçüm etiketi" }
        UiCombo { accessibleLabel: "Eksik eş politikası"; id:pairPolicy; objectName:"statisticsPairPolicy"; model:["Eşleşmeyen kişi varsa dur","Yalnız tam eşler; eksik/eşleşmeyen kişileri raporla"]; Layout.fillWidth:true; onActivated:statistics.invalidate() }
    }
    UiLabel { text:"Ölçüm birimi ve bağımsız gözlem birimi"; Layout.fillWidth:true }
    UiTextField { id:unit; objectName:"statisticsUnit"; placeholderText:"TL / kg / ilk alan kg, ikinci cm / kategorik: birimsiz"; maximumLength:1000; Layout.fillWidth:true; onTextEdited:statistics.invalidate(); Accessible.name:"Ölçüm birimi" }
    UiTextField { id:observation; objectName:"statisticsObservation"; placeholderText:"Kişi / bağımsız deney / satış kaydı"; maximumLength:1000; Layout.fillWidth:true; onTextEdited:statistics.invalidate(); Accessible.name:"Bağımsız gözlem birimi" }
    UiCheckBox { id:measurement; objectName:"statisticsMeasurement"; text:"Alanların ölçüm/kategori rolünü kontrol ettim; sayısal kimlikleri ölçüm saymıyorum"; Layout.fillWidth:true; onClicked:statistics.invalidate() }
    UiCheckBox { id:independent; objectName:"statisticsIndependent"; text:panel.path==="paired" ? "Farklı kişiler bağımsızdır; kişi içi eşleri anahtarla koruyorum":"Gözlem birimleri bağımsızdır; tekrar/zaman/küme bağımlılığını inceledim"; Layout.fillWidth:true; onClicked:statistics.invalidate() }
    UiLabel { text:"Sınamak istediğin hipotez ve yöntem"; Layout.fillWidth:true }
    UiTextField { id:hypothesis; objectName:"statisticsHypothesis"; placeholderText:"H0: grup ortalamaları eşittir; araştırma bağlamı..."; maximumLength:1000; Layout.fillWidth:true; onTextEdited:statistics.invalidate(); Accessible.name:"Hipotez bağlamı" }
    UiCombo { accessibleLabel: "Karşılaştırma yöntemi"; id:method; objectName:"statisticsMethod"; model:statistics.methods(panel.path); textRole:"label"; valueRole:"id"; Layout.fillWidth:true; Layout.minimumWidth:0; onActivated:{assumptions.checked=false;statistics.invalidate()} }
    UiCombo { accessibleLabel: "Hipotez yönü"; id:alternative; objectName:"statisticsAlternative"; model:["İki yönlü (fark/ilişki)","İlk grup/sonra < ikinci grup/önce; ilişkide negatif","İlk grup/sonra > ikinci grup/önce; ilişkide pozitif"]; Layout.fillWidth:true; onActivated:statistics.invalidate() }
    UiLabel { text:"ANOVA/Kruskal/ki-kare iki yönlü seçeneği kullanır. Bağımsız grupların yön sırası önkontrolde görünen etiket sırasıdır."; Layout.fillWidth:true; wrapMode:Text.Wrap; color:Theme.secondary }
    UiCombo { accessibleLabel: "Güven düzeyi"; id:confidence; objectName:"statisticsConfidence"; model:["%95 güven düzeyi","%90 güven düzeyi","%99 güven düzeyi"]; Layout.fillWidth:true; onActivated:statistics.invalidate() }
    UiCombo { accessibleLabel: "Karşılaştırma kapsamı"; id:scope; objectName:"statisticsScope"; model:["Mevcut tablo filtresinin tamamı","Tam dataset (filtreleri kullanma)"]; Layout.fillWidth:true; onActivated:statistics.invalidate() }
    UiCheckBox { id:approximate; objectName:"statisticsApproximate"; text:"Integer/Decimal → Float64 yaklaşık hesap kaybına açık izin ver"; Layout.fillWidth:true; onClicked:statistics.invalidate() }
    UiCheckBox { id:posthoc; objectName:"statisticsPosthoc"; text:"Bütün grup çiftlerini ayrıca karşılaştır (post-hoc ailesi)"; visible:panel.path==="groups"; Layout.fillWidth:true; onClicked:statistics.invalidate() }
    UiCombo { accessibleLabel: "Çoklu karşılaştırma düzeltmesi"; id:correction; objectName:"statisticsCorrection"; model:["Holm — aile hata kontrolü","Bonferroni — aile hata kontrolü","Benjamini–Hochberg — FDR, bağımsız/pozitif bağımlı testler","Düzeltme yok (açık seçim)"]; Layout.fillWidth:true; onActivated:statistics.invalidate() }
    UiLabel { text:"Düzeltme bu çalıştırmanın grup çiftlerine uygulanır; ayrı çalıştırmalar otomatik birleşmez. Normalite tek başına yöntemi seçmez. Dağılım/uç değer grafikleri İncele alanındadır. Bootstrap bu sürümde sunulmuyor."; Layout.fillWidth:true; wrapMode:Text.Wrap; color:Theme.secondary }
    Flow {
        Layout.fillWidth:true; spacing:Theme.sm
        UiButton { objectName:"statisticsPreflight"; text:"Önkontrolü çalıştır"; tone:"violet"; enabled:!projects.busy && dataView.datasets.length>0; onClicked:{assumptions.checked=false;statistics.create(JSON.stringify(panel.spec()),true)} }
        UiButton { tone:"mint"; text:qsTr("Bu ne işe yarar?"); helpContext:"statistics"; onClicked:panel.helpRequested(this,"statistics") }
        UiButton { tone:"mint"; text:"Seçilen yöntemi öğren"; helpContext:"statistics"; onClicked:panel.helpRequested(this,"statistics."+panel.key(method).replace(/_/g,"-")) }
        UiButton { text:qsTr("İptal"); enabled:statistics.busy; onClicked:statistics.cancel() }
    }
    }
    StateNotice { Layout.fillWidth:true; kind:statistics.errorText ? "error":statistics.busy ? "loading":"info"; heading:"Analiz durumu"; detail:statistics.errorText||statistics.message }
    ColumnLayout {
        visible:statistics.preflightCurrent && settings.checked; Layout.fillWidth:true
        UiLabel { text:"Önkontrol · n: "+JSON.stringify(statistics.preflightResult.n)+" · sıra: "+(statistics.preflightResult.group_labels||[]).join(" / ")+"\nKapsam: "+statistics.preflightResult.population_n+" · kullanılan kayıt: "+statistics.preflightResult.used_rows+" · dışlanan: "+statistics.preflightResult.excluded_rows; Layout.fillWidth:true; wrapMode:Text.Wrap }
        Repeater { model:statistics.preflightResult.summaries||[]; UiLabel { required property var modelData; text:modelData.label+" · n="+modelData.n+" · ortalama="+panel.number(modelData.mean)+" · standart sapma="+panel.number(modelData.std); Layout.fillWidth:true; wrapMode:Text.Wrap } }
        UiLabel { visible:!!statistics.preflightResult.difference_summary; text:statistics.preflightResult.difference_summary ? "Kişi içi sonra−önce farkları: n="+statistics.preflightResult.difference_summary.n+" · ortalama="+panel.number(statistics.preflightResult.difference_summary.mean)+" · standart sapma="+panel.number(statistics.preflightResult.difference_summary.std)+" · sıfır fark="+statistics.preflightResult.difference_summary.zero_differences : ""; Layout.fillWidth:true; wrapMode:Text.Wrap }
        Repeater { model:statistics.preflightResult.warnings||[]; UiLabel { required property string modelData; text:modelData; color:Theme.warning; Layout.fillWidth:true; wrapMode:Text.Wrap } }
        UiLabel { text:panel.exclusions(statistics.preflightResult.exclusions)+"\n"+(statistics.preflightResult.table ? "Satır kategorileri: "+(statistics.preflightResult.row_labels||[]).join(" / ")+" · sütun kategorileri: "+(statistics.preflightResult.column_labels||[]).join(" / ")+"\nGözlenen frekans: "+JSON.stringify(statistics.preflightResult.table)+"\nBeklenen frekans: "+JSON.stringify(statistics.preflightResult.expected):""); Layout.fillWidth:true; wrapMode:Text.Wrap }
        UiCheckBox { id:assumptions; objectName:"statisticsAssumptions"; text:"Önkontrolü, dağılım/uç değerleri, bağımsızlığı ve seçili yöntemin hipotezini inceledim"; Layout.fillWidth:true }
    }
    UiButton { objectName:"statisticsRun"; text:"Analizi çalıştır"; primary:true; tone:"violet"; enabled:statistics.preflightCurrent && assumptions.checked && !projects.busy; onClicked:{statistics.create(JSON.stringify(panel.spec()),false);settings.checked=false} }
    UiButton { text:qsTr("İptal"); visible:statistics.busy && !settings.checked; onClicked:statistics.cancel() }
    ColumnLayout {
        visible:!!statistics.analysisResult.primary; Layout.fillWidth:true
        UiLabel { objectName:"statisticsResultScope"; text:(statistics.current ? "Güncel veri/filtre sonucu":"Kayıtlı veya eski veri/yapılandırma sonucu — sürümü kontrol edin")+"\nSoru: "+(statistics.analysisResult.spec ? statistics.analysisResult.spec.question:"")+"\nSürüm: "+(statistics.analysisResult.dataset_version||""); Layout.fillWidth:true; wrapMode:Text.Wrap; font.bold:true }
        UiLabel { objectName:"statisticsPrimary"; text:statistics.analysisResult.primary && statistics.analysisResult.primary.effect ? statistics.analysisResult.method_label+"\nn="+JSON.stringify(statistics.analysisResult.n)+" · dışlanan kayıt="+statistics.analysisResult.excluded_rows+"\n"+panel.statistic(statistics.analysisResult.method)+"="+panel.number(statistics.analysisResult.primary.statistic)+" · p="+panel.pvalue(statistics.analysisResult.primary.p_value)+"\n"+statistics.analysisResult.primary.effect.name+"="+panel.number(statistics.analysisResult.primary.effect.value)+"\n"+panel.interval(statistics.analysisResult.primary.effect):""; Layout.fillWidth:true; wrapMode:Text.Wrap }
        UiLabel { text:statistics.analysisResult.table ? "Satır kategorileri: "+(statistics.analysisResult.row_labels||[]).join(" / ")+"\nSütun kategorileri: "+(statistics.analysisResult.column_labels||[]).join(" / ")+"\nGözlenen frekans: "+JSON.stringify(statistics.analysisResult.table) : "Alan/grup sırası: "+(statistics.analysisResult.group_labels||[]).join(" / "); Layout.fillWidth:true; wrapMode:Text.Wrap }
        UiLabel { text:statistics.analysisResult.spec ? "Hipotez bağlamı: "+statistics.analysisResult.spec.hypothesis+"\nÖlçüm birimi: "+statistics.analysisResult.spec.unit+" · gözlem birimi: "+statistics.analysisResult.spec.observation_unit : ""; Layout.fillWidth:true; wrapMode:Text.Wrap }
        Repeater { model:statistics.analysisResult.warnings||[]; UiLabel { required property string modelData; text:modelData; Layout.fillWidth:true; wrapMode:Text.Wrap; color:Theme.warning } }
        Repeater { model:statistics.analysisResult.comparisons||[]; UiLabel { required property var modelData; text:modelData.groups.join(" / ")+" · n="+JSON.stringify(modelData.n)+" · istatistik="+panel.number(modelData.statistic)+" · p="+panel.pvalue(modelData.p_value)+" · düzeltilmiş p="+panel.pvalue(modelData.p_adjusted)+"\n"+modelData.effect.name+"="+panel.number(modelData.effect.value)+"\n"+panel.interval(modelData.effect); Layout.fillWidth:true; wrapMode:Text.Wrap } }
        UiLabel { text:panel.correctionText(statistics.analysisResult.correction)+"\n"+panel.exclusions(statistics.analysisResult.exclusions); Layout.fillWidth:true; wrapMode:Text.Wrap }
        Flow { Layout.fillWidth:true; spacing:Theme.sm
            UiButton { objectName:"statisticsSave"; text:"Analizi projeye kaydet"; enabled:statistics.current && !projects.busy && !projects.readOnly; onClicked:statistics.save() }
            UiButton { tone:"mint"; text:"p, etki ve güven aralığını yorumla"; helpContext:"statistics.pvalue"; onClicked:panel.helpRequested(this,"statistics.pvalue") }
        }
    }
    UiCombo { accessibleLabel: "Kayıtlı karşılaştırma"; id:saved; objectName:"statisticsSaved"; model:statistics.savedAnalyses.filter(r=>r.path!=="models"&&r.path!=="resampling"&&r.path!=="experiments"&&r.path!=="bayes"&&r.path!=="causal"&&r.path!=="survival"&&r.path!=="dimensions"); textRole:"label"; valueRole:"id"; Layout.fillWidth:true; Layout.minimumWidth:0 }
    UiButton { text:"Kayıtlı analizi aç"; enabled:saved.currentIndex>=0 && !projects.busy; onClicked:{statistics.openSaved(saved.currentValue);panel.restore()} }
    }
}
