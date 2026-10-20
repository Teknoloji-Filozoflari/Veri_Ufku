import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"graphPanel"
    property string helpContext:"model.graph"
    signal helpRequested(var origin,string context)
    readonly property var tasks:["degree","centrality","components","shortest","community","layout"]
    readonly property var result:graphs.historyReport
    readonly property var view:result.view||{}
    function key(c){return c.currentValue||""}
    function display(v){try{return String(JSON.parse(v)[1])}catch(e){return String(v)}}
    function num(value){return typeof value==="number"?value.toFixed(6):"NA"}
    function analyticalText(){var a=panel.result.analysis||{};if(a.reachable!==undefined)return a.reachable?"Yol: "+a.path.map(panel.display).join(" → ")+" · toplam distance="+num(a.distance)+"\nSeçilen edge kimlikleri: "+a.edge_ids.map(panel.display).join(", "):"Hedefe ulaşılamıyor · distance=NA";if(a.values)return a.values.map(function(v){return panel.display(v.node)+(v.pagerank!==undefined?" · PageRank="+num(v.pagerank):" · degree="+v.degree+(v.in_degree!==null?" · in="+v.in_degree+" out="+v.out_degree:"")+(v.weighted_degree!==null?" · weighted="+num(v.weighted_degree):""))}).join("\n")+(a.converged!==undefined?"\nConverged="+a.converged+" · iteration="+a.iterations+" · residual="+num(a.residual):"");if(a.communities)return "Community method: greedy modularity · resolution1 · projection="+a.projection+" · Q="+num(a.modularity)+"\n"+a.communities.map(function(c,i){return (i+1)+": "+c.map(panel.display).join(", ")}).join("\n");if(a.connected)return "Connected components: "+a.connected.map(function(c){return c.map(panel.display).join(", ")}).join(" | ");if(a.weak)return "Weak: "+a.weak.map(function(c){return c.map(panel.display).join(", ")}).join(" | ")+"\nStrong: "+a.strong.map(function(c){return c.map(panel.display).join(", ")}).join(" | ");return "Görünüm işlemi; ek analitik metrik üretilmedi"}
    function config(){return {task:tasks[task.currentIndex],source:key(source),target:key(target),node:unified.checked?key(node):"",record_type:unified.checked?key(type):"",edge_id:useEdge.checked?key(edge):"",weight:useWeight.checked?key(weight):"",attributes:useAttributes.checked?key(attributes):"",node_column:key(nodeColumn),directed:directed.checked,multi_edges:multi.checked?"preserve":"reject",self_loops:loops.checked?"preserve":"reject",weight_meaning:["unweighted","distance","strength"][meaning.currentIndex],strength_to_distance:reciprocal.checked?"reciprocal":"reject",projection:["reject","topology","sum_strength"][projection.currentIndex],path_source:start.text,path_target:end.text,layout:layout.currentIndex===0?"circular":"spring",filter_nodes:JSON.parse(filter.text),view_nodes:Number(nodeBudget.text),view_edges:Number(edgeBudget.text),sample_view:sample.checked,seed:Number(seed.text)}}
    Connections {target:graphs;function onSelectGraph(value){expanded.checked=true;task.currentIndex=panel.tasks.indexOf(value)}}
    UiCheckBox {id:expanded;objectName:"graphExpanded";text:"Faz61 ağ ve graf çalışma alanı";Layout.fillWidth:true}
    ColumnLayout {visible:expanded.checked;Layout.fillWidth:true;spacing:Theme.sm
        UiLabel {text:"Node/edge · bağlantı ve yapısal ölçüler";font.bold:true;Layout.fillWidth:true}
        UiTextField {id:input;objectName:"graphSourceFile";Accessible.name:"Yerel GraphML veya GEXF dosyası";placeholderText:"Mutlak .graphml / .gexf";Layout.fillWidth:true}
        UiButton {objectName:"graphChoose";text:"GraphML/GEXF önizle";enabled:!imports.busy&&!projects.busy&&!graphs.busy;onClicked:imports.choose(input.text);Layout.fillWidth:true}
        UiButton {objectName:"graphImport";text:"Önizlenen graph snapshot'ını içe aktar";enabled:imports.ready&&!projects.busy&&!graphs.busy;onClicked:imports.importData(true);Layout.fillWidth:true}
        StateNotice {heading:"Graph import durumu";detail:imports.errorText||imports.message;kind:imports.errorText?"error":"info";Layout.fillWidth:true}
        UiLabel {text:"Statik düz GraphML/GEXF1.2;2MiB/256node/2000edge. Mixed/dynamic/nested/port/hyperedge/viz desteklenmez, sessiz düşürülmez. XML attributes metin olarak korunur, weight numeric. Node/edge satırları ve disconnected/isolated node'lar kaydedilir. Mevcut CSV/Parquet edge tablosunu da kullanabilirsiniz; ayrı node tablosu seçerek izole düğümleri koruyun.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        ColumnLayout {enabled:!graphs.busy;Layout.fillWidth:true
            UiCombo {id:task;objectName:"graphTask";accessibleLabel:"Graph analiz yöntemi";model:["Degree / weighted incidence","PageRank centrality","Connected components — weak/strong","Shortest path — distance semantics","Community — greedy modularity","Yalnız layout/filter görünümü"];Layout.fillWidth:true}
            UiCombo {id:source;objectName:"graphSource";accessibleLabel:"Edge source ColumnId";model:graphs.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiCombo {id:target;objectName:"graphTarget";accessibleLabel:"Edge target ColumnId";model:graphs.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiCheckBox {id:unified;objectName:"graphUnified";text:"Birleşik node/edge tablo şeması (GraphML/GEXF import için seç)";Layout.fillWidth:true}
            UiCombo {id:type;objectName:"graphRecordType";accessibleLabel:"Birleşik record_type node veya edge kolonu";model:graphs.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiCombo {id:node;objectName:"graphNode";accessibleLabel:"Birleşik node_id kolonu";model:graphs.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiCombo {id:nodeSource;objectName:"graphNodeSource";accessibleLabel:"Ayrı node dataset sürümü";model:graphs.nodeSources;textRole:"label";valueRole:"id";onActivated:graphs.selectNodeSource(currentValue);Layout.fillWidth:true}
            UiCombo {id:nodeColumn;objectName:"graphNodeColumn";accessibleLabel:"Ayrı node tablosu kimlik ColumnId";model:graphs.nodeColumns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiCheckBox {id:useEdge;objectName:"graphUseEdgeID";text:"Kaynak edge_id kolonu seç; yoksa SourceRecordId edge kimliğidir";Layout.fillWidth:true}
            UiCombo {id:edge;objectName:"graphEdgeID";accessibleLabel:"Edge kimlik ColumnId";model:graphs.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiCheckBox {id:useAttributes;objectName:"graphUseAttributes";text:"Kaynak attributes JSON object kolonunu koru";Layout.fillWidth:true}
            UiCombo {id:attributes;objectName:"graphAttributes";accessibleLabel:"Graph attributes JSON ColumnId";model:graphs.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiCheckBox {id:directed;objectName:"graphDirected";text:"Directed graph; dosyanın yönüyle aynı olmalı";Layout.fillWidth:true}
            UiCheckBox {id:multi;objectName:"graphMulti";text:"Paralel edge'leri ayrı kimliklerle koru; aksi halde reject";Layout.fillWidth:true}
            UiCheckBox {id:loops;objectName:"graphLoops";text:"Self-loop koru; aksi halde reject";Layout.fillWidth:true}
            UiCheckBox {id:useWeight;objectName:"graphUseWeight";text:"Weight kolonunu seç (anlamı aşağıda açık)";Layout.fillWidth:true}
            UiCombo {id:weight;objectName:"graphWeight";accessibleLabel:"Edge weight ColumnId";model:graphs.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiCombo {id:meaning;objectName:"graphMeaning";accessibleLabel:"Weight anlamı";model:["Unweighted — bir edge bir bağ","Distance / maliyet — pozitif","Strength / güç — pozitif"];Layout.fillWidth:true}
            UiCheckBox {id:reciprocal;objectName:"graphReciprocal";text:"Shortest için strength'i açıkça1/strength distance'a çevir; orijinal weight korunur";Layout.fillWidth:true}
            UiLabel {text:"PageRank distance ağırlığıyla çalıştırılmaz. Degree edge-incidence sayar: parallel ayrı, undirected loop2; ağırlıklı degree seçili weight toplamıdır. Shortest minimum toplam pozitif distance; parallel edge minimum distance, seçilen edge kimliği sonuçta. Reciprocal bir model varsayımıdır, otomatik fiziksel mesafe değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiTextField {id:start;objectName:"graphPathSource";Accessible.name:"Shortest kaynak typed JSON kimliği";text:'"a"';Layout.fillWidth:true}
            UiTextField {id:end;objectName:"graphPathTarget";Accessible.name:"Shortest hedef typed JSON kimliği";text:'"b"';Layout.fillWidth:true}
            UiCombo {id:projection;objectName:"graphProjection";accessibleLabel:"Community parallel edge basitleştirme politikası";model:["Simple projection gerekiyorsa reddet","Açık topology: parallel multiplicity ve weight kaybını kabul et","Açık sum_strength: parallel weight toplamı, edge sayısı kaybını kabul et"];Layout.fillWidth:true}
            UiLabel {text:"Community yalnız undirected strength/unweighted. Simple projection orijinal graph'ı değiştirmez; kimlikli tam export korunur. Greedy modularity resolution1; topluluk gerçek sınıf değildir. Directed/distance dönüşümü otomatik yapılmaz. PageRank/centrality önem veya nedensel etki kanıtı değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiCombo {id:layout;objectName:"graphLayout";accessibleLabel:"Graph view layout";model:["Circular","Spring —32bounded iteration"];Layout.fillWidth:true}
            UiTextField {id:filter;objectName:"graphFilter";Accessible.name:"Görünüm node filtre JSON listesi";text:"[]";Layout.fillWidth:true}
            UiTextField {id:nodeBudget;objectName:"graphNodeBudget";Accessible.name:"Görsel node bütçesi";text:"64";Layout.fillWidth:true}
            UiTextField {id:edgeBudget;objectName:"graphEdgeBudget";Accessible.name:"Görsel edge bütçesi";text:"256";Layout.fillWidth:true}
            UiCheckBox {id:sample;objectName:"graphSample";text:"Görsel bütçe aşılırsa açık seeded sample; analiz tüm graph üzerinde";Layout.fillWidth:true}
            UiTextField {id:seed;objectName:"graphSeed";Accessible.name:"Graph view seed";text:"61";Layout.fillWidth:true}
            UiButton {objectName:"graphRun";text:"Graph hesabını CPU'da başlat";primary:true;enabled:graphs.canGraphRun;onClicked:{try{graphs.startGraph(JSON.stringify(panel.config()))}catch(e){localError.text="Graph parametre/JSON biçimini kontrol edin"}}Layout.fillWidth:true}
        }
        UiLabel {id:localError;text:"";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiButton {objectName:"graphCancel";text:"Graph işini iptal et";visible:graphs.busy;onClicked:graphs.cancel();Layout.fillWidth:true}
        StateNotice {heading:"Graph hesap durumu";detail:graphs.errorText||graphs.message;kind:graphs.errorText?"error":graphs.busy?"loading":"info";Layout.fillWidth:true}
        UiLabel {objectName:"graphSummary";text:panel.result.status?panel.result.status+" · "+(panel.result.graph_spec||{}).task+" · node="+(panel.result.row_count||0)+"\n"+panel.analyticalText():"Henüz graph sonucu yok";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiCheckBox {id:technical;objectName:"graphTechnical";text:"Teknik hesap tanımı ve kimlikli sonucu göster";Layout.fillWidth:true}
        UiLabel {visible:technical.checked;text:JSON.stringify(panel.result.analysis||{});Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiLabel {objectName:"graphSampleCaption";text:panel.view.total_nodes!==undefined?"Görünüm "+(panel.view.sampled?"SAMPLED":"tam/filtreli")+" · node="+(panel.view.nodes||[]).length+"/"+panel.view.total_nodes+" · edge="+(panel.view.edges||[]).length+"/"+panel.view.total_edges+" · dışlanan node="+panel.view.excluded_nodes+" edge="+panel.view.excluded_edges+"\n"+panel.view.scope:"";Layout.fillWidth:true;wrapMode:Text.Wrap}
        Canvas {objectName:"graphCanvas";visible:!!panel.view.nodes;Layout.preferredWidth:520;Layout.preferredHeight:340;property var graphView:panel.view;onGraphViewChanged:requestPaint();onPaint:{var c=getContext("2d"),ns=graphView.nodes||[],es=graphView.edges||[],pos={};c.fillStyle="#202532";c.fillRect(0,0,width,height);c.font="12px sans-serif";for(var n of ns)pos[n.id]={x:width/2+n.x*210,y:height/2+n.y*130};for(var e of es){var a=pos[e.source],b=pos[e.target];c.strokeStyle="#ff983e";c.beginPath();if(e.source===e.target)c.arc(a.x,a.y-17,15,0,2*Math.PI);else{c.moveTo(a.x,a.y);c.quadraticCurveTo((a.x+b.x)/2+12,(a.y+b.y)/2-12,b.x,b.y)}c.stroke();if((panel.result.graph_spec||{}).directed&&e.source!==e.target){var dx=b.x-a.x,dy=b.y-a.y,l=Math.sqrt(dx*dx+dy*dy)||1,x=b.x-12*dx/l,y=b.y-12*dy/l;c.fillStyle="#fff";c.beginPath();c.moveTo(x,y);c.lineTo(x-8*dx/l+4*dy/l,y-8*dy/l-4*dx/l);c.lineTo(x-8*dx/l-4*dy/l,y-8*dy/l+4*dx/l);c.closePath();c.fill()}}for(var node of ns){var p=pos[node.id];c.fillStyle="#687ab5";c.beginPath();c.arc(p.x,p.y,10,0,2*Math.PI);c.fill();c.fillStyle="#fff";c.fillText(String(node.original_id).slice(0,24),p.x+12,p.y+4)}}}
        UiLabel {text:"Paralel kenarlar çizimde örtüşebilir; aşağıdaki kimlikli listede ayrı gösterilir. İzole node korunur. Layout mesafesi veri distance'ı değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        Repeater {model:panel.view.edges||[];UiLabel {required property var modelData;text:panel.display(modelData.source)+((panel.result.graph_spec||{}).directed?" → ":" ↔ ")+panel.display(modelData.target)+" · edge ID="+panel.display(modelData.id)+" · weight="+modelData.weight;Layout.fillWidth:true;wrapMode:Text.Wrap}}
        Repeater {model:panel.result.warnings||[];UiLabel {required property string modelData;text:modelData;color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap}}
        UiCombo {id:saved;objectName:"graphSaved";accessibleLabel:"Kalıcı graph kayıtları";model:graphs.savedRuns;textRole:"label";valueRole:"id";Layout.fillWidth:true}
        UiButton {objectName:"graphOpen";text:"Kalıcı graph snapshot aç";enabled:!graphs.busy&&saved.currentIndex>=0;onClicked:graphs.openRun(saved.currentValue);Layout.fillWidth:true}
        UiTextField {id:destination;objectName:"graphDestination";Accessible.name:"Yeni tam graph export dosyası";placeholderText:"Yeni mutlak dosya yolu";Layout.fillWidth:true}
        UiCombo {id:exportFormat;objectName:"graphExportFormat";accessibleLabel:"Kimlik koruyan graph export formatı";model:["json","graphml","gexf"];Layout.fillWidth:true}
        UiCheckBox {id:exportConsent;objectName:"graphExportConsent";text:"Tam graph kimlik ve kaynak kayıt bağlarını açıkça export edeceğim; hassas veri içerebilir";Layout.fillWidth:true}
        UiButton {objectName:"graphExport";text:"Tam graph'ı yeni yerel dosyaya yaz";enabled:exportConsent.checked&&!graphs.busy&&panel.result.status==="completed";onClicked:graphs.exportGraph(destination.text,exportFormat.currentText);Layout.fillWidth:true}
        UiLabel {text:"Export görünüm filtresini/sample'ı uygulamaz; tam graph, multi-edge ID ve kaynak kökeni korunur. Integer/string kimlik ayrımı JSON'da korunur; XML için string ID gerekir, tip kaybı varsa reddedilir. Link prediction ve network embedding burada unavailable: negative edge, temporal split/unseen-node ve training scope ayrı doğrulanmadan başarı iddiası yok. Community clustering, embedding eğitimi değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiButton {objectName:"graphHelp";text:"Node/edge, centrality/community ve graph leakage öğren";helpContext:"model.graph";onClicked:panel.helpRequested(this,helpContext);Layout.fillWidth:true}
    }
}
