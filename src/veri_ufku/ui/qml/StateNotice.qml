import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Frame {
    id: notice
    property string kind: "empty"
    property string heading: ""
    property string detail: ""
    padding: Theme.lg
    implicitHeight: body.implicitHeight + 2 * padding
    background: Rectangle {
        radius: Theme.radius
        color: notice.kind === "error" ? Theme.errorSurface : (notice.kind === "unavailable" ? Theme.warningSurface : Theme.surface)
        border.color: Theme.border
    }
    ColumnLayout {
        id: body
        width: parent.width
        spacing: Theme.sm
        Label {
            Layout.fillWidth: true
            text: (notice.kind === "error" ? "!  " : (notice.kind === "canceled" ? "×  " : "○  ")) + notice.heading
            font.pixelSize: Theme.body
            font.bold: true
            color: notice.kind === "error" ? Theme.error : (notice.kind === "unavailable" ? Theme.warning : Theme.text)
            wrapMode: Text.WordWrap
            Accessible.role: Accessible.StaticText
        }
        Label {
            Layout.fillWidth: true
            text: notice.detail
            visible: text.length > 0
            font.pixelSize: Theme.body
            wrapMode: Text.WordWrap
        }
        BusyIndicator {
            visible: notice.kind === "loading"
            running: visible
            Accessible.name: notice.heading
        }
    }
}
