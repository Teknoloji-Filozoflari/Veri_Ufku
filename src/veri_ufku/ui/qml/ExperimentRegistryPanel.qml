import QtQuick
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id: panel
    objectName: "experimentRegistryPanel"
    signal helpRequested(var origin, string context)
    property var selected: []
    property var filtered: lifecycle.experimentRuns
    property var report: lifecycle.experimentReport
    function refresh() { filtered=lifecycle.findExperiments(query.text,status.currentText==="all"?"":status.currentText,tag.text) }
    Connections { target:lifecycle;function onLifecycleChanged(){panel.refresh()} }
    UiLabel { text:"Yerel experiment / model registry";font.bold:true;Layout.fillWidth:true }
    UiLabel { text:"Run eğitim/değerlendirme kaydıdır; model version güvenli artifact üreten run kimliğidir. Aynı dataset farklı split aynı protokol değildir. Eski kayıtların bilinmeyen hash ve erişim zamanları türetilmez. Test defteri proje geneli; dış kullanım bilinmez.";wrapMode:Text.Wrap;Layout.fillWidth:true }
    UiButton { visible: false; text:"Run, sürüm ve reproducibility yardımı";helpContext:"experiment.registry";onClicked:panel.helpRequested(this,helpContext) }
    UiTextField { id:query;objectName:"experimentQuery";Accessible.name:"Run kimliği veya yöntem ara";placeholderText:"Run ara";Layout.fillWidth:true;onTextEdited:panel.refresh() }
    UiCombo { id:status;objectName:"experimentStatusFilter";accessibleLabel:"Run durum filtresi";model:["all","completed","canceled","failed","pending","running","budget_exhausted"];Layout.fillWidth:true;onActivated:panel.refresh() }
    UiTextField { id:tag;Accessible.name:"Tam tag filtresi";placeholderText:"Tam tag";Layout.fillWidth:true;onTextEdited:panel.refresh() }
    UiLabel { text:"En fazla32 koşu karşılaştırılır. Seçili run kutuları yalnız bu görünümü etkiler.";wrapMode:Text.Wrap;Layout.fillWidth:true }
    Repeater { model:panel.filtered
        ColumnLayout { id:runRow; required property var modelData;Layout.fillWidth:true
            UiCheckBox { objectName:"experimentRun_"+modelData.run_id;text:modelData.run_id+" · "+modelData.kind+" · "+modelData.status;checked:panel.selected.indexOf(modelData.run_id)>=0;onToggled:{let ids=panel.selected.slice();if(checked&&ids.indexOf(modelData.run_id)<0)ids.push(modelData.run_id);if(!checked)ids=ids.filter(id=>id!==modelData.run_id);panel.selected=ids} }
            UiLabel { text:"Model: "+(modelData.model_version||"artifact yok")+" · "+(modelData.model_status||"")+" · önce test görülmüş: "+(modelData.test_seen_before?"evet":"proje defterinde yok")+"\nErişim: "+(modelData.data_access_at||"bilinmiyor")+" · protokol: "+(modelData.protocol_id||"bilinmiyor")+"\nSplit: "+(modelData.split_id||"bilinmiyor");wrapMode:Text.Wrap;Layout.fillWidth:true }
            Flow { Layout.fillWidth:true;spacing:Theme.sm
                Repeater { model:["candidate","selected","archived"];UiButton { required property string modelData;text:modelData;enabled:!!runRow.modelData.model_version&&!projects.readOnly&&!projects.busy&&!lifecycle.busy;onClicked:lifecycle.reviseExperiment(runRow.modelData.run_id,"model_status",JSON.stringify(modelData)) } }
            }
        }
    }
    UiCombo { id:metric;objectName:"experimentMetric";accessibleLabel:"Karşılaştırma metriği";model:["mae","rmse","mase","r2","accuracy","f1","log_loss","brier","precision","recall","ndcg","ap"];Layout.fillWidth:true }
    UiButton { objectName:"experimentCompare";text:"Seçili runları doğrula ve karşılaştır";Layout.fillWidth:true;enabled:panel.selected.length>0&&panel.selected.length<=32&&!projects.busy&&!lifecycle.busy;onClicked:lifecycle.compareExperiments(JSON.stringify(panel.selected),metric.currentText) }
    UiButton { objectName:"experimentMetricRevision";text:"Seçili koşuda rapor metriğini yeni revision olarak kaydet";Layout.fillWidth:true;enabled:panel.selected.length===1&&!projects.readOnly;onClicked:lifecycle.reviseExperiment(panel.selected[0],"metric_revision",JSON.stringify(metric.currentText)) }
    UiTextField { id:tags;Accessible.name:"Tag listesi JSON";text:"[]";Layout.fillWidth:true }
    UiButton { text:"Seçili koşuya tag revision ekle";Layout.fillWidth:true;enabled:panel.selected.length===1&&!projects.readOnly;onClicked:lifecycle.reviseExperiment(panel.selected[0],"tags",tags.text) }
    UiLabel { text:"Tags: en fazla16, ASCII harf/rakam/_/-,32 karakter; secret/credential alanları yok. Export tags, raw params, model kartı ve kaynak değerleri içermez.";wrapMode:Text.Wrap;Layout.fillWidth:true }
    UiLabel { objectName:"experimentComparisonWarning";text:(panel.report.warnings||[]).join("\n");wrapMode:Text.Wrap;color:Theme.warning;Layout.fillWidth:true }
    Repeater { model:panel.report.rows||[];UiLabel { required property var modelData;text:modelData.run_id+" · "+modelData.status+" · metric mean: "+modelData.score+" · süre: "+(modelData.duration_seconds||0)+"s · "+(modelData.duration_scope||"bilinmiyor")+"\n"+"scope: "+(modelData.score_scope||"unavailable")+" · "+JSON.stringify(modelData.folds||[])+"\nÖnceki test kullanımları: "+JSON.stringify(modelData.prior_test_use_ids||[]);wrapMode:Text.Wrap;Layout.fillWidth:true } }
    RegistryFolds { runs:panel.report.rows||[];metric:panel.report.metric||"";Layout.fillWidth:true;Layout.preferredHeight:220 }
    RegistryPareto { objectName:"experimentPareto";points:panel.report.points||[];metric:panel.report.metric||"";comparable:!!panel.report.comparable&&!!panel.report.cost_comparable;Layout.fillWidth:true;Layout.preferredHeight:220 }
    UiLabel { text:panel.report.note||"";wrapMode:Text.Wrap;Layout.fillWidth:true }
    UiCheckBox { id:technical;text:"Model kartı, lineage ve hash metadata ayrıntısını göster" }
    UiLabel { visible:technical.checked;text:technical.checked?JSON.stringify(panel.report.rows||[],null,2):"";wrapMode:Text.Wrap;Layout.fillWidth:true }
    UiTextField { id:quota;Accessible.name:"Artifact disk kotası MiB";text:"4096";Layout.fillWidth:true;validator:IntValidator {bottom:16;top:1048576} }
    UiButton { text:"Artifact disk kotasını revision olarak kaydet";Layout.fillWidth:true;enabled:!projects.readOnly&&!projects.busy;onClicked:lifecycle.reviseExperiment("","quota",JSON.stringify(Number(quota.text)*1048576)) }
    UiLabel { text:"Quota tüm eski sources/snapshots artifact baytlarını sayar; metadata/geçici disk için ayrıca boş alan kontrolü vardır. Aşımda kayıt durur, otomatik silme yok. Arşivleme disk boşaltmaz. Fiziksel silme bu panelde kapalı: dataset/model/yeniden üretilebilirlik ve tarihçe kaybına yol açabilir. Ayrı proje export veya yedek kullanın. Tracking backend bağlı değil; entegrasyon bu ortamda doğrulanmadı. Bu panel ağ isteği yapmaz.";wrapMode:Text.Wrap;color:Theme.warning;Layout.fillWidth:true }
    FileDialog { id:exportDialog;title:"Yeni maskeli registry JSON";fileMode:FileDialog.SaveFile;nameFilters:["JSON (*.json)"];onAccepted:lifecycle.exportExperiments(JSON.stringify(panel.selected),metric.currentText,selectedFile.toString()) }
    UiButton { objectName:"experimentExport";text:"Seçili runları maskeli JSON olarak dışa aktar";Layout.fillWidth:true;enabled:panel.selected.length>0&&!projects.busy;onClicked:exportDialog.open() }
}
