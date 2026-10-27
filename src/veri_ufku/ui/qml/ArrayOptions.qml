import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    signal helpRequested(var origin, string context)
    property string helpContext: "array-dimensions"
    spacing: Theme.md
    UiLabel { text: "Çok boyutlu kaynak · değişken ve kesit seç"; wrapMode: Text.Wrap; Layout.fillWidth: true }
    UiLabel { text: "Takvim, birim ve boyutlar metadata ile korunur. İndeks 0'dan başlar; bitiş dahil değildir. HDF5 her eksende dimension scale ister. Tablo kolonlarından tensor çıkarılmaz."; wrapMode: Text.Wrap; Layout.fillWidth: true }
    UiCombo { objectName: "arrayVariable"; accessibleLabel: "Array ölçüm değişkeni"; property string helpContext: "array-dimensions"; model: ["Değişken seç…"].concat(imports.choices.array_variables || []); currentIndex: Math.max(0, model.indexOf(imports.settings.array_variable || "")); onActivated: if (currentIndex > 0) imports.setOption("array_variable", currentText); Layout.fillWidth: true }
    UiLabel { text: "Boyut kesiti · JSON indeks veya [başlangıç,bitiş,adım]"; wrapMode: Text.Wrap; Layout.fillWidth: true }
    UiTextField { objectName: "arraySlice"; Accessible.name: "Boyut kesiti"; property string helpContext: "array-chunks"; text: JSON.stringify(imports.settings.array_slice || {}); placeholderText: '{"time":0,"latitude":[0,10,1]}'; onEditingFinished: imports.setOption("array_slice", text); Layout.fillWidth: true }
    UiLabel { text: "Koordinat adları | ile · boşsa tüm uygun kaynak koordinatları"; wrapMode: Text.Wrap; Layout.fillWidth: true }
    UiTextField { objectName: "arrayCoordinates"; Accessible.name: "Seçili kaynak koordinatları"; property string helpContext: "array-dimensions"; text: (imports.settings.array_coordinates || []).join("|"); onEditingFinished: imports.setOption("array_coordinates", text); Layout.fillWidth: true }
    UiCheckBox { objectName: "arrayDecode"; text: "Fill/no-data ve CF scale/offset çözümünü uygula (kaynağı değiştirmez)"; property string helpContext: "array-units"; checked: imports.settings.array_decode || false; onToggled: imports.setOption("array_decode", checked); Layout.fillWidth: true }
    UiLabel { text: "Hedef birim · boşsa kaynak birimi. Dönüşüm için fill/scale çözümünü açın."; wrapMode: Text.Wrap; Layout.fillWidth: true }
    UiTextField { objectName: "arrayUnit"; Accessible.name: "Hedef ölçüm birimi"; property string helpContext: "array-units"; text: imports.settings.array_unit || ""; placeholderText: "kelvin"; onEditingFinished: imports.setOption("array_unit", text); Layout.fillWidth: true }
    UiLabel { text: "Tam tablo için satır sınırı · aşılırsa yalnız maliyet gösterilir"; wrapMode: Text.Wrap; Layout.fillWidth: true }
    UiSpinBox { Accessible.name: "Array tablo satır sınırı"; property string helpContext: "array-chunks"; from: 1; to: 10000000; editable: true; value: imports.settings.max_rows || 10000000; onValueModified: imports.setOption("max_rows", value); Layout.fillWidth: true }
    UiLabel { text: imports.formatMetadata; visible: text.length > 0; textFormat: Text.PlainText; wrapMode: Text.Wrap; Layout.fillWidth: true }
    UiButton { visible: false; text: "Boyut, kesit ve maliyet ne demek?"; property string helpContext: "array-dimensions"; onClicked: panel.helpRequested(this, helpContext); Layout.fillWidth: true }
}
