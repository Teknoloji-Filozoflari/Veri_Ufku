import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    signal helpRequested(var origin, string context)
    spacing: Theme.md
    readonly property var draft: {
        try { return JSON.parse(recipe.text) } catch (error) { return ({}) }
    }
    function loadEditor(index) {
        if (!blockTitle || !blockText) return
        let block = (draft.blocks || [])[index]
        blockTitle.text = block ? block.title : ""
        blockText.text = block ? (block.text || block.caption || "") : ""
    }
    UiCheckBox { id: expanded; objectName: "reportBuilderExpanded"; text: "Bilimsel rapor oluşturucu"; Layout.fillWidth: true }
    ColumnLayout {
        visible: expanded.checked
        Layout.fillWidth: true
        UiLabel { text: "Kayıtlı dataset/run ve artifact'lardan çevrimdışı rapor. Oluşturma mevcut analizi yeniden hesaplamaz. Keşifsel/doğrulayıcı ayrımını, model seçimini ve test kullanımını açıklayın. Kullanıcı metni hesap kanıtı değildir."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        UiLabel {
            objectName: "uxReportContextSummary"
            text: {
                let ctx = dataView.uxReportContext(JSON.stringify(preparation.modelCandidates || {}))
                return qsTr("Bağlam: sürüm ") + (ctx.dataset_version || qsTr("yok")) + qsTr(" · grafik notu ") + (ctx.chart_note_count || 0) + qsTr(" · aykırı aday n=") + (ctx.outlier_union_n || 0) + qsTr(" (uygulandı=") + (ctx.outlier_candidates_applied ? qsTr("evet") : qsTr("hayır")) + qsTr(") · model ") + (ctx.model_status || "aday") + qsTr(" auto_fit=") + (ctx.model_auto_fit ? qsTr("evet") : qsTr("hayır")) + "\n" + (ctx.provenance_note || "")
            }
            wrapMode: Text.Wrap
            Layout.fillWidth: true
            color: Theme.secondary
        }
        Flow {
            spacing: Theme.sm; Layout.fillWidth: true
            UiButton { text: "Bilimsel preset"; onClicked: recipe.text=reportBuilder.template("scientific") }
            UiButton { text: "Kısa preset"; onClicked: recipe.text=reportBuilder.template("brief") }
            UiButton {
                objectName: "reportBuilderAppendUxContext"
                text: qsTr("UX bağlamını (sürüm/not/sınır) tarife ekle")
                onClicked: {
                    reviewed.checked = false
                    let ctx = dataView.uxReportContext(JSON.stringify(preparation.modelCandidates || {}))
                    recipe.text = reportBuilder.appendUxContext(recipe.text, JSON.stringify(ctx))
                }
            }
            UiButton { objectName: "reportBuilderHelp"; text: "Bilimsel rapor yardımı"; helpContext: "report.builder"; onClicked: helpRequested(this,"report.builder") }
        }
        UiCombo { id: dataset; objectName: "reportBuilderDataset"; accessibleLabel: "Rapora bağlanacak dataset sürümü"; model: reportBuilder.datasets; textRole: "label"; valueRole: "id"; Layout.fillWidth: true }
        UiLabel { text: dataset.currentIndex>=0 && reportBuilder.datasets[dataset.currentIndex] ? JSON.stringify(reportBuilder.datasets[dataset.currentIndex].columns) : "Dataset yok"; textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
        UiCombo { id: record; objectName: "reportBuilderRecord"; accessibleLabel: "Rapora bağlanacak kayıtlı analiz grafik veya model"; model: reportBuilder.records; textRole: "label"; valueRole: "id"; Layout.fillWidth: true }
        UiCombo { id: kind; objectName: "reportBuilderKind"; accessibleLabel: "Rapor bölüm türü"; model: reportBuilder.kinds; Layout.fillWidth: true }
        UiButton { objectName: "reportBuilderAppend"; text: "Seçili bağ ile bölümü tarife ekle"; onClicked: recipe.text=reportBuilder.appendBlock(recipe.text,kind.currentText,dataset.currentValue||"",record.currentValue||"") }
        UiLabel { text: qsTr("Başlık ve açıklamalar"); font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true }
        UiTextField { id: reportTitle; objectName: "reportTitleEditor"; Accessible.name: qsTr("Rapor başlığı"); text: root.draft.title || ""; Layout.fillWidth: true; maximumLength: 200 }
        UiButton { objectName: "reportTitleApply"; text: qsTr("Rapor başlığını uygula"); onClicked: { reviewed.checked=false; recipe.text=reportBuilder.editText(recipe.text,-1,reportTitle.text,"") } }
        UiCombo { id: blockChoice; objectName: "reportBlockChoice"; accessibleLabel: qsTr("Düzenlenecek rapor bölümü"); model: root.draft.blocks || []; textRole: "title"; Layout.fillWidth: true; onActivated: root.loadEditor(currentIndex); onModelChanged: root.loadEditor(currentIndex); onCurrentIndexChanged: root.loadEditor(currentIndex) }
        UiTextField { id: blockTitle; objectName: "reportBlockTitle"; Accessible.name: qsTr("Bölüm başlığı"); placeholderText: qsTr("Bölüm başlığı"); maximumLength: 200; Layout.fillWidth: true }
        UiTextArea { id: blockText; objectName: "reportBlockText"; Accessible.name: qsTr("Bölüm metni veya grafik açıklaması"); placeholderText: qsTr("Bölüm metni veya grafik açıklaması"); textFormat: TextEdit.PlainText; wrapMode: Text.Wrap; Layout.fillWidth: true; Layout.preferredHeight: 100; visible: { let b=(root.draft.blocks || [])[blockChoice.currentIndex]; return b && ["section","note","assumption","table","chart"].indexOf(b.kind)>=0 } }
        UiButton { objectName: "reportBlockApply"; text: qsTr("Bölümü güncelle"); enabled: blockChoice.currentIndex >= 0; onClicked: { reviewed.checked=false; recipe.text=reportBuilder.editText(recipe.text,blockChoice.currentIndex,blockTitle.text,blockText.text) } }
        UiLabel { text: qsTr("Başlık ve açıklama düzenlemek sayısal sonuçları yeniden hesaplamaz. Veri ve kayıt bağlantıları korunur."); color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.Wrap }
        UiCheckBox { id: advancedRecipe; objectName: "reportAdvancedRecipe"; text: qsTr("Bölüm sırası, hassas alanlar ve gelişmiş tarif"); Layout.fillWidth: true }
        UiLabel { visible: advancedRecipe.checked; text: "Bölüm sırası blocks dizisidir; ColumnId seçimini tarifte düzenleyin. masked_columns açık hassas kolon listesidir. Grafik için allow_graphics=true yalnız görseli inceledikten sonra; grafik metni otomatik maskelenmez. Kaydedilen rapor tarifi yeniden kullanılabilir preset'tir. code_column yalnız dictionary numeric profile script/notebook paketi ekler."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        UiTextArea { id: recipe; visible: advancedRecipe.checked; objectName: "reportBuilderRecipe"; Accessible.name: "Rapor bölüm ve redaction JSON tarifi"; property string helpContext: "report.builder"; textFormat: TextEdit.PlainText; wrapMode: Text.WrapAnywhere; text: reportBuilder.template("scientific"); Layout.fillWidth: true; Layout.preferredHeight: 260 }
        Flow {
            spacing: Theme.sm; Layout.fillWidth: true
            UiButton { objectName: "reportBuilderRedact"; text: "Tarif redaction önizlemesi ve maskele"; onClicked: {reviewed.checked=false; recipe.text=reportBuilder.redactRecipe(recipe.text)} }
            UiButton { objectName: "reportBuilderRun"; text: "Raporu açıkça oluştur ve kaydet"; helpContext: "report.builder"; enabled: !reportBuilder.busy; onClicked: {reviewed.checked=false; reportBuilder.run(recipe.text)} }
            UiButton { objectName: "reportBuilderCancel"; text: "İptal"; enabled: reportBuilder.busy; onClicked: reportBuilder.cancel() }
        }
        UiCombo { id: saved; objectName: "reportBuilderSaved"; accessibleLabel: "Kayıtlı rapor ve preset"; model: reportBuilder.saved; textRole: "label"; valueRole: "id"; Layout.fillWidth: true; onCurrentValueChanged: reviewed.checked=false }
        Flow {
            spacing: Theme.sm; Layout.fillWidth: true
            UiButton { objectName: "reportBuilderOpen"; text: "Raporu hash kontrolüyle incele"; enabled: !!saved.currentValue && !reportBuilder.busy; onClicked: {reviewed.checked=false;reportBuilder.openReport(saved.currentValue)} }
            UiButton { text: "Kaydedilen tarifi preset olarak yükle"; enabled: !!saved.currentValue; onClicked: recipe.text=reportBuilder.reuse(saved.currentValue) }
        }
        UiLabel { objectName: "reportBuilderFreshness"; text: reportBuilder.freshnessText; wrapMode: Text.WrapAnywhere; color: Theme.warning; Layout.fillWidth: true }
        ScrollView {
            id: previewScroll
            Layout.fillWidth: true; Layout.preferredHeight: 420; contentWidth: availableWidth
            Accessible.name: "Rapor bulgu referans ve redaction önizlemesi"
            UiLabel { objectName: "reportBuilderPreview"; width: previewScroll.availableWidth; text: reportBuilder.preview; textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere }
        }
        UiLabel { text: "İnceleyin: sayısal alan→run bağı, manuel yorum, maskelenen alanlar, grafiklerin hassas içeriği, test geçmişi ve kaynakça. Dosyalar çevrimdışıdır. Bağlı grafik SVG/PDF ve tablo CSV/Parquet için ZIP paketini aynı dizine açın. DOCX ve yerel LLM desteklenmiyor. Eski kayıt için güncelleme yeni açık rapor eylemidir; analiz/model recompute kendi aracından ayrıca başlatılır."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        UiCheckBox { id: reviewed; objectName: "reportBuilderReviewed"; text: "Redaction, grafikler, kaynaklar ve bulgu referanslarını inceledim"; Layout.fillWidth: true }
        UiCombo { id: format; objectName: "reportBuilderFormat"; accessibleLabel: "Doğrulanan rapor formatı"; model: ["zip","md","html","pdf"]; Layout.fillWidth: true }
        UiTextField { id: destination; objectName: "reportBuilderDestination"; Accessible.name: "Yeni rapor çıktı dosyası tam yolu"; placeholderText: "Proje dışında yeni /tam/yol/rapor.zip"; Layout.fillWidth: true }
        UiButton { objectName: "reportBuilderExport"; text: "İncelenen raporu dışa aktar"; enabled: !reportBuilder.busy && reviewed.checked && !!saved.currentValue; onClicked: reportBuilder.exportReport(saved.currentValue, format.currentText, destination.text, reviewed.checked) }
        UiLabel { objectName: "reportBuilderError"; text: reportBuilder.errorText; color: Theme.warning; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    }
}
