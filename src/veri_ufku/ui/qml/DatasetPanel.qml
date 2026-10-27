import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "FocusScroll.js" as FocusScroll

ColumnLayout {
    id: panel
    objectName: "datasetPanel"
    property alias contractExpanded: contractToggle.checked
    property string pane: "profile"
    property bool autoLoad: false
    property bool inspectMode: false
    property string helpContext: "dataset.profile"
    property bool autoPageRequested: false
    signal helpRequested(var origin, string context)
    signal showValues()
    spacing: Theme.md
    function missingCountFor(name) {
        let findings = (dataView.qualityResult && dataView.qualityResult.findings) || []
        for (let i = 0; i < findings.length; i++)
            if (findings[i].code === "missing" && findings[i].column === name)
                return findings[i].count || 0
        let inv = (dataView.inventoryResult && dataView.inventoryResult.columns) || []
        for (let j = 0; j < inv.length; j++)
            if (inv[j].name === name)
                return (inv[j]["null"] || 0) + (inv[j].nan || 0)
        return 0
    }
    function requestAutoPage() {
        if (!panel.autoLoad || panel.autoPageRequested || panel.pane !== "rows" || !panel.visible)
            return
        if (!dataView || dataView.datasets.length === 0 || dataView.pageRowCount > 0)
            return
        if (dataView.busy || projects.busy)
            return
        panel.autoPageRequested = true
        Qt.callLater(function() {
            if (panel.autoLoad && panel.pane === "rows" && !dataView.busy && !projects.busy && dataView.pageRowCount === 0)
                dataView.refresh()
        })
    }
    onPaneChanged: {
        if (panel.pane !== "rows") panel.autoPageRequested = false
        else panel.requestAutoPage()
    }
    onVisibleChanged: if (panel.visible) panel.requestAutoPage()
    onAutoLoadChanged: if (panel.autoLoad) panel.requestAutoPage()
    Connections {
        target: projects
        function onChanged() {
            if (!projects.busy && !dataView.busy)
                panel.requestAutoPage()
        }
    }
    UiLabel { text: qsTr("Verini tanı"); font.pixelSize: Theme.heading; font.bold: true; wrapMode: Text.Wrap; Layout.fillWidth: true; visible: panel.pane !== "rows" }
    UiCombo { accessibleLabel: qsTr("Veri kümesi");
        visible: panel.pane !== "rows" && (panel.pane !== "profile" || dataView.datasets.length > 1) || (panel.pane === "rows" && dataView.datasets.length > 1)
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
        Layout.fillHeight: true
    UiLabel { objectName: "dataReadHeading"; visible: false; text: qsTr("Veriyi oku ve incele"); font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiLabel { visible: false; text: qsTr("Önce kayıtları gözden geçir. Ardından bir sütun seçerek eksik değerleri, farklı değerleri ve uygun sayısal özetleri hesapla."); Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    GridLayout {
        visible: false
        columns: panel.width > 600 * Theme.scale ? 2 : 1
        Layout.fillWidth: true
        UiButton { tone: "cyan"; objectName: "loadDatasetButton"; text: qsTr("Tabloyu aç / yenile"); enabled: !projects.busy && dataView.datasets.length > 0; onClicked: dataView.refresh(); Layout.fillWidth: true; multiline: true }
        UiButton { visible: false; tone: "mint"; text: qsTr("Veri profili ne işe yarar?"); onClicked: panel.helpRequested(this, "dataset.profile"); Layout.fillWidth: true; multiline: true }
    }
    UiLabel {
        objectName: "datasetPageNote"
        visible: false
        text: qsTr("Görünen sayfa tüm veri değildir. Sayfalama en fazla 200 satır taşır; filtre/sıralama görünüm dönüşümüdür, yeni veri sürümü üretmez.")
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        color: Theme.warning
        font.bold: true
    }
    UiLabel { visible: false; text: dataView.viewSummary; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    UiLabel { visible: false; text: qsTr("Tablo salt okunurdur. Arama sütun adlarını arar; gizleme veriyi silmez. Filtre ve sıralama tüm veriye uygulanır. Tablo filtresi profil kapsamından ayrı seçilir. Sütun seçimi diğer ekranlarda korunur."); Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiCheckBox { id: tableTools; objectName: "datasetToolsToggle"; visible: false; text: qsTr("Sütunlar, sıralama ve filtreler"); checked: false; Layout.fillWidth: true }
    ColumnLayout {
        visible: false
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
    UiLabel { text: dataView.message; visible: dataView.busy && text.length > 0; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    ColumnHeaderMenu { id: columnHeaderMenu }
    HorizontalHeaderView {
        objectName: "datasetHeader"
        Layout.fillWidth: true
        syncView: table
        clip: true
        resizableColumns: true
        activeFocusOnTab: false
        keyNavigationEnabled: false
        delegate: Rectangle {
            id: headerCell
            required property var display
            required property int column
            readonly property var parts: String(display === undefined ? "" : display).split(" · ")
            readonly property string columnName: parts.length > 0 ? parts[0] : ""
            readonly property string typeBadge: parts.length > 1 ? parts[1] : ""
            readonly property string roleBadge: parts.length > 2 ? parts[2] : ""
            implicitWidth: 120
            implicitHeight: headerContent.implicitHeight + 10
            color: Theme.raised
            ColumnLayout {
                id: headerContent
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.margins: 4
                spacing: 2
                UiLabel {
                    objectName: "datasetHeaderMark"
                    Layout.fillWidth: true
                    text: headerCell.columnName
                    font.bold: true
                    font.pixelSize: Theme.small
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }
                UiLabel {
                    visible: headerCell.typeBadge.length > 0 || headerCell.roleBadge.length > 0
                    Layout.fillWidth: true
                    text: {
                        let bits = []
                        if (headerCell.typeBadge) bits.push(headerCell.typeBadge)
                        if (headerCell.roleBadge) bits.push(headerCell.roleBadge)
                        if (panel.inspectMode) {
                            let miss = panel.missingCountFor(headerCell.columnName)
                            if (miss > 0) bits.push(miss + qsTr(" eksik"))
                        }
                        return bits.join(" · ")
                    }
                    color: Theme.secondary
                    font.pixelSize: Theme.small
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }
            }
            TapHandler {
                onTapped: columnHeaderMenu.openFor(parent.column)
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
        Layout.fillHeight: true
        Layout.minimumHeight: 160
        clip: true
        reuseItems: true
        model: dataView.tableModel
        columnWidthProvider: function(column) {
            let explicit = explicitColumnWidth(column)
            if (explicit >= 0)
                return Math.max(72, explicit)
            let count = Math.max(1, table.columns)
            return Math.max(72, Math.floor(table.width / count))
        }
        rowHeightProvider: function(row) { return 24 }
        onWidthChanged: if (columns > 0) forceLayout()
        ScrollBar.horizontal: ScrollBar {}
        ScrollBar.vertical: ScrollBar {}
        delegate: Rectangle {
            required property string display
            required property string rowId
            required property string sourceRecordId
            required property int row
            required property bool missing
            implicitWidth: 72
            implicitHeight: 24
            color: dataView.selectedRowIds.indexOf(rowId) >= 0 ? Theme.cyanSurface : hover.hovered ? Theme.hover : row % 2 ? Theme.alternateRow : Theme.surface
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border; opacity: 0.45 }
            UiLabel { anchors.fill: parent; anchors.leftMargin: 6; anchors.rightMargin: 6; text: parent.missing ? qsTr("∅ eksik") : parent.display; color: parent.missing ? Theme.muted : Theme.text; font.italic: parent.missing; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
            TapHandler { onTapped: { table.keyboardRow = parent.row; dataView.selectRow(parent.row); table.forceActiveFocus() } }
            HoverHandler { id: hover }
            ToolTip.visible: hover.hovered
            ToolTip.text: (missing ? qsTr("Eksik değer (null)") : display) + "\nRowId " + rowId
        }
    }
    Flow {
        visible: false
        Layout.fillWidth: true
        spacing: Theme.sm
        UiButton { objectName: "datasetCopySelection"; text: qsTr("Görünen seçimi kopyala (JSON)"); enabled: dataView.selectedRowIds.length > 0; onClicked: dataView.copyVisibleSelection(); width: Math.min(implicitWidth, parent.width) }
        UiButton { objectName: "datasetResetWidths"; text: qsTr("Sütun genişliklerini sıfırla"); onClicked: { table.clearColumnWidths(); table.forceLayout() } width: Math.min(implicitWidth, parent.width) }
    }
    UiLabel { visible: false; text: qsTr("Başlık kenarını sürükleyerek sütunu boyutlandırın. ∅ eksik değerdir; kopyalama yalnız bu sayfadaki görünen metni içerir."); color: Theme.secondary; font.pixelSize: Theme.small; Layout.fillWidth: true; wrapMode: Text.Wrap }
    RowLayout {
        visible: dataView.totalRows > 200 || dataView.busy
        Layout.fillWidth: true
        spacing: Theme.sm
        UiButton { tone: "cyan"; objectName: "datasetPreviousPage"; visible: dataView.totalRows > 200; text: qsTr("Önceki 200"); enabled: !projects.busy && dataView.pageOffset > 0; onClicked: dataView.goPage(Math.max(0, dataView.pageOffset - 200)); multiline: false }
        UiButton { tone: "cyan"; objectName: "datasetNextPage"; visible: dataView.totalRows > 200; text: qsTr("Sonraki 200"); enabled: !projects.busy && dataView.pageOffset + 200 < dataView.totalRows; onClicked: dataView.goPage(dataView.pageOffset + 200); multiline: false }
        UiButton { tone: "cyan"; objectName: "datasetCancel"; visible: dataView.busy; text: qsTr("İptal"); enabled: dataView.busy; onClicked: dataView.cancel(); multiline: false }
    }
    UiLabel {
        visible: panel.pane === "rows" && dataView.selectedRowIds.length > 0
        text: dataView.selectionText
        Layout.fillWidth: true
        wrapMode: Text.WrapAnywhere
        color: Theme.secondary
        font.pixelSize: Theme.small
    }
    }
    UiCheckBox {
        id: columnNotesToggle
        objectName: "columnNotesToggle"
        text: qsTr("Sütun ayrıntısı")
        checked: false
        visible: false
        Layout.fillWidth: true
    }
    ColumnDetails {
        id: columnDetail
        visible: panel.pane === "rows" && columnNotesToggle.checked
        Layout.fillWidth: true
        onHelpRequested: function(origin, context) { panel.helpRequested(origin, context) }
    }
}
