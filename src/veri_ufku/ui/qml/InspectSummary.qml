import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "inspectSummary"
    spacing: Theme.md

    function typeSummary() {
        let counts = {}
        let columns = dataView.datasetColumns || []
        for (let i = 0; i < columns.length; i++) {
            let kind = columns[i].type || columns[i].physical_type || "?"
            counts[kind] = (counts[kind] || 0) + 1
        }
        let names = Object.keys(counts)
        if (!names.length)
            return "Sütun yok."
        return names.map(function(kind) { return kind + ": " + counts[kind] }).join(" · ")
    }

    function statLine(column) {
        let n = column.numeric || {}
        if (n.suppressed)
            return column.name + ": sayısal özet bastırıldı."
        let q = n.quantiles || {}
        return column.name
            + " · n=" + n.finite_n
            + " · ort=" + n.mean
            + " · medyan=" + (q["0.5"] === undefined ? "—" : q["0.5"])
            + " · min=" + n.minimum
            + " · maks=" + n.maximum
            + " · çeyrek=" + (q["0.25"] === undefined ? "—" : q["0.25"])
            + "–" + (q["0.75"] === undefined ? "—" : q["0.75"])
            + " · std=" + n.std
    }

    UiLabel {
        text: "İncele özeti"
        font.pixelSize: Theme.heading
        font.bold: true
        Layout.fillWidth: true
        wrapMode: Text.Wrap
    }
    UiLabel {
        objectName: "inspectContract"
        text: "Veri burada değişmez. Not karar değildir; silme ve doldurma Hazırla’da Önizle ve ayrı Uygula ister. Sıfır geçerli bir değerdir. Boş metin null değildir. 999 gibi işaretler kendiliğinden eksik sayılmaz. Korelasyon matrisi burada uydurulmaz; ayrıntı Görselleştir’dedir."
        color: Theme.secondary
        Layout.fillWidth: true
        wrapMode: Text.Wrap
    }
    UiLabel {
        objectName: "inspectScope"
        text: dataView.viewSummary || "Tablo kapsamı henüz yok."
        Layout.fillWidth: true
        wrapMode: Text.Wrap
    }
    UiLabel {
        objectName: "inspectTypeSummary"
        text: "Tür özeti (şema): " + panel.typeSummary()
        Layout.fillWidth: true
        wrapMode: Text.Wrap
    }
    UiLabel {
        objectName: "inspectPending"
        visible: !dataView.inventoryResult.dataset_version && !dataView.describeResult.dataset_version
        text: "Eksik sayısı, dolu sayısı ve sayısal özet henüz hesaplanmadı. Sonuç uydurulmaz."
        color: Theme.warning
        Layout.fillWidth: true
        wrapMode: Text.Wrap
    }
    UiButton {
        objectName: "inspectInventory"
        text: "Sütun özetini hesapla"
        tone: "cyan"
        enabled: dataView.datasets.length > 0 && !projects.busy && !dataView.busy
        Layout.fillWidth: true
        onClicked: dataView.inspectColumns(false, false)
    }
    Repeater {
        model: dataView.inventoryResult.dataset_version ? (dataView.inventoryResult.columns || []) : []
        UiLabel {
            required property var modelData
            text: modelData.name + " · " + modelData.physical_type + " · dolu " + modelData.non_null + " · null " + modelData.null + " · nan " + modelData.nan
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
    }
    UiButton {
        objectName: "inspectDescribe"
        text: "Sayısal özeti hesapla"
        tone: "cyan"
        enabled: dataView.datasets.length > 0 && !projects.busy && !dataView.busy
        Layout.fillWidth: true
        onClicked: dataView.inspectColumns(false, true)
    }
    Repeater {
        model: dataView.describeResult.dataset_version ? (dataView.describeResult.columns || []) : []
        UiLabel {
            required property var modelData
            visible: !!modelData.numeric
            text: panel.statLine(modelData)
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
    }
    UiLabel {
        visible: !!dataView.describeResult.dataset_version
        text: "Kategorik frekans bu özette yok. Sayı uydurulmaz."
        color: Theme.secondary
        Layout.fillWidth: true
        wrapMode: Text.Wrap
    }
}
