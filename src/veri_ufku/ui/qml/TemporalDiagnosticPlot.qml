import QtQuick
Canvas {
    id:chart
    property var points:[]
    property string title:"Development diagnostic"
    property string xLabel:"Index / lag"
    onPointsChanged:requestPaint()
    onWidthChanged:requestPaint()
    onHeightChanged:requestPaint()
    Accessible.role:Accessible.Graphic
    Accessible.name:title
    onPaint:{
        const c=getContext("2d");c.clearRect(0,0,width,height);c.fillStyle=Theme.field;c.fillRect(0,0,width,height);c.fillStyle=Theme.text;c.font="12px sans-serif";c.fillText(title,12,18)
        let ps=points.filter(p=>typeof p.y==="number"&&isFinite(p.y));if(!ps.length){c.fillText("Sonlu diagnostic noktası yok",12,48);return}
        let x0=Math.min(...ps.map(p=>p.x)),x1=Math.max(...ps.map(p=>p.x)),y0=Math.min(...ps.map(p=>p.y)),y1=Math.max(...ps.map(p=>p.y));if(x0===x1)x1=x0+1;if(y0===y1){y0-=.5;y1+=.5}
        const left=72,right=width-20,top=40,bottom=height-40;c.strokeStyle=Theme.border;c.beginPath();c.moveTo(left,top);c.lineTo(left,bottom);c.lineTo(right,bottom);c.stroke();c.fillText(y0.toPrecision(3),8,bottom);c.fillText(y1.toPrecision(3),8,top);c.fillText(xLabel+" · "+x0+" … "+x1,left,height-12)
        c.strokeStyle=Theme.dataTone;c.beginPath();let started=false;points.forEach(p=>{if(typeof p.y!=="number"||!isFinite(p.y)){started=false;return}let x=left+(p.x-x0)/(x1-x0)*(right-left),y=bottom-(p.y-y0)/(y1-y0)*(bottom-top);if(!started){c.moveTo(x,y);started=true}else c.lineTo(x,y)});c.stroke()
    }
}
