import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id:root
    property var columns:[]
    property string chartKind:""
    property bool advanced:advancedChoice.checked
    signal edited()
    Layout.fillWidth:true
    function order() { return stageOrder.text.trim() ? stageOrder.text.split("|").map(v=>v.trim()):[] }
    function values() { return {parent:chartKind==="treemap" || chartKind==="sunburst" ? parentPicker.currentValue:"",target:chartKind==="sankey" || chartKind==="alluvial" ? targetPicker.currentValue:"",entity:chartKind==="funnel" && unit.currentIndex===0 ? entityPicker.currentValue:"",waterfall_role:chartKind==="waterfall" ? role.currentValue:"",missing_category:missing.currentIndex===0 ? "include":"exclude",funnel_unit:unit.currentIndex===0 ? "people":"events",advanced:advancedChoice.checked,radar_scale:"minmax"} }
    function restore(s) { for(let i=0;i<columns.length;i++) { if(columns[i].id===s.parent) parentPicker.currentIndex=i; if(columns[i].id===s.target) targetPicker.currentIndex=i; if(columns[i].id===s.entity) entityPicker.currentIndex=i; if(columns[i].id===s.waterfall_role) role.currentIndex=i; } stageOrder.text=(s.category_order||[]).join("|"); missing.currentIndex=s.missing_category==="exclude"?1:0; unit.currentIndex=s.funnel_unit==="events"?1:0; advancedChoice.checked=!!s.advanced }
    UiLabel { text:"Kompozisyon linear / tek panel; facet ve ağırlık uygulanmaz. Input şeması sonuçta saklanır. Stack: X + seri/grup + nonnegative Y. Tree: benzersiz string X node + parent + yalnız yaprak Y (iç düğüm0). Flow: string X source + target + nonnegative Y; dengeli DAG. Eksik ölçüm sum'da paydaya girmez; count eksik Y içeren kaydı da sayar."; Layout.fillWidth:true; wrapMode:Text.Wrap }
    UiCombo { id:parentPicker; objectName:"chartParent"; accessibleLabel:"Parent node kimliği"; model:root.columns; textRole:"name"; valueRole:"id"; visible:root.chartKind==="treemap" || root.chartKind==="sunburst"; Layout.fillWidth:true; onActivated:root.edited() }
    UiCombo { id:targetPicker; objectName:"chartTarget"; accessibleLabel:"Target kimliği"; model:root.columns; textRole:"name"; valueRole:"id"; visible:root.chartKind==="sankey" || root.chartKind==="alluvial"; Layout.fillWidth:true; onActivated:root.edited() }
    UiCombo { id:role; objectName:"chartWaterfallRole"; accessibleLabel:"Waterfall start/change/end alanı"; model:root.columns; textRole:"name"; valueRole:"id"; visible:root.chartKind==="waterfall"; Layout.fillWidth:true; onActivated:root.edited() }
    UiCombo { id:unit; objectName:"chartFunnelUnit"; accessibleLabel:"Funnel sayım birimi"; model:["Kişi — aşamada benzersiz kimlik, nested cohort","Olay — tekrarlar dahil; kişi dönüşümü değildir"]; visible:root.chartKind==="funnel"; Layout.fillWidth:true; onActivated:root.edited() }
    UiCombo { id:entityPicker; objectName:"chartEntity"; accessibleLabel:"Funnel kişi kimliği"; model:root.columns; textRole:"name"; valueRole:"id"; visible:root.chartKind==="funnel" && unit.currentIndex===0; Layout.fillWidth:true; onActivated:root.edited() }
    UiTextField { id:stageOrder; Accessible.name:"Kategori veya aşama sırası (dikey çizgi ile ayırın)"; objectName:"chartCompositionOrder"; placeholderText:"Aşama/kategori sırası: Başlangıç|Adım|Bitiş"; visible:root.chartKind!=="radar"; Layout.fillWidth:true; onTextEdited:root.edited() }
    UiCombo { id:missing; objectName:"chartMissingCategory"; accessibleLabel:"Eksik kategorinin paydaya katılımı"; model:["Eksik kategori ayrı pay olarak dahil","Eksik kategori dışlanır; payda azalır"]; Layout.fillWidth:true; onActivated:root.edited() }
    UiCheckBox { id:advancedChoice; objectName:"chartCompositionAdvanced"; text:"Gelişmiş radar seçeneğini aç · minmax; alan eksen sırasına bağlı"; Layout.fillWidth:true; onClicked:root.edited() }
    UiLabel { visible:root.chartKind==="radar"; text:"Radar3–6 sayısal sütun ister. Her sütun ayrı minmax0–1; sabit0.5. Farklı birimler ham ortak eksene yığılmaz. Alan eksen sırasına bağlı; dot/parallel daha açık alternatiftir."; Layout.fillWidth:true; wrapMode:Text.Wrap }
}
