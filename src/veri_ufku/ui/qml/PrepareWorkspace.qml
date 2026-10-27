import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    objectName: "prepareWorkspace"
    property var catalogControls: null
    property string viewingVersionId: ""
    spacing: Theme.sm
    Layout.fillWidth: true
    Layout.fillHeight: true
    signal helpRequested(var origin, string context)

    readonly property var impact: (operations.previewResult && operations.previewResult.impact) ? operations.previewResult.impact : ({})
    readonly property bool hasPreview: impact !== undefined && impact.before_rows !== undefined
    readonly property string scopeLabel: {
        if (!root.hasPreview)
            return qsTr("önizleme yok")
        let s = impact.scope || "full"
        return ({ full: qsTr("tam veri"), view: qsTr("görünüm"), sample: qsTr("örneklem") })[s] || s
    }

    function shortId(id) {
        if (!id)
            return "—"
        let t = String(id)
        return t.length > 8 ? t.slice(-8) : t
    }

    function runPreview() {
        if (root.catalogControls && root.catalogControls.runPreview)
            root.catalogControls.runPreview()
    }
    function runApply() {
        if (root.catalogControls && root.catalogControls.runApply)
            root.catalogControls.runApply()
    }
    function runCancel() {
        if (root.catalogControls && root.catalogControls.runCancel)
            root.catalogControls.runCancel()
    }

    // --- Etki rozetleri ---
    Flow {
        id: badges
        objectName: "prepareImpactBadges"
        Layout.fillWidth: true
        spacing: Theme.sm
        readonly property var items: root.hasPreview ? [
            { key: "rows", text: qsTr("etkilenen satır ") + (impact.changed_rows || 0) },
            { key: "nulls", text: qsTr("yeni null ") + (impact.new_nulls || 0) },
            { key: "ver", text: qsTr("sürüm ") + root.shortId(dataView.dataContent.version) + " → " + qsTr("önizleme") },
            { key: "scope", text: qsTr("kapsam ") + root.scopeLabel }
        ] : [
            { key: "idle", text: qsTr("önizleme yok — sürüm yazılmaz") }
        ]
        Repeater {
            model: badges.items
            delegate: Rectangle {
                required property var modelData
                radius: Theme.radius
                color: Theme.violetSurface
                border.color: Theme.border
                implicitHeight: 28 * Theme.scale
                implicitWidth: badgeLabel.implicitWidth + 2 * Theme.md
                UiLabel {
                    id: badgeLabel
                    anchors.centerIn: parent
                    text: modelData.text
                    font.pixelSize: Theme.small
                }
            }
        }
    }

    UiLabel {
        objectName: "prepareImpactDetail"
        visible: root.hasPreview
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        text: qsTr("Tam veri: ") + (impact.before_rows || 0) + " → " + (impact.after_rows || 0) + qsTr(" satır; ")
              + (impact.before_columns || 0) + " → " + (impact.after_columns || 0) + qsTr(" sütun. Çıkarılan: ")
              + (impact.removed_rows || 0) + qsTr("; değişen hücre: ") + (impact.changed_cells || 0) + "."
    }

    // --- Sürüm zinciri (salt okunur bakış; undo değil) ---
    ColumnLayout {
        objectName: "prepareVersionChain"
        Layout.fillWidth: true
        spacing: Theme.xs
        UiLabel { text: qsTr("Sürüm zinciri"); font.bold: true; Layout.fillWidth: true }
        UiLabel {
            text: qsTr("Tıklayınca salt okunur bakış. Geri al ayrı düğmedir; zincir silinmez.")
            color: Theme.secondary
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            font.pixelSize: Theme.small
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.xs
            Repeater {
                model: operations.history
                delegate: RowLayout {
                    required property var modelData
                    required property int index
                    spacing: 2
                    UiLabel {
                        visible: index > 0
                        text: "→"
                        color: Theme.muted
                    }
                    UiButton {
                        objectName: "prepareVersionChip_" + index
                        text: (modelData.current ? "● " : "") + "v…" + root.shortId(modelData.id)
                              + (modelData.current ? qsTr(" (aktif)") : "")
                        quiet: !modelData.current
                        enabled: true
                        onClicked: {
                            // Salt okunur etiket: aktif sürümü değiştirmez (undo/checkout değil).
                            root.viewingVersionId = modelData.id || ""
                        }
                    }
                }
            }
            UiLabel {
                visible: root.hasPreview
                text: "→ " + qsTr("önizleme")
                color: Theme.prepareTone
                font.bold: true
            }
        }
        UiLabel {
            objectName: "prepareVersionViewNote"
            visible: root.viewingVersionId.length > 0
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.secondary
            font.pixelSize: Theme.small
            text: qsTr("Salt okunur bakış: v…") + root.shortId(root.viewingVersionId)
                  + qsTr(" — aktif sürüm değişmedi. Dönmek için Uygulama → Geri al.")
        }
    }

    // --- Önce / Sonra ---
    RowLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: Theme.md
        OperationTable {
            objectName: "prepareBeforeTable"
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: qsTr("Önce")
            tableModel: operations.beforeModel
        }
        OperationTable {
            objectName: "prepareAfterTable"
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: qsTr("Sonra")
            tableModel: operations.afterModel
        }
    }

    UiLabel {
        text: operations.message + " · " + ({
            idle: qsTr("Hazır"),
            running: qsTr("Hesaplanıyor"),
            previewed: qsTr("Önizleme hazır"),
            publishing: qsTr("Kaydediliyor"),
            succeeded: qsTr("Tamamlandı"),
            failed: qsTr("Hata"),
            canceled: qsTr("İptal edildi"),
            cancel_requested: qsTr("İptal bekleniyor")
        }[operations.state] || operations.state)
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        Accessible.role: Accessible.StaticText
    }
    UiLabel {
        text: operations.errorText
        visible: text.length > 0
        color: Theme.warning
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }

    // --- Alt eylemler ---
    Flow {
        Layout.fillWidth: true
        spacing: Theme.sm
        UiButton {
            tone: "violet"
            objectName: "operationCancel"
            text: qsTr("İptal")
            enabled: operations.busy && operations.state !== "publishing"
            onClicked: root.runCancel()
        }
        UiButton {
            tone: "violet"
            objectName: "operationPreview"
            text: qsTr("Önizle")
            enabled: !projects.busy && !projects.readOnly && dataView.datasets.length > 0 && !operations.busy
            primary: !operations.canApply
            onClicked: root.runPreview()
        }
        UiButton {
            tone: "violet"
            objectName: "operationApply"
            text: qsTr("Uygula ve kaydet")
            enabled: operations.canApply
            primary: true
            onClicked: root.runApply()
        }
    }
}
