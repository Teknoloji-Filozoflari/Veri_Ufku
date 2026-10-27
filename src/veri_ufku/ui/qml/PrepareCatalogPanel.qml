import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    objectName: "prepareCatalogPanel"
    signal helpRequested(var origin, string context)
    property int selectedBlock: 1
    property int prepareScopeMode: 0
    property var touchedBlocks: ({})
    spacing: Theme.md
    Layout.fillWidth: true

    readonly property var chipDefs: [
        { index: 1, title: qsTr("Sütun temizliği") },
        { index: 2, title: qsTr("Aykırı") },
        { index: 3, title: qsTr("Kalite") },
        { index: 4, title: qsTr("Yeni sütun") },
        { index: 5, title: qsTr("Birleştirme/şekil") },
        { index: 6, title: qsTr("Özel tür") },
        { index: 7, title: qsTr("Öğrenilen") },
        { index: 8, title: qsTr("Diğer") },
        { index: 9, title: qsTr("Uygunluk") },
        { index: 10, title: qsTr("Uygulama") }
    ]

    readonly property var learnedKinds: ["missing_rows", "missing_columns", "dedup", "ordered_fill", "outlier"]

    function statusColor(status) {
        return status === "done" ? Theme.learningTone : status === "pending" ? Theme.warning : Theme.muted
    }
    function statusLabel(status) {
        return status === "done" ? qsTr("Tamam") : status === "pending" ? qsTr("Karar bekliyor") : qsTr("Dokunulmamış")
    }
    function chipStatus(index) {
        if (root.touchedBlocks[String(index)])
            return "done"
        if (operations.hasInspectDraft && draftBlockFor(operations.inspectDraft) === index)
            return "pending"
        if (index === 9 && operations.leakageHistory.length > 0)
            return "pending"
        if (index === 10 && operations.history.length > 1)
            return "pending"
        return "untouched"
    }
    function markTouched(index) {
        let next = Object.assign({}, root.touchedBlocks)
        next[String(index)] = true
        root.touchedBlocks = next
    }
    function draftBlockFor(draft) {
        if (!draft || !draft.kind)
            return 1
        let k = draft.kind
        if (k === "outlier")
            return 2
        if (k === "dedup" || k === "missing_rows" || k === "missing_columns")
            return 3
        if (k === "fill") {
            let m = (draft.method || draft.parameters && draft.parameters.method) || "median"
            return m === "constant" ? 8 : 3
        }
        if (k === "trim" || k === "convert" || k === "map_categories")
            return 1
        if (k === "ordered_fill")
            return 7
        return 1
    }
    function selectBlock(index) {
        root.selectedBlock = index
        markTouched(index)
        ops.applyPrepareBlock(index)
    }
    function isLearnedCleaning() {
        if (ops.kindIndex !== 3)
            return false
        let k = ops.cleaningKind
        if (root.learnedKinds.indexOf(k) >= 0)
            return true
        if (k === "fill")
            return ops.cleaningFillMethodIndex !== 0
        return false
    }
    readonly property string learnedNote: {
        if (!operations.previewResult || !operations.previewResult.spec)
            return ""
        let spec = operations.previewResult.spec || ({})
        let scope = spec.learned_scope || "none"
        if (scope !== "dataset")
            return ""
        let method = (spec.parameters || {}).method || spec.kind || ""
        let impact = operations.previewResult.impact || ({})
        return qsTr("Öğrenilen notu: ") + method
              + qsTr(" · learned_scope=dataset (tam veri)")
              + qsTr(" · etkilenen satır ") + (impact.changed_rows || 0)
              + qsTr(" · yeni null ") + (impact.new_nulls || 0)
              + qsTr(". Model öncesi sızıntı incelemesi gerekir.")
    }
    readonly property bool showMod2Warning: root.prepareScopeMode === 1 && root.isLearnedCleaning()

    function runPreview() {
        markTouched(root.selectedBlock)
        ops.runPreview()
    }
    function runApply() {
        operations.setPrepareScopeMode(root.prepareScopeMode === 1 ? "mod2" : "mod1")
        markTouched(10)
        ops.runApply()
    }
    function runCancel() {
        ops.runCancel()
    }

    UiLabel {
        text: qsTr("Hazırla kataloğu")
        font.pixelSize: Theme.heading
        font.bold: true
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }

    Frame {
        objectName: "inspectDraftFrame"
        visible: operations.hasInspectDraft
        Layout.fillWidth: true
        padding: Theme.md
        background: Rectangle { color: Theme.violetSurface; border.color: Theme.border; radius: Theme.radius }
        ColumnLayout {
            width: parent.width
            spacing: Theme.sm
            UiLabel {
                text: qsTr("Gelen taslaklar — İncele’den")
                font.bold: true
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }
            UiLabel {
                objectName: "inspectDraftOrigin"
                text: (operations.inspectDraft.origin || "") + "\n" + qsTr("Gerekçe: ") + (operations.inspectDraft.rationale || "")
                      + "\n" + qsTr("Beklenen etki: ") + (operations.inspectDraft.expected_impact || "")
                      + "\n" + qsTr("Taslak veri sürümü üretmez; Önizle → Uygula gerekir.")
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
            }
            Flow {
                Layout.fillWidth: true
                spacing: Theme.sm
                UiButton {
                    objectName: "inspectDraftAccept"
                    text: qsTr("Taslağı aç")
                    tone: "violet"
                    primary: true
                    onClicked: {
                        let b = root.draftBlockFor(operations.inspectDraft)
                        root.selectBlock(b)
                        ops.applyInspectDraft()
                    }
                }
                UiButton {
                    objectName: "inspectDraftClear"
                    text: qsTr("Taslağı reddet")
                    quiet: true
                    onClicked: operations.clearInspectDraft()
                }
            }
        }
    }

    ColumnLayout {
        objectName: "prepareCatalogChips"
        Layout.fillWidth: true
        spacing: Theme.xs
        Repeater {
            model: root.chipDefs
            delegate: UiButton {
                required property var modelData
                objectName: "prepareCatalogChip_" + modelData.index
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

    Frame {
        objectName: "prepareScopeMode"
        Layout.fillWidth: true
        padding: Theme.md
        background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius }
        ColumnLayout {
            width: parent.width
            spacing: Theme.sm
            UiLabel { text: qsTr("Kapsam modu"); font.bold: true; Layout.fillWidth: true }
            UiCombo {
                id: scopeMode
                objectName: "prepareScopeModeCombo"
                accessibleLabel: qsTr("Kapsam modu")
                Layout.fillWidth: true
                model: [qsTr("Mod 1 — veri kümesi öğrenimi (varsayılan)"), qsTr("Mod 2 — eğitim-katı uyarısı (uygulama yok)")]
                currentIndex: root.prepareScopeMode
                onActivated: root.prepareScopeMode = currentIndex
            }
            UiLabel {
                objectName: "prepareMod2Warning"
                visible: root.showMod2Warning
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Theme.warning
                text: qsTr("Eğitim-katı öğrenimi Model/Preparation training_fold sözleşmesine bağlanır; bu ekranda train-only uygulama yok. Apply yine mevcut cleaning yoludur; leakage bayrağı korunur.")
            }
            UiLabel {
                visible: root.selectedBlock === 9 || operations.leakageHistory.length > 0
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: qsTr("Sızıntı incelemesi gereken işlem: ") + operations.leakageHistory.length
            }
        }
    }

    UiLabel {
        objectName: "prepareLearnedNote"
        visible: root.learnedNote.length > 0 && (root.selectedBlock === 7 || root.isLearnedCleaning())
        text: root.learnedNote
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
    }

    UiLabel {
        objectName: "prepareSpecialTypeNote"
        visible: root.selectedBlock === 6
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        text: qsTr("Özel tür / sütun rolü bu sürümde Veri ve İncele metadata ile yönetilir; Hazırla’da yok.")
    }

    OperationsPanel {
        id: ops
        objectName: "operationsPanel"
        prepareShell: true
        selectedPrepareBlock: root.selectedBlock
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }

    Connections {
        target: operations
        function onChanged() {
            if (operations.hasInspectDraft && root.selectedBlock)
                Qt.callLater(function() {
                    // draft frame visible; user confirms via Taslağı aç
                })
        }
    }

    Component.onCompleted: {
        if (operations.hasInspectDraft) {
            let b = root.draftBlockFor(operations.inspectDraft)
            root.selectedBlock = b
        }
        ops.applyPrepareBlock(root.selectedBlock)
    }
}
