import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "FocusScroll.js" as FocusScroll

Button {
    id: control
    property string helpContext: ""
    property bool primary: false
    property string tone: "warm"
    readonly property color toneColor: Theme.toneColor(tone)
    readonly property color toneSurface: Theme.toneSurface(tone)
    property bool quiet: false
    property string glyph: ""
    property bool multiline: true
    implicitHeight: Math.max(Theme.controlHeight, contentItem.implicitHeight + 16)
    implicitWidth: Math.min(340 * Theme.scale, Math.max(76 * Theme.scale, contentItem.implicitWidth + 28))
    Layout.maximumWidth: implicitWidth
    Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
    padding: 8
    horizontalPadding: 14
    spacing: 8
    focusPolicy: Qt.StrongFocus
    Accessible.name: text
    ToolTip.visible: hovered && contentItem.truncated
    ToolTip.text: text
    onActiveFocusChanged: if (activeFocus) Qt.callLater(function() { FocusScroll.reveal(control) })
    contentItem: Text {
        textFormat: Text.PlainText
        text: (control.glyph ? control.glyph + "  " : "") + control.text
        color: !control.enabled ? Theme.muted : (control.primary ? Theme.accentText : (control.tone !== "warm" ? control.toneColor : Theme.text))
        font.pixelSize: Theme.body
        font.bold: control.primary || control.checked
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        wrapMode: control.multiline ? Text.WordWrap : Text.NoWrap
        elide: control.multiline ? Text.ElideNone : Text.ElideRight
    }
    background: Rectangle {
        radius: Theme.radius
        color: control.primary && control.enabled
            ? (control.down ? Theme.tonePressed(control.tone) : (control.hovered ? Theme.toneHover(control.tone) : control.toneColor))
            : (control.checked ? control.toneSurface : (control.hovered ? Theme.hover : (control.quiet ? "transparent" : Theme.raised)))
        border.color: control.activeFocus || (control.primary && control.enabled) ? control.toneColor : Theme.controlBorder
        border.width: control.activeFocus ? 2 : (control.quiet && !control.checked ? 0 : 1)
        Rectangle {
            anchors.fill: parent
            anchors.margins: -3
            radius: Theme.radius + 3
            color: "transparent"
            border.width: control.activeFocus ? 2 : 0
            border.color: control.toneColor
        }
    }
}
