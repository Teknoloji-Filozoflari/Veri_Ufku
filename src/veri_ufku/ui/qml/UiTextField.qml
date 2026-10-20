import QtQuick
import QtQuick.Controls
import "FocusScroll.js" as FocusScroll

TextField {
    id: control
    font.pixelSize: Theme.body
    implicitHeight: Theme.controlHeight
    focusPolicy: Qt.StrongFocus
    Accessible.name: placeholderText
    selectByMouse: true
    leftPadding: Theme.md
    rightPadding: Theme.md
    color: enabled ? Theme.text : Theme.muted
    placeholderTextColor: Theme.muted
    selectionColor: palette.highlight
    selectedTextColor: Theme.accentText
    background: Rectangle {
        radius: Theme.radius
        color: control.enabled ? Theme.field : Theme.background
        border.color: control.activeFocus ? control.palette.highlight : Theme.controlBorder
        border.width: control.activeFocus ? 2 : 1
    }
    onActiveFocusChanged: if (activeFocus) Qt.callLater(function() { FocusScroll.reveal(control) })
}
