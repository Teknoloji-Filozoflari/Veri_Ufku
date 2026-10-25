import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "FocusScroll.js" as FocusScroll

ColumnLayout {
    id: panel
    objectName: "datasetPanel"
    property alias contractExpanded: contractToggle.checked
    property string pane: "profile"
    property string helpContext: "dataset.profile"
    property bool autoPageRequested: false
    signal helpRequested(var origin, string context)
    signal showValues()
    spacing: Theme.md
    function requestAutoPage() {
        if (panel.autoPageRequested || panel.pane !== "rows" || !panel.visible)
            return
        if (!dataView || dataView.datasets.length === 0 || dataView.pageRowCount > 0)
            return
        if (dataView.busy || projects.busy)
            return
        panel.autoPageRequested = true
        Qt.callLater(function() {
            if (panel.pane === "rows" && !dataView.busy && !projects.busy && dataView.pageRowCount === 0)
                dataView.refresh()
        })
    }
    onPaneChanged: {
        if (panel.pane !== "rows") panel.autoPageRequested = false
        else panel.requestAutoPage()
    }
    onVisibleChanged: if (panel.visible) panel.requestAutoPage()
    UiLabel { text: qsTr("Verini tanı"); font.pixelSize: Theme.heading; font.bold: true; wrapMode: Text.Wrap; Layout.fillWidth: true }
    UiCombo { accessibleLabel: qsTr("Veri kümesi");
        visible: panel.pane !== "profile" || dataView.datasets.length > 1
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
    DatasetOverview { visible: panel.pane === "profile" || panel.pane === "describe"; descriptive: panel.pane === "describe"; Layout.fillWidth: true; onColumnChosen: function(column) { dataView.selectColumn(column); panel.showValues() } }
    SavedColumnNotes { visible: panel.pane === "profile" && notes.length > 0; Layout.fillWidth: true }
    ColumnNotes { visible: panel.pane === "profile" && dataView.datasets.length > 0; Layout.fillWidth: true }
    UiCheckBox { id: contractToggle; objectName: "dataContractToggle"; text: qsTr("Veri sözlüğü, kalite sözleşmesi ve kimlik eşlemeyi aç"); visible: panel.pane === "profile" && dataView.datasets.length > 0; property string helpContext: "contract.schema" }
    Loader { active: contractToggle.checked; visible: active && panel.pane === "profile"; Layout.fillWidth: true; sourceComponent: Component { DataContractPanel {} } }
    ValueInspection { visible: panel.pane === "values"; Layout.fillWidth: true }
    ColumnLayout {
        visible: panel.pane === "rows"
        Layout.fillWidth: true
    UiLabel { objectName: "dataReadHeading"; text: qsTr("Veriyi oku ve incele"); font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiLabel { text: qsTr("Önce kayıtları gözden geçir. Ardından bir sütun seçerek eksik değerleri, farklı değerleri ve uygun sayısal özetleri hesapla."); Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    GridLayout {
        columns: panel.width > 600 * Theme.scale ? 2 : 1
        Layout.fillWidth: true
        UiButton { tone: "cyan"; objectName: "loadDatasetButton"; text: qsTr("Tabloyu aç / yenile"); enabled: !projects.busy && dataView.datasets.length > 0; onClicked: dataView.refresh(); Layout.fillWidth: true; multiline: true }
        UiButton { tone: "mint"; text: qsTr("Veri profili ne işe yarar?"); onClicked: panel.helpRequested(this, "dataset.profile"); Layout.fillWidth: true; multiline: true }
    }
    UiLabel {
        objectName: "datasetPageScope"
        text: qsTr("Görünen sayfa tüm veri değildir. Sayfalama en fazla 200 satır taşır; filtre/sıralama görünüm dönüşümüdür, yeni veri sürümü üretmez.")
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        color: Theme.warning
        font.bold: true
    }
    UiLabel { text: dataView.viewSummary; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    UiLabel { text: qsTr("Tablo salt okunurdur. Arama sütun adlarını arar; gizleme veriyi silmez. Filtre ve sıralama tüm veriye uygulanır. Tablo filtresi profil kapsamından ayrı seçilir. Sütun seçimi diğer ekranlarda korunur."); Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiCheckBox { id: tableTools; objectName: "datasetToolsToggle"; text: qsTr("Sütunlar, sıralama ve filtreler"); checked: true; Layout.fillWidth: true }
    ColumnLayout {
        visible: tableTools.checked
        Layout.fillWidth: true
        spacing: Theme.sm
    UiTextField { Accessible.name: qsTr("Sütun ara"); objectName: "datasetColumnSearch"; placeholderText: qsTr("Sütun ara"); onTextEdited: dataView.searchColumns(text); Layout.fillWidth: true; Layout.minimumWidth: 0 }
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
            UiButton { tone: "cyan"; objectName: "datasetColumn_" + columnItem.modelData.name; text: columnItem.modelData.name + " · " + columnItem.modelData.physical_type; checked: columnItem.modelData.selected; Layout.fillWidth: true; Layout.minimumWidth: 0; onClicked: dataView.selectColumn(columnItem.modelData.id) }
            UiCheckBox { text: qsTr("Gizle"); checked: columnItem.modelData.hidden; enabled: !dataView.busy; onClicked: dataView.hideColumn(columnItem.modelData.id, checked) }
        }
    }
    GridLayout {
        Layout.fillWidth: true
        columns: panel.width > 600 * Theme.scale ? 3 : 1
        UiButton { tone: "cyan"; objectName: "datasetSortAsc"; text: qsTr("Seçili sütunu artan sırala"); enabled: !projects.busy; onClicked: dataView.sort(dataView.selectedColumn, false); Layout.fillWidth: true; multiline: true }
        UiButton { tone: "cyan"; objectName: "datasetSortDesc"; text: qsTr("Seçili sütunu azalan sırala"); enabled: !projects.busy; onClicked: dataView.sort(dataView.selectedColumn, true); Layout.fillWidth: true; multiline: true }
        UiButton { tone: "cyan"; text: qsTr("Kaynak sırasına dön"); enabled: !projects.busy; onClicked: dataView.sort("", false); Layout.fillWidth: true; multiline: true }
    }
    GridLayout {
        Layout.fillWidth: true
        columns: panel.width > 600 * Theme.scale ? 3 : 1
        UiCombo { accessibleLabel: qsTr("Filtre koşulu"); id: predicate; objectName: "datasetFilterOperator"; property var values: ["eq", "ne", "gt", "ge", "lt", "le", "contains", "is_null", "not_null", "is_nan", "is_inf"]; model: [qsTr("Eşit"), qsTr("Eşit değil"), qsTr("Büyük"), qsTr("Büyük/eşit"), qsTr("Küçük"), qsTr("Küçük/eşit"), qsTr("Metin içerir"), qsTr("Null (eksik)"), qsTr("Null değil"), "NaN", qsTr("Sonsuz (+/−)")]; Layout.fillWidth: true; Layout.minimumWidth: 0 }
        UiTextField { Accessible.name: qsTr("Filtre değeri"); id: filterValue; objectName: "datasetFilterValue"; placeholderText: qsTr("Seçili sütunda filtre değeri"); Layout.fillWidth: true; Layout.minimumWidth: 0 }
        UiButton { tone: "cyan"; objectName: "datasetAddFilter"; text: qsTr("Filtre ekle (VE)"); enabled: !projects.busy; onClicked: dataView.addFilter(dataView.selectedColumn, predicate.values[predicate.currentIndex], filterValue.text); Layout.fillWidth: true; multiline: true }
    }
    UiButton { tone: "cyan"; objectName: "datasetClearFilters"; text: qsTr("Tüm filtreleri kaldır"); enabled: !projects.busy; onClicked: dataView.clearFilters(); Layout.fillWidth: true }
    }
    UiLabel { text: dataView.errorText; visible: text.length > 0; color: Theme.error; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiLabel { text: dataView.message; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    HorizontalHeaderView {
        objectName: "datasetHeader"
        Layout.fillWidth: true
        syncView: table
        clip: true
        resizableColumns: true
        activeFocusOnTab: false
        keyNavigationEnabled: false
        delegate: Rectangle {
            required property var display
            implicitWidth: 200 * Theme.scale
            implicitHeight: 52 * Theme.scale
            color: Theme.raised
            UiLabel {
                anchors.fill: parent
                anchors.margins: Theme.sm
                text: parent.display
                font.bold: true
                font.pixelSize: Theme.small
                wrapMode: Text.WordWrap
                maximumLineCount: 3
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
            }
            Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.border }
        }
    }
    TableView {
        id: table
        objectName: "datasetTable"
        Accessible.name: qsTr("Veri tablosu, salt okunur; ok tuşlarıyla kayıt seç")
        Accessible.role: Accessible.Table
        activeFocusOnTab: true
        onActiveFocusChanged: if (activeFocus) Qt.callLater(function() { FocusScroll.reveal(table) })
        keyNavigationEnabled: false
        property int keyboardRow: 0
        function chooseRow(row) {
            if (!dataView.pageRowCount) return
            keyboardRow = Math.max(0, Math.min(dataView.pageRowCount - 1, row))
            dataView.selectRow(keyboardRow)
            positionViewAtRow(keyboardRow, TableView.Contain)
        }
        Keys.onDownPressed: chooseRow(keyboardRow + 1)
        Keys.onUpPressed: chooseRow(keyboardRow - 1)
        Keys.onSpacePressed: dataView.selectRow(keyboardRow)
        Keys.onPressed: function(event) {
            if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_C) {
                dataView.copyVisibleSelection()
                event.accepted = true
            }
        }
        Connections {
            target: dataView.tableModel
            function onModelReset() { table.keyboardRow = 0 }
            function onColumnsChanged() { table.clearColumnWidths(); table.forceLayout() }
        }
        Layout.fillWidth: true
        Layout.preferredHeight: Math.max(420, Math.min(560, panel.height > 0 ? panel.height * 0.55 : 480)) * Theme.scale
        clip: true
        reuseItems: true
        model: dataView.tableModel
        columnWidthProvider: function(column) { let explicit = explicitColumnWidth(column); return explicit >= 0 ? Math.max(96 * Theme.scale, explicit) : 200 * Theme.scale }
        rowHeightProvider: function(row) { return 34 * Theme.scale }
        ScrollBar.horizontal: ScrollBar {}
        ScrollBar.vertical: ScrollBar {}
        delegate: Rectangle {
            required property string display
            required property string rowId
            required property string sourceRecordId
            required property int row
            required property bool missing
            implicitWidth: 180 * Theme.scale
            implicitHeight: 34 * Theme.scale
            color: dataView.selectedRowIds.indexOf(rowId) >= 0 ? Theme.cyanSurface : hover.hovered ? Theme.hover : row % 2 ? Theme.alternateRow : Theme.surface
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border; opacity: 0.45 }
            UiLabel { anchors.fill: parent; anchors.margins: Theme.sm; text: parent.missing ? qsTr("∅ eksik") : parent.display; color: parent.missing ? Theme.muted : Theme.text; font.italic: parent.missing; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
            TapHandler { onTapped: { table.keyboardRow = parent.row; dataView.selectRow(parent.row); table.forceActiveFocus() } }
            HoverHandler { id: hover }
            ToolTip.visible: hover.hovered
            ToolTip.text: (missing ? qsTr("Eksik değer (null)") : display) + "\nRowId " + rowId
        }
    }
    Flow {
        Layout.fillWidth: true
        spacing: Theme.sm
        UiButton { objectName: "datasetCopySelection"; text: qsTr("Görünen seçimi kopyala (JSON)"); enabled: dataView.selectedRowIds.length > 0; onClicked: dataView.copyVisibleSelection(); width: Math.min(implicitWidth, parent.width) }
        UiButton { objectName: "datasetResetWidths"; text: qsTr("Sütun genişliklerini sıfırla"); onClicked: { table.clearColumnWidths(); table.forceLayout() } width: Math.min(implicitWidth, parent.width) }
    }
    UiLabel { text: qsTr("Başlık kenarını sürükleyerek sütunu boyutlandırın. ∅ eksik değerdir; kopyalama yalnız bu sayfadaki görünen metni içerir."); color: Theme.secondary; font.pixelSize: Theme.small; Layout.fillWidth: true; wrapMode: Text.Wrap }
    GridLayout {
        Layout.fillWidth: true
        columns: panel.width > 600 * Theme.scale ? 3 : 1
        UiButton { tone: "cyan"; objectName: "datasetPreviousPage"; text: qsTr("Önceki 200"); enabled: !projects.busy && dataView.pageOffset > 0; onClicked: dataView.goPage(Math.max(0, dataView.pageOffset - 200)); Layout.fillWidth: true }
        UiButton { tone: "cyan"; objectName: "datasetNextPage"; text: qsTr("Sonraki 200"); enabled: !projects.busy && dataView.pageOffset + 200 < dataView.totalRows; onClicked: dataView.goPage(dataView.pageOffset + 200); Layout.fillWidth: true }
        UiButton { tone: "cyan"; objectName: "datasetCancel"; text: qsTr("Sorgu / profili iptal et"); enabled: dataView.busy; onClicked: dataView.cancel(); Layout.fillWidth: true; multiline: true }
    }
    UiLabel { text: dataView.selectionText; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
    }
    ColumnDetails { id: columnDetail; visible: panel.pane === "rows"; Layout.fillWidth: true; onHelpRequested: function(origin, context) { panel.helpRequested(origin, context) } }
}
