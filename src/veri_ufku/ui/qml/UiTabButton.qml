import QtQuick
import QtQuick.Controls

TabButton {
    id: control
    property string tone: "cyan"
    implicitHeight: Math.max(Theme.controlHeight + 4, contentItem.implicitHeight + 24)
    padding: 12
    focusPolicy: Qt.StrongFocus
    Accessible.name: text
    contentItem: UiLabel {
        text: control.text
        color: control.checked ? Theme.toneColor(control.tone) : Theme.secondary
        font.pixelSize: Theme.body
        font.bold: control.checked
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        wrapMode: Text.WordWrap
    }
    background: Rectangle {
        color: control.checked ? Theme.surface : (control.hovered ? Theme.hover : Theme.chrome)
        radius: Theme.radius
        border.color: Theme.toneColor(control.tone)
        border.width: control.activeFocus ? 2 : 0
        Rectangle {
            height: 3
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            color: Theme.toneColor(control.tone)
            visible: control.checked
            radius: 1.5
        }
    }
}
