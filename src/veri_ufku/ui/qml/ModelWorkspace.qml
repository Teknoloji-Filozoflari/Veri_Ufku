import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    objectName: "modelWorkspace"
    property var catalogControls: null
    property int resultTab: 1
    spacing: Theme.sm
    Layout.fillWidth: true
    Layout.fillHeight: true
    signal helpRequested(var origin, string context)
    signal sectionRequested(int section)

    readonly property int selectedBlock: {
        if (root.catalogControls && root.catalogControls.selectedBlock !== undefined)
            return root.catalogControls.selectedBlock
        return 1
    }
    readonly property var entry: {
        let list = (root.catalogControls && root.catalogControls.schemaEntries) || []
        return list[Math.max(0, Math.min(list.length - 1, root.selectedBlock - 1))] || ({})
    }
    readonly property bool hasModel: !!(validation.summaryReport && validation.summaryReport.plan)
    readonly property var lastRun: validation.summaryReport || ({})

    function number(value) {
        return typeof value === "number" ? Number(value.toPrecision(6)) : value === null || value === undefined ? qsTr("sunulmuyor") : String(value)
    }
    function leakageText() {
        let text = (modelPaths.leakageText || "")
        if (text.length > 0)
            return text
        return qsTr("yok")
    }

    UiLabel {
        objectName: "modelWorkspaceTitle"
        text: (root.entry.index ? root.entry.index + " · " : "") + (root.entry.title || qsTr("Model"))
        font.pixelSize: Theme.heading
        font.bold: true
        Layout.fillWidth: true
        wrapMode: Text.Wrap
    }
    UiLabel {
        objectName: "modelWorkspaceSummary"
        text: root.entry.summary || ""
        color: Theme.secondary
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }

    Rectangle {
        objectName: "modelLayerStrip"
        Layout.fillWidth: true
        implicitHeight: layerRow.implicitHeight + Theme.sm * 2
        radius: Theme.radius
        color: Theme.cyanSurface
        border.color: Theme.border
        RowLayout {
            id: layerRow
            anchors.fill: parent
            anchors.margins: Theme.sm
            spacing: Theme.md
            UiLabel {
                objectName: "modelTrainN"
                text: qsTr("Eğitim: n=") + (root.lastRun.estimated_cost ? root.lastRun.estimated_cost.train_n : qsTr("atanmadı"))
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }
            UiLabel {
                objectName: "modelTestN"
                text: qsTr("Test: n=") + (root.lastRun.estimated_cost ? root.lastRun.estimated_cost.test_n : qsTr("held-out bu ekranda yok"))
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }
            UiLabel {
                objectName: "modelLeakageBadge"
                text: qsTr("Sızıntı: ") + root.leakageText()
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: (modelPaths.leakageText || "").length > 0 ? Theme.warning : Theme.text
            }
        }
    }

    // Değerlendirme protokolü: hedef/split/test planı. M-01, M-03, M-04 ve M-07'de görünür.
    ValidationProtocol {
        id: protocolSurface
        visible: root.selectedBlock === 1 || root.selectedBlock === 3 || root.selectedBlock === 4 || root.selectedBlock === 7
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }

    PreparationPanel {
        id: preparationSurface
        visible: root.selectedBlock === 1
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }

    ModelPathsPanel {
        visible: root.selectedBlock === 2
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
        onSectionRequested: function(section) { root.sectionRequested(section) }
    }

    RegressionPanel {
        visible: root.selectedBlock === 3
        Layout.fillWidth: true
        protocol: protocolSurface.spec()
        protocolBlocked: !!protocolSurface.protocolBlock
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }

    ClassificationPanel {
        visible: root.selectedBlock === 4
        Layout.fillWidth: true
        protocol: protocolSurface.spec()
        protocolBlocked: !!protocolSurface.protocolBlock
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }

    UnsupervisedPanel {
        visible: root.selectedBlock === 5
        Layout.fillWidth: true
        purpose: (preparation.report.spec || {}).purpose === "anomaly" ? "anomaly" : "clustering"
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }

    DimensionsPanel {
        visible: root.selectedBlock === 6
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }

    ValidationPanel {
        id: validationSurface
        visible: root.selectedBlock === 7
        Layout.fillWidth: true
        protocol: protocolSurface.spec()
        protocolBlocked: !!protocolSurface.protocolBlock
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }

    ExplanationPanel {
        visible: root.selectedBlock === 8
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }

    TimeSeriesPanel {
        visible: root.selectedBlock === 9
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }
    StreamPanel {
        visible: root.selectedBlock === 9
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }
    GraphPanel {
        visible: root.selectedBlock === 9
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }
    AudioPanel {
        visible: root.selectedBlock === 9
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }
    VisionPanel {
        visible: root.selectedBlock === 9
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }
    TextPanel {
        visible: root.selectedBlock === 9
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }

    NeuralPanel {
        visible: root.selectedBlock === 10
        Layout.fillWidth: true
        protocol: protocolSurface.spec()
        protocolBlocked: !!protocolSurface.protocolBlock
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }
    PatternPanel {
        visible: root.selectedBlock === 10
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }
    RecommendationPanel {
        visible: root.selectedBlock === 10
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }
    ScenarioPanel {
        visible: root.selectedBlock === 10
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }
    MonitoringPanel {
        visible: root.selectedBlock === 10
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }
    LifecyclePanel {
        visible: root.selectedBlock === 10
        Layout.fillWidth: true
        onRetrainRequested: {
            root.selectedBlock = 1
            protocolSurface.forceFocus()
        }
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }

    StateNotice {
        Layout.fillWidth: true
        kind: validation.errorText ? "error" : validation.busy ? "loading" : "info"
        heading: qsTr("Model durumu")
        detail: validation.errorText || validation.message
    }

    UiLabel {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        font.pixelSize: Theme.small
        text: qsTr("Model yeni veri sürümü üretmez; kaynak dosya değişmez. Eğitim ve değerlendirme sonuçları analysis/validation kayıtlarına yazılır.")
    }
    UiButton {
        objectName: "findingAddModel"
        text: qsTr("Bulgu defterine ekle")
        quiet: true
        Layout.fillWidth: true
        enabled: findings.available
        onClicked: findings.openFor("model")
    }
}
