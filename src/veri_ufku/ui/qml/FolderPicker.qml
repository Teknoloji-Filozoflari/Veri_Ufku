import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs as Native

Dialog {
    id: picker
    parent: Overlay.overlay
    modal: true
    anchors.centerIn: parent
    width: Math.min(800 * Theme.scale, Overlay.overlay.width - 32)
    height: Math.min(580 * Theme.scale, Overlay.overlay.height - 32)
    padding: Theme.lg
    property string acceptText: "Klasörü seç"
    property url currentFolder: projects.folderPlaces[0].url
    property url selectedFolder: currentFolder
    property var backStack: []
    signal chosen(string folder)
    Native.FolderDialog {
        id: portal
        title: qsTr("Klasör seç")
        currentFolder: picker.currentFolder
        onAccepted: { picker.chosen(selectedFolder.toString()); picker.close() }
    }
    function browse(folder) {
        backStack = backStack.concat([currentFolder])
        currentFolder = folder
        selectedFolder = folder
        search.clear()
        list.currentIndex = -1
    }
    onOpened: { selectedFolder = currentFolder; search.clear(); folders.search(""); folders.showHidden(hidden.checked); folders.load(currentFolder.toString()); list.currentIndex = -1; search.forceActiveFocus() }
    onCurrentFolderChanged: { selectedFolder = currentFolder; if (visible) folders.load(currentFolder.toString()) }
    Connections { target: folders; function onFolderCreated(folder) { if(picker.visible) { newFolder.clear(); picker.browse(folder) } } }
    background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius + 4 }
    header: UiLabel { text: picker.title; padding: Theme.lg; font.pixelSize: Theme.subheading; font.bold: true }
    contentItem: ColumnLayout {
        property string helpContext: "project"
        spacing: Theme.md
        RowLayout {
            Layout.fillWidth: true
            UiButton { text: qsTr("Sistem klasör seçicisi"); onClicked: portal.open(); Accessible.name: text }
            UiIconButton { objectName: picker.objectName + "Back"; symbol: "back"; accessibleLabel: qsTr("Geri"); enabled: picker.backStack.length > 0 && !folders.busy; onClicked: { let stack = picker.backStack.slice(); picker.currentFolder = stack.pop(); picker.backStack = stack; picker.selectedFolder = picker.currentFolder; search.clear() } }
            UiIconButton { objectName: picker.objectName + "Up"; symbol: "up"; accessibleLabel: qsTr("Üst klasör"); enabled: !folders.busy && projects.parentFolder(picker.currentFolder.toString()) !== picker.currentFolder.toString(); onClicked: picker.browse(projects.parentFolder(picker.currentFolder.toString())) }
            UiLabel { text: projects.folderName(picker.currentFolder.toString()); Layout.fillWidth: true; elide: Text.ElideMiddle; color: Theme.secondary; Accessible.name: "Geçerli klasör" }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: Theme.lg
            ColumnLayout {
                Layout.preferredWidth: picker.width < 600 ? 120 : 150
                Layout.alignment: Qt.AlignTop
                UiLabel { text: qsTr("Konumlar"); color: Theme.secondary; font.bold: true }
                Repeater {
                    model: projects.folderPlaces
                    UiButton { required property var modelData; text: modelData.name; quiet: true; Layout.fillWidth: true; onClicked: picker.browse(modelData.url) }
                }
                Item { Layout.fillHeight: true }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                UiTextField { id: search; objectName: picker.objectName + "Search"; placeholderText: qsTr("Bu klasörde ara"); Accessible.name: "Klasör ara"; Layout.fillWidth: true; onTextChanged: if (picker.visible) folders.search(text) }
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    color: Theme.background; radius: Theme.radius; border.color: Theme.border
                    ListView {
                        id: list
                        objectName: picker.objectName + "List"
                        anchors.fill: parent; anchors.margins: 4
                        clip: true; model: folders.rows; spacing: 0
                        ScrollBar.vertical: ScrollBar {}
                        delegate: ItemDelegate {
                            id: row
                            required property var modelData
                            readonly property string fileName: modelData.name
                            readonly property url fileUrl: modelData.url
                            required property int index
                            readonly property bool matches: true
                            objectName: "folderEntry_" + fileName
                            width: list.width; height: matches ? 44 * Theme.scale : 0; visible: matches
                            Accessible.name: fileName
                            highlighted: picker.selectedFolder.toString() === fileUrl.toString()
                            contentItem: UiLabel { text: "▸  " + row.fileName; color: Theme.text; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                            background: Rectangle { radius: Theme.radius; color: row.highlighted ? Theme.toneSurface("warm") : row.hovered ? Theme.hover : "transparent" }
                            onClicked: { list.currentIndex = index; picker.selectedFolder = fileUrl }
                            onDoubleClicked: picker.browse(fileUrl)
                            Keys.onReturnPressed: picker.browse(fileUrl)
                            Keys.onRightPressed: picker.browse(fileUrl)
                        }
                    }
                    BusyIndicator { anchors.centerIn: parent; running: folders.busy; visible: running }
                    UiLabel { anchors.centerIn: parent; text: folders.errorText || (search.text ? "Aramaya uygun klasör yok" : "Bu klasörde alt klasör yok"); color: folders.errorText ? Theme.error : Theme.secondary; visible: !folders.busy && folders.rows.length === 0 }
                }
                UiCheckBox { id: hidden; objectName: picker.objectName + "Hidden"; text: qsTr("Gizli klasörleri göster"); onCheckedChanged: if (picker.visible) folders.showHidden(checked) }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            UiTextField { id: newFolder; objectName: picker.objectName + "NewFolderName"; placeholderText: qsTr("Yeni klasör adı"); Accessible.name: qsTr("Yeni klasör adı"); maximumLength: 255; Layout.fillWidth: true; enabled: !folders.busy; onAccepted: if(text.trim()) folders.createFolder(picker.currentFolder.toString(), text.trim()) }
            UiButton { objectName: picker.objectName + "CreateFolder"; text: qsTr("Yeni klasör oluştur"); enabled: !folders.busy && newFolder.text.trim().length > 0; onClicked: folders.createFolder(picker.currentFolder.toString(), newFolder.text.trim()) }
        }
        UiLabel { text: folders.errorText; visible: text.length > 0; color: Theme.error; Layout.fillWidth: true; wrapMode: Text.Wrap }
        RowLayout {
            Layout.fillWidth: true
            UiLabel { text: qsTr("Seçim: ") + projects.folderName(picker.selectedFolder.toString()); Layout.fillWidth: true; elide: Text.ElideMiddle; color: Theme.secondary }
            UiButton { text: qsTr("Vazgeç"); onClicked: picker.reject() }
            UiButton { objectName: picker.objectName + "Choose"; text: picker.acceptText; primary: true; enabled: !folders.busy && folders.errorText.length === 0; onClicked: { picker.chosen(picker.selectedFolder.toString()); picker.close() } }
        }
    }
}
