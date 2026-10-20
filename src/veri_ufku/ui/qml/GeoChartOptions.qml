import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
 id:panel
 property var columns:[]
 property string chartKind:"map-point"
 signal edited()
 function key(p){return p.currentIndex>0?p.currentValue:""}
 function values(){return {geometry:key(geometry),geo_crs:crs.text,geo_measure:key(measure),geo_denominator:key(denominator),geo_measure_mode:mode.currentIndex===0?"count":"rate",geo_classification:["equal","quantile","manual"][classification.currentIndex],geo_thresholds:thresholds.text.trim()?thresholds.text.split(",").map(Number):[],bins:classes.value,grid_bins:grid.value}}
 function restore(s){crs.text=s.geo_crs||"";thresholds.text=(s.geo_thresholds||[]).join(",");mode.currentIndex=s.geo_measure_mode==="rate"?1:0;classification.currentIndex=["equal","quantile","manual"].indexOf(s.geo_classification);for(let p of [geometry,measure,denominator])for(let i=0;i<p.model.length;i++)if(p.model[i].id===s[p===geometry?"geometry":p===measure?"geo_measure":"geo_denominator"])p.currentIndex=i;}
 UiLabel {text:"Çevrimdışı yerel harita · basemap/ağ isteği yok. Nokta ve density Point; choropleth Polygon; raster doğrulanmış GeoTIFF window ister. Geometry seçilirse X/Y kullanılmaz.";Layout.fillWidth:true;wrapMode:Text.Wrap}
 UiCombo {id:geometry;objectName:"geoChartGeometry";accessibleLabel:"Harita WKT geometri";model:[{id:"",name:"Koordinat X/Y kullan"}].concat(panel.columns);textRole:"name";valueRole:"id";Layout.fillWidth:true;onActivated:panel.edited()}
 UiTextField {id:crs;objectName:"geoChartCrs";Accessible.name:"Harita kaynak CRS";placeholderText:"Boşsa kaynak metadata CRS; koordinatlarda açık EPSG";Layout.fillWidth:true;onTextEdited:panel.edited()}
 UiCombo {id:measure;objectName:"geoChartMeasure";accessibleLabel:"Harita ölçüm";model:[{id:"",name:"Ölçüm seç…"}].concat(panel.columns);textRole:"name";valueRole:"id";visible:panel.chartKind==="map-choropleth"||panel.chartKind==="map-raster";Layout.fillWidth:true;onActivated:panel.edited()}
 UiCombo {id:mode;objectName:"geoChartMode";accessibleLabel:"Harita sayım oran türü";model:["Raw sayım","Oran: numerator/denominator veya density count/m²"];visible:panel.chartKind==="map-choropleth"||panel.chartKind==="map-density";Layout.fillWidth:true;onActivated:panel.edited()}
 UiCombo {id:denominator;objectName:"geoChartDenominator";accessibleLabel:"Choropleth pozitif payda";model:[{id:"",name:"Payda seç…"}].concat(panel.columns);textRole:"name";valueRole:"id";visible:panel.chartKind==="map-choropleth"&&mode.currentIndex===1;Layout.fillWidth:true;onActivated:panel.edited()}
 UiCombo {id:classification;objectName:"geoClassification";accessibleLabel:"Choropleth classification";model:["Equal interval","Quantile · ties collapse","Manual eşikler"];visible:panel.chartKind==="map-choropleth";Layout.fillWidth:true;onActivated:panel.edited()}
 UiSpinBox {id:classes;objectName:"geoClassCount";Accessible.name:"Choropleth sınıf sayısı";from:2;to:10;value:5;visible:panel.chartKind==="map-choropleth";Layout.fillWidth:true;onValueModified:panel.edited()}
 UiTextField {id:thresholds;objectName:"geoThresholds";Accessible.name:"Manual artan sınıf eşikleri";placeholderText:"10,20,50";visible:panel.chartKind==="map-choropleth"&&classification.currentIndex===2;Layout.fillWidth:true;onTextEdited:panel.edited()}
 UiSpinBox {id:grid;objectName:"geoDensityGrid";Accessible.name:"Density grid hücre sayısı";from:2;to:80;value:20;visible:panel.chartKind==="map-density";Layout.fillWidth:true;onValueModified:panel.edited()}
 UiLabel {text:"Derece metre değildir; density metre projected CRS ister. Choropleth sayım ile oran farklı soruları yanıtlar. MAUP, antimeridian ve polygon sınırları sonucu etkiler. Haritada brushing temsil noktalarını seçer; polygon intersection filtresi değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap;color:Theme.warning}
}
