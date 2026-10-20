import QtQuick
import QtQuick.Layouts
ColumnLayout {
 id:panel
 objectName:"streamPanel"
 property string helpContext:"model.stream"
 signal helpRequested(var origin,string context)
 readonly property var result:streams.historyReport
 function config(){return {event_id:event_id.currentValue,event_time:event_time.currentValue,processing_time:processing_time.currentValue,feedback_time:feedback_time.currentValue,target:target.currentValue,features:[feature.currentValue],buffer:Number(buffer.text),window:Number(windowSize.text),lateness:Number(lateness.text),late_policy:late.currentIndex===0?"quarantine":"reject",clock:clock.currentIndex===0?"event":"processing",retrain:retrain.currentIndex===0?"alarm_only":"reset",checkpoint_every:16,seed:62}}
 Connections {target:streams;function onSelectStream(value){expanded.checked=true}}
 UiCheckBox {id:expanded;objectName:"streamExpanded";text:"Faz62 yerel stream ve özel hedefler";Layout.fillWidth:true}
 ColumnLayout {visible:expanded.checked;Layout.fillWidth:true
 UiLabel {text:"Append simülatörü — mevcut değişmez CSV/Parquet snapshot'ını16kayıtlık bloklarla oynatır. Canlı dosya izleme/ağ broker'ı mevcut değil; ağ isteği yapılmaz. Zamanlar aynı epoch/unit içinde saniye olmalı; wall clock değil kaynak processing time kullanılır.";Layout.fillWidth:true;wrapMode:Text.Wrap}
 UiLabel {text:"Binary SGD log-loss + incremental StandardScaler partial_fit. Önce predict, sonra zamanı gelen label ile score/train. Scaler yalnız label gelen eğitimde güncellenir; katsayılar yeni ölçeğe taşınır. İlk eğitimsiz tahmin NA, skor dışı. Offline modeller otomatik online sayılmaz.";Layout.fillWidth:true;wrapMode:Text.Wrap}
 UiCombo {id:event_id;objectName:"streamEventID";accessibleLabel:"Artan integer event kimliği";model:streams.columns;textRole:"name";valueRole:"id";enabled:!streams.busy;Layout.fillWidth:true}
 UiCombo {id:event_time;objectName:"streamEventTime";accessibleLabel:"Event time saniye";model:streams.columns;textRole:"name";valueRole:"id";enabled:!streams.busy;Layout.fillWidth:true}
 UiCombo {id:processing_time;objectName:"streamProcessingTime";accessibleLabel:"Processing time saniye";model:streams.columns;textRole:"name";valueRole:"id";enabled:!streams.busy;Layout.fillWidth:true}
 UiCombo {id:feedback_time;objectName:"streamFeedbackTime";accessibleLabel:"Feedback available time saniye veya null";model:streams.columns;textRole:"name";valueRole:"id";enabled:!streams.busy;Layout.fillWidth:true}
 UiCombo {id:target;objectName:"streamTarget";accessibleLabel:"Binary target0/1 veya null";model:streams.columns;textRole:"name";valueRole:"id";enabled:!streams.busy;Layout.fillWidth:true}
 UiCombo {id:feature;objectName:"streamFeature";accessibleLabel:"Numeric feature";model:streams.columns;textRole:"name";valueRole:"id";enabled:!streams.busy;Layout.fillWidth:true}
 UiTextField {id:buffer;objectName:"streamBuffer";Accessible.name:"Pending ve active window kayıt sınırı2–256";text:"64";Layout.fillWidth:true}
 UiTextField {id:windowSize;objectName:"streamWindow";Accessible.name:"Tumbling window saniye";text:"60";Layout.fillWidth:true}
 UiTextField {id:lateness;objectName:"streamLateness";Accessible.name:"Watermark gecikmesi saniye";text:"0";Layout.fillWidth:true}
 UiCombo {id:clock;objectName:"streamClock";accessibleLabel:"Window clock";model:["Event time / watermark","Processing time"];Layout.fillWidth:true}
 UiCombo {id:late;objectName:"streamLatePolicy";accessibleLabel:"Geç olay politikası";model:["Quarantine: late say, eğitim/pencere dışı; kaynak korunur","Reject: işi durdur"];Layout.fillWidth:true}
 UiCombo {id:retrain;objectName:"streamRetrain";accessibleLabel:"Drift retrain politikası";model:["Alarm only; otomatik yeniden eğitim yok","Açık reset: alarmda scaler/model sıfırla, generation kaydet"];Layout.fillWidth:true}
 UiLabel {text:"Drift: son32 scored0/1 loss'un iki16'lık yarısı; artış>.25 alarmı. İstatistiksel kanıt değildir. Missing label negatif sayılmaz; son processing time'dan sonraki feedback pending kalır. Buffer dolarsa durur, kayıt sessiz düşmez. Checkpoint sonrası next cursor; duplicate/reorder ID reject. Aynı kaynak/spec/sklearn sürümü gerekir; cihazlar arası bit eşitliği garantisi yok.";Layout.fillWidth:true;wrapMode:Text.Wrap}
 UiButton {objectName:"streamRun";text:"Yeni yerel replay başlat";enabled:streams.canStreamRun;onClicked:streams.startStream(JSON.stringify(panel.config()));Layout.fillWidth:true}
 UiButton {objectName:"streamResume";text:"Açık kalıcı checkpoint'inden devam et";enabled:streams.canStreamRun&&(panel.result.status==="running"||panel.result.status==="canceled"||panel.result.status==="budget_exhausted");onClicked:streams.resumeStream(JSON.stringify(panel.config()));Layout.fillWidth:true}
 UiButton {objectName:"streamCancel";text:"Replay iptal";visible:streams.busy;onClicked:streams.cancel();Layout.fillWidth:true}
 StateNotice {heading:"Stream durumu";detail:streams.errorText||streams.message;kind:streams.errorText?"error":streams.busy?"loading":"info";Layout.fillWidth:true}
 UiLabel {objectName:"streamSummary";text:panel.result.status?panel.result.status+" · cursor="+(panel.result.state||{}).cursor+" · trained="+(panel.result.state||{}).trained+" · scored="+(panel.result.state||{}).scored+" · accuracy="+((panel.result.metrics||{}).accuracy===null?"NA":(panel.result.metrics||{}).accuracy)+"\nPending="+((panel.result.state||{}).pending||[]).length+" · missing="+(panel.result.state||{}).missing+" · late="+(panel.result.state||{}).late+" · drift alarms="+(panel.result.state||{}).alarms+" · generation="+(panel.result.state||{}).generation:"Henüz replay yok";Layout.fillWidth:true;wrapMode:Text.Wrap}
 UiCombo {id:saved;objectName:"streamSaved";accessibleLabel:"Kalıcı stream checkpoint";model:streams.savedRuns;textRole:"label";valueRole:"id";Layout.fillWidth:true}
 UiButton {objectName:"streamOpen";text:"Seçili checkpoint'i aç";enabled:!streams.busy&&saved.currentIndex>=0;onClicked:streams.openRun(saved.currentValue);Layout.fillWidth:true}
 UiLabel {text:"Özel hedefler — development train/pool/eval role kolonu açık olmalı. Final test burada kullanılamaz. Multi-label binary0/1 iki hedef; multi-output iki numeric hedef; ordinal explicit string order ve median karar (proportional-odds model değil); semi-supervised0/1/−1(unlabeled). Group/time üyeliğini önce veri planında hazırlayın. Yeni-data model prediction/save yok; güvenli sonuç kaydı var. PU unavailable: unlabeled negatif değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap}
 UiCombo {id:specialTask;objectName:"specialTask";accessibleLabel:"Özel hedef yöntemi";model:["multilabel","multioutput","ordinal","semisupervised"];Layout.fillWidth:true}
 UiCombo {id:specialRole;objectName:"specialRole";accessibleLabel:"Development role train pool eval ColumnId";model:streams.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
 UiCombo {id:specialTarget2;objectName:"specialTarget2";accessibleLabel:"İkinci multi-label/output hedef ColumnId";model:streams.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
 UiTextField {id:ordinalOrder;objectName:"specialOrder";Accessible.name:"Ordinal sıra string JSON listesi";text:'["low","high"]';Layout.fillWidth:true}
 UiCheckBox {id:transductive;objectName:"specialTransductive";text:"LabelPropagation eval FEATURES graph'a açıkça katılsın: TRANSDUCTIVE; bağımsız test değildir";Layout.fillWidth:true}
 UiButton {objectName:"specialRun";text:"Özel hedef development hesabını başlat";enabled:streams.canStreamRun;onClicked:{try{var t=specialTask.currentText;streams.startSpecial(JSON.stringify({task:t,features:[feature.currentValue],targets:t==="multilabel"||t==="multioutput"?[target.currentValue,specialTarget2.currentValue]:[target.currentValue],role:specialRole.currentValue,order:t==="ordinal"?JSON.parse(ordinalOrder.text):[],transductive:transductive.checked,seed:62}))}catch(e){specialError.text="Ordinal sıra JSON listesini kontrol edin"}}Layout.fillWidth:true}
 UiLabel {id:specialError;text:"";Layout.fillWidth:true;wrapMode:Text.Wrap}
 UiLabel {objectName:"specialSummary";text:panel.result.schema==="SpecialTargetRun/v1"?"DEVELOPMENT · "+JSON.stringify(panel.result.metrics||{})+"\n"+((panel.result.analysis||{}).fit_scope||"")+"\n"+(panel.result.warnings||[]).join("\n"):"";Layout.fillWidth:true;wrapMode:Text.Wrap}
 UiButton {objectName:"streamHelp";text:"Bu ne işe yarar?";helpContext:"model.stream";onClicked:panel.helpRequested(this,helpContext);Layout.fillWidth:true}
 }
}
