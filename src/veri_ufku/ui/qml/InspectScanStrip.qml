import QtQuick
import QtQuick.Layouts

Flow {
    id: strip
    objectName: "inspectScanStrip"
    property int selectedBlock: 3
    signal cardChosen(int block)

    spacing: Theme.sm
    Layout.fillWidth: true

    readonly property var cards: {
        let q = dataView.qualityResult || ({})
        let findings = q.findings || []
        let missing = 0
        let missingDen = 0
        let dups = 0
        for (let i = 0; i < findings.length; i++) {
            let f = findings[i]
            if (f.code === "missing") {
                missing += f.count || 0
                missingDen = Math.max(missingDen, f.denominator || 0)
            }
            if (f.code === "duplicates_full")
                dups += f.count || 0
        }
        let content = dataView.dataContent || ({})
        let rows = dataView.totalRows || content.rows || 0
        let cols = content.columns || (dataView.datasetColumns || []).length
        let missingPct = missingDen > 0 ? ((missing / missingDen) * 100).toFixed(2).replace(".", ",") : "—"
        let outliers = (dataView.outlierCandidates.union_row_ids || []).length
        let special = (expertWorkspace.dataSpecialAdapters || []).filter(function(a) {
            return a.installed
        }).length
        let specialLabel = special > 0 ? (special + qsTr(" kurulu")) : qsTr("yok / kurulu değil")
        return [
            { block: 1, label: qsTr("Satır × sütun"), value: rows + " × " + cols, warn: false },
            { block: 3, label: qsTr("Eksik değer"), value: missingDen ? ("%" + missingPct) : qsTr("Tarama yok"), warn: missing > 0 },
            { block: 4, label: qsTr("Tam satır tekrarı"), value: q.dataset_version ? String(dups) : qsTr("Tarama yok"), warn: dups > 0 },
            { block: 4, label: qsTr("Aykırı aday"), value: outliers ? String(outliers) : qsTr("Hesaplanmadı"), warn: outliers > 0 },
            { block: 5, label: qsTr("Özel tür"), value: specialLabel, warn: false }
        ]
    }

    Repeater {
        model: strip.cards
        Rectangle {
            required property var modelData
            required property int index
            objectName: "inspectScanCard_" + (index + 1)
            width: Math.max(140, Math.min(200, (strip.width - 4 * Theme.sm) / 5))
            implicitHeight: cardCol.implicitHeight + 2 * Theme.sm
            radius: Theme.radius
            color: Theme.surface
            border.color: strip.selectedBlock === modelData.block ? Theme.controlBorder : Theme.border
            border.width: strip.selectedBlock === modelData.block ? 2 : 1
            ColumnLayout {
                id: cardCol
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.margins: Theme.sm
                spacing: 2
                UiLabel {
                    text: modelData.label
                    color: Theme.secondary
                    font.pixelSize: Theme.small
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                UiLabel {
                    text: modelData.value
                    font.bold: true
                    color: modelData.warn ? Theme.warning : Theme.text
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
            }
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    strip.selectedBlock = modelData.block
                    strip.cardChosen(modelData.block)
                }
            }
            Accessible.name: modelData.label + " " + modelData.value
            Accessible.role: Accessible.Button
        }
    }
}
