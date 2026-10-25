import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Frame {
    id: panel
    objectName: "contextSidePanel"
    property int uxStage: 0
    property string stageTitle: ""
    property string stageQuestion: ""
    signal closeRequested()
    signal learnRequested(var origin)
    signal columnChosen(string columnId)

    padding: Theme.md
    background: Rectangle {
        color: Theme.chrome
        border.color: Theme.border
        border.width: 0
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.md

        RowLayout {
            Layout.fillWidth: true
            UiLabel {
                text: qsTr("Bağlam")
                font.pixelSize: Theme.subheading
                font.bold: true
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }
            UiIconButton {
                objectName: "contextPanelClose"
                symbol: "close"
                accessibleLabel: qsTr("Bağlam panelini kapat")
                onClicked: panel.closeRequested()
            }
        }

        UiLabel {
            visible: panel.stageTitle.length > 0
            text: panel.stageTitle
            color: Theme.dataTone
            font.bold: true
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
        UiLabel {
            visible: panel.stageQuestion.length > 0
            text: panel.stageQuestion
            color: Theme.secondary
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }

        TabBar {
            id: contextTabs
            objectName: "contextPanelTabs"
            Layout.fillWidth: true
            TabButton { objectName: "contextTabColumns"; text: qsTr("Sütunlar"); width: implicitWidth }
            TabButton { objectName: "contextTabLearn"; text: qsTr("Bu adımı öğren"); width: implicitWidth }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: contextTabs.currentIndex

            ColumnLayout {
                spacing: Theme.sm
                UiTextField {
                    id: columnSearch
                    objectName: "contextColumnSearch"
                    placeholderText: qsTr("Sütun ara")
                    Accessible.name: qsTr("Sütun ara")
                    Layout.fillWidth: true
                }
                UiLabel {
                    visible: !dataView || dataView.datasets.length === 0
                    text: qsTr("Açık veri kümesi yok. Önce bir kaynak yükleyin.")
                    color: Theme.secondary
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                ListView {
                    id: columnList
                    objectName: "contextColumnList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: {
                        if (!dataView || !dataView.columns) return []
                        let q = columnSearch.text.trim().toLocaleLowerCase()
                        let rows = dataView.columns
                        if (!q) return rows
                        return rows.filter(function(c) {
                            return String(c.name || "").toLocaleLowerCase().indexOf(q) >= 0
                        })
                    }
                    delegate: ItemDelegate {
                        required property var modelData
                        width: columnList.width
                        text: modelData.name + " · " + (modelData.physical_type || "") + (modelData.role ? " · " + modelData.role : "")
                        highlighted: dataView && dataView.selectedColumn === modelData.id
                        onClicked: {
                            dataView.selectColumn(modelData.id)
                            panel.columnChosen(modelData.id)
                        }
                        Accessible.name: text
                        ToolTip.visible: hovered && !!(modelData.description)
                        ToolTip.text: modelData.description || ""
                    }
                }
                UiLabel {
                    text: qsTr("Sütun seçimi ekranlar arasında korunur. Panel kapanınca seçim ve sonuç değişmez.")
                    color: Theme.secondary
                    font.pixelSize: Theme.small
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
            }

            ColumnLayout {
                spacing: Theme.md
                UiLabel {
                    text: qsTr("Bu adımda ne yapılır, nasıl yorumlanır? Yardım isteğe bağlıdır.")
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                UiButton {
                    objectName: "contextLearnButton"
                    tone: "mint"
                    text: qsTr("Bu adımı öğren")
                    Layout.fillWidth: true
                    multiline: true
                    onClicked: panel.learnRequested(this)
                }
                UiLabel {
                    text: qsTr("Kritik uyarılar bu paneline gömülmez; sonuçların yanında kalır.")
                    color: Theme.secondary
                    font.pixelSize: Theme.small
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
            }
        }
    }
}
