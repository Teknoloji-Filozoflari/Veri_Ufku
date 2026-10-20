import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: options
    property var columns: []
    property string chartKind: ""
    property bool intervalKind: chartKind === "error-bar" || chartKind === "ci-band"
    property string helpContext: "chart.density"
    signal edited()
    Layout.fillWidth: true
    spacing: Theme.md
    function chosen(picker) { return picker.currentIndex>0 ? picker.currentValue : "" }
    function pick(picker,value) { picker.currentIndex=0; for(let i=0;i<picker.model.length;i++) if(picker.model[i].id===value) picker.currentIndex=i }
    function values() {
        return {facet:chosen(facet),weight:chosen(weight),weight_type:["none","frequency","analytic"][weightType.currentIndex],normalization:["count","probability","density","percent"][normalization.currentIndex],bandwidth:bandwidth.currentIndex===0 ? "scott":"silverman",bandwidth_factor:factor.value/100,uncertainty:["sd","se","ci"][uncertainty.currentIndex],confidence:confidence.value/100,xscale:["linear","log","symlog"][xscale.currentIndex],yscale:["linear","log","symlog"][yscale.currentIndex],linthresh:Number(threshold.text),category_order:order.text.length ? order.text.split("|"):[],palette:["accessible","viridis","grayscale"][palette.currentIndex],font:["DejaVu Sans","DejaVu Serif","DejaVu Sans Mono"][font.currentIndex],font_size:fontSize.value,annotation:annotation.text,dpi:dpi.value}
    }
    function restore(s) {
        pick(facet,s.facet);pick(weight,s.weight)
        weightType.currentIndex=["none","frequency","analytic"].indexOf(s.weight_type||"none")
        normalization.currentIndex=["count","probability","density","percent"].indexOf(s.normalization||"count")
        bandwidth.currentIndex=s.bandwidth==="silverman" ? 1:0;factor.value=(s.bandwidth_factor||1)*100
        uncertainty.currentIndex=["sd","se","ci"].indexOf(s.uncertainty||"ci");confidence.value=(s.confidence||.95)*100
        xscale.currentIndex=["linear","log","symlog"].indexOf(s.xscale||"linear");yscale.currentIndex=["linear","log","symlog"].indexOf(s.yscale||"linear")
        threshold.text=String(s.linthresh||1);order.text=(s.category_order||[]).join("|")
        palette.currentIndex=["accessible","viridis","grayscale"].indexOf(s.palette||"accessible")
        font.currentIndex=["DejaVu Sans","DejaVu Serif","DejaVu Sans Mono"].indexOf(s.font||"DejaVu Sans")
        fontSize.value=s.font_size||11;annotation.text=s.annotation||"";dpi.value=s.dpi||120
    }
        UiLabel { text:"Özetleme: her X / grup / facet için ortalama (mean). SD, SE veya noktasal CI açık seçilir."; visible:options.intervalKind; Layout.fillWidth:true; wrapMode:Text.Wrap }
        UiCombo { id:uncertainty; objectName:"chartUncertainty"; accessibleLabel:"Hata çubuğu / band anlamı"; model:["SD — gözlemlerin standart sapması","SE — ortalamanın standart hatası","CI — Student-t ortalama güven aralığı"]; currentIndex:2; Layout.fillWidth:true; visible:options.intervalKind || expanded.checked; onActivated:options.edited(); property string helpContext:"chart.uncertainty" }
        UiLabel { text:"CI güven düzeyi (yüzde); noktasal, bağımsız gözlem varsayımı"; visible:(options.intervalKind || expanded.checked) && uncertainty.currentIndex===2; Layout.fillWidth:true; wrapMode:Text.Wrap }
        UiSpinBox { id:confidence; objectName:"chartConfidence"; Accessible.name:"CI güven düzeyi yüzde"; visible:(options.intervalKind || expanded.checked) && uncertainty.currentIndex===2; from:80; to:99; value:95; editable:true; onValueModified:options.edited() }
    UiCheckBox { id:expanded; objectName:"chartDistributionSettings"; text:"Dağılım, belirsizlik ve görünüm ayarları"; Layout.fillWidth:true }
    ColumnLayout {
        visible:expanded.checked; Layout.fillWidth:true; spacing:Theme.md
        UiLabel { text:"Facet en fazla 4 panel. Ağırlık yalnız histogram/box/violin/KDE/ECDF için; survey ve sample_weight desteklenmez. Ayarlar veri sürümünü değiştirmez."; Layout.fillWidth:true; wrapMode:Text.Wrap }
        UiCombo { id:facet; objectName:"chartFacet"; accessibleLabel:"Facet sütunu"; model:[{id:"",name:"Facet yok"}].concat(options.columns); textRole:"name"; valueRole:"id"; Layout.fillWidth:true; onActivated:options.edited() }
        UiCombo { id:weight; objectName:"chartWeight"; accessibleLabel:"Ağırlık sütunu"; model:[{id:"",name:"Ağırlık yok"}].concat(options.columns); textRole:"name"; valueRole:"id"; Layout.fillWidth:true; onActivated:options.edited() }
        UiCombo { id:weightType; objectName:"chartWeightType"; accessibleLabel:"Ağırlık türü"; model:["Ağırlık kullanılmaz","Frekans — tam sayı tekrar sayısı","Analitik — betimsel pozitif kütle"]; Layout.fillWidth:true; onActivated:options.edited(); property string helpContext:"weights.types" }
        UiCombo { id:normalization; objectName:"chartNormalization"; accessibleLabel:"Histogram normalizasyonu"; model:["Histogram: sayım / ağırlık toplamı","Histogram: olasılık — yükseklik toplamı 1","Histogram: yoğunluk — alan 1","Histogram: yüzde — yükseklik toplamı 100"]; Layout.fillWidth:true; onActivated:options.edited(); property string helpContext:"chart.density" }
        UiCombo { id:bandwidth; objectName:"chartBandwidth"; accessibleLabel:"KDE bandwidth kuralı"; model:["Scott bandwidth","Silverman bandwidth"]; Layout.fillWidth:true; onActivated:options.edited() }
        UiLabel { text:"Bandwidth çarpanı (yüzde)"; Layout.fillWidth:true }
        UiSpinBox { id:factor; objectName:"chartBandwidthFactor"; Accessible.name:"Bandwidth çarpanı yüzde"; from:5; to:1000; value:100; editable:true; onValueModified:options.edited() }
        UiCombo { id:xscale; objectName:"chartXScale"; accessibleLabel:"X eksen ölçeği"; model:["X linear","X log — pozitif değerler gerekli","X symlog — sıfır / negatif destekli"]; Layout.fillWidth:true; onActivated:options.edited(); property string helpContext:"chart.log" }
        UiCombo { id:yscale; objectName:"chartYScale"; accessibleLabel:"Y eksen ölçeği"; model:["Y linear","Y log — pozitif değerler gerekli","Y symlog — sıfır / negatif destekli"]; Layout.fillWidth:true; onActivated:options.edited(); property string helpContext:"chart.log" }
        UiTextField { id:threshold; objectName:"chartLinthresh"; text:"1"; placeholderText:"Symlog doğrusal eşik"; Accessible.name:"Symlog doğrusal eşik"; Layout.fillWidth:true; onTextEdited:options.edited() }
        UiTextField { id:order; objectName:"chartCategoryOrder"; placeholderText:"Tüm grup etiketleri: B|A (boş: kaynak sırası)"; Accessible.name:"Kategorik grup sırası"; maximumLength:4000; Layout.fillWidth:true; onTextEdited:options.edited() }
        UiCombo { id:palette; objectName:"chartPalette"; accessibleLabel:"Grafik renk paleti"; model:["Okabe-Ito erişilebilir palet","Viridis paleti","Gri tonları"]; Layout.fillWidth:true; onActivated:options.edited() }
        UiCombo { id:font; objectName:"chartFont"; accessibleLabel:"Grafik fontu"; model:["DejaVu Sans","DejaVu Serif","DejaVu Sans Mono"]; Layout.fillWidth:true; onActivated:options.edited() }
        UiLabel { text:"Grafik font boyutu"; Layout.fillWidth:true }
        UiSpinBox { id:fontSize; objectName:"chartFontSize"; Accessible.name:"Grafik font boyutu"; from:8; to:20; value:11; editable:true; onValueModified:options.edited() }
        UiTextField { id:annotation; objectName:"chartAnnotation"; placeholderText:"Grafik açıklama notu"; Accessible.name:"Grafik açıklama notu"; maximumLength:200; Layout.fillWidth:true; onTextEdited:options.edited() }
        UiLabel { text:"PNG/export DPI (yüksek DPI daha fazla piksel üretir; RAM önkontrolü var)"; Layout.fillWidth:true; wrapMode:Text.Wrap }
        UiSpinBox { id:dpi; objectName:"chartDPI"; Accessible.name:"Grafik dışa aktarım DPI"; from:72; to:600; value:120; editable:true; onValueModified:options.edited() }
    }
}
