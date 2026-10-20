import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root
    property var curves: []
    UiLabel { text: "Grafik: solver'ın gerçek x/y değerleri; görünüm dışında hesap yok"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    Canvas {
        id: chart
        objectName: "lessonLabPlot"
        Layout.fillWidth: true; Layout.preferredHeight: 260
        property var colors: ["#b993e8", "#61cfb1", "#fbbf60"]
        onPaint: {
            let ctx=getContext("2d");ctx.reset();ctx.clearRect(0,0,width,height)
            let points=[];for(let c of root.curves)for(let p of c.points)points.push(p)
            if(!points.length)return
            let xmin=Infinity,xmax=-Infinity,ymin=Infinity,ymax=-Infinity
            for(let p of points){xmin=Math.min(xmin,p[0]);xmax=Math.max(xmax,p[0]);ymin=Math.min(ymin,p[1]);ymax=Math.max(ymax,p[1])}
            if(xmin===xmax){xmin-=0.5;xmax+=0.5}
            if(ymin===ymax){ymin-=0.5;ymax+=0.5}
            let left=65,right=width-20,top=18,bottom=height-40
            function px(x){return left+(x-xmin)/(xmax-xmin)*(right-left)}
            function py(y){return bottom-(y-ymin)/(ymax-ymin)*(bottom-top)}
            ctx.strokeStyle="#aaaaaa";ctx.beginPath();ctx.moveTo(left,top);ctx.lineTo(left,bottom);ctx.lineTo(right,bottom);ctx.stroke()
            ctx.font="12px sans-serif";ctx.fillStyle="#dddddd";ctx.fillText(xmin.toPrecision(4),left,bottom+20);ctx.fillText(xmax.toPrecision(4),right-50,bottom+20);ctx.fillText(ymax.toPrecision(4),1,top+10);ctx.fillText(ymin.toPrecision(4),1,bottom)
            for(let i=0;i<root.curves.length;i++){
                let values=root.curves[i].points
                ctx.strokeStyle=colors[i%colors.length];ctx.fillStyle=colors[i%colors.length];ctx.beginPath()
                for(let j=0;j<values.length;j++){let x=px(values[j][0]),y=py(values[j][1]);if(j===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)}
                ctx.stroke()
                for(let p of values){ctx.beginPath();ctx.arc(px(p[0]),py(p[1]),2,0,2*Math.PI);ctx.fill()}
            }
        }
        onWidthChanged: requestPaint()
    }
    Repeater { model: root.curves; delegate: UiLabel { required property var modelData; required property int index; text: "● "+modelData.name; color: chart.colors[index%chart.colors.length]; Layout.fillWidth: true; wrapMode: Text.WordWrap } }
    onCurvesChanged: chart.requestPaint()
}
