import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Değerlendirme protokolü: hedef, kayıt ilişkisi, split, fold, seed ve baseline.
// Model aşamasında M-01/M-03/M-04/M-07 yüzeylerinde tek örnek olarak yaşar.
ColumnLayout {
    id: panel
    objectName: "validationProtocol"
    property string helpContext: "model.validation"
    property var structures: ["independent", "group", "time", "group_time"]
    property var availability: ({})
    readonly property string protocolBlock: entity.currentIndex===1&&(structure.currentIndex!==2||!preparation.report.spec||!preparation.report.spec.group)?"Engelli: aynı varlığın geleceği yalnız zaman ve seçili kişi/cihaz anahtarıyla doğrulanabilir. Grup ayrılığıyla birlikte istenemez.":structure.currentIndex!==0&&method.currentIndex!==0?"Engelli: grup/zaman yapısında random veya stratified seçilemez; yapıya uygun varsayılanı seç.":method.currentIndex===2&&preparation.report.spec&&preparation.report.spec.purpose!=="classification"?"Engelli: stratified yalnız kategori hedef içindir.":""
    signal helpRequested(var origin, string context)
    spacing: Theme.md
    function spec() {return {structure: structures[structure.currentIndex], method: method.currentIndex===0?"auto":method.currentIndex===1?"random":"stratified", entity_use:entity.currentIndex===0?"new":"same_future", prediction_moment:moment.text, horizon_seconds:Number(horizon.text), availability:availability, seed:Number(seed.text), folds:Number(folds.text), test_fraction:Number(testRatio.text)/100, validation_fraction:Number(valRatio.text)/100, baseline:["auto","mean","median","prior","most_frequent","stratified"][baseline.currentIndex]}}
    function defaults() {let p=preparation.report.spec;if(!p)return;structure.currentIndex=p.group?(p.time?3:1):(p.time?2:0);availability={};method.currentIndex=0;entity.currentIndex=0;moment.text=p.prediction_context||""}
    Component.onCompleted: {
        panel.pipeline = (preparation.report.plan || {}).version_id || ""
        panel.defaults()
    }
    Connections { target:preparation; function onChanged(){if(panel.pipeline!==(preparation.report.plan||{}).version_id){panel.pipeline=(preparation.report.plan||{}).version_id||"";panel.defaults()}} }
    property string pipeline:""
    UiLabel { text:"Ayırma, çapraz doğrulama ve baseline";font.pixelSize:Theme.heading;font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:"Önce engelsiz bir sayısal/kategori hazırlama planı oluştur. Testi son seçiminden sonra ayrı değerlendir; test sonucuyla ayar seçme. Her test kullanımı ve sonraki koşu seçimi projede kalır.";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
    ColumnLayout {
        objectName: "modelCandidateFrame"
        visible: !!(preparation.modelCandidates && preparation.modelCandidates.candidates && preparation.modelCandidates.candidates.length)
        Layout.fillWidth: true
        spacing: Theme.sm
        UiLabel {
            text: qsTr("Gerekçeli yöntem adayları (henüz fit yok)")
            font.bold: true
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
        UiLabel {
            objectName: "modelCandidatePolicy"
            text: (preparation.modelCandidates.disclaimer || "") + "\n" + (preparation.modelCandidates.leakage_policy || "") + "\n" + (preparation.modelCandidates.test_policy || "") + "\nYapı: " + (preparation.modelCandidates.structure || "") + " — " + (preparation.modelCandidates.structure_note || "") + "\nPlan: " + (preparation.modelCandidates.split_plan || "") + " · başlangıç modeli: " + (preparation.modelCandidates.starter_model || "") + " · durum: " + (preparation.modelCandidates.status || "aday")
            color: Theme.secondary
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
        Repeater {
            model: preparation.modelCandidates.candidates || []
            delegate: ColumnLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: Theme.xs
                UiLabel {
                    objectName: "modelCandidate_" + modelData.id
                    text: qsTr("Aday · ") + modelData.label + " (" + modelData.id + ")\nNeden uygun olabilir: " + modelData.why_suitable + "\nNe zaman değil: " + modelData.when_not_suitable + "\nHazırlık: " + modelData.preparation_needed + "\nÖlçüler: " + (modelData.metrics || []).join(", ") + " · seçili=" + (modelData.selected ? "evet" : "hayır") + " · fit=" + (modelData.fitted ? "evet" : "hayır")
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
            }
        }
    }
    UiCheckBox { id:settings;objectName:"validationSettings";text:"Değerlendirme protokolünü göster";checked:true;Layout.fillWidth:true }
    UiLabel { visible:!!panel.protocolBlock;text:panel.protocolBlock;color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
    ColumnLayout { visible:settings.checked;Layout.fillWidth:true;spacing:Theme.sm
        UiLabel { text:"Kayıtlar nasıl ilişkili?";Layout.fillWidth:true }
        UiCombo { accessibleLabel: "Kayıtların ilişkisi"; id:structure;objectName:"validationStructure";model:["Bağımsız kayıtlar","Aynı kişiye/cihaza bağlı kayıtlar","Zaman sırası","Kişi/cihaz ve zaman birlikte"];Layout.fillWidth:true;onActivated:validation.invalidate() }
        UiLabel { text:structure.currentIndex===0?"Varsayılan: kategoride stratified sınıf oranını korur; sayısal hedefte seed ile rastgele. Bağımsızlık kullanıcının beyanıdır.":structure.currentIndex===1?"Varsayılan: kişiler/cihazlar bütün ayrılır; yeni varlık başarısını ölçer.":structure.currentIndex===2?"Varsayılan: geçmişten geleceğe; hedef ufku eğitim sonunda arındırılır.":"Varsayılan: çakışan grup zaman aralıkları birlikte kalır. Ayrık blok yoksa durur; random fallback yoktur.";Layout.fillWidth:true;wrapMode:Text.Wrap;color:Theme.secondary }
        UiCombo { accessibleLabel: "Ayırma yöntemi"; id:method;objectName:"validationMethod";model:["Yapıya uygun varsayılan","Rastgele (yalnız bağımsız)","Stratified (yalnız bağımsız kategori)"];Layout.fillWidth:true;onActivated:validation.invalidate() }
        UiCombo { accessibleLabel: "Yeni veri varlık kullanımı"; id:entity;objectName:"validationEntity";model:["Yeni varlıklar / bağımsız kayıtlar","Aynı varlığın geleceği (yalnız zaman)"];Layout.fillWidth:true;onActivated:validation.invalidate() }
        UiLabel { visible:structure.currentIndex===3&&entity.currentIndex===1;text:"Engelli: aynı varlığı bölümlerde paylaşmak ve grup ayrılığı çakışır. Yeni varlık seç veya yalnız zaman protokolü kur.";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiTextField { id:moment;objectName:"validationMoment";placeholderText:"Tahmin anı (ör. cihaz çalıştırılmadan önce)";maximumLength:1000;Layout.fillWidth:true;Accessible.name:"Tahmin anı";onTextEdited:validation.invalidate() }
        UiLabel { text:"Hedef ufku (saniye; 1 gün = 86400)";Layout.fillWidth:true }
        UiTextField { id:horizon;objectName:"validationHorizon";text:"0";placeholderText:"Hedef ufku, saniye (1 gün = 86400)";Layout.fillWidth:true;Accessible.name:"Hedef ufku saniye";onTextEdited:validation.invalidate() }
        UiLabel { text:"Destek sınırı: hedef ufku sabit saniye süresidir. Takvim ayı, kayıt bazlı değişen ufuk veya gecikmeli etiket kullanılabilirliği protokolü desteklenmiyor; bu planla çalıştırmayın.";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { text:"Her özelliğin ne zaman bilindiğini kaydet: 0 tahmin anında, negatif daha önce. Pozitif gelecek bilgi reddedilir. Bu bir kullanıcı beyanıdır.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:preparation.report.spec?preparation.columns.filter(c=>preparation.report.spec.features.indexOf(c.id)>=0):[]
            ColumnLayout { required property var modelData;Layout.fillWidth:true
                UiLabel { text:modelData.name;Layout.fillWidth:true }
                UiTextField { id:offset;objectName:"validationOffset_"+modelData.name;text:"0";placeholderText:"Tahmin anına göre saniye farkı";Accessible.name:modelData.name+" kullanılabilirlik zamanı";Layout.fillWidth:true;onTextEdited:{let a=Object.assign({},panel.availability);a[modelData.id]={offset_seconds:Number(text),note:note.text};panel.availability=a;validation.invalidate()} }
                UiTextField { id:note;objectName:"validationNote_"+modelData.name;placeholderText:"Bu bilgi ne zaman/neden mevcut?";maximumLength:1000;Accessible.name:modelData.name+" kullanılabilirlik gerekçesi";Layout.fillWidth:true;onTextEdited:{let a=Object.assign({},panel.availability);a[modelData.id]={offset_seconds:Number(offset.text),note:text};panel.availability=a;validation.invalidate()} }
            }
        }
        UiLabel { text:"Final test oranı (%)";Layout.fillWidth:true }
        UiTextField { id:testRatio;objectName:"validationTestRatio";text:"20";placeholderText:"Final test yüzdesi";Accessible.name:"Final test yüzdesi";Layout.fillWidth:true;onTextEdited:validation.invalidate() }
        UiLabel { text:"Validation oranı (%)";Layout.fillWidth:true }
        UiTextField { id:valRatio;objectName:"validationValRatio";text:"20";placeholderText:"Validation yüzdesi";Accessible.name:"Validation yüzdesi";Layout.fillWidth:true;onTextEdited:validation.invalidate() }
        UiLabel { text:"Geliştirme CV fold sayısı (2..10)";Layout.fillWidth:true }
        UiTextField { id:folds;objectName:"validationFolds";text:"3";placeholderText:"CV fold sayısı 2..10";Accessible.name:"CV fold sayısı";Layout.fillWidth:true;onTextEdited:validation.invalidate() }
        UiLabel { text:"Tekrar üretim seed değeri";Layout.fillWidth:true }
        UiTextField { id:seed;objectName:"validationSeed";text:"42";placeholderText:qsTr("Seed");Accessible.name:qsTr("Seed");Layout.fillWidth:true;onTextEdited:validation.invalidate() }
        UiCombo { accessibleLabel: "Başlangıç referans modeli"; id:baseline;objectName:"validationBaseline";model:["Amaç için varsayılan baseline","Regresyon: ortalama","Regresyon: medyan","Kategori: sınıf öncülü (prior)","Kategori: en sık sınıf","Kategori: eğitim oranıyla rastgele"];Layout.fillWidth:true;onActivated:validation.invalidate() }
        UiLabel { text:"Yaklaşık train: "+Math.floor((preparation.report.eligible_n||0)*(1-Number(testRatio.text)/100-Number(valRatio.text)/100))+" kayıt; "+(Number(folds.text)+1)+" pipeline fit. Grup/zaman ve ufuk gerçek boyutu azaltabilir. Maliyet n × özellik/kategori boyutu × fold sayısıyla artar; süre ve yeterlilik garantisi yok. Gerçek bölüm/fold boyutları sonuçta gösterilir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiButton { objectName:"validationRun";text:"Validation/CV baseline çalıştır ve kaydet";primary:true;tone:"violet";multiline:true;Layout.fillWidth:true;enabled:validation.canRun&&!panel.protocolBlock;onClicked:validation.create(JSON.stringify(panel.spec())) }
    }
}
