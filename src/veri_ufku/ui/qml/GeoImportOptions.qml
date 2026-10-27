import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
 id:panel
 signal helpRequested(var origin,string context)
 property string helpContext:"geo-crs"
 Layout.fillWidth:true
 UiLabel {text:"Mekânsal kaynak · CRS / geometri / extent / nodata"; font.bold:true; Layout.fillWidth:true; wrapMode:Text.Wrap}
 UiLabel {text:"Kaynak salt okunur; repair ve reprojection ayrı önizlemeli işlemdir. x=longitude,y=latitude. Vektör10000feature; raster65536hücre kesit. Yerel harita ağ gerektirmez.";Layout.fillWidth:true;wrapMode:Text.Wrap}
 UiCombo {objectName:"geoLayer";accessibleLabel:"GeoPackage layer";model:imports.choices.sheets||[];visible:imports.formatId==="geopackage";currentIndex:Math.max(0,model.indexOf(imports.settings.sheet||""));onActivated:imports.setOption("sheet",currentText);Layout.fillWidth:true}
 UiLabel {text:"Kaynak CRS eksikse açık atama · mevcut CRS'yi bu alan değiştirmez";Layout.fillWidth:true;wrapMode:Text.Wrap}
 UiTextField {objectName:"geoImportCrs";Accessible.name:"Eksik kaynak CRS ataması";text:imports.settings.geo_crs||"";placeholderText:"EPSG:4326";onEditingFinished:imports.setOption("geo_crs",text);Layout.fillWidth:true}
 UiTextField {objectName:"geoGeometryColumn";Accessible.name:"GeoParquet geometry column";visible:imports.formatId==="geoparquet";text:imports.settings.geo_geometry||"";placeholderText:"Boşsa primary_column";onEditingFinished:imports.setOption("geo_geometry",text);Layout.fillWidth:true}
 UiSpinBox {objectName:"geoRasterBand";Accessible.name:"GeoTIFF band";visible:imports.formatId==="geotiff"||imports.formatId==="tile";from:1;to:1024;value:imports.settings.geo_band||1;onValueModified:imports.setOption("geo_band",value);Layout.fillWidth:true}
 UiTextField {objectName:"geoRasterWindow";Accessible.name:"Raster window col row width height";visible:imports.formatId==="geotiff"||imports.formatId==="tile";text:JSON.stringify(imports.settings.geo_window||[]);placeholderText:"[0,0,128,128]";onEditingFinished:imports.setOption("geo_window",text);Layout.fillWidth:true}
 UiLabel {objectName:"geoSourceMetadata";text:JSON.stringify(imports.choices.geospatial||{},null,2);textFormat:Text.PlainText;wrapMode:Text.WrapAnywhere;Layout.fillWidth:true}
 UiButton { visible: false;text:"CRS ve projeksiyon ne demek?";property string helpContext:"geo-crs";onClicked:panel.helpRequested(this,helpContext);Layout.fillWidth:true}
}
