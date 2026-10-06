import QtQuick
import QtQuick.Controls
import "FocusScroll.js" as FocusScroll

ComboBox {
    id: control
    implicitHeight: Theme.controlHeight
    font.pixelSize: Theme.body
    focusPolicy: Qt.StrongFocus
    onActiveFocusChanged: if (activeFocus) Qt.callLater(function() { FocusScroll.reveal(control) })
    background: Rectangle {
        color: Theme.surface
        radius: Theme.radius
        border.color: control.activeFocus ? Theme.accent : Theme.border
        border.width: control.activeFocus ? 2 : 1
    }
}
