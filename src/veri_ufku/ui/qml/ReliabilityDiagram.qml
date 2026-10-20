import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id:chart
    property var points:[]
    property string classLabel:""
    property string scope:""
    property int n:0
    property int bins:0
    spacing:Theme.xs
    UiLabel { text:"Reliability diagram · sınıf="+chart.classLabel+" · "+chart.scope+" · n="+chart.n+" · uniform bins="+chart.bins+"\nX: mean predicted probability · Y: observed selected-class fraction · 0..1";Layout.fillWidth:true;wrapMode:Text.Wrap }
    Canvas {
        id:canvas
        Layout.fillWidth:true
        Layout.fillHeight:true
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        Connections { target:chart;function onPointsChanged(){canvas.requestPaint()} }
        onPaint:{
            let c=getContext("2d");c.clearRect(0,0,width,height)
            let left=35,top=8,w=Math.max(1,width-50),h=Math.max(1,height-35)
            c.strokeStyle=Theme.secondary;c.lineWidth=1;c.beginPath();c.moveTo(left,top);c.lineTo(left,top+h);c.lineTo(left+w,top+h);c.stroke()
            c.setLineDash([4,4]);c.beginPath();c.moveTo(left,top+h);c.lineTo(left+w,top);c.stroke();c.setLineDash([])
            c.fillStyle=Theme.secondary;c.font="11px sans-serif";c.fillText("0",left-15,top+h);c.fillText("1",left-15,top+10);c.fillText("0",left,top+h+18);c.fillText("1",left+w-8,top+h+18)
            c.strokeStyle=Theme.accent;c.fillStyle=Theme.accent;c.lineWidth=2;c.beginPath()
            chart.points.forEach((p,i)=>{let x=left+p.mean_probability*w,y=top+(1-p.fraction_positive)*h;if(i===0)c.moveTo(x,y);else c.lineTo(x,y)});c.stroke()
            chart.points.forEach(p=>{c.beginPath();c.arc(left+p.mean_probability*w,top+(1-p.fraction_positive)*h,3,0,Math.PI*2);c.fill()})
        }
    }
}
