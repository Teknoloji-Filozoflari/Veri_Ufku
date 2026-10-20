import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    required property var tableModel
    required property string title
    property string selectedIdentity: ""
    Layout.fillWidth: true
    UiLabel { text: root.title + " · ilk200 kayıt (görünüm örneği)"; font.bold: true; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    HorizontalHeaderView {
        syncView: table
        resizableColumns: true
        activeFocusOnTab: false
        keyNavigationEnabled: false
        Layout.fillWidth: true
        clip: true
        delegate: Rectangle {
            implicitWidth: 160 * Theme.scale; implicitHeight: 36 * Theme.scale
            color: Theme.raised
            border.color: Theme.border
            UiLabel { anchors.fill: parent; anchors.margins: Theme.sm; text: display; font.bold: true; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
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
            required property int row
            implicitWidth: 160 * Theme.scale; implicitHeight: 36 * Theme.scale
            color: root.selectedIdentity === rowId ? Theme.violetSurface : row % 2 ? Theme.alternateRow : Theme.surface
            UiLabel { anchors.fill: parent; anchors.margins: Theme.sm; text: display; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
            TapHandler { onTapped: root.selectedIdentity = parent.rowId }
            HoverHandler { id: hover }
            ToolTip.visible: hover.hovered
            ToolTip.text: display
            Accessible.name: display + " · " + rowId
        }
        ScrollBar.horizontal: ScrollBar {}
        ScrollBar.vertical: ScrollBar {}
    }
    UiLabel { text: "Seçili RowId: " + root.selectedIdentity; visible: root.selectedIdentity.length > 0; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
}
