import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

UiButton {
    id: control
    property string symbol: "home"
    property bool compact: false
    property color symbolColor: Theme.secondary
    implicitHeight: Math.max(44, contentItem.implicitHeight + 24)
    implicitWidth: 160
    padding: 12
    quiet: true
    Layout.maximumWidth: -1
    ToolTip.visible: compact && (hovered || activeFocus)
    ToolTip.text: text
    ToolTip.delay: hovered ? 450 : 0
    contentItem: RowLayout {
        spacing: 12
        UiSymbol {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 20
            Layout.preferredHeight: 20
            symbol: control.symbol
            ink: control.checked ? control.toneColor : control.symbolColor
        }
        UiLabel {
            visible: !control.compact
            objectName: "navigationLabel"
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            text: control.text
            color: control.checked ? control.toneColor : Theme.text
            font.pixelSize: Theme.body
            font.bold: control.checked
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.Wrap
        }
    }
    background: Rectangle {
        radius: Theme.radius
        color: control.checked ? control.toneSurface : (control.hovered ? Theme.hover : "transparent")
        border.color: control.activeFocus ? control.toneColor : (control.checked ? control.toneSurface : Theme.border)
        border.width: control.activeFocus ? 2 : (control.checked ? 1 : 0)
        Rectangle {
            x: 0
            y: 10
            width: 3
            height: parent.height - 20
            radius: 1.5
            visible: control.checked
            color: control.toneColor
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -3
            radius: Theme.radius + 3
            color: "transparent"
            border.color: control.toneColor
            border.width: control.activeFocus ? 2 : 0
        }
    }
}
