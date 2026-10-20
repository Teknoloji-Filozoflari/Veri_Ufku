import QtQuick
Canvas {
    id:chart
    property var points:[]
    property string metric:""
    property bool comparable:false
    onPointsChanged:requestPaint()
    onWidthChanged:requestPaint()
    onHeightChanged:requestPaint()
    onPaint:{
        const c=getContext("2d");c.clearRect(0,0,width,height);c.fillStyle=Theme.field;c.fillRect(0,0,width,height);c.fillStyle=Theme.text;c.font="12px sans-serif"
        c.fillText("Maliyet / "+metric+" · "+(comparable?"P: Pareto":"farklı protokol; frontier yok"),12,18)
        let ps=points.filter(p=>isFinite(p.x)&&isFinite(p.y));if(!ps.length){c.fillText("Gerçek fold/süre noktası yok",12,48);return}
        let x0=Math.min(...ps.map(p=>p.x)),x1=Math.max(...ps.map(p=>p.x)),y0=Math.min(...ps.map(p=>p.y)),y1=Math.max(...ps.map(p=>p.y));if(x0===x1){x0=Math.max(0,x0-.5);x1+=.5}if(y0===y1){y0-=.5;y1+=.5}if(metric!=="r2")y0=Math.max(0,y0)
        const left=72,right=width-16,top=40,bottom=height-42;c.strokeStyle=Theme.border;c.beginPath();c.moveTo(left,top);c.lineTo(left,bottom);c.lineTo(right,bottom);c.stroke();c.fillText("Kaydedilen süre (s); kapsam tabloda",left,height-8);c.fillText(y0.toPrecision(3),8,bottom);c.fillText(y1.toPrecision(3),8,top);c.fillText(x0.toPrecision(3),left,bottom+16);c.fillText(x1.toPrecision(3),right-35,bottom+16)
        ps.forEach((p,i)=>{let x=left+(p.x-x0)/(x1-x0)*(right-left),y=bottom-(p.y-y0)/(y1-y0)*(bottom-top);c.fillStyle=p.pareto?Theme.dataTone:Theme.warning;c.beginPath();c.arc(x,y,5,0,2*Math.PI);c.fill();c.fillText((p.pareto?"P ":"")+String(i+1),x+8,y)})
    }
}
