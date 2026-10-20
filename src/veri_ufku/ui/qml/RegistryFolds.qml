import QtQuick
Canvas {
    id:chart
    property var runs:[]
    property string metric:""
    onRunsChanged:requestPaint()
    onWidthChanged:requestPaint()
    onHeightChanged:requestPaint()
    onPaint:{
        const c=getContext("2d");c.clearRect(0,0,width,height);c.fillStyle=Theme.field;c.fillRect(0,0,width,height);c.fillStyle=Theme.text;c.font="12px sans-serif";c.fillText("Gerçek fold dağılımları · "+metric+" · run sırası tabloyla aynı",12,18)
        let ps=[];runs.forEach((r,i)=>(r.folds||[]).forEach((f,j)=>ps.push({x:i+1,fold:j,y:f.value})));if(!ps.length){c.fillText("Kayıtlı CV fold yok; yapay fold üretilmez",12,48);return}
        let y0=Math.min(...ps.map(p=>p.y)),y1=Math.max(...ps.map(p=>p.y));if(y0===y1){y0-=.5;y1+=.5}
        const left=72,right=width-20,top=40,bottom=height-40;c.strokeStyle=Theme.border;c.beginPath();c.moveTo(left,top);c.lineTo(left,bottom);c.lineTo(right,bottom);c.stroke();c.fillText(y0.toPrecision(3),8,bottom);c.fillText(y1.toPrecision(3),8,top)
        runs.forEach((r,i)=>{let x=left+(i+.5)/runs.length*(right-left);c.fillStyle=Theme.text;c.fillText(String(i+1),x,bottom+20)});ps.forEach(p=>{let x=left+(p.x-.5)/runs.length*(right-left)+((p.fold%5)-2)*4,y=bottom-(p.y-y0)/(y1-y0)*(bottom-top);c.fillStyle=Theme.dataTone;c.beginPath();c.arc(x,y,4,0,2*Math.PI);c.fill()})
    }
}
