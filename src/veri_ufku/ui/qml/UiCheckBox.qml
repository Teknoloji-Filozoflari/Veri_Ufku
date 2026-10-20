import QtQuick
import QtQuick.Controls
import "FocusScroll.js" as FocusScroll

CheckBox {
    id: control
    implicitHeight: Math.max(Theme.controlHeight, contentItem.implicitHeight + topPadding + bottomPadding)
    spacing: Theme.sm
    padding: 4
    indicator: Rectangle {
        objectName: "ovalCheckIndicator"
        implicitWidth: 32
        implicitHeight: 22
        x: control.leftPadding
        y: (control.height - height) / 2
        radius: height / 2
        color: control.checked ? Theme.toneColor("violet") : (control.hovered ? Theme.hover : Theme.background)
        opacity: control.enabled ? 1 : 0.45
        border.color: control.activeFocus ? Theme.toneColor("mint") : control.checked ? Theme.toneColor("violet") : Theme.controlBorder
        border.width: control.activeFocus ? 2 : 1
        Rectangle {
            width: 14; height: 14; radius: 7
            anchors.verticalCenter: parent.verticalCenter
            x: control.checked ? parent.width - width - 4 : 4
            color: control.checked ? Theme.accentText : Theme.secondary
            Behavior on x { NumberAnimation { duration: 100 } }
        }
    }
    Accessible.name: text
    onActiveFocusChanged: if (activeFocus) Qt.callLater(function() { FocusScroll.reveal(control) })
    contentItem: UiLabel {
        text: control.text
        leftPadding: control.indicator.width + control.spacing
        verticalAlignment: Text.AlignVCenter
        wrapMode: Text.WordWrap
        color: control.enabled ? Theme.text : Theme.muted
        font.pixelSize: Theme.body
    }
}
