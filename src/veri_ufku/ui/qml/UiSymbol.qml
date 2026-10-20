import QtQuick

Canvas {
    id: icon
    property string symbol: "home"
    property color ink: Theme.text
    implicitWidth: 24
    implicitHeight: 24
    onInkChanged: requestPaint()
    onSymbolChanged: requestPaint()
    onPaint: {
        const ctx = getContext("2d")
        ctx.reset()
        ctx.scale(width / 24, height / 24)
        ctx.strokeStyle = ink
        ctx.fillStyle = ink
        ctx.lineWidth = 1.8
        ctx.lineCap = "round"
        ctx.lineJoin = "round"
        ctx.beginPath()
        if (icon.symbol === "search") {
            ctx.arc(10, 10, 6, 0, Math.PI * 2)
            ctx.moveTo(15, 15); ctx.lineTo(21, 21)
        } else if (icon.symbol === "sidebar") {
            ctx.rect(3, 4, 18, 16)
            ctx.moveTo(9, 4); ctx.lineTo(9, 20)
        } else if (icon.symbol === "settings") {
            ctx.arc(12, 12, 4, 0, Math.PI * 2)
            for (let i = 0; i < 8; ++i) {
                const a = i * Math.PI / 4
                ctx.moveTo(12 + 7 * Math.cos(a), 12 + 7 * Math.sin(a))
                ctx.lineTo(12 + 10 * Math.cos(a), 12 + 10 * Math.sin(a))
            }
        } else if (icon.symbol === "close") {
            ctx.moveTo(6, 6); ctx.lineTo(18, 18)
            ctx.moveTo(18, 6); ctx.lineTo(6, 18)
        } else if (icon.symbol === "back") {
            ctx.moveTo(14, 5); ctx.lineTo(7, 12); ctx.lineTo(14, 19)
        } else if (icon.symbol === "chevron-down" || icon.symbol === "chevron-up") {
            const tip = icon.symbol === "chevron-down" ? 15 : 9
            const side = icon.symbol === "chevron-down" ? 9 : 15
            ctx.moveTo(5, side); ctx.lineTo(12, tip); ctx.lineTo(19, side)
        } else if (icon.symbol === "up") {
            ctx.moveTo(5, 11); ctx.lineTo(12, 4); ctx.lineTo(19, 11)
            ctx.moveTo(12, 4); ctx.lineTo(12, 21)
        } else if (icon.symbol === "sprout") {
            ctx.moveTo(12, 21)
            ctx.lineTo(12, 12)
            ctx.moveTo(12, 15)
            ctx.bezierCurveTo(4, 15, 3, 10, 3, 7)
            ctx.bezierCurveTo(9, 7, 12, 10, 12, 15)
            ctx.moveTo(12, 12)
            ctx.bezierCurveTo(12, 5, 17, 3, 21, 3)
            ctx.bezierCurveTo(21, 9, 18, 12, 12, 12)
        } else if (icon.symbol === "sliders") {
            for (let i = 0; i < 3; ++i) {
                const x = 5 + 7 * i
                const y = i === 1 ? 15 : 8
                ctx.moveTo(x, 3); ctx.lineTo(x, y - 3)
                ctx.moveTo(x, y + 3); ctx.lineTo(x, 21)
                ctx.moveTo(x + 3, y); ctx.arc(x, y, 3, 0, Math.PI * 2)
            }
        } else if (icon.symbol === "home") {
            ctx.moveTo(3, 10); ctx.lineTo(12, 3); ctx.lineTo(21, 10)
            ctx.moveTo(5, 9); ctx.lineTo(5, 21); ctx.lineTo(10, 21)
            ctx.lineTo(10, 15); ctx.lineTo(14, 15); ctx.lineTo(14, 21)
            ctx.lineTo(19, 21); ctx.lineTo(19, 9)
        } else if (icon.symbol === "table") {
            ctx.rect(3, 4, 18, 16)
            ctx.moveTo(3, 9); ctx.lineTo(21, 9)
            ctx.moveTo(3, 14); ctx.lineTo(21, 14)
            ctx.moveTo(9, 4); ctx.lineTo(9, 20)
            ctx.moveTo(15, 4); ctx.lineTo(15, 20)
        } else if (icon.symbol === "prepare") {
            ctx.moveTo(15, 3); ctx.lineTo(19, 7); ctx.lineTo(8, 18)
            ctx.lineTo(4, 14); ctx.closePath()
            ctx.moveTo(13, 5); ctx.lineTo(17, 9)
            ctx.moveTo(3, 21); ctx.lineTo(21, 21)
            ctx.moveTo(5, 3); ctx.lineTo(5, 7)
            ctx.moveTo(3, 5); ctx.lineTo(7, 5)
            ctx.moveTo(20, 13); ctx.lineTo(20, 17)
            ctx.moveTo(18, 15); ctx.lineTo(22, 15)
        } else if (icon.symbol === "chart") {
            ctx.moveTo(3, 3); ctx.lineTo(3, 21); ctx.lineTo(21, 21)
            ctx.moveTo(7, 16); ctx.lineTo(11, 11)
            ctx.lineTo(15, 13); ctx.lineTo(21, 6)
        } else if (icon.symbol === "compare") {
            ctx.moveTo(3, 7); ctx.lineTo(20, 7)
            ctx.moveTo(16, 3); ctx.lineTo(20, 7); ctx.lineTo(16, 11)
            ctx.moveTo(21, 17); ctx.lineTo(4, 17)
            ctx.moveTo(8, 13); ctx.lineTo(4, 17); ctx.lineTo(8, 21)
        } else if (icon.symbol === "model") {
            ctx.moveTo(10, 6); ctx.lineTo(6, 17)
            ctx.moveTo(14, 6); ctx.lineTo(18, 17)
            ctx.moveTo(8, 19); ctx.lineTo(16, 19)
            for (const point of [[12, 4], [5, 19], [19, 19]]) {
                ctx.moveTo(point[0] + 3, point[1])
                ctx.arc(point[0], point[1], 3, 0, Math.PI * 2)
            }
        } else if (icon.symbol === "report") {
            ctx.moveTo(14, 3); ctx.lineTo(5, 3); ctx.lineTo(5, 21)
            ctx.lineTo(19, 21); ctx.lineTo(19, 8); ctx.lineTo(14, 3)
            ctx.lineTo(14, 8); ctx.lineTo(19, 8)
            ctx.moveTo(9, 12); ctx.lineTo(15, 12)
            ctx.moveTo(9, 16); ctx.lineTo(15, 16)
        } else if (icon.symbol === "book") {
            ctx.moveTo(12, 5); ctx.bezierCurveTo(9, 3, 5, 3, 2, 4)
            ctx.lineTo(2, 19); ctx.bezierCurveTo(5, 18, 9, 18, 12, 20)
            ctx.bezierCurveTo(15, 18, 19, 18, 22, 19)
            ctx.lineTo(22, 4); ctx.bezierCurveTo(19, 3, 15, 3, 12, 5)
            ctx.lineTo(12, 20)
        }
        ctx.stroke()
    }
}
