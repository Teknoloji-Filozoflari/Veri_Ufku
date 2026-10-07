import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    signal helpRequested(var origin, string context)
    property string helpContext: "operation-preview"
    spacing: Theme.lg
    Label { text: "İşlem önizlemesi ve geçmişi"; font.pixelSize: Theme.heading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    Label { text: "Kaynak dosya ve ilk içe aktarma sürümü korunur. İşlemler yeni çalışma sürümü üretir. Tablo salt okunurdur; filtre/sıralama görünümü veriyi kendiliğinden değiştirmez."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.secondary }
    UiCombo { id: dataset; Layout.fillWidth: true; model: dataView.datasets; textRole: "label"; valueRole: "id"; currentIndex: dataView.datasets.findIndex(d => d.id === dataView.selectedDataset); enabled: !projects.busy; onActivated: dataView.selectDataset(currentValue) }
    UiCombo { id: kind; objectName: "operationKind"; Layout.fillWidth: true; model: ["Sütunu yeniden adlandır", "Sütunu çıkar", "Görünüm filtrelerini veriye uygula"]; enabled: !operations.busy; onActivated: operations.discardPreview() }
    UiCombo { id: column; objectName: "operationColumn"; Layout.fillWidth: true; model: dataView.datasetColumns; textRole: "name"; valueRole: "id"; visible: kind.currentIndex !== 2; enabled: !operations.busy; onActivated: operations.discardPreview() }
    Label { text: "Yeni sütun adı"; visible: kind.currentIndex === 0 }
    TextField { id: name; objectName: "operationName"; Layout.fillWidth: true; visible: kind.currentIndex === 0; enabled: !operations.busy; Accessible.name: "Yeni sütun adı"; maximumLength: 200; onTextEdited: operations.discardPreview() }
    Label { text: "Filtre koşullarını Veri → Veri tablosu ekranında hazırlayın. " + dataView.viewSummary; visible: kind.currentIndex === 2; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    Flow {
        Layout.fillWidth: true; spacing: Theme.sm
        UiButton { objectName: "operationPreview"; text: "Önizle"; enabled: !projects.busy && !projects.readOnly && dataView.datasets.length > 0; primary: !operations.canApply; onClicked: operations.previewOperation(["rename", "drop", "filter"][kind.currentIndex], column.currentValue || "", name.text) }
        UiButton { objectName: "operationApply"; text: "Uygula ve projeye kaydet"; enabled: operations.canApply; primary: true; onClicked: operations.apply() }
        UiButton { objectName: "operationCancel"; text: "İptal"; enabled: operations.busy && operations.state !== "publishing"; onClicked: operations.cancel() }
        UiButton { text: "Bu ne işe yarar?"; property string helpContext: "operation-preview"; onClicked: root.helpRequested(this, helpContext) }
    }
    Label { text: operations.message + " · " + ({idle: "Hazır", running: "Hesaplanıyor", previewed: "Önizleme hazır", publishing: "Kaydediliyor", succeeded: "Tamamlandı", failed: "Hata", canceled: "İptal edildi", cancel_requested: "İptal bekleniyor"}[operations.state] || operations.state); Layout.fillWidth: true; wrapMode: Text.WordWrap; Accessible.role: Accessible.StaticText }
    Label { text: operations.errorText; visible: text.length > 0; color: Theme.warning; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    ColumnLayout {
        Layout.fillWidth: true
        visible: operations.previewResult.impact !== undefined
        Label {
            Layout.fillWidth: true; wrapMode: Text.WordWrap
            property var impact: operations.previewResult.impact || {}
            text: "Tam veri: " + (impact.before_rows || 0) + " → " + (impact.after_rows || 0) + " satır; " + (impact.before_columns || 0) + " → " + (impact.after_columns || 0) + " sütun. Çıkarılan satır: " + (impact.removed_rows || 0) + "; değişen sütun: " + (impact.changed_columns || 0) + "; değişen hücre değeri: " + (impact.changed_cells || 0) + "."
        }
        Label { text: "Önce şema: " + dataView.datasetColumns.map(c => c.name + " [" + c.type + "]").join(", "); Layout.fillWidth: true; wrapMode: Text.WordWrap }
        Label { text: "Sonra şema: " + ((operations.previewResult.spec || {}).output_schema || []).map(c => c.name + " [" + c.type + "]").join(", "); Layout.fillWidth: true; wrapMode: Text.WordWrap }
        OperationTable { objectName: "operationBeforeTable"; title: "Önce"; tableModel: operations.beforeModel }
        OperationTable { objectName: "operationAfterTable"; title: "Sonra"; tableModel: operations.afterModel }
    }
    Label { text: "İşlem geçmişi"; font.pixelSize: Theme.heading; font.bold: true }
    Flow {
        Layout.fillWidth: true; spacing: Theme.sm
        UiButton { objectName: "operationUndo"; text: "Geri al"; enabled: !projects.busy && !projects.readOnly && dataView.datasets.length > 0; onClicked: operations.historyAction("undo") }
        UiButton { objectName: "operationRedo"; text: "Yinele"; enabled: !projects.busy && !projects.readOnly && dataView.datasets.length > 0; onClicked: operations.historyAction("redo") }
        UiButton { text: "Geçmiş ve geri alma yardımı"; property string helpContext: "operation-history"; onClicked: root.helpRequested(this, helpContext) }
    }
    Label { text: "Eski adımı değiştirmek için o adımın öncesine dönün, yeni parametrelerle önizleyin. Yeni dal eski sürümleri korur; yineleme zinciri temizlenir. Alt adımlar ve sonuçlar yeniden hesaplanmaz. Kayda dönüş ve geri al/yinele proje taslağını da kaydeder."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.secondary }
    Repeater {
        model: operations.history
        delegate: ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            Label { text: modelData.label + (modelData.current ? " · AKTİF" : modelData.onBranch ? " · aktif dalın önceki adımı" : " · eski dal / güncel değil"); Layout.fillWidth: true; wrapMode: Text.WordWrap }
            UiButton { text: "Bu adımın öncesine dön"; visible: modelData.parent.length > 0; enabled: !projects.busy && !projects.readOnly; onClicked: operations.checkout(modelData.parent) }
        }
    }
    Label { text: "Kaydedilmiş sonuçların güncelliği"; font.bold: true; Layout.fillWidth: true }
    Repeater {
        model: operations.resultStatuses
        delegate: Label { required property var modelData; text: modelData.label + (modelData.current ? " · güncel" : " · ESKİ VERİ SÜRÜMÜ / güncel değil") + " · " + modelData.versions; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    }
    UiButton { text: "Kaynak ile çalışma verisi farkı"; property string helpContext: "source-working"; onClicked: root.helpRequested(this, helpContext) }
}
