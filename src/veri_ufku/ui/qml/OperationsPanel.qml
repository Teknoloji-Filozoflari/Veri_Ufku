import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    signal helpRequested(var origin, string context)
    property string helpContext: "operation-preview"
    spacing: Theme.lg
    UiLabel { text: "İşlem önizlemesi ve geçmişi"; font.pixelSize: Theme.heading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    UiLabel { text: "Kaynak dosya ve ilk içe aktarma sürümü korunur. İşlemler yeni çalışma sürümü üretir. Tablo salt okunurdur; filtre/sıralama görünümü veriyi kendiliğinden değiştirmez."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.secondary }
    UiCombo { accessibleLabel: qsTr("Veri kümesi"); id: dataset; Layout.fillWidth: true; model: dataView.datasets; textRole: "label"; valueRole: "id"; currentIndex: dataView.datasets.findIndex(d => d.id === dataView.selectedDataset); enabled: !projects.busy; onActivated: dataView.selectDataset(currentValue) }
    UiCombo { accessibleLabel: "İşlem türü"; id: kind; objectName: "operationKind"; Layout.fillWidth: true; model: ["Sütunu yeniden adlandır", "Sütunu çıkar", "Görünüm filtrelerini veriye uygula", "Temizlik araçları", "Yeni kolon / tablo dönüşümleri","Mekânsal işlemler"]; enabled: !operations.busy; onActivated: operations.discardPreview() }
    UiCombo { accessibleLabel: "İşlem sütunu"; id: column; objectName: "operationColumn"; Layout.fillWidth: true; model: dataView.datasetColumns; textRole: "name"; valueRole: "id"; visible: kind.currentIndex < 2; enabled: !operations.busy; onActivated: operations.discardPreview() }
    UiLabel { text: "Yeni sütun adı"; visible: kind.currentIndex === 0 }
    UiTextField { id: name; objectName: "operationName"; Layout.fillWidth: true; visible: kind.currentIndex === 0; enabled: !operations.busy; Accessible.name: "Yeni sütun adı"; maximumLength: 200; onTextEdited: operations.discardPreview() }
    UiLabel { text: "Filtre koşullarını Veri → Veri tablosu ekranında hazırlayın. " + dataView.viewSummary; visible: kind.currentIndex === 2; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    GeoOperationOptions {id:geo;visible:kind.currentIndex===5;Layout.fillWidth:true;onHelpRequested:function(origin,context){root.helpRequested(origin,context)}}
    CleaningOptions { id: cleaning; Layout.fillWidth: true; visible: kind.currentIndex === 3; enabled: !operations.busy; onHelpRequested: function(origin, context) { root.helpRequested(origin, context) } }
    TransformationOptions { id: transforms; Layout.fillWidth: true; visible: kind.currentIndex === 4; enabled: !operations.busy; onHelpRequested: function(origin, context) { root.helpRequested(origin, context) } }
    Flow {
        Layout.fillWidth: true; spacing: Theme.sm
        UiButton { tone: "violet"; objectName: "operationPreview"; text: "Önizle"; enabled: !projects.busy && !projects.readOnly && dataView.datasets.length > 0; primary: !operations.canApply; onClicked: { if(kind.currentIndex===5) geo.preview(); else if (kind.currentIndex === 4) transforms.preview(); else if (kind.currentIndex === 3) cleaning.preview(); else operations.previewOperation(["rename", "drop", "filter"][kind.currentIndex], column.currentValue || "", name.text) } }
        UiButton { tone: "violet"; objectName: "operationApply"; text: "Uygula ve projeye kaydet"; enabled: operations.canApply; primary: true; onClicked: operations.apply() }
        UiButton { tone: "violet"; objectName: "operationCancel"; text: qsTr("İptal"); enabled: operations.busy && operations.state !== "publishing"; onClicked: operations.cancel() }
        UiButton { tone: "mint"; text: qsTr("Bu ne işe yarar?"); property string helpContext: "operation-preview"; onClicked: root.helpRequested(this, helpContext) }
    }
    UiLabel { text: operations.message + " · " + ({idle: "Hazır", running: "Hesaplanıyor", previewed: "Önizleme hazır", publishing: "Kaydediliyor", succeeded: "Tamamlandı", failed: "Hata", canceled: "İptal edildi", cancel_requested: "İptal bekleniyor"}[operations.state] || operations.state); Layout.fillWidth: true; wrapMode: Text.WordWrap; Accessible.role: Accessible.StaticText }
    UiLabel { text: operations.errorText; visible: text.length > 0; color: Theme.warning; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    ColumnLayout {
        Layout.fillWidth: true
        visible: operations.previewResult.impact !== undefined
        UiLabel {
            Layout.fillWidth: true; wrapMode: Text.WordWrap
            property var impact: operations.previewResult.impact || {}
            text: "Tam veri: " + (impact.before_rows || 0) + " → " + (impact.after_rows || 0) + " satır; " + (impact.before_columns || 0) + " → " + (impact.after_columns || 0) + " sütun. Çıkarılan satır: " + (impact.removed_rows || 0) + "; değeri değişen / çıkarılan satır: " + (impact.changed_rows || 0) + "; yeni kimlikle oluşturulan satır: " + (impact.added_rows || 0) + "; değişen sütun: " + (impact.changed_columns || 0) + "; değişen hücre değeri: " + (impact.changed_cells || 0) + "; yeni null: " + (impact.new_nulls || 0) + "; dönüşüm hatası: " + (impact.parse_errors || 0) + "; aykırı aday: " + (impact.outlier_candidates || 0) + "."
        }
        UiLabel { property var impact: operations.previewResult.impact || {}; visible: (impact.input_populations || []).length > 1; text:"Girdi kayıt sayımları: " + (impact.input_populations || []).map(p=>(p.side==="primary" ? "sol " : "sağ ")+p.rows+" ("+p.version_id.slice(-8)+")").join("; ") + ". Toplam girdi oluşumu: " + impact.total_input_occurrences + "; self-join aynı kaynak sürümünü iki girdi olarak kullanır."; Layout.fillWidth:true; wrapMode:Text.WordWrap }
        UiLabel { property var d: operations.previewResult.diagnostics || {}; visible: d.predicted_rows !== undefined; text: "Tam veri tahmini / sonuç: " + (d.predicted_rows || 0) + " satır" + (d.relationship ? " · ilişki " + d.relationship + " · eşleşen çift " + d.matched_pairs + " · eşleşmeyen sol " + d.left_unmatched + " / sağ " + d.right_unmatched : "") + ". Yeni kimlik üreten işlemde eski çalışma kayıtları yerine yeni kayıtlar sayılır; bu silinen kaynak kaydı anlamına gelmez."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        UiLabel { text: "Önce şema: " + dataView.datasetColumns.map(c => c.name + " [" + c.type + "]").join(", "); Layout.fillWidth: true; wrapMode: Text.WordWrap }
        UiLabel { text: "Sonra şema: " + ((operations.previewResult.spec || {}).output_schema || []).map(c => c.name + " [" + c.type + "]").join(", "); Layout.fillWidth: true; wrapMode: Text.WordWrap }
        Repeater { model: (operations.previewResult.diagnostics || {}).warnings || []; delegate: UiLabel { required property string modelData; text: modelData; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.warning } }
        Repeater { model: (operations.previewResult.diagnostics || {}).examples || []; delegate: UiLabel { required property var modelData; text: "Dönüşüm hatası · " + modelData.row_id + " · " + modelData.reason; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere } }
        UiCheckBox { id: compareTables; objectName: "operationCompareTables"; text: "Önce / sonra örnek tabloları göster" }
        OperationTable { visible: compareTables.checked; objectName: "operationBeforeTable"; title: qsTr("Önce"); tableModel: operations.beforeModel }
        OperationTable { visible: compareTables.checked; objectName: "operationAfterTable"; title: qsTr("Sonra"); tableModel: operations.afterModel }
    }
    Flow {
        Layout.fillWidth: true; spacing: Theme.sm
        UiButton { tone: "violet"; objectName: "operationUndo"; text: "Geri al"; enabled: !projects.busy && !projects.readOnly && dataView.datasets.length > 0; onClicked: operations.historyAction("undo") }
        UiButton { tone: "violet"; objectName: "operationRedo"; text: "Yinele"; enabled: !projects.busy && !projects.readOnly && dataView.datasets.length > 0; onClicked: operations.historyAction("redo") }
        UiButton { tone: "mint"; text: "Geçmiş ve geri alma yardımı"; property string helpContext: "operation-history"; onClicked: root.helpRequested(this, helpContext) }
    }
    UiCheckBox { id: showHistory; objectName: "operationShowHistory"; text: "İşlem geçmişi ve sonuç ayrıntılarını göster" }
    ColumnLayout {
    visible: showHistory.checked; Layout.fillWidth: true
    UiLabel { text: "İşlem geçmişi"; font.pixelSize: Theme.heading; font.bold: true }
    UiLabel { text: "Eski adımı değiştirmek için o adımın öncesine dönün, yeni parametrelerle önizleyin. Yeni dal eski sürümleri korur; yineleme zinciri temizlenir. Alt adımlar ve sonuçlar yeniden hesaplanmaz. Kayda dönüş ve geri al/yinele proje taslağını da kaydeder."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.secondary }
    Repeater {
        model: operations.history
        delegate: ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            UiLabel { text: modelData.label + (modelData.current ? " · AKTİF" : modelData.onBranch ? " · aktif dalın önceki adımı" : " · eski dal / güncel değil"); Layout.fillWidth: true; wrapMode: Text.WordWrap }
            UiButton { tone: "violet"; text: "Bu adımın öncesine dön"; visible: modelData.parent.length > 0; enabled: !projects.busy && !projects.readOnly; onClicked: operations.checkout(modelData.parent) }
        }
    }
    UiLabel { text: "Kaydedilmiş sonuçların güncelliği"; font.bold: true; Layout.fillWidth: true }
    Repeater {
        model: operations.resultStatuses
        delegate: UiLabel { required property var modelData; text: modelData.label + (modelData.current ? " · güncel" : " · ESKİ VERİ SÜRÜMÜ / güncel değil") + " · " + modelData.versions; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    }
    UiLabel { text: "Modelleme öncesi sızıntı incelemesi gereken veri bağımlı işlemler: " + operations.leakageHistory.length; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    Repeater {
        model: operations.leakageHistory
        delegate: UiLabel { required property var modelData; text: "Sızıntı incelemesi: " + modelData.kind + " " + modelData.method + " · tam veriye bağlı; sızıntı açısından inceleyin · " + modelData.input_version; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
    }
    }
    UiButton { tone: "violet"; text: "Kaynak ile çalışma verisi farkı"; property string helpContext: "source-working"; onClicked: root.helpRequested(this, helpContext) }
}
