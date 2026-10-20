import QtQuick
import QtQuick.Layouts
ColumnLayout {
    id:plot
    property var points:[]
    UiLabel { text:"Geliştirme tarihi → ölçüm; mor: gerçek, turuncu: yalnız önceki değerlerin hareketli ortalaması. En çok son 120 geliştirme dönemi.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    Canvas {
        id:canvas
        Layout.fillWidth:true;Layout.fillHeight:true
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        Connections { target:plot;function onPointsChanged(){canvas.requestPaint()} }
        onPaint: {
            let c=getContext("2d");c.reset();c.fillStyle="#161c24";c.fillRect(0,0,width,height)
            let p=plot.points;if(!p||!p.length)return
            let valid=v=>v!==null&&v!==undefined&&Number.isFinite(Number(v))
            let values=p.map(v=>Number(v.actual)).concat(p.filter(v=>valid(v.rolling)).map(v=>Number(v.rolling))).filter(v=>Number.isFinite(v))
            if(!values.length)return
            let low=Math.min(...values),high=Math.max(...values);if(low===high){low-=1;high+=1}
            let x=i=>50+i/Math.max(1,p.length-1)*(width-70),y=v=>height-40-(v-low)/(high-low)*(height-65)
            c.strokeStyle="#8e9baa";c.beginPath();c.moveTo(50,20);c.lineTo(50,height-40);c.lineTo(width-20,height-40);c.stroke()
            c.fillStyle="#cbd4df";c.font="11px sans-serif";c.fillText(high.toPrecision(4),0,20);c.fillText(low.toPrecision(4),0,height-40);c.fillText(p[0].date.slice(0,10),50,height-10);c.fillText(p[p.length-1].date.slice(0,10),Math.max(50,width-100),height-10)
            for(let field of ["actual","rolling"]){c.strokeStyle=field==="actual"?"#a69bff":"#ffa95f";c.beginPath();let started=false;for(let i=0;i<p.length;i++){if(!valid(p[i][field])){started=false;continue}if(!started){c.moveTo(x(i),y(Number(p[i][field])));started=true}else c.lineTo(x(i),y(Number(p[i][field])))}c.stroke()}
        }
        Accessible.role:Accessible.Graphic
        Accessible.name:"Geçmiş zaman serisi ve geçmiş hareketli ortalama"
        Accessible.description:"Tarih yatay, ölçüm dikey eksendedir; sayısal trend ayrıca metindir. Final kayıtlar çizilmez."
    }
}
