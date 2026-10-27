import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Frame {
    id: panel
    objectName: "dataContentPanel"
    property string helpContext: "dataset.profile"
    property var content: dataView.dataContent
    signal helpRequested(var origin, string context)
    signal columnSelected()
    padding: Theme.lg
    implicitHeight: body.implicitHeight + topPadding + bottomPadding
    background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius }
    ColumnLayout {
        id: body
        width: panel.availableWidth
        spacing: Theme.md
        UiLabel { text: "Veri içeriği"; font.pixelSize: Theme.subheading; font.bold: true; color: Theme.dataTone; Layout.fillWidth: true; wrapMode: Text.Wrap }
        UiLabel { text: "Dosyanın içinde ne var? Her satır bir kaydı, her sütun o kaydın bir özelliğini anlatır."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
        UiLabel { objectName: "dataContentSummary"; text: panel.content.rows === undefined ? "Henüz veri aktarılmadı. Üstteki alandan dosyanı seçerek başlayabilirsin." : panel.content.rows + " kayıt · " + panel.content.columns + " sütun\nKaynak: " + panel.content.source + "\nBir satır: " + (panel.content.analysis_unit || "Neyi temsil ettiği henüz belirtilmedi."); Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
        UiLabel { visible: dataView.dataDictionary.length > 0; text: "Sütun sözlüğü · bir alan seç, anlamını ve birimini tanımla"; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
        ListView {
            objectName: "dataDictionaryList"
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(contentHeight, 260 * Theme.scale)
            clip: true
            spacing: Theme.sm
            model: dataView.dataDictionary
            ScrollBar.vertical: ScrollBar {}
            delegate: Frame {
                id: entry
                required property var modelData
                width: ListView.view.width
                padding: Theme.md
                background: Rectangle { color: Theme.field; radius: Theme.radius; border.color: dataView.selectedColumn === entry.modelData.id ? Theme.dataTone : Theme.border }
                ColumnLayout {
                    width: entry.availableWidth
                    UiButton { text: entry.modelData.name + " · " + entry.modelData.physical_type; tone: "cyan"; multiline: true; Layout.fillWidth: true; enabled: !dataView.busy; onClicked: { dataView.selectColumn(entry.modelData.id); panel.columnSelected() } }
                    UiLabel { text: entry.modelData.role + (entry.modelData.unit ? " · " + entry.modelData.unit : ""); color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.Wrap }
                    UiLabel { text: entry.modelData.description || "Açıklama eklenmedi. Sütunu seçip aşağıdaki Sütunu tanıt alanına yazabilirsin."; Layout.fillWidth: true; wrapMode: Text.Wrap }
                }
            }
        }
        UiButton { visible: false; text: "Veri içeriğini nasıl yorumlarım?"; tone: "mint"; Layout.fillWidth: true; multiline: true; onClicked: panel.helpRequested(this, "dataset.profile") }
    }
}
