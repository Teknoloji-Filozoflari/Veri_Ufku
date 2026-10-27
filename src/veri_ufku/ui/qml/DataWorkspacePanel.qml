import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id: panel
    objectName: "dataWorkspacePanel"
    property int selectedBlock: 2
    property bool firstLookApproved: false
    spacing: Theme.md
    Layout.fillWidth: true

    readonly property var chipDefs: [
        { index: 1, title: qsTr("Proje") },
        { index: 2, title: qsTr("Kaynak seçimi") },
        { index: 3, title: qsTr("Okuma ayarları") },
        { index: 4, title: qsTr("Tür ve rol atama") },
        { index: 5, title: qsTr("Eksik değerler") },
        { index: 6, title: qsTr("İçe aktarma kontrolü") },
        { index: 7, title: qsTr("Veri sürümü") },
        { index: 8, title: qsTr("İlk bakış") },
        { index: 9, title: qsTr("Kaynak adaptörleri") },
        { index: 10, title: qsTr("Özel kaynaklar") }
    ]

    function chipStatus(index) {
        let hasData = dataView.datasets.length > 0
        let source = imports.sourcePath.length > 0
        if (index === 1) return projects.opened ? "done" : "pending"
        if (index === 2) return hasData || source ? "done" : "pending"
        if (index === 3) return hasData || imports.ready ? "done" : (source ? "pending" : "untouched")
        if (index === 4) return hasData ? "done" : "untouched"
        if (index === 5) return hasData ? (dataView.missingImpact.affected_rows ? "pending" : "done") : "untouched"
        if (index === 6) return hasData ? "done" : (source ? "pending" : "untouched")
        if (index === 7) return hasData ? "done" : "untouched"
        if (index === 8) return panel.firstLookApproved ? "done" : (hasData ? "pending" : "untouched")
        return "done"
    }
    function statusColor(status) {
        return status === "done" ? Theme.learningTone : status === "pending" ? Theme.warning : Theme.muted
    }
    function statusLabel(status) {
        return status === "done" ? qsTr("Tamam") : status === "pending" ? qsTr("Karar bekliyor") : qsTr("Dokunulmamış")
    }
    readonly property string healthText: {
        let warnings = (dataView.qualityResult.findings || []).length
        let pending = 0
        for (let i = 1; i <= 10; i++)
            if (chipStatus(i) === "pending") pending++
        return warnings + qsTr(" uyarı · ") + pending + qsTr(" karar bekliyor")
    }
    readonly property string primaryLabel: {
        if (selectedBlock === 2 || selectedBlock === 6) return qsTr("İçe aktar")
        if (selectedBlock === 5) return qsTr("Önizlemeyi yenile")
        if (selectedBlock === 8) return panel.firstLookApproved ? qsTr("İlk bakışı göster") : qsTr("İlk bakışı onayla")
        if (selectedBlock === 1) return qsTr("Kaydet")
        if (selectedBlock === 4) return qsTr("Kaydet")
        return qsTr("Devam")
    }
    readonly property bool primaryEnabled: {
        if (selectedBlock === 2 || selectedBlock === 6)
            return projects.opened && imports.ready && !imports.busy
        if (selectedBlock === 5)
            return !!dataView.missingImpact.column_id && !dataView.busy
        if (selectedBlock === 8)
            return dataView.datasets.length > 0 && !dataView.busy
        if (selectedBlock === 1 || selectedBlock === 4)
            return projects.opened && !projects.readOnly && !projects.busy
        return false
    }
    readonly property string primaryReason: {
        if (primaryEnabled) return primaryLabel
        if ((selectedBlock === 2 || selectedBlock === 6) && imports.busy)
            return qsTr("Dosya işleniyor…")
        if ((selectedBlock === 2 || selectedBlock === 6) && !projects.opened)
            return qsTr("İçe aktarma açık bir proje ister")
        if ((selectedBlock === 2 || selectedBlock === 6) && !imports.sourcePath)
            return qsTr("Önce kaynak seçin")
        if ((selectedBlock === 2 || selectedBlock === 6) && !imports.ready)
            return qsTr("Kaynak önizlemesi hazır değil; okuma ayarlarını kontrol edin")
        if (selectedBlock === 5)
            return qsTr("Önce etki önizlemesi alın; kalıcı doldurma Hazırla’dadır")
        if (!projects.opened) return qsTr("Önce proje açın")
        return qsTr("Bu adımda birincil eylem yok")
    }
    readonly property int nextBlock: selectedBlock < 10 ? selectedBlock + 1 : 0
    readonly property string nextTitle: {
        if (!nextBlock)
            return ""
        for (let i = 0; i < chipDefs.length; i++)
            if (chipDefs[i].index === nextBlock)
                return chipDefs[i].title
        return ""
    }
    readonly property string nextSummary: {
        if (!nextBlock)
            return ""
        if (nextBlock === 3)
            return readingSummary
        if (nextBlock === 2)
            return imports.sourcePath || qsTr("henüz seçilmedi")
        return statusLabel(chipStatus(nextBlock))
    }
    readonly property string readingSummary: {
        let d = imports.settings.delimiter === "\t" ? qsTr("sekme") : (imports.settings.delimiter || ",")
        let decimal = imports.settings.decimal || "."
        let enc = imports.settings.encoding || "utf-8"
        return d + " · " + qsTr("ondalık ") + decimal + " · " + enc
    }

    FileDialog {
        id: sourcePicker
        objectName: "dataWorkspaceFileDialog"
        title: qsTr("Veri dosyası seç")
        nameFilters: ["Veri (*.csv *.tsv *.json *.jsonl *.xlsx *.parquet)", "Tüm dosyalar (*)"]
        onAccepted: imports.choose(selectedFile.toString())
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.sm
        UiLabel {
            objectName: "dataWorkspaceTitle"
            text: qsTr("Veri")
            font.pixelSize: Theme.heading
            font.bold: true
        }
        Item { Layout.fillWidth: true }
        UiLabel {
            objectName: "dataHealthSummary"
            text: panel.healthText
            color: Theme.secondary
            font.pixelSize: Theme.small
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignRight
            Layout.maximumWidth: 280 * Theme.scale
        }
    }

    GridLayout {
        id: chipGrid
        Layout.fillWidth: true
        columns: 2
        columnSpacing: Theme.sm
        rowSpacing: Theme.sm
        Repeater {
            model: panel.chipDefs
            Rectangle {
                id: chip
                required property var modelData
                objectName: "dataBlockChip_" + modelData.index
                signal clicked()
                onClicked: panel.selectedBlock = modelData.index
                Layout.fillWidth: true
                implicitHeight: 36 * Theme.scale
                radius: Theme.radius
                color: panel.selectedBlock === modelData.index ? Theme.cyanSurface : Theme.raised
                border.color: panel.selectedBlock === modelData.index ? Theme.dataTone : Theme.border
                border.width: 1
                RowLayout {
                    id: chipRow
                    anchors.fill: parent
                    anchors.leftMargin: Theme.sm
                    anchors.rightMargin: Theme.sm
                    spacing: Theme.sm
                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: panel.statusColor(panel.chipStatus(modelData.index))
                        Layout.alignment: Qt.AlignVCenter
                    }
                    UiLabel {
                        Layout.fillWidth: true
                        text: modelData.index + " · " + modelData.title
                        elide: Text.ElideRight
                        wrapMode: Text.NoWrap
                        maximumLineCount: 1
                        font.pixelSize: Theme.small
                        font.bold: panel.selectedBlock === modelData.index
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: chip.clicked()
                }
                Accessible.name: modelData.index + " " + modelData.title + " · " + panel.statusLabel(panel.chipStatus(modelData.index))
                Accessible.role: Accessible.Button
                Accessible.onPressAction: chip.clicked()
            }
        }
    }

    ScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        contentWidth: availableWidth
        ColumnLayout {
            width: parent.width
            spacing: Theme.sm

            // 1 Proje
            ColumnLayout {
                visible: panel.selectedBlock === 1
                Layout.fillWidth: true
                UiTextField {
                    objectName: "dataBlockProjectName"
                    text: projects.name
                    Layout.fillWidth: true
                    Accessible.name: qsTr("Proje adı")
                    onEditingFinished: projects.setName(text)
                }
                UiLabel {
                    text: projects.path || qsTr("Klasör yok")
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    elide: Text.ElideMiddle
                }
                UiLabel {
                    text: projects.dirty ? qsTr("Kaydedilmedi") : qsTr("Kaydedildi")
                    color: Theme.secondary
                    Layout.fillWidth: true
                }
            }

            // 2 Kaynak
            ColumnLayout {
                visible: panel.selectedBlock === 2
                Layout.fillWidth: true
                RowLayout {
                    Layout.fillWidth: true
                    UiLabel {
                        text: imports.sourcePath || qsTr("henüz seçilmedi")
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        elide: Text.ElideMiddle
                    }
                    UiButton {
                        objectName: "dataBlockChooseFile"
                        text: imports.sourcePath ? qsTr("Değiştir") : qsTr("Dosya seç")
                        onClicked: sourcePicker.open()
                    }
                }
                UiCombo {
                    objectName: "dataBlockFormat"
                    accessibleLabel: qsTr("Biçim")
                    model: imports.formats
                    currentIndex: model.indexOf(imports.formatId)
                    Layout.fillWidth: true
                    onActivated: if (activeFocus) imports.setFormat(currentText)
                }
                UiLabel {
                    visible: imports.columns.length > 0
                    text: qsTr("İlk 3 satır")
                    Layout.fillWidth: true
                    font.bold: true
                }
                TableView {
                    visible: imports.columns.length > 0
                    objectName: "dataBlockPreviewTable"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 72
                    clip: true
                    model: imports.previewModel
                    columnWidthProvider: function(c) { return 96 }
                    rowHeightProvider: function(r) { return r < 3 ? 24 : 0 }
                    delegate: Rectangle {
                        required property string display
                        required property int row
                        implicitWidth: 96
                        implicitHeight: row < 3 ? 24 : 0
                        visible: row < 3
                        color: Theme.surface
                        UiLabel { anchors.fill: parent; anchors.margins: 2; text: parent.display; elide: Text.ElideRight; font.pixelSize: Theme.small }
                    }
                }
                UiButton {
                    objectName: "dataBlockRefreshPreview"
                    text: qsTr("Önizlemeyi yenile")
                    enabled: imports.sourcePath.length > 0 && !imports.busy
                    Layout.fillWidth: true
                    onClicked: imports.refreshPreview()
                }
            }

            // 3 Okuma ayarları
            ColumnLayout {
                visible: panel.selectedBlock === 3
                Layout.fillWidth: true
                UiLabel {
                    objectName: "dataBlockReadingSummary"
                    text: panel.readingSummary
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Theme.secondary
                }
                UiCombo {
                    objectName: "dataBlockDelimiter"
                    accessibleLabel: qsTr("Ayraç")
                    model: [",", ";", "Sekme", "|"]
                    currentIndex: [",", ";", "\t", "|"].indexOf(imports.settings.delimiter)
                    Layout.fillWidth: true
                    onActivated: imports.setOption("delimiter", [",", ";", "\t", "|"][currentIndex])
                }
                UiSpinBox {
                    objectName: "dataBlockHeaderRow"
                    from: 0
                    to: 100
                    value: imports.settings.header_row || 0
                    Accessible.name: qsTr("Başlık kaydı")
                    Layout.fillWidth: true
                    onValueModified: imports.setOption("header_row", value)
                }
                UiCombo {
                    objectName: "dataBlockDecimal"
                    accessibleLabel: qsTr("Ondalık")
                    model: [".", ","]
                    currentIndex: model.indexOf(imports.settings.decimal)
                    Layout.fillWidth: true
                    onActivated: imports.setOption("decimal", currentText)
                }
                UiTextField {
                    objectName: "dataBlockNullMarkers"
                    text: (imports.settings.null_markers || []).join("|")
                    Accessible.name: qsTr("Null işaretleri")
                    Layout.fillWidth: true
                    onEditingFinished: imports.setOption("null_markers", text)
                }
                StructuredOptions {
                    Layout.fillWidth: true
                    visible: imports.formatId !== "csv" && imports.formatId !== "tsv" && imports.sourcePath.length > 0
                }
                UiButton {
                    text: qsTr("Önizlemeyi güncelle")
                    enabled: imports.sourcePath.length > 0
                    Layout.fillWidth: true
                    onClicked: imports.refreshPreview()
                }
                UiLabel {
                    text: qsTr("Ayarlar kaynak dosyaya yazılmaz.")
                    color: Theme.secondary
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    font.pixelSize: Theme.small
                }
            }

            // 4 Tür ve rol
            ColumnLayout {
                visible: panel.selectedBlock === 4
                Layout.fillWidth: true
                ListView {
                    objectName: "dataBlockColumnList"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 180
                    clip: true
                    model: dataView.columns
                    ScrollBar.vertical: ScrollBar {}
                    delegate: UiButton {
                        required property var modelData
                        width: ListView.view.width
                        multiline: true
                        text: modelData.name + " · " + modelData.physical_type + " · " + (modelData.role || "")
                        checked: modelData.selected
                        onClicked: dataView.selectColumn(modelData.id)
                    }
                }
                ColumnDetails {
                    notesOnly: true
                    Layout.fillWidth: true
                }
            }

            // 5 Eksik
            ColumnLayout {
                visible: panel.selectedBlock === 5
                Layout.fillWidth: true
                UiCombo {
                    id: missingColumn
                    objectName: "dataBlockMissingColumn"
                    accessibleLabel: qsTr("Eksik sütun")
                    model: dataView.columns
                    textRole: "name"
                    valueRole: "id"
                    Layout.fillWidth: true
                }
                UiButton {
                    objectName: "dataBlockMissingPreview"
                    text: qsTr("Etki önizlemesi")
                    Layout.fillWidth: true
                    enabled: !!(missingColumn.currentValue)
                    onClicked: dataView.previewMissingDrop(String(missingColumn.currentValue || ""), "")
                }
                UiLabel {
                    text: dataView.missingImpact.summary || dataView.missingImpact.message || qsTr("Önizleme sürüm yazmaz. Uygula ayrıdır.")
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Theme.secondary
                }
            }

            // 6 İçe aktarma kontrolü
            ColumnLayout {
                visible: panel.selectedBlock === 6
                Layout.fillWidth: true
                UiLabel {
                    text: imports.statusText || qsTr("Kontrol bekleniyor")
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                UiLabel {
                    text: imports.ready ? qsTr("İçe aktarma hazır") : qsTr("İçe aktarma kapalı: önizleme veya proje eksik")
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: imports.ready ? Theme.secondary : Theme.warning
                }
                UiLabel {
                    visible: imports.previewWarnings.length > 0
                    text: imports.previewWarnings
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Theme.warning
                }
            }

            // 7 Sürüm
            ColumnLayout {
                visible: panel.selectedBlock === 7
                Layout.fillWidth: true
                UiLabel {
                    text: dataView.viewSummary || qsTr("Veri sürümü yok")
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                UiLabel {
                    text: qsTr("Kaynak dosya değişmez. Sürüm geçmişi mevcut proje kaydındadır.")
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Theme.secondary
                    font.pixelSize: Theme.small
                }
            }

            // 8 İlk bakış
            ColumnLayout {
                visible: panel.selectedBlock === 8
                Layout.fillWidth: true
                UiLabel {
                    text: panel.firstLookApproved ? qsTr("İlk bakış onaylandı") : qsTr("İlk bakış onayı sonrası özet çalışır; öneriler uygulanmaz.")
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                DatasetOverview {
                    visible: panel.firstLookApproved
                    Layout.fillWidth: true
                }
            }

            // 9 Adaptörler
            ColumnLayout {
                visible: panel.selectedBlock === 9
                Layout.fillWidth: true
                Repeater {
                    model: expertWorkspace.dataAdapters
                    UiLabel {
                        required property var modelData
                        text: modelData.label + " · " + modelData.status
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: modelData.installed ? Theme.secondary : Theme.muted
                    }
                }
                UiLabel {
                    text: qsTr("İndirme veya kurulum bu ekranda yok.")
                    Layout.fillWidth: true
                    font.pixelSize: Theme.small
                    color: Theme.secondary
                }
            }

            // 10 Özel
            ColumnLayout {
                visible: panel.selectedBlock === 10
                Layout.fillWidth: true
                Repeater {
                    model: expertWorkspace.dataSpecialAdapters
                    UiLabel {
                        required property var modelData
                        text: modelData.label + " · " + modelData.status
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: modelData.installed ? Theme.secondary : Theme.muted
                    }
                }
            }
        }
    }

    Rectangle {
        objectName: "dataNextBlock"
        visible: panel.nextBlock > 0
        Layout.fillWidth: true
        implicitHeight: nextRow.implicitHeight + 8
        radius: Theme.radius
        color: "transparent"
        border.color: Theme.border
        RowLayout {
            id: nextRow
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.margins: Theme.sm
            UiLabel {
                text: panel.nextBlock + " · " + panel.nextTitle
                font.pixelSize: Theme.small
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            UiLabel {
                text: panel.nextSummary
                color: Theme.secondary
                font.pixelSize: Theme.small
                elide: Text.ElideRight
            }
        }
        MouseArea {
            anchors.fill: parent
            onClicked: panel.selectedBlock = panel.nextBlock
        }
        Accessible.name: panel.nextBlock + " · " + panel.nextTitle
        Accessible.role: Accessible.Button
    }
    UiLabel {
        objectName: "dataPrimaryReason"
        visible: !panel.primaryEnabled
        text: panel.primaryReason
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        color: Theme.warning
        font.pixelSize: Theme.small
    }
    RowLayout {
        Layout.fillWidth: true
        UiButton {
            objectName: "dataPrimaryCancel"
            text: qsTr("Geri")
            onClicked: {
                if (selectedBlock > 1)
                    selectedBlock = selectedBlock - 1
            }
        }
        UiButton {
            objectName: "dataPrimaryAction"
            text: panel.primaryLabel
            primary: true
            Layout.fillWidth: true
            Layout.maximumWidth: 10000
            enabled: panel.primaryEnabled
            Accessible.description: panel.primaryReason
            onClicked: {
                if (selectedBlock === 2 || selectedBlock === 6)
                    imports.importData(false)
                else if (selectedBlock === 1 || selectedBlock === 4)
                    projects.request("save")
                else if (selectedBlock === 8) {
                    panel.firstLookApproved = true
                } else if (selectedBlock === 5) {
                    dataView.previewMissingDrop(dataView.missingImpact.column_id || "", "")
                }
            }
        }
    }
}
