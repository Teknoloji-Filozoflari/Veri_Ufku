import QtQuick
import QtQuick.Controls
import "FocusScroll.js" as FocusScroll

ComboBox {
    id: control
    property string accessibleLabel: ""
    Accessible.name: accessibleLabel
    Accessible.description: currentText
    property string tone: ""
    implicitHeight: Theme.controlHeight
    font.pixelSize: Theme.body
    focusPolicy: Qt.StrongFocus
    leftPadding: Theme.md
    rightPadding: indicator.width + Theme.md
    ToolTip.visible: hovered && displayText.length > 35
    ToolTip.text: displayText
    ToolTip.delay: 500
    onActiveFocusChanged: if (activeFocus) Qt.callLater(function() { FocusScroll.reveal(control) })
    background: Rectangle {
        color: Theme.field
        radius: Theme.radius
        border.color: control.activeFocus ? (control.tone ? Theme.toneColor(control.tone) : control.palette.highlight) : Theme.controlBorder
        border.width: control.activeFocus ? 2 : 1
    }
}
