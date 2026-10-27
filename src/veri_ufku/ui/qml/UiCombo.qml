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
    palette.text: Theme.text
    palette.buttonText: Theme.text
    palette.window: Theme.surface
    palette.windowText: Theme.text
    palette.highlightedText: Theme.text
    palette.highlight: Theme.hover
    palette.base: Theme.field
    palette.button: Theme.field
    ToolTip.visible: hovered && displayText.length > 35
    ToolTip.text: displayText
    ToolTip.delay: 500
    onActiveFocusChanged: if (activeFocus) Qt.callLater(function() { FocusScroll.reveal(control) })
    contentItem: Text {
        leftPadding: control.leftPadding
        rightPadding: control.rightPadding
        text: control.displayText
        font: control.font
        color: Theme.text
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    delegate: ItemDelegate {
        required property var model
        required property int index
        width: ListView.view ? ListView.view.width : control.width
        text: model[control.textRole]
        font: control.font
        highlighted: control.highlightedIndex === index
        hoverEnabled: control.hoverEnabled
        palette.text: Theme.text
        palette.highlightedText: Theme.text
        palette.highlight: Theme.hover
        palette.window: Theme.surface
        background: Rectangle {
            color: parent.highlighted || parent.hovered ? Theme.hover : Theme.surface
        }
    }
    popup: Popup {
        y: control.height
        width: control.width
        height: Math.min(contentItem.implicitHeight + 2, control.Window.height - 12)
        padding: 1
        palette.text: Theme.text
        palette.window: Theme.surface
        palette.highlightedText: Theme.text
        palette.highlight: Theme.hover
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.delegateModel
            currentIndex: control.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }
        background: Rectangle {
            color: Theme.surface
            border.color: Theme.controlBorder
            radius: Theme.radius
        }
    }
    background: Rectangle {
        color: Theme.field
        radius: Theme.radius
        border.color: control.activeFocus ? (control.tone ? Theme.toneColor(control.tone) : control.palette.highlight) : Theme.controlBorder
        border.width: control.activeFocus ? 2 : 1
    }
}
