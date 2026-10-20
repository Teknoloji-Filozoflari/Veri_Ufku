import QtQuick

Canvas {
    id: chart
    objectName: "searchCurve"
    property var points: []
    property string title: "İç validation eğrisi"
    property string xLabel: "Parametre"
    property string yLabel: "Metric"
    onPointsChanged:requestPaint()
    onWidthChanged:requestPaint()
    onHeightChanged:requestPaint()
    onPaint:{
        const c=getContext("2d");c.clearRect(0,0,width,height);c.fillStyle=Theme.field;c.fillRect(0,0,width,height)
        let valid=points.filter(p=>typeof p.x==="number"&&typeof p.y==="number"&&isFinite(p.x)&&isFinite(p.y)).slice().sort((a,b)=>a.x-b.x)
        c.font="12px sans-serif";c.fillStyle=Theme.text;c.fillText(title,12,18)
        if(valid.length===0){c.fillText("Geçerli numeric curve point yok",12,50);return}
        let x0=Math.min(...valid.map(p=>p.x)),x1=Math.max(...valid.map(p=>p.x)),y0=Math.min(...valid.map(p=>p.y)),y1=Math.max(...valid.map(p=>p.y))
        if(x0===x1){x0-=0.5;x1+=0.5}y0=0;y1=(yLabel==="accuracy"||yLabel==="f1_macro")?1:Math.max(0.001,y1*1.05)
        const left=72,right=width-20,top=40,bottom=height-48
        c.strokeStyle=Theme.border;c.beginPath();c.moveTo(left,top);c.lineTo(left,bottom);c.lineTo(right,bottom);c.stroke()
        c.fillText(xLabel,left,bottom+34);c.fillText(yLabel,12,top-8)
        c.fillText(x0.toPrecision(3),left,bottom+16);c.fillText(x1.toPrecision(3),right-30,bottom+16)
        c.fillText(y0.toPrecision(3),12,bottom);c.fillText(y1.toPrecision(3),12,top+10)
        c.strokeStyle=Theme.dataTone;c.lineWidth=2;c.beginPath()
        valid.forEach((p,i)=>{let x=left+(p.x-x0)/(x1-x0)*(right-left),y=bottom-(p.y-y0)/(y1-y0)*(bottom-top);if(i===0)c.moveTo(x,y);else c.lineTo(x,y)});c.stroke()
    }
}
