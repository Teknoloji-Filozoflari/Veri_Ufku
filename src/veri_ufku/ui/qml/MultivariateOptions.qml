import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id:root
    property var columns:[]
    property int selectedCount:0
    property string chartKind:""
    signal edited()
    Layout.fillWidth:true
    function values() { return {size:chartKind==="bubble" ? size.currentValue:"", bubble_encoding:encoding.currentIndex===0 ? "area":"radius", facet_scale:scale.currentIndex===0 ? "shared":"independent", heatmap_scale:heat.currentIndex===0 ? "raw":"column-zscore", heatmap_order:order.currentIndex===0 ? "input":"alphabetical", cluster_method:["average","complete","ward"][cluster.currentIndex]} }
    function restore(s) { for(let i=0;i<columns.length;i++) if(columns[i].id===s.size) size.currentIndex=i; encoding.currentIndex=s.bubble_encoding==="radius"?1:0; scale.currentIndex=s.facet_scale==="independent"?1:0; heat.currentIndex=s.heatmap_scale==="column-zscore"?1:0; order.currentIndex=s.heatmap_order==="alphabetical"?1:0; cluster.currentIndex=Math.max(0,["average","complete","ward"].indexOf(s.cluster_method)) }
    UiLabel { text:"Önkontrol: seçili "+root.selectedCount+" sütun; pair "+(root.selectedCount*root.selectedCount)+" panel. En fazla6 sütun /36 panel /4 facet. Satır limiti aşılırsa açık ilk-N örnek veya CPU aggregation seçin."; Layout.fillWidth:true; wrapMode:Text.Wrap }
    UiLabel { text:"Bubble boyut ölçümü"; visible:root.chartKind==="bubble"; Layout.fillWidth:true }
    UiCombo { id:size; objectName:"chartSize"; accessibleLabel:"Bubble boyut ölçümü"; model:root.columns; textRole:"name"; valueRole:"id"; visible:root.chartKind==="bubble"; Layout.fillWidth:true; onActivated:root.edited() }
    UiCombo { id:encoding; objectName:"chartBubbleEncoding"; accessibleLabel:"Bubble kodlama"; model:["Alan değerle orantılı","Yarıçap değerle orantılı (alan karesel)"]; visible:root.chartKind==="bubble"; Layout.fillWidth:true; onActivated:root.edited() }
    UiCombo { id:scale; objectName:"chartFacetScale"; accessibleLabel:"Facet eksen ölçeği"; model:["Ortak eksen sınırları","Bağımsız eksen sınırları"]; Layout.fillWidth:true; onActivated:root.edited() }
    UiCombo { id:heat; objectName:"chartHeatmapScale"; accessibleLabel:"Heatmap ölçek"; model:["Ham agregasyon","Sütun z-score (ddof0)"]; visible:root.chartKind.indexOf("heatmap")>=0; Layout.fillWidth:true; onActivated:root.edited() }
    UiCombo { id:order; objectName:"chartHeatmapOrder"; accessibleLabel:"Heatmap sıra"; model:["İlk görülen grup sırası","Alfabetik grup sırası"]; visible:root.chartKind.indexOf("heatmap")>=0; Layout.fillWidth:true; onActivated:root.edited() }
    UiCombo { id:cluster; objectName:"chartClusterMethod"; accessibleLabel:"Kümeleme yöntemi"; model:["Average / Euclidean","Complete / Euclidean","Ward / Euclidean"]; visible:root.chartKind==="clustered-heatmap"; Layout.fillWidth:true; onActivated:root.edited() }
}
