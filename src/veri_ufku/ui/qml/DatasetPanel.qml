import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "datasetPanel"
    property string helpContext: "dataset.profile"
    signal helpRequested(var origin, string context)
    spacing: Theme.md
    Label { text: "Veri tablosu ve profil"; font.pixelSize: Theme.heading; font.bold: true; wrapMode: Text.Wrap; Layout.fillWidth: true }
    ComboBox {
        id: datasetPicker
        objectName: "datasetPicker"
        model: dataView.datasets
        currentIndex: { let values = dataView.datasets; for (let i = 0; i < values.length; i++) if (values[i].id === dataView.selectedDataset) return i; return -1 }
        textRole: "label"
        valueRole: "id"
        onActivated: dataView.selectDataset(currentValue)
        Layout.fillWidth: true
        Layout.minimumWidth: 0
    }
    GridLayout {
        columns: panel.width > 600 * Theme.scale ? 2 : 1
        Layout.fillWidth: true
        UiButton { objectName: "loadDatasetButton"; text: "Tabloyu aç / yenile"; enabled: !projects.busy && dataView.datasets.length > 0; onClicked: dataView.refresh(); Layout.fillWidth: true; multiline: true }
        UiButton { text: "Veri profili ne işe yarar?"; onClicked: panel.helpRequested(this, "dataset.profile"); Layout.fillWidth: true; multiline: true }
    }
    Label { text: dataView.viewSummary; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    Label { text: "Hücreler salt okunurdur. Görünen hücre metni en fazla256 karakter, sayfa metni4MiB ile sınırlıdır. Arama yalnız sütun listesini arar. Gizleme veriyi silmez. Filtre ve sıralama tüm dataset’e uygulanır; sayfa sırası kalıcı kimlik değildir."; Layout.fillWidth: true; wrapMode: Text.Wrap }
    TextField { objectName: "datasetColumnSearch"; placeholderText: "Sütun ara"; onTextEdited: dataView.searchColumns(text); Layout.fillWidth: true; Layout.minimumWidth: 0 }
    ListView {
        objectName: "datasetColumnList"
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(contentHeight, 170 * Theme.scale)
        clip: true
        model: dataView.columns
        ScrollBar.vertical: ScrollBar {}
        delegate: RowLayout {
            id: columnItem
            required property var modelData
            width: ListView.view.width
            UiButton { text: columnItem.modelData.name + " · " + columnItem.modelData.physical_type; checked: columnItem.modelData.selected; Layout.fillWidth: true; Layout.minimumWidth: 0; onClicked: dataView.selectColumn(columnItem.modelData.id) }
            CheckBox { text: "Gizle"; checked: columnItem.modelData.hidden; enabled: !dataView.busy; onClicked: dataView.hideColumn(columnItem.modelData.id, checked) }
        }
    }
    GridLayout {
        Layout.fillWidth: true
        columns: panel.width > 600 * Theme.scale ? 3 : 1
        UiButton { objectName: "datasetSortAsc"; text: "Seçili sütunu artan sırala"; enabled: !projects.busy; onClicked: dataView.sort(dataView.selectedColumn, false); Layout.fillWidth: true; multiline: true }
        UiButton { objectName: "datasetSortDesc"; text: "Seçili sütunu azalan sırala"; enabled: !projects.busy; onClicked: dataView.sort(dataView.selectedColumn, true); Layout.fillWidth: true; multiline: true }
        UiButton { text: "Kaynak sırasına dön"; enabled: !projects.busy; onClicked: dataView.sort("", false); Layout.fillWidth: true; multiline: true }
    }
    GridLayout {
        Layout.fillWidth: true
        columns: panel.width > 600 * Theme.scale ? 3 : 1
        ComboBox { id: predicate; objectName: "datasetFilterOperator"; property var values: ["eq", "ne", "gt", "ge", "lt", "le", "contains", "is_null", "not_null", "is_nan", "is_inf"]; model: ["Eşit", "Eşit değil", "Büyük", "Büyük/eşit", "Küçük", "Küçük/eşit", "Metin içerir", "Null (eksik)", "Null değil", "NaN", "Sonsuz (+/−)"]; Layout.fillWidth: true; Layout.minimumWidth: 0 }
        TextField { id: filterValue; objectName: "datasetFilterValue"; placeholderText: "Seçili sütunda filtre değeri"; Layout.fillWidth: true; Layout.minimumWidth: 0 }
        UiButton { objectName: "datasetAddFilter"; text: "Filtre ekle (VE)"; enabled: !projects.busy; onClicked: dataView.addFilter(dataView.selectedColumn, predicate.values[predicate.currentIndex], filterValue.text); Layout.fillWidth: true; multiline: true }
    }
    UiButton { objectName: "datasetClearFilters"; text: "Tüm filtreleri kaldır"; enabled: !projects.busy; onClicked: dataView.clearFilters(); Layout.fillWidth: true }
    Label { text: dataView.errorText; visible: text.length > 0; color: Theme.error; Layout.fillWidth: true; wrapMode: Text.Wrap }
    Label { text: dataView.message; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    HorizontalHeaderView { Layout.fillWidth: true; syncView: table; clip: true }
    TableView {
        id: table
        objectName: "datasetTable"
        Layout.fillWidth: true
        Layout.preferredHeight: 300 * Theme.scale
        clip: true
        reuseItems: true
        model: dataView.tableModel
        columnWidthProvider: function(column) { return 180 * Theme.scale }
        rowHeightProvider: function(row) { return 34 * Theme.scale }
        ScrollBar.horizontal: ScrollBar {}
        ScrollBar.vertical: ScrollBar {}
        delegate: Rectangle {
            required property string display
            required property string rowId
            required property string sourceRecordId
            required property int row
            implicitWidth: 180 * Theme.scale
            implicitHeight: 34 * Theme.scale
            color: Theme.surface
            border.color: Theme.border
            Label { anchors.fill: parent; anchors.margins: Theme.sm; text: parent.display; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
            TapHandler { onTapped: dataView.selectRow(parent.row) }
            HoverHandler { id: hover }
            ToolTip.visible: hover.hovered
            ToolTip.text: display + "\nRowId " + rowId
        }
    }
    GridLayout {
        Layout.fillWidth: true
        columns: panel.width > 600 * Theme.scale ? 3 : 1
        UiButton { objectName: "datasetPreviousPage"; text: "Önceki 200"; enabled: !projects.busy && dataView.pageOffset > 0; onClicked: dataView.goPage(Math.max(0, dataView.pageOffset - 200)); Layout.fillWidth: true }
        UiButton { objectName: "datasetNextPage"; text: "Sonraki 200"; enabled: !projects.busy && dataView.pageOffset + 200 < dataView.totalRows; onClicked: dataView.goPage(dataView.pageOffset + 200); Layout.fillWidth: true }
        UiButton { objectName: "datasetCancel"; text: "Sorgu / profili iptal et"; enabled: dataView.busy; onClicked: dataView.cancel(); Layout.fillWidth: true; multiline: true }
    }
    Label { text: dataView.selectionText; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
    ColumnDetails { Layout.fillWidth: true; onHelpRequested: function(origin, context) { panel.helpRequested(origin, context) } }
}
