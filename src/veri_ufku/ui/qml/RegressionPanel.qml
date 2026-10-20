import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "regressionPanel"
    property var protocol
    property bool protocolBlocked: false
    property string helpContext: "model.regression"
    signal helpRequested(var origin, string context)
    readonly property var report: validation.summaryReport.regression && !validation.summaryReport.uncertainty ? validation.summaryReport : ({})
    spacing: Theme.md
    UiLabel { text:"Bir sayıyı tahmin etmek istiyorum";font.pixelSize:Theme.heading;font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:"Yukarıda sayısal hedefi, kullanılacak özellikleri ve hazırlığı seç. Bölme/tahmin bağlamı bu ekranın değerlendirme protokolünden alınır. Hedef özellik olarak kullanılamaz. Eksik hedefler açıkça kapsam dışı bırakılır; eksik özellikler yalnız train/fold içinde hazırlanır.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:"Baseline: train hedefinin ortalama/medyanı; ucuz merkez referansı, her zaman karşılaştırılır.\nDoğrusal: özelliklerin doğrusal katkısı; Ridge: katsayıları küçültür, scaling önerilir.\nRandomForest: doğrusal olmayan ilişkiler için sınırlı ağaçlar; daha pahalı. Forest en fazla 20.000, diğer adaylar 100.000 uygun kayıt; yoğun dönüşüm en fazla 4 milyon hücre ve iş bütçesi. Sessiz örnekleme yok.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCheckBox { id:linear;text:"Doğrusal adayı karşılaştır";checked:true;Layout.fillWidth:true;onClicked:validation.invalidate() }
    UiCheckBox { id:ridge;text:"Ridge adayı karşılaştır";checked:true;Layout.fillWidth:true;onClicked:validation.invalidate() }
    UiCombo { accessibleLabel: "Düzenlileştirme kuvveti"; id:alpha;objectName:"regressionAlpha";model:["Ridge alpha = 0.1","Ridge alpha = 1 (varsayılan)","Ridge alpha = 10"];currentIndex:1;Layout.fillWidth:true;onActivated:validation.invalidate() }
    UiCheckBox { id:forest;text:"RandomForest adayı karşılaştır";checked:true;Layout.fillWidth:true;onClicked:validation.invalidate() }
    UiCombo { accessibleLabel: "Ağaç sayısı"; id:trees;model:["25 ağaç","50 ağaç (varsayılan)","100 ağaç"];currentIndex:1;Layout.fillWidth:true;onActivated:validation.invalidate() }
    UiCombo { accessibleLabel: "Ağaç derinliği"; id:depth;model:["Derinlik 4","Derinlik 8 (varsayılan)","Derinlik 12"];currentIndex:1;Layout.fillWidth:true;onActivated:validation.invalidate() }
    UiTextField { id:unit;objectName:"regressionUnit";placeholderText:"Hedef ölçüm birimi (ör. TL, kg, saniye)";maximumLength:80;Accessible.name:"Hedef ölçüm birimi";Layout.fillWidth:true;onTextEdited:validation.invalidate() }
    UiLabel { text:"Aday başına validation + CV fit yapılır. En düşük geliştirme CV ortalama MAE adayı seçilir; eşitlikte listedeki ilk aday. Dar ayarlar her koşuda sabittir; sınırsız AutoML yok. Train miktarı için evrensel yeterlilik garantisi verilmez.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:"Tahmini fit sayısı: "+((1+Number(linear.checked)+Number(ridge.checked)+Number(forest.checked))*((panel.protocol?panel.protocol.folds:3)+1))+". Forest iş yükü ayrıca ağaç sayısı ve derinliğiyle artar. RAM/duvar süresi sınırı aşılırsa koşu başarısız olur; tamamlanmış gibi gösterilmez.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiButton { objectName:"regressionRun";text:"Adayları yalnız validation/CV ile karşılaştır ve kaydet";primary:true;tone:"violet";multiline:true;Layout.fillWidth:true;enabled:validation.canRun&&preparation.report.spec&&preparation.report.spec.purpose==="regression"&&!panel.protocolBlocked&&unit.text.trim().length>0;onClicked:{let c=["baseline"];if(linear.checked)c.push("linear");if(ridge.checked)c.push("ridge");if(forest.checked)c.push("forest");validation.createRegression(JSON.stringify(panel.protocol),JSON.stringify({candidates:c,alpha:[0.1,1,10][alpha.currentIndex],trees:[25,50,100][trees.currentIndex],depth:[4,8,12][depth.currentIndex],unit:unit.text.trim()}))} }
    UiButton { text:"Regresyon, hata birimi, artık ve aşırı öğrenme";helpContext:"model.regression";multiline:true;Layout.fillWidth:true;onClicked:panel.helpRequested(this,helpContext) }
    ColumnLayout { visible:!!panel.report.regression;Layout.fillWidth:true;spacing:Theme.md
        UiLabel { objectName:"regressionScope";text:panel.report.mode==="final"?"FINAL TEST — aday karşılaştırması içermez":"GELİŞTİRME — validation/CV aday karşılaştırması";font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { text:"Seçilen aday: "+(panel.report.selected_model||"")+" · "+(panel.report.regression?panel.report.regression.unit:"")+"\n"+(panel.report.interpretation==="exploratory"?"KEŞİFSEL: önceki test kullanımı var. Bu sonuç bağımsız final değerlendirme olarak yorumlanamaz.":"Yalnız bu projede kayıtlı test kullanımı bilinir; proje dışı kullanım bilinmez.");color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { text:panel.report.regression?"Kayıtlı ayarlar: Ridge alpha="+panel.report.regression.alpha+" · Forest ağaç="+panel.report.regression.trees+" · derinlik="+panel.report.regression.depth:"";Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:panel.report.comparison||[];UiLabel { required property var modelData;text:modelData.model+" · geliştirme CV MAE = "+modelData.cv_mae.toFixed(6)+" "+panel.report.regression.unit+"\nValidation: "+modelData.validation_metrics.map(m=>m.metric+"="+(m.value===null?"tanımsız":m.value.toFixed(6))).join(" · ");Layout.fillWidth:true;wrapMode:Text.Wrap } }
        UiLabel { text:"MAE, ortalama mutlak hatayı hedefin biriminde anlatır; ör. MAE 5 TL, ortalama mutlak sapma 5 TL. RMSE büyük hatalara daha duyarlıdır. R² negatif olabilir; sabit değerlendirme hedefinde tanımsız gösterilir. Bu metrikler bir doğruluk yüzdesi değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:(panel.report.evaluations||[]).filter(e=>e.scope==="validation"||e.scope==="final_test");ColumnLayout { required property var modelData;Layout.fillWidth:true;spacing:Theme.sm
            UiLabel { text:modelData.scope+" · grafik: "+modelData.prediction_coverage.displayed+" / "+modelData.prediction_coverage.total+" kayıt; metrikler bölümün tamamını kapsar. Artık = gerçek − tahmin.";Layout.fillWidth:true;wrapMode:Text.Wrap }
            PredictionPlot { objectName:"regressionActualPlot";points:modelData.predictions;residual:false;Layout.fillWidth:true;Layout.preferredHeight:240 }
            PredictionPlot { objectName:"regressionResidualPlot";points:modelData.predictions;residual:true;Layout.fillWidth:true;Layout.preferredHeight:240 }
        } }
        UiLabel { visible:panel.report.mode!=="final";text:"Final test için aşağıdaki ayrı onayı kullan. Seçilen CV adayı ve ayarları dondurulur; testte adaylar yarıştırılmaz.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    }
}
