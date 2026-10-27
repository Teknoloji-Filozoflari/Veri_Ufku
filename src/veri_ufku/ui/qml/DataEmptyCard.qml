import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Item {
    id: root
    objectName: "dataEmptyCard"
    property string draftName: "Yeni proje"
    property string draftFolder: ""
    property bool libraryOpen: false
    property bool detailsOpen: false
    property bool importAfterCreate: false
    readonly property bool showAdvanced: detailsOpen
    onVisibleChanged: if (visible) {
        detailsOpen = false
        importAfterCreate = false
    }
    readonly property bool previewReady: imports.sourcePath.length > 0
                                         && imports.errorText.length === 0
                                         && imports.columns.length > 0
                                         && !imports.busy
    readonly property string importBlockReason: {
        if (imports.busy || projects.busy)
            return qsTr("Dosya veya proje işlemi sürüyor…")
        if (!imports.sourcePath)
            return qsTr("Önce bir kaynak dosyası seçin.")
        if (imports.errorText.length > 0)
            return imports.errorText
        if (!root.previewReady)
            return qsTr("Önizleme bozuldu. Ayraç yanlışsa okuma ayarlarını açın.")
        if (projects.readOnly)
            return qsTr("Proje salt okunur; içe aktarılamaz.")
        if (!imports.ready)
            return qsTr("Önizlemeyi güncelleyin.")
        return ""
    }
    readonly property bool needsProjectForImport: root.previewReady && !projects.busy && !projects.opened
    readonly property bool canImport: imports.ready && !imports.busy && !projects.busy
    readonly property bool importGateIsHint: needsProjectForImport

    function beginImport() {
        if (root.needsProjectForImport) {
            root.importAfterCreate = true
            projects.createDefaultForImport(imports.sourcePath, nameField.text)
            return
        }
        if (root.canImport)
            imports.importData(false)
    }

    FileDialog {
        id: picker
        objectName: "dataEmptyFileDialog"
        title: qsTr("Veri dosyası seç")
        nameFilters: ["Veri (*.csv *.tsv *.json *.jsonl *.ndjson *.xlsx *.parquet)", "Tüm dosyalar (*)"]
        onAccepted: imports.choose(selectedFile.toString())
    }
    FolderPicker {
        id: projectFolder
        objectName: "dataEmptyProjectFolder"
        title: qsTr("Proje klasörü")
        onChosen: function(folder) {
            root.draftFolder = projects.folderDisplay(folder)
            if (projects.opened || projects.busy)
                return
            let label = nameField.text.length > 0 ? nameField.text : root.draftName
            projects.createInFolder(folder, label)
        }
    }
    Connections {
        target: projects
        function onChanged() {
            if (!root.importAfterCreate)
                return
            if (dataView.datasets && dataView.datasets.length > 0) {
                root.importAfterCreate = false
                return
            }
            if (!projects.opened || projects.busy || imports.busy || !imports.ready)
                return
            imports.importData(false)
        }
    }

    Rectangle {
        id: card
        anchors.centerIn: parent
        width: Math.max(280, parent.width - 48)
        height: Math.min(parent.height - 48, column.implicitHeight + 48)
        radius: Theme.radius
        color: Theme.surface
        border.color: Theme.border

        ScrollView {
            anchors.fill: parent
            anchors.margins: Theme.xl
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                id: column
                width: parent.width
                spacing: Theme.md

                UiLabel {
                    text: qsTr("Verinle çalışmaya başla")
                    font.pixelSize: Theme.heading
                    font.bold: true
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.sm
                    UiButton {
                        objectName: "chooseCsvButton"
                        text: qsTr("Dosya seç")
                        primary: true
                        enabled: !imports.busy && !projects.busy
                        onClicked: picker.open()
                    }
                    UiButton {
                        objectName: "dataEmptyLibrary"
                        text: qsTr("Verilerim")
                        enabled: !imports.busy
                        onClicked: root.libraryOpen = !root.libraryOpen
                    }
                    UiButton {
                        objectName: "dataEmptySample"
                        text: qsTr("Örnek")
                        enabled: !imports.busy
                        onClicked: root.libraryOpen = true
                    }
                }
                Loader {
                    active: root.libraryOpen
                    visible: active
                    Layout.fillWidth: true
                    sourceComponent: Component {
                        DataLibraryPanel {
                            onHelpRequested: function(origin, context) {}
                        }
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: card.width >= 720 ? 3 : 1
                    columnSpacing: Theme.md
                    rowSpacing: Theme.sm
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.xs
                        UiLabel { text: qsTr("Proje adı"); Layout.fillWidth: true }
                        UiTextField {
                            id: nameField
                            objectName: "dataEmptyProjectName"
                            property bool nameTouched: false
                            text: projects.opened ? projects.name : root.draftName
                            Layout.fillWidth: true
                            Accessible.name: qsTr("Proje adı")
                            onTextEdited: nameTouched = true
                            onEditingFinished: {
                                if (!nameTouched)
                                    return
                                nameTouched = false
                                if (projects.opened) {
                                    if (text !== projects.name)
                                        projects.setName(text)
                                } else if (text.length > 0) {
                                    root.draftName = text
                                }
                            }
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.xs
                        UiLabel { text: qsTr("Proje klasörü"); Layout.fillWidth: true }
                        RowLayout {
                            Layout.fillWidth: true
                            UiTextField {
                                objectName: "dataEmptyProjectFolderPath"
                                text: projects.opened ? projects.path : root.draftFolder
                                readOnly: true
                                Layout.fillWidth: true
                                Accessible.name: qsTr("Proje klasörü")
                                placeholderText: qsTr("İsteğe bağlı")
                            }
                            UiButton {
                                objectName: projects.opened ? "dataEmptyBrowseProject" : "importProjectButton"
                                text: qsTr("Gözat")
                                onClicked: projectFolder.open()
                            }
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.xs
                        UiLabel { text: qsTr("Kaynak"); Layout.fillWidth: true }
                        RowLayout {
                            Layout.fillWidth: true
                            UiLabel {
                                objectName: "dataEmptySourceLabel"
                                text: imports.sourcePath || qsTr("henüz seçilmedi")
                                Layout.fillWidth: true
                                elide: Text.ElideMiddle
                                color: Theme.secondary
                                verticalAlignment: Text.AlignVCenter
                            }
                            UiButton {
                                objectName: "dataEmptyBrowseSource"
                                visible: false
                                text: qsTr("Gözat")
                                quiet: true
                                enabled: !imports.busy && !projects.busy
                                onClicked: picker.open()
                            }
                        }
                    }
                }

                ColumnLayout {
                    visible: imports.sourcePath.length > 0
                    Layout.fillWidth: true
                    spacing: Theme.md
                    UiLabel {
                        visible: imports.errorText.length > 0
                        text: imports.errorText
                        color: Theme.error
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                    UiLabel {
                        objectName: "dataEmptyStatus"
                        visible: imports.statusText.length > 0
                        text: imports.statusText
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: Theme.secondary
                    }
                    UiButton {
                        objectName: "importAdvancedButton"
                        text: root.showAdvanced ? qsTr("Okuma ayarları · açık") : qsTr("Okuma ayarları")
                        checked: root.showAdvanced
                        quiet: true
                        Layout.fillWidth: true
                        onClicked: root.detailsOpen = !root.detailsOpen
                    }
                    ColumnLayout {
                        visible: root.showAdvanced
                        Layout.fillWidth: true
                        spacing: Theme.sm
                        UiCombo {
                            objectName: "importDelimiter"
                            accessibleLabel: qsTr("Ayraç")
                            visible: imports.formatId === "csv" || imports.formatId === "tsv"
                            model: [",", ";", "Sekme", "|"]
                            currentIndex: [",", ";", "\t", "|"].indexOf(imports.settings.delimiter)
                            Layout.fillWidth: true
                            onActivated: imports.setOption("delimiter", [",", ";", "\t", "|"][currentIndex])
                        }
                        StructuredOptions {
                            Layout.fillWidth: true
                            visible: imports.formatId !== "csv" && imports.formatId !== "tsv"
                        }
                        UiButton {
                            objectName: "previewCsvButton"
                            text: qsTr("Önizlemeyi güncelle")
                            enabled: !imports.busy && imports.sourcePath.length > 0
                            Layout.fillWidth: true
                            onClicked: imports.refreshPreview()
                        }
                    }
                    HorizontalHeaderView {
                        visible: imports.columns.length > 0
                        id: previewHeader
                        Layout.fillWidth: true
                        syncView: previewTable
                        clip: true
                    }
                    TableView {
                        id: previewTable
                        visible: imports.columns.length > 0
                        objectName: "csvPreviewTable"
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(120, Math.max(72, Math.min(rows, 4) * 28 + 8))
                        clip: true
                        model: imports.previewModel
                        columnWidthProvider: function(c) { return Math.max(72, width / Math.max(1, columns)) }
                        rowHeightProvider: function(r) { return 28 }
                        ScrollBar.horizontal: ScrollBar {}
                        delegate: Rectangle {
                            required property string display
                            implicitWidth: 72
                            implicitHeight: 28
                            color: Theme.surface
                            border.color: Theme.border
                            UiLabel {
                                anchors.fill: parent
                                anchors.margins: 4
                                text: parent.display
                                elide: Text.ElideRight
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                    UiButton {
                        objectName: "importCsvButton"
                        text: qsTr("İçe aktar")
                        primary: true
                        Layout.fillWidth: true
                        enabled: root.canImport || root.needsProjectForImport
                        Accessible.description: root.canImport || root.needsProjectForImport ? qsTr("İçe aktar") : root.importBlockReason
                        onClicked: root.beginImport()
                    }
                }
                // Boş kahramanda gizli; kaynak seçilince gösterilir. objectName test için kalır.
                UiLabel {
                    objectName: "importBlockReason"
                    visible: imports.sourcePath.length > 0 && root.importBlockReason.length > 0
                    text: root.importBlockReason
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: root.importGateIsHint ? Theme.secondary : Theme.warning
                }

                // Mockup’ta yok; objectName test için ağaçta kalır.
                UiLabel {
                    objectName: "dataEmptyHint"
                    visible: false
                    text: qsTr("Kaynak seçildiğinde aynı alanda önizleme açılır. Kaynak dosya değiştirilemez.")
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Theme.secondary
                    font.pixelSize: Theme.small
                }
                UiLabel {
                    objectName: "dataEmptyFooter"
                    visible: false
                    text: (imports.sourcePath ? qsTr("Kaynak seçildi") : qsTr("Kaynak yok"))
                          + " · "
                          + (projects.opened ? (projects.dirty ? qsTr("Proje kaydedilmedi") : qsTr("Proje açık")) : qsTr("Proje kaydedilmedi"))
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Theme.secondary
                    font.pixelSize: Theme.small
                }
            }
        }
    }
}
