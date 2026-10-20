import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id:panel
    objectName:"reportPanel"
    signal helpRequested(var origin, string context)
    property var formats:["csv","json","jsonl","parquet","xlsx"]
    property var description:({})
    property string describedBinding:""
    Connections { target:dataView; function onChanged(){ var binding=dataView.viewSummary; if(binding!==panel.describedBinding){ panel.describedBinding=binding; panel.description=({}); loss.checked=false } } }
    property string pendingKind:"data"
    property string pendingFormat:"csv"
    function describe(){ description=exports.describe(formats[format.currentIndex],scope.currentIndex===0 ? "view":"full",safe.checked,nullMarker.text) }
    function parameters(){return pendingKind==="data" ? {format:pendingFormat,scope:scope.currentIndex===0 ? "view":"full",spreadsheet_safe:safe.checked,accept_loss:loss.checked,null_marker:nullMarker.text}:{format:pendingFormat,title:title.text,purpose:purpose.text,scope:scope.currentIndex===0 ? "view":"full",table_rows:rows.value} }
    function choose(kind,fmt){pendingKind=kind;pendingFormat=fmt;target.nameFilters=[fmt.toUpperCase()+" (*."+fmt+")"];target.defaultSuffix=fmt;if(outputPath.text.trim()) exports.create(kind,JSON.stringify(panel.parameters()),outputPath.text.trim()); else target.open()}
    UiLabel { text:"Yeni çıktı dosyası yolu (boşsa dosya seçicisi açılır)"; Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiTextField { id:outputPath;objectName:"reportOutputPath";Accessible.name:"Yeni rapor veya veri dosyası yolu";Layout.fillWidth:true }
    UiLabel { text:"Verini ve bulgularını kaydet"; font.pixelSize:Theme.heading; font.bold:true; Layout.fillWidth:true; wrapMode:Text.Wrap }
    UiCombo { accessibleLabel: "Verini ve bulgularını kaydet"; model:dataView.datasets; textRole:"label"; valueRole:"id"; Layout.fillWidth:true; onActivated:{loss.checked=false;dataView.selectDataset(currentValue);panel.describe()} }
    UiLabel { text:dataView.viewSummary; Layout.fillWidth:true; wrapMode:Text.Wrap }
    UiLabel { text:"Kapsam"; Layout.fillWidth:true }
    UiCombo { accessibleLabel: "Dışa aktarma kapsamı"; id:scope; objectName:"exportScope"; model:["Mevcut filtreli tüm kayıtlar","Tam dataset (filtreleri kullanma)"]; Layout.fillWidth:true; onActivated:panel.describe() }
    UiLabel { text:"Temizlenmiş veri dışa aktarma"; font.pixelSize:Theme.subheading; Layout.fillWidth:true }
    UiCombo { accessibleLabel: "Çıktı biçimi"; id:format; objectName:"exportFormat"; model:["CSV — şema korunmaz","JSON — nesne listesi","JSONL — satır başına nesne","Parquet — fiziksel türleri koru","XLSX — sınırlı, formülsüz tablo"]; currentIndex:3; Layout.fillWidth:true; onActivated:{loss.checked=false;panel.describe()} }
    UiButton { objectName:"exportDescribe"; text:"Format kayıplarını ve güvenlik politikasını göster"; onClicked:panel.describe(); Layout.fillWidth:true; multiline:true }
    UiLabel { text:description.error||description.null_policy||"Önce format sınırlarını inceleyin. Parquet fiziksel türleri korur; metin formatları rol/birim/şema taşımıyor."; Layout.fillWidth:true; wrapMode:Text.Wrap }
    UiLabel { text:(description.date_policy||"")+"\n"+(description.limits||"")+"\n"+(description.safe_policy||"")+"\n"+(description.metadata_policy||""); Layout.fillWidth:true; wrapMode:Text.Wrap }
    Repeater { model:description.losses||[]; UiLabel { required property var modelData; text:modelData.column+" · "+modelData.source_type+" → "+modelData.output_type; Layout.fillWidth:true; wrapMode:Text.Wrap; color:Theme.warning } }
    UiCheckBox { id:safe; Layout.minimumWidth:0; contentItem:Text { text:safe.text; font:safe.font; color:Theme.text; wrapMode:Text.WordWrap; leftPadding:safe.indicator.width+safe.spacing; verticalAlignment:Text.AlignVCenter } objectName:"exportSafe"; checked:true; text:"CSV metinlerini spreadsheet formül yorumuna karşı koru"; visible:format.currentIndex===0; Layout.fillWidth:true; onClicked:panel.describe() }
    UiLabel { visible:format.currentIndex===0 && !safe.checked; text:"Koruma kapalı: spreadsheet programı =,+,-,@ ile başlayan metni formül olarak yorumlayabilir. XLSX metin hücreleri her zaman formülsüzdür."; Layout.fillWidth:true; wrapMode:Text.Wrap; color:Theme.warning }
    UiTextField { id:nullMarker; objectName:"exportNullMarker"; text:"\\N"; maximumLength:32; onEditingFinished:panel.describe(); visible:format.currentIndex===0; Layout.fillWidth:true; Accessible.name:"CSV null işareti" }
    UiCheckBox { id:loss; Layout.minimumWidth:0; contentItem:Text { text:loss.text; font:loss.font; color:Theme.text; wrapMode:Text.WordWrap; leftPadding:loss.indicator.width+loss.spacing; verticalAlignment:Text.AlignVCenter } objectName:"exportAcceptLoss"; text:"Format tür kayıplarını ve seçili korumanın metin etkisini okudum"; visible:format.currentIndex!==3; Layout.fillWidth:true }
    UiButton { objectName:"exportData"; helpContext:"export"; text:"Veriyi yeni dosyaya aktar"; primary:true; enabled:!projects.busy && dataView.datasets.length>0 && (format.currentIndex===3 || loss.checked); onClicked:panel.choose("data",panel.formats[format.currentIndex]); Layout.fillWidth:true; multiline:true }
    UiButton { tone: "mint"; text:"Export yardımı"; helpContext:"export"; onClicked:panel.helpRequested(this,"export"); Layout.fillWidth:true }
    UiLabel { text:"Yerel rapor"; font.pixelSize:Theme.subheading; Layout.fillWidth:true }
    UiTextField { id:title; objectName:"reportTitle"; text:"Veri_Ufku veri inceleme raporu"; maximumLength:200; Layout.fillWidth:true; Accessible.name:"Rapor başlığı" }
    UiTextArea { id:purpose; objectName:"reportPurpose"; text:qsTr("Dosyamı anlamak istiyorum"); wrapMode:TextEdit.Wrap; Layout.fillWidth:true; Accessible.name:"Raporun amacı" }
    UiLabel { text:"Rapor; kaynak/köken, sürüm/filtre, kaydedilmiş profil/kalite, temizleme geçmişi, tablo örneği ve bu sürümün grafikleriyle hazırlanır. Grafik kaydedilmediyse güncel grafik de eklenir. Eski bulgular kendi sürümüyle görünür; eksik bölümler sonuç uydurmaz. HTML/PDF font ve resimleri yereldir."; Layout.fillWidth:true; wrapMode:Text.Wrap }
    UiSpinBox { id:rows; objectName:"reportTableRows"; from:1; to:200; value:100; editable:true; Accessible.name:"Raporda gösterilecek azami tablo kaydı" }
    Flow { Layout.fillWidth:true; spacing:Theme.sm
        UiButton { objectName:"reportHTML"; text:"HTML raporu kaydet"; enabled:!projects.busy && dataView.datasets.length>0; onClicked:panel.choose("report","html") }
        UiButton { objectName:"reportPDF"; text:"PDF raporu kaydet"; enabled:!projects.busy && dataView.datasets.length>0; onClicked:panel.choose("report","pdf") }
        UiButton { text:qsTr("İptal"); enabled:exports.busy; onClicked:exports.cancel() }
        UiButton { tone: "mint"; text:qsTr("Bu ne işe yarar?"); helpContext:"report"; onClicked:panel.helpRequested(this,"report") }
    }
    StateNotice { Layout.fillWidth:true; kind:exports.errorText ? "error":exports.busy ? "loading":"info"; heading:"Çıktı durumu"; detail:exports.errorText||exports.message }
    UiLabel { objectName:"exportReceipt"; text:exports.receipt.dataset_version ? "Sürüm: "+exports.receipt.dataset_version+"\nKayıt: "+(exports.receipt.verified_rows===undefined ? exports.receipt.rows:exports.receipt.verified_rows)+" · Format: "+exports.receipt.format+"\nDosya: "+exports.receipt.published.path+"\nKoruma eklenen metin: "+(exports.receipt.spreadsheet_escaped||0)+" · Metne aktarılan sayı: "+(exports.receipt.numeric_to_text||0):""; Layout.fillWidth:true; wrapMode:Text.Wrap }
    UiCheckBox { id:receiptDetails; Layout.minimumWidth:0; contentItem:Text { text:receiptDetails.text; font:receiptDetails.font; color:Theme.text; wrapMode:Text.WordWrap; leftPadding:receiptDetails.indicator.width+receiptDetails.spacing; verticalAlignment:Text.AlignVCenter } text:"Tür kaybı ve doğrulama ayrıntılarını göster"; Layout.fillWidth:true }
    UiLabel { visible:receiptDetails.checked; text:JSON.stringify(exports.receipt); Layout.fillWidth:true; wrapMode:Text.Wrap }
    UiButton { objectName:"exportSaveProject"; text:"Projeyi kaydet (temizleme geçmişi ve çıktı kaydı)"; enabled:projects.opened && !projects.busy && !projects.readOnly; onClicked:projects.request("save"); Layout.fillWidth:true; multiline:true }
    FileDialog { id:target; objectName:"exportTarget"; title:"Yeni çıktı dosyası seçin; mevcut kaynak/dosya korunur"; fileMode:FileDialog.SaveFile; onAccepted:exports.create(panel.pendingKind,JSON.stringify(panel.parameters()),selectedFile.toString()) }
}
