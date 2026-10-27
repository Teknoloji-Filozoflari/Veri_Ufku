import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: rail
    objectName: "moduleRail"
    property int currentSection: 1
    property string currentKey: "veri"
    property bool modelInstalled: true
    property bool compact: false
    signal moduleChosen(int section, string key, var origin)

    spacing: Theme.xs

    UiLabel {
        visible: !rail.compact
        text: qsTr("ARAÇLAR")
        color: Theme.muted
        font.pixelSize: Theme.small
        font.letterSpacing: 1
        Layout.leftMargin: Theme.md
        Layout.topMargin: Theme.sm
        Layout.bottomMargin: Theme.xs
    }

    Repeater {
        model: [
            { key: "veri", section: 1, symbol: "table", tone: "cyan", text: qsTr("Veri") },
            { key: "incele", section: 1, symbol: "compare", tone: "cyan", text: qsTr("İncele") },
            { key: "gorsellestir", section: 3, symbol: "chart", tone: "cyan", text: qsTr("Görselleştir") },
            { key: "hazirla", section: 2, symbol: "prepare", tone: "violet", text: qsTr("Hazırla") },
            { key: "istatistik", section: 4, symbol: "compare", tone: "violet", text: qsTr("İstatistik") },
            { key: "model", section: 5, symbol: "model", tone: "violet", text: qsTr("Model") },
            { key: "raporla", section: 6, symbol: "report", tone: "warm", text: qsTr("Raporla") }
        ]
        UiNavigationButton {
            id: moduleButton
            required property int index
            required property var modelData
            objectName: ["moduleVeri", "moduleIncele", "moduleGrafik", "moduleHazirla", "moduleIstatistik", "moduleModel", "moduleRapor"][index]
            visible: modelData.key !== "model" || rail.modelInstalled
            compact: rail.compact
            Layout.fillWidth: true
            symbol: modelData.symbol
            tone: modelData.tone
            symbolColor: modelData.section === 6 ? Theme.reportTone : Theme.toneColor(modelData.tone)
            text: modelData.text
            checked: rail.currentKey === modelData.key
            Accessible.name: modelData.text
            Accessible.description: modelData.text
            onClicked: rail.moduleChosen(modelData.section, modelData.key, this)
            Keys.onDownPressed: nextItemInFocusChain().forceActiveFocus()
            Keys.onUpPressed: nextItemInFocusChain(false).forceActiveFocus()
        }
    }
}
