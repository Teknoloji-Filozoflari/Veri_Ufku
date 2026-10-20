import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    property bool descriptive: false
    property var result: descriptive ? dataView.describeResult : dataView.inventoryResult
    signal columnChosen(string column)
    property string requestedVersion: ""
    property bool automaticRunning: false
    Timer { id: inventoryTimer; interval: 100; onTriggered: panel.ensureInventory() }
    readonly property string selectedVersion: {
        let dataset = dataView.datasets.find(function(d) { return d.id === dataView.selectedDataset })
        return dataset ? dataset.version : ""
    }
    function ensureInventory() {
        if (!visible || descriptive || !selectedVersion || dataView.busy || projects.busy) return
        if ((result.dataset_version === selectedVersion && result.scope === "full") || requestedVersion === selectedVersion) return
        requestedVersion = selectedVersion
        automaticRunning = true
        dataView.inspectColumns(false, false)
    }
    function typeSummary() {
        let types = result.types || {}
        return Object.keys(types).map(function(kind) {
            let names = (result.columns || []).filter(function(column) {
                return column.physical_type === kind
            }).map(function(column) { return column.name })
            return kind + ": " + types[kind] + " — " + names.join(", ")
        }).join("\n")
    }
    function diskSize() {
        let bytes = result.snapshot_bytes || 0
        return bytes >= 1048576 ? (bytes / 1048576).toFixed(1) + " MiB" : bytes >= 1024 ? (bytes / 1024).toFixed(1) + " KiB" : bytes + " bayt"
    }
    onVisibleChanged: {
        if (visible) { requestedVersion = ""; inventoryTimer.start() }
        else { inventoryTimer.stop(); if (automaticRunning && dataView.busy) dataView.cancel() }
    }
    onDescriptiveChanged: inventoryTimer.start()
    onSelectedVersionChanged: inventoryTimer.start()
    Component.onCompleted: inventoryTimer.start()
    Connections { target: dataView; function onChanged() { if (!dataView.busy) panel.automaticRunning = false; if (panel.visible && !panel.descriptive) inventoryTimer.start() } }
    Connections { target: projects; function onChanged() { if (panel.visible && !panel.descriptive) inventoryTimer.start() } }
    spacing: Theme.md
    UiLabel { visible: panel.descriptive; text: panel.descriptive ? qsTr("Özet istatistikler") : qsTr("Veri profili · bütün sütunlar"); font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiLabel { visible: panel.descriptive; text: panel.descriptive ? qsTr("Sayısal ölçümlerin merkezini ve yayılımını karşılaştır. Kimlik ve kategori kodları ölçüm değildir; bu sütunlarda sayısal özet gösterilmez.") : qsTr("Sütun adlarını, fiziksel türlerini ve doluluk sayılarını birlikte gör. Bir satıra tıklayarak o sütunun değerlerini inceleyebilirsin."); Layout.fillWidth: true; color: Theme.secondary; wrapMode: Text.Wrap }
    UiButton { visible: panel.descriptive; objectName: panel.descriptive ? "computeDescribe" : "computeInventory"; text: panel.descriptive ? qsTr("Özet istatistikleri hesapla") : qsTr("Sütun özetini hesapla"); enabled: dataView.datasets.length > 0 && !projects.busy; Layout.fillWidth: true; tone: "cyan"; onClicked: { if (!dataView.busy) dataView.inspectColumns(false, panel.descriptive) } }
    UiLabel { visible: panel.descriptive; objectName: "inspectionScope"; text: panel.result.scope ? (panel.result.scope === "sample" ? "Örnek · ilk N kayıt; temsili olduğu garanti edilmez" : "Tam veri") + " · " + panel.result.used_n + " / " + panel.result.population_n + " kayıt\nVeri sürümü: " + panel.result.dataset_version : qsTr("Henüz hesaplanmadı. Dosya aktarımından sonra kapsamı seçip hesapla."); wrapMode: Text.WrapAnywhere; Layout.fillWidth: true; color: Theme.secondary }
    Frame {
        visible: !panel.descriptive && panel.result.types !== undefined
        Layout.fillWidth: true
        padding: Theme.lg
        background: Rectangle { color: Theme.surface; radius: Theme.radius; border.color: Theme.border }
        GridLayout {
            width: parent.width
            columns: panel.width > 650 * Theme.scale ? 3 : 1
            columnSpacing: Theme.xl
            rowSpacing: Theme.md
            ColumnLayout {
                UiLabel { text: qsTr("Sütun sayısı"); color: Theme.secondary }
                UiLabel { objectName: "inventoryColumnCount"; text: (panel.result.columns || []).length; font.pixelSize: Theme.subheading; font.bold: true; color: Theme.dataTone }
            }
            ColumnLayout {
                Layout.fillWidth: true
                UiLabel { text: qsTr("Veri türleri"); color: Theme.secondary }
                UiLabel { objectName: "inventoryTypes"; text: panel.typeSummary(); textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
            }
            ColumnLayout {
                UiLabel { text: qsTr("Diskteki boyut"); color: Theme.secondary }
                UiLabel { objectName: "inventoryDiskSize"; text: panel.diskSize(); font.bold: true }
            }
        }
    }
    HorizontalHeaderView {
        syncView: table; Layout.fillWidth: true; clip: true; activeFocusOnTab: false
        delegate: Rectangle {
            required property string display
            implicitHeight: 42 * Theme.scale
            implicitWidth: 170 * Theme.scale
            color: Theme.cyanSurface
            UiLabel { anchors.fill: parent; anchors.margins: Theme.md; text: parent.display; font.bold: true; color: Theme.dataTone; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
        }
    }
    TableView {
        id: table
        objectName: panel.descriptive ? "describeTable" : "inventoryTable"
        Accessible.name: panel.descriptive ? "Özet istatistik tablosu" : "Bütün sütunların profil tablosu"
        Accessible.role: Accessible.Table
        activeFocusOnTab: true
        keyNavigationEnabled: false
        property int chosenRow: 0
        property int chosenColumn: panel.descriptive ? 1 : 0
        function moveSelection(rowDelta, columnDelta) {
            if (rows === 0 || columns === 0 || (panel.descriptive && columns < 2)) return
            chosenRow = Math.max(0, Math.min(rows - 1, chosenRow + rowDelta))
            chosenColumn = Math.max(panel.descriptive ? 1 : 0, Math.min(columns - 1, chosenColumn + columnDelta))
            positionViewAtCell(Qt.point(chosenColumn, chosenRow), TableView.Contain)
        }
        function openSelection() {
            if (rows === 0 || columns === 0 || chosenColumn >= columns) return
            dataView.selectInspectionCell(chosenRow, chosenColumn, panel.descriptive)
            panel.columnChosen(dataView.selectedColumn)
        }
        onRowsChanged: chosenRow = 0
        onColumnsChanged: chosenColumn = panel.descriptive ? 1 : 0
        Keys.onDownPressed: moveSelection(1, 0)
        Keys.onUpPressed: moveSelection(-1, 0)
        Keys.onRightPressed: moveSelection(0, 1)
        Keys.onLeftPressed: moveSelection(0, -1)
        Keys.onReturnPressed: openSelection()
        Keys.onSpacePressed: openSelection()
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(420 * Theme.scale, Math.max(100 * Theme.scale, rows * 40 * Theme.scale))
        clip: true
        reuseItems: true
        model: panel.descriptive ? dataView.describeModel : dataView.infoModel
        columnWidthProvider: function(column) { return (column === 0 ? 250 : !panel.descriptive && column === 1 ? 290 : 170) * Theme.scale }
        rowHeightProvider: function(row) { return 40 * Theme.scale }
        ScrollBar.horizontal: ScrollBar {}
        ScrollBar.vertical: ScrollBar {}
        delegate: Rectangle {
            required property string display
            required property int row
            required property int column
            color: table.activeFocus && row === table.chosenRow && (!panel.descriptive || column === table.chosenColumn) ? Theme.cyanSurface : row % 2 === 0 ? Theme.surface : Theme.field
            border.color: Theme.border
            implicitHeight: 40 * Theme.scale
            implicitWidth: 170 * Theme.scale
            UiLabel { anchors.fill: parent; anchors.margins: Theme.sm; text: parent.display; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
            TapHandler { onTapped: { dataView.selectInspectionCell(parent.row, parent.column, panel.descriptive); if (!panel.descriptive || parent.column > 0) panel.columnChosen(dataView.selectedColumn) } }
            HoverHandler { id: hover }
            ToolTip.visible: hover.hovered
            ToolTip.text: display
        }
    }
    UiLabel { visible: true; text: panel.descriptive ? qsTr("count: yalnız sonlu sayılar. Null, NaN ve sonsuz dışarıda; standart sapma ddof=1, yüzdelikler doğrusal ara değerle hesaplanır. Kimlik/kategori sütunundaki — bilinçli olarak bastırılmış özettir. Tablo filtreleri bu özeti değiştirmez.") : qsTr("Dolu: null olmayan değerler; NaN ayrıca sayılır. Boş metin null değildir. Veri türü sütunun gerçek saklama türüdür. Bu özet veriyi değiştirmez. Tüm sütunlar listelenir."); Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    UiLabel { visible: panel.descriptive || dataView.errorText.length > 0; text: dataView.errorText || dataView.message; color: dataView.errorText ? Theme.error : Theme.secondary; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiLabel { visible: !panel.descriptive && !selectedVersion; text: qsTr("Sütunlarını görmek için bir veri dosyası aktar."); color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiLabel { visible: !panel.descriptive && dataView.busy; text: qsTr("Sütun özeti hazırlanıyor…"); color: Theme.secondary; Layout.fillWidth: true }
    UiButton { visible: dataView.busy; text: qsTr("Hesabı iptal et"); enabled: dataView.busy; onClicked: dataView.cancel(); Layout.fillWidth: true }
}
