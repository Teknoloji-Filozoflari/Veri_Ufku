import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id: root
    objectName: "reportCatalogPanel"
    signal helpRequested(var origin, string context)
    signal openTool(int tool, bool advanced)
    signal openDrawer()
    property var selectedSections: ({ "1": true, "8": true })
    property string recipeText: reportBuilder.template("scientific")
    property string exportFormat: "html"
    property bool reviewed: false
    property int currentFunction: 1
    spacing: Theme.md
    Layout.fillWidth: true

    // Şema: Raporla yedi işlev. Kaynak-aşamaya göre bölümler ikincil kalır.
    readonly property var functionDefs: [
        { index: 1, key: "notebook", title: qsTr("Bulgu defteri"), scope: qsTr("Çekirdek") },
        { index: 2, key: "structure", title: qsTr("Rapor yapısı"), scope: qsTr("Çekirdek") },
        { index: 3, key: "precheck", title: qsTr("Rapor öncesi kontrol"), scope: qsTr("Çekirdek") },
        { index: 4, key: "export", title: qsTr("Dışa aktar"), scope: qsTr("Çekirdek") },
        { index: 5, key: "repro", title: qsTr("Yeniden üretim"), scope: qsTr("Çekirdek") },
        { index: 6, key: "privacy", title: qsTr("Gizlilik ve paylaşım"), scope: qsTr("Çekirdek") },
        { index: 7, key: "advanced", title: qsTr("İleri çıktılar"), scope: qsTr("Modül") }
    ]
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
        nameFilters: selectedFormat === "pdf" ? ["PDF (*.pdf)"]
            : selectedFormat === "docx" ? ["Word (*.docx)"]
            : ["HTML (*.html)"]
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

    UiLabel {
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        color: Theme.secondary
        font.pixelSize: Theme.small
        text: qsTr("Yedi işlev: bulgular, yapı, kontrol, dışa aktarım, yeniden üretim, gizlilik ve ileri çıktılar.")
    }

    // Birincil işlev listesi
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 2
        Repeater {
            model: root.functionDefs
            Rectangle {
                id: functionRow
                required property var modelData
                objectName: "reportFunction_" + modelData.index
                signal clicked()
                onClicked: root.currentFunction = modelData.index
                Layout.fillWidth: true
                implicitHeight: 34 * Theme.scale
                radius: Theme.radius
                color: root.currentFunction === modelData.index ? Theme.cyanSurface : "transparent"
                border.color: root.currentFunction === modelData.index ? Theme.dataTone : Theme.border
                border.width: 1
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.sm
                    anchors.rightMargin: Theme.sm
                    spacing: Theme.sm
                    UiLabel {
                        text: modelData.index + " · " + modelData.title
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        maximumLineCount: 1
                        font.pixelSize: Theme.small
                        font.bold: root.currentFunction === modelData.index
                    }
                    UiLabel {
                        objectName: "reportFunctionScope_" + modelData.index
                        text: modelData.scope
                        color: modelData.scope === "Modül" ? Theme.muted : Theme.secondary
                        font.pixelSize: Theme.small
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: functionRow.clicked()
                }
                Accessible.name: modelData.index + " " + modelData.title + " · " + modelData.scope
                Accessible.role: Accessible.Button
                Accessible.onPressAction: functionRow.clicked()
            }
        }
    }

    StackLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        currentIndex: root.currentFunction - 1

        // 1 — Bulgu defteri
        ColumnLayout {
            spacing: Theme.sm
            UiLabel {
                objectName: "reportNotebookSummary"
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                font.pixelSize: Theme.small
                text: qsTr("Bulgu defteri: ") + findings.count + qsTr(" kayıt")
                      + (findings.staleCount > 0 ? qsTr(" · ") + findings.staleCount + qsTr(" güncel değil") : "")
            }
            UiLabel {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
                font.pixelSize: Theme.small
                text: qsTr("Defterdeki kayıtların tamamı raporun Bulgular bölümüne gerekçesiyle taşınır; hiçbiri sessizce düşmez.")
            }
            ListView {
                objectName: "reportNotebookList"
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(220, Math.max(60, findings.count * 48))
                clip: true
                model: findings.findings
                delegate: UiLabel {
                    required property var modelData
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    font.pixelSize: Theme.small
                    color: modelData.stale ? Theme.warning : Theme.text
                    text: "• " + modelData.question
                          + (modelData.stale ? qsTr("  (güncel değil)") : "")
                }
            }
            UiButton {
                objectName: "reportNotebookOpen"
                text: qsTr("Bulgu defterini aç")
                Layout.fillWidth: true
                enabled: findings.available
                onClicked: root.openDrawer()
            }
        }

        // 2 — Rapor yapısı
        ColumnLayout {
            spacing: Theme.sm
            UiLabel {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
                font.pixelSize: Theme.small
                text: qsTr("Kaynak aşamaya göre bölümler (ikincil)")
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
            UiButton {
                objectName: "reportLayoutBuild"
                text: qsTr("Raporu oluştur ve kaydet")
                tone: "violet"
                Layout.fillWidth: true
                enabled: !reportBuilder.busy && projects.opened && root.selectedCount > 0
                onClicked: root.runBuild()
            }
        }

        // 3 — Rapor öncesi kontrol
        ColumnLayout {
            spacing: Theme.sm
            UiLabel {
                objectName: "reportCatalogFreshness"
                Layout.fillWidth: true
                wrapMode: Text.WrapAnywhere
                color: Theme.warning
                font.pixelSize: Theme.small
                text: reportBuilder.freshnessText || ""
            }
            UiLabel {
                objectName: "reportLimitationsNote"
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Theme.warning
                font.pixelSize: Theme.small
                text: qsTr("Sınırlamalar: bu rapor analiz/modeli yeniden hesaplamaz; eksik metrik üretilmez; yerel LLM yok.")
            }
            UiLabel {
                objectName: "reportTestUsageNote"
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
                font.pixelSize: Theme.small
                text: qsTr("Test kullanım özeti: rapor kayıtlı çalışmaları birleştirir; test verisi yeniden kullanılmaz.")
            }
            UiCheckBox {
                id: reviewedBox
                objectName: "reportLayoutReviewed"
                text: qsTr("Önizleme, sınırlamalar ve bağları inceledim")
                Layout.fillWidth: true
                checked: root.reviewed
                onCheckedChanged: root.reviewed = checked
            }
            UiLabel {
                objectName: "reportCatalogError"
                visible: (reportBuilder.errorText || "").length > 0
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.warning
                font.pixelSize: Theme.small
                text: reportBuilder.errorText || ""
            }
        }

        // 4 — Dışa aktar
        ColumnLayout {
            spacing: Theme.sm
            UiTextField {
                id: destination
                objectName: "reportLayoutDestination"
                Layout.fillWidth: true
                placeholderText: qsTr("Çıktı dosya yolu (isteğe bağlı)")
                Accessible.name: placeholderText
            }
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
            UiButton {
                objectName: "reportExportDocx"
                text: qsTr("Word (DOCX) dışa aktar")
                tone: "violet"
                Layout.fillWidth: true
                enabled: root.canExport
                onClicked: root.runExport("docx")
            }
            UiButton {
                objectName: "reportExportZip"
                text: qsTr("Paket (ZIP) dışa aktar")
                quiet: true
                Layout.fillWidth: true
                enabled: root.canExport
                onClicked: root.runExport("zip")
            }
            UiLabel {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
                font.pixelSize: Theme.small
                text: qsTr("Rapor: PDF · HTML · Word · Markdown. Grafik: PNG/SVG/PDF. Tablo: CSV/Excel. Temiz veri: CSV/Parquet.")
            }
        }

        // 5 — Yeniden üretim
        ColumnLayout {
            spacing: Theme.sm
            UiLabel {
                objectName: "reportReproNote"
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
                font.pixelSize: Theme.small
                text: qsTr("İşlem geçmişi Python kodu, ortam ve paket sürümleri, seed ve veri+işlem+rapor paketi yeniden üretim panelinde hazırlanır.")
            }
            UiButton {
                objectName: "reportReproOpen"
                text: qsTr("Yeniden üretim panelini aç")
                Layout.fillWidth: true
                onClicked: root.openTool(1, false)
            }
        }

        // 6 — Gizlilik ve paylaşım
        ColumnLayout {
            spacing: Theme.sm
            UiLabel {
                objectName: "reportPrivacyNote"
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
                font.pixelSize: Theme.small
                text: qsTr("Kişisel sütun maskeleme, özet/örneklemle paylaşım, dışa aktarım öncesi önizleme ve onay ile veri kaynağı/lisans notu gizlilik ve paylaşım panellerinde yürür.")
            }
            UiButton {
                objectName: "reportPrivacyOpen"
                text: qsTr("Gizlilik panelini aç")
                Layout.fillWidth: true
                onClicked: root.openTool(0, true)
            }
            UiButton {
                objectName: "reportSharingOpen"
                text: qsTr("Paylaşım panelini aç")
                quiet: true
                Layout.fillWidth: true
                onClicked: root.openTool(5, false)
            }
        }

        // 7 — İleri çıktılar (Modül)
        ColumnLayout {
            spacing: Theme.sm
            UiLabel {
                objectName: "reportAdvancedModuleNote"
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.muted
                font.pixelSize: Theme.small
                text: qsTr("Modül: indir — etkileşimli HTML rapor, sunum (slayt) çıktısı ve zamanlanmış rapor bu kurulumda yok. Kurulu olmayan modülün kutusu soluk görünür; indirme yalnız açık tıklamayla başlar.")
            }
            UiButton {
                objectName: "reportAdvancedModuleInstall"
                text: qsTr("Modül: indir")
                quiet: true
                Layout.fillWidth: true
                enabled: false
                Accessible.description: qsTr("Modül sistemi bu kurulumda etkin değil; açık tıklamayla indirme başlatılmaz.")
            }
        }
    }

    Component.onCompleted: root.rebuildRecipe()
}
