import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id: panel
    objectName: "csvImportPanel"
    property string helpContext: ["ods", "sqlite", "ipc", "ipc_stream"].indexOf(imports.formatId) >= 0 ? "import.phase11" : imports.formatId === "json" ? "import.json" : imports.formatId === "jsonl" ? "import.jsonl" : imports.formatId === "xlsx" ? "import.xlsx" : imports.formatId === "parquet" ? "import.parquet" : "import.csv"
    signal helpRequested(var origin, string context)
    Layout.minimumWidth: 0
    spacing: Theme.md
    FileDialog {
        id: picker
        objectName: "csvFileDialog"
        title: "Veri dosyası seç"
        nameFilters: ["Veri (*.csv *.tsv *.json *.jsonl *.ndjson *.xlsx *.parquet *.ods *.sqlite *.db *.feather *.arrow *.ipc *.arrows)", "Tüm dosyalar (*)"]
        onAccepted: imports.choose(selectedFile.toString())
    }
    function openPicker() { picker.open() }
    Label { Layout.minimumWidth: 0; wrapMode: Text.Wrap; text: "Veri içe aktar"; font.pixelSize: Theme.heading; font.bold: true; Layout.fillWidth: true }
    GridLayout {
        columns: panel.width > 600 * Theme.scale ? 2 : 1
        Layout.fillWidth: true
        UiButton { Layout.minimumWidth: 0; Layout.fillWidth: true; multiline: true; objectName: "chooseCsvButton"; text: "Dosya seç"; enabled: !imports.busy && !projects.busy; onClicked: picker.open() }
        UiButton { Layout.minimumWidth: 0; Layout.fillWidth: true; multiline: true; text: "İçe aktarma yardımı"; onClicked: panel.helpRequested(this, panel.helpContext) }
    }
    Rectangle {
        Layout.fillWidth: true
        implicitHeight: 64 * Theme.scale
        color: drop.containsDrag ? Theme.background : Theme.surface
        border.color: Theme.accent
        radius: Theme.radius
        Label { anchors.fill: parent; anchors.margins: Theme.md; text: imports.sourcePath || "Tek bir yerel veri dosyasını buraya bırakın."; wrapMode: Text.Wrap; elide: Text.ElideMiddle; verticalAlignment: Text.AlignVCenter }
        DropArea { id: drop; objectName: "csvDropArea"; anchors.fill: parent; onDropped: function(event) { imports.dropFiles(event.urls.map(function(url) { return url.toString() })); event.acceptProposedAction() } }
    }
    ComboBox { objectName: "importFormat"; model: ["csv", "tsv", "json", "jsonl", "xlsx", "parquet", "ods", "sqlite", "ipc", "ipc_stream"]; currentIndex: model.indexOf(imports.formatId); enabled: !imports.busy; onActivated: imports.setFormat(currentText); Layout.fillWidth: true }
    StructuredOptions { visible: imports.formatId !== "csv" && imports.formatId !== "tsv"; Layout.fillWidth: true; onHelpRequested: function(origin, context) { panel.helpRequested(origin, context) } }
    Label { visible: imports.formatId === "csv" || imports.formatId === "tsv"; text: "Algılama yalnız öneridir. Kimlikleri ve uzun numaraları korumak için tüm sütunlar başlangıçta metindir. Ayar veya tür değiştiğinde yeniden önizleyin."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    GridLayout {
        Layout.fillWidth: true
        columns: panel.width > 850 * Theme.scale ? 4 : (panel.width > 500 * Theme.scale ? 2 : 1)
        visible: imports.formatId === "csv" || imports.formatId === "tsv"
        enabled: !imports.busy
        Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "Ayraç" }
        ComboBox { objectName: "importDelimiter"; property string helpContext: "import-delimiter"; model: [",", ";", "Sekme", "|"]; currentIndex: [",", ";", "\t", "|"].indexOf(imports.settings.delimiter); onActivated: imports.setOption("delimiter", [",", ";", "\t", "|"][currentIndex]); Layout.fillWidth: true; Layout.minimumWidth: 0 }
        Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "Encoding" }
        ComboBox { property string helpContext: "import-encoding"; model: ["utf-8-sig", "cp1254", "iso8859-9"]; currentIndex: model.indexOf(imports.settings.encoding); onActivated: imports.setOption("encoding", currentText); Layout.fillWidth: true; Layout.minimumWidth: 0 }
        Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "Başlık kaydı (0: yok)" }
        SpinBox { property string helpContext: "import-header"; from: 0; to: 100; value: imports.settings.header_row; editable: true; onValueModified: imports.setOption("header_row", value); Layout.fillWidth: true; Layout.minimumWidth: 0 }
        Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "Bozuk kayıt" }
        ComboBox { objectName: "importBadRows"; property string helpContext: "import-bad-rows"; model: ["Durdur", "Raporlu karantina"]; currentIndex: imports.settings.bad_rows === "stop" ? 0 : 1; onActivated: imports.setOption("bad_rows", currentIndex ? "quarantine" : "stop"); Layout.fillWidth: true; Layout.minimumWidth: 0 }
        Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "Ondalık" }
        ComboBox { property string helpContext: "import-decimal"; model: [".", ","]; currentIndex: model.indexOf(imports.settings.decimal); onActivated: imports.setOption("decimal", currentText); Layout.fillWidth: true; Layout.minimumWidth: 0 }
        Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "Binlik" }
        ComboBox { model: ["Yok", ".", ",", "Boşluk"]; currentIndex: ["", ".", ",", " "].indexOf(imports.settings.thousands); onActivated: imports.setOption("thousands", ["", ".", ",", " "][currentIndex]); Layout.fillWidth: true; Layout.minimumWidth: 0 }
        Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "Null işaretleri (| ile ayır)" }
        TextField { text: (imports.settings.null_markers || []).join("|"); placeholderText: "Örn. NA|NULL; |NA boşu da null yapar"; onEditingFinished: imports.setOption("null_markers", text); Layout.fillWidth: true; Layout.minimumWidth: 0 }
        Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "Tarih biçimi" }
        TextField { property string helpContext: "import-date"; text: imports.settings.date_format; placeholderText: "%d.%m.%Y %H:%M"; onEditingFinished: imports.setOption("date_format", text); Layout.fillWidth: true; Layout.minimumWidth: 0 }
        Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "Saat dilimi" }
        TextField { text: imports.settings.timezone; placeholderText: "Boş: yerel saat / Europe/Istanbul"; onEditingFinished: imports.setOption("timezone", text); Layout.fillWidth: true; Layout.minimumWidth: 0 }
    }
    Label { visible: imports.formatId === "csv" || imports.formatId === "tsv"; text: "Başlık numarası fiziksel satır değil, CSV kaydıdır. Boş başlıklar adlandırılır, tekrarlar ek alır; özgün başlıklar saklanır. Tarih biçimi Python strptime biçimidir."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    GridLayout {
        columns: panel.width > 600 * Theme.scale ? 2 : 1
        Layout.fillWidth: true
        UiButton { Layout.minimumWidth: 0; Layout.fillWidth: true; multiline: true; objectName: "previewCsvButton"; text: "Aynı kopyayı yeniden önizle"; enabled: !imports.busy; onClicked: imports.refreshPreview() }
        UiButton { Layout.minimumWidth: 0; Layout.fillWidth: true; multiline: true; objectName: "cancelImportButton"; text: "İptal"; enabled: imports.busy; onClicked: imports.cancel() }
    }
    Label { text: imports.errorText; visible: text.length > 0; color: Theme.error; Layout.fillWidth: true; wrapMode: Text.Wrap }
    Label { text: imports.message; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    Label { text: "Sütun türleri · öneriler yalnız sınırlı örneğe dayanır"; wrapMode: Text.Wrap; visible: imports.columns.length > 0; font.bold: true; Layout.fillWidth: true }
    ListView {
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(contentHeight, 180 * Theme.scale)
        clip: true
        model: imports.columns
        ScrollBar.vertical: ScrollBar {}
        delegate: RowLayout {
            id: columnDelegate
            required property var modelData
            required property int index
            width: ListView.view.width
            Label { Layout.minimumWidth: 0; text: modelData.name + " · öneri: " + modelData.suggestion; Layout.fillWidth: true; elide: Text.ElideRight }
            ComboBox { Layout.maximumWidth: panel.width / 2; model: imports.formatId === "csv" || imports.formatId === "tsv" ? ["text", "int64", "float64", "decimal", "date", "datetime", "boolean"] : ["auto", "text", "int64", "float64", "decimal", "date", "datetime", "boolean"]; currentIndex: model.indexOf(modelData.type); enabled: !imports.busy && ["parquet", "ipc", "ipc_stream"].indexOf(imports.formatId) < 0; onActivated: imports.setType(columnDelegate.index, currentText) }
        }
    }
    UiButton { text: "Sütun türlerini sıfırla"; enabled: !imports.busy; onClicked: imports.resetTypes(); Layout.fillWidth: true }
    HorizontalHeaderView { id: header; Layout.fillWidth: true; syncView: table; clip: true }
    TableView {
        id: table
        objectName: "csvPreviewTable"
        Layout.fillWidth: true
        Layout.preferredHeight: 220 * Theme.scale
        clip: true
        model: imports.previewModel
        columnWidthProvider: function(column) { return 180 * Theme.scale }
        rowHeightProvider: function(row) { return 34 * Theme.scale }
        ScrollBar.horizontal: ScrollBar {}
        ScrollBar.vertical: ScrollBar {}
        delegate: Rectangle {
            required property string display
            implicitWidth: 180 * Theme.scale
            implicitHeight: 34 * Theme.scale
            ToolTip.visible: hover.hovered
            ToolTip.text: display
            HoverHandler { id: hover }
            color: Theme.surface
            border.color: Theme.border
            Label { anchors.fill: parent; anchors.margins: Theme.sm; text: parent.display; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
        }
    }
    CheckBox { Layout.fillWidth: true; Layout.minimumWidth: 0; id: portable; text: "Özgün dosyanın taşınabilir kopyasını da projede sakla"; contentItem: Label { text: portable.text; leftPadding: portable.indicator.width + portable.spacing; wrapMode: Text.Wrap; verticalAlignment: Text.AlignVCenter } enabled: !imports.busy }
    Label { text: "Doğrulanmış dataset Parquet olarak her durumda saklanır. Referans seçeneğinde özgün dosya ayrıca kopyalanmaz; taşınabilir seçenekte kopyalanır. İçe aktarma, projenin mevcut değişikliklerini de kaydeder. Sınırlar: 1 GiB kaynak, 256 sütun, kayıt başına 1 MiB; CSV/JSONL/Parquet parça parça işlenir. JSON belge sınırı 64 MiB; XLSX XML parçaları 64 MiB ve toplam açılmış içerik 256 MiB sınırındadır. Bu iki adaptör tam belge belleği kullanır."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    UiButton { Layout.minimumWidth: 0; Layout.fillWidth: true; multiline: true; objectName: "importCsvButton"; primary: true; text: "İçe aktar ve projeye kaydet"; enabled: imports.ready; onClicked: imports.importData(portable.checked) }
    Label { text: imports.datasetSummary; Layout.fillWidth: true; wrapMode: Text.Wrap }
}
