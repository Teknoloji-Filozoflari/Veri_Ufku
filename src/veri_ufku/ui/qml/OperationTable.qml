import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    required property var tableModel
    required property string title
    property string selectedIdentity: ""
    Layout.fillWidth: true
    Label { text: root.title + " · ilk200 kayıt (görünüm örneği)"; font.bold: true; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    HorizontalHeaderView {
        syncView: table
        Layout.fillWidth: true
        clip: true
        delegate: Rectangle {
            implicitWidth: 160 * Theme.scale; implicitHeight: 36 * Theme.scale
            color: Theme.surface
            border.color: Theme.border
            Label { anchors.fill: parent; anchors.margins: Theme.sm; text: display; elide: Text.ElideRight }
        }
    }
    TableView {
        id: table
        Layout.fillWidth: true
        Layout.preferredHeight: 220 * Theme.scale
        model: root.tableModel
        clip: true
        reuseItems: true
        columnSpacing: 1; rowSpacing: 1
        delegate: Rectangle {
            required property string display
            required property string rowId
            implicitWidth: 160 * Theme.scale; implicitHeight: 36 * Theme.scale
            color: Theme.surface
            border.color: Theme.border
            Label { anchors.fill: parent; anchors.margins: Theme.sm; text: display; elide: Text.ElideRight }
            TapHandler { onTapped: root.selectedIdentity = parent.rowId }
            Accessible.name: display + " · " + rowId
        }
        ScrollBar.horizontal: ScrollBar {}
        ScrollBar.vertical: ScrollBar {}
    }
    Label { text: "Seçili RowId: " + root.selectedIdentity; visible: root.selectedIdentity.length > 0; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
}
