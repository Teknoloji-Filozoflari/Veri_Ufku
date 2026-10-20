import QtQuick
import QtQuick.Controls
import "FocusScroll.js" as FocusScroll

TextArea {
    id: control
    font.pixelSize: Theme.body
    focusPolicy: Qt.StrongFocus
    activeFocusOnTab: true
    selectByMouse: true
    padding: Theme.md
    color: enabled ? Theme.text : Theme.muted
    placeholderTextColor: Theme.muted
    background: Rectangle {
        radius: Theme.radius
        color: control.enabled ? Theme.field : Theme.background
        border.color: control.activeFocus ? control.palette.highlight : Theme.controlBorder
        border.width: control.activeFocus ? 2 : 1
    }
    Keys.priority: Keys.BeforeItem
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
            nextItemInFocusChain(event.key !== Qt.Key_Backtab && !(event.modifiers & Qt.ShiftModifier)).forceActiveFocus()
            event.accepted = true
        }
    }
    onActiveFocusChanged: if (activeFocus) Qt.callLater(function() { FocusScroll.reveal(control) })
}
