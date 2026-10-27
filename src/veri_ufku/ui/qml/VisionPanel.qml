import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"visionPanel"
    property string helpContext:"model.vision"
    signal helpRequested(var origin,string context)
    readonly property var result:visionAnalysis.historyReport
    readonly property var tasks:["scan","classification","transfer","detection","segmentation"]
    function config(){return {task:tasks[task.currentIndex],size:Number(size.text),crop:JSON.parse(crop.text),flip:flip.checked,epochs:Number(epochs.text),seed:Number(seed.text),learning_rate:0.01,model_folder:folder.text,score_threshold:Number(score.text),iou_thresholds:JSON.parse(iou.text)}}
    function metricText(){var m=panel.result.metrics||{};if(m.accuracy!==undefined)return "Validation n="+m.n+" · accuracy="+m.accuracy.toFixed(3)+" · aynı split baseline="+m.baseline_accuracy.toFixed(3)+"\nEtiket sırası: "+m.labels.join(", ")+"\nConfusion (gerçek → tahmin):\n"+m.confusion.map(function(r){return r.join("  ")}).join("\n");if(m.map!==undefined)return "Validation AP ortalaması="+m.map+" · IoU eşikleri="+((panel.result.vision_spec||{}).iou_thresholds||[]).join(", ");if(m.pixels!==undefined)return "Validation görüntü="+m.images+" · pixel="+m.pixels+" · foreground macro IoU="+m.macro_foreground_iou+" · Dice="+m.macro_foreground_dice;return "Model/metric hesabı yok"}
    Connections {target:visionAnalysis;function onSelectVision(value){expanded.checked=true;task.currentIndex=panel.tasks.indexOf(value)}}
    UiCheckBox {id:expanded;objectName:"visionExpanded";text:"Faz57 yerel görüntü çalışma alanını göster";Layout.fillWidth:true}
    ColumnLayout {visible:expanded.checked;Layout.fillWidth:true;spacing:Theme.sm
        UiLabel {text:"Yerel görüntü · insan etiketi · subject/video split";font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiLabel {text:"Veri ekranından görüntü klasörü veya images.json import edin. VisionManifest/v1: classes/mask_labels/images. Sınıf klasöründen gelen etiket proposed kalır; model ön etiketi ground truth değildir. Görüntüler immutable source kopyasına alınır; kaynak değişmez.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiTextField {id:source;objectName:"visionSource";Accessible.name:"Yerel görüntü klasörü veya images.json yolu";placeholderText:"Mutlak yerel görüntü klasörü / images.json";Layout.fillWidth:true}
        UiButton {objectName:"visionChoose";text:"Görüntü kaynağını import önizlemesine gönder";multiline:true;Layout.fillWidth:true;enabled:!visionAnalysis.busy&&!imports.busy&&!projects.busy;onClicked:imports.choose(source.text)}
        UiButton {objectName:"visionImport";text:"Önizlenen görüntü snapshot'ını import et";Layout.fillWidth:true;enabled:imports.ready;onClicked:imports.importData(true)}
        StateNotice {heading:"Görüntü import durumu";detail:imports.errorText||imports.message;kind:imports.errorText?"error":"info";Layout.fillWidth:true}
        UiLabel {text:"4M pixel /16MiB dosya /256 görüntü; RGB/L tek frame PNG/JPEG/WebP. EXIF orientation kopyada uygulanır; bbox/mask oriented olmalı. Bozuk/alpha/CMYK/animated/aşırı büyük resimde durur. Exact hash+dHash/RGB heuristic tüm semantik kopyaları bulma garantisi değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        ColumnLayout {enabled:!visionAnalysis.busy;Layout.fillWidth:true
            UiCombo {id:task;objectName:"visionTask";accessibleLabel:"Görüntü alt aşaması";model:["1 — manifest/duplicate/transform preview","2 — küçük RGB CNN classification","3 — safe yerel CNN frozen transfer","4 — bounded RGB pixel detection","5 — bounded RGB pixel segmentation"];Layout.fillWidth:true}
            UiLabel {text:"Detection/segmentation genel YOLO/U-Net değildir: renk-piksel logistic template, detection bbox supervision weak ve 4-neighbor components. CPU zorunlu; GPU kapalı. Final test değerlendirilmez; validation holdout kapsamı.";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiLabel {text:"Resize4..16 / normalized crop XYXY / epoch1..50 / seed";Layout.fillWidth:true}
            UiTextField {id:size;objectName:"visionSize";Accessible.name:"Görüntü resize kenarı";text:"8";Layout.fillWidth:true}
            UiTextField {id:crop;objectName:"visionCrop";Accessible.name:"Görüntü crop XYXY JSON";text:"[0,0,1,1]";Layout.fillWidth:true}
            UiTextField {id:epochs;objectName:"visionEpochs";Accessible.name:"Görüntü training epoch";text:"6";Layout.fillWidth:true}
            UiTextField {id:seed;objectName:"visionSeed";Accessible.name:"Görüntü split seed";text:"57";Layout.fillWidth:true}
            UiCheckBox {id:flip;objectName:"visionFlip";text:"Horizontal flip anlamlı: yalnız CNN train augmentation";Layout.fillWidth:true}
            UiTextField {id:folder;objectName:"visionModelFolder";Accessible.name:"Safe pretrained VisionWeights yerel klasörü";placeholderText:"Transfer: yerel model.json klasörü";Layout.fillWidth:true}
            UiTextField {id:score;objectName:"visionScore";Accessible.name:"Detection pixel score threshold";text:"0.5";Layout.fillWidth:true}
            UiTextField {id:iou;objectName:"visionIoU";Accessible.name:"Detection IoU thresholds JSON";text:"[0.5,0.75,0.95]";Layout.fillWidth:true}
            UiLabel {text:"Group/subject/video-source ve exact/near ilişkileri union component olur; bileşenler split arasında bölünmez. Review/refit aynı frozen split'i korur. Pretrained bilinen training kaynağı held-out near/grupla örtüşürse transfer reddi. Image bilinear, mask nearest; RGB/255, CNN mean0.5/std0.5. Crop dışı bbox kaybı kayıtlı.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiButton {objectName:"visionRun";text:"Görüntü alt aşamasını CPU'da çalıştır";primary:true;enabled:visionAnalysis.canVisionRun;Layout.fillWidth:true;onClicked:{try{visionAnalysis.startVision(JSON.stringify(panel.config()))}catch(error){localError.text="Tarif alanlarını kontrol edin: "+error}}}
        }
        UiLabel {id:localError;text:"";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiButton {objectName:"visionCancel";visible:visionAnalysis.busy;text:"Görüntü işini iptal et";onClicked:visionAnalysis.cancel();Layout.fillWidth:true}
        StateNotice {heading:"Görüntü hesap durumu";detail:visionAnalysis.errorText||visionAnalysis.message;kind:visionAnalysis.errorText?"error":visionAnalysis.busy?"loading":"info";Layout.fillWidth:true}
        UiLabel {objectName:"visionSummary";text:panel.result.status?panel.result.status+" · "+((panel.result.vision_spec||{}).task||"")+" · görüntü="+(panel.result.images||[]).length+" · model="+(panel.result.model_kind||"fit yok")+"\n"+panel.metricText():"Henüz image run yok";Layout.fillWidth:true;wrapMode:Text.Wrap}
        Repeater {model:(panel.result.transform||{}).preview||[];ColumnLayout {required property var modelData;Layout.fillWidth:true
            UiLabel {text:"Transform preview · "+modelData.partition+" · "+modelData.annotation_status+" · "+modelData.row_id+" · original="+modelData.original_size.join("×");Layout.fillWidth:true;wrapMode:Text.Wrap}
            Canvas {objectName:"visionPreview";Layout.preferredWidth:160;Layout.preferredHeight:160;property var pixels:modelData.transformed;onPixelsChanged:requestPaint();onPaint:{var c=getContext("2d"),n=pixels.length;for(var y=0;y<n;y++)for(var x=0;x<n;x++){var p=pixels[y][x];c.fillStyle="rgb("+p[0]+","+p[1]+","+p[2]+")";c.fillRect(x*width/n,y*height/n,width/n+1,height/n+1)}c.strokeStyle="#ff8a35";c.lineWidth=2;for(var b of modelData.boxes||[]){var z=b.xyxy;c.strokeRect(z[0]*width/n,z[1]*height/n,(z[2]-z[0])*width/n,(z[3]-z[1])*height/n)}}}
            UiLabel {visible:!!modelData.mask;text:"İnsan mask şeması · seçili resize/crop · background=0";Layout.fillWidth:true}
            Canvas {visible:!!modelData.mask;Layout.preferredWidth:160;Layout.preferredHeight:160;property var pixels:modelData.mask||[];onPixelsChanged:requestPaint();onPaint:{var c=getContext("2d"),n=pixels.length;for(var y=0;y<n;y++)for(var x=0;x<n;x++){c.fillStyle=pixels[y][x]===0?"#202532":"hsl("+(pixels[y][x]*67%360)+",80%,60%)";c.fillRect(x*width/n,y*height/n,width/n+1,height/n+1)}}}
            UiLabel {visible:!!modelData.train_augmentation_preview;text:"Yalnız train — horizontal flip önizlemesi";Layout.fillWidth:true}
            Canvas {visible:!!modelData.train_augmentation_preview;Layout.preferredWidth:160;Layout.preferredHeight:160;property var pixels:modelData.train_augmentation_preview||[];onPixelsChanged:requestPaint();onPaint:{var c=getContext("2d"),n=pixels.length;for(var y=0;y<n;y++)for(var x=0;x<n;x++){var p=pixels[y][x];c.fillStyle="rgb("+p[0]+","+p[1]+","+p[2]+")";c.fillRect(x*width/n,y*height/n,width/n+1,height/n+1)}}}
        }}
        UiLabel {text:"Model bbox/mask koordinatları seçili resize/crop içindedir; insan annotation koordinatları EXIF-oriented orijinaldedir. Öneriyi onaylamadan önce bu farkı kontrol edin.";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiLabel {text:"Confusion rows=true/columns=predicted; label order kayıtlı. Detection AP all-point interpolation, score-ranked per class/per-image unique IoU matching; COCO101/crowd/area mAP değil. Mask pooled pixels + present foreground macro IoU/Dice; absent-both undefined, background ayrı. Softmax/region score kalibre değildir. Saliency nedensel açıklama değildir; bu template üretmez.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiCombo {id:row;objectName:"visionReviewRow";accessibleLabel:"İnsan review görüntü RowId";model:visionAnalysis.visionRows;textRole:"label";valueRole:"row_id";Layout.fillWidth:true}
        UiTextArea {id:annotation;objectName:"visionAnnotation";Accessible.name:"Annotation label bbox mask JSON";text:'{"label":"red","boxes":[],"mask":""}';Layout.fillWidth:true;Layout.preferredHeight:100}
        UiTextField {id:reviewer;objectName:"visionReviewer";Accessible.name:"İnsan reviewer kimliği";placeholderText:"Review yapan kişi kimliği";Layout.fillWidth:true}
        UiCheckBox {id:consent;objectName:"visionHumanConsent";text:"Etiket/bbox/mask'ı insan olarak inceledim; model önerisini otomatik ground truth yapmıyorum";Layout.fillWidth:true}
        UiButton {objectName:"visionReview";text:"İnsan onayını yeni annotation revision olarak kaydet";multiline:true;enabled:!visionAnalysis.busy&&consent.checked&&row.currentIndex>=0;onClicked:{visionAnalysis.reviewAnnotation(row.currentValue,annotation.text,reviewer.text);consent.checked=false} Layout.fillWidth:true}
        UiLabel {text:"Review önceki model/metric'i korur; yeni revision metric/model'i invalid eder, refit gerekir. Bbox id/label/xyxy half-open oriented pixel. Mask aynı boyutlu uint8 L PNG. Extracted video frame video-source/sequence/index/time kimliği taşır; tüm video analizi var denmez.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiTextField {id:exportPath;objectName:"visionExportPath";Accessible.name:"Annotation yeni export yolu";placeholderText:"Yeni mutlak annotations.json";Layout.fillWidth:true}
        UiButton {objectName:"visionExport";text:"Annotation/review/identity ve split export";enabled:!visionAnalysis.busy&&!!panel.result.status;onClicked:visionAnalysis.exportAnnotations(exportPath.text);Layout.fillWidth:true}
        UiTextField {id:weightPath;objectName:"visionWeightPath";Accessible.name:"Safe VisionWeights export dosyası";placeholderText:"Yeni mutlak model.json";Layout.fillWidth:true}
        UiTextField {id:license;objectName:"visionLicense";Accessible.name:"Model lisans beyanı";placeholderText:"Model/data lisansı";Layout.fillWidth:true}
        UiTextField {id:datasetNote;objectName:"visionDatasetNote";Accessible.name:"Training dataset beyanı";placeholderText:"Training dataset/varsayımlar";Layout.fillWidth:true}
        UiButton {objectName:"visionWeights";text:"Kapalı CNN safe weights export";enabled:!visionAnalysis.busy&&panel.result.model_kind==="tiny_rgb_cnn/v1";onClicked:visionAnalysis.exportWeights(weightPath.text,license.text,datasetNote.text);Layout.fillWidth:true}
        UiCombo {id:saved;objectName:"visionSaved";accessibleLabel:"Kalıcı vision kayıtları";model:visionAnalysis.savedRuns;textRole:"label";valueRole:"id";Layout.fillWidth:true}
        UiButton {objectName:"visionOpen";text:"Kalıcı vision model/review/snapshot aç";enabled:!visionAnalysis.busy&&saved.currentIndex>=0;onClicked:visionAnalysis.openRun(saved.currentValue);Layout.fillWidth:true}
        UiButton {objectName:"visionPredict";text:"Aktif yeni image snapshot'ında prediction";enabled:!visionAnalysis.busy&&!!panel.result.model_kind&&panel.result.mode!=="annotation_revision";onClicked:visionAnalysis.predictData();Layout.fillWidth:true}
        UiLabel {objectName:"visionPrediction";text:(visionAnalysis.predictionReport.predictions||[]).length?"Yeni görüntü prediction: "+visionAnalysis.predictionReport.predictions.length+" kayıt · fit yapılmadı · model önerisi\n"+JSON.stringify((visionAnalysis.predictionReport.predictions||[]).slice(0,2)):"Yeni görüntü prediction yok";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiCheckBox {id:network;objectName:"visionNetwork";text:"Optional public HTTPS model indirmeyi göster";Layout.fillWidth:true}
        ColumnLayout {visible:network.checked;Layout.fillWidth:true
            UiLabel {text:"Yalnız safe VisionWeights/v1; arbitrary .pt/pickle/remote-code yok. Auth/query URL desteklenmez. Exact boyut/SHA256 ve lisans/dataset beyanı;3same-origin TLS redirect ve offline cache. Startup/açma/prediction download yapmaz.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiTextField {id:url;objectName:"visionURL";Accessible.name:"Model public HTTPS URL";Layout.fillWidth:true}
            UiTextField {id:sha;objectName:"visionSHA";Accessible.name:"Vision model SHA256";Layout.fillWidth:true}
            UiTextField {id:bytes;objectName:"visionBytes";Accessible.name:"Model download byte boyutu";Layout.fillWidth:true}
            UiCheckBox {id:terms;objectName:"visionTerms";text:"Kaynak/model lisansı ve servis koşullarını inceledim; indirmeyi açıkça başlatıyorum";Layout.fillWidth:true}
            UiButton {objectName:"visionDownload";text:"Optional doğrulanmış modeli indir";enabled:terms.checked&&!visionAnalysis.busy;onClicked:visionAnalysis.downloadModel(url.text,sha.text,Number(bytes.text),terms.checked);Layout.fillWidth:true}
        }
        UiButton { visible: false;objectName:"visionHelp";text:"BBox/mask, IoU ve duplicate leakage öğren";helpContext:"model.vision";onClicked:panel.helpRequested(this,helpContext);Layout.fillWidth:true}
    }
}
