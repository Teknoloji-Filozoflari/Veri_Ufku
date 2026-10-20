import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "moduleDiscovery"
    property string helpContext: "expert-workspace"
    // Hidden palettes must not probe all optional backends on each job update.
    readonly property var availableModules: visible ? expertWorkspace.modules : []
    spacing: Theme.sm
    UiTextField {
        objectName: "moduleSearch"
        Layout.fillWidth: true
        text: expertWorkspace.query
        placeholderText: "Amaç veya yöntem ara: ilişki, Pearson, histogram…"
        Accessible.name: "Modül araması"
        onTextEdited: expertWorkspace.search(text)
    }
    ListView {
        id: moduleScroll
        objectName: "moduleResults"
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(300 * Theme.scale, Math.max(50, count * 50))
        model: panel.availableModules
        clip: true
        reuseItems: true
        cacheBuffer: 100
        spacing: Theme.sm
        ScrollBar.vertical: ScrollBar {}
        delegate: ColumnLayout {
            required property var modelData
            width: ListView.view.width - 12
            height: implicitHeight
            RowLayout {
                Layout.fillWidth: true
                UiButton { implicitWidth: Theme.controlHeight; Layout.maximumWidth: Theme.controlHeight; text: modelData.favorite ? "★" : "☆"; Accessible.name: "Favori: " + modelData.label; onClicked: expertWorkspace.favorite(modelData.id) }
                UiButton { objectName: "module-" + modelData.id; text: modelData.label + " · " + modelData.maturity; enabled: modelData.enabled; Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.maximumWidth: 10000; onClicked: expertWorkspace.activate(modelData.id) }
                UiButton { text: "Ayrıntı"; onClicked: { details.text=JSON.stringify(expertWorkspace.details(modelData.id), null, 2); details.visible=true } }
            }
            UiLabel { visible: !modelData.enabled; text: modelData.reason; Layout.fillWidth: true; wrapMode: Text.Wrap }
        }
    }
    UiLabel { id: details; visible: false; textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true; color: Theme.secondary }
}
