import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    objectName: "reportWorkspace"
    property var catalogControls: null
    property int previewTab: 1
    spacing: Theme.sm
    Layout.fillWidth: true
    Layout.fillHeight: true
    signal helpRequested(var origin, string context)

    readonly property string previewText: reportBuilder.preview || ""
    readonly property bool hasResult: !!(reportBuilder.result && reportBuilder.result.status)
    readonly property bool stale: (reportBuilder.freshnessText || "").indexOf("STALE") === 0
    readonly property int selectedCount: catalogControls && catalogControls.selectedCount !== undefined ? catalogControls.selectedCount : 0

    UiLabel {
        text: qsTr("Rapor önizleme")
        font.pixelSize: Theme.heading
        font.bold: true
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }

    Flow {
        objectName: "reportPreviewTabs"
        Layout.fillWidth: true
        spacing: Theme.sm
        UiButton {
            objectName: "reportPreviewTab_1"
            text: qsTr("Önizleme")
            primary: root.previewTab === 1
            onClicked: root.previewTab = 1
        }
        UiButton {
            objectName: "reportPreviewTab_2"
            text: "HTML"
            primary: root.previewTab === 2
            onClicked: root.previewTab = 2
        }
        UiButton {
            objectName: "reportPreviewTab_3"
            text: "PDF"
            primary: root.previewTab === 3
            onClicked: root.previewTab = 3
        }
    }

    Rectangle {
        objectName: "reportStatusStrip"
        Layout.fillWidth: true
        implicitHeight: statusRow.implicitHeight + Theme.sm * 2
        radius: Theme.radius
        color: root.stale ? Theme.violetSurface : Theme.cyanSurface
        border.color: Theme.border
        RowLayout {
            id: statusRow
            anchors.fill: parent
            anchors.margins: Theme.sm
            spacing: Theme.md
            UiLabel {
                objectName: "reportSelectedCount"
                text: qsTr("Seçili bölüm: ") + root.selectedCount
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }
            UiLabel {
                objectName: "reportFreshness"
                text: reportBuilder.freshnessText || ""
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: root.stale ? Theme.warning : Theme.text
            }
        }
    }

    Frame {
        objectName: "reportCanvasFrame"
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 160
        padding: Theme.md
        background: Rectangle { color: Theme.raised; border.color: Theme.border; radius: Theme.radius }
        ColumnLayout {
            anchors.fill: parent
            spacing: Theme.sm
            UiLabel {
                visible: root.previewTab === 1
                objectName: "reportPreviewHint"
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
                text: root.hasResult
                    ? qsTr("Birleştirilmiş rapor önizlemesi (yeniden hesaplama yok).")
                    : qsTr("Sağdan bölüm seçin, oluşturun; önizleme kayıtlı bulgulardan dolar. DOCX/LLM yok.")
            }
            UiLabel {
                visible: root.previewTab === 2
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
                text: qsTr("HTML: oluşturulan raporun metin/HTML özeti burada; dosya için HTML dışa aktar.")
            }
            UiLabel {
                visible: root.previewTab === 3
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
                text: qsTr("PDF: yerel A4 Türkçe font; dosya için PDF dışa aktar. Düzen HTML ile birebir aynı değildir.")
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: availableWidth
                UiLabel {
                    objectName: "reportWorkspacePreview"
                    width: parent.availableWidth
                    text: root.previewText.length > 0 ? root.previewText : qsTr("Önizleme boş.")
                    textFormat: Text.PlainText
                    wrapMode: Text.WrapAnywhere
                    font.pixelSize: Theme.small
                }
            }
        }
    }

    UiLabel {
        objectName: "reportLimitationsBanner"
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.warning
        font.pixelSize: Theme.small
        text: qsTr("Bu rapor analiz/modeli yeniden hesaplamaz. ") + ((reportBuilder.limitations && reportBuilder.limitations.length) ? reportBuilder.limitations[0] : "")
    }

    StateNotice {
        Layout.fillWidth: true
        kind: reportBuilder.errorText ? "error" : reportBuilder.busy ? "loading" : "info"
        heading: qsTr("Rapor durumu")
        detail: reportBuilder.errorText || (reportBuilder.busy ? qsTr("Rapor işleniyor…") : qsTr("Hazır"))
    }
}
