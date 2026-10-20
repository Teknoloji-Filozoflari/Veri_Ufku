import QtQuick
import QtQuick.Controls

Button {
    id: control
    property string symbol: "sprout"
    property string tone: "warm"
    property string accessibleLabel: ""
    implicitWidth: Theme.controlHeight
    implicitHeight: Theme.controlHeight
    padding: 8
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    Accessible.name: accessibleLabel
    Accessible.description: accessibleLabel
    ToolTip.visible: hovered || activeFocus
    ToolTip.text: accessibleLabel
    ToolTip.delay: hovered ? 500 : 0
    contentItem: UiSymbol {
        symbol: control.symbol
        ink: Theme.toneColor(control.tone)
    }
    background: Rectangle {
        radius: Theme.radius
        color: control.checked ? Theme.toneSurface(control.tone) : (control.hovered ? Theme.hover : "transparent")
        border.color: control.checked || control.activeFocus ? Theme.toneColor(control.tone) : Theme.controlBorder
        border.width: control.checked || control.activeFocus ? 2 : 1
        Rectangle {
            anchors.fill: parent
            anchors.margins: -3
            radius: Theme.radius + 3
            color: "transparent"
            border.color: Theme.toneColor(control.tone)
            border.width: control.activeFocus ? 2 : 0
        }
    }
}
