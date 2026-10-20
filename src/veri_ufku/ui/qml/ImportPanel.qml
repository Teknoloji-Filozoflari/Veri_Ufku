import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "FocusScroll.js" as FocusScroll

ColumnLayout {
    id: panel
    objectName: "csvImportPanel"
    property string helpContext: ["netcdf", "zarr", "hdf5_array"].indexOf(imports.formatId) >= 0 ? "array-dimensions" : ["postgresql", "mysql", "mariadb", "duckdb", "http", "s3", "tile", "geocoding"].indexOf(imports.formatId) >= 0 ? "connector-connection" : ["parquet_dataset", "arrow_dataset", "avro", "orc", "hdf5", "xml", "fixed_width", "spss", "stata", "sas"].indexOf(imports.formatId) >= 0 ? "import.phase30" : ["ods", "sqlite", "ipc", "ipc_stream"].indexOf(imports.formatId) >= 0 ? "import.phase11" : imports.formatId === "json" ? "import.json" : imports.formatId === "jsonl" ? "import.jsonl" : imports.formatId === "xlsx" ? "import.xlsx" : imports.formatId === "parquet" ? "import.parquet" : "import.csv"
    signal helpRequested(var origin, string context)
    signal projectRequested()
    property bool detailsOpen: false
    onVisibleChanged: if (visible) detailsOpen = false
    readonly property bool showAdvanced: detailsOpen
    Layout.minimumWidth: 0
    spacing: Theme.md
    FileDialog {
        id: picker
        objectName: "csvFileDialog"
        title: qsTr("Veri dosyası seç")
        nameFilters: ["Veri (*.csv *.tsv *.json *.jsonl *.ndjson *.xlsx *.parquet *.ods *.sqlite *.db *.feather *.arrow *.ipc *.arrows *.avro *.orc *.h5 *.hdf5 *.nc *.netcdf *.xml *.fwf *.sav *.zsav *.dta *.sas7bdat *.xpt *.gz *.zip)", "Tüm dosyalar (*)"]
        onAccepted: imports.choose(selectedFile.toString())
    }
    FolderDialog {
        id: datasetPicker
        objectName: "datasetFolderDialog"
        title: "Parquet, Arrow veya yerel Zarr klasörü seç"
        onAccepted: imports.choose(selectedFolder.toString())
    }
    function openPicker() { picker.open() }
    UiLabel { Layout.minimumWidth: 0; wrapMode: Text.Wrap; text: qsTr("Veri içe aktar"); font.pixelSize: Theme.heading; font.bold: true; Layout.fillWidth: true }
    UiLabel { visible: !projects.opened; text: qsTr("Dosyanı aktarmak için önce bir proje oluştur veya aç."); Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    UiButton { objectName: "importProjectButton"; visible: !projects.opened; text: qsTr("Proje oluştur / aç"); tone: "cyan"; onClicked: panel.projectRequested() }
    UiLabel { text: qsTr("Dosyanı seç veya aşağıya bırak. Uygulama dosya biçimini algılar ve önizlemeyi hazırlar. Kaynak dosyan değişmez."); Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    UiButton { objectName: "chooseCsvButton"; text: qsTr("Dosya seç"); tone: "cyan"; enabled: !imports.busy && !projects.busy; onClicked: picker.open() }
    UiButton { objectName: "chooseDatasetFolder"; text: "Dataset klasörü seç"; property string helpContext: "import-partition"; enabled: !imports.busy && !projects.busy; onClicked: datasetPicker.open() }
    Rectangle {
        enabled: !imports.busy && !projects.busy
        Layout.fillWidth: true
        implicitHeight: 64 * Theme.scale
        color: drop.containsDrag ? Theme.background : Theme.surface
        border.color: Theme.accent
        radius: Theme.radius
        UiLabel { anchors.fill: parent; anchors.margins: Theme.md; text: imports.sourcePath || qsTr("Tek bir yerel veri dosyasını buraya bırakın."); wrapMode: Text.Wrap; elide: Text.ElideMiddle; verticalAlignment: Text.AlignVCenter }
        DropArea { id: drop; objectName: "csvDropArea"; anchors.fill: parent; onDropped: function(event) { imports.dropFiles(event.urls.map(function(url) { return url.toString() })); event.acceptProposedAction() } }
    }
    UiLabel { text: imports.errorText; visible: text.length > 0; color: Theme.error; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiLabel { objectName: "importStatus"; visible: text.length > 0; text: imports.statusText; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    UiLabel { visible: text.length > 0; text: imports.previewWarnings; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.warning }
    UiButton { objectName: "cancelImportButton"; visible: imports.busy; text: qsTr("İptal"); onClicked: imports.cancel() }
    UiButton { objectName: "importAdvancedButton"; text: panel.showAdvanced ? qsTr("Gelişmiş · ayrıntılar açık") : qsTr("Gelişmiş"); checked: panel.showAdvanced; tone: "violet"; onClicked: panel.detailsOpen = !panel.detailsOpen }
    ColumnLayout {
        objectName: "importAdvancedOptions"
        visible: panel.showAdvanced
        Layout.fillWidth: true
        spacing: Theme.md
        Loader { property bool created: false; active: panel.showAdvanced || created; onLoaded: created = true; Layout.fillWidth: true; sourceComponent: ConnectorPanel { Layout.fillWidth: true } }
        UiLabel { text: qsTr("Dosya yolu (dosya seçicisine alternatif)"); Layout.fillWidth: true; wrapMode: Text.Wrap }
        UiTextField { id: pathInput; objectName: "importPathInput"; Accessible.name: qsTr("Yerel veri dosyası yolu"); placeholderText: "/home/…/veri.csv"; Layout.fillWidth: true; enabled: !projects.busy; onAccepted: imports.choose(text) }
        UiButton { objectName: "importPathOpen"; text: qsTr("Bu dosyayı önizle"); enabled: !projects.busy && pathInput.text.length > 0; onClicked: imports.choose(pathInput.text) }
        UiCombo { accessibleLabel: qsTr("Dosya biçimi"); objectName: "importFormat"; Accessible.name: qsTr("Dosya biçimi"); visible: ["postgresql", "mysql", "mariadb", "duckdb", "http", "s3", "tile", "geocoding"].indexOf(imports.formatId) < 0; model: imports.formats; currentIndex: model.indexOf(imports.formatId); enabled: !imports.busy; onActivated: imports.setFormat(currentText); Layout.fillWidth: true }
        GeoImportOptions { visible: ["geojson","geopackage","shapefile","geoparquet","geotiff","tile"].indexOf(imports.formatId)>=0; Layout.fillWidth:true; onHelpRequested:function(origin,context){panel.helpRequested(origin,context)} }
        StructuredOptions { visible: imports.formatId !== "csv" && imports.formatId !== "tsv" && ["postgresql", "mysql", "mariadb", "duckdb", "http", "s3", "tile", "geocoding"].indexOf(imports.formatId) < 0; Layout.fillWidth: true; onHelpRequested: function(origin, context) { panel.helpRequested(origin, context) } }
        UiLabel { visible: imports.formatId === "csv" || imports.formatId === "tsv"; text: qsTr("Türler dosyanın tamamında algılanır. Başında sıfır olan kodlar ve karışık değerler metin olarak korunur. Ayar veya tür değiştiğinde yeniden önizleyin."); Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
        GridLayout {
            Layout.fillWidth: true
            columns: panel.width > 850 * Theme.scale ? 4 : (panel.width > 500 * Theme.scale ? 2 : 1)
            visible: imports.formatId === "csv" || imports.formatId === "tsv"
            enabled: !imports.busy
            UiLabel { Layout.fillWidth: true; wrapMode: Text.Wrap; text: qsTr("Ayraç") }
            UiCombo { accessibleLabel: qsTr("Ayraç"); objectName: "importDelimiter"; property string helpContext: "import-delimiter"; model: [",", ";", "Sekme", "|"]; currentIndex: [",", ";", "\t", "|"].indexOf(imports.settings.delimiter); onActivated: imports.setOption("delimiter", [",", ";", "\t", "|"][currentIndex]); Layout.fillWidth: true; Layout.minimumWidth: 0 }
            UiLabel { Layout.fillWidth: true; wrapMode: Text.Wrap; text: qsTr("Encoding") }
            UiCombo { accessibleLabel: qsTr("Encoding"); property string helpContext: "import-encoding"; model: ["utf-8-sig", "cp1254", "iso8859-9"]; currentIndex: model.indexOf(imports.settings.encoding); onActivated: imports.setOption("encoding", currentText); Layout.fillWidth: true; Layout.minimumWidth: 0 }
            UiLabel { Layout.fillWidth: true; wrapMode: Text.Wrap; text: qsTr("Başlık kaydı (0: yok)") }
            UiSpinBox { objectName: "importHeaderRow"; Accessible.name: qsTr("Başlık kaydı (0: yok)"); property string helpContext: "import-header"; from: 0; to: 100; value: imports.settings.header_row; editable: true; onValueModified: imports.setOption("header_row", value); Layout.fillWidth: true; Layout.minimumWidth: 0 }
            UiLabel { Layout.fillWidth: true; wrapMode: Text.Wrap; text: qsTr("Bozuk kayıt") }
            UiCombo { accessibleLabel: qsTr("Bozuk kayıt"); objectName: "importBadRows"; property string helpContext: "import-bad-rows"; model: [qsTr("Durdur"), "Raporlu karantina"]; currentIndex: imports.settings.bad_rows === "stop" ? 0 : 1; onActivated: imports.setOption("bad_rows", currentIndex ? "quarantine" : "stop"); Layout.fillWidth: true; Layout.minimumWidth: 0 }
            UiLabel { Layout.fillWidth: true; wrapMode: Text.Wrap; text: qsTr("Ondalık") }
            UiCombo { accessibleLabel: qsTr("Ondalık"); objectName: "importDecimal"; property string helpContext: "import-decimal"; model: [".", ","]; currentIndex: model.indexOf(imports.settings.decimal); onActivated: imports.setOption("decimal", currentText); Layout.fillWidth: true; Layout.minimumWidth: 0 }
            UiLabel { Layout.fillWidth: true; wrapMode: Text.Wrap; text: qsTr("Binlik") }
            UiCombo { accessibleLabel: qsTr("Binlik"); model: [qsTr("Yok"), ".", ",", qsTr("Boşluk")]; currentIndex: ["", ".", ",", " "].indexOf(imports.settings.thousands); onActivated: imports.setOption("thousands", ["", ".", ",", " "][currentIndex]); Layout.fillWidth: true; Layout.minimumWidth: 0 }
            UiLabel { Layout.fillWidth: true; wrapMode: Text.Wrap; text: qsTr("Null işaretleri (| ile ayır)") }
            UiTextField { Accessible.name: qsTr("Null işaretleri (| ile ayır)"); objectName: "importNullMarkers"; text: (imports.settings.null_markers || []).join("|"); placeholderText: qsTr("Örn. NA|NULL; |NA boşu da null yapar"); onEditingFinished: imports.setOption("null_markers", text); Layout.fillWidth: true; Layout.minimumWidth: 0 }
            UiLabel { Layout.fillWidth: true; wrapMode: Text.Wrap; text: qsTr("Tarih biçimi") }
            UiTextField { Accessible.name: qsTr("Tarih biçimi"); property string helpContext: "import-date"; text: imports.settings.date_format; placeholderText: "%d.%m.%Y %H:%M"; onEditingFinished: imports.setOption("date_format", text); Layout.fillWidth: true; Layout.minimumWidth: 0 }
            UiLabel { Layout.fillWidth: true; wrapMode: Text.Wrap; text: qsTr("Saat dilimi") }
            UiTextField { Accessible.name: qsTr("Saat dilimi"); text: imports.settings.timezone; placeholderText: qsTr("Boş: yerel saat / Europe/Istanbul"); onEditingFinished: imports.setOption("timezone", text); Layout.fillWidth: true; Layout.minimumWidth: 0 }
        }
        UiLabel { visible: imports.formatId === "csv" || imports.formatId === "tsv"; text: qsTr("Başlık numarası fiziksel satır değil, CSV kaydıdır. Boş başlıklar adlandırılır, tekrarlar ek alır; özgün başlıklar saklanır. Tarih biçimi Python strptime biçimidir."); Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
        UiButton { objectName: "previewCsvButton"; text: qsTr("Önizlemeyi güncelle"); enabled: !imports.busy && imports.sourcePath.length > 0; onClicked: imports.refreshPreview() }
        UiLabel { text: imports.message; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }

        UiLabel { text: qsTr("Sütun türleri"); wrapMode: Text.Wrap; visible: imports.columns.length > 0; font.bold: true; Layout.fillWidth: true }
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
                UiLabel { Layout.minimumWidth: 0; text: modelData.name + " · öneri: " + modelData.suggestion; Layout.fillWidth: true; elide: Text.ElideRight }
                UiCombo { accessibleLabel: qsTr("Sütun türleri"); objectName: "importType_" + modelData.name; Accessible.name: "Sütun türü: " + modelData.name; Layout.maximumWidth: panel.width / 2; model: imports.formatId === "csv" || imports.formatId === "tsv" ? ["text", "int64", "float64", "decimal", "date", "datetime", "boolean"] : ["auto", "text", "int64", "float64", "decimal", "date", "datetime", "boolean"]; currentIndex: model.indexOf(modelData.type); enabled: !imports.busy && ["postgresql", "mysql", "mariadb", "duckdb", "http", "s3", "parquet", "ipc", "ipc_stream", "parquet_dataset", "arrow_dataset", "avro", "orc", "hdf5", "spss", "stata", "sas", "netcdf", "zarr", "hdf5_array"].indexOf(imports.formatId) < 0; onActivated: { FocusScroll.retainPickerFocus(this); imports.setType(columnDelegate.index, currentText) } }
            }
        }
        UiButton { text: qsTr("Sütun türlerini sıfırla"); enabled: !imports.busy; onClicked: imports.resetTypes(); Layout.fillWidth: true }
    }
    HorizontalHeaderView { visible: imports.columns.length > 0; id: header; Layout.fillWidth: true; syncView: table; clip: true; activeFocusOnTab: false; keyNavigationEnabled: false }
    TableView {
        id: table
        visible: imports.columns.length > 0
        objectName: "csvPreviewTable"
        Accessible.name: qsTr("İçe aktarma önizlemesi, sınırlı örnek, salt okunur")
        Accessible.role: Accessible.Table
        activeFocusOnTab: true
        Keys.onTabPressed: nextItemInFocusChain().forceActiveFocus()
        Keys.onBacktabPressed: nextItemInFocusChain(false).forceActiveFocus()
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(220, Math.max(72, table.rows * 34 + 12)) * Theme.scale
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
            UiLabel { anchors.fill: parent; anchors.margins: Theme.sm; text: parent.display; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
        }
    }
    UiCheckBox { visible: panel.showAdvanced; Layout.fillWidth: true; Layout.minimumWidth: 0; id: portable; text: qsTr("Özgün dosyanın taşınabilir kopyasını da projede sakla"); contentItem: UiLabel { text: portable.text; leftPadding: portable.indicator.width + portable.spacing; wrapMode: Text.Wrap; verticalAlignment: Text.AlignVCenter } enabled: !imports.busy }
    UiLabel { visible: panel.showAdvanced; text: qsTr("Doğrulanmış dataset Parquet olarak her durumda saklanır. Referans seçeneğinde özgün dosya ayrıca kopyalanmaz; taşınabilir seçenekte kopyalanır. İçe aktarma, projenin mevcut değişikliklerini de kaydeder. Sınırlar: 1 GiB kaynak, 256 sütun, kayıt başına 1 MiB; CSV/JSONL/Parquet parça parça işlenir. JSON belge sınırı 64 MiB; XLSX XML parçaları 64 MiB ve toplam açılmış içerik 256 MiB sınırındadır. Bu iki adaptör tam belge belleği kullanır."); Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    UiButton { Layout.minimumWidth: 0; Layout.fillWidth: true; multiline: true; objectName: "importCsvButton"; primary: true; text: qsTr("İçe aktar ve projeye kaydet"); enabled: imports.ready; onClicked: imports.importData(portable.checked) }
    UiLabel { visible: panel.showAdvanced; text: imports.datasetSummary; Layout.fillWidth: true; wrapMode: Text.Wrap }
}
