import QtQuick
import QtQuick.Controls

ComboBox {
    id: control
    implicitHeight: Theme.controlHeight
    font.pixelSize: Theme.body
    focusPolicy: Qt.StrongFocus
    background: Rectangle {
        color: Theme.surface
        radius: Theme.radius
        border.color: control.activeFocus ? Theme.accent : Theme.border
        border.width: control.activeFocus ? 2 : 1
    }
}
