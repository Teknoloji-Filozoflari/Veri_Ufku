import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: panel
    property string heading: ""
    property string detail: ""
    property var library: learning
    property string articleId: library.article.id
    onArticleIdChanged: if (helpScroll.contentItem) helpScroll.contentItem.contentY = 0
    signal closeRequested()
    function focusFirst() { closeButton.forceActiveFocus() }
    color: Theme.surface
    border.color: Theme.border
    ScrollView {
        id: helpScroll
        anchors.fill: parent
        anchors.margins: Theme.xl
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: parent.width
            spacing: Theme.lg
            UiButton {
                id: closeButton
                objectName: "helpCloseButton"
                text: qsTranslate("Shell", "Close information")
                glyph: "×"
                Layout.fillWidth: true
                onClicked: panel.closeRequested()
            }
            Label { text: qsTranslate("Shell", "What is this for?"); font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            ArticleView { Layout.fillWidth: true; library: panel.library }
            Label { text: qsTranslate("Shell", "Closing this panel preserves your view, task and results."); color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        }
    }
}
