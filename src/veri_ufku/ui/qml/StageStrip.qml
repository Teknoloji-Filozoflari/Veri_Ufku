import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "UxStages.js" as UxStages

ColumnLayout {
    id: strip
    objectName: "stageStrip"
    property int currentStage: 0
    property bool compact: false
    signal stageChosen(int index, var origin)

    spacing: Theme.xs

    UiLabel {
        visible: !strip.compact
        text: qsTr("AŞAMALAR")
        color: Theme.muted
        font.pixelSize: Theme.small
        font.letterSpacing: 1
        Layout.leftMargin: Theme.md
        Layout.topMargin: Theme.sm
        Layout.bottomMargin: Theme.xs
    }

    Repeater {
        model: UxStages.stages
        UiNavigationButton {
            id: stageButton
            required property int index
            required property var modelData
            objectName: "uxStage" + index
            compact: strip.compact
            Layout.fillWidth: true
            symbol: modelData.symbol
            tone: modelData.tone
            text: strip.compact ? modelData.shortTitle : (index + ". " + modelData.shortTitle)
            checked: strip.currentStage === index
            Accessible.name: modelData.title
            Accessible.description: modelData.title
            onClicked: strip.stageChosen(index, this)
            Keys.onDownPressed: nextItemInFocusChain().forceActiveFocus()
            Keys.onUpPressed: nextItemInFocusChain(false).forceActiveFocus()
        }
    }
}
