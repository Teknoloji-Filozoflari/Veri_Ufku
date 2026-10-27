import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "classificationPanel"
    property var protocol
    property bool protocolBlocked: false
    property string helpContext: "model.classification"
    readonly property var report: validation.summaryReport.classification && !validation.summaryReport.uncertainty ? validation.summaryReport : ({})
    readonly property var distribution: (preparation.report.target || {}).class_distribution || []
    signal helpRequested(var origin, string context)
    spacing: Theme.md
    visible: !!preparation.report.spec && preparation.report.spec.purpose === "classification"
    property string pipelineId: ""
    Connections { target:preparation;function onChanged(){let id=(preparation.report.plan||{}).version_id||"";if(panel.pipelineId!==id){panel.pipelineId=id;positive.currentIndex=-1;thresholdMode.currentIndex=0;averaging.currentIndex=0}} }
    function status(value){return value==="valid"?"tanımlı":value==="undefined_no_predictions"?"hiç tahmin yok":value==="undefined_absent_class"?"bu bölümde sınıf yok":"gerçek veya tahmin edilmiş kayıt yok"}
    function config() {
        let candidates = ["baseline"]
        if (logistic.checked) candidates.push("logistic")
        if (forest.checked) candidates.push("forest")
        return {candidates:candidates, C:[0.1,1,10][regularization.currentIndex], trees:[25,50,100][trees.currentIndex], depth:[4,8,12][depth.currentIndex], averaging:["macro","weighted","micro","binary"][averaging.currentIndex], positive_class:panel.distribution.length===2 && positive.currentIndex >= 0 ? positive.currentValue : "", threshold_mode:["default","validation_manual","validation_f1"][thresholdMode.currentIndex], threshold:thresholdMode.currentIndex === 1 ? Number(threshold.text) : 0.5, cost_note:cost.text}
    }
    UiLabel { text:"Bir kategori tahmin etmek istiyorum";font.pixelSize:Theme.heading;font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:"Önce kategori hedefini ve özelliklerini hazırlıkta seç. Baseline en sık sınıf/öncül referansıdır; LogisticRegression düzenlileştirilmiş doğrusal karar, RandomForest sınırlı ağaçlarla doğrusal olmayan karar öğrenir. Scaling LogisticRegression için önerilir. Forest 20.000, diğer adaylar 100.000 kayıt; en fazla 20 sınıf. Öğrenilen hazırlık yalnız train/fold içinde; resampling yok.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:"Sınıf dağılımı — tüm kaynakta; model seçimi yalnız geliştirme CV üzerinde";font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
    Repeater { model:panel.distribution;UiLabel { required property var modelData;text:modelData.label+" · "+modelData.count+" kayıt";Layout.fillWidth:true;wrapMode:Text.Wrap } }
    UiLabel { text:"100 kaydın 95'i normal, 5'i sorunluysa her kayda normal demek %95 accuracy verir; sorunlu 5 kaydın hiçbirini bulamaz. Azınlık sınıfının recall ve F1 değerlerine de bak.";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { visible:panel.distribution.length===2;text:"Pozitif sınıf — bulmak istediğin kategori (ör. sorunlu)";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCombo { accessibleLabel: "Pozitif sınıf"; id:positive;visible:panel.distribution.length===2;objectName:"classificationPositive";property string helpContext:"classification.positive";model:panel.distribution;textRole:"label";valueRole:"label";currentIndex:-1;Layout.fillWidth:true;onActivated:validation.invalidate() }
    UiLabel { text:"Macro: her sınıfa eşit önem. Weighted: kayıt sayısıyla ağırlıklı. Micro: tek etiketli hedefte toplam doğru oranı. Binary: yalnız seçilen pozitif sınıf; sadece ikili hedef. Aynı strateji CV aday seçiminde F1 için kullanılır.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCombo { accessibleLabel: "Sınıf metriklerini birleştirme"; id:averaging;objectName:"classificationAveraging";model:["Macro — her sınıf eşit","Weighted — sınıf sayısıyla ağırlıklı","Micro — tüm kayıtlar birlikte","Binary — pozitif sınıf"];Layout.fillWidth:true;onActivated:validation.invalidate() }
    UiCheckBox { id:logistic;objectName:"classificationLogistic";text:"LogisticRegression adayı";checked:true;Layout.fillWidth:true;onClicked:validation.invalidate() }
    UiCombo { accessibleLabel: "Düzenlileştirme kuvveti"; id:regularization;objectName:"classificationC";model:["C=0.1","C=1","C=10"];currentIndex:1;Layout.fillWidth:true;onActivated:validation.invalidate() }
    UiCheckBox { id:forest;objectName:"classificationForest";text:"RandomForest adayı";checked:true;Layout.fillWidth:true;onClicked:validation.invalidate() }
    UiCombo { accessibleLabel: "Ağaç sayısı"; id:trees;objectName:"classificationTrees";model:["25 ağaç","50 ağaç","100 ağaç"];currentIndex:1;Layout.fillWidth:true;onActivated:validation.invalidate() }
    UiCombo { accessibleLabel: "Ağaç derinliği"; id:depth;objectName:"classificationDepth";model:["Derinlik 4","Derinlik 8","Derinlik 12"];currentIndex:1;Layout.fillWidth:true;onActivated:validation.invalidate() }
    UiLabel { text:"Eşik yalnız ikili hedef için: adaylar önce varsayılan 0.5 ile CV F1 üzerinden seçilir. Ardından seçilmiş modelin eşiği yalnız ayrı validation bölümünde değerlendirilir; final testte aynı sınıf, model ve eşik dondurulur.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCombo { accessibleLabel: "Karar eşiği yöntemi"; id:thresholdMode;enabled:panel.distribution.length===2;objectName:"classificationThresholdMode";property string helpContext:"classification.threshold";model:["Varsayılan 0.5","Validation üzerinde kendi eşiğim","Validation pozitif F1 ile seç (0.05..0.95)"];Layout.fillWidth:true;onActivated:validation.invalidate() }
    UiTextField { id:threshold;objectName:"classificationThreshold";text:"0.5";visible:thresholdMode.currentIndex===1;Accessible.name:"Validation karar eşiği";Layout.fillWidth:true;onTextEdited:validation.invalidate() }
    UiTextArea { id:cost;objectName:"classificationCost";placeholderText:"Yanlış alarm mı kaçırılan kayıt mı daha maliyetli? Tercihini açıkla (isteğe bağlı).";wrapMode:TextEdit.Wrap;Accessible.name:"Hata maliyeti tercihi";Layout.fillWidth:true;Layout.preferredHeight:90;onTextChanged:if(activeFocus)validation.invalidate() }
    UiLabel { text:"Hata maliyeti açıklaması kaydedilir; F1 seçimi bu maliyeti parasal olarak optimize etmez. Tahmin olasılığı kalibre edilmiş güven veya sahada güvenli otomatik karar garantisi değildir.";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiButton { objectName:"classificationRun";text:"Kategori adaylarını geliştirmede karşılaştır ve kaydet";primary:true;tone:"violet";multiline:true;Layout.fillWidth:true;enabled:validation.canRun&&!panel.protocolBlocked&&(panel.distribution.length!==2||positive.currentIndex>=0);onClicked:validation.createClassification(JSON.stringify(panel.protocol),JSON.stringify(panel.config())) }
    Flow { Layout.fillWidth:true;spacing:Theme.sm
        UiButton { visible: false; text:"Pozitif sınıf ve hata türleri";helpContext:"classification.positive";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { visible: false; text:"Precision / recall";helpContext:"classification.metrics";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { visible: false; text:"Eşik ve olasılık";helpContext:"classification.threshold";onClicked:panel.helpRequested(this,helpContext) }
    }
    UiLabel { text:"Sınıf, eşik ve model ayar geçmişi";font.bold:true;Layout.fillWidth:true }
    Repeater { model:validation.choiceHistory;UiLabel { required property var modelData;objectName:"classificationChoiceHistory";text:modelData.chosen_at+" · "+modelData.status+" · "+modelData.run_id+"\nPozitif: "+(modelData.classification.positive_class||"çok sınıflı")+" · "+modelData.classification.averaging+" · "+modelData.classification.threshold_mode+" · istenen eşik="+modelData.classification.threshold+" · C="+modelData.classification.C+" · ağaç="+modelData.classification.trees+" · derinlik="+modelData.classification.depth+"\nDondurulmuş model/eşik: "+(modelData.decision.model||"henüz yok")+" / "+(typeof modelData.decision.threshold === "number" ? modelData.decision.threshold : "henüz yok")+"\nAdaylar: "+modelData.classification.candidates.join(", ")+" · önceki final test kullanımı="+modelData.prior_test_use_ids.length+"\nMaliyet tercihi: "+(modelData.classification.cost_note||"belirtilmedi");Layout.fillWidth:true;wrapMode:Text.Wrap } }
    ColumnLayout { visible:!!panel.report.classification;Layout.fillWidth:true;spacing:Theme.md
        UiLabel { objectName:"classificationScope";text:panel.report.mode==="final"?"FINAL TEST — dondurulmuş model, sınıf ve eşik":"GELİŞTİRME — CV model seçimi; ayrı validation eşik kararı";font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { text:"Seçilen: "+(panel.report.selected_model||"")+" · averaging: "+((panel.report.classification||{}).averaging||"")+" · pozitif: "+((panel.report.decision||{}).positive_class||"çok sınıflı OvR")+((panel.report.classes||[]).length===2?" · eşik: "+((panel.report.decision||{}).threshold||0.5):" · çok sınıfta argmax; ikili eşik uygulanmaz")+"\nMaliyet tercihi: "+((panel.report.classification||{}).cost_note||"belirtilmedi");Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { text:panel.report.interpretation==="exploratory"?"KEŞİFSEL: önceki final test kullanımı var. Sonraki model/sınıf/eşik seçimleri bağımsız test gerektirir.":"Yalnız bu projedeki test kullanımı bilinir. Testin proje dışında daha önce görülmediği garanti edilemez.";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:panel.report.classification?panel.report.comparison||[]:[];UiLabel { required property var modelData;text:modelData.model+" · CV F1="+modelData.cv_f1.toFixed(6);Layout.fillWidth:true;wrapMode:Text.Wrap } }
        Repeater { model:panel.report.classification?(panel.report.mode==="final"?panel.report.evaluations||[]:(panel.report.decision_validation&&panel.report.decision_validation.metrics?[panel.report.decision_validation]:[])):[]
            ColumnLayout { required property var modelData;Layout.fillWidth:true;spacing:Theme.sm
                UiLabel { text:modelData.scope+" · "+modelData.evaluation_n+" kayıt · metrikler bu bölümün tamamında";Layout.fillWidth:true;wrapMode:Text.Wrap }
                Repeater { model:modelData.metrics;UiLabel { required property var modelData;objectName:"classificationMetric_"+modelData.metric;text:modelData.metric+" = "+((typeof modelData.value!=="number"||!isFinite(modelData.value))?"tanımsız":modelData.value.toFixed(6))+" · "+modelData.averaging+(modelData.reason?" · "+modelData.reason:"");Layout.fillWidth:true;wrapMode:Text.Wrap } }
                ConfusionMatrix { labels:modelData.classes;matrix:modelData.confusion_matrix;Layout.fillWidth:true }
                Repeater { model:modelData.per_class;UiLabel { required property var modelData;text:modelData.label+" · gerçek="+modelData.support+" · tahmin="+modelData.predicted_n+" · precision="+modelData.precision.toFixed(4)+" · recall="+modelData.recall.toFixed(4)+" · F1="+modelData.f1.toFixed(4)+"\n"+panel.status(modelData.precision_status)+" / "+panel.status(modelData.recall_status);Layout.fillWidth:true;wrapMode:Text.Wrap } }
                UiLabel { text:"Sıfır bölmede 0 raporlanır; tanımsız sınıf durumları ayrıca gösterilir. Macro tüm tanımlı sınıfları içerir. Testte bulunmayan sınıf için ROC/PR eğrisi üretilmez.";Layout.fillWidth:true;wrapMode:Text.Wrap }
                Repeater { model:modelData.curves||[];ColumnLayout { required property var modelData;Layout.fillWidth:true
                    UiLabel { text:modelData.label+" · "+(modelData.status==="valid"?"ROC-AUC="+modelData.roc_auc.toFixed(6)+" · PR-AUC (trapez)="+modelData.pr_auc.toFixed(6)+" · AP="+modelData.average_precision.toFixed(6):modelData.reason);Layout.fillWidth:true;wrapMode:Text.Wrap }
                    ClassificationCurve { visible:modelData.status==="valid";points:modelData.roc;title:"ROC · "+modelData.label;Layout.fillWidth:true;Layout.preferredHeight:200 }
                    ClassificationCurve { visible:modelData.status==="valid";points:modelData.pr;title:"Precision / Recall · "+modelData.label;precisionRecall:true;Layout.fillWidth:true;Layout.preferredHeight:200 }
                } }
                UiLabel { text:"ROC/PR çizimi en fazla 1000 eşik noktası; AUC tüm gerçek noktalarla hesaplanır. Çok sınıfta eğriler one-vs-rest. PR-AUC trapez alanıdır; AP basamak ağırlıklıdır. Olasılık kalibrasyonu bu fazda yapılmaz.";Layout.fillWidth:true;wrapMode:Text.Wrap }
            }
        }
    }
}
