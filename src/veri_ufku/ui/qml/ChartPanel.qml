import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id: panel
    objectName: "chartPanel"
    property string helpContext: "chart.histogram"
    property var selected: []
    property var recommendationRows: []
    property var galleryRows: []
    property var kindValues: ["histogram","box","bar","line","scatter","correlation","missing","array-heatmap","array-profile","violin","kde","ecdf","rug","strip","swarm","qq","pp","error-bar","ci-band","missing-pattern","pair","hexbin","density-2d","bubble","grouped-heatmap","clustered-heatmap","parallel","facets","conditional","stacked-bar","percent-bar","stacked-area","percent-area","dot","lollipop","waterfall","pareto","treemap","sunburst","sankey","alluvial","funnel","calendar","pie","donut","radar","map-point","map-choropleth","map-density","map-raster"]
    signal helpRequested(var origin, string context)
    spacing: Theme.md
    function key(picker) { return picker.currentIndex>=0 ? picker.currentValue : "" }
    function restore() {
        let s=charts.chartResult.spec
        if (!s) return
        kind.currentIndex=kindValues.indexOf(s.kind)
        for(let i=0;i<charts.columns.length;i++) {
            if(charts.columns[i].id===s.x) x.currentIndex=i
            if(charts.columns[i].id===s.y) y.currentIndex=i
        }
        group.currentIndex=0
        for(let i=0;i<group.model.length;i++) if(group.model[i].id===s.group) group.currentIndex=i
        panel.selected=s.columns; title.text=s.title; xlabel.text=s.xlabel; ylabel.text=s.ylabel; xunit.text=s.xunit; yunit.text=s.yunit
        legend.checked=s.legend; bins.value=s.bins; topn.value=s.top_n
        aggregate.currentIndex=["count","sum","mean","median","min","max","reject"].indexOf(s.aggregation)
        correlation.currentIndex=s.correlation==="pearson" ? 0:1
        scatter.currentIndex=["systematic","grid","full"].indexOf(s.scatter_mode)
        limit.value=s.point_limit; grid.value=s.grid_bins; scope.currentIndex=["view","full","sample"].indexOf(s.scope)
        sample.value=s.sample_rows; approx.checked=s.precision==="approximate"
        purpose.currentIndex=["distribution","compare","relationship","time","quality"].indexOf(s.purpose)
        panel.helpContext="chart."+s.kind.replace("_","-")
        distribution.restore(s)
        multivariate.restore(s)
        composition.restore(s)
        geo.restore(s)
        settings.checked=false
    }
    function create() {
        let name=kindValues[kind.currentIndex]
        let multiple=["correlation","missing","array-heatmap","missing-pattern","pair","grouped-heatmap","clustered-heatmap","parallel","radar"].indexOf(name)>=0
        let needsY=["line","scatter","array-profile","error-bar","ci-band","hexbin","density-2d","bubble","facets","conditional"].indexOf(name)>=0 || kind.currentIndex>=29 && name!=="funnel" && name!=="radar" || name==="bar" && aggregate.currentIndex!==0
        let spec={kind:name,x:multiple ? "":key(x),y:needsY ? key(y):"",group:(!multiple || kind.currentIndex>=20) && name.indexOf("array-")!==0 && group.currentIndex>0 ? group.currentValue:"",columns:multiple ? selected:[],title:title.text,xlabel:xlabel.text,ylabel:ylabel.text,xunit:xunit.text,yunit:yunit.text,legend:legend.checked,bins:bins.value,top_n:topn.value,aggregation:["count","sum","mean","median","min","max","reject"][aggregate.currentIndex],correlation:correlation.currentIndex===0 ? "pearson":"spearman",scatter_mode:["systematic","grid","full"][scatter.currentIndex],point_limit:limit.value,grid_bins:grid.value,scope:["view","full","sample"][scope.currentIndex],sample_rows:sample.value,precision:approx.checked ? "approximate":"reject",purpose:["distribution","compare","relationship","time","quality"][purpose.currentIndex]}
        if (name === "error-bar" || name === "ci-band") spec.aggregation="mean"
        Object.assign(spec,distribution.values())
        if(kind.currentIndex>=20 && kind.currentIndex<29) Object.assign(spec,multivariate.values())
        if(kind.currentIndex>=29 && kind.currentIndex<46) { Object.assign(spec,composition.values()); spec.facet=""; spec.weight=""; spec.weight_type="none"; spec.size=""; spec.xscale="linear"; spec.yscale="linear"; spec.category_order=composition.order(); }
        if(kind.currentIndex>=46){Object.assign(spec,geo.values());spec.group="";spec.facet="";spec.weight="";spec.weight_type="none";spec.size="";spec.xscale="linear";spec.yscale="linear";if(spec.geometry){spec.x="";spec.y="";}}
        charts.create(JSON.stringify(spec))
        settings.checked=false
    }
    UiLabel { text: "İstatistik özeti ve grafik"; font.pixelSize: Theme.heading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiCheckBox { id:settings; objectName:"chartSettings"; text:"Grafik ayarlarını göster"; checked:true; Layout.fillWidth:true }
    ColumnLayout { visible:settings.checked; Layout.fillWidth:true; spacing:Theme.md
    UiCombo { accessibleLabel: "İstatistik özeti ve grafik"; model: dataView.datasets; textRole: "label"; valueRole: "id"; Layout.fillWidth: true; Layout.minimumWidth: 0; onActivated: { dataView.selectDataset(currentValue); panel.selected=[]; charts.invalidate() } }
    UiLabel { text: dataView.viewSummary; color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiLabel { text: "Filtreler Veri → Veri tablosunda hazırlanır. Grafik veri sürümünü değiştirmez. Alan/tür/rol önerisi otomatik analiz değildir; kimlikler önerilmez."; Layout.fillWidth: true; wrapMode: Text.Wrap }
    UiTextField { id:galleryQuery; Accessible.name:"Grafik sorusu veya tür araması"; objectName:"chartGalleryQuery"; placeholderText:"Soru veya tür ara: pay, nereden nereye, hangi gün…"; Layout.fillWidth:true; onTextChanged:panel.galleryRows=charts.gallery(text,composition.advanced) }
    UiButton { objectName:"chartGallerySearch"; text:"Soruya göre grafik galerisi"; Layout.fillWidth:true; onClicked:panel.galleryRows=charts.gallery(galleryQuery.text,composition.advanced) }
    Repeater { model:panel.galleryRows; UiButton { required property var modelData; text:modelData.kind+" · "+modelData.question+"\nInput: "+modelData.schema+"\n"+modelData.status; multiline:true; Layout.fillWidth:true; enabled:modelData.ready; onClicked:kind.currentIndex=panel.kindValues.indexOf(modelData.kind) } }
    UiCombo { accessibleLabel: "Grafik amacı"; id: purpose; objectName: "chartPurpose"; model: ["Dağılımı incele","Grupları karşılaştır","İlişki ara","Zamanı incele","Eksikleri incele"]; Layout.fillWidth: true; onActivated: { panel.recommendationRows=charts.recommendations(["distribution","compare","relationship","time","quality"][currentIndex]); charts.invalidate() } }
    UiButton { text: "Tür / rol / amaca göre öner"; enabled: !projects.busy; onClicked: panel.recommendationRows=charts.recommendations(["distribution","compare","relationship","time","quality"][purpose.currentIndex]); Layout.fillWidth: true; multiline: true }
    Repeater { model: panel.recommendationRows; UiButton { required property var modelData; text: modelData.reason+" → "+modelData.kind; Layout.fillWidth: true; multiline: true; onClicked: { kind.currentIndex=panel.kindValues.indexOf(modelData.kind); for(let i=0;i<charts.columns.length;i++) if(charts.columns[i].id===modelData.column_id) x.currentIndex=i; charts.invalidate() } } }
    UiLabel { text: "Grafik türü"; Layout.fillWidth: true }
    UiCombo { accessibleLabel: "Grafik türü"; id: kind; objectName: "chartKind"; model: ["Histogram — dağılım","Kutu — medyan ve yayılım","Sütun — kategori karşılaştırması","Çizgi — sıralı zaman/ölçüm","Dağılım — iki ölçüm","Korelasyon ısı haritası","Eksik oranı","Array 2D ısı haritası · iki eksen + ölçüm","Array profil çizgisi","Violin — yoğunluk","KDE — yoğunluk","ECDF — birikimli olasılık","Rug — tekil değerler","Strip — kategoride gözlemler","Swarm — limitli çakışma yerleşimi","QQ — normal referans","PP — normal referans","Hata çubuğu — SD / SE / CI","Noktasal CI bandı","Eksiklik desenleri","Pair / scatter matrix","Hexbin — CPU sayım","2D yoğunluk — hücre histogramı","Bubble — boyut kodlama","Gruplu heatmap","Kümelenmiş heatmap","Parallel coordinates — sayısal","Facet / small multiples","Koşullu ilişki / pooled","Stacked bar","100% stacked bar","Stacked area","100% stacked area","Dot — kategori karşılaştırması","Lollipop","Waterfall — başlangıç/değişim/bitiş","Pareto","Treemap — yaprak toplamı","Sunburst — hiyerarşi","Sankey — dengeli akış","Alluvial — aşamalı akış","Funnel — kişi/olay","Takvim heatmap","Pie — en fazla6 kategori","Donut — en fazla6 kategori","Radar — gelişmiş/normalize","Nokta haritası · offline","Choropleth · sayım/oran","Yoğunluk haritası · grid","GeoTIFF raster kesit"]; Layout.fillWidth: true; onCurrentIndexChanged: panel.helpContext="chart."+panel.kindValues[currentIndex].replace("_","-"); onActivated:charts.invalidate() }
    GridLayout {
        columns: panel.width>650*Theme.scale ? 2:1
        Layout.fillWidth: true
        UiLabel { text: "X / dağılım ölçümü"; Layout.fillWidth: true; visible: kind.currentIndex<5 || kind.currentIndex>=8 && kind.currentIndex!==19 }
        UiCombo { accessibleLabel: "X ölçümü"; id:x; objectName:"chartX"; model:charts.columns; textRole:"name"; valueRole:"id"; Layout.fillWidth:true; Layout.minimumWidth:0; visible:kind.currentIndex<5 || kind.currentIndex>=8 && kind.currentIndex!==19; onActivated:{ if(kind.currentIndex===1) yunit.text=model[currentIndex].unit; else xunit.text=model[currentIndex].unit; charts.invalidate() } }
        UiLabel { text:"Y ölçümü (sütunda count için gerekmez)"; Layout.fillWidth:true; visible:(kind.currentIndex>=2 && kind.currentIndex<=4) || kind.currentIndex===8 || kind.currentIndex===17 || kind.currentIndex===18 || kind.currentIndex>=21 && kind.currentIndex!==24 && kind.currentIndex!==25 && kind.currentIndex!==26 || kind.currentIndex>=29 && kind.currentIndex!==41 && kind.currentIndex!==45 }
        UiCombo { accessibleLabel: "Y ölçümü"; id:y; objectName:"chartY"; model:charts.columns; textRole:"name"; valueRole:"id"; Layout.fillWidth:true; Layout.minimumWidth:0; visible:(kind.currentIndex>=2 && kind.currentIndex<=4) || kind.currentIndex===8 || kind.currentIndex===17 || kind.currentIndex===18 || kind.currentIndex>=21 && kind.currentIndex!==24 && kind.currentIndex!==25 && kind.currentIndex!==26 || kind.currentIndex>=29 && kind.currentIndex!==41 && kind.currentIndex!==45; onActivated:{ yunit.text=model[currentIndex].unit; charts.invalidate() } }
        UiLabel { text:"İsteğe bağlı grup / legend"; Layout.fillWidth:true; visible:kind.currentIndex<=4 || kind.currentIndex>=9 && kind.currentIndex!==19 }
        UiCombo { accessibleLabel: "Grafik grubu"; id:group; objectName:"chartGroup"; model:[{id:"",name:"Grup yok"}].concat(charts.columns); textRole:"name"; valueRole:"id"; Layout.fillWidth:true; Layout.minimumWidth:0; visible:kind.currentIndex<=4 || kind.currentIndex>=9 && kind.currentIndex!==19; onActivated:charts.invalidate() }
    }
    UiLabel { text:kind.currentIndex===7 ? "Sırayla iki boyut koordinatı/indeksi, sonra value ölçümünü seçin." : "Korelasyon/eksik oranı sütunları (en fazla20)"; visible:kind.currentIndex>=5 && kind.currentIndex<=7 || kind.currentIndex===19 || [20,24,25,26,45].indexOf(kind.currentIndex)>=0; Layout.fillWidth:true; wrapMode:Text.Wrap }
    Repeater {
        model:kind.currentIndex>=5 && kind.currentIndex<=7 || kind.currentIndex===19 || [20,24,25,26,45].indexOf(kind.currentIndex)>=0 ? charts.columns:[]
        UiCheckBox { required property var modelData; text:modelData.name+" · "+modelData.type+" · "+(modelData.role||"rol onayı yok"); Layout.fillWidth:true; checked:panel.selected.indexOf(modelData.id)>=0; onClicked:{ panel.selected=checked ? panel.selected.concat([modelData.id]):panel.selected.filter(v=>v!==modelData.id); charts.invalidate() } }
    }
    GridLayout {
        columns:panel.width>650*Theme.scale ? 2:1; Layout.fillWidth:true
        UiLabel { text:"Agregasyon / tekrar tarih politikası"; visible:kind.currentIndex===2 || kind.currentIndex===3 || kind.currentIndex===7 || kind.currentIndex===8 || kind.currentIndex===24 || kind.currentIndex===25 || kind.currentIndex>=29; Layout.fillWidth:true }
        UiCombo { accessibleLabel: "Özetleme yöntemi"; id:aggregate; objectName:"chartAggregation"; model:["Kayıt sayısı (count)","Toplam (sum)","Ortalama (mean)","Medyan (median)","En küçük","En büyük","Tekrarda dur (reject)"]; currentIndex:6; visible:kind.currentIndex===2 || kind.currentIndex===3 || kind.currentIndex===7 || kind.currentIndex===8 || kind.currentIndex===24 || kind.currentIndex===25 || kind.currentIndex>=29; Layout.fillWidth:true; onActivated:charts.invalidate() }
        UiLabel { text:"Bin sayısı (histogram aralıkları)"; visible:kind.currentIndex===0; Layout.fillWidth:true }
        UiSpinBox { id:bins; objectName:"chartBins"; from:1; to:200; value:20; editable:true; visible:kind.currentIndex===0; onValueModified:charts.invalidate(); Accessible.name:"Histogram bin sayısı" }
        UiLabel { text:"Top-N kategori / azami legend grubu"; Layout.fillWidth:true; wrapMode:Text.Wrap }
        UiSpinBox { Accessible.name: "Top-N kategori / azami legend grubu"; id:topn; objectName:"chartTopN"; from:1; to:100; value:20; editable:true; onValueModified:charts.invalidate() }
        UiLabel { text:"Korelasyon yöntemi"; visible:kind.currentIndex===5; Layout.fillWidth:true }
        UiCombo { accessibleLabel: "Korelasyon yöntemi"; id:correlation; objectName:"chartCorrelation"; model:["Pearson — doğrusal ilişki","Spearman — sıra ilişkisi (eşit sıralar ortalama)"]; visible:kind.currentIndex===5; Layout.fillWidth:true; onActivated:charts.invalidate() }
        UiLabel { text:"Scatter çizim kapsamı"; visible:kind.currentIndex===4; Layout.fillWidth:true }
        UiCombo { accessibleLabel: "Nokta örnekleme yöntemi"; id:scatter; objectName:"chartScatter"; model:["Sistematik örnekleme (temsil garantisi yok)","Izgara ortalaması / tüm hücre üyeleri","Tam noktalar (sınır aşarsa dur)"]; visible:kind.currentIndex===4; Layout.fillWidth:true; onActivated:charts.invalidate() }
        UiLabel { text:"Azami nokta sayısı"; visible:kind.currentIndex===4; Layout.fillWidth:true }
        UiSpinBox { Accessible.name: "Azami nokta sayısı"; id:limit; objectName:"chartPointLimit"; from:1; to:10000; value:10000; editable:true; visible:kind.currentIndex===4; onValueModified:charts.invalidate() }
        UiLabel { text:"Izgara eksen başına hücre"; visible:kind.currentIndex===4 && scatter.currentIndex===1; Layout.fillWidth:true }
        UiSpinBox { Accessible.name: "Izgara eksen başına hücre"; id:grid; from:2; to:80; value:40; visible:kind.currentIndex===4 && scatter.currentIndex===1; onValueModified:charts.invalidate() }
        UiLabel { text:"Hesap kapsamı"; Layout.fillWidth:true }
        UiCombo { accessibleLabel: "Grafik kapsamı"; id:scope; objectName:"chartScopeChoice"; model:["Mevcut tablo filtreleri / tam alt küme","Tam dataset (filtreleri kullanma)","Filtreli ilk-N açık örneklem"]; Layout.fillWidth:true; onActivated:charts.invalidate() }
        UiLabel { text:"İlk-N kayıt (kaynak sırası)"; visible:scope.currentIndex===2; Layout.fillWidth:true }
        UiSpinBox { Accessible.name: "İlk-N kayıt (kaynak sırası)"; id:sample; objectName:"chartSample"; from:1; to:100000; value:10000; editable:true; visible:scope.currentIndex===2; onValueModified:charts.invalidate() }
    }
    UiCheckBox { id:approx; objectName:"chartApproximate"; text:"Integer/Decimal Float64 çizim kaybına açık izin ver (kesin özet korunur)"; Layout.fillWidth:true; onClicked:charts.invalidate() }
    UiLabel { text:"Null/NaN/±sonsuz ölçümler dışlanır ve ayrı sayılır. Kategoride null ayrı grup; eksik oranında yalnız null sayılır. Çizgi artan X sıralıdır; tekrarlar seçili agregasyonla birleşir. Kutu aykırı işaretleri otomatik silmez."; Layout.fillWidth:true; wrapMode:Text.Wrap; color:Theme.warning }
    UiCheckBox { id:styleDetails; text:"Başlık, eksen adı, birim ve legend"; Layout.fillWidth:true }
    ColumnLayout {
        visible:styleDetails.checked; Layout.fillWidth:true
        UiTextField { id:title; objectName:"chartTitle"; placeholderText:"Grafik başlığı"; maximumLength:200; Layout.fillWidth:true; onTextEdited:charts.invalidate(); Accessible.name:"Grafik başlığı" }
        UiTextField { id:xlabel; placeholderText:"X ekseni adı"; maximumLength:200; Layout.fillWidth:true; onTextEdited:charts.invalidate(); Accessible.name:"X ekseni adı" }
        UiTextField { id:ylabel; placeholderText:"Y ekseni adı"; maximumLength:200; Layout.fillWidth:true; onTextEdited:charts.invalidate(); Accessible.name:"Y ekseni adı" }
        UiTextField { id:xunit; placeholderText:"X birimi"; maximumLength:200; Layout.fillWidth:true; onTextEdited:charts.invalidate(); Accessible.name:"X birimi" }
        UiTextField { id:yunit; placeholderText:"Y birimi"; maximumLength:200; Layout.fillWidth:true; onTextEdited:charts.invalidate(); Accessible.name:"Y birimi" }
        UiCheckBox { id:legend; checked:true; text:"Legend göster"; onClicked:charts.invalidate() }
    }
    }
    GeoChartOptions {id:geo;visible:kind.currentIndex>=46;columns:charts.columns;chartKind:panel.kindValues[kind.currentIndex];onEdited:charts.invalidate();Layout.fillWidth:true}
    CompositionOptions { id:composition; visible:kind.currentIndex>=29 && kind.currentIndex<46; columns:charts.columns; chartKind:panel.kindValues[kind.currentIndex]; onEdited:charts.invalidate() }
    MultivariateOptions { id:multivariate; visible:kind.currentIndex>=20 && kind.currentIndex<29; columns:charts.columns; selectedCount:panel.selected.length; chartKind:panel.kindValues[kind.currentIndex]; onEdited:charts.invalidate() }
    DistributionOptions { id:distribution; visible:kind.currentIndex<29; columns:charts.columns; chartKind:panel.kindValues[kind.currentIndex]; onEdited:charts.invalidate() }
    Flow {
        Layout.fillWidth:true; spacing:Theme.sm
        UiButton { objectName:"chartCreate"; tone:"cyan"; text:"Grafiği oluştur"; primary:true; enabled:!projects.busy && dataView.datasets.length>0; onClicked:panel.create() }
        UiButton { text:qsTr("İptal"); enabled:charts.busy; onClicked:charts.cancel() }
        UiButton { tone: "mint"; text:qsTr("Bu ne işe yarar?"); helpContext:panel.helpContext; onClicked:panel.helpRequested(this,"chart."+panel.kindValues[kind.currentIndex]) }
    }
    StateNotice { Layout.fillWidth:true; kind:charts.errorText ? "error":charts.busy ? "loading":"info"; heading:"Grafik sonucu"; detail:charts.errorText||charts.message }
    UiLabel { objectName:"chartScope"; visible:!!charts.chartResult.dataset_version; text:(charts.current ? "Seçili veri/filtre ile uyumlu":"Eski veri sürümü/filtre — yeniden oluşturun")+"\nSürüm: "+(charts.chartResult.dataset_version||"")+" · "+(charts.chartResult.scope||"")+" · kullanılan "+charts.chartResult.used_n+" / kapsam "+charts.chartResult.population_n+" / dataset "+charts.chartResult.dataset_n+"\nFiltreler: "+JSON.stringify(charts.chartResult.filters||[]); Layout.fillWidth:true; wrapMode:Text.Wrap }
    UiLabel { objectName:"chartMethodDetails"; text:charts.methodSummary; visible:!!charts.chartResult.dataset_version; Layout.fillWidth:true; wrapMode:Text.Wrap }
    Repeater { model:charts.chartResult.warnings||[]; UiLabel { required property string modelData; text:modelData; Layout.fillWidth:true; wrapMode:Text.Wrap; color:Theme.warning } }
    UiCombo { accessibleLabel: "Grafikle etkileşim modu"; id:mode; objectName:"chartMode"; model:["Sürükle / tıkla: RowId seçimi","Sürükle: yakınlaştır"]; Layout.fillWidth:true }
    Item {
        id:canvas; objectName:"chartCanvas"; Layout.fillWidth:true; Layout.preferredHeight:Math.max(260, Math.min(720 * Theme.scale, width * (charts.plotMetadata.height || 600) / (charts.plotMetadata.width || 960))); visible:charts.imageUrl.length>0
        Image { id:plot; objectName:"chartImage"; anchors.fill:parent; source:charts.imageUrl; cache:false; fillMode:Image.PreserveAspectFit }
        Canvas {
            id: selectionOverlay
            anchors.fill:parent
            onPaint: {
                let ctx=getContext("2d");ctx.clearRect(0,0,width,height)
                let selected=charts.selectionResult.point_ids||[]
                let meta=charts.plotMetadata
                if (!meta.pixels) return
                let marks=new Set(selected)
                ctx.strokeStyle="#991B1B";ctx.lineWidth=2
                for (let p of meta.pixels) if(marks.has(p.point_id)) {
                    let px=(width-plot.paintedWidth)/2+p.x/meta.width*plot.paintedWidth
                    let py=(height-plot.paintedHeight)/2+p.y/meta.height*plot.paintedHeight
                    ctx.beginPath();ctx.arc(px,py,7,0,Math.PI*2);ctx.stroke()
                }
            }
            Connections { target:charts; function onChanged() { selectionOverlay.requestPaint() } }
            onWidthChanged:requestPaint()
            onHeightChanged:requestPaint()
        }
        MouseArea {
            id:mouse; objectName:"chartMouse"; anchors.fill:parent; property real sx:0; property real sy:0
            property bool validOrigin: false
            function insideImage(x, y) {
                return plot.status === Image.Ready && plot.paintedWidth > 0 && plot.paintedHeight > 0
                    && x >= (width - plot.paintedWidth) / 2 && x <= (width + plot.paintedWidth) / 2
                    && y >= (height - plot.paintedHeight) / 2 && y <= (height + plot.paintedHeight) / 2
            }
            function nx(x) { return Math.max(0,Math.min(1,(x-(width-plot.paintedWidth)/2)/plot.paintedWidth)) }
            function ny(y) { return Math.max(0,Math.min(1,(y-(height-plot.paintedHeight)/2)/plot.paintedHeight)) }
            onPressed:function(event) { validOrigin=insideImage(event.x,event.y); if(!validOrigin){event.accepted=false;return} sx=nx(event.x);sy=ny(event.y) }
            onCanceled: validOrigin=false
            onReleased:function(event) { if(!validOrigin)return; validOrigin=false; if(mode.currentIndex===0) charts.selectRectangle(sx,sy,nx(event.x),ny(event.y));else charts.zoomRectangle(sx,sy,nx(event.x),ny(event.y)) }
        }
        Accessible.name:"Matplotlib grafik; seçim/yakınlaştırma modu ve metinli sonuç tablosu"
    }
    Flow {
        Layout.fillWidth:true; spacing:Theme.sm
        UiButton { objectName:"chartZoom"; text:"Yakınlaştır"; enabled:charts.current && !projects.busy; onClicked:charts.zoomRectangle(.25,.25,.75,.75) }
        UiButton { objectName:"chartReset"; text:"Görünümü sıfırla"; enabled:charts.current && !projects.busy; onClicked:charts.reset() }
        UiButton { objectName:"chartSave"; text:"Grafiği projeye kaydet"; enabled:charts.current && !projects.busy && !projects.readOnly; onClicked:charts.save() }
        UiButton { objectName:"chartExportPNG"; text:"PNG dışa aktar"; enabled:charts.current && !projects.busy; onClicked:{ exportDialog.nameFilters=["PNG (*.png)"]; exportDialog.defaultSuffix="png"; exportDialog.open() } }
        UiButton { objectName:"chartExportSVG"; text:"SVG dışa aktar"; enabled:charts.current && !projects.busy; onClicked:{ exportDialog.nameFilters=["SVG (*.svg)"]; exportDialog.defaultSuffix="svg"; exportDialog.open() } }
    }
    UiButton { objectName:"chartExportPDF"; text:"PDF dışa aktar"; Layout.fillWidth:true; enabled:charts.current && !projects.busy; onClicked:{ exportDialog.nameFilters=["PDF (*.pdf)"]; exportDialog.defaultSuffix="pdf"; exportDialog.open() } }
    FileDialog { id:exportDialog; title:"Yeni çıktı dosyası seçin (mevcut dosya korunur)"; fileMode:FileDialog.SaveFile; onAccepted:charts.export(selectedFile.toString(),defaultSuffix) }
    UiButton { objectName:"chartSelectionDataset"; text:"Seçili satırlardan yeni dataset önizle (Dönüştür ekranında onayla)"; enabled:charts.current && !projects.busy && !projects.readOnly && (charts.selectionResult.count||0)>0; onClicked:operations.previewChartSelection(JSON.stringify(charts.selectionResult)) }
    UiButton { objectName:"chartSelectionExportContext"; text:"Seçimi statik çıktıya işle (yalnız görünüm)"; enabled:charts.current && !charts.busy; onClicked:charts.freezeSelection() }
    UiLabel { text:"Brushing yalnız tablo vurgusudur; dataset değişmez. Filtreli yeni dataset: Veri → filtreyi hazırla → Dönüştür → Filtre. 3D bu fazda etkin değil; perspektif/örtüşme nedeniyle pair/facet 2D seçin."; Layout.fillWidth:true; wrapMode:Text.Wrap }
    UiLabel { objectName:"chartSelection"; text:qsTr("Seçim: ")+(charts.selectionResult.count||0)+" RowId · "+(charts.selectionResult.scope||"seçim yok")+"\n"+(charts.selectionResult.row_ids||[]).slice(0,5).join(", "); Layout.fillWidth:true; wrapMode:Text.Wrap }
    UiCheckBox { id:details; text:"Grafik verisi ve ham (ağırlıksız) sütun özeti"; Layout.fillWidth:true }
    ColumnLayout {
        visible:details.checked; Layout.fillWidth:true
        UiLabel { text:JSON.stringify(charts.chartResult.details||{}); Layout.fillWidth:true; wrapMode:Text.Wrap }
        Repeater { model:charts.chartResult.summary||[]; UiLabel { required property var modelData; text:modelData.column_name+" · "+JSON.stringify(modelData.numeric)+"\nNull/NaN/inf: "+JSON.stringify(modelData.counts); Layout.fillWidth:true; wrapMode:Text.Wrap } }
        UiLabel { text:"Grafik veri satırları ilk400 nokta (korelasyonda tüm çiftler); tam veri ve üyelik proje artifact içinde saklanır."; Layout.fillWidth:true; wrapMode:Text.Wrap }
        Repeater { model:details.checked ? charts.referenceRows:[]; UiLabel { required property var modelData; text:modelData; Layout.fillWidth:true; wrapMode:Text.Wrap } }
    }
    UiCombo { accessibleLabel: "Kayıtlı grafik"; id:saved; objectName:"chartSaved"; model:charts.savedCharts; textRole:"label"; valueRole:"id"; Layout.fillWidth:true; Layout.minimumWidth:0 }
    UiButton { text:"Kayıtlı grafiği aç"; enabled:saved.currentIndex>=0 && !projects.busy; onClicked:{ charts.openSaved(saved.currentValue); panel.restore() } Layout.fillWidth:true }
}
