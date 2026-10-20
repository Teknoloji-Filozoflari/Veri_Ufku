import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    property var result: dataView.profileResult
    spacing: Theme.md
    UiLabel { text: qsTr("Sütun değerlerini incele"); font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiCombo { objectName: "valuesColumn"; accessibleLabel: qsTr("İncelenecek sütun"); model: dataView.datasetColumns; textRole: "name"; valueRole: "id"; currentIndex: { let list = dataView.datasetColumns; return list.findIndex(function(c) { return c.id === dataView.selectedColumn }) } onActivated: dataView.selectColumn(currentValue); Layout.fillWidth: true }
    UiTextField { id: search; objectName: "uniqueSearch"; Accessible.name: qsTr("Görünen benzersiz değerlerde ara"); placeholderText: qsTr("Görünen değer metninde ara"); Layout.fillWidth: true }
    UiButton { objectName: "computeValues"; text: qsTr("Farklı değerleri ve tekrar sayılarını göster"); enabled: dataView.datasets.length > 0 && !projects.busy; onClicked: dataView.inspectValues(false, 0, search.text); Layout.fillWidth: true; multiline: true }
    UiLabel { objectName: "uniqueSummary"; text: panel.result.scope ? (panel.result.scope === "sample" ? "Örnek · " : "Tam veri · ") + panel.result.used_n + "/" + panel.result.population_n + " kayıt · null hariç " + panel.result.unique + " farklı değer · aramayla eşleşen " + panel.result.unique_matching : qsTr("Sütun seç ve tüm veride hesapla."); Layout.fillWidth: true; wrapMode: Text.Wrap }
    Frame {
        Layout.fillWidth: true
        padding: 1
        background: Rectangle { color: Theme.field; border.color: Theme.border; radius: Theme.radius }
        ColumnLayout {
            width: parent.width
            spacing: 0
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 44 * Theme.scale
                color: Theme.cyanSurface
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.lg
                    anchors.rightMargin: Theme.lg
                    UiLabel { text: qsTr("Değer"); font.bold: true; color: Theme.dataTone; Layout.fillWidth: true }
                    UiLabel { text: qsTr("Tekrar sayısı"); font.bold: true; color: Theme.dataTone; horizontalAlignment: Text.AlignRight; Layout.preferredWidth: 120 * Theme.scale }
                }
            }
            ListView {
                id: valueList
                objectName: "uniqueValuesList"
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(360 * Theme.scale, Math.max(96 * Theme.scale, contentHeight))
                clip: true
                model: panel.result.unique_values || []
                ScrollBar.vertical: ScrollBar {}
                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    width: ListView.view.width
                    implicitHeight: Math.max(48 * Theme.scale, valueText.implicitHeight + 2 * Theme.md)
                    color: hover.hovered ? Theme.cyanSurface : index % 2 === 0 ? Theme.surface : Theme.field
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.lg
                        anchors.rightMargin: Theme.lg
                        spacing: Theme.lg
                        UiLabel { id: valueText; text: modelData.value; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                        Rectangle {
                            Layout.preferredWidth: 100 * Theme.scale
                            Layout.preferredHeight: 28 * Theme.scale
                            color: Theme.raised
                            radius: 6
                            UiLabel { anchors.centerIn: parent; text: modelData.count; font.bold: true; color: Theme.dataTone }
                        }
                    }
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border; opacity: 0.4 }
                    HoverHandler { id: hover }
                    ToolTip.visible: hover.hovered
                    ToolTip.text: modelData.value
                }
                UiLabel { anchors.centerIn: parent; visible: valueList.count === 0; text: qsTr("Gösterilecek değer yok."); color: Theme.secondary }
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true
        UiButton { text: qsTr("Önceki değerler"); enabled: !projects.busy && panel.result.unique_offset > 0; onClicked: dataView.inspectValues(false, Math.max(0, panel.result.unique_offset - 200), panel.result.unique_query); Layout.fillWidth: true }
        UiButton { objectName: "nextUniquePage"; text: qsTr("Sonraki değerler"); enabled: !projects.busy && panel.result.unique_offset + 200 < panel.result.unique_matching; onClicked: dataView.inspectValues(false, panel.result.unique_offset + 200, panel.result.unique_query); Layout.fillWidth: true }
    }
    UiLabel { text: qsTr("Her sayfada en fazla 200 farklı değer. Null sayımı sütun profilindedir; NaN tek değer olarak birleştirilir. Görünen metin 256 karakterle sınırlıdır, fiziksel değer değişmez. Arama görünen metne uygulanır. Hesap tüm veriyi kullanır."); color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiLabel { text: (panel.result.warnings || []).join("\n") + "\n" + (dataView.errorText || dataView.message); Layout.fillWidth: true; wrapMode: Text.Wrap; color: dataView.errorText ? Theme.error : Theme.secondary }
    UiButton { visible: dataView.busy; text: qsTr("Hesabı iptal et"); enabled: dataView.busy; onClicked: dataView.cancel(); Layout.fillWidth: true }
}
