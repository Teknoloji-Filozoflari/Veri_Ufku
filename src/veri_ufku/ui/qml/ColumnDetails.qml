import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    property var details: dataView.columnDetails
    property var profile: dataView.profileResult
    property string helpContext: "column-role"
    signal helpRequested(var origin, string context)
    visible: details.name !== undefined
    spacing: Theme.md
    function val(value) { return value === null || value === undefined ? "tanımsız" : String(value) }
    function approximate(value) { if (value === null || value === undefined) return "tanımsız"; let n = Number(value); return Number.isFinite(n) ? "≈" + n.toPrecision(10) : String(value) }
    function lines(result) {
        if (!result.counts) return "Seçili sütunun profilini hesaplayın."
        let c = result.counts
        let scope = result.scope === "sample" ? "Örnek: ilk N kayıt; temsili garanti edilmez" : result.scope === "filtered" ? "Filtreli alt küme: tam tarama" : "Tüm dataset: tam tarama"
        let text = scope + "\nKullanılan " + result.used_n + " / " + result.population_n + " · Dataset " + result.dataset_rows + " kayıt / " + result.column_count + " sütun\nFiziksel tür " + result.physical_type + " · Rol " + result.role + "\nNull " + c.null + " · NaN " + c.nan + " · +∞ " + c.positive_infinity + " · −∞ " + c.negative_infinity + " · geçerli " + c.valid + " · boş metin " + c.empty_string + "\nEksik (null) oranı: " + (result.null_rate === null ? "tanımsız" : (100 * result.null_rate).toFixed(2) + "%") + " · Unique (null hariç): " + val(result.unique) + "\nÖrnek değerler: " + result.examples.join("; ")
        let n = result.numeric
        if (n && n.minimum !== null) text += "\nSayısal min " + n.minimum + " · max " + n.maximum
        if (n && !n.suppressed) text += "\nSonlu n " + n.finite_n + " · ortalama " + val(n.mean) + " · medyan " + val(n.median) + " · std " + approximate(n.std) + " (ddof=" + n.ddof + ")\nYüzdelikler (linear): " + JSON.stringify(n.quantiles)
        if (result.date_range) text += "\nTarih aralığı: " + result.date_range.minimum + " – " + result.date_range.maximum
        text += "\nEn fazla20 frekans: " + result.frequencies.map(function(f) { return f.value + ": " + f.count }).join("; ") + "\nDiğer kayıtlar: " + val(result.frequency_other_count) + "\n" + result.warnings.join("\n") + "\nProfil veri sürümü: " + result.dataset_version
        return text
    }
    Label { text: "Sütun detayı · " + (panel.details.name || ""); font.pixelSize: Theme.subheading; font.bold: true; wrapMode: Text.Wrap; Layout.fillWidth: true }
    Label { text: "Fiziksel tür: " + (panel.profile.physical_type || panel.details.physical_type || "?") + " · Özgün ad: " + (panel.details.original_name || "(boş)") + "\nColumnId: " + (panel.details.id || ""); wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
    Label { text: "Rol önerisi: " + (panel.details.proposal || "?") + " · " + (panel.details.reason || "") + "\n" + (panel.details.confirmed ? "Kullanıcı tarafından onaylanmış rol." : "Öneri onaylanmadı; rol fiziksel türü değiştirmez."); wrapMode: Text.Wrap; Layout.fillWidth: true }
    ComboBox { id: role; objectName: "columnRole"; property string helpContext: "column-role"; property var values: ["identifier", "category", "measurement", "time", "text", "ordinal", "ignored"]; model: ["Kimlik", "Kategori", "Ölçüm", "Tarih / zaman", "Serbest metin", "Ordinal — sıralı kategori", "Analizde dışarıda"]; currentIndex: Math.max(0, values.indexOf(panel.details.role)); Layout.fillWidth: true; Layout.minimumWidth: 0 }
    Label { text: "Ölçüm birimi (ör. kg, TL)"; wrapMode: Text.Wrap; Layout.fillWidth: true }
    TextField { id: unit; objectName: "columnUnit"; text: panel.details.unit || ""; Layout.fillWidth: true; Layout.minimumWidth: 0 }
    Label { text: "Ordinal kategori sırası (| ile ayır; ör. düşük|orta|yüksek)"; wrapMode: Text.Wrap; Layout.fillWidth: true }
    TextField { id: order; objectName: "columnOrdinalOrder"; text: (panel.details.ordinal_order || []).join("|"); Layout.fillWidth: true; Layout.minimumWidth: 0 }
    Label { text: "Analiz birimi: bir satır neyi temsil ediyor? (ör. satış, kişi, cihaz-gün)"; wrapMode: Text.Wrap; Layout.fillWidth: true }
    TextField { id: analysisUnit; objectName: "datasetAnalysisUnit"; text: panel.details.analysis_unit || ""; Layout.fillWidth: true; Layout.minimumWidth: 0 }
    UiButton { objectName: "applyColumnRole"; text: "Rol ve birimleri proje taslağına uygula"; enabled: !projects.busy && !projects.readOnly; onClicked: dataView.applyRole(role.values[role.currentIndex], unit.text, order.text, analysisUnit.text); Layout.fillWidth: true; multiline: true }
    GridLayout {
        columns: panel.width > 600 * Theme.scale ? 2 : 1
        Layout.fillWidth: true
        ComboBox { id: scope; objectName: "profileTarget"; model: ["Tüm dataset profili", "Tablo görünümünün profili"]; Layout.fillWidth: true; Layout.minimumWidth: 0 }
        ComboBox { id: method; objectName: "profileMethod"; model: ["Örnek: ilk10.000 kayıt", "Tam profil: tüm kayıtları tara"]; Layout.fillWidth: true; Layout.minimumWidth: 0 }
    }
    Label { text: "Standart sapma: ddof=1 örnek; ddof=0 popülasyon. Sayısal hesap yalnız sonlu değerlerde; null/NaN/∞ ayrı sayılır. Yüzdelik yöntemi linear. Tablo filtresi, Tüm dataset profiline uygulanmaz."; wrapMode: Text.Wrap; Layout.fillWidth: true }
    SpinBox { id: ddof; objectName: "profileDdof"; property string helpContext: "profile-std"; from: 0; to: 1; value: 1; Layout.fillWidth: true }
    GridLayout {
        columns: panel.width > 600 * Theme.scale ? 2 : 1
        Layout.fillWidth: true
        UiButton { objectName: "computeColumnProfile"; text: "Seçili sütunun profilini hesapla"; enabled: !projects.busy; onClicked: dataView.computeProfile(method.currentIndex === 0, scope.currentIndex === 0 ? "dataset" : "view", ddof.value); Layout.fillWidth: true; multiline: true }
        UiButton { objectName: "saveColumnProfile"; text: "Bu profili proje taslağına ekle"; enabled: !projects.busy && !projects.readOnly && panel.profile.column_id !== undefined; onClicked: dataView.saveProfile(); Layout.fillWidth: true; multiline: true }
    }
    Label { objectName: "columnProfileSummary"; text: panel.lines(panel.profile); wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
    GridLayout {
        columns: panel.width > 600 * Theme.scale ? 3 : 1
        Layout.fillWidth: true
        UiButton { property string helpContext: "profile-unique"; text: "Unique nedir?"; onClicked: panel.helpRequested(this, "profile-unique"); Layout.fillWidth: true; multiline: true }
        UiButton { property string helpContext: "profile-std"; text: "Standart sapma nedir?"; onClicked: panel.helpRequested(this, "profile-std"); Layout.fillWidth: true; multiline: true }
        UiButton { property string helpContext: "profile-quantile"; text: "Yüzdelik nedir?"; onClicked: panel.helpRequested(this, "profile-quantile"); Layout.fillWidth: true; multiline: true }
    }
    UiButton { text: "Projeyi kaydet"; enabled: !projects.busy && !projects.readOnly && projects.dirty; onClicked: projects.request("save"); Layout.fillWidth: true }
}
