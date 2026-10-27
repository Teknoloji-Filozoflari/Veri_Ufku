import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "inspectWorkspacePanel"
    property int selectedBlock: 3
    property string specialKind: ""
    property bool showFilters: false
    property var rules: []
    property var duplicates: []
    spacing: Theme.md
    Layout.fillWidth: true
    signal helpRequested(var origin, string context)
    signal prepareRequested()

    readonly property var chipDefs: [
        { index: 1, title: qsTr("Tablo ve sütunlar") },
        { index: 2, title: qsTr("Temel özet") },
        { index: 3, title: qsTr("Eksik veri") },
        { index: 4, title: qsTr("Kalite kontrolleri") },
        { index: 5, title: qsTr("Özel veri türleri") }
    ]

    function chipStatus(index) {
        let scanned = !!dataView.qualityResult.dataset_version
        if (index === 1) return dataView.datasets.length ? "done" : "untouched"
        if (index === 2) return dataView.inventoryResult.dataset_version || dataView.describeResult.dataset_version ? "done" : (dataView.datasets.length ? "pending" : "untouched")
        if (index === 3 || index === 4) {
            if (!scanned) return dataView.datasets.length ? "pending" : "untouched"
            let codes = index === 3 ? ["missing"] : ["nonfinite", "whitespace", "conversion", "invalid_date", "rule", "uniqueness", "duplicates_full", "duplicates_selected", "constant", "category_similarity", "outlier"]
            let findings = dataView.qualityResult.findings || []
            for (let i = 0; i < findings.length; i++)
                if (codes.indexOf(findings[i].code) >= 0) return "pending"
            return "done"
        }
        return "done"
    }
    function statusColor(status) {
        return status === "done" ? Theme.learningTone : status === "pending" ? Theme.warning : Theme.muted
    }
    function statusLabel(status) {
        return status === "done" ? qsTr("Tamam") : status === "pending" ? qsTr("Karar bekliyor") : qsTr("Dokunulmamış")
    }
    function findingLabel(code) {
        return ({
            missing: qsTr("Eksik değer"),
            nonfinite: qsTr("NaN / sonsuz"),
            whitespace: qsTr("Boş metin / boşluk"),
            conversion: qsTr("Tip dönüşümü"),
            invalid_date: qsTr("Geçersiz tarih"),
            rule: qsTr("Kural ihlali"),
            uniqueness: qsTr("Benzersizlik"),
            duplicates_full: qsTr("Tam satır tekrarı"),
            duplicates_selected: qsTr("Seçili sütun tekrarı"),
            constant: qsTr("Sabit sütun"),
            category_similarity: qsTr("Benzer kategori"),
            outlier: qsTr("Aykırı aday")
        })[code] || code
    }
    function findingsFor(block) {
        let findings = dataView.qualityResult.findings || []
        let out = []
        for (let i = 0; i < findings.length; i++) {
            let code = findings[i].code
            if (block === 3 && code === "missing") out.push(findings[i])
            if (block === 4 && code !== "missing") out.push(findings[i])
        }
        return out
    }
    readonly property string healthText: {
        let findings = (dataView.qualityResult.findings || []).length
        let pending = 0
        for (let i = 1; i <= 5; i++)
            if (chipStatus(i) === "pending") pending++
        return findings + qsTr(" bulgu · ") + pending + qsTr(" karar bekliyor")
    }
    readonly property string scopeText: {
        let q = dataView.qualityResult || ({})
        if (!q.dataset_version)
            return qsTr("Tarama henüz yok. Örneklem sonucu tam veri gibi sunulmaz.")
        let scope = ({ full: qsTr("tam veri"), filtered: qsTr("filtreli"), sample: qsTr("örneklem") })[q.scope] || q.scope
        return qsTr("Kapsam: ") + scope + " · " + q.used_n + " / " + q.population_n + qsTr(" · sürüm ") + String(q.dataset_version).slice(-8)
    }
    readonly property string primaryLabel: {
        if (dataView.busy) return qsTr("İptal")
        if (dataView.qualityResult.dataset_version) return qsTr("Raporu proje taslağına ekle")
        return qsTr("Taramayı çalıştır")
    }
    readonly property bool primaryEnabled: {
        if (dataView.busy) return true
        if (dataView.qualityResult.dataset_version)
            return !projects.busy && !projects.readOnly
        return dataView.datasets.length > 0 && !projects.busy
    }

    function moveFinding(finding) {
        let code = finding.code || ""
        let kind = "fill"
        let method = "median"
        let params = { missing: "null", inspect_origin: "İncele / " + panel.selectedBlock + " / " + code }
        if (code === "duplicates_full" || code === "duplicates_selected") {
            kind = "dedup"
            method = "first"
            params.keep = "first"
            params.descending = false
            params.tie_policy = "input_order_then_rowid"
            params.null_order = "reject"
            params.equality = "v1:null_equal;nan_equal;zero_equal;decimal_numeric;timezone_instant;text_exact"
        } else if (code === "outlier") {
            kind = "outlier"
            method = "mark"
            params.action = "mark"
            params.multiplier = "1.5"
            params.flag_name = "Aykırı_adayı"
        } else if (code === "whitespace") {
            kind = "trim"
            method = "both"
            params.side = "both"
        } else if (code === "category_similarity") {
            kind = "map_categories"
            method = "map"
            params.mapping = []
            params.unmapped = "keep"
        } else if (code === "conversion" || code === "invalid_date") {
            kind = "convert"
            method = code === "invalid_date" ? "Date" : "String"
            params.target = { kind: method }
            params.on_error = "reject"
            params.date_format = ""
        } else if (code === "missing" || code === "nonfinite") {
            kind = "fill"
            method = "median"
            params.method = "median"
        } else {
            // constant / uniqueness / rule: inceleme taslağı; varsayılan fill uydurma.
            kind = "trim"
            method = "both"
            params.side = "both"
            params.review_only = true
        }
        let columnId = ""
        let cols = dataView.datasetColumns || []
        for (let i = 0; i < cols.length; i++)
            if (cols[i].name === finding.column) {
                columnId = cols[i].id
                break
            }
        let columnIds = columnId ? [columnId] : []
        if (kind === "dedup") {
            if (code === "duplicates_full" && cols.length)
                columnIds = cols.map(function(c) { return c.id })
            // Sıra sütunu zorunlu; bulgu sütunu yoksa ilk sütun.
            let orderId = columnId || (cols.length ? cols[0].id : "")
            if (orderId)
                params.order_columns = [orderId]
            if (code === "duplicates_full")
                params.all_columns = true
        }
        if (kind === "fill")
            params.method = method
        let draft = {
            kind: kind,
            column_ids: columnIds,
            method: method,
            parameters: params,
            rationale: (finding.recommendation && finding.recommendation.reason) ? finding.recommendation.reason : finding.reason,
            expected_impact: (finding.recommendation && finding.recommendation.impact) ? finding.recommendation.impact : (finding.count + " / " + finding.denominator),
            origin: "İncele / " + (panel.selectedBlock === 3 ? qsTr("Eksik veri") : qsTr("Kalite")) + " / " + panel.findingLabel(finding.code),
            dataset_version: dataView.qualityResult.dataset_version || "",
            scope: dataView.qualityResult.scope || "",
            finding_code: finding.code,
            column_name: finding.column || ""
        }
        operations.setInspectDraft(draft)
        panel.prepareRequested()
    }

    RowLayout {
        Layout.fillWidth: true
        UiLabel {
            objectName: "inspectWorkspaceTitle"
            text: qsTr("İncele")
            font.pixelSize: Theme.heading
            font.bold: true
        }
        Item { Layout.fillWidth: true }
        UiLabel {
            objectName: "inspectHealthSummary"
            text: panel.healthText
            color: Theme.secondary
            font.pixelSize: Theme.small
            elide: Text.ElideRight
        }
    }
    UiLabel {
        objectName: "inspectScopeLabel"
        text: panel.scopeText
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        color: Theme.secondary
        font.pixelSize: Theme.small
    }
    UiLabel {
        text: qsTr("İncele tarama yapar, veri değiştirmez. Aday hata/silme kararı değildir. Eksiklik nedeni veriden tek başına belirlenemez.")
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        color: Theme.secondary
        font.pixelSize: Theme.small
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 2
        Repeater {
            model: panel.chipDefs
            Rectangle {
                id: chip
                required property var modelData
                objectName: "inspectBlockChip_" + modelData.index
                signal clicked()
                onClicked: panel.selectedBlock = modelData.index
                Layout.fillWidth: true
                implicitHeight: 32
                radius: Theme.radius
                color: panel.selectedBlock === modelData.index ? Theme.field : Theme.raised
                border.color: panel.selectedBlock === modelData.index ? Theme.controlBorder : Theme.border
                RowLayout {
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
                        font.pixelSize: Theme.small
                        font.bold: panel.selectedBlock === modelData.index
                    }
                    UiLabel {
                        text: panel.statusLabel(panel.chipStatus(modelData.index))
                        color: Theme.secondary
                        font.pixelSize: Theme.small
                    }
                }
                MouseArea { anchors.fill: parent; onClicked: chip.clicked() }
                Accessible.name: modelData.index + " · " + modelData.title
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

            ColumnLayout {
                visible: panel.selectedBlock === 1
                Layout.fillWidth: true
                UiLabel {
                    text: qsTr("Tablo salt okunur. Rol/açıklama/not metadata’dır; sürüm üretmez. Arama/sıralama/filtre görünüm filtresidir.")
                    color: Theme.secondary
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                ColumnDetails { Layout.fillWidth: true }
                SavedColumnNotes { Layout.fillWidth: true }
                ValueInspection { Layout.fillWidth: true }
                UiCheckBox {
                    id: contractToggle
                    objectName: "inspectContractToggle"
                    text: qsTr("Veri sözlüğü / sözleşme")
                    Layout.fillWidth: true
                }
                Loader {
                    active: contractToggle.checked
                    visible: active
                    Layout.fillWidth: true
                    sourceComponent: Component { DataContractPanel {} }
                }
            }

            ColumnLayout {
                visible: panel.selectedBlock === 2
                Layout.fillWidth: true
                DatasetOverview { Layout.fillWidth: true }
                UiLabel {
                    text: qsTr("Korelasyon nedensellik göstermez; sıfır varyanslı sütunlar dışlanır. Evrensel kalite puanı yok. Ayrıntılı grafik keşfi Görselleştir’dedir.")
                    color: Theme.secondary
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    font.pixelSize: Theme.small
                }
                UiButton {
                    objectName: "inspectCorrelationHint"
                    text: qsTr("Korelasyon için Görselleştir’e git")
                    quiet: true
                    Layout.fillWidth: true
                    onClicked: window.navigate(3, null)
                }
            }

            ColumnLayout {
                visible: panel.selectedBlock === 3
                Layout.fillWidth: true
                UiLabel {
                    text: qsTr("Eksik burada bulgudur (okuma eşlemesi Veri’dedir). Doldurma/silme tarama ekranında yapılmaz.")
                    color: Theme.secondary
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                UiCombo {
                    id: missingColumn
                    objectName: "inspectMissingColumn"
                    accessibleLabel: qsTr("Eksik sütun")
                    model: dataView.datasetColumns
                    textRole: "name"
                    valueRole: "id"
                    Layout.fillWidth: true
                }
                UiButton {
                    objectName: "inspectMissingImpact"
                    text: qsTr("Silme etkisini önizle (uygulama yok)")
                    Layout.fillWidth: true
                    enabled: !!(missingColumn.currentValue) && !dataView.busy
                    onClicked: dataView.previewMissingDrop(String(missingColumn.currentValue || ""), "")
                }
                UiLabel {
                    visible: !!dataView.missingImpact.dataset_version
                    text: dataView.missingImpact.summary || dataView.missingImpact.note || ""
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Theme.warning
                }
                Repeater {
                    model: panel.findingsFor(3)
                    Frame {
                        required property var modelData
                        Layout.fillWidth: true
                        padding: Theme.md
                        ColumnLayout {
                            width: parent.width
                            spacing: Theme.sm
                            UiLabel {
                                text: modelData.column + " · " + panel.findingLabel(modelData.code) + " · " + modelData.count + " / " + modelData.denominator
                                font.bold: true
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                            }
                            UiLabel {
                                text: modelData.reason + "\n" + qsTr("Bu bulgu otomatik düzeltme başlatmaz.")
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                            }
                            UiButton {
                                objectName: "inspectMoveToPrepare"
                                text: qsTr("Hazırla’ya taşı")
                                primary: true
                                Layout.fillWidth: true
                                onClicked: panel.moveFinding(modelData)
                            }
                        }
                    }
                }
                UiLabel {
                    visible: !!dataView.qualityResult.dataset_version && panel.findingsFor(3).length === 0
                    text: qsTr("Bu taramada eksik bulgusu yok; kusursuz olduğu anlamına gelmez.")
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
            }

            ColumnLayout {
                visible: panel.selectedBlock === 4
                Layout.fillWidth: true
                UiLabel {
                    text: qsTr("Aday hata veya silme kararı değildir. Puan üretilmez.")
                    color: Theme.secondary
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                UiButton {
                    objectName: "inspectOutlierCompute"
                    text: qsTr("Üç yöntemle aykırı aday listesi")
                    Layout.fillWidth: true
                    enabled: dataView.datasets.length > 0 && !dataView.busy
                    onClicked: {
                        let cols = dataView.datasetColumns || []
                        if (cols.length)
                            dataView.computeOutlierCandidates(cols[0].id)
                    }
                }
                UiLabel {
                    visible: !!dataView.outlierCandidates.dataset_version
                    text: qsTr("Birleşik aday: ") + (dataView.outlierCandidates.union_row_ids || []).length + " · " + (dataView.outlierCandidates.disclaimer || "")
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                Repeater {
                    model: panel.findingsFor(4)
                    Frame {
                        required property var modelData
                        Layout.fillWidth: true
                        padding: Theme.md
                        ColumnLayout {
                            width: parent.width
                            spacing: Theme.sm
                            UiLabel {
                                text: modelData.column + " · " + panel.findingLabel(modelData.code) + " · " + modelData.count + " / " + modelData.denominator
                                font.bold: true
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                            }
                            UiLabel {
                                text: modelData.reason
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                                color: Theme.secondary
                            }
                            UiButton {
                                objectName: "inspectMoveToPrepareQuality"
                                text: qsTr("Hazırla’ya taşı")
                                Layout.fillWidth: true
                                onClicked: panel.moveFinding(modelData)
                            }
                        }
                    }
                }
                UiLabel {
                    visible: !!dataView.qualityResult.dataset_version && panel.findingsFor(4).length === 0
                    text: qsTr("Bu taramada kalite adayı yok; kusursuz olduğu anlamına gelmez.")
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                QualityPanel {
                    Layout.fillWidth: true
                    onHelpRequested: function(origin, context) { panel.helpRequested(origin, context) }
                }
            }

            ColumnLayout {
                visible: panel.selectedBlock === 5
                Layout.fillWidth: true
                UiLabel {
                    text: qsTr("Özel tür panelleri yeniden yazılmaz; kurulu değilse durum gösterilir, indirme başlatılmaz.")
                    color: Theme.secondary
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                Repeater {
                    model: [
                        { id: "vision", label: qsTr("Görüntü"), component: "VisionPanel.qml" },
                        { id: "audio", label: qsTr("Ses"), component: "AudioPanel.qml" },
                        { id: "text", label: qsTr("Metin"), component: "TextPanel.qml" },
                        { id: "temporal", label: qsTr("Zaman serisi"), component: "TemporalPanel.qml" },
                        { id: "signal", label: qsTr("Sinyal"), component: "SignalPanel.qml" }
                    ]
                    UiButton {
                        required property var modelData
                        objectName: "inspectSpecial_" + modelData.id
                        text: modelData.label
                        checked: panel.specialKind === modelData.id
                        Layout.fillWidth: true
                        onClicked: panel.specialKind = panel.specialKind === modelData.id ? "" : modelData.id
                    }
                }
                Loader {
                    id: specialLoader
                    active: panel.specialKind.length > 0
                    visible: active
                    Layout.fillWidth: true
                    source: panel.specialKind === "vision" ? "VisionPanel.qml"
                          : panel.specialKind === "audio" ? "AudioPanel.qml"
                          : panel.specialKind === "text" ? "TextPanel.qml"
                          : panel.specialKind === "temporal" ? "TemporalPanel.qml"
                          : panel.specialKind === "signal" ? "SignalPanel.qml" : ""
                }
            }
        }
    }

    UiLabel {
        objectName: "inspectPrimaryReason"
        visible: !panel.primaryEnabled && !dataView.busy
        text: qsTr("Önce proje ve veri açın")
        color: Theme.warning
        font.pixelSize: Theme.small
        Layout.fillWidth: true
    }
    RowLayout {
        Layout.fillWidth: true
        UiButton {
            objectName: "inspectFilterToggle"
            text: qsTr("Filtre")
            quiet: true
            onClicked: panel.showFilters = !panel.showFilters
        }
        UiButton {
            objectName: "inspectPrimaryAction"
            text: panel.primaryLabel
            primary: true
            Layout.fillWidth: true
            Layout.maximumWidth: 10000
            enabled: panel.primaryEnabled
            onClicked: {
                if (dataView.busy)
                    dataView.cancel()
                else if (dataView.qualityResult.dataset_version)
                    dataView.saveQuality()
                else
                    dataView.computeQuality(true, "dataset", "inspect", "[]", "[]")
            }
        }
    }
}
