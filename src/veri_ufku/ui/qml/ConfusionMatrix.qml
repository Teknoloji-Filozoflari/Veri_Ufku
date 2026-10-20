import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    property var labels: []
    property var matrix: []
    id: panel
    UiLabel { text:"Karışıklık matrisi · satırlar gerçek, sütunlar tahmin";font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
    ScrollView {
        id: matrixScroll
        Layout.fillWidth:true
        Layout.preferredHeight: Math.min(420, 58 + 40 * panel.labels.length)
        contentWidth: Math.max(420, 100 + 90 * panel.labels.length)
        clip:true
        Canvas {
            objectName:"classificationConfusionMatrix"
            width:matrixScroll.contentWidth
            height:58+40*panel.labels.length
            onWidthChanged:requestPaint()
            Connections { target:panel;function onLabelsChanged(){parent.requestPaint()} function onMatrixChanged(){parent.requestPaint()} }
            onPaint: {
                let ctx=getContext("2d");ctx.clearRect(0,0,width,height);ctx.font="12px sans-serif"
                for(let i=0;i<panel.labels.length;i++){
                    ctx.fillStyle=Theme.text;ctx.fillText(String(panel.labels[i]).slice(0,12),100+i*90,20);ctx.fillText(String(panel.labels[i]).slice(0,12),4,55+i*40)
                    for(let j=0;j<panel.labels.length;j++){
                        ctx.fillStyle=i===j?Theme.mintSurface:Theme.field;ctx.fillRect(95+j*90,30+i*40,86,36)
                        ctx.fillStyle=Theme.text;ctx.fillText(String((panel.matrix[i]||[])[j]||0),125+j*90,53+i*40)
                    }
                }
            }
        }
    }
}
