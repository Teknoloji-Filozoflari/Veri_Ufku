import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    objectName: "statisticsCatalogPanel"
    signal helpRequested(var origin, string context)
    property int selectedBlock: 5
    property var touchedBlocks: ({})
    property bool assumptionsChecked: false
    spacing: Theme.md
    Layout.fillWidth: true

    readonly property var chipDefs: [
        { index: 1, title: qsTr("Dağılım ve normalilik") },
        { index: 2, title: qsTr("İlişki ölçüleri") },
        { index: 3, title: qsTr("Hipotez testi") },
        { index: 4, title: qsTr("Etki büyüklüğü ve belirsizlik") },
        { index: 5, title: qsTr("Test öneri kartı") },
        { index: 6, title: qsTr("Regresyon (çıkarım)") },
        { index: 7, title: qsTr("Sağlamlık ve deneme kaydı") },
        { index: 8, title: qsTr("İleri istatistik") }
    ]

    function statusColor(status) {
        return status === "done" ? Theme.learningTone : status === "pending" ? Theme.warning : Theme.muted
    }
    function statusLabel(status) {
        return status === "done" ? qsTr("Tamam") : status === "pending" ? qsTr("Karar bekliyor") : qsTr("Dokunulmamış")
    }
    function chipStatus(index) {
        if (index === 8)
            return "untouched"
        if (root.touchedBlocks[String(index)])
            return statistics.current || statistics.preflightCurrent ? "done" : "pending"
        if (index === 5 && (statistics.advice.question || "").length > 0)
            return "pending"
        if (index === 4 && statistics.analysisResult && statistics.analysisResult.primary)
            return "done"
        return "untouched"
    }
    function markTouched(index) {
        let next = Object.assign({}, root.touchedBlocks)
        next[String(index)] = true
        root.touchedBlocks = next
    }
    function selectBlock(index) {
        root.selectedBlock = index
        markTouched(index)
        stats.applyCatalogBlock(index)
    }

    function runPreflight() {
        markTouched(root.selectedBlock)
        stats.runPreflight()
    }
    function runFull() {
        markTouched(root.selectedBlock)
        stats.runFull()
    }
    function runSave() {
        markTouched(4)
        statistics.save()
    }
    function runReset() {
        root.assumptionsChecked = false
        stats.runReset()
    }
    function setAssumptions(checked) {
        root.assumptionsChecked = checked
        stats.setAssumptions(checked)
    }

    UiLabel {
        text: qsTr("İstatistik kataloğu")
        font.pixelSize: Theme.heading
        font.bold: true
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }

    ColumnLayout {
        objectName: "statisticsCatalogChips"
        Layout.fillWidth: true
        spacing: Theme.xs
        Repeater {
            model: root.chipDefs
            delegate: UiButton {
                required property var modelData
                objectName: "statisticsCatalogChip_" + modelData.index
                Layout.fillWidth: true
                multiline: true
                primary: root.selectedBlock === modelData.index
                text: modelData.index + ". " + modelData.title + " · " + root.statusLabel(root.chipStatus(modelData.index))
                onClicked: root.selectBlock(modelData.index)
                Rectangle {
                    width: 8; height: 8; radius: 4
                    anchors.right: parent.right
                    anchors.rightMargin: Theme.sm
                    anchors.verticalCenter: parent.verticalCenter
                    color: root.statusColor(root.chipStatus(modelData.index))
                }
            }
        }
    }

    UiLabel {
        objectName: "statisticsBlock1Note"
        visible: root.selectedBlock === 1
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        text: qsTr("Dağılım özeti önkontrol özetlerinden okunur. Shapiro-Wilk / resmi normalite testi bu sürümde desteklenmiyor. QQ/histogram için Görselleştir veya İncele kullanın; p uydurulmaz.")
    }
    UiLabel {
        objectName: "statisticsBlock6Note"
        visible: root.selectedBlock === 6
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        text: qsTr("Regresyon çıkarımı İstatistik → Modeller aracındadır (examineTool=7). Tahmin amaçlı modelleme Model bölümündedir.")
    }
    UiButton {
        objectName: "statisticsOpenModels"
        visible: root.selectedBlock === 6
        text: qsTr("Modeller aracını aç")
        tone: "violet"
        Layout.fillWidth: true
        onClicked: window.examineTool = 7
    }
    UiLabel {
        objectName: "statisticsBlock7Note"
        visible: root.selectedBlock === 7
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        text: qsTr("Bootstrap / permutation bu core analizde yok. Sağlamlık ve yeniden örnekleme İstatistik → Yeniden örnekleme aracındadır.")
    }
    UiButton {
        objectName: "statisticsOpenResampling"
        visible: root.selectedBlock === 7
        text: qsTr("Yeniden örnekleme aracını aç")
        tone: "violet"
        Layout.fillWidth: true
        onClicked: window.examineTool = 6
    }
    UiLabel {
        objectName: "statisticsUnsupportedNote"
        visible: root.selectedBlock === 8
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.warning
        text: qsTr("İleri istatistik (Bayes çıkarımı, nedensel analiz, sağkalım) bu sürümde desteklenmiyor (Faz40+). Sonuç uydurulmaz.")
    }

    StatisticsPanel {
        id: stats
        catalogMode: true
        selectedCatalogBlock: root.selectedBlock
        Layout.fillWidth: true
        visible: root.selectedBlock !== 8
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
        onAssumptionsChanged: function(checked) { root.assumptionsChecked = checked }
    }

    Component.onCompleted: {
        stats.applyCatalogBlock(root.selectedBlock)
    }
}
