import QtQuick
Canvas {
    id:chart
    property var points:[]
    onPointsChanged:requestPaint()
    onWidthChanged:requestPaint()
    onHeightChanged:requestPaint()
    onPaint:{let c=getContext("2d");c.reset();c.fillStyle="#161c24";c.fillRect(0,0,width,height);if(!points.length)return;let max=Math.max(...points.map(p=>Number(p.count)));let gap=(height-30)/points.length;c.fillStyle="#cbd4df";c.font="11px sans-serif";c.fillText("Terim → frekans (en yüksek15)",5,15);for(let i=0;i<points.length;i++){c.fillStyle="#cbd4df";c.fillText(points[i].term.slice(0,20),5,32+i*gap);c.fillStyle="#ffa95f";c.fillRect(145,22+i*gap,Number(points[i].count)/max*Math.max(1,width-200),Math.max(2,gap-4));c.fillStyle="#cbd4df";c.fillText(String(points[i].count),Math.max(150,width-45),32+i*gap)}}
    Accessible.role:Accessible.Graphic
    Accessible.name:"Terim frekans sütun grafiği"
    Accessible.description:"Terimler ve tüm kolondaki tekrar sayıları tabloda da sunulur."
}
