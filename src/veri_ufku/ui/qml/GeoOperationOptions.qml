import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
 id:panel
 signal helpRequested(var origin,string context)
 property string helpContext:"geo-crs"
 readonly property var kinds:["geo_coordinates","geo_assign","geo_reproject","geo_repair","geo_buffer","geo_area","geo_distance","geo_clip","geo_join","geo_block","geo_moran"]
 readonly property string action:kinds[kind.currentIndex]
 function template(){let p={crs:"EPSG:4326"};if(action==="geo_reproject")p.target_crs="EPSG:32635";if(["geo_coordinates","geo_area","geo_distance","geo_join","geo_block"].indexOf(action)>=0){p.output_id=operations.newColumnId();p.output_name=action==="geo_coordinates"?"geometry":action==="geo_block"?"spatial_block":action.replace("geo_","");}if(action==="geo_buffer")p.distance=100;if(action==="geo_distance")p.reference_wkt="POINT (0 0)";if(action==="geo_clip")p.mask_wkt="POLYGON ((0 0,1 0,1 1,0 1,0 0))";if(action==="geo_join"){p.predicate="intersects";}if(action==="geo_block"){p.block_size=1000;p.folds=3;p.seed=42;}if(action==="geo_moran"){p.neighbors="distance";p.threshold=1000;p.standardization="row";p.permutations=99;p.seed=42;}return p;}
 function reset(){params.text=JSON.stringify(template(),null,2);operations.discardPreview();}
 function preview(){let p=JSON.parse(params.text);let ids=[geometry.currentValue];if(action==="geo_coordinates"||action==="geo_moran")ids.push(auxiliary.currentValue);if(action==="geo_join"){p.secondary_version_id=secondary.currentValue;p.secondary_geometry=otherGeometry.currentValue;}operations.previewCleaning(action,JSON.stringify(ids),JSON.stringify(p),"chain");}
 Component.onCompleted:reset()
 UiCombo {id:kind;objectName:"geoOperationKind";accessibleLabel:"Mekânsal işlem";model:["Koordinat → Point","CRS atama · koordinat değişmez","Reproject · koordinat dönüşümü","Repair · make_valid önizle","Buffer · metre","Area · m²","Mesafe · metre","Clip · WKT mask","Spatial join · tüm matching RowIds","Spatial block validation plan","Moran I · açık komşuluk"];Layout.fillWidth:true;onActivated:panel.reset()}
 UiCombo {id:geometry;objectName:"geoOperationGeometry";accessibleLabel:"WKT geometri veya X koordinatı";model:operations.transformColumns;textRole:"name";valueRole:"id";Layout.fillWidth:true;onActivated:operations.discardPreview()}
 UiCombo {id:auxiliary;objectName:"geoOperationAuxiliary";accessibleLabel:"Y koordinatı veya Moran ölçümü";model:operations.transformColumns;textRole:"name";valueRole:"id";visible:panel.action==="geo_coordinates"||panel.action==="geo_moran";Layout.fillWidth:true;onActivated:operations.discardPreview()}
 UiCombo {id:secondary;objectName:"geoJoinDataset";accessibleLabel:"Spatial join ikinci dataset";model:operations.secondaryDatasets;textRole:"label";valueRole:"version_id";visible:panel.action==="geo_join";Layout.fillWidth:true;onActivated:operations.discardPreview()}
 UiCombo {id:otherGeometry;objectName:"geoJoinGeometry";accessibleLabel:"Spatial join ikinci geometry";model:secondary.currentIndex>=0?secondary.model[secondary.currentIndex].columns:[];textRole:"name";valueRole:"id";visible:panel.action==="geo_join";Layout.fillWidth:true;onActivated:operations.discardPreview()}
 UiLabel {text:"Taşınabilir parametre tarifi · CRS ve işlem birimleri açık";Layout.fillWidth:true;wrapMode:Text.Wrap}
 UiTextArea {id:params;objectName:"geoOperationParameters";Accessible.name:"Mekânsal işlem parametre JSON";Layout.fillWidth:true;implicitHeight:160;onTextChanged:operations.discardPreview()}
 UiLabel {text:"Preview kaynak değiştirmez; Uygula yeni sürüm üretir, undo eski geometriyi getirir. Repair tür/split değişebilir. Metre işlemleri uygun projected CRS ister; derece/Web Mercator reddi. Spatial block kolonunu model GROUP olarak seç; random split bağımlılığı çözmez, komşu blocklar hâlâ bağımlı olabilir.";Layout.fillWidth:true;wrapMode:Text.Wrap;color:Theme.warning}
 UiLabel {objectName:"geoOperationDiagnostics";text:JSON.stringify(operations.previewResult.diagnostics||{},null,2);textFormat:Text.PlainText;Layout.fillWidth:true;wrapMode:Text.WrapAnywhere}
 UiButton {text:"CRS, matching ve sızıntı yardımı";property string helpContext:"geo-leakage";Layout.fillWidth:true;onClicked:panel.helpRequested(this,helpContext)}
}
