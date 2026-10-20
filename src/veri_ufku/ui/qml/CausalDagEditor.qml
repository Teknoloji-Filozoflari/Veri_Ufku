import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

ColumnLayout {
    id: editor
    property var graph: ({nodes:[],edges:[]})
    property var columns: []
    property string helpContext: "causal"
    signal edited()
    function label(id){let c=columns.find(c=>c.id===id);return c?c.name:id}
    function change(g){graph=g;edited();canvas.requestPaint()}
    function nodeNames(){return graph.nodes.map(n=>({id:n.id,name:label(n.id)}))}
    onGraphChanged: canvas.requestPaint()
    UiLabel {text:"DAG editor · roller ve oklar kullanıcı hipotezidir; çizim kanıt değildir. Node/edge gerekçesi zorunlu.";wrapMode:Text.WordWrap;Layout.fillWidth:true}
    RowLayout {
        Layout.fillWidth:true
        UiCombo {id:node;objectName:"causalDagNode";model:editor.columns;textRole:"name";valueRole:"id";accessibleLabel:"DAG ölçülen node";Layout.fillWidth:true}
        UiTextField {id:latent;objectName:"causalDagLatent";placeholderText:"Ölçülmeyen node adı (isteğe bağlı)";Accessible.name:placeholderText;Layout.fillWidth:true}
        UiCombo {id:role;objectName:"causalDagRole";model:["treatment","outcome","confounder","mediator","collider","other"];accessibleLabel:"Kullanıcı gerekçeli DAG rolü"}
    }
    RowLayout {
        Layout.fillWidth:true
        UiTextField {id:reason;objectName:"causalDagReason";placeholderText:"Rolün zamansal/alan bilgisi gerekçesi";Accessible.name:placeholderText;Layout.fillWidth:true}
        UiButton {objectName:"causalDagAddNode";text:"Node ekle/güncelle";onClicked:{let id=latent.text.trim()?"latent:"+latent.text.trim():(node.currentValue||"");if(!id||!reason.text.trim())return;let g=JSON.parse(JSON.stringify(editor.graph));let existing=g.nodes.find(n=>n.id===id);if(existing){existing.role=role.currentText;existing.reason=reason.text}else g.nodes.push({id:id,role:role.currentText,reason:reason.text,x:.15+.16*(g.nodes.length%5),y:.25+.35*Math.floor(g.nodes.length/5)});editor.change(g)}}
    }
    RowLayout {
        Layout.fillWidth:true
        UiCombo {id:fromNode;objectName:"causalDagFrom";model:editor.nodeNames();textRole:"name";valueRole:"id";accessibleLabel:"DAG ok kaynağı";Layout.fillWidth:true}
        UiCombo {id:toNode;objectName:"causalDagTo";model:editor.nodeNames();textRole:"name";valueRole:"id";accessibleLabel:"DAG ok hedefi";Layout.fillWidth:true}
        UiTextField {id:edgeReason;objectName:"causalDagEdgeReason";placeholderText:"Yönlü etki hipotezi gerekçesi";Accessible.name:placeholderText;Layout.fillWidth:true}
        UiButton {objectName:"causalDagAddEdge";text:"Ok ekle";onClicked:{let a=fromNode.currentValue,b=toNode.currentValue;if(!a||!b||a===b||!edgeReason.text.trim())return;let g=JSON.parse(JSON.stringify(editor.graph));if(g.edges.some(e=>e.from===a&&e.to===b))return;g.edges.push({from:a,to:b,reason:edgeReason.text});editor.change(g)}}
    }
    Item {
        objectName:"causalDagCanvas";Layout.fillWidth:true;Layout.preferredHeight:260
        Canvas {
            id:canvas;anchors.fill:parent
            onPaint:{let ctx=getContext("2d");ctx.reset();ctx.strokeStyle=Theme.text;ctx.fillStyle=Theme.text;ctx.lineWidth=2;for(let e of editor.graph.edges){let a=editor.graph.nodes.find(n=>n.id===e.from),b=editor.graph.nodes.find(n=>n.id===e.to);if(!a||!b)continue;let ax=a.x*width,ay=a.y*height,bx=b.x*width,by=b.y*height;let angle=Math.atan2(by-ay,bx-ax);let boundary=Math.min(64/Math.max(.001,Math.abs(Math.cos(angle))),29/Math.max(.001,Math.abs(Math.sin(angle))));bx-=boundary*Math.cos(angle);by-=boundary*Math.sin(angle);ctx.beginPath();ctx.moveTo(ax,ay);ctx.lineTo(bx,by);ctx.stroke();ctx.beginPath();ctx.moveTo(bx,by);ctx.lineTo(bx-10*Math.cos(angle-.5),by-10*Math.sin(angle-.5));ctx.lineTo(bx-10*Math.cos(angle+.5),by-10*Math.sin(angle+.5));ctx.closePath();ctx.fill()}}
        }
        Repeater {
            model:editor.graph.nodes
            Rectangle {
                id:vertex;required property var modelData;required property int index
                x:modelData.x*parent.width-width/2;y:modelData.y*parent.height-height/2
                width:120;height:50;radius:6;color:Theme.surface;border.color:Theme.text;clip:true
                Column {anchors.fill:parent;anchors.margins:4
                    UiLabel {width:parent.width;text:editor.label(vertex.modelData.id);horizontalAlignment:Text.AlignHCenter;elide:Text.ElideRight;wrapMode:Text.NoWrap}
                    UiLabel {width:parent.width;text:vertex.modelData.role;horizontalAlignment:Text.AlignHCenter;elide:Text.ElideRight;wrapMode:Text.NoWrap}
                }
                MouseArea {anchors.fill:parent;drag.target:vertex;onReleased:{let g=JSON.parse(JSON.stringify(editor.graph));g.nodes[vertex.index].x=Math.max(.05,Math.min(.95,(vertex.x+vertex.width/2)/vertex.parent.width));g.nodes[vertex.index].y=Math.max(.05,Math.min(.95,(vertex.y+vertex.height/2)/vertex.parent.height));editor.change(g)}}
            }
        }
    }
    Repeater {
        model:editor.graph.nodes
        RowLayout {
            required property var modelData;required property int index;Layout.fillWidth:true
            UiLabel {text:editor.label(modelData.id)+" · "+modelData.role+" · "+modelData.reason;Layout.fillWidth:true;wrapMode:Text.WordWrap}
            UiButton {text:"Node sil";onClicked:{let g=JSON.parse(JSON.stringify(editor.graph));let id=modelData.id;g.nodes.splice(index,1);g.edges=g.edges.filter(e=>e.from!==id&&e.to!==id);editor.change(g)}}
        }
    }
    Repeater {
        model:editor.graph.edges
        RowLayout {
            required property var modelData;required property int index;Layout.fillWidth:true
            UiLabel {text:editor.label(modelData.from)+" → "+editor.label(modelData.to)+" · "+modelData.reason;Layout.fillWidth:true;wrapMode:Text.WordWrap}
            UiButton {text:"Ok sil";onClicked:{let g=JSON.parse(JSON.stringify(editor.graph));g.edges.splice(index,1);editor.change(g)}}
        }
    }
}
