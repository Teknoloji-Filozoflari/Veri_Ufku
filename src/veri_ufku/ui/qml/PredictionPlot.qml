import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: plot
    property var points: []
    property bool residual: false
    spacing: Theme.sm
    UiLabel { text:plot.residual?"Artık grafiği — x: tahmin, y: gerçek − tahmin (hedef birimi)":"Gerçek / tahmin — x: gerçek, y: tahmin (hedef birimi)";Layout.fillWidth:true;wrapMode:Text.Wrap }
    Canvas {
        id: canvas
        Layout.fillWidth:true;Layout.fillHeight:true
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        Connections { target:plot;function onPointsChanged(){canvas.requestPaint()} function onResidualChanged(){canvas.requestPaint()} }
        onPaint: {
            let ctx=getContext("2d");ctx.reset();ctx.fillStyle="#161c24";ctx.fillRect(0,0,width,height);
            if(!plot.points||!plot.points.length)return;
            let xs=plot.points.map(p=>plot.residual?p.predicted:p.actual),ys=plot.points.map(p=>plot.residual?p.residual:p.predicted);
            let xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys,0),ymax=Math.max(...ys,0);
            if(!plot.residual){xmin=Math.min(xmin,ymin);xmax=Math.max(xmax,ymax);ymin=xmin;ymax=xmax}
            if(xmax===xmin){xmin-=1;xmax+=1}if(ymax===ymin){ymin-=1;ymax+=1}
            let px=x=>48+(x-xmin)/(xmax-xmin)*Math.max(1,width-68),py=y=>height-30-(y-ymin)/(ymax-ymin)*Math.max(1,height-50);
            ctx.strokeStyle="#8e9baa";ctx.beginPath();ctx.moveTo(48,20);ctx.lineTo(48,height-30);ctx.lineTo(width-20,height-30);ctx.stroke();
            ctx.fillStyle="#cbd4df";ctx.font="11px sans-serif";ctx.fillText(xmin.toPrecision(4),48,height-10);ctx.fillText(xmax.toPrecision(4),Math.max(48,width-90),height-10);ctx.fillText(ymax.toPrecision(4),2,20);ctx.fillText(ymin.toPrecision(4),2,height-30);
            ctx.strokeStyle="#ffa95f";ctx.beginPath();ctx.moveTo(px(xmin),py(plot.residual?0:xmin));ctx.lineTo(px(xmax),py(plot.residual?0:xmax));ctx.stroke();
            ctx.fillStyle="#a69bff";for(let i=0;i<xs.length;i++){ctx.beginPath();ctx.arc(px(xs[i]),py(ys[i]),2.5,0,Math.PI*2);ctx.fill()}
        }
        Accessible.role:Accessible.Graphic
        Accessible.name:plot.residual?"Artık grafiği":"Gerçek tahmin grafiği"
        Accessible.description:"Turuncu çizgi ideal tahmin veya sıfır artık; sayısal skorlar metin olarak da sunulur."
    }
}
