import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "qualityPanel"
    property string helpContext: "dataset.quality"
    property var rules: []
    property var duplicates: []
    property string boundDataset: ""
    Connections { target: dataView; function onChanged() { if (panel.boundDataset!==dataView.selectedDataset) { panel.rules=[]; panel.duplicates=[]; panel.boundDataset=dataView.selectedDataset } } }
    signal helpRequested(var origin, string context)
    function columnLabel(id) { for(let c of dataView.datasetColumns) if(c.id===id) return c.name; return "Sütun artık seçili dataset içinde değil" }
    function findingLabel(code) { return ({missing:"Eksik değer",nonfinite:"NaN / sonsuz",whitespace:"Boş metin / boşluk",conversion:"Tip dönüşümü",invalid_date:"Geçersiz tarih",rule:"Kural ihlali",uniqueness:"Benzersizlik ihlali",duplicates_full:"Tam satır tekrarı",duplicates_selected:"Seçili sütun tekrarı",constant:"Sabit sütun",category_similarity:"Benzer kategori adayları",outlier:"Aykırı gözlem adayı"})[code] || code }
    spacing: Theme.md
    Label { text: "Veri kalitesi merkezi"; font.pixelSize: Theme.heading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
    Label { text: "Tarama salt okunurdur. Evrensel kalite puanı üretilmez. Adaylar hata veya silme kararı değildir. Eksiklik nedeni veriden tek başına belirlenemez."; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiCombo {
        model: dataView.datasets; textRole: "label"; valueRole: "id"
        currentIndex: { let ds = dataView.datasets; for (let i=0;i<ds.length;i++) if(ds[i].id===dataView.selectedDataset) return i; return -1 }
        onActivated: { panel.rules=[]; panel.duplicates=[]; dataView.selectDataset(currentValue) }
        enabled: !projects.busy; Layout.fillWidth: true; Layout.minimumWidth: 0
    }
    GridLayout {
        columns: panel.width > 600 * Theme.scale ? 2 : 1
        Layout.fillWidth: true
        Label { text: "Tarama miktarı" }
        UiCombo { id: amount; objectName: "qualityAmount"; model: ["Örneklem — ilk N kayıt", "Tüm seçili kapsam"]; Layout.fillWidth: true; Layout.minimumWidth: 0 }
        Label { text: "Kapsam" }
        UiCombo { id: target; model: ["Tüm dataset", "Aktif tablo filtreleri"]; Layout.fillWidth: true; Layout.minimumWidth: 0 }
        Label { text: "Amaç" }
        UiCombo { id: purpose; model: ["Veriyi incelemek", "Temizliğe hazırlanmak", "Modellemeye hazırlanmak"]; Layout.fillWidth: true; Layout.minimumWidth: 0 }
    }
    Label { text: "Tablo filtreleri: "+(dataView.filters.length ? dataView.filters.map(f => panel.columnLabel(f.column_id)+" "+f.operator+" "+f.value).join("; ") : "yok")+". Tüm dataset seçimi bu filtreleri uygulamaz."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
    Label { text: "Tekrar anahtarı: aşağıdan sütunları seçin. Tam satır tekrarları ayrıca taranır; tekrar grubunun tüm üyeleri sayılır. Seçim boşsa yalnız tam satır tekrarları taranır."; Layout.fillWidth: true; wrapMode: Text.Wrap }
    Flow {
        Layout.fillWidth: true; spacing: Theme.sm
        Repeater {
            model: dataView.datasets.length ? dataView.datasetColumns : []
            CheckBox { required property var modelData; text: modelData.name; enabled: !projects.busy; checked: panel.duplicates.indexOf(modelData.id)>=0; onToggled: { let ids=panel.duplicates.slice(); if(checked) ids.push(modelData.id); else ids=ids.filter(x=>x!==modelData.id); panel.duplicates=ids } }
        }
    }
    Label { text: "Kullanıcı kuralları (en fazla32). Null, gerekli değer kuralı olmadıkça dönüşüm/aralık ihlali sayılmaz. İzin verilen etiketler birebir karşılaştırılır."; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiCombo { id: column; objectName: "qualityRuleColumn"; model: dataView.datasetColumns; textRole: "name"; valueRole: "id"; Layout.fillWidth: true; Layout.minimumWidth: 0 }
    UiCombo { id: kind; objectName: "qualityRuleKind"; model: ["Gerekli değer", "Benzersiz (null hariç)", "Sayısal aralık", "İzin verilen etiketler", "Sonlu sayıya dönüşebilir", "Geçerli tarih", "Hedef türe kayıpsız dönüşebilir"]; Layout.fillWidth: true; Layout.minimumWidth: 0 }
    TextField { id: value; objectName: "qualityRuleValue"; placeholderText: "Alt sınır / A|B|C / int64,float64,boolean,date / ISO, %Y-%m-%d, %d.%m.%Y, %d/%m/%Y"; Layout.fillWidth: true; Layout.minimumWidth: 0; maximumLength: 1000; Accessible.name: "Kural değeri veya tarih biçimi" }
    TextField { id: upper; objectName: "qualityRuleUpper"; visible: kind.currentIndex===2; placeholderText: "Üst sınır"; Layout.fillWidth: true; Layout.minimumWidth: 0; maximumLength: 1000; Accessible.name: "Aralık üst sınırı" }
    Flow {
        Layout.fillWidth: true; spacing: Theme.sm
        UiButton { objectName: "qualityAddRule"; text: "Kural ekle"; enabled: !projects.busy && column.currentIndex>=0 && panel.rules.length<32; onClicked: panel.rules=panel.rules.concat([{column_id:column.currentValue,kind:["required","unique","range","allowed","number","date","convert"][kind.currentIndex],value:value.text,upper:upper.text}]) }
        UiButton { text: "Kuralları temizle"; enabled: !projects.busy; onClicked: panel.rules=[] }
    }
    Repeater {
        model: panel.rules
        Label { required property var modelData; text: "Kural: "+modelData.kind+" · "+panel.columnLabel(modelData.column_id)+" · "+modelData.value+" … "+modelData.upper; Layout.fillWidth: true; wrapMode: Text.Wrap }
    }
    Flow {
        Layout.fillWidth: true; spacing: Theme.sm
        UiButton { objectName: "qualityScanButton"; text: "Kaliteyi tara"; primary: true; enabled: !projects.busy && dataView.datasets.length>0; onClicked: dataView.computeQuality(amount.currentIndex===0,target.currentIndex===0 ? "dataset":"view",["inspect","clean","model"][purpose.currentIndex],JSON.stringify(panel.duplicates),JSON.stringify(panel.rules)) }
        UiButton { text: "İptal"; enabled: dataView.busy; onClicked: dataView.cancel() }
        UiButton { objectName: "qualitySaveButton"; text: "Raporu proje taslağına ekle"; enabled: !projects.busy && !projects.readOnly && !!dataView.qualityResult.dataset_version; onClicked: dataView.saveQuality() }
        UiButton { text: "Bu ne işe yarar?"; helpContext: "dataset.quality"; onClicked: panel.helpRequested(this,"dataset.quality") }
    }
    StateNotice { Layout.fillWidth: true; kind: dataView.errorText ? "error" : dataView.busy ? "loading":"info"; heading: "Kalite taraması"; detail: dataView.errorText || dataView.message }
    Label {
        objectName: "qualityScope"
        visible: !!dataView.qualityResult.dataset_version
        text: "Son tamamlanan tarama · Kapsam: "+({full:"Tüm veri",filtered:"Filtreli kapsam",sample:"Örneklem"}[dataView.qualityResult.scope])+" · taranan "+dataView.qualityResult.used_n+" / kapsam "+dataView.qualityResult.population_n+" / toplam veri "+dataView.qualityResult.dataset_n+"\nSürüm: "+dataView.qualityResult.dataset_version+"\nÖrneklemde oran yalnız taranan kayıtları anlatır. Bulgular örtüşebilir; sayıları toplanmaz."
        Layout.fillWidth: true; wrapMode: Text.Wrap
    }
    Label { visible: !!dataView.qualityResult.import_exclusions; text: "Import dışında bırakılan kayıt: "+(dataView.qualityResult.import_exclusions || {}).count+". Karantina kayıtları dataset taramasına dahil değildir; import raporundan incelenir."; Layout.fillWidth: true; wrapMode: Text.Wrap }
    Repeater { model: dataView.qualityResult.warnings || []; Label { required property string modelData; text: modelData; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.warning } }
    Label { visible: !!dataView.qualityResult.dataset_version && (dataView.qualityResult.findings || []).length===0; text: "Bu kapsam ve kurallarla bulgu bulunmadı; verinin kusursuz olduğu anlamına gelmez."; Layout.fillWidth: true; wrapMode: Text.Wrap }
    Repeater {
        model: dataView.qualityResult.findings || []
        Frame {
            required property var modelData
            Layout.fillWidth: true
            padding: Theme.md
            ColumnLayout {
                width: parent.width; spacing: Theme.sm
                Label { text: modelData.column+" · "+panel.findingLabel(modelData.code)+" · "+({candidate:"Şüpheli aday",violation:"Kesin kural ihlali",observation:"Gözlem"}[modelData.classification]); font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
                Label { text: modelData.count+" / "+modelData.denominator+" kayıt (%"+(modelData.ratio*100).toFixed(2)+") · "+modelData.scope+"\n"+modelData.reason; Layout.fillWidth: true; wrapMode: Text.Wrap; textFormat: Text.PlainText }
                Repeater { model: modelData.examples; Label { required property var modelData; text: modelData.values+(preferences.view === "advanced" ? "\nRowId: "+modelData.row_id : ""); Layout.fillWidth: true; wrapMode: Text.Wrap; textFormat: Text.PlainText } }
                Label { text: "Seçenekler: "+modelData.options.join("; ")+"\nÖneri: "+modelData.recommendation.reason+"\nÖnkoşul: "+modelData.recommendation.precondition+"\nEtki: "+modelData.recommendation.impact+"\nYalnız bilgi; düzeltme işlemi henüz mevcut değil."+(preferences.view === "advanced" ? "\nİşlem kimliği: "+modelData.recommendation.operation_id : ""); Layout.fillWidth: true; wrapMode: Text.Wrap; textFormat: Text.PlainText }
                UiButton { text: "Bulgu yardımı"; onClicked: panel.helpRequested(this,modelData.learning_id) }
            }
        }
    }
}
