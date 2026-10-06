import QtQuick
import QtQuick.Controls
import "FocusScroll.js" as FocusScroll

Button {
    id: control
    property string helpContext: ""
    property bool primary: false
    property bool quiet: false
    property string glyph: ""
    property bool multiline: false
    implicitHeight: Math.max(Theme.controlHeight, contentItem.implicitHeight + 20)
    implicitWidth: contentItem.implicitWidth + 32
    padding: 12
    spacing: 8
    focusPolicy: Qt.StrongFocus
    Accessible.name: text
    onActiveFocusChanged: if (activeFocus) Qt.callLater(function() { FocusScroll.reveal(control) })
    contentItem: Text {
        textFormat: Text.PlainText
        text: (control.glyph ? control.glyph + "  " : "") + control.text
        color: control.primary && control.enabled ? Theme.onAccent : Theme.text
        font.pixelSize: Theme.body
        font.bold: control.primary || control.checked
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        wrapMode: control.multiline ? Text.WordWrap : Text.NoWrap
        elide: control.multiline ? Text.ElideNone : Text.ElideRight
    }
    background: Rectangle {
        radius: Theme.radius
        color: control.primary && control.enabled ? Theme.accent : (control.hovered || control.checked ? Theme.background : (control.quiet ? "transparent" : Theme.surface))
        border.color: control.activeFocus ? Theme.accent : Theme.border
        border.width: control.activeFocus ? 2 : (control.quiet && !control.checked ? 0 : 1)
        Rectangle {
            anchors.fill: parent
            anchors.margins: -3
            radius: Theme.radius + 3
            color: "transparent"
            border.width: control.activeFocus ? 2 : 0
            border.color: Theme.accent
        }
    }
}
