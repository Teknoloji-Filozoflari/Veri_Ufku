import QtQuick
import QtQuick.Layouts

// Construct on first use; retain forms and signal connections when navigating away.
// Controllers and running jobs remain owned by the existing application engine.
Loader {
    id: panel
    property bool requested: false
    property bool visited: false
    active: visited
    visible: requested
    Layout.fillWidth: true
    Layout.leftMargin: Theme.xl
    Layout.rightMargin: Theme.xl
    onRequestedChanged: if (requested) visited = true
    Component.onCompleted: if (requested) visited = true
}
