import QtQuick

Canvas {
    id: plot
    objectName: "classificationCurve"
    property var points: []
    property string title: "ROC"
    property bool precisionRecall: false
    onPointsChanged:requestPaint()
    onWidthChanged:requestPaint()
    onHeightChanged:requestPaint()
    onPaint:{
        let c=getContext("2d");c.clearRect(0,0,width,height);c.fillStyle=Theme.field;c.fillRect(0,0,width,height)
        const left=48,top=30,right=width-20,bottom=height-38
        c.font="12px sans-serif";c.fillStyle=Theme.text;c.fillText(title,12,18);c.fillText(precisionRecall?"Recall":"Yanlış alarm oranı (FPR)",left,bottom+27);c.fillText(precisionRecall?"Precision":"TPR / Recall",left,top+14)
        c.strokeStyle=Theme.border;c.lineWidth=1;c.beginPath();c.moveTo(left,top);c.lineTo(left,bottom);c.lineTo(right,bottom);c.stroke();c.fillText("0",left-12,bottom+12);c.fillText("1",right-2,bottom+12);c.fillText("0",left-16,bottom);c.fillText("1",left-16,top+5)
        c.strokeStyle=Theme.dataTone;c.lineWidth=2;c.beginPath()
        points.forEach(function(p,i){let x=left+p.x*(right-left),y=bottom-p.y*(bottom-top);if(i===0)c.moveTo(x,y);else c.lineTo(x,y)});c.stroke()
    }
}
