import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id: panel
    objectName: "dataLibraryPanel"
    property string helpContext: "import.csv"
    signal helpRequested(var origin, string context)
    signal projectFolderNeeded(string sampleId)
    spacing: Theme.md

    FolderDialog {
        id: sampleFolder
        objectName: "sampleProjectFolderDialog"
        title: qsTr("Örnek proje klasörü seç")
        property string sampleId: ""
        onAccepted: dataLibrary.openSampleAsProject(sampleId, selectedFolder.toString())
    }
    FileDialog {
        id: libraryFile
        objectName: "libraryAddFileDialog"
        title: qsTr("Verilerim’e dosya ekle")
        nameFilters: ["Veri (*)", "CSV (*.csv *.tsv)", "Parquet (*.parquet)"]
        onAccepted: dataLibrary.addPathToLibrary(selectedFile.toLocalFile(), libraryName.text, libraryDescription.text, libraryTags.text)
    }

    UiLabel { text: qsTr("Örnek veri (çevrimdışı)"); font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiLabel { text: qsTr("Paketle gelen küçük örnekler. İnternet kullanılmaz; yeni proje olarak açılır."); color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.Wrap }

    Repeater {
        model: dataLibrary.samples
        Frame {
            required property var modelData
            Layout.fillWidth: true
            padding: Theme.md
            background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius }
            ColumnLayout {
                width: parent.width
                spacing: Theme.sm
                UiLabel { text: modelData.name; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
                UiLabel { text: modelData.description; color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.Wrap }
                UiLabel {
                    text: qsTr("Lisans") + ": " + modelData.license + " · " + (modelData.synthetic ? qsTr("Sentetik") : qsTr("Gerçek")) + " · " + modelData.pii_warning
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    font.pixelSize: Theme.small
                }
                UiLabel {
                    visible: !!(modelData.column_names && modelData.column_names.length)
                    text: qsTr("Sütunlar") + ": " + (modelData.column_names || []).join(", ")
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    font.pixelSize: Theme.small
                }
                UiButton {
                    objectName: "openSample_" + modelData.id
                    text: qsTr("Yeni proje olarak aç")
                    tone: "cyan"
                    enabled: modelData.available && !projects.busy && !imports.busy
                    Layout.fillWidth: true
                    multiline: true
                    onClicked: {
                        sampleFolder.sampleId = modelData.id
                        sampleFolder.open()
                    }
                }
            }
        }
    }

    UiLabel { text: qsTr("Verilerim"); font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiLabel {
        text: qsTr("Yerel kütüphane. Disk: ") + dataLibrary.diskUsageLabel + qsTr(". Kayıt silinince mevcut projeler bozulmaz; proje kendi veri sürümünü tutar.")
        color: Theme.secondary
        Layout.fillWidth: true
        wrapMode: Text.Wrap
    }
    UiTextField { id: libraryName; objectName: "libraryEntryName"; placeholderText: qsTr("Kayıt adı"); Layout.fillWidth: true; Accessible.name: qsTr("Verilerim kayıt adı") }
    UiTextField { id: libraryDescription; objectName: "libraryEntryDescription"; placeholderText: qsTr("Açıklama"); Layout.fillWidth: true; Accessible.name: qsTr("Verilerim açıklama") }
    UiTextField { id: libraryTags; objectName: "libraryEntryTags"; placeholderText: qsTr("Etiketler (virgülle)"); Layout.fillWidth: true; Accessible.name: qsTr("Verilerim etiketleri") }
    RowLayout {
        Layout.fillWidth: true
        UiButton { objectName: "libraryAddFileButton"; text: qsTr("Dosyadan Verilerim’e ekle"); tone: "cyan"; Layout.fillWidth: true; multiline: true; onClicked: libraryFile.open() }
        UiButton { objectName: "libraryAddImportButton"; text: qsTr("Önizlenen dosyayı kaydet"); enabled: !!(imports.sourcePath); Layout.fillWidth: true; multiline: true; onClicked: dataLibrary.addCurrentImportSource() }
    }

    Repeater {
        model: dataLibrary.entries
        Frame {
            required property var modelData
            Layout.fillWidth: true
            padding: Theme.md
            background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius }
            ColumnLayout {
                width: parent.width
                spacing: Theme.sm
                UiLabel { text: modelData.name; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
                UiLabel { text: modelData.description || modelData.original_name; color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.Wrap }
                UiLabel { text: modelData.pii_reminder; color: Theme.warning; Layout.fillWidth: true; wrapMode: Text.Wrap; font.pixelSize: Theme.small }
                RowLayout {
                    Layout.fillWidth: true
                    UiButton {
                        objectName: "libraryUse_" + modelData.id
                        text: qsTr("Bu projeye ekle")
                        tone: "cyan"
                        enabled: projects.opened && !imports.busy && !projects.busy
                        Layout.fillWidth: true
                        multiline: true
                        onClicked: dataLibrary.useLibraryEntry(modelData.id)
                    }
                    UiButton {
                        objectName: "libraryDelete_" + modelData.id
                        text: qsTr("Sil…")
                        Layout.fillWidth: true
                        multiline: true
                        onClicked: dataLibrary.requestDelete(modelData.id)
                    }
                }
            }
        }
    }

    ColumnLayout {
        visible: dataLibrary.pendingDeleteId.length > 0
        Layout.fillWidth: true
        spacing: Theme.sm
        UiLabel { text: qsTr("Silmeyi onayla? Yalnız Verilerim kopyası gider; açık projeler aynı kalır."); color: Theme.warning; Layout.fillWidth: true; wrapMode: Text.Wrap }
        RowLayout {
            Layout.fillWidth: true
            UiButton { objectName: "libraryConfirmDelete"; text: qsTr("Evet, sil"); tone: "warm"; Layout.fillWidth: true; onClicked: dataLibrary.confirmDelete() }
            UiButton { objectName: "libraryCancelDelete"; text: qsTr("Vazgeç"); Layout.fillWidth: true; onClicked: dataLibrary.cancelDelete() }
        }
    }

    UiLabel { visible: dataLibrary.errorText.length > 0; text: dataLibrary.errorText; color: Theme.error; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiLabel { visible: dataLibrary.message.length > 0; text: dataLibrary.message; color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.Wrap }
}
