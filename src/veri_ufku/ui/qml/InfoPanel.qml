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
    color: Theme.mintSurface
    border.color: Theme.learningTone
    ScrollView {
        id: helpScroll
        anchors.fill: parent
        anchors.margins: Theme.xl
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: parent.width
            spacing: Theme.lg
            UiButton { tone: "mint";
                id: closeButton
                objectName: "helpCloseButton"
                text: qsTranslate("Shell", "Close information")
                glyph: "×"
                Layout.fillWidth: true
                onClicked: panel.closeRequested()
            }
            UiLabel { text: qsTranslate("Shell", "What is this for?"); color: Theme.learningTone; font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            ArticleView { Layout.fillWidth: true; library: panel.library }
            UiLabel { text: qsTranslate("Shell", "Closing this panel preserves your view, task and results."); color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        }
    }
}
