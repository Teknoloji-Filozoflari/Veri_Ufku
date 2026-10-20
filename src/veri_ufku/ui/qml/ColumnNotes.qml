import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Frame {
    id: panel
    objectName: "columnNotesPanel"
    property string helpContext: "dataset.profile"
    property var drafts: ({})
    property string noteKey: ""
    property string storedText: ""
    property bool loading: false
    padding: Theme.lg
    implicitHeight: body.implicitHeight + topPadding + bottomPadding
    background: Rectangle { color: Theme.surface; radius: Theme.radius; border.color: Theme.border }
    function loadNote() {
        let key = dataView.selectedDataset + "/" + dataView.selectedColumn
        let stored = dataView.columnDetails.description || ""
        loading = true
        noteKey = key
        storedText = stored
        description.text = drafts[key] !== undefined ? drafts[key] : stored
        loading = false
    }
    Component.onCompleted: loadNote()
    Connections { target: dataView; function onChanged() { panel.loadNote() } }
    ColumnLayout {
        id: body
        width: panel.availableWidth
        spacing: Theme.md
        UiLabel { text: qsTr("Anlam ve notlar"); font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true }
        UiLabel { text: qsTr("Sütunun neyi temsil ettiğini kendi cümlelerinle yaz."); color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.Wrap }
        UiCombo {
            objectName: "columnNotePicker"
            accessibleLabel: qsTr("Açıklama yazılacak sütun")
            model: dataView.datasetColumns
            textRole: "name"
            valueRole: "id"
            currentIndex: dataView.datasetColumns.findIndex(function(column) { return column.id === dataView.selectedColumn })
            enabled: !dataView.busy && !projects.busy
            onActivated: dataView.selectColumn(currentValue)
            Layout.fillWidth: true
        }
        UiTextArea {
            id: description
            objectName: "columnNoteDescription"
            Accessible.name: qsTr("Sütunun anlamı ve kısa notu")
            placeholderText: qsTr("Örn. Age: Yolcunun yaşı. Boş değerlerde yaş bilgisi bilinmiyor.")
            wrapMode: TextEdit.Wrap
            Layout.fillWidth: true
            Layout.preferredHeight: 100 * Theme.scale
            enabled: !projects.readOnly && !projects.busy && !dataView.busy
            onTextChanged: if (!panel.loading && panel.noteKey) panel.drafts[panel.noteKey] = text
        }
        UiButton {
            objectName: "saveColumnNote"
            text: qsTr("Notu kaydet")
            tone: "cyan"
            Layout.alignment: Qt.AlignRight
            enabled: !projects.readOnly && !projects.busy && !dataView.busy && description.text !== panel.storedText
            onClicked: {
                if (dataView.applyDescription(description.text)) {
                    delete panel.drafts[panel.noteKey]
                    panel.loadNote()
                    projects.request("save")
                }
            }
        }
        UiLabel { visible: dataView.errorText.length > 0; text: dataView.errorText; color: Theme.error; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }
}
