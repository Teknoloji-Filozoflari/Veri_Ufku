import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id: panel
    objectName: "dashboardPanel"
    property string helpContext: "dashboard.canvas"
    signal helpRequested(var origin, string context)
    spacing: Theme.md
    function value(picker) { return picker.currentIndex >= 0 ? picker.currentValue || "" : "" }
    function selectedWidget() { return inspector.currentIndex >= 0 ? dashboard.viewSpec.widgets[inspector.currentIndex] : null }
    function updateInspector() {
        let w = selectedWidget(); if (!w) return
        widgetTitle.text = w.title; widgetNote.text = w.text
        gridRow.value=w.grid[0]; gridCol.value=w.grid[1]; gridHeight.value=w.grid[2]; gridWidth.value=w.grid[3]
        aggregate.currentIndex=["count","sum","mean","min","max"].indexOf(w.aggregation)
        denominatorMode.currentIndex=["none","rows","non-null","column-sum"].indexOf(w.denominator_mode)
        denominatorText.text=w.denominator; periodText.text=w.previous_period
        denominatorColumn.currentIndex=denominatorColumn.indexOfValue(w.denominator_column)
        let prior=w.previous_filters.length?w.previous_filters[0]:null
        periodColumn.currentIndex=prior?periodColumn.indexOfValue(prior.column_id):0
        periodValue.text=prior?String(prior.value):""
    }
    function updateFigure() {
        let f=dashboard.viewSpec.figure||{}
        figureRows.value=f.rows||1; figureCols.value=f.columns||2
        figureWidth.value=f.width||12;figureHeight.value=f.height||8
        palette.currentIndex=["accessible","colorblind","grayscale"].indexOf(f.palette||"accessible")
        fontPreset.currentIndex=["DejaVu Sans","DejaVu Serif","DejaVu Sans Mono"].indexOf(f.font||"DejaVu Sans")
        fontSize.value=f.font_size||11;sharedLegend.checked=f.shared_legend!==false
        caption.text=f.caption||"";unit.text=f.unit||"";source.text=f.source||""
    }
    UiCheckBox { id: expanded; objectName: "dashboardExpanded"; text: "Dashboard canvas ve Figure Composer"; Layout.fillWidth: true }
    ColumnLayout {
        visible: expanded.checked
        Layout.fillWidth: true
        spacing: Theme.md
        UiLabel { text: "Önce soruyu belirleyin. Widget'lar kayıtlı veri sürümünü kullanır; filtre ve seçim kapsamı her kartta gösterilir."; Layout.fillWidth:true; wrapMode:Text.Wrap }
        Flow { Layout.fillWidth:true; spacing:Theme.sm
            UiButton { objectName:"dashboardNew"; text:"Yeni görünüm"; enabled:!dashboard.busy && !projects.busy; onClicked:{dashboard.newView();panel.updateFigure()} }
            UiButton { objectName:"dashboardHelp"; helpContext:"dashboard.canvas"; text:"Bu ne işe yarar?"; onClicked:panel.helpRequested(this,helpContext) }
        }
        UiTextField { Accessible.name:placeholderText; id: viewName; objectName:"dashboardName"; placeholderText:"Dashboard sorusu / görünüm adı"; text:dashboard.viewSpec.name; Layout.fillWidth:true; onEditingFinished:dashboard.rename(text) }
        RowLayout { Layout.fillWidth:true
            UiCombo { id:saved; objectName:"dashboardSavedViews"; accessibleLabel:"Kaydedilmiş dashboard görünümü"; model:dashboard.savedViews; textRole:"name"; valueRole:"id"; Layout.fillWidth:true }
            UiButton { objectName:"dashboardOpen"; text:"Görünümü aç"; enabled:saved.currentIndex>=0 && !dashboard.busy && !projects.busy; onClicked:{dashboard.openSaved(panel.value(saved));Qt.callLater(panel.updateFigure);Qt.callLater(panel.updateInspector)} }
            UiButton { objectName:"dashboardSave"; text:"Görünümü kaydet"; enabled:projects.opened && !projects.readOnly && !dashboard.busy && !projects.busy; onClicked:dashboard.save() }
        }
        GridLayout { columns:panel.width>750*Theme.scale?2:1; Layout.fillWidth:true
            UiCombo { id:dataset; objectName:"dashboardDataset"; accessibleLabel:"Widget veri sürümü"; model:dashboard.datasets; textRole:"name"; valueRole:"id"; Layout.fillWidth:true }
            UiCombo { id:column; objectName:"dashboardColumn"; accessibleLabel:"KPI ölçümü / tablo sütunu"; model:dataset.currentIndex>=0?dashboard.datasets[dataset.currentIndex].columns:[]; textRole:"name"; valueRole:"id"; Layout.fillWidth:true }
            UiCombo { id:kind; objectName:"dashboardWidgetKind"; accessibleLabel:"Widget türü"; model:["Grafik","Tablo","KPI","Not"]; Layout.fillWidth:true }
            UiCombo { id:chart; objectName:"dashboardChart"; accessibleLabel:"Kayıtlı grafik sonucu"; model:dashboard.savedCharts; textRole:"name"; valueRole:"id"; Layout.fillWidth:true; visible:kind.currentIndex===0 }
        }
        UiTextField { Accessible.name:placeholderText; id:note; objectName:"dashboardNewNote"; placeholderText:"Yeni not metni"; Layout.fillWidth:true; visible:kind.currentIndex===3 }
        UiButton { objectName:"dashboardAddWidget"; text:"Widget ekle"; enabled:dataset.currentIndex>=0 && !dashboard.busy && !projects.busy; onClicked:{ let version=kind.currentIndex===0 && chart.currentIndex>=0?dashboard.savedCharts[chart.currentIndex].version:panel.value(dataset); dashboard.addWidget(["chart","table","kpi","note"][kind.currentIndex],version,panel.value(column),panel.value(chart),note.text) } }
        UiLabel { text:"Filtre kapsamı ve kaynaklar arası eşleme"; font.bold:true; Layout.fillWidth:true }
        UiCombo { id:inspector; objectName:"dashboardInspector"; accessibleLabel:"Düzenlenecek / yerel filtre uygulanacak widget"; model:dashboard.viewSpec.widgets; textRole:"title"; valueRole:"id"; Layout.fillWidth:true; onActivated:panel.updateInspector() }
        GridLayout { columns:panel.width>750*Theme.scale?3:1; Layout.fillWidth:true
            UiCombo { id:filterScope; objectName:"dashboardFilterScope"; property string helpContext:"dashboard.filters"; accessibleLabel:"Filtre kapsamı"; model:["Global: eşlenmiş widget'lar","Yerel: seçili widget"]; Layout.fillWidth:true }
            UiCombo { id:filterColumn; objectName:"dashboardFilterColumn"; accessibleLabel:"Filtre kaynak sütunu"; model:column.model; textRole:"name"; valueRole:"id"; Layout.fillWidth:true }
            UiCombo { id:filterOp; objectName:"dashboardFilterOperator"; accessibleLabel:"Filtre işlemi"; model:["Eşit","En az","En çok","İçerir","Eksik"]; Layout.fillWidth:true }
        }
        UiTextField { Accessible.name:placeholderText; id:filterValue; objectName:"dashboardFilterValue"; placeholderText:"Filtre değeri"; Layout.fillWidth:true }
        Flow { Layout.fillWidth:true; spacing:Theme.sm
            UiButton { objectName:"dashboardAddFilter"; text:"Filtre ekle"; enabled:!dashboard.busy && !projects.busy; onClicked:dashboard.addFilter(filterScope.currentIndex===1?panel.value(inspector):"",panel.value(dataset),panel.value(filterColumn),["eq","gte","lte","contains","is-null"][filterOp.currentIndex],filterValue.text) }
            UiButton { text:"Filtreleri temizle"; enabled:!dashboard.busy && !projects.busy; onClicked:dashboard.clearFilters() }
            UiButton { text:"Filtre kapsamını öğren"; helpContext:"dashboard.filters"; onClicked:panel.helpRequested(this,helpContext) }
        }
        UiLabel { text:"Eşleme kaynakları otomatik seçilmez: üstteki veri sürümü ve filtre sütunu → aşağıdaki hedef. Eşlenmeyen global filtreler kartta açıklanır. Seçim aktarımı yalnız açık anahtar eşlemesiyle yapılır."; Layout.fillWidth:true; wrapMode:Text.Wrap }
        RowLayout { Layout.fillWidth:true
            UiCombo { id:targetDataset; objectName:"dashboardMappingDataset"; accessibleLabel:"Eşleme hedef veri sürümü"; model:dashboard.datasets; textRole:"name"; valueRole:"id"; Layout.fillWidth:true }
            UiCombo { id:targetColumn; objectName:"dashboardMappingColumn"; accessibleLabel:"Eşleme hedef sütunu"; model:targetDataset.currentIndex>=0?dashboard.datasets[targetDataset.currentIndex].columns:[]; textRole:"name"; valueRole:"id"; Layout.fillWidth:true }
        }
        Flow { Layout.fillWidth:true; spacing:Theme.sm
            UiButton { objectName:"dashboardMap"; text:"Bu sütunları eşle"; enabled:!dashboard.busy && !projects.busy; onClicked:dashboard.mapColumns(panel.value(dataset),panel.value(filterColumn),panel.value(targetDataset),panel.value(targetColumn)) }
            UiButton { text:"Eşlemeleri temizle"; enabled:!dashboard.busy && !projects.busy; onClicked:dashboard.clearMappings() }
        }
        UiLabel { text:"Global filtre sayısı: "+dashboard.viewSpec.global_filters.length+" · Açık kaynak eşlemesi: "+Object.keys(dashboard.viewSpec.filter_mappings).length; Layout.fillWidth:true; wrapMode:Text.Wrap }
        UiCheckBox { id:editing; objectName:"dashboardWidgetSettings"; text:"Seçili widget: başlık, grid ve KPI tanımı"; enabled:inspector.currentIndex>=0; onClicked:panel.updateInspector(); Layout.fillWidth:true }
        ColumnLayout { visible:editing.checked && inspector.currentIndex>=0; Layout.fillWidth:true
            UiTextField { Accessible.name:placeholderText; id:widgetTitle; objectName:"dashboardWidgetTitle"; placeholderText:"Widget başlığı"; Layout.fillWidth:true }
            UiTextField { Accessible.name:placeholderText; id:widgetNote; objectName:"dashboardWidgetNote"; placeholderText:"Widget not metni"; Layout.fillWidth:true }
            Flow { Layout.fillWidth:true; spacing:Theme.sm
                UiSpinBox { id:gridRow; objectName:"dashboardGridRow"; from:0; to:44; Accessible.name:"Grid satırı"; editable:true }
                UiSpinBox { id:gridCol; objectName:"dashboardGridColumn"; from:0; to:11; Accessible.name:"Grid sütunu"; editable:true }
                UiSpinBox { id:gridHeight; objectName:"dashboardGridHeight"; from:1; to:12; value:4; Accessible.name:"Grid satır genişliği"; editable:true }
                UiSpinBox { id:gridWidth; objectName:"dashboardGridWidth"; from:1; to:12; value:6; Accessible.name:"Grid sütun genişliği"; editable:true }
            }
            UiLabel { text:"KPI: agregasyon / payda / önceki dönem (none = karşılaştırma kapalı)"; Layout.fillWidth:true; wrapMode:Text.Wrap }
            UiCombo { id:aggregate; objectName:"dashboardKpiAggregation"; accessibleLabel:"KPI agregasyonu"; model:["count","sum","mean","min","max"]; Layout.fillWidth:true }
            UiCombo { id:denominatorMode; objectName:"dashboardKpiDenominatorMode"; accessibleLabel:"KPI payda işlemi"; model:["none","rows","non-null","column-sum"]; Layout.fillWidth:true }
            UiCombo { id:denominatorColumn; objectName:"dashboardKpiDenominatorColumn"; accessibleLabel:"KPI payda sütunu"; model:column.model; textRole:"name"; valueRole:"id"; Layout.fillWidth:true }
            UiTextField { Accessible.name:placeholderText; id:denominatorText; objectName:"dashboardKpiDenominator"; placeholderText:"KPI payda tanımı"; text:"included rows"; Layout.fillWidth:true }
            UiTextField { Accessible.name:placeholderText; id:periodText; objectName:"dashboardKpiPeriod"; placeholderText:"Önceki dönem tanımı"; text:"none"; Layout.fillWidth:true }
            UiCombo { id:periodColumn; objectName:"dashboardKpiPeriodColumn"; accessibleLabel:"Önceki dönem filtre sütunu"; model:column.model; textRole:"name"; valueRole:"id"; Layout.fillWidth:true }
            UiTextField { Accessible.name:placeholderText; id:periodValue; objectName:"dashboardKpiPeriodValue"; placeholderText:"Önceki dönem eşit filtre değeri"; Layout.fillWidth:true }
            UiButton { objectName:"dashboardApplyWidget"; text:"Widget ayarlarını uygula"; enabled:!dashboard.busy && !projects.busy; onClicked:dashboard.updateWidget(panel.value(inspector),JSON.stringify({title:widgetTitle.text,text:widgetNote.text,grid:[gridRow.value,gridCol.value,gridHeight.value,gridWidth.value],aggregation:aggregate.currentText,denominator_mode:denominatorMode.currentText,denominator:denominatorText.text,denominator_column:denominatorMode.currentIndex===3?panel.value(denominatorColumn):"",previous_period:periodText.text,previous_filters:periodText.text==="none"?[]:[{column_id:panel.value(periodColumn),operator:"eq",value:periodValue.text,scope:"local",dataset_version:panel.selectedWidget().dataset_version}]})) }
            UiButton { text:"KPI tanımını öğren"; helpContext:"dashboard.kpi"; onClicked:panel.helpRequested(this,helpContext) }
        }
        Flow { Layout.fillWidth:true; spacing:Theme.sm
            UiButton { objectName:"dashboardEvaluate"; text:"Dashboard hesapla"; enabled:projects.opened && !dashboard.busy && !projects.busy; onClicked:dashboard.evaluate() }
            UiButton { objectName:"dashboardCancel"; text:"İptal"; visible:dashboard.busy; onClicked:dashboard.cancel() }
            UiButton { objectName:"dashboardClearSelection"; text:"Seçimi temizle"; enabled:!dashboard.busy && !projects.busy; onClicked:dashboard.clearSelection() }
            UiButton { objectName:"dashboardDrillDown"; text:"Seçime in (drill-down)"; enabled:!dashboard.busy && !projects.busy && !!dashboard.viewSpec.selection.dataset_version; onClicked:dashboard.drillDown(!dashboard.viewSpec.drill_down) }
        }
        UiLabel { text:dashboard.message; Layout.fillWidth:true; wrapMode:Text.Wrap }
        UiLabel { text:dashboard.errorText; color:Theme.error; visible:text.length>0; Layout.fillWidth:true; wrapMode:Text.Wrap }
        Item {
            id:canvas
            objectName:"dashboardCanvas"
            Layout.fillWidth:true
            Layout.preferredHeight:Math.max(200,...dashboard.viewSpec.widgets.map(w=>(w.grid[0]+w.grid[2])*105))
            Repeater { model:dashboard.widgets
                Rectangle {
                    id:card
                    required property var modelData
                    x:modelData.grid[1]*canvas.width/12
                    y:modelData.grid[0]*105
                    width:modelData.grid[3]*canvas.width/12-6
                    height:modelData.grid[2]*105-6
                    color:Theme.surface; border.color:modelData.freshness==="stale"?Theme.error:Theme.border; radius:Theme.radius; clip:true
                    ColumnLayout { anchors.fill:parent; anchors.margins:Theme.sm; spacing:Theme.xs
                        UiLabel { id:cardTitle; text:card.modelData.title+" · "+card.modelData.kind; font.bold:true; Layout.fillWidth:true; wrapMode:Text.Wrap }
                        UiLabel { text:card.modelData.status_text+" · "+card.modelData.dataset_version; font.pixelSize:Theme.small; Layout.fillWidth:true; wrapMode:Text.Wrap }
                        UiLabel { text:"n="+(card.modelData.n||0)+" · seçim="+(card.modelData.linked_count||0)+" · global="+(card.modelData.filter_contract?card.modelData.filter_contract.global.length:0)+" · local="+card.modelData.filters.length; Layout.fillWidth:true; wrapMode:Text.Wrap }
                        UiLabel { visible:!!card.modelData.mapping_notice; text:card.modelData.mapping_notice||""; color:Theme.error; Layout.fillWidth:true; wrapMode:Text.Wrap }
                        UiLabel { visible:card.modelData.kind==="note"; text:card.modelData.text; Layout.fillWidth:true; wrapMode:Text.Wrap }
                        UiLabel { visible:!!card.modelData.kpi; text:card.modelData.kpi?(card.modelData.kpi.value||"Tanımsız")+"\n"+card.modelData.kpi.definition+"\nPay="+card.modelData.kpi.numerator+" / payda="+(card.modelData.kpi.denominator_value??"ham agregasyon")+" · önceki="+(card.modelData.kpi.previous?card.modelData.kpi.previous.value:"none")+" · fark="+(card.modelData.kpi.difference||"—")+"\n"+card.modelData.kpi.warning:""; Layout.fillWidth:true; wrapMode:Text.Wrap }
                        UiLabel { visible:!!card.modelData.empty; text:card.modelData.empty||""; Layout.fillWidth:true; wrapMode:Text.Wrap }
                        Image { id:plot; visible:!!card.modelData.image_url; source:card.modelData.image_url||""; cache:false; fillMode:Image.PreserveAspectFit; Layout.fillWidth:true; Layout.fillHeight:true
                            MouseArea { anchors.centerIn:parent; width:plot.paintedWidth; height:plot.paintedHeight; enabled:!dashboard.busy && !projects.busy; property real sx:0; property real sy:0; onPressed:function(mouse){sx=mouse.x/width;sy=mouse.y/height} onReleased:function(mouse){dashboard.brush(card.modelData.id,sx,sy,mouse.x/width,mouse.y/height)} }
                        }
                        ScrollView { visible:card.modelData.kind==="table"; Layout.fillWidth:true; Layout.fillHeight:true; clip:true
                            ColumnLayout { width:parent.width
                                UiLabel { text:card.modelData.columns?card.modelData.columns.map(c=>c.name).join(" | "):""; Layout.fillWidth:true; wrapMode:Text.Wrap }
                                Repeater { model:card.modelData.rows||[]
                                    UiButton { required property var modelData; text:modelData.cells.join(" | "); checkable:true; checked:modelData.selected; Layout.fillWidth:true; enabled:!dashboard.busy && !projects.busy; onClicked:dashboard.selectRows(card.modelData.id,JSON.stringify([modelData.row_id])) }
                                }
                            }
                        }
                        UiLabel { visible:card.modelData.kind==="table"; text:card.modelData.page_notice||""; Layout.fillWidth:true; wrapMode:Text.Wrap }
                        UiButton { text:"Widget kaldır"; enabled:!dashboard.busy && !projects.busy; onClicked:dashboard.removeWidget(card.modelData.id) }
                    }
                    MouseArea { anchors.top:parent.top; anchors.left:parent.left; anchors.right:parent.right; height:24; drag.target:card; enabled:!dashboard.busy && !projects.busy; cursorShape:Qt.SizeAllCursor
                        onReleased:{let col=Math.max(0,Math.min(12-card.modelData.grid[3],Math.round(card.x/canvas.width*12)));let row=Math.max(0,Math.min(48-card.modelData.grid[2],Math.round(card.y/105)));dashboard.updateWidget(card.modelData.id,JSON.stringify({grid:[row,col,card.modelData.grid[2],card.modelData.grid[3]]}))}
                    }
                }
            }
        }
        UiCheckBox { id:figureExpanded; objectName:"figureExpanded"; text:"Figure Composer ayarları"; Layout.fillWidth:true }
        ColumnLayout { visible:figureExpanded.checked; Layout.fillWidth:true
            UiLabel { text:"Grafik widget'ları subplot panellerine yerleşir; kaynak grafikteki facet korunur. Ortak legend aynı grup renklerini birleştirir. SVG/PDF gerçek vektör çizimi; statik çıktı etkileşimi korumaz. HTML yerel ağsız SVG adapter ile sabit snapshot seçimlerini bağlar."; Layout.fillWidth:true; wrapMode:Text.Wrap }
            GridLayout { columns:2; Layout.fillWidth:true
                UiSpinBox { id:figureRows; objectName:"figureRows"; from:1; to:4; value:1; Accessible.name:"Figure subplot satırları" }
                UiSpinBox { id:figureCols; objectName:"figureColumns"; from:1; to:4; value:2; Accessible.name:"Figure subplot sütunları" }
                UiSpinBox { id:figureWidth; objectName:"figureWidth"; from:2; to:40; value:12; Accessible.name:"Figure genişlik inç" }
                UiSpinBox { id:figureHeight; objectName:"figureHeight"; from:2; to:40; value:8; Accessible.name:"Figure yükseklik inç" }
                UiCombo { id:palette; objectName:"figurePalette"; accessibleLabel:"Figure renk preset"; model:["accessible","colorblind","grayscale"]; Layout.fillWidth:true }
                UiCombo { id:fontPreset; objectName:"figureFont"; accessibleLabel:"Figure typography preset"; model:["DejaVu Sans","DejaVu Serif","DejaVu Sans Mono"]; Layout.fillWidth:true }
                UiSpinBox { id:fontSize; objectName:"figureFontSize"; from:8; to:20; value:11; Accessible.name:"Figure font boyutu" }
                UiCheckBox { id:sharedLegend; objectName:"figureSharedLegend"; text:"Ortak legend"; checked:true; Layout.fillWidth:true }
            }
            UiTextField { Accessible.name:placeholderText; id:caption; objectName:"figureCaption"; placeholderText:"Figure caption"; Layout.fillWidth:true }
            UiTextField { Accessible.name:placeholderText; id:unit; objectName:"figureUnit"; placeholderText:"Figure unit / birim"; Layout.fillWidth:true }
            UiTextField { Accessible.name:placeholderText; id:source; objectName:"figureSource"; placeholderText:"Figure kaynak bilgisi"; Layout.fillWidth:true }
            UiButton { objectName:"figureApply"; text:"Figure ayarlarını uygula"; enabled:!dashboard.busy && !projects.busy; onClicked:dashboard.setFigure(JSON.stringify({rows:figureRows.value,columns:figureCols.value,width:figureWidth.value,height:figureHeight.value,shared_legend:sharedLegend.checked,palette:palette.currentText,font:fontPreset.currentText,font_size:fontSize.value,caption:caption.text,unit:unit.text,source:source.text})) }
            UiCombo { id:format; objectName:"figureFormat"; accessibleLabel:"Figure export biçimi"; model:["svg","png","pdf","html"]; Layout.fillWidth:true }
            UiTextField { Accessible.name:placeholderText; id:destination; objectName:"figureDestination"; placeholderText:"Yeni figure çıktı dosyası"; Layout.fillWidth:true }
            Flow { Layout.fillWidth:true; spacing:Theme.sm
                UiButton { objectName:"figureExport"; text:"Figure / dashboard dışa aktar"; enabled:dashboard.current && !dashboard.busy && !projects.busy; onClicked:dashboard.export(destination.text,format.currentText) }
                UiButton { text:"Okunabilir figürü öğren"; helpContext:"figure.compose"; onClicked:panel.helpRequested(this,helpContext) }
            }
        }
    }
}
