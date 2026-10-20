import QtQuick
import QtQuick.Controls
import "FocusScroll.js" as FocusScroll

SpinBox {
    id: control
    font.pixelSize: Theme.body
    implicitHeight: Theme.controlHeight
    focusPolicy: Qt.StrongFocus
    Component.onCompleted: contentItem.Accessible.name = Qt.binding(function() { return control.Accessible.name })
    onActiveFocusChanged: if (activeFocus) Qt.callLater(function() { FocusScroll.reveal(control) })
}
