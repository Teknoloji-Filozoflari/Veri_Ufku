import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: drawer
    objectName: "findingDrawer"
    property bool expanded: false
    property string stage: findings.currentStage
    signal closeRequested()

    color: Theme.chrome
    border.color: Theme.border
    border.width: 0
    height: drawer.expanded ? Math.min(360, parent ? parent.height * 0.42 : 360) : 44 * Theme.scale
    visible: height > 0
    clip: true

    Rectangle {
        anchors.top: parent.top
        width: parent.width
        height: 1
        color: Theme.border
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.sm

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: Theme.sm
            spacing: Theme.sm
            UiButton {
                objectName: "findingDrawerToggle"
                quiet: true
                glyph: drawer.expanded ? "chevron-down" : "chevron-up"
                text: qsTr("Bulgu defteri") + " · " + findings.summaryText
                Accessible.name: qsTr("Bulgu defterini aç/kapat")
                onClicked: drawer.expanded = !drawer.expanded
            }
            Item { Layout.fillWidth: true }
            UiLabel {
                objectName: "findingDrawerStaleCount"
                visible: findings.staleCount > 0
                text: qsTr("%1 bulgu güncel değil").arg(findings.staleCount)
                color: Theme.warning
                font.pixelSize: Theme.small
            }
            UiIconButton {
                objectName: "findingDrawerClose"
                symbol: "close"
                accessibleLabel: qsTr("Bulgu defterini kapat")
                onClicked: {
                    drawer.expanded = false
                    drawer.closeRequested()
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: drawer.expanded
            spacing: Theme.sm

            UiLabel {
                objectName: "findingDrawerHint"
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
                font.pixelSize: Theme.small
                text: qsTr("Her aşama bulgu ekleyebilir. Sonuç kayıtlı çalışmadan okunur; veri sürümü değişirse bulgu \"güncel değil\" olarak işaretlenir.")
            }

            ListView {
                id: findingList
                objectName: "findingDrawerList"
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: findings.findings
                spacing: Theme.sm
                delegate: Rectangle {
                    required property var modelData
                    objectName: "findingRow_" + modelData.id
                    width: findingList.width
                    implicitHeight: findingBody.implicitHeight + 2 * Theme.sm
                    radius: Theme.radius
                    color: Theme.surface
                    border.color: modelData.stale ? Theme.warning : Theme.border
                    border.width: 1
                    ColumnLayout {
                        id: findingBody
                        anchors.fill: parent
                        anchors.margins: Theme.sm
                        spacing: 2
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.sm
                            UiLabel {
                                text: modelData.stage_label
                                color: Theme.dataTone
                                font.bold: true
                                font.pixelSize: Theme.small
                            }
                            UiLabel {
                                objectName: "findingStaleBadge"
                                visible: modelData.stale
                                text: qsTr("Güncel değil")
                                color: Theme.warning
                                font.pixelSize: Theme.small
                            }
                            Item { Layout.fillWidth: true }
                            UiButton {
                                objectName: "findingRemove"
                                quiet: true
                                text: qsTr("Sil")
                                Accessible.name: qsTr("Bulguyu sil") + ": " + modelData.question
                                onClicked: findings.remove(modelData.id)
                            }
                        }
                        UiLabel {
                            objectName: "findingQuestion"
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            font.bold: true
                            text: modelData.question
                        }
                        UiLabel {
                            objectName: "findingMethod"
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            color: Theme.secondary
                            font.pixelSize: Theme.small
                            text: qsTr("Yöntem: ") + modelData.method
                        }
                        UiLabel {
                            objectName: "findingResult"
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            font.pixelSize: Theme.small
                            text: qsTr("Sonuç: ") + modelData.result
                        }
                        UiLabel {
                            objectName: "findingInterpretation"
                            visible: modelData.interpretation.length > 0
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            color: Theme.secondary
                            font.pixelSize: Theme.small
                            text: qsTr("Yorum: ") + modelData.interpretation
                        }
                        UiLabel {
                            objectName: "findingDecision"
                            visible: modelData.decision.length > 0
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            color: Theme.secondary
                            font.pixelSize: Theme.small
                            text: qsTr("Seçim gerekçesi: ") + modelData.decision
                        }
                        UiLabel {
                            visible: modelData.stale && modelData.stale_reason.length > 0
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            color: Theme.warning
                            font.pixelSize: Theme.small
                            text: modelData.stale_reason
                        }
                    }
                }
            }

            UiLabel {
                objectName: "findingEmptyNote"
                visible: findings.count === 0
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
                font.pixelSize: Theme.small
                text: qsTr("Henüz bulgu yok. Bir aşamanın sonucundan \"Bulgu defterine ekle\" ile başlayın.")
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.sm
                UiCombo {
                    id: stagePicker
                    objectName: "findingStagePicker"
                    Layout.preferredWidth: 160 * Theme.scale
                    model: findings.stages
                    textRole: "label"
                    valueRole: "id"
                    accessibleLabel: qsTr("Bulgu aşaması")
                    currentIndex: 0
                    onActivated: drawer.stage = currentValue
                }
                UiTextField {
                    id: questionField
                    objectName: "findingQuestionInput"
                    Layout.fillWidth: true
                    placeholderText: qsTr("Soru")
                    Accessible.name: qsTr("Bulgu sorusu")
                }
                UiTextField {
                    id: methodField
                    objectName: "findingMethodInput"
                    Layout.fillWidth: true
                    placeholderText: qsTr("Yöntem")
                    Accessible.name: qsTr("Bulgu yöntemi")
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.sm
                UiTextArea {
                    id: interpretationField
                    objectName: "findingInterpretationInput"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 54 * Theme.scale
                    placeholderText: qsTr("Yorum")
                    Accessible.name: qsTr("Bulgu yorumu")
                }
                UiTextArea {
                    id: decisionField
                    objectName: "findingDecisionInput"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 54 * Theme.scale
                    placeholderText: qsTr("Seçim gerekçesi")
                    Accessible.name: qsTr("Bulgu seçim gerekçesi")
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.sm
                UiLabel {
                    objectName: "findingResultPreview"
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Theme.secondary
                    font.pixelSize: Theme.small
                    text: qsTr("Sonuç (kayıtlı çalışmadan): ") + findings.preview(drawer.stage)
                }
                UiButton {
                    objectName: "findingAdd"
                    text: qsTr("Bulgu defterine ekle")
                    tone: "mint"
                    primary: true
                    enabled: findings.available && questionField.text.trim().length > 0 && methodField.text.trim().length > 0
                    onClicked: {
                        if (findings.add(drawer.stage, questionField.text, methodField.text, interpretationField.text, decisionField.text)) {
                            questionField.text = ""
                            methodField.text = ""
                            interpretationField.text = ""
                            decisionField.text = ""
                        }
                    }
                }
            }
            UiLabel {
                objectName: "findingDrawerError"
                visible: (findings.errorText || "").length > 0
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.warning
                font.pixelSize: Theme.small
                text: findings.errorText || ""
            }
        }
    }
}
