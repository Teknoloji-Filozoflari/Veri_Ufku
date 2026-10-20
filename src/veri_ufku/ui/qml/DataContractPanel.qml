import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "dataContractPanel"
    property string helpContext: "contract.schema"
    property bool loading: false
    property string loadedKey: ""
    property var levels: ["unknown", "nominal", "ordinal", "interval", "ratio"]
    property var recipe: operations.contractRecipe
    spacing: Theme.md
    function invalidate() { if (!loading) operations.discardPreview() }
    function loadColumn() {
        let version = (dataView.datasets.find(d => d.id === dataView.selectedDataset) || {}).version || ""
        let key = dataView.selectedDataset + "/" + dataView.selectedColumn + "/" + version
        if (key === loadedKey) return
        loadedKey = key
        loading = true
        let c = dataView.columnDetails
        meaning.text = c.description || ""
        unit.text = c.unit || ""
        level.currentIndex = Math.max(0, levels.indexOf(c.measurement_level === "unknown" && c.role === "ordinal" ? "ordinal" : c.measurement_level || "unknown"))
        order.text = (c.ordinal_order || []).join("|")
        expectedType.text = c.physical_type || "String"
        expectedUnit.text = ""; foreignKey.checked = false
        minimum.text = ""; maximum.text = ""; nullable.checked = true; unique.checked = false
        let r = recipe.contract || {rules:[]}
        r.rules.forEach(function(rule) {
            if (rule.column_id !== dataView.selectedColumn) return
            if (rule.kind === "range") { minimum.text = rule.parameters.minimum || ""; maximum.text = rule.parameters.maximum || "" }
            if (rule.kind === "nullable") nullable.checked = rule.parameters.allowed
            if (rule.kind === "unique") unique.checked = true
            if (rule.kind === "unit") expectedUnit.text = rule.parameters.expected
            if (rule.kind === "type") expectedType.text = rule.parameters.expected
            if (rule.kind === "foreign_key") {
                foreignKey.checked = true
                reference.currentIndex = operations.secondaryDatasets.findIndex(d => d.version_id === rule.parameters.version_id)
                referenceColumn.currentIndex = ((operations.secondaryDatasets[reference.currentIndex] || {}).columns || []).findIndex(c => c.id === rule.parameters.column_id)
            }
        })
        declarative.text = JSON.stringify(recipe, null, 2)
        loading = false
    }
    function columnRecipe() {
        let value = JSON.parse(JSON.stringify(recipe))
        let id = dataView.selectedColumn
        let previous = value.semantic_metadata[id] || {role: "text", unit:"", ordinal_order:[], confirmed:false}
        previous.description = meaning.text; previous.unit = unit.text; previous.measurement_level = levels[level.currentIndex]
        if (previous.measurement_level === "ordinal") { let wasOrdinal = previous.role === "ordinal"; previous.role = "ordinal"; previous.ordinal_order = order.text.split("|"); if (!wasOrdinal) previous.confirmed = true }
        else if (previous.measurement_level !== "unknown") { if (previous.role === "ordinal") previous.role = "category"; previous.ordinal_order = [] }
        value.semantic_metadata[id] = previous
        let rules = value.contract.rules.filter(r => r.column_id !== id)
        let severityValue = severity.currentIndex === 0 ? "error" : "warning"
        function add(kind, parameters) { rules.push({id:id + "/" + kind, kind:kind, column_id:id, severity:severityValue, parameters:parameters}) }
        add("nullable", {allowed:nullable.checked})
        add("type", {expected:expectedType.text})
        if (unique.checked) add("unique", {nulls_equal:false})
        if (minimum.text || maximum.text) add("range", {minimum:minimum.text || null, maximum:maximum.text || null})
        if (expectedUnit.text) add("unit", {expected:expectedUnit.text})
        if (previous.role === "ordinal") add("ordinal", {order:previous.ordinal_order})
        if (foreignKey.checked) add("foreign_key", {version_id:reference.currentValue, column_id:referenceColumn.currentValue, nullable:nullable.checked})
        value.contract.rules = rules
        declarative.text = JSON.stringify(value, null, 2)
        return value
    }
    Component.onCompleted: loadColumn()
    Connections { target: dataView; function onChanged() { if (!operations.busy) panel.loadColumn() } }
    UiLabel { text: qsTr("Veri sözlüğü ve kalite sözleşmesi"); font.pixelSize: Theme.heading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiLabel { text: qsTr("Kurallar yeni dataset sürümüne bağlanır. Önizleme veri değiştirmez. Kaynak korunur; düzeltme veya birleşme yalnız açık onay ve Uygula ile gerçekleşir."); Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    UiCombo { id: column; objectName: "contractColumn"; accessibleLabel: qsTr("Sözlük sütunu"); model: dataView.datasetColumns; textRole: "name"; valueRole: "id"; currentIndex: dataView.datasetColumns.findIndex(c => c.id === dataView.selectedColumn); enabled: !operations.busy; onActivated: { dataView.selectColumn(currentValue); panel.loadColumn() } Layout.fillWidth: true }
    ColumnLayout {
        enabled: !operations.busy && !projects.busy && !projects.readOnly
        Layout.fillWidth: true
        UiTextArea { id: meaning; objectName: "contractMeaning"; Accessible.name: qsTr("Sütunun anlamı"); placeholderText: qsTr("Sütunun anlamı"); Layout.fillWidth: true; Layout.preferredHeight: 80; wrapMode: TextEdit.Wrap; onTextEdited: panel.invalidate() }
        UiTextField { id: unit; objectName: "contractUnit"; Accessible.name: qsTr("Kayıtlı ölçüm birimi"); placeholderText: qsTr("Kayıtlı birim: kg, yıl, TL…"); Layout.fillWidth: true; onTextEdited: panel.invalidate() }
        UiCombo { id: level; objectName: "contractMeasurementLevel"; accessibleLabel: qsTr("Ölçüm düzeyi"); property string helpContext: "contract.level"; model: ["Bilinmiyor", "Nominal · sınıf", "Ordinal · sıralı kategori", "Interval · aralık", "Ratio · oran"]; Layout.fillWidth: true; onActivated: panel.invalidate() }
        UiTextField { id: order; objectName: "contractOrder"; Accessible.name: qsTr("Ordinal sıra"); placeholderText: qsTr("Ordinal sıra: düşük|orta|yüksek"); visible: level.currentIndex === 2; Layout.fillWidth: true; onTextEdited: panel.invalidate() }
        UiTextField { id: expectedType; objectName: "contractExpectedType"; Accessible.name: qsTr("Beklenen fiziksel tür"); placeholderText: qsTr("Beklenen fiziksel tür: Int64, String…"); Layout.fillWidth: true; onTextEdited: panel.invalidate() }
        UiTextField { id: expectedUnit; objectName: "contractExpectedUnit"; Accessible.name: qsTr("Sözleşmenin beklediği birim"); placeholderText: qsTr("Beklenen birim; bilinmeyen birim de ihlaldir"); Layout.fillWidth: true; onTextEdited: panel.invalidate() }
        RowLayout {
            Layout.fillWidth: true
            UiTextField { id: minimum; objectName: "contractMinimum"; Accessible.name: qsTr("Geçerli alt sınır"); placeholderText: qsTr("Alt sınır (dahil)"); Layout.fillWidth: true; onTextEdited: panel.invalidate() }
            UiTextField { id: maximum; objectName: "contractMaximum"; Accessible.name: qsTr("Geçerli üst sınır"); placeholderText: qsTr("Üst sınır (dahil)"); Layout.fillWidth: true; onTextEdited: panel.invalidate() }
        }
        UiCheckBox { id: nullable; objectName: "contractNullable"; text: qsTr("Null (bilinmeyen) değer kabul edilir"); checked: true; onClicked: panel.invalidate() }
        UiCheckBox { id: unique; objectName: "contractUnique"; text: qsTr("Null dışındaki değerler benzersiz olmalı"); onClicked: panel.invalidate() }
        UiCombo { id: severity; objectName: "contractSeverity"; accessibleLabel: qsTr("Yeni kuralların ihlal derecesi"); model: ["Hata", "Uyarı"]; Layout.fillWidth: true; onActivated: panel.invalidate() }
        UiCheckBox { id: foreignKey; objectName: "contractForeignKey"; property string helpContext: "contract.reference"; text: qsTr("Referans tabloda bulunma kuralı ekle (foreign key)"); onClicked: panel.invalidate() }
        UiCombo { id: reference; objectName: "contractReference"; accessibleLabel: qsTr("Referans dataset sürümü"); model: operations.secondaryDatasets; textRole: "label"; valueRole: "version_id"; visible: foreignKey.checked; Layout.fillWidth: true; onActivated: panel.invalidate() }
        UiCombo { id: referenceColumn; objectName: "contractReferenceColumn"; accessibleLabel: qsTr("Referans benzersiz sütunu"); model: (operations.secondaryDatasets[reference.currentIndex] || {}).columns || []; textRole: "name"; valueRole: "id"; visible: foreignKey.checked; Layout.fillWidth: true; onActivated: panel.invalidate() }
        UiButton { objectName: "contractPreviewMetadata"; text: qsTr("Sütun sözlüğü ve kurallarını önizle"); Layout.fillWidth: true; onClicked: operations.previewSchemaContract(JSON.stringify(panel.columnRecipe())) }
        UiCheckBox { id: advanced; text: qsTr("Taşınabilir tarif ve tablo kurallarını düzenle") }
        UiTextArea { id: declarative; objectName: "contractRecipeEditor"; Accessible.name: qsTr("Declarative sözleşme tarifi JSON"); visible: advanced.checked; Layout.fillWidth: true; Layout.preferredHeight: 220; wrapMode: TextEdit.Wrap; onTextEdited: panel.invalidate() }
        UiLabel { visible: advanced.checked; text: qsTr("Tarif contract.rules dizisinde row_count için column_id boş, minimum/maximum tam sayı; foreign_key için referans version_id/column_id kullanır. Başka dataset'e aktarırken kimlikleri açıkça yeniden bağla. Kod veya SQL çalıştırılmaz."); Layout.fillWidth: true; wrapMode: Text.Wrap }
        UiButton { objectName: "contractPreviewRecipe"; text: qsTr("Düzenlenen tarifi önizle"); visible: advanced.checked; Layout.fillWidth: true; onClicked: operations.previewSchemaContract(declarative.text) }
        UiTextField { id: exportPath; objectName: "contractExportPath"; Accessible.name: qsTr("Tarif dışa aktarma yolu"); placeholderText: qsTr("Mutlak dışa aktarma yolu: /…/sozlesme.json"); visible: advanced.checked; Layout.fillWidth: true }
        UiButton { objectName: "contractExport"; text: qsTr("Tarifi JSON olarak dışa yaz"); visible: advanced.checked; Layout.fillWidth: true; onClicked: operations.exportContractRecipe(exportPath.text, declarative.text) }
        UiCombo { id: policy; objectName: "contractPolicy"; accessibleLabel: qsTr("Hata ihlalinde davranış"); property string helpContext: "contract.schema"; model: ["Dur · hata varsa yayın engellenir", "Karantina · hatalı kayıtları ayrı sakla", "Devam · ihlalleri koruyup raporla"]; Layout.fillWidth: true; onActivated: panel.invalidate() }
        UiButton { objectName: "contractValidate"; text: qsTr("Kayıtlı sözleşmeyi tam veriyle kontrol et"); Layout.fillWidth: true; onClicked: operations.previewContractCheck(JSON.stringify(panel.recipe.contract), ["stop", "quarantine", "continue"][policy.currentIndex]) }
    }
    UiLabel { text: qsTr("Tablo/tür/birim/sıra tanımı hatası tek tek kayıtları ayırarak düzeltilemez; karantina bu durumda durur. Uyarılar karantinaya alınmaz. Sonuçta hiçbir değer sessizce değiştirilmez."); Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.warning }
    UiLabel { visible: (operations.contractReport.report || {}).dataset_version !== undefined; text: (operations.contractReport.saved ? "Kaydedilmiş girdi kontrolü" : "Girdi kontrol önizlemesi") + (operations.contractReport.current ? "" : " · ESKİ SÜRÜM; yeniden kontrol gerekli") + "\nKontrol edilen sürüm: " + ((operations.contractReport.report || {}).dataset_version || "") + "\nYayın/önizleme çıktı sürümü: " + (operations.contractReport.output_version || "") + " · politika: " + (operations.contractReport.policy || ""); Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
    Repeater {
        model: (operations.contractReport.report || {}).rules || []
        delegate: UiLabel { required property var modelData; text: modelData.rule_id + " · " + ({row:"Satır",column:"Sütun",table:"Tablo",cross_table:"Tablolar arası"}[modelData.level] || modelData.level) + " · " + (modelData.severity === "error" ? "Hata" : "Uyarı") + " · ihlal " + modelData.violations + "\n" + modelData.reason + "\nÖrnekler (en fazla10): " + JSON.stringify(modelData.examples); Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
    }
    UiLabel { text: qsTr("Fuzzy kategori ve insan onaylı kimlik eşleme"); font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiLabel { text: qsTr("Benzer adlar aynı kişi değildir. Blocking aynı gruptaki adayları sınırlar; skor bir olasılık değildir. Birleşme satırları silmez; canonical_id ilişkisi ekler. Eski sonuçlar eski sürüme bağlı kalır, otomatik yeniden hesaplanmaz."); Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.warning }
    UiCombo { id: nameColumn; objectName: "entityNameColumn"; accessibleLabel: qsTr("Ad veya kategori sütunu"); model: dataView.datasetColumns; textRole: "name"; valueRole: "id"; Layout.fillWidth: true; enabled: !operations.busy; onActivated: panel.invalidate() }
    UiCombo { id: blockColumn; objectName: "entityBlockColumn"; accessibleLabel: qsTr("Blocking sütunu"); model: dataView.datasetColumns; textRole: "name"; valueRole: "id"; Layout.fillWidth: true; enabled: !operations.busy; onActivated: panel.invalidate() }
    UiSpinBox { id: threshold; objectName: "entityThreshold"; Accessible.name: qsTr("Benzerlik eşiği yüzde"); property string helpContext: "contract.fuzzy"; from: 0; to: 100; value: 80; Layout.fillWidth: true; enabled: !operations.busy; onValueModified: panel.invalidate() }
    UiTextField { id: reviewer; objectName: "entityReviewer"; Accessible.name: qsTr("Kararı veren kişi"); placeholderText: qsTr("Kararı veren kişi"); Layout.fillWidth: true; enabled: !operations.busy }
    UiTextField { id: reason; objectName: "entityReason"; Accessible.name: qsTr("İnsan onayının gerekçesi"); placeholderText: qsTr("Kimliği doğrulayan kanıt / karar gerekçesi"); Layout.fillWidth: true; enabled: !operations.busy }
    UiButton { objectName: "entityFindCandidates"; property string helpContext: "contract.merge"; text: qsTr("Blocking ile kimlik adaylarını üret"); Layout.fillWidth: true; enabled: !operations.busy && !projects.busy; onClicked: operations.previewIdentityCandidates(nameColumn.currentValue, blockColumn.currentValue, threshold.value / 100) }
    UiButton { objectName: "categoryFindCandidates"; property string helpContext: "contract.fuzzy"; text: qsTr("Kategori eşleme adaylarını üret"); Layout.fillWidth: true; enabled: !operations.busy && !projects.busy; onClicked: operations.previewCategoryCandidates(nameColumn.currentValue, threshold.value / 100) }
    Repeater {
        model: (operations.previewResult.diagnostics || {}).candidates || []
        delegate: ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            UiLabel { text: modelData.left_name + " ↔ " + modelData.right_name + " · skor " + modelData.score.toFixed(3) + " · blocking " + modelData.blocking + "\nRowId " + modelData.left + " / " + modelData.right + "\nKaynak kimlikleri " + modelData.left_source + " / " + modelData.right_source; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
            UiButton { objectName: "entityApprovePair"; text: qsTr("Bu çiftin aynı varlık olduğunu onayla ve önizle"); property string helpContext: "contract.merge"; enabled: !operations.busy && reviewer.text.trim().length > 0 && reason.text.trim().length > 0; Layout.fillWidth: true; multiline: true; onClicked: operations.approveIdentityPair(modelData.left, modelData.right, reviewer.text, reason.text) }
        }
    }
    Repeater {
        model: (operations.previewResult.diagnostics || {}).category_candidates || []
        delegate: ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            UiLabel { text: modelData.left_value + " → " + modelData.right_value + " · skor " + modelData.score.toFixed(3); Layout.fillWidth: true; wrapMode: Text.Wrap }
            UiButton { objectName: "categoryApprovePair"; text: qsTr("Soldaki kategoriyi sağdakine eşlemeyi onayla"); enabled: !operations.busy && reviewer.text.trim().length > 0 && reason.text.trim().length > 0; Layout.fillWidth: true; multiline: true; onClicked: operations.approveCategoryPair(nameColumn.currentValue, modelData.left_value, modelData.right_value, reviewer.text, reason.text) }
            UiButton { objectName: "categoryApproveReversePair"; text: qsTr("Sağdaki kategoriyi soldakine eşlemeyi onayla"); enabled: !operations.busy && reviewer.text.trim().length > 0 && reason.text.trim().length > 0; Layout.fillWidth: true; multiline: true; onClicked: operations.approveCategoryPair(nameColumn.currentValue, modelData.right_value, modelData.left_value, reviewer.text, reason.text) }
        }
    }
    UiLabel { text: operations.errorText; visible: text.length > 0; color: Theme.error; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiLabel { text: operations.message; Layout.fillWidth: true; wrapMode: Text.Wrap }
    RowLayout {
        Layout.fillWidth: true
        UiButton { objectName: "contractApply"; text: qsTr("Önizlemeyi uygula ve kaydet"); enabled: operations.canApply; Layout.fillWidth: true; multiline: true; onClicked: operations.apply() }
        UiButton { objectName: "contractCancel"; text: qsTr("İptal"); enabled: operations.busy && operations.state !== "publishing"; onClicked: operations.cancel() }
    }
    RowLayout {
        UiButton { objectName: "contractUndo"; text: qsTr("Geri al"); property string helpContext: "contract.merge"; enabled: !operations.busy && !projects.busy && !projects.readOnly; onClicked: operations.historyAction("undo") }
        UiButton { objectName: "contractRedo"; text: qsTr("Yinele"); enabled: !operations.busy && !projects.busy && !projects.readOnly; onClicked: operations.historyAction("redo") }
    }
    UiCheckBox { id: journal; text: qsTr("İnsan kararları ve bağlı sonuç/sürüm ilişkilerini göster") }
    Repeater {
        model: journal.checked ? operations.identityJournal : []
        delegate: UiLabel { required property var modelData; text: JSON.stringify(modelData, null, 2); Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
    }
}
