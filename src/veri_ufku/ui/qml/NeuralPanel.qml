import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "neuralPanel"
    property var protocol
    property bool protocolBlocked: false
    property string helpContext: "model.neural"
    signal helpRequested(var origin, string context)
    readonly property var report: neuralTraining.historyReport
    function config() {return {template: template.currentIndex===0?"mlp":"cnn", epochs:Number(epochs.text), batch:Number(batch.text), hidden:16, lr:Number(lr.text), optimizer:optimizer.currentIndex===0?"adam":"sgd", scheduler:scheduler.checked?"step":"none", patience:Number(patience.text), gradient_clip:5, seed:Number(seed.text), deterministic:deterministic.checked, class_weights:weights.checked?"balanced":"none", image_shape:template.currentIndex===1?JSON.parse(shape.text):[], image_ack:template.currentIndex===1?pixels.text:"", augmentation:flip.checked&&template.currentIndex===1?"horizontal_flip":"none", device:"cpu", mixed_precision:false, wall_seconds:Number(wall.text)}}
    function run(resume) {try {neuralTraining.start(JSON.stringify(protocol),JSON.stringify(config()),resume)} catch(error) {localError.text="Tensor ayarlarını kontrol edin: "+error}}
    Connections {target:neuralTraining;function onSelectNeural(value){expanded.checked=true;template.currentIndex=value==="cnn"?1:0}}
    UiCheckBox {id:expanded;objectName:"neuralExpanded";text:"Faz56 CPU tensor eğitimini göster";Layout.fillWidth:true}
    ColumnLayout {visible:expanded.checked;Layout.fillWidth:true;spacing:Theme.sm
        UiLabel {text:"Küçük MLP / açık görüntü CNN · CPU float32";font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiLabel {text:"En fazla 2000 satır / 1024 sayısal özellik / 100 epoch. Preprocessing yalnız train'de öğrenilir; validation loss early stopping seçer. Aynı sklearn Dummy baseline aynı ayrımla ölçülür. Final test bu panelde değerlendirilmez; sonuç bağımsız test veya CV başarısı değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiLabel {text:neuralTraining.available?"Optional PyTorch 2.13.0+cpu hazır; CPU dışında GPU/VRAM/mixed precision henüz doğrulanmadı ve kapalı.":"Optional CPU backend yok: neural extra yerel olarak kurulmalı. Uygulama ağdan otomatik model/paket indirmez.";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap}
        ColumnLayout {enabled:!neuralTraining.busy;Layout.fillWidth:true
            UiCombo {id:template;objectName:"neuralTemplate";accessibleLabel:"Tensor model şablonu";model:["MLP sayısal tablo","CNN açık piksel görüntüsü"];Layout.fillWidth:true}
            UiLabel {text:"Epoch / batch / learning rate / early stopping patience / seed / süre bütçesi (saniye)";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiTextField {id:epochs;objectName:"neuralEpochs";Accessible.name:"Tensor epoch sayısı";text:"12";Layout.fillWidth:true}
            UiTextField {id:batch;objectName:"neuralBatch";Accessible.name:"Tensor batch boyutu";text:"16";Layout.fillWidth:true}
            UiTextField {id:lr;objectName:"neuralLR";Accessible.name:"Tensor learning rate";text:"0.01";Layout.fillWidth:true}
            UiTextField {id:patience;objectName:"neuralPatience";Accessible.name:"Tensor early stopping patience";text:"5";Layout.fillWidth:true}
            UiTextField {id:seed;objectName:"neuralSeed";Accessible.name:"Tensor seed";text:"56";Layout.fillWidth:true}
            UiTextField {id:wall;objectName:"neuralWall";Accessible.name:"Tensor süre bütçesi saniye";text:"120";Layout.fillWidth:true}
            UiCombo {id:optimizer;objectName:"neuralOptimizer";accessibleLabel:"Tensor optimizer";model:["Adam","SGD momentum 0.9"];Layout.fillWidth:true}
            UiCheckBox {id:scheduler;objectName:"neuralScheduler";text:"StepLR: her 3 epoch LR × 0.8";checked:true;Layout.fillWidth:true}
            UiCheckBox {id:deterministic;objectName:"neuralDeterministic";text:"Deterministic CPU işlemleri; cihazlar arasında aynı seed birebir sonuç garantisi değildir";checked:true;Layout.fillWidth:true}
            UiCheckBox {id:weights;objectName:"neuralWeights";text:"Sınıflandırma: yalnız train sınıf sayısından balanced loss weights";Layout.fillWidth:true}
            UiLabel {visible:template.currentIndex===1;text:"CNN: hazırlıkta seçtiğiniz özelliklerin sırası NCHW row-major piksel sırası olmalı. Tablo kolonları kendiliğinden görüntü değildir. Kanal/yükseklik/genişlik [1,4,4] ve bilimsel gerekçe belirtin.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiTextField {id:shape;objectName:"neuralShape";Accessible.name:"CNN kanal yükseklik genişlik JSON";text:"[1,4,4]";visible:template.currentIndex===1;Layout.fillWidth:true}
            UiTextField {id:pixels;objectName:"neuralPixels";Accessible.name:"CNN piksel sırası gerekçesi";placeholderText:"Piksel kaynağı ve row-major sıra gerekçesi";visible:template.currentIndex===1;Layout.fillWidth:true}
            UiCheckBox {id:flip;objectName:"neuralFlip";text:"Görüntüde horizontal flip anlamlı: yalnız train augmentation";visible:template.currentIndex===1;Layout.fillWidth:true}
            UiLabel {text:"Gradient clip sınırı 5; raporda clip öncesi norm gösterilir; hidden 16. CPU/RAM/disk/süre birleşik ComputeBudget ile sınırlı; RAM bütçesi "+neuralTraining.ramMiB+" MiB. Batch gradient'leri train'den; validation eval/no_grad'dır.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiButton {objectName:"neuralRun";text:"CPU eğitimini başlat";primary:true;enabled:neuralTraining.canRun&&!panel.protocolBlocked;onClicked:panel.run(false);Layout.fillWidth:true}
            UiButton {objectName:"neuralResume";text:"Aynı ayarlarla tam checkpoint'ten devam et";multiline:true;enabled:neuralTraining.canRun&&(panel.report.status==="paused"||panel.report.status==="canceled"||panel.report.status==="running");onClicked:panel.run(true);Layout.fillWidth:true}
        }
        UiButton {objectName:"neuralPause";text:"Epoch sınırında duraklat";visible:neuralTraining.busy;onClicked:neuralTraining.pause();Layout.fillWidth:true}
        UiButton {objectName:"neuralCancel";text:"İptal — son kalıcı epoch korunur";visible:neuralTraining.busy;onClicked:neuralTraining.cancel();Layout.fillWidth:true}
        StateNotice {Layout.fillWidth:true;kind:neuralTraining.errorText?"error":neuralTraining.busy?"loading":"info";heading:"Tensor eğitim durumu";detail:neuralTraining.errorText||neuralTraining.message}
        UiLabel {id:localError;text:"";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiLabel {objectName:"neuralSummary";text:panel.report.status?(panel.report.status+" · epoch="+panel.report.epoch+" · validation "+(panel.report.comparison||{}).metric+"="+((panel.report.comparison||{}).neural===undefined?"henüz yok":(panel.report.comparison||{}).neural.toFixed(4))+" · sklearn baseline="+((panel.report.comparison||{}).sklearn_baseline||0).toFixed(4)+"\nFramework: "+(panel.report.environment||{}).torch+" · CPU float32 · CUDA: "+((panel.report.environment||{}).cuda||"yok")+" · seed="+panel.report.seed):"Henüz tensor koşusu yok";Layout.fillWidth:true;wrapMode:Text.Wrap}
        Canvas {objectName:"neuralCurves";Layout.fillWidth:true;Layout.preferredHeight:180;property var points:panel.report.curves||[];onPointsChanged:requestPaint();onWidthChanged:requestPaint();onPaint:{var c=getContext("2d");c.clearRect(0,0,width,height);if(points.length===0)return;var maxLoss=Math.max.apply(null,points.map(p=>Math.max(p.training_loss,p.validation_loss)))||1;c.strokeStyle="#999999";c.strokeRect(22,10,width-35,height-30);["training_loss","validation_loss"].forEach(function(key,index){c.strokeStyle=index===0?"#ef9b55":"#80c5ed";c.beginPath();points.forEach(function(p,i){var x=22+(width-35)*i/Math.max(1,points.length-1),y=height-20-(height-30)*p[key]/maxLoss;if(i===0)c.moveTo(x,y);else c.lineTo(x,y)});c.stroke()})}}
        UiLabel {text:"Eğriler: turuncu training loss, mavi validation loss; yatay epoch, dikey loss. Loss hedef ölçeğine bağlı; validation artarken train düşmesi overfitting işaretidir.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        Repeater {model:panel.report.curves||[];UiLabel {required property var modelData;text:"Epoch "+modelData.epoch+" · train="+modelData.training_loss.toFixed(5)+" · validation="+modelData.validation_loss.toFixed(5)+" · lr="+modelData.lr+" · gradient (clip öncesi)="+modelData.gradient_norm_max.toFixed(4);Layout.fillWidth:true;wrapMode:Text.Wrap}}
        UiLabel {text:"Safe kayıt: yalnız kapalı JSON tensor/optimizer/scheduler/RNG. Arbitrary .pt/.pkl ve pretrained Python object import kapalı. Weight reload tam resume değildir; resume kaynak/split/ayar/framework/thread ve test geçmişini doğrular. İptalde kısmi epoch atılır; önceki atomik checkpoint korunur.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiCombo {id:saved;objectName:"neuralSaved";accessibleLabel:"Kalıcı tensor kayıtları";model:neuralTraining.savedRuns;textRole:"label";valueRole:"id";Layout.fillWidth:true}
        UiButton {objectName:"neuralOpen";text:"Safe model / checkpoint aç";enabled:!neuralTraining.busy&&!projects.busy&&saved.currentIndex>=0;onClicked:neuralTraining.openRun(saved.currentValue);Layout.fillWidth:true}
        UiButton {objectName:"neuralPredict";text:"İçe aktarılmış aktif yeni veride prediction";multiline:true;enabled:neuralTraining.available&&!neuralTraining.busy&&!projects.busy&&panel.report.status==="completed";onClicked:neuralTraining.predictData();Layout.fillWidth:true}
        UiLabel {objectName:"neuralPredictions";text:neuralTraining.predictionReport.values?"Yeni veri: "+neuralTraining.predictionReport.values.length+" tahmin · fit yapılmadı · ilk 5 sonuç aşağıda":"Yeni veride henüz tahmin yok";Layout.fillWidth:true;wrapMode:Text.Wrap}
        Repeater {model:(neuralTraining.predictionReport.values||[]).slice(0,5);UiLabel {required property var modelData;required property int index;text:"Tahmin "+(index+1)+": "+(typeof modelData==="number"?modelData.toFixed(5):modelData);Layout.fillWidth:true;wrapMode:Text.Wrap}}
        UiLabel {visible:(neuralTraining.predictionReport.class_labels||[]).length>0;text:"Softmax çıktısı kalibre olasılık garantisi değildir. Sınıf sırası: "+(neuralTraining.predictionReport.class_labels||[]).join(", ");Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiCheckBox {id:technical;objectName:"neuralTechnical";text:"Tensor şeması, kaynak kimlikleri ve teknik tahmin kaydını göster";Layout.fillWidth:true}
        UiLabel {visible:technical.checked;text:JSON.stringify(panel.report.tensor_schema||{})+"\n"+JSON.stringify(neuralTraining.predictionReport);Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiButton { visible: false;objectName:"neuralHelp";text:"Tensor, epoch ve güvenli resume öğren";helpContext:"model.neural";onClicked:panel.helpRequested(this,helpContext);Layout.fillWidth:true}
    }
}
