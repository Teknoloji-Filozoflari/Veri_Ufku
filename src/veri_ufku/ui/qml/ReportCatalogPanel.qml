import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id: root
    objectName: "reportCatalogPanel"
    signal helpRequested(var origin, string context)
    property var selectedSections: ({ "1": true, "8": true })
    property string recipeText: reportBuilder.template("scientific")
    property string exportFormat: "html"
    property bool reviewed: false
    spacing: Theme.md
    Layout.fillWidth: true

    readonly property var chipDefs: [
        { index: 1, title: qsTr("Rapor özeti") },
        { index: 2, title: qsTr("Veri") },
        { index: 3, title: qsTr("İncele") },
        { index: 4, title: qsTr("Görselleştir") },
        { index: 5, title: qsTr("Hazırla") },
        { index: 6, title: qsTr("İstatistik") },
        { index: 7, title: qsTr("Model") },
        { index: 8, title: qsTr("Ekler / metodoloji") }
    ]
    readonly property int selectedCount: {
        let n = 0
        for (let i = 1; i <= 8; i++)
            if (root.selectedSections[String(i)])
                n++
        return n
    }
    readonly property string healthText: {
        let stale = (reportBuilder.freshnessText || "").indexOf("STALE") === 0
        return root.selectedCount + qsTr(" seçili") + (stale ? qsTr(" · STALE") : "")
    }
    readonly property bool canExport: {
        return !reportBuilder.busy && root.reviewed && !!(reportBuilder.saved && reportBuilder.saved.length)
    }

    function statusColor(index) {
        if (root.selectedSections[String(index)])
            return Theme.learningTone
        return Theme.muted
    }
    function statusLabel(index) {
        return root.selectedSections[String(index)] ? qsTr("Seçili") : qsTr("Seçilmedi")
    }
    function toggleSection(index) {
        let next = Object.assign({}, root.selectedSections)
        let key = String(index)
        next[key] = !next[key]
        root.selectedSections = next
        root.rebuildRecipe()
    }
    function selectedList() {
        let out = []
        for (let i = 1; i <= 8; i++)
            if (root.selectedSections[String(i)])
                out.push(i)
        return out
    }
    function rebuildRecipe() {
        root.reviewed = false
        root.recipeText = reportBuilder.composeLayout(
            titleField.text,
            protocol.currentValue || "exploratory",
            JSON.stringify(root.selectedList())
        )
    }
    function runBuild() {
        root.rebuildRecipe()
        root.reviewed = false
        reportBuilder.run(root.recipeText)
    }
    function runExport(fmt) {
        root.exportFormat = fmt
        if (!root.canExport)
            return
        let ident = reportBuilder.saved[reportBuilder.saved.length - 1].id
        let dest = destination.text
        if (!dest || dest.length === 0) {
            picker.selectedFormat = fmt
            picker.open()
            return
        }
        reportBuilder.exportReport(ident, fmt, dest, root.reviewed)
    }

    FileDialog {
        id: picker
        property string selectedFormat: "html"
        title: qsTr("Rapor çıktı dosyası")
        fileMode: FileDialog.SaveFile
        nameFilters: selectedFormat === "pdf" ? ["PDF (*.pdf)"] : ["HTML (*.html)"]
        onAccepted: {
            destination.text = selectedFile.toString().replace(/^file:\/\//, "")
            let ident = reportBuilder.saved[reportBuilder.saved.length - 1].id
            reportBuilder.exportReport(ident, selectedFormat, destination.text, root.reviewed)
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.sm
        UiLabel {
            objectName: "reportCatalogTitle"
            text: qsTr("Raporla")
            font.pixelSize: Theme.heading
            font.bold: true
        }
        Item { Layout.fillWidth: true }
        UiLabel {
            objectName: "reportHealthSummary"
            text: root.healthText
            color: Theme.secondary
            font.pixelSize: Theme.small
            elide: Text.ElideRight
            Layout.maximumWidth: 280 * Theme.scale
        }
    }

    GridLayout {
        Layout.fillWidth: true
        columns: 2
        columnSpacing: Theme.sm
        rowSpacing: Theme.sm
        Repeater {
            model: root.chipDefs
            Rectangle {
                id: chip
                required property var modelData
                objectName: "reportBlockChip_" + modelData.index
                signal clicked()
                onClicked: root.toggleSection(modelData.index)
                Layout.fillWidth: true
                implicitHeight: 36 * Theme.scale
                radius: Theme.radius
                color: root.selectedSections[String(modelData.index)] ? Theme.cyanSurface : Theme.raised
                border.color: root.selectedSections[String(modelData.index)] ? Theme.dataTone : Theme.border
                border.width: 1
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.sm
                    anchors.rightMargin: Theme.sm
                    spacing: Theme.sm
                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: root.statusColor(modelData.index)
                        Layout.alignment: Qt.AlignVCenter
                    }
                    UiLabel {
                        Layout.fillWidth: true
                        text: modelData.index + " · " + modelData.title
                        elide: Text.ElideRight
                        wrapMode: Text.NoWrap
                        maximumLineCount: 1
                        font.pixelSize: Theme.small
                        font.bold: !!root.selectedSections[String(modelData.index)]
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: chip.clicked()
                }
                Accessible.name: modelData.index + " " + modelData.title + " · " + root.statusLabel(modelData.index)
                Accessible.role: Accessible.Button
                Accessible.onPressAction: chip.clicked()
            }
        }
    }

    UiLabel { text: qsTr("Rapor ayarları"); font.bold: true; Layout.fillWidth: true }
    UiTextField {
        id: titleField
        objectName: "reportLayoutTitle"
        Layout.fillWidth: true
        text: qsTr("Veri_Ufku · Bilimsel rapor")
        placeholderText: qsTr("Rapor başlığı")
        Accessible.name: placeholderText
        onEditingFinished: root.rebuildRecipe()
    }
    UiCombo {
        id: protocol
        objectName: "reportLayoutProtocol"
        Layout.fillWidth: true
        model: [
            { id: "exploratory", label: qsTr("Keşifsel") },
            { id: "confirmatory", label: qsTr("Doğrulayıcı") }
        ]
        textRole: "label"
        valueRole: "id"
        accessibleLabel: qsTr("Protokol")
        onActivated: root.rebuildRecipe()
    }
    UiLabel {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        font.pixelSize: Theme.small
        text: qsTr("Biçim: HTML + PDF (A4). ZIP paketleme mevcut dışa aktarımda. Maske için oluşturucu paneli (gelişmiş).")
    }
    UiLabel {
        objectName: "reportLimitationsNote"
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.warning
        font.pixelSize: Theme.small
        text: qsTr("Sınırlamalar: bu rapor analiz/modeli yeniden hesaplamaz; eksik metrik üretilmez; DOCX/LLM yok.")
    }

    UiButton {
        objectName: "reportLayoutBuild"
        text: qsTr("Raporu oluştur ve kaydet")
        tone: "violet"
        Layout.fillWidth: true
        enabled: !reportBuilder.busy && projects.opened && root.selectedCount > 0
        onClicked: root.runBuild()
    }
    UiCheckBox {
        id: reviewedBox
        objectName: "reportLayoutReviewed"
        text: qsTr("Önizleme, sınırlamalar ve bağları inceledim")
        Layout.fillWidth: true
        checked: root.reviewed
        onCheckedChanged: root.reviewed = checked
    }
    UiTextField {
        id: destination
        objectName: "reportLayoutDestination"
        Layout.fillWidth: true
        placeholderText: qsTr("Çıktı dosya yolu (isteğe bağlı)")
        Accessible.name: placeholderText
    }
    UiLabel {
        objectName: "reportCatalogFreshness"
        Layout.fillWidth: true
        wrapMode: Text.WrapAnywhere
        color: Theme.warning
        font.pixelSize: Theme.small
        text: reportBuilder.freshnessText || ""
    }
    UiLabel {
        objectName: "reportCatalogError"
        visible: (reportBuilder.errorText || "").length > 0
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        color: Theme.warning
        text: reportBuilder.errorText || ""
    }

    RowLayout {
        Layout.fillWidth: true
        UiButton {
            objectName: "reportExportHtml"
            text: qsTr("HTML dışa aktar")
            Layout.fillWidth: true
            enabled: root.canExport
            onClicked: root.runExport("html")
        }
        UiButton {
            objectName: "reportExportPdf"
            text: qsTr("PDF dışa aktar")
            tone: "violet"
            primary: true
            Layout.fillWidth: true
            enabled: root.canExport
            onClicked: root.runExport("pdf")
        }
    }

    Component.onCompleted: root.rebuildRecipe()
}
