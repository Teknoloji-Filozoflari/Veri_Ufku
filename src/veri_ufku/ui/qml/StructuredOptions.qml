import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
    id: panel
    signal helpRequested(var origin, string context)
    property bool json: imports.formatId === "json" || imports.formatId === "jsonl"
    property bool excel: imports.formatId === "xlsx" || imports.formatId === "ods"
    enabled: !imports.busy
    Label { text: "Seçimler aynı değişmez kopyaya uygulanır. Önizleme en fazla 200 kaynak kaydıdır; tam import türleri yeniden doğrular. JSON sayıları Decimal/büyük integer olarak incelenir. json_text açık ve kayıpsız JSON metni dönüşümüdür; metin değerleri de tırnaklarıyla saklanır."; wrapMode: Text.Wrap; Layout.fillWidth: true }
    Label { visible: panel.json; text: "Kayıt yolu: kök liste için boş, nested için JSON Pointer (ör. /payload/records)."; wrapMode: Text.Wrap; Layout.fillWidth: true }
    ComboBox { objectName: "jsonRecordPaths"; visible: imports.formatId === "json"; model: imports.choices.record_paths || []; onActivated: imports.setOption("record_path", currentText); Layout.fillWidth: true }
    TextField { objectName: "jsonRecordPath"; property string helpContext: "import-json-path"; visible: imports.formatId === "json"; text: imports.settings.record_path || ""; placeholderText: "/payload/records"; onEditingFinished: imports.setOption("record_path", text); Layout.fillWidth: true }
    CheckBox { id: flattenOption; Layout.fillWidth: true; Layout.minimumWidth: 0; contentItem: Label { text: flattenOption.text; leftPadding: flattenOption.indicator.width + flattenOption.spacing; wrapMode: Text.Wrap; verticalAlignment: Text.AlignVCenter } objectName: "jsonFlatten"; property string helpContext: "import-flatten"; visible: panel.json; text: "Nesne alanlarını düzleştir (listeleri açmaz)"; checked: imports.settings.flatten || false; onClicked: imports.setOption("flatten", checked) }
    Label { visible: panel.json; text: "Liste yolları: " + (imports.choices.list_paths || []).join(", ") + "\nAçılacak yolları | ile ayırın. İki listenin uzunluğu 2 ve 3 ise tek kayıt 6 satır üretir. Boş/null liste bir satır korunur. Seçimden sonra yeniden önizleyin."; wrapMode: Text.Wrap; Layout.fillWidth: true }
    TextField { objectName: "jsonExpandLists"; visible: panel.json; text: (imports.settings.expand_lists || []).join("|"); placeholderText: "/items|/tags"; onEditingFinished: imports.setOption("expand_lists", text); Layout.fillWidth: true }
    Label { visible: panel.excel; text: (imports.formatId === "ods" ? "ODS sayfası · tarih sistemi " : "Excel sayfası · tarih sistemi ") + (imports.choices.date_system || "?"); Layout.fillWidth: true }
    ComboBox { objectName: "excelSheet"; property string helpContext: "import-excel-sheet"; visible: panel.excel || imports.formatId === "sqlite"; model: imports.choices.sheets || []; currentIndex: Math.max(0, model.indexOf(imports.settings.sheet || "")); onActivated: imports.setOption("sheet", currentText); Layout.fillWidth: true }
    Label { visible: imports.formatId === "sqlite"; text: "Salt okunur SQLite tablosu. " + (imports.choices.formula_behavior || ""); wrapMode: Text.WordWrap; Layout.fillWidth: true }
    Label { visible: panel.excel; text: "Veri aralığı (ör. A1:D100; boş: sayfa boyutu)"; wrapMode: Text.Wrap; Layout.fillWidth: true }
    TextField { objectName: "excelRange"; visible: panel.excel; text: imports.settings.cell_range || ""; placeholderText: "Veri aralığı: A1:D100 (boş: sayfa boyutu)"; onEditingFinished: imports.setOption("cell_range", text); Layout.fillWidth: true }
    Label { visible: panel.excel; text: "Başlık satırı (0: başlıksız)"; Layout.fillWidth: true }
    SpinBox { objectName: "excelHeader"; visible: panel.excel; from: 0; to: 1048576; editable: true; value: imports.settings.header_row || 0; onValueModified: imports.setOption("header_row", value); Layout.fillWidth: true }
    Label { visible: panel.excel; text: "Başlık fiziksel satır numarasıdır; 0 başlıksız. " + (imports.choices.formula_behavior || ""); wrapMode: Text.Wrap; Layout.fillWidth: true }
    Label { visible: panel.json || panel.excel; text: "Karışık tür / hassasiyet sınırı"; Layout.fillWidth: true }
    ComboBox { objectName: "mixed_policy"; visible: panel.json || panel.excel; property var values: ["reject", "json_text"]; model: ["Durdur: türü kullanıcı seçsin", "Kayıpsız JSON metnine dönüştür"]; currentIndex: values.indexOf(imports.settings.mixed_policy); onActivated: imports.setOption("mixed_policy", values[currentIndex]); Layout.fillWidth: true }
    Label { visible: panel.excel; text: "Birleşik hücre"; Layout.fillWidth: true }
    ComboBox { objectName: "merged_cells"; visible: panel.excel; property var values: ["reject", "anchor"]; model: ["Durdur", "Yalnız sol üst hücre"]; currentIndex: values.indexOf(imports.settings.merged_cells); onActivated: imports.setOption("merged_cells", values[currentIndex]); Layout.fillWidth: true }
    Label { visible: panel.excel; text: "Boş satır"; Layout.fillWidth: true }
    ComboBox { objectName: "blank_rows"; visible: panel.excel; property var values: ["keep", "skip"]; model: ["Boş satırları koru", "Boş satırları çıkar"]; currentIndex: values.indexOf(imports.settings.blank_rows); onActivated: imports.setOption("blank_rows", values[currentIndex]); Layout.fillWidth: true }
    Label { visible: panel.excel; text: "Formül hücresi"; Layout.fillWidth: true }
    ComboBox { objectName: "formulas"; visible: panel.excel; property var values: ["formula", "text", "cached"]; model: ["Formülü göster (= ile)", "Formül metnini göster", "Dosyadaki önbellek değerini al"]; currentIndex: values.indexOf(imports.settings.formulas); onActivated: imports.setOption("formulas", values[currentIndex]); Layout.fillWidth: true }
    Label { visible: panel.excel; text: "Excel tarih"; Layout.fillWidth: true }
    ComboBox { objectName: "excel_dates"; visible: panel.excel; property var values: ["dates", "serial"]; model: ["Saat dilimsiz tarih", "Asıl seri sayıyı koru"]; currentIndex: values.indexOf(imports.settings.excel_dates); onActivated: imports.setOption("excel_dates", values[currentIndex]); Layout.fillWidth: true }
    Label { visible: panel.json || panel.excel; text: "Bozuk kayıt"; Layout.fillWidth: true }
    ComboBox { objectName: "bad_rows"; visible: panel.json || panel.excel; property var values: ["stop", "quarantine"]; model: ["Durdur", "Raporlu karantina"]; currentIndex: values.indexOf(imports.settings.bad_rows); onActivated: imports.setOption("bad_rows", values[currentIndex]); Layout.fillWidth: true }
    Label { visible: panel.json || panel.excel; text: "Açık tür dönüşümü için tarih biçimi"; wrapMode: Text.Wrap; Layout.fillWidth: true }
    TextField { visible: panel.json || panel.excel; text: imports.settings.date_format || ""; placeholderText: "Açık tarih dönüşümü: %Y-%m-%d"; onEditingFinished: imports.setOption("date_format", text); Layout.fillWidth: true }
    Label { visible: panel.json || panel.excel; text: "Açık datetime dönüşümü için saat dilimi (boş: saat dilimsiz)"; wrapMode: Text.Wrap; Layout.fillWidth: true }
    TextField { visible: panel.json || panel.excel; text: imports.settings.timezone || ""; placeholderText: "Açık datetime dönüşümü: Europe/Istanbul; boş: naive"; onEditingFinished: imports.setOption("timezone", text); Layout.fillWidth: true }
    Label { visible: ["parquet", "ipc", "ipc_stream"].indexOf(imports.formatId) >= 0; text: "Parquet nullable, Decimal, integer, tarih, zaman birimi, timezone ve list/struct türleri korunur. Desteklenmeyen tür hata verir. Nested alanları bu adaptör açmaz. Naive tarih UTC kabul edilmez."; wrapMode: Text.Wrap; Layout.fillWidth: true }
}
