import QtQuick
import QtQuick.Layouts

Item {
    id: plot
    property var spectrumData: ({})
    property string unit: ""
    Accessible.role:Accessible.Graphic
    Accessible.name: "Sinyal spektrogramı: zaman saniye, frekans Hz, doğrusal PSD"
    implicitHeight: 310
    property var frequencies: spectrumData.frequency_hz || []
    property var times: spectrumData.center_seconds || []
    property var power: spectrumData.power || []
    property real maximum: {let m=0;for(let row of power)for(let v of row)m=Math.max(m,v);return m}
    onSpectrumDataChanged: chart.requestPaint()
    Canvas {
        id:chart
        anchors.fill:parent
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        onPaint:{let c=getContext("2d");c.clearRect(0,0,width,height);let l=65,r=25,top=30,b=55,w=width-l-r,h=height-top-b;c.fillStyle="#252b38";c.fillRect(l,top,w,h);let rows=plot.power.length,cols=plot.times.length;if(!rows||!cols)return;for(let i=0;i<rows;i++){for(let j=0;j<cols;j++){let z=plot.maximum>0?plot.power[i][j]/plot.maximum:0;c.fillStyle=Qt.rgba(.08+.9*z,.12+.7*Math.sqrt(z),.25+.3*(1-z),1);c.fillRect(l+j*w/cols,top+(rows-1-i)*h/rows,w/cols+.1,h/rows+.1)}}c.fillStyle="#f0eef4";c.font="12px sans-serif";c.fillText("Frekans (Hz)",l,18);c.fillText(Number(plot.frequencies[rows-1]).toPrecision(4),5,top+12);c.fillText("0",35,top+h);c.fillText(Number(plot.times[0]).toPrecision(4),l,top+h+20);c.fillText(Number(plot.times[cols-1]).toPrecision(4),l+w-45,top+h+20);c.fillText("Zaman (s) · PSD ("+plot.unit+"²/Hz) · renk: 0 → "+Number(plot.maximum).toPrecision(4),l,top+h+42)}
    }
}
