import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "commonResultPanel"
    property bool expert: false
    property string helpContext: "expert-workspace"
    signal helpRequested(var origin, string context)
    spacing: Theme.md
    readonly property var result: visible ? expertWorkspace.selected : ({})
    readonly property var resultChoices: visible ? expertWorkspace.resultRows : []
    UiLabel { text: "Çalışmalar ve sonuçlar"; font.bold: true; font.pixelSize: Theme.heading; Layout.fillWidth: true }
    ColumnLayout {
        visible: panel.expert
        Layout.fillWidth: true
        ModuleDiscovery { Layout.fillWidth: true }
        UiLabel { text: "Kaydedilen analiz sekmeleri"; Layout.fillWidth: true }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.sm
            Repeater { model: expertWorkspace.tabs; delegate: UiButton { required property var modelData; text: modelData.label; onClicked: expertWorkspace.selectResult(modelData.id) } }
        }
        UiCombo { objectName: "workspacePreset"; currentIndex: -1; displayText: currentIndex < 0 ? "Parametre presetini seç" : model[currentIndex].name; accessibleLabel: "Parametre preseti"; model: expertWorkspace.presets; textRole: "name"; Layout.fillWidth: true; onActivated: expertWorkspace.applyPreset(currentIndex) }
    }
    UiCombo { objectName: "workspaceResultChoice"; currentIndex: { let rows=panel.resultChoices; for(let i=0;i<rows.length;i++) if(rows[i].id===panel.result.id) return i; return -1 }
        accessibleLabel: "Sonuç seçimi"; model: panel.resultChoices; textRole: "label"; valueRole: "id"; Layout.fillWidth: true; onActivated: expertWorkspace.selectResult(currentValue) }
    UiLabel { visible: expertWorkspace.errorText.length>0; text: expertWorkspace.errorText; color: Theme.warning; Layout.fillWidth: true; wrapMode: Text.Wrap }
    ColumnLayout {
        visible: !!panel.result.id
        Layout.fillWidth: true
        UiLabel { objectName: "commonResultId"; text: panel.result.id || ""; color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
        UiLabel { text: panel.result.compatibility || ""; visible: text.length>0; color: Theme.warning; Layout.fillWidth: true; wrapMode: Text.Wrap }
        UiLabel { text: "Veri sürümü: " + (panel.result.dataset || "") + "\nYöntem: " + (panel.result.capability || "") + " · sürüm " + (panel.result.method_version || "") + " · parametre sürümü " + (panel.result.parameter_version || "") + "\nSeed: " + (panel.result.seed || "") + "\nKapsam: " + (panel.result.scope || "") + "\nFiltre: " + (panel.result.filters || ""); Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; textFormat: Text.PlainText }
        UiLabel { text: "Uyarılar: " + (panel.result.warnings || ""); Layout.fillWidth: true; wrapMode: Text.Wrap; textFormat: Text.PlainText }
        Flow {
            Layout.fillWidth: true; spacing: Theme.sm
            UiButton { visible: panel.expert; text: "Sekmeyi kaydet / kaldır"; onClicked: expertWorkspace.pin(panel.result.id) }
            UiButton { visible: panel.expert; text: "Karşılaştırmaya ekle / kaldır"; onClicked: expertWorkspace.compare(panel.result.id) }
            UiButton { visible: false; text: "Nasıl hesaplandı?"; onClicked: panel.helpRequested(this, panel.result.readonly ? "expert-workspace" : panel.result.capability) }
            UiButton { visible: false; text: "Nasıl yorumlarım?"; onClicked: panel.helpRequested(this, panel.result.readonly ? "expert-workspace" : panel.result.capability) }
            UiButton { visible: false; text: "Örnekle öğren"; onClicked: panel.helpRequested(this, "expert-workspace") }
        }
        Repeater {
            model: panel.result.artifacts || []
            delegate: ColumnLayout {
                required property var modelData
                Layout.fillWidth: true
                UiLabel { text: modelData.title + " · " + modelData.kind; font.bold: true; Layout.fillWidth: true }
                UiLabel { visible: modelData.kind !== "chart" && modelData.kind !== "table"; text: modelData.content; textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                Repeater {
                    model: modelData.rows || []
                    delegate: Rectangle {
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        implicitHeight: parameterRow.implicitHeight + Theme.sm * 2
                        color: index % 2 ? Theme.raised : Theme.surface
                        radius: Theme.radius
                        RowLayout {
                            id: parameterRow
                            anchors.left: parent.left; anchors.right: parent.right
                            anchors.margins: Theme.sm
                            UiLabel { text: modelData.name; Layout.preferredWidth: Math.min(panel.width / 3, 180); wrapMode: Text.WrapAnywhere }
                            UiLabel { text: modelData.value; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; textFormat: Text.PlainText }
                        }
                    }
                }
                Image { visible: modelData.kind === "chart"; source: modelData.uri || ""; Layout.fillWidth: true; Layout.preferredHeight: visible ? 300 : 0; fillMode: Image.PreserveAspectFit; sourceSize.width: 1200; cache: false }
            }
        }
        UiCheckBox { id: environment; text: "Hesap ortamını göster"; Layout.fillWidth: true }
        UiLabel { visible: environment.checked; text: panel.result.environment || ""; textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
    }
    GridLayout {
        visible: panel.expert && expertWorkspace.comparison.length > 0
        columns: panel.width>850 ? 2 : 1
        Layout.fillWidth: true
        Repeater {
            model: expertWorkspace.comparison
            delegate: ColumnLayout {
                required property var modelData
                Layout.fillWidth: true
                UiLabel { text: modelData.label + "\n" + modelData.id + "\nVeri: " + modelData.dataset; textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                UiLabel { text: modelData.parameters + "\n" + modelData.artifacts[0].content; textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
            }
        }
    }
    UiLabel { visible: panel.expert && expertWorkspace.comparison.length>0; text: "Farklı veri/filtre/kapsamla hesaplanan sonuçlar doğrudan kıyaslanamaz. Bu görünüm yöntem seçmez veya testleri tek aile saymaz."; color: Theme.warning; Layout.fillWidth: true; wrapMode: Text.Wrap }
}
