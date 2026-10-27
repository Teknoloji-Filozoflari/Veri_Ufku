import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: menu
    objectName: "columnHeaderMenu"
    property int columnIndex: -1
    property string columnId: ""
    property string physicalType: ""
    property string roleValue: "text"
    property string descriptionValue: ""
    property var roleIds: ["identifier", "measurement", "category", "text", "time", "ordinal", "ignored"]
    property var roleLabels: [qsTr("kimlik"), qsTr("ölçüm"), qsTr("kategori"), qsTr("metin"), qsTr("tarih"), qsTr("sıralı"), qsTr("dışarıda")]
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: Theme.md
    width: 320

    function openFor(column) {
        let cols = dataView.datasetColumns || []
        if (column < 0 || column >= cols.length)
            return
        let meta = cols[column]
        menu.columnIndex = column
        menu.columnId = meta.id || ""
        menu.physicalType = meta.physical_type || meta.type || "?"
        dataView.selectColumn(menu.columnId)
        Qt.callLater(function() {
            let details = dataView.columnDetails || {}
            menu.roleValue = details.role || "text"
            menu.descriptionValue = details.description || ""
            roleBox.currentIndex = Math.max(0, menu.roleIds.indexOf(menu.roleValue))
            descriptionField.text = menu.descriptionValue
            menu.open()
        })
    }

    background: Rectangle {
        color: Theme.surface
        border.color: Theme.controlBorder
        radius: Theme.radius
    }

    ColumnLayout {
        width: parent.width
        spacing: Theme.sm
        UiLabel {
            text: qsTr("Tür") + ": " + menu.physicalType
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            objectName: "columnHeaderPhysicalType"
        }
        UiLabel { text: qsTr("Rol"); Layout.fillWidth: true }
        UiCombo {
            id: roleBox
            objectName: "columnHeaderRole"
            accessibleLabel: qsTr("Rol")
            model: menu.roleLabels
            Layout.fillWidth: true
        }
        UiLabel { text: qsTr("Açıklama"); Layout.fillWidth: true }
        UiTextField {
            id: descriptionField
            objectName: "columnHeaderDescription"
            Layout.fillWidth: true
            Accessible.name: qsTr("Açıklama")
        }
        UiLabel {
            text: qsTr("Rol ve açıklama veri değişikliği değildir; proje kaydında saklanır, geri alma gerekmez.")
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            color: Theme.secondary
            font.pixelSize: Theme.small
        }
        RowLayout {
            Layout.fillWidth: true
            UiButton {
                objectName: "columnHeaderSave"
                text: qsTr("Kaydet")
                primary: true
                enabled: !projects.busy && !projects.readOnly && menu.columnId.length > 0
                onClicked: {
                    dataView.applyRole(
                        menu.roleIds[roleBox.currentIndex],
                        "",
                        "",
                        "",
                        descriptionField.text
                    )
                    menu.close()
                }
            }
            UiButton {
                objectName: "columnHeaderCancel"
                text: qsTr("İptal")
                onClicked: menu.close()
            }
        }
    }
}
