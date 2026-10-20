import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "RoadmapSteps.js" as Roadmap
import "FocusScroll.js" as FocusScroll

ColumnLayout {
    id: roadmap
    property bool learningMode: false
    property var library: null
    readonly property var stageModel: learningMode && library ? library.tree.map(function(entry) {
        let meta = Roadmap.stages.find(function(stage) { return stage.id === entry.id })
        return Object.assign({}, entry, meta, {groups: entry.groups})
    }) : Roadmap.stages
    objectName: learningMode ? "learningRoadmap" : "scienceRoadmap"
    property string helpContext: learningMode ? "" : "home.roadmap"
    signal navigate(int section, int tab, var origin)
    signal articleRequested(string articleId, var origin)
    spacing: Theme.lg
    UiLabel { objectName:roadmap.learningMode?"learningRoadmapHeading":"roadmapHeading";text:"Veri Bilimi Yol Haritası";font.pixelSize:Theme.heading;font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:roadmap.learningMode?"Aynı yolculuk, daha derin açıklamalar. Aşamayı aç; kavramı, örneği ve yanlış yorumları birlikte öğren.":"Bir aşamaya tıklayarak çalışma alanını aç. Ayrıntı okunda alt işlemler var; kavramlar ve örnekler Öğren sekmesindeki aynı haritada.";color:Theme.secondary;Layout.fillWidth:true;wrapMode:Text.Wrap }
    Item {
        id: trail
        objectName:roadmap.learningMode?"learningRoadmapTrail":"roadmapTrail"
        Layout.fillWidth:true
        implicitHeight:stagesColumn.height+24
        readonly property bool wide:width>=760
        function repaint() { if(roadmap.visible) line.requestPaint() }
        onWidthChanged:repaint()
        Canvas {
            id:line
            anchors.fill:parent
            onPaint:{
                let ctx=getContext("2d");ctx.reset();
                if(stages.count<2)return;
                ctx.strokeStyle=Theme.border;ctx.lineWidth=2;ctx.beginPath();
                for(let i=0;i<stages.count;i++){
                    let item=stages.itemAt(i),x=item.nodeX,y=item.y+item.nodeY;
                    if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
                }
                ctx.stroke();
            }
        }
        Column {
            id:stagesColumn
            width:parent.width
            spacing:12
            Repeater {
                id:stages
                model:roadmap.stageModel
                Item {
                    id:stage
                    required property var modelData
                    required property int index
                    objectName:roadmap.learningMode?"learningStep-"+modelData.id:"roadmapStage_"+index
                    width:stagesColumn.width
                    height:card.height
                    property bool expanded:false
                    readonly property bool opened: expanded || (roadmap.learningMode && roadmap.library && (roadmap.library.query.length > 0 || roadmap.library.category !== "Tümü"))
                    readonly property int number:Roadmap.stages.findIndex(function(entry){return entry.id===stage.modelData.id})+1
                    readonly property real nodeX:24
                    readonly property real nodeY:40
                    onHeightChanged:trail.repaint()
                    Rectangle {
                        x:stage.nodeX-21;y:stage.nodeY-21;width:42;height:42;radius:21
                        color:Theme.background;border.color:Theme.toneColor(stage.modelData.tone);border.width:2
                        UiLabel { anchors.centerIn:parent;text:stage.number.toString().padStart(2,"0");font.bold:true;font.pixelSize:14;color:Theme.toneColor(stage.modelData.tone) }
                        Rectangle { x:40;y:20;width:20;height:1;color:Theme.toneColor(stage.modelData.tone);opacity:.5 }
                    }
                    Rectangle {
                        id:card
                        objectName:roadmap.learningMode?"learningCard-"+stage.modelData.id:"roadmapCard_"+stage.index
                        x:64
                        width:stage.width-64
                        height:head.height+reveal.height
                        radius:Theme.radius
                        color:Theme.surface
                        border.color:head.hovered||stage.opened?Theme.toneColor(stage.modelData.tone):Theme.border
                        border.width:1
                        Button {
                            id:head
                            property string route:stage.modelData.route||""
                            property bool expertRoute:!!stage.modelData.advanced
                            objectName:roadmap.learningMode?"learningStage-"+stage.modelData.id:"roadmapOpen_"+stage.index
                            property string helpContext:roadmap.learningMode?"":"home.roadmap"
                            width:parent.width
                            height:Math.max(110,headerContent.implicitHeight+32)
                            padding:16
                            hoverEnabled:true
                            onActiveFocusChanged:if(activeFocus)Qt.callLater(function(){FocusScroll.reveal(head)})
                            Accessible.name:stage.modelData.title+(roadmap.learningMode?" — açıklamaları aç":" — işlem ekranını aç")
                            enabled:roadmap.learningMode || stage.modelData.section >= 0
                            Accessible.description:stage.modelData.caption
                            background:Item {}
                            contentItem:ColumnLayout {
                                id:headerContent
                                spacing:8
                                RowLayout {
                                    spacing:10
                                    UiSymbol { symbol:stage.modelData.icon;ink:Theme.toneColor(stage.modelData.tone);Layout.preferredWidth:22;Layout.preferredHeight:22 }
                                    UiLabel { text:"AŞAMA "+stage.number.toString().padStart(2,"0");font.pixelSize:11;font.letterSpacing:1.3;color:Theme.toneColor(stage.modelData.tone);Layout.fillWidth:true }
                                    UiLabel { visible:roadmap.learningMode; text:"⌄";font.pixelSize:20;color:Theme.secondary;rotation:stage.opened?180:0;Behavior on rotation {NumberAnimation {duration:180}} }
                                    UiIconButton { visible:!roadmap.learningMode; objectName:"roadmapToggle_"+stage.index; symbol:stage.opened?"chevron-up":"chevron-down"; tone:stage.modelData.tone; accessibleLabel:stage.modelData.title+" alt işlemlerini aç/kapat"; onClicked:stage.expanded=!stage.expanded }
                                }
                                UiLabel { text:stage.modelData.title;font.pixelSize:Theme.subheading;font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
                                UiLabel { text:stage.modelData.caption + (!roadmap.learningMode && stage.modelData.advanced ? " · Gelişmiş araç" : "");color:Theme.secondary;font.pixelSize:12;Layout.fillWidth:true;wrapMode:Text.Wrap }
                            }
                            onClicked:if(roadmap.learningMode)stage.expanded=!stage.expanded;else if(stage.modelData.section>=0)roadmap.navigate(stage.modelData.section,-1,this)
                            Rectangle { anchors.fill:parent;anchors.margins:3;radius:Theme.radius;color:"transparent";border.width:head.activeFocus?2:0;border.color:Theme.toneColor(stage.modelData.tone) }
                        }
                        Item {
                            id:reveal
                            y:head.height
                            width:parent.width
                            height:stage.opened?details.implicitHeight+24:0
                            clip:true
                            opacity:stage.opened?1:0
                            visible:height>0
                            Behavior on height { NumberAnimation { duration:240;easing.type:Easing.OutCubic } }
                            Behavior on opacity { NumberAnimation { duration:180 } }
                            Column {
                                id:details
                                x:12;y:4;width:parent.width-24
                                spacing:6
                                Repeater {
                                    model:roadmap.learningMode?stage.modelData.groups:stage.modelData.steps
                                    Item {
                                        id:branch
                                        required property var modelData
                                        required property int index
                                        property bool expanded:false
                                        readonly property bool opened:expanded || (roadmap.learningMode && (roadmap.library.query.length>0 || roadmap.library.category!=="Tümü"))
                                        width:details.width
                                        height:step.height+topicReveal.height
                                        Button {
                                            id:step
                                            property string route:branch.modelData.route||""
                                            property bool expertRoute:!!branch.modelData.advanced
                                            objectName:roadmap.learningMode?"learningGroup-"+branch.modelData.id:"roadmapStep_"+stage.index+"_"+branch.index
                                            property string helpContext:roadmap.learningMode?"":"home.roadmap"
                                            width:parent.width
                                            height:Math.max(60,stepContent.implicitHeight+20)
                                            padding:10
                                            hoverEnabled:true
                                            onActiveFocusChanged:if(activeFocus)Qt.callLater(function(){FocusScroll.reveal(step)})
                                            enabled:stage.opened && (roadmap.learningMode?branch.modelData.topics.length>0:!branch.modelData.planned)
                                            Accessible.name:branch.modelData.title
                                            background:Rectangle { radius:10;color:step.hovered?Theme.hover:Theme.field;border.width:step.activeFocus?2:0;border.color:Theme.toneColor(stage.modelData.tone) }
                                            contentItem:ColumnLayout {
                                                id:stepContent
                                                spacing:4
                                                RowLayout {
                                                    UiLabel { text:branch.modelData.title;font.bold:true;color:step.enabled?Theme.text:Theme.secondary;Layout.fillWidth:true;wrapMode:Text.Wrap }
                                                    UiLabel { text:roadmap.learningMode?(branch.modelData.topics.length?(branch.opened?"⌄":"›"):"Henüz içerik yok"):(branch.modelData.planned?"Planlanan":branch.modelData.advanced?"Gelişmiş ↗":"↗");color:Theme.secondary;font.pixelSize:11 }
                                                }
                                                UiLabel { visible:!!branch.modelData.english;text:branch.modelData.english||"";color:Theme.toneColor(stage.modelData.tone);font.pixelSize:11;Layout.fillWidth:true;wrapMode:Text.Wrap }
                                            }
                                            onClicked:{
                                                if(!stage.opened)return
                                                if(roadmap.learningMode){if(branch.modelData.topics.length)branch.expanded=!branch.expanded}
                                                else if(!branch.modelData.planned)roadmap.navigate(branch.modelData.section,branch.modelData.tab===undefined?-1:branch.modelData.tab,this)
                                            }
                                        }
                                        Item {
                                            id:topicReveal
                                            y:step.height;width:parent.width
                                            height:roadmap.learningMode&&branch.opened?topics.implicitHeight+16:0
                                            visible:height>0;clip:true
                                            Behavior on height { NumberAnimation { duration:200;easing.type:Easing.OutCubic } }
                                            Column {
                                                id:topics
                                                x:10;y:6;width:parent.width-20;spacing:8
                                                Repeater {
                                                    model:roadmap.learningMode?branch.modelData.topics:[]
                                                    ColumnLayout {
                                                        required property var modelData
                                                        width:topics.width
                                                        UiButton { objectName:"learningArticle-"+modelData.id; tone:stage.modelData.tone; text:modelData.title; glyph:"→"; multiline:true; Layout.fillWidth:true; Layout.maximumWidth:topics.width; onClicked:roadmap.articleRequested(modelData.id,this) }
                                                        UiLabel { text:modelData.summary; textFormat:Text.PlainText; Layout.fillWidth:true; wrapMode:Text.Wrap; color:Theme.secondary; font.pixelSize:Theme.small }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    opacity:1
                }
            }
        }
    }
    UiLabel { text:roadmap.learningMode?"Aşamalar birbirini destekler; ihtiyaç duydukça önceki konulara dönebilirsin.":"Bu harita zorunlu bir sıra veya tamamlanma puanı değildir. Planlanan yollar kapalıdır. Projeni aşağıdaki alandan oluştur, aç veya kaydet.";color:Theme.secondary;Layout.fillWidth:true;wrapMode:Text.Wrap }
}
