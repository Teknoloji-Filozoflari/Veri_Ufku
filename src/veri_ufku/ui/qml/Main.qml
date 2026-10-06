import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    objectName: "mainWindow"
    width: 920
    height: 640
    minimumWidth: 680
    minimumHeight: 540
    visible: true
    title: "Veri_Ufku"
    onClosing: function(event) {
        if (bridge && !bridge.closed) {
            event.accepted = false
            bridge.shutdown()
        }
    }
    ScrollView {
        anchors.fill: parent
        anchors.margins: 28
        contentWidth: availableWidth
        ColumnLayout {
            width: parent.width
            spacing: 18
            Label { text: "Veri_Ufku"; font.pixelSize: 28; font.bold: true }
            Label {
                text: qsTr("Local desktop application — Phase 01")
                font.pixelSize: 18
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            Label {
                text: qsTr("Infrastructure tests are available. File import, analysis and project saving are not available yet.")
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            Frame {
                Layout.fillWidth: true
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 12
                    Label { text: qsTr("Task infrastructure test"); font.bold: true }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Button { objectName: "cpuButton"; text: qsTr("Run CPU test"); enabled: bridge && !bridge.active && !bridge.closing; onClicked: bridge.start("demo.cpu") }
                        Button { objectName: "ioButton"; text: qsTr("Run I/O test"); enabled: bridge && !bridge.active && !bridge.closing; onClicked: bridge.start("demo.io") }
                        Button { objectName: "unknownButton"; text: qsTr("Test unknown progress"); enabled: bridge && !bridge.active && !bridge.closing; onClicked: bridge.start("demo.unknown") }
                    }
                    Label { objectName: "stateLabel"; text: bridge ? bridge.stateText : qsTr("Unavailable"); font.pixelSize: 18 }
                    ProgressBar {
                        objectName: "jobProgress"
                        Layout.fillWidth: true
                        indeterminate: bridge && bridge.active && bridge.progress < 0
                        value: bridge && bridge.progress >= 0 ? bridge.progress : 0
                        visible: bridge && bridge.active
                    }
                    Label { text: bridge && bridge.jobId ? qsTr("Task ID:") + " " + bridge.jobId : ""; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                    Label { objectName: "resultLabel"; text: bridge ? bridge.resultText : ""; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    Label { objectName: "errorLabel"; text: startupError || (bridge ? bridge.errorText : ""); Layout.fillWidth: true; wrapMode: Text.WordWrap; color: "#a33b24" }
                    Button { objectName: "cancelButton"; text: qsTr("Cancel task"); enabled: bridge && bridge.active && !bridge.closing; onClicked: bridge.cancel() }
                }
            }
            Frame {
                Layout.fillWidth: true
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8
                    Label { text: qsTr("Verification tools"); font.bold: true }
                    Label { text: qsTr("Change the test configuration while a task is running to verify that old results are not applied."); wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Button { objectName: "contextButton"; text: qsTr("Change test configuration"); enabled: bridge && !bridge.closing; onClicked: bridge.changeConfiguration() }
                        Button { objectName: "failureButton"; text: qsTr("Test error transfer"); enabled: bridge && !bridge.active && !bridge.closing; onClicked: bridge.start("demo.failure") }
                    }
                    Label { text: qsTr("Configuration revision:") + " " + (bridge ? bridge.revision : 0) }
                }
            }
            Button { objectName: "closeButton"; text: qsTr("Close"); onClicked: window.close() }
        }
    }
}
