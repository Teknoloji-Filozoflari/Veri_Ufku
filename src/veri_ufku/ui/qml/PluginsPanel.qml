import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id:root
    signal helpRequested(var origin,string context)
    spacing:Theme.md
    UiCheckBox { id:expanded;objectName:"pluginsExpanded";text:"Uzman eklentileri / SDK";Layout.fillWidth:true }
    ColumnLayout {
        visible:expanded.checked;Layout.fillWidth:true
        UiLabel { text:"Manifest incelemek kod çalıştırmaz. Yalnız güvendiğiniz Python eklentisini açıkça çalıştırın. Ayrı process güvenli OS sandbox değildir: eklenti aynı kullanıcının dosya, ağ ve keyring haklarına erişebilir; manifest izinleri işletim sistemi tarafından kısıtlanmaz. Kötü niyetli koddan kaynak/proje koruma garantisi yoktur.";wrapMode:Text.WordWrap;Layout.fillWidth:true }
        UiButton { objectName:"pluginsHelp";text:"Eklenti yeteneği, trusted code ve bağımlılık yardımı";helpContext:"plugin.sdk";onClicked:helpRequested(this,"plugin.sdk") }
        UiTextField { id:manifest;objectName:"pluginsManifest";Accessible.name:"Kullanıcının seçtiği yerel plugin manifest.json";placeholderText:"/tam/yol/ornek/manifest.json";Layout.fillWidth:true }
        UiButton { objectName:"pluginsInspect";text:"Yalnız manifest / kod hash / ortam uyumluluğunu incele";enabled:!plugins.busy;onClicked:{trusted.checked=false;network.checked=false;plugins.inspectManifest(manifest.text)} }
        ScrollView { id:inspection;Layout.fillWidth:true;Layout.preferredHeight:260;contentWidth:availableWidth
            UiLabel { width:inspection.availableWidth;text:plugins.inspectionText;textFormat:Text.PlainText;wrapMode:Text.WrapAnywhere }
        }
        UiCombo { id:dataset;objectName:"pluginsDataset";accessibleLabel:"Eklentiye verilen dataset sürümü";model:plugins.datasets;textRole:"label";valueRole:"id";Layout.fillWidth:true }
        UiButton { objectName:"pluginsTemplate";text:"Manifestten parametre / kolon tarifi";onClicked:recipe.text=plugins.template(dataset.currentValue || "") }
        UiTextArea { id:recipe;objectName:"pluginsRecipe";Accessible.name:"PluginInput sürüm, ColumnId, parametre ve seed JSON";property string helpContext:"plugin.sdk";textFormat:TextEdit.PlainText;wrapMode:Text.WrapAnywhere;Layout.fillWidth:true;Layout.preferredHeight:150 }
        UiCheckBox { id:trusted;objectName:"pluginsTrusted";text:"Bu kod hash'ine ve bildirilen izinlere güveniyorum; aynı kullanıcı haklarıyla çalıştırmayı seçiyorum";Layout.fillWidth:true }
        UiCheckBox { id:network;objectName:"pluginsNetwork";text:"Manifestte bildirilen ağ kullanımını ayrıca başlatmayı seçiyorum (ağ izni OS kısıtlaması değildir)";Layout.fillWidth:true }
        UiButton { objectName:"pluginsRun";text:"Seçili trusted eklentiyi çalıştır ve sonucu kaydet";enabled:!plugins.busy && trusted.checked;onClicked:plugins.execute(recipe.text,trusted.checked,network.checked) }
        UiButton { objectName:"pluginsCancel";text:"Eklenti görevini iptal et";enabled:plugins.busy;onClicked:plugins.cancel() }
        UiCombo { id:saved;objectName:"pluginsSaved";accessibleLabel:"Eklenti olmadan da okunabilen kayıtlı sonuç";model:plugins.saved;textRole:"label";valueRole:"id";Layout.fillWidth:true }
        UiButton { objectName:"pluginsOpen";text:"Kayıtlı JSON sonucu aç (eklenti yüklemez)";enabled:!plugins.busy && !!saved.currentValue;onClicked:plugins.openReport(saved.currentValue) }
        UiLabel { text:"SDK: importer/transform/stat/model/chart/lesson için API1 ve tür sözleşmeleri. Bu host bounded sonuç artifact'ı arşivler; importer/transform tablo çıktısını aktif dataset'e uygulama, model predict/load ve otomatik ders kataloğu kurulumu desteklenmiyor. Eksik eklentide kayıtlı çıktı ve yardım okunur; recompute için aynı manifest/hash/ortam ve yeni güven onayı gerekir. Otomatik pip/install, discovery veya açılışta eklenti çalıştırma yok.";wrapMode:Text.WordWrap;Layout.fillWidth:true }
        ScrollView { id:out;Layout.fillWidth:true;Layout.preferredHeight:340;contentWidth:availableWidth
            UiLabel { objectName:"pluginsOutput";width:out.availableWidth;text:plugins.outputText+"\n\nKaydedilmiş eklenti yardımı\n"+plugins.pluginHelp;textFormat:Text.PlainText;wrapMode:Text.WrapAnywhere }
        }
        UiLabel { objectName:"pluginsError";text:plugins.errorText;color:Theme.warning;wrapMode:Text.WordWrap;Layout.fillWidth:true }
    }
}
