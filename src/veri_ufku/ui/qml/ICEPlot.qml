import QtQuick
import QtQuick.Layouts
ColumnLayout {
    id:chart
    property var grid:[]
    property var lines:[]
    property var mean:[]
    UiLabel { text:"ICE — ilk10 seçili kayıt çizgisi; PDP turuncu ortalama tüm sample'da. Ham model response; CI değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    Canvas {
        id:canvas
        Layout.fillWidth:true
        Layout.fillHeight:true
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        Connections { target:chart;function onGridChanged(){canvas.requestPaint()} function onLinesChanged(){canvas.requestPaint()} function onMeanChanged(){canvas.requestPaint()} }
        onPaint:{
            let c=getContext("2d");c.clearRect(0,0,width,height);if(chart.grid.length<1)return
            let all=chart.mean.slice();chart.lines.forEach(l=>all=all.concat(l.values));if(!all.length)return
            let xmin=Math.min(...chart.grid),xmax=Math.max(...chart.grid),ymin=Math.min(...all),ymax=Math.max(...all),left=50,top=10,w=width-65,h=height-40
            if(xmax===xmin)xmax=xmin+1;if(ymax===ymin){ymin-=0.5;ymax+=0.5}
            function draw(values,color,lineWidth){c.strokeStyle=color;c.lineWidth=lineWidth;c.beginPath();values.forEach((v,i)=>{let x=left+(chart.grid[i]-xmin)/(xmax-xmin)*w,y=top+h-(v-ymin)/(ymax-ymin)*h;if(i===0)c.moveTo(x,y);else c.lineTo(x,y)});c.stroke()}
            chart.lines.forEach(l=>draw(l.values,Theme.secondary,1));draw(chart.mean,Theme.accent,3)
            c.strokeStyle=Theme.secondary;c.beginPath();c.moveTo(left,top);c.lineTo(left,top+h);c.lineTo(left+w,top+h);c.stroke();c.fillStyle=Theme.secondary;c.font="11px sans-serif";c.fillText(xmin.toPrecision(3),left,top+h+18);c.fillText(xmax.toPrecision(3),left+w-35,top+h+18);c.fillText(ymin.toPrecision(3),0,top+h);c.fillText(ymax.toPrecision(3),0,top+10)
        }
    }
}
