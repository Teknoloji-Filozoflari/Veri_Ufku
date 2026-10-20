import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Frame {
    id: panel
    objectName: "savedColumnNotesPanel"
    property var notes: dataView.dataDictionary.filter(function(column) { return column.description && column.description.trim().length > 0 })
    padding: Theme.md
    implicitHeight: body.implicitHeight + topPadding + bottomPadding
    background: Rectangle { color: Theme.surface; radius: Theme.radius; border.color: Theme.border }
    ColumnLayout {
        id: body
        width: panel.availableWidth
        spacing: Theme.sm
        UiLabel { text: qsTr("Sütun notları"); font.bold: true; color: Theme.dataTone; Layout.fillWidth: true }
        ListView {
            id: list
            objectName: "savedColumnNotesList"
            model: panel.notes
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(contentHeight, 220 * Theme.scale)
            spacing: Theme.sm
            clip: true
            ScrollBar.vertical: ScrollBar {}
            delegate: RowLayout {
                id: entry
                required property var modelData
                width: ListView.view.width
                spacing: Theme.md
                UiLabel {
                    text: entry.modelData.name
                    textFormat: Text.PlainText
                    font.bold: true
                    Layout.preferredWidth: Math.min(170 * Theme.scale, entry.width * 0.3)
                    Layout.alignment: Qt.AlignTop
                    wrapMode: Text.WrapAnywhere
                }
                UiLabel {
                    objectName: "savedColumnNote_" + entry.modelData.id
                    text: entry.modelData.description
                    textFormat: Text.PlainText
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.alignment: Qt.AlignTop
                    wrapMode: Text.WrapAnywhere
                }
            }
        }
    }
}
