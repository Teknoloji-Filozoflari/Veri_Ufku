import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    signal helpRequested(var origin, string context)
    property string helpContext: "operation-preview"
    property bool prepareShell: false
    property int selectedPrepareBlock: 1
    readonly property int kindIndex: kind.currentIndex
    readonly property string cleaningKind: cleaning.kind
    readonly property int cleaningFillMethodIndex: cleaning.fillMethodIndex
    spacing: Theme.lg

    function runPreview() {
        if (kind.currentIndex === 5)
            geo.preview()
        else if (kind.currentIndex === 4)
            transforms.preview()
        else if (kind.currentIndex === 3)
            cleaning.preview()
        else
            operations.previewOperation(["rename", "drop", "filter"][kind.currentIndex], column.currentValue || "", name.text)
    }
    function runApply() { operations.apply() }
    function runCancel() { operations.cancel() }

    function applyInspectDraft() {
        if (!operations.hasInspectDraft)
            return
        let draft = operations.inspectDraft || ({})
        kind.currentIndex = 3
        cleaning.applyInspectDraft(draft)
    }

    function applyPrepareBlock(block) {
        operations.discardPreview()
        if (block === 1) {
            kind.currentIndex = 3
            cleaning.setMethodKind("trim")
        } else if (block === 2) {
            kind.currentIndex = 3
            cleaning.setMethodKind("outlier")
        } else if (block === 3) {
            kind.currentIndex = 3
            cleaning.setMethodKind("dedup")
        } else if (block === 4) {
            kind.currentIndex = 4
            transforms.setMethodKind("computed")
        } else if (block === 5) {
            kind.currentIndex = 4
            transforms.setMethodKind("join")
        } else if (block === 6) {
            kind.currentIndex = 3
        } else if (block === 7) {
            kind.currentIndex = 3
            cleaning.setMethodKind("ordered_fill")
        } else if (block === 8) {
            kind.currentIndex = 3
            cleaning.setMethodKind("fill")
            cleaning.setFillConstant()
        } else if (block === 9) {
            kind.currentIndex = 3
        } else if (block === 10) {
            kind.currentIndex = 3
            showHistory.checked = true
        }
    }

    UiLabel {
        visible: !root.prepareShell
        text: "İşlem önizlemesi ve geçmişi"
        font.pixelSize: Theme.heading
        font.bold: true
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }
    Frame {
        objectName: root.prepareShell ? "" : "inspectDraftFrame"
        visible: !root.prepareShell && operations.hasInspectDraft
        Layout.fillWidth: true
        padding: Theme.md
        background: Rectangle { color: Theme.violetSurface; border.color: Theme.border; radius: Theme.radius }
        ColumnLayout {
            width: parent.width
            spacing: Theme.sm
            UiLabel {
                text: qsTr("İncele’den geldi — taslak işlem")
                font.bold: true
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }
            UiLabel {
                objectName: root.prepareShell ? "" : "inspectDraftOrigin"
                text: (operations.inspectDraft.origin || "") + "\n" + qsTr("Gerekçe: ") + (operations.inspectDraft.rationale || "") + "\n" + qsTr("Beklenen etki: ") + (operations.inspectDraft.expected_impact || "") + "\n" + qsTr("Taslak veri sürümü üretmez; Önizle → Uygula gerekir.")
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
            }
            UiButton {
                objectName: root.prepareShell ? "" : "inspectDraftClear"
                text: qsTr("Taslağı reddet")
                quiet: true
                onClicked: operations.clearInspectDraft()
            }
        }
    }
    UiLabel {
        objectName: "operationPreviewContract"
        visible: !root.prepareShell || root.selectedPrepareBlock === 9
        text: expertWorkspace.modelModule.installed === true
            ? "Önizleme sürüm yazmaz. Ayrı Uygula düğmesi yeni veri sürümü ve işlem geçmişi yazar. Geri al önceki sürüme döner; sürüm zinciri silinmez; kaynak dosya korunur. Önizleme önce ve sonraki satır ile sütun sayılarını, etkilenen kayıtları ve yeni eksikleri gösterir. Tüm veriye uygula bu ekrandadır. Model için planla, Model bölümündedir; plan üretilemezse nedeni yazılır."
            : "Önizleme sürüm yazmaz. Ayrı Uygula düğmesi yeni veri sürümü ve işlem geçmişi yazar. Geri al önceki sürüme döner; sürüm zinciri silinmez; kaynak dosya korunur. Önizleme önce ve sonraki satır ile sütun sayılarını, etkilenen kayıtları ve yeni eksikleri gösterir. Tüm veriye uygula bu ekrandadır. Model modülü kurulu değil; model için planla gizlidir. İstatistik bulguları Raporla’dadır."
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
    }
    UiLabel {
        visible: !root.prepareShell
        text: "Kaynak dosya ve ilk içe aktarma sürümü korunur. İşlemler yeni çalışma sürümü üretir. Tablo salt okunurdur; filtre/sıralama görünümü veriyi kendiliğinden değiştirmez."
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
    }
    Frame {
        objectName: "outlierCandidateFrame"
        visible: !root.prepareShell || root.selectedPrepareBlock === 2
        Layout.fillWidth: true
        padding: Theme.md
        background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius }
        ColumnLayout {
            width: parent.width
            spacing: Theme.sm
            UiLabel { text: qsTr("Aykırı inceleme adayları (karar yok)"); font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
            UiLabel { text: qsTr("IQR, dayanıklı z ve klasik z yan yana. Aday hata değildir. Grafik işaretleri aynı RowId kümesine bağlanır. Silme/sınırlama yalnız Önizle+Uygula ile."); color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.Wrap }
            UiCombo { accessibleLabel: qsTr("Aday sütunu"); id: outlierColumn; objectName: "outlierCandidateColumn"; model: dataView.datasetColumns; textRole: "name"; valueRole: "id"; Layout.fillWidth: true }
            UiButton {
                objectName: "outlierCandidateCompute"
                text: qsTr("Üç yöntemle aday listesi")
                tone: "violet"
                enabled: !projects.busy && !dataView.busy && outlierColumn.currentIndex >= 0
                Layout.fillWidth: true
                multiline: true
                onClicked: dataView.computeOutlierCandidates(outlierColumn.currentValue)
            }
            UiLabel {
                objectName: "outlierCandidateSummary"
                visible: !!dataView.outlierCandidates.dataset_version
                text: qsTr("Birleşik aday: ") + (dataView.outlierCandidates.union_row_ids || []).length + qsTr(" · kullanılan n=") + dataView.outlierCandidates.used_n + qsTr(" · dışlanan eksik=") + dataView.outlierCandidates.excluded_missing + "\n" + dataView.outlierCandidates.disclaimer + qsTr("\nSürüm: ") + dataView.outlierCandidates.dataset_version + (dataView.outlierCandidates.chart_marked_row_ids && dataView.outlierCandidates.chart_marked_row_ids.length ? qsTr("\nGrafik işaretleri: ") + dataView.outlierCandidates.chart_marked_row_ids.length : "")
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }
            Repeater {
                model: dataView.outlierCandidates.methods || []
                UiLabel {
                    required property var modelData
                    text: modelData.method + " · n=" + modelData.count + " · " + modelData.note
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
            }
        }
    }
    UiCombo { accessibleLabel: qsTr("Veri kümesi"); id: dataset; Layout.fillWidth: true; model: dataView.datasets; textRole: "label"; valueRole: "id"; currentIndex: dataView.datasets.findIndex(d => d.id === dataView.selectedDataset); enabled: !projects.busy; onActivated: dataView.selectDataset(currentValue); visible: !root.prepareShell || root.selectedPrepareBlock !== 6 }
    UiCombo {
        accessibleLabel: "İşlem türü"
        id: kind
        objectName: "operationKind"
        Layout.fillWidth: true
        model: ["Sütunu yeniden adlandır", "Sütunu çıkar", "Görünüm filtrelerini veriye uygula", "Temizlik araçları", "Yeni kolon / tablo dönüşümleri","Mekânsal işlemler"]
        enabled: !operations.busy
        onActivated: operations.discardPreview()
        visible: !root.prepareShell || root.selectedPrepareBlock === 1 || root.selectedPrepareBlock === 8
        Component.onCompleted: {
            if (!root.prepareShell)
                Qt.callLater(root.applyInspectDraft)
        }
    }
    Connections {
        target: operations
        enabled: !root.prepareShell
        function onChanged() { root.applyInspectDraft() }
    }
    UiCombo { accessibleLabel: "İşlem sütunu"; id: column; objectName: "operationColumn"; Layout.fillWidth: true; model: dataView.datasetColumns; textRole: "name"; valueRole: "id"; visible: kind.currentIndex < 2 && (!root.prepareShell || root.selectedPrepareBlock === 1 || root.selectedPrepareBlock === 8); enabled: !operations.busy; onActivated: operations.discardPreview() }
    UiLabel { text: "Yeni sütun adı"; visible: kind.currentIndex === 0 && (!root.prepareShell || root.selectedPrepareBlock === 1) }
    UiTextField { id: name; objectName: "operationName"; Layout.fillWidth: true; visible: kind.currentIndex === 0 && (!root.prepareShell || root.selectedPrepareBlock === 1); enabled: !operations.busy; Accessible.name: "Yeni sütun adı"; maximumLength: 200; onTextEdited: operations.discardPreview() }
    UiLabel { text: "Filtre koşullarını Veri → Veri tablosu ekranında hazırlayın. " + dataView.viewSummary; visible: kind.currentIndex === 2 && (!root.prepareShell || root.selectedPrepareBlock === 8); Layout.fillWidth: true; wrapMode: Text.WordWrap }
    GeoOperationOptions {id:geo;visible:kind.currentIndex===5 && (!root.prepareShell || root.selectedPrepareBlock === 5);Layout.fillWidth:true;onHelpRequested:function(origin,context){root.helpRequested(origin,context)}}
    CleaningOptions {
        id: cleaning
        Layout.fillWidth: true
        visible: kind.currentIndex === 3 && (!root.prepareShell || [1, 2, 3, 7, 8].indexOf(root.selectedPrepareBlock) >= 0)
        enabled: !operations.busy
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }
    TransformationOptions {
        id: transforms
        Layout.fillWidth: true
        visible: kind.currentIndex === 4 && (!root.prepareShell || root.selectedPrepareBlock === 4 || root.selectedPrepareBlock === 5)
        enabled: !operations.busy
        onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
    }
    Flow {
        visible: !root.prepareShell
        Layout.fillWidth: true
        spacing: Theme.sm
        UiButton { tone: "violet"; objectName: root.prepareShell ? "" : "operationPreview"; text: "Önizle"; enabled: !projects.busy && !projects.readOnly && dataView.datasets.length > 0; primary: !operations.canApply; onClicked: root.runPreview() }
        UiButton { tone: "violet"; objectName: root.prepareShell ? "" : "operationApply"; text: "Uygula ve projeye kaydet"; enabled: operations.canApply; primary: true; onClicked: root.runApply() }
        UiButton { tone: "violet"; objectName: root.prepareShell ? "" : "operationCancel"; text: qsTr("İptal"); enabled: operations.busy && operations.state !== "publishing"; onClicked: root.runCancel() }
        UiButton { visible: false; tone: "mint"; text: qsTr("Bu ne işe yarar?"); property string helpContext: "operation-preview"; onClicked: root.helpRequested(this, helpContext) }
    }
    UiLabel {
        visible: !root.prepareShell
        text: operations.message + " · " + ({idle: "Hazır", running: "Hesaplanıyor", previewed: "Önizleme hazır", publishing: "Kaydediliyor", succeeded: "Tamamlandı", failed: "Hata", canceled: "İptal edildi", cancel_requested: "İptal bekleniyor"}[operations.state] || operations.state)
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        Accessible.role: Accessible.StaticText
    }
    UiLabel { text: operations.errorText; visible: !root.prepareShell && text.length > 0; color: Theme.warning; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    ColumnLayout {
        Layout.fillWidth: true
        visible: !root.prepareShell && operations.previewResult.impact !== undefined
        UiLabel {
            objectName: "operationImpact"
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
        Layout.fillWidth: true
        spacing: Theme.sm
        visible: !root.prepareShell || root.selectedPrepareBlock === 10
        UiButton { tone: "violet"; objectName: "operationUndo"; text: "Geri al"; enabled: !projects.busy && !projects.readOnly && dataView.datasets.length > 0; onClicked: operations.historyAction("undo") }
        UiButton { tone: "violet"; objectName: "operationRedo"; text: "Yinele"; enabled: !projects.busy && !projects.readOnly && dataView.datasets.length > 0; onClicked: operations.historyAction("redo") }
        UiButton {
            visible: root.prepareShell && root.selectedPrepareBlock === 10
            tone: "violet"
            objectName: "prepareSaveProject"
            text: qsTr("Projeyi kaydet")
            enabled: projects.opened && projects.dirty && !projects.readOnly && !projects.busy
            onClicked: projects.request("save")
        }
        UiButton { visible: false; tone: "mint"; text: "Geçmiş ve geri alma yardımı"; property string helpContext: "operation-history"; onClicked: root.helpRequested(this, helpContext) }
    }
    UiCheckBox {
        id: showHistory
        objectName: "operationShowHistory"
        text: "İşlem geçmişi ve sonuç ayrıntılarını göster"
        visible: !root.prepareShell || root.selectedPrepareBlock === 10
    }
    ColumnLayout {
    visible: showHistory.checked && (!root.prepareShell || root.selectedPrepareBlock === 10); Layout.fillWidth: true
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
    UiButton { visible: false; tone: "violet"; text: "Kaynak ile çalışma verisi farkı"; property string helpContext: "source-working"; onClicked: root.helpRequested(this, helpContext) }
}
